---
name: agent-alerte-candidatures
description: Fiche de rôle de l'agent Alerte candidatures (rattaché à Jarvis CEO, FERMÉ jusqu'au « go alerte » de Liam) — toutes les 5 minutes, lit la feuille de réponses du formulaire « Postuler comme call caller – LM Multi-Services » et alerte Liam sur Discord pour chaque nouveau candidat (« À rappeler dans l'heure », brouillon de réponse que Liam envoie lui-même), une seule relance si la colonne Contacté est vide au bout de 2 h, une ligne dans le résumé du soir. À utiliser pour vérifier, corriger ou activer alerte-candidatures.py (verifier, etat, google-autoriser).
---

# Agent Alerte candidatures — un candidat, une alerte, un rappel dans l'heure

**Rattaché à :** Jarvis (CEO). **Script :** `B2B/agents/alerte-candidatures.py`. **Contrat :** `B2B/harness/contrats/alerte-candidatures.json`.
**Tâche serveur :** `verifier` toutes les 5 minutes (`B2B/agents/serveur-taches.json`), **jamais** dans `agents_actifs` avant le « go alerte » écrit par Liam.

## Pourquoi
Liam recrute des call callers à la commission (15 % des ventes qu'ils amènent, jamais de closers). Un candidat qui n'est pas rappelé vite part ailleurs : l'alerte pousse Liam à rappeler dans l'heure. Les candidatures par message privé ne sont pas surveillées (hors périmètre).

## Ordres pas à pas (lus dans le script)
1. `M.exiger("alerte-candidatures", ...)` : refuse de tourner hors de la machine active (sauf `--a-blanc` et `etat`).
2. Réglages `alerte-candidatures-config.json` + fichier local (hors git) : `go_alerte` (verrou, false), `envoi_automatique` (false = simulation), `feuille_id`, `onglet` (vide = premier), `compte_google`, `relance_minutes` (120), `colonne_contacte` (« Contacté »).
3. **Verrou** : `go_alerte` faux -> « rien lu, rien envoyé », code 0. Sans `feuille_id` : message avec la marche à suivre, code 0.
4. Lit toutes les valeurs de l'onglet (API Sheets, jeton `google-candidatures-token.json`, portée `spreadsheets` ; la portée `drive.file` d'appels-sid ne voit pas une feuille créée par Google Forms).
5. Reconnaît les colonnes au texte des questions (horodateur, nom/prénom, téléphone, e-mail, ville, disponibilités, message). Colonne non reconnue = champ omis, **jamais deviné**.
6. Colonne « Contacté » absente : crée **seulement l'en-tête** (ligne 1, première colonne libre). C'est la seule écriture dans la feuille.
7. Premier passage (état vide) : lignes existantes mémorisées **sans alerte**.
8. Chaque ligne inconnue (empreinte horodateur + e-mail + téléphone, aucune donnée du candidat dans l'état) : une alerte Discord « À rappeler dans l'heure » + champs présents + brouillon de réponse. Jamais deux fois la même ligne.
9. Ligne alertée, « Contacté » vide, 2 h écoulées : **une seule** relance.
10. État `alerte-candidatures-etat.json` (60 jours gardés), journal sans donnée du candidat, trace du harness à chaque `verifier` réel.

## Le brouillon de réponse (texte fixe, dans le code)
Court, oral, sans « Bonjour <prénom> », sans promesse de revenu : 15 % de commission sur les ventes qu'il amène, uniquement à la commission, rendez-vous de 15 minutes en visio avec Liam. **Rien n'est envoyé au candidat** : Liam copie, adapte et envoie lui-même.

## Résumé du soir
`resume-sid.py` (19:30) ajoute « Candidatures call callers du jour : N, dont M non contactée(s). » en lisant l'état de cet agent ; aucune ligne tant que l'agent n'a jamais tourné.

## Ce qu'il ne fait jamais
- Envoyer quoi que ce soit à un candidat ou à un prospect (message, e-mail, SMS).
- Inventer une information sur un candidat ; écrire dans la feuille autre chose que l'en-tête « Contacté ».
- Promettre un revenu ; tourner avant le « go alerte » ; afficher un jeton.

## Activation (Liam seulement, après « go alerte »)
1. Formulaire Google > onglet **Réponses** > **Lier à Sheets** (feuille gratuite) ; copier l'identifiant de la feuille (entre `/d/` et `/edit`).
2. `python B2B\agents\alerte-candidatures.py google-autoriser` (navigateur, une fois, compte qui possède la feuille).
3. Fichier local de réglages : `go_alerte: true`, `feuille_id`, puis `envoi_automatique: true` après un passage en simulation.
4. Ajouter `alerte-candidatures` à `agents_actifs` du serveur.

## Vérifier qu'il a bien tourné (pas de preuve = pas de fait)
- `python B2B\agents\alerte-candidatures.py etat` : verrou, feuille, candidatures du jour et non contactées.
- `python B2B\agents\alerte-candidatures.py verifier --a-blanc` : ce qui serait alerté, rien écrit.
- Tests : `python tests\agents\test_alerte_candidatures.py` puis `tests\b2b-rapide.ps1` en vert.
