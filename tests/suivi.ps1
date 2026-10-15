# Test SILENCIEUX : suite de conversation filtrée (suivi_strict), réglages de vitesse de CE PC (Ollama chaud dans config.local.json seulement), seuil de bruit, fin de phrase plafonnée.
# Aucun micro, aucun son, aucune fenêtre, aucun appel à Claude ni à Ollama (cerveaux simulés). Code de sortie 0 = réussi.
$ErrorActionPreference = 'Stop'
$env:JARVIS_TEST = '1'
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $Root 'lib\journal.ps1')
$TR = Join-Path $env:TEMP ('jarvis-test-' + [guid]::NewGuid().ToString('N').Substring(0, 8)); New-Item -ItemType Directory $TR, "$TR\memoire", "$TR\logs" | Out-Null; $script:JarvisRoot = $TR
'# To-do' | Set-Content "$TR\memoire\todo.md" -Encoding UTF8; '# N' | Set-Content "$TR\memoire\notes.md" -Encoding UTF8; '# R' | Set-Content "$TR\memoire\resume.md" -Encoding UTF8
$Config = Get-Content $(if ($env:JARVIS_CONFIG -and (Test-Path $env:JARVIS_CONFIG)) { $env:JARVIS_CONFIG } else { Join-Path $Root 'config.json' }) -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($l in 'voix', 'business', 'permissions', 'actions', 'coffre', 'entrees', 'ecrans', 'tableau', 'visage', 'sons', 'raccourcis', 'cerveau', 'cerveau-local', 'veille', 'memoire', 'rapide', 'discretion', 'modejeu', 'competences', 'marche', 'priorite', 'comprehension', 'routeur', 'pc', 'bureau', 'salle-marche', 'matin', 'discord', 'veille-reveil', 'boucle') { . (Join-Path $Root "lib\$l.ps1") }
$script:JarvisRoot = $TR
$echecs = 0
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }
function Fixer([string]$cle, $val) { if ($Config.PSObject.Properties[$cle]) { $Config.$cle = $val } else { $Config | Add-Member -NotePropertyName $cle -NotePropertyValue $val } }
function Effacer([string]$cle) { if ($Config.PSObject.Properties[$cle]) { $Config.PSObject.Properties.Remove($cle) } }
function Journal { $f = Join-Path $TR ('logs\journal-{0}.md' -f (Get-Date -Format 'yyyy-MM-dd')); if (Test-Path $f) { Get-Content $f -Raw -Encoding UTF8 } else { '' } }
$vraie = Get-Content (Join-Path $Root 'config.json') -Raw -Encoding UTF8 | ConvertFrom-Json

Write-Host '1) L''écoute transmet la suite de conversation avec son marquage'
$script:Entrees.Clear()
$fauxOut = [pscustomobject]@{}; $fauxOut | Add-Member -MemberType ScriptMethod -Name ReadLineAsync -Value { [Threading.Tasks.Task]::FromResult([string]$null) }
$script:Ecoute = [pscustomobject]@{ HasExited = $false; StandardOutput = $fauxOut }
$script:EcouteTache = [Threading.Tasks.Task]::FromResult('SUIVI:c''est incroyable'); Invoke-Pump
$e1 = $script:Entrees.Dequeue()
Verifier ($e1.texte -eq 'c''est incroyable' -and $e1.suivi -eq $true -and $e1.src -eq 'voix') 'ligne « SUIVI: » : ordre vocal marqué « suite de conversation »'
$script:EcouteTache = [Threading.Tasks.Task]::FromResult('ORDRE:ouvre chrome'); Invoke-Pump
$e2 = $script:Entrees.Dequeue()
Verifier ($e2.texte -eq 'ouvre chrome' -and $e2.suivi -eq $false) 'ligne « ORDRE: » : ordre normal, non marqué'
$script:Ecoute = $null; $script:EcouteTache = $null; $script:Entrees.Clear()

