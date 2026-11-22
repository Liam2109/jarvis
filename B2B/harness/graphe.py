#!/usr/bin/env python3
"""Vérifie le graphe Obsidian (15/11/2026, « un seul graphe ») : lecture seule, sans réseau ni IA.
Périmètre : INDEX.md, docs\\agents\\*.md (sans les copies de skills, orphelines et masquées), docs\\decisions\\*.md et les docs clés qu'ils citent.
  1. aucun lien [[...]] ne pointe vers une note inexistante ;
  2. graphe en arbre (22/11/2026) : seule « 🧠 Jarvis (CEO) » cite librement des agents ; une note de superviseur de domaine ne cite que le CEO
     et les agents de son domaine (B2B\harness\domaines.py, lu dans AGENTS_SUIVIS) ; toute autre note d'agent ne cite aucun agent, responsable ni skill ;
  3. les liens [[docs/decisions/...]] de chaque note sont identiques à ceux du dernier commit (git HEAD) ;
  4. le graphe forme UNE seule composante connexe.
  python B2B\\harness\\graphe.py      code 1 si un point échoue"""
import re, subprocess, sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from domaines import liens_permis   # noqa: E402  arbre des liens permis par superviseur de domaine
AGENTS, DECISIONS = RACINE / "docs" / "agents", RACINE / "docs" / "decisions"
CEO = AGENTS / "🧠 Jarvis (CEO).md"
LIEN = re.compile(r"!?\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")


def git(*a):
    r = subprocess.run(["git", "-c", "core.quotepath=false", *a], cwd=str(RACINE), capture_output=True)
    return r.stdout.decode("utf-8", "replace") if r.returncode == 0 else None


def toutes_notes():
    """Chemins relatifs (avec /) de toutes les notes .md du coffre suivies ou non ignorées par git."""
    return [x for x in (git("ls-files", "-z", "-co", "--exclude-standard", "--", "*.md") or "").split("\0") if x]


def liens(texte): return [m.group(1).strip() for m in LIEN.finditer(texte)]


def resoudre(cible, notes, par_nom):
    c = cible[:-3] if cible.lower().endswith(".md") else cible
    if "/" in c: return next((n for n in notes if n[:-3].casefold() == c.casefold()), None)
    xs = par_nom.get(c.casefold()); return xs[0] if xs else None


def perimetre():
    return ["INDEX.md"] + sorted(p.relative_to(RACINE).as_posix() for d in (AGENTS, DECISIONS) for p in d.glob("*.md"))


def verifier():
    notes = toutes_notes(); par_nom = {}; permis = liens_permis()
    for n in sorted(notes, key=len): par_nom.setdefault(Path(n).stem.casefold(), []).append(n)
    pb, aretes, noeuds = [], {}, set(perimetre())
    for n in perimetre():
        p = RACINE / n
        if not p.is_file(): pb.append(f"note du périmètre absente : {n}"); continue
        t = p.read_text(encoding="utf-8"); ls = liens(t)
        for c in ls:
            r = resoudre(c, notes, par_nom)
            if r is None: pb.append(f"lien vers une note inexistante : [[{c}]] dans {n}"); continue
            aretes.setdefault(n, set()).add(r); aretes.setdefault(r, set()).add(n); noeuds.add(r)
            if (n.startswith("docs/agents/") and p != CEO and r not in permis.get(n, ())
                    and (r.startswith("docs/agents/") or r.startswith("B2B/docs/agents/") or "/skills/" in r)):
                pb.append(f"lien interdit (agent, responsable ou skill) : [[{c}]] dans {n}")
        avant = git("show", f"HEAD:{n}")
        if avant is not None:
            dec = lambda x: sorted(c for c in liens(x) if c.startswith("docs/decisions/"))
            if dec(avant) != dec(t): pb.append(f"liens vers docs/decisions modifiés par rapport à git HEAD : {n}")
    # composantes connexes (parcours en largeur)
    reste, comp = set(noeuds), []
    while reste:
        a_voir, vu = [reste.pop()], set()
        while a_voir:
            x = a_voir.pop(); vu.add(x)
            for y in aretes.get(x, ()):
                if y in reste: reste.discard(y); a_voir.append(y)
        comp.append(sorted(vu))
    if len(comp) != 1:
        pb.append(f"{len(comp)} composantes au lieu d'une : " + " | ".join(", ".join(c[:3]) + ("…" if len(c) > 3 else "") for c in sorted(comp, key=len)))
    return pb, len(noeuds), len(comp)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    pb, n, k = verifier()
    for x in pb: print("  ECHEC " + x)
    if not pb: print(f"  OK    graphe Obsidian : {n} notes, {k} composante, aucun lien cassé, liens vers les décisions inchangés")
    return 1 if pb else 0


if __name__ == "__main__":
    sys.exit(main())
