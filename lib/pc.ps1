# Contrôle du PC à la voix, VERSION 1 : applications, sites, fenêtres, système, médias, captures, dossiers autorisés, winget (propositions seulement), YouTube.
# RÈGLES : seule VOTRE voix (ou votre saisie) commande ; une instruction trouvée dans un fichier, une page ou un e-mail est une donnée, jamais un ordre.
# Sourdine et mode jeu bloquent tous les ordres (voir Invoke-Entree). Niveau 1 = autonome ; niveau 2 = « Vous confirmez, monsieur ? » (redémarrer, veille, éteindre, forcer une fermeture, installer) ;
# niveau 3 = refusé (virements, achats, ordres boursiers, antivirus / pare-feu, mots de passe, suppression de Jarvis ou de son journal : lib\permissions.ps1). Aucune suppression de fichier.
# config.json "pc" : { applications_autorisees (liste blanche ; vide = toutes sauf la liste noire), applications_interdites (en plus de la liste noire intégrée), dossiers_autorises { nom: chemin },
#                      dossier_captures }  ;  "sites" : { nom: url }.  Jamais la fenêtre de l'orbe ; jamais un vol de focus non demandé ; fermeture toujours « propre » (CloseMainWindow).
Add-Type -TypeDefinition @'
using System; using System.Text; using System.Collections.Generic; using System.Runtime.InteropServices;
public class JarvisPc {
  delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] static extern bool EnumWindows(EnumProc p, IntPtr l);
  [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] static extern int GetWindowLong(IntPtr h, int i);
  [DllImport("user32.dll")] static extern bool ShowWindow(IntPtr h, int c);
  [DllImport("user32.dll")] static extern bool SetWindowPos(IntPtr h, IntPtr a, int x, int y, int cx, int cy, uint f);
  [DllImport("user32.dll")] static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] static extern void keybd_event(byte vk, byte sc, uint fl, UIntPtr ex);
  public static List<string> Liste() {
    var l = new List<string>();
    EnumWindows((h, p) => {
      if (!IsWindowVisible(h)) return true;
      if ((GetWindowLong(h, -20) & 0x80) != 0) return true;                    // WS_EX_TOOLWINDOW
      var t = new StringBuilder(256); GetWindowText(h, t, 256); if (t.Length == 0) return true;
      uint pid; GetWindowThreadProcessId(h, out pid); l.Add(h.ToInt64() + "|" + pid + "|" + t.ToString().Replace("|", "/")); return true;
    }, IntPtr.Zero);
    return l;
  }
  public static void Etat(IntPtr h, int cmd) { ShowWindow(h, cmd); }                                   // 9 restaurer, 3 agrandir, 7 réduire sans activer
  public static void Placer(IntPtr h, int x, int y, int w, int hh) { ShowWindow(h, 9); SetWindowPos(h, IntPtr.Zero, x, y, w, hh, 0x0004 | 0x0010); }   // sans activation
  public static void Devant(IntPtr h) { keybd_event(0x12, 0, 0, UIntPtr.Zero); keybd_event(0x12, 0, 2, UIntPtr.Zero); ShowWindow(h, 9); SetForegroundWindow(h); }
  public static void Touche(byte vk) { keybd_event(vk, 0, 0, UIntPtr.Zero); keybd_event(vk, 0, 2, UIntPtr.Zero); }
  [StructLayout(LayoutKind.Sequential)] struct RECT { public int L, T, R, B; }
  [DllImport("user32.dll")] static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] static extern bool IsIconic(IntPtr h);
  [DllImport("user32.dll")] static extern bool IsZoomed(IntPtr h);
  public static int[] Rect(IntPtr h) { RECT r; GetWindowRect(h, out r); return new int[] { r.L, r.T, r.R - r.L, r.B - r.T, IsIconic(h) ? 2 : (IsZoomed(h) ? 1 : 0) }; }      // x, y, largeur, hauteur, état (0 normal, 1 agrandie, 2 réduite)
}
'@

# ---------- Réglages ----------
$script:PcSim = @(); $script:FaussesFenetres = @(); $script:FaussesWinget = @()      # mode test : ce que les actions AURAIENT fait (aucun effet réel)
$script:AppsInterditesBase = @('keepass', 'bitwarden', '1password', 'lastpass', 'dashlane', 'nordpass', 'enpass', 'roboform', 'defender', 'windows security', 'securite windows', 'securityhealth', 'msmpeng', 'malwarebytes', 'kaspersky', 'avast', 'norton', 'bitdefender', 'eset', 'mcafee', 'pare-feu', 'firewall', 'regedit', 'jarvis')
$script:AliasApps = @{ 'le navigateur' = 'navigateur'; 'navigateur' = 'navigateur'; 'internet' = 'navigateur'; 'vs code' = 'vscode'; 'vscode' = 'vscode'; 'visual studio code' = 'vscode'; 'code' = 'vscode'; 'discord' = 'discord'; 'steam' = 'steam'; 'spotify' = 'spotify'
    'google chrome' = 'chrome'; 'chrome' = 'chrome'; 'edge' = 'edge'; 'microsoft edge' = 'edge'; 'explorateur' = 'explorateur'; 'le bloc notes' = 'bloc-notes'; 'bloc notes' = 'bloc-notes'; 'calculatrice' = 'calculatrice'; 'terminal' = 'terminal' }
