#!/usr/bin/env python3
"""Harness - alerte-candidatures : test à blanc sur une feuille factice, sans réseau ni Discord réel. Une nouvelle ligne = exactement une alerte, un deuxième passage = aucune,
la relance de 2 h se déclenche une seule fois ; verrou « go alerte » ; seul l'en-tête « Contacté » est écrit ; rien n'est inventé ; la garde laisse passer le message."""
import io, json, tempfile, unittest
from contextlib import redirect_stdout
from pathlib import Path
import commun as C

S = C.agent("alerte-candidatures")
G = C.harness("garde")
CTX = {"machine_active": True, "envoi_automatique": True, "stop": False, "deja_envoyes": 0}
ENTETE = ["Horodateur", "Prénom et nom", "Numéro de téléphone", "Adresse e-mail", "Ville", "Vos disponibilités", "Un message pour Liam ?"]
ANCIEN = ["17/11/2026 08:00:00", "Ancien Candidat", "0600000000", "ancien@exemple.test", "Lyon", "", ""]
NOUVEAU = ["17/11/2026 10:00:00", "Camille Test", "0611223344", "camille@exemple.test", "Nantes", "Soirs", "Motivé"]


class FausseFeuille:
    def __init__(self, lignes): self.lignes = [list(l) for l in lignes]; self.ecritures = []
    def lire(self): return [list(l) for l in self.lignes]
    def ecrire_entete(self, col, texte):
        self.ecritures.append((col, texte)); e = self.lignes[0]
        while len(e) <= col: e.append("")
        e[col] = texte


def conf(**k): return {**S.DEFAUT, "go_alerte": True, "envoi_automatique": True, "feuille_id": "feuille-factice", **k}


class AlerteCandidatures(unittest.TestCase):
    def setUp(self):
        tmp = Path(tempfile.mkdtemp()); S.ETAT, S.JOURNAL = tmp / "etat.json", tmp / "journal.log"
        self.envois = []; S.alerter_discord = lambda t: self.envois.append(t) or True
        self.t = 1_800_000_000; S.maintenant = lambda: self.t
        self.f = FausseFeuille([ENTETE, ANCIEN])

    def passage(self, c=None):
        with redirect_stdout(io.StringIO()): return S.cmd_verifier(c or conf(), False, self.f)

    def test_verrou_go_alerte(self):
        self.assertEqual(self.passage(conf(go_alerte=False)), 0)
        self.assertEqual((self.envois, self.f.ecritures, S.ETAT.exists()), ([], [], False), "verrou fermé : rien lu, rien écrit, rien envoyé")

    def test_une_ligne_une_alerte_puis_relance_unique(self):
        self.passage()   # premier passage : l'existant est mémorisé sans alerte, l'en-tête Contacté est créé
        self.assertEqual(self.envois, []); self.assertEqual(self.f.ecritures, [(len(ENTETE), "Contacté")])
        self.f.lignes.append(NOUVEAU + [""])
        self.passage(); self.assertEqual(len(self.envois), 1, "une nouvelle ligne = exactement une alerte")
        a = self.envois[0]
        for x in ("À rappeler dans l'heure", "Camille Test", "0611223344", "camille@exemple.test", "Nantes", "Soirs", "Motivé", "15 %", "15 minutes en visio"):
            self.assertIn(x, a)
        self.assertNotIn("Bonjour", a); self.assertNotIn("Ancien Candidat", a)
        self.passage(); self.assertEqual(len(self.envois), 1, "deuxième passage : aucune alerte")
        self.t += 119 * 60; self.passage(); self.assertEqual(len(self.envois), 1, "pas de relance avant 2 h")
        self.t += 2 * 60; self.passage(); self.assertEqual(len(self.envois), 2); self.assertIn("Relance candidature : Camille Test", self.envois[1])
        self.t += 3600; self.passage(); self.assertEqual(len(self.envois), 2, "une seule relance")
        self.assertEqual(len(self.f.ecritures), 1, "seul l'en-tête Contacté a été écrit")
        self.assertEqual(S.compte_jour(S.datetime.fromtimestamp(self.t).date().isoformat()), (1, 1))

    def test_contacte_pas_de_relance(self):
        self.passage(); self.f.lignes.append(NOUVEAU + [""]); self.passage()
        self.f.lignes[-1][-1] = "oui"; self.t += 3 * 3600; self.passage()
        self.assertEqual(len(self.envois), 1, "cocher Contacté : ni relance ni nouvelle alerte")
        self.assertEqual(S.compte_jour(S.datetime.fromtimestamp(self.t).date().isoformat()), (1, 0))

    def test_rien_invente(self):
        cols = S.colonnes(["Horodateur", "Prénom", "Téléphone"], "Contacté")
        m = S.message_alerte(["17/11/2026 11:00:00", "Sam", ""], cols)
        self.assertIn("Nom : Sam", m)
        for x in ("Téléphone :", "E-mail :", "Ville :", "Disponibilités :", "Message :"): self.assertNotIn(x, m)

    def test_simulation_rien_sur_discord(self):
        self.passage(conf(envoi_automatique=False)); self.f.lignes.append(NOUVEAU + [""]); self.passage(conf(envoi_automatique=False))
        self.assertEqual(self.envois, [])

    def test_a_blanc_n_ecrit_rien(self):
        with redirect_stdout(io.StringIO()): S.cmd_verifier(conf(), True, self.f)
        self.assertEqual((self.envois, self.f.ecritures, S.ETAT.exists()), ([], [], False))

    def test_ligne_du_resume_du_soir(self):
        R = C.agent("resume-sid"); R.CANDIDATURES_ETAT = S.ETAT; jour = S.datetime.fromtimestamp(self.t).date().isoformat()
        self.assertIsNone(R.candidatures_jour(jour), "verrou fermé : pas de ligne")
        self.assertNotIn("Candidatures", R.message_resume(jour, False, "x", False, "y", R.candidatures_jour(jour)))
        self.passage(); self.f.lignes.append(NOUVEAU + [""]); self.passage()
        self.assertIn("Candidatures call callers du jour : 1, dont 1 non contactée(s).", R.message_resume(jour, False, "x", False, "y", R.candidatures_jour(jour)))

    def test_garde_laisse_passer_l_alerte(self):
        m = S.message_alerte(NOUVEAU, S.colonnes(ENTETE, "Contacté"))
        ok, r = G.verifier_envoi("alerte-candidatures", "discord", m, maintenant=G.heure_paris(), ctx=CTX, tracer=False)
        self.assertTrue(ok, r)


if __name__ == "__main__":
    unittest.main(verbosity=1)
