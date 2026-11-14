#!/usr/bin/env python3
"""Tests silencieux de l'agent Prospection : aucun réseau, aucun vrai envoi, fichiers temporaires, .env jamais lu.  python agents\\test_prospection.py"""
import os, sys, tempfile, json
os.environ.setdefault("JARVIS_TEST", "1")   # jamais de vrai appel Discord depuis les tests
from datetime import date, timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import prospection as X
CHERCHER_REEL = X.cmd_chercher   # les scénarios de la boucle remplacent X.cmd_chercher par un faux : on garde le vrai pour le test du rapport
X.lien_exemple = lambda metier, lien_ok=None: "https://b2b-demos.vercel.app/exemple/"  # pas de réseau : page exemple du métier simulée
_preparer_reel, _publier_reel = X.cmd_preparer, X.cmd_publier   # la boucle (scénarios) remplace ces fonctions par des simulations plus bas
X.mesurer_page, X.pagespeed, X.statut_http, X.etat_https = (lambda url, **k: (50_000, 0.4)), (lambda url, **k: None), (lambda url, **k: 200), (lambda host, **k: "absent")  # mesures : aucun réseau
_liens = Path(tempfile.mkdtemp(prefix="prospection-test-liens-")); X.ICI = _liens   # liens-metiers.json temporaire : l'état réel des pages en ligne n'influence pas les tests
(_liens / "liens-metiers.json").write_text(X.json.dumps({"plombier-chauffagiste": "https://x/p/", "electricien": "https://x/e/", "restaurant": "https://x/r/"}), encoding="utf-8")

# --- e-mails publiés, réseaux, diagnostic du site ---
page = '<a href="mailto:Contact@elec-dupont.fr">écrire</a> info@agence-web.fr jean.dupont@gmail.com img@2x.png noreply@elec-dupont.fr devis [at] elec-dupont.fr'
e = X.emails_page(page, "elec-dupont.fr")
assert e[0] == ("contact@elec-dupont.fr", "generique"), e
assert ("jean.dupont@gmail.com", "nominatif") in e and not any("agence-web" in a or "noreply" in a or "png" in a for a, _ in e), e
assert X.emails_page("jean.dupont@gmail.com", "x.fr") == [("jean.dupont@gmail.com", "nominatif")]
assert X.emails_page("secretaire@autre-societe.fr", "elec-dupont.fr") == []
fb, li = X.reseaux_page('<a href="https://www.facebook.com/sharer/sharer.php?u=1"></a><a href="https://www.facebook.com/elecdupont76?ref=x">f</a><a href="https://fr.linkedin.com/company/elec-dupont/">l</a>')
assert fb == "https://www.facebook.com/elecdupont76" and li == "https://fr.linkedin.com/company/elec-dupont", (fb, li)
j = date(2026, 10, 27)
assert X.diagnostic("http://a.fr", '<meta name="viewport" content="x"> © 2025', 4, j).startswith("site sans HTTPS")
assert "mobile" in X.diagnostic("https://a.fr", "<html>© 2024</html>", 4, j) and "constaté le 27/10" in X.diagnostic("https://a.fr", "<html></html>", 4, j)
assert "depuis 2016" in X.diagnostic("https://a.fr", '<meta name="viewport" content="x"> Copyright 2012-2016', 4, j)
assert X.diagnostic("https://a.fr", '<meta name="viewport" content="x"><a href="tel:0">a</a> © 2026', 4, j) == ""
assert X.nom_affiche("ARTISAN EXPRESS") == "Artisan Express" and X.beau("SAINT-ETIENNE-DU-ROUVRAY") == "Saint-Etienne-du-Rouvray"
assert X.domaines("SARL DUPONT ELEC")[0] == "dupontelec.fr" and X.domaines("AB") == []

# --- annuaire : le siège doit être dans le département, curseur conservé ---
def api(dept, naf, page):
    return {"total_pages": 1, "results": [
        {"siren": "111111111", "nom_complet": "ELEC UN", "siege": {"code_postal": "76000", "libelle_commune": "ROUEN"}},
        {"siren": "222222222", "nom_complet": "GROS GROUPE", "siege": {"code_postal": "75020", "libelle_commune": "PARIS"}}]}
et = {"curseur": {"i": 0, "page": 1}, "vus": {}}
c = X.candidats(et, 1, api, 0)
assert [x["siren"] for x in c] == ["111111111"] and c[0]["dept"] == "76" and c[0]["metier"] == "électricien" and et["curseurs_naf"]["43.21A"]["i"] == 1, (c, et)

# --- enrichissement (faux réseau) ---
conf = dict(X.DEFAUT)
cand = {"siren": "333333333", "nc": "ELEC DUPONT", "metier": "électricien", "cp": "76000", "ville": "Rouen", "dept": "76"}
vieux = '<html>Rouen <a href="/contact">c</a> <a href="https://www.facebook.com/elecdupont">f</a> © 2015</html>'
pages = {"http://elecdupont.fr": ("http://elecdupont.fr", {}, vieux), "http://elecdupont.fr/contact": ("http://elecdupont.fr/contact", {}, "Rouen écrire à contact@elecdupont.fr")}
lire = lambda u: pages.get(u)
et2 = {"recherches": {}}
l, motif = X.enrichir(cand, et2, conf, lire, lambda c: ("", ""))
assert l and l["email"] == "contact@elecdupont.fr" and l["email_type"] == "generique" and "elecdupont.fr" in l["email_source"] and "sans HTTPS" in l["note_besoin"], (l, motif)
assert l["source"].startswith("l'annuaire officiel") and "adresse publiée sur votre site" in l["source"]
PAGE_OK = '<title>Elec Dupont, électricien à Rouen</title><meta name="viewport" content="a"><meta name="description" content="Électricien à Rouen : dépannage et installation"><h1>Elec Dupont</h1><a href="tel:0">a</a>© 2026 Rouen'
pages["http://elecdupont.fr"] = ("https://elecdupont.fr", {}, PAGE_OK)
pages["https://elecdupont.fr"] = pages["http://elecdupont.fr"]
ee = X.enrichir(cand, et2, conf, lire, lambda c: ("", ""))
assert ee[0] is None and ee[1].startswith("site correct (score de faiblesse 0"), ee
# score de faiblesse : poids des constats mesurés, seuil réglable, 2 constats cités au plus (les plus parlants d'abord)
st_ = {}
pages["http://elecdupont.fr"] = pages["https://elecdupont.fr"] = ("http://elecdupont.fr", {}, "<html>Rouen <h1>x</h1> © 2026</html>")
l3, _ = X.enrichir(cand, et2, {**conf, "seuil_faiblesse": 20}, lambda u: pages.get(u) or ("x", {}, "contact@elecdupont.fr Rouen") if "elecdupont" in u else None, lambda c: ("", ""), stat=st_)
assert l3 and st_["score"] >= 40 and st_["faible"] and l3["note_besoin"].startswith("site sans HTTPS") and l3["note_besoin"].count(" ; ") == 1 and l3["score"] == str(st_["score"]), (l3, st_)
r_, m_ = X.enrichir(cand, et2, {**conf, "seuil_faiblesse": 99}, lire, lambda c: ("", ""), stat=st_)
assert r_ is None and m_.startswith("site correct (score de faiblesse") and not st_["faible"], m_   # même page, seuil plus haut : non retenue
pages["http://elecdupont.fr"] = pages["https://elecdupont.fr"] = ("https://elecdupont.fr", {}, PAGE_OK)
assert X.score_faiblesse([("https", ""), ("mobile", ""), ("flash", ""), ("lent", "")]) == 100 and X.score_faiblesse([]) == 0
sc = dict(X.constats_seo('<html><body>Bonjour</body></html>'))
assert {"title", "description", "h1"} <= set(sc) and "aucune balise title" in sc["title"], sc
sc = dict(X.constats_seo('<title>Accueil</title><img src="a.jpg"><img src="b.jpg" alt=""><img src="c.jpg" alt="four"><img src="d.jpg">'))
assert sc["title"].startswith("titre de page très court") and "3 images sur 4 sans texte alternatif" == sc["alt"], sc
assert not X.constats_seo(PAGE_OK)
assert X.images_lourdes("https://a.fr/", '<img src="/g.jpg"><img src="/p.png">', {"taille": lambda u: 2_400_000 if u.endswith("p.png") else 90_000}).startswith("une image de la page pèse 2,4 Mo")
assert X.images_lourdes("https://a.fr/", '<img src="/g.jpg">', {"taille": lambda u: 90_000}) == ""
ct = X.trier_constats([("appel", "a"), ("https", "h"), ("copyright", "c")]); assert [k for k, _ in ct] == ["https", "copyright", "appel"], ct
pages.clear()  # pas de site : réseau trouvé -> gardé ; sinon on passe
l, m = X.enrichir(cand, et2, conf, lire, lambda c: ("https://www.facebook.com/x", ""))
assert l["facebook"] and not l["email"] and not l["site_actuel"], l
assert X.enrichir(cand, et2, conf, lire, lambda c: ("", ""))[1].startswith("aucun e-mail")
assert X.enrichir({**cand, "metier": "plâtrier"}, et2, conf, lire, lambda c: ("", ""))[0] is None
pages["http://elecdupont.fr"] = ("http://elecdupont.fr", {}, "Un autre artisan à Lille © 2010")  # autre entreprise : page non vérifiée -> ignorée
assert X.trouver_site(cand, lire) is None

# --- chaîne lot -> validation -> envoi (tout en temporaire) ---
tmp = Path(tempfile.mkdtemp(prefix="prospection-test-"))
IDENT_FAUSSE = {"prenom_nom": "Liam Test", "entreprise": "LM MULTI-SERVICES", "siret": "12345678901234", "telephone": "06 00 00 00 00", "email_reponse": "ecrire@exemple.fr"}      # identité FICTIVE : les tests ne dépendent jamais du vrai identite.json (absent d'un clone propre)
import json as _j; (tmp / "identite.json").write_text(_j.dumps(IDENT_FAUSSE), encoding="utf-8"); X.R.IDENTITE = tmp / "identite.json"
X.ETAT, X.TROUVES, X.MESSAGES, X.APERCU, X.LOTS = tmp / "etat.json", tmp / "trouves.csv", tmp / "messages.md", tmp / "apercu.html", tmp / "lots"
X.S.FICHIER = X.R.SUIVI = tmp / "suivi.csv"
X.G.PUBLIC = tmp / "public"
X.P.CONFIG = tmp / "reponses-config.json"; X.P.CONFIG.write_text('{"api": {"actif": false}}', encoding="utf-8")   # repli IMAP/SMTP, indépendant de la vraie config
X.P.lire_env = lambda _: {"GMAIL_1_APP_PASSWORD": "aaaa bbbb", "GMAIL_2_APP_PASSWORD": "cccc"}
BOITES = X.boites(); assert len(BOITES) == 2
conf = {**X.DEFAUT, "par_boite_par_jour": 2, "reseaux_par_jour": 1, "pause_envoi_s": [0, 0]}
rows = []
for i, (nom, mail) in enumerate([("Elec Un", "contact@elecun.fr"), ("Elec Deux", "contact@elecdeux.fr"), ("Elec Trois", "contact@electrois.fr"),
                                 ("Elec Quatre", "contact@elecquatre.fr"), ("Elec Cinq", "contact@eleccinq.fr"), ("Page Seule", "")]):
    r = {k: "" for k in X.COLS}
    r.update(nom=nom, metier="électricien", ville="Rouen", siren=str(100000000 + i), cp="76000", statut="trouvé", email=mail, email_type="generique" if mail else "",
             email_source="https://x.fr" if mail else "", note_besoin="site non adapté au mobile (constaté le 27/10)" if mail else "", source="l'annuaire officiel des entreprises",
             facebook="" if mail else "https://www.facebook.com/pageseule", date_collecte=str(date.today()))
    rows.append(r)
    if mail: (X.G.PUBLIC / f"{X.G.slug(nom)}-{X.G.jeton(nom, 'Rouen')}").mkdir(parents=True); (X.G.PUBLIC / f"{X.G.slug(nom)}-{X.G.jeton(nom, 'Rouen')}" / "index.html").write_text("x")
