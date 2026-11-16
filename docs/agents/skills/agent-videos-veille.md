---
name: agent-videos-veille
description: Fiche de rôle de l'agent Veille vidéos (équipe Vidéos TikTok, rattachée à Jarvis CEO) — chaque jour à 04:30 sur le serveur, recherche web gratuite (flux RSS Google Actualités, jamais TikTok) des formats stickman / motion design qui marchent en français, note courte dans Videos\veille gardée 14 jours. À utiliser pour vérifier ou corriger Videos\agents\veille.py (jour, etat).
---

# Agent Veille vidéos — ce qui marche en vidéo courte, sans toucher à TikTok

**Responsable :** Jarvis (CEO). **Script :** `Videos/agents/veille.py`. **Contrat :** `B2B/harness/contrats/videos-veille.json`.
**Tâche serveur :** `jour` chaque jour à 04:30 (`serveur-taches.json`, à partir du 17/11/2026, si `videos-veille` est dans `agents_actifs`).

## Mission
Donner chaque matin à l'agent Scripts quelques titres récents sur les formats de vidéos courtes animées en français, gratuitement et sans scraping de TikTok.

## Ordres pas à pas (lus dans le script)
1. `C.exiger("videos-veille", ...)` : machine active obligatoire (sauf `--a-blanc`).
2. Pour chaque requête de `veille_requetes` (`Videos/videos-config.json`) : flux RSS public de Google Actualités en français (sans clé ni compte).
3. Seuls titre, source et date sont gardés (2 par requête, 8 au plus) ; aucune page n'est ouverte ; tout résultat de tiktok.com est écarté.
4. Écrit `Videos/veille/AAAA-MM-JJ.md` (note courte), efface les notes de plus de 14 jours (`veille_jours_gardes`).
5. Une ligne dans `Videos/videos-veille-journal.log` ; toutes les requêtes en échec = aucune note, code 2.

## Ce qu'il ne fait jamais
- Ouvrir ou lire une page de TikTok, contourner un contrôle anti-robot (DuckDuckGo et Bing ont été écartés le 16/11/2026 pour cette raison).
- Publier, envoyer un message ou toucher à `memoire/`, `.env`, `config.json` ou un fichier local de configuration.

## Vérifier qu'il a bien tourné
- `python Videos\agents\veille.py etat` ; `python Videos\agents\veille.py jour --a-blanc` (affiche la note sans l'écrire).
- Test : `python tests\agents\test_videos.py` (flux fictif, aucun réseau). Pas de preuve = pas de « fait ».

## Quand il alerte Liam
- Jamais directement : le surveillant signale l'absence de trace après 05:00 ou une trace en erreur.
