# Harness B2B (15/11/2026)

Contrats, garde, traces et tests de chaque agent, sans token ni réseau. Inventaire : `INVENTAIRE.md`. État : `python B2B\harness\rapport.py`.

- **Référence** : `B2B\docs\OFFRE-REFERENCE.json` (prix, 2 liens Stripe, phrases interdites, 8 valeurs de Résultat, horaires). Contrôle : `python tests\coherence-offre.py` ; fautes anciennes listées dans `B2B\harness\coherence-connus.json` (avertissent).
- **Garde** (`B2B\harness\garde.py`, `garde.ps1`) avant chaque envoi. BLOQUE : `B2B\STOP`, lien Stripe non autorisé, phrase interdite, secret, envoi client hors lundi-vendredi 08:00-19:00. Avertit : machine non active, simulation, horaires du contrat, plafond du jour.
- **Traces** : `B2B\logs\agents\<agent>\AAAA-MM-JJ.jsonl` (hors git). **Surveillant** : 19:45 chaque jour et 07:50 le lundi, silence si tout va bien.
- **Ce qui engage Liam** (envoyer au client, encaisser, publier, signer) va dans `B2B\a-valider\AAAA-MM-JJ-<agent>.md`.
- **Tests** : `tests\b2b-rapide.ps1` (moins de 60 s, usage quotidien) ; série `harness.ps1` dans `tests\tout.ps1`.

## Ajouter un agent (checklist)
1. **Contrat** : `B2B\harness\contrats\<agent>.json` valide (`python B2B\harness\valider.py`), `peut_engager: false`.
2. **Garde** : chaque envoi passe par `prospection.discord`, `garde_harness(...)` ou `garde.avant_envoi(...)` ; rien n'engage Liam sans `B2B\a-valider`.
3. **Trace** : une ligne par exécution (`traces.ecrire` ou lanceur `serveur-b2b.ps1`), nom du commerce seulement.
4. **Test** : `tests\agents\test_<agent>.py` avec fixtures dans `tests\fixtures`, sans réseau, listé dans le contrat.
5. **Tâche** : entrée dans `B2B\agents\serveur-taches.json`, puis l'agent ajouté à `agents_actifs` du serveur par Liam.
6. **Skill** : `.claude\skills\agent-<agent>\SKILL.md` (rôle, limites, « pas de preuve = pas de fait »), relié à Jarvis (CEO).

Nouvel agent = contrat + skill + une entrée dans `B2B\harness\fiches-noms.json` (agent -> nom de la note) + un lien dans `docs\agents\🧠 Jarvis (CEO).md`, puis `python B2B\harness\generer-fiches.py`. La fiche détaillée est écrite dans le bloc GENERE de la note `docs\agents\<nom de la note>.md` (un seul graphe Obsidian, aucun lien vers un autre agent ; zones « Liens et décisions » et « Notes de Liam » conservées) ; les skills sont copiés dans `docs\agents\skills\`. Vérifié par `tests\b2b-rapide.ps1` : `generer-fiches.py --verifier` et `B2B\harness\graphe.py` (aucun lien cassé, liens vers les décisions identiques à git, une seule composante).

## Agents vidéo (17/11/2026)
Même harnais que le B2B : contrat `videos-*.json`, garde du contenu `C.garde_harness` (secret, phrase interdite, lien Stripe ; `B2B\STOP` bloque la publication, pas la fabrication), une trace par exécution (`C.lancer` dans `Videos\agents\commun.py`, `Fin` dans `nettoyage.ps1`), tests dans `tests\agents\test_videos.py`. Fiche des agents en 4 rubriques (rôle et limites, entrées et sorties, horaire et état, skill et règles) ; ordre de la chaîne : `CHAINE_VIDEO` dans `generer-fiches.py`, qui écrit aussi `docs\agents\⛓️ Chaîne vidéo.md` (reliée à Jarvis (CEO)).
Sources consultées avant de construire (17/11/2026), rien copié : format SKILL.md de github.com/anthropics/skills (Apache 2.0 pour les skills de documents, licence à vérifier skill par skill) et github.com/agentskills/agentskills (code Apache 2.0, docs CC-BY-4.0) : frontmatter `name` + `description` « quand l'utiliser », déjà appliqué ici ; listes github.com/Picrew/awesome-agent-harness et github.com/walkinglabs/awesome-harness-engineering (pistes : traces JSONL, garde-fous, contrats). Notre format (contrat JSON + schéma, garde, trace JSONL, fiche générée) couvre déjà ces idées : pas d'outil externe ajouté.
