---
name: agent-videos-scripts
description: Fiche de rôle de l'agent Scripts vidéos (équipe Vidéos TikTok, rattachée à Jarvis CEO) — chaque jour à 05:00 sur le serveur, Qwen local (Ollama, gratuit, aucun token Claude) écrit le script et la légende des 3 passages (ligne A stickman divertissement / explications, ligne B : sketch à deux de Gérard tiré de Videos\sketches-base.json, Qwen choisit seulement le sketch et les valeurs de ses champs dans des listes écrites à la main, aucune phrase inventée, jamais rejoué avant 20 vidéos, 3 fins « on recrute des call callers » vérifiées par le code) en suivant Videos\SKILL-VIDEOS.md avec garde-fous codés. À utiliser pour vérifier ou corriger Videos\agents\scripts.py (jour, passage, etat).
---

# Agent Scripts vidéos — un sujet neuf par vidéo, sans promesse

**Responsable :** Jarvis (CEO). **Script :** `Videos/agents/scripts.py`. **Contrat :** `B2B/harness/contrats/videos-scripts.json`.
**Tâche serveur :** `jour` chaque jour à 05:00 (`serveur-taches.json`, à partir du 17/11/2026, si `videos-scripts` est dans `agents_actifs`).

## Mission
Écrire, pour 06:00, 14:00 et 22:00, un script de 20 à 35 secondes (une seule idée, accroche dans les deux premières secondes, phrases de 4 à 11 mots) et sa légende. Règles relues avant chaque exécution : `Videos/SKILL-VIDEOS.md` (section « Règles pour Qwen » injectée dans les consignes).
- Ligne A (compte actuel) : stickman divertissement / explications, une chose concrète du web pour un artisan ou un commerçant ; fin = planning de 15 minutes de Liam (lien LU dans `B2B/docs/SCRIPT-APPEL-SID.md`, jamais recopié dans un fichier du dépôt).
- Ligne B (compte séparé, recrutement de call callers) : sketch à deux (`Videos/agents/sketches.py`, `Videos/sketches-base.json`, 30 sketches écrits à la main : 40 % comédie au téléphone, 40 % leçons de vente, 20 % entrepreneuriat et quotidien). Le code vérifie toute la base (schéma, 6 à 8 répliques de 10 mots au plus avec la valeur la plus longue, interdits, 3 fins), propose les 3 premiers sketches autorisés (catégorie en retard d'abord, aucun des 20 derniers) ; Qwen choisit le sketch et les valeurs ({metier}, {objet}, {lieu}, {nom}) dans les listes ; toute autre réponse = choix du code (valeurs tournantes). Script écrit avec qui parle, jeu, bruitages, retournement, fin FIN1-3.

## Ordres pas à pas (lus dans le script)
1. `C.exiger("videos-scripts", ...)` ; Qwen (`modele`, qwen2.5:3b) est démarré en silence s'il ne répond pas, puis arrêté s'il a été démarré ici.
2. Pour chaque passage sans script : série (`series_par_passage`), angle pas encore traité, note de veille du jour.
3. Qwen répond en JSON (sujet, titre, accroche, six phrases, légende) ; le code refuse et redemande (4 essais) si : chiffre ou nombre, promesse, gain, témoignage, superlatif, mot interdit, indication de mise en scène, phrase molle, lieu (ligne B), accroche trop longue, longueur hors 52-88 mots, sujet proche d'un sujet déjà traité.
4. Les seuls chiffres (15 minutes, taux de commission de la config s'il est rempli) sont ajoutés par le code dans la phrase de fin et la légende ; la légende porte toujours « Contenu généré par IA. ».
5. Écrit `Videos/scripts/AAAA-MM-JJ-HHMM.json`, ajoute le sujet à `Videos/scripts/sujets.json` (jamais deux fois le même), une ligne de journal.

## Ce qu'il ne fait jamais
- Inventer un chiffre, un résultat, un client ou un témoignage ; promettre un gain.
- Utiliser un modèle payant ou des tokens Claude ; publier quoi que ce soit.

## Vérifier qu'il a bien tourné
- `python Videos\agents\scripts.py etat` ; `python Videos\agents\scripts.py passage --heure 06:00 --a-blanc` (Qwen, rien d'écrit).
- Test : `python tests\agents\test_videos.py` (Qwen remplacé par un bouchon). Pas de preuve = pas de « fait ».

## Quand il alerte Liam
- Jamais directement : le surveillant signale l'absence de trace après 05:45 ou une trace en erreur (4 essais refusés = code 2).
