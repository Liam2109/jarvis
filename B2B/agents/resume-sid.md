# Agent resume-sid (9 nov. 2026)
Rôle : un **résumé Discord en fin de journée** (19 h par défaut) de l'activité B2B du jour : les cases cochées par Sid sur sa feuille Google du jour (`Appelé`, `Répondu`, `Rendez-vous pris`, `Refus` — même feuille que l'agent `appels-sid`, lue en **lecture seule**) et le **chiffre d'affaires Stripe** encaissé depuis minuit (Europe/Paris). **N'envoie rien à un prospect, à Sid ni à un client** : le seul message qu'il poste est le résumé, dans le salon Discord habituel des agents. Code : `agents\resume-sid.py` (lit `agents\google_sheets.py` et `agents\appels-sid-etat.json`, jamais écrits) ; tests : `agents\test_resume_sid.py` + `tests\resume-sid.ps1` (listé dans `tests\tout.ps1`) ; réglages : `agents\resume-sid-config.json` ; état : `agents\resume-sid-etat.json` ; journal : `agents\resume-sid-journal.log`.

**Simulation par défaut** (`envoi_automatique: false`) : le résumé est calculé et affiché en console (et journalisé), **rien sur Discord**. Un jour sans feuille Google (simulation d'appels-sid, jour hors planning, pas encore sourcé) ou sans clé Stripe valide : annoncé sans chiffre inventé, jamais un zéro silencieux.

## Commandes
| Commande | Effet |
|---|---|
| `python agents\resume-sid.py resume [--jour AAAA-MM-JJ] [--a-blanc]` | Calcule le résumé du jour et le poste (mode réel) ou l'affiche (simulation / `--a-blanc`). Un résumé par jour : un second lancement le même jour ne refait rien (sauf `--a-blanc`, qui affiche toujours). C'est ce que lance la tâche planifiée de 19 h. |
| `etat` | Date du dernier résumé envoyé (ou simulé). |
| `installer-tache` / `retirer-tache` `[--oui]` | Tâche planifiée Windows. **Sans `--oui` : affiche seulement la commande PowerShell, n'exécute rien.** |

## Sources, toutes les deux en lecture seule
- **Appels Sid** : `agents\appels-sid-etat.json` › `google` › `<jour>` › `feuille` (l'identifiant de la feuille Google créée par `appels-sid.py jour`, quand il tourne pour de vrai). La feuille est **exportée en CSV** (`google_sheets.Drive.lire_feuille`, portée `drive.file` déjà autorisée pour `appels-sid` : elle couvre les fichiers que ce jeton a créés, même partagés ensuite avec Sid) ; les colonnes `Appelé`, `Répondu`, `Rendez-vous pris`, `Refus` sont comptées par en-tête (pas par position). **Rien n'est écrit sur la feuille.** Aucune feuille ce jour-là = annoncé tel quel (pas un zéro).
- **Chiffre d'affaires** : `GET /v1/charges` (API Stripe, clé **restreinte** `STRIPE_RESTRICTED_KEY` de `Jarvis\.env`, déjà utilisée par le briefing vocal — `lib\business.ps1`), paiements `paid` et `status=succeeded` depuis minuit (Europe/Paris) ce jour-là, montant moins remboursements, regroupés par devise. Clé absente, refusée ou Stripe injoignable = annoncé tel quel.
- Aucune donnée personnelle (nom, e-mail, numéro de téléphone ou de carte) dans le message Discord : uniquement des comptes et des montants.

## Pour l'activer (Liam)
1. `appels-sid` doit déjà tourner pour de vrai (`envoi_automatique: true` dans `agents\appels-sid-config.local.json`) pour qu'une feuille Google existe chaque jour de rappel ; sans ça, la partie « Appels Sid » du résumé dit toujours « aucune feuille ».
2. `STRIPE_RESTRICTED_KEY` renseignée dans `Jarvis\.env` (voir `.env.example`) pour la partie chiffre d'affaires.
3. **Jamais dans `agents\resume-sid-config.json`** (fichier versionné, poussé sur GitHub) : `envoi_automatique: true` se met dans `agents\resume-sid-config.local.json` (créé à la main, ignoré par git, propre à cette machine). Le fichier versionné reste `envoi_automatique: false`.
4. `python agents\resume-sid.py installer-tache --oui` (tâche de 19 h 00, `heure_tache` du réglage).
5. Contrôle le lendemain : `python agents\resume-sid.py etat`, le journal, le salon Discord habituel.
