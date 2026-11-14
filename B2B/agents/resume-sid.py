#!/usr/bin/env python3
"""Agent resume-sid (LM MULTI-SERVICES) : résumé Discord en fin de journée (19 h par défaut) de l'activité de Sid et du chiffre d'affaires Stripe du jour. Aucun envoi au prospect ni à Sid,
aucune écriture dans la feuille Google (lecture seule) ; même modèle que les autres agents B2B : réglages (resume-sid-config.json), état (resume-sid-etat.json), journal, tests écrits avant le code.
`envoi_automatique: false` (défaut) = SIMULATION : rien sur Discord, la console (et le journal) disent ce qui serait envoyé.

  python agents\\resume-sid.py resume [--jour AAAA-MM-JJ] [--a-blanc]      calcule et poste (ou affiche) le résumé du jour ; c'est ce que lance la tâche planifiée de 19 h
  python agents\\resume-sid.py etat                                       dernier résumé envoyé (ou simulé)
  python agents\\resume-sid.py installer-tache | retirer-tache [--oui]    tâche planifiée Windows (heure_tache, 19:00 par défaut) ; sans --oui, affiche seulement la commande

Appels : nombre de lignes par valeur de la colonne Résultat (8 valeurs, tableur du 14/11/2026 ; anciennes feuilles : « Appelé » / « Répondu » / « Rendez-vous pris » / « Refus » coché) sur la feuille Google du jour créée par appels-sid.py (agents\\appels-sid-etat.json ›
google › <jour> › feuille, lue en lecture seule). Aucune feuille ce jour-là (simulation, jour hors planning, pas encore sourcé) : annoncé sans chiffre inventé.
Chiffre d'affaires : paiements Stripe réussis depuis minuit (Europe/Paris) ce jour-là, clé restreinte lue dans Jarvis\\.env (STRIPE_RESTRICTED_KEY), jamais affichée ;
clé absente ou refusée : annoncé sans chiffre inventé. Aucune donnée personnelle (nom, e-mail, numéro) dans le message Discord."""
import argparse, csv, io, json, os, re, subprocess, sys, urllib.error, urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ICI = Path(__file__).resolve().parent
RACINE = ICI.parent
sys.path.insert(0, str(ICI))
import machine as M   # config locale (resume-sid-config.local.json) et machine active (b2b.local.json)
import prospection as P, reponses as RP   # P.acces_discord / P.discord : salon Discord habituel ; RP.lire_env : lecture de Jarvis\.env

CONFIG, ETAT, JOURNAL = ICI / "resume-sid-config.json", ICI / "resume-sid-etat.json", ICI / "resume-sid-journal.log"
APPELS_SID_ETAT = ICI / "appels-sid-etat.json"
DEFAUT = {"envoi_automatique": False, "heure_tache": "19:00", "compte_google": "contact.lmsites@gmail.com"}
COLONNES_SUIVIES = ["Appelé", "Répondu", "Rendez-vous pris", "Refus"]   # anciennes feuilles (cases à cocher)
RESULTATS = ["Pas de réponse", "À rappeler", "RDV pris", "Non catégorique", "Je dois réfléchir", "Trop cher", "Déjà un site", "Pas le temps"]   # colonne Résultat du tableur « Appels » (= appels-sid.RESULTATS)
NOMS_DEVISE = {"EUR": "euros", "USD": "dollars", "GBP": "livres"}
TACHE = "Jarvis-ResumeSid"


class ErreurAgent(Exception):
    """Problème signalé à Liam (message clair, code de sortie 2) : l'agent s'arrête sans rien écrire de plus."""


# --- points d'accès au monde extérieur (remplacés par des doublures dans les tests) ---------------------------------
def ouvrir_drive(compte):
    import google_sheets as GS
    return GS.ouvrir(compte)


def _stripe_base():
    """https://api.stripe.com/v1/ (ou un serveur de test local, UNIQUEMENT 127.0.0.1, posé par les tests)."""
    base = os.environ.get("JARVIS_TEST_STRIPE_BASE", "")
    return base if re.match(r"^http://127\.0\.0\.1:\d+/", base) else "https://api.stripe.com/v1/"


def appel_stripe(cle, chemin):
    """GET Stripe (lecture seule). Remplacée par une doublure dans les tests : aucun réseau réel."""
    req = urllib.request.Request(_stripe_base() + chemin, headers={"Authorization": "Bearer " + cle})
    with urllib.request.urlopen(req, timeout=20) as r: return json.loads(r.read())


