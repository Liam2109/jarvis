# Voix : edge-tts (Henri / Ryan) avec repli System.Speech ; écoute Vosk -> System.Speech -> clavier
Add-Type -AssemblyName System.Speech
Add-Type -AssemblyName PresentationCore
$script:VoixDir = Join-Path (Split-Path -Parent $PSScriptRoot) 'voix'
if (-not (Get-Command Get-Politesse -ErrorAction SilentlyContinue)) { . (Join-Path $PSScriptRoot 'politesse.ps1') }      # ton majordome : catalogue unique des phrases de contrôle du PC
if (-not (Get-Command Get-VoixParam -ErrorAction SilentlyContinue)) { . (Join-Path $PSScriptRoot 'voix-naturelle.ps1') }      # voix naturelle : réglages, texte parlé, marge et fondu de fin

$script:Phrases = @{ bonjour = 'Bonjour monsieur'; ordres = 'À vos ordres'; bien = 'Très bien monsieur'; fait = "C'est fait" }

$script:ParleFlag = Join-Path (Split-Path -Parent $PSScriptRoot) 'memoire\parle.flag'
if (-not (Get-Command Set-VisageEtat -ErrorAction SilentlyContinue)) { function Set-VisageEtat([string]$e) { } }

function Set-AudioDebut {
    # Mesure : délai entre le début de l'ordre et le PREMIER SON de la réponse.
    if ($script:DernierOrdre -and -not $script:DernierOrdre.audio_s -and $script:DernierOrdre.debut) { $script:DernierOrdre.audio_s = ((Get-Date) - $script:DernierOrdre.debut).TotalSeconds }
}

function Lire-Mp3([string]$f) {
    if (Test-ModeTest) { Set-AudioDebut; return }        # tests : jamais de son
    # Lecture interruptible : "Jarvis stop" (STOP.flag) coupe la voix aussitôt, avec un fondu très court (pas de coupure sèche).
    # Fin d'audio : on attend que la lecture ATTEIGNE la fin du son, puis une marge de silence (voix_marge_fin_ms, 200 ms) avant de fermer le lecteur : la queue du son n'est plus coupée.
    $prm = Get-VoixParam
    $p = New-Object System.Windows.Media.MediaPlayer
    $p.Open([uri]$f); $p.Play(); Set-AudioDebut
    $n = 0; while (-not $p.NaturalDuration.HasTimeSpan -and $n++ -lt 50) { Start-Sleep -Milliseconds 30; Invoke-Pump }
    if ($p.NaturalDuration.HasTimeSpan) {
        $dur = $p.NaturalDuration.TimeSpan.TotalMilliseconds; $debut = Get-Date
        $plafond = $debut.AddMilliseconds((Get-DureeAttenteLecture $dur $prm.marge_ms) + 600); $finLecture = $null
        while ((Get-Date) -lt $plafond) {
            if (Test-Coupure) { Stop-AvecFondu $p $prm.fondu_ms; break }
            if (-not $finLecture -and ($p.Position.TotalMilliseconds -ge $dur - 15 -or ((Get-Date) - $debut).TotalMilliseconds -ge $dur + 600)) { $finLecture = Get-Date }
            if ($finLecture -and ((Get-Date) - $finLecture).TotalMilliseconds -ge $prm.marge_ms) { break }
            Invoke-Pump; Start-Sleep -Milliseconds 30
        }
    }
    $p.Close()
}

# ---------- Cache des phrases vocales : une phrase déjà synthétisée est rejouée INSTANTANÉMENT ----------
function Get-CheminTtsCache([string]$voix, [string]$texte) {
    $sha = [Security.Cryptography.SHA1]::Create()
    $h = ($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes("$voix|$texte")) | ForEach-Object { $_.ToString('x2') }) -join ''
    Join-Path $script:JarvisRoot "sounds\cache\$h.mp3"
}
$script:PhrasesPrechauffe = @('Bonjour monsieur', 'Bonsoir monsieur', 'À vos ordres', 'Très bien monsieur', "C'est fait", "C'est ouvert, monsieur.", "C'est fermé, monsieur.", 'Voilà, monsieur.', 'Dossier ouvert, monsieur.',
    'Je réfléchis, monsieur.', 'Votre liste de tâches est vide, monsieur.', 'Très bien monsieur, je passe en sourdine.', 'Coffre déverrouillé, monsieur.', 'Le coffre est verrouillé, monsieur.', 'À bientôt, monsieur.',
    'Arrêt immédiat, monsieur. Tout est coupé.', "Je n'ai pas pu joindre mon cerveau, monsieur. Veuillez réessayer.", 'Note enregistrée.', 'Tâche cochée.', 'Votre liste de tâches est vide.',
    "Le site tonproduit.shop répond, code 200.", "Le site tonproduit.shop répond, code 200, monsieur.", 'Sourdine activée.', "Je ne peux pas, monsieur.", 'Très bien monsieur, j''annule.')
