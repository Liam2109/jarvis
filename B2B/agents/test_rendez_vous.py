#!/usr/bin/env python3
"""Tests silencieux de l'agent rendez-vous : AUCUN réseau (faux fichier iCal, faux Discord), fichiers temporaires.  python agents\\test_rendez_vous.py
Écrits AVANT le code (rendez-vous.py). Règles de Liam : seuls les événements « Rendez-vous de 15 minutes » ; un rendez-vous annoncé UNE fois (nouveau, déplacé, annulé : messages séparés) ;
rappel 30 min avant, une fois ; au premier passage l'historique n'est jamais rejoué ; simulation par défaut (le journal dit ce qui serait posté) ; l'adresse secrète iCal n'apparaît JAMAIS
(ni journal, ni état, ni alerte, ni message, ni sortie) ; erreur = arrêt + alerte Discord."""
import contextlib, importlib.util, io, os, re, sys, tempfile, json
os.environ.setdefault("JARVIS_TEST", "1")
from datetime import datetime, timedelta, timezone
from pathlib import Path
spec = importlib.util.spec_from_file_location("rendez_vous", Path(__file__).resolve().parent / "rendez-vous.py"); D = importlib.util.module_from_spec(spec); spec.loader.exec_module(D)

def reseau(*a, **k): raise AssertionError("appel réseau interdit dans les tests")
D.telecharger_ical, D.acces_discord_reel, D.api_discord_reel = reseau, reseau, reseau
tmp = Path(tempfile.mkdtemp(prefix="rdv-test-"))
D.ETAT, D.CONFIG, D.ARRET, D.VERROU, D.JOURNAL = tmp / "etat.json", tmp / "config.json", tmp / "arret", tmp / "verrou", tmp / "journal.log"
SECRET = "SECRETTOKEN123abcXYZ"
URL = f"https://calendar.google.com/calendar/ical/liam%40example.invalid/private-{SECRET}/basic.ics"
UTC = timezone.utc
NOW = datetime(2026, 11, 4, 10, 0, tzinfo=UTC)

def VE(uid, debut, titre="Rendez-vous de 15 minutes - Jeanne", cn="Jeanne Martin", mail="jeanne.perso@example.invalid", desc=None, statut="CONFIRMED", seq=0, meet="https://meet.google.com/abc-defg-hij", extra=()):
    if desc is None: desc = "Entreprise : Boulangerie Fictive Dupont\\nE-mail de l'entreprise : contact@boulangerie-fictive.example\\nTéléphone : 06 99 99 99 99\\nNotes : ne pas afficher"
    l = ["BEGIN:VEVENT", f"UID:{uid}", f"DTSTART:{debut}", "DTEND:" + debut, f"SUMMARY:{titre}", f"STATUS:{statut}", f"SEQUENCE:{seq}", "ORGANIZER;CN=Liam:mailto:liam@example.invalid",
         "ATTENDEE;CN=Liam;PARTSTAT=ACCEPTED:mailto:liam@example.invalid", f"ATTENDEE;CN={cn};PARTSTAT=ACCEPTED:mailto:{mail}", "DESCRIPTION:" + desc, *extra]
    if meet: l.append("X-GOOGLE-CONFERENCE:" + meet)
    return "\r\n".join(l + ["END:VEVENT"])
def FEED(*evs): return "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//Google Inc//Google Calendar//EN\r\n" + "\r\n".join(evs) + "\r\nEND:VCALENDAR\r\n"
A = VE("a@google.com", "20261104T143000Z")                                                      # mercredi 4 nov. 2026, 15 h 30 à Paris (heure d'hiver)
B = VE("b@google.com", "20261105T090000Z", cn="Paul Durand", mail="paul@example.invalid", desc="Prénom : Paul\\nEntreprise : Garage Fictif Martin\\nE-mail : paul@garage-fictif.example", meet="")
HORS = VE("h@google.com", "20261104T150000Z", titre="Déjeuner avec Marc")

