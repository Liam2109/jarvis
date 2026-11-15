#!/usr/bin/env python3
"""Validateur des sorties de Jarvis CEO (harness, 15/11/2026). Jarvis ne produit que des décisions structurées (jarvis-sortie.schema.json).
Refus : schéma ; chiffre du constat introuvable dans les sources (fichiers lus) ; promesse faite au client ; action qui engage Liam sans engage_liam = true ;
agent_cible inconnu (ni contrat, ni « liam ») ; justification de plus d'une phrase.
  python B2B\\harness\\jarvis_sortie.py sortie.json [...]    code 0 si toutes valides, 1 sinon"""
import json, re, sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
RACINE = ICI.parent.parent
sys.path.insert(0, str(ICI))
from valider import valider   # noqa: E402

SCHEMA = json.loads((ICI / "jarvis-sortie.schema.json").read_text(encoding="utf-8"))
NOMBRE = re.compile(r"(?<![\w.,])\d+(?:[.,]\d+)?(?![\w])")
PROMESSE = re.compile(r"garanti|promet|promesse|vous aurez|résultat assuré|r[ée]sultats? garantis?|premier sur google|plus de clients|satisfait ou rembours|sans risque|100\s?%", re.I)
ENGAGE = re.compile(r"envoy\w*\s+(?:au|le|la|les|un|une)?\s*(?:client|prospect|devis|message|e-?mail|lien)|encaiss|rembours|publi|sign|pay|mettre en ligne|mise en ligne|d[ée]ploy|relanc\w*\s+(?:le|la|les)?\s*(?:client|prospect)", re.I)


def _texte_sources(sources, racine):
    t = []
    for s in sources:
        p = (racine / s) if not Path(s).is_absolute() else Path(s)
        try: t.append(p.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeDecodeError): t.append(None)
    return t


def _norm_nombre(n): return n.replace(",", ".")


def valider_sortie(o, racine=RACINE):
    e = valider(o, SCHEMA)
    if e: return e
    textes = _texte_sources(o["sources"], racine)
    for s, t in zip(o["sources"], textes):
        if t is None: e.append(f"source illisible : {s}")
    tout = " ".join(t for t in textes if t)
    nombres_src = {_norm_nombre(n) for n in NOMBRE.findall(tout)}
    for n in NOMBRE.findall(o["constat"]):
        if _norm_nombre(n) not in nombres_src: e.append(f"chiffre « {n} » introuvable dans les sources")
    for champ in ("constat", "decision", "action", "justification"):
        if PROMESSE.search(o[champ]): e.append(f"promesse client dans « {champ} »")
    if ENGAGE.search(o["action"] + " " + o["decision"]) and not o["engage_liam"]: e.append("action qui engage Liam sans engage_liam = true (à écrire dans B2B\\a-valider)")
    connus = {p.stem for p in (ICI / "contrats").glob("*.json")} | {"liam"}
    if o["agent_cible"] not in connus: e.append(f"agent_cible inconnu : {o['agent_cible']}")
    if len(re.findall(r"[.!?](?:\s|$)", o["justification"].strip())) > 1: e.append("justification en plus d'une phrase")
    return e


def main(argv=None):
    ko = 0
    for f in (argv if argv is not None else sys.argv[1:]):
        e = valider_sortie(json.loads(Path(f).read_text(encoding="utf-8")))
        print(("OK    " if not e else "REFUS ") + f + ("" if not e else " : " + " ; ".join(e))); ko += bool(e)
    return 1 if ko else 0


if __name__ == "__main__":
    sys.exit(main())
