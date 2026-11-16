# Idées de Liam — agence B2B
Chaque idée est notée à la date où Liam la dit. Une idée pas encore faite reste ici en une à trois lignes ; une idée réalisée est supprimée 3 semaines après (l'historique est dans git). Réduit le 15/11/2026 (sauvegarde de l'ancienne version : `B2B\donnees\sauvegardes\IDEES-MASTER-2026-11-15.md`, hors git).

## Vente et offre
- 14/11 — Offre fondateur (3 premiers clients) : 295 € au lieu de 595 €, 49 €/mois inchangé, contre le droit de montrer le site et un témoignage vidéo de 30 s.
- 14/11 — Garantie zéro risque : « si la page ne vous plaît pas, vous ne payez rien ».
- 14/11 — Avant/après chiffré : capture du site actuel (ou de son absence) et score PageSpeed à côté de la nouvelle page.
- 14/11 — Cercle proche d'abord (ami, parent, commerçant connu) pour la 1re vente et la 1re preuve.
- 14/11 — Conditions de vente écrites (contenu du pack, durée et arrêt des 49 €/mois) et SIRET sur les devis.
- 14/11 — Stripe : nom public LM MULTI-SERVICES, SIRET et mention TVA art. 293 B ; renouvellement annuel du domaine dans Stripe plus tard ; « Playwork » : lien ou orthographe à donner par Liam.
- 14/11 — Commissions : 10 % appelant + 10 % closer (au lieu de 15 + 15) ; sur le premier paiement seulement ou aussi sur les 49 €/mois, à décider.
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
- 17/11 — Vidéos : recaler l'estimation de durée de la ligne B (histoires.duree_estimee) après une dizaine de rendus : elle se trompe encore de 4 s.

## Agents
- 27/10 — Chaîne automatique entre agents (prospection → réponse positive → rendez-vous → devis → Stripe → site → mise en ligne → maintenance), validation de Liam seulement aux points à risque.
- 14/11 — Relances J+3 et J+7 (agent le plus rentable), puis rappel de closing : devis non payé sous 48 h → alerte pour rappeler.
- 14/11 — Pré-génération de pages au nom des prospects (20 d'avance), URL prête avant l'appel.
- 14/11 — CEO Jarvis autonome après la 1re vente : lit les résultats, relances, lead chaud, devis, résumé du soir ; décisions engageantes soumises à Liam.
- 15/11 — Boîte aux lettres Liam ↔ Claude Code : B2B/docs/FILE-ATTENTE.md et RESULTATS.md, après l'étape Vente.
- 30/10 — Agent Réponses : classer comme refus les refus polis (compliments puis « non », cas LM ELEC), exclure l'adresse et prévenir Liam dans 💬-réponses (à vérifier dans reponses.py).
- 14/11 — Gabarit unique pour créer les skills (entrées, procédure, règles, critère de fin, exemples).

## Sites et pages exemples
- 24/10 — Niveau « premium » avec 3D utile en option payante, après les pages standard.
- 24/10 — Mesure sans cookie des appels et clics sur le numéro, pour montrer un résultat chiffré à l'artisan après 30 jours.
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
