#!/usr/bin/env python3
"""Harness - alertes de panne : un agent en panne alerte une seule fois par jour (rendez-vous) ; le surveillant voit « erreur » et « n'a pas tourné », se tait si tout va bien,
dit « harness OK » le lundi matin. Sans réseau, sans Discord."""
import io, json, tempfile, unittest
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
import commun as C

R = C.agent("rendez-vous")
SV = C.harness("surveillant")
T = C.harness("traces")
CONTRAT = {"nom": "agent-test", "statut": "actif", "jours": [0, 1, 2, 3, 4], "alerte_si_silence": "07:45"}


class PanneAlerte(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()); R.ETAT, R.JOURNAL = self.tmp / "etat.json", self.tmp / "journal.log"

    def test_une_alerte_par_motif_et_par_jour(self):
        envoyes = []; etat = {"alertes": {}}
        for _ in range(3): R.alerter(etat, "arret|lecture", "agenda illisible", envoyes.append, "2026-11-17")
        R.alerter(etat, "arret|lecture", "agenda illisible", envoyes.append, "2026-11-18")
        self.assertEqual(len(envoyes), 2)

    def test_arret_suspend_et_alerte(self):
        envoyes = []; etat = {"alertes": {}}
        with redirect_stdout(io.StringIO()): r = R._arret(etat, "lecture", "HTTP 404", envoyes.append, "2026-11-17", False, R._fin(False))
        self.assertEqual(r["action"], "arrêt"); self.assertEqual(etat["suspendu"]["raison"], "lecture"); self.assertEqual(len(envoyes), 1)
        self.assertIn("reprendre", envoyes[0])

    def test_surveillant_erreur_et_silence(self):
        d = self.tmp / "logs"; n = datetime(2026, 11, 17, 19, 45)
        self.assertEqual(SV.defauts(n, [CONTRAT], d)[0], ["agent agent-test n'a pas tourné aujourd'hui (attendu avant 07:45)"])
        (d / "agent-test").mkdir(parents=True)
        (d / "agent-test" / "2026-11-17.jsonl").write_text(json.dumps({"heure": "2026-11-17T07:30:00", "decision": "jour", "resultat": "échec", "ok": False, "erreur": "code 2"}) + "\n", encoding="utf-8")
        l, _ = SV.defauts(n, [CONTRAT], d); self.assertEqual(len(l), 1); self.assertIn("erreur (code 2", l[0])
        (d / "agent-test" / "2026-11-17.jsonl").write_text(json.dumps({"heure": "2026-11-17T07:30:00", "decision": "jour", "resultat": "terminé", "ok": True}) + "\n", encoding="utf-8")
        l, k = SV.defauts(n, [CONTRAT], d); self.assertEqual(l, []); self.assertEqual(SV.message(n, l, k), "")

    def test_surveillant_lundi_et_jour_off(self):
        self.assertEqual(SV.message(datetime(2026, 11, 16, 7, 50), [], 5), "**Harness** : harness OK, 5 agents")
        self.assertEqual(SV.defauts(datetime(2026, 11, 21, 19, 45), [CONTRAT], self.tmp / "vide")[0], [], "samedi : agent hors jours, pas d'alerte")

    def test_surveillant_simulation_n_envoie_rien(self):
        envoyes = []
        with redirect_stdout(io.StringIO()): SV.cmd_verifier(True, datetime(2026, 11, 17, 19, 45), envoyer=envoyes.append)
        self.assertEqual(envoyes, [])


if __name__ == "__main__":
    unittest.main(verbosity=1)
