---
name: agent-appels-liam
description: Fiche de rôle de l'agent Liste d'appels de Liam (pôle Prospection) — chaque jour ouvré à 7 h 30, à partir du 17/11/2026, un tableur Google « Appels Liam AAAA-MM-JJ » de 15 lignes : relances « Je dois réfléchir » dues, puis entreprises neuves jamais données (registre commun avec Sid et les lots). À utiliser pour préparer, vérifier ou corriger la liste de Liam (appels-liam.py jour, preparer, etat, annuler).
---

# Agent Liste d'appels de Liam — relances et entreprises neuves

**Responsable :** Prospection (`.claude/skills/responsable-prospection/SKILL.md`). L'agent ne parle qu'à son responsable.
**Script :** `B2B/agents/appels-liam.py`. Il réutilise `appels-sid.py` (sélection, créneaux, format du tableur) et `registre.py` (registre commun). Note : `docs/agents/📞 Appels Liam.md`.

## Ce qu'il fait
- **Quand :** du lundi au vendredi (`jours_appel`), à 7 h 30, à partir du mardi 17/11/2026.
- **Avant la liste :** il lit la colonne Résultat des feuilles précédentes (Sid et Liam) et met le registre à jour. Ensuite seulement, il génère.
- **La liste :** 15 lignes (`par_liste`, plage 10 à 20 du contrat).
  - D'abord les relances dues : « Je dois réfléchir » donné 3 jours plus tôt, par Sid ou par Liam.
  - Puis les autres reprises de Liam : case vide (en tête de la liste suivante), Pas de réponse (après 3 jours ouvrés, 3 essais au plus), À rappeler (le jour écrit dans Note).
  - Puis des entreprises neuves, réparties sur les 5 départements (76, 27, 14, 50, 61) et mélangées entre métiers.
  - RDV pris, Non catégorique, Trop cher, Déjà un site, Pas le temps : jamais redonnée.
- **Non-doublon :** une entreprise déjà donnée à Sid, à Liam ou dans un lot d'e-mails n'est jamais redonnée (registre commun `B2B/donnees/registre-entreprises.json`, hors git).
- **Le tableur :** « Appels Liam AAAA-MM-JJ », même format que celui de Sid : Créneau (08 h à 19 h), Entreprise, Métier, Ville, Téléphone, Détail fiche, Résultat (8 valeurs), Note.
  - Il est posé à la racine du Drive du compte Google des agents, ou dans `dossier_liam_id`. Aucun dossier n'est créé.
- **Le ménage :** les feuilles « Appels Liam » de plus de 7 jours vont à la **corbeille**, seulement si elles ont déjà été lues dans le registre.

## Ce qu'il ne fait JAMAIS
- Appeler, envoyer un SMS, un e-mail ou un message à une entreprise.
- Redonner une entreprise déjà donnée à Sid ou dans un lot, ou une entreprise STOP.
- Créer un dossier Drive, supprimer définitivement un fichier, ou toucher un fichier qu'il n'a pas créé.
- Afficher un jeton, un `*.local.json` ou `.env`.

## Entrées et sorties
- **Entrées :** `appels-liam-config.json` (+ surcharge locale `envoi_automatique`), le registre commun, les feuilles « Appels » de Sid et « Appels Liam » de la veille, la réserve de `appels-sid.py`.
- **Sorties :** `B2B/docs/sid/liste-liam-AAAA-MM-JJ.csv`, la feuille Google « Appels Liam AAAA-MM-JJ », le registre, `appels-liam-etat.json`, `appels-liam-journal.log`.

## Ordres (commandes exactes, depuis la racine Jarvis)
| Ordre | Commande |
|---|---|
| Essai à blanc, sans réseau ni écriture | `python B2B\agents\appels-liam.py preparer --jour AAAA-MM-JJ --a-blanc --hors-ligne` |
| Passage du matin (tâche de 7 h 30) | `python B2B\agents\appels-liam.py jour` |
| Relances en attente, dernière liste | `python B2B\agents\appels-liam.py etat` |
| Libérer une liste qui n'a pas servi | `python B2B\agents\appels-liam.py annuler AAAA-MM-JJ` |

Sur le serveur, la commande `jour` tourne à 07:30 (`serveur-taches.json`) seulement si `appels-liam` est dans `agents_actifs` de `b2b.local.json`.

## Critère de fin (un passage `jour`)
Code 0 quand le CSV du jour existe et que la feuille Google est en place, ou bien, en simulation, que le journal dit ce qui aurait été créé. Sinon code 2, avec une alerte.

## Ce qu'il remonte au responsable
- Nombre de lignes, de relances et d'entreprises neuves du jour.
- Feuille Google illisible (relue au passage suivant), jeton Google expiré.
