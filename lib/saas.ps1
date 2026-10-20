# Point SaaS (Trouve ton produit) et briefing du matin : LECTURE SEULE, uniquement des sources déjà branchées, aucun chiffre inventé.
# Sources : site (requête GET), Supabase (fonction jarvis_stats : quiz, e-mails, abonnés), Stripe (clé restreinte en lecture : chiffre d'affaires), to-do, veille du marché, météo (Open-Meteo, seulement si meteo_latitude / meteo_longitude sont dans config.json).
# Une source absente ou refusée s'affiche « source non branchée » ou « indisponible » avec la raison ; jamais une valeur estimée.
#
# Sources NON branchées (noms exacts à fournir plus tard, voir JOURNAL-NUIT.md) :
#   - Vercel Analytics (visites) : branché dès que VERCEL_TOKEN + VERCEL_PROJECT_ID (+ VERCEL_TEAM_ID) sont dans .env ; jeton en lecture seule (aucun droit d'écriture ni de déploiement). Sinon « source non branchée ».
#   - Stripe : déjà branché si STRIPE_RESTRICTED_KEY (clé restreinte rk_…) existe ; droits minimaux en lecture seule : Charges (Read), Subscriptions (Read), rien d'autre.

function Test-DemandePointSaas([string]$texte) {
    # « as-tu les données du SaaS », « chiffres », « stats », « comment va le site », « où en est le SaaS »... (texte quelconque ; normalisé ici)
    $n = (ConvertTo-OrdreNorm "$texte").Trim() -replace '^(?:(?:hey|ok|dis|eh|oh)[\s,]+)*(?:jarvis[\s,]+)+', '' -replace '[\s.!?]+$', ''
    if (-not $n -or $n.Length -gt 120) { return $false }
    if ($n -match '\b(ouvr\w*|ferm\w*|ajout\w*|lance\w*|supprim\w*|efface\w*|modifi\w*|va sur|cree\w*|todo|rappel\w*)\b') { return $false }
    if ($n -match '^(?:les? |mes )?(?:chiffres|stats?|statistiques|donnees|resultats|bilan)(?: du jour| d hier| du moment)?$') { return $true }
    $sujet = '\b(saas|trouve ton produit|tonproduit|site|business|boutique|activite)\b'
    $verbe = '\b(donnees|chiffres?|stats?|statistiques|point|etat|bilan|resultats?|infos?|informations|comment va|comment vont|comment ca va|ou en est|ou en sont|ca donne quoi|quoi de neuf|nouvelles|marche)\b'
    [bool]($n -match $sujet -and $n -match $verbe)
}

function Get-SaasDonnees([datetime]$now = (Get-Date)) {
    # Une lecture de chaque source, chacune protégée : une panne ne casse jamais le reste.
    $depuis = $now.AddHours(-24)
    $d = @{ maj = $now; depuis = $depuis }
    try { $d.site = Get-StatutSite 8 } catch { $d.site = [pscustomobject]@{ ok = $false; code = 0; detail = "$($_.Exception.Message)" } }
    try { $d.stats = Get-SupabaseStats $depuis } catch { $d.stats = @{ dispo = $false; raison = 'Supabase : lecture impossible' } }
    try { $d.ca = Get-StripeCA $depuis } catch { $d.ca = @{ dispo = $false; raison = 'Stripe : lecture impossible' } }
    try { $d.visites = Get-VisitesBriefing $depuis } catch { $d.visites = @{ dispo = $false; raison = 'visites du site : source non branchée (Vercel Analytics)' } }
    try { $d.todo = @(Get-TodoOuverte) } catch { $d.todo = @() }
    $d.veille = Get-VeilleLigneSaas
    foreach ($k in 'site', 'stats', 'ca') {
        $ok = $(if ($k -eq 'site') { $d.site.ok } else { $d[$k].dispo })
        Write-Journal -Action "Point SaaS : lecture $k" -Resultat $(if ($ok) { 'ok' } elseif ($k -eq 'site') { "code $($d.site.code)" } else { "indisponible : $($d[$k].raison)" })
    }
    $d
}

function Get-VeilleLigneSaas {
    # La veille du marché, si elle est configurée ET branchée ; sinon une phrase honnête.
    try {
        if (-not (Test-MarcheActif)) { return 'Veille du marché désactivée (marche_actif).' }
        $r = Get-LigneMarcheCourte
        if (-not $r) { return 'Veille du marché : aucune source branchée.' }
        "$($r.ligne)"
    } catch { 'Veille du marché : indisponible.' }
}

