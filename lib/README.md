# lib — bibliothèque PowerShell de Jarvis

Fonctions chargées par `jarvis.ps1` ; un fichier = un domaine. Modifications ciblées seulement (fichiers qui fonctionnent).

## Fichiers clés
- `cerveau.ps1` / `cerveau-local.ps1` — ordre -> actions JSON via `claude -p` (aucun outil côté Claude).
- `coffre.ps1` / `coffre-dialogue.ps1` — Bitwarden (jeton en mémoire seulement).
- `matin.ps1` — briefing du matin avec rattrapage.
- `business.ps1` — statut Stripe/Supabase en lecture seule, jamais de chiffre inventé.
- `discord.ps1` / `discord-embeds.ps1` — pont et messages Discord.
- `b2b-serveur.ps1` — tâches planifiées des agents B2B sur le portable serveur.
- `rendez-vous.ps1`, `instagram.ps1`, `devis.ps1`, `prospection.ps1`, `candidatures.ps1`, `veille-train.ps1` — lancent/arrêtent les agents B2B/emploi autonomes.
- `permissions.ps1` — niveaux de permission (1 auto, 2 confirmation, 3 refusé).
- `sons.ps1`, `voix.ps1`, `voix-naturelle.ps1` — sons et synthèse vocale.
- `competences/`, `sources/` — sous-dossiers de compétences et sources additionnelles.

## Voir aussi
- [tests](../tests/README.md)
- [CLAUDE.md](../CLAUDE.md)
- [INDEX](../INDEX.md)
