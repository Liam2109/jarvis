#!/usr/bin/env python3
"""Tests silencieux de l'agent Instagram : aucun réseau, aucune publication, aucun navigateur, fichiers temporaires, jetons jamais lus.  python agents\\test_instagram.py
Écrits AVANT le code (instagram.py) : ils fixent les règles de Liam (docs\\INSTAGRAM-PLAN.md) : une publication par jour vers 12 h 30, simulation par défaut,
arrêt immédiat avec alerte sur connexion perdue / vérification de sécurité / erreur, aucune information inventée, journal de chaque action."""
import os, sys, tempfile, json
os.environ.setdefault("JARVIS_TEST", "1")
from datetime import datetime, timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import instagram as I

tmp = Path(tempfile.mkdtemp(prefix="instagram-test-"))
DOSSIER = tmp / "instagram"; DOSSIER.mkdir()
for nom in ("01-intro.png", "02-video.mp4", "03-plombier.png", "04-deroule.png", "05-a-venir.png", "06-sans-legende.png", "07-plus-tard.png"):
    (DOSSIER / nom).write_bytes(b"x" * 2048)
PLAN_TXT = """# Instagram : plan

## Règles
- Une seule publication par jour.

## File des publications
| N° | Fichier | État | Date |
|---|---|---|---|
| 1 | 01-intro.png | publié | 2026-11-03 |
| 2 | 02-video.mp4 | à publier | |
| 3 | 03-plombier.png | à publier | |
| 4 | 04-deroule.png | à publier | |
| 5 | 05-a-venir.png | à publier | |
| 6 | 06-sans-legende.png | à publier | |
| 7 | 07-plus-tard.png | à publier (boutons arrondis, plus tard) | |

Quand la file est vide : prévenir Liam.

## Légendes
1. Introduction. #artisan
2. Exemple de page pour un électricien. « Atelier Lumière » est un nom fictif. Devis écrit avant de commencer. #electricien
3. Exemple de page pour un plombier-chauffagiste. Ce n'est pas un site client. #plombier
4. De l'échange à la page en ligne : visio de 15 minutes, devis écrit avec son lien de paiement, prix réglé en une fois. #siteweb
5. Notre client numéro 1 est garanti satisfait. #artisan
7. Légende qui existe mais état « plus tard ». #artisan
"""
I.PLAN, I.DOSSIER, I.ETAT, I.CONFIG, I.ARRET, I.VERROU, I.JOURNAL, I.A_VALIDER = tmp / "plan.md", DOSSIER, tmp / "etat.json", tmp / "config.json", tmp / "arret", tmp / "verrou", tmp / "journal.log", tmp / "a-valider.md"
I.PLAN.write_text(PLAN_TXT, encoding="utf-8")

# --- lecture du plan : file, légendes, cases à cocher ---
plan = I.lire_plan(PLAN_TXT); leg = I.lire_legendes(PLAN_TXT)
assert [p["n"] for p in plan] == [1, 2, 3, 4, 5, 6, 7] and plan[0]["etat"] == "publié" and plan[0]["date"] == "2026-11-03" and plan[1]["fichier"] == "02-video.mp4" and plan[1]["etat"] == "à publier"
assert sorted(leg) == [1, 2, 3, 4, 5, 7] and leg[3].startswith("Exemple de page pour un plombier") and "réglé en une fois" in leg[4] and "acompte" not in leg[4]
coche = I.cocher(PLAN_TXT, 2, "2026-11-04")
assert "| 2 | 02-video.mp4 | publié | 2026-11-04 |" in coche and coche.replace("| 2 | 02-video.mp4 | publié | 2026-11-04 |", "| 2 | 02-video.mp4 | à publier | |") == PLAN_TXT   # seule la ligne 2 change
assert I.cocher(PLAN_TXT, 99, "2026-11-04") == PLAN_TXT

