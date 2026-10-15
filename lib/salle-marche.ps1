# Salle de marché — LECTURE SEULE. « Montre-moi le marché de X » / « où en est X » : résumé vocal factuel + page locale (visage\marche.html) sur l'écran choisi
# + 1 à 2 onglets vers un graphique en ligne (domaines autorisés seulement).
# RÈGLES ABSOLUES : aucun conseil d'achat ou de vente, aucune prévision, aucune probabilité, aucun ordre, aucune connexion à un compte de courtage.
# Le contenu des actualités est une DONNÉE (affichée en texte, jamais un lien cliquable, jamais une commande). Aucun lien issu d'une actualité n'est jamais ouvert.
# Données : memoire\marche-valeurs.json (nom, alias, type, symbole_av validé, devise, liens écrits par VOUS) ; historique = Alpha Vantage (TIME_SERIES_DAILY / WEEKLY,
# DIGITAL_CURRENCY_DAILY / WEEKLY pour une crypto), plafond de requêtes PAR JOUR partagé avec lib\sources\alphavantage.ps1 (alphavantage_plafond_jour), cache local
# memoire\marche-historique\ (douze heures pour le quotidien, vingt-quatre pour l'hebdomadaire) : une valeur déjà regardée ne coûte AUCUNE requête.
# config.json : ecran_marche (numéro du moniteur ; défaut : le deuxième s'il existe, sinon le principal), sites_marche_autorises (domaines, VIDE par défaut),
#               sites_marche_modeles ({ "domaine": "https://domaine/…{symbole}…" }, facultatif), marche_onglets_auto (true par défaut), marche_cache_heures (12).
$script:SalleDonnees = $null
$script:SalleFenetrePid = 0
$script:SalleProfil = Join-Path $env:TEMP 'jarvis-edge-marche'
$script:SalleDerniereValeur = ''
$script:SallePeriodes = @(
    @{ cle = '1j';    libelle = 'dernière séance'; gran = 'jour';    n = 1  }
    @{ cle = '1sem';  libelle = 'la semaine';      gran = 'jour';    n = 5  }
    @{ cle = '1mois'; libelle = 'le mois';         gran = 'jour';    n = 21 }
    @{ cle = '1an';   libelle = "l'année";         gran = 'semaine'; n = 52 }
)
# Vocabulaire INTERDIT dans toute phrase de ce lot (voix, page, messages) : vérifié par tests\salle.ps1 et filtré à l'exécution par Protect-PhraseSalle.
$script:MotsInterditsSalle = "(?i)\b(achet\w*|achat\w*|vend\w*|vente\w*|conseil\w*|recommand\w*|prévi\w*|prévoi\w*|prédi\w*|probab\w*|opportunit\w*|devrait|pourrait|va (monter|descendre|baisser|augmenter|grimper|chuter|rebondir|remonter)|vont (monter|descendre|baisser)|haussier\w*|baissier\w*|potentiel|objectif de cours|renforc\w*|allég\w*|sous-évalu\w*|surévalu\w*|signal d)\b"

function Protect-PhraseSalle([string]$t) {
    # Filet : une phrase qui contiendrait du vocabulaire de conseil ou de prévision n'est jamais dite telle quelle.
    if ("$t" -match $script:MotsInterditsSalle) { Write-Journal -Action 'Salle de marché' -Resultat 'phrase écartée (vocabulaire de conseil ou de prévision)'; return "Je m'en tiens aux chiffres datés et sourcés, monsieur." }
    $t
}

# ---------- Valeur, symbole validé, quota ----------
function Get-ValeurMarche([string]$texte) { Find-ValeurSuivie $texte }
function Get-SymboleValide($v) {
    # Symbole Alpha Vantage VALIDÉ : config.json alphavantage_symboles (rempli après `jarvis.ps1 avtest`) ou « symbole_av » de memoire\marche-valeurs.json. Jamais deviné.
    if ($Config.PSObject.Properties['alphavantage_symboles'] -and $Config.alphavantage_symboles) {
        foreach ($p in $Config.alphavantage_symboles.PSObject.Properties) { if ((ConvertTo-NormMarche $p.Name) -eq (ConvertTo-NormMarche $v.nom) -and "$($p.Value)".Trim()) { return "$($p.Value)".Trim() } }
    }
    if ($v.ContainsKey('symbole_av') -and "$($v.symbole_av)".Trim()) { return "$($v.symbole_av)".Trim() }
    ''
}
function Get-InfoQuotaSalle {
    # @{ n; plafond; presque } — « presque atteint » à partir de 80 % du plafond du jour (ou 2 requêtes avant).
    $plaf = Get-AvPlafond; $e = Read-AvEtat (Get-AvHeureParis)
    @{ n = [int]$e.n; plafond = [int]$plaf; presque = ([int]$e.n -ge [math]::Max(1, [math]::Min([math]::Ceiling($plaf * 0.8), $plaf - 2))) }
}

