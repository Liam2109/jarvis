# Test SILENCIEUX du mode serveur LÉGER : aucune écoute du micro (ni ecoute.py, ni Whisper, ni Vosk, ni recherche de micro), ni voix Piper, ni HUD, ni Edge ; Ollama déchargé après usage ;
# consigne « français » et rejet des réponses en chinois ; jarvis.ps1 diag-serveur (mesures simulées). Aucun micro, aucun son, aucune fenêtre, aucun service lancé. Code de sortie 0 = réussi.
$ErrorActionPreference = 'Stop'
$env:JARVIS_TEST = '1'
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $Root 'lib\journal.ps1')
$TR = Join-Path $env:TEMP ('jarvis-test-' + [guid]::NewGuid().ToString('N').Substring(0, 8)); New-Item -ItemType Directory $TR, "$TR\memoire", "$TR\logs" | Out-Null; $script:JarvisRoot = $TR
'# To-do' | Set-Content "$TR\memoire\todo.md" -Encoding UTF8; '# N' | Set-Content "$TR\memoire\notes.md" -Encoding UTF8; '# R' | Set-Content "$TR\memoire\resume.md" -Encoding UTF8
$Config = Get-Content $(if ($env:JARVIS_CONFIG -and (Test-Path $env:JARVIS_CONFIG)) { $env:JARVIS_CONFIG } else { Join-Path $Root 'config.json' }) -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($l in 'voix', 'business', 'permissions', 'actions', 'coffre', 'entrees', 'ecrans', 'tableau', 'visage', 'sons', 'raccourcis', 'cerveau', 'cerveau-local', 'veille', 'memoire', 'rapide', 'discretion', 'modejeu', 'competences', 'marche', 'priorite', 'comprehension', 'routeur', 'pc', 'bureau', 'salle-marche', 'matin', 'discord', 'veille-reveil', 'diag-serveur') { . (Join-Path $Root "lib\$l.ps1") }
$script:JarvisRoot = $TR
$echecs = 0
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }
function Fixer([string]$cle, $val) { if ($Config.PSObject.Properties[$cle]) { $Config.$cle = $val } else { $Config | Add-Member -NotePropertyName $cle -NotePropertyValue $val } }
function Effacer([string]$cle) { if ($Config.PSObject.Properties[$cle]) { $Config.PSObject.Properties.Remove($cle) } }
$vraie = Get-Content (Join-Path $Root 'config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
function Journal { $f = Join-Path $TR ('logs\journal-{0}.md' -f (Get-Date -Format 'yyyy-MM-dd')); if (Test-Path $f) { Get-Content $f -Raw -Encoding UTF8 } else { '' } }
function Get-ProcsEcoute { @(Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -ne $PID -and $_.CommandLine -match 'voix\\(ecoute|reveil|piper)' }).Count }
$procAvant = Get-ProcsEcoute

Write-Host '1) Micro : "non" par défaut, surchargeable par config.local.json'
Verifier ($vraie.serveur_micro -eq 'non') 'config.json : serveur_micro = "non"'
$cfgDir = Join-Path $TR 'cfg'; New-Item -ItemType Directory $cfgDir | Out-Null; $script:JarvisRoot = $cfgDir; Copy-Item (Join-Path $Root 'config.json') "$cfgDir\config.json"
[IO.File]::WriteAllText("$cfgDir\config.local.json", '{ "mode_serveur": true, "serveur_micro": "auto" }', [Text.UTF8Encoding]::new($false))
$jc = $env:JARVIS_CONFIG; Remove-Item Env:JARVIS_CONFIG -ErrorAction SilentlyContinue; $c = Import-ConfigJarvis; if ($jc) { $env:JARVIS_CONFIG = $jc }
Verifier ($c.mode_serveur -eq $true -and $c.serveur_micro -eq 'auto') 'config.local.json peut remettre "auto" (ou "oui") si le serveur a un micro'
$script:JarvisRoot = $TR
Fixer 'mode_serveur' $true
$script:MicroDetecte = $null; $script:FauxMicroServeur = $null
Fixer 'serveur_micro' 'non'; Verifier ((Get-MicroServeur) -eq $false -and $null -eq $script:MicroDetecte) '"non" : pas de micro, ET aucune recherche du matériel (aucun python lancé pour sonder)'
Effacer 'serveur_micro'; Verifier ((Get-MicroServeur) -eq $false -and $null -eq $script:MicroDetecte) 'réglage absent : "non" aussi'
foreach ($v in 'false', 'non', '0', 'off', '', 'nimporte quoi') { Fixer 'serveur_micro' $v; Verifier ((Get-MicroServeur) -eq $false -and $null -eq $script:MicroDetecte) "serveur_micro = « $v » : pas de micro" }
foreach ($v in 'oui', 'true', 'OUI') { Fixer 'serveur_micro' $v; Verifier ((Get-MicroServeur) -eq $true) "serveur_micro = « $v » : micro voulu" }
$script:FauxMicroServeur = $false; Fixer 'serveur_micro' 'auto'; Verifier ((Get-MicroServeur) -eq $false) '"auto" sans micro branché : pas d''écoute'
$script:FauxMicroServeur = $true; Verifier ((Get-MicroServeur) -eq $true) '"auto" avec un micro : écoute possible'
$script:FauxMicroServeur = $null

