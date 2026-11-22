---
agent: superviseur-vente
aliases: [🛒 Superviseur Vente]
name: superviseur-vente
role: "Toutes les 30 min : les agents de la vente ont-ils tourne, leurs donnees se contredisent-elles ? Corrige le sans risque, alerte et attend « go » pour tout ce qui touche a l'argent."
machine: "serveur"
planification: "toutes les 30 min, plage tous les jours 07:00-22:00"
sorties: "B2B/agents/devis-etat.json (cle manquante ajoutee vide, doublon identique retire), B2B/agents/reponses-traitees.json (doublon identique retire), B2B/agents/superviseur-vente-etat.json, B2B/agents/superviseur-vente-journal.log, B2B/a-valider/AAAA-MM-JJ-superviseur-vente.md"
responsable: Vente
statut: arrêté
horaire: "toutes les 30 min, plage tous les jours 07:00-22:00"
tags: [agent-b2b]
---
<!-- GENERE:DEBUT (régénéré par python B2B\harness\generer-fiches.py : ne pas modifier) -->
# 🛒 Superviseur Vente

**Agent :** `superviseur-vente` · **Statut :** arrêté · **Responsable :** Vente (pôle) · **Machine :** serveur
**Horaire :** toutes les 30 min, plage tous les jours 07:00-22:00
**Script :** `B2B/agents/superviseur-vente.py` · **Contrat :** `B2B/harness/contrats/superviseur-vente.json`

## Rôle et limites
### Mission
Toutes les 30 min : les agents de la vente ont-ils tourne, leurs donnees se contredisent-elles ? Corrige le sans risque, alerte et attend « go » pour tout ce qui touche a l'argent.

### Ce qu'il fait étape par étape
1. `M.exiger("superviseur-vente", ...)` : refuse hors de la machine active (sauf `--essai`).
2. Pour chaque agent suivi : son état est lu dans ses **traces** du jour (`B2B/logs/agents/<agent>/`) et dans sa tâche (`serveur-taches.json`).
   Un agent absent de `agents_actifs`, désactivé, pas encore actif ou hors de ses jours n'est jamais signalé : il n'a pas de tâche sur cette machine.
   « erreur » = dernier passage du jour `ok: false` ; « silence » = heure fixe + délai de grâce passés sans passage ; « bloque » = agent cyclique muet depuis plus de 3 cycles + grâce.
3. Agent en erreur, silencieux ou bloqué : **relancé une fois**, avec la commande de sa tâche serveur, puis noté au journal. Au passage suivant, s'il est toujours en défaut : alerte, plus de relance (jamais deux par jour).
4. Contrôles de cohérence : `devis-etat.json` (clés attendues, doublons de `ok_utilises`, dates des alertes, prix comparé à `B2B/docs/OFFRE-REFERENCE.json`),
   `stripe-alerte-etat.json` et `chiffres-serveur-etat.json` (fichiers d'argent), `rendez-vous-etat.json` (échecs de lecture de l'agenda),
   `reponses-traitees.json` (doublons), la partie financière de `dashboard/ventes.json` si elle est là, et les brouillons du jour de `B2B/a-valider` plus `B2B/messages-a-valider.md`.
5. **Corrige seul** (rien ne peut être perdu) : clé d'état manquante ajoutée **vide**, doublon **strictement identique** retiré (la première ligne reste), liste remise dans l'ordre des dates, relance d'un agent.
6. **Ne touche jamais** : un fichier d'argent (même une clé manquante : remettre `dernier_ts` à zéro réannoncerait d'anciens paiements), un montant, un prix, un devis, un chiffre du tableau de bord, un brouillon destiné à Liam ou à un client, un fichier illisible, une donnée en double qu'il faudrait choisir, une date illogique. Dans tous ces cas : une alerte Discord et une ligne dans `B2B/a-valider/AAAA-MM-JJ-superviseur-vente.md`, puis il attend le « go ».
7. Discord : un résumé court par jour même quand tout va bien (à partir de `heure_resume`), plus un message dès qu'il corrige ou découvre quelque chose de neuf. Jamais la nuit (plage 07:00-22:00) : une alerte de 3 h attend le passage du matin. Même souci = annoncé une seule fois.

### Ce qu'il n'a pas le droit de faire
- ecrire dans un fichier d'argent (stripe-alerte-etat.json, chiffres-serveur-etat.json) : signale seulement
- modifier un brouillon destine a Liam ou a un client
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
- B2B/agents/devis-etat.json
- B2B/agents/stripe-alerte-etat.json
- B2B/agents/chiffres-serveur-etat.json
- B2B/agents/rendez-vous-etat.json
- B2B/agents/reponses-traitees.json
- dashboard/ventes.json (si present)
- B2B/a-valider du jour et B2B/messages-a-valider.md (phrases interdites, liens de paiement, secrets)
- B2B/docs/OFFRE-REFERENCE.json (prix de reference)

**Écrit :**
- B2B/agents/devis-etat.json (cle manquante ajoutee vide, doublon identique retire)
- B2B/agents/reponses-traitees.json (doublon identique retire)
- B2B/agents/superviseur-vente-etat.json
- B2B/agents/superviseur-vente-journal.log
- B2B/a-valider/AAAA-MM-JJ-superviseur-vente.md

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

**Dernière trace :** aucune · **Dernière erreur :** aucune · **Dans agents_actifs (cette machine) :** non (Liam l'ajoute s'il veut le planifier)

### Historique (5 dernières traces, sans données client)
- aucune trace sur cette machine
<!-- DYNAMIQUE:FIN -->

## Skill et règles
- `.claude/skills/agent-superviseur-vente/SKILL.md` (copie : `docs/agents/skills/agent-superviseur-vente.md`)
- Pas de preuve = pas de fait : « il a tourné » = une trace du jour `ok: true` ci-dessus ; « c'est corrigé » = ses tests puis `tests\b2b-rapide.ps1` en vert.
<!-- GENERE:FIN -->

## Liens et décisions

_Zone conservée à chaque régénération : liens vers docs\decisions et docs clés seulement._

Rattaché à : [[docs/agents/🧠 Jarvis (CEO)|🧠 Jarvis (CEO)]]
Agents suivis (Vente) : [[docs/agents/🧾 Devis|🧾 Devis]] · [[docs/agents/📊 Chiffres serveur|📊 Chiffres serveur]] · [[docs/agents/💶 Alerte Stripe|💶 Alerte Stripe]] · [[docs/agents/📅 Rendez-vous|📅 Rendez-vous]] · [[docs/agents/💬 Réponses|💬 Réponses]]

## Notes de Liam

_Zone libre, conservée telle quelle à chaque régénération._
