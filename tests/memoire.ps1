# Test de la conversation et de la mémoire — dans un dossier TEMPORAIRE (votre vraie mémoire et vos vrais journaux ne sont pas touchés).
# Vérifie surtout qu'aucune donnée sensible n'est écrite nulle part. Code de sortie 0 = réussi.
$ErrorActionPreference = 'Stop'
$env:JARVIS_TEST = '1'      # TEST SILENCIEUX : aucun son, aucune fenêtre, aucun micro, aucune touche, aucune action réelle (voir lib\journal.ps1)
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $Root 'lib\journal.ps1')
$TR = Join-Path $env:TEMP ('jarvis-test-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
New-Item -ItemType Directory $TR, "$TR\memoire", "$TR\logs" | Out-Null
$script:JarvisRoot = $TR                      # AVANT le chargement des autres modules : tous les chemins pointent vers le dossier temporaire
$script:MemoireTestReelle = $true      # ce test a son PROPRE dossier temporaire (JarvisRoot = $TR) : Get-Mem n'a rien à rediriger
"# To-do de Liam`r`n- [ ] Appeler le comptable" | Set-Content "$TR\memoire\todo.md" -Encoding UTF8
"# Notes (ce que Liam demande de retenir)" | Set-Content "$TR\memoire\notes.md" -Encoding UTF8
"# Résumés quotidiens Jarvis`r`n" | Set-Content "$TR\memoire\resume.md" -Encoding UTF8
$Config = Get-Content (Get-ConfigPath) -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($l in 'voix', 'business', 'permissions', 'actions', 'coffre', 'entrees', 'ecrans', 'tableau', 'visage', 'sons', 'raccourcis', 'cerveau', 'cerveau-local', 'veille', 'memoire', 'rapide', 'discretion', 'modejeu', 'boucle') { . (Join-Path $Root "lib\$l.ps1") }
$script:JarvisRoot = $TR
$script:MemoireTestReelle = $true      # ce test a son PROPRE dossier temporaire (JarvisRoot = $TR) : Get-Mem n'a rien à rediriger
$echecs = 0
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }
$S = @{ mdp = 'hunter2xyz'; carte = '4111 1111 1111 1111'; iban = 'FR76 3000 6000 0112 3456 7890 189'; cle = 'rk_live_ABCDEF1234567890'; cvv = 'CVV 737'; pin = 'code pin 482915' }
$script:Dits = @()
function Reset-Test { $script:Conversation.Clear(); $script:ConvResumeJusqua = 0; $script:Guide = $null; $script:Dits = @(); Remove-Item "$TR\memoire\session-en-cours.jsonl" -Force -ErrorAction SilentlyContinue }
function JournalTexte { (Get-ChildItem "$TR\logs" -Filter 'journal-*.md' -ErrorAction SilentlyContinue | ForEach-Object { Get-Content $_.FullName -Raw -Encoding UTF8 }) -join "`n" }

