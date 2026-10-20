# Veille « annonces-train » par E-MAIL : lit les e-mails d'alerte d'emploi (Jobup, JobScout24, CFF / SBB) rangés par vous dans le libellé Gmail « annonces-train »,
# en extrait titre, employeur, lieu et lien, applique le même filtre (Suisse romande et Suisse alémanique proche ; offres en allemand gardées et traduites), la même traduction et la même absence de doublons que la veille horaire, et poste les cartes dans #annonces-train.
# DÉSACTIVÉE par défaut (veille_mail = "non"). Un passage toutes les 10 minutes (veille_mail_minutes, 5 au moins), dans le processus séparé veille-train.ps1 -Mail.
# SÉCURITÉ : LECTURE SEULE (portée OAuth gmail.readonly : aucun envoi, aucune modification, aucune suppression possible) ; seul le libellé annonces-train est lu ; seuls les expéditeurs autorisés ET authentifiés (DMARC / DKIM / SPF) comptent.
# Le contenu d'un e-mail est une DONNÉE : on n'en tire que des titres, des lieux et des liens (jamais suivis, jamais ouverts) ; aucune phrase d'un e-mail n'est exécutée, envoyée à Claude ou prise pour un ordre.
# Secrets : GMAIL_CLIENT_ID et GMAIL_CLIENT_SECRET dans .env (jamais affichés) ; le jeton d'accès durable est chiffré par Windows (DPAPI, lié à votre compte) dans memoire\gmail-jeton.dpapi. Autorisation unique : jarvis.ps1 gmail-autoriser.
# Base locale : memoire\veille-mail.json (messages déjà traités, dernier passage) ; les annonces déjà vues sont celles de memoire\veille-train.json (même verrou : un seul passage à la fois).

$script:MailProchainTour = [datetime]::MinValue; $script:MailRunnerLance = $false; $script:MailAvertiAutorisation = $false
$script:MailLibelle = 'annonces-train'
$script:MailPortee = 'https://www.googleapis.com/auth/gmail.readonly'
$script:MailExpediteurs = '(^|\.)(jobup\.ch|jobscout24\.ch|sbb\.ch)$'
# Rouen / Normandie (liste blanche de lieux, comme pour la Suisse romande ; texte normalisé sans accents)
$script:TrainNormand = '\b(rouen|normandie|le havre|caen|cherbourg|dieppe|evreux|elbeuf|sotteville|quevilly|mont saint aignan|barentin|yvetot|lisieux|oissel|montivilliers|fecamp|bernay|vernon|louviers|pont audemer|saint etienne du rouvray|darnetal|gisors|serquigny|alencon|saint lo|granville|avranches|coutances|flers|argentan|honfleur|deauville|bolbec|lillebonne|gonfreville|harfleur)\b'

$script:MailLieuxAffiches = @{ 'geneve' = 'Genève'; 'delemont' = 'Delémont'; 'neuchatel' = 'Neuchâtel'; 'la chaux de fonds' = 'La Chaux-de-Fonds'; 'saint maurice' = 'Saint-Maurice'; 'st maurice' = 'Saint-Maurice'; 'palezieux' = 'Palézieux'
    'evreux' = 'Évreux'; 'fecamp' = 'Fécamp'; 'alencon' = 'Alençon'; 'saint lo' = 'Saint-Lô'; 'mont saint aignan' = 'Mont-Saint-Aignan'; 'saint etienne du rouvray' = 'Saint-Étienne-du-Rouvray'; 'siders' = 'Sierre'; 'genf' = 'Genève'; 'neuenburg' = 'Neuchâtel' }      # affichage avec accents (le lieu est cherché sans accents)

function Get-MailConfig {
    $oui = @('oui', 'true', '1', 'on', 'yes'); $c = @{ actif = $false; minutes = 10 }
    if ($Config.PSObject.Properties['veille_mail'] -and "$($Config.veille_mail)".Trim().ToLower() -in $oui) { $c.actif = $true }
    if ($Config.PSObject.Properties['veille_mail_minutes'] -and "$($Config.veille_mail_minutes)" -match '^\d+$') { $c.minutes = [math]::Max(5, [math]::Min(1440, [int]$Config.veille_mail_minutes)) }
    $c
}

