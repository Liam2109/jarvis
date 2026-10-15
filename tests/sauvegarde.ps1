# Test de jarvis-sauvegarde.ps1 sur un FAUX dossier (dans %TEMP%) : le zip ne contient jamais .env. Silencieux. Code de sortie 0 = réussi.
$ErrorActionPreference = 'Stop'
$env:JARVIS_TEST = '1'
$Root = Split-Path -Parent $PSScriptRoot
$echecs = 0
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }
$tmp = Join-Path $env:TEMP "jarvis-test-sauv-$([guid]::NewGuid().ToString('N'))"
$src = Join-Path $tmp 'faux-jarvis'; $dest = Join-Path $tmp 'sauvegardes'
New-Item -ItemType Directory $src, "$src\voix\models\m", "$src\sounds\cache", "$src\memoire", "$src\lib" | Out-Null
'SECRET=abcdef123456' | Set-Content "$src\.env"; 'SECRET2=zzz' | Set-Content "$src\.env.local"; 'X=xxx' | Set-Content "$src\.env.example"
'ok' | Set-Content "$src\jarvis.ps1"; 'n' | Set-Content "$src\memoire\notes.md"; 'm' | Set-Content "$src\voix\models\m\gros.bin"; 'c' | Set-Content "$src\sounds\cache\a.mp3"; 'l' | Set-Content "$src\lib\a.ps1"
Write-Host '1) Sauvegarde d''un faux dossier'
$sortie = & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Root 'jarvis-sauvegarde.ps1') -Dossier $dest -Source $src 2>&1 | Out-String
$zip = @(Get-ChildItem $dest -Filter 'jarvis-*.zip')
Verifier ($zip.Count -eq 1 -and $zip[0].Name -match '^jarvis-\d{8}-\d{6}\.zip$') 'un zip daté est créé'
Add-Type -AssemblyName System.IO.Compression.FileSystem
$z = [IO.Compression.ZipFile]::OpenRead($zip[0].FullName); $noms = @($z.Entries | ForEach-Object FullName); $z.Dispose()
Verifier (-not ($noms -contains '.env') -and -not ($noms -contains '.env.local')) 'le zip NE CONTIENT PAS .env (ni .env.local)'
Verifier ($noms -contains '.env.example') '.env.example (sans secret) est sauvegardé'
Verifier (($noms -contains 'jarvis.ps1') -and ($noms -contains 'memoire/notes.md') -and ($noms -contains 'lib/a.ps1')) 'scripts et mémoire sauvegardés'
Verifier (-not ($noms | Where-Object { $_ -match '^voix/models|^sounds/cache' })) 'modèle Vosk et cache vocal exclus (recréables)'
Verifier ($sortie -match '\.env exclu') 'le message le confirme'
Write-Host '2) Garder N sauvegardes'
Start-Sleep -Seconds 1; & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Root 'jarvis-sauvegarde.ps1') -Dossier $dest -Source $src -Garder 1 | Out-Null
Verifier (@(Get-ChildItem $dest -Filter 'jarvis-*.zip').Count -eq 1) '-Garder 1 : seul le plus récent reste'
Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
if ($echecs) { Write-Host "`nÉCHEC : $echecs vérification(s) en échec." -ForegroundColor Red; exit 1 }
Write-Host "`nRÉUSSI"; exit 0
