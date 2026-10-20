# Veille « annonces-train » : cherche des annonces de conducteur de train (emplois ET formations) et les envoie sur Discord, une carte par NOUVELLE annonce. DÉSACTIVÉE par défaut (veille_train = "non").
# Lecture seule : aucune candidature, aucun message à des tiers, aucun projet touché. Le passage (toutes les heures, rattrapage au démarrage) tourne dans un processus séparé (veille-train.ps1) : la boucle de Jarvis n'attend jamais le réseau.
# Sources exploitables (vérifiées) : API JSON officielle des offres CFF/SBB ; API « Offres d'emploi » de France Travail (seulement si FRANCETRAVAIL_ID et FRANCETRAVAIL_SECRET sont dans .env), qui relaie aussi les offres SNCF / Transilien / RATP.
# Get-TrainPage lit les liens d'une page publique qui l'autorise (aucune source active pour l'instant : SOB, SNCF, RATP, BLS... refusent ou n'ont pas de liste lisible, voir le compte rendu).
# Politesse : une requête à la fois, 2 s au moins entre deux requêtes, robots.txt respecté, identification claire, aucun scraping de LinkedIn / Indeed, aucun contournement de protection (403 / défi anti-robot = source abandonnée et signalée).
# Base locale : memoire\veille-train.json (memoire\ n'est pas suivi par Git) : annonces déjà vues, dernier passage, dernier résumé, dernière alerte d'erreur par source.

if (-not (Get-Command Short -ErrorAction SilentlyContinue)) { function Short([string]$s, [int]$n = 4000) { if ($s -and $s.Length -gt $n) { $s.Substring(0, $n) + '…' } else { $s } } }
$script:TrainUA = 'Mozilla/5.0 (compatible; JarvisVeille/1.0; usage personnel, une requete espacee)'
$script:TrainPauseSec = 2; $script:TrainDernierReq = [datetime]::MinValue; $script:TrainRobots = @{}; $script:TrainProchainTour = [datetime]::MinValue
$script:TrainHttpStub = $null; $script:TrainNotifStub = $null; $script:TrainRunnerLance = $false
$script:TrainMaxCartes = 8; $script:TrainMaxVus = 3000

function Get-TrainConfig {
    $oui = @('oui', 'true', '1', 'on', 'yes'); $c = @{ actif = $false; minutes = 60; resume = '08:00' }
    if ($Config.PSObject.Properties['veille_train'] -and "$($Config.veille_train)".Trim().ToLower() -in $oui) { $c.actif = $true }
    if ($Config.PSObject.Properties['veille_train_minutes'] -and "$($Config.veille_train_minutes)" -match '^\d+$') { $c.minutes = [math]::Max(15, [math]::Min(1440, [int]$Config.veille_train_minutes)) }
    if ($Config.PSObject.Properties['veille_train_resume_heure'] -and "$($Config.veille_train_resume_heure)" -match '^([01]?\d|2[0-3]):[0-5]\d$') { $c.resume = "$($Config.veille_train_resume_heure)".PadLeft(5, '0') }
    $c
}

# ---------- Reconnaissance d'une annonce de conduite ----------
function ConvertTo-TrainNorm([string]$t) { ((("$t".ToLowerInvariant().Normalize([Text.NormalizationForm]::FormD)) -replace '\p{Mn}', '') -replace '[^a-z0-9]+', ' ').Trim() }
$script:TrainMotif = 'conduct(?:eur|rice)s?(?: (?:ou )?conduct(?:eur|rice))?(?: trice)? (?:de |des )?(?:trains?|lignes?|metros?|rer|tramways?|vehicules? moteurs?|manoeuvres?)|agents? de conduite|formation (?:de |d un |du )?(?:futur )?conducteur|lokfuhrer|lokfuehrer|lokomotivfuhrer|triebfahrzeugfuhrer|triebfahrzeugfuehrer|mecanicien(?:ne)? de locomotive|macchinista'
function Test-TrainAnnonce([string]$titre) { $n = ConvertTo-TrainNorm $titre; ($n -match $script:TrainMotif) -and ($n -notmatch '\b(bus|autocar|autobus)\b') }
function Get-TrainType([string]$titre) { if ((ConvertTo-TrainNorm $titre) -match 'formation|quereinstieg|zweitausbildung|reconversion|alternance|apprenti|lehre|diplome|stage') { 'Formation' } else { 'Emploi' } }
function New-TrainAnnonce([string]$source, [string]$ident, [string]$titre, [string]$employeur, [string]$lieu, [string]$date, [string]$lien) {
    if ($lien -notmatch '^https://') { $lien = '' }
    @{ id = "${source}:$ident"; source = $source; titre = "$titre".Trim(); employeur = $(if ("$employeur".Trim()) { "$employeur".Trim() } else { 'non précisé' }); lieu = $(if ("$lieu".Trim()) { "$lieu".Trim() } else { 'non précisé' }); date = "$date"; lien = $lien; type = (Get-TrainType $titre) }
}

