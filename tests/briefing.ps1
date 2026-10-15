# Test du briefing : jamais de chiffre inventé, source indisponible dite une seule fois, GET uniquement, clés jamais divulguées. Code de sortie 0 = réussi.
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$env:JARVIS_TEST = '1'      # TEST SILENCIEUX : aucun son, aucune fenêtre, aucun micro, aucune touche, aucune action réelle
. (Join-Path $Root 'lib\journal.ps1')
. (Join-Path $PSScriptRoot '_outils.ps1')
$Config = Get-Content (Get-ConfigPath) -Raw -Encoding UTF8 | ConvertFrom-Json
. (Join-Path $Root 'lib\voix.ps1'); . (Join-Path $Root 'lib\business.ps1'); . (Join-Path $Root 'lib\permissions.ps1'); . (Join-Path $Root 'lib\actions.ps1')
. (Join-Path $Root 'lib\entrees.ps1'); . (Join-Path $Root 'lib\ecrans.ps1'); . (Join-Path $Root 'lib\tableau.ps1'); . (Join-Path $Root 'lib\visage.ps1')
$echecs = 0
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }
function Jours($d) { (Get-PhrasesBusiness $d) -join ' | ' }
function Nombres([string]$t) { @([regex]::Matches(($t -replace 'code 200', ''), '\d+') | ForEach-Object { $_.Value }) }
function Donnees { param($stats = $null, $abonnes = $null, $ca = $null, $visites = $null, $site = $null)
    $ko = { param($r) @{ dispo = $false; raison = $r } }
    @{ depuis = (Get-Date).AddHours(-24); maj = (Get-Date)
       site = $(if ($site) { $site } else { [pscustomobject]@{ ok = $true; code = 200 } })
       visites = $(if ($visites) { $visites } else { & $ko 'visites du site : source non branchée (Vercel Analytics)' })
       stats = $(if ($stats) { $stats } else { & $ko 'URL ou clé Supabase absente dans .env' })
       abonnes = $(if ($abonnes) { $abonnes } else { & $ko 'clé Stripe absente dans .env' })
       ca = $(if ($ca) { $ca } else { & $ko 'clé Stripe absente dans .env' }) } }

Write-Host '1) Aucune source disponible : aucun chiffre, UNE seule phrase d''indisponibilité'
$t = Jours (Donnees)
Verifier ((Nombres $t).Count -eq 0) "aucun chiffre dans : $t"
Verifier (([regex]::Matches($t, "Je n'ai pas pu lire")).Count -eq 1) 'la phrase « Je n''ai pas pu lire » n''apparaît qu''une fois'
Verifier ($t -match 'visites' -and $t -match 'Supabase' -and $t -match 'Stripe') 'chaque source manquante est nommée (visites, Supabase, Stripe)'
Verifier (([regex]::Matches($t, 'clé Stripe absente')).Count -eq 1) 'la même cause (Stripe) n''est pas répétée'

