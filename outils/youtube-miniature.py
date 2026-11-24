#!/usr/bin/env python3
"""Miniature YouTube de Liam (24/11/2026) : à partir d'une vidéo, extrait des images nettes où le visage
est visible, choisit la meilleure (ou celle que Liam indique), compose la miniature 1280x720 et écrit
titre.txt, description.txt, miniature.jpg dans un dossier par vidéo.

Accepte aussi des photos JPG/PNG (un ou plusieurs fichiers, ou un dossier) : pas d'extraction d'images,
recadrage direct en 16:9, visage à environ un tiers du cadre. Une seule photo = miniature.jpg ; plusieurs =
miniature-<nom de la photo>.jpg, toutes dans le même dossier de sortie.

Dépendances (gratuites) : Pillow, opencv-python-headless (version 4.x : la 5.x n'a plus de détecteur de visage).
Ne modifie jamais la vidéo ni les photos d'origine : elles sont seulement lues.

Exemples :
  python outils\\youtube-miniature.py --candidats-seulement                    (dernière vidéo de youtube\\entrees)
  python outils\\youtube-miniature.py ma-video.mp4 --texte "SITE WEB 0 EURO" --cle SITE --titre "..." [--choix 2]
  python outils\\youtube-miniature.py photo1.jpg photo2.png --texte "SITE WEB 0 EURO" --nom defi
  python outils\\youtube-miniature.py C:\\photos\\defi --texte "SITE WEB 0 EURO"      (dossier de photos et/ou vidéos)
"""
import argparse
import os
import re
import sys
import unicodedata
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

LARG, HAUT = 1280, 720
JAUNE = (255, 212, 0)
BLANC = (255, 255, 255)
NOIR = (0, 0, 0)
MAX_OCTETS = 1_900_000  # sous 2 Mo avec marge
EXT_VIDEO = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".wmv"}
EXT_PHOTO = {".jpg", ".jpeg", ".png"}
RACINE = Path(__file__).resolve().parent.parent
DOSSIER_ENTREES = RACINE / "youtube" / "entrees"
DOSSIER_SORTIES = RACINE / "youtube" / "sorties"
DOSSIER_CANDIDATS = RACINE / "youtube" / "candidats"

DESCRIPTION_FIXE = (
    "LM MULTI-SERVICES\n"
    "Contact : emoliam255@gmail.com\n"
    "TikTok : https://www.tiktok.com/@lmmultiservices\n"
    "Instagram : https://www.instagram.com/liam_2109/\n"
)


class Erreur(Exception):
    pass


# ---------------------------------------------------------------- détection du visage
_CASCADES = []


def _cascades():
    if not _CASCADES:
        if not hasattr(cv2, "CascadeClassifier") or not hasattr(cv2, "data"):
            raise Erreur("OpenCV sans détecteur de visage : installer opencv-python-headless<5")
        for nom in ("haarcascade_frontalface_alt2.xml", "haarcascade_frontalface_default.xml"):
            c = cv2.CascadeClassifier(os.path.join(cv2.data.haarcascades, nom))
            if not c.empty():
                _CASCADES.append(c)
        if not _CASCADES:
            raise Erreur("détecteur de visage introuvable dans OpenCV")
    return _CASCADES


def detecter_visages(img_bgr):
    """Liste de (x, y, l, h) en pixels de l'image d'origine, du plus grand au plus petit."""
    h0, l0 = img_bgr.shape[:2]
    k = min(1.0, 960.0 / l0)
    petit = cv2.resize(img_bgr, None, fx=k, fy=k, interpolation=cv2.INTER_AREA) if k < 1 else img_bgr
    gris = cv2.equalizeHist(cv2.cvtColor(petit, cv2.COLOR_BGR2GRAY))
    mini = max(24, int(0.06 * gris.shape[0]))
    for c in _cascades():
        res = c.detectMultiScale(gris, scaleFactor=1.1, minNeighbors=6, minSize=(mini, mini))
        if len(res):
            boites = [(int(x / k), int(y / k), int(w / k), int(h / k)) for x, y, w, h in res]
            return sorted(boites, key=lambda b: b[2] * b[3], reverse=True)
    return []


def _nettete(gris):
    return float(cv2.Laplacian(gris, cv2.CV_64F).var())


