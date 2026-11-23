#!/usr/bin/env python3
"""Test ciblé : limite de durée par étape et enregistrement au fil de l'eau (annuaire, OpenStreetMap). Aucun réseau, fausse horloge, fichiers temporaires.  python agents\\test_prospection_delai.py"""
import os, sys, tempfile, shutil
os.environ.setdefault("JARVIS_TEST", "1")
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import prospection as X

tmp = Path(tempfile.mkdtemp(prefix="prospection-test-delai-"))
X.ETAT, X.TROUVES = tmp / "etat.json", tmp / "trouves.csv"
(tmp / "liens-metiers.json").write_text(X.json.dumps({"electricien": "https://x/e/", "coiffeur": "https://x/c/"}), encoding="utf-8"); X.ICI = tmp
X.exclusions = lambda: (set(), set())
temps = [0.0]; X.horloge = lambda: temps[0]
conf = {**X.DEFAUT, "duree_max_etape_s": 100, "sauvegarde_tous": 3, "cible_trouves": 1000, "max_examinees": 1000, "pause_site_s": 0}


def cand(n): return {"siren": f"{n:09d}", "nc": f"ELEC {n}", "metier": "électricien", "cp": "76000", "ville": "Rouen", "dept": "76"}


def ligne(c): return {**{k: "" for k in X.COLS}, "nom": c["nc"].title(), "metier": c["metier"], "ville": "Rouen", "siren": c["siren"], "formulaire": "http://x/c", "statut": "trouvé"}


def tester(nom, marche):
    shutil.rmtree(tmp / "x", ignore_errors=True); X.ETAT.unlink(missing_ok=True); X.TROUVES.unlink(missing_ok=True); temps[0] = 0.0
    X.ecrire_trouves([]); marche()
    print("  OK   " + nom)


# 1. annuaire : après 100 s fictives (30 s par entreprise), l'étape s'arrête ; les entreprises livrées mais non examinées reviennent dans le tampon, rien n'est perdu
def annuaire_delai():
    X.etat_ecrire({"curseur": {"i": 0, "page": 1}, "vus": {}, "tampon": {}}, False)
    lots = [[cand(n) for n in range(1, 11)]]
    X.candidats = lambda etat, n, *a, **k: ([etat["vus"].update({c["siren"]: "examiné"}) for c in lots[0]] and lots.pop(0)) if lots else []
    def enrichir(c, etat, conf, stat=None, **k):
        temps[0] += 30; stat.update(site=True, faible=True, constats=["https"], canal="formulaire"); return ligne(c), None
    X.enrichir = enrichir
    r = X.cmd_chercher(False, conf)
    assert len(r) == 4, [x["nom"] for x in r]   # 30, 60, 90 s ; la 4e commence à 90 s (< 100) et finit à 120 s ; la 5e est refusée (120 s > 100 s)
    e = X.etat_lire(); rendues = e["tampon"]["43.21A"]
    assert [c["siren"] for c in rendues] == [f"{n:09d}" for n in range(5, 11)], rendues
    assert not any(s in e["vus"] for s in (c["siren"] for c in rendues)), "les entreprises non examinées ne doivent pas être « vues »"
    assert len(X.lire_trouves()) == 4, "prospection-trouves.csv doit contenir les 4 entreprises trouvées avant l'arrêt"


# 2. annuaire : une panne au milieu n'efface pas ce qui est déjà trouvé (sauvegarde au fil de l'eau), l'entreprise en cause revient dans le tampon
def annuaire_panne():
    X.etat_ecrire({"curseur": {"i": 0, "page": 1}, "vus": {}, "tampon": {}}, False)
    lots = [[cand(n) for n in range(1, 8)]]
    X.candidats = lambda etat, n, *a, **k: ([etat["vus"].update({c["siren"]: "examiné"}) for c in lots[0]] and lots.pop(0)) if lots else []
    def enrichir(c, etat, conf, stat=None, **k):
        if c["siren"] == "000000005": raise OSError("panne simulée")
        stat.update(site=True, faible=True, constats=["https"], canal="formulaire"); return ligne(c), None
    X.enrichir = enrichir
    try: X.cmd_chercher(False, {**conf, "duree_max_etape_s": 0}); assert False, "la panne doit remonter"
    except OSError: pass
    assert [l["siren"] for l in X.lire_trouves()] == [f"{n:09d}" for n in range(1, 5)], X.lire_trouves()
    e = X.etat_lire(); assert [c["siren"] for c in e["tampon"]["43.21A"]] == [f"{n:09d}" for n in range(5, 8)] and "000000005" not in e["vus"], e


