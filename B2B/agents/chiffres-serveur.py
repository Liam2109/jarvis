#!/usr/bin/env python3
"""Agent chiffres-serveur (21/11/2026) : tous les soirs à 19:30, UNE ligne dans la feuille Google « Chiffres serveur Jarvis » (créée au premier passage) :
date du jour, nombre de devis envoyés, nombre de paiements reçus. Rien d'autre : aucun montant, aucune donnée client, aucun nom d'entreprise.
Les deux chiffres ne sont lisibles que sur le serveur (devis-etat.json, clé Stripe) : cette feuille est le pont vers le tableau de bord du gros PC, qui la lira
comme il lit déjà les feuilles d'appels de Sid. Aucune IA, aucun token Claude : deux comptages et un ajout de ligne.

  python agents\\chiffres-serveur.py jour [--jour AAAA-MM-JJ] [--essai]   le passage du soir (tâche serveur 19:30)
  python agents\\chiffres-serveur.py etat                                 verrou, jours déjà écrits, dernier passage

VERROU : `jour` n'écrit RIEN dans la vraie feuille tant que go_chiffres_serveur n'est pas true dans le fichier LOCAL de réglages (après le « go chiffres-serveur » de Liam).
--essai marche toujours : il écrit une ligne factice dans la feuille de TEST (« Chiffres serveur Jarvis (essai) »), la relit, vérifie le format, et ne touche jamais la vraie
feuille ni l'état ni le journal. `envoi_automatique: false` (défaut versionné) = SIMULATION : la ligne est affichée, rien n'est écrit dans Google.
Chiffres : devis marqués « envoyé » ce jour-là (devis-etat.json, même définition que la carte « Devis envoyés » du tableau de bord) ; paiements = nombre de paiements
Stripe réussis du jour (resume-sid.stripe_jour, lecture seule, montants jamais repris). Un chiffre indisponible = aucune ligne écrite (jamais de chiffre inventé)."""
import argparse, csv, io, json, sys, time
from datetime import date, datetime
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import machine as M   # réglages locaux de l'agent et machine active (b2b)
import prospection as P   # P.heure_paris (heure de Paris sans dépendre de la base de fuseaux de Windows)

AGENT = "chiffres-serveur"
CONFIG, ETAT, JOURNAL = ICI / "chiffres-serveur-config.json", ICI / "chiffres-serveur-etat.json", ICI / "chiffres-serveur-journal.log"
DEVIS_ETAT = ICI / "devis-etat.json"
DEFAUT = {"go_chiffres_serveur": False, "envoi_automatique": False, "compte_google": "contact.lmsites@gmail.com", "heure_tache": "19:30",
          "feuille": "Chiffres serveur Jarvis", "feuille_essai": "Chiffres serveur Jarvis (essai)"}
ENTETE = ["Date", "Devis envoyés", "Paiements reçus"]


class ErreurAgent(Exception):
    """Problème signalé à Liam (message clair, code de sortie 2) : l'agent s'arrête sans rien écrire de plus."""


# --- les deux chiffres ---------------------------------------------------------------------------------------------
def devis_envoyes(jour):
    """(dispo, nombre | raison) : devis marqués « envoyé » ce jour-là (devis-etat.json, écrit par l'agent devis sur cette machine).
    Fichier absent = aucun devis n'a encore été préparé sur cette machine : 0 (la machine active est vérifiée avant, par M.exiger)."""
    if not DEVIS_ETAT.exists(): return True, 0
    try: e = json.loads(DEVIS_ETAT.read_text(encoding="utf-8"))
    except (OSError, ValueError): return False, f"{DEVIS_ETAT.name} illisible"
    if not isinstance(e, dict): return False, f"{DEVIS_ETAT.name} illisible"
    return True, sum(1 for v in (e.get("devis") or {}).values() if isinstance(v, dict) and (v.get("historique") or {}).get("envoyé") == jour)


def paiements_recus(jour):
    """(dispo, nombre | raison) : nombre de paiements Stripe réussis du jour (resume-sid.stripe_jour, lecture seule). Aucun montant n'est repris ici."""
    try:
        import importlib.util
        s = importlib.util.spec_from_file_location("resume_sid_chiffres", ICI / "resume-sid.py")
        m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    except Exception as ex: return False, f"resume-sid.py illisible ({type(ex).__name__})"
    try: dispo, d = m.stripe_jour(jour)
    except Exception as ex: return False, f"Stripe illisible ({type(ex).__name__})"
    return (True, int(d.get("paiements") or 0)) if dispo else (False, str(d))


def ligne_du_jour(jour, devis, paiements): return [jour, str(devis), str(paiements)]


def entete_csv(): return ",".join(ENTETE) + "\n"


