#!/usr/bin/env python3
"""Harness - linkedin : lots collés par Liam -> file ; règles de contenu (emoji, image, hashtags, tutoiement, témoignage, chiffres, prix, commissions, promesses, appel à l'action,
présentiel, phrases interdites, secrets) ; alternance recrutement/prospect ; ✅ ❌ 📌 lus seulement de Liam ; un post non validé ne repart jamais ; stock < 3 jours = erreur + demande de lot ;
simulation = rien écrit, rien posté. Discord est une DOUBLURE : aucun réseau, aucun message, aucun jeton réel, dossiers temporaires."""
import contextlib, io, json, re, shutil, tempfile, unittest
from pathlib import Path
import commun as C

L = C.agent("linkedin")
V = C.harness("valider")
LIOM, AUTRE, BOT = "42", "99", "7"   # utilisateur de Liam, un autre compte, le bot
JOUR1, JOUR2, JOUR3, SAMEDI = "2026-11-23", "2026-11-24", "2026-11-25", "2026-11-28"
MOTS = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel", "india", "juliet", "kilo", "lima", "mike", "november", "oscar", "papa", "quebec", "romeo", "sierra", "tango"]
RECRUT = ("Je cherche des appelants et des closers pour vendre des sites web à des artisans et des commerçants locaux.\n\n"
          "Le travail se fait par téléphone, depuis chez vous, à vos horaires. Je vous fournis la liste des entreprises à appeler et le discours de présentation. Cette semaine : {m}.\n\n"
          "La rémunération est une commission : 15 % pour les appelants, 15 % pour les closers. Aucune formation n'est exigée, mais il faut aimer parler au téléphone "
          "et rester poli quand on vous dit non.\n\nSi ce type de mission vous parle, écrivez-moi en message privé.")
PROSPECT = ("Vous êtes artisan ou commerçant et vous n'avez pas de site web, ou un site qui date ? Sujet du jour : {m}.\n\n"
            "Je crée des sites web pour les artisans et les commerçants locaux : une page claire, qui présente votre activité, vos horaires et la façon de vous joindre. "
            "Le pack landing page est à 595 €, le site complet à 994 €, puis 49 € par mois avec l'hébergement, la maintenance et le support.\n\n"
            "Je préfère vous expliquer par téléphone ce qui vous conviendrait. Écrivez-moi en message privé.")


def recrut(k): return RECRUT.format(m=MOTS[k])
def prospect(k): return PROSPECT.format(m=MOTS[k])


def lot(r, p, extra="", d=0):
    """Texte d'un lot : r posts recrutement et p posts prospect (alternés dans le fichier), plus du texte libre éventuel ; d décale les textes (lots différents)."""
    out = ["# Lot de test\n"]; n = 0
    for k in range(max(r, p)):
        for t, f, ok in (("recrutement", recrut, k < r), ("prospect", prospect, k < p)):
            if ok: n += 1; out.append(f"## Post {n}\ntype: {t}\nstatut: en file\ntexte:\n{f(k + d)}\n")
    return "\n".join(out) + extra


class Faux:
    """Doublure de Discord : messages postés, réactions posées par des comptes précis, pannes à la demande. Aucun réseau."""
    def __init__(self): self.appels, self.msgs, self.reac, self.n, self.panne_lecture, self.posts_avant_panne = [], {}, {}, 1000, False, None
    def api(self, jeton, methode, chemin, corps=None):
        self.appels.append((methode, chemin, corps))
        if methode == "POST":
            if self.posts_avant_panne is not None:
                if self.posts_avant_panne <= 0: return None
                self.posts_avant_panne -= 1
            self.n += 1; self.msgs[str(self.n)] = corps; return {"id": str(self.n)}
        if methode == "GET" and "/reactions/" in chemin:
            if self.panne_lecture: return None
            p = chemin.split("?")[0].split("/"); return [{"id": u} for u in self.reac.get((p[4], p[6]), [])]
        return {}
    def posts(self): return [a for a in self.appels if a[0] == "POST"]
    def reagir(self, mid, emoji, *users): self.reac[(mid, emoji)] = list(users)
    acces = staticmethod(lambda conf: ("JETON-DE-TEST", "salon-test", LIOM))


