---
name: agent-relances
description: Fiche de rôle de l'agent Relances leads (pôle Vente, actif) — chaque jour ouvré à 08:00 (commande rappel : relance due ou en retard) et 08:30 (commande jour : relance datée exactement d'aujourd'hui), un seul message Discord « À rappeler aujourd'hui » pour Liam avec les leads chauds notés par Sid (À rappeler, Je dois réfléchir) : relance 1 au 3e jour ouvré, relance 2 au 7e, une seule au 15e si la note dit « moyen terme » ou « semaines » ; ne contacte que Liam, sans IA ni token. À utiliser pour vérifier ou corriger relances.py (jour, --essai, etat).
---

# Agent Relances leads — Liam rappelle lui-même ses leads chauds

**Responsable :** Vente. **Script :** `B2B/agents/relances.py`. **Contrat :** `B2B/harness/contrats/relances.json`.
**Tâche serveur :** `rappel` puis `jour` à 08:00, lundi-vendredi (`B2B/agents/serveur-taches.json`), dans `agents_actifs`.
Différent de l'agent prévu `vente-relances` (relance des devis envoyés, pas construit).

## Ordres pas à pas (lus dans le script)
1. `M.exiger("relances", ...)` : refuse hors de la machine active (sauf `--essai`).
2. Jour non ouvré (samedi, dimanche, l'un des 11 jours fériés nationaux, Pâques calculé) : rien, code 0.
3. Lit **toutes** les feuilles « Appels Sid AAAA-MM-JJ » du dossier de Sid (`dossier_sid_id` d'appels-sid, jeton Google d'appels-sid, lecture seule). Date de l'appel = date du nom de la feuille.
4. Un lead = un numéro de téléphone (normalisé, +33 accepté ; sans numéro : ignoré). Dernier résultat chaud (« À rappeler », « Je dois réfléchir ») gardé avec nom, ville, note.
5. Exclu si une feuille **plus récente** note ce numéro « RDV pris », « Non catégorique », « Trop cher », « Déjà un site » ou « Pas le temps » (« Pas de réponse » n'exclut pas).
6. Rythme : relance 1 au 3e jour ouvré après l'appel, relance 2 au 7e, puis classé. Note avec « moyen terme » ou « semaines » : une seule relance au 15e. Passage manqué : la relance la plus récente déjà due part le jour ouvré suivant (jamais une relance 1 après la 2). Nouvel appel chaud de Sid : nouveau cycle.
7. Un seul message « À rappeler aujourd'hui » (nom, ville, téléphone, relance n, date d'appel, note de Sid) ; aucun message s'il n'y a rien. Découpé seulement s'il dépasse la taille Discord.
8. `relances-etat.json` : chaque relance annoncée (numéro|date d'appel|n), jamais deux fois ; marquée seulement si Discord a bien reçu (sinon réessayée au prochain passage). Journal sans nom ni numéro, trace du harness.

9. Commande `rappel` (08:00, 24/11/2026) : lit la file `B2B/donnees/leads-chauds.json` (pas les feuilles Google) et poste « À rappeler aujourd'hui » avec les leads dont la relance est due aujourd'hui ou en retard (retard en jours, date de dernière mise à jour) ; aucun état, refait chaque jour tant que le lead est en retard. Le message de la commande `jour` (08:30) ne liste plus que les leads dont la relance est datée exactement d'aujourd'hui (plus de rattrapage).

## Ce qu'il ne fait jamais
Contacter un prospect, un client ou Sid ; écrire dans une feuille ; utiliser une IA ou un service payant ; afficher un jeton.

## Vérifier (pas de preuve = pas de fait)
- `python B2B\agents\relances.py jour --essai` (ou `--jour AAAA-MM-JJ --essai`) : lit les vraies feuilles, affiche le message, n'écrit ni n'envoie rien.
- `python B2B\agents\relances.py etat` ; dernière ligne de `relances-journal.log` ; trace du jour.
- Tests : `python tests\agents\test_relances.py` (cas de référence Envog 19/11 et 25/11, Garage du Rond Point au 15e jour ouvré, week-end, fériés, RDV pris, doublon), puis `tests\b2b-rapide.ps1`.

## Limite connue
Liam ne note pas encore ses propres rappels : un lead qu'il a déjà rappelé reste dans le cycle jusqu'à la relance 2, sauf si Sid le note ensuite (RDV pris, etc.).
