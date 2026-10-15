# Choix de l'écran de Jarvis. Réglage config.json "ecran_jarvis" :
#   "principal" (défaut : l'ÉCRAN PRINCIPAL de Windows) | "droite" | "gauche" | un index (0 = écran le plus à gauche) | un nom ("huawei", "odyssey", ...) | "\\.\DISPLAY1"
# Écran introuvable : repli sur l'écran principal.
Add-Type -AssemblyName System.Windows.Forms
Add-Type -TypeDefinition @'
using System; using System.Runtime.InteropServices;
public class JarvisEcran {
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
  [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
  public struct DD { public int cb; [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)] public string Name; [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 128)] public string Str; public int Flags; [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 128)] public string Id; [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 128)] public string Key; }
  [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern bool EnumDisplayDevices(string dev, uint i, ref DD d, uint f);
  public static string IdMoniteur(string deviceName) {
    DD d = new DD(); d.cb = Marshal.SizeOf(d);
    return EnumDisplayDevices(deviceName, 0, ref d, 0) ? d.Id : "";
  }
}
'@
[void][JarvisEcran]::SetProcessDPIAware()   # coordonnées physiques, quelle que soit la mise à l'échelle

function Get-NomsMoniteurs {
    # Table "code PnP (ex. HWV2402)" -> nom lisible (ex. "HWV HUAWEI AD80HW"), via WMI
    $t = @{}
    try {
        foreach ($m in Get-CimInstance -Namespace root\wmi -ClassName WmiMonitorID -ErrorAction Stop) {
            $nom = [Text.Encoding]::ASCII.GetString(@($m.UserFriendlyName | Where-Object { $_ -ne 0 }))
            $fab = [Text.Encoding]::ASCII.GetString(@($m.ManufacturerName | Where-Object { $_ -ne 0 }))
            if ($m.InstanceName -match '^DISPLAY\\([^\\]+)\\') { $t[$Matches[1]] = "$fab $nom".Trim() }
        }
    } catch {}
    $t
}

function Get-Ecrans {
    # Liste triée de gauche à droite : index, périphérique, nom du moniteur, position/taille
    $noms = Get-NomsMoniteurs
    $i = 0
    foreach ($s in ([Windows.Forms.Screen]::AllScreens | Sort-Object { $_.Bounds.X }, { $_.Bounds.Y })) {
        $id = [JarvisEcran]::IdMoniteur($s.DeviceName); $nom = ''
        if ($id -match '^MONITOR\\([^\\]+)\\') { $nom = $noms[$Matches[1]] }
        [pscustomobject]@{ index = $i; peripherique = $s.DeviceName; nom = "$nom"; primaire = $s.Primary; bounds = $s.Bounds; zone = $s.WorkingArea }
        $i++
    }
}

function Select-Ecran($choix, $ecrans = $null) {
    # Retourne l'écran choisi (vide = écran principal). Si le choix est introuvable : repli sur l'écran principal, avec une raison.
    if (-not $ecrans) { $ecrans = @(Get-Ecrans) } else { $ecrans = @($ecrans) }
    $c = "$choix".Trim(); $res = $null; $raison = ''
    switch -Regex ($c.ToLower()) {
        '^(droite|right)$'  { $res = $ecrans | Sort-Object { $_.bounds.X } | Select-Object -Last 1 }
        '^(gauche|left)$'   { $res = $ecrans | Sort-Object { $_.bounds.X } | Select-Object -First 1 }
        '^(|principal|primary)$' { $res = $ecrans | Where-Object primaire | Select-Object -First 1 }
        '^\d+$'             { $res = $ecrans | Where-Object { $_.index -eq [int]$c } | Select-Object -First 1 }
        default             { $res = $ecrans | Where-Object { $_.peripherique -ieq $c -or ($_.nom -and $_.nom -like "*$c*") } | Select-Object -First 1 }
    }
    if (-not $res) { $res = $ecrans | Where-Object primaire | Select-Object -First 1; if (-not $res) { $res = $ecrans | Sort-Object { $_.bounds.X } | Select-Object -First 1 }; if ("$c" -ne '' -and $c -notmatch '^(principal|primary)$') { $raison = "écran « $c » introuvable, repli sur l'écran principal" } }
    [pscustomobject]@{ ecran = $res; raison = $raison }
}