X.ecrire_trouves(rows)
assert X.cmd_preparer(True, conf, generer=False) >= 4 and not X.MESSAGES.exists() and not X.ETAT.exists()  # à blanc : rien écrit
n = X.cmd_preparer(False, conf, generer=False)
blocs = X.lire_blocs(X.MESSAGES.read_text(encoding="utf-8"))
mails = [b for b in blocs if b["meta"]["type"] == "email"]; reseau = [b for b in blocs if b["meta"]["type"] == "reseau"]
assert len(mails) == 4 and len(reseau) == 1 and n == 5, (len(mails), len(reseau))      # 2 boîtes x 2 max, 1 message réseau
assert {b["meta"]["box"] for b in mails} == set(BOITES) and all(b["statut"] == "à valider" and b["ok"] for b in mails), [b["texte"][:600] for b in mails if not b["ok"]]
assert all(X.R.LIGNE_STOP in b["corps"] and b["meta"]["box"] in b["corps"] for b in mails)   # signature + réponses dans la boîte qui écrit
assert "pageseule" in reseau[0]["texte"] and "À LA MAIN" in reseau[0]["texte"] and X.APERCU.exists()
assert X.cmd_preparer(False, conf, generer=False) == 0  # même jour : quota atteint
assert {l["statut"] for l in X.lire_trouves()} == {"préparé", "trouvé"}
ok_lien = lambda u: True
envoyes = []
fake = lambda box, mdp, msg: envoyes.append((box, msg))
assert X.cmd_envoyer(False, conf, fake, lambda s: None, ok_lien) == 0 and not envoyes   # rien de validé : aucun envoi
def valider(texte, id_): return X.marquer(texte, id_, "validé")
def statut_tous(ids, s):
    txt = X.MESSAGES.read_text(encoding="utf-8")
    for i in ids: txt = X.marquer(txt, i, s)
    X.MESSAGES.write_text(txt, encoding="utf-8")
statut_tous([b["id"] for b in mails + reseau], "validé")      # validé à la main, SANS accord Discord
assert X.cmd_envoyer(False, conf, fake, lambda s: None, ok_lien) == 0 and not envoyes   # refus : lot non approuvé sur Discord
statut_tous([b["id"] for b in mails[:3] + reseau], "à valider"); statut_tous([mails[3]["id"]], "refusé")   # Liam écarte un bloc
# Discord simulé (aucun réseau) : publication, puis « ok lot » / ✅ de Liam SEUL
UID, AUTRE, BOT = "42", "7", "999"; seq = [100]; msgs, reacts, posts = [], {}, []
X.acces_discord = lambda *a: ("jeton", "salon1", UID)
def api(jeton, m, chemin, corps=None):
    if m == "POST": seq[0] += 1; posts.append(corps["content"]); return {"id": str(seq[0])}
    if m == "PUT": reacts.setdefault(chemin.split("/")[4], []).append(BOT); return {}
    if "/reactions/" in chemin: return [{"id": u} for u in reacts.get(chemin.split("/")[4], [])]
    return [x for x in msgs if int(x["id"]) > int(chemin.split("after=")[1].split("&")[0])]
def dire(contenu, auteur=UID, bot=False, ref=None):
    seq[0] += 1; msgs.append({"id": str(seq[0]), "author": {"id": auteur, "bot": bot}, "content": contenu, **({"message_reference": {"message_id": ref}} if ref else {})})
from datetime import datetime as _dt
MATIN, SOIR = _dt(2026, 10, 28, 10, 0), _dt(2026, 10, 28, 17, 30)
assert X.heure_paris(_dt(2026, 7, 1, 12, 0, tzinfo=X.timezone.utc)).hour == 14 and X.heure_paris(_dt(2026, 1, 15, 12, 0, tzinfo=X.timezone.utc)).hour == 13   # heure de Paris, été et hiver
assert X.DEFAUT["heure_limite"] == "17:00"
# UN lot par boîte et par jour : une boîte à son quota (2) poste son lot ; l'autre (1 sur 2) attend l'heure limite
assert X.cmd_publier(True, conf, api, MATIN) == 2 and not posts and not X.etat_lire()["lots_discord"]        # à blanc : rien posté
assert X.cmd_publier(False, conf, api, MATIN) == 2 and len(posts) == 1
ld = X.etat_lire()["lots_discord"]; (lotA, vA), = ld.items(); boxA = vA["box"]; assert len(vA["ids"]) == 2 and not vA["incomplet"]
assert posts[0].startswith(f"<@42> Lot de {boxA} du {X.aujourdhui()} : 2 e-mails (quota 2). Palier du jour : 2 par boîte. Aperçu : apercu-lot.html. Réponds `ok lot` pour envoyer."), posts[0]
assert "• Elec Un, électricien, Rouen : site non adapté au mobile : <https://" in posts[0].replace("https://b2b", "https://b2b") or "• Elec Un, électricien, Rouen : site non adapté au mobile" in posts[0]
assert "Lot incomplet" not in posts[0] and "Elec Quatre" not in posts[0]
assert X.cmd_publier(False, conf, api, MATIN) == 0 and len(posts) == 1                                       # l'autre boîte : 1 sur 2, avant 17 h : rien
assert X.cmd_publier(False, {**conf, "palier": 2}, api, SOIR) == 1 and len(posts) == 2                       # après l'heure limite : lot incomplet, une fois
ld = X.etat_lire()["lots_discord"]; lotB = next(m for m in ld if m != lotA); boxB = ld[lotB]["box"]; assert boxB != boxA and ld[lotB]["incomplet"] and len(ld[lotB]["ids"]) == 1
assert posts[1].startswith(f"<@42> Lot de {boxB} du {X.aujourdhui()} : 1 e-mails (quota 2). Lot incomplet : 1 sur 2. Palier du jour : 2 par boîte."), posts[1]
assert X.cmd_publier(False, conf, api, SOIR) == 0 and X.cmd_publier(False, conf, api, MATIN) == 0 and len(posts) == 2   # jamais reposté (l'état est sur disque : redémarrage sans effet)
assert reacts[lotA] == [BOT] and reacts[lotB] == [BOT]
dire("ok lot", AUTRE); dire("ok lot", UID, bot=True); dire("ok lot demain peut-être"); reacts[lotB].append(AUTRE)
assert X.cmd_approuver(False, conf, api) == 0 and not X.etat_lire()["approuves"]                          # autre utilisateur, bot, phrase différente, ✅ d'un autre
assert X.cmd_approuver(True, conf, api) == 0
dire("OK lot !")                                                                                           # Liam seul, sans réponse : vise le DERNIER lot posté (celui de boxB), pas les deux
assert X.cmd_approuver(False, conf, api) == 1 and len(X.etat_lire()["approuves"]) == 1 and set(X.etat_lire()["approuves"]) == set(ld[lotB]["ids"])
assert X.cmd_approuver(False, conf, api) == 0 and len(X.etat_lire()["ok_utilises"]) == 1                    # ce « ok lot » est consommé : il n'ouvre pas l'autre lot
dire("ok lot", ref=lotA)                                                                                   # réponse au message du lot de boxA
assert X.cmd_approuver(False, conf, api) == 1 and len(X.etat_lire()["approuves"]) == 3
assert [b["statut"] for b in X.lire_blocs(X.MESSAGES.read_text(encoding="utf-8")) if b["meta"]["type"] == "email"] == ["validé"] * 3 + ["refusé"]
b_ = next(b for b in X.lire_blocs(X.MESSAGES.read_text(encoding="utf-8")) if b["id"] == ld[lotB]["ids"][0]); e_ = X.etat_lire()
b_["meta"] = {**b_["meta"], "box": boxA}; assert "lot approuvé est celui de" in X.refus(b_, e_, conf, set(), set(), lambda u: True)   # un lot part depuis SA boîte seulement
assert X.cmd_envoyer(True, conf, fake, lambda s: None, ok_lien) == 3 and not envoyes and "envoyé le" not in X.MESSAGES.read_text(encoding="utf-8")   # à blanc
assert X.cmd_envoyer(False, conf, fake, lambda s: None, lambda u: False) == 0 and not envoyes   # lien mort : refus
assert X.cmd_envoyer(False, conf, fake, lambda s: None, ok_lien) == 3 and len(envoyes) == 3
assert "pageseule" not in str([m["To"] for _, m in envoyes]) and all(m["List-Unsubscribe"] and "STOP" in m.get_content() for _, m in envoyes)
suivi = {r["nom"]: r for r in X.S.lire()}
assert [suivi[b["meta"]["nom"]]["statut"] for b in mails[:3]] == ["envoyé"] * 3 and suivi["Page Seule"]["statut"] == "à contacter"
assert X.cmd_envoyer(False, conf, fake, lambda s: None, ok_lien) == 0   # déjà envoyés
et3 = X.etat_lire(); assert sum(et3["envoyes"][str(date.today())].values()) == 3 and all(v <= 2 for v in et3["envoyes"][str(date.today())].values())

# --- plafond, STOP, texte modifié ---
txt = X.MESSAGES.read_text(encoding="utf-8")
X.S.statut(mails[3]["meta"]["nom"], "STOP", None, None, "test")
txt = valider(txt, mails[3]["id"]); X.MESSAGES.write_text(txt, encoding="utf-8")
e_ = X.etat_lire(); e_["approuves"].append(mails[3]["id"]); X.etat_ecrire(e_, False)   # (approuvé, mais STOP = exclu)
assert X.cmd_envoyer(False, conf, fake, lambda s: None, ok_lien) == 0   # STOP = exclusion définitive
cles, ml = X.exclusions(); assert X.S.cle(mails[3]["meta"]) in cles
b4 = dict(mails[0]); b4["corps"] = b4["corps"].replace(X.R.LIGNE_STOP, "")
etx = X.etat_lire(); etx["envois"].pop(b4["id"]); big = {**conf, "par_boite_par_jour": 50}; assert "plafond" in X.refus(b4, etx, conf, set(), set(), ok_lien); assert X.refus(b4, etx, big, set(), set(), ok_lien) == "ligne STOP absente"
b5 = dict(mails[0]); b5["corps"] += "\nOffre garantie, première page Google !"; assert "interdit" in X.refus(b5, etx, big, set(), set(), ok_lien)
b6 = dict(mails[0]); b6["meta"] = {**b6["meta"], "box": "inconnue@gmail.com"}; assert "boîte" in X.refus(b6, etx, big, set(), set(), ok_lien)

