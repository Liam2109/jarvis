# tests — tests de Jarvis

Tests silencieux (`JARVIS_TEST=1`, copie temporaire de `config.json`, mémoire/journal temporaires) : un fichier par module.

## Fichiers clés
- `tout.ps1` — lance TOUS les tests silencieux, tableau final, code de sortie 0 = tout vert.
- `_outils.ps1` — outils communs (faux serveur HTTP local, bouchons).
- `manuels.ps1` — **jamais lancé par Claude** : vraies fenêtres, vrai bruit, à lancer par Liam seul (`-Oui`).
- un fichier par domaine (ex. `rendez-vous.ps1`, `appels-sid.ps1`, `candidatures.ps1`, `instagram.ps1`, `b2b-serveur.ps1`, `voix.ps1`…), même nom que dans `lib/` ou `B2B/agents/`.

## Voir aussi
- [lib](../lib/README.md)
- [CLAUDE.md](../CLAUDE.md) (règle « aucun test bruyant »)
- [INDEX](../INDEX.md)
