---
id: monument-3d
nom: Monuments 3D
version: 1.0.0
description: Monument en 3D (géométrie procédurale, three.js local), caméra libre à la souris, fond sombre.
declencheurs:
  - "la tour eiffel => monument=eiffel"
  - "tour eiffel => monument=eiffel"
  - "eiffel => monument=eiffel"
  - "la dame de fer => monument=eiffel"
commandes:
  - "monument : changer de monument (params : monument = identifiant du registre)"
  - "recentrer : remettre la caméra par défaut"
  - "rotation : rotation automatique lente (params : actif = true ou false)"
---

# Vue « monuments 3D »

- **three.js 0.160.0 en copie locale** (`visage\lib\three\`, licence MIT) : aucun CDN, aucun modèle téléchargé.
- **Souris** : clic gauche = orbite, molette = zoom, clic droit = déplacer (OrbitControls local). **Échap** ferme la vue.
- **Registre** : `monuments\index.js`. Pour ajouter un monument : créer `monuments\<id>.js` (une fonction `construire(THREE)` qui renvoie un `Group` en géométrie simple), l'ajouter à `index.js`, puis ajouter une ligne `"<nom> => monument=<id>"` aux déclencheurs ci-dessus.
- Monuments : `eiffel`.
