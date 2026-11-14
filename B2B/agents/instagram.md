Agent retiré du serveur le 14/11/2026 (décision de Liam). Archive.

# Agent Instagram (3 nov. 2026)
Rôle : publier UN post par jour vers 12 h 30 (heure de Paris) sur lmmultiservices.normandie, d'après la file et les légendes de `docs\INSTAGRAM-PLAN.md`, cocher la ligne avec la date, et fabriquer les prochaines cartes quand la file passe sous 3 posts. Code : `agents\instagram.py` ; tests : `agents\test_instagram.py` (hors ligne, aucune publication) ; réglages : `agents\instagram-config.json` ; état : `agents\instagram-etat.json` ; journal : `agents\instagram-journal.log` ; cartes à valider : `instagram-a-valider.md` ; rendu des cartes : `sites\outils\instagram-carte.mjs`.

## Architecture (même modèle que la prospection)
1. Script autonome `agents\<agent>.py`, commandes `jour`, `continu`, `arreter`, `--a-blanc` (aucune écriture).
2. Réglages `<agent>-config.json` (clés `_aide` ignorées, défauts dans le script, `envoi_automatique: false`), état `<agent>-etat.json`, verrou `<agent>-continu.verrou` (PID), arrêt de secours `<agent>.arret` relu toutes les 5 s.
3. Jarvis lance l'agent par `lib\<agent>.ps1` : clé `<agent>_actif` de `config.json` (absente = désactivé), un lancement par session 90 s après le démarrage, jamais en mode jeu, processus caché, journal `logs\<agent>-AAAA-MM-JJ.log`. L'agent ne dépend pas de Jarvis et s'arrête quand Jarvis s'arrête (`--pid`).
4. Alertes à Liam : Discord par le bot Jarvis (API REST, jeton lu dans `Jarvis\.env`, jamais affiché), un message par motif et par jour.
5. Secrets hors git (`B2B/` est ignoré) et jamais affichés : ici `agents\instagram-token.json`.
6. Tests silencieux : `agents\test_<agent>.py` + `tests\<agent>.ps1`, listés dans `tests\tout.ps1`.

## Règles reprises de `docs\INSTAGRAM-PLAN.md`
Une publication par jour (la case cochée du jour, par l'agent, par Liam ou par l'ancienne tâche de Claude, empêche toute seconde publication) · jamais de mot de passe saisi · connexion perdue, vérification de sécurité ou erreur : ARRÊT IMMÉDIAT, alerte Discord, suspension (`reprendre` pour lever) · aucune information inventée : seules les légendes écrites dans le plan partent, filtrées (pas de « garanti », « n° 1 », avis, chiffre de clients, label, prix en €) · une ligne sans légende ou dont l'état n'est pas exactement « à publier » (par exemple « à publier (… plus tard) ») n'est jamais publiée · aucun message privé, commentaire ni abonnement (l'agent n'a aucune fonction pour cela) · journal de chaque action · `envoi_automatique: false` = simulation.

## Commandes
`python agents\instagram.py file` (file, prochain post, lignes bloquées) · `jour [--a-blanc]` · `continu` · `visuels [--a-blanc]` · `valider` · `arreter` · `reprendre`.

## Publication réelle : API officielle Instagram (Graph API)
Image : déposée NON publiée sur la Page Facebook (adresse d'image), conteneur, attente du traitement, publication, vérification de la légende sur le profil. Reel : envoi direct du fichier. Le jeton part dans l'en-tête, jamais dans une adresse ni un journal. Un échec PENDANT la publication = « publication incertaine » : rien n'est rejoué, Liam contrôle le profil.

## Pour l'activer (Liam)
1. Compte Instagram en **professionnel** (gratuit), relié à la Page Facebook LM Multi-Services.
2. developers.facebook.com : créer une app (mode développement, Liam administrateur : pas de revue d'application pour publier sur son propre compte), ajouter le produit « Instagram », générer un jeton avec `instagram_basic`, `instagram_content_publish`, `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`, le passer en jeton longue durée puis en jeton de Page ; relever `page_id` et `ig_user_id` (`/{page-id}?fields=instagram_business_account`).
3. Créer `agents\instagram-token.json` : `{"access_token": "…", "ig_user_id": "…", "page_id": "…"}` (jamais collé dans un message).
4. **Désactiver la tâche planifiée qui tourne depuis Claude** (elle n'est pas visible depuis le dépôt).
5. `config.json` : `"instagram_actif": "oui"`. Laisser `envoi_automatique` à `false` quelques jours : lire `agents\instagram-journal.log` et `python agents\instagram.py file`.
6. Quand la simulation convient : `agents\instagram-config.json` › `envoi_automatique: true`. Premier jour réel : être présent à 12 h 30 et vérifier le profil.
