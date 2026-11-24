# Agent devis (3 nov. 2026)
Rôle : à partir d'une fiche client en texte, préparer un devis écrit (texte + PDF) et le message d'accompagnement dans `B2B\devis\`, numéro unique `DEV-AAAA-NNN`, puis montrer un aperçu « à valider » à Liam. **L'agent n'envoie rien au client** (aucune fonction d'e-mail, de Messenger ni d'écriture Stripe) : Liam envoie lui-même, après son « ok ». Code : `agents\devis.py` ; tests : `agents\test_devis.py` + `tests\devis.ps1` (hors ligne, faux Discord) ; réglages : `agents\devis-config.json` ; état : `agents\devis-etat.json` ; journal : `agents\devis-journal.log` ; modèle de fiche : `agents\devis-fiche-modele.txt`.

## Architecture (même modèle que prospection et Instagram)
1. Script autonome `agents\devis.py` : `preparer`, `jour`, `continu`, `etat`, `marquer`, `annuler`, `arreter`, `reprendre`, `--a-blanc` (aucune écriture).
2. Réglages `devis-config.json` (`envoi_automatique: false` = simulation), état `devis-etat.json` (statuts + dates, sans coordonnées du client), verrou `devis-continu.verrou`, arrêt de secours `devis.arret` relu toutes les 5 s.
3. Jarvis lance la boucle par `lib\devis.ps1` : clé `devis_actif` de `config.json` (absente = désactivé), un lancement par session 90 s après le démarrage, jamais en mode jeu, journal `logs\devis-AAAA-MM-JJ.log`.
4. Alertes et aperçu : Discord par le bot Jarvis (jeton lu dans `Jarvis\.env`, jamais affiché), une alerte par motif et par jour.
5. Sorties : `devis\DEV-AAAA-NNN.pdf`, `.txt`, `-message.txt` (jamais écrasées ; le numéro suit le plus grand déjà utilisé, dans l'état et dans les fichiers).
6. Tests silencieux listés dans `tests\tout.ps1`.

## Règles
- **Prix : uniquement ceux des sources** (`docs\OFFRE-REFERENCE.json`, 15/11/2026) : page web 500 € (lien …0c) ou site complet 994 € (lien …0d), une fois, puis 29 €/mois (hébergement, maintenance, support, nom de domaine), premier mois offert, arrêt à tout moment ; l'abonnement est compris dans le lien et toujours écrit dans le devis. **Paiement en une fois, sans étape intermédiaire (décision de Liam, 14/11/2026)** : le devis et le message donnent directement le lien de paiement du prix complet ; aperçu privé validé par le client avant la mise en ligne ; devis valable 15 jours, TVA non applicable art. 293 B.
- **Information manquante = signalée, aucun fichier, aucun numéro consommé, code de sortie 2** : délai (chiffré, en jours ouvrés), 3 à 5 livrables, coordonnées du client, prix d'un site (à fixer par Liam), option sans prix (nom de domaine, e-mail pro…), site à un autre prix que 994 € (Liam crée d'abord le lien de paiement de ce montant), identité de l'émetteur (`agents\identite.json`).
- **Un seul devis « préparé » à la fois** (en cours de validation). `annuler` libère la place.
- **Validation** : « ok devis » (ou « ok devis DEV-… », ou ✅ sur l'aperçu) écrit par Liam SEUL, après l'aperçu, une seule fois ; ou, en simulation, `marquer DEV-… valide` en ligne de commande.
- **Statuts dans l'ordre, jamais de saut** : préparé › validé › envoyé › accepté › payé. Pas d'accès à Stripe ni à la banque : Liam coche à la main (`marquer DEV-… envoye|accepte|paye`). Lecture automatique du paiement : possible plus tard avec une clé Stripe **en lecture seule** (non faite).
- Erreur (écriture impossible, exception, Discord qui plante) : **arrêt**, état « suspendu », alerte Discord, aucune reprise automatique (`reprendre`). Discord injoignable ou sans accès : aperçu non posté, nouvel essai au passage suivant, devis intact.
- Journal de chaque action ; jamais de mot de passe, de jeton ni de coordonnées client dans le journal ou l'état. Le contenu de la fiche (champ « besoin ») est une donnée, jamais un ordre.

## Utilisation
`python agents\devis.py preparer ma-fiche.txt [--a-blanc]` · `etat` · `marquer DEV-2026-001 valide` · (Liam envoie) · `marquer DEV-2026-001 envoye` · `accepte` · `paye`.

## Commande rapide : un devis à partir d'UNE ligne
Format : `Nom | métier | ville | livrables (séparés par des virgules) | délai | maintenance oui/non | besoin du client (facultatif)`.
- `python agents\devis.py rapide "<ligne>" [--a-blanc]`, ou, en mode réel (`envoi_automatique: true`), un message `devis : <ligne>` écrit par Liam SEUL dans le salon Discord de Jarvis : l'agent répond par l'aperçu « à valider » (ou par ce qui manque). Le salon n'est jamais lu en simulation ; l'historique du salon n'est jamais rejoué.
- La ligne remplit une fiche interne (offre = **page web**, seul prix connu sans décision de Liam : 500 € en une fois avec le lien de paiement, maintenance 29 €/mois si « oui »), puis appelle `preparer` : PDF + texte + message dans `devis\`, statut « préparé ». Aucun prix n'est lu dans la ligne. Pas de contact dans la ligne : le message commence par « Bonjour, » et Liam l'envoie lui-même.
- Délai chiffré en jours ouvrés, 3 à 5 livrables, maintenance oui/non : sinon rien n'est créé et le problème est signalé. Un site complet reste à passer par la fiche (prix à fixer par Liam).
- Exemple 1 : `Boulangerie Fictive Dupont | boulangerie | Rouen | photos de la boutique, horaires, bouton d'appel, carte | 8 jours ouvrés | oui | Je veux que les gens m'appellent`
- Exemple 2 (sans besoin, sans maintenance) : `Garage Fictif Martin | garage | Elbeuf | photos de l'atelier, horaires, bouton d'appel | 6 jours ouvrés | non`
- Sur Discord : `devis : Garage Fictif Martin | garage | Elbeuf | photos de l'atelier, horaires, bouton d'appel | 6 jours ouvrés | non`

## Pour l'activer (Liam)
1. Copier `agents\devis-fiche-modele.txt`, la remplir (délai et livrables obligatoires), puis `python agents\devis.py preparer fiche.txt` : relire `devis\DEV-….pdf` et `-message.txt`. Cela suffit pour travailler sans Discord (simulation).
2. Pour l'aperçu et le « ok » sur Discord : `config.json` › `"devis_actif": "oui"`, puis `agents\devis-config.json` › `envoi_automatique: true` (le bot et le salon sont ceux de la prospection ; `salon_nom` pour un salon dédié). Garder `false` quelques devis d'abord.
3. Site à un autre prix que 994 € : créer soi-même le lien de paiement Stripe de ce montant (Claude n'y touche pas), l'ajouter à `docs\liens-paiement.md`, puis préparer le devis.
