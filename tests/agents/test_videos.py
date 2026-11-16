#!/usr/bin/env python3
"""Harness - équipe Vidéos TikTok (16/11/2026) : règles (SKILL-VIDEOS.md relu, sections obligatoires), veille (flux RSS fictif, rien de TikTok, purge, hooks.md),
scripts (garde-fous : chiffres, promesses, phrases molles, lieux sur la ligne B, mise en scène, sujet déjà traité ; taux de commission seulement depuis la config),
marketing (grille des accroches, 3 accroches notées, rythme, sous-titres, journal-videos.csv), création (sous-titres mot à mot en .ass dans la zone sûre, carte de fin),
publication (fermée sans « go publier » par ligne, essai obligatoire, captcha = arrêt + alerte, plafond par compte, STOP, verrou, CSV ; TikTok remplacé par un bouchon),
nettoyage (nettoyage.ps1 dans un dossier temporaire : vieux .mp4 et intermédiaires supprimés, ligne CSV avant, skill / scripts / veille / vidéos protégées intacts).
Tout se passe dans un dossier temporaire : aucun réseau, aucun Ollama, aucun navigateur, aucun rendu, rien de publié."""
import csv, importlib.util, io, json, os, shutil, subprocess, sys, tempfile, time, unittest
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
import commun as T

AG = T.RACINE / "Videos" / "agents"
sys.path.insert(0, str(AG))


def charger(nom):
    s = importlib.util.spec_from_file_location("videos_" + nom, AG / f"{nom}.py"); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


C = charger("commun"); sys.modules["commun"] = C
V, S = charger("veille"), charger("scripts"); sys.modules["scripts"] = S
MK, K, P = charger("marketing"), charger("creation"), charger("publication")
for m in (V, S, MK, K, P): m.C = C
MK.S = S

BON = {"sujet": "Le client qui cherche vos horaires un dimanche soir", "titre": "Vos horaires visibles le dimanche soir",
       "accroche": "Fermé ou ouvert ?", "legende": "Une page claire répond à la question avant même que le client appelle.",
       "scenes": ["Ouvert demain matin ? Votre client ne sait pas.",
                  "Il cherche votre nom sur son téléphone, sans réponse claire.",
                  "Vos horaires restent sur la vitrine, invisibles depuis son canapé.",
                  "Avec une page simple, il lit vos horaires et votre adresse.",
                  "Un bouton lui permet de vous appeler directement.",
                  "Lundi matin, il sait déjà quand passer chez vous."]}
CHAMPS = ("VIDEOS", "VEILLE", "SCRIPTS", "A_VALIDER", "PUBLIEES", "TRAVAIL", "SUJETS", "CONFIG", "JOURNAL_CSV", "HOOKS", "HOOKS_BASE", "SKILL")


class Base(unittest.TestCase):
    def setUp(self):
        self.r = Path(tempfile.mkdtemp(prefix="videos-test-"))
        self.ancien = {k: getattr(C, k) for k in CHAMPS}
        C.VIDEOS = self.r; C.VEILLE, C.SCRIPTS, C.A_VALIDER, C.PUBLIEES, C.TRAVAIL = (self.r / n for n in ("veille", "scripts", "a-valider", "publiees", "travail"))
        C.SUJETS = C.SCRIPTS / "sujets.json"; C.CONFIG = self.r / "videos-config.json"; C.JOURNAL_CSV = self.r / "journal-videos.csv"
        C.HOOKS, C.HOOKS_BASE, C.SKILL = self.r / "hooks.md", self.r / "hooks-base.md", self.r / "SKILL-VIDEOS.md"
        for k, f in (("CONFIG", C.CONFIG), ("HOOKS_BASE", C.HOOKS_BASE), ("SKILL", C.SKILL)): shutil.copy2(self.ancien[k], f)
        self.p_stop = (P.STOP_VIDEOS, P.STOP_B2B, P.VERROU); P.STOP_VIDEOS, P.STOP_B2B, P.VERROU = self.r / "STOP", self.r / "B2B-STOP", self.r / "publication.verrou"

    def tearDown(self):
        for k, v in self.ancien.items(): setattr(C, k, v)
        P.STOP_VIDEOS, P.STOP_B2B, P.VERROU = self.p_stop
        shutil.rmtree(self.r, ignore_errors=True)

    def conf(self, **x):
        c = C.cfg(); c.update(x); return c

    def csv(self): return C.csv_lire()


