# Devis type, appel de 15 minutes et objections
Brouillon du 26 oct. 2026, à valider par Liam. Aucun lien de paiement Stripe n'est créé. Les points marqués **[à confirmer]** sont des propositions, pas des faits.

## 1. Devis type : Landing page pro, 595 €
**Émetteur :** Liam Emo, LM MULTI-SERVICES, SIRET [à compléter], téléphone [à compléter], e-mail [à compléter].
**Client :** [nom de l'entreprise, adresse, SIRET du client].
**Mention TVA :** [à vérifier avec le statut de LM MULTI-SERVICES : « TVA non applicable, art. 293 B du CGI » ou TVA à ajouter].

### Ce qui est livré (595 €)
1. Une page web unique, adaptée au mobile : en-tête avec métier, ville et numéro cliquable, barre d'appel fixe sur mobile, services, zone d'intervention, déroulé en étapes, questions fréquentes, formulaire de 4 champs maximum, mentions légales.
2. Textes rédigés à partir des informations du client. Les avis affichés sont uniquement de vrais avis, avec l'accord de leurs auteurs ; sans avis, la section n'apparaît pas.
3. Photos : celles du client ; à défaut, photos libres de droits légendées et licence notée.
4. Mise en ligne sur un lien de démonstration, puis sur le domaine du client si l'option domaine est prise.
5. Contrôles avant livraison : mobile et ordinateur, vitesse, accessibilité, formulaire testé.
6. **Une série de retouches incluse** : textes, photos, couleurs, horaires, regroupées en un seul envoi de modifications. Toute série supplémentaire, nouvelle page ou fonctionnalité fait l'objet d'un devis.

### Délai **[à confirmer]**
Mise en ligne sous [5 à 7 jours ouvrés] après réception du paiement et des éléments du client (logo, photos, textes ou réponses aux questions, accès au domaine si besoin). Le délai court à partir du dernier élément reçu.

### Options (chacune sur accord écrit du client)
| Option | Prix | Détail |
|---|---|---|
| Nom de domaine + réglages DNS | 40 € de prestation + prix coûtant du domaine (facturé au prix réel, montré avant achat) | Domaine, pointage vers l'hébergement, HTTPS. Le domaine est au nom du client **[à confirmer]**. |
| E-mail professionnel | [à décider] + prix coûtant de l'abonnement du fournisseur | Création de l'adresse (contact@domaine), réglages de sécurité (SPF, DKIM, DMARC). |
| Maintenance | 49 €/mois (hébergement, changements, sauvegarde, contrôle de disponibilité, support) | Sans engagement après [3] mois **[à confirmer]**. Pack unique décidé par Liam le 10 nov. 2026 (remplace la distinction 29 € / 49 € ci-dessous, résolue). |

### Paiement (décidé par Liam le 14/11/2026)
- Prix complet réglé en une fois à la commande, par le lien de paiement Stripe joint au devis (liens : `docs\KIT-RDV-15MIN.md` section 4). Aperçu privé validé par le client avant la mise en ligne.
- Aucune dépense (domaine, e-mail) n'est engagée avant l'accord écrit du client sur son prix.

### Rétractation et annulation (à faire relire avant le premier devis)
- Entre professionnels, il n'y a en principe pas de délai de rétractation légal. Mais un petit artisan peut être protégé comme un consommateur dans certains cas de vente hors établissement (démarchage, signature chez lui). **À faire valider par un juriste ou par la DGCCRF avant le premier envoi.**
- Proposition commerciale : annulation sans frais (remboursement complet) jusqu'au début du travail ; après, le travail réalisé reste dû **[à confirmer par Liam]**.
- Le devis est valable [30] jours. Il est accepté par retour de « Bon pour accord » daté et signé.
- Mentions à ajouter : propriété du site après paiement complet, droit sur les photos du client, protection des données (le formulaire envoie les messages au client uniquement).

## 2. Script de l'appel de 15 minutes
**Avant l'appel (2 min)** : ouvrir SA maquette, relire sa fiche (note, avis, zone). Ne rien affirmer que je n'ai pas vérifié.

| Minutes | Étape | Ce que je dis / fais |
|---|---|---|
| 0–1 | Ouverture | « Bonjour, Liam Emo, LM MULTI-SERVICES. Je vous appelle au sujet du message sur votre site web. Vous avez 15 minutes ? » Si non : proposer un autre créneau et arrêter. |
| 1–4 | Écouter | « Comment les clients vous trouvent aujourd'hui ? » « Vous recevez des demandes par quel canal ? » « Qu'est-ce qui vous manque aujourd'hui ? » Noter ses mots exacts. |
| 4–8 | Montrer sa maquette | Partager le lien : numéro cliquable, barre d'appel mobile, zone d'intervention, formulaire. Préciser : « C'est un exemple, ce n'est pas votre site officiel ; vos vraies informations remplaceraient les zones à remplacer. » |
| 8–11 | Proposer | « Landing page pro à 595 €, une page, une série de retouches incluse, délai [à confirmer]. En option : domaine, e-mail professionnel, maintenance. » Aucune promesse de classement Google ni de nombre de clients. |
| 11–14 | Objections | Voir la section 3. Écouter, reformuler, répondre en une ou deux phrases. |
| 14–15 | Clôture | Au choix : « Je vous envoie le devis par e-mail aujourd'hui », « Je vous rappelle [jour] », ou « Pas intéressé : je vous retire de ma liste (STOP) ». Noter le résultat dans `suivi-prospects.csv` (avec l'OK de Liam pour tout changement de statut). |