Write-Host '2) Mode serveur sans micro : aucun processus d''écoute ne démarre'
Fixer 'serveur_micro' 'non'; $script:Ecoute = $null; $script:EcouteServeurRefusee = 0
Start-Ecoute
Verifier ($null -eq $script:Ecoute -and $script:EcouteServeurRefusee -eq 1) 'Start-Ecoute : refusé en mode serveur (ecoute.py n''est pas lancé)'
$script:Actif = $false; $script:EtatFichier2 = Join-Path $TR 'etat.json'; $script:SourdineFlag = Join-Path $TR 'sourdine.flag'
Set-Actif $true 'test'; Verifier ($null -eq $script:Ecoute) 'réveil / activation : toujours aucune écoute'
Switch-EcouteMode 'jeu'; Switch-EcouteMode 'normal'; Verifier ($null -eq $script:Ecoute) 'mode jeu : toujours aucune écoute'
Verifier ($script:EcouteServeurRefusee -ge 3) "chaque tentative est refusée ($($script:EcouteServeurRefusee) refus)"
Update-VeilleReveil; Verifier ($null -eq $script:VeilleProc -and (Get-EtatVeilleVoulu) -eq 'arret') 'aucune écoute de veille (reveil.py) non plus'
Verifier ((Get-ProcsEcoute) -eq $procAvant) 'aucun processus ecoute.py / reveil.py / Piper n''a été créé pendant ce test'
$mj = Get-Content (Join-Path $Root 'jarvis.ps1') -Raw -Encoding UTF8; $en = Get-Content (Join-Path $Root 'lib\entrees.ps1') -Raw -Encoding UTF8
Verifier ($en -match '(?s)function Start-Ecoute \{\s*if \(\(Test-ModeServeur\) -and -not \(Get-MicroServeur\)\)') 'le refus est la PREMIÈRE ligne de Start-Ecoute (avant tout démarrage de processus)'
Verifier ($mj -match 'if \(\$serveur\) \{ if \(Get-MicroServeur\) \{ Start-Ecoute \} \}') 'jarvis.ps1 : au démarrage du serveur, l''écoute n''est lancée que si un micro est voulu'
$nbStart = ([regex]::Matches($en, 'ProcessStartInfo ''python''')).Count
Verifier ($nbStart -ge 1) 'contrôle de non-régression : Start-Ecoute lance bien ecoute.py hors mode serveur'
Fixer 'mode_serveur' $false; $script:EcouteServeurRefusee = 0; Start-Ecoute; Verifier ($script:EcouteServeurRefusee -eq 0) 'hors mode serveur : le refus ne s''applique pas (le PC de bureau est inchangé)'
Fixer 'mode_serveur' $true

Write-Host '3) Mode serveur : ni voix, ni Piper, ni HUD, ni Edge'
Verifier ((Test-PiperPret) -eq $false -and (Test-PiperPret -Repli) -eq $false) 'Piper : jamais chargé en mode serveur'
$pj = Join-Path $env:TEMP 'jarvis-prechauffe.json'; $avant = if (Test-Path $pj) { (Get-Item $pj).LastWriteTimeUtc.Ticks } else { 0 }
Start-PrechauffageTts; $apres = if (Test-Path $pj) { (Get-Item $pj).LastWriteTimeUtc.Ticks } else { 0 }
Verifier ($avant -eq $apres) 'préchauffage de la synthèse vocale : sauté'
Verifier ($null -eq (Start-Visage)) 'HUD / Edge : aucune fenêtre'
$vr = Get-Content (Join-Path $Root 'lib\voix.ps1') -Raw -Encoding UTF8
Verifier ($vr -match '(?s)function Start-PrechauffageTts \{[^}]*?if \(Test-ModeServeur\) \{ return \}' -and $vr -match 'if \(\(Test-ModeTest\) -or \(Test-ModeServeur\)\) \{ return \$false \}') 'sources : garde-fous serveur dans voix.ps1'
Verifier (-not (Test-VeilleBureau)) 'veille du PC principal : jamais sur le serveur'
$script:Dits = @(); Parler 'Test du serveur léger.'; Verifier ((Journal) -match 'Parole non prononcée \(mode serveur\)') 'Parler : texte au journal seulement'

