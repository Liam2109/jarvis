---
agent: superviseur-videos
aliases: [🎥 Superviseur Vidéos]
name: superviseur-videos
role: "Toutes les 30 min : les sept agents de la chaine video ont-ils tourne, dans l'ordre, et leurs donnees se contredisent-elles ? Corrige le sans risque, alerte et attend « go » pour tout ce qui touche a la publication."
machine: "serveur"
planification: "toutes les 30 min, plage tous les jours 07:00-22:00"
sorties: "Videos/journal-videos.csv (ligne strictement en double retiree), Videos/scripts/sujets.json (sujet strictement en double retire), B2B/agents/superviseur-videos-etat.json, B2B/agents/superviseur-videos-journal.log, B2B/a-valider/AAAA-MM-JJ-superviseur-videos.md"
responsable: Jarvis (CEO)
statut: arrêté
horaire: "toutes les 30 min, plage tous les jours 07:00-22:00"
tags: [agent-b2b]
---
<!-- GENERE:DEBUT (régénéré par python B2B\harness\generer-fiches.py : ne pas modifier) -->
# 🎥 Superviseur Vidéos

**Agent :** `superviseur-videos` · **Statut :** arrêté · **Responsable :** Jarvis (CEO) · **Machine :** serveur
**Horaire :** toutes les 30 min, plage tous les jours 07:00-22:00
**Script :** `B2B/agents/superviseur-videos.py` · **Contrat :** `B2B/harness/contrats/superviseur-videos.json`

## Rôle et limites
### Mission
Toutes les 30 min : les sept agents de la chaine video ont-ils tourne, dans l'ordre, et leurs donnees se contredisent-elles ? Corrige le sans risque, alerte et attend « go » pour tout ce qui touche a la publication.

### Ce qu'il fait étape par étape
1. `M.exiger("superviseur-videos", ...)` : refuse hors de la machine active (sauf `--essai`).
2. Pour chaque agent suivi : son état est lu dans ses **traces** du jour (`B2B/logs/agents/<agent>/`) et dans sa tâche (`serveur-taches.json`).
   Un agent absent de `agents_actifs`, désactivé, pas encore actif ou hors de ses jours n'est jamais signalé : il n'a pas de tâche sur cette machine.
   C'est le cas normal de `videos-publication` (verrouillé jusqu'au « go publier ») et de `videos-monteur` (appelé par la création, aucune tâche à lui).
   « erreur » = dernier passage du jour `ok: false` ; « silence » = heure fixe + délai de grâce passés sans passage ; « bloque » = agent cyclique muet depuis plus de 3 cycles + grâce.
3. Agent en erreur, silencieux ou bloqué : **relancé une fois**, avec la commande de sa tâche serveur, puis noté au journal. Au passage suivant, s'il est toujours en défaut : alerte, plus de relance (jamais deux par jour).
4. Contrôles de cohérence : `Videos/videos-publication-etat.json` (clés attendues, dates des jours de publication, plafond par jour et par ligne, deux fois la même vidéo au même passage),
   `Videos/publication.verrou` (verrou oublié depuis plus de 3 h), les légendes de `Videos/a-valider/*.txt` (mention « Contenu généré par IA. », phrases interdites, liens de paiement, secrets),
   `Videos/journal-videos.csv` (lignes en double), `Videos/scripts/sujets.json` (sujets en double), et **l'ordre de la chaîne du jour** (veille → scripts → marketing → création : un maillon qui a tourné sans le précédent).
