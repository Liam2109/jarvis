#!/usr/bin/env python3
"""Harness - registre commun des entreprises, listes de Sid et de Liam (décision de Liam du 15/11/2026, actif le 17/11/2026). Sans réseau, sans vrai Drive :
entreprises fictives générées ici, résultats fictifs (tests\\fixtures\\resultats-appels.json), faux Drive en mémoire, dossiers temporaires."""
import csv, json, os, shutil, socket, tempfile, unittest, urllib.request
from pathlib import Path
import commun as C

VRAI_REGISTRE = C.RACINE / "B2B" / "donnees" / "registre-entreprises.json"
AVANT_VRAI = VRAI_REGISTRE.stat().st_mtime_ns if VRAI_REGISTRE.exists() else None
L = C.agent("appels-liam"); A = L.A; RG = A.RG; P = A.P; S = A.S
import traces as T


def interdit(*a, **k): raise AssertionError("accès réseau interdit dans les tests")
urllib.request.urlopen = interdit; socket.create_connection = interdit
A.chercher_site_web = lambda *a, **k: ""; A.lire_site = lambda *a, **k: None

FIX = json.loads((C.FIXTURES / "resultats-appels.json").read_text(encoding="utf-8"))
VILLES = {"76": [("Rouen", "76000"), ("Le Havre", "76600"), ("Dieppe", "76200")], "27": [("Évreux", "27000"), ("Vernon", "27200"), ("Louviers", "27400")],
          "14": [("Caen", "14000"), ("Lisieux", "14100"), ("Bayeux", "14400")], "50": [("Saint-Lô", "50000"), ("Cherbourg", "50100"), ("Granville", "50400")],
          "61": [("Alençon", "61000"), ("Argentan", "61200"), ("Flers", "61100")]}
METIERS = ["plombier-chauffagiste", "électricien", "coiffeur", "restaurant", "boulangerie", "fleuriste", "garage automobile"]
CR, NOM, MET, VIL, TEL, DET, RES, NOTE = range(8)


def tel(i): return "02 " + " ".join(f"{i:08d}"[k:k + 2] for k in range(0, 8, 2))


def entreprises(par=4):
    out, i = [], 1
    for d, vs in VILLES.items():
        for v, cp in vs:
            for m in METIERS:
                for k in range(par):
                    l = {c: "" for c in P.COLS}; l.update(nom=f"Fictive {m.split()[0].capitalize()} {d}-{v[:3]}-{k}", metier=m, ville=v, cp=cp, telephone=tel(i), statut="sans site, téléphone")
                    out.append(l); i += 1
    return out


