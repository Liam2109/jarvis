#!/usr/bin/env python3
"""Superviseur du domaine VENTE (21/11/2026) : toutes les 30 minutes, il regarde les agents qui mènent à la vente (devis, chiffres-serveur, stripe-alerte,
rendez-vous, reponses) et la cohérence de leurs données : ont-ils tourné ? leur dernier passage est-il en erreur ? les chiffres se contredisent-ils ?
Il corrige seul ce qui ne peut rien casser et il n'écrit RIEN dès que l'argent est en jeu : il alerte Liam sur Discord et attend son « go ».

  python agents\\superviseur-vente.py passage [--essai] [--maintenant AAAA-MM-JJTHH:MM]   un passage (tâche serveur, toutes les 30 min)
  python agents\\superviseur-vente.py etat                                                verrou, dernier passage, corrections du jour, ce qui attend un « go »

CORRIGE SEUL (rien ne peut être perdu) : relance une fois par jour un agent planté, silencieux ou bloqué ; ajoute une clé d'état manquante (vide) ;
retire un doublon strictement identique ; remet une liste dans l'ordre des dates.
NE TOUCHE JAMAIS (alerte et attend « go ») : tout fichier d'argent (stripe-alerte-etat.json, montants, prix), les chiffres financiers du tableau de bord,
un prix qui ne correspond pas à OFFRE-REFERENCE.json, un brouillon de B2B\\a-valider contenant une phrase interdite, un lien de paiement inconnu ou un secret,
un fichier illisible, une donnée en double qu'il faudrait choisir, une date illogique.
VERROU : rien n'est corrigé et rien n'est posté tant que go_superviseurs n'est pas true dans un fichier de réglages local (après le « go superviseurs » de Liam). --essai marche toujours."""
import argparse, json, re, sys
from datetime import date, datetime
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import machine as M   # machine active (refus hors du serveur, sauf --essai)

sys.path.insert(0, str(ICI.parent / "harness"))
import superviseurs as S   # moteur commun : réglages, verrou, état, journal, traces, relance, classement sûr / risqué, Discord, fiche a-valider

AGENT, DOMAINE = "superviseur-vente", "Vente"
AGENTS_SUIVIS = ["devis", "chiffres-serveur", "stripe-alerte", "rendez-vous", "reponses"]
DEFAUT = {"heure_resume": "08:45"}
RACINE = ICI.parent.parent
VENTES_JSON = RACINE / "dashboard" / "ventes.json"
A_VALIDER = RACINE / "B2B" / "a-valider"
CLES_ARGENT = ("devis", "paiements", "potentiel")


def controle_devis():
    """devis-etat.json : forme attendue, doublons de la liste « ok_utilises », dates des alertes. Un devis porte un prix : son contenu n'est jamais réécrit."""
    p = ICI / "devis-etat.json"
    out = S.controle_forme("devis", p, {"devis": dict, "alertes": dict, "ok_utilises": list})
    out += S.controle_doublons("devis", p, ["ok_utilises"], "ok_utilises")
    out += S.controle_dates_valides("devis", p, ["alertes"], "alertes de devis")
    d, pb = S.lire_json(p)
    if pb or not isinstance(d, dict) or not isinstance(d.get("devis"), dict): return out
    prix_connus = set()
    try: prix_connus = {int(o["prix_unique_eur"]) for o in S.ref_offre()["offres"].values()}
    except Exception: pass
    mauvais = []
    for cle, v in d["devis"].items():
        if not isinstance(v, dict): continue
        for champ in ("prix", "prix_eur", "montant", "total"):
            x = v.get(champ)
            if isinstance(x, (int, float)) and not isinstance(x, bool) and prix_connus and int(x) not in prix_connus: mauvais.append(str(cle)[:40])
    if mauvais:
        out.append(S.risque("devis", f"{len(mauvais)} devis à un prix absent de OFFRE-REFERENCE.json",
                            f"{', '.join(sorted(set(mauvais))[:5])} : montant jamais corrigé tout seul", cle="devis-etat|prix"))
    return out


def controle_argent():
    """Fichiers d'argent : signalés, jamais corrigés (remettre « dernier_ts » à zéro ferait réannoncer d'anciens paiements)."""
    out = S.controle_financier("stripe-alerte", ICI / "stripe-alerte-etat.json", {"dernier_ts": int, "vus": dict})
    out += S.controle_financier("chiffres-serveur", ICI / "chiffres-serveur-etat.json", {"jours": dict})
    out += S.controle_dates_valides("chiffres-serveur", ICI / "chiffres-serveur-etat.json", ["jours"], "jours déjà écrits dans la feuille")
    return out


