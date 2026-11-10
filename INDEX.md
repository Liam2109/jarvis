# Index — où chercher selon le sujet

Une ligne par domaine, avec le fichier à lire (lui seul, pas tout le dossier). Créé le 10 nov. 2026 (voir `CLAUDE.md` § 9).

| Domaine | Lire |
|---|---|
| Démarrer/arrêter Jarvis, raccourcis, permissions, voix, mémoire, Discord | [README.md](README.md) |
| Règles à respecter dans toute session (ne jamais lancer Jarvis, tests silencieux, `.env`, permissions) | [CLAUDE.md](CLAUDE.md) |
| Réglages de Jarvis (voix, raccourcis, Discord, veilles…) | `config.json` (défaut, suivi par git) + `config.local.json` (secrets/réglages de cette machine, hors git) |
| Journal du jour (ordres, actions, résultats) | `logs\journal-AAAA-MM-JJ.md` |
| Mémoire de Jarvis (to-do, notes, résumé, rappels) | `memoire\todo.md`, `memoire\notes.md`, `memoire\resume.md` |
| Agence B2B (LM MULTI-SERVICES) : règles permanentes, style des sites, ressources PC | [B2B/CLAUDE.md](B2B/CLAUDE.md) |
| Agence B2B : architecture des agents (prospection, appels, rendez-vous, réponses…) | [B2B/ARCHITECTURE-AGENT-B2B.md](B2B/ARCHITECTURE-AGENT-B2B.md) |
| Agence B2B : contexte, offres, prix, décisions prises | [B2B/docs/MEMOIRE-B2B.md](B2B/docs/MEMOIRE-B2B.md) |
| Agence B2B : ce qui reste à faire, par priorité | [B2B/docs/TODO-B2B.md](B2B/docs/TODO-B2B.md) |
| Appels téléphoniques Sid (listes, historique 365 j, Normandie) | `B2B/agents/appels-sid.py` (règles en tête de fichier) |
| Prospection e-mail, lots, zone de recherche (vagues de départements) | `B2B/agents/prospection.py`, `B2B/agents/zone.py` |
| Rendez-vous (agenda, Discord) | `B2B/agents/rendez-vous.py` |
| Sites/pages exemple générés pour les prospects | [B2B/sites/moteur/REGLES-STYLE-SITES.md](B2B/sites/moteur/REGLES-STYLE-SITES.md) (à lire avant toute page) |
| Agent Instagram | [B2B/docs/INSTAGRAM-PLAN.md](B2B/docs/INSTAGRAM-PLAN.md) + `B2B/agents/instagram.py` |
| Pont Discord (bot, salons, cache des identifiants) | `pont-discord/pont_logique.py`, `pont-discord/notifier.py` |
| Veille des annonces de conducteur de train + candidatures | `lib\veille-train.ps1`, `lib\candidatures.ps1`, [emploi/TACHE-EMPLOI-CONDUCTEUR.md](emploi/TACHE-EMPLOI-CONDUCTEUR.md) |
| Voix (synthèse, écoute, réveil) | `voix\ecoute.py`, `voix\piper_serveur.py`, `voix\reveil.py` |
| Tableau de bord / visage (pages HTML du coffre) | `visage\pilotage.html`, `visage\pilotage.js` |
| Tests | `tests\tout.ps1` (tout, silencieux) ; un fichier par module sinon (ex. `tests\rendez-vous.ps1`) ; **jamais** `tests\manuels.ps1` |
| Fichiers isolés par précaution | `quarantaine\` (jamais supprimés automatiquement) |

**Données d'exécution (jamais la doc) :** `lots\`, `memoire\*.json`, `B2B\agents\*-etat.json`, `B2B\agents\*-historique.json`, `B2B\docs\sid\*.csv` — générées par les agents, pas à lire pour comprendre une règle.
