# Test SILENCIEUX de la recherche d'emploi « conducteur de train » (tâche emploi\TACHE-EMPLOI-CONDUCTEUR.md) : zones (Paris / Rouen, Caen / Le Havre, Lens, Le Mans en dernier recours, Lille écartée), Suisse romande en français seulement, offres en allemand écartées, tramway écarté, employeurs, bac+2 / 21 ans « à vérifier », choix du CV, lettre courte, carte « brouillon prêt », relance J+7, résumé quotidien.
# Aucun réseau, aucun Discord, aucun Gmail, aucun processus lancé. Rien n'est envoyé. Code de sortie 0 = réussi.
$ErrorActionPreference = 'Stop'
$env:JARVIS_TEST = '1'
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $Root 'lib\journal.ps1')
$TR = Join-Path $env:TEMP ('jarvis-test-' + [guid]::NewGuid().ToString('N').Substring(0, 8)); New-Item -ItemType Directory $TR, "$TR\memoire", "$TR\logs" | Out-Null; $script:JarvisRoot = $TR
'# To-do' | Set-Content "$TR\memoire\todo.md" -Encoding UTF8; '# N' | Set-Content "$TR\memoire\notes.md" -Encoding UTF8; '# R' | Set-Content "$TR\memoire\resume.md" -Encoding UTF8
$Config = Get-Content $(if ($env:JARVIS_CONFIG -and (Test-Path $env:JARVIS_CONFIG)) { $env:JARVIS_CONFIG } else { Join-Path $Root 'config.json' }) -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($l in 'voix', 'business', 'permissions', 'actions', 'coffre', 'entrees', 'ecrans', 'tableau', 'visage', 'sons', 'raccourcis', 'cerveau', 'cerveau-local', 'veille', 'memoire', 'rapide', 'discretion', 'modejeu', 'competences', 'marche', 'priorite', 'comprehension', 'routeur', 'pc', 'bureau', 'salle-marche', 'matin', 'discord', 'veille-train', 'veille-mail', 'candidatures', 'cv-candidature') { . (Join-Path $Root "lib\$l.ps1") }
$script:JarvisRoot = $TR; $script:PolitesseFixe = $true
$echecs = 0
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }
function Fixer([string]$cle, $val) { if ($Config.PSObject.Properties[$cle]) { $Config.$cle = $val } else { $Config | Add-Member -NotePropertyName $cle -NotePropertyValue $val } }
function Journal { $f = Join-Path $TR ('logs\journal-{0}.md' -f (Get-Date -Format 'yyyy-MM-dd')); if (Test-Path $f) { Get-Content $f -Raw -Encoding UTF8 } else { '' } }
$hashConfig = (Get-FileHash (Join-Path $Root 'config.json')).Hash

$script:TrainPauseSec = 0; $script:Cartes = @(); $script:CandCartes = @(); $script:Routes = @()
$script:TrainHttpStub = { param($url, $m, $corps, $h) foreach ($r in $script:Routes) { if ($url -match $r.re) { return @{ code = $r.code; texte = $r.texte } } }; @{ code = 404; texte = 'introuvable' } }
$script:TrainTraductionStub = { param($t) '' }
$script:TrainNotifStub = { param($salon, $embed) $script:Cartes += @{ salon = $salon; e = $embed }; $true }
$script:CandNotifStub = $null
function Route([string]$re, [int]$code, [string]$texte) { $script:Routes = @(@{ re = $re; code = $code; texte = $texte }) + @($script:Routes) }

