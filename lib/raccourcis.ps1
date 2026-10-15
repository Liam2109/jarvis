# Raccourcis clavier globaux + état actif / sourdine (mémorisé d'un démarrage à l'autre).
# config.json "raccourcis" : { activer, desactiver, basculer, tableau, jeu, musique_moins, musique_plus, musique_couper, touche_seule }
#   Format : "Alt+Add"  (modificateurs : Alt, Ctrl, Shift, Win ; touche : nom .NET System.Windows.Forms.Keys)
#   Alias : ScrollLock (Verr. défil.), Plus / PavePlus (+ du pavé numérique = Add), Moins / PaveMoins (− du pavé numérique = Subtract)
# Interdits : Ctrl + « + » / « − » (zoom du navigateur), toute touche seule sauf Verr. défil. / Pause / F13-F24 (et + et − si "touche_seule").
Add-Type -AssemblyName System.Windows.Forms
Add-Type -ReferencedAssemblies System.Windows.Forms -TypeDefinition @'
using System; using System.Collections.Concurrent; using System.Runtime.InteropServices; using System.Windows.Forms;
public class JarvisCles : NativeWindow {
  [DllImport("user32.dll", SetLastError = true)] static extern bool RegisterHotKey(IntPtr h, int id, uint mod, uint vk);
  [DllImport("user32.dll")] static extern bool UnregisterHotKey(IntPtr h, int id);
  public ConcurrentQueue<int> File = new ConcurrentQueue<int>();
  System.Collections.Generic.List<int> ids = new System.Collections.Generic.List<int>();
  public JarvisCles() { var cp = new CreateParams(); cp.Parent = (IntPtr)(-3); CreateHandle(cp); }   // fenêtre "messages seulement" : invisible
  public int Enregistrer(int id, uint mod, uint vk) {
    if (RegisterHotKey(Handle, id, mod | 0x4000, vk)) { ids.Add(id); return 0; }                       // 0x4000 = MOD_NOREPEAT (pas de répétition en maintenant la touche)
    return Marshal.GetLastWin32Error();
  }
  protected override void WndProc(ref Message m) { if (m.Msg == 0x0312) File.Enqueue(m.WParam.ToInt32()); base.WndProc(ref m); }
  public void Liberer() { foreach (int i in ids) UnregisterHotKey(Handle, i); ids.Clear(); if (Handle != IntPtr.Zero) DestroyHandle(); }
}
'@

$script:Cles = $null
$script:ClesDefs = @{}                     # id -> @{ action; libelle }
$script:EtatFichier2 = Join-Path $script:JarvisRoot 'memoire\etat-jarvis.json'
$script:SourdineFlag = Join-Path $script:JarvisRoot 'memoire\sourdine.flag'
$script:EntreesEnAttente = New-Object System.Collections.Generic.List[object]
$script:RaccourcisRapport = @()

$script:ClesParDefaut = @{ activer = 'Alt+Add'; desactiver = 'Alt+Subtract'; basculer = 'ScrollLock'; tableau = 'Ctrl+Alt+J'; jeu = 'Ctrl+Alt+G'; musique_moins = 'Ctrl+Alt+Down'; musique_plus = 'Ctrl+Alt+Up'; musique_couper = 'Ctrl+Alt+M' }
$script:AliasCles = @{ scrolllock = 'Scroll'; verrdefil = 'Scroll'; 'verr.defil' = 'Scroll'; plus = 'Add'; paveplus = 'Add'; numpadplus = 'Add'; 'numpad+' = 'Add'; 'pavé+' = 'Add'
    moins = 'Subtract'; pavemoins = 'Subtract'; numpadminus = 'Subtract'; numpadmoins = 'Subtract'; 'numpad-' = 'Subtract'; 'pavé-' = 'Subtract' }

