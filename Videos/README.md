# Vidéos TikTok — équipe d'agents (16/11/2026)

Tout est gratuit : Qwen local (Ollama, `qwen2.5:3b`) pour les textes, voix Microsoft gratuite (`edge-tts`) avec bascule automatique sur Kokoro en local (`agents/voix.py`), rendu `stickfigure-pipeline-v2`, ffmpeg, Playwright sur le navigateur Edge du serveur. Aucun token Claude, aucune carte bancaire.
**Règles de toute l'équipe : `SKILL-VIDEOS.md`**, relu par chaque agent avant chaque exécution (fichier absent ou incomplet = l'agent refuse de tourner).

| Agent | Script | Quand (serveur) | Sortie |
|---|---|---|---|
| Nettoyage | `agents/nettoyage.ps1` | 03:30 | supprime vidéos et intermédiaires de plus de `nettoyage_jours` jours (ligne dans `journal-videos.csv` avant) |
| Veille | `agents/veille.py jour` | 04:30 | `veille/AAAA-MM-JJ.md` (30 jours), formules d'accroche ajoutées à `hooks.md` |
| Scripts | `agents/scripts.py jour` | 05:00 | `scripts/AAAA-MM-JJ-HHMM.json`, `scripts/sujets.json` |
| Marketing | `agents/marketing.py jour` | 05:30 | accroche notée (3 candidates), rythme, sous-titres dans le script ; ligne dans `journal-videos.csv` |
| Création | `agents/creation.py passage` | 06:00, 14:00, 22:00 | `a-valider/AAAA-MM-JJ-HHMM.mp4` + `.txt` + `.json` |
| Publication | `agents/publication.py publier` | 06:20, 14:20, 22:20 | **fermée** par ligne jusqu'au « go publier » de Liam |

Fiches de rôle : `.claude/skills/agent-videos-*` ; contrats : `B2B/harness/contrats/videos-*.json` ; test : `tests/agents/test_videos.py` (dans `tests\tout.ps1`).
Les tâches passent par le lanceur B2B (`B2B/agents/serveur-b2b.ps1` : machine active, verrou global, priorité basse, traces lues par le surveillant ; les `.ps1` sont lancés par PowerShell) ;
elles ne sont créées que pour les agents que Liam met dans `agents_actifs` (configuration locale B2B).