Write-Host '1. Zones de France par priorité'
$Fm = { param($lieu, $titre) Get-TrainFiltreMail $lieu $titre }
foreach ($z in @(@('Rouen', 1), @('76 - ROUEN', 1), @('Sotteville-lès-Rouen', 1), @('Paris', 1), @('75 - PARIS 08', 1), @('93 - SAINT-DENIS', 1), @('Gare du Nord, Paris', 1), @('Caen', 2), @('14 - CAEN', 2), @('Le Havre', 2), @('76 - LE HAVRE', 2), @('Lens', 3), @('62 - LENS', 3), @('Le Mans', 4), @('72 - LE MANS', 4))) {
    $f = & $Fm $z[0] 'Conducteur de train débutant'; Verifier ($f.garde -and $f.zone -eq $z[1]) "« $($z[0]) » : gardée, priorité $($z[1])"
}
foreach ($l in 'Lille', '59 - LILLE', 'Marseille', 'Lyon', 'Dieppe', 'Strasbourg', '31 - TOULOUSE') { $f = & $Fm $l 'Conducteur de train'; Verifier ($f.garde -and $f.zone -eq 5) "« $l » : hors zone France, gardée avec le tag (zone 5)" }
$f = & $Fm 'Lille' 'Lokführer:in'; Verifier (-not $f.garde -and $f.raison -eq 'langue') 'Lille, titre allemand : écartée (langue)'
Write-Host '1b. Belgique francophone, Luxembourg, Flandre'
foreach ($l in 'Bruxelles', 'Liège', 'Namur', 'Charleroi', 'Mons', 'Wallonie', 'Luxembourg', 'Esch-sur-Alzette') { $f = & $Fm $l 'Conducteur de train'; Verifier ($f.garde -and $f.zone -eq 6) "« $l » : Belgique francophone / Luxembourg, gardée (zone 6)" }
foreach ($l in 'Antwerpen', 'Gent', 'Hasselt', 'Brugge', 'Berlin') { $f = & $Fm $l 'Conducteur de train'; Verifier (-not $f.garde -and $f.raison -eq 'lieu') "« $l » : Flandre / Allemagne, écartée (lieu)" }
$f = & $Fm 'Bruxelles' 'Treinbestuurder voor NMBS'; Verifier (-not $f.garde -and $f.raison -eq 'langue') 'Bruxelles, titre néerlandais : écartée (langue)'
foreach ($e in 'SNCB', 'NMBS', 'Infrabel', 'CFL') { Verifier (Test-TrainEmployeurOk $e) "employeur ajouté : « $e » accepté" }
Verifier ((Get-TrainZoneLibelle '5') -match 'Hors zone' -and (Get-TrainZoneLibelle '6') -match 'Belgique') 'libellés de zone : hors zone, Belgique / Luxembourg'
Verifier ((Get-TrainZoneLibelle '4') -match 'Dernier recours' -and (Get-TrainZoneLibelle '1') -match 'Île-de-France / Rouen') 'libellés de zone : Le Mans = dernier recours'

Write-Host '2. Suisse : romande et en français seulement, allemand écarté'
foreach ($l in 'Lausanne', 'Genève', 'Neuchâtel', 'Sion', 'Delémont', 'Fribourg', 'Biel/Bienne') { $f = Get-TrainFiltreSuisse $l 'Conducteur de train'; Verifier ($f.garde) "Suisse romande, titre français : $l gardée" }
foreach ($l in 'Basel', 'Bern', 'Zürich', 'Olten', 'Aarau') { $f = Get-TrainFiltreSuisse $l 'Conducteur de train'; Verifier (-not $f.garde -and $f.raison -eq 'lieu') "$l : écartée (hors Suisse romande)" }
foreach ($l in 'Lausanne', 'Fribourg') { $f = Get-TrainFiltreSuisse $l 'Lokführer:in Kat. A40'; Verifier (-not $f.garde -and $f.raison -eq 'langue') "$l, titre allemand : écartée (langue)" }
$f = & $Fm 'Rouen' 'Quereinstieg Lokführer:in'; Verifier (-not $f.garde -and $f.raison -eq 'langue') 'titre allemand à Rouen : écartée (langue) aussi'

Write-Host '3. Tramway, employeurs, expérience'
Verifier ((Test-TrainTram 'Conducteur de tramway (H/F)') -and -not (Test-TrainAnnonce 'Conducteur de tramway (H/F)') -and -not (Test-TrainTram 'Conducteur de train (H/F)') -and (Test-TrainAnnonce 'Conducteur de train (H/F)')) 'tramway : reconnu et écarté ; train : gardé'
Verifier ((Get-MailMetier 'Conducteur de tramway - Rouen') -eq 'tram' -and (Get-MailMetier 'Conducteur de train - Rouen') -eq 'garde') 'e-mail : tramway classé à part'
foreach ($e in 'SNCF Voyageurs', 'Transilien', 'TER Normandie', 'RATP', 'Keolis', 'Transdev', 'Rail Logistics Europe', 'Fret SNCF', 'Europorte', 'Captrain France', 'Lineas', 'Eurocargo Rail', 'Régiorail', 'CFF / SBB', '', 'non précisé', 'Indeed (alerte e-mail)') { Verifier (Test-TrainEmployeurOk $e) "employeur accepté (ou inconnu, gardé) : « $e »" }
foreach ($e in 'Randstad', 'BLS', 'Deutsche Bahn', 'Trenitalia') { Verifier (-not (Test-TrainEmployeurOk $e)) "employeur connu hors liste : « $e » écarté" }

