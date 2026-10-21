# Test SILENCIEUX du suivi des RÉPONSES aux candidatures (lib\candidatures.ps1) : règles FR / DE / EN, Ollama, Claude Haiku et plafond de 10 appels par jour, passage complet, mises à jour d'un fil, simulation, câblage dans la veille e-mail, commande candidatures-test.
# Gmail, Discord, Ollama et Claude sont SIMULÉS : aucun réseau, aucun Google, aucun son, aucune fenêtre, aucun processus lancé. Code de sortie 0 = réussi.
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
function Journal { $f = Join-Path $TR ('logs\journal-{0}.md' -f (Get-Date -Format 'yyyy-MM-dd')); if (Test-Path $f) { Get-Content $f -Raw -Encoding UTF8 } else { '' } }
$vraie = Get-Content (Join-Path $Root 'config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$hashConfig = (Get-FileHash (Join-Path $Root 'config.json')).Hash
$TOK = 'AT_SECRET_TOKEN_0123456789'; $RT = 'RT_SECRET_REFRESH_0123456789'; $CID = 'cid-test-0123.apps.googleusercontent.com'; $CSEC = 'CLIENT_SECRET_VALUE_0123'
$sc = Get-Content (Join-Path $Root 'lib\candidatures.ps1') -Raw -Encoding UTF8

# ---------- Mondes simulés ----------
$script:CAppels = @(); $script:CMsgs = @{}; $script:CEmp = @(); $script:CEnv = @(); $script:CAutres = @(); $script:CCartes = @(); $script:CNotifOk = $true
$script:CollOllama = 0; $script:CollClaude = 0; $script:OllamaRep = ''; $script:ClaudeRep = ''
$script:TrainPauseSec = 0
function CMsg([string]$id, [string]$fil, [string]$from, [string]$auth, [string]$sujet, [string]$corps, [long]$t = 1792500000000, $labels = @('INBOX')) {
    ConvertTo-Json -Depth 10 @{ id = $id; threadId = $fil; labelIds = $labels; internalDate = "$t"; payload = @{ mimeType = 'text/plain'; headers = @(@{ name = 'From'; value = $from }, @{ name = 'Subject'; value = $sujet }, @{ name = 'Authentication-Results'; value = $auth }); body = @{ data = (ConvertTo-GmailBase64 $corps) } } }
}
function CAuth([string]$d) { "mx.google.com; dkim=pass header.d=$d; spf=pass smtp.mailfrom=$d; dmarc=pass (p=REJECT) header.from=$d" }
function CRef([string]$id, [string]$fil) { @{ id = $id; threadId = $fil } }
$script:TrainHttpStub = { param($url, $m, $corps, $h)
    $script:CAppels += @{ url = $url; m = $m }
    if ($url -match 'oauth2\.googleapis\.com/token') { return @{ code = 200; texte = '{"access_token":"AT_SECRET_TOKEN_0123456789","expires_in":3599}' } }
    if ($url -match 'users/me/labels$') { return @{ code = 200; texte = '{"labels":[{"id":"INBOX","name":"INBOX"},{"id":"Label_7","name":"annonces-train"}]}' } }
    if ($url -match 'users/me/messages\?labelIds') { return @{ code = 200; texte = (ConvertTo-Json -Compress @{ messages = @($script:CLabel) }) } }
    if ($url -match 'users/me/messages\?[^ ]*from%3A') { return @{ code = 200; texte = (ConvertTo-Json -Compress @{ messages = @($script:CEmp) }) } }
    if ($url -match 'users/me/messages\?[^ ]*q=in%3Asent') { return @{ code = 200; texte = (ConvertTo-Json -Compress @{ messages = @($script:CEnv) }) } }
    if ($url -match 'users/me/messages\?') { return @{ code = 200; texte = (ConvertTo-Json -Compress @{ messages = @($script:CAutres) }) } }
    if ($url -match 'users/me/messages/([A-Za-z0-9]+)\?') { if ($script:CMsgs.ContainsKey($Matches[1])) { return @{ code = 200; texte = $script:CMsgs[$Matches[1]] } } }
    @{ code = 404; texte = 'introuvable' }
}
$script:TrainNotifStub = { param($salon, $embed) $script:Cartes += @{ salon = $salon; e = $embed }; $true }
$script:CandNotifStub = { param($salon, $embed, $ping) $script:CCartes += @{ salon = $salon; e = $embed; ping = $ping }; $script:CNotifOk }
$script:CandOllamaStub = { param($d) $script:CollOllama++; $script:OllamaRep }
$script:CandClaudeStub = { param($d) $script:CollClaude++; $script:ClaudeRep }
$script:CLabel = @()
function Monde-Cand {
    $script:CAppels = @(); $script:CMsgs = @{}; $script:CEmp = @(); $script:CEnv = @(); $script:CAutres = @(); $script:CCartes = @(); $script:Cartes = @(); $script:CNotifOk = $true; $script:CLabel = @()
    $script:CollOllama = 0; $script:CollClaude = 0; $script:OllamaRep = ''; $script:ClaudeRep = ''; $script:Secrets = @(); $script:TrainOllamaHS = $false; $script:CandOllamaHS = $false; $script:CandPlafondAtteint = $false; $script:TrainSansEcriture = $false
    foreach ($f in 'candidatures.json', 'candidatures-quota.json', 'veille-mail.json', 'veille-train.json', 'gmail-jeton.dpapi') { Remove-Item (Join-Path $TR "memoire\$f") -Force -ErrorAction SilentlyContinue }
}
function Ajouter([string]$id, [string]$fil, [string]$from, [string]$dom, [string]$sujet, [string]$corps, [string]$ou = 'emp', [long]$t = 1792500000000, $auth = $null) {
    $script:CMsgs[$id] = CMsg $id $fil $from $(if ($auth) { $auth } else { CAuth $dom }) $sujet $corps $t
    if ($ou -eq 'emp') { $script:CEmp += CRef $id $fil } elseif ($ou -eq 'env') { $script:CAutres += CRef $id $fil }
}
$JSON_OLL = '{"type":"ENTRETIEN","confiance":"haute","entreprise":"CFF","poste":"Conducteur","resume":"Les CFF vous proposent un échange téléphonique pour le poste de conducteur. À faire : rappeler avant le 30/10/2026.","echeance":"30/10/2026"}'
$t0 = [datetime]'2026-10-21T10:00:00'

# ---------- 1. Règles gratuites (FR / DE / EN) ----------
Write-Host '1. Règles gratuites'
function Cl([string]$texte) { (Test-CandReponse (ConvertTo-TrainNorm $texte)).type }
$cas = @(
    @('Nous regrettons de vous informer que votre candidature n''a pas été retenue.', 'REFUS'), @('Leider müssen wir Ihnen eine Absage erteilen.', 'REFUS'), @('Wir haben uns für andere Kandidaten entschieden.', 'REFUS'),
    @('Unfortunately we will not be moving forward with your application.', 'REFUS'), @('Malheureusement, ce poste est déjà pourvu.', 'REFUS'), @('Suite à votre entretien, nous ne retiendrons pas votre candidature.', 'REFUS'),
    @('Malheureusement, il n''y a pas de classe publiée en Romandie pour le moment.', 'INFO'), @('Leider ist derzeit keine Klasse in der Romandie ausgeschrieben.', 'INFO'), @('Currently no classes are published in Romandie.', 'INFO'),
    @('Félicitations, vous êtes retenu pour le poste.', 'ACCEPTÉ'), @('Wir freuen uns, Ihnen eine Zusage zu geben.', 'ACCEPTÉ'), @('We are pleased to offer you the position of train driver.', 'ACCEPTÉ'),
    @('Nous vous invitons à un entretien le 3 novembre à 10h.', 'ENTRETIEN'), @('Einladung zum Vorstellungsgespräch am 3. November.', 'ENTRETIEN'), @('We would like to invite you to an interview on Monday.', 'ENTRETIEN'),
    @('Veuillez nous transmettre votre CV et vos certificats.', 'DOCUMENTS'), @('Bitte senden Sie uns Ihre Unterlagen.', 'DOCUMENTS'), @('Please send us your driving licence.', 'DOCUMENTS'),
    @('Nous avons bien reçu votre candidature.', 'ACCUSÉ'), @('Wir haben Ihre Bewerbung erhalten.', 'ACCUSÉ'), @('Thank you for applying to SBB.', 'ACCUSÉ'),
    @('Nous avons bien reçu votre candidature. Si votre profil correspond, nous vous inviterons à un entretien.', 'ACCUSÉ'),
    @('Nous vous invitons à un entretien. Veuillez nous transmettre vos documents avant le rendez-vous.', 'ENTRETIEN'),
    @('Bonjour, pouvez-vous me rappeler ? Cordialement.', ''), @('Si votre profil correspond, nous vous inviterons à un entretien.', ''))
$faux = @($cas | Where-Object { (Cl $_[0]) -ne $_[1] })
Verifier ($faux.Count -eq 0) "$($cas.Count) phrases FR / DE / EN classées comme attendu (refus, info, accepté, entretien, documents, accusé, ambigu)$(if ($faux.Count) { ' ; en échec : ' + (($faux | ForEach-Object { $_[0] }) -join ' | ') })"
Verifier ((Cl 'Malheureusement, félicitations') -eq '') 'règles qui se contredisent (regret + félicitations) : ambigu, donc Ollama puis Claude'
Verifier ((ConvertTo-CandType 'ACCEPTÉ') -eq 'ACCEPTÉ' -and (ConvertTo-CandType 'accepte') -eq 'ACCEPTÉ' -and (ConvertTo-CandType 'Accusé') -eq 'ACCUSÉ' -and (ConvertTo-CandType 'refus') -eq 'REFUS' -and (ConvertTo-CandType 'DELETE ALL') -eq '' -and (ConvertTo-CandType '') -eq '') 'types lus avec ou sans accents ; type inconnu refusé'

# ---------- 2. Faits tirés du mail ----------
Write-Host '2. Langue, entreprise, poste, dates'
Verifier ((Get-CandLangue (ConvertTo-TrainNorm 'Sehr geehrter Herr, vielen Dank für Ihre Bewerbung. Wir laden Sie zum Gespräch ein. Freundliche Grüsse')) -eq 'allemand' -and (Get-CandLangue (ConvertTo-TrainNorm 'Dear Sir, thank you for your application. We have received your CV. Regards')) -eq 'anglais' -and (Get-CandLangue (ConvertTo-TrainNorm 'Bonjour, nous avons bien reçu votre candidature pour le poste. Merci.')) -eq 'français') 'langue : allemand, anglais, français'
$dts = @(Get-CandDates 'Entretien le 28.10.2026 à 14h, merci de confirmer avant le 5 novembre 2026. Bis zum 24.10.2026 antworten.' $t0)
Verifier ($dts.Count -eq 3 -and $dts[0].date.ToString('dd/MM/yyyy') -eq '28/10/2026' -and -not $dts[0].echeance -and $dts[1].date.ToString('dd/MM/yyyy') -eq '05/11/2026' -and $dts[1].echeance -and $dts[2].date.ToString('dd/MM/yyyy') -eq '24/10/2026' -and $dts[2].echeance) 'dates numériques et en lettres (FR / DE) lues ; « avant le » et « bis zum » = échéance, pas la date de l''entretien'
Verifier ((Get-CandEntreprise 'hrs.sbb.ch' 'x' '') -eq 'CFF / SBB' -and (Get-CandEntreprise 'mob.ch' 'x' '') -eq 'MOB' -and (Get-CandEntreprise 'cj-bahn.ch' 'x' '') -eq 'Chemins de fer du Jura' -and (Get-CandEntreprise 'sncf.com' 'x' '') -eq 'SNCF' -and (Get-CandEntreprise 'francetravail.fr' 'x' '') -eq 'France Travail' -and (Get-CandEntreprise 'entreprise-xyz.ch' 'Entreprise XYZ <rh@entreprise-xyz.ch>' '') -eq 'Entreprise XYZ') 'entreprise : par le domaine des employeurs connus, sinon le nom affiché de l''expéditeur'
Verifier ((Get-CandPoste 'Votre candidature de Conducteur de train') -eq 'Conducteur de train' -and (Get-CandPoste 'Bewerbung als Lokführerin') -eq 'Lokführerin' -and (Get-CandPoste 'rien ici') -eq '') 'poste : conducteur de train, mécanicien de locomotive, Lokführer ; vide si inconnu'
$res = foreach ($t in $script:CandTypes) { Get-CandResumeModele @{ type = $t; entreprise = 'CFF / SBB'; poste = 'Conducteur de train'; langue = 'allemand'; echeance = '24/10/2026'; date_evenement = '28/10/2026' } }
Verifier (@($res | Where-Object { @([regex]::Matches($_, '[.!?](\s|$)')).Count -ne 2 }).Count -eq 0 -and $res.Count -eq 6 -and $res[1] -match '^Mail en allemand : ' -and $res[1] -match '28/10/2026' -and $res[1] -match 'avant le 24/10/2026') 'résumé de secours : exactement 2 phrases en français pour chacun des 6 types, mail allemand signalé, entretien et échéance cités'

# ---------- 3. Ollama puis Claude Haiku (10 appels par jour) ----------
Write-Host '3. Ollama, Claude Haiku, plafond'
Monde-Cand
$amb = 'Bonjour, pouvez-vous me rappeler ? Cordialement.'
$script:OllamaRep = $JSON_OLL; $r = Get-CandClassement 'Question' 'CFF <a@sbb.ch>' $amb 'sbb.ch' $t0
Verifier ($r.type -eq 'ENTRETIEN' -and $r.source -eq 'Ollama' -and $script:CollClaude -eq 0 -and $r.resume -match '^Les CFF vous proposent' -and $r.echeance -eq '30/10/2026') 'règles ambiguës : Ollama tranche (confiance haute), son résumé est gardé, Claude n''est pas appelé'
$script:OllamaRep = $JSON_OLL.Replace('haute', 'basse'); $script:ClaudeRep = '{"type":"REFUS","confiance":"haute","entreprise":"CFF","poste":"","resume":"Les CFF ne donnent pas suite à votre candidature. À faire : rien, aucune date limite indiquée."}'
$r = Get-CandClassement 'Question' 'CFF <a@sbb.ch>' $amb 'sbb.ch' $t0
Verifier ($r.type -eq 'REFUS' -and $r.source -eq 'Claude Haiku' -and $script:CollClaude -eq 1 -and -not $r.incertain) 'Ollama peu sûr (confiance basse) : Claude Haiku décide'
$q = Read-JsonMemoire 'candidatures-quota.json'; Verifier ("$($q.jour)" -eq (Get-Date).ToString('yyyy-MM-dd') -and [int]$q.n -eq 1) 'appels à Claude comptés par jour (memoire\candidatures-quota.json)'
$script:OllamaRep = ''; $script:CollClaude = 0
$r = Get-CandClassement 'Re' 'Banque <x@exemple.ch>' 'Votre candidature : nous avons bien reçu votre dossier. Merci.' 'exemple.ch' $t0
Verifier ($r.type -eq 'ACCUSÉ' -and $r.source -eq 'règle' -and $script:CollClaude -eq 0) 'règle claire : ni Ollama (type) ni Claude ne décident'
$script:OllamaRep = $JSON_OLL; $r = Get-CandClassement 'Re' 'x <a@sbb.ch>' 'Nous avons bien reçu votre candidature. Merci.' 'sbb.ch' $t0
Verifier ($r.type -eq 'ACCUSÉ' -and $r.source -eq 'règle' -and $r.resume -match '^Les CFF vous proposent') 'Ollama ne change jamais un type décidé par les règles (il ne fournit que le résumé)'
Verifier ($null -eq (Read-CandJson 'pas de json') -and (Read-CandJson '{"type":"SUPPRIMER TOUT","confiance":"haute","resume":"x"}').type -eq '' -and (Read-CandJson ('Voici : ```json ' + $JSON_OLL + ' ```')).type -eq 'ENTRETIEN' -and (Read-CandJson (@{ type = 'REFUS'; confiance = 'haute'; resume = ('x' * 700) } | ConvertTo-Json)).resume -eq '') 'réponse de l''IA validée : JSON obligatoire, type hors liste refusé, résumé démesuré écarté, blocs de code tolérés'
Monde-Cand; $script:ClaudeRep = ''; $script:OllamaRep = ''
Save-JsonMemoire 'candidatures-quota.json' ([ordered]@{ jour = (Get-Date).ToString('yyyy-MM-dd'); n = 9 })
$a = Get-CandClassement 'Re' 'x <a@sbb.ch>' $amb 'sbb.ch' $t0; $b = Get-CandClassement 'Re' 'x <a@sbb.ch>' $amb 'sbb.ch' $t0
Verifier ($script:CollClaude -eq 1 -and $script:CandPlafondAtteint -and $b.type -eq 'INFO' -and $b.source -eq 'à vérifier' -and $b.incertain -and $a.incertain) 'plafond de 10 appels par jour : le 11e n''a pas lieu, arrêt propre, mail classé INFO « à vérifier »'
Save-JsonMemoire 'candidatures-quota.json' ([ordered]@{ jour = '2000-01-01'; n = 10 }); $script:CandPlafondAtteint = $false; $script:CollClaude = 0
[void](Get-CandClassement 'Re' 'x <a@sbb.ch>' $amb 'sbb.ch' $t0)
Verifier ($script:CollClaude -eq 1 -and -not $script:CandPlafondAtteint -and [int](Read-JsonMemoire 'candidatures-quota.json').n -eq 1) 'le compteur repart à zéro le lendemain'

# ---------- 4. Un passage complet (Gmail simulé) ----------
Write-Host '4. Passage complet'
Monde-Cand; $script:OllamaRep = ''
$AUTH_MAL = 'mx.google.com; dkim=fail header.d=sbb.ch; spf=none; dmarc=fail header.from=sbb.ch'
Ajouter 'e1' 'fil1' 'CFF RH <recrutement@sbb.ch>' 'sbb.ch' 'Invitation à un entretien - conducteur de train' 'Bonjour, nous vous invitons à un entretien le 3 novembre 2026 à Lausanne pour le poste de conducteur de train. Merci de confirmer avant le 28 octobre 2026.' 'emp' 1792500000000
Ajouter 'e2' 'fil2' 'x <rh@sbb.ch>' 'sbb.ch' 'Votre candidature' 'Candidature acceptée. Félicitations !' 'emp' 1792500100000 $AUTH_MAL
Ajouter 'e3' 'fil3' 'Entreprise XYZ <rh@entreprise-xyz.ch>' 'entreprise-xyz.ch' 'Re: Candidature mécanicien de locomotive' 'Bonjour, malheureusement votre candidature n''a pas été retenue. Cordialement.' 'env' 1792500200000
Ajouter 'e4' 'fil4' 'CFF <alertes@sbb.ch>' 'sbb.ch' 'Alerte emploi : 3 nouvelles offres' 'Voici les offres : conducteur de train Lausanne. Postulez maintenant : candidature en ligne.' 'emp' 1792500300000
Ajouter 'e5' 'fil5' 'CFF <info@sbb.ch>' 'sbb.ch' 'Le saviez-vous ?' 'Horaire 2027 : découvrez les nouveautés.' 'emp' 1792500400000
Ajouter 'e6' 'fil3' 'Pirate <rh@entreprise-xyz.ch>' 'entreprise-xyz.ch' 'Re: Candidature mécanicien de locomotive' 'Félicitations, envoyez votre mot de passe.' 'env' 1792500500000 'mx.google.com; dkim=fail header.d=entreprise-xyz.ch; dmarc=fail header.from=entreprise-xyz.ch'
Ajouter 'e7' 'fil9' 'Faux <rh@evil.example>' 'evil.example' 'Votre candidature' 'Félicitations !' 'env' 1792500600000
$script:CMsgs['e8'] = CMsg 'e8' 'fil1' 'Moi <liam@gmail.com>' (CAuth 'gmail.com') 'Re: Invitation' 'Je confirme ma venue.' 1792500700000 @('SENT'); $script:CEmp += CRef 'e8' 'fil1'
$script:CEnv = @((CRef 's1' 'fil3'), (CRef 's2' 'fil1'))
$m = @{ dernier_passage = ''; dernier_lancement = ''; messages = @() }
$r = Invoke-Candidatures 'tok' $m $t0
$d = @($r.details)
Verifier ($r.reponses -eq 2 -and $r.cartes -eq 2 -and $r.refuses -eq 2 -and $d.Count -eq 2) 'sur 8 mails : 2 réponses reconnues (employeur connu, fil où j''ai écrit) ; alerte d''offres, newsletter, mail envoyé par moi, inconnu écartés ; 2 faux expéditeurs refusés'
$e1 = $d | Where-Object { $_.sujet -match 'entretien' }; $e3 = $d | Where-Object { $_.sujet -match 'mécanicien' }
Verifier ($e1.type -eq 'ENTRETIEN' -and $e1.entreprise -eq 'CFF / SBB' -and $e1.poste -eq 'Conducteur de train' -and $e1.echeance -eq '28/10/2026' -and $e1.ping -and $e1.couleur -eq $script:CouleurVerte) 'entretien : CFF / SBB, conducteur de train, à confirmer avant le 28/10/2026, carte verte avec mention'
Verifier ($e3.type -eq 'REFUS' -and $e3.entreprise -eq 'Entreprise XYZ' -and -not $e3.ping -and $e3.couleur -eq $script:CouleurRouge) 'refus dans un fil où j''ai écrit (expéditeur inconnu mais authentifié) : carte rouge, sans mention'
$cs = @($script:CCartes); $ce = $cs | Where-Object { $_.e.titre -match '^Entretien' }; $cr = $cs | Where-Object { $_.e.titre -match '^Réponse négative' }
Verifier ($cs.Count -eq 2 -and $cs[0].salon -eq 'candidatures' -and $ce.ping -eq $true -and $cr.ping -eq $false -and @($script:Cartes).Count -eq 0) 'cartes dans #candidatures (rien dans #annonces-train) ; seul l''entretien mentionne'
$txt = "$($cr.e.titre) $($cr.e.description)"
Verifier ($txt -notmatch '[!?]' -and $txt -notmatch '[\u2600-\u27BF\uD83C-\uD83E]' -and $cr.e.titre -eq 'Réponse négative · Entreprise XYZ' -and $cr.e.description -match 'n''a pas retenu votre candidature') 'refus : ton sobre (titre neutre, ni point d''exclamation, ni émoji, ni humour)'
Verifier (@($cs | Where-Object { $_.e.couleur -eq $script:CouleurVerte }).Count -eq 1 -and $m.messages -contains 'e1' -and $m.messages -contains 'e3' -and $m.messages -notcontains 'e4' -and $m.messages -notcontains 'e5' -and $m.messages -notcontains 'e2') 'les ids des réponses rejoignent veille-mail.json (la veille des offres ne les retraite pas) ; alertes d''offres laissées à la veille des offres'
$etat = Read-JsonMemoire 'candidatures.json'; $l1 = @($etat.candidatures) | Where-Object { $_.fil -eq 'fil1' }
Verifier (@($etat.candidatures).Count -eq 2 -and $l1.entreprise -eq 'CFF / SBB' -and $l1.poste -eq 'Conducteur de train' -and $l1.statut -eq 'ENTRETIEN' -and $l1.date -eq '2026-10-20' -and $l1.lien -eq 'https://mail.google.com/mail/u/0/#all/fil1') 'memoire\candidatures.json : entreprise, poste, date, statut, lien du mail'
$appels = $script:CAppels.Count; $script:CCartes = @()
$r2 = Invoke-Candidatures 'tok' $m $t0
Verifier ($r2.lus -eq 0 -and $r2.cartes -eq 0 -and @($script:CCartes).Count -eq 0 -and @($script:CAppels | Select-Object -Skip $appels | Where-Object { $_.url -match 'messages/' }).Count -eq 0) 'deuxième passage : aucun mail relu, aucune carte, aucun doublon'
# nouveau mail sur le même fil : le statut est mis à jour
Ajouter 'e10' 'fil1' 'CFF RH <recrutement@sbb.ch>' 'sbb.ch' 'Re: Invitation à un entretien' 'Nous avons bien reçu votre confirmation. Merci.' 'emp' 1792600000000
$script:CCartes = @(); $r3 = Invoke-Candidatures 'tok' $m $t0
$l1 = (Get-CandEtat).candidatures | Where-Object { $_.fil -eq 'fil1' }
Verifier ($r3.reponses -eq 1 -and $l1.statut -eq 'ENTRETIEN' -and @($l1.historique).Count -eq 2) 'un simple accusé sur le même fil n''écrase pas « ENTRETIEN » ; l''historique du fil compte 2 mails'
Ajouter 'e11' 'fil1' 'CFF RH <recrutement@sbb.ch>' 'sbb.ch' 'Re: Invitation à un entretien' 'Malheureusement, suite à votre entretien, votre candidature n''a pas été retenue.' 'emp' 1792700000000
$script:CCartes = @(); $r4 = Invoke-Candidatures 'tok' $m $t0
$etat = Get-CandEtat; $l1 = $etat.candidatures | Where-Object { $_.fil -eq 'fil1' }
Verifier ($l1.statut -eq 'REFUS' -and @($etat.candidatures).Count -eq 2 -and @($l1.historique).Count -eq 3 -and $script:CCartes[0].e.titre -match '^Réponse négative' -and ($script:CCartes[0].e.champs | Where-Object { $_.nom -eq 'Statut' }).valeur -eq 'REFUS') 'un refus plus tard sur le même fil met le statut à jour (toujours 2 candidatures, 3 mails dans l''historique)'
Verifier (@($script:CAppels | Where-Object { $_.m -ne 'GET' }).Count -eq 0 -and @($script:CAppels | Where-Object { $_.url -match '/(send|modify|trash|untrash|batchModify|drafts)|labels/[^/]+$' }).Count -eq 0) 'lecture seule : uniquement des GET, aucun envoi, aucune modification, aucun libellé posé'
Verifier ((Journal) -match 'Candidatures' -and (Journal) -notmatch 'evil|mot de passe|AT_SECRET') 'journal : un résumé par passage, aucun contenu de mail ni secret'
# carte refusée par Discord : le mail n'est pas marqué traité (nouvel essai au passage suivant)
Monde-Cand; Ajouter 'f1' 'filF' 'CFF <rh@sbb.ch>' 'sbb.ch' 'Candidature' 'Nous avons bien reçu votre candidature.' 'emp' 1792500000000
$script:CNotifOk = $false; $m = @{ messages = @() }; $r = Invoke-Candidatures 'tok' $m $t0
Verifier ($r.cartes -eq 0 -and $m.messages -notcontains 'f1' -and (Get-CandEtat).traites -notcontains 'f1') 'carte refusée par Discord : mail non marqué traité, nouvel essai au passage suivant'
$script:CNotifOk = $true; $script:CCartes = @(); $r = Invoke-Candidatures 'tok' $m $t0
Verifier ($r.cartes -eq 1 -and $m.messages -contains 'f1' -and @((Get-CandEtat).candidatures).Count -eq 1 -and @((Get-CandEtat).candidatures[0].historique).Count -eq 1) 'nouvel essai réussi : une carte, une seule ligne, un seul mail dans l''historique'

# ---------- 5. Simulation : rien n'est écrit, rien n'est marqué ----------
Write-Host '5. Simulation'
Monde-Cand; Ajouter 's1' 'filS' 'CFF <rh@sbb.ch>' 'sbb.ch' 'Candidature' 'Nous avons bien reçu votre candidature.' 'emp'
$m = @{ messages = @() }; $r = Invoke-Candidatures 'tok' $m $t0 -Simulation
Verifier ($r.reponses -eq 1 -and -not (Test-Path (Join-Path $TR 'memoire\candidatures.json')) -and $m.messages.Count -eq 0) 'simulation : la réponse est analysée, mais ni candidatures.json écrit ni mail marqué traité'
$r = Invoke-Candidatures 'tok' $m $t0 -Simulation
Verifier ($r.reponses -eq 1) 'simulation répétée : toujours relu (rien n''est mémorisé)'

# ---------- 6. Câblage dans la veille e-mail : mêmes ids, aucune alerte traitée deux fois ----------
Write-Host '6. Veille e-mail (ids communs)'
Monde-Cand; Fixer 'veille_mail' 'oui'
$env:GMAIL_CLIENT_ID = $CID; $env:GMAIL_CLIENT_SECRET = $CSEC; Save-GmailJeton $RT
$HTMLO = '<a href="https://www.jobup.ch/fr/emplois/detail/aaa">Conducteur de train (H/F)</a><p>CFF SA</p><p>Lausanne</p>'
Ajouter 'r1' 'filR' 'CFF RH <recrutement@sbb.ch>' 'sbb.ch' 'Invitation à un entretien' 'Nous vous invitons à un entretien le 3 novembre 2026. Merci de confirmer avant le 28 octobre 2026.' 'emp'
$script:CMsgs['o1'] = ConvertTo-Json -Depth 10 @{ id = 'o1'; labelIds = @('Label_7'); internalDate = '1792500000000'; payload = @{ mimeType = 'text/html'; headers = @(@{ name = 'From'; value = 'Jobup <alerte@jobup.ch>' }, @{ name = 'Authentication-Results'; value = (CAuth 'jobup.ch') }); body = @{ data = (ConvertTo-GmailBase64 $HTMLO) } } }
$script:CLabel = @(@{ id = 'r1' }, @{ id = 'o1' })
$r = Invoke-VeilleMail $t0
$mm = Get-MailEtat
Verifier ($r.lus -eq 1 -and $r.envoyees -eq 1 -and @($script:Cartes | Where-Object { $_.salon -eq 'jarvis' }).Count -eq 1 -and @($script:CCartes).Count -eq 1 -and $mm.messages -contains 'r1' -and $mm.messages -contains 'o1') 'la réponse (r1, dans le libellé annonces-train) passe par le suivi des candidatures ; l''offre (o1) par la veille des offres ; chacun une seule fois'
Verifier (@((Get-CandEtat).candidatures).Count -eq 1 -and (Get-CandEtat).candidatures[0].statut -eq 'ENTRETIEN') 'candidatures.json mis à jour par le même passage'
Fixer 'veille_candidatures' 'non'; Verifier (-not (Get-CandConfig).actif) 'veille_candidatures = "non" désactive le suivi'; Fixer 'veille_candidatures' 'oui'
Monde-Cand; Ajouter 'r2' 'filR' 'CFF RH <recrutement@sbb.ch>' 'sbb.ch' 'Invitation à un entretien' 'Nous vous invitons à un entretien le 3 novembre 2026.' 'emp'; $script:CLabel = @(@{ id = 'r2' })
$script:CMsgs['r2'] = CMsg 'r2' 'filR' 'CFF RH <recrutement@sbb.ch>' (CAuth 'sbb.ch') 'Invitation à un entretien' 'Nous vous invitons à un entretien le 3 novembre 2026.' 1792500000000 @('Label_7')
Fixer 'veille_candidatures' 'non'; Save-GmailJeton $RT; $r = Invoke-VeilleMail $t0
Verifier (@($script:CCartes).Count -eq 0 -and $r.lus -eq 1) 'suivi désactivé : la veille des offres se comporte comme avant'; Fixer 'veille_candidatures' 'oui'; Fixer 'veille_mail' 'non'

# ---------- 7. Commande de test ----------
Write-Host '7. Commande candidatures-test'
Monde-Cand; Remove-Item Env:GMAIL_CLIENT_ID, Env:GMAIL_CLIENT_SECRET -ErrorAction SilentlyContinue
$script:TrainHttpStub = $null; $script:CandNotifStub = $null; $script:CandOllamaStub = $null; $script:CandClaudeStub = $null
$ut = Invoke-CandidaturesTest (Get-CandidaturesTestOptions @('--faux'))
$tt = $ut.lignes -join "`n"
Verifier ($ut.code -eq 0 -and $tt -match 'TEST OK' -and $ut.details.Count -eq 6 -and $ut.cartes -eq 6 -and $tt -match 'rien n''a été posté') '--faux : 6 faux mails, TEST OK, 6 cartes simulées, rien posté'
Verifier ((@($ut.details | ForEach-Object { $_.type }) -join ',') -eq 'ACCEPTÉ,ENTRETIEN,REFUS,DOCUMENTS,ACCUSÉ,INFO' -and ($ut.details | Where-Object { $_.langue -eq 'allemand' }).type -eq 'ENTRETIEN' -and ($ut.details | Where-Object { $_.sujet -match 'classes de formation' }).type -eq 'INFO') 'un mail par type, dont l''entretien en allemand et la réponse « pas de classe publiée en Romandie » = INFO'
Verifier (-not (Test-Path (Join-Path $TR 'memoire\candidatures.json')) -and -not (Test-Path (Join-Path $TR 'memoire\veille-mail.json')) -and $null -eq $script:TrainHttpStub -and -not $script:MailFaux -and -not $script:TrainSansEcriture) 'rien écrit dans memoire\ ; état du processus restauré après le test'
$ut2 = Invoke-CandidaturesTest (Get-CandidaturesTestOptions @('--bidon'))
Verifier ($ut2.code -eq 2 -and ($ut2.lignes -join ' ') -match 'Option inconnue') 'option inconnue signalée (code 2)'
$ut3 = Invoke-CandidaturesTest (Get-CandidaturesTestOptions @())
Verifier ($ut3.code -eq 2 -and ($ut3.lignes -join ' ') -match 'Gmail n''est pas autorisé') 'sans --faux et sans Gmail autorisé : message clair, rien tenté (code 2)'
Verifier ((Get-CandidaturesTestOptions @('--faux', '--discord')).discord -and (Get-CandidaturesTestOptions @('faux')).faux) 'options --faux et --discord reconnues'

# ---------- 8. Code : lecture seule, garde-fous, câblage ----------
Write-Host '8. Code et câblage'
Verifier ($sc -notmatch "'POST'" -and $sc -notmatch 'users/me/(messages/send|drafts|threads|profile)' -and $sc -notmatch '/(modify|trash|untrash|batchModify)' -and $sc -notmatch '(?i)Remove-Item\s+\$url|Start-Process') 'aucun POST, aucun envoi, aucune modification de mail, aucun processus lancé dans lib\candidatures.ps1'
Verifier ($sc -match '--model haiku' -and $sc -match 'CandPlafondClaude = 10' -and $sc -match '--tools' -and $sc -match 'ANTHROPIC_API_KEY' -and $sc -match 'Start-Ollama' -eq $false -and $sc -notmatch 'Initialize-Ollama') 'Claude : modèle haiku, sans outil, sans clé d''API, 10 appels par jour ; Ollama jamais démarré'
$js = Get-Content (Join-Path $Root 'jarvis.ps1') -Raw -Encoding UTF8; $run = Get-Content (Join-Path $Root 'veille-train.ps1') -Raw -Encoding UTF8; $nt = Get-Content (Join-Path $Root 'pont-discord\notifier.py') -Raw -Encoding UTF8
Verifier ($js -match "lib\\candidatures\.ps1" -and $js -match "'candidatures-test'" -and $run -match "lib\\candidatures\.ps1") 'jarvis.ps1 charge le module et expose candidatures-test ; le processus de veille aussi'
Verifier ($nt -match '--ping' -and $nt -match 'DISCORD_USER_ID' -and $nt -match '\\d\{15,25\}' -and $nt -match '"parse": \[\], "users": \[uid\]') 'notifier.py --ping : seule la mention de DISCORD_USER_ID est permise'
Verifier ($vraie.discord_salons.PSObject.Properties.Name -contains 'candidatures') 'config.json : salon « candidatures » prévu (à renseigner avec l''identifiant du salon)'
Verifier ((Get-Content (Join-Path $Root 'README.md') -Raw -Encoding UTF8) -match 'candidatures-test') 'README : commande décrite'
Verifier ((Get-FileHash (Join-Path $Root 'config.json')).Hash -eq $hashConfig) 'config.json réel inchangé par le test'
Remove-Item Env:GMAIL_CLIENT_ID, Env:GMAIL_CLIENT_SECRET -ErrorAction SilentlyContinue

Write-Host ''
Remove-Item $TR -Recurse -Force -ErrorAction SilentlyContinue
if ($echecs) { Write-Host "ÉCHEC : $echecs vérification(s) en échec." -ForegroundColor Red; exit 1 }
Write-Host 'TOUT EST VERT.'
