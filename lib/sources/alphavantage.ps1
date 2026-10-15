# Source de marché « alphavantage » : cours via l'API Alpha Vantage (GLOBAL_QUOTE), lecture seule.
# Clé : ALPHAVANTAGE_KEY dans .env (que VOUS renseignez ; jamais affichée, journalisée ni écrite ailleurs).
# Utilisée seulement si "alphavantage" figure dans "sources_validees" ET si "marche_actif" est true.
# Limites respectées par le code :
#   - plafond de requêtes PAR JOUR (config.json "alphavantage_plafond_jour", 20 par défaut ; le compteur est dans memoire\alphavantage-quota.json,
#     une requête est comptée AVANT l'appel, échecs compris) ;
#   - lectures seulement pendant les heures de bourse de Paris, en semaine (9h00-17h30, heure de Paris) ;
#   - intervalle entre deux passes calculé pour ne jamais dépasser le plafond avec vos valeurs suivies (voir Get-AvIntervalleSecondes) ;
#   - hors lecture, les derniers cours connus sont renvoyés tels quels, avec leur date (aucune requête).
# Symboles : "alphavantage_symboles": { "Thales": "...", "Société Générale": "..." } — à renseigner après `jarvis.ps1 avtest` (UN appel SYMBOL_SEARCH
# qui affiche les symboles que le service connaît pour Paris). Aucun symbole n'est deviné.
# NB : sans abonnement, GLOBAL_QUOTE est mis à jour en fin de séance : la variation affichée est celle du DERNIER JOUR DE BOURSE (sa date est affichée ;
# une alerte « aujourd'hui » n'est donc déclenchée que si ce jour est aujourd'hui).
$script:AvMaintenant = $null; $script:AvHeureParis = $null
$script:AvFenetreSecondes = 30600           # 9h00-17h30 = 8 h 30
$script:AvMinIntervalle = 900

function Get-AvHeureParis {
    if ($script:AvHeureParis) { return $script:AvHeureParis }
    $now = if ($script:AvMaintenant) { $script:AvMaintenant } else { Get-Date }
    try { [TimeZoneInfo]::ConvertTime($now, [TimeZoneInfo]::FindSystemTimeZoneById('Romance Standard Time')) } catch { $now }
}
function Test-HeuresBoursePar([datetime]$heureParis) {
    if ($heureParis.DayOfWeek -in 'Saturday', 'Sunday') { return $false }
    $m = $heureParis.Hour * 60 + $heureParis.Minute
    ($m -ge 540 -and $m -lt 1050)
}
function Get-AvPlafond { $p = 20; if ($Config.PSObject.Properties['alphavantage_plafond_jour'] -and "$($Config.alphavantage_plafond_jour)" -match '^\d+$') { $p = [int]$Config.alphavantage_plafond_jour }; [math]::Max(1, [math]::Min(500, $p)) }
function Get-AvIntervalleSecondes([int]$nbValeurs, [int]$plafond) {
    # Une passe = une requête par valeur. Passes possibles dans la journée = plafond / valeurs ; on les répartit sur la séance. Jamais moins de 15 min.
    $passes = [math]::Max(1, [math]::Floor($plafond / [math]::Max(1, $nbValeurs)))
    [int][math]::Max($script:AvMinIntervalle, [math]::Ceiling($script:AvFenetreSecondes / $passes))
}
function Get-AvCle { $v = [Environment]::GetEnvironmentVariable('ALPHAVANTAGE_KEY', 'Process'); if ($v) { $v = $v -replace '[\s"''“”‘’]', '' }; if ($v -and $v -notmatch '^(xxx|votre|your|demo)') { $v } else { '' } }