function Get-ConfigPc { if ($Config.PSObject.Properties['pc'] -and $Config.pc) { $Config.pc } else { [pscustomobject]@{} } }
function Get-AppsInterdites { @($script:AppsInterditesBase) + @(@((Get-ConfigPc).applications_interdites) | Where-Object { $_ } | ForEach-Object { (ConvertTo-NormMarche "$_") }) }
function Test-AppInterdite([string]$nom) {
    $n = ConvertTo-NormMarche $nom
    foreach ($m in (Get-AppsInterdites)) { $mm = ConvertTo-NormMarche $m; if ($mm -and ($n -like "*$mm*")) { return $true } }
    $false
}
function Test-AppAutorisee([string]$nom) {
    $blanche = @(@((Get-ConfigPc).applications_autorisees) | Where-Object { $_ })
    if (-not $blanche.Count) { return $true }
    $n = ConvertTo-NormMarche $nom; foreach ($b in $blanche) { $bb = ConvertTo-NormMarche "$b"; if ($bb -and ($n -like "*$bb*" -or $bb -like "*$n*")) { return $true } }
    $false
}
function Get-SitesPc {
    $h = @{}
    if (Get-Variable -Name SitesConnus -Scope Script -ErrorAction SilentlyContinue) { foreach ($k in $script:SitesConnus.Keys) { if ($script:SitesConnus[$k]) { $h[(ConvertTo-NormMarche $k)] = $script:SitesConnus[$k] } } }
    if ($Config.PSObject.Properties['sites'] -and $Config.sites) { foreach ($p in $Config.sites.PSObject.Properties) { if ("$($p.Value)" -match '^https://') { $h[(ConvertTo-NormMarche $p.Name)] = "$($p.Value)" } } }
    if ($Config.site) { foreach ($k in 'mon saas', 'mon site', 'tonproduit') { if (-not $h.ContainsKey($k)) { $h[$k] = "$($Config.site)" } } }
    $h
}

# ---------- Trouver une application (tolérant) ----------
function Resolve-AppPc([string]$nom) {
    # @{ ok; nom; site; raison } — « chrome », « le navigateur », « VS Code »... ; $null-safe ; ne lance rien.
    $n0 = ConvertTo-NormMarche $nom; $n = ($n0 -replace '^((l|le|la|les|mon|ma|mes|un|une|application|appli|programme|logiciel) )+', '').Trim()
    if ($n.Length -lt 2) { return @{ ok = $false; nom = $nom; raison = 'nom vide' } }
    if (Test-AppInterdite $n) { return @{ ok = $false; nom = $nom; interdit = $true; raison = 'application protégée (gestionnaire de mots de passe, sécurité ou Jarvis)' } }
    $sites = Get-SitesPc; foreach ($k in $n0, $n, "mon $n") { if ($sites.ContainsKey($k)) { return @{ ok = $true; nom = $k; site = $sites[$k] } } }
    $cand = $null
    if ($script:AliasApps.ContainsKey($n)) {
        $a = $script:AliasApps[$n]
        if ($a -eq 'navigateur') { $a = if ($Config.apps.PSObject.Properties['chrome']) { 'chrome' } else { 'edge' } }
        $cand = $a
    }
    if (-not $cand) { foreach ($p in $Config.apps.PSObject.Properties) { if ((ConvertTo-NormMarche $p.Name) -eq $n) { $cand = $p.Name; break } } }
    if (-not $cand) {
        $apps = @(Get-StartAppsCache | ForEach-Object { @{ nom = $_.Name; n = (ConvertTo-NormMarche $_.Name) } })
        $m = @($apps | Where-Object { $_.n -eq $n })
        if (-not $m.Count) { $m = @($apps | Where-Object { $_.n.StartsWith($n) -or $_.n -like "* $n*" }) }
        if (-not $m.Count -and $n.Length -ge 5) { $m = @($apps | Where-Object { $_.n -like "*$n*" }) }
        if (-not $m.Count -and $n.Length -ge 5) { $m = @($apps | Where-Object { [math]::Abs($_.n.Length - $n.Length) -le 2 -and (Get-Distance $_.n $n) -le 2 }) }
        if ($m.Count -ge 1) { $cand = ($m | Sort-Object { $_.n.Length } | Select-Object -First 1).nom }
    }
    if (-not $cand) { return @{ ok = $false; nom = $nom; raison = 'introuvable' } }
    if (Test-AppInterdite $cand) { return @{ ok = $false; nom = $nom; interdit = $true; raison = 'application protégée' } }
    if (-not (Test-AppAutorisee $cand)) { return @{ ok = $false; nom = $nom; interdit = $true; raison = 'application absente de la liste blanche (config.json, pc.applications_autorisees)' } }
    @{ ok = $true; nom = $cand }
}

