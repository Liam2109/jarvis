# Offres sites : « Landing page pro » et « Site complet » (même moteur)
Brouillon du 26 oct. 2026, à valider par Liam. Aucun prix n'est fixé ici : les prix sont à décider par Liam (colonne « à décider »).

## Principe
Un seul moteur (`sites\moteur\generer.py`, mêmes thèmes, mêmes contenus par métier, mêmes variables CSV). Une colonne CSV `offre` : `landing` (défaut) ou `complet`.

| | Landing page pro | Site complet |
|---|---|---|
| Pages | 1 (déjà produite par le moteur) | 3 à 5 : Accueil, Services (ou Carte / Boutique), Réalisations ou Galerie, À propos + zone, Contact ; mentions légales en pied |
| Pour qui | Artisan ou commerce qui veut surtout être appelé | Qui veut présenter son travail, rassurer, être trouvé par ville |
| Contenu | Hero, preuves, services, zone, avis réels, FAQ, formulaire, barre d'appel mobile | Idem, réparti en pages ; une page par service principal possible (SEO local) |
| Technique | HTML statique, Lighthouse 85+ / 95+ / 95+, noindex tant que non vendu | Idem, menu commun, plan du site, balisage LocalBusiness |
| Prix | à décider | à décider |

## Options (communes, chacune sur devis, aucune dépense sans OK de Liam)
1. **Nom de domaine + DNS** : achat au nom du client (idéal : compte du client, ou facturé à l'identique), DNS pointé vers Vercel, HTTPS automatique. Coût annuel du domaine à vérifier au moment de l'achat. Dépense seulement avec l'OK de Liam.
2. **E-mail professionnel** (contact@domaine) : fournisseur à choisir par Liam (comparer le prix et la simplicité). Réglages MX, SPF, DKIM, DMARC. Aucun compte créé sans OK.
3. **Maintenance** (mensuelle ou annuelle) : changements de texte, photos, horaires, sauvegarde, contrôle de disponibilité. Hors forfait : nouvelle page, fonctionnalité, intégration (voir `agents\dev-sites.md`).

## Ce qui est déjà prêt / ce qui manque
- Prêt : landing page pour 3 familles (artisan, restaurant, commerce) + groupe de restaurants ; QA et score automatiques.
- À construire (non fait, en attente du OK) : `offre=complet` dans `generer.py` (une page `.html` par section, menu partagé, QA sur chaque page, score par page) ; page « options » pour le client ; gabarit de devis.
- Rappel : textes de raisons, délais, garanties = propositions à confirmer par l'artisan ; aucun faux avis ni chiffre.

## À décider par Liam
- Les prix des deux offres et des trois options, et si l'e-mail pro est revendu ou seulement installé.
- Domaine au nom du client ou de LM MULTI-SERVICES.
- Feu vert pour construire `offre=complet`.
