# Vidéos TikTok — équipe d'agents (16/11/2026)

Tout est gratuit : Qwen local (Ollama, `qwen2.5:3b`) pour les textes, voix Microsoft gratuite (`edge-tts`), rendu `stickfigure-pipeline-v2`, ffmpeg, Playwright sur le navigateur Edge du serveur. Aucun token Claude, aucune carte bancaire.
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
- **B** : recrutement de call callers pour vendre des sites web, compte séparé (passage 14:00). Aucune ville, aucun revenu chiffré ; « à la commission » tant que `lignes.B.taux_commission` est vide.
Réglages : `videos-config.json` > `lignes` (ton, compte, hashtags, message, brouillon d'accroche, lieux interdits, taux de commission). Bibliothèque d'accroches : `hooks.md` (= `hooks-base.md` + formules repérées par la veille, hors git).
`journal-videos.csv` (hors git) : une ligne par accroche choisie, vidéo prête, publication, arrêt et suppression (date ; agent ; vidéo ; ligne ; compte ; statut ; hook ; détail).

## Outils (dans `outils/`, hors git, à recloner sur une autre machine)
- `git clone --depth 1 https://github.com/vishnukayyala/stickfigure-pipeline-v2` puis `npm install` et `node node_modules/puppeteer/install.mjs` (npm 11 bloque le script d'installation).
- Python : `pip install --user edge-tts` ; ffmpeg : `winget install -e --id Gyan.FFmpeg --scope user`.
- stick-stage (`tamtree-ai/stick-stage`) a été essayé sur le même sujet : il plante sous Windows (il lance `node_modules\.bin\remotion` sans `.cmd`, ENOENT). Écarté.
- Sous-titres mot à mot : faster-whisper ne se charge pas sur ce PC (DLL de ctranslate2 manquante) ; `creation.py` demande à edge-tts (gratuit, déjà utilisé pour la voix) le temps de chaque mot, recalé sur la durée réelle de chaque phrase (`scene_timings.json` de l'outil), et incruste un `.ass` (2 à 4 mots, mot clé en jaune, Arial Black, zone sûre TikTok).

## Publication : un seul « go publier » par ligne
Avant le go d'une ligne, rien n'est publié sur son compte : tout reste dans `a-valider\`. Pour ouvrir la ligne X (Liam seulement) :
1. Regarder la première vidéo de la ligne dans `a-valider\` et dire « go publier ».
2. `pip install --user playwright` (aucun navigateur à télécharger : Edge du serveur).
3. `python Videos\agents\publication.py connexion --ligne X` : se connecter soi-même au compte de la ligne dans la fenêtre, puis la fermer (l'agent ne tape jamais de mot de passe).
4. `python Videos\agents\publication.py publier --essai --ligne X` : essai jusqu'au bouton Publier, sans cliquer (obligatoire avant le premier envoi).
5. Config locale de `Videos` (machine, hors git) : `"lignes": {"X": {"go_publier": true}}` ; `videos-publication` dans `agents_actifs` ; statut du contrat à `actif`.

Arrêt : créer un fichier `Videos\STOP` (ou `B2B\STOP`) bloque toute publication.
