# Test SILENCIEUX de la veille avec réveil (PC principal) : détecteur de claquements et phrase (voix\reveil.py, niveaux SIMULÉS), états voulus, réglages, réveil / mise en veille,
# calibrage (sortie simulée), config.local.json (Discord désactivé), installer-bureau.ps1 (fonctions + SIMULATION : aucune tâche créée), aucun micro, aucun son, aucune fenêtre.
# Code de sortie 0 = réussi.
$ErrorActionPreference = 'Stop'
$env:JARVIS_TEST = '1'
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $Root 'lib\journal.ps1')
$TR = Join-Path $env:TEMP ('jarvis-test-' + [guid]::NewGuid().ToString('N').Substring(0, 8)); New-Item -ItemType Directory $TR, "$TR\memoire", "$TR\logs" | Out-Null; $script:JarvisRoot = $TR
'# To-do' | Set-Content "$TR\memoire\todo.md" -Encoding UTF8; '# N' | Set-Content "$TR\memoire\notes.md" -Encoding UTF8; '# R' | Set-Content "$TR\memoire\resume.md" -Encoding UTF8
$Config = Get-Content $(if ($env:JARVIS_CONFIG -and (Test-Path $env:JARVIS_CONFIG)) { $env:JARVIS_CONFIG } else { Join-Path $Root 'config.json' }) -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($l in 'voix', 'business', 'permissions', 'actions', 'coffre', 'entrees', 'ecrans', 'tableau', 'visage', 'sons', 'raccourcis', 'cerveau', 'cerveau-local', 'veille', 'memoire', 'rapide', 'discretion', 'modejeu', 'competences', 'marche', 'priorite', 'comprehension', 'routeur', 'pc', 'bureau', 'salle-marche', 'matin', 'discord', 'veille-reveil') { . (Join-Path $Root "lib\$l.ps1") }
$script:JarvisRoot = $TR
$echecs = 0
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }
function Fixer([string]$cle, $val) { if ($Config.PSObject.Properties[$cle]) { $Config.$cle = $val } else { $Config | Add-Member -NotePropertyName $cle -NotePropertyValue $val } }
function Effacer([string]$cle) { if ($Config.PSObject.Properties[$cle]) { $Config.PSObject.Properties.Remove($cle) } }
$vraie = Get-Content (Join-Path $Root 'config.json') -Raw -Encoding UTF8 | ConvertFrom-Json

Write-Host '1) Détecteur de claquements et phrase de réveil (voix\reveil.py, niveaux simulés)'
$sortiePy = (& python -I (Join-Path $PSScriptRoot 'reveil.py') 2>&1 | Out-String); $codePy = $LASTEXITCODE
$nbPy = ([regex]::Matches($sortiePy, '(?m)^\s+OK ')).Count
Verifier ($codePy -eq 0 -and $nbPy -ge 50) "tests\reveil.py : tout est vert ($nbPy vérifications)"
if ($codePy -ne 0) { ($sortiePy -split "`n" | Where-Object { $_ -match 'ECHEC|ÉCHEC|Error|Traceback' }) | Select-Object -First 8 | ForEach-Object { Write-Host $_ } }

