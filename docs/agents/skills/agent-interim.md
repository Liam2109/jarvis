---
name: agent-interim
description: Fiche de rôle de l'agent Intérim (pour Liam, FERMÉ jusqu'au « go interim ») — missions d'intérim de nuit / 3x8 dans l'industrie autour de Rouen : chaque matin à 07:30, résumé Discord des alertes d'agences reçues sur emoliam255@gmail.com (offre, agence, lieu, horaires, lien ; hors région, alternance, SNCF et CACES exigé écartés), le lundi à 09:00 qui appeler / relancer / ce qui manque par agence ; suivi des agences en CSV, commande noter. Aucune connexion à un site, aucun mot de passe, aucun document lu. À utiliser pour vérifier, corriger ou activer interim.py (passage, matin, semaine, suivi, noter, gmail-autoriser).
---

# Agent Intérim — nuit / 3x8, industrie, Rouen rive gauche et rive droite

**Pour :** Liam (revenu d'appoint). **Script :** `B2B/agents/interim.py`. **Contrat :** `B2B/harness/contrats/interim.json`.
**Tâche serveur :** `passage` à 07:30 chaque jour et le lundi à 09:00 (`serveur-taches.json`), pas dans `agents_actifs` avant le « go interim ».

## Partage des rôles (règle de Liam, 18/11/2026)
- **Liam** se connecte lui-même à l'espace candidat de chaque agence, active les alertes (nuit, industrie, 3x8, Rouen), dépose ses documents, appelle, envoie.
- **L'agent** lit seulement les mails d'alerte (lecture seule), résume, rappelle. Jamais de site d'agence, de compte, de mot de passe ni de document.

## Ordres pas à pas
1. `passage` : verrou `go_interim` (fichier local de réglages) ; fermé = rien posté (sauf `--essai`).
2. À partir de 07:30, une fois par jour : `matin`. Boîte `boite` lue en `gmail.readonly` (jeton `gmail-lecture-<boîte>.json`, hors git), mails des `domaines` de la config des `jours_mails` derniers jours, jamais deux fois le même (`interim-etat.json`).
3. Par mail : texte brut (ou HTML sans balises), pièces jointes jamais ouvertes. Écarté : hors région, alternance, SNCF / train, CACES exigé (« CACES apprécié » ou « sans CACES » gardé). Gardé : objet, agence (expéditeur), lieu reconnu, horaires reconnus (nuit, 3x8, 2x8, 5x8, équipe, week-end), premier lien utile. Rien de trouvé = « non indiqué ».
4. Mail qui parle d'identifiant, de mot de passe, de carte ou de justificatif : mention « à faire toi-même », rien stocké.
5. Un seul message Discord s'il y a au moins une offre (avec le compte des écartées) ; sinon rien.
6. Le lundi à partir de 09:00, une fois : `semaine`. Pour chaque agence du suivi : appel hebdomadaire (Adéquat), adresse à confirmer, inscription, alerte, documents manquants (oui/non seulement), relance après `relance_jours` sans appel, note.

## Suivi (`B2B/agents/interim-suivi.csv`, hors git, s'ouvre dans Excel)
Colonnes : agence, rive, adresse, téléphone, lien d'inscription, inscrit en ligne, alerte activée, documents déposés (oui/non/partiel), détail des documents (nom=oui/non), dernier appel, prochaine action, adresse confirmée, source. Créé depuis la liste de départ de `interim-config.json` (chaque adresse avec sa source ; « non » tant que Liam ne l'a pas confirmée).
Noter sans éditer le fichier :
`python B2B\agents\interim.py noter adequat appele` · `noter samsic document RIB` · `noter actual inscrit` · `noter actual alerte` · `noter randstad confirme` · `noter crit action "rappeler lundi"` · `--non` pour remettre à non.

## Activation (Liam)
1. `python B2B\agents\interim.py gmail-autoriser` (navigateur, une fois, lecture seule de emoliam255@gmail.com).
2. `python B2B\agents\interim.py passage --essai` : voir le résumé, rien n'est posté.
3. Écrire « go interim » : `go_interim: true` et `envoi_automatique: true` dans le fichier local, `interim` ajouté à `agents_actifs`.

## Vérifier (pas de preuve = pas de fait)
`python tests\agents\test_interim.py` puis `tests\b2b-rapide.ps1` ; `python B2B\agents\interim.py suivi` ; dernière ligne de `interim-journal.log`.

## Préparation (rien n'est envoyé)
`emploi\interim\` : CV d'une page (brouillon à compléter avec Liam, rien inventé), mails de candidature, phrase d'appel hebdomadaire.
