---
name: agent-videos-monteur
description: Fiche de rôle de l'agent Monteur vidéos (équipe Vidéos TikTok, rattachée à Jarvis CEO) — appelé par videos-creation pour chaque sketch à deux de la ligne B, sans token Claude ni réseau : impose un changement d'image (coupe, gros plan ou zoom) au moins toutes les 3 s en lisant la timeline compilée de stick-stage avant le rendu, ajuste le rythme si la durée prévue sort de 25-35 s, mixe musique CC0 (-18 dB sous la voix), bruitages CC0 et sonnerie générée par code, incruste de très grands sous-titres de 1 à 3 mots en zone sûre, puis contrôle la vidéo (durée 25-35 s, aucune image noire, sous-titres en zone sûre, voix audible, plans de 3 s au plus) ; 2 reprises au plus, sinon mise à part dans Videos\a-part avec le motif. À utiliser pour vérifier ou corriger Videos\agents\monteur.py (etat).
---
# Agent Monteur vidéos (`videos-monteur`)

**Responsable :** Jarvis (CEO). **Script :** `Videos/agents/monteur.py` (appelé par `Videos/agents/creation.py`, aucune tâche planifiée à lui). **Contrat :** `B2B/harness/contrats/videos-monteur.json`.
**Gratuit :** code + ffmpeg + stick-stage (MIT). Aucun token Claude, aucun réseau, rien de publié.

## Rôle
Monter chaque sketch de la ligne B pour la Création : plans de 3 s au plus, son CC0, sous-titres en zone sûre, contrôle qualité ; sinon mise à part avec le motif. Limites : appelé par Création seulement (aucune tâche planifiée), ne publie jamais, aucun réseau ni token.

## Ordres pas à pas (lus dans le script)
1. `RS.rendre(..., retoucher=retoucher_plans)` : après chaque compilation du skit (avant le rendu de 2 à 3 min), `retoucher_plans` lit `generated/timeline.json` :
   durée prévue (corps + carte de fin de 2 s) hors 25-35 s -> rythme « snappy » (ou « argument ») si trop long, « sitcom » si trop court ;
   sinon un zoom bref (punch-in) au milieu de chaque plan de plus de 3 s. Recompilation, 4 fois au plus. Le skit impose déjà un cadrage différent à chaque réplique (`rendu_stickstage.plan_de`).
2. Rendu stick-stage (Gérard + interlocuteur, bouche synchronisée par Rhubarb, bruitages CC0 du catalogue dans le skit).
3. `bande_son` : voix du rendu, musique CC0 (room / resolve / mystery selon la catégorie) en boucle, réglée à 18 dB sous la voix (LUFS mesurés par ffmpeg), sonneries (générées par code) dans le silence avant la réplique, normalisation finale -14 LUFS.
4. Sous-titres `.ass` : 1 à 3 mots (16 caractères au plus), 104 px, contour 9 px, mot clé jaune, bas du texte à y = 1240, marges x 120-880 ; titre du sketch en haut 2,5 s ; « Contenu généré par IA » ; carte de fin bleu nuit 2 s.
5. Contrôle qualité : durée 25-35 s, `blackdetect` sans image noire, `controle_sous_titres` (2 lignes au plus, zone sûre), écart voix / musique ≥ 12 dB, aucun plan > 3 s (timeline).
6. Échec : nouvel essai (rythme changé si la durée est en cause), 3 essais au plus ; puis `Videos/a-part/<vidéo>.mp4` + `.json` (motifs, rapport), ligne de journal, trace du harness `ok: false`.

## Entrées et sorties (place dans la chaîne)
- **Reçoit de :** **Création** (script du sketch déjà gardé, voix par personnage déjà faites).
- **Produit :** la vidéo montée rendue à Création (qui la range dans `a-valider`) ou `Videos/a-part/<vidéo>.mp4` + `.json` (motifs).
- **Passe à :** **Création** (rangement), puis le **ton OK de Liam** et **Publication**.
- Chaîne vidéo : Veille → Scripts → Marketing → Création (→ Monteur, ligne B) → ton OK de Liam (« go publier », une fois par ligne) → Publication → Nettoyage. Fiche : `docs/agents/⛓️ Chaîne vidéo.md`.

## Ce qu'il ne fait jamais
- Publier ; rendre deux vidéos en même temps ; utiliser une musique ou un son sans licence CC0 notée dans `Videos/SKILL-VIDEOS.md` ; laisser un fond noir plein ; appeler Claude ou un service payant.

## Cas d'erreur
- Durée prévue hors 25-35 s : rythme changé avant le rendu (snappy, sitcom), voix accélérée de 12 % au plus.
- Contrôle qualité refusé (image noire, sous-titres hors zone, voix trop basse, plan > 3 s) : nouvel essai, 3 au plus.
- Échec après 3 essais : mise à part dans `Videos/a-part`, trace `ok: false` avec les motifs.
- Rendu stick-stage ou ffmpeg en erreur : compté comme un essai raté.
- Toute erreur laisse une trace `ok: false`, lue par le surveillant si l'agent est dans `agents_actifs`.

## Règles qu'il suit
- Il suit `Videos/SKILL-VIDEOS.md` relu par Création qui l'appelle, sections « Sous-titres », « Rythme et format » (musiques et bruitages CC0 listés dans le skill).
- Harness : contrat `B2B/harness/contrats/videos-monteur.json` (`peut_engager: false`) ; garde : le texte est déjà passé par celle de Création avant l'appel ; une trace par sketch monté (`_trace` de `monteur.py`) dans `B2B/logs/agents/videos-monteur/AAAA-MM-JJ.jsonl`.
- Ce qui engage Liam (publier, envoyer, encaisser, signer) n'est jamais fait sans son accord ; la publication reste verrouillée par ligne jusqu'à son « go publier ».
- Règle d'or : pas de preuve = pas de fait. « Il a tourné » se prouve par la trace du jour (`ok: true`) et le fichier produit ; « c'est corrigé » par `python tests\agents\test_videos.py` puis `tests\b2b-rapide.ps1` en vert, sortie montrée.

## Vérifier qu'il a bien tourné
- `python Videos\agents\monteur.py etat` (vidéos mises à part et dernier motif) ; le `.json` de chaque vidéo de `a-valider` porte `controle_qualite`, `essais`, `ecart_voix_musique_db`, `musique`, `musique_licence`.
- Test : `python tests\agents\test_videos.py` (classes Monteur et Sketches, aucun rendu). Pas de preuve = pas de « fait ».
