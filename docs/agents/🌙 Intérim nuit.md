---
agent: interim
aliases: [🌙 Intérim nuit]
name: interim
role: "Intérim de nuit / 3x8 autour de Rouen : résumé Discord du matin des alertes d'agences reçues, rappel du lundi par agence ; rien envoyé, aucun compte, aucun document."
machine: "serveur"
planification: "chaque jour à 07:30 + lundi 09:00, plage tous les jours 07:00-12:00"
sorties: "B2B/agents/interim-suivi.csv, B2B/agents/interim-etat.json, B2B/agents/interim-journal.log"
responsable: Liam
statut: arrêté
horaire: "chaque jour à 07:30 + lundi 09:00, plage tous les jours 07:00-12:00"
tags: [agent-b2b]
---
<!-- GENERE:DEBUT (régénéré par python B2B\harness\generer-fiches.py : ne pas modifier) -->
# 🌙 Intérim nuit

**Agent :** `interim` · **Statut :** arrêté · **Responsable :** Liam · **Machine :** serveur
**Horaire :** chaque jour à 07:30 + lundi 09:00, plage tous les jours 07:00-12:00
**Script :** `B2B/agents/interim.py` · **Contrat :** `B2B/harness/contrats/interim.json`

## Rôle et limites
### Mission
Intérim de nuit / 3x8 autour de Rouen : résumé Discord du matin des alertes d'agences reçues, rappel du lundi par agence ; rien envoyé, aucun compte, aucun document.

### Ce qu'il fait étape par étape
1. `passage` : verrou `go_interim` (fichier local de réglages) ; fermé = rien posté (sauf `--essai`).
2. À partir de 07:30, une fois par jour : `matin`. Boîte `boite` lue en `gmail.readonly` (jeton `gmail-lecture-<boîte>.json`, hors git), mails des `domaines` de la config des `jours_mails` derniers jours, jamais deux fois le même (`interim-etat.json`).
3. Par mail : texte brut (ou HTML sans balises), pièces jointes jamais ouvertes. Écarté : hors région, alternance, SNCF / train, CACES exigé (« CACES apprécié » ou « sans CACES » gardé). Gardé : objet, agence (expéditeur), lieu reconnu, horaires reconnus (nuit, 3x8, 2x8, 5x8, équipe, week-end), premier lien utile. Rien de trouvé = « non indiqué ».
4. Mail qui parle d'identifiant, de mot de passe, de carte ou de justificatif : mention « à faire toi-même », rien stocké.
5. Un seul message Discord s'il y a au moins une offre (avec le compte des écartées) ; sinon rien.
6. Le lundi à partir de 09:00, une fois : `semaine`. Pour chaque agence du suivi : appel hebdomadaire (Adéquat), adresse à confirmer, inscription, alerte, documents manquants (oui/non seulement), relance après `relance_jours` sans appel, note.

### Ce qu'il n'a pas le droit de faire
- se connecter à un site d'agence ou à un compte candidat
- gérer, demander ou stocker un mot de passe, un identifiant ou un code
- lire, copier, stocker ou téléverser une pièce d'identité, un RIB, une carte vitale, une mutuelle ou un justificatif
- envoyer, accepter ou publier quoi que ce soit (mail, candidature, CV) sans l'accord de Liam
- inventer une offre, une adresse ou un horaire
- utiliser un outil payant ou une IA
- afficher un secret (jeton, clé)
- Engager Liam (envoyer au client, encaisser, publier, signer) : `peut_engager: false`, tout passe par `B2B/a-valider/`.

## Entrées et sorties
**Lit :**
- boîte emoliam255@gmail.com en lecture seule (gmail.readonly, jeton gmail-lecture-*.json hors git), mails des domaines listés seulement, pièces jointes jamais lues
- B2B/agents/interim-config.json (liste de départ des agences, sources)
- B2B/agents/interim-suivi.csv (suivi, hors git)

**Écrit :**
- B2B/agents/interim-suivi.csv
- B2B/agents/interim-etat.json
- B2B/agents/interim-journal.log

**Discord :** alertes · **Plafond :** 3 messages par jour · **Envoi au client :** non

## Horaire et état
- **Horaire :** chaque jour à 07:30 + lundi 09:00, plage tous les jours 07:00-12:00
- **Tâche serveur :** entrée dans `B2B/agents/serveur-taches.json` ; tourne seulement si l'agent est dans `agents_actifs` (choix de Liam)
- **Contrat :** valide (`python B2B\harness\valider.py`)
- **Garde branchée :** oui
- Bloque : kill-switch `B2B\STOP`, lien Stripe non autorisé, phrase interdite (OFFRE-REFERENCE.json), secret dans le texte.
- Avertit : machine non active, envoi_automatique = false (simulation), hors horaires du contrat (07:00-12:00), plafond de 3 messages par jour.
- **Tests :** `tests/agents/test_interim.py`
- **Alerte si silence :** aucune

<!-- DYNAMIQUE:DEBUT -->
**Derniers résultats de test (cette machine) :**
- `tests/agents/test_interim.py` : pas encore lancé par `generer-fiches.py --tests`

**Dernière trace :** aucune · **Dernière erreur :** aucune · **Dans agents_actifs (cette machine) :** non (Liam l'ajoute s'il veut le planifier)

### Historique (5 dernières traces, sans données client)
- aucune trace sur cette machine
<!-- DYNAMIQUE:FIN -->

## Skill et règles
- `.claude/skills/agent-interim/SKILL.md` (copie : `docs/agents/skills/agent-interim.md`)
- Pas de preuve = pas de fait : « il a tourné » = une trace du jour `ok: true` ci-dessus ; « c'est corrigé » = ses tests puis `tests\b2b-rapide.ps1` en vert.
<!-- GENERE:FIN -->

## Liens et décisions

_Zone conservée à chaque régénération : liens vers docs\decisions et docs clés seulement._

Liens : aucun pour l'instant.

## Notes de Liam

_Zone libre, conservée telle quelle à chaque régénération._
