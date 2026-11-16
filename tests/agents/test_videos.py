#!/usr/bin/env python3
"""Harness - équipe Vidéos TikTok (16/11/2026) : règles (SKILL-VIDEOS.md relu, sections obligatoires), veille (flux RSS fictif, rien de TikTok, purge, hooks.md),
scripts (garde-fous : chiffres, promesses, phrases molles, lieux sur la ligne B, mise en scène, sujet déjà traité ; taux de commission seulement depuis la config),
marketing (grille des accroches, 3 accroches notées, rythme, sous-titres, journal-videos.csv), création (sous-titres mot à mot en .ass dans la zone sûre, carte de fin),
publication (fermée sans « go publier » par ligne, essai obligatoire, captcha = arrêt + alerte, plafond par compte, STOP, verrou, CSV ; TikTok remplacé par un bouchon),
nettoyage (nettoyage.ps1 dans un dossier temporaire : vieux .mp4 et intermédiaires supprimés, ligne CSV avant, skill / scripts / veille / vidéos protégées intacts),
voix (edge-tts simulé en échec -> bascule Kokoro, moteur dans la colonne tts ; vrai Kokoro local sur une phrase si le modèle est là, sans aucun son joué),
formules d'accroche à trous (hooks-base.md, bon public par ligne), correctif Windows de stick-stage (sur une copie, puis vérification de l'outil réel s'il est cloné).
ligne B en sketch à deux (sketches-base.json : schéma, 10 mots par réplique, 40/40/20 %, jamais rejoué avant 20 vidéos, Qwen limité aux listes, 3 fins, interdits),
voix par personnage, agent monteur (plans de 3 s au plus, durée prévue, sous-titres en zone sûre, contrôle qualité, mise à part après 3 essais),
rendu stick-stage (skit construit, débuts des répliques), sous-titres sans mot perdu ni doublé, journal CSV migré vers les colonnes de suivi.
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
VX = charger("voix"); sys.modules["voix"] = VX
SK = charger("sketches"); sys.modules["sketches"] = SK
RS = charger("rendu_stickstage"); sys.modules["rendu_stickstage"] = RS
MT = charger("monteur"); sys.modules["monteur"] = MT
MK, K, P = charger("marketing"), charger("creation"), charger("publication")
for m in (V, S, MK, K, P, VX, SK, RS, MT): m.C = C
K.RS = RS; K.MT = MT; MT.RS = RS
K.VX = VX
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
        self.assertIn("Formules ligne A", h); self.assertIn("Pourquoi vos vidéos décrochent", h); self.assertNotIn("Format court qui marche", h)
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
        # bon public : A parle à l'artisan (jamais à son client, jamais en tutoyant) ; B tutoie le futur call caller ; jamais d'adresse épelée
        mauvais_a = dict(BON, scenes=["Trouvez les horaires de votre artisan."] + BON["scenes"][1:])
        self.assertTrue(any("mauvais public" in p for p in S.verifier(mauvais_a, "A", [], c)))
        self.assertTrue(any("mauvais public" in p for p in S.verifier(dict(BON, accroche="Tu cherches ?"), "A", [], c)))
        self.assertTrue(any("mauvais public" in p for p in S.verifier(BON, "B", [], c)))          # BON vouvoie : refusé sur la ligne B
        self.assertTrue(any("adresse" in p for p in S.verifier(dict(BON, legende="Tout est sur www point monsite."), "A", [], c)))
        self.assertIsNone(S.public_faux("Tu lui dis : « Vous avez un site ? »", "B"))        # une parole citée ne compte pas
        self.assertTrue(any("mauvais public" in p for p in S.verifier(dict(BON, sujet="Obtenir vite les numéros de téléphone d'artisans"), "A", [], c)))   # point de vue du client
        self.assertIsNone(S.public_faux("Un client qui cherche un artisan tombe sur votre page.", "A"))

    def test_ligne_b_produite_sans_lien_et_commission_de_la_config(self):
        self.assertEqual(S.serie_du_passage(self.conf(lien_candidature=""), "14:00"), "B")
        c = self.conf(); f = S.fin("B", c)
        self.assertIn("à la commission", f); self.assertNotRegex(f, r"\d|%"); self.assertIsNone(S.ADRESSE.search(f)); self.assertIn("lien en bio", f); self.assertTrue(f.rstrip().endswith("?"))   # fin en boucle
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
            self.assertIsNone(S.ecrire_script(self.conf(), "2026-11-17", "06:00", FauxQwen([BON] * 6), json.loads(C.SUJETS.read_text(encoding="utf-8")), False))


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
        q = FauxQwen([{"choix": [{"id": "B03", "trous": {"quoi": "la prise de rendez-vous"}}, {"id": "B04", "trous": {"erreur": "viser 2000 euros"}},
                                 {"id": "Z99", "trous": {}}, {"id": "B05", "trous": {"action": "un deux trois quatre cinq"}}]}])
        with redirect_stdout(io.StringIO()): code = MK.traiter(self.conf(), "2026-11-16", ["14:00"], ollama_cls=lambda m: q)
        self.assertEqual(code, 0)
        d = json.loads((C.SCRIPTS / "2026-11-16-1400.json").read_text(encoding="utf-8"))
        m = d["marketing"]; textes = [a["texte"] for a in m["accroches"]]
        self.assertEqual(len(textes), len(set(textes))); self.assertIn(len(textes), (3, 4))       # 3 formules (+ le brouillon de Liam s'il est différent)
        self.assertIn("Personne ne te dit ça sur la prise de rendez-vous.", textes)                  # trou rempli, formule inchangée
        self.assertTrue(all(a["formule"] in ("brouillon de Liam",) or a["formule"].startswith("B") for a in m["accroches"]))   # jamais inventée ; Z99 et trou de 5 mots rejetés
        self.assertEqual([a["note"] for a in m["accroches"] if "2000" in a["texte"]], [0]); self.assertEqual(d["scenes"][0], m["gardee"])
        self.assertTrue(m["formule"].startswith("B") or m["formule"] == "brouillon de Liam")
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
        self.assertNotIn("reuse_audio_from", e); self.assertEqual(K.entree_outil(doc, self.conf(), self.r / "voix")["reuse_audio_from"], str(self.r / "voix"))
        f = K.filtre_final("A", True, self.conf())
        for morceau in ("subtitles=sous-titres.ass", "accroche.txt", "lt(t,2.5)", "ia.txt", "fin0.txt", "concat=n=2"): self.assertIn(morceau, f)
        self.assertNotIn("subtitles=", K.filtre_final("B", False, self.conf()))
        self.assertEqual(K.passage_proche(datetime(2026, 11, 16, 6, 3)), "06:00"); self.assertEqual(K.passage_proche(datetime(2026, 11, 16, 21, 50)), "22:00")
        self.assertLess(K.IA_Y, 1500)                                                # mention IA au-dessus de l'interface du bas de TikTok

    def test_accroche_ecran_dans_la_zone_sure(self):
        for texte in ("Fermé ou ouvert ? Votre client hésite.", "Votre client vous cherche", "Tu sais parler au téléphone ?", "Court"):
            t, taille = K.accroche_ecran(texte)
            lignes = t.split("\n"); self.assertLessEqual(len(lignes), 2)
            self.assertLessEqual(max(len(l) for l in lignes) * 0.6 * taille, K.ACCROCHE_LARGEUR + 1, texte)   # tient entre x = 120 et x = 900
            self.assertFalse(any(l.startswith(("?", " ")) for l in lignes)); self.assertEqual(t.replace("\n", " ").replace(" ", " "), " ".join(texte.split()))
        self.assertEqual(K.accroche_ecran("Court")[1], 92); self.assertIn("fontsize=60:", K.filtre_final("A", True, self.conf(), 60))

    def test_fin_ligne_b_sans_taux_invente(self):
        c = self.conf(); self.assertEqual(K.fins("B", c)[:2], ["On recrute des call callers", "À la commission"]); self.assertFalse(any("%" in x for x in K.fins("B", c)))
        self.assertIn("DM", K.fins("B", c)[2]); self.assertFalse(any("15" in x or "minutes" in x for x in K.fins("A", c)))   # ligne A : jamais de rendez-vous de 15 minutes
        c["lignes"]["B"]["taux_commission"] = "20 %"; self.assertEqual(K.fins("B", c)[1], "À la commission (20 %)")
        self.assertEqual((K.fin_s("A"), K.fin_s("B")), (3.0, 2.0)); self.assertNotIn("0x141414", K.FOND_FIN)   # jamais de fond noir plein

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


class Voix(Base):
    PHRASES = ["Votre client cherche vos horaires.", "Fermé ou ouvert ?"]

    def faux_kokoro(self, phrases, voix, dossier, vitesse=1.0, hauteur=1.0):
        self.kokoro_appele = (voix, vitesse); self.kokoro_hauteur = hauteur
        for i, _ in enumerate(phrases): VX.fichier_phrase(dossier, i).write_bytes(b"kokoro")

    def test_voix_fixe_par_ligne(self):
        c = self.conf(); a, b = VX.voix_ligne(c, "A"), VX.voix_ligne(c, "B")
        self.assertTrue(a["edge"].startswith("fr-FR") and b["edge"].startswith("fr-FR")); self.assertNotEqual(a["edge"], b["edge"])
        self.assertEqual(a["kokoro"], "ff_siwis")
        c["lignes"]["A"]["voix"] = {}; self.assertEqual(VX.voix_ligne(c, "A")["edge"], c["voix"])   # sans réglage : voix générale

    def test_edge_en_echec_bascule_sur_kokoro(self):
        os.environ["JARVIS_VIDEOS_EDGE_ECHEC"] = "1"
        try:
            with self.assertRaises(RuntimeError): VX.edge_synthese(self.PHRASES, "fr-FR-HenriNeural", self.r)   # échec simulé, aucun réseau
            r = VX.synthese(self.PHRASES, VX.voix_ligne(self.conf(), "B"), self.r / "voix", kokoro=self.faux_kokoro)
        finally: os.environ.pop("JARVIS_VIDEOS_EDGE_ECHEC", None)
        self.assertEqual(r["moteur"], "kokoro"); self.assertIn("edge-tts en échec", r["bascule"]); self.assertIsNone(r["temps"])
        self.assertEqual(self.kokoro_appele, ("ff_siwis", VX.voix_ligne(self.conf(), "B")["kokoro_vitesse"]))
        self.assertTrue(all(VX.fichier_phrase(self.r / "voix", i).read_bytes() == b"kokoro" for i in range(2)))

    def test_edge_trop_lent_ou_incomplet(self):
        import asyncio
        def lent(*a): raise asyncio.TimeoutError()
        r = VX.synthese(self.PHRASES, VX.voix_ligne(self.conf(), "A"), self.r / "v1", edge=lent, kokoro=self.faux_kokoro)
        self.assertEqual((r["moteur"], r["bascule"]), ("kokoro", f"edge-tts en échec (plus de {VX.EDGE_DELAI_S} s)"))
        def moitie(phrases, voix, dossier, delai):   # une phrase sans son : aucun mélange, toute la vidéo passe sur Kokoro
            VX.fichier_phrase(dossier, 0).write_bytes(b"edge"); return [[(0.0, 0.5)]]
        r = VX.synthese(self.PHRASES, VX.voix_ligne(self.conf(), "A"), self.r / "v2", edge=moitie, kokoro=self.faux_kokoro)
        self.assertEqual(r["moteur"], "kokoro"); self.assertEqual(VX.fichier_phrase(self.r / "v2", 0).read_bytes(), b"kokoro")
        def ok(phrases, voix, dossier, delai):
            for i, _ in enumerate(phrases): VX.fichier_phrase(dossier, i).write_bytes(b"edge")
            return [[(0.0, 0.4)], [(0.0, 0.3)]]
        r = VX.synthese(self.PHRASES, VX.voix_ligne(self.conf(), "A"), self.r / "v3", edge=ok, kokoro=self.faux_kokoro)
        self.assertEqual((r["moteur"], r["bascule"]), ("edge-tts", ""));
        def panne(*a): raise RuntimeError("modèle absent")
        with self.assertRaises(RuntimeError): VX.synthese(self.PHRASES, VX.voix_ligne(self.conf(), "A"), self.r / "v4", edge=lent, kokoro=panne)

    def test_csv_colonne_tts_et_path_sans_edge(self):
        C.csv_ligne("videos-creation", "2026-11-16-0600", "A", "compte", "à valider", "Fermé ou ouvert ?", "24 s", tts="kokoro")
        self.assertEqual(self.csv()[0]["tts"], "kokoro"); self.assertEqual(C.CSV_COLONNES[8], "tts")
        avec = self.r / "scripts-py"; avec.mkdir(); (avec / "edge-tts.exe").write_bytes(b""); sans = self.r / "bin"; sans.mkdir()
        self.assertEqual(VX.chemin_sans_edge(os.pathsep.join([str(avec), str(sans)])), str(sans))

    @unittest.skipUnless(Path(str(charger("voix").KOKORO_MODELE)).exists(), "modèle Kokoro absent (Videos\\outils\\kokoro)")
    def test_vrai_kokoro_local(self):
        os.environ["JARVIS_VIDEOS_EDGE_ECHEC"] = "1"
        try: r = VX.synthese(["Fermé ou ouvert ?"], VX.voix_ligne(self.conf(), "A"), self.r / "vrai")
        finally: os.environ.pop("JARVIS_VIDEOS_EDGE_ECHEC", None)
        f = VX.fichier_phrase(self.r / "vrai", 0)
        self.assertEqual(r["moteur"], "kokoro"); self.assertGreater(f.stat().st_size, 2000)   # vrai mp3 écrit sur le disque, jamais joué
        self.assertGreater(K.duree(f), 0.5)


class Formules(Base):
    def test_bibliotheque_a_trous(self):
        base = C.HOOKS_BASE.read_text(encoding="utf-8")
        for serie in ("A", "B"):
            f = MK.formules(serie, base); ids = [i for i, _ in f]
            self.assertGreaterEqual(len(f), 10); self.assertEqual(len(ids), len(set(ids)))
            self.assertGreaterEqual(sum(not MK.TROU.search(x) for _, x in f), 3)               # toujours 3 accroches possibles sans Qwen
            self.assertTrue(MK.trous_aide(serie, base).startswith("Trous"))
            for i, x in f:                                                                      # chaque formule, trous remplis, passe les garde-fous de sa ligne
                texte = MK.remplir(x, {n: "vos horaires" if serie == "A" else "les appels" for n in MK.TROU.findall(x)})
                self.assertIsNone(MK.elimine(texte, serie, self.conf()), (i, texte))
                self.assertNotRegex(texte.lower(), r"découvrez|comment\b")
        self.assertEqual(MK.remplir("Votre client cherche {quoi}.", {"quoi": " vos horaires. "}), "Votre client cherche vos horaires.")
        self.assertEqual(MK.remplir("{quand}, on cherche.", {"quand": "le dimanche soir"}), "Le dimanche soir, on cherche.")
        self.assertIsNone(MK.remplir("Votre client cherche {quoi}.", {"quoi": "un deux trois quatre cinq"}))   # plus de 4 mots
        self.assertIsNone(MK.remplir("Votre client cherche {quoi}.", {}))

    def test_sans_reponse_de_qwen_des_formules_sans_trou(self):
        doc = {"jour": "2026-11-16", "passage": "06:00", "serie": "A", "sujet": "horaires", "scenes": ["x", "y"]}
        out = MK.demander_accroches(FauxQwen([{"rien": 1}]), doc, "A", self.conf(), C.regles(), (), "graine")
        self.assertEqual(len(out), 3); self.assertTrue(all(i.startswith("A") and not MK.TROU.search(t) for t, i in out))
        self.assertTrue(all(MK.noter_accroche(t, "A", self.conf())[0] > 0 for t, _ in out))
        self.assertEqual(MK.noter_accroche("Découvrez comment.", "A", self.conf())[0], 0)
        self.assertEqual(MK.noter_accroche("Tu sais parler au téléphone ?", "A", self.conf())[0], 0)   # mauvais public sur A
        self.assertEqual(MK.noter_accroche("Vous savez parler au téléphone ?", "B", self.conf())[0], 0)


class StickStage(Base):
    CASSE = 'execFileSync(path.join(ws.root, "node_modules/.bin/remotion"), ["ffmpeg", "-y", ...args], { stdio: "inherit" });'

    def test_correctif_windows(self):
        sp = importlib.util.spec_from_file_location("stick_stage_windows", AG.parent / "correctifs" / "stick-stage-windows.py")
        W = importlib.util.module_from_spec(sp); sp.loader.exec_module(W)
        neuf, n = W.corriger_texte(self.CASSE)
        self.assertEqual(n, 1); self.assertNotIn(".bin/remotion", neuf)
        self.assertIn('execFileSync(process.execPath, [path.join(ws.root, "node_modules/@remotion/cli/remotion-cli.js"), "ffmpeg"', neuf)
        self.assertEqual(W.corriger_texte(neuf), (neuf, 0))                                    # idempotent
        rh = 'execFileSync(bin, ["-q", "-f", "json", "--extendedShapes", "GHX", "-d", dialog, wav], { encoding: "utf8" });'   # Rhubarb muet avec -q sous Windows
        neuf, n = W.corriger_texte(rh); self.assertEqual(n, 1); self.assertIn('["-f", "json", "--extendedShapes"', neuf); self.assertEqual(W.corriger_texte(neuf)[1], 0)
        copie = self.r / "stick-stage"
        for rel in W.FICHIERS: (copie / rel).parent.mkdir(parents=True, exist_ok=True); (copie / rel).write_text(self.CASSE.replace("ws.root", "root"), encoding="utf-8")
        self.assertEqual(W.corriger(copie, verifier=True)[1], 3); self.assertEqual(W.corriger(copie)[0], 3); self.assertEqual(W.corriger(copie, verifier=True)[1], 0)
        reel = W.DOSSIER
        if (reel / "node_modules" / "@remotion" / "cli" / "remotion-cli.js").exists():      # outil cloné sur cette machine : corrigé, et le lanceur répond
            self.assertEqual(W.corriger(reel, verifier=True)[1], 0, "relancer python Videos\\correctifs\\stick-stage-windows.py")
            r = subprocess.run([shutil.which("node") or "node", str(reel / "node_modules" / "@remotion" / "cli" / "remotion-cli.js"), "ffmpeg", "-version"],
                               capture_output=True, text=True, timeout=120, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            self.assertEqual(r.returncode, 0, r.stderr[-300:]); self.assertIn("ffmpeg version", r.stdout)


class Sketches(Base):
    def setUp(self):
        super().setUp(); self.b = SK.lire()

    def sk(self, i): return json.loads(json.dumps(self.b["sketches"][i]))

    def test_base_valide_et_repartition(self):
        self.assertEqual(SK.verifier_base(self.b, self.conf(), S), []); self.assertEqual(len(self.b["sketches"]), 30); self.assertEqual(len(self.b["fins"]), 3)
        cats = [SK.categorie(s) for s in self.b["sketches"]]; self.assertEqual((cats.count("comedie"), cats.count("lecon"), cats.count("autre")), (12, 12, 6))
        long = {c: max(SK.liste_de(self.b, c, "libre"), key=SK.mots) for c in SK.CHAMPS}
        for s in self.b["sketches"]:
            self.assertTrue(6 <= len(s["repliques"]) <= 8, s["id"]); self.assertTrue(SK.champs_de(s), s["id"])
            self.assertTrue(all(SK.mots(SK.remplir(x["texte"], long)) <= 10 for x in s["repliques"]), s["id"])
        hist, seq = [], []
        for _ in range(40):
            s, vals, genre, origine = SK.choisir(None, hist, self.b); hist.append({"serie": "B", "sketch": s["id"]}); seq.append(s["id"])
            self.assertEqual(origine, "code"); self.assertTrue(SK.valeurs_valides(s, self.b, vals, genre))
        self.assertTrue(all(len(set(seq[i:i + 20])) == 20 for i in range(21)))        # aucun sketch rejoué dans les 20 dernières vidéos
        vingt = [SK.categorie(next(x for x in self.b["sketches"] if x["id"] == i)) for i in seq[:20]]
        self.assertEqual((vingt.count("lecon"), vingt.count("comedie"), vingt.count("autre")), (8, 8, 4))   # 40 / 40 / 20 %
        self.assertEqual({SK.fin_suivante([{"serie": "B", "sketch": "x"}] * n, self.b["fins"])[0] for n in range(3)}, {0, 1, 2})   # 3 fins tournantes

    def test_refus(self):
        c = self.conf(); s = self.sk(0)
        s["repliques"][0]["texte"] = "Un mot de trop dans cette phrase vraiment beaucoup trop longue pour Gérard."
        self.assertTrue(any("mots (10 au plus)" in p for p in SK.verifier_sketch(s, self.b, c, S)))
        for mauvais, quoi in (("Mon closer gagne bien.", "interdit"), ("Selon une étude, oui.", "interdit"), ("Trouve son numéro privé.", "interdit"),
                              ("On en vend trois par jour.", "nombre"), ("Comme dit Elon Musk.", "vraie personne"), ("Il parle de {prix}.", "champ inconnu")):
            s = self.sk(0); s["repliques"][1]["texte"] = mauvais
            self.assertTrue(any(quoi in p for p in SK.verifier_sketch(s, self.b, c, S)), mauvais)
        s = self.sk(0); s["repliques"] = [dict(x, qui="G") for x in s["repliques"]]; self.assertTrue(any("tous les deux" in p for p in SK.verifier_sketch(s, self.b, c, S)))
        s = self.sk(0); s["repliques"][0]["sfx"] = "musique-connue"; self.assertTrue(any("bruitage inconnu" in p for p in SK.verifier_sketch(s, self.b, c, S)))
        self.assertTrue(any("incomplète" in p for p in SK.verifier_fin(["On recrute des call callers.", "Lien en bio."], c, S)))
        self.assertTrue(any("lieu" in p for p in SK.verifier_fin(["Call callers à la commission, près de Rouen.", "Bio ou DM."], c, S)))
        self.assertTrue(any("public" in p for p in SK.verifier_fin(["Vous voulez être call caller, à la commission ?", "Bio ou DM."], c, S)))

    def test_qwen_limite_aux_listes(self):
        s = SK.candidates([], self.b["sketches"])[0]; champs = SK.champs_de(s)
        _, _, _, o = SK.choisir(FauxQwen([{"sketch": s["id"], "genre": "h", "valeurs": {x: "astronaute" for x in champs}}]), [], self.b)
        self.assertEqual(o, "code")                                                          # valeur hors des listes : refusée, choix du code
        bon = {x: SK.liste_de(self.b, x, "h")[0] for x in champs}
        s2, vals, genre, o = SK.choisir(FauxQwen([{"sketch": s["id"], "genre": "h", "valeurs": bon}]), [], self.b)
        self.assertEqual((s2["id"], o, vals, genre), (s["id"], "qwen", bon, "h"))

    def test_ecrit_le_script_b(self):
        with redirect_stdout(io.StringIO()): f = S.ecrire_script(self.conf(), "2026-11-17", "14:00", FauxQwen([{"rien": 1}]), [], False)
        doc = json.loads(f.read_text(encoding="utf-8"))
        self.assertEqual((doc["serie"], doc["format"], doc["variante"], doc["fin_variante"]), ("B", "sketch", "code", "FIN1"))
        self.assertEqual(len(doc["qui"]), len(doc["scenes"])); self.assertEqual(doc["qui"][-2:], ["G", "G"]); self.assertEqual(doc["scenes"][-2:], self.b["fins"][0])
        self.assertFalse(any("{" in x for x in doc["scenes"])); self.assertIn(C.MENTION_IA, doc["legende"])
        self.assertEqual(json.loads(C.SUJETS.read_text(encoding="utf-8"))[0]["sketch"], doc["sketch"])
        with redirect_stdout(io.StringIO()): MK.traiter(self.conf(), "2026-11-17", ["14:00"], ollama_cls=lambda m: FauxQwen([]))
        d = json.loads(f.read_text(encoding="utf-8")); self.assertEqual(d["marketing"]["gardee"], d["scenes"][0])
        self.assertTrue(all(1 <= len(g["mots"]) <= 3 for st in d["sous_titres"] for g in st))   # sous-titres : 1 à 3 mots
        l = self.csv()[-1]; self.assertEqual((l["histoire"], l["formule"], l["theme"], l["fin"], l["ligne"]), (doc["sketch"], doc["formule"], doc["theme"], "FIN1", "B"))


class Monteur(Base):
    def doc(self, i=0):
        b = SK.lire(); s = b["sketches"][i]; vals, g = SK.valeurs_par_defaut(s, b, 1)
        return SK.document(s, vals, g, 0, b["fins"][0], self.conf(), "2026-11-17", "14:00", "code")

    def tl(self, total, coupes, punch=()):
        return {"fps": 30, "durationInFrames": total, "scenes": [{"from": 0, "timeline": {
            "shots": [{"frame": f, "framing": "two"} for f in coupes], "punchIns": [{"frame": f, "on": "gerard"} for f in punch], "durationInFrames": total,
            "beats": [{"id": "n1", "from": 0, "to": total, "synthetic": False, "audioFrom": 0}]}}]}

    def test_skit_dialogue_et_voix(self):
        d = self.doc(11)   # T12 : sonnerie au début, bruitage du catalogue à la chute
        dur = [3.5 if i % 3 == 0 else 1.5 for i in range(len(d["scenes"]))]
        sk = RS.skit_dialogue(d, RS.decor(d["decor"]), dur)
        self.assertEqual([c["id"] for c in sk["cast"]], ["gerard", "inter"]); self.assertEqual(len(sk["characters"]), 2)
        self.assertEqual({b["speaker"] for b in sk["beats"]}, {"gerard", "inter"}); self.assertNotIn("narrator", sk)
        plans = [(b["shot"]["framing"], b["shot"].get("on")) if "shot" in b else None for b in sk["beats"]]   # None : la chute, cadrée par le réalisateur
        self.assertTrue(all(a != b for a, b in zip(plans, plans[1:]) if a and b))           # une coupe à chaque réplique
        self.assertTrue(all("punchIn" in b["shot"] for b, x in zip(sk["beats"], dur) if x > RS.PLAN_LONG_S and "shot" in b))   # réplique longue : zoom
        self.assertEqual(sk["beats"][0]["pauseBeforeMs"], RS.PAUSE_SONNERIE_MS)                # la sonnerie est mixée dans ce silence
        self.assertEqual(sk["beats"][d["punchline"]]["sfx"][0]["id"], "register"); self.assertNotIn("shot", sk["beats"][d["punchline"]])
        for i in d["fin_indices"]: self.assertEqual(sk["beats"][i]["actions"][0], {"who": "gerard", "do": "look", "to": "camera", "at": {"ms": 0}})
        v = VX.voix_dialogue(self.conf(), "f"); self.assertNotEqual(v["G"]["edge"], v["I"]["edge"]); self.assertEqual(v["I"]["edge"], "fr-FR-DeniseNeural")
        self.assertNotEqual(v["G"].get("kokoro_hauteur", 1.0), v["I"].get("kokoro_hauteur", 1.0))   # Kokoro : une seule voix, deux hauteurs
        self.assertNotEqual(VX.voix_dialogue(self.conf(), "h")["I"]["edge"], v["G"]["edge"])

    def test_plans_et_duree_prevue(self):
        self.assertEqual(MT.plans_trop_longs(self.tl(300, [0, 60, 120])), [(4.0, 10.0)])
        self.assertEqual(MT.plans_trop_longs(self.tl(300, [0, 60, 120], [180, 240])), [])
        d = self.r / "skit"; (d / "generated").mkdir(parents=True)
        (d / "skit.json").write_text(json.dumps({"beats": [{"id": "n1", "speaker": "gerard"}]}), encoding="utf-8")
        (d / "generated" / "timeline.json").write_text(json.dumps(self.tl(840, [0, 60])), encoding="utf-8")   # 28 s + carte : bonne durée, plan long
        self.assertTrue(MT.retoucher_plans(d)); self.assertIn("punchIn", json.loads((d / "skit.json").read_text(encoding="utf-8"))["beats"][0]["shot"])
        (d / "generated" / "timeline.json").write_text(json.dumps(self.tl(1200, list(range(0, 1200, 60)))), encoding="utf-8")   # 40 s : trop long
        self.assertTrue(MT.retoucher_plans(d)); self.assertEqual(json.loads((d / "skit.json").read_text(encoding="utf-8"))["style"], "snappy")
        self.assertTrue(MT.retoucher_plans(d)); self.assertEqual(json.loads((d / "skit.json").read_text(encoding="utf-8"))["style"], "argument")
        with self.assertRaises(MT.TropLong): MT.retoucher_plans(d)                            # même au rythme le plus serré : la voix sera accélérée avant le rendu

    def test_sous_titres_et_controle(self):
        d = self.doc(0); plan = [C.decouper_sous_titres(s, maxi=3, mini=1, car_max=16) for s in d["scenes"]]
        self.assertTrue(all(1 <= len(g["mots"]) <= 3 for p in plan for g in p))
        self.assertEqual(" ".join(m for p in plan for g in p for m in g["mots"]), " ".join(m for s in d["scenes"] for m in C.mots_de(s)))   # aucun mot perdu
        temps = K.temps_mots(d["scenes"], [2.0] * len(d["scenes"]), edge=lambda *a: [])
        ass = MT.sous_titres_ass(plan, temps); self.assertEqual(MT.controle_sous_titres(ass), []); self.assertIn("\\c&H00D7FF&", ass)
        self.assertTrue(MT.controle_sous_titres(ass.replace(",120,200,680,1", ",20,20,100,1")))   # hors zone sûre : refusé
        trop = MT.sous_titres_ass([[{"mots": ["anticonstitutionnellement"] * 3, "cle": 0}]], [[(0, 1)] * 3]); self.assertTrue(MT.controle_sous_titres(trop))
        self.assertEqual(MT.controle(30.0, [], [], {"ecart_db": 18.0}, []), [])
        pb = MT.controle(36.2, [(3.0, 3.5)], ["x"], {"ecart_db": 8.0}, [(1.0, 5.0)])
        for mot in ("durée", "noire", "x", "voix", "plan"): self.assertTrue(any(mot in p for p in pb), mot)
        self.assertEqual(MT.style_suivant("classic", ["durée 36.2 s"], 36.2), "snappy"); self.assertEqual(MT.style_suivant("classic", ["durée 22 s"], 22), "sitcom")
        import wave
        with wave.open(str(MT.sonnerie(self.r / "s.wav")), "rb") as w: self.assertAlmostEqual(w.getnframes() / w.getframerate(), MT.SONNERIE_S, places=2)

    def test_mise_a_part_apres_trois_essais(self):
        ancien, essais = (MT.A_PART, RS.rendre), []

        def rendre(*a, **k): essais.append(1); raise RuntimeError("rendu simulé en échec")
        MT.A_PART = self.r / "a-part"; RS.rendre = rendre
        try:
            with redirect_stdout(io.StringIO()):
                r = MT.monter(self.doc(), self.conf(), "2026-11-17-1400", self.r, None, {"temps": None}, "x", "y", ["a"], K.accroche_ecran, K.temps_mots)
        finally: MT.A_PART, RS.rendre = ancien
        self.assertFalse(r["ok"]); self.assertEqual((len(essais), r["essais"]), (3, 3))
        motif = json.loads((self.r / "a-part" / "2026-11-17-1400.json").read_text(encoding="utf-8")); self.assertIn("rendu simulé", motif["motifs"][0])


class StickStageRendu(Base):
    def test_skit_et_debuts(self):
        doc = {"titre": "Essai", "scenes": ["Gérard attend.", "Le téléphone sonne !", "C'était son premier client."], "jeu": [["sad", "slump"], None, ["embarrassed", "facepalm"]],
               "punchline": 1, "style": "classic", "decor": "boutique"}
        sk = RS.skit(doc, doc["scenes"], RS.decor(doc["decor"]))
        self.assertEqual((sk["meta"]["aspect"], sk["set"], sk["style"]), ("9:16", "bookshop-morning", "classic"))
        self.assertEqual(sk["characters"][0]["id"], "gerard"); self.assertEqual(sk["characters"][0]["style"]["build"], "toon")
        self.assertEqual([b["line"] for b in sk["beats"]], doc["scenes"]); self.assertTrue(sk["beats"][1].get("punchline"))
        self.assertEqual(sk["beats"][1]["actions"][0]["expression"], "shocked")              # sans indication : la ponctuation décide
        self.assertEqual(RS.decor("cabinet"), "office-1"); self.assertEqual(RS.decor("inconnu"), "office-1")
        g = self.r / "generated"; g.mkdir()
        (g / "timeline.json").write_text(json.dumps({"fps": 30, "scenes": [{"from": 0, "timeline": {"audio": [{"beatId": "n1", "frame": 9}, {"beatId": "n2", "frame": 99}]}},
                                                                            {"from": 150, "timeline": {"audio": [{"beatId": "n3", "frame": 15}]}}]}), encoding="utf-8")
        self.assertEqual(RS.debuts_repliques(self.r, 3), [0.3, 3.3, 5.5])
        t = K.temps_mots(["Un deux.", "Trois."], [1.0, 1.0], edge=lambda *a: [], debuts=[0.5, 4.0]); self.assertGreaterEqual(t[1][0][0], 4.0)

    def test_sous_titres_sans_mot_perdu(self):
        for p in ("Quelqu'un décroche !", "Gérard, par réflexe, répond : « Allô, oui, c'est pour quoi ? »", "Non. Oui. Peut-être.", "A. B c d e f."):
            g = C.decouper_sous_titres(p); self.assertEqual(" ".join(m for x in g for m in x["mots"]), " ".join(C.mots_de(p)), p)

    def test_csv_migre(self):
        C.JOURNAL_CSV.write_text("date;agent;video;ligne;compte;statut;hook;detail;tts\r\n2026-11-16 10:00;a;v;A;c;s;h;d;edge-tts\r\n", encoding="utf-8-sig")
        C.csv_ligne("videos-creation", "v2", "B", "c", "à valider", "h", "d", tts="kokoro", histoire="H01", fin="CTA2", duree_s="30.1")
        l = self.csv(); self.assertEqual(list(l[0].keys()), C.CSV_COLONNES); self.assertEqual((l[0]["tts"], l[0]["histoire"]), ("edge-tts", ""))
        self.assertEqual((l[1]["histoire"], l[1]["fin"], l[1]["duree_s"]), ("H01", "CTA2", "30.1"))
        with self.assertRaises(ValueError): C.csv_ligne("x", inconnu="1")


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