# --- règles : légende, fichier ---
assert I.legende_ok(leg[2]) == "" and I.legende_ok(leg[3]) == "" and I.legende_ok(leg[4]) == ""          # « prix réglé en une fois » (sans montant) décidé par Liam : accepté
assert "interdit" in I.legende_ok(leg[5]) and I.legende_ok("") != "" and I.legende_ok("x" * 2300) != ""      # promesse (« garanti », « numéro 1 »), vide, plus de 2200 caractères
assert I.legende_ok("Exemple de page. ★★★★★ avis clients") != "" and I.legende_ok("Exemple. 120 clients") != ""
assert I.fichier_ok(DOSSIER / "01-intro.png") == "" and I.fichier_ok(DOSSIER / "absent.png") != "" and I.fichier_ok(DOSSIER / "x.txt") != ""

# --- prochain post : le premier « à publier » EXACT, avec légende valide et fichier ; jamais une légende inventée ---
post, raisons = I.prochain_post(plan, leg, DOSSIER)
assert post["n"] == 2 and post["type"] == "reel" and post["legende"] == leg[2] and post["fichier"] == DOSSIER / "02-video.mp4"
plan2 = I.lire_plan(I.cocher(PLAN_TXT, 2, "2026-11-04")); post3, _ = I.prochain_post(plan2, leg, DOSSIER); assert post3["n"] == 3 and post3["type"] == "image"
plan3 = I.lire_plan(I.cocher(I.cocher(I.cocher(PLAN_TXT, 2, "d"), 3, "d"), 4, "d"))
none_, rs = I.prochain_post(plan3, leg, DOSSIER)
assert none_ is None and any("n° 5" in r and "interdit" in r for r in rs) and any("n° 6" in r and "légende" in r for r in rs) and any("n° 7" in r for r in rs), rs   # 5 : promesse ; 6 : pas de légende ; 7 : « plus tard »
assert I.file_restante(plan, leg, DOSSIER) == 3 and I.file_restante(plan3, leg, DOSSIER) == 0           # 2, 3, 4 publiables ; 5, 6, 7 non

# --- moment : une seule fois par jour, vers 12 h 30 (heure de Paris), fenêtre de 90 minutes ---
conf = {**I.DEFAUT}
assert conf["envoi_automatique"] is False and conf["heure_publication"] == "12:30" and conf["file_minimum"] == 3        # simulation par défaut
J = datetime(2026, 11, 4)
assert I.moment(J.replace(hour=12, minute=29), conf) == "trop_tot" and I.moment(J.replace(hour=12, minute=30), conf) == "ok" and I.moment(J.replace(hour=13, minute=59), conf) == "ok" and I.moment(J.replace(hour=14, minute=1), conf) == "trop_tard"

# --- erreurs de l'API : connexion perdue, vérification de sécurité, autre ---
E = lambda code, msg="", sub=0: {"error": {"code": code, "error_subcode": sub, "message": msg, "type": "OAuthException"}}
assert I.classer_erreur(400, E(190, "Error validating access token")) == "connexion perdue" and I.classer_erreur(401, {}) == "connexion perdue" and I.classer_erreur(400, E(102)) == "connexion perdue"
assert I.classer_erreur(400, E(368, "temporarily blocked")) == "vérification de sécurité" and I.classer_erreur(400, E(190, "", 459)) == "vérification de sécurité"
assert I.classer_erreur(400, E(1, "Please confirm your identity (security check)")) == "vérification de sécurité"
assert I.classer_erreur(500, E(2, "boom")) == "erreur" and I.classer_erreur(400, E(4, "rate limit")) == "erreur"

# --- API officielle : enchaînement des appels (faux transport, aucun réseau) ---
class Faux:
    def __init__(self, reponses): self.appels, self.reponses = [], list(reponses)
    def __call__(self, methode, chemin, params=None, fichier=None, entetes=None, url=None):
        self.appels.append((methode, chemin, dict(params or {}), fichier, url))
        r = self.reponses.pop(0)
        if isinstance(r, Exception): raise r
        return r
