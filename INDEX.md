# Index — hub du coffre Jarvis
Lire ce fichier, puis **seulement** la note du sujet en cours (jamais tous les docs). Créé le 10 nov. 2026, hub Obsidian depuis le 14 nov. 2026 (`CLAUDE.md` § 9).

## Au centre : [[docs/agents/🧠 Jarvis (CEO)|🧠 Jarvis (CEO)]]
**Agents B2B** : notes dans `docs\agents\` (reliées à Jarvis (CEO) dans le graphe)
**Décisions** : [[docs/decisions/📌 Offre 595 + 49|📌 Offre 595 + 49]] · [[docs/decisions/📌 Sans acompte|📌 Sans acompte]] · [[docs/decisions/📌 Serveur HLQSTAU|📌 Serveur HLQSTAU]] · [[docs/decisions/📌 Validation à la main|📌 Validation à la main]] · [[docs/decisions/📌 INDEX d'abord|📌 INDEX d'abord]]
**Docs clés** : [[liens-paiement]] · [[KIT-RDV-15MIN]] · [[DEVIS-ET-OBJECTIONS]] · [[TODO-B2B]] · [[JOURNAL-B2B]] · [[IDEES-MASTER]]
**Tableau de bord** : `dashboard\index.html` (icône « Jarvis - Mon entreprise »), données `outils\agents-json.py`

## Où chercher selon le sujet
| Domaine | Lire |
|---|---|
| Règles de toute session (ne jamais lancer Jarvis, tests silencieux, `.env`, permissions) | CLAUDE |
| Démarrer/arrêter Jarvis, raccourcis, voix, mémoire, Discord | README |
| Réglages | `config.json` (suivi par git) + `config.local.json` (cette machine, hors git) |
| Journal du jour / mémoire de Jarvis | `logs\journal-AAAA-MM-JJ.md` · `memoire\todo.md`, `notes.md`, `resume.md` |
| Agence B2B : règles permanentes, style des sites, ressources PC | B2B/CLAUDE |
| Agence B2B : architecture des agents | ARCHITECTURE-AGENT-B2B |
| Agence B2B : contexte, offres, prix, décisions | MEMOIRE-B2B · à faire : TODO-B2B · journal : JOURNAL-B2B · idées : IDEES-MASTER |
| Rendez-vous, devis, objections, liens de paiement | KIT-RDV-15MIN · DEVIS-ET-OBJECTIONS · liens-paiement |
| Sites/pages exemple (à lire avant toute page) | REGLES-STYLE-SITES |
| Instagram | INSTAGRAM-PLAN |
| Transfert vers le serveur | TRANSFERT-SERVEUR |
| Pont Discord | `pont-discord/pont_logique.py`, `pont-discord/notifier.py` |
| Veille conducteur de train + candidatures | `lib\veille-train.ps1`, `lib\candidatures.ps1`, TACHE-EMPLOI-CONDUCTEUR |
| Voix (synthèse, écoute, réveil) | `voix\ecoute.py`, `voix\piper_serveur.py`, `voix\reveil.py` |
| Visage / pilotage | `visage\pilotage.html`, `visage\pilotage.js` |
| Tests | `tests\tout.ps1` (silencieux) ou un fichier par module ; **jamais** `tests\manuels.ps1` |
| Fichiers isolés par précaution | `quarantaine\` (jamais supprimés automatiquement) |

**Données d'exécution (jamais la doc, jamais dans le coffre)** : `lots\`, `memoire\*.json`, `B2B\agents\*-etat.json`, `B2B\docs\sid\*.csv`, listes d'appels.


## Lire le graphe (Ctrl+G)
- **Zone 1, Organisation (ocre)** : Jarvis (CEO) au centre, chaque agent en branche autour de lui.
- **Zone 2, Savoir** : décisions en **pétrole**, docs importantes en **brique** (liens de paiement, kit RDV, devis et objections, à faire, journal, idées).
- Un trait = « s'appuie sur » : agent -> sa décision ou sa doc ; décision -> la doc qui la détaille. Pas de flèche, pas de lien retour.
- INDEX relie seulement Jarvis (CEO) et les décisions : c'est l'entrée, pas le centre.
- Masqués : README, CLAUDE, listes d'appels, lots, mémoire, journaux, dashboard, node_modules, sites, notes orphelines.
- Les noms apparaissent en zoomant ; molette pour zoomer, clic sur un point pour ouvrir la note.
- Nouvel agent : créer `docs\agents\<Nom>.md` (avec `agent: <nom>` en tête) et l'ajouter aux liens de Jarvis (CEO).
- Réglages du graphe : `.obsidian\graph.json` (suivi par git, sans secret).
