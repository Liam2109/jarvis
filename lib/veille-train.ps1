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
# Offres pour DÉBUTANT : on écarte « déjà formé », expérimenté / confirmé, formateur / instructeur, « avec expérience » (« sans expérience » reste permis). Texte normalisé sans accents.
$script:TrainExclu = '\b(deja forme(?:e|s|es)?|forme(?:e|s|es)?|experimente(?:e|s|es)?|confirme(?:e|s|es)?|formateurs?|formatrices?|instructeurs?|instructrices?|moniteurs?|monitrices?|tuteurs?|tutrices?|seniors?|avec experience|experience (?:requise|exigee|confirmee|souhaitee|prealable)|erfahren\w*|berufserfahren\w*|ausbilder(?:in)?|instruktor(?:in)?)\b'
function Test-TrainExclu([string]$titre) { (ConvertTo-TrainNorm $titre) -match $script:TrainExclu }
# Tramway : jamais (Transdev, RATP...). Test-TrainTram ne vaut que pour un titre de CONDUITE (pour compter l'écart sans compter les autres métiers).
$script:TrainTram = '\b(tram|tramway|tramways|tram train)\b'
function Test-TrainTram([string]$titre) { $n = ConvertTo-TrainNorm $titre; ($n -match $script:TrainTram) -and ($n -match $script:TrainMotif) }
# Employeurs acceptés (liste de Liam). Un employeur CONNU hors liste est écarté ; un employeur inconnu ou vide (agence, annonce anonyme, site d'emploi) est gardé.
$script:TrainEmployeursOk = '\b(sncf|transilien|ter|ratp|keolis|transdev|rail logistics|rle|fret|europorte|captrain|lineas|eurocargo|regiorail|hexafret|cff|sbb|ffs)\b'
function Test-TrainEmployeurOk([string]$emp) { $n = ConvertTo-TrainNorm ("$emp" -replace '\(alerte e-mail\)', ''); if (-not $n -or $n -match 'non precise|^(indeed|jobup|jobscout24|jobscout|france travail|alerte e mail)$') { return $true }; $n -match $script:TrainEmployeursOk }
# Critères à VÉRIFIER (profil : 18 ans, bac général, BTS SIO interrompu, pas de bac+2) : l'annonce est GARDÉE mais marquée, jamais écartée en silence.
function Get-TrainCritereVerifier([string]$texte) {
    $n = ConvertTo-TrainNorm $texte; $r = @()
    if ($n -match '\bbac (?:2|3|4|5)\b|\bbts\b|\bdut\b|\bniveau (?:5|6|iii|ii)\b|\blicence\b|\bdiplome de niveau (?:5|6)\b') { $r += 'Bac+2 (ou diplôme supérieur) demandé' }
    if ($n -match '\b(?:21|22|23|25) ans (?:minimum|revolus|ou plus|au moins)|(?:au moins|minimum|a partir de|plus de|age minimum|age de|ages? de) (?:de )?(?:21|22|23|25) ans') { $r += 'Âge minimum de 21 ans ou plus' }
    $r -join ' ; '
}
$script:TrainEcartCles = @('lieu', 'langue', 'tram', 'employeur', 'experience')
function Get-TrainEcartTexte($h, [switch]$Tout) {
    $noms = [ordered]@{ lieu = 'hors zone'; langue = 'allemand'; tram = 'tramway'; employeur = 'autre employeur'; experience = 'expérience exigée' }; $p = @()
    foreach ($k in $noms.Keys) { $n = $(if ($h) { [int]$h[$k] } else { 0 }); if ($n -or $Tout) { $p += "$($noms[$k]) $n" } }
    $p -join ', '
}
function Add-TrainEcartsEtat($e) {
    # Écarts cumulés depuis le dernier résumé du matin (affichés dans la carte du résumé, puis remis à zéro).
    $old = $e.ecarts; $h = @{}; foreach ($k in $script:TrainEcartCles) { $h[$k] = $(if ($old) { [int]$old[$k] } else { 0 }) + [int]$script:TrainEcart[$k] }; $e.ecarts = $h
}
function Get-TrainProp($a, [string]$k) { if ($a -is [hashtable]) { "$($a[$k])" } else { "$($a.$k)" } }
function Get-TrainZoneLibelle([string]$z) { switch ($z) { '1' { 'Priorité 1 (Île-de-France / Rouen)' } '2' { 'Priorité 2 (Caen / Le Havre)' } '3' { 'Priorité 3 (Lens)' } '4' { 'Dernier recours (Le Mans)' } default { '' } } }
function Test-TrainAnnonce([string]$titre) { $n = ConvertTo-TrainNorm $titre; ($n -match $script:TrainMotif) -and ($n -notmatch '\b(bus|autocar|autobus)\b') -and ($n -notmatch $script:TrainTram) -and ($n -notmatch $script:TrainExclu) }
function Get-TrainType([string]$titre) { if ((ConvertTo-TrainNorm $titre) -match 'formation|quereinstieg|zweitausbildung|reconversion|alternance|apprenti|lehre|diplome|stage') { 'Formation' } else { 'Emploi' } }
function New-TrainAnnonce([string]$source, [string]$ident, [string]$titre, [string]$employeur, [string]$lieu, [string]$date, [string]$lien) {
    if ($lien -notmatch '^https://') { $lien = '' }
    @{ id = "${source}:$ident"; source = $source; titre = "$titre".Trim(); employeur = $(if ("$employeur".Trim()) { "$employeur".Trim() } else { 'non précisé' }); lieu = $(if ("$lieu".Trim()) { "$lieu".Trim() } else { 'non précisé' }); date = "$date"; lien = $lien; type = (Get-TrainType $titre) }
}