function Convert-Raccourci([string]$texte, [bool]$toucheSeule = $false) {
    # Retourne @{ ok; mods; vk; libelle; erreur }
    $r = @{ ok = $false; mods = 0; vk = 0; libelle = $texte; erreur = '' }
    if (-not $texte -or -not $texte.Trim()) { $r.erreur = 'raccourci vide'; return $r }
    $t = $texte.Trim(); $nomTouche = $null; $hasCtrl = $false
    if ($t.EndsWith('+')) { $nomTouche = '+'; $t = $t.Substring(0, $t.Length - 1).TrimEnd('+') }     # "Alt++" : la touche est le caractère « + »
    $parts = @($t -split '\+' | Where-Object { $_.Trim() -ne '' })
    foreach ($p in $parts) {
        switch ($p.Trim().ToLower()) {
            'alt'   { $r.mods = $r.mods -bor 1 }
            { $_ -in 'ctrl', 'control', 'ctl' } { $r.mods = $r.mods -bor 2; $hasCtrl = $true }
            'shift' { $r.mods = $r.mods -bor 4 }
            { $_ -in 'win', 'windows' } { $r.mods = $r.mods -bor 8 }
            default { if ($nomTouche) { $r.erreur = "plusieurs touches dans « $texte »"; return $r }; $nomTouche = $p.Trim() }
        }
    }
    if (-not $nomTouche) { $r.erreur = "aucune touche dans « $texte »"; return $r }
    if ($nomTouche -eq '+') { $nomTouche = 'Add' } elseif ($nomTouche -eq '-' -or $nomTouche -eq '−') { $nomTouche = 'Subtract' }
    $cle = if ($script:AliasCles.ContainsKey($nomTouche.ToLower())) { $script:AliasCles[$nomTouche.ToLower()] } else { $nomTouche }
    # Nom de touche exact (insensible à la casse) : on refuse les nombres et les listes « A,B » que Enum.Parse accepterait
    $nomExact = [Enum]::GetNames([Windows.Forms.Keys]) | Where-Object { $_ -ieq $cle } | Select-Object -First 1
    if (-not $nomExact -or $nomExact -eq 'None') { $r.erreur = "touche inconnue « $nomTouche »"; return $r }
    $k = [Enum]::Parse([Windows.Forms.Keys], $nomExact)
    # Zoom du navigateur : Ctrl + « + » / « − » interdits
    if ($hasCtrl -and $k -in [Windows.Forms.Keys]::Add, [Windows.Forms.Keys]::Subtract, [Windows.Forms.Keys]::Oemplus, [Windows.Forms.Keys]::OemMinus) {
        $r.erreur = "Ctrl + « + » / « − » est réservé au zoom du navigateur : refusé"; return $r
    }
    if ($r.mods -eq 0) {
        $autorisee = ($k -eq [Windows.Forms.Keys]::Scroll) -or ($k -eq [Windows.Forms.Keys]::Pause) -or ($k -ge [Windows.Forms.Keys]::F13 -and $k -le [Windows.Forms.Keys]::F24)
        if (-not $autorisee) { $r.erreur = "touche seule interdite (« $texte ») : ajoutez un modificateur (Alt, Ctrl, Shift, Win)"; return $r }
    }
    $r.ok = $true; $r.vk = [int]$k; $r.libelle = $texte.Trim()
    $r
}

function Get-EtatJarvis {
    if (Test-Path $script:EtatFichier2) { try { return (Get-Content $script:EtatFichier2 -Raw -Encoding UTF8 | ConvertFrom-Json) } catch {} }
    [pscustomobject]@{ actif = $true }
}
function Save-EtatJarvis([bool]$actif) { [pscustomobject]@{ actif = $actif; modifie = (Get-Date).ToString('o') } | ConvertTo-Json | Set-Content $script:EtatFichier2 -Encoding UTF8 }

