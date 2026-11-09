# Agent appels-sid (3 nov. 2026)
Rôle : **tous les appels vont à Sid**. Chaque matin, l'agent cherche de nouvelles entreprises avec un numéro de téléphone, prépare la **liste d'appels de Sid** (50 à 60 entreprises jamais appelées), la dépose dans `docs\sid\liste-sid-AAAA-MM-JJ.csv` et, une fois autorisé, dans une **feuille Google** du dossier « Sid ». **Il n'envoie rien à une entreprise ni à Sid** (pas d'e-mail, pas de message) : le seul message qu'il poste est l'alerte Discord de réserve. Code : `agents\appels-sid.py` + `agents\google_sheets.py` ; tests : `agents\test_appels_sid.py` + `tests\appels-sid.ps1` (listé dans `tests\tout.ps1`) ; réglages : `agents\appels-sid-config.json` ; état : `agents\appels-sid-etat.json` ; journal : `agents\appels-sid-journal.log`.

**Simulation par défaut** (`envoi_automatique: false`) : ni Google, ni partage, ni message Discord ; le journal dit ce qui serait fait. Le sourcing et la liste CSV, eux, sont écrits (ce sont des fichiers locaux). **Rien n'est installé ni partagé tant que Liam n'a pas dit « active ».**

## Commandes
| Commande | Effet |
|---|---|
| `python agents\appels-sid.py jour [--jour AAAA-MM-JJ] [--a-blanc]` | **Le passage du matin** : sourcer, préparer la liste, créer le dossier et la feuille Google, mettre à la corbeille les dossiers Google de plus de 7 jours, alerte de réserve. C'est ce que lance la tâche planifiée. Un jour hors `jours_appel` (réglage) : rien n'est fait, juste noté dans le journal (voir plus bas). `--a-blanc` : décrit chaque étape, aucune écriture, aucun réseau. |
| `preparer [--jour …] [--a-blanc]` | Seulement la liste du jour (une par jour). |
| `sourcer [--jour …] [--a-blanc] [--dept 27] [--simulation]` | Cherche de nouvelles entreprises avec téléphone dans toute la Normandie (OpenStreetMap + SIRENE). `--dept` : un seul département. `--simulation` : aucun réseau, données fictives. `--a-blanc` : interroge Overpass et SIRENE (lecture seule) et dit combien seraient ajoutées, sans rien écrire. |
| `etat` | Réserve par métier, jours de réserve, liste de Liam (active ou redirigée), Google, partage, dernière liste. |
| `annuler [AAAA-MM-JJ] [--force] [--a-blanc]` | Libère les entreprises d'une liste non utilisée (refusé si une case ou une remarque du CSV est remplie). Le CSV est conservé en `.annulee.csv` ; un dossier Google déjà créé reste en place. |
| `google-autoriser` | Autorisation Google, **une seule fois** (voir plus bas). |
| `rediriger-liste` / `rendre-liste` `[--a-blanc]` | La liste d'appels quotidienne de Liam n'est plus produite / lui est rendue. |
| `installer-tache` / `retirer-tache` `[--oui]` | Tâche planifiée Windows. **Sans `--oui` : affiche seulement la commande PowerShell, n'exécute rien.** |

