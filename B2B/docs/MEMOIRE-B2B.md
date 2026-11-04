# Mémoire B2B : état, décisions et règles (26 oct. 2026)
Fichier tenu à jour pour ne rien perdre entre deux conversations. Les idées détaillées restent dans `docs\IDEES-MASTER.md`.

## Identité (agents\identite.json)
- Liam Emo, LM MULTI-SERVICES, SIRET 101 839 033 00012.
- Téléphone professionnel : À COMPLÉTER. E-mail de réponse : À COMPLÉTER. Tant que ces deux champs sont vides, les messages sont marqués « ne pas envoyer ».
- Domaine existant : lmlsmulti-services.com (donné par Liam le 26 oct.). C'est un site ACTIF de débarras à Rouen (LM & LS Multi-Services, hébergé sur Netlify). Acheté chez IONOS selon Liam, date d'expiration à vérifier. NE PAS l'utiliser pour la prospection : sa réputation sert à l'activité débarras.
- Contact publié sur ce site pour LM Multi-Services : 06 68 50 64 19 et emoliam255@gmail.com. À confirmer par Liam avant de les mettre dans identite.json.
- Point d'image : ce site présente LM MULTI-SERVICES comme une entreprise de débarras. Un artisan qui vérifie le nom de l'expéditeur y tombera. Prévoir une page « création de sites pour artisans » ou un nom d'enseigne dédié.

## Objectif
- Première vente d'une landing page (590 €) avant la fin de cette semaine (au plus tard dimanche 1er nov. 2026).
- Ensuite : environ 100 e-mails de prospection par jour, toute la France, tous les métiers, tous les jours.

## Offres et prix (décidés par Liam)
- Landing page pro : 590 €.
- Site complet : 990 à 1 490 € (`offre=complet` pas encore construit : on le construit si un prospect le demande).
- Nom de domaine / DNS : 40 € + prix coûtant, domaine au nom du client.
- E-mail professionnel : sur devis.
- Maintenance : 29 à 49 € par mois.
- Devis type, script d'appel et 8 réponses aux objections : `docs\DEVIS-ET-OBJECTIONS.md` (brouillon à valider ; points à confirmer : délai, acompte, TVA, rétractation, relecture juridique).

## Parcours de vente
E-mail ou message LinkedIn/Facebook -> le prospect répond « oui » -> appel de 15 minutes -> devis -> paiement Stripe (lien Stripe PAS encore créé).
Jamais d'appel à froid.

## Règles permanentes
- Rien n'est envoyé, déployé ni dépensé sans l'accord de Liam. Un seul OK par lot d'envois.
- STOP ou refus = exclusion définitive de toutes les listes.
- Prospection B2B (CNIL) : objet en rapport avec la profession, identité de l'expéditeur, origine du contact, opposition simple et gratuite. Adresses génériques (contact@, info@) hors de ces règles. Pas de pixel de suivi des ouvertures (consentement requis). Ce n'est pas un avis juridique.
- Aucun faux chiffre, aucun faux avis, aucune promesse de classement Google, aucune fausse urgence, aucune affirmation non vérifiée sur le site d'un prospect.
- Toujours montrer à Liam un bel aperçu avant tout envoi (boîte de réception sur téléphone + message ouvert). Aperçu fait pour les 3 versions et la relance.
- Chaque idée de Liam est notée tout de suite dans `docs\IDEES-MASTER.md`.
- Bistro et céramique sont validés : ne pas les modifier.

## Méthode (changement du 26 oct.)
- PAS une maquette par prospect. Une page modèle par métier, en ligne une fois, liée dans tous les messages comme « exemple ».
- Prospection dans toute la France, pas seulement autour de Rouen.
- Après la vente seulement : personnalisation (nom, photos, couleurs, communes).

## Pages en ligne (b2b-demos.vercel.app, noindex)
- Électricien « Atelier Lumière » v3 (animée, avant/après, galerie, carte de zone, Lighthouse 100) : https://b2b-demos.vercel.app/atelier-lumiere-exemple-d80eb712/
- Bistro et céramique : validées. Marché : refait, redéploiement en attente (LCP 3,0 s à corriger). Anciens styles électricien (rassurant, technique, premium) : archivés.
- Il manque des pages modèles pour : plombier, couvreur, peintre, menuisier, maçon, etc.
- Déploiement Vercel : le dépôt Git local est bloqué (auteur du commit) ; on déploie depuis une copie hors dépôt, ou on met l'e-mail du compte Vercel dans `git config user.email`.

## Agents
- Dev sites, Rédaction, Suivi : en place (Rédaction et Suivi testés sur prospects fictifs).
- Sourcing : documenté (annuaire officiel des entreprises). `prospects_rouen.csv` (2 113 lignes) n'a ni e-mail, ni téléphone, ni note.
- Enrichissement, Qualification, Envoi, Relances, Réponses : coquilles vides, à construire.
- À faire sur `redaction.py` : lien vers la page modèle du métier via `agents\liens-metiers.json`.