class Monde:
    def __init__(self, par=4):
        self.tmp = Path(tempfile.mkdtemp(prefix="appels-registre-")); ag = self.tmp / "agents"; ag.mkdir(); (self.tmp / "docs").mkdir()
        A.SORTIE = self.tmp / "docs" / "sid"; A.MAPS = self.tmp / "prospects_maps.csv"
        A.CONFIG, A.ETAT, A.VERROU, A.ARRET, A.JOURNAL, A.HISTORIQUE = ag / "appels-sid-config.json", ag / "appels-sid-etat.json", ag / "appels-sid.verrou", ag / "appels-sid.arret", ag / "appels-sid-journal.log", ag / "appels-sid-historique.json"
        A.CONFIG_LIAM, A.ETAT_LIAM, A.PROSPECTION_CONFIG = ag / "appels-liam-config.json", ag / "appels-liam-etat.json", ag / "prospection-config.json"
        L.ARRET, L.JOURNAL = ag / "appels-liam.arret", ag / "appels-liam-journal.log"
        RG.FICHIER = self.tmp / "donnees" / "registre-entreprises.json"
        P.TROUVES, P.DOCS, P.ICI, P.ETAT, S.FICHIER = self.tmp / "prospection-trouves.csv", self.tmp / "docs", ag, ag / "prospection-etat.json", self.tmp / "suivi-prospects.csv"
        shutil.copy(C.AGENTS / "appels-sid-config.json", A.CONFIG); shutil.copy(C.AGENTS / "appels-liam-config.json", A.CONFIG_LIAM)   # les vrais réglages versionnés (100 et 15)
        (ag / "exclus-emails.json").write_text("[]", encoding="utf-8"); A.HISTORIQUE.write_text("{}", encoding="utf-8")
        P.ecrire_trouves(entreprises(par), P.TROUVES); S.ecrire([])
        with open(A.MAPS, "w", encoding="utf-8-sig", newline="") as f: csv.writer(f, delimiter=";").writerow(["nom", "metier", "ville", "telephone", "note", "avis", "site"])

    def sid(self, jour):
        conf = A.cfg(); etat = A.etat_lire(); return A.preparer_registre(RG.SID, conf, etat, jour, False, None, hors_ligne=True)

    def liam(self, jour):
        conf = A.cfg_liam(); etat = A.etat_liam_lire(); return A.preparer_registre(RG.LIAM, conf, etat, jour, False, None, hors_ligne=True)

    def lire(self, f):
        with open(f, encoding="utf-8-sig", newline="") as fh: return list(csv.reader(fh, delimiter=";"))

    def remplir(self, f, v="Non catégorique"):
        """Sid a rempli toute sa feuille (cas réel) : chaque Résultat vide reçoit `v`."""
        lignes = self.lire(f)
        for l in lignes[1:]: l[RES] = l[RES] or v
        self.ecrire(f, lignes)

    def ecrire(self, f, lignes):
        with open(f, "w", encoding="utf-8-sig", newline="") as fh: csv.writer(fh, delimiter=";").writerows(lignes)


def muet(fn, *a, **k):
    import contextlib, io
    with contextlib.redirect_stdout(io.StringIO()): return fn(*a, **k)


class Regles(unittest.TestCase):
    def test_cle_et_doublons(self):
        reg = RG.vide(); k = RG.donner(reg, {"nom": "Plomberie Éric", "ville": "Évreux", "tel": "02 32 00 00 01", "metier": "plombier", "dept": "27"}, RG.SID, "2026-11-17")
        self.assertEqual(k, "plomberie eric|evreux|0232000001")
        self.assertTrue(RG.connue(reg, "PLOMBERIE ERIC", "evreux", "")); self.assertTrue(RG.connue(reg, "Autre nom", "Rouen", "+33 2 32 00 00 01"))
        self.assertFalse(RG.connue(reg, "Plomberie Éric", "Rouen", "02 35 00 00 09"))
        x = reg["entreprises"][k]
        for champ in ("departement", "metier", "date", "a_qui", "essais", "dernier_resultat"): self.assertIn(champ, x)

    def test_dates_dans_la_note(self):
        j = "2026-11-17"   # un mardi
        self.assertEqual(RG.date_dans_note("rappeler le 20/11", j), "2026-11-20")
        self.assertEqual(RG.date_dans_note("le 2026-11-24 à 9 h", j), "2026-11-24")
        self.assertEqual(RG.date_dans_note("jeudi après 17 h", j), "2026-11-19")
        self.assertEqual(RG.date_dans_note("demain", j), "2026-11-18")
        self.assertEqual(RG.date_dans_note("samedi", j), "2026-11-23", "un samedi : le lundi suivant")
        self.assertIsNone(RG.date_dans_note("plus tard", j))

    def test_reprises(self):
        reg = RG.vide(); e = {"nom": "X", "ville": "Caen", "tel": "02 31 00 00 01", "metier": "coiffeur", "dept": "14"}; k = RG.donner(reg, e, RG.SID, "2026-11-17"); x = reg["entreprises"][k]
        RG.noter(reg, k, "", "", "2026-11-17", RG.SID); self.assertEqual((x["retour"], x["pour"], x["tete"]), ("2026-11-18", RG.SID, True))
        for n, retour in ((1, "2026-11-23"), (2, "2026-11-26")):
            RG.donner(reg, e, RG.SID, x["retour"]); RG.noter(reg, k, "Pas de réponse", "", "2026-11-18" if n == 1 else "2026-11-23", RG.SID)
            self.assertEqual((x["essais"], x["retour"]), (n, retour), "Pas de réponse : 3 jours ouvrés plus tard")
        RG.donner(reg, e, RG.SID, "2026-11-26"); RG.noter(reg, k, "Pas de réponse", "", "2026-11-26", RG.SID)
        self.assertEqual((x["essais"], x["statut"]), (3, "terminée"), "3 essais au plus"); self.assertEqual(RG.dues(reg, "2027-01-01", RG.SID), [])
        k2 = RG.donner(reg, {**e, "nom": "Y", "tel": "02 31 00 00 02"}, RG.SID, "2026-11-17"); RG.noter(reg, k2, "Je dois réfléchir", "", "2026-11-17", RG.SID)
        self.assertEqual([k for k, _ in RG.dues(reg, "2026-11-20", RG.LIAM)], [k2]); self.assertEqual(RG.dues(reg, "2026-11-19", RG.LIAM), []); self.assertEqual(RG.dues(reg, "2026-11-20", RG.SID), [])
        for i, v in enumerate(RG.FINAUX):
            kk = RG.donner(reg, {**e, "nom": f"F{i}", "tel": f"02 31 00 01 {10 + i}"}, RG.SID, "2026-11-17"); RG.noter(reg, kk, v, "", "2026-11-17", RG.SID)
            self.assertEqual(reg["entreprises"][kk]["statut"], "terminée", v)
        self.assertFalse(any(x.get("statut") == "à reprendre" for x in reg["entreprises"].values() if x["nom"].startswith("F")))


