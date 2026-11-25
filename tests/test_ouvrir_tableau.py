#!/usr/bin/env python3
"""Test de outils\\ouvrir-tableau.py (lanceur de l'icône « Jarvis - Mon entreprise »). Silencieux : aucun navigateur, aucune fenêtre, aucun accès au vrai serveur ;
un faux serveur sur 127.0.0.1 (port libre) et des fichiers temporaires. Vérifie : ordre des adresses, secret jamais dans l'adresse ni dans la sortie, repli annoncé si le serveur est éteint."""
import contextlib, importlib.util, io, json, os, shutil, socket, sys, tempfile, threading, unittest
from pathlib import Path

os.environ["JARVIS_TEST"] = "1"; sys.dont_write_bytecode = True
RACINE = Path(__file__).resolve().parent.parent
s = importlib.util.spec_from_file_location("ouvrir_tableau", RACINE / "outils" / "ouvrir-tableau.py"); O = importlib.util.module_from_spec(s); s.loader.exec_module(O)
SECRET = "SECRET-DE-TEST-0123456789abcdef"


class Test(unittest.TestCase):
    def setUp(self): self.t = Path(tempfile.mkdtemp(prefix="ouvrir-test-"))
    def tearDown(self): shutil.rmtree(self.t, ignore_errors=True)

    def conf(self, d):
        f = self.t / "b2b.local.json"; f.write_text(json.dumps(d), encoding="utf-8"); return f

    def test_hotes_nom_puis_adresse_sans_doublon(self):
        self.assertEqual(O.hotes(self.conf({"machine_active": "SERVEUR", "serveur_adresse": "10.0.0.5", "jeton": SECRET})), ["SERVEUR", "10.0.0.5"])
        self.assertEqual(O.hotes(self.conf({"machine_active": "A", "serveur_adresse": "A"})), ["A"])

    def test_hotes_fichier_absent_ou_abime(self):
        self.assertEqual(O.hotes(self.t / "absent.json"), [])
        f = self.t / "x.json"; f.write_text("{pas du json", encoding="utf-8"); self.assertEqual(O.hotes(f), [])
        self.assertEqual(O.hotes(self.conf([1, 2])), [])

    def test_choisir_prend_le_plus_prioritaire_qui_repond(self):
        self.assertEqual(O.choisir(["A", "B", "C"], test=lambda h, p, d: h in ("B", "C")), "B")   # ordre de la liste = priorité
        self.assertEqual(O.choisir(["NOM", "IP"], test=lambda h, p, d: h == "IP"), "IP")          # nom qui ne répond pas : l'IP prend le relais
        self.assertIsNone(O.choisir(["A"], test=lambda *a: False)); self.assertIsNone(O.choisir([]))

    def test_regler_ecrit_une_seule_cle_et_garde_le_reste(self):
        f = self.conf({"machine_active": "SERVEUR", "serveur_adresse": "192.168.1.13", "jeton": SECRET})
        f.write_bytes(b"\xef\xbb\xbf" + f.read_bytes())
        self.assertTrue(O.regler("192.168.1.12", f, test=lambda *a: True))
        brut = f.read_bytes(); c = json.loads(brut.decode("utf-8-sig"))
        self.assertTrue(brut.startswith(b"\xef\xbb\xbf")); self.assertEqual(c, {"machine_active": "SERVEUR", "serveur_adresse": "192.168.1.12", "jeton": SECRET})

    def test_regler_refuse_adresse_muette_ou_bizarre(self):
        f = self.conf({"serveur_adresse": "192.168.1.13"}); avant = f.read_bytes()
        self.assertFalse(O.regler("192.168.1.12", f, test=lambda *a: False))
        for mauvais in ("", "a b", "x;rm", "http://x/", "../x"): self.assertFalse(O.regler(mauvais, f, test=lambda *a: True))
        self.assertFalse(O.regler("10.0.0.1", self.t / "absent.json", test=lambda *a: True))
        self.assertEqual(f.read_bytes(), avant)

    def test_joignable_vrai_et_faux(self):
        srv = socket.socket(); srv.bind(("127.0.0.1", 0)); srv.listen(1); port = srv.getsockname()[1]
        try: self.assertTrue(O.joignable("127.0.0.1", port, 1.0))
        finally: srv.close()
        self.assertFalse(O.joignable("127.0.0.1", port, 0.5))   # port refermé

    def test_adresse_sans_secret(self):
        self.assertEqual(O.adresse("SERVEUR"), "http://SERVEUR:8080/")
        self.assertNotIn("?", O.adresse("SERVEUR")); self.assertNotIn("#", O.adresse("SERVEUR"))

    def test_main_ouvre_le_serveur_et_jamais_le_secret(self):
        ouverts = []; avant = (O.hotes, O.joignable)
        O.hotes = lambda *a: ["SERVEUR", SECRET]   # un secret placé dans la config ne doit jamais ressortir
        O.joignable = lambda h, p=8080, d=2.0: h == "SERVEUR"
        try:
            self.assertEqual(O.main([], ouvrir=ouverts.append), 0)
            self.assertEqual(ouverts, ["http://SERVEUR:8080/"])
            sortie = io.StringIO()
            with contextlib.redirect_stdout(sortie): O.main(["--adresse"], ouvrir=ouverts.append)
            self.assertNotIn(SECRET, sortie.getvalue()); self.assertEqual(len(ouverts), 1)   # --adresse n'ouvre rien
        finally: O.hotes, O.joignable = avant

    def test_main_serveur_eteint_repli_annonce(self):
        ouverts, messages = [], []; avant = (O.hotes, O.prevenir, O.subprocess.run, O.joignable)
        O.hotes = lambda *a: ["SERVEUR"]; O.prevenir = messages.append; O.subprocess.run = lambda *a, **k: None; O.joignable = lambda *a: False
        try:
            self.assertEqual(O.main([], ouvrir=ouverts.append), 2)
            self.assertEqual(len(ouverts), 1); self.assertTrue(ouverts[0].endswith("index.html")); self.assertFalse(ouverts[0].startswith("http"))
            self.assertEqual(len(messages), 1); self.assertIn("ne répond pas", messages[0]); self.assertIn("ANCIENNE", messages[0])
        finally: O.hotes, O.prevenir, O.subprocess.run, O.joignable = avant


if __name__ == "__main__":
    unittest.main(verbosity=1)