class Regles(Base):
    def test_skill_relu_et_complet(self):
        t = C.regles()
        for s in C.SECTIONS_SKILL: self.assertIn(s, t)
        self.assertIn("aucun chiffre", C.section(t, "Règles pour Qwen").lower())
        for mot in ("go publier", "taux_commission", "contenu généré par IA", "zone sûre", "nettoyage_jours", "Gratuit", "TikTok uniquement"): self.assertIn(mot.lower(), t.lower(), mot)
        C.SKILL.write_text("# vide", encoding="utf-8")
        with self.assertRaises(RuntimeError): C.regles()
        C.SKILL.unlink()
        with redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as e: C.exiger_regles("videos-test")
        self.assertEqual(e.exception.code, 3)

    def test_config_lignes(self):
        c = C.cfg()
        self.assertEqual(set(c["lignes"]), {"A", "B"}); self.assertFalse(c["lignes"]["A"]["go_publier"]); self.assertFalse(c["lignes"]["B"]["go_publier"])
        self.assertEqual(c["lignes"]["B"]["taux_commission"], "")                     # laissé vide : Liam le renseigne
        self.assertTrue(c["lignes"]["B"]["tutoiement"]); self.assertIn("lien en bio", c["lignes"]["B"]["message"])
        self.assertEqual(c["passages"], ["06:00", "14:00", "22:00"]); self.assertEqual((c["duree_min_s"], c["duree_max_s"]), (20, 35))
        self.assertEqual(c["nettoyage_jours"], 14); self.assertIn(".mp4", c["nettoyage_extensions"])
        (self.r / "videos-config.local.json").write_text(json.dumps({"lignes": {"A": {"go_publier": "oui"}, "B": {"go_publier": True}}}), encoding="utf-8")
        c = C.cfg(); self.assertFalse(c["lignes"]["A"]["go_publier"]); self.assertTrue(c["lignes"]["B"]["go_publier"])   # seul true ouvre une ligne
        self.assertTrue(c["lignes"]["B"]["message"])                                   # fusion profonde : le reste de la ligne est gardé


class Veille(Base):
    RSS = ('<rss><channel><item><title>Format court qui marche - Blog Vidéo</title><link>https://exemple.fr/a</link><pubDate>Mon, 16 Nov 2026 10:00:00 GMT</pubDate>'
           '<source url="https://exemple.fr">Blog Vidéo</source></item><item><title>Pourquoi vos vidéos décrochent - Mag</title><link>https://exemple.fr/b</link>'
           '<pubDate>Mon, 16 Nov 2026 10:00:00 GMT</pubDate><source url="https://mag.fr">Mag</source></item><item><title>Vidéo TikTok</title><link>https://www.tiktok.com/x</link>'
           '<pubDate>Mon, 16 Nov 2026 10:00:00 GMT</pubDate><source url="https://www.tiktok.com">TikTok</source></item></channel></rss>')

    def ouvrir(self, rq, timeout=0):
        self.urls.append(rq.full_url); return io.BytesIO(self.RSS.encode("utf-8"))

    def test_note_sans_tiktok_purge_et_hooks(self):
        self.urls = []
        C.VEILLE.mkdir(); (C.VEILLE / "2026-09-01.md").write_text("vieux", encoding="utf-8"); (C.VEILLE / "2026-10-20.md").write_text("récent", encoding="utf-8")
        with redirect_stdout(io.StringIO()): code = V.cmd_jour(self.conf(veille_requetes=["a", "b"]), "2026-11-16", False, ouvrir=self.ouvrir)
        self.assertEqual(code, 0)
        note = (C.VEILLE / "2026-11-16.md").read_text(encoding="utf-8")
        self.assertIn("Format court qui marche", note); self.assertNotIn("tiktok", note.lower().replace("rien de tiktok", ""))
        self.assertTrue(all("news.google.com" in u for u in self.urls))            # aucune page de TikTok n'est ouverte
        self.assertFalse((C.VEILLE / "2026-09-01.md").exists()); self.assertTrue((C.VEILLE / "2026-10-20.md").exists())   # notes gardées 30 jours
        h = C.HOOKS.read_text(encoding="utf-8")
        self.assertIn("Formules de base", h); self.assertIn("Pourquoi vos vidéos décrochent", h); self.assertNotIn("Format court qui marche", h)
        with redirect_stdout(io.StringIO()): V.cmd_jour(self.conf(veille_requetes=["a"]), "2026-11-17", False, ouvrir=self.ouvrir)
        self.assertEqual(C.HOOKS.read_text(encoding="utf-8").count("Pourquoi vos vidéos décrochent"), 1)   # jamais deux fois la même formule

    def test_a_blanc_n_ecrit_rien(self):
        self.urls = []
        with redirect_stdout(io.StringIO()): V.cmd_jour(self.conf(veille_requetes=["a"]), "2026-11-16", True, ouvrir=self.ouvrir)
        self.assertFalse(C.VEILLE.exists()); self.assertFalse(C.HOOKS.exists())


