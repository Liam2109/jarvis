---
name: agent-rendez-vous
description: Fiche de rôle de l'agent Rendez-vous (pôle Vente) — annonce sur Discord chaque rendez-vous de 15 minutes nouveau, déplacé, annulé, et un rappel 30 minutes avant, lu dans l'agenda iCal. À utiliser pour vérifier ou corriger rendez-vous.py (jour, continu, etat, arreter, reprendre).
---

# Agent Rendez-vous — l'agenda annoncé sur Discord

**Responsable :** Vente. **Script :** `B2B/agents/rendez-vous.py`. **Contrat :** `B2B/harness/contrats/rendez-vous.json` (statut actif).
**Tâche serveur :** `jour` toutes les 5 minutes.

## Mission
Annoncer sur Discord chaque rendez-vous de 15 minutes nouveau, déplacé, annulé ou proche, lu dans l'agenda iCal.

## Ordres pas à pas (lus dans le script)
1. Machine active obligatoire (`M.exiger`). Agent suspendu après une erreur : ne fait rien tant que `reprendre` n'est pas lancé.
2. Lit l'adresse iCal dans ses réglages (fichier hors git) ; seules les adresses `https://calendar.google.com/` sont acceptées.
3. Télécharge l'agenda, garde les événements dont le titre commence par « Rendez-vous de 15 minutes ».
4. Premier passage (et premier passage en mode réel) : note l'état actuel **sans rien annoncer** (l'historique n'est jamais rejoué).
5. Pour chaque rendez-vous : nouveau (futur), déplacé (futur), annulé (ou disparu de l'agenda) → un message chacun, une seule fois.
6. Rappel une seule fois par horaire, `rappel_minutes` (30) avant le début.
7. Message : prénom, entreprise, e-mail, remarque, jour et heure (Paris), lien Meet ; posté dans le salon « rdv » (mode réel) ou seulement journalisé « serait posté » (simulation).
8. Oublie les rendez-vous passés depuis plus de 2 jours, écrit l'état.

## Entrées et sorties
- Entrées : agenda iCal (adresse secrète), réglages `rendez-vous-config.json`.
- Sorties : messages Discord salon « rdv », `rendez-vous-etat.json`, `rendez-vous-journal.log`.

## Cas limites gérés par le code
- Adresse iCal absente, invalide ou refusée : arrêt, état « suspendu », alerte.
- Agenda illisible : compteur d'échecs ; alerte à partir de 3 échecs, nouvel essai au passage suivant.
- Salon « rdv » introuvable ou ambigu : rien n'est posté, **jamais de repli sur le salon par défaut**, une alerte par jour.
- Discord refuse le message : journalisé, nouvel essai au prochain passage.
- Toute autre erreur : arrêt, suspension, alerte, aucune reprise automatique.
- Le contenu des événements est une donnée d'un tiers : quelques champs extraits, nettoyés et bornés.

## Ce qu'il ne fait jamais
- Écrire dans l'agenda, répondre au prospect.
- Afficher, journaliser, stocker ou envoyer l'adresse iCal.

## Vérifier qu'il a bien tourné
- `python B2B\agents\rendez-vous.py etat` : nombre de rendez-vous suivis (jamais l'adresse).
- `python B2B\agents\rendez-vous.py jour --a-blanc` : ce qui serait posté, sans rien écrire.
- Tests : `python B2B\agents\test_rendez_vous.py` et `python tests\agents\test_rendez_vous.py`.

## Quand il alerte Liam
- Une alerte par motif et par jour : configuration, adresse refusée, agenda illisible 3 fois, salon introuvable, erreur.
- Silence : le surveillant le signale si aucune trace après 19:30.
