# Visage : serveur HTTP local (127.0.0.1 + jeton) + fenêtre Edge (--app) sur l'écran choisi + icône de barre système.
# Modes (config.json "mode_affichage") : "tableau" = tableau de bord en PLEIN ÉCRAN (jarvis_plein_ecran, true par défaut) sur l'écran choisi (ecran_jarvis, « principal » par défaut ; F11 bascule plein écran / fenêtre) ;
# "discret" = petit orbe 260x260 en bas à droite de cet écran. L'orbe peut prendre le focus UNE fois au lancement (accepté) ; jamais SetForegroundWindow sur une autre fenêtre.
# Garde-fou : seule la fenêtre au titre unique JarvisOrb-xxxx appartenant au processus Edge lancé par Jarvis peut être trouvée ou modifiée.
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type -TypeDefinition @'
using System; using System.Text; using System.Collections.Generic; using System.Runtime.InteropServices;
public class JarvisWin {
  delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] static extern bool EnumWindows(EnumProc p, IntPtr l);
  [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] static extern bool SetWindowPos(IntPtr h, IntPtr a, int x, int y, int cx, int cy, uint f);
  [DllImport("user32.dll")] static extern bool ShowWindow(IntPtr h, int c);
  [DllImport("user32.dll")] static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] static extern bool GetClientRect(IntPtr h, out RECT r);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
  static string titreOk = null; static HashSet<uint> pidsOk = new HashSet<uint>();
  public static void Autoriser(string titre, uint[] pids) { titreOk = titre; pidsOk = new HashSet<uint>(pids); }
  public static int[] Rect(IntPtr h) {     // position et taille de NOTRE fenêtre seulement (jarvis_memoriser_position)
    if (!Sur(h)) return null;
    RECT r; GetWindowRect(h, out r); return new int[] { r.L, r.T, r.R, r.B };
  }
  public static bool Sur(IntPtr h) {
    if (titreOk == null || h == IntPtr.Zero) return false;
    var t = new StringBuilder(256); GetWindowText(h, t, 256);
    if (t.ToString() != titreOk) return false;
    uint pid; GetWindowThreadProcessId(h, out pid);
    return pidsOk.Contains(pid);
  }
  public static IntPtr Trouver() {
    IntPtr res = IntPtr.Zero;
    EnumWindows((h, l) => { if (Sur(h)) { res = h; return false; } return true; }, IntPtr.Zero);
    return res;
  }
  // Mode tableau : la fenêtre (cadre compris) occupe exactement la zone de travail de l'écran (barre des tâches visible).
  // premierPlan=false : jamais "toujours au premier plan".
  public static bool PlacerZone(IntPtr h, int x, int y, int w, int hh, bool premierPlan) {
    if (!Sur(h)) return false;
    ShowWindow(h, 4);                                   // SW_SHOWNOACTIVATE
    return SetWindowPos(h, (IntPtr)(premierPlan ? -1 : -2), x, y, w, hh, 0x0010);   // SWP_NOACTIVATE
  }
  // Mode discret : zone cliente cw x ch, cadre compris posé dans le coin bas-droit de la zone de travail (marge px).
  public static bool PlacerCoin(IntPtr h, int droite, int bas, int marge, int cw, int ch, bool premierPlan) {
    if (!Sur(h)) return false;
    ShowWindow(h, 4);
    RECT wr, cr; GetWindowRect(h, out wr); GetClientRect(h, out cr);
    int extraW = Math.Max(0, (wr.R - wr.L) - cr.R), extraH = Math.Max(0, (wr.B - wr.T) - cr.B);
    int W = cw + extraW, H = ch + extraH;
    return SetWindowPos(h, (IntPtr)(premierPlan ? -1 : -2), droite - marge - W, bas - marge - H, W, H, 0x0010);
  }
  // Afficher = visible ET devant les autres fenêtres, sans prendre le focus ni modifier aucune autre fenêtre. Masquer = cachée.
  public static bool Montrer(IntPtr h, bool oui) {
    if (!Sur(h)) return false;
    ShowWindow(h, oui ? 4 : 0);
    if (oui) SetWindowPos(h, IntPtr.Zero, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010);   // HWND_TOP, NOMOVE|NOSIZE|NOACTIVATE
    return true;
  }
}
'@

