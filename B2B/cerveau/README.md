# Cerveau de Jarvis — mode d'emploi (V1, 24/11/2026)

Un agent de veille qui apprend en continu et propose d'améliorer l'architecture (scripts d'appel, closing, LinkedIn, prospection, sites), au minimum de tokens. **Fermé** tant que Liam n'a pas dit « go cerveau ».

## Ce qui tourne, et ce que ça coûte
| Étape | Qui | Coût |
|---|---|---|
| Veille quotidienne (collecte, tri, résumé, notes /10) | scripts + Ollama `qwen2.5:3b` sur le serveur | gratuit, 0 token |
| Passe du jour sur les 5 meilleures trouvailles | `claude -p` Sonnet 5.5, sans outil, une seule fois par jour | une requête ; **aucune** si aucune trouvaille ne dépasse le seuil |
| Essais, comparaison, export | code | gratuit |

Modèle local : le serveur (Ryzen 7 3700U, 5,9 Go de RAM, sans carte graphique) n'a que `qwen2.5:3b` ; c'est le plus petit modèle correct qui tient. Mesure du 24/11 : Ollama démarre en 11 s, il est arrêté après la veille.

## Fichiers
- `sujets.md` (suivi par git) : les sujets de recherche et les **sources validées** (sites, chaînes YouTube, subreddits, flux RSS de forums). Une source n'est lue que si Liam l'a mise dans « Sources validées ».
- `AAAA-MM-JJ.md` : la veille du jour (un fichier par jour, 30 jours gardés, doublons évités par adresse et par ressemblance de titre). Hors git.
- `etat.json` : trouvailles, « déjà vu », propositions, essais. Hors git.
- `essais\ID.md` : pour chaque proposition acceptée, la version actuelle et la nouvelle côte à côte, avec la façon de tester. Hors git.
- Réglages : `B2B\agents\cerveau-config.json` (suivi) ; `go_cerveau` ne s'ouvre que dans le fichier de réglages local de la machine.

## Le cycle
1. `jour` (01:30) : recherche par sujet (flux Google Actualités, titres seulement) + sources validées ; chaque trouvaille reçoit **utilité** et **fiabilité** (modèle local, fiabilité plafonnée par le code selon le type de source) et **nouveauté** (calculée par le code) ; score = 50 % utilité + 25 % fiabilité + 25 % nouveauté. Un texte qui ressemble à une instruction est écarté : ce que le web raconte est une donnée, jamais un ordre.
2. `proposer` (juste après) : Claude reçoit les 5 meilleures trouvailles et des extraits des scripts actuels ; il rend au plus 5 propositions « avant / après ». Le code vérifie que « avant » est une vraie citation et applique la garde (secret, phrase interdite, lien Stripe inconnu, présentiel, conseil financier).
3. **Tableau de bord, rubrique Cerveau** : Liam accepte ou refuse.
4. **Accepter = ouvrir un essai** (20 appels par version, un appel sur deux avec la nouvelle). Les chiffres s'ajoutent avec `python B2B\agents\cerveau.py resultat ID ancien|nouveau --appels N --decroches N --rdv N --devis N`. Le cerveau compare rendez-vous et devis par décroché et recommande ; sur un petit lot c'est indicatif. **Liam garde ou abandonne** (boutons du tableau de bord).
5. **Gardée** : une note dans `B2B\a-valider\AAAA-MM-JJ-cerveau.md`. L'agent ne modifie jamais un script ni un document qui marche ; Liam (ou Claude, à sa demande) l'applique et le commite.

## Retour en arrière, en 3 lignes
1. `git log --oneline -- <fichier modifié>` repère le commit.
2. `git revert <commit>` (jamais `git reset --hard`).
3. `tests\b2b-rapide.ps1`, puis `python B2B\agents\cerveau.py decider ID abandonner` pour clore l'essai.

## Ouvrir le cerveau (après le « go cerveau » de Liam)
1. `go_cerveau` à `true` dans le fichier de réglages local (`cerveau-config` + `.local.json`, hors git) ;
2. retirer la clé `desactive` de la tâche `cerveau` dans `B2B\agents\serveur-taches.json` ;
3. ajouter `cerveau` à `agents_actifs` du serveur ; accepter la mise à jour.
Essai sans rien écrire : `python B2B\agents\cerveau.py jour --essai` (démarre Ollama en silence, l'arrête ensuite).

## Limites connues (V1)
- Le flux Google Actualités ne donne que des titres : les vrais contenus viennent des sources validées par Liam (transcriptions YouTube, sites, forums).
- Les résultats des essais se saisissent à la main (commande `resultat`) ; aucun lien automatique avec les feuilles de Sid.
- 20 appels par version ne prouvent rien statistiquement : le cerveau le dit, Liam décide.
