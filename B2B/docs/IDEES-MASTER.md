# Idées de Liam — dossier SaaS / agence B2B
Chaque idée est notée à la date où Liam la dit, sans qu'il le demande.

## Sites d'artisans (agent Dev sites)
- 21 oct. 2026 — Les sites faits jusqu'ici sont « moches ». Il veut des sites de niveau grande marque (Apple, Nvidia, LVMH) avec un peu de 3D, « mais pas trop » : l'artisan doit dire « ouais » en voyant sa maquette.
- 21 oct. 2026 — Le site doit convertir : le client final choisit CET artisan et le contacte facilement. Espaces pour des photos (artisan, chantiers, outils, véhicule), photos d'internet seulement avec licence claire.
- 21 oct. 2026 — Un lien cliquable par prospect (Vercel). Chercher des skills, plugins et connecteurs pour de meilleurs sites.
- 21 oct. 2026 — Banque de styles Refero (styles.refero.design, DESIGN.md + MCP) à évaluer pour les directions artistiques.
- 23 oct. 2026 — Objectif : en novembre 2026, produire des maquettes d'artisans de haute qualité, un lien par prospect, dans toute la France.
- 23 oct. 2026 — Outillage demandé : prompt maître (version courte et longue) ; moteur de modèles (thème de base, contenu par métier, variables par prospect) ; 3 maquettes d'électricien en 3 directions artistiques ; script CSV qui génère une maquette par ligne avec un score qualité écrit dans agents\dev-sites.md.

- 24 oct. 2026 — Nouveaux modèles : RESTAURANT (2 maquettes, mobile d'abord, boutons Réserver et Appeler, menu, avis, horaires) et COMMERCE / BOUTIQUE (3D légère, optionnelle, avec image de repli). Photos : Unsplash, Pexels ou Pixabay uniquement, licence notée dans le registre.
- 24 oct. 2026 — `prospects.csv` modèle vide (nom, métier, ville, téléphone, email, site_actuel) et test du script sur 5 lignes fictives.
- 24 oct. 2026 — Déploiement des maquettes fictives sur UN projet Vercel dédié, pages non indexées, lien difficile à deviner : Liam décide du nom du projet (réponse du 24 oct. : « pas maintenant »).
- 24 oct. 2026 — Agent SOURCING : trouver des entreprises locales dans toute la France à partir de sources publiques (annuaire officiel des entreprises, Google Maps consulté à la main, Pages Jaunes). Par prospect : nom, métier, ville, e-mail professionnel, site actuel, note de besoin. Prospection B2B conforme : message lié à l'activité, identification claire, STOP.

- 24 oct. 2026 (suite) — Déploiement des 6 maquettes fictives (3 électricien, 2 restaurant, 1 commerce) sur un projet Vercel `b2b-demos`, pages `noindex`, lien difficile à deviner ; arrêt et question si Vercel demande un choix ou un accès.
- 24 oct. 2026 (suite) — Agent RÉDACTION : par prospect, message court e-mail + LinkedIn (accroche métier et ville, ce qui manque sur son site actuel, lien de SA maquette, « Qui je suis » Liam Emo / LM MULTI-SERVICES, ligne STOP), sans faux chiffre ni promesse de classement Google ; sortie `messages-a-valider.md`, statut « à valider », aucun envoi.
- 24 oct. 2026 (suite) — Agent SUIVI : `suivi-prospects.csv` (à contacter / envoyé / répondu / maquette envoyée / devis / signé / refusé / STOP, dates, relance J+2) ; le script ne change un statut qu'à la demande de Liam.
- 24 oct. 2026 (suite) — Test complet CSV -> maquettes -> messages -> suivi sur 3 prospects fictifs.

## Idées dérivées (à valider par Liam)
- Message de relance J+2 préparé par l'agent Relances à partir de `a-relancer`, toujours à valider.
- Une page d'index privée listant les liens des maquettes pour Liam (jamais publique).
- Après un premier lot réel, mesurer le temps passé par prospect (enrichissement à la main) pour décider quoi automatiser.
- Offre « restaurant » : réservation réelle (outil externe) à brancher après la vente ; la maquette ne fait qu'une démonstration.
- Niveau « premium » avec 3D (ampoule, robinet, toit, briques) en option payante, après les maquettes standard.
- Mesure sans cookie des appels et clics sur le numéro, pour montrer un résultat chiffré à l'artisan après 30 jours.
- 24 oct. 2026 (nuit) — Déploiement fait : projet Vercel `b2b-demos`, 6 maquettes fictives en ligne, noindex, protection Vercel Auth désactivée à la demande de Liam.
- 24 oct. 2026 — Retours de Liam sur les maquettes : restaurant « bistro » VALIDÉ (ne pas modifier) ; commerce « céramique » VALIDÉ (ne pas modifier) ; restaurant « marché » À AMÉLIORER.
- 24 oct. 2026 — Demande pour « marché » : s'inspirer des principes de groupefrenois.com (hero immersif avec phrase d'ambiance, bouton Réservations fixe, section événements avec « Demander un devis », histoire du lieu, ton chaleureux), garder le thème clair, même checklist qualité (Lighthouse, 390 et 1280 px, console, accessibilité), montrer les captures avant/après, ne déployer qu'après son OK.
- 24 oct. 2026 — Nouveau modèle RESTAURANT/GROUPE « premium » (inspiré des principes de groupefrenois.com, sans rien copier) : hero immersif avec phrase d'ambiance, une carte par maison/adresse, bouton Réservations fixe, événements/privatisations avec « Demander un devis », histoire du lieu, fidélité, recrutement, pied de page avec adresses et téléphones. Données « exemple », photos libres avec licence notée. Pas de déploiement sans son OK.
- 26 oct. 2026 — Deux offres sur le même moteur : « landing page pro » (1 page) et « site complet » (3 à 5 pages), avec options nom de domaine/DNS, e-mail pro et maintenance. Brouillon dans `docs\OFFRES-SITES.md` ; prix et feu vert de construction à décider par Liam.
- 26 oct. 2026 — Objectif : première vente de site cette semaine. Parcours : prospection par e-mail + LinkedIn (jamais d'appel à froid, jamais d'envoi sans OK par lot), puis appel de 15 min avec le prospect qui répond, puis devis, puis paiement Stripe.
- 26 oct. 2026 — Offres retenues par Liam : landing page pro 590 € ; site complet 990 à 1 490 € ; domaine/DNS 40 € + prix coûtant (domaine au nom du client) ; e-mail pro ; maintenance 29 à 49 €/mois.
- 26 oct. 2026 — À faire : compte Gmail de prospection dédié (montée 20 -> 100 envois/jour), remplir `agents\identite.json` (SIRET, téléphone, e-mail), premiers vrais prospects, devis type et réponses aux objections.
- 26 oct. 2026 — Règle : rien d'envoyé, déployé ni dépensé sans l'accord de Liam.
- 26 oct. 2026 — Changement de méthode : PAS une maquette par prospect (trop long, trop de crédits). Une page modèle par métier, liée dans le message ; prospection dans TOUTE la France, pas seulement Rouen. Le prospect qui dit oui -> appel, devis, Stripe.
- 26 oct. 2026 — Volume : maximiser les envois, 3-4 adresses d'envoi pour atteindre environ 100 e-mails/jour au total, tous les jours sans s'arrêter. Agents qui listent les prospects chaque jour, suivent les réponses et arrêtent d'écrire à ceux qui refusent (STOP / refusé). Tout automatisé, validation par lot conservée.
- 26 oct. 2026 — Objectif : première vente d'une landing page à 590 € cette semaine. Aucun envoi, déploiement ou dépense sans OK de Liam.
- 26 oct. 2026 — Lot 1 : `prospects_rouen.csv` (2 113 lignes) n'a ni téléphone, ni note, ni avis, ni e-mail : les critères (note >= 4, >= 10 avis, e-mail pro avec source) ne s'y appliquent pas. Lot partiel de 10 prospects issus de `prospects_maps.csv` (fiches Google Maps relevées à la main), `lots\lot1.csv` ; maquettes locales, QA 98/100, brouillons dans `messages-a-valider.md`, suivi initialisé. Aucun e-mail, donc 20 prospects impossibles sans enrichissement manuel.
- 26 oct. 2026 — `docs\DEVIS-ET-OBJECTIONS.md` : devis type landing 590 € (1 série de retouches incluse), options domaine/DNS 40 € + prix coûtant, e-mail pro, maintenance 29-49 €/mois, script d'appel 15 min, 8 objections. Aucun lien Stripe créé ; délai, acompte, TVA, rétractation marqués « à confirmer ».
- 26 oct. 2026 — Les 3 sites d'électricien actuels sont jugés « moches » : Liam demande une recherche pour des sites premium (animations au scroll, 3D éventuelle). Recherche faite : un seul thème réutilisable piloté par un fichier de variables par prospect ; 3 directions pour l'électricien : A « Atelier Lumière » (ampoule à filament, chaleureux), B « Schéma » (schéma électrique SVG qui se dessine), C « Courant continu » (typographique, interrupteur, sans 3D). 3D facultative et chargée à la demande. Choix de la direction à construire en premier : à décider par Liam.
- 26 oct. 2026 — Point bloquant noté : prospects_rouen.csv n'a ni e-mail, ni téléphone, ni note ; il faut une source d'e-mails publiés pour atteindre 100 envois/jour.
- 26 oct. 2026 — Retour de Liam sur « Atelier Lumière » : correct mais trop simple et pas assez animé, surtout sur mobile. v3 faite (animations pilotées par le scroll y compris mobile, curseur avant/après, bandeau défilant, chiffres animés depuis les variables, galerie, carte-schéma de zone, engagements). Vidéos de démonstration 390x844 et 1280x800 dans sites/sorties/videos/. Décision technique : scripts d'animation chargés après le premier affichage pour garder le LCP sous 1,5 s. Non déployé, attente de l'OK de Liam.
- 26 oct. 2026 — Liam autorise le déploiement de la v3 « Atelier Lumière » au même lien que la v2 : https://b2b-demos.vercel.app/atelier-lumiere-exemple-d80eb712/ (noindex, Lighthouse mobile 100/100/100/100, LCP 1,4 s). Déployée depuis une copie hors dépôt Git (blocage Vercel sur l'auteur du commit). Aucune autre page modifiée.
- 26 oct. 2026 — SIRET de LM MULTI-SERVICES donné par Liam et inscrit dans agents\identite.json (téléphone et e-mail de réponse encore vides). Il veut que Claude fasse les recherches web pour le bon e-mail de prospection, puis qu'on crée les adresses d'envoi avec des noms (prénom.nom). Règle permanente : toujours lui montrer un bel aperçu (boîte de réception sur téléphone + message ouvert) avant tout envoi.
- 26 oct. 2026 — Site vitrine de l'activité de Liam (sites pour artisans et commerces) créé dans sites/agence/ (séparé des maquettes) : accueil (hero, offres 590 € / 990 à 1 490 € / options, déroulé en 4 étapes, 3 exemples en lien vers b2b-demos, à propos, zone toute la France à distance, FAQ, contact), mentions légales (hébergeur Vercel) et confidentialité (section « Prospection et droit d'opposition : répondez STOP »). Ton « je », seul, sans âge, sans faux chiffre ni avis ni logo ni promesse Google. DA sobre : graphite + vert profond, Bricolage Grotesque + Hanken Grotesk, sans JS ni cookie, CSP stricte. Téléphone, e-mail, forme juridique, adresse, TVA : « À COMPLÉTER » affiché. Noindex tant que le domaine n'est pas branché. Lighthouse mobile 100/100/100/100 sur les 3 pages. Non déployé, attente de l'OK de Liam (nouveau projet Vercel).
- 26 oct. 2026 — Liam veut que le site de l'agence soit futuriste, « à 20 000 dollars », style Dubaï (fond skyline de Dubaï), avec de la 3D et beaucoup d'animations. Il ne veut pas que Claude (chat) code le site : Claude Code le construit, via un prompt. Le site sobre actuel (sites\agence\index.html) reste en secours.
- 26 oct. 2026 — Liam : « au pire tu me fais un site pour le web qui fait sérieux » : site vitrine pour son activité de création de sites (agence). Il garde le domaine lmlsmulti-services.com et choisit de remplacer le site de débarras actuel (précautions : sauvegarde, prévenir Léo, republier le débarras sur un sous-domaine).
- 26 oct. 2026 — Idée de Liam : créer des SKILLS Claude à donner aux agents pour qu'ils conçoivent de bons sites sans qu'on répète les consignes, un skill adapté par domaine/métier.
- 26 oct. 2026 — Consignes de Liam pour les skills : skill 3D et animation légère avec version mobile, du RÉALISME partout ; pas seulement des artisans (coiffeurs, fleuristes, etc.) : un modèle designé par type d'activité ; AUCUN PHP (jugé peu sûr), sites statiques ; des sites qui CONVERTISSENT (pas seulement beaux) ; des sites différents de ceux que font les IA habituelles ; plus tard, des sites vraiment sur mesure pour chaque client.
- 26 oct. 2026 — Skills enregistrés par Liam : site-local-conversion, site-local-animation-3d, site-local-direction-artistique (« local » = sites de commerces et artisans locaux). À proposer ensuite : familles d'activités, sécurité sans PHP, qualité et livraison. Copie des fichiers dans B2B\skills\ pour Claude Code (.claude\skills\ ne peut pas être écrit à distance).
- 26 oct. 2026 — Règle de Liam : ne JAMAIS afficher son lieu d'habitation ni une adresse personnelle dans un site (ni dans les maquettes ni dans le site de l'agence) ; zone d'intervention de l'artisan seulement.
- 26 oct. 2026 — Liam veut un aperçu avec une vue téléphone ET une vue ordinateur côte à côte, plus beau que le panneau de droite habituel, pour juger tout de suite la qualité d'un site.

