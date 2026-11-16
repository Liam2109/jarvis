#!/usr/bin/env python3
"""Agent nettoyage-fichiers (LM MULTI-SERVICES, 15/11/2026) : sans token ni réseau, chaque jour à 03:00 sur le serveur.
Supprime les traces du harness (B2B\\logs\\agents\\<agent>\\AAAA-MM-JJ.jsonl ou .json) et les entrées « - AAAA-MM-JJ … » de B2B\\docs\\JOURNAL-B2B.md
de plus de 30 jours (règle 18 de CLAUDE.md). Étendu le 16/11/2026 à tout le dossier Jarvis : supprime aussi les dossiers temporaires laissés par
les tests dans %TEMP% (préfixes connus, plus de 2 jours), les sauvegardes de B2B\\donnees\\sauvegardes de plus de 30 jours et les __pycache__.
Pour le reste (fichiers de plus de 60 jours sans lien dans INDEX.md), il écrit SEULEMENT un rapport B2B\\a-valider\\nettoyage-AAAA-MM-JJ.md, sans rien supprimer.
Garde : il ne touche JAMAIS au code, aux skills, aux docs, aux médias (instagram\\), aux .canvas, à registre-entreprises.json, memoire\\, .env,
config.json ni *.local.json, ni à rien en dehors de ces cibles. Une ligne de trace par passage (harness) et une ligne dans nettoyage-fichiers-journal.log.

  python agents\\nettoyage-fichiers.py nettoyer [--a-blanc] [--jours 30]    un passage (--a-blanc : compte sans rien supprimer)
  python agents\\nettoyage-fichiers.py etat                                 dernier passage"""
import argparse, os, re, shutil, sys, tempfile, time
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
DATE_NOM = re.compile(r"(\d{4}-\d{2}-\d{2})")
# dossiers de %TEMP% créés par les tests (tempfile.mkdtemp(prefix=...) des tests\ et B2B\agents\test_*.py, tests\tout.ps1)
TEMP_TEST = re.compile(r"^([a-z]+(-[a-z]+)*-test-|jarvis-(test|config-test|faux-serveur|rdv)-?|reponses-(rebonds|classement)-|registre-anciens-|appels-registre-)")
JOURS_TEMP, JOURS_RAPPORT = 2, 60
SAUTES_PYCACHE = {".git", "node_modules", ".venv", "venv", "memoire"}
# rapport : jamais le code, les skills, les docs, les médias, les .canvas ni ce que l'agent nettoie déjà lui-même
SAUTES_RAPPORT = SAUTES_PYCACHE | {"__pycache__", ".claude", "docs", "skills", "instagram", "models"}
SAUTES_RAPPORT_REL = {"B2B/a-valider", "B2B/donnees/sauvegardes", "B2B/logs/agents"}
EXT_GARDEES = set((".py .pyw .ps1 .psm1 .psd1 .js .mjs .cjs .ts .tsx .jsx .html .htm .css .bat .cmd .sh .vbs .json .jsonc .yaml .yml .toml .ini "
                   ".md .pdf .doc .docx .odt .canvas .png .jpg .jpeg .gif .webp .avif .svg .ico .mp4 .mov .webm .mkv .mp3 .wav .ogg .m4a .flac "
                   ".woff .woff2 .ttf .otf").split())


def protege(p):
    """Vrai pour un fichier que ce script ne doit jamais toucher."""
    p = Path(p); nom = p.name.lower()
    return (nom == "registre-entreprises.json" or nom == ".env" or nom.endswith(".env") or nom == "config.json"
            or nom.endswith(".local.json") or "memoire" in (x.lower() for x in p.parts))