Write-Host '4) Ollama : déchargé après usage sur le serveur'
function Get-PrioriteEffective { 'eleve' }
Verifier ((Get-OllamaConfig).keep -eq '5m') 'serveur : keep_alive = 5 min (même en priorité « élevée »)'
Fixer 'ollama' ([pscustomobject]@{ modele = 'qwen2.5:3b'; url = 'http://127.0.0.1:11434'; keep_alive = '10m' }); Verifier ((Get-OllamaConfig).keep -eq '10m') 'ollama.keep_alive dans config.local.json : respecté'
Fixer 'ollama' ([pscustomobject]@{ modele = 'qwen2.5:3b'; url = 'http://127.0.0.1:11434'; keep_alive = '24h' }); Verifier ((Get-OllamaConfig).keep -eq '24h') 'ollama.keep_alive = 24h reste possible si vous le demandez'
Fixer 'ollama' $vraie.ollama
Fixer 'mode_serveur' $false; Verifier ((Get-OllamaConfig).keep -eq -1) 'hors serveur : comportement d''avant (priorité élevée : modèle gardé chaud)'
Fixer 'mode_serveur' $true
$cl = Get-Content (Join-Path $Root 'lib\cerveau-local.ps1') -Raw -Encoding UTF8
Verifier ($cl -match '(?s)function Start-OllamaReveil.*?\(Test-ModeServeur\)') 'Start-OllamaReveil : pas de préchauffage sur le serveur (le modèle ne se charge qu''à la demande)'
Verifier ($vraie.cerveau -eq 'hybride') 'cerveau = hybride : ordres simples en local, questions ouvertes et textes longs par Claude'
foreach ($o in 'explique-moi la différence entre un SSD et un disque dur', 'résume ce document', 'pourquoi le ciel est bleu', 'écris un mail à un client') { Verifier (-not (Test-OrdreSimple $o)) "« $o » : question ouverte -> Claude" }
foreach ($o in 'ouvre le bloc-notes', 'quelle heure est-il', 'monte le volume') { Verifier (Test-OrdreSimple $o) "« $o » : ordre simple -> modèle local" }

Write-Host '5) Le modèle local répond en français (jamais en chinois)'
foreach ($t in '{"dit":"好的，先生","actions":[]}', '{"dit":"はい","actions":[]}', '{"dit":"Хорошо","actions":[]}', '{"dit":"안녕","actions":[]}') { Verifier (Test-TexteNonLatin $t) "détecté comme non français : $t" }
foreach ($t in '{"dit":"Très bien monsieur, c''est fait. Œuvre à ça : été, déjà, çà.","actions":[]}', '{"dit":"Il fait 21 °C – « agréable ».","actions":[]}') { Verifier (-not (Test-TexteNonLatin $t)) "français accepté (accents, œ, guillemets, tirets)" }
Verifier ($script:ConsigneFrancais -match 'TOUJOURS et UNIQUEMENT en français' -and $script:ConsigneFrancais -match 'chinois') 'consigne système en français, ajoutée à chaque appel du modèle local'
$script:OllamaTestAutorise = $true; $script:Corps = @(); $script:Reponses = New-Object System.Collections.Queue
function Invoke-RestMethod { param($Uri, $Method, $Body, $ContentType, $TimeoutSec) $script:Corps += [Text.Encoding]::UTF8.GetString($Body); [pscustomobject]@{ message = [pscustomobject]@{ content = $script:Reponses.Dequeue() } } }
$script:Reponses.Enqueue('{"dit":"好的先生","actions":[]}'); $script:Reponses.Enqueue('{"dit":"Très bien monsieur.","actions":[]}')
$r = Invoke-Ollama 'Tu es Jarvis.' 'dis ok'
Verifier ($r -match 'Très bien monsieur' -and $script:Corps.Count -eq 2) 'réponse en chinois : un 2e essai est fait automatiquement et la réponse française est gardée'
$b1 = ($script:Corps[0] | ConvertFrom-Json).messages[0].content; $b2 = ($script:Corps[1] | ConvertFrom-Json).messages[0].content
Verifier ($b1 -match 'UNIQUEMENT en français' -and $b2 -match 'UNIQUEMENT en français' -and $b2 -match 'FRANÇAIS, avec l''alphabet latin') 'le 1er appel porte la consigne ; le 2e la renforce'
$script:Corps = @(); $script:Reponses.Enqueue('{"dit":"你好","actions":[]}'); $script:Reponses.Enqueue('{"dit":"谢谢","actions":[]}')
Verifier ($null -eq (Invoke-Ollama 'x' 'y') -and $script:Corps.Count -eq 2) 'deux réponses en chinois : rejetées (null) -> l''appelant retombe sur Claude'
Verifier ((Journal) -match 'autre langue') 'le rejet est noté au journal'
$script:Corps = @(); $script:Reponses.Enqueue('{"dit":"Très bien.","actions":[]}'); [void](Invoke-Ollama 'x' 'y'); Verifier ($script:Corps.Count -eq 1) 'réponse française : un seul appel'
$script:Reponses.Enqueue('{"dit":"你好","actions":[]}'); $script:Reponses.Enqueue('{"dit":"谢谢","actions":[]}')
Verifier ($null -eq (Get-PlanLocal 'sys' 'user')) 'plan local en chinois : aucun plan accepté (le cerveau passe à Claude)'
Remove-Item Function:\Invoke-RestMethod; $script:OllamaTestAutorise = $false
Verifier ((Get-PromptSystemeLocal) -match 'en français') 'le prompt système local demande déjà le français'