Write-Host '4. Critères à vérifier (jamais d''écart silencieux)'
Verifier ((Get-TrainCritereVerifier 'Niveau Bac+2 exigé (BTS, DUT)') -match 'Bac\+2') 'bac+2 exigé : à vérifier'
Verifier ((Get-TrainCritereVerifier 'Âge minimum : 21 ans') -match '21 ans' -and (Get-TrainCritereVerifier 'avoir au moins 21 ans') -match '21 ans') '21 ans minimum : à vérifier'
Verifier (-not (Get-TrainCritereVerifier 'Niveau bac général, débutant accepté, permis B') -and -not (Get-TrainCritereVerifier 'Vous avez 18 ans ou plus')) 'bac général, 18 ans : rien à vérifier'
$script:TrainEcart = @{ lieu = 0; langue = 0 }; $script:MailEcartMetier = 0; $script:MailTrace = New-Object Collections.ArrayList
$html = '<a href="https://ex.invalid/1">Conducteur de train débutant (H/F)</a> <p>Rouen. Niveau Bac+2 exigé.</p> <a href="https://ex.invalid/2">Conducteur de tramway (H/F)</a> <p>Rouen</p> <a href="https://ex.invalid/3">Lokführer:in</a> <p>Paris</p> <a href="https://ex.invalid/4">Conducteur de train (H/F)</a> <p>Lille</p> <a href="https://ex.invalid/5">Conducteur de train (H/F)</a> <p>Le Mans</p>'
$an = @(Get-MailAnnonces $html 'sncf.fr' '2026-10-21')
Verifier ($an.Count -eq 3 -and $an[0].lieu -eq 'Rouen' -and $an[0].verifier -match 'Bac\+2' -and $an[0].zone -eq '1' -and $an[1].lieu -eq 'Lille' -and $an[1].zone -eq '5' -and $an[2].lieu -eq 'Le Mans' -and $an[2].zone -eq '4') "e-mail : Rouen (bac+2 à vérifier), Lille (hors zone) et Le Mans (dernier recours) gardées sur 5 : $($an.Count)"
Verifier ($script:TrainEcart.tram -eq 1 -and $script:TrainEcart.langue -eq 1 -and $script:TrainEcart.lieu -eq 0) 'écarts comptés : tramway 1, langue (allemand) 1, lieu 0 (Lille n''est plus écartée)'
Verifier ((@($script:MailTrace | Where-Object { $_.raison -like 'langue*' }).Count -eq 1) -and (@($script:MailTrace | Where-Object { $_.raison -like 'tramway*' }).Count -eq 1)) 'trace du test e-mail : raisons « langue » et « tramway » visibles'
$em = New-EmbedTrainAnnonce $an[0]
Verifier ($em.couleur -eq $script:CouleurOrange -and (@($em.champs | Where-Object { $_.nom -eq 'Critère à vérifier' -and $_.valeur -match 'Bac\+2' }).Count -eq 1) -and (@($em.champs | Where-Object { $_.nom -eq 'Zone' -and $_.valeur -match 'Priorité 1' }).Count -eq 1)) 'carte : orange, champs « Critère à vérifier » et « Zone »'
$emL = New-EmbedTrainAnnonce $an[1]
Verifier ($emL.couleur -eq $script:CouleurGrise -and (@($emL.champs | Where-Object { $_.nom -eq 'Zone' -and $_.valeur -match 'Hors zone' }).Count -eq 1)) 'carte Lille : grise, tag « Hors zone (France) »'
$em4 = New-EmbedTrainAnnonce $an[2]
Verifier ($em4.couleur -eq $script:CouleurOrange -and $em4.description -match 'Dernier recours' -and (@($em4.champs | Where-Object { $_.nom -eq 'Zone' -and $_.valeur -match 'Dernier recours' }).Count -eq 1)) 'carte Le Mans : marquée « dernier recours »'

