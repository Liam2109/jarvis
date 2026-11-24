---
agent: appels-sid
aliases: [📞 Appels Sid]
name: appels-sid
role: Préparer chaque matin la liste d'appels de Sid (au moins 100 entreprises avec téléphone)
machine: serveur DESKTOP-HLQSTAU (si listé dans agents_actifs)
planification: 07:30 (serveur-taches.json, commande « jour ») ; jours d'appel du lundi au vendredi
depend_de: agent-prospection
responsable: prospection
sorties: docs/sid/liste-sid-AAAA-MM-JJ.csv, tableur Google « Appels AAAA-MM-JJ » dans le dossier de Sid
statut: actif
mode: simulation
horaire: "chaque jour à 07:30, plage lundi-vendredi 07:00-19:00"
tags: [agent-b2b]
---
<!-- GENERE:DEBUT (régénéré par python B2B\harness\generer-fiches.py : ne pas modifier) -->
# 📞 Appels Sid

**Agent :** `appels-sid` · **Statut :** actif (simulation : envoi_automatique = false) · **Responsable :** Prospection (pôle) · **Machine :** serveur
**Horaire :** chaque jour à 07:30, plage lundi-vendredi 07:00-19:00
**Script :** `B2B/agents/appels-sid.py` · **Contrat :** `B2B/harness/contrats/appels-sid.json`

## Rôle et limites
### Mission
Créer chaque jour ouvré à 07:30 le tableur « Appels Sid AAAA-MM-JJ » de Sid, trié par créneau de 08:00 à 19:00.

### Ce qu'il fait étape par étape
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
- **Le tableur :** il crée **un seul** tableur Google « Appels Sid AAAA-MM-JJ », posé directement dans le dossier Drive « LM Multi-Services - Dossier Sid » (`dossier_sid_id`), sans sous-dossier ; jamais à la racine du Drive ni dans un dossier créé (`dossier_sid_id` vide = rien créé, erreur). Après création, il vérifie que la feuille est bien dans ce dossier et donne son nom et son nombre de lignes. Il ne touche jamais au document « Script d'appel Sid » du même dossier. (Nom « Appels AAAA-MM-JJ » jusqu'au 16/11/2026, encore reconnu pour le ménage.)
  - Les lignes sont triées par créneau, de 8 h à 19 h.
  - Les colonnes sont toujours, dans cet ordre : Créneau, Entreprise, Métier, Ville, Téléphone, Détail fiche, Résultat, Note.
  - Résultat est une liste de 8 valeurs, dans cet ordre : Pas de réponse, À rappeler, RDV pris, Non catégorique, Je dois réfléchir, Trop cher, Déjà un site, Pas le temps.
  - Les colonnes sont larges, l'en-tête est figé, aucune cellule n'est fusionnée.
- **Le ménage :** il met à la **corbeille** (jamais une suppression définitive) les tableurs « Appels Sid AAAA-MM-JJ » de plus de 7 jours, seulement s'ils ont déjà été lus dans le registre. Il ne crée aucun dossier et ne touche à aucun autre fichier.
- **Le stock :** sous 3 jours de listes (Sid et Liam) d'entreprises neuves, une trace en erreur que le surveillant signale ; silence sinon.
- **La réserve :** il garnit sa réserve de numéros avec la commande `sourcer` (OpenStreetMap et SIRENE, gratuits).

### Ce qu'il n'a pas le droit de faire
- envoyer au client sans accord de Liam
- encaisser ou rembourser
- publier
- signer ou promettre un résultat
- afficher un secret (jeton, clé, adresse iCal)
- appeler un prospect
- remettre un STOP dans la liste
- redonner une entreprise déjà donnée à Liam ou dans un lot
- supprimer définitivement un fichier Drive
- créer un dossier Drive
- Engager Liam (envoyer au client, encaisser, publier, signer) : `peut_engager: false`, tout passe par `B2B/a-valider/`.

## Entrées et sorties
**Lit :**
- B2B/prospects_maps.csv
- B2B/agents/appels-sid-historique.json
- B2B/agents/appels-sid-config.json
- API Sirene INSEE (lecture seule, clé gratuite hors dépôt) : entreprises créées depuis moins de 3 mois
- B2B/donnees/registre-entreprises.json
- Google Drive : 3 dernières feuilles Appels Sid AAAA-MM-JJ (relecture du Résultat, lecture seule)

