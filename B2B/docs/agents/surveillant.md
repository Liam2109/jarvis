---
agent: surveillant
statut: actif
mode: simulation
responsable: Jarvis (CEO)
horaire: "chaque jour à 19:45 + lundi 07:50, plage tous les jours 07:00-20:30"
machine: serveur
tags: [agent-b2b]
---
<!-- GENERE:DEBUT (régénéré par python B2B\harness\generer-fiches.py : ne pas modifier) -->
# surveillant

**Statut :** actif (simulation : envoi_automatique = false) · **Responsable :** [[jarvis-ceo|Jarvis (CEO)]] · **Machine :** serveur
**Horaire :** chaque jour à 19:45 + lundi 07:50, plage tous les jours 07:00-20:30
**Script :** `B2B/harness/surveillant.py` · **Contrat :** `B2B/harness/contrats/surveillant.json`

## Mission
Lire contrats et traces et signaler sur Discord chaque agent en défaut ; une ligne « harness OK » le lundi.

## Ce qu'il fait étape par étape
1. Hors `--simulation` : machine active obligatoire (`M.exiger`).
2. Lit tous les contrats `B2B/harness/contrats/*.json` ; agents d'une tâche serveur : seulement ceux de `agents_actifs` (b2b.local.json).
3. Ne surveille que les statuts `actif` et `simulation` (pas lui-même).
4. Pour chacun, lit les traces du jour `B2B/logs/agents/<agent>/AAAA-MM-JJ.jsonl` (les lignes « garde … » ne comptent pas comme exécution).
5. Défaut = une trace `ok:false` (« erreur ») ou, un jour prévu du contrat, aucune exécution passé `alerte_si_silence` (« n'a pas tourné »).
6. Message : une ligne par agent en défaut ; rien si tout va bien, sauf le lundi avant midi « harness OK, N agents ».
7. Poste avec la fonction Discord existante si `envoi_automatique` (surveillant-config.json, false par défaut), sinon affiche ; écrit sa propre trace.

## Entrées et sorties
**Lit :**
- B2B/harness/contrats
- B2B/logs/agents

**Écrit :**
- B2B/logs/agents/surveillant

**Discord :** alertes · **Plafond :** 20 messages par jour · **Envoi au client :** non

## Ce qu'il n'a pas le droit de faire
- envoyer au client sans accord de Liam
- encaisser ou rembourser
- publier
- signer ou promettre un résultat
- afficher un secret (jeton, clé, adresse iCal)
- Engager Liam (envoyer au client, encaisser, publier, signer) : `peut_engager: false`, tout passe par `B2B/a-valider/`.

## Harness
- **Contrat :** valide (`python B2B\harness\valider.py`)
- **Garde branchée :** oui
- Bloque : kill-switch `B2B\STOP`, lien Stripe non autorisé, phrase interdite (OFFRE-REFERENCE.json), secret dans le texte.
- Avertit : machine non active, envoi_automatique = false (simulation), hors horaires du contrat (07:00-20:30), plafond de 20 messages par jour.
- **Tests :** `tests/agents/test_panne_alerte.py`
- **Alerte si silence :** aucune

<!-- DYNAMIQUE:DEBUT -->
**Derniers résultats de test (cette machine) :**
- `tests/agents/test_panne_alerte.py` : réussi le 2026-11-15 19:35

**Dernière trace :** aucune

### Historique (5 dernières traces, sans données client)
- aucune trace sur cette machine
<!-- DYNAMIQUE:FIN -->

## Skill
- [[skills/agent-surveillant|agent-surveillant]]

## Liens
- Responsable : [[jarvis-ceo|Jarvis (CEO)]]
- Direction : [[jarvis-ceo|Jarvis (CEO)]] · [[00-ORGANIGRAMME|Organigramme]]
<!-- GENERE:FIN -->

## Notes de Liam

_Zone libre, conservée telle quelle à chaque régénération._
