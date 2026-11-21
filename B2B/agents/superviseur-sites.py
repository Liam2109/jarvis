#!/usr/bin/env python3
"""Superviseur du domaine SITES (21/11/2026) : toutes les 30 minutes, il relit les fichiers de sites PRÉSENTS DANS LE DÉPÔT sur cette machine
(après un git pull : le serveur ne voit que ce que git transporte, jamais le gros PC) et signale ce qui ne va pas avant que Liam ne montre une page à un client :
lien interne cassé, image ou feuille de style absente, reste de texte d'exemple (« signes IA » interdits par B2B\\CLAUDE.md), page sans titre,
page exemple qui n'est plus en noindex, site vitrine mis en noindex par erreur, phrase interdite, lien de paiement inconnu, secret.

  python agents\\superviseur-sites.py passage [--essai] [--maintenant AAAA-MM-JJTHH:MM]   un passage (tâche serveur, toutes les 30 min)
  python agents\\superviseur-sites.py etat                                                verrou, dernier passage, corrections du jour, ce qui attend un « go »

CORRIGE SEUL : seulement les doublons strictement identiques du suivi des pages exemple (un fichier de données, hors git).
NE TOUCHE JAMAIS (alerte et attend « go ») : le contenu d'une page. Un HTML, un CSS ou un JS est du travail de Liam et de Claude Code, jamais réécrit par un agent :
corriger un lien ou un texte à l'aveugle casserait la page ou changerait ce que le client va lire.
VERROU : rien n'est corrigé et rien n'est posté tant que go_superviseurs n'est pas true dans un fichier de réglages local (après le « go superviseurs » de Liam). --essai marche toujours."""
import argparse, re, sys
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlparse

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import machine as M   # machine active (refus hors du serveur, sauf --essai)

sys.path.insert(0, str(ICI.parent / "harness"))
import superviseurs as S   # moteur commun

AGENT, DOMAINE = "superviseur-sites", "Sites"
AGENTS_SUIVIS = ["page-exemple"]      # agent inactif : signalé « jamais prevu » tant que Liam ne le planifie pas
DEFAUT = {"heure_resume": "08:45", "pages_max": 60, "sites_indexables": []}
RACINE = ICI.parent.parent
SITES = RACINE / "B2B" / "sites"
PAGES_EXEMPLE = RACINE / "B2B" / "pages-exemple"
SUIVI_PAGES = PAGES_EXEMPLE / "suivi.csv"
SANS_SITE = {"moteur", "deploiement", "node_modules", "dist", "assets"}
NOINDEX = re.compile(r"<meta[^>]+name\s*=\s*[\"']robots[\"'][^>]*noindex", re.I)
LIENS = re.compile(r"""(?:href|src|poster|data-src)\s*=\s*["']([^"']+)["']""", re.I)
CSS_URL = re.compile(r"url\(\s*['\"]?([^'\")]+)['\"]?\s*\)", re.I)
TITRE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
H1 = re.compile(r"<h1[^>]*>(.*?)</h1>", re.I | re.S)
BALISES = re.compile(r"<[^>]+>")
# « Signes IA » et restes de modèle interdits par B2B\CLAUDE.md (§ Sites, point 4) : un seul suffit à refuser une page devant un client.
SIGNES = [(re.compile(r"lorem ipsum", re.I), "texte de remplissage « lorem ipsum »"),
          (re.compile(r"\b(?:todo|fixme)\b", re.I), "marque de travail en cours (TODO / FIXME)"),
          (re.compile(r"\bplaceholder\b(?![^<>]*=)", re.I), "mot « placeholder » dans le texte"),
          (re.compile(r"votre (?:texte|titre|logo|slogan|photo) ici", re.I), "texte d'exemple « votre … ici »"),
          (re.compile(r"\{\{\s*\w+\s*\}\}|\[\[\s*\w+\s*\]\]|__\w+__"), "champ de modèle non remplacé"),
          (re.compile(r"\bnom de (?:l'|la |le )?(?:entreprise|commerce|société)\b", re.I), "nom du commerce non remplacé"),
          (re.compile(r"\bxxx+\b", re.I), "texte « xxx » laissé dans la page"),
          (re.compile(r"à compléter", re.I), "mention « à compléter » laissée dans la page")]


