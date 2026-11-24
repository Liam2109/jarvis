#!/usr/bin/env python3
"""Harness - chiffres-serveur : feuille Google factice, sans réseau ni Stripe réel. Vérifie le verrou « go chiffres-serveur », le format de la ligne (3 colonnes, date ISO,
deux comptes), la création de la feuille avec son seul en-tête, une seule ligne par jour, le mode --essai (feuille de TEST uniquement, rien d'écrit en local, la vraie feuille
jamais touchée), la simulation (envoi_automatique=false), un chiffre indisponible (aucune ligne), et qu'aucun montant ni donnée client n'entre dans la feuille."""
import io, json, tempfile, unittest
from contextlib import redirect_stdout
from pathlib import Path
import commun as C

A = C.agent("chiffres-serveur")
JOUR = "2026-11-21"


class FauxDrive:
    """Drive en mémoire : seules les 4 méthodes utilisées par l'agent. `appels` garde la trace de chaque feuille touchée."""
    def __init__(self, feuilles=None):
        self.f = dict(feuilles or {})      # {titre: [lignes]}
        self.appels = []

    def _id(self, titre): return "id-" + titre

    def trouver_feuille(self, dossier, titre):
        assert dossier is None, "la feuille est cherchée à la racine du Drive"
        self.appels.append(("chercher", titre))
        return self._id(titre) if titre in self.f else None

    def creer_feuille(self, dossier, titre, contenu_csv):
        assert dossier is None
        self.appels.append(("creer", titre))
        self.f[titre] = [l.split(",") for l in contenu_csv.strip().split("\n")]
        return self._id(titre)

    def lire_feuille_csv(self, id_):
        titre = id_[3:]
        return "\n".join(",".join(c for c in l) for l in self.f[titre]) + "\n"

    def ajouter_lignes(self, id_, lignes):
        titre = id_[3:]
        self.appels.append(("ajouter", titre))
        self.f[titre] += [[str(c) for c in l] for l in lignes]
        return len(lignes)

    def titres_touches(self): return {t for _, t in self.appels}