$script:PhrasesReveilDefaut = @('Vous revoilà, monsieur.', 'Content de vous revoir, monsieur.', 'Bonjour, monsieur.', 'De retour, monsieur. Je suis à vous.', 'Ravi de vous retrouver, monsieur.')
$script:DernierReveil = ''
function Get-PhrasesReveil {
    # Liste de config.json (phrases_reveil) ou liste par défaut ; les phrases dépendant de l'heure s'y ajoutent dans Get-PhraseReveil.
    $l = @(); if ($Config -and $Config.PSObject.Properties['phrases_reveil']) { $l = @($Config.phrases_reveil | ForEach-Object { "$_".Trim() } | Where-Object { $_ }) }
    if (-not $l.Count) { $l = @($script:PhrasesReveilDefaut) }
    $l
}
function Get-PhraseReveil([datetime]$now = (Get-Date)) {
    # Salutation variée à l'activation (Alt + + / Verr. défil.). Avant 12 h : « Bonjour » favorisé ; 12-18 h : « Bon après-midi » ; après 18 h : « Bonsoir ». Jamais deux fois la même de suite.
    $liste = @(Get-PhrasesReveil)
    if ($now.Hour -lt 12) { $pool = @($liste | Where-Object { $_ -match '^Bonjour' }) + $liste + @($liste | Where-Object { $_ -match '^Bonjour' }) }      # « Bonjour » possible en priorité
    else {
        $pool = @($liste | Where-Object { $_ -notmatch '^Bonjour' })
        $pool += $(if ($now.Hour -lt 18) { 'Bon après-midi, monsieur.' } else { 'Bonsoir, monsieur.' })
    }
    $autres = @($pool | Where-Object { $_ -ne $script:DernierReveil })
    if ($autres.Count) { $pool = $autres }
    $p = $pool | Get-Random
    $script:DernierReveil = $p
    $p
}
function Get-PhrasesReveilCache { @(Get-PhrasesReveil) + 'Bon après-midi, monsieur.' + 'Bonsoir, monsieur.' }
function Start-PrechauffageTts {
    # Synthétise en arrière-plan (processus Python à priorité basse) les phrases fréquentes qui ne sont pas encore en cache.
    try {
        $dir = Join-Path $script:JarvisRoot 'sounds\cache'; if (-not (Test-Path $dir)) { New-Item -ItemType Directory $dir -Force | Out-Null }
        $f = @(Get-ChildItem $dir -Filter *.mp3 -ErrorAction SilentlyContinue | Sort-Object LastWriteTime)
        if ($f.Count -gt 500) { $f | Select-Object -First 100 | Remove-Item -Force -ErrorAction SilentlyContinue }     # ménage
        $prm = Get-VoixParam; $sig = Get-VoixSignature 'edge'
        $segments = @(@($script:PhrasesPrechauffe) + @(Get-PhrasesReveilCache) + @(Get-PolitessePrechauffe) | Select-Object -Unique | ForEach-Object { Get-MorceauxVoix $_ } | Select-Object -Unique)      # (les mêmes morceaux que ceux que Parler demandera)
        $items = @($segments | ForEach-Object { $c = Get-CheminTtsCache "$($Config.voix.fr)|$sig" $_; if (-not (Test-Path $c) -or (Get-Item $c).Length -lt 500) { @{ voix = $Config.voix.fr; texte = $_; cible = $c; rate = $prm.edge_rate; pitch = $prm.edge_pitch; volume = $prm.edge_volume } } })
        if (-not $items.Count) { return }
        $json = Join-Path $env:TEMP 'jarvis-prechauffe.json'; [IO.File]::WriteAllText($json, ($items | ConvertTo-Json -Depth 3), [Text.UTF8Encoding]::new($false))
        $pr = Start-Process python -ArgumentList '-I', "`"$(Join-Path $script:VoixDir 'prechauffe.py')`"", "`"$json`"" -WindowStyle Hidden -PassThru
        try { $pr.PriorityClass = 'BelowNormal' } catch {}
        Write-Journal -Action 'Voix' -Resultat "préchauffage du cache : $($items.Count) phrase(s) en arrière-plan"
    } catch { Write-Journal -Action 'Voix' -Resultat "préchauffage impossible : $($_.Exception.Message)" }
}

