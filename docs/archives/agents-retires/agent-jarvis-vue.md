---
name: agent-jarvis-vue
description: Fiche de rôle de la Vue Jarvis des superviseurs (rattachée à Jarvis (CEO), FERMÉE jusqu'au « go superviseurs » de Liam) — toutes les 30 minutes sur le serveur, elle remet l'état des quatre domaines (Vente, Prospection, Sites, Mail) dans un fichier court hors git et poste UN seul message Discord groupé par jour : ok / corrigé / bloqué en attente de « go ». Elle ne corrige rien et ne relance rien. À utiliser pour vérifier, corriger ou activer jarvis-vue.py (passage, --essai, etat).
---

# Vue Jarvis — l'état des quatre domaines d'un seul coup d'œil

**Responsable :** Jarvis (CEO). **Script :** `B2B/agents/jarvis-vue.py`. **Moteur commun :** `B2B/harness/superviseurs.py`.
**Contrat :** `B2B/harness/contrats/jarvis-vue.json`. **Tâche serveur :** `passage` toutes les 30 min.
**Lit :** l'état et le journal des quatre superviseurs (Vente, Prospection, Sites, Mail). **Écrit :** `B2B/logs/superviseurs/ETAT-SUPERVISEURS.md` (hors git) et son propre état.

## Ordres pas à pas (lus dans le script)
1. `M.exiger("jarvis-vue", ...)` : refuse hors de la machine active (sauf `--essai`).
2. Pour chacun des quatre domaines, elle lit **ce que le superviseur a déjà écrit** (son état et son journal) : aucun contrôle n'est refait, aucun chiffre n'est recalculé.
   Un domaine est : « ok » (rien à signaler), « corrigé » (le superviseur a réparé tout seul aujourd'hui), « bloqué » (il attend un « go » de Liam),
   « jamais passé » (le superviseur n'a pas encore tourné) ou « inconnu » (son état est illisible).
3. Elle réécrit à chaque passage un **fichier court** : un tableau d'une ligne par domaine (état, dernier passage, corrections du jour, nombre d'items en attente),
   puis la liste de ce qui attend un « go » et la liste de ce qui a été corrigé seul aujourd'hui. Pas d'historique : il est dans git et dans les journaux des superviseurs (décision du 15/11/2026).
4. Discord : **un seul message groupé par jour**, à partir de `heure_resume` (19:40 par défaut) : une ligne avec l'état des quatre domaines, puis ce qui attend un « go ».
   Rien avant cette heure, rien deux fois, rien si le verrou est fermé.
5. Elle **ne corrige rien, ne relance rien, ne supprime rien** : si deux domaines se contredisent, c'est leur superviseur qui le dit, pas elle.

## Ce qu'elle ne fait jamais
Corriger, réparer, relancer, supprimer ; recalculer un chiffre remonté par un superviseur ; écrire dans les données d'un agent ;
toucher à un fichier suivi par git ; contacter qui que ce soit d'autre que Liam ; utiliser une IA ou un service payant ; afficher un secret.

## Ouvrir l'agent (Liam seul)
Même verrou que les quatre superviseurs : `go_superviseurs` à `true` dans la variante locale de `B2B/agents/superviseurs-config.json` (hors git),
puis `jarvis-vue` ajouté à `agents_actifs` de ses réglages locaux de machine, et `envoi_automatique` à `true` pour recevoir le message groupé.

## Vérifier (pas de preuve = pas de fait)
- `python B2B\agents\jarvis-vue.py etat` : le tableau des quatre domaines à l'écran, sans rien écrire.
- `python B2B\agents\jarvis-vue.py passage --essai` : affiche le message groupé, n'écrit rien, n'envoie rien.
- Le fichier : `B2B\logs\superviseurs\ETAT-SUPERVISEURS.md` (hors git, réécrit à chaque passage).
- Tests : `python tests\agents\test_superviseurs.py` (les quatre domaines remontés avec ok / corrigé / bloqué / jamais passé, un seul message par jour,
  rien avant l'heure, elle ne touche à aucun état, `--essai`, verrou fermé), puis `tests\b2b-rapide.ps1`.

## Limite connue
Elle est aussi juste que les superviseurs : si l'un d'eux ne tourne pas, son domaine apparaît « jamais passé », ce qui ne veut pas dire que le domaine va bien.
C'est le surveillant du harness et l'agent Alerte panne qui préviennent qu'un superviseur lui-même ne tourne plus.