# ---------- Filtre « francophone en Suisse romande » (sources suisses seulement) ----------
# Lieu : liste blanche (tout ce qui n'y est pas, Zurich, Berne, Bâle, lieu inconnu... est écarté). Fribourg / Bienne (bilingues) : gardés seulement si le titre n'est pas en allemand.
# Langue : seul le titre l'indique. Titre allemand dans un lieu romand = gardé mais marqué « Allemand probable » (carte) ; la page SOB (lieu inconnu) est écartée si le titre est allemand.
$script:TrainRomand = '\b(lausanne|geneve|geneva|genf|vaud|yverdon|vevey|montreux|renens|morges|nyon|sion|sierre|siders|martigny|monthey|aigle|bex|delemont|la chaux de fonds|neuchatel|neuenburg|le locle|jura|porrentruy|valais|bulle|payerne|vallorbe|palezieux|cossonay|gland|rolle|prilly|crissier|ecublens|pully|lutry|vernier|carouge|lancy|meyrin|versoix|romont|chexbres|puidoux|villeneuve|saint maurice|st maurice|fully|orbe|echallens|moudon|avenches|saint imier|tavannes|moutier|courtelary|travers|couvet|fleurier|les brenets)\b'
$script:TrainBilingue = '\b(fribourg|freiburg|biel|bienne|murten|morat)\b'
$script:TrainMotifAllemand = 'lokfuhrer|lokfuehrer|triebfahrzeug|quereinstieg|zweitausbildung|rangier|zugmaschine|bauzug|fahrleitung|personenverkehr|guterverkehr|kategorie|\bkat\b|\bund\b|\bmit\b|erfahrung|ausbildung'
function Test-TrainAllemand([string]$titre) { $n = ConvertTo-TrainNorm $titre; ($n -match $script:TrainMotifAllemand) -and ($n -notmatch 'conduct(?:eur|rice)|mecanicien|agent de conduite') }
function Get-TrainFiltreSuisse([string]$lieu, [string]$titre) {
    # @{ garde; allemand } : garde = lieu romand (et titre non allemand si le lieu est seulement bilingue).
    $l = ConvertTo-TrainNorm $lieu; $fr = $l -match $script:TrainRomand; $bi = $l -match $script:TrainBilingue; $de = Test-TrainAllemand $titre
    $garde = ($fr -or ($bi -and -not $de))
    @{ garde = $garde; allemand = $de; raison = $(if ($garde) { '' } elseif ($bi) { 'langue' } else { 'lieu' }) }      # raison de l'écart : lieu hors liste blanche, ou lieu bilingue avec un titre allemand
}
function Add-TrainEcart([string]$raison) { if (-not $script:TrainEcart) { $script:TrainEcart = @{ lieu = 0; langue = 0 } }; $script:TrainEcart[$raison]++ }

