"""Test silencieux de l'historique du tableau de bord (outils/agents-json.py › historique, potentiel) : doublures, aucun réseau, fichier dans un dossier temporaire.
  python tests/test_historique_dashboard.py
"""
import importlib.util, json, os, shutil, sys, tempfile
from datetime import datetime
from pathlib import Path

os.environ["JARVIS_TEST"] = "1"
s = importlib.util.spec_from_file_location("aj", Path(__file__).resolve().parent.parent / "outils" / "agents-json.py")
AJ = importlib.util.module_from_spec(s); s.loader.exec_module(AJ)
tmp = Path(tempfile.mkdtemp(prefix="jarvis-histo-"))
AJ.HISTO = tmp / "data" / "historique.json"
AJ.AGENTS = tmp / "agents"            # aucun devis-etat.json : devis inconnu = null
ok = True


def verifier(cond, texte):
    global ok
    print(("OK  " if cond else "ÉCHEC ") + texte); ok = ok and cond


def res(d=None): return {r: (d or {}).get(r, 0) for r in AJ.RESULTATS}


FEUILLES = [{"modifiee": "2026-11-16", "resultats": res({"Pas de réponse": 6, "À rappeler": 2, "RDV pris": 1}), "avec": 9,
             "metiers": AJ.compter_metiers([("plombier", "À rappeler"), (" Plombier ", "RDV pris"), ("", "Pas de réponse")])},
            {"modifiee": "2026-11-17", "resultats": res({"À rappeler": 1}), "avec": 4},
            {"modifiee": "2026-11-17", "resultats": res({"RDV pris": 2}), "avec": 3}]
VENTES = {"chiffres": [{"cle": "appels", "valeur": 12, "repartition": res({"À rappeler": 3})}, {"cle": "devis", "valeur": None}, {"cle": "paiements", "valeur": None}]}
QUAND = datetime(2026, 11, 18, 10, 0)
try:
    h = AJ.historique(QUAND, VENTES, FEUILLES)
    j = {e["date"]: e for e in h["jours"]}
    verifier(sorted(j) == ["2026-11-16", "2026-11-17", "2026-11-18"], "reconstruction depuis le 16/11 : un jour par date jusqu'à aujourd'hui")
    verifier(j["2026-11-16"]["appels"] == 9 and j["2026-11-16"]["leads_chauds"] == 2 and j["2026-11-16"]["rdv"] == 1, "16/11 reconstruit depuis la feuille modifiée ce jour-là")
    verifier(j["2026-11-17"]["appels"] == 7 and j["2026-11-17"]["rdv"] == 2, "17/11 : deux feuilles modifiées ce jour-là additionnées")
    verifier(all(e["devis"] is None and e["paiements"] is None for e in h["jours"]), "devis et paiements inconnus sur ce PC : null, jamais 0")
    verifier(j["2026-11-18"]["appels"] == 12 and not j["2026-11-18"]["complet"] and j["2026-11-17"]["complet"], "aujourd'hui depuis ventes(), non complet ; jours passés complets")
    verifier(len(j["2026-11-16"]["resultats"]) == 8, "les 8 résultats sont présents pour chaque jour")
    m = j["2026-11-16"]["metiers"]
    verifier(m == {"Plombier": {"appels": 2, "chauds": 1, "rdv": 1}, "Non renseigné": {"appels": 1, "chauds": 0, "rdv": 0}}, "répartition par métier : casse et espaces unifiés, métier vide = « Non renseigné »")
    verifier(j["2026-11-17"]["metiers"] == {} and j["2026-11-18"]["metiers"] == {}, "feuilles sans colonne Métier connue : répartition vide, rien d'inventé")

    AJ.HISTO.parent.mkdir(parents=True); AJ.HISTO.write_text(json.dumps(h, ensure_ascii=False), encoding="utf-8")
    plus_bas = [dict(f, avec=1, resultats=res()) for f in FEUILLES]
    h2 = AJ.historique(QUAND, VENTES, plus_bas)
    verifier(len(h2["jours"]) == 3 and len({e["date"] for e in h2["jours"]}) == 3, "relancer ne crée aucun doublon")
    verifier({e["date"]: e["appels"] for e in h2["jours"]}["2026-11-16"] == 9, "un jour complet n'est jamais écrasé par des valeurs plus faibles")

    AJ.HISTO.write_text(json.dumps(h2, ensure_ascii=False), encoding="utf-8")
    h3 = AJ.historique(datetime(2026, 11, 19, 8, 0), {"chiffres": [{"cle": "appels", "valeur": None}]}, None)
    j3 = {e["date"]: e for e in h3["jours"]}
    verifier(j3["2026-11-18"]["complet"] and j3["2026-11-18"]["appels"] == 12 and "2026-11-19" not in j3, "le lendemain : la veille devient complète, appels inconnus = aucune entrée inventée")
    h4 = AJ.historique(QUAND, {"chiffres": [{"cle": "appels", "valeur": 15, "repartition": res()}, {"cle": "paiements", "valeur": 1}]}, None)
    verifier({e["date"]: e for e in h4["jours"]}["2026-11-18"]["paiements"] == 1, "un paiement connu remplace null")

    p = AJ.potentiel(True, FEUILLES); prix = AJ.prix_pack()
    verifier(prix == json.loads((AJ.OFFRE).read_text(encoding="utf-8-sig"))["offres"]["pack"]["prix_unique_eur"], "prix du pack lu dans OFFRE-REFERENCE.json")
    verifier(p["leads"] == 3 and p["valeur"] == 3 * prix and "indicatif" in p["detail"], "potentiel = leads chauds en cours × prix du pack, indicatif")
    verifier(AJ.potentiel(False, "mode test")["valeur"] is None, "feuilles illisibles : potentiel « — », rien d'inventé")
    verifier(AJ.feuilles_sid(None)[0] is False, "JARVIS_TEST=1 sans doublure : aucune lecture Google")
finally:
    shutil.rmtree(tmp, ignore_errors=True)
sys.exit(0 if ok else 1)