# ---------- Jeton Gmail (chiffré par Windows, lié à votre compte) ----------
function Save-GmailJeton([string]$refresh) {
    [IO.File]::WriteAllText((Get-FichierMemoire 'gmail-jeton.dpapi'), (ConvertFrom-SecureString (ConvertTo-SecureString $refresh -AsPlainText -Force)), [Text.UTF8Encoding]::new($false))
}
function Get-GmailJeton {
    $f = Get-FichierMemoire 'gmail-jeton.dpapi'; if (-not (Test-Path $f)) { return '' }
    try { [Net.NetworkCredential]::new('', (ConvertTo-SecureString ((Get-Content $f -Raw -Encoding UTF8).Trim()))).Password } catch { '' }
}
function Test-MailAutorise { [bool]((Get-EnvPropre 'GMAIL_CLIENT_ID') -and (Get-EnvPropre 'GMAIL_CLIENT_SECRET') -and (Get-GmailJeton)) }
function Add-MailSecret([string]$s) { if ($s -and $script:Secrets -notcontains $s) { $script:Secrets += $s } }

# ---------- Autorisation unique (OAuth « application de bureau », PKCE, retour sur 127.0.0.1) ----------
function New-GmailPkce {
    $b = New-Object byte[] 48; $rng = [Security.Cryptography.RandomNumberGenerator]::Create(); $rng.GetBytes($b); $rng.Dispose()
    $v = [Convert]::ToBase64String($b).TrimEnd('=').Replace('+', '-').Replace('/', '_')
    $h = [Security.Cryptography.SHA256]::Create().ComputeHash([Text.Encoding]::ASCII.GetBytes($v))
    @{ verifier = $v; challenge = [Convert]::ToBase64String($h).TrimEnd('=').Replace('+', '-').Replace('/', '_') }
}
function Get-GmailUrlAutorisation([string]$clientId, [string]$redirect, [string]$challenge, [string]$etat) {
    $e = { param($x) [uri]::EscapeDataString($x) }
    'https://accounts.google.com/o/oauth2/v2/auth?' + (@("client_id=$(& $e $clientId)", "redirect_uri=$(& $e $redirect)", 'response_type=code', "scope=$(& $e $script:MailPortee)", "code_challenge=$challenge", 'code_challenge_method=S256', "state=$etat", 'access_type=offline', 'prompt=consent') -join '&')
}
function Invoke-GmailAutoriser {
    $id = Get-EnvPropre 'GMAIL_CLIENT_ID'; $sec = Get-EnvPropre 'GMAIL_CLIENT_SECRET'
    if (-not $id -or -not $sec) { Write-Host 'GMAIL_CLIENT_ID et GMAIL_CLIENT_SECRET manquent dans .env (voir README, « Veille e-mail »).'; return }
    Add-MailSecret $id; Add-MailSecret $sec
    $pk = New-GmailPkce; $etat = [guid]::NewGuid().ToString('N'); $redirect = "http://127.0.0.1:$(Get-Random -Minimum 49200 -Maximum 49900)/"
    $url = Get-GmailUrlAutorisation $id $redirect $pk.challenge $etat
    $ln = New-Object Net.HttpListener; $ln.Prefixes.Add($redirect)
    try {
        $ln.Start()
        Write-Host "Autorisation Gmail en LECTURE SEULE. Connectez-vous dans le navigateur qui s'ouvre (3 minutes). Sinon, ouvrez cette adresse :`n$url"
        try { Start-Process $url } catch {}
        $t = $ln.GetContextAsync(); if (-not $t.Wait(180000)) { Write-Host 'Délai dépassé : relancez la commande.'; return }
        $ctx = $t.Result; $code = $ctx.Request.QueryString['code']; $etatRecu = $ctx.Request.QueryString['state']
        $page = [Text.Encoding]::UTF8.GetBytes('<html><meta charset="utf-8"><body style="font-family:sans-serif"><h3>Jarvis : autorisation reçue.</h3><p>Vous pouvez fermer cet onglet.</p></body></html>')
        $ctx.Response.ContentType = 'text/html; charset=utf-8'; $ctx.Response.OutputStream.Write($page, 0, $page.Length); $ctx.Response.Close()
    } finally { try { $ln.Stop() } catch {} }
    if (-not $code -or $etatRecu -ne $etat) { Write-Host 'Réponse invalide (code ou état incorrect) : rien n''est enregistré.'; return }
    Add-MailSecret $code
    $e = { param($x) [uri]::EscapeDataString($x) }
    $r = Invoke-TrainHttp 'https://oauth2.googleapis.com/token' 'POST' ("code=$(& $e $code)&client_id=$(& $e $id)&client_secret=$(& $e $sec)&redirect_uri=$(& $e $redirect)&grant_type=authorization_code&code_verifier=$(& $e $pk.verifier)")
    if ($r.code -ne 200) { Write-Host "Google a refusé l'échange (HTTP $($r.code)) : $(Short (Hide-Secrets $r.texte) 160)"; return }
    $o = $r.texte | ConvertFrom-Json; $portees = @("$($o.scope)" -split '\s+')
    if (-not $o.refresh_token) { Write-Host 'Google n''a pas donné de jeton durable : relancez la commande (consentement demandé à nouveau).'; return }
    Add-MailSecret "$($o.refresh_token)"; Add-MailSecret "$($o.access_token)"
    if ($portees -notcontains $script:MailPortee -or @($portees | Where-Object { $_ -match 'gmail\.(modify|send|compose|insert|labels|settings)|mail\.google\.com' }).Count) { Write-Host 'La portée accordée dépasse la lecture seule : rien n''est enregistré.'; return }
    Save-GmailJeton "$($o.refresh_token)"
    Write-Journal -Action 'Veille e-mail' -Resultat 'Gmail autorisé en lecture seule (clé chiffrée par Windows, memoire\gmail-jeton.dpapi)'
    Write-Host 'Gmail autorisé en lecture seule. Jeton enregistré (chiffré par Windows, jamais affiché). Mettez veille_mail à "oui" dans config.local.json, puis redémarrez Jarvis.'
}

