---
agent: superviseur-mail
aliases: [📬 Superviseur Mail]
name: superviseur-mail
role: "Toutes les 30 min : le tri du courrier des agences tourne-t-il, reste-t-il en lecture seule, les fiches et les actions a rappeler sont-elles intactes ? Alerte sans rien toucher si non."
machine: "serveur"
planification: "toutes les 30 min, plage tous les jours 07:00-22:00"
sorties: "B2B/agents/interim-suivi.csv (ligne strictement en double retiree), B2B/agents/interim-etat.json (cle manquante ajoutee vide), B2B/agents/superviseur-mail-etat.json, B2B/agents/superviseur-mail-journal.log, B2B/a-valider/AAAA-MM-JJ-superviseur-mail.md"
responsable: Jarvis (CEO)
statut: arrêté
horaire: "toutes les 30 min, plage tous les jours 07:00-22:00"
tags: [agent-b2b]
---
<!-- GENERE:DEBUT (régénéré par python B2B\harness\generer-fiches.py : ne pas modifier) -->
# 📬 Superviseur Mail

**Agent :** `superviseur-mail` · **Statut :** arrêté · **Responsable :** Jarvis (CEO) · **Machine :** serveur
**Horaire :** toutes les 30 min, plage tous les jours 07:00-22:00
**Script :** `B2B/agents/superviseur-mail.py` · **Contrat :** `B2B/harness/contrats/superviseur-mail.json`

## Rôle et limites
### Mission
Toutes les 30 min : le tri du courrier des agences tourne-t-il, reste-t-il en lecture seule, les fiches et les actions a rappeler sont-elles intactes ? Alerte sans rien toucher si non.

### Ce qu'il fait étape par étape
1. `M.exiger("superviseur-mail", ...)` : refuse hors de la machine active (sauf `--essai`).
2. État de l'agent de tri, lu dans ses traces du jour et dans sa tâche serveur. Tant que Liam ne l'a pas mis dans `agents_actifs`, son silence est normal et n'est pas signalé.
   En erreur, silencieux ou bloqué : **relancé une fois** par jour, puis alerte s'il reste en défaut.
3. **Lecture seule du courrier** : il lit le **code** de l'agent (`B2B/agents/interim.py`) et relève les portées Google qui y sont déclarées.
   Toute portée autre que `gmail.readonly`, ou aucune portée du tout, est une alerte immédiate. Il vérifie aussi que la boîte réglée est toujours celle attendue (`boite_attendue`).
   Il n'ouvre **jamais** la boîte, ne lit **jamais** un mail, un jeton, un mot de passe ni une pièce jointe.
4. **Fiches d'agences** : `interim-suivi.csv` (hors git) — lignes strictement en double retirées, fiche sans nom signalée ;
   `interim-config.json` (versionné, données de Liam, **jamais modifié**) — fiche incomplète (champ attendu absent), agence écrite deux fois,
   adresse marquée confirmée sans la mention de Liam : alerte seulement.
