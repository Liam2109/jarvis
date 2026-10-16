# Voix plus naturelle (Edge et Piper) : réglages validés, texte normalisé avant la synthèse (ponctuation, rythme, chiffres, pourcentages, dates, heures, listes),
# découpage en phrases avec courte pause entre elles, marge de silence et fondu en fin d'audio. Le ton majordome ne change pas : seul le texte DIT est préparé ;
# le texte affiché, journalisé ou écrit sur Discord reste celui d'origine. config.json : "voix_naturelle": false désactive la préparation du texte.
$script:MoisParles = 'janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre'

function Get-VoixNombre([string]$nom, [double]$defaut, [double]$min, [double]$max) {
    $v = $defaut
    if ($Config -and $Config.PSObject.Properties[$nom]) { $x = 0.0; if ([double]::TryParse(("$($Config.$nom)" -replace ',', '.'), [Globalization.NumberStyles]::Float, [Globalization.CultureInfo]::InvariantCulture, [ref]$x)) { $v = $x } }
    [math]::Max($min, [math]::Min($max, $v))
}
function Get-VoixTexteReglage([string]$nom, [string]$motif, [string]$defaut) {
    if ($Config -and $Config.PSObject.Properties[$nom] -and "$($Config.$nom)".Trim() -match $motif) { return "$($Config.$nom)".Trim() }
    $defaut
}
function Get-VoixParam {
    # Tous les réglages de voix, bornés. Défauts : débit légèrement plus doux, intonation un peu moins plate, marge de silence de 200 ms en fin d'audio.
    @{
        naturelle   = -not ($Config -and $Config.PSObject.Properties['voix_naturelle'] -and $Config.voix_naturelle -eq $false)
        edge_rate   = (Get-VoixTexteReglage 'voix_edge_rate' '^[+-]\d{1,2}%$' '-4%')
        edge_pitch  = (Get-VoixTexteReglage 'voix_edge_pitch' '^[+-]\d{1,3}Hz$' '-2Hz')
        edge_volume = (Get-VoixTexteReglage 'voix_edge_volume' '^[+-]\d{1,2}%$' '+0%')
        piper_length = (Get-VoixNombre 'voix_piper_length_scale' 1.08 0.8 1.5)
        piper_noise  = (Get-VoixNombre 'voix_piper_noise_scale' 0.75 0.1 1.0)
        piper_noise_w = (Get-VoixNombre 'voix_piper_noise_w' 0.9 0.1 1.2)
        piper_silence = (Get-VoixNombre 'voix_piper_sentence_silence' 0.25 0.0 1.0)
        marge_ms    = [int](Get-VoixNombre 'voix_marge_fin_ms' 200 0 600)
        fondu_ms    = [int](Get-VoixNombre 'voix_fondu_ms' 40 0 150)
        pause_ms    = [int](Get-VoixNombre 'voix_pause_phrase_ms' 220 0 800)
    }
}
function Get-EdgeArgsProsodie { $p = Get-VoixParam; "--rate=$($p.edge_rate) --pitch=$($p.edge_pitch) --volume=$($p.edge_volume)" }
function Get-VoixSignature([string]$moteur) {
    # Empreinte des réglages : entre dans la clé du cache vocal (un changement de rythme ne rejoue pas un ancien enregistrement).
    $p = Get-VoixParam; $n = $(if ($p.naturelle) { 'n' } else { 'o' })
    if ($moteur -eq 'piper') { return ("p{0}|{1}|{2}|{3}|{4}|{5}|{6}" -f $n, $p.piper_length, $p.piper_noise, $p.piper_noise_w, $p.piper_silence, $p.marge_ms, $p.fondu_ms) }
    "e$n|$($p.edge_rate)|$($p.edge_pitch)|$($p.edge_volume)"
}
function Get-PiperParamsBase64 {
    $p = Get-VoixParam
    $j = @{ length_scale = $p.piper_length; noise_scale = $p.piper_noise; noise_w = $p.piper_noise_w; sentence_silence = $p.piper_silence; marge_ms = $p.marge_ms; fondu_ms = $p.fondu_ms } | ConvertTo-Json -Compress
    [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($j))
}
function Get-DureeAttenteLecture([double]$dureeMs, [int]$margeMs) { $dureeMs + $margeMs }