## Réserve et sélection (la logique de `prospection.py` est réutilisée, pas recopiée)
- **Métiers** : restaurants (numéro seulement, aucune page d'exemple), coiffeurs, plombiers-chauffagistes, électriciens. Jamais fleuriste, boulangerie ni garage. Répartition par poids (`repartition` : 12 / 12 / 13 / 18) ; si un métier manque, les autres complètent.
- **Reprise des listes de Liam** : les entreprises de `docs\liste-appels-*.md` **jamais appelées** (aucune case « appelé » ni « répondu ») entrent dans la réserve, avec leur ligne de `prospection-trouves.csv`. Appelées, refus ou STOP : jamais reprises.
- **Écartées** : déjà sorties pour Sid (état : ne ressortent jamais, sauf `annuler`), numéro invalide (10 chiffres français 01 à 07 ou 09, +33 accepté, jamais 08), même numéro déjà pris, STOP, refus, exclu, écarté, hors zone et vagues fermées (`zone.py`), e-mail dans `exclus-emails.json`, déjà contactée par e-mail ou ayant répondu (suivi).
- **Sources** : `prospection-trouves.csv` (« sans site, téléphone », « téléphone seulement », « listé »), `suivi-prospects.csv` (« à contacter »), `prospects_maps.csv`, et les lignes des listes d'appels.
- **Ordre de la liste = ordre de la journée de Sid** : artisans du bâtiment (avant 9 h ou vers 17 h), coiffeurs (milieu de matinée), restaurants (14 h – 16 h). Créneaux indicatifs, non mesurés.

## Sourcing : de nouveaux numéros dans toute la Normandie, gratuit (4 nov. 2026)
- **Zone** : la Normandie, départements **76, 27, 14, 50, 61** (réglage `departements`, `zone: "Normandie"` ; `rayon_osm_m`, le cercle de 40 km autour de Rouen, n'existe plus). Une entreprise dont le code postal est dans un autre département (Paris, Oise, Eure-et-Loir, Bretagne…) n'est jamais retenue ; sans code postal, on ne conclut pas.
- **Sources autorisées seulement** : OpenStreetMap (API Overpass, données ouvertes ODbL) et l'API officielle « Recherche d'entreprises » (data.gouv, SIRENE ; gratuite, sans clé). Ni Google Maps, ni Pages Jaunes, ni API payante, aucun compte avec carte.
- **OpenStreetMap, découpé** : UNE requête par département et par métier (relation OpenStreetMap du département, `area["ref:INSEE"=…]`, 90 s de délai), une à la fois, **15 s entre deux**, nouvelles tentatives après 30, 60 puis 120 s si Overpass refuse (429, 5xx) ou coupe. Au plus 6 requêtes par passage (`sourcing_requetes_max`) : toute la Normandie (20 requêtes) se couvre en quelques jours, la Seine-Maritime d'abord, puis l'Eure, le Calvados, la Manche, l'Orne. Une requête déjà faite n'est pas refaite avant 30 jours. Métiers : plombier-chauffagiste (`craft=plumber` et `craft=hvac`), électricien (`craft=electrician`), coiffeur (`shop=hairdresser`), restaurant (`amenity=restaurant` et `fast_food`).
- **SIRENE** (`sirene_actif`) : pour le même département et le même métier, les entreprises **actives** des codes NAF 43.22A et 43.22B (plombier-chauffagiste), 43.21A (électricien), 96.02A (coiffeur), 56.10A et 56.10C (restaurant) ; l'API ne donne pas de téléphone, il est donc cherché (1) sur la **fiche OpenStreetMap du même nom** (y compris une fiche sans commune), puis (2) sur le **site public** (domaines usuels du nom, robots.txt respecté, page vérifiée par la commune ou le code postal ; liens `tel:` puis numéros écrits). **Seules les lignes avec un numéro français valide (fixe 01 à 05 / 09 ou mobile 06 / 07, jamais 08) sont gardées.** Un site **correct** d'après le constat vérifié de la prospection exclut l'entreprise ; un site faible la garde (« téléphone seulement ») ; un site illisible l'écarte (aucun constat possible). Au plus `sirene_requetes_max` (12) appels d'API, `sirene_pages_max` (4) pages de 25 entreprises par code NAF, `sirene_sites_max` (30) pages de sites lues par passage, avec pauses (`pause_sirene_s`, `pause_site_s`) ; un curseur garde l'endroit où reprendre, chaque entreprise examinée est notée dans l'état (jamais examinée deux fois). Honnêtement : peu d'entreprises publient leur numéro sur un site trouvé au hasard, SIRENE ajoute surtout les numéros des fiches OpenStreetMap sans commune ; la source principale reste OpenStreetMap.
- **Jamais deux fois le même numéro** : déjà donné à Sid (colonne « Téléphone » de tous les `docs\sid\liste-sid-*.csv`, listes annulées exceptées), numéro d'une entreprise STOP / refusée / exclue, numéro déjà dans la prospection, le suivi, les cartes ou les listes, même sous un autre nom d'entreprise.
- Priorité aux métiers dont la réserve est sous leur part de la cible (`cible_reserve` : 220, environ 4 jours) : plombiers, électriciens, puis coiffeurs, restaurants.
- Écriture dans **`prospection-trouves.csv`** (statut « sans site, téléphone » ou « téléphone seulement », source « OpenStreetMap… » ou « SIRENE… ; téléphone : fiche OpenStreetMap / site public ») : les lignes existantes sont conservées, jamais de fichier à moitié écrit.
- **Fin de run** : le tableau « Réserve par métier et par département » (colonnes Seine-Maritime, Eure, Calvados, Manche, Orne, inconnu) puis « Réserve : N numéro(s) = X jour(s) à 55 numéros par jour ». Même tableau avec `etat` et à la fin de `jour`. Avec `--a-blanc` : réserve projetée (actuelle + ce que le sourcing aurait ajouté).
- **Essais** : `sourcer --simulation` (aucun réseau, données fictives, rien d'écrit, permise sur toute machine), puis `sourcer --a-blanc --dept 27` (vrai réseau, UN département, rien d'écrit), puis `sourcer --dept 27` (écrit). Ne pas lancer toute la Normandie d'un coup.
- Panne (réseau, Overpass, SIRENE) : alerte Discord (une par jour), ce qui a été trouvé avant est gardé, la liste du jour est quand même préparée avec la réserve existante, nouvel essai le lendemain.

## Jours d'appel et nettoyage du Drive (9 nov. 2026)
- **`jours_appel`** (réglage, en français et en minuscules, ex. `["lundi", "mardi", "vendredi"]`) : jours où la commande `jour` (celle de la tâche planifiée de 8 h) génère vraiment la liste. Au début de `jour`, le jour de la semaine **actuel** (fuseau Europe/Paris, `prospection.heure_paris`, pas celui de `--jour`) est comparé à `jours_appel` : hors planning, l'agent logge « jour hors planning, aucune liste générée » et s'arrête **immédiatement** (aucune liste, aucun dossier Drive, aucun partage, aucune alerte Discord). Réglage absent ou invalide = tous les jours (aucune restriction). La tâche planifiée Windows reste à 8 h **tous les jours** ; c'est le script qui s'auto-limite. Les autres commandes (`preparer`, `sourcer`, `etat`, `annuler`, `google-autoriser`, `rediriger-liste`…) restent utilisables tous les jours.
- **Nettoyage du dossier « Sid »** : à chaque passage réel de `jour` (après la liste du jour), les sous-dossiers `AAAA-MM-JJ` de plus de 7 jours sont mis à la **corbeille** (jamais supprimés définitivement) ; journalisé. Simulation (`envoi_automatique: false`) et `--a-blanc` : rien n'est listé ni touché.

## Google : dossier « Sid » > « AAAA-MM-JJ » > feuille
- API **Google Drive** seulement (gratuite, OAuth, compte `contact.lmsites@gmail.com`) ; la feuille est créée en convertissant le CSV, donc l'API Sheets n'est pas nécessaire. Portée minimale `drive.file` : l'agent ne voit que ce qu'il a lui-même créé. Client `agents\google-client.json`, jeton `agents\google-sheets-token.json` (hors git, jamais affiché ni journalisé), même mécanisme que `gmail_api.py`.
- Chaque jour : dossier « Sid » (créé une fois) puis sous-dossier du jour puis feuille « Liste d'appels AAAA-MM-JJ », colonnes : `#`, `Nom`, `Ville`, `Téléphone`, `Métier`, `Créneau conseillé`, `Constat vérifié`, `Page d'exemple`, `Appelé`, `Répondu`, `Rendez-vous pris`, `Refus`, `Remarque` (pas de colonne STOP ; le CSV local a les mêmes colonnes).
- **Rien n'est recréé ni écrasé** : si le dossier du jour existe, il est reconnu (état, sinon recherche dans le Drive) ; s'il manque seulement la feuille, seule la feuille est créée.
- **Partage** : `partager_avec` vide = rien n'est partagé. Avec l'e-mail de Sid (et `envoi_automatique: true`), le dossier « Sid » est partagé **en éditeur, une seule fois** (Google envoie alors son e-mail d'invitation à Sid).
- Un jeton d'un autre compte que `compte_google` est refusé avant toute création.

## Autorisation Google : une seule fois (à faire par Liam)
1. Console Google Cloud (console.cloud.google.com), projet de `google-client.json` › **API et services › Bibliothèque** › « **Google Drive API** » › **Activer**.
2. **Écran de consentement OAuth** : si l'application est en mode « Test », ajouter `contact.lmsites@gmail.com` comme **utilisateur test**.
3. Dans un terminal : `python agents\appels-sid.py google-autoriser` ; le navigateur s'ouvre, choisir `contact.lmsites@gmail.com`, accepter (avertissement « application non validée » normal : Avancé › Continuer), puis fermer l'onglet. Le jeton est enregistré.
4. Vérifier : `python agents\appels-sid.py jour --a-blanc` ne contacte pas Google ; l'essai réel est fait par le premier `jour` avec `envoi_automatique: true`.

## La liste d'appels de Liam
Elle est produite par `cmd_liste_matin` / `cmd_appels` de `prospection.py`, déclenchés à `liste_appels_heure` (08:00) dans `prospection-config.json`, puis postée dans « appels-du-jour ». **`rediriger-liste`** met `liste_appels_heure` à `99:99` (jamais atteinte) : plus aucun fichier `docs\liste-appels-*.md`, plus aucun message pour Liam ; le code de la prospection et l'envoi d'e-mails ne sont pas touchés ; l'ancienne heure est gardée, **`rendre-liste`** la remet. Limite : la commande manuelle `prospection.py appels` force encore une liste si Liam la lance lui-même. **Non appliqué tant que Liam n'a pas dit « active »** : sinon plus personne ne recevrait de liste.

## Tâche planifiée Windows (non installée)
`python agents\appels-sid.py installer-tache` affiche la commande : tâche `Jarvis-AppelsSid`, **tous les jours à 08:00** (`heure_tache`), **rattrapage au réveil du PC si manquée** (`-StartWhenAvailable`), une seule instance à la fois (`IgnoreNew`) en plus du verrou, 2 h au plus, session de Liam, sans fenêtre (`pythonw`), lance `appels-sid.py jour`. `installer-tache --oui` l'installe, `retirer-tache --oui` la retire.

## Sûreté
- **Verrou** `appels-sid.verrou` : deux lancements en même temps sont refusés ; repris s'il est laissé par un processus mort ou vieux de plus de 3 h. **Une panne ne bloque jamais les jours suivants** : chaque étape (sourcing, liste, Google) est isolée, journalisée, alertée une fois par jour, et le passage suivant rattrape (liste existante ni refaite ni re-marquée, Google rattrapé).
- Arrêt de secours : créer `agents\appels-sid.arret`. État illisible = arrêt avec message, état jamais écrasé.
- **Alertes** (salon Discord par défaut, comme devis et rendez-vous, en mode réel seulement) : réserve sous 110 entreprises (moins de 2 jours), sourcing en échec, Google en échec, liste impossible. Une par motif et par jour, **uniquement des nombres** ; le journal ne contient ni numéro, ni e-mail, ni nom d'entreprise.
- L'état (`appels-sid-etat.json`) = clés d'entreprises, dates, identifiants de dossier Google ; **aucun numéro**.

## Pour l'activer (Liam)
1. Autoriser Google une fois (4 étapes ci-dessus).
2. `agents\appels-sid-config.json` : `partager_avec` = e-mail de Sid (optionnel) puis `envoi_automatique: true`.
3. `python agents\appels-sid.py rediriger-liste` (plus de liste pour Liam).
4. `python agents\appels-sid.py installer-tache --oui` (tâche de 8 h 00).
5. Contrôle le lendemain : `python agents\appels-sid.py etat`, le journal, le dossier « Sid » dans le Drive.