# --- réglages, état, journal ------------------------------------------------------------------------------------
def cfg():
    c = json.loads(json.dumps(DEFAUT))
    try:
        if CONFIG.exists(): c.update({k: v for k, v in json.loads(CONFIG.read_text(encoding="utf-8-sig")).items() if not k.startswith("_")})
    except (OSError, ValueError): raise ErreurAgent(f"réglages illisibles : {CONFIG.name}")
    try: M.surcharge_locale(CONFIG, c)
    except M.ErreurLocale as e: raise ErreurAgent(str(e))
    c["envoi_automatique"] = c.get("envoi_automatique") is True
    if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", str(c.get("heure_tache"))): c["heure_tache"] = DEFAUT["heure_tache"]
    c["compte_google"] = str(c.get("compte_google") or DEFAUT["compte_google"]).strip()
    return c


def etat_lire():
    try: e = json.loads(ETAT.read_text(encoding="utf-8")) if ETAT.exists() else {}
    except (OSError, ValueError): raise ErreurAgent(f"état illisible ({ETAT.name}) : rien n'est écrit ; corrigez ou supprimez le fichier à la main")
    if not isinstance(e, dict): raise ErreurAgent(f"état illisible ({ETAT.name}) : rien n'est écrit")
    e.setdefault("envoyes", {})
    return e


def etat_ecrire(e): ETAT.write_text(json.dumps(e, ensure_ascii=False, indent=1), encoding="utf-8")


def journaliser(action, detail="", a_blanc=False):
    if a_blanc: return
    with open(JOURNAL, "a", encoding="utf-8") as f: f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} | {action} | {detail}\n")


# --- source 1 : les cases cochées par Sid sur la feuille Google du jour --------------------------------------------
def stats_appels(conf, jour, drive=None):
    """(dispo, détail) : nombre d'entreprises Appelé / Répondu / Rendez-vous pris / Refus sur la feuille du jour (créée par appels-sid.py), ou (False, raison) sans chiffre inventé."""
    try:
        e = json.loads(APPELS_SID_ETAT.read_text(encoding="utf-8")) if APPELS_SID_ETAT.exists() else {}
    except (OSError, ValueError):
        return False, "état d'appels-sid illisible"
    feuille = ((e.get("google") or {}).get(jour) or {}).get("feuille")
    if not feuille: return False, f"aucune feuille Google pour le {jour} (simulation, jour hors planning, ou passage pas encore fait)"
    try:
        drive = drive or ouvrir_drive(conf["compte_google"])
        if (drive.compte() or "").lower() != conf["compte_google"].lower(): return False, "jeton Google d'un autre compte : relancez appels-sid.py google-autoriser"
        brut = drive.lire_feuille(feuille)
    except Exception as ex:
        return False, f"feuille du {jour} illisible ({type(ex).__name__})"
    lignes = list(csv.reader(io.StringIO(brut)))
    if not lignes: return False, f"feuille du {jour} vide"
    entete = lignes[0]
    if "Résultat" in entete:   # tableur « Appels AAAA-MM-JJ » (14/11/2026) : une liste Résultat (RESULTATS, 8 valeurs) au lieu des cases ; chaque valeur est comptée
        i = entete.index("Résultat"); r = [(l[i].strip() if i < len(l) else "") for l in lignes[1:]]
        return True, {"total": len(r), "Appelé": sum(1 for v in r if v), "resultats": {v: r.count(v) for v in RESULTATS},
                      "autres": sum(1 for v in r if v and v not in RESULTATS)}
    try: idx = {c: entete.index(c) for c in COLONNES_SUIVIES}
    except ValueError: return False, f"feuille du {jour} : colonnes inattendues"
    compte = {c: 0 for c in COLONNES_SUIVIES}
    for l in lignes[1:]:
        for c, i in idx.items():
            if i < len(l) and l[i].strip(): compte[c] += 1
    return True, {"total": len(lignes) - 1, **compte}


# --- source 2 : le chiffre d'affaires Stripe du jour ----------------------------------------------------------------
def debut_jour_paris(jour):
    """Horodatage Unix (UTC) du début (00:00) du jour AAAA-MM-JJ à Paris, sans dépendre de la base de fuseaux de Windows."""
    an, mois, j = (int(x) for x in jour.split("-"))
    try:
        from zoneinfo import ZoneInfo
        return int(datetime(an, mois, j, tzinfo=ZoneInfo("Europe/Paris")).timestamp())
    except Exception:
        avance = 2 if 3 <= mois <= 10 else 1   # repli : heure d'été approx. (mars-octobre = UTC+2, sinon UTC+1)
        return int((datetime(an, mois, j, tzinfo=timezone.utc) - timedelta(hours=avance)).timestamp())