Write-Host '2) config.json : tout est désactivé par défaut ; ce PC l''active dans config.local.json'
Verifier ($vraie.bureau_veille -eq $false -and $vraie.veille_reveil -eq $false) 'config.json : bureau_veille et veille_reveil sont FAUX (le serveur et les autres PC ne sont pas touchés)'
Verifier ($vraie.claquement_seuil -eq 72 -and $vraie.claquement_ecart_min_ms -eq 200 -and $vraie.claquement_ecart_max_ms -eq 800 -and $vraie.claquement_duree_max_ms -eq 120 -and $vraie.claquement_actif -eq $true -and $vraie.reveil_phrase -eq $true) 'config.json : seuil 72, écart de 0,2 à 0,8 s, claquement de 120 ms au plus, phrase et claquement actifs'
$loc = Join-Path $Root 'config.local.json'
if (Test-Path $loc) {
    $eff = Get-Content (Join-Path $Root 'config.json') -Raw -Encoding UTF8 | ConvertFrom-Json; Merge-ConfigObjet $eff (Get-Content $loc -Raw -Encoding UTF8 | ConvertFrom-Json)
    Verifier ($eff.discord_actif -eq $false) 'config.local.json de ce PC : Discord DÉSACTIVÉ (le bot reste sur le serveur)'
    Verifier ($eff.bureau_veille -eq $true -and $eff.veille_reveil -eq $true -and "$($eff.etat_au_demarrage)" -eq 'sourdine') 'config.local.json de ce PC : veille + réveil actifs, démarrage en sourdine'
    Verifier ("$($eff.ollama.keep_alive)" -eq '24h' -and $eff.ollama.modele -eq $vraie.ollama.modele) 'config.local.json de ce PC : Ollama gardé chaud 24 h, modèle de config.json conservé'
} else { Write-Host '        (pas de config.local.json ici : contrôle de ce PC sauté)' }
$gi = @(Get-Content (Join-Path $Root '.gitignore') -Encoding UTF8 | ForEach-Object { $_.Trim() }); Verifier ($gi -contains 'config.local.json') 'config.local.json est ignoré par git (jamais poussé vers le serveur)'

Write-Host '3) États voulus de l''écoute de veille'
Fixer 'voix_actif' 'oui'; Fixer 'veille_reveil' $true; Fixer 'bureau_veille' $true; $script:ModeJeu = $false      # voix_actif = oui : ces tests décrivent le comportement avec la voix (désactivée par défaut, voir testsoix-actif.ps1)
$script:Actif = $false; Verifier ((Get-EtatVeilleVoulu) -eq 'ecoute') 'en veille, réveil activé : l''écoute légère tourne'
$script:Actif = $true; Verifier ((Get-EtatVeilleVoulu) -eq 'arret') 'Jarvis réveillé : l''écoute de veille est arrêtée (le micro est à l''écoute normale)'
$script:Actif = $false; $script:ModeJeu = $true; Verifier ((Get-EtatVeilleVoulu) -eq 'arret') 'mode jeu : jamais d''écoute de veille'
$script:ModeJeu = $false; Fixer 'veille_reveil' $false; Verifier ((Get-EtatVeilleVoulu) -eq 'arret') 'veille_reveil = false : aucune écoute de veille (comportement d''avant)'
Fixer 'veille_reveil' $true; Fixer 'reveil_phrase' $false; Fixer 'claquement_actif' $false; Verifier ((Get-EtatVeilleVoulu) -eq 'arret') 'phrase ET claquement désactivés : rien à écouter'
Fixer 'claquement_actif' $true; Verifier ((Get-EtatVeilleVoulu) -eq 'ecoute' -and ((Get-ArgsVeille 'x.py') -match '--sans-voix') -and ((Get-ArgsVeille 'x.py') -notmatch '--sans-claquement')) 'phrase désactivée : seuls les claquements écoutent (--sans-voix)'
Fixer 'reveil_phrase' $true; Fixer 'claquement_actif' $false; Verifier ((Get-ArgsVeille 'x.py') -match '--sans-claquement' -and (Get-ArgsVeille 'x.py') -notmatch '--sans-voix') 'claquement désactivé : seule la phrase écoute (--sans-claquement)'
Fixer 'claquement_actif' $true
Fixer 'mode_serveur' $true; Verifier ((Get-EtatVeilleVoulu) -eq 'arret' -and -not (Test-VeilleBureau)) 'mode serveur : jamais de veille avec réveil (le serveur n''a ni HUD ni micro obligatoire)'
Effacer 'mode_serveur'; Fixer 'bureau_veille' $false; Verifier (-not (Test-VeilleBureau)) 'bureau_veille = false : démarrage normal'
Fixer 'bureau_veille' $true; Verifier (Test-VeilleBureau) 'bureau_veille = true : démarrage en veille silencieuse'
$a = Get-ArgsVeille 'C:\x\reveil.py'
Verifier ($a -match '^-I -u "C:\\x\\reveil\.py" --seuil 72 --claque-duree-max 120 --ecart-min 200 --ecart-max 800') 'arguments du processus : seuil, durée maximale, écarts pris dans config.json'
Verifier ($vraie.reveil_phrase_stricte -eq 'oui' -and $a -match '--stricte oui --confiance 0\.55') 'réveil strict : reveil_phrase_stricte = "oui" par défaut, transmis au processus de veille'
Fixer 'reveil_phrase_stricte' 'non'; Verifier ((Get-ArgsVeille 'x.py') -match '--stricte non') 'reveil_phrase_stricte = "non" : ancien comportement'; Effacer 'reveil_phrase_stricte'
Fixer 'claquement_seuil' '81,5'; Fixer 'claquement_ecart_min_ms' 50; Fixer 'claquement_ecart_max_ms' 99999
$r = Get-ReglagesVeille; Verifier ($r.seuil -eq 82 -and $r.ecart_min -eq 100 -and $r.ecart_max -eq 1500) 'réglages bornés (seuil 81,5 -> 82 ; écarts ramenés à 100 ms et 1500 ms)'
Fixer 'claquement_seuil' 'abc'; Verifier ((Get-ReglagesVeille).seuil -eq 72) 'seuil illisible : valeur par défaut 72'
Fixer 'claquement_seuil' 72; Fixer 'claquement_ecart_min_ms' 200; Fixer 'claquement_ecart_max_ms' 800