Write-Host '2) Valeurs lues : seuls ces chiffres sont dits'
$d = Donnees -stats @{ dispo = $true; sessions = 17; emails = 9; payees = 4; partiel = $false } -abonnes @{ dispo = $true; valeur = 3; partiel = $false } -ca @{ dispo = $true; montants = @{ EUR = 12345 }; paiements = 5; partiel = $false }
$t = Jours $d
Write-Host "        $t"
Verifier ($t -match '17 quiz commencés, dont 4 payés') '17 quiz commencés, dont 4 payés'
Verifier ($t -match '9 e-mails récupérés') '9 e-mails récupérés'
Verifier ($t -match '3 nouveaux abonnés') '3 nouveaux abonnés'
Verifier ($t -match "chiffre d'affaires de 123,45 euros") "chiffre d'affaires de 123,45 euros (12345 centimes)"
$autorises = @('17', '4', '9', '3', '123', '45', '24'); $dits = Nombres $t
Verifier (-not ($dits | Where-Object { $_ -notin $autorises })) "tous les nombres dits viennent des données : $($dits -join ', ')"
Verifier ($t -match 'visites du site : source non branchée') 'les visites (non branchées) sont déclarées indisponibles, pas estimées'
$d2 = Donnees -stats @{ dispo = $true; sessions = 0; emails = 0; payees = 0; partiel = $false } -abonnes @{ dispo = $true; valeur = 1; partiel = $false } -ca @{ dispo = $true; montants = @{}; paiements = 0; partiel = $false }
$t2 = Jours $d2
Verifier ($t2 -match '0 quiz commencés' -and $t2 -match '1 nouvel abonné[^s]' -and $t2 -match "chiffre d'affaires de 0 euro") 'zéros réels et singulier corrects : 0 quiz, 1 nouvel abonné, 0 euro'
$d3 = Donnees -stats @{ dispo = $true; sessions = 1000; emails = 800; payees = 1; partiel = $true } -abonnes @{ dispo = $true; valeur = 100; partiel = $true } -ca @{ dispo = $true; montants = @{ EUR = 100000; USD = 5000 }; paiements = 9; partiel = $true }
$t3 = Jours $d3
Verifier ($t3 -match 'au moins 1000 quiz' -and $t3 -match 'au moins 100 nouveaux' -and $t3 -match 'au moins 1000 euros et 50 dollars') 'résultats partiels annoncés « au moins » ; plusieurs devises'
$d4 = Donnees -site ([pscustomobject]@{ ok = $false; code = 503 })
Verifier ((Jours $d4) -match 'ne répond pas correctement\. Code 503') 'site hors ligne : code réel annoncé'
$d5 = Donnees -site ([pscustomobject]@{ ok = $false; code = 0 })
Verifier ((Jours $d5) -match 'Aucune réponse') 'site injoignable : « Aucune réponse »'

Write-Host '3) Briefing complet : salutation, rappel, to-do'
$now = Get-Date '2026-10-14 09:00'
$ph = Get-BriefingPhrases (Donnees) @('a', 'b', 'c', 'd', 'e', 'f', 'g') 'Hier, nous avons terminé le site.' $now
Verifier ($ph[0] -eq 'Bonjour monsieur') 'à 9 h : « Bonjour monsieur »'
Verifier ((Get-BriefingPhrases (Donnees) @() '' (Get-Date '2026-10-14 19:00'))[0] -eq 'Bonsoir monsieur') 'à 19 h : « Bonsoir monsieur »'
Verifier ((Get-BriefingPhrases (Donnees) @() '' (Get-Date '2026-10-14 03:00'))[0] -eq 'Bonsoir monsieur') 'à 3 h : « Bonsoir monsieur »'
Verifier ($ph[1] -eq 'Hier, nous avons terminé le site.') 'le rappel d''hier vient juste après la salutation'
Verifier (($ph[-1]) -match '7 tâches : a, b, c, d, e\. Et 2 autres\.') 'to-do : 5 premières tâches + « Et 2 autres »'
Verifier ((Get-BriefingPhrases (Donnees) @() '' $now)[-1] -eq 'Votre liste de tâches est vide.') 'to-do vide annoncée'
Verifier ((Get-BriefingPhrases (Donnees) $null '' $now)[-1] -eq 'Votre liste de tâches est vide.') 'to-do $null (cas réel : fonction qui ne renvoie rien) : pas de tâche fantôme'
Verifier ((Get-BriefingPhrases (Donnees) ([string[]]@('')) '' $now)[-1] -eq 'Votre liste de tâches est vide.') 'to-do avec chaîne vide : pas de tâche fantôme'

