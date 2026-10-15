# Test : l'orbe ne doit modifier AUCUNE autre fenêtre que la sienne.
#   powershell -NoProfile -File tests\fenetres.ps1      -> code de sortie 0 = réussi, 1 = ÉCHEC
# 1) garde-fou : Habiller/Deplacer/Montrer refusent un faux "JarvisOrb-..." (mauvais PID) et un titre en "Jarvis..." quelconque
# 2) lancement réel de l'orbe, puis comparaison avant/après du style, style étendu, position, région de TOUTES les autres fenêtres visibles
param([ValidateSet('tableau', 'discret')][string]$Mode = 'tableau')
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $Root 'lib\journal.ps1')
$Config = Get-Content (Join-Path $Root 'config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$Config.visage_port = 47631     # port de test, distinct de celui de Jarvis
$Config.mode_affichage = $Mode
. (Join-Path $Root 'lib\voix.ps1'); . (Join-Path $Root 'lib\business.ps1'); . (Join-Path $Root 'lib\permissions.ps1')
. (Join-Path $Root 'lib\actions.ps1'); . (Join-Path $Root 'lib\entrees.ps1'); . (Join-Path $Root 'lib\ecrans.ps1'); . (Join-Path $Root 'lib\tableau.ps1'); . (Join-Path $Root 'lib\visage.ps1')
Write-Host "Mode testé : $Mode"

Add-Type -TypeDefinition @'
using System; using System.Text; using System.Collections.Generic; using System.Runtime.InteropServices;
public class JarvisSnap {
  delegate bool EP(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] static extern bool EnumWindows(EP p, IntPtr l);
  [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern int GetClassName(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] static extern int GetWindowLong(IntPtr h, int i);
  [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] static extern bool GetWindowRect(IntPtr h, out RC r);
  [DllImport("user32.dll")] static extern int GetWindowRgn(IntPtr h, IntPtr r);
  [DllImport("user32.dll")] static extern IntPtr GetForegroundWindow();
  public static string TitrePremierPlan() { var t = new StringBuilder(256); GetWindowText(GetForegroundWindow(), t, 256); return t.ToString(); }
  public static string PremierPlan() { IntPtr h = GetForegroundWindow(); var t = new StringBuilder(256); GetWindowText(h, t, 256); uint pid; GetWindowThreadProcessId(h, out pid); return "pid " + pid + " | hwnd " + (long)h + " | « " + t + " »"; }
  [DllImport("gdi32.dll")] static extern IntPtr CreateRectRgn(int a, int b, int c, int d);
  [DllImport("gdi32.dll")] static extern bool DeleteObject(IntPtr o);
  [StructLayout(LayoutKind.Sequential)] struct RC { public int L, T, R, B; }
  public static List<string> Liste() {
    var l = new List<string>();
    EnumWindows((h, p) => {
      if (!IsWindowVisible(h)) return true;
      var t = new StringBuilder(256); GetWindowText(h, t, 256); uint pid; GetWindowThreadProcessId(h, out pid);
      RC r; GetWindowRect(h, out r); IntPtr rg = CreateRectRgn(0, 0, 0, 0); int rr = GetWindowRgn(h, rg); DeleteObject(rg);
      var c = new StringBuilder(64); GetClassName(h, c, 64);
      l.Add(((long)h) + "|" + pid + "|" + GetWindowLong(h, -16).ToString("X") + "|" + GetWindowLong(h, -20).ToString("X") + "|" + r.L + "," + r.T + "," + r.R + "," + r.B + "|" + (rr > 0 ? "rgn" : "-") + "|" + c + "|" + t);
      return true;
    }, IntPtr.Zero);
    return l;
  }
}
'@

function Get-Fenetres {
    $d = @{}
    foreach ($l in [JarvisSnap]::Liste()) { $p = $l.Split('|', 8); $d[$p[0]] = [pscustomobject]@{ hwnd = $p[0]; pid = $p[1]; style = $p[2]; ex = $p[3]; rect = $p[4]; rgn = $p[5]; classe = $p[6]; titre = $p[7] } }
    $d
}

$echecs = New-Object System.Collections.Generic.List[string]
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $echecs.Add($msg) } }