class FauxQwen:
    def __init__(self, reponses): self.reponses = list(reponses); self.consignes = []
    def chat(self, systeme, *a, **k): self.consignes.append(systeme); return json.dumps(self.reponses.pop(0), ensure_ascii=False)
    def __enter__(self): return self
    def __exit__(self, *a): return False


class Scripts(Base):
    def test_garde_fous(self):
        c = self.conf()
        self.assertEqual(S.verifier(BON, "A", [], c), [])
        for champ, valeur, attendu in (("titre", "Trois clients en plus", "nombre"), ("legende", "Des clients garantis.", "formulation"),
                                       ("scenes", ["La caméra montre un artisan."] + BON["scenes"][1:], "mise en scène"),
                                       ("legende", "Comme me l'a dit un client : m'a dit merci.", "formulation"), ("titre", "Gagnez 15 %", "nombre"),
                                       ("titre", "Une page web booste vos ventes", "formulation"), ("legende", "Vous gagnez en confiance.", "formulation"),
                                       ("legende", "Dans cette vidéo, on parle des horaires.", "molle")):
            x = dict(BON, **{champ: valeur})
            self.assertTrue(any(attendu in p for p in S.verifier(x, "A", [], c)), (champ, valeur))
        self.assertTrue(any("facile" in p for p in S.verifier(dict(BON, legende="Un travail facile."), "B", [], c)))
        self.assertTrue(any("lieu" in p for p in S.verifier(dict(BON, legende="Des appels depuis Caen."), "B", [], c)))
        self.assertTrue(any("revenu" in p.lower() or "formulation" in p for p in S.verifier(dict(BON, legende="Un revenu chaque mois."), "B", [], c)))
        self.assertIn("sujet déjà traité", S.verifier(BON, "A", [{"sujet": BON["sujet"], "titre": "autre"}], c))
        self.assertTrue(any("longueur" in p for p in S.verifier(dict(BON, scenes=["Vos horaires ?", "Une page claire.", "Un bouton Appeler.", "Votre adresse visible."]), "A", [], c)))

    def test_ligne_b_produite_sans_lien_et_commission_de_la_config(self):
        self.assertEqual(S.serie_du_passage(self.conf(lien_candidature=""), "14:00"), "B")
        c = self.conf(); f = S.fin("B", c)
        self.assertIn("une commission", f); self.assertNotRegex(f, r"\d|%"); self.assertIn("lien en bio", f); self.assertTrue(f.rstrip().endswith("?"))   # fin en boucle
        self.assertNotIn("Normandie", S.systeme("B", c, C.regles())); self.assertIn("aucun chiffre", S.systeme("B", c, C.regles()).lower())
        c["lignes"]["B"]["taux_commission"] = "15 %"
        self.assertIn("15 % de commission", S.fin("B", c)); self.assertIn("(15 % sur chaque vente)", S.legende("B", BON, c))
        c["lignes"]["B"]["taux_commission"] = ""; leg = S.legende("B", BON, c)
        self.assertIn("À la commission", leg); self.assertNotIn("%", leg); self.assertIn(C.MENTION_IA, leg)

    def test_ecrit_le_script_et_la_liste_des_sujets(self):
        mauvais = dict(BON, titre="Le meilleur site en 3 jours")
        q = FauxQwen([mauvais, BON])
        with redirect_stdout(io.StringIO()): f = S.ecrire_script(self.conf(), "2026-11-16", "06:00", q, [], False)
        doc = json.loads(f.read_text(encoding="utf-8"))
        self.assertEqual(doc["scenes"][-1], S.SERIES["A"]["fin"]); self.assertIn(C.MENTION_IA, doc["legende"])
        self.assertIn("aucun chiffre", q.consignes[0].lower())   # règles du skill injectées dans les consignes de Qwen
        self.assertEqual(json.loads(C.SUJETS.read_text(encoding="utf-8"))[0]["sujet"], BON["sujet"])
        self.assertTrue(20 <= doc["mots"] / 2.6 <= 35, doc["mots"])                # ~2,6 mots par seconde : 20 à 35 s
        with redirect_stdout(io.StringIO()):                                        # même sujet le lendemain : refusé
            self.assertIsNone(S.ecrire_script(self.conf(), "2026-11-17", "06:00", FauxQwen([BON] * 4), json.loads(C.SUJETS.read_text(encoding="utf-8")), False))


