---
agent: appels-liam
aliases: [📞 Appels Liam]
name: appels-liam
role: "Créer chaque jour ouvré à 07:30 le tableur « Appels Liam AAAA-MM-JJ » : relances « Je dois réfléchir » dues, puis entreprises neuves jamais données (registre commun)."
machine: "serveur"
planification: "chaque jour à 07:30, plage lundi-vendredi 07:00-19:00"
sorties: "Google Drive : Appels Liam AAAA-MM-JJ, B2B/donnees/registre-entreprises.json, B2B/agents/appels-liam-etat.json, B2B/agents/appels-liam-journal.log"
responsable: Prospection
statut: actif
mode: simulation
horaire: "chaque jour à 07:30, plage lundi-vendredi 07:00-19:00"
tags: [agent-b2b]
---
<!-- GENERE:DEBUT (régénéré par python B2B\harness\generer-fiches.py : ne pas modifier) -->
# 📞 Appels Liam

**Agent :** `appels-liam` · **Statut :** actif (simulation : envoi_automatique = false) · **Responsable :** Prospection (pôle) · **Machine :** serveur
**Horaire :** chaque jour à 07:30, plage lundi-vendredi 07:00-19:00
**Script :** `B2B/agents/appels-liam.py` · **Contrat :** `B2B/harness/contrats/appels-liam.json`

## Mission
Créer chaque jour ouvré à 07:30 le tableur « Appels Liam AAAA-MM-JJ » : relances « Je dois réfléchir » dues, puis entreprises neuves jamais données (registre commun).

## Ce qu'il fait étape par étape
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

## Entrées et sorties
**Lit :**
- B2B/donnees/registre-entreprises.json
- B2B/agents/appels-liam-config.json
- Google Drive : Appels AAAA-MM-JJ et Appels Liam AAAA-MM-JJ (colonne Résultat)

**Écrit :**
- Google Drive : Appels Liam AAAA-MM-JJ
- B2B/donnees/registre-entreprises.json
- B2B/agents/appels-liam-etat.json
- B2B/agents/appels-liam-journal.log

**Discord :** alertes · **Plafond :** 5 messages par jour · **Envoi au client :** non

## Ce qu'il n'a pas le droit de faire
- envoyer au client sans accord de Liam
- encaisser ou rembourser
- publier
- signer ou promettre un résultat
- afficher un secret (jeton, clé, adresse iCal)
- appeler un prospect
- remettre un STOP dans la liste
- redonner une entreprise déjà donnée à Sid ou dans un lot
- supprimer définitivement un fichier Drive
- créer un dossier Drive
- Engager Liam (envoyer au client, encaisser, publier, signer) : `peut_engager: false`, tout passe par `B2B/a-valider/`.

## Harness
- **Contrat :** valide (`python B2B\harness\valider.py`)
- **Garde branchée :** oui
- Bloque : kill-switch `B2B\STOP`, lien Stripe non autorisé, phrase interdite (OFFRE-REFERENCE.json), secret dans le texte.
- Avertit : machine non active, envoi_automatique = false (simulation), hors horaires du contrat (07:00-19:00), plafond de 5 messages par jour.
- **Tests :** `tests/agents/test_appels_registre.py`
- **Alerte si silence :** après 07:45 (surveillant)

<!-- DYNAMIQUE:DEBUT -->
**Derniers résultats de test (cette machine) :**
- `tests/agents/test_appels_registre.py` : pas encore lancé par `generer-fiches.py --tests`

**Dernière trace :** aucune

### Historique (5 dernières traces, sans données client)
- aucune trace sur cette machine
<!-- DYNAMIQUE:FIN -->

## Skill
- `.claude/skills/agent-appels-liam/SKILL.md` (copie : `docs/agents/skills/agent-appels-liam.md`)
<!-- GENERE:FIN -->

## Liens et décisions

_Zone conservée à chaque régénération : liens vers docs\decisions et docs clés seulement._

Liste d'appels de Liam (à partir du 17/11/2026) : relances « Je dois réfléchir » puis entreprises neuves, registre commun avec Sid et les lots d'e-mails (`B2B/agents/registre.py`).
Détail : `.claude/skills/agent-appels-liam/SKILL.md` · scripts : script d'appel (version Liam)
Liens : [[docs/decisions/📌 Offre 595 + 49|📌 Offre 595 + 49]]

## Notes de Liam

_Zone libre, conservée telle quelle à chaque régénération._
