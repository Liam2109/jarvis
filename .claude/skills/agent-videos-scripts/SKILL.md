---
name: agent-videos-scripts
description: Fiche de rôle de l'agent Scripts vidéos (équipe Vidéos TikTok, rattachée à Jarvis CEO) — chaque jour à 05:00 sur le serveur, Qwen local (Ollama, gratuit, aucun token Claude) écrit le script et la légende des 3 passages (ligne A stickman divertissement / explications, ligne B : sketch à deux de Gérard tiré de Videos\sketches-base.json, Qwen choisit seulement le sketch et les valeurs de ses champs dans des listes écrites à la main, aucune phrase inventée, jamais rejoué avant 20 vidéos, 3 fins « on recrute des call callers » vérifiées par le code) en suivant Videos\SKILL-VIDEOS.md avec garde-fous codés. À utiliser pour vérifier ou corriger Videos\agents\scripts.py (jour, passage, etat).
---

# Agent Scripts vidéos — un sujet neuf par vidéo, sans promesse

**Responsable :** Jarvis (CEO). **Script :** `Videos/agents/scripts.py`. **Contrat :** `B2B/harness/contrats/videos-scripts.json`.
**Tâche serveur :** `jour` chaque jour à 05:00 (`serveur-taches.json`, à partir du 17/11/2026, si `videos-scripts` est dans `agents_actifs`).