$script:VisageEtatVal = 'ecoute'
$script:VisageHwnd = [IntPtr]::Zero
$script:VisageVisible = $true
$script:Http = $null; $script:HttpTache = $null; $script:Jeton = $null; $script:Tray = $null
$script:EdgeProfil = Join-Path $env:TEMP 'jarvis-edge'
$script:TitreOrbe = $null; $script:EdgePid = 0; $script:EcranVisage = $null

function Set-VisageEtat([string]$e) {
    # En sourdine, l'orbe reste en état « sourdine » quoi qu'on lui demande.
    if ($script:Actif -eq $false) { $e = 'sourdine' }
    $script:VisageEtatVal = $e
}

function Get-ArbrePids([int]$racine) {
    # Le processus Edge lancé par Jarvis + ses descendants (rien d'autre).
    $tous = @(Get-CimInstance Win32_Process | Select-Object ProcessId, ParentProcessId)
    $res = New-Object System.Collections.Generic.List[uint32]; $res.Add([uint32]$racine)
    for ($i = 0; $i -lt $res.Count; $i++) { foreach ($p in $tous) { if ($p.ParentProcessId -eq $res[$i] -and -not $res.Contains([uint32]$p.ProcessId)) { $res.Add([uint32]$p.ProcessId) } } }
    , $res.ToArray()
}

function Read-Corps($req) {
    $sr = New-Object IO.StreamReader($req.InputStream, [Text.Encoding]::UTF8); $t = $sr.ReadToEnd(); $sr.Dispose()
    if ($t) { try { return ($t | ConvertFrom-Json) } catch {} }
    $null
}

function Send-Http($ctx, [string]$corps, [string]$type = 'application/json; charset=utf-8', [int]$code = 200) {
    $b = [Text.Encoding]::UTF8.GetBytes($corps)
    $ctx.Response.StatusCode = $code; $ctx.Response.ContentType = $type; $ctx.Response.ContentLength64 = $b.Length
    $ctx.Response.Headers.Add('Cache-Control', 'no-store')
    $ctx.Response.OutputStream.Write($b, 0, $b.Length); $ctx.Response.Close()
}

function Switch-Visage {
    if ($script:VisageHwnd -eq [IntPtr]::Zero) { return }
    $voulu = -not $script:VisageVisible
    if ([JarvisWin]::Montrer($script:VisageHwnd, $voulu)) { $script:VisageVisible = $voulu }
}