Write-Host '5. Choix du CV'
$c = Get-CvChoix @{ employeur = 'SNCF Voyageurs'; titre = 'Conducteur de train' }; Verifier ($c.cle -eq 'voyageurs' -and $c.existe -and -not $c.note) 'SNCF Voyageurs -> CV voyageurs (fichier présent)'
Verifier ((Get-CvChoix @{ employeur = 'Transilien'; titre = 'Conducteur' }).cle -eq 'voyageurs' -and (Get-CvChoix @{ employeur = 'TER Normandie'; titre = 'Conducteur' }).cle -eq 'voyageurs') 'Transilien, TER -> voyageurs'
foreach ($e in 'RATP', 'Keolis', 'Transdev') { $c = Get-CvChoix @{ employeur = $e; titre = 'Conducteur de métro' }; Verifier ($c.cle -eq 'ratp-keolis' -and $c.existe) "$e -> CV ratp-keolis" }
foreach ($e in 'Captrain France', 'Fret SNCF', 'Europorte', 'Lineas', 'Rail Logistics Europe', 'Eurocargo Rail', 'Régiorail') { $c = Get-CvChoix @{ employeur = $e; titre = 'Conducteur de train' }; Verifier ($c.cle -eq 'fret' -and $c.existe) "$e -> CV fret" }
$c = Get-CvChoix @{ employeur = 'CFF / SBB'; titre = 'Conducteur de locomotive' }; Verifier ($c.cle -eq 'voyageurs' -and $c.note -match 'CFF') 'CFF / SBB -> CV voyageurs avec la note « CV CFF pas encore prêt »'

Write-Host '6. Lettre courte (modèle, aucune invention)'
$a = New-TrainAnnonce 'ft' '900' 'Conducteur de train débutant (H/F) <script>alert(1)</script>' 'SNCF Voyageurs' 'Rouen' '2026-10-21' 'https://emploi.sncf.com/offre/900'
$lt = New-CvLettre $a; $modele = (Get-Content (Join-Path $Root 'emploi\lettre-modele.md') -Raw -Encoding UTF8) -replace "`r", ''
Verifier ($lt -and $lt -match 'chez SNCF Voyageurs' -and $lt -notmatch '\{EMPLOYEUR\}' -and $lt -match 'Liam Emo' -and $lt -match '88 %' -and $lt -match 'Stickem Normandie') 'employeur inséré, vrai profil conservé (MOOC 88 %, Stickem Normandie)'
Verifier ($lt -notmatch 'script|alert' -and $lt -notmatch 'Conducteur de train débutant') 'le titre de l''annonce n''entre pas dans la lettre'
$corps = @(($lt -split "`n") | Where-Object { $_.Trim() }); Verifier (($corps.Count - 4) -le 8) "corps de 8 lignes au plus : $($corps.Count - 4)"
$memeLignes = @(($lt -split "`n") | Where-Object { $_ -and $modele -notmatch [regex]::Escape($_) -and $_ -notmatch 'SNCF Voyageurs' }); Verifier ($memeLignes.Count -eq 0) 'aucune ligne en dehors du modèle (rien d''inventé)'
$ltx = New-CvLettre (New-TrainAnnonce 'mail' 'x' 'Conducteur de train' 'Indeed (alerte e-mail)' 'Rouen' '' ''); Verifier ($ltx -match 'au sein de votre entreprise' -and $ltx -notmatch 'Indeed') 'employeur inconnu (site d''emploi) : « au sein de votre entreprise »'