# ---------- Gmail : lecture seule (GET uniquement ; le seul POST est l'échange de jeton) ----------
function Get-GmailAccessToken {
    $id = Get-EnvPropre 'GMAIL_CLIENT_ID'; $sec = Get-EnvPropre 'GMAIL_CLIENT_SECRET'; $rt = Get-GmailJeton
    if (-not $id -or -not $sec -or -not $rt) { throw 'Gmail non autorisé : renseignez GMAIL_CLIENT_ID / GMAIL_CLIENT_SECRET dans .env puis lancez jarvis.ps1 gmail-autoriser' }
    Add-MailSecret $id; Add-MailSecret $sec; Add-MailSecret $rt
    $e = { param($x) [uri]::EscapeDataString($x) }
    $r = Invoke-TrainHttp 'https://oauth2.googleapis.com/token' 'POST' ("client_id=$(& $e $id)&client_secret=$(& $e $sec)&refresh_token=$(& $e $rt)&grant_type=refresh_token")
    if ($r.code -ne 200) { throw "accès Gmail refusé (HTTP $($r.code)) : relancez jarvis.ps1 gmail-autoriser" }
    $tok = "$(($r.texte | ConvertFrom-Json).access_token)"; if (-not $tok) { throw 'accès Gmail : réponse vide' }
    Add-MailSecret $tok; $tok
}
function Invoke-GmailGet([string]$chemin, [string]$tok) {
    $r = Invoke-TrainHttp ("https://gmail.googleapis.com/gmail/v1/users/me/$chemin") 'GET' '' @{ Authorization = "Bearer $tok"; Accept = 'application/json' }
    if ($r.code -ne 200) { throw "Gmail HTTP $($r.code) $(Short (Hide-Secrets $r.texte) 100)" }
    $r.texte | ConvertFrom-Json
}
function Get-GmailLibelleId([string]$tok) {
    $l = @((Invoke-GmailGet 'labels' $tok).labels | Where-Object { "$($_.name)" -ieq $script:MailLibelle }) | Select-Object -First 1
    if (-not $l) { throw "libellé Gmail « $($script:MailLibelle) » introuvable (créez-le et ajoutez un filtre Gmail sur les expéditeurs autorisés)" }
    "$($l.id)"
}
function ConvertFrom-GmailBase64([string]$s) {
    if (-not $s) { return '' }; $b = $s.Replace('-', '+').Replace('_', '/'); switch ($b.Length % 4) { 2 { $b += '==' } 3 { $b += '=' } }
    try { [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($b)) } catch { '' }
}
function Get-GmailCorps($part, [int]$prof = 0) {
    # HTML (et texte brut) d'un message ; profondeur et taille bornées.
    if ($prof -gt 6 -or -not $part) { return @{ html = ''; txt = '' } }
    $html = ''; $txt = ''; $mt = "$($part.mimeType)"
    if ($mt -eq 'text/html' -and $part.body.data) { $html = ConvertFrom-GmailBase64 "$($part.body.data)" }
    elseif ($mt -eq 'text/plain' -and $part.body.data) { $txt = ConvertFrom-GmailBase64 "$($part.body.data)" }
    foreach ($p in @($part.parts)) { $s = Get-GmailCorps $p ($prof + 1); $html += $s.html; $txt += $s.txt }
    if ($html.Length -gt 600000) { $html = $html.Substring(0, 600000) }
    @{ html = $html; txt = $txt }
}
function Get-GmailEntetes($msg, [string]$nom) { (@($msg.payload.headers | Where-Object { "$($_.name)" -ieq $nom } | ForEach-Object { "$($_.value)" }) -join ' ; ') }

