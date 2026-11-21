#!/usr/bin/env python3
"""Superviseur du domaine PROSPECTION (21/11/2026) : toutes les 30 minutes, il regarde les agents qui remplissent la journée d'appels (relances, appels-sid,
prospection) et la cohérence de leurs données : ont-ils tourné ? un prospect est-il compté deux fois ? une date est-elle illogique ? les chiffres d'appels,
de leads et de rendez-vous du tableau de bord se contredisent-ils ? Il corrige seul ce qui ne peut rien casser, il alerte et attend « go » pour le reste.

  python agents\\superviseur-prospection.py passage [--essai] [--maintenant AAAA-MM-JJTHH:MM]   un passage (tâche serveur, toutes les 30 min)
  python agents\\superviseur-prospection.py etat                                                verrou, dernier passage, corrections du jour, ce qui attend un « go »

CORRIGE SEUL (rien ne peut être perdu) : relance une fois par jour un agent planté, silencieux ou bloqué ; ajoute une clé d'état manquante (vide) ;
retire un doublon strictement identique (un prospect relancé deux fois dans la même liste) ; remet l'historique du tableau de bord dans l'ordre des dates.
NE TOUCHE JAMAIS (alerte et attend « go ») : deux entrées pour le même jour (laquelle garder ?), une date dans le futur, une clé de relance mal formée,
un compte de relances qui ne colle pas aux relances mémorisées, plus de leads chauds ou de rendez-vous que d'appels, un fichier illisible.
VERROU : rien n'est corrigé et rien n'est posté tant que go_superviseurs n'est pas true dans un fichier de réglages local (après le « go superviseurs » de Liam). --essai marche toujours."""
import argparse, re, sys
from datetime import date, datetime
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import machine as M   # machine active (refus hors du serveur, sauf --essai)

sys.path.insert(0, str(ICI.parent / "harness"))
import superviseurs as S   # moteur commun

AGENT, DOMAINE = "superviseur-prospection", "Prospection"
AGENTS_SUIVIS = ["relances", "appels-sid", "prospection"]
DEFAUT = {"heure_resume": "08:45"}
RACINE = ICI.parent.parent
HISTORIQUE_JSON = RACINE / "dashboard" / "data" / "historique.json"
CLE_ANNONCE = re.compile(r"^0\d{9}\|\d{4}-\d{2}-\d{2}\|\d+$")


def controle_relances():
    """relances-etat.json : forme, dates d'envoi, clés d'annonce « téléphone|date d'appel|numéro de relance », compte du jour cohérent avec les annonces."""
    p = ICI / "relances-etat.json"
    out = S.controle_forme("relances", p, {"annonces": dict, "envois": dict})
    out += S.controle_dates_valides("relances", p, ["envois"], "envois de relances")
    d, pb = S.lire_json(p)
    if pb or not isinstance(d, dict): return out
    annonces, envois = d.get("annonces"), d.get("envois")
    if isinstance(annonces, dict):
        mauvaises = [k for k in annonces if not CLE_ANNONCE.match(str(k))]
        if mauvaises:
            out.append(S.risque("relances", f"{len(mauvaises)} clé(s) de relance mal formée(s)",
                                "attendu « téléphone|date d'appel|numéro » : une clé n'est jamais supprimée tout seul (le lead serait relancé deux fois)", cle="relances|cles"))
        futures = sorted({str(k).split("|")[1] for k in annonces if CLE_ANNONCE.match(str(k)) and str(k).split("|")[1] > date.today().isoformat()})
        if futures:
            out.append(S.risque("relances", "appel daté dans le futur dans les relances annoncées", f"{', '.join(futures[:5])} : donnée illogique, rien n'est touché", cle="relances|appel-futur"))
    if isinstance(annonces, dict) and isinstance(envois, dict):
        for jour, n in sorted(envois.items()):
            if not isinstance(n, int) or isinstance(n, bool) or n < 0:
                out.append(S.risque("relances", f"compte d'envois invalide pour le {jour}", f"« {n} » n'est pas un nombre de relances", cle=f"relances|envois|{jour}|type")); continue
            reels = sum(1 for v in annonces.values() if str(v) == jour)
            if reels and n > reels:
                out.append(S.risque("relances", f"le {jour}, {n} relance(s) annoncée(s) mais {reels} mémorisée(s)",
                                    "les deux chiffres se contredisent : Liam dit lequel est bon", cle=f"relances|envois|{jour}|ecart"))
    return out