class Marketing(Base):
    def test_grille(self):
        c = self.conf()
        n_bon, _ = MK.noter_accroche("Vos horaires, vraiment visibles ?", "A", c)
        n_long, _ = MK.noter_accroche("Une page web permet aux clients de trouver les horaires de la boutique facilement le soir", "A", c)
        self.assertGreater(n_bon, n_long); self.assertGreaterEqual(n_bon, 8)
        for t in ("Trois clients en plus ?", "Des clients garantis ?", "Découvrez comment.", "Dans cette vidéo on parle de vous ?"): self.assertEqual(MK.noter_accroche(t, "A", c)[0], 0, t)
        self.assertEqual(MK.noter_accroche("Tu appelles depuis Rouen ?", "B", c)[0], 0)
        self.assertGreater(MK.noter_accroche("Tu sais parler au téléphone ?", "B", c)[0], MK.noter_accroche("Vous savez parler au téléphone ?", "B", c)[0])
        n1, _ = MK.noter_accroche("Vos horaires, vraiment visibles ?", "A", c, ["Vos horaires vraiment visibles"])
        self.assertEqual(n1, n_bon - 1)                                              # pas neuve : -1
        best, notes = MK.choisir(["Vos horaires, vraiment visibles ?", "Bonjour, voici une page web pour vous", "Une page en 3 clics ?"], "A", c, [])
        self.assertEqual(best, "Vos horaires, vraiment visibles ?"); self.assertEqual(len(notes), 3)

    def test_couper_et_sous_titres(self):
        self.assertEqual(MK.couper("Court et net."), ["Court et net."])
        a, b = MK.couper("Il cherche votre nom sur son téléphone, et il ne trouve aucune réponse claire")
        self.assertTrue(4 <= len(a.split()) <= 11 and 4 <= len(b.split()) <= 11, (a, b))
        g = C.decouper_sous_titres("Tu appelles de chez toi, tu décroches des rendez-vous, tu touches une commission.")
        self.assertTrue(all(2 <= len(x["mots"]) <= 4 for x in g), g)
        self.assertEqual(" ".join(m for x in g for m in x["mots"]), "Tu appelles de chez toi, tu décroches des rendez-vous, tu touches une commission.")
        self.assertTrue(all(x["cle"] >= 0 for x in g)); self.assertEqual(g[0]["mots"][g[0]["cle"]], "appelles")

    def test_retravaille_le_script_et_ecrit_le_csv(self):
        C.SCRIPTS.mkdir()
        doc = {"jour": "2026-11-16", "passage": "14:00", "serie": "B", "accroche": "Découvrez comment.", "sujet": "décrocher un rendez-vous",
               "scenes": ["Tu veux un travail depuis chez toi ?", "Tu appelles des artisans avec une liste et un script déjà prêts pour toi, sans chercher.",
                          "Ton rôle : décrocher un rendez-vous.", S.fin("B", self.conf())]}
        (C.SCRIPTS / "2026-11-16-1400.json").write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        q = FauxQwen([{"accroches": ["Tu sais décrocher un téléphone ?", "Un revenu de 2000 euros ?", "Bonjour à tous, voici une offre"]}])
        with redirect_stdout(io.StringIO()): code = MK.traiter(self.conf(), "2026-11-16", ["14:00"], ollama_cls=lambda m: q)
        self.assertEqual(code, 0)
        d = json.loads((C.SCRIPTS / "2026-11-16-1400.json").read_text(encoding="utf-8"))
        m = d["marketing"]; self.assertEqual(len(m["accroches"]), 4)                 # 3 de Qwen + le brouillon de Liam
        self.assertIn(m["gardee"], ("Tu sais décrocher un téléphone ?", "Tu sais parler au téléphone ?")); self.assertEqual(d["scenes"][0], m["gardee"])
        self.assertEqual([a["note"] for a in m["accroches"] if "2000" in a["texte"]], [0])
        self.assertGreater(len(d["scenes"]), len(doc["scenes"]))                    # phrase longue coupée en deux
        self.assertEqual(d["scenes"][-1], doc["scenes"][-1]); self.assertNotEqual(d["accroche"], "Découvrez comment.")
        self.assertEqual(len(d["sous_titres"]), len(d["scenes"]))
        lignes = self.csv(); self.assertEqual(len(lignes), 1)
        self.assertEqual((lignes[0]["agent"], lignes[0]["video"], lignes[0]["ligne"], lignes[0]["hook"]), ("videos-marketing", "2026-11-16-1400", "B", m["gardee"]))
        self.assertIn("note", lignes[0]["detail"])
        with redirect_stdout(io.StringIO()): MK.traiter(self.conf(), "2026-11-16", ["14:00"], ollama_cls=lambda m: FauxQwen([]))   # déjà fait : Qwen pas rappelé
        self.assertEqual(len(self.csv()), 1)