Write-Host '4) Fournisseurs réels contre un faux serveur local (aucun accès Internet)'
$port = 47651; $log = Join-Path $env:TEMP 'jarvis-faux-serveur.log'; Remove-Item $log -ErrorAction SilentlyContinue
$srv = Start-FauxServeur @($port, $log) {
    param($port, $log)
    $l = New-Object Net.HttpListener; $l.Prefixes.Add("http://127.0.0.1:$port/"); $l.Start()
    while ($true) {
        $c = $l.GetContext(); $r = $c.Request; $auth = "$($r.Headers['Authorization'])"
        $corps = if ($r.HasEntityBody) { (New-Object IO.StreamReader($r.InputStream, [Text.Encoding]::UTF8)).ReadToEnd() } else { '' }
        Add-Content $log ("{0} {1} {2}{3}" -f $r.HttpMethod, $r.Url.AbsolutePath, $(if ($auth -like '*DENIED*') { 'DENIED' } elseif ($auth) { 'AUTH' } else { 'NOAUTH' }), $(if ($r.Url.Query -match 'jeton_secret') { ' TOKENINURL' } else { '' }))
        $code = 200; $body = '{}'
        if ($auth -like '*DENIED*') { $code = 403; $body = '{"error":"forbidden"}' }
        elseif ($r.Url.AbsolutePath -eq '/ping') { $body = '"pong"' }
        elseif ($r.Url.AbsolutePath -eq '/v1/subscriptions') { $body = '{"data":[{"id":"sub_1"},{"id":"sub_2"}],"has_more":false}' }
        elseif ($r.Url.AbsolutePath -eq '/v1/charges') { $body = '{"data":[{"paid":true,"status":"succeeded","amount":5000,"amount_refunded":1000,"currency":"eur"},{"paid":true,"status":"succeeded","amount":2000,"amount_refunded":0,"currency":"eur"},{"paid":false,"status":"failed","amount":9999,"amount_refunded":0,"currency":"eur"}],"has_more":false}' }
        elseif ($r.Url.AbsolutePath -eq '/rest/v1/rpc/jarvis_stats') {
            # La fonction n'accepte que le paramètre p_token (autre nom -> 404 PGRST202, comme PostgREST) et que le bon jeton (sinon 403 / 42501).
            if ($r.HttpMethod -ne 'POST') { $code = 405; $body = '{"message":"method not allowed"}' }
            elseif ("$($r.Headers['apikey'])" -eq 'sb_cle_404') { $code = 404; $body = '{"code":"PGRST202","message":"Could not find the function public.jarvis_stats(p_token) in the schema cache"}' }
            elseif ($corps -notmatch '"p_token"\s*:') { $code = 404; $body = '{"code":"PGRST202","message":"Could not find the function public.jarvis_stats(jeton) in the schema cache"}' }
            elseif ($corps -notmatch 'jeton_secret_1234567890') { $code = 403; $body = '{"code":"42501","message":"jeton invalide"}' }
            else { $body = '{"quiz_total":40,"quiz_24h":4,"quiz_7j":12,"emails_total":20,"emails_24h":2,"abonnes_actifs":7,"nouveaux_abonnes_24h":2,"abonnes_en_annulation":1,"paiements_echoues":1,"demandes_retractation_a_traiter":0,"adresse_test":"a@exemple.fr"}' }
        }
        $b = [Text.Encoding]::UTF8.GetBytes($body); $c.Response.StatusCode = $code; $c.Response.ContentType = 'application/json'; $c.Response.ContentLength64 = $b.Length
        $c.Response.OutputStream.Write($b, 0, $b.Length); $c.Response.Close()
    }
}
try {
    for ($i = 0; $i -lt 40; $i++) { try { [void](Invoke-WebRequest "http://127.0.0.1:$port/ping" -UseBasicParsing -TimeoutSec 1); break } catch { Start-Sleep -Milliseconds 250 } }
    Import-JarvisEnv   # d'abord le .env réel (peut être vide), PUIS les variables de test
    $env:JARVIS_TEST_STRIPE_BASE = "http://127.0.0.1:$port/v1/"
    $env:STRIPE_RESTRICTED_KEY = 'rk_test_CLEFSECRETE1234567890'; $env:SUPABASE_URL = "http://127.0.0.1:$port"; $env:SUPABASE_READ_KEY = 'sb_cle_secrete_1234567890'; $env:JARVIS_STATS_TOKEN = 'jeton_secret_1234567890'; $script:Supabase404n = 0
    $script:Secrets += 'rk_test_CLEFSECRETE1234567890', 'sb_cle_secrete_1234567890', 'jeton_secret_1234567890'
    $depuis = (Get-Date).AddHours(-24)
    $a = Get-StripeAbonnes $depuis; Verifier ($a.dispo -and $a.valeur -eq 2) 'Stripe abonnés : 2 lus'
    $c = Get-StripeCA $depuis;      Verifier ($c.dispo -and $c.montants['EUR'] -eq 6000 -and $c.paiements -eq 2) "Stripe chiffre d'affaires : 60 euros (5000 - 1000 remboursés + 2000 ; le paiement échoué est ignoré)"
    $s = Get-SupabaseStats $depuis; Verifier ($s.dispo -and $s.http -eq 200 -and $s.sessions -eq 4 -and $s.emails -eq 2 -and $s.saas.quiz_total -eq 40 -and $s.saas.quiz_7j -eq 12 -and $s.saas.abonnes_actifs -eq 7 -and $s.saas.abonnes_en_annulation -eq 1 -and $s.saas.paiements_echoues -eq 1 -and $s.saas.demandes_retractation_a_traiter -eq 0) 'Supabase (jarvis_stats, paramètre p_token) : HTTP 200, les 10 totaux lus (quiz 40/4/12, e-mails 20/2, 7 abonnés actifs, 1 en annulation, 1 paiement échoué, 0 rétractation)'
    # Briefing complet avec ces vraies fonctions
    $script:Dits = @(); function Parler([string]$t, $Langue) { $script:Dits += $t }
    function Get-StatutSite { param($timeout) [pscustomobject]@{ ok = $true; code = 200; detail = '' } }
    $script:BriefingLignes = New-Object System.Collections.Generic.List[string]
    Invoke-BriefingCorps
    $dit = $script:Dits -join ' | '
    Write-Host "        $dit"
    Verifier ($dit -match '4 quiz commencés' -and $dit -match '2 e-mails récupérés' -and $dit -match '2 nouveaux abonnés' -and $dit -match "60 euros") 'le briefing dit exactement ce qui a été lu'
    Verifier ($script:Dits[0] -match '^Bon(jour|soir) monsieur$') 'il commence par la salutation'
    Verifier ($dit -notmatch '@exemple\.fr') 'aucune adresse e-mail n''est prononcée'
    # .env avec espaces, retour à la ligne et guillemets autour des valeurs : nettoyés
    $env:SUPABASE_READ_KEY = """ sb_cle_secrete_1234567890 
"""; $env:JARVIS_STATS_TOKEN = """jeton_secret_1234567890 
"""
    $sn = Get-SupabaseStats $depuis; Verifier ($sn.dispo -and $sn.http -eq 200) 'valeurs de .env avec espaces / retours à la ligne / guillemets : nettoyées, lecture réussie'
    $env:SUPABASE_READ_KEY = 'sb_cle_secrete_1234567890'; $env:JARVIS_STATS_TOKEN = 'jeton_secret_1234567890'
    $env:SUPABASE_URL = "SUPABASE_URL=http://127.0.0.1:$port"
    $sp = Get-SupabaseStats $depuis; Verifier ($sp.dispo -and $sp.http -eq 200) 'valeur « SUPABASE_URL=SUPABASE_URL=https://... » (nom recopié dans .env) : tolérée'
    $env:SUPABASE_URL = "http://127.0.0.1:$port"
    # Jeton faux : 403
    $env:JARVIS_STATS_TOKEN = 'mauvais_jeton_xxxxxxxx'; $script:Secrets += 'mauvais_jeton_xxxxxxxx'
    $s403 = Get-SupabaseStats $depuis; Verifier (-not $s403.dispo -and $s403.http -eq 403 -and $s403.cas -eq '403' -and $s403.raison -match 'jeton refusé' -and $s403.raison -notmatch 'mauvais_jeton') 'jeton faux : HTTP 403 (42501), « Mon SaaS : indisponible », le jeton n''est pas dans le message'
    $env:JARVIS_STATS_TOKEN = 'jeton_secret_1234567890'
    # Cache de l'API pas à jour : 404, UN SEUL nouvel essai programmé
    $env:SUPABASE_READ_KEY = 'sb_cle_404'; $script:Secrets += 'sb_cle_404'; $script:Supabase404n = 0
    $a404 = Get-SupabaseStats $depuis; $b404 = Get-SupabaseStats $depuis
    Verifier ($a404.http -eq 404 -and $a404.cas -eq '404' -and $a404.reessai -and -not $b404.reessai) '404 : un nouvel essai est programmé UNE fois (pas de boucle)'
    $env:SUPABASE_READ_KEY = 'sb_cle_secrete_1234567890'
    # Erreur 403 : clé refusée
    $env:STRIPE_RESTRICTED_KEY = 'rk_test_DENIED_1234567890'; $script:Secrets += 'rk_test_DENIED_1234567890'
    $a2 = Get-StripeAbonnes $depuis
    Verifier (-not $a2.dispo -and $a2.raison -match 'clé refusée ou permission') "403 : « $($a2.raison) »"
    Verifier ($a2.raison -notmatch 'rk_test') 'la raison ne contient pas la clé'
    # Que des GET, jamais une écriture
    Start-Sleep -Milliseconds 300
    $req = @(Get-Content $log)
    $stripe = @($req | Where-Object { $_ -match ' /v1/' }); $supa = @($req | Where-Object { $_ -match ' /rest/' })
    Verifier ($req.Count -ge 5 -and @($stripe | Where-Object { $_ -notmatch '^GET ' }).Count -eq 0) "Stripe : uniquement des GET ($($stripe.Count) requêtes)"
    Verifier ($supa.Count -ge 1 -and @($supa | Where-Object { $_ -notmatch '^POST /rest/v1/rpc/jarvis_stats ' }).Count -eq 0) "Supabase : uniquement POST /rest/v1/rpc/jarvis_stats ($($supa.Count) requêtes), aucune table lue, jamais d'autre nom de paramètre"
    Verifier (@($req | Where-Object { $_ -match 'quiz_sessions|TOKENINURL' }).Count -eq 0) 'le jeton n''est jamais dans l''URL et aucune table n''est interrogée'
    Verifier ((@($req | Where-Object { $_ -match 'NOAUTH' -and $_ -notmatch '/ping' })).Count -eq 0) 'toutes les requêtes portent l''authentification (en en-tête)'
} finally {
    Stop-FauxServeur $srv
    Remove-Item Env:JARVIS_TEST_STRIPE_BASE -ErrorAction SilentlyContinue
}
$j = Get-Content (Get-ChildItem (Get-DossierLogs) -Filter 'journal-*.md' | Sort-Object Name | Select-Object -Last 1).FullName -Raw -Encoding UTF8
Verifier ($j -notmatch 'rk_test_|sb_cle_secrete|jeton_secret|@exemple\.fr') 'le journal ne contient ni clé ni adresse e-mail'
Verifier ($j -match 'Briefing : lecture ca') 'les lectures de source sont journalisées (sans valeur sensible)'

