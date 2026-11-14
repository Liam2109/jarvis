---
agent: reponses
aliases: [Réponses]
name: reponses
role: Trier les réponses reçues aux e-mails et tenir la liste d'exclusion (STOP, refus)
machine: serveur DESKTOP-HLQSTAU (si listé dans agents_actifs)
planification: toutes les 15 min (serveur-taches.json, « --jours 14 »)
depend_de: agent-prospection
sorties: reponses-traitees.json, exclus-emails.json (hors git)
---
# Réponses
Un « STOP » est définitif : l'adresse ne sera plus jamais contactée.
Détail : `B2B/agents/reponses.md`
Liens : [[docs/decisions/Validation à la main|Validation à la main]]
