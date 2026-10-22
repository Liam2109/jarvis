# three.js (copie locale)

- **Bibliothèque** : three.js, version **0.160.0** (paquet npm `three@0.160.0`, téléchargé une seule fois ; plus aucun téléchargement ensuite).
- **Licence** : MIT, voir `LICENSE` (Copyright © 2010-2023 three.js authors).
- **Fichiers gardés** : `build/three.module.min.js` et `examples/jsm/controls/OrbitControls.js` (le seul module qui l'importe est `'three'`).
- **Aucun CDN** : la page `visage\index.html` déclare une *import map* locale (`three` -> `/lib/three/build/three.module.min.js`). Aucun modèle 3D n'est téléchargé : les monuments sont construits en géométrie procédurale (`visage\vues\monument-3d\monuments\`).
- Mise à jour : remplacer ces deux fichiers par ceux d'une autre version du même paquet, en gardant les chemins.
