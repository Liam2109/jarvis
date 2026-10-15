# Test du mode jeu / ne pas déranger. N'ouvre ni fenêtre, ni micro, ni son, ne touche à aucun focus ; le premier plan est SIMULÉ.
$ErrorActionPreference = 'Stop'
$env:JARVIS_TEST = '1'      # TEST SILENCIEUX : aucun son, aucune fenêtre, aucun micro, aucune touche, aucune action réelle (voir lib\journal.ps1)
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $Root 'lib\journal.ps1'); Import-JarvisEnv
$Config = Get-Content (Get-ConfigPath) -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($l in 'voix', 'business', 'permissions', 'actions', 'coffre', 'entrees', 'ecrans', 'tableau', 'visage', 'sons', 'raccourcis', 'cerveau', 'cerveau-local', 'veille', 'memoire', 'rapide', 'discretion', 'modejeu', 'boucle') { . (Join-Path $Root "lib\$l.ps1") }
Remove-Item $script:StopFlag, $script:ParleFlag -ErrorAction SilentlyContinue
$echecs = 0
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }

$tmp = Join-Path $env:TEMP "jarvis-test-jeu-$([guid]::NewGuid().ToString('N'))"; New-Item -ItemType Directory $tmp | Out-Null
function Get-FichierAlertes { Join-Path $tmp 'alertes.json' }
function Get-FichierBriefingVocal { Join-Path $tmp 'briefing-vocal.txt' }
$script:AlertesCache = $null
# Tout ce qui ferait du bruit ou toucherait au disque est remplacé et compté
$script:Lectures = 0; $script:Dits = @(); $script:Musiques = 0; $script:Lecteurs = 0
function Lire-Mp3([string]$f) { $script:Lectures++ }
function Stop-Musiques { $script:Musiques++ }
function New-Lecteur([string]$f, [double]$v) { $script:Lecteurs++; $null }
$script:RappelsFaux = @()
function Get-Rappels { @($script:RappelsFaux) }
function Save-Rappels($l) { }
function Add-Conv([string]$role, [string]$texte) { $script:Conv += "$role|$texte" }
$script:Conv = @()

Write-Host '1) Premier plan : seul un jeu ou une application plein écran déclenche le mode'
function PP($proc, $titre = '', $plein = $false, $classe = 'Cls', $pid_ = 5000) { @{ pid = $pid_; proc = $proc; classe = $classe; titre = $titre; plein = $plein } }
$cfg = Get-ConfigJeu
foreach ($p in 'steam', 'steamwebhelper', 'RobloxPlayerBeta', 'Minecraft.Windows', 'eldenring', 'VALORANT-Win64-Shipping') { Verifier (Test-JeuPremierPlan (PP $p) $cfg) "jeu reconnu : $p" }
Verifier (Test-JeuPremierPlan (PP 'javaw' 'Minecraft 1.20') $cfg) 'Minecraft Java (javaw + titre Minecraft)'
Verifier (-not (Test-JeuPremierPlan (PP 'javaw' 'Mon éditeur') $cfg)) 'javaw sans Minecraft : pas un jeu'
Verifier (-not (Test-JeuPremierPlan (PP 'chrome' 'Minecraft wiki - Google Chrome') $cfg)) 'un onglet de navigateur intitulé « Minecraft » n''est PAS un jeu'
Verifier (-not (Test-JeuPremierPlan (PP 'WINWORD' 'Document1') $cfg)) 'Word maximisé (avec barre de titre) : pas un jeu'
Verifier (Test-JeuPremierPlan (PP 'monjeu' 'Mon Jeu' $true) $cfg) 'application inconnue en plein écran (sans barre de titre) : mode jeu'
Verifier (Test-JeuPremierPlan (PP 'vlc' 'film.mkv' $true) $cfg) 'vidéo plein écran : mode ne pas déranger'
Verifier (-not (Test-JeuPremierPlan (PP 'explorer' '' $true 'Progman') $cfg)) 'le bureau Windows n''est pas un plein écran'
Verifier (-not (Test-JeuPremierPlan (PP 'msedge' 'JarvisOrb-1234' $true) $cfg)) 'l''orbe de Jarvis n''est jamais pris pour un jeu (titre unique)'
$script:EdgePid = 7000
function Get-ArbrePids([int]$racine) { @(7000, 7001, 7002) }
Verifier (-not (Test-JeuPremierPlan (PP 'msedge' 'Autre titre' $true 'Chrome_WidgetWin_1' 7001) $cfg)) 'ni aucune fenêtre du processus Edge lancé par Jarvis (PID)'
$script:EdgePid = 0
Verifier (-not (Test-JeuPremierPlan $null $cfg)) 'pas de fenêtre au premier plan : pas de mode jeu'
$cfg2 = Get-ConfigJeu; $cfg2.plein_ecran = $false
Verifier (-not (Test-JeuPremierPlan (PP 'monjeu' 'Mon Jeu' $true) $cfg2) -and (Test-JeuPremierPlan (PP 'steam') $cfg2)) 'plein_ecran_auto=false : seule la liste d''applications compte'
$src = (Get-Content (Join-Path $Root 'lib\modejeu.ps1') -Raw) + (Get-Content (Join-Path $Root 'lib\discretion.ps1') -Raw)
Verifier ($src -notmatch 'SetForegroundWindow|SetFocus|AppActivate|\.Activate\(|BringWindowToTop|SwitchToThisWindow') 'aucun appel qui vole le focus (SetForegroundWindow, AppActivate...) dans le mode jeu'

