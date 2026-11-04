# B2B — règles permanentes (LM MULTI-SERVICES)

Ce fichier s'ajoute à `..\CLAUDE.md` (règles de Jarvis, toujours valables : ne jamais lancer Jarvis, aucun test bruyant, `.env` jamais affiché, aucun envoi sans accord).

## Sites, pages exemples et maquettes : règle permanente de Liam (30 oct. 2026)
À CHAQUE création, refonte ou modification d'un site, d'une page exemple ou d'une maquette — y compris quand la tâche est lancée par la boucle de prospection ou par un agent — :

1. **Lire d'abord `sites\moteur\REGLES-STYLE-SITES.md`** (interdits « signes IA », base obligatoire, sept familles de style, recettes, contrôle).
2. **Appliquer la chaîne de skills site-local, dans l'ordre** : références → direction artistique → palette signature → interface signature → structure variée → réalisme photos → interaction signature → conversion → notation.
3. **Une famille de style différente par métier**, et au moins 3 axes qui changent d'un métier à l'autre : famille, rayon des angles (jamais le même deux fois de suite), paire de polices. Couleur d'accent tirée d'un élément réel du commerce.
4. **Interdits** : ombres décalées, bordures épaisses (2-3 px), étiquettes inclinées, pilules identiques d'un site à l'autre, badge au-dessus du titre, un mot du titre en couleur, grille de 3 cartes à icône. Plus de 3 « signes IA » (section 1 du fichier de règles) = page refusée.
5. **Notation ≥ 8/10** (grille du skill site-local-notation-wow), refaire sinon (3 tours au plus), puis **montrer les captures mobile 390 px et PC 1280 px à Liam**.
6. **Rien n'est déployé** (b2b-demos.vercel.app) sans l'accord de Liam ; toute page reste en `noindex` avec la mention « exemple, pas votre site ».
7. Avant de livrer : noter la structure dans `sites\moteur\STRUCTURES.md`, les photos dans `CREDITS.json`, les références dans `REFERENCES.md`.

## Relecture des règles et des skills : décision de Liam (02 nov. 2026)
- **Avant CHAQUE page, et après toute reprise**, relire **en entier** `sites\moteur\REGLES-STYLE-SITES.md` et le `SKILL.md` de chaque skill site-local : chaine-obligatoire, page-longue, rythme-ecrans, la fiche métier du skill (metier-garage, metier-boulangerie, metier-plombier, metier-electricien ; fleuriste : sites\moteur\metiers\fleuriste.md écrite avant la page), animation-3d, direction-artistique, interface-signature, structure-variee, palette-signature, realisme-photos, signature-interaction, conversion, notation-wow, references. Les skills à jour sont dans `AppData\Local\Claude-Data\…\skills-plugin\…\skills\`.
- **Fiche par métier** `sites\moteur\metiers\<métier>.md` (identité, univers, ton, plan des écrans, 3D prévue, points de contrôle) : créée avec la page, relue à chaque modification. Le garage est validé par Liam avant de passer aux autres pages.
- Écrire **en tête de réponse** « **Skills relus :** » suivi de la liste. **Sans cette ligne, le travail n'est pas valable.** Un skill introuvable est signalé dans la ligne.
- Les pages sont désormais **longues et futuristes** (6 à 8 écrans, 700 à 1 100 mots, entrée orchestrée, animation par écran, section épinglée sur PC, 3D three.js sur PC avec repli mobile, Lighthouse mobile ≥ 90) : voir la section 6 de `REGLES-STYLE-SITES.md`. Notation complémentaire sur 10 : futurisme et animation, qualité de rédaction, valeur perçue ; refaire sous 8.
- Ordre de refonte : garage, boulangerie, plombier, électricien, fleuriste, une page à la fois ; ne rien déployer ; dire à Liam quelle page est prête et sa note.

Une tâche de site qui n'a pas lu le fichier de règles ou qui saute la notation n'est pas terminée.


## Ressources du PC : règles permanentes (décision de Liam, 02 nov. 2026)
Les navigateurs de test (headless_shell, chromium) ont fait monter le processeur de Liam jusqu'à 80 %. Le design ne change pas, seules les ressources sont limitées.

1. **Un seul navigateur de test à la fois**, jamais plusieurs en parallèle (pas de scripts de capture lancés en même temps, pas de second navigateur pendant qu'un premier est ouvert).
2. **Priorité basse et peu de processus** : le navigateur de test tourne en priorité « sous la normale » (`start /LOW`, ou `Process.PriorityClass = BelowNormal`) avec le moins de processus possible. Les scripts de `sites\outils\*.mjs` importent `chromium` depuis `.\nav-leger.mjs` (et non depuis `playwright`) : priorité basse héritée, un seul processus de rendu, verrou « une instance à la fois ». Tout nouveau script fait de même.
3. **Regrouper les captures** : une seule session de navigateur par tâche (un lancement, plusieurs pages et tailles), jamais un lancement par capture.
4. **Lighthouse, mesure de contraste, planche de comparaison : une seule fois, à la fin de la tâche**, pas après chaque petite modification.
5. **Fermeture en fin de tâche** : fermer tous les navigateurs de test (headless_shell, chromium) et le serveur local de test, vérifier avec `Get-Process` et le dire dans le compte rendu. Fermeture dans un bloc `finally` (ou par `nav-leger.mjs`) même en cas d'erreur.
6. **Jamais de `taskkill` global** sur `chrome.exe`, `node.exe` ou `python.exe` : arrêter le processus ou le port que l'on a soi-même lancé (par son PID, ou par sa ligne de commande, par exemple `http.server 8765`). Le Chrome de Liam, `prospection.py`, le pont Discord et Ollama ne sont pas à moi : ne pas y toucher.
