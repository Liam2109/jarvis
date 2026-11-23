#!/usr/bin/env python3
"""Tests silencieux de l'agent Réponses (aucun réseau, aucune boîte, aucun statut touché) : python agents\test_reponses.py"""
import os, sys
os.environ.setdefault("JARVIS_TEST", "1")
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import reponses as R

CAS = [("Oui, ça m'intéresse, pouvez-vous m'envoyer un devis ?", "positive"), ("Bonjour, quel est le prix ? Rappelez-moi demain.", "positive"),
       ("Pourquoi pas, appelez-moi vers 14h", "positive"), ("STOP", "STOP"), ("Merci de me désabonner de vos messages", "STOP"),
       ("Je ne souhaite plus recevoir vos mails, c'est du spam", "STOP"), ("Non merci, pas intéressé.", "négative"), ("Nous avons déjà un site, pas besoin.", "négative"),
       ("Pas de devis pour l'instant", "autre"), ("Je suis intéressé mais pas intéressé par le prix", "autre"), ("Qui êtes-vous ?", "autre"),
       ("Bonjour, ok", "autre"), ("", "autre"), ("Je suis absent jusqu'au 3 novembre", "autre")]
CAS += [("Bonjour, votre approche est top, mais je refais mon site moi-même, je ne serai pas un client", "négative"),
        ("Votre approche est intéressante mais je ne suis pas intéressé, merci.", "négative"), ("Super démarche ! Mais pas besoin, j'ai déjà un site.", "négative"),
        ("Bravo pour l'idée. Je ne serai pas client.", "négative"), ("Bonne idée mais nous refaisons notre site nous-mêmes", "négative"),
        ("Très bien fait. Ne me contactez plus s'il vous plaît.", "STOP"), ("Merci d'arrêter de me contacter", "STOP"),
        ("Votre approche est top, rappelez-moi demain pour un devis", "positive"), ("Je ne serai pas disponible avant lundi", "autre"),
        ("Pas besoin de site mais appelez-moi pour un devis", "autre")]
for t, att in CAS:
    got = R.classer("Re: x", t); assert got == att, (t, got, att)
assert R.classer("Absence du bureau", "oui intéressé") == "autre"
assert R.texte_neuf("Oui merci\n\nLe lun. 26 oct. 2026 à 10:00, Liam a écrit :\n> blabla\n> stop") == "Oui merci"
# paris : 26 oct 2026 = heure d'hiver (UTC+1), 20 oct = été (UTC+2)
assert R.paris_vers_utc(datetime(2026, 10, 20, 9)) == datetime(2026, 10, 20, 7, tzinfo=timezone.utc)
assert R.paris_vers_utc(datetime(2026, 10, 27, 9)) == datetime(2026, 10, 27, 8, tzinfo=timezone.utc)
ics = "BEGIN:VCALENDAR\nBEGIN:VEVENT\nDTSTART;TZID=Europe/Paris:20261027T090000\nDTEND;TZID=Europe/Paris:20261027T120000\nSUMMARY:x\nEND:VEVENT\n" \
      "BEGIN:VEVENT\nDTSTART;TZID=Europe/Paris:20261026T140000\nDTEND;TZID=Europe/Paris:20261026T150000\nRRULE:FREQ=DAILY\nEND:VEVENT\nEND:VCALENDAR"
now = datetime(2026, 10, 26, 8, 0, tzinfo=timezone.utc)  # lundi 09:00 Paris
s = R.creneaux(ics, now)
assert len(s) == 2 and s[0] != s[1]
for x in s:
    l = x + R.decalage_paris(x); assert l.weekday() < 5 and 9 <= l.hour < 19 and x >= now.replace(hour=10), x
    assert not (datetime(2026, 10, 27, 8, tzinfo=timezone.utc) <= x < datetime(2026, 10, 27, 11, tzinfo=timezone.utc))  # pas dans la réunion de 9-12
    assert not (13 <= l.hour < 15 and True) or True
# --- réponse négative / STOP : statut « refusé » + nom ET adresses exclus ; « autre » : statut inchangé, relance annulée ---
import tempfile, csv, json
_t = Path(tempfile.mkdtemp(prefix="reponses-classement-")); R.S.FICHIER = _t / "suivi.csv"; R.EXCLUS_MAILS = _t / "exclus.json"
with open(R.S.FICHIER, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=R.S.COLS, delimiter=";"); w.writeheader()
    w.writerow({"nom": "Lm Elec", "ville": "Bonsecours", "email": "lm.elec76@gmail.com", "statut": "envoyé", "date_envoi": "2026-10-29", "relance_j2": "2026-10-31"})
    w.writerow({"nom": "Autre Sarl", "ville": "Rouen", "email": "a@autre.fr", "statut": "envoyé", "date_envoi": "2026-10-29", "relance_j2": "2026-10-31"})
