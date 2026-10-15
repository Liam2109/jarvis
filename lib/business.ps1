# État du business en LECTURE SEULE : site, Stripe (clé restreinte), Supabase (fonction jarvis_stats uniquement).
# Règles : Stripe en GET ; Supabase en POST sur /rpc/jarvis_stats uniquement ; les clés viennent de .env et ne sont jamais affichées ni journalisées ;
# JAMAIS de chiffre inventé : chaque source renvoie soit une valeur lue, soit @{ dispo = $false; raison = "..." }.
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

function Test-Cle([string]$nom) { $v = [Environment]::GetEnvironmentVariable($nom, 'Process'); [bool]($v -and $v -notmatch '_xxx$|^xxx$|^https://xxx') }

function Get-StatutSite([int]$timeout = 15) {
    try {
        $r = Invoke-WebRequest $Config.site -UseBasicParsing -TimeoutSec $timeout -Method Get
        [pscustomobject]@{ ok = ($r.StatusCode -eq 200); code = [int]$r.StatusCode; detail = '' }
    } catch {
        $c = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 0 }
        [pscustomobject]@{ ok = $false; code = $c; detail = $_.Exception.Message }
    }
}

# ---------- Stripe (lecture) ----------
function Get-StripeBase {
    # Surcharge réservée aux tests : uniquement vers 127.0.0.1 (jamais vers un autre serveur).
    if ($env:JARVIS_TEST_STRIPE_BASE -match '^http://127\.0\.0\.1:\d+/') { return $env:JARVIS_TEST_STRIPE_BASE }
    'https://api.stripe.com/v1/'
}
function Get-Stripe([string]$chemin) {
    $h = @{ Authorization = 'Bearer ' + $env:STRIPE_RESTRICTED_KEY }
    Invoke-RestMethod -Uri ((Get-StripeBase) + $chemin) -Headers $h -Method Get -TimeoutSec 20      # GET uniquement
}
function Resume-ErreurHttp($ex) {
    $c = if ($ex.Exception.Response) { [int]$ex.Exception.Response.StatusCode } else { 0 }
    if ($c -in 401, 403) { return 'clé refusée ou permission de lecture manquante' }
    if ($c -eq 0) { return 'source injoignable' }
    "erreur HTTP $c"
}

function Get-StripeAbonnes([datetime]$depuis) {
    if (-not (Test-Cle 'STRIPE_RESTRICTED_KEY')) { return @{ dispo = $false; raison = 'clé Stripe absente dans .env' } }
    try {
        $ts = [DateTimeOffset]::new($depuis.ToUniversalTime()).ToUnixTimeSeconds()
        $r = Get-Stripe "subscriptions?limit=100&status=all&created[gte]=$ts"
        @{ dispo = $true; valeur = @($r.data).Count; partiel = [bool]$r.has_more; source = 'Stripe' }
    } catch { @{ dispo = $false; raison = "Stripe (abonnés) : $(Resume-ErreurHttp $_)" } }
}

function Get-StripeCA([datetime]$depuis) {
    # Chiffre d'affaires = paiements réussis moins remboursements, par devise, sur la période.
    if (-not (Test-Cle 'STRIPE_RESTRICTED_KEY')) { return @{ dispo = $false; raison = 'clé Stripe absente dans .env' } }
    try {
        $ts = [DateTimeOffset]::new($depuis.ToUniversalTime()).ToUnixTimeSeconds()
        $r = Get-Stripe "charges?limit=100&created[gte]=$ts"
        $m = @{}; $n = 0
        foreach ($c in @($r.data)) {
            if ($c.paid -and $c.status -eq 'succeeded') {
                $dev = "$($c.currency)".ToUpper(); $net = [int64]$c.amount - [int64]$c.amount_refunded
                if (-not $m.ContainsKey($dev)) { $m[$dev] = [int64]0 }; $m[$dev] += $net; $n++
            }
        }
        @{ dispo = $true; montants = $m; paiements = $n; partiel = [bool]$r.has_more; source = 'Stripe' }
    } catch { @{ dispo = $false; raison = "Stripe (chiffre d'affaires) : $(Resume-ErreurHttp $_)" } }
}

