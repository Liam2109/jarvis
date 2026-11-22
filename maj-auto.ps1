# Mise à jour AUTOMATIQUE de Jarvis depuis GitHub (tâche planifiée « Jarvis-MajAuto », toutes les 10 minutes ; voir installer-serveur.ps1).
#   git fetch ; si origin/main a du nouveau : git pull --ff-only -> arrêt de Jarvis -> tests\tout.ps1 ->
#     tout est vert : Jarvis est relancé (nouvelle version)
#     un test est rouge : git reset --hard sur l'ancien commit, Jarvis relancé (ancienne version), journal + alerte Discord ; le commit refusé n'est pas réessayé tant qu'il reste le même.
#   Après des tests verts, SI B2B\agents\b2b.local.json existe (réglage propre à cette machine) : dépendances Python de B2B\requirements.txt puis tâches planifiées « Jarvis-B2B-<agent> » des seuls agents
#   actifs (lib\b2b-serveur.ps1, idempotent). Sans ce fichier (PC de bureau) : rien. Un échec de cette étape n'annule jamais la mise à jour de Jarvis.
#   Quand il n'y a RIEN à tirer (serveur déjà à jour, ou commits d'ici pas encore poussés), les tâches B2B MANQUANTES sont tout de même créées (22/11/2026) : un agent
#   ajouté à agents_actifs sans nouveau commit avait sinon une tâche qui n'arrivait jamais, donc une fausse alerte « Panne » chaque jour. Une tâche existante n'est pas touchée.
#   Local en avance (origin est un ancêtre du local) = « à jour », AUCUNE alerte. Vraie divergence (chacun a des commits que l'autre n'a pas) = refus + alerte, au plus une
#   fois toutes les -HeuresSilenceAlerte heures tant qu'elle n'est pas résolue (avant : une alerte identique toutes les 10 min).
# Ne touche JAMAIS aux fichiers de memoire\ de Liam (todo, notes, résumé), à logs\ ni à config.local.json (ignorés par git : ni pull ni reset ne les modifient) ; dans memoire\ il n'écrit
# et ne supprime que SES fichiers : son verrou, maj-auto-refuse.txt et maj-auto-alertes.json (heure du dernier envoi de chaque alerte). .env n'est écrit que par le déchiffrement ATOMIQUE de .env.chiffre
# (ancien .env dans .env.bak ; échec = ancien .env conservé + alerte ; mise à jour refusée = clés remises comme avant).
# Options (tests / essais) : -Simulation (dit s'il y a une mise à jour, ne change rien) · -Racine · -ScriptTests · -SansArret · -SansRelance · -SansPip · -FichierAlerte (alerte écrite dans ce fichier au lieu de Discord) · -HeuresSilenceAlerte.
param([switch]$Simulation, [string]$Racine = $PSScriptRoot, [string]$ScriptTests = 'tests\tout.ps1', [switch]$SansArret, [switch]$SansRelance, [switch]$SansPip, [string]$FichierAlerte = '', [string]$Branche = 'main', [double]$HeuresSilenceAlerte = 6)
$ErrorActionPreference = 'Stop'
Set-Location $Racine
. (Join-Path $Racine 'lib\journal.ps1')
if (Test-Path (Join-Path $Racine 'lib\env-chiffre.ps1')) { . (Join-Path $Racine 'lib\env-chiffre.ps1') }      # synchro chiffrée du .env (absente d'un très ancien clone : la 1re mise à jour l'apporte)
if (Test-Path (Join-Path $Racine 'lib\b2b-serveur.ps1')) { . (Join-Path $Racine 'lib\b2b-serveur.ps1') }      # agents B2B du serveur : dépendances Python + tâches planifiées (après un pull réussi et des tests verts)
$script:Sortie = New-Object System.Collections.Generic.List[string]
function Say([string]$t) { $script:Sortie.Add($t); Write-Host $t }
function Invoke-Git {
    $ErrorActionPreference = 'Continue'
    $o = & git -C $Racine @args 2>&1 | Out-String
    @{ code = $LASTEXITCODE; sortie = $o.Trim() }
}
function Test-AlerteEnSilence([string]$cle) {
    # Anti-boucle (22/11/2026) : une même alerte NON RÉSOLUE revenait à chaque passage (toutes les 10 min, ~300 messages Discord). Avec une clé, elle n'est
    # envoyée qu'une fois toutes les $HeuresSilenceAlerte heures. Retourne $true s'il faut se taire ; sinon note l'heure d'envoi et retourne $false.
    if (-not $cle) { return $false }
    $h = Read-JsonMemoire 'maj-auto-alertes.json' $null
    $o = @{}; if ($h) { foreach ($p in $h.PSObject.Properties) { $o[$p.Name] = "$($p.Value)" } }
    if ($o.ContainsKey($cle)) {
        try { if (((Get-Date) - [datetime]::Parse($o[$cle], [Globalization.CultureInfo]::InvariantCulture, [Globalization.DateTimeStyles]::RoundtripKind)).TotalHours -lt $HeuresSilenceAlerte) { return $true } } catch { }
    }
    $o[$cle] = (Get-Date).ToString('o'); Save-JsonMemoire 'maj-auto-alertes.json' $o
    $false
}
function Reset-AlerteSilence {
    # Plus rien à signaler (serveur à jour ou version adoptée) : le compteur de silence est oublié, la prochaine vraie alerte part tout de suite.
    Remove-Item (Get-FichierMemoire 'maj-auto-alertes.json') -Force -ErrorAction SilentlyContinue
}
function Send-AlerteMaj([string]$texte, [string]$Cle = '') {
    # Alerte Discord (salon système, mention de Liam) : REST direct, car Jarvis est arrêté pendant les tests. Le jeton n'est jamais affiché ni journalisé.
    $texte = Hide-Secrets $texte
    if ($Cle -and (Test-AlerteEnSilence $Cle)) {
        Write-Journal -Action 'Mise à jour auto' -Resultat "alerte « $Cle » déjà envoyée il y a moins de $HeuresSilenceAlerte h : pas renvoyée"
        Say "alerte déjà envoyée il y a moins de $HeuresSilenceAlerte h : pas renvoyée (silence)"; return
    }
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
        [void](Invoke-RestMethod -Uri "https://discord.com/api/v10/channels/$canal/messages" -Method Post -Headers @{ Authorization = "Bot $tok"; 'User-Agent' = 'DiscordBot (jarvis-maj-auto, 1.0)' } -Body ([Text.Encoding]::UTF8.GetBytes($corps)) -ContentType 'application/json; charset=utf-8' -TimeoutSec 20)
        Write-Journal -Action 'Mise à jour auto' -Resultat 'alerte Discord envoyée'
    } catch {
        $detail = ''; try { $dj = $_.ErrorDetails.Message | ConvertFrom-Json; if ($dj.code) { $detail = " [Discord code $($dj.code) : $($dj.message)]" } } catch { }      # le code d'erreur de Discord (50001 = salon non visible, 50013 = droit d'écrire manquant) : jamais le jeton
        Write-Journal -Action 'Mise à jour auto' -Resultat ("alerte Discord échouée : " + (Hide-Secrets $_.Exception.Message) + $detail + " ; diagnostic : powershell -File diag-discord.ps1")
    }
}
function Start-JarvisServeur {
    if ($SansRelance) { Say 'relance de Jarvis : ignorée (-SansRelance)'; return }
    Start-Process powershell.exe -ArgumentList '-NoProfile', '-ExecutionPolicy', 'Bypass', '-WindowStyle', 'Hidden', '-File', "`"$Racine\jarvis.ps1`"" -WindowStyle Hidden -WorkingDirectory $Racine | Out-Null
    Say 'Jarvis relancé'
}
function Sync-TachesManquantesB2B {
    # Rattrapage (22/11/2026) : les tâches « Jarvis-B2B-<agent> » n'étaient (re)créées qu'APRÈS un pull suivi de tests verts. Un agent ajouté à agents_actifs
    # sans nouveau commit n'avait donc jamais sa tâche, et panne-alerte le signalait « en panne » chaque jour (nettoyage-fichiers, relances, chiffres-serveur,
    # surveillant et les 2 superviseurs, le 22/11/2026). Seules les tâches MANQUANTES sont créées : une tâche existante n'est jamais touchée.
    if ($Simulation) { return }
    if (-not (Get-Command Sync-B2BTaches -ErrorAction SilentlyContinue)) { return }
    try {
        $s = Sync-B2BTaches $Racine -SeulementManquantes
        if ($s) { Say $s; foreach ($l in @($s -split "`n" | Where-Object { $_.Trim() })) { Write-Journal -Action 'B2B serveur' -Resultat $l } }
    } catch { Say "B2B : rattrapage des tâches ignoré (erreur : $($_.Exception.Message))" }
}
function Stop-JarvisServeur {
    if ($SansArret) { Say 'arrêt de Jarvis : ignoré (-SansArret)'; return }
    $a = Join-Path $Racine 'arreter.ps1'
    if (Test-Path $a) { & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $a | Out-Null }
    Say 'Jarvis arrêté (arreter.ps1)'
}

