# Test du chemin rapide (sans IA) : reconnaissance, refus des cas douteux, sûreté, niveaux, et durées. Code de sortie 0 = réussi.
$ErrorActionPreference = 'Stop'
$env:JARVIS_TEST = '1'      # TEST SILENCIEUX : aucun son, aucune fenêtre, aucun micro, aucune touche, aucune action réelle (voir lib\journal.ps1)
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $Root 'lib\journal.ps1')
$TR = Join-Path $env:TEMP ('jarvis-test-' + [guid]::NewGuid().ToString('N').Substring(0, 8)); New-Item -ItemType Directory $TR, "$TR\memoire", "$TR\logs" | Out-Null; $script:JarvisRoot = $TR
"# To-do de Liam`r`n- [ ] Appeler le comptable" | Set-Content "$TR\memoire\todo.md" -Encoding UTF8; '# Notes' | Set-Content "$TR\memoire\notes.md" -Encoding UTF8; '# R' | Set-Content "$TR\memoire\resume.md" -Encoding UTF8
$Config = Get-Content (Get-ConfigPath) -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($l in 'voix', 'business', 'permissions', 'actions', 'coffre', 'entrees', 'ecrans', 'tableau', 'visage', 'sons', 'raccourcis', 'cerveau', 'cerveau-local', 'veille', 'memoire', 'rapide', 'marche', 'comprehension', 'pc', 'bureau', 'discretion', 'modejeu', 'boucle') { . (Join-Path $Root "lib\$l.ps1") }
$script:JarvisRoot = $TR
$echecs = 0
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }
function Premier($plan) { if ($plan -and @($plan.actions).Count) { $plan.actions[0] } else { $null } }

