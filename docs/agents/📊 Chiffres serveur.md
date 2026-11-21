---
agent: chiffres-serveur
aliases: [📊 Chiffres serveur]
name: chiffres-serveur
role: "Tous les soirs à 19:30, une ligne dans la feuille Google « Chiffres serveur Jarvis » : date, devis envoyés, paiements reçus. Aucun montant, aucune donnée client."
machine: "serveur"
planification: "chaque jour à 19:30, plage tous les jours 19:00-23:59"
sorties: "feuille Google « Chiffres serveur Jarvis » (une ligne par soir : date, devis envoyés, paiements reçus), B2B/agents/chiffres-serveur-etat.json, B2B/agents/chiffres-serveur-journal.log"
responsable: Argent
statut: arrêté
horaire: "chaque jour à 19:30, plage tous les jours 19:00-23:59"
tags: [agent-b2b]
---
<!-- GENERE:DEBUT (régénéré par python B2B\harness\generer-fiches.py : ne pas modifier) -->
# 📊 Chiffres serveur

**Agent :** `chiffres-serveur` · **Statut :** arrêté · **Responsable :** Argent (pôle) · **Machine :** serveur
**Horaire :** chaque jour à 19:30, plage tous les jours 19:00-23:59
**Script :** `B2B/agents/chiffres-serveur.py` · **Contrat :** `B2B/harness/contrats/chiffres-serveur.json`

## Rôle et limites
### Mission
Tous les soirs à 19:30, une ligne dans la feuille Google « Chiffres serveur Jarvis » : date, devis envoyés, paiements reçus. Aucun montant, aucune donnée client.

### Ce qu'il fait étape par étape
1. `M.exiger("chiffres-serveur", ...)` : refuse hors de la machine active (sauf `--essai`).
2. Verrou fermé et pas `--essai` : rien, code 0, une ligne au journal.
3. **Devis** = devis dont `historique.envoyé` vaut ce jour-là dans `devis-etat.json` (même définition que la carte « Devis envoyés » du tableau de bord). Fichier absent sur la machine active = aucun devis préparé = 0. Fichier illisible = chiffre indisponible.
4. **Paiements** = nombre de paiements Stripe réussis du jour (`resume-sid.stripe_jour`, lecture seule, clé jamais affichée). Les montants ne sont **jamais** repris.
5. Un seul chiffre indisponible : **aucune ligne** écrite, code 2, journal et trace en erreur (jamais de chiffre inventé).
6. Garde du harness avant écriture (`garde.verifier_envoi`, canal « feuille ») : secret, phrase interdite, lien Stripe, `B2B\STOP`.
7. Feuille cherchée par son nom à la racine du Drive du compte Google des agents (même jeton que `appels-sid`, portée `drive.file`) ; créée avec sa seule ligne d'en-tête `Date,Devis envoyés,Paiements reçus` si elle n'existe pas, jamais remplacée.
8. Jour déjà présent dans la feuille (colonne Date) : rien ajouté — une seule ligne par jour, même si l'état local a été perdu. Une ligne déjà écrite n'est jamais modifiée.
9. Ligne ajoutée à la fin (`values.append`, RAW), puis **relue** : 3 colonnes et mêmes valeurs, sinon code 2 et alerte au journal.
10. `chiffres-serveur-etat.json` : les jours écrits. Journal sans aucun chiffre client. Trace du harness à chaque passage.

### Ce qu'il n'a pas le droit de faire
- écrire un montant, un nom d'entreprise, un e-mail ou un téléphone dans la feuille
- écrire deux lignes pour le même jour, ou modifier une ligne déjà écrite
- écrire dans la vraie feuille avant le « go chiffres-serveur » de Liam
- toucher la vraie feuille en mode essai (feuille de test seulement)
- inventer un chiffre quand la source est indisponible
- lire ou écrire une autre feuille, un autre fichier Drive ou une feuille de Sid
- contacter un prospect, un client ou Sid
- utiliser une IA ou un service payant
- afficher un secret (jeton, clé)
- encaisser, publier ou signer
- Engager Liam (envoyer au client, encaisser, publier, signer) : `peut_engager: false`, tout passe par `B2B/a-valider/`.

## Entrées et sorties
**Lit :**
- B2B/agents/devis-etat.json (statuts des devis, lecture seule, aucune coordonnée client)
- Stripe en lecture seule (nombre de paiements réussis du jour, via resume-sid.stripe_jour ; clé lue dans Jarvis/.env, jamais affichée)
- B2B/agents/chiffres-serveur-config.json

**Écrit :**
- feuille Google « Chiffres serveur Jarvis » (une ligne par soir : date, devis envoyés, paiements reçus)
- B2B/agents/chiffres-serveur-etat.json
- B2B/agents/chiffres-serveur-journal.log

**Discord :** aucun · **Plafond :** 1 messages par jour · **Envoi au client :** non

## Horaire et état
- **Horaire :** chaque jour à 19:30, plage tous les jours 19:00-23:59
- **Tâche serveur :** entrée dans `B2B/agents/serveur-taches.json` ; tourne seulement si l'agent est dans `agents_actifs` (choix de Liam)
- **Contrat :** valide (`python B2B\harness\valider.py`)
- **Garde branchée :** non
- Bloque : kill-switch `B2B\STOP`, lien Stripe non autorisé, phrase interdite (OFFRE-REFERENCE.json), secret dans le texte.
- Avertit : machine non active, envoi_automatique = false (simulation), hors horaires du contrat (19:00-23:59), plafond de 1 messages par jour.
- **Tests :** `tests/agents/test_chiffres_serveur.py`
- **Alerte si silence :** aucune

<!-- DYNAMIQUE:DEBUT -->
**Derniers résultats de test (cette machine) :**
- `tests/agents/test_chiffres_serveur.py` : pas encore lancé par `generer-fiches.py --tests`

**Dernière trace :** aucune · **Dernière erreur :** aucune · **Dans agents_actifs (cette machine) :** non (Liam l'ajoute s'il veut le planifier)

### Historique (5 dernières traces, sans données client)
- aucune trace sur cette machine
<!-- DYNAMIQUE:FIN -->

## Skill et règles
- `.claude/skills/agent-chiffres-serveur/SKILL.md` (copie : `docs/agents/skills/agent-chiffres-serveur.md`)
- Pas de preuve = pas de fait : « il a tourné » = une trace du jour `ok: true` ci-dessus ; « c'est corrigé » = ses tests puis `tests\b2b-rapide.ps1` en vert.
<!-- GENERE:FIN -->

## Liens et décisions

_Zone conservée à chaque régénération : liens vers docs\decisions et docs clés seulement._

Liens : aucun pour l'instant.

## Notes de Liam

_Zone libre, conservée telle quelle à chaque régénération._
