#!/usr/bin/env python3
"""Tests silencieux de l'historique permanent des appels : AUCUN réseau, aucun Discord, fichiers temporaires.  python agents\\test_historique_appels.py
Garanties testées : ajout seulement (rien ne baisse, rien ne s'écrase), fichier illisible jamais écrasé, copie avant corbeille, chiffres déduits du Résultat, aucun nom dans ce que lit le
tableau de bord, alerte Discord une seule fois quand la feuille du jour disparaît."""
import contextlib, csv, importlib.util, io, json, os, socket, sys, tempfile, urllib.request
from datetime import datetime
from pathlib import Path
os.environ.setdefault("JARVIS_TEST", "1")
ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))


def reseau(*a, **k): raise AssertionError("appel réseau interdit dans les tests")
urllib.request.urlopen = reseau; socket.create_connection = reseau
import historique_appels as HA

echecs = 0
def verifier(cond, msg):
    global echecs
    if cond: print("  OK    " + msg)
    else: print("  ECHEC " + msg); echecs += 1


tmp = Path(tempfile.mkdtemp(prefix="hist-appels-test-")); F = tmp / "donnees" / "historique-appels.json"
ENTETE = ["Créneau", "Entreprise", "Métier", "Ville", "Téléphone", "Détail fiche", "Résultat", "Note"]
def feuille(*resultats):
    t = io.StringIO(); w = csv.writer(t); w.writerow(ENTETE)
    for i, r in enumerate(resultats): w.writerow(["9h", f"Entreprise {i}", "Plombier", "Rouen", f"02350000{i:02d}", "", r, "n" if r else ""])
    return t.getvalue()
T0 = datetime(2026, 11, 24, 19, 30)

print("1. Ajout seulement : un relevé identique n'est pas ajouté, un relevé plus pauvre n'efface rien")
F.parent.mkdir(parents=True)
verifier(HA.enregistrer_feuilles([("2026-11-23", "Sid", "Appels Sid 2026-11-23", feuille("RDV pris", "Pas de réponse", "À rappeler", ""))], F, T0) == 1, "premier relevé ajouté")
verifier(HA.enregistrer_feuilles([("2026-11-23", "Sid", "Appels Sid 2026-11-23", feuille("RDV pris", "Pas de réponse", "À rappeler", ""))], F, T0) == 0, "même feuille relue : aucun doublon")
avant = F.read_text(encoding="utf-8")
verifier(HA.enregistrer_feuilles([("2026-11-23", "Sid", "Appels Sid 2026-11-23", feuille("", "", "", ""))], F, T0) == 1, "feuille vidée par erreur : le relevé vide est AJOUTÉ (rien n'est modifié)")
h = HA.charger(F)
verifier(len(h["releves"]) == 2 and json.loads(avant)["releves"][0] == h["releves"][0], "le premier relevé est intact")
verifier(HA.par_jour(h)["2026-11-23"]["Sid"]["appele"] == 3, "les totaux restent ceux du relevé le plus complet (3 appels), pas du vide")
verifier(F.with_name(F.name + ".avant").exists(), "version précédente gardée dans historique-appels.json.avant")

print("2. Chiffres déduits du Résultat (8 valeurs), jamais inventés")
HA.enregistrer_feuilles([("2026-11-24", "Liam", "Appels Liam 2026-11-24", feuille("RDV pris", "Pas de réponse", "Pas de réponse", "Trop cher", "Je dois réfléchir", "À rappeler"))], F, T0)
c = HA.par_jour(HA.charger(F))["2026-11-24"]["Liam"]
verifier((c["appele"], c["decroche"], c["interesse"], c["rdv"], c["refus"], c["a_rappeler"]) == (6, 4, 3, 1, 1, 1), f"Liam : appelés 6, décrochés 4, intéressés 3, RDV 1, refus 1, à rappeler 1 ({c['appele']}, {c['decroche']}, {c['interesse']}, {c['rdv']}, {c['refus']}, {c['a_rappeler']})")
verifier(c["exemple_envoye"] is None and c["devis"] is None, "exemple envoyé et devis : null (absents des feuilles), pas 0")
verifier(HA.ajouter(HA.vide(), "2026-11-20", "Sid", "x", "A,B\n1,2\n") is False, "ancienne feuille sans colonne Résultat : ignorée")

print("3. Fichier illisible : jamais écrasé")
F2 = tmp / "casse.json"; F2.write_text("{pas du json", encoding="utf-8")
try: HA.enregistrer_feuilles([("2026-11-24", "Sid", "Appels Sid 2026-11-24", feuille("RDV pris"))], F2, T0); leve = False
except Exception: leve = True
verifier(leve and F2.read_text(encoding="utf-8") == "{pas du json", "l'erreur remonte et le fichier est inchangé")