def noter(img_bgr, boite):
    """Note d'une image : netteté du visage x racine de sa taille ; 0 si coupé ou mal exposé."""
    h0, l0 = img_bgr.shape[:2]
    gris = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    if boite is None:
        return _nettete(gris)
    x, y, w, h = boite
    if x < 0 or y < 0 or x + w > l0 or y + h > h0:
        return 0.0
    visage = cv2.resize(gris[y:y + h, x:x + w], (192, 192), interpolation=cv2.INTER_AREA)
    lum = float(visage.mean())
    expo = 1.0 if 55 <= lum <= 210 else 0.4
    return _nettete(visage) * ((w * h) / float(l0 * h0)) ** 0.5 * expo


# ---------------------------------------------------------------- extraction des candidats
def extraire_candidats(video, nb=5, echantillons=60):
    """Renvoie (candidats, visage_trouve). candidat = dict(idx, t, boite, note, image BGR)."""
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise Erreur(f"vidéo illisible : {video}")
    try:
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 25.0)
        if total <= 0:
            raise Erreur("nombre d'images de la vidéo inconnu")
        debut, fin = int(total * 0.02), max(int(total * 0.02) + 1, int(total * 0.98))
        indices = sorted(set(int(i) for i in np.linspace(debut, fin - 1, min(echantillons, fin - debut))))
        mesures = []
        for idx in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ok, img = cap.read()
            if not ok or img is None:
                continue
            visages = detecter_visages(img)
            boite = visages[0] if visages else None
            mesures.append({"idx": idx, "t": idx / fps, "boite": boite, "note": noter(img, boite)})
        if not mesures:
            raise Erreur("aucune image lisible dans la vidéo")
        avec_visage = [m for m in mesures if m["boite"] is not None and m["note"] > 0]
        pool = avec_visage if avec_visage else mesures
        pool = sorted(pool, key=lambda m: m["note"], reverse=True)
        ecart = max(1, total // (2 * nb))
        choisis = []
        for m in pool:
            if all(abs(m["idx"] - c["idx"]) >= ecart for c in choisis):
                choisis.append(m)
            if len(choisis) == nb:
                break
        for m in choisis:
            cap.set(cv2.CAP_PROP_POS_FRAMES, m["idx"])
            ok, img = cap.read()
            m["image"] = img if ok else None
        choisis = [m for m in choisis if m.get("image") is not None]
        if not choisis:
            raise Erreur("impossible de relire les images choisies")
        return choisis, bool(avec_visage)
    finally:
        cap.release()


def enregistrer_candidats(candidats, dossier):
    dossier.mkdir(parents=True, exist_ok=True)
    for ancien in dossier.glob("candidat-*.jpg"):  # seulement nos propres fichiers
        ancien.unlink()
    chemins = []
    for i, c in enumerate(candidats, 1):
        p = dossier / f"candidat-{i}.jpg"
        cv2.imwrite(str(p), c["image"], [cv2.IMWRITE_JPEG_QUALITY, 95])
        chemins.append(p)
    return chemins


# ---------------------------------------------------------------- composition
def _police(taille):
    windir = os.environ.get("WINDIR", r"C:\Windows")
    for nom in ("impact.ttf", "ariblk.ttf"):
        p = os.path.join(windir, "Fonts", nom)
        if os.path.exists(p):
            return ImageFont.truetype(p, taille)
    raise Erreur("police Impact / Arial Black introuvable dans Windows\\Fonts")


def _fond_flou(img_rgb):
    """Image entière agrandie pour couvrir 1280x720 (recadrée au centre) puis floutée : jamais d'étirement."""
    w, h = img_rgb.size
    k = max(LARG / w, HAUT / h)
    g = img_rgb.resize((max(LARG, round(w * k)), max(HAUT, round(h * k))), Image.LANCZOS)
    x0, y0 = (g.width - LARG) // 2, (g.height - HAUT) // 2
    g = g.crop((x0, y0, x0 + LARG, y0 + HAUT))
    g = g.filter(ImageFilter.GaussianBlur(28))
    return ImageEnhance.Brightness(g).enhance(0.75)


def composer_image(img_bgr, boite, cote=None):
    """Canvas 1280x720 : visage ~ au tiers, d'un côté. Renvoie (image RGB, cote, visage_connu)."""
    h0, l0 = img_bgr.shape[:2]
    connu = boite is not None
    if boite is None:  # repli honnête : sujet supposé au centre haut, taille moyenne
        hh = int(0.22 * h0)
        boite = (int(l0 / 2 - hh / 2), int(0.28 * h0), hh, hh)
    x, y, w, h = boite
    cx, cy = x + w / 2.0, y + h / 2.0
    if cote not in ("gauche", "droite"):
        cote = "gauche" if cx < l0 / 2 else "droite"
    cible_x = LARG / 3.0 if cote == "gauche" else 2 * LARG / 3.0
    cible_y = HAUT * 0.46
    s = min(3.0, max(0.2, 0.42 * HAUT / float(h)))
    rgb = Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))
    fond = _fond_flou(rgb)
    fw, fh = max(1, round(l0 * s)), max(1, round(h0 * s))
    av = rgb.resize((fw, fh), Image.LANCZOS)
    ox, oy = round(cible_x - cx * s), round(cible_y - cy * s)
    # masque à bords adoucis, seulement sur les bords qui sont à l'intérieur de la miniature
    marge, bord = 80, 14
    masque = Image.new("L", (LARG + 2 * marge, HAUT + 2 * marge), 0)
    x0 = ox + marge + (bord if ox > 0 else -marge)
    y0 = oy + marge + (bord if oy > 0 else -marge)
    x1 = ox + fw + marge - (bord if ox + fw < LARG else -marge)
    y1 = oy + fh + marge - (bord if oy + fh < HAUT else -marge)
    ImageDraw.Draw(masque).rectangle((x0, y0, x1, y1), fill=255)
    masque = masque.filter(ImageFilter.GaussianBlur(bord / 2.0)).crop((marge, marge, marge + LARG, marge + HAUT))
    couche = Image.new("RGB", (LARG, HAUT))
    couche.paste(av, (ox, oy))
    canvas = Image.composite(couche, fond, masque)
    return _finition(canvas, cote), cote, connu


