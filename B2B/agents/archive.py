#!/usr/bin/env python3
"""Archive restaurable des leads et des appels (26/11/2026, filet de sécurité) : plus rien ne se supprime vraiment.
Toute suppression d'une entreprise du registre (registre.liberer, commande « supprimer ») ou d'un lead de la file des leads chauds passe d'abord ici :
une ligne JSON est ajoutée à B2B\\donnees\\archive\\archive.jsonl (jamais réécrite, hors git), avec l'entrée complète. Aucun réseau, aucun envoi, aucun token.

Restaurer (3 lignes) :
  python B2B\\agents\\sauvegarde-leads.py archives               liste les éléments archivés (id, date, quoi, nom, raison)
  python B2B\\agents\\sauvegarde-leads.py restaurer <id>         remet l'entrée à sa place (refuse si la clé existe déjà : rien n'est écrasé)
  la file des leads chauds est recalculée depuis le registre à chaque passage : un lead restauré là-bas n'y reste que si le registre le justifie encore."""
import json, os, sys, tempfile
from datetime import datetime
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
FICHIER = RACINE / "donnees" / "archive" / "archive.jsonl"
if os.environ.get("JARVIS_TEST") == "1":   # tests : jamais la vraie archive
    FICHIER = Path(tempfile.mkdtemp(prefix="archive-test-")) / "archive.jsonl"
QUOI = ("registre", "leads-chauds")   # registre : B2B\donnees\registre-entreprises.json › entreprises ; leads-chauds : B2B\donnees\leads-chauds.json › leads


class ErreurArchive(Exception):
    """Message clair pour Liam ; rien n'est écrit."""


def _lignes(fichier=None):
    f = Path(fichier or FICHIER)
    if not f.exists(): return []
    out = []
    for l in f.read_text(encoding="utf-8").splitlines():
        if l.strip():
            try: out.append(json.loads(l))
            except ValueError: continue   # une ligne abîmée n'empêche pas de lire les autres
    return out


def _ajouter(ligne, fichier=None):
    f = Path(fichier or FICHIER); f.parent.mkdir(parents=True, exist_ok=True)
    with open(f, "a", encoding="utf-8") as h: h.write(json.dumps(ligne, ensure_ascii=False, sort_keys=True) + "\n")


def archiver(quoi, cle, valeur, raison="", fichier=None, maintenant=None):
    """Range une entrée avant qu'elle ne soit supprimée. -> id. À appeler AVANT la suppression : si l'écriture échoue, l'erreur remonte et rien n'est supprimé."""
    if quoi not in QUOI: raise ErreurArchive(f"type inconnu « {quoi} » (attendu : {', '.join(QUOI)})")
    n = maintenant or datetime.now(); deja = [l for l in _lignes(fichier) if str(l.get("id", "")).startswith(f"{n:%Y%m%d-%H%M%S}")]
    i = f"{n:%Y%m%d-%H%M%S}-{len(deja) + 1}"
    _ajouter({"id": i, "date": f"{n:%Y-%m-%d %H:%M:%S}", "quoi": quoi, "cle": cle, "raison": str(raison)[:200], "valeur": valeur}, fichier)
    return i


def archives(fichier=None):
    """Éléments archivés pas encore restaurés, du plus récent au plus ancien."""
    lignes = _lignes(fichier); rest = {l["id"] for l in lignes if l.get("restaure_le")}
    return [l for l in reversed(lignes) if "valeur" in l and l["id"] not in rest]


def _nom(l):
    v = l.get("valeur") or {}
    return str(v.get("nom") or l.get("cle", "")).strip()


def decrire(l): return f"{l['id']} | {l['date'][:10]} | {l['quoi']} | {_nom(l)} | {l.get('raison') or '-'}"


def _ecrire_json(f, d):
    tmp = f.with_name(f.name + ".tmp"); tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8"); os.replace(tmp, f)


def restaurer(ident, fichier=None, registre=None, leads=None, maintenant=None):
    """Remet l'entrée archivée `ident` dans son fichier d'origine. registre / leads : chemins des fichiers cibles (par défaut les vrais). -> description de l'entrée.
    Refuse si l'id est inconnu, déjà restauré, ou si la clé existe déjà dans le fichier cible (rien n'est écrasé)."""
    ligne = next((l for l in archives(fichier) if l["id"] == ident), None)
    if not ligne: raise ErreurArchive(f"id « {ident} » inconnu ou déjà restauré (liste : sauvegarde-leads.py archives)")
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    if ligne["quoi"] == "registre":
        import registre as RG
        with RG.verrou(registre):
            reg = RG.charger(registre)
            if ligne["cle"] in reg["entreprises"]: raise ErreurArchive("cette entreprise existe déjà dans le registre : rien n'est écrasé")
            reg["entreprises"][ligne["cle"]] = ligne["valeur"]; RG.sauver(reg, registre)
    else:
        import leads_chauds as LC
        f = Path(leads or LC.FICHIER); d = LC.charger(f)
        if ligne["cle"] in d["leads"]: raise ErreurArchive("ce lead existe déjà dans la file : rien n'est écrasé")
        d["leads"][ligne["cle"]] = ligne["valeur"]; f.parent.mkdir(parents=True, exist_ok=True); _ecrire_json(f, d)
    n = maintenant or datetime.now()
    _ajouter({"id": ident, "restaure_le": f"{n:%Y-%m-%d %H:%M:%S}"}, fichier)
    return decrire(ligne)


def supprimer(quoi, cle, raison="suppression demandée", fichier=None, registre=None, leads=None):
    """Seule façon de retirer à la main un lead ou un appel : archive puis supprime. -> id d'archive."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    if quoi == "registre":
        import registre as RG
        with RG.verrou(registre):
            reg = RG.charger(registre)
            if cle not in reg["entreprises"]: raise ErreurArchive("clé inconnue dans le registre : rien n'est supprimé")
            i = archiver("registre", cle, reg["entreprises"][cle], raison, fichier)
            del reg["entreprises"][cle]; RG.sauver(reg, registre)
    elif quoi == "leads-chauds":
        import leads_chauds as LC
        f = Path(leads or LC.FICHIER); d = LC.charger(f)
        if cle not in d["leads"]: raise ErreurArchive("clé inconnue dans la file des leads chauds : rien n'est supprimé")
        i = archiver("leads-chauds", cle, d["leads"][cle], raison, fichier); del d["leads"][cle]; _ecrire_json(f, d)
    else: raise ErreurArchive(f"type inconnu « {quoi} » (attendu : {', '.join(QUOI)})")
    return i
