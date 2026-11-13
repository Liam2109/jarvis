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
