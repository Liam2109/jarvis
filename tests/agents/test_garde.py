#!/usr/bin/env python3
"""Garde commune (B2B\\harness\\garde.py) : pour chaque règle, un cas qui doit bloquer (ou avertir) et un cas qui doit passer. Sans réseau."""
import os, sys, tempfile, unittest
from datetime import datetime
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
os.environ["JARVIS_HARNESS_LOGS"] = tempfile.mkdtemp(prefix="garde-test-")
sys.path.insert(0, str(RACINE / "B2B" / "harness"))
import garde as G  # noqa: E402

MARDI_10H = datetime(2026, 11, 17, 10, 0)      # heure de Paris (naïve)
SAMEDI_10H = datetime(2026, 11, 21, 10, 0)
MARDI_20H = datetime(2026, 11, 17, 20, 0)
OK_CTX = {"machine_active": True, "envoi_automatique": True, "stop": False, "deja_envoyes": 0}
PACK = "https://buy.stripe.com/14AfZifr7dZj7vxc4g5EY0c"


def v(texte, canal="discord", agent="stripe-alerte", quand=MARDI_10H, **ctx):
    return G.verifier_envoi(agent, canal, texte, "client", maintenant=quand, ctx={**OK_CTX, **ctx}, tracer=False)


def bloque(r, mot): return not r[0] and any(x.startswith("BLOQUE") and mot in x for x in r[1])
def averti(r, mot): return r[0] and any(x.startswith("AVERTIT") and mot in x for x in r[1])


class Garde(unittest.TestCase):
    def test_stop(self):
        self.assertTrue(bloque(v("Paiement reçu", stop=True), "STOP")); self.assertEqual(v("Paiement reçu"), (True, []))

    def test_lien_stripe(self):
        self.assertTrue(bloque(v("Payer : https://buy.stripe.com/7sYaEY2ElaN7179d8k5EY07"), "lien Stripe"))
        self.assertTrue(v(f"Payer : {PACK}")[0])

    def test_phrases_interdites(self):
        for p in ("sans abonnement obligatoire", "maintenance facultative", "590 €", "de 10 h à 12 h"):
            self.assertTrue(bloque(v(f"Offre : {p}"), "phrase interdite"), p)
        self.assertTrue(bloque(v("La maintenance est facultative"), "facultative"))
        self.assertTrue(v("500 € une fois, puis 29 €/mois, arrêt possible à tout moment")[0]); self.assertTrue(v("Visio de 15 minutes, caméra facultative")[0])

    def test_secrets(self):
        jeton = "M" + "a" * 23 + "." + "b" * 6 + "." + "c" * 30
        for s in (jeton, "sk_live_" + "x" * 20, "sk_test_" + "x" * 20, "whsec_" + "x" * 20, "https://calendar.google.com/calendar/ical/abc%40group/" + "private" + "-0123456789abcdef0123/basic.ics"):   # fausse adresse construite (jamais en clair dans git)
            self.assertTrue(bloque(v("voici " + s), "secret"), s[:8])
        self.assertTrue(v("clé lue dans .env, jamais affichée")[0])

    def test_horaires_client(self):
        self.assertTrue(bloque(v("Bonjour", canal="email_client", agent="prospection", quand=SAMEDI_10H), "hors lundi"))
        self.assertTrue(bloque(v("Bonjour", canal="email_client", agent="prospection", quand=MARDI_20H), "hors lundi"))
        self.assertTrue(v("Bonjour", canal="email_client", agent="prospection")[0])
        self.assertTrue(v("Paiement reçu", quand=SAMEDI_10H)[0])      # Discord vers Liam : pas de restriction client

    def test_machine_active(self):
        self.assertTrue(averti(v("x", machine_active=False), "machine")); self.assertFalse(any("machine" in x for x in v("x")[1]))

    def test_envoi_automatique(self):
        self.assertTrue(averti(v("x", envoi_automatique=False), "envoi_automatique")); self.assertFalse(any("envoi_auto" in x for x in v("x")[1]))

    def test_horaires_contrat(self):
        self.assertTrue(averti(v("x", agent="appels-sid", quand=MARDI_20H), "hors horaires"))
        self.assertFalse(any("hors horaires" in x for x in v("x", agent="appels-sid")[1]))

    def test_plafond(self):
        self.assertTrue(averti(v("x", deja_envoyes=30), "plafond")); self.assertFalse(any("plafond" in x for x in v("x", deja_envoyes=29)[1]))

    def test_agent_prevu_et_inconnu(self):
        self.assertTrue(averti(v("x", agent="production"), "prevu")); self.assertTrue(averti(v("x", agent="inconnu-xyz"), "aucun contrat"))

    def test_trace_sans_donnee_client(self):
        G.verifier_envoi("stripe-alerte", "discord", "Écrire à jean@exemple.fr ou 06 12 34 56 78 : sk_live_" + "x" * 20, maintenant=MARDI_10H, ctx=OK_CTX)
        t = (Path(os.environ["JARVIS_HARNESS_LOGS"]) / "stripe-alerte" / "2026-11-17.jsonl").read_text(encoding="utf-8")
        self.assertIn("secret", t); self.assertNotIn("jean@", t); self.assertNotIn("sk_live_x", t); self.assertNotIn("06 12", t)

    def test_avant_envoi_panne(self):
        ancien = G.verifier_envoi; G.verifier_envoi = lambda *a, **k: 1 / 0
        import io; from contextlib import redirect_stdout
        try:
            with redirect_stdout(io.StringIO()) as f: self.assertTrue(G.avant_envoi("discord", "x", agent="stripe-alerte"))
            self.assertIn("garde indisponible", f.getvalue())
        finally: G.verifier_envoi = ancien


if __name__ == "__main__":
    unittest.main(verbosity=1)