try {
    Write-Host '1) Données sensibles : masquées partout'
    $cas = @(
        @{ e = "mon mot de passe Vercel est $($S.mdp)"; pas = $S.mdp }, @{ e = "retiens que le mot de passe est $($S.mdp), merci"; pas = $S.mdp }, @{ e = "password = $($S.mdp)"; pas = $S.mdp },
        @{ e = "ma carte $($S.carte) expire en 12/28"; pas = '4111' }, @{ e = "ma carte 4111-1111-1111-1111"; pas = '4111' }, @{ e = "mon iban est $($S.iban)"; pas = '3000 6000' },
        @{ e = "clé : $($S.cle)"; pas = $S.cle }, @{ e = "le $($S.cvv) au dos"; pas = '737' }, @{ e = "$($S.pin) et voilà"; pas = '482915' }, @{ e = 'Bearer abcdef1234567890token'; pas = 'abcdef1234567890token' },
        @{ e = 'bic : BNPAFRPPXXX'; pas = 'BNPAFRPP' }, @{ e = 'mon numéro de sécu 1 85 05 78 006 084 36'; pas = '006 084' }
    )
    foreach ($c in $cas) { $m = Hide-Secrets $c.e; Verifier ($m -notmatch [regex]::Escape($c.pas)) "masqué : « $($c.e) » -> « $m »" }
    foreach ($ok in 'Vous avez 17 quiz commencés', 'Appelle le 06 12 34 56 78', 'rendez-vous le 14/10 à 09 h 30', "le code HTTP est 200", 'le site a 1700 Go libres') { Verifier ((Hide-Secrets $ok) -eq $ok) "texte ordinaire intact : « $ok »" }

    Write-Host '2) Panneau de conversation (voix, texte, réponses, actions)'
    Reset-Test; $script:Actif = $false
    Parler 'Bonjour monsieur'                                           # VRAIE fonction Parler, en sourdine : texte seulement
    Verifier (@($script:Conversation | Where-Object { $_.role -eq 'jarvis' -and $_.texte -eq 'Bonjour monsieur' }).Count -eq 1) 'en sourdine, la réponse de Jarvis apparaît quand même par écrit'
    Add-Conv 'liam' "mon mot de passe est $($S.mdp) et ma carte $($S.carte)"
    $dern = $script:Conversation[-1].texte
    Verifier ($dern -notmatch 'hunter2xyz|4111') "Add-Conv masque avant d'afficher : « $dern »"
    $don = Get-DonneesTableau
    Verifier (@($don.conversation).Count -eq 2 -and $don.conversation[0].role -eq 'jarvis' -and $don.conversation[1].role -eq 'liam') 'le tableau de bord reçoit la conversation dans l''ordre'
    Verifier ((($don | ConvertTo-Json -Depth 6 -Compress) -notmatch 'hunter2xyz|4111 1111')) 'le JSON envoyé au tableau de bord ne contient aucune donnée sensible'
    Verifier ((Get-Content "$TR\memoire\session-en-cours.jsonl" -Raw) -notmatch 'hunter2xyz|4111') 'le fichier de session (secours) est déjà masqué'
    $script:Actif = $true
    function Parler([string]$Texte, $Langue) { $script:Dits += $Texte; Add-Conv 'jarvis' $Texte }       # bouchon : pas de voix réelle pendant la suite du test
    Reset-Test
    $script:Actions['ouvrir_app'].run = { param($a) Rep $true "Application ouverte : $($a.nom)" }
    $script:Actions['powershell'].run = { param($a) Rep $true 'Commande terminée (code 0)' }
    $r = Invoke-UneAction ([pscustomobject]@{ type = 'ouvrir_app'; nom = 'Chrome' }) 'ouvre Chrome'
    Verifier (@($script:Conversation | Where-Object { $_.role -eq 'action' -and $_.texte -eq 'Application ouverte : Chrome' }).Count -eq 1) 'ordre exécuté : ligne courte « Application ouverte : Chrome »'
    $r = Invoke-UneAction ([pscustomobject]@{ type = 'virement'; montant = 100 }) 'vire 100 euros'
    Verifier (@($script:Conversation | Where-Object { $_.role -eq 'action' -and $_.texte -match '^Refusé : .*les virements' }).Count -eq 1) 'niveau 3 : ligne « Refusé : ... »'
    $script:ReponseTest = 'non'; $r = Invoke-UneAction ([pscustomobject]@{ type = 'powershell'; code = 'Get-Date'; resume = 'afficher la date' }) 'donne la date'
    $act = @($script:Conversation | Where-Object { $_.role -eq 'action' } | ForEach-Object { $_.texte })
    Verifier (($act -match '^Demande de confirmation : exécuter une commande').Count -eq 1 -and ($act -match '^Annulé : ').Count -eq 1) 'niveau 2 refusé : « Demande de confirmation » puis « Annulé »'
    $script:ReponseTest = 'oui'; Reset-Test
    $r = Invoke-UneAction ([pscustomobject]@{ type = 'powershell'; code = 'Get-Date'; resume = 'afficher la date' }) 'donne la date'
    Verifier (@($script:Conversation | Where-Object { $_.role -eq 'action' -and $_.texte -eq 'Commande terminée (code 0)' }).Count -eq 1) 'niveau 2 accepté : résultat affiché'
    $script:ReponseTest = ''

    Write-Host '2b) Ordre écrit en sourdine : réponse écrite, AUCUNE action'
    Reset-Test; $script:Actif = $false; $exec = 0
    $script:Actions['ouvrir_app'].run = { param($a) $script:exec++; Rep $true 'x' }; $script:exec = 0
    function Get-Plan([string]$o) { [pscustomobject]@{ dit = 'Voici la réponse écrite.'; langue = 'fr'; actions = @([pscustomobject]@{ type = 'ouvrir_app'; nom = 'Chrome' }) } }
    function Parler([string]$Texte, $Langue) { $script:Dits += $Texte; Add-Conv 'jarvis' $Texte }
    Invoke-OrdreSourdine 'ouvre Chrome et dis-moi bonjour'
    $c = @($script:Conversation | ForEach-Object { "$($_.role): $($_.texte)" })
    Verifier ($c -contains 'liam: ouvre Chrome et dis-moi bonjour') 'l''ordre écrit apparaît dans le panneau'
    Verifier ($c -contains 'jarvis: Voici la réponse écrite.') 'la réponse apparaît par écrit'
    Verifier (($c -match '^action: Non exécuté \(sourdine\) : ouvrir l''application Chrome').Count -eq 1) 'l''action est listée « Non exécuté (sourdine) »'
    Verifier ($script:exec -eq 0) 'AUCUNE action exécutée en sourdine'
    Verifier ((JournalTexte) -match 'Action NON exécutée \(sourdine\)') 'refus tracé dans le journal'
    $script:Actif = $true

    Write-Host '3) Résumé de session (fin de session et soir) dans memoire\resume.md'
    Reset-Test
    Add-Conv 'liam' 'ouvre le bloc-notes'; Add-Conv 'jarvis' 'Très bien monsieur.'; Add-Conv 'action' 'Application ouverte : bloc-notes'
    Add-Conv 'liam' "note que le mot de passe du wifi est $($S.mdp), carte $($S.carte)"; Add-Conv 'jarvis' 'Note enregistrée.'; Add-Conv 'action' 'Note enregistrée.'
    $script:PromptRecu = ''
    $script:Reponse = "Voici le résumé :`n### Décisions`n- Utiliser le bloc-notes pour les idées`n### Fait`n- Bloc-notes ouvert`n- Note enregistrée`n### Reste à faire`n- Appeler le comptable`n### À retenir`n- Le wifi : mot de passe est $($S.mdp), IBAN $($S.iban)"
    function Invoke-Claude([string]$s, [string]$u, [int]$t) { $script:PromptRecu = $u; $script:Reponse }
    Verifier (Invoke-ResumeSession 'fin de session') 'un résumé est écrit'
    $res = Get-Content "$TR\memoire\resume.md" -Raw -Encoding UTF8
    $d = Get-Date -Format 'yyyy-MM-dd'
    Verifier ($res -match "## Conversation du $d \(session \d\d:\d\d–\d\d:\d\d · fin de session\)") 'bloc « Conversation du … (session hh:mm–hh:mm) » ajouté'
    Verifier ($res -match '### Décisions' -and $res -match '### Fait' -and $res -match '### Reste à faire' -and $res -match '### À retenir') 'les quatre sections : décisions, fait, reste à faire, à retenir'
    Verifier ($res -notmatch 'hunter2xyz|FR76 3000|4111') 'AUCUNE donnée sensible dans resume.md (même si le cerveau en renvoie une)'
    Verifier ($script:PromptRecu -notmatch 'hunter2xyz|4111') 'rien de sensible n''est envoyé au cerveau pour le résumé'
    Verifier ($res -notmatch 'Voici le résumé') 'le texte parasite avant les sections est retiré'
    Verifier (-not (Test-Path "$TR\memoire\session-en-cours.jsonl")) 'le fichier de secours est supprimé une fois résumé'
    Verifier (-not (Invoke-ResumeSession 'soir')) 'sans nouveau message, rien n''est résumé deux fois'
    Add-Conv 'liam' 'et maintenant ?'; Add-Conv 'jarvis' 'Je suis à votre écoute.'
    $n0 = ([regex]::Matches((Get-Content "$TR\memoire\resume.md" -Raw), '## Conversation du')).Count
    Verifier ((Invoke-ResumeSession 'soir') -and ([regex]::Matches((Get-Content "$TR\memoire\resume.md" -Raw), '## Conversation du')).Count -eq $n0 + 1) 'les nouveaux messages font un nouveau bloc'
    foreach ($mauvais in @('du texte sans structure', $null)) {
        Reset-Test; Add-Conv 'liam' 'ouvre Chrome'; Add-Conv 'action' 'Application ouverte : Chrome'; Add-Conv 'jarvis' 'Fait.'
        $script:Reponse = $mauvais; [void](Invoke-ResumeSession 'secours')
        $dernier = ((Get-Content "$TR\memoire\resume.md" -Raw) -split '## Conversation du')[-1]
        Verifier ($dernier -match 'Application ouverte : Chrome' -and $dernier -match '### Reste à faire' -and $dernier -match 'Appeler le comptable') "cerveau en échec ($(if ($null -eq $mauvais) { 'aucune réponse' } else { 'sans structure' })) : résumé de secours (faits réels + to-do)"
    }

    Write-Host '4) « Hier, nous avons fait X ; il reste Y »'
    $hier = (Get-Date).AddDays(-1).ToString('yyyy-MM-dd'); $avant = (Get-Date).AddDays(-3).ToString('yyyy-MM-dd')
    "# Résumés quotidiens Jarvis`r`n`r`n## Conversation du $hier (session 10:00–10:30 · fin de session)`n### Décisions`n- rien`n### Fait`n- Site vérifié`n- Facture envoyée`n- Mail trié`n- Quatrième chose`n### Reste à faire`n- Relancer le client`n- Payer la TVA`n### À retenir`n- rien`n" | Set-Content "$TR\memoire\resume.md" -Encoding UTF8
    $rap = Get-RappelHier
    Write-Host "        $rap"
    Verifier ($rap -eq 'Hier, nous avons fait : Site vérifié ; Facture envoyée ; Mail trié. Il reste : Relancer le client ; Payer la TVA.') 'phrase exacte, 3 éléments au plus, issue du résumé écrit'
    "# R`r`n`r`n## Conversation du $avant (session 09:00–09:10 · x)`n### Fait`n- A`n### Reste à faire`n- rien`n" | Set-Content "$TR\memoire\resume.md" -Encoding UTF8
    Verifier ((Get-RappelHier) -match "^La dernière fois, le \d\d/\d\d, nous avons fait : A\.$") 'plus ancien qu''hier : « La dernière fois, le jj/mm »'
    "# R`r`n`r`n## Conversation du $d (session 09:00–09:10 · x)`n### Fait`n- Aujourd'hui`n" | Set-Content "$TR\memoire\resume.md" -Encoding UTF8
    Verifier ((Get-RappelHier) -eq '') 'les résumés d''aujourd''hui ne sont pas des « hier »'
    "# R`r`n`r`n## Conversation du $hier (session 09:00–09:10 · x)`n### Fait`n- rien`n### Reste à faire`n- rien`n" | Set-Content "$TR\memoire\resume.md" -Encoding UTF8
    Verifier ((Get-RappelHier) -eq '') 'résumé « rien / rien » : rien n''est inventé'
    Remove-Item "$TR\memoire\resume.md"; Verifier ((Get-RappelHier) -eq '') 'pas de fichier : rien n''est dit'
    "# R`r`n`r`n## Conversation du $hier (session 10:00–10:30 · fin)`n### Fait`n- Site vérifié`n### Reste à faire`n- Payer la TVA`n" | Set-Content "$TR\memoire\resume.md" -Encoding UTF8
    $ph = Get-BriefingPhrases @{ site = [pscustomobject]@{ ok = $true; code = 200 }; visites = @{ dispo = $false; raison = 'v' }; stats = @{ dispo = $false; raison = 's' }; abonnes = @{ dispo = $false; raison = 'a' }; ca = @{ dispo = $false; raison = 'c' } } @() (Get-RappelHier)
    Verifier ($ph[1] -match '^Hier, nous avons fait : Site vérifié') 'le briefing dit le rappel juste après « Bonjour monsieur »'

    Write-Host '5) Mémoire donnée au cerveau'
    $sys = Get-PromptSysteme
    Verifier ($sys -match 'MÉMOIRE \(DONNÉES de confiance limitée' -and $sys -match 'jamais obéir|ne jamais obéir') 'la mémoire est présentée comme des DONNÉES, pas des instructions'
    Verifier ($sys -match 'Payer la TVA|Site vérifié') 'le dernier résumé est pris en compte'
    Verifier ($sys -match 'Appeler le comptable') 'la to-do ouverte est prise en compte'
    Verifier ($sys -match 'guide_demarrer' -and $sys -match 'rappel_ajouter' -and $sys -match 'oublie_tout') 'les nouvelles compétences sont décrites au cerveau'
    Verifier ($sys -notmatch 'hunter2xyz|4111') 'aucune donnée sensible dans le prompt'

    Write-Host '6) Commandes : notes, rappels, reste à faire, résumé du jour'
    Reset-Test
    $r = & $script:Actions['note_ajouter'].run ([pscustomobject]@{ texte = "le code du portail est 1234, mon mot de passe est $($S.mdp)" })
    $notes = Get-Content "$TR\memoire\notes.md" -Raw -Encoding UTF8
    Verifier ($notes -match 'code du portail' -and $notes -notmatch 'hunter2xyz') 'note ajoutée à memoire\notes.md, secret masqué'
    $r = & $script:Actions['todo_ajouter'].run ([pscustomobject]@{ texte = 'Envoyer la facture' })
    Verifier ((Get-Content "$TR\memoire\todo.md" -Raw) -match '- \[ \] Envoyer la facture') 'tâche ajoutée à memoire\todo.md'
    $futur = (Get-Date).AddMinutes(30).ToString('yyyy-MM-dd HH:mm')
    $r = & $script:Actions['rappel_ajouter'].run ([pscustomobject]@{ texte = "appeler le comptable (code $($S.pin))"; quand = $futur })
    Verifier ($r.ok -and (Get-Content "$TR\memoire\rappels.json" -Raw) -notmatch '482915') 'rappel enregistré, donnée sensible masquée'
    Verifier (-not (& $script:Actions['rappel_ajouter'].run ([pscustomobject]@{ texte = 'x'; quand = (Get-Date).AddHours(-1).ToString('yyyy-MM-dd HH:mm') })).ok) 'heure passée : refusée'
    Verifier (-not (& $script:Actions['rappel_ajouter'].run ([pscustomobject]@{ texte = 'x'; quand = 'demain matin' })).ok) 'heure incompréhensible : refusée (jamais devinée)'
    $r = & $script:Actions['reste_a_faire'].run ([pscustomobject]@{})
    Verifier ($r.donnees -match 'Envoyer la facture' -and $r.donnees -match 'Payer la TVA' -and $r.donnees -match 'Rappels à venir') '« qu''est-ce qu''il reste à faire » : to-do + reste à faire + rappels'
    Add-Conv 'liam' 'ouvre Chrome'; Add-Conv 'action' 'Application ouverte : Chrome'
    $r = & $script:Actions['resume_jour'].run ([pscustomobject]@{})
    Verifier ($r.donnees -match 'Application ouverte : Chrome') '« résume ce qu''on a fait aujourd''hui » : lit la conversation du jour'
    # rappel échu : dit une seule fois ; en sourdine : écrit seulement
    $l = @(Get-Rappels); $l[0].quand = (Get-Date).AddMinutes(-1).ToString('yyyy-MM-dd HH:mm'); Save-Rappels $l
    $script:Dits = @(); $script:ProchainRappel = (Get-Date).AddSeconds(-1); Invoke-Rappels
    Verifier (@($script:Dits | Where-Object { (Test-PhrasePolitesse 'rappel' $_) -and $_ -match 'appeler le comptable' }).Count -eq 1) 'rappel échu : dit'
    $script:ProchainRappel = (Get-Date).AddSeconds(-1); $script:Dits = @(); Invoke-Rappels
    Verifier ($script:Dits.Count -eq 0) 'et une seule fois'

    Write-Host '7) Aide pas à pas'
    Reset-Test; $script:AppelsPlan = 0; function Get-Plan([string]$o) { $script:AppelsPlan++; $null }
    $r = & $script:Actions['guide_demarrer'].run ([pscustomobject]@{ titre = 'Créer un compte Stripe'; etapes = @('Ouvrir stripe.com', 'Cliquer sur Créer un compte', "Saisir l'e-mail", 'Valider') })
    Verifier ($r.ok -and $script:Guide.etapes.Count -eq 4 -and $script:Dits[-1] -match 'Étape 1 sur 4 : Ouvrir stripe.com') 'étape 1 donnée, pas les suivantes'
    Verifier ((Get-DonneesTableau).guide.courant -eq 0 -and (Get-DonneesTableau).guide.etapes.Count -eq 4) 'le fil du guide est dans le panneau'
    Invoke-Ordre 'suivant'; Verifier ($script:Guide.courant -eq 1 -and $script:Dits[-1] -match 'Étape 2 sur 4') '« suivant » : étape 2'
    Invoke-Ordre 'répète'; Verifier ($script:Guide.courant -eq 1 -and $script:Dits[-1] -match 'Étape 2 sur 4') '« répète » : même étape'
    Invoke-Ordre "c'est fait"; Verifier ($script:Guide.courant -eq 2) '« c''est fait » : étape 3'
    Invoke-Ordre 'étape précédente'; Verifier ($script:Guide.courant -eq 1) '« étape précédente »'
    Verifier ($script:AppelsPlan -eq 0) 'la navigation dans le guide ne passe pas par le cerveau (pas de validation inventée)'
    Invoke-Ordre 'annule le guide'; Verifier ($null -eq $script:Guide) '« annule le guide » : arrêté'
    [void](& $script:Actions['guide_demarrer'].run ([pscustomobject]@{ titre = 'Court'; etapes = @('A', 'B') })); Invoke-Ordre 'ok'; Invoke-Ordre 'ok'
    Verifier ($null -eq $script:Guide -and $script:Dits[-1] -match 'est terminé') 'dernière étape validée : guide terminé'
    Verifier (-not (& $script:Actions['guide_demarrer'].run ([pscustomobject]@{ titre = 'x'; etapes = @('seule') })).ok) 'un guide d''une seule étape est refusé'

    Write-Host '8) « Oublie tout » (niveau 2, corbeille)'
    "# R`r`n`r`n## Conversation du $hier (x)`n### Fait`n- Quelque chose`n" | Set-Content "$TR\memoire\resume.md" -Encoding UTF8
    Add-Conv 'liam' 'bonjour'
    Verifier ((Get-Niveau ([pscustomobject]@{ type = 'oublie_tout' })).niveau -eq 2) 'niveau 2 : confirmation obligatoire'
    $script:ReponseTest = 'non'; $r = Invoke-UneAction ([pscustomobject]@{ type = 'oublie_tout' }) 'oublie tout'
    Verifier ($null -eq $r -and (Get-Content "$TR\memoire\resume.md" -Raw) -match 'Quelque chose') 'refus : rien n''est effacé'
    $script:ReponseTest = 'oui'; $jAvant = (JournalTexte).Length; $r = Invoke-UneAction ([pscustomobject]@{ type = 'oublie_tout' }) 'oublie tout'
    $script:ReponseTest = ''
    Verifier ($r -and $r.ok -and (Get-Content "$TR\memoire\resume.md" -Raw) -notmatch 'Quelque chose') 'accepté : résumés vidés'
    Verifier ((Get-Content "$TR\memoire\notes.md" -Raw) -notmatch 'portail' -and (Test-Path "$TR\memoire\notes.md")) 'notes vidées (en-tête recréé)'
    Verifier (@(Get-Rappels).Count -eq 0 -and @($script:Conversation.ToArray() | Where-Object { $_.texte -eq 'bonjour' }).Count -eq 0 -and $script:Conversation.Count -le 1 -and $null -eq $script:Guide) 'rappels, conversation et guide vidés (seule la ligne de résultat de l''action reste affichée)'
    Verifier ((Get-Content "$TR\memoire\todo.md" -Raw) -match 'Envoyer la facture') 'la to-do est conservée'
    $j = JournalTexte
    Verifier ($j.Length -gt $jAvant -and $j -match 'Mémoire vidée \(oublie tout\)' -and $j -match 'Parole|Ordre|REFUS|Résumé') 'le journal est intact et trace l''effacement'

    Write-Host '9) Session interrompue (arrêt forcé) : résumée au démarrage suivant'
    Reset-Test
    $lignes = @(@{ d = $hier; h = '08:00'; role = 'liam'; texte = 'ouvre Chrome' }, @{ d = $hier; h = '08:01'; role = 'action'; texte = 'Application ouverte : Chrome' }, @{ d = $hier; h = '08:02'; role = 'jarvis'; texte = 'Fait.' })
    ($lignes | ForEach-Object { $_ | ConvertTo-Json -Compress }) | Set-Content "$TR\memoire\session-en-cours.jsonl" -Encoding UTF8
    $script:Reponse = "### Décisions`n- rien`n### Fait`n- Chrome ouvert`n### Reste à faire`n- rien`n### À retenir`n- rien"
    Initialize-Memoire
    Verifier ($script:LignesOrphelines.Count -eq 3 -and -not (Test-Path "$TR\memoire\session-en-cours.jsonl")) 'le fichier d''une session interrompue est repris'
    Invoke-ResumeOrphelin
    $res = Get-Content "$TR\memoire\resume.md" -Raw -Encoding UTF8
    Verifier ($res -match "## Conversation du $hier \(session 08:00–08:02 · session précédente interrompue\)" -and $res -match 'Chrome ouvert') 'résumé écrit avec la date de la session interrompue'

    Write-Host '10) Balayage final : aucune donnée sensible nulle part'
    Add-Conv 'liam' "retiens $($S.carte) $($S.iban) $($S.cle) $($S.cvv) mon mot de passe est $($S.mdp)"
    Write-Journal -Ordre "mon mot de passe est $($S.mdp) carte $($S.carte)" -Action "iban $($S.iban)" -Resultat "clé $($S.cle)"
    [void](Add-Memoire 'notes.md' "- note : $($S.carte) $($S.iban) mot de passe est $($S.mdp)")
    $tout = (Get-ChildItem $TR -Recurse -File | ForEach-Object { Get-Content $_.FullName -Raw -Encoding UTF8 }) -join "`n"
    foreach ($k in 'hunter2xyz', '4111 1111 1111 1111', '4111-1111', 'FR76 3000 6000', 'rk_live_ABCDEF', '482915', 'CVV 737') { Verifier ($tout -notmatch [regex]::Escape($k)) "« $k » n'apparaît dans AUCUN fichier (mémoire, session, rappels, journal)" }
    Verifier ((Get-ChildItem $TR -Recurse -File).Count -ge 5) "($((Get-ChildItem $TR -Recurse -File).Count) fichiers examinés)"
} finally {
    Remove-Item $TR -Recurse -Force -ErrorAction SilentlyContinue
}

if ($echecs) { Write-Host "`nÉCHEC : $echecs vérification(s) en échec." -ForegroundColor Red; exit 1 }
Write-Host "`nRÉUSSI"; exit 0
