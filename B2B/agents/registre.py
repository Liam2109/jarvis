#!/usr/bin/env python3
"""Registre commun des entreprises (décision de Liam du 15/11/2026, actif à partir du mardi 17/11/2026) : B2B\\donnees\\registre-entreprises.json, hors git.
Une entreprise déjà donnée (liste de Sid, liste de Liam ou lot d'e-mails) n'est JAMAIS redonnée à personne, sauf les reprises ci-dessous.
Clé = nom normalisé | commune normalisée | téléphone (10 chiffres). Une entreprise est aussi reconnue par son seul téléphone, ou par son nom et sa commune (même entreprise, autre numéro).
Pour chaque entreprise : département, métier, date donnée, à qui (Sid, Liam, lot e-mail), nombre d'essais, dernier résultat (+ retour, pour qui, note, dernière feuille).

Reprises (lues dans la colonne Résultat des feuilles « Appels » de Sid et « Appels Liam ») :
  case vide en fin de journée -> en tête de la liste suivante de la même personne ;
  Pas de réponse             -> retour après 3 jours ouvrés, 3 essais au plus (au 3e, plus jamais redonnée) ;
  À rappeler                 -> lead chaud : liste de LIAM le jour écrit dans Note (17/11, 2026-11-20, mardi, demain…), sinon le jour ouvré suivant ; plus jamais chez Sid ;
  Je dois réfléchir          -> lead chaud : relance dans la liste de Liam 3 jours plus tard ;
  (leads chauds : alerte Discord pour Liam une seule fois par lead, voir appels-sid.alerter_leads ; décision du 17/11/2026)
  RDV pris, Non catégorique, Trop cher, Déjà un site, Pas le temps -> jamais redonnée.
Aucun réseau, aucun envoi : ce module ne fait que lire et écrire le fichier du registre (écriture atomique, verrou)."""
import json, os, re, time, unicodedata, contextlib
from datetime import date, timedelta
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
FICHIER = RACINE / "donnees" / "registre-entreprises.json"
if os.environ.get("JARVIS_TEST") == "1":   # tests : jamais le vrai registre (un dossier temporaire par processus)
    import tempfile; FICHIER = Path(tempfile.mkdtemp(prefix="registre-test-")) / "registre-entreprises.json"
DEBUT = "2026-11-17"            # premier jour des nouvelles règles (la liste de Sid du lundi 16/11 suit encore les anciennes)
LECTURE_DEPUIS = "2026-11-16"   # feuilles dont le Résultat est lu dans le registre (celle du 16/11 est lue le 17/11)
SID, LIAM, LOT = "Sid", "Liam", "lot e-mail"
FINAUX = ("RDV pris", "Non catégorique", "Trop cher", "Déjà un site", "Pas le temps")
CHAUDS = ("À rappeler", "Je dois réfléchir")   # leads chauds : retirés de la liste de Sid, donnés à Liam, alerte Discord une seule fois par lead (décision de Liam du 17/11/2026)
ESSAIS_MAX = 3                  # Pas de réponse : 3 essais au plus
JOURS_OUVRES_SANS_REPONSE = 3   # Pas de réponse : retour après 3 jours ouvrés
JOURS_REFLECHIR = 3             # Je dois réfléchir : relance de Liam 3 jours plus tard
JOURS_SEMAINE = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
VERROU_MAX_S = 600


def actif(jour): return str(jour) >= DEBUT


def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def tel_norm(t):
    d = re.sub(r"\D", "", str(t or ""))
    if d.startswith("33") and len(d) == 11: d = "0" + d[2:]
    return d if len(d) == 10 else ""


def cle(nom, commune, tel): return f"{norm(nom)}|{norm(commune)}|{tel_norm(tel)}"


# --- fichier ---------------------------------------------------------------------------------------------------------
def vide(): return {"version": 1, "entreprises": {}, "feuilles_lues": {}}


def charger(fichier=None):
    f = Path(fichier or FICHIER)
    if not f.exists(): return vide()
    r = json.loads(f.read_text(encoding="utf-8"))   # illisible : l'erreur remonte, rien n'est écrasé
    if not isinstance(r, dict) or not isinstance(r.get("entreprises"), dict): raise ValueError("registre illisible")
    r.setdefault("feuilles_lues", {}); return r