CONF_API = {**I.DEFAUT, "graph_version": "v99.0", "poll_essais": 3, "poll_pause_s": 0}
JET = {"access_token": "SECRET-NE-JAMAIS-AFFICHER", "ig_user_id": "111", "page_id": "222"}
img = {"n": 3, "type": "image", "fichier": DOSSIER / "03-plombier.png", "legende": leg[3]}
f = Faux([{"id": "ph1"}, {"images": [{"source": "https://cdn.fb/ph1.jpg"}]}, {"id": "ct1"}, {"status_code": "IN_PROGRESS"}, {"status_code": "FINISHED"}, {"id": "med1"}, {"permalink": "https://www.instagram.com/p/AbC/", "caption": leg[3], "timestamp": "2026-11-04T11:31:00+0000"}])
r = I.PublieurApi(CONF_API, JET, f, dormir=lambda s: None).publier(img, maintenant=datetime(2026, 11, 4, 12, 35))
assert r["id"] == "med1" and r["permalink"].endswith("/p/AbC/"), r
ch = [(m, c) for m, c, *_ in f.appels]
assert ch == [("POST", "222/photos"), ("GET", "ph1"), ("POST", "111/media"), ("GET", "ct1"), ("GET", "ct1"), ("POST", "111/media_publish"), ("GET", "med1")], ch
assert f.appels[0][2].get("published") == "false" and f.appels[0][3] == DOSSIER / "03-plombier.png"          # photo déposée NON publiée sur la Page : sert seulement d'adresse d'image
assert f.appels[2][2]["image_url"] == "https://cdn.fb/ph1.jpg" and f.appels[2][2]["caption"] == leg[3] and f.appels[5][2]["creation_id"] == "ct1"
assert all("SECRET" not in json.dumps(a[2]) for a in f.appels), "le jeton ne passe jamais dans les paramètres (en-tête seulement)"
vid = {"n": 2, "type": "reel", "fichier": DOSSIER / "02-video.mp4", "legende": leg[2]}
f = Faux([{"id": "ct2", "uri": "https://rupload.facebook.com/ig-api-upload/v99.0/ct2"}, {"success": True}, {"status_code": "FINISHED"}, {"id": "med2"}, {"permalink": "https://www.instagram.com/reel/XyZ/", "caption": leg[2], "timestamp": "2026-11-04T11:31:00+0000"}])
r = I.PublieurApi(CONF_API, JET, f, dormir=lambda s: None).publier(vid, maintenant=datetime(2026, 11, 4, 12, 35))
assert r["id"] == "med2" and f.appels[0][2]["media_type"] == "REELS" and f.appels[0][2]["upload_type"] == "resumable" and f.appels[1][4] == "https://rupload.facebook.com/ig-api-upload/v99.0/ct2" and f.appels[1][3] == DOSSIER / "02-video.mp4"
# échec de traitement, erreur HTTP, vérification qui ne correspond pas : toujours une ErreurInstagram classée
f = Faux([{"id": "ct2", "uri": "u"}, {"success": True}, {"status_code": "ERROR"}])
try: I.PublieurApi(CONF_API, JET, f, dormir=lambda s: None).publier(vid, maintenant=datetime(2026, 11, 4, 12, 35)); assert False
except I.ErreurInstagram as e: assert e.genre == "erreur"
f = Faux([I.ErreurHttp(400, E(190, "token expiré"))])
try: I.PublieurApi(CONF_API, JET, f, dormir=lambda s: None).publier(img, maintenant=datetime(2026, 11, 4, 12, 35)); assert False
except I.ErreurInstagram as e: assert e.genre == "connexion perdue" and "SECRET" not in str(e)
f = Faux([{"id": "ph1"}, {"images": [{"source": "u"}]}, {"id": "ct1"}, {"status_code": "FINISHED"}, {"id": "med1"}, {"permalink": "p", "caption": "AUTRE TEXTE", "timestamp": "2026-11-04T11:31:00+0000"}])
try: I.PublieurApi(CONF_API, JET, f, dormir=lambda s: None).publier(img, maintenant=datetime(2026, 11, 4, 12, 35)); assert False
except I.ErreurInstagram as e: assert e.genre == "erreur" and "vérification" in str(e)                      # publié mais le profil ne montre pas la bonne légende : arrêt et alerte
f = Faux([I.ErreurHttp(0, {})] * 3)
try: I.PublieurApi({**CONF_API, "poll_essais": 1}, {"access_token": "t", "ig_user_id": "1", "page_id": ""}, f, dormir=lambda s: None).publier(img, maintenant=datetime(2026, 11, 4, 12, 35)); assert False
except I.ErreurInstagram as e: assert e.genre in ("erreur", "connexion perdue")                             # Page absente : pas de photo déposable
assert I.jeton_lu(tmp / "absent.json") is None