# ---------- Réseau poli (bouchon en test) ----------
function Wait-TrainPoli { if ($script:TrainPauseSec -gt 0) { $r = $script:TrainPauseSec - ((Get-Date) - $script:TrainDernierReq).TotalSeconds; if ($r -gt 0) { Start-Sleep -Milliseconds ([int]($r * 1000)) } }; $script:TrainDernierReq = Get-Date }
function Invoke-TrainHttp([string]$url, [string]$methode = 'GET', [string]$corps = '', [hashtable]$entetes = @{}) {
    # @{ code; texte } ; code 0 = erreur réseau (texte = raison). Jamais d'exception.
    if ($script:TrainHttpStub) { return (& $script:TrainHttpStub $url $methode $corps $entetes) }
    Wait-TrainPoli
    try {
        $a = @{ Uri = $url; Method = $methode; UseBasicParsing = $true; TimeoutSec = 30; Headers = (@{ 'User-Agent' = $script:TrainUA; 'Accept-Language' = 'fr,de;q=0.8' } + $entetes) }
        if ($corps) { $a.Body = $corps; $a.ContentType = 'application/x-www-form-urlencoded' }
        $r = Invoke-WebRequest @a
        $ms = New-Object IO.MemoryStream; $r.RawContentStream.CopyTo($ms)
        @{ code = [int]$r.StatusCode; texte = [Text.Encoding]::UTF8.GetString($ms.ToArray()) }
    } catch {
        $code = 0; try { $code = [int]$_.Exception.Response.StatusCode } catch {}
        @{ code = $code; texte = (Hide-Secrets $_.Exception.Message) }
    }
}
function Test-TrainRobots([string]$url) {
    # robots.txt de l'hôte (une fois par passage) : faux si le chemin est interdit pour « * ». Pas de robots.txt lisible = permis.
    $u = [uri]$url; $h = $u.Host
    if (-not $script:TrainRobots.ContainsKey($h)) {
        $r = Invoke-TrainHttp "https://$h/robots.txt"; $regles = @()
        if ($r.code -eq 200) {
            $groupe = $false
            foreach ($l in ($r.texte -split "`r?`n")) {
                $l = ($l -replace '#.*$', '').Trim()
                if ($l -match '^(?i)user-agent\s*:\s*(.+)$') { $groupe = ($Matches[1].Trim() -eq '*') }
                elseif ($groupe -and $l -match '^(?i)disallow\s*:\s*(\S+)$') { $regles += $Matches[1] }
            }
        }
        $script:TrainRobots[$h] = $regles
    }
    $chemin = $u.PathAndQuery
    foreach ($p in $script:TrainRobots[$h]) { $re = '^' + ([regex]::Escape($p) -replace '\\\*', '.*' -replace '\\\$$', '$'); if ($chemin -match $re) { return $false } }
    $true
}
function Get-TrainTexte([string]$url) {
    # Page publique : robots.txt respecté ; 403 / 429 / défi anti-robot = refus honnête (jamais de contournement).
    if (-not (Test-TrainRobots $url)) { throw "robots.txt interdit cette page ($(([uri]$url).Host))" }
    $r = Invoke-TrainHttp $url
    if ($r.code -eq 200 -and $r.texte -notmatch '(?i)just a moment|cf-challenge|captcha') { return $r.texte }
    if ($r.code -in 403, 429 -or $r.texte -match '(?i)just a moment|captcha') { throw "accès refusé (HTTP $($r.code)) : protection anti-robot, source non exploitable" }
    throw "HTTP $($r.code) $(Short $r.texte 120)"
}

