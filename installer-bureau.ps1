# Jarvis sur le PC PRINCIPAL : démarrage automatique en VEILLE silencieuse à l'ouverture de session, réveil à la voix (« réveille-toi Jarvis ») ou par double claquement de mains.
#   powershell -ExecutionPolicy Bypass -File installer-bureau.ps1              (installe ; relançable sans risque : tout est idempotent)
#   powershell -ExecutionPolicy Bypass -File installer-bureau.ps1 -Simulation  (dit ce qui serait fait, ne change RIEN)
#   powershell -ExecutionPolicy Bypass -File installer-bureau.ps1 -Retirer     (supprime la tâche « Jarvis-Bureau »)
# Fait : config.local.json (réglages de CE PC, ignoré par git) : bureau_veille + veille_reveil + démarrage en sourdine + Ollama gardé chaud (keep_alive 24h) et DISCORD DÉSACTIVÉ
# (le bot tourne déjà sur le serveur : deux instances répondraient en double) ; les autres clés déjà présentes sont conservées · tâche planifiée « Jarvis-Bureau » (ouverture de session,
# 30 s de délai, session de l'utilisateur, sans droits administrateur, une seule instance) · retire l'ancienne tâche « Jarvis » (installer.ps1) qui ferait démarrer Jarvis deux fois.
# Au démarrage, Jarvis ne montre RIEN (ni HUD ni plein écran) et ne fait aucun son jusqu'au réveil. Aucune clé n'est lue, affichée ni écrite. Jamais exécuté par Claude (CLAUDE.md).
param([switch]$Simulation, [switch]$Retirer, [switch]$SeulementFonctions, [string]$Racine = $PSScriptRoot)
$ErrorActionPreference = 'Stop'
$script:Simulation = [bool]$Simulation
$script:Journal = New-Object System.Collections.Generic.List[string]
$script:NomTache = 'Jarvis-Bureau'