# --- la journée : simulation par défaut ---
alertes = []; al = alertes.append
class Boom:
    appels = 0
    def publier(self, post, maintenant=None): Boom.appels += 1; raise AssertionError("ne doit pas être appelé")
J12 = datetime(2026, 11, 4, 12, 35)
r = I.cmd_jour(conf, False, J12, Boom(), al)
assert r["action"] == "simulation" and r["n"] == 2 and Boom.appels == 0 and I.PLAN.read_text(encoding="utf-8") == PLAN_TXT, r             # rien publié, plan intact
e = I.etat_lire(); assert e["simulations"]["2026-11-04"]["n"] == 2 and not e.get("publications")
assert I.cmd_jour(conf, False, J12 + timedelta(minutes=10), Boom(), al)["action"] == "rien" and len(I.etat_lire()["simulations"]) == 1   # une seule simulation par jour
assert I.cmd_jour(conf, False, J.replace(hour=12, minute=10), Boom(), al)["action"] == "attente"
jr = I.JOURNAL.read_text(encoding="utf-8"); assert "simulation" in jr and "n° 2" in jr and "SECRET" not in jr          # journal de chaque action
# à blanc : aucune écriture
avant = (I.PLAN.read_text(encoding="utf-8"), I.ETAT.read_text(encoding="utf-8"), I.JOURNAL.read_text(encoding="utf-8"))
r = I.cmd_jour(conf, True, J12 + timedelta(days=1), Boom(), al); assert r["action"] == "simulation"
assert (I.PLAN.read_text(encoding="utf-8"), I.ETAT.read_text(encoding="utf-8"), I.JOURNAL.read_text(encoding="utf-8")) == avant

# --- mode automatique : une publication par jour, case cochée avec la date ---
I.ETAT.unlink(); I.JOURNAL.unlink()
CONF_AUTO = {**conf, "envoi_automatique": True}
class Pub:
    def __init__(self): self.posts = []
    def publier(self, post, maintenant=None): self.posts.append(post["n"]); return {"id": f"m{post['n']}", "permalink": f"https://www.instagram.com/p/n{post['n']}/"}
pub = Pub()
r = I.cmd_jour(CONF_AUTO, False, J12, pub, al)
assert r["action"] == "publié" and r["n"] == 2 and pub.posts == [2], r
txt = I.PLAN.read_text(encoding="utf-8"); assert "| 2 | 02-video.mp4 | publié | 2026-11-04 |" in txt and "| 3 | 03-plombier.png | à publier | |" in txt
assert I.etat_lire()["publications"]["2026-11-04"]["n"] == 2
assert I.cmd_jour(CONF_AUTO, False, J12 + timedelta(minutes=20), pub, al)["action"] == "rien" and pub.posts == [2]       # jamais deux le même jour
assert I.cmd_jour(CONF_AUTO, False, J12 + timedelta(days=1), pub, al)["n"] == 3 and pub.posts == [2, 3]               # le lendemain : le suivant
# une publication déjà cochée aujourd'hui dans le plan (à la main, ou par l'ancienne tâche de Claude) : rien de plus
I.PLAN.write_text(I.cocher(txt, 4, "2026-11-06"), encoding="utf-8")
assert I.cmd_jour(CONF_AUTO, False, datetime(2026, 11, 6, 12, 40), pub, al)["action"] == "rien" and pub.posts == [2, 3]
I.PLAN.write_text(PLAN_TXT, encoding="utf-8"); I.ETAT.unlink()

