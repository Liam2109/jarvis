# Sources de données

## OpenStreetMap (découverte « depuis les sites »)
- Données © les contributeurs d'OpenStreetMap, licence **ODbL 1.0** : https://www.openstreetmap.org/copyright
- Accès par l'API **Overpass** (https://overpass-api.de) : une requête à la fois, pause entre deux requêtes (`pause_overpass_s`), User-Agent explicite, nouvel essai espacé après un refus (429, 5xx).
- Champs lus : `website`, `contact:website`, `email`, `contact:email`, `phone`, `contact:phone`, nom, adresse. Rien d'autre.
- Les données OpenStreetMap ne sont ni republiées ni revendues. La mention de la source figure dans `prospection-trouves.csv` (colonne `source`).
- Activation : `decouverte_osm` dans `agents\prospection-config.json` (défaut `false`).

## Annuaire officiel des entreprises (recherche-entreprises.api.gouv.fr)
Nom, activité (NAF), siège (commune, code postal). Pas de téléphone, d'e-mail ni de site dans cette source.

## Site de l'entreprise elle-même
Page d'accueil lue une seule fois par prospect, après lecture de `robots.txt`, avec un délai poli (`pause_site_s`) ; pages contact / mentions légales seulement pour y trouver une adresse publiée par l'entreprise. Adresses de plateformes (wix, ovh, ionos…) ignorées. Aucune adresse n'est devinée ni générée.

## Ce qui n'est jamais lu automatiquement
Google, Facebook, fiches Google Business. Liam peut coller une adresse ou un lien dans `docs\liste-appels-AAAA-MM-JJ.md` ; l'agent relit ces colonnes à chaque cycle.
