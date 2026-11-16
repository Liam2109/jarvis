# SKILL-VIDEOS — règles de l'équipe Vidéos TikTok (16/11/2026)

Relu par CHAQUE agent vidéo avant chaque exécution (`commun.regles()` : fichier absent ou sans les sections ci-dessous = l'agent refuse de tourner).
Les sections « Règles pour Qwen » et « Grille des accroches » sont injectées telles quelles dans les consignes de Qwen. Le code vérifie ensuite chaque règle (garde-fous codés) : une règle écrite ici ne suffit jamais seule.

## Équipe (dans l'ordre d'un passage)
1. **Veille** (`agents/veille.py`, 04:30) : recherche web gratuite (flux RSS Google Actualités, jamais TikTok) de ce qui marche : stickman, motion design, formats courts ; note du jour dans `veille\`, formules d'accroche repérées ajoutées à `hooks.md` (bibliothèque = modèle versionné `hooks-base.md` + formules repérées, réécrite chaque jour).
2. **Scripts** (`agents/scripts.py`, 05:00) : Qwen écrit le script de chaque passage (une idée, phrases courtes, légende).
3. **Marketing** (`agents/marketing.py`, 05:30) : réécrit accroche, rythme et sous-titres ; 3 accroches notées, la meilleure gardée et inscrite dans `journal-videos.csv`.
4. **Création** (`agents/creation.py`, 06:00, 14:00, 22:00) : fabrique la vidéo (stickfigure-pipeline-v2, voix edge-tts, ffmpeg) dans `a-valider\`.
5. **Publication** (`agents/publication.py`, 06:20, 14:20, 22:20) : publie sur TikTok seulement les lignes que Liam a ouvertes par « go publier ».
6. **Nettoyage** (`agents/nettoyage.ps1`, 03:30) : supprime les vidéos et fichiers intermédiaires de plus de `nettoyage_jours` jours, après une ligne dans `journal-videos.csv`.

## Gratuit, local, sans token Claude
- Texte : Qwen local via Ollama (`modele`). Voix : edge-tts (gratuite). Montage : stickfigure-pipeline-v2 + ffmpeg. Navigateur : Playwright sur le navigateur déjà installé.
- Aucun service payant, aucune carte bancaire, aucun appel à Claude ni à une API payante.

## Rythme et format
- 3 vidéos par jour, aux heures de `passages` (06:00, 14:00, 22:00 : ne pas les changer sans Liam). Ligne de chaque passage : `series_par_passage`.
- Vertical 9:16 (1080x1920), style bonhomme bâton (stickman) sur fond sombre.
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
- **A — stickman divertissement / explications**, compte TikTok actuel. Ton : vivant, simple, vouvoiement, un bonhomme bâton qui explique une chose concrète du web pour les artisans et commerçants. Fin : planning de 15 minutes de Liam (lien lu dans `B2B\docs\SCRIPT-APPEL-SID.md`, jamais recopié).
- **B — recrutement d'appelants (call callers)** pour vendre des sites web, compte TikTok séparé. Ton : direct, tutoiement, « je te le dis cash ». Message : Liam cherche des call callers pour vendre des sites web ; on appelle depuis chez soi, on décroche des rendez-vous, on touche une commission sur chaque vente, pas de salaire fixe, liste et script fournis, postuler via le lien en bio (formulaire Google).
  - Ne cite ni ville ni lieu.
  - Taux de commission : champ `lignes.B.taux_commission`, laissé vide ; Liam le renseigne. Tant qu'il est vide, la vidéo dit seulement « à la commission ».
  - INTERDIT : promettre ou chiffrer un revenu, citer un témoignage ou un nombre de ventes.

## Règles pour Qwen
- Une seule idée par vidéo. Phrases courtes, à l'oral, naturelles, comme on parle. Aucune phrase molle (« dans cette vidéo », « aujourd'hui on va voir », « il est important de », « n'hésitez pas », « tout simplement », « découvrez »).
- Aucun chiffre ni nombre, même en lettres (les seuls chiffres sont ajoutés par le code). Aucune promesse de résultat, de clients, de gain ou de revenu. Aucun témoignage, aucun client réel ou inventé. Aucun contenu copié : les titres de la veille donnent des idées de format, jamais des phrases à reprendre.
- Pas de superlatif, pas de « garanti », « facile », « secret », « incroyable », « meilleur ». Pas d'appel à s'abonner, liker ou commenter. Pas de lien.
- Seulement le texte lu par la voix : jamais de caméra, de plan, de scène, de narrateur.
- Ligne B : jamais de ville, de région ni de lieu ; jamais de montant, de pourcentage ni de nombre de ventes.

## Grille des accroches
L'accroche est la première phrase : lue en 2 secondes au plus, elle crée tension ou curiosité. Note sur 10, calculée par le code (`marketing.noter_accroche`) :
- **+3** forme qui accroche : question, contradiction (« pourtant », « faux », « arrête », « personne ne »), erreur courante (« erreur », « vous perdez », « tu rates »), ou résultat montré avant l'explication.
- **+3** courte : 6 mots ou moins (+3), 7 à 8 mots (+2), 9 à 10 mots (+1), plus de 10 mots (0 : plus de 2 secondes).
- **+2** parle directement au public de la ligne (« vous » pour A, « tu » pour B).
- **+1** concrète : nomme une chose qu'on voit (téléphone, horaires, bouton, appel, liste, rendez-vous, client, page…).
- **+1** neuve : aucune des 20 dernières accroches de `journal-videos.csv` n'a les mêmes mots.
- **Éliminée (0)** : chiffre, promesse, mot interdit ou phrase molle. Ouverture molle (« Bonjour », « Aujourd'hui », « Découvrez », « Dans cette vidéo ») : −3.
Égalité : la plus courte gagne. Les 3 accroches, leur note et la gagnante sont écrites dans `journal-videos.csv`.

## Rétention
- 20 à 35 secondes (fin comprise) ; un changement visuel toutes les 2 à 3 secondes (une phrase = une image, 4 à 11 mots par phrase) ; fin en boucle (la dernière phrase renvoie à l'accroche) ou question qui relance.

## Sous-titres
- Mot par mot, synchronisés avec la voix : temps des mots donnés par edge-tts (déjà retenu, gratuit), recalés sur la durée réelle de chaque phrase ; à défaut, répartis selon la longueur des mots dans la phrase.
- Grosse police grasse (Arial Black / Arial gras), blanc sur contour noir épais, 2 à 4 mots à l'écran, le mot clé en couleur d'accent (jaune).
- Zone sûre TikTok (1080x1920) : rien sous y = 1500 (légende et boutons du bas), rien à droite de x = 900 (boutons j'aime / commentaires / partage), rien au-dessus de y = 220. Sous-titres centrés vers y = 1150.

## Contenu interdit (toutes lignes)
- Promesse fausse, chiffre ou témoignage inventé, contenu copié, données personnelles, ville ou lieu sur la ligne B.

## Nettoyage
- Supprimé après `nettoyage_jours` jours (14 par défaut, réglable dans la config) : `.mp4` et intermédiaires (son, images, sous-titres de rendu) dans `a-valider\`, `publiees\`, `travail\` et `outils\stickfigure-pipeline-v2\output\`. Une ligne dans `journal-videos.csv` avant chaque suppression.
- Jamais supprimé : ce fichier, `hooks.md`, `README.md`, la config, `agents\`, `scripts\`, les notes de veille de moins de 30 jours, les vidéos listées dans `videos_protegees`. Le nettoyage n'écrit que dans `Videos\`.
