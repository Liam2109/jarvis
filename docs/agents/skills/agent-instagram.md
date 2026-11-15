---
name: agent-instagram
description: Fiche de rôle de l'agent Instagram (pôle Prospection, arrêté par décision de Liam) — publiait un post par jour vers 12:30 depuis INSTAGRAM-PLAN.md. À utiliser seulement pour comprendre ou réactiver instagram.py ; ne pas le relancer sans accord de Liam.
---

# Agent Instagram — arrêté

**Responsable :** Prospection. **Script :** `B2B/agents/instagram.py`. **Contrat :** `B2B/harness/contrats/instagram.json` (statut inactif).
**Décision :** `docs/decisions/📌 Instagram retiré.md`. Aucune tâche serveur. Publier engage Liam : jamais sans son accord.

## Mission
Publier un post par jour à 12:30 (agent retiré par décision de Liam).

## Ordres pas à pas (lus dans le script)
1. `jour` : si c'est l'heure (12:30 heure de Paris, fenêtre de 90 minutes), prend le prochain post de la file `docs\INSTAGRAM-PLAN.md`.
2. Vérifie la légende (mots interdits : garanti, n° 1, meilleur, avis, prix en €, etc.) et le fichier (image ou vidéo).
3. Publie par l'API officielle Instagram (Graph API, jeton dans `instagram-token.json`, hors git, jamais affiché) ; en simulation (défaut), rien n'est publié ni coché.
4. Coche la ligne du plan avec la date.
5. `visuels` : file sous 3 posts → fabrique les prochaines cartes, à valider par Liam dans `instagram-a-valider.md` ; `valider` les ajoute à la file.

## Entrées et sorties
- Entrées : `B2B/docs/INSTAGRAM-PLAN.md`, `instagram-a-valider.md`, jeton Graph API.
- Sorties : publication Instagram, plan coché, `instagram-etat.json`, `instagram-journal.log`, alertes Discord.

## Cas limites gérés par le code
- Une seule publication par jour.
- Connexion perdue, vérification de sécurité, erreur ou publication incertaine : arrêt immédiat, alerte Discord, aucune reprise automatique (`reprendre`).

## Ce qu'il ne fait jamais
- Saisir un mot de passe, envoyer un message privé, commenter, s'abonner.
- Inventer une information (légendes du plan seulement, « exemple, pas un site client »).

## Vérifier qu'il a bien tourné
- `python B2B\agents\instagram.py file` : prochain post et lignes bloquées.
- Test : `python B2B\agents\test_instagram.py`.

## Quand il alerte Liam
- Toute erreur ou suspension (alerte Discord, une par motif et par jour).
- Réactivation : à compléter par Liam (décision « Instagram retiré » en vigueur).
