---
agent: devis
aliases: [🧾 Devis]
name: devis
role: Préparer le devis écrit (texte + PDF) et son message avec le lien de paiement du prix complet ; aperçu « à valider » pour Liam
machine: serveur DESKTOP-HLQSTAU (si listé dans agents_actifs)
planification: toutes les 3 min (serveur-taches.json, commande « jour »)
depend_de: agent-rendez-vous
sorties: B2B/devis/DEV-AAAA-NNN.pdf, .txt, -message.txt ; devis-etat.json
responsable: Vente
statut: actif
mode: simulation
horaire: "toutes les 3 min, plage tous les jours 07:00-22:00"
tags: [agent-b2b]
---
<!-- GENERE:DEBUT (régénéré par python B2B\harness\generer-fiches.py : ne pas modifier) -->
# 🧾 Devis

**Agent :** `devis` · **Statut :** actif (simulation : envoi_automatique = false) · **Responsable :** Vente (pôle) · **Machine :** serveur
**Horaire :** toutes les 3 min, plage tous les jours 07:00-22:00
**Script :** `B2B/agents/devis.py` · **Contrat :** `B2B/harness/contrats/devis.json`

## Rôle et limites
### Mission
Préparer le devis écrit (texte et PDF) à partir d'une fiche, le montrer à Liam et attendre « ok devis » ; rien ne part au client.

### Ce qu'il fait étape par étape
1. `preparer fiche.txt` ou `rapide "Nom | métier | ville | livrables | délai | oui/non | besoin"` (ou « devis : … » écrit par Liam dans le salon, mode réel).
2. Lit la fiche et `identite.json`, attribue le numéro `DEV-AAAA-NNN`.
3. Prix et liens : uniquement ceux de `OFFRE-REFERENCE.json` (page web 500 €, site complet 994 €, puis 29 €/mois, premier mois offert, lien Stripe qui comprend l'abonnement).
4. Une information absente (délai, livrables, option sans prix, lien sur mesure) : listée « À COMPLÉTER », l'agent s'arrête.
5. Écrit texte, PDF et message d'accompagnement dans `B2B\devis\`, statut « préparé ».
6. `jour` : en mode réel, poste l'aperçu « à valider » à Liam sur Discord puis cherche son « ok devis » ; en simulation, rien sur Discord (valider avec `marquer`).
7. « ok » reçu : statut « validé » ; Liam envoie lui-même puis `marquer DEV-… envoye`, `accepte`, `paye` (dans l'ordre, jamais de saut).

### Ce qu'il n'a pas le droit de faire
- envoyer au client sans accord de Liam
- encaisser ou rembourser
- publier
- signer ou promettre un résultat
- afficher un secret (jeton, clé, adresse iCal)
- envoyer le devis au client
- changer un prix
- Engager Liam (envoyer au client, encaisser, publier, signer) : `peut_engager: false`, tout passe par `B2B/a-valider/`.

## Entrées et sorties
**Lit :**
- fiche devis
- B2B/agents/identite.json
- Discord (ok devis)

**Écrit :**
- devis PDF/texte
- B2B/agents/devis-etat.json

**Discord :** devis · **Plafond :** 20 messages par jour · **Envoi au client :** non

## Horaire et état
- **Horaire :** toutes les 3 min, plage tous les jours 07:00-22:00
- **Tâche serveur :** entrée dans `B2B/agents/serveur-taches.json` ; tourne seulement si l'agent est dans `agents_actifs` (choix de Liam)
- **Contrat :** valide (`python B2B\harness\valider.py`)
- **Garde branchée :** oui
- Bloque : kill-switch `B2B\STOP`, lien Stripe non autorisé, phrase interdite (OFFRE-REFERENCE.json), secret dans le texte.
- Avertit : machine non active, envoi_automatique = false (simulation), hors horaires du contrat (07:00-22:00), plafond de 20 messages par jour.
- **Tests :** `B2B/agents/test_devis.py`
- **Alerte si silence :** aucune

<!-- DYNAMIQUE:DEBUT -->
**Derniers résultats de test (cette machine) :**
- `B2B/agents/test_devis.py` : pas encore lancé par `generer-fiches.py --tests`

**Dernière trace :** 2026-11-25 00:00 ok · **Dernière erreur :** aucune · **Dans agents_actifs (cette machine) :** oui

### Historique (5 dernières traces, sans données client)
- 2026-11-25 00:00 | jour | ok | 0.24 s
- 2026-11-24 23:57 | jour | ok | 0.23 s
- 2026-11-24 23:54 | jour | ok | 0.25 s
- 2026-11-24 23:51 | jour | ok | 0.13 s
- 2026-11-24 23:48 | jour | ok | 0.22 s
<!-- DYNAMIQUE:FIN -->

## Skill et règles
- `.claude/skills/agent-devis/SKILL.md` (copie : `docs/agents/skills/agent-devis.md`)
- Pas de preuve = pas de fait : « il a tourné » = une trace du jour `ok: true` ci-dessus ; « c'est corrigé » = ses tests puis `tests\b2b-rapide.ps1` en vert.
<!-- GENERE:FIN -->

## Liens et décisions

_Zone conservée à chaque régénération : liens vers docs\decisions et docs clés seulement._

N'envoie jamais rien au client ; `envoi_automatique` = false (Liam valide les 3 premiers à la main).
Détail : `B2B/agents/devis.md` · liens : liens de paiement
Liens : [[docs/decisions/📌 Sans acompte|📌 Sans acompte]] · [[DEVIS-ET-OBJECTIONS]]

## Notes de Liam

_Zone libre, conservée telle quelle à chaque régénération._
