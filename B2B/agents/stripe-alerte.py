#!/usr/bin/env python3
"""Agent stripe-alerte (LM MULTI-SERVICES) : alerte Discord dès qu'un nouveau paiement Stripe arrive. Aucune écriture sur Stripe (lecture seule, clé RESTREINTE), aucun remboursement
ni aucune autre action : seulement lire et alerter. Même modèle que les autres agents B2B : réglages (stripe-alerte-config.json), état (stripe-alerte-etat.json), journal.
`envoi_automatique: false` (défaut) = SIMULATION : rien sur Discord, la console (et le journal) disent ce qui serait envoyé.

  python agents\\stripe-alerte.py verifier [--a-blanc]                    une vérification : alerte chaque paiement Stripe réussi vu depuis le dernier passage ; c'est ce que lance la tâche planifiée
  python agents\\stripe-alerte.py etat                                    dernier paiement vu, nombre mémorisé
  python agents\\stripe-alerte.py installer-tache | retirer-tache [--oui] tâche planifiée Windows (répétée toutes les intervalle_minutes minutes) ; sans --oui, affiche seulement la commande

Premier passage (aucun point de départ encore enregistré) : les paiements déjà existants sont mémorisés SANS alerte (on ne veut pas une rafale d'alertes pour l'historique au premier
lancement) ; le journal le dit. Les passages suivants n'alertent QUE les paiements créés depuis le dernier passage, un par un, dans l'ordre, jamais deux fois le même (identifiant Stripe
mémorisé). Clé Stripe absente, refusée ou Stripe injoignable : rien n'est inventé, le prochain passage réessaie. Aucune donnée personnelle (nom, e-mail, numéro de carte) dans le message
Discord : seulement un montant, une devise et, si Stripe en donne une, une description courte du paiement."""
import argparse, json, os, re, subprocess, sys, time, urllib.error, urllib.request
from datetime import datetime
from pathlib import Path

ICI = Path(__file__).resolve().parent
RACINE = ICI.parent
sys.path.insert(0, str(ICI))
import machine as M   # config locale (stripe-alerte-config.local.json) et machine active (b2b.local.json)
import prospection as P, reponses as RP   # P.acces_discord / P.discord : salon Discord habituel ; RP.lire_env : lecture de Jarvis\.env

CONFIG, ETAT, JOURNAL = ICI / "stripe-alerte-config.json", ICI / "stripe-alerte-etat.json", ICI / "stripe-alerte-journal.log"
DEFAUT = {"envoi_automatique": False, "intervalle_minutes": 5}
NOMS_DEVISE = {"EUR": "euros", "USD": "dollars", "GBP": "livres"}
VUS_MAX = 300   # au-delà, seuls les VUS_GARDES identifiants les plus récents sont gardés (mémoire bornée)
VUS_GARDES = 200
TACHE = "Jarvis-StripeAlerte"


class ErreurAgent(Exception):
    """Problème signalé à Liam (message clair, code de sortie 2) : l'agent s'arrête sans rien écrire de plus."""


# --- points d'accès au monde extérieur (remplacés par des doublures dans les tests) ---------------------------------
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
    n = c.get("intervalle_minutes")
    c["intervalle_minutes"] = n if isinstance(n, int) and not isinstance(n, bool) and 1 <= n <= 1440 else DEFAUT["intervalle_minutes"]
    return c


def etat_lire():
    try: e = json.loads(ETAT.read_text(encoding="utf-8")) if ETAT.exists() else {}
    except (OSError, ValueError): raise ErreurAgent(f"état illisible ({ETAT.name}) : rien n'est écrit ; corrigez ou supprimez le fichier à la main")
    if not isinstance(e, dict): raise ErreurAgent(f"état illisible ({ETAT.name}) : rien n'est écrit")
    e.setdefault("dernier_ts", 0); e.setdefault("vus", {})
    return e


def etat_ecrire(e): ETAT.write_text(json.dumps(e, ensure_ascii=False, indent=1), encoding="utf-8")


def journaliser(action, detail="", a_blanc=False):
    if a_blanc: return
    with open(JOURNAL, "a", encoding="utf-8") as f: f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} | {action} | {detail}\n")