# ---------- Historique (cache local, plafond de requêtes) ----------
function Get-DirHistoriqueMarche { $d = Split-Path (Get-FichierMemoire 'marche-historique\x'); if (-not (Test-Path $d)) { New-Item -ItemType Directory $d -Force | Out-Null }; $d }
function Get-CacheHeures { $h = 12; if ($Config.PSObject.Properties['marche_cache_heures'] -and "$($Config.marche_cache_heures)" -match '^\d+$') { $h = [math]::Max(1, [math]::Min(72, [int]$Config.marche_cache_heures)) }; $h }
function Get-FichierHistorique([string]$symbole, [string]$gran) { Join-Path (Get-DirHistoriqueMarche) (("{0}-{1}.json" -f ($symbole -replace '[^A-Za-z0-9._-]', '_'), $gran)) }

function ConvertFrom-ReponseSerieAv($r) {
    # Réponse Alpha Vantage -> points triés @{ t; o; h; l; c }. $null si la réponse n'a pas de série.
    $serie = $null
    foreach ($p in $r.PSObject.Properties) { if ($p.Name -match '^(Time Series|Weekly Time Series)') { $serie = $p.Value; break } }
    if (-not $serie) { return $null }
    $pts = @()
    foreach ($j in $serie.PSObject.Properties) {
        $d = [datetime]::MinValue; if (-not [datetime]::TryParseExact($j.Name, 'yyyy-MM-dd', [Globalization.CultureInfo]::InvariantCulture, [Globalization.DateTimeStyles]::None, [ref]$d)) { continue }
        $val = @{}; foreach ($k in 'open', 'high', 'low', 'close') { $pr = $j.Value.PSObject.Properties | Where-Object { $_.Name -match "^\d[ab]?\. $k" } | Select-Object -First 1; if ($pr) { $val[$k] = ConvertTo-NombreFr "$($pr.Value)" } }
        if ($null -eq $val['close']) { continue }
        $pts += [pscustomobject]@{ t = $d.ToString('yyyy-MM-dd'); o = $val['open']; h = $val['high']; l = $val['low']; c = $val['close'] }
    }
    @($pts | Sort-Object t)
}

