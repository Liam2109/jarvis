---
agent: videos-monteur
aliases: [✂️ Monteur vidéos]
name: videos-monteur
role: "Appelé par videos-creation pour chaque sketch à deux de la ligne B : plans de 3 s au plus, musique et bruitages CC0, sous-titres de 1 à 3 mots en zone sûre, contrôle qualité (25-35 s, aucune image noire, voix audible) ; 2 reprises au plus, sinon mise à part dans Videos/a-part avec le motif."
machine: "gros PC"
planification: "à la demande (aucune tâche serveur), plage tous les jours 06:00-23:00"
sorties: "Videos/travail/<vidéo> (temporaire), Videos/a-part/AAAA-MM-JJ-HHMM.mp4 (+ .json, motif), Videos/videos-monteur-journal.log, B2B/logs/agents/videos-monteur"
responsable: Jarvis (CEO)
statut: actif
mode: réel
horaire: "à la demande (aucune tâche serveur), plage tous les jours 06:00-23:00"
tags: [agent-b2b]
---
<!-- GENERE:DEBUT (régénéré par python B2B\harness\generer-fiches.py : ne pas modifier) -->
# ✂️ Monteur vidéos

**Agent :** `videos-monteur` · **Statut :** actif · **Responsable :** Jarvis (CEO) · **Machine :** gros PC
**Horaire :** à la demande (aucune tâche serveur), plage tous les jours 06:00-23:00
**Script :** `Videos/agents/monteur.py` · **Contrat :** `B2B/harness/contrats/videos-monteur.json`

## Rôle et limites
### Mission
Monte chaque sketch de la ligne B (appelé par videos-creation) : plans de 3 s au plus, son CC0, sous-titres en zone sûre, contrôle qualité ; sinon mise à part.

### Ce qu'il fait étape par étape
1. `RS.rendre(..., retoucher=retoucher_plans)` : après chaque compilation du skit (avant le rendu de 2 à 3 min), `retoucher_plans` lit `generated/timeline.json` :
   durée prévue (corps + carte de fin de 2 s) hors 25-35 s -> rythme « snappy » (ou « argument ») si trop long, « sitcom » si trop court ;
   sinon un zoom bref (punch-in) au milieu de chaque plan de plus de 3 s. Recompilation, 4 fois au plus. Le skit impose déjà un cadrage différent à chaque réplique (`rendu_stickstage.plan_de`).
2. Rendu stick-stage (Gérard + interlocuteur, bouche synchronisée par Rhubarb, bruitages CC0 du catalogue dans le skit).
3. `bande_son` : voix du rendu, musique CC0 (room / resolve / mystery selon la catégorie) en boucle, réglée à 18 dB sous la voix (LUFS mesurés par ffmpeg), sonneries (générées par code) dans le silence avant la réplique, normalisation finale -14 LUFS.
4. Sous-titres `.ass` : 1 à 3 mots (16 caractères au plus), 104 px, contour 9 px, mot clé jaune, bas du texte à y = 1240, marges x 120-880 ; titre du sketch en haut 2,5 s ; « Contenu généré par IA » ; carte de fin bleu nuit 2 s.
5. Contrôle qualité : durée 25-35 s, `blackdetect` sans image noire, `controle_sous_titres` (2 lignes au plus, zone sûre), écart voix / musique ≥ 12 dB, aucun plan > 3 s (timeline).
6. Échec : nouvel essai (rythme changé si la durée est en cause), 3 essais au plus ; puis `Videos/a-part/<vidéo>.mp4` + `.json` (motifs, rapport), ligne de journal, trace du harness `ok: false`.

### Ce qu'il n'a pas le droit de faire
- publier une vidéo
- rendre deux vidéos en même temps
- utiliser une musique ou un son sans licence CC0 notée dans Videos/SKILL-VIDEOS.md
- laisser un fond noir plein
- produire une vidéo sans la mention « Contenu généré par IA »
- appeler Claude ou un service payant
- toucher à memoire/, .env, config.json, .obsidian/ ou un fichier *.local.json
- envoyer au client, encaisser ou signer
- Engager Liam (envoyer au client, encaisser, publier, signer) : `peut_engager: false`, tout passe par `B2B/a-valider/`.

