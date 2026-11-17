#!/usr/bin/env python3
"""Décors de jour de la ligne B (17/11/2026) dans stick-stage (tamtree-ai/stick-stage, MIT, cloné dans Videos\\outils\\stick-stage, hors git).
Les décors sont des DONNÉES (Videos\\stick-stage\\decors\\*.json, versionnés) qui placent des pièces déjà dessinées par l'outil (mur, comptoir, vitrine,
canapé…) : aucun code de dessin n'est écrit. stick-stage charge ses décors par import dans src/data/index.ts : ce script copie chaque fichier dans
src/data/sets/ et ajoute la ligne d'import et le nom dans la liste des décors. Idempotent ; à relancer après chaque nouveau clonage de l'outil
(creation.py le lance avant chaque rendu de sketch, sans effet s'il n'y a rien à faire).
  python Videos\\correctifs\\stick-stage-decors.py [--dossier CHEMIN] [--verifier]
--verifier : n'écrit rien, code 1 s'il manque un décor."""
import argparse, json, re, shutil, sys
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent.parent / "outils" / "stick-stage"
DECORS = Path(__file__).resolve().parent.parent / "stick-stage" / "decors"
ANCRE = "export const sets: Record<string, SetDef> = createSets(["


def nom_js(id_): return re.sub(r"-(\w)", lambda m: m.group(1).upper(), id_)


def installer(dossier=DOSSIER, decors=DECORS, verifier=False):
    """-> (ajoutés, manquants)."""
    index = Path(dossier) / "src" / "data" / "index.ts"
    if not index.exists(): return 0, ["src/data/index.ts introuvable"]
    t = index.read_text(encoding="utf-8"); ajoutes, manquants = 0, []
    for f in sorted(Path(decors).glob("*.json")):
        id_ = json.loads(f.read_text(encoding="utf-8"))["id"]; n = nom_js(id_)
        cible = Path(dossier) / "src" / "data" / "sets" / f.name
        imp = f'import {n} from "./sets/{f.name}";'
        a_jour = cible.exists() and cible.read_bytes() == f.read_bytes() and imp in t and f"\n  {n},\n" in t
        if a_jour: continue
        if verifier: manquants.append(id_); continue
        shutil.copy2(f, cible)
        if imp not in t:
            if ANCRE not in t: return ajoutes, [f"liste des décors introuvable dans index.ts ({ANCRE})"]
            t = t.replace(ANCRE, f"{imp}\n{ANCRE}", 1)
            i = t.index(ANCRE) + len(ANCRE); t = t[:i] + f"\n  {n}," + t[i:]
        ajoutes += 1
    if ajoutes: index.write_text(t, encoding="utf-8", newline="")
    return ajoutes, manquants


def main(argv=None):
    a = argparse.ArgumentParser(prog="stick-stage-decors"); a.add_argument("--dossier", default=str(DOSSIER)); a.add_argument("--verifier", action="store_true")
    a = a.parse_args(argv)
    if not Path(a.dossier).exists(): print(f"stick-stage absent ({a.dossier}) : rien à faire."); return 0
    ajoutes, manquants = installer(a.dossier, verifier=a.verifier)
    if a.verifier:
        print("stick-stage : " + (f"décors manquants : {', '.join(manquants)}" if manquants else "tous les décors sont installés")); return 1 if manquants else 0
    if manquants: print(f"! {'; '.join(manquants)}"); return 1
    print(f"stick-stage : {ajoutes} décor(s) installé(s)" if ajoutes else "stick-stage : décors déjà installés"); return 0


if __name__ == "__main__":
    sys.exit(main())
