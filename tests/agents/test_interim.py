#!/usr/bin/env python3
"""Harness - interim : faux Gmail (aucun réseau), aucun Discord réel. Offre de nuit gardée avec agence / lieu / horaires / lien ; Suisse, alternance, SNCF et CACES exigé écartés ;
un mail n'est résumé qu'une fois ; verrou « go interim » ; rappel du lundi (Adéquat chaque semaine, documents Samsic manquants) ; noter sans éditer le fichier ; --essai n'écrit rien ;
aucun document n'est lu (le suivi ne contient que oui/non)."""
import io, json, tempfile, unittest
from contextlib import redirect_stdout
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
import commun as C

I = C.agent("interim")
G = C.harness("garde")
CTX = {"machine_active": True, "envoi_automatique": True, "stop": False, "deja_envoyes": 0}
CONF = json.loads((C.AGENTS / "interim-config.json").read_text(encoding="utf-8"))


def mail(exp, sujet, corps, html=False):
    m = EmailMessage(); m["From"] = exp; m["Subject"] = sujet
    m.set_content(corps, subtype="html" if html else "plain"); return m.as_bytes()


MAILS = {
    "a": mail("Adecco <alertes@adecco.fr>", "Opérateur de production H/F - nuit", "Poste de nuit en 3x8 à Saint-Étienne-du-Rouvray. Postuler : https://www.adecco.fr/offre/123 Se désabonner : https://www.adecco.fr/unsubscribe"),
    "b": mail("Randstad <noreply@randstad.fr>", "Opérateur Genève", "Mission à Genève (Suisse) https://randstad.fr/x"),
    "c": mail("Manpower <alerte@manpower.fr>", "Cariste", "CACES 3 obligatoire, Rouen https://manpower.fr/y"),
    "d": mail("Hellowork <a@hellowork.com>", "Opérateur en alternance", "Contrat en alternance à Rouen"),
    "e": mail("Indeed <a@indeed.com>", "Conducteur de train SNCF", "SNCF recrute à Rouen"),
    "f": mail("Pub <promo@exemple.test>", "Super promo", "rien à voir"),
    "g": mail("Samsic <rouen@samsic-emploi.fr>", "Demande de justificatif", "<p>Merci de déposer vos justificatifs dans Mes documents : <a href=\"https://candidat.samsic-emploi.fr/docs\">espace</a></p>", html=True),
    "h": mail("Crit <a@crit-job.com>", "Agent de production agro", "Le Grand-Quevilly, horaires en 2x8, CACES apprécié mais non obligatoire https://crit-job.com/z"),
}


class FauxGmail:
    def __init__(self): self.lus = []
    def ids(self, requete, maxi=60): return list(MAILS)
    def brut(self, i): self.lus.append(i); return MAILS[i]


