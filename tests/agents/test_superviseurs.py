#!/usr/bin/env python3
"""Harness - superviseurs de domaine (21/11/2026, Vidéos le 22/11) : les cinq superviseurs (Vente, Prospection, Sites, Mail, Vidéos) et la vue Jarvis, sur des cas SIMULÉS
dans un dossier temporaire. Aucun réseau, aucun Discord, aucun agent lancé (la relance est une doublure), aucun vrai fichier de données touché.

Trois familles de cas, pour chaque domaine : un agent planté ou silencieux (il doit être relancé UNE fois, pas deux) ; un doublon ou une clé manquante
(corrigé tout seul, sans rien perdre) ; un cas risqué (argent, suppression, donnée à choisir, lecture seule perdue) qui doit ALERTER sans rien toucher.
Plus : le verrou « go superviseurs » fermé (rien n'est corrigé), le mode --essai (rien n'est écrit), la garde du harness sur le message, et la fiche B2B\\a-valider."""
import io, json, os, shutil, tempfile, unittest
from contextlib import redirect_stdout
from datetime import date, datetime
from pathlib import Path
import commun as C

V = C.agent("superviseur-vente")
P = C.agent("superviseur-prospection")
ST = C.agent("superviseur-sites")
ML = C.agent("superviseur-mail")
VD = C.agent("superviseur-videos")
JV = C.agent("jarvis-vue")
S = V.S                      # le moteur commun, partagé par les six scripts
G = C.harness("garde")
LUNDI = datetime(2026, 11, 23, 10, 0)      # lundi 23/11/2026 à 10 h, dans la plage d'envoi (07:00-22:00)
JOUR = f"{LUNDI:%Y-%m-%d}"
CTX_GARDE = {"machine_active": True, "envoi_automatique": True, "stop": False, "deja_envoyes": 0}


def conf(**kw):
    c = dict(S.DEFAUT); c.update({"go_superviseurs": True, "envoi_automatique": True}); c.update(kw); return c


class Base(unittest.TestCase):
    """Chaque test travaille dans un dossier temporaire : l'état, le journal, la fiche a-valider et les fichiers de données y sont écrits, jamais dans B2B."""

    AGENT = DOMAINE = ""
    SUIVIS = []
    TACHES = {}

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="superviseurs-test-"))
        self.traces = self.tmp / "traces"
        self.envois, self.relances = [], []
        self.ancien = {"AGENTS": S.AGENTS, "A_VALIDER": S.A_VALIDER, "taches": S.taches, "actifs": S.agents_actifs}
        S.AGENTS = self.tmp
        S.A_VALIDER = self.tmp / "a-valider"
        S.taches = lambda: dict(self.TACHES)
        S.agents_actifs = lambda: set(self.TACHES)      # doublure : les reglages propres a la machine ne decident pas du resultat des tests
        self.addCleanup(self.ranger)

    def ranger(self):
        S.AGENTS, S.A_VALIDER, S.taches = self.ancien["AGENTS"], self.ancien["A_VALIDER"], self.ancien["taches"]
        S.agents_actifs = self.ancien["actifs"]
        shutil.rmtree(self.tmp, ignore_errors=True)

    # --- outils ---------------------------------------------------------------------------------------------------
    def trace(self, agent, ok=True, heure="07:31", erreur=None, decision="jour"):
        d = self.traces / agent; d.mkdir(parents=True, exist_ok=True)
        ligne = {"heure": f"{JOUR}T{heure}:00", "decision": decision, "resultat": "terminé" if ok else "erreur", "duree_s": 1.0, "ok": ok}
        if erreur: ligne["erreur"] = erreur
        with (d / f"{JOUR}.jsonl").open("a", encoding="utf-8") as f: f.write(json.dumps(ligne, ensure_ascii=False) + "\n")

    def ecrire(self, nom, data):
        p = self.tmp / nom; p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8"); return p

    def lire(self, nom):
        return json.loads((self.tmp / nom).read_text(encoding="utf-8"))

    def passer(self, controles=None, essai=False, c=None, maintenant=None, etat=None):
        """Un passage du superviseur. -> (texte du résumé, soucis)."""
        faux_relance = lambda nom, ts=None: (self.relances.append(nom) or True, "relancé, code 0")
        tampon = io.StringIO()
        with redirect_stdout(tampon):
            _code, texte, soucis = S.passage(self.AGENT, self.DOMAINE, self.SUIVIS, controles if controles is not None else self.CONTROLES,
                                             c or conf(), essai, maintenant or LUNDI, dossier_traces=self.traces,
                                             relance=faux_relance, envoyer=lambda t: self.envois.append(t) or True, etat=etat)
        self.sortie = tampon.getvalue()
        return texte, soucis

    def bloques(self, soucis): return [s for s in soucis if s.risque]
    def corriges(self, soucis): return [s for s in soucis if s.corrige]


