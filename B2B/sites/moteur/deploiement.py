#!/usr/bin/env python3
"""Prépare sites\\deploiement\\ : le dossier à envoyer sur UN projet Vercel (maquettes choisies + assets + vercel.json + robots.txt).
  python sites\\moteur\\deploiement.py --fictives     les maquettes marquées exemple (hors pages de test)
  python sites\\moteur\\deploiement.py nom1 nom2      des dossiers précis de sites\\public\\
Ne publie rien : l'envoi sur Vercel se fait seulement avec l'accord de Liam."""
import json, shutil, sys
from pathlib import Path

SITES = Path(__file__).resolve().parent.parent
PUBLIC, DEST = SITES / "public", SITES / "deploiement"
manifeste = json.loads((SITES / "sorties" / "manifeste.json").read_text(encoding="utf-8"))
args = sys.argv[1:]
if args == ["--fictives"]: choix = [d for d, m in manifeste.items() if m.get("exemple") and "-test-" not in d]
else: choix = [a for a in args if (PUBLIC / a / "index.html").exists()]
if not choix: sys.exit("Rien à préparer.")
if DEST.exists(): shutil.rmtree(DEST)
DEST.mkdir()
for f in ("assets", "vercel.json", "robots.txt", "index.html"):
    s = PUBLIC / f
    shutil.copytree(s, DEST / f) if s.is_dir() else shutil.copy2(s, DEST / f)
for d in choix: shutil.copytree(PUBLIC / d, DEST / d)
print(f"{len(choix)} maquette(s) dans {DEST} :")
for d in choix: print("  /" + d + "/")
print("Taille :", round(sum(f.stat().st_size for f in DEST.rglob("*") if f.is_file()) / 1e6, 1), "Mo")
