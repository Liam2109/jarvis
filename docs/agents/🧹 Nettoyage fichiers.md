---
agent: nettoyage-fichiers
aliases: [🧹 Nettoyage fichiers]
name: nettoyage-fichiers
role: "Chaque jour à 03:00, supprimer les traces B2B/logs/agents et les entrées de JOURNAL-B2B.md de plus de 30 jours, sans token ni réseau."
machine: "serveur"
planification: "chaque jour à 03:00, plage tous les jours 03:00-04:00"
sorties: "B2B/logs/agents, B2B/docs/JOURNAL-B2B.md, B2B/agents/nettoyage-fichiers-journal.log"
responsable: Jarvis (CEO)
statut: actif
mode: réel
horaire: "chaque jour à 03:00, plage tous les jours 03:00-04:00"
tags: [agent-b2b]
---
<!-- GENERE:DEBUT (régénéré par python B2B\harness\generer-fiches.py : ne pas modifier) -->
# 🧹 Nettoyage fichiers

**Agent :** `nettoyage-fichiers` · **Statut :** actif · **Responsable :** Jarvis (CEO) · **Machine :** serveur
**Horaire :** chaque jour à 03:00, plage tous les jours 03:00-04:00
**Script :** `B2B/agents/nettoyage-fichiers.py` · **Contrat :** `B2B/harness/contrats/nettoyage-fichiers.json`

## Mission
Chaque jour à 03:00, supprimer les traces B2B/logs/agents et les entrées de JOURNAL-B2B.md de plus de 30 jours, sans token ni réseau.

## Ce qu'il fait étape par étape
1. `M.exiger("nettoyage-fichiers", ...)` : machine active obligatoire (sauf `--a-blanc`) ; `B2B\STOP` présent = rien supprimé.
2. Limite = aujourd'hui moins 30 jours (`--jours`, borné 1-3650) ; une date égale à la limite est gardée.
3. Traces : dans `B2B/logs/agents/<agent>/`, supprime les fichiers `AAAA-MM-JJ.jsonl` (ou `.json`, compteurs de la garde) datés avant la limite.
4. Journal : dans `B2B/docs/JOURNAL-B2B.md`, retire les lignes `- AAAA-MM-JJ …` datées avant la limite ; en-tête, lignes non datées, BOM et fins de ligne conservés ; écriture atomique.
5. Garde avant chaque suppression : seulement ces deux cibles, jamais un lien ni un fichier protégé.
6. Une ligne de trace du harness et une ligne dans `nettoyage-fichiers-journal.log` par passage (nombres supprimés, refus de la garde).

## Entrées et sorties
**Lit :**
- B2B/logs/agents
- B2B/docs/JOURNAL-B2B.md

**Écrit :**
- B2B/logs/agents
- B2B/docs/JOURNAL-B2B.md
- B2B/agents/nettoyage-fichiers-journal.log

**Discord :** aucun · **Plafond :** 0 messages par jour · **Envoi au client :** non

## Ce qu'il n'a pas le droit de faire
- toucher à B2B/donnees/registre-entreprises.json
- toucher à memoire/
- toucher à .env, config.json ou un fichier *.local.json
- supprimer un fichier hors de B2B/logs/agents et de JOURNAL-B2B.md
- supprimer une trace ou une entrée de 30 jours ou moins
- envoyer au client, encaisser, publier ou signer
- afficher un secret (jeton, clé, adresse iCal)
- Engager Liam (envoyer au client, encaisser, publier, signer) : `peut_engager: false`, tout passe par `B2B/a-valider/`.

## Harness
- **Contrat :** valide (`python B2B\harness\valider.py`)
- **Garde branchée :** non
- Bloque : kill-switch `B2B\STOP`, lien Stripe non autorisé, phrase interdite (OFFRE-REFERENCE.json), secret dans le texte.
- Avertit : machine non active, envoi_automatique = false (simulation), hors horaires du contrat (03:00-04:00), plafond de 0 messages par jour.
- **Tests :** `tests/agents/test_nettoyage_fichiers.py`
- **Alerte si silence :** après 03:30 (surveillant)

<!-- DYNAMIQUE:DEBUT -->
**Derniers résultats de test (cette machine) :**
- `tests/agents/test_nettoyage_fichiers.py` : pas encore lancé par `generer-fiches.py --tests`

**Dernière trace :** aucune

### Historique (5 dernières traces, sans données client)
- aucune trace sur cette machine
<!-- DYNAMIQUE:FIN -->

## Skill
- `.claude/skills/agent-nettoyage-fichiers/SKILL.md` (copie : `docs/agents/skills/agent-nettoyage-fichiers.md`)
<!-- GENERE:FIN -->

## Liens et décisions

_Zone conservée à chaque régénération : liens vers docs\decisions et docs clés seulement._

Liens : aucun pour l'instant.

## Notes de Liam

_Zone libre, conservée telle quelle à chaque régénération._