# =====================================================================================================================
class Vente(Base):
    AGENT, DOMAINE, SUIVIS = "superviseur-vente", "Vente", ["devis", "stripe-alerte"]
    TACHES = {"devis": {"script": "devis.py", "commandes": [["jour"]], "toutes_minutes": 3},
              "stripe-alerte": {"script": "stripe-alerte.py", "commandes": [["verifier"]], "toutes_minutes": 5}}

    def setUp(self):
        super().setUp()
        V.ICI, V.RACINE = self.tmp, self.tmp
        V.VENTES_JSON, V.A_VALIDER = self.tmp / "ventes.json", self.tmp / "a-valider"
        self.CONTROLES = V.CONTROLES
        self.trace("devis", heure="09:50"); self.trace("stripe-alerte", heure="09:50")      # par défaut : les deux agents cycliques viennent de tourner
        self.ecrire("devis-etat.json", {"devis": {}, "alertes": {}, "ok_utilises": []})
        self.ecrire("stripe-alerte-etat.json", {"dernier_ts": 0, "vus": {}})

    # --- agent planté ---------------------------------------------------------------------------------------------
    def test_agent_plante_relance_une_seule_fois(self):
        self.trace("devis", ok=False, heure="09:10", erreur="RuntimeError")
        texte, soucis = self.passer()
        self.assertEqual(self.relances, ["devis"], "l'agent en erreur est relancé une fois")
        self.assertIn("agent devis erreur", " ".join(s.change for s in self.corriges(soucis)))
        self.assertIn("corrigé", texte)
        texte2, soucis2 = self.passer()
        self.assertEqual(self.relances, ["devis"], "deuxième passage : jamais une deuxième relance le même jour")
        self.assertTrue(any("toujours erreur après une relance" in s.quoi for s in self.bloques(soucis2)), texte2)

    def test_agent_bloque_est_relance(self):
        shutil.rmtree(self.traces / "devis")      # agent cyclique (toutes les 3 min) sans aucune trace depuis le matin
        _texte, soucis = self.passer()
        self.assertEqual(self.relances, ["devis"])
        self.assertIn("aucun passage depuis plus de", " ".join(s.detail for s in soucis))

    # --- corrections sûres ----------------------------------------------------------------------------------------
    def test_doublon_identique_retire(self):
        self.ecrire("devis-etat.json", {"devis": {}, "alertes": {}, "ok_utilises": ["ok-1", "ok-2", "ok-1"]})
        _texte, soucis = self.passer()
        self.assertEqual(self.lire("devis-etat.json")["ok_utilises"], ["ok-1", "ok-2"], "le doublon part, l'ordre et la première occurrence restent")
        self.assertTrue(any("doublon" in s.quoi for s in self.corriges(soucis)))

    def test_cle_manquante_ajoutee_vide(self):
        self.ecrire("devis-etat.json", {"devis": {"a": {}}, "ok_utilises": []})
        self.passer()
        e = self.lire("devis-etat.json")
        self.assertEqual(e["alertes"], {}, "la clé manquante est ajoutée vide")
        self.assertEqual(e["devis"], {"a": {}}, "rien d'autre n'a bougé")

    # --- cas risqués : alerte, rien touché ------------------------------------------------------------------------
    def test_argent_jamais_complete_tout_seul(self):
        self.ecrire("stripe-alerte-etat.json", {"vus": {}})      # « dernier_ts » absent : le compléter réannoncerait d'anciens paiements
        avant = (self.tmp / "stripe-alerte-etat.json").read_text(encoding="utf-8")
        _texte, soucis = self.passer()
        self.assertTrue(any("dernier_ts" in s.quoi and s.risque for s in soucis), "fichier d'argent : alerte, jamais de correction")
        self.assertEqual((self.tmp / "stripe-alerte-etat.json").read_text(encoding="utf-8"), avant, "le fichier d'argent n'a pas bougé")

    def test_prix_hors_reference_alerte(self):
        self.ecrire("devis-etat.json", {"devis": {"garage-rouen": {"prix": 123}}, "alertes": {}, "ok_utilises": []})
        _texte, soucis = self.passer()
        self.assertTrue(any("prix absent de OFFRE-REFERENCE.json" in s.quoi for s in self.bloques(soucis)))
        self.assertEqual(self.lire("devis-etat.json")["devis"]["garage-rouen"]["prix"], 123, "un montant n'est jamais corrigé")

    def test_potentiel_qui_ne_colle_pas_alerte(self):
        prix = int(S.ref_offre()["offres"]["pack"]["prix_unique_eur"])
        (self.tmp / "ventes.json").write_text(json.dumps({"chiffres": [
            {"cle": "paiements", "valeur": -2},
            {"cle": "potentiel", "valeur": prix * 2 + 1, "leads": 2, "prix": prix}]}, ensure_ascii=False), encoding="utf-8")
        _texte, soucis = self.passer()
        quoi = " | ".join(s.quoi for s in self.bloques(soucis))
        self.assertIn("chiffre négatif pour « paiements »", quoi)
        self.assertIn("ne vaut pas leads × prix", quoi)

    def test_brouillon_avec_phrase_interdite_alerte(self):
        phrase = S.ref_offre()["phrases_interdites"][0]
        d = self.tmp / "a-valider"; d.mkdir(parents=True, exist_ok=True)
        (d / f"{date.today().isoformat()}-devis.md").write_text(f"# Devis\n\nTexte : {phrase}.\n", encoding="utf-8")
        _texte, soucis = self.passer()
        self.assertTrue(any("phrase interdite" in s.quoi for s in self.bloques(soucis)))

    # --- fiche a-valider, verrou, essai, garde --------------------------------------------------------------------
    def test_fiche_a_valider_ecrite_une_fois(self):
        self.ecrire("stripe-alerte-etat.json", {"vus": {}})
        self.passer()
        f = self.tmp / "a-valider" / f"{JOUR}-superviseur-vente.md"
        self.assertTrue(f.is_file(), "ce qui attend un « go » est écrit dans B2B\\a-valider")
        t1 = f.read_text(encoding="utf-8")
        self.assertIn("Rien n'a été touché", t1)
        self.passer()
        self.assertEqual(f.read_text(encoding="utf-8"), t1, "le même souci n'est jamais écrit deux fois")
        self.assertEqual(len(self.envois), 1, "ni annoncé deux fois sur Discord")

    def test_verrou_ferme_ne_corrige_rien(self):
        self.ecrire("devis-etat.json", {"devis": {}, "alertes": {}, "ok_utilises": ["x", "x"]})
        texte, soucis = self.passer(c=conf(go_superviseurs=False))
        self.assertEqual(self.lire("devis-etat.json")["ok_utilises"], ["x", "x"], "verrou fermé : aucune correction")
        self.assertEqual(self.corriges(soucis), [])
        self.assertEqual(self.envois, [])
        self.assertIn("verrou « go superviseurs » fermé", texte)
        self.assertFalse((self.tmp / "superviseur-vente-etat.json").exists())

    def test_essai_n_ecrit_rien_et_ne_relance_rien(self):
        self.trace("devis", ok=False, heure="09:10", erreur="RuntimeError")
        self.ecrire("devis-etat.json", {"devis": {}, "alertes": {}, "ok_utilises": ["x", "x"]})
        self.passer(essai=True)
        self.assertEqual(self.relances, []); self.assertEqual(self.envois, [])
        self.assertEqual(self.lire("devis-etat.json")["ok_utilises"], ["x", "x"])
        self.assertFalse((self.tmp / "superviseur-vente-etat.json").exists())
        self.assertFalse((self.tmp / "superviseur-vente-journal.log").exists())
        self.assertFalse((self.tmp / "a-valider").exists())

    def test_le_message_passe_la_garde_du_harness(self):
        self.ecrire("stripe-alerte-etat.json", {"vus": {}})
        texte, _ = self.passer()
        ok, raisons = G.verifier_envoi("superviseur-vente", "discord", texte, maintenant=G.heure_paris(), ctx=CTX_GARDE, tracer=False)
        self.assertTrue(ok, raisons)

    def test_rien_a_signaler_un_seul_resume_par_jour(self):
        texte, soucis = self.passer()
        self.assertEqual(soucis, []); self.assertIn("tous à l'heure", texte)
        self.assertEqual(len(self.envois), 1, "le résumé part même quand tout va bien (une fois par jour)")
        self.passer()
        self.assertEqual(len(self.envois), 1, "et pas à chaque passage de 30 min")

    def test_la_nuit_rien_n_est_annonce(self):
        self.ecrire("stripe-alerte-etat.json", {"vus": {}})
        self.passer(maintenant=datetime(2026, 11, 23, 3, 0))
        self.assertEqual(self.envois, [], "aucune alerte Discord la nuit")
        self.assertIn("hors plage d'envoi", self.sortie)
        self.assertFalse((self.tmp / "a-valider").exists(), "la fiche attend le passage du matin")