## Problème de fond : les e-mails
- Les artisans sans site web n'ont presque jamais d'e-mail publié. Piste A (cette semaine) : LinkedIn et Facebook à la main. Piste B (volume) : cibler les artisans avec un vieux site, dont l'e-mail est dans les mentions légales (proposée à Liam, réponse en attente).

## E-mail de prospection : plan de test
- 3 versions + relance J+2 prêtes (aperçu publié dans Claude).
- Test A/B : boîtes 1 et 2 = version Courte ; boîtes 3 et 4 = version Argumentée. Décision après environ 100 envois par version. Version « Vieux site » seulement avec un constat vérifié à la main.
- Mesure : réponses « oui » et rendez-vous, pas les ouvertures.

## Boîtes d'envoi
- Ne pas envoyer en masse depuis des Gmail gratuits ni depuis le domaine principal : risque de blocage des comptes et de réputation du domaine.
- Plan : domaine ou sous-domaine dédié à la prospection, 4 boîtes avec des noms humains, SPF + DKIM + DMARC, chauffe de 3 à 4 semaines (semaine 1 : 5 à 10 mails par boîte, puis 25 à 30 par boîte et par jour). 100 par jour atteints vers le 20 novembre.
- Première adresse choisie : liam.emo@[domaine d'envoi]. Suivantes proposées : liam@, bonjour@, contact@.
- Dépenses (domaine, boîtes, outil d'envoi) : seulement avec l'accord de Liam.

## À faire, dans l'ordre
1. Liam : donner téléphone pro et e-mail de réponse (-> `identite.json`).
2. Liam : confirmer le nom du domaine IONOS et choisir le domaine d'envoi.
3. Liam : 10 à 15 messages LinkedIn/Facebook par jour à la main (artisans sans site, vérifiés à la main) + 5 à 10 artisans ou commerçants qu'il connaît.
4. Claude Code : `redaction.py` + `liens-metiers.json` (lien vers la page modèle).
5. Décider de la piste B (artisans avec vieux site) pour l'agent Sourcing.
6. Pages modèles des autres métiers (plombier d'abord).
7. Construire Envoi, Réponses et Relances, avec validation par lot.
8. Valider le devis, puis créer le lien Stripe (avec l'accord de Liam).

## Site vitrine de l'activité (créé le 26 oct. 2026)
- Dossier `sites/agence/` (accueil, mentions légales, confidentialité). Régénération : `python sites/agence/build.py` ; contrôle : `node sites/outils/qa-agence.mjs`. Doc : `sites/agence/LISEZ-MOI.md`.
- Répond au « point d'image » : le site de débarras LM & LS Multi-Services reste séparé ; cette vitrine présente la création de sites pour artisans et commerces sous le nom LM MULTI-SERVICES, avec Liam Emo.
- Contenu : prix 590 € (landing), 990 à 1 490 € (site complet), domaine/DNS 40 € + prix coûtant, e-mail pro sur devis, maintenance 29 à 49 €/mois ; parcours message, appel de 15 minutes, devis, paiement sécurisé ; 3 exemples en ligne (électricien, bistro, céramique) présentés comme fictifs.
- À compléter par Liam avant mise en ligne : téléphone, e-mail (identite.json), forme juridique, adresse, TVA. Les numéros du site de débarras ne sont PAS repris tant que Liam ne les a pas confirmés.
- État : non déployé ; il faut un NOUVEAU projet Vercel (déploiement depuis une copie hors dépôt Git) et l'OK de Liam. Noindex à retirer quand le domaine est branché.
- Page confidentialité : prospection B2B, STOP, durées (3 ans après le dernier échange sans collaboration), à faire relire.

## Site « luxe » : fond photo de Dubaï (26 oct. 2026)
- Dossier `sites/agence/luxe/` (version sobre `sites/agence/index.html` intacte). Doc : `sites/agence/luxe/LISEZ-MOI.md` (régénérer, fichiers à envoyer à Netlify : index.html à la racine, sans build.py, notes, tools\ ni src\).
- Fond : photo ZQ Lee (Unsplash, licence Unsplash, crédit dans `assets/img/CREDITS.json` et les mentions légales), retouchée par `sites/outils/fond-photo.mjs`, rendue en WebGL2 par `src/skyline.js` (5 Ko). Ancienne skyline procédurale three.js gardée seulement pour comparaison (`src/skyline-procedural.js`).
- Contrôles : `qa-luxe.mjs`, `contraste.mjs`, `clavier.mjs`, `lh.mjs`, `videos-luxe.mjs` (dans `sites/outils/`). Captures avant/après : `sites/sorties/agence-luxe/fond/` ; vidéos MP4 : `sites/sorties/agence-luxe/scroll-mobile-390x844.mp4` et `scroll-bureau-1280x800.mp4`.
- Lighthouse mobile accueil 88 / 96 / 96 (la mesure à 88 vient du WebGL logiciel de Chrome sans carte graphique, TBT 230 ms). Console propre, navigation clavier complète avec focus visible, mouvement réduit = image fixe.
- Téléphone, e-mail, forme juridique, adresse, TVA : « À COMPLÉTER » affiché (identite.json). Aucun faux avis, chiffre, logo ni promesse Google. Rien n'est déployé : attente de l'OK de Liam.
