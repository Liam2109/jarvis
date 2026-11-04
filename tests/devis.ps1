# Test SILENCIEUX de l'intégration de l'agent devis (lib\devis.ps1) : désactivé par défaut, lancement unique 90 s après le démarrage, jamais en mode jeu, aucun processus lancé (JARVIS_TEST=1),
# appel présent dans jarvis.ps1, simulation par défaut ; puis les tests Python hors ligne de l'agent (faux Discord, aucun envoi, aucun réseau).
$ErrorActionPreference = 'Stop'
$env:JARVIS_TEST = '1'
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $Root 'lib\journal.ps1')
$TR = Join-Path $env:TEMP ('jarvis-test-' + [guid]::NewGuid().ToString('N').Substring(0, 8)); New-Item -ItemType Directory $TR, "$TR\memoire", "$TR\logs" | Out-Null; $script:JarvisRoot = $TR
$Config = Get-Content $(if ($env:JARVIS_CONFIG -and (Test-Path $env:JARVIS_CONFIG)) { $env:JARVIS_CONFIG } else { Join-Path $Root 'config.json' }) -Raw -Encoding UTF8 | ConvertFrom-Json
. (Join-Path $Root 'lib\devis.ps1')
$echecs = 0
function Get-Instantane([string]$f) { if (Test-Path -LiteralPath $f) { $i = Get-Item -LiteralPath $f; "$($i.Length):$($i.LastWriteTimeUtc.Ticks)" } else { 'absent' } }      # un fichier d'agent (état, journal) peut déjà exister (portable serveur : les agents tournent pour de vrai) : les tests ne doivent pas le CHANGER, pas exiger qu'il n'existe pas
$ag0 = Join-Path $Root 'B2B\agents'; $avantFic = @{}; foreach ($n in 'devis-etat.json', 'devis-journal.log') { $avantFic[$n] = Get-Instantane (Join-Path $ag0 $n) }
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }
function Fixer([string]$cle, $val) { if ($Config.PSObject.Properties[$cle]) { $Config.$cle = $val } else { $Config | Add-Member -NotePropertyName $cle -NotePropertyValue $val } }
function Effacer([string]$cle) { if ($Config.PSObject.Properties[$cle]) { $Config.PSObject.Properties.Remove($cle) } }
$hashConfig = (Get-FileHash (Join-Path $Root 'config.json')).Hash
$t0 = Get-Date

try {
    Write-Host '1. Désactivé par défaut'
    Effacer 'devis_actif'; $script:DevisLance = $false; $script:DevisDebut = $null; $script:DevisRunnerLance = $false
    Verifier (-not (Get-DevisConfig).actif) 'sans réglage devis_actif : désactivé'
    Verifier ((Update-Devis $t0) -eq $false -and (Update-Devis $t0.AddMinutes(10)) -eq $false -and -not $script:DevisRunnerLance) 'désactivé : aucun lancement, même longtemps après'
    Fixer 'devis_actif' 'non'; Verifier (-not (Get-DevisConfig).actif) '« non » : désactivé'

    Write-Host '2. Activé : un seul lancement, 90 s après le démarrage'
    Fixer 'devis_actif' 'oui'; $script:DevisLance = $false; $script:DevisDebut = $null
    Verifier ((Update-Devis $t0) -eq $false) 'à l''instant du démarrage : pas encore'
    Verifier ((Update-Devis $t0.AddSeconds(60)) -eq $false -and -not $script:DevisRunnerLance) '60 s après : pas encore'
    $script:ModeJeu = $true; Verifier ((Update-Devis $t0.AddSeconds(120)) -eq $false -and -not $script:DevisLance) 'mode jeu : rien, et réessai plus tard'
    $script:ModeJeu = $false
    Verifier ((Update-Devis $t0.AddSeconds(100)) -eq $true -and $script:DevisRunnerLance) '100 s après (hors jeu) : lancement (simulé en test)'
    $script:DevisRunnerLance = $false
    Verifier ((Update-Devis $t0.AddSeconds(500)) -eq $false -and -not $script:DevisRunnerLance) 'un seul lancement par session de Jarvis'

    Write-Host '3. Branchement dans jarvis.ps1 et fichiers'
    $j = Get-Content (Join-Path $Root 'jarvis.ps1') -Raw -Encoding UTF8
    Verifier ($j -match "lib\\devis\.ps1") 'jarvis.ps1 charge lib\devis.ps1'
    Verifier ($j -match '\[void\]\(Update-Devis\)') 'jarvis.ps1 appelle Update-Devis dans la boucle'
    Verifier (Test-Path (Join-Path $Root 'B2B\agents\devis.py')) 'B2B\agents\devis.py présent'
    $cfgAgent = Get-Content (Join-Path $Root 'B2B\agents\devis-config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    Verifier ($cfgAgent.envoi_automatique -eq $false) 'devis-config.json : envoi_automatique = false par défaut (simulation)'
    $src = Get-Content (Join-Path $Root 'B2B\agents\devis.py') -Raw -Encoding UTF8
    Verifier ($src -notmatch 'print\([^)]*(jeton|token|password)') 'devis.py n''affiche jamais de jeton ni de mot de passe'
    Verifier ($src -match 'def cmd_rapide' -and $src -match 'def fiche_rapide' -and $src -match '_recevoir_discord') 'devis.py : commande rapide (ligne unique) et réception « devis : … » sur Discord présentes'
    Verifier ($src -notmatch 'smtplib|send_message|api\.stripe\.com|\bimport stripe\b') 'devis.py : aucune fonction d''envoi au client, aucun accès Stripe en écriture'

    Write-Host '4. Tests Python de l''agent (hors ligne : faux Discord, fichiers temporaires, aucun envoi)'
    $py = Get-Command python -ErrorAction SilentlyContinue
    if ($py) {
        $env:PYTHONIOENCODING = 'utf-8'
        $sortie = & $py.Source -I (Join-Path $Root 'B2B\agents\test_devis.py') 2>&1 | Out-String
        Verifier ($LASTEXITCODE -eq 0 -and $sortie -match 'OK : tous les tests de l''agent devis passent') 'agents\test_devis.py : tous les tests passent'
        Remove-Item Env:PYTHONIOENCODING -ErrorAction SilentlyContinue
    } else { Write-Host '  (python introuvable : tests Python sautés)' }
    Verifier (-not (Test-Path (Join-Path $Root 'B2B\agents\devis-continu.verrou'))) 'aucun verrou de boucle laissé'
    Verifier ((Get-Instantane (Join-Path $ag0 'devis-etat.json')) -eq $avantFic['devis-etat.json']) 'aucun état écrit dans le dépôt par les tests (un état existant est inchangé)'
    Verifier ((Get-Instantane (Join-Path $ag0 'devis-journal.log')) -eq $avantFic['devis-journal.log']) 'aucun journal écrit dans le dépôt par les tests (un journal existant est inchangé)'

    Write-Host '5. Propreté'
    Verifier ((Get-FileHash (Join-Path $Root 'config.json')).Hash -eq $hashConfig) 'config.json inchangé'
} finally {
    Remove-Item $TR -Recurse -Force -ErrorAction SilentlyContinue
}
if ($echecs) { Write-Host "`n$echecs ÉCHEC(S)" -ForegroundColor Red; exit 1 }
Write-Host "`nTOUT EST VERT." -ForegroundColor Green; exit 0