def silencieux(f, *a, **k):
    s = io.StringIO()
    with contextlib.redirect_stdout(s): r = f(*a, **k)
    return r, s.getvalue()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="linkedin-test-"))
        self.sauve = (L.DOSSIER, L.JOURNAL, L.CONFIG); L.DOSSIER, L.JOURNAL, L.CONFIG = self.tmp / "linkedin", self.tmp / "journal.log", self.tmp / "linkedin-config.json"
        L.DOSSIER.mkdir(); self.conf = L.cfg(); self.reel = dict(self.conf, envoi_automatique=True); self.d = Faux(); L.RAISON = None
    def tearDown(self):
        L.DOSSIER, L.JOURNAL, L.CONFIG = self.sauve; shutil.rmtree(self.tmp, ignore_errors=True)
    def lot(self, r=6, p=6, nom="lot-2026-11-22.md", extra="", d=0): (L.DOSSIER / nom).write_text(lot(r, p, extra, d), encoding="utf-8")
    def jour(self, jour, conf=None, **k): return silencieux(L.cmd_jour, conf or self.reel, jour, api=self.d.api, acces=self.d.acces, dormir=lambda s: None, **k)
    def etat(self): return L.etat_lire()
    def statuts(self): return {p["id"]: p["statut"] for p in self.etat()["posts"]}
    def par_statut(self, s): return [p for p in self.etat()["posts"] if p["statut"] == s]


class Lot(Base):
    def test_lecture_du_format(self):
        posts, err = L.lire_lot("\ufeff" + lot(2, 2).replace("\n", "\r\n"))   # BOM et fins de ligne Windows
        self.assertEqual((len(posts), err), (4, [])); self.assertEqual([p["type"] for p in posts], ["recrutement", "prospect"] * 2)
        self.assertTrue(posts[0]["texte"].startswith("Je cherche") and posts[0]["texte"].endswith("message privé."))
        self.assertIn("\n\n", posts[0]["texte"])   # les paragraphes sont gardés

    def test_blocs_mal_formes(self):
        mauvais = "## Post 1\ntype: article\ntexte:\nx\n\n## Post 2\ntype: prospect\nstatut: publié\ntexte:\nx\n\n## Post 3\ntype: prospect\ntexte:\n\n## Post 4\ntype: prospect\ncouleur: bleu\ntexte:\nx\n"
        posts, err = L.lire_lot(mauvais)
        self.assertEqual(posts, []); self.assertEqual(len(err), 4)
        self.assertTrue("type" in err[0] and "statut" in err[1] and "texte absent" in err[2] and "ligne inattendue" in err[3], err)
        self.assertTrue(L.lire_lot("rien du tout")[1])   # aucun bloc

    def test_import_partiel_et_idempotent(self):
        self.lot(3, 3, extra="\n## Post 7\ntype: prospect\ntexte:\n" + prospect(5).replace("Vous êtes", "Tu es") + "\n")   # un post tutoyé
        e = self.etat(); res, sortie = silencieux(L.importer, e, self.conf)
        self.assertEqual((res["importes"], len(e["posts"])), (6, 6)); self.assertIn("tutoiement", sortie + str(res)); self.assertEqual(len(res["lots"]["lot-2026-11-22.md"]["refuses"]), 1)
        res2 = L.importer(e, self.conf)   # deuxième import : rien de nouveau, rien en double
        self.assertEqual((res2["importes"], len(e["posts"]), res2["lots"]["lot-2026-11-22.md"]["deja"]), (0, 6, 6))
        self.assertTrue(all(p["statut"] == "en_file" and len(p["id"]) == 8 for p in e["posts"]))
        self.lot(3, 3, nom="lot-2026-11-29.md")   # même contenu dans un autre lot : pas de doublon
        self.assertEqual(L.importer(e, self.conf)["importes"], 0)

    def test_importer_en_essai_n_ecrit_rien(self):
        self.lot(); res, _ = silencieux(L.importer, L.etat_lire(), self.conf); self.assertEqual(res["importes"], 12)   # importer() seul travaille en mémoire
        self.assertFalse(L.FILE().exists())
        boom = lambda *a, **k: self.fail("Discord appelé en --essai")
        silencieux(L.cmd_jour, self.reel, JOUR1, essai=True, api=boom, acces=boom)   # même avec envoi_automatique=true, --essai ne touche à rien
        self.assertFalse(L.FILE().exists()); self.assertFalse(L.JOURNAL.exists())