# --- lecture iCal : filtre du titre, champs, dédoublonnage, annulation ---
ev = D.lire_ical(FEED(A, B, HORS)); assert sorted(e["prenom"] for e in ev.values()) == ["Jeanne", "Paul"], ev                       # hors sujet ignoré
a = ev["a@google.com|"]; assert a["entreprise"] == "Boulangerie Fictive Dupont" and a["email"] == "contact@boulangerie-fictive.example" and a["meet"] == "https://meet.google.com/abc-defg-hij" and a["debut"] == datetime(2026, 11, 4, 14, 30, tzinfo=UTC) and not a["annule"]
b = ev["b@google.com|"]; assert b["prenom"] == "Paul" and b["entreprise"] == "Garage Fictif Martin" and b["email"] == "paul@garage-fictif.example" and b["meet"] == ""          # « Prénom : » du formulaire prime sur le nom de l'invité
assert "Liam" not in [e["prenom"] for e in ev.values()]                                                                                  # l'organisateur n'est jamais l'appelant
sans = D.lire_ical(FEED(VE("c@google.com", "20261104T160000Z", desc="Notes : rien", extra=())))["c@google.com|"]
assert sans["entreprise"] == "Martin" and sans["email"] == "jeanne.perso@example.invalid" and sans["prenom"] == "Jeanne"                    # sans description : convention du formulaire (CN = « Prénom Nom », Nom = entreprise), e-mail de l'invité
rep = FEED(VE("a@google.com", "20261104T143000Z", desc="Entreprise : Boulangerie Fic\\, tive\r\n  Dupont\\nE-mail de l'entreprise : x@y.example"))
assert D.lire_ical(rep)["a@google.com|"]["entreprise"] == "Boulangerie Fic, tive Dupont" or D.lire_ical(rep)["a@google.com|"]["entreprise"].startswith("Boulangerie Fic, tive"), D.lire_ical(rep)   # lignes repliées, virgule échappée
dbl = D.lire_ical(FEED(A, VE("a@google.com", "20261104T150000Z", seq=2), A)); assert len(dbl) == 1 and dbl["a@google.com|"]["debut"].hour == 15            # doublon : la plus haute SEQUENCE gagne
assert D.lire_ical(FEED(VE("x@google.com", "20261104T150000Z", statut="CANCELLED")))["x@google.com|"]["annule"] is True
assert D.lire_ical(FEED("\r\n".join(["BEGIN:VEVENT", "UID:j@g", "DTSTART;VALUE=DATE:20261104", "SUMMARY:Rendez-vous de 15 minutes - Jour", "END:VEVENT"]))) == {}      # sans heure : ignoré
assert D.lire_ical("n'importe quoi") is None and D.lire_ical(FEED()) == {}                                                                  # pas un iCal : None ; iCal vide : {}
loc = D.lire_ical(FEED(VE("l@google.com", "20261104T150000Z", meet="", extra=("LOCATION:https://meet.google.com/zzz-yyyy-xxx",))))["l@google.com|"]; assert loc["meet"] == "https://meet.google.com/zzz-yyyy-xxx"

# --- heure de Paris ---
assert D.quand(datetime(2026, 11, 4, 14, 30, tzinfo=UTC)) == "mercredi 04/11/2026 à 15 h 30" and D.quand(datetime(2026, 7, 1, 12, 5, tzinfo=UTC)) == "mercredi 01/07/2026 à 14 h 05"      # hiver +1, été +2
assert D.quand(datetime(2026, 11, 4, 15, 0, tzinfo=UTC)).endswith("16 h 00")

# --- messages : prénom, entreprise, e-mail, jour et heure, Meet ; rien d'autre ---
m = D.message("nouveau", a)
for x in ("Nouveau rendez-vous", "Appelant : Jeanne", "Entreprise : Boulangerie Fictive Dupont", "E-mail : contact@boulangerie-fictive.example", "mercredi 04/11/2026 à 15 h 30 (heure de Paris)", "https://meet.google.com/abc-defg-hij"): assert x in m, (x, m)
assert "06 99" not in m and "ne pas afficher" not in m and "jeanne.perso" not in m and "Martin" not in m                                    # téléphone, notes, nom de famille, e-mail de l'invité (quand celui de l'entreprise existe) : jamais
assert "Meet" not in D.message("nouveau", b) and "Entreprise : Martin" in D.message("nouveau", sans) and "E-mail : jeanne.perso@example.invalid" in D.message("nouveau", sans) and "Prénom :" not in m

