---
name: agent-nettoyage-fichiers
description: Fiche de rôle de l'agent Nettoyage fichiers (rattaché à Jarvis CEO) — chaque jour à 03:00 sur le serveur, supprime sans token les traces B2B\logs\agents et les entrées de JOURNAL-B2B.md de plus de 30 jours. À utiliser pour vérifier ou corriger nettoyage-fichiers.py (nettoyer, etat).
---

# Agent Nettoyage fichiers — fichiers de suivi courts (règle 18)

**Responsable :** Jarvis (CEO). **Script :** `B2B/agents/nettoyage-fichiers.py`. **Contrat :** `B2B/harness/contrats/nettoyage-fichiers.json`.
**Tâche serveur :** `nettoyer` chaque jour à 03:00 (`serveur-taches.json`).

## Mission
Supprimer les traces du harness et les entrées du journal B2B de plus de 30 jours, sans token ni réseau ; l'historique reste dans git.

## Ordres pas à pas (lus dans le script)
1. `M.exiger("nettoyage-fichiers", ...)` : machine active obligatoire (sauf `--a-blanc`) ; `B2B\STOP` présent = rien supprimé.
2. Limite = aujourd'hui moins 30 jours (`--jours`, borné 1-3650) ; une date égale à la limite est gardée.
3. Traces : dans `B2B/logs/agents/<agent>/`, supprime les fichiers `AAAA-MM-JJ.jsonl` (ou `.json`, compteurs de la garde) datés avant la limite.
4. Journal : dans `B2B/docs/JOURNAL-B2B.md`, retire les lignes `- AAAA-MM-JJ …` datées avant la limite ; en-tête, lignes non datées, BOM et fins de ligne conservés ; écriture atomique.
5. Garde avant chaque suppression : seulement ces deux cibles, jamais un lien ni un fichier protégé.
6. Une ligne de trace du harness et une ligne dans `nettoyage-fichiers-journal.log` par passage (nombres supprimés, refus de la garde).

## Ce qu'il ne fait jamais
- Toucher à `B2B/donnees/registre-entreprises.json`, `memoire/`, `.env`, `config.json` ou un `*.local.json`.
- Supprimer quoi que ce soit hors de `B2B/logs/agents` et de `JOURNAL-B2B.md`, ou de 30 jours et moins.
- Envoyer un message, au client ou sur Discord.

## Vérifier qu'il a bien tourné
- `python B2B\agents\nettoyage-fichiers.py etat` : dernier passage.
- `python B2B\agents\nettoyage-fichiers.py nettoyer --a-blanc` : ce qui serait supprimé, sans rien supprimer.
- Test : `python tests\agents\test_nettoyage_fichiers.py` (arborescence fictive). Pas de preuve = pas de « fait ».

## Quand il alerte Liam
- Jamais directement : panne-alerte prévient si la tâche de 03:00 n'a pas tourné ; le surveillant signale une trace en erreur.
