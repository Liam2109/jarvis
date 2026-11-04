#!/usr/bin/env python3
"""Tests silencieux du filtre d'adresses (filtre_adresses.py) et de son branchement : aucun réseau, aucun envoi, fichiers temporaires.  python agents\\test_filtre_adresses.py"""
import os, sys, tempfile, json, csv
os.environ.setdefault("JARVIS_TEST", "1")
from datetime import date, timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import filtre_adresses as FA

# --- syntaxe, faute de frappe, exclusions, source, MX (fonctions pures) ---
L = lambda mail, src="https://x.fr/contact": {"email": mail, "email_source": src}
mort = lambda d: d != "mort.fr"
assert FA.controle_adresse(L("contact@elec-dupont.fr"), set(), mort) == ("", [])
for mauvaise in ("contact@", "@x.fr", "a b@x.fr", "a@x", "a..b@x.fr", "a@-x.fr", "a@x..fr", "a@x.f", ".a@x.fr"):
    assert FA.controle_adresse(L(mauvaise), set(), mort)[0] == FA.MOTIF_SYNTAXE, mauvaise
assert FA.controle_adresse(L("jean@gmial.com"), set(), mort)[0] == "domaine proche de gmail.com (faute de frappe probable)"
assert FA.controle_adresse(L("jean@gmai.com"), set(), mort)[0].startswith("domaine proche de gmail.com")
assert FA.controle_adresse(L("jean@orange.fr"), set(), mort)[0] == "" and FA.controle_adresse(L("jean@gmail.com"), set(), mort)[0] == ""   # les vrais domaines passent
assert FA.faute_de_frappe("alive.fr") == "" and FA.faute_de_frappe("elec-dupont.fr") == ""                                                     # un domaine d'entreprise n'est jamais « corrigé »
assert FA.distance_un("gmail.com", "gmial.com") and FA.distance_un("gmail.com", "gmaill.com") and not FA.distance_un("gmail.com", "gmail.com") and not FA.distance_un("gmail.com", "gmxil.fr")
assert FA.controle_adresse(L("Contact@Elec-Dupont.FR "), {"contact@elec-dupont.fr"}, mort)[0] == FA.MOTIF_EXCLU      # exclus-emails.json : casse et espaces sans effet
assert FA.controle_adresse(L("contact@elec-dupont.fr", ""), set(), mort)[0] == FA.MOTIF_SANS_SOURCE                   # adresse déduite, sans source visible
assert FA.controle_adresse({"email": "contact@elec-dupont.fr"}, set(), mort)[0] == FA.MOTIF_SANS_SOURCE
assert FA.controle_adresse(L("contact@mort.fr"), set(), mort)[0] == FA.MOTIF_MX
assert FA.controle_adresse(L("contact@mort.fr"), set(), None)[0] == ""                                                # pas de résolveur : pas de contrôle DNS
assert FA.controle_adresse({"email": ""}, set(), mort) == ("", [])                                                    # sans e-mail : rien à contrôler ici
# la clé du CSV du lot n'a pas de « _ » : emailsource
assert FA.controle_adresse({"email": "contact@a.fr", "emailsource": "OpenStreetMap (tag email)"}, set(), mort) == ("", [])

# --- origine et avertissements (non bloquants) ---
assert FA.origine(L("a@b.fr", "OpenStreetMap (tag email)"))[0] == "OpenStreetMap"
assert FA.origine(L("a@b.fr", "https://x.fr/"))[0] == "site de l'entreprise" and FA.origine(L("a@b.fr", "page contact / mentions légales de https://x.fr/"))[0] == "site de l'entreprise"
assert FA.origine(L("a@b.fr", "page d'accueil de https://x.fr/"))[1] == "page d'accueil : https://x.fr/"
assert FA.origine(L("a@b.fr", "saisie à la main par Liam (liste d'appels du 2026-11-02)"))[0] == "saisie à la main" and FA.origine(L("a@b.fr", ""))[0] == "inconnue"
_, av = FA.controle_adresse(L("sophie.denoyelle@bbox.fr", "OpenStreetMap (tag email)"), set(), mort)
assert any("OpenStreetMap" in x for x in av) and any("prénom.nom" in x for x in av), av
assert FA.controle_adresse(L("contact@elec-dupont.fr", "OpenStreetMap (tag email)"), set(), mort)[1] == []        # domaine pro : aucun avertissement
et = FA.etiquette_origine(L("sophie.denoyelle@bbox.fr", "OpenStreetMap (tag email)"))
assert et.startswith("OpenStreetMap — ") and "ℹ à vérifier" in et, et
assert FA.etiquette_origine(L("contact@elec-dupont.fr", "page contact / mentions légales de https://elec-dupont.fr/")) == "site de l'entreprise — page contact ou mentions légales : https://elec-dupont.fr/"