Write-Host '5) Clés absentes : indisponible, sans appel réseau'
foreach ($k in 'STRIPE_RESTRICTED_KEY', 'SUPABASE_URL', 'SUPABASE_READ_KEY', 'JARVIS_STATS_TOKEN') { [Environment]::SetEnvironmentVariable($k, '', 'Process') }
$depuis = (Get-Date).AddHours(-24)
Verifier ((Get-StripeAbonnes $depuis).raison -match 'absente') 'Stripe abonnés : clé absente -> indisponible'
Verifier ((Get-StripeCA $depuis).raison -match 'absente') 'Stripe CA : clé absente -> indisponible'
Verifier ((Get-SupabaseStats $depuis).raison -match 'absente') 'Supabase : clé absente -> indisponible'
$env:SUPABASE_URL = 'http://127.0.0.1:9'; $env:SUPABASE_READ_KEY = 'sb_cle_secrete_1234567890'
Verifier ((Get-SupabaseStats $depuis).raison -match 'JARVIS_STATS_TOKEN absent') 'Supabase : jeton absent -> indisponible, sans appel réseau (le port 9 n''est pas écouté)'
foreach ($k in 'SUPABASE_URL', 'SUPABASE_READ_KEY') { [Environment]::SetEnvironmentVariable($k, '', 'Process') }
Verifier (-not (Get-VisitesBriefing $depuis).dispo) 'visites : source non branchée -> indisponible, jamais estimée'

if ($echecs) { Write-Host "`nÉCHEC : $echecs vérification(s) en échec." -ForegroundColor Red; exit 1 }
Write-Host "`nRÉUSSI"; exit 0
