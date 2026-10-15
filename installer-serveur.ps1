# Jarvis en SERVEUR 24/7 sur un PC Windows (vieux PC, sans écran ni micro obligatoires), mis à jour automatiquement depuis GitHub.
#   powershell -ExecutionPolicy Bypass -File installer-serveur.ps1            (installe ; relançable sans risque : tout est idempotent)
#   powershell -ExecutionPolicy Bypass -File installer-serveur.ps1 -Simulation (dit ce qui serait fait, ne change RIEN)
# Fait : Git, Python et Ollama via winget (s'ils manquent) · dépendances Python (requirements.txt) · voix Piper, cache Whisper « small » et petit modèle Vosk (hors git, téléchargés ici)
# · modèle Ollama choisi selon la RAM (8 Go ou moins : qwen2.5:3b ; sinon qwen2.5:7b) · .env créé depuis .env.example SANS JAMAIS écraser un .env existant (puis ouvert dans le Bloc-notes)
# · config.local.json (réglages de CETTE machine : mode serveur, Discord actif, CPU) créé s'il n'existe pas · veille désactivée sur secteur, fermeture du capot = ne rien faire
# · 2 tâches planifiées : « Jarvis-Serveur » (démarrage à l'ouverture de session) et « Jarvis-MajAuto » (mise à jour toutes les 10 minutes).
# Aucun droit administrateur requis pour les tâches (session de l'utilisateur) ; winget peut en demander pour Git / Ollama. Aucune clé n'est lue, affichée ni écrite par ce script.
# Jamais exécuté par Claude (CLAUDE.md : rien ne s'installe tout seul).
param([switch]$Simulation, [switch]$SansBlocNotes, [switch]$SansModeles, [switch]$SansTaches, [switch]$SansOllama, [switch]$SeulementFonctions, [string]$Racine = $PSScriptRoot)
$ErrorActionPreference = 'Stop'
$script:Simulation = [bool]$Simulation
$script:Journal = New-Object System.Collections.Generic.List[string]

