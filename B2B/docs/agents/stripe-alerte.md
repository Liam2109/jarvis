---
agent: stripe-alerte
statut: actif
mode: simulation
responsable: Argent
horaire: "toutes les 5 min, plage tous les jours 00:00-24:00"
machine: serveur
tags: [agent-b2b]
---
<!-- GENERE:DEBUT (régénéré par python B2B\harness\generer-fiches.py : ne pas modifier) -->
# stripe-alerte

**Statut :** actif (simulation : envoi_automatique = false) · **Responsable :** [[responsable-argent|Responsable Argent]] · **Machine :** serveur
**Horaire :** toutes les 5 min, plage tous les jours 00:00-24:00
**Script :** `B2B/agents/stripe-alerte.py` · **Contrat :** `B2B/harness/contrats/stripe-alerte.json`

## Mission
Alerter Liam sur Discord à chaque nouveau paiement Stripe réussi, en lecture seule.

## Ce qu'il fait étape par étape
1. `M.exiger("stripe-alerte", ...)` : refuse de tourner si cette machine n'est pas la machine active (sauf `--a-blanc`).
2. Lit les réglages `stripe-alerte-config.json` (+ `.local.json`) : `envoi_automatique` (false par défaut = simulation), `intervalle_minutes` (5).
3. Lit la clé `STRIPE_RESTRICTED_KEY` dans `Jarvis\.env` (jamais affichée). Clé absente : « rien à vérifier », journalisé, code 0.
4. Premier passage (aucun `dernier_ts`) : lit les 10 derniers paiements, les mémorise **sans alerte**, fixe le point de départ.
5. Passages suivants : `GET charges?created[gte]=<dernier_ts>`, garde ceux `paid` + `succeeded` jamais vus, triés par date.
6. Pour chacun : message « Nouveau paiement Stripe : 595 euros (description) » ; posté sur Discord si `envoi_automatique`, sinon affiché « [simulation] ».
7. Mémorise les identifiants vus (300 au plus, garde les 200 plus récents) et le dernier horodatage dans `stripe-alerte-etat.json`.
8. Écrit une trace du harness (`B2B/logs/agents/stripe-alerte/AAAA-MM-JJ.jsonl`) à chaque `verifier` réel.

## Entrées et sorties
**Lit :**
- Stripe charges (clé restreinte, lecture)

**Écrit :**
- B2B/agents/stripe-alerte-etat.json
- B2B/agents/stripe-alerte-journal.log

**Discord :** alertes · **Plafond :** 30 messages par jour · **Envoi au client :** non

## Ce qu'il n'a pas le droit de faire
- envoyer au client sans accord de Liam
- encaisser ou rembourser
- publier
- signer ou promettre un résultat
- afficher un secret (jeton, clé, adresse iCal)
- écrire sur Stripe
- créer un lien de paiement
- Engager Liam (envoyer au client, encaisser, publier, signer) : `peut_engager: false`, tout passe par `B2B/a-valider/`.

## Harness
- **Contrat :** valide (`python B2B\harness\valider.py`)
- **Garde branchée :** oui
- Bloque : kill-switch `B2B\STOP`, lien Stripe non autorisé, phrase interdite (OFFRE-REFERENCE.json), secret dans le texte.
- Avertit : machine non active, envoi_automatique = false (simulation), hors horaires du contrat (00:00-24:00), plafond de 30 messages par jour.
- **Tests :** `B2B/agents/test_stripe_alerte.py`, `tests/agents/test_stripe_alerte.py`
- **Alerte si silence :** après 19:30 (surveillant)

<!-- DYNAMIQUE:DEBUT -->
**Derniers résultats de test (cette machine) :**
- `B2B/agents/test_stripe_alerte.py` : réussi le 2026-11-15 19:35
- `tests/agents/test_stripe_alerte.py` : réussi le 2026-11-15 19:35

**Dernière trace :** aucune

### Historique (5 dernières traces, sans données client)
- aucune trace sur cette machine
<!-- DYNAMIQUE:FIN -->

## Skill
- [[skills/agent-stripe-alerte|agent-stripe-alerte]]

## Liens
- Responsable : [[responsable-argent|Responsable Argent]]
- Direction : [[jarvis-ceo|Jarvis (CEO)]] · [[00-ORGANIGRAMME|Organigramme]]
<!-- GENERE:FIN -->

## Notes de Liam

_Zone libre, conservée telle quelle à chaque régénération._
