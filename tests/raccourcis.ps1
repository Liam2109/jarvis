# Test des raccourcis et de la SOURDINE TOTALE — 100 % SIMULÉ : aucune vraie touche, aucun raccourci système, aucune fenêtre, aucun son, aucun micro.
# Les raccourcis arrivent par la file du faux objet de raccourcis ; l'écoute, la voix et les sons sont des bouchons ; l'état est écrit dans %TEMP%.
# Code de sortie 0 = réussi.
$ErrorActionPreference = 'Stop'
$env:JARVIS_TEST = '1'      # TEST SILENCIEUX : aucun son, aucune fenêtre, aucun micro, aucune touche, aucune action réelle
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $Root 'lib\journal.ps1'); Import-JarvisEnv
$Config = Get-Content (Get-ConfigPath) -Raw -Encoding UTF8 | ConvertFrom-Json
$Config.visage_port = 47633; $Config.mode_affichage = 'discret'
# Touches par défaut explicites : le test ne dépend pas de ce que contient la config
$Config.raccourcis = [pscustomobject]@{ activer = 'Alt+Add'; desactiver = 'Alt+Subtract'; basculer = 'ScrollLock'; tableau = 'Ctrl+Alt+J'; jeu = 'Ctrl+Alt+G'; touche_seule = $false }
foreach ($l in 'voix', 'business', 'permissions', 'actions', 'coffre', 'entrees', 'ecrans', 'tableau', 'visage', 'sons', 'raccourcis', 'cerveau', 'cerveau-local', 'veille', 'memoire', 'rapide', 'discretion', 'modejeu', 'boucle') { . (Join-Path $Root "lib\$l.ps1") }
Remove-Item $script:StopFlag, $script:ParleFlag -ErrorAction SilentlyContinue
$echecs = 0
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }

# --- Tout est détourné vers %TEMP% ou remplacé par un bouchon ---
$tmp = Join-Path $env:TEMP "jarvis-test-sourdine-$([guid]::NewGuid().ToString('N'))"; New-Item -ItemType Directory $tmp | Out-Null
$script:EtatFichier2 = Join-Path $tmp 'etat-jarvis.json'; $script:SourdineFlag = Join-Path $tmp 'sourdine.flag'
function Get-FichierAlertes { Join-Path $tmp 'alertes.json' }
function Get-FichierBriefingVocal { Join-Path $tmp 'briefing-vocal.txt' }
$script:AlertesCache = $null
# faux dossier de sons (jingle généré + fausse ambiance) : aucun fichier réel n'est lu ni écrit
$script:SonsDossier = Join-Path $tmp 'sounds'; New-Item -ItemType Directory $script:SonsDossier | Out-Null; [IO.File]::WriteAllBytes((Join-Path $script:SonsDossier 'ambiance.mp3'), [byte[]](1..64))
$script:MicOuvert = $false; $script:OuvertureMic = 0; $script:FermetureMic = 0
function Start-Ecoute { $script:MicOuvert = $true; $script:OuvertureMic++ }
function Stop-Ecoute { $script:MicOuvert = $false; $script:FermetureMic++ }
function Start-PrechauffageTts { }
$script:Dits = @(); $script:OrdresRecus = @(); $script:OrdresSourdine = @(); $script:Visages = 0
function Parler([string]$Texte, $Langue) { if ($script:Actif -ne $false -and $script:ModeJeu -ne $true -and (Test-VoixPermise).ok) { $script:Dits += $Texte } }
function Invoke-Ordre([string]$o) { $script:OrdresRecus += $o }
function Invoke-OrdreSourdine([string]$o) { $script:OrdresSourdine += $o }
function Switch-Visage { $script:Visages++ }
function New-CleGlobale {
    $o = [pscustomobject]@{ File = New-Object 'System.Collections.Concurrent.ConcurrentQueue[int]'; Enreg = @() }
    $o | Add-Member ScriptMethod Enregistrer { param($id, $mod, $vk) $this.Enreg += "$id/$mod/$vk"; 0 }
    $o | Add-Member ScriptMethod Liberer { }
    $o
}
function Touche([int]$id) { $script:Cles.File.Enqueue($id); Invoke-PumpRaccourcis }      # « appuie » sur le raccourci d'identifiant $id (simulation)

