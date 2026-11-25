#!/usr/bin/env python3
"""Harness - linkedin-equipe, mode automatique : fermé par défaut, un seul geste par passage, quota 20 dès le premier jour, plafond 100 par semaine), DM avec prix et jamais identiques, relance unique,
réponse négative = exclusion, arrêt d'urgence + alerte Discord à tout avertissement de LinkedIn (aucun contournement), kill-switch, journal des envois. LinkedIn est SIMULÉ : aucun réseau, aucune fenêtre."""
import json, sys, unittest
from datetime import datetime, timedelta
from pathlib import Path
import commun as C
from test_linkedin_equipe import Base, E, LI, JOUR

LA = E.LA


class Auto(Base):
    def setUp(self):
        super().setUp()
        self.vieux = LA.f_stop_global; LA.f_stop_global = lambda: self.t / "STOP"
        self.conf.update({"go_linkedin_auto": True}); self.nav = LA.Simule(); self.alertes = []; self.fabr = 0
        self.t0 = datetime.fromisoformat(JOUR + "T08:00:00")

    def tearDown(self):
        LA.f_stop_global = self.vieux; super().tearDown()

    def tick(self, now, nav=None):
        self.fabr = 0; self.nav = nav or self.nav; courant = self.nav
        def fab(c): self.fabr += 1; return courant
        return LA.tick(self.conf, now.date().isoformat(), now, fabrique=fab, alerter=lambda t: self.alertes.append(t) or True, dormir=lambda s: None)

    def preparer(self, jour=JOUR):
        self.jour(jour, modele=lambda t: None); e = self.etat()
        for i in e["jours"][jour]["demandes"]:
            c = e["cibles"][i]
            if c["type"] == "entreprise": self.nav.resultats[c["lien"]] = [{"nom": c["dirigeant"] or "Gérant " + i, "texte": "Gérant " + (c["entreprise"] or c["nom"]), "profil": "https://www.linkedin.com/in/" + i, "bouton": True}]
            elif c["type"] == "closer": self.nav.resultats[c["lien"]] = [{"nom": "Closer " + i, "texte": "", "profil": "https://www.linkedin.com/in/c" + i, "bouton": True}]
        return e

    def passages(self, n, debut=None, pas=15):
        now = debut or self.t0
        for k in range(n): self.assertEqual(self.tick(now + timedelta(minutes=pas * k)), 0)

    def envoyes(self, t): return [x for x in self.nav.envoyes if x[0] == t]