print("4. Copie avant corbeille")
class Drive:
    def __init__(s, panne=False): s.panne, s.feuilles = panne, {"id1": ("Appels Sid 2026-11-18", feuille("Trop cher", "RDV pris"))}
    def lister_feuilles(s, racine): return [(i, n) for i, (n, _) in s.feuilles.items()]
    def lire_feuille_csv(s, i):
        if s.panne: raise OSError("panne simulée")
        return s.feuilles[i][1]
    def compte(s): return "contact.lmsites@gmail.com"
FICHIER_TEST = HA.FICHIER
verifier(HA.sauver_avant_corbeille(Drive(), "id1", "Appels Sid 2026-11-18") is True and HA.par_jour(HA.charger())["2026-11-18"]["Sid"]["appele"] == 2, "feuille copiée, la corbeille peut suivre")
verifier(HA.sauver_avant_corbeille(Drive(panne=True), "id1", "Appels Sid 2026-11-19") is False, "lecture impossible : False (la feuille ne doit pas partir à la corbeille)")
verifier(HA.sauver_avant_corbeille(Drive(), "id1", "2026-11-01") is True, "ancien dossier sans titre de feuille : rien à copier")

print("5. Ce que lit le tableau de bord : des comptes seulement")
HA.enregistrer_feuilles([("2026-11-24", "Sid", "Appels Sid 2026-11-24", feuille("RDV pris", "Pas de réponse"))], None, T0)
d = HA.pour_tableau_de_bord(T0, jours=30); t = json.dumps(d, ensure_ascii=False)
verifier(d["disponible"] and d["appelants"] == ["Sid"] and [j["date"] for j in d["jours"]] == ["2026-11-18", "2026-11-24"], "appelant Sid, jours triés")
verifier("Entreprise" not in t and "0235" not in t and '"note"' not in t, "aucun nom d'entreprise, téléphone ni note")
verifier(HA.pour_tableau_de_bord(T0, tmp / "absent.json")["disponible"] is False, "fichier absent sur ce PC : indisponible, jamais 0")
sortie = tmp / "data"; HA.ecrire_tableau_de_bord(sortie, T0)
verifier((sortie / "historique-appels.js").read_text(encoding="utf-8").startswith("window.JARVIS_APPELS = "), "historique-appels.js écrit pour la page")

print("6. Résumé du soir : relevé + alerte Discord UNE fois si la feuille du jour a disparu")
spec = importlib.util.spec_from_file_location("resume_sid_h", ICI / "resume-sid.py"); A = importlib.util.module_from_spec(spec); spec.loader.exec_module(A)
A.ETAT, A.JOURNAL, A.APPELS_SID_ETAT, A.APPELS_SID_CONFIG, A.APPELS_LIAM_CONFIG = (tmp / "etat.json", tmp / "j.log", tmp / "sid-etat.json", tmp / "sid-config.json", tmp / "liam-config.json")
A.APPELS_SID_CONFIG.write_text(json.dumps({"dossier_sid_id": "dossier"}), encoding="utf-8"); A.APPELS_LIAM_CONFIG.write_text("{}", encoding="utf-8")
ALERTES = []; A.alerter_discord = lambda texte: ALERTES.append(texte) or True
conf = {"envoi_automatique": True, "compte_google": "contact.lmsites@gmail.com"}
d = Drive(); d.feuilles = {"id1": ("Appels Sid 2026-11-23", feuille("RDV pris"))}
A.APPELS_SID_ETAT.write_text(json.dumps({"google": {"2026-11-24": {"feuille": "id-du-jour"}}}), encoding="utf-8")
etat = {"envoyes": {}}
msg = A.historiser(conf, "2026-11-24", etat, False, d)
verifier(len(ALERTES) == 1 and "2026-11-24" in ALERTES[0], "feuille du jour absente du Drive : une alerte Discord")
A.historiser(conf, "2026-11-24", etat, False, d)
verifier(len(ALERTES) == 1 and etat["disparues"]["2026-11-24"] is True, "deuxième passage : pas de seconde alerte")
d.feuilles["id-du-jour"] = ("Appels Sid 2026-11-25", feuille("RDV pris")); ALERTES.clear()
A.APPELS_SID_ETAT.write_text(json.dumps({"google": {"2026-11-25": {"feuille": "id-du-jour"}}}), encoding="utf-8")
A.historiser(conf, "2026-11-25", {"envoyes": {}}, False, d)
verifier(not ALERTES, "feuille du jour présente : aucune alerte")
verifier("0 feuille(s) lue(s)" in A.historiser(conf, "2026-11-25", {"envoyes": {}}, False, Drive(panne=True)), "une feuille illisible est sautée, le résumé continue")
verifier("à blanc" in A.historiser(conf, "2026-11-25", {"envoyes": {}}, True, d), "à blanc : rien n'est lu ni écrit")

print()
if echecs: print(f"{echecs} ÉCHEC(S)"); sys.exit(1)
print("OK : tous les tests de l'historique des appels passent")
