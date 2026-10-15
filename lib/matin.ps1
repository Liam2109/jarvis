# Briefing du matin AVEC RATTRAPAGE.
# Au premier démarrage de Jarvis de la journée (aucun briefing déjà fait aujourd'hui, mémorisé dans memoire\briefing-jour.json), Jarvis prépare un briefing
# de tout ce qui s'est passé depuis sa dernière fermeture (heure mémorisée dans memoire\arret.json) :
#   (a) mon SaaS via jarvis_stats, avec la comparaison « depuis hier » ; (b) actualités et marché retenus par la veille de fond (valeurs suivies d'abord) ;
#   (c) alertes graves et rappels retenus pendant la sourdine ou le mode jeu.
# Il s'affiche TOUJOURS au tableau dès le démarrage, SANS voix. Il n'est dit qu'une seule fois, à la première activation (Alt + +) de la journée, si
# "briefing_vocal" est true (défaut) — jamais en sourdine ni en mode jeu. Commandes : « relis le briefing », « briefing de la nuit ».
# Une source indisponible donne « indisponible (cause) » sur sa ligne, sans bloquer le reste.
$script:BriefingMatin = $null

function Save-HeureArret { Save-JsonMemoire 'arret.json' ([ordered]@{ arret = (Get-Date).ToString('o') }) }
function Get-DepuisBriefing([datetime]$now = (Get-Date)) {
    $o = Read-JsonMemoire 'arret.json'
    $d = if ($o -and $o.arret) { ConvertTo-DateMarche $o.arret } else { [datetime]::MinValue }
    if ($d -eq [datetime]::MinValue -or $d -ge $now) { return $now.AddHours(-24) }
    if (($now - $d).TotalDays -gt 7) { return $now.AddDays(-7) }
    $d
}
function Get-BriefingVocalActif {
    # briefing_vocal : true (défaut) / false, ou l'ancienne forme { "actif": true }.
    $b = $Config.briefing_vocal
    if ($null -eq $b) { return $true }
    if ($b -is [bool]) { return $b }
    if ($b.PSObject.Properties['actif']) { return [bool]$b.actif }
    $true
}

# ---------- (a) Mon SaaS ----------
$script:MetriquesSaas = @(@('quiz_24h', 'Nouveaux quiz'), @('emails_24h', 'E-mails récupérés'), @('nouveaux_abonnes_24h', 'Nouveaux abonnés'), @('abonnes_en_annulation', 'Abonnés en annulation'),
    @('paiements_echoues', 'Paiements échoués'), @('demandes_retractation_a_traiter', 'Demandes de rétractation à traiter'))
function Get-LignesSaas($saas, $hier) {
    # Fonction PURE. $saas : hashtable des totaux lus ; $hier : relevé de la veille (objet ou hashtable) ou $null.
    $l = @()
    foreach ($m in $script:MetriquesSaas) {
        $k = $m[0]
        if (-not $saas.ContainsKey($k)) { $l += "$($m[1]) : indisponible (champ absent de jarvis_stats)."; continue }
        $v = [int64]$saas[$k]; $h = $null
        if ($hier -is [hashtable]) { if ($hier.ContainsKey($k)) { $h = [int64]$hier[$k] } }
        elseif ($hier) { $p = $hier.PSObject.Properties[$k]; if ($p -and $null -ne $p.Value -and "$($p.Value)" -match '^-?\d+$') { $h = [int64]$p.Value } }
        $cmp = if ($null -eq $h) { "pas de relevé d'hier pour comparer" } else { $d = $v - $h; "depuis hier : $h, " + $(if ($d -gt 0) { "+$d" } elseif ($d -lt 0) { "$d" } else { 'inchangé' }) }
        $l += "$($m[1]) : $v ($cmp)."
    }
    $l
}
function Get-HierSaas([datetime]$now = (Get-Date)) {
    $o = Read-JsonMemoire 'saas-releves.json'; if (-not $o -or -not $o.PSObject.Properties['jours']) { return $null }
    $auj = $now.ToString('yyyy-MM-dd')
    $k = @($o.jours.PSObject.Properties.Name | Where-Object { $_ -lt $auj } | Sort-Object -Descending | Select-Object -First 1)
    if ($k.Count) { $o.jours.($k[0]) } else { $null }
}
function Save-ReleveSaas($saas, [datetime]$now = (Get-Date)) {
    $o = Read-JsonMemoire 'saas-releves.json'; $jours = [ordered]@{}
    if ($o -and $o.PSObject.Properties['jours']) { foreach ($p in ($o.jours.PSObject.Properties | Sort-Object Name | Select-Object -Last 6)) { $jours[$p.Name] = $p.Value } }
    $j = [ordered]@{}; foreach ($m in $script:MetriquesSaas) { if ($saas.ContainsKey($m[0])) { $j[$m[0]] = [int64]$saas[$m[0]] } }
    foreach ($k in 'abonnes_actifs', 'quiz_total') { if ($saas.ContainsKey($k)) { $j[$k] = [int64]$saas[$k] } }      # pour le taux de conversion « depuis hier »
    $jours[$now.ToString('yyyy-MM-dd')] = $j
    Save-JsonMemoire 'saas-releves.json' ([ordered]@{ jours = $jours })
}