# ---------- Sources ----------
function Get-TrainSbb {
    $json = Get-TrainTexte 'https://company.sbb.ch/content/internet/corporate/en/jobs-karriere/jobs/job-suche/jcr:content/parmain/jobfilter.results.json'
    $o = $json | ConvertFrom-Json; $out = @()
    foreach ($j in @($o)) {
        if (-not (Test-TrainAnnonce "$($j.title)")) { continue }
        $lieu = $(if ($j.attributes.'100') { @($j.attributes.'100') -join ', ' } else { '' })
        $d = ''; if ("$($j.start_date)" -match '^\d{4}-\d{2}-\d{2}') { $d = $Matches[0] }
        $f = Get-TrainFiltreSuisse $lieu "$($j.title)"; if (-not $f.garde) { Add-TrainEcart $f.raison; continue }
        $a = New-TrainAnnonce 'sbb' "$($j.id)" "$($j.title)" 'CFF / SBB' $lieu $d "$($j.links.directlink)"
        if ($f.allemand) { $a.langue = 'Allemand probable (titre en allemand)' }
        $out += $a
    }
    $out
}
function Get-TrainFranceTravail {
    $id = Get-EnvPropre 'FRANCETRAVAIL_ID'; $sec = Get-EnvPropre 'FRANCETRAVAIL_SECRET'
    if (-not $id -or -not $sec) { return $null }      # non configurée : source ignorée (ni erreur ni alerte)
    foreach ($s in @($id, $sec)) { if ($script:Secrets -notcontains $s) { $script:Secrets += $s } }
    $e = { param($x) [uri]::EscapeDataString($x) }
    $t = Invoke-TrainHttp 'https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=%2Fpartenaire' 'POST' ("grant_type=client_credentials&client_id=$(& $e $id)&client_secret=$(& $e $sec)&scope=" + (& $e 'api_offresdemploiv2 o2dsoffre'))
    if ($t.code -ne 200) { throw "jeton refusé (HTTP $($t.code)) : vérifiez FRANCETRAVAIL_ID / FRANCETRAVAIL_SECRET et l'abonnement à l'API Offres d'emploi" }
    $tok = ($t.texte | ConvertFrom-Json).access_token; if ($script:Secrets -notcontains $tok) { $script:Secrets += $tok }
    $out = @(); $vus = @{}
    foreach ($region in '28', '11') {      # 28 = Normandie, 11 = Île-de-France
        foreach ($mot in 'conducteur de train', 'conducteur de ligne', 'agent de conduite', 'formation conducteur', 'conducteur de metro', 'conducteur RER') {
            $r = Invoke-TrainHttp ("https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search?motsCles=$(& $e $mot)&region=$region&range=0-49&sort=1") 'GET' '' @{ Authorization = "Bearer $tok"; Accept = 'application/json' }
            if ($r.code -eq 204) { continue }
            if ($r.code -ne 200) { throw "recherche refusée (HTTP $($r.code)) $(Short (Hide-Secrets $r.texte) 100)" }
            foreach ($o in @(($r.texte | ConvertFrom-Json).resultats)) {
                if (-not (Test-TrainAnnonce "$($o.intitule)") -or $vus.ContainsKey("$($o.id)")) { continue }
                $vus["$($o.id)"] = $true
                $lien = "$($o.origineOffre.urlOrigine)"; if ($lien -notmatch '^https://') { $lien = "https://candidat.francetravail.fr/offres/recherche/detail/$($o.id)" }
                $d = ''; if ("$($o.dateCreation)" -match '^\d{4}-\d{2}-\d{2}') { $d = $Matches[0] }
                $out += New-TrainAnnonce 'ft' "$($o.id)" "$($o.intitule)" "$($o.entreprise.nom)" "$($o.lieuTravail.libelle)" $d $lien
            }
        }
    }
    $out
}
function Get-TrainPage([string]$cle, [string]$url, [string]$employeur) {
    # Page HTML publique : les LIENS dont le texte parle de conduite de train (aucune autre extraction).
    $html = Get-TrainTexte $url; $out = @()
    foreach ($m in [regex]::Matches($html, '(?is)<a\s[^>]*href="([^"]+)"[^>]*>(.*?)</a>')) {
        $txt = ([Net.WebUtility]::HtmlDecode(($m.Groups[2].Value -replace '<[^>]+>', ' ')) -replace '\s+', ' ').Trim()
        if (-not $txt -or -not (Test-TrainAnnonce $txt)) { continue }
        if (Test-TrainAllemand $txt) { Add-TrainEcart 'langue'; continue }      # lieu inconnu : un titre allemand est écarté
        $lien = ''; try { $lien = ([uri]::new([uri]$url, [Net.WebUtility]::HtmlDecode($m.Groups[1].Value))).AbsoluteUri } catch {}
        $out += New-TrainAnnonce $cle $lien $txt $employeur 'Suisse' '' $lien
    }
    $out
}
function Get-TrainSources {
    @(@{ nom = 'CFF / SBB'; f = { Get-TrainSbb } }, @{ nom = 'France Travail'; f = { Get-TrainFranceTravail } })
}

