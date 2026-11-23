# Carte des relais entre agents (23/11/2026)

**Règles de Liam (23/11)**
1. Messages et relances partent seuls ; tout ce qui touche à l'argent (devis, lien Stripe, paiement, remboursement) reste à la validation de Liam.
2. Quand un humain doit agir (Sid, un closer, Liam) : message Discord avec son nom, l'action à faire et l'échéance.
3. Après un paiement : Claude Code construit le site depuis la fiche du client, Liam valide avant la mise en ligne.
4. Un agent qui échoue essaie de se corriger seul sans rien casser, sinon il alerte Liam.
5. Visibilité : une ligne par relais dans le dashboard, une alerte Discord par événement important, un résumé le soir.

| Événement | Voit (cadence) | Écrit | Lit ensuite | MANQUE |
|---|---|---|---|---|
| Réponse de prospect | reponses (15 min) | suivi-prospects.csv (répondu/refusé/STOP), exclus-emails.json, Discord « 🚨 PRIORITÉ » + 3 créneaux non réservés | Liam seul ; rédaction saute les exclus | Rien ne répond au prospect (agent en lecture seule) ; registre non mis à jour ; pas d'échéance dans l'alerte |
| Rendez-vous | rendez-vous (5 min, iCal) | rendez-vous-etat.json, Discord rdv (nouveau, déplacé, annulé, rappel 30 min) | Liam ; superviseur-vente (échecs) | Aucun lien RDV ↔ prospect (statut non posé) ; pas de fiche pré-RDV ; rien au prospect ; pas de « devis à faire » après le RDV |
| Devis | devis (3 min) sur ordre de Liam (« devis : … » Discord) | B2B\devis\DEV-*.txt/pdf, devis-etat.json, aperçu Discord, « ok devis » de Liam | superviseur-vente (prix = OFFRE-REFERENCE) | Jamais déclenché par un RDV ; statut suivi-prospects « devis/signé » écrit par personne ; « envoyé/accepté/payé » cochés à la main |
| Paiement | stripe-alerte (5 min, lecture seule) ; resume-sid 19:30 (CA du jour) | stripe-alerte-etat.json, Discord (montant, devise, description) | superviseur-vente (argent : alerte seulement) ; chiffres-serveur | Paiement non rattaché à un devis ni à un client (aucun nom) ; devis jamais « payé » ; rien ne démarre la suite |
| Livraison du site | AUCUN agent | — | superviseur-sites lit le dépôt, mais il est désactivé | Fiche client, file « à construire », fiche B2B\a-valider\AAAA-MM-JJ-livraison.md, Discord à Liam (nom, action, échéance), validation avant mise en ligne |
| Lead chaud de Sid | appels-sid 07:30 puis relances 08:30 ; resume-sid 19:30 | Registre (pour=Liam, retour), alerte Discord 1× par lead, relances-etat.json, message « À rappeler aujourd'hui » | Liam | appels-liam est désactivé (18/11) : le registre alimente donc aucune liste ; relances relit les feuilles, pas le registre (calendriers différents : J+3 et 3e jour ouvré) ; résultat du rappel de Liam lu nulle part |
| Candidat appelant | alerte-candidatures (5 min) | Discord + brouillon, relance à 2 h, colonne « Contacté » | Liam ; panne-alerte | Verrou go_alerte fermé tant que Liam n'a pas écrit « go alerte » ; réponse au candidat jamais envoyée (canal d'envoi inexistant) ; pas de lien vers le RDV de 15 min |

**Manques transverses** : aucun des agents lus n'écrit de « ligne de relais » pour le dashboard (règle 5) ; aucune alerte ne porte le nom de l'humain ni l'échéance (règle 2) ; seuls les superviseurs corrigent seuls, et uniquement l'inoffensif (règle 4).

**3 maillons à relier en premier (par effet sur les ventes)**
1. Réponse positive → réponse automatique au prospect (créneaux de 15 min, message seul) + statut et registre à jour + Discord avec échéance : c'est la vente la plus proche, aujourd'hui elle attend Liam ; vérifier d'abord la portée d'envoi de gmail_api.py.
2. Lead chaud de Sid → une seule file pour Liam : relire le registre dans relances (ou rouvrir appels-liam après correction des fausses alertes Panne), alerte avec nom, téléphone, jour de rappel, puis lire le résultat.
3. Paiement → fiche client + livraison : stripe-alerte propose le rattachement au devis dans a-valider, Liam valide, puis Claude Code construit le site et Liam valide avant la mise en ligne.