def stripe_jour(jour):
    """(dispo, détail) : montants encaissés (paiements réussis moins remboursements, par devise) depuis minuit (Paris) ce jour-là, ou (False, raison) sans chiffre inventé."""
    env = RP.lire_env(RACINE.parent / ".env"); cle = env.get("STRIPE_RESTRICTED_KEY", "").strip()
    if not cle or cle.endswith("_xxx") or cle == "xxx": return False, "clé Stripe absente de Jarvis\\.env (STRIPE_RESTRICTED_KEY)"
    try:
        r = appel_stripe(cle, f"charges?limit=100&created[gte]={debut_jour_paris(jour)}")
    except urllib.error.HTTPError as ex:
        return False, "clé Stripe refusée ou permission de lecture manquante" if ex.code in (401, 403) else f"Stripe a répondu HTTP {ex.code}"
    except Exception as ex:
        return False, f"Stripe injoignable ({type(ex).__name__})"
    montants, n = {}, 0
    for c in r.get("data") or []:
        if c.get("paid") and c.get("status") == "succeeded":
            dev = str(c.get("currency") or "").upper(); net = int(c.get("amount") or 0) - int(c.get("amount_refunded") or 0)
            montants[dev] = montants.get(dev, 0) + net; n += 1
    return True, {"montants": montants, "paiements": n, "partiel": bool(r.get("has_more"))}


# --- message et envoi ------------------------------------------------------------------------------------------
def _montants_texte(montants):
    parts = []
    for dev in sorted(montants):
        v = montants[dev] / 100; txt = f"{v:.2f}"
        if txt.endswith(".00"): txt = txt[:-3]
        parts.append(f"{txt.replace('.', ',')} {NOMS_DEVISE.get(dev, dev)}")
    return " et ".join(parts) if parts else "0 euro"


def message_resume(jour, dispo_a, appels, dispo_c, ca):
    l = [f"Résumé du {jour} :"]
    if dispo_a and "resultats" in appels:
        detail = ", ".join(f"{v} {n}" for v, n in appels["resultats"].items()) + (f", autre valeur {appels['autres']}" if appels.get("autres") else "")
        l.append(f"Appels Sid — {appels['total']} entreprise(s) sur la liste : {appels['Appelé']} avec un résultat, {appels['total'] - appels['Appelé']} sans résultat. {detail}.")
        if appels["resultats"].get("RDV pris"): l.append(f"RDV pris : {appels['resultats']['RDV pris']} — à voir dans le tableur du jour (ces entreprises sortent de la liste d'appels).")
    elif dispo_a:
        l.append(f"Appels Sid — {appels['total']} entreprise(s) sur la liste : {appels['Appelé']} appelée(s), {appels['Répondu']} répondu(es), "
                 f"{appels['Rendez-vous pris']} rendez-vous pris, {appels['Refus']} refus.")
    else:
        l.append(f"Appels Sid — pas de chiffre : {appels}.")
    if dispo_c:
        au = "au moins " if ca["partiel"] else ""
        l.append(f"Chiffre d'affaires Stripe du jour : {au}{_montants_texte(ca['montants'])} ({ca['paiements']} paiement(s) réussi(s)).")
    else:
        l.append(f"Chiffre d'affaires Stripe — pas de chiffre : {ca}.")
    return "\n".join(l)


def alerter_discord(texte):
    """Poste dans le salon Discord habituel (celui des autres agents) ; jeton lu par prospection.py dans Jarvis\\.env, jamais affiché."""
    try:
        a = P.acces_discord()
        if not a: return False
        jeton, salon, uid = a
        r = P.discord(jeton, "POST", f"/channels/{salon}/messages", {"content": f"<@{uid}> {texte}"[:1900], "allowed_mentions": {"users": [uid]}})
        return bool(r and "id" in r)
    except Exception as ex: print(f"  alerte Discord impossible ({type(ex).__name__})"); return False


