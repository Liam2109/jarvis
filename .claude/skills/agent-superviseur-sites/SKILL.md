---
name: agent-superviseur-sites
description: Fiche de rôle du Superviseur Sites (pôle Production, FERMÉ jusqu'au « go superviseurs » de Liam) — toutes les 30 minutes sur le serveur, relit les fichiers de sites présents dans le dépôt après un git pull (jamais le gros PC) et alerte Liam sur ce qui ne va pas avant qu'une page soit montrée à un client : lien interne cassé, image ou police absente, reste de modèle ou « signe IA », page sans titre, page exemple qui n'est plus en noindex, phrase interdite, lien de paiement inconnu. Il ne réécrit JAMAIS une page. À utiliser pour vérifier, corriger ou activer superviseur-sites.py (passage, --essai, etat).
---

# Superviseur Sites — aucune page cassée ni page d'exemple non terminée montrée à un client

**Responsable :** Production. **Script :** `B2B/agents/superviseur-sites.py`. **Moteur commun :** `B2B/harness/superviseurs.py`.
**Contrat :** `B2B/harness/contrats/superviseur-sites.json`. **Tâche serveur :** `passage` toutes les 30 min.
**Agent suivi :** page-exemple (inactif : aucune tâche, donc jamais signalé).

## Ordres pas à pas (lus dans le script)
1. `M.exiger("superviseur-sites", ...)` : refuse hors de la machine active (sauf `--essai`).
2. Il ne voit que ce que **git transporte** : un dossier de site est un dossier de `B2B/sites/` ou de `B2B/pages-exemple/` qui contient un `index.html` **sur cette machine**.
   Aucun accès au gros PC, aucun réseau, aucun navigateur, aucune capture.
3. Pour chaque page HTML (au plus `pages_max` par site) :
   - **liens internes** : chaque `href`, `src`, `poster` et `url()` relatif doit viser un fichier qui existe ; un lien qui sort du dossier du site est signalé.
   - **images, polices et médias** : contrôlés seulement si le dossier contient au moins un média sur cette machine. `.gitignore` ne versionne pas les photos ni les polices :
     sur le serveur, leur absence est normale, ce n'est pas un défaut de la page.
   - **restes de modèle et « signes IA »** (B2B/CLAUDE.md § Sites, point 4) : « lorem ipsum », TODO / FIXME, « placeholder », « votre texte ici », champ de modèle non remplacé
     (`{{…}}`, `[[…]]`, `__…__`), nom du commerce non remplacé, « xxx », « à compléter ».
   - **conformité minimale** : un `<title>` non vide et un `<h1>`.
   - **noindex** : une page exemple reste en noindex (B2B/CLAUDE.md § Sites, point 6). Un site qui doit au contraire être indexé se déclare dans `sites_indexables` des réglages ;
     il est alors signalé s'il est en noindex. Rien n'est deviné à partir du nom du dossier.
   - **offre** : phrase interdite, lien de paiement absent de `B2B/docs/OFFRE-REFERENCE.json`, secret dans le fichier.
4. `B2B/pages-exemple/suivi.csv` (hors git) : lignes strictement en double retirées (**seule correction automatique de ce domaine**) ;
   deux fiches pour le même lien avec des valeurs différentes : alerte, rien n'est supprimé.
5. **Ne touche jamais** un fichier de site (HTML, CSS, JS, image) : corriger un lien ou un texte à l'aveugle casserait la page ou changerait ce que le client va lire.
   Tout part en alerte Discord et dans `B2B/a-valider/AAAA-MM-JJ-superviseur-sites.md`, puis il attend le « go » ; Liam ou Claude Code corrige la page en relisant les règles de style.
6. Discord : un résumé court par jour même quand tout va bien, plus un message dès qu'il y a du neuf ; rien entre 22:00 et 07:00 ; même souci annoncé une seule fois.

## Ce qu'il ne fait jamais
Modifier, déployer, mettre en ligne ou retirer une page ; ouvrir un navigateur ; prendre une capture ; noter une page (c'est la grille des skills de style, avec Liam) ;
toucher à un fichier suivi par git ; utiliser une IA ou un service payant ; afficher un secret.

## Ouvrir l'agent (Liam seul)
`go_superviseurs` à `true` dans la variante locale de `B2B/agents/superviseurs-config.json` (hors git), puis `superviseur-sites` ajouté à `agents_actifs`
de ses réglages locaux de machine, et `envoi_automatique` à `true` pour recevoir les messages Discord.

## Vérifier (pas de preuve = pas de fait)
- `python B2B\agents\superviseur-sites.py passage --essai` : lit tout, affiche, n'écrit rien, n'envoie rien.
- `python B2B\agents\superviseur-sites.py etat` : sites lus dans le dépôt, dernier passage, ce qui attend un « go ».
- Tests : `python tests\agents\test_superviseurs.py` (page conforme sans souci, lien cassé, média absent, reste de modèle, noindex d'une page exemple,
  site déclaré indexable mis en noindex, page sans titre, suivi dédoublonné, deux fiches pour un même lien, média non versionné qui n'est pas un défaut), puis `tests\b2b-rapide.ps1`.

## Limite connue
Sur le serveur, git ne transporte que le code des sites : il n'y a souvent qu'un dossier à relire, et le superviseur ne peut rien dire des pages qui vivent seulement sur le gros PC
ou en ligne. Il lit des fichiers, pas une page rendue : une page laide mais valide passe (c'est la notation des skills de style, avec Liam, qui s'en occupe).