# --- formulaire Google à 3 champs (Prénom, Nom, e-mail), SANS description : le nom de l'invité est « Prénom Nom » ; Prénom = APPELANT, Nom = ENTREPRISE appelée, e-mail = e-mail de l'entreprise ---
def F(cn, mail="contact@boulangerie-fictive.example", desc="", **k): return D.lire_ical(FEED(VE("f@google.com", "20261104T143000Z", cn=cn, mail=mail, desc=desc, **k)))["f@google.com|"]
f1 = F("Sid Boulangerie Fictive Dupont"); assert (f1["prenom"], f1["entreprise"], f1["email"]) == ("Sid", "Boulangerie Fictive Dupont", "contact@boulangerie-fictive.example"), f1
mf = D.message("nouveau", f1)
for x in ("Appelant : Sid", "Entreprise : Boulangerie Fictive Dupont", "E-mail : contact@boulangerie-fictive.example", "mercredi 04/11/2026 à 15 h 30 (heure de Paris)", "Lien Meet : https://meet.google.com/abc-defg-hij"): assert x in mf, (x, mf)
assert "Prénom" not in mf and "Martin" not in mf and mf.splitlines()[1:4] == ["Appelant : Sid", "Entreprise : Boulangerie Fictive Dupont", "E-mail : contact@boulangerie-fictive.example"]
assert F("  Sid   Boulangerie  Dupont ")["entreprise"] == "Boulangerie Dupont" and F("Jean-Pierre Garage Fictif Martin")["prenom"] == "Jean-Pierre"
for cn_vide, appelant in (("Sid", "Sid"), ("", ""), ("   ", ""), ("sid@exemple.invalid", ""), ("Sid contact@boulangerie.example", "Sid")):       # nom vide ou ressemblant à une adresse e-mail : « non renseignée »
    g = F(cn_vide); assert g["entreprise"] == "", (cn_vide, g)
    mg = D.message("nouveau", g); assert "Entreprise : non renseignée" in mg and f"Appelant : {appelant or 'non renseigné'}" in mg and "contact@boulangerie.example" not in mg.split("E-mail")[0] and "sid@" not in mg.split("E-mail")[0], (cn_vide, mg)
assert F("Sid Autre Nom", desc="Entreprise : Garage Priorité\\nNotes : x")["entreprise"] == "Garage Priorité" and F("Sid Autre Nom", desc="Entreprise : Garage Priorité")["prenom"] == "Sid"   # la description a priorité
assert F("Sid Boulangerie", desc="Notes : rien")["entreprise"] == "Boulangerie" and F("Sid Boulangerie", mail="")["email"] == ""                   # description sans « Entreprise » : le formulaire sert
assert F("Sid Boulangerie", desc="E-mail : direction@boulangerie.example")["email"] == "direction@boulangerie.example"                               # « E-mail » de la description prime aussi
assert "Rendez-vous déplacé" in D.message("deplace", a, avant=datetime(2026, 11, 4, 9, 0, tzinfo=UTC)) and "Avant : mercredi 04/11/2026 à 10 h 00" in D.message("deplace", a, avant=datetime(2026, 11, 4, 9, 0, tzinfo=UTC))
assert "Rendez-vous annulé" in D.message("annule", a) and "Rappel" in D.message("rappel", a) and "30 minutes" in D.message("rappel", a)
mal = {**a, "prenom": "@everyone `<@123>` **x**", "entreprise": "A" * 300, "email": "pas un mail"}; mm = D.message("nouveau", mal)
assert "<" not in mm and "`" not in mm and "**x**" not in mm and "A" * 100 not in mm and "E-mail : non renseigné" in mm                         # champs d'un tiers = données : nettoyés, bornés

# --- faux Discord, journal, alertes ---
class Faux:
    """Faux Discord. Le salon par défaut (2e valeur de acces) est « salon-defaut » ; le salon « 📅-rdv » (catégorie « B2B VENTE SITE WEB ») est « salon-rdv »."""
    def __init__(self):
        self.posts, self.cibles, self.appels, self.panne_post, self.panne_salons, self.acces_appels = [], [], [], False, False, 0; self.n = 100
        self.salons = [{"id": "cat1", "name": "B2B VENTE SITE WEB", "type": 4}, {"id": "salon-rdv", "name": "📅-rdv", "type": 0, "parent_id": "cat1"}, {"id": "x1", "name": "général", "type": 0},
                       {"id": "x2", "name": "rdv", "type": 2}, {"id": "x3", "name": "rdv-archive", "type": 0}]
    def acces(self): self.acces_appels += 1; return ("jeton-faux", "salon-defaut", "42")
    def api(self, jeton, methode, chemin, corps=None):
        self.appels.append((methode, chemin, corps))
        if methode == "GET":
            if chemin == "/users/@me/guilds": return None if self.panne_salons else [{"id": "g1"}]
            return self.salons if chemin == "/guilds/g1/channels" else []
        if self.panne_post: return None
        self.n += 1; self.posts.append(corps["content"]); self.cibles.append(chemin); return {"id": str(self.n)}
alertes = []
def alerte(t): alertes.append(t)
def journal(): return D.JOURNAL.read_text(encoding="utf-8") if D.JOURNAL.exists() else ""
def effacer():
    for p in (D.ETAT, D.JOURNAL, D.ARRET, D.VERROU): p.unlink(missing_ok=True)
    alertes.clear()
