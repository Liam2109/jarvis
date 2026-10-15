# Test SILENCIEUX du mode serveur 24/7 : dépôt git (ce qui serait commité, gros fichiers, secrets), requirements.txt, config.local.json, mode serveur, installer-serveur.ps1 (fonctions + SIMULATION,
# rien n'est installé), maj-auto.ps1 sur de VRAIS petits dépôts git temporaires (origine locale, aucun réseau, aucun push vers GitHub, Jarvis jamais lancé ni arrêté). Aucun secret affiché.
# Code de sortie 0 = réussi.
$ErrorActionPreference = 'Stop'
$env:JARVIS_TEST = '1'
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $Root 'lib\journal.ps1')
$TR = Join-Path $env:TEMP ('jarvis-test-' + [guid]::NewGuid().ToString('N').Substring(0, 8)); New-Item -ItemType Directory $TR, "$TR\memoire", "$TR\logs" | Out-Null; $script:JarvisRoot = $TR
'# To-do' | Set-Content "$TR\memoire\todo.md" -Encoding UTF8; '# N' | Set-Content "$TR\memoire\notes.md" -Encoding UTF8; '# R' | Set-Content "$TR\memoire\resume.md" -Encoding UTF8
$Config = Get-Content $(if ($env:JARVIS_CONFIG -and (Test-Path $env:JARVIS_CONFIG)) { $env:JARVIS_CONFIG } else { Join-Path $Root 'config.json' }) -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($l in 'voix', 'business', 'permissions', 'actions', 'coffre', 'entrees', 'ecrans', 'tableau', 'visage', 'sons', 'raccourcis', 'cerveau', 'cerveau-local', 'veille', 'memoire', 'rapide', 'discretion', 'modejeu', 'competences', 'marche', 'priorite', 'comprehension', 'routeur', 'pc', 'bureau', 'salle-marche', 'matin', 'discord') { . (Join-Path $Root "lib\$l.ps1") }
$script:JarvisRoot = $TR
$echecs = 0
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }
function Fixer([string]$cle, $val) { if ($Config.PSObject.Properties[$cle]) { $Config.$cle = $val } else { $Config | Add-Member -NotePropertyName $cle -NotePropertyValue $val } }
function Effacer([string]$cle) { if ($Config.PSObject.Properties[$cle]) { $Config.PSObject.Properties.Remove($cle) } }
function Hash([string]$f) { if (Test-Path $f) { (Get-FileHash $f).Hash } else { '' } }
$vraie = Get-Content (Join-Path $Root 'config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$aGit = [bool](Get-Command git -ErrorAction SilentlyContinue)

Write-Host '1) Dépôt : ce qui serait commité'
$gi = @(Get-Content (Join-Path $Root '.gitignore') -Encoding UTF8 | ForEach-Object { $_.Trim() })
foreach ($e in '.env', 'memoire/', 'logs/', '__pycache__/', 'quarantaine/', 'voix/models/', 'config.local.json') { Verifier ($gi -contains $e) ".gitignore exclut « $e »" }
$gros = @(Get-ChildItem $Root -Recurse -File -Force -ErrorAction SilentlyContinue | Where-Object { $_.Length -gt 50MB })
Write-Host ("        fichiers de plus de 50 Mo (jamais dans git) : " + (($gros | ForEach-Object { "$($_.FullName.Substring($Root.Length + 1)) ($([int]($_.Length / 1MB)) Mo)" }) -join ' ; '))
if ($aGit) {
    $gd = Join-Path $TR 'gd'; & git init --bare -q $gd 2>$null
    $cand = @(& git --git-dir=$gd --work-tree=$Root ls-files --others --exclude-standard 2>$null | ForEach-Object { $_ -replace '/', '\' })
    Verifier ($cand.Count -gt 40) "git add -A ajouterait $($cand.Count) fichiers (simulé sans toucher au dossier : aucun .git créé ici)"
    $tailleCand = ($cand | ForEach-Object { (Get-Item (Join-Path $Root $_)).Length } | Measure-Object -Sum).Sum
    Write-Host ("        taille totale à commiter : {0:N1} Mo" -f ($tailleCand / 1MB))
    Verifier (@($cand | Where-Object { (Get-Item (Join-Path $Root $_)).Length -gt 50MB }).Count -eq 0) 'AUCUN fichier de plus de 50 Mo ne serait commité'
    Verifier (@($cand | Where-Object { $_ -eq '.env' -or $_ -like 'memoire\*' -or $_ -like 'logs\*' -or $_ -like 'quarantaine\*' -or $_ -like '*__pycache__*' -or $_ -like 'voix\models\*' -or $_ -eq 'config.local.json' -or $_ -like '*.pyc' }).Count -eq 0) '.env, memoire\, logs\, quarantaine\, __pycache__, voix\models\ et config.local.json sont exclus'
    foreach ($f in 'jarvis.ps1', 'maj-auto.ps1', 'installer-serveur.ps1', 'requirements.txt', '.env.example', 'config.json', 'README.md', 'lib\discord.ps1', 'pont-discord\pont.py', 'voix\ecoute.py', 'tests\tout.ps1', '.gitignore') { Verifier ($cand -contains $f) "sera commité : $f" }
    $motifs = 'rk_live_[A-Za-z0-9]{10,}', 'sk_live_[A-Za-z0-9]{10,}', 'eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\.', '[A-Za-z0-9_-]{23,28}\.[A-Za-z0-9_-]{6,7}\.[A-Za-z0-9_-]{27,}'
    $fauxJeton = 'MTIzNDU2Nzg5MDEyMzQ1Njc4.GabcDE.abcdefghijklmnopqrstuvwxyz0123456789ABCD'      # (faux jeton des tests : voulu)
    $suspects = @($cand | Where-Object { ($_ -match '\.(ps1|py|json|md|html|js|txt|example|css)$' -or $_ -eq '.gitignore') -and $_ -notlike 'tests\*' } | Where-Object { $t = Get-Content (Join-Path $Root $_) -Raw -Encoding UTF8 -ErrorAction SilentlyContinue; if ($t) { $t = $t.Replace($fauxJeton, ''); foreach ($m in $motifs) { if ($t -match $m) { return $true } } }; $false })
    Verifier ($suspects.Count -eq 0) ('aucune clé ni aucun jeton (Stripe, JWT, Discord) dans les fichiers à commiter (hors faux exemples des tests)' + $(if ($suspects.Count) { ' — à examiner : ' + ($suspects -join ', ') }))
    $jr = ''; if (Test-Path (Join-Path $Root '.env')) { foreach ($l in (Get-Content (Join-Path $Root '.env') -Encoding UTF8)) { if ($l -match '^\s*(DISCORD_BOT_TOKEN|STRIPE_RESTRICTED_KEY|JARVIS_STATS_TOKEN|SUPABASE_READ_KEY|ALPHAVANTAGE_KEY)\s*=\s*(.{12,})$') { $v = $Matches[2].Trim().Trim('"'); if ($v -notmatch '^xxx|_xxx$') { $jr += "$v`n" } } } }
    $fuite = @(); foreach ($v in ($jr -split "`n" | Where-Object { $_ })) { foreach ($f in $cand) { if (Select-String -Path (Join-Path $Root $f) -Pattern $v -SimpleMatch -Quiet -ErrorAction SilentlyContinue) { $fuite += $f } } }
    Verifier ($fuite.Count -eq 0) 'aucune valeur réelle de .env n''apparaît dans un fichier à commiter (contrôle sans rien afficher)'
} else { Verifier $true '(git absent de ce PC : contrôle des fichiers à commiter sauté)' }

Write-Host '2) requirements.txt'
$req = Get-Content (Join-Path $Root 'requirements.txt') -Raw -Encoding UTF8
foreach ($p in 'sounddevice', 'vosk', 'faster-whisper', 'numpy', 'edge-tts', 'piper-tts', 'discord.py') { Verifier ($req -match "(?m)^$([regex]::Escape($p))[>=<]") "requirements.txt : $p" }
Verifier ($req -notmatch 'nvidia|cuda') 'aucun paquet GPU (le serveur tourne sur le CPU)'
$imports = @(Get-ChildItem (Join-Path $Root 'voix'), (Join-Path $Root 'pont-discord') -Filter *.py | ForEach-Object { Get-Content $_.FullName -Raw -Encoding UTF8 })
Verifier (($imports -join "`n") -match 'import discord' -and ($imports -join "`n") -match 'import edge_tts' -and ($imports -join "`n") -match 'sounddevice') 'les modules importés par le code sont couverts par requirements.txt'

Write-Host '3) config.json et config.local.json'
Verifier ($vraie.mode_serveur -eq $false -and $vraie.serveur_micro -eq 'auto') 'config.json : mode_serveur = false (PC de bureau inchangé), serveur_micro = auto'
$ex = Get-Content (Join-Path $Root '.env.example') -Raw -Encoding UTF8
foreach ($k in 'DISCORD_BOT_TOKEN', 'DISCORD_USER_ID', 'ALPHAVANTAGE_KEY', 'STRIPE_RESTRICTED_KEY', 'SUPABASE_URL', 'SUPABASE_READ_KEY', 'JARVIS_STATS_TOKEN') { Verifier ($ex -match "(?m)^$k=") ".env.example contient $k" }
$b = [pscustomobject]@{ a = 1; ollama = [pscustomobject]@{ modele = 'gros'; url = 'u' }; liste = @(1, 2) }
Merge-ConfigObjet $b ([pscustomobject]@{ a = 2; ollama = [pscustomobject]@{ modele = 'petit' }; neuf = 'x' })
Verifier ($b.a -eq 2 -and $b.ollama.modele -eq 'petit' -and $b.ollama.url -eq 'u' -and $b.neuf -eq 'x') 'fusion de config : le local écrase clé par clé, le reste est conservé'
$cfgDir = Join-Path $TR 'cfg'; New-Item -ItemType Directory $cfgDir | Out-Null; $script:JarvisRoot = $cfgDir
Copy-Item (Join-Path $Root 'config.json') "$cfgDir\config.json"
[IO.File]::WriteAllText("$cfgDir\config.local.json", '{ "mode_serveur": true, "discord_actif": true, "ollama": { "modele": "qwen2.5:3b" } }', [Text.UTF8Encoding]::new($false))
$jc = $env:JARVIS_CONFIG; Remove-Item Env:JARVIS_CONFIG -ErrorAction SilentlyContinue
$c = Import-ConfigJarvis
Verifier ($c.mode_serveur -eq $true -and $c.discord_actif -eq $true -and $c.ollama.modele -eq 'qwen2.5:3b' -and $c.ollama.url -eq $vraie.ollama.url -and $c.valeurs_suivies.Count -ge 1) 'Import-ConfigJarvis : config.json + config.local.json (réglages de la machine, le reste du réseau inchangé)'
Set-Content "$cfgDir\config.local.json" '{ pas du json' -Encoding UTF8; $c = Import-ConfigJarvis
Verifier ($c.mode_serveur -eq $false) 'config.local.json illisible : ignoré, aucun plantage'
Remove-Item "$cfgDir\config.local.json"; $c = Import-ConfigJarvis; Verifier ($c.mode_serveur -eq $false) 'sans config.local.json : config.json seule'
if ($jc) { $env:JARVIS_CONFIG = $jc }
Fixer 'x' 1; $script:JarvisRoot = $TR
$mj = Get-Content (Join-Path $Root 'jarvis.ps1') -Raw -Encoding UTF8; $vf = Get-Content (Join-Path $Root 'veille-fond.ps1') -Raw -Encoding UTF8
Verifier ($mj -match '\$Config = Import-ConfigJarvis' -and $vf -match 'Import-ConfigJarvis') 'jarvis.ps1 et la veille de fond lisent config.json + config.local.json'
$py = Get-Content (Join-Path $Root 'pont-discord\pont_logique.py') -Raw -Encoding UTF8
Verifier ($py -match 'config\.local\.json') 'le pont Discord lit aussi config.local.json (salons forcés)'

Write-Host '4) Mode serveur : ni HUD, ni voix, ni musique ; Discord et micro (s''il existe)'
Verifier ((Test-ModeServeur) -eq $false) 'mode_serveur = false : rien ne change'
Fixer 'mode_serveur' $true
Verifier ((Test-ModeServeur) -eq $true) 'mode_serveur = true reconnu'
function Journal { $f = Join-Path $TR ('logs\journal-{0}.md' -f (Get-Date -Format 'yyyy-MM-dd')); if (Test-Path $f) { Get-Content $f -Raw -Encoding UTF8 } else { '' } }
$j0 = (Journal).Length
$script:CanalDiscord = $null
Parler 'Bonjour monsieur, test du mode serveur.'
Verifier ((Journal).Substring($j0) -match 'Parole non prononcée \(mode serveur\)' -and (Journal).Substring($j0) -notmatch 'Parole \(test silencieux\)') 'Parler : aucune voix en mode serveur (le texte reste au journal)'
$script:CanalDiscord = 'jarvis'; $script:DiscordTampon = New-Object System.Collections.Generic.List[string]
Parler 'Réponse pour Discord.'
Verifier ($script:DiscordTampon.Count -eq 1 -and $script:DiscordTampon[0] -eq 'Réponse pour Discord.') 'Discord reste actif : les réponses partent toujours sur Discord'
$script:CanalDiscord = $null; $script:DiscordTampon = $null
$script:Joue = $false
Verifier ($null -eq (Start-MusiqueDemarrage) -and $null -eq (Start-Ambiance) -and $null -eq (Invoke-Son 'actif')) 'musique de démarrage, ambiance et sons : désactivés'
Verifier ($null -eq (Start-Visage)) 'Start-Visage : pas de fenêtre ni de HUD'
$script:FauxMicroServeur = $false; Verifier ((Get-MicroServeur) -eq $false) 'aucun micro : l''écoute est désactivée'
$script:FauxMicroServeur = $true; Verifier ((Get-MicroServeur) -eq $true) 'un micro est branché : l''écoute reste possible'
$script:FauxMicroServeur = $null; Fixer 'serveur_micro' 'false'; Verifier ((Get-MicroServeur) -eq $false) 'serveur_micro = false : jamais d''écoute'
Fixer 'serveur_micro' 'true'; Verifier ((Get-MicroServeur) -eq $true) 'serveur_micro = true : écoute forcée'
Fixer 'serveur_micro' 'auto'
Verifier ($mj -match '\$serveur = Test-ModeServeur' -and $mj -match 'if \(-not \$serveur\) \{ Start-Visage \}' -and $mj -match 'if \(\$serveur\) \{ if \(Get-MicroServeur\) \{ Start-Ecoute \} \}' -and $mj -match 'Initialize-Raccourcis \}') 'jarvis.ps1 : en mode serveur, ni HUD, ni raccourcis, écoute seulement s''il y a un micro'
Verifier ($mj -match 'Start-PontDiscord' -and $mj -match "-not \`$SansCoffre -and -not \`$serveur") 'jarvis.ps1 : le pont Discord démarre toujours ; pas de fenêtre du coffre en mode serveur'
Verifier ($mj -match '-not \$script:ModeJeu -and -not \$serveur\) \{ Update-Tableau') 'pas de mise à jour du tableau de bord (HUD) en mode serveur'
Effacer 'mode_serveur'; Verifier ((Test-ModeServeur) -eq $false) 'retour à mode_serveur = false : tout redevient normal'

Write-Host '5) installer-serveur.ps1 (fonctions, puis SIMULATION : rien n''est installé)'
$inst = Join-Path $Root 'installer-serveur.ps1'
. $inst -SeulementFonctions -Racine $TR
Verifier ((Select-ModeleOllama 4) -eq 'qwen2.5:3b' -and (Select-ModeleOllama 8) -eq 'qwen2.5:3b' -and (Select-ModeleOllama 8.1) -eq 'qwen2.5:7b' -and (Select-ModeleOllama 16) -eq 'qwen2.5:7b') 'modèle Ollama selon la RAM : 8 Go ou moins -> qwen2.5:3b ; au-delà -> qwen2.5:7b'
$srv = Join-Path $TR 'srv'; New-Item -ItemType Directory $srv | Out-Null
Copy-Item (Join-Path $Root '.env.example') "$srv\.env.example"
$script:Simulation = $true
Verifier ((New-EnvSiNecessaire $srv) -eq 'cree' -and -not (Test-Path "$srv\.env")) 'simulation : « .env serait créé », rien n''est écrit'
$script:Simulation = $false
Verifier ((New-EnvSiNecessaire $srv) -eq 'cree' -and (Hash "$srv\.env") -eq (Hash "$srv\.env.example")) '.env absent : créé depuis .env.example'
[IO.File]::WriteAllText("$srv\.env", "DISCORD_BOT_TOKEN=valeur-secrete-de-test-xyz`n", [Text.UTF8Encoding]::new($false)); $h0 = Hash "$srv\.env"
Verifier ((New-EnvSiNecessaire $srv) -eq 'existe' -and (Hash "$srv\.env") -eq $h0) '.env existant : JAMAIS écrasé (contenu identique)'
Remove-Item "$srv\.env.example"; Remove-Item "$srv\.env"; Verifier ((New-EnvSiNecessaire $srv) -eq 'modele-absent') '.env.example absent : signalé, rien créé'
Verifier ((New-ConfigLocale $srv 'qwen2.5:3b') -eq 'cree') 'config.local.json créé'
$cl = Get-Content "$srv\config.local.json" -Raw -Encoding UTF8 | ConvertFrom-Json
Verifier ($cl.mode_serveur -eq $true -and $cl.discord_actif -eq $true -and $cl.etat_au_demarrage -eq 'actif' -and $cl.moteur_voix_appareil -eq 'cpu' -and $cl.ollama.modele -eq 'qwen2.5:3b') 'config.local.json : mode serveur, Discord actif, CPU, modèle choisi'
$h1 = Hash "$srv\config.local.json"; Verifier ((New-ConfigLocale $srv 'qwen2.5:7b') -eq 'existe' -and (Hash "$srv\config.local.json") -eq $h1) 'config.local.json existant : conservé (relançable sans risque)'
$ins = Get-Content $inst -Raw -Encoding UTF8
foreach ($m in 'Git.Git', 'Python.Python.3.11', 'Ollama.Ollama', 'requirements.txt', 'standby-timeout-ac 0', 'hibernate-timeout-ac 0', 'LIDACTION 0', 'Jarvis-Serveur', 'Jarvis-MajAuto', 'New-TimeSpan -Minutes 10', 'fr_FR-\$v-medium', 'faster-whisper-small', 'notepad.exe', 'AtLogOn') { Verifier ($ins -match [regex]::Escape($m) -or $ins -match $m) "installer-serveur.ps1 prévoit : $m" }
Verifier ($ins -notmatch '(?i)Remove-Item[^\r\n]*\.env' -and $ins -notmatch 'Set-Content[^\r\n]*\.env\b' ) 'installer-serveur.ps1 : aucune écriture ni suppression de .env en dehors de New-EnvSiNecessaire'
# simulation complète dans un dossier temporaire
$sim = Join-Path $TR 'sim'; New-Item -ItemType Directory $sim | Out-Null
Copy-Item (Join-Path $Root '.env.example') "$sim\.env.example"; Copy-Item (Join-Path $Root 'requirements.txt') "$sim\requirements.txt"
$taches0 = @(Get-ScheduledTask -ErrorAction SilentlyContinue | Where-Object { $_.TaskName -like 'Jarvis*' } | ForEach-Object { $_.TaskName }) -join ','
$sortie = & powershell -NoProfile -ExecutionPolicy Bypass -File $inst -Simulation -SansBlocNotes -Racine $sim 2>&1 | Out-String; $code = $LASTEXITCODE
$taches1 = @(Get-ScheduledTask -ErrorAction SilentlyContinue | Where-Object { $_.TaskName -like 'Jarvis*' } | ForEach-Object { $_.TaskName }) -join ','
Verifier ($code -eq 0 -and $sortie -match 'SIMULATION' -and $sortie -match 'RAM détectée' -and $sortie -match 'qwen2\.5:(3b|7b)') 'simulation : se déroule jusqu''au bout et annonce la RAM et le modèle'
Verifier ($sortie -match 'pip install -r requirements\.txt' -and $sortie -match 'fr_FR-tom-medium\.onnx' -and $sortie -match 'Whisper' -and $sortie -match 'Vosk') 'simulation : dépendances Python, voix Piper, Whisper et Vosk'
Verifier ($sortie -match 'powercfg /change standby-timeout-ac 0' -and $sortie -match 'powercfg /setacvalueindex SCHEME_CURRENT SUB_BUTTONS LIDACTION 0') 'simulation : jamais de veille sur secteur, capot fermé = ne rien faire'
Verifier ($sortie -match 'Jarvis-Serveur' -and $sortie -match 'Jarvis-MajAuto' -and $sortie -match '\.env créé depuis \.env\.example' -and $sortie -match 'config\.local\.json créé') 'simulation : les 2 tâches planifiées, .env et config.local.json'
Verifier (-not (Test-Path "$sim\.env") -and -not (Test-Path "$sim\config.local.json") -and -not (Test-Path "$sim\logs") -and -not (Test-Path "$sim\voix") -and $taches0 -eq $taches1) 'simulation : RIEN n''a été créé (ni .env, ni config, ni modèle, ni tâche planifiée)'
Verifier ($sortie -notmatch 'valeur-secrete') 'aucun secret dans la sortie'

Write-Host '6) maj-auto.ps1 sur de vrais dépôts git temporaires (origine locale, aucun réseau)'
$maj = Join-Path $Root 'maj-auto.ps1'
$mc = Get-Content $maj -Raw -Encoding UTF8
Verifier ($mc -match 'pull --ff-only' -and $mc -match 'reset --hard' -and $mc -match 'merge-base --is-ancestor' -and $mc -match 'Send-AlerteMaj' -and $mc -match 'arreter\.ps1' -and $mc -match 'maj-auto-refuse\.txt') 'maj-auto.ps1 : fetch, pull --ff-only, tests, arrêt/relance, reset --hard, alerte, commit refusé mémorisé'
Verifier ($mc -notmatch '(?i)(Remove-Item|Set-Content|Out-File|Copy-Item|Move-Item)[^\r\n]*\.env\b' -and $mc -notmatch 'Remove-Item[^\r\n]*memoire') 'maj-auto.ps1 : ne modifie jamais .env ni memoire\'
if (-not $aGit) { Verifier $true '(git absent : scénarios de mise à jour sautés)' } else {
    $env:GIT_AUTHOR_NAME = 'test'; $env:GIT_AUTHOR_EMAIL = 't@t.t'; $env:GIT_COMMITTER_NAME = 'test'; $env:GIT_COMMITTER_EMAIL = 't@t.t'
    $ErrorActionPreference = 'Continue'      # (git écrit des avertissements sur stderr : ce ne sont pas des erreurs)
    $g = { & git -c init.defaultBranch=main -c core.autocrlf=false @args 2>$null | Out-Null }
    $O = Join-Path $TR 'origin.git'; $D = Join-Path $TR 'dev'; $S = Join-Path $TR 'serveur'
    & $g init --bare -q $O; & $g clone -q $O $D; & git -C $D checkout -q -b main 2>$null
    New-Item -ItemType Directory "$D\lib", "$D\tests" | Out-Null
    Copy-Item (Join-Path $Root 'lib\journal.ps1') "$D\lib\journal.ps1"; Copy-Item $maj "$D\maj-auto.ps1"
    "[Console]::Error.WriteLine('stub arreter'); exit 0" | Set-Content "$D\arreter.ps1" -Encoding ASCII
    "ECHO_STUB" | Out-Null
    "Write-Host '  OK  test factice'; exit 0" | Set-Content "$D\tests\tout.ps1" -Encoding ASCII
    ".env`nmemoire/`nlogs/`nconfig.local.json`n" | Set-Content "$D\.gitignore" -Encoding ASCII
    '1' | Set-Content "$D\VERSION.txt" -Encoding ASCII; "sounddevice>=0.5" | Set-Content "$D\requirements.txt" -Encoding ASCII
    & git -C $D add -A 2>$null; & git -C $D -c user.name=t -c user.email=t@t.t commit -q -m v1 2>$null; & git -C $D push -q origin main 2>$null; & git -C $O symbolic-ref HEAD refs/heads/main 2>$null
    & $g clone -q -b main $O $S
    New-Item -ItemType Directory "$S\memoire" -Force | Out-Null
    [IO.File]::WriteAllText("$S\.env", "DISCORD_BOT_TOKEN=secret-de-test`n", [Text.UTF8Encoding]::new($false)); 'ma to-do' | Set-Content "$S\memoire\todo.md" -Encoding UTF8; '{"a":1}' | Set-Content "$S\config.local.json" -Encoding ASCII
    $hEnv = Hash "$S\.env"; $hTodo = Hash "$S\memoire\todo.md"; $hLoc = Hash "$S\config.local.json"
    $alerte = Join-Path $TR 'alerte.txt'
    $jt = $env:JARVIS_TEST; $jc2 = $env:JARVIS_CONFIG; Remove-Item Env:JARVIS_TEST, Env:JARVIS_CONFIG -ErrorAction SilentlyContinue      # (le journal et la mémoire du dépôt de test restent DANS ce dépôt temporaire)
    function Maj([string[]]$plus = @()) { $o = & powershell -NoProfile -ExecutionPolicy Bypass -File "$S\maj-auto.ps1" -Racine $S -SansArret -SansRelance -SansPip -FichierAlerte $alerte @plus 2>&1 | Out-String; @{ sortie = $o; code = $LASTEXITCODE } }
    function Pousser([string]$version, [string]$tests = "Write-Host '  OK  test factice'; exit 0") {
        $version | Set-Content "$D\VERSION.txt" -Encoding ASCII; $tests | Set-Content "$D\tests\tout.ps1" -Encoding ASCII
        & git -C $D add -A 2>$null; & git -C $D -c user.name=t -c user.email=t@t.t commit -q -m "v$version" 2>$null; & git -C $D push -q origin main 2>$null
    }
    function Tete([string]$d) { (& git -C $d rev-parse HEAD 2>$null).Trim() }
    function Intacts { (Hash "$S\.env") -eq $hEnv -and (Hash "$S\memoire\todo.md") -eq $hTodo -and (Hash "$S\config.local.json") -eq $hLoc }
    $v1 = Tete $S
    # A : rien de neuf
    $r = Maj
    Verifier ($r.code -eq 0 -and $r.sortie -match 'à jour' -and (Tete $S) -eq $v1 -and -not (Test-Path $alerte)) 'A) rien de neuf : « à jour », rien ne bouge, aucune alerte'
    # B : neuf + tests verts
    Pousser '2'
    $r = Maj '-Simulation'
    Verifier ($r.sortie -match 'mise à jour disponible' -and $r.sortie -match 'simulation' -and (Tete $S) -eq $v1) 'simulation : annonce la mise à jour sans rien changer'
    $r = Maj
    Verifier ($r.code -eq 0 -and $r.sortie -match 'tests verts' -and (Tete $S) -eq (Tete $D) -and ((Get-Content "$S\VERSION.txt" -Raw).Trim() -eq '2') -and -not (Test-Path $alerte)) 'B) nouveau commit + tests verts : pull en avance rapide, version adoptée, aucune alerte'
    Verifier ($r.sortie -match 'arrêt de Jarvis : ignoré' -and $r.sortie -match 'relance de Jarvis : ignorée') 'B) Jarvis est arrêté avant les tests puis relancé après (ici ignorés par -SansArret / -SansRelance : Jarvis jamais lancé par le test)'
    Verifier (Intacts) 'B) .env, memoire\ et config.local.json strictement inchangés'
    Verifier ((Get-Content "$S\logs\journal-$(Get-Date -Format 'yyyy-MM-dd').md" -Raw -Encoding UTF8) -match 'tests verts : version') 'B) noté au journal'
    $v2 = Tete $S
    # C : tests rouges -> retour arrière + alerte
    Pousser '3' "Write-Host '  ECHEC test factice'; exit 1"
    $r = Maj
    Verifier ($r.code -eq 5 -and (Tete $S) -eq $v2 -and ((Get-Content "$S\VERSION.txt" -Raw).Trim() -eq '2')) 'C) tests rouges : retour à la version précédente (git reset --hard), fichiers revenus à l''état d''avant'
    Verifier ((Test-Path $alerte) -and (Get-Content $alerte -Raw) -match 'REFUSÉE' -and (Get-Content $alerte -Raw) -match $v2.Substring(0, 7) -and (Get-Content $alerte -Raw) -notmatch 'secret-de-test') 'C) alerte (Discord) : « mise à jour REFUSÉE », version de retour indiquée, aucun secret'
    Verifier (Intacts) 'C) .env, memoire\ et config.local.json inchangés après le retour arrière'
    Verifier ((Get-Content "$S\logs\journal-$(Get-Date -Format 'yyyy-MM-dd').md" -Raw -Encoding UTF8) -match 'REFUSÉE') 'C) noté au journal'
    Remove-Item $alerte -Force
    $r = Maj
    Verifier ($r.code -eq 0 -and $r.sortie -match 'déjà refusée' -and -not (Test-Path $alerte) -and (Tete $S) -eq $v2) 'C) le même commit refusé n''est pas réessayé toutes les 10 minutes (Jarvis n''est pas arrêté pour rien)'
    # D : correction -> adoptée
    Pousser '4'
    $r = Maj
    Verifier ($r.code -eq 0 -and $r.sortie -match 'tests verts' -and (Tete $S) -eq (Tete $D) -and -not (Test-Path "$S\memoire\maj-auto-refuse.txt")) 'D) un nouveau commit corrigé est adopté (le refus est oublié)'
    $v4 = Tete $S
    # E : historique divergent
    "local" | Set-Content "$S\LOCAL.txt" -Encoding ASCII; & git -C $S add -A 2>$null; & git -C $S -c user.name=t -c user.email=t@t.t commit -q -m local 2>$null
    $vLocal = Tete $S
    Pousser '5'
    $r = Maj
    Verifier ($r.code -eq 2 -and (Tete $S) -eq $vLocal -and (Test-Path $alerte) -and (Get-Content $alerte -Raw) -match 'historique') 'E) historique local qui diverge : aucune mise à jour, aucun écrasement, alerte'
    & git -C $S reset -q --hard $v4 2>$null; Remove-Item $alerte -Force -ErrorAction SilentlyContinue
    # F : fichier suivi modifié sur le serveur
    Add-Content "$S\VERSION.txt" 'modif locale' -Encoding ASCII
    $r = Maj
    Verifier ($r.code -eq 3 -and (Test-Path $alerte) -and (Get-Content $alerte -Raw) -match 'config\.local\.json' -and (Get-Content "$S\VERSION.txt" -Raw) -match 'modif locale') 'F) fichier suivi modifié à la main : refus, rien n''est écrasé, l''alerte explique où mettre les réglages locaux'
    & git -C $S checkout -q -- VERSION.txt 2>$null; Remove-Item $alerte -Force -ErrorAction SilentlyContinue
    $r = Maj
    Verifier ($r.code -eq 0 -and (Tete $S) -eq (Tete $D) -and (Intacts)) 'puis tout rentre dans l''ordre au passage suivant (mise à jour adoptée, .env et memoire\ intacts)'
    if ($jt) { $env:JARVIS_TEST = $jt }; if ($jc2) { $env:JARVIS_CONFIG = $jc2 }
    Verifier (@(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'jarvis\.ps1' -and $_.CommandLine -match [regex]::Escape($S) }).Count -eq 0) 'Jarvis n''a été ni lancé ni arrêté par ce test'
}
Write-Host '7) Intégration'
$tt = Get-Content (Join-Path $Root 'tests\tout.ps1') -Raw -Encoding UTF8
Verifier ($tt -match "serveur\.ps1") 'tests\tout.ps1 inclut ce test'
foreach ($f in 'installer-serveur.ps1', 'maj-auto.ps1', 'tests\serveur.ps1', 'lib\journal.ps1') { Verifier ((Get-Content (Join-Path $Root $f) -Encoding Byte -TotalCount 3) -join ',' -eq '239,187,191') "$f : UTF-8 avec BOM (PowerShell 5.1)" }
Verifier ((Get-Content (Join-Path $Root 'README.md') -Raw -Encoding UTF8) -match 'installer-serveur\.ps1' -and (Get-Content (Join-Path $Root 'README.md') -Raw -Encoding UTF8) -match 'maj-auto\.ps1') 'README : section « Serveur 24/7 »'
$vf2 = Get-Content (Join-Path $Root 'CLAUDE.md') -Raw -Encoding UTF8
Verifier ($vf2 -match 'installer\.ps1') '(CLAUDE.md inchangé : jamais d''installation lancée par Claude)'

Remove-Item $TR -Recurse -Force -ErrorAction SilentlyContinue
if ($echecs) { Write-Host "`nÉCHEC : $echecs vérification(s) en échec." -ForegroundColor Red; exit 1 }
Write-Host "`nRÉUSSI"; exit 0
