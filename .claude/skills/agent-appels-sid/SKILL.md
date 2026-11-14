---
name: agent-appels-sid
description: Fiche de rôle de l'agent Liste d'appels de Sid (pôle Prospection) — chaque jour ouvré à 8 h, un seul tableur Google « Appels AAAA-MM-JJ » de 100 entreprises triées par créneau, dans le dossier Drive de Sid. À utiliser pour préparer, vérifier ou corriger la liste d'appels (appels-sid.py jour, preparer, sourcer, etat, annuler).
---

# Agent Liste d'appels de Sid — le tableur du jour

**Responsable :** Prospection (`.claude/skills/responsable-prospection/SKILL.md`). L'agent ne parle qu'à son responsable.
**Script :** `B2B/agents/appels-sid.py`, propre à cet agent. Il réutilise les fonctions de `prospection.py` (exclusions, zone) sans en lancer les commandes. Note : `docs/agents/📞 Appels Sid.md`.

## Ce qu'il fait
- **Quand :** du lundi au vendredi (`jours_appel`), à 8 h, il prépare **une** liste de 100 entreprises. Il en met au moins 100 et au plus 130.
- **Quelles entreprises :**
  - environ 20 métiers locaux, en Normandie ;
  - un téléphone valide, et aucun site trouvé ;
  - une entreprise appelée est oubliée 1 an (`jours_sans_rappel` 365).
- **Reprises (jours ouvrés, lundi au vendredi) :** le Détail fiche indique « Reprise de la liste du … », avec la note de Sid.
  - Pas de réponse : revient 2 jours ouvrés plus tard, sur un autre créneau, 3 tentatives en tout ; ensuite, oubliée 1 an.
  - À rappeler : revient le jour ouvré suivant.
  - Je dois réfléchir, Pas le temps : reviennent une seule fois, 7 jours plus tard.
  - RDV pris : sort de la liste, signalé dans le résumé du soir.
  - Non catégorique, Trop cher, Déjà un site : oubliée 1 an.
  - Case vide : revient dans la liste suivante.
- **Le tableur :** il crée **un seul** tableur Google « Appels AAAA-MM-JJ », posé directement dans le dossier Drive de Sid (`dossier_sid_id`), sans sous-dossier.
  - Les lignes sont triées par créneau, de 8 h à 19 h.
  - Les colonnes sont toujours, dans cet ordre : Créneau, Entreprise, Métier, Ville, Téléphone, Détail fiche, Résultat, Note.
  - Résultat est une liste de 8 valeurs, dans cet ordre : Pas de réponse, À rappeler, RDV pris, Non catégorique, Je dois réfléchir, Trop cher, Déjà un site, Pas le temps.
  - Les colonnes sont larges, l'en-tête est figé, aucune cellule n'est fusionnée.
- **Le ménage :** il met à la **corbeille** (jamais une suppression définitive) les tableurs de plus de 7 jours, et les anciens sous-dossiers datés.
- **La réserve :** il garnit sa réserve de numéros avec la commande `sourcer` (OpenStreetMap et SIRENE, gratuits).

## Ce qu'il ne fait JAMAIS
- Appeler, envoyer un SMS, un e-mail ou un message à une entreprise ou à Sid.
- Écrire un fichier `liste-appels-*.md` : c'est arrêté depuis le 14/11/2026, et les anciens restent seulement en lecture.
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
  - le tableur de la veille, pour la colonne Résultat.
- **Sorties :**
  - `B2B/docs/sid/liste-sid-AAAA-MM-JJ.csv` ;
  - le tableur Google « Appels AAAA-MM-JJ » ;
  - `appels-sid-etat.json`, `appels-sid-historique.json`, `appels-sid-journal.log` ;
  - une alerte Discord si la réserve est basse ou si Google tombe en panne.

## Ordres (commandes exactes, depuis la racine Jarvis)
| Ordre | Commande |
|---|---|
| Essai à blanc : le tableur du jour en texte, sans réseau ni écriture | `python B2B\agents\appels-sid.py preparer --jour AAAA-MM-JJ --a-blanc --hors-ligne` |
| Passage du matin (tâche de 8 h) | `python B2B\agents\appels-sid.py jour` (essai : `--a-blanc`) |
| La liste seule, en CSV local | `python B2B\agents\appels-sid.py preparer --jour AAAA-MM-JJ` |
| Garnir la réserve | `python B2B\agents\appels-sid.py sourcer` (essai : `--a-blanc` ; un département : `--dept 27` ; sans réseau : `--simulation`) |
| Réserve, dernière liste, état de Google | `python B2B\agents\appels-sid.py etat` |
| Libérer une liste qui n'a pas servi | `python B2B\agents\appels-sid.py annuler AAAA-MM-JJ` (essai : `--a-blanc`) |
| Autorisation Google, **par Liam seulement** | `python B2B\agents\appels-sid.py google-autoriser` |

Sur le serveur, la commande `jour` tourne à 08:00 (`serveur-taches.json`). Un samedi ou un dimanche, elle note « jour hors planning » et ne fait rien.

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
- Le soir : les colonnes Résultat remplies par Sid, lues par l'agent `resume-sid`.
