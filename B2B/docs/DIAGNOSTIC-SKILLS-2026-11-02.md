# Diagnostic des skills site-local-* et de REGLES-STYLE-SITES.md (02/11/2026, soir)

Demande de Liam (19 h 39) : les pages récentes (plombier étape 1, boulangerie) sont « vraiment moches », il préférait l'ancienne version, et la cause vient des skills. Ce document donne : (1) le constat, (2) les contradictions entre skills, (3) pour chaque fichier, ses défauts puis son **texte complet corrigé**, (4) la procédure de comparaison obligatoire. **Aucun skill n'a été modifié.** Liam enregistre lui-même les textes de la partie 3.

Lecture faite : les 19 skills `site-local-*` (chaine-obligatoire, page-longue, rythme-ecrans, metier-plombier, metier-electricien, metier-garage, metier-boulangerie, animation-3d, direction-artistique, interface-signature, structure-variee, palette-signature, realisme-photos, signature-interaction, conversion, notation-wow, references, niveau-10000, futurisme-utile) et `sites\moteur\REGLES-STYLE-SITES.md`, en entier. Aucun n'a changé depuis ma lecture (dernières modifications : futurisme-utile et niveau-10000, 19 h 04).

---

## 1. Constat : pourquoi les skills produisent des pages laides

