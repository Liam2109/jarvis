---
name: agent-nettoyage-fichiers
description: Fiche de rôle de l'agent Nettoyage fichiers (rattaché à Jarvis CEO) — chaque jour à 03:00 sur le serveur, supprime sans token les traces B2B\logs\agents et les entrées de JOURNAL-B2B.md de plus de 30 jours, les dossiers de test de %TEMP% de plus de 2 jours, les sauvegardes de plus de 30 jours et les __pycache__ ; liste le reste de vieux dans B2B\a-valider sans rien supprimer. À utiliser pour vérifier ou corriger nettoyage-fichiers.py (nettoyer, etat).
---

# Agent Nettoyage fichiers — fichiers de suivi courts (règle 18)

**Responsable :** Jarvis (CEO). **Script :** `B2B/agents/nettoyage-fichiers.py`. **Contrat :** `B2B/harness/contrats/nettoyage-fichiers.json`.
**Tâche serveur :** `nettoyer` chaque jour à 03:00 (`serveur-taches.json`).

## Mission
Garder le dossier Jarvis propre, sans token ni réseau : supprimer seul ce qui est sans valeur (traces et journal B2B de plus de 30 jours, dossiers de test de %TEMP%, vieilles sauvegardes, `__pycache__`) ; pour tout le reste, seulement un rapport, Liam décide. L'historique reste dans git.

## Ordres pas à pas (lus dans le script)
1. `M.exiger("nettoyage-fichiers", ...)` : machine active obligatoire (sauf `--a-blanc`) ; `B2B\STOP` présent = rien supprimé.
2. Limite = aujourd'hui moins 30 jours (`--jours`, borné 1-3650) ; une date égale à la limite est gardée.
3. Traces : dans `B2B/logs/agents/<agent>/`, supprime les fichiers `AAAA-MM-JJ.jsonl` (ou `.json`, compteurs de la garde) datés avant la limite.
4. Journal : dans `B2B/docs/JOURNAL-B2B.md`, retire les lignes `- AAAA-MM-JJ …` datées avant la limite ; en-tête, lignes non datées, BOM et fins de ligne conservés ; écriture atomique.
5. %TEMP% : supprime les dossiers aux préfixes des tests (`*-test-*`, `jarvis-test-*`, `jarvis-config-test-*`, `reponses-rebonds-*`…) modifiés il y a plus de 2 jours ; rien d'autre dans %TEMP%.
6. `B2B/donnees/sauvegardes/` : supprime les fichiers datés (nom `AAAA-MM-JJ`, sinon date de modification) avant la limite de 30 jours.
7. `__pycache__` : supprime tous ceux du dossier Jarvis (hors `.git`, `node_modules`, venv, `memoire`).
8. Rapport : les autres fichiers de plus de 60 jours sans lien dans `INDEX.md` (chemin ou nom), hors code, skills, docs, médias, `.canvas` et fichiers protégés, sont listés dans `B2B/a-valider/nettoyage-AAAA-MM-JJ.md` ; rien n'est supprimé, et pas de fichier s'il n'y a rien.
9. Garde avant chaque suppression : seulement ces cibles, jamais un lien ni un fichier protégé ; un fichier verrouillé est passé sans bloquer le reste.
10. Une ligne de trace du harness et une ligne dans `nettoyage-fichiers-journal.log` par passage (nombres supprimés, refus de la garde).

## Ce qu'il ne fait jamais
- Toucher au code, aux skills, aux docs, aux médias (`instagram/`) ou aux `.canvas`.
- Toucher à `B2B/donnees/registre-entreprises.json`, `memoire/`, `.env`, `config.json` ou un `*.local.json`.
- Supprimer quoi que ce soit hors des cibles ci-dessus, en dessous de leur âge, ou un fichier listé dans le rapport.
- Envoyer un message, au client ou sur Discord.

## Vérifier qu'il a bien tourné
- `python B2B\agents\nettoyage-fichiers.py etat` : dernier passage.
- `python B2B\agents\nettoyage-fichiers.py nettoyer --a-blanc` : ce qui serait supprimé, sans rien supprimer.
- Test : `python tests\agents\test_nettoyage_fichiers.py` (arborescence fictive). Pas de preuve = pas de « fait ».

## Quand il alerte Liam
- Jamais directement : panne-alerte prévient si la tâche de 03:00 n'a pas tourné ; le surveillant signale une trace en erreur.