$script:Prefetch = @{}      # phrase suivante en cours de synthèse (réponses longues : on commence à parler dès la 1re phrase)
$script:DernierModeVoix = ''
# ---------- Voix locale Piper (config.json : "voix_moteur": "piper" ; "edge" par défaut = voix en ligne, qui reste le repli) ----------
# Un serveur Python (voix\piper_serveur.py, priorité basse) garde la voix chargée : 0,1 à 0,3 s par phrase, sans réseau. Voix : fr_FR-siwis-medium (licence CC-BY 4.0, usage personnel permis).
$script:PiperProc = $null; $script:PiperPret = Join-Path $env:TEMP 'jarvis-piper-pret.flag'; $script:PiperProchainEssai = [datetime]::MinValue
function Get-VoixMoteur { if ($Config.PSObject.Properties['voix_moteur'] -and "$($Config.voix_moteur)" -eq 'piper') { 'piper' } else { 'edge' } }
function Get-PiperVoix {
    # Voix Piper : "voix_piper" dans config.json — "tom" (homme, défaut) ou "siwis" (femme, en option). Si le fichier de la voix choisie manque, repli sur l'autre.
    $v = if ($Config.PSObject.Properties['voix_piper'] -and "$($Config.voix_piper)".Trim()) { "$($Config.voix_piper)".Trim().ToLowerInvariant() } else { 'tom' }
    if ($v -notmatch '^[a-z0-9_]+$') { $v = 'tom' }
    if (-not (Test-Path (Join-Path $script:VoixDir "models\piper\fr_FR-$v-medium.onnx"))) { $v = if ($v -eq 'tom') { 'siwis' } else { 'tom' } }
    $v
}
function Get-PiperModele { Join-Path $script:VoixDir "models\piper\fr_FR-$(Get-PiperVoix)-medium.onnx" }
function Test-PiperPret([switch]$Repli) {
    # -Repli : la voix en ligne (edge) a échoué ; la voix locale Piper (homme par défaut) sert de secours à la place de la voix de Windows (Hortense, seule voix installée = féminine).
    if (Test-ModeTest) { return $false }
    if ($Repli) { if ($Config.PSObject.Properties['voix_repli_piper'] -and $Config.voix_repli_piper -eq $false) { return $false } }
    elseif ((Get-VoixMoteur) -ne 'piper') { return $false }
    if ($script:PiperProc -and -not $script:PiperProc.HasExited) { return (Test-Path $script:PiperPret) }
    if ((Get-Date) -lt $script:PiperProchainEssai -or -not (Test-Path (Get-PiperModele))) { return $false }
    $script:PiperProchainEssai = (Get-Date).AddMinutes(5)          # au plus un démarrage / 5 min ; pendant le chargement (~8 s), les phrases partent en voix en ligne
    try {
        Remove-Item $script:PiperPret -ErrorAction SilentlyContinue
        $psi = New-Object System.Diagnostics.ProcessStartInfo 'python', "-I -u `"$(Join-Path $script:VoixDir 'piper_serveur.py')`" `"$(Get-PiperModele)`" `"$script:PiperPret`" $(Get-PiperParamsBase64)"
        $psi.UseShellExecute = $false; $psi.CreateNoWindow = $true; $psi.RedirectStandardInput = $true
        $script:PiperProc = [System.Diagnostics.Process]::Start($psi); try { $script:PiperProc.PriorityClass = 'BelowNormal' } catch {}
        Write-Journal -Action 'Voix' -Resultat 'voix locale Piper : chargement en arrière-plan (priorité basse)'
    } catch { Write-Journal -Action 'Voix' -Resultat "voix locale Piper impossible : $($_.Exception.Message)" }
    $false
}
function Send-PiperRequete([string]$texte, [string]$dest) {
    $t = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($texte))
    $script:PiperProc.StandardInput.WriteLine((@{ t = $t; d = $dest } | ConvertTo-Json -Compress)); $script:PiperProc.StandardInput.Flush()
}
function Stop-Piper { try { if ($script:PiperProc -and -not $script:PiperProc.HasExited) { $script:PiperProc.StandardInput.Close(); if (-not $script:PiperProc.WaitForExit(1500)) { $script:PiperProc.Kill() } } } catch { }; $script:PiperProc = $null; Remove-Item $script:PiperPret -ErrorAction SilentlyContinue }

