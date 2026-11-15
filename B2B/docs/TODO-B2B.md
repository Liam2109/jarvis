# To-do B2B — LM MULTI-SERVICES

_Mise à jour : 16 nov. 2026, 0 h (le fait est supprimé ; l'historique est dans le journal et dans git)_

## Lundi 16 nov. (appels d'abord)
- [ ] 07 h 20 : session ouverte sur le serveur ; 07 h 35 : la feuille de Sid existe, sinon `Start-ScheduledTask Jarvis-B2B-appels-sid`
- [ ] 19 h 30 : le résumé Discord compte bien les 8 valeurs de Résultat
- [ ] Sid : lire l'accroche à voix haute, noter les phrases exactes qui ont fait dire non ; bilan Sid du 13 nov. à lui envoyer

## Avant le premier devis envoyé (ça coûte une vente)
- [ ] Droit de rétractation (vente à distance), formulation d'arrêt, transfert du domaine (code chez le bureau d'enregistrement) : à faire relire
- [ ] Prévoir comment livrer un site complet multi-pages avant d'en vendre un
- [ ] Décider les commissions (≈10 % appelant, 10 % closer ?) et si c'est sur le premier paiement seulement ou aussi sur les 49 €/mois
- [ ] Décider : petit acompte (environ 100 €) pour le client sans confiance ? Contredit « sans acompte » ; pas dans les scripts avant décision
- [ ] Test de cohérence : étendre aux notes docs\decisions et docs\agents (la note « Offre 595 + 49 » avait encore 990–1 490 € et « lien à créer », hors du périmètre du test) ; vérifier aussi les 3 autres notes de décision

## Liam
- [ ] Valider la liste des idées supprimées d'IDEES-MASTER.md (sauvegarde dans B2B\donnees\sauvegardes\) et trancher la section « À trancher »
- [ ] Lundi 16 : prendre les ~15 dernières lignes de la feuille de Sid (ta propre liste « Appels Liam » commence mardi 17)
- [ ] Serveur : ajouter « nettoyage-fichiers » aux agents actifs (tâche chaque jour à 03:00)
- [ ] Serveur : accepter la mise à jour puis ajouter appels-liam aux agents actifs (et envoi_automatique à true dans la config locale d'appels-liam pour la feuille Google)
- [ ] Envoyer SCRIPT-APPEL-SID.md à Sid (seulement celui-là ; closing et techniques restent à toi)
- [ ] Serveur : `git -C <dossier Jarvis> config core.hooksPath .githooks`, ajouter « surveillant » aux agents actifs
- [ ] Mettre l'adresse secrète iCal dans la config locale de l'agent Rendez-vous, puis dire « fait »
- [ ] Vérifier que /codex:setup a marché (sans clé API)
- [ ] Stripe : SIRET et mention TVA art. 293 B en pied de facture ; site web (encore ecom-quiz.vercel.app) et description publique
- [ ] Malt : candidats « Prospection téléphonique B2B », répondre à Eric Ling
- [ ] Facebook Normandie et Leboncoin : poster l'offre « page exemple à ton nom »

## Agents (ensuite, une étape à la fois)
- [ ] Les tests laissent des dossiers dans %TEMP% : les faire se nettoyer eux-mêmes ; 6 mentions « Répondu / Refus » gardées exprès (anciennes feuilles de Sid)
- [ ] Terminer l'étape Vente (réparer reponses.py, puis Réponses, Rendez-vous, Devis, Relances J+3 et J+7, lead chaud), chacun avec contrat + garde + test + fiche avant activation
- [ ] Fiches agents : 19 « à compléter par Liam » (production, vente-relances, responsables Vente / Argent / Production) à remplir avec l'étape Vente ; agents sur le serveur : relancer generer-fiches.py là-bas pour avoir les traces
- [ ] Faire passer la publication et le déploiement des pages exemples par la garde (non branchés)
- [ ] CEO Jarvis autonome, pont Discord de Jarvis (connecte: false) : après la 1re vente
- [ ] Production (design, code, publication) : après la 1re vente
- [ ] Tableau de bord (maquette validée, voir IDEES-MASTER 14/11) : agents en ligne, courbes, closing, commissions, pipeline
- [ ] Fiche d'accueil client (photos, couleurs, logo, avis, spécificités)
- [ ] Recruter d'autres appelants (15 %), un spécialiste restaurants, des closers (10 %)
- [ ] Enrichir TECHNIQUES-CLOSING.md avec de bonnes phrases de vente
- [ ] Liam s'entraîne au jeu de rôle des objections (« Je dois réfléchir », « C'est trop cher »)
- [ ] Sid doit faire plus d'appels par jour
- [ ] Domaine : renouvellement annuel dans Stripe (plus tard), clarifier « Playwork »
- [ ] Question jamais tranchée : `veille_mail` = bon mapping pour « agent Réponses » ?
- [ ] Parrainage (1 mois de maintenance offert) ; paiement en 3x sans frais (Alma/Floa)
- [ ] Connecteur d'écoute de réunions : nom à donner par Liam, vérifier gratuité et accord des participants
- [ ] Skills du catalogue Claude : Liam colle les noms
