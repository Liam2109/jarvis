#!/usr/bin/env python3
"""Agent panne-alerte (LM MULTI-SERVICES) : alerte Discord si un agent B2B actif, planifié à heure fixe (serveur-taches.json), n'a pas tourné aujourd'hui passé un délai de grâce
après son heure prévue. Lecture seule (outils\\agents-json.py + journaux des agents) : aucune écriture ailleurs, aucune relance, jamais deux fois la même alerte le même jour.
Même modèle que les autres agents B2B : réglages (panne-alerte-config.json), état (panne-alerte-etat.json), journal. `envoi_automatique: false` (défaut) = SIMULATION.

  python agents\\panne-alerte.py verifier [--a-blanc]    une vérification (agents à heure fixe seulement, ex. appels-sid 07:30, resume-sid 19:30) ; lancé périodiquement par la tâche planifiée
  python agents\\panne-alerte.py etat                    dernières pannes alertées (ou simulées) aujourd'hui

Un agent à « toutes_minutes » (devis, rendez-vous, reponses, prospection, stripe-alerte) n'est pas concerné : il n'a pas d'heure unique à manquer."""
import argparse, importlib.util, json, re, sys
from datetime import date, datetime
from pathlib import Path

ICI = Path(__file__).resolve().parent
RACINE = ICI.parent
sys.path.insert(0, str(ICI))
import machine as M   # config locale (panne-alerte-config.local.json) et machine active (b2b.local.json)
import prospection as P   # P.acces_discord / P.discord : salon Discord habituel

CONFIG, ETAT, JOURNAL = ICI / "panne-alerte-config.json", ICI / "panne-alerte-etat.json", ICI / "panne-alerte-journal.log"
DEFAUT = {"envoi_automatique": False, "intervalle_minutes": 5, "grace_minutes": 15}
AGENTS_JSON = RACINE.parent / "outils" / "agents-json.py"
TACHE = "Jarvis-PanneAlerte"


class ErreurAgent(Exception):
    """Problème signalé à Liam (message clair, code de sortie 2) : l'agent s'arrête sans rien écrire de plus."""


# --- point d'accès au monde extérieur (remplacé par une doublure dans les tests) ------------------------------------
def construire_agents():
    """Liste des agents (outils\\agents-json.py › construire()['agents']) : nom, planifié, horaire, dernier_passage. Lecture seule (journaux + schtasks + état)."""
    spec = importlib.util.spec_from_file_location("agents_json", AGENTS_JSON)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod.construire()["agents"]


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
    g = c.get("grace_minutes")
    c["grace_minutes"] = g if isinstance(g, int) and not isinstance(g, bool) and 0 <= g <= 240 else DEFAUT["grace_minutes"]
    return c


def etat_lire():
    try: e = json.loads(ETAT.read_text(encoding="utf-8")) if ETAT.exists() else {}
    except (OSError, ValueError): raise ErreurAgent(f"état illisible ({ETAT.name}) : rien n'est écrit ; corrigez ou supprimez le fichier à la main")
    if not isinstance(e, dict): raise ErreurAgent(f"état illisible ({ETAT.name}) : rien n'est écrit")
    e.setdefault("alertes", {})
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


# --- détection ------------------------------------------------------------------------------------------------------
def taches_serveur():
    """serveur-taches.json › agents : « actif_le » (AAAA-MM-JJ) et « jours » (0 = lundi) de chaque tâche ; {} s'il est illisible."""
    try: return json.loads((ICI / "serveur-taches.json").read_text(encoding="utf-8"))["agents"]
    except (OSError, ValueError, KeyError): return {}


def jours_contrat(nom):
    """Jours du contrat de l'agent (B2B/harness/contrats/<nom>.json), None sans contrat."""
    try: return json.loads((RACINE / "harness" / "contrats" / f"{nom}.json").read_text(encoding="utf-8"))["jours"]
    except (OSError, ValueError, KeyError): return None


def attendu_ce_jour(nom, jour, taches, jours=None):
    """Faux avant la date d'activation (actif_le) et hors des jours prévus (tâche, sinon contrat) : week-end d'un agent des jours ouvrés = aucune alerte (15/11/2026)."""
    t = taches.get(nom) or {}
    if t.get("actif_le") and jour.isoformat() < str(t["actif_le"]): return False
    js = t.get("jours") or (jours if jours is not None else jours_contrat(nom))
    return js is None or jour.weekday() in js