Write-Host '2) La suite sans « Jarvis » : règle ou routeur, sinon ignorée (jamais Claude)'
$script:Dits = New-Object System.Collections.Generic.List[string]; $script:AppelsClaude = 0; $script:AppelsRouteur = 0; $script:PlanRouteur = $null
function Parler { param([string]$t, $Langue) $script:Dits.Add($t) }
function Get-Plan([string]$ordre) { $script:AppelsClaude++; $null }
function Resolve-Routeur([string]$ordre) { $script:AppelsRouteur++; $script:RouteurRaison = 'conversation en 900 ms'; $script:RouteurEtat = 'conversation'; $script:PlanRouteur }
function Resolve-IntentionTolerante([string]$o) { $null }
Effacer 'suivi_strict'
foreach ($c in 'c''est incroyable', 'wow', 'non non non n''y pas', 'ah par contre du coup j''aimerais bien que plus tard tu fasses un truc') {
    $script:Dits.Clear(); $script:AppelsClaude = 0; $script:OrdreSuivi = $true; $j0 = (Journal).Length
    Invoke-OrdreCorps $c; $script:OrdreSuivi = $false
    Verifier ($script:AppelsClaude -eq 0 -and $script:Dits.Count -eq 0 -and (Journal).Substring($j0) -match 'Suite de conversation ignorée') "suite « $c » : ni Claude, ni réponse parlée, notée au journal"
}
$script:Dits.Clear(); $script:AppelsClaude = 0; $script:OrdreSuivi = $true
Invoke-OrdreCorps 'quelle heure est-il'; $script:OrdreSuivi = $false
Verifier ($script:Dits.Count -ge 1 -and $script:AppelsClaude -eq 0) 'suite comprise par une RÈGLE (« quelle heure est-il ») : exécutée'
$script:Dits.Clear(); $script:PlanRouteur = New-PlanRapide 'Très bien monsieur.' @() $null 'routeur'; $script:OrdreSuivi = $true
Invoke-OrdreCorps 'mets un peu plus de son s''il te plait'; $script:OrdreSuivi = $false; $script:PlanRouteur = $null
Verifier ($script:AppelsRouteur -ge 1 -and $script:Dits -contains 'Très bien monsieur.' -and $script:AppelsClaude -eq 0) 'suite comprise par le ROUTEUR : exécutée, sans Claude'
$script:Dits.Clear(); $script:AppelsClaude = 0; $script:OrdreSuivi = $false
Invoke-OrdreCorps 'wow'
Verifier ($script:AppelsClaude -eq 1) 'même phrase AVEC « Jarvis » (ordre normal) : transmise à Claude comme avant'
Fixer 'suivi_strict' $false; $script:AppelsClaude = 0; $script:OrdreSuivi = $true
Invoke-OrdreCorps 'wow'; $script:OrdreSuivi = $false
Verifier ($script:AppelsClaude -eq 1) 'suivi_strict = false : ancien comportement (la suite va à Claude)'
Effacer 'suivi_strict'

Write-Host '3) Invoke-Entree : le marquage est posé pendant l''ordre puis retiré'
$script:Vu = $null; function Invoke-Ordre([string]$o) { $script:Vu = $script:OrdreSuivi }
$script:Actif = $true; $script:ModeJeu = $false
Invoke-Entree @{ src = 'voix'; texte = 'hello'; suivi = $true; entendu = $false }
Verifier ($script:Vu -eq $true -and $script:OrdreSuivi -eq $false) 'entrée « suite » : Invoke-Ordre la voit marquée, puis le marquage disparaît'
$script:Vu = $null; Invoke-Entree @{ src = 'voix'; texte = 'hello'; entendu = $false }
Verifier ($script:Vu -eq $false) 'entrée normale : non marquée'
$script:Vu = $null; Invoke-Entree @{ src = 'clavier'; texte = 'hello'; suivi = $false; entendu = $false }
Verifier ($script:Vu -eq $false) 'ordre écrit : jamais filtré'
Remove-Item Function:\Invoke-Ordre
$mj = Get-Content (Join-Path $Root 'lib\cerveau.ps1') -Raw -Encoding UTF8
Verifier ($mj -match '(?s)Resolve-IntentionTolerante.*?OrdreSuivi.*?Test-OrdreControlePc') 'le filtre vient APRÈS la règle et le routeur et AVANT Claude'

Write-Host '4) Réglages de vitesse : config.json (général) et config.local.json (CE PC)'
Verifier ($vraie.suivi_strict -eq $true -and $vraie.bruit_adaptatif -eq $true) 'config.json : suivi_strict et bruit_adaptatif actifs par défaut'
Verifier ($vraie.duree_max_phrase_s -eq 20) 'config.json : phrase continue plafonnée à 20 s (30 s avant)'
Verifier ($vraie.whisper_peripherique -eq 'cuda' -and $vraie.moteur_voix_appareil -eq 'cuda') 'config.json : whisper_peripherique et moteur_voix_appareil alignés sur cuda'
Verifier (-not $vraie.PSObject.Properties['ollama_toujours_chaud'] -and -not ($vraie.ollama.PSObject.Properties['keep_alive'])) 'config.json : AUCUN réglage « Ollama chaud » (ce serait appliqué au serveur)'
Verifier ($vraie.voix_moteur -eq 'edge') 'la voix reste Edge'
$loc = Join-Path $Root 'config.local.json'
if (Test-Path $loc) {
    $l = Get-Content $loc -Raw -Encoding UTF8 | ConvertFrom-Json
    Verifier ($l.ollama_toujours_chaud -eq $true -and "$($l.ollama.keep_alive)" -eq '24h') 'config.local.json de ce PC : Ollama chaud en permanence (keep_alive 24 h)'
    Verifier (-not $l.PSObject.Properties['mode_serveur']) 'config.local.json de ce PC : pas en mode serveur'
} else { Write-Host '        (pas de config.local.json ici : contrôle de ce PC sauté)' }
$mc = Get-MicroConfig
Verifier ($mc.duree_max -eq 20 -and $mc.bruit -eq $true -and $mc.whisper_peripherique -eq 'cuda') 'Get-MicroConfig : phrase max 20 s, bruit adaptatif, Whisper sur cuda'
Verifier ((Get-ArgsEcoute 'x.py') -match '--bruit-adaptatif 1' -and (Get-ArgsEcoute 'x.py') -match '--duree-max 20') 'arguments de l''écoute : --bruit-adaptatif 1, --duree-max 20'
Fixer 'bruit_adaptatif' $false; Verifier ((Get-ArgsEcoute 'x.py') -match '--bruit-adaptatif 0') 'bruit_adaptatif = false : seuil fixe (--bruit-adaptatif 0)'
Fixer 'bruit_adaptatif' $true

