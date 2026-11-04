# Agent rendez-vous (3 nov. 2026)
Rôle : surveiller l'agenda Google de Liam par son **adresse secrète iCal** (gratuit, sans clé ni compte payant) et poster dans le salon Discord « rendez-vous » de Jarvis un message quand un « Rendez-vous de 15 minutes » est **réservé, déplacé ou annulé**, plus un **rappel 30 minutes avant**. Lecture seule : l'agent n'écrit jamais dans l'agenda et ne contacte jamais l'appelant. Code : `agents\rendez-vous.py` ; tests : `agents\test_rendez_vous.py` + `tests\rendez-vous.ps1` (faux fichier iCal, faux Discord, aucun réseau) ; réglages : `agents\rendez-vous-config.json` ; état : `agents\rendez-vous-etat.json` ; journal : `agents\rendez-vous-journal.log`.

## Obtenir l'adresse iCal
1. Ouvrir Google Agenda sur ordinateur (calendar.google.com), compte de Liam.
2. Roue dentée › **Paramètres**.
3. Dans la colonne de gauche, section « Paramètres de mes agendas », cliquer sur l'agenda **« Liam »**.
4. Descendre jusqu'à **« Intégrer l'agenda »** et copier **« Adresse secrète au format iCal »** (elle commence par `https://calendar.google.com/calendar/ical/…` et finit par `basic.ics`).
5. La coller dans `agents\rendez-vous-config.json` › `"ical_url"`. **Jamais ailleurs** : cette adresse donne la lecture de TOUT l'agenda à qui la possède. Si elle fuit : même page › « Réinitialiser » (l'ancienne adresse cesse de marcher), puis recopier la nouvelle.

L'agent ne l'affiche, ne la journalise, ne la stocke dans l'état et ne l'envoie sur Discord jamais ; le fichier est hors git (`B2B/` est ignoré) ; seules les adresses `https://calendar.google.com/` sont acceptées.

