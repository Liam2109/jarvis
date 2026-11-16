---
name: agent-videos-publication
description: Fiche de rôle de l'agent Publication TikTok (équipe Vidéos TikTok, FERMÉ par ligne jusqu'au « go publier » de Liam) — après le go d'une ligne (A stickman, B recrutement), publie ses vidéos de Videos\a-valider sur le compte de la ligne avec Playwright et un profil persistant où Liam s'est connecté lui-même, étiquette IA activée, 3 par jour et par compte ; essai obligatoire ; anomalie = arrêt et alerte Discord. À utiliser pour vérifier ou corriger Videos\agents\publication.py (publier, connexion, etat) ; ne jamais ouvrir une ligne sans l'ordre de Liam.
---

# Agent Publication TikTok — un seul « go publier » par ligne, puis automatique

**Responsable :** Jarvis (CEO). **Script :** `Videos/agents/publication.py`. **Contrat :** `B2B/harness/contrats/videos-publication.json` (statut `inactif` tant qu'aucune ligne n'est ouverte).
**Tâche serveur prévue :** `publier` à 06:20, 14:20 et 22:20 (ligne du passage : `series_par_passage`), seulement si `videos-publication` est dans `agents_actifs`.
**Règles :** `Videos/SKILL-VIDEOS.md`, relu avant chaque exécution (section « Publication »).

## Ouvrir une ligne (Liam seulement, une fois par ligne)
1. Liam regarde la première vidéo de la ligne dans `Videos\a-valider` et dit « go publier ».
2. `pip install --user playwright` (aucun navigateur téléchargé : Edge du serveur, `navigateur: msedge`).
3. `python Videos\agents\publication.py connexion --ligne A` : la fenêtre du profil de la ligne s'ouvre ; Liam se connecte LUI-MÊME au compte de la ligne puis ferme la fenêtre.
4. `python Videos\agents\publication.py publier --essai --ligne A` : va jusqu'au bouton Publier sans cliquer (obligatoire avant le premier envoi).
5. Dans la config locale de `Videos` (machine) : `"lignes": {"A": {"go_publier": true}}` ; `videos-publication` dans `agents_actifs` ; statut du contrat à `actif`.

## Ordres pas à pas (lus dans le script)
1. Refus avant toute ouverture : `Videos\STOP` ou `B2B\STOP`, ligne arrêtée aujourd'hui, `go_publier` pas à true, aucun essai réussi, 3 publications déjà faites sur le compte, hors des heures prévues (+/- 45 min), passage déjà publié.
2. Prend la plus ancienne vidéo complète de la ligne (mp4 + txt avec « Contenu généré par IA. » + json `contenu_ia: true`) ; la légende passe par la garde du harness.
3. Verrou : jamais deux publications en même temps. Ouvre le profil persistant de la ligne, va sur la page de dépôt de TikTok Studio, délais aléatoires entre les gestes.
4. Après chaque geste : page contrôlée ; captcha, connexion ou vérification demandée, interface inattendue, échec = ARRÊT de la ligne pour la journée, alerte Discord, ligne CSV.
5. Dépose la vidéo, colle la légende, active l'étiquette « contenu généré par IA » (introuvable = rien publié), clique sur Publier (sauf essai), lit la confirmation.
6. Déplace la vidéo vers `Videos\publiees`, une ligne dans `journal-videos.csv` (date, compte, hook, résultat), dans le journal et dans Discord.

## Ce qu'il ne fait jamais
- Taper ou stocker un mot de passe, un code ou une clé ; contourner un captcha ou réessayer après une anomalie.
- Liker, s'abonner, commenter, envoyer un message ; publier sans étiquette IA, plus de 3 fois par jour et par compte, ou sur une ligne sans go.
- Écrire le go à la place de Liam.

## Vérifier
- `python Videos\agents\publication.py etat` ; `python Videos\agents\publication.py publier --a-blanc` (rien n'est ouvert).
- Test : `python tests\agents\test_videos.py` (TikTok remplacé par un bouchon : fermé sans go, essai obligatoire, captcha, plafond, STOP, verrou, CSV).
- Les sélecteurs de TikTok Studio n'ont pas pu être essayés sans compte connecté : l'essai à blanc devant Liam le vérifie.
