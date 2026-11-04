# Test SILENCIEUX de l'intégration de l'agent Instagram (lib\instagram.ps1) : désactivé par défaut, lancement unique 90 s après le démarrage, jamais en mode jeu, aucun processus lancé (JARVIS_TEST=1),
# appel présent dans jarvis.ps1, simulation par défaut ; puis les tests Python hors ligne de l'agent (faux transport Instagram, aucune publication, aucun réseau).
$ErrorActionPreference = 'Stop'
$env:JARVIS_TEST = '1'
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $Root 'lib\journal.ps1')
$TR = Join-Path $env:TEMP ('jarvis-test-' + [guid]::NewGuid().ToString('N').Substring(0, 8)); New-Item -ItemType Directory $TR, "$TR\memoire", "$TR\logs" | Out-Null; $script:JarvisRoot = $TR
$Config = Get-Content $(if ($env:JARVIS_CONFIG -and (Test-Path $env:JARVIS_CONFIG)) { $env:JARVIS_CONFIG } else { Join-Path $Root 'config.json' }) -Raw -Encoding UTF8 | ConvertFrom-Json
. (Join-Path $Root 'lib\instagram.ps1')
$echecs = 0
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }
function Fixer([string]$cle, $val) { if ($Config.PSObject.Properties[$cle]) { $Config.$cle = $val } else { $Config | Add-Member -NotePropertyName $cle -NotePropertyValue $val } }
function Effacer([string]$cle) { if ($Config.PSObject.Properties[$cle]) { $Config.PSObject.Properties.Remove($cle) } }
$hashConfig = (Get-FileHash (Join-Path $Root 'config.json')).Hash
$t0 = Get-Date

try {
    Write-Host '1. Désactivé par défaut'
    Effacer 'instagram_actif'; $script:InstagramLancee = $false; $script:InstagramDebut = $null; $script:InstagramRunnerLance = $false
    Verifier (-not (Get-InstagramConfig).actif) 'sans réglage instagram_actif : désactivé'
    Verifier ((Update-Instagram $t0) -eq $false -and (Update-Instagram $t0.AddMinutes(10)) -eq $false -and -not $script:InstagramRunnerLance) 'désactivé : aucun lancement, même longtemps après'
    Fixer 'instagram_actif' 'non'; Verifier (-not (Get-InstagramConfig).actif) '« non » : désactivé'

    Write-Host '2. Activé : un seul lancement, 90 s après le démarrage'
    Fixer 'instagram_actif' 'oui'; $script:InstagramLancee = $false; $script:InstagramDebut = $null
    Verifier ((Update-Instagram $t0) -eq $false) 'à l''instant du démarrage : pas encore'
    Verifier ((Update-Instagram $t0.AddSeconds(60)) -eq $false -and -not $script:InstagramRunnerLance) '60 s après : pas encore'
    $script:ModeJeu = $true; Verifier ((Update-Instagram $t0.AddSeconds(120)) -eq $false -and -not $script:InstagramLancee) 'mode jeu : rien, et réessai plus tard'
    $script:ModeJeu = $false
    Verifier ((Update-Instagram $t0.AddSeconds(100)) -eq $true -and $script:InstagramRunnerLance) '100 s après (hors jeu) : lancement (simulé en test)'
    $script:InstagramRunnerLance = $false
    Verifier ((Update-Instagram $t0.AddSeconds(500)) -eq $false -and -not $script:InstagramRunnerLance) 'un seul lancement par session de Jarvis'

    Write-Host '3. Branchement dans jarvis.ps1 et fichiers'
    $j = Get-Content (Join-Path $Root 'jarvis.ps1') -Raw -Encoding UTF8
    Verifier ($j -match "lib\\instagram\.ps1") 'jarvis.ps1 charge lib\instagram.ps1'
    Verifier ($j -match '\[void\]\(Update-Instagram\)') 'jarvis.ps1 appelle Update-Instagram dans la boucle'
    Verifier (Test-Path (Join-Path $Root 'B2B\agents\instagram.py')) 'B2B\agents\instagram.py présent'
    $cfgAgent = Get-Content (Join-Path $Root 'B2B\agents\instagram-config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    Verifier ($cfgAgent.envoi_automatique -eq $false) 'instagram-config.json : envoi_automatique = false par défaut (simulation)'
    Verifier ($cfgAgent.heure_publication -eq '12:30') 'instagram-config.json : publication à 12:30'
    Verifier ((Get-Content (Join-Path $Root 'B2B\agents\instagram.py') -Raw -Encoding UTF8) -notmatch 'print\([^)]*access_token') 'instagram.py n''affiche jamais le jeton (access_token absent des print)'

    Write-Host '4. Tests Python de l''agent (hors ligne : faux transport, fichiers temporaires, aucune publication)'
    $py = Get-Command python -ErrorAction SilentlyContinue
    if ($py) {
        $env:PYTHONIOENCODING = 'utf-8'
        $sortie = & $py.Source (Join-Path $Root 'B2B\agents\test_instagram.py') 2>&1 | Out-String
        Verifier ($LASTEXITCODE -eq 0 -and $sortie -match 'OK : tous les tests de l''agent Instagram passent') 'agents\test_instagram.py : tous les tests passent'
        Remove-Item Env:PYTHONIOENCODING -ErrorAction SilentlyContinue
    } else { Write-Host '  (python introuvable : tests Python sautés)' }
    Verifier (-not (Test-Path (Join-Path $Root 'B2B\agents\instagram-continu.verrou'))) 'aucun verrou de boucle laissé'
    Verifier (-not (Test-Path (Join-Path $Root 'B2B\agents\instagram-etat.json'))) 'aucun état écrit dans le dépôt par les tests'

    Write-Host '5. Propreté'
    Verifier ((Get-FileHash (Join-Path $Root 'config.json')).Hash -eq $hashConfig) 'config.json inchangé'
} finally {
    Remove-Item $TR -Recurse -Force -ErrorAction SilentlyContinue
}
if ($echecs) { Write-Host "`n$echecs ÉCHEC(S)" -ForegroundColor Red; exit 1 }
Write-Host "`nTOUT EST VERT." -ForegroundColor Green; exit 0
