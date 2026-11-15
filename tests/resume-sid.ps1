# Test SILENCIEUX de l'agent resume-sid (résumé Discord du soir : appels Sid + chiffre d'affaires Stripe) : fichiers présents, simulation par défaut dans le fichier versionné,
# aucune action d'écriture sur Stripe ni d'envoi à une entreprise dans le code, branchement dans tests\tout.ps1 ; puis les tests Python hors ligne (faux fichiers, dossiers temporaires, aucun réseau).
$ErrorActionPreference = 'Stop'
$env:JARVIS_TEST = '1'
$Root = Split-Path -Parent $PSScriptRoot
$echecs = 0
function Get-Instantane([string]$f) { if (Test-Path -LiteralPath $f) { $i = Get-Item -LiteralPath $f; "$($i.Length):$($i.LastWriteTimeUtc.Ticks)" } else { 'absent' } }      # un fichier d'agent (état, journal) peut déjà exister (portable serveur : l'agent tourne pour de vrai) : les tests ne doivent pas le CHANGER, pas exiger qu'il n'existe pas
$ag0 = Join-Path $Root 'B2B\agents'; $avantFic = @{}; foreach ($n in 'resume-sid-etat.json', 'resume-sid-journal.log') { $avantFic[$n] = Get-Instantane (Join-Path $ag0 $n) }
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }
$hashConfig = (Get-FileHash (Join-Path $Root 'config.json')).Hash
$ag = Join-Path $Root 'B2B\agents'

Write-Host '1. Fichiers et réglages'
foreach ($f in 'resume-sid.py', 'resume-sid-config.json', 'resume-sid.md', 'test_resume_sid.py') { Verifier (Test-Path (Join-Path $ag $f)) "B2B\agents\$f présent" }
$cfgAgent = Get-Content (Join-Path $ag 'resume-sid-config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
Verifier ($cfgAgent.envoi_automatique -eq $false) 'resume-sid-config.json : envoi_automatique = false par défaut (fichier versionné ; activation réelle par machine dans resume-sid-config.local.json, ignoré par git)'
Verifier ($cfgAgent.heure_tache -eq '19:30') 'resume-sid-config.json : heure_tache = 19:30 (jours ouvrés, étape Argent du 15/11/2026)'
$src = Get-Content (Join-Path $ag 'resume-sid.py') -Raw -Encoding UTF8
Verifier ($src -notmatch 'smtplib|send_message|gmail_api|webbrowser|os\.system|shell=True|places\.googleapis|stripe\.com/v1/(refunds|payouts|transfers|customers)') 'resume-sid.py : aucun envoi d''e-mail ni de message à une entreprise, aucune écriture Stripe (lecture seule)'
Verifier ($src -match 'lire_feuille' -and $src -notmatch 'creer_feuille|creer_dossier|partager\(') 'resume-sid.py : lit la feuille Google de Sid, n''en crée ni n''en partage aucune (lecture seule)'
# Diagnostic seulement (ne compte pas dans $echecs) : l'activation réelle (tâche planifiée) varie d'une machine à l'autre et ne doit jamais bloquer tests\tout.ps1 / maj-auto.ps1
$tacheReelle = Get-ScheduledTask -TaskName 'Jarvis-ResumeSid' -ErrorAction SilentlyContinue
Write-Host "  INFO  tâche planifiée Jarvis-ResumeSid : $(if ($tacheReelle) { 'installée sur cette machine' } else { 'non installée sur cette machine' })"
$tout = Get-Content (Join-Path $Root 'tests\tout.ps1') -Raw -Encoding UTF8
Verifier ($tout -match "f = 'resume-sid\.ps1'") 'tests\tout.ps1 lance ce test'

Write-Host '2. Tests Python de l''agent (hors ligne)'
$py = Get-Command python -ErrorAction SilentlyContinue
if ($py) {
    $env:PYTHONIOENCODING = 'utf-8'
    $sortie = & $py.Source -I (Join-Path $ag 'test_resume_sid.py') 2>&1 | Out-String
    Verifier ($LASTEXITCODE -eq 0 -and $sortie -match 'OK : tous les tests de l''agent resume-sid passent') 'agents\test_resume_sid.py : tous les tests passent'
    Remove-Item Env:PYTHONIOENCODING -ErrorAction SilentlyContinue
} else { Write-Host '  (python introuvable : tests Python sautés)' }
foreach ($f in 'resume-sid-etat.json', 'resume-sid-journal.log') { Verifier ((Get-Instantane (Join-Path $ag0 $f)) -eq $avantFic[$f]) "aucun $f écrit dans le dépôt par les tests (un fichier existant est inchangé)" }

Write-Host '3. Propreté'
Verifier ((Get-FileHash (Join-Path $Root 'config.json')).Hash -eq $hashConfig) 'config.json inchangé'
if ($echecs) { Write-Host "`n$echecs ÉCHEC(S)" -ForegroundColor Red; exit 1 }
Write-Host "`nTOUT EST VERT." -ForegroundColor Green; exit 0
