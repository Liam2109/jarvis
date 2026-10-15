# Fenêtre de déverrouillage Bitwarden — processus SÉPARÉ de Jarvis (la boucle principale ne s'arrête jamais).
# Votre mot de passe principal n'existe que dans CE processus, quelques secondes : il passe à `bw` par une variable d'environnement du
# processus fils (jamais en argument, jamais sur le disque, jamais journalisé, jamais lu à voix haute) et n'est PAS renvoyé à Jarvis.
# Sortie (une seule ligne, ASCII) :  SESSION:<jeton>   |   ERREUR:<message>   |   ANNULE
param(
    [ValidateSet('login', 'unlock')][string]$Mode = 'unlock',
    [string]$Email = '',
    [string]$SimuleResultat = '',     # RÉSERVÉ AUX TESTS : renvoie ce résultat sans fenêtre ni mot de passe
    [int]$SimuleSecondes = 0
)
$ErrorActionPreference = 'Stop'
if ($SimuleResultat) { Start-Sleep -Seconds $SimuleSecondes; Write-Output $SimuleResultat; exit 0 }
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

function Find-BwCmd {
    $g = Get-Command bw -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $g) { return $null }
    $c = [IO.Path]::ChangeExtension($g.Source, '.cmd'); if (Test-Path $c) { return $c }
    if ($g.Source -match '\.exe$') { return $g.Source }
    $null
}

function Invoke-BwLocal([string[]]$arguments, [hashtable]$env2, [int]$timeoutSec = 90) {
    $bw = Find-BwCmd; if (-not $bw) { return @{ code = 127; out = ''; err = 'bw introuvable' } }
    $a = ($arguments | ForEach-Object { if ($_ -match '[\s"&|<>^]') { '"' + ($_ -replace '"', '') + '"' } else { $_ } }) -join ' '
    $psi = New-Object Diagnostics.ProcessStartInfo 'cmd.exe', ('/c ""' + $bw + '" ' + $a + ' --nointeraction"')
    $psi.UseShellExecute = $false; $psi.CreateNoWindow = $true; $psi.RedirectStandardOutput = $true; $psi.RedirectStandardError = $true
    foreach ($k in $env2.Keys) { $psi.EnvironmentVariables[$k] = $env2[$k] }
    $p = [Diagnostics.Process]::Start($psi)
    $so = $p.StandardOutput.ReadToEndAsync(); $se = $p.StandardError.ReadToEndAsync()
    if (-not $p.WaitForExit($timeoutSec * 1000)) { try { $p.Kill() } catch {}; return @{ code = -1; out = ''; err = 'délai dépassé' } }
    @{ code = $p.ExitCode; out = $so.Result.Trim(); err = $se.Result.Trim() }
}

$besoinEmail = ($Mode -eq 'login')
$f = New-Object Windows.Forms.Form
$f.Text = 'Jarvis - Coffre Bitwarden'; $f.StartPosition = 'CenterScreen'; $f.TopMost = $true
$f.FormBorderStyle = 'FixedDialog'; $f.MaximizeBox = $false; $f.MinimizeBox = $false
$f.BackColor = [Drawing.Color]::FromArgb(14, 20, 30); $f.ForeColor = [Drawing.Color]::FromArgb(160, 225, 255)
$script:yy = 12
function Add-Champ([string]$txt, [bool]$masque) {
    $l = New-Object Windows.Forms.Label; $l.Text = $txt; $l.Location = New-Object Drawing.Point(12, $script:yy); $l.AutoSize = $true; $f.Controls.Add($l)
    $t = New-Object Windows.Forms.TextBox; $t.Location = New-Object Drawing.Point(12, ($script:yy + 20)); $t.Width = 336
    $t.BackColor = [Drawing.Color]::FromArgb(24, 34, 48); $t.ForeColor = [Drawing.Color]::White; if ($masque) { $t.UseSystemPasswordChar = $true }
    $f.Controls.Add($t); $script:yy += 52; $t
}
$tEmail = $null; $tCode = $null
if ($besoinEmail) { $tEmail = Add-Champ 'E-mail du compte Bitwarden' $false; $tEmail.Text = $Email }
$tPwd = Add-Champ 'Mot de passe principal (reste dans cette fenêtre, jamais enregistré)' $true
if ($besoinEmail) { $tCode = Add-Champ 'Code à deux facteurs (si activé, sinon vide)' $false }
$ok = New-Object Windows.Forms.Button; $ok.Text = 'Déverrouiller'; $ok.Location = New-Object Drawing.Point(190, ($script:yy - 4)); $ok.Width = 158; $ok.DialogResult = 'OK'
$ok.BackColor = [Drawing.Color]::FromArgb(0, 120, 170); $ok.ForeColor = [Drawing.Color]::White; $ok.FlatStyle = 'Flat'
$ko = New-Object Windows.Forms.Button; $ko.Text = 'Plus tard'; $ko.Location = New-Object Drawing.Point(12, ($script:yy - 4)); $ko.Width = 100; $ko.DialogResult = 'Cancel'
$f.Controls.AddRange(@($ok, $ko)); $f.AcceptButton = $ok; $f.CancelButton = $ko
$f.ClientSize = New-Object Drawing.Size(360, ($script:yy + 36))
$f.Add_Shown({ $f.Activate(); $tPwd.Focus() })
$res = $f.ShowDialog()
if ($res -ne 'OK' -or -not $tPwd.Text) { Write-Output 'ANNULE'; exit 0 }
$pwd2 = $tPwd.Text; $email2 = if ($tEmail) { $tEmail.Text.Trim() } else { ''}; $code2 = if ($tCode) { $tCode.Text.Trim() } else { '' }
$f.Dispose()
try {
    $env2 = @{ JARVIS_BW_PWD = $pwd2 }
    if ($Mode -eq 'login') {
        if (-not $email2) { Write-Output 'ERREUR:adresse e-mail manquante'; exit 0 }
        $a = @('login', $email2, '--passwordenv', 'JARVIS_BW_PWD', '--raw'); if ($code2) { $a += @('--method', '0', '--code', $code2) }
        $r = Invoke-BwLocal $a $env2 90
    } else { $r = Invoke-BwLocal @('unlock', '--passwordenv', 'JARVIS_BW_PWD', '--raw') $env2 60 }
    if ($r.code -ne 0 -or -not $r.out) { $m = ("$($r.err)" -replace '\s+', ' '); if ($pwd2) { $m = $m.Replace($pwd2, '[SECRET]') }; if ($m.Length -gt 150) { $m = $m.Substring(0, 150) }; Write-Output ("ERREUR:" + ($m -replace '[^\x20-\x7E]', '?')); exit 0 }
    $sync = Invoke-BwLocal @('sync') @{ BW_SESSION = $r.out.Trim() } 90
    Write-Output ('SESSION:' + $r.out.Trim())
} finally { $pwd2 = $null; $env2 = $null; $tPwd.Text = '' }