function Write-Etape([string]$t) { $script:Journal.Add($t); Write-Host $t }
function Invoke-Etape([string]$description, [scriptblock]$bloc) {
    if ($script:Simulation) { Write-Etape "[simulation] $description"; return $null }
    Write-Etape "-> $description"; & $bloc
}
function Get-ReglagesBureau {
    # Réglages de CE PC. discord_actif est TOUJOURS ramené à faux ; les autres clés ne sont posées que si elles manquent.
    [ordered]@{ discord_actif = $false; bureau_veille = $true; veille_reveil = $true; etat_au_demarrage = 'sourdine'; ollama = [pscustomobject]@{ keep_alive = '24h' } }
}
function Update-ConfigLocaleBureau([string]$racine) {
    # @{ statut : 'cree' | 'complete' | 'inchange' ; discord : 'desactive' | 'deja-desactive' }
    $f = Join-Path $racine 'config.local.json'
    $o = [ordered]@{}
    $existe = Test-Path $f
    if ($existe) { try { $c = Get-Content $f -Raw -Encoding UTF8 | ConvertFrom-Json; foreach ($p in $c.PSObject.Properties) { $o[$p.Name] = $p.Value } } catch { throw 'config.local.json est illisible : corrigez-le ou supprimez-le, puis relancez ce script' } }
    $avant = ($o | ConvertTo-Json -Depth 6 -Compress)
    $discord = if ($o.Contains('discord_actif') -and $o['discord_actif'] -eq $false) { 'deja-desactive' } else { 'desactive' }
    $regl = Get-ReglagesBureau
    foreach ($k in $regl.Keys) {
        $v = $regl[$k]
        if ($k -eq 'discord_actif') { $o[$k] = $false }
        elseif ($k -eq 'ollama') {
            if (-not $o.Contains('ollama') -or $null -eq $o['ollama']) { $o['ollama'] = $v }
            elseif (-not $o['ollama'].PSObject.Properties['keep_alive']) { $o['ollama'] | Add-Member -NotePropertyName keep_alive -NotePropertyValue $v.keep_alive }
        }
        elseif (-not $o.Contains($k)) { $o[$k] = $v }
    }
    $apres = ($o | ConvertTo-Json -Depth 6 -Compress)
    $statut = if (-not $existe) { 'cree' } elseif ($avant -ne $apres) { 'complete' } else { 'inchange' }
    if ($statut -ne 'inchange' -and -not $script:Simulation) { [IO.File]::WriteAllText($f, ($o | ConvertTo-Json -Depth 6), [Text.UTF8Encoding]::new($false)) }
    @{ statut = $statut; discord = $discord }
}
function Register-TacheBureau([string]$racine) {
    $user = "$env:USERDOMAIN\$env:USERNAME"
    $a = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$racine\jarvis.ps1`"" -WorkingDirectory $racine
    $t = New-ScheduledTaskTrigger -AtLogOn -User $user; $t.Delay = 'PT30S'
    $s = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -MultipleInstances IgnoreNew
    $p = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
    Invoke-Etape "tâche planifiée « $script:NomTache » : Jarvis démarre en veille silencieuse à l'ouverture de session (30 s après, session de $user)" {
        Register-ScheduledTask -TaskName $script:NomTache -Action $a -Trigger $t -Settings $s -Principal $p -Description 'Jarvis (PC principal) : veille silencieuse, réveil par la voix ou un double claquement' -Force | Out-Null }
    if (Get-ScheduledTask -TaskName 'Jarvis' -ErrorAction SilentlyContinue) { Invoke-Etape 'suppression de l''ancienne tâche « Jarvis » (remplacée par « Jarvis-Bureau »)' { Unregister-ScheduledTask -TaskName 'Jarvis' -Confirm:$false } }
    if (Get-ScheduledTask -TaskName 'Jarvis-Serveur' -ErrorAction SilentlyContinue) { Write-Etape 'ATTENTION : une tâche « Jarvis-Serveur » existe sur ce PC alors que ce n''est pas le serveur : supprimez-la (ce script ne la touche pas).' }
}
function Unregister-TacheBureau {
    if (Get-ScheduledTask -TaskName $script:NomTache -ErrorAction SilentlyContinue) { Invoke-Etape "suppression de la tâche « $script:NomTache »" { Unregister-ScheduledTask -TaskName $script:NomTache -Confirm:$false } }
    else { Write-Etape "OK  la tâche « $script:NomTache » n'existe pas" }
}
if ($SeulementFonctions) { return }

Write-Host "=== Jarvis (PC principal) : veille et réveil ($Racine)$(if ($Simulation) { ' — SIMULATION : rien n''est modifié' }) ===" -ForegroundColor Cyan
Set-Location $Racine
if ($Retirer) { Unregister-TacheBureau; Write-Host 'TERMINÉ.' -ForegroundColor Green; return }
if (-not (Test-Path (Join-Path $Racine 'jarvis.ps1'))) { throw "jarvis.ps1 introuvable dans $Racine" }
$r = Update-ConfigLocaleBureau $Racine
Write-Etape $(switch ($r.statut) { 'cree' { 'config.local.json créé (veille + réveil, démarrage en sourdine, Ollama chaud 24 h, Discord désactivé)' } 'complete' { 'config.local.json complété (vos autres réglages sont conservés)' } default { 'OK  config.local.json est déjà à jour' } })
Write-Etape $(if ($r.discord -eq 'desactive') { 'Discord DÉSACTIVÉ sur ce PC (discord_actif = false) : le bot reste sur le serveur' } else { 'OK  Discord est déjà désactivé sur ce PC' })
Register-TacheBureau $Racine
Write-Host ''
Write-Host 'TERMINÉ.' -ForegroundColor Green
Write-Host 'À faire : 1) fermer puis rouvrir la session Windows (ou redémarrer) pour tester ; 2) dire « Jarvis, calibre les claquements » une fois réveillé (5 s de silence) ; 3) tester « réveille-toi Jarvis » et le double claquement ; 4) vérifier qu''aucun Jarvis ne tourne déjà (arreter.ps1) avant le prochain démarrage.'
if (-not $Simulation) {
    New-Item -ItemType Directory (Join-Path $Racine 'logs') -Force | Out-Null
    Add-Content (Join-Path $Racine 'logs\installation-bureau.log') (@("# $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')") + $script:Journal) -Encoding UTF8
}