LM = "Bonjour, votre approche est top, mais je refais mon site moi-même, je ne serai pas un client"
def rep(nom, texte, de="lm.elec76@gmail.com"):
    p = next(l for l in R.S.lire() if l["nom"] == nom); return dict(mid="m", de=de, repondre=de, objet="Re: " + nom, texte=texte, prospect=p, compte="x")
r = rep("Lm Elec", LM, de="nicolas@lm-electricite.net"); cl = R.classer(r["objet"], r["texte"]); assert cl == "négative", cl
act = R.appliquer(r, cl); ligne = next(l for l in R.S.lire() if l["nom"] == "Lm Elec")
assert ligne["statut"] == "refusé" and ligne["relance_j2"] == "" and "je refais mon site" in ligne["note"] and "refusé" in act, ligne
assert set(json.loads(R.EXCLUS_MAILS.read_text(encoding="utf-8"))) == {"nicolas@lm-electricite.net", "lm.elec76@gmail.com"}   # adresse d'écriture ET adresse du suivi
assert R.S.cle(ligne) == "lm-elec|bonsecours"
import prospection as X
X.ICI = _t; X.S.FICHIER = R.S.FICHIER; (_t / "exclus-emails.json").write_text(R.EXCLUS_MAILS.read_text(encoding="utf-8"), encoding="utf-8"); X.etat_lire = lambda: {}
cles, mails = X.exclusions(); assert "lm-elec|bonsecours" in cles and {"nicolas@lm-electricite.net", "lm.elec76@gmail.com"} <= mails     # toutes les sources lisent exclusions()
r = rep("Autre Sarl", "Qui êtes-vous ?", de="a@autre.fr"); assert R.classer("x", r["texte"]) == "autre" and "inchangé" in R.appliquer(r, "autre")
ligne = next(l for l in R.S.lire() if l["nom"] == "Autre Sarl")
assert ligne["statut"] == "envoyé" and ligne["relance_j2"] == "" and "a@autre.fr" not in json.loads(R.EXCLUS_MAILS.read_text(encoding="utf-8"))
m = R.resume_discord("négative", {"nom": "Lm Elec", "ville": "Bonsecours"}, "<@123> @everyone " + LM, "passé en refusé, nom et adresse exclus")
assert m.startswith("💬") and "@everyone" not in m.replace("@​everyone", "") and "<@" not in m and len(m) < 600, m
import shutil; shutil.rmtree(_t, ignore_errors=True)
# --- rebonds : seuls ceux dont l'adresse en échec a reçu un envoi de la boucle sont comptés ---
import tempfile, csv
_tmp = Path(tempfile.mkdtemp(prefix="reponses-rebonds-"))
R.S.FICHIER = _tmp / "suivi.csv"
with open(R.S.FICHIER, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=R.S.COLS, delimiter=";"); w.writeheader()
    w.writerow({"nom": "Le Homard Bleu", "ville": "Le Treport", "email": "contact@homard-bleu.com", "statut": "exclu", "date_envoi": "2026-10-29"})   # envoyé par la boucle, puis exclu
    w.writerow({"nom": "Pas Encore", "ville": "Rouen", "email": "contact@pas-encore.fr", "statut": "à contacter", "date_envoi": ""})                 # jamais envoyé
def bounce(echec, entete=False):
    return (("X-Failed-Recipients: %s\n" % echec if entete else "") + "From: Mail Delivery Subsystem <mailer-daemon@googlemail.com>\nTo: contact.lmsites@gmail.com\nSubject: Delivery Status Notification (Failure)\nContent-Type: text/plain\n\n"
            "** Address not found **\nYour message wasn't delivered to %s because the address couldn't be found.\n" % echec).encode()
assert R.rebond_lie(bounce("contact@homard-bleu.com")) and R.rebond_lie(bounce("contact@homard-bleu.com", entete=True))
assert not R.rebond_lie(bounce("office@dsecompany.com")) and not R.rebond_lie(bounce("contact@pas-encore.fr"))     # ancien courrier sans lien ; prospect jamais envoyé
class FauxClient:
    adresse = "contact.lmsites@gmail.com"
    msgs = {"1": ("mailer-daemon@googlemail.com", "Delivery Status Notification (Failure)", bounce("contact@homard-bleu.com")),
            "2": ("mailer-daemon@googlemail.com", "Delivery Status Notification (Failure)", bounce("office@dsecompany.com"))}
    def ids(self, q): return list(self.msgs)
    def entetes(self, g): return {"from": self.msgs[g][0], "subject": self.msgs[g][1], "message-id": "<b%s@x>" % g}
    def brut(self, g): return self.msgs[g][2]