def jours_ecrits(texte):
    """Dates (colonne 1) déjà présentes dans la feuille : la même journée n'est jamais écrite deux fois, même si l'état local a été perdu."""
    out = set()
    for i, r in enumerate(csv.reader(io.StringIO(texte or ""))):
        if i == 0 or not r: continue
        v = (r[0] or "").strip()
        if v: out.add(v)
    return out


def derniere_ligne(texte):
    """Dernière ligne non vide de la feuille, telle que Google la rend (contrôle du format après écriture)."""
    rs = [r for r in csv.reader(io.StringIO(texte or "")) if any((c or "").strip() for c in r)]
    return rs[-1] if rs else []


def format_ok(lu, attendu):
    """Vrai si la ligne relue a bien 3 colonnes et les mêmes valeurs (texte) que la ligne écrite."""
    return len(lu) == len(ENTETE) and [str(c).strip() for c in lu] == [str(c).strip() for c in attendu]


# --- monde extérieur (doublures dans les tests) --------------------------------------------------------------------
def ouvrir_drive(compte):
    import google_sheets as GS
    return GS.ouvrir(compte)


def garde_ok(texte):
    """Garde du harness avant d'écrire dans Google (secret, phrase interdite, lien Stripe, B2B\\STOP). Une panne de la garde n'empêche pas l'écriture, elle est dite."""
    try:
        sys.path.insert(0, str(ICI.parent / "harness")); import garde as G
        ok, raisons = G.verifier_envoi(AGENT, "feuille", texte)
        if not ok: print("  ! garde : écriture BLOQUÉE (" + " ; ".join(x for x in raisons if x.startswith("BLOQUE")) + ")")
        return ok
    except Exception as ex: print(f"  garde indisponible ({type(ex).__name__}) : écriture non contrôlée"); return True


def feuille(drive, titre, creer=True):
    """(id, contenu CSV) de la feuille `titre` à la racine du Drive du compte ; créée avec sa seule ligne d'en-tête si elle n'existe pas (jamais remplacée)."""
    i = drive.trouver_feuille(None, titre)
    if not i:
        if not creer: return None, ""
        i = drive.creer_feuille(None, titre, entete_csv())
        print(f"  feuille « {titre} » créée (en-tête seul)")
    return i, drive.lire_feuille_csv(i)


# --- réglages, état, journal ---------------------------------------------------------------------------------------
def cfg():
    c = json.loads(json.dumps(DEFAUT))
    try:
        if CONFIG.exists(): c.update({k: v for k, v in json.loads(CONFIG.read_text(encoding="utf-8-sig")).items() if not k.startswith("_")})
    except (OSError, ValueError): raise ErreurAgent(f"réglages illisibles : {CONFIG.name}")
    try: M.surcharge_locale(CONFIG, c)
    except M.ErreurLocale as e: raise ErreurAgent(str(e))
    for k in ("go_chiffres_serveur", "envoi_automatique"): c[k] = c.get(k) is True
    c["compte_google"] = str(c.get("compte_google") or DEFAUT["compte_google"]).strip()
    for k in ("feuille", "feuille_essai"): c[k] = str(c.get(k) or DEFAUT[k]).strip() or DEFAUT[k]
    if c["feuille_essai"] == c["feuille"]: raise ErreurAgent("feuille_essai doit être différente de feuille (le mode essai ne touche jamais la vraie feuille)")
    return c


def etat_lire():
    try: e = json.loads(ETAT.read_text(encoding="utf-8")) if ETAT.exists() else {}
    except (OSError, ValueError): raise ErreurAgent(f"état illisible ({ETAT.name}) : rien n'est écrit ; corrigez ou supprimez le fichier à la main")
    if not isinstance(e, dict): raise ErreurAgent(f"état illisible ({ETAT.name}) : rien n'est écrit")
    e.setdefault("jours", {})
    return e


