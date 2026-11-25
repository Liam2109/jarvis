#!/usr/bin/env python3
"""Harness - linkedin-equipe : le lot du jour se génère (post, commentaires, demandes de connexion 70/30, plafonds), cibles filtrées (décideur, 1 à 9 personnes, zone, jamais contactées),
DM variés et conformes, suivi par cases (acceptation -> DM du jour, relance unique à J+3, réponse positive -> leads chauds), file.json de l'agent linkedin jamais modifié.
Silencieux : aucun réseau (recherche et modèle sont des doublures), aucun Discord, aucun fichier réel (états et tableau de bord dans des dossiers temporaires)."""
import json, shutil, tempfile, unittest
from pathlib import Path
import commun as C

E = C.agent("linkedin-equipe")
LI = E.LI
JOUR = "2026-11-24"   # mardi
ENT = "siren;nom;metier;adresse;cp;ville;creation;effectif;telephone;note;avis;site\n"
POST = ("Vous êtes artisan ou commerçant et vous n'avez pas de site web, ou un site qui date ? Sujet du jour : alpha.\n\n"
        "Je crée des sites web pour les artisans et les commerçants locaux : une page claire, qui présente votre activité, vos horaires et la façon de vous joindre. "
        "Le pack landing page est à 500 €, le site complet à 994 €, puis 29 € par mois avec l'hébergement, la maintenance et le support.\n\n"
        "Je préfère vous expliquer par téléphone ce qui vous conviendrait. Écrivez-moi en message privé.")
HTML = "".join(f'<a rel="nofollow" class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Ffr.linkedin.com%2Fposts%2Fpersonne{i}-activite-{i}&rut=x">Post numéro {i} sur les artisans</a>' for i in range(40))


def ligne(i, metier="plombier-chauffagiste", cp="76000", ville="ROUEN", eff="01", nom=None, an="2020"):
    return f"{900000 + i};{nom or f'ENTREPRISE{i} SERVICES'};{metier};1 RUE X {cp} {ville};{cp};{ville};{an}-01-01;{eff};;;;\n"


class Base(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp(prefix="le-test-"))
        self.old = (E.SOURCES, E.SUIVI, E.ETAT, E.SORTIE, LI.DOSSIER, LI.FILE)
        E.SOURCES = {"rouen": self.t / "rouen.csv", "large": self.t / "large.csv", "trouves": self.t / "trouves.csv"}; E.SUIVI = self.t / "suivi.csv"
        E.ETAT = self.t / "equipe.json"; E.SORTIE = self.t / "data"
        LI.DOSSIER = self.t / "linkedin"; LI.DOSSIER.mkdir(); LI.FILE = lambda: LI.DOSSIER / "file.json"
        (LI.DOSSIER / "lot-2026-11-23.md").write_text("# lot\n\n## Post 1\ntype: prospect\nstatut: en file\ntexte:\n" + POST + "\n\n## Post 2\ntype: prospect\ntexte:\n" + POST.replace("alpha", "bravo") + "\n", encoding="utf-8")
        E.RG.FICHIER = self.t / "registre.json"
        self.conf = E.cfg(); self.conf["commentaires"] = 10; self.conf["go_linkedin_auto"] = False   # jamais dépendre du vrai réglage du serveur
        (self.t / "rouen.csv").write_text(ENT + "".join(ligne(i) for i in range(1, 200)), encoding="utf-8-sig")
        (self.t / "large.csv").write_text(ENT, encoding="utf-8-sig"); (self.t / "trouves.csv").write_text("nom;metier;ville;cp;linkedin\n", encoding="utf-8-sig")
        E.SUIVI.write_text("nom;ville;statut;date_envoi\n", encoding="utf-8-sig")

    def tearDown(self):
        E.SOURCES, E.SUIVI, E.ETAT, E.SORTIE, LI.DOSSIER, LI.FILE = self.old; shutil.rmtree(self.t, ignore_errors=True)

    def jour(self, jour=JOUR, **kw):
        kw.setdefault("http", lambda url: HTML); kw.setdefault("modele", lambda titre: "Merci pour ce partage, un sujet utile pour les artisans de la région."); kw.setdefault("dormir", lambda s: None)
        return E.cmd_jour(self.conf, jour, **kw)

    def etat(self): return json.loads(E.ETAT.read_text(encoding="utf-8"))
    def sortie(self): return json.loads((E.SORTIE / "linkedin.json").read_text(encoding="utf-8"))


