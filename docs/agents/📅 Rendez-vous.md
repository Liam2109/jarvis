---
agent: rendez-vous
aliases: [📅 Rendez-vous]
name: rendez-vous
role: Surveiller l'agenda (iCal, lecture seule) et annoncer sur Discord les rendez-vous de 15 min réservés, déplacés, annulés, plus un rappel 30 min avant
machine: serveur DESKTOP-HLQSTAU (si listé dans agents_actifs)
planification: toutes les 5 min (serveur-taches.json, commande « jour »)
depend_de: adresse iCal (hors git)
sorties: salon Discord « rendez-vous », rendez-vous-etat.json
responsable: Vente
statut: actif
mode: réel
horaire: "toutes les 5 min, plage tous les jours 00:00-24:00"
tags: [agent-b2b]
---
<!-- GENERE:DEBUT (régénéré par python B2B\harness\generer-fiches.py : ne pas modifier) -->
# 📅 Rendez-vous

**Agent :** `rendez-vous` · **Statut :** actif · **Responsable :** Vente (pôle) · **Machine :** serveur
**Horaire :** toutes les 5 min, plage tous les jours 00:00-24:00
**Script :** `B2B/agents/rendez-vous.py` · **Contrat :** `B2B/harness/contrats/rendez-vous.json`

## Rôle et limites
### Mission
Annoncer sur Discord chaque rendez-vous de 15 minutes nouveau, déplacé, annulé ou proche, lu dans l'agenda iCal.

### Ce qu'il fait étape par étape
1. Machine active obligatoire (`M.exiger`). Agent suspendu après une erreur : ne fait rien tant que `reprendre` n'est pas lancé.
2. Lit l'adresse iCal dans ses réglages (fichier hors git) ; seules les adresses `https://calendar.google.com/` sont acceptées.
3. Télécharge l'agenda, garde les événements dont le titre commence par « Rendez-vous de 15 minutes ».
4. Premier passage (et premier passage en mode réel) : note l'état actuel **sans rien annoncer** (l'historique n'est jamais rejoué).
5. Pour chaque rendez-vous : nouveau (futur), déplacé (futur), annulé (ou disparu de l'agenda) → un message chacun, une seule fois.
6. Rappel une seule fois par horaire, `rappel_minutes` (30) avant le début.
7. Message : prénom, entreprise, e-mail, remarque, jour et heure (Paris), lien Meet ; posté dans le salon « rdv » (mode réel) ou seulement journalisé « serait posté » (simulation).
8. Oublie les rendez-vous passés depuis plus de 2 jours, écrit l'état.

### Ce qu'il n'a pas le droit de faire
- envoyer au client sans accord de Liam
- encaisser ou rembourser
- publier
- signer ou promettre un résultat
- afficher un secret (jeton, clé, adresse iCal)
- répondre au prospect
- modifier l'agenda
- Engager Liam (envoyer au client, encaisser, publier, signer) : `peut_engager: false`, tout passe par `B2B/a-valider/`.

## Entrées et sorties
**Lit :**
- agenda iCal (adresse secrète, rendez-vous-config.local.json)

**Écrit :**
- B2B/agents/rendez-vous-etat.json
- B2B/agents/rendez-vous-journal.log

**Discord :** rdv · **Plafond :** 40 messages par jour · **Envoi au client :** non

## Horaire et état
- **Horaire :** toutes les 5 min, plage tous les jours 00:00-24:00
- **Tâche serveur :** entrée dans `B2B/agents/serveur-taches.json` ; tourne seulement si l'agent est dans `agents_actifs` (choix de Liam)
- **Contrat :** valide (`python B2B\harness\valider.py`)
- **Garde branchée :** oui
- Bloque : kill-switch `B2B\STOP`, lien Stripe non autorisé, phrase interdite (OFFRE-REFERENCE.json), secret dans le texte.
- Avertit : machine non active, envoi_automatique = false (simulation), hors horaires du contrat (00:00-24:00), plafond de 40 messages par jour.
- **Tests :** `B2B/agents/test_rendez_vous.py`, `tests/agents/test_rendez_vous.py`
- **Alerte si silence :** après 19:30 (surveillant)

<!-- DYNAMIQUE:DEBUT -->
**Derniers résultats de test (cette machine) :**
- `B2B/agents/test_rendez_vous.py` : pas encore lancé par `generer-fiches.py --tests`
- `tests/agents/test_rendez_vous.py` : pas encore lancé par `generer-fiches.py --tests`

**Dernière trace :** 2026-11-24 19:31 ok · **Dernière erreur :** aucune · **Dans agents_actifs (cette machine) :** oui

### Historique (5 dernières traces, sans données client)
- 2026-11-24 19:31 | jour | ok | 0.52 s
- 2026-11-24 19:26 | jour | ok | 0.41 s
- 2026-11-24 19:21 | jour | ok | 0.39 s
- 2026-11-24 19:16 | jour | ok | 0.78 s
- 2026-11-24 19:11 | jour | ok | 0.49 s
<!-- DYNAMIQUE:FIN -->

## Skill et règles
- `.claude/skills/agent-rendez-vous/SKILL.md` (copie : `docs/agents/skills/agent-rendez-vous.md`)
- Pas de preuve = pas de fait : « il a tourné » = une trace du jour `ok: true` ci-dessus ; « c'est corrigé » = ses tests puis `tests\b2b-rapide.ps1` en vert.
<!-- GENERE:FIN -->

## Liens et décisions

_Zone conservée à chaque régénération : liens vers docs\decisions et docs clés seulement._

Lecture seule : n'écrit jamais dans l'agenda. Le rendez-vous suit le kit du rendez-vous.
Détail : `B2B/agents/rendez-vous.md`
Liens : [[KIT-RDV-15MIN]]

## Notes de Liam

_Zone libre, conservée telle quelle à chaque régénération._