def etat_ecrire(e): ETAT.write_text(json.dumps(e, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")


def journaliser(action, detail=""):
    with open(JOURNAL, "a", encoding="utf-8") as f: f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} | {action} | {detail}\n")


# --- le passage du soir --------------------------------------------------------------------------------------------
def cmd_jour(conf, jour, essai=False, drive=None):
    try: date.fromisoformat(jour)
    except ValueError: raise ErreurAgent(f"jour attendu au format AAAA-MM-JJ (reçu « {jour} »)")
    if not essai and not conf["go_chiffres_serveur"]:
        print("Verrou : Liam n'a pas encore écrit « go chiffres-serveur » (go_chiffres_serveur pas encore à true dans les réglages de cette machine) : rien écrit.")
        journaliser("jour", f"{jour} : verrou « go chiffres-serveur » fermé")
        return 0
    dispo_d, d = devis_envoyes(jour)
    dispo_p, p = paiements_recus(jour)
    if not (dispo_d and dispo_p):
        raison = " ; ".join(x for ok, x in ((dispo_d, f"devis : {d}"), (dispo_p, f"paiements : {p}")) if not ok)
        print(f"  ! chiffre indisponible ({raison}) : aucune ligne écrite (jamais de chiffre inventé)")
        if not essai: journaliser("jour", f"{jour} : aucune ligne ({raison})")
        return 2
    ligne = ligne_du_jour(jour, d, p)
    texte = ",".join(ligne)
    titre = conf["feuille_essai"] if essai else conf["feuille"]
    if not garde_ok(texte):
        if not essai: journaliser("jour", f"{jour} : écriture bloquée par la garde")
        return 2
    if not essai and not conf["envoi_automatique"]:
        print(f"[simulation : envoi_automatique=false] ligne qui serait ajoutée à « {titre} » : {texte}")
        journaliser("jour", f"{jour} : simulation ({d} devis, {p} paiements)")
        return 0
    try:
        dr = drive or ouvrir_drive(conf["compte_google"])
        id_, avant = feuille(dr, titre)
        if jour in jours_ecrits(avant):
            print(f"{jour} : déjà une ligne pour ce jour dans « {titre} » : rien ajouté.")
            if not essai:
                e = etat_lire(); e["jours"].setdefault(jour, f"{datetime.now():%Y-%m-%d %H:%M:%S}"); etat_ecrire(e)
                journaliser("jour", f"{jour} : déjà écrit, rien ajouté")
            return 0
        dr.ajouter_lignes(id_, [ligne])
        lu = derniere_ligne(dr.lire_feuille_csv(id_))
    except Exception as ex:
        print(f"  ! feuille « {titre} » inaccessible ({type(ex).__name__}) : rien écrit, réessayé au prochain passage")
        if not essai: journaliser("jour", f"{jour} : Google indisponible ({type(ex).__name__})")
        return 2
    if not format_ok(lu, ligne):
        print(f"  ! format inattendu après écriture dans « {titre} » : relu « {','.join(str(c) for c in lu)} », attendu « {texte} »")
        if not essai: journaliser("jour", f"{jour} : format relu inattendu")
        return 2
    if essai:
        print(f"[essai] ligne factice ajoutée à la feuille de test « {titre} » : {texte} — format relu conforme ({' / '.join(ENTETE)}) ; la vraie feuille n'a pas été touchée.")
        return 0
    print(f"{jour} : ligne ajoutée à « {titre} » — {d} devis envoyé(s), {p} paiement(s) reçu(s).")
    e = etat_lire(); e["jours"][jour] = f"{datetime.now():%Y-%m-%d %H:%M:%S}"; etat_ecrire(e)
    journaliser("jour", f"{jour} : ligne ajoutée ({d} devis, {p} paiements)")
    return 0


def cmd_etat(conf):
    e = etat_lire(); js = sorted(e["jours"])
    print(f"Verrou « go chiffres-serveur » : {'ouvert' if conf['go_chiffres_serveur'] else 'FERMÉ (rien n’est écrit)'} ; "
          f"envoi_automatique : {'oui' if conf['envoi_automatique'] else 'non (simulation)'}.")
    print(f"Feuille : « {conf['feuille']} » (essai : « {conf['feuille_essai']} »). {len(js)} jour(s) écrit(s) ; dernier : {js[-1] if js else 'aucun'}.")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog=AGENT, description="Une ligne par soir dans la feuille Google « Chiffres serveur Jarvis » : date, devis envoyés, paiements reçus.")
    sp = p.add_subparsers(dest="cmd", required=True)
    j = sp.add_parser("jour"); j.add_argument("--jour", default=None)
    j.add_argument("--essai", "--a-blanc", dest="essai", action="store_true", help="écrit une ligne factice dans la feuille de TEST, vérifie le format, ne touche pas la vraie feuille")
    sp.add_parser("etat")
    args = p.parse_args(argv); M.exiger(AGENT, args.cmd, getattr(args, "essai", False))
    try:
        conf = cfg()
        if args.cmd == "etat": return cmd_etat(conf)
        return cmd_jour(conf, args.jour or P.heure_paris().date().isoformat(), args.essai)
    except ErreurAgent as e:
        print(f"  ! {e}"); return 2
    except OSError as e:
        print(f"  ! erreur de fichier : {e.strerror or type(e).__name__}"); return 2


if __name__ == "__main__":
    _t0 = time.time(); _code = main()
    if sys.argv[1:2] == ["jour"] and not {"--essai", "--a-blanc"} & set(sys.argv):   # trace du harness (B2B\logs\agents\chiffres-serveur), jamais bloquante
        try:
            sys.path.insert(0, str(ICI.parent / "harness")); import traces
            traces.ecrire(AGENT, "jour", "terminé" if _code == 0 else "échec", time.time() - _t0, ok=_code == 0, erreur=None if _code == 0 else f"code {_code}")
        except Exception: pass
    sys.exit(_code)
