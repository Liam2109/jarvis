#!/usr/bin/env python3
"""Tests silencieux de l'agent stripe-alerte : AUCUN réseau, aucun envoi, fichiers temporaires (rien dans le dépôt).  python agents\\test_stripe_alerte.py
Écrits AVANT le code (stripe-alerte.py). Règles de Liam : simulation par défaut (envoi_automatique=false dans le fichier versionné), aucune action sur Stripe (lecture seule),
premier passage = point de départ fixé SANS alerter sur l'historique, jamais deux fois le même paiement, aucune donnée personnelle dans le message Discord."""
import contextlib, importlib.util, io, json, os, socket, sys, tempfile, urllib.error, urllib.request
from pathlib import Path
os.environ.setdefault("JARVIS_TEST", "1")
ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))

def reseau(*a, **k): raise AssertionError("appel réseau interdit dans les tests")
urllib.request.urlopen = reseau; socket.create_connection = reseau

spec = importlib.util.spec_from_file_location("stripe_alerte", ICI / "stripe-alerte.py"); A = importlib.util.module_from_spec(spec); spec.loader.exec_module(A)

tmp = Path(tempfile.mkdtemp(prefix="stripe-alerte-test-"))
(tmp / "B2B" / "agents").mkdir(parents=True)
A.ICI, A.RACINE = tmp / "B2B" / "agents", tmp / "B2B"
A.CONFIG, A.ETAT, A.JOURNAL = A.ICI / "stripe-alerte-config.json", A.ICI / "stripe-alerte-etat.json", A.ICI / "stripe-alerte-journal.log"
ENV_JARVIS = tmp / ".env"      # RACINE.parent / ".env" (comme le vrai Jarvis\.env, un niveau au-dessus de B2B)
A.M.verifier = lambda *a, **k: (True, "")      # la garde « machine active » (machine.py) est testée dans test_machine.py


ALERTES, EXEC = [], []
def faux_alerte(texte): ALERTES.append(texte); return True
def faux_executer(cmd): EXEC.append(cmd); return 0, ""
A.alerter_discord = faux_alerte; A.executer = faux_executer


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


def monde(config=None, env="STRIPE_RESTRICTED_KEY=rk_live_vraie\n"):
    for f in (A.ETAT, A.JOURNAL): f.unlink(missing_ok=True)
    A.CONFIG.write_text(json.dumps(config or {}), encoding="utf-8")
    A.M.chemin_local(A.CONFIG).unlink(missing_ok=True)
    ENV_JARVIS.write_text(env, encoding="utf-8")
    ALERTES.clear(); EXEC.clear()


def charge(id_, created, amount=29700, currency="eur", paid=True, status="succeeded", description=""):
    return {"id": id_, "created": created, "amount": amount, "amount_refunded": 0, "currency": currency, "paid": paid, "status": status, "description": description}


print("1. Réglages : simulation par défaut, intervalle valide")
monde()
c = A.cfg()
verifier(c["envoi_automatique"] is False, "envoi_automatique = false par défaut")
verifier(c["intervalle_minutes"] == 5, "intervalle_minutes = 5 par défaut")
monde(config={"intervalle_minutes": "pas un nombre"})
verifier(A.cfg()["intervalle_minutes"] == 5, "intervalle_minutes invalide : repli sur 5")
monde(config={"intervalle_minutes": 15})
verifier(A.cfg()["intervalle_minutes"] == 15, "intervalle_minutes réglé à 15 : respecté")

print("2. message_paiement : montant, devise, description courte, jamais de donnée personnelle")
txt = A.message_paiement(charge("ch_1", 1000, amount=29700, currency="eur", description="Acompte site complet"))
verifier(txt == "Nouveau paiement Stripe : 297 euros (Acompte site complet)", f"message correct : {txt!r}")
txt2 = A.message_paiement(charge("ch_2", 1000, amount=500, currency="usd", description=""))
verifier(txt2 == "Nouveau paiement Stripe : 5 dollars", "sans description : pas de parenthèses vides")
long_desc = "x" * 200
txt3 = A.message_paiement(charge("ch_3", 1000, description=long_desc))
verifier(len(txt3) < len(long_desc) + 40, "description longue : coupée (pas de message démesuré)")

print("3. cmd_verifier : clé absente, rien à vérifier, rien écrit")
monde(env="")
code, sortie = lancer("verifier")
verifier(code == 0 and "absente" in sortie and A.etat_lire()["dernier_ts"] == 0, "clé Stripe absente : signalé, rien écrit")

print("4. cmd_verifier : premier passage, aucune alerte sur l'historique")
monde()
A.appel_stripe = lambda cle, chemin: {"data": [charge("ch_a", 1000), charge("ch_b", 2000)]}
code, sortie = lancer("verifier")
verifier(code == 0 and not ALERTES and "Premier passage" in sortie, "premier passage : aucune alerte")
etat = A.etat_lire()
verifier(etat["dernier_ts"] == 2000 and set(etat["vus"]) == {"ch_a", "ch_b"}, f"point de départ fixé au plus récent, les deux mémorisés : {etat}")
verifier("premier passage" in A.JOURNAL.read_text(encoding="utf-8"), "journalisé")

print("5. cmd_verifier : --a-blanc au premier passage n'écrit rien")
monde()
A.appel_stripe = lambda cle, chemin: {"data": [charge("ch_a", 1000)]}
code, sortie = lancer("verifier", "--a-blanc")
verifier(code == 0 and "à blanc" in sortie and A.etat_lire()["dernier_ts"] == 0, "--a-blanc : affiche, n'écrit rien")