class Interim(unittest.TestCase):
    def setUp(self):
        tmp = Path(tempfile.mkdtemp()); I.ETAT, I.JOURNAL, I.SUIVI = tmp / "etat.json", tmp / "journal.log", tmp / "suivi.csv"
        self.envois = []; I.alerter_discord = lambda t: self.envois.append(t) or True
        self.n = datetime(2026, 11, 23, 9, 5); I.maintenant = lambda: self.n   # lundi 23/11/2026, 09:05
        self.conf = {**I.DEFAUT, **{k: v for k, v in CONF.items() if not k.startswith("_")}, "go_interim": True, "envoi_automatique": True}

    def taire(self, f, *a):
        with redirect_stdout(io.StringIO()) as s: code = f(*a)
        return code, s.getvalue()

    def test_matin_garde_et_ecarte(self):
        g = FauxGmail(); self.assertEqual(self.taire(I.cmd_matin, self.conf, False, g)[0], 0)
        self.assertEqual(len(self.envois), 1); m = self.envois[0]
        self.assertIn("Opérateur de production H/F - nuit — Adecco — Saint Etienne Du Rouvray — horaires : nuit, 3x8", m)
        self.assertIn("https://www.adecco.fr/offre/123", m); self.assertNotIn("unsubscribe", m)
        self.assertIn("Agent de production agro — Crit — Le Grand Quevilly — horaires : 2x8", m)
        self.assertIn("Demande de justificatif", m); self.assertIn("à faire toi-même", m); self.assertIn("https://candidat.samsic-emploi.fr/docs", m)
        for x in ("Genève", "Cariste", "alternance", "SNCF", "Super promo"): self.assertNotIn(x, m.split("Écartées")[0])
        self.assertIn("Écartées : 1 CACES exigé, 1 SNCF / train, 1 alternance, 1 expéditeur hors liste, 1 hors région.", m)
        ok, r = G.verifier_envoi("interim", "discord", m, maintenant=G.heure_paris(), ctx=CTX, tracer=False); self.assertTrue(ok, r)

    def test_un_mail_une_seule_fois(self):
        self.taire(I.cmd_matin, self.conf, False, FauxGmail()); self.taire(I.cmd_matin, self.conf, False, FauxGmail())
        self.assertEqual(len(self.envois), 1)

    def test_rien_n_est_invente(self):
        o = I.analyser("Adecco <a@adecco.fr>", "Opérateur", "Mission sans autre détail", CONF["domaines"])
        self.assertEqual((o["lieu"], o["horaires"], o["lien"]), ("non indiqué", "non indiqués", "aucun lien"))

    def test_verrou_go_interim(self):
        self.conf["go_interim"] = False
        self.assertEqual(self.taire(I.cmd_passage, self.conf, False, FauxGmail())[0], 0)
        self.assertEqual(self.envois, []); self.assertFalse(I.ETAT.exists())

    def test_essai_n_ecrit_rien(self):
        self.conf["go_interim"] = False
        code, sortie = self.taire(I.cmd_passage, self.conf, True, FauxGmail())
        self.assertEqual(code, 0); self.assertIn("[essai]", sortie); self.assertEqual(self.envois, [])
        for f in (I.ETAT, I.JOURNAL, I.SUIVI): self.assertFalse(f.exists(), f.name)

    def test_passage_lundi_matin_et_semaine_une_fois(self):
        self.taire(I.cmd_passage, self.conf, False, FauxGmail()); self.assertEqual(len(self.envois), 2)
        s = self.envois[1]
        self.assertIn("Adéquat Rouen", s); self.assertIn("appeler cette semaine", s)
        self.assertIn("documents à déposer toi-même : pièce d'identité, RIB", s)
        self.taire(I.cmd_passage, self.conf, False, FauxGmail()); self.assertEqual(len(self.envois), 2, "rien de plus le même jour")
        self.n = datetime(2026, 11, 24, 9, 5); self.taire(I.cmd_passage, self.conf, False, FauxGmail())
        self.assertEqual(len(self.envois), 2, "mardi : plus de mail nouveau, pas de rappel de semaine")

    def test_mardi_pas_de_rappel_semaine(self):
        self.n = datetime(2026, 11, 24, 9, 5); self.taire(I.cmd_passage, self.conf, False, FauxGmail())
        self.assertEqual(len(self.envois), 1)

    def test_avant_07_30_rien(self):
        self.n = datetime(2026, 11, 24, 6, 0); self.taire(I.cmd_passage, self.conf, False, FauxGmail()); self.assertEqual(self.envois, [])

    def test_noter(self):
        self.taire(I.cmd_noter, self.conf, "adequat", "appele", "", False)
        self.taire(I.cmd_noter, self.conf, "samsic", "document", "RIB", False)
        self.taire(I.cmd_noter, self.conf, "samsic", "inscrit", "", False)
        l = {x["agence"]: x for x in I.suivi_lire(self.conf)}
        self.assertEqual(l["Adéquat Rouen"]["dernier_appel"], "2026-11-23")
        self.assertIn("RIB=oui", l["Samsic Emploi Rouen Industrie/Tertiaire"]["documents_detail"])
        self.assertEqual(l["Samsic Emploi Rouen Industrie/Tertiaire"]["documents_deposes"], "partiel")
        self.assertEqual(l["Randstad Rouen"]["adresse_confirmee"], "non")

    def test_noter_ambigu_refuse(self):
        with self.assertRaises(I.ErreurAgent): I.cmd_noter(self.conf, "rouen", "appele", "", False)

    def test_liste_de_depart_sans_invention(self):
        for a in CONF["agences"]:
            self.assertTrue(a.get("source"), a["agence"])
            if a["confirmee"] != "non": self.assertTrue(a["source"].startswith("Liam") and "non confirmé" not in a["source"], a["agence"])
            if not a["adresse"]: self.assertIn("inconnue", a["note"], a["agence"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
