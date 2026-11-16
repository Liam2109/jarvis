---
agent: videos-marketing
aliases: [📣 Marketing vidéos]
name: videos-marketing
role: "À 05:30, Qwen local propose 3 accroches par script, notées par la grille de Videos/SKILL-VIDEOS.md : la meilleure est gardée (journal-videos.csv), rythme resserré, sous-titres de 2 à 4 mots préparés."
machine: "serveur"
planification: "chaque jour à 05:30, plage tous les jours 05:30-06:15"
sorties: "Videos/scripts/AAAA-MM-JJ-HHMM.json (champ marketing), Videos/journal-videos.csv, Videos/videos-marketing-journal.log"
responsable: Jarvis (CEO)
statut: actif
mode: réel
horaire: "chaque jour à 05:30, plage tous les jours 05:30-06:15"
tags: [agent-b2b]
---
<!-- GENERE:DEBUT (régénéré par python B2B\harness\generer-fiches.py : ne pas modifier) -->
# 📣 Marketing vidéos

**Agent :** `videos-marketing` · **Statut :** actif · **Responsable :** Jarvis (CEO) · **Machine :** serveur
**Horaire :** chaque jour à 05:30, plage tous les jours 05:30-06:15
**Script :** `Videos/agents/marketing.py` · **Contrat :** `B2B/harness/contrats/videos-marketing.json`

## Mission
À 05:30, Qwen local propose 3 accroches par script, notées par la grille du skill : la meilleure est gardée (journal-videos.csv) ; rythme resserré, sous-titres de 2 à 4 mots préparés.

## Ce qu'il fait étape par étape
1. `C.exiger` (machine active) puis `C.exiger_regles` (skill présent et complet, sinon refus code 3).
2. Pour chaque script du jour sans champ `marketing` : Qwen choisit 3 formules de la ligne dans `Videos/hooks.md` (`- A01 | …`, `- B01 | …`) et remplit leurs trous (1 à 4 mots) ; il n'invente aucune phrase. Formule inconnue ou trou invalide = rejeté, complété par des formules sans trou (jamais inventées). Ligne B : la première phrase du brouillon de Liam concourt aussi (si elle est différente).
3. `noter_accroche` : note sur 10 (forme qui accroche +3, courte +3, adresse directe +2, concrète +1, neuve +1, ouverture molle −3) ; éliminée (0) si chiffre, promesse, mot interdit, phrase molle, mauvais public (A : vouvoyer l'artisan, jamais son client ; B : tutoyer le futur call caller), adresse épelée ou lieu (ligne B). L'accroche écran = l'accroche gardée (7 mots au plus). La meilleure remplace la première phrase ; égalité = la plus courte.
4. Rythme : phrase de plus de 11 mots coupée en deux (une image toutes les 2 à 4 s) ; durée estimée (2,6 mots/s + carte de fin) comparée à 20-35 s.
5. Sous-titres : groupes de 2 à 4 mots, mot clé (le plus long mot plein) en couleur d'accent ; utilisés par l'agent Création.
6. Une ligne dans `Videos/journal-videos.csv` (accroche gardée, sa note et celle des autres) et une dans le journal de l'agent.

## Entrées et sorties
**Lit :**
- Videos/SKILL-VIDEOS.md
- Videos/hooks.md
- Videos/videos-config.json
- Videos/scripts/AAAA-MM-JJ-HHMM.json
- Videos/journal-videos.csv

**Écrit :**
- Videos/scripts/AAAA-MM-JJ-HHMM.json (champs marketing, accroche, phrases, sous_titres)
- Videos/journal-videos.csv
- Videos/videos-marketing-journal.log

**Discord :** aucun · **Plafond :** 0 messages par jour · **Envoi au client :** non

## Ce qu'il n'a pas le droit de faire
- garder une accroche avec un chiffre, une promesse, un témoignage, une phrase molle ou un lieu (ligne B)
- inventer un revenu ou un nombre de ventes
- utiliser un modèle payant ou des tokens Claude
- publier, liker, s'abonner, commenter ou envoyer un message sur TikTok
- toucher à memoire/, .env, config.json, .obsidian/ ou un fichier *.local.json
- afficher un secret (jeton, clé, adresse iCal)
- envoyer au client, encaisser ou signer
- Engager Liam (envoyer au client, encaisser, publier, signer) : `peut_engager: false`, tout passe par `B2B/a-valider/`.

## Harness
- **Contrat :** valide (`python B2B\harness\valider.py`)
- **Garde branchée :** non
- Bloque : kill-switch `B2B\STOP`, lien Stripe non autorisé, phrase interdite (OFFRE-REFERENCE.json), secret dans le texte.
- Avertit : machine non active, envoi_automatique = false (simulation), hors horaires du contrat (05:30-06:15), plafond de 0 messages par jour.
- **Tests :** `tests/agents/test_videos.py`
- **Alerte si silence :** après 06:15 (surveillant)

<!-- DYNAMIQUE:DEBUT -->
**Derniers résultats de test (cette machine) :**
- `tests/agents/test_videos.py` : pas encore lancé par `generer-fiches.py --tests`

**Dernière trace :** aucune

### Historique (5 dernières traces, sans données client)
- aucune trace sur cette machine
<!-- DYNAMIQUE:FIN -->

## Skill
- `.claude/skills/agent-videos-marketing/SKILL.md` (copie : `docs/agents/skills/agent-videos-marketing.md`)
<!-- GENERE:FIN -->

## Liens et décisions

_Zone conservée à chaque régénération : liens vers docs\decisions et docs clés seulement._

Liens : aucun pour l'instant.

## Notes de Liam

_Zone libre, conservée telle quelle à chaque régénération._
