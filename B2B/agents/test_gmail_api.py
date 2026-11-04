#!/usr/bin/env python3
"""Tests silencieux du mode API Gmail, plusieurs comptes (aucun réseau, aucune bibliothèque Google, aucun vrai jeton, .env jamais lu, rien n'est envoyé) : python agents\\test_gmail_api.py"""
import base64, contextlib, io, json, sys, tempfile
from email.message import EmailMessage
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gmail_api as GA, reponses as R, prospection as X

tmp = Path(tempfile.mkdtemp(prefix="gmail-api-test-"))
LIAM, LM = "liamdigital2109@gmail.com", "contact.lmsites@gmail.com"


def sortie(f, *a, **k):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf): r = f(*a, **k)
    return r, buf.getvalue()


# --- gmail_api : un jeton par compte, erreurs traduites, client sur un faux service ---
GA.DOSSIER = tmp
assert GA.chemin_jeton("Liam@Gmail.com").name == "gmail-token-liam@gmail.com.json" and GA.comptes_autorises() == []
try: GA.credentials(LM); raise SystemExit("JetonExpire attendu")
except GA.JetonExpire as e: assert "test-gmail-api.py " + LM in str(e) and LM in str(e)                      # le message dit quel compte relancer
(tmp / f"gmail-token-{LIAM}.json").write_text("{}", encoding="utf-8"); assert GA.comptes_autorises() == [LIAM] and GA.jeton_existe(LIAM) and not GA.jeton_existe(LM)


class RefreshError(Exception): pass
class HttpError(Exception):
    def __init__(self, code): self.resp = type("R", (), {"status": code})()
assert isinstance(GA._traduire(RefreshError(), LM), GA.JetonExpire) and LM in str(GA._traduire(RefreshError(), LM)) and isinstance(GA._traduire(HttpError(401)), GA.JetonExpire)
assert GA._traduire(HttpError(403)).code == 403 and GA._traduire(TimeoutError()).code == 0 and "réseau" in str(GA._traduire(TimeoutError()))
assert str(GA._traduire(ValueError("secret"))) == "ValueError"   # le texte de l'erreur n'est jamais repris


class Rq:
    def __init__(s, v): s.v = v
    def execute(s):
        if isinstance(s.v, Exception): raise s.v
        return s.v


class Svc:
    def __init__(s): s.envoyes = []
    def users(s): return s
    def messages(s): return s
    def getProfile(s, userId): return Rq({"emailAddress": LIAM})
    def list(s, userId, q, maxResults, pageToken=None):
        return Rq({"messages": [{"id": "a"}, {"id": "b"}], "nextPageToken": "p2"} if pageToken is None else {"messages": [{"id": "c"}]})
    def get(s, userId, id, format, metadataHeaders=None):
        if format == "raw": return Rq({"raw": base64.urlsafe_b64encode("Subject: é\r\n\r\nSalut".encode()).decode().rstrip("=")})
        return Rq({"payload": {"headers": [{"name": "From", "value": "A <a@b.fr>"}, {"name": "Message-ID", "value": "<m1>"}]}})
    def send(s, userId, body): s.envoyes.append(body); return Rq({"id": "G1"})


svc = Svc(); cl = GA.Client(svc, LIAM)
assert cl.profil() == LIAM and cl.ids("in:inbox") == ["a", "b", "c"] and cl.ids("x", maxi=2) == ["a", "b"]
assert cl.entetes("a") == {"from": "A <a@b.fr>", "message-id": "<m1>"} and cl.brut("a").endswith(b"Salut")
m = EmailMessage(); m["From"] = f"Liam Emo <{LIAM}>"; m["To"] = "a@b.fr"; m["Subject"] = "Objet"; m.set_content("Corps é")
assert cl.envoyer(m) == "G1"
envoye = svc.envoyes[0]["raw"]; assert b"Subject: Objet" in base64.urlsafe_b64decode(envoye + "=" * (-len(envoye) % 4))
cl_ko = GA.Client(type("S", (), {"users": lambda s: s, "getProfile": lambda s, userId: Rq(HttpError(403))})(), LM)
try: cl_ko.profil(); raise SystemExit("ErreurApi attendue")
except GA.ErreurApi as e: assert e.code == 403 and str(e) == "HTTP 403"

