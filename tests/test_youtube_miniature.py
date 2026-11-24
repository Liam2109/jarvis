#!/usr/bin/env python3
"""Test silencieux de outils\\youtube-miniature.py sur une vidéo factice (dossier temporaire, rien d'ouvert,
ni son, ni fenêtre). Lancer : python tests\\test_youtube_miniature.py"""
import hashlib
import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

RACINE = Path(__file__).resolve().parent.parent
OUTIL = RACINE / "outils" / "youtube-miniature.py"
spec = importlib.util.spec_from_file_location("ytmin", OUTIL)
ytmin = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ytmin)

ECHECS = []


def verifier(nom, condition, detail=""):
    print(("OK      " if condition else "ECHEC   ") + nom + (f" ({detail})" if detail else ""))
    if not condition:
        ECHECS.append(nom)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def image_factice(w, h, avec_visage, bruit):
    """Décor texturé + visage dessiné (peau, yeux, sourcils, nez, bouche) du côté gauche."""
    rng = np.random.default_rng(7)
    fond = np.full((h, w, 3), (90, 70, 50), np.uint8)
    fond = cv2.add(fond, rng.integers(0, 30, (h, w, 3), dtype=np.uint8))
    if avec_visage:
        cx, cy, r = int(w * 0.28), int(h * 0.45), int(min(w, h) * 0.22)
        cv2.ellipse(fond, (cx, cy), (int(r * 0.8), r), 0, 0, 360, (150, 175, 225), -1)
        for dx in (-1, 1):
            ex = cx + dx * int(r * 0.32)
            cv2.rectangle(fond, (ex - int(r * 0.22), cy - int(r * 0.28)), (ex + int(r * 0.22), cy - int(r * 0.2)), (30, 30, 30), -1)
            cv2.ellipse(fond, (ex, cy - int(r * 0.08)), (int(r * 0.17), int(r * 0.1)), 0, 0, 360, (240, 240, 240), -1)
            cv2.circle(fond, (ex, cy - int(r * 0.08)), int(r * 0.08), (20, 20, 20), -1)
        cv2.line(fond, (cx, cy), (cx - 5, cy + int(r * 0.3)), (110, 135, 190), 6)
        cv2.ellipse(fond, (cx, cy + int(r * 0.55)), (int(r * 0.3), int(r * 0.1)), 0, 0, 360, (60, 60, 160), -1)
    if bruit:  # flou de bougé : images à écarter
        fond = cv2.GaussianBlur(fond, (0, 0), 9)
    return fond


