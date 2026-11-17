---
name: agent-videos-creation
description: Fiche de rôle de l'agent Création vidéos (équipe Vidéos TikTok, rattachée à Jarvis CEO) — à 06:00, 14:00 et 22:00 sur le serveur, fabrique la vidéo du passage avec stick-stage en style toon (couleurs, décor de jour, Gérard articulé, plans et transitions ; gratuit, voix edge-tts, bascule automatique sur Kokoro local s'il échoue, moteur noté dans journal-videos.csv colonne tts), 9:16, 20-35 s, sous-titres mot à mot (2 à 4 mots, mot clé en jaune, zone sûre TikTok), accroche, mention « Contenu généré par IA », et la range dans Videos\a-valider ; ne publie rien. À utiliser pour vérifier ou corriger Videos\agents\creation.py (passage, etat).
---

# Agent Création vidéos — une vidéo prête à valider par passage

**Responsable :** Jarvis (CEO). **Script :** `Videos/agents/creation.py`. **Contrat :** `B2B/harness/contrats/videos-creation.json`.
**Tâche serveur :** `passage` à 06:00, 14:00 et 22:00 (`serveur-taches.json`, `heures_en_plus`, à partir du 17/11/2026, si `videos-creation` est dans `agents_actifs`).
**Outil :** stick-stage (`Videos/outils/stick-stage`, MIT, cloné hors git, corrigé pour Windows par `Videos/correctifs/stick-stage-windows.py` : lanceur Remotion et Rhubarb sans « -q »). Ligne B (sketch à deux, 17/11/2026) : après la voix (une par personnage, `voix.voix_dialogue`), tout le montage est confié à l'agent monteur (`Videos/agents/monteur.py`, skill `agent-videos-monteur`) ; vidéo acceptée -> `a-valider`, refusée 3 fois -> `a-part` (motif en .json), ligne dans `journal-videos.csv` dans les deux cas.