# ---------- (b) Actualités et marché ----------
function Get-LignesMarcheBriefing([datetime]$depuis) {
    if (-not (Test-MarcheActif) -or -not (Get-SourcesValideesConfig).Count) { return @('Actualités et marché : source non branchée (aucune source validée).') }
    $d = Read-RelevesDepuis $depuis
    if (-not $d.releves) { return @('Actualités et marché : indisponible (aucun relevé de la veille de fond depuis votre dernière fermeture).') }
    $l = @('Actualités et marché depuis votre dernière fermeture :')
    $vues = @{}
    foreach ($v in (Get-ValeursSuivies)) {
        $c = Select-CoursValeur $d.cours $v
        $a = @(Select-ActusValeur $d.actus $v 2)
        foreach ($x in $a) { $vues[(ConvertTo-NormMarche "$($x.source) $($x.titre)")] = $true }
        if ($c) { $l += Get-PhraseCours $c } else { $l += "$($v.nom) : cours indisponible dans vos sources." }
        foreach ($x in $a) { $l += "  $(Get-PhraseActu $x)" }
    }
    $g = @($d.actus | Where-Object { -not $vues.ContainsKey((ConvertTo-NormMarche "$($_.source) $($_.titre)")) } | Select-Object -First 3)
    if ($g.Count) { $l += 'Marché général : ' + (($g | ForEach-Object { Get-PhraseActu $_ }) -join ' ') } elseif (-not @($d.actus).Count) { $l += 'Aucune actualité nouvelle dans vos sources.' }
    $l
}

# ---------- (c) Alertes graves et rappels retenus ----------
function Get-LignesRetenus([datetime]$depuis, [datetime]$now = (Get-Date)) {
    $l = @()
    $h = Read-AlertesVues
    foreach ($k in $h.Keys) {
        $e = $h[$k]; if (-not $e.grave -or $e.ignoree) { continue }
        $dt = ConvertTo-DateMarche $e.derniere_vue
        if ($dt -ge $depuis) { $l += "Alerte grave : $($e.titre) (vue le $($dt.ToString('dd/MM à HH:mm')))." }
    }
    foreach ($r in @(Get-Rappels)) {
        if ($r.fait) { continue }
        $q = [datetime]::MinValue
        if ([datetime]::TryParseExact("$($r.quand)", 'yyyy-MM-dd HH:mm', [Globalization.CultureInfo]::InvariantCulture, [Globalization.DateTimeStyles]::None, [ref]$q) -and $q -le $now -and $q -ge $depuis) { $l += "Rappel manqué : $($r.texte) (prévu le $($q.ToString('dd/MM à HH:mm')))." }
    }
    foreach ($x in $script:Retenu.ToArray()) { if ($x.type -in 'rappel', 'alerte') { $l += "$(if ($x.type -eq 'rappel') { 'Rappel retenu' } else { 'Alerte grave retenue' }) : $($x.texte) ($($x.heure))." } }
    if (-not $l.Count) { return @('Alertes graves et rappels : rien de retenu depuis votre dernière fermeture.') }
    @('Alertes graves et rappels retenus :') + $l
}

