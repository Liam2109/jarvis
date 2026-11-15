---
name: agent-resume-sid
description: Fiche de rôle de l'agent Résumé du soir de Sid (rattaché à Jarvis CEO) — à 19:30 les jours ouvrés, poste sur Discord les appels de Sid par valeur de Résultat et le chiffre d'affaires Stripe du jour. À utiliser pour vérifier ou corriger resume-sid.py (resume, etat).
---

# Agent Résumé du soir — appels de Sid et chiffre d'affaires

**Responsable :** Jarvis (CEO). **Script :** `B2B/agents/resume-sid.py`. **Contrat :** `B2B/harness/contrats/resume-sid.json`.
**Tâche serveur :** `resume` à 19:30.

## Mission
Poster à 19:30 (jours ouvrés) le résumé du soir : appels de Sid par valeur de Résultat et chiffre d'affaires Stripe du jour.

## Ordres pas à pas (lus dans le script)
1. `M.exiger("resume-sid", ...)` : machine active obligatoire (sauf `--a-blanc`).
2. Réglages `resume-sid-config.json` (+ `.local.json`) : `envoi_automatique` (false = simulation), `heure_tache`, `compte_google`.
3. Samedi ou dimanche (heure de Paris) : « pas de résumé le week-end », journalisé, fin.
4. Résumé du jour déjà envoyé (ou simulé) : rien de plus.
5. Appels : lit l'identifiant de la feuille du jour dans `appels-sid-etat.json`, ouvre la feuille Google **en lecture**, compte chaque valeur de la colonne Résultat (8 valeurs) ; anciennes feuilles : colonnes Appelé / Répondu / Rendez-vous pris / Refus.
6. Chiffre d'affaires : paiements Stripe réussis depuis minuit (Paris), remboursements déduits, par devise ; « au moins » si Stripe dit qu'il y en a plus.
7. Compose le message, le poste (mode réel) ou l'affiche (simulation), note le jour dans `resume-sid-etat.json` (60 jours gardés), journalise, écrit une trace du harness.

## Entrées et sorties
- Entrées : `appels-sid-etat.json`, feuille Google « Appels AAAA-MM-JJ » (lecture), API Stripe `charges` (lecture, clé `STRIPE_RESTRICTED_KEY` de `Jarvis\.env`).
- Sorties : message Discord (salon habituel, via `prospection.discord`), `resume-sid-etat.json`, `resume-sid-journal.log`, trace `B2B/logs/agents/resume-sid/`.

## Cas limites gérés par le code
- Aucune feuille ce jour-là, feuille vide ou illisible, colonnes inattendues : « pas de chiffre » avec la raison, jamais un chiffre inventé.
- Jeton Google d'un autre compte : le dit (« relancez appels-sid.py google-autoriser »).
- Clé Stripe absente, refusée ou Stripe injoignable : « pas de chiffre » avec la raison.
- Fuseau absent sous Windows : repli heure d'été approximative (mars-octobre).

## Ce qu'il ne fait jamais
- Écrire dans la feuille de Sid, écrire à Sid ou à un prospect.
- Inventer un chiffre ; mettre un nom, un e-mail ou un numéro dans le message.

## Vérifier qu'il a bien tourné
- `python B2B\agents\resume-sid.py etat` : dernier résumé envoyé ou simulé.
- `python B2B\agents\resume-sid.py resume --a-blanc` : affiche le résumé sans rien écrire.
- Tests : `python B2B\agents\test_resume_sid.py` et `python tests\agents\test_resume_sid.py`.

## Quand il alerte Liam
- Le résumé lui-même, chaque soir ouvré.
- Silence : le surveillant et panne-alerte le signalent si rien n'a tourné après 19:40 / 19:45.
