---
agent: page-exemple
aliases: [🌐 Page exemple]
name: page-exemple
role: Sur « métier, ville, nom » envoyé dans Discord, générer une page exemple déployée en aperçu (noindex) et renvoyer seulement le lien
machine: gros PC (lancé par Jarvis, lib/page-exemple.ps1) ; pas de tâche serveur
planification: non planifié sur le serveur (absent de serveur-taches.json)
depend_de: B2B/sites/moteur, règles de style des sites
sorties: page sur b2b-demos (aperçu), page-exemple-etat.json
responsable: Production
statut: arrêté
horaire: "à la demande (aucune tâche serveur), plage tous les jours 08:00-22:00"
tags: [agent-b2b]
---
<!-- GENERE:DEBUT (régénéré par python B2B\harness\generer-fiches.py : ne pas modifier) -->
# 🌐 Page exemple

**Agent :** `page-exemple` · **Statut :** arrêté · **Responsable :** Production (pôle) · **Machine :** gros PC
**Horaire :** à la demande (aucune tâche serveur), plage tous les jours 08:00-22:00
**Script :** `B2B/agents/page-exemple.py` · **Contrat :** `B2B/harness/contrats/page-exemple.json`

## Rôle et limites
### Mission
Générer et déployer une page exemple personnalisée à la demande de Liam sur Discord, depuis un modèle validé.

### Ce qu'il fait étape par étape
1. Déclencheur : `generer "plombier, Yvetot, Dupont Plomberie"` ou un message de Liam (seul `DISCORD_USER_ID`) dans le salon dédié ; curseur posé au premier passage, avancé avant le traitement.
2. Analyse « métier, ville, nom » ; métier non reconnu : rien n'est créé, l'agent le dit.
3. Ville ou nom absent : hypothèse par défaut, dite dans la réponse (aucune question à Liam).
4. Choisit le modèle validé du métier (plombier, électricien, coiffeur, fleuriste, boulangerie, garage, restaurant), crée `sites/deploiement/<slug>`.
5. Délègue l'écriture et le déploiement à un sous-agent `claude -p` (outils limités ; jamais git push, git config ni git add -A).
6. Exige une ligne LIEN ; vérifie lui-même que le lien est sur `b2b-demos.vercel.app`, contient le slug et répond 200 avec `noindex`.
7. Ajoute une ligne à `pages-exemple\suivi.csv`, répond sur Discord **seulement avec le lien**.

### Ce qu'il n'a pas le droit de faire
- envoyer au client sans accord de Liam
- encaisser ou rembourser
- publier
- signer ou promettre un résultat
- afficher un secret (jeton, clé, adresse iCal)
- déployer sans accord
- Engager Liam (envoyer au client, encaisser, publier, signer) : `peut_engager: false`, tout passe par `B2B/a-valider/`.

## Entrées et sorties
**Lit :**
- Discord (demandes de Liam)
- modèles de pages

**Écrit :**
- pages exemples
- B2B/agents/page-exemple-etat.json

**Discord :** pages · **Plafond :** 20 messages par jour · **Envoi au client :** non

## Horaire et état
- **Horaire :** à la demande (aucune tâche serveur), plage tous les jours 08:00-22:00
- **Tâche serveur :** aucune dans serveur-taches.json
- **Contrat :** valide (`python B2B\harness\valider.py`)
- **Garde branchée :** partielle : alertes Discord gardées, déploiement de page non gardé (Vercel, accord de Liam)
- Bloque : kill-switch `B2B\STOP`, lien Stripe non autorisé, phrase interdite (OFFRE-REFERENCE.json), secret dans le texte.
- Avertit : machine non active, envoi_automatique = false (simulation), hors horaires du contrat (08:00-22:00), plafond de 20 messages par jour.
- **Tests :** aucun : à compléter par Liam
- **Alerte si silence :** aucune

<!-- DYNAMIQUE:DEBUT -->
**Derniers résultats de test (cette machine) :**
- aucun test

**Dernière trace :** aucune · **Dernière erreur :** aucune · **Dans agents_actifs (cette machine) :** non (Liam l'ajoute s'il veut le planifier)

### Historique (5 dernières traces, sans données client)
- aucune trace sur cette machine
<!-- DYNAMIQUE:FIN -->

## Skill et règles
- `.claude/skills/agent-page-exemple/SKILL.md` (copie : `docs/agents/skills/agent-page-exemple.md`)
- Pas de preuve = pas de fait : « il a tourné » = une trace du jour `ok: true` ci-dessus ; « c'est corrigé » = ses tests puis `tests\b2b-rapide.ps1` en vert.
<!-- GENERE:FIN -->

## Liens et décisions

_Zone conservée à chaque régénération : liens vers docs\decisions et docs clés seulement._

Toute page suit les règles de style et porte « exemple, pas votre site ».
Code : `B2B/agents/page-exemple.py` (pas encore de doc .md dédiée)
Liens : [[TODO-B2B]]

## Notes de Liam

_Zone libre, conservée telle quelle à chaque régénération._