class Listes(unittest.TestCase):
    def setUp(self): self.m = Monde()

    def test_lundi_16_inchange(self):
        muet(A.main, ["preparer", "--jour", "2026-11-16", "--a-blanc", "--hors-ligne"])
        self.assertFalse(RG.FICHIER.exists(), "lundi 16/11 : ancienne génération, le registre n'est ni créé ni lu")
        self.assertFalse(RG.actif("2026-11-16")); self.assertTrue(RG.actif("2026-11-17"))

    def test_sid_et_liam_le_17(self):
        n_sid = A.cfg()["par_liste"]; self.assertEqual(n_sid, 100, "même nombre que la génération actuelle (appels-sid-config.json, par_liste)")
        sid = muet(self.m.sid, "2026-11-17"); liam = muet(self.m.liam, "2026-11-17")
        self.assertEqual(len(sid), n_sid); self.assertEqual(len(liam), 15); self.assertEqual(A.cfg_liam()["par_liste"], 15)
        lignes = self.m.lire(A.chemin("2026-11-17"))
        self.assertEqual(lignes[0], A.COLONNES); self.assertEqual(len(lignes) - 1, n_sid)
        self.assertTrue(all(8 * 60 <= A._debut_minutes(l[CR]) < 19 * 60 for l in lignes[1:]), "créneaux 08 h - 19 h")
        self.assertEqual(len({l[TEL] for l in lignes[1:]}), n_sid, "toutes différentes")
        par_dept = {d: sum(1 for c in sid if c["dept"] == d) for d in VILLES}
        self.assertTrue(all(18 <= n <= 22 for n in par_dept.values()), f"répartie sur les 5 départements : {par_dept}")
        self.assertGreaterEqual(len({c["metier"] for c in sid}), 5, "mélangée entre métiers")
        voisins = sum(1 for a, b in zip(lignes[1:], lignes[2:]) if a[VIL] == b[VIL])
        self.assertEqual(voisins, 0, "jamais deux lignes voisines de la même ville")
        ls = self.m.lire(A.chemin_liam("2026-11-17"))
        self.assertEqual(ls[0], A.COLONNES); self.assertFalse({l[TEL] for l in ls[1:]} & {l[TEL] for l in lignes[1:]}, "aucune entreprise de Liam n'est chez Sid")
        reg = RG.charger(); self.assertEqual(len(reg["entreprises"]), n_sid + 15)
        self.assertEqual({x["a_qui"] for x in reg["entreprises"].values()}, {RG.SID, RG.LIAM})

    def test_reprises_entre_jours(self):
        muet(self.m.sid, "2026-11-17"); muet(self.m.liam, "2026-11-17")
        f = A.chemin("2026-11-17"); lignes = self.m.lire(f); corps = lignes[1:]
        nom = {}
        for i, l in enumerate(corps):
            v, note = FIX["lignes"][i] if i < len(FIX["lignes"]) else (FIX["reste"], "")
            l[RES], l[NOTE] = v, note; nom.setdefault(v + "|" + note, l[NOM])
        self.m.ecrire(f, lignes)
        pdr, rap20, refl, rdv, vide, rap_sans = (nom["Pas de réponse|"], nom["À rappeler|rappeler le 20/11 après 17 h"], nom["Je dois réfléchir|voir avec son associé"],
                                                 nom["RDV pris|jeudi 10 h"], nom["|"], nom["À rappeler|pas de date"])
        finals = {nom[f"{v}|"] for v in ("Non catégorique", "Trop cher", "Déjà un site", "Pas le temps")} | {rdv}
        s18 = muet(self.m.sid, "2026-11-18"); l18 = self.m.lire(A.chemin("2026-11-18"))
        reg = RG.charger(); self.assertIn(f"{RG.SID}|2026-11-17", reg["feuilles_lues"], "Résultat de la veille lus AVANT la génération")
        self.assertEqual(l18[1][NOM], vide, "ligne sans Résultat : en tête de la liste suivante"); self.assertIn("sans résultat", l18[1][DET])
        n18 = {l[NOM] for l in l18[1:]}
        self.assertNotIn(rap_sans, n18, "À rappeler : lead chaud, plus jamais chez Sid (17/11/2026)")
        self.assertFalse({pdr, rap20, refl} & n18); self.assertFalse(finals & n18)
        self.m.remplir(A.chemin("2026-11-18")); muet(self.m.liam, "2026-11-18"); muet(self.m.sid, "2026-11-19"); muet(self.m.liam, "2026-11-19")
        self.assertIn(rap_sans, {l[NOM] for l in self.m.lire(A.chemin_liam("2026-11-18"))[1:]}, "À rappeler sans date lisible : liste de Liam du jour ouvré suivant")
        self.m.remplir(A.chemin("2026-11-19")); muet(self.m.sid, "2026-11-20"); muet(self.m.liam, "2026-11-20")
        l20 = {l[NOM]: l for l in self.m.lire(A.chemin("2026-11-20"))[1:]}; liam20 = self.m.lire(A.chemin_liam("2026-11-20")); lm20 = {l[NOM]: l for l in liam20[1:]}
        self.assertNotIn(rap20, l20, "À rappeler : jamais chez Sid"); self.assertIn(rap20, lm20, "À rappeler : liste de Liam le jour écrit dans Note (20/11)")
        self.assertIn("note : rappeler le 20/11", lm20[rap20][DET])
        self.assertIn(pdr, l20, "Pas de réponse le 17 : de retour 3 jours ouvrés plus tard (le 20)")
        tete20 = [l for l in liam20[1:] if l[NOM] in (refl, rap20, rap_sans)]
        self.assertEqual(liam20[1:len(tete20) + 1], tete20, "leads chauds (Je dois réfléchir, À rappeler) en tête de la liste de Liam")
        self.assertIn("Relance « Je dois réfléchir »", lm20[refl][DET], "Je dois réfléchir : relance de Liam 3 jours plus tard")
        self.assertNotIn(refl, l20, "jamais dans la liste de Sid")
        for j in ("2026-11-23", "2026-11-24"): muet(self.m.sid, j); muet(self.m.liam, j)
        tous = set()
        for j in ("2026-11-18", "2026-11-19", "2026-11-20", "2026-11-23", "2026-11-24"):
            tous |= {l[NOM] for l in self.m.lire(A.chemin(j))[1:]} | {l[NOM] for l in self.m.lire(A.chemin_liam(j))[1:]}
        self.assertFalse(finals & tous, "RDV pris, Non catégorique, Trop cher, Déjà un site, Pas le temps : jamais redonnée")
        x = RG.charger()["entreprises"]; e = next(v for v in x.values() if v["nom"] == rdv)
        self.assertEqual((e["dernier_resultat"], e["essais"], e["a_qui"]), ("RDV pris", 1, RG.SID))

    def test_feuille_google_illisible_non_marquee(self):
        muet(self.m.sid, "2026-11-17"); etat = A.etat_lire(); etat["google"]["2026-11-17"] = {"feuille": "F1"}; A.etat_ecrire(etat)
        class Panne:
            def lire_feuille_csv(self, i): raise OSError("panne simulée")
        conf = A.cfg(); conf["envoi_automatique"] = True
        reg = RG.charger(); lues, _, echecs = muet(A.lire_resultats, reg, "2026-11-18", [(RG.SID, conf, etat, A.chemin)], Panne())
        self.assertEqual((lues, len(echecs)), (0, 1)); self.assertNotIn(f"{RG.SID}|2026-11-17", reg["feuilles_lues"], "jamais marquée lue : relue au passage suivant")

    def test_stock_et_surveillant(self):
        dossier = Path(os.environ["JARVIS_HARNESS_LOGS"]); jour = "2026-11-17"; aujourd = __import__("datetime").date.today().isoformat()   # la trace est datée du jour où le code tourne
        conf, cl = A.cfg(), A.cfg_liam(); etat = A.etat_lire(); RG.sauver(RG.vide())
        stock, seuil = muet(A.verifier_stock, conf, cl, etat, jour, "appels-sid-test-stock")
        self.assertEqual(seuil, 3 * (100 + 15)); self.assertGreaterEqual(stock, seuil); self.assertEqual(T.lire("appels-sid-test-stock", aujourd, dossier), [], "silencieux quand le stock suffit")
        muet(self.m.sid, jour); muet(self.m.liam, jour)
        stock, seuil = muet(A.verifier_stock, conf, cl, A.etat_lire(), jour, "appels-sid-test-stock")
        self.assertLess(stock, seuil); t = T.lire("appels-sid-test-stock", aujourd, dossier)
        self.assertTrue(t and t[-1]["ok"] is False and "stock bas" in t[-1]["erreur"], "trace en erreur : le surveillant la signale")

    def test_lot_emails_dans_le_registre(self):
        lot = [{"nom": "Fictive Plombier 76-Rou-0", "ville": "Rouen", "telephone": tel(1), "metier": "plombier-chauffagiste", "cp": "76000"}]
        muet(P.noter_lot_registre, lot)
        x = next(iter(RG.charger()["entreprises"].values())); self.assertEqual(x["a_qui"], RG.LOT)
        sid = muet(self.m.sid, "2026-11-17"); self.assertNotIn(tel(1).replace(" ", ""), {c["tel"].replace(" ", "") for c in sid}, "déjà dans un lot : jamais donnée à Sid")
        av = P.aujourdhui; P.aujourdhui = lambda: "2026-11-16"
        try: self.assertIsNone(P.registre_commun(), "lots : registre seulement à partir du 17/11")
        finally: P.aujourdhui = av


