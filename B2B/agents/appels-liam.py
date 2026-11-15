#!/usr/bin/env python3
"""Agent appels-liam (LM MULTI-SERVICES, décision de Liam du 15/11/2026, à partir du mardi 17/11/2026) : chaque jour ouvré à 07:30, la liste d'appels de Liam
« Appels Liam AAAA-MM-JJ » : 15 lignes (plage 10 à 20 du contrat), d'abord les relances dues (« Je dois réfléchir » depuis 3 jours, puis les reprises de Liam), ensuite des
entreprises neuves. Même registre commun que Sid (B2B\\donnees\\registre-entreprises.json, voir registre.py) : une entreprise donnée à Sid n'est jamais donnée à Liam, et inversement.
Même format que le tableur de Sid (Créneau, Entreprise, Métier, Ville, Téléphone, Détail fiche, Résultat à 8 valeurs, Note). Aucun appel, aucun message à une entreprise.
`envoi_automatique: false` (défaut, appels-liam-config.json) = SIMULATION : CSV local seulement (docs\\sid\\liste-liam-AAAA-MM-JJ.csv), ni Google ni Discord.
La feuille Google est posée à la racine du Drive du compte Google des agents (ou dans dossier_liam_id) : aucun dossier n'est créé.

  python agents\\appels-liam.py jour [--jour AAAA-MM-JJ] [--a-blanc]      le passage du matin : relire les feuilles, liste du jour, feuille Google, corbeille des feuilles lues de plus de 7 jours
  python agents\\appels-liam.py preparer [--jour AAAA-MM-JJ] [--a-blanc] [--hors-ligne]   la liste seule (CSV local)
  python agents\\appels-liam.py etat                                     dernière liste, relances en attente
  python agents\\appels-liam.py annuler [AAAA-MM-JJ] [--a-blanc]         libère les entreprises neuves d'une liste qui n'a pas servi"""
import argparse, csv, importlib.util, io, json, sys
from datetime import date
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
_s = importlib.util.spec_from_file_location("appels_sid", ICI / "appels-sid.py"); A = importlib.util.module_from_spec(_s); _s.loader.exec_module(A)
import registre as RG
P = A.P
ARRET, JOURNAL = ICI / "appels-liam.arret", ICI / "appels-liam-journal.log"


def journaliser(action, detail="", a_blanc=False):
    """Une ligne par action, jamais de numéro, d'e-mail ni de nom d'entreprise."""
    if a_blanc: return
    from datetime import datetime
    with open(JOURNAL, "a", encoding="utf-8") as f: f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} | {action} | {detail}\n")


def alerter(etat, cle, texte, conf, jour, a_blanc=False):
    """Une alerte par motif et par jour sur Discord (bot habituel, garde du harness dans P.discord) ; simulation : journal seulement."""
    k = f"{jour}|{cle}"
    if a_blanc or etat["alertes"].get(k): return
    etat["alertes"][k] = True; A.etat_liam_ecrire(etat); journaliser("alerte", f"{cle} : {texte}"[:300])
    if not conf["envoi_automatique"]: return
    try:
        a = P.acces_discord()
        if a:
            jeton, salon, uid = a
            P.discord(jeton, "POST", f"/channels/{salon}/messages", {"content": f"<@{uid}> **Appels Liam** : {texte}"[:1900], "allowed_mentions": {"users": [uid]}})
    except Exception as e: print(f"  alerte Discord impossible ({type(e).__name__})")


def racine_liam(conf): return conf["dossier_liam_id"] or "root"


