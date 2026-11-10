# Test SILENCIEUX de l'agent appels-sid (liste d'appels du matin pour Sid) : fichiers présents, simulation par défaut dans le fichier versionné, aucun envoi ni réseau dans le code, branchement dans tests\tout.ps1 ;
# puis les tests Python hors ligne (faux fichiers, dossiers temporaires, aucun réseau).
$ErrorActionPreference = 'Stop'
$env:JARVIS_TEST = '1'
$Root = Split-Path -Parent $PSScriptRoot
$echecs = 0
function Get-Instantane([string]$f) { if (Test-Path -LiteralPath $f) { $i = Get-Item -LiteralPath $f; "$($i.Length):$($i.LastWriteTimeUtc.Ticks)" } else { 'absent' } }      # un fichier d'agent (état, journal) peut déjà exister (portable serveur : les agents tournent pour de vrai) : les tests ne doivent pas le CHANGER, pas exiger qu'il n'existe pas
$ag0 = Join-Path $Root 'B2B\agents'; $avantFic = @{}; foreach ($n in 'appels-sid-etat.json', 'appels-sid.verrou', 'appels-sid-journal.log', 'appels-sid-historique.json', 'google-sheets-token.json') { $avantFic[$n] = Get-Instantane (Join-Path $ag0 $n) }
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }
$hashConfig = (Get-FileHash (Join-Path $Root 'config.json')).Hash
$hashProsp = (Get-FileHash (Join-Path $Root 'B2B\agents\prospection-config.json')).Hash
$ag = Join-Path $Root 'B2B\agents'

Write-Host '1. Fichiers et réglages'
foreach ($f in 'appels-sid.py', 'google_sheets.py', 'appels-sid-config.json', 'appels-sid.md', 'test_appels_sid.py') { Verifier (Test-Path (Join-Path $ag $f)) "B2B\agents\$f présent" }
$cfgAgent = Get-Content (Join-Path $ag 'appels-sid-config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
Verifier ($cfgAgent.envoi_automatique -eq $false) 'appels-sid-config.json : envoi_automatique = false par défaut (fichier versionné ; activation réelle par machine dans appels-sid-config.local.json, ignoré par git)'
Verifier ($cfgAgent.par_liste -ge 100 -and $cfgAgent.par_liste -le 130) 'appels-sid-config.json : par_liste entre 100 et 130 (règle fixe de Liam, 10 nov. 2026)'
Verifier ($cfgAgent.cible_reserve -ge 400 -and $cfgAgent.seuil_alerte -eq 200) 'appels-sid-config.json : réserve cible 400, alerte sous 200 (2 jours à 100/jour)'
Verifier ($cfgAgent.jours_sans_rappel -eq 365) 'appels-sid-config.json : jours_sans_rappel = 365 (règle fixe de Liam, 10 nov. 2026)'
$src = Get-Content (Join-Path $ag 'appels-sid.py') -Raw -Encoding UTF8
Verifier ($src -notmatch 'smtplib|send_message|gmail_api|stripe|webbrowser|os\.system|shell=True|places\.googleapis') 'appels-sid.py : aucun envoi d''e-mail ni de message à une entreprise, aucun Stripe, aucune API payante'
Verifier (-not $cfgAgent.partager_avec) 'appels-sid-config.json : aucun partager_avec dans le fichier versionné (rien n''est partagé ; l''adresse vit dans appels-sid-config.local.json, ignoré par git)'
Verifier (@($cfgAgent.jours_appel) -join ',' -eq 'lundi,mardi,jeudi') 'appels-sid-config.json : jours_appel = lundi, mardi, jeudi'
# Diagnostic seulement (ne compte pas dans $echecs) : l'activation réelle (tâche planifiée, envoi_automatique local) varie d'une machine à l'autre
# et ne doit jamais bloquer tests\tout.ps1 / maj-auto.ps1 sur une machine qui n'a pas vocation à être le serveur. Voir `python agents\appels-sid.py etat`.
$tacheReelle = Get-ScheduledTask -TaskName 'Jarvis-AppelsSid' -ErrorAction SilentlyContinue
Write-Host "  INFO  tâche planifiée Jarvis-AppelsSid : $(if ($tacheReelle) { 'installée sur cette machine' } else { 'non installée sur cette machine' })"
$tout = Get-Content (Join-Path $Root 'tests\tout.ps1') -Raw -Encoding UTF8
Verifier ($tout -match "f = 'appels-sid\.ps1'") 'tests\tout.ps1 lance ce test'

Write-Host '2. Tests Python de l''agent (hors ligne)'
$py = Get-Command python -ErrorAction SilentlyContinue
if ($py) {
    $env:PYTHONIOENCODING = 'utf-8'
    $sortie = & $py.Source -I (Join-Path $ag 'test_appels_sid.py') 2>&1 | Out-String
    Verifier ($LASTEXITCODE -eq 0 -and $sortie -match 'OK : tous les tests de l''agent appels-sid passent') 'agents\test_appels_sid.py : tous les tests passent'
    Remove-Item Env:PYTHONIOENCODING -ErrorAction SilentlyContinue
} else { Write-Host '  (python introuvable : tests Python sautés)' }
foreach ($f in 'appels-sid-etat.json', 'appels-sid.verrou', 'appels-sid-journal.log', 'appels-sid-historique.json', 'google-sheets-token.json') { Verifier ((Get-Instantane (Join-Path $ag0 $f)) -eq $avantFic[$f]) "aucun $f écrit dans le dépôt par les tests (un fichier existant est inchangé)" }
Verifier (-not (Test-Path (Join-Path $Root 'B2B\docs\sid\liste-sid-2026-11-04.csv'))) 'aucune liste de test dans B2B\docs\sid'

Write-Host '3. Propreté'
Verifier ((Get-FileHash (Join-Path $Root 'config.json')).Hash -eq $hashConfig) 'config.json inchangé'
Verifier ((Get-FileHash (Join-Path $Root 'B2B\agents\prospection-config.json')).Hash -eq $hashProsp) 'prospection-config.json inchangé (la liste de Liam n''est redirigée que sur ordre)'
if ($echecs) { Write-Host "`n$echecs ÉCHEC(S)" -ForegroundColor Red; exit 1 }
Write-Host "`nTOUT EST VERT." -ForegroundColor Green; exit 0
