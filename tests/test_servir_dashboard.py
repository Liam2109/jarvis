#!/usr/bin/env python3
"""Audit de sécurité de outils\\servir-dashboard.py (24/11/2026), un test par point : l'écriture POST /api/linkedin n'accepte que la machine elle-même ou le secret du serveur, limite la taille
de la requête, valide id et action avant tout fichier, n'écrit que dans l'état LinkedIn (aucun chemin ne vient de la requête), n'expose rien d'autre (ni noms de prospects, ni trace d'erreur),
et le tableau de bord existant continue d'être servi en lecture seule. Silencieux : serveur sur 127.0.0.1, port libre, dossiers temporaires, module « équipe » en doublure ou isolé."""
import http.client, importlib.util, json, os, shutil, sys, tempfile, threading, unittest
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path

os.environ["JARVIS_TEST"] = "1"; sys.dont_write_bytecode = True
RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "tests" / "agents"))
s = importlib.util.spec_from_file_location("servir_dashboard", RACINE / "outils" / "servir-dashboard.py"); S = importlib.util.module_from_spec(s); s.loader.exec_module(S)
OK_ID = "0123abcd"


class Faux:
    """Doublure du module linkedin-equipe : note ce qu'on lui demande, n'écrit rien."""
    class ErreurAgent(Exception): pass
    def __init__(self): self.appels = []; self.panne = None
    def cfg(self): return {}
    def appliquer_et_exporter(self, conf, ident, action, jour):
        if self.panne: raise self.panne
        self.appels.append((ident, action)); return "ok"


class Base(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp(prefix="srv-test-")); (self.t / "data").mkdir()
        for n, c in (("index.html", "<html>ok</html>"), ("agents.js", "window.A=1;"), ("data/linkedin.js", "window.JARVIS_LINKEDIN={noms:1};"), ("secret.txt", "ne doit jamais sortir")): (self.t / n).write_text(c, encoding="utf-8")
        self.old = (S.SECRET_FICHIER, S.DOSSIER, S._EQUIPE, S.LOOPBACK); S.SECRET_FICHIER = self.t / "config" / "dashboard.local"; S.DOSSIER = self.t
        self.faux = Faux(); S._EQUIPE = self.faux
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), partial(S.LectureSeule, directory=str(self.t))); self.port = self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def tearDown(self):
        self.srv.shutdown(); self.srv.server_close(); S.SECRET_FICHIER, S.DOSSIER, S._EQUIPE, S.LOOPBACK = self.old; shutil.rmtree(self.t, ignore_errors=True)

    def req(self, methode, chemin, corps=None, entetes=None, brut=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10); h = dict(entetes or {})
        data = brut if brut is not None else (json.dumps(corps).encode("utf-8") if corps is not None else None)
        c.request(methode, chemin, body=data, headers=h); r = c.getresponse(); b = r.read().decode("utf-8", "replace"); c.close(); return r.status, b

    def post(self, corps=None, secret=None, jarvis="1", type_="application/json", **kw):
        h = {"Content-Type": type_}
        if jarvis: h["X-Jarvis"] = jarvis
        if secret is not None: h["X-Jarvis-Secret"] = secret
        return self.req("POST", "/api/linkedin", corps, h, **kw)

    def a_distance(self): S.LOOPBACK = ()   # le client (127.0.0.1) est alors traité comme une machine du réseau


class TestOrigine(Base):
    def test_machine_elle_meme_sans_secret(self):
        c, b = self.post({"id": OK_ID, "action": "accepte"}); self.assertEqual((c, json.loads(b)["message"]), (200, "ok")); self.assertEqual(self.faux.appels, [(OK_ID, "accepte")])

    def test_machine_distante_sans_secret_ou_faux_secret_refusee(self):
        self.a_distance(); sec = S.secret()
        for s_ in (None, "", "faux", sec[:-1], sec + "x"):
            c, b = self.post({"id": OK_ID, "action": "accepte"}, secret=s_); self.assertEqual(c, 403, s_); self.assertNotIn(sec, b)
        self.assertEqual(self.faux.appels, [])   # rien n'a été appelé, donc rien n'a été écrit

    def test_machine_distante_avec_le_bon_secret(self):
        self.a_distance(); c, _ = self.post({"id": OK_ID, "action": "accepte"}, secret=S.secret()); self.assertEqual(c, 200); self.assertEqual(len(self.faux.appels), 1)

    def test_secret_cree_une_fois_hors_du_depot_et_jamais_servi(self):
        sec = S.secret(); self.assertGreaterEqual(len(sec), 20); self.assertEqual(sec, S.secret()); self.assertEqual(S.SECRET_FICHIER.read_text(encoding="utf-8").strip(), sec)
        for chemin in ("/config/dashboard.local", "/B2B/config/dashboard.local", "/secret.txt"): self.assertEqual(self.req("GET", chemin)[0], 404)
        import subprocess   # le vrai fichier de secret est ignoré par git (jamais commité)
        r = subprocess.run(["git", "check-ignore", "-q", str(RACINE / "B2B" / "config" / "dashboard.local")], cwd=RACINE); self.assertEqual(r.returncode, 0)
        self.assertEqual(S.SECRET_FICHIER.name, "dashboard.local"); self.assertEqual(S.__dict__["SECRET_FICHIER"], S.SECRET_FICHIER)

    def test_en_tete_x_jarvis_obligatoire(self):
        self.assertEqual(self.post({"id": OK_ID, "action": "accepte"}, jarvis=None)[0], 405); self.assertEqual(self.post({"id": OK_ID, "action": "accepte"}, jarvis="0")[0], 405); self.assertEqual(self.faux.appels, [])