- 26 oct 2026 (soir) : agent Prospection automatisé : trouve les entreprises (Google, sites), cherche un e-mail sur leur site (mentions légales/contact) ; sans e-mail, trouve Facebook ou LinkedIn et prépare le message. Création des boîtes e-mail : demain (27 oct).
- 26 oct 2026 : les sites manquent encore d'animation : renforcer via le skill site-local-animation-3d. Nouveau skill site-local-references (Refero : s'inspirer des meilleurs sites par métier, adapter sans copier, pas de banderole en haut de page).
- 26 oct 2026 : téléphone et e-mail de contact enregistrés dans agents\identite.json.

- 26 oct 2026 (soir) : agent Réponses (agents/reponses.py) : lit en IMAP, en lecture seule, les réponses des prospects connus (suivi-prospects.csv) sur les 2 boîtes Gmail, les classe par règles (positive / négative / STOP / autre ; doute = autre), poste les positives sur Discord (salon paiement) avec 2 créneaux de 15 min de l'agenda Google (non réservés), et met le statut répondu / refusé / STOP. Ne répond jamais au prospect. Option --test (faux message, aucun statut) ; idempotent (reponses-traitees.json). À configurer : mots de passe d'application Gmail et lien iCal secret dans B2B/.env, identifiant du salon dans agents/reponses-config.json.

- 27 oct 2026 : agent Prospection créé (agents/prospection.py, tests, prospection.md). Chaîne quotidienne : réponses -> recherche (annuaire, site, e-mail publié, Facebook/LinkedIn) -> lot de 10 par boîte -> relance J+2 unique -> envoi des seuls blocs « validé ». À blanc par défaut pour tester. Idées : (1) déployer les maquettes du lot seulement après ton OK, sinon le lien est refusé à l envoi ; (2) modèle de maquette plâtrier ; (3) corriger sourcing.py (siège hors département).

- 27 oct 2026 : agent Prospection intégré à Jarvis (lib/prospection.ps1, prospection_actif, désactivé par défaut) : lot du jour posté sur Discord, envoi seulement après « ok lot » / ✅ de Liam, envoi_automatique=false par défaut. Idée : lier le résumé du matin de Jarvis au nombre de réponses positives de la veille.

- 27 oct 2026 : page modèle plombier-chauffagiste créée (direction « Eau & cuivre », exemple fictif noindex, non déployée) : hero goutte au bout d un tuyau de cuivre, vanne qui se ferme au scroll, un seul bouton Appeler, aucune banderole, aucune photo (zones à remplacer). Idées : (1) trouver 3 photos libres de plomberie avec licence vérifiée pour un second niveau de réalisme ; (2) lien de maquette plombier dans les messages de prospection une fois déployé avec l accord de Liam ; (3) modèle équivalent pour couvreur et maçon avec leur objet signature.

- 2026-10-27 : page exemple plombier jugee 6/10 par Liam (correcte mais pas de photos animees, pas d avant/apres, couleurs banales). 3 skills crees : site-local-signature-interaction, site-local-palette-signature, site-local-notation-wow. Refaire la page plombier avec avant/apres + palette cuivre/vert-de-gris + note sur 10 avant de montrer.