# --- fenêtre manquée : pas de publication tardive, alerte une seule fois ---
alertes.clear(); pub = Pub()
r = I.cmd_jour(CONF_AUTO, False, J.replace(hour=15, minute=0), pub, al)
assert r["action"] == "manqué" and not pub.posts and len(alertes) == 1 and "manqu" in alertes[0].lower()
I.cmd_jour(CONF_AUTO, False, J.replace(hour=15, minute=30), pub, al); assert len(alertes) == 1                       # alerte une seule fois par jour
I.ETAT.unlink(); alertes.clear()

# --- arrêt immédiat avec alerte : connexion perdue, vérification de sécurité, erreur ---
for genre in ("connexion perdue", "vérification de sécurité", "erreur"):
    I.ETAT.unlink(missing_ok=True); alertes.clear(); I.PLAN.write_text(PLAN_TXT, encoding="utf-8")
    class Casse:
        appels = 0
        def publier(self, post, maintenant=None): Casse.appels += 1; raise I.ErreurInstagram(genre, "détail sans secret")
    r = I.cmd_jour(CONF_AUTO, False, J12, Casse(), al)
    assert r["action"] == "arrêt" and r["raison"] == genre and len(alertes) == 1 and genre in alertes[0] and "reprendre" in alertes[0], (genre, r, alertes)
    assert I.etat_lire()["suspendu"]["raison"] == genre and "| 2 | 02-video.mp4 | à publier | |" in I.PLAN.read_text(encoding="utf-8")     # rien coché
    r = I.cmd_jour(CONF_AUTO, False, J12 + timedelta(minutes=5), Casse(), al)
    assert r["action"] == "arrêt" and Casse.appels == 1 and len(alertes) == 1                                        # suspendu : plus aucun appel, pas de seconde alerte
    I.reprendre(); assert "suspendu" not in I.etat_lire()
# publié mais vérification du profil en échec : la ligne EST cochée (jamais de seconde publication), puis arrêt et alerte
I.ETAT.unlink(missing_ok=True); alertes.clear(); I.PLAN.write_text(PLAN_TXT, encoding="utf-8")
class Verif:
    def publier(self, post, maintenant=None): raise I.ErreurInstagram("erreur", "vérification du profil : légende différente", publie=True, resultat={"id": "m2", "permalink": "https://www.instagram.com/p/z/"})
r = I.cmd_jour(CONF_AUTO, False, J12, Verif(), al)
assert r["action"] == "arrêt" and "| 2 | 02-video.mp4 | publié | 2026-11-04 |" in I.PLAN.read_text(encoding="utf-8") and I.etat_lire()["publications"]["2026-11-04"]["id"] == "m2" and I.etat_lire()["suspendu"]["raison"] == "erreur" and len(alertes) == 1
I.reprendre()
# échec PENDANT la publication (délai dépassé, réseau) : on ne sait pas si le post est parti -> publication incertaine, rien coché, jamais rejoué tout seul
I.ETAT.unlink(missing_ok=True); alertes.clear(); I.PLAN.write_text(PLAN_TXT, encoding="utf-8")
class Pendant:
    def publier(self, post, maintenant=None): raise I.ErreurInstagram("erreur", "HTTP 0", incertain=True)
r = I.cmd_jour(CONF_AUTO, False, J12, Pendant(), al)
assert r["action"] == "arrêt" and r["raison"] == "publication incertaine" and I.etat_lire()["en_cours"]["n"] == 2 and "| 2 | 02-video.mp4 | à publier | |" in I.PLAN.read_text(encoding="utf-8") and len(alertes) == 1
assert I.cmd_jour(CONF_AUTO, False, J12 + timedelta(minutes=5), Pub(), al)["action"] == "arrêt"
I.reprendre()
# jeton absent en mode réel : connexion perdue, arrêt et alerte (jamais de mot de passe demandé)
I.ETAT.unlink(); alertes.clear(); I.PLAN.write_text(PLAN_TXT, encoding="utf-8")
r = I.cmd_jour(CONF_AUTO, False, J12, None, al, jeton=None)
assert r["action"] == "arrêt" and r["raison"] == "connexion perdue" and len(alertes) == 1 and "jeton" in alertes[0].lower()
# plantage entre la création et la publication : jamais de seconde publication automatique
I.ETAT.unlink(); alertes.clear(); e = I.etat_lire(); e["en_cours"] = {"jour": "2026-11-04", "n": 2, "etape": "media_publish"}; I.etat_ecrire(e)
pub = Pub(); r = I.cmd_jour(CONF_AUTO, False, J12, pub, al)
assert r["action"] == "arrêt" and r["raison"] == "publication incertaine" and not pub.posts and len(alertes) == 1
I.reprendre(); assert "en_cours" not in I.etat_lire()