def sauver(reg, fichier=None):
    f = Path(fichier or FICHIER); f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f.name + ".tmp"); tmp.write_text(json.dumps(reg, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8"); os.replace(tmp, f)


@contextlib.contextmanager
def verrou(fichier=None, attente_s=60):
    """Un seul écrivain à la fois (appels-sid, appels-liam, prospection) ; un verrou de plus de 10 min est celui d'un processus mort : repris."""
    v = Path(fichier or FICHIER).with_suffix(".verrou"); v.parent.mkdir(parents=True, exist_ok=True); t0 = time.time()
    while True:
        try: fd = os.open(str(v), os.O_CREAT | os.O_EXCL | os.O_WRONLY); os.write(fd, str(os.getpid()).encode()); os.close(fd); break
        except FileExistsError:
            try:
                if time.time() - v.stat().st_mtime > VERROU_MAX_S: v.unlink(missing_ok=True); continue
            except OSError: continue
            if time.time() - t0 > attente_s: raise TimeoutError("registre des entreprises verrouillé")
            time.sleep(0.5)
    try: yield
    finally: v.unlink(missing_ok=True)


# --- recherche --------------------------------------------------------------------------------------------------------
def index(reg):
    """(noms|communes, téléphones) de toutes les entreprises du registre."""
    nc, tels = set(), set()
    for k, e in reg["entreprises"].items():
        n, c, t = k.split("|", 2); nc.add(f"{n}|{c}")
        if t: tels.add(t)
    return nc, tels


def trouver(reg, nom, commune, tel):
    """Clé de l'entreprise déjà connue (même clé, même téléphone, ou même nom et commune), sinon None."""
    k = cle(nom, commune, tel)
    if k in reg["entreprises"]: return k
    t = tel_norm(tel); nc = f"{norm(nom)}|{norm(commune)}"
    return next((x for x in reg["entreprises"] if (t and x.endswith("|" + t)) or x.rsplit("|", 1)[0] == nc), None)


def connue(reg, nom, commune, tel, idx=None):
    nc, tels = idx or index(reg); t = tel_norm(tel)
    return f"{norm(nom)}|{norm(commune)}" in nc or bool(t and t in tels)


# --- écriture ---------------------------------------------------------------------------------------------------------
def donner(reg, e, a_qui, jour, feuille="", creneau=""):
    """Note qu'une entreprise est donnée (neuve ou reprise) à `a_qui` le `jour`. e : nom, ville, tel, metier, dept. -> clé."""
    k = trouver(reg, e["nom"], e.get("ville", ""), e.get("tel", "")) or cle(e["nom"], e.get("ville", ""), e.get("tel", ""))
    x = reg["entreprises"].setdefault(k, {"nom": e["nom"], "commune": e.get("ville", ""), "tel": tel_norm(e.get("tel", "")), "departement": e.get("dept", "") or "",
                                          "metier": e.get("metier", "") or "", "date": jour, "a_qui": a_qui, "essais": 0, "dernier_resultat": "", "statut": "donnée"})
    x.update(a_qui=a_qui, feuille=feuille or x.get("feuille", ""), donnee_le=jour, retour="", pour="", statut="donnée", tete=False, creneau=creneau or x.get("creneau", ""))
    if e.get("dept") and not x.get("departement"): x["departement"] = e["dept"]
    return k


def jour_ouvre(jour, n):
    d = date.fromisoformat(jour)
    while n > 0:
        d += timedelta(days=1)
        if d.weekday() < 5: n -= 1
    return d.isoformat()


def ouvre_ou_suivant(d):
    while d.weekday() >= 5: d += timedelta(days=1)
    return d


def date_dans_note(note, jour):
    """Jour de rappel écrit par Sid ou Liam dans Note, après `jour` (le jour de la feuille) ; None si aucun jour n'est lisible."""
    t = norm(note); ref = date.fromisoformat(jour); d = None
    m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", note or "")
    if m:
        try: d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError: d = None
    if d is None:
        m = re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", note or "")
        if m:
            a = int(m.group(3)) if m.group(3) else ref.year
            a = a + 2000 if a < 100 else a
            try:
                d = date(a, int(m.group(2)), int(m.group(1)))
                if not m.group(3) and d <= ref: d = date(a + 1, d.month, d.day)
            except ValueError: d = None
    if d is None:
        if re.search(r"\bapres demain\b", t): d = ref + timedelta(days=2)
        elif re.search(r"\bdemain\b", t): d = ref + timedelta(days=1)
        elif "semaine prochaine" in t: d = ref + timedelta(days=7 - ref.weekday())
        else:
            for i, j in enumerate(JOURS_SEMAINE):
                if re.search(rf"\b{j}\b", t): d = ref + timedelta(days=((i - ref.weekday()) % 7) or 7); break
    if d is None or d <= ref: return None
    return ouvre_ou_suivant(d).isoformat()


def noter(reg, k, resultat, note, jour_feuille, qui):
    """Applique le Résultat d'une ligne de la feuille de `qui` du `jour_feuille` (règles du module). -> la décision, en clair."""
    x = reg["entreprises"][k]; v = (resultat or "").strip()
    x.setdefault("lus", {})[f"{qui}|{jour_feuille}"] = v   # ce qui a été appliqué pour cette feuille : une ligne relue plus tard (relire) n'est jamais comptée deux fois
    if not v and (x.get("statut") == "terminée" or (x.get("pour") == LIAM and x.get("dernier_resultat") in CHAUDS)):
        return "sans résultat, mais déjà terminée ou lead chaud : rien ne change"   # une case vide ne fait jamais revenir un « Non catégorique » ni un lead chaud chez Sid (17/11/2026)
    x["note"] = (note or "").strip()[:300]
    if not v:
        x.update(retour=jour_ouvre(jour_feuille, 1), pour=qui, statut="à reprendre", tete=True); return "sans résultat : en tête de la liste suivante"
    x["essais"] = int(x.get("essais", 0)) + 1; x["dernier_resultat"] = v; x["tete"] = False; x["resultat_le"] = jour_feuille
    if v == "Pas de réponse":
        if x["essais"] >= ESSAIS_MAX: x.update(retour="", pour="", statut="terminée"); return f"pas de réponse, {ESSAIS_MAX} essais : plus jamais redonnée"
        x.update(retour=jour_ouvre(jour_feuille, JOURS_OUVRES_SANS_REPONSE), pour=qui, statut="à reprendre"); return f"pas de réponse : retour après {JOURS_OUVRES_SANS_REPONSE} jours ouvrés"
    if v == "À rappeler":
        d = date_dans_note(note, jour_feuille)
        x.update(retour=d or jour_ouvre(jour_feuille, 1), pour=LIAM, statut="à reprendre")   # lead chaud : pour Liam, jamais rendu à Sid (décision du 17/11/2026)
        return "à rappeler : liste de Liam, " + ("le jour écrit dans Note" if d else "aucun jour lisible dans Note, jour ouvré suivant")
    if v == "Je dois réfléchir":
        x.update(retour=(date.fromisoformat(jour_feuille) + timedelta(days=JOURS_REFLECHIR)).isoformat(), pour=LIAM, statut="à reprendre"); return f"je dois réfléchir : relance de Liam dans {JOURS_REFLECHIR} jours"
    x.update(retour="", pour="", statut="terminée")
    return "jamais redonnée" if v in FINAUX else f"valeur inconnue « {v[:30]} » : jamais redonnée"


def relire(reg, qui, jour_feuille, lignes):
    """Résultats notés APRÈS la première lecture d'une feuille (17/11/2026 : Sid a noté ses appels dans la feuille de la veille, déjà lue à 7 h 30). Chaque ligne n'est appliquée
    qu'une fois (x['lus'], ou même résultat déjà enregistré pour ce jour) ; un Résultat final l'emporte toujours ; un autre n'écrase ni une entreprise terminée ni un résultat
    plus récent. Pas de réponse : règles de noter (essais) inchangées. lignes : [{nom, ville, tel, resultat, note}]. -> nombre de lignes appliquées."""
    n = 0; f = f"{qui}|{jour_feuille}"
    for l in lignes:
        v = (l.get("resultat") or "").strip(); k = trouver(reg, l.get("nom", ""), l.get("ville", ""), l.get("tel", "")) if v else None
        if not k: continue
        x = reg["entreprises"][k]; lus = x.setdefault("lus", {})
        deja = lus.get(f) == v or (f not in lus and x.get("resultat_le") == jour_feuille and x.get("dernier_resultat") == v)
        perime = v not in FINAUX and (x.get("statut") == "terminée" or x.get("resultat_le", "") > jour_feuille)
        if deja or perime: lus[f] = v; continue
        noter(reg, k, v, l.get("note", ""), jour_feuille, qui); n += 1
    return n


def leads_chauds(reg, depuis=LECTURE_DEPUIS):
    """Leads chauds (À rappeler, Je dois réfléchir) notés par Sid depuis `depuis` et pas encore signalés à Liam (alerte_lead). -> [(clé, entrée)]."""
    return sorted(((k, x) for k, x in reg["entreprises"].items() if x.get("dernier_resultat") in CHAUDS and x.get("resultat_le", "") >= depuis and not x.get("alerte_lead")
                   and any(c.startswith(f"{SID}|") and v == x["dernier_resultat"] for c, v in (x.get("lus") or {}).items())), key=lambda kx: (kx[1]["resultat_le"], kx[0]))


def dues(reg, jour, qui):
    """Reprises dues le `jour` pour `qui` : d'abord les lignes restées sans résultat (en tête), puis par date de retour. -> [(clé, entrée)]."""
    xs = [(k, x) for k, x in reg["entreprises"].items() if x.get("statut") == "à reprendre" and x.get("pour") == qui and x.get("retour") and x["retour"] <= jour]
    return sorted(xs, key=lambda kx: (not kx[1].get("tete"), kx[1]["retour"], kx[0]))


def liberer(reg, feuille, jour):
    """Annulation d'une liste qui n'a pas servi : les entreprises neuves de cette feuille sont retirées, les reprises redeviennent dues."""
    n = 0
    for k in [k for k, x in reg["entreprises"].items() if x.get("feuille") == feuille]:
        x = reg["entreprises"][k]
        if x.get("date") == jour and not x.get("essais"): del reg["entreprises"][k]
        else: x.update(statut="à reprendre", retour=jour, pour=x.get("a_qui", SID))
        n += 1
    return n


# --- anciens lots (décision de Liam du 15/11/2026) ---------------------------------------------------------------------
# Entreprises déjà données avant le registre : lots d'e-mails (B2B\lots\*.csv), fiches « préparé » de prospection-trouves.csv, prospects « envoyé »,
# « STOP » ou « refusé » de suivi-prospects.csv. Importées comme données au lot e-mail, SANS résultat d'appel ; une entreprise déjà connue n'est pas recopiée.
# Les annuaires bruts (prospects*.csv) ne sont PAS importés : personne n'a jamais reçu ces entreprises, elles restent la réserve des listes d'appels.
DONNEES_TROUVES = ("préparé",)
DONNEES_SUIVI = ("envoyé", "STOP", "refusé")


def _csv(f):
    import csv
    try:
        with open(f, encoding="utf-8-sig", newline="") as h: return list(csv.DictReader(h, delimiter=";"))
    except OSError: return []


def anciens(racine=RACINE):
    """-> [(entreprise, jour, source)] des fichiers anciens présents dans `racine` (dossier B2B)."""
    import zone as ZN
    racine = Path(racine); out = []
    def e(l): return {"nom": (l.get("nom") or "").strip(), "ville": l.get("ville", ""), "tel": l.get("telephone", ""), "metier": l.get("metier", ""), "dept": ZN.dept_de_cp(str(l.get("cp", ""))) or ""}
    for f in sorted((racine / "lots").glob("*.csv")):
        m = re.search(r"\d{4}-\d{2}-\d{2}", f.name)
        for l in _csv(f): out.append((e(l), m.group(0) if m else (l.get("date_collecte") or "2026-10-26")[:10], f"lots/{f.name}"))
    for l in _csv(racine / "prospection-trouves.csv"):
        if l.get("statut") in DONNEES_TROUVES: out.append((e(l), (l.get("date_collecte") or "2026-10-27")[:10], "prospection-trouves.csv"))
    for l in _csv(racine / "suivi-prospects.csv"):
        if l.get("statut") in DONNEES_SUIVI: out.append((e(l), (l.get("date_envoi") or l.get("date_statut") or "2026-10-27")[:10], "suivi-prospects.csv"))
    return [x for x in out if x[0]["nom"]]


def importer_anciens(reg, lignes):
    """Ajoute au registre les entreprises inconnues (ni même clé, ni même téléphone, ni même nom et commune). -> {source: ajoutées}."""
    n = {}
    for e, jour, source in lignes:
        n.setdefault(source, 0)
        if trouver(reg, e["nom"], e["ville"], e["tel"]): continue
        k = donner(reg, e, LOT, jour, feuille=f"ancien|{source}"); reg["entreprises"][k]["statut"] = "donnée"; n[source] += 1
    return n


if __name__ == "__main__":
    import argparse, sys
    p = argparse.ArgumentParser(prog="registre", description="Registre commun des entreprises.")
    sp = p.add_subparsers(dest="cmd", required=True)
    sp.add_parser("importer-anciens").add_argument("--a-blanc", action="store_true")
    a = p.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parent)); import machine as M
    M.exiger("registre", a.cmd, a.a_blanc)
    lignes = anciens()
    with (contextlib.nullcontext() if a.a_blanc else verrou()):
        reg = charger(); avant = len(reg["entreprises"]); n = importer_anciens(reg, lignes)
        if not a.a_blanc: sauver(reg)
    for s, x in n.items(): print(f"  {s} : {x} ajoutée(s)")
    print(f"{sum(n.values())} entreprise(s) ajoutée(s) sur {len(lignes)} ligne(s) lue(s) ; registre : {avant} -> {len(reg['entreprises'])}" + (" (à blanc, rien écrit)" if a.a_blanc else ""))