# =====================================================================================================================
class Prospection(Base):
    AGENT, DOMAINE, SUIVIS = "superviseur-prospection", "Prospection", ["relances"]
    TACHES = {"relances": {"script": "relances.py", "commandes": [["jour"]], "heure": "08:30", "jours": [0, 1, 2, 3, 4]}}

    def setUp(self):
        super().setUp()
        P.ICI, P.RACINE = self.tmp, self.tmp
        P.HISTORIQUE_JSON = self.tmp / "historique.json"
        self.CONTROLES = P.CONTROLES
        self.trace("relances", heure="08:31")
        self.ecrire("relances-etat.json", {"annonces": {}, "envois": {}})

    def test_agent_silencieux_a_son_heure_est_relance(self):
        shutil.rmtree(self.traces / "relances")      # 08:30 + 20 min de grâce dépassés, aucun passage
        _texte, soucis = self.passer()
        self.assertEqual(self.relances, ["relances"])
        self.assertIn("aucun passage aujourd'hui", " ".join(s.detail for s in soucis))

    def test_samedi_aucune_alerte(self):
        shutil.rmtree(self.traces / "relances")
        _texte, soucis = self.passer(maintenant=datetime(2026, 11, 21, 10, 0))      # samedi : l'agent n'est pas prévu
        self.assertEqual(self.relances, []); self.assertEqual(soucis, [])

    def test_doublon_de_relance_email_retire(self):
        self.ecrire("prospection-etat.json", {"vus": {}, "envois": {}, "relances": ["a|rouen", "b|elbeuf", "a|rouen"],
                                              "lots": {}, "envoyes": {}, "recherches": {}})
        _texte, soucis = self.passer()
        self.assertEqual(self.lire("prospection-etat.json")["relances"], ["a|rouen", "b|elbeuf"], "le prospect compté deux fois ne l'est plus qu'une")
        self.assertTrue(any("doublon" in s.quoi for s in self.corriges(soucis)))

    def test_historique_remis_dans_l_ordre(self):
        P.HISTORIQUE_JSON.write_text(json.dumps({"jours": [{"date": "2026-11-19", "appels": 3}, {"date": "2026-11-17", "appels": 2}]}), encoding="utf-8")
        _texte, soucis = self.passer()
        self.assertEqual([x["date"] for x in json.loads(P.HISTORIQUE_JSON.read_text(encoding="utf-8"))["jours"]], ["2026-11-17", "2026-11-19"])
        self.assertTrue(any("ordre des dates" in s.quoi for s in self.corriges(soucis)))

    def test_deux_entrees_pour_le_meme_jour_alerte_sans_rien_supprimer(self):
        contenu = {"jours": [{"date": "2026-11-19", "appels": 3}, {"date": "2026-11-19", "appels": 7}]}
        P.HISTORIQUE_JSON.write_text(json.dumps(contenu), encoding="utf-8")
        _texte, soucis = self.passer()
        self.assertTrue(any("date(s) en double" in s.quoi for s in self.bloques(soucis)))
        self.assertEqual(json.loads(P.HISTORIQUE_JSON.read_text(encoding="utf-8")), contenu, "aucune ligne supprimée : Liam choisit")

    def test_chiffres_qui_se_contredisent_alerte(self):
        P.HISTORIQUE_JSON.write_text(json.dumps({"jours": [{"date": "2026-11-19", "appels": 2, "leads_chauds": 5, "rdv": 3}]}), encoding="utf-8")
        _texte, soucis = self.passer()
        quoi = " | ".join(s.quoi for s in self.bloques(soucis))
        self.assertIn("5 leads chauds pour 2 appel(s)", quoi)
        self.assertIn("3 rendez-vous pour 2 appel(s)", quoi)

    def test_date_future_et_cle_mal_formee_alertent(self):
        self.ecrire("relances-etat.json", {"annonces": {"pas-une-cle": "2026-11-19", "0612345678|2030-01-01|1": "2026-11-19"},
                                           "envois": {"2026-11-19": 1}})
        _texte, soucis = self.passer()
        quoi = " | ".join(s.quoi for s in self.bloques(soucis))
        self.assertIn("clé(s) de relance mal formée(s)", quoi)
        self.assertIn("appel daté dans le futur", quoi)
        self.assertEqual(len(self.lire("relances-etat.json")["annonces"]), 2, "aucune relance mémorisée n'est supprimée")

    def test_compte_d_envois_contradictoire_alerte(self):
        self.ecrire("relances-etat.json", {"annonces": {"0612345678|2026-11-16|1": "2026-11-19"}, "envois": {"2026-11-19": 4}})
        _texte, soucis = self.passer()
        self.assertTrue(any("mais 1 mémorisée" in s.quoi for s in self.bloques(soucis)))


