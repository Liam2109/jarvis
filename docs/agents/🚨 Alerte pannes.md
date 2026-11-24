---
agent: panne-alerte
aliases: [🚨 Alerte pannes]
name: panne-alerte
role: "Alerter Liam sur Discord quand un agent planifié à heure fixe n'a pas tourné après son délai de grâce, une seule fois par jour."
machine: "serveur"
planification: "toutes les 5 min, plage tous les jours 00:00-24:00"
sorties: "B2B/agents/panne-alerte-etat.json, B2B/agents/panne-alerte-journal.log"
responsable: Jarvis (CEO)
statut: actif
mode: simulation
horaire: "toutes les 5 min, plage tous les jours 00:00-24:00"
tags: [agent-b2b]
---
<!-- GENERE:DEBUT (régénéré par python B2B\harness\generer-fiches.py : ne pas modifier) -->
# 🚨 Alerte pannes

**Agent :** `panne-alerte` · **Statut :** actif (simulation : envoi_automatique = false) · **Responsable :** Jarvis (CEO) · **Machine :** serveur
**Horaire :** toutes les 5 min, plage tous les jours 00:00-24:00
**Script :** `B2B/agents/panne-alerte.py` · **Contrat :** `B2B/harness/contrats/panne-alerte.json`

## Rôle et limites
### Mission
Alerter Liam sur Discord quand un agent planifié à heure fixe n'a pas tourné après son délai de grâce, une seule fois par jour.

### Ce qu'il fait étape par étape
1. `M.exiger("panne-alerte", ...)` : machine active obligatoire (sauf `--a-blanc`).
2. Réglages `panne-alerte-config.json` (+ `.local.json`) : `envoi_automatique` (false = simulation), `intervalle_minutes` (5), `grace_minutes` (15, borné 0-240).
3. Construit la liste des agents avec `outils\agents-json.py` (`construire()["agents"]`) : nom, planifié, horaire, dernier passage.
4. Ne garde que les agents planifiés « chaque jour à HH:MM » (ex. appels-sid 07:30, resume-sid 19:30) ; les agents « toutes les N minutes » ne sont pas concernés.
5. Panne = heure prévue + délai de grâce dépassée et aucun passage aujourd'hui.
6. Pour chaque panne pas encore alertée aujourd'hui : « ⚠️ Panne : <agent> — aucune exécution aujourd'hui (prévue HH:MM) », postée (mode réel) ou affichée (simulation), journalisée.
7. Mémorise les alertes du jour dans `panne-alerte-etat.json` (30 jours gardés).

### Ce qu'il n'a pas le droit de faire
- envoyer au client sans accord de Liam
- encaisser ou rembourser
- publier
- signer ou promettre un résultat
- afficher un secret (jeton, clé, adresse iCal)
- relancer un agent
- Engager Liam (envoyer au client, encaisser, publier, signer) : `peut_engager: false`, tout passe par `B2B/a-valider/`.

## Entrées et sorties
**Lit :**
- outils/agents-json.py
- journaux des agents
- B2B/agents/serveur-taches.json
- B2B/agents/b2b.local.json (agents_actifs)
- B2B/agents/<agent>-config.json et sa variante locale (verrous go_*, booléens seulement)

**Écrit :**
- B2B/agents/panne-alerte-etat.json
- B2B/agents/panne-alerte-journal.log

**Discord :** alertes · **Plafond :** 10 messages par jour · **Envoi au client :** non

## Horaire et état
- **Horaire :** toutes les 5 min, plage tous les jours 00:00-24:00
- **Tâche serveur :** entrée dans `B2B/agents/serveur-taches.json` ; tourne seulement si l'agent est dans `agents_actifs` (choix de Liam)
- **Contrat :** valide (`python B2B\harness\valider.py`)
- **Garde branchée :** oui
- Bloque : kill-switch `B2B\STOP`, lien Stripe non autorisé, phrase interdite (OFFRE-REFERENCE.json), secret dans le texte.
- Avertit : machine non active, envoi_automatique = false (simulation), hors horaires du contrat (00:00-24:00), plafond de 10 messages par jour.
- **Tests :** `tests/agents/test_panne_alerte.py`
- **Alerte si silence :** après 19:40 (surveillant)

<!-- DYNAMIQUE:DEBUT -->
**Derniers résultats de test (cette machine) :**
- `tests/agents/test_panne_alerte.py` : pas encore lancé par `generer-fiches.py --tests`

**Dernière trace :** 2026-11-24 19:31 ok · **Dernière erreur :** aucune · **Dans agents_actifs (cette machine) :** oui

### Historique (5 dernières traces, sans données client)
- 2026-11-24 19:31 | verifier | ok | 2.08 s
- 2026-11-24 19:26 | verifier | ok | 2.94 s
- 2026-11-24 19:21 | verifier | ok | 2.45 s
- 2026-11-24 19:16 | verifier | ok | 3.62 s
- 2026-11-24 19:11 | verifier | ok | 2.13 s
<!-- DYNAMIQUE:FIN -->

## Skill et règles
- `.claude/skills/agent-panne-alerte/SKILL.md` (copie : `docs/agents/skills/agent-panne-alerte.md`)
- Pas de preuve = pas de fait : « il a tourné » = une trace du jour `ok: true` ci-dessus ; « c'est corrigé » = ses tests puis `tests\b2b-rapide.ps1` en vert.
<!-- GENERE:FIN -->

## Liens et décisions

_Zone conservée à chaque régénération : liens vers docs\decisions et docs clés seulement._

Liens : aucun pour l'instant.

## Notes de Liam

_Zone libre, conservée telle quelle à chaque régénération._
