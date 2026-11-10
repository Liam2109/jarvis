# Agent stripe-alerte (9 nov. 2026)
Rôle : une **alerte Discord dès qu'un nouveau paiement Stripe arrive**, sans attendre le résumé du soir (`resume-sid`). Lecture seule (clé Stripe **restreinte**, `STRIPE_RESTRICTED_KEY` de `Jarvis\.env`, déjà utilisée par le briefing vocal — `lib\business.ps1`) : **aucune action sur Stripe**, aucun remboursement, aucune écriture. Code : `agents\stripe-alerte.py` ; tests : `agents\test_stripe_alerte.py` + `tests\stripe-alerte.ps1` (listé dans `tests\tout.ps1`) ; réglages : `agents\stripe-alerte-config.json` ; état : `agents\stripe-alerte-etat.json` ; journal : `agents\stripe-alerte-journal.log`.

**Simulation par défaut** (`envoi_automatique: false`) : chaque nouveau paiement est affiché en console et journalisé, **rien sur Discord**.

## Commandes
| Commande | Effet |
|---|---|
| `python agents\stripe-alerte.py verifier [--a-blanc]` | Une vérification : compare les paiements Stripe réussis à ceux déjà vus, alerte chaque nouveau, un par un, dans l'ordre. C'est ce que lance la tâche planifiée (répétée toutes les `intervalle_minutes` minutes, 5 par défaut). `--a-blanc` : affiche ce qui serait fait, n'écrit rien. |
| `etat` | Date du dernier paiement vu, nombre d'identifiants mémorisés. |
| `installer-tache` / `retirer-tache` `[--oui]` | Tâche planifiée Windows. **Sans `--oui` : affiche seulement la commande PowerShell, n'exécute rien.** |

## Premier passage : jamais une rafale d'alertes sur l'historique
Au tout premier lancement (aucun point de départ encore enregistré dans `stripe-alerte-etat.json`), l'agent lit les derniers paiements existants, les mémorise comme déjà vus, et **n'alerte rien** : ce sont des paiements d'avant l'activation, pas des nouveautés. Le journal le dit (« premier passage : point de départ fixé »). Les passages suivants n'alertent que les paiements **créés depuis le dernier passage**, réussis (`paid` et `status=succeeded`), jamais deux fois le même (identifiant Stripe mémorisé, jusqu'à 300 gardés). Clé absente, refusée ou Stripe injoignable : rien n'est inventé, code de sortie 2, le prochain passage réessaie.

## Le message Discord
Uniquement un **montant**, une **devise** et, si Stripe en fournit une, une **description courte** du paiement (max 80 caractères) — jamais un nom, un e-mail ou un numéro de carte. Exemple : « Nouveau paiement Stripe : 297,00 euros (Acompte 30 % du site complet) ».

## Pour l'activer (Liam)
1. `STRIPE_RESTRICTED_KEY` renseignée dans `Jarvis\.env` (voir `.env.example`) ; une clé **restreinte** (lecture seule sur les paiements suffit), jamais la clé secrète complète.
2. **Jamais dans `agents\stripe-alerte-config.json`** (fichier versionné, poussé sur GitHub) : `envoi_automatique: true` se met dans `agents\stripe-alerte-config.local.json` (créé à la main, ignoré par git, propre à cette machine). Le fichier versionné reste `envoi_automatique: false`.
3. `python agents\stripe-alerte.py verifier` une première fois à la main, pour fixer le point de départ SANS alerter sur l'historique (vérifier que la console dit bien « premier passage »).
4. `python agents\stripe-alerte.py installer-tache --oui` (vérification toutes les `intervalle_minutes` minutes).
5. Contrôle : `python agents\stripe-alerte.py etat`, le journal, le salon Discord habituel au prochain vrai paiement.