function Start-SynthTts([string]$texte, [string]$voix, [switch]$ForcerPiper) {
    # Lance la synthèse (processus edge-tts) sans attendre ; une phrase déjà en cache est prête immédiatement.
    if ((-not $ForcerPiper -and (Test-PiperPret)) -or ($ForcerPiper -and (Test-PiperPret -Repli))) {      # voix locale prête : fichier WAV (cache pour les phrases courtes)
        $cw = if ($texte.Length -le 200) { [IO.Path]::ChangeExtension((Get-CheminTtsCache "piper-$(Get-PiperVoix)|$(Get-VoixSignature 'piper')" $texte), '.wav') } else { $null }
        if ($cw -and (Test-Path $cw) -and (Get-Item $cw).Length -gt 500) { return @{ pret = $true; mp3 = $cw; cache = $cw; mode = 'piper (cache)' } }
        $wav = if ($cw) { $cw } else { Join-Path $env:TEMP ("jarvis-{0}.wav" -f [guid]::NewGuid().ToString('N')) }
        if ($cw) { $d = Split-Path $cw; if (-not (Test-Path $d)) { New-Item -ItemType Directory $d -Force | Out-Null } }
        Remove-Item $wav -ErrorAction SilentlyContinue
        Send-PiperRequete $texte $wav
        return @{ pret = $false; piper = $true; mp3 = $wav; dest = "$wav.part"; cache = $cw; mode = 'piper' }
    }
    $cache = if ($texte.Length -le 200) { Get-CheminTtsCache "$voix|$(Get-VoixSignature 'edge')" $texte } else { $null }
    if ($cache -and (Test-Path $cache) -and (Get-Item $cache).Length -gt 500) { return @{ pret = $true; mp3 = $cache; cache = $cache; mode = 'edge-tts (cache)' } }
    $mp3 = if ($cache) { $cache } else { Join-Path $env:TEMP ("jarvis-{0}.mp3" -f [guid]::NewGuid().ToString('N')) }
    $dest = "$mp3.part"; Remove-Item $dest -ErrorAction SilentlyContinue
    if ($cache) { $d = Split-Path $cache; if (-not (Test-Path $d)) { New-Item -ItemType Directory $d -Force | Out-Null } }
    $psi = New-Object System.Diagnostics.ProcessStartInfo 'python', "-m edge_tts --voice $voix $(Get-EdgeArgsProsodie) --text `"$($texte -replace '"',"'")`" --write-media `"$dest`""
    $psi.UseShellExecute = $false; $psi.CreateNoWindow = $true; $psi.RedirectStandardError = $true
    @{ pret = $false; proc = [System.Diagnostics.Process]::Start($psi); dest = $dest; mp3 = $mp3; cache = $cache; mode = 'edge-tts' }
}
function Wait-SynthTts($h, [double]$delai) {
    # $true si le fichier audio est prêt dans le délai ; sinon $false (l'appelant bascule sur la voix locale de Windows).
    if ($h.pret) { return $true }
    $fin = (Get-Date).AddSeconds($delai)
    if ($h.piper) {
        while (-not (Test-Path $h.mp3) -and (Get-Date) -lt $fin -and -not (Test-Coupure)) { Invoke-Pump; Start-Sleep -Milliseconds 15 }
        if ((Test-Path $h.mp3) -and (Get-Item $h.mp3).Length -gt 500) { $h.pret = $true; return $true }
        return $false
    }
    while (-not $h.proc.HasExited -and (Get-Date) -lt $fin -and -not (Test-Coupure)) { Invoke-Pump; Start-Sleep -Milliseconds 25 }
    if (-not $h.proc.HasExited) { try { $h.proc.Kill() } catch {}; return $false }
    if ($h.proc.ExitCode -ne 0 -or -not (Test-Path $h.dest) -or (Get-Item $h.dest).Length -lt 500) { return $false }
    Move-Item $h.dest $h.mp3 -Force; $h.pret = $true; $true
}
function Lire-Morceau([string]$texte, [string]$voix, [string]$langue, [string]$suivant = '') {
    $tSynth = Get-Date
    $h = if ($script:Prefetch.ContainsKey($texte)) { $v = $script:Prefetch[$texte]; $script:Prefetch.Remove($texte); $v } else { Start-SynthTts $texte $voix }
    if ($suivant -and -not $script:Prefetch.ContainsKey($suivant)) { $script:Prefetch[$suivant] = Start-SynthTts $suivant $voix }      # on synthétise la suite pendant qu'on lit celle-ci
    $delai = if ($texte.Length -le 60) { 5 } else { 15 }          # phrase brève : 5 s pour la voix en ligne (le démarrage de edge-tts seul prend ~1,5 s) avant de basculer sur la voix locale de Windows
    try {
        if (Wait-SynthTts $h $delai) { $script:DernierModeVoix = $h.mode; if ($script:DernierOrdre -and $null -eq $script:DernierOrdre.synth_ms) { $script:DernierOrdre.synth_ms = ((Get-Date) - $tSynth).TotalMilliseconds }; Lire-Mp3 $h.mp3 } else { throw 'synthèse en ligne trop lente ou indisponible' }
    } catch {
        if (Test-Coupure) { return }
        if ($langue -eq 'fr' -and (Test-PiperPret -Repli)) {      # d'abord la voix locale Piper (homme), prête ou en cours de chargement ; Windows n'a qu'une voix féminine
            $hp = Start-SynthTts $texte $voix -ForcerPiper
            if (Wait-SynthTts $hp 6) { $script:DernierModeVoix = 'piper (repli)'; Write-Journal -Action 'Voix' -Resultat "repli Piper ($(Get-PiperVoix)) : la voix en ligne $voix n'a pas répondu en $delai s"; Lire-Mp3 $hp.mp3; return }
        }
        $script:DernierModeVoix = 'System.Speech (repli)'
        $s = New-Object System.Speech.Synthesis.SpeechSynthesizer
        # Repli : une voix d'HOMME française si Windows en a une (jamais « Hortense » par défaut) ; sinon la voix française disponible, et le journal le dit.
        $fr = @($s.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Culture.Name -like 'fr*' })
        $frH = $fr | Where-Object { $_.VoiceInfo.Gender -eq 'Male' } | Select-Object -First 1
        $choix = if ($frH) { $frH } else { $fr | Select-Object -First 1 }
        if ($choix -and $langue -eq 'fr') { $s.SelectVoice($choix.VoiceInfo.Name) }
        Write-Journal -Action 'Voix' -Resultat "repli System.Speech : $(if ($choix) { "$($choix.VoiceInfo.Name) ($($choix.VoiceInfo.Gender))" } else { 'voix par défaut' }) - la voix en ligne $voix n'a pas répondu en $delai s"
        $s.SpeakAsync($texte) | Out-Null; Set-AudioDebut
        while ($s.State -eq 'Speaking') { if (Test-Coupure) { $s.SpeakAsyncCancelAll(); break }; Invoke-Pump; Start-Sleep -Milliseconds 40 }
        $s.Dispose()
    } finally {
        if (-not $h.cache) { Remove-Item $h.mp3 -ErrorAction SilentlyContinue }
        Remove-Item "$($h.mp3).part" -ErrorAction SilentlyContinue
    }
}
function Parler {
    param([Parameter(Mandatory)][string]$Texte, [ValidateSet('fr','en')][string]$Langue = 'fr')
    $voix = if ($Langue -eq 'en') { $Config.voix.en } else { $Config.voix.fr }
    if (Get-Command Add-Conv -ErrorAction SilentlyContinue) { Add-Conv 'jarvis' $Texte }      # le texte apparaît tout de suite au panneau (avant même la voix)
    if ($script:CanalDiscord) {   # ordre venu de Discord : la réponse est ÉCRITE sur Discord (lib\discord.ps1), jamais prononcée
        if ($script:CaptureBriefing) { $script:BriefingLignes.Add($Texte) }
        Add-TamponDiscord $Texte; Write-Journal -Action 'Réponse écrite (Discord)' -Resultat (Short $Texte 300); return
    }
    if (Test-ModeServeur) { if ($script:CaptureBriefing) { $script:BriefingLignes.Add($Texte) }; Write-Journal -Action 'Parole non prononcée (mode serveur)' -Resultat $Texte; return }      # serveur : aucune voix (le texte reste au journal et sur Discord)
    if ($script:Actif -eq $false) {   # sourdine : Jarvis ne parle pas (le texte reste visible au tableau de bord et dans le journal)
        if ($script:CaptureBriefing) { $script:BriefingLignes.Add($Texte) }
        Write-Journal -Action 'Parole non prononcée (sourdine)' -Resultat $Texte
        return
    }
    if (Get-Command Test-VoixPermise -ErrorAction SilentlyContinue) {
        $perm = Test-VoixPermise
        if (-not $perm.ok) { if ($script:CaptureBriefing) { $script:BriefingLignes.Add($Texte) }; Retenir-Parole $Texte $perm.raison; return }
    }
    if (Test-Coupure) { return }
    if ($script:DernierOrdre -and -not $script:DernierOrdre.parole_s -and $script:DernierOrdre.debut) { $script:DernierOrdre.parole_s = ((Get-Date) - $script:DernierOrdre.debut).TotalSeconds }      # mesure : demande de parole
    if (Test-ModeTest) { Set-AudioDebut; if ($script:CaptureBriefing) { $script:BriefingLignes.Add($Texte) }; Write-Journal -Action 'Parole (test silencieux)' -Resultat $Texte; return }     # tests : jamais de son
    if ($script:AccuseLecteur) { Wait-AccuseFini }      # l'accusé instantané se termine avant la suite (pas de chevauchement)
    $tn = Get-Date
    $morceaux = @(Get-MorceauxVoix $Texte)      # texte préparé pour être DIT (chiffres, ponctuation, rythme), une phrase par morceau : on parle dès la 1re phrase
    if ($script:DernierOrdre) { $script:DernierOrdre.norm_ms = ((Get-Date) - $tn).TotalMilliseconds }      # mesure : coût de la préparation du texte (diagnostic vocal)
    Set-Content $script:ParleFlag '1' -Encoding ASCII; Set-VisageEtat 'parle'
    if (Get-Command Set-SonsParole -ErrorAction SilentlyContinue) { Set-SonsParole $true }   # la musique baisse pendant que Jarvis parle
    try {
        for ($i = 0; $i -lt $morceaux.Count; $i++) { if (Test-Coupure) { break }; Lire-Morceau $morceaux[$i] $voix $Langue $(if ($i + 1 -lt $morceaux.Count) { $morceaux[$i + 1] } else { '' }); if ($i + 1 -lt $morceaux.Count) { Wait-PauseVoix } }
    } finally {
        $script:Prefetch.Clear()
        Remove-Item $script:ParleFlag -ErrorAction SilentlyContinue; Set-VisageEtat 'ecoute'
        if (Get-Command Set-SonsParole -ErrorAction SilentlyContinue) { Set-SonsParole $false }   # la musique remonte doucement
    }
    Write-Host "Jarvis : $Texte"
    if ($script:CaptureBriefing) { $script:BriefingLignes.Add($Texte) }
    Write-Journal -Action "Parole ($script:DernierModeVoix)" -Resultat $Texte
}
function Dire([string]$cle) { Parler $script:Phrases[$cle] }

