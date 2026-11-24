---
name: agent-sauvegarde-leads
description: Fiche de rôle de l'agent Sauvegarde leads (rattaché à Jarvis CEO) — chaque nuit à 03:30 sur le serveur, copie sans token les fichiers de leads, d'appels, de résultats d'appels, de leads chauds et de relances dans B2B\sauvegardes\AAAA-MM-JJ (30 jours gardés) ; toute suppression de lead ou d'appel passe par une archive restaurable. À utiliser pour vérifier ou corriger sauvegarde-leads.py et archive.py (sauvegarder, archives, restaurer, supprimer, etat).
---

# Agent Sauvegarde leads — le filet de sécurité des leads et des appels

**Responsable :** Jarvis (CEO). **Scripts :** `B2B/agents/sauvegarde-leads.py`, `B2B/agents/archive.py`. **Contrat :** `B2B/harness/contrats/sauvegarde-leads.json`.
**Tâche serveur :** `sauvegarder` chaque jour à 03:30 (`serveur-taches.json`), dans `agents_actifs`.

## Ordres pas à pas (lus dans le script)
1. `M.exiger("sauvegarde-leads", ...)` : machine active obligatoire (sauf `--a-blanc`, `archives`, `etat`).
2. `sauvegarder` copie dans `B2B/sauvegardes/AAAA-MM-JJ/` (même chemin relatif) : registre des entreprises (résultats d'appels), file des leads chauds, archive, états relances / appels-sid / appels-liam, historique d'appels-sid, `suivi-prospects.csv`, `prospection-trouves.csv`, listes `docs/sid/*.csv`. Fichier absent : passé ; registre absent : échec (code 2).
3. La copie est construite dans un dossier `.tmp` puis échangée, tailles vérifiées : une copie ratée ne détruit jamais la sauvegarde précédente.
4. Supprime seulement les dossiers `AAAA-MM-JJ` de `B2B/sauvegardes` de plus de 30 jours.
5. Archive : `registre.liberer` et la sortie d'un lead de la file des leads chauds écrivent d'abord l'entrée complète dans `B2B/donnees/archive/archive.jsonl` ; `supprimer <registre|leads-chauds> <clé>` est la seule suppression manuelle (archive puis suppression).
6. Restaurer en 3 lignes : `python B2B/agents/sauvegarde-leads.py archives` (liste id, date, nom, raison) ; `python B2B/agents/sauvegarde-leads.py restaurer <id>` (refuse si la clé existe déjà) ; la file des leads chauds est recalculée depuis le registre à chaque passage, un lead restauré là n'y reste que si le registre le justifie encore.
7. Un fichier entier se restaure en copiant celui de `B2B/sauvegardes/<jour>/` à son emplacement d'origine sous `B2B/`.
8. Journal `sauvegarde-leads-journal.log` sans nom ni numéro, trace du harness.

## Ce qu'il ne fait jamais
Supprimer un lead sans l'archiver ; écraser une entrée en restaurant ; toucher à `.env`, `config.json` ou `*.local.json` ; envoyer un message ; utiliser une IA ou un service payant.

## Vérifier (pas de preuve = pas de fait)
`python tests/agents/test_sauvegarde_leads.py` puis `tests/b2b-rapide.ps1`.