sortie = io.StringIO()
def P(feed, conf, fx, now=NOW, a_blanc=False, url=URL):
    with contextlib.redirect_stdout(sortie): return D.passage({**conf, "ical_url": url}, a_blanc, now, (feed if callable(feed) else (lambda u: feed)), fx.api, fx.acces, alerte)
base = D.cfg(); assert base["envoi_automatique"] is False and base["cycle_minutes"] == 5 and base["ical_url"] == "" and base["salon_nom"] == "rdv" and base["salon_id"] == "" and base["rappel_minutes"] == 30
reel = {**base, "envoi_automatique": True}

# --- premier passage : l'état actuel est noté, l'historique n'est JAMAIS rejoué ---
effacer(); fx = Faux(); r = P(FEED(A, B, HORS), reel, fx)
assert r["action"] == "état noté" and not fx.posts and D.etat_lire()["initialise"] is True and len(D.etat_lire()["rdv"]) == 2 and "état noté" in journal()
r = P(FEED(A, B, HORS), reel, fx); assert not fx.posts and r["action"] == "ok" and r["messages"] == []                                   # rien de nouveau : rien posté
# --- nouveau : une seule fois, même si l'événement est en double dans le fichier ---
C = VE("c@google.com", "20261106T080000Z", cn="Sophie Lenoir", mail="sophie@example.invalid", desc="Entreprise : Fleuriste Fictive\\nE-mail de l'entreprise : fleurs@fictive.example")
r = P(FEED(A, B, C, C), reel, fx); assert len(fx.posts) == 1 and "Nouveau rendez-vous" in fx.posts[0] and "Sophie" in fx.posts[0] and "Fleuriste Fictive" in fx.posts[0] and "vendredi 06/11/2026 à 09 h 00" in fx.posts[0]
P(FEED(A, B, C, C), reel, fx); P(FEED(B, A, C), reel, fx); assert len(fx.posts) == 1                                                      # jamais deux fois
envoi = [a for a in fx.appels if a[0] == "POST"]; assert len(envoi) == 1 and envoi[0][1] == "/channels/salon-rdv/messages" and envoi[0][2]["allowed_mentions"] == {"users": ["42"]}     # salon « 📅-rdv » trouvé par « rdv », emoji ignoré
assert fx.cibles == ["/channels/salon-rdv/messages"] and not [c for c in fx.cibles if "salon-defaut" in c]
# --- déplacé : un message séparé, une seule fois par nouvel horaire ---
C2 = VE("c@google.com", "20261106T100000Z", cn="Sophie Lenoir", mail="sophie@example.invalid", desc="Entreprise : Fleuriste Fictive\\nE-mail de l'entreprise : fleurs@fictive.example", seq=1)
P(FEED(A, B, C2), reel, fx); assert len(fx.posts) == 2 and "Rendez-vous déplacé" in fx.posts[1] and "11 h 00" in fx.posts[1] and "Avant : vendredi 06/11/2026 à 09 h 00" in fx.posts[1], fx.posts
P(FEED(A, B, C2), reel, fx); P(FEED(A, B, C2, C2), reel, fx); assert len(fx.posts) == 2
# --- annulé : par STATUS:CANCELLED, ou parce que l'événement a disparu du fichier : un seul message ---
Cx = VE("c@google.com", "20261106T100000Z", cn="Sophie Lenoir", mail="sophie@example.invalid", desc="Entreprise : Fleuriste Fictive\\nE-mail de l'entreprise : fleurs@fictive.example", statut="CANCELLED", seq=2)
P(FEED(A, B, Cx), reel, fx); assert len(fx.posts) == 3 and "Rendez-vous annulé" in fx.posts[2] and "Fleuriste Fictive" in fx.posts[2]
P(FEED(A, B, Cx), reel, fx); P(FEED(A, B), reel, fx); assert len(fx.posts) == 3
P(FEED(A), reel, fx); assert len(fx.posts) == 4 and "Rendez-vous annulé" in fx.posts[3] and "Garage Fictif Martin" in fx.posts[3]            # B a disparu (avenir) : annulé
P(FEED(A), reel, fx); assert len(fx.posts) == 4
assert P(FEED(), reel, fx)["action"] == "ok" and len(fx.posts) == 5                                                                        # A disparaît aussi : annulé
# un événement passé qui sort du fichier n'est pas une annulation
effacer(); fx = Faux(); P(FEED(A), reel, fx, now=NOW); P(FEED(), reel, fx, now=NOW + timedelta(days=2)); assert not fx.posts
# une annulation jamais vue avant ne déclenche aucun message ; un rendez-vous réactivé (même UID) redevient « nouveau »
effacer(); fx = Faux(); P(FEED(A), reel, fx); P(FEED(A, Cx), reel, fx); assert not fx.posts
P(FEED(A, C), reel, fx); assert len(fx.posts) == 1 and "Nouveau rendez-vous" in fx.posts[0]