# --- relance J+2, une seule ---
nom0 = mails[0]["meta"]["nom"]; il_y_a_3 = str(date.today() - timedelta(days=3))
X.S.statut(nom0, "envoyé", None, il_y_a_3, "")
avant = X.MESSAGES.read_text(encoding="utf-8"); X.cmd_relances(True, {**conf, "par_boite_par_jour": 5}); assert X.MESSAGES.read_text(encoding="utf-8") == avant  # à blanc : rien écrit
n = X.cmd_relances(False, {**conf, "par_boite_par_jour": 5}); assert n == 1
rel = [b for b in X.lire_blocs(X.MESSAGES.read_text(encoding="utf-8")) if b["meta"] and b["meta"]["type"] == "relance"]
assert len(rel) == 1 and "une seule fois" in rel[0]["corps"] and X.R.LIGNE_STOP in rel[0]["corps"] and rel[0]["statut"] == "à valider"
conf5 = {**conf, "par_boite_par_jour": 5}
e_ = X.etat_lire(); e_["lots_discord"]["99999"] = {"ids": ["x"], "date": str(date.today() - timedelta(days=1)), "approuve": False}; e_["lots_box"] = {}; X.etat_ecrire(e_, False)   # lot d'hier, jamais approuvé ; lendemain : plus de lot posté ce jour-là
assert X.cmd_publier(False, {**conf5, "envoi_automatique": True}, api, SOIR) == 1 and "Envoi automatique ACTIVÉ" in posts[-1] and "relance J+2" in posts[-1]
envoyes.clear()
assert X.cmd_envoyer(False, conf5, fake, lambda s: None, ok_lien) == 0 and not envoyes             # relance publiée mais ni « ok lot » ni envoi automatique : rien
assert X.cmd_approuver(False, {**conf5, "envoi_automatique": True}, api) == 1                         # envoi automatique : lot DU JOUR d'office
assert not X.etat_lire()["lots_discord"]["99999"].get("approuve")                                        # le lot d'hier reste en attente
assert X.cmd_envoyer(False, conf5, fake, lambda s: None, ok_lien) == 1 and envoyes[0][1]["In-Reply-To"]
assert X.cmd_relances(False, {**conf, "par_boite_par_jour": 5}) == 0   # plus jamais de 2e relance
# --- démarrage (une fois par jour) et écoute ---
X.DERNIER, X.VERROU = tmp / "dernier.txt", tmp / "verrou"; appels = []
X.cmd_jour = lambda a, c: appels.append(a)
X.cmd_demarrage(True, conf5, api=api); assert appels == [True] and not X.DERNIER.exists() and not X.VERROU.exists()      # à blanc : date non écrite
t = [0]; dormir = lambda s: t.__setitem__(0, t[0] + 1800); horloge = lambda: t[0]; c1 = {**conf5, "ecoute_max_heures": 1}
X.cmd_demarrage(False, c1, dormir=dormir, api=api, envoi=fake, lien_ok=ok_lien, maintenant=horloge)
assert appels == [True, False] and X.DERNIER.read_text() == str(date.today()) and not X.VERROU.exists() and t[0] >= 3600    # lot d'hier en attente : écoute bornée à 1 h
X.cmd_demarrage(False, c1, dormir=dormir, api=api, envoi=fake, lien_ok=ok_lien, maintenant=horloge); assert appels == [True, False]   # pas de 2e journée le même jour
X.VERROU.write_text("1"); assert X.cmd_ecouter(False, c1) == 0 and X.VERROU.exists()                                                 # un écouteur tourne déjà
# --- fonctionnement continu (boucle) : horloge et pauses simulées, aucune recherche réelle, aucun réseau, rien d'envoyé ---
import json as _j, os as _os
X.VERROU_C, X.ARRET = tmp / "continu.verrou", tmp / "arret"
assert X.quota_jour(conf) == 4 and X.quota_jour({**X.DEFAUT}) == 20 and X.quota_jour({**X.DEFAUT, "quota_par_boite": 3}) == 6 and X.quota_jour({**X.DEFAUT}, 1) == 10   # 10 par boîte x boîtes, plafonné
assert X.processus_vivant(_os.getpid()) and not X.processus_vivant(99999999)

_ORIG = {n: getattr(X, n) for n in ("cmd_reponses", "cmd_chercher", "cmd_preparer", "cmd_relances", "cmd_publier", "cmd_approuver", "cmd_envoyer")}   # les scénarios remplacent ces étapes : remises en place avant les tests des salons
def scenario(nom, **kw):
    """Repart d'un état vide ; retourne (appels, horloge, dormir) pour une boucle simulée."""
    X.ETAT, X.MESSAGES, X.TROUVES = tmp / f"etat-{nom}.json", tmp / f"messages-{nom}.md", tmp / f"trouves-{nom}.csv"
    X.ETAT.write_text(json.dumps({"vagues": {"ouverte": 4, "ouvertures": {}}}), encoding="utf-8")   # toutes les vagues ouvertes : ces scénarios ne testent pas l'ouverture des vagues (voir le scénario « vagues »)
    X.ecrire_trouves([]); X.DERNIER.unlink(missing_ok=True); X.VERROU_C.unlink(missing_ok=True); X.ARRET.unlink(missing_ok=True)
    ap, h = [], [1_000_000.0]
    X.cmd_reponses = lambda a: ap.append(("reponses", h[0]))
    X.cmd_chercher = kw.get("chercher") or (lambda a, c: ap.append(("chercher", h[0])) or [])
    X.cmd_preparer = lambda a, c, **k: ap.append(("preparer", h[0])) or 0
    X.cmd_relances = lambda a, c: ap.append(("relances", h[0])) or 0
    X.cmd_publier = lambda a, c, **k: ap.append(("publier", c["envoi_automatique"])) or 0
    X.cmd_approuver = lambda a, c, **k: 0
    X.cmd_envoyer = kw.get("envoyer") or (lambda a, c, **k: ap.append(("envoyer",)) or 0)
    return ap, h, (lambda s: h.__setitem__(0, h[0] + s))

# 0. vagues : la vague 1 ne donne rien -> après 3 recherches sans nouveau, la vague 2 s'ouvre, puis la 3 et la 4 ; ensuite seulement la liste est déclarée épuisée
ap, h, dormir = scenario("vagues"); X.ETAT.write_text(json.dumps({}), encoding="utf-8"); cf = {**X.DEFAUT, "envoi_automatique": True}
X.cmd_continu(False, cf, dormir=dormir, maintenant=lambda: h[0], vivant=lambda: h[0] < 1_000_000 + 7200, lien_ok=ok_lien)
et = X.etat_lire(); rech = [x[1] for x in ap if x[0] == "chercher"]
assert len(rech) == 12 and et["vagues"]["ouverte"] == 4 and sorted(et["vagues"]["ouvertures"]) == ["2", "3", "4"] and X.ZN.VAGUE_MAX == 4, (len(rech), et["vagues"])
X.ZN.ouvrir(1)
ap, h, dormir = scenario("vagues0"); X.ETAT.write_text(json.dumps({}), encoding="utf-8"); cf = {**X.DEFAUT, "envoi_automatique": True, "seuil_vague": 0}   # seuil 0 : la vague 1 reste la seule ouverte
X.cmd_continu(False, cf, dormir=dormir, maintenant=lambda: h[0], vivant=lambda: h[0] < 1_000_000 + 7200, lien_ok=ok_lien)
assert len([x for x in ap if x[0] == "chercher"]) == 3 and X.vagues_etat(X.etat_lire())["ouverte"] == 1
X.ZN.ouvrir(1)

# 1. prospects épuisés : 3 recherches espacées de 10 min sans nouveau, puis veille ; la ligne de bilan dit pourquoi ; arrêt quand Jarvis s'arrête
ap, h, dormir = scenario("epuise"); cf = {**X.DEFAUT, "envoi_automatique": True}
X.cmd_continu(False, cf, dormir=dormir, maintenant=lambda: h[0], vivant=lambda: h[0] < 1_000_000 + 7200, lien_ok=ok_lien)
rech = [x[1] for x in ap if x[0] == "chercher"]
assert len(rech) == 3 and rech[1] - rech[0] >= 600 and rech[2] - rech[1] >= 600, rech          # pas de boucle serrée : un cycle toutes les 10 minutes
assert all(x[1] is False for x in ap if x[0] == "publier") and not X.VERROU_C.exists()          # jamais d'envoi automatique en mode continu
l = X.DERNIER.read_text(encoding="utf-8"); assert l.startswith(str(date.today())) and "épuisée" in l and "envoyés 0" in l and "bloqués 0" in l, l
n0 = len(ap); X.cmd_continu(False, cf, dormir=dormir, maintenant=lambda: h[0], vivant=lambda: h[0] < 1_000_000 + 10800, lien_ok=ok_lien)
assert len(ap) == n0 and "épuisée" in X.DERNIER.read_text(encoding="utf-8")                      # reprise après redémarrage : la journée finie n'est pas refaite
assert _j.loads(X.ETAT.read_text(encoding="utf-8"))["continu"]["fini"]

# 2. recul exponentiel après une erreur (10, 20, 40 min... plafonné à 60), retour à 10 min après un succès
def casse(a, c): ap.append(("chercher", h[0])); raise OSError("annuaire indisponible")
ap, h, dormir = scenario("recul", chercher=casse)
X.cmd_continu(False, {**X.DEFAUT}, dormir=dormir, maintenant=lambda: h[0], vivant=lambda: h[0] < 1_000_000 + 4 * 3600, lien_ok=ok_lien)
rech = [x[1] for x in ap if x[0] == "chercher"]; ecarts = [round((b - a) / 60) for a, b in zip(rech, rech[1:])]
assert ecarts[:3] == [20, 40, 60] and max(ecarts) <= 61, ecarts

# 3. quota atteint : 20 envoyés -> veille jusqu'au lendemain, ligne claire ; lot posté dès 5 e-mails prêts ou fin de quota
def envoie(a, c, **k):
    e = X.etat_lire(); e["envoyes"][X.aujourdhui()] = {BOITES[0]: 10, BOITES[1]: 10}; X.etat_ecrire(e, False)
ap, h, dormir = scenario("quota", envoyer=envoie)
X.cmd_continu(False, {**X.DEFAUT}, dormir=dormir, maintenant=lambda: h[0], vivant=lambda: h[0] < 1_000_000 + 3600, lien_ok=ok_lien)
l = X.DERNIER.read_text(encoding="utf-8"); assert "envoyés 20" in l and "quota atteint" in l and len([x for x in ap if x[0] == "chercher"]) == 1, l

# 4. commande de secours : « arreter » coupe la boucle proprement, même en pleine pause
ap, h, _ = scenario("arret")
def dormir_arret(s):
    h[0] += s
    if len([x for x in ap if x[0] == "chercher"]) >= 1: X.cmd_arreter()
X.VERROU_C.write_text("99999999"); X.cmd_arreter(); assert not X.ARRET.exists() and not X.VERROU_C.exists()            # aucune boucle : rien à couper, aucun reste
X.VERROU_C.unlink(missing_ok=True)
X.cmd_continu(False, {**X.DEFAUT}, dormir=dormir_arret, maintenant=lambda: h[0], lien_ok=ok_lien)
l = X.DERNIER.read_text(encoding="utf-8"); assert "arrêt demandé" in l and not X.ARRET.exists() and not X.VERROU_C.exists(), l
X.VERROU_C.write_text(str(_os.getpid())); assert X.cmd_continu(False, {**X.DEFAUT}, lien_ok=ok_lien) == 0 and X.VERROU_C.exists()   # une seule boucle à la fois
X.VERROU_C.unlink(missing_ok=True)
assert X.cmd_continu(True, {**X.DEFAUT}) == 0                                                                           # à blanc : rien lancé
# --- commerces et restaurants : codes NAF, page exemple obligatoire (fichier temporaire), textes propres à chaque métier ---
codes = dict(X.NAF)
assert len(X.NAF) == 17 and all(codes.get(c) for c in ("56.10A", "56.10C", "96.02A", "47.76Z", "10.71C", "10.71D", "45.20A")), X.NAF
assert X.NAF[:7] == X.NAF_BATIMENT and codes["56.10A"] == "restaurant" and codes["96.02A"] == "coiffeur" and codes["45.20A"] == "garage automobile"
assert (X.R.cle_metier("restauration rapide"), X.R.cle_metier("coiffeur"), X.R.cle_metier("fleuriste"), X.R.cle_metier("pâtisserie"), X.R.cle_metier("boulangerie"),
        X.R.cle_metier("garage automobile"), X.R.cle_metier("électricien"), X.R.cle_metier("plâtrier")) == ("restaurant", "coiffeur", "fleuriste", "boulangerie", "boulangerie", "garage", "electricien", None)
ICI0 = X.ICI; X.ICI = tmp   # liens-metiers.json temporaire : l'état réel des pages en ligne n'influence pas les tests
(tmp / "liens-metiers.json").write_text(X.json.dumps({"plombier-chauffagiste": "https://x/p/", "electricien": "https://x/e/", "restaurant": "https://x/r/"}), encoding="utf-8")
assert X.metiers_actifs() == {"plombier", "electricien", "restaurant"}
assert X.metier_actif("restaurant") and X.metier_actif("restauration rapide") and X.metier_actif("électricien")
assert not any(X.metier_actif(m) for m in ("coiffeur", "fleuriste", "boulangerie", "pâtisserie", "garage automobile", "plâtrier"))
assert X.enrichir({**cand, "metier": "coiffeur"}, et2, conf, lire, lambda c: ("", ""))[0] is None   # pas de page exemple : le prospect n'entre pas
_liens = X.ICI   # ici X.ICI est le dossier temporaire du bloc précédent
appels = []
def api2(dept, naf, page):
    appels.append(naf)
    return {"total_pages": 1, "results": [{"siren": f"{len(appels):05d}{k:03d}", "nom_complet": f"X {naf} {k}", "siege": {"code_postal": dept + "000", "libelle_commune": "ROUEN"}} for k in range(5)]}