## Deux lignes, deux comptes
- **A** : stickman divertissement / explications, compte TikTok actuel (passages 06:00 et 22:00).
- **B** : histoires drôles du business avec Gérard (`histoires-base.md`, `agents/histoires.py`), compte séparé de recrutement (passage 14:00) ; « on recrute des call callers à la commission » seulement dans la fin. Aucune ville, aucun revenu chiffré.
Réglages : `videos-config.json` > `lignes` (ton, compte, voix, hashtags, message, brouillon d'accroche, lieux interdits, taux de commission). Bibliothèque d'accroches : `hooks.md` (= `hooks-base.md` + formules repérées par la veille, hors git) ; les formules à trous `- A01 | …` / `- B01 | …` de `hooks-base.md` sont écrites à la main : Qwen les choisit et remplit les trous, il n'invente pas l'accroche.
`journal-videos.csv` (hors git) : une ligne par accroche choisie, vidéo prête, publication, arrêt et suppression (date ; agent ; vidéo ; ligne ; compte ; statut ; hook ; détail ; tts = moteur de voix réellement utilisé ; histoire ; formule d'accroche ; thème ; fin = variante de l'appel à l'action ; durée ; voix ; date de publication ; adresse TikTok). Un fichier à l'ancien en-tête est migré tout seul. L'adresse TikTok n'est pas encore relevée par l'agent publication (à ajouter avant le premier « go publier »).

## Outils (dans `outils/`, hors git, à recloner sur une autre machine)
- `git clone --depth 1 https://github.com/vishnukayyala/stickfigure-pipeline-v2` puis `npm install` et `node node_modules/puppeteer/install.mjs` (npm 11 bloque le script d'installation).
- Python : `pip install --user edge-tts` ; ffmpeg : `winget install -e --id Gyan.FFmpeg --scope user`.
- **Rendu retenu le 17/11/2026 : stick-stage** (`tamtree-ai/stick-stage`, MIT), style toon, `"outil": "stick-stage"` dans la config (`agents/rendu_stickstage.py`, `agents/stickstage-rendu.mts`, Gérard : `stick-stage/gerard.json`, personnage du skit, l'outil n'est pas modifié). Comparaison sur la même scène de 15 s (`essais\`, hors git ; voix edge-tts identique) :
  - theunfinishedco (HUSS41N), flat : le plus beau (bureau de jour, personnage adulte, 5 plans, transitions), 31 s de rendu, 905 Mo ; stick : 30 s, 922 Mo. **Aucune licence** : interdit de l'utiliser ou d'en copier le code sans l'accord de l'auteur. À creuser seulement si l'auteur l'accorde.
  - figures (cherifya, MIT) : papier ancien, personnage minuscule, ni décor ni caméra ; 79 s, 676 Mo ; son rendu officiel exige Playwright. Écarté.
  - stick-stage toon (MIT) : couleurs, décors de jour, gros plans automatiques, bouche synchronisée ; 76 s pour 18 s, 1,3 Go (vidéo de 33 s : environ 3 min, 1,05 Go). Retenu.
  - skill Claude « stickman » (michxlai, MIT, installé dans `~/.claude/skills/synced`) : pas retenu ; son rendu exige Playwright + Chromium, il sort du 1920x1080, sa palette est un crépuscule (pas des couleurs de jour) et il fait réécrire un film par Claude à chaque vidéo (tokens Claude) ; aucune vidéo quotidienne n'en dépend.
- Montage que stick-stage fait seul (aucun monteur à écrire) : choix du plan pour chaque réplique (plan à deux, moyen, gros plan, très gros plan), coupes aux changements de réplique, gros plan de réaction après la chute, « punch-ins » (zooms brefs) sur les temps forts, textes « slam », transitions entre scènes (coupe, fondu, glissé, volet, whip), style de réalisation (`classic`, `deadpan`, `snappy`… : pauses, durée de réaction, transition), bouche synchronisée (Rhubarb), clignements et respiration, symboles (sueur, point d'exclamation), bruitages de son catalogue, sous-titres (désactivés : on incruste les nôtres, mot à mot). Pas de mouvement de caméra libre (pas de travelling ni de panoramique) et Gérard reste à sa marque (il ne traverse pas la pièce).
- stick-stage plantait sous Windows : il lance `node_modules\.bin\remotion` par `execFileSync` (sans shell, donc sans `.cmd`) : ENOENT. Correctif : `python Videos\correctifs\stick-stage-windows.py` (Node lance directement `@remotion/cli/remotion-cli.js` ; idempotent ; à relancer après chaque clonage ; `--verifier` pour contrôler). Testé dans `tests/agents/test_videos.py`.
- Voix de secours Kokoro (locale, gratuite, sans compte) : `pip install --user kokoro-onnx`, puis dans `outils/kokoro/` le modèle `kokoro-v1.0.int8.onnx` et `voices-v1.0.bin` (github.com/thewh1teagle/kokoro-onnx, release model-files-v1.0). Le runtime Visual C++ n'est pas installé sur le serveur : `outils/kokoro/dll/` contient des copies signées Microsoft de `msvcp140.dll`, `msvcp140_1.dll`, `vcruntime140.dll`, `vcruntime140_1.dll` (prises dans Edge et OneDrive), chargées seulement par `voix.py`. Kokoro n'a qu'une voix française (`ff_siwis`, féminine). Échec d'edge-tts simulé : variable `JARVIS_VIDEOS_EDGE_ECHEC=1`.
- Sous-titres mot à mot : faster-whisper ne se charge pas sur ce PC (DLL de ctranslate2 manquante) ; `creation.py` demande à edge-tts (gratuit, déjà utilisé pour la voix) le temps de chaque mot, recalé sur la durée réelle de chaque phrase (`scene_timings.json` de l'outil), et incruste un `.ass` (2 à 4 mots, mot clé en jaune, Arial Black, zone sûre TikTok).

## Publication : un seul « go publier » par ligne
Avant le go d'une ligne, rien n'est publié sur son compte : tout reste dans `a-valider\`. Pour ouvrir la ligne X (Liam seulement) :
1. Regarder la première vidéo de la ligne dans `a-valider\` et dire « go publier ».
2. `pip install --user playwright` (aucun navigateur à télécharger : Edge du serveur).
3. `python Videos\agents\publication.py connexion --ligne X` : se connecter soi-même au compte de la ligne dans la fenêtre, puis la fermer (l'agent ne tape jamais de mot de passe).
4. `python Videos\agents\publication.py publier --essai --ligne X` : essai jusqu'au bouton Publier, sans cliquer (obligatoire avant le premier envoi).
5. Config locale de `Videos` (machine, hors git) : `"lignes": {"X": {"go_publier": true}}` ; `videos-publication` dans `agents_actifs` ; statut du contrat à `actif`.

Arrêt : créer un fichier `Videos\STOP` (ou `B2B\STOP`) bloque toute publication.
