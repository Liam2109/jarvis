# B2B/agents — scripts des agents

Un agent = un script Python autonome (`<agent>.py`) + sa doc (`<agent>.md`) + ses réglages/état/journal JSON. Simulation par défaut (`envoi_automatique: false`).

## Fichiers clés
- `prospection.py` / `.md` — trouve les entreprises, prépare les lots, zones (`zone.py`).
- `appels-sid.py` / `.md` — liste d'appels quotidienne pour Sid (jamais d'envoi direct).
- `rendez-vous.py` / `.md` — surveille l'agenda Google, alerte Discord (lecture seule).
- `instagram.py` / `.md` — un post/jour sur lmmultiservices.normandie.
- `devis.py` / `.md` — prépare devis PDF, n'envoie jamais.
- `resume-sid.py` / `.md` — résumé Discord du soir (appels + CA Stripe).
- `stripe-alerte.py` / `.md` — alerte Discord à chaque paiement Stripe (lecture seule).
- `suivi.py` / `.md` — tient `suivi-prospects.csv`, ne change jamais un statut seul.
- `redaction.py` / `.md` — brouillons de messages (jamais envoyés).
- `dev-sites.md`, `sourcing.md`, `qualification.md`, `enrichissement.md`, `envoi.md`, `relances.md`, `reponses.py`/`.md` — autres étapes de la chaîne (voir `../ARCHITECTURE-AGENT-B2B.md`).

## Voir aussi
- [B2B](../README.md)
- [docs](../docs/README.md)
- [INDEX](../../INDEX.md)