et3 = {"curseur": {"i": 0, "page": 1}, "vus": {}}
c = X.candidats(et3, 9, api2, 0)     # trois métiers actifs : environ un tiers chacun, alternés bâtiment / commerce
par = {}
for x in c: par[x["metier"]] = par.get(x["metier"], 0) + 1
assert len(c) == 9 and par == {"électricien": 3, "restaurant": 3, "plombier-chauffagiste": 3}, par
assert not {"96.02A", "47.76Z", "10.71C", "10.71D", "45.20A", "43.91B", "43.99C"} & set(appels), appels   # sans page exemple : ni lus, ni marqués « vus »
assert len(et3["tampon"]["43.21A"]) == 2 and len(et3["vus"]) == 9   # les 5 résultats de la page : 3 livrés (vus), 2 gardés pour le prochain passage
c = X.candidats(et3, 9, api2, 0)
assert len(c) == 9 and len({x["siren"] for x in c}) == 9 and not {x["siren"] for x in c} & set(list(et3["vus"])[:9]), "pas de doublon d'un passage à l'autre"
c = X.candidats({"vus": {}}, 2, api2, 0)   # au moins un métier du bâtiment et un de commerce
assert {x["metier"] for x in c} == {"électricien", "restaurant"}, c
(_liens / "liens-metiers.json").write_text(X.json.dumps({"restaurant": "https://x/r/", "coiffeur": "https://x/c/", "electricien": "https://x/e/"}), encoding="utf-8")
c = X.candidats(et3, 9, api2, 0)   # le coiffeur s'active tout seul, depuis le début (Normandie)
assert "96.02A" in appels and any(x["metier"] == "coiffeur" and x["dept"] == "76" for x in c) and {x["metier"] for x in c} >= {"électricien", "restaurant", "coiffeur"}, (appels, c)
(_liens / "liens-metiers.json").write_text(X.json.dumps({"plombier": "https://x/p/", "electricien": "https://x/e/"}), encoding="utf-8")
c = X.candidats({"vus": {}}, 4, api2, 0)   # aucun commerce actif : le bâtiment seul, deux métiers
assert {x["metier"] for x in c} == {"électricien", "plombier-chauffagiste"} and len(c) == 4
(_liens / "liens-metiers.json").write_text("{}", encoding="utf-8")
assert X.candidats({"vus": {}}, 3, api2, 0) == []   # aucun métier actif : aucune lecture de l'annuaire
(_liens / "liens-metiers.json").write_text(X.json.dumps({"plombier-chauffagiste": "https://x/p/", "electricien": "https://x/e/", "restaurant": "https://x/r/"}), encoding="utf-8")
# migration de l'ancien curseur unique : progression et pages vues conservées
et4 = {"curseur": {"i": 7 * 2 + 3, "page": 5}, "vus": {"1": "x"}}   # 3e département, 4e métier (43.99C), page 5
cn = X.curseurs(et4)
assert cn["43.21A"] == {"i": 3, "page": 1} and cn["43.91B"] == {"i": 3, "page": 1} and cn["43.99C"] == {"i": 2, "page": 5} and cn["43.34Z"] == {"i": 2, "page": 1} and et4["vus"] == {"1": "x"}, cn
assert X.curseurs(et4) is cn and et4["curseur"].get("migre")   # une seule migration
et5 = {"curseur": {"i": 0, "page": 20}, "vus": {}, "curseurs_com": {"56.10A": {"i": 4, "page": 2}}}
cn = X.curseurs(et5); assert cn["43.21A"] == {"i": 0, "page": 20} and cn["43.22A"] == {"i": 0, "page": 1} and cn["56.10A"] == {"i": 4, "page": 2} and "curseurs_com" not in et5
# annuaire : l'API refuse -> nouveaux essais espacés, puis l'erreur remonte (la boucle recule)
import io, urllib.error
essais, pauses = [], []
def ouvrir(rq, timeout=0):
    essais.append(1)
    if len(essais) < 3: raise urllib.error.HTTPError(rq.full_url, 429, "Too Many Requests", {"Retry-After": "7"}, None)
    return io.BytesIO(b'{"results": [], "total_pages": 1}')
assert X.appel_api("76", "43.21A", 1, ouvrir, pauses.append) == {"results": [], "total_pages": 1} and len(essais) == 3 and pauses == [7, 3, 7, 10], pauses
def toujours_503(rq, timeout=0): raise urllib.error.HTTPError(rq.full_url, 503, "Service Unavailable", {}, None)
try: X.appel_api("76", "43.21A", 1, toujours_503, lambda s: None); raise SystemExit("503 permanent : l'erreur aurait dû remonter")
except urllib.error.HTTPError: pass
try: X.appel_api("76", "43.21A", 1, lambda rq, timeout=0: (_ for _ in ()).throw(urllib.error.HTTPError(rq.full_url, 400, "Bad Request", {}, None)), lambda s: None); raise SystemExit("400 : pas de nouvel essai")
except urllib.error.HTTPError: pass
assert X.DEFAUT["max_examinees"] == 300 and X.DEFAUT["par_boite_par_jour"] == 10
# constats vérifiables (aucune mesure réelle : outils injectés)
j = date(2026, 10, 27); vp = '<meta name="viewport" content="x"><a href="tel:0">a</a>'
assert [k for k, _ in X.constats_statiques("https://a.fr", vp + '<object data="a.swf"></object> © 2015', 4, j)] == ["copyright", "flash"]
tab_html = "<table cellpadding=0><tr><td>" + "<table><tr><td>a</td></tr></table>" * 3 + "</td></tr></table>"
assert "tableaux" in dict(X.constats_statiques("https://a.fr", vp + tab_html, 4, j)) and "tableaux" not in dict(X.constats_statiques("https://a.fr", vp + "<table><tr><td>x</td></tr></table><div></div>", 4, j))
conf2 = {**X.DEFAUT}; ok_o = {"mesure": lambda u: (80_000, 0.5), "statut": lambda u: 200, "psi": lambda u: 90, "https": lambda h: "absent"}
bon = '<title>Dupont, électricien à Rouen</title><meta name="description" content="Électricien à Rouen, devis gratuit">' + vp + "<h1>Dupont</h1> © 2026"
assert X.constats_site("https://a.fr", bon, conf2, {}, ok_o, j) == []
r = dict(X.constats_site("https://a.fr", bon, conf2, {}, {**ok_o, "mesure": lambda u: (2_300_000, 6.4)}, j)); assert r == {"lent": "la page d'accueil met 6,4 s à se charger", "lourd": "la page d'accueil pèse 2,3 Mo (code seul, hors images)"}, r
assert X.constats_site("https://a.fr", bon, conf2, {}, {**ok_o, "psi": lambda u: 38}, j) == [("pagespeed", "score PageSpeed mobile de 38 sur 100")]
assert X.constats_site("https://a.fr", bon, conf2, {"pagespeed": {X.aujourdhui(): 30}}, {**ok_o, "psi": lambda u: 1 / 0}, j) == []   # plafond du jour atteint : PageSpeed n'est pas appelé
carte = bon + '<iframe src="https://cartes.exemple/plan?x=1"></iframe>'
assert dict(X.constats_site("https://a.fr", carte, conf2, {}, {**ok_o, "statut": lambda u: 404}, j)) == {"iframe": "carte intégrée qui ne s'affiche plus (erreur 404 constatée)"}
assert X.constats_site("https://a.fr", carte, conf2, {}, {**ok_o, "statut": lambda u: 403}, j) == []   # seules les erreurs 404 et 410 comptent
r = dict(X.constats_site("http://a.fr", bon, conf2, {}, {**ok_o, "https": lambda h: "certificat"}, j)); assert "certificat" in r and "https" not in r
r = X.constats_site("http://a.fr", "<html>© 2010</html>", conf2, {}, ok_o, j); assert [k for k, _ in r][:4] == ["https", "mobile", "copyright", "appel"] and X.note_constats(r, j).count(" ; ") == 1   # le message en cite deux au plus
# adresses publiées sur le site de l'entreprise, simplement masquées
cf_mail = "contact@elec-dupont.fr"; cle_cf = 0x4f
hexs = "%02x" % cle_cf + "".join("%02x" % (ord(ch) ^ cle_cf) for ch in cf_mail)
assert X.decode_cf(hexs) == cf_mail and X.emails_page(f'<a class="__cf_email__" data-cfemail="{hexs}">[email&#160;protected]</a>', "elec-dupont.fr") == [(cf_mail, "generique")]
assert X.emails_page(f'<a href="/cdn-cgi/l/email-protection#{hexs}">écrire</a>', "elec-dupont.fr") == [(cf_mail, "generique")]
for masque in ("contact [arobase] elec-dupont [point] fr", "contact(at)elec-dupont(dot)fr", "contact arobase elec-dupont.fr", "contact&#64;elec-dupont.fr", "contact{at}elec-dupont{dot}fr"):
    assert X.emails_page("Écrivez-nous : " + masque, "elec-dupont.fr") == [(cf_mail, "generique")], masque
assert X.emails_page('<script type="application/ld+json">{"@type":"Electrician","email":"mailto:contact@elec-dupont.fr"}</script>', "elec-dupont.fr") == [(cf_mail, "generique")]
assert X.emails_page('{"email":"contact\\u0040elec-dupont.fr"}', "elec-dupont.fr") == [(cf_mail, "generique")]
assert X.emails_page('<span itemprop="email">contact@elec-dupont.fr</span>', "elec-dupont.fr") == [(cf_mail, "generique")]
assert X.emails_page('{"email":"studio@agence-web.fr"} <a data-cfemail="' + "%02x" % cle_cf + "".join("%02x" % (ord(ch) ^ cle_cf) for ch in "pub@regie-pub.com") + '">x</a>', "elec-dupont.fr") == []   # autre domaine : jamais
# site avec seulement un formulaire de contact : message à coller à la main, compté à part
form_page = '<form action="/envoi"><input name="nom"><textarea name="message"></textarea></form>'
assert X.a_formulaire(form_page) and not X.a_formulaire('<form><input name="q"></form>') and not X.a_formulaire('<form class="newsletter"><textarea></textarea></form>')
pages_f = {"http://elecdupont.fr": ("http://elecdupont.fr", {}, '<html>Rouen <a href="/contact">c</a> © 2015</html>'), "http://elecdupont.fr/contact": ("http://elecdupont.fr/contact", {}, "Rouen " + form_page)}
st = {}
l, m = X.enrichir(cand, {"recherches": {}}, conf, lambda u: pages_f.get(u), lambda c: ("", ""), stat=st)
assert l and not l["email"] and l["formulaire"] == "http://elecdupont.fr/contact" and st["canal"] == "formulaire" and st["faible"] and st["site"] and "https" in st["constats"], (l, m, st)
r, err = X.construire_bloc({"nom": "Chez Test", "metier": "restaurant", "ville": "Rouen", "email": "", "formulaire": "http://x/contact", "notebesoin": "site sans HTTPS (constaté le 27/10)", "telephone": ""},
                           {"prenom_nom": "Liam Test", "entreprise": "LM", "siret": "12345678901234", "telephone": "06 00 00 00 00", "email_reponse": "a@b.fr"}, [], {}, "", exemple="https://x/exemple/")
assert err is None and '"type": "formulaire"' in r[1] and "COLLER À LA MAIN" in r[1] and "Message pour le formulaire de contact" in r[1] and "✅ prêt à relire" in r[1] and "- Canal : formulaire de contact http://x/contact" in r[1], r
# rapport : examinées par métier, sites faibles, e-mails, par constat
tab = {}
X.compter(tab, "électricien", {"site": True, "faible": True, "constats": ["https", "mobile"], "canal": "email"})
X.compter(tab, "électricien", {"site": False, "faible": False, "constats": [], "canal": "reseau"})
X.compter(tab, "restaurant", {"site": True, "faible": False, "constats": [], "canal": ""})
assert tab["électricien"]["examinees"] == 2 and tab["électricien"]["constats"] == {"https": 1, "mobile": 1} and tab["électricien"]["email"] == 1 and tab["électricien"]["sans_site"] == 1 and tab["restaurant"]["site"] == 1
txt = X.rapport_texte(tab, "Test"); assert all(m in txt for m in ("électricien", "restaurant", "TOTAL", "Goulot", "https 1")) and X.re.search(r"TOTAL\s+3\s+1\s+2\s+1\s+1\s+0\s+1\b", txt), txt
ident_t = {"prenom_nom": "Liam Test", "entreprise": "LM MULTI-SERVICES", "siret": "12345678901234", "telephone": "06 00 00 00 00", "email_reponse": "ecrire@exemple.fr"}
def texte_bloc(metier):
    r, err = X.R.bloc({"nom": "Chez Test", "metier": metier, "ville": "Rouen", "email": "contact@cheztest.fr", "emailtype": "generique", "emailsource": "page contact de son site",
                       "notebesoin": "site non adapté au mobile (constaté le 27/10)", "telephone": ""}, ident_t, [], {}, "https://x/exemple/")
    assert err is None and "⛔" not in r[1] and "(exemple, pas votre site)" in r[1] and X.R.LIGNE_STOP in r[1] and not X.R.INTERDITS.search(r[1].split("### E-mail")[1]), (metier, err, r and r[1])
    return r[1].lower()
