---
agent: resume-sid
statut: actif
mode: simulation
responsable: Jarvis (CEO)
horaire: "chaque jour à 19:30, plage lundi-vendredi 18:00-23:00"
machine: serveur
tags: [agent-b2b]
---
<!-- GENERE:DEBUT (régénéré par python B2B\harness\generer-fiches.py : ne pas modifier) -->
# resume-sid

**Statut :** actif (simulation : envoi_automatique = false) · **Responsable :** [[jarvis-ceo|Jarvis (CEO)]] · **Machine :** serveur
**Horaire :** chaque jour à 19:30, plage lundi-vendredi 18:00-23:00
**Script :** `B2B/agents/resume-sid.py` · **Contrat :** `B2B/harness/contrats/resume-sid.json`

## Mission
Poster à 19:30 (jours ouvrés) le résumé du soir : appels de Sid par valeur de Résultat et chiffre d'affaires Stripe du jour.

## Ce qu'il fait étape par étape
1. `M.exiger("resume-sid", ...)` : machine active obligatoire (sauf `--a-blanc`).
2. Réglages `resume-sid-config.json` (+ `.local.json`) : `envoi_automatique` (false = simulation), `heure_tache`, `compte_google`.
3. Samedi ou dimanche (heure de Paris) : « pas de résumé le week-end », journalisé, fin.
4. Résumé du jour déjà envoyé (ou simulé) : rien de plus.
5. Appels : lit l'identifiant de la feuille du jour dans `appels-sid-etat.json`, ouvre la feuille Google **en lecture**, compte chaque valeur de la colonne Résultat (8 valeurs) ; anciennes feuilles : colonnes Appelé / Répondu / Rendez-vous pris / Refus.
6. Chiffre d'affaires : paiements Stripe réussis depuis minuit (Paris), remboursements déduits, par devise ; « au moins » si Stripe dit qu'il y en a plus.
7. Compose le message, le poste (mode réel) ou l'affiche (simulation), note le jour dans `resume-sid-etat.json` (60 jours gardés), journalise, écrit une trace du harness.

## Entrées et sorties
**Lit :**
- Google Sheets : Appels AAAA-MM-JJ (lecture)
- Stripe charges (lecture)

**Écrit :**
- B2B/agents/resume-sid-etat.json
- B2B/agents/resume-sid-journal.log

**Discord :** alertes · **Plafond :** 2 messages par jour · **Envoi au client :** non

## Ce qu'il n'a pas le droit de faire
- envoyer au client sans accord de Liam
- encaisser ou rembourser
- publier
- signer ou promettre un résultat
- afficher un secret (jeton, clé, adresse iCal)
- inventer un chiffre
- écrire dans la feuille de Sid
- Engager Liam (envoyer au client, encaisser, publier, signer) : `peut_engager: false`, tout passe par `B2B/a-valider/`.

## Harness
- **Contrat :** valide (`python B2B\harness\valider.py`)
- **Garde branchée :** oui
- Bloque : kill-switch `B2B\STOP`, lien Stripe non autorisé, phrase interdite (OFFRE-REFERENCE.json), secret dans le texte.
- Avertit : machine non active, envoi_automatique = false (simulation), hors horaires du contrat (18:00-23:00), plafond de 2 messages par jour.
- **Tests :** `B2B/agents/test_resume_sid.py`, `tests/agents/test_resume_sid.py`
- **Alerte si silence :** après 19:40 (surveillant)

<!-- DYNAMIQUE:DEBUT -->
**Derniers résultats de test (cette machine) :**
- `B2B/agents/test_resume_sid.py` : réussi le 2026-11-15 19:35
- `tests/agents/test_resume_sid.py` : réussi le 2026-11-15 19:35

**Dernière trace :** aucune

### Historique (5 dernières traces, sans données client)
- aucune trace sur cette machine
<!-- DYNAMIQUE:FIN -->

## Skill
- [[skills/agent-resume-sid|agent-resume-sid]]

## Liens
- Responsable : [[jarvis-ceo|Jarvis (CEO)]]
- Direction : [[jarvis-ceo|Jarvis (CEO)]] · [[00-ORGANIGRAMME|Organigramme]]
<!-- GENERE:FIN -->

## Notes de Liam

_Zone libre, conservée telle quelle à chaque régénération._
