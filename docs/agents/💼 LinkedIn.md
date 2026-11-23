---
agent: linkedin
aliases: [💼 LinkedIn]
name: linkedin
role: "Chaque jour ouvré à 07:45, poste sur Discord 1 à 2 posts LinkedIn pour Liam, à valider (✅ ❌) puis coller lui-même. Ne publie jamais sur LinkedIn."
machine: "serveur"
planification: "chaque jour à 07:45, plage lundi-vendredi 07:45-19:00"
sorties: "B2B/linkedin/file.json (file des posts, statuts, état), B2B/agents/linkedin-journal.log"
responsable: Prospection
statut: actif
mode: simulation
horaire: "chaque jour à 07:45, plage lundi-vendredi 07:45-19:00"
tags: [agent-b2b]
---
<!-- GENERE:DEBUT (régénéré par python B2B\harness\generer-fiches.py : ne pas modifier) -->
# 💼 LinkedIn

**Agent :** `linkedin` · **Statut :** actif (simulation : envoi_automatique = false) · **Responsable :** Prospection (pôle) · **Machine :** serveur
**Horaire :** chaque jour à 07:45, plage lundi-vendredi 07:45-19:00
**Script :** `B2B/agents/linkedin.py` · **Contrat :** `B2B/harness/contrats/linkedin.json`

## Rôle et limites
### Mission
Chaque jour ouvré à 07:45, poste sur Discord 1 à 2 posts LinkedIn pour Liam, à valider (✅ ❌) puis coller lui-même. Ne publie jamais sur LinkedIn.

### Ce qu'il fait étape par étape
1. `M.exiger("linkedin", ...)` : refuse hors de la machine active (sauf `--essai`).
2. **Import** : chaque `lot-*.md` est lu ; un post conforme est rangé `en file` (identifiant = 8 caractères du texte, jamais deux fois le même texte) ; un post refusé ou un bloc mal formé est signalé, les autres passent. Un lot avec refus déclenche **un** message Discord par jour.
3. **Réactions** (✅ ❌ 📌) des posts proposés depuis moins de 7 jours : **seules celles posées par Liam comptent** (ni le bot, ni un autre compte). ❌ gagne sur ✅. ✅ → `prêt`. 📌 → `publié` (la date est au journal). Discord illisible : rien ne change et aucun post n'est déclaré non validé à tort.
4. **Non validé** : un post proposé un jour précédent sans ✅ ni ❌ passe `non validé`, signalé **une seule fois**. **Il ne repart jamais seul** : Liam le valide (✅ ou `valider ID`) ou le rejette.
5. **Posts du jour**, en alternance stricte : un `recrutement` (créneau 08:30) puis un `prospect` (12:30) ; `posts_par_jour = 1` alterne un par jour. Chaque post est un message : texte dans un bloc à copier, puis les boutons ✅ ❌ 📌 posés par le bot. Si un type manque, rien n'est posté à sa place. Un texte modifié à la main dans `file.json` est recontrôlé : s'il viole une règle, il est écarté et n'est jamais envoyé.
6. **Stock** : moins de 3 jours de posts après le passage = **code 5**, trace en erreur (le surveillant la signale) et message « demande un nouveau lot à Claude ».
7. Journal `B2B/agents/linkedin-journal.log` : une ligne par fait (`proposé`, `prêt`, `publié` avec sa date, `rejeté`, `non validé`). Aucun secret.

### Ce qu'il n'a pas le droit de faire
- publier sur LinkedIn, par une API ou en automatisant le site (Liam copie et colle lui-même)
- republier seul un post proposé et non validé (il est signalé, jamais reproposé)
- proposer un post qui contient un emoji, une image, un lien, un e-mail, un téléphone ou plus de 3 hashtags
- tutoyer, inventer un témoignage, un client ou un chiffre, promettre un résultat ou un gain
- écrire un prix ou une commission autre que ceux de OFFRE-REFERENCE.json (pack 595 €, site complet 994 €, 49 €/mois) et des commissions 15 % appelants et 10 % closers
- utiliser une phrase interdite de OFFRE-REFERENCE.json ou un appel à l'action autre que « écrivez-moi en message privé »
- proposer de passer sur place ou de rencontrer un prospect (appels seulement)
- présenter une page exemple comme un client
- lire une réaction d'un autre compte que celui de Liam
- appeler Claude, une IA ou un service payant
- contacter un prospect, un client ou Sid
- afficher un secret (jeton, clé)
- encaisser, publier ou signer
- Engager Liam (envoyer au client, encaisser, publier, signer) : `peut_engager: false`, tout passe par `B2B/a-valider/`.

## Entrées et sorties
**Lit :**
- B2B/linkedin/lot-AAAA-MM-JJ.md (lots de posts écrits par Claude dans le chat, collés par Liam)
- B2B/linkedin/file.json
- B2B/docs/OFFRE-REFERENCE.json (prix)
- B2B/agents/linkedin-config.json
- réactions ✅ ❌ 📌 de Liam sur Discord (lecture seule)

**Écrit :**
- B2B/linkedin/file.json (file des posts, statuts, état)
- B2B/agents/linkedin-journal.log

**Discord :** b2b · **Plafond :** 6 messages par jour · **Envoi au client :** non

## Horaire et état
- **Horaire :** chaque jour à 07:45, plage lundi-vendredi 07:45-19:00
- **Tâche serveur :** entrée dans `B2B/agents/serveur-taches.json` ; tourne seulement si l'agent est dans `agents_actifs` (choix de Liam)
- **Contrat :** valide (`python B2B\harness\valider.py`)
- **Garde branchée :** oui
- Bloque : kill-switch `B2B\STOP`, lien Stripe non autorisé, phrase interdite (OFFRE-REFERENCE.json), secret dans le texte.
- Avertit : machine non active, envoi_automatique = false (simulation), hors horaires du contrat (07:45-19:00), plafond de 6 messages par jour.
- **Tests :** `tests/agents/test_linkedin.py`
- **Alerte si silence :** après 08:15 (surveillant)

<!-- DYNAMIQUE:DEBUT -->
**Derniers résultats de test (cette machine) :**
- `tests/agents/test_linkedin.py` : pas encore lancé par `generer-fiches.py --tests`

**Dernière trace :** aucune · **Dernière erreur :** aucune · **Dans agents_actifs (cette machine) :** non (Liam l'ajoute s'il veut le planifier)

### Historique (5 dernières traces, sans données client)
- aucune trace sur cette machine
<!-- DYNAMIQUE:FIN -->

## Skill et règles
- `.claude/skills/agent-linkedin/SKILL.md` (copie : `docs/agents/skills/agent-linkedin.md`)
- Pas de preuve = pas de fait : « il a tourné » = une trace du jour `ok: true` ci-dessus ; « c'est corrigé » = ses tests puis `tests\b2b-rapide.ps1` en vert.
<!-- GENERE:FIN -->

## Liens et décisions

_Zone conservée à chaque régénération : liens vers docs\decisions et docs clés seulement._

Liens : aucun pour l'instant.

## Notes de Liam

_Zone libre, conservée telle quelle à chaque régénération._