cfg_tmp = tmp / "reponses-config.json"; cfg_tmp.write_text(json.dumps({"salon_paiement_id": "1", "comptes": [{"adresse": "x@gmail.com", "var": "V"}], "api": {"actif": True, "adresse": LIAM}}), encoding="utf-8")
avant_cfg = cfg_tmp.read_text(encoding="utf-8"); GA.enregistrer_adresse(LM.upper(), cfg_tmp); GA.enregistrer_adresse(LM, cfg_tmp); c = GA.M.lire_fusionnee(cfg_tmp)      # le compte ajouté est écrit dans reponses-config.local.json
assert c["api"]["comptes"] == [LIAM, LM] and c["api"]["actif"] is True and c["salon_paiement_id"] == "1" and c["comptes"][0]["var"] == "V" and cfg_tmp.read_text(encoding="utf-8") == avant_cfg      # ancien réglage repris, pas de doublon

# --- test-gmail-api.py : un compte en argument, ou tous les comptes déjà autorisés ---
import importlib.util
spec = importlib.util.spec_from_file_location("tga", Path(__file__).with_name("test-gmail-api.py")); T = importlib.util.module_from_spec(spec); spec.loader.exec_module(T)
T.GA.bibliotheques = lambda: None
T.GA.client = lambda a: GA.Client(None, a)                   # « autorisé » : renvoie le compte demandé
T.GA.enregistrer_adresse = lambda a: None
r, txt = sortie(T.main, []); assert r == 0 and txt.strip() == f"OK, adresse = {LIAM}"                  # sans argument : seulement les comptes déjà autorisés (LM n'a pas de jeton)
r, txt = sortie(T.main, [LM]); assert r == 0 and txt.strip() == f"OK, adresse = {LM}"                  # avec argument : ce compte seul
def refuse(a): raise GA.JetonExpire(a)
T.GA.client = refuse; r, txt = sortie(T.main, []); assert r == 1 and "ERREUR" in txt                  # sans argument : aucune autorisation lancée (autoriser n'existe pas dans ce test)
T.GA.autoriser = lambda a: (_ for _ in ()).throw(RuntimeError("navigateur")); r, txt = sortie(T.main, [LM]); assert r == 1 and "RuntimeError" in txt   # argument : l'autorisation est tentée, erreur sobre

# --- reponses : réglages et lecture sur plusieurs comptes ---
R.CONFIG = tmp / "absent-config.json"; assert R.cfg()["api"] == {"actif": False, "comptes": []}
R.CONFIG = cfg_tmp; assert R.cfg()["api"] == {"actif": True, "comptes": [LIAM, LM]}
GA.M.chemin_local(cfg_tmp).unlink(missing_ok=True); cfg_tmp.write_text(json.dumps({"api": {"adresse": "Z@gmail.com"}}), encoding="utf-8"); assert R.cfg()["api"] == {"actif": False, "comptes": ["z@gmail.com"]}


def brut(de, objet, corps, reply=None):
    e = EmailMessage(); e["From"] = de; e["To"] = LIAM; e["Subject"] = objet; e.set_content(corps)
    if reply: e["Reply-To"] = reply
    return e.as_bytes()


class Faux:
    def __init__(s, adresse=LIAM, mails=None): s.adresse, s.lus, s.req, s.mails = adresse, [], [], mails if mails is not None else Faux.MAILS
    def ids(s, requete, maxi=500): s.req.append(requete); return list(s.mails)
    def entetes(s, gid): return s.mails[gid][0]
    def brut(s, gid): s.lus.append(gid); return s.mails[gid][1]


Faux.MAILS = {
    "1": ({"from": "Elec Un <contact@elecun.fr>", "subject": "Re: bonjour", "message-id": "<1@x>"}, brut("contact@elecun.fr", "Re: bonjour", "Oui, ça m'intéresse, envoyez un devis.\n\nLe lun. 26 oct. 2026 à 10:00, Liam a écrit :\n> STOP", "autre@elecun.fr")),
    "2": ({"from": "Inconnu <inconnu@x.fr>", "subject": "Promo", "message-id": "<2@x>"}, brut("inconnu@x.fr", "Promo", "STOP")),
    "3": ({"from": "Moi <liamdigital2109@gmail.com>", "subject": "Re: x", "message-id": "<3@x>"}, brut(LIAM, "Re: x", "oui")),
    "4": ({"from": "Quelqu'un <q@y.fr>", "subject": "Re: Elec Deux : une maquette de site pour votre activité", "message-id": "<4@x>"}, brut("q@y.fr", "Re: Elec Deux : une maquette de site pour votre activité", "Non merci, pas intéressé.")),
    "5": ({"from": "Elec Un <contact@elecun.fr>", "subject": "Re: bonjour", "message-id": "<déjà@x>"}, brut("contact@elecun.fr", "Re: bonjour", "oui"))}