# --- rappel 30 minutes avant, une seule fois ; jamais pour un rendez-vous annulé ; nouvel horaire = nouveau rappel ---
effacer(); fx = Faux(); P(FEED(A), reel, fx)
P(FEED(A), reel, fx, now=datetime(2026, 11, 4, 13, 59, tzinfo=UTC)); assert not fx.posts                                                  # 31 min avant : trop tôt
P(FEED(A), reel, fx, now=datetime(2026, 11, 4, 14, 1, tzinfo=UTC)); assert len(fx.posts) == 1 and "Rappel" in fx.posts[0] and "Jeanne" in fx.posts[0] and "https://meet.google.com/abc-defg-hij" in fx.posts[0]
P(FEED(A), reel, fx, now=datetime(2026, 11, 4, 14, 6, tzinfo=UTC)); P(FEED(A), reel, fx, now=datetime(2026, 11, 4, 14, 29, tzinfo=UTC)); assert len(fx.posts) == 1   # une seule fois
effacer(); fx = Faux(); P(FEED(A), reel, fx); P(FEED(A), reel, fx, now=datetime(2026, 11, 4, 14, 31, tzinfo=UTC)); assert not fx.posts          # rendez-vous commencé : plus de rappel
effacer(); fx = Faux(); P(FEED(A), reel, fx); P(FEED(VE("a@google.com", "20261104T143000Z", statut="CANCELLED", seq=1)), reel, fx, now=datetime(2026, 11, 4, 14, 5, tzinfo=UTC))
assert len(fx.posts) == 1 and "annulé" in fx.posts[0]                                                                                      # annulé : pas de rappel
effacer(); fx = Faux(); P(FEED(A), reel, fx); P(FEED(A), reel, fx, now=datetime(2026, 11, 4, 14, 1, tzinfo=UTC))
A2 = VE("a@google.com", "20261104T170000Z", seq=1); P(FEED(A2), reel, fx, now=datetime(2026, 11, 4, 14, 2, tzinfo=UTC)); P(FEED(A2), reel, fx, now=datetime(2026, 11, 4, 16, 40, tzinfo=UTC))
assert [("Rappel" in p, "déplacé" in p) for p in fx.posts] == [(True, False), (False, True), (True, False)], fx.posts                      # rappel, déplacement, nouveau rappel
# rendez-vous pris moins de 30 min avant : « nouveau » puis rappel, chacun une fois
effacer(); fx = Faux(); P(FEED(B), reel, fx); P(FEED(B, A), reel, fx, now=datetime(2026, 11, 4, 14, 10, tzinfo=UTC)); assert ["Nouveau" in p or "Rappel" in p for p in fx.posts] == [True, True] and "Nouveau" in fx.posts[0] and "Rappel" in fx.posts[1]
# le rappel d'un rendez-vous déjà là au premier passage part quand même (il regarde l'avenir, pas l'historique)
effacer(); fx = Faux(); P(FEED(A), reel, fx, now=datetime(2026, 11, 4, 14, 10, tzinfo=UTC)); assert len(fx.posts) == 1 and "Rappel" in fx.posts[0]

# --- simulation : rien d'envoyé, le journal dit ce qui serait posté, une seule fois ; passage au réel sans inonder le salon ---
effacer(); fx = Faux(); sim = base
P(FEED(A), sim, fx); P(FEED(A, B), sim, fx); P(FEED(A, B), sim, fx)
assert not fx.appels and fx.acces_appels == 0 and len(re.findall(r"serait posté", journal())) == 1 and "nouveau" in journal() and "Paul" in journal() and "paul@garage" not in journal() and "meet.google" not in journal()
P(FEED(A, B), sim, fx, now=datetime(2026, 11, 4, 14, 5, tzinfo=UTC)); assert len(re.findall(r"serait posté", journal())) == 2 and "rappel" in journal() and not fx.appels
P(FEED(A, B, C), reel, fx, now=datetime(2026, 11, 4, 14, 6, tzinfo=UTC)); assert not fx.posts and D.etat_lire()["reel_initialise"] is True       # 1er passage réel : état noté, pas de déluge
P(FEED(A, B, C, VE("d@google.com", "20261107T080000Z", cn="Lea Roy", mail="lea@example.invalid")), reel, fx, now=datetime(2026, 11, 4, 14, 7, tzinfo=UTC)); assert len(fx.posts) == 1 and "Lea" in fx.posts[0]

