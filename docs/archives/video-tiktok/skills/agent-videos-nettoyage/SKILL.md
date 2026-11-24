---
name: agent-videos-nettoyage
description: Fiche de rôle de l'agent Nettoyage vidéos (équipe Vidéos TikTok, rattachée à Jarvis CEO) — chaque jour à 03:30 sur le serveur, script PowerShell sans token qui supprime les vidéos (.mp4) et fichiers intermédiaires de Videos\ plus vieux que nettoyage_jours (14 par défaut, réglable dans la config), après une ligne dans journal-videos.csv. À utiliser pour vérifier ou corriger Videos\agents\nettoyage.ps1 (-Simulation).
---

# Agent Nettoyage vidéos — la place sur le disque, sans rien perdre d'utile

**Responsable :** Jarvis (CEO). **Script :** `Videos/agents/nettoyage.ps1`. **Contrat :** `B2B/harness/contrats/videos-nettoyage.json`.
**Tâche serveur :** chaque jour à 03:30 (`serveur-taches.json`, à partir du 17/11/2026, si `videos-nettoyage` est dans `agents_actifs` ; le lanceur `serveur-b2b.ps1` lance les `.ps1` avec PowerShell).

## Rôle
Libérer la place sur le disque : supprimer les vidéos et fichiers intermédiaires de `Videos\` plus vieux que `nettoyage_jours`, après une ligne de journal. Limites : n'écrit et ne supprime que dans `Videos\` (dossiers listés), jamais un document, un script, un réglage ni une vidéo protégée.

## Ordres pas à pas (lus dans le script)
1. Refuse (code 3) si cette machine n'est pas la machine active (`B2B\agents\b2b.local.json`).
2. Lit `nettoyage_jours`, `nettoyage_extensions` et `videos_protegees` dans la config vidéo (jamais dans le code) ; un document, un script ou un réglage (.md, .py, .ps1, .json, .txt, .csv) n'est jamais une extension à supprimer.
3. Cherche les fichiers plus vieux que la limite dans `a-valider`, `publiees`, `travail` et `outils\stickfigure-pipeline-v2\output` seulement (jamais `node_modules`).
4. Pour chaque vidéo finie : une ligne dans `Videos\journal-videos.csv` (date, nom, statut, hook lu dans son .json), puis suppression de la vidéo, de sa légende et de son .json. Pour les intermédiaires : une ligne par dossier, puis suppression.
5. Retire les dossiers vides de `travail`, écrit un résumé dans `Videos\videos-nettoyage-journal.log`.

## Entrées et sorties (place dans la chaîne)
- **Reçoit de :** **Publication** (`Videos/publiees`) et **Création** (`Videos/a-valider`, `Videos/travail`, sorties de l'outil).
- **Produit :** fichiers supprimés ; une ligne par vidéo (et par dossier d'intermédiaires) dans `journal-videos.csv` ; résumé dans `Videos/videos-nettoyage-journal.log`.
- **Passe à :** aucun (dernier maillon) ; la place libérée sert aux rendus suivants de **Création**.
- Chaîne vidéo : Veille → Scripts → Marketing → Création (→ Monteur, ligne B) → ton OK de Liam (« go publier », une fois par ligne) → Publication → Nettoyage. Fiche : `docs/agents/⛓️ Chaîne vidéo.md`.

## Ce qu'il ne fait jamais
- Écrire ou supprimer hors de `Videos\` ; toucher au skill, à `hooks*.md`, au README, à la config, à `agents\`, `scripts\`, `veille\` ou aux vidéos protégées (la vidéo test `2026-11-16-2200`).
- Utiliser un token, le réseau ou un service payant.

## Cas d'erreur
- Machine non active : refus code 3, trace `ok: false`.
- Réglages illisibles ou `nettoyage_jours` < 1 : rien supprimé, code 2, trace `ok: false`.
- Erreur inattendue : arrêt, code 1, trace `ok: false` (aucune suppression hors des dossiers listés).
- Toute erreur laisse une trace `ok: false`, lue par le surveillant si l'agent est dans `agents_actifs`.

## Règles qu'il suit
- Il ne lit pas `Videos/SKILL-VIDEOS.md` (script PowerShell) mais en applique la section « Nettoyage ».
- Harness : contrat `B2B/harness/contrats/videos-nettoyage.json` (`peut_engager: false`) ; garde : sans objet (aucun texte produit), garde de chemins codée (seulement les dossiers listés de `Videos\`) ; une trace par exécution réelle (fonction `Fin` de `nettoyage.ps1`, aucune en `-Simulation`) dans `B2B/logs/agents/videos-nettoyage/AAAA-MM-JJ.jsonl`.
- Ce qui engage Liam (publier, envoyer, encaisser, signer) n'est jamais fait sans son accord ; la publication reste verrouillée par ligne jusqu'à son « go publier ».
- Règle d'or : pas de preuve = pas de fait. « Il a tourné » se prouve par la trace du jour (`ok: true`) et le fichier produit ; « c'est corrigé » par `python tests\agents\test_videos.py` puis `tests\b2b-rapide.ps1` en vert, sortie montrée.

## Vérifier
- `powershell -File Videos\agents\nettoyage.ps1 -Simulation` (dit ce qui serait supprimé, ne supprime rien).
- Test : `python tests\agents\test_videos.py` (classe Nettoyage, dossier temporaire) et `B2B\agents\test_machine.py` (refus hors machine active). Pas de preuve = pas de « fait ».

## Quand il alerte Liam
- Jamais directement : le surveillant signale l'absence de trace après 04:15 ou une trace en erreur.
