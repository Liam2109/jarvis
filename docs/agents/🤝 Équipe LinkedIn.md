---
agent: linkedin-equipe
aliases: [🤝 Équipe LinkedIn]
name: linkedin-equipe
role: "Chaque jour ouvré à 08:00, prépare le lot LinkedIn du jour pour le tableau de bord (post, commentaires, demandes de connexion, DM, relances) ; Liam envoie tout lui-même."
machine: "serveur"
planification: "chaque jour à 08:00, plage lundi-vendredi 08:00-19:00"
sorties: "B2B/linkedin/equipe.json (cibles, suivi, textes), dashboard/data/linkedin.json et linkedin.js (rubrique LinkedIn), B2B/donnees/registre-entreprises.json (seulement une réponse positive cochée par Liam : lead chaud), B2B/agents/linkedin-equipe-journal.log"
responsable: Prospection
statut: actif
mode: réel
horaire: "chaque jour à 08:00, plage lundi-vendredi 08:00-19:00"
tags: [agent-b2b]
---
<!-- GENERE:DEBUT (régénéré par python B2B\harness\generer-fiches.py : ne pas modifier) -->
# 🤝 Équipe LinkedIn

**Agent :** `linkedin-equipe` · **Statut :** actif · **Responsable :** Prospection (pôle) · **Machine :** serveur
**Horaire :** chaque jour à 08:00, plage lundi-vendredi 08:00-19:00
**Script :** `B2B/agents/linkedin-equipe.py` · **Contrat :** `B2B/harness/contrats/linkedin-equipe.json`

## Rôle et limites
### Mission
Chaque jour ouvré à 08:00, prépare le lot LinkedIn du jour pour le tableau de bord (post, commentaires, demandes de connexion, DM, relances) ; Liam envoie tout lui-même.

### Ce qu'il fait étape par étape
à compléter par Liam (aucun skill ne décrit les étapes).

### Ce qu'il n'a pas le droit de faire
- envoyer une demande de connexion ou un message sur LinkedIn (Liam copie et envoie lui-même)
- scraper ou automatiser LinkedIn, utiliser son API ou se connecter à un compte
- modifier la file des posts de l'agent linkedin ou l'activer
- dépasser 100 demandes de connexion par semaine (plafond_semaine) ou 20 par jour ouvré (demandes_par_jour)
- écrire un DM ou une relance avec emoji, tutoiement, promesse, chiffre non vérifié, lien, coordonnées ou présentiel
- relancer plus d'une fois la même personne
- contacter une entreprise déjà contactée (e-mail, appel, registre)
- donner un conseil d'achat ou de vente financier
- afficher un secret (jeton, clé)
- encaisser, publier ou signer
- Engager Liam (envoyer au client, encaisser, publier, signer) : `peut_engager: false`, tout passe par `B2B/a-valider/`.

## Entrées et sorties
**Lit :**
- B2B/prospects_rouen.csv, B2B/prospects.csv, B2B/prospection-trouves.csv (cibles déjà trouvées)
- B2B/suivi-prospects.csv et B2B/donnees/registre-entreprises.json (déjà contactés : exclus)
- B2B/linkedin/lot-AAAA-MM-JJ.md et file.json (posts de l'agent linkedin, lecture seule)
- B2B/agents/linkedin-equipe-config.json

**Écrit :**
- B2B/linkedin/equipe.json (cibles, suivi, textes)
- dashboard/data/linkedin.json et linkedin.js (rubrique LinkedIn)
- B2B/donnees/registre-entreprises.json (seulement une réponse positive cochée par Liam : lead chaud)
- B2B/agents/linkedin-equipe-journal.log

**Discord :** aucun · **Plafond :** 0 messages par jour · **Envoi au client :** non

## Horaire et état
- **Horaire :** chaque jour à 08:00, plage lundi-vendredi 08:00-19:00
- **Tâche serveur :** entrée dans `B2B/agents/serveur-taches.json` ; tourne seulement si l'agent est dans `agents_actifs` (choix de Liam)
- **Contrat :** valide (`python B2B\harness\valider.py`)
- **Garde branchée :** non
- Bloque : kill-switch `B2B\STOP`, lien Stripe non autorisé, phrase interdite (OFFRE-REFERENCE.json), secret dans le texte.
- Avertit : machine non active, envoi_automatique = false (simulation), hors horaires du contrat (08:00-19:00), plafond de 0 messages par jour.
- **Tests :** `tests/agents/test_linkedin_equipe.py`
- **Alerte si silence :** après 09:00 (surveillant)

<!-- DYNAMIQUE:DEBUT -->
**Derniers résultats de test (cette machine) :**
- `tests/agents/test_linkedin_equipe.py` : pas encore lancé par `generer-fiches.py --tests`

**Dernière trace :** aucune · **Dernière erreur :** aucune · **Dans agents_actifs (cette machine) :** non (Liam l'ajoute s'il veut le planifier)

### Historique (5 dernières traces, sans données client)
- aucune trace sur cette machine
<!-- DYNAMIQUE:FIN -->

## Skill et règles
- `.claude/skills/agent-linkedin-equipe/SKILL.md` (copie : `docs/agents/skills/agent-linkedin-equipe.md`)
- Pas de preuve = pas de fait : « il a tourné » = une trace du jour `ok: true` ci-dessus ; « c'est corrigé » = ses tests puis `tests\b2b-rapide.ps1` en vert.
<!-- GENERE:FIN -->

## Liens et décisions

_Zone conservée à chaque régénération : liens vers docs\decisions et docs clés seulement._

Liens : aucun pour l'instant.

## Notes de Liam

_Zone libre, conservée telle quelle à chaque régénération._
