---
agent: gardien
aliases: [🔍 Gardien]
name: gardien
responsable: Jarvis (CEO)
statut: arrêté
horaire: "chaque jour à 21:00, plage dim 21:00-23:59"
tags: [agent-b2b]
---
<!-- GENERE:DEBUT (régénéré par python B2B\harness\generer-fiches.py : ne pas modifier) -->
# 🔍 Gardien

**Agent :** `gardien` · **Statut :** arrêté · **Responsable :** Jarvis (CEO) · **Machine :** serveur
**Horaire :** chaque jour à 21:00, plage dim 21:00-23:59
**Script :** `B2B/agents/gardien.py` · **Contrat :** `B2B/harness/contrats/gardien.json`

## Rôle et limites
### Mission
Chaque dimanche 21:00 : vérifie agents, fiches, liens et échanges de fichiers ; corrige seul le réversible, archive l'inutile, attend le « go » pour tout envoi.

### Ce qu'il fait étape par étape
à compléter par Liam (aucun skill ne décrit les étapes).

### Ce qu'il n'a pas le droit de faire
- écrire à un prospect, publier, encaisser ou signer
- modifier envoi_automatique ou un réglage d'envoi (aucun fichier de réglages n'est écrit)
- relancer ou archiver un agent qui envoie à un prospect
- réécrire un lien vers docs/decisions
- supprimer définitivement un agent (archive seulement)
- afficher un secret
- Engager Liam (envoyer au client, encaisser, publier, signer) : `peut_engager: false`, tout passe par `B2B/a-valider/`.

## Entrées et sorties
**Lit :**
- B2B/harness/contrats/*.json
- B2B/agents/serveur-taches.json
- B2B/logs/agents (traces)
- docs/agents/*.md (liens)
- B2B/harness/fiches-noms.json

**Écrit :**
- B2B/agents/gardien-etat.json
- B2B/agents/gardien-journal.log
- docs/COMMENT-CA-MARCHE.md
- docs/agents/*.md (fiches générées, liens cassés)
- docs/archives/agents-retires/gardien-archives.json
- B2B/a-valider/AAAA-MM-JJ-gardien.md

**Discord :** alertes · **Plafond :** 1 messages par jour · **Envoi au client :** non

## Horaire et état
- **Horaire :** chaque jour à 21:00, plage dim 21:00-23:59
- **Tâche serveur :** entrée dans `B2B/agents/serveur-taches.json` ; tourne seulement si l'agent est dans `agents_actifs` (choix de Liam)
- **Contrat :** valide (`python B2B\harness\valider.py`)
- **Garde branchée :** oui
- Bloque : kill-switch `B2B\STOP`, lien Stripe non autorisé, phrase interdite (OFFRE-REFERENCE.json), secret dans le texte.
- Avertit : machine non active, envoi_automatique = false (simulation), hors horaires du contrat (21:00-23:59), plafond de 1 messages par jour.
- **Tests :** `tests/agents/test_gardien.py`
- **Alerte si silence :** aucune

<!-- DYNAMIQUE:DEBUT -->
**Derniers résultats de test (cette machine) :**
- `tests/agents/test_gardien.py` : pas encore lancé par `generer-fiches.py --tests`

**Dernière trace :** aucune · **Dernière erreur :** aucune · **Dans agents_actifs (cette machine) :** non (Liam l'ajoute s'il veut le planifier)

### Historique (5 dernières traces, sans données client)
- aucune trace sur cette machine
<!-- DYNAMIQUE:FIN -->

## Skill et règles
- `.claude/skills/agent-gardien/SKILL.md` (copie : `docs/agents/skills/agent-gardien.md`)
- Pas de preuve = pas de fait : « il a tourné » = une trace du jour `ok: true` ci-dessus ; « c'est corrigé » = ses tests puis `tests\b2b-rapide.ps1` en vert.
<!-- GENERE:FIN -->

## Liens et décisions

_Zone conservée à chaque régénération : liens vers docs\decisions et docs clés seulement._

Liens : aucun pour l'instant.

## Notes de Liam

_Zone libre, conservée telle quelle à chaque régénération._