function Invoke-RequeteVisage($ctx) {
    $req = $ctx.Request; $port = $Config.visage_port
    $hoteOk = $req.Headers['Host'] -eq "127.0.0.1:$port"
    $origine = $req.Headers['Origin']
    if (-not $hoteOk -or ($origine -and $origine -ne "http://127.0.0.1:$port")) { Send-Http $ctx 'interdit' 'text/plain' 403; return }
    $chemin = $req.Url.AbsolutePath
    if ($req.HttpMethod -eq 'GET') {
        if (($chemin -like '/vues/*' -or $chemin -like '/lib/three/*') -and (Get-Command Get-FichierVueHttp -ErrorAction SilentlyContinue)) {      # code des vues et three.js LOCAL : fichiers connus seulement (liste blanche), mêmes contrôles d'hôte et d'origine, jamais memoire\ ni config
            $f = Get-FichierVueHttp $chemin; if ($f) { Send-Http $ctx $f.corps $f.type; return }
            Send-Http $ctx 'introuvable' 'text/plain' 404; return
        }
        if ($chemin -like '/pilotage/*' -and (Get-Command Get-FichierPilotageHttp -ErrorAction SilentlyContinue)) {      # scripts du workspace Pilotage (liste blanche, désactivé par défaut : pilotage_actif) ; mêmes contrôles d'hôte et d'origine
            $f = Get-FichierPilotageHttp $chemin; if ($f) { Send-Http $ctx $f.corps $f.type; return }
            Send-Http $ctx 'introuvable' 'text/plain' 404; return
        }
        if ($chemin -eq '/pilotage' -and (Get-Command Get-PagePilotage -ErrorAction SilentlyContinue)) {      # page Pilotage : même jeton que la salle de marché
            if ($req.QueryString['k'] -ne $script:Jeton) { Send-Http $ctx 'interdit' 'text/plain' 403; return }
            $html = Get-PagePilotage $script:Jeton; if ($html) { Send-Http $ctx $html 'text/html; charset=utf-8'; return }
            Send-Http $ctx 'introuvable' 'text/plain' 404; return
        }
        if ($chemin -eq '/') {
            if ($req.QueryString['k'] -ne $script:Jeton) { Send-Http $ctx 'interdit' 'text/plain' 403; return }
            $html = [IO.File]::ReadAllText((Join-Path $script:JarvisRoot 'visage\index.html'), [Text.Encoding]::UTF8).Replace('__TOKEN__', $script:Jeton).Replace('__TITRE__', $script:TitreOrbe).Replace('__MODE__', "$($Config.mode_affichage)").Replace('<!--__WIDGETS__-->', $(if ((Get-Command Get-PilotageConfig -ErrorAction SilentlyContinue) -and (Get-PilotageConfig).actif) { '<script src="/pilotage/widgets.js" defer></script>' } else { '' }))
            Send-Http $ctx $html 'text/html; charset=utf-8'; return
        }
        if ($chemin -eq '/marche') {      # page « salle de marché » (lecture seule) : même jeton, mêmes contrôles d'hôte et d'origine
            if ($req.QueryString['k'] -ne $script:Jeton) { Send-Http $ctx 'interdit' 'text/plain' 403; return }
            $html = [IO.File]::ReadAllText((Join-Path $script:JarvisRoot 'visage\marche.html'), [Text.Encoding]::UTF8).Replace('__TOKEN__', $script:Jeton)
            Send-Http $ctx $html 'text/html; charset=utf-8'; return
        }
        if ($req.QueryString['k'] -eq $script:Jeton) {
            if ($chemin -eq '/marche-donnees' -and (Get-Command Get-DonneesSalleMarche -ErrorAction SilentlyContinue)) { Send-Http $ctx ((Get-DonneesSalleMarche) | ConvertTo-Json -Depth 8 -Compress); return }
            if ($chemin -eq '/etat') { $niv = if (Get-Command Get-DonneesMicro -ErrorAction SilentlyContinue) { [int](Get-DonneesMicro).niveau } else { 0 }; Send-Http $ctx (@{ etat = $script:VisageEtatVal; niveau = $niv; jeu = [bool]($script:ModeJeu -eq $true); ack = [int]$script:AccuseN } + $(if (Get-Command Get-VuesEtatHttp -ErrorAction SilentlyContinue) { Get-VuesEtatHttp } else { @{} }) | ConvertTo-Json -Depth 6 -Compress); return }      # état de l'orbe + niveau du micro (anneaux) + mode jeu : sondage rapide et léger
            if ($chemin -eq '/pilotage-donnees' -and (Get-Command Get-DonneesPilotage -ErrorAction SilentlyContinue)) { $d = Get-DonneesPilotage; if ($d) { Send-Http $ctx ($d | ConvertTo-Json -Depth 8 -Compress); return } }      # lecture seule, champs choisis un par un
            if ($chemin -eq '/pilotage-widgets' -and (Get-Command Get-WidgetsPilotage -ErrorAction SilentlyContinue)) { $d = Get-WidgetsPilotage; if ($d) { Send-Http $ctx ($d | ConvertTo-Json -Depth 4 -Compress); return } }
            if ($chemin -eq '/donnees') { Send-Http $ctx ((Get-DonneesTableau) | ConvertTo-Json -Depth 6 -Compress); $script:PageChargee = $true; return }
        }
        Send-Http $ctx 'introuvable' 'text/plain' 404; return
    }
    if ($req.HttpMethod -eq 'POST' -and $req.Headers['X-Jarvis-Token'] -eq $script:Jeton) {
        $c = Read-Corps $req
        if ($chemin -eq '/pilotage-action' -and (Get-Command Invoke-PilotageAction -ErrorAction SilentlyContinue)) { Send-Http $ctx ((Invoke-PilotageAction $c) | ConvertTo-Json -Compress); return }      # boutons Approuver / Rejeter / Plus tard : mêmes fonctions que Discord
        if ($chemin -eq '/pilotage-widget' -and (Get-Command Invoke-PilotageWidget -ErrorAction SilentlyContinue)) { Send-Http $ctx ((Invoke-PilotageWidget $c) | ConvertTo-Json -Compress); return }      # barre de widgets : actions et niveaux existants
        switch ($chemin) {
            '/ordre'   { if ($c.texte) { $script:Entrees.Enqueue(@{ src = 'visage'; texte = "$($c.texte)".Trim(); entendu = $false }) } }
            '/reduire' { Switch-Visage }
            '/vue'     { if (Get-Command Receive-VueEtat -ErrorAction SilentlyContinue) { Receive-VueEtat $c } }      # la page signale qu'une vue est ouverte / fermée / en erreur (Échap, bouton Fermer)
        }
        Send-Http $ctx '{"ok":true}'; return
    }
    Send-Http $ctx 'interdit' 'text/plain' 403
}

