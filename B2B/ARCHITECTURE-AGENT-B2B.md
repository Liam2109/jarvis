# Agent B2B (4e superviseur de Jarvis, voir C75) — architecture

Jarvis (directeur) -> Superviseur B2B -> sous-agents. Les ordres descendent, les résumés remontent à Jarvis (Discord #b2b).

## Sous-agents
| Agent | Rôle | Entrée -> Sortie | Autonomie |
|---|---|---|---|
| 1. Sourcing | Liste d'entreprises locales (API Sirene) | secteur + zone -> prospects.csv | 100 % auto, 1x/semaine |
| 2. Enrichissement | Téléphone, note, avis, a un site ? (Google Maps) | prospects.csv -> prospects_enrichis.csv | auto, par lots |
| 3. Qualification | Score : pas de site, note >= 4, >= 10 avis | enrichis -> short-list | 100 % auto |
| 4. Maquette | Une maquette par prospect (maquette-entreprise.html) | short-list -> maquettes\ + lien Vercel | auto |
| 5. Rédaction | Mail (4-6 lignes) + message LinkedIn/Facebook, avec mentions légales et STOP | short-list + lien -> brouillons | auto, brouillons seulement |
| 6. Envoi | Envoie les mails validés (Instantly ou Gmail), 20-30/boîte/jour | brouillons validés -> envois | SEULEMENT après ton OK par lot |
| 7. Réponses | Classe les réponses (intéressé / plus tard / non / STOP), met à jour la liste d'exclusion | boîte mail -> résumé + notif | auto, ne répond jamais seul |
| 9. Dev sites | Fait les maquettes (même complexes : 3D, sections spéciales), personnalise après la vente, gère les demandes spéciales d'un client (changement, ajout, site sur mesure) | short-list + demandes clients -> sites (lien Vercel), modifications | auto pour les maquettes ; sites spéciaux et changements après vente : validation de Liam avant mise en ligne |
| 8. Relances | J+3, J+7, J+14 puis arrêt | suivi -> brouillons | brouillons, validation |

## Dossier de chaque agent (agents\<nom>.md)
Chaque agent a son fichier, qu'il lit au début et met à jour à la fin de chaque tâche :
- Rôle et consignes (ce qu'il sait faire, ses skills/plugins).
- Clients et prospects suivis : nom, métier, ville, statut, lien du site, dates.
- Demandes en cours : qui a demandé quoi, quand, état (à faire / en cours / à valider / fait).
- Historique des décisions de Liam (ce qu'il a validé ou refusé).
Jarvis lit ces fichiers pour son résumé quotidien. Fichiers : agents\sourcing.md, enrichissement.md, qualification.md, dev-sites.md, redaction.md, envoi.md, reponses.md, relances.md.

## Agent Dev sites (précisions)
- Skills : design (rendu non générique), 3D (three.js, scroll), checklist qualité mobile/vitesse/clarté.
- Un modèle par métier + un objet 3D par métier (ampoule, robinet, toit, briques). Modèle de départ : prototype électricien 3D.
- Un site par prospect contacté, sur un lien (Vercel, projet unique, pages non indexées).
- Après la vente : personnalisation (textes, photos, couleurs), et demandes spéciales, chacune notée dans dev-sites.md.
- Au début, c'est lent et compliqué : sites complexes faits un par un, avec retour de Liam, avant d'automatiser.

## Agent Dev sites : état au 24 oct. 2026
- Moteur : `sites\moteur\generer.py` (CSV -> une page par prospect, score /100 dans agents\dev-sites.md). Familles : artisan (6 métiers, 3 directions), restaurant (2), commerce (1, 3D facultative au clic).
- Contrôle : `sites\outils\qa.mjs` (captures 390/1280, console, Lighthouse mobile). Prompt maître : `recherche-sites\07-prompt-maitre.md`. Références restaurants/commerces et licences photo : `recherche-sites\10-restaurants-commerces.md`.
- Déploiement : un seul projet Vercel, pages `noindex`, jeton dans l'URL. Pas encore créé (attente de l'accord de Liam).

## Agents Rédaction et Suivi : état au 24 oct. 2026 (détail dans agents\redaction.md et agents\suivi.md)
- Chaîne testée sur 3 prospects fictifs : CSV -> `generer.py` (maquettes) -> `agents\redaction.py` (`messages-a-valider.md`, statut « à valider ») -> `agents\suivi.py` (`suivi-prospects.csv`). Résultat du test : `sites\exemples\resultat-test\`.
- Rédaction : e-mail + LinkedIn, accroche métier + ville, constat seulement s'il est vérifié (`note_besoin`), lien de SA maquette, « Qui je suis », STOP. Contrôles ⚠ avant envoi (identité incomplète dans `agents\identite.json`, lien non déployé, e-mail sans source…). Aucun envoi.
- Suivi : statuts à contacter / envoyé / répondu / maquette envoyée / devis / signé / refusé / STOP ; relance J+2 ; le script ne change un statut qu'à la demande de Liam. STOP = exclusion définitive, sautée par Rédaction.
- Vercel : projet `b2b-demos` en ligne (24 oct. 2026), base https://b2b-demos.vercel.app ; `agents\identite.json` › `base_url_maquettes` renseignée. Les pages de vrais prospects ne sont déployées qu'avec l'accord de Liam.

## Agent Sourcing : architecture (24 oct. 2026, détail dans agents\sourcing.md)
- Sources publiques seulement : annuaire officiel des entreprises (API, automatique), fiches Google Maps et Pages Jaunes consultées à la main, site propre de l'entreprise. Pas d'achat de liste, pas d'adresse devinée.
- Sortie : `prospects.csv` (nom, métier, ville, téléphone, e-mail pro avec type et source, site actuel, note de besoin) -> Qualification -> Dev sites.
- Conformité B2B : message lié à l'activité, identification (LM MULTI-SERVICES + SIRET), origine du contact, STOP, liste d'exclusion, traçabilité. À faire relire avant le premier envoi.

## Règles
- Aucun envoi sans validation de Liam (comme l'agent Mail).
- Liste d'exclusion : un STOP = plus jamais recontacté.
- Mentions dans chaque message : LM MULTI-SERVICES + SIRET, origine du contact (fiche Google publique), "Répondez STOP".
- Suivi dans memoire\b2b.json (statuts : trouvé / maquette / envoyé / réponse / client / exclu).
- Résumé quotidien à Jarvis : nb envoyés, réponses, intéressés, STOP.
- Gmail : volume très bas (20-30/jour/boîte), sinon spam.

## Ordre de construction
1 Sourcing (fait) -> 9 Dev sites (en cours : prototype 3D) -> 2/3 Enrichissement+Qualification -> 4 Maquette (liée à Dev sites) -> 5 Rédaction -> 7 Réponses -> 6 Envoi -> 8 Relances. On ne démarche pas tant qu'un site validé par Liam n'existe pas.