## Entrées et sorties
**Chaîne vidéo :** Veille → Scripts → Marketing → Création → **Monteur (ligne B)** → Ton OK de Liam (« go publier », une fois par ligne) → Publication (verrouillée) → Nettoyage (fiche « ⛓️ Chaîne vidéo »)
- **Reçoit de :** Création : vidéo rendue (ligne A : directement dans Videos/a-valider)
- **Produit :** sketch monté et contrôlé, rangé dans Videos/a-valider (sinon Videos/a-part)
- **Passe à :** Ton OK de Liam (« go publier », une fois par ligne)

**Lit :**
- Videos/travail/<vidéo> (voix, rendu)
- Videos/outils/stick-stage (hors git : skit, timeline, musique et bruitages CC0)

**Écrit :**
- Videos/travail/<vidéo> (temporaire)
- Videos/a-part/AAAA-MM-JJ-HHMM.mp4 (+ .json, motif)
- Videos/videos-monteur-journal.log
- B2B/logs/agents/videos-monteur

**Discord :** aucun · **Plafond :** 0 messages par jour · **Envoi au client :** non

## Horaire et état
- **Horaire :** à la demande (aucune tâche serveur), plage tous les jours 06:00-23:00
- **Tâche serveur :** aucune (appelé par un autre agent ou lancé à la main)
- **Contrat :** valide (`python B2B\harness\valider.py`)
- **Garde branchée :** sans objet : le texte du sketch est gardé par videos-creation avant l'appel (aucun envoi)
- Bloque : kill-switch `B2B\STOP`, lien Stripe non autorisé, phrase interdite (OFFRE-REFERENCE.json), secret dans le texte.
- Avertit : machine non active, envoi_automatique = false (simulation), hors horaires du contrat (06:00-23:00), plafond de 0 messages par jour.
- **Tests :** `tests/agents/test_videos.py`
- **Alerte si silence :** aucune

<!-- DYNAMIQUE:DEBUT -->
**Derniers résultats de test (cette machine) :**
- `tests/agents/test_videos.py` : pas encore lancé par `generer-fiches.py --tests`

**Dernière trace :** 2026-11-17 00:22 ok · **Dernière erreur :** 2026-11-17 00:11 monter 2026-11-17-1400 (durée 35.8 s (25 à 35 s attendues)) · **Dans agents_actifs (cette machine) :** non (Liam l'ajoute s'il veut le planifier)

### Historique (5 dernières traces, sans données client)
- 2026-11-17 00:22 | monter 2026-11-18-1400 | ok | 205.41 s
- 2026-11-17 00:18 | monter 2026-11-17-1400 | ok | 301.63 s
- 2026-11-17 00:11 | monter 2026-11-17-1400 | ERREUR (durée 35.8 s (25 à 35 s attendues)) | 669.24 s
- 2026-11-16 23:58 | monter 2026-11-17-1400 | ERREUR (durée 43.9 s (25 à 35 s attendues); plan de 3.2 s à 0.0 s (3 s au plus)) | 777.96 s
<!-- DYNAMIQUE:FIN -->

## Skill et règles
- `.claude/skills/agent-videos-monteur/SKILL.md` (copie : `docs/agents/skills/agent-videos-monteur.md`)
- Règles : Videos/SKILL-VIDEOS.md (règles communes de l'équipe Vidéos, relues avant chaque exécution ; absentes ou incomplètes = refus, code 3)
- Pas de preuve = pas de fait : « il a tourné » = une trace du jour `ok: true` ci-dessus ; « c'est corrigé » = ses tests puis `tests\b2b-rapide.ps1` en vert.
<!-- GENERE:FIN -->

## Liens et décisions

_Zone conservée à chaque régénération : liens vers docs\decisions et docs clés seulement._

Liens : aucun pour l'instant.

## Notes de Liam

_Zone libre, conservée telle quelle à chaque régénération._
