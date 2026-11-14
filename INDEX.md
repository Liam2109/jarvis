# Index — hub du coffre Jarvis
Lire ce fichier, puis **seulement** la note du sujet en cours (jamais tous les docs). Créé le 10 nov. 2026, hub Obsidian depuis le 14 nov. 2026 (`CLAUDE.md` § 9).

## Au centre : [[jarvis-ceo|Jarvis (CEO)]]
**Agents B2B** : [[agent-prospection|prospection]] · [[agent-appels-sid|appels-sid]] · [[agent-rendez-vous|rendez-vous]] · [[agent-reponses|réponses]] · [[agent-devis|devis]] · [[agent-instagram|instagram]] · [[agent-page-exemple|page-exemple]] · [[agent-stripe-alerte|stripe-alerte]] · [[agent-resume-sid|resume-sid]]
**Décisions** : [[decision-serveur-hlqstau|serveur DESKTOP-HLQSTAU]] · [[decision-offre-595-49|offre 595 € + 49 €/mois]] · [[decision-sans-acompte|sans acompte]] · [[decision-validation-manuelle|validation à la main]] · [[decision-index-d-abord|INDEX d'abord]]
**Tableau de bord** : `dashboard\index.html` (icône « Jarvis - Mon entreprise »), données `outils\agents-json.py`

## Où chercher selon le sujet
| Domaine | Lire |
|---|---|
| Règles de toute session (ne jamais lancer Jarvis, tests silencieux, `.env`, permissions) | [[CLAUDE.md\|CLAUDE]] |
| Démarrer/arrêter Jarvis, raccourcis, voix, mémoire, Discord | [[README.md\|README]] |
| Réglages | `config.json` (suivi par git) + `config.local.json` (cette machine, hors git) |
| Journal du jour / mémoire de Jarvis | `logs\journal-AAAA-MM-JJ.md` · `memoire\todo.md`, `notes.md`, `resume.md` |
| Agence B2B : règles permanentes, style des sites, ressources PC | [[B2B/CLAUDE.md\|B2B/CLAUDE]] |
| Agence B2B : architecture des agents | [[B2B/ARCHITECTURE-AGENT-B2B.md\|ARCHITECTURE-AGENT-B2B]] |
| Agence B2B : contexte, offres, prix, décisions | [[MEMOIRE-B2B]] · à faire : [[TODO-B2B]] · journal : [[JOURNAL-B2B]] · idées : [[IDEES-MASTER]] |
| Rendez-vous, devis, objections, liens de paiement | [[KIT-RDV-15MIN]] · [[DEVIS-ET-OBJECTIONS]] · [[liens-paiement]] |
| Sites/pages exemple (à lire avant toute page) | [[REGLES-STYLE-SITES]] |
| Instagram | [[INSTAGRAM-PLAN]] |
| Transfert vers le serveur | [[TRANSFERT-SERVEUR]] |
| Pont Discord | `pont-discord/pont_logique.py`, `pont-discord/notifier.py` |
| Veille conducteur de train + candidatures | `lib\veille-train.ps1`, `lib\candidatures.ps1`, [[TACHE-EMPLOI-CONDUCTEUR]] |
| Voix (synthèse, écoute, réveil) | `voix\ecoute.py`, `voix\piper_serveur.py`, `voix\reveil.py` |
| Visage / pilotage | `visage\pilotage.html`, `visage\pilotage.js` |
| Tests | `tests\tout.ps1` (silencieux) ou un fichier par module ; **jamais** `tests\manuels.ps1` |
| Fichiers isolés par précaution | `quarantaine\` (jamais supprimés automatiquement) |

**Données d'exécution (jamais la doc, jamais dans le coffre)** : `lots\`, `memoire\*.json`, `B2B\agents\*-etat.json`, `B2B\docs\sid\*.csv`, listes d'appels.

Dossiers : [[B2B/README.md\|B2B]] · [[B2B/agents/README.md\|B2B/agents]] · [[B2B/docs/README.md\|B2B/docs]] · [[docs/README.md\|docs]] · [[lib/README.md\|lib]] · [[tests/README.md\|tests]] · [[voix/README.md\|voix]]
