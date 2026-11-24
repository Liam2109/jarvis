---
agent: videos-publication
aliases: [📤 Publication TikTok]
name: videos-publication
role: "DÉSACTIVÉ jusqu'au « go publier » de Liam : publie les vidéos de Videos/a-valider sur TikTok via la session déjà ouverte par Liam, étiquette IA activée, 3 par jour au plus."
machine: "serveur"
planification: "chaque jour à 06:20, plage tous les jours 05:15-22:45"
sorties: "Videos/publiees, Videos/videos-publication-etat.json, Videos/videos-publication-journal.log"
responsable: Jarvis (CEO)
statut: arrêté
horaire: "chaque jour à 06:20, 14:20, 22:20, plage tous les jours 05:15-22:45"
tags: [agent-b2b]
---
<!-- GENERE:DEBUT (régénéré par python B2B\harness\generer-fiches.py : ne pas modifier) -->
# 📤 Publication TikTok

**Agent :** `videos-publication` · **Statut :** arrêté · **Responsable :** Jarvis (CEO) · **Machine :** serveur
**Horaire :** chaque jour à 06:20, 14:20, 22:20, plage tous les jours 05:15-22:45
**Script :** `Videos/agents/publication.py` · **Contrat :** `B2B/harness/contrats/videos-publication.json`

## Rôle et limites
### Mission
Fermé par ligne jusqu'au « go publier » de Liam ; ensuite publie les vidéos de la ligne sur son compte TikTok (Playwright, profil persistant), étiquette IA, 3 par jour et par compte ; anomalie = arrêt.

### Ce qu'il fait étape par étape
1. Refus avant toute ouverture : `Videos\STOP` ou `B2B\STOP`, ligne arrêtée aujourd'hui, `go_publier` pas à true, aucun essai réussi, 3 publications déjà faites sur le compte, hors des heures prévues (+/- 45 min), passage déjà publié.
2. Prend la plus ancienne vidéo complète de la ligne (mp4 + txt avec « Contenu généré par IA. » + json `contenu_ia: true`) ; la légende passe par la garde du harness.
3. Verrou : jamais deux publications en même temps. Ouvre le profil persistant de la ligne, va sur la page de dépôt de TikTok Studio, délais aléatoires entre les gestes.
4. Après chaque geste : page contrôlée ; captcha, connexion ou vérification demandée, interface inattendue, échec = ARRÊT de la ligne pour la journée, alerte Discord, ligne CSV.
5. Dépose la vidéo, colle la légende, coche la case TikTok « contenu généré par IA » et la VÉRIFIE cochée juste avant de cliquer sur Publier (règle du 17/11/2026 : plus de texte IA à l'image) ; essai (dry-run) : s'arrête devant Publier et dit où se trouve la case (section, position à l'écran) ; sinon clique sur Publier et lit la confirmation.
6. Déplace la vidéo vers `Videos\publiees`, une ligne dans `journal-videos.csv` (date, compte, hook, résultat), dans le journal et dans Discord.

### Ce qu'il n'a pas le droit de faire
- taper un mot de passe, demander un code ou une clé, en stocker un
- continuer ou contourner après un captcha, une demande de connexion ou de vérification, une interface inattendue ou un échec (arrêt + alerte, rien d'autre ce jour-là sur la ligne)
- liker, s'abonner, commenter ou envoyer un message
- publier sans l'étiquette « contenu généré par IA » cochée et vérifiée juste avant de valider (échec = rien publié, alerte Discord, vidéo mise à part)
- publier plus de 3 vidéos par jour et par compte, hors des heures prévues, ou deux à la fois
- publier sur une ligne sans son « go publier » ni sans essai réussi
- publier si Videos/STOP ou B2B/STOP existe
- toucher à memoire/, .env, config.json, .obsidian/ ou écrire un fichier *.local.json
- afficher un secret (jeton, clé, adresse iCal)
- envoyer au client, encaisser ou signer
- Engager Liam (envoyer au client, encaisser, publier, signer) : `peut_engager: false`, tout passe par `B2B/a-valider/`.

## Entrées et sorties
**Chaîne vidéo :** Veille → Scripts → Marketing → Création → Monteur (ligne B) → Ton OK de Liam (« go publier », une fois par ligne) → **Publication (verrouillée)** → Nettoyage (fiche « ⛓️ Chaîne vidéo »)
- **Reçoit de :** Ton OK de Liam (« go publier », une fois par ligne) : ligne ouverte : go_publier = true dans la config locale
- **Produit :** vidéo publiée, déplacée dans Videos/publiees
- **Passe à :** Nettoyage

**Lit :**
- Videos/a-valider
- Videos/SKILL-VIDEOS.md
- Videos/videos-config.json
- Videos/videos-config.local.json (lignes.A / lignes.B : go_publier, écrit par Liam seulement)
- profil du navigateur de chaque ligne (%LOCALAPPDATA%/JarvisTikTok/ligne-A, ligne-B), session ouverte par Liam

**Écrit :**
- Videos/publiees
- Videos/videos-publication-etat.json
- Videos/videos-publication-journal.log
- Videos/journal-videos.csv
- Videos/publication.verrou

**Discord :** salon des agents (une ligne par publication ou essai, alerte d'arrêt) · **Plafond :** 7 messages par jour · **Envoi au client :** non

## Horaire et état
- **Horaire :** chaque jour à 06:20, 14:20, 22:20, plage tous les jours 05:15-22:45
- **Tâche serveur :** entrée dans `B2B/agents/serveur-taches.json` ; tourne seulement si l'agent est dans `agents_actifs` (choix de Liam)
- **Contrat :** valide (`python B2B\harness\valider.py`)
- **Garde branchée :** oui
- Bloque : kill-switch `B2B\STOP`, lien Stripe non autorisé, phrase interdite (OFFRE-REFERENCE.json), secret dans le texte.
- Avertit : machine non active, envoi_automatique = false (simulation), hors horaires du contrat (05:15-22:45), plafond de 7 messages par jour.
- **Tests :** `tests/agents/test_videos.py`
- **Alerte si silence :** aucune

<!-- DYNAMIQUE:DEBUT -->
**Derniers résultats de test (cette machine) :**
- `tests/agents/test_videos.py` : pas encore lancé par `generer-fiches.py --tests`

**Dernière trace :** aucune · **Dernière erreur :** aucune · **Dans agents_actifs (cette machine) :** non (Liam l'ajoute s'il veut le planifier)

### Historique (5 dernières traces, sans données client)
- aucune trace sur cette machine
<!-- DYNAMIQUE:FIN -->

## Skill et règles
- `.claude/skills/agent-videos-publication/SKILL.md` (copie : `docs/agents/skills/agent-videos-publication.md`)
- Règles : Videos/SKILL-VIDEOS.md (règles communes de l'équipe Vidéos, relues avant chaque exécution ; absentes ou incomplètes = refus, code 3)
- Pas de preuve = pas de fait : « il a tourné » = une trace du jour `ok: true` ci-dessus ; « c'est corrigé » = ses tests puis `tests\b2b-rapide.ps1` en vert.
<!-- GENERE:FIN -->

## Liens et décisions

_Zone conservée à chaque régénération : liens vers docs\decisions et docs clés seulement._

Liens : aucun pour l'instant.

## Notes de Liam

_Zone libre, conservée telle quelle à chaque régénération._