def controle_appels_sid():
    """appels-sid-etat.json (listes du jour, suivi Google) et appels-sid-historique.json (un numéro déjà appelé = un jour et une raison)."""
    p = ICI / "appels-sid-etat.json"
    out = S.controle_forme("appels-sid", p, {"sorties": dict, "listes": dict, "alertes": dict, "google": dict})
    out += S.controle_dates_valides("appels-sid", p, ["listes"], "listes d'appels déjà préparées")
    h = ICI / "appels-sid-historique.json"
    d, pb = S.lire_json(h)
    if pb: return out + [pb]
    if isinstance(d, dict):
        futurs = sorted({str(v.get("jour")) for v in d.values() if isinstance(v, dict) and str(v.get("jour") or "") > date.today().isoformat()})
        if futurs:
            out.append(S.risque("appels-sid", "numéro marqué appelé à une date future dans l'historique",
                                f"{', '.join(futurs[:5])} : le numéro serait écarté des prochaines listes pour rien", cle="appels-sid|historique|futur"))
        sans_jour = [k for k, v in d.items() if not isinstance(v, dict) or not str(v.get("jour") or "").strip()]
        if sans_jour:
            out.append(S.risque("appels-sid", f"{len(sans_jour)} entrée(s) d'historique sans date", "entrée jamais complétée ni supprimée tout seul", cle="appels-sid|historique|sans-jour"))
    return out


def controle_prospection():
    """prospection-etat.json : forme, doublons de la liste des relances d'e-mails (un prospect relancé deux fois), dates des lots et des envois."""
    p = ICI / "prospection-etat.json"
    out = S.controle_forme("prospection", p, {"vus": dict, "envois": dict, "relances": list, "lots": dict, "envoyes": dict, "recherches": dict})
    out += S.controle_doublons("prospection", p, ["relances"], "relances d'e-mails")
    out += S.controle_dates_valides("prospection", p, ["lots"], "lots préparés")
    out += S.controle_dates_valides("prospection", p, ["envoyes"], "lots envoyés")
    return out


def controle_tableau_bord():
    """dashboard/data/historique.json (écrit par le gros PC ; absent sur le serveur = rien à vérifier) : une entrée par jour, dans l'ordre,
    et des chiffres qui ne se contredisent pas (jamais plus de leads chauds ou de rendez-vous que d'appels)."""
    out = S.controle_entrees_datees("tableau de bord", HISTORIQUE_JSON, "jours", "date")
    d, pb = S.lire_json(HISTORIQUE_JSON)
    if pb: return out
    if d is None or not isinstance(d, dict) or not isinstance(d.get("jours"), list): return out
    for x in d["jours"]:
        if not isinstance(x, dict): continue
        jour, appels = str(x.get("date") or "?"), x.get("appels")
        if not isinstance(appels, int) or isinstance(appels, bool): continue
        for cle, libelle in (("leads_chauds", "leads chauds"), ("rdv", "rendez-vous")):
            v = x.get(cle)
            if isinstance(v, int) and not isinstance(v, bool) and v > appels:
                out.append(S.risque("tableau de bord", f"le {jour}, {v} {libelle} pour {appels} appel(s)",
                                    "chiffres contradictoires : Liam dit lequel est bon (aucun n'est recalculé tout seul)", cle=f"historique|{jour}|{cle}"))
    return out


CONTROLES = [("relances", controle_relances), ("appels de Sid", controle_appels_sid),
             ("prospection", controle_prospection), ("tableau de bord", controle_tableau_bord)]


def cmd_etat(conf):
    r = S.resume_pour_jarvis(AGENT, DOMAINE, conf)
    print(f"Superviseur {DOMAINE} : {r['etat']} ; verrou « go superviseurs » {r['verrou']} ; dernier passage : {r['dernier_passage'] or 'aucun'}.")
    print(f"  agents suivis : {', '.join(AGENTS_SUIVIS)}")
    print(f"  corrections du jour : {len(r['corrections'])}" + ("".join(f"\n    - {x}" for x in r["corrections"][:10]) if r["corrections"] else ""))
    print(f"  en attente d'un « go » : {len(r['bloques'])}" + ("".join(f"\n    - {x}" for x in r["bloques"][:10]) if r["bloques"] else ""))
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog=AGENT, description="Superviseur du domaine Prospection : agents à l'heure, aucun prospect compté deux fois, chiffres d'appels cohérents.")
    sp = p.add_subparsers(dest="cmd", required=True)
    j = sp.add_parser("passage"); j.add_argument("--essai", "--a-blanc", dest="essai", action="store_true", help="lit, affiche, n'écrit rien, n'envoie rien, ne relance rien")
    j.add_argument("--maintenant", default=None, help="heure figée (tests)")
    sp.add_parser("etat")
    a = p.parse_args(argv)
    M.exiger(AGENT, a.cmd, getattr(a, "essai", False))
    try:
        conf = S.cfg(AGENT, DEFAUT)
        if a.cmd == "etat": return cmd_etat(conf)
        return S.lancer(AGENT, DOMAINE, AGENTS_SUIVIS, CONTROLES, conf, a.essai, datetime.fromisoformat(a.maintenant) if a.maintenant else None)
    except S.ErreurAgent as e:
        print(f"  ! {e}"); return 2
    except OSError as e:
        print(f"  ! erreur de fichier : {e.strerror or type(e).__name__}"); return 2


if __name__ == "__main__":
    sys.exit(main())
