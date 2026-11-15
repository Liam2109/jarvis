---
agent: devis
statut: actif
mode: simulation
responsable: Vente
horaire: "toutes les 3 min, plage tous les jours 07:00-22:00"
machine: serveur
tags: [agent-b2b]
---
<!-- GENERE:DEBUT (régénéré par python B2B\harness\generer-fiches.py : ne pas modifier) -->
# devis

**Statut :** actif (simulation : envoi_automatique = false) · **Responsable :** [[responsable-vente|Responsable Vente]] · **Machine :** serveur
**Horaire :** toutes les 3 min, plage tous les jours 07:00-22:00
**Script :** `B2B/agents/devis.py` · **Contrat :** `B2B/harness/contrats/devis.json`

## Mission
Préparer le devis écrit (texte et PDF) à partir d'une fiche, le montrer à Liam et attendre « ok devis » ; rien ne part au client.

## Ce qu'il fait étape par étape
1. `preparer fiche.txt` ou `rapide "Nom | métier | ville | livrables | délai | oui/non | besoin"` (ou « devis : … » écrit par Liam dans le salon, mode réel).
2. Lit la fiche et `identite.json`, attribue le numéro `DEV-AAAA-NNN`.
3. Prix et liens : uniquement ceux de `OFFRE-REFERENCE.json` (page web 595 €, site complet 994 €, puis 49 €/mois, premier mois offert, lien Stripe qui comprend l'abonnement).
4. Une information absente (délai, livrables, option sans prix, lien sur mesure) : listée « À COMPLÉTER », l'agent s'arrête.
5. Écrit texte, PDF et message d'accompagnement dans `B2B\devis\`, statut « préparé ».
6. `jour` : en mode réel, poste l'aperçu « à valider » à Liam sur Discord puis cherche son « ok devis » ; en simulation, rien sur Discord (valider avec `marquer`).
7. « ok » reçu : statut « validé » ; Liam envoie lui-même puis `marquer DEV-… envoye`, `accepte`, `paye` (dans l'ordre, jamais de saut).

## Entrées et sorties
**Lit :**
- fiche devis
- B2B/agents/identite.json
- Discord (ok devis)

**Écrit :**
- devis PDF/texte
- B2B/agents/devis-etat.json

**Discord :** devis · **Plafond :** 20 messages par jour · **Envoi au client :** non

## Ce qu'il n'a pas le droit de faire
- envoyer au client sans accord de Liam
- encaisser ou rembourser
- publier
- signer ou promettre un résultat
- afficher un secret (jeton, clé, adresse iCal)
- envoyer le devis au client
- changer un prix
- Engager Liam (envoyer au client, encaisser, publier, signer) : `peut_engager: false`, tout passe par `B2B/a-valider/`.

## Harness
- **Contrat :** valide (`python B2B\harness\valider.py`)
- **Garde branchée :** oui
- Bloque : kill-switch `B2B\STOP`, lien Stripe non autorisé, phrase interdite (OFFRE-REFERENCE.json), secret dans le texte.
- Avertit : machine non active, envoi_automatique = false (simulation), hors horaires du contrat (07:00-22:00), plafond de 20 messages par jour.
- **Tests :** `B2B/agents/test_devis.py`
- **Alerte si silence :** aucune

<!-- DYNAMIQUE:DEBUT -->
**Derniers résultats de test (cette machine) :**
- `B2B/agents/test_devis.py` : réussi le 2026-11-15 19:34

**Dernière trace :** aucune

### Historique (5 dernières traces, sans données client)
- aucune trace sur cette machine
<!-- DYNAMIQUE:FIN -->

## Skill
- [[skills/agent-devis|agent-devis]]

## Liens
- Responsable : [[responsable-vente|Responsable Vente]]
- Direction : [[jarvis-ceo|Jarvis (CEO)]] · [[00-ORGANIGRAMME|Organigramme]]
<!-- GENERE:FIN -->

## Notes de Liam

_Zone libre, conservée telle quelle à chaque régénération._
