---
name: agent-appels-sid
description: Fiche de rôle de l'agent Liste d'appels de Sid (pôle Prospection) — chaque jour ouvré à 7 h 30, un seul tableur Google « Appels AAAA-MM-JJ » de 100 entreprises triées par créneau, dans le dossier Drive de Sid. À utiliser pour préparer, vérifier ou corriger la liste d'appels (appels-sid.py jour, preparer, sourcer, etat, annuler).
---

# Agent Liste d'appels de Sid — le tableur du jour

**Responsable :** Prospection (`.claude/skills/responsable-prospection/SKILL.md`). L'agent ne parle qu'à son responsable.
**Script :** `B2B/agents/appels-sid.py`, propre à cet agent. Il réutilise les fonctions de `prospection.py` (exclusions, zone) sans en lancer les commandes. Note : `docs/agents/📞 Appels Sid.md`.

## Ce qu'il fait
- **Quand :** du lundi au vendredi (`jours_appel`), à 7 h 30, il prépare **une** liste de 100 entreprises. Il en met au moins 100 et au plus 130.
- **Quelles entreprises :**
  - environ 20 métiers locaux, au plus 20 entreprises par métier ;
  - en Normandie seulement, réparties à tour de rôle sur les 5 départements (76, 27, 14, 50, 61) et mélangées entre métiers, jamais regroupées par ville ;
  - un téléphone valide, et aucun site trouvé ;
  - jamais une entreprise déjà donnée à Sid, à Liam ou dans un lot d'e-mails : registre commun `B2B/donnees/registre-entreprises.json` (hors git, `B2B/agents/registre.py`), à partir du 17/11/2026.
- **Avant la liste :** il lit la colonne Résultat des feuilles précédentes (Sid et Liam) et met le registre à jour. Ensuite seulement, il génère. Une feuille Google illisible n'est pas marquée lue : elle est relue au passage suivant.
- **Reprises (à partir du 17/11/2026) :** le Détail fiche indique « Reprise de la liste du … », avec la note.
  - Case vide en fin de journée : en tête de la liste suivante.
  - Pas de réponse : revient après 3 jours ouvrés, 3 essais au plus.
  - À rappeler : revient le jour écrit dans Note (20/11, 2026-11-24, jeudi, demain), sinon le jour ouvré suivant.
  - Je dois réfléchir : relance dans la liste de Liam 3 jours plus tard, jamais chez Sid.
  - RDV pris, Non catégorique, Trop cher, Déjà un site, Pas le temps : jamais redonnée.
  - La liste du lundi 16/11 suit encore les anciennes règles ; elle est lue dans le registre le 17/11.
- **Le tableur :** il crée **un seul** tableur Google « Appels AAAA-MM-JJ », posé directement dans le dossier Drive de Sid (`dossier_sid_id`), sans sous-dossier.
  - Les lignes sont triées par créneau, de 8 h à 19 h.
  - Les colonnes sont toujours, dans cet ordre : Créneau, Entreprise, Métier, Ville, Téléphone, Détail fiche, Résultat, Note.
  - Résultat est une liste de 8 valeurs, dans cet ordre : Pas de réponse, À rappeler, RDV pris, Non catégorique, Je dois réfléchir, Trop cher, Déjà un site, Pas le temps.
  - Les colonnes sont larges, l'en-tête est figé, aucune cellule n'est fusionnée.
- **Le ménage :** il met à la **corbeille** (jamais une suppression définitive) les tableurs « Appels AAAA-MM-JJ » de plus de 7 jours, seulement s'ils ont déjà été lus dans le registre. Il ne crée aucun dossier et ne touche à aucun autre fichier.
- **Le stock :** sous 3 jours de listes (Sid et Liam) d'entreprises neuves, une trace en erreur que le surveillant signale ; silence sinon.
- **La réserve :** il garnit sa réserve de numéros avec la commande `sourcer` (OpenStreetMap et SIRENE, gratuits).