function Get-MeteoBriefing {
    # Météo gratuite (Open-Meteo, sans clé) SEULEMENT si meteo_latitude et meteo_longitude sont renseignées dans config.json ; sinon « source non configurée ». @{ dispo; texte }.
    $lat = "$($Config.meteo_latitude)" -replace ',', '.'; $lon = "$($Config.meteo_longitude)" -replace ',', '.'
    if ($lat -notmatch '^-?\d{1,2}(\.\d+)?$' -or $lon -notmatch '^-?\d{1,3}(\.\d+)?$') { return @{ dispo = $false; texte = 'source non configurée (meteo_latitude et meteo_longitude dans config.json)' } }
    if (Test-ModeTest) { return @{ dispo = $false; texte = 'source non configurée (test)' } }
    try {
        $u = "https://api.open-meteo.com/v1/forecast?latitude=$lat&longitude=$lon&current=temperature_2m,weather_code&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=auto&forecast_days=1"
        $r = Invoke-RestMethod -Uri $u -TimeoutSec 10 -Method Get
        $c = [int]$r.current.weather_code
        $ciel = switch ($c) { 0 { 'ciel dégagé' } { $_ -in 1, 2 } { 'peu nuageux' } 3 { 'couvert' } { $_ -in 45, 48 } { 'brouillard' } { $_ -in 51, 53, 55, 56, 57 } { 'bruine' } { $_ -in 61, 63, 65, 66, 67, 80, 81, 82 } { 'pluie' } { $_ -in 71, 73, 75, 77, 85, 86 } { 'neige' } { $_ -in 95, 96, 99 } { 'orage' } default { 'temps variable' } }
        $fr = [Globalization.CultureInfo]::GetCultureInfo('fr-FR')
        $t = "$ciel, $(([double]$r.current.temperature_2m).ToString('0', $fr)) °C maintenant (de $(([double]$r.daily.temperature_2m_min[0]).ToString('0', $fr)) à $(([double]$r.daily.temperature_2m_max[0]).ToString('0', $fr)) °C), pluie possible à $([int]$r.daily.precipitation_probability_max[0]) %"
        @{ dispo = $true; texte = $t }
    } catch { @{ dispo = $false; texte = 'indisponible (Open-Meteo ne répond pas)' } }
}

