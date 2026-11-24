#!/usr/bin/env python3
"""Agent sauvegarde-leads (LM MULTI-SERVICES, 24/11/2026) : le filet de sécurité des leads et des appels, sans token ni réseau ni Discord.

  python agents\\sauvegarde-leads.py sauvegarder [--a-blanc]   chaque nuit à 03:30 : copie les fichiers de leads, d'appels, de résultats d'appels, de leads chauds et de relances
                                                              dans B2B\\sauvegardes\\AAAA-MM-JJ\\ ; garde 30 jours, supprime les dossiers plus anciens
  python agents\\sauvegarde-leads.py archives                  liste ce qui a été supprimé (archive restaurable, voir archive.py)
  python agents\\sauvegarde-leads.py restaurer <id>            remet une entrée archivée à sa place (rien n'est écrasé)
  python agents\\sauvegarde-leads.py supprimer <registre|leads-chauds> <clé>   la seule façon de retirer un lead : archive d'abord, supprime ensuite
  python agents\\sauvegarde-leads.py etat                      dernière sauvegarde

Restaurer un fichier entier : copier le fichier voulu de B2B\\sauvegardes\\<jour>\\ à son emplacement d'origine (même chemin relatif, sous B2B\\).
Ne touche jamais .env, config.json ni *.local.json. Le journal ne contient ni nom ni numéro."""
import argparse, os, re, shutil, sys, time
from datetime import date, datetime, timedelta
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI)); sys.path.insert(0, str(ICI.parent / "harness"))
import machine as M   # noqa: E402
import archive as AR  # noqa: E402

AGENT = "sauvegarde-leads"
B2B = ICI.parent
DEST = B2B / "sauvegardes"
JOURNAL = ICI / f"{AGENT}-journal.log"
GARDE_JOURS = 30
# chemins relatifs à B2B\ : leads (registre, file des leads chauds, suivi), appels (états, historique, listes de Sid), résultats d'appels (registre + feuilles notées), relances, archive des suppressions
FICHIERS = ["donnees/registre-entreprises.json", "donnees/leads-chauds.json", "donnees/archive/archive.jsonl",
            "agents/relances-etat.json", "agents/appels-sid-etat.json", "agents/appels-sid-historique.json", "agents/appels-liam-etat.json",
            "suivi-prospects.csv", "prospection-trouves.csv"]
DOSSIERS = [("docs/sid", "*.csv")]
NOM_JOUR = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class ErreurAgent(Exception):
    pass


def journaliser(action, detail=""):
    with open(JOURNAL, "a", encoding="utf-8") as f: f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} | {action} | {detail}\n")


def sources(racine=None):
    """[(chemin relatif, chemin absolu)] des fichiers à copier qui existent."""
    racine = Path(racine or B2B); out = []
    for r in FICHIERS:
        if (racine / r).is_file(): out.append((r, racine / r))
    for d, motif in DOSSIERS:
        out += [(f"{d}/{p.name}", p) for p in sorted((racine / d).glob(motif)) if p.is_file()]
    return out


def sauvegarder(jour, racine=None, dest=None, a_blanc=False):
    """Copie les fichiers dans dest\\AAAA-MM-JJ\\ (construit à côté puis échangé : une copie ratée ne détruit jamais la sauvegarde précédente), vérifie les tailles. -> (copiés, supprimés)."""
    racine = Path(racine or B2B); dest = Path(dest or DEST); src = sources(racine)
    if not any(r.startswith("donnees/registre") for r, _ in src): raise ErreurAgent("registre-entreprises.json introuvable : rien de sauvegardé")
    if a_blanc: return len(src), len(anciennes(jour, dest))
    dest.mkdir(parents=True, exist_ok=True)
    tmp, final = dest / f"{jour}.tmp", dest / jour
    shutil.rmtree(tmp, ignore_errors=True); tmp.mkdir()
    try:
        for r, p in src:
            cible = tmp / r; cible.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(p, cible)
            if cible.stat().st_size != p.stat().st_size: raise ErreurAgent(f"copie incomplète : {r}")
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True); raise
    if final.exists(): shutil.rmtree(final)
    os.replace(tmp, final)
    return len(src), supprimer_anciennes(jour, dest)