Write-Host '4) Réveil, « Je vous écoute. » et mise en veille'
$script:Etats = @()
function Start-Ecoute { $script:Etats += 'start' }; function Stop-Ecoute { $script:Etats += 'stop' }; function Release-GpuModeles { $script:Etats += 'liberer' }
function Start-OllamaReveil { $script:Etats += 'ollama' }
$script:Dits = New-Object System.Collections.Generic.List[string]
function Parler { param([string]$t) $script:Dits.Add($t) }
$script:EtatFichier2 = Join-Path $TR 'etat.json'; $script:SourdineFlag = Join-Path $TR 'sourdine.flag'; $script:Actif = $true
Set-Actif $false 'test'
Verifier (($script:Etats -join ',') -notmatch 'liberer') 'mise en veille du PC principal : Ollama reste chaud (le modèle n''est pas déchargé du GPU)'
Verifier ($script:Actif -eq $false -and (Test-Path $script:SourdineFlag)) 'Jarvis est en sourdine (rien ne parle, rien n''est exécuté)'
Fixer 'bureau_veille' $false; $script:Actif = $true; $script:Etats = @(); Set-Actif $false 'test'
Verifier (($script:Etats -join ',') -match 'liberer') 'sans bureau_veille : la sourdine libère toujours le GPU (comportement d''avant)'
Fixer 'bureau_veille' $true
# réveil par le double claquement : processus simulé qui a déjà imprimé REVEIL:claque
$fauxProc = [pscustomobject]@{ HasExited = $false; ExitCode = 0 }; $fauxProc | Add-Member -MemberType ScriptMethod -Name Kill -Value { $this.HasExited = $true }
$script:Actif = $false; $script:Etats = @(); $script:Dits.Clear()
$script:VeilleProc = $fauxProc; $script:VeilleTache = [Threading.Tasks.Task]::FromResult('REVEIL:claque')
Invoke-PumpVeille
Verifier ($script:Actif -eq $true -and $null -eq $script:VeilleProc) 'double claquement : Jarvis se réveille et l''écoute de veille est fermée'
Verifier (($script:Etats -join ',') -match 'start') 'réveillé : l''écoute normale (micro) démarre'
Verifier ($script:Dits.Count -eq 1 -and $script:Dits[0] -eq 'Je vous écoute.') "réveillé par les mains : réponse brève « $($script:Dits -join ' ') »"
$fauxProc2 = [pscustomobject]@{ HasExited = $false; ExitCode = 0 }; $fauxProc2 | Add-Member -MemberType ScriptMethod -Name Kill -Value { $this.HasExited = $true }
Set-Actif $false 'test'; $script:Etats = @(); $script:Dits.Clear()
$script:VeilleProc = $fauxProc2; $script:VeilleTache = [Threading.Tasks.Task]::FromResult('REVEIL:phrase')
Invoke-PumpVeille
Verifier ($script:Actif -eq $true -and $script:Dits.Count -eq 1 -and $script:Dits[0] -eq 'Je vous écoute.') 'phrase « réveille-toi Jarvis » : réveil et « Je vous écoute. »'
$fauxOut = [pscustomobject]@{}; $fauxOut | Add-Member -MemberType ScriptMethod -Name ReadLineAsync -Value { [Threading.Tasks.Task]::FromResult([string]'suite') }; $fauxProc3 = [pscustomobject]@{ HasExited = $false; ExitCode = 0; StandardOutput = $fauxOut }; $fauxProc3 | Add-Member -MemberType ScriptMethod -Name Kill -Value { $this.HasExited = $true }
Set-Actif $false 'test'; $script:Etats = @()
$script:VeilleProc = $fauxProc3; $script:VeilleTache = [Threading.Tasks.Task]::FromResult('PRET:veille')
Invoke-PumpVeille
Verifier ($script:Actif -eq $false -and $script:VeilleProc -eq $fauxProc3 -and $script:VeilleTache -ne $null) 'sortie « PRET:veille » : aucun réveil, l''écoute continue'
$script:VeilleTache = [Threading.Tasks.Task]::FromResult('REVEIL:autre'); Invoke-PumpVeille
Verifier ($script:Actif -eq $false) 'une ligne inconnue ne réveille pas'
$script:VeilleProc = $null; $script:VeilleTache = $null
$script:Actif = $true; $fauxProc4 = [pscustomobject]@{ HasExited = $false; ExitCode = 0 }; $fauxProc4 | Add-Member -MemberType ScriptMethod -Name Kill -Value { $this.HasExited = $true }
$script:VeilleProc = $fauxProc4; $script:VeilleTache = [Threading.Tasks.Task]::FromResult('REVEIL:claque'); Invoke-PumpVeille
Verifier ($script:Actif -eq $true -and $null -eq $script:VeilleProc) 'réveil alors que Jarvis est déjà réveillé : ignoré proprement'
$ent = Get-Content (Join-Path $Root 'lib\entrees.ps1') -Raw -Encoding UTF8
Verifier ($ent -match 'Invoke-PumpVeille') 'la boucle principale (Invoke-Pump) lit l''écoute de veille'
Write-Host '   « Jarvis, mets-toi en veille »'
foreach ($o in 'mets-toi en veille', 'Jarvis, mets-toi en veille', 'passe en veille', 'va en veille', 'mets toi en veille Jarvis', 'veille Jarvis') {
    $pl = Get-PlanRapide $o; Verifier ($pl -and $pl.actions[0].type -eq 'sourdine') "« $o » -> mise en veille (sourdine)"
}
foreach ($o in 'mets-moi une alarme', 'réveille-moi à sept heures', 'ouvre chrome') { $pl = Get-PlanRapide $o; Verifier (-not ($pl -and $pl.actions.Count -and $pl.actions[0].type -eq 'sourdine')) "« $o » ne met PAS en veille" }
$pl = Get-PlanRapide 'mets-toi en veille'; Verifier ($pl.regle -eq 'mise_en_veille' -and $pl.dit -match 'veille') 'la réponse annonce la veille'

