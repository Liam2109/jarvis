# Harness B2B (15/11/2026) : cohérence de l'offre, contrats d'agents, garde, traces, surveillant, tests d'agents (tests\agents\test_*.py), sorties de Jarvis CEO.
# Silencieux : aucun réseau (127.0.0.1 au plus), aucun envoi Discord / Stripe / mail, traces dans un dossier temporaire. Code de sortie 0 = réussi.
$ErrorActionPreference = 'Continue'
$env:JARVIS_TEST = '1'; $env:PYTHONIOENCODING = 'utf-8'; $env:PYTHONDONTWRITEBYTECODE = '1'
$Root = Split-Path -Parent $PSScriptRoot
$env:JARVIS_HARNESS_LOGS = Join-Path $env:TEMP ('jarvis-test-harness-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
$echecs = 0
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }
$py = (Get-Command python -ErrorAction SilentlyContinue)
if (-not $py) { Write-Host '  OK    (python absent : harness sauté)'; exit 0 }
function Py([string[]]$a) { $o = & $py.Source @a 2>&1 | Out-String; return @{ code = $LASTEXITCODE; sortie = $o } }
try {
    Write-Host '1) Cohérence de l''offre (OFFRE-REFERENCE.json)'
    $r = Py @((Join-Path $PSScriptRoot 'coherence-offre.py'))
    Verifier ($r.code -eq 0) ("aucune faute nouvelle : " + (($r.sortie -split "`n" | Select-Object -Last 2) -join ' ').Trim())
    Write-Host '2) Contrats d''agents (contrat.schema.json)'
    $r = Py @((Join-Path $Root 'B2B\harness\valider.py'))
    Verifier ($r.code -eq 0) (($r.sortie -split "`n" | Where-Object { $_ -match 'contrats :|ECHEC' }) -join ' ').Trim()
    Write-Host '3) Tests d''agents (garde, appels-sid, résumé du soir, stripe-alerte, alertes de panne, rendez-vous, sorties de Jarvis CEO)'
    foreach ($t in Get-ChildItem (Join-Path $PSScriptRoot 'agents') -Filter 'test_*.py' | Sort-Object Name) {
        $sw = [Diagnostics.Stopwatch]::StartNew(); $r = Py @($t.FullName)
        Verifier ($r.code -eq 0) ("{0} ({1:N1} s){2}" -f $t.Name, $sw.Elapsed.TotalSeconds, $(if ($r.code -ne 0) { ' - ' + (($r.sortie -split "`n" | Where-Object { $_ -match 'Error|FAIL|assert' } | Select-Object -First 3) -join ' | ') }))
    }
    Write-Host '4) Surveillant en simulation (rien sur Discord)'
    $r = Py @((Join-Path $Root 'B2B\harness\surveillant.py'), 'verifier', '--simulation', '--maintenant', '2026-11-16T07:50')
    Verifier ($r.code -eq 0 -and $r.sortie -match '\[simulation\]') 'surveillant --simulation : rien posté, une trace écrite'
    $r = Py @((Join-Path $Root 'B2B\harness\rapport.py'))
    Verifier ($r.code -eq 0 -and $r.sortie -match '\| surveillant \| valide' -and $r.sortie -notmatch 'INVALIDE|MANQUANT') 'rapport.py : un contrat valide et des tests présents pour chaque agent'
} finally { Remove-Item -Recurse -Force $env:JARVIS_HARNESS_LOGS -ErrorAction SilentlyContinue; Remove-Item Env:JARVIS_HARNESS_LOGS -ErrorAction SilentlyContinue }
if ($echecs) { Write-Host "ÉCHEC : $echecs vérification(s) du harness." -ForegroundColor Red; exit 1 }
Write-Host 'OK : harness B2B vert.'; exit 0
