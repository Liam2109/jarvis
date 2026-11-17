---
agent: stripe-alerte
aliases: [💶 Alerte Stripe]
name: stripe-alerte
role: Alerte Discord dès qu'un nouveau paiement Stripe arrive (montant seulement)
machine: non planifié sur le serveur (absent de serveur-taches.json)
planification: tâche Windows propre toutes les 5 min, installée seulement par Liam (« installer --oui ») ; aucune sur le gros PC
depend_de: clé Stripe restreinte en lecture seule (Jarvis/.env, jamais affichée)
sorties: message Discord « Nouveau paiement Stripe »
responsable: Argent
statut: actif
mode: simulation
horaire: "toutes les 5 min, plage tous les jours 00:00-24:00"
tags: [agent-b2b]
---
<!-- GENERE:DEBUT (régénéré par python B2B\harness\generer-fiches.py : ne pas modifier) -->
# 💶 Alerte Stripe

**Agent :** `stripe-alerte` · **Statut :** actif (simulation : envoi_automatique = false) · **Responsable :** Argent (pôle) · **Machine :** serveur
**Horaire :** toutes les 5 min, plage tous les jours 00:00-24:00
**Script :** `B2B/agents/stripe-alerte.py` · **Contrat :** `B2B/harness/contrats/stripe-alerte.json`

## Rôle et limites
### Mission
Alerter Liam sur Discord à chaque nouveau paiement Stripe réussi, en lecture seule.

### Ce qu'il fait étape par étape
1. `M.exiger("stripe-alerte", ...)` : refuse de tourner si cette machine n'est pas la machine active (sauf `--a-blanc`).
2. Lit les réglages `stripe-alerte-config.json` (+ `.local.json`) : `envoi_automatique` (false par défaut = simulation), `intervalle_minutes` (5).
3. Lit la clé `STRIPE_RESTRICTED_KEY` dans `Jarvis\.env` (jamais affichée). Clé absente : « rien à vérifier », journalisé, code 0.
4. Premier passage (aucun `dernier_ts`) : lit les 10 derniers paiements, les mémorise **sans alerte**, fixe le point de départ.
5. Passages suivants : `GET charges?created[gte]=<dernier_ts>`, garde ceux `paid` + `succeeded` jamais vus, triés par date.
6. Pour chacun : message « Nouveau paiement Stripe : 595 euros (description) » ; posté sur Discord si `envoi_automatique`, sinon affiché « [simulation] ».
7. Mémorise les identifiants vus (300 au plus, garde les 200 plus récents) et le dernier horodatage dans `stripe-alerte-etat.json`.
8. Écrit une trace du harness (`B2B/logs/agents/stripe-alerte/AAAA-MM-JJ.jsonl`) à chaque `verifier` réel.

### Ce qu'il n'a pas le droit de faire
- envoyer au client sans accord de Liam
- encaisser ou rembourser
- publier
- signer ou promettre un résultat
- afficher un secret (jeton, clé, adresse iCal)
- écrire sur Stripe
- créer un lien de paiement
- Engager Liam (envoyer au client, encaisser, publier, signer) : `peut_engager: false`, tout passe par `B2B/a-valider/`.

## Entrées et sorties
**Lit :**
- Stripe charges (clé restreinte, lecture)

**Écrit :**
- B2B/agents/stripe-alerte-etat.json
- B2B/agents/stripe-alerte-journal.log

**Discord :** alertes · **Plafond :** 30 messages par jour · **Envoi au client :** non

## Horaire et état
- **Horaire :** toutes les 5 min, plage tous les jours 00:00-24:00
- **Tâche serveur :** entrée dans `B2B/agents/serveur-taches.json` ; tourne seulement si l'agent est dans `agents_actifs` (choix de Liam)
- **Contrat :** valide (`python B2B\harness\valider.py`)
- **Garde branchée :** oui
- Bloque : kill-switch `B2B\STOP`, lien Stripe non autorisé, phrase interdite (OFFRE-REFERENCE.json), secret dans le texte.
- Avertit : machine non active, envoi_automatique = false (simulation), hors horaires du contrat (00:00-24:00), plafond de 30 messages par jour.
- **Tests :** `B2B/agents/test_stripe_alerte.py`, `tests/agents/test_stripe_alerte.py`
- **Alerte si silence :** après 19:30 (surveillant)

<!-- DYNAMIQUE:DEBUT -->
**Derniers résultats de test (cette machine) :**
- `B2B/agents/test_stripe_alerte.py` : pas encore lancé par `generer-fiches.py --tests`
- `tests/agents/test_stripe_alerte.py` : pas encore lancé par `generer-fiches.py --tests`

**Dernière trace :** 2026-11-17 01:23 ok · **Dernière erreur :** aucune · **Dans agents_actifs (cette machine) :** oui

### Historique (5 dernières traces, sans données client)
- 2026-11-17 01:23 | verifier | ok | 0.65 s
- 2026-11-17 01:23 | verifier | ok | 0.31 s
- 2026-11-17 01:18 | verifier | ok | 0.6 s
- 2026-11-17 01:18 | verifier | ok | 0.28 s
- 2026-11-17 01:13 | verifier | ok | 0.63 s
<!-- DYNAMIQUE:FIN -->

## Skill et règles
- `.claude/skills/agent-stripe-alerte/SKILL.md` (copie : `docs/agents/skills/agent-stripe-alerte.md`)
- Pas de preuve = pas de fait : « il a tourné » = une trace du jour `ok: true` ci-dessus ; « c'est corrigé » = ses tests puis `tests\b2b-rapide.ps1` en vert.
<!-- GENERE:FIN -->

## Liens et décisions

_Zone conservée à chaque régénération : liens vers docs\decisions et docs clés seulement._

Aucune action sur Stripe : ni remboursement, ni écriture. Jamais de nom, d'e-mail ni de carte dans l'alerte.
Détail : `B2B/agents/stripe-alerte.md`
Liens : [[liens-paiement]]

## Notes de Liam

_Zone libre, conservée telle quelle à chaque régénération._
