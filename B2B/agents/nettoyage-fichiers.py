#!/usr/bin/env python3
"""Agent nettoyage-fichiers (LM MULTI-SERVICES, 15/11/2026) : sans token ni réseau, chaque jour à 03:00 sur le serveur.
Supprime les traces du harness (B2B\\logs\\agents\\<agent>\\AAAA-MM-JJ.jsonl ou .json) et les entrées « - AAAA-MM-JJ … » de B2B\\docs\\JOURNAL-B2B.md
de plus de 30 jours (règle 18 de CLAUDE.md). Garde : il ne touche JAMAIS à registre-entreprises.json, memoire\\, .env, config.json ni *.local.json,
ni à rien en dehors de ces deux cibles. Une ligne de trace par passage (harness) et une ligne dans nettoyage-fichiers-journal.log.

  python agents\\nettoyage-fichiers.py nettoyer [--a-blanc] [--jours 30]    un passage (--a-blanc : compte sans rien supprimer)
  python agents\\nettoyage-fichiers.py etat                                 dernier passage"""
import argparse, os, re, sys, time
from datetime import date, datetime, timedelta
from pathlib import Path

ICI = Path(__file__).resolve().parent
RACINE = ICI.parent.parent   # dossier Jarvis
sys.path.insert(0, str(ICI)); sys.path.insert(0, str(ICI.parent / "harness"))
import machine as M   # noqa: E402
import traces as T    # noqa: E402

AGENT = "nettoyage-fichiers"
JOURNAL = ICI / f"{AGENT}-journal.log"
FICHIER_TRACE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.jsonl?$")
ENTREE = re.compile(r"^- (\d{4}-\d{2}-\d{2})\b")


def protege(p):
    """Vrai pour un fichier que ce script ne doit jamais toucher."""
    p = Path(p); nom = p.name.lower()
    return (nom == "registre-entreprises.json" or nom == ".env" or nom.endswith(".env") or nom == "config.json"
            or nom.endswith(".local.json") or "memoire" in (x.lower() for x in p.parts))


def garde(p, racine):
    """Seules cibles permises : un fichier de trace daté dans B2B/logs/agents/<agent>/ ou B2B/docs/JOURNAL-B2B.md ; jamais un fichier protégé ni un lien."""
    p = Path(p); logs = (racine / "B2B" / "logs" / "agents").resolve()
    if protege(p) or p.is_symlink(): return False
    r = p.resolve()
    if r == (racine / "B2B" / "docs" / "JOURNAL-B2B.md").resolve(): return True
    return r.parent.parent == logs and FICHIER_TRACE.match(r.name) is not None


def nettoyer_traces(racine, limite, a_blanc=False):
    """-> (supprimés, refusés par la garde). Fichiers datés strictement avant la limite."""
    logs = racine / "B2B" / "logs" / "agents"; n = refus = 0
    if not logs.is_dir(): return 0, 0
    for d in logs.iterdir():
        if not d.is_dir() or d.is_symlink(): continue
        for f in d.iterdir():
            m = FICHIER_TRACE.match(f.name)
            if not m or m.group(1) >= limite.isoformat(): continue
            if not garde(f, racine): refus += 1; continue
            if not a_blanc: f.unlink()
            n += 1
    return n, refus


def nettoyer_journal(racine, limite, a_blanc=False):
    """-> entrées supprimées. Garde l'en-tête, les lignes non datées, l'encodage (BOM) et les fins de ligne."""
    f = racine / "B2B" / "docs" / "JOURNAL-B2B.md"
    if not f.is_file() or not garde(f, racine): return 0
    brut = f.read_bytes(); bom = brut.startswith(b"\xef\xbb\xbf")
    lignes = brut.decode("utf-8-sig").splitlines(keepends=True)
    gardees = [l for l in lignes if not ((m := ENTREE.match(l)) and m.group(1) < limite.isoformat())]
    n = len(lignes) - len(gardees)
    if n and not a_blanc:
        tmp = f.with_suffix(".md.tmp")
        tmp.write_bytes((b"\xef\xbb\xbf" if bom else b"") + "".join(gardees).encode("utf-8"))
        os.replace(tmp, f)
    return n


def passage(racine=RACINE, jours=30, a_blanc=False, aujourdhui=None):
    limite = (aujourdhui or date.today()) - timedelta(days=jours)
    t, refus = nettoyer_traces(racine, limite, a_blanc)
    j = nettoyer_journal(racine, limite, a_blanc)
    return {"limite": limite.isoformat(), "traces": t, "journal": j, "refus": refus, "a_blanc": a_blanc}


def main(argv=None):
    p = argparse.ArgumentParser(prog=AGENT, description="Supprime traces et entrées du journal B2B de plus de N jours (sans token).")
    sp = p.add_subparsers(dest="cmd", required=True)
    n = sp.add_parser("nettoyer"); n.add_argument("--a-blanc", action="store_true"); n.add_argument("--jours", type=int, default=30)
    sp.add_parser("etat")
    a = p.parse_args(argv)
    if a.cmd == "etat":
        try: print(JOURNAL.read_text(encoding="utf-8").splitlines()[-1])
        except (OSError, IndexError): print("Aucun passage.")
        return 0
    M.exiger(AGENT, a.cmd, a.a_blanc)
    if (ICI.parent / "STOP").exists(): print("  ! kill-switch B2B\\STOP présent : rien supprimé"); return 0
    if not 1 <= a.jours <= 3650: print("  ! --jours doit être entre 1 et 3650"); return 2
    t0 = time.time()
    try:
        r = passage(jours=a.jours, a_blanc=a.a_blanc)
    except OSError as e:
        T.ecrire(AGENT, "nettoyer", "erreur", time.time() - t0, ok=False, erreur=type(e).__name__)
        print(f"  ! erreur de fichier : {e.strerror or type(e).__name__}"); return 2
    texte = f"{r['traces']} trace(s) et {r['journal']} entrée(s) du journal avant le {r['limite']}" + (" (à blanc, rien supprimé)" if a.a_blanc else " supprimées") + (f", {r['refus']} refusée(s) par la garde" if r["refus"] else "")
    T.ecrire(AGENT, "nettoyer" + (" --a-blanc" if a.a_blanc else ""), texte, time.time() - t0, ok=True)
    try:
        with JOURNAL.open("a", encoding="utf-8") as f: f.write(f"{datetime.now():%Y-%m-%d %H:%M} | nettoyer | {texte}\n")
    except OSError: pass
    print(texte); return 0


if __name__ == "__main__":
    sys.exit(main())
