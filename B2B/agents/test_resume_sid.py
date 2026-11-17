#!/usr/bin/env python3
"""Tests silencieux de l'agent resume-sid : AUCUN réseau, aucun envoi, fichiers temporaires (rien dans le dépôt).  python agents\\test_resume_sid.py
Écrits AVANT le code (resume-sid.py). Règles de Liam : résumé du soir (appels Sid comptés sur une feuille Google lue en lecture seule + chiffre d'affaires Stripe du jour),
simulation par défaut (envoi_automatique=false dans le fichier versionné), aucun chiffre inventé quand une source manque, un seul résumé par jour."""
import contextlib, csv, importlib.util, io, json, os, socket, sys, tempfile, urllib.error, urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
os.environ.setdefault("JARVIS_TEST", "1")
ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))

def reseau(*a, **k): raise AssertionError("appel réseau interdit dans les tests")
urllib.request.urlopen = reseau; socket.create_connection = reseau

spec = importlib.util.spec_from_file_location("resume_sid", ICI / "resume-sid.py"); A = importlib.util.module_from_spec(spec); spec.loader.exec_module(A)

tmp = Path(tempfile.mkdtemp(prefix="resume-sid-test-"))
(tmp / "B2B" / "agents").mkdir(parents=True)
A.ICI, A.RACINE = tmp / "B2B" / "agents", tmp / "B2B"
A.CONFIG, A.ETAT, A.JOURNAL, A.APPELS_SID_ETAT = (A.ICI / "resume-sid-config.json", A.ICI / "resume-sid-etat.json", A.ICI / "resume-sid-journal.log", A.ICI / "appels-sid-etat.json")
ENV_JARVIS = tmp / ".env"      # RACINE.parent / ".env" (comme le vrai Jarvis\.env, un niveau au-dessus de B2B)
A.M.verifier = lambda *a, **k: (True, "")      # la garde « machine active » (machine.py) est testée dans test_machine.py


# --- doublures : aucun accès réseau, Google ni Discord réels -------------------------------------------------------
ALERTES, EXEC, STRIPE_APPELS = [], [], []
def faux_alerte(texte): ALERTES.append(texte); return True
def faux_executer(cmd): EXEC.append(cmd); return 0, ""
A.alerter_discord = faux_alerte; A.executer = faux_executer
A.maintenant_paris = lambda: datetime(2026, 11, 16)   # lundi (jour ouvré) : indépendant du jour réel d'exécution des tests


class FauxDrive:
    """Même interface que google_sheets.Drive (compte, lire_feuille) : une feuille = un texte CSV déjà en mémoire."""
    def __init__(s, compte="contact.lmsites@gmail.com"): s.compte_reel, s.feuilles, s.panne = compte, {}, False
    def compte(s): return s.compte_reel
    def lire_feuille(s, id_):
        if s.panne: raise A.ErreurAgent("panne simulée")
        if id_ not in s.feuilles: raise KeyError(id_)
        return s.feuilles[id_]
DRIVE = FauxDrive()
A.ouvrir_drive = lambda compte: DRIVE


ENTETE = ["#", "Nom", "Ville", "Téléphone", "Métier", "Créneau conseillé", "Constat vérifié", "Page d'exemple", "Appelé", "Répondu", "Rendez-vous pris", "Refus", "Remarque"]
def csv_sid(lignes):
    """Texte CSV (comme un export Google Sheets, séparateur « , ») : en-tête appels-sid + les lignes données (dict colonne -> valeur)."""
    tampon = io.StringIO(); w = csv.writer(tampon)
    w.writerow(ENTETE)
    for l in lignes: w.writerow([l.get(c, "") for c in ENTETE])
    return tampon.getvalue()


echecs = 0
def verifier(cond, msg):
    global echecs
    if cond: print("  OK    " + msg)
    else: print("  ECHEC " + msg); echecs += 1