class Regles(Base):
    def pb(self, texte, type_="prospect"): return L.controle(type_, texte, self.conf)
    def refuse(self, texte, mot, type_="prospect"):
        pb = self.pb(texte, type_); self.assertTrue(any(mot in x for x in pb), f"« {mot} » attendu dans {pb}")

    def test_posts_conformes(self):
        self.assertEqual(self.pb(recrut(0), "recrutement"), []); self.assertEqual(self.pb(prospect(0)), [])

    def test_contenu(self):
        p, r = prospect(0), recrut(0)
        self.refuse(p.replace("Je crée", "Je crée ✅"), "emoji"); self.refuse(p.replace("Je crée", "😀 Je crée"), "emoji")
        self.refuse(p + "\n![visuel](photo.png)", "image"); self.refuse(p.replace("Je crée", "Voici une photo jointe. Je crée"), "image")
        self.refuse(p.replace("Je crée", "#site #web #artisan #local Je crée"), "hashtags"); self.assertEqual(self.pb(p.replace("Je crée", "#site #web Je crée")), [])
        self.refuse(p.replace("Vous êtes", "Tu es"), "tutoiement"); self.refuse(p.replace("vos horaires", "tes horaires"), "tutoiement"); self.refuse(p.replace("votre activité", "ton entreprise"), "tutoiement")
        for t in ("Un client m'a dit que c'était parfait.", "Nos clients nous font confiance.", "Voici un témoignage.", "« Le site a changé ma vie, je recommande à tous les commerçants de la ville »."):
            self.refuse(p.replace("Je crée", t + " Je crée"), "témoignage")
        for t in ("Résultat garanti.", "Vous allez vendre plus.", "Gagnez des clients.", "Vous aurez plus de clients.", "Un revenu passif."):
            self.refuse(p.replace("Je crée", t + " Je crée"), "promesse")
        self.refuse(p.replace("Je crée", "Ce plombier a déjà un site. Je crée"), "page exemple"); self.refuse(p.replace("Je crée", "Voyez des clients comme vous. Je crée"), "page exemple")
        self.refuse(p.replace("Écrivez-moi en message privé.", "Merci de votre lecture."), "dernière ligne")   # appel à l'action absent
        self.refuse(p + " Écrivez-moi en message privé.", "dernière ligne")   # appel à l'action en double
        self.refuse(p.replace("Je crée", "Contactez-moi ! Je crée"), "autre appel"); self.refuse(p.replace("Je crée", "Réservez votre créneau. Je crée"), "autre appel")
        self.refuse(p.replace("Je crée", "Voir https://exemple.fr. Je crée"), "lien"); self.refuse(p.replace("Je crée", "Écrivez à moi@exemple.fr. Je crée"), "e-mail")
        self.refuse(p.replace("Je préfère", "Je peux passer vous voir en boutique. Je préfère"), "présentiel"); self.refuse(p.replace("Je préfère", "On peut se rencontrer. Je préfère"), "présentiel")
        self.refuse(p.replace("Je crée", "`code` Je crée"), "accent grave"); self.refuse("trop court. Écrivez-moi en message privé.", "trop court"); self.refuse(p + " " + "a" * 1500, "trop long")

    def test_chiffres_prix_commissions(self):
        p, r = prospect(0), recrut(0)
        self.refuse(p.replace("994 €", "1200 €"), "prix"); self.refuse(p.replace("595 €", "590 €"), "prix"); self.refuse(p.replace("49 € par mois", "29 € par mois"), "prix")
        self.refuse(p.replace("994 €", "595 €"), "pas du site complet"); self.refuse(p.replace("à 595 €", "à 994 €"), "pas du pack")   # prix du pack et du site complet inversés
        self.refuse(p.replace("49 € par mois", "49 €"), "par mois")
        self.refuse(p.replace("Je crée", "Depuis 20 ans, je crée"), "chiffre non vérifié"); self.refuse(p.replace("Je crée", "Je crée en 48 heures"), "chiffre non vérifié")
        self.refuse(r.replace("15 % pour les appelants, 15 % pour les closers", "10 % pour les appelants, 15 % pour les closers"), "commission", "recrutement")   # commissions inversées
        self.refuse(r.replace("15 % pour les appelants", "20 % pour les appelants"), "commission", "recrutement")
        self.refuse(r.replace("15 % pour les appelants, 15 % pour les closers", "15 % de commission"), "sans « appelant »", "recrutement")
        self.assertEqual(self.pb(r.replace("15 % pour les appelants, 15 % pour les closers", "les closers touchent 15 %, les appelants 15 %"), "recrutement"), [])
        self.assertEqual(self.pb(r.replace("15 % pour les appelants, 15 % pour les closers", "15 % pour les appelants et 15 % pour les closers"), "recrutement"), [])

    def test_offre_garde_et_types(self):
        p, r = prospect(0), recrut(0)
        for ph in ("sans abonnement obligatoire", "maintenance facultative", "590 €", "29 €/mois"): self.refuse(p.replace("Je crée", ph + ". Je crée"), "phrase interdite")
        self.refuse(p.replace("Je crée", "https://buy.stripe.com/inconnu123. Je crée"), "lien Stripe")
        faux = "sk_" + "live_" + "abcdefghijklmnop"   # faux secret assemblé à l'exécution : jamais écrit en toutes lettres dans un fichier (hook pre-commit)
        self.refuse(p.replace("Je crée", faux + ". Je crée"), "secret")
        self.refuse(p + "\n" + r, "dernière ligne")
        self.refuse(r.replace("appelants et des closers", "personnes").replace("pour les appelants", "pour les gens").replace("pour les closers", "pour les gens"), "appelants ou des closers", "recrutement")
        self.refuse(p.replace("artisans et les commerçants", "gens").replace("artisan ou commerçant", "chef d'entreprise"), "site web pour artisans", "prospect")
        self.refuse(p.replace("Je crée", "Je recrute des appelants. Je crée"), "pas de recrutement", "prospect")
        self.refuse(p, "inconnu", "article")