def alerter_discord(texte):
    """Poste dans le salon Discord habituel (celui des autres agents) ; jeton lu par prospection.py dans Jarvis\\.env, jamais affiché."""
    try:
        a = P.acces_discord()
        if not a: return False
        jeton, salon, uid = a
        r = P.discord(jeton, "POST", f"/channels/{salon}/messages", {"content": f"<@{uid}> {texte}"[:1900], "allowed_mentions": {"users": [uid]}})
        return bool(r and "id" in r)
    except Exception as ex: print(f"  alerte Discord impossible ({type(ex).__name__})"); return False


def message_paiement(c):
    """Montant et devise seulement (plus une courte description si Stripe en donne une) : jamais un nom, un e-mail ni un numéro de carte."""
    montant = (c.get("amount") or 0) / 100; dev = str(c.get("currency") or "eur").upper()
    txt = f"{montant:.2f}"
    if txt.endswith(".00"): txt = txt[:-3]
    desc = str(c.get("description") or "").strip()[:80]
    return f"Nouveau paiement Stripe : {txt.replace('.', ',')} {NOMS_DEVISE.get(dev, dev)}" + (f" ({desc})" if desc else "")


# --- la vérification ------------------------------------------------------------------------------------------
def cmd_verifier(conf, a_blanc):
    env = RP.lire_env(RACINE.parent / ".env"); cle = env.get("STRIPE_RESTRICTED_KEY", "").strip()
    if not cle or cle.endswith("_xxx") or cle == "xxx":
        print("  ! clé Stripe absente de Jarvis\\.env (STRIPE_RESTRICTED_KEY) : rien à vérifier"); journaliser("verifier", "clé Stripe absente", a_blanc); return 0
    etat = etat_lire()
    try:
        if not etat["dernier_ts"]:
            r = appel_stripe(cle, "charges?limit=10")
            charges = sorted(r.get("data") or [], key=lambda c: c.get("created") or 0)
            if a_blanc: print(f"[à blanc] premier passage : {len(charges)} paiement(s) déjà existant(s), aucune alerte (point de départ serait fixé)"); return 0
            etat["dernier_ts"] = charges[-1]["created"] if charges else int(time.time())
            etat["vus"] = {str(c["id"]): True for c in charges if c.get("id")}
            etat_ecrire(etat)
            journaliser("verifier", f"premier passage : point de départ fixé ({len(charges)} paiement(s) existant(s), aucune alerte)")
            print(f"Premier passage : {len(charges)} paiement(s) déjà existant(s), aucune alerte (point de départ fixé)."); return 0
        r = appel_stripe(cle, f"charges?limit=100&created[gte]={etat['dernier_ts']}")
    except urllib.error.HTTPError as ex:
        msg = "clé Stripe refusée ou permission de lecture manquante" if ex.code in (401, 403) else f"Stripe a répondu HTTP {ex.code}"
        print(f"  ! {msg} : le prochain passage réessaie"); journaliser("verifier", msg, a_blanc); return 2
    except Exception as ex:
        print(f"  ! Stripe injoignable ({type(ex).__name__}) : le prochain passage réessaie"); journaliser("verifier", f"injoignable ({type(ex).__name__})", a_blanc); return 2
    toutes = r.get("data") or []
    nouveaux = sorted((c for c in toutes if str(c.get("id")) not in etat["vus"] and c.get("paid") and c.get("status") == "succeeded"), key=lambda c: c.get("created") or 0)
    if a_blanc:
        print(f"[à blanc] {len(nouveaux)} nouveau paiement(s) : " + ("; ".join(message_paiement(c) for c in nouveaux) if nouveaux else "aucun")); return 0
    for c in nouveaux:
        texte = message_paiement(c)
        if conf["envoi_automatique"]:
            ok = alerter_discord(texte); print(texte); print("  (posté sur Discord)" if ok else "  ! Discord : non envoyé (voir ci-dessus)")
        else:
            print("[simulation : envoi_automatique=false] " + texte)
        journaliser("paiement", texte)
    for c in toutes:
        if c.get("id"): etat["vus"][str(c["id"])] = True
        if c.get("created"): etat["dernier_ts"] = max(etat["dernier_ts"], int(c["created"]))
    if len(etat["vus"]) > VUS_MAX:
        for k in list(etat["vus"])[:-VUS_GARDES]: del etat["vus"][k]
    etat_ecrire(etat)
    journaliser("verifier", f"{len(nouveaux)} nouveau(x) paiement(s)")
    print(f"{len(nouveaux)} nouveau(x) paiement(s)." if nouveaux else "Aucun nouveau paiement.")
    return 0


