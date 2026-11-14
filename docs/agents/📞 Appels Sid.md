---
agent: appels-sid
aliases: [📞 Appels Sid]
name: appels-sid
role: Préparer chaque matin la liste d'appels de Sid (au moins 100 entreprises avec téléphone)
machine: serveur DESKTOP-HLQSTAU (si listé dans agents_actifs)
planification: 08:00 (serveur-taches.json, commande « jour ») ; jours d'appel lundi, mardi, jeudi, vendredi
depend_de: agent-prospection
sorties: docs/sid/liste-sid-AAAA-MM-JJ.csv, feuille Google du jour
---
# 📞 Appels Sid
Tous les appels vont à Sid. Les cases cochées sont lues le soir par agent-resume-sid.
Détail : `B2B/agents/appels-sid.md` · scripts : script d'appel
Liens : [[docs/decisions/📌 Offre 595 + 49|📌 Offre 595 + 49]]
