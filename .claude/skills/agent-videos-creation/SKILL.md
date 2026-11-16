---
name: agent-videos-creation
description: Fiche de rôle de l'agent Création vidéos (équipe Vidéos TikTok, rattachée à Jarvis CEO) — à 06:00, 14:00 et 22:00 sur le serveur, fabrique la vidéo du passage avec stick-stage en style toon (couleurs, décor de jour, Gérard articulé, plans et transitions ; gratuit, voix edge-tts, bascule automatique sur Kokoro local s'il échoue, moteur noté dans journal-videos.csv colonne tts), 9:16, 20-35 s, sous-titres mot à mot (2 à 4 mots, mot clé en jaune, zone sûre TikTok), accroche, mention « Contenu généré par IA », et la range dans Videos\a-valider ; ne publie rien. À utiliser pour vérifier ou corriger Videos\agents\creation.py (passage, etat).
---

# Agent Création vidéos — une vidéo prête à valider par passage

**Responsable :** Jarvis (CEO). **Script :** `Videos/agents/creation.py`. **Contrat :** `B2B/harness/contrats/videos-creation.json`.
**Tâche serveur :** `passage` à 06:00, 14:00 et 22:00 (`serveur-taches.json`, `heures_en_plus`, à partir du 17/11/2026, si `videos-creation` est dans `agents_actifs`).
**Outil :** `Videos/outils/stickfigure-pipeline-v2` (cloné, hors git). stick-stage a été écarté le 16/11/2026 : il plante sous Windows (`node_modules\.bin\remotion` lancé sans `.cmd`).

## Ordres pas à pas (lus dans le script)
1. `C.exiger("videos-creation", ...)` ; passage = l'heure prévue la plus proche (ou `--heure`) ; rien si la vidéo existe déjà ; code 2 si le script du passage manque.
2. Verrou `Videos/creation.verrou` : un seul rendu à la fois.
3. Voix d'abord (`Videos/agents/voix.py`) : voix fixe de la ligne (`lignes.<X>.voix` : `edge`, `kokoro`, `kokoro_vitesse`) ; edge-tts en principal, Kokoro local (`Videos/outils/kokoro`, hors git) si edge-tts échoue (erreur, pas d'internet, plus de 30 s pour toute la narration) ; jamais deux moteurs dans une vidéo. Entrée de l'outil : narration seule, portrait 1080×1920, fond sombre, `reuse_audio_from` = nos fichiers de voix (edge-tts retiré du PATH de l'outil pour qu'il ne refasse pas la voix) ; l'outil fait les dessins et le corps de la vidéo (priorité sous la normale, 25 min au plus, seul son propre arbre de processus est arrêté).
4. ffmpeg ajoute : gros sous-titres (le fichier de sous-titres de l'outil), accroche à l'écran pendant les 2,5 premières secondes (une ou deux lignes, taille ajustée pour tenir entre x = 120 et x = 900), « Contenu généré par IA » pendant toute la vidéo, carte de fin française de 3 s (A : 15 minutes avec Liam ; B : candidature).
5. Range `Videos/a-valider/AAAA-MM-JJ-HHMM.mp4` + `.txt` (légende avec la mention IA) + `.json` (durée, `contenu_ia`, `etiquette_ia_tiktok`), une ligne de journal ; une ligne dans `Videos/journal-videos.csv` (colonne `tts` = moteur réellement utilisé) ; la durée hors 20-35 s est signalée. Sous-titres : temps des mots par edge-tts, recalés sur la durée réelle de chaque phrase (`scene_timings.json`), sinon répartis selon la longueur des mots.

## Ce qu'il ne fait jamais
- Publier, rendre deux vidéos en même temps, arrêter un processus qu'il n'a pas lancé, produire une vidéo sans la mention IA.

## Vérifier qu'il a bien tourné
- `python Videos\agents\creation.py etat` ; `python Videos\agents\creation.py passage --heure 06:00 --a-blanc`.
- Test : `python tests\agents\test_videos.py` (aucun rendu). Pas de preuve = pas de « fait ».

## Quand il alerte Liam
- Jamais directement : le surveillant signale l'absence de trace après 06:45 ou une trace en erreur.
