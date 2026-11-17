---
agent: videos-scripts
aliases: [✍️ Scripts vidéos]
name: videos-scripts
role: "Chaque jour, Qwen local (Ollama, gratuit) écrit les scripts et légendes des 3 passages (séries A et B) ; garde-fous codés : aucun chiffre inventé, aucune promesse, aucun témoignage, jamais le même sujet."
machine: "serveur"
planification: "chaque jour à 05:00, plage tous les jours 05:00-05:45"
sorties: "Videos/scripts/AAAA-MM-JJ-HHMM.json, Videos/scripts/sujets.json, Videos/videos-scripts-journal.log"
responsable: Jarvis (CEO)
statut: actif
mode: réel
horaire: "chaque jour à 05:00, plage tous les jours 05:00-05:45"
tags: [agent-b2b]
---
<!-- GENERE:DEBUT (régénéré par python B2B\harness\generer-fiches.py : ne pas modifier) -->
# ✍️ Scripts vidéos

**Agent :** `videos-scripts` · **Statut :** actif · **Responsable :** Jarvis (CEO) · **Machine :** serveur
**Horaire :** chaque jour à 05:00, plage tous les jours 05:00-05:45
**Script :** `Videos/agents/scripts.py` · **Contrat :** `B2B/harness/contrats/videos-scripts.json`

## Rôle et limites
### Mission
Chaque jour, Qwen local (Ollama, gratuit) écrit les scripts et légendes des 3 passages (lignes A et B) ; garde-fous codés : aucun chiffre inventé, aucune promesse, aucun témoignage, jamais le même sujet.

### Ce qu'il fait étape par étape
1. `C.exiger("videos-scripts", ...)` ; Qwen (`modele`, qwen2.5:3b) est démarré en silence s'il ne répond pas, puis arrêté s'il a été démarré ici.
2. Pour chaque passage sans script : série (`series_par_passage`), angle pas encore traité, note de veille du jour.
3. Qwen répond en JSON (sujet, titre, accroche, six phrases, légende) ; le code refuse et redemande (4 essais) si : chiffre ou nombre, promesse, gain, témoignage, superlatif, mot interdit, indication de mise en scène, phrase molle, lieu (ligne B), accroche trop longue, longueur hors 52-88 mots, sujet proche d'un sujet déjà traité.
4. Les seuls chiffres (15 minutes, taux de commission de la config s'il est rempli) sont ajoutés par le code dans la phrase de fin et la légende ; la légende porte toujours « Contenu généré par IA. ».
5. Écrit `Videos/scripts/AAAA-MM-JJ-HHMM.json`, ajoute le sujet à `Videos/scripts/sujets.json` (jamais deux fois le même), une ligne de journal.

### Ce qu'il n'a pas le droit de faire
- écrire un chiffre, un gain, une promesse de résultat ou un témoignage inventé
- reprendre un sujet déjà traité
- recopier le lien du planning dans un fichier du dépôt
- utiliser un modèle payant ou des tokens Claude
- publier, liker, s'abonner, commenter ou envoyer un message sur TikTok
- toucher à memoire/, .env, config.json, .obsidian/ ou un fichier *.local.json
- afficher un secret (jeton, clé, adresse iCal)
- envoyer au client, encaisser ou signer
- Engager Liam (envoyer au client, encaisser, publier, signer) : `peut_engager: false`, tout passe par `B2B/a-valider/`.

## Entrées et sorties
**Chaîne vidéo :** Veille → **Scripts** → Marketing → Création → Monteur (ligne B) → Ton OK de Liam (« go publier », une fois par ligne) → Publication (verrouillée) → Nettoyage (fiche « ⛓️ Chaîne vidéo »)
- **Reçoit de :** Veille : note du jour (Videos/veille) + formules d'accroche (hooks.md)
- **Produit :** script + légende (Videos/scripts/AAAA-MM-JJ-HHMM.json)
- **Passe à :** Marketing

**Lit :**
- Videos/veille
- Videos/videos-config.json
- B2B/docs/SCRIPT-APPEL-SID.md (lien du planning, lu seulement)
- Videos/scripts/sujets.json

**Écrit :**
- Videos/scripts/AAAA-MM-JJ-HHMM.json
- Videos/scripts/sujets.json
- Videos/videos-scripts-journal.log

**Discord :** aucun · **Plafond :** 0 messages par jour · **Envoi au client :** non

## Horaire et état
- **Horaire :** chaque jour à 05:00, plage tous les jours 05:00-05:45
- **Tâche serveur :** entrée dans `B2B/agents/serveur-taches.json`, active à partir du 2026-11-17 ; tourne seulement si l'agent est dans `agents_actifs` (choix de Liam)
- **Contrat :** valide (`python B2B\harness\valider.py`)
- **Garde branchée :** non
- Bloque : kill-switch `B2B\STOP`, lien Stripe non autorisé, phrase interdite (OFFRE-REFERENCE.json), secret dans le texte.
- Avertit : machine non active, envoi_automatique = false (simulation), hors horaires du contrat (05:00-05:45), plafond de 0 messages par jour.
- **Tests :** `tests/agents/test_videos.py`
- **Alerte si silence :** après 05:45 (surveillant)

<!-- DYNAMIQUE:DEBUT -->
**Derniers résultats de test (cette machine) :**
- `tests/agents/test_videos.py` : pas encore lancé par `generer-fiches.py --tests`

**Dernière trace :** aucune · **Dernière erreur :** aucune · **Dans agents_actifs (cette machine) :** non (Liam l'ajoute s'il veut le planifier)

### Historique (5 dernières traces, sans données client)
- aucune trace sur cette machine
<!-- DYNAMIQUE:FIN -->

## Skill et règles
- `.claude/skills/agent-videos-scripts/SKILL.md` (copie : `docs/agents/skills/agent-videos-scripts.md`)
- Règles : Videos/SKILL-VIDEOS.md (règles communes de l'équipe Vidéos, relues avant chaque exécution ; absentes ou incomplètes = refus, code 3)
- Pas de preuve = pas de fait : « il a tourné » = une trace du jour `ok: true` ci-dessus ; « c'est corrigé » = ses tests puis `tests\b2b-rapide.ps1` en vert.
<!-- GENERE:FIN -->

## Liens et décisions

_Zone conservée à chaque régénération : liens vers docs\decisions et docs clés seulement._

Liens : aucun pour l'instant.

## Notes de Liam

_Zone libre, conservée telle quelle à chaque régénération._