function Ecouter-Ordre {
    # Retourne le texte de l'ordre, ou $null. Essaie Vosk, puis System.Speech, puis le clavier.
    param([int]$Timeout = 60)
    if (Test-ModeTest) { return $null }                  # tests : jamais le micro
    $py = Join-Path $script:VoixDir 'ecoute.py'
    $out = & python -I $py --timeout $Timeout 2>$null
    $o = $out | Where-Object { $_ -like 'ORDRE:*' } | Select-Object -First 1
    if ($o) { return $o.Substring(6).Trim() }
    if ($LASTEXITCODE -eq 3) {
        Write-Host '(Vosk/micro indisponible, repli System.Speech)'
        try {
            $r = New-Object System.Speech.Recognition.SpeechRecognitionEngine ([Globalization.CultureInfo]'fr-FR')
            $r.SetInputToDefaultAudioDevice()
            $r.LoadGrammar((New-Object System.Speech.Recognition.DictationGrammar))
            $res = $r.Recognize([TimeSpan]::FromSeconds($Timeout))
            if ($res -and $res.Text -match '(?i)jarvis\s*(.*)') { return $Matches[1].Trim() }
            return $null
        } catch { Write-Host '(micro indisponible, saisie clavier)' }
    }
    return $null
}

function Lire-Clavier { $t = Read-Host 'Ordre (clavier)'; if ($t) { $t.Trim() } }
