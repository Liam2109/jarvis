#!/usr/bin/env python3
"""Harness - hooks Claude Code (.claude\\hooks) : chaque hook reçoit un JSON d'exemple, bloque (code 2) ou laisse passer (code 0), en moins de 2 s. Aucun fichier modifié."""
import json, subprocess, sys, time, unittest
import commun as C

H = C.RACINE / ".claude" / "hooks"


def lancer(hook, outil, entree):
    t = time.time()
    p = subprocess.run([sys.executable, str(H / hook)], input=json.dumps({"tool_name": outil, "tool_input": entree}).encode("utf-8"), capture_output=True, timeout=10)
    return p.returncode, p.stderr.decode("utf-8", "replace"), time.time() - t


BLOQUES_BASH = ["git add -A", "git add --all", "git add .", "git add B2B/x.py . && git commit", "git reset --hard HEAD~1", "git clean -fd", "git push --force origin main",
                "git push -f", "cat .env", "type C:\\Users\\Liam\\Jarvis\\.env", "Get-Content B2B\\agents\\rendez-vous-config.local.json", "grep TOKEN .env", "head -5 b2b.local.json"]
PERMIS_BASH = ["git add B2B/harness/garde.py tests/agents/test_garde.py", "git status --short", "git push", "git reset HEAD B2B/x.py", "cat README.md",
               "python tests/coherence-offre.py", "git check-ignore -v B2B/.env", "ls *.local.json", "cat .env.example"]


class Hooks(unittest.TestCase):
    def test_pre_bash(self):
        for c in BLOQUES_BASH:
            code, err, d = lancer("pre_bash.py", "Bash", {"command": c}); self.assertEqual(code, 2, c); self.assertIn("refusée", err); self.assertLess(d, 2, c)
        for c in PERMIS_BASH:
            code, err, d = lancer("pre_bash.py", "Bash", {"command": c}); self.assertEqual((code, err), (0, ""), c); self.assertLess(d, 2, c)
        self.assertEqual(lancer("pre_bash.py", "PowerShell", {"command": "git add -A"})[0], 2)

    def test_pre_edit(self):
        for f in ("C:\\Users\\Liam\\Jarvis\\memoire\\todo.md", "C:\\Users\\Liam\\Jarvis\\.env", "C:/Users/Liam/Jarvis/B2B/agents/b2b.local.json", "C:\\Users\\Liam\\Jarvis\\config.local.json"):
            code, err, d = lancer("pre_edit.py", "Write", {"file_path": f, "content": "x"}); self.assertEqual(code, 2, f); self.assertLess(d, 2)
        for f in ("C:\\Users\\Liam\\Jarvis\\B2B\\docs\\TODO-B2B.md", "C:\\Users\\Liam\\Jarvis\\.env.example", "C:\\Users\\Liam\\Jarvis\\B2B\\agents\\devis-config.json"):
            self.assertEqual(lancer("pre_edit.py", "Edit", {"file_path": f})[:2], (0, ""), f)

    def test_post_edit(self):
        code, err, d = lancer("post_edit.py", "Write", {"file_path": str(C.RACINE / "B2B" / "docs" / "SCRIPT-APPEL-SID.md")})
        self.assertEqual((code, err), (0, ""), "fichier cohérent : sortie vide"); self.assertLess(d, 2)
        code, err, d = lancer("post_edit.py", "Write", {"file_path": str(C.RACINE / "README.md")}); self.assertEqual((code, err), (0, ""), "hors périmètre : rien")
        # fichier fautif simulé sous B2B\docs : créé dans un dossier temporaire du périmètre puis supprimé
        tmp = C.RACINE / "B2B" / "docs" / "harness" / "_test-hook-faute.md"
        try:
            tmp.write_text("Maintenance facultative, 29 €/mois.\n", encoding="utf-8")
            code, err, d = lancer("post_edit.py", "Write", {"file_path": str(tmp)})
            self.assertEqual(code, 2); self.assertIn("ECHEC", err); self.assertIn("_test-hook-faute.md:1", err); self.assertLess(d, 2)
        finally: tmp.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
