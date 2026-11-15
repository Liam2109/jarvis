---
agent: rendez-vous
statut: actif
mode: réel
responsable: Vente
horaire: "toutes les 5 min, plage tous les jours 00:00-24:00"
machine: serveur
tags: [agent-b2b]
---
<!-- GENERE:DEBUT (régénéré par python B2B\harness\generer-fiches.py : ne pas modifier) -->
# rendez-vous

**Statut :** actif · **Responsable :** [[responsable-vente|Responsable Vente]] · **Machine :** serveur
**Horaire :** toutes les 5 min, plage tous les jours 00:00-24:00
**Script :** `B2B/agents/rendez-vous.py` · **Contrat :** `B2B/harness/contrats/rendez-vous.json`

## Mission
Annoncer sur Discord chaque rendez-vous de 15 minutes nouveau, déplacé, annulé ou proche, lu dans l'agenda iCal.

## Ce qu'il fait étape par étape
1. Machine active obligatoire (`M.exiger`). Agent suspendu après une erreur : ne fait rien tant que `reprendre` n'est pas lancé.
2. Lit l'adresse iCal dans ses réglages (fichier hors git) ; seules les adresses `https://calendar.google.com/` sont acceptées.
3. Télécharge l'agenda, garde les événements dont le titre commence par « Rendez-vous de 15 minutes ».
4. Premier passage (et premier passage en mode réel) : note l'état actuel **sans rien annoncer** (l'historique n'est jamais rejoué).
5. Pour chaque rendez-vous : nouveau (futur), déplacé (futur), annulé (ou disparu de l'agenda) → un message chacun, une seule fois.
6. Rappel une seule fois par horaire, `rappel_minutes` (30) avant le début.
7. Message : prénom, entreprise, e-mail, remarque, jour et heure (Paris), lien Meet ; posté dans le salon « rdv » (mode réel) ou seulement journalisé « serait posté » (simulation).
8. Oublie les rendez-vous passés depuis plus de 2 jours, écrit l'état.

## Entrées et sorties
**Lit :**
- agenda iCal (adresse secrète, rendez-vous-config.local.json)

**Écrit :**
- B2B/agents/rendez-vous-etat.json
- B2B/agents/rendez-vous-journal.log

**Discord :** rdv · **Plafond :** 40 messages par jour · **Envoi au client :** non

## Ce qu'il n'a pas le droit de faire
- envoyer au client sans accord de Liam
- encaisser ou rembourser
- publier
- signer ou promettre un résultat
- afficher un secret (jeton, clé, adresse iCal)
- répondre au prospect
- modifier l'agenda
- Engager Liam (envoyer au client, encaisser, publier, signer) : `peut_engager: false`, tout passe par `B2B/a-valider/`.

## Harness
- **Contrat :** valide (`python B2B\harness\valider.py`)
- **Garde branchée :** oui
- Bloque : kill-switch `B2B\STOP`, lien Stripe non autorisé, phrase interdite (OFFRE-REFERENCE.json), secret dans le texte.
- Avertit : machine non active, envoi_automatique = false (simulation), hors horaires du contrat (00:00-24:00), plafond de 40 messages par jour.
- **Tests :** `B2B/agents/test_rendez_vous.py`, `tests/agents/test_rendez_vous.py`
- **Alerte si silence :** après 19:30 (surveillant)

<!-- DYNAMIQUE:DEBUT -->
**Derniers résultats de test (cette machine) :**
- `B2B/agents/test_rendez_vous.py` : réussi le 2026-11-15 19:35
- `tests/agents/test_rendez_vous.py` : réussi le 2026-11-15 19:35

**Dernière trace :** aucune

### Historique (5 dernières traces, sans données client)
- aucune trace sur cette machine
<!-- DYNAMIQUE:FIN -->

## Skill
- [[skills/agent-rendez-vous|agent-rendez-vous]]

## Liens
- Responsable : [[responsable-vente|Responsable Vente]]
- Direction : [[jarvis-ceo|Jarvis (CEO)]] · [[00-ORGANIGRAMME|Organigramme]]
<!-- GENERE:FIN -->

## Notes de Liam

_Zone libre, conservée telle quelle à chaque régénération._