# ---------- Filtre « francophone en Suisse romande » (sources suisses seulement) ----------
# Lieu : liste blanche = Suisse romande (Vaud, Genève, Valais, Neuchâtel, Jura, Fribourg, Bienne...) + Suisse alémanique proche (Bâle, Soleure, Berne, Argovie). Tout le reste (Zurich et l'est du pays, Suisse centrale, lieu inconnu) est écarté.
# Langue : les offres EN ALLEMAND sont ÉCARTÉES (comptées « langue »), partout ; seules les offres en français de Suisse romande sont gardées (Fribourg et Bienne, bilingues, comprises). Bâle, Berne, Argovie... ne sont plus acceptées.
$script:TrainRomand = '\b(lausanne|geneve|geneva|genf|vaud|yverdon|vevey|montreux|renens|morges|nyon|sion|sierre|siders|martigny|monthey|aigle|bex|delemont|la chaux de fonds|neuchatel|neuenburg|le locle|jura|porrentruy|valais|bulle|payerne|vallorbe|palezieux|cossonay|gland|rolle|prilly|crissier|ecublens|pully|lutry|vernier|carouge|lancy|meyrin|versoix|romont|chexbres|puidoux|villeneuve|saint maurice|st maurice|fully|orbe|echallens|moudon|avenches|saint imier|tavannes|moutier|courtelary|travers|couvet|fleurier|les brenets|bussigny|denges|echandens|saint sulpice|st sulpice|chavannes|penthalaz|daillens|sullens|lonay|etoy|allaman|aubonne|epalinges|cully|paudex|bremblens|romanel|vufflens|bercher|grandson|sainte croix|ste croix|la sarraz|chavornay|lucens|oron|chatel saint denis|chatel st denis|vuadens|estavayer|marly|givisiez|villars sur glane|vouvry|collombey|saxon|riddes|conthey|vetroz|evionnaz|cornavin|onex|thonex|chene bourg|satigny|bernex|plan les ouates|cointrin|coppet|boudry|colombier|peseux|cornaux|saint blaise|val de ruz|cernier|fontainemelon|courrendlin|glovelier|bassecourt|saignelegier|reconvilier|malleray|bevilard|sonceboz|la neuveville)\b'
$script:TrainBilingue = '\b(fribourg|freiburg|biel|bienne|murten|morat)\b'
$script:TrainProche = '\b(basel|bale|baselland|basel land|liestal|muttenz|pratteln|allschwil|binningen|arlesheim|sissach|birsfelden|munchenstein|riehen|laufon|solothurn|soleure|olten|grenchen|granges|oensingen|dulliken|balsthal|hagendorf|schonenwerd|zuchwil|biberist|gerlafingen|dornach|breitenbach|bern|berne|jura bernois|burgdorf|langenthal|lyss|thun|interlaken|koniz|ostermundigen|worb|munsingen|aargau|argovie|aarau|baden|brugg|lenzburg|wohlen|zofingen|rheinfelden|oftringen|suhr|wettingen|spreitenbach|windisch|rupperswil|mellingen|beinwil am see|brig|brigue|visp|viege|naters|zermatt|raron|leuk)\b'
$script:TrainMotifAllemand = 'lokfuhrer|lokfuehrer|triebfahrzeug|quereinstieg|zweitausbildung|rangier|zugmaschine|bauzug|fahrleitung|personenverkehr|guterverkehr|kategorie|\bkat\b|\bund\b|\bmit\b|erfahrung|ausbildung'
function Test-TrainAllemand([string]$titre) { $n = ConvertTo-TrainNorm $titre; ($n -match $script:TrainMotifAllemand) -and ($n -notmatch 'conduct(?:eur|rice)|mecanicien|agent de conduite') }
function Get-TrainFiltreSuisse([string]$lieu, [string]$titre) {
    # @{ garde; allemand; raison } : garde = lieu romand ou bilingue ET titre non allemand ; raison = 'lieu' (hors Suisse romande) ou 'langue' (titre allemand) si écartée.
    $l = ConvertTo-TrainNorm $lieu; $lieuOk = ($l -match $script:TrainRomand) -or ($l -match $script:TrainBilingue); $de = Test-TrainAllemand $titre
    @{ garde = ($lieuOk -and -not $de); allemand = $de; raison = $(if (-not $lieuOk) { 'lieu' } elseif ($de) { 'langue' } else { '' }) }
}
# Île-de-France (SNCF Voyageurs Île-de-France, Transilien) : même principe
$script:TrainIdf = '\b(paris|ile de france|saint lazare|montparnasse|gare du nord|gare de l est|gare de lyon|austerlitz|versailles|saint quentin en yvelines|massy|juvisy|melun|cergy|pontoise|mantes la jolie|creteil|saint denis|bobigny|nanterre|la defense|argenteuil|noisy le sec|marne la vallee|torcy|meaux|provins|rambouillet|evry|corbeil essonnes|etampes|orly|villeneuve saint georges|trappes|plaisir|acheres|poissy|conflans sainte honorine|sartrouville|ermont|pantin|bondy|aulnay sous bois|rosny sous bois|le bourget|chelles|lagny|mitry|roissy|vaires)\b'
# Zones acceptées par priorité : 1 = Île-de-France + Rouen, 2 = Caen + Le Havre, 3 = Lens, 4 = Le Mans (dernier recours). Lille et le reste : écartés.
$script:TrainZoneRouen = '\b(rouen|sotteville|quevilly|petit quevilly|grand quevilly|elbeuf|mont saint aignan|darnetal|oissel|barentin|saint etienne du rouvray|canteleu|maromme|deville les rouen|bois guillaume)\b'
$script:TrainZoneCaenHavre = '\b(caen|herouville saint clair|mondeville|ifs|ouistreham|le havre|harfleur|montivilliers|gonfreville|sainte adresse)\b'
$script:TrainZoneLens = '\b(lens|livin|avion|henin beaumont|mericourt|billy montigny|harnes|loos en gohelle|sallaumines|noyelles godault)\b'
$script:TrainZoneLeMans = '\b(le mans|allonnes|arnage|ruaudin|coulaines)\b'
function Get-TrainFiltreMail([string]$lieu, [string]$titre) {
    # @{ garde; allemand; raison ('lieu' | 'langue' | ''); zone (1 à 4, 0 = Suisse) }. Zones de France par priorité (voir TrainZone*) ; sinon Suisse romande, en français. Un titre allemand est écarté partout.
    $l = ConvertTo-TrainNorm $lieu; $z = 0
    if ($l -match $script:TrainIdf -or "$lieu" -match '^\s*(75|77|78|91|92|93|94|95)\s*-' -or $l -match $script:TrainZoneRouen) { $z = 1 }
    elseif ($l -match $script:TrainZoneCaenHavre) { $z = 2 } elseif ($l -match $script:TrainZoneLens) { $z = 3 } elseif ($l -match $script:TrainZoneLeMans) { $z = 4 }
    if ($z) { $de = Test-TrainAllemand $titre; return @{ garde = (-not $de); allemand = $de; raison = $(if ($de) { 'langue' } else { '' }); zone = $z } }
    $f = Get-TrainFiltreSuisse $lieu $titre; $f.zone = 0; $f
}
function Add-TrainEcart([string]$raison) { if (-not $script:TrainEcart) { $script:TrainEcart = @{ lieu = 0; langue = 0 } }; if (-not $script:TrainEcart.ContainsKey($raison)) { $script:TrainEcart[$raison] = 0 }; $script:TrainEcart[$raison]++ }

