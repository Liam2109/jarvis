---
name: prospection
role: Trouver des entreprises (bâtiment d'abord, Normandie puis France), un contact public, préparer les lots ; envoyer seulement ce que Liam valide
machine: serveur DESKTOP-HLQSTAU (si listé dans agents_actifs)
planification: toutes les 10 min (serveur-taches.json, commande « jour »)
depend_de: "[[agent-reponses]]"
sorties: lots, prospection-etat.json, messages Discord à valider
---
# Agent prospection
Rien ne part sans le « ok lot » de Liam ; `prospection_actif` = non sur le gros PC.
Détail : [[B2B/agents/prospection.md|doc de l'agent]] · code `B2B/agents/prospection.py`
Liens : [[jarvis-ceo]] · [[decision-validation-manuelle]] · [[decision-serveur-hlqstau]]
