---
agent: jarvis-ceo
statut: actif
mode: simulation
responsable: Liam
horaire: "à la demande (aucune tâche serveur), plage tous les jours 07:30-21:00"
machine: gros PC
tags: [agent-b2b]
---
<!-- GENERE:DEBUT (régénéré par python B2B\harness\generer-fiches.py : ne pas modifier) -->
# jarvis-ceo

**Statut :** actif (simulation : envoi_automatique = false) · **Responsable :** Liam · **Machine :** gros PC
**Horaire :** à la demande (aucune tâche serveur), plage tous les jours 07:30-21:00
**Script :** `.claude/skills/jarvis-ceo/SKILL.md` · **Contrat :** `B2B/harness/contrats/jarvis-ceo.json`

## Mission
Lire l'état des responsables, décider, déléguer et prévenir Liam ; ne produit que des décisions structurées (jarvis-sortie.schema.json).

## Ce qu'il fait étape par étape
- **07 h 45 : brief du matin.** Liste d'appels prête ou non, ce qui attend Liam, la seule action prioritaire du jour.
- **Le soir (19 h) : résumé.** Appels passés, rendez-vous, devis, paiements, ce qui a cassé.
- **Immédiatement : alertes.** Une panne, un paiement reçu ou un rendez-vous pris.

## Entrées et sorties
**Lit :**
- états et journaux des agents
- B2B/logs/agents
- B2B/docs/TODO-B2B.md

**Écrit :**
- B2B/a-valider/AAAA-MM-JJ-jarvis-ceo.md

**Discord :** alertes · **Plafond :** 6 messages par jour · **Envoi au client :** non

## Ce qu'il n'a pas le droit de faire
- envoyer au client sans accord de Liam
- encaisser ou rembourser
- publier
- signer ou promettre un résultat
- afficher un secret (jeton, clé, adresse iCal)
- promettre au client
- faire la tâche d'un agent
- Engager Liam (envoyer au client, encaisser, publier, signer) : `peut_engager: false`, tout passe par `B2B/a-valider/`.

## Harness
- **Contrat :** valide (`python B2B\harness\valider.py`)
- **Garde branchée :** sans objet : pas de script (sorties validées par jarvis_sortie.py)
- Bloque : kill-switch `B2B\STOP`, lien Stripe non autorisé, phrase interdite (OFFRE-REFERENCE.json), secret dans le texte.
- Avertit : machine non active, envoi_automatique = false (simulation), hors horaires du contrat (07:30-21:00), plafond de 6 messages par jour.
- **Tests :** `tests/agents/test_jarvis_sortie.py`
- **Alerte si silence :** aucune

<!-- DYNAMIQUE:DEBUT -->
**Derniers résultats de test (cette machine) :**
- `tests/agents/test_jarvis_sortie.py` : réussi le 2026-11-15 19:35

**Dernière trace :** aucune

### Historique (5 dernières traces, sans données client)
- aucune trace sur cette machine
<!-- DYNAMIQUE:FIN -->

## Skill
- [[skills/jarvis-ceo|jarvis-ceo]]

## Liens
- Responsable : Liam
- Direction : [[jarvis-ceo|Jarvis (CEO)]] · [[00-ORGANIGRAMME|Organigramme]]
<!-- GENERE:FIN -->

## Notes de Liam

_Zone libre, conservée telle quelle à chaque régénération._