def _finition(canvas, cote):
    canvas = ImageEnhance.Contrast(canvas).enhance(1.08)
    canvas = ImageEnhance.Color(canvas).enhance(1.12)
    # dégradé sombre côté texte, pour la lisibilité
    xs = np.linspace(0.0, 1.0, LARG)
    a = np.clip((xs - 0.35) / 0.65, 0, 1) if cote == "gauche" else np.clip((0.65 - xs) / 0.65, 0, 1)
    a = (a * 0.5)[None, :, None]
    arr = np.asarray(canvas, dtype=np.float32) * (1 - a)
    return Image.fromarray(arr.astype(np.uint8))


def composer_photo(img_bgr, boite, cote=None):
    """Photo : recadrage direct en 16:9 (pas de fond flou), visage à ~ un tiers du cadre.
    Renvoie (image RGB 1280x720, cote, visage_connu). Le cadre est toujours rempli par la photo."""
    h0, l0 = img_bgr.shape[:2]
    connu = boite is not None
    if boite is None:
        hh = int(0.22 * h0)
        boite = (int(l0 / 2 - hh / 2), int(0.28 * h0), hh, hh)
    x, y, w, h = boite
    cx, cy = x + w / 2.0, y + h / 2.0
    if cote not in ("gauche", "droite"):
        cote = "gauche" if cx < l0 / 2 else "droite"
    cible_x = LARG / 3.0 if cote == "gauche" else 2 * LARG / 3.0
    cible_y = HAUT * 0.46
    couvre = max(LARG / float(l0), HAUT / float(h0))
    s = max(couvre, min(3.0, 0.42 * HAUT / float(h)))
    fw, fh = max(LARG, round(l0 * s)), max(HAUT, round(h0 * s))
    rgb = Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)).resize((fw, fh), Image.LANCZOS)
    ox = min(0, max(LARG - fw, round(cible_x - cx * s)))
    oy = min(0, max(HAUT - fh, round(cible_y - cy * s)))
    return _finition(rgb.crop((-ox, -oy, -ox + LARG, -oy + HAUT)), cote), cote, connu


