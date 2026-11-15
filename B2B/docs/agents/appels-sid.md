---
agent: appels-sid
statut: actif
mode: simulation
responsable: Prospection
horaire: "chaque jour à 07:30, plage lundi-vendredi 07:00-19:00"
machine: serveur
tags: [agent-b2b]
---
<!-- GENERE:DEBUT (régénéré par python B2B\harness\generer-fiches.py : ne pas modifier) -->
# appels-sid

**Statut :** actif (simulation : envoi_automatique = false) · **Responsable :** [[responsable-prospection|Responsable Prospection]] · **Machine :** serveur
**Horaire :** chaque jour à 07:30, plage lundi-vendredi 07:00-19:00
**Script :** `B2B/agents/appels-sid.py` · **Contrat :** `B2B/harness/contrats/appels-sid.json`

## Mission
Créer chaque jour ouvré à 07:30 le tableur « Appels AAAA-MM-JJ » de Sid, trié par créneau de 08:00 à 19:00.

## Ce qu'il fait étape par étape
- **Quand :** du lundi au vendredi (`jours_appel`), à 7 h 30, il prépare **une** liste de 100 entreprises. Il en met au moins 100 et au plus 130.
- **Quelles entreprises :**
  - environ 20 métiers locaux, au plus 20 entreprises par métier ; ordre : plombier-chauffagiste, électricien, couvreur, maçon, coiffeur, puis les autres ;
  - en Normandie seulement : départements 76, 27, 14, 50, 61 ;
  - un téléphone valide, et aucun site trouvé ;
  - une entreprise appelée est oubliée 1 an (`jours_sans_rappel` 365).
- **Reprises (jours ouvrés, lundi au vendredi) :** le Détail fiche indique « Reprise de la liste du … », avec la note de Sid.
  - Pas de réponse : revient 2 jours ouvrés plus tard, sur un autre créneau, 3 tentatives en tout ; ensuite, oubliée 1 an.
  - À rappeler : revient le jour ouvré suivant.
  - Je dois réfléchir, Pas le temps : reviennent une seule fois, 7 jours plus tard.
  - RDV pris : sort de la liste, signalé dans le résumé du soir.
  - Non catégorique, Trop cher, Déjà un site : oubliée 1 an.
  - Case vide : revient dans la liste suivante.
  - Les reprises comptent dans les 20 par métier ; celles en trop attendent la liste suivante.
- **Le tableur :** il crée **un seul** tableur Google « Appels AAAA-MM-JJ », posé directement dans le dossier Drive de Sid (`dossier_sid_id`), sans sous-dossier.
  - Les lignes sont triées par créneau, de 8 h à 19 h.
  - Les colonnes sont toujours, dans cet ordre : Créneau, Entreprise, Métier, Ville, Téléphone, Détail fiche, Résultat, Note.
  - Résultat est une liste de 8 valeurs, dans cet ordre : Pas de réponse, À rappeler, RDV pris, Non catégorique, Je dois réfléchir, Trop cher, Déjà un site, Pas le temps.
  - Les colonnes sont larges, l'en-tête est figé, aucune cellule n'est fusionnée.
- **Le ménage :** il met à la **corbeille** (jamais une suppression définitive) les tableurs de plus de 7 jours, et les anciens sous-dossiers datés.
- **La réserve :** il garnit sa réserve de numéros avec la commande `sourcer` (OpenStreetMap et SIRENE, gratuits).

## Entrées et sorties
**Lit :**
- B2B/prospects_maps.csv
- B2B/agents/appels-sid-historique.json
- B2B/agents/appels-sid-config.json

**Écrit :**
- Google Drive : Appels AAAA-MM-JJ
- B2B/agents/appels-sid-etat.json
- B2B/agents/appels-sid-journal.log

**Discord :** alertes · **Plafond :** 5 messages par jour · **Envoi au client :** non

## Ce qu'il n'a pas le droit de faire
- envoyer au client sans accord de Liam
- encaisser ou rembourser
- publier
- signer ou promettre un résultat
- afficher un secret (jeton, clé, adresse iCal)
- appeler un prospect
- remettre un STOP dans la liste
- Engager Liam (envoyer au client, encaisser, publier, signer) : `peut_engager: false`, tout passe par `B2B/a-valider/`.

## Harness
- **Contrat :** valide (`python B2B\harness\valider.py`)
- **Garde branchée :** oui
- Bloque : kill-switch `B2B\STOP`, lien Stripe non autorisé, phrase interdite (OFFRE-REFERENCE.json), secret dans le texte.
- Avertit : machine non active, envoi_automatique = false (simulation), hors horaires du contrat (07:00-19:00), plafond de 5 messages par jour.
- **Tests :** `B2B/agents/test_appels_sid.py`, `tests/agents/test_appels_sid.py`
- **Alerte si silence :** après 07:45 (surveillant)

<!-- DYNAMIQUE:DEBUT -->
**Derniers résultats de test (cette machine) :**
- `B2B/agents/test_appels_sid.py` : réussi le 2026-11-15 19:34
- `tests/agents/test_appels_sid.py` : réussi le 2026-11-15 19:35

**Dernière trace :** aucune

### Historique (5 dernières traces, sans données client)
- aucune trace sur cette machine
<!-- DYNAMIQUE:FIN -->

## Skill
- [[skills/agent-appels-sid|agent-appels-sid]]

## Liens
- Responsable : [[responsable-prospection|Responsable Prospection]]
- Direction : [[jarvis-ceo|Jarvis (CEO)]] · [[00-ORGANIGRAMME|Organigramme]]
<!-- GENERE:FIN -->

## Notes de Liam

_Zone libre, conservée telle quelle à chaque régénération._
