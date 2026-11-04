# Test SILENCIEUX de l'intégration de l'agent rendez-vous (lib\rendez-vous.ps1) : désactivé par défaut, lancement unique 90 s après le démarrage, jamais en mode jeu, aucun processus lancé (JARVIS_TEST=1),
# appel présent dans jarvis.ps1, simulation par défaut ; puis les tests Python hors ligne de l'agent (faux fichier iCal, faux Discord, aucun réseau, aucun message).
$ErrorActionPreference = 'Stop'
$env:JARVIS_TEST = '1'
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $Root 'lib\journal.ps1')
$TR = Join-Path $env:TEMP ('jarvis-test-' + [guid]::NewGuid().ToString('N').Substring(0, 8)); New-Item -ItemType Directory $TR, "$TR\memoire", "$TR\logs" | Out-Null; $script:JarvisRoot = $TR
$Config = Get-Content $(if ($env:JARVIS_CONFIG -and (Test-Path $env:JARVIS_CONFIG)) { $env:JARVIS_CONFIG } else { Join-Path $Root 'config.json' }) -Raw -Encoding UTF8 | ConvertFrom-Json
. (Join-Path $Root 'lib\rendez-vous.ps1')
$echecs = 0
$jrnRdv = Join-Path $Root 'B2B\agents\rendez-vous-journal.log'; $jrnAvant = $(if (Test-Path $jrnRdv) { (Get-Item $jrnRdv).Length } else { -1 })      # le vrai journal peut exister (refus de la machine inactive écrit par Jarvis) : on vérifie qu'il ne bouge pas
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }
function Fixer([string]$cle, $val) { if ($Config.PSObject.Properties[$cle]) { $Config.$cle = $val } else { $Config | Add-Member -NotePropertyName $cle -NotePropertyValue $val } }
function Effacer([string]$cle) { if ($Config.PSObject.Properties[$cle]) { $Config.PSObject.Properties.Remove($cle) } }
$hashConfig = (Get-FileHash (Join-Path $Root 'config.json')).Hash
$t0 = Get-Date