Write-Host '1) Analyse des raccourcis'
$p = Convert-Raccourci 'Alt+Add';            Verifier ($p.ok -and $p.mods -eq 1 -and $p.vk -eq 0x6B) 'Alt+Add = Alt + « + » du pavé numérique'
$p = Convert-Raccourci 'alt+subtract';       Verifier ($p.ok -and $p.mods -eq 1 -and $p.vk -eq 0x6D) 'minuscules acceptées : Alt + « − » du pavé numérique'
$p = Convert-Raccourci 'Alt+PaveMoins';      Verifier ($p.ok -and $p.vk -eq 0x6D) 'alias PaveMoins -> Subtract'
$p = Convert-Raccourci 'Alt++';              Verifier ($p.ok -and $p.mods -eq 1 -and $p.vk -eq 0x6B) '« Alt++ » = Alt + le caractère +'
$p = Convert-Raccourci 'ScrollLock';         Verifier ($p.ok -and $p.mods -eq 0 -and $p.vk -eq 0x91) 'ScrollLock seul est autorisé (Verr. défil.)'
$p = Convert-Raccourci 'Ctrl+Alt+J';         Verifier ($p.ok -and $p.mods -eq 3 -and $p.vk -eq 0x4A) 'Ctrl+Alt+J'
$p = Convert-Raccourci 'Ctrl+Alt+G';         Verifier ($p.ok -and $p.mods -eq 3 -and $p.vk -eq 0x47) 'Ctrl+Alt+G (mode jeu)'
$p = Convert-Raccourci 'Ctrl+Add';           Verifier (-not $p.ok -and $p.erreur -match 'zoom') 'Ctrl+« + » refusé (zoom du navigateur)'
$p = Convert-Raccourci 'Ctrl+Subtract';      Verifier (-not $p.ok -and $p.erreur -match 'zoom') 'Ctrl+« − » refusé (zoom du navigateur)'
$p = Convert-Raccourci 'Ctrl+Alt+Add';       Verifier (-not $p.ok) 'Ctrl+Alt+« + » refusé aussi (contient Ctrl)'
$p = Convert-Raccourci 'Ctrl+Oemplus';       Verifier (-not $p.ok) 'Ctrl+« + » du clavier principal refusé'
$p = Convert-Raccourci 'Ctrl+OemMinus';      Verifier (-not $p.ok) 'Ctrl+« - » du clavier principal refusé'
$p = Convert-Raccourci 'Add';                Verifier (-not $p.ok -and $p.erreur -match 'seule') '« + » seul refusé comme raccourci ordinaire'
$p = Convert-Raccourci 'J';                  Verifier (-not $p.ok) 'une lettre seule est refusée (elle casserait la frappe)'
$p = Convert-Raccourci 'Alt+Bidule';         Verifier (-not $p.ok -and $p.erreur -match 'inconnue') 'touche inconnue refusée'
$p = Convert-Raccourci '';                   Verifier (-not $p.ok) 'raccourci vide refusé'

Write-Host '2) Les 8 raccourcis attendus (enregistrement simulé)'
$Config | Add-Member -NotePropertyName etat_au_demarrage -NotePropertyValue '' -Force
[IO.File]::WriteAllText($script:EtatFichier2, '{"actif": true}')
$problemes = Initialize-Raccourcis
Verifier (@($problemes).Count -eq 0) ("aucun problème d'enregistrement" + $(if (@($problemes).Count) { ' : ' + ($problemes -join ' ; ') }))
Verifier ($script:RaccourcisRapport.Count -eq 8) "8 raccourcis : $($script:RaccourcisRapport -join ' ; ')"
foreach ($a in 'activer = Alt+Add', 'desactiver = Alt+Subtract', 'basculer = ScrollLock', 'tableau = Ctrl+Alt+J', 'jeu = Ctrl+Alt+G', 'musique_moins = Ctrl+Alt+Down', 'musique_plus = Ctrl+Alt+Up', 'musique_couper = Ctrl+Alt+M') { Verifier ($script:RaccourcisRapport -contains $a) "raccourci présent : $a" }
Verifier (-not ($script:RaccourcisRapport -match 'seul')) 'touche_seule désactivée : « + » et « − » seuls NON enregistrés'
Verifier ($script:Actif -eq $true) 'état mémorisé « actif » (etat_au_demarrage vide) : Jarvis démarre actif'
$id = @{}; foreach ($k in $script:ClesDefs.Keys) { $id[$script:ClesDefs[$k].action] = $k }