class TestTaille(Base):
    def test_trop_gros_refuse_sans_lire(self):
        self.assertEqual(self.post(brut=b'{"id":"' + b"a" * 600 + b'"}')[0], 413); self.assertEqual(self.faux.appels, [])

    def test_sans_longueur_ou_type_incorrect(self):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10); c.putrequest("POST", "/api/linkedin"); c.putheader("X-Jarvis", "1"); c.putheader("Content-Type", "application/json"); c.putheader("Content-Length", "0"); c.endheaders()
        self.assertEqual(c.getresponse().status, 411); c.close()
        self.assertEqual(self.post(brut=b'{"id":"0123abcd","action":"accepte"}', type_="text/plain")[0], 415); self.assertEqual(self.faux.appels, [])

    def test_json_invalide(self):
        for brut in (b"pas du json", b"[1,2]", b'{"id": "0123abcd"}', b"\xff\xfe"): self.assertEqual(self.post(brut=brut)[0], 400, brut)
        self.assertEqual(self.faux.appels, [])


class TestChamps(Base):
    def test_identifiant_et_action_valides_avant_tout_fichier(self):
        for corps in ({"id": "../../etc/passwd", "action": "accepte"}, {"id": "..\\..\\B2B\\.env", "action": "accepte"}, {"id": "0123ABCD", "action": "accepte"}, {"id": "0123abc", "action": "accepte"},
                      {"id": "0123abcd0", "action": "accepte"}, {"id": 12345678, "action": "accepte"}, {"id": ["0123abcd"], "action": "accepte"}, {"id": OK_ID, "action": "supprimer"},
                      {"id": OK_ID, "action": "../x"}, {"id": OK_ID, "action": None}, {"id": OK_ID, "action": "accepte\n"}, {"id": OK_ID + "\n", "action": "accepte"}):
            self.assertEqual(self.post(corps)[0], 400, corps)
        self.assertEqual(self.faux.appels, [])

    def test_toutes_les_actions_de_l_agent_sont_permises_et_pas_plus(self):
        import commun   # même liste que l'agent (aucune action ajoutée côté serveur sans l'agent)
        self.assertEqual(set(S.ACTIONS_OK), set(commun.agent("linkedin-equipe").ACTIONS))

    def test_ne_pas_donner_de_chemin(self):
        self.post({"id": OK_ID, "action": "accepte", "fichier": "../../.env", "chemin": "C:\\x"}); self.assertEqual(self.faux.appels, [(OK_ID, "accepte")])   # les champs en trop sont ignorés
        src = (RACINE / "outils" / "servir-dashboard.py").read_text(encoding="utf-8"); bloc = src[src.index("def do_POST"):src.index("do_PUT")]
        for interdit in ("open(", "write_text", "Path(", "os.", "shutil", "subprocess"): self.assertNotIn(interdit, bloc)   # le gestionnaire POST n'ouvre ni n'écrit aucun fichier lui-même