function Set-Actif([bool]$actif, [string]$source = '') {
    # SOURDINE TOTALE (Alt + − ) : plus de voix, de musique, de bip, de popup, d'alerte dite, plus d'écoute (le micro est LIBÉRÉ : le processus
    # d'écoute est arrêté, plus aucune détection de « Jarvis »), aucun ordre exécuté. Les alertes graves restent au journal et au panneau.
    # Activation (Alt + +) : micro rouvert, salutation variée (phrases_reveil).
    if ($script:Actif -eq $actif) { if ($actif) { Invoke-Son 'actif' }; return }
    $script:Actif = $actif
    Save-EtatJarvis $actif
    if ($actif) { Remove-Item $script:SourdineFlag -ErrorAction SilentlyContinue } else { Set-Content $script:SourdineFlag '1' -Encoding ASCII }
    if (Get-Command Set-SonsSourdine -ErrorAction SilentlyContinue) { Set-SonsSourdine (-not $actif) }   # sourdine = musique coupée ; activation = l'ambiance (si activée) reprend
    if (-not $actif) {
        if ($script:SonJoueur) { try { $script:SonJoueur.Stop() } catch {} }            # aucun son en cours
        Stop-Ecoute                                                                  # micro libéré (le processus de reconnaissance s'arrête : VRAM libérée)
        if (Get-Command Release-GpuModeles -ErrorAction SilentlyContinue) { Release-GpuModeles }      # Ollama : modèle déchargé du GPU
        $script:Ecoute = $null; $script:EcouteTache = $null
    } else {
        Start-Ecoute                                                                 # micro rouvert
        if (-not (Test-ModeTest) -and (Get-Command Start-OllamaReveil -ErrorAction SilentlyContinue)) { Start-OllamaReveil }
        if (-not (Test-ModeTest) -and (Get-Command Test-PiperPret -ErrorAction SilentlyContinue)) { [void](Test-PiperPret -Repli) }      # voix locale Piper (homme) chargée en secours : jamais la voix féminine de Windows si la voix en ligne tarde      # le modèle du routeur est préchargé dès le réveil (keep_alive 30 min) : pas de premier appel lent
    }
    Set-VisageEtat 'ecoute'                    # devient « sourdine » automatiquement si $script:Actif est faux
    Write-Journal -Action $(if ($actif) { 'Jarvis ACTIVÉ' } else { 'Jarvis en SOURDINE TOTALE (muet, sourd, micro libéré, aucun ordre exécuté)' }) -Resultat "ok ($source)"
    if ($actif) {
        $n = $script:EntreesEnAttente.Count; $script:EntreesEnAttente.Clear()
        if ($n) { Write-Journal -Action 'Alertes de la sourdine' -Resultat "$n alerte(s) gardée(s) au journal et au panneau, non dites" }
        Invoke-Son 'actif'
        if (-not $script:BriefingEnAttente) { Invoke-AvecContexteVoix 'reponse' { Parler (Get-PhraseReveil) } }
    }
}
function New-CleGlobale { New-Object JarvisCles }      # (les tests la remplacent par une fausse : aucun raccourci système réel)

