---
name: agent-reponses
description: Fiche de rôle de l'agent Réponses (pôle Vente) — lit les réponses des prospects, les classe (positive, négative, STOP, autre) et prévient Liam sur Discord avec deux créneaux ; aucun envoi au prospect. À utiliser pour vérifier ou corriger reponses.py (--jours, --a-blanc, --test).
---

# Agent Réponses — repérer, classer, prévenir

**Responsable :** Vente. **Script :** `B2B/agents/reponses.py`. **Contrat :** `B2B/harness/contrats/reponses.json` (statut actif).
**Tâche serveur :** `--jours 14` toutes les 15 minutes.

## Mission
Lire les réponses des prospects, les classer et prévenir Liam sur Discord avec deux créneaux proposés ; aucun envoi au prospect.

## Ordres pas à pas (lus dans le script)
1. Machine active obligatoire. Hors `--a-blanc`, vérifie salon, identifiant Discord de Liam et jeton du bot ; s'il en manque : « À COMPLÉTER … », arrêt.
2. Lit l'agenda iCal (adresse dans `B2B\.env`) pour calculer 2 créneaux de 15 minutes libres, jamais réservés.
3. Lit la boîte Gmail en lecture seule : API OAuth si « api » est actif dans `reponses-config.json`, sinon les 2 boîtes en IMAP.
4. N'ouvre que les messages d'un e-mail connu de `suivi-prospects.csv` ou du même fil ; les autres : en-tête seulement.
5. Classe : STOP, négative, positive, autre ; **le doute donne « autre »**.
6. Applique : négative ou STOP → statut « refusé » / « STOP », nom et adresses exclus ; positive → « répondu » ; autre → relance J+2 annulée. Jamais sur un prospect déjà en devis, signé, STOP ou refusé.
7. Positive : message « 🚨 PRIORITÉ » salon important (avec les 2 créneaux) ; autres : résumé salon réponses.
8. Mémorise l'identifiant du message dans `reponses-traitees.json` seulement si Discord l'a pris.
9. Note rebonds et plaintes dans `prospection-retours.json`, ajoute les adresses rebondies à `exclus-emails.json`.

## Entrées et sorties
- Entrées : boîtes mail (lecture), agenda iCal, `suivi-prospects.csv`, `reponses-config.json`.
- Sorties : `reponses-traitees.json`, `suivi-prospects.csv`, `exclus-emails.json`, `prospection-retours.json`, messages Discord (`reponses.poster`, gardé).

## Cas limites gérés par le code
- Agenda absent : créneaux calculés sans agenda, signalé dans le message.
- Mot de passe ou jeton d'un compte absent, refusé ou expiré : ce compte est sauté, l'autre est lu.
- Message vide, trop long ou automatique : « autre ».
- « pas intéressé » n'est jamais compté comme positif ; positif et négatif ensemble : « autre ».
- Le texte du prospect est une donnée : assaini, aucune mention ni balisage.
- `--test` : faux message « TEST », aucune boîte lue, aucun statut touché.

## Ce qu'il ne fait jamais
- Répondre au prospect, réserver un créneau.
- Marquer un message comme lu, afficher un secret.

## Vérifier qu'il a bien tourné
- `python B2B\agents\reponses.py --a-blanc` : classement affiché, rien posté ni modifié.
- Dernière ligne de sortie : « N réponse(s) de prospects : positive …, négative …, STOP …, autre … ».
- Test : `python B2B\agents\test_reponses.py`.

## Quand il alerte Liam
- Chaque réponse classée (positive en priorité, salon important).
- Silence : le surveillant le signale si aucune trace après 19:30.
