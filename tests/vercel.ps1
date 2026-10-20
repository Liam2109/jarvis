# Test SILENCIEUX de la lecture des visites (Vercel Analytics) : GET seulement, jeton en en-tête (jamais dans l'URL, jamais affiché), faux serveur local 127.0.0.1 (aucun accès Internet).
# Sans VERCEL_TOKEN / VERCEL_PROJECT_ID : « source non branchée », aucun chiffre inventé. Code de sortie 0 = réussi.
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$env:JARVIS_TEST = '1'
. (Join-Path $Root 'lib\journal.ps1')
. (Join-Path $PSScriptRoot '_outils.ps1')
. (Join-Path $Root 'lib\business.ps1')
. (Join-Path $Root 'lib\saas.ps1')
$echecs = 0
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }
foreach ($k in 'VERCEL_TOKEN', 'VERCEL_PROJECT_ID', 'VERCEL_TEAM_ID', 'JARVIS_TEST_VERCEL_BASE') { [Environment]::SetEnvironmentVariable($k, $null, 'Process') }
$depuis = (Get-Date).AddHours(-24)

Write-Host '1) Rien de branché : source non branchée, aucun chiffre'
$v = Get-VisitesBriefing $depuis
Verifier (-not $v.dispo -and $v.raison -match 'non branchée' -and -not $v.ContainsKey('valeur')) 'sans réglage : indisponible, « source non branchée »'
$env:VERCEL_TOKEN = 'vercel_jeton_SECRET_1234567890'
Verifier ((Get-VisitesBriefing $depuis).raison -match 'non branchée') 'jeton sans identifiant de projet : toujours non branchée'
$env:VERCEL_PROJECT_ID = 'prj_test123'
Verifier ((Get-VisitesBriefing $depuis).raison -match 'non branchée') 'mode test sans faux serveur : jamais le vrai Vercel'

