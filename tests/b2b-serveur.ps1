# Test SILENCIEUX des agents B2B sur le portable serveur : liste blanche git (rien de secret ne part), config locale, machine active, lanceur serveur (priorité basse, un agent à la fois, aucun navigateur),
# tâches planifiées (plan et idempotence, SANS rien enregistrer), dépendances Python, intégration à maj-auto.ps1 (dépôts git temporaires, aucun réseau), séparation rapide / complète de tests\tout.ps1, document de transfert.
# Aucun agent n'est lancé (python factice), rien n'est installé, aucune tâche planifiée créée, aucun secret affiché. Code de sortie 0 = réussi.
$ErrorActionPreference = 'Stop'
$env:JARVIS_TEST = '1'
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $Root 'lib\journal.ps1')
$TR = Join-Path $env:TEMP ('jarvis-test-' + [guid]::NewGuid().ToString('N').Substring(0, 8)); New-Item -ItemType Directory $TR, "$TR\memoire", "$TR\logs" | Out-Null; $script:JarvisRoot = $TR
$echecs = 0
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }
function Hash([string]$f) { if (Test-Path $f) { (Get-FileHash $f).Hash } else { '' } }
function Lire([string]$f) { Get-Content $f -Raw -Encoding UTF8 }
$B2B = Join-Path $Root 'B2B'; $AG = Join-Path $B2B 'agents'
$aGit = [bool](Get-Command git -ErrorAction SilentlyContinue)
$avantConfig = Hash (Join-Path $Root 'config.json')