# ---------- Fenêtres ----------
function Test-FenetreProtegee($f) {
    # Jamais l'orbe de Jarvis (titre unique JarvisOrb-xxxx, ou son Edge), jamais Jarvis lui-même, jamais une application protégée.
    if ("$($f.titre)" -like 'JarvisOrb-*' -or "$($f.titre)" -like 'Jarvis*' -or ($script:EdgePid -and [int]$f.pid -eq [int]$script:EdgePid) -or [int]$f.pid -eq $PID) { return $true }
    (Test-AppInterdite "$($f.proc) $($f.titre)")
}
function Get-FenetresPc {
    # [@{ hwnd; pid; proc; titre }] — fenêtres visibles, SANS la fenêtre de l'orbe, ni Jarvis, ni les applications protégées. (Remplacé par un bouchon dans les tests.)
    if (Test-ModeTest) { return @($script:FaussesFenetres | Where-Object { -not (Test-FenetreProtegee $_) }) }
    $res = @()
    foreach ($l in [JarvisPc]::Liste()) {
        $p = $l -split '\|', 3; $id = [int]$p[1]
        $proc = try { (Get-Process -Id $id -ErrorAction Stop).ProcessName } catch { '' }
        if (-not $proc -or $p[2] -eq 'Program Manager') { continue }
        $f = @{ hwnd = [int64]$p[0]; pid = $id; proc = $proc; titre = $p[2] }
        if (Test-FenetreProtegee $f) { continue }
        $res += $f
    }
    $res
}
function Select-FenetrePc([string]$nom) {
    $n = ConvertTo-NormMarche $nom
    $alias = if ($script:AliasApps.ContainsKey($n)) { $script:AliasApps[$n] } else { $n }
    $cles = @($n, $alias) + $(if ($alias -eq 'navigateur') { @('chrome', 'msedge', 'firefox') } elseif ($alias -eq 'vscode') { @('code') } else { @() })
    foreach ($f in (Get-FenetresPc)) { $p = ConvertTo-NormMarche $f.proc; $t = ConvertTo-NormMarche $f.titre; foreach ($c in $cles) { if ($c -and ($p -like "*$c*" -or $t -like "*$c*")) { return $f } } }
    $null
}
function Set-FenetreEtat($f, [string]$mode, $zone) {
    # Seam : seul point qui agit sur une fenêtre (bouchon dans les tests). mode : gauche | droite | plein | reduire | devant | ecran
    if (Test-ModeTest) { $script:PcSim += "fenetre:${mode}:$($f.proc)"; return }
    $h = [IntPtr]::new([int64]$f.hwnd)
    switch ($mode) {
        'gauche'  { [JarvisPc]::Placer($h, $zone.X, $zone.Y, [int]($zone.Width / 2), $zone.Height) }
        'droite'  { [JarvisPc]::Placer($h, $zone.X + [int]($zone.Width / 2), $zone.Y, [int]($zone.Width / 2), $zone.Height) }
        'plein'   { [JarvisPc]::Etat($h, 3) }
        'reduire' { [JarvisPc]::Etat($h, 7) }
        'devant'  { [JarvisPc]::Devant($h) }
        'ecran'   { [JarvisPc]::Placer($h, $zone.X, $zone.Y, $zone.Width, $zone.Height); [JarvisPc]::Etat($h, 3) }
        'rect'    { if ([int]$zone.Etat -eq 1) { [JarvisPc]::Etat($h, 3) } elseif ([int]$zone.Etat -eq 2) { [JarvisPc]::Etat($h, 7) } else { [JarvisPc]::Placer($h, [int]$zone.X, [int]$zone.Y, [int]$zone.Width, [int]$zone.Height) } }      # disposition mémorisée
    }
}
function Get-RectFenetre($f) {
    # Seam : position et état d'une fenêtre (bouchon dans les tests : $f.rect = @(x, y, largeur, hauteur, état)).
    if (Test-ModeTest) { if ($f.rect) { return @($f.rect) } else { return @(0, 0, 800, 600, 0) } }
    @([JarvisPc]::Rect([IntPtr]::new([int64]$f.hwnd)))
}
function Get-ZoneFenetre($f) { try { $s = [Windows.Forms.Screen]::FromHandle([IntPtr]::new([int64]$f.hwnd)).WorkingArea; @{ X = $s.X; Y = $s.Y; Width = $s.Width; Height = $s.Height } } catch { @{ X = 0; Y = 0; Width = 1280; Height = 720 } } }

