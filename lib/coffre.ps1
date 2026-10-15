# Coffre Bitwarden (bw CLI, serveur européen).
# - Liam déverrouille lui-même (boîte de dialogue masquée) ; Jarvis ne garde que le jeton de session, EN MÉMOIRE.
# - Les mots de passe ne sont jamais lus à voix haute, jamais journalisés, jamais envoyés à Claude, jamais écrits sur le disque,
#   et saisis par frappe clavier (pas de presse-papiers).
Add-Type -AssemblyName System.Windows.Forms
$script:BwSession = $null
$script:BwServeur = 'https://vault.bitwarden.eu'
$script:BwCmd = $null

function Find-Bw {
    if ($script:BwCmd) { return $script:BwCmd }
    $g = Get-Command bw -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($g) { $c = [IO.Path]::ChangeExtension($g.Source, '.cmd'); if (Test-Path $c) { $script:BwCmd = $c } elseif ($g.Source -match '\.exe$') { $script:BwCmd = $g.Source } }
    $script:BwCmd
}

function Invoke-Bw([string[]]$arguments, [hashtable]$env2 = @{}, [int]$timeoutSec = 60) {
    # Les secrets passent par l'environnement du processus enfant, jamais par la ligne de commande.
    $bw = Find-Bw; if (-not $bw) { return @{ code = 127; sortie = 'bw introuvable'; err = '' } }
    $psi = New-Object Diagnostics.ProcessStartInfo 'cmd.exe', ('/c ""' + $bw + '" ' + (($arguments | ForEach-Object { if ($_ -match '[\s"&|<>^]') { '"' + ($_ -replace '"', '') + '"' } else { $_ } }) -join ' ') + ' --nointeraction"')
    $psi.UseShellExecute = $false; $psi.CreateNoWindow = $true
    $psi.RedirectStandardOutput = $true; $psi.RedirectStandardError = $true
    $psi.StandardOutputEncoding = [Text.Encoding]::UTF8; $psi.StandardErrorEncoding = [Text.Encoding]::UTF8
    if ($script:BwSession) { $psi.EnvironmentVariables['BW_SESSION'] = $script:BwSession }
    foreach ($k in $env2.Keys) { $psi.EnvironmentVariables[$k] = $env2[$k] }
    $p = [Diagnostics.Process]::Start($psi)
    $so = $p.StandardOutput.ReadToEndAsync(); $se = $p.StandardError.ReadToEndAsync()
    $fin = (Get-Date).AddSeconds($timeoutSec)
    while (-not $p.HasExited) {
        if ((Get-Date) -gt $fin -or (Test-Stop)) { try { $p.Kill() } catch {}; return @{ code = -1; sortie = ''; err = 'interrompu' } }
        Invoke-Pump; Start-Sleep -Milliseconds 100
    }
    $p.WaitForExit()
    @{ code = $p.ExitCode; sortie = $so.Result.Trim(); err = (Hide-Secrets $se.Result.Trim()) }
}

function Initialize-Coffre {
    # Impose le serveur européen avant tout (possible seulement si aucun compte n'est connecté).
    if (-not (Find-Bw)) { return 'absent' }
    $s = Get-CoffreStatut
    if ($s -eq 'unauthenticated') {
        $cur = (Invoke-Bw @('config', 'server')).sortie
        if ($cur -notlike "*vault.bitwarden.eu*") { [void](Invoke-Bw @('config', 'server', $script:BwServeur)) }
    }
    $s
}

function Get-CoffreStatut {
    $r = Invoke-Bw @('status')
    if ($r.code -ne 0) { return 'erreur' }
    try {
        $j = $r.sortie | ConvertFrom-Json
        if ($j.serverUrl -and $j.serverUrl -notlike '*vault.bitwarden.eu*') { return 'mauvais_serveur' }
        if ($script:BwSession -and $j.status -eq 'locked') { $script:BwSession = $null }
        return $j.status
    } catch { return 'erreur' }
}