class TestLot(Base):
    def test_lot_complet(self):
        self.assertEqual(self.jour(), 0); s = self.sortie()
        self.assertEqual(len(s["demandes"]), 20); self.assertEqual(sum(1 for d in s["demandes"] if d["type"] == "entreprise"), 14); self.assertEqual(sum(1 for d in s["demandes"] if d["type"] == "closer"), 6)
        self.assertEqual(len(s["commentaires"]), 10); self.assertIn("alpha", s["post"]["texte"])
        for d in s["demandes"]: self.assertTrue(d["lien"].startswith("https://www.linkedin.com/search/results/people/?keywords=")); self.assertTrue(d["dm"])
        self.assertTrue(all(c["url"].startswith("https://fr.linkedin.com/posts/") for c in s["commentaires"]))
        self.assertNotIn("posts/personne", json.dumps([d["lien"] for d in s["demandes"]]))   # les liens de recherche ne pointent jamais vers un profil scrapé

    def test_une_seule_fois_par_jour_et_jamais_le_week_end(self):
        self.jour(); avant = self.etat(); self.jour(); self.assertEqual(avant["jours"][JOUR]["demandes"], self.etat()["jours"][JOUR]["demandes"])
        self.assertEqual(self.jour("2026-11-28"), 0); self.assertNotIn("2026-11-28", self.etat()["jours"])

    def test_file_des_posts_jamais_modifiee(self):
        self.jour(); self.assertFalse((LI.DOSSIER / "file.json").exists())   # l'agent linkedin n'est ni activé ni modifié
        self.jour("2026-11-25"); self.assertIn("bravo", self.sortie()["post"]["texte"])
        self.assertEqual(self.jour("2026-11-26"), 5)   # plus de post en stock : code 5 (le surveillant le signale), le reste du lot est quand même fait
        self.assertIsNone(self.sortie()["post"]); self.assertEqual(len(self.sortie()["demandes"]), 20)

    def test_plafond_hebdomadaire_et_report(self):
        self.conf["plafond_semaine"] = 30; self.jour()
        e = self.etat()
        for i in e["jours"][JOUR]["demandes"][:15]: E.cmd_coche(self.conf, i, "demande_envoyee", JOUR)
        self.jour("2026-11-25"); s = self.sortie()
        self.assertEqual(len(s["demandes"]), 15)   # 30 - 15 envoyées ; les 5 non envoyées de la veille sont reportées d'abord, puis du neuf
        self.assertEqual(sum(1 for d in s["demandes"] if d["prevu_le"] == JOUR), 5)
        for i in [d["id"] for d in s["demandes"]][:15]: E.cmd_coche(self.conf, i, "demande_envoyee", "2026-11-25")
        e = self.etat(); e["cibles"]["zzzz"] = {"id": "zzzz", "type": "entreprise", "nom": "X"}   # une cible neuve : le 31e envoi de la semaine est refusé
        with self.assertRaises(E.ErreurAgent): E.appliquer(e, "zzzz", "demande_envoyee", "2026-11-25", self.conf)
        self.jour("2026-11-26"); self.assertEqual(self.sortie()["demandes"], []); self.assertIn("plafond", " ".join(self.sortie()["notes"]))
        self.jour("2026-11-30"); self.assertEqual(len(self.sortie()["demandes"]), 20)   # nouvelle semaine : le plafond repart

    def test_reglages_modifiables(self):
        self.conf.update(demandes_par_jour=10, part_entreprises=0.5); self.jour(); s = self.sortie()
        self.assertEqual((len(s["demandes"]), sum(1 for d in s["demandes"] if d["type"] == "entreprise")), (10, 5))