# ---------- Texte parlé ----------
function ConvertTo-JourParle([int]$j) { if ($j -eq 1) { 'premier' } else { "$j" } }
function ConvertTo-DateParlee([int]$j, [int]$m, [string]$annee = '') {
    if ($j -lt 1 -or $j -gt 31 -or $m -lt 1 -or $m -gt 12) { return $null }
    "le $(ConvertTo-JourParle $j) $($script:MoisParles[$m - 1])" + $(if ($annee) { " $annee" } else { '' })
}
function Format-TexteVoix([string]$t) {
    # Rend un texte écrit agréable à DIRE : chiffres, pourcentages, euros, dates et heures en toutes lettres ; puces et listes en phrases ; virgules, points et pauses aux bons endroits ;
    # phrases très longues coupées. Idempotent ; une phrase déjà propre reste identique (le cache vocal des phrases fixes continue de servir).
    if (-not $t) { return $t }
    $t = $t -replace '[\*`#]+', ''
    $lignes = @($t -split '\r?\n' | ForEach-Object { ($_ -replace '^\s*(?:[•–\-]|\d+[.)])\s+', '').Trim() } | Where-Object { $_ })
    if ($lignes.Count -gt 1) { $lignes = @($lignes | ForEach-Object { if ($_ -match '[.!?…:;,]$') { $_ } else { "$_." } }) }
    $t = ($lignes -join ' ')
    # dates (un « le », « du », « au »... déjà présent est conservé tel quel, avec sa majuscule éventuelle)
    $t = [regex]::Replace($t, '(?<![\d/])((?i:le|du|au|depuis|jusqu''au)\s+)?(20\d\d)-(\d{2})-(\d{2})(?![\d-])', { param($m) $d = ConvertTo-DateParlee ([int]$m.Groups[4].Value) ([int]$m.Groups[3].Value) $m.Groups[2].Value; if (-not $d) { return $m.Value }; if ($m.Groups[1].Success) { $m.Groups[1].Value + ($d -replace '^le ', '') } else { $d } })
    $t = [regex]::Replace($t, '(?<![\d/])((?i:le|du|au|depuis|jusqu''au)\s+)?(\d{1,2})/(\d{1,2})/(\d{4})(?![\d/])', { param($m) $d = ConvertTo-DateParlee ([int]$m.Groups[2].Value) ([int]$m.Groups[3].Value) $m.Groups[4].Value; if (-not $d) { return $m.Value }; if ($m.Groups[1].Success) { $m.Groups[1].Value + ($d -replace '^le ', '') } else { $d } })
    $t = [regex]::Replace($t, '(?<=\b(?i:le|du|au|depuis|jusqu''au)\s)(\d{1,2})/(\d{1,2})(?![\d/])', { param($m) $d = ConvertTo-DateParlee ([int]$m.Groups[1].Value) ([int]$m.Groups[2].Value); if ($d) { $d -replace '^le ', '' } else { $m.Value } })
    # heures
    $t = [regex]::Replace($t, '(?<![\d:])([01]?\d|2[0-3]):([0-5]\d)(?![\d:])', { param($m) $h = [int]$m.Groups[1].Value; $mi = [int]$m.Groups[2].Value; "$h heure$(if ($h -gt 1) { 's' })" + $(if ($mi) { " $mi" } else { '' }) })
    # pourcentages (avec signe) puis monnaies
    $t = [regex]::Replace($t, '(?<![\w,.])(?:([+\-−–])\s?)?(\d+(?:[,.]\d+)?)\s?%', { param($m) $s = $m.Groups[1].Value; $pre = $(if ($s -eq '+') { 'plus ' } elseif ($s) { 'moins ' } else { '' }); "$pre$($m.Groups[2].Value) pour cent" })
    $t = $t -replace '(?<![\d,.])1\s?€', '1 euro' -replace '\s?€', ' euros' -replace '(\d)\s?EUR\b', '$1 euros' -replace '(\d)\s?(?:USD|\$)', '$1 dollars'
    $t = $t -replace '\bN°\s?', 'numéro ' -replace '\bn°\s?', 'numéro ' -replace '\s&\s', ' et ' -replace '\s*(?:->|→)\s*', ', '
    # listes : « a ; b ; c » -> « a, b et c »
    $parts = @($t -split '\s*;\s*' | Where-Object { $_.Trim() })
    if ($parts.Count -ge 3) { $t = (($parts[0..($parts.Count - 2)] | ForEach-Object { $_.Trim(' .') }) -join ', ') + ' et ' + $parts[-1].Trim() } else { $t = ($parts -join ', ') }
    $t = $t -replace '\s*\(([^)]*)\)', ', $1,' -replace '\s:\s', ', ' -replace '(?<=\w):\s(?=[a-zà-ÿ])', ', '
    # nettoyage de la ponctuation
    $t = $t -replace '\s+', ' ' -replace '\s+([,.;])', '$1' -replace ',(\s*,)+', ',' -replace ',\s*([.!?…])', '$1' -replace '(?<!\.)\.\s*\.(?!\.)', '.' -replace '([.!?…])\s*,', '$1'
    $t = $t.Trim().TrimStart(',', ' ')
    # phrases très longues : coupées à une virgule proche du milieu
    $ph = @([regex]::Split($t, '(?<=[.!?…])\s+'))
    $sortie = @()
    foreach ($p in $ph) {
        if ($p.Length -gt 150) {
            $mid = $p.Length / 2; $best = -1; $bd = [double]::MaxValue
            foreach ($m in [regex]::Matches($p, ', ')) { if ($m.Index -ge 50 -and ($p.Length - $m.Index) -ge 50 -and [math]::Abs($m.Index - $mid) -lt $bd) { $bd = [math]::Abs($m.Index - $mid); $best = $m.Index } }
            if ($best -ge 0) { $a = $p.Substring(0, $best) + '.'; $b = $p.Substring($best + 2); $sortie += $a; $sortie += ($b.Substring(0, 1).ToUpperInvariant() + $b.Substring(1)); continue }
        }
        $sortie += $p
    }
    ($sortie -join ' ').Trim()
}
function Get-MorceauxVoix([string]$texte) {
    # Les morceaux à synthétiser, dans l'ordre : une phrase chacun (pause entre eux), les très courts fragments rattachés à la suivante.
    # voix_naturelle = false : comportement d'avant (un seul morceau, ou des phrases au-delà de 140 caractères).
    $texte = "$texte"
    if (-not (Get-VoixParam).naturelle) {
        if ($texte.Length -gt 140) { $ph = @([regex]::Split($texte, '(?<=[.!?])\s+') | Where-Object { $_.Trim() }); if ($ph.Count -ge 2) { return $ph } }
        return @($texte)
    }
    $n = Format-TexteVoix $texte
    $ph = @([regex]::Split($n, '(?<=[.!?…])\s+') | Where-Object { $_.Trim() })
    $m = New-Object System.Collections.Generic.List[string]
    $reste = ''
    foreach ($p in $ph) {
        $cur = $(if ($reste) { "$reste $p" } else { $p }); $reste = ''
        if ($cur.Length -lt 12 -and $p -ne $ph[-1]) { $reste = $cur } else { $m.Add($cur) }
    }
    if ($reste) { $m.Add($reste) }
    if (-not $m.Count) { return @($n) }
    @($m)
}
function Wait-PauseVoix {
    $ms = (Get-VoixParam).pause_ms; if ($ms -le 0) { return }
    $fin = (Get-Date).AddMilliseconds($ms)
    while ((Get-Date) -lt $fin) { if (Test-Coupure) { break }; Invoke-Pump; Start-Sleep -Milliseconds 20 }
}
function Stop-AvecFondu($lecteur, [int]$fonduMs) {
    # Arrêt de la lecture sans clic ni coupure sèche : le volume descend en quelques pas très courts.
    try {
        if ($fonduMs -gt 0) { $v0 = [double]$lecteur.Volume; for ($i = 1; $i -le 4; $i++) { $lecteur.Volume = $v0 * (1 - $i / 4.0); Start-Sleep -Milliseconds ([math]::Max(1, [int]($fonduMs / 4))) } }
        $lecteur.Stop()
    } catch { }
}

