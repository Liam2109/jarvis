# B2B — agence LM MULTI-SERVICES

Création et vente de sites web pour artisans/commerçants (Normandie) : prospection, maquettes, devis, rendez-vous, suivi.

## Fichiers clés
- `ARCHITECTURE-AGENT-B2B.md` — la chaîne des sous-agents (Jarvis -> superviseur B2B -> agents).
- `CLAUDE.md` — règles permanentes (style des sites, ressources PC) ; s'ajoute à `../CLAUDE.md`.
- `LISEZ-MOI.md` — kit de démarrage historique (sourcing -> maquette -> envoi).
- `PROMPT-RECHERCHE-SITES.md` / `PROMPT-RECHERCHE-SITES-LONG.md` — prompts maîtres pour générer les pages.
- `generer.py`, `sourcing.py` — premiers scripts (maquette par prospect, liste Sirene).
- `sites/` — moteur de pages et pages exemple (voir `sites/moteur/REGLES-STYLE-SITES.md`, à lire avant toute page).

## Voir aussi
- [agents](agents/README.md) — scripts autonomes par agent
- [docs](docs/README.md) — contexte, offres, journal
- [INDEX](../INDEX.md)