# ---------- Expéditeur autorisé ET authentifié ----------
function Get-MailDomaine([string]$from) {
    # Domaine de l'adresse réelle (celle entre < >, ou l'adresse seule) : un nom affiché « x@jobup.ch » ne trompe pas.
    $f = "$from".Trim(); $m = [regex]::Match($f, '<([^<>@\s]+@([^<>\s@]+))>\s*$')
    if (-not $m.Success) { $m = [regex]::Match($f, '^([^<>@\s"]+@([^<>\s@"]+))$') }
    if ($m.Success) { $m.Groups[2].Value.ToLowerInvariant().TrimEnd('.') } else { '' }
}
function Test-MailExpediteur([string]$from, [string]$auth) {
    $d = Get-MailDomaine $from; if (-not $d -or $d -notmatch $script:MailExpediteurs) { return $false }
    # Authentification notée par Gmail : DMARC réussi pour ce domaine, ou DKIM / SPF réussi POUR un domaine autorisé (un faux « From » échoue).
    if ($auth -match '(?i)dmarc=pass[^;]*header\.from=@?([A-Za-z0-9.\-]+)') { foreach ($m in [regex]::Matches($auth, '(?i)dmarc=pass[^;]*header\.from=@?([A-Za-z0-9.\-]+)')) { if ($m.Groups[1].Value.ToLowerInvariant() -match $script:MailExpediteurs) { return $true } } }
    foreach ($m in [regex]::Matches($auth, '(?i)dkim=pass[^;]*?header\.(?:d|i)=@?([A-Za-z0-9.\-]+)')) { if ($m.Groups[1].Value.ToLowerInvariant() -match $script:MailExpediteurs) { return $true } }
    foreach ($m in [regex]::Matches($auth, '(?i)spf=pass[^;]*?smtp\.mailfrom=(?:[^@\s;]*@)?([A-Za-z0-9.\-]+)')) { if ($m.Groups[1].Value.ToLowerInvariant() -match $script:MailExpediteurs) { return $true } }
    $false
}
function Get-MailEmployeur([string]$d) {
    if ($d -match 'jobup') { return 'Jobup (alerte e-mail)' }; if ($d -match 'jobscout24') { return 'JobScout24 (alerte e-mail)' }; if ($d -match 'sbb\.ch') { return 'CFF / SBB (alerte e-mail)' }
    'Alerte e-mail'
}
$script:MailEmployeursConnus = [ordered]@{ 'cff|sbb|ffs' = 'CFF / SBB'; 'bls' = 'BLS'; 'sob' = 'SOB'; 'thurbo' = 'Thurbo'; 'tpf' = 'TPF'; 'travys' = 'TRAVYS'; 'transn' = 'transN'; 'mbc' = 'MBC'; 'rbs' = 'RBS'; 'zentralbahn' = 'Zentralbahn'; 'aare seeland mobil|asm' = 'ASM'; 'blt' = 'BLT'; 'tpg' = 'TPG'; 'tl' = 'TL'; 'chemins de fer du jura|cj' = 'Chemins de fer du Jura'; 'mob' = 'MOB'; 'bob' = 'BOB'; 'matterhorn gotthard' = 'Matterhorn Gotthard Bahn'; 'rhaetische|rhb' = 'RhB' }
function Get-MailEmployeurTexte([string]$texte, [string]$defaut) {
    # Employeur lu dans le texte de l'offre (compagnies ferroviaires connues) ; sinon l'étiquette de l'expéditeur.
    $n = ConvertTo-TrainNorm $texte; foreach ($k in $script:MailEmployeursConnus.Keys) { if ($n -match ('\b(' + $k + ')\b')) { return $script:MailEmployeursConnus[$k] } }
    $defaut
}

