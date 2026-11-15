# Inventaire des agents B2B (harness, 15/11/2026)

Lecture seule du dépôt. Tous les envois Discord des agents passent par `prospection.discord()` (bot, `POST /channels/<salon>/messages`), sauf `reponses.poster()`. Le seul canal vers un client est l'e-mail SMTP/API Gmail de `prospection.py` (après « ok lot » de Liam).

| Agent | Script | Horaire | Lit | Écrit | Canaux | Flags |
|---|---|---|---|---|---|---|
| appels-sid | `B2B\agents\appels-sid.py jour` | 07:30 (tâche serveur Jarvis-B2B-appels-sid), jours ouvrés | prospects Maps/CSV, historique, config | tableur Google « Appels AAAA-MM-JJ » (Drive de Sid), état, historique, journal | Google Sheets/Drive, Discord (alertes) | machine_active, envoi_automatique=false (versionné) |
| panne-alerte | `panne-alerte.py verifier` | toutes les 5 min (tâche serveur, ajouté par l'étape Argent le 15/11) | outils\agents-json.py, journaux des agents | état, journal | Discord (alertes) | machine_active, envoi_automatique=false |
| resume-sid | `resume-sid.py resume` | 19:30 jours ouvrés (tâche serveur depuis l'étape Argent, 15/11) | feuille Google du jour (lecture), Stripe charges (lecture) | état, journal | Discord | machine_active, envoi_automatique=false |
| stripe-alerte | `stripe-alerte.py verifier` | toutes les 5 min (tâche serveur depuis l'étape Argent, 15/11) | Stripe charges (clé restreinte, lecture) | état, journal | Discord | machine_active, envoi_automatique=false |
| rendez-vous | `rendez-vous.py jour` | toutes les 5 min (tâche serveur) | agenda iCal (adresse secrète dans le .local) | état, journal | Discord salon « rdv » | machine_active, **envoi_automatique=true dans le fichier versionné** |
| devis | `devis.py jour` | toutes les 3 min (tâche serveur) | fiche devis, identite.json, Discord (« ok devis ») | PDF/texte devis, état, journal | Discord (aperçu à Liam ; rien vers le client) | machine_active, envoi_automatique=false ; **liens Stripe anciens (…06, …07) dans le code** |
| reponses | `reponses.py --jours 14` | toutes les 15 min (tâche serveur) | boîtes mail (IMAP/API Gmail), agenda (créneaux), suivi | reponses-traitees.json, suivi, exclus | Discord (`reponses.poster`) | machine_active, envoi_automatique (local) |
| prospection (recherche + lots d'e-mails) | `prospection.py jour` | toutes les 10 min (tâche serveur) | API entreprises, OSM/Places, sites web, état | lots, messages-a-valider.md, état, journal | **E-mail client** (SMTP/API Gmail, après « ok lot »), Discord | machine_active, envoi_automatique=false, plafond par_boite_par_jour=10, heure_limite 17:00 |
| page-exemple | `page-exemple.py jour/continu` | à la demande (Discord) | Discord (demandes de Liam), modèles | pages déployées, suivi | Discord, déploiement (Vercel) | machine_active ; pas de tâche serveur |
| instagram | `instagram.py jour` | 12:30 (retiré, décision « Instagram retiré ») | INSTAGRAM-PLAN.md | état | API Graph Instagram, Discord | envoi_automatique=false ; inactif |
| suivi | `suivi.py` | à la main | suivi-prospects.csv | suivi-prospects.csv | aucun | — |
| redaction | `redaction.py` | à la main | prospects, identité | brouillons (aucun envoi) | aucun | — |
| pont Discord | `pont-discord\pont.py`, `notifier.py` | lancé par `jarvis.ps1` (Liam) | Discord | journal | Discord | hors B2B (non touché) |
| Jarvis CEO | skill `jarvis-ceo` | à la demande (aucun script) | états, journaux, TODO | — | Discord (via Claude, à la demande) | — |
| Vente : réponses, devis, relances J+3/J+7 | — | prévu | — | — | — | non construit |
| Production | — | prévu | — | — | — | non construit |

## Skills (`.claude\skills\`)
`agent-appels-sid`, `agent-lots-emails`, `agent-recherche`, `responsable-prospection`, `scripts-appel`, `jarvis-ceo` : fiches de rôle lues par Claude, aucun envoi propre.

## Tâches serveur (`B2B\agents\serveur-taches.json`)
appels-sid 07:30 · devis 3 min · rendez-vous 5 min · reponses 15 min · prospection 10 min · resume-sid 19:30 · stripe-alerte 5 min · panne-alerte 5 min · surveillant 19:45 et lundi 07:50. Créées par `maj-auto.ps1` seulement pour les agents de `agents_actifs` (b2b.local.json).
