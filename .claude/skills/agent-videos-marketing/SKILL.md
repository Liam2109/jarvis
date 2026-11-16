---
name: agent-videos-marketing
description: Fiche de rôle de l'agent Marketing vidéos (équipe Vidéos TikTok, rattachée à Jarvis CEO) — chaque jour à 05:30 sur le serveur, entre Scripts et Création, Qwen local (gratuit, aucun token Claude) propose 3 accroches par script ; le code les note avec la grille de Videos\SKILL-VIDEOS.md, garde la meilleure (journal-videos.csv), resserre le rythme et prépare les sous-titres mot à mot. À utiliser pour vérifier ou corriger Videos\agents\marketing.py (jour, passage, etat).
---

# Agent Marketing vidéos — l'accroche, le rythme, les sous-titres

**Responsable :** Jarvis (CEO). **Script :** `Videos/agents/marketing.py`. **Contrat :** `B2B/harness/contrats/videos-marketing.json`.
**Tâche serveur :** `jour` chaque jour à 05:30 (`serveur-taches.json`, à partir du 17/11/2026, si `videos-marketing` est dans `agents_actifs`).
**Règles :** `Videos/SKILL-VIDEOS.md`, relu avant chaque exécution (sections « Grille des accroches », « Rétention », « Sous-titres »).

## Ordres pas à pas (lus dans le script)
1. `C.exiger` (machine active) puis `C.exiger_regles` (skill présent et complet, sinon refus code 3).
2. Pour chaque script du jour sans champ `marketing` : Qwen propose 3 accroches (8 mots au plus) en s'inspirant de `Videos/hooks.md` ; ligne B : la première phrase du brouillon de Liam concourt aussi.
3. `noter_accroche` : note sur 10 (forme qui accroche +3, courte +3, adresse directe +2, concrète +1, neuve +1, ouverture molle −3) ; éliminée (0) si chiffre, promesse, mot interdit, phrase molle ou lieu (ligne B). La meilleure remplace la première phrase ; égalité = la plus courte.
4. Rythme : phrase de plus de 11 mots coupée en deux (une image toutes les 2 à 4 s) ; durée estimée (2,6 mots/s + carte de fin) comparée à 20-35 s.
5. Sous-titres : groupes de 2 à 4 mots, mot clé (le plus long mot plein) en couleur d'accent ; utilisés par l'agent Création.
6. Une ligne dans `Videos/journal-videos.csv` (accroche gardée, sa note et celle des autres) et une dans le journal de l'agent.

## Ce qu'il ne fait jamais
- Garder une accroche avec un chiffre, une promesse, un revenu, un témoignage ou un lieu (ligne B).
- Utiliser un modèle payant ou des tokens Claude ; publier quoi que ce soit.

## Vérifier qu'il a bien tourné
- `python Videos\agents\marketing.py etat` ; `python Videos\agents\marketing.py passage --heure 06:00 --a-blanc` (Qwen, rien d'écrit).
- Test : `python tests\agents\test_videos.py` (Qwen remplacé par un bouchon). Pas de preuve = pas de « fait ».

## Quand il alerte Liam
- Jamais directement : le surveillant signale l'absence de trace après 06:15 ou une trace en erreur (aucune accroche valable = code 2 ; le script est alors utilisé tel quel par Création).