# ---------- Extraction : titre, lieu, lien (rien d'autre n'est gardé) ----------
function ConvertTo-MailTexte([string]$h) {
    $t = $h -replace '(?is)<(script|style)[^>]*>.*?</\1>', ' ' -replace '(?s)<!--.*?-->', ' ' -replace '<[^>]+>', ' '
    ([Net.WebUtility]::HtmlDecode($t) -replace '[\u0000-\u001f\u007f​-‏ -‮﻿]', ' ' -replace '\s+', ' ').Trim()
}
function Get-MailLieu([string]$texte) {
    # Premier lieu reconnu (liste blanche Suisse romande / Normandie) dans le texte ; '' si aucun (l'annonce sera écartée).
    $n = ConvertTo-TrainNorm $texte; $best = $null
    foreach ($re in $script:TrainRomand, $script:TrainBilingue, $script:TrainProche, $script:TrainNormand) { $m = [regex]::Match($n, $re); if ($m.Success -and (-not $best -or $m.Index -lt $best.Index)) { $best = $m } }
    if (-not $best) { return '' }
    if ($script:MailLieuxAffiches.ContainsKey($best.Value)) { $script:MailLieuxAffiches[$best.Value] } else { ([Globalization.CultureInfo]::InvariantCulture).TextInfo.ToTitleCase($best.Value) }
}
function Get-TrainFiltreMail([string]$lieu, [string]$titre) {
    # Rouen / Normandie : gardé ; sinon le filtre Suisse romande habituel (lieu romand, ou bilingue avec un titre non allemand).
    if ((ConvertTo-TrainNorm $lieu) -match $script:TrainNormand) { return @{ garde = $true; allemand = $false; raison = '' } }
    Get-TrainFiltreSuisse $lieu $titre
}
function Get-MailAnnonces([string]$html, [string]$domaine, [string]$date) {
    # Les LIENS dont le texte parle de conduite de train ; le lieu est cherché dans le texte qui suit le lien (jusqu'à l'annonce suivante). Retourne les annonces GARDÉES ; les écartées sont comptées (Add-TrainEcart).
    $employeur = Get-MailEmployeur $domaine; $out = @(); $vus = @{}
    $ancres = @([regex]::Matches($html, '(?is)<a\s[^>]*?href\s*=\s*["'']([^"'']+)["''][^>]*>(.*?)</a>') | ForEach-Object { [pscustomobject]@{ fin = $_.Index + $_.Length; debut = $_.Index; href = $_.Groups[1].Value; titre = (ConvertTo-MailTexte $_.Groups[2].Value) } })
    $cand = @($ancres | Where-Object { $_.titre.Length -ge 6 -and $_.titre.Length -le 200 -and (Test-TrainAnnonce $_.titre) })
    for ($i = 0; $i -lt $cand.Count; $i++) {
        $a = $cand[$i]; $finCtx = $(if ($i + 1 -lt $cand.Count) { $cand[$i + 1].debut } else { $html.Length }); $finCtx = [math]::Min($finCtx, $a.fin + 1500)
        $ctx = $(if ($finCtx -gt $a.fin) { ConvertTo-MailTexte $html.Substring($a.fin, $finCtx - $a.fin) } else { '' })
        $lieu = Get-MailLieu "$($a.titre) $ctx"
        $f = Get-TrainFiltreMail $lieu $a.titre
        if (-not $f.garde) { Add-TrainEcart $f.raison; continue }
        $sha = [Security.Cryptography.SHA1]::Create(); $h = (($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes((ConvertTo-TrainNorm $a.titre) + '|' + (ConvertTo-TrainNorm $lieu))) | ForEach-Object { $_.ToString('x2') }) -join ''); $sha.Dispose()
        $ident = $h.Substring(0, 16); if ($vus.ContainsKey($ident)) { continue }; $vus[$ident] = $true
        $n = New-TrainAnnonce 'mail' $ident $a.titre (Get-MailEmployeurTexte "$($a.titre) $ctx" $employeur) $lieu $date ([Net.WebUtility]::HtmlDecode($a.href).Trim())
        if ($f.allemand) { $n.langue = 'Allemand probable (titre en allemand)' }
        $out += $n
    }
    $out
}

