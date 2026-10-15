# Sons : petits sons de changement d'état, jingle de démarrage généré en code, musique de démarrage / d'ambiance avec ducking.
# Aucune ressource protégée : le jingle est synthétisé ici (arpège ascendant do-mi-sol-do puis « ding » de cloche, ≈ 2 s). Vous pouvez
# déposer votre propre musique dans sounds\demarrage.mp3 (ou .wav) et sounds\ambiance.mp3.
# Réglages config.json : volume_musique (0-1), volume_pendant_voix (part du volume normal conservée pendant que Jarvis parle, 0.2 = 20 %),
#                        duree_fondu (secondes pour remonter doucement), musique_ambiance (false par défaut).
Add-Type -AssemblyName PresentationCore
Add-Type -TypeDefinition @'
using System; using System.IO;
public class JarvisJingle {
  const int SR = 44100;
  public static byte[] Generer() {
    double duree = 2.0; int n = (int)(SR * duree); double[] s = new double[n];
    double[] arpege = { 523.25, 659.25, 783.99, 1046.50 };               // do5 mi5 sol5 do6 : notes qui montent
    for (int k = 0; k < arpege.Length; k++) {
      double t0 = 0.05 + k * 0.17; int i0 = (int)(t0 * SR); int len = (int)(0.34 * SR);
      for (int i = 0; i < len && i0 + i < n; i++) {
        double t = (double)i / SR, env = Math.Min(1.0, t / 0.012) * Math.Exp(-t * 7.0);
        s[i0 + i] += 0.30 * env * (Math.Sin(2 * Math.PI * arpege[k] * t) + 0.25 * Math.Sin(2 * Math.PI * arpege[k] * 2 * t));
      }
    }
    double[] pad = { 130.81, 196.00, 261.63 };                           // nappe grave douce (do sol do)
    for (int i = 0; i < n; i++) {
      double t = (double)i / SR, env = Math.Min(1.0, t / 0.4) * Math.Min(1.0, (duree - t) / 0.5);
      foreach (double f in pad) s[i] += 0.07 * env * Math.Sin(2 * Math.PI * f * t);
    }
    double[] part = { 1.0, 2.0, 2.76, 5.40 }, amp = { 1.0, 0.45, 0.30, 0.10 };   // « ding » : partiels de cloche
    int d0 = (int)(0.78 * SR);
    for (int i = 0; d0 + i < n; i++) {
      double t = (double)i / SR, env = Math.Min(1.0, t / 0.004) * Math.Exp(-t * 3.2), v = 0;
      for (int p = 0; p < part.Length; p++) v += amp[p] * Math.Sin(2 * Math.PI * 1318.51 * part[p] * t) * Math.Exp(-t * p * 1.5);
      s[d0 + i] += 0.34 * env * v;
    }
    int fin = (int)(0.18 * SR);
    for (int i = 0; i < fin; i++) s[n - 1 - i] *= (double)i / fin;       // fondu de sortie : finit dans le silence
    double max = 0; for (int i = 0; i < n; i++) max = Math.Max(max, Math.Abs(s[i]));
    double g = max > 0.9 ? 0.9 / max : 1.0;                              // jamais de saturation
    var ms = new MemoryStream(); var bw = new BinaryWriter(ms);
    bw.Write(new char[] { 'R', 'I', 'F', 'F' }); bw.Write(36 + n * 2); bw.Write(new char[] { 'W', 'A', 'V', 'E', 'f', 'm', 't', ' ' });
    bw.Write(16); bw.Write((short)1); bw.Write((short)1); bw.Write(SR); bw.Write(SR * 2); bw.Write((short)2); bw.Write((short)16);
    bw.Write(new char[] { 'd', 'a', 't', 'a' }); bw.Write(n * 2);
    for (int i = 0; i < n; i++) bw.Write((short)(32767 * g * s[i]));
    bw.Flush(); return ms.ToArray();
  }
}
'@

