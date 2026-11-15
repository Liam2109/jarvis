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
