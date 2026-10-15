# Mode jeu / ne pas déranger.
# Actif quand : une application plein écran ou un jeu est au premier plan, OU « mode jeu » (voix), OU Ctrl+Alt+G, OU pendant des heures
# choisies dans config.json. Alors Jarvis : se tait complètement, ne joue aucune musique ni aucun son, masque son tableau de bord,
# ne prend jamais le focus, garde seulement les alertes GRAVES (en silence) et résume ce qu'il a retenu à « mode jeu off ».
#
# config.json : "mode_jeu": { "auto": true,
#                              "applications": [ "steam", "roblox", "minecraft", ... ],          (noms de processus ou parties de noms)
#                              "heures": [ { "de": "20:00", "a": "23:30" } ],                    (vide par défaut)
#                              "plein_ecran_auto": true }                                       (toute application plein écran déclenche le mode)
#               "raccourcis": { "jeu": "Ctrl+Alt+G" }
# Lecture seule du premier plan : aucune API de prise de focus, aucune fenêtre n'est modifiée par la détection.
$script:ModeJeu = $false; $script:ModeJeuSource = ''; $script:ModeJeuDepuis = [datetime]::MinValue
$script:ModeJeuManuel = $false; $script:JeuIgnorer = $false
$script:JeuVu = 0; $script:JeuAbsent = 0
$script:ProchainTestJeu = [datetime]::MinValue
$script:VisageCacheParJeu = $false
$script:DernierResumeJeu = ''

if (-not ('JarvisFg' -as [type])) {
    Add-Type -TypeDefinition @'
using System; using System.Text; using System.Runtime.InteropServices;
public class JarvisFg {
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
  [StructLayout(LayoutKind.Sequential)] public struct MONITORINFO { public int cb; public RECT mon; public RECT work; public uint flags; }
  [DllImport("user32.dll")] static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] static extern int GetWindowThreadProcessId(IntPtr h, out int pid);
  [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern int GetClassName(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] static extern IntPtr MonitorFromWindow(IntPtr h, uint flags);
  [DllImport("user32.dll")] static extern bool GetMonitorInfo(IntPtr m, ref MONITORINFO mi);
  [DllImport("user32.dll", EntryPoint = "GetWindowLongW")] static extern int GetWindowLong(IntPtr h, int i);
  // LECTURE SEULE : "pid|classe|titre|plein" ("plein" = 1 si la fenêtre sans barre de titre couvre tout son écran, comme un jeu ou une vidéo plein écran).
  public static string Lire() {
    IntPtr h = GetForegroundWindow(); if (h == IntPtr.Zero) return "";
    int pid; GetWindowThreadProcessId(h, out pid);
    var c = new StringBuilder(256); GetClassName(h, c, 256);
    var t = new StringBuilder(256); GetWindowText(h, t, 256);
    RECT r; if (!GetWindowRect(h, out r)) return "";
    IntPtr m = MonitorFromWindow(h, 2); var mi = new MONITORINFO(); mi.cb = Marshal.SizeOf(typeof(MONITORINFO));
    bool plein = false;
    if (m != IntPtr.Zero && GetMonitorInfo(m, ref mi)) {
      bool couvre = r.L <= mi.mon.L && r.T <= mi.mon.T && r.R >= mi.mon.R && r.B >= mi.mon.B;
      bool titre = (GetWindowLong(h, -16) & 0x00C00000) != 0;      // WS_CAPTION : une fenêtre maximisée classique garde sa barre de titre
      plein = couvre && !titre;
    }
    return pid + "|" + c + "|" + t.ToString().Replace("|", "/") + "|" + (plein ? "1" : "0");
  }
}
'@
}

function Get-ConfigJeu {
    $c = $Config.mode_jeu
    $apps = if ($c -and $c.applications) { @($c.applications | ForEach-Object { "$_".ToLower() }) } else {
        @('steam', 'steamwebhelper', 'roblox', 'minecraft', 'eldenring', 'valorant', 'fortnite', 'leagueoflegends', 'league of legends', 'cs2', 'csgo', 'dota2', 'gta5', 'rdr2', 'overwatch', 'r5apex', 'rocketleague', 'genshin', 'cyberpunk', 'witcher3') }
    @{ auto = $(if ($c -and $c.PSObject.Properties['auto']) { [bool]$c.auto } else { $true })
       plein_ecran = $(if ($c -and $c.PSObject.Properties['plein_ecran_auto']) { [bool]$c.plein_ecran_auto } else { $true })
       applications = $apps
       heures = @($(if ($c -and $c.heures) { $c.heures })) }
}

function Test-ModeJeu { $script:ModeJeu -eq $true }

function Get-PremierPlan {
    # @{ pid; proc; classe; titre; plein } ou $null. Lecture seule.
    try {
        $s = [JarvisFg]::Lire(); if (-not $s) { return $null }
        $p = $s.Split('|', 4)
        $proc = ''; try { $proc = (Get-Process -Id ([int]$p[0]) -ErrorAction Stop).ProcessName } catch {}
        @{ pid = [int]$p[0]; proc = $proc; classe = $p[1]; titre = $p[2]; plein = ($p[3] -eq '1') }
    } catch { $null }
}