# --- réservation du formulaire à 3 champs de bout en bout : simulation (journal seulement) puis mode réel (un message) ---
FORM = VE("f@google.com", "20261106T080000Z", cn="Sid Boulangerie Fictive Dupont", mail="contact@boulangerie-fictive.example", desc="")
effacer(); fx = Faux(); P(FEED(A), sim, fx); P(FEED(A, FORM), sim, fx)
assert not fx.appels and "serait posté | nouveau | Sid | Boulangerie Fictive Dupont" in journal() and "contact@" not in journal()
effacer(); fx = Faux(); P(FEED(A), reel, fx); P(FEED(A, FORM), reel, fx); P(FEED(A, FORM), reel, fx)
assert len(fx.posts) == 1 and "Appelant : Sid" in fx.posts[0] and "Entreprise : Boulangerie Fictive Dupont" in fx.posts[0] and "E-mail : contact@boulangerie-fictive.example" in fx.posts[0] and "vendredi 06/11/2026 à 09 h 00 (heure de Paris)" in fx.posts[0] and "meet.google.com/abc-defg-hij" in fx.posts[0]

# --- à blanc : aucune écriture, aucun appel Discord ---
effacer(); fx = Faux(); P(FEED(A), reel, fx); et = D.ETAT.read_text(encoding="utf-8"); jn = journal()
r = P(FEED(A, B), reel, fx, a_blanc=True); assert D.ETAT.read_text(encoding="utf-8") == et and journal() == jn and not fx.appels and r["messages"] == ["nouveau"]

# --- Discord qui refuse le message : rien n'est marqué, nouvel essai au passage suivant ---
effacer(); fx = Faux(); P(FEED(A), reel, fx); fx.panne_post = True; P(FEED(A, B), reel, fx); assert not fx.posts and "b@google.com|" not in D.etat_lire()["rdv"]
fx.panne_post = False; P(FEED(A, B), reel, fx); assert len(fx.posts) == 1 and "Paul" in fx.posts[0]; P(FEED(A, B), reel, fx); assert len(fx.posts) == 1
# accès Discord incomplet : rien posté, rien marqué
effacer(); fx = Faux(); P(FEED(A), reel, fx); fx.acces = lambda: None; P(FEED(A, B), reel, fx); assert not fx.posts and "b@google.com|" not in D.etat_lire()["rdv"] and not D.etat_lire().get("suspendu")

# --- salon Discord : « 📅-rdv » trouvé par son nom sans emoji, ou par salon_id ; JAMAIS de repli sur le salon par défaut ---
fx = Faux(); assert D.resoudre_salon(reel, "j", fx.api) == "salon-rdv"                                                                      # nom « rdv » : ni « rdv-archive », ni le salon vocal « rdv », ni « général »
assert D.resoudre_salon({**reel, "salon_nom": "📅-RDV"}, "j", fx.api) == "salon-rdv" and D.resoudre_salon({**reel, "salon_nom": "📅│rdv"}, "j", fx.api) == "salon-rdv"
n_get = len(fx.appels); assert D.resoudre_salon({**reel, "salon_id": "123456789012345678", "salon_nom": "autre"}, "j", fx.api) == "123456789012345678" and len(fx.appels) == n_get     # identifiant : aucune recherche
# --- mémorisation : la 1re résolution par nom écrit salon_id dans rendez-vous-config.local.json (M.ecrire_local), relu par cfg() : plus besoin de rappeler /guilds au passage suivant ---
assert D.cfg()["salon_id"] == "salon-rdv"
fx2 = Faux(); fx2.salons = [{"id": "777777777777777777", "name": "📅-rdv", "type": 0}]
assert D.resoudre_salon({**reel, "salon_nom": "rdv"}, "j", fx2.api) == "777777777777777777" and len(fx2.appels) == 2      # 1re fois : cherché (2 appels GET)
assert D.cfg()["salon_id"] == "777777777777777777"
n_get3 = len(fx2.appels); assert D.resoudre_salon(D.cfg(), "j", fx2.api) == "777777777777777777" and len(fx2.appels) == n_get3   # 2e fois : salon_id en cache, aucun appel Discord
for mauvais, mot in (({"salon_id": "abc/../x"}, "salon_id"), ({"salon_nom": "inexistant"}, "introuvable"), ({"salon_nom": ""}, "salon_nom"), ({"salon_nom": "rdv-archive", "salon_id": "12"}, "salon_id")):
    try: D.resoudre_salon({**reel, **mauvais}, "j", fx.api); assert False, mauvais
    except D.ErreurSalon as e: assert mot in str(e), (mauvais, str(e))