# ---------- Le briefing COURT (5 lignes au plus) + les détails à la demande ----------
function Format-PctFr([double]$v) { $v.ToString('0.#', [Globalization.CultureInfo]::GetCultureInfo('fr-FR')) }
function Get-TauxConversion($saas, $hier) {
    # Fonction PURE. Taux de conversion = abonnés actifs / quiz (cumul), en %. Comparaison « depuis hier » si le relevé d'hier a les deux chiffres.
    if (-not $saas -or -not $saas.ContainsKey('abonnes_actifs') -or -not $saas.ContainsKey('quiz_total') -or [int64]$saas['quiz_total'] -le 0) { return @{ dispo = $false; raison = 'quiz ou abonnés actifs absents de jarvis_stats' } }
    $pct = [double]$saas['abonnes_actifs'] / [double]$saas['quiz_total'] * 100
    $h = $null
    if ($hier) { $a = $hier.PSObject.Properties['abonnes_actifs']; $q = $hier.PSObject.Properties['quiz_total']; if ($a -and $q -and [int64]$q.Value -gt 0) { $h = [double]$a.Value / [double]$q.Value * 100 } }
    @{ dispo = $true; pct = $pct; hier = $h; delta = $(if ($null -ne $h) { $pct - $h } else { $null }) }
}
function Format-ConversionLigne($t) {
    if (-not $t.dispo) { return "Taux de conversion : indisponible ($($t.raison))." }
    $cmp = if ($null -eq $t.hier) { 'pas de relevé d''hier pour comparer' } else { $d = [math]::Round($t.delta, 1); "hier $(Format-PctFr $t.hier) %, " + $(if ($d -gt 0) { "+$(Format-PctFr $d) point" } elseif ($d -lt 0) { "$(Format-PctFr $d) point" } else { 'inchangé' }) }
    "Taux de conversion : $(Format-PctFr $t.pct) % (abonnés actifs / quiz ; $cmp)."
}
function Get-LignesCourtes($d) {
    # Fonction PURE. $d : stats, hier, ca, marche (ligne ou $null), retractations. Retourne @{ lignes; parle } — 5 lignes au plus.
    $s = $d.stats; $lignes = @(); $parle = @()
    if (-not $s.dispo) {
        $c = "Mon SaaS : indisponible ($(($s.raison -replace '^Supabase : ', '').TrimEnd('.')))."
        $lignes += $c; $parle += "Mon SaaS est indisponible."
    } else {
        $g = $s.saas
        $q = if ($g.ContainsKey('quiz_24h')) { [int64]$g['quiz_24h'] } else { $null }; $n = if ($g.ContainsKey('nouveaux_abonnes_24h')) { [int64]$g['nouveaux_abonnes_24h'] } else { $null }; $a = if ($g.ContainsKey('abonnes_en_annulation')) { [int64]$g['abonnes_en_annulation'] } else { $null }
        $f = { param($v) if ($null -eq $v) { 'n/d' } else { "$v" } }
        $lignes += "Nouveaux quiz : $(& $f $q) · Nouveaux abonnés : $(& $f $n) · En annulation : $(& $f $a)."
        $parle += "$(& $f $q) quiz, $(& $f $n) nouveaux abonné$(if ($n -gt 1) { 's' }), $(& $f $a) en annulation."
    }
    if ($d.ca.dispo) { $m = if ($d.ca.montants.Count) { Format-Montants $d.ca.montants } else { '0 euro' }; $lignes += "Chiffre d'affaires sur la période : $(if ($d.ca.partiel) { 'au moins ' })$m."; $parle += "Chiffre d'affaires : $m." }
    else { $cause = ("$($d.ca.raison)" -replace '^Stripe[^:]*: ', '').TrimEnd('.'); $lignes += "Chiffre d'affaires : indisponible ($cause)."; $parle += "Chiffre d'affaires indisponible." }
    if ($s.dispo) {
        $t = Get-TauxConversion $s.saas $d.hier
        $lignes += Format-ConversionLigne $t
        if ($t.dispo) { $parle += "Conversion : $(Format-PctFr $t.pct) %$(if ($null -ne $t.hier) { ", hier $(Format-PctFr $t.hier)" })." }
    }
    if ($d.marche) { $lignes += $d.marche.ligne }
    if ($s.dispo -and $s.saas.ContainsKey('demandes_retractation_a_traiter') -and [int64]$s.saas['demandes_retractation_a_traiter'] -gt 0) {
        $r = [int64]$s.saas['demandes_retractation_a_traiter']
        $lignes += "Demande$(if ($r -gt 1) { 's' }) de rétractation à traiter : $r."; $parle += "$r demande$(if ($r -gt 1) { 's' }) de rétractation à traiter."
    }
    if ($d.marche -and $d.marche.parle) { $parle += $d.marche.parle }      # en dernier : c'est la première phrase retirée si la version dite dépasse 15 s
    @{ lignes = @($lignes | Select-Object -First 5); parle = @($parle) }
}
function Limit-BriefingDit([string[]]$phrases, [int]$maxMots = 36) {
    # La version dite dure au plus 15 s (≈ 2,6 mots par seconde en voix de synthèse : 36 mots ≈ 14 s). On retire d'abord les dernières phrases ajoutées.
    $l = @($phrases)
    while ($l.Count -gt 2 -and (($l -join ' ') -split '\s+').Count -gt $maxMots) { $l = @($l | Select-Object -First ($l.Count - 1)) }
    $l
}
function Get-DureeDitSecondes([string[]]$phrases) { [math]::Round((((@($phrases) -join ' ') -split '\s+' | Where-Object { $_ }).Count) / 2.6, 1) }
function Get-LigneMarcheCourte {
    # Une ligne marché SEULEMENT s'il y a une source branchée (marché actif + source validée et présente). Sinon $null : aucune ligne.
    if (Get-RaisonMarche) { return $null }
    $r = Read-DernierReleve
    if (-not $r) { return @{ ligne = 'Marché : en attente du premier relevé de la veille de fond.'; parle = '' } }
    $morceaux = @(); $dits = @()
    foreach ($v in (Get-ValeursSuivies | Select-Object -First 3)) {
        $c = Select-CoursValeur $r.cours $v; if (-not $c) { continue }
        $var = if ($null -ne $c.variation_pct -and "$($c.variation_pct)" -ne '') { ' ' + $(if ([double]$c.variation_pct -ge 0) { '+' } else { '' }) + (Format-PctFr ([double]$c.variation_pct)) + ' %' } else { '' }
        $morceaux += "$($v.nom) $(([double]$c.prix).ToString('0.####', $script:MarcheFr)) $(Get-NomDevise $c.devise)$var"
        $dits += "$($v.nom) $(([double]$c.prix).ToString('0.####', $script:MarcheFr))$var"
    }
    if (-not $morceaux.Count) { return @{ ligne = 'Marché : aucun cours dans le dernier relevé.'; parle = '' } }
    @{ ligne = 'Marché : ' + ($morceaux -join ' ; ') + '.'; parle = 'Marché : ' + (($dits | Select-Object -First 2) -join ', ') + '.' }
}