t = texte_bloc("restaurant")
assert all(m in t for m in ("restaurateurs", "carte", "horaires", "accès", "réserv")) and "panne" not in t and "fuite" not in t and "travaux" not in t, t
t = texte_bloc("restauration rapide"); assert "panne" not in t and "carte" in t
for metier, mots in (("coiffeur", ("coiffeurs", "rendez-vous", "prestations")), ("fleuriste", ("fleuristes", "compositions", "commande")),
                     ("boulangerie", ("boulangers", "horaires")), ("pâtisserie", ("boulangers",)), ("garage automobile", ("garagistes", "rendez-vous", "horaires"))):
    t = texte_bloc(metier)
    assert all(m in t for m in mots) and not any(m in t for m in ("panne", "fuite", "zone d'intervention", "classement")), (metier, t)
t = texte_bloc("électricien"); assert "panne" in t and "électriciens" in t   # le bâtiment garde ses textes (l'e-mail ne décrit plus le contenu de la page : « zone d'intervention » n'y figure plus)
orig_c, orig_e = X.candidats, X.enrichir
lots = [[{"siren": "777777777", "nc": "ELEC TEST", "metier": "électricien", "cp": "76000", "ville": "Rouen", "dept": "76"}], []]
X.candidats = lambda etat, n, *a, **k: lots.pop(0)
def faux_enrichir(c, etat, conf, stat=None, **k):
    stat.update(site=True, faible=True, constats=["https"], canal="formulaire")
    return {**{k_: "" for k_ in X.COLS}, "nom": "Elec Test", "metier": c["metier"], "ville": "Rouen", "siren": c["siren"], "formulaire": "http://x/contact", "statut": "trouvé"}, None
X.enrichir = faux_enrichir
CHERCHER_REEL(False, {**X.DEFAUT})
e = X.etat_lire(); assert e["stats"]["cumul"]["électricien"]["formulaire"] == 1 and e["stats"]["jours"][X.aujourdhui()]["électricien"]["constats"] == {"https": 1}, e.get("stats")
X.candidats, X.enrichir = orig_c, orig_e
X.cmd_rapport(X.DEFAUT)
# --- découverte depuis les sites (OpenStreetMap), modèle « pas de site trouvé », SMS, liste d'appels, saisies de Liam : tout est simulé, aucun réseau, rien n'est envoyé ---
(X.ICI / "liens-metiers.json").write_text(X.json.dumps({"plombier-chauffagiste": "https://x/p/", "electricien": "https://x/e/", "restaurant": "https://x/r/", "coiffeur": "https://x/c/", "fleuriste": "https://x/f/",
                                                         "boulangerie": "https://x/b/", "garage": "https://x/g/"}), encoding="utf-8")
conf3 = {**X.DEFAUT, "pause_site_s": 0}
rq = X.requete_overpass(["craft=electrician", "craft=hvac"], {"id": "rouen-40km", "type": "rayon"}, conf3)
assert 'nwr["craft"="electrician"](around:40000,49.4431,1.0993);' in rq and 'nwr["craft"="hvac"]' in rq and "out center tags" in rq, rq
X.ZN.ouvrir(1)
assert 'ref:INSEE"="27"' in X.requete_overpass(["shop=bakery"], {"id": "dept-27", "type": "dept", "dept": "27"}, conf3) and X.zones_osm()[0]["id"] == "rouen-40km" and [z["id"] for z in X.zones_osm()[1:]] == ["dept-76", "dept-27"]
assert "(around:20000,49.4938,0.1077)" in X.requete_overpass(["craft=roofer"], {"id": "havre-20km", "type": "rayon", "centre": (49.4938, 0.1077), "rayon": 20000}, conf3) and {"taxi", "auto-école", "esthéticienne"} <= {m for _, m in X.NAF_COMMERCES} and {"taxi", "auto-école", "esthéticienne"} <= {m for m, _ in X.OSM_METIERS}
els = {"elements": [
    {"type": "node", "id": 1, "tags": {"name": "ELEC DURAND", "addr:city": "Rouen", "addr:postcode": "76000", "website": "elecdurand.fr", "contact:email": "Contact@ElecDurand.fr", "phone": "+33 2 35 00 00 01"}},
    {"type": "way", "id": 2, "center": {}, "tags": {"name": "Sans commune", "phone": "02 35 00 00 02"}}, {"type": "node", "id": 3, "tags": {"addr:city": "Rouen"}},
    {"type": "node", "id": 4, "tags": {"name": "Plomberie Petit", "addr:city": "Elbeuf", "addr:postcode": "76500", "contact:phone": "02 35 00 00 04;02 35 00 00 05"}}]}
cs_ = X.candidats_osm(els, "électricien")
assert [c["id"] for c in cs_] == ["node/1", "node/4"] and cs_[0]["site"] == "https://elecdurand.fr" and cs_[0]["emails"] == ["contact@elecdurand.fr"] and cs_[0]["telephone"] == "02 35 00 00 01" and cs_[1]["telephone"] == "02 35 00 00 04", cs_
vus_rq = []
def ouvrir_ov(rq_, timeout=0): vus_rq.append(rq_); return io.BytesIO(b'{"elements": []}')
X.appel_overpass("[out:json];", ouvrir_ov, lambda s: None); ua = vus_rq[0].get_header("User-agent")
assert ua.startswith("LM-MULTI-SERVICES-prospection") and "1 requête à la fois" in ua and vus_rq[0].data.startswith(b"data=")
assert X.email_valide("a.b@x.fr") and not X.email_valide("pas un mail") and not X.email_valide("a@b")
assert all(X.email_plateforme(a) for a in ("support@wix.com", "x@ovh.net", "y@ionos.fr", "z@sentry.io", "me@wixpress.com")) and not X.email_plateforme("contact@elecdurand.fr")
# enrichir_osm : un seul accès à la page d'accueil, ordre des adresses, formulaire, téléphone seulement
acces = []
def faux_lire(pages):
    def lire_(u, chrono=None):
        acces.append(u); p_ = pages.get(u)
        if not p_: return None
        if chrono is not None: chrono["sec"], chrono["octets"] = 0.3, len(p_)
        return (u, {}, p_)
    return lire_
VP = '<meta name="viewport" content="x">'
faible = "<html>Rouen " + VP + " © 2012 <a href=\"/contact\">contact</a></html>"   # © ancien, aucun lien d'appel
outils_t = {"https": lambda h: "absent", "statut": lambda u: 200}
base_c = {"id": "node/10", "nom": "Elec Durand", "metier": "électricien", "ville": "Rouen", "cp": "76000", "site": "https://elecdurand.fr", "emails": [], "telephone": "02 35 00 00 01"}
def essai(c, pages, **kw):
    acces.clear(); st_ = {}; l_, m_ = X.enrichir_osm({**base_c, **c}, {"recherches": {}}, conf3, faux_lire(pages), outils_t, st_, lambda s: None); return l_, m_, st_
l, m, st_ = essai({"emails": ["support@wix.com", "contact@elecdurand.fr"]}, {"https://elecdurand.fr": faible})
assert l["email"] == "contact@elecdurand.fr" and l["email_source"] == "OpenStreetMap (tag email)" and st_["canal"] == "email" and "copyright" in st_["constats"] and acces.count("https://elecdurand.fr") == 1 and "modele" in l and l["modele"] == "", (l, m)
l, m, st_ = essai({}, {"https://elecdurand.fr": faible.replace("</html>", '<a href="mailto:info@elecdurand.fr">m</a></html>')})
assert l["email"] == "info@elecdurand.fr" and "page d'accueil" in l["email_source"] and acces.count("https://elecdurand.fr") == 1, (l, m)
l, m, st_ = essai({}, {"https://elecdurand.fr": faible, "https://elecdurand.fr/contact": "Rouen écrire : bureau@elecdurand.fr"})
assert l["email"] == "bureau@elecdurand.fr" and "contact / mentions" in l["email_source"] and acces.count("https://elecdurand.fr") == 1, (l, m)
l, m, st_ = essai({}, {"https://elecdurand.fr": faible, "https://elecdurand.fr/contact": "Rouen <form><textarea name=message></textarea></form>"})
assert not l["email"] and l["formulaire"] == "https://elecdurand.fr/contact" and st_["canal"] == "formulaire" and l["statut"] == "trouvé", (l, m)
l, m, st_ = essai({}, {"https://elecdurand.fr": faible})
assert l["statut"] == "téléphone seulement" and l["telephone"] and st_["canal"] == "telephone" and st_["site"] and not st_["telephone"], (l, m)
l, m, st_ = essai({"telephone": ""}, {"https://elecdurand.fr": faible}); assert l is None and "aucun" in m
l, m, st_ = essai({}, {"https://elecdurand.fr": '<html><title>Elec Durand, électricien à Rouen</title><meta name="description" content="Électricien à Rouen, devis gratuit"><h1>Durand</h1>Rouen ' + VP + '<a href="tel:0235000001">a</a> © 2026</html>'}); assert l is None and m.startswith("site correct") and st_["site"] and not st_["faible"]
# fiche sans site : domaines usuels testés (jamais devinés au-delà), modèle « pas de site trouvé »
l, m, st_ = essai({"site": "", "telephone": "02 35 00 00 01"}, {})
assert l["statut"] == "sans site, téléphone" and l["modele"] == "sans-site" and l["osm"] == "node/10" and st_["telephone"] and st_["canal"] == "telephone" and 1 <= len(acces) <= 4 and all(a.startswith("https://") for a in acces), (l, m, acces)
l, m, st_ = essai({"site": "", "emails": ["contact@elecdurand.fr"]}, {})
assert l["email"] == "contact@elecdurand.fr" and l["modele"] == "sans-site" and l["statut"] == "trouvé" and st_["canal"] == "email", (l, m)
l, m, st_ = essai({"site": "", "telephone": ""}, {}); assert l is None
l, m, st_ = essai({"site": "https://elecdurand.fr", "telephone": "02 35 00 00 01"}, {})   # site déclaré mais illisible (robots ou panne) : aucune affirmation sur ce site
assert l is None and "aucun constat vérifié" in m, (l, m)   # règle permanente : sans constat vérifié sur son site, l'entreprise est exclue
# exclusions permanentes : chaînes, services publics, site de réseau, domaine partagé
assert X.motif_exclusion("La Taverne Alsacienne", "rouen@lestavernes.com", "https://www.lestavernes.com/rouen-bonsecours/") and X.motif_exclusion("Restaurant universitaire du Madrillet", "r@crous-normandie.fr")
assert not X.motif_exclusion("Auto-école Dupont") and not X.motif_exclusion("Elec Durand", "contact@elecdurand.fr", "https://elecdurand.fr/accueil")
assert X.motif_exclusion("A", "a@groupe.fr", "", X.partages_connus([{"nom": "A", "ville": "X", "email": "a@groupe.fr"}, {"nom": "B", "ville": "Y", "email": "b@groupe.fr"}])) == "domaine partagé entre plusieurs établissements"
# message « pas de site trouvé » : formule exacte, jamais « vous n'avez pas de site », STOP, lien de la page exemple, aucun ⚠ sur ce point
ident_o = {"prenom_nom": "Liam Test", "entreprise": "LM MULTI-SERVICES", "siret": "12345678901234", "telephone": "06 00 00 00 00", "email_reponse": "ecrire@exemple.fr"}
r, err = X.R.bloc({"nom": "Chez Durand", "metier": "coiffeur", "ville": "Rouen", "email": "contact@chezdurand.fr", "emailtype": "generique", "emailsource": "OpenStreetMap (tag email)", "modele": "sans-site", "telephone": ""}, ident_o, [], {}, "https://x/c/")
assert err is None and "je n'ai pas trouvé de site à votre nom" in r[1].lower() and not X.re.search(r"vous n.avez pas de site", r[1], X.re.I) and X.R.LIGNE_STOP in r[1] and "https://x/c/ (exemple, pas votre site)" in r[1] and "⛔" not in r[1] and "⚠" not in r[1], r[1]
assert X.R.INTERDITS.search("Vous n'avez pas de site, monsieur") and X.R.INTERDITS.search("première page")
# accroche (2 phrases) et SMS (300 caractères au plus, identification, STOP) pour tous les métiers actifs
for libelle in ("électricien", "plombier-chauffagiste", "restaurant", "coiffeur", "fleuriste", "boulangerie", "garage automobile"):
    cle = X.R.cle_metier(libelle); lig = {"nom": "Chez Test", "ville": "Saint-Étienne-du-Rouvray", "metier": libelle}
    sms = X.R.sms_appel(lig, ident_o, cle, "https://b2b-demos.vercel.app/atelier-ciseaux-exemple-d853d203/"); acc = X.R.accroche_appel(lig, ident_o, cle, "site non adapté au mobile (constaté le 27/10)")
    assert len(sms) <= 300 and "STOP" in sms and "Liam Test" in sms and "LM MULTI-SERVICES" in sms and "exemple, pas votre site" in sms and not X.R.INTERDITS.search(sms), (libelle, len(sms), sms)
    assert acc.count(". ") == 1 and acc.endswith(".") and len(X.re.findall(r"\.", acc.replace("(constaté le 27/10)", ""))) == 2 and "constaté" in acc and not X.R.INTERDITS.search(acc), acc