def lire_photo(chemin):
    """Photo JPG/PNG -> tableau BGR (orientation EXIF respectée). Le fichier n'est que lu."""
    try:
        with Image.open(chemin) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            return cv2.cvtColor(np.asarray(im), cv2.COLOR_RGB2BGR)
    except Exception as e:
        raise Erreur(f"photo illisible : {chemin} ({e})")


def valider_texte(texte, cle):
    mots = texte.upper().split()
    if not 3 <= len(mots) <= 4:
        raise Erreur(f"--texte doit avoir 3 ou 4 mots (reçu {len(mots)})")
    if cle is None:
        cle = max(mots, key=len)
    cle = cle.upper()
    if cle not in mots:
        raise Erreur(f"--cle « {cle} » n'est pas dans le texte : {' '.join(mots)}")
    return mots, mots.index(cle)


def dessiner_texte(img, mots, i_cle, cote):
    zone_l = int(LARG * 0.43)
    zone_x = int(LARG * 0.545) if cote == "gauche" else int(LARG * 0.025)
    d = ImageDraw.Draw(img)
    n = len(mots)
    taille = 220
    while taille > 40:
        f = _police(taille)
        stroke = max(6, round(taille * 0.09))
        plus_large = max(d.textlength(m, font=f) for m in mots) + 2 * stroke
        if plus_large <= zone_l and n * taille * 1.0 <= HAUT * 0.9:
            break
        taille -= 4
    f = _police(taille)
    stroke = max(6, round(taille * 0.09))
    pas = taille * 1.0
    haut_bloc = pas * n
    y0 = (HAUT - haut_bloc) / 2.0 + pas / 2.0
    cx = zone_x + zone_l / 2.0
    for i, m in enumerate(mots):
        d.text((cx, y0 + i * pas), m, font=f, fill=JAUNE if i == i_cle else BLANC,
               stroke_width=stroke, stroke_fill=NOIR, anchor="mm")
    return taille


def exporter_jpg(img, chemin):
    q = 92
    while True:
        img.save(chemin, "JPEG", quality=q, optimize=True)
        if os.path.getsize(chemin) <= MAX_OCTETS or q <= 50:
            break
        q -= 6
    if os.path.getsize(chemin) > MAX_OCTETS:
        raise Erreur("miniature.jpg dépasse 2 Mo même à qualité 50")
    return os.path.getsize(chemin), q


# ---------------------------------------------------------------- titre et description
def _est_emoji(c):
    return ord(c) >= 0x1F000 or unicodedata.category(c) == "So" or c in "\u200d\ufe0f"


def valider_titre(titre):
    titre = titre.strip()
    if any(_est_emoji(c) for c in titre):
        raise Erreur("le titre ne doit contenir aucun emoji")
    if len(titre) > 70:
        raise Erreur(f"titre trop long ({len(titre)} caractères, visé : environ 60, 70 au plus)")
    majuscules = [m for m in re.findall(r"[^\W\d_]{2,}", titre) if m.isupper()]
    if not 2 <= len(majuscules) <= 3:
        raise Erreur(f"le titre doit avoir 2 à 3 mots-clés en MAJUSCULES (trouvé : {len(majuscules)})")
    return titre


def ecrire_textes(dossier, titre, resume):
    (dossier / "titre.txt").write_text(valider_titre(titre) + "\n", encoding="utf-8")
    corps = (resume.strip() + "\n\n" if resume and resume.strip() else "") + DESCRIPTION_FIXE
    (dossier / "description.txt").write_text(corps, encoding="utf-8")


# ---------------------------------------------------------------- ligne de commande
def _slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower() or "video"


def _derniere_video():
    vids = [p for p in DOSSIER_ENTREES.glob("*") if p.suffix.lower() in EXT_VIDEO] if DOSSIER_ENTREES.exists() else []
    if not vids:
        raise Erreur(f"aucune vidéo dans {DOSSIER_ENTREES}")
    return max(vids, key=lambda p: p.stat().st_mtime)


def _dans(chemin, parent):
    try:
        Path(chemin).resolve().relative_to(Path(parent).resolve())
        return True
    except ValueError:
        return False


