#!/usr/bin/env python3
"""Harness - gardien de l'architecture (24/11/2026) : cas SIMULÉS, aucun réseau, aucun Discord, aucune relance réelle, aucun vrai fichier de données touché.
Cas : agent sensible muet (jamais relancé seul) ; agent de la liste fermée muet (relancé UNE fois) ; doublons jugés par Claude (doublure) ; essai sans passe Claude ;
verrou fermé ; rapport de 10 lignes au plus ; archivage et restauration identiques à l'origine ; carte du trajet (pointillés) ; règle d'ajout (nouvel agent sans fiche = rouge)."""
import io, json, shutil, tempfile, unittest
from contextlib import redirect_stdout
from datetime import date, datetime
from pathlib import Path
import commun as C

G = C.agent("gardien")
S, AR = G.S, G.AR
NOM = "".join(["vi", "eux"])      # nom construit : le test ne se cite pas lui-même
LIMITE = "mission longue assez pour le contrat"


def contrat(nom, statut="actif", envoi=False, **kw):
    c = {"nom": nom, "responsable": "Vente", "mission": f"{LIMITE} {nom}", "statut": statut, "script": f"B2B/agents/{nom}.py", "jours": [0], "heures": {"debut": "08:00", "fin": "09:00"},
         "fichiers_lus": [], "fichiers_ecrits": [], "canaux_discord": [], "envoi_client": envoi, "actions_interdites": ["x"], "plafonds": {"messages_par_jour": 0},
         "peut_engager": False, "alerte_si_silence": None, "tests": [f"tests/agents/test_{nom}.py"]}
    c.update(kw); return c


def ctx(cs, ts=None, actifs=None, **kw):
    conf = S.cfg("gardien", G.DEFAUT); conf["go_superviseurs"] = True
    d = {"contrats": {c["nom"]: c for c in cs}, "ts": ts if ts is not None else {c["nom"]: {"script": "x.py", "commandes": [["a"]], "heure": "08:00"} for c in cs},
         "actifs": set(actifs if actifs is not None else [c["nom"] for c in cs]), "conf": conf, "jour": "2026-11-29", "date": date(2026, 11, 29),
         "etat": {"relances": {}, "corrections": {}}, "relance": None, "claude": None, "traces": Path(tempfile.mkdtemp(prefix="gardien-traces-")), "essai": False, "sans_scripts": True}
    d.update(kw); return d


