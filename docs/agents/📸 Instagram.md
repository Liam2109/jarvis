---
agent: instagram
aliases: [📸 Instagram]
name: instagram
role: Publier un post par jour vers 12 h 30 d'après la file du plan Instagram, et fabriquer les prochaines cartes
machine: serveur DESKTOP-HLQSTAU (si listé dans agents_actifs)
planification: toutes les 5 min (serveur-taches.json, « jour » puis « valider »)
depend_de: jeton Instagram (hors git)
sorties: post Instagram, instagram-etat.json
---
# 📸 Instagram
Simulation tant que `envoi_automatique` = false ; légendes sans promesse ni chiffre.
Détail : `B2B/agents/instagram.md` · plan : plan Instagram
Liens : [[docs/decisions/📌 Validation à la main|📌 Validation à la main]]