$script:DernierSon = $null
$script:SonJoueur = $null
$script:Musique = $null; $script:Ambiance = $null
$script:SonsParole = $false
$script:VolActuel = $null
$script:SonsDernierTick = $null
$script:SonsDossier = Join-Path $script:JarvisRoot 'sounds'

function Get-ReglageSon([string]$nom, [double]$defaut) {
    if ($Config -and $Config.PSObject.Properties[$nom] -and $null -ne $Config.$nom -and "$($Config.$nom)" -ne '') { try { return [double]("$($Config.$nom)" -replace ',', '.') } catch {} }
    $defaut
}
# Volume choisi à la voix / au clavier : mémorisé dans memoire\musique.json (jamais dans config.json) ; config.json ne donne que le volume de départ.
$script:MusiqueEtat = $null
function Get-EtatMusique {
    if ($null -eq $script:MusiqueEtat) {
        $o = Read-JsonMemoire 'musique.json'
        $v = $null; if ($o -and $null -ne $o.volume -and "$($o.volume)" -match '^[0-9.,]+$') { $v = [math]::Max(0.0, [math]::Min(1.0, [double]::Parse("$($o.volume)".Replace(',', '.'), [Globalization.CultureInfo]::InvariantCulture))) }
        $script:MusiqueEtat = @{ volume = $v; coupee = [bool]($o -and $o.coupee) }
    }
    $script:MusiqueEtat
}
function Save-EtatMusique { $e = Get-EtatMusique; Save-JsonMemoire 'musique.json' ([ordered]@{ volume = $e.volume; coupee = $e.coupee; modifie = (Get-Date).ToString('o') }) }
function Get-VolumeBase { $e = Get-EtatMusique; if ($null -ne $e.volume) { return [double]$e.volume }; [math]::Max(0.0, [math]::Min(1.0, (Get-ReglageSon 'volume_musique' 0.2))) }
function Test-MusiqueCoupee { [bool](Get-EtatMusique).coupee }
function Set-VolumeMusique([double]$v, [switch]$Explicite) {
    # Explicite = « musique à N pour cent » (0 à 100 permis). Sinon plancher de 5 % : « baisse » ne rend jamais la musique inaudible.
    $e = Get-EtatMusique; $e.volume = [math]::Round([math]::Max($(if ($Explicite) { 0.0 } else { 0.05 }), [math]::Min(1.0, $v)), 2); Save-EtatMusique
    Write-Journal -Action 'Volume de la musique' -Resultat "$([int]($e.volume * 100)) % (mémorisé dans memoire\musique.json)"
    $e.volume
}
function Step-VolumeMusique([double]$delta) {
    # +/- 10 % du volume maximal. Monter dé-coupe la musique.
    $v = Set-VolumeMusique ((Get-VolumeBase) + $delta)
    if ($delta -gt 0 -and (Test-MusiqueCoupee)) { [void](Set-MusiqueCoupee $false) }
    $v
}
function Set-MusiqueCoupee([bool]$coupee) {
    $e = Get-EtatMusique; $e.coupee = $coupee; Save-EtatMusique
    Write-Journal -Action 'Musique' -Resultat $(if ($coupee) { 'coupée (volume mémorisé conservé)' } else { 'remise' })
    if (-not $coupee -and (Get-Command Start-Ambiance -ErrorAction SilentlyContinue)) { Start-Ambiance }      # remonte doucement ; relance l'ambiance si elle n'avait pas démarré
    $coupee
}
function Invoke-CommandeMusique([string]$cmd, $valeur = $null) {
    # cmd : baisser | monter | couper | remettre | tres_bas | basculer | niveau (valeur = 0 à 100 %). Retourne la phrase à dire.
    switch ($cmd) {
        'niveau'   {
            $n = -1; if ($null -eq $valeur -or -not [int]::TryParse("$valeur", [ref]$n) -or $n -lt 0 -or $n -gt 100) { return 'La musique se règle entre 0 et 100 pour cent, monsieur.' }
            $v = Set-VolumeMusique ($n / 100.0) -Explicite
            if ($n -gt 0 -and (Test-MusiqueCoupee)) { [void](Set-MusiqueCoupee $false) }
        }
        'baisser'  { $v = Step-VolumeMusique -0.1 }
        'monter'   { $v = Step-VolumeMusique 0.1 }
        'tres_bas' { $v = Set-VolumeMusique 0.1 }
        'couper'   { [void](Set-MusiqueCoupee $true); return 'Musique coupée, monsieur.' }
        'remettre' { [void](Set-MusiqueCoupee $false); return "Musique remise, monsieur, à $([int]((Get-VolumeBase) * 100)) %." }
        'basculer' { $c = -not (Test-MusiqueCoupee); [void](Set-MusiqueCoupee $c); return $(if ($c) { 'Musique coupée, monsieur.' } else { 'Musique remise, monsieur.' }) }
        default    { return 'Commande de musique inconnue, monsieur.' }
    }
    "Musique à $([int]($v * 100)) %, monsieur."
}
Add-Action 'musique' 1 'régler la musique' 'musique(commande, valeur?) : commande = baisser | monter | couper | remettre | tres_bas | niveau (alors valeur = 0 à 100) — règle la musique de fond de Jarvis (volume mémorisé)' {
    param($a)
    $t = Invoke-CommandeMusique "$($a.commande)" $a.valeur      # (texte d'information, utilisé par les tests ; la réponse parlée passe par le ton majordome)
    if ($t -match '^La musique se règle') { return (Rep $false (Get-Politesse 'refus' @{ raison = 'la musique se règle entre 0 et 100 pour cent' })) }
    if ($t -match '^Commande de musique inconnue') { return (Rep $false (Get-Politesse 'incompris')) }
    Rep $true (Get-Politesse 'silencieux')
} { param($a) "musique : $($a.commande)" }
function Get-FractionVoix { [math]::Max(0.0, [math]::Min(1.0, (Get-ReglageSon 'volume_pendant_voix' 0.2))) }
function Get-DureeFondu { [math]::Max(0.05, (Get-ReglageSon 'duree_fondu' 1.2)) }

