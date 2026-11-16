#!/usr/bin/env python3
"""Agent videos-veille (équipe Vidéos TikTok, 16/11/2026) : une fois par jour, recherche web gratuite sur les formats stickman / motion design qui marchent en français ;
écrit une note courte Videos\\veille\\AAAA-MM-JJ.md (titres, sites, dates) ; garde 14 jours ; les titres en forme d'accroche enrichissent Videos\\hooks.md
(= hooks-base.md + formules repérées, 40 au plus). Règles relues avant chaque exécution : Videos\\SKILL-VIDEOS.md. Source : flux RSS public de Google Actualités (français, sans clé ni compte).
DuckDuckGo répond « anomaly » (contrôle anti-robot) depuis ce serveur et le flux RSS de Bing ignore la requête (essais du 16/11/2026) : non utilisés, aucun contournement.
JAMAIS de scraping de TikTok : aucune page n'est ouverte, et tout résultat sur tiktok.com est écarté. Aucun envoi, aucune publication.
  python Videos\\agents\\veille.py jour [--a-blanc]
  python Videos\\agents\\veille.py etat"""
import argparse, html, re, sys, urllib.error, urllib.parse, urllib.request
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import commun as C   # noqa: E402

AGENT = "videos-veille"
EXCLUS = re.compile(r"(^|\.)tiktok\.com$|(^|\.)tiktokv\.com$", re.I)
MAX_RESULTATS = 8
PAR_REQUETE = 2


def chercher(requete, ouvrir=urllib.request.urlopen):
    """[(titre, source, date, lien)] du flux RSS Google Actualités en français ; aucune page de résultat n'est ouverte ; tiktok.com écarté."""
    u = "https://news.google.com/rss/search?" + urllib.parse.urlencode({"q": requete, "hl": "fr", "gl": "FR", "ceid": "FR:fr"})
    rq = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 (compatible; JarvisVideos/1.0)"})
    with ouvrir(rq, timeout=15) as r: flux = r.read(600_000).decode("utf-8", "replace")
    net = lambda s: " ".join(html.unescape(re.sub(r"<[^>]+>", "", s or "")).split())
    out = []
    for it in re.findall(r"<item>(.*?)</item>", flux, re.S):
        champ = lambda nom: (re.search(rf"<{nom}[^>]*>(.*?)</{nom}>", it, re.S) or [None, ""])[1]
        source = re.search(r'<source url="([^"]*)"[^>]*>(.*?)</source>', it, re.S)
        hote = urllib.parse.urlparse(html.unescape(source.group(1))).netloc.lower().removeprefix("www.") if source else ""
        if EXCLUS.search(hote): continue
        titre = net(champ("title")); nom_source = net(source.group(2)) if source else hote
        if nom_source and titre.endswith(" - " + nom_source): titre = titre[: -len(nom_source) - 3]
        out.append((titre[:120], nom_source or hote, net(champ("pubDate"))[5:16], net(champ("link"))))
    return out


def note(jour, resultats):
    lignes = [f"# Veille vidéos du {jour}", "", "Recherche web (Google Actualités, titres seulement, aucune page ouverte, rien de TikTok) :", ""]
    lignes += [f"- {t} ({s}, {d})" for t, s, d, _ in resultats] or ["- aucun résultat exploitable aujourd'hui"]
    return "\n".join(lignes) + "\n"


def purger(jour, jours_gardes):
    """Efface les notes de plus de `jours_gardes` jours (nom AAAA-MM-JJ.md). -> nombre effacé."""
    limite = date.fromisoformat(jour) - timedelta(days=jours_gardes); n = 0
    for f in C.VEILLE.glob("*.md"):
        try: d = date.fromisoformat(f.stem)
        except ValueError: continue
        if d < limite: f.unlink(); n += 1
    return n


FORME_ACCROCHE = re.compile(r"\?|\bpourquoi\b|\bcomment\b|\berreurs?\b|\bpersonne ne\b|\bpourtant\b|\barr[êe]tez\b|\bstop\b|\bvraiment\b|\bfaux\b|\bsecret\b|\bce que\b", re.I)
HOOKS_MAX = 40
DEBUT_BLOC, FIN_BLOC = "<!-- VEILLE:DEBUT", "<!-- VEILLE:FIN -->"


