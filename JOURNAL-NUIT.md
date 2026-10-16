# JOURNAL-NUIT — réduire le temps de réponse (Discord d'abord, voix ensuite)

Session autonome du 16/10/2026. Rien n'a été poussé sur GitHub. Jarvis a été arrêté (`arreter.ps1`) avant `tests\tout.ps1`, puis relancé.

## Lectures retenues (doutes tranchés sans vous demander)
- Le second énoncé de la tâche (objectif principal : Discord sur le serveur, secondaire : voix) a remplacé le premier ; je l'ai suivi.
- « Pas de clé API » : `ANTHROPIC_API_KEY` n'est pas dans `.env` → je n'ai rien demandé. Le code utilise l'API si la clé existe, sinon `claude -p` allégé. L'API n'a donc **pas pu être testée en vrai** ici (testée contre un faux serveur SSE local).
- Une « question hors règles » = question ouverte (pourquoi, explique, donne-moi une idée…). Tout ce qui ressemble à une commande, à la mémoire/to-do, au marché ou à l'investissement reste traité par Jarvis (permissions, confirmations, routeur) : le nouveau module ne produit que du texte.
- Le modèle rapide est `claude-haiku-5-5` (API) et l'alias `haiku` (claude -p). Je l'ai aussi mis en `claude_modele` pour Jarvis (voix/PC) : sur mes mesures il renvoie du JSON valide 6 fois sur 6 et gagne ~1,2 s.
- Le message « je réfléchis… » : pour la conversation directe, vrai message modifié ensuite ; pour les commandes qui passent par Jarvis, l'indicateur « en train d'écrire » existant (immédiat) suffit.
- Les tests réels exigeant micro, son ou orbe n'ont pas été lancés (règles du projet). Les chiffres vocaux « avant » viennent du diagnostic réel déjà enregistré (`logs\diag-voix-*.jsonl`).

## 1) Mesures AVANT (rien changé)
**Chemin d'un message Discord « hors règles » (code lu et journaux) :**
1. Discord → `pont.py` (Python, déjà en marche : pas de relance) → écrit un fichier JSON dans `memoire\discord\entrant`.
2. La boucle PowerShell de Jarvis (déjà en marche) relève le dossier toutes les ~250 ms → file d'attente.
3. `Invoke-OrdreCorps` : règles (≈ 10 ms), puis **routeur Ollama** (modèle 7B) puis **`claude -p`** avec le prompt complet.
4. Réponse écrite dans `memoire\discord\sortant`, relevée par le pont toutes les 0,3 s, envoyée.
- **Aucun `powershell.exe` n'est relancé par message** (Jarvis et le pont sont deux processus permanents). Mais **chaque question ouverte relance `cmd.exe` + `claude.cmd` (Node) en entier** : `claude -p` démarre à froid à chaque fois.

| Étape | Mesuré sur ce PC (GPU) | Sur le serveur (CPU, 5,9 Go) |
|---|---|---|
| pont → fichier → Jarvis → file | ≈ 0,3–0,5 s (poll 250 ms + 300 ms) | idem |
| règles | 0,01–0,04 s (journal) | idem |
| routeur Ollama 7B (avant `claude`) | 1,2–3,4 s (journal : « routeur en 2,80 s », « 3,39 s ») | **non mesuré ici** ; 7B sur CPU + chargement à froid = la grande part de la minute (délai maxi du routeur 20 s, puis `claude`) |
| `claude -p`, prompt complet, modèle par défaut | **4,77 s en moyenne** (3,2–6,7) sur 3 questions ouvertes | plus long (CPU, 5,9 Go) |
| envoi Discord | < 0,5 s | idem |

**Voix (gros PC), diagnostic réel du 15/10 :** fin de phrase 240 ms à 4 s selon l'ambiance ; reconnaissance Whisper **10–17 ms** (modèle chaud, cuda) ; routeur ≈ 1,0–1,7 s ; « chargement du modèle » Ollama 7,5 s **une fois** (réveil) ; Claude 6,8 s ; synthèse Edge 12 ms–1,6 s. Exemple question ouverte : **15,2 s** de la fin de parole au premier son (silence 4 s + Claude 6,8 s + routeur 1 s + attente). Exemple commande : 4,8 s. Whisper et Ollama ne se rechargent donc pas à chaque échange (déjà le cas) ; ce qui coûtait : la **réponse complète attendue** avant de parler et `claude -p` à froid.