function Get-VolumeSuivant([double]$actuel, [double]$cible, [double]$dt, [double]$base, [double]$bas, [double]$dureeMontee, [double]$dureeDescente = 0.3) {
    # Fonction pure (testée) : la musique baisse vite quand Jarvis parle et remonte DOUCEMENT (en dureeMontee) quand il a fini.
    $ampl = [math]::Max(0.0001, $base - $bas)
    if ($cible -gt $actuel) { return [math]::Min($cible, $actuel + ($ampl / $dureeMontee) * $dt) }
    [math]::Max($cible, $actuel - ($ampl / $dureeDescente) * $dt)
}

function Set-SonsParole([bool]$parle) { $script:SonsParole = $parle }

function Update-Sons {
    # Appelée en permanence par Invoke-Pump : ducking, fin de la musique de démarrage, boucle de l'ambiance.
    if (-not $script:Musique -and -not $script:Ambiance) { $script:SonsDernierTick = $null; return }
    $now = Get-Date
    $dt = if ($script:SonsDernierTick) { [math]::Min(0.5, ($now - $script:SonsDernierTick).TotalSeconds) } else { 0.0 }
    $script:SonsDernierTick = $now
    $base = Get-VolumeBase; $bas = $base * (Get-FractionVoix)      # volume mémorisé (voix / raccourcis), baissé pendant que Jarvis parle
    $coupee = Test-MusiqueCoupee
    if ($null -eq $script:VolActuel) { $script:VolActuel = $(if ($coupee) { 0.0 } else { $base }) }
    $cible = if ($coupee) { 0.0 } elseif ($script:SonsParole) { $bas } else { $base }       # coupée : silence, la fin de la parole ne la rallume pas
    $script:VolActuel = Get-VolumeSuivant $script:VolActuel $cible $dt $base $bas (Get-DureeFondu)
    foreach ($nom in 'Musique', 'Ambiance') {
        $p = (Get-Variable -Name $nom -Scope Script -ValueOnly)
        if (-not $p) { continue }
        try {
            $p.Volume = $script:VolActuel
            if ($p.NaturalDuration.HasTimeSpan -and $p.Position -ge ($p.NaturalDuration.TimeSpan - [TimeSpan]::FromMilliseconds(80))) {
                if ($nom -eq 'Ambiance') { $p.Position = [TimeSpan]::Zero; $p.Play() }      # boucle
                else { $p.Close(); Set-Variable -Name $nom -Scope Script -Value $null; Write-Journal -Action 'Musique de démarrage' -Resultat 'terminée' }
            }
        } catch {}
    }
}