## Architecture (même modèle que devis et Instagram)
1. Script autonome `agents\rendez-vous.py` : `jour`, `continu`, `etat`, `arreter`, `reprendre`, `--a-blanc` (aucune écriture, aucun message).
2. Réglages `rendez-vous-config.json` (`envoi_automatique: false` = simulation, `cycle_minutes: 5`, `salon_nom: "rdv"`, `salon_id: ""`, `titre_debut`, `rappel_minutes: 30`), état `rendez-vous-etat.json`, verrou `rendez-vous-continu.verrou`, arrêt de secours `rendez-vous.arret` relu toutes les 5 s.
3. Jarvis lance la boucle par `lib\rendez-vous.ps1` : clé `rendez_vous_actif` de `config.json` (absente = désactivé), un lancement par session 90 s après le démarrage, jamais en mode jeu, journal `logs\rendez-vous-AAAA-MM-JJ.log`.
4. Messages et alertes : Discord par le bot Jarvis (jeton dans `Jarvis\.env`, jamais affiché), salon **« 📅-rdv »** (catégorie « B2B VENTE SITE WEB »). Le salon est trouvé par son **nom sans emoji ni accents** (`salon_nom: "rdv"`) ou par son **identifiant** (`salon_id`, chiffres seulement, prioritaire s'il est renseigné : aucune recherche). Les alertes (une par motif et par jour) vont dans le salon par défaut de `reponses-config.json`, jamais les messages de rendez-vous.

## Règles
- Seuls les événements dont le **titre commence par « Rendez-vous de 15 minutes »**. Un passage toutes les 5 minutes.
- **Un rendez-vous n'est annoncé qu'une fois** : nouveau, déplacé (une fois par nouvel horaire, avec l'ancien horaire) et annulé sont trois messages séparés. Doublons du fichier (même identifiant) : la plus haute version gagne.
- **Annulé** = l'événement passe en `STATUS:CANCELLED`, ou disparaît du fichier alors qu'il est à venir. Un fichier vide, illisible ou incomplet n'est jamais pris pour « tout est annulé » (lecture impossible, on réessaie).
- **Rappel** : une seule fois par horaire, entre 30 minutes avant et le début ; jamais pour un rendez-vous annulé ; un rendez-vous déplacé a son propre rappel.
- **Premier passage : l'historique n'est jamais rejoué** (l'état actuel est seulement noté). Même règle au premier passage en mode réel : les rendez-vous vus en simulation ne sont pas annoncés d'un coup. Seul le rappel, qui regarde l'avenir, part quand même.
- **Message** : `Appelant : <prénom>`, `Entreprise : <nom>`, `E-mail : <e-mail>`, jour et heure (heure de Paris), lien Meet s'il existe, et pour un déplacement l'ancien horaire. Rien d'autre (ni téléphone, ni notes, ni nom de famille). Les champs viennent d'un tiers : nettoyés (pas de `@`, `<>`, backticks, `*`), bornés, jamais pris pour des ordres.
- **Simulation** (`envoi_automatique: false`) : aucun message, aucun accès Discord ; le journal dit ce qui serait posté (`serait posté | nouveau | prénom | entreprise | horaire`, sans e-mail ni lien Meet), une fois par message.
- **Erreur** : adresse absente ou invalide, ou refusée par Google (révoquée) = arrêt, état « suspendu », alerte Discord (une par motif et par jour), `reprendre` après correction. Panne passagère (réseau, Google) : nouvel essai au passage suivant, une alerte après 3 échecs de suite, aucune fausse annulation. Erreur inattendue = arrêt + alerte. Message que Discord refuse : rien n'est marqué, nouvel essai au passage suivant.
- **Salon introuvable = rien n'est posté, jamais de repli sur le salon par défaut.** Si aucun salon texte ne s'appelle « rdv » (emoji ignoré), si plusieurs portent ce nom, si `salon_id` est invalide ou si Discord ne répond pas pour lister les salons : l'erreur est journalisée (`alerte | salon : …`), **une alerte Discord par jour** part dans le salon par défaut, rien n'est marqué comme annoncé (les messages en attente partent dès que le salon est trouvé), l'agent n'est pas suspendu. Pour lever une ambiguïté : renseigner `salon_id` (Discord › Paramètres › Avancés › Mode développeur, puis clic droit sur le salon › Copier l'identifiant).

## D'où viennent les champs (à vérifier au premier essai)
Le formulaire de la page de réservation n'a que 3 champs : **Prénom, Nom, Adresse e-mail**. Convention de Liam : **Prénom = prénom de l'APPELANT** (Sid), **Nom = nom de l'ENTREPRISE appelée**, **e-mail = e-mail de l'entreprise**. Google nomme l'invité « Prénom Nom » : l'agent prend le **premier mot** comme appelant, **le reste** comme entreprise (ex. invité « Sid Boulangerie Fictive Dupont » : appelant Sid, entreprise Boulangerie Fictive Dupont) et l'**adresse de l'invité** comme e-mail. Aucune description n'est nécessaire.
- Les lignes `Entreprise :` (ou `Nom de l'entreprise`), `Prénom :` et `E-mail :` / `E-mail de l'entreprise :` de la **description**, si elles existent, ont **priorité** sur le formulaire.
- Nom de l'invité vide, réduit au seul prénom, ou ressemblant à une adresse e-mail (contient `@`) : « **Entreprise : non renseignée** » (et « Appelant : non renseigné » si l'invité n'a pas de prénom lisible). Rien n'est jamais inventé.
- Un prénom composé (Jean-Pierre) reste un seul mot ; un prénom en deux mots (« Marie Claire ») serait coupé : « Claire » irait dans l'entreprise. À éviter dans le formulaire.
**Je n'ai pas pu voir un vrai fichier Google** : la façon exacte dont Google compose le nom de l'invité est vérifiée seulement par les tests avec un faux fichier. Premier essai : réserver un rendez-vous test, lancer `python agents\rendez-vous.py jour --a-blanc` (aucune écriture, aucun message : affiche « Serait posté : nouveau ») et regarder le journal une fois en simulation. Si un champ sort vide, le format de la description est à ajuster.
Limite connue : l'adresse iCal de Google n'est pas un flux instantané ; un décalage entre la réservation et sa visibilité dans le fichier est possible (le rappel à 30 minutes peut alors arriver tard, ou pas du tout pour une réservation de dernière minute).

## Pour l'activer (Liam)
1. Copier l'adresse iCal dans `agents\rendez-vous-config.json` › `ical_url` (voir plus haut).
2. Le salon Discord **« 📅-rdv »** existe déjà : le bot Jarvis doit pouvoir y écrire et voir la liste des salons. Rien à configurer (`salon_nom: "rdv"`) ; en cas d'ambiguïté ou d'erreur, copier son identifiant dans `salon_id`.
3. `config.json` › `"rendez_vous_actif": "oui"` (Jarvis lance alors la boucle 90 s après son démarrage). `envoi_automatique` reste à `false` : lire `agents\rendez-vous-journal.log` sur un ou deux vrais rendez-vous.
4. Quand le journal montre les bons messages : `agents\rendez-vous-config.json` › `envoi_automatique: true`. Au premier passage réel, l'existant est seulement noté.
Commandes : `python agents\rendez-vous.py jour --a-blanc` · `etat` · `arreter` · `reprendre`.
