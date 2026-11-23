---
name: agent-linkedin
description: Fiche de rôle de l'agent LinkedIn (pôle Prospection, EN SIMULATION et fermé jusqu'au « go linkedin » de Liam) — chaque jour ouvré à 07:45 sur le serveur, poste sur Discord 1 à 2 posts LinkedIn pour le profil personnel de Liam (texte brut à copier, ✅ valider, ❌ rejeter, 📌 publié) ; Liam valide puis colle lui-même, l'agent ne publie JAMAIS sur LinkedIn. À utiliser pour écrire un lot de posts, vérifier, corriger ou activer linkedin.py (importer, jour, valider, rejeter, publie, etat).
---

# Agent LinkedIn — un à deux posts par jour, validés et collés par Liam

**Responsable :** Prospection. **Script :** `B2B/agents/linkedin.py`. **Contrat :** `B2B/harness/contrats/linkedin.json`. **Note :** `docs/agents/💼 LinkedIn.md`.
**Tâche serveur :** `jour` à 07:45, lundi à vendredi (`B2B/agents/serveur-taches.json`, clé `desactive` tant que Liam n'a pas dit « go linkedin »).
**Pourquoi :** Liam recrute des appelants (15 %) et des closers (10 %) et cherche des artisans et commerçants locaux pour un site web. LinkedIn est son canal écrit ; l'agent lui évite d'y penser chaque matin, sans rien publier à sa place.

## Qui fait quoi
- **Claude (dans le chat)** écrit les posts, par lots d'environ 14 (7 recrutement + 7 prospect). **Aucun appel à une IA sur le serveur.**
- **Liam** colle le lot dans `B2B\linkedin\lot-AAAA-MM-JJ.md`, valide ou rejette chaque post sur Discord, **copie-colle lui-même sur LinkedIn**, puis réagit 📌.
- **L'agent** contrôle les lots, range les posts dans `B2B\linkedin\file.json`, poste les posts du jour sur Discord, relit les réactions de Liam, surveille le stock.

## Écrire un lot (consignes à Claude)
Format exact (un bloc `##` par post ; tout ce qui précède le premier `##` est ignoré) :

```
## Post 1
type: recrutement
statut: en file
texte:
Le texte du post, sur plusieurs lignes.

Écrivez-moi en message privé.
```

Un lot de 14 = 7 `recrutement` + 7 `prospect`. Règles que la garde fait respecter (un post qui les viole est **refusé à l'import** avec sa raison, les autres sont gardés) :
- **Ton** : vouvoiement, oral et direct. Jamais de tutoiement.
- **Ni emoji, ni image, ni lien, ni e-mail, ni téléphone, ni `@`, ni accent grave.** Au plus 3 hashtags (le mieux : aucun). Entre 150 et 1 500 caractères.
- **Aucun chiffre** hors : pack **595 €**, site complet **994 €**, **49 € par mois** (le mot « mois » dans la même proposition), commissions **15 %** pour les appelants et **10 %** pour les closers (le bon rôle dans la même proposition). Pas de date, pas de « 3 clients », pas de « en 48 h ». Le pack ne coûte pas 994 €, le site complet ne coûte pas 595 €.
- **Aucun témoignage inventé**, aucune citation, pas de « nos clients » / « mes clients » ; **aucune page exemple présentée comme un client**.
- **Aucune promesse de résultat ni de gain** (« garanti », « gagnez », « plus de clients », « revenu passif », « doubler »…).
- **Aucune phrase interdite** : la liste `phrases_interdites` de `OFFRE-REFERENCE.json` (lue par la garde, jamais recopiée ici).
- **Rien de présentiel** (appels seulement : jamais « passer vous voir », « en boutique », « rencontrer »).
- **Appel à l'action unique, en dernière ligne, une seule fois** : « Écrivez-moi en message privé. » Aucun autre (« contactez », « réservez », « commentez », « lien en commentaire »…).
- `recrutement` : parle des appelants et/ou des closers. `prospect` : parle d'un site web pour artisans ou commerçants, sans recrutement ni commission.

## Ordres pas à pas (lus dans le script)
1. `M.exiger("linkedin", ...)` : refuse hors de la machine active (sauf `--essai`).
2. **Import** : chaque `lot-*.md` est lu ; un post conforme est rangé `en file` (identifiant = 8 caractères du texte, jamais deux fois le même texte) ; un post refusé ou un bloc mal formé est signalé, les autres passent. Un lot avec refus déclenche **un** message Discord par jour.
3. **Réactions** (✅ ❌ 📌) des posts proposés depuis moins de 7 jours : **seules celles posées par Liam comptent** (ni le bot, ni un autre compte). ❌ gagne sur ✅. ✅ → `prêt`. 📌 → `publié` (la date est au journal). Discord illisible : rien ne change et aucun post n'est déclaré non validé à tort.
4. **Non validé** : un post proposé un jour précédent sans ✅ ni ❌ passe `non validé`, signalé **une seule fois**. **Il ne repart jamais seul** : Liam le valide (✅ ou `valider ID`) ou le rejette.
5. **Posts du jour**, en alternance stricte : un `recrutement` (créneau 08:30) puis un `prospect` (12:30) ; `posts_par_jour = 1` alterne un par jour. Chaque post est un message : texte dans un bloc à copier, puis les boutons ✅ ❌ 📌 posés par le bot. Si un type manque, rien n'est posté à sa place. Un texte modifié à la main dans `file.json` est recontrôlé : s'il viole une règle, il est écarté et n'est jamais envoyé.
6. **Stock** : moins de 3 jours de posts après le passage = **code 5**, trace en erreur (le surveillant la signale) et message « demande un nouveau lot à Claude ».
7. Journal `B2B/agents/linkedin-journal.log` : une ligne par fait (`proposé`, `prêt`, `publié` avec sa date, `rejeté`, `non validé`). Aucun secret.

## Ce qu'il ne fait jamais
Publier sur LinkedIn (aucune API, aucune automatisation du site) ; reproposer un post non validé ; lire la réaction d'un autre compte ; appeler Claude ou une IA ; contacter un prospect, un client ou Sid ; afficher un jeton ; engager Liam (`peut_engager: false`).

## Ordres (depuis la racine Jarvis)
| Ordre | Commande |
|---|---|
| Contrôler un lot sans rien écrire | `python B2B\agents\linkedin.py importer --essai` |
| Ranger les posts conformes dans la file | `python B2B\agents\linkedin.py importer` |
| Voir ce que le passage posterait (rien écrit, rien posté) | `python B2B\agents\linkedin.py jour --essai` |
| Passage du jour (réel seulement si `envoi_automatique` est `true`) | `python B2B\agents\linkedin.py jour` |
| Décider à la main | `python B2B\agents\linkedin.py valider ID` · `rejeter ID` · `publie ID` |
| File, stock en jours, posts en attente | `python B2B\agents\linkedin.py etat` |

## Ouvrir l'agent (Liam seul, après « go linkedin »)
1. Retirer la clé `desactive` de l'entrée `linkedin` de `B2B/agents/serveur-taches.json`.
2. Ajouter `linkedin` à `agents_actifs` dans `B2B/agents/b2b.local.json` (sur le serveur).
3. `envoi_automatique` à `true` dans `B2B/agents/linkedin-config.local.json` (hors git). Tant qu'il est `false`, `jour` reste une simulation : il affiche et n'écrit rien.
4. Facultatif : `salon_nom` (même fichier local) pour un salon dédié ; vide = salon B2B habituel des autres agents.
Les lots `B2B\linkedin\lot-*.md` sont versionnés (poussés avec git pour arriver sur le serveur) ; `file.json` ne l'est jamais.

## Vérifier (pas de preuve = pas de fait)
- `python tests\agents\test_linkedin.py` : lot, règles de contenu, alternance, réactions de Liam seul, non-validé jamais reproposé, stock, simulation sans écriture, aucune IA. Puis `python B2B\harness\valider.py`, `python B2B\harness\generer-fiches.py --verifier` et `tests\b2b-rapide.ps1`.
