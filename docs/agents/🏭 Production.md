---
agent: production
aliases: [🏭 Production]
name: production
role: "Produire le site du client après paiement, le faire valider par Liam avant toute mise en ligne."
machine: "à compléter par Liam"
planification: "à compléter par Liam"
sorties: "B2B/a-valider/AAAA-MM-JJ-production.md"
responsable: Production
statut: prévu
horaire: "à compléter par Liam"
tags: [agent-b2b]
---
<!-- GENERE:DEBUT (régénéré par python B2B\harness\generer-fiches.py : ne pas modifier) -->
# 🏭 Production

**Agent :** `production` · **Statut :** prévu · **Responsable :** Production (pôle) · **Machine :** à compléter par Liam
**Horaire :** à compléter par Liam
**Script :** à compléter par Liam (aucun script) · **Contrat :** `B2B/harness/contrats/production.json`

## Rôle et limites
### Mission
Produire le site du client après paiement, le faire valider par Liam avant toute mise en ligne.

### Ce qu'il fait étape par étape
à compléter par Liam (agent non construit).

### Ce qu'il n'a pas le droit de faire
- envoyer au client sans accord de Liam
- encaisser ou rembourser
- publier
- signer ou promettre un résultat
- afficher un secret (jeton, clé, adresse iCal)
- mettre en ligne sans accord
- Engager Liam (envoyer au client, encaisser, publier, signer) : `peut_engager: false`, tout passe par `B2B/a-valider/`.

## Entrées et sorties
**Lit :**
- devis signé
- paiement Stripe (lecture)

**Écrit :**
- B2B/a-valider/AAAA-MM-JJ-production.md

**Discord :** pages · **Plafond :** 10 messages par jour · **Envoi au client :** non

## Horaire et état
- **Horaire :** à compléter par Liam
- **Tâche serveur :** aucune dans serveur-taches.json
- **Contrat :** valide (`python B2B\harness\valider.py`)
- **Garde branchée :** à brancher avant activation
- Bloque : kill-switch `B2B\STOP`, lien Stripe non autorisé, phrase interdite (OFFRE-REFERENCE.json), secret dans le texte.
- Avertit : machine non active, envoi_automatique = false (simulation), hors horaires du contrat (08:00-19:00), plafond de 10 messages par jour.
- **Tests :** aucun : à compléter par Liam
- **Alerte si silence :** aucune

<!-- DYNAMIQUE:DEBUT -->
**Derniers résultats de test (cette machine) :**
- aucun test

**Dernière trace :** aucune · **Dernière erreur :** aucune · **Dans agents_actifs (cette machine) :** non (Liam l'ajoute s'il veut le planifier)

### Historique (5 dernières traces, sans données client)
- aucune trace sur cette machine
<!-- DYNAMIQUE:FIN -->

## Skill et règles
- `.claude/skills/agent-production/SKILL.md` (copie : `docs/agents/skills/agent-production.md`)
- Pas de preuve = pas de fait : « il a tourné » = une trace du jour `ok: true` ci-dessus ; « c'est corrigé » = ses tests puis `tests\b2b-rapide.ps1` en vert.
<!-- GENERE:FIN -->

## Liens et décisions

_Zone conservée à chaque régénération : liens vers docs\decisions et docs clés seulement._

Liens : aucun pour l'instant.

## Notes de Liam

_Zone libre, conservée telle quelle à chaque régénération._