## Rôle
Fabriquer la vidéo de chaque passage (stick-stage, voix, sous-titres ; aucun texte IA à l'image depuis le 17/11/2026) et la ranger dans `Videos/a-valider`. Limites : un seul rendu à la fois, ne publie jamais, n'arrête que ses propres processus.

## Ordres pas à pas (lus dans le script)
1. `C.exiger("videos-creation", ...)` ; passage = l'heure prévue la plus proche (ou `--heure`) ; rien si la vidéo existe déjà ; code 2 si le script du passage manque.
2. Verrou `Videos/creation.verrou` : un seul rendu à la fois.
3. Voix d'abord (`Videos/agents/voix.py`) : voix fixe de la ligne (`lignes.<X>.voix` : `edge`, `kokoro`, `kokoro_vitesse`) ; edge-tts en principal, Kokoro local (`Videos/outils/kokoro`, hors git) si edge-tts échoue (erreur, pas d'internet, plus de 30 s pour toute la narration) ; jamais deux moteurs dans une vidéo. Entrée de l'outil : narration seule, portrait 1080×1920, fond sombre, `reuse_audio_from` = nos fichiers de voix (edge-tts retiré du PATH de l'outil pour qu'il ne refasse pas la voix) ; l'outil fait les dessins et le corps de la vidéo (priorité sous la normale, 25 min au plus, seul son propre arbre de processus est arrêté).
4. ffmpeg ajoute : gros sous-titres (le fichier de sous-titres de l'outil), accroche à l'écran pendant les 2,5 premières secondes (une ou deux lignes, taille ajustée pour tenir entre x = 120 et x = 900), carte de fin (plus de texte « Contenu généré par IA » à l'image depuis le 17/11/2026 : l'étiquette TikTok est cochée par videos-publication ; la mention reste dans la légende) française de 3 s (A : 15 minutes avec Liam ; B : candidature).
5. Range `Videos/a-valider/AAAA-MM-JJ-HHMM.mp4` + `.txt` (légende avec la mention IA) + `.json` (durée, `contenu_ia`, `etiquette_ia_tiktok`), une ligne de journal ; une ligne dans `Videos/journal-videos.csv` (colonne `tts` = moteur réellement utilisé) ; la durée hors 20-35 s est signalée. Sous-titres : temps des mots par edge-tts, recalés sur la durée réelle de chaque phrase (`scene_timings.json`), sinon répartis selon la longueur des mots.

## Entrées et sorties (place dans la chaîne)
- **Reçoit de :** **Marketing** (ou **Scripts** si Marketing n'a rien gardé) : `Videos/scripts/AAAA-MM-JJ-HHMM.json`.
- **Produit :** `Videos/a-valider/AAAA-MM-JJ-HHMM.mp4` + `.txt` (légende) + `.json` (métadonnées) ; une ligne dans `journal-videos.csv`. Ligne B : le montage est confié au **Monteur**.
- **Passe à :** **Monteur** (ligne B, appelé directement) ; puis le **ton OK de Liam** (« go publier », une fois par ligne) ; puis **Publication**.
- Chaîne vidéo : Veille → Scripts → Marketing → Création (→ Monteur, ligne B) → ton OK de Liam (« go publier », une fois par ligne) → Publication → Nettoyage. Fiche : `docs/agents/⛓️ Chaîne vidéo.md`.

## Ce qu'il ne fait jamais
- Publier, rendre deux vidéos en même temps, arrêter un processus qu'il n'a pas lancé, écrire une légende sans la mention IA, incruster un texte IA à l'image.

## Cas d'erreur
- Script du passage absent : code 2 (Scripts doit passer avant), trace `ok: false`.
- Script bloqué par la garde du harness (secret, phrase interdite) : aucun rendu, code 4, trace `ok: false` « garde contenu ».
- Autre rendu en cours (verrou) : passage abandonné, code 1.
- edge-tts en échec : bascule automatique sur Kokoro local ; les deux en échec : code 1.
- Rendu ou montage ffmpeg en échec : code 1 ; ligne B refusée 3 fois par le Monteur : vidéo dans `Videos/a-part`, code 1.
- Machine non active ou `SKILL-VIDEOS.md` incomplet : refus code 3.
- Toute erreur laisse une trace `ok: false`, lue par le surveillant si l'agent est dans `agents_actifs`.

## Règles qu'il suit
- Il relit `Videos/SKILL-VIDEOS.md` avant chaque exécution (`C.exiger_regles` : absent ou incomplet = refus, code 3), sections « Rythme et format », « Sous-titres », « Deux lignes éditoriales ».
- Harness : contrat `B2B/harness/contrats/videos-creation.json` (`peut_engager: false`) ; garde du contenu `C.garde_harness` avant écriture (secret, phrase interdite d'`OFFRE-REFERENCE.json`, lien Stripe non autorisé ; `B2B\STOP` bloque la publication, pas la fabrication) ; une trace par exécution (`C.lancer` : commande, durée, ok, erreur ; rien pour `etat` ni `--a-blanc`) dans `B2B/logs/agents/videos-creation/AAAA-MM-JJ.jsonl`.
- Ce qui engage Liam (publier, envoyer, encaisser, signer) n'est jamais fait sans son accord ; la publication reste verrouillée par ligne jusqu'à son « go publier ».
- Règle d'or : pas de preuve = pas de fait. « Il a tourné » se prouve par la trace du jour (`ok: true`) et le fichier produit ; « c'est corrigé » par `python tests\agents\test_videos.py` puis `tests\b2b-rapide.ps1` en vert, sortie montrée.

## Vérifier qu'il a bien tourné
- `python Videos\agents\creation.py etat` ; `python Videos\agents\creation.py passage --heure 06:00 --a-blanc`.
- Test : `python tests\agents\test_videos.py` (aucun rendu). Pas de preuve = pas de « fait ».

## Quand il alerte Liam
- Jamais directement : le surveillant signale l'absence de trace après 06:45 ou une trace en erreur.
