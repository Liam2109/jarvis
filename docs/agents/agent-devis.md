---
name: devis
role: Préparer le devis écrit (texte + PDF) et son message avec le lien de paiement du prix complet ; aperçu « à valider » pour Liam
machine: serveur DESKTOP-HLQSTAU (si listé dans agents_actifs)
planification: toutes les 3 min (serveur-taches.json, commande « jour »)
depend_de: "[[agent-rendez-vous]]"
sorties: B2B/devis/DEV-AAAA-NNN.pdf, .txt, -message.txt ; devis-etat.json
---
# Agent devis
N'envoie jamais rien au client ; `envoi_automatique` = false (Liam valide les 3 premiers à la main).
Détail : [[B2B/agents/devis.md|doc de l'agent]] · liens : [[B2B/docs/liens-paiement.md|liens de paiement]]
Liens : [[jarvis-ceo]] · [[decision-sans-acompte]] · [[decision-offre-595-49]] · [[decision-validation-manuelle]]