**Règles :** ne jamais mentir, ne jamais inventer d'urgence, accepter un « non » à la première réponse claire, traiter tout « STOP » immédiatement et définitivement.

## 3. Les 8 objections les plus fréquentes
Principe : écouter, reconnaître l'objection, répondre avec des faits vérifiables, proposer l'étape suivante. Jamais de chiffre inventé ni de promesse de classement Google.

1. **« J'ai déjà un site. »**
   Réponse : « Très bien. Je ne vous demande pas de le remplacer au téléphone. Regardez simplement la maquette : si votre site actuel fait déjà ce qu'elle fait (numéro cliquable sur mobile, formulaire, zone d'intervention), vous n'avez pas besoin de moi. Sinon, ça vous dit de comparer ? » *(Ne pas critiquer son site sans l'avoir vu.)*
2. **« C'est trop cher. »**
   Réponse : « Je comprends. 595 € est un tarif unique, sans abonnement obligatoire : une page, une série de retouches, la mise en ligne. Si un seul chantier obtenu par le site rembourse l'investissement, ça vaut le coup ; sinon, ne le faites pas. Je ne peux pas vous promettre ce chiffre. Vous préférez qu'on regarde ce qui compte vraiment pour vous ? » *(Pas de remise improvisée ; toute remise est décidée avant par Liam.)*
3. **« Je n'ai pas le temps. »**
   Réponse : « C'est justement pour ça que je fais le gros du travail. Il me faut une demi-heure de votre temps en tout : vos infos et vos photos. Le reste, c'est moi. On cale 15 minutes quand vous voulez ? »
4. **« Facebook me suffit. »**
   Réponse : « Facebook marche bien pour vos habitués. Un site à vous reste accessible même à quelqu'un qui n'a pas de compte, vous le contrôlez, et il porte votre numéro cliquable. Les deux se complètent. »
5. **« Je n'ai pas besoin de clients, j'ai déjà du travail. »**
   Réponse : « Tant mieux. Ce site sert aussi à choisir vos clients (zone, type de chantier) et à ne pas perdre un appel manqué pendant que vous êtes sur un chantier. Si votre carnet est plein, ne changez rien. »
6. **« Ça marchera sur Google ? »**
   Réponse : « Je ne promets aucun classement : personne ne peut honnêtement le faire. Ce que je garantis : un site rapide, lisible sur mobile, avec votre ville et votre métier clairement écrits. Le reste dépend de beaucoup de choses. »
7. **« Je dois en parler à mon associé / mon comptable. »**
   Réponse : « Bien sûr. Je vous envoie le devis par écrit pour que vous puissiez le leur montrer. Je vous rappelle [jour] ? »
8. **« Je ne connais pas votre société, je n'ai pas confiance. »**
   Réponse : « Normal. Voici mon identité : Liam Emo, LM MULTI-SERVICES, SIRET [à compléter]. Rien ne se paie avant le devis signé, la maquette est gratuite et sans engagement, et vous validez un aperçu privé avant toute mise en ligne. Vous pouvez aussi me répondre STOP et je ne vous recontacte plus. »

### À éviter, toujours
- Citer un nombre de clients, d'appels ou de visites gagnés (aucune mesure réelle à ce jour).
- Dire « première page Google », « n°1 », « garanti ».
- Créer une fausse urgence (« offre jusqu'à ce soir »).
- Relancer quelqu'un qui a dit STOP ou « non » clairement.

## 4. À valider par Liam (ordre)
1. ~~Prix et contenu des options : e-mail pro, différence 29 € / 49 €~~ : résolu le 10 nov. 2026, pack unique 49 €/mois tout compris (site, domaine, e-mail pro, hébergement, maintenance).
2. Délai de livraison et durée d'engagement de la maintenance.
3. ~~Schéma de paiement~~ : résolu le 14/11/2026, paiement en une fois avec le lien du prix complet.
4. Mention de TVA et texte juridique de rétractation (relecture).
5. Texte des 8 réponses et du script d'appel.