# ---------- Mise en forme : champs lisibles, jamais de phrase en chaîne ----------
function Get-RaisonSaasLisible([string]$raison, [string]$secours = 'source non lue') {
    # Raison d'indisponibilité écrite pour Liam. Sans les mots « jeton », « token », « clé API » : le masque des secrets les efface et laisse « [SECRET] » dans le texte.
    $r = "$raison"
    if ($r -match '(?i)jeton.*(refus|faux)') { return 'accès refusé par Supabase (identifiant de lecture à vérifier)' }
    if ($r -match '(?i)SUPABASE_READ_KEY.*refus|cl[ée] Supabase.*refus') { return 'accès refusé par Supabase (clé de lecture à vérifier)' }
    if ($r -match '(?i)JARVIS_STATS_TOKEN absent') { return 'statistiques non configurées (réglage Supabase incomplet dans .env)' }
    if ($r -match '(?i)URL ou cl[ée] Supabase absente') { return 'Supabase non configuré (réglages manquants dans .env)' }
    if ($r -match '(?i)introuvable') { return 'fonction de statistiques introuvable côté Supabase' }
    $r = $r -replace '^(Supabase|Stripe)( \([^)]*\))? : ', ''
    if ($r.Trim()) { $r } else { $secours }
}
function Format-ValeurSaas($d) {
    # Textes des champs à partir des données lues. @{ site; quiz; emails; abonnes; ca; visites; taches; veille; echecs }
    $o = @{}
    if ($d.site.ok) { $o.site = "En ligne (HTTP $($d.site.code))" } elseif ($d.site.code) { $o.site = "Problème : HTTP $($d.site.code)" } else { $o.site = 'Ne répond pas' }
    $nd = { param($x, $fallback) "Indisponible : $(Get-RaisonSaasLisible "$($x.raison)" $fallback)" }
    if ($d.stats.dispo) {
        $s = $d.stats.saas
        $o.quiz = $(if ($s.ContainsKey('quiz_24h')) { "$($s.quiz_24h) sur 24 h" + $(if ($s.ContainsKey('quiz_total')) { "`nTotal : $($s.quiz_total)" } else { '' }) } elseif ($s.ContainsKey('quiz_total')) { "Total : $($s.quiz_total)" } else { 'Non communiqué par la source' })
        $o.emails = $(if ($s.ContainsKey('emails_24h')) { "$($s.emails_24h) sur 24 h" + $(if ($s.ContainsKey('emails_total')) { "`nTotal : $($s.emails_total)" } else { '' }) } elseif ($s.ContainsKey('emails_total')) { "Total : $($s.emails_total)" } else { 'Non communiqué par la source' })
        $ab = @(); if ($s.ContainsKey('abonnes_actifs')) { $ab += "$($s.abonnes_actifs) actif" + $(if ([int64]$s.abonnes_actifs -gt 1) { 's' }) }
        if ($s.ContainsKey('nouveaux_abonnes_24h')) { $ab += "$($s.nouveaux_abonnes_24h) nouveau" + $(if ([int64]$s.nouveaux_abonnes_24h -gt 1) { 'x' }) + ' sur 24 h' }
        if ($s.ContainsKey('abonnes_en_annulation') -and [int64]$s.abonnes_en_annulation -gt 0) { $ab += "$($s.abonnes_en_annulation) en cours d'annulation" }
        $o.abonnes = $(if ($ab.Count) { $ab -join "`n" } else { 'Non communiqué par la source' })
        $o.echecs = $(if ($s.ContainsKey('paiements_echoues') -and [int64]$s.paiements_echoues -gt 0) { "$($s.paiements_echoues) paiement" + $(if ([int64]$s.paiements_echoues -gt 1) { 's' }) + ' échoué' + $(if ([int64]$s.paiements_echoues -gt 1) { 's' }) } else { '' })
    } else {
        $o.quiz = & $nd $d.stats 'source non lue'; $o.emails = $o.quiz; $o.abonnes = $o.quiz; $o.echecs = ''
    }
    if ($d.ca.dispo) { $o.ca = $(if ($d.ca.montants.Count) { (Format-Montants $d.ca.montants) + ' sur 24 h' } else { '0 € sur 24 h' }) + $(if ($d.ca.partiel) { ' (au moins)' } else { '' }) }
    elseif ("$($d.ca.raison)" -match 'absente') { $o.ca = "Source non branchée`n(STRIPE_RESTRICTED_KEY)" } else { $o.ca = & $nd $d.ca 'source non lue' }
    $o.visites = $(if ($d.visites.dispo) { "$($d.visites.valeur) sur 24 h" } elseif ("$($d.visites.raison)" -match '(?i)non branch|absente?\b') { 'Source non branchée (Vercel Analytics)' } else { & $nd $d.visites 'source non lue' })
    $t = @($d.todo)
    $o.taches = $(if ($t.Count) { "$($t.Count) ouverte" + $(if ($t.Count -gt 1) { 's' }) + "`n" + (($t | Select-Object -First 3 | ForEach-Object { "• $_" }) -join "`n") + $(if ($t.Count -gt 3) { "`n… et $($t.Count - 3) autre" + $(if ($t.Count -gt 4) { 's' }) } else { '' }) } else { 'Aucune tâche ouverte' })
    $o.veille = "$($d.veille)"
    $o
}

function New-EmbedSaas($d, [string]$titre = 'Trouve ton produit · le point', [string]$intro = '', $meteo = $null) {
    $v = Format-ValeurSaas $d
    $alerte = (-not $d.site.ok) -or [bool]$v.echecs
    $champs = @(
        @{ nom = ((Get-EmojiModele $(if ($d.site.ok) { 'ok' } else { 'alerte' })) + ' Site'); valeur = $v.site; inline = $true },
        @{ nom = 'Quiz'; valeur = $v.quiz; inline = $true },
        @{ nom = 'E-mails'; valeur = $v.emails; inline = $true },
        @{ nom = 'Abonnés'; valeur = $v.abonnes; inline = $true },
        @{ nom = "Chiffre d'affaires"; valeur = $v.ca; inline = $true },
        @{ nom = 'Visites'; valeur = $v.visites; inline = $true })
    if ($v.echecs) { $champs += @{ nom = ((Get-EmojiModele 'alerte') + ' Paiements'); valeur = $v.echecs; inline = $true } }
    if ($meteo) { $champs += @{ nom = 'Météo'; valeur = $(if ($meteo.dispo) { $meteo.texte } else { "Source non configurée" }); inline = $false } }
    $champs += @{ nom = ((Get-EmojiModele 'note') + ' Tâches'); valeur = $v.taches; inline = $false }
    $champs += @{ nom = ((Get-EmojiModele 'hausse') + ' Veille'); valeur = $v.veille; inline = $false }
    $desc = if ($intro) { $intro } else { "$(Get-SalutationHeure), voici le point sur Trouve ton produit." }
    New-EmbedDiscord ((Get-EmojiModele 'hausse') + " $titre") $desc $(if ($alerte) { $script:CouleurOrange } else { $script:CouleurBleue }) $champs (Get-PiedDiscord '' $d.maj)
}

