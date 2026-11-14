---
name: page-exemple
role: Sur « métier, ville, nom » envoyé dans Discord, générer une page exemple déployée en aperçu (noindex) et renvoyer seulement le lien
machine: gros PC (lancé par Jarvis, lib/page-exemple.ps1) ; pas de tâche serveur
planification: non planifié sur le serveur (absent de serveur-taches.json)
depend_de: B2B/sites/moteur, règles de style des sites
sorties: page sur b2b-demos (aperçu), page-exemple-etat.json
---
# Agent page-exemple
Toute page suit [[B2B/sites/moteur/REGLES-STYLE-SITES.md|les règles de style]] et porte « exemple, pas votre site ».
Code : `B2B/agents/page-exemple.py` (pas encore de doc .md dédiée)
Liens : [[jarvis-ceo]] · [[agent-prospection]]