Write-Host '6) jarvis.ps1 diag-serveur (mesures simulées)'
$role = { param($n, $c) Get-RoleProcessus ([pscustomobject]@{ Name = $n; CommandLine = $c }) }
Verifier ((& $role 'python.exe' 'python -I -u C:\J\voix\ecoute.py --x') -eq 'écoute du micro (ecoute.py)' -and (& $role 'python.exe' 'python pont-discord\pont.py') -eq 'pont Discord' -and (& $role 'ollama.exe' 'ollama serve') -eq 'Ollama (service)' -and (& $role 'notepad.exe' 'notepad') -eq $null) 'rôles reconnus (écoute, pont Discord, Ollama) ; le reste est ignoré'
$reel = Get-RamProcessusJarvis; Verifier ($reel.totalMo -gt 500 -and $reel.libreMo -gt 0) "lecture réelle de la RAM : $($reel.totalMo) Mo au total (lecture seule)"
function Get-RamProcessusJarvis { @{ totalMo = 5900; libreMo = 400; processus = @(@{ role = 'Ollama (modèle chargé)'; pid = 11; mo = 2400 }, @{ role = 'écoute du micro (ecoute.py)'; pid = 12; mo = 900 }, @{ role = 'pont Discord'; pid = 13; mo = 120 }) } }
function Measure-ReponseClaude { @{ ok = $true; ms = 21000; raison = '' } }
function Measure-ReponseOllama { @{ actif = $true; pret = $true; modele = 'qwen2.5:3b'; froidMs = 31000; chaudMs = 9000; chargeMo = 2400; keep = '5m'; raison = '' } }
$rap = (Get-DiagServeur) -join "`n"
Verifier ($rap -match 'Diagnostic du serveur' -and $rap -match '5[,.]8 Go au total' -and $rap -match '93 % utilisés' -and $rap -match '2400 Mo\s+Ollama' -and $rap -match 'TOTAL lié à Jarvis') 'RAM : total, libre, % et détail par processus avec TOTAL'
Verifier ($rap -match 'Claude \(claude -p\)\s+: 21[,.]0 s' -and $rap -match '1er appel 31[,.]0 s, appel suivant 9[,.]0 s') 'temps de réponse de Claude et d''Ollama affichés (1er appel / suivant)'
Verifier ($rap -match 'ANOMALIE : une écoute du micro tourne' -and $rap -match 'Ollama occupe 2400 Mo' -and $rap -match 'mémoire est presque pleine' -and $rap -match 'Claude met 21[,.]0 s' -and $rap -match 'Ollama est lent') 'résumé : écoute anormale, Ollama trop gros, mémoire pleine, Claude et Ollama lents'
Verifier ($rap -notmatch 'C:\\|--x|python -I') 'aucune ligne de commande ni chemin dans le rapport'
function Get-RamProcessusJarvis { @{ totalMo = 5900; libreMo = 3500; processus = @(@{ role = 'pont Discord'; pid = 13; mo = 120 }) } }
function Measure-ReponseClaude { @{ ok = $true; ms = 4200; raison = '' } }
function Measure-ReponseOllama { @{ actif = $false; pret = $false; modele = 'qwen2.5:3b'; froidMs = 0; chaudMs = 0; chargeMo = 0; keep = '5m'; raison = 'Ollama installé mais le service ne répond pas' } }
$rap = (Get-DiagServeur) -join "`n"
Verifier ($rap -match 'Rien d''anormal' -and $rap -match 'Claude \(claude -p\)\s+: 4[,.]2 s' -and $rap -match 'Ollama\s+: non mesuré') 'serveur sain : « rien d''anormal », Ollama arrêté = non mesuré (jamais démarré par le diagnostic)'
function Measure-ReponseClaude { @{ ok = $false; ms = 90000; raison = 'pas de réponse (claude introuvable, non connecté ou délai dépassé)' } }
$rap = (Get-DiagServeur) -join "`n"; Verifier ($rap -match 'ÉCHEC' -and $rap -match 'Claude ne répond pas') 'Claude muet : signalé'
$rap = (Get-DiagServeur -SansMesure) -join "`n"; Verifier ($rap -match 'mesures de temps non faites') '-SansMesure : aucun appel'
Verifier ($mj -match "'diag-serveur' \{ Get-DiagServeur" -and $mj -match 'lib\\diag-serveur\.ps1' -and $mj -match '#   diag-serveur') 'jarvis.ps1 diag-serveur : commande branchée et documentée'
$ds = Get-Content (Join-Path $Root 'lib\diag-serveur.ps1') -Raw -Encoding UTF8
Verifier ($ds -notmatch 'Stop-Process|\.Kill\(|Remove-Item|Set-Content|WriteAllText|Start-Process|ollama serve') 'le diagnostic ne modifie rien, n''arrête rien et ne démarre aucun service'