# --- file vide : alerte une fois, jamais d'invention ---
I.ETAT.unlink(); alertes.clear(); I.PLAN.write_text(PLAN_TXT.replace("| à publier |", "| publié |"), encoding="utf-8")
pub = Pub(); r = I.cmd_jour(CONF_AUTO, False, J12, pub, al)
assert r["action"] == "file vide" and not pub.posts and len(alertes) == 1 and "file" in alertes[0].lower()
I.cmd_jour(CONF_AUTO, False, J12 + timedelta(minutes=10), pub, al); assert len(alertes) == 1
I.PLAN.write_text(PLAN_TXT, encoding="utf-8"); I.ETAT.unlink()

# --- visuels : cartes fabriquées quand la file passe sous 3 posts, à valider par Liam tant que le mode automatique est faux ---
captures = tmp / "captures"; captures.mkdir(); (captures / "coiffeur.png").write_bytes(b"c" * 100)
SOURCES = [{"cle": "coiffeur", "metier": "coiffeur", "titre": "Coiffeur", "nom_fictif": "Atelier Ciseaux", "capture": str(captures / "coiffeur.png"), "hashtags": "#coiffeur #siteweb #rouen"},
           {"cle": "fleuriste", "metier": "fleuriste", "titre": "Fleuriste", "nom_fictif": "Maison Pétale", "capture": str(captures / "absente.png"), "hashtags": "#fleuriste"}]
rendus = []
def rendre(source, sortie): rendus.append(source["cle"]); Path(sortie).write_bytes(b"png")
CONF_V = {**conf, "sources_cartes": SOURCES}
# le profil serveur (b2b.local.json « serveur »: true) interdit la fabrication de cartes (aucun navigateur) : ce test ne doit pas dépendre de la machine qui le lance
serveur_reel = I.M.serveur; I.M.serveur = lambda: True
assert I.cmd_visuels(CONF_V, False, rendre)["action"] == "serveur" and not rendus, "profil serveur : aucune carte fabriquée"
I.M.serveur = lambda: False
assert I.cmd_visuels(CONF_V, False, rendre)["action"] == "assez" and not rendus                                          # 3 posts publiables : rien à fabriquer
plan_bas = I.cocher(PLAN_TXT, 2, "2026-11-04"); I.PLAN.write_text(plan_bas, encoding="utf-8")                           # il reste 3 et 4 : 2 publiables (< 3)
r = I.cmd_visuels(CONF_V, False, rendre)
assert r["action"] == "proposé" and rendus == ["coiffeur"] and any("fleuriste" in m and "capture" in m for m in r["manques"]), r
av = I.A_VALIDER.read_text(encoding="utf-8")
assert "à valider" in av and "Exemple de page pour un coiffeur" in av and "Atelier Ciseaux" in av and "nom fictif" in av and "pas un site client" in av.lower()
assert I.PLAN.read_text(encoding="utf-8") == plan_bas                                                                    # tant que Liam n'a pas validé, la file n'est pas touchée
assert I.cmd_visuels(CONF_V, False, rendre)["action"] == "déjà proposé" and rendus == ["coiffeur"]                       # pas de doublon
assert I.integrer_valides(CONF_V, False) == []                                                                          # rien de validé
I.A_VALIDER.write_text(av.replace("**Statut : à valider**", "**Statut : validé**"), encoding="utf-8")
ajoutes = I.integrer_valides(CONF_V, False)
assert ajoutes == [8] and "| 8 | 08-coiffeur.png | à publier | |" in I.PLAN.read_text(encoding="utf-8") and 8 in I.lire_legendes(I.PLAN.read_text(encoding="utf-8")) and (DOSSIER / "08-coiffeur.png").exists()
assert I.legende_ok(I.lire_legendes(I.PLAN.read_text(encoding="utf-8"))[8]) == ""
# mode automatique : la carte est ajoutée sans attendre, avec les mêmes règles ; à blanc : rien d'écrit
I.PLAN.write_text(plan_bas, encoding="utf-8"); I.A_VALIDER.unlink(); (DOSSIER / "08-coiffeur.png").unlink(); rendus.clear()
r = I.cmd_visuels(CONF_V, True, rendre); assert r["action"] == "proposé" and not rendus and not I.A_VALIDER.exists() and I.PLAN.read_text(encoding="utf-8") == plan_bas
r = I.cmd_visuels({**CONF_V, "envoi_automatique": True}, False, rendre)
assert r["action"] == "ajouté" and "| 8 | 08-coiffeur.png | à publier | |" in I.PLAN.read_text(encoding="utf-8")