Write-Host '2) Faux serveur local'
$port = 47662; $log = Join-Path $env:TEMP 'jarvis-faux-vercel.log'; Remove-Item $log -ErrorAction SilentlyContinue
$srv = Start-FauxServeur @($port, $log) {
    param($port, $log)
    $l = New-Object Net.HttpListener; $l.Prefixes.Add("http://127.0.0.1:$port/"); $l.Start()
    while ($true) {
        $c = $l.GetContext(); $r = $c.Request; $auth = "$($r.Headers['Authorization'])"
        Add-Content $log ("{0} {1} {2}{3}{4}" -f $r.HttpMethod, $r.Url.AbsolutePath, $(if ($auth -match 'Bearer ') { 'AUTH' } else { 'NOAUTH' }), $(if ($r.Url.Query -match 'SECRET') { ' TOKENINURL' } else { '' }), $(if ($r.Url.Query -match 'teamId=team_x') { ' TEAM' } else { '' }))
        $code = 200; $body = '{}'
        if ($r.Url.AbsolutePath -eq '/ping') { $body = '"pong"' }
        elseif ($auth -like '*DENIED*') { $code = 403; $body = '{"error":"forbidden"}' }
        elseif ($auth -like '*NOPLAN*') { $code = 404; $body = '{"error":"not found"}' }
        elseif ($auth -like '*BOOM*') { $code = 500; $body = '{"error":"boom"}' }
        elseif ($auth -like '*WEIRD*') { $body = '{"x":"y"}' }
        elseif ($auth -like '*VARIANT*') { $body = '{"data":{"total":7}}' }
        elseif ($r.Url.AbsolutePath -eq '/v1/query/web-analytics/visits/count' -and $r.Url.Query -match 'projectId=prj_test123') { $body = '{"count":42}' }
        $b = [Text.Encoding]::UTF8.GetBytes($body); $c.Response.StatusCode = $code; $c.Response.ContentType = 'application/json'; $c.Response.ContentLength64 = $b.Length
        $c.Response.OutputStream.Write($b, 0, $b.Length); $c.Response.Close()
    }
}
try {
    for ($i = 0; $i -lt 40; $i++) { try { [void](Invoke-WebRequest "http://127.0.0.1:$port/ping" -UseBasicParsing -TimeoutSec 1); break } catch { Start-Sleep -Milliseconds 250 } }
    $env:JARVIS_TEST_VERCEL_BASE = "http://127.0.0.1:$port"
    $v = Get-VisitesBriefing $depuis
    Verifier ($v.dispo -and $v.valeur -eq 42) 'visites lues : 42'
    $env:VERCEL_TEAM_ID = 'team_x'
    [void](Get-VisitesBriefing $depuis)
    $env:VERCEL_TOKEN = 'vercel_VARIANT_SECRET_1234567890'; $v = Get-VisitesBriefing $depuis
    Verifier ($v.dispo -and $v.valeur -eq 7) 'autre forme de réponse (data.total) lue : 7'
    $env:VERCEL_TOKEN = 'vercel_WEIRD_SECRET_1234567890'; $v = Get-VisitesBriefing $depuis
    Verifier (-not $v.dispo -and $v.raison -match 'non reconnue' -and -not $v.ContainsKey('valeur')) 'réponse inconnue : indisponible, aucun chiffre inventé'
    $env:VERCEL_TOKEN = 'vercel_DENIED_SECRET_1234567890'; $v = Get-VisitesBriefing $depuis
    Verifier (-not $v.dispo -and $v.raison -match 'accès refusé') 'HTTP 403 : « accès refusé »'
    $env:VERCEL_TOKEN = 'vercel_NOPLAN_SECRET_1234567890'; $v = Get-VisitesBriefing $depuis
    Verifier (-not $v.dispo -and $v.raison -match 'indisponibles pour ce projet ou ce forfait') 'HTTP 404 : analyses indisponibles pour ce forfait'
    $env:VERCEL_TOKEN = 'vercel_BOOM_SECRET_1234567890'; $v = Get-VisitesBriefing $depuis
    Verifier (-not $v.dispo -and $v.raison -match 'erreur HTTP 500') 'HTTP 500 : erreur nommée'
    $env:VERCEL_PROJECT_ID = 'prj bad;id'; $v = Get-VisitesBriefing $depuis
    Verifier (-not $v.dispo -and $v.raison -match 'illisible') 'identifiant de projet douteux : refusé sans appel'
    $env:VERCEL_PROJECT_ID = 'prj_test123'

    Write-Host '3) Confidentialité et lecture seule'
    $req = @(Get-Content $log)
    Verifier (@($req | Where-Object { $_ -notmatch '^GET ' -and $_ -notmatch '/ping' }).Count -eq 0) 'uniquement des requêtes GET'
    Verifier (@($req | Where-Object { $_ -match 'TOKENINURL' }).Count -eq 0) 'le jeton n''est jamais dans l''URL'
    Verifier (@($req | Where-Object { $_ -match 'NOAUTH' -and $_ -notmatch '/ping' }).Count -eq 0) 'jeton envoyé en en-tête Authorization'
    Verifier (@($req | Where-Object { $_ -match ' TEAM' }).Count -ge 1) 'VERCEL_TEAM_ID transmis quand il est renseigné'
    $tous = "$($v.raison) " + (Hide-Secrets 'x vercel_BOOM_SECRET_1234567890 y')
    Verifier ($tous -notmatch 'vercel_BOOM' -and $tous -match '\[SECRET\]') 'le jeton est masqué dans les textes et les raisons'
} finally {
    Stop-FauxServeur $srv
    foreach ($k in 'VERCEL_TOKEN', 'VERCEL_PROJECT_ID', 'VERCEL_TEAM_ID', 'JARVIS_TEST_VERCEL_BASE') { [Environment]::SetEnvironmentVariable($k, $null, 'Process') }
    Remove-Item $log -Force -ErrorAction SilentlyContinue
}

Write-Host '4) Affichage : non branchée = information, vraie erreur = raison lisible'
$base = @{ site = [pscustomobject]@{ ok = $true; code = 200 }; stats = @{ dispo = $false; raison = 'x' }; ca = @{ dispo = $false; raison = 'x' }; todo = @(); veille = '' }
$o = Format-ValeurSaas ($base + @{ visites = @{ dispo = $false; raison = 'visites du site : source non branchée (Vercel Analytics)' } })
Verifier ($o.visites -eq 'Source non branchée (Vercel Analytics)') 'visites non branchées : « Source non branchée (Vercel Analytics) »'
$o = Format-ValeurSaas ($base + @{ visites = @{ dispo = $false; raison = 'Vercel : accès refusé (droits de lecture à vérifier)' } })
Verifier ($o.visites -match '^Indisponible : Vercel : accès refusé') 'visites en erreur : « Indisponible : … » avec la raison'
$o = Format-ValeurSaas ($base + @{ visites = @{ dispo = $true; valeur = 42 } })
Verifier ($o.visites -eq '42 sur 24 h') 'visites lues : « 42 sur 24 h »'

if ($echecs) { Write-Host "`nÉCHEC : $echecs vérification(s) en échec." -ForegroundColor Red; exit 1 }
Write-Host "`nRÉUSSI"; exit 0