Write-Host '1) Reconnaissance : ordre -> action attendue'
$now = Get-Date
$cas = @(
    @('quelle heure est-il ?', '', $null), @('Jarvis, quelle heure est-il', '', $null), @("dis-moi l'heure", '', $null), @('il est quelle heure', '', $null),
    @('quel jour sommes-nous', '', $null), @('quelle est la date', '', $null), @('on est le combien ?', '', $null),
    @('passe en sourdine', 'sourdine', $null), @('mets-toi en sourdine', 'sourdine', $null), @('tais-toi', 'sourdine', $null), @('silence', 'sourdine', $null),
    @('déverrouille le coffre', 'bitwarden_deverrouiller', $null), @('ouvre le coffre', 'bitwarden_deverrouiller', $null), @('rouvre la fenêtre du coffre', 'bitwarden_deverrouiller', $null), @('Jarvis, déverrouille le coffre s''il te plaît', 'bitwarden_deverrouiller', $null),
    @('verrouille le coffre', 'bitwarden_verrouiller', $null), @('ferme le coffre', 'bitwarden_verrouiller', $null), @('le coffre est-il ouvert ?', 'bitwarden_statut', $null),
    @('oublie tout', 'oublie_tout', $null),
    @('mets le volume à 30', 'volume', @{ niveau = 30 }), @('règle le son à 50 %', 'volume', @{ niveau = 50 }), @('monte le volume', 'volume', @{ delta = 10 }), @('baisse un peu le son', 'volume', @{ delta = -10 }), @('coupe le son', 'volume', @{ muet = $true }), @('remets le son', 'volume', @{ muet = $false }),
    @('mets la luminosité à 40', 'luminosite', @{ niveau = 40 }),
    @('lance une analyse rapide Defender', 'analyse_defender', @{ mode = 'rapide' }), @('lance une analyse complète antivirus', 'analyse_defender', @{ mode = 'complete' }),
    @('y a-t-il des menaces sur mon pc', 'scanner_menaces', $null), @('cherche des processus suspects', 'scanner_menaces', $null),
    @("combien d'abonnés j'ai", 'business_etat', $null), @("chiffre d'affaires", 'business_etat', $null), @('comment va mon business', 'business_etat', $null),
    @("l'état du site", 'etat_site', $null), @('est-ce que le site marche ?', 'etat_site', $null), @('mon site est en ligne ?', 'etat_site', $null),
    @("donne-moi l'état de mon système", 'etat_systeme', $null), @('comment va mon PC', 'etat_systeme', $null), @('combien de mémoire reste-t-il', 'etat_systeme', $null), @('quelle est la charge du processeur', 'etat_systeme', $null),
    @('suis-je connecté à internet', 'reseau_etat', $null), @('internet marche ?', 'reseau_etat', $null),
    @("qu'est-ce qu'il reste à faire", 'reste_a_faire', $null), @("qu'est-ce que j'ai à faire", 'reste_a_faire', $null),
    @("résume ce qu'on a fait aujourd'hui", 'resume_jour', $null), @('fais-moi un résumé de la journée', 'resume_jour', $null),
    @('lis ma to-do', 'todo_lire', $null), @('montre-moi mes tâches', 'todo_lire', $null),
    @('ajoute appeler le comptable à ma to-do', 'todo_ajouter', @{ texte = 'appeler le comptable' }), @('ajoute la tâche : envoyer la facture', 'todo_ajouter', @{ texte = 'envoyer la facture' }),
    @('coche la tâche appeler le comptable', 'todo_terminer', @{ texte = 'appeler le comptable' }),
    @('note que le code du wifi est dans le tiroir', 'note_ajouter', @{ texte = 'le code du wifi est dans le tiroir' }), @('retiens que Marc est en vacances', 'note_ajouter', @{ texte = 'Marc est en vacances' }), @('prends en note : acheter du pain', 'note_ajouter', @{ texte = 'acheter du pain' }),
    @('fais le briefing', 'briefing_dire', $null),
    @('ouvre mes documents', 'ouvrir_chemin', $null), @('ouvre le dossier téléchargements', 'pc_dossier', $null),
    @('ouvre youtube', 'ouvrir_site', @{ url = 'https://www.youtube.com' }), @('ouvre mon site', 'ouvrir_site', @{ url = "$($Config.site)" }), @('ouvre tonproduit.shop', 'ouvrir_site', @{ url = 'tonproduit.shop' }), @('va sur vercel', 'ouvrir_site', @{ url = 'https://vercel.com/dashboard' }),
    @('ouvre le bloc-notes', 'ouvrir_app', @{ nom = 'bloc-notes' }), @('ouvre Chrome', 'ouvrir_app', @{ nom = 'Chrome' }), @('lance la calculatrice', 'ouvrir_app', @{ nom = 'calculatrice' }), @('Jarvis, ouvre VS Code', 'ouvrir_app', @{ nom = 'vscode' }),
    @('ferme Chrome', 'pc_fermer', @{ nom = 'chrome' }), @('ferme le bloc-notes', 'pc_fermer', @{ nom = 'bloc-notes' }), @("ferme l'application calculatrice", 'pc_fermer', @{ nom = 'calculatrice' })
)
foreach ($c in $cas) {
    $p = Get-PlanRapide $c[0]; $a = Premier $p
    $ok = $p -and ((-not $c[1] -and @($p.actions).Count -eq 0 -and $p.dit) -or ($c[1] -and $a -and $a.type -eq $c[1]))
    if ($ok -and $c[2]) { foreach ($k in $c[2].Keys) { if ("$($a.$k)" -ine "$($c[2][$k])") { $ok = $false } } }
    Verifier $ok ("« $($c[0]) » -> $(if ($c[1]) { $c[1] } else { 'réponse directe' })" + $(if ($p -and $a) { " ($(($a | ConvertTo-Json -Compress)))" } elseif ($p) { " : $($p.dit)" } else { ' : NON RECONNU' }))
}