# --- rebonds : adresses refusées DÉFINITIVEMENT (reponses.echecs_permanents) ---
import reponses as RP
def dsn(statut, diag, dest="jean@orange.fr"):
    return (f"From: Mail Delivery Subsystem <mailer-daemon@googlemail.com>\nSubject: Delivery Status Notification (Failure)\nMIME-Version: 1.0\nContent-Type: multipart/report; report-type=delivery-status; boundary=\"b\"\n\n"
            f"--b\nContent-Type: text/plain; charset=utf-8\n\nLe message n'a pas été remis\n--b\nContent-Type: message/delivery-status\n\nReporting-MTA: dns; googlemail.com\n\n"
            f"Final-Recipient: rfc822; {dest}\nAction: failed\nStatus: {statut}\nDiagnostic-Code: smtp; {diag}\n\n--b--\n").encode()
assert RP.echecs_permanents(dsn("5.1.1", "550 5.1.1 The email account that you tried to reach does not exist")) == {"jean@orange.fr"}
assert RP.echecs_permanents(dsn("5.5.0", "550 5.5.0 Requested action not taken: mailbox unavailable", "Re@Outlook.fr")) == {"re@outlook.fr"}
assert RP.echecs_permanents(dsn("5.7.1", "554 5.7.1 <contact@royal-donuts.fr>: Relay access denied", "contact@royal-donuts.fr")) == {"contact@royal-donuts.fr"}   # le domaine ne reçoit pas ce courrier
assert RP.echecs_permanents(dsn("4.2.2", "452 4.2.2 The recipient's inbox is out of storage space")) == set()                      # retard : l'adresse existe
assert RP.echecs_permanents(dsn("4.4.1", "The recipient server did not accept our requests to connect")) == set()
assert RP.echecs_permanents(dsn("5.2.0", "552 5.2.0 spam detected")) == set()                                                       # refus de contenu : pas un problème d'adresse
assert RP.echecs_permanents(b"From: a@b.fr\nSubject: bonjour\n\nsalut") == set()
tmp = Path(tempfile.mkdtemp(prefix="filtre-test-"))
IDENT_FAUSSE = {"prenom_nom": "Liam Test", "entreprise": "LM MULTI-SERVICES", "siret": "12345678901234", "telephone": "06 00 00 00 00", "email_reponse": "ecrire@exemple.fr"}      # identité FICTIVE : les tests ne dépendent jamais du vrai identite.json (absent d'un clone propre)
import json as _j; (tmp / "identite.json").write_text(_j.dumps(IDENT_FAUSSE), encoding="utf-8")
fx = tmp / "exclus-emails.json"
assert RP.exclure_adresses(sorted({"jean@orange.fr", "re@outlook.fr"}), fx) == ["jean@orange.fr", "re@outlook.fr"] and RP.exclure_adresses(["jean@orange.fr"], fx) == []

# --- branchement dans prospection.py : lot (cmd_preparer), bloc, relances ---
import prospection as X
X.lien_exemple = lambda metier, lien_ok=None: "https://b2b-demos.vercel.app/exemple/"
_liens = Path(tempfile.mkdtemp(prefix="prospection-test-liens-")); X.ICI = _liens
(_liens / "liens-metiers.json").write_text(json.dumps({"electricien": "https://x/e/"}), encoding="utf-8")
(_liens / "exclus-emails.json").write_text(json.dumps(["contact@rebondie.fr"]), encoding="utf-8")   # lue par prospection.exclusions()
X.R.IDENTITE = tmp / "identite.json"
X.ETAT, X.TROUVES, X.MESSAGES, X.APERCU, X.LOTS = tmp / "etat.json", tmp / "trouves.csv", tmp / "messages.md", tmp / "apercu.html", tmp / "lots"
X.S.FICHIER = X.R.SUIVI = tmp / "suivi.csv"; X.G.PUBLIC = tmp / "public"
X.P.CONFIG = tmp / "reponses-config.json"; X.P.CONFIG.write_text('{"api": {"actif": false}}', encoding="utf-8")
X.P.lire_env = lambda _: {"GMAIL_1_APP_PASSWORD": "aaaa bbbb", "GMAIL_2_APP_PASSWORD": "cccc"}
X.RESOLVEUR_MX = lambda d: (3, []) if "mort" in d else (0, [(10, "x")])   # DNS simulé : mort.fr n'existe pas
conf = {**X.DEFAUT, "par_boite_par_jour": 10, "reseaux_par_jour": 0, "pause_envoi_s": [0, 0]}
rows = []
CAS = [("Bonne Un", "contact@bonneun.fr", "https://bonneun.fr/"), ("Bonne Osm", "contact@bonneosm.fr", "OpenStreetMap (tag email)"), ("Rebondie", "contact@rebondie.fr", "https://rebondie.fr/"),
       ("Domaine Mort", "contact@mort.fr", "https://mort.fr/"), ("Faute", "jean@gmial.com", "https://faute.fr/"), ("Sans Source", "contact@sanssource.fr", ""), ("Mal Formee", "contact@mal..formee.fr", "https://mal.fr/")]
