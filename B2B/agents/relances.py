#!/usr/bin/env python3
"""Agent relances (LM MULTI-SERVICES, 18/11/2026) : chaque jour ouvré à 08:00 (commande « rappel » : leads de la file dont la relance est due ou en retard) puis à 08:30 (commande « jour »), UN message Discord « À rappeler aujourd'hui » pour Liam avec les leads chauds notés par Sid qu'il doit
rappeler lui-même. Il ne contacte personne d'autre que Liam. Aucune IA, aucun token : lecture des feuilles Google et calcul de dates.

  python agents\\relances.py jour [--jour AAAA-MM-JJ] [--essai]     le passage du jour (tâche serveur 08:30) ; --essai : lit les vraies feuilles, affiche le message, n'écrit et n'envoie rien
  python agents\\relances.py rappel [--jour AAAA-MM-JJ] [--essai]   08:00 : leads de la file (donnees\\leads-chauds.json) dont la relance est due aujourd'hui ou en retard, avec leur dernière mise à jour
  python agents\\relances.py etat                                  nombre de relances déjà annoncées, dernier envoi

Règles (décision de Liam du 18/11/2026) :
 - Source : TOUTES les feuilles « Appels Sid AAAA-MM-JJ » du dossier de Sid (dossier_sid_id d'appels-sid), lecture seule. Date de l'appel = date du nom de la feuille.
 - Lead chaud : Résultat « À rappeler » ou « Je dois réfléchir ». Un lead = un numéro de téléphone (sans numéro : ignoré, rien n'est deviné).
 - Rythme : relance 1 au 3e jour ouvré après l'appel, relance 2 au 7e, puis le lead est classé. Note de Sid contenant « moyen terme » ou « semaines » : une seule relance, au 15e.
   Jours ouvrés = lundi-vendredi hors jours fériés français. Un passage manqué est rattrapé le jour ouvré suivant (la relance la plus récente déjà due seulement).
 - Exclusion : une feuille PLUS RÉCENTE note ce numéro « RDV pris », « Non catégorique », « Trop cher », « Déjà un site » ou « Pas le temps ».
 - Un lead n'est annoncé qu'une fois par relance (relances-etat.json) ; aucun message s'il n'y a rien ; rien le week-end ni un jour férié.
`envoi_automatique: false` (défaut versionné) = SIMULATION : rien sur Discord. Le journal ne contient ni nom ni numéro."""
import argparse, csv, io, json, re, sys, time, unicodedata
from datetime import date, datetime, timedelta
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import machine as M   # config locale (relances-config.local.json) et machine active (b2b.local.json)
import prospection as P   # P.acces_discord / P.discord (garde du harness avant chaque POST), P.heure_paris

AGENT = "relances"
CONFIG, ETAT, JOURNAL = ICI / "relances-config.json", ICI / "relances-etat.json", ICI / "relances-journal.log"
APPELS_SID_CONFIG = ICI / "appels-sid-config.json"
DEFAUT = {"envoi_automatique": False, "compte_google": "contact.lmsites@gmail.com", "heure_tache": "08:00"}
CHAUDS = {"À rappeler", "Je dois réfléchir"}
EXCLUS = {"RDV pris", "Non catégorique", "Trop cher", "Déjà un site", "Pas le temps"}
RYTHME = [(1, 3), (2, 7)]          # (numéro de relance, n-ième jour ouvré après l'appel)
RYTHME_MOYEN_TERME = [(1, 15)]
MOTS_MOYEN_TERME = ("moyen terme", "semaines")
TITRE = re.compile(r"Appels Sid (\d{4}-\d{2}-\d{2})")
GARDE_JOURS = 150


class ErreurAgent(Exception):
    """Problème signalé à Liam (message clair, code de sortie 2) : l'agent s'arrête sans rien écrire de plus."""


# --- calendrier ---------------------------------------------------------------------------------------------------
def paques(an):
    """Dimanche de Pâques (calendrier grégorien, algorithme de Meeus/Jones/Butcher)."""
    a, b, c = an % 19, an // 100, an % 100
    d, e = b // 4, b % 4
    g = (8 * b + 13) // 25; h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7; m = (a + 11 * h + 19 * l) // 433
    mois = (h + l - 7 * m + 90) // 25; jour = (h + l - 7 * m + 33 * mois + 19) % 32
    return date(an, mois, jour)