def exporter_google(conf, etat, jour, drive, a_blanc):
    """Crée une seule fois la feuille « Appels Liam AAAA-MM-JJ » (racine du Drive ou dossier_liam_id, aucun dossier créé), mise en forme comme celle de Sid."""
    titre = A.TITRE_LIAM.format(jour)
    if not conf["envoi_automatique"] or a_blanc:
        print(f"  Google : {'à blanc' if a_blanc else 'simulation (envoi_automatique=false)'} : serait créée « {titre} »"); return
    f = A.chemin_liam(jour)
    if not f.exists(): raise A.ErreurAgent(f"la liste du {jour} n'existe pas ({f.name}) : rien à envoyer à Google")
    if (drive.compte() or "").lower() != conf["compte_google"].lower(): raise A.ErreurAgent(f"le jeton Google appartient à un autre compte que {conf['compte_google']}")
    jg = etat["google"].setdefault(jour, {})
    if not jg.get("feuille"):
        racine = racine_liam(conf); jg["feuille"] = drive.trouver_feuille(racine, titre) or None
        if not jg["feuille"]:
            with open(f, encoding="utf-8-sig", newline="") as fh: lignes = list(csv.reader(fh, delimiter=";"))
            t = io.StringIO(); csv.writer(t).writerows(lignes)
            jg["feuille"] = drive.creer_feuille(racine, titre, t.getvalue()); A._formater_sans_bloquer(drive, jg["feuille"])
        A.etat_liam_ecrire(etat)
    journaliser("google", f"{jour} : feuille en place"); print(f"  Google : « {titre} » en place")


def _etape(nom, fn, conf, etat, jour, a_blanc):
    try: return fn()
    except A.ErreurAgent as e: print(f"  ! {nom} : {e}"); journaliser("erreur", f"{nom} : {e}"[:200], a_blanc); alerter(etat, nom, f"{nom} : {e}"[:300], conf, jour, a_blanc)
    except Exception as e: print(f"  ! {nom} : {type(e).__name__}"); journaliser("erreur", f"{nom} : {type(e).__name__}", a_blanc); alerter(etat, nom, f"{nom} : échec ({type(e).__name__})", conf, jour, a_blanc)
    return None


def cmd_preparer(conf, jour, a_blanc, hors_ligne=False):
    if ARRET.exists(): raise A.ErreurAgent(f"arrêt de secours présent ({ARRET.name}) : rien n'est généré")
    if not RG.actif(jour): raise A.ErreurAgent(f"la liste de Liam commence le {RG.DEBUT} (registre commun)")
    a_blanc = a_blanc or hors_ligne
    with A.sous_verrou(a_blanc):
        etat = A.etat_liam_lire(); drive = None if (a_blanc or not conf["envoi_automatique"]) else A.ouvrir_drive(conf)
        A.preparer_registre(RG.LIAM, conf, etat, jour, a_blanc, drive, hors_ligne)
        return 0


def cmd_jour(conf, jour, a_blanc):
    if ARRET.exists(): raise A.ErreurAgent(f"arrêt de secours présent ({ARRET.name}) : rien n'est fait")
    nom_jour = A.JOURS_SEMAINE[A.maintenant_paris().weekday()]
    if nom_jour not in conf["jours_appel"]:
        print(f"Jour hors planning ({nom_jour}) : aucune liste générée."); journaliser("jour", f"{jour} : jour hors planning ({nom_jour})", a_blanc); return 0
    if not RG.actif(jour): print(f"Liste de Liam : commence le {RG.DEBUT} (registre commun), rien aujourd'hui."); return 0
    with A.sous_verrou(a_blanc):
        etat = A.etat_liam_lire(); print(f"Passage Liam du {jour}" + (" [à blanc]" if a_blanc else ""))
        drive = None if (a_blanc or not conf["envoi_automatique"]) else A.ouvrir_drive(conf)
        if jour in etat["listes"] or A.chemin_liam(jour).exists(): print(f"  liste du {jour} : déjà préparée"); liste = True
        else: liste = _etape("liste", lambda: A.preparer_registre(RG.LIAM, conf, etat, jour, a_blanc, drive), conf, etat, jour, a_blanc) is not None
        if liste: _etape("google", lambda: exporter_google(conf, etat, jour, drive, a_blanc), conf, etat, jour, a_blanc)
        _etape("nettoyage", lambda: A.nettoyer_feuilles_lues(RG.LIAM, racine_liam(conf), jour, drive, a_blanc, conf["envoi_automatique"]), conf, etat, jour, a_blanc)
        return 0 if liste else 2