function New-Lecteur([string]$fichier, [double]$volume) {
    if (Test-ModeTest) {      # tests : faux lecteur silencieux (mêmes propriétés : Volume, Position, NaturalDuration)
        $o = [pscustomobject]@{ Volume = $volume; Debut = Get-Date; Fichier = $fichier; NaturalDuration = [pscustomobject]@{ HasTimeSpan = $true; TimeSpan = [TimeSpan]::FromSeconds(8) } }
        $o | Add-Member ScriptProperty Position { [TimeSpan]::FromSeconds(((Get-Date) - $this.Debut).TotalSeconds) } { param($v) $this.Debut = (Get-Date) - $v }
        foreach ($m in 'Play', 'Stop', 'Close') { $o | Add-Member ScriptMethod $m { } }
        return $o
    }
    $p = New-Object System.Windows.Media.MediaPlayer
    $p.Open([uri]$fichier); $p.Volume = $volume; $p.Play(); $p
}

function Find-FichierSon([string]$base) {
    # sounds\<base>.mp3 / .wav / .m4a ; tolère aussi « <base>.mp3.mp3 » (extension doublée quand Windows cache les extensions). $null si absent.
    foreach ($ext in 'mp3', 'wav', 'm4a') {
        foreach ($nom in "$base.$ext", "$base.$ext.$ext") { $f = Join-Path $script:SonsDossier $nom; if (Test-Path -LiteralPath $f -PathType Leaf) { return $f } }
    }
    $null
}

function Get-FichierDemarrage {
    # sounds\demarrage.mp3 / .wav si présent ; sinon le jingle original généré en code.
    if (-not (Test-Path $script:SonsDossier)) { New-Item -ItemType Directory $script:SonsDossier | Out-Null }
    $f = Find-FichierSon 'demarrage'; if ($f) { return @{ fichier = $f; genere = $false } }
    $f = Join-Path $script:SonsDossier 'jingle-genere.wav'
    [IO.File]::WriteAllBytes($f, [JarvisJingle]::Generer())
    @{ fichier = $f; genere = $true }
}

function Start-MusiqueDemarrage([string]$fichier = '') {
    if (Test-ModeServeur) { return }
    # La musique commence À VOLUME NORMAL ; la parole viendra par-dessus (le ducking baisse la musique sans jamais la couper).
    if ($script:ModeJeu -eq $true -or $script:Actif -eq $false) { return }       # mode jeu ou sourdine : aucune musique
    try {
        $src = if ($fichier) { @{ fichier = $fichier; genere = $false } } else { Get-FichierDemarrage }
        $script:VolActuel = $(if (Test-MusiqueCoupee) { 0.0 } else { Get-VolumeBase }); $script:SonsDernierTick = Get-Date
        $script:Musique = New-Lecteur $src.fichier $script:VolActuel
        Write-Journal -Action 'Musique de démarrage' -Resultat ("lancée : " + (Split-Path $src.fichier -Leaf) + $(if ($src.genere) { ' (jingle original généré en code)' }) + " à $([int]($script:VolActuel * 100)) %")
    } catch { Write-Journal -Action 'Musique de démarrage' -Resultat "échec : $($_.Exception.Message)" }
}