function Get-SaasLignes($d) {
    # La même chose en phrases courtes (voix, réponse écrite sans embed). Pas de point-virgule en chaîne, pas de double point.
    $v = Format-ValeurSaas $d
    $p = New-Object System.Collections.Generic.List[string]
    $c = { param($t) ("$t" -replace '\s*\r?\n\s*', ', ').Trim(' ', '.', ',') }
    $p.Add("Site : $(& $c $v.site).")
    $p.Add("Quiz : $(& $c $v.quiz).")
    $p.Add("E-mails : $(& $c $v.emails).")
    $p.Add("Abonnés : $(& $c $v.abonnes).")
    $p.Add("Chiffre d'affaires : $(& $c $v.ca).")
    $p.Add("Visites : $(& $c $v.visites).")
    $t = @($d.todo); $p.Add($(if ($t.Count) { "Tâches ouvertes : $($t.Count)." } else { 'Aucune tâche ouverte.' }))
    @($p)
}

function Get-SaasTexte($d) { (Get-SaasLignes $d) -join ' ' }

function Get-EmbedSaasDiscord { New-EmbedSaas (Get-SaasDonnees) }

# ---------- Briefing du matin (embed dans le salon principal) ----------
function Get-BriefingConfig {
    # briefing_actif ("oui" / "non", défaut "non") et briefing_heure ("HH:mm", défaut 07:30)
    $oui = @('oui', 'true', '1', 'on', 'yes')
    $actif = $false; if ($Config.PSObject.Properties['briefing_actif'] -and "$($Config.briefing_actif)".Trim().ToLower() -in $oui) { $actif = $true }
    $h = '07:30'; if ($Config.PSObject.Properties['briefing_heure'] -and "$($Config.briefing_heure)" -match '^([01]?\d|2[0-3]):([0-5]\d)$') { $h = ('{0:00}:{1}' -f [int]$Matches[1], $Matches[2]) }
    @{ actif = $actif; heure = $h }
}

function New-EmbedBriefingMatinSaas([datetime]$now = (Get-Date)) {
    $d = Get-SaasDonnees $now
    $m = Get-MeteoBriefing
    $intro = "$(Get-SalutationHeure $now), voici votre briefing du $($now.ToString('dddd d MMMM', [Globalization.CultureInfo]::GetCultureInfo('fr-FR')))."
    New-EmbedSaas $d 'Briefing du matin' $intro $m
}

function Send-BriefingMatinSaas {
    # Poste le briefing dans le salon principal via le pont. Retourne $true si le message est parti.
    $e = New-EmbedBriefingMatinSaas
    $ok = Send-MessageDiscord 'jarvis' '' '' $e
    Write-Journal -Action 'Briefing du matin (Discord)' -Resultat $(if ($ok) { 'embed envoyé dans le salon principal' } else { 'non envoyé (pont arrêté ou salon introuvable)' })
    $ok
}

function Update-BriefingMatinSaas {
    # Appelée par l'entretien Discord : à briefing_heure (jusqu'à 4 h après), une seule fois par jour, seulement si briefing_actif = "oui".
    $c = Get-BriefingConfig
    if (-not $c.actif -or -not $script:DiscordPumpActif) { return $false }
    $now = Get-Date; $auj = $now.ToString('yyyy-MM-dd')
    $h = [datetime]::ParseExact("$auj $($c.heure)", 'yyyy-MM-dd HH:mm', $null)
    if ($now -lt $h -or $now -gt $h.AddHours(4)) { return $false }
    $o = Read-JsonMemoire 'briefing-matin-saas.json'; if ($o -and "$($o.date)" -eq $auj) { return $false }
    Save-JsonMemoire 'briefing-matin-saas.json' ([ordered]@{ date = $auj })
    [void](Send-BriefingMatinSaas)
    $true
}

function Invoke-BriefingTest {
    # jarvis.ps1 briefing-test : construit le briefing MAINTENANT et le poste dans le salon principal (bot, appel direct : le pont n'a pas besoin de tourner).
    # Retourne le texte de résultat. Rien n'est lu en dehors des sources branchées.
    $e = New-EmbedBriefingMatinSaas
    $f = Join-Path $env:TEMP ('jarvis-briefing-' + [guid]::NewGuid().ToString('N').Substring(0, 8) + '.json')
    [IO.File]::WriteAllText($f, ($e | ConvertTo-Json -Depth 6), [Text.UTF8Encoding]::new($false))
    try {
        $o = (& python -I (Join-Path $script:RacineReelle 'pont-discord\notifier.py') --racine $script:RacineReelle --salon jarvis --embed $f 2>&1 | Out-String).Trim()
    } finally { Remove-Item $f -Force -ErrorAction SilentlyContinue }
    $o = Hide-Secrets $o
    Write-Journal -Action 'Briefing du matin (test)' -Resultat (Short $o 200)
    $o
}