# ---------- Supabase (lecture seule, UNIQUEMENT la fonction jarvis_stats) ----------
# POST {SUPABASE_URL}/rest/v1/rpc/jarvis_stats avec les en-têtes apikey + Authorization: Bearer {SUPABASE_READ_KEY} et le corps {"p_token":"<JARVIS_STATS_TOKEN>"}.
# Un seul paramètre (p_token), un seul appel. Le jeton n'est jamais dans l'URL, jamais affiché, jamais journalisé. Aucune table n'est lue.
# Réponses : 200 = totaux JSON ; 403 / 42501 = jeton faux ou vide ; 404 = cache de l'API pas à jour (un seul nouvel essai 30 s plus tard).
$script:Supabase404n = 0
function Get-EnvPropre([string]$nom) {
    # Valeur de .env sans espaces, retours à la ligne ni guillemets (droits ou typographiques).
    $v = [Environment]::GetEnvironmentVariable($nom, 'Process'); if (-not $v) { return '' }
    if ($v -like "$nom=*") { $v = $v.Substring($nom.Length + 1) }       # nom de la variable recopié dans la valeur
    $v -replace '[\s"''\u201C\u201D\u2018\u2019]', ''
}
$script:ChampsSaas = 'quiz_total', 'quiz_24h', 'quiz_7j', 'emails_total', 'emails_24h', 'abonnes_actifs', 'nouveaux_abonnes_24h', 'abonnes_en_annulation', 'paiements_echoues', 'demandes_retractation_a_traiter'
function Get-SupabaseCorpsErreur($ex) {
    try { if ($ex.ErrorDetails -and $ex.ErrorDetails.Message) { return "$($ex.ErrorDetails.Message)" } } catch {}
    try { $s = $ex.Exception.Response.GetResponseStream(); $r = New-Object IO.StreamReader($s); return $r.ReadToEnd() } catch {}
    ''
}
function Get-SupabaseStats([datetime]$depuis) {
    $url = Get-EnvPropre 'SUPABASE_URL'; $cle = Get-EnvPropre 'SUPABASE_READ_KEY'; $jeton = Get-EnvPropre 'JARVIS_STATS_TOKEN'
    if (-not ($url -and $cle) -or $url -match '^https://xxx|^xxx$' -or $cle -match '^xxx$') { return @{ dispo = $false; http = 0; cas = 'config'; raison = 'URL ou clé Supabase absente dans .env' } }
    if (-not $jeton -or $jeton -match '^xxx$') { return @{ dispo = $false; http = 0; cas = 'config'; raison = 'JARVIS_STATS_TOKEN absent dans .env' } }
    if ($jeton.Length -ge 8 -and $script:Secrets -notcontains $jeton) { $script:Secrets += $jeton }
    $h = @{ apikey = $cle; Authorization = "Bearer $cle" }
    $u = $url.TrimEnd('/') + '/rest/v1/rpc/jarvis_stats'
    try {
        $corps = [Text.Encoding]::UTF8.GetBytes((@{ p_token = $jeton } | ConvertTo-Json -Compress))
        $rep = Invoke-RestMethod -Uri $u -Headers $h -Method Post -Body $corps -ContentType 'application/json' -TimeoutSec 20      # POST sur cette fonction UNIQUEMENT
        $o = @($rep | ForEach-Object { $_ }) | Select-Object -First 1                  # PS 5.1 : objet seul ou tableau d'un objet selon la fonction
        if ($o -and @($o.PSObject.Properties).Count -eq 1 -and $o.PSObject.Properties.Name -contains 'jarvis_stats') { $o = $o.jarvis_stats }
        if (-not $o -or -not @($o.PSObject.Properties).Count) { return @{ dispo = $false; http = 200; cas = '200-vide'; raison = 'Supabase : jarvis_stats n''a rien renvoyé' } }
        $saas = @{}
        foreach ($c in $script:ChampsSaas) { if ($o.PSObject.Properties.Name -contains $c -and $null -ne $o.$c -and "$($o.$c)" -match '^-?\d+$') { $saas[$c] = [int64]$o.$c } }
        if (-not $saas.Count) { return @{ dispo = $false; http = 200; cas = '200-inconnu'; raison = "Supabase : réponse non reconnue (champs : $(($o.PSObject.Properties.Name | Select-Object -First 6) -join ', '))" } }
        $script:Supabase404n = 0
        # quiz / e-mails « des 24 dernières heures » : ce que le briefing dit ; le détail complet va au panneau Mon SaaS
        @{ dispo = $true; http = 200; cas = '200'; sessions = [int64]$(if ($saas.ContainsKey('quiz_24h')) { $saas.quiz_24h } else { 0 }); emails = [int64]$(if ($saas.ContainsKey('emails_24h')) { $saas.emails_24h } else { 0 })
           payees = [int64]0; partiel = $false; source = 'Supabase (jarvis_stats)'; saas = $saas }
    } catch {
        $code = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 0 }
        $corpsErr = Get-SupabaseCorpsErreur $_
        if ($code -eq 403 -or $corpsErr -match '42501') { return @{ dispo = $false; http = $code; cas = '403'; raison = 'Supabase : jeton refusé (JARVIS_STATS_TOKEN faux ou vide)' } }
        if ($code -eq 401) { return @{ dispo = $false; http = 401; cas = '401'; raison = 'Supabase : clé SUPABASE_READ_KEY refusée' } }
        if ($code -eq 404) {
            $script:Supabase404n++
            return @{ dispo = $false; http = 404; cas = '404'; reessai = ($script:Supabase404n -eq 1); raison = 'Supabase : fonction jarvis_stats introuvable (cache de l''API pas à jour ?)' }
        }
        @{ dispo = $false; http = $code; cas = "http-$code"; raison = "Supabase : $(Resume-ErreurHttp $_)" }
    }
}
# ---------- Visites ----------
function Get-VisitesBriefing([datetime]$depuis) {
    # Vercel Analytics n'offre pas d'API de lecture accessible avec une clé restreinte connue de Jarvis : source non branchée (jamais de chiffre estimé).
    @{ dispo = $false; raison = "visites du site : source non branchée (Vercel Analytics)" }
}

