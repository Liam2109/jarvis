---
name: agent-gardien
description: Fiche de rôle de l'agent Gardien de l'architecture (rattaché à Jarvis CEO, FERMÉ jusqu'au « go gardien » de Liam) — chaque dimanche à 21:00 sur le serveur, vérifie doublons, agents muets depuis 14 jours, liens cassés, fiches orphelines et échanges de fichiers entre agents ; corrige seul le réversible, archive (jamais supprime) un agent inutilisé depuis 30 jours, attend le « go » pour tout ce qui envoie, publie ou encaisse. À utiliser pour vérifier, corriger ou activer gardien.py (passage, etat, restaurer).
---

# Agent Gardien de l'architecture

**Responsable :** Jarvis (CEO). **Script :** `B2B/agents/gardien.py`. **Contrat :** `B2B/harness/contrats/gardien.json`. **Tâche serveur :** `passage`, dimanche 21:00.
**Génère :** `B2B/harness/architecture.py` (page Architecture du tableau de bord, carte et fiches de 3 lignes dans `docs\COMMENT-CA-MARCHE.md`).

## Ordres
1. Script gratuit : agents muets (14 j), échanges de fichiers absents, doublons suspects, liens cassés, fiches pas à jour, contradictions contrat / planification, archivage.
2. Une seule passe `claude -p` (Sonnet 5.5, sans outil) si des doublons sont suspects : elle juge, elle ne corrige rien.
3. Corrige seul : liens, fiches, carte, redémarrage (liste fermée `REDEMARRABLES`), archive un agent sans tâche ni test ni contrat qui l'exige (inactif 30 j).
4. Tout le reste : fiche `B2B\a-valider\AAAA-MM-JJ-gardien.md` et attente du « go ». Rapport Discord de 10 lignes au plus ; gros problème en tête.
5. Restaurer un agent archivé : `python B2B\agents\gardien.py restaurer <agent>` (fiche, copie de skill et lien remis ; puis `generer-fiches.py`).

## Ne fait jamais
Écrire à un prospect, publier, encaisser, toucher `envoi_automatique` ou un réglage d'envoi, réécrire un lien de `docs\decisions`, supprimer un agent, ouvrir son propre verrou (`go_gardien`).