# --- boucle continue : arrêt de secours, verrou, Jarvis arrêté, une seule instance ---
I.PLAN.write_text(PLAN_TXT, encoding="utf-8"); I.ETAT.unlink(missing_ok=True); I.JOURNAL.unlink(missing_ok=True); alertes.clear()
horloge = [datetime(2026, 11, 4, 12, 31)]
def dormir(s): horloge[0] += timedelta(seconds=s)
I.ARRET.write_text("1", encoding="utf-8")
assert I.cmd_continu(CONF_AUTO, False, dormir=dormir, maintenant=lambda: horloge[0], publieur=Pub(), alerte=al) == "arrêt demandé" and not I.VERROU.exists() and not I.ARRET.exists()
pub = Pub()
assert I.cmd_continu(CONF_AUTO, False, dormir=dormir, maintenant=lambda: horloge[0], publieur=pub, alerte=al, vivant=lambda: False) == "Jarvis s'est arrêté" and not pub.posts
pub = Pub(); cycles = [0]
def vivant_deux_cycles(): cycles[0] += 1; return cycles[0] < 4
assert I.cmd_continu(CONF_AUTO, False, dormir=dormir, maintenant=lambda: horloge[0], publieur=pub, alerte=al, vivant=vivant_deux_cycles) == "Jarvis s'est arrêté" and pub.posts == [2]   # publie une fois, puis veille
I.VERROU.write_text(str(os.getpid()), encoding="utf-8"); assert I.boucle_active() and I.cmd_continu(CONF_AUTO, False, dormir=dormir, maintenant=lambda: horloge[0], publieur=Pub(), alerte=al) == "déjà lancée"; I.VERROU.unlink()
assert I.cmd_continu(CONF_AUTO, True, dormir=dormir, maintenant=lambda: horloge[0]) == "à blanc"                          # à blanc : rien lancé
# suspendu : la boucle s'arrête dès le premier cycle (aucune reprise automatique après une erreur)
e = I.etat_lire(); e["suspendu"] = {"raison": "erreur", "date": "2026-11-04"}; I.etat_ecrire(e)
assert I.cmd_continu(CONF_AUTO, False, dormir=dormir, maintenant=lambda: horloge[0], publieur=Pub(), alerte=al) == "suspendu (erreur)"
I.reprendre()

# --- réglages : fichier absent = valeurs par défaut sûres (simulation) ---
assert I.cfg()["envoi_automatique"] is False
I.CONFIG.write_text(json.dumps({"envoi_automatique": True, "_aide": "x"}), encoding="utf-8"); assert I.cfg()["envoi_automatique"] is True and "_aide" not in I.cfg()

print("OK : tous les tests de l'agent Instagram passent (dossier temporaire :", tmp, ")")
import shutil; shutil.rmtree(tmp, ignore_errors=True)
I.M.serveur = serveur_reel
