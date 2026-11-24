#!/usr/bin/env python3
"""Correctif Windows de stick-stage (tamtree-ai/stick-stage, cloné dans Videos\\outils\\stick-stage, hors git) — 16/11/2026.
Cause du plantage : stick-stage lance `execFileSync(path.join(<racine>, "node_modules/.bin/remotion"), [...])`. Sous Windows, `.bin\\remotion` est un script
shell (seuls `remotion.cmd` / `remotion.ps1` s'exécutent) et execFileSync ne passe pas par un shell : ENOENT, le rendu s'arrête.
Correctif : lancer Node lui-même sur le point d'entrée JavaScript du paquet (`node_modules/@remotion/cli/remotion-cli.js`, champ « bin » du paquet),
ce qui marche sous Windows, Linux et macOS, sans shell.
Second défaut (17/11/2026, sketch à deux : premiers personnages qui parlent à l'écran) : Rhubarb 1.14 sous Windows n'écrit RIEN sur la sortie standard avec
l'option « -q » ; la synchro des lèvres plante (« Unexpected end of JSON input »). Correctif : appeler Rhubarb sans « -q » (sa progression part sur stderr). Idempotent : relancer ne change rien ; à relancer après chaque nouveau clonage de l'outil.
  python Videos\\correctifs\\stick-stage-windows.py [--dossier CHEMIN] [--verifier]
--verifier : n'écrit rien, code 1 s'il reste un appel cassé."""
import argparse, re, sys
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent.parent / "outils" / "stick-stage"
FICHIERS = ("scripts/render.ts", "src/node/adapters.ts", "src/server/pipeline.ts")
CASSE = re.compile(r'execFileSync\(\s*path\.join\(\s*([\w.]+)\s*,\s*"node_modules/\.bin/remotion"\s*\)\s*,\s*\[')
REPARE = r'execFileSync(process.execPath, [path.join(\1, "node_modules/@remotion/cli/remotion-cli.js"), '

RHUBARB_CASSE = re.compile(r'\[\s*"-q"\s*,\s*"-f"\s*,\s*"json"')
RHUBARB_REPARE = '["-f", "json"'


def corriger_texte(texte):
    """-> (texte corrigé, nombre d'appels réparés)."""
    texte, n = CASSE.subn(REPARE, texte)
    texte, m = RHUBARB_CASSE.subn(RHUBARB_REPARE, texte)
    return texte, n + m


def corriger(dossier=DOSSIER, verifier=False):
    """-> (réparés, restants, fichiers absents)."""
    repares = restants = 0; absents = []
    for rel in FICHIERS:
        f = Path(dossier) / rel
        if not f.exists(): absents.append(rel); continue
        t = f.read_text(encoding="utf-8"); neuf, n = corriger_texte(t)
        if verifier: restants += n; continue
        if n: f.write_text(neuf, encoding="utf-8", newline=""); repares += n
    return repares, restants, absents


def main(argv=None):
    a = argparse.ArgumentParser(prog="stick-stage-windows"); a.add_argument("--dossier", default=str(DOSSIER)); a.add_argument("--verifier", action="store_true")
    a = a.parse_args(argv)
    if not Path(a.dossier).exists(): print(f"stick-stage absent ({a.dossier}) : rien à faire."); return 0
    repares, restants, absents = corriger(a.dossier, a.verifier)
    if absents: print(f"Fichiers introuvables (version de l'outil différente ?) : {', '.join(absents)}")
    if a.verifier:
        print("stick-stage : " + (f"{restants} appel(s) cassé(s) sous Windows" if restants else "aucun appel cassé")); return 1 if restants else 0
    print(f"stick-stage : {repares} appel(s) réparé(s)" if repares else "stick-stage : déjà corrigé"); return 0


if __name__ == "__main__":
    sys.exit(main())