def en_panne(agents, maintenant, grace_minutes, taches=None, jours=None):
    """-> [(nom, heure)] des agents actifs, planifiés à heure fixe (ex. « chaque jour à 07:30 »), dont l'heure + délai de grâce est dépassée sans passage aujourd'hui.
    Jamais un agent pas encore actif (actif_le de serveur-taches.json) ni hors de ses jours (contrat : lundi-vendredi -> rien le samedi et le dimanche). `jours` (tests) : {nom: [jours]}."""
    j = maintenant.date().isoformat(); minute_actuelle = maintenant.hour * 60 + maintenant.minute
    taches = taches_serveur() if taches is None else taches
    out = []
    for a in agents:
        if not a.get("planifie"): continue
        if not attendu_ce_jour(a["nom"], maintenant.date(), taches, (jours or {}).get(a["nom"]) if jours is not None else None): continue
        m = re.match(r"chaque jour à (\d{2}):(\d{2})$", str(a.get("horaire") or ""))
        if not m: continue
        heure = m.group(1) + ":" + m.group(2); minute_prevue = int(m.group(1)) * 60 + int(m.group(2))
        if minute_actuelle < minute_prevue + grace_minutes: continue   # trop tôt pour juger ce jour-ci
        if str(a.get("dernier_passage") or "").startswith(j): continue   # déjà passé aujourd'hui
        out.append((a["nom"], heure))
    return out


def cmd_verifier(conf, a_blanc, maintenant=None):
    agents = construire_agents(); maintenant = maintenant or datetime.now()   # maintenant : heure figée (tests)
    pannes = en_panne(agents, maintenant, conf["grace_minutes"])
    j = maintenant.date().isoformat()
    etat = etat_lire()
    deja = etat["alertes"].get(j, {})
    nouveaux = [(nom, heure) for nom, heure in pannes if nom not in deja]
    if a_blanc:
        print("[à blanc] " + (f"{len(nouveaux)} panne(s) : " + "; ".join(f"{n} (prévu {h})" for n, h in nouveaux) if nouveaux else "aucune panne")); return 0
    for nom, heure in nouveaux:
        texte = f"⚠️ Panne : {nom} — aucune exécution aujourd'hui (prévue {heure})\nPour vérifier : python agents\\{nom}.py etat"
        if conf["envoi_automatique"]:
            ok = alerter_discord(texte); print(texte); print("  (posté sur Discord)" if ok else "  ! Discord : non envoyé (voir ci-dessus)")
        else:
            print("[simulation : envoi_automatique=false] " + texte)
        deja[nom] = True
        journaliser("panne", f"{nom} : aucune exécution aujourd'hui (prévue {heure})")
    etat["alertes"][j] = deja
    for ancien in sorted(etat["alertes"])[:-30]: del etat["alertes"][ancien]
    etat_ecrire(etat)
    print(f"{len(nouveaux)} panne(s) détectée(s)." if nouveaux else "Aucune panne détectée.")
    return 0


def cmd_etat():
    etat = etat_lire()
    j = date.today().isoformat(); du_jour = etat["alertes"].get(j, {})
    if not du_jour: print("Aucune panne alertée aujourd'hui."); return 0
    print(f"{len(du_jour)} panne(s) alertée(s) (ou simulée(s)) aujourd'hui : {', '.join(sorted(du_jour))}."); return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="panne-alerte", description="Alerte Discord si un agent B2B planifié à heure fixe n'a pas tourné à son heure (lecture seule).")
    base = argparse.ArgumentParser(add_help=False); base.add_argument("--a-blanc", action="store_true", help="affiche sans rien écrire ni envoyer")
    sp = p.add_subparsers(dest="cmd", required=True)
    sp.add_parser("verifier", parents=[base])
    sp.add_parser("etat", parents=[base])
    args = p.parse_args(argv); M.exiger("panne-alerte", args.cmd, getattr(args, "a_blanc", False))
    try:
        conf = cfg()
        if args.cmd == "verifier": return cmd_verifier(conf, args.a_blanc)
        return cmd_etat()
    except ErreurAgent as e:
        print(f"  ! {e}"); return 2
    except OSError as e:
        print(f"  ! erreur de fichier : {e.strerror or type(e).__name__}"); return 2


if __name__ == "__main__":
    sys.exit(main())