Trois références de Liam ont été ouvertes en vraie capture le 02/11/2026 à 19 h 50 (dossier `sites\refs\captures-2026-11-02\` : `linear-pc.png`, `raycast-pc.png`, `apple-pc.png`, plus les versions mobile). Ce que montrent ces captures, et pas seulement leur réputation :

| | Linear | Raycast | Apple (page Mac) | Plombier étape 1 |
|---|---|---|---|---|
| Éléments visibles dans le premier écran | environ 5 (titre, une phrase, menu, un petit bouton, une capture produit) | environ 5 (titre, une phrase, menu, un bouton, une image) | environ 6 (titre, bande de produits, menu, un lien) | une dizaine (relevé d'état, horloge, titre, texte, adresse, bouton, lien, menu bas, lien téléphone, rail, goutte, cadre de visée) |
| Couleurs d'accent | aucune dans le titre ; neutres | une seule teinte, dans l'image | aucune ; photos des produits | cuivre + bleu-vert + gris |
| Bouton d'appel à l'action | rectangle arrondi simple | rectangle simple, texte lisible | simple, pastille ou lien | forme à coins coupés, roue, voyant, lueur, aimant |
| Titre | très grand, serré, 2 lignes | très grand, centré, 2 lignes | très grand, 1 mot | très grand mais entouré d'étiquettes mono |
| Espace vide | beaucoup | beaucoup | énormément | peu : tout est rempli |
| Image | une capture du produit réel | une image forte | de vraies photos produit | vraie vidéo (bien), mais cachée par le voile et les calques |

**Ce qui fait leur qualité : un seul message par écran, un très grand titre, un seul visuel réel, beaucoup d'espace, des boutons ordinaires et nets.** Ce n'est pas la quantité d'effets.

**Les skills disent l'inverse.** Ils décrivent un style par une liste de caractéristiques à appliquer (« cockpit », « coins coupés », « voyants », « jauges », « halo conique », « lueur qui suit le curseur », « effet magnétique », « vanne qui tourne », « goutte guide »), ils exigent une animation par écran et un moment 3D, et ils font noter la page par Claude lui-même. Résultat : Claude empile les effets demandés, chacun étant conforme à une consigne, et l'ensemble est chargé, décoratif et « typique IA ». Aucun skill ne demande de regarder un vrai site à côté de la page.

### Les 5 problèmes principaux

1. **Accumulation obligatoire d'effets** (animation-3d « niveau d'ambition minimum », niveau-10000 « finitions d'agence », chaine-obligatoire « préférence du 02/11 prioritaire ») : une animation par écran, un écran épinglé, un moment 3D, un curseur, un aimant, un texte cinétique, tout cela *exigé*.
2. **Descriptions de style à la place de références** (futurisme-utile « cockpit », interface-signature « boutons en robinet, en vanne, en clé à molette », direction-artistique « parti pris en une phrase ») : un mot ne fixe pas un niveau de finition ; Claude invente des formes décoratives (roue de vanne, goutte, coins coupés).
3. **Boutons et cadres dessinés pour le métier** (interface-signature, futurisme-utile) : le bouton d'appel doit être « dessiné pour le métier », ce qui produit des objets bizarres au lieu d'un bouton net.
4. **Auto-notation par Claude** (notation-wow, niveau-10000 « note sur 10 de l'effet wow », REGLES §6.8 « quatre grilles ») : Claude s'est donné 8,4 et 8,5 sur des pages que Liam juge laides. Une note donnée par celui qui a produit la page n'a aucune valeur.
5. **Contradictions non arbitrées** (voir partie 2) : sobre et futuriste, une seule audace et une animation partout, pas de curseur personnalisé et curseur exigé… Claude choisit au cas par cas, donc au hasard, et la clause « la préférence du 02/11 l'emporte » donne systématiquement raison à l'effet.

---

## 2. Contradictions entre skills

| Sujet | Un skill dit | Un autre dit |
|---|---|---|
| Style | REGLES §1, direction-artistique : sobre, une seule audace par page | chaine-obligatoire, niveau-10000, animation-3d : futuriste, très animé, tout est prioritaire sur « toute consigne plus sage » |
| Curseur personnalisé | REGLES §1 : interdit (signe IA) | niveau-10000, animation-3d : exigé sur ordinateur |
| Compteurs | REGLES §1 : « compteurs qui montent depuis 0 » interdits | animation-3d : « chiffre ou jauge qui progresse » |
| Fondu des sections | REGLES §1 : interdit | page-longue : animation propre à chaque écran, « jamais un simple fondu » (donc effet lourd à chaque fois) |
| Lighthouse | signature-interaction : ≥ 95 | chaine, page-longue : ≥ 90 |
| Interaction signature | signature-interaction : une seule, dans les 2 premiers écrans | niveau-10000 : film en premier écran + animation à chaque écran + 3D |
| 3D | futurisme-utile : « rien de décoratif », sinon vidéo | metier-* : 3D de vanne, étrier, four, ampoule exigée dans le plan |
| Épinglage | rythme-ecrans : « pas de zone vide », 150 % max | animation-3d : section épinglée obligatoire |
| Bouton | REGLES §2 : « le plus visible, seul élément saturé » ; conversion : simple | interface-signature, futurisme-utile : bouton « signature » dessiné pour le métier avec lueur et aimant |
| Variété | structure-variee : 4 axes sur 6 différents à chaque métier | conversion : mêmes éléments clés à la même place |
| Notation | notation-wow : note sur 10, 8 minimum, 3 itérations | notation-wow : « Liam a noté 6/10 » : seule la note de Liam compte ; l'auto-notation n'a jamais correspondu à son jugement |
| Références | references : chercher de vraies références | références lues comme du texte (Refero illisible par l'outil de lecture) ; jamais de capture comparée |

**Arbitrage proposé :** la sobriété et la netteté l'emportent sur tout. Le futurisme se limite à la qualité (typographie, image, rythme), jamais à des éléments d'interface « technologiques ».

---

## 3. Fichier par fichier : problèmes, puis texte corrigé

Convention : chaque bloc « Texte corrigé » est le fichier complet à enregistrer (front-matter compris). Les noms de dossier sont inchangés, sauf deux renommages suggérés (marqués « renommage suggéré »).

### 3.1 `sites\moteur\REGLES-STYLE-SITES.md`

**Problèmes**
- §3 « sept familles » : chaque famille est une liste d'effets (« lueur qui suit le curseur », « halo conique », « texte qui défile », « verre », « immersif cinétique ») : le catalogue sert de menu d'effets.
- §4 « recettes » : encore des effets prêts à coller ; Claude les applique tous.
- §6 « pages longues et futuristes » : impose futuriste, une animation propre par écran, une 3D, 700 à 1 100 mots, quatre grilles de notation : accumulation et auto-notation.
- §1 interdit le curseur personnalisé et les compteurs, que niveau-10000 et animation-3d exigent.
- Aucune référence visuelle réelle, aucune comparaison de captures.

**Texte corrigé**

```markdown
# RÈGLES DE STYLE DES SITES (à lire AVANT toute création ou refonte de page)

Version corrigée du 02/11/2026. Décision de Liam : les pages récentes sont jugées laides. Principe unique : **sobre, net, grand.** Peu d'éléments, une très bonne typographie, de grands espaces, un seul accent, une vraie photo ou vidéo, des boutons simples, un mouvement discret. On part de vrais sites que Liam a choisis (liste dans `sites\refs\REFERENCES-LIAM.md`), pas d'une description.

## 0. Relecture et rapport
- Avant CHAQUE page (et après toute reprise), relire en entier ce fichier et le SKILL.md de chaque skill site-local, ainsi que `sites\refs\REFERENCES-LIAM.md`.
- Écrire en tête de la réponse une ligne « **Skills relus :** » avec la liste réelle. Un skill introuvable est signalé.
- Une fiche par métier `sites\moteur\metiers\<métier>.md`, relue à chaque modification.

## 1. Interdits
Signes « fait par IA » :
- ombres décalées pleines, bordures de 2-3 px, étiquettes inclinées ; badge au-dessus du titre ; un mot du titre en couleur ; titre centré par défaut ;
- grille de trois cartes à icône ; icônes génériques ; dégradé violet/bleu ; texte en dégradé ; Inter par défaut ;
- néomorphisme, « liquid glass », fond crème + serif + terracotta, noir + accent acide.

Habillages « technologiques » (ajoutés le 02/11/2026) :
- style cockpit, tableau de bord ou HUD : cadres de visée, coins coupés, voyants, jauges, relevés en police mono, rails, règles graduées décoratives ;
- lueurs, halos, reflets qui balayent un bouton, effet magnétique, curseur personnalisé ;
- boutons dessinés comme un objet du métier (vanne, clé, interrupteur, ciseaux, pain) ;
- orbes, gouttes ou avatars qui guident, texte cinétique, marquee ;
- scène 3D (voir §6) ;
- plus de **deux** effets de mouvement visibles à la fois.

Plus de 2 interdits sur une page = page refusée.

## 2. Base obligatoire
- Bouton d'appel : zone d'au moins 48 px, contraste texte 4,5:1, le plus visible de la page. Barre d'appel fixe en bas sur mobile (Appeler plein, Itinéraire en texte ou filet), seulement sur téléphone.
- Focus clavier visible, `prefers-reduced-motion` respecté (tout est visible, rien ne bouge), animer seulement `transform` et `opacity`.
- CSS + JS natif, moins de 100 Ko hors images, polices libres auto-hébergées WOFF2, images WebP/AVIF.
- Pas de faux avis, pas de chiffre inventé, mention « exemple, pas votre site » (petite étiquette dans l'en-tête et le pied), `noindex`.
- Lighthouse mobile ≥ 90, LCP < 2,5 s, CLS < 0,1, accessibilité 100.

## 3. Trois familles seulement (une par page)
1. **Clair éditorial** : fond blanc ou papier, texte encre, très grands titres, photos nettes. Boulangerie, fleuriste, coiffeur, restaurant.
2. **Sombre net** : fond quasi noir, texte clair, un accent, filets 1 px très discrets, aucune lueur. Garage, électricien, barbier.
3. **Photo plein cadre** : une photo ou vidéo réelle sur tout le premier écran, titre blanc très grand dessus, voile uniforme pour la lisibilité. Tous métiers.

Varier d'une page à l'autre : famille, paire de polices, accent. L'accent vient d'un objet réel du métier mais reste sobre (une seule teinte, pas de dégradé).

## 4. Composants (valeurs à respecter)
- **Bouton principal** : rectangle plein à angles de 6 px (ou 0 si famille éditoriale, jamais coins coupés), fond = accent, texte en police du site 16-17 px, graisse 600, pas de capitales mono, hauteur 52-56 px, padding horizontal 28 px. Survol : fond 8 % plus sombre, 150 ms. Focus : contour 3 px. Appui : décalage de 1 px. Une icône de téléphone de 20 px est permise, rien d'autre.
- **Bouton secondaire** : lien souligné ou bouton à filet 1 px, même hauteur et même rayon.
- **Navigation** : logo à gauche, 3 à 5 liens en texte, un seul bouton d'appel à droite, fond uni ou verre léger (une seule couche), pas de bandeau au-dessus.
- **Titres** : police de caractère (grotesque ou serif de qualité), 56 à 96 px sur ordinateur, 36 à 48 px sur mobile, interlettrage -1 à -3 %, interligne 1,0 à 1,1, trois lignes au plus.
- **Texte** : 17-18 px, interligne 1,6, 60 à 70 caractères par ligne, une seule graisse courante.
- **Espaces** : échelle de 8 px, sections avec 96 à 160 px de marge verticale sur ordinateur (64 à 96 sur mobile), largeur de contenu 1 120 à 1 200 px.
- **Formulaire** : champs de 52 px, bordure 1 px, étiquette au-dessus en 14 px (pas de mono), un seul bouton.
- **Carte** : iframe Google Maps chargée au clic, cadre de 1 px, mêmes angles que les boutons, bouton Itinéraire = bouton secondaire.

## 5. Mouvement discret (liste fermée)
Autorisé : (1) le titre du premier écran apparaît (opacité + 12 px, 600 ms) ; (2) un léger zoom lent de l'image ou de la vidéo du premier écran (6 % au plus) ; (3) les images et blocs apparaissent une fois au défilement (opacité + 16 px, 500 ms) ; (4) changement de couleur au survol d'un bouton ; (5) accordéons de la FAQ. Rien d'autre sans l'accord de Liam.

## 6. Photo, vidéo, 3D
- Le premier écran montre une vraie photo ou une vraie vidéo libre de droit (voir site-local-realisme-photos), d'un bon cadrage.
- **3D : interdite par défaut.** Elle n'est faite que si Liam la demande, avec de vrais modèles réalistes ; sinon photo ou vidéo.

## 7. Longueur
5 à 7 sections, 500 à 800 mots utiles, 6 à 9 hauteurs d'écran sur ordinateur. Aucun épinglage par défaut. Dernier écran : contact complet (bouton d'appel, adresse, carte au clic, horaires, formulaire court). L'avant-dernier apporte une information utile.

## 8. Contrôle obligatoire avant de montrer (voir site-local-chaine-obligatoire)
Comparer la page, en capture, à 2 ou 3 sites de `REFERENCES-LIAM.md`, côte à côte. Si la page est moins sobre ou moins nette, la refaire. La note finale est celle de Liam ; Claude ne se note pas sur 10.
```

### 3.2 `site-local-chaine-obligatoire`

**Problèmes**
- La « préférence de Liam du 02/11/2026 (prioritaire sur le reste) » remplace « sobre » par « une séquence d'entrée orchestrée, une animation par section, une interaction signature, un moment 3D » : c'est le moteur de l'accumulation.
- Elle impose 11 skills dans un ordre rigide, dont references (texte) et notation (auto) : beaucoup de procédure, aucune comparaison réelle.
- « Valeur perçue 1 500 € » comme critère : Claude l'achète avec des effets.
- Contrôles = captures, signes IA, notation « complémentaire » : tous auto-évalués.

**Texte corrigé**

```markdown
---
name: "site-local-chaine-obligatoire"
description: "À lire au début de toute tâche qui crée, refait ou modifie un site, une page ou une maquette locale : relecture, ordre des skills, comparaison obligatoire avec les sites de référence de Liam avant de montrer."
---

# Chaîne obligatoire pour tout site ou maquette

Décision de Liam (02/11/2026, 19 h 39) : les pages récentes étaient laides parce que les skills poussaient à empiler des effets. Nouvelle règle de fond : **sobre, net, grand** (voir `sites\moteur\REGLES-STYLE-SITES.md`). Cette règle prime sur tout autre skill en cas de contradiction.

## Relecture obligatoire
1. Au début de CHAQUE page, et après toute reprise ou compaction, relire en entier : `sites\moteur\REGLES-STYLE-SITES.md`, `sites\refs\REFERENCES-LIAM.md` et le SKILL.md de chaque skill site-local utile. Ne jamais travailler de mémoire.
2. Écrire en tête de la réponse « Skills relus : … » avec la liste exacte. Sans cette ligne, le travail n'est pas valable.

## Ordre de travail
1. **Références** : ouvrir (captures réelles) les 2 ou 3 sites de `REFERENCES-LIAM.md` les plus proches du besoin (skill site-local-references).
2. **Fiche métier** : `sites\moteur\metiers\<métier>.md` (contenu, sections, photos à chercher).
3. **Direction** : une famille (3 possibles), un accent, deux polices (skills direction-artistique et palette-signature).
4. **Photos et vidéo** : trouver d'abord le visuel du premier écran (skill realisme-photos).
5. **Texte** : rédiger les 5 à 7 sections (skill page-longue), puis la structure et les composants simples (skills structure-variee, interface-signature, rythme-ecrans).
6. **Conversion** : bouton d'appel, barre mobile, contact complet (skill conversion).
7. **Mouvement** : seulement la liste fermée de REGLES §5 (skill animation-3d).
8. **Comparaison** (étape obligatoire, voir ci-dessous), puis rapport.

## Étape obligatoire : comparer aux références avant de montrer
1. Capturer chaque référence choisie par Liam et la page, aux mêmes tailles (1440 × 900 et 390 × 844), premier écran et un écran du milieu. Dossier `captures\comparaison\`.
2. Assembler une planche côte à côte (références à gauche, page à droite) et la regarder.
3. Remplir ce tableau dans le rapport (mesures, pas impressions) :

| Mesure | Référence la plus proche | Ma page | Seuil |
|---|---|---|---|
| Éléments visibles dans le premier écran | … | … | au plus égal à la référence + 1 |
| Couleurs d'accent | … | … | 1 |
| Polices | … | … | 2 |
| Taille du titre (PC) | … | … | ≥ 56 px |
| Marge de la section / espace vide | … | … | pas plus dense que la référence |
| Effets de mouvement simultanés | … | … | ≤ 2 |
| Forme du bouton d'appel | … | … | rectangle simple |

4. Écrire le verdict : « plus sobre / aussi sobre / moins sobre que la référence, plus nette / moins nette ». **Si la page est moins sobre ou moins nette, la refaire** (3 tours au plus), puis joindre la planche au rapport.
5. Si un site de référence refuse le navigateur ou demande un compte, demander à Liam une capture et la ranger dans `sites\refs\`.

## Contrôles techniques
Captures 390 et 1280 px, Lighthouse mobile ≥ 90, accessibilité 100, contraste 4,5:1 mesuré sur les pixels réels, mouvement réduit, aucun faux avis, mention « exemple, pas votre site », `noindex`. Aucun déploiement sans accord de Liam. Noter la structure dans `sites\moteur\STRUCTURES.md`.

## Notation
Claude ne se donne pas de note sur 10. Il présente la planche de comparaison et le tableau ; la note est celle de Liam.
```

### 3.3 `site-local-references`

**Problèmes**
- Les références sont « cherchées » par Claude (recherche web, Refero illisible par l'outil de lecture) et décrites en texte : pas de capture, donc aucun niveau visuel réel. Les derniers REFERENCES.md citent des sites « non ouverts » ou des pages Awwwards qui ne donnent que des titres.
- Aucun lien avec la page produite : pas de comparaison.
- La règle « pas de banderole » est bonne mais isolée.

**Texte corrigé**

```markdown
---
name: "site-local-references"
description: "Avant de concevoir une page, ouvrir en vraie capture les sites de référence choisis par Liam, relever ce qui les rend nets, et en tirer des principes. À utiliser avant la direction artistique et avant de montrer une page."
---

# Références : des sites choisis par Liam, ouverts en capture

Principe : Claude ne choisit pas seul le niveau visuel. Liam fournit les sites (Linear, Raycast, Apple, Awwwards, Godly, et d'autres qu'il ajoute). Ils sont listés dans `sites\refs\REFERENCES-LIAM.md`, par catégorie : sombre et net, clair éditorial, photo plein cadre, artisan local.

## Avant de concevoir
1. Lire `sites\refs\REFERENCES-LIAM.md`, choisir 2 ou 3 références de la catégorie voulue (une sombre et une claire si le métier le permet).
2. Les ouvrir avec le navigateur (Playwright), prendre les captures 1440 × 900 et 390 × 844 : premier écran, puis deux écrans plus bas. Les enregistrer dans `captures\ref-<site>-pc.png` et `-mobile.png`. Regarder les images (pas seulement le texte de la page).
3. Pour chaque référence, noter en 5 lignes : nombre d'éléments dans le premier écran, taille et chasse du titre, type de bouton, rapport entre texte et espace vide, ce qui est animé (peu). Écrire 3 principes à retenir et ce qu'on ne reprend pas.
4. Consigner dans `REFERENCES.md` de la page : sites ouverts, date, principes. Un site non ouvert ou non vu en capture n'est pas cité comme référence.

## Règles
- Ne jamais copier : ni textes, ni images, ni logo, ni code, ni mise en page à l'identique. On reprend des principes (rythme, échelle, espace).
- Pas de bannière ni de bandeau défilant au-dessus de l'en-tête, sauf information réelle (fermeture exceptionnelle).
- En-tête : logo à gauche, 3 à 5 liens, un bouton d'appel à droite.
- Les références servent aussi à la comparaison finale (voir site-local-chaine-obligatoire) : on rouvre les mêmes captures.

## Contrôle
`REFERENCES.md` liste 2 ou 3 sites réellement ouverts avec leurs captures ; la page ne ressemble à aucun d'eux pris isolément, mais n'est pas plus chargée que le plus chargé.
```

### 3.4 `site-local-direction-artistique`

**Problèmes**
- « Écrire le parti pris en une phrase » (« chaleureux comme un atelier d'orfèvre ») : description verbale, sans image.
- « Une seule audace par page » contredit les autres skills, qui ne le respectent plus.
- « Matières crédibles… brume, halo discret sur les lumières, 3D réaliste » : pousse à l'ajout d'effets de lumière.
- Les « clichés d'IA » sont bien, mais la liste omet les nouveaux habillages (cockpit, HUD).
- Contrôles = comparer à « trois sites génériques du métier » (mauvaise référence) au lieu des sites de Liam.

**Texte corrigé**

```markdown
---
name: "site-local-direction-artistique"
description: "Définir la direction artistique d'une page locale : une famille, un accent, deux polices, un visuel réel, en partant des références de Liam. À utiliser avant de coder."
---

# Direction artistique

Objectif : le visiteur comprend le métier et se sent en confiance en trois secondes. La page est **sobre, nette, grande**. Elle ne cherche pas à « faire technologique ». Lire `sites\moteur\REGLES-STYLE-SITES.md` et ouvrir les références (site-local-references).

## 1. Décider (en cinq lignes, avec les captures de référence ouvertes à côté)
1. La famille : clair éditorial, sombre net ou photo plein cadre.
2. Le visuel du premier écran : quelle photo ou vidéo réelle (voir realisme-photos), avec le cadrage voulu.
3. L'accent : une teinte, tirée d'un objet réel du métier (tube de cuivre, enseigne, croûte), utilisée pour le bouton d'appel et rien d'autre.
4. Les polices : une police pour les titres (grotesque ou serif de caractère), une pour le texte. Pas d'Inter, de Roboto, d'Arial ni de Space Grotesk par défaut.
5. Le titre du premier écran : une phrase d'information (métier + ville), 3 lignes au plus.

## 2. Jetons CSS
4 à 6 variables : fond, texte, texte secondaire, filet, accent, éventuellement un second fond. Neutres teintés légèrement (pas de gris pur). Contraste du texte ≥ 4,5:1, mesuré sur les pixels réels derrière le texte quand il est sur une photo.

## 3. Composition
- Un message par écran, un très grand titre, un seul visuel par écran, beaucoup d'espace vide.
- Alterner écrans denses (texte) et écrans aérés (image).
- Pas de calques décoratifs : pas de trame, de grain forcé, de lueur, de cadre de visée.
- Le titre de chaque section répond à une question du client (qui, quoi, combien, où, comment) en une ligne.

## 4. Clichés « IA » à éviter
Voir REGLES-STYLE-SITES §1 : signes classiques et habillages « technologiques » (cockpit, HUD, jauges, voyants, lueurs, coins coupés). Un seul de ces éléments = le retirer.

## 5. Contrôles
- Test des trois secondes : on devine le métier, la ville et comment appeler.
- Test des références : planche côte à côte avec 2 ou 3 sites de Liam (skill chaine-obligatoire). La page doit être aussi sobre et nette.
- Test du remplacement : si on change le nom et la ville, la page pourrait-elle servir à un autre métier ? Alors la refaire.

## Livrable
Bloc de jetons CSS, cinq lignes de décision, captures 390 et 1280 px, planche de comparaison.
```

### 3.5 `site-local-palette-signature`

**Problèmes**
- L'objectif « jamais bleu/orange générique, tirée de la matière » pousse à des combinaisons inhabituelles (vert-de-gris + cuivre, graphite + laiton) choisies pour être *différentes*, non pour être belles ; avec 2 couleurs vives plus le bleu de l'eau, on dépasse l'accent unique.
- « Extraire 3 couleurs d'une vraie photo (pipette) » : acceptable, mais sans référence de palette réelle.
- Aucune mesure de contraste sur photo.

**Texte corrigé**

```markdown
---
name: "site-local-palette-signature"
description: "Choisir la palette d'une page locale : neutres, un seul accent tiré d'un objet réel du métier, contrastes mesurés."
---

# Palette : neutres + un seul accent

Une palette réussie est presque entièrement neutre ; l'accent est rare. On regarde d'abord les palettes des références ouvertes (Linear : sombre et neutre ; Apple : blanc et gris ; Raycast : noir et une teinte). On ne cherche pas la différence, on cherche la netteté.

## Méthode
1. Deux neutres : un fond (blanc cassé, papier, ou quasi noir) et un texte (encre ou blanc cassé), légèrement teintés vers l'accent. Un troisième neutre pour les filets et le texte secondaire.
2. Un accent unique, tiré d'un objet réel du métier (cuivre d'un tube, rouge d'enseigne, croûte du pain, vert d'un feuillage). Il sert au bouton d'appel et à un petit nombre de détails (liens, voyant de focus). Jamais deux accents.
3. Vérifier : texte ≥ 4,5:1 sur son fond ; texte du bouton ≥ 4,5:1 sur l'accent ; texte sur photo mesuré sur les pixels réels (outil `sites\outils\contraste-plombier.mjs`, à adapter à la page).
4. Interdits : dégradés, bleu #007bff, orange chantier saturé, violet, deux teintes vives.

## Exemples de départ (à ajuster sur la photo choisie)
- Plomberie : fond #F4F5F3, texte #14262D, accent cuivre #A94A21.
- Électricité (sombre net) : fond #0E1113, texte #ECEAE4, accent laiton #C9A24B.
- Boulangerie : fond #F3F4F0, texte #1A2230, accent croûte #A65A1F.
- Garage (sombre net) : fond #101214, texte #ECEDEE, accent rouge #C8322B.
- Fleuriste : fond #F7F5F1, texte #1F2A22, accent vert #2F6B3F.

## Typographie
Deux familles libres maximum, auto-hébergées (WOFF2), `font-display: swap`. Titre en police de caractère, texte en police neutre lisible. Échelle fixe : 14 / 17 / 20 / 28 / 48 / 72 / 96 px (fluide avec `clamp`).

## Vérification
Mettre côte à côte la page et deux références : le nombre de couleurs vives est-il le même ou inférieur ? Elles doivent se ressembler par leur retenue.
```

### 3.6 `site-local-interface-signature`  (renommage suggéré : `site-local-interface-nette`)

**Problèmes**
- C'est la cause directe des boutons « moches » : « chaque composant tiré de l'univers du métier » (plombier : « boutons en robinet ou en vanne qui tourne au clic », électricien : « boutons en interrupteur », garage : « clé à molette », boulangerie : « pain qui lève »). Résultat : roue de vanne, coins coupés, objets décoratifs.
- Sept familles dont plusieurs catalogues d'effets (halo conique, texte qui défile, verre, magnétique).
- « Un seul concept d'interface appliqué partout » force à tout décorer de la même façon.

**Texte corrigé**

```markdown
---
name: "site-local-interface-signature"
description: "Interface simple et nette d'une page locale : navigation, boutons, étiquettes, formulaire. Pas de composants dessinés comme un objet du métier. Renommage suggéré : site-local-interface-nette."
---

# Interface nette

Problème corrigé : les boutons et cadres dessinés « pour le métier » (vanne, clé, interrupteur, pain qui lève, coins coupés, voyants, lueurs) ont donné des pages jugées laides par Liam (02/11/2026). Les références (Linear, Raycast, Apple) utilisent des composants ordinaires, très bien exécutés.

## Principe
L'identité du métier vient de la **photo, du titre, de la couleur d'accent et du texte**, pas de la forme des boutons. Tous les composants sont standards ; leur finition fait la qualité.

## Composants (valeurs détaillées dans REGLES-STYLE-SITES §4)
- **Bouton d'appel** : rectangle plein à angles de 6 px, fond accent, texte 16-17 px graisse 600, hauteur 52-56 px, icône de téléphone de 20 px. Survol : fond plus sombre de 8 %. Aucune lueur, aucun reflet, aucun aimant, aucune roue, aucun voyant.
- **Bouton secondaire** : lien souligné ou filet 1 px, mêmes dimensions.
- **Navigation** : logo, 3 à 5 liens, un bouton d'appel.
- **Étiquette « exemple, pas votre site »** : petite ligne de texte 13 px en en-tête et en pied, sans pastille.
- **Séparateurs** : filet 1 px de la couleur du texte à 15 %, ou simple espace.
- **Formulaire** : étiquettes au-dessus, champs 52 px, bordure 1 px, bouton plein.
- **Carte** : cadre 1 px, mêmes angles que les boutons ; bouton Itinéraire = secondaire.
- **Focus** : contour 3 px visible, contrasté.

## Interdits
Voir REGLES-STYLE-SITES §1 : coins coupés, cadres de visée, voyants, jauges, relevés mono, lueurs, reflets, aimant, curseur personnalisé, objets du métier en guise de boutons, ombres décalées, bordures de 2-3 px, pilules identiques d'un site à l'autre.

## Contrôle
Recadrer la navigation et les deux boutons, les placer à côté des mêmes éléments de Linear, Raycast ou Apple : sont-ils aussi simples, aussi nets, aussi peu nombreux ? Sinon, simplifier.
```

### 3.7 `site-local-structure-variee`

**Problèmes**
- « Différer des deux dernières pages sur au moins 4 des 6 axes » : la variété devient un objectif en soi ; le hero « objet animé (vanne, four, rouleau) » pousse aux gadgets.
- Aucune limite basse de qualité : on varie même si la structure est moins bonne.
- Contradiction avec conversion (mêmes éléments aux mêmes endroits).

**Texte corrigé**

```markdown
---
name: "site-local-structure-variee"
description: "Varier modestement la structure d'une page d'un métier à l'autre, sans sacrifier la clarté : type de premier écran, ordre des sections."
---

# Structure : variée, mais toujours claire

Les pages d'un métier à l'autre ne doivent pas être des copies, mais la clarté passe avant la variété. Lister d'abord les structures déjà faites dans `sites\moteur\STRUCTURES.md`.

## Ce qu'on fait varier (au moins 2 des 4)
1. **Premier écran** : photo ou vidéo plein cadre avec titre dessus, ou titre très grand sur fond uni avec un grand visuel dessous, ou deux colonnes (texte / photo). Jamais un objet animé.
2. **Ordre des sections** : ce qui rassure le plus ce métier vient en premier (dépannage d'abord pour un plombier, réalisations d'abord pour un électricien, carte d'abord pour un restaurant).
3. **Grille** : colonne unique, deux colonnes asymétriques, bandes pleine largeur alternées, mosaïque de photos.
4. **Section propre au métier** : avant/après de photos réelles, déroulé d'un chantier en étapes, carte du menu, horaires du four.

## Ce qui ne varie pas
Navigation simple, bouton d'appel au même endroit (en-tête, premier écran, fin de page, barre mobile), contact complet en dernier écran.

## Règles
- Aucune section fourre-tout : chaque bloc répond à une question du client.
- Pas de composant inventé pour être différent.
- Comparer avec les références : leur structure est simple (une idée par écran).

## Contrôle
Une capture complète par page, côte à côte avec les deux précédentes pages et une référence : la nouvelle page se distingue par sa photo, son ordre et sa section propre, pas par des effets. Noter la structure dans `STRUCTURES.md`.
```

### 3.8 `site-local-page-longue`

**Problèmes**
- « 6 à 8 écrans, 700 à 1 100 mots » : on remplit pour atteindre la longueur ; les pages sont trop longues et trop denses face aux références (peu de mots, énormément d'espace).
- « Chaque écran a son animation propre… jamais un simple fondu » : impose un effet par écran.
- « Une grande section signature au milieu » : encore un effet.
- Plan type rigide en 8 écrans.

**Texte corrigé**

```markdown
---
name: "site-local-page-longue"
description: "Écrire une landing page locale de 5 à 7 sections, claire et crédible, avec peu de mots par écran et beaucoup d'espace."
---

# Page locale : 5 à 7 sections, peu de mots, beaucoup d'espace

Corrigé le 02/11/2026 : les pages longues et chargées ont été jugées laides. Les références (Linear, Apple) disent une chose par écran, en peu de mots, avec beaucoup de blanc.

## Plan (à adapter au métier)
1. **Premier écran** : métier, ville, une phrase d'information, bouton d'appel, visuel réel.
2. **Ce que nous faisons** : 4 à 6 prestations réelles, une phrase concrète chacune (liste simple, pas trois cartes à icône).
3. **Comment ça se passe** : 3 ou 4 étapes d'une intervention (délais indicatifs marqués comme exemples).
4. **Réalisations ou matériel** : photos réelles légendées (avant/après si on a de vraies photos).
5. **Garanties, horaires, zone** : engagements marqués comme exemples, communes desservies en texte.
6. **Questions fréquentes** : 5 questions utiles (prix, délai, déplacement, paiement, garanties).
7. **Contact** : appel, adresse, carte au clic, horaires, formulaire court.

Fusionner si le métier s'y prête ; jamais moins de 5 sections.

## Écriture
- Français courant et précis, vouvoiement, phrases courtes. **40 à 90 mots par section, 500 à 800 mots au total.**
- Vocabulaire réel du métier et du lieu (quartiers, communes de Normandie).
- Interdits : « Bienvenue chez », « passionné », « qualité et service », « à votre écoute », superlatifs sans preuve, « leader ».
- Aucun chiffre, avis ou diplôme inventé ; horaires, adresse, numéro, tarifs sont des exemples signalés.
- Titres d'information (ce que fait l'entreprise, ce qui est inclus), jamais de question familière au client ; les lire à voix haute.

## Mouvement
Seulement la liste fermée de REGLES-STYLE-SITES §5. Le texte reste lisible sans JavaScript.

## Contrôle
Compter les sections et les mots ; supprimer toute phrase qui pourrait figurer sur la page d'un autre métier ; corriger l'orthographe ; comparer à la densité de texte des références.
```

### 3.9 `site-local-rythme-ecrans`

**Problèmes**
- Il traite de réglages d'animation (écran épinglé « livrant quelque chose à chaque tiers », « 150 % ») qui supposent des écrans épinglés : l'épinglage devient la norme.
- La carte : « habiller la carte (cadre aux angles de la famille de style, légende, pastille exemple) » : invite à décorer.
- Bon : ton, vouvoiement, écrans de fin complets, vraie carte Google Maps au clic. À garder.

**Texte corrigé**

```markdown
---
name: "site-local-rythme-ecrans"
description: "Longueur, ton et écrans finaux d'une page locale : défilement court, contact complet, vraie carte Google Maps au clic."
---

# Rythme des écrans

Retours de Liam sur les pages précédentes : « c'est long à scroller pour rien », ton parfois vulgaire, derniers écrans pauvres, carte dessinée moche.

## Longueur
- Ordinateur : 6 à 9 hauteurs d'écran au total. Mobile : 9 à 13.
- **Aucun écran épinglé par défaut.** Si Liam en demande un, 150 % de hauteur d'écran au plus.
- Pas de zone vide pour « laisser jouer » une animation. L'espace vide est voulu (marges larges), pas un temps mort.
- Navigation par ancres et bouton d'appel toujours accessibles.

## Ton
Vouvoiement, pro, précis, sans familiarité ni blague. Titres d'information, jamais de question générique au client. Relire chaque titre à voix haute.

## Écrans de fin
- L'avant-dernier apporte une vraie information utile (démarche, ce qui est inclus, délais).
- Le dernier est une clôture complète : bouton d'appel net, adresse, carte, horaires, formulaire de rappel court, engagements (exemples signalés), pied de page propre. Autant de soin que le premier écran, avec les mêmes composants simples.

## Carte et itinéraire
- Vraie carte Google Maps : `<iframe>` d'intégration (adresse d'exemple), `loading="lazy"`, dimensions fixées, `title` explicite, `referrerpolicy="no-referrer-when-downgrade"`, chargée seulement au clic sur « Afficher la carte » (confidentialité et performance).
- URL d'intégration à utiliser telle quelle (elle évite une redirection) : `https://www.google.com/maps/embed?origin=mfe&pb=!1m3!2m1!1s<adresse+encodée>!6i15!3m1!1sfr!5m1!1sfr`.
- Bouton « Itinéraire » (lien `https://www.google.com/maps/dir/?api=1&destination=…`) de même format que le bouton secondaire, et « Appeler » à côté sur mobile.
- Cadre de 1 px, mêmes angles que les boutons. Pas de légende ni de pastille décorative.

## Contrôle
Comparer visuellement les écrans 1, dernier et avant-dernier : même typographie, mêmes composants, même soin. Chronométrer un défilement régulier : si rien de nouveau n'apparaît pendant un demi-écran, raccourcir.
```

### 3.10 `site-local-realisme-photos`

**Problèmes**
- Bon fond (vraies photos, licence notée, pas d'illustrations), mais :
- Critère « photos prises sur le terrain, léger désordre crédible » : donne des photos de stock sombres, peu nettes ; aucune exigence de qualité ni d'étalonnage ; aucun contrôle de cadrage sur le premier écran.
- Pas de place pour la vidéo, que Liam a aimée sur la boulangerie.
- Le hero « Hero ≤ 150 Ko » peut entraîner une photo trop compressée.

**Texte corrigé**

```markdown
---
name: "site-local-realisme-photos"
description: "Choisir de vraies photos et vidéos libres de droit, nettes et bien cadrées, pour une page locale crédible. Licences notées dans CREDITS.json."
---

# Photos et vidéo : réelles, nettes, bien cadrées

Un artisan inspire confiance par du réel. Le visuel du premier écran est le plus important de la page : Liam a beaucoup aimé la vraie vidéo de la boulangerie (mains dans la farine) ; c'est le modèle à suivre.

## Sources et licences
Pexels, Pixabay, Unsplash, Mixkit, Wikimedia Commons, ou photos du client. Chaque fichier est noté dans `CREDITS.json` (URL, auteur, licence, date, usage, dimensions). Sans licence notée, la page est bloquée. Pas de logo, de marque ni de personne reconnaissable ; pas d'image générée par IA ; pas de photo d'un autre pays (prises, panneaux, plaques).

## Choisir
1. Chercher 15 à 20 candidats, en ouvrir les captures, garder les 2 ou 3 meilleurs.
2. **Premier écran** : une vidéo de 6 à 10 secondes (gros plan du geste du métier, sans visage) ou une photo large, **nette, lumineuse, bien cadrée, avec de la place pour le titre**. Si la meilleure photo est sombre ou floue, en choisir une autre.
3. Écrans suivants : une photo par section utile, jamais décorative.
4. Si aucune image n'est convaincante, le dire dans le rapport et laisser un emplacement « photo du client à venir ».

## Traitement
- Un seul étalonnage pour toute la page (légère correction de contraste, pas de filtre fort). Voile uniforme sous le texte pour la lisibilité, sans calques décoratifs.
- Vidéo : WebM de 1 à 4 Mo, lue une fois sur ordinateur, image de repli (poster) sur mobile, connexion lente et mouvement réduit. Image de repli = LCP, `fetchpriority="high"`.
- Images WebP, `width` et `height` fixés, `alt` décrivant ce que l'on voit réellement.

## Crédibilité
Concret, preuves vraies uniquement (aucun faux avis, chiffre ou label), mise en page ordinaire, vouvoiement, vocabulaire du métier. Un site sobre vaut mieux qu'un site spectaculaire qui sonne faux.

## Contrôle
Regarder chaque image à pleine taille. Comparer le premier écran à ceux des références : l'image est-elle aussi nette et aussi bien cadrée ? Lister dans le rapport les images, leur licence et ce qui reste à remplacer par des photos du client.
```

### 3.11 `site-local-signature-interaction`  (renommage suggéré : `site-local-moment-utile`)

**Problèmes**
- « Chaque page contient une interaction signature, visible dans les 2 premiers écrans, plus 2 micro-animations » : cumule avec les animations par écran des autres skills.
- « Une page propre mais sans moment fort vaut 6/10 : ce skill vise 9/10 » : encourage l'auto-notation et le gadget.
- Les propositions « goutte d'eau qui révèle la photo », « rouleau qui peint », « nuages qui s'écartent » : décoratives.
- L'avant/après de photos réelles est utile : à garder, seulement si l'on a de vraies photos.
- Lighthouse ≥ 95 contredit ≥ 90.

**Texte corrigé**

```markdown
---
name: "site-local-signature-interaction"
description: "Un seul moment interactif, seulement s'il aide à décider : avant/après de vraies photos, ou rien. Renommage suggéré : site-local-moment-utile."
---

# Un moment utile, ou rien

Corrigé le 02/11/2026 : les « interactions signature » (schéma de maison, manette, vanne, règle des heures) ont produit des pages jugées laides. Règle : **aucun gadget.** Une interaction n'existe que si elle aide le visiteur à décider d'appeler.

## Test avant d'ajouter une interaction
1. Quelle question du client règle-t-elle ? (une phrase)
2. Un texte ou une photo ne ferait-il pas aussi bien ? Si oui, utiliser le texte ou la photo.
3. Existe-t-elle sur une référence de Liam ? Sinon, ne pas l'ajouter.

## Seule interaction recommandée : avant/après de vraies photos
Valable pour plombier (salle de bain), électricien (tableau, éclairage), peintre, couvreur, maçon, plâtrier, menuisier.
- Deux photos du même cadrage, même ratio, vraies et sous licence notée dans `CREDITS.json`. Sinon, pas d'avant/après.
- Curseur à poignée de 44 px, tactile et clavier (flèches), `aria-label`, valeur initiale 50 %, étiquettes « Avant » et « Après ».
- Mention « photos d'illustration, exemple » ; jamais présentées comme un chantier du prospect.
- `prefers-reduced-motion` : l'état « après » est affiché sans effet.
- Moins de 30 Ko de JavaScript, images WebP avec dimensions.

## Rien d'autre par défaut
Pas de schéma interactif, de règle graduée, de maison à points, de jauge, de séquence au défilement, de curseur personnalisé. Si Liam en demande un, le faire simple et l'accompagner d'une planche de comparaison.

## Vérification
Capture 390 et 1280 px ; la page reste belle sans l'interaction ; l'interaction ne masque ni le numéro de téléphone ni le bouton d'appel ; Lighthouse mobile ≥ 90.
```

### 3.12 `site-local-conversion`

**Problèmes** (peu)
- Bon fond. À garder presque tel quel.
- Manque : spécification du bouton d'appel simple (aujourd'hui contredite par interface-signature/futurisme-utile) et rappel que le premier écran contient **un seul** bouton d'appel.

**Texte corrigé**

```markdown
---
name: "site-local-conversion"
description: "Concevoir une page locale qui convertit : une action principale, preuves honnêtes, mobile d'abord, SEO local, bouton d'appel simple et net."
---

# Page locale qui convertit

Une page convertit quand le visiteur comprend en cinq secondes qui, quoi et où, et peut agir en un geste.

## 1. Une action principale
Appeler (dépannage, urgence), demander un devis (travaux), réserver (restaurant, coiffeur), commander (fleuriste), venir (commerce de quartier). Une action secondaire au plus.
**Le premier écran contient un seul bouton d'appel** ; l'en-tête peut montrer le numéro en texte, pas un second bouton. Le bouton est un rectangle simple (REGLES §4).

## 2. Structure de persuasion
1. Promesse au premier écran : métier, ville, ce que fait l'entreprise.
2. Preuves vraies, visibles tôt (voir 4).
3. Réduction du risque : devis écrit, assurance, garantie, uniquement ce que l'entreprise confirme (exemples signalés).
4. Déroulé simple en 3 ou 4 étapes.
5. FAQ qui lève les 5 freins : prix, délai, déplacement, démarches, garanties.
6. Rappel de l'action principale en fin de page.

## 3. Mobile d'abord
Barre d'action fixe en bas (Appeler plein, Itinéraire en texte ou filet), cibles ≥ 48 px, `env(safe-area-inset-bottom)`, liens `tel:`, formulaire de 4 champs maximum avec libellés visibles. La barre apparaît quand le premier écran est passé.

## 4. Preuves honnêtes
Avis Google réels avec lien et accord ; qualifications avec numéro vérifiable ; photos réelles ; ancienneté fournie par l'entreprise. Aucun faux avis (délit : jusqu'à 2 ans de prison et 300 000 euros), aucun compteur inventé, aucune fausse urgence, aucun « 24 h/24 » sans horaires réels.

## 5. Référencement local
Titre et description avec métier et ville ; communes en texte HTML ; JSON-LD du type précis avec `areaServed` (jamais `aggregateRating` sur son propre site) ; nom, adresse et téléphone identiques à la fiche Google.

## 6. Mesure sans cookie
Mesure d'audience sans cookie (exemption CNIL, à vérifier), ou « comment nous avez-vous connus ? » à chaque appel. Pas de pixel de suivi sans consentement. Point après 30 jours avec l'artisan ; aucune promesse chiffrée avant mesure.

## 7. Liste de contrôle
- [ ] Action principale visible sans défiler, sur mobile.
- [ ] En cinq secondes : qui, quoi, où.
- [ ] Un seul bouton d'appel dans le premier écran.
- [ ] Preuves réelles et sourcées, FAQ complète.
- [ ] Barre mobile, `tel:` testé, formulaire court testé.
- [ ] Communes en texte, JSON-LD validé.
- [ ] Aucun chiffre, avis ou badge sans source.
```

### 3.13 `site-local-animation-3d`  (renommage suggéré : `site-local-mouvement-discret`)

**Problèmes**
- « Niveau d'ambition minimum pour chaque page » : six exigences (entrée orchestrée, animation par écran, section épinglée, typographie cinétique + marquee + curseur personnalisé, **moment 3D**, parallaxe, grain, lueurs) : c'est la liste d'accumulation.
- 3D obligatoire malgré le retour « la 3D n'a aucun sens » ; en plus on y lit des instructions de modélisation avancée (biseaux, normales, bloom) qui n'aboutissent pas dans le budget.
- Trois niveaux techniques (CSS, GSAP + Lenis, three.js) présentés comme à utiliser : bibliothèques supplémentaires.
- Contradiction avec REGLES §1 (curseur, compteurs).
- À conserver : repli mobile, mouvement réduit, budget de performance, `transform`/`opacity` seulement.

**Texte corrigé**

```markdown
---
name: "site-local-animation-3d"
description: "Mouvement discret d'une page locale : liste fermée d'effets autorisés, accessibilité, performance. Pas de 3D par défaut. Renommage suggéré : site-local-mouvement-discret."
---

# Mouvement discret

Décision de Liam (02/11/2026, 19 h 39) : moins d'effets. Le texte et l'appel restent utilisables sans animation. Le mouvement sert à rendre la page agréable, jamais à impressionner.

## Liste fermée des effets autorisés
1. Apparition du titre du premier écran : opacité et décalage de 12 px, 600 ms, une seule fois.
2. Léger zoom lent de l'image ou de la vidéo du premier écran (6 % au plus, 8 à 10 s).
3. Apparition des images et des blocs au défilement : opacité et décalage de 16 px, 500 ms, une seule fois, pas sur toutes les sections.
4. Changement de couleur au survol et au focus d'un bouton ou d'un lien (150 ms).
5. Accordéons de la FAQ.
6. Vidéo du premier écran (voir realisme-photos) : lue une fois, puis image tenue.

Au plus **2 effets visibles à la fois**. Tout autre effet (parallaxe forte, texte cinétique, marquee, curseur personnalisé, lueur, aimant, épinglage, séquence pilotée au défilement, particules) est interdit sans accord écrit de Liam.

## 3D
Interdite par défaut. Une 3D n'est ajoutée que si Liam la demande ; elle sert alors une utilité écrite en une phrase et utilise de vrais modèles réalistes, avec repli en image. Sinon, vraie photo ou vraie vidéo.

## Techniques
CSS natif et JavaScript natif. Pas de GSAP, Lenis ni three.js sauf demande de Liam. `animation-timeline: view()` possible sous `@supports`. Animer seulement `transform` et `opacity`.

## Version mobile
Mêmes effets en plus légers ; vidéo remplacée par l'image de repli ; aucun suivi du pointeur.

## Accessibilité
`prefers-reduced-motion: reduce` coupe tout : contenu visible immédiatement, vidéo remplacée par l'image. Aucun clignotement. Le contenu important est dans le HTML.

## Budget
JS au chargement ≤ 60 Ko ; Lighthouse mobile ≥ 90, LCP < 2,5 s, CLS < 0,1 ; images et vidéos avec dimensions.

## Erreurs courantes
Animer `top`, `width` ou `height` ; LCP en `opacity: 0` ; polices ou images sans dimensions ; texte dépendant du JavaScript ; effet qui n'explique rien ; empiler plus de deux effets.

## Contrôle
Série d'images de l'entrée (0, 1, 2 s) et capture de la page en mouvement réduit. La page doit paraître calme et nette, comme les références.
```

### 3.14 `site-local-niveau-10000`  (renommage suggéré : `site-local-premier-ecran`)

**Problèmes**
- C'est le skill le plus nocif : « ça vaut 10 000 € », « prime sur toute consigne plus sage », « le premier écran est un film », « finitions d'agence : typographie cinétique, curseur personnalisé, magnétique, Lenis, parallaxe, grain, vignettage », « effet wow à noter sur 10 ». L'ancrage « 10 000 € » se traduit par plus d'effets.
- Les idées par métier (« eau qui coule et se divise dans un réseau de tuyaux en cuivre », « pièce qui s'allume par zones avec halo volumétrique ») : gadgets.
- Il contient une idée très bonne, à garder : **une vraie vidéo libre de droit en premier écran** (la boulangerie, aimée par Liam), avec image de repli.
- Les garde-fous (accessibilité, repli mobile, licences) sont bons.

**Texte corrigé**

```markdown
---
name: "site-local-niveau-10000"
description: "Premier écran d'une page locale : une vraie vidéo ou photo plein cadre, un très grand titre, un bouton. Pas d'effets de démonstration. Renommage suggéré : site-local-premier-ecran."
---

# Premier écran : un grand visuel réel et un grand titre

Décision de Liam (02/11/2026, 19 h 39) : l'accueil de la boulangerie (vraie vidéo, titre géant) est très apprécié ; les pages chargées d'effets sont jugées laides. Ce skill remplace l'ancienne exigence « niveau 10 000 € » : la valeur perçue vient de la qualité du visuel, de la typographie et de l'espace, pas du nombre d'effets.

## Recette
1. **Visuel** : vraie vidéo de 6 à 10 s libre de droit (Pexels, Pixabay, Mixkit), gros plan du geste du métier, sans visage, étalonnée légèrement, ou une grande photo nette. Voir realisme-photos pour la recherche et les licences.
2. **Titre** : métier + ville, 56 à 96 px sur ordinateur, 2 ou 3 lignes, blanc ou encre selon le fond, en police de caractère.
3. **Une phrase** d'information sous le titre (une ligne ou deux).
4. **Un bouton d'appel** simple (REGLES §4). Un lien texte secondaire possible.
5. **Voile uniforme** sous le texte pour la lisibilité (contraste ≥ 4,5:1 mesuré). Aucun calque décoratif.
6. En-tête : logo, 3 à 5 liens, numéro en texte ou bouton d'appel (un seul des deux dans le premier écran).

## Mouvement
Seulement : titre qui apparaît, léger zoom lent, vidéo lue une fois puis image tenue.

## Mobile, mouvement réduit, performance
Image de repli (poster) sur mobile, connexion lente et mouvement réduit ; poster = LCP (`fetchpriority="high"`, ≤ 150 Ko) ; vidéo WebM ≤ 4 Mo chargée après le premier affichage. Lighthouse mobile ≥ 90.

## Test avant de montrer
1. Planche côte à côte avec le premier écran de 2 ou 3 références de Liam (voir chaine-obligatoire) : aussi peu d'éléments, titre aussi grand, visuel aussi net ?
2. Ouvrir la page sans animation : elle reste complète et belle.
3. Compte rendu honnête de ce qui a été testé (navigateur, sans carte graphique).
```

### 3.15 `site-local-futurisme-utile`  (renommage suggéré : `site-local-sobriete-utile`)

**Problèmes**
- La cause directe de l'étape 1 plombier : « Interface futuriste (cockpit) : cadres fins, **coins coupés**, lignes de mesure, petites étiquettes en police mono, **indicateurs qui s'animent**, lueur contrôlée, verre dépoli, dégradés lumineux » ; « bouton d'appel signature : grand, **effet magnétique sur PC, lueur**, dessiné pour le métier » ; « guide ou avatar (orbe lumineux…) ».
- « Valent des milliers d'euros » comme objectif : même ancrage que niveau-10000.
- À garder : la règle d'or « rien de décoratif : à quoi ça sert ? » et l'obligation de faire valider par Liam un premier écran, un bouton d'appel et une clôture avant le reste.

**Texte corrigé**

```markdown
---
name: "site-local-futurisme-utile"
description: "Règle d'or : rien de décoratif. Chaque élément a une utilité écrite en une phrase. Validation de Liam sur le premier écran, le bouton d'appel et la clôture avant le reste. Renommage suggéré : site-local-sobriete-utile."
---

# Rien de décoratif

Retours de Liam sur la page plombier (02/11/2026) : la 3D n'a aucun sens, le schéma de départ est moche, le bouton d'appel et le bloc contact sont moches, puis, après la tentative « cockpit », la page est de nouveau jugée laide. Leçon : ajouter des éléments « technologiques » (coins coupés, voyants, jauges, relevés, lueurs, roue de vanne, goutte guide) aggrave le problème. Le style visé est celui de Linear, Raycast, Apple : sobre, net, grand.

## Règle d'or
Chaque élément (visuel, animation, composant) répond à : « à quoi sert-il pour le visiteur ? » en une phrase écrite dans le rapport. Sans réponse, on le supprime. En cas de doute, on supprime.

## Ce qui est « futuriste » ici
La qualité : une typographie très soignée, de grands espaces, une vraie image nette, des transitions douces, une page rapide. Pas d'habillage d'interface.

## 3D
Interdite par défaut (voir animation-3d). Utilité reconnue seulement si Liam la demande : démonstration du service ou fond immersif très discret, avec vrai modèle, repli image, utilité écrite.

## Bouton d'appel et contact (priorité haute)
- Un bouton simple et net (REGLES §4), le plus visible de la page, repris dans le dernier écran. Pas de lueur, d'aimant, de forme spéciale, de voyant.
- Bloc contact : adresse, horaires en texte, vraie carte Google Maps au clic, bouton Itinéraire secondaire, formulaire court, dans les mêmes composants que le reste.
- Montrer la capture à Liam avec la planche de comparaison.

## Méthode
1. Ouvrir les références choisies par Liam (capture). 2. Écrire en 5 lignes : visuel du premier écran, famille, accent, polices, composants. 3. Construire le premier écran, le bouton d'appel et la clôture. 4. Comparer à la planche, montrer à Liam, attendre son accord avant le reste.

## Contrôle
Chaque élément a son utilité écrite ; le premier écran compte autant d'éléments que les références (+1 au plus) ; texte lisible sans animation ; version mobile propre ; mouvement réduit respecté ; garde-fous habituels (Lighthouse ≥ 90, licences, « exemple, pas votre site », `noindex`, aucun déploiement sans accord).
```

### 3.16 `site-local-notation-wow`  (renommage suggéré : `site-local-comparaison-et-validation`)

**Problèmes**
- La grille de notation (0 à 2 par critère, dont « moment fort » et « photos animées ») récompense les effets ; elle est remplie par Claude, qui s'est donné 8,4 sur une page que Liam juge laide.
- Aucune comparaison avec un site réel.
- Règle « 3 itérations maximum » sans critère extérieur : on s'arrête quand Claude est content.
- Contient « liam a noté 6/10 » : la seule note qui compte est la sienne.

**Texte corrigé**

```markdown
---
name: "site-local-notation-wow"
description: "Avant de montrer une page : comparaison mesurée avec les sites de référence de Liam, puis validation de Liam. Claude ne se donne pas de note sur 10. Renommage suggéré : site-local-comparaison-et-validation."
---

# Comparaison et validation (remplace la notation « wow »)

Constat du 02/11/2026 : Claude s'est noté 8,4 à 8,5 sur des pages que Liam juge laides. Une auto-note n'est pas une mesure. Désormais : une comparaison à des sites réels, puis la note de Liam.

## 1. Comparaison obligatoire (voir chaine-obligatoire)
- Capturer 2 ou 3 sites de `sites\refs\REFERENCES-LIAM.md` et la page, aux mêmes tailles (1440 × 900 et 390 × 844), premier écran et un écran du milieu.
- Assembler une planche côte à côte et la regarder.
- Remplir le tableau de mesures : éléments visibles dans le premier écran, couleurs d'accent, polices, taille du titre, densité, effets simultanés, forme du bouton.

## 2. Checklist binaire (oui ou non, sans note)
- [ ] Un seul accent. [ ] Deux polices au plus. [ ] Titre ≥ 56 px sur ordinateur.
- [ ] Un seul bouton d'appel dans le premier écran, rectangle simple.
- [ ] Vraie photo ou vidéo avec licence notée dans `CREDITS.json`.
- [ ] Au plus 2 effets de mouvement simultanés, aucun interdit de REGLES §1.
- [ ] Appel visible sur mobile, Lighthouse mobile ≥ 90, accessibilité 100, mouvement réduit géré.
- [ ] Aucun faux avis ni chiffre inventé ; « exemple, pas votre site » ; `noindex`.

## 3. Verdict
Écrire : « plus sobre / aussi sobre / moins sobre » et « plus nette / aussi nette / moins nette » que la référence la plus proche. **Si « moins » sur l'un des deux, refaire** (3 tours au plus). Sinon, présenter à Liam avec la planche, les captures 390 et 1280 px et 3 lignes : ce qui est fort, ce qui reste faible, ce qui diffère des références.

## 4. Validation
La note et l'accord sont ceux de Liam. Ne jamais modifier une page déjà validée (bistro, céramique) sans demande.
```

### 3.17 `site-local-metier-plombier`

**Problèmes**
- « Concept signature : un schéma de maison à 5 points… avec le tracé d'un tuyau qui se dessine » : exactement ce que Liam a jugé moche (« plan de maison »).
- « Moment 3D : raccord, vanne ou radiateur en cuivre et inox » : 3D sans utilité.
- Famille « atelier / plan : rayon 0, capitales mono » : habillage technique.
- Plan en 8 écrans, sans mention de l'avant/après de photos réelles.
- Couleurs : « cuivre, inox, eau (bleu froid) » : trois teintes.

**Texte corrigé**

```markdown
---
name: "site-local-metier-plombier"
description: "Fiche de la page plombier-chauffagiste : contenu, sections, visuels à chercher, ton. Sans schéma ni 3D décoratifs."
---

# Page plombier, fiche métier

Lire d'abord REGLES-STYLE-SITES, site-local-chaine-obligatoire et site-local-references. Retour de Liam (02/11/2026) : plus de schéma de maison, plus de 3D de vannes, pas d'habillage technique.

## Identité
- Famille : clair éditorial ou photo plein cadre. Accent : cuivre d'un tube (#A94A21 environ), un seul. Titres en grotesque de caractère, texte en police neutre.
- Le visiteur comprend : « il intervient vite, il explique, il donne un devis écrit ».
- Visuel du premier écran : la vidéo Pexels 7584762 (siphon, flexible, robinet d'arrêt, une main), 8 s, ou une photo nette de raccord en cuivre. Titre géant par-dessus. Un bouton d'appel simple.

## Sections (5 à 7)
1. Premier écran : « Plombier chauffagiste à Rouen », une phrase, bouton d'appel.
2. Dépannage : fuite, chasse d'eau, chauffe-eau, débouchage ; pour chacun, le premier geste (fermer l'arrivée d'eau…) et notre intervention. Liste simple en colonnes.
3. Chauffage : entretien annuel, remplacement de chaudière, désembouage, radiateurs ; une photo réelle.
4. Salle de bain : déroulé d'un chantier en étapes ; avant/après de **vraies photos libres de droit** si elles existent (sinon une seule photo légendée).
5. Devis et garanties : comment est construit un devis, déplacement, délais, paiement ; assurance et qualifications **marquées comme exemples**.
6. Questions fréquentes : prix, délai, déplacement, paiement, garanties.
7. Contact : bouton d'appel, adresse (exemple), carte Google Maps au clic, Itinéraire, horaires, zone d'intervention en texte, formulaire de rappel court, engagements (exemples).

## Ton
Vouvoiement, vocabulaire exact (siphon, flexible, robinet d'arrêt, groupe de sécurité, désembouage). Jamais de question familière au client.

## Contrôles
6 à 9 hauteurs d'écran sur ordinateur ; aucun écran épinglé ; aucune 3D ; aucun « 24 h/24 » sans horaires ; planche de comparaison avec 2 ou 3 références de Liam ; captures 390 et 1280 px ; « exemple, pas votre site », `noindex`.
```

### 3.18 `site-local-metier-electricien`

**Problèmes**
- « Concept signature : une manette d'interrupteur, la page s'allume, halo qui suit le curseur » : effet gadget, halo explicitement interdit par REGLES corrigées.
- « Moment 3D : ampoule ou suspension avec halo et verre réaliste » : 3D décorative.
- « Fond de nuit chaude, lumière comme seul accent », « famille halo » : style chargé.
- Plan 8 écrans avec « domotique et bornes » : sections de remplissage.

**Texte corrigé**

```markdown
---
name: "site-local-metier-electricien"
description: "Fiche de la page électricien : contenu, sections, visuels à chercher, ton. Sans manette, halo ni 3D décoratifs."
---

# Page électricien, fiche métier

Lire d'abord REGLES-STYLE-SITES, site-local-chaine-obligatoire et site-local-references. Retour de Liam (02/11/2026) : sobre, net, grand ; pas de gadget.

## Identité
- Famille : sombre net ou clair éditorial. Un seul accent, le laiton ou le jaune chaud d'un appareillage (#C9A24B environ), réservé au bouton d'appel. Titres en grotesque de caractère.
- Le visiteur comprend : « sécurité d'abord, puis confort ».
- Visuel du premier écran : une grande photo nette d'un tableau électrique refait, ou d'une pièce bien éclairée, ou une courte vidéo libre de droit. Titre géant par-dessus. Un bouton d'appel simple.

## Sections (5 à 7)
1. Premier écran : « Électricien à Rouen », une phrase, bouton d'appel.
2. Mise en sécurité : tableau électrique, mise aux normes, diagnostic, ce qui est vérifié (NF C 15-100 expliquée simplement).
3. Dépannage : disjoncteur qui saute, panne partielle, prise ou interrupteur défectueux ; premier geste et intervention.
4. Éclairage et rénovation : photos réelles d'éclairages, déroulé d'un chantier en étapes ; avant/après de vraies photos si elles existent.
5. Options : bornes de recharge, domotique, sans promesse chiffrée inventée.
6. Devis, garanties, questions fréquentes : certificats à présenter (exemples), assurance, délais, paiement.
7. Contact : comme la fiche plombier (appel, carte au clic, Itinéraire, horaires, formulaire court, engagements).

## Ton
Vouvoiement, précis, sans alarmisme. Aucun numéro de certification inventé.

## Contrôles
6 à 9 hauteurs d'écran ; aucun écran épinglé ; aucune 3D ; aucun halo ; planche de comparaison avec les références de Liam ; captures 390 et 1280 px ; « exemple, pas votre site », `noindex`.
```

### 3.19 `site-local-metier-garage`

**Problèmes**
- « Précision sombre » avec 3D de disque et étrier en écran 3 (jugée « pas ouf » par Liam), « ligne qui se trace », « bande horizontale épinglée », « petit schéma interactif de véhicule » : quatre gadgets.
- « Bouton d'appel animé » à l'écran 8 : encore un effet.
- Les corrections de ton (vouvoiement, pas de question vulgaire) et la clôture complète sont bonnes : à garder.

**Texte corrigé**

```markdown
---
name: "site-local-metier-garage"
description: "Fiche de la page garage automobile : contenu, sections, visuels à chercher, ton. Sans 3D ni schéma décoratifs."
---

# Page garage, fiche métier

Lire d'abord REGLES-STYLE-SITES, site-local-chaine-obligatoire, site-local-rythme-ecrans et site-local-references. Retours de Liam : ton vouvoiement sans vulgarité, défilement court, derniers écrans soignés, pas de 3D approximative.

## Identité
- Famille : sombre net. Graphite très sombre, un seul rouge d'étrier (#C8322B environ) réservé à l'appel. Titres en grotesque condensée de qualité, texte en police neutre.
- Le visiteur pense « précision et transparence » : chaque section montre ce que le garage vérifie.
- Visuel du premier écran : grande photo nette d'atelier ou de pièce mécanique (disque, étrier, clé), ou courte vidéo libre de droit. Titre géant par-dessus. Un bouton d'appel simple.

## Sections (5 à 7)
1. Premier écran : « Garage automobile à Rouen », une phrase, bouton d'appel.
2. Diagnostic et entretien : vidange, filtres, courroie, liquides, ce qui est inclus.
3. Freinage : disques, plaquettes, liquide ; ce qui est contrôlé ; une photo réelle.
4. Pneus : montage, équilibrage, géométrie, saisonnier, délais indicatifs.
5. Pièces et devis : pièces d'origine ou équivalentes, garantie, devis écrit avant travaux.
6. Contrôle technique : préparer la visite, points les plus souvent refusés (freinage, éclairage, pneus, émissions), contre-visite ; liste claire de 120 mots utiles.
7. Contact complet : appel, adresse (exemple), carte au clic, Itinéraire, horaires, formulaire de rappel (symptôme, immatriculation facultative), engagements (exemples).

## Ton
Vouvoiement, vocabulaire de mécanicien précis. Titres d'information (« Freinage : disques, plaquettes, liquide »). Pas de question lancée au client, pas de familiarité.

## Contrôles
6 à 9 hauteurs d'écran ; aucun écran épinglé ; aucune 3D ; planche de comparaison avec les références de Liam ; captures 390 et 1280 px ; « exemple, pas votre site », `noindex`.
```

### 3.20 `site-local-metier-boulangerie`

**Problèmes**
- « Concept signature : une règle graduée de 5 h à 19 h » (interactive) et « fournil en 3D (four, pain qui gonfle, vapeur) » : deux gadgets ; Liam a dit que la 3D du four n'était pas convaincante et que le reste de la page n'était pas son style.
- À garder : le premier écran « film » (vraie vidéo, titre géant), très aimé de Liam.
- Famille « éditorial papier porté vers le cinétique » : ambiguïté.

**Texte corrigé**

```markdown
---
name: "site-local-metier-boulangerie"
description: "Fiche de la page boulangerie : contenu, sections, premier écran en vraie vidéo, ton. Sans 3D ni règle interactive."
---

# Page boulangerie, fiche métier

Lire d'abord REGLES-STYLE-SITES, site-local-chaine-obligatoire et site-local-references. Retours de Liam (02/11/2026) : le premier écran avec la vraie vidéo est « très très beau » (à garder) ; la 3D du four n'est pas convaincante ; le reste de la page n'est pas son style.

## Identité
- Famille : clair éditorial. Fond blanc de farine légèrement gris-vert, encre bleu nuit, un seul accent chaud tiré de la croûte (#A65A1F environ) pour le bouton d'appel. Titres en serif de caractère (Young Serif ou équivalent), texte en grotesque neutre.
- Le visiteur sent le métier : farine, four, pain.
- Premier écran : la vidéo Pexels 11265881 (mains dans la farine, 8 s, WebM de 1 Mo) en plein cadre, titre géant par-dessus, une phrase, un bouton d'appel. Image de repli sur mobile.

## Sections (5 à 7)
1. Premier écran : « Boulangerie à Rouen », une phrase, bouton d'appel.
2. Le pain : baguette tradition, levain, farines, temps de fermentation (données du métier, non inventées), une grande photo.
3. Viennoiseries et pâtisseries : une photo réelle et deux phrases sur le feuilletage.
4. Les fournées et les horaires : liste simple des heures de sortie du four (exemple), pas de règle interactive.
5. Commandes : anniversaires, pâtisseries, pains spéciaux, délais indicatifs, comment commander.
6. L'artisan et les ingrédients : provenance, méthode, sans superlatifs ni faux chiffres.
7. Contact complet : appel, adresse (exemple), carte au clic, Itinéraire, horaires de la semaine, formulaire de commande court, pied de page propre.

## Ton
Vouvoiement, phrases courtes, termes exacts (grigne, pâton, levain). Aucune formule « Bienvenue ». Aucun faux avis.

## Contrôles
6 à 9 hauteurs d'écran ; aucun écran épinglé ; aucune 3D ; planche de comparaison avec les références de Liam ; captures 390 et 1280 px ; « exemple, pas votre site », `noindex`.
```

---

## 4. Nouveau fichier à créer par Liam : `sites\refs\REFERENCES-LIAM.md`

Les skills corrigés le lisent à chaque page. Modèle à remplir :

```markdown
# Références choisies par Liam (ne pas modifier sans lui)

## Sombre et net
- https://linear.app/ : très grand titre, une phrase, une capture produit, beaucoup d'espace.
- https://www.raycast.com/ : une image forte, un titre, un bouton.
## Clair éditorial
- https://www.apple.com/fr/ : très grandes photos, texte court, boutons simples.
## Photo plein cadre
- (à compléter par Liam : pages repérées sur Awwwards ou Godly)
## Artisan ou commerce local bien fait
- (à compléter par Liam)
```

Captures réalisées le 02/11/2026 pour ce diagnostic : `sites\refs\captures-2026-11-02\` (Linear, Raycast, Apple, en PC et mobile).

## 5. Limites de ce diagnostic

- Les « problèmes » viennent de la lecture des textes et des retours de Liam ; je n'ai pas testé les skills corrigés (rien n'a été construit).
- Les captures de référence sont des premiers écrans à une date donnée ; ces sites changent. Les comparaisons doivent être refaites avec des captures fraîches.
- Godly et Awwwards n'ont pas été capturés : Liam doit choisir les pages précises.
- La « comparaison » repose en partie sur mon jugement (sobre ou non) ; le tableau de mesures la rend vérifiable, mais **la validation reste celle de Liam**.
- Le renommage de certains skills est une suggestion ; les noms actuels sont cités dans d'autres fichiers (REGLES, CLAUDE.md de `B2B`), à mettre à jour ensemble.
