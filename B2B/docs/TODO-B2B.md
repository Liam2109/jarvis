# To-do B2B — LM MULTI-SERVICES

_Mise à jour : 24 nov. 2026 (le fait est supprimé ; l'historique est dans le journal et dans git)_

## Équipe LinkedIn (à activer par Liam)
- [ ] LinkedIn automatique, avant le « go linkedin auto » : `pip install playwright` + `playwright install msedge` sur le serveur, `python B2Bgents\linkedin-equipe.py auto connexion` (tu te connectes toi-même), puis `go_linkedin_auto: true`. Surveille le premier jour : les sélecteurs de LinkedIn n'ont pu être testés qu'en simulation.
- [ ] Ajouter `linkedin-equipe` à agents_actifs du serveur, redémarrer le service du tableau de bord (nouvelle écriture POST /api/linkedin), puis ouvrir la rubrique LinkedIn depuis http://serveur:8080 (les cases ne s'enregistrent pas depuis le fichier du gros PC)

## Lundi 16 nov. (appels d'abord)
- [ ] 19 h 30 : le résumé Discord compte bien les 8 valeurs de Résultat
- [ ] Sid : lire l'accroche à voix haute, noter les phrases exactes qui ont fait dire non ; bilan Sid du 13 nov. à lui envoyer
- [ ] Vérifier dans quelques jours que les lignes reprises depuis le 13/11 obtiennent enfin un vrai Résultat (la liste ne doit plus être 100 % reprises)
- [ ] Plombier-chauffagiste, électricien, maçon, couvreur, coiffeur : réserve quasi à 0 même après un passage élargi (3 trouvés sur plus de 100 appels SIRENE) ; à surveiller, pas de solution miracle (données publiques rares pour ces métiers)

## Avant le premier devis envoyé (ça coûte une vente)
- [ ] Droit de rétractation (vente à distance), formulation d'arrêt, transfert du domaine (code chez le bureau d'enregistrement) : à faire relire
- [ ] Clause de rétractation de 14 jours dans le devis, à faire relire
- [ ] Prévoir comment livrer un site complet multi-pages avant d'en vendre un
- [ ] Commissions : appelant 15 %, closer 15 % (décidé le 23/11) ; à décider : sur le premier paiement seulement ou aussi sur les 29 €/mois ; aligner OFFRE-REFERENCE.json, scripts et TECHNIQUES-CLOSING si besoin
- [ ] Décider : petit acompte (environ 100 €) pour le client sans confiance ? Contredit « sans acompte » ; pas dans les scripts avant décision
- [ ] Test de cohérence : étendre aux notes docs\decisions et docs\agents (la note « Offre 500 + 29 » est corrigée à la main, mais le test ne la couvre pas) ; vérifier aussi les 3 autres notes de décision