class FauxDrive:
    def __init__(self): self.feuilles, self.dossiers, self.corbeille, self.supprimes = {}, {}, set(), []
    def lister_feuilles(self, parent): return [(i, n) for i, (n, p) in self.feuilles.items() if p == parent and i not in self.corbeille]
    def lister_dossiers(self, parent): return [(i, n) for i, (n, p) in self.dossiers.items() if p == parent and i not in self.corbeille]
    def mettre_corbeille(self, i): self.corbeille.add(i)


class Corbeille(unittest.TestCase):
    def setUp(self): self.m = Monde(par=1)

    def test_corbeille_seulement_feuilles_lues(self):
        reg = RG.vide(); reg["feuilles_lues"].update({"Sid|2026-11-05": "2026-11-17", "Liam|2026-11-05": "2026-11-17", "Sid|2026-11-16": "2026-11-17"}); RG.sauver(reg)
        d = FauxDrive(); d.feuilles = {"a": ("Appels 2026-11-05", "SID"), "b": ("Appels 2026-11-06", "SID"), "c": ("Appels 2026-11-16", "SID"), "e": ("Budget 2026-11-01", "SID"),
                                       "f": ("Appels Liam 2026-11-05", "root"), "g": ("Appels Liam 2026-11-06", "root")}
        d.dossiers = {"h": ("2026-10-01", "SID")}
        n = muet(A.nettoyer_feuilles_lues, RG.SID, "SID", "2026-11-17", d, False, True) + muet(A.nettoyer_feuilles_lues, RG.LIAM, "root", "2026-11-17", d, False, True)
        self.assertEqual(d.corbeille, {"a", "f"}, "plus de 7 jours ET déjà lue : corbeille ; jamais non lue, récente, autre fichier ni dossier"); self.assertEqual(n, 2)
        self.assertEqual(muet(A.nettoyer_feuilles_lues, RG.SID, "SID", "2026-11-17", d, False, False), 0, "simulation : rien")

    def test_aucun_dossier_cree(self):
        src = (C.AGENTS / "appels-liam.py").read_text(encoding="utf-8") + (C.AGENTS / "registre.py").read_text(encoding="utf-8")
        self.assertNotIn("creer_dossier", src); self.assertNotIn(".delete(", src)