class Creation(Base):
    def test_entree_et_filtre(self):
        doc = {"jour": "2026-11-16", "passage": "22:00", "scenes": BON["scenes"]}
        e = K.entree_outil(doc, self.conf())
        self.assertEqual((e["format"], e["dark_mode"], e["title"]), ("portrait", True, "2026-11-16-2200")); self.assertTrue(e["voice"].startswith("fr-FR"))
        f = K.filtre_final("A", True, self.conf())
        for morceau in ("subtitles=sous-titres.ass", "accroche.txt", "lt(t,2.5)", "ia.txt", "fin0.txt", "concat=n=2"): self.assertIn(morceau, f)
        self.assertNotIn("subtitles=", K.filtre_final("B", False, self.conf()))
        self.assertEqual(K.passage_proche(datetime(2026, 11, 16, 6, 3)), "06:00"); self.assertEqual(K.passage_proche(datetime(2026, 11, 16, 21, 50)), "22:00")
        self.assertLess(K.IA_Y, 1500)                                                # mention IA au-dessus de l'interface du bas de TikTok

    def test_fin_ligne_b_sans_taux_invente(self):
        c = self.conf(); self.assertEqual(K.fins("B", c)[0], "À la commission, sans fixe"); self.assertFalse(any("%" in x for x in K.fins("B", c)))
        c["lignes"]["B"]["taux_commission"] = "20 %"; self.assertEqual(K.fins("B", c)[0], "Commission 20 %, sans fixe")

    def test_sous_titres_mot_a_mot(self):
        scenes = ["Tu sais parler au téléphone ?", "Liste et script fournis."]
        t = K.temps_mots(scenes, [2.0, 1.5], edge=lambda *a: [])                   # edge-tts absent : répartition selon la longueur des mots
        self.assertEqual([len(x) for x in t], [5, 4]); self.assertAlmostEqual(t[1][0][0], 2.0 + 0.045, places=2)
        self.assertTrue(all(a < b for x in t for a, b in x)); self.assertLessEqual(t[1][-1][1], 3.5)
        faux = lambda p, v: [(0.1 + 0.5 * i, 0.5 + 0.5 * i) for i in range(len(C.mots_de(p)))]   # temps edge-tts trop longs : recalés sur la durée réelle
        t2 = K.temps_mots(scenes, [2.0, 1.5], edge=faux)
        self.assertLessEqual(t2[0][-1][1], 2.0 + 1e-9); self.assertGreaterEqual(t2[1][0][0], 2.0)
        ass = K.sous_titres_ass({"scenes": scenes}, t2)
        self.assertIn("PlayResY: 1920", ass); self.assertIn(f",{K.ST_MARGE_G},{K.ST_MARGE_D},{1920 - K.ST_BAS},", ass); self.assertIn(K.ACCENT_ASS, ass)
        dial = [l for l in ass.splitlines() if l.startswith("Dialogue:")]
        self.assertTrue(2 <= len(dial) <= 4, dial)                                   # groupes de 2 à 4 mots
        self.assertIn("téléphone ?", ass)                                       # le « ? » reste collé à son mot
        self.assertLessEqual(1080 - K.ST_MARGE_D, 900); self.assertLessEqual(K.ST_BAS, 1500)   # zone sûre : ni boutons à droite, ni interface du bas

    def test_sans_script_rien_n_est_rendu(self):
        with redirect_stdout(io.StringIO()): self.assertEqual(K.fabriquer(self.conf(), "2026-11-16", "06:00"), 2)
        self.assertFalse(C.A_VALIDER.exists())