# liste d'appels : 20 lignes au plus, tous métiers actifs, colonnes à remplir, cases à cocher
X.DOCS = tmp / "docs"; X.DOCS.mkdir(exist_ok=True)
lignes_a = [{**{k: "" for k in X.COLS}, "nom": f"{lib[:3].title()} Entreprise {i}", "ville": "Rouen", "metier": lib, "telephone": f"02 35 00 {i:02d} 0{j}", "statut": X.STATUTS_TEL[i % 2], "osm": f"node/{i}{j}", "modele": "sans-site"}
            for j, lib in enumerate(("électricien", "restaurant", "coiffeur")) for i in range(1, 11)]
X.ecrire_trouves(lignes_a)
conf20 = {**X.DEFAUT, "appels_par_jour": 20}
choisies = X.choisir_appels(lignes_a, {}, conf20, set())
par_m = {}
for l in choisies: par_m[l["metier"]] = par_m.get(l["metier"], 0) + 1
assert len(choisies) == 20 and min(par_m.values()) >= 6 and len({X.S.cle(l) for l in choisies}) == 20 and set(par_m) == {"électricien", "restaurant", "coiffeur"}, par_m
exclue = {X.S.cle(choisies[0])}; assert X.S.cle(choisies[0]) not in {X.S.cle(l) for l in X.choisir_appels(lignes_a, {}, conf20, exclue)}
etat_t = X.etat_lire(); etat_t.pop("appels", None); X.etat_ecrire(etat_t, False)
assert X.cmd_appels(False, conf3, jour="2026-10-27") == 0 and not (X.DOCS / "liste-appels-2026-10-27.md").exists()   # par défaut (14/11/2026) : plus aucun liste-appels-*.md
conf3 = {**conf3, "appels_par_jour": 20, "liste_appels_md": True}
assert X.cmd_appels(False, conf3, jour="2026-10-28") == 20 and X.cmd_appels(False, conf3, jour="2026-10-28") == 0   # une seule liste par jour
fichier = X.DOCS / "liste-appels-2026-10-28.md"; md = fichier.read_text(encoding="utf-8")
assert "e-mail trouvé (à remplir par Liam)" in md and "lien Facebook / fiche Google (à remplir)" in md and md.count("<!-- k:") == 20 and md.count("[ ] | [ ] | [ ] | [ ]") == 20 and "OpenStreetMap" in md and "ODbL" in md
assert all(len(m_.group(1)) <= 300 for m_ in X.re.finditer(r"SMS \(\d+ caractères\) : `(.+?)`", md)) and md.count("STOP") >= 21 and "Rien n'est envoyé" in md
assert sum(1 for l in X.lire_trouves() if l["statut"] == "listé") == 20
assert "## Bloc 1 sur 1" in md and "### Suivi, bloc 1" in md and "## Créneaux conseillés" in md   # blocs de 25, tableau de suivi, créneaux
# reprise : les numéros listés mais jamais appelés reviennent d'abord (liste la plus récente en premier), puis des nouveaux ; appelé ou refus = jamais repris
cles_l = [m_.group(1).replace("~", "|") for m_ in X.re.finditer(r"<!-- k:(.+?) -->", md)]
rep = X.choisir_appels(lignes_a, {}, {**X.DEFAUT, "appels_par_jour": 25}, set())
assert [X.S.cle(l) for l in rep[:20]] == cles_l and len(rep) == 25 and not ({X.S.cle(l) for l in rep[20:]} & set(cles_l)), len(rep)
fichier.write_text(md.replace("[ ] | [ ] | [ ] | [ ]", "[x] | [ ] | [ ] | [ ]", 1), encoding="utf-8")
assert cles_l[0] not in [X.S.cle(l) for l in X.choisir_appels(lignes_a, {}, conf20, set())]
fichier.write_text(md.replace("[ ] | [ ] | [ ] | [ ]", "[ ] | [ ] | [x] | [ ]", 1), encoding="utf-8")
assert cles_l[0] not in [X.S.cle(l) for l in X.choisir_appels(lignes_a, {}, conf20, set())]
fichier.write_text(md, encoding="utf-8")
# Liam remplit le tableau : adresse valide -> prochain lot ; adresse invalide ignorée ; refus et STOP -> exclusion définitive ; lien noté, jamais ouvert
lignes_md = md.split("\n"); idx = [i for i, l_ in enumerate(lignes_md) if "<!-- k:" in l_]
def remplir(i, col, val): c_ = lignes_md[i].strip().strip("|").split("|"); c_[col] = f" {val} "; lignes_md[i] = "| " + " | ".join(x.strip() for x in c_) + " |"
cle1, cle2, cle3, cle4, cle5 = [X.re.search(r"<!-- k:(.+?) -->", lignes_md[idx[n]]).group(1).replace("~", "|") for n in range(5)]
remplir(idx[0], 6, "Contact@ChezUn.fr"); remplir(idx[0], 7, "https://www.facebook.com/chezun")
remplir(idx[1], 10, "[x]"); remplir(idx[2], 11, "[X]"); remplir(idx[3], 6, "pas-un-mail"); remplir(idx[4], 6, "contact@chezun.fr")
fichier.write_text("\n".join(lignes_md), encoding="utf-8")
assert X.integrer_saisies(False, conf3) == 1
par = {X.S.cle(l): l for l in X.lire_trouves()}
assert par[cle1]["email"] == "contact@chezun.fr" and par[cle1]["statut"] == "trouvé" and par[cle1]["email_type"] == "saisi" and "Liam" in par[cle1]["email_source"] and par[cle1]["fiche_web"] == "https://www.facebook.com/chezun" and par[cle1]["modele"] == "sans-site"
assert par[cle2]["statut"] == "refusé" and par[cle3]["statut"] == "STOP" and par[cle4]["statut"] != "trouvé" and not par[cle4]["email"] and not par[cle5]["email"], [par[c_]["statut"] for c_ in (cle2, cle3, cle4, cle5)]
cles_x, mails_x = X.exclusions(); assert cle2 in cles_x and cle3 in cles_x and cle1 not in cles_x
assert X.integrer_saisies(False, conf3) == 0   # relecture suivante : rien de nouveau
assert cle2 not in {X.S.cle(l) for l in X.choisir_appels(X.lire_trouves(), X.etat_lire(), X.DEFAUT, X.exclusions()[0] | set(X.etat_lire()["appels"]["exclus"]))}
# découverte complète simulée : requêtes une à une avec pauses, exclusions, doublons, SMS stockés non envoyés, rapport
def ouvrir_osm(rq_, timeout=0):
    d = X.urllib.parse.parse_qs(rq_.data.decode())["data"][0]
    if "craft" in d and "electrician" in d: els_ = [{"type": "node", "id": 101, "tags": {"name": "Elec Nord", "addr:city": "Rouen", "addr:postcode": "76000", "website": "https://elecnord.fr", "phone": "02 35 11 00 01"}}]
    elif "amenity" in d: els_ = [{"type": "node", "id": 201, "tags": {"name": "Chez Marcel", "addr:city": "Rouen", "addr:postcode": "76000", "phone": "02 35 11 00 02"}}, {"type": "node", "id": 202, "tags": {"name": "Chez Lucie", "addr:city": "Rouen", "addr:postcode": "76000", "email": "lucie@chezlucie.fr"}}]
    else: els_ = []
    return io.BytesIO(X.json.dumps({"elements": els_}).encode())
pages_o = {"https://elecnord.fr": "<html>Rouen © 2011</html>"}
pauses_o = []
conf4 = {**X.DEFAUT, "pause_site_s": 0, "pause_overpass_s": 15, "osm_requetes_par_passage": 2, "osm_max_examinees": 10}
etat_t = X.etat_lire(); etat_t.pop("osm", None); etat_t.pop("stats_osm", None); etat_t.pop("sans_site_telephone", None); X.etat_ecrire(etat_t, False)
nv = X.cmd_decouvrir(False, conf4, ouvrir_osm, faux_lire(pages_o), pauses_o.append, outils_t)
e_ = X.etat_lire(); noms_nv = {l["nom"]: l for l in nv}
assert e_["osm"]["faits"] == ["rouen-40km|électricien", "rouen-40km|plombier-chauffagiste"] and pauses_o.count(15) == 1, (e_["osm"]["faits"], pauses_o)
assert noms_nv["Elec Nord"]["statut"] == "téléphone seulement" and "osm:node/101" in e_["vus"], noms_nv
nv2 = X.cmd_decouvrir(False, conf4, ouvrir_osm, faux_lire(pages_o), pauses_o.append, outils_t)   # 2e passage : requêtes suivantes (restaurant, coiffeur), pas de doublon
noms2 = {l["nom"]: l for l in nv2}; e_ = X.etat_lire()
assert len(e_["osm"]["faits"]) == 4 and noms2["Chez Marcel"]["statut"] == "sans site, téléphone" and noms2["Chez Lucie"]["email"] == "lucie@chezlucie.fr" and noms2["Chez Lucie"]["modele"] == "sans-site" and "Elec Nord" not in noms2, noms2
tel_o = e_["sans_site_telephone"]; assert "restaurant" in tel_o and "électricien" in tel_o and all(len(v["sms"]) <= 300 and "STOP" in v["sms"] and v["sms_envoye"] is False for m_ in tel_o.values() for v in m_.values()), tel_o
assert e_["stats_osm"]["cumul"]["restaurant"]["telephone"] == 1 and e_["stats_osm"]["cumul"]["restaurant"]["email"] == 1 and e_["stats_osm"]["cumul"]["électricien"]["telephone"] == 1 and e_["stats_osm"]["cumul"]["électricien"]["site"] == 1
# STOP déjà enregistré : une fiche OSM du même nom et de la même commune n'est pas reprise
etat_t = X.etat_lire(); etat_t["osm"]["tampon"] = [{"id": "node/301", "nom": X.R.G.slug and "Chez Marcel", "metier": "restaurant", "ville": "Rouen", "cp": "", "site": "", "emails": ["marcel@chezmarcel.fr"], "telephone": "02 35 11 00 02"}]; X.etat_ecrire(etat_t, False)
assert X.cmd_decouvrir(False, conf4, ouvrir_osm, faux_lire(pages_o), pauses_o.append, outils_t) == [] and X.etat_lire()["vus"]["osm:node/301"] == "exclu ou déjà connu"
assert X.DEFAUT["decouverte_osm"] is False and X.DEFAUT["appels_par_jour"] == 100 and X.DEFAUT["liste_appels_heure"] == "08:00"
tab_o = {}; X.compter(tab_o, "coiffeur", {"site": False, "faible": False, "constats": [], "canal": "telephone"}); X.compter(tab_o, "coiffeur", {"site": True, "faible": True, "constats": ["appel"], "canal": "formulaire"})
tx_o = X.rapport_texte(tab_o, "OSM"); assert "tél. seul" in tx_o and X.re.search(r"coiffeur\s+2\s+1\s+1\s+1\s+0\s+1\s+0\s+1", tx_o), tx_o