print("6. cmd_verifier : nouveaux paiements alertés un par un, jamais deux fois, non réussis ignorés")
monde(config={"envoi_automatique": False})
A.ETAT.write_text(json.dumps({"dernier_ts": 1000, "vus": {"ch_a": True}}), encoding="utf-8")
A.appel_stripe = lambda cle, chemin: {"data": [
    charge("ch_a", 1000),                                   # déjà vu (borne « gte ») : jamais une seconde alerte
    charge("ch_b", 1500, amount=10000, description="Site vitrine"),
    charge("ch_c", 2000, paid=False, status="failed"),       # échoué : jamais alerté
    charge("ch_d", 2500, amount=5000),
]}
code, sortie = lancer("verifier")
verifier(code == 0 and not ALERTES and sortie.count("Nouveau paiement Stripe") == 2, "simulation : affiché pour les 2 nouveaux paiements réussis, rien sur Discord")
verifier("Site vitrine" in sortie and "ch_c" not in sortie, "contenu correct, le paiement échoué n'apparaît pas")
etat = A.etat_lire()
verifier(etat["dernier_ts"] == 2500 and {"ch_a", "ch_b", "ch_c", "ch_d"} <= set(etat["vus"]), f"tous mémorisés (même l'échoué, pour ne pas le relire), dernier_ts avancé : {etat}")
code, sortie = lancer("verifier")
verifier(code == 0 and "Aucun nouveau paiement" in sortie, "relancé tout de suite : plus rien de nouveau")

print("7. cmd_verifier : envoi_automatique=true -> posté sur Discord ; Discord injoignable -> annoncé, pas de panne")
monde(config={"envoi_automatique": True})
A.ETAT.write_text(json.dumps({"dernier_ts": 1000, "vus": {}}), encoding="utf-8")
A.appel_stripe = lambda cle, chemin: {"data": [charge("ch_e", 1500)]}
code, sortie = lancer("verifier")
verifier(code == 0 and len(ALERTES) == 1 and "posté sur Discord" in sortie, "envoi_automatique=true : posté")
A.alerter_discord = lambda texte: False
monde(config={"envoi_automatique": True})
A.ETAT.write_text(json.dumps({"dernier_ts": 1000, "vus": {}}), encoding="utf-8")
A.appel_stripe = lambda cle, chemin: {"data": [charge("ch_f", 1500)]}
code, sortie = lancer("verifier")
verifier(code == 0 and "non envoyé" in sortie, "Discord injoignable : annoncé, l'agent ne plante pas")
A.alerter_discord = faux_alerte

print("8. cmd_verifier : clé refusée (HTTP 401) et Stripe injoignable, rien n'est inventé")
monde()
A.ETAT.write_text(json.dumps({"dernier_ts": 1000, "vus": {}}), encoding="utf-8")
A.appel_stripe = lambda cle, chemin: (_ for _ in ()).throw(urllib.error.HTTPError(chemin, 401, "refusé", {}, None))
code, sortie = lancer("verifier")
verifier(code == 2 and "refusée" in sortie and A.etat_lire()["dernier_ts"] == 1000, "clé refusée : code 2, état inchangé")
A.appel_stripe = lambda cle, chemin: (_ for _ in ()).throw(ConnectionError())
code, sortie = lancer("verifier")
verifier(code == 2 and A.etat_lire()["dernier_ts"] == 1000, "Stripe injoignable : code 2, état inchangé")

print("9. mémoire bornée des identifiants vus")
monde()
A.ETAT.write_text(json.dumps({"dernier_ts": 1000, "vus": {f"ch_old_{i}": True for i in range(A.VUS_MAX)}}), encoding="utf-8")
A.appel_stripe = lambda cle, chemin: {"data": [charge("ch_new", 1500)]}
lancer("verifier")
verifier(len(A.etat_lire()["vus"]) <= A.VUS_GARDES + 1, "au-delà de VUS_MAX : la mémoire est bornée (les plus anciens sont oubliés)")

print("10. etat")
monde()
code, sortie = lancer("etat")
verifier(code == 0 and "Aucune vérification" in sortie, "etat, rien vérifié : le dit")
A.appel_stripe = lambda cle, chemin: {"data": [charge("ch_g", 1000)]}
lancer("verifier")
code, sortie = lancer("etat")
verifier(code == 0 and "1 identifiant" in sortie, "etat, après un premier passage : le compte apparaît")

print("11. installer-tache / retirer-tache : rien sans --oui, commande correcte (répétition)")
monde(config={"intervalle_minutes": 10})
code, sortie = lancer("installer-tache")
verifier(code == 0 and not EXEC and "stripe-alerte.py" in sortie and "verifier" in sortie and "Jarvis-StripeAlerte" in sortie, "sans --oui : commande affichée seulement, rien exécuté")
code, sortie = lancer("installer-tache", "--oui")
verifier(code == 0 and len(EXEC) == 1 and "RepetitionInterval" in EXEC[0] and "10" in EXEC[0] and "Jarvis-StripeAlerte" in EXEC[0], "--oui : tâche installée, répétée toutes les 10 minutes")
code, sortie = lancer("retirer-tache", "--oui")
verifier(code == 0 and len(EXEC) == 2 and "Unregister-ScheduledTask" in EXEC[1] and "Jarvis-StripeAlerte" in EXEC[1], "retirer-tache --oui : désinstalle la bonne tâche")

print()
if echecs: print(f"{echecs} ÉCHEC(S)"); sys.exit(1)
print("OK : tous les tests de l'agent stripe-alerte passent")
