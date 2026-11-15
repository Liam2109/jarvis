---
agent: page-exemple
statut: arrêté
responsable: Production
horaire: "à la demande (aucune tâche serveur), plage tous les jours 08:00-22:00"
machine: gros PC
tags: [agent-b2b]
---
<!-- GENERE:DEBUT (régénéré par python B2B\harness\generer-fiches.py : ne pas modifier) -->
# page-exemple

**Statut :** arrêté · **Responsable :** [[responsable-production|Responsable Production]] · **Machine :** gros PC
**Horaire :** à la demande (aucune tâche serveur), plage tous les jours 08:00-22:00
**Script :** `B2B/agents/page-exemple.py` · **Contrat :** `B2B/harness/contrats/page-exemple.json`

## Mission
Générer et déployer une page exemple personnalisée à la demande de Liam sur Discord, depuis un modèle validé.

## Ce qu'il fait étape par étape
1. Déclencheur : `generer "plombier, Yvetot, Dupont Plomberie"` ou un message de Liam (seul `DISCORD_USER_ID`) dans le salon dédié ; curseur posé au premier passage, avancé avant le traitement.
2. Analyse « métier, ville, nom » ; métier non reconnu : rien n'est créé, l'agent le dit.
3. Ville ou nom absent : hypothèse par défaut, dite dans la réponse (aucune question à Liam).
4. Choisit le modèle validé du métier (plombier, électricien, coiffeur, fleuriste, boulangerie, garage, restaurant), crée `sites/deploiement/<slug>`.
5. Délègue l'écriture et le déploiement à un sous-agent `claude -p` (outils limités ; jamais git push, git config ni git add -A).
6. Exige une ligne LIEN ; vérifie lui-même que le lien est sur `b2b-demos.vercel.app`, contient le slug et répond 200 avec `noindex`.
7. Ajoute une ligne à `pages-exemple\suivi.csv`, répond sur Discord **seulement avec le lien**.

## Entrées et sorties
**Lit :**
- Discord (demandes de Liam)
- modèles de pages

**Écrit :**
- pages exemples
- B2B/agents/page-exemple-etat.json

**Discord :** pages · **Plafond :** 20 messages par jour · **Envoi au client :** non

## Ce qu'il n'a pas le droit de faire
- envoyer au client sans accord de Liam
- encaisser ou rembourser
- publier
- signer ou promettre un résultat
- afficher un secret (jeton, clé, adresse iCal)
- déployer sans accord
- Engager Liam (envoyer au client, encaisser, publier, signer) : `peut_engager: false`, tout passe par `B2B/a-valider/`.

## Harness
- **Contrat :** valide (`python B2B\harness\valider.py`)
- **Garde branchée :** partielle : alertes Discord gardées, déploiement de page non gardé (Vercel, accord de Liam)
- Bloque : kill-switch `B2B\STOP`, lien Stripe non autorisé, phrase interdite (OFFRE-REFERENCE.json), secret dans le texte.
- Avertit : machine non active, envoi_automatique = false (simulation), hors horaires du contrat (08:00-22:00), plafond de 20 messages par jour.
- **Tests :** aucun : à compléter par Liam
- **Alerte si silence :** aucune

<!-- DYNAMIQUE:DEBUT -->
**Derniers résultats de test (cette machine) :**
- aucun test

**Dernière trace :** aucune

### Historique (5 dernières traces, sans données client)
- aucune trace sur cette machine
<!-- DYNAMIQUE:FIN -->

## Skill
- [[skills/agent-page-exemple|agent-page-exemple]]

## Liens
- Responsable : [[responsable-production|Responsable Production]]
- Direction : [[jarvis-ceo|Jarvis (CEO)]] · [[00-ORGANIGRAMME|Organigramme]]
<!-- GENERE:FIN -->

## Notes de Liam

_Zone libre, conservée telle quelle à chaque régénération._