## Liam
- [ ] Cerveau (fermé) : dire « go cerveau » quand tu veux l'ouvrir, puis go_cerveau à true dans les réglages locaux, retirer la clé « desactive » de la tâche cerveau dans serveur-taches.json et ajouter cerveau à agents_actifs ; avant : valider des sources (sites, chaînes YouTube, subreddits, forums) dans B2B\cerveau\sujets.md, sans quoi il ne lit que la recherche par sujet (titres seulement) ; ensuite, redémarrer le service du tableau de bord (POST /api/cerveau) et saisir les chiffres des essais avec `cerveau.py resultat`
- [ ] URGENT Sid : aucun appel depuis ~1 semaine ; il a répondu le 23/11 : OK pour lui, son entreprise est encore en cours de création ; lui demander une date précise de reprise, sans date mercredi chercher un autre appelant
- [ ] Serveur : mise en veille « Jamais » + capot « ne rien faire » (arrêté 22/11 23:51 → 23/11 10:56 et 22/11 09:28 → 17:00)
- [ ] Stock de Sid : limite de durée prospection faite (d557e44) ; rendre à Sid les 11 fiches « préparé » (coiffeur/plombier/électricien) ; zone limitée aux départements 76, 27, 14, 50, 61 (décision 14/11) : à relever seulement si le stock manque
- [ ] Dashboard (01b8143) : ouvrir la page et vérifier à l'œil colonnes par superviseur, ~6 agents passés aujourd'hui, clic = note + journal ; reste : bouton corbeille sur les leads chauds
- [ ] Recrutement appelants : annonce Facebook postée le 23/11 dans 5 groupes (Téléprospection freelance, 100 % Télétravail, Teleconseiller, Suisse/France, Freelancer-Télétravail ; Télévendeur non vérifié) ; formulaire https://forms.gle/5G8FEigjU5Ks6Z2G6 ; 0 réponse au soir du 23/11 ; relire le 24/11 matin, sinon reposter avec un angle plus direct
- [ ] Valider la liste des idées supprimées d'IDEES-MASTER.md (sauvegarde dans B2B\donnees\sauvegardes\) et trancher la section « À trancher »
- [ ] Lundi 16 : prendre les ~15 dernières lignes de la feuille de Sid (ta propre liste « Appels Liam » commence mardi 17)
- [ ] Serveur : ajouter « nettoyage-fichiers » aux agents actifs (tâche chaque jour à 03:00)
- [ ] Serveur : pour recevoir le message de 08:00, `envoi_automatique` doit être à true dans la config locale de relances (sauvegarde-leads et linkedin-equipe sont planifiés : premiers passages le 25/11 à 03:30 et 08:00, à vérifier)
- [ ] Vérifier toi-même dans la config locale B2B\agents que agents_actifs contient surveillant, appels-liam et nettoyage-fichiers (lecture refusée à Claude par la garde des secrets)
- [ ] superviseur-sites et superviseur-mail à activer quand ces domaines tourneront pour de vrai : retirer leur clé « desactive » de serveur-taches.json (la vue Jarvis ensuite, elle n'a de sens qu'avec les quatre domaines)
- [ ] Si tu veux la double sécurité, retirer toi-même superviseur-sites, superviseur-mail et jarvis-vue de agents_actifs, et passer envoi_automatique à false dans le fichier local commun des superviseurs en le laissant à true pour Vente et Prospection seulement (écriture refusée à Claude par la garde des secrets)
- [ ] Réserve neuve trop mince (334, dont 0 électricien, maçon, couvreur ou coiffeur) : liste de Sid du 17/11 prévue à 97 lignes au lieu de 100, à décider (plafond par métier ou nouvelles sources)
- [ ] Serveur : accepter la mise à jour puis ajouter appels-liam aux agents actifs (et envoi_automatique à true dans la config locale d'appels-liam pour la feuille Google)
- [ ] Envoyer SCRIPT-APPEL-SID.md à Sid (seulement celui-là ; closing et techniques restent à toi)
- [ ] Serveur : `git -C <dossier Jarvis> config core.hooksPath .githooks`, ajouter « surveillant » aux agents actifs
- [ ] Mettre l'adresse secrète iCal dans la config locale de l'agent Rendez-vous, puis dire « fait »
- [ ] Vérifier que /codex:setup a marché (sans clé API)
- [ ] Stripe : SIRET et mention TVA art. 293 B en pied de facture ; site web (encore ecom-quiz.vercel.app) et description publique
- [ ] Malt : candidats « Prospection téléphonique B2B », répondre à Eric Ling
- [ ] Facebook Normandie et Leboncoin : poster l'offre « page exemple à ton nom »
- [ ] Donner un Drive à Claude pour le prompt d'un site classique (modèle à réutiliser)

## Agents (ensuite, une étape à la fois)
- [ ] Vérifier dans Drive que « Appels Sid 2026-11-23 » existe avec 100 lignes (sinon appels-sid est encore en simulation)
- [ ] Les tests laissent des dossiers dans %TEMP% : les faire se nettoyer eux-mêmes ; 6 mentions « Répondu / Refus » gardées exprès (anciennes feuilles de Sid)
- [ ] Terminer l'étape Vente (réparer reponses.py, puis Réponses, Rendez-vous, Devis, relances des devis J+3 et J+7 ; relances des leads chauds faites le 18/11), chacun avec contrat + garde + test + fiche avant activation
- [ ] Fiches agents : 19 « à compléter par Liam » (production, vente-relances, responsables Vente / Argent / Production) à remplir avec l'étape Vente ; agents sur le serveur : relancer generer-fiches.py là-bas pour avoir les traces
- [ ] Rubrique « Historique des appels » sur le gros PC : historique-appels.json est tenu sur le serveur (hors git), le gros PC affiche « absent sur ce PC » tant qu'il n'est pas relayé (comme devis et paiements) ; à décider avec Liam
- [ ] Tableau de bord (gros PC) : lire la feuille « Chiffres serveur Jarvis » dans outils\agents-json.py (devis et paiements des jours passés de historique.json, aujourd'hui null) pour remplir les courbes Devis et Ventes — la feuille se remplit depuis le 21/11 au soir
- [ ] Faire passer la publication et le déploiement des pages exemples par la garde (non branchés)
- [ ] CEO Jarvis autonome, pont Discord de Jarvis (connecte: false) : après la 1re vente
- [ ] Production (design, code, publication) : après la 1re vente
- [ ] Tableau de bord, suite : devis et ventes du serveur dans l'historique du gros PC (feuille « Chiffres serveur », idée du 18/11 dans IDEES-MASTER, à valider par Liam) ; commissions
- [ ] Fiche d'accueil client (photos, couleurs, logo, avis, spécificités)
- [ ] Recruter d'autres call callers (15 %, jamais de closers), dont un spécialiste restaurants
- [ ] Intérim : créer les alertes sur l'espace candidat des agences, lancer `interim.py gmail-autoriser`, dire « go interim », répondre aux 4 questions du CV, déposer les 7 documents Samsic (toi-même)
- [ ] Alerte candidatures : lier le formulaire à une feuille (Réponses > Lier à Sheets), lancer `alerte-candidatures.py google-autoriser`, puis écrire « go alerte »
- [ ] Devis : à construire (hors du tableau de bord tant qu'il n'est pas livré ; tourne en simulation, reste les relances des devis J+3 et J+7)
- [ ] Enrichir TECHNIQUES-CLOSING.md avec de bonnes phrases de vente
- [ ] Liam s'entraîne au jeu de rôle des objections (« Je dois réfléchir », « C'est trop cher »)
- [ ] Sid doit faire plus d'appels par jour
- [ ] Domaine : renouvellement annuel dans Stripe (plus tard), clarifier « Playwork »
- [ ] Question jamais tranchée : `veille_mail` = bon mapping pour « agent Réponses » ?
- [ ] Parrainage (1 mois de maintenance offert) ; paiement en 3x sans frais (Alma/Floa)
- [ ] Connecteur d'écoute de réunions : nom à donner par Liam, vérifier gratuité et accord des participants
- [ ] Skills du catalogue Claude : Liam colle les noms

## Gardien de l'architecture
- [ ] Dire « go gardien » : mettre `go_gardien` à true dans `B2B\agents\gardien-config.local.json`, ajouter `gardien` à agents_actifs, puis `envoi_automatique` à true si le rapport doit partir sur Discord (la tâche est dimanche 21:00)
- [ ] Premier rapport : retirer `appels-liam` de agents_actifs s'il y est encore, décider pour `linkedin-equipe` (planifié, jamais passé) et le contrat de `sauvegarde-leads` (lit appels-liam-etat.json, retiré)

## Pas prioritaire
- [ ] Désactiver dans Stripe les anciens liens de paiement (pack 595 € et site complet à 49 €/mois), à faire par Liam ; ne pas les envoyer. Déployer les vitrines avec le nouveau prix (500 € + 29 €/mois), seulement quand un prospect visite le site agence.
