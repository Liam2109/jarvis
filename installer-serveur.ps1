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
. (Join-Path $PSScriptRoot 'lib\env-chiffre.ps1')      # synchro chiffrée du .env (mot de passe protégé par DPAPI)

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
# ---------- Python : un VRAI Python 3.11 (jamais le faux raccourci du Microsoft Store) ----------
$script:PythonExe = ''
$script:DossiersPythonParDefaut = @((Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311'), 'C:\Program Files\Python311', 'C:\Python311')      # (tests : vidé)
function Test-CheminWindowsApps([string]$chemin) { "$chemin" -match '(?i)[\\/]WindowsApps[\\/]' }
function Find-PythonReel {
    # Retourne @{ exe; version } pour un Python 3.11 qui S'EXÉCUTE vraiment (« --version » ou « py -3.11 »), ou $null. Tout python.exe situé dans WindowsApps (le raccourci du Store,
    # qui n'est pas un Python et ouvrirait le Store) est ignoré et JAMAIS exécuté.
    $exes = New-Object System.Collections.Generic.List[string]
    $py = @(Get-Command py -All -ErrorAction SilentlyContinue | Where-Object { $_.CommandType -eq 'Application' -and -not (Test-CheminWindowsApps $_.Source) }) | Select-Object -First 1
    if ($py) {
        try { $o = (& $py.Source -3.11 -c "import sys; print(sys.executable)" 2>$null | Out-String).Trim(); if ($LASTEXITCODE -eq 0 -and $o -and (Test-Path $o) -and -not (Test-CheminWindowsApps $o)) { $exes.Add($o) } } catch { }
    }
    foreach ($c in @(Get-Command python -All -ErrorAction SilentlyContinue | Where-Object { $_.CommandType -eq 'Application' })) { if (-not (Test-CheminWindowsApps $c.Source)) { $exes.Add($c.Source) } }
    foreach ($d in $script:DossiersPythonParDefaut) { $e = Join-Path $d 'python.exe'; if ((Test-Path $e) -and -not (Test-CheminWindowsApps $e)) { $exes.Add($e) } }
    foreach ($e in ($exes | Select-Object -Unique)) {
        try { $v = (& $e --version 2>&1 | Out-String).Trim(); if ($LASTEXITCODE -eq 0 -and $v -match '^Python 3\.11\.\d+') { return @{ exe = $e; version = $v } } } catch { }
    }
    $null
}
function Install-PythonSiAbsent {
    $p = Find-PythonReel
    if ($p) { $script:PythonExe = $p.exe; Write-Etape "OK  Python 3.11 est déjà installé ($($p.version) : $($p.exe))"; return }
    if (-not (Test-Commande 'winget')) { Write-Etape "ATTENTION : aucun vrai Python 3.11 (le raccourci du Microsoft Store ne compte pas) et winget est absent : installez Python 3.11 à la main (python.org), puis relancez ce script."; return }
    Invoke-Etape "installation de Python 3.11 (winget Python.Python.3.11) : aucun vrai Python 3.11 détecté (le raccourci du Microsoft Store ne compte pas)" {
        & winget install --id Python.Python.3.11 -e --source winget --accept-package-agreements --accept-source-agreements --silent
        Update-CheminSession      # le PATH de CETTE session est actualisé avant pip
        $q = Find-PythonReel
        if (-not $q) { Write-Etape 'ATTENTION : Python 3.11 n''est pas encore trouvable après l''installation : fermez cette fenêtre, ouvrez-en une nouvelle et relancez ce script.'; return }
        $script:PythonExe = $q.exe
        $env:Path = "$(Split-Path $q.exe);$(Join-Path (Split-Path $q.exe) 'Scripts');$env:Path"      # ce Python passe devant le faux raccourci pour la suite du script
        Write-Etape "OK  Python 3.11 installé ($($q.version) : $($q.exe))"
    }
    if ($script:Simulation) { $script:PythonExe = 'python' }
}
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
function Initialize-ClesServeur([string]$racine) {
    # Dépôt avec .env.chiffre : le mot de passe est demandé UNE fois (saisie masquée, 3 essais), vérifié sur .env.chiffre, puis gardé protégé par DPAPI (lié au compte Windows de ce PC), HORS du dépôt.
    # Retourne 'sans-chiffre' | 'simulation' | 'ok' | 'echec'. Le mot de passe n'est jamais affiché ni écrit en clair.
    if (-not (Test-Path (Join-Path $racine '.env.chiffre'))) { return 'sans-chiffre' }
    if ($script:Simulation) { Write-Etape '[simulation] demander UNE fois le mot de passe des clés (saisie masquée), le garder protégé par DPAPI hors du dépôt, puis créer .env depuis .env.chiffre'; return 'simulation' }
    $texte = Get-Content (Join-Path $racine '.env.chiffre') -Raw -Encoding UTF8
    $m = Read-MotDePasseDpapi
    if ($m) { $t = Unprotect-EnvTexte $texte $m; Clear-Octets $m; if ($t.ok) { Clear-Octets $t.octets; Write-Etape 'OK  mot de passe des clés déjà enregistré (protégé par DPAPI)'; return 'ok' } }
    for ($i = 1; $i -le 3; $i++) {
        $s = Read-MotDePasseSaisie "Mot de passe des clés (.env.chiffre) - essai $i sur 3"
        $b = ConvertTo-OctetsMotDePasse $s; $t = Unprotect-EnvTexte $texte $b; Clear-Octets $b
        if ($t.ok) { Clear-Octets $t.octets; Save-MotDePasseDpapi $s; Write-Etape "mot de passe des clés enregistré, protégé par DPAPI ($(Get-FichierMotDePasseServeur))"; return 'ok' }
        Write-Host "Mot de passe incorrect ou fichier altéré ($($t.raison))."
    }
    Write-Etape 'ATTENTION : mot de passe des clés non validé : .env n''a pas été créé depuis .env.chiffre.'
    'echec'
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
    else { Invoke-Etape 'téléchargement du modèle Whisper « small » (≈ 0,5 Go, Hugging Face Systran/faster-whisper-small)' { & $script:PythonExe -I -c "from huggingface_hub import snapshot_download; snapshot_download('Systran/faster-whisper-small', local_dir=r'$wh')"; if ($LASTEXITCODE -ne 0) { throw 'téléchargement Whisper échoué' } } }
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
Install-PythonSiAbsent
if (-not $SansOllama) { Install-WingetSiAbsent 'Ollama.Ollama' 'ollama' 'Ollama' }
Update-CheminSession
# 2) Dépendances Python
if (Test-Path (Join-Path $Racine 'requirements.txt')) { Invoke-Etape 'pip install -r requirements.txt' { if (-not $script:PythonExe) { throw 'aucun Python 3.11 utilisable : relancez ce script dans une nouvelle fenêtre' }; & $script:PythonExe -m pip install --disable-pip-version-check -r (Join-Path $Racine 'requirements.txt'); if ($LASTEXITCODE -ne 0) { throw 'pip a échoué' } } }
else { Write-Etape 'ATTENTION : requirements.txt est absent.' }
# 3) Modèles (hors git)
if (-not $SansModeles) { Install-Modeles $Racine }
if (-not $SansOllama) { Install-Ollama $modele }
# 4) .env et réglages de la machine
$cles = Initialize-ClesServeur $Racine
$e = 'existe'
if ($cles -eq 'ok') {
    $r = Initialize-EnvDepuisChiffre $Racine
    Write-Etape $(if ($r.statut -eq 'cree') { '.env créé depuis .env.chiffre (clés synchronisées depuis le PC principal)' } elseif (Test-Path (Join-Path $Racine '.env')) { 'OK  .env existe déjà : conservé tel quel (les prochaines modifications arrivent par la mise à jour automatique)' } else { "ATTENTION : .env non créé ($($r.raison))" })
} elseif ($cles -eq 'simulation') { $e = 'simulation' }
else {
    $e = New-EnvSiNecessaire $Racine
    Write-Etape $(switch ($e) { 'cree' { ".env créé depuis .env.example : REMPLISSEZ-LE (jeton Discord, identifiant, clés)" } 'existe' { 'OK  .env existe déjà : conservé tel quel (jamais écrasé)' } default { 'ATTENTION : .env.example est absent' } })
}
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
