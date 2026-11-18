#!/usr/bin/env python3
"""Harness - relances : feuilles « Appels Sid » factices, sans réseau ni Discord réel. Cas de référence de Liam (18/11/2026) : Envog Coiffure (appel lundi 16/11) sort le jeudi 19/11
(relance 1) et le mercredi 25/11 (relance 2) ; Garage du Rond Point (« moyen terme ») une seule fois au 15e jour ouvré ; week-end sauté ; lead exclu par un RDV pris plus tard ;
pas de doublon si le script tourne deux fois le même jour ; jours fériés ; mode --essai sans écriture."""
import io, json, tempfile, unittest
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path
import commun as C

R = C.agent("relances")
G = C.harness("garde")
CTX = {"machine_active": True, "envoi_automatique": True, "stop": False, "deja_envoyes": 0}
ENTETE = "Créneau,Entreprise,Métier,Ville,Téléphone,Détail fiche,Résultat,Note"


def csv_(*lignes): return "\n".join([ENTETE] + [",".join(f'"{c}"' for c in l) for l in lignes])


ENVOG = ["09:00", "Envog Coiffure", "coiffeur", "Rouen", "02 35 11 22 33", "", "À rappeler", "rappeler après 17 h"]
GARAGE = ["10:00", "Garage du Rond Point", "garage", "Elbeuf", "06 11 22 33 44", "", "Je dois réfléchir", "projet à moyen terme"]
FLEUR = ["11:00", "Fleurs Test", "fleuriste", "Évreux", "+33 2 32 00 00 01", "", "Je dois réfléchir", ""]


class FauxDrive:
    def __init__(self, feuilles): self.f = feuilles   # {jour: csv}
    def lister_feuilles(self, racine): return [(j, f"Appels Sid {j}") for j in self.f] + [("autre", "Notes diverses")]
    def lire_feuille_csv(self, i): return self.f[i]


