---
name: agent-videos-veille
description: Fiche de rôle de l'agent Veille vidéos (équipe Vidéos TikTok, rattachée à Jarvis CEO) — chaque jour à 04:30 sur le serveur, recherche web gratuite (flux RSS Google Actualités, jamais TikTok) des formats stickman / motion design qui marchent en français, note courte dans Videos\veille gardée 14 jours. À utiliser pour vérifier ou corriger Videos\agents\veille.py (jour, etat).
---

# Agent Veille vidéos — ce qui marche en vidéo courte, sans toucher à TikTok

**Responsable :** Jarvis (CEO). **Script :** `Videos/agents/veille.py`. **Contrat :** `B2B/harness/contrats/videos-veille.json`.
**Tâche serveur :** `jour` chaque jour à 04:30 (`serveur-taches.json`, à partir du 17/11/2026, si `videos-veille` est dans `agents_actifs`).

## Rôle
Donner chaque matin à l'agent Scripts quelques titres récents sur les formats de vidéos courtes animées en français, gratuitement et sans scraping de TikTok. Limites : lecture de flux RSS publics seulement, aucune page ouverte, rien publié, aucun token Claude.
Donner chaque matin à l'agent Scripts quelques titres récents sur les formats de vidéos courtes animées en français, gratuitement et sans scraping de TikTok.

## Ordres pas à pas (lus dans le script)
1. `C.exiger("videos-veille", ...)` : machine active obligatoire (sauf `--a-blanc`).
2. Pour chaque requête de `veille_requetes` (`Videos/videos-config.json`) : flux RSS public de Google Actualités en français (sans clé ni compte).
3. Seuls titre, source et date sont gardés (2 par requête, 8 au plus) ; aucune page n'est ouverte ; tout résultat de tiktok.com est écarté.
4. Écrit `Videos/veille/AAAA-MM-JJ.md` (note courte), efface les notes de plus de 14 jours (`veille_jours_gardes`).
5. Une ligne dans `Videos/videos-veille-journal.log` ; toutes les requêtes en échec = aucune note, code 2.

## Entrées et sorties (place dans la chaîne)
- **Reçoit de :** aucun (premier maillon) ; lit `veille_requetes` dans `Videos/videos-config.json` et les flux RSS de Google Actualités.
- **Produit :** `Videos/veille/AAAA-MM-JJ.md` (titres, sources, dates) et le bloc de formules repérées dans `Videos/hooks.md`.
- **Passe à :** **Scripts** (05:00) lit la note du jour ; **Marketing** (05:30) lit `hooks.md`.
- Chaîne vidéo : Veille → Scripts → Marketing → Création (→ Monteur, ligne B) → ton OK de Liam (« go publier », une fois par ligne) → Publication → Nettoyage. Fiche : `docs/agents/⛓️ Chaîne vidéo.md`.

## Ce qu'il ne fait jamais
- Ouvrir ou lire une page de TikTok, contourner un contrôle anti-robot (DuckDuckGo et Bing ont été écartés le 16/11/2026 pour cette raison).
- Publier, envoyer un message ou toucher à `memoire/`, `.env`, `config.json` ou un fichier local de configuration.

## Cas d'erreur
- Toutes les requêtes en échec (pas d'internet) : aucune note, code 2, trace `ok: false` ; Scripts tourne quand même sans note.
- Résultat venant de tiktok.com : écarté avant écriture.
- Titre bloqué par la garde (secret, phrase interdite) : écarté, trace `ok: false` « garde contenu ».
- Machine non active : refus code 3 ; `SKILL-VIDEOS.md` absent ou incomplet : refus code 3.
- Toute erreur laisse une trace `ok: false`, lue par le surveillant si l'agent est dans `agents_actifs`.

## Règles qu'il suit
- Il relit `Videos/SKILL-VIDEOS.md` avant chaque exécution (`C.exiger_regles` : absent ou incomplet = refus, code 3), sections « Équipe », « Gratuit, local, sans token Claude ».
- Harness : contrat `B2B/harness/contrats/videos-veille.json` (`peut_engager: false`) ; garde du contenu `C.garde_harness` avant écriture (secret, phrase interdite d'`OFFRE-REFERENCE.json`, lien Stripe non autorisé ; `B2B\STOP` bloque la publication, pas la fabrication) ; une trace par exécution (`C.lancer` : commande, durée, ok, erreur ; rien pour `etat` ni `--a-blanc`) dans `B2B/logs/agents/videos-veille/AAAA-MM-JJ.jsonl`.
- Ce qui engage Liam (publier, envoyer, encaisser, signer) n'est jamais fait sans son accord ; la publication reste verrouillée par ligne jusqu'à son « go publier ».
- Règle d'or : pas de preuve = pas de fait. « Il a tourné » se prouve par la trace du jour (`ok: true`) et le fichier produit ; « c'est corrigé » par `python tests\agents\test_videos.py` puis `tests\b2b-rapide.ps1` en vert, sortie montrée.

## Vérifier qu'il a bien tourné
- `python Videos\agents\veille.py etat` ; `python Videos\agents\veille.py jour --a-blanc` (affiche la note sans l'écrire).
- Test : `python tests\agents\test_videos.py` (flux fictif, aucun réseau). Pas de preuve = pas de « fait ».

## Quand il alerte Liam
- Jamais directement : le surveillant signale l'absence de trace après 05:00 ou une trace en erreur.