function Get-HistoriqueValeur($v, [string]$symbole, [string]$gran) {
    # @{ ok; points; maj; source; cache; perime; raison }. Cache d'abord ; sinon UNE requête (comptée AVANT l'appel, plafond du jour respecté) ; cache périmé en dernier recours.
    $f = Get-FichierHistorique $symbole $gran
    $c = $null; if (Test-Path $f) { try { $c = Get-Content $f -Raw -Encoding UTF8 | ConvertFrom-Json } catch { $c = $null } }
    $ttl = (Get-CacheHeures) * $(if ($gran -eq 'semaine') { 2 } else { 1 })
    $age = if ($c) { ((Get-Date) - (ConvertTo-DateMarche $c.maj)).TotalHours } else { 1e9 }
    if ($c -and $age -lt $ttl) { return @{ ok = $true; points = @($c.points); maj = "$($c.maj)"; source = "$($c.source)"; cache = $true; perime = $false; raison = '' } }
    $paris = Get-AvHeureParis; $plaf = Get-AvPlafond; $e = Read-AvEtat $paris
    $secours = { param($raison) if ($c) { @{ ok = $true; points = @($c.points); maj = "$($c.maj)"; source = "$($c.source)"; cache = $true; perime = $true; raison = $raison } } else { @{ ok = $false; points = @(); raison = $raison } } }
    if (-not (Get-AvCle)) { return (& $secours 'clé ALPHAVANTAGE_KEY absente dans .env') }
    if ($e.n -ge $plaf) { return (& $secours "quota du jour atteint ($($e.n)/$plaf)") }
    $crypto = ("$($v.type)" -eq 'crypto')
    $fn = if ($crypto) { if ($gran -eq 'semaine') { 'DIGITAL_CURRENCY_WEEKLY' } else { 'DIGITAL_CURRENCY_DAILY' } } else { if ($gran -eq 'semaine') { 'TIME_SERIES_WEEKLY' } else { 'TIME_SERIES_DAILY' } }
    $params = if ($crypto) { @{ symbol = $symbole; market = $(if ($v.ContainsKey('devise') -and $v.devise) { $v.devise } else { 'EUR' }) } } else { @{ symbol = $symbole } }
    if (-not $crypto -and $gran -eq 'jour') { $params['outputsize'] = 'compact' }
    $e.n++; Save-AvEtat $e
    try { $r = Get-AvReponse $fn $params } catch { return (& $secours "Alpha Vantage indisponible ($(Get-AvCauseErreur $_))") }
    if ($r.PSObject.Properties['Note'] -or $r.PSObject.Properties['Information']) { $e.n = $plaf; Save-AvEtat $e; return (& $secours 'limite de requêtes signalée par Alpha Vantage') }
    if ($r.PSObject.Properties['Error Message']) { return (& $secours "symbole « $symbole » refusé par Alpha Vantage (lancez jarvis.ps1 avtest)") }
    $pts = ConvertFrom-ReponseSerieAv $r
    if (-not $pts -or $pts.Count -lt 2) { return (& $secours "aucune série pour « $symbole » (symbole inconnu ou non couvert)") }
    $pts = @($pts | Select-Object -Last 260)
    $maj = (Get-Date).ToString('o')
    [IO.File]::WriteAllText($f, ([ordered]@{ symbole = $symbole; gran = $gran; maj = $maj; source = 'Alpha Vantage'; points = $pts } | ConvertTo-Json -Depth 4), [Text.UTF8Encoding]::new($false))
    @{ ok = $true; points = $pts; maj = $maj; source = 'Alpha Vantage'; cache = $false; perime = $false; raison = '' }
}

# ---------- Chiffres factuels : variation, plus haut / plus bas, moyennes mobiles ----------
function Get-StatsPeriode($points, [int]$n) {
    # Les n dernières séances : variation = dernière clôture contre la clôture qui précède ces séances. $null s'il manque des points (rien n'est extrapolé).
    $p = @($points); if ($p.Count -lt $n + 1) { return $null }
    $fen = @($p | Select-Object -Last ($n + 1)); $base = $fen[0]; $fin = $fen[-1]; $seance = @($fen | Select-Object -Skip 1)
    $haut = ($seance | Sort-Object { [double]$(if ($null -ne $_.h) { $_.h } else { $_.c }) } -Descending | Select-Object -First 1); $bas = ($seance | Sort-Object { [double]$(if ($null -ne $_.l) { $_.l } else { $_.c }) } | Select-Object -First 1)
    @{ n = $n; points = @($fen | ForEach-Object { @{ t = "$($_.t)"; c = [double]$_.c } }); debut = @{ date = "$($base.t)"; c = [double]$base.c }; fin = @{ date = "$($fin.t)"; c = [double]$fin.c }
       variation_pct = [math]::Round(([double]$fin.c / [double]$base.c - 1) * 100, 2)
       haut = @{ v = [double]$(if ($null -ne $haut.h) { $haut.h } else { $haut.c }); date = "$($haut.t)" }; bas = @{ v = [double]$(if ($null -ne $bas.l) { $bas.l } else { $bas.c }); date = "$($bas.t)" } }
}
function Get-ReperesMoyennes($pointsJour) {
    # Position du dernier cours par rapport aux moyennes mobiles à 20 et 50 séances, 200 si l'historique est assez long. Faits datés, sans interprétation.
    $p = @($pointsJour); $res = @()
    if (-not $p.Count) { return $res }
    $der = $p[-1]
    foreach ($k in 20, 50, 200) {
        if ($p.Count -lt $k) { $res += @{ libelle = "moyenne mobile $k séances"; disponible = $false; note = "indisponible (historique de $($p.Count) séances seulement)"; date = "$($der.t)" }; continue }
        $mm = (@($p | Select-Object -Last $k) | Measure-Object c -Average).Average
        $ecart = [math]::Round(([double]$der.c / $mm - 1) * 100, 2)
        $pos = if ([math]::Abs($ecart) -lt 0.05) { 'au niveau de' } elseif ($ecart -gt 0) { 'au-dessus de' } else { 'au-dessous de' }
        $res += @{ libelle = "moyenne mobile $k séances"; disponible = $true; valeur = [math]::Round($mm, 4); position = $pos; ecart_pct = $ecart; date = "$($der.t)" }
    }
    $res
}

