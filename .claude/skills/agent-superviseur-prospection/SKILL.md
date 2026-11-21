---
name: agent-superviseur-prospection
description: Fiche de rôle du Superviseur Prospection (pôle Prospection, FERMÉ jusqu'au « go superviseurs » de Liam) — toutes les 30 minutes sur le serveur, vérifie que les agents de la prospection (relances, appels-sid, prospection) ont tourné et qu'aucun prospect n'est compté deux fois ; retire un doublon identique, remet l'historique du tableau de bord dans l'ordre, relance une fois un agent planté, et alerte sans rien toucher dès qu'il faudrait choisir entre deux données. À utiliser pour vérifier, corriger ou activer superviseur-prospection.py (passage, --essai, etat).
---

# Superviseur Prospection — la journée d'appels se remplit, sans doublon ni date impossible

**Responsable :** Prospection. **Script :** `B2B/agents/superviseur-prospection.py`. **Moteur commun :** `B2B/harness/superviseurs.py`.
**Contrat :** `B2B/harness/contrats/superviseur-prospection.json`. **Tâche serveur :** `passage` toutes les 30 min.
**Agents suivis :** relances, appels-sid, prospection.

## Ordres pas à pas (lus dans le script)
1. `M.exiger("superviseur-prospection", ...)` : refuse hors de la machine active (sauf `--essai`).
2. État de chaque agent suivi, lu dans ses traces du jour et dans sa tâche serveur (mêmes règles que le Superviseur Vente : un agent absent de `agents_actifs`,
   désactivé ou hors de ses jours n'est jamais signalé ; le samedi, un agent des jours ouvrés a le droit de se taire).
3. Agent en erreur, silencieux ou bloqué : **relancé une fois** par jour, puis alerte s'il reste en défaut.
4. Contrôles de cohérence :
   - `relances-etat.json` : clés attendues ; clé d'annonce bien formée (« téléphone|date d'appel|numéro de relance ») ; aucune date d'appel dans le futur ;
     le compte d'envois d'un jour ne dépasse pas les relances mémorisées pour ce jour.
   - `appels-sid-etat.json` : clés attendues, dates des listes déjà préparées. `appels-sid-historique.json` : aucun numéro marqué appelé à une date future, aucune entrée sans date.
   - `prospection-etat.json` : clés attendues, doublons de la liste des relances d'e-mails (un prospect relancé deux fois), dates des lots préparés et envoyés.
   - `dashboard/data/historique.json` (si le fichier est là) : une seule entrée par jour, dans l'ordre des dates, et jamais plus de leads chauds ou de rendez-vous que d'appels.
5. **Corrige seul** : clé d'état manquante ajoutée vide, doublon strictement identique retiré, `jours` de l'historique remis dans l'ordre des dates, relance d'un agent.
6. **Ne touche jamais** : une relance déjà annoncée (la supprimer ferait rappeler le lead deux fois), deux entrées pour le même jour (Liam choisit laquelle garder),
   une date dans le futur, une clé mal formée, un chiffre d'appels, de leads ou de rendez-vous. Alerte Discord + ligne dans `B2B/a-valider/AAAA-MM-JJ-superviseur-prospection.md`, puis il attend le « go ».
7. Discord : un résumé court par jour même quand tout va bien, plus un message dès qu'il y a du neuf ; rien entre 22:00 et 07:00 ; même souci annoncé une seule fois.

## Ce qu'il ne fait jamais
Écrire dans une feuille Google de Sid ; supprimer une ligne, une relance ou une entrée d'historique ; recalculer un chiffre ;
toucher au code, aux docs ou à un fichier suivi par git ; contacter un prospect, un client ou Sid ; utiliser une IA ou un service payant ; afficher un secret.

## Ouvrir l'agent (Liam seul)
`go_superviseurs` à `true` dans la variante locale de `B2B/agents/superviseurs-config.json` (hors git) — elle ouvre les quatre superviseurs et la vue Jarvis d'un coup —
puis `superviseur-prospection` ajouté à `agents_actifs` de ses réglages locaux de machine, et `envoi_automatique` à `true` pour recevoir les messages Discord.

## Vérifier (pas de preuve = pas de fait)
- `python B2B\agents\superviseur-prospection.py passage --essai` : lit tout, affiche, n'écrit rien, n'envoie rien.
- `python B2B\agents\superviseur-prospection.py etat` : verrou, dernier passage, corrections du jour, ce qui attend un « go ».
- Tests : `python tests\agents\test_superviseurs.py` (agent silencieux relancé, samedi sans alerte, doublon de relance retiré, historique remis dans l'ordre,
  deux entrées pour le même jour signalées sans rien supprimer, leads chauds ou rendez-vous supérieurs aux appels, clé mal formée, date future), puis `tests\b2b-rapide.ps1`.

## Limite connue
`dashboard/data/historique.json` et `dashboard/ventes.json` sont écrits par le gros PC : sur le serveur ils sont souvent absents, et le superviseur ne peut alors rien en dire.