def cmd_resume(conf, jour, a_blanc, drive=None):
    etat = etat_lire()
    if not a_blanc and etat["envoyes"].get(jour):
        print(f"Résumé du {jour} déjà envoyé (ou simulé) aujourd'hui : rien de plus."); return 0
    dispo_a, appels = stats_appels(conf, jour, drive)
    dispo_c, ca = stripe_jour(jour)
    texte = message_resume(jour, dispo_a, appels, dispo_c, ca)
    if a_blanc:
        print("[à blanc] serait " + ("envoyé" if conf["envoi_automatique"] else "affiché seulement") + " :\n" + texte); return 0
    if conf["envoi_automatique"]:
        ok = alerter_discord(texte); print(texte); print("  (posté sur Discord)" if ok else "  ! Discord : non envoyé (voir ci-dessus)")
    else:
        print("[simulation : envoi_automatique=false] " + texte)
    etat["envoyes"][jour] = True
    for ancien in sorted(etat["envoyes"])[:-60]: del etat["envoyes"][ancien]
    etat_ecrire(etat)
    journaliser("resume", f"{jour} : appels {'ok' if dispo_a else 'indisponible'}, Stripe {'ok' if dispo_c else 'indisponible'}", a_blanc)
    return 0


def cmd_etat():
    etat = etat_lire()
    if not etat["envoyes"]: print("Aucun résumé envoyé pour l'instant."); return 0
    print(f"{len(etat['envoyes'])} résumé(s) envoyé(s) (ou simulé(s)), dernier : {max(etat['envoyes'])}."); return 0


# --- tâche planifiée Windows (jamais installée sans --oui) ---------------------------------------------------------
def _ps(s): return str(s).replace("'", "''")


def executer(commande):
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", commande], capture_output=True, text=True, timeout=120)
    return r.returncode, " ".join((r.stderr or r.stdout or "").split())[:200]


def commande_tache(action, conf):
    if action == "retirer": return f"Unregister-ScheduledTask -TaskName '{TACHE}' -Confirm:$false"
    py = Path(sys.executable); pyw = py.with_name("pythonw.exe"); pyw = pyw if pyw.exists() else py   # pythonw : aucune fenêtre ; la trace est dans resume-sid-journal.log
    return (f"$a = New-ScheduledTaskAction -Execute '{_ps(pyw)}' -Argument '\"{_ps(Path(__file__).resolve())}\" resume' -WorkingDirectory '{_ps(RACINE)}'; "
            f"$t = New-ScheduledTaskTrigger -Daily -At {conf['heure_tache']}; $p = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited; "
            "$s = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 1); "
            f"Register-ScheduledTask -TaskName '{TACHE}' -Action $a -Trigger $t -Principal $p -Settings $s -Description 'Resume Discord du soir (appels Sid + Stripe), LM MULTI-SERVICES' -Force")


def cmd_tache(action, oui, conf):
    cmd = commande_tache(action, conf); verbe = "installer" if action == "installer" else "retirer"
    if not oui:
        print(f"Commande PowerShell ({verbe} la tâche « {TACHE} », tous les jours à {conf['heure_tache']}, rattrapage au réveil du PC si manquée) — rien n'est exécuté :\n\n{cmd}\n\n"
              f"Pour l'exécuter vraiment : python agents\\resume-sid.py {verbe}-tache --oui")
        return 0
    code, msg = executer(cmd)
    if code != 0: print(f"  ! la tâche n'a pas pu être {'installée' if action == 'installer' else 'retirée'} : {msg or 'code ' + str(code)}"); return 2
    journaliser(f"{verbe}-tache", TACHE); print(f"Tâche « {TACHE} » {'installée' if action == 'installer' else 'retirée'}."); return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="resume-sid", description="Résumé Discord du soir : appels Sid + chiffre d'affaires Stripe du jour (aucun envoi à Sid ni au client).")
    base = argparse.ArgumentParser(add_help=False); base.add_argument("--a-blanc", action="store_true", help="affiche sans rien écrire ni envoyer")
    sp = p.add_subparsers(dest="cmd", required=True)
    sp.add_parser("resume", parents=[base]).add_argument("--jour", default=None)
    sp.add_parser("etat", parents=[base])
    for nom in ("installer-tache", "retirer-tache"): sp.add_parser(nom, parents=[base]).add_argument("--oui", action="store_true")
    args = p.parse_args(argv); M.exiger("resume-sid", args.cmd, getattr(args, "a_blanc", False))
    try:
        conf = cfg()
        if args.cmd == "resume": return cmd_resume(conf, (getattr(args, "jour", None) or date.today().isoformat()), args.a_blanc)
        if args.cmd == "etat": return cmd_etat()
        return cmd_tache("installer" if args.cmd == "installer-tache" else "retirer", args.oui, conf)
    except ErreurAgent as e:
        print(f"  ! {e}"); return 2
    except OSError as e:
        print(f"  ! erreur de fichier : {e.strerror or type(e).__name__}"); return 2


if __name__ == "__main__":
    sys.exit(main())