def garde(p, racine, temp=None):
    """Seules cibles permises : un fichier de trace daté dans B2B/logs/agents/<agent>/, B2B/docs/JOURNAL-B2B.md, un fichier de
    B2B/donnees/sauvegardes/, un dossier __pycache__ du dossier Jarvis, un dossier de test (préfixe connu) directement dans temp ;
    jamais un fichier protégé ni un lien."""
    p = Path(p); racine = Path(racine).resolve(); logs = racine / "B2B" / "logs" / "agents"
    if protege(p) or p.is_symlink(): return False
    r = p.resolve()
    if r == racine / "B2B" / "docs" / "JOURNAL-B2B.md": return True
    if r.parent.parent == logs and FICHIER_TRACE.match(r.name): return True
    if r.parent == racine / "B2B" / "donnees" / "sauvegardes" and not r.is_dir(): return True
    if r.name == "__pycache__" and racine in r.parents: return True
    return temp is not None and r.parent == Path(temp).resolve() and TEMP_TEST.match(r.name) is not None


def _supprimer(p):
    """-> 1 si supprimé, 0 sinon (fichier verrouillé, droits) : un échec ne bloque pas le reste du passage."""
    try:
        shutil.rmtree(p) if p.is_dir() and not p.is_symlink() else p.unlink()
        return 1
    except OSError:
        return 0


def nettoyer_temp(racine, temp, seuil, a_blanc=False):
    """-> (supprimés, refus). Dossiers de test laissés dans temp, modifiés avant le seuil (horodatage)."""
    n = refus = 0
    if not temp or not Path(temp).is_dir(): return 0, 0
    for d in Path(temp).iterdir():
        if not TEMP_TEST.match(d.name): continue
        try:
            if d.lstat().st_mtime >= seuil: continue
        except OSError: continue
        if not garde(d, racine, temp): refus += 1; continue
        n += 1 if a_blanc else _supprimer(d)
    return n, refus


def nettoyer_sauvegardes(racine, limite, a_blanc=False):
    """-> (supprimés, refus). Fichiers de B2B/donnees/sauvegardes datés (nom, sinon horodatage) avant la limite."""
    s = racine / "B2B" / "donnees" / "sauvegardes"; n = refus = 0
    if not s.is_dir(): return 0, 0
    seuil = datetime.combine(limite, datetime.min.time()).timestamp()
    for f in s.iterdir():
        m = DATE_NOM.search(f.name)
        vieux = m.group(1) < limite.isoformat() if m else f.lstat().st_mtime < seuil
        if not vieux: continue
        if not garde(f, racine): refus += 1; continue
        n += 1 if a_blanc else _supprimer(f)
    return n, refus


def nettoyer_pycache(racine, a_blanc=False):
    """-> (supprimés, refus). Tous les dossiers __pycache__ du dossier Jarvis (hors .git, node_modules, venv, memoire)."""
    n = refus = 0
    for dp, dns, _ in os.walk(racine):
        for d in [d for d in dns if d == "__pycache__"]:
            dns.remove(d); p = Path(dp) / d
            if not garde(p, racine): refus += 1; continue
            n += 1 if a_blanc else _supprimer(p)
        dns[:] = [d for d in dns if d.lower() not in SAUTES_PYCACHE and not os.path.islink(os.path.join(dp, d))]
    return n, refus


def vieux_sans_lien(racine, seuil):
    """-> [(chemin relatif, octets, date)] : fichiers modifiés avant le seuil, absents d'INDEX.md, hors code, skills, docs,
    médias, .canvas et fichiers protégés. Lecture seule."""
    try: index = (racine / "INDEX.md").read_text(encoding="utf-8-sig")
    except OSError: index = ""
    out = []
    for dp, dns, fns in os.walk(racine):
        rel_d = Path(dp).relative_to(racine).as_posix()
        dns[:] = [d for d in dns if d.lower() not in SAUTES_RAPPORT and not os.path.islink(os.path.join(dp, d))
                  and (f"{rel_d}/{d}" if rel_d != "." else d) not in SAUTES_RAPPORT_REL]
        for nom in fns:
            f = Path(dp) / nom
            if f.suffix.lower() in EXT_GARDEES or protege(f) or f.is_symlink(): continue
            rel = f.relative_to(racine).as_posix()
            if rel in index or rel.replace("/", "\\") in index or nom in index: continue
            try: st = f.stat()
            except OSError: continue
            if st.st_mtime < seuil: out.append((rel, st.st_size, date.fromtimestamp(st.st_mtime).isoformat()))
    return sorted(out, key=lambda x: -x[1])