class TestCibles(Base):
    def test_filtres_decideur_effectif_zone_contactes(self):
        (self.t / "rouen.csv").write_text(ENT + ligne(1, nom="JULIEN RUPALLEY (JR PLOMBERIE)") + ligne(2, eff="12") + ligne(3, cp="75001", ville="PARIS") + ligne(4, cp="27000", ville="EVREUX")
                                          + ligne(5, nom="DEJA CONTACTEE") + ligne(6, nom="REGISTRE ENTREPRISE") + ligne(7, metier="restaurant"), encoding="utf-8-sig")
        E.SUIVI.write_text("nom;ville;statut;date_envoi\nDEJA CONTACTEE;ROUEN;envoyé;2026-11-01\n", encoding="utf-8-sig")
        reg = E.RG.vide(); E.RG.donner(reg, {"nom": "REGISTRE ENTREPRISE", "ville": "ROUEN", "tel": "", "metier": "plombier"}, "Sid", JOUR); E.RG.sauver(reg)
        noms = [c["nom"] for c in E.candidats(self.conf)]
        self.assertEqual(noms[0], "Julien Rupalley")   # dirigeant connu d'abord
        self.assertTrue(all("Deja Contactee" not in x and "Registre" not in x and "Entreprise2" not in x for x in noms))   # trop grande (12), contactée, déjà appelée
        self.assertEqual(sum(1 for c in E.candidats(self.conf) if c["niveau"] == 0), 1 + 0)   # zone_niveau 1 trie Seine-Maritime d'abord ; Eure ensuite
        self.assertNotIn("Paris", [c["ville"] for c in E.candidats(self.conf)]); self.assertTrue(all(c["bat"] for c in E.candidats(self.conf)))   # commerces exclus par défaut

    def test_elargissement_progressif(self):
        (self.t / "rouen.csv").write_text(ENT + ligne(1) + ligne(2, cp="27000", ville="EVREUX"), encoding="utf-8-sig")
        e = E.etat_lire(); self.assertEqual([c["ville"] for c in E.cibles_entreprises(self.conf, e, 1)], ["Rouen"])
        self.assertEqual(sorted(c["ville"] for c in E.cibles_entreprises(self.conf, e, 2)), ["Evreux", "Rouen"])   # niveau épuisé : le suivant est utilisé
        self.conf["commerces_locaux"] = True; (self.t / "trouves.csv").write_text("nom;metier;ville;cp;linkedin\nBoulangerie Dupont;boulangerie;Rouen;76000;\n", encoding="utf-8-sig")
        self.assertIn("Boulangerie Dupont", [c["nom"] for c in E.candidats(self.conf)])

    def test_closers_jamais_deux_fois_la_meme_recherche(self):
        e = E.etat_lire(); a = E.cibles_closers(self.conf, e, 30)
        self.assertEqual(len({c["id"] for c in a}), 30); self.assertTrue(all(c["lien"].startswith("https://www.linkedin.com/search/results/people/") for c in a))
        for c in a: e["cibles"][c["id"]] = c
        self.assertFalse({c["id"] for c in E.cibles_closers(self.conf, e, 30)} & {c["id"] for c in a})


class TestMessages(Base):
    def test_dm_conformes_et_tous_differents(self):
        self.conf["demandes_par_jour"] = 200; self.conf["plafond_semaine"] = 1000; self.jour(); dms = [c["dm"] for c in self.etat()["cibles"].values()]
        self.assertEqual(len(dms), len(set(dms)), "deux DM identiques")
        for t in dms:
            self.assertEqual(E.controle_message(t, 420), [], t); self.assertNotRegex(t, r"(?i)^bonjour")
        self.assertGreater(len({t.split(".")[0] for t in dms}), 3)   # ouvertures variées, pas de motif unique

    def test_controle_message_refuse(self):
        for mauvais in ("Bonjour, je te propose un site pour toi, ça t'intéresse vraiment ?", "Vous allez gagner beaucoup de clients garantis avec notre site, répondez vite.",
                        "Je peux passer vous voir sur place pour vous présenter mon site web.", "Écrivez à contact@exemple.fr pour votre site web, merci beaucoup.", "Avec 3 clients de plus par mois grâce au site web, vous serez ravi."):
            self.assertTrue(E.controle_message(mauvais), mauvais)

    def test_relance_unique_apres_3_jours(self):
        self.jour(); i = self.etat()["jours"][JOUR]["demandes"][0]
        for a in ("demande_envoyee", "accepte", "dm_envoye"): E.cmd_coche(self.conf, i, a, JOUR)
        E.cmd_coche(self.conf, i, "annuler", JOUR) if False else None
        E.exporter(self.etat(), self.conf, "2026-11-26"); self.assertEqual(self.sortie()["relances"], [])   # J+2 : trop tôt
        E.exporter(self.etat(), self.conf, "2026-11-27"); r = self.sortie()["relances"]; self.assertEqual([x["id"] for x in r], [i]); self.assertEqual(E.controle_message(r[0]["relance"], 420), [])
        E.cmd_coche(self.conf, i, "relance_envoyee", "2026-11-27"); E.exporter(self.etat(), self.conf, "2026-12-05"); self.assertEqual(self.sortie()["relances"], [])   # une seule relance