try {
    Write-Host '1. Désactivé par défaut'
    Effacer 'rendez_vous_actif'; $script:RendezVousLance = $false; $script:RendezVousDebut = $null; $script:RendezVousRunnerLance = $false
    Verifier (-not (Get-RendezVousConfig).actif) 'sans réglage rendez_vous_actif : désactivé'
    Verifier ((Update-RendezVous $t0) -eq $false -and (Update-RendezVous $t0.AddMinutes(10)) -eq $false -and -not $script:RendezVousRunnerLance) 'désactivé : aucun lancement, même longtemps après'
    Fixer 'rendez_vous_actif' 'non'; Verifier (-not (Get-RendezVousConfig).actif) '« non » : désactivé'

    Write-Host '2. Activé : un seul lancement, 90 s après le démarrage'
    Fixer 'rendez_vous_actif' 'oui'; $script:RendezVousLance = $false; $script:RendezVousDebut = $null
    Verifier ((Update-RendezVous $t0) -eq $false) 'à l''instant du démarrage : pas encore'
    Verifier ((Update-RendezVous $t0.AddSeconds(60)) -eq $false -and -not $script:RendezVousRunnerLance) '60 s après : pas encore'
    $script:ModeJeu = $true; Verifier ((Update-RendezVous $t0.AddSeconds(120)) -eq $false -and -not $script:RendezVousLance) 'mode jeu : rien, et réessai plus tard'
    $script:ModeJeu = $false
    Verifier ((Update-RendezVous $t0.AddSeconds(100)) -eq $true -and $script:RendezVousRunnerLance) '100 s après (hors jeu) : lancement (simulé en test)'
    $script:RendezVousRunnerLance = $false
    Verifier ((Update-RendezVous $t0.AddSeconds(500)) -eq $false -and -not $script:RendezVousRunnerLance) 'un seul lancement par session de Jarvis'

    Write-Host '3. Branchement dans jarvis.ps1 et fichiers'
    $j = Get-Content (Join-Path $Root 'jarvis.ps1') -Raw -Encoding UTF8
    Verifier ($j -match "lib\\rendez-vous\.ps1") 'jarvis.ps1 charge lib\rendez-vous.ps1'
    Verifier ($j -match '\[void\]\(Update-RendezVous\)') 'jarvis.ps1 appelle Update-RendezVous dans la boucle'
    Verifier (Test-Path (Join-Path $Root 'B2B\agents\rendez-vous.py')) 'B2B\agents\rendez-vous.py présent'
    $cfgAgent = Get-Content (Join-Path $Root 'B2B\agents\rendez-vous-config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    Verifier ($cfgAgent.envoi_automatique -eq $false) 'rendez-vous-config.json : envoi_automatique = false par défaut (simulation)'
    $src = Get-Content (Join-Path $Root 'B2B\agents\rendez-vous.py') -Raw -Encoding UTF8
    Verifier ($src -notmatch 'print\([^)]*(jeton|token|password)') 'rendez-vous.py n''affiche jamais de jeton ni de mot de passe'
    Verifier (-not $cfgAgent.ical_url -and $cfgAgent.cycle_minutes -eq 5 -and -not $cfgAgent.salon_id) 'rendez-vous-config.json : aucune adresse iCal ni salon dans le fichier versionné (ils vivent dans rendez-vous-config.local.json, ignoré par git), vérification toutes les 5 min'
    Verifier ($src -notmatch 'smtplib|send_message|api\.stripe\.com|getpass') 'rendez-vous.py : aucune fonction d''envoi à un tiers, aucun accès Stripe, aucun mot de passe saisi'
    Verifier ((& git -C $Root check-ignore 'B2B/agents/rendez-vous-config.local.json') -match 'local\.json') 'rendez-vous-config.local.json (adresse secrète iCal) est ignoré par git ; le fichier par défaut, sans secret, est versionné'

    Write-Host '4. Tests Python de l''agent (hors ligne : faux iCal, faux Discord, fichiers temporaires, aucun message)'
    $py = Get-Command python -ErrorAction SilentlyContinue
    if ($py) {
        $env:PYTHONIOENCODING = 'utf-8'
        $sortie = & $py.Source -I (Join-Path $Root 'B2B\agents\test_rendez_vous.py') 2>&1 | Out-String
        Verifier ($LASTEXITCODE -eq 0 -and $sortie -match 'OK : tous les tests de l''agent rendez-vous passent') 'agents\test_rendez_vous.py : tous les tests passent'
        Remove-Item Env:PYTHONIOENCODING -ErrorAction SilentlyContinue
    } else { Write-Host '  (python introuvable : tests Python sautés)' }
    Verifier (-not (Test-Path (Join-Path $Root 'B2B\agents\rendez-vous-continu.verrou'))) 'aucun verrou de boucle laissé'
    Verifier (-not (Test-Path (Join-Path $Root 'B2B\agents\rendez-vous-etat.json'))) 'aucun état écrit dans le dépôt par les tests'
    Verifier ($jrnAvant -eq $(if (Test-Path $jrnRdv) { (Get-Item $jrnRdv).Length } else { -1 })) 'aucun journal écrit dans le dépôt par les tests (le journal existant, s''il y en a un, est inchangé)'

    Write-Host '5. Propreté'
    Verifier ((Get-FileHash (Join-Path $Root 'config.json')).Hash -eq $hashConfig) 'config.json inchangé'
} finally {
    Remove-Item $TR -Recurse -Force -ErrorAction SilentlyContinue
}
if ($echecs) { Write-Host "`n$echecs ÉCHEC(S)" -ForegroundColor Red; exit 1 }
Write-Host "`nTOUT EST VERT." -ForegroundColor Green; exit 0
