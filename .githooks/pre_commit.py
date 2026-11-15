#!/usr/bin/env python3
"""Hook git pre-commit du projet Jarvis (harness, 15/11/2026), activé par : git config core.hooksPath .githooks
Refuse le commit (code 1) si un fichier indexé : est .env ou un *.local.json ; contient un secret (jeton Discord, sk_live_, sk_test_, rk_live_, whsec_, adresse iCal secrète) ;
ou ajoute une faute de cohérence de l'offre (tests\\coherence-offre.py sur les fichiers indexés). Le secret n'est jamais affiché : seulement fichier:ligne et sa nature."""
import importlib.util, io, re, subprocess, sys
from contextlib import redirect_stdout
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "B2B" / "harness"))


def indexes():
    o = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"], cwd=RACINE, capture_output=True).stdout.decode("utf-8", "replace")
    return [f for f in o.split("\0") if f]


def contenu_indexe(f):
    try: return subprocess.run(["git", "show", f":{f}"], cwd=RACINE, capture_output=True, timeout=20).stdout.decode("utf-8", "replace")
    except Exception: return ""


def main():
    import garde as G
    fichiers = indexes(); fautes = []
    for f in fichiers:
        nom = f.rsplit("/", 1)[-1]
        if nom == ".env" or nom.endswith(".local.json"): fautes.append(f"{f} : fichier secret indexé (jamais dans git)"); continue
        for i, l in enumerate(contenu_indexe(f).splitlines(), 1):
            for s in G.secrets_dans(l): fautes.append(f"{f}:{i} : secret ({s})")
    s = importlib.util.spec_from_file_location("coherence_offre", RACINE / "tests" / "coherence-offre.py"); m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    out = io.StringIO()
    with redirect_stdout(out): code = m.main(["--fichiers"] + [str(RACINE / f) for f in fichiers])
    if code: fautes += [l for l in out.getvalue().splitlines() if l.strip()]
    if fautes:
        sys.stderr.buffer.write(("Commit refusé par le harness :\n  " + "\n  ".join(fautes[:30]) + "\n").encode("utf-8")); return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