def feries(an):
    """Les 11 jours fériés nationaux français (hors Alsace-Moselle)."""
    p = paques(an)
    return {date(an, 1, 1), p + timedelta(days=1), date(an, 5, 1), date(an, 5, 8), p + timedelta(days=39), p + timedelta(days=50),
            date(an, 7, 14), date(an, 8, 15), date(an, 11, 1), date(an, 11, 11), date(an, 12, 25)}


def est_ouvre(d): return d.weekday() < 5 and d not in feries(d.year)


def ouvre_apres(d, n):
    """Le n-ième jour ouvré après la date d (d exclu)."""
    while n > 0:
        d += timedelta(days=1)
        if est_ouvre(d): n -= 1
    return d


# --- lecture des feuilles de Sid ----------------------------------------------------------------------------------
def tel_cle(brut):
    """Numéro -> 10 chiffres (« 0612345678 ») ; +33 / 0033 acceptés ; « » si ce n'est pas un numéro français."""
    d = re.sub(r"\D", "", str(brut or ""))
    if d.startswith("0033"): d = "0" + d[4:]
    elif d.startswith("33") and len(d) == 11: d = "0" + d[2:]
    return d if re.fullmatch(r"0\d{9}", d) else ""


def tel_lisible(t): return " ".join(t[k:k + 2] for k in range(0, 10, 2)) if len(t) == 10 else t


def lignes_feuille(texte):
    """CSV d'une feuille « Appels Sid » -> [{nom, ville, tel, resultat, note}] (colonnes repérées par l'en-tête ; feuille sans « Résultat » : aucune ligne)."""
    rows = list(csv.reader(io.StringIO(texte or "")))
    if not rows or "Résultat" not in rows[0]: return []
    e = rows[0]; ix = {k: (e.index(c) if c in e else None) for k, c in (("nom", "Entreprise"), ("ville", "Ville"), ("tel", "Téléphone"), ("resultat", "Résultat"), ("note", "Note"))}
    v = lambda r, k: r[ix[k]].strip() if ix[k] is not None and ix[k] < len(r) else ""
    return [{k: v(r, k) for k in ix} for r in rows[1:]]


def lire_feuilles(drive, racine):
    """[(jour, lignes)] de toutes les feuilles « Appels Sid AAAA-MM-JJ » du dossier de Sid, par date croissante. Lecture seule."""
    out = []
    for i, nom in drive.lister_feuilles(racine):
        m = TITRE.fullmatch(nom or "")
        if m: out.append((m.group(1), lignes_feuille(drive.lire_feuille_csv(i))))
    return sorted(out, key=lambda x: x[0])


def _plat(t): return "".join(c for c in unicodedata.normalize("NFD", str(t).lower()) if unicodedata.category(c) != "Mn")


def leads(feuilles):
    """{tel: lead} : dernier résultat chaud de chaque numéro, sauf si une feuille plus récente l'exclut. lead = nom, ville, resultat (la raison : « À rappeler » ou « Je dois réfléchir »), note, appel (date), moyen_terme."""
    chauds, exclus = {}, {}
    for jour, lignes in feuilles:
        for l in lignes:
            t = tel_cle(l["tel"])
            if not t: continue
            if l["resultat"] in CHAUDS: chauds[t] = {"nom": l["nom"], "ville": l["ville"], "resultat": l["resultat"], "note": l["note"], "appel": jour, "moyen_terme": any(m in _plat(l["note"]) for m in MOTS_MOYEN_TERME)}
            elif l["resultat"] in EXCLUS: exclus[t] = max(jour, exclus.get(t, ""))
    return {t: x for t, x in chauds.items() if not (t in exclus and exclus[t] > x["appel"])}


def cle_annonce(t, lead, n): return f"{t}|{lead['appel']}|{n}"