Write-Host '2) Dates et heures des rappels'
$now = [datetime]'2026-10-13 21:30'
function Q([string]$o) { $n = ConvertTo-OrdreNorm $o; $q = Get-QuandFr $n $now; if ($q) { $q.quand.ToString('yyyy-MM-dd HH:mm') } else { $null } }
foreach ($c in @(@('demain à 9 h', '2026-10-14 09:00'), @('demain à 9h30', '2026-10-14 09:30'), @('dans 10 minutes', '2026-10-13 21:40'), @('dans deux heures', '2026-10-13 23:30'), @("dans un quart d'heure", '2026-10-13 21:45'), @('dans une demi-heure', '2026-10-13 22:00'),
    @('à 15 h 30', '2026-10-14 15:30'), @('à 22 h', '2026-10-13 22:00'), @('ce soir à 23 h', '2026-10-13 23:00'), @('lundi à 10h30', '2026-10-19 10:00'.Replace('10:00','10:30')), @('mardi à 8 h', '2026-10-20 08:00'), @('demain matin', '2026-10-14 09:00'), @('demain soir', '2026-10-14 19:00'),
    @('après-demain à 14 h', '2026-10-15 14:00'), @('le 25 octobre à 9 h', '2026-10-25 09:00'), @('le 2 octobre à 9 h', '2027-10-02 09:00'), @('dans 3 jours', '2026-10-16 21:30'), @('demain', '2026-10-14 09:00'))) {
    Verifier ((Q $c[0]) -eq $c[1]) ("« $($c[0]) » -> $($c[1])  (obtenu : $(Q $c[0]))")
}
foreach ($c in 'quand tu peux', 'ce soir', 'à 25 h', 'un jour', 'bientôt', "aujourd'hui") { Verifier ($null -eq (Q $c)) "heure non devinée : « $c »" }
$p = Get-PlanRapide "rappelle-moi demain à 9 h d'appeler le comptable"; $a = Premier $p
Verifier ($a.type -eq 'rappel_ajouter' -and $a.texte -eq "appeler le comptable") "rappel : texte « $($a.texte) »"
$p = Get-PlanRapide 'rappelle-moi dans 10 minutes de sortir le pain'; $a = Premier $p
Verifier ($a.type -eq 'rappel_ajouter' -and $a.texte -eq 'sortir le pain') "rappel relatif : « $($a.texte) » à $($a.quand)"
$p = Get-PlanRapide 'à 15 h 30 rappelle-moi de partir chez le dentiste'; $a = Premier $p
Verifier ($a.type -eq 'rappel_ajouter' -and $a.texte -eq 'partir chez le dentiste' -and $a.quand -match ' 15:30$') "heure avant la formule : « $($a.texte) » à $($a.quand)"
$p = Get-PlanRapide 'rappelle-moi lundi à 10h30 de relancer Marc'; $a = Premier $p
Verifier ($a.type -eq 'rappel_ajouter' -and $a.texte -eq 'relancer Marc') "jour de semaine : « $($a.texte) » à $($a.quand)"
Verifier ($null -eq (Get-PlanRapide 'rappelle-moi de payer la TVA')) 'rappel SANS heure : non reconnu (jamais deviné) -> cerveau'
Verifier ($null -eq (Get-PlanRapide "rappelle-moi quand tu peux d'appeler Marc")) 'rappel à l''heure floue : non reconnu -> cerveau'

Write-Host '3) Ce qui NE doit PAS être reconnu (passe au cerveau)'
foreach ($o in 'supprime le fichier C:\temp\a.txt', 'désinstalle Skype', 'exécute le script test.ps1', 'écris un script qui trie mes téléchargements', 'résume ce fichier', 'fais un virement de 100 euros', 'achète des actions Air Liquide', 'désactive Windows Defender', 'dois-je acheter des actions ?',
    'donne-moi le mot de passe de Vercel', 'ouvre un truc et dis-moi bonjour', 'ferme tout', 'ferme la fenêtre', 'arrête le guide', "quel est le sens de la vie", 'déplace mes factures dans Documents', 'envoie un mail à Marc', 'tue le processus chrome', 'mets le volume', 'ouvre', 'note', 'ajoute à ma to-do', 'peux-tu m''aider à préparer ma déclaration', 'explique-moi comment créer un compte Stripe', 'compare ces deux fichiers') {
    Verifier ($null -eq (Get-PlanRapide $o)) "non reconnu : « $o »"
}

Write-Host '4) Sûreté : le chemin rapide ne produit jamais d''action dangereuse'
$types = @{}; foreach ($c in $cas) { $p = Get-PlanRapide $c[0]; foreach ($a in @($p.actions)) { $types[$a.type] = (Get-Niveau $a).niveau } }
$interdits = 'powershell', 'executer_script', 'supprimer_fichier', 'deplacer_fichier', 'installer_programme', 'desinstaller_programme', 'tuer_processus', 'mettre_en_quarantaine', 'envoyer_message', 'bitwarden_saisir', 'virement', 'achat', 'trade', 'action_financiere'
Verifier (-not ($types.Keys | Where-Object { $_ -in $interdits })) "aucun type dangereux produit ($($types.Count) types : $(($types.Keys | Sort-Object) -join ', '))"
$niv2 = @($types.GetEnumerator() | Where-Object { $_.Value -ge 2 } | ForEach-Object { $_.Key })
Verifier ($niv2.Count -eq 1 -and $niv2[0] -eq 'oublie_tout') "seule action de niveau 2 : « oublie tout » ($($niv2 -join ', '))"
Verifier (-not ($types.Values | Where-Object { $_ -ge 3 })) 'aucune action de niveau 3'
$Config | Add-Member -NotePropertyName chemin_rapide -NotePropertyValue $false -Force
Verifier ($null -eq (Get-PlanRapide 'quelle heure est-il')) 'config "chemin_rapide": false désactive les règles'
$Config.chemin_rapide = $true