# ---------- Déverrouillage NON BLOQUANT ----------
# La fenêtre (lib\coffre-dialogue.ps1) tourne dans un processus séparé : Jarvis continue de fonctionner pendant qu'elle attend votre mot de passe.
# Seul le jeton de session revient, en mémoire ; le mot de passe principal ne passe jamais par Jarvis.
$script:CoffreProc = $null; $script:CoffreSortie = $null; $script:CoffreAnnonce = $false; $script:CoffreMode = ''

function Start-CoffreDialogue([string]$etat = '', [string]$simule = '', [int]$simuleSecondes = 0) {
    # Retourne un texte. Ne bloque JAMAIS (le processus est lancé puis on rend la main).
    if ($script:Actif -eq $false) { return 'Jarvis est en sourdine : aucune fenêtre ne s''ouvre.' }     # sourdine totale : pas de popup
    if ((Test-ModeTest) -and -not $simule) { return 'Fenêtre de déverrouillage non ouverte (mode test).' }
    if ($script:CoffreProc -and -not $script:CoffreProc.HasExited) { return 'La fenêtre de déverrouillage est déjà ouverte.' }
    if (-not $etat) { $etat = Initialize-Coffre }
    if ($etat -eq 'absent') { return "Bitwarden CLI n'est pas installé." }
    if ($etat -eq 'mauvais_serveur') { return 'Le compte est connecté à un autre serveur que le serveur européen. Déconnectez-le (bw logout) puis réessayez.' }
    if ($etat -eq 'unlocked' -and $script:BwSession) { return 'Le coffre est déjà déverrouillé.' }
    $mode = if ($etat -eq 'unauthenticated') { 'login' } else { 'unlock' }
    $args2 = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$(Join-Path $PSScriptRoot 'coffre-dialogue.ps1')`"", '-Mode', $mode)
    if ($env:BW_EMAIL) { $args2 += @('-Email', "`"$env:BW_EMAIL`"") }
    if ($simule) { $args2 += @('-SimuleResultat', "`"$simule`"", '-SimuleSecondes', "$simuleSecondes") }
    $psi = New-Object Diagnostics.ProcessStartInfo 'powershell.exe', ($args2 -join ' ')
    $psi.UseShellExecute = $false; $psi.CreateNoWindow = $true; $psi.RedirectStandardOutput = $true      # on ne lit que le jeton de session
    $script:CoffreProc = [Diagnostics.Process]::Start($psi)
    $script:CoffreSortie = $script:CoffreProc.StandardOutput.ReadToEndAsync(); $script:CoffreMode = $mode
    Write-Journal -Action 'Coffre Bitwarden' -Resultat "fenêtre de déverrouillage ouverte ($mode) ; Jarvis continue sans accès aux mots de passe"
    'Fenêtre de déverrouillage ouverte : saisissez votre mot de passe principal. Je continue en attendant.'
}

function Invoke-PumpCoffre {
    # Appelée en permanence : récupère le résultat quand la fenêtre se ferme. Ne bloque jamais.
    if (-not $script:CoffreProc -or -not $script:CoffreProc.HasExited) { return }
    $sortie = ''; try { $sortie = "$($script:CoffreSortie.Result)" } catch {}
    $script:CoffreProc = $null; $script:CoffreSortie = $null
    $ligne = ($sortie -split "`r?`n" | Where-Object { $_ -match '^(SESSION:|ERREUR:|ANNULE)' } | Select-Object -First 1)
    if ($ligne -like 'SESSION:*') {
        $script:BwSession = $ligne.Substring(8).Trim(); if ($script:BwSession.Length -ge 8) { $script:Secrets += $script:BwSession }
        Write-Journal -Action 'Déverrouillage du coffre' -Resultat 'réussi (session gardée en mémoire seulement, rien sur le disque)'
        $script:Entrees.Enqueue(@{ src = 'systeme'; texte = '[coffre] deverrouille'; entendu = $false })
    }
    elseif ($ligne -like 'ERREUR:*') { Write-Journal -Action 'Déverrouillage du coffre' -Resultat ("échec : " + (Hide-Secrets $ligne.Substring(7))); $script:Entrees.Enqueue(@{ src = 'systeme'; texte = '[coffre] echec'; entendu = $false }) }
    else { Write-Journal -Action 'Déverrouillage du coffre' -Resultat 'reporté par Liam (« Plus tard »)' }
}

function Stop-CoffreDialogue { if ($script:CoffreProc -and -not $script:CoffreProc.HasExited) { try { Stop-Process -Id $script:CoffreProc.Id -Force -ErrorAction SilentlyContinue } catch {} }; $script:CoffreProc = $null }

function Open-Coffre { Start-CoffreDialogue }      # compatibilité : non bloquant
function Close-Coffre { $script:BwSession = $null; [void](Invoke-Bw @('lock')) }

function Find-ItemsCoffre([string]$recherche) {
    # Retourne uniquement id/nom/présence d'identifiant : jamais les mots de passe.
    $r = Invoke-Bw @('list', 'items', '--search', $recherche)
    if ($r.code -ne 0) { return $null }
    try { $items = @($r.sortie | ConvertFrom-Json | ForEach-Object { $_ }) } catch { return $null }
    $res = @($items | Where-Object { $_.type -eq 1 } | ForEach-Object { [pscustomobject]@{ id = $_.id; nom = $_.name; identifiant = [bool]$_.login.username } })
    $items = $null; $r = $null
    , $res
}

Add-Type -TypeDefinition @'
using System; using System.Text; using System.Runtime.InteropServices;
public class JarvisFenetre {
  [DllImport("user32.dll")] static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  public static string Titre() { var sb = new StringBuilder(256); GetWindowText(GetForegroundWindow(), sb, 256); return sb.ToString(); }
}
'@

function ConvertTo-SendKeys([string]$t) { ($t.ToCharArray() | ForEach-Object { if ('+^%~(){}[]'.Contains([string]$_)) { '{' + $_ + '}' } else { [string]$_ } }) -join '' }

Add-Action 'bitwarden_statut' 1 'lire l''état du coffre' 'bitwarden_statut() : dit si le coffre Bitwarden est verrouillé ou déverrouillé' {
    param($a)
    $s = Get-CoffreStatut
    Rep $true $(switch ($s) { 'unlocked' { 'Le coffre est déverrouillé.' } 'locked' { 'Le coffre est verrouillé.' } 'unauthenticated' { "Aucun compte Bitwarden n'est connecté." } 'absent' { "Bitwarden CLI n'est pas installé." } default { "État du coffre : $s" } })
} { param($a) "lire l'état du coffre" }

Add-Action 'bitwarden_deverrouiller' 1 'ouvrir la fenêtre de déverrouillage' 'bitwarden_deverrouiller() : ouvre la fenêtre où Liam saisit lui-même son mot de passe principal Bitwarden' {
    param($a)
    Rep $true (Start-CoffreDialogue)
} { param($a) "déverrouiller le coffre" }

Add-Action 'bitwarden_verrouiller' 1 'verrouiller le coffre' 'bitwarden_verrouiller() : verrouille le coffre et oublie le jeton de session' {
    param($a) Close-Coffre; Rep $true 'Coffre verrouillé.'
} { param($a) "verrouiller le coffre" }

Add-Action 'bitwarden_chercher' 1 'chercher un identifiant (noms seulement)' 'bitwarden_chercher(recherche) : liste les NOMS des éléments du coffre correspondant (jamais les mots de passe)' {
    param($a)
    if ((Get-CoffreStatut) -ne 'unlocked') { return Rep $false 'Le coffre est verrouillé. Dites « déverrouille le coffre » pour ouvrir la fenêtre ; je continue de fonctionner en attendant.' }
    $it = Find-ItemsCoffre "$($a.recherche)"
    if ($null -eq $it) { return Rep $false 'Recherche impossible dans le coffre.' }
    if ($it.Count -eq 0) { return Rep $true "Aucun élément ne correspond à « $($a.recherche) »." }
    Rep $true ("$($it.Count) élément(s) : " + (($it | Select-Object -First 8 | ForEach-Object { $_.nom }) -join ', '))
} { param($a) "chercher « $($a.recherche) » dans le coffre" }

Add-Action 'bitwarden_saisir' 2 'saisir un identifiant dans un formulaire' 'bitwarden_saisir(recherche, champ?) : saisit au clavier, dans la fenêtre active, le mot de passe (champ="motdepasse", défaut), l''identifiant ("identifiant") ou les deux séparés par Tab ("les_deux"). Le mot de passe n''est jamais lu ni affiché' {
    param($a)
    if ((Get-CoffreStatut) -ne 'unlocked') { return Rep $false 'Le coffre est verrouillé. Dites « déverrouille le coffre » pour ouvrir la fenêtre ; je continue de fonctionner en attendant.' }
    $it = Find-ItemsCoffre "$($a.recherche)"
    if ($null -eq $it -or $it.Count -eq 0) { return Rep $false "Aucun élément du coffre ne correspond à « $($a.recherche) »." }
    if ($it.Count -gt 1) { return Rep $false ("Plusieurs éléments correspondent : " + (($it | Select-Object -First 5 | ForEach-Object { $_.nom }) -join ', ') + '. Précisez lequel.') }
    $titre = [JarvisFenetre]::Titre()
    if ($a.PSObject.Properties['_fenetre'] -and $a._fenetre -and $titre -ne $a._fenetre) { return Rep $false 'La fenêtre active a changé depuis la confirmation : saisie annulée.' }
    if (-not $titre -or $titre -like 'Jarvis*') { return Rep $false 'Aucun formulaire actif détecté : saisie annulée.' }
    if (Test-Courtier $titre) { return Rep $false 'Cette fenêtre est celle d''un courtier ou d''une banque : je ne saisis jamais d''identifiant là-bas.' }
    $champ = "$($a.champ)"; $id = $it[0].id; $n = 0; $pwd = $null; $usr = $null
    try {
        if ($champ -ne 'identifiant') {
            $r = Invoke-Bw @('get', 'password', $id); if ($r.code -ne 0 -or -not $r.sortie) { return Rep $false "Cet élément n'a pas de mot de passe." }
            $pwd = $r.sortie; $script:Secrets += $pwd   # tout écho accidentel sera masqué dans le journal
        }
        if ($champ -eq 'identifiant' -or $champ -eq 'les_deux') {
            $r2 = Invoke-Bw @('get', 'username', $id); $usr = $r2.sortie
            if ($usr) { $script:Secrets += $usr }
        }
        $touches = switch ($champ) { 'identifiant' { ConvertTo-SendKeys $usr } 'les_deux' { (ConvertTo-SendKeys $usr) + '{TAB}' + (ConvertTo-SendKeys $pwd) } default { ConvertTo-SendKeys $pwd } }
        Start-Sleep -Milliseconds 400
        [Windows.Forms.SendKeys]::SendWait($touches)
        $n = $touches.Length
    } finally {
        $script:Secrets = @($script:Secrets | Where-Object { $_ -ne $pwd -and $_ -ne $usr })
        $pwd = $null; $usr = $null; $touches = $null; $r = $null; $r2 = $null
    }
    $quoi = switch ($champ) { 'identifiant' { 'identifiant' } 'les_deux' { 'identifiant et mot de passe' } default { 'mot de passe' } }
    Rep $true "Saisie effectuée pour « $($it[0].nom) » ($quoi)."
} { param($a)
    $t = [JarvisFenetre]::Titre()
    $a | Add-Member -NotePropertyName _fenetre -NotePropertyValue $t -Force
    $quoi = switch ("$($a.champ)") { 'identifiant' { "l'identifiant" } 'les_deux' { "l'identifiant et le mot de passe" } default { 'le mot de passe' } }
    "saisir $quoi correspondant à « $($a.recherche) » dans la fenêtre « $t »"
}