class DriveSid:
    """Faux dossier de Sid : feuilles « Appels Sid AAAA-MM-JJ » modifiables après coup, lecture seule pour l'agent."""
    def __init__(self): self.f = {}
    def poser(self, jour, texte): self.f[f"F{jour}"] = (f"Appels Sid {jour}", texte)
    def lister_feuilles(self, parent): return [(i, n) for i, (n, _) in self.f.items()] + [("X", "Budget 2026-11-16")]
    def lire_feuille_csv(self, i): return self.f[i][1]


class Relecture(unittest.TestCase):
    """Cas réel du 17/11/2026 : Sid note ses appels du jour dans la feuille de la VEILLE, déjà lue à 7 h 30 (cases vides à ce moment-là)."""
    def setUp(self):
        self.m = Monde(par=1); self.alertes = []; self.av = A.alerter_discord
        A.alerter_discord = lambda t: self.alertes.append(t) or True
    def tearDown(self): A.alerter_discord = self.av

    def csv_drive(self, f, resultats):
        lignes = self.m.lire(f)
        for l in lignes[1:]:
            if l[NOM] in resultats: l[RES], l[NOTE] = resultats[l[NOM]]
        return "\n".join(",".join('"' + c.replace('"', '""') + '"' for c in l) for l in lignes)

    def sid(self, jour, drive, envoi=True):
        conf = A.cfg(); conf["envoi_automatique"] = envoi; conf["alerte_leads_envoi"] = envoi; conf["dossier_sid_id"] = "DSID"; etat = A.etat_lire()
        return muet(A.preparer_registre, RG.SID, conf, etat, jour, False, drive, hors_ligne=True)

    def test_feuille_de_la_veille_relue(self):
        d = DriveSid(); muet(self.m.sid, "2026-11-17"); f17 = A.chemin("2026-11-17"); corps = self.m.lire(f17)[1:]
        chaud, refl, non, rdv, pdr = (corps[i][NOM] for i in range(5))
        d.poser("2026-11-17", self.csv_drive(f17, {}))
        self.sid("2026-11-18", d)                     # 18/11 7 h 30 : feuille du 17 lue, tout est vide -> tout revient en tête
        f18 = A.chemin("2026-11-18"); self.assertTrue({chaud, non} <= {l[NOM] for l in self.m.lire(f18)[1:]}, "situation du 17/11 reproduite")
        d.poser("2026-11-18", self.csv_drive(f18, {}))
        d.poser("2026-11-17", self.csv_drive(f17, {chaud: ("À rappeler", "intéressée, rappeler quand dispo"), refl: ("Je dois réfléchir", "voir associé"),
                                                   non: ("Non catégorique", "a déjà ses clients"), rdv: ("RDV pris", "jeudi"), pdr: ("Pas de réponse", "")}))
        self.sid("2026-11-19", d)                     # 19/11 : relecture des 3 dernières feuilles, dont celle du 17 déjà lue
        n19 = {l[NOM] for l in self.m.lire(A.chemin("2026-11-19"))[1:]}
        self.assertFalse({chaud, refl, non, rdv} & n19, "Non catégorique, RDV pris, À rappeler, Je dois réfléchir : retirés de la liste de Sid")
        self.assertEqual(len(self.alertes), 2, "une alerte Discord par lead chaud")
        self.assertTrue(any(chaud in t and "À rappeler" in t and "rappeler quand dispo" in t for t in self.alertes), "entreprise et Note dans l'alerte")
        x = {v["nom"]: v for v in RG.charger()["entreprises"].values()}
        self.assertEqual(x[pdr]["essais"], 1); self.assertEqual(x[non]["statut"], "terminée"); self.assertEqual(x[chaud]["pour"], RG.LIAM)
        d.poser("2026-11-19", self.csv_drive(A.chemin("2026-11-19"), {}))
        self.sid("2026-11-20", d)
        self.assertEqual(len(self.alertes), 2, "jamais deux fois la même alerte")
        x = {v["nom"]: v for v in RG.charger()["entreprises"].values()}
        self.assertEqual(x[pdr]["essais"], 1, "Pas de réponse relu plusieurs fois : compté une seule fois")
        self.assertNotIn(non, {l[NOM] for l in self.m.lire(A.chemin("2026-11-20"))[1:]}, "case vide d'une feuille plus récente : Non catégorique ne revient jamais")

    def test_simulation_rien_envoye(self):
        d = DriveSid(); muet(self.m.sid, "2026-11-17"); f17 = A.chemin("2026-11-17"); chaud = self.m.lire(f17)[1][NOM]
        d.poser("2026-11-17", self.csv_drive(f17, {chaud: ("À rappeler", "")}))
        self.sid("2026-11-18", d, envoi=False)
        self.assertEqual(self.alertes, [], "simulation : aucun Discord")
        self.assertFalse(any(v.get("alerte_lead") for v in RG.charger()["entreprises"].values()), "rien marqué : l'alerte partira une fois l'envoi activé")
        self.assertNotIn(chaud, (A.JOURNAL.read_text(encoding="utf-8") if A.JOURNAL.exists() else ""), "jamais de nom d'entreprise dans le journal")


class Fin(unittest.TestCase):
    def test_vrai_registre_intact(self):
        self.assertEqual(VRAI_REGISTRE.stat().st_mtime_ns if VRAI_REGISTRE.exists() else None, AVANT_VRAI, "le vrai registre n'est jamais touché par les tests")


if __name__ == "__main__":
    unittest.main(verbosity=1)