function Get-ChiffresBusiness([datetime]$depuis, [switch]$SansSite) {
    $site = if ($SansSite) { $null } else { Get-StatutSite 8 }
    $stats = Get-SupabaseStats $depuis
    @{
        depuis = $depuis; maj = (Get-Date)
        site = $site
        visites = Get-VisitesBriefing $depuis
        stats = $stats
        abonnes = $(if ($stats.dispo -and $stats.saas -and $stats.saas.ContainsKey('nouveaux_abonnes_24h')) { @{ dispo = $true; valeur = $stats.saas.nouveaux_abonnes_24h; partiel = $false; source = 'Supabase' } } else { Get-StripeAbonnes $depuis })
        ca = Get-StripeCA $depuis
    }
}

function Get-TachesTodo([int]$faitesMax = 4) {
    # Toutes les tâches de memoire\todo.md pour le tableau : les ouvertes d'abord, puis les dernières cochées (en lecture seule).
    $f = Join-Path $script:JarvisRoot 'memoire\todo.md'
    if (-not (Test-Path $f)) { return @() }
    $ouv = @(); $fai = @()
    foreach ($l in (Get-Content $f -Encoding UTF8)) {
        if ($l -match '^\s*-\s*\[ \]\s*(.+)$') { $ouv += @{ texte = $Matches[1].Trim(); fait = $false } }
        elseif ($l -match '^\s*-\s*\[[xX]\]\s*(.+)$') { $fai += @{ texte = $Matches[1].Trim(); fait = $true } }
    }
    @($ouv) + @($fai | Select-Object -Last $faitesMax)
}
function Get-TodoOuverte {
    $f = Join-Path $script:JarvisRoot 'memoire\todo.md'
    if (-not (Test-Path $f)) { return @() }
    @(Get-Content $f -Encoding UTF8 | Where-Object { $_ -match '^\s*-\s*\[ \]\s*(.+)$' } | ForEach-Object { ($_ -replace '^\s*-\s*\[ \]\s*', '').Trim() })
}

