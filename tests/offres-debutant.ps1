# Test SILENCIEUX de la veille d'offres « conducteur de train débutant » : exclusion (déjà formé / expérimenté / formateur), employeurs et lieux (Hexafret, Captrain, Lineas, MOB, TPF, SNCF Normandie / Île-de-France), pages configurables (robots.txt), carte Discord avec lien et brouillon Gmail (rien n'est envoyé).
# Aucun réseau, aucun Discord, aucun Gmail, aucun processus lancé. Code de sortie 0 = réussi.
$ErrorActionPreference = 'Stop'
$env:JARVIS_TEST = '1'
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $Root 'lib\journal.ps1')
$TR = Join-Path $env:TEMP ('jarvis-test-' + [guid]::NewGuid().ToString('N').Substring(0, 8)); New-Item -ItemType Directory $TR, "$TR\memoire", "$TR\logs" | Out-Null; $script:JarvisRoot = $TR
'# To-do' | Set-Content "$TR\memoire\todo.md" -Encoding UTF8; '# N' | Set-Content "$TR\memoire\notes.md" -Encoding UTF8; '# R' | Set-Content "$TR\memoire\resume.md" -Encoding UTF8
$Config = Get-Content $(if ($env:JARVIS_CONFIG -and (Test-Path $env:JARVIS_CONFIG)) { $env:JARVIS_CONFIG } else { Join-Path $Root 'config.json' }) -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($l in 'voix', 'business', 'permissions', 'actions', 'coffre', 'entrees', 'ecrans', 'tableau', 'visage', 'sons', 'raccourcis', 'cerveau', 'cerveau-local', 'veille', 'memoire', 'rapide', 'discretion', 'modejeu', 'competences', 'marche', 'priorite', 'comprehension', 'routeur', 'pc', 'bureau', 'salle-marche', 'matin', 'discord', 'veille-train', 'veille-mail', 'candidatures') { . (Join-Path $Root "lib\$l.ps1") }
$script:JarvisRoot = $TR; $script:PolitesseFixe = $true
$echecs = 0
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }
function Fixer([string]$cle, $val) { if ($Config.PSObject.Properties[$cle]) { $Config.$cle = $val } else { $Config | Add-Member -NotePropertyName $cle -NotePropertyValue $val } }
function Effacer([string]$cle) { if ($Config.PSObject.Properties[$cle]) { $Config.PSObject.Properties.Remove($cle) } }
function Journal { $f = Join-Path $TR ('logs\journal-{0}.md' -f (Get-Date -Format 'yyyy-MM-dd')); if (Test-Path $f) { Get-Content $f -Raw -Encoding UTF8 } else { '' } }
$vraie = Get-Content (Join-Path $Root 'config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$hashConfig = (Get-FileHash (Join-Path $Root 'config.json')).Hash

# ---------- Réseau et Discord simulés ----------
$script:TrainPauseSec = 0; $script:Appels = @(); $script:Cartes = @(); $script:Routes = @()
$script:TrainHttpStub = { param($url, $m, $corps, $h) $script:Appels += @{ url = $url; m = $m }; foreach ($r in $script:Routes) { if ($url -match $r.re) { return @{ code = $r.code; texte = $r.texte } } }; @{ code = 404; texte = 'introuvable' } }
$script:TrainTraductionStub = { param($t) '' }
$script:TrainNotifStub = { param($salon, $embed) $script:Cartes += @{ salon = $salon; e = $embed }; $true }
function Route([string]$re, [int]$code, [string]$texte) { $script:Routes = @(@{ re = $re; code = $code; texte = $texte }) + @($script:Routes) }

Write-Host '1. Exclusion : déjà formé / expérimenté / formateur'
foreach ($t in 'Conducteur de train débutant (H/F)', 'Conducteur de train - sans expérience', 'Formation conducteur de train', 'Conducteur de train H/F - Normandie') { Verifier (Test-TrainAnnonce $t) "gardée : $t" }
foreach ($t in 'Conducteur de train déjà formé', 'Conducteur de train expérimenté (H/F)', 'Conducteur de train expérimentée', 'Formateur conducteur de train', 'Formatrice conducteur de ligne', 'Conducteur de train confirmé', 'Conducteur de train avec expérience', 'Instructeur conducteur de train', 'Conducteur de train formé', 'Erfahrener Lokführer', 'Lokführer berufserfahren') { Verifier (-not (Test-TrainAnnonce $t)) "écartée : $t" }
Verifier ((Get-MailMetier 'Conducteur de train débutant - Rouen') -eq 'garde') 'e-mail : débutant gardé'
Verifier ((Get-MailMetier 'Agent de conduite expérimenté') -eq 'noire' -and (Get-MailMetier 'Formateur agent de conduite') -eq 'noire' -and (Get-MailMetier 'Conducteur de train déjà formé') -eq 'noire') 'e-mail : expérimenté / formateur / déjà formé en liste noire'

Write-Host '2. Employeurs et lieux (e-mails)'
foreach ($d in 'hexafret.com', 'captrain.fr', 'lineas.net', 'mob.ch', 'tpf.ch', 'sncf.fr') { Verifier (Test-MailExpediteur "RH <rh@$d>" "mx.google.com; dmarc=pass header.from=$d") "expéditeur authentifié accepté : $d" }
Verifier (-not (Test-MailExpediteur 'RH <rh@hexafret.com.evil.ru>' 'mx.google.com; dmarc=pass header.from=hexafret.com.evil.ru')) 'faux domaine refusé'
Verifier (-not (Test-MailExpediteur 'RH <rh@captrain.fr>' 'mx.google.com; dmarc=fail header.from=captrain.fr')) 'expéditeur non authentifié refusé'
$html = '<a href="https://ex.invalid/1">Conducteur de train débutant (H/F)</a> <p>Rouen</p> <a href="https://ex.invalid/2">Conducteur de train expérimenté</a> <p>Rouen</p> <a href="https://ex.invalid/3">Conducteur de train (H/F)</a> <p>Gare du Nord, Paris</p> <a href="https://ex.invalid/4">Conducteur de train (H/F)</a> <p>Marseille</p>'
$script:TrainEcart = @{ lieu = 0; langue = 0 }; $script:MailEcartMetier = 0
$script:MailTrace = New-Object Collections.ArrayList
$an = @(Get-MailAnnonces $html 'hexafret.com' '2026-10-21')
Verifier ($an.Count -eq 3) "3 offres gardées (Rouen débutant, Paris, Marseille hors zone avec tag : décision du 27/10) sur 4 : $($an.Count)"
Verifier ($an.Count -ge 1 -and $an[0].lieu -eq 'Rouen' -and $an[0].employeur -match 'Hexafret') 'Hexafret reconnu, lieu Rouen'
Verifier ($an.Count -ge 2 -and $an[1].lieu -match 'Paris|Gare du Nord') 'Île-de-France acceptée'
Verifier ($script:MailEcartMetier -eq 1 -and $script:TrainEcart.lieu -eq 0 -and $an.Count -ge 3 -and $an[2].lieu -match 'Marseille' -and "$($an[2].zone)") 'une écartée pour métier (expérimenté) ; Marseille n''est plus écartée : gardée hors zone, avec son tag (addendum du 27/10)'
Verifier ((Get-MailEmployeurTexte 'Captrain France - conducteur' 'x') -eq 'Captrain' -and (Get-MailEmployeurTexte 'Lineas Academy' 'x') -eq 'Lineas' -and (Get-MailEmployeurTexte 'MOB Montreux Oberland' 'x') -eq 'MOB' -and (Get-MailEmployeurTexte 'TPF Fribourg' 'x') -eq 'TPF') 'Captrain, Lineas, MOB, TPF reconnus dans le texte'

Write-Host '3. Pages d''offres configurables (robots.txt respecté)'
$page = '<html><a href="/offres/1">Conducteur de train débutant (H/F)</a> <a href="/offres/2">Conducteur de train expérimenté</a> <a href="/offres/3">Formateur conducteur de train</a> <a href="/contact">Contact</a></html>'
Verifier (@(Get-TrainPagesConfig).Count -eq 0) 'aucune page déclarée par défaut'
Fixer 'veille_offres_pages' @([pscustomobject]@{ nom = 'Captrain'; url = 'https://exemple-captrain.invalid/emploi'; employeur = 'Captrain'; lieu = 'Normandie' }, [pscustomobject]@{ nom = 'TPF'; url = 'https://exemple-tpf.invalid/emploi'; employeur = 'TPF'; lieu = 'Fribourg' }, [pscustomobject]@{ nom = 'Mauvais'; url = 'http://pas-https.invalid/'; employeur = 'X' })
Route 'exemple-captrain\.invalid/robots' 200 "User-agent: *`nDisallow:"; Route 'exemple-captrain\.invalid/emploi' 200 $page
Route 'exemple-tpf\.invalid/robots' 200 "User-agent: *`nDisallow: /*"; Route 'exemple-tpf\.invalid/emploi' 200 $page
$src = @(Get-TrainPagesConfig); Verifier ($src.Count -eq 2) 'deux pages https prises, l''adresse http refusée'
$r = @(& $src[0].f); Verifier ($r.Count -eq 1 -and $r[0].employeur -eq 'Captrain' -and $r[0].lieu -eq 'Normandie' -and $r[0].lien -eq 'https://exemple-captrain.invalid/offres/1') 'Captrain : seule l''offre débutant est gardée, lien absolu'
$ok = $false; try { [void](& $src[1].f) } catch { $ok = "$($_.Exception.Message)" -match 'robots' }; Verifier $ok 'TPF (robots.txt Disallow: /*) : page non lue, source en panne signalée'
Verifier (@(Get-TrainSources).Count -eq 4) 'les pages s''ajoutent aux sources CFF et France Travail'
Fixer 'veille_offres_pages' @()

Write-Host '4. Carte Discord et brouillon Gmail'
Fixer 'candidature_telephone' '06 68 50 64 19'
$a = New-TrainAnnonce 'ft' '42' 'Conducteur de train débutant (H/F)' 'Hexafret' 'Rouen' '2026-10-21' 'https://candidat.francetravail.fr/offres/recherche/detail/42'
$c = Get-CandBrouillonChamp $a
Verifier ($c -and $c.nom -eq 'Candidature' -and $c.valeur.Length -le 1024) 'champ « Candidature » présent, 1024 caractères au plus'
$u = [regex]::Match($c.valeur, '\((https://mail\.google\.com/mail/\?view=cm[^)]+)\)').Groups[1].Value
Verifier ($u -ne '' -and $u -notmatch '[?&]to=') 'lien de rédaction Gmail, sans destinataire'
$corps = [uri]::UnescapeDataString(($u -split '&body=')[1]); $objet = [uri]::UnescapeDataString((($u -split '&su=')[1] -split '&body=')[0])
Verifier ($objet -eq 'Candidature - Conducteur de train débutant (H/F)') "objet : $objet"
Verifier ($corps -match 'Liam Emo' -and $corps -match '06 68 50 64 19' -and $corps -match 'francetravail\.fr/offres' -and $corps -match 'Hexafret, Rouen') 'corps : nom, téléphone, lien de l''offre, employeur et lieu'
Verifier ($c.valeur -match 'joignez votre CV' -and $c.valeur -match 'Rien n''est envoyé') 'la carte rappelle de joindre le CV et que rien n''est envoyé'
$e = New-EmbedTrainAnnonce $a; Verifier (@($e.champs | Where-Object { $_.nom -eq 'Lien' }).Count -eq 1 -and @($e.champs | Where-Object { $_.nom -eq 'Candidature' }).Count -eq 1) 'carte de l''offre : lien + brouillon'
$long = New-TrainAnnonce 'ft' '43' ('Conducteur de train débutant ' + ('é' * 150)) 'Hexafret' 'Rouen' '' 'https://candidat.francetravail.fr/offres/recherche/detail/43'
$cl = Get-CandBrouillonChamp $long; Verifier ($null -eq $cl -or $cl.valeur.Length -le 1024) 'titre très long : lien raccourci ou omis, jamais plus de 1024 caractères'
$mal = New-TrainAnnonce 'ft' '44' "Conducteur`r`nde train&to=evil@x.fr" 'X' 'Rouen' '' ''
$cm = Get-CandBrouillonChamp $mal; $um = [regex]::Match($cm.valeur, '\((https://[^)]+)\)').Groups[1].Value
Verifier ($um -notmatch '[?&]to=') 'un titre piégé ne peut pas ajouter de destinataire (tout est encodé)'
Fixer 'candidature_brouillon' 'non'; Verifier ($null -eq (Get-CandBrouillonChamp $a)) 'candidature_brouillon = "non" : aucun brouillon'; Fixer 'candidature_brouillon' 'oui'
Fixer 'candidature_telephone' ''
$sans = [uri]::UnescapeDataString(((Get-CandBrouillonChamp $a).valeur -split '&body=')[1]); Verifier ($sans -notmatch 'Téléphone') 'sans téléphone configuré : la ligne est omise'
Fixer 'candidature_telephone' '06 68 50 64 19'

Write-Host '5. Passage complet : nouvelle offre = une carte avec lien + brouillon, jamais d''envoi'
Fixer 'veille_train' 'oui'; $env:FRANCETRAVAIL_ID = 'PAR_test_0123'; $env:FRANCETRAVAIL_SECRET = 'S3cr3t_test'
$script:Cartes = @(); $script:Appels = @(); $script:TrainRobots = @{}; Remove-Item (Join-Path $TR 'memoire\veille-train.json') -Force -ErrorAction SilentlyContinue
Route 'robots\.txt' 200 "User-agent: *`nDisallow:"; Route 'company\.sbb\.ch/robots' 200 "User-agent: *`nDisallow: /infos/"; Route 'jobfilter\.results\.json' 200 '[]'
Route 'access_token' 200 '{"access_token":"AT_test_9999"}'
Route 'offres/search' 200 '{"resultats":[{"id":"900","intitule":"Conducteur de train débutant (H/F)","entreprise":{"nom":"SNCF Voyageurs"},"lieuTravail":{"libelle":"76 - Rouen"},"dateCreation":"2026-10-21T08:00:00Z","origineOffre":{"urlOrigine":"https://emploi.sncf.com/offre/900"}},{"id":"901","intitule":"Conducteur de train expérimenté","entreprise":{"nom":"SNCF Voyageurs"},"lieuTravail":{"libelle":"76 - Rouen"},"origineOffre":{"urlOrigine":"https://emploi.sncf.com/offre/901"}},{"id":"902","intitule":"Formateur conducteur de train","entreprise":{"nom":"SNCF Voyageurs"},"lieuTravail":{"libelle":"75 - Paris"}}]}'
$t0 = Get-Date '2026-10-21T10:00:00'
$res = Invoke-VeilleTrain $t0
$off = @($script:Cartes | Where-Object { $_.salon -eq 'jarvis' -and "$($_.e.titre)" -like 'Conducteur de train*' })
Verifier ($res.nouvelles -eq 1 -and $off.Count -eq 1) "1 nouvelle offre sur 3 (expérimenté et formateur ignorés) -> 1 carte : $($off.Count)"
Verifier ($off.Count -eq 1 -and @($off[0].e.champs | Where-Object { $_.nom -eq 'Lien' -and $_.valeur -eq 'https://emploi.sncf.com/offre/900' }).Count -eq 1 -and @($off[0].e.champs | Where-Object { $_.nom -eq 'Candidature' }).Count -eq 1) 'la carte porte le lien SNCF et le brouillon Gmail'
$res2 = Invoke-VeilleTrain $t0.AddMinutes(61)
Verifier ($res2.nouvelles -eq 0 -and @($script:Cartes | Where-Object { $_.salon -eq 'jarvis' -and "$($_.e.titre)" -like 'Conducteur de train*' }).Count -eq 1) 'deuxième passage : aucune nouvelle carte (pas de doublon)'
Verifier (@($script:Appels | Where-Object { $_.url -match 'gmail|googleapis' }).Count -eq 0) 'aucun appel Gmail pendant la veille : seulement la lecture des offres'
Remove-Item Env:FRANCETRAVAIL_ID, Env:FRANCETRAVAIL_SECRET -ErrorAction SilentlyContinue

Write-Host '6. Sécurité du code'
$code = (Get-Content (Join-Path $Root 'lib\candidatures.ps1') -Raw -Encoding UTF8) + (Get-Content (Join-Path $Root 'lib\veille-mail.ps1') -Raw -Encoding UTF8)
Verifier ($code -notmatch 'messages/send|users/me/drafts|gmail\.compose|gmail\.send' -and $code -match 'gmail\.readonly') 'Gmail reste en lecture seule : aucun appel d''envoi ni de brouillon via l''API'
Verifier ((Get-FileHash (Join-Path $Root 'config.json')).Hash -eq $hashConfig) 'config.json réel inchangé par le test'

Write-Host ''
Remove-Item $TR -Recurse -Force -ErrorAction SilentlyContinue
if ($echecs) { Write-Host "ÉCHEC : $echecs vérification(s) en échec." -ForegroundColor Red; exit 1 }
Write-Host 'TOUT EST VERT.'