function Update-ClesDepuisChiffre {
    # Déchiffre .env.chiffre vers .env (atomique, sauvegarde .env.bak). Échec (mauvais mot de passe, fichier corrompu) : l'ancien .env est CONSERVÉ, journal + alerte Discord. Retourne le statut.
    if (-not (Get-Command Restore-EnvDepuisChiffre -ErrorAction SilentlyContinue)) { return 'absent' }
    $m = Read-MotDePasseDpapi
    try { $r = Restore-EnvDepuisChiffre $Racine $m } finally { Clear-Octets $m }
    switch ($r.statut) {
        'echec' { $msg = "clés (.env) NON mises à jour : $($r.raison). L'ancien .env est conservé ; vérifiez le mot de passe du serveur (installer-serveur.ps1)"; Write-Journal -Action 'Mise à jour auto' -Resultat $msg; Send-AlerteMaj $msg; Say $msg }
        'cree' { Write-Journal -Action 'Mise à jour auto' -Resultat '.env créé depuis .env.chiffre'; Say 'clés (.env) créées depuis .env.chiffre' }
        'mis-a-jour' { Write-Journal -Action 'Mise à jour auto' -Resultat '.env mis à jour depuis .env.chiffre (ancien .env sauvegardé dans .env.bak)'; Say 'clés (.env) mises à jour depuis .env.chiffre (sauvegarde .env.bak)' }
    }
    $r.statut
}