def formules(resultats, jour):
    """Titres repérés qui ont une forme d'accroche (question, erreur, contradiction…) : notés comme formules à adapter, jamais à copier."""
    return [f"- {jour} : « {t} » ({s}) : forme {'question' if '?' in t else 'contradiction / erreur / curiosité'}" for t, s, _, _ in resultats if FORME_ACCROCHE.search(t)]


def enrichir_hooks(nouvelles):
    """Réécrit Videos\\hooks.md = hooks-base.md + formules repérées (les plus récentes d'abord, sans doublon, HOOKS_MAX au plus). -> nombre ajouté."""
    try: base = C.HOOKS_BASE.read_text(encoding="utf-8")
    except OSError: return 0
    try: ancien = C.HOOKS.read_text(encoding="utf-8")
    except OSError: ancien = ""
    bloc = ancien.split(DEBUT_BLOC, 1)[1].split(FIN_BLOC, 1)[0] if DEBUT_BLOC in ancien and FIN_BLOC in ancien else ""
    deja = [l for l in bloc.splitlines() if l.startswith("- ")]
    vus = {l.split(" : ", 1)[-1] for l in deja}; ajout = [l for l in nouvelles if l.split(" : ", 1)[-1] not in vus]
    lignes = (ajout + deja)[:HOOKS_MAX]
    if DEBUT_BLOC not in base or FIN_BLOC not in base: return 0
    tete, reste = base.split(DEBUT_BLOC, 1); entete_bloc, queue = reste.split(FIN_BLOC, 1)
    entete_bloc = entete_bloc.split("\n", 1)[0]
    C.HOOKS.write_text(tete + DEBUT_BLOC + entete_bloc + "\n" + "".join(l + "\n" for l in lignes) + FIN_BLOC + queue, encoding="utf-8")
    return len(ajout)


def cmd_jour(conf, jour, a_blanc, ouvrir=urllib.request.urlopen):
    vus, resultats, echecs = set(), [], 0
    for q in conf["veille_requetes"]:
        try: rs = chercher(q, ouvrir)
        except (urllib.error.URLError, OSError) as e: echecs += 1; print(f"  ! recherche impossible ({type(e).__name__}) : {q}"); continue
        pris = 0
        for r in rs:
            if r[3] in vus or r[0] in {x[0] for x in resultats}: continue
            vus.add(r[3]); resultats.append(r); pris += 1
            if pris >= PAR_REQUETE: break
    resultats = resultats[:MAX_RESULTATS]
    texte = note(jour, resultats)
    if a_blanc: print(f"[à blanc] note du {jour} ({len(resultats)} source(s)) :\n{texte}"); return 0
    if echecs == len(conf["veille_requetes"]) and conf["veille_requetes"]:
        C.journal(AGENT, "veille", f"{jour} : recherche web impossible ({echecs} requête(s))"); print("Recherche web impossible : aucune note écrite."); return 2
    C.VEILLE.mkdir(parents=True, exist_ok=True)
    (C.VEILLE / f"{jour}.md").write_text(texte, encoding="utf-8")
    n = purger(jour, conf["veille_jours_gardes"])
    h = enrichir_hooks(formules(resultats, jour))
    C.journal(AGENT, "veille", f"{jour} : note écrite ({len(resultats)} source(s)), {h} formule(s) ajoutée(s) à hooks.md, {n} ancienne(s) note(s) effacée(s)")
    print(f"Note de veille du {jour} : {len(resultats)} source(s) ; {n} note(s) de plus de {conf['veille_jours_gardes']} jours effacée(s).")
    return 0


def cmd_etat():
    notes = sorted(C.VEILLE.glob("*.md"))
    print(f"{len(notes)} note(s) de veille" + (f", dernière : {notes[-1].name}" if notes else "")); return 0


def main(argv=None):
    a = argparse.ArgumentParser(prog="videos-veille"); sp = a.add_subparsers(dest="cmd", required=True)
    j = sp.add_parser("jour"); j.add_argument("--a-blanc", action="store_true"); j.add_argument("--jour")
    sp.add_parser("etat")
    a = a.parse_args(argv)
    if a.cmd == "etat": return cmd_etat()
    C.exiger(AGENT, a.cmd, a.a_blanc); C.exiger_regles(AGENT, a.a_blanc)
    return cmd_jour(C.cfg(), a.jour or f"{C.heure_paris():%Y-%m-%d}", a.a_blanc)


if __name__ == "__main__":
    sys.exit(main())
