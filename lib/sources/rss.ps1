# Source de marché « rss » : flux RSS/Atom OFFICIELS, lecture seule. Titres + source + date SEULEMENT (jamais d'article copié).
# Les flux sont listés dans config.json "rss_flux" : [ { "nom": "BCE", "url": "https://www.ecb.europa.eu/rss/press.xml" } ]  (https obligatoire).
# La source n'est utilisée que si "rss" figure dans "sources_validees" ET si "marche_actif" est true.
# Politesse : User-Agent honnête, au plus UNE lecture par flux toutes les 15 minutes (cache dans memoire\veille\rss-cache.json, même si
# "rss_minutes" est réglé plus bas), flux illisible = « indisponible (cause) » sans bloquer les autres. Le contenu reçu est une donnée non fiable
# (balises retirées, longueur bornée, DTD interdites). Vérifiez les conditions d'utilisation de CHAQUE flux avant de l'ajouter.
$script:RssUserAgent = 'Jarvis-lecteur-RSS/1.0 (usage personnel, lecture seule, un appel par flux toutes les 15 min)'
$script:RssMinMinutes = 15

function Get-FluxRssConfig {
    @($Config.rss_flux | Where-Object { $_ -and "$($_.nom)".Trim() -and "$($_.url)" -match '^https://[^/\s]+' })
}
function Get-RssMinutes { $m = $script:RssMinMinutes; if ($Config.PSObject.Properties['rss_minutes'] -and "$($Config.rss_minutes)" -match '^\d+$') { $m = [math]::Max($m, [int]$Config.rss_minutes) }; $m }

function Get-FluxRssXml([string]$url) {
    # Seul point réseau du module (remplacé par un bouchon dans les tests). Retourne un XmlDocument ; lève une exception en cas d'échec.
    if (-not (Test-UrlFluxAutorisee $url)) { throw 'adresse refusée (https obligatoire)' }
    $r = Invoke-WebRequest $url -UseBasicParsing -TimeoutSec 15 -Method Get -Headers @{ 'User-Agent' = $script:RssUserAgent; 'Accept' = 'application/rss+xml, application/atom+xml, application/xml;q=0.9, */*;q=0.5' }
    $flot = $r.RawContentStream; $flot.Position = 0
    $reglages = New-Object Xml.XmlReaderSettings; $reglages.DtdProcessing = [Xml.DtdProcessing]::Prohibit; $reglages.XmlResolver = $null
    $lecteur = [Xml.XmlReader]::Create($flot, $reglages)
    $x = New-Object Xml.XmlDocument; $x.XmlResolver = $null; $x.Load($lecteur); $lecteur.Close()
    $x
}

function ConvertFrom-XmlRss($x) {
    # Titres et dates uniquement. @() si le flux est valide mais vide ; lève une exception si ce n'est pas un flux RSS/Atom.
    $noeuds = @($x.SelectNodes('//item')); if (-not $noeuds.Count) { $noeuds = @($x.SelectNodes("//*[local-name()='entry']")) }
    $racine = $x.DocumentElement.LocalName
    if ($racine -notin 'rss', 'feed', 'RDF') { throw 'ce n''est pas un flux RSS/Atom' }
    $res = @()
    foreach ($n in $noeuds) {
        $get = { param($nom) $e = $n.SelectSingleNode("*[local-name()='$nom']"); if ($e) { $e.InnerText } else { '' } }
        $titre = if (Get-Command Format-TexteExterne -ErrorAction SilentlyContinue) { Format-TexteExterne (& $get 'title') 180 } else { "$(& $get 'title')".Trim() }
        $ds = & $get 'pubDate'; if (-not $ds) { $ds = & $get 'published' }; if (-not $ds) { $ds = & $get 'updated' }; if (-not $ds) { $ds = & $get 'date' }
        $dt = [DateTimeOffset]::MinValue
        if (-not $titre -or -not [DateTimeOffset]::TryParse($ds, [Globalization.CultureInfo]::InvariantCulture, [Globalization.DateTimeStyles]::AssumeUniversal, [ref]$dt)) { continue }
        $res += [pscustomobject]@{ titre = $titre; date = $dt.LocalDateTime.ToString('o') }
    }
    $res
}

function Get-RssCause($ex) {
    $c = 0; try { if ($ex.Exception.Response) { $c = [int]$ex.Exception.Response.StatusCode } } catch {}
    if ($c) { return "HTTP $c" }
    $m = "$($ex.Exception.Message)"
    if ($m -match 'refusée|pas un flux') { return $m }
    if ($m -match 'délai|timed? ?out|expiré') { return 'délai dépassé' }
    if ($m -match 'XML|xml|racine|élément|element') { return 'flux illisible' }
    'réseau injoignable'
}

function Get-ActusRss([datetime]$depuis, [datetime]$now = (Get-Date)) {
    $flux = @(Get-FluxRssConfig)
    if (-not $flux.Count) { return @{ dispo = $false; raison = 'aucun flux dans rss_flux (config.json)' } }
    $cacheObj = Read-JsonMemoire 'veille\rss-cache.json'
    $cache = @{}; if ($cacheObj) { foreach ($p in $cacheObj.PSObject.Properties) { $cache[$p.Name] = $p.Value } }
    $items = @(); $avert = @(); $ok = 0; $change = $false
    foreach ($f in $flux) {
        $nom = "$($f.nom)".Trim(); $c = $cache[$nom]; $lu = if ($c) { ConvertTo-DateMarche $c.lu } else { [datetime]::MinValue }
        $liste = $null
        if ($c -and ($now - $lu).TotalMinutes -lt (Get-RssMinutes)) {                                                       # cache : AUCUN appel réseau avant 15 min
            if ($c.erreur) { $avert += "$nom : indisponible ($($c.erreur))" }
            $liste = if ($c.erreur -and -not @($c.items).Count) { $null } else { @($c.items) }
        }
        else {
            try {
                $x = Get-FluxRssXml "$($f.url)"
                $liste = @(ConvertFrom-XmlRss $x | Select-Object -First 40)
                $cache[$nom] = [pscustomobject]@{ lu = $now.ToString('o'); items = @($liste); erreur = '' }; $change = $true
            } catch {
                $cause = Get-RssCause $_
                $avert += Short (Hide-Secrets "$nom : indisponible ($cause)") 120
                $cache[$nom] = [pscustomobject]@{ lu = $now.ToString('o'); items = @($(if ($c) { $c.items })); erreur = $cause }; $change = $true     # on ne réessaie pas avant le délai
                $liste = if ($c) { @($c.items) } else { $null }
            }
        }
        if ($null -ne $liste) {
            $ok++
            foreach ($i in $liste) { if (-not $i) { continue }; $d = ConvertTo-DateMarche $i.date; if ($d -ge $depuis -and $d -le $now.AddDays(30)) { $items += @{ titre = "$($i.titre)"; resume = ''; date = $d.ToString('o'); source = $nom; valeur = '' } } }
        }
    }
    if ($change) { Save-JsonMemoire 'veille\rss-cache.json' $cache }
    if (-not $ok) { return @{ dispo = $false; raison = ($avert -join ' ; ') } }
    @{ dispo = $true; items = @($items); avertissements = @($avert) }
}

Register-SourceMarche -Nom 'rss' -MinSecondes 0 -Actus {
    param($valeurs, [datetime]$depuis)
    Get-ActusRss $depuis
}