class TestAuto(Auto):
    def test_ferme_par_defaut_aucun_navigateur(self):
        self.conf["go_linkedin_auto"] = False; self.assertEqual(self.tick(self.t0), 0); self.assertEqual(self.fabr, 0); self.assertEqual(self.nav.envoyes, [])
        self.assertIs(E.DEFAUT["go_linkedin_auto"], False)

    def test_hors_plage_week_end_et_ecart(self):
        self.preparer(); self.assertEqual(self.tick(self.t0.replace(hour=7, minute=30)), 0); self.assertEqual(self.tick(self.t0.replace(hour=18, minute=5)), 0)
        self.assertEqual(self.tick(datetime.fromisoformat("2026-11-28T09:00:00")), 0); self.assertEqual(self.fabr, 0)
        self.tick(self.t0); n = len(self.nav.envoyes); self.tick(self.t0 + timedelta(minutes=3)); self.assertEqual(len(self.nav.envoyes), n)   # moins de 7 minutes : rien

    def test_une_action_par_passage_post_d_abord(self):
        self.preparer(); self.tick(self.t0); self.assertEqual([x[0] for x in self.nav.envoyes], ["post"]); self.assertIn("alpha", self.nav.envoyes[0][2])
        self.tick(self.t0 + timedelta(minutes=15)); self.assertEqual(len(self.envoyes("post")), 1); self.assertEqual(len(self.envoyes("demande")), 1)

    def test_quota_20_des_le_premier_jour_sans_jamais_depasser_le_plafond(self):
        self.preparer(); self.passages(40, pas=15)   # 08:00 à 18:00
        self.assertEqual(len(self.envoyes("demande")), 20)   # 20 dès le premier jour, pas de montée progressive
        self.conf["plafond_semaine"] = 25; self.preparer("2026-11-25"); self.passages(40, debut=datetime.fromisoformat("2026-11-25T08:00:00"))
        self.assertEqual(len(self.envoyes("demande")), 25)   # plafond strict de la semaine
        self.conf["plafond_semaine"] = 100; self.preparer("2026-11-30"); self.nav.envoyes.clear(); self.passages(40, debut=datetime.fromisoformat("2026-11-30T08:00:00"))
        self.assertEqual(len(self.envoyes("demande")), 20)   # nouvelle semaine : 20

    def test_repartition_sur_la_journee(self):
        self.preparer()
        for k in range(4): self.tick(self.t0 + timedelta(minutes=15 * k))
        self.assertLessEqual(len(self.envoyes("demande")), 2)   # pas de rafale à l'ouverture

    def test_profil_ambigu_ecarte(self):
        e = self.preparer(); c = next(c for c in e["cibles"].values() if c["type"] == "entreprise")
        self.nav.resultats[c["lien"]] = [{"nom": "Quelqu'un d'autre", "texte": "x", "profil": "https://www.linkedin.com/in/zz", "bouton": True}]
        e["jours"][JOUR]["demandes"].remove(c["id"]); e["jours"][JOUR]["demandes"].insert(0, c["id"]); E.etat_ecrire(e)
        self.passages(3); self.assertTrue(self.etat()["cibles"][c["id"]].get("ignore")); self.assertFalse([x for x in self.envoyes("demande") if "zz" in x[1]])

    def accepter(self, n=3):
        self.preparer(); self.passages(14); e = self.etat()
        ent = [c for c in e["cibles"].values() if c.get("demande_envoyee_le") and c["type"] == "entreprise"][:n]
        self.assertGreaterEqual(len(ent), 1); self.nav.connexions = [c["nom_profil"] for c in ent]
        e["auto"]["derniere_verif"] = (self.t0 - timedelta(hours=2)).isoformat(); E.etat_ecrire(e); return ent

    def test_dm_avec_prix_jamais_identique_puis_relance_unique(self):
        ent = self.accepter(); self.nav.envoyes.clear(); self.passages(6, debut=self.t0 + timedelta(hours=4)); dms = self.envoyes("dm")
        self.assertEqual(len(dms), len(ent)); self.assertEqual(len({d[2] for d in dms}), len(dms))   # jamais deux textes identiques
        for d in dms: self.assertIn("29 €", d[2]); self.assertIn("500 €", d[2]); self.assertEqual(LA.verifier_texte(d[2]), []); self.assertFalse(d[2].lower().startswith("bonjour"))
        e = self.etat(); self.assertTrue(all(e["cibles"][c["id"]]["dm_envoye_le"] == JOUR for c in ent))
        jr = "2026-11-27"; self.preparer(jr); self.nav.envoyes.clear(); self.nav.connexions = []
        self.passages(6, debut=datetime.fromisoformat(jr + "T08:00:00")); rel = self.envoyes("dm"); self.assertEqual(len(rel), len(ent))   # relance à J+3
        self.assertTrue(all("relance" in self.etat()["cibles"][c["id"]] for c in ent)); self.nav.envoyes.clear()
        self.passages(8, debut=datetime.fromisoformat(jr + "T11:00:00")); self.assertEqual(self.envoyes("dm"), [])   # une seule relance par personne

    def test_reponses_positive_vers_leads_chauds_negative_exclut(self):
        ent = self.accepter(2); self.passages(6, debut=self.t0 + timedelta(hours=4))
        self.nav.conversations = [{"nom": ent[0]["nom_profil"], "dernier": "Oui, appelez-moi demain", "de_moi": False}, {"nom": ent[1]["nom_profil"], "dernier": "STOP, ne m'écrivez plus", "de_moi": False}] if len(ent) > 1 else \
            [{"nom": ent[0]["nom_profil"], "dernier": "STOP", "de_moi": False}]
        e = self.etat(); e["auto"]["derniere_verif"] = (self.t0 - timedelta(hours=2)).isoformat(); E.etat_ecrire(e)
        self.assertEqual(self.tick(self.t0 + timedelta(hours=8)), 0); e = self.etat()
        if len(ent) > 1: self.assertEqual(e["cibles"][ent[0]["id"]]["reponse"], "positive"); self.assertTrue(e["cibles"][ent[0]["id"]].get("lead_chaud"))
        neg = ent[-1]["id"]; self.assertEqual(e["cibles"][neg]["reponse"], "negative"); self.assertTrue(e["cibles"][neg]["ignore"])
        self.assertEqual(LA.classer_reponse("Non merci"), "negative"); self.assertEqual(LA.classer_reponse("Combien ça coûte ?"), "positive"); self.assertEqual(LA.classer_reponse("Bonne journée"), "autre")

    def test_commentaires_quota_bas_sans_doublon(self):
        self.preparer(); self.passages(40); com = self.envoyes("commentaire"); self.assertEqual(len(com), 3); self.assertEqual(len({x[2] for x in com}), 3)

    def test_journal_des_envois(self):
        self.preparer(); self.passages(4); l = [json.loads(x) for x in LA.f_envois().read_text(encoding="utf-8").splitlines()]
        self.assertEqual(l[0]["type"], "post"); self.assertTrue(all(x["texte"] and x["le"] for x in l)); self.assertEqual(len(l), len(self.nav.envoyes))


