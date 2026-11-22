---
name: agent-superviseur-videos
description: Fiche de rôle du Superviseur Vidéos (domaine Vidéos, rattaché à Jarvis CEO, FERMÉ jusqu'au « go superviseur-videos » de Liam) — toutes les 30 minutes sur le serveur, vérifie que les sept agents de la chaîne vidéo (veille, scripts, marketing, création, monteur, publication, nettoyage) ont tourné, dans l'ordre, et que leurs données ne se contredisent pas ; relance une fois un agent planté, retire un doublon identique du journal des vidéos et des sujets, et n'écrit JAMAIS dans l'état de publication ni dans une légende destinée au public (alerte Discord et attend « go »). À utiliser pour vérifier, corriger ou activer superviseur-videos.py (passage, --essai, etat).
---

# Superviseur Vidéos — la chaîne tourne dans l'ordre, et rien ne repart tout seul sur TikTok

**Responsable :** Jarvis (CEO). **Script :** `B2B/agents/superviseur-videos.py`. **Moteur commun :** `B2B/harness/superviseurs.py`.
**Contrat :** `B2B/harness/contrats/superviseur-videos.json`. **Tâche serveur :** `passage` toutes les 30 min (écrite, `desactive` tant que Liam n'a pas dit « go »).
**Agents suivis (7) :** videos-veille, videos-scripts, videos-marketing, videos-creation, videos-monteur, videos-publication, videos-nettoyage.

## Ordres pas à pas (lus dans le script)
1. `M.exiger("superviseur-videos", ...)` : refuse hors de la machine active (sauf `--essai`).
2. Pour chaque agent suivi : son état est lu dans ses **traces** du jour (`B2B/logs/agents/<agent>/`) et dans sa tâche (`serveur-taches.json`).
   Un agent absent de `agents_actifs`, désactivé, pas encore actif ou hors de ses jours n'est jamais signalé : il n'a pas de tâche sur cette machine.
   C'est le cas normal de `videos-publication` (verrouillé jusqu'au « go publier ») et de `videos-monteur` (appelé par la création, aucune tâche à lui).
   « erreur » = dernier passage du jour `ok: false` ; « silence » = heure fixe + délai de grâce passés sans passage ; « bloque » = agent cyclique muet depuis plus de 3 cycles + grâce.
3. Agent en erreur, silencieux ou bloqué : **relancé une fois**, avec la commande de sa tâche serveur, puis noté au journal. Au passage suivant, s'il est toujours en défaut : alerte, plus de relance (jamais deux par jour).
4. Contrôles de cohérence : `Videos/videos-publication-etat.json` (clés attendues, dates des jours de publication, plafond par jour et par ligne, deux fois la même vidéo au même passage),
   `Videos/publication.verrou` (verrou oublié depuis plus de 3 h), les légendes de `Videos/a-valider/*.txt` (mention « Contenu généré par IA. », phrases interdites, liens de paiement, secrets),
   `Videos/journal-videos.csv` (lignes en double), `Videos/scripts/sujets.json` (sujets en double), et **l'ordre de la chaîne du jour** (veille → scripts → marketing → création : un maillon qui a tourné sans le précédent).
5. **Corrige seul** (rien ne peut être perdu) : relance d'un agent, ligne **strictement identique** retirée de `journal-videos.csv`, sujet **strictement en double** retiré de `sujets.json` (la première occurrence et l'ordre restent).
6. **Ne touche jamais** : `videos-publication-etat.json` (compléter une clé ou retirer une ligne de publication pourrait faire **republier** une vidéo : c'est public et ça engage Liam),
   le verrou `publication.verrou` (le retirer autoriserait deux publications en même temps), le contenu d'une vidéo, d'une légende ou d'un script (texte destiné au public),
   un fichier illisible, un plafond dépassé, une date illogique, une chaîne dans le désordre. Dans tous ces cas : une alerte Discord et une ligne dans `B2B/a-valider/AAAA-MM-JJ-superviseur-videos.md`, puis il attend le « go ».
7. Discord : un résumé court par jour même quand tout va bien (à partir de `heure_resume`), plus un message dès qu'il corrige ou découvre quelque chose de neuf. Jamais la nuit (plage 07:00-22:00) : une alerte de 3 h attend le passage du matin. Même souci = annoncé une seule fois.

## Ce qu'il ne fait jamais
Publier ou dépublier ; réécrire une vidéo, une légende ou un script ; supprimer une donnée ; écraser une valeur déjà écrite ; toucher à l'argent ;
toucher au code, aux skills, aux docs ou à un fichier suivi par git ; écrire dans les données d'un autre domaine ; corriger avant ses deux « go » ;
contacter qui que ce soit d'autre que Liam ; utiliser une IA ou un service payant ; afficher un secret.

## Ouvrir l'agent (Liam seul)
Ce domaine a **deux** verrous, et les deux doivent être ouverts : le verrou commun `go_superviseurs` (variante locale de `B2B/agents/superviseurs-config.json`, déjà ouvert sur le serveur depuis le 21/11)
et son verrou **propre** `go_superviseur_videos`, qui reste `false` dans `B2B/agents/superviseur-videos-config.json` (versionné). Un superviseur ajouté après coup ne s'ouvre donc jamais tout seul.
Pour l'ouvrir, après avoir dit « go superviseur-videos » : mettre `go_superviseur_videos` à `true` dans `B2B/agents/superviseur-videos-config.local.json` (hors git), `envoi_automatique` à `true` quand il veut les messages Discord,
retirer la clé `desactive` de `superviseur-videos` dans `B2B/agents/serveur-taches.json`, puis ajouter `superviseur-videos` à `agents_actifs` de ses réglages locaux de machine.

## Vérifier (pas de preuve = pas de fait)
- `python B2B\agents\superviseur-videos.py passage --essai` : lit tout, affiche le résumé, n'écrit rien, n'envoie rien, ne relance rien.
- `python B2B\agents\superviseur-videos.py etat` : verrou, dernier passage, corrections du jour, ce qui attend un « go ».
- Tests : `python tests\agents\test_superviseurs.py` (agent planté relancé une seule fois, doublon du journal et des sujets retirés, état de publication jamais touché, verrou de publication jamais retiré, légende sans mention IA, chaîne dans le désordre, plafond dépassé, verrou propre fermé même quand le verrou commun est ouvert, `--essai`), puis `tests\b2b-rapide.ps1`.

## Limite connue
Il juge un agent sur ses traces : un agent qui tourne sans écrire de trace passerait pour silencieux. Les données vidéo (`Videos/a-valider`, `scripts`, `journal-videos.csv`)
vivent sur le **serveur** et sont hors git : sur le gros PC ces contrôles ne trouvent rien à regarder, ce qui est normal et n'est pas un défaut.
Il ne juge ni la qualité d'une vidéo, ni la justesse d'une accroche : seul Liam regarde ce qui part sur TikTok.
