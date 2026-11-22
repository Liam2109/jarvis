---
agent: superviseur-prospection
aliases: [🧭 Superviseur Prospection]
name: superviseur-prospection
role: "Toutes les 30 min : les agents de la prospection ont-ils tourne, un prospect est-il compte deux fois, une date est-elle illogique ? Corrige le sans risque, alerte pour le reste."
machine: "serveur"
planification: "toutes les 30 min, plage tous les jours 07:00-22:00"
sorties: "B2B/agents/relances-etat.json (cle manquante ajoutee vide), B2B/agents/appels-sid-etat.json (cle manquante ajoutee vide), B2B/agents/prospection-etat.json (cle manquante ajoutee vide, doublon identique retire), dashboard/data/historique.json (jours remis dans l'ordre des dates), B2B/agents/superviseur-prospection-etat.json, B2B/agents/superviseur-prospection-journal.log, B2B/a-valider/AAAA-MM-JJ-superviseur-prospection.md"
responsable: Prospection
statut: arrêté
horaire: "toutes les 30 min, plage tous les jours 07:00-22:00"
tags: [agent-b2b]
---
<!-- GENERE:DEBUT (régénéré par python B2B\harness\generer-fiches.py : ne pas modifier) -->
# 🧭 Superviseur Prospection

**Agent :** `superviseur-prospection` · **Statut :** arrêté · **Responsable :** Prospection (pôle) · **Machine :** serveur
**Horaire :** toutes les 30 min, plage tous les jours 07:00-22:00
**Script :** `B2B/agents/superviseur-prospection.py` · **Contrat :** `B2B/harness/contrats/superviseur-prospection.json`

## Rôle et limites
### Mission
Toutes les 30 min : les agents de la prospection ont-ils tourne, un prospect est-il compte deux fois, une date est-elle illogique ? Corrige le sans risque, alerte pour le reste.

### Ce qu'il fait étape par étape
1. `M.exiger("superviseur-prospection", ...)` : refuse hors de la machine active (sauf `--essai`).
2. État de chaque agent suivi, lu dans ses traces du jour et dans sa tâche serveur (mêmes règles que le Superviseur Vente : un agent absent de `agents_actifs`,
   désactivé ou hors de ses jours n'est jamais signalé ; le samedi, un agent des jours ouvrés a le droit de se taire).
3. Agent en erreur, silencieux ou bloqué : **relancé une fois** par jour, puis alerte s'il reste en défaut.
4. Contrôles de cohérence :
   - `relances-etat.json` : clés attendues ; clé d'annonce bien formée (« téléphone|date d'appel|numéro de relance ») ; aucune date d'appel dans le futur ;
     le compte d'envois d'un jour ne dépasse pas les relances mémorisées pour ce jour.
   - `appels-sid-etat.json` : clés attendues, dates des listes déjà préparées. `appels-sid-historique.json` : aucun numéro marqué appelé à une date future, aucune entrée sans date.
   - `prospection-etat.json` : clés attendues, doublons de la liste des relances d'e-mails (un prospect relancé deux fois), dates des lots préparés et envoyés.
   - `dashboard/data/historique.json` (si le fichier est là) : une seule entrée par jour, dans l'ordre des dates, et jamais plus de leads chauds ou de rendez-vous que d'appels.
5. **Corrige seul** : clé d'état manquante ajoutée vide, doublon strictement identique retiré, `jours` de l'historique remis dans l'ordre des dates, relance d'un agent.
6. **Ne touche jamais** : une relance déjà annoncée (la supprimer ferait rappeler le lead deux fois), deux entrées pour le même jour (Liam choisit laquelle garder),
   une date dans le futur, une clé mal formée, un chiffre d'appels, de leads ou de rendez-vous. Alerte Discord + ligne dans `B2B/a-valider/AAAA-MM-JJ-superviseur-prospection.md`, puis il attend le « go ».
7. Discord : un résumé court par jour même quand tout va bien, plus un message dès qu'il y a du neuf ; rien entre 22:00 et 07:00 ; même souci annoncé une seule fois.

### Ce qu'il n'a pas le droit de faire
- supprimer une relance deja annoncee (le lead serait relance deux fois)
- recalculer un chiffre d'appels, de leads ou de rendez-vous
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
- B2B/harness/contrats (horaires attendus)
- B2B/logs/agents (traces du jour)
- B2B/agents/serveur-taches.json
- B2B/agents/relances-etat.json
- B2B/agents/appels-sid-etat.json
- B2B/agents/appels-sid-historique.json
- B2B/agents/prospection-etat.json
- dashboard/data/historique.json (si present)

**Écrit :**
- B2B/agents/relances-etat.json (cle manquante ajoutee vide)
- B2B/agents/appels-sid-etat.json (cle manquante ajoutee vide)
- B2B/agents/prospection-etat.json (cle manquante ajoutee vide, doublon identique retire)
- dashboard/data/historique.json (jours remis dans l'ordre des dates)
- B2B/agents/superviseur-prospection-etat.json
- B2B/agents/superviseur-prospection-journal.log
- B2B/a-valider/AAAA-MM-JJ-superviseur-prospection.md

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

**Dernière trace :** 2026-11-22 17:51 ok · **Dernière erreur :** aucune · **Dans agents_actifs (cette machine) :** oui

### Historique (5 dernières traces, sans données client)
- 2026-11-22 17:51 | passage | ok | 0.9 s
- 2026-11-22 17:51 | passage | ok | 0.68 s
- 2026-11-22 17:51 | garde discord | ok (AVERTIT : envoi_automatique = false : l'agent devrait être en simulation) | 0.0 s
<!-- DYNAMIQUE:FIN -->

## Skill et règles
- `.claude/skills/agent-superviseur-prospection/SKILL.md` (copie : `docs/agents/skills/agent-superviseur-prospection.md`)
- Pas de preuve = pas de fait : « il a tourné » = une trace du jour `ok: true` ci-dessus ; « c'est corrigé » = ses tests puis `tests\b2b-rapide.ps1` en vert.
<!-- GENERE:FIN -->

## Liens et décisions

_Zone conservée à chaque régénération : liens vers docs\decisions et docs clés seulement._

Rattaché à : [[docs/agents/🧠 Jarvis (CEO)|🧠 Jarvis (CEO)]]
Agents suivis (Prospection) : [[docs/agents/☎️ Relances leads|☎️ Relances leads]] · [[docs/agents/📞 Appels Sid|📞 Appels Sid]] · [[docs/agents/🔎 Prospection|🔎 Prospection]]

## Notes de Liam

_Zone libre, conservée telle quelle à chaque régénération._
