#!/usr/bin/env python3
"""Harness - sorties de Jarvis CEO : 3 décisions valides, 5 refusées (chiffre inventé, promesse client, engagement sans engage_liam, schéma, agent inconnu). Sans réseau."""
import unittest
import commun as C

J = C.harness("jarvis_sortie")
SRC = ["tests/fixtures/jarvis/appels-2026-11-17.json", "tests/fixtures/jarvis/stripe-2026-11-17.json"]


def sortie(**k):
    base = {"date": "2026-11-17", "constat": "100 entreprises sur la liste, 42 avec un résultat, 3 RDV pris.", "sources": SRC,
            "decision": "Garder la liste du matin telle quelle.", "agent_cible": "appels-sid", "action": "Préparer la liste de demain à 07:30.",
            "engage_liam": False, "justification": "Le taux de RDV est correct sur la journée."}
    base.update(k); return base


VALIDES = [
    sortie(),
    sortie(constat="1 paiement de 595 € encaissé aujourd'hui.", agent_cible="jarvis-ceo", decision="Prévenir Liam.", action="Poster le résumé du soir sur Discord.",
           justification="Un paiement est arrivé."),
    sortie(constat="4 « Trop cher » et 3 RDV pris.", decision="Proposer à Liam d'envoyer le devis aux 3 RDV.", agent_cible="devis",
           action="Écrire les brouillons de devis dans B2B/a-valider pour validation.", engage_liam=True, justification="Les devis engagent Liam."),
]
INVALIDES = {
    "chiffre inventé": sortie(constat="100 entreprises appelées, 9 RDV pris."),
    "promesse client": sortie(action="Dire au prospect que le site lui apportera plus de clients."),
    "engage sans accord": sortie(decision="Envoyer le devis au client.", action="Envoyer le devis au client par e-mail.", agent_cible="devis"),
    "schéma": {k: v for k, v in sortie().items() if k != "justification"},
    "agent inconnu": sortie(agent_cible="agent-fantome"),
}


class JarvisSortie(unittest.TestCase):
    def test_trois_valides(self):
        for i, s in enumerate(VALIDES): self.assertEqual(J.valider_sortie(s, C.RACINE), [], i)

    def test_cinq_invalides(self):
        attendu = {"chiffre inventé": "introuvable", "promesse client": "promesse", "engage sans accord": "engage_liam", "schéma": "justification", "agent inconnu": "agent_cible"}
        for nom, s in INVALIDES.items():
            e = J.valider_sortie(s, C.RACINE); self.assertTrue(e, nom); self.assertTrue(any(attendu[nom] in x for x in e), (nom, e))

    def test_source_illisible(self):
        self.assertTrue(any("source illisible" in x for x in J.valider_sortie(sortie(sources=["tests/fixtures/jarvis/absent.json"]), C.RACINE)))


if __name__ == "__main__":
    unittest.main(verbosity=1)
