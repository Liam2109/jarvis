#!/usr/bin/env python3
"""Historique permanent des appels (décision de Liam du 24/11/2026) : B2B\\donnees\\historique-appels.json, hors git, repris par la sauvegarde de 03:30.

Pourquoi : les résultats de Sid et de Liam n'existent qu'à deux endroits, la feuille Google « Appels Sid / Appels Liam AAAA-MM-JJ » et, après la lecture de 07:30, le registre commun
(dernier résultat de chaque entreprise). Aucun des deux ne garde « combien d'appels, par qui, quel jour » : la feuille part à la corbeille au bout de 7 jours.

Règles : AJOUT SEULEMENT. Chaque relevé est une photo d'une feuille à un instant donné (jour de son titre, appelant, lignes notées) ; un relevé identique au précédent n'est pas
ajouté ; rien n'est jamais modifié ni supprimé. Pour un jour et un appelant, les totaux sont ceux du relevé le plus complet (le plus de résultats notés ; à égalité le plus récent) : une
feuille vidée par erreur ne fait jamais baisser l'historique. Avant chaque écriture, la version précédente est gardée dans historique-appels.json.avant (restaurable) ; la copie de 03:30
(sauvegarde-leads) fait le reste. Aucun réseau ici : les feuilles sont lues par l'appelant (resume-sid à 19:30, appels-sid avant la corbeille) avec ses propres accès Google.

Colonnes de la feuille : Résultat (8 valeurs) et Note. Les cases « décroché / intéressé / exemple envoyé / devis » n'existent pas dans le tableur : elles sont DÉDUITES du Résultat
(voir CHIFFRES) ; « exemple envoyé » et « devis » ne sont pas suivis par feuille et restent à null, jamais inventés."""
import csv, io, json, os, re, shutil, sys, tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

ICI = Path(__file__).resolve().parent
RACINE = ICI.parent
sys.path.insert(0, str(ICI))
FICHIER = RACINE / "donnees" / "historique-appels.json"
if os.environ.get("JARVIS_TEST") == "1":   # tests : jamais le vrai historique
    FICHIER = Path(tempfile.mkdtemp(prefix="historique-appels-test-")) / "historique-appels.json"

RESULTATS = ["Pas de réponse", "À rappeler", "RDV pris", "Non catégorique", "Je dois réfléchir", "Trop cher", "Déjà un site", "Pas le temps"]   # = appels-sid.RESULTATS
REFUS = ("Non catégorique", "Trop cher", "Déjà un site", "Pas le temps")
INTERESSE = ("À rappeler", "Je dois réfléchir", "RDV pris")
SID, LIAM = "Sid", "Liam"
TITRES = ((SID, re.compile(r"Appels (?:Sid )?(\d{4}-\d{2}-\d{2})")), (LIAM, re.compile(r"Appels Liam (\d{4}-\d{2}-\d{2})")))
CHIFFRES = ["appele", "decroche", "interesse", "exemple_envoye", "rdv", "devis", "refus", "a_rappeler"]


class ErreurHistorique(Exception):
    pass


def vide(): return {"version": 1, "releves": []}


def charger(fichier=None):
    f = Path(fichier or FICHIER)
    if not f.exists(): return vide()
    h = json.loads(f.read_text(encoding="utf-8"))   # illisible : l'erreur remonte, RIEN n'est écrasé
    if not isinstance(h, dict) or not isinstance(h.get("releves"), list): raise ErreurHistorique(f"{f.name} illisible : rien n'est écrit, restaurez {f.name}.avant ou la sauvegarde")
    return h


def ecrire(h, fichier=None):
    f = Path(fichier or FICHIER); f.parent.mkdir(parents=True, exist_ok=True)
    if f.exists(): shutil.copy2(f, f.with_name(f.name + ".avant"))
    tmp = f.with_name(f.name + ".tmp"); tmp.write_text(json.dumps(h, ensure_ascii=False, indent=1), encoding="utf-8"); os.replace(tmp, f)


def lignes_notees(csv_texte):
    """CSV d'une feuille -> (lignes notées [{entreprise, ville, tel, metier, resultat, note}], nombre de lignes) ; None si la feuille n'a pas de colonne Résultat (ancien format)."""
    lignes = list(csv.reader(io.StringIO(csv_texte or "")))
    if not lignes or "Résultat" not in lignes[0]: return None
    e = lignes[0]; ix = {c: (e.index(n) if n in e else None) for c, n in (("entreprise", "Entreprise"), ("ville", "Ville"), ("tel", "Téléphone"), ("metier", "Métier"), ("resultat", "Résultat"), ("note", "Note"))}
    v = lambda l, k: l[ix[k]].strip() if ix[k] is not None and ix[k] < len(l) else ""
    return [{c: v(l, c) for c in ix} for l in lignes[1:] if v(l, "resultat")], max(0, len(lignes) - 1)


def _signature(r): return [(l["entreprise"], l["tel"], l["resultat"], l["note"]) for l in r["lignes"]]


def ajouter(h, jour, appelant, feuille, csv_texte, maintenant=None):
    """Ajoute le relevé de la feuille (en mémoire, voir ecrire) sauf s'il est identique au dernier relevé du même jour et du même appelant ; une feuille sans colonne Résultat est
    ignorée. -> True si un relevé a été ajouté."""
    lu = lignes_notees(csv_texte)
    if lu is None: return False
    lignes, total = lu
    r = {"jour": jour, "appelant": appelant, "feuille": feuille, "releve_le": (maintenant or datetime.now()).strftime("%Y-%m-%d %H:%M:%S"), "total": total, "lignes": lignes}
    d = next((x for x in reversed(h["releves"]) if x["jour"] == jour and x["appelant"] == appelant), None)
    if d and _signature(d) == _signature(r) and d.get("total") == total: return False
    h["releves"].append(r); return True