def lancer(*argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
        try: code = A.main(list(argv))
        except SystemExit as e: code = e.code if isinstance(e.code, int) else 2
    return code, buf.getvalue()


def monde(config=None, appels_sid_etat=None, env=""):
    for f in (A.ETAT, A.JOURNAL): f.unlink(missing_ok=True)
    A.CONFIG.write_text(json.dumps(config or {}), encoding="utf-8")
    A.M.chemin_local(A.CONFIG).unlink(missing_ok=True)
    if appels_sid_etat is not None: A.APPELS_SID_ETAT.write_text(json.dumps(appels_sid_etat), encoding="utf-8")
    else: A.APPELS_SID_ETAT.unlink(missing_ok=True)
    ENV_JARVIS.write_text(env, encoding="utf-8")
    DRIVE.__init__(); ALERTES.clear(); EXEC.clear()


JOUR = "2026-11-09"

print("1. Réglages : simulation par défaut, heure de tâche valide")
monde()
c = A.cfg()
verifier(c["envoi_automatique"] is False, "envoi_automatique = false par défaut")
verifier(c["heure_tache"] == "19:00", "heure_tache = 19:00 par défaut")
monde(config={"heure_tache": "pas une heure"})
verifier(A.cfg()["heure_tache"] == "19:00", "heure_tache invalide dans le fichier : repli sur 19:00")

print("2. debut_jour_paris : minuit à Paris, hiver (UTC+1) et été (UTC+2)")
# zoneinfo (tzdata) n'est pas installé sur ce PC (comme prospection.heure_paris) : repli attendu, vérifié directement contre l'heure UTC connue, été et hiver.
attendu_hiver = int(datetime(2026, 11, 8, 23, 0, tzinfo=timezone.utc).timestamp())
verifier(A.debut_jour_paris(JOUR) == attendu_hiver, f"{JOUR} (hiver, UTC+1) : horodatage correct")
attendu_ete = int(datetime(2026, 6, 30, 22, 0, tzinfo=timezone.utc).timestamp())
verifier(A.debut_jour_paris("2026-07-01") == attendu_ete, "2026-07-01 (été, UTC+2) : horodatage correct")

print("3. stats_appels : aucune feuille, feuille absente, feuille lisible")
monde()
dispo, detail = A.stats_appels(A.cfg(), JOUR, DRIVE)
verifier(dispo is False and "aucune feuille" in detail, "pas d'état appels-sid : aucune feuille, pas un zéro")
monde(appels_sid_etat={"google": {JOUR: {}}})
dispo, detail = A.stats_appels(A.cfg(), JOUR, DRIVE)
verifier(dispo is False and "aucune feuille" in detail, "jour présent mais sans feuille (simulation d'appels-sid) : pas un zéro")
monde(appels_sid_etat={"google": {JOUR: {"feuille": "F1"}}})
DRIVE.feuilles["F1"] = csv_sid([
    {"Nom": "A", "Appelé": "x", "Répondu": "x", "Rendez-vous pris": "x"},
    {"Nom": "B", "Appelé": "x", "Refus": "x"},
    {"Nom": "C"},
])
dispo, detail = A.stats_appels(A.cfg(), JOUR, DRIVE)
verifier(dispo is True and detail == {"total": 3, "Appelé": 2, "Répondu": 1, "Rendez-vous pris": 1, "Refus": 1}, f"3 lignes comptées par en-tête : {detail}")
DRIVE.feuilles["F1"] = "Créneau,Entreprise,Métier,Ville,Téléphone,Détail fiche,Résultat,Note\n08 h,A,,,,,RDV pris,\n08 h 10,B,,,,,Refus,\n08 h 20,C,,,,,Pas de réponse,\n08 h 30,D,,,,,,\n"
dispo, detail = A.stats_appels(A.cfg(), JOUR, DRIVE)
verifier(dispo is True and detail["total"] == 4 and detail["Appelé"] == 3 and detail["resultats"]["RDV pris"] == 1 and detail["resultats"]["Pas de réponse"] == 1 and detail["autres"] == 1,
         f"tableur « Appels » (colonne Résultat, 14/11/2026) : {detail}")
DRIVE.feuilles["F1"] = "Créneau,Entreprise,Métier,Ville,Téléphone,Détail fiche,Résultat,Note\n" + "".join(f"08 h,E{k},,,,,{v},\n" for k, v in enumerate(A.RESULTATS)) + "09 h,Z,,,,,,\n"
dispo, detail = A.stats_appels(A.cfg(), JOUR, DRIVE)
verifier(dispo is True and list(detail["resultats"]) == ["Pas de réponse", "À rappeler", "RDV pris", "Non catégorique", "Je dois réfléchir", "Trop cher", "Déjà un site", "Pas le temps"]
         and all(n == 1 for n in detail["resultats"].values()) and detail["Appelé"] == 8 and detail["total"] == 9, "les 8 valeurs de Résultat, dans l'ordre, chacune comptée")
txt8 = A.message_resume(JOUR, True, detail, False, "clé absente")
verifier(all(f"{v} 1" in txt8 for v in A.RESULTATS) and "8 avec un résultat, 1 sans résultat" in txt8 and "E0" not in txt8, "résumé du soir : chaque valeur comptée, aucun nom d'entreprise")
verifier("RDV pris : 1 — à voir dans le tableur du jour" in txt8, "résumé du soir : les RDV pris sont signalés à part")

print("4. stats_appels : pannes sans jamais inventer de chiffre")
monde(appels_sid_etat={"google": {JOUR: {"feuille": "F2"}}})
DRIVE.feuilles["F2"] = "entete,sans,les,bonnes,colonnes\n1,2,3,4,5\n"
dispo, detail = A.stats_appels(A.cfg(), JOUR, DRIVE)
verifier(dispo is False and "colonnes" in detail, "colonnes attendues absentes : signalé, pas un zéro")
monde(appels_sid_etat={"google": {JOUR: {"feuille": "F1"}}})
DRIVE.feuilles["F1"] = csv_sid([{"Nom": "A", "Appelé": "x"}])
DRIVE.compte_reel = "un-autre-compte@example.invalid"
dispo, detail = A.stats_appels(A.cfg(), JOUR, DRIVE)
verifier(dispo is False and "autre compte" in detail, "jeton d'un autre compte Google : refusé, pas de lecture")
DRIVE.compte_reel = "contact.lmsites@gmail.com"; DRIVE.panne = True
dispo, detail = A.stats_appels(A.cfg(), JOUR, DRIVE)
verifier(dispo is False, "panne Drive : signalée, pas un zéro")
DRIVE.panne = False

print("5. stripe_jour : clé absente, clé refusée, paiements lus")
monde(env="")
dispo, detail = A.stripe_jour(JOUR)
verifier(dispo is False and "absente" in detail, "aucune clé Stripe dans .env : pas un chiffre inventé")
monde(env="STRIPE_RESTRICTED_KEY=rk_live_xxx\n")
dispo, detail = A.stripe_jour(JOUR)
verifier(dispo is False, "clé encore à « xxx » (exemple non rempli) : pas un chiffre inventé")
monde(env="STRIPE_RESTRICTED_KEY=rk_live_vraie\n")
def stripe_ok(cle, chemin):
    STRIPE_APPELS.append(chemin)
    return {"data": [
        {"paid": True, "status": "succeeded", "amount": 29700, "amount_refunded": 0, "currency": "eur"},
        {"paid": True, "status": "succeeded", "amount": 10000, "amount_refunded": 3000, "currency": "eur"},   # remboursé en partie : net 7000
        {"paid": True, "status": "succeeded", "amount": 500, "amount_refunded": 0, "currency": "usd"},
        {"paid": False, "status": "failed", "amount": 99999, "amount_refunded": 0, "currency": "eur"},        # échoué : jamais compté
    ], "has_more": False}
A.appel_stripe = stripe_ok
dispo, detail = A.stripe_jour(JOUR)
verifier(dispo is True and detail == {"montants": {"EUR": 36700, "USD": 500}, "paiements": 3, "partiel": False}, f"paiements réussis sommés par devise, remboursements déduits, échec ignoré : {detail}")
verifier(bool(STRIPE_APPELS) and "charges" in STRIPE_APPELS[0] and "created" in STRIPE_APPELS[0], "la clé n'est jamais dans le chemin, le filtre « created » si")
A.appel_stripe = lambda cle, chemin: (_ for _ in ()).throw(urllib.error.HTTPError(chemin, 401, "refusé", {}, None))
dispo, detail = A.stripe_jour(JOUR)
verifier(dispo is False and "refusée" in detail, "HTTP 401 : clé refusée, message clair, pas un chiffre inventé")
A.appel_stripe = lambda cle, chemin: (_ for _ in ()).throw(ConnectionError())
dispo, detail = A.stripe_jour(JOUR)
verifier(dispo is False, "Stripe injoignable : signalé, pas un chiffre inventé")

print("6. message_resume : les deux sources, disponibles ou pas")
txt = A.message_resume(JOUR, True, {"total": 3, "Appelé": 2, "Répondu": 1, "Rendez-vous pris": 1, "Refus": 0}, True, {"montants": {"EUR": 29700}, "paiements": 1, "partiel": False})
verifier("2 appelée" in txt and "1 répondu" in txt and "1 rendez-vous pris" in txt and "297" in txt and "1 paiement" in txt, f"les deux sources dans le message : {txt!r}")
txt2 = A.message_resume(JOUR, False, "pas de feuille", False, "clé absente")
verifier("pas de feuille" in txt2 and "clé absente" in txt2, "aucune source disponible : les deux raisons apparaissent, aucun nombre inventé")

print("7. cmd_resume : simulation, réel, --a-blanc, un seul résumé par jour")
A.appel_stripe = lambda cle, chemin: {"data": [], "has_more": False}
monde(config={"envoi_automatique": False}, appels_sid_etat={"google": {JOUR: {"feuille": "F1"}}}, env="")
DRIVE.feuilles["F1"] = csv_sid([{"Nom": "A", "Appelé": "x"}])
code, sortie = lancer("resume", "--jour", JOUR)
verifier(code == 0 and "simulation" in sortie.lower() and not ALERTES, "simulation (envoi_automatique=false) : affiché, rien sur Discord")
verifier(A.etat_lire()["envoyes"].get(JOUR) is True, "l'état note le résumé du jour même en simulation")
code, sortie = lancer("resume", "--jour", JOUR)
verifier(code == 0 and "déjà envoyé" in sortie, "même jour, second lancement : rien de plus (idempotent)")
code, sortie = lancer("resume", "--jour", JOUR, "--a-blanc")
verifier(code == 0 and "à blanc" in sortie, "--a-blanc : affiche quand même, même si déjà envoyé")

monde(config={"envoi_automatique": True}, appels_sid_etat={"google": {JOUR: {"feuille": "F1"}}}, env="")
code, sortie = lancer("resume", "--jour", JOUR)
verifier(code == 0 and len(ALERTES) == 1 and "posté sur Discord" in sortie, "envoi_automatique=true : posté dans le salon habituel")
A.alerter_discord = lambda texte: False
monde(config={"envoi_automatique": True}, appels_sid_etat={"google": {JOUR: {"feuille": "F1"}}}, env="")
code, sortie = lancer("resume", "--jour", JOUR)
verifier(code == 0 and "non envoyé" in sortie, "Discord injoignable : annoncé, l'agent ne plante pas")
A.alerter_discord = faux_alerte

print("7 bis. jour hors planning (week-end) : aucune lecture, aucun envoi, comme appels-sid.py")
reel_maintenant_paris = A.maintenant_paris
monde(config={"envoi_automatique": True}, appels_sid_etat={"google": {JOUR: {"feuille": "F1"}}}, env="")
for nom, jour_simule in (("samedi", datetime(2026, 11, 14)), ("dimanche", datetime(2026, 11, 15))):
    A.maintenant_paris = lambda j=jour_simule: j
    code, sortie = lancer("resume", "--jour", JOUR)
    verifier(code == 0 and "hors planning" in sortie and nom in sortie and not ALERTES, f"{nom} : jour hors planning, rien envoyé")
    verifier(JOUR not in A.etat_lire()["envoyes"], f"{nom} : rien n'est marqué envoyé pour {JOUR}")
A.maintenant_paris = reel_maintenant_paris

print("8. resume sans --jour : le jour d'aujourd'hui")
monde(config={"envoi_automatique": False})
code, sortie = lancer("resume")
verifier(code == 0 and date.today().isoformat() in A.etat_lire()["envoyes"], "sans --jour : la date d'aujourd'hui est utilisée")

print("9. etat")
monde(config={"envoi_automatique": False})
code, sortie = lancer("etat")
verifier(code == 0 and "Aucun résumé" in sortie, "etat, rien envoyé : le dit")
lancer("resume", "--jour", JOUR)
code, sortie = lancer("etat")
verifier(code == 0 and JOUR in sortie, "etat, après un résumé : la date apparaît")

print("10. installer-tache / retirer-tache : rien sans --oui, commande correcte")
monde(config={"heure_tache": "19:30"})
code, sortie = lancer("installer-tache")
verifier(code == 0 and not EXEC and "resume-sid.py" in sortie and "resume" in sortie and "Jarvis-ResumeSid" in sortie, "sans --oui : commande affichée seulement, rien exécuté")
code, sortie = lancer("installer-tache", "--oui")
verifier(code == 0 and len(EXEC) == 1 and "19:30" in EXEC[0] and "Jarvis-ResumeSid" in EXEC[0] and "IgnoreNew" in EXEC[0] and "StartWhenAvailable" in EXEC[0], "--oui : tâche installée à la bonne heure, rattrapage, une seule instance")
code, sortie = lancer("retirer-tache", "--oui")
verifier(code == 0 and len(EXEC) == 2 and "Unregister-ScheduledTask" in EXEC[1] and "Jarvis-ResumeSid" in EXEC[1], "retirer-tache --oui : désinstalle la bonne tâche")

print("11. Toutes les feuilles « Appels Sid » modifiées aujourd'hui (17/11/2026 : Sid avait noté ses appels dans la feuille de la veille)")
class DriveSid(FauxDrive):
    """Dossier de Sid : (id, nom, modifiedTime UTC) + contenu ; lecture seule."""
    def __init__(s, feuilles): super().__init__(); s.liste = feuilles
    def lister_feuilles_modifiees(s, parent): return [(i, n, m) for i, (n, m, _) in s.liste.items()] if parent == "DSID" else []
    def lire_feuille_csv(s, i): return s.liste[i][2]
COL = ["Créneau", "Entreprise", "Métier", "Ville", "Téléphone", "Détail fiche", "Résultat", "Note"]
def feuille(*res):
    t = io.StringIO(); w = csv.writer(t); w.writerow(COL)
    for i, (r, n) in enumerate(res): w.writerow(["9 h", f"Entreprise {i}", "Coiffeur", "Caen", "02 31 00 00 0%d" % i, "", r, n])
    return t.getvalue()
cfg_sid = Path(tempfile.mkdtemp(prefix="resume-sid-cfg-")) / "appels-sid-config.json"; cfg_sid.write_text(json.dumps({"dossier_sid_id": "DSID"}), encoding="utf-8")
av_cfg = A.APPELS_SID_CONFIG; A.APPELS_SID_CONFIG = cfg_sid
try:
    J = "2026-11-17"
    d = DriveSid({"a": ("Appels Sid 2026-11-16", "2026-11-17T17:37:27.472Z", feuille(("À rappeler", "intéressée, rappeler quand dispo"), ("Non catégorique", ""), ("Pas de réponse", ""), ("", ""))),
                  "b": ("Appels Sid 2026-11-17", "2026-11-17T06:38:59.418Z", feuille(("", ""), ("", ""))),
                  "c": ("Appels Sid 2026-11-13", "2026-11-14T08:00:00Z", feuille(("RDV pris", ""))),            # modifiée un autre jour : pas comptée
                  "d": ("Appels Sid 2026-11-12", "2026-11-16T23:30:00Z", feuille(("RDV pris", ""))),            # 23 h 30 UTC = 00 h 30 le 17 à Paris : comptée
                  "e": ("Budget", "2026-11-17T10:00:00Z", feuille(("RDV pris", "")))})                        # autre fichier : jamais lu
    dispo, det = A.stats_appels(A.cfg(), J, d)
    verifier(dispo and det["Appelé"] == 4 and det["resultats"]["À rappeler"] == 1 and det["resultats"]["RDV pris"] == 1 and det["resultats"]["Non catégorique"] == 1,
             "résultats de toutes les feuilles modifiées aujourd'hui (heure de Paris), pas seulement celle du jour ; autres jours et autres fichiers ignorés")
    msg = A.message_resume(J, dispo, det, False, "test")
    verifier("Attention : la feuille du jour (Appels Sid 2026-11-17) est vide" in msg and "Appels Sid 2026-11-16" in msg, "feuille du jour vide mais ancienne remplie : écrit clairement")
    verifier("À rappeler : Entreprise 0" in msg and "rappeler quand dispo" in msg, "les À rappeler sont listés avec leur Note")
    verifier("02 31" not in msg, "jamais de numéro dans le résumé")
    d2 = DriveSid({"b": ("Appels Sid 2026-11-17", "2026-11-17T18:00:00Z", feuille(("Pas de réponse", ""), ("", "")))})
    dispo, det = A.stats_appels(A.cfg(), J, d2); msg = A.message_resume(J, dispo, det, False, "test")
    verifier(det["Appelé"] == 1 and "Attention" not in msg, "feuille du jour remplie : aucun avertissement")
finally: A.APPELS_SID_CONFIG = av_cfg

print()
if echecs: print(f"{echecs} ÉCHEC(S)"); sys.exit(1)
print("OK : tous les tests de l'agent resume-sid passent")