class Passage(Base):
    def test_simulation_n_ecrit_rien(self):
        self.lot(); conf = dict(self.conf, envoi_automatique=False); boom = lambda *a, **k: self.fail("Discord appelé en simulation")
        code, sortie = silencieux(L.cmd_jour, conf, JOUR1, api=boom, acces=boom)
        self.assertEqual(code, 0); self.assertFalse(L.FILE().exists()); self.assertIn("simulation", sortie)
        self.assertEqual(len(re.findall(r"message qui serait posté", sortie)), 2); self.assertIn("```", sortie)
        self.assertTrue(sortie.index("(recrutement)") < sortie.index("(prospect)"))
        self.assertEqual(silencieux(L.cmd_jour, conf, JOUR1, essai=True, api=boom, acces=boom)[0], 0)
        self.assertEqual(len(L.JOURNAL.read_text(encoding="utf-8").splitlines()), 2)   # la simulation journalise, --essai non (mêmes 2 lignes qu'avant)

    def test_premier_jour(self):
        self.lot(); code, sortie = self.jour(JOUR1); self.assertEqual(code, 0)
        posts = self.d.posts(); self.assertEqual(len(posts), 2)
        a, b = (x[2]["content"] for x in posts)
        self.assertTrue(a.startswith("<@42> **LinkedIn, post 1/2** (recrutement)") and "vers 08:30" in a); self.assertTrue(b.startswith("**LinkedIn, post 2/2** (prospect)") and "vers 12:30" in b)
        self.assertEqual(posts[0][2]["allowed_mentions"], {"users": ["42"]}); self.assertEqual(posts[1][2]["allowed_mentions"], {"parse": []})
        for m in (a, b): self.assertTrue(re.search(r"```\n.+\n```", m, re.S) and "✅ valider" in m and len(m) < 1990)
        self.assertEqual(len([x for x in self.d.appels if x[0] == "PUT"]), 6)   # ✅ ❌ 📌 sur chacun des deux messages
        e = self.etat(); self.assertEqual([p["statut"] for p in e["posts"][:2]], ["propose", "propose"]); self.assertEqual(sorted(e["jours"][JOUR1]), sorted(p["id"] for p in self.par_statut("propose")))
        self.assertNotIn("JETON-DE-TEST", sortie + L.JOURNAL.read_text(encoding="utf-8") + json.dumps(L.FILE().read_text(encoding="utf-8")))   # aucun secret écrit ou affiché
        n = len(self.d.appels); self.assertEqual(self.jour(JOUR1)[0], 0); self.assertEqual(len(self.d.posts()), 2)   # même jour : rien de reposté
        self.assertTrue(all(x[0] == "GET" for x in self.d.appels[n:]))   # seulement des lectures de réactions

    def test_alternance_un_post_par_jour(self):
        self.lot(); conf = dict(self.reel, posts_par_jour=1, creneaux=["08:30"])
        for j in (JOUR1, JOUR2, JOUR3): self.jour(j, conf)
        self.assertEqual([p["type"] for p in self.etat()["posts"] if p["propose_le"]], ["recrutement", "prospect", "recrutement"])

    def test_decisions_de_liam_seul(self):
        self.lot(); self.jour(JOUR1); ids = [p["id"] for p in self.etat()["posts"][:2]]; m1, m2 = sorted(self.d.msgs)[:2]
        self.d.reagir(m1, L.OK, BOT, LIOM); self.d.reagir(m2, L.OK, BOT, AUTRE)   # post 2 : seulement le bot et un autre compte
        n_avant = len(self.d.posts()); code, _ = self.jour(JOUR2)
        s = self.statuts(); self.assertEqual((s[ids[0]], s[ids[1]]), ("pret", "non_valide")); self.assertEqual(code, 0)
        nouveaux = [x[2]["content"] for x in self.d.posts()[n_avant:]]
        self.assertEqual(len(nouveaux), 3)   # un signalement « non validé » puis 2 nouveaux posts
        self.assertIn("non validé", nouveaux[0]); self.assertIn(ids[1], nouveaux[0]); self.assertNotIn("```", nouveaux[0])
        for m in nouveaux[1:]: self.assertTrue(all(i not in m for i in ids))   # le post non validé ne repart JAMAIS
        for p in self.par_statut("propose"): self.assertEqual(p["propose_le"], JOUR2)
        self.jour(JOUR3); self.assertEqual(len([x for x in self.d.posts() if "non validé" in x[2]["content"] and ids[1] in x[2]["content"]]), 1)   # le même post n'est signalé qu'une seule fois

    def test_rejet_publication_et_conflit(self):
        self.lot(); self.jour(JOUR1); ids = [p["id"] for p in self.etat()["posts"][:2]]; m1, m2 = sorted(self.d.msgs)[:2]
        self.d.reagir(m1, L.OK, LIOM); self.d.reagir(m1, L.PIN, LIOM); self.d.reagir(m2, L.OK, LIOM); self.d.reagir(m2, L.KO, LIOM)   # 1 : ✅ puis 📌 ; 2 : ✅ et ❌ (❌ gagne)
        self.jour(JOUR2); s = self.statuts(); self.assertEqual((s[ids[0]], s[ids[1]]), ("publie", "rejete"))
        pub = next(p for p in self.etat()["posts"] if p["id"] == ids[0]); self.assertEqual((pub["publie_le"], pub["decide_le"]), (JOUR2, JOUR2))
        self.assertRegex(L.JOURNAL.read_text(encoding="utf-8"), rf"\| publié \| {ids[0]} \(recrutement\) le {JOUR2}")   # la date de publication est dans le journal
        self.d.reagir(m1, L.KO, LIOM); self.jour(JOUR3); self.assertEqual(self.statuts()[ids[0]], "publie")   # un post publié ne revient pas en arrière
        n = len(self.d.appels); self.jour(JOUR3); self.assertEqual([x for x in self.d.appels[n:] if x[0] == "GET" and f"/{m1}/" in x[1]], [])   # plus relu une fois publié

    def test_pret_puis_publie_par_pin(self):
        self.lot(); self.jour(JOUR1); pid = self.etat()["posts"][0]["id"]; m1 = sorted(self.d.msgs)[0]
        self.d.reagir(m1, L.OK, LIOM); self.jour(JOUR2); self.assertEqual(self.statuts()[pid], "pret")
        self.d.reagir(m1, L.PIN, LIOM); self.jour(JOUR3); self.assertEqual(self.statuts()[pid], "publie")

    def test_lecture_discord_impossible(self):
        self.lot(); self.jour(JOUR1); self.d.panne_lecture = True
        code, sortie = self.jour(JOUR2); self.assertEqual(code, 0); self.assertIn("illisibles", sortie)
        self.assertEqual(len(self.par_statut("non_valide")), 0)   # jamais « non validé » sur une lecture ratée
        self.d.panne_lecture = False; self.d.reagir(sorted(self.d.msgs)[0], L.OK, LIOM); self.jour(JOUR3)
        self.assertEqual(len(self.par_statut("pret")), 1)

    def test_week_end(self):
        self.lot(); code, sortie = self.jour(SAMEDI); self.assertEqual(code, 0); self.assertEqual(self.d.appels, []); self.assertIn("non ouvré", sortie)

    def test_stock_bas(self):
        self.lot(3, 3); code, _ = self.jour(JOUR1)   # 3 + 3 posts : après le premier jour il reste 2 jours < 3
        self.assertEqual(code, 5); self.assertIn("stock bas : 2 jour(s)", L.RAISON); self.assertIn("nouveau lot à Claude", L.RAISON)
        msgs = [x[2]["content"] for x in self.d.posts()]; self.assertEqual(len(msgs), 3); self.assertTrue("nouveau lot à Claude" in msgs[-1] and "```" not in msgs[-1])
        self.assertEqual(self.jour(JOUR1)[0], 5); self.assertEqual(len(self.d.posts()), 3)   # même jour : pas de second message de stock
        L.RAISON = None; self.lot(4, 4, nom="lot-2026-11-23.md", d=3); self.assertEqual(self.jour(JOUR2)[0], 0)   # nouveau lot : plus d'alerte
        self.assertEqual(L.jours_de_stock(self.etat()["posts"], self.etat()["prochain_type"], 2), 5)

    def test_stock_vide(self):
        code, _ = self.jour(JOUR1); self.assertEqual(code, 5); self.assertIn("0 jour(s)", L.RAISON); self.assertEqual(len(self.d.posts()), 1)   # seulement la demande de lot

    def test_alternance_stricte_sans_un_type(self):
        self.lot(0, 4); code, sortie = self.jour(JOUR1)   # pas un seul post recrutement : rien n'est posté à la place
        self.assertIn("alternance stricte", sortie); self.assertEqual(self.par_statut("propose"), []); self.assertEqual(code, 5)

    def test_discord_tombe_en_cours_de_route(self):
        self.lot(); self.d.posts_avant_panne = 1; code, _ = self.jour(JOUR1)
        self.assertEqual(code, 2); self.assertIn("Discord", L.RAISON); self.assertEqual([p["type"] for p in self.par_statut("propose")], ["recrutement"])
        self.d.posts_avant_panne = None; self.assertEqual(self.jour(JOUR1)[0], 0)   # reprise : seulement le post manquant, du bon type
        self.assertEqual([p["type"] for p in self.etat()["posts"] if p["propose_le"] == JOUR1], ["recrutement", "prospect"]); self.assertEqual(len(self.d.msgs), 2)   # 2 messages pris (la tentative ratée n'en est pas un)

    def test_acces_discord_incomplet(self):
        self.lot(); code, _ = silencieux(L.cmd_jour, self.reel, JOUR1, api=self.d.api, acces=lambda c: None)
        self.assertEqual(code, 2); self.assertIn("accès Discord", L.RAISON); self.assertEqual(self.d.appels, []); self.assertEqual(self.par_statut("propose"), [])

    def test_texte_modifie_a_la_main_est_ecarte(self):
        self.lot(); e = self.etat(); silencieux(L.importer, e, self.conf); e["posts"][0]["texte"] += " Tu peux écrire à moi@exemple.fr"; L.etat_ecrire(e)
        self.jour(JOUR1); self.assertEqual(self.etat()["posts"][0]["statut"], "rejete")   # jamais envoyé
        self.assertTrue(all("moi@exemple.fr" not in x[2]["content"] for x in self.d.posts()))
        par_id = {p["id"]: p["type"] for p in self.etat()["posts"]}; self.assertEqual([par_id[i] for i in self.etat()["jours"][JOUR1]], ["recrutement", "prospect"])   # le créneau est repris par le post suivant du même type

    def test_file_illisible(self):
        L.FILE().write_text("{pas du json", encoding="utf-8")
        with self.assertRaises(L.ErreurAgent): self.jour(JOUR1)
        self.assertEqual(L.FILE().read_text(encoding="utf-8"), "{pas du json"); self.assertEqual(self.d.appels, [])


