---
agent: reponses
aliases: [💬 Réponses]
name: reponses
role: Trier les réponses reçues aux e-mails et tenir la liste d'exclusion (STOP, refus)
machine: serveur DESKTOP-HLQSTAU (si listé dans agents_actifs)
planification: toutes les 15 min (serveur-taches.json, « --jours 14 »)
depend_de: agent-prospection
sorties: reponses-traitees.json, exclus-emails.json (hors git)
responsable: Vente
statut: actif
mode: réel
horaire: "toutes les 15 min, plage tous les jours 00:00-24:00"
tags: [agent-b2b]
---
<!-- GENERE:DEBUT (régénéré par python B2B\harness\generer-fiches.py : ne pas modifier) -->
# 💬 Réponses

**Agent :** `reponses` · **Statut :** actif · **Responsable :** Vente (pôle) · **Machine :** serveur
**Horaire :** toutes les 15 min, plage tous les jours 00:00-24:00
**Script :** `B2B/agents/reponses.py` · **Contrat :** `B2B/harness/contrats/reponses.json`

## Rôle et limites
### Mission
Lire les réponses des prospects, les classer et prévenir Liam sur Discord avec deux créneaux proposés ; aucun envoi au prospect.

### Ce qu'il fait étape par étape
1. Machine active obligatoire. Hors `--a-blanc`, vérifie salon, identifiant Discord de Liam et jeton du bot ; s'il en manque : « À COMPLÉTER … », arrêt.
2. Lit l'agenda iCal (adresse dans `B2B\.env`) pour calculer 2 créneaux de 15 minutes libres, jamais réservés.
3. Lit la boîte Gmail en lecture seule : API OAuth si « api » est actif dans `reponses-config.json`, sinon les 2 boîtes en IMAP.
4. N'ouvre que les messages d'un e-mail connu de `suivi-prospects.csv` ou du même fil ; les autres : en-tête seulement.
5. Classe : STOP, négative, positive, autre ; **le doute donne « autre »**.
6. Applique : négative ou STOP → statut « refusé » / « STOP », nom et adresses exclus ; positive → « répondu » ; autre → relance J+2 annulée. Jamais sur un prospect déjà en devis, signé, STOP ou refusé.
7. Positive : message « 🚨 PRIORITÉ » salon important (avec les 2 créneaux) ; autres : résumé salon réponses.
8. Mémorise l'identifiant du message dans `reponses-traitees.json` seulement si Discord l'a pris.
9. Note rebonds et plaintes dans `prospection-retours.json`, ajoute les adresses rebondies à `exclus-emails.json`.

### Ce qu'il n'a pas le droit de faire
- envoyer au client sans accord de Liam
- encaisser ou rembourser
- publier
- signer ou promettre un résultat
- afficher un secret (jeton, clé, adresse iCal)
- répondre au prospect
- Engager Liam (envoyer au client, encaisser, publier, signer) : `peut_engager: false`, tout passe par `B2B/a-valider/`.

## Entrées et sorties
**Lit :**
- boîtes mail (lecture)
- agenda (créneaux)
- suivi-prospects.csv

**Écrit :**
- reponses-traitees.json
- suivi-prospects.csv
- exclus-emails.json

**Discord :** reponses · **Plafond :** 40 messages par jour · **Envoi au client :** non

## Horaire et état
- **Horaire :** toutes les 15 min, plage tous les jours 00:00-24:00
- **Tâche serveur :** entrée dans `B2B/agents/serveur-taches.json` ; tourne seulement si l'agent est dans `agents_actifs` (choix de Liam)
- **Contrat :** valide (`python B2B\harness\valider.py`)
- **Garde branchée :** oui
- Bloque : kill-switch `B2B\STOP`, lien Stripe non autorisé, phrase interdite (OFFRE-REFERENCE.json), secret dans le texte.
- Avertit : machine non active, envoi_automatique = false (simulation), hors horaires du contrat (00:00-24:00), plafond de 40 messages par jour.
- **Tests :** `B2B/agents/test_reponses.py`
- **Alerte si silence :** après 19:30 (surveillant)

<!-- DYNAMIQUE:DEBUT -->
**Derniers résultats de test (cette machine) :**
- `B2B/agents/test_reponses.py` : pas encore lancé par `generer-fiches.py --tests`

**Dernière trace :** 2026-11-24 23:51 ok · **Dernière erreur :** aucune · **Dans agents_actifs (cette machine) :** oui

### Historique (5 dernières traces, sans données client)
- 2026-11-24 23:51 | --jours 14 | ok | 8.81 s
- 2026-11-24 23:36 | --jours 14 | ok | 8.39 s
- 2026-11-24 23:21 | --jours 14 | ok | 8.76 s
- 2026-11-24 23:07 | --jours 14 | ok | 8.79 s
- 2026-11-24 22:51 | --jours 14 | ok | 8.55 s
<!-- DYNAMIQUE:FIN -->

## Skill et règles
- `.claude/skills/agent-reponses/SKILL.md` (copie : `docs/agents/skills/agent-reponses.md`)
- Pas de preuve = pas de fait : « il a tourné » = une trace du jour `ok: true` ci-dessus ; « c'est corrigé » = ses tests puis `tests\b2b-rapide.ps1` en vert.
<!-- GENERE:FIN -->

## Liens et décisions

_Zone conservée à chaque régénération : liens vers docs\decisions et docs clés seulement._

Un « STOP » est définitif : l'adresse ne sera plus jamais contactée.
Détail : `B2B/agents/reponses.md`
Liens : [[docs/decisions/📌 Validation à la main|📌 Validation à la main]]

## Notes de Liam

_Zone libre, conservée telle quelle à chaque régénération._