def collecter(entrees):
    """Fichiers vidéo/photo à traiter : fichiers donnés et contenu (non récursif) des dossiers donnés."""
    fichiers = []
    for e in entrees:
        p = Path(e)
        if p.is_dir():
            sous = sorted(f for f in p.iterdir() if f.is_file() and f.suffix.lower() in EXT_VIDEO | EXT_PHOTO)
            if not sous:
                raise Erreur(f"aucune photo ni vidéo dans le dossier : {p}")
            fichiers += sous
        elif p.is_file():
            if p.suffix.lower() not in EXT_VIDEO | EXT_PHOTO:
                raise Erreur(f"format non pris en charge : {p.name} (photos JPG/PNG ou vidéos)")
            fichiers.append(p)
        else:
            raise Erreur(f"fichier ou dossier introuvable : {p}")
    vus, uniques = set(), []
    for f in fichiers:
        r = f.resolve()
        if r not in vus:
            vus.add(r)
            uniques.append(f)
    return uniques


def traiter_photos(photos, nom, a, sorties):
    """Une miniature par photo dans sorties\\<nom> : miniature.jpg si une seule, sinon miniature-<photo>.jpg."""
    if a.candidats_seulement:
        print("Photos : pas de candidats à extraire (rien à faire avec --candidats-seulement).")
        return
    if not a.texte:
        raise Erreur("--texte est obligatoire pour composer la miniature")
    mots, i_cle = valider_texte(a.texte, a.cle)
    boite_forcee = None
    if a.visage:
        try:
            boite_forcee = [float(v) for v in a.visage.split(",")]
            if len(boite_forcee) != 4:
                raise ValueError
        except ValueError:
            raise Erreur("--visage attend X,Y,L,H (4 nombres entre 0 et 1)")
    dossier = sorties / nom
    dossier.mkdir(parents=True, exist_ok=True)
    pris = set()
    for photo in photos:
        img = lire_photo(photo)
        h0, l0 = img.shape[:2]
        if boite_forcee:
            fx, fy, fl, fh = boite_forcee
            boite = (int(fx * l0), int(fy * h0), int(fl * l0), int(fh * h0))
        else:
            visages = detecter_visages(img)
            boite = visages[0] if visages else None
        comp, cote, connu = composer_photo(img, boite, a.cote)
        taille = dessiner_texte(comp, mots, i_cle, cote)
        if len(photos) == 1:
            sortie = dossier / "miniature.jpg"
        else:
            base, n = f"miniature-{_slug(photo.stem)}", 2
            fichier = base
            while fichier in pris:
                fichier, n = f"{base}-{n}", n + 1
            pris.add(fichier)
            sortie = dossier / f"{fichier}.jpg"
        octets, q = exporter_jpg(comp, sortie)
        print(f"Photo : {photo} -> {sortie} ({LARG}x{HAUT}, {octets / 1e6:.2f} Mo, qualité {q}, police {taille} px, "
              f"visage à {cote}{'' if connu else ' ; ATTENTION visage non détecté, position supposée (utiliser --visage et --cote)'})")
    if a.titre:
        ecrire_textes(dossier, a.titre, a.resume)
        print(f"Textes : {dossier / 'titre.txt'}, {dossier / 'description.txt'}")