def cmd_etat(conf):
    etat = A.etat_liam_lire()
    try: reg = RG.charger()
    except (OSError, ValueError): print("Registre illisible."); return 2
    jour = date.today().isoformat(); attente = [x for x in reg["entreprises"].values() if x.get("statut") == "à reprendre" and x.get("pour") == RG.LIAM]
    print(f"Liste de Liam : {conf['par_liste']} lignes par jour ({'Google' if conf['envoi_automatique'] else 'simulation'}) ; {len(etat['listes'])} liste(s) préparée(s)" + (f", dernière : {max(etat['listes'])}" if etat["listes"] else ""))
    print(f"Relances et reprises en attente pour Liam : {len(attente)} (dont {sum(1 for x in attente if x['retour'] <= jour)} dues aujourd'hui)")
    print(f"Registre : {len(reg['entreprises'])} entreprise(s) déjà données (Sid, Liam, lots d'e-mails)")
    return 0


def cmd_annuler(jour, a_blanc):
    with A.sous_verrou(a_blanc):
        etat = A.etat_liam_lire(); jour = jour or (max(etat["listes"]) if etat["listes"] else None)
        if not jour or jour not in etat["listes"]: raise A.ErreurAgent(f"aucune liste à annuler{' pour le ' + jour if jour else ''}")
        if a_blanc: print(f"Annulation du {jour} [à blanc] : {etat['listes'][jour]['nombre']} entreprise(s) seraient libérées"); return 0
        with RG.verrou():
            reg = RG.charger(); n = RG.liberer(reg, f"{RG.LIAM}|{jour}", jour); RG.sauver(reg)
        del etat["listes"][jour]; etat["google"].pop(jour, None); A.etat_liam_ecrire(etat)
        f = A.chemin_liam(jour)
        if f.exists(): f.replace(A.chemin_liam(jour).with_name(f"liste-liam-{jour}.annulee.csv"))
        journaliser("annuler", f"{jour} : {n} entreprise(s) libérées"); print(f"Liste de Liam du {jour} annulée : {n} entreprise(s) libérées ou remises en attente.")
        return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="appels-liam", description="Liste d'appels du matin pour Liam (aucun envoi).")
    base = argparse.ArgumentParser(add_help=False); base.add_argument("--a-blanc", action="store_true")
    sp = p.add_subparsers(dest="cmd", required=True)
    for nom in ("jour", "preparer"): sp.add_parser(nom, parents=[base]).add_argument("--jour", default=None)
    sp.choices["preparer"].add_argument("--hors-ligne", action="store_true")
    sp.add_parser("etat", parents=[base]); c = sp.add_parser("annuler", parents=[base]); c.add_argument("jour", nargs="?")
    a = p.parse_args(argv); A.M.exiger("appels-liam", a.cmd, getattr(a, "a_blanc", False) or getattr(a, "hors_ligne", False))
    try:
        conf = A.cfg_liam(); jour = A.date_valide(getattr(a, "jour", None) or date.today().isoformat()) if a.cmd in ("jour", "preparer") else None
        if a.cmd == "jour": return cmd_jour(conf, jour, a.a_blanc)
        if a.cmd == "preparer": return cmd_preparer(conf, jour, a.a_blanc, a.hors_ligne)
        if a.cmd == "etat": return cmd_etat(conf)
        return cmd_annuler(A.date_valide(a.jour) if a.jour else None, a.a_blanc)
    except A.ErreurAgent as e: print(f"  ! {e}"); return 2
    except OSError as e: print(f"  ! erreur de fichier : {e.strerror or type(e).__name__}"); return 2


if __name__ == "__main__":
    sys.exit(main())