# ---------- Vitesse V3 : réponses parlées courtes, accusé instantané, réponse en flux ----------
function Get-ReponsesCourtes { -not ($Config -and $Config.PSObject.Properties['reponses_courtes'] -and $Config.reponses_courtes -eq $false) }      # défaut : 2 à 3 phrases à voix haute
function Limit-DitVocal([string]$dit, [int]$maxPhrases = 3, [int]$maxCar = 320) {
    # Réponse PARLÉE courte : 3 phrases et 320 caractères au plus ; le reste (le détail) va à l'écran ou sur Discord, sur demande (« détaille »). @{ court; complet; coupe }
    $t = "$dit".Trim()
    $ph = @([regex]::Split($t, '(?<=[.!?…])\s+') | Where-Object { $_.Trim() })
    if ($ph.Count -le $maxPhrases -and $t.Length -le $maxCar) { return @{ court = $t; complet = $t; coupe = $false } }
    $c = ($ph | Select-Object -First $maxPhrases) -join ' '
    if ($c.Length -gt $maxCar) { $c = $c.Substring(0, $maxCar); $k = $c.LastIndexOfAny(@(' ', ',', ';')); if ($k -gt 60) { $c = $c.Substring(0, $k) }; $c = $c.TrimEnd(' ', ',', ';') + '.' }
    @{ court = $c; complet = $t; coupe = $true }
}
$script:DernierDitComplet = ''
$script:AccuseLecteur = $null; $script:DernierAccuse = ''
$script:ActionsAccuse = 'ouvrir_app', 'ouvrir_site', 'ouvrir_chemin', 'vscode_ouvrir', 'pc_dossier', 'mode_pc', 'analyse_defender', 'business_etat', 'point_saas', 'marche_valeur', 'marche_resume', 'salle_marche',
    'briefing_dire', 'briefing_relire', 'briefing_details', 'winget_proposer', 'pc_capture', 'scanner_menaces', 'dossier_valeur', 'surveiller_5'