class TestFile(Auto):
    def test_auto_sans_closers_et_commerces_inclus(self):
        (self.t / "trouves.csv").write_text("nom;metier;ville;cp;linkedin;site_actuel;statut\nSalon Belle;coiffeur;ROUEN;76000;;;listé\nResto Avec Site;restaurant;ROUEN;76000;;http://x.fr;listé\nResto Exclu;restaurant;ROUEN;76000;;;exclu\n", encoding="utf-8-sig")
        self.preparer(); e = self.etat(); self.assertEqual({c["type"] for c in e["cibles"].values()}, {"entreprise"})   # jamais d'appelants/closers
        noms = [c["nom"] for c in E.candidats(self.conf)]; self.assertIn("Salon Belle", noms); self.assertNotIn("Resto Exclu", noms)
        self.assertLess(noms.index("Salon Belle"), noms.index("Resto Avec Site"))   # sans site d'abord

    def test_la_file_se_remplit_seule_sans_doublon_quand_les_cibles_sont_introuvables(self):
        self.jour(modele=lambda t: None)   # aucun résultat de recherche programmé : toutes les cibles du lot sont introuvables
        for k in range(60): self.tick(self.t0 + timedelta(minutes=15 * k % 600))
        e = self.etat(); ids = list(e["cibles"]); self.assertEqual(len(ids), len(set(ids))); self.assertGreater(len(ids), 20)   # des cibles neuves ont été ajoutées
        self.assertLessEqual(e["auto"].get("ajoutees", 0), 60); self.assertEqual(self.envoyes("demande"), [])   # introuvable = écarté, jamais de hasard

    def test_apercu_n_ecrit_rien_et_n_envoie_rien(self):
        self.preparer(); avant = E.ETAT.read_text(encoding="utf-8")
        import io, contextlib; buf = io.StringIO()
        with contextlib.redirect_stdout(buf): LA.apercu(self.conf, self.etat(), JOUR)
        self.assertEqual(E.ETAT.read_text(encoding="utf-8"), avant); self.assertEqual(self.nav.envoyes, []); self.assertIn("SANS note", buf.getvalue()); self.assertIn("500 €", buf.getvalue())


