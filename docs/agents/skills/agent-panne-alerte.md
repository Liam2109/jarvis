---
name: agent-panne-alerte
description: Fiche de rôle de l'agent Alerte panne (rattaché à Jarvis CEO) — prévient Liam sur Discord quand un agent planifié à heure fixe n'a pas tourné après son délai de grâce, une fois par jour. À utiliser pour vérifier ou corriger panne-alerte.py (verifier, etat).
---

# Agent Alerte panne — un agent à heure fixe n'a pas tourné

**Responsable :** Jarvis (CEO). **Script :** `B2B/agents/panne-alerte.py`. **Contrat :** `B2B/harness/contrats/panne-alerte.json`.
**Tâche serveur :** `verifier` toutes les 5 minutes.

## Mission
Alerter Liam sur Discord quand un agent planifié à heure fixe n'a pas tourné après son délai de grâce, une seule fois par jour.

## Ordres pas à pas (lus dans le script)
1. `M.exiger("panne-alerte", ...)` : machine active obligatoire (sauf `--a-blanc`).
2. Réglages `panne-alerte-config.json` (+ `.local.json`) : `envoi_automatique` (false = simulation), `intervalle_minutes` (5), `grace_minutes` (15, borné 0-240).
3. Construit la liste des agents avec `outils\agents-json.py` (`construire()["agents"]`) : nom, planifié, horaire, dernier passage.
4. Ne garde que les agents planifiés « chaque jour à HH:MM » (ex. appels-sid 07:30, resume-sid 19:30) ; les agents « toutes les N minutes » ne sont pas concernés.
5. Panne = heure prévue + délai de grâce dépassée et aucun passage aujourd'hui.
6. Pour chaque panne pas encore alertée aujourd'hui : « ⚠️ Panne : <agent> — aucune exécution aujourd'hui (prévue HH:MM) », postée (mode réel) ou affichée (simulation), journalisée.
7. Mémorise les alertes du jour dans `panne-alerte-etat.json` (30 jours gardés).

## Entrées et sorties
- Entrées : `outils/agents-json.py` (journaux, tâches planifiées, états), réglages.
- Sorties : message Discord (salon habituel, via `prospection.discord`), `panne-alerte-etat.json`, `panne-alerte-journal.log`.

## Cas limites gérés par le code
- Trop tôt pour juger (avant heure + grâce) : rien.
- **Agent en attente (22/11/2026) : rien.** Un agent absent de `agents_actifs` (Liam ne l'a pas encore ouvert sur cette machine) ou dont un verrou `go_*` est fermé dans ses réglages (ex. `go_interim` avant le « go interim ») n'est pas cassé : il attend. Il n'est jamais compté en panne et rien ne part sur Discord. Même règle que les superviseurs et le surveillant du harness. Le verrou commun des superviseurs est lu dans l'ordre du code (fichiers versionnés d'abord, variantes locales ensuite), donc un « go » posé une seule fois dans la variante locale commune est bien vu.
- Agent désactivé dans `serveur-taches.json`, pas encore actif (`actif_le`) ou hors de ses jours (week-end d'un agent des jours ouvrés) : rien.
- Jamais deux fois la même alerte le même jour.
- État illisible : arrêt, code 2, rien n'est écrit.
- Discord injoignable : « Discord : non envoyé », l'alerte est quand même notée pour le jour.

## Ce qu'il ne fait jamais
- Relancer un agent, écrire ailleurs que dans son état et son journal.
- Afficher le jeton Discord.

## Vérifier qu'il a bien tourné
- `python B2B\agents\panne-alerte.py etat` : pannes alertées aujourd'hui.
- `python B2B\agents\panne-alerte.py verifier --a-blanc` : ce qui serait alerté, sans rien écrire.
- Test : `python tests\agents\test_panne_alerte.py`.
- Le script n'écrit pas de trace du harness lui-même : celle-ci vient du lanceur `serveur-b2b.ps1` sur le serveur.

## Quand il alerte Liam
- Chaque agent à heure fixe en panne, une fois par jour.
- Silence : le surveillant le signale si aucune trace après 19:40.
