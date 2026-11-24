---
agent: videos-nettoyage
aliases: [🧽 Nettoyage vidéos]
name: videos-nettoyage
role: "À 03:30, sans token : supprime dans Videos les .mp4 et intermédiaires de plus de nettoyage_jours jours (14, config), après une ligne dans journal-videos.csv."
machine: "serveur"
planification: "chaque jour à 03:30, plage tous les jours 03:30-04:15"
sorties: "Videos/journal-videos.csv, Videos/videos-nettoyage-journal.log"
responsable: Jarvis (CEO)
statut: actif
mode: réel
horaire: "chaque jour à 03:30, plage tous les jours 03:30-04:15"
tags: [agent-b2b]
---
<!-- GENERE:DEBUT (régénéré par python B2B\harness\generer-fiches.py : ne pas modifier) -->
# 🧽 Nettoyage vidéos

**Agent :** `videos-nettoyage` · **Statut :** actif · **Responsable :** Jarvis (CEO) · **Machine :** serveur
**Horaire :** chaque jour à 03:30, plage tous les jours 03:30-04:15
**Script :** `Videos/agents/nettoyage.ps1` · **Contrat :** `B2B/harness/contrats/videos-nettoyage.json`

## Rôle et limites
### Mission
À 03:30, sans token : supprime dans Videos les .mp4 et intermédiaires de plus de nettoyage_jours jours (14, config), après une ligne dans journal-videos.csv ; skill, scripts et veille intacts.

### Ce qu'il fait étape par étape
1. Refuse (code 3) si cette machine n'est pas la machine active (`B2B\agents\b2b.local.json`).
2. Lit `nettoyage_jours`, `nettoyage_extensions` et `videos_protegees` dans la config vidéo (jamais dans le code) ; un document, un script ou un réglage (.md, .py, .ps1, .json, .txt, .csv) n'est jamais une extension à supprimer.
3. Cherche les fichiers plus vieux que la limite dans `a-valider`, `publiees`, `travail` et `outils\stickfigure-pipeline-v2\output` seulement (jamais `node_modules`).
4. Pour chaque vidéo finie : une ligne dans `Videos\journal-videos.csv` (date, nom, statut, hook lu dans son .json), puis suppression de la vidéo, de sa légende et de son .json. Pour les intermédiaires : une ligne par dossier, puis suppression.
5. Retire les dossiers vides de `travail`, écrit un résumé dans `Videos\videos-nettoyage-journal.log`.

### Ce qu'il n'a pas le droit de faire
- supprimer hors de Videos, ou dans agents, scripts, veille, node_modules
- supprimer SKILL-VIDEOS.md, hooks, README, la config ou une vidéo de videos_protegees
- supprimer sans avoir écrit la ligne de journal-videos.csv
- lire ou utiliser un token
- toucher à memoire/, .env, config.json, .obsidian/ ou un fichier *.local.json
- envoyer au client, encaisser ou signer
- Engager Liam (envoyer au client, encaisser, publier, signer) : `peut_engager: false`, tout passe par `B2B/a-valider/`.

## Entrées et sorties
**Chaîne vidéo :** Veille → Scripts → Marketing → Création → Monteur (ligne B) → Ton OK de Liam (« go publier », une fois par ligne) → Publication (verrouillée) → **Nettoyage** (fiche « ⛓️ Chaîne vidéo »)
- **Reçoit de :** Publication (verrouillée) : vidéo publiée, déplacée dans Videos/publiees
- **Produit :** vieux fichiers supprimés après une ligne de journal-videos.csv
- **Passe à :** aucun (dernier maillon)

**Lit :**
- Videos/videos-config.json (nettoyage_jours, nettoyage_extensions, videos_protegees)
- Videos/a-valider
- Videos/publiees
- Videos/travail
- Videos/outils/stickfigure-pipeline-v2/output

**Écrit :**
- Videos/journal-videos.csv
- Videos/videos-nettoyage-journal.log
- suppressions dans Videos/a-valider, publiees, travail, outils/stickfigure-pipeline-v2/output

**Discord :** aucun · **Plafond :** 0 messages par jour · **Envoi au client :** non

## Horaire et état
- **Horaire :** chaque jour à 03:30, plage tous les jours 03:30-04:15
- **Tâche serveur :** entrée dans `B2B/agents/serveur-taches.json`, active à partir du 2026-11-17 ; tourne seulement si l'agent est dans `agents_actifs` (choix de Liam)
- **Contrat :** valide (`python B2B\harness\valider.py`)
- **Garde branchée :** sans objet : ne produit aucun texte, n'envoie rien (garde de chemins codée : seulement les dossiers listés de Videos)
- Bloque : kill-switch `B2B\STOP`, lien Stripe non autorisé, phrase interdite (OFFRE-REFERENCE.json), secret dans le texte.
- Avertit : machine non active, envoi_automatique = false (simulation), hors horaires du contrat (03:30-04:15), plafond de 0 messages par jour.
- **Tests :** `tests/agents/test_videos.py`, `B2B/agents/test_machine.py`
- **Alerte si silence :** après 04:15 (surveillant)

<!-- DYNAMIQUE:DEBUT -->
**Derniers résultats de test (cette machine) :**
- `tests/agents/test_videos.py` : pas encore lancé par `generer-fiches.py --tests`
- `B2B/agents/test_machine.py` : pas encore lancé par `generer-fiches.py --tests`

**Dernière trace :** aucune · **Dernière erreur :** aucune · **Dans agents_actifs (cette machine) :** non (Liam l'ajoute s'il veut le planifier)

### Historique (5 dernières traces, sans données client)
- aucune trace sur cette machine
<!-- DYNAMIQUE:FIN -->

## Skill et règles
- `.claude/skills/agent-videos-nettoyage/SKILL.md` (copie : `docs/agents/skills/agent-videos-nettoyage.md`)
- Règles : Videos/SKILL-VIDEOS.md (règles communes de l'équipe Vidéos, relues avant chaque exécution ; absentes ou incomplètes = refus, code 3)
- Pas de preuve = pas de fait : « il a tourné » = une trace du jour `ok: true` ci-dessus ; « c'est corrigé » = ses tests puis `tests\b2b-rapide.ps1` en vert.
<!-- GENERE:FIN -->

## Liens et décisions

_Zone conservée à chaque régénération : liens vers docs\decisions et docs clés seulement._

Liens : aucun pour l'instant.

## Notes de Liam

_Zone libre, conservée telle quelle à chaque régénération._
