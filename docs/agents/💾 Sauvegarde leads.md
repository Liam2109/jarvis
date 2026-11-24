---
agent: sauvegarde-leads
aliases: [💾 Sauvegarde leads]
name: sauvegarde-leads
role: "Chaque nuit à 03:30, copier leads, appels, résultats d'appels, leads chauds et relances dans B2B/sauvegardes (30 jours) ; archive restaurable pour toute suppression ; sans token."
machine: "serveur"
planification: "chaque jour à 03:30, plage tous les jours 03:30-04:30"
sorties: "B2B/sauvegardes/AAAA-MM-JJ (copies, suppression au-delà de 30 jours), B2B/donnees/archive/archive.jsonl (archive des suppressions), B2B/agents/sauvegarde-leads-journal.log"
responsable: Jarvis (CEO)
statut: actif
mode: réel
horaire: "chaque jour à 03:30, plage tous les jours 03:30-04:30"
tags: [agent-b2b]
---
<!-- GENERE:DEBUT (régénéré par python B2B\harness\generer-fiches.py : ne pas modifier) -->
# 💾 Sauvegarde leads

**Agent :** `sauvegarde-leads` · **Statut :** actif · **Responsable :** Jarvis (CEO) · **Machine :** serveur
**Horaire :** chaque jour à 03:30, plage tous les jours 03:30-04:30
**Script :** `B2B/agents/sauvegarde-leads.py` · **Contrat :** `B2B/harness/contrats/sauvegarde-leads.json`

## Rôle et limites
### Mission
Chaque nuit à 03:30, copier leads, appels, résultats d'appels, leads chauds et relances dans B2B/sauvegardes (30 jours) ; archive restaurable pour toute suppression ; sans token.

### Ce qu'il fait étape par étape
1. `M.exiger("sauvegarde-leads", ...)` : machine active obligatoire (sauf `--a-blanc`, `archives`, `etat`).
2. `sauvegarder` copie dans `B2B/sauvegardes/AAAA-MM-JJ/` (même chemin relatif) : registre des entreprises (résultats d'appels), file des leads chauds, archive, états relances / appels-sid / appels-liam, historique d'appels-sid, `suivi-prospects.csv`, `prospection-trouves.csv`, listes `docs/sid/*.csv`. Fichier absent : passé ; registre absent : échec (code 2).
3. La copie est construite dans un dossier `.tmp` puis échangée, tailles vérifiées : une copie ratée ne détruit jamais la sauvegarde précédente.
4. Supprime seulement les dossiers `AAAA-MM-JJ` de `B2B/sauvegardes` de plus de 30 jours.
5. Archive : `registre.liberer` et la sortie d'un lead de la file des leads chauds écrivent d'abord l'entrée complète dans `B2B/donnees/archive/archive.jsonl` ; `supprimer <registre|leads-chauds> <clé>` est la seule suppression manuelle (archive puis suppression).
6. Restaurer en 3 lignes : `python B2B/agents/sauvegarde-leads.py archives` (liste id, date, nom, raison) ; `python B2B/agents/sauvegarde-leads.py restaurer <id>` (refuse si la clé existe déjà) ; la file des leads chauds est recalculée depuis le registre à chaque passage, un lead restauré là n'y reste que si le registre le justifie encore.
7. Un fichier entier se restaure en copiant celui de `B2B/sauvegardes/<jour>/` à son emplacement d'origine sous `B2B/`.
8. Journal `sauvegarde-leads-journal.log` sans nom ni numéro, trace du harness.

### Ce qu'il n'a pas le droit de faire
- supprimer un lead ou un appel sans l'archiver d'abord
- écraser une entrée existante en restaurant
- toucher à .env, config.json ou un fichier *.local.json
- supprimer autre chose que des dossiers AAAA-MM-JJ de B2B/sauvegardes de plus de 30 jours
- envoyer un message, au client ou sur Discord
- utiliser une IA ou un service payant
- Engager Liam (envoyer au client, encaisser, publier, signer) : `peut_engager: false`, tout passe par `B2B/a-valider/`.

## Entrées et sorties
**Lit :**
- B2B/donnees/registre-entreprises.json
- B2B/donnees/leads-chauds.json
- B2B/donnees/archive/archive.jsonl
- B2B/agents/relances-etat.json
- B2B/agents/appels-sid-etat.json
- B2B/agents/appels-sid-historique.json
- B2B/agents/appels-liam-etat.json
- B2B/suivi-prospects.csv
- B2B/prospection-trouves.csv
- B2B/docs/sid/*.csv

**Écrit :**
- B2B/sauvegardes/AAAA-MM-JJ (copies, suppression au-delà de 30 jours)
- B2B/donnees/archive/archive.jsonl (archive des suppressions)
- B2B/agents/sauvegarde-leads-journal.log

**Discord :** aucun · **Plafond :** 0 messages par jour · **Envoi au client :** non

## Horaire et état
- **Horaire :** chaque jour à 03:30, plage tous les jours 03:30-04:30
- **Tâche serveur :** entrée dans `B2B/agents/serveur-taches.json` ; tourne seulement si l'agent est dans `agents_actifs` (choix de Liam)
- **Contrat :** valide (`python B2B\harness\valider.py`)
- **Garde branchée :** non
- Bloque : kill-switch `B2B\STOP`, lien Stripe non autorisé, phrase interdite (OFFRE-REFERENCE.json), secret dans le texte.
- Avertit : machine non active, envoi_automatique = false (simulation), hors horaires du contrat (03:30-04:30), plafond de 0 messages par jour.
- **Tests :** `tests/agents/test_sauvegarde_leads.py`
- **Alerte si silence :** après 05:00 (surveillant)

<!-- DYNAMIQUE:DEBUT -->
**Derniers résultats de test (cette machine) :**
- `tests/agents/test_sauvegarde_leads.py` : pas encore lancé par `generer-fiches.py --tests`

**Dernière trace :** 2026-11-24 18:56 ok · **Dernière erreur :** aucune · **Dans agents_actifs (cette machine) :** oui

### Historique (5 dernières traces, sans données client)
- 2026-11-24 18:56 | sauvegarder | ok | 0.06 s
<!-- DYNAMIQUE:FIN -->

## Skill et règles
- `.claude/skills/agent-sauvegarde-leads/SKILL.md` (copie : `docs/agents/skills/agent-sauvegarde-leads.md`)
- Pas de preuve = pas de fait : « il a tourné » = une trace du jour `ok: true` ci-dessus ; « c'est corrigé » = ses tests puis `tests\b2b-rapide.ps1` en vert.
<!-- GENERE:FIN -->

## Liens et décisions

_Zone conservée à chaque régénération : liens vers docs\decisions et docs clés seulement._

Liens : aucun pour l'instant.

## Notes de Liam

_Zone libre, conservée telle quelle à chaque régénération._
