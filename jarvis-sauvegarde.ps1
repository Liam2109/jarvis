# Sauvegarde de Jarvis : zip daté du dossier du projet, SANS le fichier .env (clés et jetons) ni les gros fichiers recréables.
#   powershell -ExecutionPolicy Bypass -File jarvis-sauvegarde.ps1                  -> C:\Users\Liam\Jarvis-sauvegardes\jarvis-AAAAMMJJ-HHMMSS.zip
#   powershell -ExecutionPolicy Bypass -File jarvis-sauvegarde.ps1 -Dossier D:\sauv  -> ailleurs
#   ... -Garder 10                                                                   -> ne garde que les 10 zips les plus récents de CE dossier
# Exclus : .env (jamais sauvegardé ici : gardez-le dans votre coffre), voix\models (modèle Vosk, à retélécharger), sounds\cache (voix pré-synthétisées),
#          .git. Inclus : scripts, config.json, memoire\ (notes, to-do, résumés, rappels), logs\ (journal), sounds\ (vos sons), README.
# Restauration : dézippez dans un dossier, copiez votre .env à côté de jarvis.ps1 et remettez le modèle Vosk dans voix\models.
param([string]$Dossier = 'C:\Users\Liam\Jarvis-sauvegardes', [string]$Source = '', [int]$Garder = 0)
$ErrorActionPreference = 'Stop'
if (-not $Source) { $Source = $PSScriptRoot }
$Source = (Resolve-Path $Source).Path.TrimEnd('\')
Add-Type -AssemblyName System.IO.Compression, System.IO.Compression.FileSystem
if (-not (Test-Path $Dossier)) { New-Item -ItemType Directory $Dossier -Force | Out-Null }
$zip = Join-Path $Dossier ("jarvis-{0}.zip" -f (Get-Date -Format 'yyyyMMdd-HHmmss'))
$exclus = @('^\.env$', '^\.env\..*(?<!\.example)$', '^voix\\models(\\|$)', '^sounds\\cache(\\|$)', '^\.git(\\|$)', '^quarantaine(\\|$)')
$n = 0; $octets = 0
$fs = [IO.File]::Open($zip, 'CreateNew'); $archive = New-Object IO.Compression.ZipArchive($fs, [IO.Compression.ZipArchiveMode]::Create)
try {
    foreach ($f in Get-ChildItem $Source -Recurse -File -Force) {
        $rel = $f.FullName.Substring($Source.Length + 1)
        if ($exclus | Where-Object { $rel -match $_ }) { continue }
        if ($f.FullName -like "$Dossier*") { continue }                                  # jamais le dossier des sauvegardes lui-même
        [void][IO.Compression.ZipFileExtensions]::CreateEntryFromFile($archive, $f.FullName, $rel.Replace('\', '/'), [IO.Compression.CompressionLevel]::Optimal)
        $n++; $octets += $f.Length
    }
} finally { $archive.Dispose(); $fs.Dispose() }
# Contrôle : le zip ne doit contenir AUCUN fichier de secrets
$z = [IO.Compression.ZipFile]::OpenRead($zip)
try { $interdits = @($z.Entries | Where-Object { $_.FullName -match '(^|/)\.env$|(^|/)\.env\.(?!example)' }); $nb = $z.Entries.Count } finally { $z.Dispose() }
if ($interdits.Count) { Remove-Item $zip -Force; throw "ARRÊT : le zip contenait .env, il a été supprimé." }
if ($Garder -gt 0) { Get-ChildItem $Dossier -Filter 'jarvis-*.zip' | Sort-Object LastWriteTime -Descending | Select-Object -Skip $Garder | Remove-Item -Force }
Write-Host ("Sauvegarde créée : {0}  ({1} fichiers, {2:N1} Mo avant compression, {3:N1} Mo après) — .env exclu." -f $zip, $nb, ($octets / 1MB), ((Get-Item $zip).Length / 1MB))
