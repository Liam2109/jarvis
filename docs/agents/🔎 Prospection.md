---
agent: prospection
aliases: [🔎 Prospection]
name: prospection
role: Trouver des entreprises (bâtiment d'abord, Normandie puis France), un contact public, préparer les lots ; envoyer seulement ce que Liam valide
machine: serveur DESKTOP-HLQSTAU (si listé dans agents_actifs)
planification: toutes les 10 min (serveur-taches.json, commande « jour »)
depend_de: agent-reponses
responsable: prospection
sorties: lots, prospection-etat.json, messages Discord à valider
---
# 🔎 Prospection
Rien ne part sans le « ok lot » de Liam ; `prospection_actif` = non sur le gros PC.
Détail : `B2B/agents/prospection.md` · code `B2B/agents/prospection.py`
Responsable : Prospection (`.claude/skills/responsable-prospection/SKILL.md`). Script partagé par deux agents : Recherche (`.claude/skills/agent-recherche/SKILL.md`) et Lots d'e-mails (`.claude/skills/agent-lots-emails/SKILL.md`).
Liens : [[docs/decisions/📌 Validation à la main|📌 Validation à la main]]
