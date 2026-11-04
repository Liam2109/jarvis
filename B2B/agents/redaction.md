# Agent rédaction
Rôle : écrire, pour chaque prospect, un brouillon de message court (e-mail + version LinkedIn) lié à son activité et à sa ville, avec le lien de SA maquette. Brouillons seulement. Il n'envoie rien, jamais.

## Entrées / sorties
- Entrées : `prospects.csv` (colonnes lues : nom, metier, ville, telephone, email, site_actuel ; facultatif : `note_besoin`, `email_type`, `email_source`, `source`, `fictif`), `agents\identite.json` (Liam Emo, LM MULTI-SERVICES, SIRET, téléphone, e-mail de réponse, adresse de base des maquettes), `suivi-prospects.csv` (les STOP et refusés sont sautés), les maquettes de `sites\public\`.
- Sortie : `messages-a-valider.md` : un bloc par prospect, statut « à valider », avec contrôles (⚠ / ℹ) et deux textes. Une régénération conserve les statuts que Liam a changés dans le fichier.
- Commande : `python agents\redaction.py prospects.csv` (après `python sites\moteur\generer.py prospects.csv`).

## Structure du message (e-mail)
1. Objet clair : « <Nom> : une maquette de site pour votre activité à <ville> ». Jamais de « Re: », jamais d'urgence inventée.
2. « Qui je suis » : Liam Emo, LM MULTI-SERVICES, SIRET.
3. Accroche liée au métier et à la ville (phrase par métier, sans chiffre).
4. Constat : uniquement ce qui est écrit dans `note_besoin` (fait vérifié à la main). Sans note et sans site dans le CSV : « je n'ai pas trouvé de site rattaché à votre fiche », signalé « à vérifier ». Si le prospect a un site que personne n'a vérifié : aucune affirmation.
5. Lien de sa maquette + ce qu'elle montre + « ce n'est pas votre site officiel, c'est un exemple ».
6. Appel à l'action simple : répondre ou appeler.
7. Pied : pourquoi ce message (origine du contact) + ligne STOP.

## Interdits (contrôlés par le script)
Chiffre ou pourcentage inventé, prix, « classement », « première page », « n°1 », « garanti », « référencement », fausse urgence, faux avis, affirmation non vérifiée sur le site du prospect. Le script signale tout mot interdit trouvé.

## Contrôles affichés dans chaque bloc
Prospect fictif · maquette absente · lien non actif (projet Vercel non déployé) · identité incomplète (SIRET, téléphone, e-mail de réponse) · pas d'e-mail · e-mail nominatif ou sans source · « pas de site » non vérifié · ligne STOP · mots interdits. Un bloc avec ⚠ est « à corriger avant envoi ».

## Ce que l'agent fait seul / ce qui demande Liam
- Seul : brouillons, contrôles, regénération.
- Liam : relire et valider chaque bloc, remplir `identite.json`, vérifier les constats, décider de l'envoi (agent Envoi, après son OK par lot).
- Jamais : envoyer, contacter, créer un compte, inventer un fait.

## Clients et prospects suivis
Voir `suivi-prospects.csv` (agent Suivi).

## Demandes en cours
| Date | De qui | Demande | État (à faire / en cours / à valider / fait) |
|---|---|---|---|
| 2026-10-24 | Liam | Script de rédaction + `messages-a-valider.md` | fait (testé sur 3 prospects fictifs) |

## Décisions de Liam
- 24 oct. 2026 : message court (e-mail et LinkedIn) avec accroche liée à l'activité et à la ville, ce qui manque sur le site actuel, lien de SA maquette, « Qui je suis » (Liam Emo, LM MULTI-SERVICES), ligne STOP. Pas de faux chiffres, pas de promesse de classement Google. Aucun envoi.
- 29 oct. 2026 : e-mail plus court, sans détails sur l'âge du site ; une seule proposition : appel ou Google Meet de 15 min (créneau par réponse, ou appel au numéro), ou échange par e-mail. Gabarit dans redaction.py › corps_email. Toujours : lien exemple « pas votre site », mention d'origine, ligne STOP, pas de prix, pas de promesse Google.