function Invoke-PumpVisage {
    if ($script:Tray) { [Windows.Forms.Application]::DoEvents() }
    if (-not $script:Http) { return }
    $n = 0
    while ($script:HttpTache -and $script:HttpTache.IsCompleted -and $n++ -lt 6) {
        $ctx = $null; try { $ctx = $script:HttpTache.Result } catch {}
        $script:HttpTache = $script:Http.GetContextAsync()
        if ($ctx) { try { Invoke-RequeteVisage $ctx } catch { try { $ctx.Response.Abort() } catch {} } }
    }
}

function New-IconeOrbe {
    # Icône simple : orbe cyan lumineux sur fond sombre (même dessin que le favicon de la page).
    $bmp = New-Object Drawing.Bitmap 32, 32
    $g = [Drawing.Graphics]::FromImage($bmp); $g.SmoothingMode = 'AntiAlias'
    $g.Clear([Drawing.Color]::FromArgb(255, 5, 8, 13))
    $gp = New-Object Drawing.Drawing2D.GraphicsPath; $gp.AddEllipse(4, 4, 24, 24)
    $pb = New-Object Drawing.Drawing2D.PathGradientBrush $gp
    $pb.CenterColor = [Drawing.Color]::FromArgb(255, 235, 252, 255); $pb.SurroundColors = @([Drawing.Color]::FromArgb(255, 40, 170, 230))
    $pb.CenterPoint = New-Object Drawing.PointF 16, 16
    $g.FillEllipse($pb, 4, 4, 24, 24)
    $g.Dispose(); [Drawing.Icon]::FromHandle($bmp.GetHicon())
}

function Get-GeometrieVisage {
    # Géométrie de la fenêtre selon le mode et l'écran choisi (fonction pure : testable).
    #  tableau : type "zone"  = cadre compris, exactement la zone de travail (WorkingArea : barre des tâches visible)
    #  discret : type "coin"  = zone cliente taille x taille, cadre compris posé en bas à droite de la zone de travail
    param($ecran, [string]$mode, [int]$taille = 260, [int]$marge = 24, [bool]$plein = $false)
    $z = $ecran.zone
    if ($mode -ne 'discret' -and $plein) { $b = $ecran.bounds; return @{ type = 'zone'; plein = $true; x = $b.X; y = $b.Y; w = $b.Width; h = $b.Height } }      # plein écran : tout l'écran choisi (barre des tâches comprise)
    if ($mode -eq 'discret') { return @{ type = 'coin'; droite = $z.Right; bas = $z.Bottom; marge = $marge; w = $taille; h = $taille; x = $z.Right - $taille - $marge; y = $z.Bottom - $taille - $marge } }
    @{ type = 'zone'; x = $z.X; y = $z.Y; w = $z.Width; h = $z.Height }
}

