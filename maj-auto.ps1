# Mise à jour AUTOMATIQUE de Jarvis depuis GitHub (tâche planifiée « Jarvis-MajAuto », toutes les 10 minutes ; voir installer-serveur.ps1).
#   git fetch ; si origin/main a du nouveau : git pull --ff-only -> arrêt de Jarvis -> tests\tout.ps1 ->
#     tout est vert : Jarvis est relancé (nouvelle version)
#     un test est rouge : git reset --hard sur l'ancien commit, Jarvis relancé (ancienne version), journal + alerte Discord ; le commit refusé n'est pas réessayé tant qu'il reste le même.
# Ne touche JAMAIS à .env, memoire\, logs\ ni config.local.json (ignorés par git : ni pull ni reset ne les modifient).
# Options (tests / essais) : -Simulation (dit s'il y a une mise à jour, ne change rien) · -Racine · -ScriptTests · -SansArret · -SansRelance · -SansPip · -FichierAlerte (alerte écrite dans ce fichier au lieu de Discord).
param([switch]$Simulation, [string]$Racine = $PSScriptRoot, [string]$ScriptTests = 'tests\tout.ps1', [switch]$SansArret, [switch]$SansRelance, [switch]$SansPip, [string]$FichierAlerte = '', [string]$Branche = 'main')
$ErrorActionPreference = 'Stop'
Set-Location $Racine
. (Join-Path $Racine 'lib\journal.ps1')
$script:Sortie = New-Object System.Collections.Generic.List[string]
function Say([string]$t) { $script:Sortie.Add($t); Write-Host $t }
function Invoke-Git {
    $ErrorActionPreference = 'Continue'
    $o = & git -C $Racine @args 2>&1 | Out-String
    @{ code = $LASTEXITCODE; sortie = $o.Trim() }
}
function Send-AlerteMaj([string]$texte) {
    # Alerte Discord (salon système, mention de Liam) : REST direct, car Jarvis est arrêté pendant les tests. Le jeton n'est jamais affiché ni journalisé.
    $texte = Hide-Secrets $texte
    if ($FichierAlerte) { Set-Content $FichierAlerte $texte -Encoding UTF8; return }
    try {
        Import-JarvisEnv
        $tok = [Environment]::GetEnvironmentVariable('DISCORD_BOT_TOKEN', 'Process'); $uid = [Environment]::GetEnvironmentVariable('DISCORD_USER_ID', 'Process')
        if (-not $tok -or $tok -match '^xxx') { Write-Journal -Action 'Mise à jour auto' -Resultat 'alerte Discord impossible : DISCORD_BOT_TOKEN absent'; return }
        $canal = ''
        $cache = Read-JsonMemoire 'discord-salons.json'; if ($cache -and $cache.salons) { foreach ($k in 'systeme', 'jarvis') { if (-not $canal -and $cache.salons.PSObject.Properties[$k]) { $canal = "$($cache.salons.$k)" } } }
        if (-not $canal) { $cfg = Import-ConfigJarvis; if ($cfg.discord_salons) { foreach ($k in 'systeme', 'jarvis') { if (-not $canal -and $cfg.discord_salons.PSObject.Properties[$k] -and "$($cfg.discord_salons.$k)") { $canal = "$($cfg.discord_salons.$k)" } } } }
        if ($canal -notmatch '^\d{5,25}$') { Write-Journal -Action 'Mise à jour auto' -Resultat 'alerte Discord impossible : aucun salon connu'; return }
        $mention = $(if ($uid -match '^\d{15,25}$') { "<@$uid> " } else { '' })
        $corps = @{ content = ($mention + [char]0x26A0 + [char]0xFE0F + ' ' + $texte); allowed_mentions = @{ users = @($(if ($mention) { $uid })) } } | ConvertTo-Json -Depth 4 -Compress
        [void](Invoke-RestMethod -Uri "https://discord.com/api/v10/channels/$canal/messages" -Method Post -Headers @{ Authorization = "Bot $tok" } -Body ([Text.Encoding]::UTF8.GetBytes($corps)) -ContentType 'application/json; charset=utf-8' -TimeoutSec 20)
        Write-Journal -Action 'Mise à jour auto' -Resultat 'alerte Discord envoyée'
    } catch { Write-Journal -Action 'Mise à jour auto' -Resultat ("alerte Discord échouée : " + (Hide-Secrets $_.Exception.Message)) }
}
function Start-JarvisServeur {
    if ($SansRelance) { Say 'relance de Jarvis : ignorée (-SansRelance)'; return }
    Start-Process powershell.exe -ArgumentList '-NoProfile', '-ExecutionPolicy', 'Bypass', '-WindowStyle', 'Hidden', '-File', "`"$Racine\jarvis.ps1`"" -WindowStyle Hidden -WorkingDirectory $Racine | Out-Null
    Say 'Jarvis relancé'
}
function Stop-JarvisServeur {
    if ($SansArret) { Say 'arrêt de Jarvis : ignoré (-SansArret)'; return }
    $a = Join-Path $Racine 'arreter.ps1'
    if (Test-Path $a) { & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $a | Out-Null }
    Say 'Jarvis arrêté (arreter.ps1)'
}

# Un seul passage à la fois
$verrou = Get-FichierMemoire 'maj-auto.lock'
if ((Test-Path $verrou) -and ((Get-Date) - (Get-Item $verrou).LastWriteTime).TotalMinutes -lt 45) { Say 'mise à jour déjà en cours : rien à faire'; return }
if (-not (Test-Path (Join-Path $Racine '.git'))) { Write-Journal -Action 'Mise à jour auto' -Resultat 'ce dossier n''est pas un dépôt git'; Say 'pas un dépôt git'; exit 1 }
Set-Content $verrou (Get-Date).ToString('o') -Encoding ASCII
try {
    $f = Invoke-Git fetch origin $Branche
    if ($f.code -ne 0) { Write-Journal -Action 'Mise à jour auto' -Resultat ("fetch impossible (réseau ?) : " + (Hide-Secrets ($f.sortie -replace '\s+', ' '))); Say 'fetch impossible'; return }
    $ancien = (Invoke-Git rev-parse HEAD).sortie; $nouveau = (Invoke-Git rev-parse "origin/$Branche").sortie
    if ($ancien -eq $nouveau) { Say 'à jour'; return }
    $refuse = Get-FichierMemoire 'maj-auto-refuse.txt'
    if ((Test-Path $refuse) -and ((Get-Content $refuse -Raw).Trim() -eq $nouveau)) { Say "version $($nouveau.Substring(0, 7)) déjà refusée (tests rouges) : en attente d'un nouveau commit"; return }
    if ((Invoke-Git merge-base --is-ancestor $ancien $nouveau).code -ne 0) {
        $m = "mise à jour refusée : l'historique local ($($ancien.Substring(0, 7))) n'est pas un ancêtre de origin/$Branche ($($nouveau.Substring(0, 7))) ; rien n'a été changé"
        Write-Journal -Action 'Mise à jour auto' -Resultat $m; Send-AlerteMaj $m; Say $m; exit 2
    }
    Say "mise à jour disponible : $($ancien.Substring(0, 7)) -> $($nouveau.Substring(0, 7))"
    if ($Simulation) { Say '[simulation] rien n''est modifié'; return }
    if ((Invoke-Git status --porcelain --untracked-files=no).sortie) {
        $m = 'mise à jour refusée : des fichiers suivis par git ont été modifiés sur ce PC (mettez les réglages de cette machine dans config.local.json)'
        Write-Journal -Action 'Mise à jour auto' -Resultat $m; Send-AlerteMaj $m; Say $m; exit 3
    }
    $p = Invoke-Git pull --ff-only origin $Branche
    if ($p.code -ne 0) { $m = 'mise à jour refusée : git pull --ff-only a échoué'; Write-Journal -Action 'Mise à jour auto' -Resultat ($m + ' : ' + (Hide-Secrets ($p.sortie -replace '\s+', ' '))); Send-AlerteMaj $m; Say $m; exit 4 }
    Write-Journal -Action 'Mise à jour auto' -Resultat "pull réussi : $($ancien.Substring(0, 7)) -> $($nouveau.Substring(0, 7)) ; arrêt de Jarvis puis tests"
    Stop-JarvisServeur
    $rouge = ''
    $changes = @((Invoke-Git diff --name-only $ancien $nouveau).sortie -split "`n" | ForEach-Object { $_.Trim() })
    if (-not $SansPip -and ($changes -contains 'requirements.txt') -and (Test-Path (Join-Path $Racine 'requirements.txt'))) {
        & python -m pip install --disable-pip-version-check -r (Join-Path $Racine 'requirements.txt') 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) { $rouge = 'pip install -r requirements.txt a échoué' }
    }
    if (-not $rouge) {
        $t = Join-Path $Racine $ScriptTests
        if (-not (Test-Path $t)) { $rouge = "script de tests introuvable ($ScriptTests)" }
        else {
            $o = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $t 2>&1 | Out-String; $code = $LASTEXITCODE
            if ($code -ne 0) { $fin = @($o -split "`n" | Where-Object { $_ -match 'ECHEC|ROUGE|ÉCHEC' } | Select-Object -First 4) -join ' ; '; $rouge = "tests rouges (code $code)$(if ($fin) { ' : ' + $fin })" }
        }
    }
    if (-not $rouge) {
        Write-Journal -Action 'Mise à jour auto' -Resultat "tests verts : version $($nouveau.Substring(0, 7)) adoptée"
        Remove-Item $refuse -Force -ErrorAction SilentlyContinue
        Say "tests verts : version $($nouveau.Substring(0, 7)) adoptée"; Start-JarvisServeur; return
    }
    $r = Invoke-Git reset --hard $ancien
    Set-Content $refuse $nouveau -Encoding ASCII
    $m = "mise à jour $($nouveau.Substring(0, 7)) REFUSÉE ($(Hide-Secrets $rouge)) : retour à la version précédente $($ancien.Substring(0, 7))"
    Write-Journal -Action 'Mise à jour auto' -Resultat ($m + $(if ($r.code -ne 0) { ' ; ATTENTION : git reset a échoué' } else { '' }))
    Send-AlerteMaj $m; Say $m; Start-JarvisServeur; exit 5
} finally { Remove-Item $verrou -Force -ErrorAction SilentlyContinue }