function Write-Etape([string]$t) { $script:Journal.Add($t); Write-Host $t }
function Invoke-Etape([string]$description, [scriptblock]$bloc) {
    # Simulation : dit ce qui serait fait. Sinon : le fait.
    if ($script:Simulation) { Write-Etape "[simulation] $description"; return $null }
    Write-Etape "-> $description"; & $bloc
}
function Update-CheminSession {
    # Après un winget : les nouveaux programmes sont trouvables sans rouvrir la fenêtre.
    $m = [Environment]::GetEnvironmentVariable('Path', 'Machine'); $u = [Environment]::GetEnvironmentVariable('Path', 'User')
    $env:Path = (@($m, $u) | Where-Object { $_ }) -join ';'
}
function Test-Commande([string]$nom) { [bool](Get-Command $nom -ErrorAction SilentlyContinue) }
function Get-RamGo { try { [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 1) } catch { 8.0 } }
function Select-ModeleOllama([double]$ramGo) {
    # Petit PC : un modèle de 3 milliards de paramètres (≈ 2 Go) ; sinon celui de la version principale.
    if ($ramGo -le 8) { 'qwen2.5:3b' } else { 'qwen2.5:7b' }
}
function Get-CheminOllama {
    $c = Get-Command ollama -ErrorAction SilentlyContinue; if ($c) { return $c.Source }
    $p = Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe'; if (Test-Path $p) { return $p }
    $null
}
function Install-WingetSiAbsent([string]$id, [string]$commande, [string]$nom) {
    if (Test-Commande $commande) { Write-Etape "OK  $nom est déjà installé"; return }
    if (-not (Test-Commande 'winget')) { Write-Etape "ATTENTION : winget est absent : installez $nom à la main ($id), puis relancez ce script."; return }
    Invoke-Etape "installation de $nom (winget $id)" { & winget install --id $id -e --source winget --accept-package-agreements --accept-source-agreements --silent; Update-CheminSession }
}
function New-EnvSiNecessaire([string]$racine) {
    # Crée .env depuis .env.example SEULEMENT s'il n'existe pas. Retourne 'cree' | 'existe' | 'modele-absent'. N'écrase JAMAIS un .env existant ; ne lit ni n'affiche aucune valeur.
    $env1 = Join-Path $racine '.env'; $ex = Join-Path $racine '.env.example'
    if (Test-Path $env1) { return 'existe' }
    if (-not (Test-Path $ex)) { return 'modele-absent' }
    if ($script:Simulation) { return 'cree' }
    Copy-Item $ex $env1 -ErrorAction Stop
    'cree'
}
function New-ConfigLocale([string]$racine, [string]$modele) {
    # config.local.json : réglages PROPRES à cette machine (jamais suivi par git, donc jamais écrasé ni bloquant pour les mises à jour). Retourne 'cree' | 'existe'.
    $f = Join-Path $racine 'config.local.json'
    if (Test-Path $f) { return 'existe' }
    if ($script:Simulation) { return 'cree' }
    $o = [ordered]@{ mode_serveur = $true; discord_actif = $true; etat_au_demarrage = 'actif'; serveur_micro = 'auto'; moteur_voix_appareil = 'cpu'; whisper_peripherique = 'cpu'; ollama = [ordered]@{ modele = $modele } }
    [IO.File]::WriteAllText($f, ($o | ConvertTo-Json -Depth 4), [Text.UTF8Encoding]::new($false))
    'cree'
}
function Get-Fichier([string]$url, [string]$dest, [long]$tailleMin) {
    # Téléchargement si absent ou trop petit (relançable : un fichier complet n'est jamais retéléchargé). Écrit en .part puis renomme.
    if ((Test-Path $dest) -and (Get-Item $dest).Length -ge $tailleMin) { Write-Etape "OK  déjà présent : $(Split-Path $dest -Leaf)"; return }
    Invoke-Etape "téléchargement de $(Split-Path $dest -Leaf)" {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        $d = Split-Path $dest; if (-not (Test-Path $d)) { New-Item -ItemType Directory $d -Force | Out-Null }
        $tmp = "$dest.part"; Remove-Item $tmp -ErrorAction SilentlyContinue
        Invoke-WebRequest -Uri $url -OutFile $tmp -UseBasicParsing
        if ((Get-Item $tmp).Length -lt $tailleMin) { Remove-Item $tmp -Force; throw "fichier trop petit : $(Split-Path $dest -Leaf)" }
        Move-Item $tmp $dest -Force
    }
}
function Install-Modeles([string]$racine) {
    $base = 'https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR'
    $piper = Join-Path $racine 'voix\models\piper'
    foreach ($v in 'tom', 'siwis') {
        Get-Fichier "$base/$v/medium/fr_FR-$v-medium.onnx" (Join-Path $piper "fr_FR-$v-medium.onnx") 20MB
        Get-Fichier "$base/$v/medium/fr_FR-$v-medium.onnx.json" (Join-Path $piper "fr_FR-$v-medium.onnx.json") 1KB
    }
    $wh = Join-Path $racine 'voix\models\faster-whisper-small'
    if ((Test-Path (Join-Path $wh 'model.bin')) -and (Get-Item (Join-Path $wh 'model.bin')).Length -gt 400MB) { Write-Etape 'OK  déjà présent : cache Whisper « small »' }
    else { Invoke-Etape 'téléchargement du modèle Whisper « small » (≈ 0,5 Go, Hugging Face Systran/faster-whisper-small)' { & python -I -c "from huggingface_hub import snapshot_download; snapshot_download('Systran/faster-whisper-small', local_dir=r'$wh')"; if ($LASTEXITCODE -ne 0) { throw 'téléchargement Whisper échoué' } } }
    $vosk = Join-Path $racine 'voix\models\vosk-model-small-fr-0.22'
    if (Test-Path (Join-Path $vosk 'am')) { Write-Etape 'OK  déjà présent : petit modèle Vosk' }
    else {
        $zip = Join-Path $env:TEMP 'vosk-small-fr.zip'
        Get-Fichier 'https://alphacephei.com/vosk/models/vosk-model-small-fr-0.22.zip' $zip 30MB
        Invoke-Etape 'extraction du petit modèle Vosk' { Expand-Archive $zip -DestinationPath (Join-Path $racine 'voix\models') -Force; Remove-Item $zip -Force -ErrorAction SilentlyContinue }
    }
}
function Install-Ollama([string]$modele) {
    $exe = Get-CheminOllama
    if (-not $exe -and -not $script:Simulation) { Write-Etape 'ATTENTION : Ollama introuvable : le modèle local ne sera pas téléchargé (relancez ce script après installation).'; return }
    Invoke-Etape "modèle Ollama « $modele » (choisi selon la RAM)" {
        $lance = $null
        $repond = { try { [void](Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -TimeoutSec 3); $true } catch { $false } }
        if (-not (& $repond)) { $lance = Start-Process $exe -ArgumentList 'serve' -WindowStyle Hidden -PassThru; $fin = (Get-Date).AddSeconds(40); while (-not (& $repond) -and (Get-Date) -lt $fin) { Start-Sleep -Seconds 1 } }
        $tags = $null; try { $tags = Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -TimeoutSec 5 } catch { }
        if ($tags -and ($tags.models | Where-Object { $_.name -like "$modele*" })) { Write-Etape "OK  modèle déjà présent : $modele" } else { & $exe pull $modele }
        if ($lance) { try { Stop-Process -Id $lance.Id -Force } catch { } }      # (Jarvis démarre et arrête Ollama lui-même)
    }
}
function Set-VeilleServeur {
    # Jamais de veille sur secteur ; fermeture du capot = ne rien faire (secteur et batterie).
    $cmds = @('/change standby-timeout-ac 0', '/change hibernate-timeout-ac 0', '/setacvalueindex SCHEME_CURRENT SUB_BUTTONS LIDACTION 0', '/setdcvalueindex SCHEME_CURRENT SUB_BUTTONS LIDACTION 0', '/setactive SCHEME_CURRENT')
    foreach ($c in $cmds) {
        Invoke-Etape "powercfg $c" { & powercfg @($c -split ' ') | Out-Null; if ($LASTEXITCODE -ne 0) { Write-Etape "ATTENTION : powercfg $c a échoué (droits ?)" } }
    }
}
function Register-TachesServeur([string]$racine) {
    $user = "$env:USERDOMAIN\$env:USERNAME"
    $principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
    $ps = 'powershell.exe'
    # 1) Jarvis (mode serveur) à l'ouverture de session, relancé s'il s'arrête
    $a1 = New-ScheduledTaskAction -Execute $ps -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$racine\jarvis.ps1`"" -WorkingDirectory $racine
    $t1 = New-ScheduledTaskTrigger -AtLogOn -User $user; $t1.Delay = 'PT30S'
    $s1 = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) -StartWhenAvailable -RestartCount 5 -RestartInterval (New-TimeSpan -Minutes 1) -MultipleInstances IgnoreNew
    Invoke-Etape 'tâche planifiée « Jarvis-Serveur » : démarrage de Jarvis (mode serveur) à l''ouverture de session' {
        Register-ScheduledTask -TaskName 'Jarvis-Serveur' -Action $a1 -Trigger $t1 -Settings $s1 -Principal $principal -Description 'Jarvis en mode serveur (démarrage à la connexion)' -Force | Out-Null }
    # 2) Mise à jour automatique toutes les 10 minutes
    $a2 = New-ScheduledTaskAction -Execute $ps -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$racine\maj-auto.ps1`"" -WorkingDirectory $racine
    $t2 = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(2) -RepetitionInterval (New-TimeSpan -Minutes 10) -RepetitionDuration (New-TimeSpan -Days 3650)
    $s2 = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 40) -StartWhenAvailable -MultipleInstances IgnoreNew
    Invoke-Etape 'tâche planifiée « Jarvis-MajAuto » : mise à jour toutes les 10 minutes (maj-auto.ps1)' {
        Register-ScheduledTask -TaskName 'Jarvis-MajAuto' -Action $a2 -Trigger $t2 -Settings $s2 -Principal $principal -Description 'Mise à jour automatique de Jarvis depuis GitHub' -Force | Out-Null }
    # L'ancienne tâche « Jarvis » (installer.ps1) ferait démarrer Jarvis deux fois.
    if (Get-ScheduledTask -TaskName 'Jarvis' -ErrorAction SilentlyContinue) { Invoke-Etape 'suppression de l''ancienne tâche « Jarvis » (remplacée par « Jarvis-Serveur »)' { Unregister-ScheduledTask -TaskName 'Jarvis' -Confirm:$false } }
}
if ($SeulementFonctions) { return }