function Test-JeuPremierPlan($info, $cfg = $null) {
    # PURE. Un jeu ou une application plein écran est-il au premier plan ? Jamais l'orbe de Jarvis ni le bureau.
    if (-not $info) { return $false }
    if (-not $cfg) { $cfg = Get-ConfigJeu }
    $proc = "$($info.proc)".ToLower(); $titre = "$($info.titre)"; $classe = "$($info.classe)"
    if ($titre -like 'JarvisOrb*') { return $false }
    if ($script:EdgePid -and $info.pid -and (Get-ArbrePids $script:EdgePid) -contains $info.pid) { return $false }
    if ($classe -in 'Progman', 'WorkerW', 'Shell_TrayWnd', 'Shell_SecondaryTrayWnd', 'NotifyIconOverflowWindow') { return $false }
    if ($proc -in 'explorer', 'searchhost', 'startmenuexperiencehost', 'lockapp', 'shellexperiencehost', 'textinputhost', 'applicationframehost' -and -not $info.plein) { return $false }
    foreach ($a in $cfg.applications) {
        if (-not $a) { continue }
        if ($proc -eq $a -or $proc -like "*$a*") { return $true }       # nom du processus seulement : un onglet de navigateur intitulé « Minecraft » n'est pas un jeu
    }
    if ($proc -in 'javaw', 'java' -and $titre.ToLower().Contains('minecraft')) { return $true }       # Minecraft Java tourne dans javaw
    if ($cfg.plein_ecran -and $info.plein -and $proc -notin 'explorer', 'searchhost', 'lockapp') { return $true }
    $false
}

function Test-DansHeuresJeu([datetime]$now = (Get-Date), $heures = $null) {
    if ($null -eq $heures) { $heures = (Get-ConfigJeu).heures }
    $h = $now.ToString('HH:mm')
    foreach ($pl in @($heures)) {
        if (-not $pl -or -not $pl.de -or -not $pl.a) { continue }
        $de = "$($pl.de)"; $a = "$($pl.a)"
        if ($de -le $a) { if ($h -ge $de -and $h -lt $a) { return $true } }
        else { if ($h -ge $de -or $h -lt $a) { return $true } }          # plage qui passe minuit (ex. 22:00 -> 02:00)
    }
    $false
}

function Enter-ModeJeu([string]$source) {
    if ($script:ModeJeu) { return }
    $script:ModeJeu = $true; $script:ModeJeuSource = $source; $script:ModeJeuDepuis = Get-Date
    $script:Retenu.Clear()
    if (Get-Command Set-FlagModeJeu -ErrorAction SilentlyContinue) { Set-FlagModeJeu $true }       # la veille de fond se met en pause
    if (Get-Command Switch-EcouteMode -ErrorAction SilentlyContinue) { Switch-EcouteMode 'jeu' }   # le GPU est libéré (reconnaissance légère sur CPU)
    if (Get-Command Release-GpuModeles -ErrorAction SilentlyContinue) { Release-GpuModeles }
    if (Get-Command Stop-Musiques -ErrorAction SilentlyContinue) { Stop-Musiques }
    if (Get-Command Set-SonsParole -ErrorAction SilentlyContinue) { Set-SonsParole $false }
    # Le tableau de bord est masqué (ShowWindow SW_HIDE sur NOTRE fenêtre, repérée par le PID de l'Edge lancé par Jarvis) : aucun focus n'est touché.
    $script:VisageCacheParJeu = $false
    if ($script:VisageHwnd -and $script:VisageHwnd -ne [IntPtr]::Zero -and $script:VisageVisible) {
        try { if ([JarvisWin]::Montrer($script:VisageHwnd, $false)) { $script:VisageVisible = $false; $script:VisageCacheParJeu = $true } } catch {}
    }
    Write-Journal -Action 'MODE JEU activé' -Resultat "source : $source ; Jarvis se tait, aucun son, tableau de bord masqué, alertes graves gardées en silence"
}

function Get-ResumeJeu {
    # Ce que Jarvis a retenu : uniquement des faits réellement survenus, jamais de remplissage.
    $graves = @($script:Retenu | Where-Object { $_.type -eq 'alerte' -and $_.grave })
    $rappels = @($script:Retenu | Where-Object { $_.type -eq 'rappel' })
    $paroles = @($script:Retenu | Where-Object { $_.type -eq 'parole' })
    $p = New-Object System.Collections.Generic.List[string]
    if ($graves.Count) { $p.Add("$($graves.Count) alerte$(if ($graves.Count -gt 1) { 's graves' } else { ' grave' }) : " + (($graves | ForEach-Object { "$($_.texte) à $($_.heure)" }) -join ' ; ')) }
    if ($rappels.Count) { $p.Add("$($rappels.Count) rappel$(if ($rappels.Count -gt 1) { 's' }) : " + (($rappels | ForEach-Object { "$($_.texte) (prévu à $($_.heure))" }) -join ' ; ')) }
    if ($paroles.Count) { $p.Add("$($paroles.Count) message$(if ($paroles.Count -gt 1) { 's' }) retenu$(if ($paroles.Count -gt 1) { 's' }) au tableau de bord") }
    if (-not $p.Count) { return 'Rien à signaler pendant votre partie, monsieur.' }
    'Pendant votre partie, monsieur : ' + ($p -join '. ') + '.'
}