def dossiers_sites():
    """Dossiers de sites réellement présents dans le dépôt sur cette machine (un dossier = un index.html). Jamais de réseau, jamais le gros PC."""
    out = []
    for racine in (SITES, PAGES_EXEMPLE):
        if not racine.is_dir(): continue
        for d in sorted(x for x in racine.iterdir() if x.is_dir() and x.name not in SANS_SITE):
            if (d / "index.html").is_file(): out.append(d)
    return out


def pages(dossier, maxi):
    return sorted(dossier.rglob("*.html"))[:maxi]


MEDIAS = (".png", ".jpg", ".jpeg", ".webp", ".avif", ".gif", ".svg", ".ico", ".mp4", ".webm", ".mov", ".woff", ".woff2", ".ttf", ".otf")


def est_exemple(dossier, indexables=()):
    """Page exemple : noindex obligatoire (B2B\\CLAUDE.md § Sites, point 6). Un site qui doit au contraire être indexé se déclare dans
    « sites_indexables » des réglages : rien n'est deviné à partir du nom du dossier."""
    return dossier.name not in {str(x) for x in (indexables or ())}


def medias_transportes(dossier):
    """Vrai si ce dossier de site contient au moins une image, une vidéo ou une police sur cette machine. Faux = git ne transporte pas ses médias
    (c'est le cas sur le serveur : .gitignore ne versionne que le HTML, le CSS et le JS) : réclamer une image absente n'aurait aucun sens."""
    return any(p.suffix.lower() in MEDIAS for p in dossier.rglob("*") if p.is_file())


def cible_locale(valeur):
    """Chemin local visé par un href/src, ou None pour un lien externe, un ancrage, un mailto, un tel ou une donnée en ligne."""
    v = (valeur or "").strip()
    if not v or v.startswith(("#", "data:", "mailto:", "tel:", "javascript:", "//")): return None
    u = urlparse(v)
    if u.scheme or u.netloc: return None
    chemin = unquote(u.path)
    return chemin or None


