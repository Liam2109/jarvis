#!/usr/bin/env python3
"""Harness - sauvegarde-leads (24/11/2026) : sauvegarde nocturne, 30 jours de garde, archive restaurable, message de 08:00 « À rappeler aujourd'hui ».
Aucun réseau, aucun Discord, dossiers temporaires uniquement."""
import io, json, shutil, tempfile, unittest
from contextlib import redirect_stdout
from pathlib import Path
import commun as C

S = C.agent("sauvegarde-leads")
AR = C.agent("archive")
R = C.agent("relances")
RG = C.agent("registre")


def ecrire(p, d): p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")


class Sauvegarde(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sauvegarde-leads-test-")); self.b2b = self.tmp / "B2B"; self.dest = self.tmp / "sauvegardes"
        ecrire(self.b2b / "donnees" / "registre-entreprises.json", {"version": 1, "entreprises": {"a|rouen|0235000001": {"nom": "A"}}, "feuilles_lues": {}})
        ecrire(self.b2b / "donnees" / "leads-chauds.json", {"leads": {}, "alertes": {}})
        ecrire(self.b2b / "agents" / "relances-etat.json", {"annonces": {}})
        (self.b2b / "docs" / "sid").mkdir(parents=True); (self.b2b / "docs" / "sid" / "liste-sid-2026-11-24.csv").write_text("x", encoding="utf-8")
        self.reg, self.lead, self.arch = self.tmp / "reg.json", self.tmp / "lead.json", self.tmp / "archive.jsonl"
        ecrire(self.reg, {"version": 1, "entreprises": {"a|rouen|0235000001": {"nom": "Auto Dupont", "statut": "à reprendre"}}, "feuilles_lues": {}})
        ecrire(self.lead, {"leads": {"k": {"nom": "Lead K", "jour": "2026-11-20"}}, "alertes": {}})

    def tearDown(self): shutil.rmtree(self.tmp, ignore_errors=True)

    def test_copie_les_fichiers_et_garde_30_jours(self):
        for j in ("2026-10-01", "2026-10-25", "2026-10-26"): (self.dest / j).mkdir(parents=True)
        n, s = S.sauvegarder("2026-11-24", self.b2b, self.dest)
        self.assertEqual((n, s), (4, 1))   # seul 2026-10-01 a plus de 30 jours ; 10-25 (30 j pile) et 10-26 restent
        self.assertTrue((self.dest / "2026-11-24" / "donnees" / "registre-entreprises.json").is_file())
        self.assertTrue((self.dest / "2026-11-24" / "docs" / "sid" / "liste-sid-2026-11-24.csv").is_file())
        self.assertEqual(sorted(p.name for p in self.dest.iterdir()), ["2026-10-25", "2026-10-26", "2026-11-24"])

    def test_relance_le_meme_jour_remplace_et_a_blanc_ecrit_rien(self):
        S.sauvegarder("2026-11-24", self.b2b, self.dest, a_blanc=True); self.assertFalse(self.dest.exists())
        S.sauvegarder("2026-11-24", self.b2b, self.dest); ecrire(self.b2b / "agents" / "relances-etat.json", {"annonces": {"z": 1}})
        S.sauvegarder("2026-11-24", self.b2b, self.dest)
        self.assertIn('"z"', (self.dest / "2026-11-24" / "agents" / "relances-etat.json").read_text(encoding="utf-8"))
        self.assertEqual([p.name for p in self.dest.iterdir()], ["2026-11-24"])   # aucun .tmp laissé

    def test_sans_registre_echec_et_rien_supprime(self):
        (self.dest / "2026-09-01").mkdir(parents=True); (self.b2b / "donnees" / "registre-entreprises.json").unlink()
        with self.assertRaises(S.ErreurAgent): S.sauvegarder("2026-11-24", self.b2b, self.dest)
        self.assertTrue((self.dest / "2026-09-01").exists())

    def test_ne_supprime_que_des_dossiers_dates(self):
        (self.dest / "important").mkdir(parents=True); (self.dest / "2026-01-01").mkdir(); (self.dest / "2026-01-02.txt").write_text("x")
        S.supprimer_anciennes("2026-11-24", self.dest)
        self.assertEqual(sorted(p.name for p in self.dest.iterdir()), ["2026-01-02.txt", "important"])

    def test_suppression_archivee_puis_restauree(self):
        i = AR.supprimer("registre", "a|rouen|0235000001", "test", self.arch, self.reg, self.lead)
        self.assertNotIn("a|rouen|0235000001", json.loads(self.reg.read_text(encoding="utf-8"))["entreprises"])
        self.assertEqual([l["id"] for l in AR.archives(self.arch)], [i])
        AR.restaurer(i, self.arch, self.reg, self.lead)
        self.assertEqual(json.loads(self.reg.read_text(encoding="utf-8"))["entreprises"]["a|rouen|0235000001"]["nom"], "Auto Dupont")
        self.assertEqual(AR.archives(self.arch), [])
        with self.assertRaises(AR.ErreurArchive): AR.restaurer(i, self.arch, self.reg, self.lead)   # déjà restauré

    def test_restaurer_n_ecrase_jamais(self):
        i = AR.supprimer("leads-chauds", "k", "test", self.arch, self.reg, self.lead)
        d = json.loads(self.lead.read_text(encoding="utf-8")); d["leads"]["k"] = {"nom": "Nouveau"}; ecrire(self.lead, d)
        with self.assertRaises(AR.ErreurArchive): AR.restaurer(i, self.arch, self.reg, self.lead)
        self.assertEqual(json.loads(self.lead.read_text(encoding="utf-8"))["leads"]["k"]["nom"], "Nouveau")
        with self.assertRaises(AR.ErreurArchive): AR.supprimer("registre", "inconnue", "x", self.arch, self.reg, self.lead)

    def test_liberer_et_sortie_de_file_archivent(self):
        import archive; archive.FICHIER = self.arch   # le module vu par registre et leads_chauds
        reg = RG.vide(); k = RG.donner(reg, {"nom": "Neuve", "ville": "Rouen", "tel": "0235000009"}, RG.SID, "2026-11-24", feuille="Sid|2026-11-24")
        RG.liberer(reg, "Sid|2026-11-24", "2026-11-24")
        self.assertNotIn(k, reg["entreprises"]); a = AR.archives(self.arch); self.assertEqual((len(a), a[0]["quoi"], a[0]["cle"]), (1, "registre", k))
        import leads_chauds as LC
        f = self.tmp / "file.json"; ecrire(f, {"leads": {"z": {"nom": "Z"}}, "alertes": {"z": "x"}, "version": 1})
        LC.synchroniser(RG.vide(), "2026-11-24", None, f, self.tmp / "suivi.csv")
        self.assertEqual({l["quoi"] for l in AR.archives(self.arch)}, {"registre", "leads-chauds"})


class Rappel(unittest.TestCase):
    FILE = [{"nom": "En retard", "ville": "Elbeuf", "tel": "0235000001", "jour": "2026-11-20", "resultat_le": "2026-11-16"},
            {"nom": "Aujourd'hui", "ville": "Rouen", "tel": "0235000002", "jour": "2026-11-24", "resultat_le": "2026-11-18"},
            {"nom": "Demain", "ville": "Rouen", "tel": "0235000003", "jour": "2026-11-25", "resultat_le": "2026-11-19"},
            {"nom": "Sans date", "tel": "0235000004", "jour": ""}]

    def test_dus_et_en_retard_seulement(self):
        dus = R.leads_dus_file("2026-11-24", lambda: self.FILE)
        self.assertEqual([x["nom"] for x in dus], ["En retard", "Aujourd'hui"])
        m = R.message_rappel(dus, "2026-11-24")
        self.assertIn("En retard", m); self.assertIn("en retard de 4 j", m); self.assertIn("dernière mise à jour le 16/11", m)
        self.assertIn("relance prévue aujourd'hui", m); self.assertNotIn("Demain", m); self.assertNotIn("Sans date", m)

    def test_envoi_week_end_et_rien(self):
        envois = []; R.alerter_discord = lambda t: envois.append(t) or True
        conf = {**R.DEFAUT, "envoi_automatique": True}
        with redirect_stdout(io.StringIO()):
            self.assertEqual(R.cmd_rappel(conf, "2026-11-24", False, lambda: self.FILE), 0)
            self.assertEqual(R.cmd_rappel(conf, "2026-11-28", False, lambda: self.FILE), 0)   # samedi
            self.assertEqual(R.cmd_rappel(conf, "2026-11-24", False, lambda: [self.FILE[2]]), 0)   # rien de dû
            self.assertEqual(R.cmd_rappel({**conf, "envoi_automatique": False}, "2026-11-24", True, lambda: self.FILE), 0)   # essai : rien envoyé
        self.assertEqual(len(envois), 1)


if __name__ == "__main__": unittest.main()