Write-Host '7) installer-serveur.ps1 : nouvelle config.local.json'
$sd = Join-Path $TR 'is'; New-Item -ItemType Directory $sd | Out-Null
. (Join-Path $Root 'installer-serveur.ps1') -SeulementFonctions -Racine $sd
[void](New-ConfigLocale $sd 'qwen2.5:3b'); $j = Get-Content "$sd\config.local.json" -Raw -Encoding UTF8 | ConvertFrom-Json
Verifier ($j.serveur_micro -eq 'non' -and $j.ollama.keep_alive -eq '5m' -and $j.mode_serveur -eq $true -and $j.discord_actif -eq $true) 'installateur : serveur_micro = non, Ollama déchargé après 5 min, mode serveur, Discord actif'

Write-Host '8) Réponse rapide sur le serveur : aucun routeur ni modèle local (CPU seul), Claude direct'
Fixer 'mode_serveur' $true; Effacer 'serveur_cerveau_local'; Fixer 'cerveau' 'hybride'
$script:OllamaCache = @{ installe = $true; actif = $true; modeles = @('qwen2.5:7b'); pret = $true; raison = '' }; $script:OllamaCacheHeure = Get-Date
Verifier ((Get-ModeCerveau) -eq 'claude') 'mode serveur : cerveau effectif = claude, même si Ollama est prêt (aucun modèle chargé pour le routage)'
Verifier ($null -eq (Resolve-Routeur 'quelle est la capitale de la France') -and $script:RouteurEtat -eq 'indisponible') 'mode serveur : le routeur local est sauté (aucun appel à Ollama)'
Fixer 'serveur_cerveau_local' $true; Verifier ((Get-ModeCerveau) -eq 'hybride') 'serveur_cerveau_local = true : le cerveau local redevient possible'
Fixer 'mode_serveur' $false; Effacer 'serveur_cerveau_local'; Verifier ((Get-ModeCerveau) -eq 'hybride') 'PC principal : cerveau hybride inchangé'
Verifier ($vraie.serveur_cerveau_local -eq $false -and $vraie.discord_conversation -eq $true -and $vraie.claude_modele -eq 'haiku' -and $vraie.discord_conversation_modele -match 'haiku') 'config.json : modèle rapide, conversation directe Discord, cerveau local du serveur désactivé'
$ej = Get-Content (Join-Path $Root '.env.example') -Raw -Encoding UTF8; Verifier ($ej -match 'ANTHROPIC_API_KEY=') '.env.example documente ANTHROPIC_API_KEY'

Write-Host ''
Remove-Item $TR -Recurse -Force -ErrorAction SilentlyContinue
Verifier ((Get-ProcsEcoute) -eq $procAvant) 'aucun processus d''écoute ou de voix créé par ce test'
if ($echecs) { Write-Host "ÉCHEC : $echecs vérification(s) en échec." -ForegroundColor Red; exit 1 }
Write-Host 'TOUT EST VERT.'