class Decisions(Base):
    def test_cli(self):
        self.lot(); e = self.etat(); silencieux(L.importer, e, self.conf); L.etat_ecrire(e); ids = [p["id"] for p in e["posts"]]
        silencieux(L.cmd_decision, "valider", ids[0][:5], JOUR1); self.assertEqual(self.statuts()[ids[0]], "pret")
        silencieux(L.cmd_decision, "publie", ids[0], JOUR2); p = next(x for x in self.etat()["posts"] if x["id"] == ids[0]); self.assertEqual((p["statut"], p["publie_le"]), ("publie", JOUR2))
        silencieux(L.cmd_decision, "rejeter", ids[1], JOUR2); self.assertEqual(self.statuts()[ids[1]], "rejete")
        for action, i in (("rejeter", ids[0]), ("valider", ids[1]), ("publie", ids[1])):
            with self.assertRaises(L.ErreurAgent): L.cmd_decision(action, i, JOUR2)   # transitions impossibles
        for mauvais in ("zzzz", ids[0][:3], ""):
            with self.assertRaises(L.ErreurAgent): L.cmd_decision("valider", mauvais, JOUR2)
        self.assertEqual(silencieux(L.cmd_etat, self.conf)[0], 0)
        self.assertRegex(L.JOURNAL.read_text(encoding="utf-8"), rf"\| prêt \| {ids[0]} \(.*à la main")


