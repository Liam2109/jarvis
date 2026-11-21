#!/usr/bin/env python3
"""Superviseur du domaine MAIL (21/11/2026) : toutes les 30 minutes, il surveille l'agent qui trie la boîte des alertes d'agences (interim, emoliam255) :
a-t-il tourné ? la lecture Gmail est-elle TOUJOURS en lecture seule ? les fiches d'agences sont-elles intactes ? une action « à rappeler » a-t-elle disparu
sans raison ? Il corrige seul ce qui ne peut rien casser dans le suivi (hors git), et il alerte Liam sans rien toucher pour tout le reste.

  python agents\\superviseur-mail.py passage [--essai] [--maintenant AAAA-MM-JJTHH:MM]   un passage (tâche serveur, toutes les 30 min)
  python agents\\superviseur-mail.py etat                                                verrou, dernier passage, corrections du jour, ce qui attend un « go »

Il ne lit JAMAIS la boîte, ni un jeton, ni un mot de passe : il lit le CODE de l'agent (les portées Gmail déclarées), ses réglages versionnés et son suivi.
CORRIGE SEUL (rien ne peut être perdu) : relance une fois par jour l'agent planté, silencieux ou bloqué ; retire une ligne strictement en double du suivi ;
ajoute une clé d'état manquante (vide).
NE TOUCHE JAMAIS (alerte et attend « go ») : une portée Gmail autre que la lecture seule, une boîte différente de celle attendue, une fiche d'agence
incomplète ou en double, une action à rappeler disparue, une adresse d'agence « confirmée » sans l'avoir été par Liam, un fichier illisible.
VERROU : rien n'est corrigé et rien n'est posté tant que go_superviseurs n'est pas true dans un fichier de réglages local (après le « go superviseurs » de Liam). --essai marche toujours."""
import argparse, re, sys
from datetime import datetime
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import machine as M   # machine active (refus hors du serveur, sauf --essai)

sys.path.insert(0, str(ICI.parent / "harness"))
import superviseurs as S   # moteur commun

AGENT, DOMAINE = "superviseur-mail", "Mail"
AGENTS_SUIVIS = ["interim"]
DEFAUT = {"heure_resume": "08:45", "boite_attendue": "emoliam255@gmail.com", "portee_attendue": "https://www.googleapis.com/auth/gmail.readonly"}
SCRIPT_TRI = ICI / "interim.py"
CONFIG_TRI = ICI / "interim-config.json"
ETAT_TRI = ICI / "interim-etat.json"
SUIVI_TRI = ICI / "interim-suivi.csv"
PORTEE = re.compile(r"https://(?:www\.)?googleapis\.com/auth/[\w.\-]+")
COLONNES_FICHE = ("agence", "confirmee", "source")      # champs attendus d'une fiche d'agence dans les réglages de l'agent de tri


def controle_lecture_seule(conf):
    """Le tri de la boîte doit rester en LECTURE SEULE : toute portée Google autre que gmail.readonly dans le code de l'agent est une alerte immédiate.
    Aucun jeton n'est lu ni affiché : seules les portées écrites dans le script sont regardées."""
    out = []
    if not SCRIPT_TRI.is_file():
        return [S.risque("interim", "le script de tri du courrier est absent", f"{SCRIPT_TRI.name} introuvable : plus rien n'est trié", cle="interim|script-absent")]
    try: t = SCRIPT_TRI.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return [S.risque("interim", f"{SCRIPT_TRI.name} illisible", type(e).__name__, cle="interim|script-illisible")]
    attendue = str(conf.get("portee_attendue") or DEFAUT["portee_attendue"])
    trouvees = sorted(set(PORTEE.findall(t)))
    en_trop = [p for p in trouvees if p != attendue]
    if en_trop:
        out.append(S.risque("interim", "la lecture Gmail n'est plus en lecture seule",
                            f"portée(s) en trop : {', '.join(en_trop)} — arrêter l'agent avant de relancer un passage", cle="interim|portees"))
    elif not trouvees:
        out.append(S.risque("interim", "aucune portée Gmail déclarée dans le script de tri",
                            "la lecture seule n'est plus garantie par le code : à vérifier à la main", cle="interim|portees-absentes"))
    c, pb = S.lire_json(CONFIG_TRI)
    if pb: return out + [pb]
    if isinstance(c, dict):
        boite = str(c.get("boite") or "").strip()
        if boite and boite != str(conf.get("boite_attendue") or DEFAUT["boite_attendue"]):
            out.append(S.risque("interim", "la boîte triée n'est plus celle attendue",
                                "réglage « boite » changé : un superviseur ne choisit pas une boîte à la place de Liam", cle="interim|boite"))
    return out


def controle_etat_tri():
    """interim-etat.json : forme attendue et dates valides (mails déjà résumés, rappels déjà envoyés)."""
    out = S.controle_forme("interim", ETAT_TRI, {"vus": dict, "matin": dict, "semaine": dict})
    for cle, libelle in (("matin", "résumés du matin déjà envoyés"), ("semaine", "rappels du lundi déjà envoyés")):
        out += S.controle_dates_valides("interim", ETAT_TRI, [cle], libelle)
    return out


