# To-do B2B — LM MULTI-SERVICES

_Dernière mise à jour : 9 nov. 2026, 19h33_

## En cours ce soir
- [ ] Sid appelle la liste "Lundi" (23 plombiers/électriciens) — colonne Constat remplie, Drive débloqué
- [ ] Mardi (61 coiffeurs) et jeudi (102 restaurants) — même traitement "Constat" à lancer

## Construit aujourd'hui (9 nov.)
- [x] Tableau de bord du matin (brief quotidien, publié + programmé 8h37 en semaine)
- [x] Pack tout-inclus Stripe (595€ + 20€/mois maintenance) — lien : https://buy.stripe.com/4gM5kEa6N08taHJc4g5EY05
- [x] Accès écriture Drive donné à Sid
- [x] Annonce apporteur d'affaires postée sur 8 groupes Facebook

## À construire — validé par Liam ce soir
- [ ] Modèles de messages post-appel pour Sid/apporteurs (évite de rédiger à chaque fois)
- [ ] Relance automatique des prospects sans réponse à J+3 (nécessite Jarvis, prompt Claude Code à fournir)
- [ ] Résumé du soir sur Discord (appels faits / RDV pris / revenu du jour)
- [ ] Tableau de bord "revenu" visuel, style futuriste sobre (page dédiée, mis à jour en direct)
- [ ] Paiement en 3x sans frais — à explorer via un partenaire (Alma/Floa), pas natif Stripe France

## En attente de décision Liam
- [ ] `veille_mail` = bon mapping pour "agent réponses" ? (question jamais tranchée)
- [ ] Programme de parrainage (1 mois de maintenance offert) — à ajouter au script d'appel si validé