function New-BriefingMatin([datetime]$now = (Get-Date)) {
    $depuis = Get-DepuisBriefing $now
    $quand = if ($depuis.Date -eq $now.Date) { "aujourd'hui à $($depuis.ToString('HH:mm'))" } elseif ($depuis.Date -eq $now.Date.AddDays(-1)) { "hier à $($depuis.ToString('HH:mm'))" } else { "le $($depuis.ToString('dd/MM à HH:mm'))" }
    # --- lectures (une fois) ---
    try { $stats = Get-SupabaseStats $depuis } catch { $stats = @{ dispo = $false; raison = "Supabase : $($_.Exception.Message)" } }
    Write-Journal -Action 'Briefing du matin : lecture Mon SaaS' -Resultat $(if ($stats.dispo) { 'ok' } else { "indisponible : $($stats.raison)" })
    try { $ca = Get-StripeCA $depuis } catch { $ca = @{ dispo = $false; raison = "Stripe : $($_.Exception.Message)" } }
    Write-Journal -Action 'Briefing du matin : lecture chiffre d''affaires' -Resultat $(if ($ca.dispo) { 'ok' } else { "indisponible : $($ca.raison)" })
    $hier = Get-HierSaas $now
    if ($stats.dispo) { Save-ReleveSaas $stats.saas $now }
    $marche = try { Get-LigneMarcheCourte } catch { $null }
    # --- version courte : 5 lignes au plus ---
    $c = Get-LignesCourtes @{ stats = $stats; hier = $hier; ca = $ca; marche = $marche }
    $ouverture = "$(Get-SalutationHeure $now)."
    $parle = Limit-BriefingDit (@($ouverture) + @($c.parle | Where-Object { $_ }))
    # --- détails complets (« détails du briefing ») ---
    $l = @("$(Get-SalutationHeure $now). Voici ce qui s'est passé depuis votre dernière fermeture ($quand).")
    $rappel = if (Get-Command Get-RappelHier -ErrorAction SilentlyContinue) { try { Get-RappelHier } catch { '' } } else { '' }
    if ($rappel) { $l += $rappel }
    if ($stats.dispo) { $l += 'Mon SaaS depuis hier :'; $l += @(Get-LignesSaas $stats.saas $hier) } else { $l += "Mon SaaS : indisponible ($(($stats.raison -replace '^Supabase : ', '').TrimEnd('.')))." }
    $l += $c.lignes | Where-Object { $_ -match "^Chiffre d'affaires|^Taux de conversion" }
    if ($ca.dispo) { $l += "Paiements réussis sur la période : $($ca.paiements)." }
    foreach ($bloc in { Get-LignesMarcheBriefing $depuis }, { Get-LignesRetenus $depuis $now }) {
        try { $l += @(& $bloc) } catch { $l += "Une partie du briefing est indisponible ($($_.Exception.Message -replace '\s+', ' '))."; Write-Journal -Action 'Briefing du matin' -Resultat "bloc indisponible : $($_.Exception.Message)" }
    }
    try {
        $s = Get-StatutSite 8
        $l += $(if ($s.ok) { 'Site tonproduit.shop : en ligne.' } else { "Site tonproduit.shop : hors ligne ou en erreur$(if ($s.code) { " (code $($s.code))" } else { ' (aucune réponse)' })." })
    } catch { $l += 'Site tonproduit.shop : indisponible (vérification impossible).' }
    $todo = @(Get-TodoOuverte); $l += $(if ($todo.Count) { "Tâches ouvertes : $($todo.Count)." } else { 'Liste de tâches vide.' })
    $net = { param($x) if ($x -match '^Mon SaaS') { "$x" } else { Hide-Secrets "$x" } }      # (texte fixe de Mon SaaS : « jeton refusé » ne doit pas être masqué ; le reste vient de sources externes)
    @{ date = $now.ToString('yyyy-MM-dd'); genere = $now.ToString('o'); depuis = $depuis.ToString('o'); dit = $false
       lignes = @($c.lignes | ForEach-Object { & $net $_ }); parle = @($parle | ForEach-Object { & $net $_ }); details = @($l | ForEach-Object { & $net $_ }) }
}
function Save-BriefingMatin { $b = $script:BriefingMatin; Save-JsonMemoire 'briefing-jour.json' ([ordered]@{ date = $b.date; genere = $b.genere; depuis = $b.depuis; dit = [bool]$b.dit; lignes = @($b.lignes); parle = @($b.parle); details = @($b.details) }) }
function Show-BriefingMatin([switch]$Details) {
    $script:BriefingLignes.Clear()
    foreach ($x in @($(if ($Details) { $script:BriefingMatin.details } else { $script:BriefingMatin.lignes }))) { $script:BriefingLignes.Add("$x") }
}