Write-Host '5) Dans le pipeline : agit d''abord, répond ensuite, mêmes niveaux, aucune IA'
$script:Dits = @(); $script:Sequence = @(); $script:AppelsGetPlan = 0
function Parler([string]$Texte, $Langue) { $script:Dits += $Texte; $script:Sequence += "dit:$Texte"; Add-Conv 'jarvis' $Texte }
function Get-Plan([string]$o) { $script:AppelsGetPlan++; $script:VoieCerveau = 'claude'; [pscustomobject]@{ dit = 'Réponse du cerveau.'; langue = 'fr'; actions = @() } }
$script:Actions['ouvrir_app'].run = { param($a) $script:Sequence += "action:ouvrir_app:$($a.nom)"; Rep $true "Application ouverte : $($a.nom)" }
$script:Actions['fermer_app'].run = { param($a) $script:Sequence += "action:fermer_app:$($a.nom)"; Rep $false "Aucune fenêtre ouverte pour « $($a.nom) »." }
# AUCUNE vraie action dangereuse ne doit s'exécuter pendant ce test (volume, navigateur, sourdine, Defender...) : on les remplace toutes par des bouchons inoffensifs
foreach ($k in 'volume', 'luminosite', 'ouvrir_site', 'ouvrir_chemin', 'etat_site', 'analyse_defender', 'sourdine', 'scanner_menaces', 'etat_systeme', 'reseau_etat', 'business_etat', 'briefing_dire', 'bitwarden_deverrouiller', 'bitwarden_verrouiller', 'bitwarden_statut') { $script:Actions[$k].run = { param($a) Rep $true '(bouchon)' '(bouchon)' } }
Invoke-Ordre 'ouvre le bloc-notes'
Verifier ($script:Sequence[0] -eq 'action:ouvrir_app:bloc-notes' -and $script:Sequence[1] -match '^dit:' -and (Test-PhrasePolitesse 'fait_action' ($script:Sequence[1] -replace '^dit:', ''))) 'l''action part AVANT la réponse parlée'
Verifier ($script:AppelsGetPlan -eq 0) 'aucun appel au cerveau'
Verifier ($script:DernierOrdre.voie -eq 'rapide' -and $script:DernierOrdre.plan_s -lt 0.2) ("voie « rapide », plan en {0:N3} s" -f $script:DernierOrdre.plan_s)
Verifier ((Get-ChildItem "$TR\logs" -Filter 'journal-*.md' | ForEach-Object { Get-Content $_.FullName -Raw -Encoding UTF8 }) -match 'rapide en \d,\d\d s \(règle : app_ouvrir\)|rapide en \d\.\d\d s \(règle : app_ouvrir\)') 'le journal note la voie et la durée'
$script:Sequence = @(); $script:Dits = @(); Invoke-Ordre 'quelle heure est-il ?'
Verifier ($script:Dits[0] -match '^Il est \d+ heures?( \d+)?, monsieur\.$') "réponse directe : « $($script:Dits[0]) »"
$script:Sequence = @(); $script:Dits = @(); Invoke-Ordre 'ferme le bloc-notes'
Verifier ($script:Dits.Count -eq 1 -and $script:Dits[0] -match 'Aucune fenêtre ouverte') 'action en échec : on dit l''échec (pas « C''est fermé »)'
$script:Dits = @(); Invoke-Ordre "fais un truc bizarre avec mes photos"
Verifier ($script:AppelsGetPlan -eq 1 -and $script:Dits[0] -eq 'Réponse du cerveau.' -and $script:DernierOrdre.voie -eq 'claude') 'ordre non reconnu : transmis au cerveau'
# niveau 2 conservé
"# R`r`n`r`n## Conversation du 2026-01-01 (x)`n### Fait`n- Quelque chose`n" | Set-Content "$TR\memoire\resume.md" -Encoding UTF8
$script:ReponseTest = 'non'; $script:Dits = @(); Invoke-Ordre 'oublie tout'
Verifier ((Get-Content "$TR\memoire\resume.md" -Raw) -match 'Quelque chose' -and @($script:Dits | Where-Object { Test-PhrasePolitesse 'confirmer' $_ }).Count -eq 1) '« oublie tout » : confirmation exigée, refus respecté'
$script:ReponseTest = 'oui'; $script:Dits = @(); Invoke-Ordre 'oublie tout'
Verifier ((Get-Content "$TR\memoire\resume.md" -Raw) -notmatch 'Quelque chose') '« oublie tout » : exécuté après « oui »'
$script:ReponseTest = ''
# notes / to-do / rappel réels (dossier temporaire)
$script:Dits = @(); Invoke-Ordre 'note que le code du portail est dans la boîte aux lettres'
Verifier ((Get-Content "$TR\memoire\notes.md" -Raw) -match 'code du portail') 'note enregistrée dans memoire\notes.md'
Invoke-Ordre 'ajoute envoyer la facture à ma to-do'
Verifier ((Get-Content "$TR\memoire\todo.md" -Raw) -match '- \[ \] envoyer la facture') 'tâche ajoutée à memoire\todo.md'
$script:Dits = @(); Invoke-Ordre 'lis ma to-do'
Verifier ($script:Dits[0] -match '^Vous avez 2 tâches : Appeler le comptable, envoyer la facture\.$') "to-do lue : « $($script:Dits[0]) »"
Invoke-Ordre 'rappelle-moi demain à 9 h de relancer Marc'
$r = @(Get-Rappels); Verifier ($r.Count -eq 1 -and $r[0].texte -eq 'relancer Marc' -and $r[0].quand -match ' 09:00$') "rappel enregistré : $($r[0].texte) à $($r[0].quand)"
Verifier ($script:Dits[-1] -match 'je vous le rappellerai le \d\d/\d\d à 9 heures\.') "confirmation : « $($script:Dits[-1]) »"
Invoke-Ordre "résume ce qu'on a fait aujourd'hui"
Verifier ($script:Dits[-1] -match "^Aujourd'hui, nous avons : " -and $script:Dits[-1] -match 'Note enregistrée') "résumé sans IA : « $($script:Dits[-1]) »"
Invoke-Ordre "qu'est-ce qu'il reste à faire"
Verifier ($script:Dits[-1] -match 'envoyer la facture' -and $script:Dits[-1] -match 'relancer Marc') '« reste à faire » : to-do + rappels'
Verifier ($script:AppelsGetPlan -eq 1) 'tout cela sans le moindre appel au cerveau (1 seul appel : l''ordre inconnu)'

