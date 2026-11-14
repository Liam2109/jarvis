---
agent: rendez-vous
aliases: [Rendez-vous]
name: rendez-vous
role: Surveiller l'agenda (iCal, lecture seule) et annoncer sur Discord les rendez-vous de 15 min réservés, déplacés, annulés, plus un rappel 30 min avant
machine: serveur DESKTOP-HLQSTAU (si listé dans agents_actifs)
planification: toutes les 5 min (serveur-taches.json, commande « jour »)
depend_de: adresse iCal (hors git)
sorties: salon Discord « rendez-vous », rendez-vous-etat.json
---
# Rendez-vous
Lecture seule : n'écrit jamais dans l'agenda. Le rendez-vous suit le kit du rendez-vous.
Détail : `B2B/agents/rendez-vous.md`
Liens : [[KIT-RDV-15MIN]]
