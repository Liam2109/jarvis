---
name: agent-linkedin-equipe
description: Fiche de rôle de l'équipe LinkedIn (pôle Prospection) — chaque jour ouvré à 08:00 sur le serveur, prépare le « lot du jour » affiché dans la rubrique LinkedIn du tableau de bord (post à coller, ~10 commentaires, 20 demandes de connexion sans note, DM prêts pour les acceptations, relance unique à J+3) ; Liam envoie tout lui-même, rien n'est envoyé ni scrapé. À utiliser pour vérifier, corriger ou régler linkedin-equipe.py (jour, coche, etat, exporter).
---

# Équipe LinkedIn — des agents préparent, Liam envoie

**Responsable :** Prospection. **Script :** `B2B/agents/linkedin-equipe.py`. **Contrat :** `B2B/harness/contrats/linkedin-equipe.json`. **Réglages :** `B2B/agents/linkedin-equipe-config.json`.
**Tâche serveur :** `jour` à 08:00, lundi à vendredi ; elle tourne seulement si `linkedin-equipe` est dans `agents_actifs` (choix de Liam).

## Le lot du jour (rubrique LinkedIn du tableau de bord du serveur, jamais Discord)
1. **Post** : le prochain post « prospect » de la file de l'agent `linkedin` (skill linkedin-posts), sans activer cet agent ni toucher à `file.json`. Stock vide : code 5 et note « demandez un lot à Claude ».
2. **Commentaires** (~10) : posts LinkedIn publics trouvés par un moteur de recherche (jamais en parcourant LinkedIn), brouillon par le modèle local Ollama s'il répond, sinon gabarit signalé « relisez avant de poster ».
3. **Demandes de connexion SANS note** : `demandes_par_jour` (20) par jour ouvré, plafond strict `plafond_semaine` (100 ; on monte par paliers dans le fichier de réglages). 70 % entreprises (`part_entreprises`), 30 % appelants / closers.
   - Entreprises : décideur (dirigeant connu quand le fichier le donne, sinon recherche « gérant … »), 1 à 9 personnes (effectif non renseigné gardé), bâtiment d'abord (`commerces_locaux` : true les élargit), Seine-Maritime d'abord (`zone_niveau` : 2 ajoute Eure, Calvados, Manche, Orne ; un niveau épuisé passe au suivant), créations récentes en priorité (l'activité LinkedIn réelle n'est pas mesurable sans scraping). Sources : `prospects_rouen.csv`, `prospects.csv`, `prospection-trouves.csv` ; jamais une entreprise déjà contactée (suivi e-mails, registre d'appels).
   - Appelants / closers : une recherche LinkedIn (intitulé × zone × page) ; Liam choisit le profil dans la recherche.
   - Chaque cible : lien de recherche LinkedIn cliquable + DM court prêt (jamais deux textes identiques, pas de « Bonjour prénom », aucune promesse ni chiffre).
4. **Suivi** (cases du tableau de bord, POST `/api/linkedin` de `outils\servir-dashboard.py`, ou `python agents\linkedin-equipe.py coche ID ACTION`) : demande envoyée -> acceptée (le DM sort dans « DM du jour ») -> DM envoyé -> a répondu. Relance unique 3 jours après un DM sans réponse. Réponse positive -> registre (`À rappeler`, source LinkedIn) donc leads chauds.

## Ce qu'il ne fait jamais
Envoyer, publier, se connecter à LinkedIn, appeler son API, scraper ; dépasser les plafonds ; relancer deux fois ; contacter une entreprise déjà contactée. Les noms de prospects vivent dans `B2B\linkedin\equipe.json` et `dashboard\data\`, hors git.

## Vérifier
`python tests\agents\test_linkedin_equipe.py` (silencieux, aucun réseau), puis `tests\b2b-rapide.ps1`. « Il a tourné » = une trace du jour dans `B2B\logs\agents\linkedin-equipe`.