try {
Write-Host '1) Liste blanche git : ce qui serait poussé de B2B\'
$gi = @(Get-Content (Join-Path $Root '.gitignore') -Encoding UTF8 | ForEach-Object { $_.Trim() })
Verifier ($gi -notcontains 'B2B/') 'la ligne « B2B/ » (tout ignorer) a disparu de .gitignore : remplacée par une liste blanche'
Verifier ($gi -contains 'B2B/*' -and $gi -contains '*.local.json') '.gitignore : B2B/* ignoré par défaut, *.local.json ignoré partout'
if (-not $aGit) { Verifier $true '(git absent : contrôles de la liste blanche sautés)' } else {
    $gd = Join-Path $TR 'gd'; & git init --bare -q $gd 2>$null
    $cand = @(& git -C $Root --git-dir=$gd --work-tree=$Root ls-files --others --exclude-standard 2>$null | ForEach-Object { $_ -replace '/', '\' } | Where-Object { $_ -like 'B2B\*' })
    Verifier ($cand.Count -gt 40) "B2B : $($cand.Count) fichiers seraient ajoutés par git add (simulé sans toucher au dossier)"
    $tailles = @($cand | ForEach-Object { (Get-Item (Join-Path $Root $_)).Length }); $total = ($tailles | Measure-Object -Sum).Sum
    Write-Host ("        taille de B2B à pousser : {0:N2} Mo, plus gros fichier : {1:N0} Ko" -f ($total / 1MB), (($tailles | Measure-Object -Maximum).Maximum / 1KB))
    Verifier ($total -lt 4MB -and (($tailles | Measure-Object -Maximum).Maximum) -lt 1MB) 'B2B : moins de 4 Mo au total, aucun fichier de plus de 1 Mo'
    $doit = @('CLAUDE.md', 'requirements.txt', 'generer.py', 'sourcing.py', 'docs\MEMOIRE-B2B.md', 'docs\INSTAGRAM-PLAN.md', 'docs\KIT-RDV-15MIN.md', 'sites\moteur\generer.py', 'sites\moteur\modeles3.py',
              'agents\liens-metiers.json', 'agents\serveur-taches.json', 'agents\serveur-b2b.ps1', 'agents\machine.py', 'agents\test_machine.py', 'agents\identite.exemple.json', 'agents\devis-fiche-modele.txt')
    $agence = 'DESIGN.md', 'assets\slider.js', 'assets\style.css', 'build.py', 'confidentialite.html', 'index.html', 'mentions-legales.html', 'merci.html'   # site de l'agence : versionné
    $doit += @($agence | ForEach-Object { "sites\agence\$_" })
    $doit += @(Get-ChildItem $AG -File | Where-Object { $_.Extension -in '.py', '.md' -or $_.Name -like '*-config.json' } | ForEach-Object { "agents\$($_.Name)" })
    $manque = @($doit | Select-Object -Unique | Where-Object { $_ -notin ($cand | ForEach-Object { $_ -replace '^B2B\\', '' }) })
    Verifier ($manque.Count -eq 0) ('versionné : agents\*.py, *.md, tests, configs par défaut, liens-metiers.json, docs, requirements, code de sites\moteur, site sites\agence' + $(if ($manque.Count) { ' — MANQUE : ' + ($manque -join ', ') }))
    $interdit = '(^|\\)(gmail-(token|client)[^\\]*|instagram-token[^\\]*|google-sheets-token[^\\]*|google-client[^\\]*|ical_url[^\\]*)$', '\.local\.json$', '-etat\.json$', '\.verrou$', '\.arret$', 'prospection-retours', 'exclus', '\.csv$', '\.log$', '^B2B\\lots\\', 'messages-a-valider',
                '^B2B\\docs\\sid\\', '^B2B\\docs\\liste-appels', '(^|\\)\.env', 'identite\.json$', 'reponses-traitees', 'liens-metiers\.avant', '__pycache__', '\.(png|jpe?g|gif|mp4|zip|pdf|ico|woff2?)$', '^B2B\\(maquettes|instagram|facebook|jarvis-ref|skills|recherche-sites|devis)\\', 'apercu-lot', 'suivi-prospects', 'prospects[^\\]*\.html$'
    $sorti = @($cand | Where-Object { $c = $_; ($interdit | Where-Object { $c -match $_ }).Count }); $sorti += @($cand | Where-Object { $_ -like 'B2B\sites\*' -and $_ -notmatch '^B2B\\sites\\moteur\\[^\\]+\.py$' -and ($_ -replace '^B2B\\sites\\agence\\', '') -notin $agence })
    Verifier ($sorti.Count -eq 0) ('rien de secret, d''état, de prospect, de journal, de média ni de site n''est versionné' + $(if ($sorti.Count) { ' — À EXAMINER : ' + (($sorti | Select-Object -First 5) -join ', ') }))
    # git check-ignore : chemins (même inexistants) qui DOIVENT être ignorés / suivis
    $ignores = 'B2B/agents/gmail-token-x@y.fr.json', 'B2B/agents/gmail-token.json', 'B2B/agents/gmail-client.json', 'B2B/agents/gmail-client-ancien.json', 'B2B/agents/instagram-token.json', 'B2B/agents/google-sheets-token.json', 'B2B/agents/google-client.json', 'B2B/agents/ical_url',
               'B2B/agents/ical_url.txt', 'B2B/agents/b2b.local.json', 'B2B/agents/rendez-vous-config.local.json', 'B2B/agents/devis-etat.json', 'B2B/agents/prospection-etat.json', 'B2B/agents/instagram-continu.verrou', 'B2B/agents/devis.arret', 'B2B/agents/prospection-retours.json',
               'B2B/agents/exclus-emails.json', 'B2B/agents/exclus-x.json', 'B2B/agents/reponses-traitees.json', 'B2B/agents/identite.json', 'B2B/agents/appels-sid-journal.log', 'B2B/agents/serveur-b2b.log', 'B2B/prospects.csv', 'B2B/suivi-prospects.csv', 'B2B/lots/lot-1.csv', 'B2B/sites/x/index.html', 'B2B/sites/moteur/photos/a.jpg',
               'B2B/sites/moteur/base.css', 'B2B/messages-a-valider.md', 'B2B/docs/sid/a.csv', 'B2B/docs/liste-appels-2026-11-04.md', 'B2B/docs/archives/liste-appels-2026-11-04.md', 'B2B/docs/archives/racine/liste-appels-2026-11-04.md', 'B2B/.env', 'B2B/devis/DEV-1.pdf', 'B2B/instagram/01-intro.png', 'B2B/maquettes/a.html', 'B2B/agents/__pycache__/a.pyc', 'B2B/docs/instagram-photo-profil.png'
    $pasIgnores = 'B2B/agents/prospection.py', 'B2B/agents/prospection.md', 'B2B/agents/liens-metiers.json', 'B2B/agents/test_devis.py', 'B2B/agents/rendez-vous-config.json', 'B2B/agents/serveur-taches.json', 'B2B/agents/serveur-b2b.ps1', 'B2B/docs/MEMOIRE-B2B.md', 'B2B/CLAUDE.md', 'B2B/sites/moteur/generer.py', 'B2B/requirements.txt', 'B2B/agents/identite.exemple.json', 'B2B/sites/agence/index.html', 'B2B/sites/agence/assets/style.css', 'B2B/sites/agence/build.py'
    $ignores += 'B2B/sites/agence/identite.json', 'B2B/sites/agence/x.local.json'
    $mauvaisI = @($ignores | Where-Object { & git -C $Root check-ignore -q -- $_ 2>$null; $LASTEXITCODE -ne 0 }); $mauvaisN = @($pasIgnores | Where-Object { & git -C $Root check-ignore -q -- $_ 2>$null; $LASTEXITCODE -eq 0 })
    Verifier ($mauvaisI.Count -eq 0) ('git check-ignore : tous les secrets, états, verrous, listes et journaux sont ignorés' + $(if ($mauvaisI.Count) { ' — PAS IGNORÉS : ' + ($mauvaisI -join ', ') }))
    Verifier ($mauvaisN.Count -eq 0) ('git check-ignore : le code et les configs par défaut ne sont pas ignorés' + $(if ($mauvaisN.Count) { ' — IGNORÉS À TORT : ' + ($mauvaisN -join ', ') }))
    # configs par défaut : aucune valeur secrète ni propre à la machine, tout éteint
    $sens = '^(ical_url|partager_avec|salon_(?!nom$).*|utilisateur_id|image_url_base|compte_google|comptes|api|.*token.*|.*secret.*|.*password.*|.*mdp.*)$'; $mal = @()
    foreach ($f in ($cand | Where-Object { $_ -like 'B2B\agents\*-config.json' })) {
        $j = Lire (Join-Path $Root $f) | ConvertFrom-Json
        foreach ($p in $j.PSObject.Properties) { if ($p.Name -match $sens -and $null -ne $p.Value -and "$($p.Value | ConvertTo-Json -Compress)" -notin '""', '[]', '{}') { $mal += "$f : $($p.Name)" } }
        # rendez-vous : true voulu dans le fichier suivi (le serveur poste sur Discord sans fichier local ; surchargeable par rendez-vous-config.local.json)
        if ($j.PSObject.Properties['envoi_automatique'] -and $j.envoi_automatique -eq $true -and $f -ne 'B2B\agents\rendez-vous-config.json') { $mal += "$f : envoi_automatique = true" }
        if (Select-String -Path (Join-Path $Root $f) -Pattern 'calendar/ical' -SimpleMatch -Quiet) { $mal += "$f : URL iCal" }
    }
    Verifier ($mal.Count -eq 0) ('configs par défaut versionnées : aucun secret, aucun identifiant de salon, aucune URL iCal, envoi_automatique = false (sauf rendez-vous, voulu)' + $(if ($mal.Count) { ' — ' + ($mal -join ' ; ') }))
    # aucun motif de clé ni de jeton dans les fichiers versionnés
    $motifs = 'rk_live_[A-Za-z0-9]{10,}', 'sk_live_[A-Za-z0-9]{10,}', 'AIza[0-9A-Za-z_-]{30,}', 'ya29\.[0-9A-Za-z_-]{20,}', '"refresh_token"\s*:\s*"[^"]{10,}', '"client_secret"\s*:\s*"[^"]{10,}', 'GOCSPX-[0-9A-Za-z_-]{10,}', 'calendar\.google\.com/calendar/ical/[^\s"]*private-[0-9a-f]{20,}',
              'EAA[A-Za-z0-9]{40,}', 'IGQ[A-Za-z0-9_-]{40,}', 'eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\.', '[A-Za-z0-9_-]{23,28}\.[A-Za-z0-9_-]{6,7}\.[A-Za-z0-9_-]{27,}', '1//0[0-9A-Za-z_-]{30,}'
    $textes = @($cand | Where-Object { $_ -match '\.(py|ps1|json|md|txt|html|js|css)$' }); $suspects = @()
    foreach ($f in $textes) { $t = Lire (Join-Path $Root $f); foreach ($m in $motifs) { if ($t -match $m) { $suspects += "$f ($($m.Substring(0, [Math]::Min(12, $m.Length)))…)" ; break } } }
    Verifier ($suspects.Count -eq 0) ('aucune clé, aucun jeton, aucune adresse iCal privée dans les fichiers de B2B à pousser' + $(if ($suspects.Count) { ' — À EXAMINER : ' + (($suspects | Select-Object -First 5) -join ', ') }))
    # valeurs RÉELLES des fichiers secrets locaux : aucune ne doit apparaître dans un fichier à pousser (contrôle sans rien afficher)
    $secrets = @(Get-ChildItem $AG -File -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '^(gmail-(token|client)|instagram-token|google-sheets-token|google-client)' -or $_.Name -like '*.local.json' })
    # (ni une adresse e-mail ni un NOM de variable d'environnement n'est un secret : ils figurent déjà dans le code ; on ne cherche que des jetons, clés et adresses iCal)
    $vals = New-Object System.Collections.Generic.HashSet[string]
    foreach ($s in $secrets) { foreach ($m in [regex]::Matches((Lire $s.FullName), ':\s*"([^"]{20,})"')) { $v = $m.Groups[1].Value; if ($v -match '^[A-Za-z0-9._~+/=%@:-]+$' -and $v -notmatch '^https://(oauth2|accounts|www)\.google' -and $v -notmatch '^[^@/]+@[^@/]+\.[a-z]{2,}$' -and $v -cnotmatch '^[A-Z][A-Z0-9_]+$') { [void]$vals.Add($v) } } }
    $envB2B = Join-Path $B2B '.env'; if (Test-Path $envB2B) { foreach ($l in (Get-Content $envB2B -Encoding UTF8)) { if ($l -match '^\s*[A-Z0-9_]+\s*=\s*(\S{12,})\s*$') { [void]$vals.Add($Matches[1]) } } }
    $fuite = 0; foreach ($v in $vals) { foreach ($f in $textes) { if (Select-String -Path (Join-Path $Root $f) -Pattern $v -SimpleMatch -Quiet -ErrorAction SilentlyContinue) { $fuite++ } } }
    Verifier ($fuite -eq 0) "aucune des $($vals.Count) valeurs secrètes locales (jetons, clients, adresses iCal, B2B\.env) n'apparaît dans un fichier à pousser"
    # clone propre : les agents s'importent sans aucun fichier local ni dossier ignoré
    $propre = Join-Path $TR 'propre'; foreach ($f in $cand) { $d = Join-Path $propre (Split-Path $f -Parent); New-Item -ItemType Directory $d -Force | Out-Null; Copy-Item (Join-Path $Root $f) (Join-Path $propre $f) }
    $py = Get-Command python -ErrorAction SilentlyContinue
    if ($py) {
        # agents du serveur = ceux de serveur-taches.json (instagram retiré le 14/11/2026), plus machine.py
        $agServ = @((Lire (Join-Path $AG 'serveur-taches.json') | ConvertFrom-Json).agents.PSObject.Properties | Where-Object { "$($_.Value.script)" -notmatch '[\\/]' } | ForEach-Object { [IO.Path]::GetFileNameWithoutExtension($_.Value.script) })
        $liste = (@($agServ) + 'machine' | ForEach-Object { "'$_'" }) -join ', '
        $code = "import importlib.util, sys; sys.dont_write_bytecode = True`nfrom pathlib import Path`nsys.path.insert(0, 'B2B/agents')`nfor n in ($liste,):`n    s = importlib.util.spec_from_file_location(n.replace('-', '_'), 'B2B/agents/' + n + '.py'); m = importlib.util.module_from_spec(s); s.loader.exec_module(m)`nprint('IMPORTS_OK')"
        $o = & { Push-Location $propre; try { & $py.Source -c $code 2>&1 | Out-String } finally { Pop-Location } }
        Verifier ($o -match 'IMPORTS_OK' -and $agServ.Count -ge 5) ("clone propre (seulement les fichiers versionnés) : les $($agServ.Count) agents du serveur et machine.py s'importent" + $(if ($o -notmatch 'IMPORTS_OK') { ' — ' + ($o.Trim() -split "`n" | Select-Object -Last 2) -join ' ' }))
    }
}

Write-Host '1 bis) Tests Python hors ligne : config locale, machine active, serveur sans navigateur, refus de bout en bout'
$pyt = Get-Command python -ErrorAction SilentlyContinue
if ($pyt) {
    $ancienEnc = $env:PYTHONIOENCODING; $env:PYTHONIOENCODING = 'utf-8'
    $o = & $pyt.Source (Join-Path $AG 'test_machine.py') 2>&1 | Out-String; $codePy = $LASTEXITCODE
    if ($null -eq $ancienEnc) { Remove-Item Env:PYTHONIOENCODING -ErrorAction SilentlyContinue } else { $env:PYTHONIOENCODING = $ancienEnc }
    Verifier ($codePy -eq 0 -and $o -match 'OK : tous les tests de la config locale') ('test_machine.py (config locale, machine active, serveur) : tous les tests passent' + $(if ($codePy -ne 0) { ' — ' + (($o -split "`n" | Select-Object -Last 3) -join ' ') }))
} else { Verifier $true '(python absent de ce PC : tests Python sautés)' }
Write-Host '2) Fichiers de la fonction : requirements, BOM, documents'
$req = Join-Path $B2B 'requirements.txt'; $rq = $(if (Test-Path $req) { Lire $req } else { '' })
foreach ($p in 'google-api-python-client', 'google-auth-oauthlib', 'google-auth-httplib2') { Verifier ($rq -match "(?m)^$([regex]::Escape($p))[>=<]") "B2B\requirements.txt : $p" }
Verifier ($rq -notmatch '(?im)^(playwright|selenium|pyppeteer|puppeteer|torch|faster-whisper|vosk)') 'B2B\requirements.txt : aucun navigateur ni paquet lourd (serveur 6 Go)'
foreach ($f in 'lib\b2b-serveur.ps1', 'B2B\agents\serveur-b2b.ps1', 'tests\b2b-serveur.ps1', 'maj-auto.ps1', 'tests\tout.ps1') { Verifier ((Get-Content (Join-Path $Root $f) -Encoding Byte -TotalCount 3) -join ',' -eq '239,187,191') "$f : UTF-8 avec BOM (PowerShell 5.1)" }
foreach ($f in 'machine.py', 'test_machine.py') { Verifier ((Get-Content (Join-Path $AG $f) -Encoding Byte -TotalCount 3) -join ',' -ne '239,187,191') "B2B\agents\$f : UTF-8 sans BOM" }
$doc = Join-Path $Root 'docs\TRANSFERT-SERVEUR.md'; $dt = $(if (Test-Path $doc) { Lire $doc } else { '' })
foreach ($k in 'gmail-token', 'gmail-client', 'instagram-token', 'google-sheets-token', 'google-client', 'identite.json', 'b2b.local.json', 'prospection-etat.json', 'exclus-emails.json', 'reponses-traitees.json', 'devis-etat.json', 'rendez-vous-etat.json', 'instagram-etat.json', 'appels-sid-etat.json', '.local.json', 'prospection-trouves.csv', 'messages-a-valider.md', 'B2B\.env') {
    Verifier ($dt -match [regex]::Escape($k)) "docs\TRANSFERT-SERVEUR.md liste : $k" }
$ordre = @('arrêter', 'copier', 'machine_active', 'agent par agent') | ForEach-Object { $dt.IndexOf($_, [StringComparison]::OrdinalIgnoreCase) }
Verifier (@($ordre | Where-Object { $_ -lt 0 }).Count -eq 0 -and (($ordre | Sort-Object) -join ',') -eq ($ordre -join ',')) 'TRANSFERT-SERVEUR.md : l''ordre est 1) arrêter les agents du PC, 2) copier, 3) machine_active, 4) activer agent par agent'
Verifier ($dt -match 'Get-ScheduledTask' -and $dt -match 'Jarvis-B2B' -and $dt -match 'double') 'TRANSFERT-SERVEUR.md : explique comment vérifier que rien ne tourne en double'

Write-Host '3) Lanceur serveur (serveur-b2b.ps1) : machine, un agent à la fois, priorité basse, aucun navigateur'
$AGT = Join-Path $TR 'B2B\agents'; New-Item -ItemType Directory $AGT | Out-Null
Copy-Item (Join-Path $AG 'serveur-b2b.ps1') $AGT
$tableReelle = Lire (Join-Path $AG 'serveur-taches.json') | ConvertFrom-Json
$nomsReels = @($tableReelle.agents.PSObject.Properties | ForEach-Object { $_.Name })
Verifier ('instagram' -notin $nomsReels -and 'surveillant' -in $nomsReels -and 'appels-liam' -in $nomsReels -and $nomsReels.Count -eq 25 -and 'sauvegarde-leads' -in $nomsReels -and 'linkedin-equipe' -in $nomsReels -and 'cerveau' -in $nomsReels -and 'linkedin' -in $nomsReels -and 'relances' -in $nomsReels -and 'interim' -in $nomsReels -and 'chiffres-serveur' -in $nomsReels -and @($nomsReels | Where-Object { $_ -like 'videos-*' -or $_ -like '*-videos' }).Count -eq 0) "serveur-taches.json : instagram retiré (décision du 14/11/2026), resume-sid/stripe-alerte/panne-alerte ajoutés (étape Argent, 15/11/2026), surveillant du harness, appels-liam et nettoyage-fichiers (15/11/2026), relances et interim (18/11/2026), chiffres-serveur, 5 superviseurs de domaine (Vidéos le 22/11/2026) la vue Jarvis et linkedin (23/11/2026, fermé jusqu'au « go linkedin »), sauvegarde-leads, linkedin-equipe et cerveau (24/11/2026), gardien (24/11/2026, dimanche 21:00, fermé jusqu''au « go gardien »), $($nomsReels.Count - $nomsVideos.Count) agents B2B + $($nomsVideos.Count) agents vidéos (16/11/2026)"
$al = $tableReelle.agents.'appels-liam'
Verifier ($al.heure -eq '07:30' -and $al.actif_le -eq '2026-11-17' -and (@($al.jours) -join ',') -eq '0,1,2,3,4' -and (@($al.commandes | ForEach-Object { $_ -join ' ' }) -join ';') -eq 'jour') 'serveur-taches.json : appels-liam à 07:30, actif le 17/11/2026, lundi à vendredi seulement'
Verifier ($tableReelle.agents.surveillant.heure -eq '19:45' -and $tableReelle.agents.surveillant.lundi -eq '07:50') 'serveur-taches.json : surveillant chaque jour à 19:45 et le lundi à 07:50'
Verifier (@($tableReelle.agents.PSObject.Properties | Where-Object { ($_.Value.commandes | ForEach-Object { $_ -join ' ' }) -match 'continu|visuels' }).Count -eq 0) 'serveur-taches.json : aucune commande « continu » ni « visuels » (Edge)'
# agent FICTIF à deux commandes, seulement dans la copie temporaire : vérifie l'ordre des commandes et l'arrêt du cycle sur échec
$tableReelle.agents | Add-Member -NotePropertyName 'deux-etapes' -NotePropertyValue ([pscustomobject]@{ script = 'deux-etapes.py'; commandes = (@('jour'), @('valider')); toutes_minutes = 5 })
# appels-liam est désactivé (clé « desactive », 18/11/2026) : la copie temporaire retire la clé pour tester les dates et jours ; agent FICTIF « en-pause » pour tester la clé elle-même
Verifier ([bool]$tableReelle.agents.'appels-liam'.desactive) 'serveur-taches.json : appels-liam désactivé (clé desactive, 18/11/2026)'
$tableReelle.agents.'appels-liam'.PSObject.Properties.Remove('desactive')
$tableReelle.agents | Add-Member -NotePropertyName 'en-pause' -NotePropertyValue ([pscustomobject]@{ script = 'en-pause.py'; commandes = (, @('jour')); heure = '07:30'; desactive = '2026-11-18 : test' })
[IO.File]::WriteAllText("$AGT\serveur-taches.json", ($tableReelle | ConvertTo-Json -Depth 6), [Text.UTF8Encoding]::new($false))
foreach ($n in @($nomsReels) + 'deux-etapes' + 'en-pause') { '# stub' | Set-Content "$AGT\$n.py" -Encoding ASCII }
$LOCAL = Join-Path $AGT 'b2b.local.json'
function Local([object]$o) { [IO.File]::WriteAllText($LOCAL, ($o | ConvertTo-Json -Depth 4), [Text.UTF8Encoding]::new($false)) }
function Lance([string]$agent, [string[]]$plus = @()) { $o = & powershell -NoProfile -ExecutionPolicy Bypass -File "$AGT\serveur-b2b.ps1" -Agent $agent -NomMachine 'PC-SERVEUR' -NomMutex ("JarvisB2BTest" + $script:mx) @plus 2>&1 | Out-String; @{ sortie = $o; code = $LASTEXITCODE } }
$script:mx = [guid]::NewGuid().ToString('N').Substring(0, 8)
$r = Lance 'rendez-vous' '-Simulation'
Verifier ($r.code -eq 3 -and $r.sortie -match 'machine_active' -and (Lire "$AGT\serveur-b2b.log") -match 'refusé') 'sans b2b.local.json : refusé (code 3), dit dans le journal, rien lancé'
Local @{ machine_active = 'PC-BUREAU'; agents_actifs = @('rendez-vous') }
$r = Lance 'rendez-vous' '-Simulation'
Verifier ($r.code -eq 3 -and $r.sortie -match 'PC-BUREAU' -and $r.sortie -match 'PC-SERVEUR') 'autre machine active : refusé, les deux noms sont indiqués'
Local @{ machine_active = 'pc-serveur'; agents_actifs = @('devis') }
$r = Lance 'rendez-vous' '-Simulation'
Verifier ($r.code -eq 4 -and $r.sortie -match 'actif') 'agent non marqué actif dans la config locale : rien lancé (code 4)'
Local @{ machine_active = 'PC-SERVEUR'; agents_actifs = @('rendez-vous', 'devis', 'appels-sid', 'deux-etapes', 'instagram') }
$r = Lance 'rendez-vous' '-Simulation'
Verifier ($r.code -eq 0 -and $r.sortie -match 'SIMULATION' -and $r.sortie -match 'rendez-vous\.py jour' -and $r.sortie -notmatch 'visuels|continu') 'machine et agent actifs : cycle « jour », ni « visuels » (Edge) ni « continu » (simulation)'
Verifier ($r.sortie -match 'BelowNormal' -and $r.sortie -match 'JARVIS_B2B_SERVEUR=1') 'priorité « sous la normale » et profil serveur annoncés'
$r = Lance 'deux-etapes' '-Simulation'
Verifier ($r.code -eq 0 -and $r.sortie -match 'deux-etapes\.py jour' -and $r.sortie -match 'deux-etapes\.py valider' -and $r.sortie.IndexOf('py jour') -lt $r.sortie.IndexOf('py valider')) 'agent à deux commandes : jour puis valider annoncés, dans l''ordre (simulation)'
$r = Lance 'appels-sid' '-Simulation'; Verifier ($r.code -eq 0 -and $r.sortie -match 'appels-sid\.py jour') 'appels-sid : commande « jour »'
# date d'activation et jours ouvrés (appels-liam : actif le 17/11/2026, lundi-vendredi) : avant la date ou le week-end, rien n'est lancé
Local @{ machine_active = 'PC-SERVEUR'; agents_actifs = @('appels-liam') }
$vus = @{}
foreach ($j in '2026-11-15', '2026-11-16', '2026-11-17', '2026-11-21') { $env:JARVIS_B2B_AUJOURDHUI = $j; $vus[$j] = Lance 'appels-liam' '-Simulation' }
Remove-Item Env:\JARVIS_B2B_AUJOURDHUI -ErrorAction SilentlyContinue
Local @{ machine_active = 'PC-SERVEUR'; agents_actifs = @('en-pause') }
$r = Lance 'en-pause' '-Simulation'; Verifier ($r.code -eq 0 -and $r.sortie -match 'désactivé' -and $r.sortie -notmatch 'en-pause\.py jour') 'agent désactivé (clé desactive) : rien lancé même s''il est dans agents_actifs (code 0)'
Verifier ($vus['2026-11-15'].code -eq 0 -and $vus['2026-11-15'].sortie -match 'pas encore actif' -and $vus['2026-11-15'].sortie -notmatch 'SIMULATION' -and $vus['2026-11-16'].sortie -match 'pas encore actif') 'appels-liam dimanche 15 et lundi 16/11 : pas encore actif, rien lancé (code 0)'
Verifier ($vus['2026-11-17'].code -eq 0 -and $vus['2026-11-17'].sortie -match 'appels-liam\.py jour') 'appels-liam mardi 17/11 : commande « jour » lancée'
Verifier ($vus['2026-11-21'].code -eq 0 -and $vus['2026-11-21'].sortie -match 'hors planning' -and $vus['2026-11-21'].sortie -notmatch 'SIMULATION') 'appels-liam samedi 21/11 : jour hors planning, rien lancé'
Local @{ machine_active = 'PC-SERVEUR'; agents_actifs = @('rendez-vous', 'devis', 'appels-sid', 'deux-etapes', 'instagram') }
$r = Lance 'inconnu' '-Simulation'; Verifier ($r.code -eq 6) 'agent inconnu : refusé (code 6)'
$r = Lance 'instagram' '-Simulation'; Verifier ($r.code -eq 6 -and $r.sortie -notmatch 'SIMULATION') 'instagram (retiré du serveur), même encore listé dans agents_actifs : refusé (code 6), rien lancé'
# python factice : vrai lancement, aucun agent
$fa = Join-Path $TR 'fauxpy.cmd'; $trace = Join-Path $TR 'trace.txt'
"@echo off`r`necho %* ; serveur=%JARVIS_B2B_SERVEUR% >> `"$trace`"`r`nif `"%FAUX_ECHEC%`"==`"1`" exit /b 1`r`nexit /b 0" | Set-Content $fa -Encoding ASCII
$r = Lance 'deux-etapes' '-Python', $fa
$t = $(if (Test-Path $trace) { @(Get-Content $trace) } else { @() })
Verifier ($r.code -eq 0 -and $t.Count -eq 2 -and $t[0] -match 'deux-etapes\.py"? jour' -and $t[1] -match 'deux-etapes\.py"? valider' -and $t[0] -match 'serveur=1') 'lancement réel (python factice) : jour puis valider, dans l''ordre, profil serveur posé'
Verifier ((Lire "$AGT\serveur-b2b.log") -match 'BelowNormal' -and (Lire "$AGT\serveur-b2b.log") -match 'terminé') 'journal du lanceur : priorité basse appliquée, fin notée'
Remove-Item $trace -Force; $env:FAUX_ECHEC = '1'
$r = Lance 'deux-etapes' '-Python', $fa; Remove-Item Env:FAUX_ECHEC
$t = @(Get-Content $trace)
Verifier ($r.code -ne 0 -and $t.Count -eq 1 -and (Lire "$AGT\serveur-b2b.log") -match 'échec') 'une commande qui échoue arrête le cycle (la suivante n''est pas lancée), noté au journal'
# un seul agent à la fois : le verrou global est tenu par un autre processus
$mu = New-Object System.Threading.Mutex($false, "Global\JarvisB2BTest$($script:mx)"); [void]$mu.WaitOne(0)
try { Remove-Item $trace -Force -ErrorAction SilentlyContinue; $r = Lance 'devis' '-Python', $fa, '-AttenteMax', '0.05'; Verifier ($r.code -eq 5 -and -not (Test-Path $trace) -and $r.sortie -match 'occup') 'un autre agent tourne : celui-ci n''est PAS lancé (code 5), il repassera au prochain cycle' }
finally { $mu.ReleaseMutex(); $mu.Dispose() }
$src = Lire (Join-Path $AG 'serveur-b2b.ps1')
Verifier ($src -match 'PriorityClass' -and $src -match 'BelowNormal' -and $src -notmatch '(?i)taskkill|Stop-Process\s+-Name|msedge|chrome|node\.exe') 'lanceur : priorité basse, aucun taskkill global, aucun navigateur'

Write-Host '4) Tâches planifiées B2B : plan, idempotence, seulement les agents actifs (rien n''est enregistré)'
. (Join-Path $Root 'lib\b2b-serveur.ps1')
$RB = Join-Path $TR 'racine'; New-Item -ItemType Directory "$RB\B2B\agents", "$RB\logs", "$RB\memoire" | Out-Null; Copy-Item (Join-Path $AG 'serveur-taches.json') "$RB\B2B\agents"; '# stub' | Set-Content "$RB\B2B\requirements.txt" -Encoding ASCII
$LB = "$RB\B2B\agents\b2b.local.json"
function LocalB([object]$o) { [IO.File]::WriteAllText($LB, ($o | ConvertTo-Json -Depth 4), [Text.UTF8Encoding]::new($false)) }
$script:NomMachineB2B = 'PC-SERVEUR'
$p = Get-B2BTaches $RB; Verifier ((-not $p.ok) -and $p.taches.Count -eq 0 -and $p.raison -match 'machine_active') 'sans config locale : aucune tâche, raison donnée'
LocalB @{ machine_active = 'PC-BUREAU'; agents_actifs = @('rendez-vous') }
$p = Get-B2BTaches $RB; Verifier ((-not $p.ok) -and $p.taches.Count -eq 0 -and $p.raison -match 'PC-BUREAU') 'autre machine : aucune tâche'
LocalB @{ machine_active = 'PC-SERVEUR' }
$p = Get-B2BTaches $RB; Verifier ($p.ok -and $p.taches.Count -eq 0) 'machine bonne mais aucun agent actif : aucune tâche (tout éteint par défaut)'
LocalB @{ machine_active = 'PC-SERVEUR'; agents_actifs = @('rendez-vous', 'appels-sid', 'inconnu', 'instagram') }
$p = Get-B2BTaches $RB; $noms = @($p.taches | ForEach-Object { $_.nom })
Verifier ($p.ok -and $noms.Count -eq 2 -and 'Jarvis-B2B-rendez-vous' -in $noms -and 'Jarvis-B2B-appels-sid' -in $noms -and $p.avertissements -match 'inconnu') 'seuls les agents actifs ont une tâche « Jarvis-B2B-<agent> » ; un nom inconnu est signalé, ignoré'
Verifier ('Jarvis-B2B-instagram' -notin $noms -and $p.avertissements -match 'instagram') 'instagram encore listé dans agents_actifs : aucune tâche (retiré de serveur-taches.json), signalé comme inconnu'
$ti = $p.taches | Where-Object { $_.agent -eq 'rendez-vous' }; $ta = $p.taches | Where-Object { $_.agent -eq 'appels-sid' }
Verifier ($ti.minutes -eq 5 -and -not $ti.heure -and $ta.heure -eq '07:30' -and -not $ta.minutes) 'rendez-vous : toutes les 5 minutes ; appels-sid : tous les jours à 07:30'
Verifier ($ti.arguments -match 'serveur-b2b\.ps1' -and $ti.arguments -match '-Agent rendez-vous' -and $ti.arguments -match 'ExecutionPolicy Bypass' -and $ti.arguments -notmatch 'visuels|continu') 'la tâche appelle le lanceur (priorité basse + verrou), jamais un agent directement'
$script:Reg = @(); $script:Sup = @(); $script:Exist = @('Jarvis-B2B-devis', 'Jarvis-B2B-instagram', 'Jarvis-MajAuto', 'Jarvis-Serveur')
$script:B2BHooks = @{ Existantes = { $script:Exist }; Enregistrer = { param($t) $script:Reg += $t.nom }; Supprimer = { param($n) $script:Sup += $n } }
$s = Sync-B2BTaches $RB
Verifier (($script:Reg | Sort-Object) -join ',' -eq 'Jarvis-B2B-appels-sid,Jarvis-B2B-rendez-vous') 'synchro : les tâches des agents actifs sont (re)créées'
Verifier ((($script:Sup | Sort-Object) -join ',') -eq 'Jarvis-B2B-devis,Jarvis-B2B-instagram') 'synchro : les tâches d''un agent désactivé (devis) et d''un agent retiré du serveur (instagram, encore listé) sont retirées ; Jarvis-MajAuto et Jarvis-Serveur ne sont JAMAIS touchées'
$premier = ($script:Reg | Sort-Object) -join ','; $script:Reg = @(); $script:Sup = @(); $script:Exist = @('Jarvis-B2B-appels-sid', 'Jarvis-B2B-rendez-vous', 'Jarvis-MajAuto')
[void](Sync-B2BTaches $RB)
Verifier ((($script:Reg | Sort-Object) -join ',') -eq $premier -and $script:Sup.Count -eq 0) 'idempotent : relancée, même résultat, rien à retirer, aucun doublon'
# -SeulementManquantes (22/11/2026) : rattrapage appelé par maj-auto toutes les 10 min quand le serveur est déjà à jour. Incident : nettoyage-fichiers était dans agents_actifs mais sans tâche
# (les tâches n'étaient créées qu'après un pull), donc « Panne : nettoyage-fichiers » chaque jour. Une tâche qui existe déjà ne doit JAMAIS être réenregistrée (son « toutes les N min » repartirait de zéro).
$script:Reg = @(); $script:Sup = @(); $script:Exist = @('Jarvis-B2B-rendez-vous', 'Jarvis-MajAuto', 'Jarvis-Serveur')
LocalB @{ machine_active = 'PC-SERVEUR'; agents_actifs = @('rendez-vous', 'appels-sid') }
$s = Sync-B2BTaches $RB -SeulementManquantes
Verifier ((($script:Reg | Sort-Object) -join ',') -eq 'Jarvis-B2B-appels-sid' -and $script:Sup.Count -eq 0) 'rattrapage : seule la tâche MANQUANTE (appels-sid) est créée, celle qui existe (rendez-vous) n''est pas réenregistrée'
Verifier ($s -match 'Jarvis-B2B-appels-sid' -and $s -notmatch 'Jarvis-B2B-rendez-vous') 'rattrapage : seule la tâche créée est dite (journal)'
$script:Reg = @(); $script:Sup = @(); $script:Exist = @('Jarvis-B2B-rendez-vous', 'Jarvis-B2B-appels-sid', 'Jarvis-MajAuto')
$s = Sync-B2BTaches $RB -SeulementManquantes
Verifier ($script:Reg.Count -eq 0 -and $script:Sup.Count -eq 0 -and -not $s) 'rattrapage : rien ne manque -> aucune tâche touchée et RIEN n''est dit (pas une ligne de journal toutes les 10 min)'
$script:Reg = @(); $script:Sup = @(); $script:Exist = @('Jarvis-B2B-rendez-vous', 'Jarvis-B2B-appels-sid', 'Jarvis-B2B-instagram', 'Jarvis-MajAuto')
$s = Sync-B2BTaches $RB -SeulementManquantes
Verifier ($script:Reg.Count -eq 0 -and (($script:Sup | Sort-Object) -join ',') -eq 'Jarvis-B2B-instagram') 'rattrapage : une tâche en trop est tout de même retirée ; Jarvis-MajAuto jamais touchée'
LocalB @{ machine_active = 'PC-BUREAU'; agents_actifs = @('rendez-vous') }; $script:Reg = @(); $script:Sup = @(); $script:Exist = @('Jarvis-B2B-rendez-vous')
[void](Sync-B2BTaches $RB -SeulementManquantes)
Verifier ($script:Reg.Count -eq 0 -and (($script:Sup | Sort-Object) -join ',') -eq 'Jarvis-B2B-rendez-vous') 'rattrapage sur une autre machine : rien n''est créé, les tâches d''ici sont retirées'
LocalB @{ machine_active = 'PC-SERVEUR'; agents_actifs = @('rendez-vous', 'appels-sid') }
LocalB @{ machine_active = 'PC-BUREAU'; agents_actifs = @('rendez-vous') }; $script:Reg = @(); $script:Sup = @()
[void](Sync-B2BTaches $RB)
Verifier ($script:Reg.Count -eq 0) 'autre machine : aucune tâche enregistrée (même si des agents sont listés)'
LocalB @{ machine_active = 'PC-SERVEUR'; agents_actifs = @('rendez-vous') }
$script:Pip = @(); $script:B2BHooks.Pip = { param($req) $script:Pip += $req; $true }
Verifier ((Install-B2BDependances $RB) -eq $true -and $script:Pip.Count -eq 1 -and $script:Pip[0] -like '*B2B\requirements.txt') 'dépendances : pip install -r B2B\requirements.txt'
$script:B2BHooks.Pip = { param($req) $false }; Verifier ((Install-B2BDependances $RB) -eq $false) 'pip qui échoue : renvoie faux, sans lever d''exception'
$script:B2BHooks.Pip = { param($req) $script:Pip += $req; $true }
Remove-Item "$RB\B2B\requirements.txt"; $script:Pip = @(); Verifier ((Install-B2BDependances $RB) -eq $true -and $script:Pip.Count -eq 0) 'pas de requirements.txt : rien à installer'
'# stub' | Set-Content "$RB\B2B\requirements.txt" -Encoding ASCII
$reel = Lire (Join-Path $Root 'lib\b2b-serveur.ps1')
Verifier ($reel -match 'JARVIS_TEST' -and $reel -match 'Register-ScheduledTask' -and $reel -match 'Jarvis-B2B-') 'lib : tâches réelles seulement hors mode test, nom « Jarvis-B2B-<agent> »'
$env:JARVIS_B2B_SIMULATION = '1'; $script:B2BHooks = $null
$o = Update-B2BServeur $RB; Verifier ($o -match 'simulation|test') 'Update-B2BServeur en mode test : ne touche à aucune vraie tâche (simulation)'
Remove-Item Env:JARVIS_B2B_SIMULATION

Write-Host '5) maj-auto.ps1 : l''étape B2B (dépôts git temporaires, aucun réseau)'
$maj = Join-Path $Root 'maj-auto.ps1'; $mc = Lire $maj
Verifier ($mc -match 'b2b-serveur\.ps1' -and $mc -match 'Update-B2BServeur') 'maj-auto.ps1 charge lib\b2b-serveur.ps1 et appelle Update-B2BServeur'
$iTests = $mc.IndexOf('tests verts : version'); $iB2B = $mc.IndexOf('Update-B2BServeur ', $mc.IndexOf('function ') + 1); $iPull = $mc.IndexOf('pull --ff-only origin')
Verifier ($iB2B -gt $iPull -and $iB2B -gt 0) 'l''étape B2B vient APRÈS un pull réussi'
Verifier ($mc -match 'Sync-B2BTaches \$Racine -SeulementManquantes' -and $mc -match "if \(\`$ancien -eq \`$nouveau\) \{ Say 'à jour'; Reset-AlerteSilence; Sync-TachesManquantesB2B") 'maj-auto.ps1 : serveur déjà à jour -> les tâches B2B MANQUANTES sont tout de même créées (22/11/2026)'
if (-not $aGit) { Verifier $true '(git absent : scénarios sautés)' } else {
    $env:GIT_AUTHOR_NAME = 'test'; $env:GIT_AUTHOR_EMAIL = 't@t.t'; $env:GIT_COMMITTER_NAME = 'test'; $env:GIT_COMMITTER_EMAIL = 't@t.t'
    $ErrorActionPreference = 'Continue'
    $g = { & git -c init.defaultBranch=main -c core.autocrlf=false @args 2>$null | Out-Null }
    $O = Join-Path $TR 'origin.git'; $D = Join-Path $TR 'dev'; $S = Join-Path $TR 'serveur'
    & $g init --bare -q $O; & $g clone -q $O $D; & git -C $D checkout -q -b main 2>$null
    New-Item -ItemType Directory "$D\lib", "$D\tests", "$D\B2B\agents" | Out-Null
    foreach ($f in 'lib\journal.ps1', 'lib\env-chiffre.ps1', 'lib\b2b-serveur.ps1') { Copy-Item (Join-Path $Root $f) "$D\$f" }; Copy-Item $maj "$D\maj-auto.ps1"; Copy-Item (Join-Path $AG 'serveur-taches.json') "$D\B2B\agents"
    "[Console]::Error.WriteLine('stub arreter'); exit 0" | Set-Content "$D\arreter.ps1" -Encoding ASCII; "Write-Host '  OK  test factice'; exit 0" | Set-Content "$D\tests\tout.ps1" -Encoding ASCII
    ".env`n.env.bak`nmemoire/`nlogs/`n*.local.json`n" | Set-Content "$D\.gitignore" -Encoding ASCII; '1' | Set-Content "$D\VERSION.txt" -Encoding ASCII; '# req' | Set-Content "$D\B2B\requirements.txt" -Encoding ASCII
    & git -C $D add -A 2>$null; & git -C $D -c user.name=t -c user.email=t@t.t commit -q -m v1 2>$null; & git -C $D push -q origin main 2>$null; & git -C $O symbolic-ref HEAD refs/heads/main 2>$null
    & $g clone -q -b main $O $S; New-Item -ItemType Directory "$S\memoire" -Force | Out-Null
    $jt = $env:JARVIS_TEST; Remove-Item Env:JARVIS_TEST, Env:JARVIS_CONFIG -ErrorAction SilentlyContinue
    $env:JARVIS_B2B_SIMULATION = '1'; $env:JARVIS_B2B_MACHINE_TEST = 'PC-SERVEUR'      # (aucune vraie tâche : plan seulement ; nom de machine imposé)
    function Maj([string[]]$plus = @()) { $o = & powershell -NoProfile -ExecutionPolicy Bypass -File "$S\maj-auto.ps1" -Racine $S -SansArret -SansRelance -FichierAlerte "$TR\alerte.txt" @plus 2>&1 | Out-String; @{ sortie = $o; code = $LASTEXITCODE } }
    function Pousser([string]$version, [string]$tests = "Write-Host '  OK  test factice'; exit 0") { $version | Set-Content "$D\VERSION.txt" -Encoding ASCII; $tests | Set-Content "$D\tests\tout.ps1" -Encoding ASCII; & git -C $D add -A 2>$null; & git -C $D -c user.name=t -c user.email=t@t.t commit -q -m "v$version" 2>$null; & git -C $D push -q origin main 2>$null }
    function JournalS { $f = "$S\logs\journal-$(Get-Date -Format 'yyyy-MM-dd').md"; if (Test-Path $f) { Get-Content $f -Raw -Encoding UTF8 } else { '' } }
    # a) pas de config locale B2B : mise à jour normale, étape B2B muette
    Pousser '2'; $r = Maj
    Verifier ($r.code -eq 0 -and $r.sortie -match 'tests verts' -and $r.sortie -notmatch 'Jarvis-B2B' -and (JournalS) -notmatch 'B2B : tâche') 'a) serveur sans config B2B locale : mise à jour normale, aucune tâche B2B'
    # b) config locale du serveur : rendez-vous actif -> sa tâche est (re)créée après les tests verts
    [IO.File]::WriteAllText("$S\B2B\agents\b2b.local.json", '{ "machine_active": "PC-SERVEUR", "agents_actifs": ["rendez-vous"] }', [Text.UTF8Encoding]::new($false))
    Pousser '3'; $r = Maj
    Verifier ($r.code -eq 0 -and $r.sortie -match 'tests verts' -and (JournalS) -match 'Jarvis-B2B-rendez-vous' -and (JournalS) -notmatch 'Jarvis-B2B-devis') 'b) agent actif dans la config locale : sa tâche est recréée après le pull et les tests verts, et lui seul'
    Verifier ((& git -C $S status --porcelain --untracked-files=no).Count -eq 0) 'b) la config locale ne rend pas l''arbre git « modifié » (la mise à jour suivante n''est pas bloquée)'
    # c) tests rouges : aucune tâche touchée
    $avant = (JournalS).Length; Pousser '4' "Write-Host '  ECHEC factice'; exit 1"; $r = Maj
    Verifier ($r.code -eq 5 -and (JournalS).Substring($avant) -notmatch 'B2B : tâche') 'c) tests rouges : retour arrière, aucune tâche B2B créée ou changée'
    Remove-Item Env:JARVIS_B2B_SIMULATION, Env:JARVIS_B2B_MACHINE_TEST -ErrorAction SilentlyContinue; $env:JARVIS_TEST = $jt
}

Write-Host '6) tests\tout.ps1 : les suites B2B font partie de la suite complète lancée par maj-auto (rien n''est désactivé)'
$tt = Lire (Join-Path $Root 'tests\tout.ps1')
Verifier ($tt -match 'b2b-serveur\.ps1' -and $tt -match 'rendez-vous\.ps1' -and $tt -match 'appels-sid\.ps1' -and $tt -match 'prospection\.ps1') 'tout.ps1 contient b2b-serveur.ps1 et les suites des agents B2B'
Verifier ($tt -notmatch '\$Rapide -and' -and $mc -match 'ScriptTests = ''tests\\tout\.ps1''') 'maj-auto.ps1 lance toujours tests\tout.ps1 en entier : aucune suite écartée (les suites B2B pèsent environ 5 % de la durée totale)'
} finally {
    if ($env:JARVIS_B2B_SIMULATION) { Remove-Item Env:JARVIS_B2B_SIMULATION -ErrorAction SilentlyContinue }
    Remove-Item Env:JARVIS_B2B_MACHINE_TEST -ErrorAction SilentlyContinue
    if ($mu) { try { $mu.Dispose() } catch { } }
    Remove-Item $TR -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item (Join-Path $env:TEMP 'jarvis-test-memoire') -Recurse -Force -ErrorAction SilentlyContinue
}
Verifier ((Hash (Join-Path $Root 'config.json')) -eq $avantConfig) 'config.json inchangé par ce test'
if ($echecs) { Write-Host "ÉCHEC : $echecs vérification(s) en échec." -ForegroundColor Red; exit 1 }
Write-Host 'OK : tests B2B serveur réussis.'; exit 0
