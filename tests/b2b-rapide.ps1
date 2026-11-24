# Passe RAPIDE du B2B (harness, 15/11/2026), moins de 60 s, pour l'usage quotidien : à lancer avant d'annoncer un résultat (« pas de preuve = pas de fait »).
# = harness (cohérence, contrats, garde, tests d'agents, surveillant) + tests Python courts des agents. La passe complète reste tests\tout.ps1 (≈ 25 min).
# (tests\rapide.ps1 existe déjà : il teste le chemin rapide vocal de Jarvis ; ce fichier-ci ne le remplace pas.)
$env:JARVIS_TEST = '1'; $env:PYTHONIOENCODING = 'utf-8'; $env:PYTHONDONTWRITEBYTECODE = '1'
$Root = Split-Path -Parent $PSScriptRoot; $sw = [Diagnostics.Stopwatch]::StartNew(); $rouge = 0
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'harness.ps1'); if ($LASTEXITCODE -ne 0) { $rouge++ }
Write-Host '5) Tests Python courts des agents B2B'
$py = (Get-Command python -ErrorAction SilentlyContinue)
foreach ($f in 'test_machine.py', 'test_stripe_alerte.py', 'test_resume_sid.py', 'test_rendez_vous.py', 'test_devis.py', 'test_reponses.py', 'test_appels_sid.py', 'test_leads_chauds.py') {
    $t = [Diagnostics.Stopwatch]::StartNew(); $o = & $py.Source (Join-Path $Root "B2B\agents\$f") 2>&1 | Out-String; $c = $LASTEXITCODE
    if ($c -eq 0) { Write-Host ("  OK    {0} ({1:N1} s)" -f $f, $t.Elapsed.TotalSeconds) } else { Write-Host ("  ECHEC {0} : {1}" -f $f, (($o -split "`n" | Select-Object -Last 2) -join ' ')) -ForegroundColor Red; $rouge++ }
}
Write-Host '6) Fiches Obsidian des agents : chaque contrat a sa note dans docs\agents (fiches-noms.json) et son bloc GENERE à jour, chaque agent actif a un skill'
& $py.Source (Join-Path $Root 'B2B\harness\generer-fiches.py') --verifier; if ($LASTEXITCODE -ne 0) { $rouge++ }
Write-Host '7) Graphe Obsidian : aucun lien cassé, liens vers les décisions identiques à git, une seule composante'
& $py.Source (Join-Path $Root 'B2B\harness\graphe.py'); if ($LASTEXITCODE -ne 0) { $rouge++ }
Write-Host '8) Architecture : agents, contrats, fiches, tâches serveur et carte du trajet du client à jour (règle d''ajout d''un agent)'
& $py.Source (Join-Path $Root 'B2B\harness\architecture.py') --verifier; if ($LASTEXITCODE -ne 0) { $rouge++ }
Write-Host ("Durée : {0:N0} s" -f $sw.Elapsed.TotalSeconds)
if ($rouge) { Write-Host "ROUGE : $rouge série(s) en échec." -ForegroundColor Red; exit 1 }
Write-Host 'VERT : passe rapide B2B réussie.' -ForegroundColor Green; exit 0