class TestResume(Auto):
    def test_resume_du_soir_une_fois_lu_dans_le_journal(self):
        self.preparer(); self.passages(4)
        LA.envoi_journal("acceptee", "x", "Nom", "(demande acceptée)"); LA.envoi_journal("reponse", "x", "Nom", "(réponse reçue)")
        auj = datetime.now().date().isoformat(); t = LA.texte_resume(auj); self.assertIn("1 acceptées", t); self.assertIn("1 réponses", t); self.assertIn("1 posts", t); self.assertIn("AUTO-STOP : non", t)
        envoyes = []; al = lambda m: envoyes.append(m) or True
        self.assertFalse(LA.resume(self.conf, JOUR, datetime.fromisoformat(JOUR + "T18:04:00"), al)); self.assertEqual(envoyes, [])
        self.assertTrue(LA.resume(self.conf, JOUR, datetime.fromisoformat(JOUR + "T18:05:00"), al)); self.assertEqual(len(envoyes), 1)
        self.assertFalse(LA.resume(self.conf, JOUR, datetime.fromisoformat(JOUR + "T18:15:00"), al)); self.assertEqual(len(envoyes), 1)
        LA.f_arret().write_text("x", encoding="utf-8"); self.assertIn("AUTO-STOP actif", LA.texte_resume(auj))


class TestGardeFous(Auto):
    def alerte_apres_un_envoi(self, url, texte):
        self.preparer(); self.tick(self.t0); self.nav.alerte = (url, texte)
        self.assertEqual(self.tick(self.t0 + timedelta(minutes=15)), 6)

    def test_chaque_avertissement_arrete_tout_et_alerte_une_seule_fois(self):
        for url, texte in (("https://www.linkedin.com/checkpoint/challenge/x", ""), ("https://www.linkedin.com/feed/", "Vérification de sécurité : prouvez que vous n'êtes pas un robot"),
                           ("https://www.linkedin.com/feed/", "Vous avez atteint la limite hebdomadaire d'invitations"), ("https://www.linkedin.com/feed/", "Votre compte a été temporairement restreint"),
                           ("https://www.linkedin.com/feed/", "Veuillez résoudre ce CAPTCHA"), ("https://www.linkedin.com/login", "Se connecter à LinkedIn"), ("https://www.linkedin.com/feed/", "Avertissement")):
            with self.subTest(texte=texte or url):
                if LA.f_arret().exists(): LA.reprendre()
                self.alertes.clear(); self.nav = LA.Simule(); self.alerte_apres_un_envoi(url, texte)
                self.assertTrue(LA.f_arret().exists()); self.assertEqual(len(self.alertes), 1); self.assertTrue(self.nav.ferme)
                for k in (2, 3): self.assertEqual(self.tick(self.t0 + timedelta(minutes=15 * k)), 6)   # plus aucun passage ne lance le navigateur
                self.assertEqual(len(self.alertes), 1); self.assertEqual(self.fabr, 0)

    def test_reprise_par_liam_seulement(self):
        self.alerte_apres_un_envoi("https://www.linkedin.com/checkpoint/x", ""); self.assertEqual(LA.reprendre(), 0); self.assertFalse(LA.f_arret().exists())
        self.nav.alerte = None; self.nav.url = "https://www.linkedin.com/feed/"; self.assertEqual(self.tick(self.t0 + timedelta(hours=1)), 0)

    def test_page_inattendue_arrete_aussi(self):
        self.preparer(); self.tick(self.t0); self.nav.panne = "demander"; self.assertEqual(self.tick(self.t0 + timedelta(minutes=15)), 6)
        self.assertEqual(len(self.alertes), 1); self.assertIn("inattendue", self.alertes[0])

    def test_kill_switch(self):
        self.preparer(); (self.t / "STOP").write_text("x"); self.assertEqual(self.tick(self.t0), 0); self.assertEqual(self.fabr, 0); self.assertEqual(self.nav.envoyes, [])

    def test_aucun_identifiant_ni_dissimulation_dans_le_code(self):
        src = Path(LA.__file__).read_text(encoding="utf-8")
        for mot in ("add_cookies", "storage_state", "li_at", "navigator.webdriver", "stealth", "user_agent", "getpass"): self.assertNotIn(mot, src, mot)

    def test_playwright_jamais_importe_en_test(self):
        self.assertNotIn("playwright", sys.modules)


if __name__ == "__main__":
    unittest.main(verbosity=1)