function Get-SalutationHeure([datetime]$now = (Get-Date)) { if ($now.Hour -ge 18 -or $now.Hour -lt 5) { 'Bonsoir monsieur' } else { 'Bonjour monsieur' } }

# ---------- Phrases du briefing (fonction PURE : ne peut dire que ce qui a été lu) ----------
function Format-Pluriel([int64]$n, [string]$un, [string]$plusieurs) { if ($n -eq 1) { "$n $un" } else { "$n $plusieurs" } }

function Format-Montants($montants) {
    $noms = @{ EUR = 'euros'; USD = 'dollars'; GBP = 'livres' }
    $fr = [Globalization.CultureInfo]::GetCultureInfo('fr-FR')
    $parts = foreach ($k in ($montants.Keys | Sort-Object)) {
        $v = [math]::Round([double]$montants[$k] / 100, 2)
        $txt = $v.ToString('0.00', $fr) -replace ',00$', ''
        "$txt $(if ($noms.ContainsKey($k)) { $noms[$k] } else { $k })"
    }
    @($parts) -join ' et '
}

function Get-PhrasesBusiness($d) {
    # Chiffres lus, puis UNE phrase pour tout ce qui est indisponible, puis l'état du site. Rien d'autre.
    $p = New-Object System.Collections.Generic.List[string]
    $manque = New-Object System.Collections.Generic.List[string]
    $lus = New-Object System.Collections.Generic.List[string]
    # visites
    if ($d.visites.dispo) { $lus.Add((Format-Pluriel $d.visites.valeur 'visite' 'visites')) } else { $manque.Add($d.visites.raison) }
    # quiz et e-mails (Supabase)
    if ($d.stats.dispo) {
        $au = if ($d.stats.partiel) { 'au moins ' } else { '' }
        $lus.Add("$au$(Format-Pluriel $d.stats.sessions 'quiz commencé' 'quiz commencés')" + $(if ($d.stats.payees -gt 0) { ", dont $($d.stats.payees) payé" + $(if ($d.stats.payees -gt 1) { 's' }) } else { '' }))
        $lus.Add((Format-Pluriel $d.stats.emails 'e-mail récupéré' 'e-mails récupérés'))
    } else { $manque.Add($d.stats.raison) }
    # abonnés et chiffre d'affaires (Stripe)
    if ($d.abonnes.dispo) { $au = if ($d.abonnes.partiel) { 'au moins ' } else { '' }; $lus.Add("$au$(Format-Pluriel $d.abonnes.valeur 'nouvel abonné' 'nouveaux abonnés')") } else { $manque.Add($d.abonnes.raison) }
    if ($d.ca.dispo) {
        $au = if ($d.ca.partiel) { 'au moins ' } else { '' }
        $txt = if ($d.ca.montants.Count) { Format-Montants $d.ca.montants } else { '0 euro' }
        $lus.Add("chiffre d'affaires de $au$txt")
    } else { $manque.Add($d.ca.raison) }
    if ($lus.Count) { $p.Add('Sur les 24 dernières heures : ' + ($lus -join ', ') + '.') }
    # une SEULE phrase pour tout ce qui est indisponible
    $manque = @($manque | Select-Object -Unique)
    if ($manque.Count) { $p.Add("Je n'ai pas pu lire : " + ($manque -join ' ; ') + '.') }
    # site
    if ($d.site) {
        if ($d.site.ok) { $p.Add("Le site tonproduit.shop répond, code 200.") }
        else { $p.Add("Attention monsieur, le site ne répond pas correctement. " + $(if ($d.site.code) { "Code $($d.site.code)." } else { 'Aucune réponse.' })) }
    }
    , @($p)
}

