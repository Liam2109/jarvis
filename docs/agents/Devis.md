---
agent: devis
aliases: [Devis]
name: devis
role: Préparer le devis écrit (texte + PDF) et son message avec le lien de paiement du prix complet ; aperçu « à valider » pour Liam
machine: serveur DESKTOP-HLQSTAU (si listé dans agents_actifs)
planification: toutes les 3 min (serveur-taches.json, commande « jour »)
depend_de: agent-rendez-vous
sorties: B2B/devis/DEV-AAAA-NNN.pdf, .txt, -message.txt ; devis-etat.json
---
# Devis
N'envoie jamais rien au client ; `envoi_automatique` = false (Liam valide les 3 premiers à la main).
Détail : `B2B/agents/devis.md` · liens : liens de paiement
Liens : [[docs/decisions/Sans acompte|Sans acompte]] · [[DEVIS-ET-OBJECTIONS]]
