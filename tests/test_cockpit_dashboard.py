"""Test silencieux du cockpit « Aujourd'hui » (outils/agents-json.py › etat_agent, actions_du_jour) : aucun réseau, aucun fichier écrit.
  python tests/test_cockpit_dashboard.py
"""
import importlib.util, os, sys
from datetime import datetime
from pathlib import Path

os.environ["JARVIS_TEST"] = "1"
s = importlib.util.spec_from_file_location("aj", Path(__file__).resolve().parent.parent / "outils" / "agents-json.py")
AJ = importlib.util.module_from_spec(s); s.loader.exec_module(AJ)
ok = True


def verifier(cond, texte):
    global ok
    print(("OK  " if cond else "ÉCHEC ") + texte); ok = ok and cond


mer = datetime(2026, 11, 25, 20, 30); sam = datetime(2026, 11, 28, 20, 30); matin = datetime(2026, 11, 25, 7, 0)
e = AJ.etat_agent
verifier(e(mer, "2026-11-25 19:30:10", "19:30", None, None)[0] == "ok", "agent du soir passé aujourd'hui : ok")
verifier(e(mer, "2026-11-24 19:30:10", "19:30", None, None)[0] == "bloque", "agent du soir pas passé, heure + 60 min dépassée : bloqué")
verifier(e(matin, "2026-11-24 19:30:10", "19:30", None, None)[0] == "attente", "agent du soir avant son heure : en attente")
verifier(e(mer, "2026-11-25 20:25:00", None, 10, None)[0] == "ok", "agent toutes les 10 min, passé il y a 5 min : ok")
verifier(e(mer, "2026-11-25 18:00:00", None, 10, None)[0] == "bloque", "agent toutes les 10 min, silencieux 2 h 30 : bloqué")
verifier(e(sam, "2026-11-27 08:00:00", "08:00", None, [0, 1, 2, 3, 4])[0] == "repos", "agent des jours ouvrés un samedi : repos, pas bloqué")
verifier(e(mer, "2026-11-25 20:25:00", None, 10, None, arret=True)[0] == "auto-stop", "arrêt automatique : AUTO-STOP")
verifier(e(mer, "2026-11-25 20:25:00", None, 10, None, suspendu=True)[0] == "auto-stop", "agent suspendu : AUTO-STOP")
verifier(e(mer, "2026-11-25 20:25:00", None, 10, None, erreur="en erreur")[0] == "bloque", "erreur du dernier passage : bloqué")
verifier(e(mer, None, None, 10, None)[0] == "bloque", "aucun passage visible pour un agent fréquent : bloqué")
a = AJ.actions_du_jour(3)
verifier(len(a) <= 3 and all(x["texte"] and len(x["texte"]) <= 125 for x in a), "au plus 3 actions, texte court")
verifier(not a or a[0]["urgent"] or not any(x["urgent"] for x in a), "URGENT passe en premier")
# 25/11/2026 : liste des appels (un appel par ligne, sans téléphone, heure jamais inventée) et source des leads chauds
ap = AJ.appels_liste()
verifier(ap["heure_notee"] is False and all(x["heure"] == "" for x in ap["appels"]), "liste des appels : l'heure n'est jamais inventée")
verifier(all(set(x) == {"nom", "ville", "metier", "date", "heure", "resultat", "note", "appelant"} for x in ap["appels"]), "liste des appels : aucun téléphone, mêmes champs partout")
verifier(all(x["resultat"] and len(x["date"]) == 10 for x in ap["appels"]), "liste des appels : chaque ligne a un résultat et une date")
verifier(AJ.sources_drive([{"jour": "2026-11-16", "lignes": [{"nom": "Envog Coiffure"}]}]) == {"2026-11-16": {"envogcoiffure"}}, "sources du Drive : noms normalisés par jour de feuille")
# 25/11/2026 : pages du tableau de bord (structure du fichier, pas de rendu)
html = (Path(__file__).resolve().parent.parent / "dashboard" / "index.html").read_text(encoding="utf-8")
jour = html[html.index("function vueJour()"):html.index("function vueChauds()")]
verifier("zoneLeads" not in jour and "LinkedIn" not in jour and "ck-diag" not in jour and "ck-bandeau" not in jour, "Aujourd'hui : ni leads chauds, ni LinkedIn, ni diagnostic, ni bandeau")
verifier('"Appels passés"' in jour and '"Décrochés"' in jour and '"Devis envoyés"' in jour and '"Paiements"' in jour, "Aujourd'hui : gros chiffre à gauche, trois lignes à droite, deux cartes (devis, paiements)")
verifier("lkResume()" in html and "linkedin_stop" in html and "function diagnostic()" in html and "data-pole" in html and "pointerdown" in html and "jarvis-archi-pos" in html, "LinkedIn avec état, Agents avec diagnostic, architecture déplaçable avec filtres")
sys.exit(0 if ok else 1)