class ChiffresServeur(unittest.TestCase):
    def setUp(self):
        tmp = Path(tempfile.mkdtemp())
        A.ETAT, A.JOURNAL, A.DEVIS_ETAT = tmp / "etat.json", tmp / "journal.log", tmp / "devis-etat.json"
        A.garde_ok = lambda t: True      # la garde est testée par test_garde.py ; ici on ne veut aucune trace parasite
        A.paiements_recus = lambda jour: (True, 1)
        self.conf = {**A.DEFAUT, "go_chiffres_serveur": True, "envoi_automatique": True}
        self.drive = FauxDrive()

    def passer(self, jour=JOUR, essai=False, attendu=0):
        with redirect_stdout(io.StringIO()) as s:
            code = A.cmd_jour(self.conf, jour, essai, self.drive)
        self.assertEqual(code, attendu, s.getvalue())
        return s.getvalue()

    def devis(self, *jours):
        """devis-etat.json factice : un devis marqué « envoyé » par jour donné (plus un devis seulement préparé, qui ne compte pas)."""
        d = {f"DEV-{i}": {"statut": "envoyé", "historique": {"préparé": j, "envoyé": j}, "entreprise": "Envog Coiffure", "prix": 500} for i, j in enumerate(jours)}
        d["DEV-prepare"] = {"statut": "préparé", "historique": {"préparé": JOUR}, "entreprise": "Garage du Rond Point", "prix": 500}
        A.DEVIS_ETAT.write_text(json.dumps({"devis": d}, ensure_ascii=False), encoding="utf-8")

    def lignes(self, titre=None): return self.drive.f[titre or self.conf["feuille"]]

    # --- verrou ---------------------------------------------------------------------------------------------------
    def test_verrou_ferme_rien_ecrit(self):
        self.conf["go_chiffres_serveur"] = False
        self.devis(JOUR)
        s = self.passer()
        self.assertIn("go chiffres-serveur", s)
        self.assertEqual(self.drive.f, {}, "aucune feuille créée ni touchée tant que le verrou est fermé")
        self.assertFalse(A.ETAT.exists())

    def test_essai_marche_verrou_ferme_et_ne_touche_que_la_feuille_de_test(self):
        self.conf["go_chiffres_serveur"] = False
        self.devis(JOUR)
        s = self.passer(essai=True)
        self.assertIn("[essai]", s)
        self.assertEqual(self.drive.titres_touches(), {self.conf["feuille_essai"]}, "la vraie feuille n'est jamais touchée en essai")
        self.assertNotIn(self.conf["feuille"], self.drive.f)
        self.assertEqual(self.lignes(self.conf["feuille_essai"])[-1], [JOUR, "1", "1"])
        self.assertFalse(A.ETAT.exists(), "--essai n'écrit ni état"); self.assertFalse(A.JOURNAL.exists(), "ni journal")

    # --- format et contenu de la feuille --------------------------------------------------------------------------
    def test_creation_de_la_feuille_puis_une_ligne(self):
        self.devis(JOUR, JOUR)
        self.passer()
        self.assertEqual(self.lignes()[0], A.ENTETE, "ligne 1 = en-tête, rien d'autre")
        self.assertEqual(self.lignes()[1], [JOUR, "2", "1"])
        self.assertEqual(len(self.lignes()), 2)
        self.assertIn(("creer", self.conf["feuille"]), self.drive.appels)

    def test_trois_colonnes_seulement_sans_montant_ni_donnee_client(self):
        self.devis(JOUR)
        self.passer()
        texte = "\n".join(",".join(l) for l in self.lignes())
        self.assertEqual(A.ENTETE, ["Date", "Devis envoyés", "Paiements reçus"])
        for l in self.lignes(): self.assertEqual(len(l), 3, l)
        for interdit in ("500", "€", "Envog", "Garage", "@", "02 35"):
            self.assertNotIn(interdit, texte, f"« {interdit} » ne doit jamais entrer dans la feuille")

    def test_seuls_les_devis_envoyes_du_jour_comptent(self):
        self.devis("2026-11-20", JOUR, JOUR, "2026-11-22")
        self.passer()
        self.assertEqual(self.lignes()[-1], [JOUR, "2", "1"], "ni la veille, ni le lendemain, ni un devis seulement préparé")

    def test_sans_devis_etat_zero_devis(self):
        self.passer()
        self.assertEqual(self.lignes()[-1], [JOUR, "0", "1"], "aucun devis préparé sur cette machine = 0, jamais « inconnu »")

    # --- une seule ligne par jour ---------------------------------------------------------------------------------
    def test_pas_de_doublon_le_meme_jour(self):
        self.devis(JOUR)
        self.passer(); self.passer()
        self.assertEqual(len(self.lignes()), 2, "deuxième passage le même jour : aucune ligne ajoutée")

    def test_pas_de_doublon_meme_si_l_etat_local_est_perdu(self):
        self.devis(JOUR)
        self.passer()
        A.ETAT.unlink()
        self.passer()
        self.assertEqual(len(self.lignes()), 2, "la feuille elle-même dit que le jour est déjà écrit")

    def test_un_jour_par_soir_s_empile(self):
        self.devis("2026-11-20", JOUR)
        self.passer("2026-11-20"); self.passer(JOUR)
        self.assertEqual([l[0] for l in self.lignes()], ["Date", "2026-11-20", JOUR])
        self.assertEqual(sorted(json.loads(A.ETAT.read_text(encoding="utf-8"))["jours"]), ["2026-11-20", JOUR])

    # --- chiffre indisponible, simulation, format relu -------------------------------------------------------------
    def test_paiements_indisponibles_aucune_ligne(self):
        A.paiements_recus = lambda jour: (False, "clé Stripe absente de Jarvis\\.env")
        self.devis(JOUR)
        s = self.passer(attendu=2)
        self.assertIn("aucune ligne écrite", s)
        self.assertEqual(self.drive.f, {}, "jamais de chiffre inventé, jamais de ligne partielle")

    def test_devis_etat_illisible_aucune_ligne(self):
        A.DEVIS_ETAT.write_text("{ cassé", encoding="utf-8")
        self.passer(attendu=2)
        self.assertEqual(self.drive.f, {})

    def test_simulation_rien_dans_google(self):
        self.conf["envoi_automatique"] = False
        self.devis(JOUR)
        s = self.passer()
        self.assertIn("simulation", s)
        self.assertEqual(self.drive.f, {})
        self.assertFalse(A.ETAT.exists(), "rien n'est marqué écrit en simulation")

    def test_format_relu_different_signale(self):
        self.devis(JOUR)
        self.drive.ajouter_lignes = lambda id_, lignes: self.drive.f.__getitem__(id_[3:]).append(["bricolé"]) or 1
        s = self.passer(attendu=2)
        self.assertIn("format inattendu", s)

    def test_google_indisponible_rien_ecrit(self):
        def casse(*a, **k): raise OSError("réseau")
        self.drive.trouver_feuille = casse
        self.devis(JOUR)
        s = self.passer(attendu=2)
        self.assertIn("inaccessible", s)
        self.assertFalse(A.ETAT.exists())

    def test_jour_mal_forme_refuse(self):
        with self.assertRaises(A.ErreurAgent):
            with redirect_stdout(io.StringIO()): A.cmd_jour(self.conf, "21/11/2026", False, self.drive)

    # --- fonctions pures ------------------------------------------------------------------------------------------
    def test_jours_ecrits_et_derniere_ligne(self):
        csv = "Date,Devis envoyés,Paiements reçus\n2026-11-20,0,0\n2026-11-21,2,1\n"
        self.assertEqual(A.jours_ecrits(csv), {"2026-11-20", "2026-11-21"})
        self.assertEqual(A.derniere_ligne(csv), ["2026-11-21", "2", "1"])
        self.assertEqual(A.jours_ecrits("Date,Devis envoyés,Paiements reçus\n"), set(), "feuille neuve : aucun jour")
        self.assertTrue(A.format_ok(["2026-11-21", "2", "1"], ["2026-11-21", "2", "1"]))
        self.assertFalse(A.format_ok(["2026-11-21", "2"], ["2026-11-21", "2", "1"]))

    def test_config_par_defaut_verrouillee(self):
        c = json.loads((C.AGENTS / "chiffres-serveur-config.json").read_text(encoding="utf-8-sig"))
        self.assertIs(c["go_chiffres_serveur"], False); self.assertIs(c["envoi_automatique"], False)
        self.assertNotIn("compte_google", c, "aucun identifiant de compte dans un fichier versionné")
        self.assertNotEqual(c["feuille"], c["feuille_essai"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