class Relances(unittest.TestCase):
    def setUp(self):
        tmp = Path(tempfile.mkdtemp()); R.ETAT, R.JOURNAL = tmp / "etat.json", tmp / "journal.log"
        self.envois = []; R.alerter_discord = lambda t: self.envois.append(t) or True
        self.conf = {**R.DEFAUT, "envoi_automatique": True, "dossier_sid_id": "dossier-factice"}
        self.drive = FauxDrive({"2026-11-16": csv_(ENVOG, GARAGE, FLEUR)})

    def passer(self, jour, essai=False):
        n = len(self.envois)
        with redirect_stdout(io.StringIO()): self.assertEqual(R.cmd_jour(self.conf, jour, essai, self.drive), 0)
        return self.envois[n:]

    def sorties(self, debut, fin, nom):
        """Jours (AAAA-MM-JJ) où le lead `nom` apparaît en passant chaque jour calendaire de debut à fin, avec le numéro de relance."""
        out, d = [], date.fromisoformat(debut)
        while d <= date.fromisoformat(fin):
            for m in self.passer(d.isoformat()):
                for l in m.split("\n"):
                    if nom in l: out.append((d.isoformat(), "relance 2" if "relance 2" in l else "relance 1"))
            d = d.fromordinal(d.toordinal() + 1)
        return out

    def test_envog_jeudi_19_puis_mercredi_25(self):
        self.assertEqual(self.sorties("2026-11-16", "2026-12-31", "Envog Coiffure"), [("2026-11-19", "relance 1"), ("2026-11-25", "relance 2")])

    def test_garage_moyen_terme_une_seule_fois_au_15e(self):
        self.assertEqual(R.ouvre_apres(date(2026, 11, 16), 15), date(2026, 12, 7))
        self.assertEqual(self.sorties("2026-11-16", "2027-01-31", "Garage du Rond Point"), [("2026-12-07", "relance 1")])

    def test_week_end_saute(self):
        self.assertEqual(R.ouvre_apres(date(2026, 11, 19), 3), date(2026, 11, 24), "jeudi + 3 jours ouvrés = mardi (samedi et dimanche sautés)")
        self.assertEqual(self.passer("2026-11-21"), []); self.assertEqual(self.passer("2026-11-22"), [])

    def test_jours_feries(self):
        self.assertEqual(R.paques(2026), date(2026, 4, 5)); self.assertIn(date(2026, 11, 11), R.feries(2026)); self.assertIn(date(2026, 5, 14), R.feries(2026))   # Ascension
        self.assertEqual(R.ouvre_apres(date(2026, 11, 9), 3), date(2026, 11, 13), "le 11 novembre ne compte pas")
        self.assertFalse(R.est_ouvre(date(2026, 12, 25)))

    def test_exclu_par_rdv_pris_plus_tard(self):
        rdv = list(ENVOG); rdv[6] = "RDV pris"
        self.drive.f["2026-11-18"] = csv_(rdv)
        m = self.passer("2026-11-19")[0]
        self.assertIn("Fleurs Test", m); self.assertNotIn("Envog Coiffure", m, "RDV pris le 18/11 : Envog n'est plus relancé")
        self.assertEqual(self.sorties("2026-11-20", "2026-12-31", "Envog Coiffure"), [])

    def test_pas_de_reponse_plus_tard_n_exclut_pas(self):
        pr = list(ENVOG); pr[6] = "Pas de réponse"; self.drive.f["2026-11-18"] = csv_(pr)
        self.assertEqual(self.sorties("2026-11-16", "2026-11-19", "Envog Coiffure"), [("2026-11-19", "relance 1")])

    def test_pas_de_doublon_le_meme_jour(self):
        m = self.passer("2026-11-19"); self.assertEqual(len(m), 1, "un seul message")
        self.assertIn("Envog Coiffure", m[0]); self.assertIn("Fleurs Test", m[0]); self.assertNotIn("Garage du Rond Point", m[0])
        self.assertEqual(self.passer("2026-11-19"), [], "deuxième passage le même jour : aucun message")

    def test_contenu_du_message(self):
        m = self.passer("2026-11-19")[0]
        for x in ("À rappeler aujourd'hui", "Envog Coiffure (Rouen)", "02 35 11 22 33", "relance 1", "note de Sid : rappeler après 17 h", "02 32 00 00 01"):
            self.assertIn(x, m)
        ok, r = G.verifier_envoi("relances", "discord", m, maintenant=G.heure_paris(), ctx=CTX, tracer=False); self.assertTrue(ok, r)

    def test_aucun_message_s_il_n_y_a_rien(self):
        self.assertEqual(self.passer("2026-11-17"), []); self.assertEqual(self.passer("2026-11-18"), [])

    def test_essai_n_ecrit_ni_n_envoie(self):
        self.assertEqual(self.passer("2026-11-19", essai=True), []); self.assertFalse(R.ETAT.exists()); self.assertFalse(R.JOURNAL.exists())
        self.assertEqual(len(self.passer("2026-11-19")), 1, "après un essai, le vrai passage annonce bien")

    def test_simulation_rien_sur_discord(self):
        self.conf["envoi_automatique"] = False
        self.assertEqual(self.passer("2026-11-19"), []); self.assertEqual(len(json.loads(R.ETAT.read_text(encoding="utf-8"))["annonces"]), 2)

    def test_passage_manque_rattrape_sans_relance_1_tardive(self):
        self.assertEqual(self.sorties("2026-11-25", "2026-12-31", "Envog Coiffure"), [("2026-11-25", "relance 2")])

    def test_nouvel_appel_chaud_relance_le_cycle(self):
        self.passer("2026-11-19"); self.passer("2026-11-25")
        self.drive.f["2026-11-30"] = csv_(ENVOG)
        self.assertEqual(self.sorties("2026-11-30", "2026-12-04", "Envog Coiffure"), [("2026-12-03", "relance 1")])


if __name__ == "__main__":
    unittest.main(verbosity=1)
