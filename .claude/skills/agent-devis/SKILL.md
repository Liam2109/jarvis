---
name: agent-devis
description: Fiche de rôle de l'agent Devis (pôle Vente) — prépare le devis écrit (texte et PDF) depuis une fiche, montre un aperçu à Liam et attend « ok devis » ; rien ne part au client. À utiliser pour préparer, valider, marquer ou annuler un devis (devis.py preparer, rapide, jour, etat, marquer, annuler).
---

# Agent Devis — préparer, faire valider, jamais envoyer

**Responsable :** Vente. **Script :** `B2B/agents/devis.py`. **Contrat :** `B2B/harness/contrats/devis.json`.
**Tâche serveur :** `jour` toutes les 3 minutes.

## Mission
Préparer le devis écrit (texte et PDF) à partir d'une fiche, le montrer à Liam et attendre « ok devis » ; rien ne part au client.

## Ordres pas à pas (lus dans le script)
1. `preparer fiche.txt` ou `rapide "Nom | métier | ville | livrables | délai | oui/non | besoin"` (ou « devis : … » écrit par Liam dans le salon, mode réel).
2. Lit la fiche et `identite.json`, attribue le numéro `DEV-AAAA-NNN`.
3. Prix et liens : uniquement ceux de `OFFRE-REFERENCE.json` (page web 500 €, site complet 994 €, puis 29 €/mois, premier mois offert, lien Stripe qui comprend l'abonnement).
4. Une information absente (délai, livrables, option sans prix, lien sur mesure) : listée « À COMPLÉTER », l'agent s'arrête.
5. Écrit texte, PDF et message d'accompagnement dans `B2B\devis\`, statut « préparé ».
6. `jour` : en mode réel, poste l'aperçu « à valider » à Liam sur Discord puis cherche son « ok devis » ; en simulation, rien sur Discord (valider avec `marquer`).
7. « ok » reçu : statut « validé » ; Liam envoie lui-même puis `marquer DEV-… envoye`, `accepte`, `paye` (dans l'ordre, jamais de saut).

## Entrées et sorties
- Entrées : fiche texte ou ligne rapide, `identite.json`, messages Discord de Liam.
- Sorties : `B2B\devis\` (texte, PDF, message), `devis-etat.json`, `devis-journal.log`, aperçu Discord salon devis.

## Cas limites gérés par le code
- Un seul devis « préparé » à la fois : le suivant est refusé tant que Liam n'a pas validé ou annulé.
- Ligne Discord prise en compte seulement si elle vient de Liam (pas d'un bot) ; curseur posé au premier passage, jamais de rejeu de l'historique.
- Discord injoignable : « nouvel essai au prochain passage ».
- Erreur d'écriture ou autre : arrêt, suspension, alerte ; `reprendre` pour repartir.
- `annuler` impossible sur un devis déjà envoyé.

## Ce qu'il ne fait jamais
- Envoyer le devis au client (aucune fonction d'envoi e-mail, Messenger ou Stripe).
- Changer un prix ou inventer une information.
- Accéder à la banque ou à Stripe : « payé » est coché à la main par Liam.

## Vérifier qu'il a bien tourné
- `python B2B\agents\devis.py etat` : liste des devis et statuts.
- `python B2B\agents\devis.py jour --a-blanc`.
- Test : `python B2B\agents\test_devis.py`.

## Quand il alerte Liam
- Aperçu « à valider » de chaque devis (mode réel).
- Arrêt sur erreur (alerte Discord, une par motif et par jour).
- `alerte_si_silence` : aucune (agent à la demande).