function Start-Ambiance {
    if (Test-ModeServeur) { return }
    if (-not [bool]$Config.musique_ambiance -or $script:ModeJeu -eq $true -or $script:Actif -eq $false) { return }
    $f = Find-FichierSon 'ambiance'
    if (-not $f) { Write-Journal -Action 'Musique d''ambiance' -Resultat 'activée dans config.json mais sounds\ambiance.mp3 est absent'; return }
    if ($script:Ambiance -or $script:Actif -eq $false) { return }
    if ($null -eq $script:VolActuel) { $script:VolActuel = $(if (Test-MusiqueCoupee) { 0.0 } else { Get-VolumeBase }) }
    try { $script:Ambiance = New-Lecteur $f $script:VolActuel; Write-Journal -Action 'Musique d''ambiance' -Resultat 'lancée en boucle' } catch { Write-Journal -Action 'Musique d''ambiance' -Resultat "échec : $($_.Exception.Message)" }
}

function Stop-Musiques {
    foreach ($nom in 'Musique', 'Ambiance') {
        $p = (Get-Variable -Name $nom -Scope Script -ValueOnly)
        if ($p) { try { $p.Stop(); $p.Close() } catch {}; Set-Variable -Name $nom -Scope Script -Value $null }
    }
}

function Set-SonsSourdine([bool]$sourdine) {
    # Sourdine : toute musique est coupée. À la réactivation, l'ambiance (si activée) reprend ; la musique de démarrage ne rejoue pas.
    if ($sourdine) { Stop-Musiques; $script:SonsParole = $false } else { Start-Ambiance }
}

function New-OctetsWav([double[]]$freqs, [int]$msParNote = 90, [double]$volume = 0.25) {
    # WAV PCM 16 bits mono 22 050 Hz : suite de notes sinusoïdales (petits sons de changement d'état).
    $sr = 22050; $ms = New-Object IO.MemoryStream; $bw = New-Object IO.BinaryWriter $ms
    $n = [int]($sr * $msParNote / 1000); $total = $n * $freqs.Count
    $bw.Write([Text.Encoding]::ASCII.GetBytes('RIFF')); $bw.Write([int](36 + $total * 2)); $bw.Write([Text.Encoding]::ASCII.GetBytes('WAVEfmt '))
    $bw.Write([int]16); $bw.Write([int16]1); $bw.Write([int16]1); $bw.Write([int]$sr); $bw.Write([int]($sr * 2)); $bw.Write([int16]2); $bw.Write([int16]16)
    $bw.Write([Text.Encoding]::ASCII.GetBytes('data')); $bw.Write([int]($total * 2))
    foreach ($f in $freqs) {
        for ($i = 0; $i -lt $n; $i++) {
            $env = [math]::Min(1.0, [math]::Min($i / 220.0, ($n - $i) / 440.0))
            $bw.Write([int16](32767 * $volume * $env * [math]::Sin(2 * [math]::PI * $f * $i / $sr)))
        }
    }
    $bw.Flush(); $ms.ToArray()
}

function Invoke-Son([string]$nom) {
    if (Test-ModeServeur) { return }
    # nom : actif (deux notes montantes) | sourdine (deux notes descendantes)
    if ($script:ModeJeu -eq $true -or $script:Actif -eq $false) { return }       # mode jeu ou sourdine : aucun son, aucun bip
    $freqs = switch ($nom) { 'actif' { @(660.0, 990.0) } 'sourdine' { @(880.0, 520.0) } default { $null } }
    if (-not $freqs) { return }
    $script:DernierSon = @{ nom = $nom; heure = (Get-Date) }
    try {
        $b = New-OctetsWav $freqs
        if (Test-ModeTest) { return }      # tests : on note le son demandé, on ne le joue pas
        if ($script:SonJoueur) { try { $script:SonJoueur.Stop(); $script:SonJoueur.Dispose() } catch {} }
        $script:SonJoueur = New-Object Media.SoundPlayer (New-Object IO.MemoryStream (, $b))
        $script:SonJoueur.Play()    # asynchrone
    } catch { Write-Journal -Action 'Son' -Resultat "échec : $($_.Exception.Message)" }
}