def controle_une_page(dossier, page, exemple, medias=True):
    """Soucis d'une page : liens et fichiers absents, titre vide, noindex, signes IA, phrases interdites. Tout est RISQUÉ (une page n'est jamais réécrite)."""
    out = []
    rel = page.relative_to(RACINE).as_posix()
    try: t = page.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return [S.risque("sites", f"{rel} illisible", type(e).__name__, cle=f"{rel}|illisible")]
    manquants = []
    for v in set(LIENS.findall(t)) | set(CSS_URL.findall(t)):
        c = cible_locale(v)
        if not c: continue
        base = page.parent if not c.startswith("/") else dossier
        cible = (base / c.lstrip("/")).resolve()
        try: cible.relative_to(dossier.resolve())
        except ValueError:
            out.append(S.risque("sites", f"lien qui sort du site dans {rel}", f"« {c[:60]} » : à vérifier à la main", cle=f"{rel}|{c[:60]}|dehors")); continue
        if not cible.exists() and not (cible.suffix == "" and (cible / "index.html").exists()):
            manquants.append(c[:60])
    if manquants:
        images = [x for x in manquants if Path(x).suffix.lower() in MEDIAS]
        if images and medias:
            out.append(S.risque("sites", f"{len(images)} image(s), police(s) ou média(s) absent(s) dans {rel}", ", ".join(sorted(set(images))[:5]), cle=f"{rel}|medias-absents"))
        autres = [x for x in manquants if x not in images]
        if autres:
            out.append(S.risque("sites", f"{len(autres)} lien(s) interne(s) cassé(s) dans {rel}", ", ".join(sorted(set(autres))[:5]), cle=f"{rel}|liens-casses"))
    titre = BALISES.sub("", (TITRE.search(t).group(1) if TITRE.search(t) else "")).strip()
    if not titre:
        out.append(S.risque("sites", f"{rel} n'a pas de titre", "une page sans <title> ne se partage pas", cle=f"{rel}|titre"))
    if not H1.search(t):
        out.append(S.risque("sites", f"{rel} n'a pas de titre principal <h1>", "conformité minimale des pages (règles de style)", cle=f"{rel}|h1"))
    if exemple and not NOINDEX.search(t):
        out.append(S.risque("sites", f"{rel} n'est plus en noindex", "une page exemple reste en noindex (B2B\\CLAUDE.md § Sites, point 6)", cle=f"{rel}|noindex"))
    if not exemple and NOINDEX.search(t):
        out.append(S.risque("sites", f"{rel} (site vitrine) est en noindex", "le site de l'agence n'apparaîtra pas sur Google", cle=f"{rel}|noindex-vitrine"))
    texte_visible = BALISES.sub(" ", re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", t, flags=re.I | re.S))
    for rx, quoi in SIGNES:
        if rx.search(texte_visible):
            out.append(S.risque("sites", f"{quoi} dans {rel}", "reste de modèle ou de texte d'exemple : à corriger avant de montrer la page", cle=f"{rel}|{quoi[:30]}"))
    for faute in S.fautes_de_texte(t):
        out.append(S.risque("sites", f"{faute} dans {rel}", "contenu d'un site : jamais réécrit par un agent", cle=f"{rel}|{faute[:40]}"))
    return out


def controle_pages(maxi=None, indexables=()):
    """Aucun dossier de site dans le dépôt : rien à dire (normal sur le serveur, git ne transporte que le code des sites)."""
    out = []
    for d in dossiers_sites():
        exemple, medias = est_exemple(d, indexables), medias_transportes(d)
        for p in pages(d, int(maxi or DEFAUT["pages_max"])): out += controle_une_page(d, p, exemple, medias)
    return out


def controle_suivi_pages():
    """pages-exemple\\suivi.csv (hors git, données de l'agent page-exemple) : lignes en double, ou deux fiches pour le même lien."""
    return S.controle_doublons_csv("page-exemple", SUIVI_PAGES, "lien")


CONTROLES = [("pages du dépôt", controle_pages), ("suivi des pages exemple", controle_suivi_pages)]


def cmd_etat(conf):
    r = S.resume_pour_jarvis(AGENT, DOMAINE, conf)
    print(f"Superviseur {DOMAINE} : {r['etat']} ; verrou « go superviseurs » {r['verrou']} ; dernier passage : {r['dernier_passage'] or 'aucun'}.")
    ds = dossiers_sites()
    noms = ", ".join(d.name for d in ds) or "aucun (git ne transporte pas les sites, sauf celui de l'agence)"
    print(f"  sites lus dans le dépôt : {noms}")
    print(f"  corrections du jour : {len(r['corrections'])}" + ("".join(f"\n    - {x}" for x in r["corrections"][:10]) if r["corrections"] else ""))
    print(f"  en attente d'un « go » : {len(r['bloques'])}" + ("".join(f"\n    - {x}" for x in r["bloques"][:10]) if r["bloques"] else ""))
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog=AGENT, description="Superviseur du domaine Sites : fichiers du dépôt relus (liens, images, style, noindex), aucune page réécrite.")
    sp = p.add_subparsers(dest="cmd", required=True)
    j = sp.add_parser("passage"); j.add_argument("--essai", "--a-blanc", dest="essai", action="store_true", help="lit, affiche, n'écrit rien, n'envoie rien")
    j.add_argument("--maintenant", default=None, help="heure figée (tests)")
    sp.add_parser("etat")
    a = p.parse_args(argv)
    M.exiger(AGENT, a.cmd, getattr(a, "essai", False))
    try:
        conf = S.cfg(AGENT, DEFAUT)
        if a.cmd == "etat": return cmd_etat(conf)
        controles = [("pages du dépôt", lambda: controle_pages(conf.get("pages_max"), conf.get("sites_indexables"))),
                     ("suivi des pages exemple", controle_suivi_pages)]
        return S.lancer(AGENT, DOMAINE, AGENTS_SUIVIS, controles, conf, a.essai, datetime.fromisoformat(a.maintenant) if a.maintenant else None)
    except S.ErreurAgent as e:
        print(f"  ! {e}"); return 2
    except OSError as e:
        print(f"  ! erreur de fichier : {e.strerror or type(e).__name__}"); return 2


if __name__ == "__main__":
    sys.exit(main())
