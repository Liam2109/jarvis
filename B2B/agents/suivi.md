# Agent suivi
Rôle : tenir `suivi-prospects.csv` : où en est chaque prospect, quand relancer. Il ne change JAMAIS un statut tout seul : seule la commande `statut`, lancée à la demande de Liam, le fait.

## Fichier `suivi-prospects.csv` (séparateur `;`)
`nom ; metier ; ville ; email ; telephone ; statut ; date_statut ; date_envoi ; relance_j2 ; maquette ; note ; historique`
Statuts : **à contacter · envoyé · répondu · maquette envoyée · devis · signé · refusé · STOP**.
- `relance_j2` : posée à date d'envoi + 2 jours quand le statut passe à « envoyé » ou « maquette envoyée » ; effacée pour tout autre statut.
- `STOP` : exclusion définitive. Plus aucun message, y compris par une autre source ou une autre campagne. L'agent Rédaction saute ces prospects ; « refusé » aussi.
- `historique` : chaque changement (date, ancien -> nouveau) est ajouté, rien n'est effacé.

## Commandes
| Commande | Effet |
|---|---|
| `python agents\suivi.py init prospects.csv` | ajoute les prospects absents en « à contacter ». Ne touche à aucun statut existant. |
| `python agents\suivi.py statut "Nom" "envoyé" [--ville V] [--date AAAA-MM-JJ] [--note "…"]` | change UN statut, à la demande de Liam. |
| `python agents\suivi.py a-relancer` | liste (lecture seule) les « envoyé » dont la relance est due. Ne prépare ni n'envoie rien. |
| `python agents\suivi.py liste [statut]` | affichage. |

## Ce que l'agent fait seul / ce qui demande Liam
- Seul : `init` (nouveaux prospects), `a-relancer`, `liste`, résumé pour Jarvis (nb par statut, relances dues).
- Liam : tout changement de statut. Après un envoi réel, Liam dit « Zeta est envoyé » et l'agent lance `statut`.
- Jamais : envoyer, relancer lui-même, passer un prospect en STOP sans demande, supprimer une ligne.
- Relance : le brouillon de relance (J+2, puis J+7 et J+14 de l'architecture) viendra de l'agent Relances, à valider.

## Clients et prospects suivis
Voir `suivi-prospects.csv`.

## Demandes en cours
| Date | De qui | Demande | État (à faire / en cours / à valider / fait) |
|---|---|---|---|
| 2026-10-24 | Liam | Fichier de suivi + script (statut seulement à sa demande) | fait (testé sur 3 prospects fictifs) |

## Décisions de Liam
- 24 oct. 2026 : statuts à contacter / envoyé / répondu / maquette envoyée / devis / signé / refusé / STOP ; dates ; relance J+2 ; le script ne change un statut qu'à sa demande.
