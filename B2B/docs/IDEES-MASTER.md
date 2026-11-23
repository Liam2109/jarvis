# Idées de Liam — agence B2B
Chaque idée est notée à la date où Liam la dit. Une idée pas encore faite reste ici en une à trois lignes ; une idée réalisée est supprimée 3 semaines après (l'historique est dans git). Réduit le 15/11/2026 (sauvegarde de l'ancienne version : `B2B\donnees\sauvegardes\IDEES-MASTER-2026-11-15.md`, hors git).

## Vente et offre
- 14/11 — Garantie zéro risque : « si la page ne vous plaît pas, vous ne payez rien ».
- 14/11 — Avant/après chiffré : capture du site actuel (ou de son absence) et score PageSpeed à côté de la nouvelle page.
- 14/11 — Cercle proche d'abord (ami, parent, commerçant connu) pour la 1re vente et la 1re preuve.
- 14/11 — Conditions de vente écrites (contenu du pack, durée et arrêt des 29 €/mois) et SIRET sur les devis.
- 14/11 — Stripe : nom public LM MULTI-SERVICES, SIRET et mention TVA art. 293 B ; renouvellement annuel du domaine dans Stripe plus tard ; « Playwork » : lien ou orthographe à donner par Liam.
- 14/11 — Commissions : 10 % appelant + 10 % closer (au lieu de 15 + 15) ; sur le premier paiement seulement ou aussi sur les 29 €/mois, à décider.
- 14/11 — Prévoir comment livrer un site complet multi-pages avant d'en vendre un.
- 15/11 — Client sans confiance : petit acompte (~100 €) qui paie un appel de travail, site préparé sous 24 h. À décider (contredit « sans acompte »).
- 15/11 — Enrichir TECHNIQUES-CLOSING.md avec de bonnes phrases de vente.