# =====================================================================================================================
class Sites(Base):
    AGENT, DOMAINE, SUIVIS = "superviseur-sites", "Sites", []
    TACHES = {}
    PAGE_PROPRE = ("<!doctype html><html><head><meta charset=\"utf-8\"><meta name=\"robots\" content=\"noindex\">"
                   "<title>Garage Dupont</title><link rel=\"stylesheet\" href=\"style.css\"></head>"
                   "<body><h1>Garage Dupont, Rouen</h1><img src=\"photo.jpg\" alt=\"atelier\"></body></html>")

    def setUp(self):
        super().setUp()
        ST.RACINE, ST.SITES, ST.PAGES_EXEMPLE = self.tmp, self.tmp / "sites", self.tmp / "pages-exemple"
        ST.SUIVI_PAGES = ST.PAGES_EXEMPLE / "suivi.csv"
        self.indexables = []
        self.CONTROLES = [("pages du dépôt", lambda: ST.controle_pages(None, self.indexables)), ("suivi des pages exemple", ST.controle_suivi_pages)]
        self.site = ST.SITES / "premium-garage"; self.site.mkdir(parents=True)
        (self.site / "logo.svg").write_text("<svg/>", encoding="utf-8")      # au moins un media : git transporte donc les medias de ce site

    def page(self, html, nom="index.html"):
        (self.site / nom).write_text(html, encoding="utf-8")

    def test_page_conforme_aucun_souci(self):
        self.page(self.PAGE_PROPRE)
        (self.site / "style.css").write_text("body{color:#111}", encoding="utf-8")
        (self.site / "photo.jpg").write_bytes(b"\xff\xd8\xff")
        _texte, soucis = self.passer()
        self.assertEqual([s.ligne() for s in soucis], [])

    def test_lien_casse_image_absente_et_reste_de_modele(self):
        self.page(self.PAGE_PROPRE.replace("</body>", "<a href=\"contact.html\">Contact</a><p>Lorem ipsum dolor</p></body>"))
        avant = (self.site / "index.html").read_text(encoding="utf-8")
        _texte, soucis = self.passer()
        quoi = " | ".join(s.quoi for s in soucis)
        self.assertIn("lien(s) interne(s) cassé(s)", quoi)
        self.assertIn("absent(s)", quoi)
        self.assertIn("lorem ipsum", quoi)
        self.assertTrue(all(s.risque for s in soucis), "une page n'est jamais réécrite par un agent")
        self.assertEqual((self.site / "index.html").read_text(encoding="utf-8"), avant)

    def test_page_exemple_sans_noindex_alerte(self):
        self.page(self.PAGE_PROPRE.replace("<meta name=\"robots\" content=\"noindex\">", ""))
        (self.site / "style.css").write_text("x", encoding="utf-8"); (self.site / "photo.jpg").write_bytes(b"x")
        _texte, soucis = self.passer()
        self.assertTrue(any("n'est plus en noindex" in s.quoi for s in soucis))

    def test_site_vitrine_en_noindex_alerte(self):
        self.indexables = ["agence"]      # declare indexable dans les reglages : le noindex devient une alerte
        agence = ST.SITES / "agence"; agence.mkdir()
        (agence / "index.html").write_text("<html><head><meta name=\"robots\" content=\"noindex\"><title>LM</title></head><body><h1>LM</h1></body></html>", encoding="utf-8")
        _texte, soucis = self.passer()
        self.assertTrue(any("site vitrine) est en noindex" in s.quoi for s in soucis))

    def test_page_sans_titre_alerte(self):
        self.page("<html><head><meta name=\"robots\" content=\"noindex\"></head><body><p>texte</p></body></html>")
        _texte, soucis = self.passer()
        quoi = " | ".join(s.quoi for s in soucis)
        self.assertIn("n'a pas de titre", quoi); self.assertIn("<h1>", quoi)

    def test_suivi_des_pages_dedoublonne(self):
        ST.PAGES_EXEMPLE.mkdir(parents=True, exist_ok=True)
        ST.SUIVI_PAGES.write_text("date,nom,lien\n2026-11-20,Dupont,https://ex.test/a\n2026-11-20,Dupont,https://ex.test/a\n", encoding="utf-8")
        _texte, soucis = self.passer()
        self.assertEqual(len(ST.SUIVI_PAGES.read_text(encoding="utf-8").strip().splitlines()), 2, "la ligne en double est retirée, l'en-tête reste")
        self.assertTrue(any("en double" in s.quoi for s in self.corriges(soucis)))

    def test_deux_fiches_pour_le_meme_lien_alerte(self):
        ST.PAGES_EXEMPLE.mkdir(parents=True, exist_ok=True)
        contenu = "date,nom,lien\n2026-11-20,Dupont,https://ex.test/a\n2026-11-20,Durand,https://ex.test/a\n"
        ST.SUIVI_PAGES.write_text(contenu, encoding="utf-8")
        _texte, soucis = self.passer()
        self.assertTrue(any("en double avec des valeurs différentes" in s.quoi for s in self.bloques(soucis)))
        self.assertEqual(ST.SUIVI_PAGES.read_text(encoding="utf-8"), contenu, "rien n'est supprimé : Liam choisit")

    def test_media_non_versionne_n_est_pas_une_image_manquante(self):
        (self.site / "logo.svg").unlink()      # aucun media dans le dossier : git ne les transporte pas sur cette machine
        self.page(self.PAGE_PROPRE)
        (self.site / "style.css").write_text("body{color:#111}", encoding="utf-8")
        _texte, soucis = self.passer()
        self.assertEqual([s.ligne() for s in soucis], [], "photo.jpg absente mais aucun media versionne : ce n'est pas un probleme")

    def test_aucun_site_dans_le_depot_rien_a_dire(self):
        shutil.rmtree(self.site)
        _texte, soucis = self.passer()
        self.assertEqual(soucis, [], "sur le serveur, git ne transporte pas les sites : ce n'est pas un problème")


