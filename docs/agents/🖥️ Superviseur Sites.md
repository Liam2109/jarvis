---
agent: superviseur-sites
aliases: [🖥️ Superviseur Sites]
name: superviseur-sites
role: "Toutes les 30 min : relit les fichiers de sites presents dans le depot (liens casses, images absentes, restes de modele, noindex) et alerte Liam. Ne reecrit jamais une page."
machine: "serveur"
planification: "toutes les 30 min, plage tous les jours 07:00-22:00"
sorties: "B2B/pages-exemple/suivi.csv (ligne strictement en double retiree), B2B/agents/superviseur-sites-etat.json, B2B/agents/superviseur-sites-journal.log, B2B/a-valider/AAAA-MM-JJ-superviseur-sites.md"
responsable: Production
statut: arrêté
horaire: "toutes les 30 min, plage tous les jours 07:00-22:00"
tags: [agent-b2b]
---
<!-- GENERE:DEBUT (régénéré par python B2B\harness\generer-fiches.py : ne pas modifier) -->
# 🖥️ Superviseur Sites

**Agent :** `superviseur-sites` · **Statut :** arrêté · **Responsable :** Production (pôle) · **Machine :** serveur
**Horaire :** toutes les 30 min, plage tous les jours 07:00-22:00
**Script :** `B2B/agents/superviseur-sites.py` · **Contrat :** `B2B/harness/contrats/superviseur-sites.json`

## Rôle et limites
### Mission
Toutes les 30 min : relit les fichiers de sites presents dans le depot (liens casses, images absentes, restes de modele, noindex) et alerte Liam. Ne reecrit jamais une page.

### Ce qu'il fait étape par étape
1. `M.exiger("superviseur-sites", ...)` : refuse hors de la machine active (sauf `--essai`).
2. Il ne voit que ce que **git transporte** : un dossier de site est un dossier de `B2B/sites/` ou de `B2B/pages-exemple/` qui contient un `index.html` **sur cette machine**.
   Aucun accès au gros PC, aucun réseau, aucun navigateur, aucune capture.
3. Pour chaque page HTML (au plus `pages_max` par site) :
   - **liens internes** : chaque `href`, `src`, `poster` et `url()` relatif doit viser un fichier qui existe ; un lien qui sort du dossier du site est signalé.
   - **images, polices et médias** : contrôlés seulement si le dossier contient au moins un média sur cette machine. `.gitignore` ne versionne pas les photos ni les polices :
     sur le serveur, leur absence est normale, ce n'est pas un défaut de la page.
   - **restes de modèle et « signes IA »** (B2B/CLAUDE.md § Sites, point 4) : « lorem ipsum », TODO / FIXME, « placeholder », « votre texte ici », champ de modèle non remplacé
     (`{{…}}`, `…`, `__…__`), nom du commerce non remplacé, « xxx », « à compléter ».
   - **conformité minimale** : un `<title>` non vide et un `<h1>`.
   - **noindex** : une page exemple reste en noindex (B2B/CLAUDE.md § Sites, point 6). Un site qui doit au contraire être indexé se déclare dans `sites_indexables` des réglages ;
     il est alors signalé s'il est en noindex. Rien n'est deviné à partir du nom du dossier.
   - **offre** : phrase interdite, lien de paiement absent de `B2B/docs/OFFRE-REFERENCE.json`, secret dans le fichier.
4. `B2B/pages-exemple/suivi.csv` (hors git) : lignes strictement en double retirées (**seule correction automatique de ce domaine**) ;
   deux fiches pour le même lien avec des valeurs différentes : alerte, rien n'est supprimé.
5. **Ne touche jamais** un fichier de site (HTML, CSS, JS, image) : corriger un lien ou un texte à l'aveugle casserait la page ou changerait ce que le client va lire.
   Tout part en alerte Discord et dans `B2B/a-valider/AAAA-MM-JJ-superviseur-sites.md`, puis il attend le « go » ; Liam ou Claude Code corrige la page en relisant les règles de style.
