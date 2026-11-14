---
agent: stripe-alerte
aliases: [💶 Alerte Stripe]
name: stripe-alerte
role: Alerte Discord dès qu'un nouveau paiement Stripe arrive (montant seulement)
machine: non planifié sur le serveur (absent de serveur-taches.json)
planification: tâche Windows propre toutes les 5 min, installée seulement par Liam (« installer --oui ») ; aucune sur le gros PC
depend_de: clé Stripe restreinte en lecture seule (Jarvis/.env, jamais affichée)
sorties: message Discord « Nouveau paiement Stripe »
---
# 💶 Alerte Stripe
Aucune action sur Stripe : ni remboursement, ni écriture. Jamais de nom, d'e-mail ni de carte dans l'alerte.
Détail : `B2B/agents/stripe-alerte.md`
Liens : [[liens-paiement]]
