# memoire — mémoire persistante de Jarvis

Données d'exécution générées par Jarvis (jamais la doc) : to-do, notes, résumé, état, caches Discord/voix.

## Fichiers clés
- `todo.md`, `notes.md`, `resume.md`, `profil.md` — mémoire texte lue/écrite par Jarvis.
- `etat-jarvis.json`, `arret.json`, `briefing-jour.json` — état de session et rattrapage du matin.
- `discord/`, `discord-salons.json`, `discord-claude.json` — échanges et identifiants de salons Discord.
- `candidatures*.json`, `veille-train.json`, `veille-mail.json` — états des veilles emploi/mail.
- `sourdine.flag`, `jarvis.pid` — indicateurs d'état (sourdine, processus en cours).

## Voir aussi
- [tests](../tests/README.md)
- [INDEX](../INDEX.md) (section « Mémoire de Jarvis »)