# ---------- Base locale ----------
function Get-TrainEtat {
    $o = Read-JsonMemoire 'veille-train.json'; $e = @{ vus = @(); nouvelles = @(); dernier_passage = ''; dernier_lancement = ''; dernier_resume = ''; erreurs = @{}; pid = 0 }
    if ($o) {
        foreach ($k in 'dernier_passage', 'dernier_lancement', 'dernier_resume') { if ($o.PSObject.Properties[$k]) { $e[$k] = "$($o.$k)" } }
        if ($o.PSObject.Properties['pid'] -and "$($o.pid)" -match '^\d+$') { $e.pid = [int]$o.pid }
        if ($o.PSObject.Properties['vus']) { $e.vus = @($o.vus | ForEach-Object { "$_" }) }
        if ($o.PSObject.Properties['nouvelles']) { $e.nouvelles = @($o.nouvelles | ForEach-Object { $h = @{}; foreach ($p in $_.PSObject.Properties) { $h[$p.Name] = "$($p.Value)" }; $h }) }
        if ($o.PSObject.Properties['erreurs'] -and $o.erreurs) { foreach ($p in $o.erreurs.PSObject.Properties) { $e.erreurs[$p.Name] = "$($p.Value)" } }
    }
    $e
}
function Save-TrainEtat($e) {
    $e.vus = @($e.vus | Select-Object -Last $script:TrainMaxVus)
    Save-JsonMemoire 'veille-train.json' ([ordered]@{ dernier_passage = $e.dernier_passage; dernier_lancement = $e.dernier_lancement; dernier_resume = $e.dernier_resume; pid = $e.pid; erreurs = $e.erreurs; vus = @($e.vus); nouvelles = @($e.nouvelles) })
}

