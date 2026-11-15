---
agent: instagram
statut: arrêté
responsable: Prospection
horaire: "à la demande (aucune tâche serveur), plage tous les jours 12:30-14:00"
machine: gros PC
tags: [agent-b2b]
---
<!-- GENERE:DEBUT (régénéré par python B2B\harness\generer-fiches.py : ne pas modifier) -->
# instagram

**Statut :** arrêté · **Responsable :** [[responsable-prospection|Responsable Prospection]] · **Machine :** gros PC
**Horaire :** à la demande (aucune tâche serveur), plage tous les jours 12:30-14:00
**Script :** `B2B/agents/instagram.py` · **Contrat :** `B2B/harness/contrats/instagram.json`

## Mission
Publier un post par jour à 12:30 (agent retiré par décision de Liam).

## Ce qu'il fait étape par étape
1. `jour` : si c'est l'heure (12:30 heure de Paris, fenêtre de 90 minutes), prend le prochain post de la file `docs\INSTAGRAM-PLAN.md`.
2. Vérifie la légende (mots interdits : garanti, n° 1, meilleur, avis, prix en €, etc.) et le fichier (image ou vidéo).
3. Publie par l'API officielle Instagram (Graph API, jeton dans `instagram-token.json`, hors git, jamais affiché) ; en simulation (défaut), rien n'est publié ni coché.
4. Coche la ligne du plan avec la date.
5. `visuels` : file sous 3 posts → fabrique les prochaines cartes, à valider par Liam dans `instagram-a-valider.md` ; `valider` les ajoute à la file.

## Entrées et sorties
**Lit :**
- B2B/docs/INSTAGRAM-PLAN.md

**Écrit :**
- état instagram

**Discord :** instagram · **Plafond :** 1 messages par jour · **Envoi au client :** non

## Ce qu'il n'a pas le droit de faire
- envoyer au client sans accord de Liam
- encaisser ou rembourser
- publier
- signer ou promettre un résultat
- afficher un secret (jeton, clé, adresse iCal)
- Engager Liam (envoyer au client, encaisser, publier, signer) : `peut_engager: false`, tout passe par `B2B/a-valider/`.

## Harness
- **Contrat :** valide (`python B2B\harness\valider.py`)
- **Garde branchée :** partielle : alertes Discord gardées, publication Instagram non gardée (agent retiré)
- Bloque : kill-switch `B2B\STOP`, lien Stripe non autorisé, phrase interdite (OFFRE-REFERENCE.json), secret dans le texte.
- Avertit : machine non active, envoi_automatique = false (simulation), hors horaires du contrat (12:30-14:00), plafond de 1 messages par jour.
- **Tests :** `B2B/agents/test_instagram.py`
- **Alerte si silence :** aucune

<!-- DYNAMIQUE:DEBUT -->
**Derniers résultats de test (cette machine) :**
- `B2B/agents/test_instagram.py` : réussi le 2026-11-15 19:34

**Dernière trace :** aucune

### Historique (5 dernières traces, sans données client)
- aucune trace sur cette machine
<!-- DYNAMIQUE:FIN -->

## Skill
- [[skills/agent-instagram|agent-instagram]]

## Liens
- Responsable : [[responsable-prospection|Responsable Prospection]]
- Direction : [[jarvis-ceo|Jarvis (CEO)]] · [[00-ORGANIGRAMME|Organigramme]]
<!-- GENERE:FIN -->

## Notes de Liam

_Zone libre, conservée telle quelle à chaque régénération._
