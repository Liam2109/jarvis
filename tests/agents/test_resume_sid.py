#!/usr/bin/env python3
"""Harness - résumé du soir (resume-sid) : compte les 8 valeurs de Résultat, jamais « Répondu » ni « Refus » sur le tableur actuel ; aucun chiffre inventé. Sans réseau."""
import json, tempfile, unittest
from pathlib import Path
import commun as C

S = C.agent("resume-sid")
REF = json.loads((C.RACINE / "B2B" / "docs" / "OFFRE-REFERENCE.json").read_text(encoding="utf-8"))
FEUILLE = (C.FIXTURES / "feuille-appels.csv").read_text(encoding="utf-8")


class FauxDrive:
    def __init__(self, brut): self.brut = brut
    def compte(self): return "compte-test@exemple.invalid"
    def lire_feuille(self, _id): return self.brut


class ResumeSid(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()); S.APPELS_SID_ETAT = self.tmp / "appels-sid-etat.json"
        S.APPELS_SID_ETAT.write_text(json.dumps({"google": {"2026-11-17": {"feuille": "id-fictif"}}}), encoding="utf-8")
        self.conf = {"compte_google": "compte-test@exemple.invalid"}

    def test_compte_les_huit_valeurs(self):
        ok, a = S.stats_appels(self.conf, "2026-11-17", FauxDrive(FEUILLE))
        self.assertTrue(ok)
        self.assertEqual(list(a["resultats"]), REF["resultats_appel"])
        self.assertEqual(a["resultats"]["RDV pris"], 2); self.assertEqual(a["resultats"]["Pas de réponse"], 2); self.assertEqual(a["resultats"]["Trop cher"], 1)
        self.assertEqual(a["total"], 12); self.assertEqual(a["Appelé"], 10); self.assertEqual(a["autres"], 0)

    def test_message_sans_anciennes_valeurs(self):
        ok, a = S.stats_appels(self.conf, "2026-11-17", FauxDrive(FEUILLE))
        t = S.message_resume("2026-11-17", ok, a, True, {"montants": {"EUR": 59500}, "paiements": 1, "partiel": False})
        for v in REF["resultats_appel"]: self.assertIn(v, t)
        for v in REF["resultats_anciens"]: self.assertNotIn(v, t)
        self.assertIn("595 euros", t)

    def test_aucun_chiffre_invente(self):
        S.APPELS_SID_ETAT.write_text("{}", encoding="utf-8")
        ok, raison = S.stats_appels(self.conf, "2026-11-17", FauxDrive(FEUILLE))
        self.assertFalse(ok); t = S.message_resume("2026-11-17", ok, raison, False, "clé absente")
        self.assertIn("pas de chiffre", t)


if __name__ == "__main__":
    unittest.main(verbosity=1)