## 2) Corrections
1. `pont-discord\conversation.py` (nouveau) : réponse directe depuis le pont, sans fichier d'échange, ni boucle PowerShell, ni Ollama.
   - Règles locales instantanées : heure, date, salutations, remerciements.
   - Sinon API Anthropic en streaming (`aiohttp`, clé `ANTHROPIC_API_KEY`), modèle `discord_conversation_modele`.
   - Sans clé ou si l'API échoue : `claude -p` allégé lancé directement par Python (`--tools ""`, un tour, `haiku`, prompt court de 12 lignes).
   - « 💭 Je réfléchis… » aussitôt, modifié au fil du flux (≈ 1 fois/s), puis remplacé par la réponse finale. Si aucune voie n'est dispo (plafond, panne) : message retiré et Jarvis reprend la main comme avant.
   - Mémoire des 10 derniers échanges (disque), majordome courtois, 2–3 phrases, aucun conseil d'investissement, plafond quotidien partagé avec Jarvis.
2. Serveur léger : `Get-ModeCerveau` renvoie `claude` en mode serveur (plus de routeur ni de modèle local chargé) sauf `serveur_cerveau_local: true`.
3. Voix : `claude_flux: true` (1re phrase dite pendant que Claude écrit la suite ; le code et ses tests existaient, désactivés), `claude_modele: haiku`, réponses 2–3 phrases (320 car.), historique Jarvis porté à 10 échanges.
4. `jarvis.ps1 notifier "texte"` + `pont-discord\notifier.py` : poste dans le salon système via le bot (REST direct, sans mention, jeton jamais affiché).

## 3) Mesures APRÈS
Sur ce PC (réel, `claude -p` allégé appelé par Python, 3 questions ouvertes) : **3 750 / 3 719 / 3 765 ms** de bout en bout (soit −1 s sur le prompt complet par défaut, et **sans** le routeur ni la boucle PowerShell). Règles locales (heure, date, salut) : **< 5 ms**. `mesure-claude.ps1` (haiku, prompt complet) : 3,63 s ; (haiku, prompt court) : 3,42 s ; (modèle par défaut) : 4,77 s / 5,15 s.

| Cas | Avant | Après |
|---|---|---|
| Discord : heure / date / salut | 0,5–5 s (PowerShell) ; sur serveur : routeur CPU possible | **instantané** (< 0,1 s, aucun appel) |
| Discord : question ouverte, **sans clé API** | ≈ 5–6 s ici ; **~2 min sur le serveur** (routeur 7B CPU + `claude` à froid) | ≈ 3,7 s ici (mesuré) ; serveur : plus de routeur ni de modèle → il reste `claude -p` seul (**à mesurer sur le serveur**, estimé 6–12 s) |
| Discord : question ouverte, **avec clé API** | — | attendu **≈ 1–2 s** jusqu'au premier mot, réponse courte complète en ≈ 2–3 s (**non mesuré : pas de clé**) |
| Voix : question ouverte | 15,2 s (journal réel, dont 4 s de silence de fin de phrase) | première phrase dite pendant que Claude écrit (gain attendu 1–3 s) + haiku (−1,2 s) ; **à constater en vrai** (test micro interdit) |

**Honnêteté :** mesuré ici = `claude -p` allégé (3,7 s) et la logique du pont (tests : flux SSE réel contre un faux serveur local, repli, plafond, mémoire, retrait du message d'attente). Visible seulement sur le serveur après la mise à jour (`maj-auto` ou `git pull`, puis relance) : le gain du routeur retiré. Visible seulement avec la clé : le « < 5 s » garanti. **Sans clé, le plancher est ~3,5 s sur ce PC** (démarrage de `claude -p`), donc < 5 s n'est tenable sur le serveur qu'avec la clé API.

## 4) Tests
- Nouveau `tests\conversation-pont.py` (40 vérifications, intégré à `tests\discord.ps1`) ; `serveur-leger.ps1` (cerveau serveur, config) ; `vitesse-v3.ps1` (flux activé, 3 phrases).
- `tests\tout.ps1` : **31 suites vertes**, contrôles de propreté OK (config.json, memoire\, .env inchangés, aucun processus restant, aucun fichier temporaire).
- README et `.env.example` mis à jour.

## 5) À faire de votre côté
1. Créer une clé sur console.anthropic.com et l'ajouter dans `.env` : `ANTHROPIC_API_KEY=sk-ant-…`, puis `jarvis.ps1 env-pousser` et `git push` (vous poussez vous-même) pour la copier chiffrée sur le serveur.
2. Sur le serveur : `git pull` (ou attendre `maj-auto`), puis relancer Jarvis. Vérifier dans les logs du pont : « conversation directe : API Anthropic (streaming) ».
3. Réessayer à la voix sur le gros PC une question ouverte et dire si la première phrase part bien tôt (`claude_flux` est maintenant actif ; repasser à `false` si besoin).
