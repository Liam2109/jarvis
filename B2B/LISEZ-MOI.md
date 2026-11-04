# Sites pour artisans (LM MULTI-SERVICES) — kit de démarrage (21 oct. 2026)

## Ordre à suivre
1. `python sourcing.py` -> `prospects.csv` (artisans actifs autour de Rouen, base Sirene, gratuit).
2. Compléter téléphone / note / avis / site avec Outscraper (Google Maps, 500 fiches gratuites). Garder ceux SANS site, note >= 4, >= 10 avis.
3. `python generer.py prospects.csv` -> un fichier par artisan dans `maquettes\`.
4. Héberger sur Vercel (gratuit), puis APPELER + envoyer le lien (SMS ou mail).

## Règles (issues de la recherche)
- Téléphone d'abord (numéro pro de la fiche Google), mail/SMS avec le lien de la maquette ensuite. Pas de WhatsApp à froid.
- Chaque message : qui tu es (LM MULTI-SERVICES + SIRET), d'où vient le contact (fiche Google publique), "Répondez STOP". Liste d'exclusion obligatoire.
- Mail froid : domaine secondaire + SPF/DKIM/DMARC + warm-up 14-21 jours, 20-30 mails/boîte/jour. Jamais depuis ton Gmail.
- Devis : formulaire de rétractation 14 jours (art. L221-3) si signature chez l'artisan, pas d'acompte le jour même.
- Offre : 59 EUR/mois sans frais de création, ou 590-990 EUR + 19-29 EUR/mois. 3 premiers clients : tarif fondateur contre un avis Google.
- Meta Ads seulement après 1-3 ventes (10-20 EUR/jour).
- Aucun envoi sans ton OK.

## Objectifs réalistes 30 jours
20-30 contacts/jour, 6-12 rendez-vous, 1-3 ventes (estimation, pas une garantie).