def controle_rendez_vous():
    p = ICI / "rendez-vous-etat.json"
    out = S.controle_forme("rendez-vous", p, {"initialise": bool, "reel_initialise": bool, "rdv": dict, "alertes": dict, "echecs": int})
    d, pb = S.lire_json(p)
    if not pb and isinstance(d, dict) and isinstance(d.get("echecs"), int) and d["echecs"] >= 5:
        out.append(S.risque("rendez-vous", f"{d['echecs']} échecs de lecture de l'agenda d'affilée",
                            "l'agent s'arrête de lui-même : vérifier l'adresse iCal dans ses réglages locaux", cle="rendez-vous|echecs"))
    return out


def controle_reponses():
    """reponses-traitees.json : liste des réponses déjà traitées. Un doublon ferait reclasser deux fois la même réponse."""
    return S.controle_doublons("reponses", ICI / "reponses-traitees.json", [], "réponses déjà traitées")


def controle_tableau_bord():
    """Partie financière de dashboard/ventes.json (écrite par le gros PC ; absente sur le serveur = rien à vérifier).
    Chiffre négatif, prix différent de OFFRE-REFERENCE.json ou Potentiel qui ne colle pas à leads × prix : alerte, jamais de correction."""
    d, pb = S.lire_json(VENTES_JSON)
    if pb: return [pb]
    if d is None or not isinstance(d, dict) or not isinstance(d.get("chiffres"), list): return []
    out = []
    par_cle = {str(c.get("cle")): c for c in d["chiffres"] if isinstance(c, dict)}
    for cle in CLES_ARGENT:
        c = par_cle.get(cle) or {}
        v = c.get("valeur")
        if isinstance(v, (int, float)) and not isinstance(v, bool) and v < 0:
            out.append(S.risque("tableau de bord", f"chiffre négatif pour « {cle} » dans ventes.json", f"{v} : chiffre d'argent jamais corrigé tout seul", cle=f"ventes|{cle}|negatif"))
    pot = par_cle.get("potentiel") or {}
    try: prix_ref = int(S.ref_offre()["offres"]["pack"]["prix_unique_eur"])
    except Exception: prix_ref = None
    prix, leads, valeur = pot.get("prix"), pot.get("leads"), pot.get("valeur")
    if prix_ref is not None and isinstance(prix, (int, float)) and not isinstance(prix, bool) and int(prix) != prix_ref:
        out.append(S.risque("tableau de bord", "le prix du Potentiel ne vient pas de OFFRE-REFERENCE.json",
                            "le tableau de bord et la référence de l'offre se contredisent : Liam tranche", cle="ventes|potentiel|prix"))
    if all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in (prix, leads, valeur)) and int(leads) * int(prix) != int(valeur):
        out.append(S.risque("tableau de bord", "le Potentiel ne vaut pas leads × prix",
                            f"{leads} × {prix} ne donne pas {valeur} : calcul à reprendre, rien n'est touché", cle="ventes|potentiel|calcul"))
    return out


def controle_brouillons():
    """Brouillons que Liam doit envoyer ou valider (B2B\\a-valider du jour, B2B\\messages-a-valider.md) : phrase interdite, lien de paiement inconnu, secret.
    Un texte destiné à un client n'est JAMAIS réécrit par un agent : Liam le corrige lui-même."""
    out = []
    fichiers = sorted(A_VALIDER.glob(f"{date.today().isoformat()}*.md")) if A_VALIDER.is_dir() else []
    m = RACINE / "B2B" / "messages-a-valider.md"
    if m.is_file(): fichiers.append(m)
    for f in fichiers:
        if f.name.startswith(date.today().isoformat()) and AGENT in f.name: continue   # sa propre fiche du jour
        try: t = f.read_text(encoding="utf-8", errors="replace")
        except OSError: continue
        for faute in S.fautes_de_texte(t):
            out.append(S.risque("brouillon", f"{faute} dans {f.name}", "brouillon destiné à Liam : jamais réécrit par un agent", cle=f"{f.name}|{faute[:40]}"))
    return out


CONTROLES = [("devis", controle_devis), ("argent", controle_argent), ("rendez-vous", controle_rendez_vous),
             ("réponses", controle_reponses), ("tableau de bord", controle_tableau_bord), ("brouillons", controle_brouillons)]


def cmd_etat(conf):
    r = S.resume_pour_jarvis(AGENT, DOMAINE, conf)
    print(f"Superviseur {DOMAINE} : {r['etat']} ; verrou « go superviseurs » {r['verrou']} ; dernier passage : {r['dernier_passage'] or 'aucun'}.")
    print(f"  agents suivis : {', '.join(AGENTS_SUIVIS)}")
    print(f"  corrections du jour : {len(r['corrections'])}" + ("".join(f"\n    - {x}" for x in r["corrections"][:10]) if r["corrections"] else ""))
    print(f"  en attente d'un « go » : {len(r['bloques'])}" + ("".join(f"\n    - {x}" for x in r["bloques"][:10]) if r["bloques"] else ""))
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog=AGENT, description="Superviseur du domaine Vente : agents à l'heure, données cohérentes, argent jamais touché.")
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