# 3. à blanc : rien n'est écrit, même avec une durée dépassée
def annuaire_a_blanc():
    X.etat_ecrire({"curseur": {"i": 0, "page": 1}, "vus": {}, "tampon": {}}, False); avant = X.ETAT.read_text(encoding="utf-8")
    lots = [[cand(n) for n in range(1, 6)]]
    X.candidats = lambda etat, n, *a, **k: lots.pop(0) if lots else []
    def enrichir(c, etat, conf, stat=None, **k):
        temps[0] += 60; stat.update(site=True, faible=True, constats=["https"], canal="formulaire"); return ligne(c), None
    X.enrichir = enrichir
    X.cmd_chercher(True, conf)
    assert X.ETAT.read_text(encoding="utf-8") == avant and X.lire_trouves() == [], "à blanc : état et fichier inchangés"


# 4. OpenStreetMap : arrêt après la durée, la réserve reste dans l'état, sauvegarde toutes les 3 entreprises
def osm_delai():
    tampon = [{"id": f"node/{n}", "nom": f"Elec {n}", "metier": "électricien", "ville": "Rouen", "cp": "76000", "site": "", "emails": [], "telephone": f"02 35 00 00 {n:02d}", "source": "OpenStreetMap"} for n in range(1, 9)]
    X.etat_ecrire({"vus": {}, "osm": {"faits": [], "tampon": tampon}}, False)
    sauvegardes = []; vrai = X.sauver_au_fil
    X.sauver_au_fil = lambda *a, **k: (sauvegardes.append(len(a[2])), vrai(*a, **k))[1]
    def enrichir_osm(c, etat, conf, lire, outils, st, dormir):
        temps[0] += 30; st.update(canal="telephone", site=False); return {**{k: "" for k in X.COLS}, "nom": c["nom"], "metier": c["metier"], "ville": "Rouen", "telephone": c["telephone"], "statut": "sans site, téléphone", "siren": c["id"]}, None
    X.enrichir_osm = enrichir_osm; X.requetes_osm = lambda etat: iter([])
    X.motif_ligne = lambda *a, **k: None; X.memoriser_telephone = lambda *a, **k: None
    try: r = X.cmd_decouvrir(False, {**conf, "osm_max_examinees": 40, "osm_max_jour": 500, "osm_requetes_par_passage": 0, "pause_overpass_s": 0}, dormir=lambda s: None)
    finally: X.sauver_au_fil = vrai
    assert len(r) == 4, len(r)
    e = X.etat_lire(); assert [c["id"] for c in e["osm"]["tampon"]] == [f"node/{n}" for n in range(5, 9)], e["osm"]["tampon"]
    assert len(X.lire_trouves()) == 4 and 3 in sauvegardes, (sauvegardes, len(X.lire_trouves()))


try:
    print("Limite de durée par étape et sauvegarde au fil de l'eau")
    orig = (X.candidats, X.enrichir, X.exclusions)
    tester("annuaire : arrêt après la durée, rien de perdu", annuaire_delai)
    tester("annuaire : une panne garde les entreprises déjà trouvées", annuaire_panne)
    tester("annuaire : à blanc, rien d'écrit", annuaire_a_blanc)
    tester("OpenStreetMap : arrêt après la durée, réserve conservée", osm_delai)
    assert X.delai_depasse(0, {"duree_max_etape_s": 0}) is False and X.delai_depasse(0, {}) is False, "0 ou absent = sans limite"
    assert "duree_max_etape_s" in X.DEFAUT and X.DEFAUT["duree_max_etape_s"] > 0
    print("OK : tous les tests passent")
finally:
    shutil.rmtree(tmp, ignore_errors=True)
