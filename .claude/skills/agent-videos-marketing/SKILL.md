---
name: agent-videos-marketing
description: Fiche de rôle de l'agent Marketing vidéos (équipe Vidéos TikTok, rattachée à Jarvis CEO) — chaque jour à 05:30 sur le serveur, entre Scripts et Création, Qwen local (gratuit, aucun token Claude) choisit 3 formules d'accroche à trous écrites à la main (Videos\hooks.md) et remplit seulement leurs trous ; le code les note avec la grille de Videos\SKILL-VIDEOS.md, garde la meilleure (journal-videos.csv), resserre le rythme et prépare les sous-titres mot à mot. À utiliser pour vérifier ou corriger Videos\agents\marketing.py (jour, passage, etat).
---

# Agent Marketing vidéos — l'accroche, le rythme, les sous-titres

**Responsable :** Jarvis (CEO). **Script :** `Videos/agents/marketing.py`. **Contrat :** `B2B/harness/contrats/videos-marketing.json`.
**Tâche serveur :** `jour` chaque jour à 05:30 (`serveur-taches.json`, à partir du 17/11/2026, si `videos-marketing` est dans `agents_actifs`).
**Règles :** `Videos/SKILL-VIDEOS.md`, relu avant chaque exécution (sections « Grille des accroches », « Rétention », « Sous-titres »).

## Rôle
Choisir la meilleure accroche de chaque script (3 formules à trous notées par la grille), resserrer le rythme et préparer les sous-titres. Limites : Qwen remplit seulement les trous de formules écrites à la main ; aucune phrase inventée ; ne fabrique ni ne publie de vidéo.

## Ordres pas à pas (lus dans le script)
1. `C.exiger` (machine active) puis `C.exiger_regles` (skill présent et complet, sinon refus code 3).
2. Pour chaque script du jour sans champ `marketing` : Qwen choisit 3 formules de la ligne dans `Videos/hooks.md` (`- A01 | …`, `- B01 | …`) et remplit leurs trous (1 à 4 mots) ; il n'invente aucune phrase. Formule inconnue ou trou invalide = rejeté, complété par des formules sans trou (jamais inventées). Ligne B : la première phrase du brouillon de Liam concourt aussi (si elle est différente).
3. `noter_accroche` : note sur 10 (forme qui accroche +3, courte +3, adresse directe +2, concrète +1, neuve +1, ouverture molle −3) ; éliminée (0) si chiffre, promesse, mot interdit, phrase molle, mauvais public (A : vouvoyer l'artisan, jamais son client ; B : tutoyer le futur call caller), adresse épelée ou lieu (ligne B). L'accroche écran = l'accroche gardée (7 mots au plus). La meilleure remplace la première phrase ; égalité = la plus courte.
4. Rythme : phrase de plus de 11 mots coupée en deux (une image toutes les 2 à 4 s) ; durée estimée (2,6 mots/s + carte de fin) comparée à 20-35 s.
5. Sous-titres : groupes de 2 à 4 mots, mot clé (le plus long mot plein) en couleur d'accent ; utilisés par l'agent Création.
6. Une ligne dans `Videos/journal-videos.csv` (accroche gardée, sa note et celle des autres) et une dans le journal de l'agent.

## Entrées et sorties (place dans la chaîne)
- **Reçoit de :** **Scripts** (`Videos/scripts/AAAA-MM-JJ-HHMM.json` sans champ `marketing`) ; **Veille** (`Videos/hooks.md`).
- **Produit :** le même fichier de script enrichi du champ `marketing` (accroche gardée, notes, durée estimée, sous-titres) ; une ligne dans `Videos/journal-videos.csv`.
- **Passe à :** **Création** (06:00, 14:00, 22:00) rend la vidéo à partir du script enrichi.
- Chaîne vidéo : Veille → Scripts → Marketing → Création (→ Monteur, ligne B) → ton OK de Liam (« go publier », une fois par ligne) → Publication → Nettoyage. Fiche : `docs/agents/⛓️ Chaîne vidéo.md`.

## Ce qu'il ne fait jamais
- Garder une accroche avec un chiffre, une promesse, un revenu, un témoignage ou un lieu (ligne B).
- Utiliser un modèle payant ou des tokens Claude ; publier quoi que ce soit.

## Cas d'erreur
- Aucune accroche valable : code 2, trace `ok: false` ; le script est laissé tel quel et Création l'utilise.
- Qwen muet ou réponse hors liste : formules sans trou (jamais inventées).
- Script retravaillé bloqué par la garde du harness : il n'est pas réécrit, trace `ok: false` « garde contenu ».
- Machine non active ou `SKILL-VIDEOS.md` incomplet : refus code 3.
- Toute erreur laisse une trace `ok: false`, lue par le surveillant si l'agent est dans `agents_actifs`.

## Règles qu'il suit
- Il relit `Videos/SKILL-VIDEOS.md` avant chaque exécution (`C.exiger_regles` : absent ou incomplet = refus, code 3), sections « Grille des accroches », « Rétention », « Sous-titres ».
- Harness : contrat `B2B/harness/contrats/videos-marketing.json` (`peut_engager: false`) ; garde du contenu `C.garde_harness` avant écriture (secret, phrase interdite d'`OFFRE-REFERENCE.json`, lien Stripe non autorisé ; `B2B\STOP` bloque la publication, pas la fabrication) ; une trace par exécution (`C.lancer` : commande, durée, ok, erreur ; rien pour `etat` ni `--a-blanc`) dans `B2B/logs/agents/videos-marketing/AAAA-MM-JJ.jsonl`.
- Ce qui engage Liam (publier, envoyer, encaisser, signer) n'est jamais fait sans son accord ; la publication reste verrouillée par ligne jusqu'à son « go publier ».
- Règle d'or : pas de preuve = pas de fait. « Il a tourné » se prouve par la trace du jour (`ok: true`) et le fichier produit ; « c'est corrigé » par `python tests\agents\test_videos.py` puis `tests\b2b-rapide.ps1` en vert, sortie montrée.

## Vérifier qu'il a bien tourné
- `python Videos\agents\marketing.py etat` ; `python Videos\agents\marketing.py passage --heure 06:00 --a-blanc` (Qwen, rien d'écrit).
- Test : `python tests\agents\test_videos.py` (Qwen remplacé par un bouchon). Pas de preuve = pas de « fait ».

## Quand il alerte Liam
- Jamais directement : le surveillant signale l'absence de trace après 06:15 ou une trace en erreur (aucune accroche valable = code 2 ; le script est alors utilisé tel quel par Création).