# ---------- Cartes Discord (ton « info » : bleu ; « attention » : orange) ----------
# ---------- Traduction du titre allemand (Ollama local déjà lancé ; jamais Claude, Ollama n'est jamais démarré ici) ----------
function Get-TrainOllama {
    $o = $null; if ($Config -and $Config.PSObject.Properties['ollama']) { $o = $Config.ollama }
    $url = $(if ($o -and $o.url) { "$($o.url)".TrimEnd('/') } else { 'http://127.0.0.1:11434' })
    if ($url -notmatch '^http://(127\.0\.0\.1|localhost):\d{2,5}$') { return $null }      # service local seulement
    $keep = $(if ($o -and $o.PSObject.Properties['keep_alive'] -and "$($o.keep_alive)" -match '^\d+[smhd]$') { "$($o.keep_alive)" } elseif ($Config -and $Config.PSObject.Properties['ollama_toujours_chaud'] -and $Config.ollama_toujours_chaud -eq $true) { '24h' } else { '5m' })      # ne raccourcit pas le « chaud » du PC principal
    @{ url = $url; modele = $(if ($o -and $o.modele) { "$($o.modele)" } else { 'qwen2.5:7b' }); keep = $keep }
}
function Invoke-TrainTraduction([string]$titre) {
    # Titre traduit en français, ou '' si Ollama est absent, trop lent ou répond n'importe quoi : la carte garde alors le titre original, sans erreur.
    if ($script:TrainTraductionStub) { return [string](& $script:TrainTraductionStub $titre) }
    if ($script:TrainOllamaHS) { return '' }
    $c = Get-TrainOllama; if (-not $c) { return '' }
    try {
        $corps = @{ model = $c.modele; stream = $false; keep_alive = $c.keep; options = @{ temperature = 0; num_predict = 60 }; messages = @(
            @{ role = 'system'; content = "Tu traduis des titres d'offres d'emploi ferroviaires de l'allemand vers le français. Réponds uniquement par la traduction, courte, sur une seule ligne, sans guillemets ni explication. Ne traduis pas les noms de lieux ni d'entreprises." },
            @{ role = 'user'; content = $titre }) } | ConvertTo-Json -Depth 6 -Compress
        $w = Invoke-WebRequest -Uri "$($c.url)/api/chat" -Method Post -Body ([Text.Encoding]::UTF8.GetBytes($corps)) -ContentType 'application/json; charset=utf-8' -TimeoutSec 60 -UseBasicParsing
        $ms = New-Object IO.MemoryStream; $w.RawContentStream.CopyTo($ms); $r = [Text.Encoding]::UTF8.GetString($ms.ToArray()) | ConvertFrom-Json
        $t = (("$($r.message.content)" -split "`r?`n" | Where-Object { $_.Trim() } | Select-Object -First 1) -replace '^[\s"«»''“”]+|[\s"«»''“”]+$', '').Trim()
        if ($t.Length -ge 3 -and $t.Length -le 160 -and $t -ne $titre) { return $t }
        ''
    } catch { $script:TrainOllamaHS = $true; '' }      # Ollama éteint ou trop lent : plus d'essai pendant ce passage
}
function Get-TrainTraduction($a) {
    # Seulement pour un titre allemand ; résultat gardé dans memoire\traductions-train.json (300 titres au plus) pour ne jamais retraduire la même annonce.
    if (-not (Test-TrainAllemand "$($a.titre)")) { return '' }
    $h = [ordered]@{}; $cache = Read-JsonMemoire 'traductions-train.json'
    if ($cache) { foreach ($p in $cache.PSObject.Properties) { $h[$p.Name] = $p.Value } }
    $k = "$($a.id)"
    if ($h.Contains($k) -and "$($h[$k].titre)" -eq "$($a.titre)" -and "$($h[$k].fr)") { return "$($h[$k].fr)" }
    $fr = Invoke-TrainTraduction "$($a.titre)"; if (-not $fr) { return '' }
    $h[$k] = [ordered]@{ titre = "$($a.titre)"; fr = $fr }
    $cles = @($h.Keys); if ($cles.Count -gt 300) { foreach ($x in $cles[0..($cles.Count - 301)]) { $h.Remove($x) } }
    Save-JsonMemoire 'traductions-train.json' $h
    $fr
}
function New-EmbedTrainAnnonce($a) {
    $champs = @(@{ nom = 'Employeur'; valeur = $a.employeur; inline = $true }, @{ nom = 'Lieu'; valeur = $a.lieu; inline = $true }, @{ nom = 'Type'; valeur = $a.type; inline = $true },
        @{ nom = $(if ($a.date) { 'Date' } else { 'Repérée le' }); valeur = $(if ($a.date) { ([datetime]$a.date).ToString('dd/MM/yyyy') } else { (Get-Date).ToString('dd/MM/yyyy') }); inline = $true })
    if ($a.langue) { $champs += @{ nom = 'Langue'; valeur = $a.langue; inline = $true } }
    if ($a.lien) { $champs += @{ nom = 'Lien'; valeur = $a.lien; inline = $false } }
    $fr = $(if ($a -is [hashtable]) { $a['titre_fr'] } else { $a.titre_fr })
    $desc = "Nouvelle annonce de conduite de train ($($a.type.ToLower()))."
    if ($fr) { $desc += "`n-# Titre original : $($a.titre) · traduit automatiquement" }      # petit texte Discord sous le titre traduit
    New-EmbedDiscord $(if ($fr) { $fr } else { $a.titre }) $desc $script:CouleurBleue $champs (Get-PiedDiscord 'annonces-train')
}
function New-EmbedTrainResume($nouvelles, $sourcesMuettes = @()) {
    $n = @($nouvelles); $desc = $(if ($n.Count) { "$($n.Count) nouvelle$(if ($n.Count -gt 1) { 's' }) annonce$(if ($n.Count -gt 1) { 's' }) depuis hier." } else { 'Aucune nouvelle annonce depuis hier.' })
    $champs = @(); if ($n.Count) { $champs += @{ nom = 'Annonces'; valeur = (@($n | Select-Object -First 10 | ForEach-Object { "• $(if ($_.titre_fr) { $_.titre_fr } else { $_.titre }) · $($_.employeur) · $($_.lieu)" }) -join "`n"); inline = $false } }
    if (@($sourcesMuettes).Count) { $champs += @{ nom = 'Sources en panne'; valeur = (@($sourcesMuettes) -join ', '); inline = $false } }
    New-EmbedDiscord 'Annonces conducteur de train · résumé du matin' $desc $script:CouleurBleue $champs (Get-PiedDiscord 'annonces-train')
}
function New-EmbedTrainAttention([string]$source, [string]$raison) {
    New-EmbedDiscord 'Attention : veille des annonces de train' "La source « $source » ne répond pas correctement. Je continue avec les autres et je ne vous le redirai pas avant demain.`n`nQue faire : rien d'urgent ; si cela dure, dites-le-moi." $script:CouleurOrange @(@{ nom = 'Raison'; valeur = $raison; inline = $false }) (Get-PiedDiscord 'annonces-train')
}
function Send-TrainNotif([string]$salon, $embed) {
    # Vrai si Discord a accepté la carte. Même mécanisme que l'agent de dev (notifier.py, REST direct, sans mention).
    if ($script:TrainNotifStub) { return [bool](& $script:TrainNotifStub $salon $embed) }
    $salon = 'annonces-train'      # toutes les cartes de la veille (annonces, résumé, alertes) vont dans ce salon ; non réglé = repli de notifier.py sur « jarvis »
    $tmp = Join-Path $env:TEMP ('jarvis-train-' + [guid]::NewGuid().ToString('N').Substring(0, 8) + '.json'); $encPrec = $null
    try {
        try { $encPrec = [Console]::OutputEncoding; [Console]::OutputEncoding = [Text.Encoding]::UTF8 } catch {}      # notifier.py écrit en UTF-8 : sans cela « envoyé » devient « envoyÚ »
        [IO.File]::WriteAllText($tmp, ($embed | ConvertTo-Json -Depth 6), [Text.UTF8Encoding]::new($false))
        $o = (& python -I (Join-Path $script:RacineReelle 'pont-discord\notifier.py') --racine $script:RacineReelle --salon $salon --embed $tmp 2>&1 | Out-String).Trim()
        Write-Journal -Action 'Veille annonces-train : Discord' -Resultat (Short (Hide-Secrets $o) 120)
        $o -match '^ok'
    } catch { $false } finally { if ($encPrec) { try { [Console]::OutputEncoding = $encPrec } catch {} }; Remove-Item $tmp -Force -ErrorAction SilentlyContinue }
}