- 27 oct 2026 (suite) : page plombier refaite après la note 6/10 de Liam (non déployée, noindex). Palette « Vert-de-gris & cuivre » (#1F4A45 / #F4F1EA / #9A4F25), pipette sur les photos ; curseur avant/après sur la salle de bain (souris, doigt, clavier, mouvement réduit) ; zoom lent du hero et révélation de la photo du radiateur au scroll. Décision de Liam (option 2) : aucune vraie paire avant/après libre de droits n'existe, donc « Avant (simulé) » = la photo Pexels « après » vieillie par sites/outils/avant-simule.mjs, étiquetée « simulé » + « Illustration » ; photo source et traitement notés dans CREDITS.json et registre-licences.md ; remplacement par les photos de l'artisan = 2 chemins dans plombier.json (img_avant, img_apres). Note wow 9/10 (photos 1/2 à cause de l'avant simulé). Lighthouse mobile 99/100/100/100, LCP 2,0 s, CLS 0. Idées : (1) demander à chaque futur plombier prospect 2 photos avant/après de son chantier (accord écrit) : c'est le meilleur argument de vente de la page ; (2) même curseur pour l'électricien (tableau) et le plâtrier ; (3) le curseur n'a pas de repli sans JavaScript : à ajouter si une page réelle part en ligne.

- 27 oct 2026 (Gmail API) : envoi et lecture des e-mails branchés sur l'API Gmail (OAuth « application de bureau ») à la place d'IMAP/SMTP, car contact.lmsite@gmail.com est refusé par Google. Nouveau : agents/gmail_api.py (flux installed-app, jeton agents/gmail-token.json, portées gmail.send + gmail.readonly seulement), agents/test-gmail-api.py (autorisation une fois, affiche « OK, adresse = … », n'envoie rien, inscrit l'adresse dans reponses-config.json › api › adresse), agents/test_gmail_api.py (sans réseau). prospection.py : mode api = un seul expéditeur (l'adresse autorisée), mêmes protections (bloc « validé » + approbation Discord, 10/jour, pauses 90–300 s, lien en ligne, STOP, signature) ; reponses.py : même classement et mêmes alertes Discord, lecture en-têtes d'abord. « api »: {"actif": false} = repli IMAP/SMTP. Jeton expiré (mode Test, 7 jours) : message « relance python agents/test-gmail-api.py », envoi/lecture sautés, le reste continue. Installation : pip install google-auth-oauthlib google-api-python-client. Idées : (1) passer l'application Google en « Production » (usage perso, portées sensibles sans validation pour moins de 100 utilisateurs) supprime l'expiration à 7 jours ; (2) un seul expéditeur = 10 e-mails/jour au lieu de 20 : ajouter une 2e adresse seulement si besoin ; (3) les blocs « à valider » déjà préparés avec l'ancienne boîte seront refusés à l'envoi : les régénérer.

- 27 oct 2026 (Gmail API, 2 boîtes) : l'API Gmail gère maintenant une liste de comptes (reponses-config.json › api › comptes : liamdigital2109@gmail.com et contact.lmsite@gmail.com), même client OAuth, un jeton par compte (agents/gmail-token-<adresse>.json, ajouté à .gitignore ; l'ancien gmail-token.json de liamdigital2109 a été renommé sans être lu). Envoi : chaque boîte a ses 10 envois/jour, le nom affiché reste « Liam Emo », les lots sont répartis entre les boîtes autorisées, un prospect n'est contacté que depuis UNE boîte (contrôle à l'envoi et dans le lot) et la relance part de la boîte du premier message. Lecture : les deux boîtes, la boîte réceptrice est indiquée dans l'alerte #business. test-gmail-api.py <adresse> autorise ce compte seul (vérifie que le compte autorisé est bien celui demandé avant d'enregistrer le jeton) ; sans argument il teste les comptes déjà autorisés. Une boîte sans jeton valide est sautée (message « relance python agents/test-gmail-api.py <adresse> »), l'autre continue. Reste à faire par Liam : python agents/test-gmail-api.py contact.lmsite@gmail.com. Idée : les blocs « à valider » préparés avant l'ajout de la 2e boîte restent sur la 1re ; les lots suivants se répartissent seuls.

- 27 oct 2026 (lot périmé remplacé) : le lot posté dans #business venait de l'ancien messages-a-valider.md (expéditeur contact.lmsite@ inexistant, maquette sarl-itc-bati non en ligne). Corrigé : contact.lmsite@ → contact.lmsites@ dans agents\ (reponses-config.json, reponses.py, scripts de test Gmail, compteur de lot de prospection-etat.json) ; les journaux et les lignes d'historique ci-dessus restent tels quels. Ancien messages-a-valider.md et apercu-lot.html archivés dans lots\archives\ (suffixe -perime). Nouvelle règle dans prospection.py preparer : le lien d'un message est la page exemple du métier (agents\liens-metiers.json, vérifiée en ligne = 200, mention « exemple, pas votre site ») tant que les maquettes personnalisées ne sont pas déployées ; sans page exemple en ligne pour son métier, le prospect n'entre pas dans le lot. La commande affiche le nombre de prospects par canal (e-mail / Facebook / LinkedIn) et « LOT VIDE : aucun e-mail utilisable » plutôt que de produire un lot vide. Résultat du jour : 7 prospects (tous électriciens, 1 e-mail, 5 Facebook, 1 LinkedIn), aucune page exemple électricien en ligne (seul plombier-chauffagiste existe) → lot vide, rien posté ni envoyé. À faire : page modèle électricien (skill page-modele-metier) puis son lien dans liens-metiers.json.

- 2026-10-27 (Liam) : (1) prospecter TOUS les metiers sans site web (fleuristes, coiffeurs, restaurants, etc.), pas seulement plombiers et electriciens : plus de probabilite d'achat. Il faut une page exemple par metier en ligne (a faire a la chaine). (2) Les animations doivent etre verifiees sur Windows (environ 60 % des visiteurs) : tester Chrome/Edge Windows avec effets d'animation actives, et prefers-reduced-motion gere ; chercher des sources d'animations libres (Lottie, CSS, GSAP deja present). Sur le PC de Liam les animations Windows sont coupees : les reactiver pour juger. (3) Argument de vente : on vend la VISIBILITE (etre trouve, etre contacte), pas le site web. Sans promesse de classement Google. Idee a noter dans la to-do : page exemple par metier + test Windows.

- 27 oct 2026 (page plombier, animations) : eau.css renforcé (CSS natif, transform / opacity / translate seulement, donc CLS 0) : texte du hero qui monte élément par élément, parallaxe léger du hero et des photos du dépannage et du chauffage (propriété translate, indépendante du zoom et de la révélation), apparitions décalées dans les listes, détail propre au métier : le filet de chaque geste, étape, engagement et bloc chauffage « se met en eau » de cuivre au scroll ; retour net au survol (boutons, besoins, communes, photos, blocs). prefers-reduced-motion respecté (0 animation, tout visible). Vérifié avec reducedMotion no-preference (61 animations) et reduce (0). Lighthouse mobile 98 / accessibilité 100 / SEO 100, CLS 0, LCP 2,1 s ; bureau 100. Vidéos du défilement : sites\sorties\plombier-exemple\animation\ (390x844 et 1280x800, console vide). Rien déployé. Pas encore fait : pages exemple coiffeur, fleuriste, restaurant, garage, boulangerie, couvreur, maçon, peintre (partie B) et recherche élargie aux métiers à page exemple (partie C).
- 27 oct 2026 (prospection en continu) : prospection.py continu --pid <Jarvis> (lancé une fois par session par lib\prospection.ps1, processus caché séparé). Un cycle toutes les cycle_minutes (10) : réponses (1 h au plus), recherche, lot, relance (1 par jour), publication Discord dès lot_min_emails (5) e-mails prêts ou fin de quota, approbation, envoi (pauses 90-300 s, plafond 10 par boîte et par jour inchangés). Quota du jour = quota_par_boite (10) x boîtes autorisées (20 avec deux boîtes), plafonné par par_boite_par_jour. Recul exponentiel après une erreur (10, 20, 40 puis 60 min au plus). État repris après redémarrage (prospection-etat.json › continu). Fin de journée (quota envoyé, prospects éligibles épuisés après epuise_apres recherches vides, ou plus rien à valider) : veille jusqu'au lendemain et une ligne dans prospection-dernier-lancement.txt (trouvés, préparés, validés, envoyés, bloqués, raison). Arrêt aussi si Jarvis s'arrête. envoi_automatique est forcé à false en mode continu : rien ne part sans « ok lot » / ✅ de Liam. Secours : python agents\prospection.py arreter. Tests hors ligne dans agents\test_prospection.py (quota, cadence, recul, épuisement, reprise, arrêt) ; tests\prospection.ps1 vert.

- 2026-10-27 (Liam) : (7) AGENT DEVIS : des qu'un call se termine par « on valide », un agent redige le devis (modele a faire), le soumet a Liam, puis genere le lien Stripe (acompte 30 % puis solde avant mise en ligne) ; liens crees le 27 oct, voir docs\liens-paiement.md. (8) AUTOMATISER LA CHAINE ENTRE LES AGENTS pour que Liam ne soit pas le relais : prospection -> leads -> reponse positive -> call (creneaux) -> devis -> Stripe -> creation du site -> mise en ligne -> maintenance. Un evenement dans un agent declenche le suivant, avec une validation de Liam seulement aux points a risque. (9) DISCORD : creer plus de salons, ranges par agent (B2B: prospection, leads, devis, paiements, sites ; autres: annonces train, etc.), car « business » est trop vague. A faire plus tard, Liam envoie un resume. (10) Nom de domaine : le prix depend du domaine (environ 19,90 EUR l'an evoque par Liam) ; a trancher plus tard.