function Get-AccuseCache {
    # Un accusé PRÉ-ENREGISTRÉ (phrase du catalogue « accuse », déjà en cache vocal) ; jamais de synthèse à la demande. @{ texte; chemin } ou $null.
    $phrase = Get-Politesse 'accuse'; if (-not $phrase) { return $null }
    $seg = @(Get-MorceauxVoix $phrase); if ($seg.Count -ne 1) { return $null }
    $cands = @()
    if ((Get-VoixMoteur) -eq 'piper') { $cands += [IO.Path]::ChangeExtension((Get-CheminTtsCache "piper-$(Get-PiperVoix)|$(Get-VoixSignature 'piper')" $seg[0]), '.wav') }
    $cands += (Get-CheminTtsCache "$($Config.voix.fr)|$(Get-VoixSignature 'edge')" $seg[0])
    foreach ($c in $cands) { if ((Test-Path $c) -and (Get-Item $c).Length -gt 500) { return @{ texte = $phrase; chemin = $c } } }
    $null
}
function Test-AccuseUtile($plan) {
    # Accusé seulement pour une commande qui prend un instant (ouvrir, données, point...), jamais pour un réglage évident, jamais en sourdine / mode jeu / Discord / discret.
    if (-not $plan -or -not $plan.actions -or -not @($plan.actions).Count) { return $false }
    if ($Config -and $Config.PSObject.Properties['accuse_instantane'] -and $Config.accuse_instantane -eq $false) { return $false }
    if ($script:CanalDiscord -or $script:Actif -eq $false -or $script:ModeJeu -eq $true -or (Test-Stop)) { return $false }
    if (Get-Command Test-VoixPermise -ErrorAction SilentlyContinue) { if (-not (Test-VoixPermise).ok) { return $false } }
    [bool](@($plan.actions | Where-Object { $_ -and "$($_.type)".ToLower() -in $script:ActionsAccuse }).Count)
}
function Start-AccuseInstantane($plan) {
    # Joue l'accusé SANS attendre (lecture asynchrone) : l'action démarre aussitôt. Parler attend la fin de l'accusé avant de dire la suite (Wait-AccuseFini).
    if (-not (Test-AccuseUtile $plan)) { return $false }
    $a = Get-AccuseCache; if (-not $a) { return $false }
    $script:DernierAccuse = $a.texte
    if (Test-ModeTest) { return $true }          # tests : jamais de son
    try {
        $p = New-Object System.Windows.Media.MediaPlayer; $p.Open([uri]$a.chemin); $p.Play(); $script:AccuseLecteur = $p; $script:AccuseDebut = Get-Date
        if (Get-Command Set-AudioDebut -ErrorAction SilentlyContinue) { Set-AudioDebut }
        $true
    } catch { $script:AccuseLecteur = $null; $false }
}
function Wait-AccuseFini {
    if (-not $script:AccuseLecteur) { return }
    try {
        $fin = $script:AccuseDebut.AddSeconds(2.5)
        while ((Get-Date) -lt $fin -and -not (Test-Coupure)) {
            if ($script:AccuseLecteur.NaturalDuration.HasTimeSpan -and $script:AccuseLecteur.Position -ge $script:AccuseLecteur.NaturalDuration.TimeSpan) { break }
            Invoke-Pump; Start-Sleep -Milliseconds 30
        }
        $script:AccuseLecteur.Close()
    } catch { }
    $script:AccuseLecteur = $null
}

