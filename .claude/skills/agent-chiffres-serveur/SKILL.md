---
name: agent-chiffres-serveur
description: Fiche de rôle de l'agent Chiffres serveur (pôle Argent, FERMÉ jusqu'au « go chiffres-serveur » de Liam) — tous les soirs à 19:30 sur le serveur, écrit UNE ligne dans la feuille Google « Chiffres serveur Jarvis » (créée au premier passage) : date du jour, nombre de devis envoyés, nombre de paiements reçus, rien d'autre (aucun montant, aucune donnée client). C'est le pont vers les courbes Devis et Ventes du tableau de bord du gros PC. À utiliser pour vérifier, corriger ou activer chiffres-serveur.py (jour, --essai, etat).
---

# Agent Chiffres serveur — deux chiffres par soir dans une feuille Google

**Responsable :** Argent. **Script :** `B2B/agents/chiffres-serveur.py`. **Contrat :** `B2B/harness/contrats/chiffres-serveur.json`.
**Tâche serveur :** `jour` à 19:30, tous les jours (`B2B/agents/serveur-taches.json`) ; à ajouter à `agents_actifs` par Liam.
**Pourquoi :** les deux chiffres ne sont lisibles que sur le serveur (`devis-etat.json`, clé Stripe de `Jarvis\.env`). Le tableau de bord tourne sur le gros PC et affiche « pas encore de données » pour Devis et Ventes : cette feuille est le pont, lue comme les feuilles d'appels de Sid.

## Verrou (ordre de Liam)
Rien n'est écrit dans la vraie feuille tant que `go_chiffres_serveur` n'est pas `true` dans les réglages **locaux** de l'agent (hors git), c'est-à-dire après le « go chiffres-serveur » écrit par Liam. `--essai` marche toujours. `envoi_automatique: false` (défaut versionné) = simulation : la ligne est affichée, rien ne part dans Google.

## Ordres pas à pas (lus dans le script)
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

## Ce qu'il ne fait jamais
Écrire un montant, un nom d'entreprise, un e-mail ou un téléphone dans la feuille ; écrire deux lignes pour le même jour ou modifier une ligne ; toucher la vraie feuille en `--essai` ; lire une autre feuille ou un autre fichier Drive ; contacter un prospect, un client ou Sid ; utiliser une IA ou un service payant ; afficher un jeton ou une clé ; encaisser, publier, signer.

## Vérifier (pas de preuve = pas de fait)
- `python B2B\agents\chiffres-serveur.py jour --essai` : écrit une ligne factice dans « Chiffres serveur Jarvis (essai) », la relit, dit si le format est conforme ; la vraie feuille, l'état et le journal ne sont pas touchés.
- `python B2B\agents\chiffres-serveur.py etat` : verrou, nombre de jours écrits, dernier jour.
- Tests : `python tests\agents\test_chiffres_serveur.py` (verrou, format 3 colonnes, aucun montant ni nom, pas de doublon même sans état, chiffre indisponible, simulation, essai), puis `tests\b2b-rapide.ps1`.

## Reste à faire côté gros PC
`outils\agents-json.py` ne lit pas encore cette feuille : les courbes Devis et Ventes de la page Statistiques resteront en « pas encore de données » jusqu'à ce que `historique.json` soit complété depuis « Chiffres serveur Jarvis » (devis et paiements des jours passés, aujourd'hui `null`). À faire après le « go chiffres-serveur », quand la feuille existe (noté dans `B2B\docs\TODO-B2B.md`).
