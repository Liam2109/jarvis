# Test : pas d'écran blanc au lancement. Un processus fils filme (≈ 14 images/s) la zone de travail de l'écran choisi pendant que l'orbe démarre ;
# on compare la proportion de pixels quasi blancs à celle d'avant le lancement. Code de sortie 0 = réussi.
param([ValidateSet('tableau', 'discret')][string]$Mode = 'tableau')
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $Root 'lib\journal.ps1')
$Config = Get-Content (Join-Path $Root 'config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$Config.visage_port = 47632; $Config.mode_affichage = $Mode
. (Join-Path $Root 'lib\voix.ps1'); . (Join-Path $Root 'lib\business.ps1'); . (Join-Path $Root 'lib\permissions.ps1')
. (Join-Path $Root 'lib\actions.ps1'); . (Join-Path $Root 'lib\entrees.ps1'); . (Join-Path $Root 'lib\ecrans.ps1'); . (Join-Path $Root 'lib\tableau.ps1'); . (Join-Path $Root 'lib\visage.ps1')
Write-Host "Mode testé : $Mode"

$ecran = (Select-Ecran $Config.ecran_jarvis).ecran
$z = $ecran.zone
# Région filmée : toute la zone de travail (tableau) ou le coin de 320x320 où se trouve l'orbe (discret : sinon un flash resterait sous le seuil)
$reg = if ($Mode -eq 'discret') { @{ X = $z.Right - 320; Y = $z.Bottom - 320; W = 320; H = 320 } } else { @{ X = $z.X; Y = $z.Y; W = $z.Width; H = $z.Height } }
$csv = Join-Path $env:TEMP 'jarvis-flash.csv'
Remove-Item $csv -ErrorAction SilentlyContinue
$code = @"
Add-Type -AssemblyName System.Drawing
`$z = @{ X = $($reg.X); Y = $($reg.Y); W = $($reg.W); H = $($reg.H) }
`$full = New-Object Drawing.Bitmap `$z.W, `$z.H; `$gf = [Drawing.Graphics]::FromImage(`$full)
`$small = New-Object Drawing.Bitmap 64, 36; `$gs = [Drawing.Graphics]::FromImage(`$small)
`$sw = [Diagnostics.Stopwatch]::StartNew(); `$out = New-Object System.Collections.Generic.List[string]
while (`$sw.Elapsed.TotalSeconds -lt 13) {
  `$gf.CopyFromScreen(`$z.X, `$z.Y, 0, 0, `$full.Size); `$gs.DrawImage(`$full, 0, 0, 64, 36)
  `$blanc = 0; `$n = 0
  for (`$y = 0; `$y -lt 36; `$y++) { for (`$x = 0; `$x -lt 64; `$x++) { `$p = `$small.GetPixel(`$x, `$y); `$l = 0.299 * `$p.R + 0.587 * `$p.G + 0.114 * `$p.B; if (`$l -gt 235) { `$blanc++ }; `$n++ } }
  `$out.Add(('{0},{1:N3}' -f [int]`$sw.Elapsed.TotalMilliseconds, (`$blanc / `$n)))
  Start-Sleep -Milliseconds 20
}
[IO.File]::WriteAllLines('$csv', `$out)
"@
$film = Start-Process powershell -ArgumentList '-NoProfile', '-WindowStyle', 'Hidden', '-Command', $code -PassThru
$echecs = 0
try {
    Start-Sleep -Milliseconds 2500                      # état de départ filmé avant le lancement
    Start-Visage
    $temoin = $null
    if ($env:JARVIS_TEST_TEMOIN) {   # contrôle du détecteur : une page blanche volontaire (processus Edge à part, profil jetable) DOIT faire échouer le test
        $codeT = "Add-Type -AssemblyName System.Windows.Forms; Add-Type -ReferencedAssemblies System.Windows.Forms -TypeDefinition 'public class FW : System.Windows.Forms.Form { protected override bool ShowWithoutActivation { get { return true; } } }'; `$f = New-Object FW; `$f.FormBorderStyle = 'None'; `$f.StartPosition = 'Manual'; `$f.Bounds = New-Object Drawing.Rectangle($($z.X), $($z.Y), $($z.Width), $($z.Height)); `$f.BackColor = [Drawing.Color]::White; `$f.TopMost = `$true; `$t = New-Object Windows.Forms.Timer; `$t.Interval = 2500; `$t.Add_Tick({ `$f.Close() }); `$t.Start(); [Windows.Forms.Application]::Run(`$f)"
        Start-Sleep -Milliseconds 800
        $temoin = Start-Process powershell -ArgumentList '-NoProfile', '-WindowStyle', 'Hidden', '-Command', $codeT -PassThru
        Write-Host '  (témoin : fenêtre blanche volontaire de 2,5 s sur toute la zone de travail)'
    }
    for ($i = 0; $i -lt 28; $i++) { Invoke-PumpVisage; Start-Sleep -Milliseconds 250 }
    if ($temoin -and -not $temoin.HasExited) { Stop-Process -Id $temoin.Id -Force -ErrorAction SilentlyContinue }
    [void]$film.WaitForExit(20000)
} finally { try { Stop-Visage } catch {}; if (-not $film.HasExited) { Stop-Process -Id $film.Id -Force -ErrorAction SilentlyContinue } }

if (-not (Test-Path $csv)) { Write-Host 'ECHEC : aucune image enregistrée' -ForegroundColor Red; exit 1 }
$f = Get-Content $csv | ForEach-Object { $p = $_.Split(','); [pscustomobject]@{ t = [int]$p[0]; blanc = [double]($p[1] -replace ',', '.') } }
$base = ($f | Where-Object { $_.t -lt 2000 } | Measure-Object blanc -Average).Average
$max = ($f | Where-Object { $_.t -ge 2000 } | Measure-Object blanc -Maximum).Maximum
Write-Host ("  {0} images filmées ; part de pixels blancs : départ {1:P0}, maximum ensuite {2:P0}" -f $f.Count, $base, $max)
# Flash = hausse de blanc très au-dessus de l'état de départ (le tableau est sombre, l'orbe discrète couvre peu de pixels)
$seuil = [math]::Min(0.95, $base + 0.15)
$flash = @($f | Where-Object { $_.t -ge 2000 -and $_.blanc -gt $seuil })
if ($flash.Count) { Write-Host ("  ECHEC {0} image(s) avec flash blanc (> {1:P0}), première à {2} ms" -f $flash.Count, $seuil, $flash[0].t) -ForegroundColor Red; $echecs++ }
else { Write-Host "  OK    aucun flash blanc (seuil $([int]($seuil * 100)) % de pixels blancs)" }
if ($echecs) { Write-Host "`nÉCHEC" -ForegroundColor Red; exit 1 }
Write-Host "`nRÉUSSI"; exit 0