function Initialize-Raccourcis {
    # Lit config.json, enregistre les raccourcis globaux, retourne la liste des problèmes (vide si tout va bien).
    $script:RaccourcisRapport = @(); $problemes = @()
    $cfg = $Config.raccourcis
    $get = { param($nom) if ($cfg -and $cfg.PSObject.Properties[$nom] -and "$($cfg.$nom)".Trim()) { "$($cfg.$nom)" } else { $script:ClesParDefaut[$nom] } }
    $toucheSeule = [bool]($cfg -and $cfg.touche_seule)
    $script:Cles = New-CleGlobale
    $defs = @(@{ id = 1; action = 'activer'; nom = 'activer' }, @{ id = 2; action = 'desactiver'; nom = 'desactiver' }, @{ id = 3; action = 'basculer'; nom = 'basculer' }, @{ id = 4; action = 'tableau'; nom = 'tableau' }, @{ id = 7; action = 'jeu'; nom = 'jeu' },
        @{ id = 8; action = 'musique_moins'; nom = 'musique_moins' }, @{ id = 9; action = 'musique_plus'; nom = 'musique_plus' }, @{ id = 10; action = 'musique_couper'; nom = 'musique_couper' })
    $vus = @{}
    foreach ($d in $defs) {
        $txt = & $get $d.nom; $p = Convert-Raccourci $txt
        if (-not $p.ok) {
            $problemes += "raccourci « $($d.nom) » : $($p.erreur) (valeur par défaut utilisée : $($script:ClesParDefaut[$d.nom]))"
            $p = Convert-Raccourci $script:ClesParDefaut[$d.nom]
        }
        $cleU = "$($p.mods)-$($p.vk)"
        if ($vus.ContainsKey($cleU)) { $problemes += "raccourci « $($d.nom) » ($($p.libelle)) déjà utilisé pour « $($vus[$cleU]) » : ignoré"; continue }
        $vus[$cleU] = $d.nom
        $err = $script:Cles.Enregistrer($d.id, [uint32]$p.mods, [uint32]$p.vk)
        if ($err -eq 0) { $script:ClesDefs[$d.id] = @{ action = $d.action; libelle = $p.libelle }; $script:RaccourcisRapport += "$($d.action) = $($p.libelle)" }
        else { $problemes += "raccourci « $($d.nom) » ($($p.libelle)) non enregistré : $(if ($err -eq 1409) { 'déjà utilisé par un autre programme' } else { "erreur Windows $err" })" }
    }
    if ($toucheSeule) {
        foreach ($d in @(@{ id = 5; action = 'activer'; vk = [int][Windows.Forms.Keys]::Add; l = '+ (pavé numérique)' }, @{ id = 6; action = 'desactiver'; vk = [int][Windows.Forms.Keys]::Subtract; l = '− (pavé numérique)' })) {
            $err = $script:Cles.Enregistrer($d.id, 0, [uint32]$d.vk)
            if ($err -eq 0) { $script:ClesDefs[$d.id] = @{ action = $d.action; libelle = $d.l }; $script:RaccourcisRapport += "$($d.action) = $($d.l) seul" }
            else { $problemes += "touche seule $($d.l) non enregistrée (erreur Windows $err)" }
        }
        $script:AvertissementToucheSeule = $true
        Write-Journal -Action 'AVERTISSEMENT raccourcis' -Resultat "touche_seule activée : les touches + et − du pavé numérique sont réservées à Jarvis dans tous les programmes"
    }
    Write-Journal -Action 'Raccourcis clavier globaux' -Resultat ($(if ($script:RaccourcisRapport) { 'actifs : ' + ($script:RaccourcisRapport -join ' ; ') } else { 'aucun actif' }) + $(if ($problemes) { ' | problèmes : ' + ($problemes -join ' ; ') }))
    # État mémorisé du dernier arrêt
    $e = Get-EtatJarvis
    $choix = "$($Config.etat_au_demarrage)".Trim().ToLower()        # "sourdine" | "actif" | (vide : état mémorisé au dernier arrêt)
    $demarreMuet = switch ($choix) { 'sourdine' { $true } 'actif' { $false } default { $e.actif -eq $false } }
    if ($demarreMuet) { $script:Actif = $false; Set-Content $script:SourdineFlag '1' -Encoding ASCII; Set-VisageEtat 'ecoute'; Write-Journal -Action 'Démarrage en SOURDINE' -Resultat $(if ($choix -eq 'sourdine') { 'config.json : etat_au_demarrage = sourdine (rien ne parle, rien n''écoute, aucun son jusqu''à Alt + +)' } else { 'état mémorisé au dernier arrêt' }) }
    else { $script:Actif = $true; Remove-Item $script:SourdineFlag -ErrorAction SilentlyContinue }
    , $problemes
}

function Stop-Raccourcis { if ($script:Cles) { try { $script:Cles.Liberer() } catch {}; $script:Cles = $null } }

function Invoke-Raccourci([int]$id) {
    $d = $script:ClesDefs[$id]; if (-not $d) { return }
    switch ($d.action) {
        'activer'    { Set-Actif $true  "raccourci $($d.libelle)" }
        'desactiver' { Set-Actif $false "raccourci $($d.libelle)" }
        'basculer'   { Set-Actif (-not $script:Actif) "raccourci $($d.libelle)" }
        'jeu'        { if (Get-Command Switch-ModeJeu -ErrorAction SilentlyContinue) { Switch-ModeJeu "raccourci $($d.libelle)" } }
        'musique_moins'  { if (Get-Command Invoke-CommandeMusique -ErrorAction SilentlyContinue) { [void](Invoke-CommandeMusique 'baisser') } }      # sans voix : le volume est mémorisé
        'musique_plus'   { if (Get-Command Invoke-CommandeMusique -ErrorAction SilentlyContinue) { [void](Invoke-CommandeMusique 'monter') } }
        'musique_couper' { if (Get-Command Invoke-CommandeMusique -ErrorAction SilentlyContinue) { [void](Invoke-CommandeMusique 'basculer') } }
        'tableau'    { Switch-Visage; Write-Journal -Action 'Tableau de bord affiché/masqué' -Resultat "raccourci $($d.libelle) : $(if ($script:VisageVisible) { 'affiché' } else { 'masqué' })" }
    }
}

function Invoke-PumpRaccourcis {
    if (-not $script:Cles) { return }
    [Windows.Forms.Application]::DoEvents()
    $id = 0; $n = 0
    while ($n++ -lt 8 -and $script:Cles.File.TryDequeue([ref]$id)) { try { Invoke-Raccourci $id } catch { Write-Journal -Action 'Raccourci' -Resultat "erreur : $($_.Exception.Message)" } }
}
