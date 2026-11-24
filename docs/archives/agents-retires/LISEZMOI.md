# Agents retirés du tableau de bord et du graphe (24/11/2026)

Rien n'est supprimé : tout l'historique est dans git. Les fiches Obsidian rangées ici sont ignorées du graphe (`.obsidian/app.json`). Les **scripts** restent dans `B2B/agents/` (des tests et des contrats du harness les citent) ; ils sont simplement absents de la grille Agents (`RETIRES` dans `outils/agents-json.py`) et sans fiche (`null` dans `B2B/harness/fiches-noms.json`). Les copies de leurs skills (`agent-<nom>.md`) sont rangées ici aussi ; les skills d'origine restent dans `.claude/skills/`, et `generer-fiches.py --verifier` échoue si une copie revient dans `docs/agents/skills/` ou manque ici (`RETIRES` dans `B2B/harness/generer-fiches.py`). Pour en réactiver un : retirer son nom de `RETIRES` (les deux listes), remettre sa fiche dans `docs/agents/` et son nom dans `fiches-noms.json`, puis lancer `python B2B\harness\generer-fiches.py` (la copie du skill est régénérée dans `docs/agents/skills/`).

- **appels-liam** : fermé (désactivé sur le serveur) ; la liste de Liam est couverte par la file des leads chauds et les relances.
- **facebook** : jamais construit, aucun script ni fiche ; une idée sans vente à court terme.
- **superviseur-sites** : fermé jusqu'au « go superviseurs », jamais activé ; peu de pages à surveiller avant les premières ventes.
- **superviseur-mail** : fermé, jamais activé ; surveillait l'agent intérim, lui-même pas encore construit.
- **superviseur-videos** : fermé, jamais activé ; la chaîne vidéo reste suivie par le surveillant du harness.
- **jarvis-vue** : fermé, jamais activé ; ne servait que si les cinq superviseurs tournaient, le tableau de bord remplit ce rôle.
- **linkedin** : remplacé par `linkedin-equipe` (lot du jour dans le tableau de bord, Liam envoie lui-même).
- **vente-relances** : doublon de `relances` (le rappel « À rappeler aujourd'hui » à 08:00), jamais construit.
- **registre** : fichier de données du registre des entreprises (`B2B/agents/registre.py`), pas un agent ; il n'a pas de fiche.