# ---------- Base locale des messages traités ----------
function Get-MailEtat {
    $o = Read-JsonMemoire 'veille-mail.json'; $m = @{ dernier_passage = ''; dernier_lancement = ''; messages = @() }
    if ($o) { foreach ($k in 'dernier_passage', 'dernier_lancement') { if ($o.PSObject.Properties[$k]) { $m[$k] = "$($o.$k)" } }; if ($o.PSObject.Properties['messages']) { $m.messages = @($o.messages | ForEach-Object { "$_" }) } }
    $m
}
function Save-MailEtat($m) { Save-JsonMemoire 'veille-mail.json' ([ordered]@{ dernier_passage = $m.dernier_passage; dernier_lancement = $m.dernier_lancement; messages = @($m.messages | Select-Object -Last 500) }) }

# ---------- Un passage ----------
function Invoke-VeilleMail([datetime]$now = (Get-Date)) {
    # Retourne @{ lus; nouvelles; envoyees; erreur }. Une erreur Gmail = une carte « attention » par jour, jamais de plantage.
    $e = Get-TrainEtat; $m = Get-MailEtat; $jour = $now.ToString('yyyy-MM-dd')
    $e.pid = $PID; Save-TrainEtat $e      # même verrou que la veille horaire : un seul passage à la fois (les dates de la veille horaire ne bougent pas)
    $m.dernier_lancement = $now.ToString('o'); Save-MailEtat $m
    $script:TrainEcart = @{ lieu = 0; langue = 0 }; $script:TrainOllamaHS = $false
    $lus = 0; $refuses = 0; $gardees = 0; $nouvelles = 0; $envoyees = 0; $erreur = ''; $deja = @{}
    try {
        $tok = Get-GmailAccessToken; $lib = Get-GmailLibelleId $tok
        $liste = Invoke-GmailGet ("messages?labelIds=$([uri]::EscapeDataString($lib))&maxResults=25&q=" + [uri]::EscapeDataString('newer_than:7d')) $tok
        foreach ($ref in @($liste.messages)) {
            if (-not $ref -or $m.messages -contains "$($ref.id)") { continue }
            if ($envoyees -ge $script:TrainMaxCartes) { break }      # le reste au passage suivant (10 minutes), pas de rafale
            $msg = Invoke-GmailGet ("messages/$([uri]::EscapeDataString("$($ref.id)"))?format=full") $tok
            if (@($msg.labelIds) -notcontains $lib) { continue }      # seul le libellé annonces-train compte
            $lus++
            $from = Get-GmailEntetes $msg 'From'
            if (-not (Test-MailExpediteur $from (Get-GmailEntetes $msg 'Authentication-Results'))) { $refuses++; $m.messages += "$($ref.id)"; continue }
            $date = ''; try { $date = [DateTimeOffset]::FromUnixTimeMilliseconds([long]"$($msg.internalDate)").LocalDateTime.ToString('yyyy-MM-dd') } catch {}
            $corps = Get-GmailCorps $msg.payload
            $annonces = @(Get-MailAnnonces $corps.html (Get-MailDomaine $from) $date); $gardees += $annonces.Count
            $toutEnvoye = $true
            foreach ($a in @($annonces | Where-Object { $e.vus -notcontains $_.id -and -not $deja.ContainsKey($_.id) })) {
                $nouvelles++
                if ($envoyees -ge $script:TrainMaxCartes) { $toutEnvoye = $false; break }
                $deja[$a.id] = $true
                try { $fr = Get-TrainTraduction $a; if ($fr) { $a.titre_fr = $fr } } catch {}      # sans traduction : titre original
                if (Send-TrainNotif 'jarvis' (New-EmbedTrainAnnonce $a)) { $envoyees++; $e.vus += $a.id; $a.vu_le = $now.ToString('o'); $e.nouvelles += $a } else { $toutEnvoye = $false }
            }
            if ($toutEnvoye) { $m.messages += "$($ref.id)" }      # un message n'est « traité » que si toutes ses nouvelles annonces sont parties
        }
    } catch {
        $erreur = Short (Hide-Secrets $_.Exception.Message) 200
        if ($e.erreurs['E-mail (Gmail)'] -ne $jour) { if (Send-TrainNotif 'systeme' (New-EmbedTrainAttention 'E-mail (Gmail)' $erreur)) { $e.erreurs['E-mail (Gmail)'] = $jour } }      # une carte par jour
    }
    $e.nouvelles = @($e.nouvelles | Where-Object { try { ($now - [datetime]$_.vu_le).TotalDays -lt 7 } catch { $false } })
    $e.pid = 0; Save-TrainEtat $e
    $m.dernier_passage = $now.ToString('o'); Save-MailEtat $m
    $ecL = [int]$script:TrainEcart.lieu; $ecG = [int]$script:TrainEcart.langue
    if ($lus -or $erreur -or $envoyees) {      # rien à dire = rien dans le journal (un passage toutes les 10 minutes)
        Write-Journal -Action 'Veille e-mail' -Resultat "$(Format-Pluriel $lus 'mail lu' 'mails lus'), $(Format-Pluriel ($gardees + $ecL + $ecG) 'offre' 'offres'), $(Format-Pluriel $gardees 'gardée' 'gardées') ($($ecL + $ecG) écartée(s) hors Suisse romande / alémanique proche)$(if ($refuses) { " ; $refuses expéditeur(s) refusé(s) (non autorisé ou non authentifié)" }) ; $nouvelles nouvelle(s), $envoyees carte(s)$(if ($erreur) { ', erreur : ' + $erreur })"
    }
    @{ lus = $lus; nouvelles = $nouvelles; envoyees = $envoyees; erreur = $erreur }
}