class Publication(Base):
    def video(self, nom="2026-11-16-0600", serie="A"):
        C.A_VALIDER.mkdir(exist_ok=True)
        (C.A_VALIDER / f"{nom}.mp4").write_bytes(b"x"); (C.A_VALIDER / f"{nom}.txt").write_text(f"Titre\n\n{C.MENTION_IA}", encoding="utf-8")
        (C.A_VALIDER / f"{nom}.json").write_text(json.dumps({"titre": "Titre", "contenu_ia": True, "serie": serie, "hook": "Vos horaires ?"}), encoding="utf-8")

    def lancer(self, maintenant, publieur, go=(), essai_fait=True, essai=False, ligne=None, garde=lambda t: True):
        self.alertes = []
        base = C.cfg
        def cfg():
            c = base()
            for l in go: c["lignes"][l]["go_publier"] = True
            return c
        C.cfg = cfg
        if essai_fait:
            e = C.etat_lire(P.AGENT, P.ETAT_DEFAUT); e["essais"] = {"A": "2026-11-15 10:00", "B": "2026-11-15 10:00"}; C.etat_ecrire(P.AGENT, e)
        try:
            with redirect_stdout(io.StringIO()): return P.cmd_publier(False, maintenant, ligne=ligne, essai=essai, publieur=publieur, alerter=self.alertes.append, garde=garde)
        finally: C.cfg = base

    def test_fermee_sans_go_publier(self):
        self.assertFalse(any(l.get("go_publier") for l in json.loads(self.ancien["CONFIG"].read_text(encoding="utf-8"))["lignes"].values()))
        self.video(); appels = []
        self.assertEqual(self.lancer(datetime(2026, 11, 16, 6, 0), lambda *a: appels.append(a)), 4)
        self.assertEqual(appels, []); self.assertTrue((C.A_VALIDER / "2026-11-16-0600.mp4").exists())
        self.video("2026-11-16-1400", "B")                                           # go de A seulement : la ligne B reste fermée
        self.assertEqual(self.lancer(datetime(2026, 11, 16, 14, 5), lambda *a: appels.append(a), go=("A",)), 4); self.assertEqual(appels, [])

    def test_essai_obligatoire_puis_essai_sans_clic(self):
        self.video(); appels = []
        self.assertEqual(self.lancer(datetime(2026, 11, 16, 6, 0), lambda *a: appels.append(a), go=("A",), essai_fait=False), 4)
        self.assertEqual(appels, [])
        self.assertEqual(self.lancer(datetime(2026, 11, 16, 10, 0), lambda *a: appels.append(a) or "essai", essai_fait=False, essai=True, ligne="A"), 0)
        self.assertEqual(appels[0][-1], True)                                        # publieur appelé en mode essai
        self.assertTrue((C.A_VALIDER / "2026-11-16-0600.mp4").exists())             # rien publié, rien déplacé
        self.assertTrue(C.etat_lire(P.AGENT, P.ETAT_DEFAUT)["essais"].get("A"))
        self.assertEqual(self.csv()[-1]["statut"], "essai réussi (rien publié)")

    def test_blocages_detectes(self):
        for t in ("Faites glisser le curseur pour terminer le puzzle", "Vérification de sécurité", "Too many attempts. Try again later", "Avertissement : violation",
                  "Saisissez le code de vérification"):
            self.assertIsNotNone(P.blocage(t), t)
        self.assertIsNotNone(P.blocage("", "https://www.tiktok.com/login?redirect=x"))
        self.assertIsNone(P.blocage("Téléverser une vidéo", "https://www.tiktok.com/tiktokstudio/upload"))

    def test_captcha_arret_alerte_et_rien_d_autre_ce_jour(self):
        self.video()
        def captcha(*a): raise P.Arret("« captcha » affiché par TikTok")
        self.assertEqual(self.lancer(datetime(2026, 11, 16, 6, 5), captcha, go=("A",)), 1)
        self.assertTrue(self.alertes and "arrêtée" in self.alertes[0]); self.assertTrue((C.A_VALIDER / "2026-11-16-0600.mp4").exists())
        self.assertEqual(self.csv()[-1]["statut"], "arrêt"); self.assertEqual(self.csv()[-1]["hook"], "Vos horaires ?")
        self.assertFalse(P.VERROU.exists())
        appels = []
        self.assertEqual(self.lancer(datetime(2026, 11, 16, 22, 0), lambda *a: appels.append(a), go=("A",)), 4)
        self.assertEqual(appels, [])
        def plante(*a): raise RuntimeError("interface")
        self.assertEqual(self.lancer(datetime(2026, 11, 17, 6, 0), plante, go=("A",)), 1)   # erreur inattendue = arrêt aussi

    def test_publie_deplace_plafonne_et_journalise(self):
        for n in ("a", "b", "c", "d"): self.video(f"2026-11-16-{n}")
        ok = lambda *a: "https://www.tiktok.com/tiktokstudio/content"
        c = C.cfg(); c["series_par_passage"] = {"06:00": "A", "14:00": "A", "22:00": "A"}
        base = C.cfg; C.cfg = lambda: json.loads(json.dumps(c))
        try:
            for h in (5, 13, 22): self.assertEqual(self.lancer(datetime(2026, 11, 16, h, 50 if h != 22 else 10), ok, go=("A",)), 0)
            self.assertEqual(len(list(C.PUBLIEES.glob("*.mp4"))), 3); self.assertTrue(all("étiquette IA" in a for a in self.alertes))
            self.assertEqual(self.lancer(datetime(2026, 11, 16, 22, 20), ok, go=("A",)), 0)   # passage déjà fait / plafond
            self.assertEqual(len(list(C.PUBLIEES.glob("*.mp4"))), 3)
            self.assertEqual(self.lancer(datetime(2026, 11, 17, 10, 0), ok, go=("A",)), 0)    # hors des heures prévues
            self.assertEqual(len(list(C.A_VALIDER.glob("*.mp4"))), 1)
        finally: C.cfg = base
        pub = [l for l in self.csv() if l["statut"] == "publié"]
        self.assertEqual(len(pub), 3); self.assertTrue(all(l["compte"] and l["hook"] == "Vos horaires ?" for l in pub))

    def test_stop_verrou_garde_et_mention_ia(self):
        self.video(); appels = []
        (self.r / "STOP").write_text("", encoding="utf-8")
        self.assertEqual(self.lancer(datetime(2026, 11, 16, 6, 0), lambda *a: appels.append(a), go=("A",)), 4)
        (self.r / "STOP").unlink(); P.VERROU.write_text("1", encoding="utf-8")       # une autre publication en cours
        self.assertEqual(self.lancer(datetime(2026, 11, 16, 6, 0), lambda *a: appels.append(a), go=("A",)), 0); P.VERROU.unlink()
        self.assertEqual(self.lancer(datetime(2026, 11, 16, 6, 0), lambda *a: appels.append(a), go=("A",), garde=lambda t: False), 4)
        (C.A_VALIDER / "2026-11-16-0600.txt").write_text("Titre sans mention", encoding="utf-8")
        self.assertIsNone(P.prochaine_video("A")); self.assertEqual(appels, [])