def enregistrer_feuilles(feuilles, fichier=None, maintenant=None):
    """feuilles : [(jour, appelant, nom, csv_texte)]. Relit le fichier, ajoute, écrit une seule fois si besoin. -> nombre de relevés ajoutés. Une lecture impossible du fichier remonte."""
    h = charger(fichier); n = sum(1 for j, a, nom, t in feuilles if ajouter(h, j, a, nom, t, maintenant))
    if n: ecrire(h, fichier)
    return n


def titre(nom):
    """(appelant, jour) d'après le nom d'une feuille, ou None."""
    for qui, motif in TITRES:
        m = motif.fullmatch(nom or "")
        if m: return qui, m.group(1)
    return None


def releve_drive(drive, racines):
    """Lit (lecture seule) toutes les feuilles « Appels Sid / Appels Liam » des dossiers `racines` {appelant: id de dossier ou « root »} et les ajoute à l'historique.
    -> (relevés ajoutés, feuilles lues, noms des feuilles présentes sur le Drive). Une feuille illisible est sautée, jamais fatale."""
    lues, presentes = [], []
    for qui, racine in racines.items():
        if not racine: continue
        for i, nom in drive.lister_feuilles(racine):
            t = titre(nom)
            if not t or t[0] != qui: continue
            presentes.append(nom)
            try: lues.append((t[1], qui, nom, drive.lire_feuille_csv(i)))
            except Exception: continue
    return enregistrer_feuilles(lues), len(lues), presentes


def sauver_avant_corbeille(drive, id_, nom):
    """Appelé AVANT de mettre une feuille à la corbeille : copie ses résultats dans l'historique. -> True si c'est fait (ou si la feuille n'est pas une feuille d'appels à suivre) ;
    False si la lecture ou l'écriture a échoué : la feuille ne doit alors PAS être mise à la corbeille."""
    t = titre(nom)
    if not t: return True
    try: enregistrer_feuilles([(t[1], t[0], nom, drive.lire_feuille_csv(id_))]); return True
    except Exception: return False


# --- lecture : totaux par jour et par appelant -------------------------------------------------------------------------
def chiffres(lignes):
    """Chiffres déduits du Résultat. appelé = ligne notée ; décroché = appelé sauf « Pas de réponse » ; intéressé = À rappeler + Je dois réfléchir + RDV pris ; exemple envoyé et devis : None."""
    r = [l["resultat"] for l in lignes]
    return {"appele": len(r), "decroche": sum(1 for v in r if v != "Pas de réponse"), "interesse": sum(1 for v in r if v in INTERESSE), "exemple_envoye": None,
            "rdv": r.count("RDV pris"), "devis": None, "refus": sum(1 for v in r if v in REFUS), "a_rappeler": r.count("À rappeler"),
            "resultats": {v: r.count(v) for v in RESULTATS}}


def par_jour(h):
    """{jour: {appelant: chiffres}} : pour un jour et un appelant, le relevé le plus complet (le plus de lignes notées, à égalité le plus récent)."""
    meilleur = {}
    for r in h["releves"]:
        k = (r["jour"], r["appelant"]); b = meilleur.get(k)
        if b is None or len(r["lignes"]) >= len(b["lignes"]): meilleur[k] = r
    out = {}
    for (j, a), r in meilleur.items(): out.setdefault(j, {})[a] = chiffres(r["lignes"])
    return out


def pour_tableau_de_bord(maintenant=None, fichier=None, jours=30):
    """Ce que le tableau de bord lit (dashboard\\data\\historique-appels.js) : des COMPTES seulement, jamais un nom d'entreprise, un téléphone ni une note. {} si le fichier n'existe pas sur ce PC."""
    f = Path(fichier or FICHIER)
    if not f.exists(): return {"disponible": False, "raison": "historique-appels.json absent sur ce PC (il est tenu sur le serveur)", "jours": []}
    maintenant = maintenant or datetime.now(); depuis = (maintenant.date() - timedelta(days=jours - 1)).isoformat()
    p = par_jour(charger(f)); qui = sorted({a for x in p.values() for a in x}, key=lambda a: (a != SID, a))
    return {"disponible": True, "maj": maintenant.strftime("%Y-%m-%d %H:%M:%S"), "appelants": qui, "resultats": RESULTATS,
            "jours": [{"date": j, "par": {a: {c: v for c, v in x[a].items()} for a in x}} for j, x in sorted(p.items()) if j >= depuis]}


def ecrire_tableau_de_bord(sortie, maintenant=None, fichier=None):
    """Écrit data\\historique-appels.json et .js (lu par la page même en file://) dans le dossier `sortie` (dashboard\\data)."""
    d = pour_tableau_de_bord(maintenant, fichier); t = json.dumps(d, ensure_ascii=False, indent=1)
    sortie = Path(sortie); sortie.mkdir(parents=True, exist_ok=True)
    for nom, contenu in (("historique-appels.json", t), ("historique-appels.js", "window.JARVIS_APPELS = " + t + ";\n")):
        tmp = sortie / (nom + ".tmp"); tmp.write_text(contenu, encoding="utf-8"); os.replace(tmp, sortie / nom)


if __name__ == "__main__":
    h = charger(); p = par_jour(h)
    print(f"{len(h['releves'])} relevé(s), {len(p)} jour(s)" + (f", du {min(p)} au {max(p)}" if p else ""))
