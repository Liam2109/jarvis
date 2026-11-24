#!/usr/bin/env python3
"""File unique « leads chauds » (maillon 2 de docs\\agents\\CARTE-RELAIS.md, 23/11/2026) : B2B\\donnees\\leads-chauds.json, hors git, reconstruite depuis le registre des entreprises.
Les leads chauds ne sont plus « pour Liam » : ils vont à Sid par défaut (ou à un closer, réglage « rappelle_lead »). Liam ne rappelle pas.
Un lead = une entrée du registre dont le dernier Résultat est « À rappeler » ou « Je dois réfléchir » (une clé = un lead, jamais de doublon).
Sortent de la file : STOP / « pas intéressé » / « non » écrit dans la note, STOP ou refus enregistré par l'agent Réponses (suivi-prospects.csv), Résultat final noté depuis.
Un « moyen terme » (ou « semaines ») reste, avec sa date de relance = 15e jour ouvré après l'appel.
Une seule alerte Discord par lead, à son entrée (mémoire « alertes », jamais effacée : un lead qui sort puis revient n'est pas ré-annoncé).
AUCUN contact avec un prospect : ce module ne lit et n'écrit que des fichiers locaux ; l'envoi Discord est fourni par l'appelant (`envoyer`)."""
import json, os, re
from pathlib import Path
import registre as RG

FICHIER = RG.RACINE / "donnees" / "leads-chauds.json"
if os.environ.get("JARVIS_TEST") == "1":   # tests : jamais la vraie file
    import tempfile; FICHIER = Path(tempfile.mkdtemp(prefix="leads-chauds-test-")) / "leads-chauds.json"
SUIVI = RG.RACINE / "suivi-prospects.csv"
REFUS_STATUTS = ("STOP", "refusé")
MOYEN_TERME = ("moyen terme", "semaines")
REFUS = re.compile(r"\bstop\b|pas interesse|\bnon merci\b|^non\b|\bne veut pas\b|\brefuse\b")
JOURS_MOYEN_TERME = 15


def refus_dans_note(note):
    """STOP / « pas intéressé » / « non » dans la note, sauf si elle dit « moyen terme » (ou « semaines ») : ce lead-là reste."""
    t = RG.norm(note)
    return bool(REFUS.search(t)) and not any(m in t for m in MOYEN_TERME)


def refus_reponses(suivi=None):
    """(téléphones, noms normalisés) des prospects que l'agent Réponses a classés STOP ou refusé (suivi-prospects.csv, lecture seule)."""
    tels, noms = set(), set()
    for l in RG._csv(suivi or SUIVI):
        if l.get("statut") in REFUS_STATUTS:
            if RG.tel_norm(l.get("telephone")): tels.add(RG.tel_norm(l.get("telephone")))
            if RG.norm(l.get("nom")): noms.add(RG.norm(l.get("nom")))
    return tels, noms


def date_relance(x):
    """Jour de rappel : date du registre ; moyen terme : pas avant le 15e jour ouvré après l'appel (GT Concept / Garage du Rond Point : 07/12)."""
    r = x.get("retour") or ""
    if x.get("resultat_le") and any(m in RG.norm(x.get("note")) for m in MOYEN_TERME):
        r = max(r, RG.jour_ouvre(x["resultat_le"], JOURS_MOYEN_TERME))
    return r


def courants(reg, refus=None, rappelle="Sid"):
    """{clé: lead} des leads chauds en cours (nom, téléphone, jour de rappel, métier, dernière réponse, qui rappelle) ; refus = (tels, noms) de refus_reponses."""
    tels, noms = refus or (set(), set()); out = {}
    for k, x in reg["entreprises"].items():
        if x.get("dernier_resultat") not in RG.CHAUDS or x.get("statut") != "à reprendre": continue
        if refus_dans_note(x.get("note")) or (x.get("tel") and x["tel"] in tels) or RG.norm(x.get("nom")) in noms: continue
        out[k] = {"nom": x.get("nom", ""), "tel": x.get("tel", ""), "jour": date_relance(x), "metier": x.get("metier", ""),
                  "derniere_reponse": f"{x['dernier_resultat']} : {x.get('note') or '(note vide)'}", "rappelle": rappelle, "resultat_le": x.get("resultat_le", ""),
                  "ville": x.get("commune", ""), "resultat": x["dernier_resultat"], "note": x.get("note", ""), "moyen_terme": any(m in RG.norm(x.get("note")) for m in MOYEN_TERME)}
    return out


def tel_lisible(t): return " ".join(t[i:i + 2] for i in range(0, 10, 2)) if len(t) == 10 else t


def texte_alerte(l):
    return (f"Lead chaud à rappeler par {l['rappelle']} : {l['nom']}, {tel_lisible(l['tel'])}, le {l['jour'] or 'dès que possible'} ({l['metier'] or 'métier non noté'}). "
            f"Dernière réponse — {l['derniere_reponse']}. Aucun message n'est envoyé au prospect.")


def charger(fichier=None):
    f = Path(fichier or FICHIER)
    if not f.exists(): return {"version": 1, "leads": {}, "alertes": {}}
    d = json.loads(f.read_text(encoding="utf-8"))   # illisible : l'erreur remonte, rien n'est écrasé
    if not isinstance(d, dict) or not isinstance(d.get("leads"), dict): raise ValueError("file des leads chauds illisible")
    d.setdefault("alertes", {}); return d


def lire(fichier=None):
    """Leads de la file, triés par jour de rappel (lu par le tableau de bord). None si la file n'existe pas ou est illisible."""
    f = Path(fichier or FICHIER)
    if not f.exists(): return None
    try: d = charger(f)
    except (OSError, ValueError): return None
    return sorted(d["leads"].values(), key=lambda l: (l.get("jour") or "9999", l["nom"]))


def synchroniser(reg, jour, envoyer=None, fichier=None, suivi=None, rappelle="Sid", ecrire=True):
    """Met la file à jour depuis le registre et alerte une fois par nouveau lead. envoyer(texte) -> bool (None : simulation, rien envoyé, rien marqué).
    ecrire=False : rien n'est écrit. -> (entrés, sortis, textes des alertes à envoyer ou envoyées)."""
    f = Path(fichier or FICHIER); d = charger(f); avant = set(d["leads"]); cour = courants(reg, refus_reponses(suivi), rappelle)
    for k, l in cour.items(): d["leads"][k] = {**d["leads"].get(k, {}), **l}   # une clé = une entrée : jamais de doublon
    sortis = [k for k in avant if k not in cour]
    for k in sortis:
        if ecrire:
            import archive as AR; AR.archiver("leads-chauds", k, d["leads"][k], "sorti de la file (refus, résultat final ou retour du registre)")   # archive restaurable (26/11/2026)
        del d["leads"][k]
    entres = [k for k in cour if k not in avant]; textes = []
    for k, l in cour.items():
        if k in d["alertes"]: continue
        t = texte_alerte(l); textes.append(t)
        if envoyer is None: print("  [simulation] alerte lead chaud : " + t); continue
        if envoyer(t): d["alertes"][k] = jour
        else: print("  ! alerte lead chaud non envoyée : réessayée au prochain passage")
    if ecrire:
        d["maj"] = jour; f.parent.mkdir(parents=True, exist_ok=True)
        tmp = f.with_name(f.name + ".tmp"); tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8"); os.replace(tmp, f)
    return entres, sortis, textes