# ---------- Dossiers autorisés et recherche de fichiers ----------
function Get-DossiersAutorises {
    $h = @{}
    $defaut = @{ documents = [Environment]::GetFolderPath('MyDocuments'); telechargements = (Join-Path $env:USERPROFILE 'Downloads'); bureau = [Environment]::GetFolderPath('Desktop') }
    if (-not (Test-ModeTest)) { foreach ($k in $defaut.Keys) { $h[$k] = $defaut[$k] } }      # (les tests ne fouillent jamais vos vrais dossiers)
    $c = (Get-ConfigPc).dossiers_autorises
    if ($c) { foreach ($p in $c.PSObject.Properties) { if ("$($p.Value)".Trim()) { $h[(ConvertTo-NormMarche $p.Name)] = [Environment]::ExpandEnvironmentVariables("$($p.Value)") } } }
    $h
}
function Resolve-DossierPc([string]$nom) {
    $n = (ConvertTo-NormMarche $nom) -replace '^((le|la|les|mon|mes|l|de|du|des) )+', ''; $n = $n.TrimEnd('s')
    $d = Get-DossiersAutorises
    foreach ($k in $d.Keys) { $kk = (ConvertTo-NormMarche $k).TrimEnd('s'); if ($kk -eq $n -or ($n.Length -ge 4 -and $kk -like "*$n*")) { return @{ ok = $true; nom = $k; chemin = $d[$k] } } }
    @{ ok = $false; raison = 'dossier absent de la liste autorisée' }
}
function Find-FichiersPc([string]$motif, [int]$max = 8) {
    # Recherche SEULEMENT dans les dossiers autorisés, profondeur et durée bornées, jamais les fichiers secrets ni le dossier de Jarvis.
    $res = @(); $fin = (Get-Date).AddSeconds(6); $m = ConvertTo-NormMarche $motif
    foreach ($d in (Get-DossiersAutorises).Values) {
        if (-not (Test-Path $d)) { continue }
        foreach ($f in (Get-ChildItem $d -Recurse -File -Depth 4 -ErrorAction SilentlyContinue)) {
            if ((Get-Date) -gt $fin -or (Test-Stop)) { break }
            if ((Test-CheminSecret $f.FullName) -or (Test-CheminJarvis $f.FullName)) { continue }
            if ((ConvertTo-NormMarche $f.BaseName) -like "*$m*") { $res += $f; if ($res.Count -ge $max) { return $res } }
        }
    }
    $res
}

# ---------- Système ----------
function Invoke-SystemePc([string]$commande, [string]$arg = '') {
    # Seam : seule fonction qui touche au système (bouchon dans les tests).
    if (Test-ModeTest) { $script:PcSim += "systeme:$commande"; return }
    switch ($commande) {
        'verrouiller' { Start-Process rundll32.exe 'user32.dll,LockWorkStation' }
        'redemarrer'  { Start-Process shutdown.exe '/r /t 20' }
        'eteindre'    { Start-Process shutdown.exe '/s /t 20' }
        'annuler'     { Start-Process shutdown.exe '/a' }
        'veille'      { Start-Process rundll32.exe 'powrprof.dll,SetSuspendState 0,1,0' }
        'media'       { [JarvisPc]::Touche([byte]$arg) }                       # 0xB3 lecture/pause, 0xB0 suivant, 0xB1 précédent
        'capture'     {
            Add-Type -AssemblyName System.Drawing
            $v = [Windows.Forms.SystemInformation]::VirtualScreen
            $bmp = New-Object Drawing.Bitmap $v.Width, $v.Height; $g = [Drawing.Graphics]::FromImage($bmp); $g.CopyFromScreen($v.X, $v.Y, 0, 0, $bmp.Size)
            $bmp.Save($arg, [Drawing.Imaging.ImageFormat]::Png); $g.Dispose(); $bmp.Dispose()
        }
    }
}
function Get-DossierCaptures {
    $c = (Get-ConfigPc).dossier_captures
    if ($c) { [Environment]::ExpandEnvironmentVariables("$c") } else { Join-Path ([Environment]::GetFolderPath('MyPictures')) 'Jarvis' }
}

