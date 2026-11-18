---
agent: relances
aliases: [☎️ Relances leads]
name: relances
role: "Chaque jour ouvré à 08:30, un message Discord « À rappeler aujourd'hui » pour Liam : leads chauds de Sid à J+3 et J+7 ouvrés (J+15 si moyen terme) ; ne contacte que Liam."
machine: "serveur"
planification: "chaque jour à 08:30, plage lundi-vendredi 08:00-19:00"
sorties: "B2B/agents/relances-etat.json, B2B/agents/relances-journal.log"
responsable: Vente
statut: actif
mode: réel
horaire: "chaque jour à 08:30, plage lundi-vendredi 08:00-19:00"
tags: [agent-b2b]
---
<!-- GENERE:DEBUT (régénéré par python B2B\harness\generer-fiches.py : ne pas modifier) -->
# ☎️ Relances leads

**Agent :** `relances` · **Statut :** actif · **Responsable :** Vente (pôle) · **Machine :** serveur
**Horaire :** chaque jour à 08:30, plage lundi-vendredi 08:00-19:00
**Script :** `B2B/agents/relances.py` · **Contrat :** `B2B/harness/contrats/relances.json`

## Rôle et limites
### Mission
Chaque jour ouvré à 08:30, un message Discord « À rappeler aujourd'hui » pour Liam : leads chauds de Sid à J+3 et J+7 ouvrés (J+15 si moyen terme) ; ne contacte que Liam.

### Ce qu'il fait étape par étape
1. `M.exiger("relances", ...)` : refuse hors de la machine active (sauf `--essai`).
2. Jour non ouvré (samedi, dimanche, l'un des 11 jours fériés nationaux, Pâques calculé) : rien, code 0.
3. Lit **toutes** les feuilles « Appels Sid AAAA-MM-JJ » du dossier de Sid (`dossier_sid_id` d'appels-sid, jeton Google d'appels-sid, lecture seule). Date de l'appel = date du nom de la feuille.
4. Un lead = un numéro de téléphone (normalisé, +33 accepté ; sans numéro : ignoré). Dernier résultat chaud (« À rappeler », « Je dois réfléchir ») gardé avec nom, ville, note.
5. Exclu si une feuille **plus récente** note ce numéro « RDV pris », « Non catégorique », « Trop cher », « Déjà un site » ou « Pas le temps » (« Pas de réponse » n'exclut pas).
6. Rythme : relance 1 au 3e jour ouvré après l'appel, relance 2 au 7e, puis classé. Note avec « moyen terme » ou « semaines » : une seule relance au 15e. Passage manqué : la relance la plus récente déjà due part le jour ouvré suivant (jamais une relance 1 après la 2). Nouvel appel chaud de Sid : nouveau cycle.
7. Un seul message « À rappeler aujourd'hui » (nom, ville, téléphone, relance n, date d'appel, note de Sid) ; aucun message s'il n'y a rien. Découpé seulement s'il dépasse la taille Discord.
8. `relances-etat.json` : chaque relance annoncée (numéro|date d'appel|n), jamais deux fois ; marquée seulement si Discord a bien reçu (sinon réessayée au prochain passage). Journal sans nom ni numéro, trace du harness.

### Ce qu'il n'a pas le droit de faire
- contacter un prospect, un client ou Sid (seul Liam reçoit le message)
- écrire dans une feuille de Sid
- annoncer deux fois la même relance d'un lead
- plus de deux relances par appel chaud
- relancer un lead noté ensuite RDV pris, Non catégorique, Trop cher, Déjà un site ou Pas le temps
- utiliser une IA ou un service payant
- afficher un secret (jeton, clé, adresse iCal)
- encaisser, publier ou signer
- Engager Liam (envoyer au client, encaisser, publier, signer) : `peut_engager: false`, tout passe par `B2B/a-valider/`.

## Entrées et sorties
**Lit :**
- feuilles Google « Appels Sid AAAA-MM-JJ » du dossier de Sid (lecture seule, jeton d'appels-sid)
- B2B/agents/appels-sid-config.json (dossier_sid_id)
- B2B/agents/relances-config.json

**Écrit :**
- B2B/agents/relances-etat.json
- B2B/agents/relances-journal.log

**Discord :** alertes · **Plafond :** 3 messages par jour · **Envoi au client :** non

## Horaire et état
- **Horaire :** chaque jour à 08:30, plage lundi-vendredi 08:00-19:00
- **Tâche serveur :** entrée dans `B2B/agents/serveur-taches.json` ; tourne seulement si l'agent est dans `agents_actifs` (choix de Liam)
- **Contrat :** valide (`python B2B\harness\valider.py`)
- **Garde branchée :** oui
- Bloque : kill-switch `B2B\STOP`, lien Stripe non autorisé, phrase interdite (OFFRE-REFERENCE.json), secret dans le texte.
- Avertit : machine non active, envoi_automatique = false (simulation), hors horaires du contrat (08:00-19:00), plafond de 3 messages par jour.
- **Tests :** `tests/agents/test_relances.py`
- **Alerte si silence :** après 09:30 (surveillant)

<!-- DYNAMIQUE:DEBUT -->
**Derniers résultats de test (cette machine) :**
- `tests/agents/test_relances.py` : pas encore lancé par `generer-fiches.py --tests`

**Dernière trace :** aucune · **Dernière erreur :** aucune · **Dans agents_actifs (cette machine) :** oui

### Historique (5 dernières traces, sans données client)
- aucune trace sur cette machine
<!-- DYNAMIQUE:FIN -->

## Skill et règles
- `.claude/skills/agent-relances/SKILL.md` (copie : `docs/agents/skills/agent-relances.md`)
- Pas de preuve = pas de fait : « il a tourné » = une trace du jour `ok: true` ci-dessus ; « c'est corrigé » = ses tests puis `tests\b2b-rapide.ps1` en vert.
<!-- GENERE:FIN -->

## Liens et décisions

_Zone conservée à chaque régénération : liens vers docs\decisions et docs clés seulement._

Liens : aucun pour l'instant.

## Notes de Liam

_Zone libre, conservée telle quelle à chaque régénération._