function Initialize-BriefingMatin([datetime]$now = (Get-Date)) {
    # Au démarrage. Retourne $true si un NOUVEAU briefing a été préparé. Ne dit RIEN. Positionne BriefingEnAttente = « à dire à la première activation ».
    $o = Read-JsonMemoire 'briefing-jour.json'
    if ($o -and "$($o.date)" -eq $now.ToString('yyyy-MM-dd') -and $o.lignes -and $o.parle) {
        $script:BriefingMatin = @{ date = "$($o.date)"; genere = "$($o.genere)"; depuis = "$($o.depuis)"; lignes = @($o.lignes | ForEach-Object { "$_" }); parle = @($o.parle | ForEach-Object { "$_" }); details = @($o.details | ForEach-Object { "$_" }); dit = [bool]$o.dit }
        $neuf = $false
    } else {
        $dejaDit = [bool]($o -and "$($o.date)" -eq $now.ToString('yyyy-MM-dd') -and $o.dit)      # ancien format du même jour : on garde « déjà dit »
        $script:BriefingMatin = New-BriefingMatin $now; $script:BriefingMatin.dit = $dejaDit; Save-BriefingMatin; $neuf = $true
        Write-Journal -Action 'Briefing du matin préparé' -Resultat "$(@($script:BriefingMatin.lignes).Count) ligne(s) courtes (version dite ≈ $(Get-DureeDitSecondes $script:BriefingMatin.parle) s), affiché au tableau sans voix ; dit une seule fois à la première activation"
    }
    Show-BriefingMatin
    $script:BriefingEnAttente = ((Get-BriefingVocalActif) -and -not $script:BriefingMatin.dit)
    $neuf
}
function Invoke-BriefingMatinDire([switch]$Demande, [switch]$Details) {
    # Sans -Demande : la première activation de la journée. Jamais en sourdine (on attend), jamais en mode jeu (on renonce pour la journée).
    # -Demande : Liam l'a demandé (« relis le briefing ») : dit à nouveau la version courte. -Details : « détails du briefing » : tout le détail.
    if (-not $script:BriefingMatin) { try { [void](Initialize-BriefingMatin) } catch { Write-Journal -Action 'Briefing du matin' -Resultat "indisponible : $($_.Exception.Message)" } }
    if (-not $script:BriefingMatin) { $script:BriefingEnAttente = $false; return }
    if ($script:Actif -eq $false) { return }
    if (-not $Demande -and -not $Details) {
        $script:BriefingEnAttente = $false
        if ($script:BriefingMatin.dit) { return }
        if ($script:ModeJeu -eq $true) { Write-Journal -Action 'Briefing du matin' -Resultat 'mode jeu : non dit (affiché au tableau seulement)'; $script:BriefingMatin.dit = $true; Save-BriefingMatin; return }
        if (-not (Get-BriefingVocalActif)) { return }
    }
    if ($Details) { Show-BriefingMatin -Details } else { Show-BriefingMatin }
    $texte = if ($Details) { @($script:BriefingMatin.details) } else { @($script:BriefingMatin.parle) }
    Invoke-AvecContexteVoix $(if ($Demande -or $Details) { 'reponse' } else { 'briefing' }) {
        Set-VisageEtat 'reflechit'
        foreach ($x in $texte) { if (Test-Coupure) { break }; Parler (($x -replace '^\s+', '')) }
        Set-VisageEtat 'ecoute'
    }
    if (-not $Demande -and -not $Details) { $script:BriefingMatin.dit = $true; Save-BriefingMatin; Write-Journal -Action 'Briefing du matin' -Resultat 'dit (une seule fois aujourd''hui)' }
}

if (Get-Command Add-Action -ErrorAction SilentlyContinue) {
    Add-Action 'briefing_relire' 1 'relire le briefing du matin' 'briefing_relire() : relit à voix haute la version courte du briefing du matin / de la nuit (depuis la dernière fermeture)' {
        param($a)
        if (-not $script:BriefingMatin) { [void](Initialize-BriefingMatin) }
        Invoke-BriefingMatinDire -Demande
        Rep $true 'Voilà, monsieur.'
    } { param($a) 'relire le briefing' }
    Add-Action 'briefing_details' 1 'donner les détails du briefing' 'briefing_details() : affiche et dit le briefing complet (SaaS, marché, alertes retenues, site, tâches)' {
        param($a)
        if (-not $script:BriefingMatin) { [void](Initialize-BriefingMatin) }
        Invoke-BriefingMatinDire -Details
        Rep $true 'Voilà le détail, monsieur.'
    } { param($a) 'détails du briefing' }
}