# --- montée en charge : 10, puis +10 par jour jusqu'au plafond ; gel + alerte Discord si les rebonds ou plaintes montent ---
X.ETAT, X.RETOURS = tmp / "montee.json", tmp / "retours.json"; cm = {**X.DEFAUT}; alertes = []
def api_m(jeton, m, chemin, corps=None): alertes.append(corps["content"]); return {"id": "1"}
paliers = [X.avec_montee(cm, False, api_m, date(2026, 10, 29) + timedelta(days=i))["palier"] for i in range(-1, 6)]
assert paliers == [10, 10, 20, 30, 40, 50, 50] and X.etat_lire()["montee"]["depart"] == "2026-10-29", paliers   # départ le lendemain du premier appel (28/10) ; plafond 50
assert X.avec_montee({**cm, "montee_plafond": 30}, False, api_m, date(2026, 11, 20))["par_boite_par_jour"] == 30 and X.avec_montee({**cm, "montee": False})["par_boite_par_jour"] == 10
e_ = X.etat_lire(); e_["montee"].pop("gele", None); e_["envoyes"] = {"2026-10-30": {"a@x.fr": 60, "b@x.fr": 60}}; X.etat_ecrire(e_, False)
X.RETOURS.write_text(X.json.dumps({"rebonds": {f"m{i}": "2026-10-30" for i in range(3)}, "plaintes": {}}), encoding="utf-8")
assert X.avec_montee(cm, False, api_m, date(2026, 10, 31))["palier"] == 30 and not alertes and not X.etat_lire()["montee"].get("gele")   # 3 rebonds sur 120 envois (2,5 %) : on continue
X.RETOURS.write_text(X.json.dumps({"rebonds": {f"m{i}": "2026-10-30" for i in range(8)}, "plaintes": {}}), encoding="utf-8")
c_ = X.avec_montee(cm, False, api_m, date(2026, 10, 31)); assert c_["palier"] == 30 and c_["montee_gelee"] and len(alertes) == 1 and "<@42>" in alertes[0] and "Palier figé à 30" in alertes[0], alertes   # 8 sur 120 : gel au palier du jour + alerte
assert X.avec_montee(cm, False, api_m, date(2026, 11, 3))["palier"] == 30 and len(alertes) == 1                       # gelé : plus d'augmentation, alerte une seule fois
e_ = X.etat_lire(); e_["envoyes"] = {"2026-10-20": {"a@x.fr": 120}}; X.etat_ecrire(e_, False); X.RETOURS.write_text(X.json.dumps({"rebonds": {f"m{i}": "2026-10-20" for i in range(8)}, "plaintes": {}}), encoding="utf-8")   # anciens retours
X.cmd_montee(False, cm, True); e_ = X.etat_lire(); assert not e_["montee"].get("gele") and X.palier_du_jour(e_, cm, date.today()) == 30   # --reprendre : repart du palier figé
X.RETOURS.write_text(X.json.dumps({"rebonds": {}, "plaintes": {"p1": str(date.today())}}), encoding="utf-8")
assert X.avec_montee(cm, False, api_m, date.today())["montee_gelee"]                                              # une plainte suffit
e_ = X.etat_lire(); e_["envoyes"] = {X.aujourdhui(): {"a@x.fr": 2}}; assert X.annonce_envoi(e_, api_m) and alertes[-1] == "Envoyé : 2. Réponses : 0. STOP : 0."

# --- Google Places : fiches -> candidats (site vitrine ignoré), plafond du jour, erreur sans clé affichée, source sautée sans clé ---
cp_ = X.candidats_places({"places": [{"id": "A1", "displayName": {"text": "SALON TEST"}, "formattedAddress": "1 rue X, 76000 Rouen, France", "nationalPhoneNumber": "02 35 00 00 00", "websiteUri": "https://www.planity.com/salon-test"},
                                     {"id": "A2", "displayName": {"text": "Sans adresse"}, "formattedAddress": "Rouen"}, {"id": "A3", "displayName": {"text": "Vrai Site"}, "formattedAddress": "2 rue Y, 76100 Rouen, France", "websiteUri": "https://vrai-site.fr/"}]}, "coiffeur")
assert [c["id"] for c in cp_] == ["places/A1", "places/A3"] and cp_[0]["site"] == "" and cp_[1]["site"] == "https://vrai-site.fr/" and cp_[0]["cp"] == "76000" and cp_[0]["telephone"] == "", cp_   # le téléphone de Google n'est jamais repris
# cmd_places : rien de Google (nom, adresse, téléphone) dans l'état ; l'état ne garde que place_id, domaine et jugement
X.ETAT, X.TROUVES = tmp / "etat-places.json", tmp / "trouves-places.csv"; X.ecrire_trouves([])
class _R(__import__("io").BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): return False
ouv_pl = lambda rq, timeout=0: _R(__import__("json").dumps({"places": [{"id": "P9", "displayName": {"text": "Salon Secret"}, "formattedAddress": "3 rue Z, 76000 Rouen, France", "websiteUri": "https://salon-secret.fr/"}]}).encode())
X.cle_places = lambda: "CLE"
X.cmd_places(False, {**X.DEFAUT, "pause_site_s": 0}, ouvrir=ouv_pl, lire=lambda u, **k: None, dormir=lambda s: None)
brut = X.ETAT.read_text(encoding="utf-8"); e_ = __import__("json").loads(brut)
assert "Salon Secret" not in brut and "3 rue Z" not in brut and "tampon" not in e_["places"] and "places:places/P9" in e_["vus"] and e_["places"]["jugements"]["P9"]["domaine"] == "salon-secret.fr", brut[:400]
assert X.DEFAUT["places_max_jour"] == 30 and X.DEFAUT["decouverte_places"] is False
class _Err(Exception): pass
def refus(rq, timeout=0): raise X.urllib.error.HTTPError(rq.full_url, 403, "x", {}, __import__("io").BytesIO(b'{"error":{"message":"billing disabled CLEFSECRETE"}}'))
try: X.appel_places("coiffeur Rouen", "CLEFSECRETE", refus); assert False
except OSError as e_: assert "403" in str(e_) and "billing disabled" in str(e_) and "CLEFSECRETE" not in str(e_), e_

# --- filtre annuaire (ETI/GE, 50 salariés et plus, associations, administrations, établissements publics ; donnée manquante = rien d'écarté) ---
assert X.motif_annuaire({"categorie": "ETI"}) and X.motif_annuaire({"categorie": "GE"}) and X.motif_annuaire({"tranche": "21"}) and X.motif_annuaire({"tranche": "32"})
assert all(X.motif_annuaire({"nature": n}) for n in ("9220", "7385", "7210", "7120", "4110", "8110", "9110", "9300"))
assert not X.motif_annuaire({}) and not X.motif_annuaire({"categorie": "PME", "tranche": "12", "nature": "5710"}) and not X.motif_annuaire({"categorie": "", "tranche": "NN", "nature": "1000"})
import os as _os2
_env = _os2.environ.pop("JARVIS_TEST", None)
try:
    class _Rep(__import__("io").BytesIO):
        def __enter__(self): return self
        def __exit__(self, *a): return False
    rep = {"results": [{"siren": "1", "nom_complet": "Bon Elec SARL", "siege": {"libelle_commune": "ROUEN"}, "categorie_entreprise": "ETI", "tranche_effectif_salarie": "41", "nature_juridique": "7385"}]}
    f_ = X.appel_fiche({"nom": "Bon Elec", "ville": "Rouen", "siren": ""}, lambda rq, timeout=0: _Rep(__import__("json").dumps(rep).encode()))
    assert f_ == {"categorie": "ETI", "tranche": "41", "nature": "7385"}, f_
    assert X.appel_fiche({"nom": "Autre", "ville": "Rouen", "siren": ""}, lambda rq, timeout=0: _Rep(__import__("json").dumps(rep).encode())) == {}     # nom différent : introuvable, rien d'écarté
    assert X.appel_fiche({"nom": "Bon Elec", "ville": "Caen", "siren": ""}, lambda rq, timeout=0: _Rep(__import__("json").dumps(rep).encode())) == {}      # autre commune
    def panne(rq, timeout=0): raise OSError("réseau")
    assert X.appel_fiche({"nom": "Bon Elec", "ville": "Rouen", "siren": ""}, panne) == {}                                                                 # erreur : rien d'écarté
finally:
    if _env is not None: _os2.environ["JARVIS_TEST"] = _env
X.ETAT, X.MESSAGES, X.TROUVES = tmp / "etat-ann.json", tmp / "messages-ann.md", tmp / "trouves-ann.csv"
rows = []
for i, nom in enumerate(["Bon Elec", "Grosse Elec", "Asso Elec", "Elec Inconnu", "Elec Cinquante"]):
    r = {k: "" for k in X.COLS}
    r.update(nom=nom, metier="électricien", ville="Rouen", siren=str(200000000 + i), cp="76000", statut="trouvé", email=f"contact@{X.G.slug(nom)}.fr", email_type="generique", email_source="https://x.fr",
             note_besoin="site non adapté au mobile (constaté le 27/10)", source="l'annuaire officiel des entreprises", date_collecte=str(date.today()))
    rows.append(r); (X.G.PUBLIC / f"{X.G.slug(nom)}-{X.G.jeton(nom, 'Rouen')}").mkdir(parents=True); (X.G.PUBLIC / f"{X.G.slug(nom)}-{X.G.jeton(nom, 'Rouen')}" / "index.html").write_text("x")
X.ecrire_trouves(rows)
fiches_ = {"Bon Elec": {"categorie": "PME", "tranche": "12", "nature": "5710"}, "Grosse Elec": {"categorie": "ETI"}, "Asso Elec": {"nature": "9220"}, "Elec Cinquante": {"tranche": "21"}}
_preparer_reel(False, {**conf, "par_boite_par_jour": 5}, generer=False, api_fiche=lambda l: fiches_.get(l["nom"], {}))
st_ann = {l["nom"]: l["statut"] for l in X.lire_trouves()}
assert st_ann == {"Bon Elec": "préparé", "Grosse Elec": "exclu", "Asso Elec": "exclu", "Elec Inconnu": "préparé", "Elec Cinquante": "exclu"}, st_ann
assert "Grosse Elec" not in X.MESSAGES.read_text(encoding="utf-8") and "Asso Elec" not in X.MESSAGES.read_text(encoding="utf-8")
assert X.etat_lire()["fiches_annuaire"]["grosse-elec|rouen"]["categorie"] == "ETI"       # fiche publique en cache, aucune requête au prochain passage
# --- re-vérification de dernière minute : constats non reconfirmés retirés, entreprise écartée si plus aucun, « pas de site trouvé » épargné ---
X.MESSAGES, X.TROUVES = tmp / "messages-rev.md", tmp / "trouves-rev.csv"
def bloc_(nom, constat, typ="email", box=BOITES[0]):
    m = {"type": typ, "formulaire": "", "box": box, "email": f"c@{X.G.slug(nom)}.fr", "nom": nom, "ville": "Rouen", "metier": "électricien", "lot": str(date.today()), "lien": "", "facebook": "", "linkedin": "", "constat": constat}
    return f"## {nom} — électricien — Rouen\n<!-- id:{X.G.slug(nom)}|rouen -->\n<!-- meta:{X.meta_texte(m)} -->\n**Statut : à valider**\n\n```\nEn regardant votre activité : {constat} (constaté le 27/10).\n```\n\n"
