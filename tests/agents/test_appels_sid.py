#!/usr/bin/env python3
"""Harness - appels-sid : liste créée dans l'ordre des créneaux 08:00-19:00 ; mapping des 8 valeurs de Résultat (référence OFFRE-REFERENCE.json). Sans réseau."""
import json, unittest
import commun as C

A = C.agent("appels-sid")
REF = json.loads((C.RACINE / "B2B" / "docs" / "OFFRE-REFERENCE.json").read_text(encoding="utf-8"))


def choisie(nom, metier, eviter=""):
    return {"nom": nom, "metier": metier, "ville": "Rouen", "tel": "0200000000", "constat": "", "prox": 0, "eviter": eviter}


class AppelsSid(unittest.TestCase):
    def test_liste_dans_l_ordre_des_creneaux(self):
        ch = [choisie(f"P{i}", "plombier") for i in range(6)] + [choisie(f"C{i}", "coiffeur") for i in range(6)] + [choisie(f"R{i}", "restaurant") for i in range(4)]
        lignes = A.lignes_csv(ch)
        self.assertEqual(lignes[0], A.COLONNES)
        debuts = [A._debut_minutes(l[0]) for l in lignes[1:]]
        self.assertEqual(debuts, sorted(debuts), "lignes triées par heure de début")
        self.assertTrue(all(8 * 60 <= d < 19 * 60 for d in debuts), "créneaux entre 08:00 et 19:00")
        self.assertEqual(len(lignes) - 1, len(ch))

    def test_creneaux_dans_les_fenetres_8_19(self):
        for m in A.FENETRES_8_19:
            for i in range(10):
                d = A._debut_minutes(A.creneau_ligne(m, i, 10)); self.assertTrue(8 * 60 <= d < 19 * 60, (m, i, d))

    def test_heure_de_la_liste(self):
        self.assertEqual(A.DEFAUT["heure_tache"], REF["appels_sid"]["liste_creee_a"])
        t = json.loads((C.AGENTS / "serveur-taches.json").read_text(encoding="utf-8"))["agents"]["appels-sid"]
        self.assertEqual(t["heure"], "07:30")

    def test_huit_valeurs_de_resultat(self):
        self.assertEqual(A.RESULTATS, REF["resultats_appel"])
        self.assertEqual(A.COLONNES.index("Résultat"), A.I_RESULTAT)
        for ancien in REF["resultats_anciens"]: self.assertNotIn(ancien, A.RESULTATS)

    def test_mapping_resultat_vers_reprise(self):
        """Toute valeur remplie = appelé, sauf « À rappeler » (ligne reprise) ; vide = non appelé."""
        for v in A.RESULTATS: self.assertEqual(A._appele(v, False), v != "À rappeler", v)
        self.assertFalse(A._appele("", False)); self.assertFalse(A._appele("  ", False))

    def test_pas_de_reponse_change_de_creneau(self):
        ch = [choisie("P0", "plombier", eviter="08 h – 08 h 20")] + [choisie(f"P{i}", "plombier") for i in range(1, 6)]
        l = next(x for x in A.lignes_csv(ch)[1:] if x[1] == "P0")
        self.assertGreaterEqual(abs(A._debut_minutes(l[0]) - 8 * 60), 60)


if __name__ == "__main__":
    unittest.main(verbosity=1)
