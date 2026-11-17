---
agent: alerte-candidatures
aliases: [🙋 Alerte candidatures]
name: alerte-candidatures
role: "Alerter Liam sur Discord à chaque candidature de call caller (brouillon de réponse joint, une relance à 2 h si non contacté) ; fermé jusqu'au « go alerte »."
machine: "serveur"
planification: "toutes les 5 min, plage tous les jours 00:00-24:00"
sorties: "B2B/agents/alerte-candidatures-etat.json, B2B/agents/alerte-candidatures-journal.log, en-tête « Contacté » de la feuille de réponses (seulement s'il manque)"
responsable: Jarvis (CEO)
statut: arrêté
horaire: "toutes les 5 min, plage tous les jours 00:00-24:00"
tags: [agent-b2b]
---
<!-- GENERE:DEBUT (régénéré par python B2B\harness\generer-fiches.py : ne pas modifier) -->
# 🙋 Alerte candidatures

**Agent :** `alerte-candidatures` · **Statut :** arrêté · **Responsable :** Jarvis (CEO) · **Machine :** serveur
**Horaire :** toutes les 5 min, plage tous les jours 00:00-24:00
**Script :** `B2B/agents/alerte-candidatures.py` · **Contrat :** `B2B/harness/contrats/alerte-candidatures.json`

## Rôle et limites
### Mission
Alerter Liam sur Discord à chaque candidature de call caller (brouillon de réponse joint, une relance à 2 h si non contacté) ; fermé jusqu'au « go alerte ».

### Ce qu'il fait étape par étape
1. `M.exiger("alerte-candidatures", ...)` : refuse de tourner hors de la machine active (sauf `--a-blanc` et `etat`).
2. Réglages `alerte-candidatures-config.json` + fichier local (hors git) : `go_alerte` (verrou, false), `envoi_automatique` (false = simulation), `feuille_id`, `onglet` (vide = premier), `compte_google`, `relance_minutes` (120), `colonne_contacte` (« Contacté »).
3. **Verrou** : `go_alerte` faux -> « rien lu, rien envoyé », code 0. Sans `feuille_id` : message avec la marche à suivre, code 0.
4. Lit toutes les valeurs de l'onglet (API Sheets, jeton `google-candidatures-token.json`, portée `spreadsheets` ; la portée `drive.file` d'appels-sid ne voit pas une feuille créée par Google Forms).
5. Reconnaît les colonnes au texte des questions (horodateur, nom/prénom, téléphone, e-mail, ville, disponibilités, message). Colonne non reconnue = champ omis, **jamais deviné**.
6. Colonne « Contacté » absente : crée **seulement l'en-tête** (ligne 1, première colonne libre). C'est la seule écriture dans la feuille.
7. Premier passage (état vide) : lignes existantes mémorisées **sans alerte**.
8. Chaque ligne inconnue (empreinte horodateur + e-mail + téléphone, aucune donnée du candidat dans l'état) : une alerte Discord « À rappeler dans l'heure » + champs présents + brouillon de réponse. Jamais deux fois la même ligne.
9. Ligne alertée, « Contacté » vide, 2 h écoulées : **une seule** relance.
10. État `alerte-candidatures-etat.json` (60 jours gardés), journal sans donnée du candidat, trace du harness à chaque `verifier` réel.

### Ce qu'il n'a pas le droit de faire
- envoyer un message, un e-mail ou un SMS à un candidat ou à un prospect
- inventer une information sur un candidat (un champ absent est omis)
- écrire dans la feuille autre chose que l'en-tête « Contacté » quand il manque
- promettre un revenu ou un montant au candidat
- tourner avant le « go alerte » de Liam
- afficher un secret (jeton, clé, adresse iCal)
- encaisser, publier ou signer
- Engager Liam (envoyer au client, encaisser, publier, signer) : `peut_engager: false`, tout passe par `B2B/a-valider/`.

## Entrées et sorties
**Lit :**
- feuille de réponses Google du formulaire « Postuler comme call caller » (API Sheets, jeton google-candidatures-token.json)
- B2B/agents/alerte-candidatures-config.json
- fichier local de réglages (go_alerte, feuille_id : écrits par Liam seulement)

**Écrit :**
- B2B/agents/alerte-candidatures-etat.json
- B2B/agents/alerte-candidatures-journal.log
- en-tête « Contacté » de la feuille de réponses (seulement s'il manque)

**Discord :** alertes · **Plafond :** 40 messages par jour · **Envoi au client :** non

## Horaire et état
- **Horaire :** toutes les 5 min, plage tous les jours 00:00-24:00
- **Tâche serveur :** entrée dans `B2B/agents/serveur-taches.json` ; tourne seulement si l'agent est dans `agents_actifs` (choix de Liam)
- **Contrat :** valide (`python B2B\harness\valider.py`)
- **Garde branchée :** oui
- Bloque : kill-switch `B2B\STOP`, lien Stripe non autorisé, phrase interdite (OFFRE-REFERENCE.json), secret dans le texte.
- Avertit : machine non active, envoi_automatique = false (simulation), hors horaires du contrat (00:00-24:00), plafond de 40 messages par jour.
- **Tests :** `tests/agents/test_alerte_candidatures.py`
- **Alerte si silence :** aucune

<!-- DYNAMIQUE:DEBUT -->
**Derniers résultats de test (cette machine) :**
- `tests/agents/test_alerte_candidatures.py` : pas encore lancé par `generer-fiches.py --tests`

**Dernière trace :** aucune · **Dernière erreur :** aucune · **Dans agents_actifs (cette machine) :** non (Liam l'ajoute s'il veut le planifier)

### Historique (5 dernières traces, sans données client)
- aucune trace sur cette machine
<!-- DYNAMIQUE:FIN -->

## Skill et règles
- `.claude/skills/agent-alerte-candidatures/SKILL.md` (copie : `docs/agents/skills/agent-alerte-candidatures.md`)
- Pas de preuve = pas de fait : « il a tourné » = une trace du jour `ok: true` ci-dessus ; « c'est corrigé » = ses tests puis `tests\b2b-rapide.ps1` en vert.
<!-- GENERE:FIN -->

## Liens et décisions

_Zone conservée à chaque régénération : liens vers docs\decisions et docs clés seulement._

Liens : aucun pour l'instant.

## Notes de Liam

_Zone libre, conservée telle quelle à chaque régénération._