# ---------- Un passage ----------
function Invoke-VeilleTrain([datetime]$now = (Get-Date)) {
    # Retourne @{ nouvelles; envoyees; erreurs; resume }. Une source en erreur n'arrête pas les autres.
    $e = Get-TrainEtat; $c = Get-TrainConfig; $jour = $now.ToString('yyyy-MM-dd')
    $e.pid = $PID; $e.dernier_lancement = $now.ToString('o'); Save-TrainEtat $e
    $trouvees = @(); $erreurs = @(); $muettes = @(); $script:TrainEcart = @{ lieu = 0; langue = 0 }; $script:TrainOllamaHS = $false
    foreach ($s in Get-TrainSources) {
        try {
            $r = & $s.f
            if ($null -eq $r) { continue }
            $trouvees += @($r)
        } catch {
            $raison = Short (Hide-Secrets $_.Exception.Message) 200; $erreurs += $s.nom; $muettes += $s.nom
            Write-Journal -Action 'Veille annonces-train' -Resultat "$($s.nom) : $raison"
            if ($e.erreurs["$($s.nom)"] -ne $jour) { if (Send-TrainNotif 'systeme' (New-EmbedTrainAttention $s.nom $raison)) { $e.erreurs["$($s.nom)"] = $jour } }      # une carte par source et par jour
        }
    }
    $nouvelles = @($trouvees | Where-Object { $e.vus -notcontains $_.id } | Sort-Object { $_.id } -Unique)
    $envoyees = 0; $n = 0
    foreach ($a in $nouvelles) {
        $n++
        if ($n -gt $script:TrainMaxCartes) { break }
        try { $fr = Get-TrainTraduction $a; if ($fr) { $a.titre_fr = $fr } } catch {}      # jamais d'erreur : sans traduction, titre original
        if (Send-TrainNotif 'jarvis' (New-EmbedTrainAnnonce $a)) { $envoyees++; $e.vus += $a.id; $a.vu_le = $now.ToString('o'); $e.nouvelles += $a }
    }
    $reste = @($nouvelles | Select-Object -Skip $script:TrainMaxCartes)
    if ($reste.Count) {      # trop d'annonces d'un coup (premier passage) : une seule carte pour le reste, pas de rafale
        $emb = New-EmbedDiscord "$($reste.Count) autres nouvelles annonces" 'Pour ne pas vous noyer, voici les titres ; les liens sont dans les sources officielles.' $script:CouleurBleue @(@{ nom = 'Annonces'; valeur = (@($reste | Select-Object -First 12 | ForEach-Object { "• $($_.titre) · $($_.employeur) · $($_.lieu)" + $(if ($_.lien) { " · $($_.lien)" } else { '' }) }) -join "`n"); inline = $false }) (Get-PiedDiscord 'annonces-train')
        if (Send-TrainNotif 'jarvis' $emb) { foreach ($a in $reste) { $e.vus += $a.id; $a.vu_le = $now.ToString('o'); $e.nouvelles += $a } }
    }
    $e.nouvelles = @($e.nouvelles | Where-Object { try { ($now - [datetime]$_.vu_le).TotalDays -lt 7 } catch { $false } })
    $resume = $false
    if ($now.ToString('HH:mm') -ge $c.resume -and $e.dernier_resume -ne $jour) {      # résumé quotidien du matin (rattrapage : au premier passage après l'heure)
        $veille = @($e.nouvelles | Where-Object { try { ($now - [datetime]$_.vu_le).TotalHours -lt 24 -and ($_.source -ne 'sbb' -or (Get-TrainFiltreSuisse $_.lieu $_.titre).garde) } catch { $false } })      # anciennes alémaniques déjà vues : jamais dans le résumé
        if (Send-TrainNotif 'jarvis' (New-EmbedTrainResume $veille $muettes)) { $e.dernier_resume = $jour; $resume = $true }
    }
    $e.dernier_passage = $now.ToString('o'); $e.pid = 0; Save-TrainEtat $e
    $ecL = [int]$script:TrainEcart.lieu; $ecG = [int]$script:TrainEcart.langue
    Write-Journal -Action 'Veille annonces-train' -Resultat "$($trouvees.Count + $ecL + $ecG) annonce(s) de conduite vue(s) : $($trouvees.Count) gardée(s), $($ecL + $ecG) écartée(s) par le filtre Suisse romande (lieu $ecL, langue $ecG) ; $($nouvelles.Count) nouvelle(s), $envoyees carte(s)$(if ($erreurs.Count) { ', sources en erreur : ' + ($erreurs -join ', ') })"
    @{ nouvelles = $nouvelles.Count; envoyees = $envoyees; erreurs = $erreurs; resume = $resume }
}

