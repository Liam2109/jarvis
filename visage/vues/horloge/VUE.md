---
id: horloge
nom: Horloge
version: 1.0.0
description: Grande horloge plein écran (heure, date, secondes facultatives), sur fond sombre.
declencheurs:
  - "horloge"
  - "l'heure en grand"
commandes:
  - "secondes : afficher ou masquer les secondes (params : actif = true ou false)"
  - "format : 24 h ou 12 h (params : h12 = true ou false)"
---

# Vue « horloge »

Vue d'exemple, la plus simple : elle montre comment écrire une vue.

- `show(params)` crée la racine `position: fixed` plein écran (idempotent : un deuxième appel ne duplique rien) et lance UN minuteur.
- `hide()` arrête le minuteur et retire tout le DOM.
- `command(cmd, params)` : `secondes`, `format`.

Règles de toute vue : JS vanilla, aucun appel réseau, aucun `eval`, aucune lecture de `memoire\` ni de la config.