# =====================================================================================================================
class Mail(Base):
    AGENT, DOMAINE, SUIVIS = "superviseur-mail", "Mail", ["interim"]
    TACHES = {"interim": {"script": "interim.py", "commandes": [["passage"]], "heure": "07:30", "lundi": "09:00"}}
    COLONNES = "agence,adresse_confirmee,source,prochaine_action\n"

    def setUp(self):
        super().setUp()
        ML.ICI = self.tmp
        ML.SCRIPT_TRI, ML.CONFIG_TRI = self.tmp / "interim.py", self.tmp / "interim-config.json"
        ML.ETAT_TRI, ML.SUIVI_TRI = self.tmp / "interim-etat.json", self.tmp / "interim-suivi.csv"
        self.trace("interim", heure="07:31")
        ML.SCRIPT_TRI.write_text('PORTEES = ["https://www.googleapis.com/auth/gmail.readonly"]\n', encoding="utf-8")
        self.ecrire("interim-config.json", {"boite": "emoliam255@gmail.com",
                                            "agences": [{"agence": "Adéquat Rouen", "adresse_confirmee": "oui", "source": "Liam", "confirmee": "oui (Liam)"}]})
        self.ecrire("interim-etat.json", {"vus": {}, "matin": {}, "semaine": {}})
        ML.SUIVI_TRI.write_text(self.COLONNES + "Adéquat Rouen,oui,Liam,rappeler lundi\n", encoding="utf-8")
        self.conf_mail = conf(boite_attendue="emoliam255@gmail.com", portee_attendue="https://www.googleapis.com/auth/gmail.readonly")

    def controles(self, etat):
        return [("lecture seule", lambda: ML.controle_lecture_seule(self.conf_mail)), ("état du tri", ML.controle_etat_tri),
                ("fiches d'agences", ML.controle_fiches_agences), ("actions à rappeler", lambda: ML.controle_actions_perdues(etat))]

    def passer_mail(self, essai=False, c=None):
        etat = S.etat_lire(self.AGENT)
        return self.passer(self.controles(etat), essai, c or self.conf_mail, etat=etat)

    def test_tout_en_ordre_aucun_souci(self):
        _texte, soucis = self.passer_mail()
        self.assertEqual([s.ligne() for s in soucis], [])

    def test_portee_en_ecriture_alerte_tout_de_suite(self):
        ML.SCRIPT_TRI.write_text('PORTEES = ["https://www.googleapis.com/auth/gmail.readonly", "https://www.googleapis.com/auth/gmail.modify"]\n', encoding="utf-8")
        _texte, soucis = self.passer_mail()
        s = [x for x in self.bloques(soucis) if "lecture seule" in x.quoi]
        self.assertTrue(s, "une portée Gmail en écriture doit alerter")
        self.assertIn("gmail.modify", s[0].detail)

    def test_boite_changee_alerte(self):
        self.ecrire("interim-config.json", {"boite": "autre@gmail.com", "agences": []})
        _texte, soucis = self.passer_mail()
        self.assertTrue(any("n'est plus celle attendue" in s.quoi for s in self.bloques(soucis)))

    def test_fiche_en_double_identique_retiree(self):
        ML.SUIVI_TRI.write_text(self.COLONNES + "Adéquat Rouen,oui,Liam,rappeler lundi\nAdéquat Rouen,oui,Liam,rappeler lundi\n", encoding="utf-8")
        _texte, soucis = self.passer_mail()
        self.assertEqual(len(ML.SUIVI_TRI.read_text(encoding="utf-8").strip().splitlines()), 2)
        self.assertTrue(any("en double" in s.quoi for s in self.corriges(soucis)))

    def test_fiche_incomplete_et_agence_en_double_alertent(self):
        self.ecrire("interim-config.json", {"boite": "emoliam255@gmail.com",
                                            "agences": [{"agence": "Crit Rouen"}, {"agence": "Crit Rouen", "adresse_confirmee": "non", "source": "x"}]})
        _texte, soucis = self.passer_mail()
        quoi = " | ".join(s.quoi for s in self.bloques(soucis))
        self.assertIn("incomplète(s)", quoi); self.assertIn("deux fois", quoi)

    def test_adresse_confirmee_sans_liam_alerte(self):
        self.ecrire("interim-config.json", {"boite": "emoliam255@gmail.com",
                                            "agences": [{"agence": "Supplay Rouen", "adresse_confirmee": "oui", "source": "annuaire", "confirmee": "oui"}]})
        _texte, soucis = self.passer_mail()
        self.assertTrue(any("confirmée(s) sans Liam" in s.quoi for s in self.bloques(soucis)))

    def test_action_a_rappeler_disparue_alerte_sans_la_retablir(self):
        self.passer_mail()      # premier passage : l'action est mémorisée
        ML.SUIVI_TRI.write_text(self.COLONNES + "Adéquat Rouen,oui,Liam,\n", encoding="utf-8")
        _texte, soucis = self.passer_mail()
        s = [x for x in self.bloques(soucis) if "disparu" in x.quoi]
        self.assertTrue(s, "une action à rappeler qui disparaît doit alerter")
        self.assertIn("Adéquat Rouen", s[0].detail)
        self.assertIn(",\n", ML.SUIVI_TRI.read_text(encoding="utf-8"))      # rien n'a été rétabli

    def test_script_de_tri_absent_alerte(self):
        ML.SCRIPT_TRI.unlink()
        _texte, soucis = self.passer_mail()
        self.assertTrue(any("script de tri du courrier est absent" in s.quoi for s in self.bloques(soucis)))


