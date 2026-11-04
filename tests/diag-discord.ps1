# Test SILENCIEUX de diag-discord.ps1 (diagnostic des alertes Discord du portable) : faux serveur local 127.0.0.1 (aucun accès à Discord), faux jeton, dossier temporaire.
# Vérifie : le diagnostic dit la cause (403, code Discord 50001, en-tête de client, serveurs du robot), n'affiche JAMAIS le jeton, n'écrit rien, n'envoie rien sans -Envoyer.
$ErrorActionPreference = 'Stop'
$env:JARVIS_TEST = '1'
$Root = Split-Path -Parent $PSScriptRoot
$echecs = 0
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }
$TR = Join-Path $env:TEMP ('jarvis-test-diag-' + [guid]::NewGuid().ToString('N').Substring(0, 8)); New-Item -ItemType Directory $TR, "$TR\memoire" | Out-Null
$jeton = 'MTIzNDU2Nzg5MDEyMzQ1Njc4.GabcDE.' + ('x7Q' * 9)      # faux jeton de la forme d'un jeton de robot
"DISCORD_BOT_TOKEN=$jeton`r`nDISCORD_USER_ID=123456789012345678`r`n" | Set-Content "$TR\.env" -Encoding UTF8
'{ "salons": { "jarvis": "555666777888999000" } }' | Set-Content "$TR\memoire\discord-salons.json" -Encoding UTF8
$port = 47800 + (Get-Random -Maximum 150)
$srv = Start-Job -ArgumentList $port -ScriptBlock {
    param($port)
    $l = New-Object Net.HttpListener; $l.Prefixes.Add("http://127.0.0.1:$port/"); $l.Start(); $fin = (Get-Date).AddSeconds(60)
    while ((Get-Date) -lt $fin) {
        $t = $l.GetContextAsync(); while (-not $t.Wait(500)) { if ((Get-Date) -gt $fin) { break } }; if (-not $t.IsCompleted) { break }
        $c = $t.Result; $u = $c.Request.Url.AbsolutePath; $ua = "$($c.Request.UserAgent)"; $code = 200; $corps = '{}'
        if ($u -eq '/users/@me') { if ($ua -match 'DiscordBot') { $corps = '{"id":"1234567890","username":"RobotTest"}' } else { $code = 403; $corps = '{"message":"Forbidden","code":40333}' } }
        elseif ($u -eq '/users/@me/guilds') { $corps = '[{"id":"999000111","name":"Serveur du PC"}]' }
        elseif ($u -like '/channels/555666777888999000*') { $code = 403; $corps = '{"message":"Missing Access","code":50001}' }
        $b = [Text.Encoding]::UTF8.GetBytes($corps); $c.Response.StatusCode = $code; $c.Response.ContentType = 'application/json'; $c.Response.OutputStream.Write($b, 0, $b.Length); $c.Response.Close()
    }
    $l.Stop()
}
try {
    Start-Sleep -Milliseconds 800
    Write-Host '1) Diagnostic sans -Envoyer'
    $avant = @(Get-ChildItem $TR -Recurse -File | ForEach-Object { "$($_.FullName):$($_.Length)" }) -join '|'
    $sortie = & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Root 'diag-discord.ps1') -Api "http://127.0.0.1:$port" -Racine $TR 2>&1 | Out-String; $code = $LASTEXITCODE
    Verifier ($code -eq 0 -and $sortie -match 'Diagnostic Discord') 'le diagnostic se lance et se termine'
    Verifier ($sortie -notmatch [regex]::Escape($jeton) -and $sortie -notmatch 'MTIzNDU2' -and $sortie -notmatch '(x7Q){3}') 'le jeton n''est affiché NULLE PART (ni entier, ni en morceau)'
    Verifier ($sortie -match 'présent, 59 caractères, empreinte [0-9A-F]{4}') 'jeton : présence, longueur et empreinte de 4 caractères seulement'
    Verifier ($sortie -match 'discord-salons\.json' -and $sortie -match '\.\.\.9000') 'salon : origine (cache du pont) et fin de l''identifiant seulement'
    Verifier ($sortie -match 'SANS en-tête|sans en-tête de client\)\s*:\s*HTTP 403' -and $sortie -match 'RobotTest' -and $sortie -match 'User-Agent DiscordBot|en-tête de client DiscordBot|en-tête est la cause|cause est l.en-tête') 'le cas « refusé sans en-tête de client, accepté avec » est reconnu'
    Verifier ($sortie -match 'Discord code 50001 : Missing Access') 'le code d''erreur de Discord (50001) est affiché'
    Verifier ($sortie -match 'Missing Access : le robot n''est pas dans ce serveur') 'la lecture explique la cause probable en français'
    Verifier ($sortie -match 'Serveur du PC') 'les serveurs où le robot est présent sont listés'
    Verifier ($sortie -match 'Envoi non essayé') 'aucun message n''est envoyé sans -Envoyer'
    $apres = @(Get-ChildItem $TR -Recurse -File | ForEach-Object { "$($_.FullName):$($_.Length)" }) -join '|'
    Verifier ($avant -eq $apres) 'aucun fichier créé ni modifié par le diagnostic'
    Write-Host '2) Sans jeton'
    Remove-Item "$TR\.env" -Force; $s2 = & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Root 'diag-discord.ps1') -Api "http://127.0.0.1:$port" -Racine $TR 2>&1 | Out-String
    Verifier ($s2 -match 'ABSENT') 'jeton absent : dit clairement que ce n''est pas un 403'
    Write-Host '3) Code'
    $d = Get-Content (Join-Path $Root 'diag-discord.ps1') -Raw -Encoding UTF8
    Verifier ($d -notmatch 'Invoke-RestMethod .*-Method Post(?!.*Envoyer)' -and $d -match 'if \(\$Envoyer\)') 'le seul envoi est protégé par -Envoyer'
    $mc = Get-Content (Join-Path $Root 'maj-auto.ps1') -Raw -Encoding UTF8
    Verifier ($mc -match "'User-Agent' = 'DiscordBot" -and $mc -match 'Discord code' -and $mc -match 'diag-discord\.ps1') 'maj-auto.ps1 : en-tête de client Discord, code d''erreur de Discord dans le journal, renvoi vers le diagnostic'
    Verifier (([IO.File]::ReadAllBytes((Join-Path $Root 'diag-discord.ps1'))[0..2] -join ',') -eq '239,187,191') 'diag-discord.ps1 : UTF-8 avec BOM'
} finally {
    Stop-Job $srv -ErrorAction SilentlyContinue; Remove-Job $srv -Force -ErrorAction SilentlyContinue
    Remove-Item $TR -Recurse -Force -ErrorAction SilentlyContinue
}
if ($echecs) { Write-Host "`nÉCHEC : $echecs vérification(s) en échec." -ForegroundColor Red; exit 1 }
Write-Host "`nRÉUSSI"; exit 0
