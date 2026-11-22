"""Test silencieux de l'historique du tableau de bord (outils/agents-json.py › historique, leads_a_appeler, aligner_jour, potentiel) : doublures, aucun réseau, fichier dans un dossier temporaire.
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
R = AJ._relances()                    # chargé avant de détourner AGENTS : critère de lead chaud et rythme de l'agent Relances
AJ.AGENTS = tmp / "agents"            # aucun devis-etat.json : devis inconnu = null
ok = True


def verifier(cond, texte):
    global ok
    print(("OK  " if cond else "ÉCHEC ") + texte); ok = ok and cond


def res(d=None): return {r: (d or {}).get(r, 0) for r in AJ.RESULTATS}


# Un appel compte le jour de la FEUILLE qui le porte (date de son titre), jamais le jour où la feuille a été modifiée : ici Sid a noté la feuille du 16/11 le 17 puis le 19.
FEUILLES = [{"jour": "2026-11-16", "modifiee": "2026-11-19", "resultats": res({"Pas de réponse": 6, "À rappeler": 2, "RDV pris": 1}), "avec": 9,
             "metiers": AJ.compter_metiers([("plombier", "À rappeler"), (" Plombier ", "RDV pris"), ("", "Pas de réponse")]),
             "lignes": [{"nom": "Envog Coiffure", "ville": "Rouen", "tel": "02 35 11 22 33", "resultat": "À rappeler", "note": "rappeler après 17 h"},
                        {"nom": "Fleurs Test", "ville": "Évreux", "tel": "02 32 00 00 01", "resultat": "À rappeler", "note": ""},
                        {"nom": "Boucherie Test", "ville": "Caen", "tel": "02 31 00 00 02", "resultat": "RDV pris", "note": ""}]},
            {"jour": "2026-11-17", "modifiee": "2026-11-17", "resultats": res({"À rappeler": 1}), "avec": 4,
             "lignes": [{"nom": "Envog Coiffure", "ville": "Rouen", "tel": "02 35 11 22 33", "resultat": "Trop cher", "note": "a rappelé pour dire non"}]},
            {"jour": "2026-11-18", "modifiee": "2026-11-17", "resultats": res({"RDV pris": 2}), "avec": 3, "lignes": []}]
VENTES = {"chiffres": [{"cle": "appels", "valeur": 12, "repartition": res({"À rappeler": 3})}, {"cle": "devis", "valeur": None}, {"cle": "paiements", "valeur": None}]}
QUAND = datetime(2026, 11, 18, 10, 0)
try:
    h = AJ.historique(QUAND, VENTES, FEUILLES)
    j = {e["date"]: e for e in h["jours"]}
    verifier(sorted(j) == ["2026-11-16", "2026-11-17", "2026-11-18"], "un jour par date depuis le 16/11 jusqu'à aujourd'hui")
    verifier(j["2026-11-16"]["appels"] == 9 and j["2026-11-16"]["leads_chauds"] == 2 and j["2026-11-16"]["rdv"] == 1, "16/11 compté depuis la feuille du 16/11, même notée les jours suivants")
    verifier(j["2026-11-17"]["appels"] == 4 and j["2026-11-17"]["leads_chauds"] == 1, "17/11 : seule la feuille du 17/11, jamais celle du 16 rouverte ce jour-là")
    verifier(all(e["devis"] is None and e["paiements"] is None for e in h["jours"]), "devis et paiements inconnus sur ce PC : null, jamais 0")
    verifier(j["2026-11-18"]["appels"] == 3 and not j["2026-11-18"]["complet"] and j["2026-11-17"]["complet"], "aujourd'hui depuis la feuille du jour, non complet ; jours passés complets")
    verifier(len(j["2026-11-16"]["resultats"]) == 8, "les 8 résultats sont présents pour chaque jour")
    m = j["2026-11-16"]["metiers"]
    verifier(m == {"Plombier": {"appels": 2, "chauds": 1, "rdv": 1}, "Non renseigné": {"appels": 1, "chauds": 0, "rdv": 0}}, "répartition par métier : casse et espaces unifiés, métier vide = « Non renseigné »")
    verifier(j["2026-11-17"]["metiers"] == {} and j["2026-11-18"]["metiers"] == {}, "feuilles sans colonne Métier connue : répartition vide, rien d'inventé")

    AJ.HISTO.parent.mkdir(parents=True); AJ.HISTO.write_text(json.dumps(h, ensure_ascii=False), encoding="utf-8")
    h2 = AJ.historique(QUAND, VENTES, FEUILLES)
    verifier(len(h2["jours"]) == 3 and len({e["date"] for e in h2["jours"]}) == 3, "relancer ne crée aucun doublon")
    verifier({e["date"]: e["appels"] for e in h2["jours"]} == {"2026-11-16": 9, "2026-11-17": 4, "2026-11-18": 3}, "relancer donne exactement les mêmes comptes (aucun cumul)")

    # Le bug du 22/11/2026 : un historique déjà faussé (la feuille du 16/11 recomptée en entier le 17 et le 18) se corrige tout seul au passage suivant.
    faux = json.loads(json.dumps(h2))
    for e in faux["jours"]:
        if e["date"] in ("2026-11-17", "2026-11-18"): e.update(appels=9, leads_chauds=2, rdv=1, resultats=res({"Pas de réponse": 6, "À rappeler": 2, "RDV pris": 1}))
    AJ.HISTO.write_text(json.dumps(faux, ensure_ascii=False), encoding="utf-8")
    h3 = AJ.historique(QUAND, VENTES, FEUILLES)
    j3 = {e["date"]: e for e in h3["jours"]}
    verifier(j3["2026-11-17"]["appels"] == 4 and j3["2026-11-17"]["leads_chauds"] == 1, "jour passé faussé : recalculé depuis sa feuille, même vers le bas")

    # Feuille mise à la corbeille au bout de 7 jours : le jour garde la valeur enregistrée, elle n'est jamais remise à zéro.
    AJ.HISTO.write_text(json.dumps(h3, ensure_ascii=False), encoding="utf-8")
    h4 = AJ.historique(QUAND, VENTES, [f for f in FEUILLES if f["jour"] != "2026-11-16"])
    verifier({e["date"]: e["appels"] for e in h4["jours"]}["2026-11-16"] == 9, "feuille à la corbeille : le jour déjà enregistré est gardé tel quel")
    h5 = AJ.historique(QUAND, VENTES, [])
    verifier({e["date"]: e["appels"] for e in h5["jours"]} == {"2026-11-16": 9, "2026-11-17": 4, "2026-11-18": 3}, "aucune feuille lue : l'historique n'est pas remis à zéro")

    h6 = AJ.historique(datetime(2026, 11, 19, 8, 0), {"chiffres": [{"cle": "appels", "valeur": None}]}, None)
    j6 = {e["date"]: e for e in h6["jours"]}
    verifier(j6["2026-11-18"]["complet"] and j6["2026-11-18"]["appels"] == 3 and "2026-11-19" not in j6, "sans lecture Google : la veille devient complète, aucune entrée inventée")
    h7 = AJ.historique(QUAND, {"chiffres": [{"cle": "appels", "valeur": 15, "repartition": res()}, {"cle": "paiements", "valeur": 1}]}, None)
    verifier({e["date"]: e for e in h7["jours"]}["2026-11-18"]["paiements"] == 1, "un paiement connu remplace null")

    # Leads chauds à appeler : critère et rythme de l'agent Relances, la raison vient de la feuille, rien n'est inventé.
    dispo, leads = AJ.leads_a_appeler(FEUILLES, "2026-11-22", R)
    noms = [l["nom"] for l in leads]
    verifier(dispo and noms == ["Fleurs Test"], "lead chaud exclu par une feuille plus récente (« Trop cher ») : retiré, comme chez l'agent Relances")
    verifier(leads[0]["raison"] == "À rappeler" and leads[0]["note"] == "" and leads[0]["appel"] == "2026-11-16", "la raison est le Résultat noté par Sid ; sans note de Sid, la note reste vide")
    verifier(leads[0]["relance"] == 1 and leads[0]["prevu"] == "2026-11-19" and leads[0]["due"] is True, "relance et date prévue calculées par relances.etape (jours ouvrés)")
    verifier(AJ.leads_a_appeler(FEUILLES, "2026-11-17", R)[1][0]["due"] is False, "avant le 3e jour ouvré : le lead est là mais pas encore dû")
    p = AJ.potentiel(dispo, leads); prix = AJ.prix_pack()
    verifier(prix == json.loads((AJ.OFFRE).read_text(encoding="utf-8-sig"))["offres"]["pack"]["prix_unique_eur"], "prix du pack lu dans OFFRE-REFERENCE.json")
    verifier(p["leads"] == 1 and p["valeur"] == prix and "indicatif" in p["detail"], "potentiel = leads chauds en cours (mêmes exclusions) × prix du pack, indicatif")
    verifier(AJ.potentiel(False, "mode test")["valeur"] is None, "feuilles illisibles : potentiel « — », rien d'inventé")

    # Carte « Aujourd'hui » : la feuille du jour, pas les feuilles rouvertes aujourd'hui.
    v = AJ.aligner_jour({"chiffres": [{"cle": "appels", "valeur": 99, "detail": "", "repartition": res({"À rappeler": 9})}, {"cle": "chauds", "valeur": 9, "detail": ""},
                                      {"cle": "rdv", "valeur": 9, "detail": ""}, {"cle": "paiements", "valeur": 2, "detail": "intact"}]}, FEUILLES, "2026-11-17")
    c = {x["cle"]: x for x in v["chiffres"]}
    verifier(c["appels"]["valeur"] == 4 and c["chauds"]["valeur"] == 1 and c["rdv"]["valeur"] == 0, "chiffres du jour = feuille « Appels Sid » du jour seulement")
    verifier(c["appels"]["repartition"]["À rappeler"] == 1 and c["paiements"]["valeur"] == 2, "répartition refaite, les autres chiffres (paiements) ne sont pas touchés")
    vide = AJ.aligner_jour({"chiffres": [{"cle": "appels", "valeur": 23, "detail": ""}]}, FEUILLES, "2026-11-22")
    verifier(vide["chiffres"][0]["valeur"] == 0 and "aucune feuille" in vide["chiffres"][0]["detail"], "aucune feuille pour aujourd'hui : 0 appel, la raison est dite")

    verifier(AJ.feuilles_sid(None)[0] is False, "JARVIS_TEST=1 sans doublure : aucune lecture Google")
finally:
    shutil.rmtree(tmp, ignore_errors=True)
sys.exit(0 if ok else 1)
