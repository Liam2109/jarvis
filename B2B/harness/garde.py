#!/usr/bin/env python3
"""Garde commune des envois (harness, 15/11/2026). verifier_envoi(agent, canal, texte, destinataire) -> (ok, raisons).

BLOQUE (ok = False) : kill-switch B2B\\STOP présent ; lien Stripe non autorisé ; phrase interdite (OFFRE-REFERENCE.json) ; secret dans le texte
(jeton Discord, sk_live_, sk_test_, whsec_, adresse iCal secrète) ; envoi à un client (canal « email_client ») hors lundi-vendredi 08:00-19:00 (Paris).
AVERTIT seulement (écrit dans la trace, n'empêche pas) : machine non active, envoi_automatique à false, hors jours/heures du contrat, plafond du jour dépassé.
Aucune donnée client n'est écrite : ni texte, ni destinataire (seulement sa nature).
  python B2B\\harness\\garde.py --agent X --canal discord < texte     (garde.ps1) : affiche {"ok":..,"raisons":[..]} ; code 0 si ok, 2 si bloqué"""
import json, os, re, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ICI = Path(__file__).resolve().parent
RACINE = ICI.parent.parent
sys.path.insert(0, str(ICI))
import traces as T   # noqa: E402

REF = RACINE / "B2B" / "docs" / "OFFRE-REFERENCE.json"
STOP = RACINE / "B2B" / "STOP"
AGENTS = RACINE / "B2B" / "agents"
LIEN = re.compile(r"https://buy\.stripe\.com/[A-Za-z0-9]+")
SECRETS = [(re.compile(r"\b[MN][A-Za-z\d_-]{23,25}\.[A-Za-z\d_-]{6}\.[A-Za-z\d_-]{27,38}\b"), "jeton Discord"),
           (re.compile(r"\bsk_live_[A-Za-z0-9]{8,}"), "clé Stripe sk_live_"), (re.compile(r"\bsk_test_[A-Za-z0-9]{8,}"), "clé Stripe sk_test_"),
           (re.compile(r"\brk_live_[A-Za-z0-9]{8,}"), "clé Stripe restreinte"), (re.compile(r"\bwhsec_[A-Za-z0-9]{8,}"), "secret webhook whsec_"),
           (re.compile(r"calendar\.google\.com/calendar/ical/[^\s]+/private-[0-9a-f]+", re.I), "adresse iCal secrète"),
           (re.compile(r"/ical/[^\s]*private-[0-9a-f]{16,}", re.I), "adresse iCal secrète")]


def secrets_dans(texte):
    return sorted({nom for rx, nom in SECRETS if rx.search(texte or "")})


def heure_paris(maintenant=None):
    if maintenant is None and os.environ.get("JARVIS_GARDE_MAINTENANT"): return datetime.fromisoformat(os.environ["JARVIS_GARDE_MAINTENANT"])   # tests : heure de Paris figée
    n = maintenant or datetime.now(timezone.utc)
    if n.tzinfo is None: return n   # déjà une heure de Paris (tests)
    u = n.astimezone(timezone.utc).replace(tzinfo=None)
    def dernier_dimanche(m): d = datetime(u.year, m, 31, 1); return d - timedelta(days=(d.weekday() + 1) % 7)
    return u + timedelta(hours=2 if dernier_dimanche(3) <= u < dernier_dimanche(10) else 1)


def _hm(s): h, m = s.split(":"); return int(h) * 60 + int(m)


def dans_creneau(n, jours, debut, fin):
    return n.weekday() in jours and _hm(debut) <= n.hour * 60 + n.minute < _hm(fin)


def ref():
    return json.loads(REF.read_text(encoding="utf-8"))


def contrat(agent):
    p = ICI / "contrats" / f"{agent}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def _contexte_reel(agent):
    """machine_active (bool) et envoi_automatique (bool) lus comme les agents (machine.py) ; aucune valeur n'est affichée."""
    ctx = {}
    try:
        sys.path.insert(0, str(AGENTS)); import machine as M
        ctx["machine_active"] = M.verifier(agent, "garde", journal=os.devnull)[0]
        cfg = AGENTS / f"{agent}-config.json"
        if cfg.exists(): ctx["envoi_automatique"] = M.lire_fusionnee(cfg).get("envoi_automatique") is True
    except Exception: pass
    return ctx


def _compteur(agent, jour, ajouter=False):
    p = T.dossier_logs() / "_garde" / f"{jour}.json"
    try: c = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError): c = {}
    if ajouter:
        c[agent] = c.get(agent, 0) + 1
        try: p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(c), encoding="utf-8")
        except OSError: pass
    return c.get(agent, 0)


