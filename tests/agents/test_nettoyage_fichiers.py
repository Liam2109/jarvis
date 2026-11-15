#!/usr/bin/env python3
"""Harness - nettoyage-fichiers : sur une arborescence FICTIVE (dossier temporaire), supprime traces et entrées du journal de plus de 30 jours,
garde le reste, ne touche jamais aux fichiers protégés (registre, memoire\\, .env, config.json, *.local.json), --a-blanc ne supprime rien. Sans réseau."""
import shutil, tempfile, unittest
from datetime import date
from pathlib import Path
import commun as C

N = C.agent("nettoyage-fichiers")
AUJ = date(2026, 12, 20)   # limite = 2026-11-20


class Nettoyage(unittest.TestCase):
    def setUp(self):
        self.r = Path(tempfile.mkdtemp(prefix="nettoyage-test-"))
        self.logs = self.r / "B2B" / "logs" / "agents" / "appels-sid"; self.logs.mkdir(parents=True)
        for j in ("2026-10-01", "2026-11-19", "2026-11-20", "2026-12-19"): (self.logs / f"{j}.jsonl").write_text("{}\n", encoding="utf-8")
        g = self.r / "B2B" / "logs" / "agents" / "_garde"; g.mkdir(); (g / "2026-10-01.json").write_text("{}", encoding="utf-8")
        (self.logs / "notes.txt").write_text("x", encoding="utf-8")                       # non daté : gardé
        (self.logs / "2026-10-01.local.json").write_text("{}", encoding="utf-8")         # protégé, même vieux
        self.proteges = [self.r / "B2B" / "donnees" / "registre-entreprises.json", self.r / "memoire" / "2026-10-01.jsonl",
                         self.r / ".env", self.r / "config.json", self.r / "B2B" / "agents" / "b2b.local.json"]
        for p in self.proteges: p.parent.mkdir(parents=True, exist_ok=True); p.write_text("ne pas toucher", encoding="utf-8")
        self.j = self.r / "B2B" / "docs" / "JOURNAL-B2B.md"; self.j.parent.mkdir(parents=True)
        self.j.write_bytes("# JOURNAL\r\n\r\n- 2026-10-15 : vieux fait.\r\n- 2026-11-19 (soir) : vieux aussi.\r\n- 2026-11-20 : gardé (30 jours pile).\r\n- 2026-12-19 : récent.\r\n".encode("utf-8"))

    def tearDown(self):
        shutil.rmtree(self.r, ignore_errors=True)

    def test_passage(self):
        r = N.passage(self.r, 30, aujourdhui=AUJ)
        self.assertEqual((r["traces"], r["journal"], r["refus"]), (3, 2, 0))
        self.assertEqual(sorted(p.name for p in self.logs.iterdir()), ["2026-10-01.local.json", "2026-11-20.jsonl", "2026-12-19.jsonl", "notes.txt"])
        self.assertEqual(self.j.read_bytes().decode("utf-8"), "# JOURNAL\r\n\r\n- 2026-11-20 : gardé (30 jours pile).\r\n- 2026-12-19 : récent.\r\n")
        for p in self.proteges: self.assertEqual(p.read_text(encoding="utf-8"), "ne pas toucher", p)
        self.assertEqual(N.passage(self.r, 30, aujourdhui=AUJ)["traces"], 0)   # deuxième passage : plus rien

    def test_a_blanc(self):
        avant = self.j.read_bytes()
        r = N.passage(self.r, 30, a_blanc=True, aujourdhui=AUJ)
        self.assertEqual((r["traces"], r["journal"]), (3, 2))
        self.assertEqual(len(list(self.logs.iterdir())), 6); self.assertEqual(self.j.read_bytes(), avant)

    def test_garde(self):
        for p in self.proteges + [self.r / "B2B" / "docs" / "TODO-B2B.md", self.r / "B2B" / "logs" / "agents" / "2026-10-01.jsonl"]:
            self.assertFalse(N.garde(p, self.r), p)
        self.assertTrue(N.garde(self.logs / "2026-10-01.jsonl", self.r)); self.assertTrue(N.garde(self.j, self.r))


if __name__ == "__main__":
    unittest.main(verbosity=1)