Write-Host '5) Calibrage des claquements (mesure simulée, aucun micro)'
$c = ConvertFrom-CalibrageClaquements 'bruit parasite
CALIBRAGE:{"ambiant_moyen": 28.5, "ambiant_p99": 41, "ambiant_max": 50, "seuil": 59, "blocs": 250}
'
Verifier ($c.ok -and $c.seuil -eq 59 -and $c.ambiant_p99 -eq 41) 'sortie de la mesure lue : seuil 59'
Verifier (-not (ConvertFrom-CalibrageClaquements '').ok -and -not (ConvertFrom-CalibrageClaquements 'CALIBRAGE:{pas du json}').ok) 'sortie vide ou illisible : refusée'
Verifier (-not (ConvertFrom-CalibrageClaquements 'CALIBRAGE:{"seuil": 120, "blocs": 250}').ok -and -not (ConvertFrom-CalibrageClaquements 'CALIBRAGE:{"seuil": 10, "blocs": 250}').ok) 'seuil hors bornes (30 à 98) : refusé'
Verifier (-not (ConvertFrom-CalibrageClaquements 'CALIBRAGE:{"seuil": 60, "blocs": 10}').ok) 'mesure trop courte (moins de 50 blocs) : refusée'
$script:Actif = $false; $script:SortieCalibrageTest = 'CALIBRAGE:{"ambiant_moyen": 33.1, "ambiant_p99": 52, "ambiant_max": 61, "seuil": 70, "blocs": 250}'
$cfgAvant = if (Test-Path "$TR\config.local.json") { Get-Content "$TR\config.local.json" -Raw } else { '' }
$res = Invoke-CalibrageClaquements
Verifier ($res.ok -and $res.texte -match '70 sur 100') 'calibrage : le seuil trouvé est annoncé'
$cl = Get-Content "$TR\config.local.json" -Raw -Encoding UTF8 | ConvertFrom-Json
Verifier ($cl.claquement_seuil -eq 70 -and $Config.claquement_seuil -eq 70) 'calibrage : seuil écrit dans config.local.json (réglage de CE PC) et pris en compte aussitôt'
Verifier ((Get-Content (Join-Path $Root 'config.json') -Raw -Encoding UTF8 | ConvertFrom-Json).claquement_seuil -eq 72) 'config.json n''est JAMAIS modifié par le calibrage'
Save-ConfigLocale @{ autre = 'x' }; $cl = Get-Content "$TR\config.local.json" -Raw -Encoding UTF8 | ConvertFrom-Json
Verifier ($cl.claquement_seuil -eq 70 -and $cl.autre -eq 'x') 'config.local.json : les autres clés sont conservées'
$script:SortieCalibrageTest = 'micro occupé'; $res = Invoke-CalibrageClaquements
Verifier (-not $res.ok -and $res.texte -match 'pas pu mesurer' -and (Get-Content "$TR\config.local.json" -Raw -Encoding UTF8 | ConvertFrom-Json).claquement_seuil -eq 70) 'mesure impossible : message poli, réglage inchangé'
foreach ($o in 'calibre les claquements', 'Jarvis, calibre les claquements', 'calibre le bruit ambiant', 'calibrer les claquements de mains', 'règle les claquements') { $pl = Get-PlanRapide $o; Verifier ($pl -and $pl.actions[0].type -eq 'calibre_claquements') "« $o » est compris" }