p1, p2 = {"nom": "Elec Un", "ville": "Rouen", "statut": "envoyé"}, {"nom": "Elec Deux", "ville": "Rouen", "statut": "envoyé"}
par_mail = {"contact@elecun.fr": p1}; par_nom = {R.S.G.slug("Elec Deux"): p2}
faux = Faux()
rep = R.lire_boite_api(faux, 14, {"<déjà@x>"}, par_mail, par_nom, {LIAM})
assert [r["mid"] for r in rep] == ["<1@x>", "<4@x>"] and faux.lus == ["1", "4"], (rep, faux.lus)   # inconnu, nous-mêmes et déjà traité : corps jamais lu
assert faux.req[0].startswith("in:inbox after:") and rep[0]["compte"] == LIAM
assert rep[0]["texte"] == "Oui, ça m'intéresse, envoyez un devis." and rep[0]["repondre"] == "autre@elecun.fr" and rep[1]["repondre"] == "q@y.fr"
assert [R.classer(r["objet"], r["texte"]) for r in rep] == ["positive", "négative"]

cfg_api = {"api": {"actif": True, "comptes": [LIAM, LM]}}; deja = {"<déjà@x>"}
boites_ouvertes = []
def ouvrir_deux(a): boites_ouvertes.append(a); return Faux(a, {"1": Faux.MAILS["1"]} if a == LM else {"4": Faux.MAILS["4"]})
ok, _ = sortie(R.lire_api, cfg_api, 14, deja, par_mail, par_nom, set(), ouvrir_deux)
assert boites_ouvertes == [LIAM, LM] and [(r["compte"], r["mid"]) for r in ok] == [(LIAM, "<4@x>"), (LM, "<1@x>")]       # les deux boîtes sont lues, la boîte réceptrice est notée


def lm_expire(a):
    if a == LM: raise GA.JetonExpire(a)
    return Faux(a, {"4": Faux.MAILS["4"]})
r, txt = sortie(R.lire_api, cfg_api, 14, deja, par_mail, par_nom, set(), lm_expire)
assert [x["compte"] for x in r] == [LIAM] and f"{LM} : Jeton Gmail de {LM}" in txt and f"test-gmail-api.py {LM}" in txt       # LM sautée, LIAM lue, aucune exception
def toutes_ko(a):
    if a == LIAM: raise GA.ErreurApi(0, "réseau")
    raise GA.BibliothequeManquante("Bibliothèques Google absentes")
r, txt = sortie(R.lire_api, cfg_api, 14, deja, par_mail, par_nom, set(), toutes_ko); assert r == [] and "réseau" in txt and "Bibliothèques" in txt
ex = R.message_discord("42", p1, "Oui", "autre@elecun.fr", [], True, boite=LM)
assert f"reçue sur la boîte {LM}" in ex and "Adresse de réponse : autre@elecun.fr" in ex and "<@42>" in ex                    # Discord : la boîte est indiquée
assert "reçue sur la boîte" not in R.message_discord("42", p1, "Oui", "a@b.fr", [], True)

# --- prospection : comptes autorisés, un prospect = une boîte, envoi par boîte, jeton refusé sans bloquer l'autre ---
R.CONFIG = cfg_tmp
def ecrire_cfg(api): cfg_tmp.write_text(json.dumps({"comptes": [{"adresse": "a@gmail.com", "var": "A"}, {"adresse": "b@gmail.com", "var": "B"}], "api": api}), encoding="utf-8")
ecrire_cfg({"actif": True, "comptes": [LIAM, LM]}); assert X.boites() == [LIAM]                  # LM n'a pas encore de jeton : pas de lot préparé pour elle
(tmp / f"gmail-token-{LM}.json").write_text("{}", encoding="utf-8"); assert X.boites() == [LIAM, LM]
ecrire_cfg({"actif": True, "comptes": []}); assert X.boites() == []
ecrire_cfg({"actif": False}); assert X.boites() == ["a@gmail.com", "b@gmail.com"]                # repli IMAP/SMTP quand « api » est désactivé
ecrire_cfg({"actif": True, "comptes": [LIAM, LM]})


class Envoi:
    def __init__(s, adresse): s.adresse, s.vus = adresse, []
    def envoyer(s, msg): s.vus.append(msg); return "G9"
    def entetes(s, gid): return {"message-id": "<reel@mail.gmail.com>"}


