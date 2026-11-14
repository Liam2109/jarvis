---
name: appels-sid
role: Préparer chaque matin la liste d'appels de Sid (au moins 100 entreprises avec téléphone)
machine: serveur DESKTOP-HLQSTAU (si listé dans agents_actifs)
planification: 08:00 (serveur-taches.json, commande « jour ») ; jours d'appel lundi, mardi, jeudi, vendredi
depend_de: "[[agent-prospection]]"
sorties: docs/sid/liste-sid-AAAA-MM-JJ.csv, feuille Google du jour
---
# Agent appels-sid
Tous les appels vont à Sid. Les cases cochées sont lues le soir par [[agent-resume-sid]].
Détail : [[B2B/agents/appels-sid.md|doc de l'agent]] · scripts : [[B2B/docs/SCRIPT-APPEL-SID.md|script d'appel]]
Liens : [[jarvis-ceo]] · [[decision-offre-595-49]]
