# To-do B2B — LM MULTI-SERVICES

_Mise à jour : 16 nov. 2026, 17 h 30 (le fait est supprimé ; l'historique est dans le journal et dans git)_

## Lundi 16 nov. (appels d'abord)
- [x] 07 h 35 : la feuille de Sid n'existait pas (simulation depuis le 13/11 au soir) ; corrigé, feuille « Appels 2026-11-16 » créée (100 lignes), alerte surveillant 08:15 ajoutée pour la prochaine fois
- [x] Cause du 13/11 cherchée : aucun test ni agent fautif trouvé (probablement une étape manuelle de TRANSFERT-SERVEUR.md interrompue) ; garde ajoutée dans tests\tout.ps1 pour la détecter à l'avenir
- [ ] 19 h 30 : le résumé Discord compte bien les 8 valeurs de Résultat
- [ ] Sid : lire l'accroche à voix haute, noter les phrases exactes qui ont fait dire non ; bilan Sid du 13 nov. à lui envoyer
- [ ] Vérifier dans quelques jours que les lignes reprises depuis le 13/11 obtiennent enfin un vrai Résultat (la liste ne doit plus être 100 % reprises)
- [ ] Plombier-chauffagiste, électricien, maçon, couvreur, coiffeur : réserve quasi à 0 même après un passage élargi (3 trouvés sur plus de 100 appels SIRENE) ; à surveiller, pas de solution miracle (données publiques rares pour ces métiers)

## Avant le premier devis envoyé (ça coûte une vente)
- [ ] Droit de rétractation (vente à distance), formulation d'arrêt, transfert du domaine (code chez le bureau d'enregistrement) : à faire relire
- [ ] Clause de rétractation de 14 jours dans le devis, à faire relire
- [ ] Prévoir comment livrer un site complet multi-pages avant d'en vendre un
- [ ] Décider les commissions (≈10 % appelant, 10 % closer ?) et si c'est sur le premier paiement seulement ou aussi sur les 49 €/mois
- [ ] Décider : petit acompte (environ 100 €) pour le client sans confiance ? Contredit « sans acompte » ; pas dans les scripts avant décision
- [ ] Test de cohérence : étendre aux notes docs\decisions et docs\agents (la note « Offre 595 + 49 » avait encore 990–1 490 € et « lien à créer », hors du périmètre du test) ; vérifier aussi les 3 autres notes de décision

## Liam
- [ ] Vidéos : ajouter videos-nettoyage, videos-veille, videos-scripts, videos-marketing et videos-creation à agents_actifs (3 vidéos par jour dès le 17/11, tout reste dans a-valider ; chaque agent écrit alors une trace et le surveillant le suit)
- [ ] Vidéos ligne A puis ligne B : dire « go publier » sur la première vidéo de la ligne, puis suivre Videos\README.md (playwright, connexion toi-même, essai, go_publier dans la config locale) ; rien n'est publié avant
- [ ] Vidéos ligne B : créer le compte TikTok séparé, mettre le formulaire Google en bio, renseigner `lignes.B.taux_commission` si tu veux un taux dans les vidéos (vide = « à la commission »)
- [ ] Valider la liste des idées supprimées d'IDEES-MASTER.md (sauvegarde dans B2B\donnees\sauvegardes\) et trancher la section « À trancher »
- [ ] Lundi 16 : prendre les ~15 dernières lignes de la feuille de Sid (ta propre liste « Appels Liam » commence mardi 17)
- [ ] Serveur : ajouter « nettoyage-fichiers » aux agents actifs (tâche chaque jour à 03:00)
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

## Agents (ensuite, une étape à la fois)
- [ ] Vidéos : regarder les sketchs test de la ligne B (Videos-valider6-11-17-1400 T03, 2026-11-18-1400 L01, 2026-11-19-1400 série épisode 1 avec Nadia, 2026-11-20-1400 N01 avec M. Bernard) ; pour un nouveau lot de 20 sketches, le demander à Claude dans le chat (Codex absent du serveur) puis « python Videosgents\sketches.py lot Videos\idees-nouvelles\AAAA-MM-JJ.json »
- [ ] Vidéos : faire un « publier --essai » sur chaque ligne avant le go publier, pour voir où TikTok place la case « contenu généré par IA » (le dry-run le dit)
- [ ] Vidéos : avant le « go publier », faire relever l'adresse TikTok par l'agent publication (colonne url_tiktok de journal-videos.csv, vide pour l'instant)
- [ ] Les tests laissent des dossiers dans %TEMP% : les faire se nettoyer eux-mêmes ; 6 mentions « Répondu / Refus » gardées exprès (anciennes feuilles de Sid)
- [ ] Terminer l'étape Vente (réparer reponses.py, puis Réponses, Rendez-vous, Devis, relances des devis J+3 et J+7 ; relances des leads chauds faites le 18/11), chacun avec contrat + garde + test + fiche avant activation
- [ ] Fiches agents : 19 « à compléter par Liam » (production, vente-relances, responsables Vente / Argent / Production) à remplir avec l'étape Vente ; agents sur le serveur : relancer generer-fiches.py là-bas pour avoir les traces
- [ ] Tableau de bord (gros PC) : lire la feuille « Chiffres serveur Jarvis » dans outils\agents-json.py (devis et paiements des jours passés de historique.json, aujourd'hui null) pour remplir les courbes Devis et Ventes — la feuille se remplit depuis le 21/11 au soir
- [ ] Faire passer la publication et le déploiement des pages exemples par la garde (non branchés)
- [ ] CEO Jarvis autonome, pont Discord de Jarvis (connecte: false) : après la 1re vente
- [ ] Production (design, code, publication) : après la 1re vente
- [ ] Tableau de bord, suite : devis et ventes du serveur dans l'historique du gros PC (feuille « Chiffres serveur », idée du 18/11 dans IDEES-MASTER, à valider par Liam) ; commissions
- [ ] Fiche d'accueil client (photos, couleurs, logo, avis, spécificités)
- [ ] Recruter d'autres call callers (15 %, jamais de closers), dont un spécialiste restaurants
- [ ] Intérim : créer les alertes sur l'espace candidat des agences, lancer `interim.py gmail-autoriser`, dire « go interim », répondre aux 4 questions du CV, déposer les 7 documents Samsic (toi-même)
- [ ] Alerte candidatures : lier le formulaire à une feuille (Réponses > Lier à Sheets), lancer `alerte-candidatures.py google-autoriser`, puis écrire « go alerte »
- [ ] Enrichir TECHNIQUES-CLOSING.md avec de bonnes phrases de vente
- [ ] Liam s'entraîne au jeu de rôle des objections (« Je dois réfléchir », « C'est trop cher »)
- [ ] Sid doit faire plus d'appels par jour
- [ ] Domaine : renouvellement annuel dans Stripe (plus tard), clarifier « Playwork »
- [ ] Question jamais tranchée : `veille_mail` = bon mapping pour « agent Réponses » ?
- [ ] Parrainage (1 mois de maintenance offert) ; paiement en 3x sans frais (Alma/Floa)
- [ ] Connecteur d'écoute de réunions : nom à donner par Liam, vérifier gratuité et accord des participants
- [ ] Skills du catalogue Claude : Liam colle les noms
