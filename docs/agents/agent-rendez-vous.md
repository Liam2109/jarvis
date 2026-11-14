---
name: rendez-vous
role: Surveiller l'agenda (iCal, lecture seule) et annoncer sur Discord les rendez-vous de 15 min réservés, déplacés, annulés, plus un rappel 30 min avant
machine: serveur DESKTOP-HLQSTAU (si listé dans agents_actifs)
planification: toutes les 5 min (serveur-taches.json, commande « jour »)
depend_de: adresse iCal (hors git)
sorties: salon Discord « rendez-vous », rendez-vous-etat.json
---
# Agent rendez-vous
Lecture seule : n'écrit jamais dans l'agenda. Le rendez-vous suit le [[B2B/docs/KIT-RDV-15MIN.md|kit du rendez-vous]].
Détail : [[B2B/agents/rendez-vous.md|doc de l'agent]]
Liens : [[jarvis-ceo]] · [[agent-devis]]