# ---------- Boucle de Jarvis (légère : aucun réseau ici) ----------
function Test-MailLancementRecent([datetime]$now = (Get-Date), [int]$minutes = 2) {
    $d = [datetime]::MinValue; $m = Get-MailEtat
    [datetime]::TryParse($m.dernier_lancement, [Globalization.CultureInfo]::InvariantCulture, [Globalization.DateTimeStyles]::RoundtripKind, [ref]$d) -and ($now - $d).TotalMinutes -lt $minutes
}
function Update-VeilleMail([datetime]$now = (Get-Date)) {
    # Ne fait RIEN si veille_mail n'est pas "oui" ou si Gmail n'est pas autorisé. Lance un passage toutes les 10 minutes (veille_mail_minutes). Jamais en mode jeu.
    $c = Get-MailConfig; if (-not $c.actif) { return $false }
    if ($now -lt $script:MailProchainTour) { return $false }; $script:MailProchainTour = $now.AddSeconds(30)
    if ($script:ModeJeu -eq $true) { return $false }
    if (-not (Test-MailAutorise)) {
        if (-not $script:MailAvertiAutorisation) { $script:MailAvertiAutorisation = $true; Write-Journal -Action 'Veille e-mail' -Resultat 'activée mais Gmail non autorisé : renseignez GMAIL_CLIENT_ID / GMAIL_CLIENT_SECRET dans .env puis lancez jarvis.ps1 gmail-autoriser' }
        return $false
    }
    $e = Get-TrainEtat; if (Test-TrainProcessusVivant $e.pid) { return $false }      # la veille horaire (ou un autre passage) tourne : on attend
    $d = [datetime]::MinValue; if ([datetime]::TryParse($e.dernier_lancement, [Globalization.CultureInfo]::InvariantCulture, [Globalization.DateTimeStyles]::RoundtripKind, [ref]$d) -and ($now - $d).TotalMinutes -lt 2) { return $false }      # la veille horaire vient d'être lancée
    $m = Get-MailEtat
    foreach ($k in @(@('dernier_passage', $c.minutes), @('dernier_lancement', 3))) { $d = [datetime]::MinValue; if ([datetime]::TryParse($m[$k[0]], [Globalization.CultureInfo]::InvariantCulture, [Globalization.DateTimeStyles]::RoundtripKind, [ref]$d) -and ($now - $d).TotalMinutes -lt $k[1]) { return $false } }
    if (Test-ModeTest) { $script:MailRunnerLance = $true; return $true }
    $s = Join-Path $script:RacineReelle 'veille-train.ps1'; if (-not (Test-Path $s)) { return $false }
    $m.dernier_lancement = $now.ToString('o'); Save-MailEtat $m
    try { [void](Start-Process powershell -ArgumentList '-NoProfile', '-ExecutionPolicy', 'Bypass', '-WindowStyle', 'Hidden', '-File', "`"$s`"", '-Mail' -WindowStyle Hidden -PassThru); $true } catch { Write-Journal -Action 'Veille e-mail' -Resultat 'lancement impossible'; $false }
}
