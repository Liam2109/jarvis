
## Addendum 27/10/2026 : recherche élargie (décision de Liam)
Liam élargit la recherche : **Suisse romande, Belgique francophone (Wallonie, Bruxelles), Luxembourg, et en général les pays francophones/proches**. Il dit « on s'en fout » des limites de zone en France pour les annonces SNCF : afficher TOUTES les offres fret/voyageurs en France, débutant accepté, avec un tag de distance (zone 1 à 4 = prioritaire, « hors zone » = affichée quand même, en gris), au lieu de les écarter.
À faire :
1. Zone « hors zone France » : ne plus écarter, afficher avec le tag. Garder écartés : allemand, tramway, bus, expérience exigée, autre employeur hors liste.
2. Ajouter des employeurs : SNCB / NMBS, Infrabel (si conduite), CFL (Luxembourg), plus ceux déjà listés. Ajouter Belgique (Wallonie, Bruxelles) et Luxembourg dans les filtres de lieu ; les offres néerlandaises (Flandre) restent écartées comme l'allemand.
3. Mettre à jour les tests silencieux en conséquence (Lille « hors zone » = gardée avec tag, offre allemande = écartée, Belgique francophone = gardée).
4. Sources : alertes Gmail existantes ; proposer à Liam des alertes e-mail à créer pour SNCB/CFL/jobup.ch/jobs.ch.
Les candidatures restent des BROUILLONS : Liam envoie lui-même (le clic « Postuler » sur les sites est à faire par lui).

## Réalisé (27/10/2026)
- Zone 5 « Hors zone (France) » : toute offre française hors des zones 1 à 4 est gardée, carte grise avec le champ Zone ; zone 6 « Belgique francophone / Luxembourg » (Wallonie, Bruxelles, Luxembourg). Flandre, Suisse alémanique, Allemagne : écartées (lieu). Titres allemands ET néerlandais : écartés (langue, compté avec « allemand »).
- Employeurs ajoutés : SNCB / NMBS, Infrabel, CFL (filtre + reconnaissance dans le texte des alertes).
- Tests mis à jour (`tests\emploi-conducteur.ps1`) : Lille gardée hors zone, Belgique / Luxembourg gardés, Flandre écartée, titre néerlandais écarté.
- Reste à faire par Liam : créer les alertes e-mail SNCB (sncb.be), CFL (cfl.lu), jobup.ch / jobs.ch ; leurs domaines d'expéditeur ne sont PAS encore dans la liste blanche de `lib\veille-mail.ps1` (`MailExpediteurs`) : à ajouter quand les alertes existent.