def anciennes(jour, dest=None, garde=GARDE_JOURS):
    limite = date.fromisoformat(jour) - timedelta(days=garde); dest = Path(dest or DEST)
    if not dest.is_dir(): return []
    return [p for p in dest.iterdir() if p.is_dir() and NOM_JOUR.match(p.name) and date.fromisoformat(p.name) < limite]


def supprimer_anciennes(jour, dest=None, garde=GARDE_JOURS):
    """Supprime les sauvegardes de plus de 30 jours (seulement des dossiers AAAA-MM-JJ de B2B\\sauvegardes)."""
    n = 0
    for p in anciennes(jour, dest, garde):
        shutil.rmtree(p, ignore_errors=True); n += 1
    return n


def cmd_sauvegarder(a_blanc, jour=None):
    jour = jour or f"{date.today():%Y-%m-%d}"
    try: n, s = sauvegarder(jour, a_blanc=a_blanc)
    except (ErreurAgent, OSError) as e:
        print(f"  ! sauvegarde impossible : {e}"); journaliser("sauvegarder", f"{jour} : échec ({type(e).__name__})"); return 2
    print(f"{jour} : {n} fichier(s) {'à copier' if a_blanc else 'copié(s)'} dans B2B\\sauvegardes\\{jour}, {s} ancienne(s) sauvegarde(s) {'à supprimer' if a_blanc else 'supprimée(s)'} (au-delà de {GARDE_JOURS} jours)" + (" (à blanc, rien écrit)" if a_blanc else ""))
    if not a_blanc: journaliser("sauvegarder", f"{jour} : {n} fichier(s), {s} ancienne(s) supprimée(s)")
    return 0


def cmd_archives():
    xs = AR.archives()
    if not xs: print("Archive vide : rien n'a été supprimé."); return 0
    for l in xs[:50]: print(AR.decrire(l))
    print(f"{len(xs)} élément(s) archivé(s) ; restaurer : sauvegarde-leads.py restaurer <id>"); return 0


def cmd_etat():
    ds = sorted(p.name for p in DEST.iterdir() if p.is_dir() and NOM_JOUR.match(p.name)) if DEST.is_dir() else []
    print(f"{len(ds)} sauvegarde(s) ; dernière : {ds[-1] if ds else 'aucune'} ; {len(AR.archives())} élément(s) archivé(s)."); return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog=AGENT, description="Sauvegarde nocturne et archive restaurable des leads et des appels.")
    sp = p.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("sauvegarder"); s.add_argument("--a-blanc", "--essai", dest="a_blanc", action="store_true"); s.add_argument("--jour", default=None)
    sp.add_parser("archives"); sp.add_parser("etat")
    r = sp.add_parser("restaurer"); r.add_argument("id")
    d = sp.add_parser("supprimer"); d.add_argument("quoi", choices=AR.QUOI); d.add_argument("cle"); d.add_argument("--raison", default="suppression demandée")
    a = p.parse_args(argv)
    M.exiger(AGENT, a.cmd, getattr(a, "a_blanc", False) or a.cmd == "archives")
    try:
        if a.cmd == "etat": return cmd_etat()
        if a.cmd == "archives": return cmd_archives()
        if a.cmd == "restaurer": print("Restauré : " + AR.restaurer(a.id)); journaliser("restaurer", a.id); return 0
        if a.cmd == "supprimer": i = AR.supprimer(a.quoi, a.cle, a.raison); print(f"Archivé puis supprimé (id {i}) ; pour revenir en arrière : restaurer {i}"); journaliser("supprimer", f"{a.quoi} archivé {i}"); return 0
        return cmd_sauvegarder(a.a_blanc, a.jour)
    except AR.ErreurArchive as e:
        print(f"  ! {e}"); return 2


if __name__ == "__main__":
    _t0 = time.time(); _code = main()
    if sys.argv[1:2] == ["sauvegarder"] and not {"--a-blanc", "--essai"} & set(sys.argv):   # trace du harness, jamais bloquante
        try: import traces; traces.ecrire(AGENT, "sauvegarder", "terminé" if _code == 0 else "échec", time.time() - _t0, ok=_code == 0, erreur=None if _code == 0 else f"code {_code}")
        except Exception: pass
    sys.exit(_code)