X.MESSAGES.write_text(bloc_("Rev Un", "aucune balise title sur la page d'accueil ; page construite en Flash") + bloc_("Rev Deux", "page construite en Flash") + bloc_("Rev Trois", "aucun site trouvé à son nom") + bloc_("Rev Quatre", "aucune balise title sur la page d'accueil"), encoding="utf-8")
lg = []
for nom, site in (("Rev Un", "https://revun.fr"), ("Rev Deux", "https://revdeux.fr"), ("Rev Trois", ""), ("Rev Quatre", "https://revquatre.fr")):
    r = {k: "" for k in X.COLS}; r.update(nom=nom, ville="Rouen", site_actuel=site, statut="préparé"); lg.append(r)
appels_lire = []
def lire_rev(u, **k):
    appels_lire.append((u, k.get("timeout"), k.get("robots_timeout")))
    return None if "revquatre" in u else (u, {}, "<html><body><p>bonjour</p></body></html>")
gardes_, ecartes_ = X.reverifier_lot(X.lire_blocs(X.MESSAGES.read_text(encoding="utf-8")), lg, X.DEFAUT, lire_rev)
assert [b["meta"]["nom"] for b in gardes_] == ["Rev Un", "Rev Trois"] and {b["meta"]["nom"] for b, _ in ecartes_} == {"Rev Deux", "Rev Quatre"}, (gardes_, ecartes_)
assert len(appels_lire) == 3 and all(a[1] == 1 and a[2] == 1 for a in appels_lire)        # UN accès par entreprise avec site, 1 s de délai ; aucun accès pour « pas de site trouvé »
assert gardes_[0]["meta"]["constat"] == "aucune balise title sur la page d'accueil"       # le constat non reconfirmé est retiré du message Discord
txt_rev = X.MESSAGES.read_text(encoding="utf-8"); assert "Flash" in txt_rev.split("## Rev Deux")[1] and "Flash" not in txt_rev.split("## Rev Un")[1].split("## Rev Deux")[0] and "(constaté le " + date.today().strftime("%d/%m") in txt_rev   # et du texte de l'e-mail, daté d'aujourd'hui
# publication : le lot posté ne contient que les entreprises reconfirmées ; les autres sont écartées (statut) et le lot est signalé incomplet
X.ETAT = tmp / "etat-rev.json"; X.ecrire_trouves(lg); X.MESSAGES.write_text(bloc_("Rev Un", "aucune balise title sur la page d'accueil") + bloc_("Rev Deux", "page construite en Flash"), encoding="utf-8")
posts.clear()
assert _publier_reel(False, {**conf, "par_boite_par_jour": 2}, api, SOIR, lire_verif=lire_rev) == 1 and len(posts) == 1, posts
assert "Rev Un" in posts[0][-1] if isinstance(posts[0], tuple) else True
txt_rev = X.MESSAGES.read_text(encoding="utf-8"); assert "écarté à la re-vérification" in txt_rev.split("## Rev Deux")[1]

for _n, _f in _ORIG.items(): setattr(X, _n, _f)
# --- salons par nom : lots / réponses / appels-du-jour ---
cfg_t = tmp / "cfg-salons.json"; cfg_t.write_text(X.json.dumps({"salon_paiement_id": "OLD", "autre": 1}), encoding="utf-8")
guildes = {"/users/@me/guilds": [{"id": "g1"}], "/guilds/g1/channels": [{"id": "c1", "type": 4, "name": "B2B vente site web"}, {"id": "c2", "type": 0, "name": "📦│Lots", "parent_id": "c1"}, {"id": "c3", "type": 0, "name": "lots", "parent_id": "autre"}, {"id": "c4", "type": 0, "name": "réponses", "parent_id": "c1"}, {"id": "c5", "type": 2, "name": "appels-du-jour"}]}
vus = []; lire_f = lambda ch: (vus.append(ch), guildes.get(ch))[1]
assert X.P.salon_par_nom("jeton", "salon_lots_id", "lots", "OLD", lire_f, cfg_t) == "c2"                         # catégorie « B2B vente site web » préférée
assert X.P.salon_par_nom("jeton", "salon_reponses_id", "Réponses", "OLD", lire_f, cfg_t) == "c4"                 # casse et accents ignorés
k = X.P.M.lire_fusionnee(cfg_t); assert X.json.loads(cfg_t.read_text(encoding="utf-8")) == {"salon_paiement_id": "OLD", "autre": 1}, "le fichier versionné ne bouge pas (le cache est dans le .local.json)"; assert k == {"salon_paiement_id": "OLD", "autre": 1, "salon_lots_id": "c2", "salon_reponses_id": "c4"}, k
n_ = len(vus); assert X.P.salon_par_nom("jeton", "salon_lots_id", "lots", "OLD", lire_f, cfg_t) == "c2" and len(vus) == n_   # cache : aucune nouvelle requête
assert X.P.salon_par_nom("jeton", "salon_appels_id", "appels-du-jour", "OLD", lire_f, cfg_t) == "OLD" and "salon_appels_id" not in X.P.M.lire_fusionnee(cfg_t)   # vocal ou introuvable : ancien salon
assert X.P.salon_par_nom("jeton", "x", "lots", "OLD", lambda ch: None, tmp / "absent.json") == "OLD"             # API en échec : ancien salon
# lot posté dans le salon « lots », lot ancien resté dans l'ancien salon : chacun lu dans SON salon
X.acces_discord = lambda cle=None, nom=None, api=None: ("jeton", "lots1" if cle else "ancien1", UID)
X.ETAT = tmp / "etat-salons.json"; X.etat_ecrire({"lots_discord": {"500": {"ids": ["a"], "date": X.aujourdhui(), "box": "b"}, "600": {"ids": ["b"], "date": X.aujourdhui(), "box": "b", "salon": "lots1"}}}, False)
lus = []
def api_s(jeton, m, chemin, corps=None): lus.append(chemin); return []
X.cmd_approuver(False, {**conf, "envoi_automatique": False}, api_s)
assert any(c.startswith("/channels/ancien1/messages?after=500") for c in lus) and any(c.startswith("/channels/lots1/messages?after=600") for c in lus), lus
posts_a = []; X.acces_discord = lambda cle=None, nom=None, api=None: ("jeton", "appels1", UID)
api_p = lambda j, m, ch, c=None: (posts_a.append((ch, c["content"], c.get("embeds", []))), {"id": "1"})[1]
assert X.poster_liste(fichier, "2026-10-28", api_p) and len(posts_a) == 2 and all(p_[0] == "/channels/appels1/messages" for p_ in posts_a)
assert "Créneaux conseillés" in posts_a[0][1] and "Bloc 1 sur 1" in posts_a[1][1] and "📞" in posts_a[1][2][0]["description"], posts_a
msgs = X.messages_liste([{"n": i, "nom": "Dupont <@1> *x*", "ville": "Rouen", "tel": "0102030405", "metier": "plombier", "lien": "https://b2b-demos.vercel.app/p/", "constat": "constat " * 30} for i in range(1, 101)], "2026-11-02")
assert len(msgs) >= 5 and all(len(t_) <= 2000 and sum(len(e_) for e_ in em) <= 6000 and all(len(e_) <= 4096 for e_ in em) for t_, em in msgs), [(len(t_), [len(e_) for e_ in em]) for t_, em in msgs]
assert not any("<@" in t_ or any("<@" in e_ for e_ in em) for t_, em in msgs) and sum("Bloc 4 sur 4" in t_ for t_, em in msgs) >= 1
# 8 h : rien avant l'heure, une seule fois par jour ensuite
posts_h = []; api_h = lambda j, m, ch, c=None: (posts_h.append(ch), {"id": "1"})[1]
from datetime import datetime as _dt
e_ = X.etat_lire(); e_.setdefault("appels", {})["postee"] = ""; X.etat_ecrire(e_, False); (X.DOCS / f"liste-appels-{X.aujourdhui()}.md").write_text(md, encoding="utf-8")
conf8 = {**conf3, "liste_appels_heure": "08:00"}
assert X.cmd_liste_matin(conf8, api_h, paris=_dt(2026, 11, 2, 7, 59)) == 0 and not posts_h
assert X.cmd_liste_matin(conf8, api_h, paris=_dt(2026, 11, 2, 8, 0)) == 1 and posts_h and X.etat_lire()["appels"]["postee"] == X.aujourdhui()
n_h = len(posts_h); assert X.cmd_liste_matin(conf8, api_h, paris=_dt(2026, 11, 2, 9, 0)) == 0 and len(posts_h) == n_h


# --- MX : le domaine doit pouvoir recevoir du courrier avant tout envoi ---
def rep_dns(rcode, mx):   # réponse DNS minimale : question « a.fr MX » + un enregistrement MX par (préférence, nom)
    ent = bytes([0x12, 0x34, 0x81, 0x80 | rcode, 0, 1, 0, len(mx), 0, 0, 0, 0]) + b"\x01a\x02fr\x00\x00\x0f\x00\x01"
    for pref, nom in mx:
        rd = pref.to_bytes(2, "big") + (b"\x00" if not nom else bytes([len(nom)]) + nom.encode() + b"\x02fr\x00")
        ent += b"\xc0\x0c\x00\x0f\x00\x01\x00\x00\x01\x2c" + len(rd).to_bytes(2, "big") + rd
    return ent
assert X.analyser_mx(rep_dns(0, [(10, "mx1"), (20, "mx2")])) == (0, [(10, "x"), (20, "x")]) and X.analyser_mx(rep_dns(3, [])) == (3, []) and X.analyser_mx(rep_dns(0, [(0, "")])) == (0, [(0, "")])
assert X.domaine_recoit_courrier("a.fr", lambda d: (0, [(10, "x")])) is True
assert X.domaine_recoit_courrier("a.fr", lambda d: (3, [])) is False                      # NXDOMAIN
assert X.domaine_recoit_courrier("a.fr", lambda d: (0, [(0, "")])) is False               # MX nul : « ce domaine ne reçoit rien »
assert X.domaine_recoit_courrier("nom-sans-adresse.invalid", lambda d: (0, [])) is False  # ni MX ni adresse A/AAAA
def panne(d): raise OSError("DNS injoignable")
assert X.domaine_recoit_courrier("a.fr", panne) is True and X.domaine_recoit_courrier("a.fr", lambda d: (2, [])) is True   # doute : jamais d'exclusion
_boites = X.boites; X.boites = lambda: ["b"]
X.RESOLVEUR_MX = lambda d: (3, []) if d == "mort.fr" else (0, [(10, "x")])
bm = lambda adr: {"id": "m1", "ok": True, "corps": "", "objet": "", "meta": {"type": "email", "email": adr, "box": "b", "nom": "N", "ville": "V"}}
e_mx = {"approuves": ["m1"], "lots_discord": {}, "envois": {}, "relances": [], "envoyes": {}}
assert X.refus(bm("contact@mort.fr"), e_mx, conf, set(), set(), lambda u: True) == X.MOTIF_MX            # refusé avant tout envoi
assert X.refus(bm("contact@vivant.fr"), e_mx, conf, set(), set(), lambda u: True) != X.MOTIF_MX
assert X.refus(bm("contact@mort.fr"), e_mx, {**conf, "verifier_mx": False}, set(), set(), lambda u: True) != X.MOTIF_MX   # réglage verifier_mx = false
X.RESOLVEUR_MX = None; X.boites = _boites
_fich = X.S.FICHIER; X.S.FICHIER = tmp / "suivi-mx.csv"
with open(X.S.FICHIER, "w", encoding="utf-8-sig", newline="") as f_:
    w_ = X.csv.DictWriter(f_, fieldnames=X.S.COLS, delimiter=";"); w_.writeheader(); w_.writerow({"nom": "Mort SARL", "ville": "Rouen", "email": "contact@mort.fr", "statut": "à contacter"})
X.exclure_domaine_mort({"nom": "Mort SARL", "ville": "Rouen", "email": "contact@mort.fr"})
r_mx = X.S.lire()[0]; assert r_mx["statut"] == "exclu" and "aucun enregistrement MX" in r_mx["note"] and "à contacter -> exclu" in r_mx["historique"]
X.S.FICHIER = _fich

print("OK : tous les tests passent (dossier temporaire :", tmp, ")")
import shutil; shutil.rmtree(tmp, ignore_errors=True)
