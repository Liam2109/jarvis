---
agent: videos-creation
aliases: [🎬 Création vidéos]
name: videos-creation
role: "À 06:00, 14:00 et 22:00, fabrique la vidéo du passage (stickfigure-pipeline-v2, voix edge-tts, 9:16, 20-35 s, sous-titres mot à mot, mention « Contenu généré par IA ») et la range dans Videos/a-valider."
machine: "serveur"
planification: "chaque jour à 06:00, plage tous les jours 06:00-23:00"
sorties: "Videos/a-valider/AAAA-MM-JJ-HHMM.mp4 (+ .txt, .json), Videos/travail (temporaire), Videos/outils/stickfigure-pipeline-v2/output, Videos/videos-creation-journal.log"
responsable: Jarvis (CEO)
statut: actif
mode: réel
horaire: "chaque jour à 06:00, 14:00, 22:00, plage tous les jours 06:00-23:00"
tags: [agent-b2b]
---
<!-- GENERE:DEBUT (régénéré par python B2B\harness\generer-fiches.py : ne pas modifier) -->
# 🎬 Création vidéos

**Agent :** `videos-creation` · **Statut :** actif · **Responsable :** Jarvis (CEO) · **Machine :** serveur
**Horaire :** chaque jour à 06:00, 14:00, 22:00, plage tous les jours 06:00-23:00
**Script :** `Videos/agents/creation.py` · **Contrat :** `B2B/harness/contrats/videos-creation.json`