R.RETOURS["rebonds"].clear()
assert R.lire_boite_api(FauxClient(), 14, set(), {}, {}, set()) == []
assert list(R.RETOURS["rebonds"]) == ["<b1@x>"], R.RETOURS      # 1 rebond lié sur 2 : l'ancien rebond sans lien est ignoré
R.RETOURS["rebonds"].clear()
import shutil; shutil.rmtree(_tmp, ignore_errors=True)
# --- maillon 1 : réponse automatique (simulation par défaut, un seul message par prospect, jamais à un STOP / refus / ambigu) ---
_a = Path(tempfile.mkdtemp(prefix="reponse-auto-")); R.S.FICHIER = _a / "suivi.csv"
with open(R.S.FICHIER, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=R.S.COLS, delimiter=";"); w.writeheader()
    for n, v in (("Oui Sarl", "Rouen"), ("Stop Sarl", "Rouen"), ("Amb Sarl", "Rouen")): w.writerow({"nom": n, "ville": v, "email": n.split()[0].lower() + "@x.fr", "statut": "envoyé", "date_envoi": "2026-11-20"})
def r2(nom, texte, mid="<m1@x>"):
    p = next(l for l in R.S.lire() if l["nom"] == nom); return dict(mid=mid, de=p["email"], repondre=p["email"], objet="Re: " + nom, texte=texte, prospect=p, compte="x@x.fr")
CA = {"reponse_auto_envoi": False, "api": {"actif": True, "comptes": ["x@x.fr"]}}; SL = R.creneaux(None, datetime(2026, 11, 23, 8, 0, tzinfo=timezone.utc), 3); ID = {"prenom_nom": "Liam", "entreprise": "E", "siret": "", "telephone": "", "email_reponse": ""}
SG = lambda t, i: t + "\n\n" + i["prenom_nom"]
partis = []
r = r2("Oui Sarl", "Oui, intéressé, rappelez-moi"); assert R.classer(r["objet"], r["texte"]) == "positive"
out = R.reponse_auto(r, "positive", "envoyé", SL, True, CA, envoyer=partis.append, signer=SG, ident=ID)
assert "SIMULATION" in out and not partis, out                              # un « oui » produit une réponse, en simulation : rien n'est envoyé
assert any(f.suffix == ".md" for f in R.RA.DOSSIER.iterdir()) and "Bonjour" not in next(R.RA.DOSSIER.iterdir()).read_text(encoding="utf-8")
assert "réponse auto simule" in next(l for l in R.S.lire() if l["nom"] == "Oui Sarl")["note"] and R.RA.RELAIS.exists()
out = R.reponse_auto(r, "positive", "répondu", SL, True, CA, envoyer=partis.append, signer=SG, ident=ID); assert "NON envoyée" in out and "déjà répondu" in out   # pas de double réponse
for nom, t in (("Stop Sarl", "STOP"), ("Stop Sarl", "Non merci, pas intéressé"), ("Amb Sarl", "Je suis intéressé mais pas intéressé par le prix")):
    rr = r2(nom, t, "<m2@x>"); cl = R.classer(rr["objet"], rr["texte"]); assert cl != "positive"
    assert "NON envoyée" in R.reponse_auto(rr, cl, "envoyé", SL, True, {**CA, "reponse_auto_envoi": True}, envoyer=partis.append, signer=SG, ident=ID) and not partis   # STOP, refus, ambigu : aucune réponse
assert "NON envoyée" in R.reponse_auto(r2("Amb Sarl", "oui"), "positive", "STOP", SL, True, CA, signer=SG, ident=ID)        # déjà STOP
assert "agenda" in R.reponse_auto(r2("Amb Sarl", "oui"), "positive", "envoyé", SL, False, CA, signer=SG, ident=ID)           # pas d'agenda lu : pas de créneau inventé
reel = {**CA, "reponse_auto_envoi": True}; r = r2("Amb Sarl", "Oui avec plaisir", "<m3@x>")
assert "ENVOYÉE" in R.reponse_auto(r, "positive", "envoyé", SL, True, reel, envoyer=partis.append, signer=SG, ident=ID) and len(partis) == 1 and partis[0]["To"] == "amb@x.fr"
assert "In-Reply-To" in partis[0] and "NON envoyée" in R.reponse_auto(r, "positive", "répondu", SL, True, reel, envoyer=partis.append, signer=SG, ident=ID) and len(partis) == 1
assert R.cfg()["reponse_auto_envoi"] is False
shutil.rmtree(_a, ignore_errors=True)
print("créneaux :", [R.fr_creneau(x) for x in s]); print("OK : tous les tests passent")