Write-Host '6) Sourdine : réponse écrite, aucune action'
$script:Actif = $false; $script:Dits = @(); $script:Sequence = @()
Invoke-OrdreSourdine 'quelle heure est-il ?'
Verifier ((@($script:Conversation.ToArray() | Where-Object { $_.role -eq 'jarvis' -and $_.texte -match '^Il est ' }).Count -ge 1)) 'l''heure est répondue par écrit'
Invoke-OrdreSourdine 'ouvre Chrome'
Verifier (-not ($script:Sequence -match 'action:ouvrir_app') -and @($script:Conversation.ToArray() | Where-Object { $_.texte -match 'Non exécuté \(sourdine\)' }).Count -ge 1) '« ouvre Chrome » : non exécuté, signalé'
$script:Actif = $true

Write-Host '7) Durées'
$ordres = 'ouvre le bloc-notes', 'quelle heure est-il', 'ferme Chrome', 'quel jour sommes-nous', 'mets le volume à 30', 'lis ma to-do', "l'état du site", 'ouvre youtube', 'passe en sourdine', 'rappelle-moi demain à 9 h de partir'
[void](Get-PlanRapide 'ouvre le bloc-notes')       # première utilisation : charge la liste des applications
$t = foreach ($o in $ordres) { $sw = [Diagnostics.Stopwatch]::StartNew(); for ($i = 0; $i -lt 20; $i++) { [void](Get-PlanRapide $o) }; $sw.Elapsed.TotalMilliseconds / 20 }
Write-Host ("        reconnaissance : médiane {0:N1} ms, max {1:N1} ms par ordre" -f (($t | Sort-Object)[[int]($t.Count / 2)]), ($t | Measure-Object -Maximum).Maximum)
Verifier (($t | Measure-Object -Maximum).Maximum -lt 50) 'reconnaissance de chaque ordre : moins de 50 ms'
$Config.cerveau = 'hybride'; $mes = @(); foreach ($o in $ordres[0..7]) { $script:Dits = @(); $sw = [Diagnostics.Stopwatch]::StartNew(); $script:ReponseTest = ''; Invoke-Ordre $o; $mes += $sw.Elapsed.TotalSeconds }
Verifier (($mes | Measure-Object -Maximum).Maximum -lt 2) ("ordre complet (plan + action simulée + réponse simulée) : max {0:N2} s" -f ($mes | Measure-Object -Maximum).Maximum)

Remove-Item $TR -Recurse -Force -ErrorAction SilentlyContinue
if ($echecs) { Write-Host "`nÉCHEC : $echecs vérification(s) en échec." -ForegroundColor Red; exit 1 }
Write-Host "`nRÉUSSI"; exit 0