Write-Host '7. Carte « brouillon prêt » : rien ne part'
$script:CandNotifStub = { param($salon, $embed, $ping) $script:CandCartes += @{ salon = $salon; e = $embed; ping = $ping }; $true }
Fixer 'candidature_brouillon' 'oui'
$a.zone = '1'; $a.verifier = 'Bac+2 (ou diplôme supérieur) demandé'
Remove-Item (Join-Path $TR 'memoire\candidatures.json') -Force -ErrorAction SilentlyContinue
$ok = Invoke-CvBrouillon $a (Get-Date '2026-10-21T10:00:00')
$cb = @($script:CandCartes)[0]
Verifier ($ok -and $script:CandCartes.Count -eq 1 -and $cb.salon -eq 'candidatures' -and -not $cb.ping) 'une carte dans le salon candidatures, sans mention'
Verifier ($cb.e.titre -eq 'Brouillon prêt · SNCF Voyageurs' -and $cb.e.couleur -eq $script:CouleurOrange) 'titre « Brouillon prêt », orange car un critère est à vérifier'
$ch = $cb.e.champs; Verifier ((@($ch | Where-Object { $_.nom -eq 'CV choisi' -and $_.valeur -match 'CV_Liam_Emo_voyageurs\.pdf' }).Count -eq 1) -and (@($ch | Where-Object { $_.nom -eq 'Annonce' -and $_.valeur -eq 'https://emploi.sncf.com/offre/900' }).Count -eq 1) -and (@($ch | Where-Object { $_.nom -eq 'Lettre' -and $_.valeur -match 'chez SNCF Voyageurs' }).Count -eq 1) -and (@($ch | Where-Object { $_.nom -eq 'Critère à vérifier' }).Count -eq 1)) 'la carte porte l''annonce, le CV choisi, la lettre et le critère à vérifier'
$u = [regex]::Match($cb.e.description, '\((https://mail\.google\.com/mail/\?view=cm[^)]+)\)').Groups[1].Value
Verifier ($u -and $u -notmatch '[?&]to=' -and ([uri]::UnescapeDataString(($u -split '&body=')[1]) -match 'chez SNCF Voyageurs') -and $cb.e.description -match 'Rien n''est envoyé') 'lien de brouillon Gmail pré-rempli avec la lettre, sans destinataire ; « rien n''est envoyé »'
foreach ($ch in $cb.e.champs) { if ($ch.valeur.Length -gt 1024) { Verifier $false "champ trop long : $($ch.nom)" } }
$etat = Get-CandEtat; $lg = @($etat.candidatures | Where-Object { $_.fil -eq 'brouillon:ft:900' })
Verifier ($lg.Count -eq 1 -and $lg[0].statut -eq 'BROUILLON' -and $lg[0].relance -eq '2026-10-28') 'suivi : ligne BROUILLON dans candidatures.json, relance au 28/10 (J+7)'
$script:CandCartes = @(); Fixer 'candidature_brouillon' 'non'
[void](Invoke-CvBrouillon (New-TrainAnnonce 'ft' '901' 'Conducteur de train' 'RATP' 'Paris' '' '') (Get-Date '2026-10-21T10:00:00'))
Verifier ($script:CandCartes.Count -eq 1 -and $script:CandCartes[0].e.description -notmatch 'mail\.google' -and (@($script:CandCartes[0].e.champs | Where-Object { $_.nom -eq 'CV choisi' -and $_.valeur -match 'ratp-keolis' }).Count -eq 1)) 'candidature_brouillon = "non" : carte sans lien Gmail (CV ratp-keolis), lettre toujours là'
Fixer 'candidature_brouillon' 'oui'
$script:CandCartes = @(); $z4 = New-TrainAnnonce 'ft' '906' 'Conducteur de train' 'SNCF' 'Le Mans' '' ''; $z4.zone = '4'
[void](Invoke-CvBrouillon $z4 (Get-Date '2026-10-21T10:00:00'))
Verifier ($script:CandCartes.Count -eq 1 -and $script:CandCartes[0].e.description -match 'Dernier recours' -and $script:CandCartes[0].e.couleur -eq $script:CouleurOrange) 'Le Mans : carte « dernier recours »'
$script:CandNotifStub = $null; $script:CandCartes = @()
Verifier (-not (Invoke-CvBrouillon $a) -and $script:CandCartes.Count -eq 0) 'tests silencieux sans bouchon : aucune carte réelle'
$script:CandNotifStub = { param($salon, $embed, $ping) $script:CandCartes += @{ salon = $salon; e = $embed; ping = $ping }; $true }
$script:TrainSansEcriture = $true; $n0 = (Get-CandEtat).candidatures.Count; [void](Invoke-CvBrouillon (New-TrainAnnonce 'ft' '950' 'Conducteur de train' 'SNCF' 'Rouen' '' '') (Get-Date))
Verifier ((Get-CandEtat).candidatures.Count -eq $n0) 'simulation (veille-mail-test) : aucune ligne écrite'; $script:TrainSansEcriture = $false