## Rôle et limites
### Mission
À 06:00, 14:00 et 22:00, fabrique la vidéo du passage (stick-stage toon, voix edge-tts ou Kokoro, 9:16, sous-titres, aucun texte IA à l'image) dans Videos/a-valider ; ligne B : videos-monteur.

### Ce qu'il fait étape par étape
1. `C.exiger("videos-creation", ...)` ; passage = l'heure prévue la plus proche (ou `--heure`) ; rien si la vidéo existe déjà ; code 2 si le script du passage manque.
2. Verrou `Videos/creation.verrou` : un seul rendu à la fois.
3. Voix d'abord (`Videos/agents/voix.py`) : voix fixe de la ligne (`lignes.<X>.voix` : `edge`, `kokoro`, `kokoro_vitesse`) ; edge-tts en principal, Kokoro local (`Videos/outils/kokoro`, hors git) si edge-tts échoue (erreur, pas d'internet, plus de 30 s pour toute la narration) ; jamais deux moteurs dans une vidéo. Entrée de l'outil : narration seule, portrait 1080×1920, fond sombre, `reuse_audio_from` = nos fichiers de voix (edge-tts retiré du PATH de l'outil pour qu'il ne refasse pas la voix) ; l'outil fait les dessins et le corps de la vidéo (priorité sous la normale, 25 min au plus, seul son propre arbre de processus est arrêté).
4. ffmpeg ajoute : gros sous-titres (le fichier de sous-titres de l'outil), accroche à l'écran pendant les 2,5 premières secondes (une ou deux lignes, taille ajustée pour tenir entre x = 120 et x = 900), carte de fin (plus de texte « Contenu généré par IA » à l'image depuis le 17/11/2026 : l'étiquette TikTok est cochée par videos-publication ; la mention reste dans la légende) française de 3 s (A : 15 minutes avec Liam ; B : candidature).
5. Range `Videos/a-valider/AAAA-MM-JJ-HHMM.mp4` + `.txt` (légende avec la mention IA) + `.json` (durée, `contenu_ia`, `etiquette_ia_tiktok`), une ligne de journal ; une ligne dans `Videos/journal-videos.csv` (colonne `tts` = moteur réellement utilisé) ; la durée hors 20-35 s est signalée. Sous-titres : temps des mots par edge-tts, recalés sur la durée réelle de chaque phrase (`scene_timings.json`), sinon répartis selon la longueur des mots.

### Ce qu'il n'a pas le droit de faire
- publier une vidéo
- rendre deux vidéos en même temps
- arrêter un processus qu'il n'a pas lancé
- incruster un texte « contenu généré par IA » à l'image (règle du 17/11/2026 : étiquette TikTok cochée par videos-publication)
- publier, liker, s'abonner, commenter ou envoyer un message sur TikTok
- toucher à memoire/, .env, config.json, .obsidian/ ou un fichier *.local.json
- afficher un secret (jeton, clé, adresse iCal)
- envoyer au client, encaisser ou signer
- Engager Liam (envoyer au client, encaisser, publier, signer) : `peut_engager: false`, tout passe par `B2B/a-valider/`.

## Entrées et sorties
**Chaîne vidéo :** Veille → Scripts → Marketing → **Création** → Monteur (ligne B) → Ton OK de Liam (« go publier », une fois par ligne) → Publication (verrouillée) → Nettoyage (fiche « ⛓️ Chaîne vidéo »)
- **Reçoit de :** Marketing : script enrichi : accroche gardée, rythme, sous-titres
- **Produit :** vidéo rendue (ligne A : directement dans Videos/a-valider)
- **Passe à :** Monteur (ligne B)

**Lit :**
- Videos/scripts
- Videos/videos-config.json
- Videos/SKILL-VIDEOS.md
- Videos/outils/stick-stage (hors git)

**Écrit :**
- Videos/a-valider/AAAA-MM-JJ-HHMM.mp4 (+ .txt, .json)
- Videos/a-part (vidéo refusée par le monteur)
- Videos/travail (temporaire)
- Videos/journal-videos.csv
- Videos/videos-creation-journal.log
- B2B/logs/agents/videos-creation (trace)

**Discord :** aucun · **Plafond :** 0 messages par jour · **Envoi au client :** non

## Horaire et état
- **Horaire :** chaque jour à 06:00, 14:00, 22:00, plage tous les jours 06:00-23:00
- **Tâche serveur :** entrée dans `B2B/agents/serveur-taches.json`, active à partir du 2026-11-17 ; tourne seulement si l'agent est dans `agents_actifs` (choix de Liam)
- **Contrat :** valide (`python B2B\harness\valider.py`)
- **Garde branchée :** non
- Bloque : kill-switch `B2B\STOP`, lien Stripe non autorisé, phrase interdite (OFFRE-REFERENCE.json), secret dans le texte.
- Avertit : machine non active, envoi_automatique = false (simulation), hors horaires du contrat (06:00-23:00), plafond de 0 messages par jour.
- **Tests :** `tests/agents/test_videos.py`
- **Alerte si silence :** après 06:45 (surveillant)

<!-- DYNAMIQUE:DEBUT -->
**Derniers résultats de test (cette machine) :**
- `tests/agents/test_videos.py` : pas encore lancé par `generer-fiches.py --tests`

**Dernière trace :** aucune · **Dernière erreur :** aucune · **Dans agents_actifs (cette machine) :** non (Liam l'ajoute s'il veut le planifier)

### Historique (5 dernières traces, sans données client)
- aucune trace sur cette machine
<!-- DYNAMIQUE:FIN -->

## Skill et règles
- `.claude/skills/agent-videos-creation/SKILL.md` (copie : `docs/agents/skills/agent-videos-creation.md`)
- Règles : Videos/SKILL-VIDEOS.md (règles communes de l'équipe Vidéos, relues avant chaque exécution ; absentes ou incomplètes = refus, code 3)
- Pas de preuve = pas de fait : « il a tourné » = une trace du jour `ok: true` ci-dessus ; « c'est corrigé » = ses tests puis `tests\b2b-rapide.ps1` en vert.
<!-- GENERE:FIN -->

## Liens et décisions

_Zone conservée à chaque régénération : liens vers docs\decisions et docs clés seulement._

Liens : aucun pour l'instant.

## Notes de Liam

_Zone libre, conservée telle quelle à chaque régénération._