def video_factice(chemin, avec_visage=True, w=1280, h=720, secondes=4, fps=10):
    ecr = cv2.VideoWriter(str(chemin), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    n = secondes * fps
    for i in range(n):
        ecr.write(image_factice(w, h, avec_visage, bruit=(i < n // 3)))
    ecr.release()


def lancer(args):
    return subprocess.run([sys.executable, str(OUTIL)] + args, capture_output=True, text=True, encoding="utf-8")


def main():
    with tempfile.TemporaryDirectory(prefix="yt-test-") as tmp:
        tmp = Path(tmp)
        entrees, sorties, cands = tmp / "entrees", tmp / "sorties", tmp / "candidats"
        entrees.mkdir()
        video = entrees / "demo.mp4"
        video_factice(video, avec_visage=True)
        h_avant = sha(video)
        verifier("vidéo factice créée", video.stat().st_size > 1000, f"{video.stat().st_size} octets")

        # 1. détecteur réel sur le visage dessiné (information : un dessin n'est pas un vrai visage)
        img = image_factice(1280, 720, True, False)
        trouves = ytmin.detecter_visages(img)
        print(f"INFO    détecteur réel sur le visage dessiné : {len(trouves)} visage(s) {trouves[:1]}")

        # 2. chaîne complète, visage forcé (le dessin ne remplace pas un vrai visage pour le détecteur)
        r = lancer([str(video), "--texte", "SITE WEB ZERO EURO", "--cle", "SITE",
                    "--titre", "Je CRÉE un SITE WEB pour 0 € : défi jour 1",
                    "--resume", "Premier jour du défi : je construis mon premier site.",
                    "--nom", "demo", "--sorties", str(sorties), "--dossier-candidats", str(cands),
                    "--visage", "0.14,0.23,0.28,0.44", "--cote", "gauche"])
        print(r.stdout.strip())
        verifier("outil terminé sans erreur", r.returncode == 0, r.stderr.strip()[:200])
        sortie = sorties / "demo"
        for f in ("titre.txt", "description.txt", "miniature.jpg"):
            verifier(f"{f} écrit", (sortie / f).is_file())
        if (sortie / "miniature.jpg").is_file():
            im = Image.open(sortie / "miniature.jpg")
            verifier("miniature 1280x720 JPEG", im.size == (1280, 720) and im.format == "JPEG", f"{im.size} {im.format}")
            verifier("miniature sous 2 Mo", (sortie / "miniature.jpg").stat().st_size < 2_000_000,
                     f"{(sortie / 'miniature.jpg').stat().st_size / 1e6:.2f} Mo")
            a = np.asarray(im.convert("RGB")).astype(int)
            jaune = ((a[:, :, 0] > 220) & (a[:, :, 1] > 180) & (a[:, :, 2] < 80)).sum()
            blanc = ((a[:, :, 0] > 245) & (a[:, :, 1] > 245) & (a[:, :, 2] > 245)).sum()
            verifier("texte blanc et mot-clé jaune présents", jaune > 2000 and blanc > 2000, f"jaune {jaune} px, blanc {blanc} px")
            moitie_texte = a[:, LARG_MOITIE:, :]
            noir = ((moitie_texte.sum(axis=2)) < 40).sum()
            verifier("contour noir épais côté texte", noir > 5000, f"{noir} px")
        d = (sortie / "description.txt").read_text(encoding="utf-8")
        verifier("description = résumé + bloc fixe tel quel", d.endswith(ytmin.DESCRIPTION_FIXE) and "LM MULTI-SERVICES" in d
                 and "Contact : emoliam255@gmail.com" in d and "https://www.tiktok.com/@lmmultiservices" in d
                 and "https://www.instagram.com/liam_2109/" in d)
        t = (sortie / "titre.txt").read_text(encoding="utf-8").strip()
        verifier("titre écrit, moins de 70 caractères", 0 < len(t) <= 70, f"{len(t)} car. : {t}")
        verifier("candidats enregistrés", len(list((cands / "demo").glob("candidat-*.jpg"))) >= 1,
                 f"{len(list((cands / 'demo').glob('candidat-*.jpg')))} fichier(s)")
        verifier("vidéo d'origine intacte", sha(video) == h_avant)

        # 3. géométrie : boîte noire à droite d'un cadre blanc -> centre au 2/3, côté gauche libre
        cadre = np.full((1080, 1920, 3), 255, np.uint8)
        cv2.rectangle(cadre, (1300, 300), (1500, 560), (0, 0, 0), -1)
        comp, cote, _ = ytmin.composer_image(cadre, (1300, 300, 200, 260))
        arr = np.asarray(comp).astype(int)
        sombre = np.argwhere(arr.sum(axis=2) < 30)
        cx = sombre[:, 1].mean() if len(sombre) else -1
        verifier("visage à droite -> côté « droite »", cote == "droite")
        verifier("visage centré à environ un tiers du bord", abs(cx - 2 * 1280 / 3) < 40, f"x = {cx:.0f}, attendu {2 * 1280 / 3:.0f}")
        verifier("place libre de l'autre côté", (sombre[:, 1] > 1280 * 0.45).all() if len(sombre) else False)

        # 4. vidéo verticale (téléphone) : fond flou, jamais d'étirement (bords de l'image d'origine proportionnels)
        vert = tmp / "entrees" / "vertical.mp4"
        video_factice(vert, avec_visage=True, w=720, h=1280)
        r = lancer([str(vert), "--texte", "TROIS MOTS ICI", "--nom", "vertical", "--sorties", str(sorties),
                    "--dossier-candidats", str(cands), "--visage", "0.14,0.23,0.28,0.2", "--cote", "droite"])
        verifier("vidéo verticale : miniature 1280x720",
                 r.returncode == 0 and Image.open(sorties / "vertical" / "miniature.jpg").size == (1280, 720), r.stderr.strip()[:200])

        # 5. refus : titres et textes invalides
        for nom, titre in (("emoji", "Je crée un SITE WEB 🔥"), ("trop long", "SITE WEB " + "x" * 70),
                           ("1 seul mot-clé", "Je crée un SITE pour 0 euro"), ("4 mots-clés", "UN SITE WEB EN LIGNE")):
            try:
                ytmin.valider_titre(titre)
                verifier(f"titre refusé : {nom}", False)
            except ytmin.Erreur:
                verifier(f"titre refusé : {nom}", True)
        try:
            ytmin.valider_texte("DEUX MOTS", None)
            verifier("texte de 2 mots refusé", False)
        except ytmin.Erreur:
            verifier("texte de 2 mots refusé", True)

        # 6. aucun visage : prévient (pas de fausse promesse)
        sans = entrees / "sans-visage.mp4"
        video_factice(sans, avec_visage=False)
        r = lancer([str(sans), "--candidats-seulement", "--dossier-candidats", str(cands)])
        verifier("sans visage : l'outil le dit", r.returncode == 0 and "aucun visage détecté" in r.stdout.lower(), r.stdout.strip()[:120])

        # 7. jamais d'écriture dans youtube\entrees
        r = lancer([str(video), "--candidats-seulement", "--dossier-candidats", str(entrees)])
        verifier("écriture dans entrees refusée", r.returncode == 2 and "entrees" in r.stderr)
        verifier("vidéo d'origine toujours intacte", sha(video) == h_avant)

    print()
    print("TOUT EST VERT" if not ECHECS else f"{len(ECHECS)} ECHEC(S) : {', '.join(ECHECS)}")
    return 1 if ECHECS else 0


LARG_MOITIE = 640

if __name__ == "__main__":
    sys.exit(main())