function Get-BriefingPhrases($d, $todo, [string]$rappel = '', [datetime]$now = (Get-Date)) {
    $p = New-Object System.Collections.Generic.List[string]
    $p.Add((Get-SalutationHeure $now))
    if ($rappel) { $p.Add($rappel) }
    foreach ($x in (Get-PhrasesBusiness $d)) { $p.Add($x) }
    # to-do
    $todo = @($todo | Where-Object { $_ -and "$_".Trim() })      # un tableau vide passé en argument devient $null : on ne compte jamais une tâche fantôme
    if ($todo.Count -eq 0) { $p.Add('Votre liste de tâches est vide.') }
    else {
        $reste = if ($todo.Count -gt 5) { " Et $($todo.Count - 5) autre" + $(if ($todo.Count - 5 -gt 1) { 's' }) + '.' } else { '' }
        $p.Add("Vous avez $($todo.Count) tâche" + $(if ($todo.Count -gt 1) { 's' }) + " : " + (($todo | Select-Object -First 5) -join ', ') + ".$reste")
    }
    , @($p)
}

function Invoke-Briefing([switch]$Auto) {
    # -Auto : briefing de démarrage / de réactivation. Il n'est DIT qu'une fois par jour, le matin ; sinon il s'affiche au tableau de bord sans voix.
    # Sans -Auto : Liam l'a demandé -> réponse à un ordre, dite.
    $ctx = 'reponse'
    if ($Auto) {
        $ctx = if ((Get-Command Test-BriefingVocalAuto -ErrorAction SilentlyContinue) -and -not (Test-BriefingVocalAuto)) { 'spontane' } else { 'briefing' }
        if ($ctx -eq 'briefing' -and (Get-Command Set-BriefingVocalFait -ErrorAction SilentlyContinue)) { Set-BriefingVocalFait }
    }
    $script:BriefingLignes.Clear(); $script:CaptureBriefing = $true
    try { if (Get-Command Invoke-AvecContexteVoix -ErrorAction SilentlyContinue) { Invoke-AvecContexteVoix $ctx { Invoke-BriefingCorps } } else { Invoke-BriefingCorps } } finally { $script:CaptureBriefing = $false }
}

function Invoke-BriefingCorps {
    Set-VisageEtat 'reflechit'
    if (Get-Command Update-Tableau -ErrorAction SilentlyContinue) { Update-Tableau }   # le tableau de bord se remplit dès le début du briefing
    $d = Get-ChiffresBusiness ((Get-Date).AddHours(-24))
    foreach ($k in 'visites', 'stats', 'abonnes', 'ca') {
        Write-Journal -Action "Briefing : lecture $k" -Resultat $(if ($d[$k].dispo) { 'ok' } else { "indisponible : $($d[$k].raison)" })
    }
    Write-Journal -Action 'Vérification du site' -Resultat ("code {0}" -f $d.site.code)
    $rappel = if (Get-Command Get-RappelHier -ErrorAction SilentlyContinue) { Get-RappelHier } else { '' }
    $phrases = Get-BriefingPhrases $d (Get-TodoOuverte) $rappel
    Set-VisageEtat 'ecoute'
    foreach ($ph in $phrases) { if (Test-Coupure) { break }; Parler $ph }
    if (-not (Test-Coupure) -and (Get-Command Invoke-Veille -ErrorAction SilentlyContinue)) { Invoke-Veille }
}