- 2026-10-27 (Liam) : (4) calendrier de reservation pour le site agence de luxe (prise de rendez-vous, creneaux de 15 min, relie a l'agenda) : a cadrer. (5) L'e-mail de reponse officiel est contact.lmsites@gmail.com (avec un s) : emoliam255@gmail.com remplace partout dans les messages et signatures ; liamdigital2109@gmail.com est la 2e boite d'envoi. (6) Rappel : IDEES-MASTER.md a ete ecrase par un outil ; version restauree a partir de la derniere copie complete (ajouts de Claude Code et de Liam conserves).

- 2026-10-27 (Liam, retours page plombier en ligne) : (11) adapter chaque page aux couleurs de l'entreprise du prospect (logo/charte) en plus de la palette du metier ; (12) le curseur avant/apres ne marche pas chez Liam sur la page en ligne (a diagnostiquer : navigateur, souris/doigt) ; (13) pas d'effet de scroll marquant sur la version en ligne (la version renforcee n'est pas deployee) ; (14) des sections 'bizarres' vers le milieu de la page, a preciser avec une capture.

- 2026-10-27 (Liam, avis sur les pages) : les 3 pages electricite (premium, famille rassurant, technique) sont jugees tres bonnes ; bistro, ceramique, marche : correctes. (15) PAGE RESTAURANT : hero anime ou en video (idee : un mouvement vers le four, flammes/braises/vapeur), puis au scroll des photos de plats typiques qui donnent envie, puis une CARTE vraiment propre (sections, prix, lisible sur telephone, allergenes). Video libre de droits a licence notee, sinon animation CSS/GSAP. Plats et prix fictifs signales comme exemple.

- 2026-10-27 (Claude Code) : PROSPECTION ELARGIE aux commerces et restaurants. NAF ajoutes : 56.10A, 56.10C (restaurant), 96.02A (coiffeur), 47.76Z (fleuriste), 10.71C et 10.71D (boulangerie, patisserie), 45.20A (garage). Regle : un metier n'entre dans la recherche que si agents\liens-metiers.json contient sa page exemple (cles : electricien, plombier-chauffagiste, restaurant, coiffeur, fleuriste, boulangerie, garage) ; actifs aujourd'hui : electricien, plombier, restaurant. Les autres s'activent seuls a l'ajout de la ligne. Textes de message propres a chaque metier (restaurant : carte, horaires, acces, reservation ; pas de « panne » hors batiment). A FAIRE : pages exemple coiffeur, fleuriste, boulangerie, garage avant toute prospection de ces metiers ; la restauration rapide (56.10C) reutilise la page restaurant, a juger (page plus adaptee ?).
- 2026-10-27 (Claude Code) : PAGE RESTAURANT « Braise » (direction braise, feu de bois) : hero photo de four + braises/lueur/vapeur en canvas sur ordinateur (aucune video : 0 Ko de video), image fixe 4:5 sur mobile et mouvement reduit ; six grandes photos de plats empilees au scroll ; carte HTML avec navigation collante, prix alignes, allergenes sous chaque plat. Plats, prix, adresse, horaires fictifs signales « exemple ». Licences dans sites\moteur\photos\CREDITS.json (Pexels). Lighthouse mobile 99/100/100/100. Non deployee. IDEE : brancher cette page sur « restaurant » dans liens-metiers.json si Liam la prefere au bistro.
- 2026-10-27 (Claude Code) : STRUCTURES VARIEES (skill site-local-structure-variee). sites\moteur\STRUCTURES.md decrit les 5 pages sur les 6 axes et fixe d'avance la structure des pages a venir (coiffeur, fleuriste, boulangerie, garage, couvreur, maconnerie, peintre ; chaque page differe des deux precedentes sur au moins 4 axes, controle par script). Plombier refait : hero partage 50/50 avec le curseur avant/apres, en-tete reduit a Appeler + Devis, cartes a defilement horizontal, frise horizontale, sections denses. Braise refaite : menu lateral fixe sur grand ecran, carte editoriale a 2 colonnes (titre et categories collees a gauche). Captures pleine page cote a cote : sites\sorties\structures\planche-390.png et planche-1280.png (node sites\outils\structures-captures.mjs). Lighthouse mobile : plombier 99/100/100/100, Braise 99/100/100/100. Rien deploye ; electricien, bistro et ceramique non touches. IDEE : les pages deja EN LIGNE (plombier, electricien) gardent l'ancienne forme tant que Liam n'a pas valide la nouvelle ; a decider quelle version remplace laquelle dans liens-metiers.json.
- 2026-10-27 (Claude Code) : PROSPECTION, passe unique : (A) un curseur par code NAF (curseurs_naf) au lieu de departement par departement, repartition par metier actif (un tiers chacun, batiment et commerce en alternance), pages vues et progression conservees ; (B) constats verifiables elargis (https, certificat, viewport, PageSpeed mobile du jour, (c) ancien, Flash, tableaux, carte en erreur, page lente ou lourde), adresses masquees (Cloudflare, arobase, schema.org), canal « formulaire de contact » compte a part (message a coller a la main), max_examinees 300 avec recul si l'API refuse, rapport par metier et par constat (commande : python agents\prospection.py rapport). A SURVEILLER : le goulot reel apparaitra apres quelques passages ; PageSpeed sans cle est plafonne a 30 mesures par jour (une cle API gratuite augmenterait le quota, a creer par Liam, jamais dans le depot).

- 2026-10-27 (Claude Code) : INTERFACE SIGNATURE (skill site-local-interface-signature) appliquee a Braise (ardoise, pelle a pizza, braise), plombier (tuyau de cuivre, vanne, ecrou, goutte), electricien (modules de disjoncteurs, interrupteur a bascule, bornier, plaque jaune vissee, gaine) et bistro (nappe, jeton de caisse, ticket perfore, fil rouge, tampon) ; ceramique inchangee. Univers ecrit dans sites\moteur\STRUCTURES.md. Controle automatique : node sites\outils\interface-controle.mjs <pages> (captures recadrees navigation + boutons dans sites\sorties\interface\, contraste mesure sur les pixels autour du texte, zones tactiles 44 px, focus clavier, mouvement reduit, Lighthouse mobile). Correctifs de conformite faits en route : largeur tactile des liens du bistro, transitions coupees en mouvement reduit, texte du bouton Devis du plombier. A SURVEILLER : le test Lighthouse de l'electricien (accessibilite 96) tombe sur un paragraphe dont l'opacite est animee par GSAP (contraste 4,49 pendant l'apparition) ; pas touche, animation conservee.
- 2026-10-27 (Claude Code) : QUATRE NOUVELLES PAGES EXEMPLES (locales, non deployees) : coiffeur, fleuriste, boulangerie, garage automobile, avec la structure prevue, la palette tiree de la matiere du metier, une interaction signature, 6 a 11 photos Pexels par page (licences dans sites\moteur\photos\CREDITS.json), et l'interface signature. Lighthouse mobile : coiffeur 99/100/100/100, fleuriste 99/100/100/100, boulangerie 98 a 99/100/100/100, garage 98 a 99/100/100/100. Notes (grille site-local-notation-wow, auto-evaluation) : coiffeur 9, fleuriste 9, boulangerie 9, garage 9 ; points faibles : coiffeur sans photo au-dessus de la ligne de flottaison (hero typographique voulu), fleuriste sans visage ni mains en action au catalogue, boulangerie dont la fournee « ouvert maintenant » repose sur des horaires inventes, garage dont les prix sont des exemples. IDEES : (1) deployer ces quatre pages quand Liam a valide l'apercu (repartir de l'etat reellement en ligne, comme pour Braise) puis ajouter les cles coiffeur, fleuriste, boulangerie, garage dans agents\liens-metiers.json pour activer la prospection de ces metiers ; (2) une cle API PageSpeed gratuite pour la prospection (jamais dans le depot).

- 2026-10-27 (Liam) : Coiffeur : pas de réservation en ligne, les salons ont déjà leur appli. La page sert à être trouvé, montrer le travail, appeler ou écrire.

- 2026-10-27 (Claude Code) : COIFFEUR REFAIT sans reservation (voir la note de Liam ci-dessus) : hero « ciseaux qui coupent » (photo de salon sombre, ciseaux qui decoupent COUPE. COULEUR. SOIN. un mot a la fois), galerie du travail qui defile au scroll, plan dessine et itineraire, avis en zone modele, contact appeler/ecrire. Lighthouse mobile 99/100/100/100, LCP 1,5 s, CLS 0. Une mesure isolee est tombee a 92 (TBT 354 ms) pendant que la machine etait chargee ; deux autres mesures a 99. Captures : sites\sorties\local\coiffeur\ et sites\sorties\interface\coiffeur.png. Photos : la photo du salon est recadree pour ecarter une personne visible dans le reflet du miroir. IDEE : si Liam veut un avant/apres, il faudra de vraies photos du salon (meme cadrage) ; aucune paire libre de droits n'a ete trouvee.

28 oct. 2026 - Prospection : un lot par boite et par jour (2 messages Discord au plus), poste quand le quota du palier est atteint ou a 17 h (heure de Paris) en lot incomplet ; un "ok lot" par lot ; score de faiblesse du site (0-100, seuil reglable) ; montee en charge 10 puis +10 par jour jusqu'a 50, gelee et signalee si les rebonds ou plaintes montent ; decouverte OpenStreetMap (ODbL, voir docs\SOURCES-DONNEES.md) et liste d'appels sans envoi de SMS. IDEE : un tableau de bord des rebonds par boite apres une semaine d'envois.

## 2026-10-29 - Serveur Discord de Liam (organisation)
- Catégories prévues : TABLEAU DE BORD (avec Jarvis System), B2B, Autres projets (SaaS), Carrière, Contenu.
- Tableau de bord = Jarvis System : salons existants -jarvis (discussion), -système, -business, annonces-train, paiements, résumé-du-jour ; à ajouter : important, journal, erreurs.
- B2B : lots, réponses, rdv, appels-du-jour, devis, paiements, livraisons.
- Autres projets : idées, un salon par SaaS (saas-ciel, quiz-artisans, tri-mail).
- Contenu : idées-vidéos, scripts-cold-call, résultats.
- Idée : cold call en parallèle des e-mails, 10 entreprises sans site par jour avec numéro, le reste en réserve, refus = exclusion permanente ; Liam se filme (sans enregistrer la voix du prospect sans accord).

29 oct. 2026 - SERVEUR 24/7 (note de préparation, rien à changer ni à envoyer pour l'instant)
Contexte : Liam utilise un petit PC portable (celui de Mathéo, avec carte Wi-Fi) comme serveur allumé en continu pour Jarvis et le service « Radiant 4 ». Les agents B2B pourront y tourner à terme.
- Doit tourner sur le serveur 24/7 : Jarvis (cerveau, voix, veille, pont Discord) ; service « Radiant 4 » ; agents B2B sans envoi : sourcing et découverte (annuaire, OpenStreetMap, Google Places), génération des maquettes, rédaction des brouillons, suivi des prospects, liste d'appels ; mise à jour des salons Discord (résumé du jour, journal).
- Reste sur le PC principal de Liam : envoi des e-mails (boîtes contact.lmsites@gmail.com et liamdigital2109@gmail.com, jetons OAuth gmail-token-*.json), validation par lot (« ok lot » ou ✅ de Liam dans 📦-lots), lecture des réponses Gmail, secrets (B2B\.env, Jarvis\.env), cold calls.
- Règles à respecter pour la bascule : un seul écrivain à la fois sur prospection-etat.json et messages-a-valider.md (sinon une machine écrase l'autre, déjà arrivé) ; une seule boucle d'envoi à la fois (verrou prospection-continu.verrou) ; aucun secret copié sans accord de Liam ; envoi automatique toujours désactivé, rien ne part sans « ok lot ».
- A décider plus tard : où vivent les fichiers partagés (état, messages, config), comment le serveur transmet les lots au PC principal, démarrage automatique du serveur, sauvegardes, accès à distance (sans payer, solutions gratuites uniquement).



## 2026-10-29 — Salon vocal « Travail » + chrono Jarvis
- Idée de Liam : dans le serveur Discord, un salon vocal « 💼 Travail ». Quand il s est dedans, Jarvis compte le temps passé.
- Un salon texte en dessous affiche : temps du jour, de la semaine, du mois, avec totaux propres (ex. « Aujourd hui : 7 h »).
- Pistes : événements voice_state_update du bot, enregistrement début/fin dans un JSON, message épinglé mis à jour, bilan hebdo/mensuel, gestion des coupures (AFK = pause).
- Statut : idée notée, rien codé.


## 2026-10-30 — Sites exemples : style personnalisé par entreprise
- Retour du 1er artisan qui a répondu (LM ELEC) : il a félicité l approche mais a reconnu « la patte Claude » dans l exemple de site.
- Liam : contours, couleurs et formes trop génériques ; il faut un style personnalisé par entreprise. Les sites sont faits par Claude Code (le chat relie les skills et donne les prompts).
- Piste : chaîne de skills site-local (références, direction artistique, palette, interface, structure, photos, interaction signature, note ≥ 8/10) ; page pilote coiffeurs à lancer dans Claude Code.

## 2026-10-30 — Réponses prospects : classement automatique
- Liam veut que le passage en « refusé » soit automatique dans Jarvis, sans qu il ait à le dire.
- Cas LM ELEC : refus poli avec compliments, classé « autre » à tort. Il faut classer ces refus déguisés comme négatifs, exclure l adresse et le nom automatiquement, et prévenir Liam dans 💬-réponses.

## À reprendre plus tard : échecs anciens de agents	est_prospection.py (relevés le 02/11/2026, sans lien avec les vagues)
- Lignes 387, 391, 466 : textes de rédaction (redaction.py) qui ne correspondent plus aux assertions (boulangerie/coiffeur sans « panne », électricien avec « zone d'intervention », phrase « je n'ai pas trouvé de site à votre nom »).
- Lignes 417 et 530-538 : fiches OpenStreetMap avec une commune mais ni code postal ni coordonnées (« Elbeuf », « Rouen ») : rejetées par la règle de zone depuis le 30/10 ; les données OSM réelles ont des coordonnées, c'est le jeu de test à compléter.
- Lignes 654-655 : `cmd_approuver` appelé avec 3 arguments alors que `scenario()` l'a remplacé par un lambda à 2 arguments.
- Lancer le test ligne à ligne pour les voir tous : instruction par instruction (ast), JARVIS_TEST=1.

## Retours de Liam sur l'accueil boulangerie v5 (2 novembre 2026, 16 h 19)
- Premier écran avec la vidéo : très apprécié (« très très belle »). À garder comme référence pour les autres métiers.
- Le nuage 3D / la scène 3D du four : pas convaincant. À améliorer plus tard.
- La structure du reste de la page (sections après l'accueil) : n'est pas trop son style. À retravailler.
- Niveau global : « ça va pour l'instant », mais il faudra plus tard faire un site vraiment beaucoup mieux.

## Retour de Liam, 2 novembre 2026, 16 h 24 (suite, accueil boulangerie v5)
- La section contact / bouton « Appeler » n'est pas belle : à refaire (contact + clôture).
- Plus tard : « masteriser » les sites (niveau nettement supérieur), pas maintenant.
- Idée : prendre un cold caller (quelqu'un qui appelle à sa place) quand ce sera possible. Voir la réponse sur le moment et les conditions.

## Retour de Liam sur la page plombier v1 (2 novembre 2026, 19 h 03)
- La page est « nulle » : il faut tout refaire dans un style vraiment futuriste, qui vaut des milliers d'euros.
- Le bouton « Appeler » est super moche, le bloc itinéraire / contact aussi : à refaire entièrement.
- Le schéma de départ (plan de maison) est moche : à supprimer ou remplacer.
- La 3D n'a aucun sens ni aucune utilité : une 3D n'est acceptable que si elle SERT (fond immersif, guide ou avatar qui accompagne et oriente l'utilisateur, démonstration du service). Pas de 3D décorative.
- Affiner les skills pour monter le niveau futuriste (nouveau skill « futurisme utile »).

- 2026-11-03 : RÈGLE PERMANENTE : le premier écran de CHAQUE page/site exemple doit être animé (titre qui se révèle, vidéo ou photo en mouvement lent), au même niveau que les premières pages faites, jamais une photo fixe.

- 2026-11-03 : Appelants (ex. Sid) : recrutement possible par écrit ou par un court appel SANS caméra ; Liam leur donne son planning de rendez-vous (créneaux visio de 15 min : après-midi, ou matin à partir de 11 h) et l appelant propose un créneau dans cette liste. Liam préfère recruter par message (flemme des longs échanges).

- 2026-11-03 : Agent Instagram autonome : la tâche planifiée quotidienne publie déjà seule ; idée de Liam = qu elle produise aussi les prochains visuels et vidéos (quand la file passe sous 3 posts) pour ne plus dépendre de Claude dans le chat.

- 2026-11-03 : Agent Devis : Liam n aime pas faire les devis ; un agent prépare le devis écrit (offre, prix, lien d acompte Stripe) et Liam le valide.
- 2026-11-03 : Accès appelants : page ou tableau partagé pour que les appelants (ex. Sid) voient les créneaux libres de Liam et leurs chiffres, SANS mot de passe ni accès à ses comptes (ex. lien de planning de rendez-vous Google Agenda).

- 2026-11-03 : Liam ne veut AUCUNE offre gratuite (pas de page offerte contre avis) : toujours payant. Agent devis décidé (obligatoire). Planning Google Agenda réservable créé (lundi-vendredi 10 h-16 h, 15 min) : https://calendar.google.com/calendar/appointments/schedules/AcZssZ3xvWSaK8qGD2TTJST9f12yK_AUNGA7Ru59_qoYk2p4O5MM8noDvTqnw9HKVJ-I2t8ddNvMIgF7 . Reste à ajouter : lien Google Meet automatique et 2 questions (entreprise, site ou landing page) dans le formulaire de réservation. Contact appelants : proposer WhatsApp (numéro à donner par Liam).

- 2026-11-03 : Appel de lancement avec Sid jeudi 5 nov 14 h en Google Meet (fiche : docs\APPEL-SID.md). Agenda de Liam = emoliam255@gmail.com. Mise en ligne des pages : Liam dit « ok vercel » et Claude déploie (jamais Liam lui-même). Prochaines pages métier : fleuriste puis garage, validées une par une. Agent devis : décidé, à faire construire par Claude Code.

- 2026-11-04 : appels-sid : sourcer les numéros sur TOUTE la Normandie (14, 27, 50, 61, 76) pour avoir environ un mois de réserve (objectif : 50-60 numéros/jour x 4 métiers). Liam veut Google Maps en plus d OpenStreetMap. Contrainte : Google Places API demande un compte de facturation (carte), or Liam refuse de mettre sa carte ; scraper Maps est contraire aux CGU. Piste gratuite : OSM sur toute la Normandie + annuaire officiel SIRENE (entreprises par code NAF, sans téléphone) à croiser.

- 2026-11-04 : Restaurant : page **Le Velours** retenue (https://b2b-demos.vercel.app/le-velours-exemple-ef5bae7c/). A faire : ajouter une vidéo en tête de page (hero vidéo), comme les autres pages métier. Ensuite : lire les réponses du Google Form de Sid.

## 2026-11-05 (soir) - Listes d appels et bot 24h/24
- Page restaurant a creer (aucune page exemple pour les restaurants, Sid les appelle sans page).
- Bot qui tourne 24h/24 sur le portable serveur : genere chaque soir la liste d appels du lendemain (artisans du batiment en Normandie via SIRENE + OSM) et la depose dans le Drive de Sid ; a activer samedi apres reinitialisation des tokens.
- Listes plus longues : la liste de lundi n a que 35 lignes (seulement 10 artisans du batiment avec numero dans les fichiers locaux), viser plus de lignes par jour.

- 2026-11-05 : Portable serveur : surveillance du Wi-Fi. Si pas de connexion internet pendant 5 minutes, redémarrer la carte Wi-Fi ; si toujours rien, redémarrer le portable (une fois par heure au maximum), et les agents B2B/Jarvis doivent repartir seuls au démarrage. Alerte Discord au retour du réseau. Cause connue : problème de carte Wi-Fi, portable à 84 % d utilisation (4 nov.).

## 2026-11-05 (soir) - Regle des listes d appels (bot)
- Minimum 40 a 45 lignes par jour d appel (au lieu de 35).
- Rotation sur une semaine glissante : a chaque nouveau jour, le bot cree la liste du prochain jour d appel et retire celle du meme jour de la semaine precedente (ex. le mardi 7 il retire le fichier du mardi 1 et cree celui du mercredi 8 ; le mercredi 8 il retire celui du mercredi 2 et cree celui du jeudi 9). Il garde donc une semaine de fichiers dans le dossier.
- Idee de securite : ranger l ancien fichier dans un dossier Archive plutot que le supprimer, pour garder les comptes rendus de Sid.

## 2026-11-08 (soir) - Recherche d'un autre cold caller
- ZillaSales inutile (couvre seulement USA/Canada), abandonne.
- Pistes retenues : Malt, Codeur.com, en plus des 2 groupes Facebook deja utilises pour Sid.
- Annonce prete a poster :
  Titre : Commercial terrain / teleprospecteur independant - commission 15% (Rouen, Normandie)
  LM MULTI-SERVICES (micro-entreprise, creation de sites web pour artisans et commerces locaux) cherche un commercial independant pour de la prospection telephonique en Normandie (76, 27, 14, 50, 61).
  - Mission : appeler des entreprises sans site web (plombiers, electriciens, coiffeurs, restaurants), proposer un rendez-vous visio de 15 minutes.
  - Pas de vente ni de prix a donner au telephone : uniquement la prise de rendez-vous.
  - Remuneration : 15% du prix reellement encaisse par client apporte, verse sous 30 jours apres paiement. Aucun salaire, aucune avance.
  - Listes d'appels fournies chaque jour, aucune prospection a faire soi-meme.
  - Independance totale : horaires et rythme libres.
  - Statut requis : micro-entreprise (SIRET).
  Contact : [e-mail / WhatsApp de Liam]
- A faire par Liam : creer compte Malt et/ou Codeur.com, coller l'annonce (compte + paiement = action personnelle, non faite par Claude).

## 2026-11-09 (nuit) - Idee : vault Obsidian pour Jarvis
- Liam propose de brancher Obsidian (app de notes markdown avec liens entre notes + vue graphe) sur Jarvis : les journaux, l'historique des idees (ce fichier), les fiches clients/prospects deviendraient des notes liees entre elles au lieu de fichiers .md isoles.
- Avis Claude (pas encore fait) : pas prioritaire ce soir - ni urgent ni bloquant, scope pas encore cadre (quel contenu dans le vault ? genere automatiquement ou range a la main ?). A spec proprement avant de dev : liste precise de ce qui irait dans le vault et ce que ca apporte de plus que les fichiers .md actuels.
- Statut : en attente, a rediscuter quand le reste (planning Sid, recrutement, sites) est stabilise.

- 2026-11-13 (Liam) : ARCHITECTURE TYPE OBSIDIAN a refaire pour utiliser moins de tokens : coffre = dossier Jarvis, INDEX.md comme hub, notes courtes avec liens [[...]], une note par agent et par decision. Obsidian (gratuit) sert seulement a VOIR le graphe ; Claude n'a pas besoin de l'installer, il lit les fichiers .md. A faire avant le reste.
- 2026-11-13 (Liam) : ARCHITECTURE A PARTIR DU CEO : Jarvis. Les TikTok donnes a Claude contenaient l'architecture complete (contenu perdu avec la conversation supprimee, a redonner). Jarvis doit tourner 24/24 sur le serveur Liam, pas seulement quand le gros PC est allume.
- 2026-11-13 (Liam) : les prompts Claude Code doivent se terminer par la machine : « gros PC » ou « serveur Liam ».
- 2026-11-13 (Liam) : tout ce qui est a faire est note dans TODO-B2B.md, JOURNAL-B2B.md et IDEES-MASTER.md (fichiers deja crees), pour le garder a vie. Ne jamais supprimer de conversation : l'historique n'est pas une sauvegarde, les fichiers le sont.


## 2026-11-14 (nuit) - Session Opus : tout ce qui fait vendre vite

### Argent qui fuit aujourd'hui (a corriger avant la 1re vente)
- Aucun lien Stripe pour l'abonnement 49 EUR/mois. Les liens 595 EUR et 994 EUR n'encaissent que la partie unique : le recurrent n'est jamais preleve. Perte = 588 EUR par an et par client. A creer dans Stripe : prix recurrent 49 EUR/mois, et un lien unique "595 EUR a la commande + 49 EUR/mois".
- Nom public Stripe encore "Trouve ton produit" : le client voit un nom inconnu au moment de payer, juste avant de valider. A passer a LM MULTI-SERVICES.
- Decision du 14/11 : plus d'acompte. Lien de paiement complet envoye directement avec le devis. Les liens acompte/solde (177/413/297/693) deviennent inutiles.
- Manque pour rassurer un commercant : mentions legales + SIRET sur le site et sur les devis, conditions de vente ecrites (ce que comprend le pack, duree et resiliation de l'abonnement 49 EUR/mois).

### Ce qui fait signer le premier client
- Offre fondateur (3 premiers clients) : 295 EUR au lieu de 595 EUR + 49 EUR/mois inchange, en echange du droit de montrer le site en reference et d'un temoignage video de 30 secondes. La 1re vente vaut une preuve, pas un revenu ; le recurrent est preserve.
- Garantie zero risque : "si la page ne vous plait pas, vous ne payez rien". Supprime l'objection principale quand on n'a aucune reference.
- Page deja en ligne a leur nom + QR code imprime : en passage physique, le patron voit sa page sur son propre telephone en 10 secondes.
- Avant/apres chiffre : capture de leur site actuel (ou absence de site) + score PageSpeed a cote de la nouvelle page. Argument mesure, pas un avis esthetique.
- Ciblage par ordre de facilite : fiche Google avec au moins 20 avis et 4,2 etoiles, mais pas de site. Ils ont deja des clients et rien pour les capter.
- Horaires reels : samedi matin 10h-12h = artisans (souvent au depot), 14h30-16h30 = commerces calmes. Ne pas appeler coiffeurs et restaurants le samedi (rush). Appels telephoniques : lundi et mardi 9h-11h.
- Cercle proche d'abord : un ami, un parent, un commercant deja connu. C'est le chemin le plus court vers la 1re vente et la 1re preuve.

### Agents a creer, par rentabilite
1. Relance J+3 et J+7 : la majorite des reponses viennent des relances, pas du 1er message. Agent le plus rentable a construire.
2. Pre-generation de pages en masse : 20 pages au nom des prospects d'avance, URL prete avant l'appel.
3. Signaux d'achat - entreprises nouvellement immatriculees dans la zone (API Sirene, gratuite) : besoin de site immediat et budget de lancement.
4. Detection de site mort : erreur, certificat expire, pas mobile, PageSpeed sous 50 -> prospect avec argument chiffre.
5. Rappel de closing : devis envoye et non paye sous 48h -> alerte pour rappeler.
6. CEO Jarvis : resume Discord matin et soir, alerte si un agent plante, tableau de bord revenu.

### Sites
- Un seul objectif par page : appeler. Numero cliquable collant en bas sur mobile.
- Une page de demonstration par metier = cout marginal nul pour chaque nouveau prospect du meme metier.
- Preuve sociale honnete : ne jamais inventer de temoignage. Utiliser les pages d'exemple reellement realisees et les scores de vitesse.

### Obsidian et vue 3D de l'entreprise (demande de Liam le 14/11)
- Obsidian : gratuit, coffre = dossier Jarvis, vue graphe native. Notes courtes avec liens [[...]] = moins de tokens pour Claude.
- Tableau de bord 3D cliquable : page HTML locale (three.js), icone sur le bureau, lit un agents.json genere par un script qui scanne les agents et leurs etats. CEO Jarvis au centre, agents en orbite, vert/rouge selon l'etat, clic = details. Se met a jour tout seul quand un agent est cree. Script sans tokens Claude.
- 2026-11-14 (Liam) : coffre Obsidian sur le dossier Jarvis (INDEX.md hub, notes agents et décisions) et tableau de bord 3D local sans token (dashboard\index.html, mis à jour toutes les 5 min). Suite possible : voir l'état du serveur en direct (petit fichier d'état publié par le serveur, à décider).
- 2026-11-14 (Liam) : tableau de bord 2D de l'entreprise (organigramme par pôles, pipeline, à faire, journal, décisions, idées), servi par le serveur sur le port 8080 pour voir son état en direct depuis le gros PC (tâches à créer là-bas avec outils\taches-dashboard-serveur.ps1 -Oui).

### 2026-11-14 (midi) - Idees de Liam
- Appels uniquement, jamais de presentiel : tout le plan de vente passe par le telephone (Liam et Sid).
- Skill « scripts d'appel » (Opus, par metier, versions Sid et Liam), a valider avec Claude avant usage.
- Skill de design de site, puis equipe design / code / publication.
- Connecteur d'ecoute de reunion (nom a donner par Liam) : verifier gratuite et accord des participants.
- Serveur « qui ne bouge plus » : Claude reste relie au gros PC, le serveur recupere par git (maj-auto) ; plus aucune manipulation sur le serveur.
- CEO Jarvis autonome apres la 1re vente : lit les resultats, relances J+3/J+7, lead chaud, devis, resume Discord le soir ; decisions engageantes soumises a Liam.
- Personnalite de Claude : sincere, sans flatterie, efficace, orientee vente.

### 2026-11-14 (apres-midi) - Idees de Liam (video et architecture)
- Astuces d'une video (a appliquer a Claude Code) : boucles avec critere de fin (ne pas rendre la main avant 100 %), un skill par tache repetitive, hooks automatiques, sous-agents a contexte propre, bon modele par tache (Opus/Fable pour le complexe, Sonnet/Haiku pour le simple), /compact apres chaque tache, mode plan pour les grosses taches.
- Un skill dedie par agent (appels-sid, prospection, devis, reponses, rendez-vous) pour ne plus repeter ses consignes ; plus tard.
- Reorganiser l'architecture des agents : Liam doit trouver un exemple a montrer ; les agents sans lien avec la vente sont a revoir. Instagram est retire (decision du 14/11).
- Skill « scripts d'appel » generique : genere le script pour n'importe quelle entreprise (versions Sid et Liam), pas des scripts figes par metier.
- Appels uniquement du lundi au vendredi, jamais le week-end.
- Gabarit unique pour creer des skills (entrees, procedure, regles, critere de fin, exemples a valider) pour economiser des tokens.

### 2026-11-14 (soir) - Architecture voulue par Liam (validee sur le schema)
- Organigramme : Liam et Claude (conseil) en haut ; Jarvis = CEO ; Jarvis ne parle qu'aux responsables (agents maitres), chaque responsable gere ses petits agents.
- Responsables : Prospection (recherche, lots d'e-mails, liste d'appels de Sid) ; Vente (reponses, rendez-vous, devis, relances J+3/J+7) ; Argent (alerte Stripe, resume du soir, alerte pannes) ; Production plus tard apres la 1re vente (design, code, publication). Agents facultatifs ajoutables plus tard.
- Chaque agent a UNE fiche de role = son skill : ce qu'il fait, ce qu'il ne fait jamais, ses ordres precis. Un clic sur un agent dans le tableau de bord ouvre cette fiche (pas le journal).
- On avance etape par etape, un agent a la fois avec son skill ; pas de refonte d'un coup. Ne pas renommer les scripts : regrouper d'abord logiquement.
- Liste d'appels : UN seul tableur par jour, supprime au bout d'une semaine ; plus aucun dossier cree chaque jour ; lignes triees par heure d'appel, colonnes larges, toujours les memes, tres propre ; jours ouvres uniquement (lundi a vendredi). Regles deja fixees : 100 appels, creneaux 8 h a 19 h, entreprise deja appelee oubliee un an.
- Tableau de bord : style Apple, fond transparent, menu a gauche (architecture, ventes, to-do, taches, graphiques) ; reste servi par le serveur (port 8080) et ouvert comme une appli (fenetre d'application sur le bureau), pas un artefact (il ne peut pas lire l'etat du serveur en direct) ; clic sur un agent = sa fiche de role.
- Scripts d'appel : trop vendeurs d'apres Sid (non categorique a chaque fois) ; le skill doit sonner humain et sans pression (premiere phrase sur eux, aucun prix ni mot « offre » dans la version Sid, une seule question).
- Demander a Sid les phrases exactes qui ont fait dire non.

### 2026-11-14 (apres-midi tardif, 15 h - 16 h) - Tableau de bord, commissions, Stripe, revue etape 1
- Tableau de bord (maquette montree dans le chat, validee dans l'esprit) : verre transparent blanc avec une touche de bleu, fond violet proche du fond d'ecran Dubai de Liam (sans le copier), coins arrondis, style Apple, utile et un peu futuriste.
- Barre a gauche en icones qui s'ouvre quand on passe la souris. Vues : vue d'ensemble, appels du jour, pipeline, agents, argent, a faire.
- Les cartes « appels du jour / rendez-vous » en haut ne servent pas : les remplacer par les courbes de la semaine (lundi a vendredi) : appels, rendez-vous, devis envoyes, ventes, taches des agents ; infobulle au survol.
- Taux : appel vers rendez-vous, rendez-vous vers devis, taux de closing. Meilleurs creneaux d'appel (carte de chaleur jour x heure). Pourquoi ils disent non (classement des refus lu dans la colonne Resultat). Commissions modifiables. Pipeline (RDV, devis, relance J+3, paye). Objectif premiere vente 0/1. Prochaine action.
- Pense pour un grand ecran : courbes et architecture complete cote a cote. Le serveur le sert (port 8080), ouvert comme une appli.
- Agents en ligne : un voyant par sous-agent (vert = a l'heure, orange = en retard, rouge = plante + alerte, gris = pas cree ou desactive), d'apres la derniere execution de la tache sur le serveur ; un responsable prend la couleur du pire de ses sous-agents. Il manque l'heure de derniere execution dans agents-json.py (a ajouter a l'etape tableau de bord).
- Les vrais agents sont les sous-agents (scripts) ; les responsables les regroupent. Pas de 5e responsable « Systeme » maintenant (l'alerte pannes reste sous Argent), a revoir plus tard.
- Chiffres de la maquette = exemples (marques « exemple »). Seuls vrais : ventes 0, CA 0, commissions 0. Les vrais chiffres viendront du journal des appels de Sid.
- Colonne Resultat du tableur de Sid = liste fixe de 8 valeurs (Sid ne tape rien) : Pas de reponse, A rappeler, RDV pris, Non categorique, Je dois reflechir, Trop cher, Deja un site, Pas le temps. Les refus doivent tous finir dans des tableaux propres pour alimenter le tableau de bord.
- Regles de reprise proposees (a valider par Liam) : Pas de reponse = revient 2 jours ouvres plus tard sur un autre creneau, 3 tentatives max puis oubliee 1 an (Claude Code l'avait oubliee 1 an d'un coup : erreur, ~70 % ne decrochent pas) ; A rappeler = jour ouvre suivant avec la note ; Je dois reflechir et Pas le temps = une seule reprise a J+7 ; RDV pris = sort de la liste ; Non categorique, Trop cher, Deja un site = oubliee 1 an.
- Commissions : Liam trouve 15 % + 15 % (appelant + closer = 30 %) trop ; il pense a 10 % chacun (20 % au total). Pas de chiffre verifie sur les taux habituels. A decider : commission sur le premier paiement seulement (conseille) ou aussi sur les 49 EUR/mois. Taux modifiables dans la vue Argent du tableau de bord.
- Resiliation (decision Liam, remplace ma proposition « site hors ligne ») : le client arrete les 49 EUR/mois quand il veut, l'arret prend effet a la fin du mois paye ; le site reste en ligne tel quel et il garde son nom de domaine, mais plus de modification ni de support. Plus de preavis. Phrase au telephone : « Vous pouvez arreter les 49 euros par mois quand vous voulez. Le site reste en ligne tel quel, mais je ne le modifie plus et il n'y a plus de support. » Pas juriste : faire relire, surtout droit de retractation en vente a distance.
- Domaine : titulaire = le client (son nom et son adresse), compte chez le registrar = Liam, code de transfert donne si le client part ; a verifier chez le registrar choisi (varie selon .fr ou .com). Renouvellement annuel du domaine facture au client : plus tard, prix annuel dans Stripe. Le produit Stripe dit « maintenance, hebergement et nom de domaine » : a corriger si le domaine est facture a part.
- « Playwork » (idee : le client achete domaine + hebergement pour 1 an) : nom introuvable, Liam doit donner le lien ou l'orthographe. Domaine offert la 1re annee : non, sauf exception.
- Hebergement : Vercel, Liam a deja le plan Pro (le plan gratuit Hobby interdit l'usage commercial).
- Stripe, 2 liens crees le 14/11 (mode reel), un seul lien par offre : pack 595 EUR + 49 EUR/mois avec 30 jours de maintenance gratuits : https://buy.stripe.com/3cIbJ2diZ3kF9DF9W85EY0a ; site complet 994 EUR + 49 EUR/mois avec 30 jours gratuits : https://buy.stripe.com/bJeaEY7YF4oJ035d8k5EY0b . Le texte sous le bouton annonce les 49 EUR et l'arret possible. Verifie en ouvrant les pages : le total du jour est bon.
- Decision modifiee le 14/11 : avant, 3 mois offerts seulement comme levier ; maintenant 1 mois de maintenance inclus par defaut dans le lien. Trois mois offerts = exceptionnel (si besoin : lien separe avec essai de 90 jours).
- Stripe, problemes : la page affiche « skyshoot » (nom public du compte) au lieu de LM MULTI-SERVICES : a changer dans Parametres > Informations publiques. Le bouton « Payer et commencer la periode d'essai » ne peut pas etre modifie. Les anciens liens (acompte 30 %, solde, 2 liens du matin sans mois offert) sont toujours actifs : a desactiver quand Liam le dit. La mention « TVA non applicable, art. 293 B du CGI » + SIRET n'est pas sur les nouveaux liens : a mettre dans les reglages de facturation Stripe.
- Closing : dire « meme soin, tout sur une seule page » et pas « meme qualite » (une landing n'est pas un site complet) ; annoncer les 49 EUR/mois avant le paiement ; Liam n'a jamais livre de site complet multi-pages, a prevoir avant de le promettre.
- Entrainement : prompt de jeu de role (plombier mefiant, 8 echanges, note sur 10, moment ou le client est perdu, 2 phrases a remplacer) donne a Liam pour une autre conversation.
- Revue etape 1 de Claude Code (commit fba5e73, lu dans les vrais fichiers) : OK = responsable-prospection + 3 fiches (agent-recherche, agent-lots-emails, agent-appels-sid), 25 commandes citees toutes existantes, tests verts (seul « memoire\ inchange » echoue car Jarvis tournait). A corriger avant lundi : Pas de reponse oublie 1 an ; Resultat a 4 valeurs au lieu de 8 ; entreprises hors Normandie (Eure-et-Loir) dans la reserve ; melange des metiers (76 lignes garagiste/boulanger/fleuriste/restaurant sur 100, seulement plombier 1, electricien 1, couvreur 2, macon 1) ; tableur Google jamais cree pour de vrai (essai a blanc, drive.file a verifier dans le dossier de Sid). A ranger : anciens liste-appels-*.md. .obsidian/graph.json bloque git pull --rebase. Prompt de correction en 7 points donne a Liam (gros PC).

### 2026-11-15 (01 h) - Codex, skills par agent, Obsidian
- Codex : plugin openai/codex-plugin-cc installe (v1.0.6, gros PC). Liam dit avoir fait /reload-plugins et /codex:setup. Idee de Liam : Codex fait les taches ou il est meilleur, Claude Code le reste, pour economiser des tokens (non prouve). Pas de cle API, compte ChatGPT gratuit.
- Idee de Liam : un skill detaille par agent et par responsable, avec ses ordres. On commence par Jarvis (CEO), le plus gros.
- Idee de Liam (plus tard) : Obsidian en vue "espace", architecture ultra realiste de l espace, pour voir les agents. Les agents d abord.
- Idee de Liam : entreprise qui tourne seule (PC et serveur allumes), notifications Discord. Boite aux lettres moi-Claude Code : B2B/docs/FILE-ATTENTE.md et RESULTATS.md, apres l etape Vente.

### 2026-11-15 (18 h) - Domaine inclus, harness de coherence, fichiers corriges
- Decision de Liam : le 49 euros par mois inclut le nom de domaine (domaine au nom du client). Le texte Stripe "Maintenance, hebergement et nom de domaine" est donc exact.
- Idee de Liam : un harness, c est-a-dire des verifications automatiques (sans token) qui attrapent les fautes de coherence : mauvais lien Stripe, phrase fausse ("sans abonnement", "facultative"), anciens prix, mauvaises heures, anciennes valeurs de Resultat. Source unique OFFRE-REFERENCE.json + tests\coherence-offre.py dans tests\tout.ps1.
- Fautes trouvees le 15/11 : liens-paiement.md donnait les liens sans premier mois offert ; DEVIS-ET-OBJECTIONS.md disait "sans abonnement obligatoire" ; SCRIPT-APPEL-SID.md : heures 10-12 et 14-17 au lieu de la liste 8-19, Resultat a 4 valeurs, maintenance "facultative" ; bouton du site vitrine luxe2 sur l ancien lien 994 sans abonnement. Versions corrigees ecrites en .NOUVEAU.md a cote des anciennes.
- Agent Rendez-vous arrete depuis le 10/11 : adresse iCal secrete a mettre par Liam dans le fichier local de config (jamais dans le chat ni sur GitHub).

### 2026-11-15 (18 h) - Harness par agent
- Principe : chaque agent a un contrat (B2B/harness/contrats/<agent>.json : mission, jours et heures, fichiers lus et ecrits, salons Discord, interdits, plafond par jour, peut_engager toujours false, heure limite sans trace, tests), une garde avant chaque envoi, une trace par execution et un test sans reseau.
- Zero token au runtime : Python et PowerShell standard, aucun appel d API payante, tests sans reseau, envois en simulation tant que envoi_automatique vaut false dans les fichiers versionnes.
- Reference unique : B2B/docs/OFFRE-REFERENCE.json (595 et 994 EUR une fois, puis 49 EUR/mois tout inclus, premier mois offert, arret libre, 2 liens Stripe seulement, 8 valeurs de Resultat, liste de Sid a 07:30, creneaux 08:00-19:00). tests/coherence-offre.py compare docs, skills, agents et site vitrine a ce fichier.
- La garde avertit par defaut et BLOQUE seulement : lien Stripe non autorise, phrase interdite, secret, envoi client hors lundi-vendredi 08:00-19:00, fichier B2B/STOP (kill-switch).
- Ce qui engage Liam (envoyer au client, encaisser, publier, signer) n est jamais execute par un agent : ecrit dans B2B/a-valider/AAAA-MM-JJ-<agent>.md pour validation.
- Surveillant : 19:45 chaque jour et 07:50 le lundi ; une ligne par agent en defaut (n a pas tourne, erreur), silence sinon, "harness OK, N agents" le lundi.
- Jarvis CEO ne sort que des decisions structurees (jarvis-sortie.schema.json) : chiffres trouves dans les sources, aucune promesse client, engage_liam a true des qu une action engage.
- Claude Code a son propre harness : CLAUDE.md (regles 13 a 17), hooks .claude/hooks (ajout global a git, reset dur, clean, push force, lecture de .env et *.local.json, ecriture dans memoire/), hook git pre-commit (secrets et coherence). Pas de preuve = pas de "fait" : tests/b2b-rapide.ps1 (moins de 60 s).

### 2026-11-15 (18 h) - Fiches Obsidian par agent
- Une fiche par agent (B2B/docs/agents/<agent>.md) generee depuis son contrat, son skill et ses traces par python B2B/harness/generer-fiches.py : mission, etapes, entrees et sorties, interdits, harness (garde, tests, derniere trace, alerte si silence), skill, historique sans donnees client.
- Organigramme en graphe (00-ORGANIGRAMME.md, liens [[...]] et bloc Mermaid) : Liam, Jarvis (CEO), 4 responsables, agents. Zone "Notes de Liam" conservee a chaque regeneration.
- Un skill par agent dans .claude/skills/agent-<nom> (copie dans B2B/docs/agents/skills) ; tests/b2b-rapide.ps1 verifie que chaque contrat a sa fiche a jour et chaque agent actif son skill.
- 2026-11-15 (20 h) - Un seul graphe Obsidian : le hub INDEX, les fiches détaillées générées dans les notes agents

## 2026-11-15 (20 h) - Techniques de closing de Liam
- Face a « je dois reflechir » : demander combien de temps, laisser PLUS que demande (1 semaine -> 2 semaines) pour le detendre, puis poser la question de blocage avec la phrase de douleur dite par le client : « qu'est-ce qui vous bloque aujourd'hui et qui permettrait de passer a l'action directement ? ». Version plus directe : « qu'est-ce qui vous empeche de passer a l'action maintenant ? ».
- Si la raison est la confiance : idee de Liam d'un petit acompte (environ 100 EUR) qui paie un appel de travail, puis infos et site prepare sous 24 h. A DECIDER : contredit « sans acompte » (liens d'acompte desactives le 15/11) ; en attendant, chemin sans argent (maquette gratuite, apercu prive, premier mois offert, appel de cadrage gratuit).
- Sortie elegante si pas de confiance : « on a passe du temps ensemble, je comprends, c'est dommage mais si vous le souhaitez... » puis maquette par e-mail sans engagement.
- Sid note la phrase exacte de douleur du client dans Note : munition pour la question de blocage.
- Fichier : B2B/docs/TECHNIQUES-CLOSING.md (a rechercher et enrichir avec de bonnes phrases de vente).