# ---------- winget : propositions seulement ; rien n'est installé sans votre « oui » ----------
$script:WingetPropose = @()
function Invoke-WingetRecherche([string]$q) {
    # Seam (bouchon dans les tests) : `winget search` limité à la source officielle « winget », 3 résultats.
    if (Test-ModeTest) { return @($script:FaussesWinget) }
    $sortie = & winget search --source winget --accept-source-agreements --count 3 $q 2>$null
    @($sortie | Where-Object { $_ -match '\S+\s+\S+\.\S+' -and $_ -notmatch '^(Nom|Name|-)' } | Select-Object -First 3 | ForEach-Object { $c = $_ -split '\s{2,}'; @{ nom = $c[0].Trim(); id = $c[1].Trim() } })
}
function Invoke-WingetInstall([string]$id) { if (Test-ModeTest) { $script:PcSim += "winget:$id"; return 'ok (simulé)' }; & winget install --id $id --exact --source winget --accept-package-agreements --accept-source-agreements 2>&1 | Out-String }

# ---------- Actions ----------
$script:CapacitesJusqua = [datetime]::MinValue
$script:Capacites = @(
    @{ titre = 'Applications et sites'; lignes = @('ouvre <application ou site> — Chrome, « le navigateur », VS Code, Discord, Steam, mon SaaS, Vercel, Supabase, Stripe, GitHub…', 'ferme <application> — fermeture propre, jamais forcée sans confirmation', 'mets <recherche> sur YouTube — ouvre la page de résultats') }
    @{ titre = 'Fenêtres'; lignes = @('mets <application> à gauche / à droite / en plein écran', 'mets <application> sur l''écran de droite / de gauche', 'réduis tout · passe sur <application>') }
    @{ titre = 'Système'; lignes = @('volume à N pour cent · coupe le son · musique à N pour cent', 'pause · suivant · précédent (média)', 'fais une capture d''écran · verrouille le PC', 'redémarre / mets en veille / éteins le PC — avec confirmation') }
    @{ titre = 'Fichiers'; lignes = @('ouvre le dossier <documents, téléchargements, bureau, projets…> — dossiers autorisés seulement', 'trouve le fichier <nom> — aucune suppression, jamais') }
    @{ titre = 'Installer'; lignes = @('j''ai besoin d''une application pour… — je propose 1 à 3 options gratuites (winget) ; rien n''est installé sans votre « oui »') }
    @{ titre = 'Bureau et modes'; lignes = @('enregistre cette disposition · remets mon bureau comme avant (confirmation)', 'mode travail / détente / nuit — définis dans config.json (modes)', 'mets un minuteur de N minutes · rappelle-moi dans N minutes de…', 'résume mon presse-papiers · résume mon écran (titres des fenêtres) — jamais de données sensibles sans « oui »', 'demande à Claude Code de… — prépare la demande, la relit, exige « oui » (essai à blanc par défaut)') }
    @{ titre = 'Salle de marché (lecture seule)'; lignes = @('montre-moi le marché de <valeur> · où en est <valeur> — résumé chiffré daté et sourcé + page sur l''écran choisi (1 J / 1 S / 1 M / 1 A)', 'ouvre le graphique de <valeur> — onglets des domaines de sites_marche_autorises seulement', 'ferme la salle de marché') }
    @{ titre = 'Jarvis'; lignes = @('quelle heure est-il · briefing · détails du briefing · ma to-do · j''ai fini <tâche>', 'quoi de neuf sur le marché · les 5 à regarder · fais-moi un dossier sur…', 'baisse / monte la musique · priorité normale / élevée / maximum', 'sourdine · mode jeu · Jarvis stop (arrêt d''urgence)') }
)
# Ce que Jarvis énumère à voix haute (5 à la fois). Chaque entrée porte un exemple réel : tests\politesse.ps1 vérifie que cet exemple est bien reconnu (aucune capacité inventée).
$script:CapaciteIdx = 0
$script:CapacitesVoix = @(
    @{ dit = 'ouvrir une application ou un site'; ex = 'ouvre chrome' }
    @{ dit = 'fermer une application'; ex = 'ferme discord' }
    @{ dit = 'placer une fenêtre à gauche, à droite ou en plein écran'; ex = 'mets chrome à gauche' }
    @{ dit = 'réduire toutes les fenêtres'; ex = 'réduis tout' }
    @{ dit = 'régler le volume'; ex = 'volume à 40 pour cent' }
    @{ dit = 'régler la musique'; ex = 'baisse la musique' }
    @{ dit = 'mettre en pause ou passer au morceau suivant'; ex = 'pause' }
    @{ dit = 'faire une capture d''écran'; ex = 'fais une capture d''écran' }
    @{ dit = 'verrouiller le PC'; ex = 'verrouille le PC' }
    @{ dit = 'redémarrer, mettre en veille ou éteindre le PC, avec votre confirmation'; ex = 'mets le PC en veille' }
    @{ dit = 'ouvrir un dossier autorisé ou trouver un fichier'; ex = 'ouvre le dossier documents' }
    @{ dit = 'vous proposer une application à installer'; ex = 'j''ai besoin d''une application pour dessiner' }
    @{ dit = 'enregistrer puis remettre la disposition de votre bureau'; ex = 'enregistre cette disposition' }
    @{ dit = 'passer en mode travail, détente ou nuit'; ex = 'mode travail' }
    @{ dit = 'lancer un minuteur ou un rappel'; ex = 'mets un minuteur de 10 minutes' }
    @{ dit = 'résumer votre presse-papiers ou ce qui est ouvert à l''écran'; ex = 'résume mon presse-papiers' }
    @{ dit = 'préparer une demande pour Claude Code, avec votre accord'; ex = 'demande à claude code de lister les fichiers' }
    @{ dit = 'ouvrir la salle de marché d''une valeur de votre liste, en lecture seule'; ex = 'montre-moi le marché de Thales' }
    @{ dit = 'donner l''heure, le briefing ou votre liste de tâches'; ex = 'quelle heure est-il' }
    @{ dit = 'passer en sourdine ou en mode jeu'; ex = 'mode jeu' }
)
$script:AppRefus = { param($r, $nom) Get-RefusApp $r $nom }
function Get-RefusSansFenetre([string]$nom) { Get-Politesse 'refus' @{ raison = "aucune fenêtre ouverte pour $nom" } }
if (Get-Command Add-Action -ErrorAction SilentlyContinue) {
    Add-Action 'pc_fermer' 1 'fermer une application' 'pc_fermer(nom) : ferme proprement les fenêtres d''une application (jamais forcée, jamais Jarvis ni le système)' {
        param($a)
        $r = Resolve-AppPc "$($a.nom)"; if (-not $r.ok -or $r.site) { return (Rep $false (& $script:AppRefus $r "$($a.nom)")) }
        $f = @(Get-FenetresPc | Where-Object { $x = $_; (ConvertTo-NormMarche $x.proc) -like "*$(ConvertTo-NormMarche $r.nom)*" -or (ConvertTo-NormMarche $x.titre) -like "*$(ConvertTo-NormMarche $r.nom)*" })
        if (-not $f.Count) { return (Rep $false (Get-RefusSansFenetre $r.nom)) }
        foreach ($x in $f) { try { [void](Get-Process -Id $x.pid -ErrorAction Stop).CloseMainWindow() } catch {} }
        Rep $true (Get-Politesse 'fait_action' @{ x = "je ferme $($r.nom)" })
    } { param($a) "fermer proprement $($a.nom)" }
    Add-Action 'pc_forcer_fermeture' 2 'forcer la fermeture d''une application' 'pc_forcer_fermeture(nom) : tue les processus d''une application qui ne répond pas (confirmation obligatoire)' {
        param($a)
        $r = Resolve-AppPc "$($a.nom)"; if (-not $r.ok -or $r.site) { return (Rep $false (& $script:AppRefus $r "$($a.nom)")) }
        $ps = @(Get-FenetresPc | Where-Object { (ConvertTo-NormMarche $_.proc) -like "*$(ConvertTo-NormMarche $r.nom)*" } | ForEach-Object { $_.pid } | Select-Object -Unique)
        foreach ($i in $ps) { Stop-Process -Id $i -Force -ErrorAction SilentlyContinue }
        Rep $true (Get-Politesse 'fait_action' @{ x = "j'ai forcé la fermeture de $($r.nom)" })
    } { param($a) "FORCER la fermeture de $($a.nom)" }
    Add-Action 'pc_fenetre' 1 'placer une fenêtre' 'pc_fenetre(nom, mode : gauche|droite|plein|reduire|devant|ecran, ecran?) : place, réduit ou amène devant une fenêtre (jamais l''orbe)' {
        param($a)
        $r = Resolve-AppPc "$($a.nom)"; if (-not $r.ok -or $r.site) { return (Rep $false (& $script:AppRefus $r "$($a.nom)")) }
        $f = Select-FenetrePc $r.nom; if (-not $f) { return (Rep $false (Get-RefusSansFenetre $r.nom)) }
        $zone = Get-ZoneFenetre $f
        if ("$($a.ecran)") { $sel = Select-Ecran "$($a.ecran)"; if ($sel -and $sel.ecran) { $zone = @{ X = $sel.ecran.zone.X; Y = $sel.ecran.zone.Y; Width = $sel.ecran.zone.Width; Height = $sel.ecran.zone.Height } } }
        Set-FenetreEtat $f "$($a.mode)" $zone
        Rep $true (Get-Politesse 'fait')
    } { param($a) "fenêtre $($a.nom) : $($a.mode)$(if ($a.ecran) { ' sur l''écran ' + $a.ecran })" }
    Add-Action 'pc_reduire_tout' 1 'réduire toutes les fenêtres' 'pc_reduire_tout() : réduit toutes les fenêtres (jamais l''orbe de Jarvis)' {
        param($a) $n = 0; foreach ($f in (Get-FenetresPc)) { Set-FenetreEtat $f 'reduire' $null; $n++ }
        Rep $true (Get-Politesse 'fait_action' @{ x = "j'ai réduit $n fenêtre$(if ($n -gt 1) { 's' })" })
    } { param($a) 'réduire toutes les fenêtres' }
    Add-Action 'pc_media' 1 'commande média' 'pc_media(touche : pause|suivant|precedent) : touche multimédia' {
        param($a) $vk = switch ("$($a.touche)") { 'pause' { 0xB3 } 'suivant' { 0xB0 } 'precedent' { 0xB1 } default { 0 } }
        if (-not $vk) { return (Rep $false (Get-Politesse 'incompris')) }; Invoke-SystemePc 'media' "$vk"; Rep $true (Get-Politesse 'silencieux')
    } { param($a) "média : $($a.touche)" }
    Add-Action 'pc_capture' 1 'capture d''écran' 'pc_capture() : enregistre une capture d''écran dans le dossier de captures' {
        param($a) $d = Get-DossierCaptures; if (-not (Test-Path $d)) { New-Item -ItemType Directory $d -Force | Out-Null }
        $f = Join-Path $d ("capture-{0}.png" -f (Get-Date -Format 'yyyyMMdd-HHmmss')); Invoke-SystemePc 'capture' $f; Write-Journal -Action 'Capture d''écran' -Resultat $f; Rep $true (Get-Politesse 'fait_action' @{ x = 'la capture est enregistrée' })
    } { param($a) 'capture d''écran' }
    Add-Action 'pc_verrouiller' 1 'verrouiller le PC' 'pc_verrouiller() : verrouille la session Windows' { param($a) Invoke-SystemePc 'verrouiller'; Rep $true (Get-Politesse 'fait_action' @{ x = 'je verrouille le PC' }) } { param($a) 'verrouiller le PC' }
    Add-Action 'pc_redemarrer' 2 'redémarrer le PC' 'pc_redemarrer() : redémarre le PC dans 20 secondes (confirmation)' { param($a) Invoke-SystemePc 'redemarrer'; Rep $true ((Get-Politesse 'fait_action' @{ x = 'je redémarre dans vingt secondes' }) + ' ' + (Get-Politesse 'annulable')) } { param($a) 'REDÉMARRER le PC' }
    Add-Action 'pc_veille' 2 'mettre le PC en veille' 'pc_veille() : met le PC en veille (confirmation)' { param($a) Invoke-SystemePc 'veille'; Rep $true (Get-Politesse 'fait_action' @{ x = 'je mets le PC en veille' }) } { param($a) 'mettre le PC en VEILLE' }
    Add-Action 'pc_eteindre' 2 'éteindre le PC' 'pc_eteindre() : éteint le PC dans 20 secondes (confirmation)' { param($a) Invoke-SystemePc 'eteindre'; Rep $true ((Get-Politesse 'fait_action' @{ x = "j'éteins dans vingt secondes" }) + ' ' + (Get-Politesse 'annulable')) } { param($a) 'ÉTEINDRE le PC' }
    Add-Action 'pc_annuler_arret' 1 'annuler l''extinction' 'pc_annuler_arret() : annule un redémarrage ou une extinction en attente' { param($a) Invoke-SystemePc 'annuler'; Rep $true (Get-Politesse 'fait_action' @{ x = "l'extinction est annulée" }) } { param($a) 'annuler l''extinction' }
    Add-Action 'pc_dossier' 1 'ouvrir un dossier autorisé' 'pc_dossier(nom) : ouvre un dossier de la liste autorisée (documents, téléchargements, bureau, projets…)' {
        param($a) $r = Resolve-DossierPc "$($a.nom)"
        if (-not $r.ok) { return (Rep $false (Get-Politesse 'refus' @{ raison = "ce dossier n'est pas dans la liste autorisée" })) }
        if (-not (Test-Path $r.chemin)) { return (Rep $false (Get-Politesse 'refus' @{ raison = "le dossier $($r.nom) n'existe pas" })) }
        $res = & $script:Actions['ouvrir_chemin'].run ([pscustomobject]@{ type = 'ouvrir_chemin'; chemin = $r.chemin }); if ($res -and $res.ok) { Rep $true (Get-Politesse 'fait_action' @{ x = "j'ouvre le dossier $($r.nom)" }) } else { Rep $false (Get-Politesse 'refus' @{ raison = "je n'ai pas pu ouvrir $($r.nom)" }) }
    } { param($a) "ouvrir le dossier $($a.nom)" }
    Add-Action 'pc_trouver_fichier' 1 'trouver un fichier' 'pc_trouver_fichier(nom) : cherche un fichier dans les dossiers autorisés (aucune suppression)' {
        param($a) $f = @(Find-FichiersPc "$($a.nom)")
        if (-not $f.Count) { return (Rep $true (Get-Politesse 'rien_trouve' @{ x = "« $($a.nom) »" })) }
        $liste = ($f | Select-Object -First 3 | ForEach-Object { "$($_.Name) dans $($_.DirectoryName)" }) -join ' ; '
        Rep $true (Get-Politesse 'info' @{ x = "$($f.Count) fichier$(if ($f.Count -gt 1) { 's' }) : $liste" })
    } { param($a) "trouver le fichier $($a.nom)" }
    Add-Action 'winget_proposer' 1 'proposer des applications' 'winget_proposer(requete) : propose 1 à 3 applications gratuites de la source officielle winget ; n''installe RIEN' {
        param($a) $q = "$($a.requete)".Trim()
        if ($q.Length -lt 2 -or $q -notmatch '^[\p{L}0-9 .+#-]{2,60}$') { return (Rep $false (Get-Politesse 'incompris')) }
        $r = @(Invoke-WingetRecherche $q); $script:WingetPropose = @($r)
        Write-Journal -Action 'winget : proposition' -Resultat "« $q » : $(@($r | ForEach-Object { $_.id }) -join ', ')"
        if (-not $r.Count) { return (Rep $true (Get-Politesse 'rien_trouve' @{ x = "« $q »" })) }
        $i = 0; Rep $true (Get-Politesse 'info' @{ x = ("$($r.Count) option$(if ($r.Count -gt 1) { 's' }) gratuite$(if ($r.Count -gt 1) { 's' }) : " + (($r | ForEach-Object { $i++; "$i, $($_.nom)" }) -join ' ; ') + '. Dites « installe le numéro » suivi du chiffre pour en installer une') })
    } { param($a) "chercher une application : $($a.requete)" }
    Add-Action 'winget_installer' 2 'installer une application proposée' 'winget_installer(numero) : installe UNE option qui vient d''être proposée (source officielle winget uniquement ; confirmation obligatoire)' {
        param($a) $n = [int]$a.numero
        if ($n -lt 1 -or $n -gt $script:WingetPropose.Count) { return (Rep $false (Get-Politesse 'refus' @{ raison = 'aucune proposition à ce numéro' })) }
        $p = $script:WingetPropose[$n - 1]
        if ("$($p.id)" -notmatch '^[A-Za-z0-9][A-Za-z0-9.+_-]{1,80}$') { return (Rep $false (Get-Politesse 'refus' @{ raison = 'identifiant refusé' })) }
        Write-Journal -Action 'winget : installation' -Resultat "$($p.id) (source winget) — confirmée par Liam"
        $s = Invoke-WingetInstall $p.id; Rep $true (Get-Politesse 'fait_action' @{ x = "l'installation de $($p.nom) est terminée" }) $s
    } { param($a) "INSTALLER l'option $($a.numero) proposée (winget)" }
    Add-Action 'capacites' 1 'lister les commandes' 'capacites(suite?) : affiche au tableau la liste de ce que Jarvis sait faire et en énumère 5 à voix haute à la fois (suite=true : les 5 suivantes)' {
        param($a)
        $script:CapacitesJusqua = (Get-Date).AddSeconds(90)
        $l = @($script:CapacitesVoix)
        if (-not ($a.suite -eq $true -or "$($a.suite)" -eq 'True')) { $script:CapaciteIdx = 0 }
        if ($script:CapaciteIdx -ge $l.Count) { $script:CapaciteIdx = 0; return (Rep $true (Get-Politesse 'fin_liste')) }
        $lot = @($l | Select-Object -Skip $script:CapaciteIdx -First 5 | ForEach-Object { $_.dit })
        $script:CapaciteIdx += $lot.Count
        $reste = $l.Count - $script:CapaciteIdx
        $t = Get-Politesse 'liste_capacites' @{ x = ($lot -join ' ; ') }
        if ($reste -gt 0) { $t += ' ' + (Get-Politesse 'suite_capacites') }
        Rep $true $t
    } { param($a) 'liste des commandes' }
}
