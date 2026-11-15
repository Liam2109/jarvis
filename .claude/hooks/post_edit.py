#!/usr/bin/env python3
"""Hook PostToolUse (Edit, Write, MultiEdit) du projet Jarvis (harness, 15/11/2026) : après une écriture sous B2B\\docs, .claude\\skills ou B2B\\agents,
cohérence rapide de l'offre sur CE fichier (tests\\coherence-offre.py). Sortie vide si tout va bien ; sinon les échecs (code 2 : Claude les voit et corrige)."""
import importlib.util, io, json, sys
from contextlib import redirect_stdout
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
SURVEILLES = ("B2B/docs/", ".claude/skills/", "B2B/agents/")


def main():
    try: d = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace") or "{}")
    except ValueError: return 0
    f = str((d.get("tool_input") or {}).get("file_path") or "")
    if not f: return 0
    p = Path(f).resolve()
    try: rel = p.relative_to(RACINE).as_posix()
    except ValueError: return 0
    if not rel.startswith(SURVEILLES): return 0
    s = importlib.util.spec_from_file_location("coherence_offre", RACINE / "tests" / "coherence-offre.py"); m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    out = io.StringIO()
    with redirect_stdout(out): code = m.main(["--fichiers", str(p)])
    if code: sys.stderr.buffer.write(("Cohérence de l'offre (B2B\\docs\\OFFRE-REFERENCE.json) :\n" + out.getvalue()).encode("utf-8")); return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