Write-Host '2) Heures (activation par défaut à certaines heures)'
$h1 = @([pscustomobject]@{ de = '20:00'; a = '23:30' })
Verifier ((Test-DansHeuresJeu ([datetime]'2026-10-14 21:00') $h1) -and -not (Test-DansHeuresJeu ([datetime]'2026-10-14 23:30') $h1) -and -not (Test-DansHeuresJeu ([datetime]'2026-10-14 19:59') $h1)) '20:00-23:30 : 21:00 oui, 23:30 non, 19:59 non'
$h2 = @([pscustomobject]@{ de = '22:00'; a = '02:00' })
Verifier ((Test-DansHeuresJeu ([datetime]'2026-10-14 23:00') $h2) -and (Test-DansHeuresJeu ([datetime]'2026-10-15 01:00') $h2) -and -not (Test-DansHeuresJeu ([datetime]'2026-10-15 03:00') $h2)) 'plage qui passe minuit (22:00-02:00)'
Verifier (-not (Test-DansHeuresJeu ([datetime]'2026-10-14 21:00') @())) 'aucune plage (défaut) : jamais d''activation horaire'
Verifier (@((Get-ConfigJeu).heures).Count -eq 0) 'config.json par défaut : heures vides'

Write-Host '3) Entrée et sortie automatiques (premier plan simulé, deux relevés consécutifs)'
$script:ModeJeu = $false; $script:ModeJeuManuel = $false; $script:JeuIgnorer = $false; $script:JeuVu = 0; $script:JeuAbsent = 0
$script:PP = $null
function Get-PremierPlan { $script:PP }
function Tick { $script:ProchainTestJeu = [datetime]::MinValue; Update-ModeJeu }
$script:PP = PP 'RobloxPlayerBeta' 'Roblox'
Tick; Verifier (-not $script:ModeJeu) 'un premier relevé ne suffit pas (évite un faux déclenchement)'
Tick; Verifier ($script:ModeJeu -and $script:ModeJeuSource -match 'jeu') 'au 2e relevé : MODE JEU activé'
Verifier ($script:Musiques -ge 1) 'la musique est coupée à l''entrée'
Write-Host '   — pendant le mode jeu —'
$avant = $script:Lectures; $script:ContexteVoix = 'reponse'
Parler 'Une réponse quelconque'
Verifier ($script:Lectures -eq $avant) 'Jarvis ne dit RIEN (même dans un contexte de réponse)'
$script:ContexteVoix = 'alerte'; Parler 'Alerte'; $script:ContexteVoix = 'briefing'; Parler 'Briefing'; $script:ContexteVoix = 'spontane'
Verifier ($script:Lectures -eq $avant) 'ni alerte, ni briefing'
$script:DernierSon = $null; Invoke-Son 'actif'; Invoke-Son 'sourdine'
Verifier ($null -eq $script:DernierSon) 'aucun petit son'
$script:Lecteurs = 0; Start-MusiqueDemarrage; $Config.musique_ambiance = $true; Start-Ambiance; $Config.musique_ambiance = $false
Verifier ($script:Lecteurs -eq 0) 'aucune musique (démarrage ni ambiance)'
# Alerte grave et rappel retenus, le reste non
$script:Retenu.Clear()
function Find-ProcessusSuspects { @([pscustomobject]@{ nom = 'svchost.exe'; pid = 4001; chemin = 'C:\Users\Liam\AppData\Local\Faux\svchost.exe'; raison = 'imite un processus Windows hors de System32'; signature = 'NON SIGNÉ' },
    [pscustomobject]@{ nom = 'outil.exe'; pid = 4002; chemin = (Join-Path $env:USERPROFILE 'Downloads\outil.exe'); raison = 'exécutable non signé dans un dossier à risque'; signature = 'NON SIGNÉ' }) }