## Ce qu'il ne fait JAMAIS
- Appeler, envoyer un SMS, un e-mail ou un message à une entreprise ou à Sid.
- Écrire un fichier `liste-appels-*.md` : c'est arrêté depuis le 14/11/2026. Les anciens sont rangés dans `B2B/docs/archives/`, en lecture seule.
- Redonner une entreprise STOP, refusée ou hors zone, ou un numéro déjà donné à Sid.
- Supprimer définitivement un fichier Drive, ou toucher un fichier qu'il n'a pas créé (portée `drive.file`).
- Demander une nouvelle autorisation Google sans l'accord de Liam.
- Afficher un jeton, `google-client.json`, un `*.local.json` ou `.env`.
- Installer ou retirer une tâche planifiée sans Liam (`--oui`).
- Affirmer qu'une entreprise n'a pas de site : la phrase reste « à confirmer avec vous ».

## Entrées et sorties
- **Entrées :**
  - `appels-sid-config.json`, plus la surcharge locale `envoi_automatique` ;
  - la réserve : `prospection-trouves.csv`, `prospects_maps.csv`, le suivi ;
  - `appels-sid-etat.json` et `appels-sid-historique.json` ;
  - le tableur de la veille, pour la colonne Résultat ;
  - le registre commun `B2B/donnees/registre-entreprises.json`.
- **Sorties :**
  - `B2B/docs/sid/liste-sid-AAAA-MM-JJ.csv` ;
  - le tableur Google « Appels AAAA-MM-JJ » ;
  - `appels-sid-etat.json`, `appels-sid-historique.json`, `appels-sid-journal.log` ;
  - une alerte Discord si la réserve est basse ou si Google tombe en panne.

## Ordres (commandes exactes, depuis la racine Jarvis)
| Ordre | Commande |
|---|---|
| Essai à blanc : le tableur du jour en texte, sans réseau ni écriture | `python B2B\agents\appels-sid.py preparer --jour AAAA-MM-JJ --a-blanc --hors-ligne` |
| Passage du matin (tâche de 7 h 30) | `python B2B\agents\appels-sid.py jour` (essai : `--a-blanc`) |
| La liste seule, en CSV local | `python B2B\agents\appels-sid.py preparer --jour AAAA-MM-JJ` |
| Garnir la réserve | `python B2B\agents\appels-sid.py sourcer` (essai : `--a-blanc` ; un département : `--dept 27` ; sans réseau : `--simulation`) |
| Réserve, dernière liste, état de Google | `python B2B\agents\appels-sid.py etat` |
| Libérer une liste qui n'a pas servi | `python B2B\agents\appels-sid.py annuler AAAA-MM-JJ` (essai : `--a-blanc`) |
| Autorisation Google, **par Liam seulement** | `python B2B\agents\appels-sid.py google-autoriser` |

Sur le serveur, la commande `jour` tourne à 07:30 (`serveur-taches.json`, `heure_tache`). Un samedi ou un dimanche, elle note « jour hors planning » et ne fait rien.

## Critère de fin (un passage `jour`)
Le passage se termine avec le code 0 quand :
- le CSV du jour existe ;
- le tableur « Appels AAAA-MM-JJ » est en place, ou bien, en simulation (`envoi_automatique` = false), le journal dit ce qui aurait été créé ;
- le nettoyage et l'affichage de la réserve sont faits.

Si la liste n'a pas pu être faite, le code est 2, avec une alerte.

## Ce qu'il remonte au responsable
- Nombre de lignes du jour, nombre de reprises, répartition par métier.
- Réserve restante : une alerte sous `seuil_alerte` (200, soit environ 2 jours).
- Panne du sourcing ou de Google, jeton Google expiré.
- Tableur créé sans mise en forme (liste Résultat, en-tête figé) : l'API « Google Sheets » est à activer dans le projet Google Cloud, par Liam.
- Le soir : les colonnes Résultat remplies par Sid, lues par l'agent `resume-sid`.