class TestExposition(Base):
    def test_rien_d_autre_n_est_accessible_ou_modifiable(self):
        self.assertEqual(self.req("POST", "/api/autre", {"id": OK_ID, "action": "accepte"}, {"X-Jarvis": "1", "Content-Type": "application/json"})[0], 405)
        self.assertEqual(self.req("POST", "/index.html", {"a": 1}, {"X-Jarvis": "1"})[0], 405); self.assertEqual(self.req("GET", "/api/linkedin")[0], 404)
        for m in ("PUT", "DELETE", "PATCH"): self.assertEqual(self.req(m, "/api/linkedin", {"id": OK_ID, "action": "accepte"}, {"X-Jarvis": "1"})[0], 405)
        for chemin in ("/../secret.txt", "/%2e%2e/secret.txt", "/data/", "/data", "/config/dashboard.local", "/secret.txt", "/data/linkedin.json"): self.assertEqual(self.req("GET", chemin)[0], 404, chemin)
        self.assertEqual(self.faux.appels, [])

    def test_erreur_interne_sans_detail(self):
        self.faux.panne = RuntimeError("C:\\Users\\Serveur Liam\\Jarvis\\B2B\\linkedin\\equipe.json illisible"); c, b = self.post({"id": OK_ID, "action": "accepte"})
        self.assertEqual(c, 500); self.assertNotIn("Users", b); self.assertNotIn("equipe.json", b)
        self.faux.panne = Faux.ErreurAgent("plafond atteint"); S.equipe().ErreurAgent = Faux.ErreurAgent; c, b = self.post({"id": OK_ID, "action": "accepte"}); self.assertEqual((c, json.loads(b)["message"]), (409, "plafond atteint"))

    def test_noms_de_prospects_proteges(self):
        self.assertEqual(self.req("GET", "/data/linkedin.js")[0], 200)   # la machine elle-même
        self.a_distance(); self.assertEqual(self.req("GET", "/data/linkedin.js")[0], 403); self.assertEqual(self.req("GET", "/data/linkedin.js?k=faux")[0], 403); self.assertEqual(self.req("HEAD", "/data/linkedin.js")[0], 403)
        c, b = self.req("GET", "/data/linkedin.js?t=1&k=" + S.secret()); self.assertEqual(c, 200); self.assertIn("JARVIS_LINKEDIN", b)

    def test_tableau_de_bord_existant_intact(self):
        self.a_distance()
        for chemin, attendu in (("/", "ok"), ("/index.html", "ok"), ("/agents.js", "window.A=1;")): c, b = self.req("GET", chemin); self.assertEqual(c, 200, chemin); self.assertIn(attendu, b)
        r = self.req("GET", "/agents.js"); c = http.client.HTTPConnection("127.0.0.1", self.port); c.request("GET", "/agents.js"); rep = c.getresponse(); rep.read()
        self.assertIn("connect-src 'self'", rep.getheader("Content-Security-Policy")); self.assertIn("frame-ancestors 'none'", rep.getheader("Content-Security-Policy")); self.assertEqual(rep.getheader("X-Content-Type-Options"), "nosniff"); c.close()


class TestEcritureReelle(Base):
    def test_n_ecrit_que_dans_l_etat_linkedin(self):
        """Avec le vrai module (état et tableau de bord dans des dossiers temporaires) : une case cochée modifie l'état et son export, rien d'autre, et jamais le vrai dépôt."""
        import commun; E = commun.agent("linkedin-equipe"); S._EQUIPE = E
        E.ETAT = self.t / "etat" / "equipe.json"; E.SORTIE = self.t / "sortie"; E.JOURNAL = self.t / "etat" / "journal.log"; E.RG.FICHIER = self.t / "registre.json"
        E.etat_ecrire({"cibles": {OK_ID: {"id": OK_ID, "type": "entreprise", "nom": "Test", "demande_prevue_le": "2026-11-24"}}, "jours": {}, "textes": [], "posts_utilises": [], "commentaires_urls": []})
        reel = [RACINE / "B2B" / "linkedin" / "equipe.json", RACINE / "dashboard" / "data" / "linkedin.json", RACINE / "B2B" / "donnees" / "registre-entreprises.json"]
        avant = [(p.exists(), p.stat().st_mtime if p.exists() else 0) for p in reel]; autour = sorted(p.name for p in self.t.rglob("*") if p.is_file())
        c, _ = self.post({"id": OK_ID, "action": "demande_envoyee"}); self.assertEqual(c, 200)
        self.assertTrue(json.loads(E.ETAT.read_text(encoding="utf-8"))["cibles"][OK_ID]["demande_envoyee_le"])
        nouveaux = sorted(set(p.name for p in self.t.rglob("*") if p.is_file()) - set(autour)); self.assertEqual(set(nouveaux) - {"equipe.json", "journal.log", "linkedin.json", "linkedin.js", "equipe.json.tmp"}, set())
        self.assertEqual(avant, [(p.exists(), p.stat().st_mtime if p.exists() else 0) for p in reel])   # le vrai état, le vrai tableau de bord et le vrai registre n'ont pas bougé
        self.assertEqual(self.post({"id": "ffffffff", "action": "demande_envoyee"})[0], 409)   # cible inconnue : refus propre, rien d'écrit de plus


class TestSimultane(Base):
    def test_une_ecriture_a_la_fois(self):
        self.assertTrue(hasattr(S.VERROU, "acquire")); en_cours, max_en_cours, lock = [0], [0], threading.Lock()
        def lent(conf, ident, action, jour):
            with lock: en_cours[0] += 1; max_en_cours[0] = max(max_en_cours[0], en_cours[0])
            import time; time.sleep(0.05)
            with lock: en_cours[0] -= 1
            return "ok"
        self.faux.appliquer_et_exporter = lent; th = [threading.Thread(target=lambda: self.post({"id": OK_ID, "action": "accepte"})) for _ in range(6)]
        [t.start() for t in th]; [t.join() for t in th]; self.assertEqual(max_en_cours[0], 1)


if __name__ == "__main__":
    unittest.main(verbosity=1)