Write-Host '8. Passage complet France Travail : zones, allemand, tram, employeurs, expérience'
Fixer 'veille_train' 'oui'; $env:FRANCETRAVAIL_ID = 'PAR_test_0123'; $env:FRANCETRAVAIL_SECRET = 'S3cr3t_test'
$script:Cartes = @(); $script:CandCartes = @(); $script:TrainRobots = @{}
Remove-Item (Join-Path $TR 'memoire\veille-train.json'), (Join-Path $TR 'memoire\candidatures.json'), (Join-Path $TR 'memoire\candidatures-resume.json') -Force -ErrorAction SilentlyContinue
Route 'robots\.txt' 200 "User-agent: *`nDisallow:"; Route 'jobfilter\.results\.json' 200 '[]'; Route 'access_token' 200 '{"access_token":"AT_test_9999"}'
$offres = @(
    '{"id":"900","intitule":"Conducteur de train débutant (H/F)","entreprise":{"nom":"SNCF Voyageurs"},"lieuTravail":{"libelle":"76 - ROUEN"},"dateCreation":"2026-10-21T08:00:00Z","description":"Niveau Bac+2 souhaité.","experienceExige":"D","origineOffre":{"urlOrigine":"https://emploi.sncf.com/offre/900"}}'
    '{"id":"901","intitule":"Conducteur de train (H/F)","entreprise":{"nom":"SNCF Voyageurs"},"lieuTravail":{"libelle":"59 - LILLE"},"experienceExige":"D"}'
    '{"id":"902","intitule":"Conducteur de tramway (H/F)","entreprise":{"nom":"Transdev"},"lieuTravail":{"libelle":"75 - PARIS"},"experienceExige":"D"}'
    '{"id":"903","intitule":"Lokführer:in","entreprise":{"nom":"SNCF"},"lieuTravail":{"libelle":"75 - PARIS"},"experienceExige":"D"}'
    '{"id":"904","intitule":"Conducteur de train (H/F)","entreprise":{"nom":"Keolis"},"lieuTravail":{"libelle":"14 - CAEN"},"experienceExige":"E"}'
    '{"id":"905","intitule":"Conducteur de train (H/F)","entreprise":{"nom":"Randstad"},"lieuTravail":{"libelle":"75 - PARIS"},"experienceExige":"D"}'
    '{"id":"906","intitule":"Conducteur de train débutant","entreprise":{"nom":"SNCF"},"lieuTravail":{"libelle":"72 - LE MANS"},"experienceExige":"D","origineOffre":{"urlOrigine":"https://emploi.sncf.com/offre/906"}}'
    '{"id":"907","intitule":"Conducteur de train (H/F)","entreprise":{"nom":"Fret SNCF"},"lieuTravail":{"libelle":"62 - LENS"},"experienceExige":"D","origineOffre":{"urlOrigine":"https://emploi.sncf.com/offre/907"}}')
Route 'offres/search' 200 ('{"resultats":[' + ($offres -join ',') + ']}')
$t0 = Get-Date '2026-10-21T10:00:00'
$res = Invoke-VeilleTrain $t0
$cartesO = @($script:Cartes | Where-Object { $_.salon -eq 'jarvis' -and "$($_.e.titre)" -like 'Conducteur de train*' })
Verifier ($res.nouvelles -eq 4 -and $cartesO.Count -eq 4) "4 annonces gardées sur 8 (Rouen, Lille hors zone, Le Mans, Lens) : $($res.nouvelles) nouvelles, $($cartesO.Count) cartes"
Verifier ((Journal) -match '8 annonce\(s\) de conduite vue\(s\) : 4 gardée\(s\), 4 écartée\(s\) \(hors zone 0, allemand 1, tramway 1, autre employeur 1, expérience exigée 1\)') 'journal : 4 écartées visibles par raison (allemand, tramway, Randstad, expérience exigée) ; Lille gardée hors zone'
$r1 = @($cartesO | Where-Object { @($_.e.champs | Where-Object { $_.nom -eq 'Critère à vérifier' }).Count -eq 1 }); Verifier ($r1.Count -eq 1) 'Rouen : bac+2 lu dans l''annonce -> « Critère à vérifier »'
$resumeC = @($script:Cartes | Where-Object { "$($_.e.titre)" -match 'résumé' })
Verifier ($resumeC.Count -eq 1 -and (@($resumeC[0].e.champs | Where-Object { $_.nom -eq 'Annonces écartées' -and $_.valeur -notmatch 'hors zone' -and $_.valeur -match 'allemand 1' -and $_.valeur -match 'tramway 1' }).Count -eq 1)) 'résumé du matin : les écarts sont affichés (allemand, tramway...), plus de « hors zone »'
Verifier ($script:CandCartes.Count -eq 4 -and @($script:CandCartes | Where-Object { $_.salon -eq 'candidatures' -and $_.e.titre -like 'Brouillon prêt*' }).Count -eq 4) '4 cartes « brouillon prêt » dans #candidatures (une par annonce gardée)'
Verifier (@($script:CandCartes | Where-Object { @($_.e.champs | Where-Object { $_.nom -eq 'CV choisi' -and $_.valeur -match 'fret' }).Count -eq 1 }).Count -eq 1) 'Fret SNCF (Lens) -> CV fret'
$res2 = Invoke-VeilleTrain $t0.AddMinutes(61)
Verifier ($res2.nouvelles -eq 0 -and $script:CandCartes.Count -eq 4) 'deuxième passage : ni nouvelle carte ni nouveau brouillon (pas de doublon)'
Remove-Item Env:FRANCETRAVAIL_ID, Env:FRANCETRAVAIL_SECRET -ErrorAction SilentlyContinue