def ecrire_rapport(racine, jour, liste):
    """Écrit B2B/a-valider/nettoyage-AAAA-MM-JJ.md (rien n'est supprimé : Liam décide). -> chemin."""
    f = racine / "B2B" / "a-valider" / f"nettoyage-{jour}.md"; f.parent.mkdir(parents=True, exist_ok=True)
    total = sum(x[1] for x in liste) / 1e6
    lignes = [f"# Nettoyage : fichiers à vérifier ({jour})", "",
              f"Agent nettoyage-fichiers. {len(liste)} fichier(s) de plus de {JOURS_RAPPORT} jours sans lien dans INDEX.md ({total:.1f} Mo).",
              "**Rien n'a été supprimé.** Liam décide fichier par fichier ; code, skills, docs, médias, .canvas et fichiers protégés sont exclus.", "",
              "| Fichier | Taille | Modifié le |", "|---|---:|---|"]
    lignes += [f"| `{r}` | {o / 1e3:.0f} Ko | {d} |" for r, o, d in liste[:300]]
    if len(liste) > 300: lignes += ["", f"… et {len(liste) - 300} autre(s), les plus petits."]
    f.write_text("\n".join(lignes) + "\n", encoding="utf-8")
    return f


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


def passage(racine=RACINE, jours=30, a_blanc=False, aujourdhui=None, temp=None):
    """temp=None : %TEMP% n'est pas regardé (tests) ; main() passe tempfile.gettempdir()."""
    jour = aujourdhui or date.today(); limite = jour - timedelta(days=jours)
    maintenant = datetime.combine(jour, datetime.now().time()).timestamp()
    t, refus = nettoyer_traces(racine, limite, a_blanc)
    j = nettoyer_journal(racine, limite, a_blanc)
    tp, r1 = nettoyer_temp(racine, temp, maintenant - JOURS_TEMP * 86400, a_blanc)
    s, r2 = nettoyer_sauvegardes(racine, limite, a_blanc)
    pc, r3 = nettoyer_pycache(racine, a_blanc)
    liste = vieux_sans_lien(racine, maintenant - JOURS_RAPPORT * 86400)
    rapport = str(ecrire_rapport(racine, jour.isoformat(), liste)) if liste and not a_blanc else ""
    return {"limite": limite.isoformat(), "traces": t, "journal": j, "temp": tp, "sauvegardes": s, "pycache": pc,
            "a_verifier": len(liste), "rapport": rapport, "refus": refus + r1 + r2 + r3, "a_blanc": a_blanc}


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
        r = passage(jours=a.jours, a_blanc=a.a_blanc, temp=tempfile.gettempdir())
    except OSError as e:
        T.ecrire(AGENT, "nettoyer", "erreur", time.time() - t0, ok=False, erreur=type(e).__name__)
        print(f"  ! erreur de fichier : {e.strerror or type(e).__name__}"); return 2
    texte = (f"{r['traces']} trace(s) et {r['journal']} entrée(s) du journal avant le {r['limite']}, {r['temp']} dossier(s) temporaire(s) de test, "
             f"{r['sauvegardes']} sauvegarde(s), {r['pycache']} __pycache__" + (" (à blanc, rien supprimé)" if a.a_blanc else " supprimés")
             + (f", {r['refus']} refusé(s) par la garde" if r["refus"] else "")
             + (f" ; {r['a_verifier']} vieux fichier(s) à vérifier" + (f" (rapport B2B\\a-valider\\{Path(r['rapport']).name})" if r["rapport"] else "") if r["a_verifier"] else ""))
    T.ecrire(AGENT, "nettoyer" + (" --a-blanc" if a.a_blanc else ""), texte, time.time() - t0, ok=True)
    try:
        with JOURNAL.open("a", encoding="utf-8") as f: f.write(f"{datetime.now():%Y-%m-%d %H:%M} | nettoyer | {texte}\n")
    except OSError: pass
    print(texte); return 0


if __name__ == "__main__":
    sys.exit(main())