class Gardien(unittest.TestCase):
    def test_agent_sensible_jamais_relance(self):
        for nom, envoi in (("prospection", True), ("devis", False)):      # envoi à un prospect, ou hors liste fermée
            out = G.ctrl_inactivite(ctx([contrat(nom, envoi=envoi)]))
            self.assertEqual(len(out), 1); self.assertTrue(out[0].risque); self.assertIsNone(out[0].reparer); self.assertTrue(out[0].cle.startswith(G.CRITIQUE))

    def test_agent_liste_fermee_relance_une_fois(self):
        appels = []
        c = ctx([contrat("relances")], relance=lambda n, ts: (appels.append(n) or (True, "relancé, code 0")))
        s = G.ctrl_inactivite(c)[0]; self.assertFalse(s.risque)
        s.reparer(); s2 = G.ctrl_inactivite(c)[0]; s2.reparer()
        self.assertEqual(appels, ["relances"], "une seule relance par jour")

    def test_agent_pas_planifie_ici_ignore(self):
        self.assertEqual(G.ctrl_inactivite(ctx([contrat("relances")], actifs=[])), [])

    def test_doublons_claude_et_essai(self):
        a, b = contrat("alpha", fichiers_ecrits=["B2B/donnees/commun.json"]), contrat("beta", fichiers_ecrits=["B2B/donnees/commun.json"])
        n = []
        rep = lambda conf, prompt: (n.append(1) or '{"vrais_doublons":[{"agents":["alpha","beta"],"raison":"même travail"}]}')
        out = G.ctrl_doublons(ctx([a, b], claude=rep)); self.assertEqual(len(n), 1)
        self.assertTrue(out[0].risque and "doublon" in out[0].quoi)
        G.ctrl_doublons(ctx([a, b], claude=rep, essai=True)); self.assertEqual(len(n), 1, "essai : aucune passe Claude")
        self.assertEqual(G.ctrl_doublons(ctx([contrat("alpha"), contrat("zeta", fichiers_ecrits=["autre.json"])], claude=rep)), [], "aucun suspect = zéro token")
        self.assertEqual(len(n), 1)

    def test_verrou_ferme_et_rapport(self):
        conf = S.cfg("gardien", G.DEFAUT)      # verrou fermé par défaut (go_gardien false)
        self.assertFalse(conf["go_superviseurs"])
        envoyes = []
        with redirect_stdout(io.StringIO()):
            soucis, texte = G.passage(conf, essai=True, maintenant=datetime(2026, 11, 29, 21, 0), envoyer=envoyes.append, claude=lambda *a: "{}", sans_scripts=True, ts={}, actifs=set())
        self.assertEqual(envoyes, []); self.assertFalse(any(s.corrige for s in soucis))
        self.assertLessEqual(len(texte.splitlines()), 10)

    def test_rapport_10_lignes(self):
        soucis = [S.risque(f"a{i}", "quoi", "détail", cle=G.CRITIQUE + str(i)) for i in range(8)]
        for i in range(6):
            s = S.sur(f"r{i}", "x", lambda: "ok", cle=f"r{i}"); s.corrige, s.change = True, f"réparé {i}"; soucis.append(s)
        t = G.rapport(soucis, [f"maillon {i}" for i in range(9)])
        self.assertLessEqual(len(t.splitlines()), 10); self.assertIn("Gros problème", t)

    def test_archivage_et_restauration(self):
        tmp = Path(tempfile.mkdtemp(prefix="gardien-arch-"))
        notes, arch = tmp / "agents", tmp / "archives"; (notes / "skills").mkdir(parents=True)
        (notes / "🔍 Zed.md").write_text("---\nagent: zed\n---\ncorps\n", encoding="utf-8")
        (notes / "skills" / "agent-zed.md").write_text("skill", encoding="utf-8")
        (notes / "CEO.md").write_text("Liens : [[docs/agents/🔍 Zed|🔍 Zed]] · [[docs/agents/🧠 Autre|🧠 Autre]]\n\n## Notes de Liam\n", encoding="utf-8")
        noms = tmp / "fiches-noms.json"; noms.write_text('{\n "zed": "🔍 Zed",\n "autre": "🧠 Autre"\n}\n', encoding="utf-8")
        orig = (G.NOTES, G.ARCHIVE, G.FICHES_NOMS, AR.ARCHIVES_JSON, G.lancer_script)
        G.NOTES, G.ARCHIVE, G.FICHES_NOMS, AR.ARCHIVES_JSON, G.lancer_script = notes, arch, noms, tmp / "a.json", (lambda *a: (0, ""))
        try:
            G.archiver("zed")
            self.assertFalse((notes / "🔍 Zed.md").exists()); self.assertTrue((arch / "🔍 Zed.md").exists(), "archivé, jamais supprimé")
            ceo = (notes / "CEO.md").read_text(encoding="utf-8"); self.assertNotIn("Zed", ceo); self.assertIn("Autre", ceo)
            self.assertIsNone(json.loads(noms.read_text(encoding="utf-8"))["zed"]); self.assertIn("zed", G.archives_lire())
            G.restaurer("zed")
            self.assertTrue((notes / "🔍 Zed.md").exists() and (notes / "skills" / "agent-zed.md").exists())
            self.assertEqual(json.loads(noms.read_text(encoding="utf-8"))["zed"], "🔍 Zed")
            self.assertIn("[[docs/agents/🔍 Zed|🔍 Zed]]", (notes / "CEO.md").read_text(encoding="utf-8")); self.assertEqual(G.archives_lire(), {})
        finally:
            G.NOTES, G.ARCHIVE, G.FICHES_NOMS, AR.ARCHIVES_JSON, G.lancer_script = orig; shutil.rmtree(tmp, ignore_errors=True)

    def test_archivage_protections(self):
        base = contrat(NOM, statut="inactif")
        noms = {NOM: "Vieux"}
        orig = AR.GF.noms; AR.GF.noms = lambda: noms
        try:
            self.assertEqual(len(G.ctrl_archivage(ctx([base], ts={}))), 1)
            self.assertEqual(G.ctrl_archivage(ctx([base], ts={NOM: {"heure": "08:00"}})), [], "tâche serveur (attend un go) : jamais archivé")
            self.assertEqual(G.ctrl_archivage(ctx([contrat(NOM, statut="actif")], ts={})), [], "actif : jamais")
            self.assertEqual(G.ctrl_archivage(ctx([contrat(NOM, statut="inactif", envoi=True)], ts={})), [], "envoi : jamais")
            noms["autre"] = "Autre"
            lecteur = contrat("autre", fichiers_lus=["B2B/agents/" + NOM + "-etat.json"])
            self.assertEqual(G.ctrl_archivage(ctx([base, lecteur], ts={"autre": {"heure": "08:00"}})), [], "un autre contrat le lit")
            noms["production"] = "Prod"
            self.assertEqual(G.ctrl_archivage(ctx([contrat("production", statut="prevu")], ts={})), [], "dans le trajet du client")
        finally: AR.GF.noms = orig

    def test_aucune_ecriture_de_reglages(self):
        for l in Path(G.__file__).read_text(encoding="utf-8").splitlines():
            if "write_text" in l or "open(" in l: self.assertNotRegex(l, r"config|envoi_automatique|\.local\.json", l.strip())

    def test_carte_et_regle_d_ajout(self):
        d = AR.construire(); ids = {n["id"]: n for n in d["noeuds"]}
        self.assertTrue(ids["production"]["manque"] and ids["validation"]["manque"])
        self.assertIn("-.->", d["mermaid"]); self.assertEqual(AR.verifier(d), [])
        self.assertTrue(all(len(a["fiche"]) == 3 for a in d["agents"]))
        orig = AR.GF.contrats
        AR.GF.contrats = lambda: orig() + [contrat("fantome")]
        try:
            pb = AR.verifier(AR.construire()); self.assertTrue(any("fantome" in p for p in pb), "un agent sans fiche doit faire échouer")
        finally: AR.GF.contrats = orig


if __name__ == "__main__":
    unittest.main(verbosity=1)