def etape(lead, jour):
    """(numéro de relance, date prévue, déjà due ?) d'un lead au `jour` : la relance la plus récente déjà due, sinon la prochaine à venir. Seule définition du rythme (lue aussi par le tableau de bord)."""
    rythme = RYTHME_MOYEN_TERME if lead["moyen_terme"] else RYTHME
    j = date.fromisoformat(jour)
    dates = [(n, ouvre_apres(date.fromisoformat(lead["appel"]), k)) for n, k in rythme]
    dues = [x for x in dates if x[1] <= j]
    n, d = dues[-1] if dues else dates[0]
    return n, d.isoformat(), bool(dues)


def a_rappeler(tous, jour, etat):
    """[(tel, lead, n)] à annoncer le `jour` : la relance la plus récente déjà due, si elle n'a jamais été annoncée et si aucune relance plus tardive ne l'a déjà été."""
    out = []
    for t, x in sorted(tous.items(), key=lambda kv: (kv[1]["appel"], kv[1]["nom"])):
        n, prevue, due = etape(x, jour)
        if not due or prevue != jour: continue   # 24/11/2026 : seulement les leads datés EXACTEMENT d'aujourd'hui ; le retard est dans le message de 08:00 (commande « rappel »)
        rythme = RYTHME_MOYEN_TERME if x["moyen_terme"] else RYTHME
        if any(cle_annonce(t, x, m) in etat["annonces"] for m, _ in rythme if m >= n): continue
        out.append((t, x, n))
    return out


def message(liste):
    l = [f"**À rappeler aujourd'hui** ({len(liste)} lead(s) chaud(s) notés par Sid) :"]
    for t, x, n in liste:
        l.append(f"- {x['nom'] or '(nom absent)'}" + (f" ({x['ville']})" if x["ville"] else "") + f" — {tel_lisible(t)} — relance {n}"
                 + (" (moyen terme)" if x["moyen_terme"] else "") + f" — appel du {date.fromisoformat(x['appel']):%d/%m} — note de Sid : {x['note'] or '(vide)'}")
    return "\n".join(l)


def leads_dus_file(jour, lire=None):
    """[lead] de la file des leads chauds (leads_chauds.py) dont la relance est due le `jour` ou en retard : sans date de relance, rien (jamais deviné). Les plus en retard d'abord."""
    if lire is None:
        import leads_chauds as LC; lire = LC.lire
    file = lire() or []
    return sorted((l for l in file if l.get("jour") and l["jour"] <= jour), key=lambda l: (l["jour"], l.get("nom", "")))


def message_rappel(dus, jour):
    """Message de 08:00 : nom, téléphone, date de relance (retard en jours) et date de dernière mise à jour de chaque lead."""
    l = [f"**À rappeler aujourd'hui** ({len(dus)} lead(s) dont la relance est due ou en retard) :"]
    for x in dus:
        retard = (date.fromisoformat(jour) - date.fromisoformat(x["jour"])).days
        maj = f" — dernière mise à jour le {date.fromisoformat(x['resultat_le']):%d/%m}" if x.get("resultat_le") else " — dernière mise à jour inconnue"
        l.append(f"- {x.get('nom') or '(nom absent)'}" + (f" ({x['ville']})" if x.get("ville") else "") + f" — {tel_lisible(x.get('tel', ''))} — "
                 + ("relance prévue aujourd'hui" if retard == 0 else f"en retard de {retard} j (prévue le {date.fromisoformat(x['jour']):%d/%m})") + maj)
    return "\n".join(l)


def morceaux(texte, n=1800):
    """Découpe un message trop long pour Discord aux fins de ligne (jamais une ligne coupée)."""
    out, cur = [], ""
    for ligne in texte.split("\n"):
        if cur and len(cur) + len(ligne) + 1 > n: out.append(cur); cur = "(suite) "
        cur += ("\n" if cur and not cur.endswith(" ") else "") + ligne
    return out + [cur] if cur else out


# --- monde extérieur (doublures dans les tests) -------------------------------------------------------------------
def ouvrir_drive(compte):
    import google_sheets as GS
    return GS.ouvrir(compte)


def alerter_discord(texte):
    """Salon Discord habituel des agents (même accès que les autres agents, jeton lu dans Jarvis\\.env, jamais affiché) ; garde du harness avant chaque POST."""
    try:
        a = P.acces_discord()
        if not a: return False
        jeton, salon, uid = a
        r = P.discord(jeton, "POST", f"/channels/{salon}/messages", {"content": f"<@{uid}> {texte}"[:1900], "allowed_mentions": {"users": [uid]}})
        return bool(r and "id" in r)
    except Exception as ex: print(f"  alerte Discord impossible ({type(ex).__name__})"); return False