**Écrit :**
- Google Drive : Appels Sid AAAA-MM-JJ
- B2B/donnees/registre-entreprises.json
- B2B/agents/appels-sid-etat.json
- B2B/agents/appels-sid-journal.log

**Discord :** alertes · **Plafond :** 5 messages par jour · **Envoi au client :** non

## Horaire et état
- **Horaire :** chaque jour à 07:30, plage lundi-vendredi 07:00-19:00
- **Tâche serveur :** entrée dans `B2B/agents/serveur-taches.json` ; tourne seulement si l'agent est dans `agents_actifs` (choix de Liam)
- **Contrat :** valide (`python B2B\harness\valider.py`)
- **Garde branchée :** oui
- Bloque : kill-switch `B2B\STOP`, lien Stripe non autorisé, phrase interdite (OFFRE-REFERENCE.json), secret dans le texte.
- Avertit : machine non active, envoi_automatique = false (simulation), hors horaires du contrat (07:00-19:00), plafond de 5 messages par jour.
- **Tests :** `B2B/agents/test_appels_sid.py`, `B2B/agents/test_nouvelles_entreprises.py`, `tests/agents/test_appels_sid.py`, `tests/agents/test_appels_registre.py`
- **Alerte si silence :** après 07:45 (surveillant)

<!-- DYNAMIQUE:DEBUT -->
**Derniers résultats de test (cette machine) :**
- `B2B/agents/test_appels_sid.py` : pas encore lancé par `generer-fiches.py --tests`
- `B2B/agents/test_nouvelles_entreprises.py` : pas encore lancé par `generer-fiches.py --tests`
- `tests/agents/test_appels_sid.py` : pas encore lancé par `generer-fiches.py --tests`
- `tests/agents/test_appels_registre.py` : pas encore lancé par `generer-fiches.py --tests`

**Dernière trace :** 2026-11-24 17:44 ERREUR · **Dernière erreur :** 2026-11-24 17:44 stock (stock bas : 331 entreprise(s) neuve(s), moins de 3 jours de listes (seuil 345)) · **Dans agents_actifs (cette machine) :** oui

### Historique (5 dernières traces, sans données client)
- 2026-11-24 17:44 | stock | ERREUR (stock bas : 331 entreprise(s) neuve(s), moins de 3 jours de listes (seuil 345)) | 0.0 s
- 2026-11-23 12:14 | stock | ERREUR (stock bas : 331 entreprise(s) neuve(s), moins de 3 jours de listes (seuil 345)) | 0.0 s
- 2026-11-22 07:30 | jour | ok | 0.35 s
- 2026-11-21 07:30 | jour | ok | 0.29 s
- 2026-11-20 07:39 | jour | ok | 565.49 s
<!-- DYNAMIQUE:FIN -->

## Skill et règles
- `.claude/skills/agent-appels-sid/SKILL.md` (copie : `docs/agents/skills/agent-appels-sid.md`)
- Pas de preuve = pas de fait : « il a tourné » = une trace du jour `ok: true` ci-dessus ; « c'est corrigé » = ses tests puis `tests\b2b-rapide.ps1` en vert.
<!-- GENERE:FIN -->

## Liens et décisions

_Zone conservée à chaque régénération : liens vers docs\decisions et docs clés seulement._

Tous les appels vont à Sid. La colonne Résultat (Pas de réponse, À rappeler, RDV pris, Non catégorique, Je dois réfléchir, Trop cher, Déjà un site, Pas le temps) est lue le soir par agent-resume-sid.
Détail : `B2B/agents/appels-sid.md` · scripts : script d'appel
Responsable : Prospection (`.claude/skills/responsable-prospection/SKILL.md`) · fiche : `.claude/skills/agent-appels-sid/SKILL.md`
Liens : [[docs/decisions/📌 Offre 500 + 29|📌 Offre 500 + 29]]

## Notes de Liam

_Zone libre, conservée telle quelle à chaque régénération._