Write-Host '6) Démarrage en veille silencieuse (jarvis.ps1, arreter.ps1, politesse)'
$mj = Get-Content (Join-Path $Root 'jarvis.ps1') -Raw -Encoding UTF8
Verifier ($mj -match "lib\\veille-reveil\.ps1") 'jarvis.ps1 charge lib\veille-reveil.ps1'
Verifier ($mj -match '\$veilleBureau = \(Test-VeilleBureau\)' -and $mj -match 'if \(-not \$serveur -and -not \$veilleBureau\) \{ Start-Visage') 'démarrage en veille : ni HUD ni plein écran (Start-Visage seulement s''il n''y a pas de veille)'
Verifier ($mj -match 'if \(\$veilleBureau\) \{[^}]*Set-Actif \$false' -and $mj -match 'Start-PreChauffageBureau') 'démarrage en veille : sourdine forcée, Ollama / Piper / cache vocal préchauffés'
Verifier ($mj -match 'Update-VeilleReveil' -and $mj -match 'Stop-EcouteVeille') 'la boucle relance l''écoute de veille si elle s''arrête ; elle est fermée à la sortie'
$ra = Get-Content (Join-Path $Root 'lib\raccourcis.ps1') -Raw -Encoding UTF8
Verifier ($ra -match 'Start-VisageReveil' -and $ra -match 'Stop-VisageVeille') 'le HUD s''affiche au réveil et se ferme en veille'
$arr = Get-Content (Join-Path $Root 'arreter.ps1') -Raw -Encoding UTF8; Verifier ($arr -match 'reveil\\\.py') 'arreter.ps1 ferme aussi l''écoute de veille'
Verifier ((Get-Politesse 'reveil_ecoute') -eq 'Je vous écoute.') 'phrase de réveil : « Je vous écoute. » (brève, dans le catalogue de politesse)'
Verifier ($Config.PSObject.Properties['veille_reveil'] -and (Get-Content (Join-Path $Root 'lib\veille-reveil.ps1') -Raw -Encoding UTF8) -notmatch 'Invoke-Expression|iex ') 'aucune évaluation de texte dans la veille'
$vr = Get-Content (Join-Path $Root 'lib\cerveau-local.ps1') -Raw -Encoding UTF8
Verifier ($vr -match 'keep_alive' -and $vr -match '\[switch\]\$Force') 'Ollama : keep_alive configurable (ollama.keep_alive) et préchauffage forcé au démarrage en veille'
Fixer 'ollama' ([pscustomobject]@{ modele = 'qwen2.5:7b'; url = 'http://127.0.0.1:11434'; keep_alive = '24h' }); Verifier ((Get-OllamaConfig).keep -eq '24h') 'ollama.keep_alive = 24h : le modèle reste chargé 24 h'
Fixer 'ollama' ([pscustomobject]@{ modele = 'qwen2.5:7b'; url = 'http://127.0.0.1:11434'; keep_alive = 'n''importe quoi; rm' }); Verifier ((Get-OllamaConfig).keep -eq '30m' -or (Get-OllamaConfig).keep -eq -1) 'ollama.keep_alive invalide : ignoré (valeur par défaut)'
Fixer 'ollama' $vraie.ollama
$pr = Get-Content (Join-Path $Root 'voix\reveil.py') -Raw -Encoding UTF8
Verifier ((Get-Content (Join-Path $Root 'voix\reveil.py') -Encoding Byte -TotalCount 3)[0] -ne 0xEF) 'voix\reveil.py est en UTF-8 sans BOM'
Verifier ($pr -match 'parle_en_cours') 'l''écoute de veille ignore tout pendant que Jarvis parle'