# --- réglages, état, journal --------------------------------------------------------------------------------------
def cfg():
    c = dict(DEFAUT)
    try:
        if CONFIG.exists(): c.update({k: v for k, v in json.loads(CONFIG.read_text(encoding="utf-8-sig")).items() if not k.startswith("_")})
    except (OSError, ValueError): raise ErreurAgent(f"réglages illisibles : {CONFIG.name}")
    try: M.surcharge_locale(CONFIG, c)
    except M.ErreurLocale as e: raise ErreurAgent(str(e))
    c["envoi_automatique"] = c.get("envoi_automatique") is True
    c["compte_google"] = str(c.get("compte_google") or DEFAUT["compte_google"]).strip()
    try: c["dossier_sid_id"] = str(M.lire_fusionnee(APPELS_SID_CONFIG).get("dossier_sid_id") or "").strip()
    except Exception: c["dossier_sid_id"] = ""
    return c


def etat_lire():
    try: e = json.loads(ETAT.read_text(encoding="utf-8")) if ETAT.exists() else {}
    except (OSError, ValueError): raise ErreurAgent(f"état illisible ({ETAT.name}) : rien n'est écrit ; corrigez ou supprimez le fichier à la main")
    if not isinstance(e, dict): raise ErreurAgent(f"état illisible ({ETAT.name}) : rien n'est écrit")
    e.setdefault("annonces", {}); e.setdefault("envois", {})
    return e


