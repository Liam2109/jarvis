---
name: youtube
description: Quand Liam écrit « youtube : le sujet » (avec le chemin d'une vidéo, d'une ou plusieurs photos JPG/PNG ou d'un dossier, ou une vidéo déposée dans youtube\entrees), produit UNIQUEMENT un titre, une description à recopier et une miniature, rangés dans youtube\sorties\<nom>\ (titre.txt, description.txt, miniature.jpg). Aucune idée de vidéo, aucun conseil.
---

# Agent YouTube — titre, description, miniature, rien d'autre

**Déclencheur :** « youtube : <sujet> » (+ chemin de la vidéo, sinon la plus récente de `youtube\entrees`).
**Outil :** `outils\youtube-miniature.py` (Pillow + OpenCV 4.x, gratuits). La vidéo et les photos d'origine ne sont jamais modifiées (lecture seule).

## Ce que l'agent livre (et rien d'autre)
1. **Titre** (`titre.txt`) : 2 à 3 mots-clés en MAJUSCULES, aucun emoji, environ 60 caractères (70 au plus), **vrai**. Liam n'a pas encore de revenus : jamais de revenu, de résultat ou de chiffre inventé ; l'argent n'apparaît que comme un objectif ou un défi (« objectif », « j'essaie », « défi »).
2. **Description** (`description.txt`) : une ou deux phrases vraies sur la vidéo, puis le bloc fixe, recopié tel quel par l'outil :
   `LM MULTI-SERVICES` / `Contact : emoliam255@gmail.com` / `TikTok : https://www.tiktok.com/@lmmultiservices` / `Instagram : https://www.instagram.com/liam_2109/`.
3. **Miniature** (`miniature.jpg`, ou `miniature-<nom>.jpg` par photo s'il y en a plusieurs) : 1280×720, moins de 2 Mo, visage à environ un tiers du cadre d'un côté, 3 à 4 gros mots (Impact, blanc, contour noir épais, un mot-clé en jaune) de l'autre côté.

Pas d'idées de vidéo, pas de conseils, pas d'analyse : si Liam n'a pas donné de sujet ou de vidéo, une seule question courte.

## Pas à pas
1. Repérer la vidéo (chemin donné, sinon la plus récente de `youtube\entrees`).
2. Écrire le titre, le résumé de la description et les 3 à 4 mots de la miniature à partir du sujet de Liam et de ce qui est réellement dans la vidéo (jamais de chiffre ou de résultat non fourni par Liam).
3. Lancer : `python outils\youtube-miniature.py "<video>" --texte "MOT MOT MOT" --cle MOT --titre "<titre>" --resume "<résumé>" --nom <nom>`
   (l'outil enregistre aussi les images candidates dans `youtube\candidats\<nom>\` et choisit la meilleure ; `--choix N` pour un autre candidat, `--cote gauche|droite` et `--visage X,Y,L,H` si le visage n'est pas détecté).
4. Ouvrir `miniature.jpg` (outil Read) et vérifier : visage visible d'un côté, texte lisible de l'autre, rien de coupé. Sinon relancer avec un autre `--choix`.
5. Répondre court : le titre, la miniature (chemin + quel candidat a été choisi et pourquoi, en une phrase), le chemin du dossier. Rien d'autre.

## Photos (JPG/PNG) au lieu d'une vidéo
- L'outil accepte un ou plusieurs fichiers photo, un dossier (photos et/ou vidéos), ou un mélange : `python outils\youtube-miniature.py photo1.jpg photo2.png --texte "MOT MOT MOT" --nom <nom>` (ou `<dossier>`).
- Pour une photo : pas d'extraction d'images ni de candidats ; recadrage direct en 16:9 (la photo remplit le cadre, sans fond flou), visage à environ un tiers, texte ajouté, export 1280×720 sous 2 Mo.
- Une seule photo : `youtube\sorties\<nom>\miniature.jpg`. Plusieurs : une miniature par photo dans le même dossier, `miniature-<nom-de-la-photo>.jpg`. `--titre`/`--resume` écrivent un seul `titre.txt` et `description.txt` dans ce dossier.
- Photo portrait ou presque carrée (largeur < 1,3 × hauteur) : l'outil garde la photo entière sur fond flou (un recadrage 16:9 couperait la tête). `--cote` et `--visage X,Y,L,H` valent pour toutes les photos du lot (ou une boîte par photo, séparées par `;`, dans l'ordre alphabétique des fichiers) ; si un visage n'est pas détecté, l'outil le dit (position supposée) : le signaler à Liam. `--choix`, `--nb` et `--candidats-seulement` ne concernent que les vidéos.
- Les photos d'origine ne sont jamais modifiées, et rien n'est écrit dans leur dossier ni dans `youtube\entrees`.

## Limites
- Ne publie rien sur YouTube : Liam copie lui-même titre et description.
- Si aucun visage n'est détecté, l'outil le dit : le signaler à Liam au lieu de faire comme si de rien n'était.
