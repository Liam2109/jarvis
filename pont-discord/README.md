# pont-discord — bot Discord de Jarvis

Processus séparé, lancé/arrêté par `jarvis.ps1` (seulement si `discord_actif: true`), qui relie Jarvis au salon Discord de Liam.

## Fichiers clés
- `pont.py` — lancement du bot (jeton hérité de `.env`, jamais en argument).
- `pont_logique.py` — logique de filtrage (aucun réseau, testable avec un faux client) : un seul utilisateur, salons listés.
- `notifier.py` — poste un message ponctuel sans passer par Jarvis (appel REST direct).
- `conversation.py` — réponses directes légères (règle locale -> API Anthropic -> repli `claude -p`), aucune commande n'y est traitée.

## Voir aussi
- [lib](../lib/README.md) — `discord.ps1`, `discord-embeds.ps1`
- [CLAUDE.md](../CLAUDE.md)
- [INDEX](../INDEX.md)