function Get-PleinEcranVisage { -not ($Config.PSObject.Properties['jarvis_plein_ecran'] -and $Config.jarvis_plein_ecran -eq $false) }      # défaut : plein écran
function Get-MemoriserPosition { [bool]($Config.PSObject.Properties['jarvis_memoriser_position'] -and $Config.jarvis_memoriser_position -eq $true) }      # défaut : non
function Get-FenetreMemorisee($ecrans) {
    # Position choisie à la main, mémorisée dans memoire\fenetre-jarvis.json ; ignorée si elle ne tombe plus sur aucun écran. $null si absente ou invalide.
    $o = Read-JsonMemoire 'fenetre-jarvis.json'; if (-not $o) { return $null }
    try { $x = [int]$o.x; $y = [int]$o.y; $w = [int]$o.w; $h = [int]$o.h } catch { return $null }
    if ($w -lt 200 -or $h -lt 150) { return $null }
    $cx = $x + [int]($w / 2); $cy = $y + [int]($h / 2)
    foreach ($e in @($ecrans)) { $b = $e.bounds; if ($cx -ge $b.X -and $cx -lt ($b.X + $b.Width) -and $cy -ge $b.Y -and $cy -lt ($b.Y + $b.Height)) { return @{ type = 'zone'; plein = $false; x = $x; y = $y; w = $w; h = $h } } }
    $null
}
function Save-FenetreMemorisee([int[]]$rect) {
    if (-not $rect -or $rect.Count -lt 4) { return $false }
    $w = $rect[2] - $rect[0]; $h = $rect[3] - $rect[1]; if ($w -lt 200 -or $h -lt 150 -or $rect[0] -le -30000) { return $false }      # (fenêtre réduite : on ne mémorise pas)
    Save-JsonMemoire 'fenetre-jarvis.json' ([ordered]@{ x = $rect[0]; y = $rect[1]; w = $w; h = $h; date = (Get-Date).ToString('o') }); $true
}