# ---------- Réseau poli (bouchon en test) ----------
function Wait-TrainPoli { if ($script:TrainPauseSec -gt 0) { $r = $script:TrainPauseSec - ((Get-Date) - $script:TrainDernierReq).TotalSeconds; if ($r -gt 0) { Start-Sleep -Milliseconds ([int]($r * 1000)) } }; $script:TrainDernierReq = Get-Date }
function Invoke-TrainHttp([string]$url, [string]$methode = 'GET', [string]$corps = '', [hashtable]$entetes = @{}, [int]$timeoutSec = 30) {
    # @{ code; texte } ; code 0 = erreur réseau (texte = raison). Jamais d'exception.
    $script:TrainDernierTimeout = $timeoutSec      # (lu par les tests)
    if ($script:TrainHttpStub) { return (& $script:TrainHttpStub $url $methode $corps $entetes) }
    Wait-TrainPoli
    try {
        $a = @{ Uri = $url; Method = $methode; UseBasicParsing = $true; TimeoutSec = $timeoutSec; Headers = (@{ 'User-Agent' = $script:TrainUA; 'Accept-Language' = 'fr,de;q=0.8' } + $entetes) }
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
        if (Test-TrainTram "$($j.title)") { Add-TrainEcart 'tram'; continue }
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
    foreach ($region in '28', '11', '32', '52') {      # 28 = Normandie (Rouen, Caen, Le Havre), 11 = Île-de-France, 32 = Hauts-de-France (Lens), 52 = Pays de la Loire (Le Mans)
        foreach ($mot in 'conducteur de train', 'conducteur de ligne', 'agent de conduite', 'formation conducteur', 'conducteur de metro', 'conducteur RER', 'conducteur de train debutant') {
            $r = Invoke-TrainHttp ("https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search?motsCles=$(& $e $mot)&region=$region&range=0-49&sort=1") 'GET' '' @{ Authorization = "Bearer $tok"; Accept = 'application/json' }
            if ($r.code -eq 204) { continue }
            if ($r.code -ne 200) { throw "recherche refusée (HTTP $($r.code)) $(Short (Hide-Secrets $r.texte) 100)" }
            foreach ($o in @(($r.texte | ConvertFrom-Json).resultats)) {
                if ($vus.ContainsKey("$($o.id)")) { continue }; $vus["$($o.id)"] = $true
                if (Test-TrainTram "$($o.intitule)") { Add-TrainEcart 'tram'; continue }
                if (-not (Test-TrainAnnonce "$($o.intitule)")) { continue }
                $f = Get-TrainFiltreMail "$($o.lieuTravail.libelle)" "$($o.intitule)"; if (-not $f.garde) { Add-TrainEcart $f.raison; continue }      # zones de Liam (lib\veille-mail.ps1) ; titre allemand écarté
                if (-not (Test-TrainEmployeurOk "$($o.entreprise.nom)")) { Add-TrainEcart 'employeur'; continue }
                if ("$($o.experienceExige)" -eq 'E') { Add-TrainEcart 'experience'; continue }      # débutant accepté obligatoire
                $lien = "$($o.origineOffre.urlOrigine)"; if ($lien -notmatch '^https://') { $lien = "https://candidat.francetravail.fr/offres/recherche/detail/$($o.id)" }
                $d = ''; if ("$($o.dateCreation)" -match '^\d{4}-\d{2}-\d{2}') { $d = $Matches[0] }
                $n = New-TrainAnnonce 'ft' "$($o.id)" "$($o.intitule)" "$($o.entreprise.nom)" "$($o.lieuTravail.libelle)" $d $lien
                if ($f.zone) { $n.zone = "$($f.zone)" }
                $v = Get-TrainCritereVerifier ("$($o.intitule) $($o.description) $(@($o.formations | ForEach-Object { "$($_.niveauLibelle) $($_.domaineLibelle)" }) -join ' ') $($o.qualificationLibelle)"); if ($v) { $n.verifier = $v }
                $out += $n
            }
        }
    }
    $out
}
function Get-TrainPage([string]$cle, [string]$url, [string]$employeur, [string]$lieuPage = 'Suisse') {
    # Page HTML publique : les LIENS dont le texte parle de conduite de train (aucune autre extraction).
    $html = Get-TrainTexte $url; $out = @()
    foreach ($m in [regex]::Matches($html, '(?is)<a\s[^>]*href="([^"]+)"[^>]*>(.*?)</a>')) {
        $txt = ([Net.WebUtility]::HtmlDecode(($m.Groups[2].Value -replace '<[^>]+>', ' ')) -replace '\s+', ' ').Trim()
        if ($txt -and (Test-TrainTram $txt)) { Add-TrainEcart 'tram'; continue }
        if (-not $txt -or -not (Test-TrainAnnonce $txt)) { continue }
        if (Test-TrainAllemand $txt) { Add-TrainEcart 'langue'; continue }      # lieu inconnu : un titre allemand est écarté
        $lien = ''; try { $lien = ([uri]::new([uri]$url, [Net.WebUtility]::HtmlDecode($m.Groups[1].Value))).AbsoluteUri } catch {}
        $out += New-TrainAnnonce $cle $lien $txt $employeur $lieuPage '' $lien
    }
    $out
}
function Get-TrainPagesConfig {
    # Pages d'offres que VOUS déclarez dans config.json : "veille_offres_pages": [ { "nom": "Captrain", "url": "https://...", "employeur": "Captrain", "lieu": "Normandie" } ] (https seulement ; robots.txt respecté ; une page illisible = source en panne signalée une fois par jour).
    if (-not $Config.PSObject.Properties['veille_offres_pages']) { return @() }
    @(@($Config.veille_offres_pages) | Where-Object { $_ -and "$($_.url)" -match '^https://' -and "$($_.nom)".Trim() } | ForEach-Object {
        $p = $_; $emp = $(if ("$($p.employeur)".Trim()) { "$($p.employeur)".Trim() } else { "$($p.nom)".Trim() }); $lieu = $(if ("$($p.lieu)".Trim()) { "$($p.lieu)".Trim() } else { 'non précisé' })
        @{ nom = "$($p.nom)".Trim(); f = { Get-TrainPage ('page-' + (ConvertTo-TrainNorm $p.nom).Replace(' ', '-')) "$($p.url)" $emp $lieu }.GetNewClosure() }
    })
}
function Get-TrainSources {
    @(@{ nom = 'CFF / SBB'; f = { Get-TrainSbb } }, @{ nom = 'France Travail'; f = { Get-TrainFranceTravail } }) + @(Get-TrainPagesConfig)
}

# ---------- Base locale ----------
function Get-TrainEtat {
    $o = Read-JsonMemoire 'veille-train.json'; $e = @{ vus = @(); nouvelles = @(); dernier_passage = ''; dernier_lancement = ''; dernier_resume = ''; erreurs = @{}; pid = 0; ecarts = @{} }
    if ($o) {
        foreach ($k in 'dernier_passage', 'dernier_lancement', 'dernier_resume') { if ($o.PSObject.Properties[$k]) { $e[$k] = "$($o.$k)" } }
        if ($o.PSObject.Properties['pid'] -and "$($o.pid)" -match '^\d+$') { $e.pid = [int]$o.pid }
        if ($o.PSObject.Properties['vus']) { $e.vus = @($o.vus | ForEach-Object { "$_" }) }
        if ($o.PSObject.Properties['nouvelles']) { $e.nouvelles = @($o.nouvelles | ForEach-Object { $h = @{}; foreach ($p in $_.PSObject.Properties) { $h[$p.Name] = "$($p.Value)" }; $h }) }
        if ($o.PSObject.Properties['erreurs'] -and $o.erreurs) { foreach ($p in $o.erreurs.PSObject.Properties) { $e.erreurs[$p.Name] = "$($p.Value)" } }
        if ($o.PSObject.Properties['ecarts'] -and $o.ecarts) { foreach ($p in $o.ecarts.PSObject.Properties) { $e.ecarts[$p.Name] = "$($p.Value)" } }
    }
    $e
}
function Save-TrainEtat($e) {
    $e.vus = @($e.vus | Select-Object -Last $script:TrainMaxVus)
    Save-JsonMemoire 'veille-train.json' ([ordered]@{ dernier_passage = $e.dernier_passage; dernier_lancement = $e.dernier_lancement; dernier_resume = $e.dernier_resume; pid = $e.pid; erreurs = $e.erreurs; ecarts = $e.ecarts; vus = @($e.vus); nouvelles = @($e.nouvelles) })
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
    if (-not $script:TrainSansEcriture) { Save-JsonMemoire 'traductions-train.json' $h }      # (commande veille-mail-test en simulation : rien n'est écrit)
    $fr
}
function New-EmbedTrainAnnonce($a) {
    $champs = @(@{ nom = 'Employeur'; valeur = $a.employeur; inline = $true }, @{ nom = 'Lieu'; valeur = $a.lieu; inline = $true }, @{ nom = 'Type'; valeur = $a.type; inline = $true },
        @{ nom = $(if ($a.date) { 'Date' } else { 'Repérée le' }); valeur = $(if ($a.date) { ([datetime]$a.date).ToString('dd/MM/yyyy') } else { (Get-Date).ToString('dd/MM/yyyy') }); inline = $true })
    if ($a.langue) { $champs += @{ nom = 'Langue'; valeur = $a.langue; inline = $true } }
    $z = Get-TrainProp $a 'zone'; $v = Get-TrainProp $a 'verifier'
    if ($z) { $champs += @{ nom = 'Zone'; valeur = (Get-TrainZoneLibelle $z); inline = $true } }
    if ($v) { $champs += @{ nom = 'Critère à vérifier'; valeur = $v; inline = $true } }      # gardée, jamais écartée en silence
    if ($a.lien) { $champs += @{ nom = 'Lien'; valeur = $a.lien; inline = $false } }
    if (Get-Command Get-CandBrouillonChamp -ErrorAction SilentlyContinue) { $b = Get-CandBrouillonChamp $a; if ($b) { $champs += $b } }      # lib\candidatures.ps1 : lien « brouillon Gmail » (rien n'est envoyé)
    $fr =$(if ($a -is [hashtable]) { $a['titre_fr'] } else { $a.titre_fr })
    $desc = "Nouvelle annonce de conduite de train ($($a.type.ToLower()))."
    if ($fr) { $desc += "`n-# Titre original : $($a.titre) · traduit automatiquement" }      # petit texte Discord sous le titre traduit
    if ($z -eq '4') { $desc += "`n-# Dernier recours : zone Le Mans." }
    New-EmbedDiscord (Get-TrainTitreAffiche $a) $desc $(if ($v -or $z -eq '4') { $script:CouleurOrange } else { $script:CouleurBleue }) $champs (Get-PiedDiscord 'annonces-train')
}
function Get-TrainTitreAffiche($a) {
    # Titre traduit s'il existe, sinon l'original ; « [DE] » devant toute annonce en allemand.
    $de = [bool]"$($a.langue)" -or (Test-TrainAllemand "$($a.titre)"); $t = $(if ("$($a.titre_fr)") { "$($a.titre_fr)" } else { "$($a.titre)" })
    $(if ($de) { "[DE] $t" } else { $t })
}
function Get-TrainLigneAnnonce($a) {
    # Une ligne Discord : titre cliquable (lien de l'annonce) · employeur · lieu. Sans lien : titre simple.
    $t = (Get-TrainTitreAffiche $a) -replace '[\[\]]', ''
    $l = "$($a.lien)" -replace '\)', '%29' -replace '\s', '%20'
    $debut = $(if ($l -match '^https://') { "• [$t]($l)" } else { "• $t" })
    "$debut · $($a.employeur) · $($a.lieu)"
}
function Get-TrainChampsAnnonces($liste, [int]$max = 10, [string]$nom = 'Annonces') {
    # Plusieurs champs si besoin : Discord limite chaque champ à 1024 caractères (les liens longs ne doivent jamais être coupés).
    $champs = @(); $bloc = @(); $taille = 0; $premier = $true
    foreach ($a in @($liste | Select-Object -First $max)) {
        $ligne = Get-TrainLigneAnnonce $a
        if ($ligne.Length -gt 1000) { $ligne = "• $(Get-TrainTitreAffiche $a) · $($a.employeur) · $($a.lieu)" }
        if ($taille + $ligne.Length + 1 -gt 1000 -and $bloc.Count) { $champs += @{ nom = $(if ($premier) { $nom } else { "$nom (suite)" }); valeur = ($bloc -join "`n"); inline = $false }; $premier = $false; $bloc = @(); $taille = 0 }
        $bloc += $ligne; $taille += $ligne.Length + 1
    }
    if ($bloc.Count) { $champs += @{ nom = $(if ($premier) { $nom } else { "$nom (suite)" }); valeur = ($bloc -join "`n"); inline = $false } }
    $champs
}
function New-EmbedTrainResume($nouvelles, $sourcesMuettes = @(), $ecarts = $null) {
    $n = @($nouvelles); $desc = $(if ($n.Count) { "$($n.Count) nouvelle$(if ($n.Count -gt 1) { 's' }) annonce$(if ($n.Count -gt 1) { 's' }) depuis hier." } else { 'Aucune nouvelle annonce depuis hier.' })
    $champs = @(); if ($n.Count) { $champs += @(Get-TrainChampsAnnonces $n 10 'Annonces') }      # titres cliquables (lien de l'annonce)
    $et = Get-TrainEcartTexte $ecarts; if ($et) { $champs += @{ nom = 'Annonces écartées'; valeur = $et; inline = $false } }
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
    $trouvees = @(); $erreurs = @(); $muettes = @(); $script:TrainEcart = @{ lieu = 0; langue = 0; tram = 0; employeur = 0; experience = 0 }; $script:TrainOllamaHS = $false
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
    Add-TrainEcartsEtat $e
    $nouvelles = @($trouvees | Where-Object { $e.vus -notcontains $_.id } | Sort-Object { $_.id } -Unique)
    $envoyees = 0; $n = 0
    foreach ($a in $nouvelles) {
        $n++
        if ($n -gt $script:TrainMaxCartes) { break }
        try { $fr = Get-TrainTraduction $a; if ($fr) { $a.titre_fr = $fr } } catch {}      # jamais d'erreur : sans traduction, titre original
        if (Send-TrainNotif 'jarvis' (New-EmbedTrainAnnonce $a)) { $envoyees++; $e.vus += $a.id; $a.vu_le = $now.ToString('o'); $e.nouvelles += $a; if (Get-Command Invoke-CvBrouillon -ErrorAction SilentlyContinue) { Invoke-CvBrouillon $a $now } }      # lib\cv-candidature.ps1 : brouillon prêt dans #candidatures (rien n'est envoyé)
    }
    $reste = @($nouvelles | Select-Object -Skip $script:TrainMaxCartes)
    if ($reste.Count) {      # trop d'annonces d'un coup (premier passage) : une seule carte pour le reste, pas de rafale
        $emb = New-EmbedDiscord "$($reste.Count) autres nouvelles annonces" 'Pour ne pas vous noyer, voici les titres ; cliquez sur un titre pour ouvrir l''annonce.' $script:CouleurBleue @(Get-TrainChampsAnnonces $reste 12 'Annonces') (Get-PiedDiscord 'annonces-train')
        if (Send-TrainNotif 'jarvis' $emb) { foreach ($a in $reste) { $e.vus += $a.id; $a.vu_le = $now.ToString('o'); $e.nouvelles += $a } }
    }
    $e.nouvelles = @($e.nouvelles | Where-Object { try { ($now - [datetime]$_.vu_le).TotalDays -lt 7 } catch { $false } })
    $resume = $false
    if ($now.ToString('HH:mm') -ge $c.resume -and $e.dernier_resume -ne $jour) {      # résumé quotidien du matin (rattrapage : au premier passage après l'heure)
        $veille = @($e.nouvelles | Where-Object { try { ($now - [datetime]$_.vu_le).TotalHours -lt 24 -and ($_.source -ne 'sbb' -or (Get-TrainFiltreSuisse $_.lieu $_.titre).garde) } catch { $false } })      # anciennes alémaniques déjà vues : jamais dans le résumé
        if (Send-TrainNotif 'jarvis' (New-EmbedTrainResume $veille $muettes $e.ecarts)) { $e.dernier_resume = $jour; $resume = $true; $e.ecarts = @{} }
    }
    $e.dernier_passage = $now.ToString('o'); $e.pid = 0; Save-TrainEtat $e
    $ecT = 0; foreach ($k in $script:TrainEcartCles) { $ecT += [int]$script:TrainEcart[$k] }
    Write-Journal -Action 'Veille annonces-train' -Resultat "$($trouvees.Count + $ecT) annonce(s) de conduite vue(s) : $($trouvees.Count) gardée(s), $ecT écartée(s) ($(Get-TrainEcartTexte $script:TrainEcart -Tout)) ; $($nouvelles.Count) nouvelle(s), $envoyees carte(s)$(if ($erreurs.Count) { ', sources en erreur : ' + ($erreurs -join ', ') })"
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
    if ((Get-Command Test-MailLancementRecent -ErrorAction SilentlyContinue) -and (Test-MailLancementRecent $now)) { return $false }      # un passage e-mail vient d'être lancé : un seul processus à la fois
    foreach ($k in @(@('dernier_passage', $c.minutes), @('dernier_lancement', 10))) { $d = [datetime]::MinValue; if ([datetime]::TryParse($e[$k[0]], [Globalization.CultureInfo]::InvariantCulture, [Globalization.DateTimeStyles]::RoundtripKind, [ref]$d) -and ($now - $d).TotalMinutes -lt $k[1]) { return $false } }
    if (Test-ModeTest) { $script:TrainRunnerLance = $true; return $true }
    $s = Join-Path $script:RacineReelle 'veille-train.ps1'; if (-not (Test-Path $s)) { return $false }
    $e.dernier_lancement = $now.ToString('o'); Save-TrainEtat $e
    try { [void](Start-Process powershell -ArgumentList '-NoProfile', '-ExecutionPolicy', 'Bypass', '-WindowStyle', 'Hidden', '-File', "`"$s`"" -WindowStyle Hidden -PassThru); $true } catch { Write-Journal -Action 'Veille annonces-train' -Resultat 'lancement impossible'; $false }
}
