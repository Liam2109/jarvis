---
agent: jarvis-vue
aliases: [🪟 Vue Jarvis]
name: jarvis-vue
role: "Toutes les 30 min : remet l'etat des quatre superviseurs (ok, corrige, bloque) dans un fichier court et un seul message Discord groupe par jour. Ne corrige rien, ne relance rien."
machine: "serveur"
planification: "toutes les 30 min, plage tous les jours 07:00-23:00"
sorties: "B2B/logs/superviseurs/ETAT-SUPERVISEURS.md (hors git, reecrit a chaque passage), B2B/agents/jarvis-vue-etat.json, B2B/agents/jarvis-vue-journal.log"
responsable: Jarvis (CEO)
statut: arrêté
horaire: "toutes les 30 min, plage tous les jours 07:00-23:00"
tags: [agent-b2b]
---
<!-- GENERE:DEBUT (régénéré par python B2B\harness\generer-fiches.py : ne pas modifier) -->
# 🪟 Vue Jarvis

**Agent :** `jarvis-vue` · **Statut :** arrêté · **Responsable :** Jarvis (CEO) · **Machine :** serveur
**Horaire :** toutes les 30 min, plage tous les jours 07:00-23:00
**Script :** `B2B/agents/jarvis-vue.py` · **Contrat :** `B2B/harness/contrats/jarvis-vue.json`

## Rôle et limites
### Mission
Toutes les 30 min : remet l'etat des quatre superviseurs (ok, corrige, bloque) dans un fichier court et un seul message Discord groupe par jour. Ne corrige rien, ne relance rien.

### Ce qu'il fait étape par étape
1. `M.exiger("jarvis-vue", ...)` : refuse hors de la machine active (sauf `--essai`).
2. Pour chacun des quatre domaines, elle lit **ce que le superviseur a déjà écrit** (son état et son journal) : aucun contrôle n'est refait, aucun chiffre n'est recalculé.
   Un domaine est : « ok » (rien à signaler), « corrigé » (le superviseur a réparé tout seul aujourd'hui), « bloqué » (il attend un « go » de Liam),
   « jamais passé » (le superviseur n'a pas encore tourné) ou « inconnu » (son état est illisible).
3. Elle réécrit à chaque passage un **fichier court** : un tableau d'une ligne par domaine (état, dernier passage, corrections du jour, nombre d'items en attente),
   puis la liste de ce qui attend un « go » et la liste de ce qui a été corrigé seul aujourd'hui. Pas d'historique : il est dans git et dans les journaux des superviseurs (décision du 15/11/2026).
4. Discord : **un seul message groupé par jour**, à partir de `heure_resume` (19:40 par défaut) : une ligne avec l'état des quatre domaines, puis ce qui attend un « go ».
   Rien avant cette heure, rien deux fois, rien si le verrou est fermé.
5. Elle **ne corrige rien, ne relance rien, ne supprime rien** : si deux domaines se contredisent, c'est leur superviseur qui le dit, pas elle.

### Ce qu'il n'a pas le droit de faire
- corriger, reparer ou relancer quoi que ce soit (elle ne fait que lire)
- recalculer un chiffre remonte par un superviseur
- supprimer une donnee, une ligne, une fiche ou un fichier
- ecraser une valeur deja ecrite par un agent ou par Liam
- toucher a un montant, un paiement, un prix ou un devis
- toucher au code, aux skills, aux docs ou a un fichier suivi par git
- ecrire dans les donnees d'un autre domaine que le sien
- corriger quoi que ce soit avant le « go superviseurs » de Liam
- relancer plus d'une fois par jour le meme agent
- contacter un prospect, un client, Sid ou qui que ce soit d'autre que Liam
- utiliser une IA ou un service payant
- afficher un secret (jeton, cle, adresse iCal)
- envoyer au client, encaisser, publier ou signer
- Engager Liam (envoyer au client, encaisser, publier, signer) : `peut_engager: false`, tout passe par `B2B/a-valider/`.

## Entrées et sorties
**Lit :**
- B2B/agents/superviseur-*-etat.json et leurs journaux
- B2B/agents/superviseur-*-config.json (verrou)

**Écrit :**
- B2B/logs/superviseurs/ETAT-SUPERVISEURS.md (hors git, reecrit a chaque passage)
- B2B/agents/jarvis-vue-etat.json
- B2B/agents/jarvis-vue-journal.log

**Discord :** alertes · **Plafond :** 6 messages par jour · **Envoi au client :** non

## Horaire et état
- **Horaire :** toutes les 30 min, plage tous les jours 07:00-23:00
- **Tâche serveur :** entrée dans `B2B/agents/serveur-taches.json`, active à partir du 2026-11-21 ; tourne seulement si l'agent est dans `agents_actifs` (choix de Liam)
- **Contrat :** valide (`python B2B\harness\valider.py`)
- **Garde branchée :** oui
- Bloque : kill-switch `B2B\STOP`, lien Stripe non autorisé, phrase interdite (OFFRE-REFERENCE.json), secret dans le texte.
- Avertit : machine non active, envoi_automatique = false (simulation), hors horaires du contrat (07:00-23:00), plafond de 6 messages par jour.
- **Tests :** `tests/agents/test_superviseurs.py`
- **Alerte si silence :** aucune

<!-- DYNAMIQUE:DEBUT -->
**Derniers résultats de test (cette machine) :**
- `tests/agents/test_superviseurs.py` : pas encore lancé par `generer-fiches.py --tests`

**Dernière trace :** aucune · **Dernière erreur :** aucune · **Dans agents_actifs (cette machine) :** non (Liam l'ajoute s'il veut le planifier)

### Historique (5 dernières traces, sans données client)
- aucune trace sur cette machine
<!-- DYNAMIQUE:FIN -->

## Skill et règles
- `.claude/skills/agent-jarvis-vue/SKILL.md` (copie : `docs/agents/skills/agent-jarvis-vue.md`)
- Pas de preuve = pas de fait : « il a tourné » = une trace du jour `ok: true` ci-dessus ; « c'est corrigé » = ses tests puis `tests\b2b-rapide.ps1` en vert.
<!-- GENERE:FIN -->

## Liens et décisions

_Zone conservée à chaque régénération : liens vers docs\decisions et docs clés seulement._

Liens : aucun pour l'instant.

## Notes de Liam

_Zone libre, conservée telle quelle à chaque régénération._
