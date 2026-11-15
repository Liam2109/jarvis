#!/usr/bin/env python3
"""Harness - stripe-alerte : un paiement simulé donne le bon message (seulement les paiements réussis) ; un ancien lien Stripe n'est jamais relayé (garde). Sans réseau."""
import io, json, tempfile, unittest
from contextlib import redirect_stdout
from pathlib import Path
import commun as C

S = C.agent("stripe-alerte")
G = C.harness("garde")
CHARGES = json.loads((C.FIXTURES / "stripe-charges.json").read_text(encoding="utf-8"))
CTX = {"machine_active": True, "envoi_automatique": True, "stop": False, "deja_envoyes": 0}


class StripeAlerte(unittest.TestCase):
    def setUp(self):
        tmp = Path(tempfile.mkdtemp()); S.ETAT, S.JOURNAL = tmp / "etat.json", tmp / "journal.log"
        S.ETAT.write_text(json.dumps({"dernier_ts": 1763360000, "vus": {}}), encoding="utf-8")
        S.RP.lire_env = lambda _p: {"STRIPE_RESTRICTED_KEY": "cle-de-test-fictive"}
        S.appel_stripe = lambda _cle, _chemin: CHARGES
        self.envois = []; S.alerter_discord = lambda t: self.envois.append(t) or True

    def test_message_paiement(self):
        self.assertEqual(S.message_paiement(CHARGES["data"][0]), "Nouveau paiement Stripe : 595 euros (Pack landing page)")

    def test_paiement_simule_seulement_les_reussis(self):
        f = io.StringIO()
        with redirect_stdout(f): code = S.cmd_verifier({"envoi_automatique": True}, False)
        self.assertEqual(code, 0); self.assertEqual(self.envois, ["Nouveau paiement Stripe : 595 euros (Pack landing page)"])
        with redirect_stdout(io.StringIO()): S.cmd_verifier({"envoi_automatique": True}, False)
        self.assertEqual(len(self.envois), 1, "jamais deux fois le même paiement")

    def test_simulation_rien_sur_discord(self):
        with redirect_stdout(io.StringIO()): S.cmd_verifier({"envoi_automatique": False}, False)
        self.assertEqual(self.envois, [])

    def test_ne_relaie_pas_un_ancien_lien(self):
        t = S.message_paiement({"amount": 99400, "currency": "eur", "description": "https://buy.stripe.com/7sYaEY2ElaN7179d8k5EY07"})
        ok, r = G.verifier_envoi("stripe-alerte", "discord", t, maintenant=G.heure_paris(), ctx=CTX, tracer=False)
        self.assertFalse(ok); self.assertTrue(any("lien Stripe" in x for x in r))
        ok, _ = G.verifier_envoi("stripe-alerte", "discord", S.message_paiement(CHARGES["data"][0]), ctx=CTX, tracer=False)
        self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main(verbosity=1)