class Nettoyage(Base):
    def test_supprime_vieux_fichiers_seulement(self):
        jarvis = self.r / "jarvis"; vid = jarvis / "Videos"; (jarvis / "B2B" / "agents").mkdir(parents=True)
        (jarvis / "B2B" / "agents" / "b2b.local.json").write_text(json.dumps({"machine_active": os.environ.get("COMPUTERNAME", "")}), encoding="utf-8")
        shutil.copytree(AG.parent / "agents", vid / "agents", ignore=shutil.ignore_patterns("__pycache__"))
        for f in ("videos-config.json", "SKILL-VIDEOS.md", "hooks-base.md"): shutil.copy2(AG.parent / f, vid / f)
        vieux = time.time() - 20 * 86400; recent = time.time() - 2 * 86400
        def fichier(rel, age, contenu="x"):
            p = vid / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(contenu, encoding="utf-8"); os.utime(p, (age, age)); return p
        a = fichier("a-valider/2026-10-01-0600.mp4", vieux); fichier("a-valider/2026-10-01-0600.json", vieux, json.dumps({"hook": "Vos horaires ?", "serie": "A"}))
        fichier("a-valider/2026-10-01-0600.txt", vieux)
        neuf = fichier("a-valider/2026-11-15-0600.mp4", recent); prot = fichier("a-valider/2026-11-16-2200.mp4", vieux)
        inter = [fichier("travail/2026-10-01-0600/corps.mp4", vieux), fichier("outils/stickfigure-pipeline-v2/output/audio/scene_001.mp3", vieux),
                 fichier("outils/stickfigure-pipeline-v2/output/frames/f1.png", vieux)]
        gardes = [fichier("scripts/2026-10-01-0600.json", vieux), fichier("veille/2026-10-25.md", vieux), fichier("outils/stickfigure-pipeline-v2/node_modules/x/demo.mp4", vieux),
                  fichier("publiees/notes.md", vieux), vid / "SKILL-VIDEOS.md", vid / "videos-config.json"]
        os.utime(vid / "SKILL-VIDEOS.md", (vieux, vieux))
        ps = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(vid / "agents" / "nettoyage.ps1")]
        env = {**os.environ, "JARVIS_TEST": "1"}
        s = subprocess.run(ps + ["-Simulation"], capture_output=True, text=True, timeout=120, env=env)
        self.assertEqual(s.returncode, 0, s.stdout + s.stderr); self.assertTrue(a.exists()); self.assertFalse((vid / "journal-videos.csv").exists())
        p = subprocess.run(ps, capture_output=True, text=True, timeout=120, env=env)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertFalse(a.exists()); self.assertFalse(a.with_suffix(".txt").exists()); self.assertFalse(a.with_suffix(".json").exists())
        self.assertTrue(all(not f.exists() for f in inter), [str(f) for f in inter if f.exists()])
        self.assertTrue(neuf.exists() and prot.exists()); self.assertTrue(all(f.exists() for f in gardes), [str(f) for f in gardes if not f.exists()])
        with (vid / "journal-videos.csv").open(encoding="utf-8-sig", newline="") as f: lignes = list(csv.DictReader(f, delimiter=";"))
        v = [l for l in lignes if l["video"] == "2026-10-01-0600"]
        self.assertEqual(len(v), 1); self.assertEqual((v[0]["hook"], v[0]["ligne"]), ("Vos horaires ?", "A")); self.assertIn("supprimée", v[0]["statut"])
        self.assertTrue(any("intermédiaires" in l["statut"] for l in lignes))
        self.assertTrue(all(p.parent == vid for p in vid.glob("*.csv")))
        (jarvis / "B2B" / "agents" / "b2b.local.json").write_text(json.dumps({"machine_active": "UNE-AUTRE-MACHINE"}), encoding="utf-8")
        self.assertEqual(subprocess.run(ps, capture_output=True, text=True, timeout=120, env=env).returncode, 3)   # machine non active : refus


if __name__ == "__main__":
    unittest.main(verbosity=1)