# ---------- Phrases (voix) ----------
function Format-PctSalle([double]$x) { ([math]::Abs($x)).ToString('0.0#', $script:MarcheFr) + ' %' }
function Get-VerbeVariation([double]$x) { if ([math]::Abs($x) -lt 0.05) { 'est stable' } elseif ($x -gt 0) { 'progresse' } else { 'recule' } }
function Get-FragmentVariation($nom, [double]$x, [string]$periode) {
    if ([math]::Abs($x) -lt 0.05) { return "$nom est stable $periode" }
    "$nom $(Get-VerbeVariation $x) de $(Format-PctSalle $x) $periode"
}
function Get-PhraseSalle($b) {
    # « Thales recule de 3,2 % sur la semaine et progresse de 1,1 % sur le mois, monsieur. Source Alpha Vantage, au 12/10. » — chiffres seulement.
    $s1 = $b.periodes['1sem']; $s2 = $b.periodes['1mois']; $s0 = $b.periodes['1j']; $nom = $b.nom
    $dateTxt = $null
    $parts = @()
    if ($s1 -and $s2) { $parts += ((Get-FragmentVariation $nom $s1.variation_pct 'sur la semaine') + ' et ' + (Get-VerbeVariation $s2.variation_pct) + $(if ([math]::Abs($s2.variation_pct) -ge 0.05) { ' de ' + (Format-PctSalle $s2.variation_pct) } else { '' }) + ' sur le mois, monsieur.') }
    elseif ($s1) { $parts += ((Get-FragmentVariation $nom $s1.variation_pct 'sur la semaine') + ', monsieur.') }
    elseif ($s0) { $parts += ((Get-FragmentVariation $nom $s0.variation_pct 'sur la dernière séance') + ', monsieur.') }
    $ref = if ($s0) { $s0 } elseif ($s1) { $s1 } else { $s2 }
    if ($ref) {
        $dateTxt = ([datetime]::ParseExact($ref.fin.date, 'yyyy-MM-dd', $null)).ToString('dd/MM')
        $dev = if ($b.devise) { " $($b.devise)" } else { '' }
        $parts += ("Dernier cours : " + ([double]$ref.fin.c).ToString('0.####', $script:MarcheFr) + "$dev.")
    }
    $m = @($b.reperes | Where-Object { $_.disponible } | Select-Object -First 1)
    if ($m.Count) { $parts += ("Il est $($m[0].position) sa $($m[0].libelle -replace 'moyenne mobile (\d+) séances', 'moyenne à $1 séances') ($(Format-PctSalle $m[0].ecart_pct) d'écart).") }
    $parts += ("Source $($b.source)" + $(if ($dateTxt) { ", au $dateTxt" } else { '' }) + $(if ($b.cache_perime) { ' (données du cache, plus anciennes)' } else { '' }) + '.')
    if ($b.quota.presque) { $parts += 'Le quota de requêtes du jour est presque atteint.' }
    Protect-PhraseSalle ($parts -join ' ')
}

