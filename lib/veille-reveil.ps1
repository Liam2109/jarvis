# Veille avec RÉVEIL : sur le PC principal, Jarvis démarre en VEILLE silencieuse (sourdine : ni voix, ni HUD, ni plein écran, aucun ordre exécuté) et n'écoute que deux choses,
# avec un processus léger (voix\reveil.py : Vosk petit modèle à GRAMMAIRE RESTREINTE + détecteur de claquements) :
#   1) la phrase « réveille-toi Jarvis » ;   2) un DOUBLE CLAQUEMENT de mains (deux pics brefs espacés de 0,2 à 0,8 s ; seuil réglable : « calibre les claquements »).
# Faux déclenchements évités (voir voix\reveil.py) : pic isolé, son long, rafale de bruits, et tout ce qui se passe pendant que Jarvis parle.
# Réveillé : « Je vous écoute. », écoute normale (Whisper), HUD affiché. « Jarvis, mets-toi en veille » : retour en veille (HUD fermé, écoute légère).
# config.json (tout est désactivé par défaut ; ce PC l'active dans config.local.json) : veille_reveil, bureau_veille, reveil_phrase, claquement_actif, claquement_seuil,
# claquement_ecart_min_ms, claquement_ecart_max_ms, claquement_duree_max_ms. Jamais en mode serveur ni en mode jeu.
$script:VeilleProc = $null; $script:VeilleTache = $null; $script:VeilleProchainEssai = [datetime]::MinValue
$script:VisageDemarre = $false; $script:SortieCalibrageTest = $null