class Cadre(unittest.TestCase):
    def test_aucune_ia_ni_service_payant(self):
        src = (C.AGENTS / "linkedin.py").read_text(encoding="utf-8"); mods = set()
        for l in src.splitlines():
            m = re.match(r"\s*(?:from\s+([\w.]+)\s+import|import\s+([\w., ]+))", l)
            if m: mods |= {x.strip().split(" as ")[0].split(".")[0] for x in (m.group(1) or m.group(2)).split(",")}
        self.assertLessEqual(mods, {"argparse", "copy", "hashlib", "json", "re", "sys", "time", "unicodedata", "datetime", "pathlib", "machine", "prospection", "garde", "traces"}, mods)
        for interdit in ("anthropic", "openai", "ollama", "subprocess", "requests", "playwright", "selenium", "linkedin.com", "api.linkedin"): self.assertNotIn(interdit, src.lower(), interdit)   # aucune IA, aucun site LinkedIn

    def test_contrat_reglages_et_tache(self):
        c = json.loads((C.HARNESS / "contrats" / "linkedin.json").read_text(encoding="utf-8")); schema = json.loads((C.HARNESS / "contrat.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(V.valider(c, schema), []); self.assertFalse(c["peut_engager"]); self.assertFalse(c["envoi_client"]); self.assertEqual((c["statut"], c["responsable"]), ("simulation", "Prospection"))
        self.assertEqual((c["jours"], c["heures"]["debut"]), ([0, 1, 2, 3, 4], "07:45")); self.assertTrue((C.RACINE / c["tests"][0]).is_file())
        reg = json.loads((C.AGENTS / "linkedin-config.json").read_text(encoding="utf-8")); self.assertIs(reg["envoi_automatique"], False)   # défaut versionné = simulation
        self.assertFalse(any(k in reg for k in ("token", "jeton", "cle", "salon_linkedin_id")))   # aucun secret ni identifiant dans le fichier suivi par git
        t = json.loads((C.AGENTS / "serveur-taches.json").read_text(encoding="utf-8"))["agents"]["linkedin"]
        self.assertEqual((t["script"], t["commandes"], t["heure"], t["jours"]), ("linkedin.py", [["jour"]], "07:45", [0, 1, 2, 3, 4])); self.assertTrue(t["desactive"])   # fermé jusqu'au « go linkedin »
        self.assertEqual(json.loads((C.HARNESS / "fiches-noms.json").read_text(encoding="utf-8"))["linkedin"], "💼 LinkedIn")
        self.assertTrue((C.RACINE / ".claude" / "skills" / "agent-linkedin" / "SKILL.md").is_file())


if __name__ == "__main__":
    unittest.main(verbosity=1)