Write-Host '2b) Musique au clavier : Ctrl+Alt+Bas / Haut (-/+ 10 %) et Ctrl+Alt+M (couper / remettre), volume mémorisé hors config.json'
$script:MusiqueEtat = $null; Remove-Item (Get-FichierMemoire 'musique.json') -ErrorAction SilentlyContinue
$v0 = Get-VolumeBase
Touche $id['musique_moins']; Verifier ([math]::Abs((Get-VolumeBase) - ($v0 - 0.1)) -lt 0.001) ("Ctrl+Alt+Bas : {0:P0} -> {1:P0}" -f $v0, (Get-VolumeBase))
Touche $id['musique_plus']; Touche $id['musique_plus']; Verifier ([math]::Abs((Get-VolumeBase) - ($v0 + 0.1)) -lt 0.001) ("Ctrl+Alt+Haut deux fois : {0:P0}" -f (Get-VolumeBase))
Touche $id['musique_couper']; Verifier (Test-MusiqueCoupee) 'Ctrl+Alt+M : musique coupée'
Touche $id['musique_couper']; Verifier (-not (Test-MusiqueCoupee)) 'Ctrl+Alt+M à nouveau : musique remise'
$script:MusiqueEtat = $null; Verifier ([math]::Abs((Get-VolumeBase) - ($v0 + 0.1)) -lt 0.001) 'le volume choisi est relu depuis memoire\ (mémorisé)'
Remove-Item (Get-FichierMemoire 'musique.json') -ErrorAction SilentlyContinue; $script:MusiqueEtat = $null

Write-Host '3) Alt + « − » : SOURDINE TOTALE'
$script:Actif = $true; Remove-Item $script:SourdineFlag -ErrorAction SilentlyContinue
Start-Ecoute; $script:OuvertureMic = 0; $script:FermetureMic = 0
Start-MusiqueDemarrage; $Config.musique_ambiance = $true
if (-not (Test-Path (Join-Path $Root 'sounds\ambiance.mp3'))) { Write-Host '  (sounds\ambiance.mp3 absent : l''ambiance est vérifiée avec le faux lecteur)' -ForegroundColor DarkGray }
$script:Ambiance = New-Lecteur 'faux.mp3' 0.3
$script:Dits = @(); $script:Entrees.Clear()
Touche $id['desactiver']
Verifier ($script:Actif -eq $false) 'Alt + − : Jarvis est en sourdine'
Verifier ((Get-Content $script:EtatFichier2 -Raw) -match '"actif":\s*false') 'état mémorisé : actif = false'
Verifier (Test-Path $script:SourdineFlag) 'drapeau sourdine posé'
Verifier ($null -eq $script:Musique -and $null -eq $script:Ambiance) 'MUSIQUE coupée (démarrage et ambiance)'
Verifier ($script:MicOuvert -eq $false -and $script:FermetureMic -eq 1) 'MICRO libéré : le processus d''écoute est arrêté'
Verifier ($null -eq $script:Ecoute) 'plus aucun processus d''écoute : plus aucune détection du mot « Jarvis »'
$script:DernierSon = $null; Invoke-Son 'actif'; Invoke-Son 'sourdine'
Verifier ($null -eq $script:DernierSon) 'aucun bip, aucun carillon'
$script:Lecteurs = 0; Start-MusiqueDemarrage; Start-Ambiance
Verifier ($null -eq $script:Musique -and $null -eq $script:Ambiance) 'impossible de relancer une musique en sourdine'
$avant = $script:Dits.Count; Parler 'Phrase de test'; Verifier ($script:Dits.Count -eq $avant) 'aucune voix'
Verifier ((Start-CoffreDialogue) -match 'sourdine' -and $null -eq $script:CoffreProc) 'aucune popup : la fenêtre du coffre ne s''ouvre pas'
function Find-ProcessusSuspects { @([pscustomobject]@{ nom = 'svchost.exe'; pid = 4001; chemin = 'C:\Users\Liam\AppData\Local\Faux\svchost.exe'; raison = 'imite un processus Windows hors de System32'; signature = 'NON SIGNÉ' }) }
Invoke-ScanMenaces
Verifier ($script:Entrees.Count -eq 0) 'aucune alerte n''est dite, même grave'
Verifier (@(Get-AlertesPanneau 6).Count -eq 1 -and @(Get-AlertesPanneau 6)[0].grave) 'l''alerte grave reste dans le panneau et le journal, sans bruit'
Invoke-Entree @{ src = 'voix'; texte = 'ouvre chrome'; entendu = $false }
Verifier ($script:OrdresRecus.Count -eq 0) 'ordre vocal : IGNORÉ (aucun ordre exécuté)'
Invoke-Entree @{ src = 'clavier'; texte = 'ouvre chrome'; entendu = $false }
Verifier ($script:OrdresRecus.Count -eq 0 -and $script:OrdresSourdine.Count -eq 1) 'ordre écrit : réponse écrite seulement, AUCUNE action'
Invoke-Entree @{ src = 'systeme'; texte = '[menace]'; entendu = $false; menace = [pscustomobject]@{ nom = 'x.exe'; pid = 1; chemin = 'C:\x\x.exe'; signature = ''; raison = 'test' } }
Verifier ($script:Dits.Count -eq $avant -and $script:EntreesEnAttente.Count -eq 0) 'alerte système en sourdine : journalisée, ni dite ni mise en attente'
Touche $id['desactiver']; Verifier ($script:Actif -eq $false -and $script:FermetureMic -eq 1) 'Alt + − répété : reste en sourdine, sans rien casser'

