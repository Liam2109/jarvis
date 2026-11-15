---
tags: [organigramme]
---
<!-- GENERE:DEBUT (régénéré par python B2B\harness\generer-fiches.py : ne pas modifier) -->
# Organigramme B2B

Généré depuis les contrats (`B2B/harness/contrats`). Liam décide ; Jarvis (CEO) pilote ; chaque responsable pilote ses agents.

- Liam
  - [[jarvis-ceo|Jarvis (CEO)]]
    - [[panne-alerte]] (actif, rattaché directement à Jarvis)
    - [[resume-sid]] (actif, rattaché directement à Jarvis)
    - [[surveillant]] (actif, rattaché directement à Jarvis)
    - [[responsable-prospection|Responsable Prospection]]
      - [[appels-sid]] (actif)
      - [[instagram]] (arrêté)
      - [[prospection]] (actif)
    - [[responsable-vente|Responsable Vente]]
      - [[devis]] (actif)
      - [[rendez-vous]] (actif)
      - [[reponses]] (actif)
      - [[vente-relances]] (prévu)
    - [[responsable-argent|Responsable Argent]]
      - [[stripe-alerte]] (actif)
    - [[responsable-production|Responsable Production]]
      - [[page-exemple]] (arrêté)
      - [[production]] (prévu)

```mermaid
flowchart TD
  liam["Liam"] --> ceo["Jarvis (CEO)"]
  ceo --> panne_alerte["panne-alerte (actif)"]
  ceo --> resume_sid["resume-sid (actif)"]
  ceo --> surveillant["surveillant (actif)"]
  ceo --> r_prospection["Responsable Prospection"]
  r_prospection --> appels_sid["appels-sid (actif)"]
  r_prospection --> instagram["instagram (arrêté)"]
  r_prospection --> prospection["prospection (actif)"]
  ceo --> r_vente["Responsable Vente"]
  r_vente --> devis["devis (actif)"]
  r_vente --> rendez_vous["rendez-vous (actif)"]
  r_vente --> reponses["reponses (actif)"]
  r_vente --> vente_relances["vente-relances (prévu)"]
  ceo --> r_argent["Responsable Argent"]
  r_argent --> stripe_alerte["stripe-alerte (actif)"]
  ceo --> r_production["Responsable Production"]
  r_production --> page_exemple["page-exemple (arrêté)"]
  r_production --> production["production (prévu)"]
```
<!-- GENERE:FIN -->

## Notes de Liam

_Zone libre, conservée telle quelle à chaque régénération._
