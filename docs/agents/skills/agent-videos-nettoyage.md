---
name: agent-videos-nettoyage
description: Fiche de rôle de l'agent Nettoyage vidéos (équipe Vidéos TikTok, rattachée à Jarvis CEO) — chaque jour à 03:30 sur le serveur, script PowerShell sans token qui supprime les vidéos (.mp4) et fichiers intermédiaires de Videos\ plus vieux que nettoyage_jours (14 par défaut, réglable dans la config), après une ligne dans journal-videos.csv. À utiliser pour vérifier ou corriger Videos\agents\nettoyage.ps1 (-Simulation).
---

# Agent Nettoyage vidéos — la place sur le disque, sans rien perdre d'utile

**Responsable :** Jarvis (CEO). **Script :** `Videos/agents/nettoyage.ps1`. **Contrat :** `B2B/harness/contrats/videos-nettoyage.json`.
**Tâche serveur :** chaque jour à 03:30 (`serveur-taches.json`, à partir du 17/11/2026, si `videos-nettoyage` est dans `agents_actifs` ; le lanceur `serveur-b2b.ps1` lance les `.ps1` avec PowerShell).

## Ordres pas à pas (lus dans le script)
1. Refuse (code 3) si cette machine n'est pas la machine active (`B2B\agents\b2b.local.json`).
2. Lit `nettoyage_jours`, `nettoyage_extensions` et `videos_protegees` dans la config vidéo (jamais dans le code) ; un document, un script ou un réglage (.md, .py, .ps1, .json, .txt, .csv) n'est jamais une extension à supprimer.
3. Cherche les fichiers plus vieux que la limite dans `a-valider`, `publiees`, `travail` et `outils\stickfigure-pipeline-v2\output` seulement (jamais `node_modules`).
4. Pour chaque vidéo finie : une ligne dans `Videos\journal-videos.csv` (date, nom, statut, hook lu dans son .json), puis suppression de la vidéo, de sa légende et de son .json. Pour les intermédiaires : une ligne par dossier, puis suppression.
5. Retire les dossiers vides de `travail`, écrit un résumé dans `Videos\videos-nettoyage-journal.log`.

## Ce qu'il ne fait jamais
- Écrire ou supprimer hors de `Videos\` ; toucher au skill, à `hooks*.md`, au README, à la config, à `agents\`, `scripts\`, `veille\` ou aux vidéos protégées (la vidéo test `2026-11-16-2200`).
- Utiliser un token, le réseau ou un service payant.

## Vérifier
- `powershell -File Videos\agents\nettoyage.ps1 -Simulation` (dit ce qui serait supprimé, ne supprime rien).
- Test : `python tests\agents\test_videos.py` (classe Nettoyage, dossier temporaire) et `B2B\agents\test_machine.py` (refus hors machine active). Pas de preuve = pas de « fait ».

## Quand il alerte Liam
- Jamais directement : le surveillant signale l'absence de trace après 04:15 ou une trace en erreur.
