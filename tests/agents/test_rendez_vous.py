#!/usr/bin/env python3
"""Harness - rendez-vous : lit un iCal fictif (fixture), jamais la vraie adresse ; une adresse en erreur n'apparaît jamais dans le message. Sans réseau (127.0.0.1 seulement)."""
import unittest
import commun as C

R = C.agent("rendez-vous")
ICS = (C.FIXTURES / "rdv-fictif.ics").read_text(encoding="utf-8")


class RendezVous(unittest.TestCase):
    def test_fixture_fictive(self):
        self.assertNotIn("private-", ICS); self.assertNotIn("calendar.google.com/calendar/ical", ICS)

    def test_lit_l_ical_fictif(self):
        evs = R.lire_ical(ICS, "Rendez-vous de 15 minutes")
        self.assertEqual(len(evs), 1, "seuls les titres « Rendez-vous de 15 minutes » comptent")
        e = next(iter(evs.values()))
        self.assertEqual((e["prenom"], e["entreprise"]), ("Sid", "Plomberie Durand"))
        self.assertEqual(e["meet"], "https://meet.google.com/abc-defg-hij")
        t = R.message("nouveau", e)
        self.assertIn("Entreprise : Plomberie Durand", t); self.assertIn("Quand :", t); self.assertIn("Lien Meet", t)

    def test_pas_un_ical(self):
        self.assertIsNone(R.lire_ical("<html>erreur</html>"))

    def test_adresse_jamais_dans_l_erreur(self):
        url = "http://127.0.0.1:9/calendar/ical/x/" + "private" + "-0123456789abcdef/basic.ics"   # fausse adresse construite (jamais en clair dans git)
        with self.assertRaises(R.ErreurLecture) as e: R.telecharger_ical(url)
        self.assertNotIn("private-", str(e.exception)); self.assertNotIn("127.0.0.1", str(e.exception))
        self.assertIsNone(e.exception.__cause__)

    def test_la_vraie_adresse_n_est_pas_lue(self):
        appels = []; ancien = R.telecharger_ical; R.telecharger_ical = lambda u: appels.append(u) or ""
        try: R.lire_ical(ICS)
        finally: R.telecharger_ical = ancien
        self.assertEqual(appels, [])


if __name__ == "__main__":
    unittest.main(verbosity=1)
