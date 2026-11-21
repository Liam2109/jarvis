---
name: agent-superviseur-vente
description: Fiche de rôle du Superviseur Vente (pôle Vente, FERMÉ jusqu'au « go superviseurs » de Liam) — toutes les 30 minutes sur le serveur, vérifie que les agents de la vente (devis, chiffres-serveur, stripe-alerte, rendez-vous, reponses) ont tourné et que leurs données ne se contredisent pas ; relance une fois un agent planté, retire un doublon identique, ajoute une clé d'état manquante, et n'écrit JAMAIS dans un fichier d'argent (alerte Discord et attend « go »). À utiliser pour vérifier, corriger ou activer superviseur-vente.py (passage, --essai, etat).
---

# Superviseur Vente — les agents de la vente tournent, et leurs chiffres ne se contredisent pas

**Responsable :** Vente. **Script :** `B2B/agents/superviseur-vente.py`. **Moteur commun :** `B2B/harness/superviseurs.py`.
**Contrat :** `B2B/harness/contrats/superviseur-vente.json`. **Tâche serveur :** `passage` toutes les 30 min.
**Agents suivis :** devis, chiffres-serveur, stripe-alerte, rendez-vous, reponses.

## Ordres pas à pas (lus dans le script)
1. `M.exiger("superviseur-vente", ...)` : refuse hors de la machine active (sauf `--essai`).
2. Pour chaque agent suivi : son état est lu dans ses **traces** du jour (`B2B/logs/agents/<agent>/`) et dans sa tâche (`serveur-taches.json`).
   Un agent absent de `agents_actifs`, désactivé, pas encore actif ou hors de ses jours n'est jamais signalé : il n'a pas de tâche sur cette machine.
   « erreur » = dernier passage du jour `ok: false` ; « silence » = heure fixe + délai de grâce passés sans passage ; « bloque » = agent cyclique muet depuis plus de 3 cycles + grâce.
3. Agent en erreur, silencieux ou bloqué : **relancé une fois**, avec la commande de sa tâche serveur, puis noté au journal. Au passage suivant, s'il est toujours en défaut : alerte, plus de relance (jamais deux par jour).
4. Contrôles de cohérence : `devis-etat.json` (clés attendues, doublons de `ok_utilises`, dates des alertes, prix comparé à `B2B/docs/OFFRE-REFERENCE.json`),
   `stripe-alerte-etat.json` et `chiffres-serveur-etat.json` (fichiers d'argent), `rendez-vous-etat.json` (échecs de lecture de l'agenda),
   `reponses-traitees.json` (doublons), la partie financière de `dashboard/ventes.json` si elle est là, et les brouillons du jour de `B2B/a-valider` plus `B2B/messages-a-valider.md`.
5. **Corrige seul** (rien ne peut être perdu) : clé d'état manquante ajoutée **vide**, doublon **strictement identique** retiré (la première ligne reste), liste remise dans l'ordre des dates, relance d'un agent.
6. **Ne touche jamais** : un fichier d'argent (même une clé manquante : remettre `dernier_ts` à zéro réannoncerait d'anciens paiements), un montant, un prix, un devis, un chiffre du tableau de bord, un brouillon destiné à Liam ou à un client, un fichier illisible, une donnée en double qu'il faudrait choisir, une date illogique. Dans tous ces cas : une alerte Discord et une ligne dans `B2B/a-valider/AAAA-MM-JJ-superviseur-vente.md`, puis il attend le « go ».
7. Discord : un résumé court par jour même quand tout va bien (à partir de `heure_resume`), plus un message dès qu'il corrige ou découvre quelque chose de neuf. Jamais la nuit (plage 07:00-22:00) : une alerte de 3 h attend le passage du matin. Même souci = annoncé une seule fois.

## Ce qu'il ne fait jamais
Supprimer une donnée ; écraser une valeur déjà écrite ; toucher à l'argent ; toucher au code, aux skills, aux docs ou à un fichier suivi par git ;
écrire dans les données d'un autre domaine ; corriger avant le « go superviseurs » ; contacter qui que ce soit d'autre que Liam ; utiliser une IA ou un service payant ; afficher un secret.

## Ouvrir l'agent (Liam seul)
Le verrou `go_superviseurs` reste `false` dans les fichiers de réglages versionnés. Pour ouvrir les quatre superviseurs et la vue Jarvis d'un coup,
Liam met `go_superviseurs` à `true` dans la variante locale de `B2B/agents/superviseurs-config.json` (hors git), met `envoi_automatique` à `true` quand il veut les messages Discord,
puis ajoute `superviseur-vente` à `agents_actifs` de ses réglages locaux de machine.

## Vérifier (pas de preuve = pas de fait)
- `python B2B\agents\superviseur-vente.py passage --essai` : lit tout, affiche le résumé, n'écrit rien, n'envoie rien, ne relance rien.
- `python B2B\agents\superviseur-vente.py etat` : verrou, dernier passage, corrections du jour, ce qui attend un « go ».
- Tests : `python tests\agents\test_superviseurs.py` (agent planté relancé une seule fois, doublon retiré, clé ajoutée vide, fichier d'argent jamais touché, prix hors référence, Potentiel incohérent, verrou fermé, `--essai`), puis `tests\b2b-rapide.ps1`.

## Limite connue
Il juge un agent sur ses traces : un agent qui tourne sans écrire de trace passerait pour silencieux, et un agent qui écrit « ok » en se trompant passerait pour sain.
Les contrôles de cohérence portent sur la forme et les contradictions visibles, pas sur la justesse d'un chiffre (seul Liam sait si un devis est vrai).
