"""Test silencieux du bloc « Aujourd'hui » du tableau de bord (outils/agents-json.py › ventes) : doublures, aucun réseau, aucun fichier écrit.
  python tests/test_ventes_dashboard.py
"""
import importlib.util, json, os, sys
from datetime import datetime
from pathlib import Path

os.environ["JARVIS_TEST"] = "1"
s = importlib.util.spec_from_file_location("aj", Path(__file__).resolve().parent.parent / "outils" / "agents-json.py")
AJ = importlib.util.module_from_spec(s); s.loader.exec_module(AJ)
QUAND = datetime(2026, 11, 17, 18, 0)
ok = True


def verifier(cond, texte):
    global ok
    print(("OK  " if cond else "ÉCHEC ") + texte); ok = ok and cond


class Doublure:
    def __init__(self, appels, stripe): self.a, self.s = appels, stripe
    def cfg(self): return {}
    def stats_appels(self, conf, jour): return self.a
    def stripe_jour(self, jour): return self.s
    def _montants_texte(self, m): return f"{sum(m.values()) // 100} euros"


res = {"Pas de réponse": 5, "À rappeler": 2, "RDV pris": 1, "Je dois réfléchir": 3}
v = AJ.ventes(QUAND, Doublure((True, {"multi": True, "feuilles": [{}, {}], "resultats": res, "Appelé": 11, "a_rappeler": [{"entreprise": "Boulangerie Secrète", "note": "x"}]}),
                              (True, {"montants": {"EUR": 59500}, "paiements": 1, "partiel": False})))
c = {x["cle"]: x for x in v["chiffres"]}
verifier(c["appels"]["valeur"] == 11 and "2 feuilles" in c["appels"]["detail"], "appels notés par Sid : 11 sur 2 feuilles")
verifier(c["chauds"]["valeur"] == 5, "leads chauds = À rappeler + Je dois réfléchir")
verifier(c["rdv"]["valeur"] == 1, "rendez-vous pris")
verifier(c["paiements"]["valeur"] == 1 and "595 euros" in c["paiements"]["detail"], "paiements Stripe du jour")
verifier("Boulangerie Secrète" not in json.dumps(v, ensure_ascii=False), "aucun nom d'entreprise dans ventes.json")
verifier(("candidatures" in c) == (AJ.AGENTS / "alerte-candidatures.py").exists() and c.get("candidatures", {"valeur": None})["valeur"] is None, "candidatures : ligne seulement si l'agent existe, jamais un chiffre inventé")

v = AJ.ventes(QUAND, Doublure((False, "jeton Google d'un autre compte"), (False, "clé Stripe absente")))
c = {x["cle"]: x for x in v["chiffres"]}
verifier(all(c[k]["valeur"] is None and c[k]["raison"] for k in ("appels", "chauds", "rdv", "paiements")), "indisponible : « — » avec une raison, jamais un chiffre inventé")
verifier(all(x["valeur"] is None for x in AJ.ventes(QUAND)["chiffres"] if x["cle"] != "devis"), "JARVIS_TEST=1 sans doublure : aucun réseau, rien d'inventé")
sys.exit(0 if ok else 1)
