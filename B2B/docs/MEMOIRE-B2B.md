# Mémoire B2B : état actuel (15 nov. 2026)
Seulement l'état présent ; le récit du passé est dans git et dans `JOURNAL-B2B.md`. Ancienne version : `B2B\donnees\sauvegardes\MEMOIRE-B2B-2026-11-15.md` (hors git).

## Identité
- Liam Emo, LM MULTI-SERVICES (micro-entreprise), SIRET 101 839 033 00012, TVA non applicable (art. 293 B du CGI). Coordonnées publiques dans `agents\identite.json`.
- Site vitrine : https://lmlsmulti-services.com (version luxe2, Netlify, en production depuis le 12/11). Sources dans `sites/agence/`.

## Offre (référence unique : `docs\OFFRE-REFERENCE.json`)
- Pack landing page 500 € ou site complet 994 €, payés en une fois, puis 29 €/mois (hébergement, maintenance, support, nom de domaine au nom du client), premier mois offert, arrêt possible à tout moment.
- Sans acompte : le lien Stripe du prix complet part avec le devis (2 liens seulement, voir `liens-paiement.md`).
- À l'arrêt des 29 €/mois : le site reste en ligne tel quel, le client garde son domaine, plus de modification ni de support.
- Hébergement des pages : Vercel (plan Pro). Aucune offre gratuite.

## Parcours de vente
- Appels uniquement, jamais de présentiel, du lundi au vendredi. Sid (appelant) obtient un rendez-vous visio de 15 min ; Liam conclut.
- Puis devis (agent Devis, validé par Liam), puis paiement Stripe.
- Listes d'appels : Sid 100 lignes chaque jour ouvré à 07 h 30 (créneaux 08 h-19 h) ; Liam 15 lignes à partir du 17/11 ; registre commun sans doublon.

## Règles permanentes
- Rien n'est envoyé, déployé, publié ni dépensé sans l'accord de Liam ; ce qui l'engage est écrit dans `B2B\a-valider\`. Kill-switch : `B2B\STOP`.
- STOP ou refus = exclusion définitive de toutes les listes.
- Prospection B2B (CNIL) : objet lié à la profession, identité de l'expéditeur, origine du contact, opposition simple ; pas de pixel de suivi. Pas un avis juridique.
- Aucun faux chiffre, faux avis, promesse de classement Google ni fausse urgence.
- Pages exemples : `noindex`, mention « exemple, pas votre site », jamais l'adresse personnelle de Liam ; déploiement par Claude quand Liam dit « ok vercel ». Bistro et céramique validés : ne pas les modifier.

## Pages exemples en ligne
- Une page par métier dans `agents\liens-metiers.json` : plombier-chauffagiste, électricien, restaurant, coiffeur, fleuriste, boulangerie, garage.
- Aperçus récents en attente du « déploie » de Liam : coiffeur Velin, pizzeria Pala.

## Agents et machines
- Les agents B2B tournent sur le serveur DESKTOP-HLQSTAU (mise à jour par git, tâche Jarvis-MajAuto) ; le gros PC ne fait que le travail avec Claude Code.
- Organisation : Jarvis (CEO), responsables Prospection, Vente, Argent, Production ; une fiche par agent dans `docs\agents\`, un contrat dans `B2B\harness\contrats\`.
- Prospection par e-mail : 2 boîtes Gmail API, `envoi_automatique` false, `prospection_actif` « non ».
- Agent Rendez-vous arrêté tant que l'adresse iCal secrète n'est pas dans sa config locale.
- Pas encore construits : Relances J+3/J+7, Production.

## Questions ouvertes
Voir `TODO-B2B.md` (rétractation, commissions, acompte, site complet multi-pages).