## Rôle
Écrire le script et la légende des 3 passages du jour (06:00, 14:00, 22:00) avec Qwen local, dans les limites des garde-fous codés. Limites : n'invente aucun chiffre, résultat, client ni témoignage ; ligne B : Qwen choisit seulement dans des listes écrites à la main ; ne fabrique ni ne publie de vidéo.
Écrire, pour 06:00, 14:00 et 22:00, un script de 20 à 35 secondes (une seule idée, accroche dans les deux premières secondes, phrases de 4 à 11 mots) et sa légende. Règles relues avant chaque exécution : `Videos/SKILL-VIDEOS.md` (section « Règles pour Qwen » injectée dans les consignes).
- Ligne A (compte actuel) : stickman divertissement / explications, une chose concrète du web pour un artisan ou un commerçant ; fin = planning de 15 minutes de Liam (lien LU dans `B2B/docs/SCRIPT-APPEL-SID.md`, jamais recopié dans un fichier du dépôt).
- Ligne B (compte séparé, recrutement de call callers) : sketch à deux (`Videos/agents/sketches.py`, `Videos/sketches-base.json`, 30 sketches écrits à la main : 40 % comédie au téléphone, 40 % leçons de vente, 20 % entrepreneuriat et quotidien). Le code vérifie toute la base (schéma, 6 à 8 répliques de 10 mots au plus avec la valeur la plus longue, interdits, 3 fins), propose les 3 premiers sketches autorisés (catégorie en retard d'abord, aucun des 20 derniers) ; Qwen choisit le sketch et les valeurs ({metier}, {objet}, {lieu}, {nom}) dans les listes ; toute autre réponse = choix du code (valeurs tournantes). Script écrit avec qui parle, jeu, bruitages, retournement, fin FIN1-3.

## Ordres pas à pas (lus dans le script)
1. `C.exiger("videos-scripts", ...)` ; Qwen (`modele`, qwen2.5:3b) est démarré en silence s'il ne répond pas, puis arrêté s'il a été démarré ici.
2. Pour chaque passage sans script : série (`series_par_passage`), angle pas encore traité, note de veille du jour.
3. Qwen répond en JSON (sujet, titre, accroche, six phrases, légende) ; le code refuse et redemande (4 essais) si : chiffre ou nombre, promesse, gain, témoignage, superlatif, mot interdit, indication de mise en scène, phrase molle, lieu (ligne B), accroche trop longue, longueur hors 52-88 mots, sujet proche d'un sujet déjà traité.
4. Les seuls chiffres (15 minutes, taux de commission de la config s'il est rempli) sont ajoutés par le code dans la phrase de fin et la légende ; la légende porte toujours « Contenu généré par IA. ».
5. Écrit `Videos/scripts/AAAA-MM-JJ-HHMM.json`, ajoute le sujet à `Videos/scripts/sujets.json` (jamais deux fois le même), une ligne de journal.

## Entrées et sorties (place dans la chaîne)
- **Reçoit de :** **Veille** (`Videos/veille/AAAA-MM-JJ.md`, facultative) ; `Videos/sketches-base.json` (ligne B) ; `Videos/scripts/sujets.json` (sujets déjà traités).
- **Produit :** `Videos/scripts/AAAA-MM-JJ-HHMM.json` (sujet, titre, accroche, scènes, légende avec « Contenu généré par IA. ») et le sujet ajouté à `sujets.json`.
- **Passe à :** **Marketing** (05:30) retravaille chaque script du jour ; à défaut, **Création** l'utilise tel quel.
- Chaîne vidéo : Veille → Scripts → Marketing → Création (→ Monteur, ligne B) → ton OK de Liam (« go publier », une fois par ligne) → Publication → Nettoyage. Fiche : `docs/agents/⛓️ Chaîne vidéo.md`.

## Ce qu'il ne fait jamais
- Inventer un chiffre, un résultat, un client ou un témoignage ; promettre un gain.
- Utiliser un modèle payant ou des tokens Claude ; publier quoi que ce soit.

## Cas d'erreur
- 4 réponses de Qwen refusées par les garde-fous : pas de script pour ce passage, code 2, trace `ok: false` ; Création s'arrête alors sur « script manquant » (code 2).
- Ollama ne répond pas après 30 s : code non nul, trace `ok: false` avec l'erreur.
- Script bloqué par la garde du harness (secret, phrase interdite, lien Stripe non autorisé) : rien n'est écrit, trace `ok: false` « garde contenu ».
- Machine non active ou `SKILL-VIDEOS.md` incomplet : refus code 3.
- Toute erreur laisse une trace `ok: false`, lue par le surveillant si l'agent est dans `agents_actifs`.

## Règles qu'il suit
- Il relit `Videos/SKILL-VIDEOS.md` avant chaque exécution (`C.exiger_regles` : absent ou incomplet = refus, code 3), sections « Règles pour Qwen » (injectée dans les consignes), « Deux lignes éditoriales ».
- Harness : contrat `B2B/harness/contrats/videos-scripts.json` (`peut_engager: false`) ; garde du contenu `C.garde_harness` avant écriture (secret, phrase interdite d'`OFFRE-REFERENCE.json`, lien Stripe non autorisé ; `B2B\STOP` bloque la publication, pas la fabrication) ; une trace par exécution (`C.lancer` : commande, durée, ok, erreur ; rien pour `etat` ni `--a-blanc`) dans `B2B/logs/agents/videos-scripts/AAAA-MM-JJ.jsonl`.
- Ce qui engage Liam (publier, envoyer, encaisser, signer) n'est jamais fait sans son accord ; la publication reste verrouillée par ligne jusqu'à son « go publier ».
- Règle d'or : pas de preuve = pas de fait. « Il a tourné » se prouve par la trace du jour (`ok: true`) et le fichier produit ; « c'est corrigé » par `python tests\agents\test_videos.py` puis `tests\b2b-rapide.ps1` en vert, sortie montrée.

## Vérifier qu'il a bien tourné
- `python Videos\agents\scripts.py etat` ; `python Videos\agents\scripts.py passage --heure 06:00 --a-blanc` (Qwen, rien d'écrit).
- Test : `python tests\agents\test_videos.py` (Qwen remplacé par un bouchon). Pas de preuve = pas de « fait ».

## Quand il alerte Liam
- Jamais directement : le surveillant signale l'absence de trace après 05:45 ou une trace en erreur (4 essais refusés = code 2).