# Un seul passage à la fois
$verrou = Get-FichierMemoire 'maj-auto.lock'
if ((Test-Path $verrou) -and ((Get-Date) - (Get-Item $verrou).LastWriteTime).TotalMinutes -lt 45) { Say 'mise à jour déjà en cours : rien à faire'; return }
if (-not (Test-Path (Join-Path $Racine '.git'))) { Write-Journal -Action 'Mise à jour auto' -Resultat 'ce dossier n''est pas un dépôt git'; Say 'pas un dépôt git'; exit 1 }
Set-Content $verrou (Get-Date).ToString('o') -Encoding ASCII
try {
    if (-not $Simulation -and -not (Test-Path (Join-Path $Racine '.env')) -and (Test-Path (Join-Path $Racine '.env.chiffre'))) { [void](Update-ClesDepuisChiffre) }      # 1er démarrage : .env absent -> créé depuis .env.chiffre
    $f = Invoke-Git fetch origin $Branche
    if ($f.code -ne 0) { Write-Journal -Action 'Mise à jour auto' -Resultat ("fetch impossible (réseau ?) : " + (Hide-Secrets ($f.sortie -replace '\s+', ' '))); Say 'fetch impossible'; return }
    $ancien = (Invoke-Git rev-parse HEAD).sortie; $nouveau = (Invoke-Git rev-parse "origin/$Branche").sortie
    if ($ancien -eq $nouveau) { Say 'à jour'; Reset-AlerteSilence; Sync-TachesManquantesB2B; return }
    $refuse = Get-FichierMemoire 'maj-auto-refuse.txt'
    if ((Test-Path $refuse) -and ((Get-Content $refuse -Raw).Trim() -eq $nouveau)) { Say "version $($nouveau.Substring(0, 7)) déjà refusée (tests rouges) : en attente d'un nouveau commit"; return }
    if ((Invoke-Git merge-base --is-ancestor $ancien $nouveau).code -ne 0) {
        if ((Invoke-Git merge-base --is-ancestor $nouveau $ancien).code -eq 0) {
            # Local EN AVANCE : des commits faits ICI ne sont pas encore poussés. Ce n'est PAS une divergence (origin est un ancêtre du local) : il n'y a simplement
            # rien à tirer. Avant le 22/11/2026 ce cas déclenchait l'alerte « l'historique local n'est pas un ancêtre de origin/main » à chaque passage.
            $n = (Invoke-Git rev-list --count "$nouveau..$ancien").sortie
            Say "à jour : $n commit(s) fait(s) ici ne sont pas encore poussés vers origin/$Branche ; rien à tirer"
            Reset-AlerteSilence; Sync-TachesManquantesB2B; return
        }
        $m = "mise à jour refusée : l'historique local ($($ancien.Substring(0, 7))) a divergé de origin/$Branche ($($nouveau.Substring(0, 7))) : chacun a des commits que l'autre n'a pas ; rien n'a été changé"
        Write-Journal -Action 'Mise à jour auto' -Resultat $m; Send-AlerteMaj $m -Cle 'historique-divergent'; Say $m; exit 2
    }
    Say "mise à jour disponible : $($ancien.Substring(0, 7)) -> $($nouveau.Substring(0, 7))"
    if ($Simulation) { Say '[simulation] rien n''est modifié'; return }
    if ((Invoke-Git status --porcelain --untracked-files=no).sortie) {
        $m = 'mise à jour refusée : des fichiers suivis par git ont été modifiés sur ce PC (mettez les réglages de cette machine dans config.local.json)'
        Write-Journal -Action 'Mise à jour auto' -Resultat $m; Send-AlerteMaj $m -Cle 'modifs-locales'; Say $m; exit 3
    }
    $p = Invoke-Git pull --ff-only origin $Branche
    if ($p.code -ne 0) { $m = 'mise à jour refusée : git pull --ff-only a échoué'; Write-Journal -Action 'Mise à jour auto' -Resultat ($m + ' : ' + (Hide-Secrets ($p.sortie -replace '\s+', ' '))); Send-AlerteMaj $m; Say $m; exit 4 }
    Write-Journal -Action 'Mise à jour auto' -Resultat "pull réussi : $($ancien.Substring(0, 7)) -> $($nouveau.Substring(0, 7)) ; arrêt de Jarvis puis tests"
    $changes = @((Invoke-Git diff --name-only $ancien $nouveau).sortie -split "`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ })
    Stop-JarvisServeur
    $rouge = ''
    $envMaj = $false
    if ($changes -contains '.env.chiffre') { $envMaj = ((Update-ClesDepuisChiffre) -in 'mis-a-jour', 'cree') }
    if ($changes.Count -gt 0 -and @($changes | Where-Object { $_ -ne '.env.chiffre' }).Count -eq 0) {      # seules les clés ont changé : aucun code nouveau, donc pas de tests ; Jarvis est simplement redémarré
        Write-Journal -Action 'Mise à jour auto' -Resultat "clés seules : redémarrage de Jarvis ($($nouveau.Substring(0, 7)))"
        Say 'clés seules : pas de tests, redémarrage de Jarvis'; Start-JarvisServeur; return
    }
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
        Reset-AlerteSilence
        Say "tests verts : version $($nouveau.Substring(0, 7)) adoptée"
        if (Get-Command Update-B2BServeur -ErrorAction SilentlyContinue) {      # agents B2B : requirements + tâches planifiées des agents ACTIFS seulement (b2b.local.json) ; sans réglage B2B sur cette machine : rien
            $b2b = Update-B2BServeur $Racine -SansPip:$SansPip; if ($b2b) { Say $b2b }
            if ($script:B2BPipEchec) { Send-AlerteMaj 'agents B2B : pip install -r B2B\requirements.txt a échoué sur le serveur (Jarvis est à jour ; vérifier Python et le réseau)' }
        }
        Start-JarvisServeur; return
    }
    $r = Invoke-Git reset --hard $ancien
    if ($envMaj -and (Test-Path (Join-Path $Racine '.env.bak'))) { Copy-Item (Join-Path $Racine '.env.bak') (Join-Path $Racine '.env') -Force; Write-Journal -Action 'Mise à jour auto' -Resultat 'clés (.env) remises à l''état d''avant la mise à jour refusée'; Say 'clés (.env) remises à l''état d''avant' }
    Set-Content $refuse $nouveau -Encoding ASCII
    $m = "mise à jour $($nouveau.Substring(0, 7)) REFUSÉE ($(Hide-Secrets $rouge)) : retour à la version précédente $($ancien.Substring(0, 7))"
    Write-Journal -Action 'Mise à jour auto' -Resultat ($m + $(if ($r.code -ne 0) { ' ; ATTENTION : git reset a échoué' } else { '' }))
    Send-AlerteMaj $m; Say $m; Start-JarvisServeur; exit 5
} finally { Remove-Item $verrou -Force -ErrorAction SilentlyContinue }