Write-Host '4) Alt + « + » : réactivation'
$script:Dits = @(); $script:Entrees.Clear()
Touche $id['activer']
Verifier ($script:Actif -eq $true) 'Alt + + : Jarvis est actif'
Verifier ($script:MicOuvert -eq $true -and $script:OuvertureMic -eq 1) 'micro rouvert (écoute relancée)'
Verifier (-not (Test-Path $script:SourdineFlag)) 'drapeau sourdine retiré'
Verifier ($script:Dits.Count -eq 1 -and (@(Get-PhrasesReveil) + 'Bon après-midi, monsieur.' + 'Bonsoir, monsieur.') -contains $script:Dits[0] -and $script:Dits[0] -ne 'À vos ordres, monsieur.') 'une salutation variée est dite (plus « À vos ordres »)'
$script:DernierReveil = ''; $suite = @(1..40 | ForEach-Object { Get-PhraseReveil ([datetime]'2026-10-14 09:00') })
Verifier (-not (1..39 | Where-Object { $suite[$_] -eq $suite[$_ - 1] })) 'jamais la même salutation deux fois de suite'
Verifier (@($suite | Where-Object { $_ -match '^Bon(soir|.*après-midi)' }).Count -eq 0) 'matin : ni « Bonsoir » ni « Bon après-midi »'
$pm = @(1..40 | ForEach-Object { Get-PhraseReveil ([datetime]'2026-10-14 14:00') }); Verifier (($pm -contains 'Bon après-midi, monsieur.') -and -not ($pm -match '^Bonjour|^Bonsoir')) '12 h - 18 h : « Bon après-midi », pas de « Bonjour »'
$soir = @(1..40 | ForEach-Object { Get-PhraseReveil ([datetime]'2026-10-14 20:00') }); Verifier (($soir -contains 'Bonsoir, monsieur.') -and -not ($soir -match '^Bonjour|après-midi')) 'après 18 h : « Bonsoir », pas de « Bonjour »'
$sauve = $Config.phrases_reveil; $Config.phrases_reveil = @('Phrase A.', 'Phrase B.'); Verifier (((Get-PhrasesReveil) -join '|') -eq 'Phrase A.|Phrase B.') 'liste lue depuis config.json (phrases_reveil)'; $Config.phrases_reveil = $sauve
Verifier ((Get-PhrasesReveilCache) -contains 'Bonsoir, monsieur.' -and (Get-PhrasesReveilCache) -contains 'Vous revoilà, monsieur.') 'les salutations font partie du cache des phrases fixes'
Verifier ((Get-Content $script:EtatFichier2 -Raw) -match '"actif":\s*true') 'état mémorisé : actif = true'
$script:DernierSon = $null; Invoke-Son 'actif'; Verifier ($null -ne $script:DernierSon) 'les petits sons fonctionnent de nouveau'
Start-MusiqueDemarrage; Start-Ambiance; Verifier ($null -ne $script:Musique -and $null -ne $script:Ambiance) 'musique et ambiance peuvent repartir'
Stop-Musiques
Invoke-Entree @{ src = 'voix'; texte = 'ouvre chrome'; entendu = $false }
Verifier ($script:OrdresRecus.Count -eq 1) 'les ordres sont de nouveau exécutés'