# =====================================================================================================================
class Videos(Base):
    """Domaine Vidéos (22/11/2026) : sept agents, un verrou PROPRE en plus du verrou commun, et rien qui puisse faire repartir une vidéo sur TikTok."""

    AGENT, DOMAINE, SUIVIS = "superviseur-videos", "Vidéos", ["videos-scripts", "videos-creation"]
    TACHES = {"videos-scripts": {"script": "scripts.py", "commandes": [["jour"]], "heure": "05:45"},
              "videos-creation": {"script": "creation.py", "commandes": [["passage"]], "heure": "06:00"}}
    ENTETE_CSV = "date;agent;video;ligne;compte;statut;hook;detail;tts\n"
    LIGNE_CSV = "2026-11-23;videos-creation;2026-11-23-0600;A;;rendu;accroche;;edge\n"
    LEGENDE = "Gérard découvre son site.\n\n#artisan #site\n\nContenu généré par IA."

    def setUp(self):
        super().setUp()
        VD.RACINE, VD.VIDEOS = self.tmp, self.tmp / "Videos"
        VD.VIDEOS.mkdir(parents=True, exist_ok=True)
        VD.JOURNAL_CSV = VD.VIDEOS / "journal-videos.csv"
        VD.SUJETS = VD.VIDEOS / "scripts" / "sujets.json"
        VD.PUBLICATION_ETAT = VD.VIDEOS / "videos-publication-etat.json"
        VD.VERROU_PUBLICATION = VD.VIDEOS / "publication.verrou"
        VD.A_VALIDER_VIDEOS = VD.VIDEOS / "a-valider"
        self.trace("videos-scripts", heure="05:46"); self.trace("videos-creation", heure="06:01")
        self.CONTROLES = VD.controles(conf(), LUNDI, self.traces)

    def publication(self, data):
        VD.PUBLICATION_ETAT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8"); return VD.PUBLICATION_ETAT

    def legende(self, texte, nom="2026-11-23-0600.txt"):
        VD.A_VALIDER_VIDEOS.mkdir(parents=True, exist_ok=True)
        f = VD.A_VALIDER_VIDEOS / nom; f.write_text(texte, encoding="utf-8"); return f

    def journal(self, lignes=2):
        VD.JOURNAL_CSV.write_text(self.ENTETE_CSV + self.LIGNE_CSV * lignes, encoding="utf-8"); return VD.JOURNAL_CSV

    # --- rien à dire ----------------------------------------------------------------------------------------------
    def test_sans_donnees_video_aucun_souci(self):
        _texte, soucis = self.passer()
        self.assertEqual([s.ligne() for s in soucis], [], "sur le gros PC les données vidéo sont absentes : ce n'est pas un problème")

    # --- agent planté ---------------------------------------------------------------------------------------------
    def test_agent_plante_relance_une_seule_fois(self):
        self.trace("videos-creation", ok=False, heure="06:02", erreur="RuntimeError")
        self.passer()
        self.assertEqual(self.relances, ["videos-creation"])
        _texte2, soucis2 = self.passer()
        self.assertEqual(self.relances, ["videos-creation"], "jamais deux relances le même jour")
        self.assertTrue(any("toujours erreur après une relance" in s.quoi for s in self.bloques(soucis2)))

    def test_maillon_silencieux_a_son_heure_est_relance(self):
        shutil.rmtree(self.traces / "videos-scripts")      # 05:45 + délai de grâce dépassés, aucun passage
        _texte, soucis = self.passer()
        self.assertEqual(self.relances, ["videos-scripts"])
        self.assertIn("aucun passage aujourd'hui", " ".join(s.detail for s in soucis))

    # --- corrections sûres ----------------------------------------------------------------------------------------
    def test_ligne_en_double_du_journal_retiree(self):
        self.journal(2)
        _texte, soucis = self.passer()
        self.assertEqual(len(VD.JOURNAL_CSV.read_text(encoding="utf-8").strip().splitlines()), 2, "la ligne en double part, l'en-tête reste")
        self.assertTrue(any("en double" in s.quoi for s in self.corriges(soucis)))

    def test_sujet_en_double_retire(self):
        VD.SUJETS.parent.mkdir(parents=True, exist_ok=True)
        a = {"jour": "2026-11-23", "passage": "06:00", "sujet": "le devis qui ne vient jamais", "titre": "Le devis fantôme"}
        b = {"jour": "2026-11-23", "passage": "14:00", "sujet": "le site jamais fini", "titre": "Le site fantôme"}
        VD.SUJETS.write_text(json.dumps([a, b, a], ensure_ascii=False), encoding="utf-8")
        _texte, soucis = self.passer()
        self.assertEqual(json.loads(VD.SUJETS.read_text(encoding="utf-8")), [a, b], "le doublon part, l'ordre et la première occurrence restent")
        self.assertTrue(any("doublon" in s.quoi for s in self.corriges(soucis)))

    # --- cas risqués : alerte, rien touché ------------------------------------------------------------------------
    def test_etat_de_publication_jamais_complete_tout_seul(self):
        p = self.publication({"publications": {}})      # « arrets » et « essais » absents
        avant = p.read_text(encoding="utf-8")
        _texte, soucis = self.passer()
        quoi = " | ".join(s.quoi for s in self.bloques(soucis))
        self.assertIn("clé « arrets » absente", quoi); self.assertIn("clé « essais » absente", quoi)
        self.assertEqual(p.read_text(encoding="utf-8"), avant, "l'état de publication n'a pas bougé : une vidéo publiée ne doit pas repartir")
        self.assertEqual(self.corriges(soucis), [])

    def test_plafond_de_publications_depasse_alerte(self):
        faites = [{"ligne": "A", "passage": h, "video": f"v{i}.mp4"} for i, h in enumerate(("06:00", "14:00", "22:00", "23:00"))]
        p = self.publication({"publications": {"2026-11-22": faites}, "arrets": {}, "essais": {}})
        avant = p.read_text(encoding="utf-8")
        _texte, soucis = self.passer()
        self.assertTrue(any("4 publications le 2026-11-22 sur la ligne A" in s.quoi for s in self.bloques(soucis)))
        self.assertEqual(p.read_text(encoding="utf-8"), avant, "aucune ligne retirée : elle ferait republier la vidéo")

    def test_meme_video_publiee_deux_fois_alerte(self):
        deux = [{"ligne": "A", "passage": "06:00", "video": "v1.mp4"}, {"ligne": "A", "passage": "06:00", "video": "v1.mp4"}]
        self.publication({"publications": {"2026-11-22": deux}, "arrets": {}, "essais": {}})
        _texte, soucis = self.passer()
        self.assertTrue(any("deux fois la même vidéo publiée" in s.quoi for s in self.bloques(soucis)))

    def test_jour_de_publication_dans_le_futur_alerte(self):
        self.publication({"publications": {"2030-01-01": []}, "arrets": {}, "essais": {}})
        _texte, soucis = self.passer()
        self.assertTrue(self.bloques(soucis), "une date de publication dans le futur doit alerter")
        self.assertIn("futur", " ".join(s.quoi + " " + s.detail for s in self.bloques(soucis)))

    def test_verrou_de_publication_oublie_alerte_sans_etre_retire(self):
        VD.VERROU_PUBLICATION.write_text("1234", encoding="utf-8")
        vieux = datetime(2026, 11, 22, 1, 0).timestamp()
        os.utime(VD.VERROU_PUBLICATION, (vieux, vieux))
        _texte, soucis = self.passer()
        self.assertTrue(any("verrou de publication en place depuis" in s.quoi for s in self.bloques(soucis)))
        self.assertTrue(VD.VERROU_PUBLICATION.is_file(), "le verrou n'est jamais retiré : ce serait deux publications en même temps")

    def test_verrou_de_publication_recent_nest_pas_un_souci(self):
        VD.VERROU_PUBLICATION.write_text("1234", encoding="utf-8")
        _texte, soucis = self.passer()
        self.assertEqual([s.ligne() for s in soucis], [], "une publication en cours est normale")

    def test_legende_sans_mention_ia_alerte_sans_la_reecrire(self):
        f = self.legende("Gérard découvre son site.\n\n#artisan")
        avant = f.read_text(encoding="utf-8")
        _texte, soucis = self.passer()
        self.assertTrue(any("sans la mention" in s.quoi for s in self.bloques(soucis)))
        self.assertEqual(f.read_text(encoding="utf-8"), avant, "une légende destinée au public n'est jamais réécrite")

    def test_legende_avec_phrase_interdite_alerte(self):
        phrase = S.ref_offre()["phrases_interdites"][0]
        self.legende(self.LEGENDE + "\n\n" + phrase)
        _texte, soucis = self.passer()
        self.assertTrue(any("phrase interdite" in s.quoi for s in self.bloques(soucis)))

    def test_legende_conforme_aucun_souci(self):
        self.legende(self.LEGENDE)
        _texte, soucis = self.passer()
        self.assertEqual([s.ligne() for s in soucis], [])

    def test_chaine_dans_le_desordre_alerte(self):
        shutil.rmtree(self.traces / "videos-scripts")      # la création a tourné, les scripts jamais
        _texte, soucis = self.passer()
        quoi = " | ".join(s.quoi for s in self.bloques(soucis))
        self.assertIn("videos-creation a tourné aujourd'hui, videos-scripts jamais", quoi)   # marketing n'est pas planifié ici : il sort de la chaîne
        self.assertTrue(all(s.risque for s in self.bloques(soucis) if "désordre" in s.detail), "une chaîne en désordre n'est jamais relancée")

    # --- verrou propre au domaine ---------------------------------------------------------------------------------
    def test_verrou_propre_ferme_meme_quand_le_verrou_commun_est_ouvert(self):
        commun = self.tmp / "superviseurs-config.json"
        commun.write_text(json.dumps({"go_superviseurs": True, "envoi_automatique": True}), encoding="utf-8")
        self.ecrire("superviseur-videos-config.json", {"go_superviseur_videos": False})
        ancien = S.COMMUN; S.COMMUN = commun
        try:
            c = S.cfg("superviseur-videos", VD.DEFAUT)
            self.assertEqual(c["verrou_propre"], "go_superviseur_videos")
            self.assertFalse(c["go_superviseurs"], "« go superviseurs » ouvert ne suffit pas : ce domaine a son propre verrou")
            self.ecrire("superviseur-videos-config.json", {"go_superviseur_videos": True})
            self.assertTrue(S.cfg("superviseur-videos", VD.DEFAUT)["go_superviseurs"], "les deux verrous ouverts : le domaine tourne")
            self.ecrire("superviseur-vente-config.json", {})
            cv = S.cfg("superviseur-vente")
            self.assertIsNone(cv.get("verrou_propre"), "les quatre premiers superviseurs n'ont pas de verrou propre")
            self.assertTrue(cv["go_superviseurs"], "et cette nouveauté ne les referme pas")
        finally:
            S.COMMUN = ancien

    def test_verrou_ferme_ne_corrige_rien_et_nomme_son_verrou(self):
        avant = self.journal(2).read_text(encoding="utf-8")
        texte, soucis = self.passer(c=conf(go_superviseurs=False, verrou_propre="go_superviseur_videos"))
        self.assertEqual(VD.JOURNAL_CSV.read_text(encoding="utf-8"), avant, "verrou fermé : aucune correction")
        self.assertEqual(self.corriges(soucis), []); self.assertEqual(self.envois, [])
        self.assertIn("verrou « go_superviseur_videos » fermé", texte)
        self.assertFalse((self.tmp / "superviseur-videos-etat.json").exists())

    # --- essai, fiche, garde --------------------------------------------------------------------------------------
    def test_essai_n_ecrit_rien_et_ne_relance_rien(self):
        self.trace("videos-creation", ok=False, heure="06:02", erreur="RuntimeError")
        avant = self.journal(2).read_text(encoding="utf-8")
        self.passer(essai=True)
        self.assertEqual(self.relances, []); self.assertEqual(self.envois, [])
        self.assertEqual(VD.JOURNAL_CSV.read_text(encoding="utf-8"), avant)
        self.assertFalse((self.tmp / "superviseur-videos-etat.json").exists())
        self.assertFalse((self.tmp / "superviseur-videos-journal.log").exists())
        self.assertFalse((self.tmp / "a-valider").exists())

    def test_fiche_a_valider_ecrite_une_fois(self):
        self.publication({"publications": {}})
        self.passer()
        f = self.tmp / "a-valider" / (JOUR + "-superviseur-videos.md")
        self.assertTrue(f.is_file(), "ce qui attend un « go » est écrit dans B2B\\a-valider")
        t1 = f.read_text(encoding="utf-8")
        self.passer()
        self.assertEqual(f.read_text(encoding="utf-8"), t1, "le même souci n'est jamais écrit deux fois")
        self.assertEqual(len(self.envois), 1, "ni annoncé deux fois sur Discord")

    def test_le_message_passe_la_garde_du_harness(self):
        self.publication({"publications": {}})
        texte, _ = self.passer()
        ok, raisons = G.verifier_envoi("superviseur-videos", "discord", texte, maintenant=G.heure_paris(), ctx=CTX_GARDE, tracer=False)
        self.assertTrue(ok, raisons)


