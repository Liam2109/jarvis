# Ordre des pages premium (1er novembre 2026)

## Source des chiffres
`docs\liste-appels-2026-11-02.md` n'existe pas encore (la liste du jour n'est pas écrite). Chiffres calculés à partir de :
- `prospection-trouves.csv` : fiches « sans site, téléphone » ou « téléphone seulement », en zone (`agents\zone.py`) ;
- `suivi-prospects.csv` : statut « à contacter », avec téléphone, ville en zone.
Une même entreprise peut être dans les deux fichiers : les totaux sont donc un maximum, pas un compte exact.

| Rang | Métier | trouves (sans site, tél.) | suivi (à contacter, tél.) | Total max | Page |
|---|---|---|---|---|---|
| — | restaurant | 57 | 13 | 70 | existe déjà : sautée |
| — | coiffeur | 27 | 3 | 30 | existe déjà : sautée |
| 1 | boulangerie | 43 | 6 | 49 | **faite** (v1 du 1er nov.) |
| 2 | garage automobile | 21 | 4 | 25 | **faite** (v1 du 1er nov.) |
| 3 | fleuriste | 11 | 0 | 11 | **faite** |
| 4 | électricien | 0 | 4 | 4 | **faite** |
| 5 | plombier (dont chauffagiste) | 0 | 4 | 4 | **faite** |
| 6 | couvreur | 0 | 1 | 1 | à faire |
| 7 | maçon | 0 | 1 | 1 | à faire |
| 8 | peintre | 0 | 0 | 0 | à faire (aucun numéro pour l'instant) |

Égalité électricien / plombier à 4 : l'électricien d'abord (ordre voulu par Liam).

## Pages faites

### 1. Boulangerie — famille « Éditorial papier », note 8/10
- Dossier : `sites\premium-boulangerie\` (ouvrir `index.html`). Rien n'est déployé ; `liens-metiers.json` n'est pas touché.
- Style : éditorial papier (filets 1 px, sections numérotées, flèche qui glisse), angles 2 px, Young Serif + Hanken Grotesk.
- Couleurs : fond farine gris-vert (pas de crème), encre bleu nuit, bleu du tablier rayé uniquement sur l'appel.
- Concept d'interface tiré du métier : **la règle des fournées**, une règle graduée de 5 h à 19 h ; on glisse l'heure, la liste montre ce qui est sorti du four, ce qui est au comptoir et ce qui vient, et la photo change. Horaires d'exemple, signalés.
- Appel : 52 px (48 px dans l'en-tête), barre Appeler / Itinéraire collée sur téléphone seulement, mention « exemple, pas votre site », noindex.
- Captures : `sites\premium-boulangerie\captures\` (`mobile-390-haut.png`, `mobile-390-page.png`, `pc-1280-haut.png`, `pc-1280-page.png`, `controle.json`).
- Contrôles : aucun débordement mobile, aucune erreur console, 3 secondes (métier, ville, appel visibles en haut), test du remplacement (la règle des fournées ne va sur aucun autre métier), signes IA : 0 sur 14.
- Lighthouse mobile (local, 1er nov.) : performance 98, accessibilité 100, bonnes pratiques 100, SEO 63 (uniquement à cause du `noindex` voulu). Corrigé : contraste des heures « plus tard » et favicon.
- Références : Refero n'a aucun style de boulangerie ; 2 références ouvertes, 4 seulement citées (voir `sites\premium-boulangerie\REFERENCES.md`). À compléter avant déploiement.
- Limites : photos libres génériques (pas celles du commerce).

### 2. Garage — famille « Précision sombre », note 8/10
- Dossier : `sites\premium-garage\index.html`. Rien n'est déployé ; `liens-metiers.json` n'est pas touché.
- Style : graphite (pas noir pur), paliers de teinte à la place des ombres, filets 1 px à 11 %, chiffres tabulaires, angles 6 px, Barlow Condensed + Manrope. Accent = rouge d'étrier de frein peint (photo du dossier), réservé à l'appel.
- Concept tiré du métier : **la demande de réparation à composer** : on coche ce que la voiture a (voyant, freins, vidange, pneus, moteur, contrôle technique) ; le ticket à droite liste la demande, change de photo et donne la phrase à dire au téléphone. Lueur qui suit le curseur sur les cases (cliquables, pointeur précis seulement).
- Appel : 52 px (48 px en en-tête), barre Appeler / Itinéraire sur téléphone seulement, « exemple, pas votre site », noindex.
- Captures : `sites\premium-garage\captures\` (`mobile-390-*.png`, `pc-1280-*.png`, dont `-interaction.png` avec deux cases cochées).
- Lighthouse mobile local : performance 98, accessibilité 100, bonnes pratiques 100, SEO 63 (`noindex` voulu). Aucun débordement, aucune erreur console.
- Test du remplacement : le ticket « demande de réparation » ne va sur aucun autre métier. Signes IA : 0 à 1 sur 14 (lueur curseur, admise sur éléments cliquables).
- Limites : références Refero non refaites pour ce métier ; photos libres génériques.

### 3. Fleuriste — famille « Mat tactile », note 8/10
- Dossier : `sites\premium-fleuriste\`. Angles 12 px, Bricolage Grotesque + Figtree. Fond turquoise pâle des pots de l'étal, vert bouteille, rose pivoine réservé à l'appel. Boutons pleins à ombre interne qui s'enfoncent.
- Concept : **le calendrier du seau** : douze mois en étiquettes ; on choisit un mois, la liste de fleurs de saison et la photo changent (saisons générales en France, « selon les arrivages »). Hero en bande de photo étroite avec carte qui la chevauche.
- Lighthouse mobile local (2 nov., polices préchargées, image différée) : performance 99, accessibilité 100, bonnes pratiques 100, SEO 63 (`noindex`). Captures : `sites\premium-fleuriste\captures\`.
- Limites : photos d'illustration (les mois sans photo exacte utilisent des photos de l'étal) .

### 4. Plombier — famille « Atelier / plan », note 8/10
- Dossier : `sites\premium-plombier\`. Angles 0, capitales mono (IBM Plex Mono), Unbounded + Figtree, grille en filets, remplissage qui monte au survol. Papier de plan gris, encre bleu nuit, cuivre d'un tube réservé à l'appel.
- Concept : **le schéma de la maison** : plan en traits avec cinq points numérotés (chaudière, radiateurs, robinet, évacuation, WC) ; chaque point donne le signe, ce qu'on vérifie, ce qu'on fait, avec photo. Aucun prix ni délai inventé.
- Lighthouse mobile local (2 nov., polices préchargées, image de héros mobile) : performance 97, accessibilité 100, bonnes pratiques 100, SEO 63 (`noindex`). Captures : `sites\premium-plombier\captures\`.
- Polices : IBM Plex Mono servie depuis `polices\` (licence OFL notée dans `CREDITS.json`), aucune requête externe. Limite : deux numéros du schéma touchent une étiquette.

### 5. Électricien — famille « Halo », note 8/10
- Dossier : `sites\premium-electricien\`. Angles 4 px, Fraunces + Barlow. Plâtre gris, noir, jaune du fil de terre réservé à l'appel ; halo conique au survol et au focus, effet magnétique (souris seulement, 6 px au plus).
- Concept : **l'interrupteur à manette** : on bascule la manette (bouton `switch`, au clavier aussi), la photo passe d'un mur ouvert à un couloir éclairé. Les deux photos sont des illustrations libres, légendées comme telles : ce n'est pas le même chantier.
- Lighthouse mobile local : performance 98, accessibilité 100, bonnes pratiques 100, SEO 63 (`noindex`). Captures : `sites\premium-electricien\captures\`.
- Limites : mobile, l'interrupteur est sous la première vue.

## Reprise du haut de page (2 novembre 2026, v2)
Demande de Liam : l'interaction signature visible dès le premier écran, une seule séquence d'entrée, un traitement de photo plus fort ou une 3D légère. Mêmes familles de style, rien n'est déployé. Captures dans `sites\premium-<métier>\captures\` (`pc-1280-haut.png`, `mobile-390-haut.png`, `*-interaction.png`, images de la séquence `seq-300/800/1400/3200.png`, version mouvement réduit `reduit-900.png`).

| Page | Interaction dès le 1er écran | Séquence d'entrée (une seule) | Photo / 3D légère | Note | Lighthouse mobile |
|---|---|---|---|---|---|
| boulangerie | règle des heures et photo du four | titre ligne à ligne, rideau du four, règle qui se dessine, aiguille de 5 h à 8 h | teinte, lueur, grain, inclinaison 3D à la souris | 8/10 | 95 / 100 / 100 |
| garage | six cases + demande + appel, fond qui change avec la case | titre, cases une à une, projecteur qui balaie l'atelier | photo étalonnée, projecteur qui suit le pointeur, trame | 8/10 | 91 / 100 / 100 |
| fleuriste | douze mois suspendus sous la bande, fleurs du mois | rideau, mois qui tombent, cartes qui montent, pétales | étalonnage saturé, lueur, grain, pétales en rotation 3D | 8/10 | 95 / 100 / 100 |
| plombier | plan de la maison à 5 points, fiche du point | balayage de plan, points qui tombent, gouttes dans les tuyaux | photo en calque d'impression sous le trait | 8/10 | 99 / 100 / 100 |
| électricien | manette + couloir éteint | arrivée dans le noir, la manette bascule seule | nuit, halo de l'applique, grain | 8/10 | 98 / 100 / 100 |

Vérifié sur les cinq : appel 48 px au moins, barre d'appel mobile seulement, aucun débordement, aucune erreur console, mouvement réduit (rien de caché, aucune animation).
Limites assumées : la 3D reste légère (inclinaison, rotations CSS), pas de modèle 3D comme sur Le Velours ni le coiffeur v3 ; le garage reste à 91 en performance (7 photos dans le héros).

## Refonte en pages longues (2 novembre 2026, décision de Liam)
Règles : `sites\moteur\REGLES-STYLE-SITES.md` sections 0 et 6, skill `site-local-page-longue` (créé le 2/11, il n'existait pas). Ordre : garage, boulangerie, plombier, électricien, fleuriste.

### Garage — page longue v4 (corrigée après le retour de Liam du 2/11) : prête, non déployée
- Dossier : `sites\premium-garage\` (`index.html`, `garage3d.js`, `vendor	hree.module.min.js` r170). Fiche métier : `sites\moteur\metiers\garage.md`.
- Corrections : titres d'information au vouvoiement (plus aucune question familière) ; défilement PC 9,4 hauteurs d'écran (mesuré 7 542 px à 800 px), 2 écrans épinglés de 78 % et 68 % ; écran 6 « pièces et matériel » ajouté ; écran 7 contrôle technique développé (à préparer avec cases, schéma de véhicule à 6 points, contre-visite) ; écran 8 refait en vraie clôture (numéro, plan d'accès, horaires, formulaire de rappel, engagements, pied de page).
- 3D : disque en acier brossé (stries concentriques), étrier avec pistons, nervures, vis, flexible ; serrage au défilement.
- Mesures : 1 089 mots ; Lighthouse mobile performance 96-97, accessibilité 100, bonnes pratiques 100, LCP 2,0 s, CLS 0 ; aucun débordement, aucune erreur console ; appels 68 et 52 px ; mouvement réduit : rien de caché, aucune animation.
- Captures : `sites\premium-garage\captures\` : `entree-300/800/1400/3200.png`, `defil-01..13.png`, `pc-1280-page.png` (mouvement réduit), `mobile-390-haut.png`, `mobile-390-page-1..3.png`.
- Notes : grille notation-wow 9/10 ; futurisme et animation 8/10 ; rédaction 8/10 ; valeur perçue 8/10.
- Limites : photos libres génériques ; 3D testée seulement en WebGL logiciel (pas sur carte graphique réelle) ; la 3D n'est pas dans la mesure Lighthouse (mobile).

## Suivi pour Liam
| Métier | Nombre de numéros | Page prête | Lien après déploiement |
|---|---|---|---|
| boulangerie | 49 | oui (local) | à venir, après ton accord |
| garage automobile | 25 | oui (page longue v3, local) | à venir, après ton accord |
| fleuriste | 11 | oui (local) | à venir, après ton accord |
| électricien | 4 | oui (local) | à venir, après ton accord |
| plombier | 4 | oui (local) | à venir, après ton accord |
| couvreur | 1 | non | à venir |
| maçon | 1 | non | à venir |
| peintre | 0 | non | à venir |

### Boulangerie v4 (2 nov. 2026, page longue)
- 8 ecrans, 3D four et pain (PC), PC ~9,2 hauteurs, 1076 mots. Lighthouse mobile 95 / 100 / 100 / SEO 63 (noindex voulu). Captures dans sites\premium-boulangerie\captures\ (defil-*, entree-*, mobile-390-page-1..3, pc-1280-page). Rien deploye.
