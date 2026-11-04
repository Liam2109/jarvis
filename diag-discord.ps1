# Diagnostic des alertes Discord de maj-auto.ps1 (« alerte Discord échouée : ... (403) Interdit »). LECTURE SEULE, n'affiche AUCUN secret :
#   powershell -ExecutionPolicy Bypass -File diag-discord.ps1            (à lancer sur le portable serveur, dans le dossier de Jarvis)
#   powershell -ExecutionPolicy Bypass -File diag-discord.ps1 -Envoyer   (en plus : UN message de test dans le salon d'alerte, pour essayer vraiment l'envoi)
# Il refait EXACTEMENT ce que fait maj-auto (même jeton, même salon, même appel) et affiche seulement : présence du jeton (longueur et empreinte de 4 caractères pour le comparer à celui du PC),
# codes HTTP, code et texte d'erreur de Discord, nom du robot, nom des serveurs et du salon. Rien d'autre : ni le jeton, ni le contenu de .env.
# Ne modifie aucun fichier. -Api et -Racine servent aux tests (faux serveur local).
param([switch]$Envoyer, [string]$Api = 'https://discord.com/api/v10', [string]$Racine = $PSScriptRoot)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'lib\journal.ps1')
$script:JarvisRoot = $Racine
try { [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12 } catch { }
function Dire([string]$t, [string]$couleur = 'Gray') { if ($script:tok) { $t = $t.Replace($script:tok, '[SECRET]') }; Write-Host $t -ForegroundColor $couleur }      # (le jeton lui-même n'est jamais écrit, même par erreur)
function Fin4([string]$s) { if ($s.Length -le 4) { return '...' } '...' + $s.Substring($s.Length - 4) }
function Appeler([string]$methode, [string]$chemin, [hashtable]$entetes, $corps = $null) {
    # -> @{ code (0 = pas de réponse) ; json ; texte }. Ne lève jamais d'exception.
    try {
        $p = @{ Uri = "$Api$chemin"; Method = $methode; Headers = $entetes; UseBasicParsing = $true; TimeoutSec = 20 }
        if ($corps) { $p.Body = [Text.Encoding]::UTF8.GetBytes($corps); $p.ContentType = 'application/json; charset=utf-8' }
        $r = Invoke-WebRequest @p
        $j = $null; try { $j = $r.Content | ConvertFrom-Json } catch { }
        return @{ code = [int]$r.StatusCode; json = $j; texte = "$($r.Content)" }
    } catch {
        $code = 0; $txt = ''
        if ($_.Exception.Response) { try { $code = [int]$_.Exception.Response.StatusCode; $txt = (New-Object IO.StreamReader($_.Exception.Response.GetResponseStream())).ReadToEnd() } catch { } }
        $j = $null; try { $j = $txt | ConvertFrom-Json } catch { }
        return @{ code = $code; json = $j; texte = $txt; erreur = $_.Exception.Message }
    }
}
function Decrire($r) {
    if ($r.code -eq 0) { return "aucune réponse ($(Hide-Secrets "$($r.erreur)"))" }
    $d = "HTTP $($r.code)"
    if ($r.json -and $r.json.PSObject.Properties['code']) { $d += " ; Discord code $($r.json.code) : $($r.json.message)" }
    elseif ($r.code -ge 400 -and $r.texte) { $d += " ; réponse qui n'est pas de Discord (pare-feu, filtre du réseau ou protection du site) : « " + (Hide-Secrets ((($r.texte -replace '\s+', ' ')).Substring(0, [Math]::Min(90, ($r.texte -replace '\s+', ' ').Length)))) + " »" }
    $d
}
$sens = @{ 50001 = 'Missing Access : le robot n''est pas dans ce serveur, ou ne voit pas ce salon (salon d''un autre serveur, robot expulsé, droit « Voir le salon » retiré)'
           50013 = 'Missing Permissions : le robot voit le salon mais n''a pas le droit d''y écrire (« Envoyer des messages » retiré sur le salon ou le rôle du robot)'
           50007 = 'Impossible d''écrire à cet utilisateur (message privé fermé)'
           40333 = 'Discord a bloqué la requête (réseau ou en-tête de client refusé)'
           10003 = 'salon inconnu : l''identifiant du salon est faux ou le salon a été supprimé'
           0 = 'Discord refuse ce jeton ou ce client' }
Dire "Diagnostic Discord du $(Get-Date -Format 'yyyy-MM-dd HH:mm') sur $env:COMPUTERNAME (lecture seule, aucun secret affiché)" 'Cyan'

# 1) jeton et identifiant de Liam (présence seulement)
Import-JarvisEnv
$script:tok = [Environment]::GetEnvironmentVariable('DISCORD_BOT_TOKEN', 'Process'); $tok = $script:tok; $uid = [Environment]::GetEnvironmentVariable('DISCORD_USER_ID', 'Process')
if (-not $tok -or $tok -match '^xxx') { Dire '1) DISCORD_BOT_TOKEN : ABSENT de .env sur cette machine (maj-auto écrirait « alerte Discord impossible », pas « 403 ») : copiez le .env chiffré / lancez la synchro des clés.' 'Red'; exit 1 }
$empreinte = ([BitConverter]::ToString([Security.Cryptography.SHA256]::Create().ComputeHash([Text.Encoding]::UTF8.GetBytes($tok))) -replace '-', '').Substring(0, 4)
Dire "1) Jeton du robot : présent, $($tok.Length) caractères, empreinte $empreinte (lancez la même commande sur le PC : l'empreinte doit être IDENTIQUE si c'est le même robot). DISCORD_USER_ID : $(if ("$uid" -match '^\d{15,25}$') { 'présent' } else { 'ABSENT ou invalide (la mention de Liam manquera)' })"

# 2) le salon retenu, comme maj-auto
$canal = ''; $origine = ''
$cache = Read-JsonMemoire 'discord-salons.json'
if ($cache -and $cache.salons) { foreach ($k in 'systeme', 'jarvis') { if (-not $canal -and $cache.salons.PSObject.Properties[$k]) { $canal = "$($cache.salons.$k)"; $origine = "memoire\discord-salons.json (salon « $k », cache écrit par le pont de CETTE machine)" } } }
if (-not $canal) { $cfg = Import-ConfigJarvis; if ($cfg.discord_salons) { foreach ($k in 'systeme', 'jarvis') { if (-not $canal -and $cfg.discord_salons.PSObject.Properties[$k] -and "$($cfg.discord_salons.$k)") { $canal = "$($cfg.discord_salons.$k)"; $origine = "config.json (discord_salons.$k : l'identifiant écrit pour le PC)" } } } }
if ($canal -notmatch '^\d{5,25}$') { Dire '2) Aucun salon connu (ni memoire\discord-salons.json, ni config.json) : maj-auto écrirait « aucun salon connu », pas « 403 ».' 'Red'; exit 1 }
Dire "2) Salon utilisé par les alertes : identifiant $(Fin4 $canal), pris dans $origine"

# 3) le jeton : même appel que maj-auto (sans en-tête de client), puis avec un en-tête de client Discord
$r1 = Appeler 'GET' '/users/@me' @{ Authorization = "Bot $tok" }
$r2 = Appeler 'GET' '/users/@me' @{ Authorization = "Bot $tok"; 'User-Agent' = 'DiscordBot (jarvis-diag, 1.0)' }
Dire "3) Le jeton (appel comme maj-auto, sans en-tête de client) : $(Decrire $r1)"
Dire "   Le jeton (avec en-tête de client DiscordBot)        : $(Decrire $r2)"
if ($r1.code -ne 200 -and $r2.code -eq 200) { Dire '   -> Discord refuse l''appel SANS en-tête de client mais l''accepte AVEC : la cause est l''en-tête (maj-auto doit envoyer un User-Agent DiscordBot : corrigé dans cette version).' 'Yellow' }
if ($r1.code -in 401) { Dire '   -> 401 : jeton refusé (régénéré dans le portail Discord, ou mal recopié) : ce n''est PAS un 403.' 'Yellow' }
$bot = $(if ($r2.code -eq 200) { $r2.json } elseif ($r1.code -eq 200) { $r1.json } else { $null })
if ($bot) { Dire "   Robot : « $($bot.username) » (identifiant $(Fin4 "$($bot.id)"))" }

# 4) serveurs du robot et salon
$h = @{ Authorization = "Bot $tok"; 'User-Agent' = 'DiscordBot (jarvis-diag, 1.0)' }
$g = Appeler 'GET' '/users/@me/guilds' $h
if ($g.code -eq 200) { $noms = @($g.json | ForEach-Object { "« $($_.name) » ($(Fin4 "$($_.id)"))" }); Dire "4) Serveurs où ce robot est présent : $($noms.Count)$(if ($noms.Count) { ' : ' + ($noms -join ', ') })" } else { Dire "4) Liste des serveurs du robot : $(Decrire $g)" }
$c = Appeler 'GET' "/channels/$canal" $h
if ($c.code -eq 200) {
    Dire "5) Salon $(Fin4 $canal) : visible, nom « $($c.json.name) », serveur $(Fin4 "$($c.json.guild_id)")" 'Green'
    if ($g.code -eq 200 -and $c.json.guild_id -and -not (@($g.json | Where-Object { "$($_.id)" -eq "$($c.json.guild_id)" }).Count)) { Dire '   -> le robot n''est pas membre du serveur de ce salon.' 'Yellow' }
} else { Dire "5) Salon $(Fin4 $canal) : $(Decrire $c)" 'Yellow' }
$m = Appeler 'GET' "/channels/$canal/messages?limit=1" $h
Dire "6) Lecture du salon (droits « Voir le salon » et « Lire l'historique ») : $(Decrire $m)"
if ($Envoyer) {
    $e = Appeler 'POST' "/channels/$canal/messages" $h ((@{ content = 'Test de diagnostic Discord (diag-discord.ps1) : aucune action, vous pouvez ignorer ce message.'; allowed_mentions = @{ parse = @() } }) | ConvertTo-Json -Compress)
    Dire "7) Envoi d'un message de test (droit « Envoyer des messages ») : $(Decrire $e)"
    $dernier = $e
} else { Dire '7) Envoi non essayé (ajoutez -Envoyer pour poster UN message de test dans ce salon).'; $dernier = $null }

# lecture
$pire = @($r2, $c, $m, $dernier | Where-Object { $_ -and $_.code -ge 400 } | Select-Object -First 1)[0]
Write-Host ''
if ($pire) {
    $dc = $(if ($pire.json -and $pire.json.PSObject.Properties['code']) { [int]$pire.json.code } else { -1 })
    Dire "Lecture : $(if ($sens.ContainsKey($dc)) { $sens[$dc] } elseif ($pire.code -eq 403) { 'HTTP 403 sans code Discord : filtre du réseau ou de l''en-tête de client (voir 3).' } else { 'voir le code HTTP ci-dessus.' })" 'Yellow'
    Dire 'À faire : donner au robot, dans CE serveur et sur CE salon, les droits Voir le salon + Envoyer des messages + Lire l''historique ; ou, si le salon est celui du PC, créer le salon « système » et le lister dans memoire\discord-salons.json (écrit par le pont) ; vérifier que l''empreinte du jeton (1) est la même que sur le PC.'
} else { Dire 'Lecture : aucune erreur trouvée : les alertes devraient partir. Si maj-auto échoue encore, regardez la ligne « alerte Discord échouée » de logs\journal-*.md (elle indique maintenant le code Discord).' 'Green' }
exit 0