# Fenêtre leurre dans un AUTRE processus
$titreLeurre = 'JarvisOrb-leurre01'
$codeLeurre = "Add-Type -AssemblyName System.Windows.Forms; Add-Type -ReferencedAssemblies System.Windows.Forms -TypeDefinition 'public class FS : System.Windows.Forms.Form { protected override bool ShowWithoutActivation { get { return true; } } }'; `$f = New-Object FS; `$f.Text = '$titreLeurre'; `$f.Width = 300; `$f.Height = 200; `$f.StartPosition = 'Manual'; `$f.Location = New-Object Drawing.Point(200, 200); `$t = New-Object Windows.Forms.Timer; `$t.Interval = 90000; `$t.Add_Tick({ `$f.Close() }); `$t.Start(); [Windows.Forms.Application]::Run(`$f)"
$leurre = Start-Process powershell -ArgumentList '-NoProfile', '-WindowStyle', 'Hidden', '-Command', $codeLeurre -PassThru
$leurre2 = $null
try {
    $hL = [IntPtr]::Zero; $fin = (Get-Date).AddSeconds(15)
    while ($hL -eq [IntPtr]::Zero -and (Get-Date) -lt $fin) {
        Start-Sleep -Milliseconds 300
        $f = (Get-Fenetres).Values | Where-Object { $_.titre -eq $titreLeurre } | Select-Object -First 1
        if ($f) { $hL = [IntPtr][long]$f.hwnd }
    }
    Verifier ($hL -ne [IntPtr]::Zero) 'fenêtre leurre créée'

    Write-Host '1) Garde-fou sur le leurre (titre JarvisOrb-... mais mauvais processus)'
    [JarvisWin]::Autoriser($null, [uint32[]]@())
    Verifier (-not [JarvisWin]::PlacerZone($hL, 0, 0, 300, 300, $false)) 'PlacerZone refusé sans autorisation'
    Verifier (-not [JarvisWin]::PlacerCoin($hL, 1000, 1000, 24, 260, 260, $false)) 'PlacerCoin refusé sans autorisation'
    [JarvisWin]::Autoriser($titreLeurre, [uint32[]]@([uint32]$PID))      # bon titre, mais PID autorisé = ce script, pas le leurre
    Verifier (-not [JarvisWin]::PlacerZone($hL, 0, 0, 300, 300, $true)) 'PlacerZone refusé : titre identique mais mauvais PID'
    Verifier (-not [JarvisWin]::PlacerCoin($hL, 1000, 1000, 24, 260, 260, $true)) 'PlacerCoin refusé : titre identique mais mauvais PID'
    Verifier (-not [JarvisWin]::Montrer($hL, $false)) 'Montrer(masquer) refusé : mauvais PID'
    Verifier (-not [JarvisWin]::Montrer($hL, $true)) 'Montrer(afficher/devant) refusé : mauvais PID'
    Verifier ([JarvisWin]::Trouver() -eq [IntPtr]::Zero) 'Trouver ne renvoie pas le leurre'
    [JarvisWin]::Autoriser($null, [uint32[]]@())

    Write-Host '2) Lancement réel de l''orbe, comparaison avant/après de toutes les autres fenêtres'
    $avant = Get-Fenetres
    $fgAvant = [JarvisSnap]::PremierPlan()
    Write-Host "  Focus AVANT le lancement           : $fgAvant"
    Start-Visage
    for ($i = 0; $i -lt 6; $i++) { Invoke-PumpVisage; Start-Sleep -Milliseconds 250 }       # laisse le focus se stabiliser
    $hOrbe = $script:VisageHwnd
    Verifier ($hOrbe -ne [IntPtr]::Zero) "orbe trouvée par PID + titre unique ($script:TitreOrbe)"
    # Focus : l'orbe peut le prendre UNE fois au lancement (toléré). Ensuite il ne doit plus bouger.
    $fgLancement = [JarvisSnap]::PremierPlan()
    Write-Host "  Focus APRÈS le lancement           : $fgLancement"
    $pidsOrbe = [uint32[]](Get-ArbrePids $script:EdgePid)
    $fgPid = [uint32](($fgLancement -split '\|')[0] -replace '[^\d]', '')
    Verifier (($fgLancement -eq $fgAvant) -or ($pidsOrbe -contains $fgPid)) 'au lancement, le focus est resté ou est passé à l''orbe (rien d''autre)'
    if ($fgLancement -ne $fgAvant) { Write-Host '  (toléré) l''orbe a pris le focus une seule fois au lancement' }
    for ($i = 0; $i -lt 20; $i++) { Invoke-PumpVisage; Start-Sleep -Milliseconds 250 }       # 5 s de plus
    $fgFinal = [JarvisSnap]::PremierPlan()
    Write-Host "  Focus 5 s plus tard                : $fgFinal"
    Verifier ($fgFinal -eq $fgLancement) 'le focus ne change plus après le lancement'
    if ($env:JARVIS_TEST_SABOTAGE) {   # auto-vérification du test : on modifie volontairement le leurre, le test DOIT échouer
        Add-Type -MemberDefinition '[DllImport("user32.dll")] public static extern int GetWindowLong(IntPtr h, int i); [DllImport("user32.dll")] public static extern int SetWindowLong(IntPtr h, int i, int v);' -Name Sab -Namespace JarvisTest
        [void][JarvisTest.Sab]::SetWindowLong($hL, -20, ([JarvisTest.Sab]::GetWindowLong($hL, -20) -bor 0x80))
        Write-Host '  (sabotage volontaire du leurre)'
    }
    $apres = Get-Fenetres
    if ($hOrbe -ne [IntPtr]::Zero) {
        $o = $apres[[string][long]$hOrbe]
        Verifier ($o -and $o.titre -eq $script:TitreOrbe) 'la fenêtre de l''orbe porte le titre unique'
        Verifier ($o -and $o.rgn -eq '-') 'aucune région de fenêtre (fenêtre rectangulaire)'
        Verifier ($o -and (([Convert]::ToInt64($o.ex, 16) -band 0x8) -eq 0)) 'pas « toujours au premier plan » par défaut'
        # Position : sur l'écran choisi, dans sa zone de travail (barre des tâches visible)
        $geo = Get-GeometrieVisage $script:EcranVisage $Mode ([int]$Config.visage_taille)
        $z = $script:EcranVisage.zone; $b = $script:EcranVisage.bounds
        $rc = $o.rect.Split(',') | ForEach-Object { [int]$_ }      # gauche, haut, droite, bas
        $ok8 = { param($a, $b2) [math]::Abs($a - $b2) -le 8 }
        if ($Mode -eq 'tableau' -and (Get-PleinEcranVisage)) {
            Verifier ((& $ok8 $rc[0] $b.X) -and (& $ok8 $rc[1] $b.Y) -and (& $ok8 $rc[2] ($b.X + $b.Width)) -and (& $ok8 $rc[3] ($b.Y + $b.Height))) "PLEIN ÉCRAN sur l'écran choisi ($($b.Width)x$($b.Height) en $($b.X),$($b.Y)) : obtenu $($o.rect)"
        } elseif ($Mode -eq 'tableau') {
            Verifier ((& $ok8 $rc[0] $z.X) -and (& $ok8 $rc[1] $z.Y) -and (& $ok8 $rc[2] ($z.X + $z.Width)) -and (& $ok8 $rc[3] ($z.Y + $z.Height))) "tableau = zone de travail de l'écran choisi ($($z.Width)x$($z.Height) en $($z.X),$($z.Y)) : obtenu $($o.rect)"
            Verifier ($rc[3] -le ($b.Y + $b.Height) - ($b.Height - $z.Height) + 8) 'la barre des tâches reste visible (le tableau ne la recouvre pas)'
        } else {
            $largeur = $rc[2] - $rc[0]
            Verifier ($largeur -ge 260 -and $largeur -le 300) "orbe discrète : largeur de fenêtre $largeur px (zone cliente 260)"
            Verifier ((& $ok8 $rc[2] ($z.X + $z.Width - 24)) -and (& $ok8 $rc[3] ($z.Y + $z.Height - 24))) "orbe discrète en bas à droite de la zone de travail (marge 24) : obtenu $($o.rect)"
        }
        Verifier ($rc[0] -ge ($b.X - 8) -and $rc[2] -le ($b.X + $b.Width + 8) -and $rc[1] -ge ($b.Y - 8) -and $rc[3] -le ($b.Y + $b.Height + 8)) "la fenêtre reste entièrement sur l'écran choisi ($($script:EcranVisage.peripherique))"
    }
    foreach ($k in $avant.Keys) {
        $a = $avant[$k]
        if ($hOrbe -ne [IntPtr]::Zero -and $k -eq [string][long]$hOrbe) { continue }
        if (-not $apres.ContainsKey($k)) { continue }          # fenêtre fermée par l'utilisateur : pas une modification de notre part
        $b = $apres[$k]
        $diff = @(); foreach ($c in 'style', 'ex', 'rect', 'rgn') { if ($a.$c -ne $b.$c) { $diff += "$c $($a.$c) -> $($b.$c)" } }
        Verifier ($diff.Count -eq 0) ("fenêtre inchangée : « $($a.titre) » [$($a.classe)] (pid $($a.pid))" + $(if ($diff.Count) { ' | ' + ($diff -join ' ; ') }))
    }
    Verifier ($apres.ContainsKey([string][long]$hL)) 'le leurre existe toujours'
} finally {
    try { Stop-Visage } catch {}
    foreach ($p in $leurre, $leurre2) { if ($p -and -not $p.HasExited) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue } }
}

if ($echecs.Count) { Write-Host "`nÉCHEC : $($echecs.Count) vérification(s) en échec." -ForegroundColor Red; exit 1 }
Write-Host "`nRÉUSSI : seule la fenêtre de l'orbe a été modifiée."; exit 0
