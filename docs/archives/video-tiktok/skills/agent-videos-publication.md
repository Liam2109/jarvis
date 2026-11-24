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

## Rôle
Publier sur TikTok les vidéos d'une ligne que Liam a ouverte par « go publier », 3 par jour et par compte, étiquette IA activée. Limites : VERROUILLÉ (contrat `inactif`) tant que Liam n'a pas donné son go et ajouté l'agent à `agents_actifs` ; aucun mot de passe, aucun contournement.

## Ordres pas à pas (lus dans le script)
1. Refus avant toute ouverture : `Videos\STOP` ou `B2B\STOP`, ligne arrêtée aujourd'hui, `go_publier` pas à true, aucun essai réussi, 3 publications déjà faites sur le compte, hors des heures prévues (+/- 45 min), passage déjà publié.
2. Prend la plus ancienne vidéo complète de la ligne (mp4 + txt avec « Contenu généré par IA. » + json `contenu_ia: true`) ; la légende passe par la garde du harness.
3. Verrou : jamais deux publications en même temps. Ouvre le profil persistant de la ligne, va sur la page de dépôt de TikTok Studio, délais aléatoires entre les gestes.
4. Après chaque geste : page contrôlée ; captcha, connexion ou vérification demandée, interface inattendue, échec = ARRÊT de la ligne pour la journée, alerte Discord, ligne CSV.
5. Dépose la vidéo, colle la légende, coche la case TikTok « contenu généré par IA » et la VÉRIFIE cochée juste avant de cliquer sur Publier (règle du 17/11/2026 : plus de texte IA à l'image) ; essai (dry-run) : s'arrête devant Publier et dit où se trouve la case (section, position à l'écran) ; sinon clique sur Publier et lit la confirmation.
6. Déplace la vidéo vers `Videos\publiees`, une ligne dans `journal-videos.csv` (date, compte, hook, résultat), dans le journal et dans Discord.

## Entrées et sorties (place dans la chaîne)
- **Reçoit de :** **Création** / **Monteur** (`Videos/a-valider/*.mp4` + `.txt` + `.json` avec `contenu_ia: true`) et le **ton OK de Liam** (`lignes.<X>.go_publier: true`, écrit par Liam seulement).
- **Produit :** la vidéo publiée puis déplacée dans `Videos/publiees` ; une ligne dans `journal-videos.csv` ; alerte Discord en cas d'anomalie.
- **Passe à :** **Nettoyage** (03:30) supprime plus tard les vidéos publiées trop vieilles.
- Chaîne vidéo : Veille → Scripts → Marketing → Création (→ Monteur, ligne B) → ton OK de Liam (« go publier », une fois par ligne) → Publication → Nettoyage. Fiche : `docs/agents/⛓️ Chaîne vidéo.md`.

## Ce qu'il ne fait jamais
- Taper ou stocker un mot de passe, un code ou une clé ; contourner un captcha ou réessayer après une anomalie.
- Liker, s'abonner, commenter, envoyer un message ; publier sans étiquette IA, plus de 3 fois par jour et par compte, ou sur une ligne sans go.
- Écrire le go à la place de Liam.

## Cas d'erreur
- Ligne sans go, essai jamais réussi, plafond atteint, hors horaire, `Videos\STOP` ou `B2B\STOP` : rien publié (aucune ouverture du navigateur).
- Légende bloquée par la garde du harness : rien publié, code 4.
- Captcha, connexion demandée, interface inattendue : ARRÊT de la ligne pour la journée, alerte Discord, code 1, trace `ok: false`.
- Case « contenu généré par IA » introuvable ou non cochée (`EtiquetteIA`) : rien publié, ARRÊT de la ligne pour la journée, alerte Discord, vidéo mise à part dans `Videos/a-part` (+ `<vidéo>.motif.json`) ; en essai, la vidéo reste dans `a-valider`.
- Machine non active ou `SKILL-VIDEOS.md` incomplet : refus code 3.
- Toute erreur laisse une trace `ok: false`, lue par le surveillant si l'agent est dans `agents_actifs`.

## Règles qu'il suit
- Il relit `Videos/SKILL-VIDEOS.md` avant chaque exécution (`C.exiger_regles` : absent ou incomplet = refus, code 3), sections « Publication : un seul « go publier » par ligne ».
- Harness : contrat `B2B/harness/contrats/videos-publication.json` (`peut_engager: false`) ; garde complète du harness sur la légende (`garde_harness` : STOP, secret, phrase interdite) ; une trace par exécution (`C.lancer` : commande, durée, ok, erreur ; rien pour `etat` ni `--a-blanc`) dans `B2B/logs/agents/videos-publication/AAAA-MM-JJ.jsonl`.
- Ce qui engage Liam (publier, envoyer, encaisser, signer) n'est jamais fait sans son accord ; la publication reste verrouillée par ligne jusqu'à son « go publier ».
- Règle d'or : pas de preuve = pas de fait. « Il a tourné » se prouve par la trace du jour (`ok: true`) et le fichier produit ; « c'est corrigé » par `python tests\agents\test_videos.py` puis `tests\b2b-rapide.ps1` en vert, sortie montrée.

## Vérifier
- `python Videos\agents\publication.py etat` ; `python Videos\agents\publication.py publier --a-blanc` (rien n'est ouvert).
- Test : `python tests\agents\test_videos.py` (TikTok remplacé par un bouchon : fermé sans go, essai obligatoire, captcha, plafond, STOP, verrou, CSV).
- Les sélecteurs de TikTok Studio n'ont pas pu être essayés sans compte connecté : l'essai à blanc devant Liam le vérifie.