fx.salons.append({"id": "x9", "name": "rdv", "type": 0})
try: D.resoudre_salon(reel, "j", fx.api); assert False
except D.ErreurSalon as e: assert "plusieurs" in str(e)                                                                                      # ambigu : on ne devine pas
fx = Faux(); fx.panne_salons = True
try: D.resoudre_salon(reel, "j", fx.api); assert False
except D.ErreurSalon as e: assert "illisible" in str(e)
# bout en bout, salon_id : le message part dans ce salon sans chercher par nom
effacer(); fx = Faux(); idc = {**reel, "salon_id": "123456789012345678"}; P(FEED(A), idc, fx); P(FEED(A, B), idc, fx)
assert fx.cibles == ["/channels/123456789012345678/messages"] and not [a for a in fx.appels if a[0] == "GET"]
# salon introuvable : rien n'est posté (ni dans le salon par défaut), rien n'est marqué, journal + UNE alerte par jour, pas de suspension ; le salon créé, le message en attente part
effacer(); fx = Faux(); P(FEED(A), reel, fx); fx.salons = [x for x in fx.salons if x["id"] != "salon-rdv"]
for i in range(3): r = P(FEED(A, C), reel, fx, now=NOW + timedelta(minutes=5 * i))
assert not fx.posts and not fx.cibles and "c@google.com|" not in D.etat_lire()["rdv"] and "suspendu" not in D.etat_lire(), (fx.cibles, r)
assert len(alertes) == 1 and "rdv" in alertes[0] and "introuvable" in alertes[0] and "par défaut" in alertes[0] and "salon-defaut" not in alertes[0]
assert "alerte | salon" in journal() and "introuvable" in journal() and "message non posté" in journal()
P(FEED(A, C), reel, fx, now=NOW + timedelta(hours=5)); assert len(alertes) == 1                                                              # même jour (Paris) : pas de seconde alerte
P(FEED(A, C), reel, fx, now=NOW + timedelta(days=1, hours=3)); assert len(alertes) == 2 and not fx.posts                                      # jour suivant : une nouvelle alerte
fx.salons.append({"id": "salon-rdv", "name": "📅-rdv", "type": 0}); P(FEED(A, C), reel, fx, now=NOW + timedelta(days=1, hours=3, minutes=5))
assert len(fx.posts) == 1 and "Sophie" in fx.posts[0] and fx.cibles == ["/channels/salon-rdv/messages"]
# Discord illisible, ou plusieurs salons « rdv » : même règle
for cas in ("panne", "double"):
    effacer(); fx = Faux(); P(FEED(A), reel, fx)
    if cas == "panne": fx.panne_salons = True
    else: fx.salons.append({"id": "x9", "name": "📅 rdv", "type": 0})
    P(FEED(A, C), reel, fx); assert not fx.posts and len(alertes) == 1 and "c@google.com|" not in D.etat_lire()["rdv"], cas
# rappel : même règle (jamais dans un autre salon)
effacer(); fx = Faux(); fx.salons = [x for x in fx.salons if x["id"] != "salon-rdv"]; P(FEED(A), reel, fx); P(FEED(A), reel, fx, now=datetime(2026, 11, 4, 14, 5, tzinfo=UTC)); assert not fx.posts and len(alertes) == 1
# simulation : aucune recherche de salon, aucun appel Discord
effacer(); fx = Faux(); fx.salons = []; P(FEED(A), base, fx); P(FEED(A, B), base, fx); assert not fx.appels and not alertes

# --- erreurs ---
effacer(); fx = Faux(); r = P(FEED(A), reel, fx, url="")
assert r["action"] == "arrêt" and D.etat_lire()["suspendu"]["raison"] == "configuration" and len(alertes) == 1 and "rendez-vous-config.json" in alertes[0]
assert P(FEED(A), reel, fx, url="")["action"] == "arrêt" and len(alertes) == 1                                                             # suspendu : plus rien, une seule alerte
D.reprendre(); assert "suspendu" not in D.etat_lire()
for mauvaise in ("http://calendar.google.com/x.ics", "https://example.com/x.ics", "https://calendar.google.com.evil.example/x.ics"):      # seulement https://calendar.google.com/
    assert P(FEED(A), reel, fx, url=mauvaise)["action"] == "arrêt" and D.etat_lire()["suspendu"]["raison"] == "configuration"; D.reprendre()