def controle_fiches_agences():
    """Fiches d'agences : le suivi (hors git) et la liste de départ versionnée. Lignes en double identiques -> corrigées ;
    fiche incomplète, conflit de fiche ou adresse « confirmée » sans Liam -> alerte, jamais touchée (ce sont les données de Liam)."""
    out = S.controle_doublons_csv("interim", SUIVI_TRI, "agence")
    lignes = S.lignes_csv(SUIVI_TRI)
    vides = [l.get("agence") or "(sans nom)" for l in lignes if not str(l.get("agence") or "").strip()]
    if vides:
        out.append(S.risque("interim", f"{len(vides)} fiche(s) d'agence sans nom dans le suivi", "fiche jamais complétée ni supprimée tout seul", cle="interim|suivi|sans-nom"))
    c, pb = S.lire_json(CONFIG_TRI)
    if pb: return out + [pb]
    if isinstance(c, dict) and isinstance(c.get("agences"), list):
        incompletes = [str(a.get("agence") or "(sans nom)")[:40] for a in c["agences"] if isinstance(a, dict) and any(k not in a for k in COLONNES_FICHE)]
        if incompletes:
            out.append(S.risque("interim", f"{len(incompletes)} fiche(s) d'agence incomplète(s) dans les réglages",
                                f"{', '.join(sorted(set(incompletes))[:5])} : champ attendu absent (réglage versionné, jamais modifié par un agent)", cle="interim|agences|incompletes"))
        noms = [str(a.get("agence") or "").strip() for a in c["agences"] if isinstance(a, dict)]
        doubles = sorted({n for n in noms if n and noms.count(n) > 1})
        if doubles:
            out.append(S.risque("interim", f"{len(doubles)} agence(s) écrite(s) deux fois dans les réglages", f"{', '.join(doubles[:5])} : Liam choisit laquelle garder", cle="interim|agences|doubles"))
        faux_oui = [str(a.get("agence") or "")[:40] for a in c["agences"]
                    if isinstance(a, dict) and str(a.get("confirmee") or "").strip().startswith("oui") and "liam" not in str(a.get("confirmee") or "").lower()]
        if faux_oui:
            out.append(S.risque("interim", f"{len(faux_oui)} adresse(s) marquée(s) confirmée(s) sans Liam",
                                f"{', '.join(sorted(set(faux_oui))[:5])} : seul Liam confirme une adresse (commande « noter … confirme »)", cle="interim|agences|confirmee"))
    return out


def controle_actions_perdues(etat):
    """Les actions « à rappeler » (colonne prochaine_action du suivi) ne doivent pas disparaître sans raison : comparaison avec le passage précédent."""
    valeurs = {str(l.get("agence") or "")[:60]: str(l.get("prochaine_action") or "") for l in S.lignes_csv(SUIVI_TRI) if str(l.get("agence") or "").strip()}
    return S.controle_disparition("interim", etat, "prochaine_action", valeurs, "action(s) à rappeler")


def cmd_etat(conf):
    r = S.resume_pour_jarvis(AGENT, DOMAINE, conf)
    print(f"Superviseur {DOMAINE} : {r['etat']} ; verrou « go superviseurs » {r['verrou']} ; dernier passage : {r['dernier_passage'] or 'aucun'}.")
    print(f"  agent suivi : {', '.join(AGENTS_SUIVIS)} ; suivi lu : {SUIVI_TRI.name} ({len(S.lignes_csv(SUIVI_TRI))} fiche(s))")
    print(f"  corrections du jour : {len(r['corrections'])}" + ("".join(f"\n    - {x}" for x in r["corrections"][:10]) if r["corrections"] else ""))
    print(f"  en attente d'un « go » : {len(r['bloques'])}" + ("".join(f"\n    - {x}" for x in r["bloques"][:10]) if r["bloques"] else ""))
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog=AGENT, description="Superviseur du domaine Mail : le tri du courrier tourne, reste en lecture seule, et aucune fiche ni action ne disparaît.")
    sp = p.add_subparsers(dest="cmd", required=True)
    j = sp.add_parser("passage"); j.add_argument("--essai", "--a-blanc", dest="essai", action="store_true", help="lit, affiche, n'écrit rien, n'envoie rien, ne relance rien")
    j.add_argument("--maintenant", default=None, help="heure figée (tests)")
    sp.add_parser("etat")
    a = p.parse_args(argv)
    M.exiger(AGENT, a.cmd, getattr(a, "essai", False))
    try:
        conf = S.cfg(AGENT, DEFAUT)
        if a.cmd == "etat": return cmd_etat(conf)
        etat = S.etat_lire(AGENT)      # l'empreinte du passage précédent sert au contrôle des actions perdues
        controles = [("lecture seule", lambda: controle_lecture_seule(conf)), ("état du tri", controle_etat_tri),
                     ("fiches d'agences", controle_fiches_agences), ("actions à rappeler", lambda: controle_actions_perdues(etat))]
        return S.lancer(AGENT, DOMAINE, AGENTS_SUIVIS, controles, conf, a.essai, datetime.fromisoformat(a.maintenant) if a.maintenant else None, etat)
    except S.ErreurAgent as e:
        print(f"  ! {e}"); return 2
    except OSError as e:
        print(f"  ! erreur de fichier : {e.strerror or type(e).__name__}"); return 2


if __name__ == "__main__":
    sys.exit(main())
