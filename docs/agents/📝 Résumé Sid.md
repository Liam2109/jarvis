---
agent: resume-sid
aliases: [📝 Résumé Sid]
name: resume-sid
role: Résumé Discord du soir (19 h) : cases cochées par Sid sur sa feuille du jour et chiffre d'affaires Stripe du jour
machine: non planifié sur le serveur (absent de serveur-taches.json)
planification: tâche Windows de 19 h, installée seulement par Liam (« installer --oui ») ; aucune sur le gros PC
depend_de: agent-appels-sid
sorties: message Discord du soir
responsable: Jarvis (CEO)
statut: actif
mode: simulation
horaire: "chaque jour à 19:30, plage lundi-vendredi 18:00-23:00"
tags: [agent-b2b]
---
<!-- GENERE:DEBUT (régénéré par python B2B\harness\generer-fiches.py : ne pas modifier) -->
# 📝 Résumé Sid

**Agent :** `resume-sid` · **Statut :** actif (simulation : envoi_automatique = false) · **Responsable :** Jarvis (CEO) · **Machine :** serveur
**Horaire :** chaque jour à 19:30, plage lundi-vendredi 18:00-23:00
**Script :** `B2B/agents/resume-sid.py` · **Contrat :** `B2B/harness/contrats/resume-sid.json`

## Rôle et limites
### Mission
Poster à 19:30 (jours ouvrés) le résumé du soir : appels de Sid par valeur de Résultat et chiffre d'affaires Stripe du jour.

### Ce qu'il fait étape par étape
1. `M.exiger("resume-sid", ...)` : machine active obligatoire (sauf `--a-blanc`).
2. Réglages `resume-sid-config.json` (+ `.local.json`) : `envoi_automatique` (false = simulation), `heure_tache`, `compte_google`.
3. Samedi ou dimanche (heure de Paris) : « pas de résumé le week-end », journalisé, fin.
4. Résumé du jour déjà envoyé (ou simulé) : rien de plus.
5. Appels : lit l'identifiant de la feuille du jour dans `appels-sid-etat.json`, ouvre la feuille Google **en lecture**, compte chaque valeur de la colonne Résultat (8 valeurs) ; anciennes feuilles : colonnes Appelé / Répondu / Rendez-vous pris / Refus.
6. Chiffre d'affaires : paiements Stripe réussis depuis minuit (Paris), remboursements déduits, par devise ; « au moins » si Stripe dit qu'il y en a plus.
7. Compose le message, le poste (mode réel) ou l'affiche (simulation), note le jour dans `resume-sid-etat.json` (60 jours gardés), journalise, écrit une trace du harness.

### Ce qu'il n'a pas le droit de faire
- envoyer au client sans accord de Liam
- encaisser ou rembourser
- publier
- signer ou promettre un résultat
- afficher un secret (jeton, clé, adresse iCal)
- inventer un chiffre
- écrire dans la feuille de Sid
- Engager Liam (envoyer au client, encaisser, publier, signer) : `peut_engager: false`, tout passe par `B2B/a-valider/`.

## Entrées et sorties
**Lit :**
- Google Sheets : toutes les feuilles Appels Sid AAAA-MM-JJ modifiées le jour (lecture)
- Stripe charges (lecture)

**Écrit :**
- B2B/agents/resume-sid-etat.json
- B2B/agents/resume-sid-journal.log

**Discord :** alertes · **Plafond :** 2 messages par jour · **Envoi au client :** non

## Horaire et état
- **Horaire :** chaque jour à 19:30, plage lundi-vendredi 18:00-23:00
- **Tâche serveur :** entrée dans `B2B/agents/serveur-taches.json` ; tourne seulement si l'agent est dans `agents_actifs` (choix de Liam)
- **Contrat :** valide (`python B2B\harness\valider.py`)
- **Garde branchée :** oui
- Bloque : kill-switch `B2B\STOP`, lien Stripe non autorisé, phrase interdite (OFFRE-REFERENCE.json), secret dans le texte.
- Avertit : machine non active, envoi_automatique = false (simulation), hors horaires du contrat (18:00-23:00), plafond de 2 messages par jour.
- **Tests :** `B2B/agents/test_resume_sid.py`, `tests/agents/test_resume_sid.py`
- **Alerte si silence :** après 19:40 (surveillant)

<!-- DYNAMIQUE:DEBUT -->
**Derniers résultats de test (cette machine) :**
- `B2B/agents/test_resume_sid.py` : pas encore lancé par `generer-fiches.py --tests`
- `tests/agents/test_resume_sid.py` : pas encore lancé par `generer-fiches.py --tests`

**Dernière trace :** 2026-11-20 19:30 ok · **Dernière erreur :** aucune · **Dans agents_actifs (cette machine) :** oui

### Historique (5 dernières traces, sans données client)
- 2026-11-20 19:30 | resume | ok | 3.22 s
- 2026-11-20 19:30 | resume | ok | 2.93 s
- 2026-11-19 19:30 | resume | ok | 5.86 s
- 2026-11-19 19:30 | resume | ok | 5.57 s
- 2026-11-18 19:30 | resume | ok | 4.91 s
<!-- DYNAMIQUE:FIN -->

## Skill et règles
- `.claude/skills/agent-resume-sid/SKILL.md` (copie : `docs/agents/skills/agent-resume-sid.md`)
- Pas de preuve = pas de fait : « il a tourné » = une trace du jour `ok: true` ci-dessus ; « c'est corrigé » = ses tests puis `tests\b2b-rapide.ps1` en vert.
<!-- GENERE:FIN -->

## Liens et décisions

_Zone conservée à chaque régénération : liens vers docs\decisions et docs clés seulement._

Lecture seule de la feuille Google et de Stripe.
Détail : `B2B/agents/resume-sid.md`
Liens : [[JOURNAL-B2B]]

## Notes de Liam

_Zone libre, conservée telle quelle à chaque régénération._