effacer(); fx = Faux(); P(FEED(A), reel, fx)
def refus(u): raise D.ErreurLecture("HTTP 404", definitive=True)
r = P(refus, reel, fx); assert r["action"] == "arrêt" and D.etat_lire()["suspendu"]["raison"] == "adresse iCal refusée" and len(alertes) == 1 and not fx.posts; D.reprendre()      # adresse révoquée
def panne(u): raise D.ErreurLecture("délai dépassé", definitive=False)
for i in range(4): r = P(panne, reel, fx, now=NOW + timedelta(minutes=5 * i))
assert r["action"] == "lecture impossible" and "suspendu" not in D.etat_lire() and len(alertes) == 2 and not fx.posts                         # panne passagère : on réessaie, une alerte à la 3e panne, aucune fausse annulation
assert P(FEED(A), reel, fx)["action"] == "ok" and D.etat_lire()["echecs"] == 0
for faux_fichier in ("<html>connexion</html>", "", "BEGIN:VCALENDAR"): assert P(faux_fichier, reel, fx)["action"] == "lecture impossible" and not fx.posts          # fichier invalide : jamais pris pour « tout est annulé »
assert D.etat_lire()["rdv"]["a@google.com|"]["statut"] == "actif"
def boum(u): raise ValueError("bug")
r = P(boum, reel, fx); assert r["action"] == "arrêt" and D.etat_lire()["suspendu"]["raison"] == "erreur" and "reprendre" in alertes[-1]; D.reprendre()

# --- l'adresse secrète n'apparaît nulle part ---
for p in (D.ETAT, D.JOURNAL): assert SECRET not in p.read_text(encoding="utf-8") and "private-" not in p.read_text(encoding="utf-8"), p
assert SECRET not in "".join(alertes) and SECRET not in sortie.getvalue() and "private-" not in sortie.getvalue() and "ical/liam" not in sortie.getvalue() and SECRET not in json.dumps(fx.appels)
src = Path(spec.origin).read_text(encoding="utf-8")
assert not re.search(r"print\([^)]*(url|ical_url|adresse)", src, re.I) and not re.search(r"smtplib|send_message|gmail_api|getpass|input\(|api\.stripe", src)
assert "ical_url" not in json.dumps(D.etat_lire())

# --- ménage de l'état : les rendez-vous passés depuis plus de 2 jours sortent de l'état ---
effacer(); fx = Faux(); P(FEED(A), reel, fx); assert "a@google.com|" in D.etat_lire()["rdv"]
P(FEED(), reel, fx, now=NOW + timedelta(days=4)); assert D.etat_lire()["rdv"] == {}

# --- boucle : un passage toutes les 5 min, verrou, arrêt de secours, suspension, Jarvis arrêté ---
def boucle(feed, **k):
    t, appels = [0.0], []
    def lire(u): appels.append(1); return feed
    f2 = Faux()
    def dormir(s): t[0] += s
    r = D.cmd_continu({**reel, "ical_url": URL}, False, dormir=dormir, maintenant=lambda: NOW + timedelta(seconds=t[0]), lire_ical=lire, api=f2.api, acces=f2.acces, alerte=alerte, **k); return r, len(appels)
effacer(); D.ARRET.write_text("1"); assert boucle(FEED(A))[0].startswith("arrêt") and not D.VERROU.exists() and not D.ARRET.exists()
n = [0]
def vivant(): n[0] += 1; return n[0] <= 130                                                                                                 # 130 battements de 5 s ≈ 10 min
r, passages = boucle(FEED(A), vivant=vivant); assert r == "Jarvis s'est arrêté" and passages == 3 and not D.VERROU.exists(), passages         # t = 0, 5 min, 10 min : jamais plus d'un passage toutes les 5 minutes
e = D.etat_lire(); e["suspendu"] = {"raison": "erreur", "date": "x", "detail": ""}; D.etat_ecrire(e); assert boucle(FEED(A))[0].startswith("suspendu"); D.reprendre()
D.VERROU.write_text(str(os.getpid())); assert D.cmd_continu(reel, False) == "déjà lancée"; D.VERROU.unlink()
assert D.cmd_continu(reel, True) == "à blanc" and not D.VERROU.exists()
def boum2(u): raise ValueError("bug")
effacer(); rr, _ = boucle(boum2); assert rr.startswith("suspendu") and len(alertes) == 1, (rr, alertes)                                      # erreur dans la boucle : arrêt + alerte

import shutil; shutil.rmtree(tmp, ignore_errors=True)
print("OK : tous les tests de l'agent rendez-vous passent")
