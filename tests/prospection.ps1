# Test SILENCIEUX de l'intégration de l'agent Prospection (lib\prospection.ps1) : désactivé par défaut, lancement unique 90 s après le démarrage, jamais en mode jeu,
# aucun processus lancé (JARVIS_TEST=1), appel présent dans jarvis.ps1 ; puis les tests Python hors ligne de l'agent (faux SMTP, faux Discord, rien d'envoyé).
$ErrorActionPreference = 'Stop'
$env:JARVIS_TEST = '1'
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $Root 'lib\journal.ps1')
$TR = Join-Path $env:TEMP ('jarvis-test-' + [guid]::NewGuid().ToString('N').Substring(0, 8)); New-Item -ItemType Directory $TR, "$TR\memoire", "$TR\logs" | Out-Null; $script:JarvisRoot = $TR
$Config = Get-Content $(if ($env:JARVIS_CONFIG -and (Test-Path $env:JARVIS_CONFIG)) { $env:JARVIS_CONFIG } else { Join-Path $Root 'config.json' }) -Raw -Encoding UTF8 | ConvertFrom-Json
. (Join-Path $Root 'lib\prospection.ps1')
$echecs = 0
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }
function Fixer([string]$cle, $val) { if ($Config.PSObject.Properties[$cle]) { $Config.$cle = $val } else { $Config | Add-Member -NotePropertyName $cle -NotePropertyValue $val } }
function Effacer([string]$cle) { if ($Config.PSObject.Properties[$cle]) { $Config.PSObject.Properties.Remove($cle) } }
$hashConfig = (Get-FileHash (Join-Path $Root 'config.json')).Hash
$t0 = Get-Date

try {
    Write-Host '1. Désactivé par défaut'
    Effacer 'prospection_actif'; $script:ProspectionLancee = $false; $script:ProspectionDebut = $null; $script:ProspectionRunnerLance = $false
    Verifier (-not (Get-ProspectionConfig).actif) 'sans réglage prospection_actif : désactivé'
    Verifier ((Update-Prospection $t0) -eq $false -and (Update-Prospection $t0.AddMinutes(10)) -eq $false -and -not $script:ProspectionRunnerLance) 'désactivé : aucun lancement, même longtemps après'
    Fixer 'prospection_actif' 'non'; Verifier (-not (Get-ProspectionConfig).actif) '« non » : désactivé'

    Write-Host '2. Activé : un seul lancement, 90 s après le démarrage'
    Fixer 'prospection_actif' 'oui'; $script:ProspectionLancee = $false; $script:ProspectionDebut = $null
    Verifier ((Update-Prospection $t0) -eq $false) 'à l''instant du démarrage : pas encore'
    Verifier ((Update-Prospection $t0.AddSeconds(60)) -eq $false -and -not $script:ProspectionRunnerLance) '60 s après : pas encore'
    $script:ModeJeu = $true; Verifier ((Update-Prospection $t0.AddSeconds(120)) -eq $false -and -not $script:ProspectionLancee) 'mode jeu : rien, et réessai plus tard'
    $script:ModeJeu = $false
    Verifier ((Update-Prospection $t0.AddSeconds(100)) -eq $true -and $script:ProspectionRunnerLance) '100 s après (hors jeu) : lancement (simulé en test)'
    $script:ProspectionRunnerLance = $false
    Verifier ((Update-Prospection $t0.AddSeconds(500)) -eq $false -and -not $script:ProspectionRunnerLance) 'un seul lancement par session de Jarvis'

    Write-Host '3. Branchement dans jarvis.ps1 et fichiers'
    $j = Get-Content (Join-Path $Root 'jarvis.ps1') -Raw -Encoding UTF8
    Verifier ($j -match "lib\\prospection\.ps1") 'jarvis.ps1 charge lib\prospection.ps1'
    Verifier ($j -match '\[void\]\(Update-Prospection\)') 'jarvis.ps1 appelle Update-Prospection dans la boucle'
    Verifier (Test-Path (Join-Path $Root 'B2B\agents\prospection.py')) 'B2B\agents\prospection.py présent'
    $cfgAgent = Get-Content (Join-Path $Root 'B2B\agents\prospection-config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    Verifier ($cfgAgent.envoi_automatique -eq $false) 'prospection-config.json : envoi_automatique = false par défaut'
    Verifier ($cfgAgent.par_boite_par_jour -le 10 -and $cfgAgent.pause_envoi_s[0] -ge 90 -and $cfgAgent.pause_envoi_s[1] -le 300) 'plafond 10 par boîte et par jour, pauses 90 à 300 s'

    Write-Host '4. Tests Python de l''agent (hors ligne : faux SMTP, faux Discord, fichiers temporaires)'
    $py = Get-Command python -ErrorAction SilentlyContinue
    if ($py) {
        $env:PYTHONIOENCODING = 'utf-8'
        $sortie = & $py.Source (Join-Path $Root 'B2B\agents\test_prospection.py') 2>&1 | Out-String
        Verifier ($LASTEXITCODE -eq 0 -and $sortie -match 'OK : tous les tests passent') 'agents\test_prospection.py : tous les tests passent'
        Remove-Item Env:PYTHONIOENCODING -ErrorAction SilentlyContinue
    } else { Write-Host '  (python introuvable : tests Python sautés)' }
    Verifier (-not (Test-Path (Join-Path $Root 'B2B\agents\prospection.verrou'))) 'aucun verrou d''écoute laissé'

    Write-Host '5. Propreté'
    Verifier ((Get-FileHash (Join-Path $Root 'config.json')).Hash -eq $hashConfig) 'config.json inchangé'
} finally {
    Remove-Item $TR -Recurse -Force -ErrorAction SilentlyContinue
}
if ($echecs) { Write-Host "`n$echecs ÉCHEC(S)" -ForegroundColor Red; exit 1 }
Write-Host "`nTOUT EST VERT." -ForegroundColor Green; exit 0