5. **Corrige seul** (rien ne peut être perdu) : relance d'un agent, ligne **strictement identique** retirée de `journal-videos.csv`, sujet **strictement en double** retiré de `sujets.json` (la première occurrence et l'ordre restent).
6. **Ne touche jamais** : `videos-publication-etat.json` (compléter une clé ou retirer une ligne de publication pourrait faire **republier** une vidéo : c'est public et ça engage Liam),
   le verrou `publication.verrou` (le retirer autoriserait deux publications en même temps), le contenu d'une vidéo, d'une légende ou d'un script (texte destiné au public),
   un fichier illisible, un plafond dépassé, une date illogique, une chaîne dans le désordre. Dans tous ces cas : une alerte Discord et une ligne dans `B2B/a-valider/AAAA-MM-JJ-superviseur-videos.md`, puis il attend le « go ».
7. Discord : un résumé court par jour même quand tout va bien (à partir de `heure_resume`), plus un message dès qu'il corrige ou découvre quelque chose de neuf. Jamais la nuit (plage 07:00-22:00) : une alerte de 3 h attend le passage du matin. Même souci = annoncé une seule fois.

### Ce qu'il n'a pas le droit de faire
- ecrire dans Videos/videos-publication-etat.json : signale seulement (une video deja publiee pourrait repartir)
- retirer le verrou Videos/publication.verrou (deux publications en meme temps)
- publier, depublier ou toucher a une video, une legende ou un script : texte destine au public
- supprimer une donnee, une ligne, une fiche ou un fichier
- ecraser une valeur deja ecrite par un agent ou par Liam
- toucher a un montant, un paiement, un prix ou un devis
- toucher au code, aux skills, aux docs ou a un fichier suivi par git
- ecrire dans les donnees d'un autre domaine que le sien
- corriger quoi que ce soit avant le « go superviseurs » commun ET le « go superviseur-videos » propre a ce domaine
- relancer plus d'une fois par jour le meme agent
- contacter un prospect, un client, Sid ou qui que ce soit d'autre que Liam
- utiliser une IA ou un service payant
- afficher un secret (jeton, cle, adresse iCal)
- envoyer au client, encaisser, publier ou signer
- Engager Liam (envoyer au client, encaisser, publier, signer) : `peut_engager: false`, tout passe par `B2B/a-valider/`.

## Entrées et sorties
**Lit :**
- B2B/harness/contrats (horaires attendus)
- B2B/logs/agents (traces du jour des sept agents video)
- B2B/agents/serveur-taches.json
- Videos/videos-publication-etat.json (si present)
- Videos/publication.verrou (si present)
- Videos/a-valider/*.txt (legendes qui attendent Liam)
- Videos/journal-videos.csv (si present)
- Videos/scripts/sujets.json (si present)
- B2B/docs/OFFRE-REFERENCE.json (phrases interdites, liens de paiement)

**Écrit :**
- Videos/journal-videos.csv (ligne strictement en double retiree)
- Videos/scripts/sujets.json (sujet strictement en double retire)
- B2B/agents/superviseur-videos-etat.json
- B2B/agents/superviseur-videos-journal.log
- B2B/a-valider/AAAA-MM-JJ-superviseur-videos.md

**Discord :** alertes · **Plafond :** 6 messages par jour · **Envoi au client :** non

## Horaire et état
- **Horaire :** toutes les 30 min, plage tous les jours 07:00-22:00
- **Tâche serveur :** entrée dans `B2B/agents/serveur-taches.json`, active à partir du 2026-11-22 ; tourne seulement si l'agent est dans `agents_actifs` (choix de Liam)
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
- `.claude/skills/agent-superviseur-videos/SKILL.md` (copie : `docs/archives/agents-retires/agent-superviseur-videos.md`)
- Pas de preuve = pas de fait : « il a tourné » = une trace du jour `ok: true` ci-dessus ; « c'est corrigé » = ses tests puis `tests\b2b-rapide.ps1` en vert.
<!-- GENERE:FIN -->

## Liens et décisions

_Zone conservée à chaque régénération : liens vers docs\decisions et docs clés seulement._

Rattaché à : [[docs/agents/🧠 Jarvis (CEO)|🧠 Jarvis (CEO)]]
Agents suivis (Vidéos) : [[docs/agents/🎞️ Veille vidéos|🎞️ Veille vidéos]] · [[docs/agents/✍️ Scripts vidéos|✍️ Scripts vidéos]] · [[docs/agents/📣 Marketing vidéos|📣 Marketing vidéos]] · [[docs/agents/🎬 Création vidéos|🎬 Création vidéos]] · [[docs/agents/✂️ Monteur vidéos|✂️ Monteur vidéos]] · [[docs/agents/📤 Publication TikTok|📤 Publication TikTok]] · [[docs/agents/🧽 Nettoyage vidéos|🧽 Nettoyage vidéos]]

## Notes de Liam

_Zone libre, conservée telle quelle à chaque régénération._