function Get-AvReponse([string]$fonction, [hashtable]$params) {
    # Seul point réseau du module (remplacé par un bouchon dans les tests). La clé n'apparaît que dans l'URL de l'appel, jamais ailleurs.
    $q = ($params.GetEnumerator() | ForEach-Object { "$($_.Key)=$([uri]::EscapeDataString("$($_.Value)"))" }) -join '&'
    $url = "https://www.alphavantage.co/query?function=$fonction&$q&apikey=$(Get-AvCle)"
    Invoke-RestMethod -Uri $url -Method Get -TimeoutSec 15 -Headers @{ 'User-Agent' = 'Jarvis-lecteur-cours/1.0 (usage personnel, lecture seule)' }
}
function Get-AvCauseErreur($ex) {
    $m = "$($ex.Exception.Message)"; $cle = Get-AvCle; if ($cle) { $m = $m.Replace($cle, '[SECRET]') }
    $c = 0; try { if ($ex.Exception.Response) { $c = [int]$ex.Exception.Response.StatusCode } } catch {}
    if ($c) { return "HTTP $c" }
    if ($m -match 'délai|timed? ?out|expiré') { return 'délai dépassé' }
    'réseau injoignable'
}

function Read-AvEtat([datetime]$heureParis) {
    $o = Read-JsonMemoire 'alphavantage-quota.json'
    $e = @{ date = $heureParis.ToString('yyyy-MM-dd'); n = 0; derniere = ''; quotes = @{} }
    if ($o) {
        if ($o.quotes) { foreach ($p in $o.quotes.PSObject.Properties) { $e.quotes[$p.Name] = $p.Value } }          # les derniers cours survivent au changement de jour
        if ("$($o.date)" -eq $e.date) { $e.n = [int]$o.n; $e.derniere = "$($o.derniere)" }
    }
    $e
}
function Save-AvEtat($e) { Save-JsonMemoire 'alphavantage-quota.json' ([ordered]@{ date = $e.date; n = $e.n; derniere = $e.derniere; quotes = $e.quotes }) }

function Get-CoursAlphaVantage($valeurs) {
    if (-not (Get-AvCle)) { return @{ dispo = $false; raison = 'clé ALPHAVANTAGE_KEY absente dans .env' } }
    $paris = Get-AvHeureParis; $plaf = Get-AvPlafond
    $map = @{}; if ($Config.alphavantage_symboles) { foreach ($p in $Config.alphavantage_symboles.PSObject.Properties) { if ("$($p.Value)".Trim()) { $map[(ConvertTo-NormMarche $p.Name)] = "$($p.Value)".Trim() } } }
    $avec = @(); $avert = @()
    foreach ($v in @($valeurs)) { $s = $map[(ConvertTo-NormMarche $v.nom)]; if ($s) { $avec += @{ v = $v; s = $s } } else { $avert += "symbole Alpha Vantage non configuré pour $($v.nom) (lancez jarvis.ps1 avtest)" } }
    if (-not $avec.Count) { return @{ dispo = $false; raison = ($avert -join ' ; ') } }
    $e = Read-AvEtat $paris
    $interv = Get-AvIntervalleSecondes $avec.Count $plaf
    $maint = if ($script:AvMaintenant) { $script:AvMaintenant } else { Get-Date }
    $der = ConvertTo-DateMarche $e.derniere
    $lire = (Test-HeuresBoursePar $paris) -and ($e.n -lt $plaf) -and ($der -eq [datetime]::MinValue -or ($maint - $der).TotalSeconds -ge $interv)
    if ($lire) {
        $e.derniere = $maint.ToString('o')
        foreach ($x in $avec) {
            if ($e.n -ge $plaf) { break }
            $e.n++; Save-AvEtat $e                                                      # compté AVANT l'appel
            try { $r = Get-AvReponse 'GLOBAL_QUOTE' @{ symbol = $x.s } } catch { $avert += "Alpha Vantage : $($x.v.nom) indisponible ($(Get-AvCauseErreur $_))"; continue }
            if ($r.PSObject.Properties['Note'] -or $r.PSObject.Properties['Information']) { $e.n = $plaf; Save-AvEtat $e; $avert += 'Alpha Vantage : limite signalée par le service (quota atteint)'; break }
            if ($r.PSObject.Properties['Error Message']) { $avert += "Alpha Vantage : symbole « $($x.s) » refusé pour $($x.v.nom) (lancez jarvis.ps1 avtest)"; continue }
            $g = $r.'Global Quote'
            if (-not $g -or -not $g.'05. price') { $avert += "Alpha Vantage : aucune cotation pour $($x.v.nom) ($($x.s)) — symbole inconnu ou non couvert"; continue }
            $prix = ConvertTo-NombreFr "$($g.'05. price')"; $var = ConvertTo-NombreFr ("$($g.'10. change percent')" -replace '%', '')
            $jour = [datetime]::MinValue
            if ($null -eq $prix -or -not [datetime]::TryParseExact("$($g.'07. latest trading day')", 'yyyy-MM-dd', [Globalization.CultureInfo]::InvariantCulture, [Globalization.DateTimeStyles]::None, [ref]$jour)) { $avert += "Alpha Vantage : réponse illisible pour $($x.v.nom)"; continue }
            $e.quotes[$x.v.nom] = [pscustomobject]@{ nom = $x.v.nom; symbole = $x.s; prix = $prix; devise = 'EUR'; variation_pct = $var; date = $jour.AddHours(17).AddMinutes(30).ToString('o'); source = 'Alpha Vantage' }
        }
        Save-AvEtat $e
    }
    if ($e.n -ge $plaf) { $avert += "Alpha Vantage : quota du jour atteint ($($e.n)/$plaf), reprise demain" }
    $cours = @(); foreach ($x in $avec) { $q = $e.quotes[$x.v.nom]; if ($q) { $cours += @{ nom = "$($q.nom)"; symbole = "$($q.symbole)"; prix = [double]$q.prix; devise = "$($q.devise)"; variation_pct = $q.variation_pct; date = "$($q.date)"; source = 'Alpha Vantage' } } }
    @{ dispo = $true; cours = @($cours); avertissements = @($avert | Select-Object -Unique) }
}

