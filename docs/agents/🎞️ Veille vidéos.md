---
agent: videos-veille
aliases: [🎞️ Veille vidéos]
name: videos-veille
role: "Une fois par jour, recherche web gratuite (Google Actualités RSS, sans TikTok) des formats stickman / motion design en français ; note courte dans Videos/veille, gardée 14 jours."
machine: "serveur"
planification: "chaque jour à 04:30, plage tous les jours 04:30-05:00"
sorties: "Videos/veille/AAAA-MM-JJ.md, Videos/videos-veille-journal.log"
responsable: Jarvis (CEO)
statut: actif
mode: réel
horaire: "chaque jour à 04:30, plage tous les jours 04:30-05:00"
tags: [agent-b2b]
---
<!-- GENERE:DEBUT (régénéré par python B2B\harness\generer-fiches.py : ne pas modifier) -->
# 🎞️ Veille vidéos

**Agent :** `videos-veille` · **Statut :** actif · **Responsable :** Jarvis (CEO) · **Machine :** serveur
**Horaire :** chaque jour à 04:30, plage tous les jours 04:30-05:00
**Script :** `Videos/agents/veille.py` · **Contrat :** `B2B/harness/contrats/videos-veille.json`

## Rôle et limites
### Mission
Une fois par jour, recherche web gratuite (Google Actualités RSS, sans TikTok) des formats stickman / motion design en français ; note courte dans Videos/veille, gardée 14 jours.

### Ce qu'il fait étape par étape
1. `C.exiger("videos-veille", ...)` : machine active obligatoire (sauf `--a-blanc`).
2. Pour chaque requête de `veille_requetes` (`Videos/videos-config.json`) : flux RSS public de Google Actualités en français (sans clé ni compte).
3. Seuls titre, source et date sont gardés (2 par requête, 8 au plus) ; aucune page n'est ouverte ; tout résultat de tiktok.com est écarté.
4. Écrit `Videos/veille/AAAA-MM-JJ.md` (note courte), efface les notes de plus de 14 jours (`veille_jours_gardes`).
5. Une ligne dans `Videos/videos-veille-journal.log` ; toutes les requêtes en échec = aucune note, code 2.

### Ce qu'il n'a pas le droit de faire
- ouvrir ou lire une page de tiktok.com (aucun scraping de TikTok)
- contourner un contrôle anti-robot d'un moteur de recherche
- garder une note de plus de 14 jours
- publier, liker, s'abonner, commenter ou envoyer un message sur TikTok
- toucher à memoire/, .env, config.json, .obsidian/ ou un fichier *.local.json
- afficher un secret (jeton, clé, adresse iCal)
- envoyer au client, encaisser ou signer
- Engager Liam (envoyer au client, encaisser, publier, signer) : `peut_engager: false`, tout passe par `B2B/a-valider/`.

## Entrées et sorties
**Chaîne vidéo :** **Veille** → Scripts → Marketing → Création → Monteur (ligne B) → Ton OK de Liam (« go publier », une fois par ligne) → Publication (verrouillée) → Nettoyage (fiche « ⛓️ Chaîne vidéo »)
- **Reçoit de :** aucun (premier maillon)
- **Produit :** note du jour (Videos/veille) + formules d'accroche (hooks.md)
- **Passe à :** Scripts

**Lit :**
- Videos/videos-config.json
- flux RSS Google Actualités (lecture)

**Écrit :**
- Videos/veille/AAAA-MM-JJ.md
- Videos/videos-veille-journal.log

**Discord :** aucun · **Plafond :** 0 messages par jour · **Envoi au client :** non

## Horaire et état
- **Horaire :** chaque jour à 04:30, plage tous les jours 04:30-05:00
- **Tâche serveur :** entrée dans `B2B/agents/serveur-taches.json`, active à partir du 2026-11-17 ; tourne seulement si l'agent est dans `agents_actifs` (choix de Liam)
- **Contrat :** valide (`python B2B\harness\valider.py`)
- **Garde branchée :** non
- Bloque : kill-switch `B2B\STOP`, lien Stripe non autorisé, phrase interdite (OFFRE-REFERENCE.json), secret dans le texte.
- Avertit : machine non active, envoi_automatique = false (simulation), hors horaires du contrat (04:30-05:00), plafond de 0 messages par jour.
- **Tests :** `tests/agents/test_videos.py`
- **Alerte si silence :** après 05:00 (surveillant)

<!-- DYNAMIQUE:DEBUT -->
**Derniers résultats de test (cette machine) :**
- `tests/agents/test_videos.py` : pas encore lancé par `generer-fiches.py --tests`

**Dernière trace :** aucune · **Dernière erreur :** aucune · **Dans agents_actifs (cette machine) :** non (Liam l'ajoute s'il veut le planifier)

### Historique (5 dernières traces, sans données client)
- aucune trace sur cette machine
<!-- DYNAMIQUE:FIN -->

## Skill et règles
- `.claude/skills/agent-videos-veille/SKILL.md` (copie : `docs/agents/skills/agent-videos-veille.md`)
- Règles : Videos/SKILL-VIDEOS.md (règles communes de l'équipe Vidéos, relues avant chaque exécution ; absentes ou incomplètes = refus, code 3)
- Pas de preuve = pas de fait : « il a tourné » = une trace du jour `ok: true` ci-dessus ; « c'est corrigé » = ses tests puis `tests\b2b-rapide.ps1` en vert.
<!-- GENERE:FIN -->

## Liens et décisions

_Zone conservée à chaque régénération : liens vers docs\decisions et docs clés seulement._

Liens : aucun pour l'instant.

## Notes de Liam

_Zone libre, conservée telle quelle à chaque régénération._