X._client.clear(); e1, e2 = Envoi(LIAM), Envoi(LM); ouv = {LIAM: e1, LM: e2}
msg = EmailMessage(); msg["From"] = f"Liam Emo <{LM}>"; msg["Message-ID"] = "<local@gmail.com>"; msg.set_content("x")
X.envoi_api(LM, None, msg, lambda b: ouv[b]); assert e2.vus == [msg] and not e1.vus and msg["Message-ID"] == "<reel@mail.gmail.com>"   # envoi par la bonne boîte, Message-ID réel relu
X._client.clear()
try: X.envoi_api(LIAM, None, msg, lambda b: e2); raise SystemExit("refus attendu")
except GA.ErreurApi as ex: assert ex.code == 403                                                  # le jeton ouvert doit être celui de la boîte demandée

refus0 = X.refus; X._client.clear()
def bloc(i, box, mail="a@b.fr", typ="email"):
    return {"id": i, "statut": "validé", "ok": True, "objet": "o", "corps": "Bonjour\n" + X.R.LIGNE_STOP, "texte": "",
            "meta": {"type": typ, "box": box, "email": mail, "nom": "N" + i, "ville": "Rouen", "lot": "2026-10-27", "lien": "https://x", "origine": "o1"}}
et = {"approuves": ["b1", "b2", "r1"], "envois": {"o1": {"email": "a@b.fr", "box": LM}}, "envoyes": {}, "relances": [], "lots_discord": {}}
conf = {**X.DEFAUT, "pause_envoi_s": [0, 0]}
assert "déjà contacté" in refus0(bloc("b1", LIAM), et, conf, set(), set(), lambda u: True)            # même prospect depuis l'autre boîte : refusé
assert refus0(bloc("b2", LIAM, "autre@b.fr"), et, conf, set(), set(), lambda u: True) == ""          # autre prospect : accepté
assert "autre boîte" in refus0(bloc("r1", LIAM, typ="relance"), et, conf, set(), set(), lambda u: True)   # la relance part de la boîte du premier message
assert refus0(bloc("r1", LM, typ="relance"), et, conf, set(), set(), lambda u: True) == ""

X.ETAT, X.MESSAGES = tmp / "etat.json", tmp / "messages.md"; X.MESSAGES.write_text("# x\n", encoding="utf-8")
X.P.lire_env = lambda _: (_ for _ in ()).throw(AssertionError("B2B\\.env lu"))   # en mode API aucun mot de passe d'application n'est utilisé
X.R.charger_identite = lambda: ({"prenom_nom": "Liam Emo"}, [])
X.exclusions = lambda: (set(), set()); X.S.statut = lambda *a, **k: None; X.marquer = lambda t, i, n: t; X.refus = lambda *a, **k: ""
X.lire_blocs = lambda t: [bloc("1", LIAM), bloc("2", LM, "c@d.fr"), bloc("3", LIAM, "e@f.fr")]
appels = []


def scenario(erreurs):
    """erreurs : {boîte: exception}. Renvoie (nombre envoyé, boîtes appelées, texte)."""
    appels.clear(); X._client.clear()
    if X.ETAT.exists(): X.ETAT.unlink()
    def envoi(box, mdp, msg):
        assert mdp is None and msg["From"] == f"Liam Emo <{box}>"; appels.append(box)
        if box in erreurs: raise erreurs[box]
    n, txt = sortie(X.cmd_envoyer, False, conf, envoi, lambda s: None, lambda u: True)
    return n, list(appels), txt


n, a, txt = scenario({}); assert n == 3 and a == [LIAM, LM, LIAM]
n, a, txt = scenario({LIAM: GA.JetonExpire(LIAM)})                                                       # jeton de LIAM refusé : LIAM sautée (une seule tentative), LM envoie
assert n == 1 and a == [LIAM, LM] and f"test-gmail-api.py {LIAM}" in txt and X._client["hors"] == {LIAM}
n, a, txt = scenario({LM: GA.ErreurApi(403)}); assert n == 2 and a == [LIAM, LM, LIAM] and X._client["hors"] == {LM}   # refus général de LM : LM sautée, LIAM continue
n, a, txt = scenario({LM: GA.ErreurApi(400)}); assert n == 2 and not X._client["hors"] and "HTTP 400" in txt          # refus propre à un message : on passe au suivant
n, a, txt = scenario({LIAM: GA.BibliothequeManquante("Bibliothèques Google absentes"), LM: GA.JetonExpire(LM)}); assert n == 0 and a == [LIAM]   # bibliothèques absentes : rien ne peut partir
print("OK : tous les tests passent (aucun réseau, aucun envoi)")
import shutil; shutil.rmtree(tmp, ignore_errors=True)