def cmd_etat():
    etat = etat_lire()
    if not etat["dernier_ts"]: print("Aucune vérification Stripe pour l'instant."); return 0
    print(f"Dernier paiement vu : {datetime.fromtimestamp(etat['dernier_ts']):%Y-%m-%d %H:%M} ; {len(etat['vus'])} identifiant(s) mémorisé(s)."); return 0


# --- tâche planifiée Windows (jamais installée sans --oui), répétée toutes les intervalle_minutes minutes ----------
def _ps(s): return str(s).replace("'", "''")


def executer(commande):
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", commande], capture_output=True, text=True, timeout=120)
    return r.returncode, " ".join((r.stderr or r.stdout or "").split())[:200]


def commande_tache(action, conf):
    if action == "retirer": return f"Unregister-ScheduledTask -TaskName '{TACHE}' -Confirm:$false"
    py = Path(sys.executable); pyw = py.with_name("pythonw.exe"); pyw = pyw if pyw.exists() else py   # pythonw : aucune fenêtre ; la trace est dans stripe-alerte-journal.log
    return (f"$a = New-ScheduledTaskAction -Execute '{_ps(pyw)}' -Argument '\"{_ps(Path(__file__).resolve())}\" verifier' -WorkingDirectory '{_ps(RACINE)}'; "
            f"$t = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(2) -RepetitionInterval (New-TimeSpan -Minutes {conf['intervalle_minutes']}) -RepetitionDuration (New-TimeSpan -Days 3650); "
            f"$p = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited; "
            "$s = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 10); "
            f"Register-ScheduledTask -TaskName '{TACHE}' -Action $a -Trigger $t -Principal $p -Settings $s -Description 'Alerte Discord sur nouveau paiement Stripe, LM MULTI-SERVICES' -Force")


def cmd_tache(action, oui, conf):
    cmd = commande_tache(action, conf); verbe = "installer" if action == "installer" else "retirer"
    if not oui:
        print(f"Commande PowerShell ({verbe} la tâche « {TACHE} », toutes les {conf['intervalle_minutes']} minutes) — rien n'est exécuté :\n\n{cmd}\n\n"
              f"Pour l'exécuter vraiment : python agents\\stripe-alerte.py {verbe}-tache --oui")
        return 0
    code, msg = executer(cmd)
    if code != 0: print(f"  ! la tâche n'a pas pu être {'installée' if action == 'installer' else 'retirée'} : {msg or 'code ' + str(code)}"); return 2
    journaliser(f"{verbe}-tache", TACHE); print(f"Tâche « {TACHE} » {'installée' if action == 'installer' else 'retirée'}."); return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="stripe-alerte", description="Alerte Discord sur nouveau paiement Stripe (lecture seule, aucune action sur Stripe).")
    base = argparse.ArgumentParser(add_help=False); base.add_argument("--a-blanc", action="store_true", help="affiche sans rien écrire ni envoyer")
    sp = p.add_subparsers(dest="cmd", required=True)
    sp.add_parser("verifier", parents=[base])
    sp.add_parser("etat", parents=[base])
    for nom in ("installer-tache", "retirer-tache"): sp.add_parser(nom, parents=[base]).add_argument("--oui", action="store_true")
    args = p.parse_args(argv); M.exiger("stripe-alerte", args.cmd, getattr(args, "a_blanc", False))
    try:
        conf = cfg()
        if args.cmd == "verifier": return cmd_verifier(conf, args.a_blanc)
        if args.cmd == "etat": return cmd_etat()
        return cmd_tache("installer" if args.cmd == "installer-tache" else "retirer", args.oui, conf)
    except ErreurAgent as e:
        print(f"  ! {e}"); return 2
    except OSError as e:
        print(f"  ! erreur de fichier : {e.strerror or type(e).__name__}"); return 2


if __name__ == "__main__":
    _t0 = time.time(); _code = main()
    if sys.argv[1:2] == ["verifier"] and "--a-blanc" not in sys.argv:   # trace du harness (B2B\logs\agents\stripe-alerte), jamais bloquante
        try: sys.path.insert(0, str(ICI.parent / "harness")); import traces; traces.ecrire("stripe-alerte", "verifier", "terminé" if _code == 0 else "échec", time.time() - _t0, ok=_code == 0, erreur=None if _code == 0 else f"code {_code}")
        except Exception: pass
    sys.exit(_code)