6. Discord : un résumé court par jour même quand tout va bien, plus un message dès qu'il y a du neuf ; rien entre 22:00 et 07:00 ; même souci annoncé une seule fois.

### Ce qu'il n'a pas le droit de faire
- modifier un fichier de site (HTML, CSS, JS, image) : signale seulement
- deployer, mettre en ligne ou retirer une page
- supprimer une donnee, une ligne, une fiche ou un fichier
- ecraser une valeur deja ecrite par un agent ou par Liam
- toucher a un montant, un paiement, un prix ou un devis
- toucher au code, aux skills, aux docs ou a un fichier suivi par git
- ecrire dans les donnees d'un autre domaine que le sien
- corriger quoi que ce soit avant le « go superviseurs » de Liam
- relancer plus d'une fois par jour le meme agent
- contacter un prospect, un client, Sid ou qui que ce soit d'autre que Liam
- utiliser une IA ou un service payant
- afficher un secret (jeton, cle, adresse iCal)
- envoyer au client, encaisser, publier ou signer
- Engager Liam (envoyer au client, encaisser, publier, signer) : `peut_engager: false`, tout passe par `B2B/a-valider/`.

## Entrées et sorties
**Lit :**
- B2B/sites/*/ et B2B/pages-exemple/*/ presents dans le depot (HTML, CSS, JS)
- B2B/pages-exemple/suivi.csv (si present)
- B2B/docs/OFFRE-REFERENCE.json (phrases interdites, liens de paiement)
- B2B/logs/agents (traces du jour)
- B2B/agents/serveur-taches.json

**Écrit :**
- B2B/pages-exemple/suivi.csv (ligne strictement en double retiree)
- B2B/agents/superviseur-sites-etat.json
- B2B/agents/superviseur-sites-journal.log
- B2B/a-valider/AAAA-MM-JJ-superviseur-sites.md

**Discord :** alertes · **Plafond :** 6 messages par jour · **Envoi au client :** non

## Horaire et état
- **Horaire :** toutes les 30 min, plage tous les jours 07:00-22:00
- **Tâche serveur :** entrée dans `B2B/agents/serveur-taches.json`, active à partir du 2026-11-21 ; tourne seulement si l'agent est dans `agents_actifs` (choix de Liam)
- **Contrat :** valide (`python B2B\harness\valider.py`)
- **Garde branchée :** oui
- Bloque : kill-switch `B2B\STOP`, lien Stripe non autorisé, phrase interdite (OFFRE-REFERENCE.json), secret dans le texte.
- Avertit : machine non active, envoi_automatique = false (simulation), hors horaires du contrat (07:00-22:00), plafond de 6 messages par jour.
- **Tests :** `tests/agents/test_superviseurs.py`
- **Alerte si silence :** aucune

<!-- DYNAMIQUE:DEBUT -->
**Derniers résultats de test (cette machine) :**
- `tests/agents/test_superviseurs.py` : pas encore lancé par `generer-fiches.py --tests`

**Dernière trace :** aucune · **Dernière erreur :** aucune · **Dans agents_actifs (cette machine) :** non (Liam l'ajoute s'il veut le planifier)

### Historique (5 dernières traces, sans données client)
- aucune trace sur cette machine
<!-- DYNAMIQUE:FIN -->

## Skill et règles
- `.claude/skills/agent-superviseur-sites/SKILL.md` (copie : `docs/agents/skills/agent-superviseur-sites.md`)
- Pas de preuve = pas de fait : « il a tourné » = une trace du jour `ok: true` ci-dessus ; « c'est corrigé » = ses tests puis `tests\b2b-rapide.ps1` en vert.
<!-- GENERE:FIN -->

## Liens et décisions

_Zone conservée à chaque régénération : liens vers docs\decisions et docs clés seulement._

Liens : aucun pour l'instant.

## Notes de Liam

_Zone libre, conservée telle quelle à chaque régénération._