# ---------- Construction des données de la page ----------
function Get-ActusSalle($v, [int]$max = 5) {
    # Actualités déjà relevées par la veille (sources validées), texte seulement : titre, source, date. Aucune adresse n'est conservée.
    $r = Read-DernierReleve; if (-not $r) { return @() }
    @(Select-ActusValeur $r.actus $v $max | ForEach-Object { @{ titre = (Short (Hide-Secrets "$($_.titre)") 160); source = "$($_.source)"; date = "$($_.date)" } })
}
function New-DonneesSalle($v, [string]$symbole) {
    # @{ ok; donnees; raison } — jusqu'à DEUX requêtes (quotidien + hebdomadaire), souvent zéro grâce au cache.
    $j = Get-HistoriqueValeur $v $symbole 'jour'
    if (-not $j.ok) { return @{ ok = $false; raison = $j.raison } }
    $w = Get-HistoriqueValeur $v $symbole 'semaine'
    $per = [ordered]@{}
    foreach ($p in $script:SallePeriodes) {
        $src = if ($p.gran -eq 'semaine') { $w } else { $j }
        if (-not $src.ok) { continue }
        $st = Get-StatsPeriode $src.points $p.n
        if ($st) { $st.libelle = $p.libelle; $per[$p.cle] = $st }
    }
    if (-not $per.Count) { return @{ ok = $false; raison = "historique trop court pour $($v.nom)" } }
    $avert = @(); if ($j.perime) { $avert += "données quotidiennes du cache (plus anciennes) : $($j.raison)" }; if ($w.ok -and $w.perime) { $avert += "données hebdomadaires du cache (plus anciennes) : $($w.raison)" }; if (-not $w.ok) { $avert += "historique de l'année indisponible : $($w.raison)" }
    $q = Get-InfoQuotaSalle
    $b = @{ nom = $v.nom; symbole = $symbole; type = $(if ($v.ContainsKey('type')) { $v.type } else { 'action' }); devise = $(if ($v.ContainsKey('devise')) { $v.devise } else { '' })
            maj = "$($j.maj)"; source = "$($j.source)"; cache = [bool]$j.cache; cache_perime = [bool]($j.perime -or $w.perime); quota = $q; avertissements = $avert
            periodes = $per; reperes = @(Get-ReperesMoyennes $j.points); actus = @(Get-ActusSalle $v) }
    $b.phrase = Get-PhraseSalle $b
    @{ ok = $true; donnees = $b }
}
function Get-DonneesSalleMarche { if ($script:SalleDonnees) { $script:SalleDonnees } else { @{ vide = $true } } }

