# DESIGN.md — site vitrine LM MULTI-SERVICES (lmlsmulti-services.com)

Refonte du 11/11/2026. Références : Linear (priorité 1), Raycast (2), Apple (3, avec prudence) — voir `sites\refs\REFERENCES-LIAM.md`. Objectif : sobre, net, grand, riche en vraies photos, sans aucun signe « fait par IA ».

## Ce qu'on reprend des références
- **Linear** : titre très grand et serré, une seule phrase sous le titre, énormément d'espace blanc, neutres sombres, un petit bouton plein, aucune icône décorative.
- **Raycast** : un seul visuel fort par écran, un seul bouton d'action, une seule teinte d'accent utilisée avec parcimonie (jamais en fond, seulement sur l'action et 2 détails).
- **Apple** (avec prudence, trop policé pour un artisan) : l'espace entre les blocs et la hiérarchie typographique claire — pas le ton, pas le minimalisme total.
- Ce qu'on NE reprend PAS : produit logiciel, jargon technique, icônes d'interface, ton froid — le site reste chaleureux et concret, écrit pour un artisan qui n'a jamais eu de site.

## Couleurs (jetons existants, conservés : déjà sobres et non génériques)
| Jeton | Valeur | Rôle |
|---|---|---|
| `--bg` | #f5f6f7 | Fond clair général |
| `--paper` | #fff | Cartes, formulaire |
| `--ink` | #1b1f23 | Texte principal, fonds sombres |
| `--ink2` | #262b31 | Pied de page |
| `--muted` | #59626b | Texte secondaire |
| `--line` | #d8dde2 | Filets, bordures |
| `--accent` | #0e7c66 | Action (bouton d'appel), détails |
| `--accent-d` | #0a5c4c | Accent sur fond clair (contraste) |
| `--accent-l` | #52d4b4 | Accent sur fond sombre |
| `--accent-soft` | #e3f1ed | Fond très clair d'accent |

Un seul accent (vert profond), jamais de dégradé. Choix du vert : c'est la couleur de la confirmation — une fiche trouvée, un appel qui aboutit — pas une couleur de métier au sens propre puisque LM MULTI-SERVICES vend des sites, pas un geste d'artisan. Si Liam préfère une autre teinte, les jetons sont centralisés dans `:root` (une seule ligne à changer).

## Typographie
- Titres : **Bricolage Grotesque** (500–800), auto-hébergée, `text-wrap: balance`.
- Texte : **Hanken Grotesk** (400–700), auto-hébergée.
- Échelle fluide (`clamp`) : H1 38–68px, H2 28–44px, H3 20–24px, corps 17px mobile / 18px desktop.
- Aucune police par défaut (pas Inter, pas Roboto, pas Space Grotesk).

## Composants
- Boutons rectangulaires à coins 10px (`--r`), jamais en pilule, un seul plein (accent), un en filet.
- Cartes : filet 1px + rayon 14px, pas d'ombre portée.
- Numéros de section en contour (`.num-contour`) : repère de position, pas de décoration.
- Photos en cadre avec rideau doux + léger zoom (`.photo-cadre`), jamais d'illustration ni de forme flottante.
- Interaction signature : curseur avant/après dans le hero (« sans site » / « avec votre page ») — reprise et affinée, c'est la preuve directe de la promesse du site.

## Mouvements autorisés (liste fermée, REGLES §5 bis — au plus 2 à l'écran)
1. Hero : titre révélé ligne par ligne + curseur avant/après interactif.
2. Titres de section révélés ligne par ligne (déjà en place, `.titre-anime`).
3. Numéros de section en contour qui s'allument au défilement (déjà en place, `.num-contour`).
4. **Nouveau** : un écran épinglé (Solution) — une photo fixe (page exemple sur téléphone) et trois phrases qui se succèdent, ≤150 % de hauteur d'écran, empilé sur mobile.
5. Photos révélées par un rideau doux + léger zoom (déjà en place, `.photo-cadre`), appliqué à Problème, Offre, Déroulé.
6. **Nouveau** : une phrase géante révélée mot par mot, sur une photo plein cadre assombrie, juste avant la clôture.
7. Apparition douce (opacité + léger décalage) des cartes FAQ et de la grille d'exemples.

Pas de 3D : la version « luxe » (Dubaï, WebGL) existe dans `sites/agence/luxe/` mais n'est pas le projet demandé ici ; Liam a demandé Linear/Raycast, sobre, pas de 3D décorative.

## Plan des écrans (8, hors en-tête/pied)
1. Hero — promesse + curseur avant/après
2. Le problème — client qui cherche, ne trouve pas
3. La solution — ce que « être trouvé » veut dire, écran épinglé (3 phrases + photo téléphone)
4. Exemples — 3 pages réelles (plombier, électricien, coiffeur), liens cliquables
5. L'offre — 595 €, puis 49 €/mois, tout compris
6. Comment ça se passe — 4 étapes, appel → devis → paiement → mise en ligne
7. Questions fréquentes — 8 questions
8. Phrase géante (transition) puis clôture — appel très visible, Messenger, e-mail, formulaire court

## Contrôle
Captures 390 px et 1280 px prises après construction (`sites\outils\`, navigateur léger). Comparaison avec les captures Linear/Raycast de `sites\refs\captures-2026-11-02\` (réutilisées, non refaites — à signaler). Note sur 10 avant de montrer à Liam (skill site-local-notation-wow). Aucun déploiement en production sans son accord ; seule une préversion est montrée.