Write-Host '5) Ollama chaud en permanence sur CE PC (jamais sur le serveur)'
Verifier (-not (Test-GardeOllamaChaud)) 'config.json seul : Ollama se décharge en sourdine comme avant'
Fixer 'ollama_toujours_chaud' $true; Fixer 'ollama' ([pscustomobject]@{ modele = 'qwen2.5:7b'; url = 'http://127.0.0.1:11434'; delai_secondes = 60 })
Verifier ((Test-GardeOllamaChaud) -and (Get-OllamaConfig).keep -eq '24h') 'ollama_toujours_chaud : le modèle reste chargé 24 h'
Fixer 'ollama' ([pscustomobject]@{ modele = 'qwen2.5:7b'; url = 'http://127.0.0.1:11434'; keep_alive = '2h' }); Verifier ((Get-OllamaConfig).keep -eq '2h') 'ollama.keep_alive explicite : respecté'
Fixer 'ollama' ([pscustomobject]@{ modele = 'qwen2.5:3b'; url = 'http://127.0.0.1:11434' }); Fixer 'mode_serveur' $true; Verifier (-not (Test-GardeOllamaChaud) -and (Get-OllamaConfig).keep -eq '5m') 'mode serveur : ignoré, le modèle se décharge après 5 min'
Effacer 'mode_serveur'
$script:Etats = @(); function Start-Ecoute { }; function Stop-Ecoute { }; function Release-GpuModeles { $script:Etats += 'liberer' }
$script:EtatFichier2 = Join-Path $TR 'etat.json'; $script:SourdineFlag = Join-Path $TR 'sourdine.flag'; $script:Actif = $true
Set-Actif $false 'test'; Verifier ($script:Etats.Count -eq 0) 'sourdine sur ce PC : le modèle n''est PAS déchargé du GPU'
Fixer 'ollama_toujours_chaud' $false; $script:Actif = $true; $script:Etats = @(); Set-Actif $false 'test'; Verifier ($script:Etats -contains 'liberer') 'sans le réglage : déchargé comme avant'
$jv = Get-Content (Join-Path $Root 'jarvis.ps1') -Raw -Encoding UTF8
Verifier ($jv -match 'elseif \(Test-GardeOllamaChaud\) \{ Start-OllamaReveil -Force \}') 'jarvis.ps1 : au démarrage, le modèle est préchauffé même en sourdine'
Verifier ((Get-Content (Join-Path $Root 'lib\raccourcis.ps1') -Raw -Encoding UTF8) -match 'Enter-ModeJeu|ollama_toujours_chaud') 'la sourdine tient compte de ollama_toujours_chaud'
$mjx = Get-Content (Join-Path $Root 'lib\modejeu.ps1') -Raw -Encoding UTF8; Verifier ($mjx -match 'Release-GpuModeles') 'le mode jeu libère toujours le GPU (les jeux passent avant)'

Write-Host '6) Écoute : SUIVI, hallucinations de Whisper, seuil de bruit adaptatif (voix\ecoute.py, simulé)'
$sortiePy = (& python -I (Join-Path $PSScriptRoot 'suivi.py') 2>&1 | Out-String); $codePy = $LASTEXITCODE
Verifier ($codePy -eq 0 -and ([regex]::Matches($sortiePy, '(?m)^\s+OK ')).Count -ge 40) "tests\suivi.py : tout est vert ($(([regex]::Matches($sortiePy, '(?m)^\s+OK ')).Count) vérifications)"
if ($codePy -ne 0) { ($sortiePy -split "`n" | Where-Object { $_ -match 'ECHEC|Error|Traceback' }) | Select-Object -First 8 | ForEach-Object { Write-Host $_ } }

Write-Host ''
Remove-Item $TR -Recurse -Force -ErrorAction SilentlyContinue
if ($echecs) { Write-Host "ÉCHEC : $echecs vérification(s) en échec." -ForegroundColor Red; exit 1 }
Write-Host 'TOUT EST VERT.'
