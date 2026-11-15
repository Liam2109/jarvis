---
agent: vente-relances
statut: prévu
responsable: Vente
horaire: "à compléter par Liam"
machine: à compléter par Liam
tags: [agent-b2b]
---
<!-- GENERE:DEBUT (régénéré par python B2B\harness\generer-fiches.py : ne pas modifier) -->
# vente-relances

**Statut :** prévu · **Responsable :** [[responsable-vente|Responsable Vente]] · **Machine :** à compléter par Liam
**Horaire :** à compléter par Liam
**Script :** à compléter par Liam (aucun script) · **Contrat :** `B2B/harness/contrats/vente-relances.json`

## Mission
Relancer à J+3 et J+7 les prospects qui ont reçu un devis, brouillons écrits dans B2B/a-valider pour Liam.

## Ce qu'il fait étape par étape
à compléter par Liam (agent non construit).

## Entrées et sorties
**Lit :**
- suivi-prospects.csv
- devis envoyés

**Écrit :**
- B2B/a-valider/AAAA-MM-JJ-vente-relances.md

**Discord :** devis · **Plafond :** 20 messages par jour · **Envoi au client :** oui, seulement après accord de Liam

## Ce qu'il n'a pas le droit de faire
- envoyer au client sans accord de Liam
- encaisser ou rembourser
- publier
- signer ou promettre un résultat
- afficher un secret (jeton, clé, adresse iCal)
- plus de deux relances
- relancer un STOP
- Engager Liam (envoyer au client, encaisser, publier, signer) : `peut_engager: false`, tout passe par `B2B/a-valider/`.

## Harness
- **Contrat :** valide (`python B2B\harness\valider.py`)
- **Garde branchée :** à brancher avant activation
- Bloque : kill-switch `B2B\STOP`, lien Stripe non autorisé, phrase interdite (OFFRE-REFERENCE.json), secret dans le texte, envoi client hors lundi-vendredi 08:00-19:00.
- Avertit : machine non active, envoi_automatique = false (simulation), hors horaires du contrat (08:00-19:00), plafond de 20 messages par jour.
- **Tests :** aucun : à compléter par Liam
- **Alerte si silence :** aucune

<!-- DYNAMIQUE:DEBUT -->
**Derniers résultats de test (cette machine) :**
- aucun test

**Dernière trace :** aucune

### Historique (5 dernières traces, sans données client)
- aucune trace sur cette machine
<!-- DYNAMIQUE:FIN -->

## Skill
- [[skills/agent-vente-relances|agent-vente-relances]]

## Liens
- Responsable : [[responsable-vente|Responsable Vente]]
- Direction : [[jarvis-ceo|Jarvis (CEO)]] · [[00-ORGANIGRAMME|Organigramme]]
<!-- GENERE:FIN -->

## Notes de Liam

_Zone libre, conservée telle quelle à chaque régénération._
