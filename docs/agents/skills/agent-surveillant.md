---
name: agent-surveillant
description: Fiche de rôle du Surveillant du harness (rattaché à Jarvis CEO) — lit contrats et traces et signale sur Discord chaque agent en défaut (silence ou erreur) ; « harness OK » le lundi matin. À utiliser pour vérifier ou corriger B2B/harness/surveillant.py (verifier).
---

# Surveillant du harness — qui n'a pas tourné, qui a échoué

**Responsable :** Jarvis (CEO). **Script :** `B2B/harness/surveillant.py` (tâche serveur via `B2B/agents/surveillant.py`). **Contrat :** `B2B/harness/contrats/surveillant.json`.
**Tâche serveur :** `verifier` à 19:45 chaque jour et 07:50 le lundi.

## Mission
Lire contrats et traces et signaler sur Discord chaque agent en défaut ; une ligne « harness OK » le lundi.

## Ordres pas à pas (lus dans le script)
1. Hors `--simulation` : machine active obligatoire (`M.exiger`).
2. Lit tous les contrats `B2B/harness/contrats/*.json` ; agents d'une tâche serveur : seulement ceux de `agents_actifs` (b2b.local.json).
3. Ne surveille que les statuts `actif` et `simulation` (pas lui-même).
4. Pour chacun, lit les traces du jour `B2B/logs/agents/<agent>/AAAA-MM-JJ.jsonl` (les lignes « garde … » ne comptent pas comme exécution).
5. Défaut = une trace `ok:false` (« erreur ») ou, un jour prévu du contrat, aucune exécution passé `alerte_si_silence` (« n'a pas tourné »).
6. Message : une ligne par agent en défaut ; rien si tout va bien, sauf le lundi avant midi « harness OK, N agents ».
7. Poste avec la fonction Discord existante si `envoi_automatique` (surveillant-config.json, false par défaut), sinon affiche ; écrit sa propre trace.

## Entrées et sorties
- Entrées : contrats, traces, `serveur-taches.json`, `b2b.local.json` (agents actifs).
- Sorties : message Discord (via `prospection.discord`), trace `B2B/logs/agents/surveillant/`.

## Cas limites gérés par le code
- `machine` illisible : surveille tous les contrats.
- Discord injoignable : « Discord : non envoyé » dans la trace.
- `--maintenant AAAA-MM-JJTHH:MM` pour rejouer une heure donnée.

## Ce qu'il ne fait jamais
- Relancer un agent ou corriger une trace.
- Écrire ailleurs que dans sa trace.

## Vérifier qu'il a bien tourné
- `python B2B\harness\surveillant.py verifier --simulation` : le message, sans rien envoyer.
- `python B2B\harness\rapport.py` : tableau agent / contrat / garde / test / dernière trace.
- Test (contrat) : `python tests\agents\test_panne_alerte.py` ; série `tests\harness.ps1`.

## Quand il alerte Liam
- Chaque agent en défaut (19:45), et la ligne « harness OK » du lundi matin.