function Invoke-AvTest {
    # `jarvis.ps1 avtest` : UN SEUL appel (SYMBOL_SEARCH « thales ») pour voir quels symboles le service connaît pour Paris. Compte pour 1 sur le quota du jour.
    if (Test-ModeTest) { return @('(test : aucun appel réel)') }
    if (-not (Get-AvCle)) { return @('ALPHAVANTAGE_KEY est absente de .env : ajoutez-la (ALPHAVANTAGE_KEY=votre_clé), sans guillemets.') }
    $paris = Get-AvHeureParis; $e = Read-AvEtat $paris
    if ($e.n -ge (Get-AvPlafond)) { return @("Quota du jour déjà atteint ($($e.n)/$(Get-AvPlafond)) : réessayez demain.") }
    $e.n++; Save-AvEtat $e
    try { $r = Get-AvReponse 'SYMBOL_SEARCH' @{ keywords = 'thales' } } catch { return @("Appel impossible ($(Get-AvCauseErreur $_)).") }
    if ($r.PSObject.Properties['Note'] -or $r.PSObject.Properties['Information']) { return @('Le service signale une limite de requêtes (clé invalide ou quota). Rien d''autre n''a été fait.') }
    $m = @($r.bestMatches)
    if (-not $m.Count) { return @('Aucun résultat pour « thales ». Alpha Vantage ne couvre peut-être pas Euronext Paris : voir README.') }
    @("Résultats pour « thales » (1 requête comptée, $($e.n)/$(Get-AvPlafond) aujourd'hui) :") + @($m | ForEach-Object { "  $($_.'1. symbol')   $($_.'2. name')   région : $($_.'4. region')   devise : $($_.'8. currency')" }) +
        @('Recopiez le symbole de Paris dans config.json, "alphavantage_symboles". Si aucune ligne ne vient de Paris, ce service ne convient pas pour vos valeurs.')
}

Register-SourceMarche -Nom 'alphavantage' -MinSecondes 0 -Cours {
    param($valeurs)
    Get-CoursAlphaVantage $valeurs
}
