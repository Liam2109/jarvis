# To-do B2B — LM MULTI-SERVICES

_Mise à jour : 15 nov. 2026, 19 h 20 (le fait est supprimé ; l'historique est dans le journal et dans git)_

## Lundi 16 nov. (appels d'abord)
- [ ] 07 h 20 : session ouverte sur le serveur ; 07 h 35 : la feuille de Sid existe, sinon `Start-ScheduledTask Jarvis-B2B-appels-sid`
- [ ] 19 h 30 : le résumé Discord compte bien les 8 valeurs de Résultat
- [ ] Sid : lire l'accroche à voix haute, noter les phrases exactes qui ont fait dire non ; bilan Sid du 13 nov. à lui envoyer

## Avant le premier devis envoyé (ça coûte une vente)
- [ ] Droit de rétractation (vente à distance), formulation d'arrêt, transfert du domaine (code chez le bureau d'enregistrement) : à faire relire
- [ ] Prévoir comment livrer un site complet multi-pages avant d'en vendre un
- [ ] Décider les commissions (≈10 % appelant, 10 % closer ?) et si c'est sur le premier paiement seulement ou aussi sur les 49 €/mois
- [ ] Décider : petit acompte (environ 100 €) pour le client sans confiance ? Contredit « sans acompte » ; pas dans les scripts avant décision
- [ ] Dire à Sid de noter dans Note la phrase exacte de douleur du client (pas seulement celle du non)
- [ ] Test de cohérence : ajouter « pas obligatoire » aux phrases interdites (non détecté avant la correction de objections.md)
- [ ] Valider les règles de reprise des appels (Pas de réponse = 3 tentatives, etc.)

## Liam
- [ ] Ouvrir B2B\docs\agents comme coffre Obsidian (« Ouvrir un dossier comme coffre »), commencer par 00-ORGANIGRAMME
- [ ] Serveur : `git -C <dossier Jarvis> config core.hooksPath .githooks`, ajouter « surveillant » aux agents actifs
- [ ] Mettre l'adresse secrète iCal dans la config locale de l'agent Rendez-vous, puis dire « fait »
- [ ] Vérifier que /codex:setup a marché (sans clé API)
- [ ] Stripe : SIRET et mention TVA art. 293 B en pied de facture ; site web (encore ecom-quiz.vercel.app) et description publique
- [ ] Malt : candidats « Prospection téléphonique B2B », répondre à Eric Ling
- [ ] Facebook Normandie et Leboncoin : poster l'offre « page exemple à ton nom »

## Agents (ensuite, une étape à la fois)
- [ ] Les tests laissent des dossiers dans %TEMP% : les faire se nettoyer eux-mêmes ; 6 mentions « Répondu / Refus » gardées exprès (anciennes feuilles de Sid)
- [ ] Étape Vente, en commençant par réparer reponses.py (caractères de contrôle) : Réponses (lire contact.lmsites et liamdigital2109), Rendez-vous, Devis, Relances J+3 / J+7 et lead chaud ; chacun avec contrat, garde, test et fiche avant activation
- [ ] Fiches agents : 19 « à compléter par Liam » (production, vente-relances, responsables Vente / Argent / Production) à remplir avec l'étape Vente ; agents sur le serveur : relancer generer-fiches.py là-bas pour avoir les traces
- [ ] Faire passer la publication et le déploiement des pages exemples par la garde (non branchés)
- [ ] CEO Jarvis autonome, pont Discord de Jarvis (connecte: false) : après la 1re vente
- [ ] Production (design, code, publication) : après la 1re vente
- [ ] Tableau de bord (maquette validée, voir IDEES-MASTER 14/11) : agents en ligne, courbes, closing, commissions, pipeline
- [ ] Fiche d'accueil client (photos, couleurs, logo, avis, spécificités)
- [ ] Recruter d'autres appelants (15 %), un spécialiste restaurants, des closers (10 %)
- [ ] Relire TECHNIQUES-CLOSING.md (créé le 15/11), le dire à voix haute, jeu de rôle du closing (« je dois réfléchir », « trop cher », plombier méfiant)
- [ ] Domaine : renouvellement annuel dans Stripe (plus tard), clarifier « Playwork »
- [ ] Question jamais tranchée : `veille_mail` = bon mapping pour « agent Réponses » ?
- [ ] Parrainage (1 mois de maintenance offert) ; paiement en 3x sans frais (Alma/Floa)
- [ ] Connecteur d'écoute de réunions : nom à donner par Liam, vérifier gratuité et accord des participants
- [ ] Skills du catalogue Claude : Liam colle les noms
- [ ] Ouvrir B2B\docsgents comme coffre Obsidian
