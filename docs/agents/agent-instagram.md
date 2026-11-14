---
name: instagram
role: Publier un post par jour vers 12 h 30 d'après la file du plan Instagram, et fabriquer les prochaines cartes
machine: serveur DESKTOP-HLQSTAU (si listé dans agents_actifs)
planification: toutes les 5 min (serveur-taches.json, « jour » puis « valider »)
depend_de: jeton Instagram (hors git)
sorties: post Instagram, instagram-etat.json
---
# Agent Instagram
Simulation tant que `envoi_automatique` = false ; légendes sans promesse ni chiffre.
Détail : [[B2B/agents/instagram.md|doc de l'agent]] · plan : [[B2B/docs/INSTAGRAM-PLAN.md|plan Instagram]]
Liens : [[jarvis-ceo]] · [[decision-validation-manuelle]]
