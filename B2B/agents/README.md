# B2B/agents — scripts des agents

Un agent = un script Python autonome (`<agent>.py`) + sa doc (`<agent>.md`) + ses réglages/état/journal JSON. Simulation par défaut (`envoi_automatique: false`).

## Secrets et réglages propres à une machine
`machine.py` (`surcharge_locale`) fait lire chaque `<agent>-config.json` (suivi par git, jamais de secret) puis le surcharger avec `<agent>-config.local.json` (même dossier, `*.local.json` hors git). Tout secret ou identifiant propre à une machine (adresse iCal, jeton, identifiant de salon mémorisé) va dans le fichier `.local.json`, jamais dans le fichier suivi, qui garde sa clé vide (ex. `rendez-vous-config.json` › `ical_url: ""`, vraie valeur dans `rendez-vous-config.local.json`).

## Fichiers clés
- `machine.py` — config locale (`surcharge_locale`, `ecrire_local`) et machine active (`b2b.local.json`), utilisés par tous les agents.
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
