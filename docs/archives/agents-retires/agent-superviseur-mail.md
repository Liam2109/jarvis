---
name: agent-superviseur-mail
description: Fiche de rôle du Superviseur Mail (rattaché à Jarvis (CEO), FERMÉ jusqu'au « go superviseurs » de Liam) — toutes les 30 minutes sur le serveur, surveille l'agent interim qui trie la boîte des alertes d'agences : a-t-il tourné, la lecture Gmail est-elle toujours en lecture seule, les fiches d'agences sont-elles intactes, une action « à rappeler » a-t-elle disparu ? Il ne lit ni la boîte ni un jeton ; il dédoublonne le suivi et alerte sans rien toucher pour tout le reste. À utiliser pour vérifier, corriger ou activer superviseur-mail.py (passage, --essai, etat).
---

# Superviseur Mail — le tri du courrier tourne, reste en lecture seule, et rien ne disparaît

**Responsable :** Jarvis (CEO). **Script :** `B2B/agents/superviseur-mail.py`. **Moteur commun :** `B2B/harness/superviseurs.py`.
**Contrat :** `B2B/harness/contrats/superviseur-mail.json`. **Tâche serveur :** `passage` toutes les 30 min.
**Agent suivi :** interim (tri des alertes d'agences reçues sur la boîte dédiée, lecture seule).

## Ordres pas à pas (lus dans le script)
1. `M.exiger("superviseur-mail", ...)` : refuse hors de la machine active (sauf `--essai`).
2. État de l'agent de tri, lu dans ses traces du jour et dans sa tâche serveur. Tant que Liam ne l'a pas mis dans `agents_actifs`, son silence est normal et n'est pas signalé.
   En erreur, silencieux ou bloqué : **relancé une fois** par jour, puis alerte s'il reste en défaut.
3. **Lecture seule du courrier** : il lit le **code** de l'agent (`B2B/agents/interim.py`) et relève les portées Google qui y sont déclarées.
   Toute portée autre que `gmail.readonly`, ou aucune portée du tout, est une alerte immédiate. Il vérifie aussi que la boîte réglée est toujours celle attendue (`boite_attendue`).
   Il n'ouvre **jamais** la boîte, ne lit **jamais** un mail, un jeton, un mot de passe ni une pièce jointe.
4. **Fiches d'agences** : `interim-suivi.csv` (hors git) — lignes strictement en double retirées, fiche sans nom signalée ;
   `interim-config.json` (versionné, données de Liam, **jamais modifié**) — fiche incomplète (champ attendu absent), agence écrite deux fois,
   adresse marquée confirmée sans la mention de Liam : alerte seulement.
5. **Actions « à rappeler »** : la colonne `prochaine_action` du suivi est mémorisée à chaque passage (empreinte dans l'état du superviseur).
   Une action présente au passage précédent et devenue vide est signalée, et **n'est jamais rétablie** : Liam dit s'il faut la remettre.
6. État du tri (`interim-etat.json`) : clés attendues (ajoutées vides si elles manquent), dates des résumés du matin et des rappels du lundi.
7. Tout ce qui n'est pas corrigeable sans risque part en alerte Discord et dans `B2B/a-valider/AAAA-MM-JJ-superviseur-mail.md`, puis il attend le « go ».
   Discord : un résumé court par jour même quand tout va bien, plus un message dès qu'il y a du neuf ; rien entre 22:00 et 07:00 ; même souci annoncé une seule fois.

## Ce qu'il ne fait jamais
Ouvrir la boîte, lire un mail, un jeton, un mot de passe ou une pièce jointe ; se connecter à un site d'agence ; modifier les réglages versionnés de l'agent de tri
(les fiches d'agences sont les données de Liam) ; rétablir tout seul une action disparue ; supprimer une fiche ; contacter une agence ; utiliser une IA ou un service payant ; afficher un secret.

## Ouvrir l'agent (Liam seul)
`go_superviseurs` à `true` dans la variante locale de `B2B/agents/superviseurs-config.json` (hors git), puis `superviseur-mail` ajouté à `agents_actifs`
de ses réglages locaux de machine, et `envoi_automatique` à `true` pour recevoir les messages Discord. Surveiller l'agent de tri ne l'ouvre pas :
le tri lui-même reste fermé jusqu'au « go interim ».

## Vérifier (pas de preuve = pas de fait)
- `python B2B\agents\superviseur-mail.py passage --essai` : lit tout, affiche, n'écrit rien, n'envoie rien.
- `python B2B\agents\superviseur-mail.py etat` : verrou, dernier passage, nombre de fiches lues, ce qui attend un « go ».
- Tests : `python tests\agents\test_superviseurs.py` (tout en ordre, portée en écriture, boîte changée, fiche en double retirée, fiche incomplète,
  agence écrite deux fois, adresse confirmée sans Liam, action à rappeler disparue, script de tri absent), puis `tests\b2b-rapide.ps1`.

## Limite connue
Il contrôle la lecture seule à partir du code, pas à partir du jeton lui-même (qu'il n'a pas le droit de lire) : un jeton accordé plus large que le code ne se verrait pas ici.
La disparition d'une action se mesure d'un passage au suivant : une action ajoutée puis retirée entre deux passages de 30 minutes passerait inaperçue.
