# Agent dev-sites
Rôle : fabriquer les maquettes de sites d'artisans (un lien par prospect), puis les sites spéciaux et la personnalisation après la vente.
Objectif au 23 oct. 2026 : en novembre 2026, produire des maquettes de haute qualité, dans toute la France, sans rien inventer.

**Règle permanente de Liam (30 oct. 2026) : avant toute création ou modification de page, lire `sites\moteur\REGLES-STYLE-SITES.md`, appliquer la chaîne de skills site-local, note >= 8/10, captures à Liam, rien déployé sans son accord (voir `B2B\CLAUDE.md`).**

## Entrées
- Fichier de prospects CSV : nom, metier, ville, telephone, site (site actuel). Colonnes facultatives : zone, note, avis, annees, labels, services, direction. Séparateur `;` ou `,`.
- Short-list de l'agent Qualification (même format).
- Demandes des clients après vente (texte, photos, couleurs, horaires).
- Consignes : `recherche-sites\07-prompt-maitre.md` (prompt maître), `sites\CLAUDE.md` (méthode et interdits), checklist qualité (section 14 de `PROMPT-RECHERCHE-SITES-LONG.md`).

## Sorties
- `sites\public\<nom>-<jeton>\index.html` : une page par prospect, `noindex`, lien difficile à deviner. Un seul projet Vercel pour tout `sites\public\`.
- `sites\public\vercel.json` et `robots.txt` (non indexé, en-tête `X-Robots-Tag`).
- Un score qualité sur 100 par maquette, écrit dans la section « Score qualité » ci-dessous.
- Un registre des photos et licences par maquette (`registre-licences.md` dans le dossier de la maquette si une photo est utilisée).
- Résumé pour Jarvis (Discord #b2b) : nb de maquettes, scores, blocages.

## Outils (dans `sites\`)
- `moteur\generer.py` : thème de base + 3 directions artistiques + contenu par métier (`moteur\metiers\*.json`) + variables par prospect. Python seul, aucune dépendance.
- `outils\qa.mjs` : captures 390 et 1280 px, console, débordement, Lighthouse mobile (Playwright + Lighthouse, installés dans `sites\outils\`).
- Commandes : `python sites\moteur\generer.py prospects.csv` puis `node sites\outils\qa.mjs [filtre]` puis `python sites\moteur\generer.py --rescore`.
- `sites\moteur\deploiement.py` : prépare `sites\deploiement\` (dossier à envoyer sur UN projet Vercel). Ne publie rien.

## Modèles disponibles (24 oct. 2026)
| Famille | Métiers reconnus dans le CSV | Directions | Particularités |
|---|---|---|---|
| artisan | électricien, plombier, couvreur, maçon, peintre, menuisier | technique, rassurant, premium | zone d'intervention, preuves, devis |
| restaurant | restaurant, brasserie, bistro, pizzeria, crêperie | bistro (sombre), marché (clair) | Réserver + Appeler, carte HTML, horaires, avis (zone modèle), réservation 4 champs |
| commerce | commerce, boutique, magasin | atelier | produits, horaires, FAQ, 3D facultative (chargée au clic, image de repli) |
- CSV : colonnes `nom ; metier ; ville ; telephone ; email ; site_actuel` (modèle vide : `sites\prospects.csv`). Facultatives : zone, note, avis, annees, labels, services, direction, illustrations (oui = photos d'illustration libres, légendées « à remplacer »), exemple.
- Photos : bibliothèque libre `sites\moteur\photos\` (9 photos Unsplash, auteur et lien dans `licences.csv`, registre écrit dans chaque maquette). Par défaut, un vrai prospect n'a PAS de photo d'illustration (zones « à remplacer »), sauf `illustrations=oui`.
- 3D : modèle CC0 Poly Haven (vase) + `model-viewer` (Apache-2.0), chargés seulement au clic. Disponible uniquement sur la maquette d'exemple du commerce tant qu'aucun modèle propre au prospect n'existe.
- Le score /70 a 44 points communs et 26 propres à la famille ; QA /30 inchangée.
- Photos de la bibliothèque : voir `recherche-sites\10-restaurants-commerces.md` (références et licences).

## Offres (brouillon du 26 oct. 2026, voir `docs\OFFRES-SITES.md`)
- Landing page pro (1 page, déjà produite) et site complet (3 à 5 pages, à construire : colonne CSV `offre`). Options : nom de domaine/DNS, e-mail pro, maintenance. Prix à décider par Liam.

## Ce que l'agent fait seul
- Générer des maquettes en local à partir d'un CSV, avec les données réelles du CSV et rien d'autre.
- Marquer en clair toute zone à remplacer (photos, avis, SIRET, tarifs) et tout contenu « exemple ».
- Contrôler (captures, Lighthouse, console), corriger, recalculer le score. Maximum 3 essais de correction, puis demande à Liam.
- Mettre à jour ce fichier et `docs\IDEES-MASTER.md`.

## Ce qui demande l'OK de Liam
- Tout déploiement Vercel d'une page au nom d'une vraie entreprise, et tout envoi du lien à un prospect.
- Création de compte, dépense (domaine, banque d'images, abonnement), saisie de mot de passe, connexion à un service.
- Nouveau modèle 3D, vidéo, ou toute photo hors licence claire ; toute photo réelle d'un artisan (accord écrit de celui-ci).
- Après vente : nouvelle page, fonctionnalité, intégration, site sur mesure. Les changements de texte, photo, couleur, horaire peuvent être préparés seuls mais ne sont mis en ligne qu'avec l'OK de Liam.

## Règles dures
- Aucun faux avis, faux chiffre, faux client, faux label, faux logo. Les avis réels viennent de la fiche Google, avec accord de l'artisan.
- Photos : uniquement licence claire (Unsplash, Pexels, Pixabay, ou photos de l'artisan avec accord). Aucune marque ni image protégée copiée.
- Les « raisons de choisir », délais et garanties du modèle sont des propositions : l'artisan doit les confirmer avant mise en ligne.
- Deux échecs sur la même action : arrêt et question à Liam.

## Clients et prospects suivis
<!-- SUIVI:DEBUT (lignes de maquettes écrites par generer.py) -->
| Nom | Métier | Ville | Statut | Lien du site | Dernière action |
|---|---|---|---|---|---|
| Exemple Électricité (technique) | Électricien | Rouen | EXEMPLE (fictif), local | sites\public\exemple-electricite-technique-e87214db\ | 2026-11-04 : génération |
| Exemple Élec Famille (rassurant) | Électricien | Elbeuf | EXEMPLE (fictif), local | sites\public\exemple-elec-famille-rassurant-bd4ff644\ | 2026-11-04 : génération |
| Atelier Exemple Électricité (premium) | Électricien | Rouen | EXEMPLE (fictif), local | sites\public\atelier-exemple-electricite-premium-2fcedd73\ | 2026-11-04 : génération |
| Exemple Plomberie Test | plombier-chauffagiste | Rouen | EXEMPLE (fictif), local | sites\public\exemple-plomberie-test-e488c97a\ | 2026-11-04 : génération |
| Exemple Toiture Test | Couvreur | Le Havre | EXEMPLE (fictif), local | sites\public\exemple-toiture-test-9e622a35\ | 2026-11-04 : génération |
| Exemple Maçonnerie Test | maçon | Évreux | EXEMPLE (fictif), local | sites\public\exemple-maconnerie-test-3c46931c\ | 2026-11-04 : génération |
| Bistro Exemple | Restaurant | Rouen | EXEMPLE (fictif), local | sites\public\bistro-exemple-48a524c0\ | 2026-11-04 : génération |
| La Table Exemple du Marché | Restaurant | Rouen | EXEMPLE (fictif), local | sites\public\la-table-exemple-du-marche-c7b5c52e\ | 2026-11-04 : génération |
| Atelier Exemple Céramique | Commerce | Rouen | EXEMPLE (fictif), local | sites\public\atelier-exemple-ceramique-0ae1f090\ | 2026-11-04 : génération |
| Restaurant Fictif Alpha | restaurant | Rouen | maquette générée, locale, non déployée | sites\public\restaurant-fictif-alpha-025809a7\ | 2026-11-04 : génération |
| Boutique Fictive Beta | commerce | Caen | maquette générée, locale, non déployée | sites\public\boutique-fictive-beta-028abdda\ | 2026-11-04 : génération |
| Electricite Fictive Gamma | électricien | Le Havre | maquette générée, locale, non déployée | sites\public\electricite-fictive-gamma-8e1abaa5\ | 2026-11-04 : génération |
| Plomberie Fictive Delta | plombier-chauffagiste | Évreux | maquette générée, locale, non déployée | sites\public\plomberie-fictive-delta-243c0b9c\ | 2026-11-04 : génération |
| Crêperie Fictive Epsilon | crêperie | Dieppe | maquette générée, locale, non déployée | sites\public\creperie-fictive-epsilon-e783ade9\ | 2026-11-04 : génération |
| Restaurant Fictif Zeta | restaurant | Rouen | maquette générée, locale, non déployée | sites\public\restaurant-fictif-zeta-a290ac64\ | 2026-11-04 : génération |
| Boutique Fictive Eta | commerce | Caen | maquette générée, locale, non déployée | sites\public\boutique-fictive-eta-e26d291e\ | 2026-11-04 : génération |
| Electricite Fictive Theta | électricien | Le Havre | maquette générée, locale, non déployée | sites\public\electricite-fictive-theta-0724a954\ | 2026-11-04 : génération |
| Maisons Exemple | Groupe de restaurants | Rouen | EXEMPLE (fictif), local | sites\public\maisons-exemple-1a69713c\ | 2026-11-04 : génération |
| Sarah Elec | électricien | Rouen | maquette générée, locale, non déployée | sites\public\sarah-elec-20e5ecea\ | 2026-11-04 : génération |
| Antoine Soualah Electricité | électricien | Sotteville-lès-Rouen | maquette générée, locale, non déployée | sites\public\antoine-soualah-electricite-e4bb73c3\ | 2026-11-04 : génération |
| 2ac électricité | électricien | Rouen | maquette générée, locale, non déployée | sites\public\2ac-electricite-df0c6906\ | 2026-11-04 : génération |
| Bricoleroy | électricien | Saint-Étienne-du-Rouvray | maquette générée, locale, non déployée | sites\public\bricoleroy-31d4a1f9\ | 2026-11-04 : génération |
| Couvreur Rouen Toiture | couvreur | Rouen | maquette générée, locale, non déployée | sites\public\couvreur-rouen-toiture-84b859fd\ | 2026-11-04 : génération |
| Paplorey Sébastien Plomberie Chauffage | plombier-chauffagiste | Le Petit-Quevilly | maquette générée, locale, non déployée | sites\public\paplorey-sebastien-plomberie-chauffage-6c784418\ | 2026-11-04 : génération |
| CNET plomberie | plombier | Elbeuf | maquette générée, locale, non déployée | sites\public\cnet-plomberie-8732ebb0\ | 2026-11-04 : génération |
| Emv | plombier | Elbeuf | maquette générée, locale, non déployée | sites\public\emv-3e49f04d\ | 2026-11-04 : génération |
| MJ Service | plombier | Elbeuf | maquette générée, locale, non déployée | sites\public\mj-service-d238ff21\ | 2026-11-04 : génération |
| Adas Bat | maçon | Rouen | maquette générée, locale, non déployée | sites\public\adas-bat-9dac48e5\ | 2026-11-04 : génération |
| Atelier Lumière Exemple | Électricien | Rouen | EXEMPLE (fictif), local | sites\public\atelier-lumiere-exemple-d80eb712\ | 2026-11-04 : génération |
| Atelier Exemple Plomberie | Plombier-chauffagiste | Rouen | EXEMPLE (fictif), local | sites\public\atelier-exemple-plomberie-230739a0\ | 2026-11-04 : génération |
| La Braise Exemple | Restaurant | Rouen | EXEMPLE (fictif), local | sites\public\la-braise-exemple-c6dc7659\ | 2026-11-04 : génération |
| Le Homard Bleu | restaurant | Le Treport | maquette générée, locale, non déployée | sites\public\le-homard-bleu-7476cd38\ | 2026-11-04 : génération |
| Europe Plomberie Chauffage | plombier-chauffagiste | Le Petit-Quevilly | maquette générée, locale, non déployée | sites\public\europe-plomberie-chauffage-25a53508\ | 2026-11-04 : génération |
| Atelier Ciseaux Exemple | Coiffeur | Rouen | EXEMPLE (fictif), local | sites\public\atelier-ciseaux-exemple-d853d203\ | 2026-11-04 : génération |
| Atelier Pétale Exemple | Fleuriste | Rouen | EXEMPLE (fictif), local | sites\public\atelier-petale-exemple-f16bf51c\ | 2026-11-04 : génération |
| Robitaille Energie | plombier-chauffagiste | Doudeville | maquette générée, locale, non déployée | sites\public\robitaille-energie-7ad491ee\ | 2026-11-04 : génération |
| Fournil Exemple | Boulangerie | Rouen | EXEMPLE (fictif), local | sites\public\fournil-exemple-c0eabd62\ | 2026-11-04 : génération |
| Garage Exemple Mécanique | Garage automobile | Rouen | EXEMPLE (fictif), local | sites\public\garage-exemple-mecanique-bac687fe\ | 2026-11-04 : génération |
| Normandie Plomberie Chauffage | plombier-chauffagiste | Le Havre | maquette générée, locale, non déployée | sites\public\normandie-plomberie-chauffage-352fb386\ | 2026-11-04 : génération |
| Gps - Guiller Plomberie Services | plombier-chauffagiste | Le Havre | maquette générée, locale, non déployée | sites\public\gps-guiller-plomberie-services-141a08aa\ | 2026-11-04 : génération |
| P'tit Bouillon - LH | restaurant | Le Havre | maquette générée, locale, non déployée | sites\public\p-tit-bouillon-lh-8af7f289\ | 2026-11-04 : génération |
| Taverne Paillette | restaurant | Le Havre | maquette générée, locale, non déployée | sites\public\taverne-paillette-a5c66ea4\ | 2026-11-04 : génération |
| Restaurant La Tablée | restaurant | Le Havre | maquette générée, locale, non déployée | sites\public\restaurant-la-tablee-8cd6e13a\ | 2026-11-04 : génération |
| A M Energies | plombier-chauffagiste | Lansargues | maquette générée, locale, non déployée | sites\public\a-m-energies-a00ed153\ | 2026-11-04 : génération |
| Nicolas Morin | plombier-chauffagiste | Caux | maquette générée, locale, non déployée | sites\public\nicolas-morin-73226cac\ | 2026-11-04 : génération |
| Clim Mag | plombier-chauffagiste | Pérols | maquette générée, locale, non déployée | sites\public\clim-mag-e24759ff\ | 2026-11-04 : génération |
| Mon Adoucisseur 34 | plombier-chauffagiste | Roujan | maquette générée, locale, non déployée | sites\public\mon-adoucisseur-34-e03173db\ | 2026-11-04 : génération |
| Gra Plomberie | plombier-chauffagiste | Montauban-de-Luchon | maquette générée, locale, non déployée | sites\public\gra-plomberie-9673b765\ | 2026-11-04 : génération |
| Campodarne | plombier-chauffagiste | Montauban-de-Luchon | maquette générée, locale, non déployée | sites\public\campodarne-6aea0074\ | 2026-11-04 : génération |
| Luiz Plomberie | plombier-chauffagiste | Cierp-Gaud | maquette générée, locale, non déployée | sites\public\luiz-plomberie-6994d205\ | 2026-11-04 : génération |
| M'Concept | plombier-chauffagiste | Ponlat-Taillebourg | maquette générée, locale, non déployée | sites\public\m-concept-15702cae\ | 2026-11-04 : génération |
| Tav'Elec | plombier-chauffagiste | Tavel | maquette générée, locale, non déployée | sites\public\tav-elec-8f819158\ | 2026-11-04 : génération |
| Maison Las Clauzes | restaurant | Moux | maquette générée, locale, non déployée | sites\public\maison-las-clauzes-9ff7c8f7\ | 2026-11-04 : génération |
| Bistr'O bo bun | restaurant | Labège | maquette générée, locale, non déployée | sites\public\bistr-o-bo-bun-247d7c90\ | 2026-11-04 : génération |
| 3 Brasseurs | restaurant | Montpellier | maquette générée, locale, non déployée | sites\public\3-brasseurs-45888ce8\ | 2026-11-04 : génération |
| Il Ristorante | restaurant | Montpellier | maquette générée, locale, non déployée | sites\public\il-ristorante-5402ccbb\ | 2026-11-04 : génération |
| Le Canard sur le Toit | restaurant | Colomiers | maquette générée, locale, non déployée | sites\public\le-canard-sur-le-toit-9bd110d4\ | 2026-11-04 : génération |
| Le Beau Marché | restaurant | Beaumarchés | maquette générée, locale, non déployée | sites\public\le-beau-marche-635cee07\ | 2026-11-04 : génération |
| Le Grand Café | restaurant | Roujan | maquette générée, locale, non déployée | sites\public\le-grand-cafe-b1a6cca7\ | 2026-11-04 : génération |
| Le Céleste | restaurant | Le Havre | maquette générée, locale, non déployée | sites\public\le-celeste-21a81f8e\ | 2026-11-04 : génération |
| Quai des délices | restaurant | Le Havre | maquette générée, locale, non déployée | sites\public\quai-des-delices-2e4b0d28\ | 2026-11-04 : génération |
| Le Bicorne | restaurant | Étretat | maquette générée, locale, non déployée | sites\public\le-bicorne-20f38596\ | 2026-11-04 : génération |
| Les Tables de la Gare | restaurant | Neufchâtel-en-Bray | maquette générée, locale, non déployée | sites\public\les-tables-de-la-gare-824dc0e4\ | 2026-11-04 : génération |
| O'Tacos | restaurant | Le Havre | maquette générée, locale, non déployée | sites\public\o-tacos-f247f417\ | 2026-11-04 : génération |
| Brasserie Le Relais De La Poste | restaurant | Évreux | maquette générée, locale, non déployée | sites\public\brasserie-le-relais-de-la-poste-7a9c9aad\ | 2026-11-04 : génération |
| Le Royal Wok | restaurant | Dieppe | maquette générée, locale, non déployée | sites\public\le-royal-wok-e56ccb53\ | 2026-11-04 : génération |
| Bchef | restaurant | Montivilliers | maquette générée, locale, non déployée | sites\public\bchef-9d2a7481\ | 2026-11-04 : génération |
| Le Resto | restaurant | Le Havre | maquette générée, locale, non déployée | sites\public\le-resto-04aabecc\ | 2026-11-04 : génération |
| G La Dalle | restaurant | Le Havre | maquette générée, locale, non déployée | sites\public\g-la-dalle-dae02492\ | 2026-11-04 : génération |
| Don Gusto | restaurant | Le Havre | maquette générée, locale, non déployée | sites\public\don-gusto-4d8ffe39\ | 2026-11-04 : génération |
| Macicia | restaurant | Le Havre | maquette générée, locale, non déployée | sites\public\macicia-90989fef\ | 2026-11-04 : génération |
| Origines | restaurant | Le Havre | maquette générée, locale, non déployée | sites\public\origines-f22b04cc\ | 2026-11-04 : génération |
| Le Potager | restaurant | Le Havre | maquette générée, locale, non déployée | sites\public\le-potager-299490b6\ | 2026-11-04 : génération |
| Le Sorrento | restaurant | Le Havre | maquette générée, locale, non déployée | sites\public\le-sorrento-c8d14221\ | 2026-11-04 : génération |
| Le Catanzaro | restaurant | Neufchâtel-en-Bray | maquette générée, locale, non déployée | sites\public\le-catanzaro-066ca206\ | 2026-11-04 : génération |
| Crep'eat | restaurant | Montivilliers | maquette générée, locale, non déployée | sites\public\crep-eat-35b1551a\ | 2026-11-04 : génération |
| Les Enfants Sages | restaurant | Le Havre | maquette générée, locale, non déployée | sites\public\les-enfants-sages-4e768aa7\ | 2026-11-04 : génération |
| Nv Elec | électricien | Martigny | maquette générée, locale, non déployée | sites\public\nv-elec-6adb0f98\ | 2026-11-04 : génération |
| Acdc Electricite | électricien | Normanville | maquette générée, locale, non déployée | sites\public\acdc-electricite-17fe8fba\ | 2026-11-04 : génération |
| EMCS Plombier Chauffagiste Carreleur | plombier-chauffagiste | Gravigny | maquette générée, locale, non déployée | sites\public\emcs-plombier-chauffagiste-carreleur-70ede967\ | 2026-11-04 : génération |
| Le Tosny | restaurant | Épaignes | maquette générée, locale, non déployée | sites\public\le-tosny-153b533f\ | 2026-11-04 : génération |
| Le Jardin des Plumes | restaurant | Giverny | maquette générée, locale, non déployée | sites\public\le-jardin-des-plumes-49b68a10\ | 2026-11-04 : génération |
| Le Diplomate | restaurant | Le Havre | maquette générée, locale, non déployée | sites\public\le-diplomate-07649df0\ | 2026-11-04 : génération |
| Brasserie de la Cote | restaurant | Le Treport | maquette générée, locale, non déployée | sites\public\brasserie-de-la-cote-d96ea5d0\ | 2026-11-04 : génération |
| Route 76 | restaurant | Ecrainville | maquette générée, locale, non déployée | sites\public\route-76-0dfbd006\ | 2026-11-04 : génération |
| Labella | restaurant | Elbeuf | maquette générée, locale, non déployée | sites\public\labella-0abdcb0e\ | 2026-11-04 : génération |
| L'haumea | restaurant | Dieppe | maquette générée, locale, non déployée | sites\public\l-haumea-5ee04ae9\ | 2026-11-04 : génération |
| Le Cabestan et Sa Plume | restaurant | Yport | maquette générée, locale, non déployée | sites\public\le-cabestan-et-sa-plume-20d167d0\ | 2026-11-04 : génération |
| Harmonie Plomberie | plombier-chauffagiste | Amfreville-sur-Iton | maquette générée, locale, non déployée | sites\public\harmonie-plomberie-ca950940\ | 2026-11-04 : génération |
| Patagogo | restaurant | Beuzeville | maquette générée, locale, non déployée | sites\public\patagogo-9b8efbad\ | 2026-11-04 : génération |
| Le Saint Nicolas | restaurant | Gravigny | maquette générée, locale, non déployée | sites\public\le-saint-nicolas-666e3635\ | 2026-11-04 : génération |
| Ninja Sushi | restaurant | Beuzeville | maquette générée, locale, non déployée | sites\public\ninja-sushi-a4985409\ | 2026-11-04 : génération |
| Flavor | restaurant | Évreux | maquette générée, locale, non déployée | sites\public\flavor-76125cc9\ | 2026-11-04 : génération |
| Le Saint-Edouard | restaurant | Bernay | maquette générée, locale, non déployée | sites\public\le-saint-edouard-a0468b23\ | 2026-11-04 : génération |
| Le Moulin Fouret | restaurant | Saint-Aubin-le-Vertueux | maquette générée, locale, non déployée | sites\public\le-moulin-fouret-9d907ac4\ | 2026-11-04 : génération |
| La Savoyarde | restaurant | La Noë-Poulain | maquette générée, locale, non déployée | sites\public\la-savoyarde-1dc77508\ | 2026-11-04 : génération |
| Gael OLIVIER - Electricité générale | électricien | Saint-Aubin-lès-Elbeuf | maquette générée, locale, non déployée | sites\public\gael-olivier-electricite-generale-c76091a7\ | 2026-11-04 : génération |
| Arélec Énergie | électricien | Belbeuf | maquette générée, locale, non déployée | sites\public\arelec-energie-3e3d0177\ | 2026-11-04 : génération |
| Cogelec - Colombel Générale d'Electricité | électricien | Saint-Aubin-lès-Elbeuf | maquette générée, locale, non déployée | sites\public\cogelec-colombel-generale-d-electricite-9af6747d\ | 2026-11-04 : génération |
| Eco Confort Energies | plombier-chauffagiste | Belbeuf | maquette générée, locale, non déployée | sites\public\eco-confort-energies-af43e787\ | 2026-11-04 : génération |
| Palais des Regates | restaurant | Sainte-Adresse | maquette générée, locale, non déployée | sites\public\palais-des-regates-2be61689\ | 2026-11-04 : génération |
| L'oritano | restaurant | Rouen | maquette générée, locale, non déployée | sites\public\l-oritano-ffa3f8f5\ | 2026-11-04 : génération |
| Sarl Duval | plombier-chauffagiste | Thiberville | maquette générée, locale, non déployée | sites\public\sarl-duval-9e6aa844\ | 2026-11-04 : génération |
| JCD Electrique | électricien | Sotteville-lès-Rouen | maquette générée, locale, non déployée | sites\public\jcd-electrique-9a048449\ | 2026-11-04 : génération |
| Restaurant Le Bistrot Du Halage | restaurant | Sotteville-lès-Rouen | maquette générée, locale, non déployée | sites\public\restaurant-le-bistrot-du-halage-dbc6dd09\ | 2026-11-04 : génération |
| Le BunKer | restaurant | Sotteville-lès-Rouen | maquette générée, locale, non déployée | sites\public\le-bunker-a8c0e483\ | 2026-11-04 : génération |
| Roze | restaurant | Mathieu | maquette générée, locale, non déployée | sites\public\roze-10957be6\ | 2026-11-04 : génération |
| Le DG | restaurant | Lisieux | maquette générée, locale, non déployée | sites\public\le-dg-e9a0b60a\ | 2026-11-04 : génération |
| Le Vieux Normand | restaurant | Trouville-sur-Mer | maquette générée, locale, non déployée | sites\public\le-vieux-normand-cf00b638\ | 2026-11-04 : génération |
| La Réserve Péché Iodé | restaurant | Merville-Franceville-Plage | maquette générée, locale, non déployée | sites\public\la-reserve-peche-iode-d3d9ab37\ | 2026-11-04 : génération |
| La Table d'Hôtes | restaurant | Ouistreham | maquette générée, locale, non déployée | sites\public\la-table-d-hotes-ca5acaff\ | 2026-11-04 : génération |
| Le Patio | restaurant | Caen | maquette générée, locale, non déployée | sites\public\le-patio-59684ad9\ | 2026-11-04 : génération |
| Pizza Presto | restaurant | Colleville-Montgomery | maquette générée, locale, non déployée | sites\public\pizza-presto-4be1ca80\ | 2026-11-04 : génération |
| L'Antidote | restaurant | Cairon | maquette générée, locale, non déployée | sites\public\l-antidote-008d7548\ | 2026-11-04 : génération |
| Gani | restaurant | Villers-sur-Mer | maquette générée, locale, non déployée | sites\public\gani-2b90ebaa\ | 2026-11-04 : génération |
| La Terasse d'Emile | restaurant | Mondeville | maquette générée, locale, non déployée | sites\public\la-terasse-d-emile-8a2608ec\ | 2026-11-04 : génération |
| La Fabrique | restaurant | Lion-sur-Mer | maquette générée, locale, non déployée | sites\public\la-fabrique-e538a05d\ | 2026-11-04 : génération |
| Restaurant Inter-Administratif | restaurant | Caen | maquette générée, locale, non déployée | sites\public\restaurant-inter-administratif-63714321\ | 2026-11-04 : génération |
| Honorine | restaurant | Deauville | maquette générée, locale, non déployée | sites\public\honorine-28bc9385\ | 2026-11-04 : génération |
| Le Hasting's | restaurant | Cabourg | maquette générée, locale, non déployée | sites\public\le-hasting-s-99456019\ | 2026-11-04 : génération |
| Hostellerie Normande | restaurant | Houlgate | maquette générée, locale, non déployée | sites\public\hostellerie-normande-203dfcea\ | 2026-11-04 : génération |
| Let's wok | restaurant | Caen | maquette générée, locale, non déployée | sites\public\let-s-wok-1099dd9d\ | 2026-11-04 : génération |
| Memphis | restaurant | Mondeville | maquette générée, locale, non déployée | sites\public\memphis-bd1febd0\ | 2026-11-04 : génération |
| Le Manoir d'Hastings | restaurant | Bénouville | maquette générée, locale, non déployée | sites\public\le-manoir-d-hastings-dc2f20fc\ | 2026-11-04 : génération |
| Musa Giorgia | restaurant | Ifs | maquette générée, locale, non déployée | sites\public\musa-giorgia-7b6fc185\ | 2026-11-04 : génération |
| Le Victoria | restaurant | Honfleur | maquette générée, locale, non déployée | sites\public\le-victoria-2aec5976\ | 2026-11-04 : génération |
<!-- SUIVI:FIN -->

## Demandes en cours
| Date | De qui | Demande | État (à faire / en cours / à valider / fait) |
|---|---|---|---|

## Score qualité des maquettes
<!-- SCORES:DEBUT (écrit par generer.py, ne pas modifier à la main) -->
| Date | Maquette | Direction | Auto /70 | QA /30 | Total | Points à corriger |
|---|---|---|---|---|---|---|
| 2026-11-04 | exemple-electricite-technique-e87214db | technique | 70 | 30 | 100/100 | — |
| 2026-11-04 | exemple-elec-famille-rassurant-bd4ff644 | rassurant | 70 | 30 | 100/100 | — |
| 2026-11-04 | atelier-exemple-electricite-premium-2fcedd73 | premium | 70 | 30 | 100/100 | — |
| 2026-11-04 | exemple-plomberie-test-e488c97a | rassurant | 65 | 30 | 95/100 | Zone d'intervention (≥ 2 communes) (2/4) ; Preuves en haut, fondées sur des données fournies (2/5) |
| 2026-11-04 | exemple-toiture-test-9e622a35 | technique | 55 | 30 | 85/100 | Téléphone manquant ou invalide ; Numéro cliquable (en-tête ou hero, contact, pied, barre) (0/5) ; Barre d'appel fixe mobile (Appeler + une 2e action) (0/5) |
| 2026-11-04 | exemple-maconnerie-test-3c46931c | premium | 65 | 30 | 95/100 | Zone d'intervention (≥ 2 communes) (2/4) ; Preuves en haut, fondées sur des données fournies (2/5) |
| 2026-11-04 | bistro-exemple-48a524c0 | bistro | 70 | 30 | 100/100 | — |
| 2026-11-04 | la-table-exemple-du-marche-c7b5c52e | marche | 70 | 30 | 100/100 | — |
| 2026-11-04 | atelier-exemple-ceramique-0ae1f090 | atelier | 70 | 30 | 100/100 | — |
| 2026-11-04 | restaurant-fictif-alpha-025809a7 | bistro | 70 | 30 | 100/100 | — |
| 2026-11-04 | boutique-fictive-beta-028abdda | atelier | 70 | 30 | 100/100 | — |
| 2026-11-04 | electricite-fictive-gamma-8e1abaa5 | technique | 65 | 30 | 95/100 | Zone d'intervention (≥ 2 communes) (2/4) ; Preuves en haut, fondées sur des données fournies (2/5) |
| 2026-11-04 | plomberie-fictive-delta-243c0b9c | rassurant | 65 | 30 | 95/100 | Zone d'intervention (≥ 2 communes) (2/4) ; Preuves en haut, fondées sur des données fournies (2/5) |
| 2026-11-04 | creperie-fictive-epsilon-e783ade9 | bistro | 70 | 30 | 100/100 | — |
| 2026-11-04 | restaurant-fictif-zeta-a290ac64 | bistro | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | boutique-fictive-eta-e26d291e | atelier | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | electricite-fictive-theta-0724a954 | technique | 65 | — | 65/70 (QA à faire) | Zone d'intervention (≥ 2 communes) (2/4) ; Preuves en haut, fondées sur des données fournies (2/5) ; QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | maisons-exemple-1a69713c | maison | 70 | 30 | 100/100 | — |
| 2026-11-04 | sarah-elec-20e5ecea | technique | 68 | 30 | 98/100 | Zone d'intervention (≥ 2 communes) (2/4) |
| 2026-11-04 | antoine-soualah-electricite-e4bb73c3 | technique | 68 | 30 | 98/100 | Zone d'intervention (≥ 2 communes) (2/4) |
| 2026-11-04 | 2ac-electricite-df0c6906 | technique | 68 | 30 | 98/100 | Zone d'intervention (≥ 2 communes) (2/4) |
| 2026-11-04 | bricoleroy-31d4a1f9 | technique | 68 | 30 | 98/100 | Zone d'intervention (≥ 2 communes) (2/4) |
| 2026-11-04 | couvreur-rouen-toiture-84b859fd | technique | 68 | 30 | 98/100 | Zone d'intervention (≥ 2 communes) (2/4) |
| 2026-11-04 | paplorey-sebastien-plomberie-chauffage-6c784418 | rassurant | 68 | 30 | 98/100 | Zone d'intervention (≥ 2 communes) (2/4) |
| 2026-11-04 | cnet-plomberie-8732ebb0 | rassurant | 68 | 30 | 98/100 | Zone d'intervention (≥ 2 communes) (2/4) |
| 2026-11-04 | emv-3e49f04d | rassurant | 68 | 30 | 98/100 | Zone d'intervention (≥ 2 communes) (2/4) |
| 2026-11-04 | mj-service-d238ff21 | rassurant | 68 | 30 | 98/100 | Zone d'intervention (≥ 2 communes) (2/4) |
| 2026-11-04 | adas-bat-9dac48e5 | premium | 68 | 30 | 98/100 | Zone d'intervention (≥ 2 communes) (2/4) |
| 2026-11-04 | atelier-lumiere-exemple-d80eb712 | lumiere | 70 | 30 | 100/100 | — |
| 2026-11-04 | atelier-exemple-plomberie-230739a0 | eau | 63 | 30 | 93/100 | Preuves en haut, fondées sur des données fournies (0/5) ; Contenu : 4-6 services, 5-8 questions, 3-4 étapes (4/6) |
| 2026-11-04 | la-braise-exemple-c6dc7659 | braise | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | le-homard-bleu-7476cd38 | bistro | 58 | — | 58/70 (QA à faire) | Téléphone manquant ou invalide ; Numéro cliquable (en-tête ou hero, contact, pied, barre) (0/5) ; Barre d'appel fixe mobile (Appeler + une 2e action) (0/5) |
| 2026-11-04 | europe-plomberie-chauffage-25a53508 | eau | 49 | — | 49/70 (QA à faire) | Téléphone manquant ou invalide ; Numéro cliquable (en-tête ou hero, contact, pied, barre) (0/5) ; Barre d'appel fixe mobile (Appeler + une 2e action) (0/5) |
| 2026-11-04 | atelier-ciseaux-exemple-d853d203 | salon | 55 | — | 55/70 (QA à faire) | Zone d'intervention (≥ 2 communes) (0/4) ; Preuves en haut, fondées sur des données fournies (0/5) ; Contenu : 4-6 services, 5-8 questions, 3-4 étapes (0/6) |
| 2026-11-04 | atelier-petale-exemple-f16bf51c | petale | 53 | — | 53/70 (QA à faire) | Visuel du hero (photo ou zone à remplacer) (0/2) ; Zone d'intervention (≥ 2 communes) (0/4) ; Preuves en haut, fondées sur des données fournies (0/5) |
| 2026-11-04 | robitaille-energie-7ad491ee | eau | 49 | — | 49/70 (QA à faire) | Téléphone manquant ou invalide ; Numéro cliquable (en-tête ou hero, contact, pied, barre) (0/5) ; Barre d'appel fixe mobile (Appeler + une 2e action) (0/5) |
| 2026-11-04 | fournil-exemple-c0eabd62 | fournil | 55 | — | 55/70 (QA à faire) | Zone d'intervention (≥ 2 communes) (0/4) ; Preuves en haut, fondées sur des données fournies (0/5) ; Contenu : 4-6 services, 5-8 questions, 3-4 étapes (0/6) |
| 2026-11-04 | garage-exemple-mecanique-bac687fe | garage | 55 | — | 55/70 (QA à faire) | Zone d'intervention (≥ 2 communes) (0/4) ; Preuves en haut, fondées sur des données fournies (0/5) ; Contenu : 4-6 services, 5-8 questions, 3-4 étapes (0/6) |
| 2026-11-04 | normandie-plomberie-chauffage-352fb386 | eau | 49 | — | 49/70 (QA à faire) | Téléphone manquant ou invalide ; Numéro cliquable (en-tête ou hero, contact, pied, barre) (0/5) ; Barre d'appel fixe mobile (Appeler + une 2e action) (0/5) |
| 2026-11-04 | gps-guiller-plomberie-services-141a08aa | eau | 49 | — | 49/70 (QA à faire) | Téléphone manquant ou invalide ; Numéro cliquable (en-tête ou hero, contact, pied, barre) (0/5) ; Barre d'appel fixe mobile (Appeler + une 2e action) (0/5) |
| 2026-11-04 | p-tit-bouillon-lh-8af7f289 | bistro | 58 | — | 58/70 (QA à faire) | Téléphone manquant ou invalide ; Numéro cliquable (en-tête ou hero, contact, pied, barre) (0/5) ; Barre d'appel fixe mobile (Appeler + une 2e action) (0/5) |
| 2026-11-04 | taverne-paillette-a5c66ea4 | bistro | 58 | — | 58/70 (QA à faire) | Téléphone manquant ou invalide ; Numéro cliquable (en-tête ou hero, contact, pied, barre) (0/5) ; Barre d'appel fixe mobile (Appeler + une 2e action) (0/5) |
| 2026-11-04 | restaurant-la-tablee-8cd6e13a | bistro | 58 | — | 58/70 (QA à faire) | Téléphone manquant ou invalide ; Numéro cliquable (en-tête ou hero, contact, pied, barre) (0/5) ; Barre d'appel fixe mobile (Appeler + une 2e action) (0/5) |
| 2026-11-04 | a-m-energies-a00ed153 | eau | 59 | — | 59/70 (QA à faire) | Visuel du hero (photo ou zone à remplacer) (0/2) ; Zone d'intervention (≥ 2 communes) (2/4) ; Preuves en haut, fondées sur des données fournies (0/5) |
| 2026-11-04 | nicolas-morin-73226cac | eau | 59 | — | 59/70 (QA à faire) | Visuel du hero (photo ou zone à remplacer) (0/2) ; Zone d'intervention (≥ 2 communes) (2/4) ; Preuves en haut, fondées sur des données fournies (0/5) |
| 2026-11-04 | clim-mag-e24759ff | eau | 59 | — | 59/70 (QA à faire) | Visuel du hero (photo ou zone à remplacer) (0/2) ; Zone d'intervention (≥ 2 communes) (2/4) ; Preuves en haut, fondées sur des données fournies (0/5) |
| 2026-11-04 | mon-adoucisseur-34-e03173db | eau | 59 | — | 59/70 (QA à faire) | Visuel du hero (photo ou zone à remplacer) (0/2) ; Zone d'intervention (≥ 2 communes) (2/4) ; Preuves en haut, fondées sur des données fournies (0/5) |
| 2026-11-04 | gra-plomberie-9673b765 | eau | 57 | — | 57/70 (QA à faire) | Titre et description avec métier + ville (3/5) ; Visuel du hero (photo ou zone à remplacer) (0/2) ; Zone d'intervention (≥ 2 communes) (2/4) |
| 2026-11-04 | campodarne-6aea0074 | eau | 57 | — | 57/70 (QA à faire) | Titre et description avec métier + ville (3/5) ; Visuel du hero (photo ou zone à remplacer) (0/2) ; Zone d'intervention (≥ 2 communes) (2/4) |
| 2026-11-04 | luiz-plomberie-6994d205 | eau | 59 | — | 59/70 (QA à faire) | Visuel du hero (photo ou zone à remplacer) (0/2) ; Zone d'intervention (≥ 2 communes) (2/4) ; Preuves en haut, fondées sur des données fournies (0/5) |
| 2026-11-04 | m-concept-15702cae | eau | 57 | — | 57/70 (QA à faire) | Titre et description avec métier + ville (3/5) ; Visuel du hero (photo ou zone à remplacer) (0/2) ; Zone d'intervention (≥ 2 communes) (2/4) |
| 2026-11-04 | tav-elec-8f819158 | eau | 59 | — | 59/70 (QA à faire) | Visuel du hero (photo ou zone à remplacer) (0/2) ; Zone d'intervention (≥ 2 communes) (2/4) ; Preuves en haut, fondées sur des données fournies (0/5) |
| 2026-11-04 | maison-las-clauzes-9ff7c8f7 | bistro | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | bistr-o-bo-bun-247d7c90 | bistro | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | 3-brasseurs-45888ce8 | bistro | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | il-ristorante-5402ccbb | bistro | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | le-canard-sur-le-toit-9bd110d4 | bistro | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | le-beau-marche-635cee07 | bistro | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | le-grand-cafe-b1a6cca7 | bistro | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | le-celeste-21a81f8e | bistro | 58 | — | 58/70 (QA à faire) | Téléphone manquant ou invalide ; Numéro cliquable (en-tête ou hero, contact, pied, barre) (0/5) ; Barre d'appel fixe mobile (Appeler + une 2e action) (0/5) |
| 2026-11-04 | quai-des-delices-2e4b0d28 | bistro | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | le-bicorne-20f38596 | bistro | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | les-tables-de-la-gare-824dc0e4 | bistro | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | o-tacos-f247f417 | bistro | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | brasserie-le-relais-de-la-poste-7a9c9aad | bistro | 58 | — | 58/70 (QA à faire) | Téléphone manquant ou invalide ; Numéro cliquable (en-tête ou hero, contact, pied, barre) (0/5) ; Barre d'appel fixe mobile (Appeler + une 2e action) (0/5) |
| 2026-11-04 | le-royal-wok-e56ccb53 | bistro | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | bchef-9d2a7481 | bistro | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | le-resto-04aabecc | bistro | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | g-la-dalle-dae02492 | bistro | 58 | — | 58/70 (QA à faire) | Téléphone manquant ou invalide ; Numéro cliquable (en-tête ou hero, contact, pied, barre) (0/5) ; Barre d'appel fixe mobile (Appeler + une 2e action) (0/5) |
| 2026-11-04 | don-gusto-4d8ffe39 | bistro | 58 | — | 58/70 (QA à faire) | Téléphone manquant ou invalide ; Numéro cliquable (en-tête ou hero, contact, pied, barre) (0/5) ; Barre d'appel fixe mobile (Appeler + une 2e action) (0/5) |
| 2026-11-04 | macicia-90989fef | bistro | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | origines-f22b04cc | bistro | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | le-potager-299490b6 | bistro | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | le-sorrento-c8d14221 | bistro | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | le-catanzaro-066ca206 | bistro | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | crep-eat-35b1551a | bistro | 58 | — | 58/70 (QA à faire) | Téléphone manquant ou invalide ; Numéro cliquable (en-tête ou hero, contact, pied, barre) (0/5) ; Barre d'appel fixe mobile (Appeler + une 2e action) (0/5) |
| 2026-11-04 | les-enfants-sages-4e768aa7 | bistro | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | nv-elec-6adb0f98 | lumiere | 53 | — | 53/70 (QA à faire) | Téléphone manquant ou invalide ; Numéro cliquable (en-tête ou hero, contact, pied, barre) (0/5) ; Barre d'appel fixe mobile (Appeler + une 2e action) (0/5) |
| 2026-11-04 | acdc-electricite-17fe8fba | lumiere | 63 | — | 63/70 (QA à faire) | Zone d'intervention (≥ 2 communes) (2/4) ; Preuves en haut, fondées sur des données fournies (0/5) ; QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | emcs-plombier-chauffagiste-carreleur-70ede967 | eau | 59 | — | 59/70 (QA à faire) | Visuel du hero (photo ou zone à remplacer) (0/2) ; Zone d'intervention (≥ 2 communes) (2/4) ; Preuves en haut, fondées sur des données fournies (0/5) |
| 2026-11-04 | le-tosny-153b533f | bistro | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | le-jardin-des-plumes-49b68a10 | bistro | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | le-diplomate-07649df0 | bistro | 58 | — | 58/70 (QA à faire) | Téléphone manquant ou invalide ; Numéro cliquable (en-tête ou hero, contact, pied, barre) (0/5) ; Barre d'appel fixe mobile (Appeler + une 2e action) (0/5) |
| 2026-11-04 | brasserie-de-la-cote-d96ea5d0 | bistro | 58 | — | 58/70 (QA à faire) | Téléphone manquant ou invalide ; Numéro cliquable (en-tête ou hero, contact, pied, barre) (0/5) ; Barre d'appel fixe mobile (Appeler + une 2e action) (0/5) |
| 2026-11-04 | route-76-0dfbd006 | bistro | 58 | — | 58/70 (QA à faire) | Téléphone manquant ou invalide ; Numéro cliquable (en-tête ou hero, contact, pied, barre) (0/5) ; Barre d'appel fixe mobile (Appeler + une 2e action) (0/5) |
| 2026-11-04 | labella-0abdcb0e | bistro | 58 | — | 58/70 (QA à faire) | Téléphone manquant ou invalide ; Numéro cliquable (en-tête ou hero, contact, pied, barre) (0/5) ; Barre d'appel fixe mobile (Appeler + une 2e action) (0/5) |
| 2026-11-04 | l-haumea-5ee04ae9 | bistro | 58 | — | 58/70 (QA à faire) | Téléphone manquant ou invalide ; Numéro cliquable (en-tête ou hero, contact, pied, barre) (0/5) ; Barre d'appel fixe mobile (Appeler + une 2e action) (0/5) |
| 2026-11-04 | le-cabestan-et-sa-plume-20d167d0 | bistro | 58 | — | 58/70 (QA à faire) | Téléphone manquant ou invalide ; Numéro cliquable (en-tête ou hero, contact, pied, barre) (0/5) ; Barre d'appel fixe mobile (Appeler + une 2e action) (0/5) |
| 2026-11-04 | harmonie-plomberie-ca950940 | eau | 49 | — | 49/70 (QA à faire) | Téléphone manquant ou invalide ; Numéro cliquable (en-tête ou hero, contact, pied, barre) (0/5) ; Barre d'appel fixe mobile (Appeler + une 2e action) (0/5) |
| 2026-11-04 | patagogo-9b8efbad | bistro | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | le-saint-nicolas-666e3635 | bistro | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | ninja-sushi-a4985409 | bistro | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | flavor-76125cc9 | bistro | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | le-saint-edouard-a0468b23 | bistro | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | le-moulin-fouret-9d907ac4 | bistro | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | la-savoyarde-1dc77508 | bistro | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | gael-olivier-electricite-generale-c76091a7 | lumiere | 53 | — | 53/70 (QA à faire) | Téléphone manquant ou invalide ; Numéro cliquable (en-tête ou hero, contact, pied, barre) (0/5) ; Barre d'appel fixe mobile (Appeler + une 2e action) (0/5) |
| 2026-11-04 | arelec-energie-3e3d0177 | lumiere | 53 | — | 53/70 (QA à faire) | Téléphone manquant ou invalide ; Numéro cliquable (en-tête ou hero, contact, pied, barre) (0/5) ; Barre d'appel fixe mobile (Appeler + une 2e action) (0/5) |
| 2026-11-04 | cogelec-colombel-generale-d-electricite-9af6747d | lumiere | 53 | — | 53/70 (QA à faire) | Téléphone manquant ou invalide ; Numéro cliquable (en-tête ou hero, contact, pied, barre) (0/5) ; Barre d'appel fixe mobile (Appeler + une 2e action) (0/5) |
| 2026-11-04 | eco-confort-energies-af43e787 | eau | 49 | — | 49/70 (QA à faire) | Téléphone manquant ou invalide ; Numéro cliquable (en-tête ou hero, contact, pied, barre) (0/5) ; Barre d'appel fixe mobile (Appeler + une 2e action) (0/5) |
| 2026-11-04 | palais-des-regates-2be61689 | bistro | 58 | — | 58/70 (QA à faire) | Téléphone manquant ou invalide ; Numéro cliquable (en-tête ou hero, contact, pied, barre) (0/5) ; Barre d'appel fixe mobile (Appeler + une 2e action) (0/5) |
| 2026-11-04 | l-oritano-ffa3f8f5 | bistro | 58 | — | 58/70 (QA à faire) | Téléphone manquant ou invalide ; Numéro cliquable (en-tête ou hero, contact, pied, barre) (0/5) ; Barre d'appel fixe mobile (Appeler + une 2e action) (0/5) |
| 2026-11-04 | sarl-duval-9e6aa844 | eau | 49 | — | 49/70 (QA à faire) | Téléphone manquant ou invalide ; Numéro cliquable (en-tête ou hero, contact, pied, barre) (0/5) ; Barre d'appel fixe mobile (Appeler + une 2e action) (0/5) |
| 2026-11-04 | jcd-electrique-9a048449 | lumiere | 53 | — | 53/70 (QA à faire) | Téléphone manquant ou invalide ; Numéro cliquable (en-tête ou hero, contact, pied, barre) (0/5) ; Barre d'appel fixe mobile (Appeler + une 2e action) (0/5) |
| 2026-11-04 | restaurant-le-bistrot-du-halage-dbc6dd09 | bistro | 60 | — | 60/70 (QA à faire) | Téléphone manquant ou invalide ; Numéro cliquable (en-tête ou hero, contact, pied, barre) (0/5) ; Barre d'appel fixe mobile (Appeler + une 2e action) (0/5) |
| 2026-11-04 | le-bunker-a8c0e483 | bistro | 60 | — | 60/70 (QA à faire) | Téléphone manquant ou invalide ; Numéro cliquable (en-tête ou hero, contact, pied, barre) (0/5) ; Barre d'appel fixe mobile (Appeler + une 2e action) (0/5) |
| 2026-11-04 | roze-10957be6 | bistro | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | le-dg-e9a0b60a | bistro | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | le-vieux-normand-cf00b638 | bistro | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | la-reserve-peche-iode-d3d9ab37 | bistro | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | la-table-d-hotes-ca5acaff | bistro | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | le-patio-59684ad9 | bistro | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | pizza-presto-4be1ca80 | bistro | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | l-antidote-008d7548 | bistro | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | gani-2b90ebaa | bistro | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | la-terasse-d-emile-8a2608ec | bistro | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | la-fabrique-e538a05d | bistro | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | restaurant-inter-administratif-63714321 | bistro | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | honorine-28bc9385 | bistro | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | le-hasting-s-99456019 | bistro | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | hostellerie-normande-203dfcea | bistro | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | let-s-wok-1099dd9d | bistro | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | memphis-bd1febd0 | bistro | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | le-manoir-d-hastings-dc2f20fc | bistro | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | musa-giorgia-7b6fc185 | bistro | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
| 2026-11-04 | le-victoria-2aec5976 | bistro | 70 | — | 70/70 (QA à faire) | QA non lancée (node sites\outils\qa.mjs) |
<!-- SCORES:FIN -->

## Décisions de Liam
- 21 oct. 2026 : sites « beaucoup mieux », style de grandes marques avec un peu de 3D « mais pas trop » ; le site doit convaincre l'artisan et faire appeler le client ; photos d'internet seulement avec licence claire ; un lien par prospect.
- 23 oct. 2026 : priorité = maquettes de qualité dans toute la France pour novembre 2026 ; moteur de modèles + prompt maître + script CSV.
- 24 oct. 2026 : modèles restaurant (2 directions) et commerce (1 direction, 3D légère optionnelle avec image de repli) ajoutés ; `prospects.csv` modèle vide créé ; script testé sur 5 lignes fictives (restaurant, commerce, électricien, plombier, crêperie).
- 24 oct. 2026 : déploiement Vercel des 6 maquettes fictives : Liam a répondu « Pas maintenant ». Rien n'a été créé sur Vercel. Dossier prêt : `sites\deploiement\`.
- 24 oct. 2026 (nuit) : projet Vercel `b2b-demos` créé (CLI, compte de Liam), protection Vercel Auth désactivée, 6 maquettes fictives déployées en production, `noindex` + `robots.txt` Disallow, liens vérifiés (HTTP 200, console sans erreur, 3D du vase OK). Base : https://b2b-demos.vercel.app/<dossier>/ . Un vrai prospect n'a un lien actif qu'après son propre déploiement (accord de Liam).
- 24 oct. 2026 : bistro et céramique VALIDÉS (copies dans `sitesvalides\`, empreintes dans `sites\sorties\hash-valides.txt`, ne pas modifier). « Marché » refait (hero immersif, bouton Réservations fixe, événements avec « Demander un devis », histoire du lieu) : captures avant/après dans `sites\sorties\avant-marche\` et `sites\sorties\captures\la-table-exemple-du-marche-c7b5c52e\`. En attente de l'OK de Liam avant tout redéploiement. Point ouvert : LCP 3,0 s (cible 2,5 s), performance 94.
- 26 oct. 2026 : électricien « rassurant » et « premium » vérifiés en ligne (HTTP 200, identiques aux fichiers locaux, noindex, polices chargées ; Lighthouse local 99 et 100). Correction d'un caractère de contrôle (le caractère de contrôle backspace) dans le score « Événements » de `generer.py` : « Maisons Exemple » passe à 100/100.
- 26 oct. 2026 : lot 1 partiel (10 prospects réels de `lots\lot1.csv`, maquettes locales non déployées, QA 98/100 chacune, brouillons « à valider », suivi « à contacter »). Devis et objections dans `docs\DEVIS-ET-OBJECTIONS.md`.
- 26 oct. 2026 : nouvelle méthode « premium 2026 » (spec dans recherche-sites/11-premium-2026.md, texte reçu coupé à « Règles bloquantes du »). Plus de maquette par prospect : thème de base + DA par métier. DA A « Atelier Lumière » (électricien) construite dans sites/moteur (modeles3.py, themes/lumiere.css, bloc « lumiere » de metiers/electricien.json), direction par défaut de l'électricien. Anciens styles technique/rassurant/premium conservés : direction=technique|rassurant|premium, ou python sites/moteur/generer.py --archive. Exemple : sites/public/atelier-lumiere-exemple-d80eb712 (QA 100/100, non déployé). Maquettes de lots/lot1.csv mises de côté. Reste : photos des 3 prestations (zones « à remplacer »), 3D facultative au clic (pas de modèle d'ampoule libre), DA des autres métiers, fin de la spec.
- 26 oct. 2026 : spec « premium 2026 » complétée (recherche-sites/11-premium-2026.md). Rendu validé par Liam, hero intact. Règles bloquantes codées dans sites/moteur/modeles3.py (badge sans numéro, note/avis sans source, photo sans entrée dans sites/moteur/photos/CREDITS.json, « 24 h/24 » sans horaires, chiffre hors variables, alt, aggregateRating : page non écrite si un contrôle échoue). 3 photos Unsplash (éclairage, tableau, rénovation) sur la page modèle, utilisées seulement pour exemple=oui ou illustrations=oui. Ampoule SVG gardée, pas de 3D. QA : perf/a11y/SEO/BP 100, LCP 1,6 s, CLS 0,001, lisible sans JS, clavier OK. qa.mjs mesure maintenant CLS, mode sans JS et tabulation. Non déployé.
- 26 oct. 2026 : page modèle « Atelier Lumière » déployée (OK de Liam pour cette page seulement) : https://b2b-demos.vercel.app/atelier-lumiere-exemple-d80eb712/ . Seule cette page a été ajoutée au projet b2b-demos ; les 6 autres pages sont restées identiques octet pour octet (bistro, céramique, marché, 3 électricien anciens styles). Vérifié en ligne : HTTP 200, console propre, noindex (en-tête X-Robots-Tag + meta), polices Fraunces et Inter chargées, 3 images chargées, Lighthouse mobile perf 100 / accessibilité 100 / SEO 100 / bonnes pratiques 100, LCP 1,3 s, CLS 0,001. Photo « tableau » remplacée par un interrupteur noir à manette laiton (Unsplash, Lunyon, CREDITS.json). Première tentative de déploiement bloquée par Vercel (auteur du commit Git local sans droit sur le projet) : déployé depuis une copie hors du dépôt. Résultats : sites/sorties/verif-en-ligne-lumiere.json.
- 26 oct. 2026 : « Atelier Lumière » v3 (retour de Liam : trop simple, pas assez animé, surtout sur mobile). Hero (mise en page, texte), palette, polices et règles bloquantes conservés. Animations : hero orchestré en CSS pur (titre mot par mot, ampoule qui s'allume, accroche puis boutons en dernier, transform seul, texte toujours opaque) ; fil rouge « allumage » piloté par le scroll (barre de progression, halo et ampoule qui montent, aube sombre vers clair après le hero) ; révélations sur toutes les sections (CSS animation-timeline si disponible, sinon GSAP + ScrollTrigger, mobile compris) ; méthode avec ligne qui se dessine et étapes qui s'allument (mobile et bureau) ; cartes au toucher/survol, FAQ animée, bouton Appeler qui sonne ; tout sous prefers-reduced-motion. Contenu : curseur avant/après (input range, clavier OK, 2 photos CREDITS.json), bandeau défilant (statique si mouvement réduit), chiffres animés seulement depuis les variables note/avis/années, galerie de 4 photos d'exemple, carte-schéma SVG de la zone + liste HTML, 3 engagements à confirmer. Scripts : gsap 3.15 + ScrollTrigger + lumiere.js = 123 Ko bruts, injectés à la première interaction ou 1,8 s après load (en defer au parsing, le LCP simulé de Lighthouse montait de 1,6 s à 2,5 s). QA : perf/a11y/SEO/BP 100, LCP 1,4 s, CLS 0, sans JS lisible, clavier OK, console propre. Vidéos MP4 : sites/sorties/videos/. NON déployé : attente de l'OK de Liam.
- 26 oct. 2026 : « Atelier Lumière » v3 déployée au même lien que la v2 (OK de Liam) : https://b2b-demos.vercel.app/atelier-lumiere-exemple-d80eb712/ . Déploiement depuis une copie hors du dépôt Git (le déploiement dans le dépôt est bloqué par Vercel : auteur du commit sans droit sur le projet). Seuls la page Lumière (dossier et images) et assets/js/lumiere.js ont changé ; les 6 autres pages sont restées identiques octet pour octet. Scripts injectés après le premier affichage (conservé). Vérifié en ligne : HTTP 200 (page, 9 images, polices Fraunces et Inter, gsap, ScrollTrigger, lumiere.js), console propre à 390 et 1280 px, noindex (en-tête + meta), aucun débordement, curseur avant/après (clavier : 0 %, 100 %, découpe qui suit) et bandeau défilant OK. Lighthouse mobile sur l'adresse publique, 3 passes : perf 100, accessibilité 100, SEO 100, bonnes pratiques 100, LCP 1,4 s, CLS 0 à 0,003, TBT 20 à 60 ms, poids 162 à 193 Ko. Détail : sites/sorties/verif-en-ligne-lumiere-v3.json.
- 26 oct. 2026 : site vitrine de l'activité créé dans sites/agence/ (non déployé, voir docs/MEMOIRE-B2B.md). Ne touche pas aux maquettes.
- 30 oct. 2026 : page pilote coiffeur « verre clair » (v2, validée par Liam) déployée en production avec l'accord de Liam : https://b2b-demos.vercel.app/atelier-ciseaux-verre-exemple-0501955c/ . Déploiement depuis une copie hors dépôt Git = les 13 pages déjà en ligne (empreintes SHA-1 identiques à la production du jour ; la-table : version en ligne conservée, la v2 locale reste non déployée) + la nouvelle page. Vérifié : 14 ressources en HTTP 200, en-tête X-Robots-Tag + meta noindex, console propre à 390 et 1280 px, polices chargées, bouton d'appel 48 px. `agents\liens-metiers.json` : coiffeur pointe vers cette page ; un e-mail coiffeur construit par construire_bloc contient ce lien et « (exemple, pas votre site) ». L'ancienne page atelier-ciseaux-exemple-d853d203 reste en ligne (anciens e-mails). Sources locales : sites\coiffeur-pilote\ (v1 sombre : sites\coiffeur-pilote-v1\).
- 30 oct. 2026 : restaurant pilote « Le Velours » v2 (immersif cinétique, validé par Liam, sans rideau d'entrée ni bande de mots) déployé en production avec son accord : https://b2b-demos.vercel.app/le-velours-exemple-ef5bae7c/ . Même méthode que le coiffeur : copie hors dépôt = les 14 pages déjà en ligne (production vérifiée avant : dernier déploiement = celui du coiffeur) + la nouvelle ; les autres pages restent en HTTP 200 (la-table et coiffeur identiques octet pour octet). Vérifié en ligne : 20 fichiers en 200 (three.js, plate3d.js, images, polices), noindex (en-tête + meta), console propre à 390 et 1280 px, assiette en WebGL sur ordinateur. Lighthouse mobile (serveur local compressé) : perf 98, accessibilité 100, bonnes pratiques 100, LCP 2,3 s, CLS 0. agents\liens-metiers.json : restaurant pointe vers cette page ; un e-mail restaurant construit par construire_bloc contient ce lien et « (exemple, pas votre site) ». L'ancien lien restaurant (la-braise) reste en ligne. Sources : sites\restaurant-pilote\ (v1 : sites\restaurant-pilote-v1\ ; version avec rideau et bande de mots : sites\restaurant-pilote-v2-rideau\).
- 30 oct. 2026 (correctif) : sur le restaurant « Le Velours » déployé le matin, la carte, la photo du saumon et les textes de « La salle » ne s'affichaient pas : leurs révélations par masque ne se déclenchaient jamais (un IntersectionObserver ne voit pas un élément entièrement masqué par clip-path). Corrigé (lecture de la position au défilement) et redéployé au même lien ; vérifié en ligne : 11 éléments sur 11 révélés à 390 et 1280 px, console propre, les 14 autres pages toujours en 200. Même correction appliquée au pilote coiffeur v3 (local, non déployé : sites\coiffeur-pilote\, famille verre clair cinétique, ciseaux 3D, note 9/10).
- 30 oct. 2026 : coiffeur pilote v3 (verre clair cinétique, ciseaux 3D, validé par Liam) déployé en production avec son accord : https://b2b-demos.vercel.app/atelier-ciseaux-cine-exemple-546e7247/ . Même méthode (copie hors dépôt = les 16 pages en ligne, production vérifiée avant ; la-table, restaurant et coiffeur v2 identiques). Vérifié en ligne section par section à 390 et 1280 px, bas de page compris : 17 fichiers en 200, noindex (en-tête + meta), 22 éléments sur 22 révélés, 10 mèches, aucune image cassée, aucun débordement, console propre, polices chargées, ciseaux en WebGL sur ordinateur. Captures : sites\coiffeur-pilote\captures-en-ligne\. agents\liens-metiers.json : coiffeur pointe vers cette page ; e-mail coiffeur de test : nouveau lien, mention « (exemple, pas votre site) ». L'ancienne page coiffeur (atelier-ciseaux-verre-exemple-0501955c) reste en ligne pour les e-mails déjà envoyés.
