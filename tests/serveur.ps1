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
    $cand = @(& git -C $Root --git-dir=$gd --work-tree=$Root ls-files --others --exclude-standard 2>$null | ForEach-Object { $_ -replace '/', '\' })
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
Verifier ($vraie.mode_serveur -eq $false -and $vraie.serveur_micro -eq 'non') 'config.json : mode_serveur = false (PC de bureau inchangé), serveur_micro = non'
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
Verifier ($mj -match '\$serveur = Test-ModeServeur' -and $mj -match 'if \(-not \$serveur -and -not \$veilleBureau\) \{ Start-Visage' -and $mj -match 'if \(\$serveur\) \{ if \(Get-MicroServeur\) \{ Start-Ecoute \} \}' -and $mj -match 'Initialize-Raccourcis \}') 'jarvis.ps1 : en mode serveur, ni HUD, ni raccourcis, écoute seulement s''il y a un micro'
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
# --- détection d'un VRAI Python 3.11 (le faux python.exe du Microsoft Store ne compte pas) ---
$fk = Join-Path $TR 'faux-python'; $wa = "$fk\Users\x\AppData\Local\Microsoft\WindowsApps"; $bon = "$fk\bon"; $vieux = "$fk\vieux"; $pyl = "$fk\launcher"; $apres = "$fk\apres"
New-Item -ItemType Directory $wa, $bon, $vieux, $pyl, $apres -Force | Out-Null
$marque = Join-Path $fk 'store-execute.txt'
"@echo off`r`necho store>> `"$marque`"`r`necho Python was not found; run without arguments to install from the Microsoft Store 1>&2`r`nexit /b 9009" | Set-Content "$wa\python.bat" -Encoding ASCII
"@echo off`r`necho store>> `"$marque`"`r`nexit /b 9009" | Set-Content "$wa\py.bat" -Encoding ASCII
"@echo off`r`necho Python 3.11.9" | Set-Content "$bon\python.bat" -Encoding ASCII
"@echo off`r`necho Python 3.9.13" | Set-Content "$vieux\python.bat" -Encoding ASCII
"@echo off`r`nif `"%1`"==`"-3.11`" (echo $bon\python.bat) else (exit /b 1)" | Set-Content "$pyl\py.bat" -Encoding ASCII
$sys32 = Join-Path $env:SystemRoot 'System32'; $pathAvant = $env:Path; $script:DossiersPythonParDefaut = @()
$env:Path = "$wa;$sys32"
$r = Find-PythonReel
Verifier ($null -eq $r -and -not (Test-Path $marque)) 'seul le faux raccourci du Store (WindowsApps\python.exe) existe : AUCUN Python trouvé, et le raccourci n''est jamais exécuté'
Verifier ((Test-CheminWindowsApps 'C:\Users\Liam\AppData\Local\Microsoft\WindowsApps\python.exe') -and -not (Test-CheminWindowsApps 'C:\Users\Liam\AppData\Local\Programs\Python\Python311\python.exe')) 'tout chemin contenant WindowsApps est reconnu comme faux'
$env:Path = "$wa;$bon;$sys32"; $r = Find-PythonReel
Verifier ($r -and $r.exe -eq "$bon\python.bat" -and $r.version -eq 'Python 3.11.9' -and -not (Test-Path $marque)) 'faux raccourci devant, vrai Python derrière : le vrai est trouvé (version réellement exécutée), le faux ignoré'
$env:Path = "$vieux;$sys32"; Verifier ($null -eq (Find-PythonReel)) 'un Python 3.9 n''est pas un Python 3.11 : refusé'
$env:Path = "$pyl;$sys32"; $r = Find-PythonReel; Verifier ($r -and $r.exe -eq "$bon\python.bat") 'py -3.11 : le lanceur donne le chemin du vrai Python 3.11'
$env:Path = "$wa;$vieux;$sys32"; Verifier ($null -eq (Find-PythonReel) -and -not (Test-Path $marque)) 'Store + Python 3.9 : aucun 3.11, toujours rien d''exécuté dans WindowsApps'
# installation : winget est appelé, le PATH de la session est actualisé AVANT pip
$script:WingetAppels = @(); $script:OrdreEtapes = @()
function winget { $script:WingetAppels += ($args -join ' '); $script:OrdreEtapes += 'winget'; "@echo off`r`necho Python 3.11.9" | Set-Content "$apres\python.bat" -Encoding ASCII }
function Update-CheminSession { $script:OrdreEtapes += 'chemin'; $env:Path = "$apres;$env:Path" }
$script:Simulation = $false; $script:PythonExe = ''
$env:Path = "$wa;$sys32"
Install-PythonSiAbsent
Verifier ($script:WingetAppels.Count -eq 1 -and $script:WingetAppels[0] -match 'install --id Python\.Python\.3\.11' -and $script:PythonExe -eq "$apres\python.bat") 'pas de vrai Python 3.11 : winget installe Python.Python.3.11, puis le vrai Python est retrouvé'
Verifier (($script:OrdreEtapes -join ',') -eq 'winget,chemin' -and $env:Path.StartsWith((Split-Path "$apres\python.bat"))) 'le PATH de la session est actualisé juste après winget (avant pip) et le vrai Python passe devant'
Verifier (-not (Test-Path $marque)) '…sans jamais exécuter le faux raccourci du Store'
$script:WingetAppels = @(); $script:PythonExe = ''; $env:Path = "$bon;$sys32"
Install-PythonSiAbsent
Verifier ($script:WingetAppels.Count -eq 0 -and $script:PythonExe -eq "$bon\python.bat") 'vrai Python 3.11 présent : « déjà installé », winget n''est pas appelé'
$script:Simulation = $true; $script:WingetAppels = @(); $script:PythonExe = ''; $env:Path = "$wa;$sys32"
Install-PythonSiAbsent
Verifier ($script:WingetAppels.Count -eq 0 -and $script:Journal[-1] -match '\[simulation\] installation de Python 3\.11') 'simulation : annonce l''installation de Python sans rien exécuter'
$script:Simulation = $false
Remove-Item function:winget, function:Update-CheminSession; $env:Path = $pathAvant
. $inst -SeulementFonctions -Racine $TR      # (fonctions d'origine remises)
$script:DossiersPythonParDefaut = @((Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311'))
$insPy = Get-Content $inst -Raw -Encoding UTF8
Verifier ($insPy -match '& \$script:PythonExe -m pip' -and $insPy -match '& \$script:PythonExe -I -c' -and $insPy -notmatch '& python ' -and $insPy -notmatch "Install-WingetSiAbsent 'Python") 'pip et le téléchargement Whisper utilisent le Python détecté ; plus de détection par « Get-Command python » seul'
Verifier ($insPy -match 'Get-Command py ' -and $insPy -match '-3\.11' -and $insPy -match '--version' -and $insPy -match '\^Python 3\\\.11') 'détection : py -3.11 puis python --version réellement exécutés, version 3.11 exigée'
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
$lignesEnv = @($mc -split "`n" | Where-Object { $_ -match '(?i)(Remove-Item|Set-Content|Out-File|Copy-Item|Move-Item)[^\r\n]*\.env\b' })
Verifier ($lignesEnv.Count -eq 1 -and $lignesEnv[0] -match '\.env\.bak' -and $mc -notmatch 'Remove-Item[^\r\n]*memoire') 'maj-auto.ps1 : n''écrit .env que par le déchiffrement atomique (Restore-EnvDepuisChiffre) et pour remettre l''ancien .env.bak après un retour arrière ; ne touche jamais memoire\'
if (-not $aGit) { Verifier $true '(git absent : scénarios de mise à jour sautés)' } else {
    $env:GIT_AUTHOR_NAME = 'test'; $env:GIT_AUTHOR_EMAIL = 't@t.t'; $env:GIT_COMMITTER_NAME = 'test'; $env:GIT_COMMITTER_EMAIL = 't@t.t'
    $ErrorActionPreference = 'Continue'      # (git écrit des avertissements sur stderr : ce ne sont pas des erreurs)
    $g = { & git -c init.defaultBranch=main -c core.autocrlf=false @args 2>$null | Out-Null }
    $O = Join-Path $TR 'origin.git'; $D = Join-Path $TR 'dev'; $S = Join-Path $TR 'serveur'
    & $g init --bare -q $O; & $g clone -q $O $D; & git -C $D checkout -q -b main 2>$null
    New-Item -ItemType Directory "$D\lib", "$D\tests" | Out-Null
    Copy-Item (Join-Path $Root 'lib\journal.ps1') "$D\lib\journal.ps1"; Copy-Item $maj "$D\maj-auto.ps1"; Copy-Item (Join-Path $Root 'lib\env-chiffre.ps1') "$D\lib\env-chiffre.ps1"
    "[Console]::Error.WriteLine('stub arreter'); exit 0" | Set-Content "$D\arreter.ps1" -Encoding ASCII
    "ECHO_STUB" | Out-Null
    "Write-Host '  OK  test factice'; exit 0" | Set-Content "$D\tests\tout.ps1" -Encoding ASCII
    ".env`n.env.bak`n.env.tmp`nmemoire/`nlogs/`nconfig.local.json`n" | Set-Content "$D\.gitignore" -Encoding ASCII
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
    # ----- Clés chiffrées (.env.chiffre) -----
    . (Join-Path $Root 'lib\env-chiffre.ps1')
    $PW2 = 'mdp-serveur-test-Ω-4Zq!'; $mdp2 = [Text.Encoding]::UTF8.GetBytes($PW2)
    $mdpFichier = Join-Path $TR 'serveur-mdp.dpapi'; $env:JARVIS_ENV_MDP_FICHIER = $mdpFichier
    Save-MotDePasseDpapi (ConvertTo-SecureDepuisTexte $PW2) $mdpFichier
    function Cles([string]$valeur, [string]$mdpTexte = $PW2) {
        # côté PC principal : écrit le .env du dépôt de développement, le chiffre (env-chiffrer.ps1), commit et pousse
        [IO.File]::WriteAllText("$D\.env", "CLE=$valeur`n", [Text.UTF8Encoding]::new($false))
        $a = $env:JARVIS_TEST; $env:JARVIS_TEST = '1'; $env:JARVIS_ENV_MDP_TEST = $mdpTexte; $env:JARVIS_ENV_ITER_TEST = '20000'
        & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Root 'env-chiffrer.ps1') -Racine $D -Commit 2>&1 | Out-Null
        Remove-Item Env:JARVIS_ENV_MDP_TEST, Env:JARVIS_ENV_ITER_TEST; if ($a) { $env:JARVIS_TEST = $a } else { Remove-Item Env:JARVIS_TEST -ErrorAction SilentlyContinue }
        & git -C $D push -q origin main 2>$null
    }
    function EnvServeur { (Get-Content "$S\.env" -Raw -Encoding UTF8).Trim() }
    $secretsTest = 'ancienne-valeur|nouvelle-valeur|troisieme|quatrieme|cinquieme|sixieme'
    [IO.File]::WriteAllText("$S\.env", "CLE=ancienne-valeur`n", [Text.UTF8Encoding]::new($false)); Remove-Item "$S\.env.bak" -ErrorAction SilentlyContinue; Remove-Item $alerte -ErrorAction SilentlyContinue
    $vAvant = Tete $S
    # G : seules les clés changent -> déchiffrement atomique, .env.bak, pas de tests, Jarvis redémarré
    Cles 'nouvelle-valeur'
    $r = Maj
    Verifier ($r.code -eq 0 -and (EnvServeur) -eq 'CLE=nouvelle-valeur' -and (Get-Content "$S\.env.bak" -Raw).Trim() -eq 'CLE=ancienne-valeur' -and -not (Test-Path "$S\.env.tmp")) 'G) .env.chiffre change : .env déchiffré, ancien .env sauvegardé dans .env.bak, aucun fichier temporaire'
    Verifier ($r.sortie -match 'clés \(\.env\) mises à jour' -and $r.sortie -match 'clés seules : pas de tests, redémarrage de Jarvis' -and (Tete $S) -eq (Tete $D) -and -not (Test-Path $alerte)) 'G) clés seules : pas de tests (aucun code nouveau), Jarvis redémarré, aucune alerte'
    Verifier ($r.sortie -notmatch $secretsTest -and ((Get-Content "$S\logs\journal-$(Get-Date -Format 'yyyy-MM-dd').md" -Raw -Encoding UTF8) -notmatch $secretsTest)) 'G) ni la sortie ni le journal ne contiennent de valeur de clé'
    # H : mauvais mot de passe sur le serveur -> .env conservé, journal, alerte
    Save-MotDePasseDpapi (ConvertTo-SecureDepuisTexte 'mauvais-mdp-serveur-12') $mdpFichier
    Cles 'troisieme-valeur'
    $r = Maj
    Verifier ($r.code -eq 0 -and (EnvServeur) -eq 'CLE=nouvelle-valeur' -and (Test-Path $alerte) -and (Get-Content $alerte -Raw) -match 'clés \(\.env\) NON mises à jour' -and (Get-Content $alerte -Raw) -match 'ancien \.env est conservé') 'H) mot de passe du serveur incorrect : l''ancien .env est conservé, journal et alerte Discord'
    Verifier ((Get-Content $alerte -Raw) -notmatch $secretsTest -and (Get-Content $alerte -Raw) -notmatch 'mauvais-mdp|mdp-serveur-test' -and (Get-Content "$S\logs\journal-$(Get-Date -Format 'yyyy-MM-dd').md" -Raw -Encoding UTF8) -match 'NON mises à jour') 'H) l''alerte et le journal ne contiennent ni clé ni mot de passe'
    Remove-Item $alerte -Force
    # I : fichier corrompu
    Save-MotDePasseDpapi (ConvertTo-SecureDepuisTexte $PW2) $mdpFichier
    Cles 'quatrieme-valeur'
    $cc = Get-Content "$D\.env.chiffre" -Raw; Set-Content "$D\.env.chiffre" ($cc -replace 'donnees=.', 'donnees=!') -Encoding ASCII -NoNewline
    & git -C $D add -A 2>$null; & git -C $D -c user.name=t -c user.email=t@t.t commit -q -m corrompu 2>$null; & git -C $D push -q origin main 2>$null
    $r = Maj
    Verifier ($r.code -eq 0 -and (EnvServeur) -eq 'CLE=nouvelle-valeur' -and (Test-Path $alerte) -and (Get-Content $alerte -Raw) -match 'NON mises à jour') 'I) .env.chiffre corrompu : l''ancien .env est conservé, alerte'
    Remove-Item $alerte -Force
    # J : 1er démarrage (.env absent) -> créé depuis .env.chiffre
    Cles 'cinquieme-valeur'
    $r = Maj; Remove-Item $alerte -ErrorAction SilentlyContinue
    Remove-Item "$S\.env"
    $r = Maj
    Verifier ($r.code -eq 0 -and (EnvServeur) -eq 'CLE=cinquieme-valeur' -and $r.sortie -match 'créées depuis \.env\.chiffre') 'J) premier démarrage : .env absent -> créé depuis .env.chiffre (même sans nouvelle version)'
    # K : mise à jour refusée (tests rouges) qui change aussi les clés -> les clés reviennent à l'état d'avant
    $avant = EnvServeur
    [IO.File]::WriteAllText("$D\.env", "CLE=sixieme-valeur`n", [Text.UTF8Encoding]::new($false))
    $a0 = $env:JARVIS_TEST; $env:JARVIS_TEST = '1'; $env:JARVIS_ENV_MDP_TEST = $PW2; $env:JARVIS_ENV_ITER_TEST = '20000'
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Root 'env-chiffrer.ps1') -Racine $D 2>&1 | Out-Null
    Remove-Item Env:JARVIS_ENV_MDP_TEST, Env:JARVIS_ENV_ITER_TEST; if ($a0) { $env:JARVIS_TEST = $a0 } else { Remove-Item Env:JARVIS_TEST -ErrorAction SilentlyContinue }
    Pousser '6' "Write-Host '  ECHEC test factice'; exit 1"
    $vK = Tete $S
    $r = Maj
    Verifier ($r.code -eq 5 -and (Tete $S) -eq $vK -and (EnvServeur) -eq $avant -and $r.sortie -match 'remises à l''état d''avant') 'K) mise à jour refusée (tests rouges) : le code ET les clés reviennent à l''état d''avant'
    Remove-Item Env:JARVIS_ENV_MDP_FICHIER
    if ($jt) { $env:JARVIS_TEST = $jt }; if ($jc2) { $env:JARVIS_CONFIG = $jc2 }
    Verifier (@(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'jarvis\.ps1' -and $_.CommandLine -match [regex]::Escape($S) }).Count -eq 0) 'Jarvis n''a été ni lancé ni arrêté par ce test'
}
Write-Host '8) Synchro chiffrée du .env : chiffrement, mauvais mot de passe, altération, DPAPI, aucune fuite dans git'
. (Join-Path $Root 'lib\env-chiffre.ps1')
$PW = 'mdp-de-test-Ω-9X!q-Zéro'; $mdp = [Text.Encoding]::UTF8.GetBytes($PW)
$SEC1 = 'tok-fictif-AAAA1111bbbbCCCC'; $SEC2 = 'rk_live_fictifBBBB2222cccc'; $SEC3 = 'cle-supabase-fictive-9876'
$clair = [Text.Encoding]::UTF8.GetBytes("DISCORD_BOT_TOKEN=$SEC1`r`nSTRIPE_RESTRICTED_KEY=$SEC2`nSUPABASE_READ_KEY=$SEC3`nACCENTS=é à ü Ω ✓`n")
Verifier ($script:EnvIterations -ge 600000) 'dérivation de clé : au moins 600 000 itérations PBKDF2-HMAC-SHA256 par défaut'
$sw = [Diagnostics.Stopwatch]::StartNew(); $txt = Protect-EnvOctets $clair $mdp; $r = Unprotect-EnvTexte $txt $mdp; $ms = $sw.ElapsedMilliseconds
Verifier ($r.ok -and (Test-OctetsEgaux $r.octets $clair)) "aller-retour avec les vraies itérations (600 000) : contenu identique octet pour octet ($ms ms pour chiffrer + déchiffrer)"
$script:EnvIterations = 20000      # (les autres vérifications utilisent 20 000 itérations : même code, plus rapide)
$txt = Protect-EnvOctets $clair $mdp; $l = @($txt -split "`n" | Where-Object { $_ })
Verifier ($l.Count -eq 6 -and $l[0] -eq 'JARVIS-ENV-V1' -and $l[1] -eq 'iter=20000' -and $l[2] -match '^sel=' -and $l[3] -match '^iv=' -and $l[4] -match '^donnees=' -and $l[5] -match '^mac=') 'format : en-tête, itérations, sel, IV, données, MAC (6 lignes de texte)'
Verifier ($txt -notmatch [regex]::Escape($SEC1) -and $txt -notmatch [regex]::Escape($SEC2) -and $txt -notmatch 'DISCORD_BOT_TOKEN' -and $txt -notmatch [regex]::Escape($PW) -and $txt -notmatch 'STRIPE') 'rien en clair : ni valeur, ni nom de variable, ni mot de passe dans .env.chiffre'
$txt2 = Protect-EnvOctets $clair $mdp
Verifier ($txt -ne $txt2 -and ($txt -split "`n")[2] -ne ($txt2 -split "`n")[2] -and ($txt -split "`n")[3] -ne ($txt2 -split "`n")[3]) 'sel et IV aléatoires : deux chiffrements du même .env sont différents'
Verifier ((Unprotect-EnvTexte $txt2 $mdp).ok -and (Unprotect-EnvTexte ($txt -replace "`n", "`r`n") $mdp).ok) 'les deux se déchiffrent (fins de ligne Windows ou Unix)'
$mauv = Unprotect-EnvTexte $txt ([Text.Encoding]::UTF8.GetBytes('mauvais-mot-de-passe'))
Verifier (-not $mauv.ok -and $null -eq $mauv.octets -and $mauv.raison -match 'incorrect ou fichier altéré') 'mauvais mot de passe : refusé, aucune donnée rendue'
Verifier (-not (Unprotect-EnvTexte $txt ([byte[]]@())).ok -and -not (Unprotect-EnvTexte $txt ([Text.Encoding]::UTF8.GetBytes($PW + ' '))).ok -and -not (Unprotect-EnvTexte $txt ([Text.Encoding]::UTF8.GetBytes($PW.ToUpper()))).ok) 'mot de passe vide, avec un espace de plus ou en majuscules : refusé'
function Alterer([string]$t, [string]$cle, [scriptblock]$f) { ($t -split "`n" | ForEach-Object { if ($_ -like "$cle=*") { & $f $_ } else { $_ } }) -join "`n" }
$flip = { param($x) $i = $x.IndexOf('=') + 3; $c = $x[$i]; $x.Substring(0, $i) + $(if ($c -eq 'A') { 'B' } else { 'A' }) + $x.Substring($i + 1) }
foreach ($k in 'donnees', 'mac', 'sel', 'iv') { $a = Unprotect-EnvTexte (Alterer $txt $k $flip) $mdp; Verifier (-not $a.ok -and $null -eq $a.octets -and $a.raison -match 'incorrect ou fichier altéré') "fichier altéré (un caractère de « $k » change) : détecté, rien n'est déchiffré" }
$a = Unprotect-EnvTexte (Alterer $txt 'iter' { 'iter=20001' }) $mdp; Verifier (-not $a.ok) 'nombre d''itérations modifié : détecté'
$a = Unprotect-EnvTexte (Alterer $txt 'iter' { 'iter=999999999' }) $mdp; Verifier (-not $a.ok -and $a.raison -match 'format') 'itérations absurdes : refusé avant tout calcul (pas de blocage)'
$a = Unprotect-EnvTexte (($txt -split "`n" | Select-Object -First 5) -join "`n") $mdp; Verifier (-not $a.ok -and $a.raison -match 'format') 'fichier tronqué (ligne manquante) : refusé'
$a = Unprotect-EnvTexte ($txt + "ligne=ajoutee`n") $mdp; Verifier (-not $a.ok) 'ligne ajoutée : refusé'
$a = Unprotect-EnvTexte ($txt -replace 'JARVIS-ENV-V1', 'JARVIS-ENV-V2') $mdp; Verifier (-not $a.ok) 'autre version de format : refusé'
$a = Unprotect-EnvTexte 'n''importe quoi' $mdp; Verifier (-not $a.ok) 'fichier quelconque : refusé sans exception'
$a = Unprotect-EnvTexte (Alterer $txt 'donnees' { 'donnees=!!pas-du-base64!!' }) $mdp; Verifier (-not $a.ok) 'base64 invalide : refusé sans exception'
# DPAPI
$fm = Join-Path $TR 'cache-serveur\env-mdp.dpapi'
Save-MotDePasseDpapi (ConvertTo-SecureDepuisTexte $PW) $fm
$lu = Read-MotDePasseDpapi $fm
Verifier ($lu -and (Test-OctetsEgaux $lu $mdp)) 'DPAPI : le mot de passe enregistré se relit à l''identique (même compte Windows)'
Verifier ((Get-Content $fm -Raw) -notmatch [regex]::Escape($PW) -and (Get-Content $fm -Raw).Length -gt 100) 'DPAPI : le fichier ne contient pas le mot de passe en clair'
Verifier ($null -eq (Read-MotDePasseDpapi (Join-Path $TR 'absent.dpapi'))) 'DPAPI : fichier absent -> $null (pas d''exception)'
Set-Content (Join-Path $TR 'corrompu.dpapi') 'pas du dpapi' -Encoding ASCII; Verifier ($null -eq (Read-MotDePasseDpapi (Join-Path $TR 'corrompu.dpapi'))) 'DPAPI : fichier illisible -> $null'
$env:JARVIS_ENV_MDP_FICHIER = $fm; Verifier ((Get-FichierMotDePasseServeur) -eq $fm) 'emplacement du mot de passe : remplaçable (tests) ; par défaut dans %LOCALAPPDATA%\Jarvis, HORS du dépôt'
Remove-Item Env:JARVIS_ENV_MDP_FICHIER; Verifier ((Get-FichierMotDePasseServeur) -like "$env:LOCALAPPDATA*" -and (Get-FichierMotDePasseServeur) -notlike "$Root*") 'emplacement par défaut : hors du dossier Jarvis'
# restauration atomique
$rr = Join-Path $TR 'restaure'; New-Item -ItemType Directory $rr | Out-Null
[IO.File]::WriteAllText("$rr\.env.chiffre", $txt, [Text.UTF8Encoding]::new($false))
$x = Restore-EnvDepuisChiffre $rr $mdp
Verifier ($x.statut -eq 'cree' -and (Test-OctetsEgaux ([IO.File]::ReadAllBytes("$rr\.env")) $clair) -and -not (Test-Path "$rr\.env.tmp") -and -not (Test-Path "$rr\.env.bak")) '.env absent : créé depuis .env.chiffre (contenu identique, aucun fichier temporaire)'
$x = Restore-EnvDepuisChiffre $rr $mdp; Verifier ($x.statut -eq 'inchange' -and -not (Test-Path "$rr\.env.bak")) 'même contenu : « inchangé » (pas de sauvegarde inutile, pas de redémarrage)'
$clair2 = [Text.Encoding]::UTF8.GetBytes("DISCORD_BOT_TOKEN=nouvelle-valeur-zzz`n")
[IO.File]::WriteAllText("$rr\.env.chiffre", (Protect-EnvOctets $clair2 $mdp), [Text.UTF8Encoding]::new($false))
$x = Restore-EnvDepuisChiffre $rr $mdp
Verifier ($x.statut -eq 'mis-a-jour' -and (Test-OctetsEgaux ([IO.File]::ReadAllBytes("$rr\.env")) $clair2) -and (Test-OctetsEgaux ([IO.File]::ReadAllBytes("$rr\.env.bak")) $clair) -and -not (Test-Path "$rr\.env.tmp")) 'nouvelle version : .env remplacé, ancien .env gardé dans .env.bak, aucun fichier temporaire'
$hAvant = Hash "$rr\.env"
$x = Restore-EnvDepuisChiffre $rr ([Text.Encoding]::UTF8.GetBytes('faux-mot-de-passe'))
Verifier ($x.statut -eq 'echec' -and (Hash "$rr\.env") -eq $hAvant -and -not (Test-Path "$rr\.env.tmp")) 'mauvais mot de passe : l''ancien .env est conservé tel quel'
Set-Content "$rr\.env.chiffre" ([regex]::Replace((Get-Content "$rr\.env.chiffre" -Raw), 'mac=(.)', { param($m) 'mac=' + $(if ($m.Groups[1].Value -eq 'Z') { 'Y' } else { 'Z' }) })) -Encoding ASCII
$x = Restore-EnvDepuisChiffre $rr $mdp; Verifier ($x.statut -eq 'echec' -and (Hash "$rr\.env") -eq $hAvant) 'fichier corrompu : l''ancien .env est conservé tel quel'
$x = Restore-EnvDepuisChiffre $rr $null; Verifier ($x.statut -eq 'echec' -and $x.raison -match 'mot de passe du serveur absent' -and (Hash "$rr\.env") -eq $hAvant) 'mot de passe du serveur absent : échec clair, .env intact'
$x = Restore-EnvDepuisChiffre (Join-Path $TR 'vide') $mdp; Verifier ($x.statut -eq 'absent') 'sans .env.chiffre : rien à faire'
# Initialize (1er démarrage)
$ini = Join-Path $TR 'premier'; New-Item -ItemType Directory $ini | Out-Null; [IO.File]::WriteAllText("$ini\.env.chiffre", $txt, [Text.UTF8Encoding]::new($false))
$env:JARVIS_ENV_MDP_FICHIER = $fm
$x = Initialize-EnvDepuisChiffre $ini; Verifier ($x.statut -eq 'cree' -and (Test-OctetsEgaux ([IO.File]::ReadAllBytes("$ini\.env")) $clair)) 'premier démarrage : .env créé depuis .env.chiffre avec le mot de passe DPAPI'
$h = Hash "$ini\.env"; $x = Initialize-EnvDepuisChiffre $ini; Verifier ($x.statut -eq 'rien' -and (Hash "$ini\.env") -eq $h) '.env déjà présent : jamais touché au démarrage'
Remove-Item Env:JARVIS_ENV_MDP_FICHIER
# script env-chiffrer.ps1 + audit git
if ($aGit) {
    $ErrorActionPreference = 'Continue'
    $T = Join-Path $TR 'depot-cles'; New-Item -ItemType Directory $T | Out-Null
    $env:GIT_AUTHOR_NAME = 'test'; $env:GIT_AUTHOR_EMAIL = 't@t.t'; $env:GIT_COMMITTER_NAME = 'test'; $env:GIT_COMMITTER_EMAIL = 't@t.t'
    & git -c init.defaultBranch=main init -q $T 2>$null
    Copy-Item (Join-Path $Root '.gitignore') "$T\.gitignore"; 'print("x")' | Set-Content "$T\code.py" -Encoding ASCII
    [IO.File]::WriteAllText("$T\.env", [Text.Encoding]::UTF8.GetString($clair), [Text.UTF8Encoding]::new($false))
    & git -C $T add -A 2>$null; & git -C $T commit -q -m base 2>$null
    $env:JARVIS_ENV_MDP_TEST = $PW; $env:JARVIS_ENV_ITER_TEST = '20000'
    function Chiffrer { $o = & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Root 'env-chiffrer.ps1') -Racine $T -Commit 2>&1 | Out-String; @{ sortie = $o; code = $LASTEXITCODE } }
    $c1 = Chiffrer
    $suivis = @(& git -C $T ls-files 2>$null)
    Verifier ($c1.code -eq 0 -and (Test-Path "$T\.env.chiffre") -and $suivis -contains '.env.chiffre' -and $suivis -notcontains '.env' -and $c1.sortie -match 'Commit créé' -and $c1.sortie -match 'git push') 'env-chiffrer.ps1 -Commit : .env.chiffre créé et commité, la commande « git push » est donnée, .env n''est pas suivi'
    Verifier ($c1.sortie -notmatch [regex]::Escape($SEC1) -and $c1.sortie -notmatch [regex]::Escape($PW)) 'la sortie du script ne contient ni clé ni mot de passe'
    $nb1 = @(& git -C $T log --oneline 2>$null).Count
    $c2 = Chiffrer
    Verifier ($c2.sortie -match 'déjà à jour' -and @(& git -C $T log --oneline 2>$null).Count -eq $nb1) '.env inchangé : « déjà à jour », aucun commit inutile'
    [IO.File]::WriteAllText("$T\.env", "DISCORD_BOT_TOKEN=valeur-modifiee-QQQ`n", [Text.UTF8Encoding]::new($false))
    $c3 = Chiffrer
    Verifier ($c3.code -eq 0 -and $c3.sortie -match 'Commit créé' -and @(& git -C $T log --oneline 2>$null).Count -eq $nb1 + 1) 'clé modifiée : nouveau commit de .env.chiffre'
    $modifies = @(& git -C $T show --name-only --pretty=format: HEAD 2>$null | Where-Object { $_ })
    Verifier ($modifies.Count -eq 1 -and $modifies[0] -eq '.env.chiffre') 'le commit ne contient QUE .env.chiffre'
    $dec = Unprotect-EnvTexte (Get-Content "$T\.env.chiffre" -Raw -Encoding UTF8) $mdp
    Verifier ($dec.ok -and [Text.Encoding]::UTF8.GetString($dec.octets) -match 'valeur-modifiee-QQQ') 'le .env.chiffre commité se déchiffre avec le mot de passe'
    $env:JARVIS_ENV_MDP_TEST = 'court'; $c4 = Chiffrer; Verifier ($c4.code -ne 0 -and $c4.sortie -match 'trop court') 'mot de passe trop court : refusé'
    $env:JARVIS_ENV_MDP_TEST = $PW
    # audit : rien de sensible nulle part dans git
    $valeurs = @($SEC1, $SEC2, $SEC3, 'valeur-modifiee-QQQ', $PW, 'DISCORD_BOT_TOKEN=', 'STRIPE_RESTRICTED_KEY=')
    $log = (& git -C $T log -p --all 2>$null | Out-String)
    $objets = (& git -C $T cat-file --batch-all-objects --batch 2>$null | Out-String)
    $arbre = (@(Get-ChildItem $T -Recurse -File -Force | Where-Object { $_.FullName -notmatch '\\\.git\\' -and $_.Name -ne '.env' } | ForEach-Object { Get-Content $_.FullName -Raw -Encoding UTF8 -ErrorAction SilentlyContinue }) -join "`n")
    $fuites = @($valeurs | Where-Object { $log.Contains($_) -or $objets.Contains($_) -or $arbre.Contains($_) })
    Verifier ($fuites.Count -eq 0) 'git log -p --all, tous les objets git et l''arbre de travail (hors .env) : AUCUNE valeur de clé, AUCUN nom de variable de clé, AUCUN mot de passe'
    Verifier (@(& git -C $T ls-files 2>$null | Where-Object { $_ -match '^\.env$|\.env\.bak|\.env\.tmp' }).Count -eq 0 -and (& git -C $T check-ignore .env .env.bak .env.tmp 2>$null).Count -eq 3) '.env, .env.bak et .env.tmp sont ignorés par git ; git ls-files ne les contient pas'
    Verifier ((& git -C $T check-ignore .env.chiffre 2>$null).Count -eq 0 -and (& git -C $T check-ignore .env.example 2>$null).Count -eq 0) '.env.chiffre et .env.example ne sont PAS ignorés (suivis)'
    $disque = @(Get-ChildItem $TR -Recurse -File -Force -ErrorAction SilentlyContinue | Where-Object { $_.FullName -notmatch '\\\.git\\' } | Where-Object { (Select-String -Path $_.FullName -Pattern $PW -SimpleMatch -Quiet -ErrorAction SilentlyContinue) })
    Verifier ($disque.Count -eq 0) 'le mot de passe n''est écrit sur aucun fichier (ni dépôt, ni DPAPI, ni temporaire)'
    Remove-Item Env:JARVIS_ENV_MDP_TEST, Env:JARVIS_ENV_ITER_TEST
    $ErrorActionPreference = 'Stop'
} else { Verifier $true '(git absent : audit du dépôt sauté)' }
$si = Get-Content (Join-Path $Root 'installer-serveur.ps1') -Raw -Encoding UTF8; $ec = Get-Content (Join-Path $Root 'env-chiffrer.ps1') -Raw -Encoding UTF8; $lib = Get-Content (Join-Path $Root 'lib\env-chiffre.ps1') -Raw -Encoding UTF8
Verifier ($si -match 'Initialize-ClesServeur' -and $si -match 'Save-MotDePasseDpapi' -and $si -match 'essai \$i sur 3' -and $si -match 'Read-MotDePasseSaisie') 'installer-serveur.ps1 : demande le mot de passe UNE fois (3 essais), le vérifie, le protège par DPAPI'
Verifier ($lib -match 'Read-Host \$invite -AsSecureString' -and $lib -notmatch 'Write-Host[^;\r\n]*\$mdp' -and $ec -notmatch 'Write-Host\s+[^;\r\n]*\$b[12]' -and $ec -match 'Clear-Octets') 'mot de passe : saisie masquée (SecureString), jamais affiché, octets effacés après usage'
$ecr = @($lib -split "`n" | Where-Object { $_ -match 'WriteAllText|WriteAllBytes|Set-Content|Out-File' -and $_ -match '\$mdp|\$m1|\$b1' })
Verifier ($ecr.Count -eq 1 -and $ecr[0] -match 'ConvertFrom-SecureString' -and $ec -notmatch 'Set-Content|Out-File[^\r\n]*\$b1') 'le mot de passe en clair n''est jamais écrit : seule la version protégée par DPAPI (ConvertFrom-SecureString) est écrite'
$mj = Get-Content (Join-Path $Root 'jarvis.ps1') -Raw -Encoding UTF8
Verifier ($mj -match "'env-pousser'" -and $mj -match 'env-chiffrer\.ps1' -and $mj -match 'Initialize-EnvDepuisChiffre') 'jarvis.ps1 env-pousser branché ; 1er démarrage : .env créé depuis .env.chiffre'
$gi2 = @(Get-Content (Join-Path $Root '.gitignore') -Encoding UTF8 | ForEach-Object { $_.Trim() })
Verifier ($gi2 -contains '.env' -and $gi2 -contains '.env.bak' -and $gi2 -contains '.env.tmp' -and $gi2 -notcontains '.env.chiffre' -and $gi2 -notcontains '.env*') '.gitignore : .env, .env.bak, .env.tmp ; .env.chiffre n''y est pas'
Verifier ((Get-Content (Join-Path $Root '.env.example') -Raw -Encoding UTF8) -match 'env-pousser') '.env.example explique la synchro chiffrée'
$script:EnvIterations = 600000

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