function Start-Visage {
    if (-not $Config.visage -or (Test-ModeTest) -or (Test-ModeServeur)) { return }      # tests : jamais de fenêtre ; mode serveur : pas de HUD
    try {
        $port = [int]$Config.visage_port
        $script:Jeton = [guid]::NewGuid().ToString('N')
        $script:TitreOrbe = 'JarvisOrb-' + [guid]::NewGuid().ToString('N').Substring(0, 8)
        $script:Http = New-Object Net.HttpListener
        $script:Http.Prefixes.Add("http://127.0.0.1:$port/"); $script:Http.Start()
        $script:HttpTache = $script:Http.GetContextAsync()
        # Icône de barre système
        $script:Tray = New-Object Windows.Forms.NotifyIcon
        $script:Tray.Icon = New-IconeOrbe; $script:Tray.Text = 'Jarvis'; $script:Tray.Visible = $true
        $menu = New-Object Windows.Forms.ContextMenuStrip
        [void]$menu.Items.Add('Afficher / masquer Jarvis', $null, { Switch-Visage })
        [void]$menu.Items.Add('Quitter Jarvis', $null, { $script:Quitter = $true })
        $script:Tray.ContextMenuStrip = $menu
        $script:Tray.add_MouseClick({ param($s, $e) if ($e.Button -eq 'Left') { Switch-Visage } })
        # Écran et géométrie
        $mode = if ("$($Config.mode_affichage)" -eq 'discret') { 'discret' } else { 'tableau' }
        $sel = Select-Ecran $Config.ecran_jarvis
        $script:EcranVisage = $sel.ecran
        if ($sel.raison) { Write-Journal -Action 'Choix de l''écran' -Resultat $sel.raison }
        $plein = ($mode -eq 'tableau' -and (Get-PleinEcranVisage))
        $geo = Get-GeometrieVisage $sel.ecran $mode ([int]$Config.visage_taille) 24 $plein
        if ($mode -eq 'tableau' -and (Get-MemoriserPosition)) { $mem = Get-FenetreMemorisee @(Get-Ecrans); if ($mem) { $geo = $mem; $plein = $false } }      # position choisie à la main, seulement si jarvis_memoriser_position = true
        $premier = [bool]$Config.orbe_premier_plan
        # Fenêtre Edge : lancée réduite pour ne pas voler le focus, puis placée sans activation
        $edge = (Get-Command msedge -ErrorAction SilentlyContinue).Source
        if (-not $edge) { $edge = "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe" }
        $url = "http://127.0.0.1:$port/?k=$($script:Jeton)"
        $args2 = @("--app=$url", "--user-data-dir=`"$script:EdgeProfil`"", "--window-size=$($geo.w),$($geo.h)", "--window-position=$($geo.x),$($geo.y)", '--no-first-run', '--no-default-browser-check', '--disable-extensions', '--disable-sync', '--force-dark-mode')
        if ($plein) { $args2 += '--start-fullscreen' }      # plein écran sur l'écran choisi (F11 bascule plein écran / fenêtre)
        $script:PageChargee = $false
        $ep = Start-Process $edge -PassThru -WindowStyle Minimized -ArgumentList $args2   # réduite : rien n'est visible tant que la page n'est pas prête (pas d'écran blanc)
        $script:EdgePid = $ep.Id
        if (-not ($Config.PSObject.Properties['priorite_cpu_basse'] -and $Config.priorite_cpu_basse -eq $false)) { try { $ep.PriorityClass = 'BelowNormal' } catch {} }
        $fin = (Get-Date).AddSeconds(15)
        while ($script:VisageHwnd -eq [IntPtr]::Zero -and (Get-Date) -lt $fin) {
            Invoke-PumpVisage; Start-Sleep -Milliseconds 200
            # Seul le processus lancé ici (et ses enfants) + le titre unique exact peuvent désigner la fenêtre.
            [JarvisWin]::Autoriser($script:TitreOrbe, [uint32[]](Get-ArbrePids $script:EdgePid))
            $script:VisageHwnd = [JarvisWin]::Trouver()
        }
        if ($script:VisageHwnd -ne [IntPtr]::Zero) {
            # On n'affiche la fenêtre qu'une fois la page chargée et ses données servies, puis on laisse 500 ms pour la première image sombre.
            $fin = (Get-Date).AddSeconds(10)
            while (-not $script:PageChargee -and (Get-Date) -lt $fin) { Invoke-PumpVisage; Start-Sleep -Milliseconds 100 }
            $t = (Get-Date).AddMilliseconds(500); while ((Get-Date) -lt $t) { Invoke-PumpVisage; Start-Sleep -Milliseconds 50 }
            if ($geo.type -eq 'coin') { [void][JarvisWin]::PlacerCoin($script:VisageHwnd, $geo.droite, $geo.bas, $geo.marge, $geo.w, $geo.h, $premier) }
            else { [void][JarvisWin]::PlacerZone($script:VisageHwnd, $geo.x, $geo.y, $geo.w, $geo.h, $premier) }
        }
        Write-Journal -Action 'Affichage Jarvis' -Resultat $(if ($script:VisageHwnd -ne [IntPtr]::Zero) { "mode $mode sur $($sel.ecran.peripherique) $($sel.ecran.nom) (zone de travail $($geo.w)x$($geo.h) en $($geo.x),$($geo.y)), port $port" } else { 'fenêtre introuvable' })
    } catch { Write-Journal -Action 'Affichage Jarvis' -Resultat "échec : $($_.Exception.Message)" }
}

function Stop-Visage {
    try {   # jarvis_memoriser_position = true : on garde la position choisie à la main (jamais le plein écran lui-même)
        if ((Get-MemoriserPosition) -and $script:VisageHwnd -ne [IntPtr]::Zero) {
            $r = [JarvisWin]::Rect($script:VisageHwnd)
            if ($r) { $pleinEcran = @(Get-Ecrans | Where-Object { $_.bounds.X -eq $r[0] -and $_.bounds.Y -eq $r[1] -and ($_.bounds.X + $_.bounds.Width) -eq $r[2] -and ($_.bounds.Y + $_.bounds.Height) -eq $r[3] }).Count; if (-not $pleinEcran) { [void](Save-FenetreMemorisee $r) } }
        }
    } catch {}
    if (Get-Command Stop-FenetreMarche -ErrorAction SilentlyContinue) { Stop-FenetreMarche }      # la fenêtre de la salle de marché se ferme avec Jarvis
    try { if ($script:Tray) { $script:Tray.Visible = $false; $script:Tray.Dispose(); $script:Tray = $null } } catch {}
    try { if ($script:Http) { $script:Http.Stop(); $script:Http.Close(); $script:Http = $null } } catch {}
    try {   # ferme uniquement l'Edge lancé par Jarvis (son PID et ses enfants), jamais un autre processus
        if ($script:EdgePid) { foreach ($p in (Get-ArbrePids $script:EdgePid)) { Stop-Process -Id $p -Force -ErrorAction SilentlyContinue } }
    } catch {}
}
