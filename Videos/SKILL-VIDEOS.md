# SKILL-VIDEOS — règles de l'équipe Vidéos TikTok (16/11/2026)

Relu par CHAQUE agent vidéo avant chaque exécution (`commun.regles()` : fichier absent ou sans les sections ci-dessous = l'agent refuse de tourner).
Les sections « Règles pour Qwen » et « Grille des accroches » sont injectées telles quelles dans les consignes de Qwen. Le code vérifie ensuite chaque règle (garde-fous codés) : une règle écrite ici ne suffit jamais seule.

## Équipe (dans l'ordre d'un passage)
1. **Veille** (`agents/veille.py`, 04:30) : recherche web gratuite (flux RSS Google Actualités, jamais TikTok) de ce qui marche : stickman, motion design, formats courts ; note du jour dans `veille\`, formules d'accroche repérées ajoutées à `hooks.md` (bibliothèque = modèle versionné `hooks-base.md` + formules repérées, réécrite chaque jour).
2. **Scripts** (`agents/scripts.py`, 05:00) : Qwen écrit le script de chaque passage (une idée, phrases courtes, légende).
3. **Marketing** (`agents/marketing.py`, 05:30) : réécrit accroche, rythme et sous-titres ; 3 accroches notées, la meilleure gardée et inscrite dans `journal-videos.csv`.
4. **Création** (`agents/creation.py`, 06:00, 14:00, 22:00) : fabrique la vidéo (stick-stage en style toon, voix edge-tts, ffmpeg) dans `a-valider\`.
4 bis. **Monteur** (`agents/monteur.py`, appelé par Création pour la ligne B) : plans de 3 s au plus, musique et bruitages, sous-titres, contrôle qualité (25-35 s, aucune image noire, sous-titres en zone sûre, voix au moins 12 dB au-dessus de la musique) ; 2 reprises au plus, puis vidéo mise à part dans `a-part\` avec le motif.
5. **Publication** (`agents/publication.py`, 06:20, 14:20, 22:20) : publie sur TikTok seulement les lignes que Liam a ouvertes par « go publier ».
6. **Nettoyage** (`agents/nettoyage.ps1`, 03:30) : supprime les vidéos et fichiers intermédiaires de plus de `nettoyage_jours` jours, après une ligne dans `journal-videos.csv`.

## Gratuit, local, sans token Claude
- Texte : Qwen local via Ollama (`modele`). Voix : edge-tts (gratuite), bascule automatique sur Kokoro local s'il échoue (erreur, pas d'internet, plus de 30 s) ; une voix fixe par ligne (`lignes.<X>.voix`) ; moteur noté dans `journal-videos.csv` (colonne `tts`). Montage : stickfigure-pipeline-v2 + ffmpeg. Navigateur : Playwright sur le navigateur déjà installé.
- Aucun service payant, aucune carte bancaire, aucun appel à Claude ni à une API payante.

## Rythme et format
- 3 vidéos par jour, aux heures de `passages` (06:00, 14:00, 22:00 : ne pas les changer sans Liam). Ligne de chaque passage : `series_par_passage`.
- Vertical 9:16 (1080x1920), rendu stick-stage en style toon : couleurs réalistes de jour, vrai décor (bureau, cabinet, librairie, café, cuisine, salon, rue, parc), Gérard articulé (expressions, gestes, bouche synchronisée), plusieurs plans, coupes et transitions ; jamais de fond noir plein (carte de fin bleu nuit).
- TikTok uniquement. Chaque vidéo porte la mention « Contenu généré par IA » à l'écran et dans la légende, et l'étiquette TikTok « contenu généré par IA » est activée à la publication (introuvable = rien n'est publié).

## Publication : un seul « go publier » par ligne
- Liam valide UNE fois la première vidéo de chaque ligne (A, B) en disant « go publier ». Avant ce go, rien n'est publié sur le compte de la ligne : tout reste dans `a-valider\`.
- Après le go d'une ligne (`lignes.<X>.go_publier: true` dans `videos-config.local.json` de la machine, jamais par un agent), ses vidéos sont publiées automatiquement.
- Un essai à blanc (`publier --essai --ligne X` : jusqu'au bouton Publier, sans cliquer) doit avoir réussi avant le premier vrai envoi d'une ligne.
- Plafond : 3 publications par jour et par compte ; jamais deux publications en même temps ; délais aléatoires entre les gestes.
- Anomalie (captcha, connexion ou vérification demandée, interface inattendue, échec) = arrêt, aucun contournement, aucune nouvelle tentative le même jour, journal + alerte Discord.
- `Videos\STOP` (ou `B2B\STOP`) présent = plus aucune publication.
- L'agent ne tape JAMAIS de mot de passe et n'en stocke aucun : Liam se connecte lui-même, une fois, dans le profil du navigateur de la ligne.

## Deux lignes éditoriales (réglages dans `videos-config.json` > `lignes`, surchargés par `videos-config.local.json`)
- **A — stickman divertissement / explications**, compte TikTok actuel. Ton : vivant, simple, vouvoiement, un bonhomme bâton qui explique une chose concrète du web pour les artisans et commerçants. Fin : « votre page répond à ça ? le lien est dans la description » ; jamais de rendez-vous de 15 minutes, aucune promesse.
- **B — sketch à deux** (compte TikTok séparé, recrutement de call callers, décision de Liam du 17/11/2026) : Gérard + un interlocuteur (client, collègue, voisin…), 6 à 8 répliques de 10 mots au plus, chacune répond à la précédente, un retournement drôle, puis la fin dite par Gérard face caméra ; 25 à 35 s. 40 % comédie de Gérard au téléphone, 40 % leçons de vente au téléphone, 20 % entrepreneuriat et quotidien. Les 30 sketches sont écrits à la main dans `sketches-base.json` : **aucune phrase n'est inventée par Qwen**, qui choisit seulement le sketch et remplit les champs ({metier}, {objet}, {lieu}, {nom}) avec les listes écrites à la main (toute autre valeur est refusée). Aucun sketch rejoué dans les 20 dernières vidéos. 3 fins tournantes (« on recrute des call callers à la commission », formulaire en bio ou DM ; jamais « près de Rouen » ni « chez moi »). Deux voix edge-tts (Gérard : Henri ; interlocutrice : Denise ; interlocuteur : Rémy) ; en bascule Kokoro (une seule voix française), Gérard plus grave (hauteur 0,85) que l'interlocuteur.
  - Ne cite ni ville ni lieu.
  - Taux de commission : champ `lignes.B.taux_commission`, laissé vide ; Liam le renseigne. Tant qu'il est vide, la vidéo dit seulement « à la commission ».
  - Candidature : « lien en bio », jamais une adresse épelée (ni « www », ni « point com », ni lien).
  - INTERDIT : promettre ou chiffrer un revenu, « mon closer gagne », témoignage (faux ou non), statistique non vérifiée, nombre de ventes, trouver le numéro privé d'un décideur, imiter une vraie personne, « rendez-vous de 15 minutes », « Découvrez comment ».

## Règles pour Qwen
- Une seule idée par vidéo. Phrases courtes, à l'oral, naturelles, comme on parle. Aucune phrase molle (« dans cette vidéo », « aujourd'hui on va voir », « il est important de », « n'hésitez pas », « tout simplement », « découvrez »).
- Aucun chiffre ni nombre, même en lettres (les seuls chiffres sont ajoutés par le code). Aucune promesse de résultat, de clients, de gain ou de revenu. Aucun témoignage, aucun client réel ou inventé. Aucun contenu copié : les titres de la veille donnent des idées de format, jamais des phrases à reprendre.
- Pas de superlatif, pas de « garanti », « facile », « secret », « incroyable », « meilleur ». Pas d'appel à s'abonner, liker ou commenter. Pas de lien.
- Seulement le texte lu par la voix : jamais de caméra, de plan, de scène, de narrateur.
- Ligne B : jamais de ville, de région ni de lieu ; jamais de montant, de pourcentage ni de nombre de ventes.

## Grille des accroches
L'accroche est la première phrase : lue en 2 secondes au plus, elle crée tension ou curiosité. Elle vient TOUJOURS d'une formule à trous écrite à la main dans `hooks.md` (Qwen choisit la formule et remplit les trous, il n'invente pas). Ligne A : on parle à l'artisan ou au commerçant (vouvoiement), jamais à son client ; ligne B : on tutoie le futur call caller. Jamais « Découvrez comment ». Note sur 10, calculée par le code (`marketing.noter_accroche`) :
- **+3** forme qui accroche : question, contradiction (« pourtant », « faux », « arrête », « personne ne »), erreur courante (« erreur », « vous perdez », « tu rates »), ou résultat montré avant l'explication.
- **+3** courte : 6 mots ou moins (+3), 7 à 8 mots (+2), 9 à 10 mots (+1), plus de 10 mots (0 : plus de 2 secondes).
- **+2** parle directement au public de la ligne (« vous » pour A, « tu » pour B).
- **+1** concrète : nomme une chose qu'on voit (téléphone, horaires, bouton, appel, liste, rendez-vous, client, page…).
- **+1** neuve : aucune des 20 dernières accroches de `journal-videos.csv` n'a les mêmes mots.
- **Éliminée (0)** : chiffre, promesse, mot interdit, phrase molle, mauvais public ou adresse épelée. Ouverture molle (« Bonjour », « Aujourd'hui », « Découvrez », « Dans cette vidéo ») : −3.
Égalité : la plus courte gagne. Les 3 accroches, leur note et la gagnante sont écrites dans `journal-videos.csv`.

## Rétention
- 20 à 35 secondes (fin comprise) ; un changement visuel toutes les 2 à 3 secondes (une phrase = une image, 4 à 11 mots par phrase) ; fin en boucle (la dernière phrase renvoie à l'accroche) ou question qui relance.

## Sous-titres
- Mot par mot, synchronisés avec la voix : temps des mots donnés par edge-tts (repères WordBoundary, gratuits), recalés sur le début réel de chaque réplique dans la vidéo ; à défaut (Kokoro), répartis selon la longueur des mots.
- Ligne B (sketch) : très grands (104 px), 1 à 3 mots à la fois (16 caractères au plus par groupe), au centre vers le bas (bas du texte à y = 1240), contour de 9 px, mot clé en jaune ; le monteur vérifie que chaque sous-titre tient en 2 lignes entre x = 120 et x = 880 et au-dessus de y = 1300.
- Grosse police grasse (Arial Black / Arial gras), blanc sur contour noir épais, 2 à 4 mots à l'écran, le mot clé en couleur d'accent (jaune).
- Zone sûre TikTok (1080x1920) : rien sous y = 1500 (légende et boutons du bas), rien à droite de x = 900 (boutons j'aime / commentaires / partage), rien au-dessus de y = 220. Sous-titres centrés vers y = 1150.

## Musique et bruitages (ligne B, monteur) : licences
- Musique de fond légère en continu, environ 18 dB sous la voix (mesurée en LUFS par ffmpeg), volume final normalisé à -14 LUFS (crête -1,5 dB). Fichiers : `outils/stick-stage/public/music/` (room pour la comédie, resolve pour les leçons, mystery pour le reste) : **CC0-1.0**, synthétisés par code par l'auteur de stick-stage (`scripts/music-gen.ts`, catalogue `src/data/music.json`).
- Bruitages aux moments forts (pop, coup de bureau = thud, ding, rimshot, record-scratch, crickets, register, click, door-knock, buzzer) : catalogue de stick-stage `public/sfx/` : **CC0-1.0**, synthétisés par code (`scripts/sfx-gen.ts`, catalogue `src/data/sfx.json`).
- Sonnerie de téléphone : générée par notre code (`agents/monteur.py`, fonction `sonnerie`, sinusoïdes) : aucun droit tiers.
- Jamais de musique protégée (morceau du commerce, son « tendance » TikTok) ni de son téléchargé sans licence CC0 notée ici.

## Contenu interdit (toutes lignes)
- Promesse fausse, chiffre ou témoignage inventé, contenu copié, données personnelles, ville ou lieu sur la ligne B.

## Nettoyage
- Supprimé après `nettoyage_jours` jours (14 par défaut, réglable dans la config) : `.mp4` et intermédiaires (son, images, sous-titres de rendu) dans `a-valider\`, `publiees\`, `travail\` et `outils\stickfigure-pipeline-v2\output\`. Une ligne dans `journal-videos.csv` avant chaque suppression.
- Jamais supprimé : ce fichier, `hooks.md`, `README.md`, la config, `agents\`, `scripts\`, les notes de veille de moins de 30 jours, les vidéos listées dans `videos_protegees`. Le nettoyage n'écrit que dans `Videos\`.