# ---------- Boucle de Jarvis (légère : aucun réseau ici) ----------
function Test-TrainProcessusVivant([int]$procId) { if ($procId -le 0) { return $false }; try { $p = Get-CimInstance Win32_Process -Filter "ProcessId=$procId" -ErrorAction SilentlyContinue; [bool]($p -and $p.CommandLine -match 'veille-train\.ps1') } catch { $false } }
function Update-VeilleTrain([datetime]$now = (Get-Date)) {
    # Ne fait RIEN si veille_train n'est pas "oui". Lance un passage si le dernier date de plus d'une heure (donc aussi au démarrage : rattrapage). Jamais en mode jeu.
    $c = Get-TrainConfig; if (-not $c.actif) { return $false }
    if ($now -lt $script:TrainProchainTour) { return $false }; $script:TrainProchainTour = $now.AddSeconds(60)
    if ($script:ModeJeu -eq $true) { return $false }
    $e = Get-TrainEtat; if (Test-TrainProcessusVivant $e.pid) { return $false }
    foreach ($k in @(@('dernier_passage', $c.minutes), @('dernier_lancement', 10))) { $d = [datetime]::MinValue; if ([datetime]::TryParse($e[$k[0]], [Globalization.CultureInfo]::InvariantCulture, [Globalization.DateTimeStyles]::RoundtripKind, [ref]$d) -and ($now - $d).TotalMinutes -lt $k[1]) { return $false } }
    if (Test-ModeTest) { $script:TrainRunnerLance = $true; return $true }
    $s = Join-Path $script:RacineReelle 'veille-train.ps1'; if (-not (Test-Path $s)) { return $false }
    $e.dernier_lancement = $now.ToString('o'); Save-TrainEtat $e
    try { [void](Start-Process powershell -ArgumentList '-NoProfile', '-ExecutionPolicy', 'Bypass', '-WindowStyle', 'Hidden', '-File', "`"$s`"" -WindowStyle Hidden -PassThru); $true } catch { Write-Journal -Action 'Veille annonces-train' -Resultat 'lancement impossible'; $false }
}