Write-Host "=== Installation de Jarvis en serveur ($Racine)$(if ($Simulation) { ' — SIMULATION : rien n''est modifié' }) ===" -ForegroundColor Cyan
Set-Location $Racine
$ram = Get-RamGo; $modele = Select-ModeleOllama $ram
Write-Etape "RAM détectée : $ram Go -> modèle Ollama : $modele"
# 1) Programmes
Install-WingetSiAbsent 'Git.Git' 'git' 'Git'
Install-WingetSiAbsent 'Python.Python.3.11' 'python' 'Python 3.11'
if (-not $SansOllama) { Install-WingetSiAbsent 'Ollama.Ollama' 'ollama' 'Ollama' }
Update-CheminSession
# 2) Dépendances Python
if (Test-Path (Join-Path $Racine 'requirements.txt')) { Invoke-Etape 'pip install -r requirements.txt' { & python -m pip install --disable-pip-version-check -r (Join-Path $Racine 'requirements.txt'); if ($LASTEXITCODE -ne 0) { throw 'pip a échoué' } } }
else { Write-Etape 'ATTENTION : requirements.txt est absent.' }
# 3) Modèles (hors git)
if (-not $SansModeles) { Install-Modeles $Racine }
if (-not $SansOllama) { Install-Ollama $modele }
# 4) .env et réglages de la machine
$e = New-EnvSiNecessaire $Racine
Write-Etape $(switch ($e) { 'cree' { ".env créé depuis .env.example : REMPLISSEZ-LE (jeton Discord, identifiant, clés)" } 'existe' { 'OK  .env existe déjà : conservé tel quel (jamais écrasé)' } default { 'ATTENTION : .env.example est absent' } })
if ($e -eq 'cree' -and -not $SansBlocNotes) { Invoke-Etape 'ouverture de .env dans le Bloc-notes' { Start-Process notepad.exe (Join-Path $Racine '.env') } }
$c = New-ConfigLocale $Racine $modele
Write-Etape $(if ($c -eq 'cree') { "config.local.json créé (mode serveur, Discord actif, CPU, modèle $modele)" } else { 'OK  config.local.json existe déjà : conservé' })
if (-not (Test-Path (Join-Path $Racine '.git'))) { Write-Etape 'ATTENTION : ce dossier n''est pas un clone git : la mise à jour automatique ne fonctionnera pas.' }
else { Invoke-Etape 'git : fusions en avance rapide seulement (pull.ff only)' { & git -C $Racine config pull.ff only } }
# 5) Alimentation et tâches
Set-VeilleServeur
if (-not $SansTaches) { Register-TachesServeur $Racine }
Write-Host ''
Write-Host 'TERMINÉ.' -ForegroundColor Green
Write-Host 'À faire une fois : 1) remplir .env (DISCORD_BOT_TOKEN, DISCORD_USER_ID, clés) ; 2) activer l''ouverture de session automatique de Windows (netplwiz) pour que « Jarvis-Serveur » démarre seul après une coupure de courant ; 3) redémarrer le PC une fois pour tester.'
if (-not $Simulation) {
    New-Item -ItemType Directory (Join-Path $Racine 'logs') -Force | Out-Null
    Add-Content (Join-Path $Racine 'logs\installation-serveur.log') (@("# $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')") + $script:Journal) -Encoding UTF8
}
