# Test SILENCIEUX de la veille « annonces-train » (lib\veille-train.ps1) : reconnaissance des annonces, sources (CFF / SBB, France Travail, SOB) avec des RÉPONSES SIMULÉES, robots.txt, base locale (une seule notification),
# cartes Discord, erreurs (une alerte par source et par jour), plafond de cartes, résumé du matin, rattrapage et planification. Aucun réseau, aucun Discord, aucun processus lancé, aucun jeton réel. Code de sortie 0 = réussi.
$ErrorActionPreference = 'Stop'
$env:JARVIS_TEST = '1'
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $Root 'lib\journal.ps1')
$TR = Join-Path $env:TEMP ('jarvis-test-' + [guid]::NewGuid().ToString('N').Substring(0, 8)); New-Item -ItemType Directory $TR, "$TR\memoire", "$TR\logs" | Out-Null; $script:JarvisRoot = $TR
'# To-do' | Set-Content "$TR\memoire\todo.md" -Encoding UTF8; '# N' | Set-Content "$TR\memoire\notes.md" -Encoding UTF8; '# R' | Set-Content "$TR\memoire\resume.md" -Encoding UTF8
$Config = Get-Content $(if ($env:JARVIS_CONFIG -and (Test-Path $env:JARVIS_CONFIG)) { $env:JARVIS_CONFIG } else { Join-Path $Root 'config.json' }) -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($l in 'voix', 'business', 'permissions', 'actions', 'coffre', 'entrees', 'ecrans', 'tableau', 'visage', 'sons', 'raccourcis', 'cerveau', 'cerveau-local', 'veille', 'memoire', 'rapide', 'discretion', 'modejeu', 'competences', 'marche', 'priorite', 'comprehension', 'routeur', 'pc', 'bureau', 'salle-marche', 'matin', 'discord', 'veille-train') { . (Join-Path $Root "lib\$l.ps1") }
$script:JarvisRoot = $TR; $script:PolitesseFixe = $true
$echecs = 0
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }
function Fixer([string]$cle, $val) { if ($Config.PSObject.Properties[$cle]) { $Config.$cle = $val } else { $Config | Add-Member -NotePropertyName $cle -NotePropertyValue $val } }
function Effacer([string]$cle) { if ($Config.PSObject.Properties[$cle]) { $Config.PSObject.Properties.Remove($cle) } }
function Journal { $f = Join-Path $TR ('logs\journal-{0}.md' -f (Get-Date -Format 'yyyy-MM-dd')); if (Test-Path $f) { Get-Content $f -Raw -Encoding UTF8 } else { '' } }
$vraie = Get-Content (Join-Path $Root 'config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$hashConfig = (Get-FileHash (Join-Path $Root 'config.json')).Hash

# ---------- Réseau et Discord simulés ----------
$script:Appels = @(); $script:Cartes = @(); $script:NotifOk = $true; $script:Routes = @()
$script:TrainPauseSec = 0
$script:TrainHttpStub = { param($url, $m, $corps, $h) $script:Appels += @{ url = $url; m = $m; h = $h; corps = $corps }; foreach ($r in $script:Routes) { if ($url -match $r.re) { return @{ code = $r.code; texte = $r.texte } } }; @{ code = 404; texte = 'introuvable' } }
$script:TrainNotifStub = { param($salon, $embed) $script:Cartes += @{ salon = $salon; e = $embed }; $script:NotifOk }
function Route([string]$re, [int]$code, [string]$texte) { $script:Routes = @(@{ re = $re; code = $code; texte = $texte }) + @($script:Routes) }
function Reset-Mondes { $script:Appels = @(); $script:Cartes = @(); $script:Routes = @(); $script:NotifOk = $true; $script:TrainRobots = @{}; Remove-Item (Join-Path $TR 'memoire\veille-train.json') -Force -ErrorAction SilentlyContinue }
function SbbJson($titres) { $i = 100; '[' + ((@($titres | ForEach-Object { $i++; '{"id":"' + $i + '","viewkey":"k' + $i + '","title":"' + $_ + '","attributes":{"100":["Zürich"]},"links":{"directlink":"https://jobs.sbb.ch/v2/offene-stellen/x/k' + $i + '"},"start_date":"2026-10-14T15:11:47Z"}' })) -join ',') + ']' }
$ROBOTS_SBB = "User-agent: *`nDisallow: /infos/`nDisallow: /content/plc/"
function Monde-Normal { Reset-Mondes; Route '/robots\.txt' 200 "User-agent: *`nDisallow:"; Route 'company\.sbb\.ch/robots' 200 $ROBOTS_SBB; Route 'jobfilter\.results\.json' 200 (SbbJson @('Lokführer:in Kat. A40', 'Technicien lignes de contact', 'Quereinstieg Lokführer:in Personenverkehr 03/2027')); Route 'sob\.ch/jobs-und-karriere/offene-stellen' 200 '<html><body><a href="/jobs-und-karriere/offene-stellen/lokfuehrer-1">Lokführer/in 80-100%</a> <a href="/impressum">Impressum</a></body></html>' }
$cartes_de = { param($salon) @($script:Cartes | Where-Object { $_.salon -eq $salon }) }

# ---------- 1. Réglage et configuration ----------
Write-Host '1. Réglage'
Verifier ($vraie.veille_train -eq 'non') 'config.json : veille_train = "non" (désactivée par défaut)'
Verifier (-not (Get-TrainConfig).actif) 'désactivée par défaut'
Fixer 'veille_train' 'oui'; Verifier ((Get-TrainConfig).actif) 'veille_train = "oui" l''active'
Fixer 'veille_train_minutes' '5'; Verifier ((Get-TrainConfig).minutes -eq 15) 'intervalle borné à 15 minutes au moins'; Effacer 'veille_train_minutes'
Verifier ((Get-TrainConfig).minutes -eq 60 -and (Get-TrainConfig).resume -eq '08:00') 'défauts : une heure, résumé à 08:00'
Fixer 'veille_train_resume_heure' '7:30'; Verifier ((Get-TrainConfig).resume -eq '07:30') 'heure du résumé réglable'; Fixer 'veille_train_resume_heure' 'n''importe quoi'; Verifier ((Get-TrainConfig).resume -eq '08:00') 'heure illisible : retour au défaut'; Effacer 'veille_train_resume_heure'
Fixer 'veille_train' 'non'

# ---------- 2. Reconnaissance des annonces ----------
Write-Host '2. Reconnaissance'
$oui = 'Conducteur de train (H/F)', 'Lokführer:in Kat. B100 Fahrleitungszugmaschine', 'Quereinstieg Lokführer:in Bauzug', 'Conducteur·trice de véhicule moteur cat. B100', 'Agent de conduite TER', 'Formation conducteur de ligne', 'Triebfahrzeugführer/in', 'Mécanicien de locomotive', 'Conducteur de métro', 'Conducteur ou conductrice de manoeuvre et lignes locales - TER', 'Conducteur / conductrice de trains lignes Transilien', 'Conducteur RER'
$non = 'Conducteur de bus (H/F)', 'Chauffeur livreur', 'Technicien lignes de contact', 'Kundenberater:in im Contact Center', 'Conducteur de travaux', 'Autobus Chauffeur'
Verifier (@($oui | Where-Object { -not (Test-TrainAnnonce $_) }).Count -eq 0) "reconnues : $($oui.Count) intitulés de conduite (français et allemand)"
Verifier (@($non | Where-Object { Test-TrainAnnonce $_ }).Count -eq 0) "ignorées : bus, travaux, contact, livreur ($($non.Count) intitulés)"
Verifier ((Get-TrainType 'Quereinstieg Lokführer:in') -eq 'Formation' -and (Get-TrainType 'Formation conducteur de ligne') -eq 'Formation' -and (Get-TrainType 'Conducteur de train') -eq 'Emploi') 'type : formation ou emploi'
$a = New-TrainAnnonce 'x' '1' 'Conducteur de train' '' '' '' 'http://pas-https.example/a'
Verifier ($a.lien -eq '' -and $a.employeur -eq 'non précisé' -and $a.lieu -eq 'non précisé') 'lien non https écarté, employeur et lieu « non précisé » plutôt que vides'

# ---------- 3. Sources ----------
Write-Host '3. Sources (réponses simulées)'
Monde-Normal
$sbb = @(Get-TrainSbb)
Verifier ($sbb.Count -eq 2 -and $sbb[0].employeur -eq 'CFF / SBB' -and $sbb[0].lieu -eq 'Zürich' -and $sbb[0].date -eq '2026-10-14' -and $sbb[0].lien -match '^https://jobs\.sbb\.ch/') 'CFF / SBB : 2 annonces de conduite sur 3, employeur, lieu, date, lien'
Verifier (@($script:Appels | Where-Object { $_.url -match 'robots\.txt' }).Count -eq 1) 'robots.txt lu avant la page'
$p = @(Get-TrainPage 'sob' 'https://www.sob.ch/jobs-und-karriere/offene-stellen' 'SOB')
Verifier ($p.Count -eq 1 -and $p[0].lien -eq 'https://www.sob.ch/jobs-und-karriere/offene-stellen/lokfuehrer-1' -and $p[0].titre -match 'Lokführer') 'SOB : seul le lien de conduite est repris, lien absolu'
Verifier ($null -eq (Get-TrainFranceTravail)) 'France Travail sans FRANCETRAVAIL_ID / SECRET : ignorée (ni erreur ni alerte)'
Remove-Item Env:FRANCETRAVAIL_ID, Env:FRANCETRAVAIL_SECRET -ErrorAction SilentlyContinue
$SECRET = 'S3cr3t-valeur-test-XYZ123'; $env:FRANCETRAVAIL_ID = 'PAR_test_0123456789abcdef'; $env:FRANCETRAVAIL_SECRET = $SECRET
Monde-Normal
Route 'access_token' 200 '{"access_token":"jeton-de-test-0000","expires_in":1499}'
Route 'offres/search' 204 ''
Route 'offres/search\?motsCles=conducteur%20de%20train&region=28' 200 '{"resultats":[{"id":"187PWLS","intitule":"Conducteur / conductrice de trains lignes Transilien (H/F)","entreprise":{"nom":"SNCF Voyageurs"},"lieuTravail":{"libelle":"78 - Yvelines"},"dateCreation":"2026-10-18T08:00:00.000Z","origineOffre":{"urlOrigine":"https://candidat.francetravail.fr/offres/recherche/detail/187PWLS"}},{"id":"999","intitule":"Chauffeur de bus","entreprise":{"nom":"X"},"lieuTravail":{"libelle":"76 - Rouen"},"dateCreation":"2026-10-18T08:00:00.000Z"}]}'
$ft = @(Get-TrainFranceTravail)
Verifier ($ft.Count -eq 1 -and $ft[0].employeur -eq 'SNCF Voyageurs' -and $ft[0].lieu -eq '78 - Yvelines' -and $ft[0].date -eq '2026-10-18') 'France Travail : annonce de conduite gardée, chauffeur de bus écarté'
$tokAppel = @($script:Appels | Where-Object { $_.url -match 'access_token' })[0]; $rech = @($script:Appels | Where-Object { $_.url -match 'offres/search' })
Verifier ($tokAppel.m -eq 'POST' -and $tokAppel.url -notmatch 'S3cr3t' -and $rech.Count -eq 12 -and (@($rech | Where-Object { $_.h.Authorization -eq 'Bearer jeton-de-test-0000' }).Count -eq 12)) 'France Travail : jeton en POST (jamais dans l''URL), 12 recherches (6 mots-clés × 2 régions), jeton en en-tête'
Verifier (@($rech | Where-Object { $_.url -match 'region=28' }).Count -eq 6 -and @($rech | Where-Object { $_.url -match 'region=11' }).Count -eq 6) 'régions : Normandie (28) et Île-de-France (11)'
Monde-Normal; Route 'access_token' 401 "refusé $SECRET"
$msg = ''; try { [void](Get-TrainFranceTravail) } catch { $msg = $_.Exception.Message }
Verifier ($msg -match 'jeton refusé' -and $msg -notmatch 'S3cr3t') 'jeton refusé : message clair, secret absent'
Verifier ((@(Get-TrainSources | ForEach-Object nom) -join '|') -eq 'CFF / SBB|France Travail') 'sources actives : CFF / SBB, France Travail (SOB, SNCF, RATP refusent les robots : non exploitées)'
function Get-TrainSources { @(@{ nom = 'CFF / SBB'; f = { Get-TrainSbb } }, @{ nom = 'France Travail'; f = { Get-TrainFranceTravail } }, @{ nom = 'Page test'; f = { Get-TrainPage 'sob' 'https://www.sob.ch/jobs-und-karriere/offene-stellen' 'SOB' } }) }      # (test : une 3e source simulée pour exercer Get-TrainPage dans les passages)
$src = Get-Content (Join-Path $Root 'lib\veille-train.ps1') -Raw -Encoding UTF8
Verifier ($src -notmatch '(?i)https?://[^\s''"]*(linkedin|indeed)') 'aucune adresse LinkedIn / Indeed dans le code'
Verifier ($src -notmatch '(?i)\bpostul|apply|candidater|Send-Mail|SendMail|Invoke-RestMethod') 'aucune candidature, aucun e-mail, aucune requête libre'

# ---------- 4. robots.txt et protections ----------
Write-Host '4. robots.txt et protections anti-robot'
Monde-Normal; Route 'company\.sbb\.ch/robots' 200 "User-agent: *`nDisallow: /content/internet/"
$msg = ''; try { [void](Get-TrainSbb) } catch { $msg = $_.Exception.Message }
Verifier ($msg -match 'robots\.txt interdit' -and @($script:Appels | Where-Object { $_.url -match 'jobfilter' }).Count -eq 0) 'chemin interdit par robots.txt : aucune requête vers la page'
Monde-Normal; Route 'company\.sbb\.ch/robots' 200 "User-agent: Googlebot`nDisallow: /`n`nUser-agent: *`nDisallow: /infos/"
Verifier (Test-TrainRobots 'https://company.sbb.ch/content/internet/x.json') 'robots.txt : seul le groupe « * » compte'
Monde-Normal; Route 'company\.sbb\.ch/robots' 200 "User-agent: *`nDisallow: /*/secret/*.json`nDisallow: /priv`$"
Verifier (-not (Test-TrainRobots 'https://company.sbb.ch/a/secret/x.json') -and (Test-TrainRobots 'https://company.sbb.ch/a/public/x.json') -and -not (Test-TrainRobots 'https://company.sbb.ch/priv') -and (Test-TrainRobots 'https://company.sbb.ch/priv2')) 'jokers (*) et fin de chemin ($) du robots.txt'
Monde-Normal; Route 'jobfilter' 403 '<html>Just a moment...</html>'
$msg = ''; try { [void](Get-TrainSbb) } catch { $msg = $_.Exception.Message }
Verifier ($msg -match 'anti-robot') 'HTTP 403 / défi anti-robot : source abandonnée, jamais contournée'
Monde-Normal; Route 'jobfilter' 200 '<html>Just a moment... captcha</html>'
$msg = ''; try { [void](Get-TrainSbb) } catch { $msg = $_.Exception.Message }
Verifier ($msg -match 'anti-robot') 'page de défi renvoyée avec un code 200 : reconnue aussi'
$script:TrainPauseSec = 1; $script:TrainDernierReq = Get-Date; $sw = [Diagnostics.Stopwatch]::StartNew(); Wait-TrainPoli; $sw.Stop(); $script:TrainPauseSec = 0
Verifier ($sw.Elapsed.TotalSeconds -ge 0.8) 'rythme poli : on attend entre deux requêtes'
Verifier ($src -match 'TrainPauseSec = 2') 'rythme réel : 2 secondes au moins entre deux requêtes'

# ---------- 5. Passages : une seule notification par annonce ----------
Write-Host '5. Base locale et cartes'
Remove-Item Env:FRANCETRAVAIL_ID, Env:FRANCETRAVAIL_SECRET -ErrorAction SilentlyContinue
Monde-Normal; Fixer 'veille_train' 'oui'
$t0 = [datetime]'2026-10-19T03:00:00'
$r = Invoke-VeilleTrain $t0
$jarvis = @(& $cartes_de 'jarvis')
Verifier ($r.nouvelles -eq 3 -and $r.envoyees -eq 3 -and $jarvis.Count -eq 3) 'premier passage : 3 annonces (2 SBB + 1 SOB), 3 cartes'
$c = $jarvis | Where-Object { $_.e.titre -match 'A40' } | Select-Object -First 1
$noms = @($c.e.champs | ForEach-Object { $_.nom })
Verifier ($c.e.couleur -eq $script:CouleurBleue -and $noms -contains 'Employeur' -and $noms -contains 'Lieu' -and $noms -contains 'Date' -and $noms -contains 'Lien' -and $noms -contains 'Type') 'carte : ton info (bleu), titre, employeur, lieu, date, lien, type'
Verifier ((@($c.e.champs | Where-Object { $_.nom -eq 'Date' })[0].valeur) -eq '14/10/2026' -and (@($c.e.champs | Where-Object { $_.nom -eq 'Lien' })[0].valeur) -match '^https://jobs\.sbb\.ch/') 'carte : date lisible (jj/mm/aaaa), lien https'
Verifier (($c.e.titre + $c.e.description + $c.e.pied) -notmatch '[☀-➿\uD83C-\uDBFF]') 'carte : aucun emoji'
$r = Invoke-VeilleTrain ($t0.AddHours(1))
Verifier ($r.nouvelles -eq 0 -and $r.envoyees -eq 0 -and @(& $cartes_de 'jarvis').Count -eq 3) 'second passage : rien de nouveau, aucune carte (une seule notification par annonce)'
$etat = Read-JsonMemoire 'veille-train.json'
Verifier (@($etat.vus).Count -eq 3 -and $etat.dernier_passage) 'base locale : 3 annonces vues, dernier passage noté (memoire\veille-train.json)'
Route 'jobfilter\.results\.json' 200 (SbbJson @('Lokführer:in Kat. A40', 'Technicien lignes de contact', 'Quereinstieg Lokführer:in Personenverkehr 03/2027', 'Conducteur de train TER'))
$script:TrainRobots = @{}; $r = Invoke-VeilleTrain ($t0.AddHours(2))
Verifier ($r.nouvelles -eq 1 -and $r.envoyees -eq 1 -and @(& $cartes_de 'jarvis').Count -eq 4) 'une nouvelle annonce apparaît : exactement une carte de plus'
Verifier (@(& $cartes_de 'systeme').Count -eq 0) 'aucune alerte quand tout va bien'

# ---------- 6. Discord indisponible : on réessaie ----------
Write-Host '6. Discord indisponible'
Monde-Normal; $script:NotifOk = $false; $r = Invoke-VeilleTrain $t0
Verifier ($r.envoyees -eq 0 -and @((Read-JsonMemoire 'veille-train.json').vus).Count -eq 0) 'carte non acceptée : l''annonce n''est PAS marquée vue'
$script:NotifOk = $true; $script:Cartes = @(); $script:TrainRobots = @{}; $r = Invoke-VeilleTrain ($t0.AddHours(1))
Verifier ($r.envoyees -eq 3) 'au passage suivant, les 3 cartes partent'

# ---------- 7. Plafond de cartes (premier passage) ----------
Write-Host '7. Plafond de cartes'
Monde-Normal; Route 'jobfilter\.results\.json' 200 (SbbJson (1..12 | ForEach-Object { "Lokführer:in Standort $_" }))
$r = Invoke-VeilleTrain $t0
$jarvis = @(& $cartes_de 'jarvis')
Verifier ($jarvis.Count -eq 9 -and @($jarvis | Where-Object { $_.e.titre -match 'autres nouvelles annonces' }).Count -eq 1) '13 annonces d''un coup : 8 cartes + 1 carte groupée, pas de rafale'
$script:Cartes = @(); $script:TrainRobots = @{}; $r = Invoke-VeilleTrain ($t0.AddHours(1))
Verifier ($r.nouvelles -eq 0 -and $script:Cartes.Count -eq 0) 'les annonces du lot groupé sont bien marquées vues'

# ---------- 8. Erreurs : une carte « attention » par source et par jour ----------
Write-Host '8. Erreurs'
Monde-Normal; Route 'jobfilter' 500 'panne'
$r = Invoke-VeilleTrain $t0
$sys = @(& $cartes_de 'systeme')
Verifier ($r.erreurs -contains 'CFF / SBB' -and $sys.Count -eq 1 -and $sys[0].e.couleur -eq $script:CouleurOrange -and $sys[0].e.titre -match 'Attention') 'source en erreur : une carte « attention » (orange)'
Verifier (@(& $cartes_de 'jarvis').Count -ge 1 -and (@($script:Cartes | Where-Object { $_.e.titre -match 'Lokf' })).Count -eq 1) 'les autres sources continuent (SOB : 1 carte)'
$script:TrainRobots = @{}; $r = Invoke-VeilleTrain ($t0.AddHours(1)); $r = Invoke-VeilleTrain ($t0.AddHours(2))
Verifier (@(& $cartes_de 'systeme').Count -eq 1) 'même source, même jour : pas de seconde alerte (pas de spam)'
$script:TrainRobots = @{}; $r = Invoke-VeilleTrain ($t0.AddDays(1))
Verifier (@(& $cartes_de 'systeme').Count -eq 2) 'le lendemain, si la panne dure : une nouvelle alerte'
Verifier ((Journal) -notmatch 'panne.*panne.*panne.*panne' -and (Journal) -match 'CFF / SBB') 'l''erreur est journalisée'

# ---------- 9. Résumé du matin et rattrapage ----------
Write-Host '9. Résumé du matin'
Monde-Normal
$r = Invoke-VeilleTrain ([datetime]'2026-10-19T07:00:00')
Verifier (-not $r.resume -and @($script:Cartes | Where-Object { $_.e.titre -match 'résumé' }).Count -eq 0) 'avant 08:00 : pas de résumé'
$script:TrainRobots = @{}; $r = Invoke-VeilleTrain ([datetime]'2026-10-19T08:30:00')
$res = @($script:Cartes | Where-Object { $_.e.titre -match 'résumé' })
Verifier ($r.resume -and $res.Count -eq 1 -and $res[0].e.description -match '3 nouvelles annonces' -and $res[0].e.champs[0].valeur -match 'Lokf') 'après 08:00 (rattrapage inclus) : un résumé avec les annonces des dernières 24 h'
$script:TrainRobots = @{}; $r = Invoke-VeilleTrain ([datetime]'2026-10-19T09:30:00')
Verifier (@($script:Cartes | Where-Object { $_.e.titre -match 'résumé' }).Count -eq 1) 'un seul résumé par jour'
$script:TrainRobots = @{}; $r = Invoke-VeilleTrain ([datetime]'2026-10-21T08:05:00')
$res = @($script:Cartes | Where-Object { $_.e.titre -match 'résumé' })
Verifier ($res.Count -eq 2 -and $res[1].e.description -match 'Aucune nouvelle annonce') 'deux jours plus tard : résumé « aucune nouvelle annonce »'

# ---------- 10. Planification dans la boucle de Jarvis ----------
Write-Host '10. Planification'
Reset-Mondes; $script:TrainProchainTour = [datetime]::MinValue; $script:TrainRunnerLance = $false
Fixer 'veille_train' 'non'; Verifier (-not (Update-VeilleTrain $t0) -and -not $script:TrainRunnerLance) 'veille_train = "non" : rien ne se lance'
Fixer 'veille_train' 'oui'; $script:TrainProchainTour = [datetime]::MinValue
Verifier ((Update-VeilleTrain $t0) -and $script:TrainRunnerLance) 'activée, jamais passée : un passage est lancé (rattrapage au démarrage)'
$script:TrainRunnerLance = $false; $script:TrainProchainTour = [datetime]::MinValue
$e = Get-TrainEtat; $e.dernier_passage = $t0.ToString('o'); $e.dernier_lancement = $t0.ToString('o'); Save-TrainEtat $e
Verifier (-not (Update-VeilleTrain $t0.AddMinutes(30)) -and -not $script:TrainRunnerLance) 'dernier passage il y a 30 minutes : pas encore'
$script:TrainProchainTour = [datetime]::MinValue
Verifier ((Update-VeilleTrain $t0.AddMinutes(61)) -and $script:TrainRunnerLance) 'dernier passage il y a plus d''une heure : nouveau passage'
$script:TrainRunnerLance = $false; $script:TrainProchainTour = [datetime]::MinValue; $script:ModeJeu = $true
Verifier (-not (Update-VeilleTrain $t0.AddMinutes(200)) -and -not $script:TrainRunnerLance) 'mode jeu : aucun passage (aucun réseau pendant le jeu)'
$script:ModeJeu = $false; $script:TrainProchainTour = [datetime]::MinValue
$e = Get-TrainEtat; $e.dernier_passage = $t0.AddHours(-5).ToString('o'); $e.dernier_lancement = $t0.AddMinutes(200).AddMinutes(-3).ToString('o'); Save-TrainEtat $e
Verifier (-not (Update-VeilleTrain $t0.AddMinutes(200)) -and -not $script:TrainRunnerLance) 'lancement il y a 3 minutes (passage planté ?) : pas de relance en boucle'
Verifier ((Get-Content (Join-Path $Root 'jarvis.ps1') -Raw -Encoding UTF8) -match 'Update-VeilleTrain' -and (Test-Path (Join-Path $Root 'veille-train.ps1'))) 'jarvis.ps1 appelle Update-VeilleTrain ; veille-train.ps1 (passage séparé) existe'
$pass = Get-Content (Join-Path $Root 'veille-train.ps1') -Raw -Encoding UTF8
Verifier ($pass -notmatch '(?i)Start-Visage|Parler|Start-Ecoute|Start-Piper|Start-Ollama' -and $src -notmatch '(?i)Parler |Start-Ecoute|Start-Piper|Start-Ollama|Start-Visage') 'compatible serveur léger : aucune voix, aucun micro, aucune fenêtre, aucun Ollama'

# ---------- 11. Secrets ----------
Write-Host '11. Secrets'
$env:FRANCETRAVAIL_ID = 'PAR_test_0123456789abcdef'; $env:FRANCETRAVAIL_SECRET = $SECRET
Monde-Normal; Route 'access_token' 401 "refusé $SECRET"; $script:Secrets = @()
$r = Invoke-VeilleTrain $t0
$tout = (Journal) + (($script:Cartes | ForEach-Object { $_.e | ConvertTo-Json -Depth 6 }) -join ' ') + (Get-Content (Join-Path $TR 'memoire\veille-train.json') -Raw -Encoding UTF8)
Verifier ($r.erreurs -contains 'France Travail' -and $tout -notmatch 'S3cr3t' -and $tout -notmatch 'PAR_test_0123') 'journal, cartes et base locale : ni identifiant ni secret France Travail'
Remove-Item Env:FRANCETRAVAIL_ID, Env:FRANCETRAVAIL_SECRET -ErrorAction SilentlyContinue
Verifier ((Get-FileHash (Join-Path $Root 'config.json')).Hash -eq $hashConfig) 'config.json réel inchangé par le test'

Write-Host ''
Remove-Item $TR -Recurse -Force -ErrorAction SilentlyContinue
if ($echecs) { Write-Host "ÉCHEC : $echecs vérification(s) en échec." -ForegroundColor Red; exit 1 }
Write-Host 'TOUT EST VERT.'

