---
name: scripts-appel
description: Générer le script d'appel d'une entreprise (tout métier, même inconnu) à partir de son nom, sa ville, son métier et sa fiche Google. Deux versions : Sid (obtenir un échange de 15 min) et Liam (conclure). Ton humain, calme, jamais vendeur. À utiliser pour toute demande de script d'appel, de liste d'appels commentée ou de réponse à une objection au téléphone.
---

# Scripts d'appel (LM MULTI-SERVICES)

## Pourquoi ce skill existe
Les premiers scripts faisaient trop vendeur : Sid a reçu un non catégorique à chaque appel. Un bon appel ressemble à quelqu'un du coin qui pose une question, pas à un argumentaire. Ce skill produit cet appel-là, pour n'importe quel métier.

## Quand l'utiliser
- Liam ou Sid demande « le script pour [entreprise] », une liste d'appels avec scripts, ou une réponse à une objection entendue au téléphone.
- Pas pour un e-mail ni un message écrit (autres règles), pas pour un rendez-vous en personne : **appels seulement, jamais de présentiel**, du lundi au vendredi.

## Entrées
| Entrée | Exemple | Si absente |
|---|---|---|
| [NOM] | Le Petit Comptoir | demander, ne jamais inventer |
| [VILLE] | Darnétal | demander |
| [MÉTIER] | restaurant | demander |
| [DÉTAIL FICHE] | pas de site ; 4,6 sur 120 avis ; photos ; horaires | **ne rien citer** de la fiche, ne rien supposer |

## Procédure
1. Lire `metiers.md` : trouver la fiche du métier. Métier absent : appliquer la règle « métier inconnu » en bas de ce fichier-là et écrire en une ligne la famille choisie.
2. Lire `structure.md` et remplir les deux versions (Sid, puis Liam) avec le vocabulaire du métier.
3. Le détail de la fiche n'est repris **que s'il est fourni**, mot pour mot (un chiffre fourni peut être cité, jamais arrondi ni embelli).
4. Ajouter les 3 objections les plus probables pour ce métier, tirées de `objections.md` et adaptées (pas les six à chaque fois).
5. Passer la **boucle de contrôle** ci-dessous sur chaque version. Rendre seulement quand tout est coché.

## Règles « pas vendeur » (obligatoires, les deux versions)
1. La première phrase parle d'eux ou de leur situation (leur fiche, leur métier), jamais de nous ni de notre offre.
2. On reconnaît tout de suite qu'on dérange : « je vous prends 30 secondes, vous me dites si ça tombe mal ».
3. **Mots interdits** : prix, tarif, euro, €, offre, promo, opportunité, solution, propose/proposer, incroyable, gratuit, garanti, référencement, SEO, conversion, landing, visibilité, digital, booster. Dans la version Liam, le prix est permis **seulement** dans la réponse à « c'est combien ? ».
4. Une seule question de découverte, vraie et facile, puis **se taire et écouter**. Les seules autres questions permises : demander le créneau du rendez-vous (Sid) ou l'adresse e-mail du devis (Liam).
5. Le rendez-vous est un échange de 15 min, en visio, sans engagement, jamais une vente.
6. Un « non » est accepté avec le sourire. Une seule relance douce au plus, et **aucune** si le non est net ou si la personne dit « ne rappelez pas » (noter « ne pas rappeler »).
7. Phrases courtes, langage parlé, vouvoiement, pas de jargon.
8. Argument central : être trouvé et appelé par les gens qui cherchent ce métier sur leur téléphone. On décrit ce que fait la page (bouton d'appel, horaires, photos, adresse), on ne promet aucun résultat.
9. Aucune fausse promesse, aucun témoignage ou client inventé, aucun chiffre non fourni, aucune fausse urgence, jamais se faire passer pour Google ou un organisme officiel.
10. Phrases neutres pour la personne qui appelle (pas d'accord au masculin ou au féminin : « j'ai vu » plutôt que « je suis tombé »).

## Contexte business (à ne pas réinventer)
- LM MULTI-SERVICES, près de Rouen. Sid prend le rendez-vous (commission 15 %) ; Liam conclut.
- Lien de réservation (Sid) : https://calendar.app.google/kmCmw8PKKkK7pjMn6
- Version Liam seulement, à la demande : page web 595 € ; site complet 994 € (lien Stripe prêt) ; maintenance facultative 49 €/mois (site, domaine, e-mail pro, hébergement). Pas d'acompte : le devis écrit contient le lien de paiement du prix complet, réglé en une fois ; aperçu privé validé par le client avant toute mise en ligne.
- Sources : `B2B/docs/KIT-RDV-15MIN.md` (déroulé du rendez-vous, liens de paiement), `B2B/docs/DEVIS-ET-OBJECTIONS.md` (devis, objections), décisions `docs/decisions/📌 Offre 595 + 49.md` et `📌 Sans acompte.md`. Si elles changent, elles priment sur ce skill.

## Format de sortie
```
### [NOM] — [MÉTIER], [VILLE]
Fiche citée : [détail fourni, ou « rien de fourni, rien cité »]
Meilleur moment d'appel : [tiré de metiers.md]

#### Version Sid (objectif : un échange de 15 min)
1. Accroche (≤ 45 mots, ~18 s) — 3 phrases
2. La question — 1 phrase, puis silence
3. Après sa réponse — reprendre ses mots, puis le rendez-vous
4. Si oui — 2 créneaux, nom de l'entreprise, e-mail, confirmation à voix haute
5. Si non — sortie polie (+ relance douce unique si le non est hésitant)
Objections probables : 3, réponses version Sid

#### Version Liam (objectif : conclure)
(mêmes étapes 1-2-5) + reformulation, ce que fait la page, devis par e-mail avec lien de paiement
Si « c'est combien ? » : la phrase de prix
Objections probables : 3, réponses version Liam

#### Contrôle
| | Sid | Liam |
| (a) … (f) | ✅/❌ | ✅/❌ |
```

## Boucle de contrôle (ne rien rendre avant que tout passe)
Relire chaque version, point par point :
- (a) La première phrase est-elle centrée sur eux (leur fiche, leur commerce, leur métier), sans « nous », sans notre offre ?
- (b) Aucun mot interdit (règle 3) ? Version Liam : le prix n'apparaît que dans la réponse à « c'est combien ? ».
- (c) Une seule question de découverte ?
- (d) Moins de 20 secondes avant la question : **45 mots au plus** avant elle (débit calme ≈ 2,5 mots par seconde) ?
- (e) Sortie « non » polie prévue, avec au plus une relance douce ?
- (f) Aucune promesse de résultat, aucun chiffre, avis ou client qui n'a pas été fourni ?

Un seul point en échec : réécrire la version et recommencer toute la liste. Montrer la liste cochée avec le script.