function Exit-ModeJeu([string]$source) {
    if (-not $script:ModeJeu) { return $null }
    $resume = Get-ResumeJeu
    $duree = [int]((Get-Date) - $script:ModeJeuDepuis).TotalMinutes
    $script:ModeJeu = $false; $script:ModeJeuSource = ''
    if (Get-Command Set-FlagModeJeu -ErrorAction SilentlyContinue) { Set-FlagModeJeu $false }
    if (Get-Command Switch-EcouteMode -ErrorAction SilentlyContinue) { Switch-EcouteMode 'normal' } # le modèle est rechargé aussitôt
    if ($script:VisageCacheParJeu -and $script:VisageHwnd -ne [IntPtr]::Zero) {
        try { if ([JarvisWin]::Montrer($script:VisageHwnd, $true)) { $script:VisageVisible = $true } } catch {}      # réaffiché SANS activation
    }
    $script:VisageCacheParJeu = $false
    if (Get-Command Start-Ambiance -ErrorAction SilentlyContinue) { Start-Ambiance }        # reprend seulement si l'ambiance est activée dans config.json
    $script:DernierResumeJeu = $resume
    Write-Journal -Action 'MODE JEU terminé' -Resultat "après $duree min ; $resume"
    $script:Retenu.Clear()
    $resume
}

function Switch-ModeJeu([string]$source = 'raccourci') {
    if ($script:ModeJeu) { [void](Set-ModeJeu $false $source) } else { [void](Set-ModeJeu $true $source) }
}

function Set-ModeJeu([bool]$on, [string]$source = 'ordre') {
    # Commande de Liam (voix, raccourci). Retourne le résumé quand on sort du mode.
    if ($on) { $script:ModeJeuManuel = $true; $script:JeuIgnorer = $false; Enter-ModeJeu "manuel ($source)"; return $null }
    $script:ModeJeuManuel = $false
    $script:JeuIgnorer = $true          # tant que le jeu / l'horaire continue, on ne se réactive pas tout seul
    $r = Exit-ModeJeu "manuel ($source)"
    $r
}

function Update-ModeJeu {
    # Appelée par la boucle principale ; teste toutes les 3 s au plus. Deux relevés consécutifs sont nécessaires pour entrer ou sortir.
    $now = Get-Date
    if ($now -lt $script:ProchainTestJeu) { return }
    $script:ProchainTestJeu = $now.AddSeconds(3)
    $cfg = Get-ConfigJeu
    $horaire = Test-DansHeuresJeu $now $cfg.heures
    $jeu = $false
    if ($cfg.auto) { $jeu = Test-JeuPremierPlan (Get-PremierPlan) $cfg }
    if ($script:ModeJeuManuel) { return }                         # activé à la main : on ne sort que sur ordre
    if ($script:JeuIgnorer) { if (-not $jeu -and -not $horaire) { $script:JeuIgnorer = $false }; $script:JeuVu = 0; return }
    if ($horaire -or $jeu) {
        $script:JeuAbsent = 0
        $script:JeuVu++
        if (-not $script:ModeJeu -and ($horaire -or $script:JeuVu -ge 2)) { Enter-ModeJeu $(if ($horaire) { 'horaire' } else { 'jeu ou plein écran détecté' }) }
    } else {
        $script:JeuVu = 0
        if ($script:ModeJeu) {
            $script:JeuAbsent++
            if ($script:JeuAbsent -ge 2) {
                $script:JeuAbsent = 0
                $r = Exit-ModeJeu 'fin automatique'
                if ($r -and (Get-Command Add-Conv -ErrorAction SilentlyContinue)) { Add-Conv 'jarvis' $r }       # affiché au tableau de bord, jamais dit à voix haute
            }
        }
    }
}

Add-Action 'mode_jeu' 1 'activer ou quitter le mode jeu' 'mode_jeu(etat) : etat = "on" ou "off". Mode jeu / ne pas déranger : Jarvis se tait, aucun son, tableau masqué ; "off" résume ce qui a été retenu' {
    param($a)
    if ("$($a.etat)" -match '^(?i:off|non|fin|stop|desactive|arret)') {
        if (-not $script:ModeJeu) { return Rep $true 'Le mode jeu n''est pas actif, monsieur.' }
        $r = Set-ModeJeu $false 'ordre vocal'; return Rep $true $r
    }
    if ($script:ModeJeu) { return Rep $true '' }
    [void](Set-ModeJeu $true 'ordre vocal'); Rep $true ''
} { param($a) "mode jeu $($a.etat)" }

Protect-ActionsTest      # (dernier module qui déclare des actions) : en mode test, aucune action réelle
