#!/usr/bin/env python3
"""Surveillant du harness (15/11/2026) : lit les contrats (B2B\\harness\\contrats) et les traces du jour (B2B\\logs\\agents) et signale sur Discord
une ligne par agent en défaut : « agent X n'a pas tourné » (aucune trace après son heure alerte_si_silence) ou « agent X : erreur » (trace ok:false).
Silence si tout va bien, sauf le lundi matin : « harness OK, N agents ». Envoi avec la fonction existante (prospection.acces_discord / discord) ;
envoi_automatique = false (défaut, surveillant-config.json) ou --simulation : rien sur Discord, le texte est affiché.
  python B2B\\agents\\surveillant.py verifier [--simulation] [--maintenant AAAA-MM-JJTHH:MM]"""
import argparse, json, sys, time
from datetime import datetime
from pathlib import Path

ICI = Path(__file__).resolve().parent
AGENTS = ICI.parent / "agents"
sys.path.insert(0, str(ICI)); sys.path.insert(0, str(AGENTS))
import traces as T   # noqa: E402

CONFIG = AGENTS / "surveillant-config.json"
SURVEILLES = ("actif", "simulation")


def contrats():
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted((ICI / "contrats").glob("*.json"))]


def _hm(s): h, m = s.split(":"); return int(h) * 60 + int(m)


def contrats_surveilles():
    """Agents d'une tâche serveur : seulement ceux de agents_actifs (b2b.local.json) ; les autres (tâches Windows locales) : selon leur contrat."""
    cs = contrats()
    try:
        import machine as M; actifs = set(M.agents_actifs())
        serveur = set(json.loads((AGENTS / "serveur-taches.json").read_text(encoding="utf-8"))["agents"])
    except Exception: return cs
    return [c for c in cs if c["nom"] not in serveur or c["nom"] in actifs]


def taches_serveur():
    """serveur-taches.json › agents (actif_le, jours) ; {} s'il est illisible."""
    try: return json.loads((AGENTS / "serveur-taches.json").read_text(encoding="utf-8"))["agents"]
    except (OSError, ValueError, KeyError): return {}


def attendu(nom, jours_contrat, jour_date, taches):
    """Vrai si l'agent doit tourner ce jour-là : date d'activation atteinte (« actif_le » de serveur-taches.json) et jour prévu (contrat, et « jours » de la tâche s'il y en a)."""
    t = taches.get(nom) or {}
    if t.get("actif_le") and jour_date.isoformat() < str(t["actif_le"]): return False
    return jour_date.weekday() in jours_contrat and (not t.get("jours") or jour_date.weekday() in t["jours"])


def _feuille_appels_sid_creee(jour):
    """Vrai si l'état réel d'appels-sid montre une feuille Google effectivement créée pour ce jour (etat['google'][jour]['feuille']) ;
    False aussi bien si rien n'a tourné que si l'agent est resté en simulation (envoi_automatique=false) : dans les deux cas, aucune feuille pour Sid."""
    try:
        g = json.loads((AGENTS / "appels-sid-etat.json").read_text(encoding="utf-8")).get("google") or {}
        return bool((g.get(jour) or {}).get("feuille"))
    except (OSError, ValueError):
        return False


def defauts(maintenant, cs=None, dossier=None, taches=None):
    """Lignes de défaut (une par agent) et nombre d'agents surveillés. Un agent pas encore actif (actif_le) ou hors de ses jours (week-end d'un agent des jours ouvrés) : silence."""
    jour = f"{maintenant:%Y-%m-%d}"; minutes = maintenant.hour * 60 + maintenant.minute; out = []; n = 0
    taches = taches_serveur() if taches is None else taches
    for c in (cs if cs is not None else contrats()):
        if c["statut"] not in SURVEILLES or c["nom"] == "surveillant": continue
        t_ = taches.get(c["nom"]) or {}
        if t_.get("actif_le") and jour < str(t_["actif_le"]): continue   # pas encore actif : ni compté ni alerté
        n += 1; t = T.lire(c["nom"], jour, dossier)
        execs = [x for x in t if not str(x.get("decision", "")).startswith("garde ")]
        erreurs = [x for x in t if not x.get("ok", True)]
        if erreurs:
            e = erreurs[-1]; out.append(f"agent {c['nom']} : erreur ({str(e.get('erreur') or e.get('resultat'))[:120]}, {e.get('heure', '')[11:16]})")
        elif c.get("alerte_si_silence") and attendu(c["nom"], c["jours"], maintenant.date(), taches) and minutes >= _hm(c["alerte_si_silence"]) and not execs:
            out.append(f"agent {c['nom']} n'a pas tourné aujourd'hui (attendu avant {c['alerte_si_silence']})")
        elif (c["nom"] == "appels-sid" and c.get("alerte_si_pas_de_feuille") and attendu(c["nom"], c["jours"], maintenant.date(), taches)
              and minutes >= _hm(c["alerte_si_pas_de_feuille"]) and not _feuille_appels_sid_creee(jour)):
            out.append(f"agent appels-sid : aucune feuille « Appels {jour} » dans le Drive de Sid (attendu avant {c['alerte_si_pas_de_feuille']}) — vérifier envoi_automatique")
    return out, n


def message(maintenant, lignes, n):
    if lignes: return "**Harness**\n" + "\n".join(lignes)
    if maintenant.weekday() == 0 and maintenant.hour < 12: return f"**Harness** : harness OK, {n} agents"
    return ""


def envoi_automatique():
    try:
        import machine as M; return M.lire_fusionnee(CONFIG).get("envoi_automatique") is True
    except Exception: return False


def poster(texte):
    """Fonction d'envoi existante des agents (bot Discord, salon habituel). True si posté."""
    import prospection as P
    a = P.acces_discord()
    if not a: return False
    jeton, salon, uid = a
    return P.discord(jeton, "POST", f"/channels/{salon}/messages", {"content": f"<@{uid}> {texte}"[:1900], "allowed_mentions": {"users": [uid]}}) is not None


def cmd_verifier(simulation, maintenant=None, envoyer=None):
    n0 = time.time(); m = maintenant or datetime.now()
    lignes, n = defauts(m, contrats_surveilles()); texte = message(m, lignes, n)
    reel = not simulation and envoi_automatique()
    if not texte: res = "silence (tout va bien)"
    elif reel: res = "posté" if (envoyer or poster)(texte) else "Discord : non envoyé"
    else: res = "simulation"
    print(texte or "(silence : tout va bien)") ; print(f"  [{res}]")
    T.ecrire("surveillant", "verifier", f"{len(lignes)} défaut(s) sur {n} agents ; {res}", time.time() - n0, ok=True)
    return 0


def main(argv=None):
    a = argparse.ArgumentParser(prog="surveillant"); sp = a.add_subparsers(dest="cmd", required=True)
    v = sp.add_parser("verifier"); v.add_argument("--simulation", action="store_true"); v.add_argument("--maintenant")
    a = a.parse_args(argv)
    if not a.simulation:
        import machine as M; M.exiger("surveillant", a.cmd)
    return cmd_verifier(a.simulation, datetime.fromisoformat(a.maintenant) if a.maintenant else None)


if __name__ == "__main__":
    sys.exit(main())