$script:Entrees.Clear(); Invoke-ScanMenaces; Invoke-ScanMenaces
Verifier ($script:Entrees.Count -eq 0) 'aucune alerte n''est envoyée à la voix'
Verifier (@($script:Retenu | Where-Object { $_.type -eq 'alerte' }).Count -eq 1) 'l''alerte GRAVE est gardée en silence, une seule fois (la non grave est seulement dans le panneau)'
Verifier (@(Get-AlertesPanneau 6).Count -eq 2) 'les deux alertes sont dans le panneau'
$script:RappelsFaux = @([pscustomobject]@{ quand = (Get-Date).AddMinutes(-1).ToString('yyyy-MM-dd HH:mm'); texte = 'appeler le comptable'; fait = $false })
$script:ProchainRappel = [datetime]::MinValue; Invoke-Rappels
Verifier (@($script:Retenu | Where-Object { $_.type -eq 'rappel' }).Count -eq 1 -and $script:Lectures -eq $avant) 'un rappel arrivé à échéance est retenu, pas dit'
Parler 'Message retenu'
Verifier (@($script:Retenu | Where-Object { $_.type -eq 'parole' }).Count -ge 1) 'ce que Jarvis aurait dit est compté'
$d = Get-DonneesTableau
Verifier ($d.mode_jeu -eq $true) 'le tableau de bord sait que le mode jeu est actif (fenêtre masquée)'
Write-Host '   — fin de partie —'
$script:PP = PP 'explorer' '' $false 'Shell_TrayWnd'; $script:Dits = @(); $script:Conv = @()
function Parler([string]$Texte, $Langue) { $script:Dits += $Texte }
Tick; Verifier ($script:ModeJeu) 'un seul relevé « hors jeu » ne suffit pas'
Tick; Verifier (-not $script:ModeJeu) 'au 2e relevé : mode jeu terminé'
Verifier ($script:Dits.Count -eq 0) 'sortie AUTOMATIQUE : le résumé n''est pas dit à voix haute'
Verifier (($script:Conv -join ' ') -match 'Pendant votre partie' -and ($script:Conv -join ' ') -match 'svchost' -and ($script:Conv -join ' ') -match 'comptable') 'il est écrit au tableau : alerte grave et rappel'
Verifier ($script:DernierResumeJeu -notmatch 'outil\.exe') 'le résumé ne contient que ce qui est grave ou attendu (pas l''alerte non grave)'
Verifier ($script:Retenu.Count -eq 0) 'la liste des éléments retenus est vidée'