## Pas encore construit (ancien backlog)
- [ ] Agent Devis vocal (devis + lien Stripe généré pendant l'appel)
- [ ] Jarvis → tâches automatiques sur Discord
- [ ] Relancer Jarvis sur le serveur (bot Discord) — à faire physiquement sur "le petit PC"
- [ ] Écouter le message vocal de Sid et y répondre

## Reprise du 13 nov. 2026 (soir) apres suppression d'une conversation Claude
Verifie dans les fichiers : DEJA FAIT = site vitrine luxe2 en production (12 nov.), INDEX.md + README par dossier (10 nov.), pont Discord (probable), sourcing elargi a la Normandie, boutons Stripe 595 EUR et 994 EUR.
Regle : tout prompt Claude Code se termine par la machine : « gros PC » ou « serveur Liam ».

### A faire, par priorite
- [ ] Bilan Sid (vendredi 13 nov.) : lui envoyer le message (appels, conversations, RDV, ou il remplit la feuille) ; feuilles du 10 et du 13 nov. vides ; puis une semaine de plus ou on passe a autre chose
- [ ] Lire les reponses prospects sur contact.lmsites et liamdigital2109 (Claude chat ne lit que emoliam255) ; reponses.py ou connecter ces comptes
- [ ] Malt : voir les candidats a l'annonce « Prospection telephonique B2B » (nouveaux chaque jour du 10 au 13 nov.), repondre a Eric Ling
- [ ] TRANSFERT VERS SERVEUR LIAM (docs\TRANSFERT-SERVEUR.md) : b2b.local.json = machine_active DESKTOP-OBKCBTL, agents_actifs vide, serveur false, donc tout s'arrete quand le gros PC est eteint. Etapes 1-2 sur le gros PC, 3-4 sur le serveur Liam (nom a relever avec $env:COMPUTERNAME)
- [ ] ARCHITECTURE « CEO JARVIS » : Jarvis (CEO) tourne 24/24 sur le serveur Liam ; base = organigramme du 3 nov. (Liam > Claude et Jarvis > domaines > departements) ; contenu des TikTok a redonner par Liam (perdu avec la conversation)
- [ ] ARCHITECTURE TYPE OBSIDIAN pour economiser les tokens : coffre = dossier Jarvis, INDEX.md = hub, notes courtes avec frontmatter et liens [[...]] ; a faire AVANT le reste
- [ ] Retrouver ou refaire : IDEES-B2B-10nov.md, REPRISE-10NOV-SOIR.md, TECHNIQUES-CLOSING.md, SCRIPT-CLOSING-LIAM.md, idees TikTok (introuvables sur le gros PC ; REGLES-LISTES-APPEL fusionne dans agents\appels-sid.md)
- [ ] Poster l'offre « page exemple a ton nom » dans les groupes Facebook de Normandie et sur Leboncoin
- [ ] Jeu de role de closing (« je dois reflechir », « trop cher », « pourquoi vous »)
- [ ] Mise en production des pages en apercu (Velin, Pala, electricien v1, plombier v3) quand Liam dit « deploie »
- [ ] Agent Devis, resume du soir sur Discord, relance J+3, tableau de bord revenu
- [ ] Recruter d'autres appelants (etudiants 15 %, specialiste restaurants, closers 10 %)
- [ ] Paiement en 3 fois sans frais, parrainage

## Mise a jour du 14 nov. 2026 (soir) - ordre voulu par Liam
- [x] Agent Instagram retire du serveur (commit 9cba427) ; tache Jarvis-B2B-instagram absente du serveur
- [x] Regles Claude dans CLAUDE.md (franchise, appels seulement, associe)
- [ ] Valider le skill « scripts-appel » (generateur, version non vendeur) avec Claude : 4 exemples + liste cochee a coller dans le chat
- [ ] Etape 1 : liste d'appels propre (un tableur par jour, supprime apres 7 jours, trie par heure, colonnes larges, lundi a vendredi, aucun dossier cree) - avant lundi 16 nov. pour Sid
- [ ] Etape 2 : regrouper les agents en 4 responsables (Prospection, Vente, Argent, Production plus tard) + une fiche de role par agent (= son skill), un agent a la fois
- [ ] Etape 3 : tableau de bord transparent style Apple, menu a gauche, clic sur un agent = sa fiche, ouvert comme une appli
- [ ] Gabarit commun pour creer les skills (entrees, procedure, regles, critere de fin, exemples)
- [ ] Demander a Sid les phrases exactes qui ont fait dire non
- [ ] Relances J+3 / J+7 et lead chaud (envois coupes, validation a la main)
- [ ] Skill de design de site, puis equipe design / code / publication (apres la 1re vente)
- [ ] Connecteur d'ecoute de reunions : nom a donner par Liam ; verifier gratuite et accord des participants
- [ ] CEO Jarvis autonome (resume Discord le soir) apres la 1re vente
- [ ] Stripe : SIRET en pied de facture, desactiver les anciens liens quand Liam dit « desactive »
- [ ] Serveur : netplwiz (ouverture de session automatique), secrets des agents s'il en manque
- [ ] Appels uniquement du lundi au vendredi ; jamais de presentiel

## Mise a jour du 14 nov. 2026 (apres-midi tardif)

Avant lundi 16/11, 8 h (ordre de priorite)
- [ ] Lancer sur le gros PC le prompt de correction de l'etape 1 (8 valeurs Resultat, regles de reprise, hors zone, melange des metiers, test reel du tableur Google, rangement des anciens liste-appels, .obsidian/graph.json)
- [ ] Valider les regles de reprise des appels (Pas de reponse = 3 tentatives, etc.)
- [ ] Decider les commissions : 10 % appelant + 10 % closer ? sur le premier paiement seulement ou aussi sur les 49 EUR/mois ?
- [ ] Sid : lire l'accroche a voix haute et donner les phrases exactes qui ont fait dire non
- [ ] Scripts d'appel : phrase des 49 EUR/mois avant le paiement, 1er mois offert, arret possible (site reste en ligne sans support) ; retirer l'ancien lien de reservation dans SCRIPT-APPEL-SID.md ; recreer TECHNIQUES-CLOSING.md et SCRIPT-CLOSING-LIAM.md (accord de Liam)
- [ ] Entrainement : jeu de role du plombier mefiant (autre conversation)

Ensuite
- [ ] Etape Vente : agents Reponses, Rendez-vous, Devis, Relances J+3/J+7, chacun avec sa fiche de role (prompt apres la revue de l'etape 1)
- [ ] Etape Argent : Alerte Stripe, Resume du soir, Alerte pannes
- [ ] Tableau de bord (maquette validee, voir IDEES-MASTER du 14/11 apres-midi tardif) : verre blanc/bleu, barre gauche au survol, courbes de la semaine, taux de closing, creneaux, refus, commissions, pipeline, agents en ligne (heure de derniere execution a ajouter dans agents-json.py)
- [ ] Fiche d'accueil client (photos, couleurs, logo, avis, specificites)
- [ ] Stripe : desactiver les anciens liens (acompte, solde, 2 liens du matin) quand Liam dit « desactive »
- [ ] Stripe : mention « TVA non applicable art. 293 B » + SIRET dans les reglages de facturation
- [ ] Domaine : titulaire = client, renouvellement annuel dans Stripe (plus tard), corriger le texte du produit de maintenance, clarifier « Playwork »
- [ ] Faire relire la formulation d'arret/resiliation et le droit de retractation (vente a distance)
- [ ] Prevoir comment livrer un site complet multi-pages avant d'en vendre un
- [ ] Skills du catalogue Claude : Liam colle les noms (Ventes, Contacts et prospects, E-mails et messages, Marketing, Sites web)
- [ ] Hebergement : Vercel Pro deja pris (ok pour l'usage commercial)

## Ajout du 14 nov. 2026 (soir)
- [ ] Plugin Codex dans Claude Code (gros PC, apres la fin du run en cours) : /plugin marketplace add openai/codex-plugin-cc ; /plugin install codex@openai-codex ; /reload-plugins ; /codex:setup ; connexion ChatGPT par Liam. Usage : seconde relecture des scripts qui touchent a l argent (agent Argent, alerte Stripe, devis). Pas de gain de CA avant la 1re vente.
- [ ] Stripe : reste le site web (encore ecom-quiz.vercel.app) et la description publique (ancien projet formation) a mettre sur LM MULTI-SERVICES. Nom public et libelle de releve : fait et verifie le 14/11.
- [ ] Activer Google Sheets API (console Google Cloud, projet du client OAuth) : sans ca, tableur de Sid sans liste Resultat ni en-tete fige.
- [ ] Serveur : git checkout -- .obsidian/graph.json une fois, puis zone --a-blanc puis zone (prompt lance le 14/11 17 h).
- [ ] Etape Vente : commencer par reparer reponses.py (caracteres de controle).

- [ ] Codex : plugin installe (v1.0.6) ; Liam dit avoir fait /reload-plugins et /codex:setup (non verifie). Usage : relire un script de l etape Argent. Ne pas donner de cle API.
- [ ] Skill detaille pour CHAQUE agent et responsable, en commencant par Jarvis (CEO) : mission, ordres, regles, ce qui demande la validation de Liam.
- [ ] Serveur : verifier la tache Jarvis-B2B-appels-sid (07:30), doublon Jarvis-AppelsSid, veille du PC, pourquoi pas de liste les 11 et 13/11. Plan de secours lundi 7 h 35 : Start-ScheduledTask Jarvis-B2B-appels-sid.
- [ ] Harness : brancher la garde, un contrat et un test sur chaque nouvel agent Vente (reponses, devis, relances J+3 et J+7) avant de l activer (checklist B2B/docs/harness/README.md).
