---
agent: prospection
statut: actif
mode: simulation
responsable: Prospection
horaire: "toutes les 10 min, plage lundi-vendredi 08:00-19:00"
machine: serveur
tags: [agent-b2b]
---
<!-- GENERE:DEBUT (régénéré par python B2B\harness\generer-fiches.py : ne pas modifier) -->
# prospection

**Statut :** actif (simulation : envoi_automatique = false) · **Responsable :** [[responsable-prospection|Responsable Prospection]] · **Machine :** serveur
**Horaire :** toutes les 10 min, plage lundi-vendredi 08:00-19:00
**Script :** `B2B/agents/prospection.py` · **Contrat :** `B2B/harness/contrats/prospection.json`

## Mission
Trouver des entreprises locales, préparer les lots d'e-mails, les soumettre à Liam et n'envoyer que les lots approuvés.

## Ce qu'il fait étape par étape
**Selon [[skills/agent-recherche|agent-recherche]] :**
- Cherche des entreprises (bâtiment d'abord, puis commerces), en Normandie par vagues de départements.
- Sources : annuaire officiel (SIRENE), OpenStreetMap, Google Places si `decouverte_places` est vrai.
- Garde celles qui n'ont pas de site, ou un site faible. Le constat doit être vérifiable, jamais un avis.
- Trouve un contact **public** : e-mail publié par l'entreprise, Facebook, LinkedIn ou formulaire.
- Écrit chaque prospect dans `prospection-trouves.csv`.

**Selon [[skills/agent-lots-emails|agent-lots-emails]] :**
- **Préparer** : prend les prospects « trouvé » et prépare un lot de 10 par boîte Gmail. Il écrit `messages-a-valider.md` (statut « à valider ») et l'aperçu `apercu-lot.html`.
- **Relancer** : prépare **une** relance à J+2, depuis la même boîte que le premier message.
- **Faire valider** : poste le lot sur Discord, puis lit l'accord de **Liam seul** (« ok lot » ou ✅).
- **Envoyer** : envoie seulement les blocs « validé » **et** approuvés, avec une pause aléatoire entre deux envois et un palier de montée en charge.

## Entrées et sorties
**Lit :**
- API entreprises, OSM, sites publics
- B2B/agents/prospection-etat.json

**Écrit :**
- lots
- messages-a-valider.md
- B2B/agents/prospection-etat.json

**Discord :** lots, alertes · **Plafond :** 40 messages par jour · **Envoi au client :** oui, seulement après accord de Liam

## Ce qu'il n'a pas le droit de faire
- envoyer au client sans accord de Liam
- encaisser ou rembourser
- publier
- signer ou promettre un résultat
- afficher un secret (jeton, clé, adresse iCal)
- écrire à un STOP ou un exclu
- dépasser par_boite_par_jour
- Engager Liam (envoyer au client, encaisser, publier, signer) : `peut_engager: false`, tout passe par `B2B/a-valider/`.

## Harness
- **Contrat :** valide (`python B2B\harness\valider.py`)
- **Garde branchée :** oui
- Bloque : kill-switch `B2B\STOP`, lien Stripe non autorisé, phrase interdite (OFFRE-REFERENCE.json), secret dans le texte, envoi client hors lundi-vendredi 08:00-19:00.
- Avertit : machine non active, envoi_automatique = false (simulation), hors horaires du contrat (08:00-19:00), plafond de 40 messages par jour.
- **Tests :** `B2B/agents/test_prospection.py`
- **Alerte si silence :** après 19:30 (surveillant)

<!-- DYNAMIQUE:DEBUT -->
**Derniers résultats de test (cette machine) :**
- `B2B/agents/test_prospection.py` : réussi le 2026-11-15 19:35

**Dernière trace :** aucune

### Historique (5 dernières traces, sans données client)
- aucune trace sur cette machine
<!-- DYNAMIQUE:FIN -->

## Skill
- [[skills/agent-recherche|agent-recherche]]
- [[skills/agent-lots-emails|agent-lots-emails]]

## Liens
- Responsable : [[responsable-prospection|Responsable Prospection]]
- Direction : [[jarvis-ceo|Jarvis (CEO)]] · [[00-ORGANIGRAMME|Organigramme]]
<!-- GENERE:FIN -->

## Notes de Liam

_Zone libre, conservée telle quelle à chaque régénération._