Write-Host '7) installer-bureau.ps1 (fonctions, puis SIMULATION : aucune tâche créée)'
$ib = Join-Path $Root 'installer-bureau.ps1'
$octets = [IO.File]::ReadAllBytes($ib); Verifier ($octets[0] -eq 0xEF -and $octets[1] -eq 0xBB -and $octets[2] -eq 0xBF) 'installer-bureau.ps1 : UTF-8 avec BOM'
$err = $null; [void][Management.Automation.Language.Parser]::ParseFile($ib, [ref]$null, [ref]$err); Verifier ($err.Count -eq 0) 'installer-bureau.ps1 : syntaxe correcte'
$ibTxt = Get-Content $ib -Raw -Encoding UTF8
Verifier ($ibTxt -match "Jarvis-Bureau" -and $ibTxt -match 'New-ScheduledTaskTrigger -AtLogOn' -and $ibTxt -match 'MultipleInstances IgnoreNew' -and $ibTxt -match 'RunLevel Limited' -and $ibTxt -notmatch 'RunLevel Highest') 'tâche « Jarvis-Bureau » : ouverture de session, une seule instance, sans droits administrateur'
Verifier ($ibTxt -match 'jarvis\.ps1' -and $ibTxt -notmatch 'mode_serveur') 'la tâche lance jarvis.ps1 (jamais le mode serveur)'
$simDir = Join-Path $TR 'ib'; New-Item -ItemType Directory $simDir | Out-Null
. $ib -SeulementFonctions -Racine $simDir
$s = Update-ConfigLocaleBureau $simDir
$j = Get-Content "$simDir\config.local.json" -Raw -Encoding UTF8 | ConvertFrom-Json
Verifier ($s.statut -eq 'cree' -and $j.discord_actif -eq $false -and $j.bureau_veille -eq $true -and $j.veille_reveil -eq $true -and $j.etat_au_demarrage -eq 'sourdine' -and $j.ollama.keep_alive -eq '24h') 'config.local.json créé : veille, réveil, sourdine au démarrage, Ollama chaud, Discord désactivé'
$s = Update-ConfigLocaleBureau $simDir; Verifier ($s.statut -eq 'inchange') 'relancé : rien ne change (idempotent)'
[IO.File]::WriteAllText("$simDir\config.local.json", '{ "discord_actif": true, "claquement_seuil": 64, "ollama": { "modele": "qwen2.5:3b" }, "bureau_veille": false }', [Text.UTF8Encoding]::new($false))
$s = Update-ConfigLocaleBureau $simDir; $j = Get-Content "$simDir\config.local.json" -Raw -Encoding UTF8 | ConvertFrom-Json
Verifier ($s.discord -eq 'desactive' -and $j.discord_actif -eq $false) 'Discord activé par erreur dans config.local.json : CORRIGÉ (discord_actif = false)'
Verifier ($j.claquement_seuil -eq 64 -and $j.ollama.modele -eq 'qwen2.5:3b' -and $j.ollama.keep_alive -eq '24h' -and $j.bureau_veille -eq $false) 'vos autres réglages sont conservés (seuil 64, modèle, bureau_veille choisi par vous) ; keep_alive ajouté'
Set-Content "$simDir\config.local.json" '{ pas du json' -Encoding UTF8; $leve = $false; try { [void](Update-ConfigLocaleBureau $simDir) } catch { $leve = $true }
Verifier ($leve -and (Get-Content "$simDir\config.local.json" -Raw) -match 'pas du json') 'config.local.json illisible : erreur claire, fichier NON écrasé'
$tacheAvant = [bool](Get-ScheduledTask -TaskName 'Jarvis-Bureau' -ErrorAction SilentlyContinue)
$sortie = (& powershell -NoProfile -ExecutionPolicy Bypass -File $ib -Simulation 2>&1 | Out-String)
$tacheApres = [bool](Get-ScheduledTask -TaskName 'Jarvis-Bureau' -ErrorAction SilentlyContinue)
Verifier ($sortie -match 'SIMULATION' -and $sortie -match '\[simulation\] tâche planifiée « Jarvis-Bureau »' -and $sortie -match 'TERMINÉ') 'simulation : dit ce qui serait fait (tâche « Jarvis-Bureau »)'
Verifier ($tacheAvant -eq $tacheApres) 'simulation : aucune tâche planifiée créée ni supprimée'
$sortie2 = (& powershell -NoProfile -ExecutionPolicy Bypass -File $ib -Simulation -Retirer 2>&1 | Out-String)
Verifier ($sortie2 -match 'TERMINÉ' -and ([bool](Get-ScheduledTask -TaskName 'Jarvis-Bureau' -ErrorAction SilentlyContinue)) -eq $tacheApres) 'simulation -Retirer : rien n''est supprimé'

Write-Host ''
Remove-Item $TR -Recurse -Force -ErrorAction SilentlyContinue
if ($echecs) { Write-Host "ÉCHEC : $echecs vérification(s) en échec." -ForegroundColor Red; exit 1 }
Write-Host 'TOUT EST VERT.'