## Prospection et appels
- 27/10 — Corriger sourcing.py (siège hors département).
- 27/10 — Résumé du matin de Jarvis : nombre de réponses positives de la veille.
- 27/10 — Clé API PageSpeed gratuite (à créer par Liam, jamais dans le dépôt) pour dépasser 30 mesures par jour.
- 27/10 — Passer l'application Google (Gmail API) en « Production » pour supprimer l'expiration du jeton à 7 jours.
- 28/10 — Tableau de bord des rebonds par boîte après une semaine d'envois.
- 14/11 — Cibler en priorité les fiches Google avec au moins 20 avis et 4,2 étoiles, sans site.
- 14/11 — Créneaux d'appel adaptés au métier (pas de coiffeurs ni de restaurants pendant le rush), en semaine seulement.
- 14/11 — Signaux d'achat : entreprises nouvellement immatriculées dans la zone (API Sirene, gratuite).
- 14/11 — Demander à Sid les phrases exactes qui ont fait dire non.
- 15/11 — Onglet « relances » dans la feuille de Liam, avec l'historique des essais de chaque entreprise.
- 16/11 — Vidéos TikTok gratuites en bonhomme bâton (Qwen local + stickfigure-pipeline-v2), 3 par jour : ligne A stickman explications → planning 15 min ; ligne B recrutement de call callers → lien en bio. Construit (Videos\, 6 agents dont marketing et nettoyage), publication en attente du « go publier » de chaque ligne.
- 16/11 — Vidéos : voix Kokoro locale en secours si edge-tts échoue (réalisée le 16/11) ; sous-titres qui évitent les personnages (pas encore faite).
- 16/11 — Vidéos : relier chaque formule d'accroche (colonne hook de journal-videos.csv) aux réservations de 15 min une fois la ligne A publiée, et garder les formules qui amènent des rendez-vous.
- 16/11 — Vidéos : Kokoro n'a qu'une voix française féminine ; si la bascule sert souvent, essayer Piper (déjà utilisé par Jarvis) pour garder une voix masculine en secours.
- 17/11 — Vidéos : demander à l'auteur de theunfinishedco (HUSS41N, sans licence) l'autorisation d'utiliser son moteur : c'était le plus beau rendu des essais.
- 17/11 — Vidéos : faire marcher Gérard d'un point à un autre et varier les décors par histoire (stick-stage le place à une marque fixe, les 2 vidéos test sont au bureau).
- 17/11 — Vidéos : raccourcir de quelques mots les sketches les plus longs (T03 a dû être accéléré de quelques % pour tenir en 35 s) ; le monteur le fait seul, mais une voix au débit naturel sonne mieux.
- 17/11 — Vidéos : écrire la série suivante (3 à 5 épisodes) dans le prochain lot ; ajouter une pièce « voiture » à stick-stage si Liam veut ce décor (aucune n'existe).
- 17/11 — Vidéos au niveau des agents B2B (contrat, garde du contenu, trace par exécution, test, skill détaillé, fiche en 4 rubriques, fiche Chaîne vidéo) : réalisée le 17/11. Suite possible : une alerte du surveillant si aucune vidéo n'arrive dans a-valider deux passages de suite.

## Agents
- 27/10 — Chaîne automatique entre agents (prospection → réponse positive → rendez-vous → devis → Stripe → site → mise en ligne → maintenance), validation de Liam seulement aux points à risque.
- 14/11 — Relances J+3 et J+7 (agent le plus rentable), puis rappel de closing : devis non payé sous 48 h → alerte pour rappeler.
- 14/11 — CEO Jarvis autonome après la 1re vente : lit les résultats, relances, lead chaud, devis, résumé du soir ; décisions engageantes soumises à Liam.
- 15/11 — Boîte aux lettres Liam ↔ Claude Code : B2B/docs/FILE-ATTENTE.md et RESULTATS.md, après l'étape Vente.
- 30/10 — Agent Réponses : classer comme refus les refus polis (compliments puis « non », cas LM ELEC), exclure l'adresse et prévenir Liam dans 💬-réponses (à vérifier dans reponses.py).
- 14/11 — Gabarit unique pour créer les skills (entrées, procédure, règles, critère de fin, exemples).

- 23/11 — Agent LinkedIn : 1 à 2 posts par jour sur ton profil, en alternance recrutement appelants/closers (15 % / 10 %) et recherche de prospects pour un site web ; sans emoji ni image ; vouvoiement ; CTA = message privé ; Claude écrit un lot de ~14 posts dans le chat, l'agent les distribue sur Discord, tu valides (✅) puis tu copies-colles toi-même. Construit le 23/11 en simulation, en attente du « go linkedin ».
- 23/11 — LinkedIn, mesurer avant d'insister : noter pendant 3 semaines quel type de post (recrutement ou prospect) amène un message privé, puis garder seulement celui qui mène à un appelant, un closer ou un rendez-vous. Les artisans locaux sont peu sur LinkedIn : les posts « prospect » risquent de ne rien rapporter.

- 23/11 — Conversation LinkedIn dédiée : une conversation neuve à chaque fois (sans historique), écrire « post LinkedIn » ou « post LinkedIn : <idée> » et recevoir 2 posts à coller ; à faire chaque jour dans la to-do ; cibles élargies à tous ceux sans site (artisans, commerçants, agriculteurs) ; closers à 15 % comme les appelants ; Discord seulement si un salon LinkedIn existe.
## Sites et pages exemples
- 24/10 — Niveau « premium » avec 3D utile en option payante, après les pages standard.
- 24/10 — Restaurant : réservation réelle (outil externe) branchée après la vente.
- 27/10 — Adapter chaque page aux couleurs et au logo de l'entreprise (style personnalisé, éviter « la patte Claude » relevée par LM ELEC le 30/10).
- 27/10 — Demander à chaque plombier client 2 vraies photos avant/après (accord écrit) ; même curseur pour électricien et plâtrier ; repli sans JavaScript si la page part en ligne.
- 27/10 — Pages exemples manquantes : couvreur, maçon, peintre, menuisier, plâtrier (chacune avec son objet signature).
- 27/10 — Vérifier les animations sur Windows (Chrome/Edge, effets d'animation activés).
- 02/11 — Boulangerie v5 : améliorer la 3D du four, retravailler la structure après l'accueil et la section contact ; plus tard, « masteriser » les sites.
- 04/11 — Le Velours (restaurant) : ajouter une vidéo en tête de page.
- 11/11 — Skill « site-premium-cinematique » à écrire après validation de luxe2 par Liam.

## Équipe
- 08/11 — Recruter d'autres appelants : Codeur.com en plus de Malt et des 2 groupes Facebook.
- 03/11 — Appelants : lien Google Meet automatique dans le planning de rendez-vous ; contact par WhatsApp (numéro à donner par Liam).
- 14/11 — Connecteur d'écoute de réunion (nom à donner par Liam) : vérifier gratuité et accord des participants.

## Jarvis, Discord et outils
- 29/10 — Discord : salons important, journal, erreurs ; catégories Autres projets (saas-ciel, quiz-artisans, tri-mail), Carrière, Contenu (idées-vidéos, scripts-cold-call, résultats).
- 29/10 — Salon vocal « 💼 Travail » : Jarvis compte le temps passé dedans et affiche jour, semaine, mois dans un salon texte.
- 29/10 — Contenu : Liam se filme pendant ses appels (jamais la voix du prospect sans accord).
- 05/11 — Serveur : sans internet 5 min → redémarrer la carte Wi-Fi, sinon le PC (1 fois par heure au plus), agents relancés seuls, alerte Discord au retour.
- 14/11 — Tableau de bord : courbes de la semaine, taux appel → RDV → devis → closing, carte de chaleur des créneaux, motifs de refus, commissions modifiables, pipeline, voyant par agent (heure de dernière exécution à ajouter dans agents-json.py).
- 14/11 — Méthode Claude Code (vidéo) : boucles avec critère de fin, sous-agents, bon modèle par tâche, /compact après chaque tâche.
- 15/11 — Obsidian en vue « espace » pour voir les agents (plus tard).

## À trancher (peut-être dépassées, à confirmer par Liam)
- 24/10 — Page d'index privée des liens de maquettes pour Liam (le tableau de bord la remplace peut-être).
- 24/10 — Mesurer le temps passé par prospect pour décider quoi automatiser.
- 26/10 — Aperçu côte à côte téléphone + ordinateur pour juger un site.
- 26/10 — Volume e-mail ~100/jour : domaine d'envoi dédié et boîtes à noms humains (plan e-mail mis de côté depuis les appels ?).
- 27/10 — Restauration rapide (56.10C) : page dédiée ou page restaurant.
- 05/11 — Listes d'appels : archiver plutôt que supprimer l'ancienne feuille, pour garder les comptes rendus de Sid.
- 14/11 — 5e responsable « Système » (l'alerte pannes reste sous Argent pour l'instant).
- 02/11 — Échecs anciens de test_prospection.py (textes de redaction.py, fiches OSM sans code postal, cmd_approuver à 3 arguments).

## Ajouts du chat 17 nov. (copie complète : IDEES-CLAUDE-CHAT.md)
- Agent événements hebdo : au moins 10 événements, 45 min max, gratuit ou pas cher, zone élargie si gros événement, envoi Discord le dimanche soir. « go événements », après les premières ventes.
- Fiverr et LinkedIn : sources de freelances/missions en plus de Malt. trustmrr.com : trouver des idées de SaaS, plus tard.
- Agents conférence, CV (modifier ses CV), contrat : plus tard, pas avant les ventes.
- Skill GitHub heydamir/unslop (CC BY 4.0, crédit à Damir Sokolovsky) pour redessiner le dashboard. « go dashboard ».
- Obsidian en 3D plus tard : système solaire, une planète = un agent/dossier, soleil bleu = Jarvis.
- Groupes Facebook (étudiants, recherche de closers) : recruter des appelants. Commission décidée : 15 % appelants et 15 % closers.
- Lettres aux restaurants avec carte de visite : abandonné. Vidéo de recrutement à filmer par Liam.
- Correctif Sid (17/11, commit 7b04941) : relecture des 3 dernières feuilles, leads chauds en alerte Discord, résumé sur toutes les feuilles modifiées.
23/11 — Agents qui se parlent : chaque événement (réponse, rendez-vous, devis, paiement) doit déclencher l'agent suivant tout seul (réponse « oui » → devis → lien Stripe → relance), Liam surveille seulement. D'abord : carte des passages de relais entre agents et des maillons manquants (lecture seule).
23/11 — TikTok = personal brand IA/automatisation, face caméra, sans objectif de vente ; une vidéo longue par jour au début ; acheteurs = téléphone + LinkedIn.

## Prix et offre (décidé par Liam le 23/11, à aligner plus tard)
- 23/11 — Prix pack environ 495 € (au lieu de 595 €) ; 29 €/mois (domaine, hébergement et petites modifications inclus) à la place de « 49 €/an + modifications payantes ». Reste à confirmer : 495 ou 500, prix du site complet, commissions sur le premier paiement seulement ou aussi sur les 29 €/mois. Scripts, devis, OFFRE-REFERENCE.json, TECHNIQUES-CLOSING et Stripe pas encore alignés. Abandonnés : offre fondateur 295 €, pages pré-générées avant l'appel, mesure des appels/clics.

## Social media
- 23/11 — Catégorie « Social media » tout à gauche du dashboard : stats TikTok et YouTube (YouTube via API gratuite, TikTok à la main), Instagram plus tard. TikTok perso : conversation « TikTok » (écrire « idée » : sujet + début, milieu, fin), vidéos faites par Liam lui-même (IA surtout, aussi soin de soi et personal brand ; ni son business ni sa vie).
- 23/11 — Chaque vidéo : un titre et une description avec les liens YouTube, TikTok et Instagram de Liam (liens à donner, dans la description) ; à ajouter à la fiche idees-tiktok.
- 23/11 — Agent type Claude Cowork (agent qui travaille seul sur le PC à partir d'un objectif), côté biz, plus tard.
