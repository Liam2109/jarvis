#!/usr/bin/env python3
"""Harness - nettoyage-fichiers : sur une arborescence FICTIVE (dossier temporaire), supprime traces et entrées du journal de plus de 30 jours,
garde le reste, ne touche jamais aux fichiers protégés (registre, memoire\\, .env, config.json, *.local.json), --a-blanc ne supprime rien. Sans réseau."""
import os, shutil, tempfile, unittest
from datetime import date, datetime
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


class ToutJarvis(unittest.TestCase):
    """Extension du 16/11/2026 : %TEMP% fictif, sauvegardes, __pycache__ supprimés ; le reste seulement listé dans B2B/a-valider."""
    def setUp(self):
        self.r = Path(tempfile.mkdtemp(prefix="nettoyage-test-")); self.tmp = Path(tempfile.mkdtemp(prefix="nettoyage-test-temp-"))
        maint = datetime.combine(AUJ, datetime.now().time()).timestamp(); self.vieux = lambda p, j: os.utime(p, (maint - j * 86400,) * 2)
        def f(rel, age=0, base=None):
            p = (base or self.r) / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text("ne pas toucher", encoding="utf-8")
            if age: self.vieux(p, age)
            return p
        # %TEMP% fictif : dossiers de test vieux (supprimés), récent ou d'une autre appli (gardés)
        self.t_vieux = [f(n + "/x.txt", base=self.tmp).parent for n in ("appels-sid-test-abc", "jarvis-test-123", "reponses-rebonds-x")]
        self.t_garde = [f(n + "/x.txt", base=self.tmp).parent for n in ("appels-sid-test-neuf", "autre-appli-vieille", "tmpabc")]
        for d in self.t_vieux + self.t_garde[1:]: self.vieux(d, 3)
        self.vieux(self.t_garde[0], 1)
        s = "B2B/donnees/sauvegardes/"
        self.supprimes = [f(s + "JOURNAL-B2B-2026-11-15.md"), f(s + "ancien.zip", 40),
                          f("B2B/agents/__pycache__/x.pyc"), f("tests/__pycache__/y.pyc")]
        f("INDEX.md").write_text("- `logs/lie.log` : utile\n", encoding="utf-8")
        self.gardes = [f(s + "MEMOIRE-B2B-2026-12-01.md"), f(s + "recent.zip", 1),f("memoire/__pycache__/z.pyc"),
                       f("logs/lie.log", 90), f("vieux.py", 90), f("docs/vieux.txt", 90), f("instagram/v.mp4", 90), f("instagram/n.txt", 90),
                       f("Sans titre.canvas", 90), f(".claude/skills/a/notes.txt", 90), f("B2B/donnees/registre-entreprises.json", 90),
                       f("config.json", 90), f(".env", 90), f("a.local.json", 90), f("memoire/vieux.log", 90), f("recent.log", 30)]
        self.a_lister = [f("logs/oublie.log", 90), f("B2B/vieux-export.csv", 61)]

    def tearDown(self):
        shutil.rmtree(self.r, ignore_errors=True); shutil.rmtree(self.tmp, ignore_errors=True)

    def test_passage(self):
        r = N.passage(self.r, 30, aujourdhui=AUJ, temp=self.tmp)
        self.assertEqual((r["temp"], r["sauvegardes"], r["pycache"], r["a_verifier"], r["refus"]), (3, 2, 2, 2, 0))
        for p in self.t_vieux + self.supprimes: self.assertFalse(p.exists(), p)
        for p in self.t_garde + self.a_lister: self.assertTrue(p.exists(), p)
        for p in self.gardes: self.assertEqual(p.read_text(encoding="utf-8"), "ne pas toucher", p)
        rap = self.r / "B2B" / "a-valider" / "nettoyage-2026-12-20.md"; texte = rap.read_text(encoding="utf-8")
        self.assertEqual(r["rapport"], str(rap)); self.assertIn("Rien n'a été supprimé", texte)
        for x in ("logs/oublie.log", "B2B/vieux-export.csv"): self.assertIn(x, texte)
        for x in ("`logs/lie.log`", "vieux.py", "docs/", "instagram", ".canvas", "skills", "registre", "config.json", ".env", "local.json", "memoire", "recent"):
            self.assertNotIn(x, texte.split("|---|")[-1])

    def test_a_blanc(self):
        r = N.passage(self.r, 30, a_blanc=True, aujourdhui=AUJ, temp=self.tmp)
        self.assertEqual((r["temp"], r["sauvegardes"], r["pycache"], r["a_verifier"], r["rapport"]), (3, 2, 2, 2, ""))
        for p in self.t_vieux + self.supprimes: self.assertTrue(p.exists(), p)
        self.assertFalse((self.r / "B2B" / "a-valider").exists())

    def test_garde(self):
        self.assertTrue(N.garde(self.t_vieux[0], self.r, self.tmp)); self.assertTrue(N.garde(self.supprimes[0], self.r))
        self.assertTrue(N.garde(self.supprimes[2].parent, self.r))
        for p in [self.t_vieux[0]] + self.t_garde[1:] + self.gardes[2:] + self.a_lister + [self.r / "B2B" / "donnees" / "sauvegardes" / "registre-entreprises.json"]:
            self.assertFalse(N.garde(p if p.name != "z.pyc" else p.parent, self.r, None if p == self.t_vieux[0] else self.tmp), p)


if __name__ == "__main__":
    unittest.main(verbosity=1)