# =====================================================================================================================
class VueJarvis(Base):
    AGENT, DOMAINE, SUIVIS = "jarvis-vue", "Jarvis", []
    TACHES = {}

    def setUp(self):
        super().setUp()
        JV.ICI = self.tmp
        JV.SORTIE = self.tmp / "ETAT-SUPERVISEURS.md"
        self.ecrire("superviseur-vente-etat.json", {"corrections": {}, "en_attente": {}, "relances": {}, "resumes": {}, "empreintes": {}})
        self.ecrire("superviseur-prospection-etat.json", {"corrections": {date.today().isoformat(): ["un doublon retiré de relances"]},
                                                          "en_attente": {}, "relances": {}, "resumes": {}, "empreintes": {}})
        self.ecrire("superviseur-mail-etat.json", {"corrections": {}, "relances": {}, "resumes": {}, "empreintes": {},
                                                   "en_attente": {"interim|portees": {"depuis": JOUR, "quoi": "interim : la lecture Gmail n'est plus en lecture seule"}}})
        # superviseur-sites : aucun fichier d'état -> « jamais passé »

    def passer_vue(self, essai=False, c=None, maintenant=None):
        with redirect_stdout(io.StringIO()):
            code = JV.cmd_passage(c or conf(heure_resume="19:40"), essai, maintenant or datetime(2026, 11, 23, 19, 45),
                                  envoyer=lambda t: self.envois.append(t) or True)
        return code

    def test_les_cinq_domaines_sont_remontes(self):
        self.assertEqual(self.passer_vue(), 0)
        t = JV.SORTIE.read_text(encoding="utf-8")
        for x in ("Vente", "Prospection", "Sites", "Mail", "Vidéos", "BLOQUÉ", "corrigé", "jamais passé"):
            self.assertIn(x, t)
        self.assertIn("la lecture Gmail n'est plus en lecture seule", t)
        self.assertEqual(len(self.envois), 1, "un seul message Discord groupé")
        self.assertIn("en attente de ton « go »", self.envois[0])

    def test_un_seul_message_par_jour(self):
        self.passer_vue(); self.passer_vue(maintenant=datetime(2026, 11, 23, 20, 15))
        self.assertEqual(len(self.envois), 1)

    def test_rien_avant_l_heure_du_resume(self):
        self.passer_vue(maintenant=datetime(2026, 11, 23, 10, 0))
        self.assertEqual(self.envois, [], "le message groupé part le soir, à partir de heure_resume")
        self.assertTrue(JV.SORTIE.is_file(), "le fichier court est tenu à jour à chaque passage")

    def test_elle_ne_corrige_rien(self):
        avant = {p.name: p.read_text(encoding="utf-8") for p in self.tmp.glob("superviseur-*-etat.json")}
        self.passer_vue()
        for nom, t in avant.items():
            self.assertEqual((self.tmp / nom).read_text(encoding="utf-8"), t, "la vue Jarvis ne touche à aucun état de superviseur")

    def test_essai_n_ecrit_rien(self):
        self.passer_vue(essai=True)
        self.assertEqual(self.envois, []); self.assertFalse(JV.SORTIE.exists())
        self.assertFalse((self.tmp / "jarvis-vue-etat.json").exists())

    def test_verrou_ferme_rien_envoye(self):
        self.passer_vue(c=conf(go_superviseurs=False, heure_resume="19:40"))
        self.assertEqual(self.envois, [])
        self.assertTrue(JV.SORTIE.is_file(), "le fichier d'état reste lisible même verrou fermé")

    def test_le_message_passe_la_garde_du_harness(self):
        self.passer_vue()
        ok, raisons = G.verifier_envoi("jarvis-vue", "discord", self.envois[0], maintenant=G.heure_paris(), ctx=CTX_GARDE, tracer=False)
        self.assertTrue(ok, raisons)


if __name__ == "__main__":
    unittest.main(verbosity=1)
