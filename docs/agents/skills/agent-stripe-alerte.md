---
name: agent-stripe-alerte
description: Fiche de rôle de l'agent Alerte Stripe (pôle Argent) — alerte Liam sur Discord à chaque nouveau paiement Stripe réussi, en lecture seule. À utiliser pour vérifier, corriger ou expliquer stripe-alerte.py (verifier, etat).
---

# Agent Alerte Stripe — un paiement, une alerte

**Responsable :** Argent. **Script :** `B2B/agents/stripe-alerte.py`. **Contrat :** `B2B/harness/contrats/stripe-alerte.json`.
**Tâche serveur :** `verifier` toutes les 5 minutes (`B2B/agents/serveur-taches.json`).

## Mission
Alerter Liam sur Discord à chaque nouveau paiement Stripe réussi, en lecture seule.

## Ordres pas à pas (lus dans le script)
1. `M.exiger("stripe-alerte", ...)` : refuse de tourner si cette machine n'est pas la machine active (sauf `--a-blanc`).
2. Lit les réglages `stripe-alerte-config.json` (+ `.local.json`) : `envoi_automatique` (false par défaut = simulation), `intervalle_minutes` (5).
3. Lit la clé `STRIPE_RESTRICTED_KEY` dans `Jarvis\.env` (jamais affichée). Clé absente : « rien à vérifier », journalisé, code 0.
4. Premier passage (aucun `dernier_ts`) : lit les 10 derniers paiements, les mémorise **sans alerte**, fixe le point de départ.
5. Passages suivants : `GET charges?created[gte]=<dernier_ts>`, garde ceux `paid` + `succeeded` jamais vus, triés par date.
6. Pour chacun : message « Nouveau paiement Stripe : 595 euros (description) » ; posté sur Discord si `envoi_automatique`, sinon affiché « [simulation] ».
7. Mémorise les identifiants vus (300 au plus, garde les 200 plus récents) et le dernier horodatage dans `stripe-alerte-etat.json`.
8. Écrit une trace du harness (`B2B/logs/agents/stripe-alerte/AAAA-MM-JJ.jsonl`) à chaque `verifier` réel.

## Entrées et sorties
- Entrées : API Stripe `charges` (GET seulement), `Jarvis\.env` (clé restreinte), réglages.
- Sorties : message Discord (salon habituel des agents, via `prospection.discord`, donc via la garde), `stripe-alerte-etat.json`, `stripe-alerte-journal.log`, trace.

## Cas limites gérés par le code
- Clé refusée (HTTP 401/403) ou Stripe injoignable : message clair, code 2, le prochain passage réessaie ; rien n'est inventé.
- Un paiement n'est jamais alerté deux fois (identifiant mémorisé).
- Premier lancement : pas de rafale d'alertes pour l'historique.
- État illisible : arrêt sans rien écrire (« corrigez ou supprimez le fichier à la main »).
- `--a-blanc` : affiche ce qui serait alerté, n'écrit rien.

## Ce qu'il ne fait jamais
- Écrire sur Stripe, rembourser, créer un lien de paiement (clé restreinte en lecture).
- Mettre un nom, un e-mail ou un numéro de carte dans le message : montant, devise et description courte seulement.
- Afficher la clé.

## Vérifier qu'il a bien tourné
- `python B2B\agents\stripe-alerte.py etat` : dernier paiement vu et nombre mémorisé.
- Dernière ligne de `B2B\agents\stripe-alerte-journal.log` et trace du jour.
- Tests : `python B2B\agents\test_stripe_alerte.py` et `python tests\agents\test_stripe_alerte.py`.

## Quand il alerte Liam
- À chaque nouveau paiement réussi (mode réel seulement).
- Silence prolongé : le surveillant signale l'agent si aucune trace après 19:30 (`alerte_si_silence`).