# ---------- Écran et fenêtre ----------
function Get-EcranMarche {
    # config.json ecran_marche (numéro, comme ecran_jarvis) ; par défaut le deuxième écran (de gauche à droite) s'il existe, sinon le principal.
    $ecrans = @(Get-Ecrans)
    $c = if ($Config.PSObject.Properties['ecran_marche']) { "$($Config.ecran_marche)".Trim() } else { '' }
    if ($c -ne '') { return (Select-Ecran $c $ecrans).ecran }
    if ($ecrans.Count -ge 2) { return ($ecrans | Where-Object { $_.index -eq 1 } | Select-Object -First 1) }
    ($ecrans | Where-Object primaire | Select-Object -First 1)
}
function Test-FenetreMarcheOuverte { $script:SalleFenetrePid -gt 0 -and [bool](Get-Process -Id $script:SalleFenetrePid -ErrorAction SilentlyContinue) }
function Open-FenetreMarche($ecran) {
    # Seam (bouchon dans les tests). Fenêtre Edge --app, profil à part, placée par ses arguments sur la zone de travail de l'écran choisi ; la page s'actualise toute seule.
    if (Test-ModeTest) { $script:PcSim += "salle:fenetre:ecran$($ecran.index)"; return $true }
    if (-not $script:Http -or -not $script:Jeton) { return $false }
    if (Test-FenetreMarcheOuverte) { return $true }
    $edge = (Get-Command msedge -ErrorAction SilentlyContinue).Source; if (-not $edge) { $edge = "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe" }
    if (-not (Test-Path $edge)) { return $false }
    $z = $ecran.zone; $url = "http://127.0.0.1:$([int]$Config.visage_port)/marche?k=$($script:Jeton)"
    $a = @("--app=$url", "--user-data-dir=`"$script:SalleProfil`"", "--window-position=$($z.X),$($z.Y)", "--window-size=$($z.Width),$($z.Height)", '--no-first-run', '--no-default-browser-check', '--disable-extensions', '--disable-sync', '--force-dark-mode')
    $p = Start-Process $edge -ArgumentList $a -PassThru
    $script:SalleFenetrePid = $p.Id
    if (-not ($Config.PSObject.Properties['priorite_cpu_basse'] -and $Config.priorite_cpu_basse -eq $false)) { try { $p.PriorityClass = 'BelowNormal' } catch {} }
    Write-Journal -Action 'Salle de marché' -Resultat "fenêtre ouverte sur $($ecran.peripherique) $($ecran.nom) ($($z.Width)x$($z.Height) en $($z.X),$($z.Y))"
    $true
}
function Stop-FenetreMarche {
    # Ferme uniquement l'Edge lancé pour la salle de marché (son PID et ses enfants).
    if (Test-ModeTest) { if ($script:SalleFenetrePid -gt 0) { $script:PcSim += 'salle:fermee' }; $script:SalleFenetrePid = 0; return }
    try { if ($script:SalleFenetrePid -gt 0) { foreach ($p in (Get-ArbrePids $script:SalleFenetrePid)) { Stop-Process -Id $p -Force -ErrorAction SilentlyContinue } } } catch {}
    $script:SalleFenetrePid = 0
}

# ---------- Onglets : domaines autorisés seulement, liens écrits par VOUS, jamais issus d'une actualité ----------
function Get-DomainesMarcheAutorises { if ($Config.PSObject.Properties['sites_marche_autorises']) { @($Config.sites_marche_autorises | ForEach-Object { ("$_".Trim().ToLowerInvariant() -replace '^https?://', '' -replace '/.*$', '' -replace '^www\.', '') } | Where-Object { $_ }) } else { @() } }
function Test-UrlMarcheAutorisee([string]$url) {
    $u = $null
    if (-not [uri]::TryCreate("$url".Trim(), 'Absolute', [ref]$u) -or $u.Scheme -ne 'https' -or $u.UserInfo) { return $false }
    $h = $u.Host.ToLowerInvariant() -replace '^www\.', ''
    foreach ($d in (Get-DomainesMarcheAutorises)) { if ($h -eq $d -or $h.EndsWith('.' + $d)) { return $true } }
    $false
}
function Get-LiensCandidatsMarche($v) {
    # Liens possibles pour la valeur : « liens » de memoire\marche-valeurs.json (écrits par vous) + modèles de config.json « sites_marche_modeles » ({symbole}).
    $l = @(); if ($v.ContainsKey('liens')) { $l += @($v.liens) }
    $sym = if ($v.ContainsKey('symbole_web') -and $v.symbole_web) { $v.symbole_web } elseif (Get-SymboleValide $v) { Get-SymboleValide $v } else { "$($v.symbole)" }
    if ($sym -and $Config.PSObject.Properties['sites_marche_modeles'] -and $Config.sites_marche_modeles) {
        foreach ($p in $Config.sites_marche_modeles.PSObject.Properties) { if ("$($p.Value)" -match '\{symbole\}') { $l += ("$($p.Value)").Replace('{symbole}', [uri]::EscapeDataString($sym)) } }
    }
    @($l | Where-Object { $_ } | Select-Object -Unique)
}
function Get-LiensAutorisesMarche($v) { @(Get-LiensCandidatsMarche $v | Where-Object { Test-UrlMarcheAutorisee $_ } | Select-Object -First 2) }
function Open-OngletsMarche($urls, $ecran) {
    # Seam (bouchon dans les tests). Une seule NOUVELLE fenêtre du navigateur avec 1 ou 2 onglets, positionnée par ses arguments sur l'écran choisi.
    if (Test-ModeTest) { $script:PcSim += "salle:onglets:$(@($urls).Count):ecran$($ecran.index)"; $script:OngletsOuverts = @($urls); return $true }
    $nav = (Get-Command chrome -ErrorAction SilentlyContinue).Source; if (-not $nav) { $nav = (Get-Command msedge -ErrorAction SilentlyContinue).Source }
    if (-not $nav) { return $false }
    $z = $ecran.zone
    $a = @('--new-window', "--window-position=$($z.X),$($z.Y)", "--window-size=$($z.Width),$($z.Height)") + @($urls)
    Start-Process $nav -ArgumentList $a | Out-Null
    $true
}

# ---------- Actions ----------
function Get-RaisonSalleIndisponible {
    if (-not (Test-MarcheActif)) { return 'le marché est désactivé (marche_actif dans config.json)' }
    if ('alphavantage' -notin (Get-SourcesValideesConfig)) { return "la source Alpha Vantage n'est pas validée (sources_validees)" }
    if (-not (Get-Command Get-AvReponse -ErrorAction SilentlyContinue)) { return 'le module Alpha Vantage est absent (lib\sources)' }
    ''
}
if (Get-Command Add-Action -ErrorAction SilentlyContinue) {
    Add-Action 'salle_marche' 1 'ouvrir la salle de marché d''une valeur' 'salle_marche(nom?) : lecture seule — résumé factuel à voix haute (variation, repères, source, date) et page « salle de marché » sur l''écran choisi pour une valeur de memoire\marche-valeurs.json ; jamais de conseil ni de prévision' {
        param($a)
        $nom = "$($a.nom)".Trim()
        if (-not $nom) { $nom = $script:SalleDerniereValeur }
        if (-not $nom) { return (Rep $false (Get-Politesse 'incompris')) }
        $v = Get-ValeurMarche $nom
        if (-not $v) { return (Rep $false (Get-Politesse 'valeur_inconnue' @{ x = $nom })) }
        $ind = Get-RaisonSalleIndisponible; if ($ind) { return (Rep $false (Get-Politesse 'refus' @{ raison = $ind })) }
        $sym = Get-SymboleValide $v
        if (-not $sym) { return (Rep $false (Get-Politesse 'refus' @{ raison = "le symbole de $($v.nom) n'est pas validé (jarvis.ps1 avtest)" })) }
        $r = New-DonneesSalle $v $sym
        if (-not $r.ok) { return (Rep $false (Get-Politesse 'refus' @{ raison = $r.raison })) }
        $script:SalleDonnees = $r.donnees; $script:SalleDerniereValeur = $v.nom
        Write-Journal -Action 'Salle de marché' -Resultat "$($v.nom) ($sym) : $(@($r.donnees.periodes.Keys) -join ', ')$(if ($r.donnees.cache) { ' (cache)' })"
        $ecran = Get-EcranMarche
        if (-not (Open-FenetreMarche $ecran)) { Write-Journal -Action 'Salle de marché' -Resultat 'fenêtre non ouverte (affichage Jarvis désactivé ou Edge introuvable)' }
        $auto = -not ($Config.PSObject.Properties['marche_onglets_auto'] -and $Config.marche_onglets_auto -eq $false)
        if ($auto) { $liens = @(Get-LiensAutorisesMarche $v); if ($liens.Count) { [void](Open-OngletsMarche $liens $ecran) } }
        Rep $true $r.donnees.phrase
    } { param($a) "salle de marché : $($a.nom)" }

    Add-Action 'salle_marche_fermer' 1 'fermer la salle de marché' 'salle_marche_fermer() : ferme la fenêtre de la salle de marché (jamais un autre programme)' {
        param($a) Stop-FenetreMarche; Rep $true (Get-Politesse 'fait')
    } { param($a) 'fermer la salle de marché' }

    # Niveau 1 si au moins un lien est dans un domaine autorisé (ou s'il n'y a aucun lien à ouvrir) ; sinon refus poli (niveau 3, décidé par le code).
    Add-Action 'marche_onglets' { param($a)
        $v = Get-ValeurMarche "$($a.nom)"; if (-not $v) { return 1 }
        $c = @(Get-LiensCandidatsMarche $v); if (-not $c.Count) { return 1 }
        if (@(Get-LiensAutorisesMarche $v).Count) { 1 } else { 3 }
    } 'ce site de marché n''est pas dans ma liste autorisée (sites_marche_autorises)' 'marche_onglets(nom) : ouvre 1 à 2 onglets vers un graphique en ligne de la valeur, uniquement vers les domaines de sites_marche_autorises ; jamais un lien issu d''une actualité' {
        param($a)
        $v = Get-ValeurMarche "$($a.nom)"; if (-not $v) { return (Rep $false (Get-Politesse 'valeur_inconnue' @{ x = "$($a.nom)" })) }
        $liens = @(Get-LiensAutorisesMarche $v)
        if (-not $liens.Count) { return (Rep $false (Get-Politesse 'refus' @{ raison = "aucun lien de graphique configuré pour $($v.nom)" })) }
        if (-not (Open-OngletsMarche $liens (Get-EcranMarche))) { return (Rep $false (Get-Politesse 'refus' @{ raison = 'aucun navigateur trouvé' })) }
        Write-Journal -Action 'Salle de marché : onglets' -Resultat "$($v.nom) : $(@($liens | ForEach-Object { ([uri]$_).Host }) -join ', ')"
        Rep $true (Get-Politesse 'fait_action' @{ x = "j'ouvre le graphique de $($v.nom)" })
    } { param($a) "ouvrir les onglets de marché de $($a.nom)" }
}
