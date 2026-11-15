---
name: agent-vente-relances
description: Fiche de rôle de l'agent Relances (pôle Vente, prévu, non construit) — relancer à J+3 et J+7 les prospects qui ont reçu un devis, brouillons écrits dans B2B/a-valider pour Liam. Contrat seulement ; à compléter.
---

# Agent Relances J+3 / J+7 — prévu

**Responsable :** Vente. **Script :** aucun (statut « prevu »). **Contrat :** `B2B/harness/contrats/vente-relances.json`.

## Mission
Relancer à J+3 et J+7 les prospects qui ont reçu un devis, brouillons écrits dans B2B/a-valider pour Liam.

## Contrat (ce qui est déjà fixé)
- Jours : lundi à vendredi, 08:00-19:00.
- Lit : `suivi-prospects.csv`, devis envoyés.
- Écrit : `B2B/a-valider/AAAA-MM-JJ-vente-relances.md` (brouillons ; Liam envoie).
- Discord : salon devis, 20 messages par jour au plus. `envoi_client: true` dans le contrat, mais `peut_engager: false` : rien ne part sans Liam.
- Interdit : envoyer au client sans accord de Liam, encaisser ou rembourser, publier, signer ou promettre un résultat, afficher un secret, plus de deux relances, relancer un STOP.
- Tests : aucun pour l'instant.

## Ordres pas à pas
À compléter par Liam (aucun script).

## Entrées et sorties détaillées
À compléter par Liam.

## Cas limites gérés
À compléter par Liam.

## Vérifier qu'il a bien tourné
À compléter par Liam. Avant activation : contrat valide, garde branchée, trace, test, skill (checklist de `B2B/docs/harness/README.md`).

## Quand il alerte Liam
À compléter par Liam.