def verifier_envoi(agent, canal, texte, destinataire="", maintenant=None, ctx=None, tracer=True):
    """(ok, raisons). raisons : « BLOQUE : … » ou « AVERTIT : … ». ctx (tests) : machine_active, envoi_automatique, stop (bool), deja_envoyes (int)."""
    r = ref(); n = heure_paris(maintenant); jour = f"{n:%Y-%m-%d}"; texte = texte or ""
    ctx = dict(_contexte_reel(agent) if ctx is None else ctx)
    c = contrat(agent); bloque, avertit = [], []
    if ctx.get("stop", STOP.exists()): bloque.append("kill-switch B2B\\STOP présent : aucun envoi")
    for l in LIEN.findall(texte):
        if l not in r["liens_stripe_autorises"]: bloque.append(f"lien Stripe non autorisé (…{l[-6:]})")
    bas = texte.lower()
    for ph in r["phrases_interdites"]:
        if ph == "facultative":
            if any("facultati" in s and re.search(r"maintenance|abonnement|h[ée]bergement|€|mois", s) for s in re.split(r"[.;|!?\n]", bas)): bloque.append("phrase interdite « facultative » (offre)")   # même phrase ou même champ
        elif ph.lower() in bas: bloque.append(f"phrase interdite « {ph} »")
    for s in secrets_dans(texte): bloque.append(f"secret dans le texte ({s})")
    if canal == "email_client":
        e = r["envoi_client"]
        if not dans_creneau(n, e["jours"], e["debut"], e["fin"]): bloque.append(f"envoi client hors lundi-vendredi {e['debut']}-{e['fin']} ({n:%a %H:%M})")
    if ctx.get("machine_active") is False: avertit.append("machine non active (b2b.local.json)")
    if ctx.get("envoi_automatique") is False: avertit.append("envoi_automatique = false : l'agent devrait être en simulation")
    if c:
        if not dans_creneau(n, c["jours"], c["heures"]["debut"], c["heures"]["fin"]): avertit.append(f"hors horaires du contrat ({c['heures']['debut']}-{c['heures']['fin']})")
        deja = ctx.get("deja_envoyes", _compteur(agent, jour))
        if deja >= c["plafonds"]["messages_par_jour"]: avertit.append(f"plafond du jour atteint ({deja}/{c['plafonds']['messages_par_jour']})")
        if c["statut"] == "prevu": avertit.append("agent au statut « prevu » : il ne devrait pas envoyer")
    else: avertit.append(f"aucun contrat pour l'agent « {agent} »")
    raisons = [f"BLOQUE : {x}" for x in bloque] + [f"AVERTIT : {x}" for x in avertit]
    ok = not bloque
    if tracer:
        if ok and ctx.get("deja_envoyes") is None: _compteur(agent, jour, ajouter=True)
        if raisons: T.ecrire(agent, f"garde {canal}", "envoi bloqué" if not ok else "envoi averti", 0, ok=ok, erreur="; ".join(raisons), maintenant=n if maintenant else None)
    return ok, raisons


def agent_courant():
    """Nom de l'agent = nom du script lancé (appels-sid.py -> appels-sid)."""
    return Path(sys.argv[0] or "inconnu").stem or "inconnu"


def avant_envoi(canal, texte, destinataire="", agent=None):
    """Appel unique placé avant chaque envoi : True si l'envoi peut partir. Une panne de la garde n'empêche jamais un envoi (elle est dite)."""
    try:
        ok, raisons = verifier_envoi(agent or agent_courant(), canal, texte, destinataire)
        if not ok: print("  ! garde : envoi BLOQUÉ (" + " ; ".join(x for x in raisons if x.startswith("BLOQUE")) + ")")
        return ok
    except Exception as e:
        print(f"  ! garde indisponible ({type(e).__name__}) : envoi non contrôlé"); return True


def main(argv=None):
    import argparse
    a = argparse.ArgumentParser(); a.add_argument("--agent", required=True); a.add_argument("--canal", default="discord"); a.add_argument("--destinataire", default="")
    a = a.parse_args(argv)
    texte = sys.stdin.buffer.read().decode("utf-8", "replace")
    ok, raisons = verifier_envoi(a.agent, a.canal, texte, a.destinataire)
    print(json.dumps({"ok": ok, "raisons": raisons}, ensure_ascii=False))
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