Write-Host '9. Suivi : relance à J+7 et résumé quotidien'
$script:CandCartes = @(); $tj = Get-Date '2026-10-29T09:00:00'
$s = Invoke-CvSuivi $tj
$rel = @($script:CandCartes | Where-Object { $_.e.titre -like 'Relance à envisager*' })
Verifier ($s.relances -eq 4 -and $rel.Count -eq 4 -and $rel[0].e.couleur -eq $script:CouleurOrange) '8 jours plus tard : 4 relances à envisager (une carte par candidature sans réponse)'
$sr = @($script:CandCartes | Where-Object { $_.e.titre -eq 'Candidatures · résumé du jour' })
Verifier ($s.resume -and $sr.Count -eq 1 -and $sr[0].e.champs[0].valeur -match 'BROUILLON : 4') 'résumé du jour posté une fois (4 brouillons)'
$script:CandCartes = @(); $s2 = Invoke-CvSuivi $tj.AddHours(1)
Verifier ($s2.relances -eq 0 -and -not $s2.resume -and $script:CandCartes.Count -eq 0) 'même jour : ni seconde relance ni second résumé'
$s3 = Invoke-CvSuivi $tj.AddDays(1)
Verifier ($s3.relances -eq 0 -and $s3.resume) 'lendemain : nouveau résumé, aucune relance répétée'
$ex = @{ candidatures = @([ordered]@{ fil = 'brouillon:x'; entreprise = 'SNCF Voyageurs'; date = '2026-10-21'; statut = 'BROUILLON' }, [ordered]@{ fil = 'f1'; entreprise = 'SNCF'; date = '2026-10-25'; statut = 'REFUS' }, [ordered]@{ fil = 'brouillon:y'; entreprise = 'RATP'; date = '2026-10-21'; statut = 'BROUILLON' }) }
Verifier ((Test-CvRepondu $ex $ex.candidatures[0]) -and -not (Test-CvRepondu $ex $ex.candidatures[2])) 'une candidature déjà répondue (refus SNCF) n''est pas relancée ; RATP sans réponse oui'

Write-Host '10. Sécurité du code'
$code = Get-Content (Join-Path $Root 'lib\cv-candidature.ps1') -Raw -Encoding UTF8
Verifier ($code -notmatch 'messages/send|users/me/drafts|gmail\.compose|gmail\.send|Invoke-WebRequest|Invoke-RestMethod|Send-MailMessage') 'le module n''envoie rien : ni Gmail, ni réseau (seulement la carte Discord)'
Verifier ((Get-Content (Join-Path $Root 'jarvis.ps1') -Raw -Encoding UTF8) -match 'lib\\cv-candidature\.ps1' -and (Get-Content (Join-Path $Root 'veille-train.ps1') -Raw -Encoding UTF8) -match 'lib\\cv-candidature\.ps1') 'module chargé par Jarvis et par le passage de veille'
$bytes = [IO.File]::ReadAllBytes((Join-Path $Root 'lib\cv-candidature.ps1')); Verifier ($bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) 'cv-candidature.ps1 en UTF-8 avec BOM'
Verifier ((Get-FileHash (Join-Path $Root 'config.json')).Hash -eq $hashConfig) 'config.json réel inchangé par le test'

Write-Host ''
Remove-Item $TR -Recurse -Force -ErrorAction SilentlyContinue
if ($echecs) { Write-Host "ÉCHEC : $echecs vérification(s) en échec." -ForegroundColor Red; exit 1 }
Write-Host 'TOUT EST VERT.'