function Get-ReglageVeille([string]$nom, [double]$defaut, [double]$min, [double]$max) {
    $v = $defaut
    if ($Config -and $Config.PSObject.Properties[$nom]) { $x = 0.0; if ([double]::TryParse(("$($Config.$nom)" -replace ',', '.'), [Globalization.NumberStyles]::Float, [Globalization.CultureInfo]::InvariantCulture, [ref]$x)) { $v = $x } }
    [math]::Max($min, [math]::Min($max, $v))
}
function Get-ReglagesVeille {
    @{
        reveil          = [bool]($Config -and $Config.PSObject.Properties['veille_reveil'] -and $Config.veille_reveil -eq $true)
        phrase          = -not ($Config -and $Config.PSObject.Properties['reveil_phrase'] -and $Config.reveil_phrase -eq $false)
        claquement      = -not ($Config -and $Config.PSObject.Properties['claquement_actif'] -and $Config.claquement_actif -eq $false)
        seuil           = [int](Get-ReglageVeille 'claquement_seuil' 72 30 98)
        ecart_min       = [int](Get-ReglageVeille 'claquement_ecart_min_ms' 200 100 600)
        ecart_max       = [int](Get-ReglageVeille 'claquement_ecart_max_ms' 800 300 1500)
        duree_max       = [int](Get-ReglageVeille 'claquement_duree_max_ms' 120 40 300)
    }
}
function Test-VeilleBureau { [bool]($Config -and $Config.PSObject.Properties['bureau_veille'] -and $Config.bureau_veille -eq $true -and -not (Test-ModeServeur)) }
function Get-EtatVeilleVoulu {
    # 'ecoute' : le processus de veille doit tourner (Jarvis est en sourdine/veille, réveil activé, ni serveur ni mode jeu). Sinon 'arret'.
    $r = Get-ReglagesVeille
    if ($r.reveil -and $script:Actif -eq $false -and $script:ModeJeu -ne $true -and -not (Test-ModeServeur) -and ($r.phrase -or $r.claquement)) { 'ecoute' } else { 'arret' }
}
function Get-ArgsVeille([string]$py) {
    $r = Get-ReglagesVeille; $mc = Get-MicroConfig
    "-I -u `"$py`" --seuil $($r.seuil) --claque-duree-max $($r.duree_max) --ecart-min $($r.ecart_min) --ecart-max $($r.ecart_max)" + $(if ($mc.nom) { " --micro `"$($mc.nom)`"" } else { '' }) +
        $(if ($mc.variantes.Count) { " --variantes `"$($mc.variantes -join ',')`"" } else { '' }) + $(if ($mc.modele_chemin) { " --modele-chemin `"$($mc.modele_chemin)`"" } else { '' }) +
        $(if (-not $r.claquement) { ' --sans-claquement' } else { '' }) + $(if (-not $r.phrase) { ' --sans-voix' } else { '' })
}
function Start-EcouteVeille {
    if (Test-ModeTest) { return }
    if ($script:VeilleProc -and -not $script:VeilleProc.HasExited) { return }
    $py = Join-Path $script:VoixDir 'reveil.py'
    $psi = New-Object Diagnostics.ProcessStartInfo 'python', (Get-ArgsVeille $py)
    $psi.UseShellExecute = $false; $psi.CreateNoWindow = $true; $psi.RedirectStandardOutput = $true; $psi.RedirectStandardError = $true; $psi.StandardOutputEncoding = [Text.Encoding]::UTF8
    try {
        $script:VeilleProc = [Diagnostics.Process]::Start($psi)
        try { $script:VeilleProc.PriorityClass = 'BelowNormal' } catch { }
        $script:VeilleTache = $script:VeilleProc.StandardOutput.ReadLineAsync(); $script:VeilleProc.StandardError.ReadToEndAsync() | Out-Null
        Write-Journal -Action 'Veille' -Resultat 'écoute de veille démarrée (« réveille-toi Jarvis » et double claquement ; processus léger)'
    } catch { Write-Journal -Action 'Veille' -Resultat "écoute de veille impossible : $($_.Exception.Message)"; $script:VeilleProc = $null; $script:VeilleProchainEssai = (Get-Date).AddSeconds(60) }
}
function Stop-EcouteVeille {
    try { if ($script:VeilleProc -and -not $script:VeilleProc.HasExited) { $script:VeilleProc.Kill() } } catch { }
    $script:VeilleProc = $null; $script:VeilleTache = $null
}
function Update-VeilleReveil {
    # Appelée au démarrage, par Set-Actif et par la boucle principale : démarre ou arrête l'écoute de veille selon l'état voulu (redémarrage espacé de 30 s si elle plante).
    $voulu = Get-EtatVeilleVoulu
    $tourne = [bool]($script:VeilleProc -and -not $script:VeilleProc.HasExited)
    if ($voulu -eq 'ecoute' -and -not $tourne -and (Get-Date) -ge $script:VeilleProchainEssai) { Start-EcouteVeille }
    elseif ($voulu -eq 'arret' -and $script:VeilleProc) { Stop-EcouteVeille }
}
function Invoke-PumpVeille {
    if (-not $script:VeilleProc -or -not $script:VeilleTache -or -not $script:VeilleTache.IsCompleted) { return }
    $ligne = $null; try { $ligne = $script:VeilleTache.Result } catch { }
    if ($null -eq $ligne) {
        if ($script:VeilleProc.HasExited) { Write-Journal -Action 'Veille' -Resultat "écoute de veille arrêtée (code $($script:VeilleProc.ExitCode)) : nouvel essai dans 30 s"; $script:VeilleProc = $null; $script:VeilleTache = $null; $script:VeilleProchainEssai = (Get-Date).AddSeconds(30) }
        return
    }
    if ($ligne -match '^REVEIL:(phrase|claque)$') { Invoke-Reveil $Matches[1]; return }
    $script:VeilleTache = $script:VeilleProc.StandardOutput.ReadLineAsync()
}
function Start-VisageReveil { if (-not $script:VisageDemarre -and -not (Test-ModeServeur) -and -not (Test-ModeTest)) { try { Start-Visage; $script:VisageDemarre = $true } catch { Write-Journal -Action 'Affichage Jarvis' -Resultat "affichage au réveil impossible : $($_.Exception.Message)" } } }
function Stop-VisageVeille {
    # Veille du PC principal : le HUD se ferme (rien à l'écran tant que Jarvis n'est pas réveillé).
    if (-not $script:VisageDemarre -or (Test-ModeTest)) { return }
    try { Stop-Visage } catch { }
    $script:VisageHwnd = [IntPtr]::Zero; $script:EdgePid = 0; $script:VisageDemarre = $false
}
function Start-PreChauffageBureau {
    # Démarrage en veille sur le PC principal : tout est chauffé SANS un son ni une fenêtre, pour un réveil instantané (Ollama garde le modèle selon ollama.keep_alive, Piper chargé, cache vocal rempli).
    if (Test-ModeTest) { return }
    try { Start-OllamaReveil -Force } catch { Write-Journal -Action 'Veille' -Resultat "préchauffage d'Ollama impossible : $($_.Exception.Message)" }
    try { if ((Get-VoixMoteur) -eq 'piper') { [void](Test-PiperPret) } } catch { }
    try { Start-PrechauffageTts; $script:TtsPrechauffe = $true } catch { }
}
function Invoke-Reveil([string]$source) {
    # Réveil par la phrase ou le double claquement : « Je vous écoute. », écoute normale, HUD affiché.
    Stop-EcouteVeille
    if ($script:Actif -ne $false) { return }
    Write-Journal -Action 'Réveil de Jarvis' -Resultat $(if ($source -eq 'claque') { 'double claquement de mains' } else { 'phrase « réveille-toi Jarvis »' })
    Set-Actif $true "réveil ($source)"
}
# ---------- Calibrage des claquements ----------
function ConvertFrom-CalibrageClaquements([string]$sortie) {
    # « CALIBRAGE:{json} » (voix\reveil.py --calibre) -> @{ ok; seuil; ambiant_moyen; ambiant_p99; ambiant_max } ; ok = faux si la sortie est illisible ou hors bornes.
    $m = [regex]::Match("$sortie", '(?m)^CALIBRAGE:(\{.*\})\s*$')
    if (-not $m.Success) { return @{ ok = $false } }
    try { $j = $m.Groups[1].Value | ConvertFrom-Json } catch { return @{ ok = $false } }
    $s = 0; if (-not [int]::TryParse("$($j.seuil)", [ref]$s) -or $s -lt 30 -or $s -gt 98 -or [int]$j.blocs -lt 50) { return @{ ok = $false } }
    @{ ok = $true; seuil = $s; ambiant_moyen = [double]$j.ambiant_moyen; ambiant_p99 = [int]$j.ambiant_p99; ambiant_max = [int]$j.ambiant_max }
}
function Save-ConfigLocale($valeurs) {
    # Fusionne des clés dans config.local.json (réglages de CE PC, ignoré par git) sans toucher aux autres. Jamais config.json.
    $f = Join-Path $script:JarvisRoot 'config.local.json'
    $o = [ordered]@{}
    if (Test-Path $f) { try { $c = Get-Content $f -Raw -Encoding UTF8 | ConvertFrom-Json; foreach ($p in $c.PSObject.Properties) { $o[$p.Name] = $p.Value } } catch { } }
    foreach ($k in $valeurs.Keys) { $o[$k] = $valeurs[$k] }
    [IO.File]::WriteAllText($f, ($o | ConvertTo-Json -Depth 6), [Text.UTF8Encoding]::new($false))
}
function Invoke-CalibrageClaquements {
    # Mesure le bruit ambiant (5 s de silence demandé) et règle claquement_seuil. @{ ok; texte }.
    $r = Get-ReglagesVeille; $etait = [bool]$script:VeilleProc
    Stop-EcouteVeille
    try {
        if (Test-ModeTest) { $sortie = "$script:SortieCalibrageTest" }
        else {
            $mc = Get-MicroConfig; $a = @('-I', '-u', (Join-Path $script:VoixDir 'reveil.py'), '--calibre', '5'); if ($mc.nom) { $a += @('--micro', $mc.nom) }
            $sortie = (& python @a 2>$null | Out-String)
        }
        $c = ConvertFrom-CalibrageClaquements $sortie
        if (-not $c.ok) { return @{ ok = $false; texte = "Je n'ai pas pu mesurer le bruit ambiant, monsieur (micro occupé ou absent)." } }
        Save-ConfigLocale @{ claquement_seuil = $c.seuil }
        if ($Config.PSObject.Properties['claquement_seuil']) { $Config.claquement_seuil = $c.seuil } else { $Config | Add-Member -NotePropertyName claquement_seuil -NotePropertyValue $c.seuil }
        Write-Journal -Action 'Calibrage des claquements' -Resultat "bruit ambiant : niveau moyen $($c.ambiant_moyen), pic $($c.ambiant_p99) sur 100 ; seuil réglé à $($c.seuil) (config.local.json)"
        @{ ok = $true; texte = "Bruit ambiant mesuré : niveau $([int]$c.ambiant_moyen) sur 100, pics à $($c.ambiant_p99). J'ai réglé le seuil de claquement à $($c.seuil) sur 100, monsieur. Mettez-moi en veille et faites un double claquement pour essayer." }
    } finally { Update-VeilleReveil }
}
if (Get-Command Add-Action -ErrorAction SilentlyContinue) {
    Add-Action 'calibre_claquements' 1 'calibrer les claquements' 'calibre_claquements() : mesure le bruit ambiant pendant 5 secondes (restez silencieux) et règle le seuil du double claquement (config.local.json)' {
        param($a)
        if (-not (Test-ModeTest)) { Parler 'Restez silencieux cinq secondes, monsieur, je mesure le bruit ambiant.' }
        $r = Invoke-CalibrageClaquements; Rep $r.ok $r.texte
    } { param($a) 'calibrer les claquements' }
}
if ($P -and $FIN -and (Get-Command New-PlanRapide -ErrorAction SilentlyContinue) -and $script:ReglesRapides) {
    $script:ReglesRapides = @(
        @{ nom = 'calibre_claquements'; re = "$P(?:calibre|calibrer|regle|mesure)(?: moi)? (?:les |le |mes )?(?:claquements?(?: de mains)?|bruit ambiant)$FIN"
           build = { param($m, $o, $n) New-PlanRapide '' @(Act 'calibre_claquements') { param($r) "$($r[0].texte)" } 'calibre_claquements' } },
        @{ nom = 'mise_en_veille'; re = "$P(?:(?:mets|mettre) toi en veille|(?:passe|va|reste)(?: toi)? en veille|veille jarvis)(?: jarvis)?$FIN"
           build = { param($m, $o, $n) New-PlanRapide 'Très bien monsieur, je me mets en veille.' @(Act 'sourdine') $null 'mise_en_veille' } }
    ) + @($script:ReglesRapides)
}