def etat_ecrire(e): ETAT.write_text(json.dumps(e, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")


def journaliser(action, detail=""):
    with open(JOURNAL, "a", encoding="utf-8") as f: f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} | {action} | {detail}\n")


# --- le passage du jour -------------------------------------------------------------------------------------------
def cmd_jour(conf, jour, essai, drive=None):
    if not est_ouvre(date.fromisoformat(jour)):
        print(f"{jour} : jour non ouvré (week-end ou férié), aucune relance.")
        if not essai: journaliser("jour", f"{jour} : jour non ouvré")
        return 0
    if not conf["dossier_sid_id"]:
        print("  ! dossier de Sid inconnu (dossier_sid_id d'appels-sid) : rien à lire")
        if not essai: journaliser("jour", "dossier de Sid inconnu")
        return 2
    etat = etat_lire()
    try:
        d = drive or ouvrir_drive(conf["compte_google"]); feuilles = lire_feuilles(d, conf["dossier_sid_id"])
    except Exception as ex:
        print(f"  ! feuilles de Sid illisibles ({type(ex).__name__}) : rien envoyé")
        if not essai: journaliser("jour", f"feuilles illisibles ({type(ex).__name__})")
        return 2
    liste = a_rappeler(leads(feuilles), jour, etat)
    if not liste:
        print(f"{jour} : {len(feuilles)} feuille(s) lue(s), aucun lead à rappeler aujourd'hui : aucun message.")
        if not essai: journaliser("jour", f"{jour} : {len(feuilles)} feuille(s), rien à rappeler")
        return 0
    texte = message(liste)
    if essai:
        print(f"[essai] {len(feuilles)} feuille(s) lue(s) ; message qui serait envoyé (rien écrit, rien envoyé) :\n{texte}"); return 0
    if conf["envoi_automatique"]:
        ok = all(alerter_discord(m) for m in morceaux(texte)); print(texte); print("  (posté sur Discord)" if ok else "  ! Discord : non envoyé, réessayé au prochain passage")
        if not ok: journaliser("jour", f"{jour} : Discord indisponible, {len(liste)} relance(s) non annoncée(s)"); return 2
    else:
        print("[simulation : envoi_automatique=false] " + texte)
    for t, x, n in liste: etat["annonces"][cle_annonce(t, x, n)] = jour
    etat["envois"][jour] = len(liste)
    limite = (date.fromisoformat(jour) - timedelta(days=GARDE_JOURS)).isoformat()
    etat["annonces"] = {k: v for k, v in etat["annonces"].items() if v >= limite}; etat["envois"] = {k: v for k, v in etat["envois"].items() if k >= limite}
    etat_ecrire(etat)
    journaliser("jour", f"{jour} : {len(liste)} relance(s) annoncée(s) ({sum(1 for *_, n in liste if n == 1)} n°1, {sum(1 for *_, n in liste if n == 2)} n°2)")
    return 0


def cmd_rappel(conf, jour, essai, lire=None):
    """Passe de 08:00 : un message Discord « À rappeler aujourd'hui » avec les leads de la file dont la relance est due aujourd'hui ou en retard, avec leur date de dernière mise à jour.
    Aucun contact client, aucune écriture (pas d'état : le message est refait chaque jour tant que le lead est en retard). Simulation tant que envoi_automatique est false."""
    if not est_ouvre(date.fromisoformat(jour)):
        print(f"{jour} : jour non ouvré, aucun rappel."); return 0
    try: dus = leads_dus_file(jour, lire)
    except (OSError, ValueError, ImportError) as ex:
        print(f"  ! file des leads chauds illisible ({type(ex).__name__}) : rien envoyé")
        if not essai: journaliser("rappel", "file illisible")
        return 2
    if not dus:
        print(f"{jour} : aucun lead dû ni en retard : aucun message.")
        if not essai: journaliser("rappel", f"{jour} : rien à rappeler")
        return 0
    texte = message_rappel(dus, jour)
    if essai: print("[essai] message qui serait envoyé (rien envoyé) :\n" + texte); return 0
    if conf["envoi_automatique"]:
        ok = all(alerter_discord(m) for m in morceaux(texte)); print(texte); print("  (posté sur Discord)" if ok else "  ! Discord : non envoyé")
        journaliser("rappel", f"{jour} : {len(dus)} lead(s) {'annoncé(s)' if ok else 'non annoncé(s), Discord indisponible'}")
        return 0 if ok else 2
    print("[simulation : envoi_automatique=false] " + texte); journaliser("rappel", f"{jour} : {len(dus)} lead(s) (simulation)"); return 0


def cmd_etat():
    e = etat_lire()
    print(f"{len(e['annonces'])} relance(s) annoncée(s) mémorisée(s) ; dernier envoi : {max(e['envois']) if e['envois'] else 'aucun'}."); return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog=AGENT, description="Liste quotidienne des leads chauds à rappeler par Liam (Discord, aucun contact client).")
    sp = p.add_subparsers(dest="cmd", required=True)
    j = sp.add_parser("jour"); j.add_argument("--jour", default=None); j.add_argument("--essai", "--a-blanc", dest="essai", action="store_true", help="lit, affiche, n'écrit et n'envoie rien")
    r = sp.add_parser("rappel"); r.add_argument("--jour", default=None); r.add_argument("--essai", "--a-blanc", dest="essai", action="store_true", help="affiche, n'envoie rien")
    sp.add_parser("etat")
    args = p.parse_args(argv); M.exiger(AGENT, args.cmd, getattr(args, "essai", False))
    try:
        if args.cmd == "etat": return cmd_etat()
        if args.cmd == "rappel": return cmd_rappel(cfg(), args.jour or P.heure_paris().date().isoformat(), args.essai)
        return cmd_jour(cfg(), args.jour or P.heure_paris().date().isoformat(), args.essai)
    except ErreurAgent as e:
        print(f"  ! {e}"); return 2
    except OSError as e:
        print(f"  ! erreur de fichier : {e.strerror or type(e).__name__}"); return 2


if __name__ == "__main__":
    _t0 = time.time(); _code = main()
    if sys.argv[1:2] in (["jour"], ["rappel"]) and not {"--essai", "--a-blanc"} & set(sys.argv):   # trace du harness (B2B\logs\agents\relances), jamais bloquante
        try: sys.path.insert(0, str(ICI.parent / "harness")); import traces; traces.ecrire(AGENT, sys.argv[1], "terminé" if _code == 0 else "échec", time.time() - _t0, ok=_code == 0, erreur=None if _code == 0 else f"code {_code}")
        except Exception: pass
    sys.exit(_code)