Write-Host '4) Commandes : « mode jeu », « mode jeu off », raccourci Ctrl+Alt+G'
foreach ($o in 'mode jeu', 'active le mode jeu', 'ne pas déranger', 'je vais jouer', 'passe en mode jeu') { $p = Get-PlanRapide $o; Verifier ($p -and $p.actions[0].type -eq 'mode_jeu' -and $p.actions[0].etat -eq 'on') "« $o » -> mode jeu ON (chemin rapide)" }
foreach ($o in 'mode jeu off', 'désactive le mode jeu', 'arrête le mode jeu', 'fin du mode jeu', "j'ai fini de jouer", 'quitte le mode jeu') { $p = Get-PlanRapide $o; Verifier ($p -and $p.actions[0].type -eq 'mode_jeu' -and $p.actions[0].etat -eq 'off') "« $o » -> mode jeu OFF (chemin rapide)" }
Verifier ((Get-Niveau ([pscustomobject]@{ type = 'mode_jeu'; etat = 'on' })).niveau -eq 1) 'niveau de permission 1 (aucun risque)'
$script:ModeJeu = $false; $script:Dits = @()
Invoke-Ordre 'mode jeu'
Verifier ($script:ModeJeu -and $script:Dits.Count -eq 0) 'ordre vocal « mode jeu » : activé, et Jarvis se tait'
Verifier ($script:ModeJeuManuel) 'activation manuelle : ne s''arrête pas toute seule'
$script:PP = PP 'explorer' '' $false 'Shell_TrayWnd'; Tick; Tick; Tick
Verifier ($script:ModeJeu) 'même sans jeu au premier plan, le mode manuel reste actif'
$script:Retenu.Add(@{ type = 'alerte'; texte = 'machin.exe'; heure = '21:10'; grave = $true })
Invoke-Ordre 'mode jeu off'
Verifier (-not $script:ModeJeu -and $script:Dits.Count -eq 1 -and $script:Dits[0] -match 'machin\.exe') 'ordre « mode jeu off » : Jarvis résume à voix haute ce qu''il a retenu'
Invoke-Ordre 'mode jeu off'; Verifier ($script:Dits[-1] -match 'pas actif') 'mode jeu off hors mode jeu : le dit simplement'
$script:Dits = @(); $script:Retenu.Clear()
Verifier ((Get-ResumeJeu) -eq 'Rien à signaler pendant votre partie, monsieur.') 'rien retenu : « Rien à signaler », jamais de remplissage inventé'
$k = Convert-Raccourci 'Ctrl+Alt+G'
Verifier ($k.ok -and $k.mods -eq 3 -and $script:ClesParDefaut.jeu -eq 'Ctrl+Alt+G') 'raccourci Ctrl+Alt+G valide (jamais Ctrl + / −)'
$script:ClesDefs[7] = @{ action = 'jeu'; libelle = 'Ctrl+Alt+G' }
Invoke-Raccourci 7; Verifier ($script:ModeJeu) 'Ctrl+Alt+G : mode jeu activé'
Invoke-Raccourci 7; Verifier (-not $script:ModeJeu) 'Ctrl+Alt+G de nouveau : mode jeu terminé'

Write-Host '5) Sortie manuelle pendant un jeu, et heures'
$script:PP = PP 'steam'; $script:JeuIgnorer = $false
Tick; Tick; Verifier ($script:ModeJeu) 'jeu détecté : mode jeu'
Set-ModeJeu $false 'test' | Out-Null
Verifier (-not $script:ModeJeu) '« mode jeu off » pendant que le jeu tourne : sort'
Tick; Tick; Tick; Verifier (-not $script:ModeJeu) '... et ne se réactive pas tout seul tant que le jeu est au premier plan'
$script:PP = PP 'explorer' '' $false 'Shell_TrayWnd'; Tick; Verifier (-not $script:JeuIgnorer) 'le jeu est fermé : la détection automatique est de nouveau armée'
$script:PP = PP 'steam'; Tick; Tick; Verifier ($script:ModeJeu) '... un nouveau jeu redéclenche le mode'
[void](Exit-ModeJeu 'test'); $script:PP = PP 'explorer' '' $false 'Shell_TrayWnd'; Tick; Tick
$Config.mode_jeu | Add-Member -NotePropertyName heures -NotePropertyValue @([pscustomobject]@{ de = '00:00'; a = '23:59' }) -Force
$script:JeuIgnorer = $false; Tick
Verifier ($script:ModeJeu -and $script:ModeJeuSource -eq 'horaire') 'plage horaire en cours : mode jeu activé par défaut (source « horaire »)'
[void](Set-ModeJeu $false 'test'); Tick; Tick
Verifier (-not $script:ModeJeu) 'je le désactive à la main pendant la plage : il reste désactivé'
$Config.mode_jeu.heures = @(); Tick; Verifier (-not $script:JeuIgnorer) 'la plage est finie : la détection est de nouveau armée'

Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
if ($echecs) { Write-Host "`nÉCHEC : $echecs vérification(s) en échec." -ForegroundColor Red; exit 1 }
Write-Host "`nRÉUSSI"; exit 0
