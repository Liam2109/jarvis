---
agent: appels-sid
aliases: [📞 Appels Sid]
name: appels-sid
role: Préparer chaque matin la liste d'appels de Sid (au moins 100 entreprises avec téléphone)
machine: serveur DESKTOP-HLQSTAU (si listé dans agents_actifs)
planification: 08:00 (serveur-taches.json, commande « jour ») ; jours d'appel du lundi au vendredi
depend_de: agent-prospection
responsable: prospection
sorties: docs/sid/liste-sid-AAAA-MM-JJ.csv, tableur Google « Appels AAAA-MM-JJ » dans le dossier de Sid
---
# 📞 Appels Sid
Tous les appels vont à Sid. La colonne Résultat (Pas de réponse, À rappeler, RDV pris, Non catégorique, Je dois réfléchir, Trop cher, Déjà un site, Pas le temps) est lue le soir par agent-resume-sid.
Détail : `B2B/agents/appels-sid.md` · scripts : script d'appel
Responsable : Prospection (`.claude/skills/responsable-prospection/SKILL.md`) · fiche : `.claude/skills/agent-appels-sid/SKILL.md`
Liens : [[docs/decisions/📌 Offre 595 + 49|📌 Offre 595 + 49]]
