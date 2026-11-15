---
name: agent-page-exemple
description: Fiche de rôle de l'agent Page exemple (pôle Production, inactif) — sur un message « métier, ville, nom » de Liam dans Discord, génère et déploie une page exemple personnalisée depuis le modèle validé du métier. À utiliser pour vérifier ou corriger page-exemple.py (generer, jour, etat).
---

# Agent Page exemple — une page à son nom, à la demande

**Responsable :** Production. **Script :** `B2B/agents/page-exemple.py`. **Contrat :** `B2B/harness/contrats/page-exemple.json` (statut inactif).
**Tâche serveur :** aucune (lancé à la demande ; le profil serveur n'a pas de navigateur). Avant toute page : `B2B/CLAUDE.md` et `sites\moteur\REGLES-STYLE-SITES.md`.

## Mission
Générer et déployer une page exemple personnalisée à la demande de Liam sur Discord, depuis un modèle validé.

## Ordres pas à pas (lus dans le script)
1. Déclencheur : `generer "plombier, Yvetot, Dupont Plomberie"` ou un message de Liam (seul `DISCORD_USER_ID`) dans le salon dédié ; curseur posé au premier passage, avancé avant le traitement.
2. Analyse « métier, ville, nom » ; métier non reconnu : rien n'est créé, l'agent le dit.
3. Ville ou nom absent : hypothèse par défaut, dite dans la réponse (aucune question à Liam).
4. Choisit le modèle validé du métier (plombier, électricien, coiffeur, fleuriste, boulangerie, garage, restaurant), crée `sites/deploiement/<slug>`.
5. Délègue l'écriture et le déploiement à un sous-agent `claude -p` (outils limités ; jamais git push, git config ni git add -A).
6. Exige une ligne LIEN ; vérifie lui-même que le lien est sur `b2b-demos.vercel.app`, contient le slug et répond 200 avec `noindex`.
7. Ajoute une ligne à `pages-exemple\suivi.csv`, répond sur Discord **seulement avec le lien**.

## Entrées et sorties
- Entrées : messages Discord de Liam, modèles de pages, `identite.json`, réglages `page-exemple-config.json`.
- Sorties : dossier `sites/deploiement/<slug>`, page déployée (Vercel, noindex), `pages-exemple\suivi.csv`, `page-exemple-etat.json`, journal.

## Cas limites gérés par le code
- Sous-agent en échec ou délai dépassé, pas de ligne LIEN, lien inattendu, lien qui ne répond pas : pas de lien envoyé, échec journalisé, alerte.
- Modèle introuvable : échec.
- Erreur : arrêt, suspension, `reprendre` pour repartir.

## Ce qu'il ne fait jamais
- Répondre à quelqu'un d'autre que Liam, rejouer l'historique du salon.
- Pousser sur git, indexer la page.
- Attention : le sous-agent `claude -p` consomme des jetons au moment de l'exécution ; l'agent est inactif (contrat).

## Vérifier qu'il a bien tourné
- `python B2B\agents\page-exemple.py etat` : pages déjà générées.
- `pages-exemple\suivi.csv` et `page-exemple-journal.log`.
- Tests : aucun dans le contrat (à compléter par Liam).

## Quand il alerte Liam
- Échec de génération ou de vérification du lien, arrêt sur erreur.
- `alerte_si_silence` : aucune.