5. **Actions « à rappeler »** : la colonne `prochaine_action` du suivi est mémorisée à chaque passage (empreinte dans l'état du superviseur).
   Une action présente au passage précédent et devenue vide est signalée, et **n'est jamais rétablie** : Liam dit s'il faut la remettre.
6. État du tri (`interim-etat.json`) : clés attendues (ajoutées vides si elles manquent), dates des résumés du matin et des rappels du lundi.
7. Tout ce qui n'est pas corrigeable sans risque part en alerte Discord et dans `B2B/a-valider/AAAA-MM-JJ-superviseur-mail.md`, puis il attend le « go ».
   Discord : un résumé court par jour même quand tout va bien, plus un message dès qu'il y a du neuf ; rien entre 22:00 et 07:00 ; même souci annoncé une seule fois.

### Ce qu'il n'a pas le droit de faire
- ouvrir la boite, lire un mail, un jeton, un mot de passe ou une piece jointe
- modifier B2B/agents/interim-config.json (fiches d'agences : donnees de Liam)
- retablir tout seul une action a rappeler disparue
- supprimer une donnee, une ligne, une fiche ou un fichier
- ecraser une valeur deja ecrite par un agent ou par Liam
- toucher a un montant, un paiement, un prix ou un devis
- toucher au code, aux skills, aux docs ou a un fichier suivi par git
- ecrire dans les donnees d'un autre domaine que le sien
- corriger quoi que ce soit avant le « go superviseurs » de Liam
- relancer plus d'une fois par jour le meme agent
- contacter un prospect, un client, Sid ou qui que ce soit d'autre que Liam
- utiliser une IA ou un service payant
- afficher un secret (jeton, cle, adresse iCal)
- envoyer au client, encaisser, publier ou signer
- Engager Liam (envoyer au client, encaisser, publier, signer) : `peut_engager: false`, tout passe par `B2B/a-valider/`.

## Entrées et sorties
**Lit :**
- B2B/agents/interim.py (portees Gmail declarees dans le code)
- B2B/agents/interim-config.json (boite reglee, fiches d'agences)
- B2B/agents/interim-etat.json
- B2B/agents/interim-suivi.csv
- B2B/logs/agents (traces du jour)
- B2B/agents/serveur-taches.json

**Écrit :**
- B2B/agents/interim-suivi.csv (ligne strictement en double retiree)
- B2B/agents/interim-etat.json (cle manquante ajoutee vide)
- B2B/agents/superviseur-mail-etat.json
- B2B/agents/superviseur-mail-journal.log
- B2B/a-valider/AAAA-MM-JJ-superviseur-mail.md

**Discord :** alertes · **Plafond :** 6 messages par jour · **Envoi au client :** non

## Horaire et état
- **Horaire :** toutes les 30 min, plage tous les jours 07:00-22:00
- **Tâche serveur :** entrée dans `B2B/agents/serveur-taches.json`, active à partir du 2026-11-21 ; tourne seulement si l'agent est dans `agents_actifs` (choix de Liam)
- **Contrat :** valide (`python B2B\harness\valider.py`)
- **Garde branchée :** oui
- Bloque : kill-switch `B2B\STOP`, lien Stripe non autorisé, phrase interdite (OFFRE-REFERENCE.json), secret dans le texte.
- Avertit : machine non active, envoi_automatique = false (simulation), hors horaires du contrat (07:00-22:00), plafond de 6 messages par jour.
- **Tests :** `tests/agents/test_superviseurs.py`
- **Alerte si silence :** aucune

<!-- DYNAMIQUE:DEBUT -->
**Derniers résultats de test (cette machine) :**
- `tests/agents/test_superviseurs.py` : pas encore lancé par `generer-fiches.py --tests`

**Dernière trace :** aucune · **Dernière erreur :** aucune · **Dans agents_actifs (cette machine) :** oui

### Historique (5 dernières traces, sans données client)
- aucune trace sur cette machine
<!-- DYNAMIQUE:FIN -->

## Skill et règles
- `.claude/skills/agent-superviseur-mail/SKILL.md` (copie : `docs/archives/agents-retires/agent-superviseur-mail.md`)
- Pas de preuve = pas de fait : « il a tourné » = une trace du jour `ok: true` ci-dessus ; « c'est corrigé » = ses tests puis `tests\b2b-rapide.ps1` en vert.
<!-- GENERE:FIN -->

## Liens et décisions

_Zone conservée à chaque régénération : liens vers docs\decisions et docs clés seulement._

Rattaché à : [[docs/agents/🧠 Jarvis (CEO)|🧠 Jarvis (CEO)]]
Agents suivis (Mail) : [[docs/agents/🌙 Intérim nuit|🌙 Intérim nuit]]

## Notes de Liam

_Zone libre, conservée telle quelle à chaque régénération._