class TestSuivi(Base):
    def test_chaine_et_ordre(self):
        self.jour(); i = self.etat()["jours"][JOUR]["demandes"][0]
        with self.assertRaises(E.ErreurAgent): E.appliquer(self.etat(), i, "accepte", JOUR, self.conf)   # pas avant « demande envoyée »
        E.cmd_coche(self.conf, i, "demande_envoyee", JOUR); self.assertEqual(self.sortie()["dms"], [])
        E.cmd_coche(self.conf, i, "accepte", JOUR); self.assertEqual([x["id"] for x in self.sortie()["dms"]], [i]); self.assertTrue(self.sortie()["dms"][0]["dm"])   # l'acceptation génère le DM du jour
        E.cmd_coche(self.conf, i, "dm_envoye", JOUR); self.assertEqual(self.sortie()["dms"], []); self.assertEqual(self.sortie()["suivi"]["dm_envoyes"], 1)
        E.cmd_coche(self.conf, i, "annuler", JOUR); self.assertEqual(len(self.sortie()["dms"]), 1)   # une case cochée par erreur s'annule

    def test_reponse_positive_dans_les_leads_chauds(self):
        self.jour(); i = [c for c in self.etat()["jours"][JOUR]["demandes"] if self.etat()["cibles"][c]["type"] == "entreprise"][0]
        for a in ("demande_envoyee", "accepte", "dm_envoye", "repondu_positif"): E.cmd_coche(self.conf, i, a, JOUR)
        reg = E.RG.charger(); x = next(v for v in reg["entreprises"].values() if v["dernier_resultat"] == "À rappeler")
        self.assertIn("LinkedIn", x["note"]); self.assertEqual(self.sortie()["suivi"]["positives"], 1)
        import leads_chauds as LC; self.assertEqual(len(LC.courants(reg)), 1)   # même file que les leads chauds de Sid
        j = [c for c in self.etat()["jours"][JOUR]["demandes"] if c != i][0]
        for a in ("demande_envoyee", "accepte", "repondu_autre"): E.cmd_coche(self.conf, j, a, JOUR)
        self.assertEqual(len(E.RG.charger()["entreprises"]), 1)   # une réponse non positive n'entre pas dans les leads chauds

    def test_profil_introuvable_ecarte(self):
        self.jour(); i = self.etat()["jours"][JOUR]["demandes"][0]; E.cmd_coche(self.conf, i, "ignorer", JOUR); self.assertNotIn(i, [d["id"] for d in self.sortie()["demandes"]])


class TestCommentaires(Base):
    def test_gabarits_si_modele_absent_ou_non_conforme(self):
        self.jour(modele=lambda t: None); c = self.sortie()["commentaires"]
        self.assertEqual(len(c), 10); self.assertEqual(len({x["texte"] for x in c}), 10); self.assertTrue(all("gabarit" in x["source"] for x in c))
        for x in c: self.assertEqual(E.controle_message(x["texte"], 280, commentaire=True), [])
        self.setUp.__self__.tearDown(); self.setUp(); self.jour(modele=lambda t: "Contactez-moi pour un site web, mon offre est à 3 euros !"); self.assertTrue(all("gabarit" in x["source"] for x in self.sortie()["commentaires"]))

    def test_recherche_en_panne(self):
        def panne(url): raise OSError("réseau")
        self.assertEqual(self.jour(http=panne), 0); s = self.sortie(); self.assertEqual(s["commentaires"], []); self.assertEqual(len(s["demandes"]), 20)
        self.assertIn("0 commentaire", " ".join(s["notes"]))

    def test_aucun_acces_a_linkedin_pour_chercher(self):
        vus = []; self.jour(http=lambda u: (vus.append(u), HTML)[1]); self.assertTrue(vus and all(u.startswith("https://html.duckduckgo.com/") for u in vus))   # moteur de recherche public seulement


class TestExport(Base):
    def test_essai_ne_touche_rien(self):
        self.assertEqual(self.jour(essai=True), 0); self.assertFalse(E.ETAT.exists()); self.assertFalse((E.SORTIE / "linkedin.js").exists())

    def test_export_js_lisible_par_le_tableau_de_bord(self):
        self.jour(); t = (E.SORTIE / "linkedin.js").read_text(encoding="utf-8"); self.assertTrue(t.startswith("window.JARVIS_LINKEDIN = {")); self.assertTrue(t.rstrip().endswith("};"))


if __name__ == "__main__":
    unittest.main(verbosity=1)