Write-Host '5) Verr. défil. (bascule) et autres raccourcis'
$script:Dits = @()
Touche $id['basculer']; Verifier ($script:Actif -eq $false -and $script:MicOuvert -eq $false) 'Verr. défil. : actif -> sourdine (micro fermé)'
Touche $id['basculer']; Verifier ($script:Actif -eq $true -and $script:MicOuvert -eq $true) 'Verr. défil. : sourdine -> actif (micro rouvert)'
Touche $id['tableau']; Verifier ($script:Visages -eq 1) 'Ctrl+Alt+J : affiche / cache le tableau de bord'
Touche $id['jeu']; Verifier ($script:ModeJeu -eq $true) 'Ctrl+Alt+G : mode jeu activé'
Touche $id['jeu']; Verifier ($script:ModeJeu -eq $false) 'Ctrl+Alt+G de nouveau : mode jeu terminé'

Write-Host '6) Démarrage : etat_au_demarrage'
Stop-Raccourcis
foreach ($cas in @(@('sourdine', '{"actif": true}', $false), @('actif', '{"actif": false}', $true), @('', '{"actif": false}', $false), @('', '{"actif": true}', $true))) {
    $Config.etat_au_demarrage = $cas[0]; [IO.File]::WriteAllText($script:EtatFichier2, $cas[1]); $script:Actif = $true
    [void](Initialize-Raccourcis); Stop-Raccourcis
    Verifier ($script:Actif -eq $cas[2]) ("etat_au_demarrage = « $($cas[0]) » avec état mémorisé $($cas[1]) -> " + $(if ($cas[2]) { 'actif' } else { 'sourdine (muet, sourd, sans son)' }))
}
$Config.etat_au_demarrage = 'sourdine'; [void](Initialize-Raccourcis)
Verifier ($script:Actif -eq $false -and (Test-Path $script:SourdineFlag)) 'démarrage en sourdine : drapeau posé avant toute écoute'
Stop-Raccourcis

Write-Host '7) Option « touche seule » (désactivée par défaut) — simulation'
$Config.raccourcis.touche_seule = $true; $Config.etat_au_demarrage = 'actif'; [IO.File]::WriteAllText($script:EtatFichier2, '{"actif": true}')
$pb = Initialize-Raccourcis
Verifier ($script:RaccourcisRapport.Count -eq 10 -and ($script:RaccourcisRapport -match 'seul').Count -eq 2 -and $script:AvertissementToucheSeule) 'touche_seule = true : « + » et « − » seuls enregistrés (10 au total) et AVERTISSEMENT prévu'
$idSeul = @{}; foreach ($k in $script:ClesDefs.Keys) { if ($script:ClesDefs[$k].libelle -match 'seul|pavé') { $idSeul[$script:ClesDefs[$k].action] = $k } }
$script:Actif = $true; Touche $idSeul['desactiver']; Verifier ($script:Actif -eq $false) '« − » seul : sourdine'
Touche $idSeul['activer']; Verifier ($script:Actif -eq $true) '« + » seul : activation'
Stop-Raccourcis

Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
if ($echecs) { Write-Host "`nÉCHEC : $echecs vérification(s) en échec." -ForegroundColor Red; exit 1 }
Write-Host "`nRÉUSSI"; exit 0