for i, (nom, mail, src) in enumerate(CAS):
    r = {k: "" for k in X.COLS}
    r.update(nom=nom, metier="électricien", ville="Rouen", siren=str(200000000 + i), cp="76000", statut="trouvé", email=mail, email_type="generique", email_source=src,
             note_besoin="site non adapté au mobile (constaté le 27/10)", source="l'annuaire officiel des entreprises", date_collecte=str(date.today()))
    rows.append(r)
    d = X.G.PUBLIC / f"{X.G.slug(nom)}-{X.G.jeton(nom, 'Rouen')}"; d.mkdir(parents=True); (d / "index.html").write_text("x")
X.ecrire_trouves(rows)
n = X.cmd_preparer(False, conf, generer=False)
blocs = X.lire_blocs(X.MESSAGES.read_text(encoding="utf-8")); mails = [b for b in blocs if b["meta"]["type"] == "email"]
assert sorted(b["meta"]["nom"] for b in mails) == ["Bonne Osm", "Bonne Un"], [b["meta"]["nom"] for b in mails]
ec = X.etat_lire()["adresses_ecartees"]
assert len(ec) == 4 and {v["motif"].split(" (")[0] for v in ec.values()} == {FA.MOTIF_MX.split(" (")[0], "domaine proche de gmail.com", FA.MOTIF_SANS_SOURCE.split(" (")[0], FA.MOTIF_SYNTAXE}, ec
statuts = {l["nom"]: l["statut"] for l in X.lire_trouves()}
assert statuts["Domaine Mort"] == statuts["Faute"] == statuts["Sans Source"] == statuts["Mal Formee"] == "exclu" and statuts["Bonne Un"] == "préparé"
assert "Rebondie" not in ec.__str__() and statuts["Rebondie"] == "trouvé"   # déjà rebondie : écartée plus tôt, par exclusions() (dispo), sans passer par le filtre
por = {b["meta"]["nom"]: b for b in mails}
assert "- Origine de l'adresse : OpenStreetMap — tag « email » d'une fiche OpenStreetMap" in por["Bonne Osm"]["texte"] and por["Bonne Osm"]["meta"]["origine_adresse"] == "OpenStreetMap"
assert "- Origine de l'adresse : site de l'entreprise — page : https://bonneun.fr/" in por["Bonne Un"]["texte"] and por["Bonne Un"]["ok"] and por["Bonne Osm"]["ok"]
# réglage filtre_adresses = false : l'ancien comportement (rien d'écarté par ce filtre)
rows2 = [{**r, "statut": "trouvé", "nom": r["nom"] + " bis", "siren": str(int(r["siren"]) + 50), "email": "contact@autre-mort.fr", "email_source": "https://autre-mort.fr/"} for r in rows[3:4]]
d = X.G.PUBLIC / f"{X.G.slug('Domaine Mort bis')}-{X.G.jeton('Domaine Mort bis', 'Rouen')}"; d.mkdir(parents=True); (d / "index.html").write_text("x")
X.ecrire_trouves(X.lire_trouves() + rows2)
X.cmd_preparer(False, {**conf, "filtre_adresses": False}, generer=False)
assert any(b["meta"]["nom"] == "Domaine Mort bis" for b in X.lire_blocs(X.MESSAGES.read_text(encoding="utf-8")))

# relances : jamais vers une adresse rebondie (exclus-emails.json)
hier = str(date.today() - timedelta(days=1))
with open(X.S.FICHIER, "w", encoding="utf-8-sig", newline="") as f_:
    w_ = csv.DictWriter(f_, fieldnames=X.S.COLS, delimiter=";"); w_.writeheader()
    for nom, mail in (("Ok Relance", "contact@okrelance.fr"), ("Rebondie Relance", "contact@rebondie.fr")):
        w_.writerow({"nom": nom, "ville": "Rouen", "email": mail, "statut": "envoyé", "date_envoi": str(date.today() - timedelta(days=2)), "relance_j2": hier})
etr = X.etat_lire()
for nom, mail in (("Ok Relance", "contact@okrelance.fr"), ("Rebondie Relance", "contact@rebondie.fr")):
    etr["envois"][X.S.cle({"nom": nom, "ville": "Rouen"})] = {"nom": nom, "ville": "Rouen", "email": mail, "box": X.boites()[0], "date": str(date.today() - timedelta(days=2)), "message_id": "<x@y>", "objet": "Objet", "lien": "https://x/"}
X.etat_ecrire(etr, False)
assert X.cmd_relances(False, conf) == 1
rel = [b for b in X.lire_blocs(X.MESSAGES.read_text(encoding="utf-8")) if b["meta"] and b["meta"].get("type") == "relance"]
assert [b["meta"]["email"] for b in rel] == ["contact@okrelance.fr"], rel

X.RESOLVEUR_MX = None
print("OK : tous les tests du filtre d'adresses passent (dossier temporaire :", tmp, ")")
import shutil; shutil.rmtree(tmp, ignore_errors=True); shutil.rmtree(_liens, ignore_errors=True)