def principal(argv=None):
    ap = argparse.ArgumentParser(description="Miniature YouTube de Liam")
    ap.add_argument("entrees", nargs="*", help="vidéos et/ou photos JPG/PNG, ou dossiers (sinon : la vidéo la plus "
                                               "récente de youtube\\entrees)")
    ap.add_argument("--texte", help="3 ou 4 mots pour la miniature")
    ap.add_argument("--cle", help="le mot du texte à mettre en jaune (sinon : le plus long)")
    ap.add_argument("--titre", help="titre de la vidéo (écrit dans titre.txt)")
    ap.add_argument("--resume", help="une ou deux phrases vraies pour la description (avant le bloc fixe)")
    ap.add_argument("--nom", help="nom du dossier de sortie (sinon : nom de la vidéo)")
    ap.add_argument("--choix", type=int, help="numéro du candidat à utiliser (sinon : le meilleur)")
    ap.add_argument("--nb", type=int, default=5, help="nombre de candidats (5 par défaut)")
    ap.add_argument("--cote", choices=("gauche", "droite"), help="côté du visage (sinon : celui de la vidéo)")
    ap.add_argument("--visage", help="forcer le visage : X,Y,L,H en fractions de l'image (0 à 1)")
    ap.add_argument("--candidats-seulement", action="store_true", help="n'enregistrer que les candidats")
    ap.add_argument("--sorties", help="dossier parent des sorties (défaut : youtube\\sorties)")
    ap.add_argument("--dossier-candidats", help="dossier parent des candidats (défaut : youtube\\candidats)")
    a = ap.parse_args(argv)

    fichiers = collecter(a.entrees) if a.entrees else [_derniere_video()]
    videos = [f for f in fichiers if f.suffix.lower() in EXT_VIDEO]
    photos = [f for f in fichiers if f.suffix.lower() in EXT_PHOTO]
    sorties = Path(a.sorties) if a.sorties else DOSSIER_SORTIES
    cands = Path(a.dossier_candidats) if a.dossier_candidats else DOSSIER_CANDIDATS
    for f in fichiers:
        for d in (sorties, cands):
            if _dans(d, f.parent) or _dans(d, DOSSIER_ENTREES):
                raise Erreur("jamais d'écriture dans le dossier d'une vidéo ou d'une photo ni dans youtube\\entrees "
                             "(entrees) : choisir un autre dossier de sortie")

    for video in videos:
        seule = len(videos) == 1 and not photos
        traiter_video(video, _slug(a.nom or video.stem) if seule else _slug(video.stem), a, sorties, cands)
    if photos:
        if a.nom:
            nom = _slug(a.nom)
        elif len(photos) == 1:
            nom = _slug(photos[0].stem)
        elif len(a.entrees) == 1 and Path(a.entrees[0]).is_dir():
            nom = _slug(Path(a.entrees[0]).resolve().name)
        else:
            nom = "photos"
        traiter_photos(photos, nom, a, sorties)
    return 0


def traiter_video(video, nom, a, sorties, cands):
    print(f"Vidéo : {video}")
    candidats, trouve = extraire_candidats(video, nb=max(1, a.nb))
    chemins = enregistrer_candidats(candidats, cands / nom)
    if not trouve:
        print("ATTENTION : aucun visage détecté, images les plus nettes à la place (utiliser --visage et --cote).")
    for i, (c, p) in enumerate(zip(candidats, chemins), 1):
        v = "visage" if c["boite"] is not None else "sans visage"
        print(f"  candidat {i} : {p} (t = {c['t']:.1f} s, {v}, note {c['note']:.1f})")
    if a.candidats_seulement:
        return 0

    if not a.texte:
        raise Erreur("--texte est obligatoire pour composer la miniature")
    mots, i_cle = valider_texte(a.texte, a.cle)
    k = (a.choix or 1) - 1
    if not 0 <= k < len(candidats):
        raise Erreur(f"--choix doit être entre 1 et {len(candidats)}")
    c = candidats[k]
    boite = c["boite"]
    if a.visage:
        try:
            fx, fy, fl, fh = [float(v) for v in a.visage.split(",")]
        except ValueError:
            raise Erreur("--visage attend X,Y,L,H (4 nombres entre 0 et 1)")
        h0, l0 = c["image"].shape[:2]
        boite = (int(fx * l0), int(fy * h0), int(fl * l0), int(fh * h0))
    img, cote, connu = composer_image(c["image"], boite, a.cote)
    taille = dessiner_texte(img, mots, i_cle, cote)

    dossier = sorties / nom
    dossier.mkdir(parents=True, exist_ok=True)
    octets, q = exporter_jpg(img, dossier / "miniature.jpg")
    if a.titre:
        ecrire_textes(dossier, a.titre, a.resume)
    print(f"Choisi : candidat {k + 1}{' (le meilleur)' if k == 0 and not a.choix else ''}, "
          f"visage à {cote}{'' if connu else ' (position supposée : visage non détecté)'}")
    print(f"Miniature : {dossier / 'miniature.jpg'} ({LARG}x{HAUT}, {octets / 1e6:.2f} Mo, qualité {q}, police {taille} px)")
    if a.titre:
        print(f"Textes : {dossier / 'titre.txt'}, {dossier / 'description.txt'}")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    try:
        sys.exit(principal())
    except Erreur as e:
        print(f"ERREUR : {e}", file=sys.stderr)
        sys.exit(2)
