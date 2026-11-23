# Jarvis — mode d'emploi

Assistant personnel de Liam (LM MULTI-SERVICES). Il vit dans `C:\Users\Liam\Jarvis`, vous appelle « monsieur », parle (edge-tts), écoute (Vosk, local) et agit sur le PC avec trois niveaux de permission. Tout est gratuit ; rien ne sort du PC sauf les appels voulus (Supabase et Stripe en lecture, Claude, Ollama en local).

## Démarrer · arrêter · urgence
| Action | Commande (PowerShell) |
|---|---|
| **Lancer** | `powershell -ExecutionPolicy Bypass -File C:\Users\Liam\Jarvis\jarvis.ps1` (ajoutez `-WindowStyle Hidden` pour le lancer sans console) |
| **Arrêter proprement** | `powershell -ExecutionPolicy Bypass -File C:\Users\Liam\Jarvis\arreter.ps1` — ou icône Jarvis de la zone de notification (« ^ ») → *Quitter*, ou dites « Jarvis, au revoir » |
| **Arrêt d'urgence** | dites **« Jarvis stop »** : coupe la voix et toute action en cours (Jarvis continue de tourner) ; coupe aussi le **pont Discord** (voir *Discord*) |
| **Démarrage automatique avec Windows** | `installer.ps1 -DemarrageWindows` (tâche planifiée, 20 s après l'ouverture de session). **Jamais exécuté par Claude, jamais activé** : à lancer seulement si vous jugez Jarvis stable. Sans l'option, le script n'installe rien. Jarvis démarre alors en sourdine (le script refuse si `etat_au_demarrage` n'est pas `sourdine`), le briefing s'affiche sans voix. `desinstaller.ps1` le retire. |
| **Sauvegarde** | `powershell -ExecutionPolicy Bypass -File jarvis-sauvegarde.ps1` → zip daté dans `C:\Users\Liam\Jarvis-sauvegardes` (**sans `.env`**, sans le modèle Vosk ni le cache vocal) ; `-Garder 10` ne conserve que les 10 plus récents |