# ---------- Réponse de Claude en flux : on parle dès la première phrase (claude_flux = true, activé par défaut ; false pour revenir à l'attente de la réponse complète) ----------
function Get-ClaudeFlux { [bool]($Config -and $Config.PSObject.Properties['claude_flux'] -and $Config.claude_flux -eq $true) }
function ConvertFrom-FluxClaude([string[]]$lignes) {
    # Lignes JSON de « claude -p --output-format stream-json --include-partial-messages » -> @{ texte (cumulé) ; final ; fini }. Tolérant : une ligne illisible est ignorée.
    $texte = New-Object System.Text.StringBuilder; $final = $null; $assistant = ''
    foreach ($l in @($lignes)) {
        if (-not "$l".Trim()) { continue }
        try { $e = $l | ConvertFrom-Json } catch { continue }
        if ($e.type -eq 'stream_event' -and $e.event -and $e.event.type -eq 'content_block_delta' -and $e.event.delta -and $e.event.delta.PSObject.Properties['text']) { [void]$texte.Append("$($e.event.delta.text)") }
        elseif ($e.type -eq 'assistant' -and $e.message -and $e.message.content) { $assistant = (@($e.message.content | Where-Object { $_.PSObject.Properties['text'] } | ForEach-Object { $_.text }) -join '') }
        elseif ($e.type -eq 'result' -and $e.PSObject.Properties['result']) { $final = "$($e.result)" }
    }
    $t = $texte.ToString(); if (-not $t) { $t = $assistant }
    @{ texte = $t; final = $final; fini = ($null -ne $final) }
}
function Get-PremierePhraseDit([string]$cumul) {
    # Dans le JSON en cours d'écriture {"dit":"Première phrase. Deuxième...", ...}, retourne la PREMIÈRE phrase dès qu'elle est terminée ; sinon $null.
    $m = [regex]::Match("$cumul", '"dit"\s*:\s*"((?:[^"\\]|\\.)*)')
    if (-not $m.Success) { return $null }
    try { $brut = ('"' + $m.Groups[1].Value + '"') | ConvertFrom-Json } catch { return $null }
    $f = [regex]::Match("$brut", '^(.+?[.!?…])(\s|$)')
    if (-not $f.Success) { return $null }
    $ph = $f.Groups[1].Value.Trim()
    if ($ph.Length -lt 12) { return $null }
    # la phrase doit être suivie d'un espace dans le texte (sinon elle peut encore s'allonger : « 3,5 » -> « 3. »)
    if ($f.Groups[2].Value -eq '' -and $cumul -notmatch '"dit"\s*:\s*"(?:[^"\\]|\\.)*"') { return $null }
    $ph
}
function Get-DitRestant([string]$dit) {
    # Ce qui reste à dire quand la première phrase a déjà été dite en flux.
    $d = "$dit".Trim(); $dp = "$script:DitPartiel".Trim()
    if (-not $dp) { return $d }
    if ($d.StartsWith($dp)) { return $d.Substring($dp.Length).Trim() }
    $d
}
$script:DitPartiel = ''; $script:SurPhraseClaude = $null