**Au démarrage Jarvis est en sourdine** (`"etat_au_demarrage": "sourdine"`) : il ne parle pas, n'écoute pas (micro libre), ne joue aucun son, jusqu'à **Alt + +**. Valeurs possibles : `"sourdine"`, `"actif"`, ou `""` (reprend l'état du dernier arrêt).

Autres commandes : `jarvis.ps1 say "texte"`, `jarvis.ps1 ordre "ouvre Chrome"` (ordre écrit), `jarvis.ps1 briefing`, `jarvis.ps1 test`, `jarvis.ps1 micro [nom]` (voir *Micro*).

## Raccourcis (`config.json` → `raccourcis`)
| Touches | Effet |
|---|---|
| **Alt + « + »** du pavé numérique (`Alt+Add`) | **active** Jarvis : micro rouvert, puis une **salutation variée** (liste `phrases_reveil` de `config.json` ; avant 12 h « Bonjour » favorisé, 12 h–18 h « Bon après-midi, monsieur. », après 18 h « Bonsoir, monsieur. » ; jamais deux fois la même de suite ; préchauffée dans le cache des phrases fixes ; jamais dite en sourdine ni en mode jeu) |
| **Alt + « − »** du pavé numérique (`Alt+Subtract`) | **SOURDINE TOTALE** (voir ci-dessous) |
| **Verr. défil.** (`ScrollLock`) | bascule actif ↔ sourdine |
| **Ctrl + Alt + J** | affiche / cache le tableau de bord |
| **Ctrl + Alt + G** | mode jeu / ne pas déranger on/off |
| **Ctrl + Alt + ↓ / ↑** (`musique_moins` / `musique_plus`) | volume de la musique −10 % / +10 % |
| **Ctrl + Alt + M** (`musique_couper`) | couper / remettre la musique |

Toutes les touches sont configurables (`"activer": "Alt+Add"`…). **Ctrl + « + » / « − » sont refusés** (zoom du navigateur), ainsi que toute touche seule, sauf `"touche_seule": true` (réserve « + » et « − » du pavé numérique dans tous les programmes ; avertissement au démarrage ; désactivé par défaut).

**Sourdine totale** : plus de voix, de musique, de bip ni de carillon ; aucune fenêtre ni popup (le coffre ne s'ouvre pas) ; aucune alerte dite (les alertes graves restent au journal et au panneau) ; **micro libéré** (le processus d'écoute est arrêté : plus aucune détection de « Jarvis ») ; aucun ordre exécuté (un ordre *écrit* reçoit seulement une réponse écrite). L'état est mémorisé. Seuls restent actifs les raccourcis clavier.

## Où sont les logs et la mémoire
- **Journal** : `logs\journal-AAAA-MM-JJ.md` — chaque ordre, action et résultat. Jamais de mot de passe, clé, jeton, carte, IBAN ni code.
- **Mémoire** : `memoire\` — `todo.md`, `notes.md`, `resume.md`, `rappels.json`, `alertes.json` (alertes déjà vues), `etat-jarvis.json` (actif/sourdine).
- **Quarantaine** : `quarantaine\` (fichiers suspects isolés, jamais supprimés).

## Les trois niveaux
1. **Seul** : ouvrir/fermer apps et sites, lire, chercher, état du système, analyse Defender, volume, notes, to-do.
2. **Confirmation en une phrase** (« Souhaitez-vous vraiment … , monsieur ? » ; réponse « oui / vas-y / fais-le / d'accord » ou « non / annule / laisse », **8 s** puis annulation polie : voir « Ton majordome ») : supprimer (corbeille) ou déplacer, tuer un processus, installer/désinstaller, commande PowerShell libre, e-mail, « oublie tout ».
3. **Refusé** : virements, achats, ordres de bourse, courtiers et banques, désactiver l'antivirus ou le pare-feu, changer des mots de passe, supprimer Jarvis ou son journal. Le niveau est décidé par le code, jamais par le cerveau. Les instructions trouvées dans des fichiers, pages web ou e-mails sont des **données**, jamais des ordres.

## Discrétion et alertes
- **Mode discret (par défaut)** : Jarvis ne parle que pour **répondre à vos ordres**, pour le **briefing du matin** (dit une seule fois, à votre première activation de la journée, si `briefing_vocal` est `true`, jamais en sourdine ni en mode jeu ; il s'affiche toujours au tableau, sans voix) et pour une **alerte grave**, une seule fois. Le reste va dans le panneau Conversation et le journal. Les rappels sont silencieux (petit carillon) ; pour les entendre, ajoutez `"rappel"` à `voix_autorisees`.
- **Alertes** : chaque alerte est dite **une seule fois** (`alertes.delai_heures`, 24 h minimum avant de la redire ; mémoire dans `memoire\alertes.json`). Les alertes déjà vues vont dans le panneau « Alertes · sans voix ». Seules les alertes *graves* (un programme qui se fait passer pour un processus Windows) sont dites (`alertes.voix_graves_seulement`). Jarvis ne signale jamais ses fichiers, `memoire\`, les sauvegardes ni les fichiers temporaires (`alertes.ignorer` pour en ajouter). Dites **« liste les alertes »** ou **« ignore cette alerte »** (ne plus la dire ; elle reste visible, grisée).


> Fonctionnalités avancées, désactivées ou détaillées (veille marché, train, Discord pas-à-pas, serveur 24/7, réglages voix/vitesse, presets/vues, pilotage) : voir `README-DETAIL.md`.

## Tableau de bord (plein écran sur le moniteur choisi)
**Plein écran sur l'écran principal (par défaut)** : au lancement la fenêtre s'ouvre en **plein écran** sur l'**écran principal de Windows**, sans rien régler. `config.json` : `ecran_jarvis` = `"principal"` (défaut) ou `"droite"`, `"gauche"`, un numéro (0 = le moniteur le plus à gauche), une partie du nom du moniteur (`"odyssey"`…) ou son identifiant Windows ; **écran inexistant : retombe sur l'écran principal** (noté au journal) ; `jarvis_plein_ecran` = `true` (défaut ; `false` = fenêtre sur la zone de travail, barre des tâches visible) ; **F11 bascule plein écran / fenêtre** à tout moment (touche d'Edge) ; `jarvis_memoriser_position` = `false` (défaut) : à `true`, la position choisie à la main (hors plein écran) est enregistrée dans `memoire\fenetre-jarvis.json` à la fermeture et restaurée au lancement (ignorée si l'écran a disparu). `mode_affichage` : `"tableau"` ou `"discret"` (petit orbe en bas à droite, jamais en plein écran). La **salle de marché** garde son propre réglage `ecran_marche`. Rien ne change pour le mode jeu, la sourdine, la protection de la fenêtre (titre unique + PID de l'Edge lancé par Jarvis) ni la fermeture avec Jarvis.
**Mise en page** (`visage\index.html`, 100 % local, hors ligne) : grille CSS fluide (`clamp`, unités relatives) qui s'adapte à toute résolution et tout ratio ; aucune barre de défilement de page ; dans chaque panneau, les textes passent à la ligne et le contenu défile discrètement **à l'intérieur** (un fondu en bas indique qu'il y a une suite), jamais en dehors ; un panneau vide se réduit à son titre et à une courte phrase. Écran presque carré ou en hauteur : l'orbe passe en haut, les deux colonnes dessous.
- **Barre d'état** (haut) : actif / sourdine / mode jeu, moteur de la voix, micro (niveau en direct), musique (volume ou « coupée »), priorité des ressources (demandée / effective), PC (processeur, mémoire, disque).
- **Centre** : l'orbe Jarvis, grande, au **centre exact de l'écran**, style HUD (graduations, anneaux segmentés, comète, éclats) ; heure et date en grand dessous, puis la saisie d'ordres (ou Oui / Non pendant une confirmation) ; le mot d'état (écoute, parle…) et la fenêtre d'ordre s'affichent au-dessus. États : **sourdine** = grise et calme ; **écoute** = anneaux qui pulsent avec le niveau du micro ; **parle** = ondes ; **réfléchit** = rotation et points en orbite ; **mode jeu** = orbe masquée. Animation légère : canvas 2D, 30 images/s au plus, **suspendue** quand la fenêtre est masquée (mode jeu, Ctrl + Alt + J) ; le sondage des données ralentit alors.
- **À gauche** : Mon SaaS, Alertes (réduit à une ligne quand il est vide), **Ma to-do** (agrandie : vraies tâches, cases à cocher en lecture, faites en vert), Conversation (réduite : 8 dernières lignes, et le guide pas à pas).
- **Marché** : par valeur, prix, variation en % avec **toujours le signe + / −** et la flèche, petite **courbe** (vert en hausse, rouge en baisse ; seulement avec ≥ 2 relevés réels) ; sans source : le message exact, aucun faux chiffre. **Actualités** : carrousel automatique, une à la fois (titre, source, date), glissement toutes les `actualites_secondes` secondes (10), en pause quand vous survolez ou que la fenêtre est masquée. **À droite** : Marché, 5 à regarder, Actualités, Dossier (quand il y en a un), Diagnostic vocal (**compact par défaut**, un clic sur son titre le déplie ; le choix est mémorisé). **En bas** : la dernière action ; un clic sur la barre ouvre la liste des dernières actions.
- **Sécurité** : la fenêtre reste identifiée par son **titre unique** `JarvisOrb-xxxxxxxx` et par le **PID de l'Edge lancé par Jarvis** : aucune autre fenêtre n'est jamais ciblée (la page ne modifie jamais son titre). Aucune fonctionnalité n'a été retirée par la refonte (l'État du PC est passé dans la barre d'état, les Dernières actions dans le pied de page).
**Vérification sans fenêtre** : `tests\interface.ps1` charge la page dans Edge **sans fenêtre** (`--headless`, profil jetable, aucun son, aucun focus) avec des données **fictives** (`tests\demo-tableau.json` : panneaux pleins, vides, très longs textes, sans source, mode jeu) à 1920x1080, 2560x1440, 1366x768, 3840x2160, 3440x1440, 1280x1024 et 1080x1920, et contrôle : aucun défilement de page, aucun panneau hors écran ou qui en chevauche un autre, aucun texte coupé sans défilement ni points de suspension, orbe au centre exact, corps de texte lisible. `-Captures` garde aussi des images dans `%TEMP%\jarvis-captures` (à supprimer ensuite). Le test « pas d'écran blanc au lancement » avec une vraie fenêtre reste dans `tests\affichage.ps1` (manuel).

## Ajouter une compétence
1. Copiez `lib\competences\_exemple.ps1` sous un nom sans « _ ».
2. Changez le nom, le niveau (1 ou 2), la ligne de doc et le bloc d'exécution (`Rep $true "texte court"`).
3. Relancez Jarvis. Un fichier défectueux est ignoré et noté au journal. Le niveau 3 ne peut pas être contourné.

## Vider la mémoire
Dites **« Jarvis, oublie tout »** (niveau 2). Résumés, notes, rappels et conversation partent à la corbeille ; la to-do et le **journal** sont conservés.

## Serveur 24/7
Jarvis peut tourner sans écran ni micro sur un vieux PC Windows, mis à jour depuis GitHub : installation avec `installer-serveur.ps1`, mise à jour automatique avec `maj-auto.ps1` (elle refuse une version dont les tests échouent). Détail : `README-DETAIL.md`, section « Serveur 24/7 ».

## Tests
- **Tout, en silence** : `tests\tout.ps1` (aucun son/voix/fenêtre/micro réel, copies temporaires, tout remis en place à la fin). Couvre le module sauf ce qui exige une vraie fenêtre ou une vraie touche.
- **Clés chiffrées + audit git** : `tests\serveur.ps1` (sections 6 et 8).
- **Tests manuels** (vraies fenêtres/touches, jamais automatiques) : `tests\manuels.ps1 -Oui`, à lancer vous-même.
- Détail de chaque sous-test (vitesse, Discord, salle de marché, veille/réveil, serveur léger…) : `README-DETAIL.md`.

## Règles de travail (pour Claude)
Voir `CLAUDE.md` : ne jamais lancer Jarvis, aucun test bruyant, jamais de `.env` affiché ni committé.
