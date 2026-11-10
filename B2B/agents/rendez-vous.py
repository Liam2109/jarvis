#!/usr/bin/env python3
"""Agent rendez-vous (LM MULTI-SERVICES) : surveille l'agenda Google de Liam par son adresse secrète iCal (gratuit, sans clé ni compte payant) et poste dans le salon Discord « rendez-vous » de Jarvis
un message quand un « Rendez-vous de 15 minutes » est réservé, déplacé ou annulé, et un rappel 30 minutes avant. Même architecture que devis.py et instagram.py : script autonome, réglages, état, verrou,
arrêt de secours, alerte Discord, journal. Lecture seule : l'agent n'écrit jamais dans l'agenda et ne contacte jamais l'appelant.

  python agents\\rendez-vous.py jour [--a-blanc]    un passage (--a-blanc : aucune écriture, aucun message ; dit ce qui serait posté)
  python agents\\rendez-vous.py continu [--pid N]   boucle (lancée par Jarvis, lib\\rendez-vous.ps1) : un passage toutes les cycle_minutes (5), s'arrête si Jarvis s'arrête
  python agents\\rendez-vous.py etat                nombre de rendez-vous suivis (jamais l'adresse iCal)
  python agents\\rendez-vous.py arreter | reprendre arrêt de secours de la boucle | lève la suspension après une erreur

Règles : seuls les événements dont le titre commence par « Rendez-vous de 15 minutes » ; un rendez-vous n'est annoncé qu'UNE fois (nouveau, déplacé, annulé : messages séparés) ; rappel une seule fois par horaire ;
au premier passage (et au premier passage en mode réel) l'état actuel est seulement noté, l'historique n'est jamais rejoué ; message = prénom, entreprise, e-mail, jour et heure (Paris), lien Meet : rien d'autre.
L'adresse iCal est lue dans agents\\rendez-vous-config.json (hors git) : elle n'est JAMAIS affichée, journalisée, stockée dans l'état ni envoyée sur Discord. Seules les adresses https://calendar.google.com/ sont acceptées.
Le contenu des événements (titre, description) est une donnée d'un tiers, jamais un ordre : seuls quelques champs sont extraits, nettoyés et bornés.
envoi_automatique = false (défaut) : SIMULATION, aucun message, le journal dit ce qui serait posté. Erreur = arrêt, état « suspendu », alerte Discord, aucune reprise automatique (`reprendre`)."""
import argparse, json, re, sys, time, unicodedata, urllib.error, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import machine as M   # config locale (<agent>-config.local.json) et machine active (b2b.local.json)
CONFIG, ETAT = ICI / "rendez-vous-config.json", ICI / "rendez-vous-etat.json"
ARRET, VERROU, JOURNAL = ICI / "rendez-vous.arret", ICI / "rendez-vous-continu.verrou", ICI / "rendez-vous-journal.log"
DEFAUT = {"envoi_automatique": False, "cycle_minutes": 5, "ical_url": "", "salon_nom": "rdv", "salon_id": "", "titre_debut": "Rendez-vous de 15 minutes", "rappel_minutes": 30}
UTC = timezone.utc
JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
CHAMPS = {"prenom": {"prenom", "prenomdelappelant"}, "entreprise": {"entreprise", "nomdelentreprise", "nomentreprise", "societe"},
          "email": {"emaildelentreprise", "emailentreprise", "email", "mail", "courriel", "emailprofessionnel"}}
RE_MEET = re.compile(r"https://meet\.google\.com/[a-z0-9-]{3,40}")
RE_MAIL = re.compile(r"[^\s@<>`*]{1,64}@[^\s@<>`*]{1,200}")


class ErreurSalon(Exception):
    """Salon Discord des rendez-vous introuvable, ambigu ou illisible : rien n'est posté (jamais de repli sur le salon par défaut)."""


class ErreurLecture(Exception):
    """Lecture de l'agenda impossible. definitive : l'adresse est refusée (révoquée, 401/403/404/410) ; sinon panne passagère. Le message ne contient JAMAIS l'adresse."""
    def __init__(self, msg, definitive=False): super().__init__(msg); self.definitive = definitive


# --- réglages, état, journal ---------------------------------------------------------------------------------------
def cfg():
    c = dict(DEFAUT)
    if CONFIG.exists(): c.update({k: v for k, v in json.loads(CONFIG.read_text(encoding="utf-8-sig")).items() if not k.startswith("_")})
    return M.surcharge_locale(CONFIG, c)


def etat_lire():
    e = json.loads(ETAT.read_text(encoding="utf-8")) if ETAT.exists() else {}
    e.setdefault("initialise", False); e.setdefault("reel_initialise", False); e.setdefault("rdv", {}); e.setdefault("alertes", {}); e.setdefault("echecs", 0)
    return e


def etat_ecrire(e): ETAT.write_text(json.dumps(e, ensure_ascii=False, indent=1), encoding="utf-8")


def journaliser(action, detail="", a_blanc=False):
    """Une ligne par action. Jamais l'adresse iCal, un jeton, l'e-mail ni le lien Meet."""
    if a_blanc: return
    with open(JOURNAL, "a", encoding="utf-8") as f: f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} | {action} | {detail}\n")


def _norm(s): return re.sub(r"[^a-z0-9]", "", "".join(c for c in unicodedata.normalize("NFD", (s or "").lower()) if unicodedata.category(c) != "Mn"))


# --- heure de Paris ------------------------------------------------------------------------------------------------------
def paris(dt):
    """datetime aware -> heure de Paris (heure d'été comprise), sans dépendre de la base de fuseaux de Windows. Résultat sans fuseau."""
    u = dt.astimezone(UTC)
    try:
        from zoneinfo import ZoneInfo
        return u.astimezone(ZoneInfo("Europe/Paris")).replace(tzinfo=None)
    except Exception: pass
    n = u.replace(tzinfo=None)
    def dernier_dimanche(m): d = datetime(n.year, m, 31, 1); return d - timedelta(days=(d.weekday() + 1) % 7)
    return n + timedelta(hours=2 if dernier_dimanche(3) <= n < dernier_dimanche(10) else 1)


def _paris_vers_utc(local):
    for h in (1, 2):
        c = (local - timedelta(hours=h)).replace(tzinfo=UTC)
        if paris(c) == local: return c
    return (local - timedelta(hours=1)).replace(tzinfo=UTC)


def quand(dt):
    p = paris(dt); return f"{JOURS[p.weekday()]} {p:%d/%m/%Y} à {p:%H} h {p:%M}"


def _dt(x): return datetime.fromisoformat(x) if isinstance(x, str) else x


# --- lecture du fichier iCal ----------------------------------------------------------------------------------------------
def _proprietes(bloc):
    out = {}
    for l in bloc:
        m = re.match(r'^([A-Za-z0-9-]+)((?:;(?:[^:;"]|"[^"]*")*)*):(.*)$', l)
        if not m: continue
        par = {k.upper(): v.strip('"') for k, v in re.findall(r';([A-Za-z-]+)=("[^"]*"|[^;]*)', m.group(2))}
        out.setdefault(m.group(1).upper(), []).append((par, m.group(3)))
    return out


def _texte(v): return re.sub(r"\\(.)", lambda m: "\n" if m.group(1) in "nN" else m.group(1), v)


def _debut(props):
    if "DTSTART" not in props: return None
    par, v = props["DTSTART"][0]
    if par.get("VALUE", "").upper() == "DATE" or not re.fullmatch(r"\d{8}T\d{6}Z?", v): return None   # journée entière ou format inconnu : pas d'heure, ignoré
    d = datetime.strptime(v.rstrip("Z"), "%Y%m%dT%H%M%S")
    if v.endswith("Z"): return d.replace(tzinfo=UTC)
    if par.get("TZID"):
        try:
            from zoneinfo import ZoneInfo
            return d.replace(tzinfo=ZoneInfo(par["TZID"])).astimezone(UTC)
        except Exception: pass
    return _paris_vers_utc(d)


def lire_ical(texte, prefixe=None):
    """Fichier iCal -> {clé: événement} limité aux titres commençant par `prefixe` ; None si ce n'est pas un iCal complet (jamais pris pour « agenda vide »).
    événement : cle, debut (UTC), annule, prenom, entreprise, email, meet, seq, modif. Doublons : la plus haute SEQUENCE (puis la dernière modification) gagne."""
    prefixe = (prefixe or DEFAUT["titre_debut"]).casefold()
    if not texte or "BEGIN:VCALENDAR" not in texte or "END:VCALENDAR" not in texte: return None
    lignes = re.sub(r"\n[ \t]", "", texte.replace("\r\n", "\n").replace("\r", "\n")).split("\n"); evs, bloc = {}, None
    for l in lignes:
        if l.strip() == "BEGIN:VEVENT": bloc = []
        elif l.strip() == "END:VEVENT" and bloc is not None:
            e = _evenement(bloc, prefixe); bloc = None
            if e and (e["cle"] not in evs or (e["seq"], e["modif"]) > (evs[e["cle"]]["seq"], evs[e["cle"]]["modif"])): evs[e["cle"]] = e
        elif bloc is not None: bloc.append(l)
    return evs


def _evenement(bloc, prefixe):
    p = _proprietes(bloc); titre = _texte(p["SUMMARY"][0][1]).strip() if "SUMMARY" in p else ""
    if not titre.casefold().startswith(prefixe) or "UID" not in p: return None
    debut = _debut(p)
    if not debut: return None
    rec = p["RECURRENCE-ID"][0][1] if "RECURRENCE-ID" in p else ""
    orga = (p["ORGANIZER"][0][1] if "ORGANIZER" in p else "").lower().replace("mailto:", "")
    invite = next(((par, v.lower().replace("mailto:", "")) for par, v in p.get("ATTENDEE", []) if par.get("CUTYPE", "").upper() != "RESOURCE" and v.lower().replace("mailto:", "") != orga), None)
    champs = {}
    for l in _texte(p["DESCRIPTION"][0][1] if "DESCRIPTION" in p else "").split("\n"):
        m = re.match(r"\s*([^:]{1,40}?)\s*:\s*(.+?)\s*$", l)
        if m:
            for cle, noms in CHAMPS.items():
                if _norm(m.group(1)) in noms: champs.setdefault(cle, m.group(2)[:200])
    # Formulaire Google à 3 champs (Prénom, Nom, e-mail) : le nom de l'invité est « Prénom Nom » ; Prénom = APPELANT, Nom = ENTREPRISE appelée, e-mail = e-mail de l'entreprise.
    # Une ligne « Entreprise : » / « Prénom : » / « E-mail : » de la description a priorité ; un nom vide ou ressemblant à une adresse e-mail ne donne ni appelant ni entreprise (jamais inventés).
    toks = (invite[0].get("CN", "") if invite else "").split(); prem = toks[0] if toks and "@" not in toks[0] else ""; reste = " ".join(toks[1:]) if prem else ""
    prenom, entreprise = champs.get("prenom") or prem, champs.get("entreprise") or ("" if "@" in reste else reste)
    mail = champs.get("email", ""); mail = mail if RE_MAIL.fullmatch(mail) else (invite[1] if invite and RE_MAIL.fullmatch(invite[1]) else "")
    meet = RE_MEET.search(" ".join(v for lst in p.values() for _, v in lst))
    return {"cle": f"{p['UID'][0][1].strip()}|{rec}", "debut": debut, "annule": "CANCELLED" in (p["STATUS"][0][1].upper() if "STATUS" in p else ""), "prenom": prenom, "entreprise": entreprise,
            "email": mail, "meet": meet.group(0) if meet else "", "seq": int(p["SEQUENCE"][0][1]) if "SEQUENCE" in p and p["SEQUENCE"][0][1].strip().isdigit() else 0, "modif": p["LAST-MODIFIED"][0][1] if "LAST-MODIFIED" in p else ""}


def telecharger_ical(url):
    """Transport réel (lecture seule). Toute erreur -> ErreurLecture SANS l'adresse (ni dans le message ni dans la chaîne d'exceptions)."""
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Jarvis-rendez-vous/1.0"}), timeout=30) as r: brut = r.read(5_000_001)
    except urllib.error.HTTPError as e: raise ErreurLecture(f"HTTP {e.code}", e.code in (401, 403, 404, 410)) from None
    except Exception as e: raise ErreurLecture(type(e).__name__, False) from None
    if len(brut) > 5_000_000: raise ErreurLecture("fichier trop gros")
    return brut.decode("utf-8", "replace")


# --- messages Discord --------------------------------------------------------------------------------------------------------
def _net(v, n=80): return " ".join(re.sub(r"[`*<>@~|]", "", v or "").split())[:n]


def message(type_, e, avant=None, minutes=30):
    """Appelant (prénom), entreprise, e-mail, jour et heure (Paris), lien Meet : rien d'autre. Champs d'un tiers nettoyés et bornés."""
    tete = {"nouveau": "**Nouveau rendez-vous**", "deplace": "**Rendez-vous déplacé**", "annule": "**Rendez-vous annulé**", "rappel": f"**Rappel : rendez-vous dans {minutes} minutes**"}[type_]
    mail = e.get("email", ""); mail = mail if RE_MAIL.fullmatch(mail) and len(mail) <= 100 else ""
    l = [tete, f"Appelant : {_net(e.get('prenom')) or 'non renseigné'}", f"Entreprise : {_net(e.get('entreprise')) or 'non renseignée'}", f"E-mail : {mail or 'non renseigné'}", f"Quand : {quand(_dt(e['debut']))} (heure de Paris)"]
    if type_ == "deplace" and avant: l.append(f"Avant : {quand(_dt(avant))}")
    if type_ != "annule" and RE_MEET.fullmatch(e.get("meet", "")): l.append(f"Lien Meet : {e['meet']}")
    return "\n".join(l)


def _norm_salon(t):
    """« 📅-rdv » -> « rdv » : minuscules, sans accents, sans emoji ni séparateurs."""
    return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().lower())


def resoudre_salon(conf, jeton, api):
    """Identifiant du salon des rendez-vous : `salon_id` s'il est renseigné (chiffres seulement), sinon le salon texte dont le nom, sans emoji ni accents, est `salon_nom` (« 📅-rdv » = « rdv »).
    Dès la première résolution par nom, l'identifiant trouvé est mémorisé dans `salon_id` (agents\\rendez-vous-config.local.json, hors git) : les passages suivants ne rappellent plus
    /guilds puis /guilds/{id}/channels (cause des 403 Cloudflare en boucle). Introuvable, plusieurs salons du même nom ou liste illisible : ErreurSalon. JAMAIS de repli sur le salon par défaut."""
    sid = str(conf.get("salon_id") or "").strip()
    if sid:
        if re.fullmatch(r"\d{5,25}", sid): return sid
        raise ErreurSalon("salon_id invalide dans agents\\rendez-vous-config.json (chiffres seulement)")
    nom = _norm_salon(conf.get("salon_nom"))
    if not nom: raise ErreurSalon("ni salon_id ni salon_nom dans agents\\rendez-vous-config.json")
    guildes = api(jeton, "GET", "/users/@me/guilds")
    if guildes is None: raise ErreurSalon("liste des serveurs Discord illisible")
    trouves = []
    for g in guildes:
        canaux = api(jeton, "GET", f"/guilds/{g['id']}/channels")
        if canaux is None: raise ErreurSalon("liste des salons Discord illisible")
        trouves += [str(c["id"]) for c in canaux if c.get("type") in (0, 5) and _norm_salon(c.get("name")) == nom]
    if not trouves: raise ErreurSalon(f"salon « {conf['salon_nom']} » introuvable (nom comparé sans emoji ni accents) : renseigner salon_id dans agents\\rendez-vous-config.json")
    if len(trouves) > 1: raise ErreurSalon(f"plusieurs salons nommés « {conf['salon_nom']} » : renseigner salon_id dans agents\\rendez-vous-config.json")
    salon = trouves[0]
    try: M.ecrire_local(CONFIG, {"salon_id": salon})
    except (OSError, ValueError) as e: print(f"  cache du salon « {conf['salon_nom']} » non écrit ({type(e).__name__})")
    return salon


def acces_discord_reel():
    """(jeton, salon par défaut, uid) du bot Jarvis (secrets dans Jarvis\\.env lus par prospection.py, jamais affichés) ou None. Le salon par défaut ne sert qu'aux ALERTES : les messages de
    rendez-vous vont dans le salon résolu par resoudre_salon, jamais dans celui-ci."""
    import prospection as PR
    return PR.acces_discord()


def api_discord_reel(jeton, methode, chemin, corps=None):
    import prospection as PR
    return PR.discord(jeton, methode, chemin, corps)


def alerter_discord(texte):
    try:
        a = acces_discord_reel()
        if not a: return False
        jeton, salon, uid = a
        r = api_discord_reel(jeton, "POST", f"/channels/{salon}/messages", {"content": f"<@{uid}> **Rendez-vous** : {texte}"[:1900], "allowed_mentions": {"users": [uid]}})
        return bool(r and "id" in r)
    except Exception as ex: print(f"  alerte Discord impossible ({type(ex).__name__})"); return False


def alerter(etat, cle, texte, alerte, jour, a_blanc=False):
    """Une alerte par motif et par jour."""
    k = f"{jour}|{cle}"
    if a_blanc or etat["alertes"].get(k): return
    etat["alertes"][k] = True; etat_ecrire(etat); journaliser("alerte", f"{cle} : {texte}"[:300]); alerte(texte)


def _fin(a_blanc):
    def fin(action, detail="", **k):
        journaliser(action, detail, a_blanc); print(f"  Rendez-vous : {action}" + (f" ({detail})" if detail else "")); return {"action": action, **k}
    return fin


def _arret(etat, genre, detail, alerte, jour, a_blanc, fin):
    if not a_blanc: etat["suspendu"] = {"raison": genre, "date": jour, "detail": detail[:200]}; etat_ecrire(etat)
    alerter(etat, f"arret|{genre}", f"Agent arrêté ({genre}) : {detail}. Rien n'est posté tant que ce n'est pas réglé : `python agents\\rendez-vous.py reprendre`.", alerte, jour, a_blanc)
    return fin("arrêt", f"{genre} : {detail}", raison=genre)


# --- le passage ---------------------------------------------------------------------------------------------------------------
def _fiche(ev, statut): return {"debut": ev["debut"].isoformat(), "statut": statut, "annonces": [], "prenom": ev["prenom"], "entreprise": ev["entreprise"], "email": ev["email"], "meet": ev["meet"]}


def passage(conf, a_blanc=False, maintenant=None, lire=None, api=None, acces=None, alerte=None):
    """Un passage. -> {"action": état noté | ok | lecture impossible | arrêt, "messages": [types posté(s) ou qui seraient postés]}."""
    maintenant = maintenant or datetime.now(UTC); jour = str(paris(maintenant).date()); alerte = alerte or alerter_discord; api = api or api_discord_reel; acces = acces or acces_discord_reel
    lire = lire or telecharger_ical; etat = etat_lire(); fin = _fin(a_blanc)
    if etat.get("suspendu"): return fin("arrêt", "suspendu : " + etat["suspendu"]["raison"], raison=etat["suspendu"]["raison"], messages=[])
    url = str(conf.get("ical_url") or "")
    if not url.startswith("https://calendar.google.com/"): return {**_arret(etat, "configuration", "adresse iCal absente ou invalide dans agents\\rendez-vous-config.json (seule une adresse https://calendar.google.com/ est acceptée)", alerte, jour, a_blanc, fin), "messages": []}
    try:
        try:
            evs = lire_ical(lire(url), conf["titre_debut"])
            if evs is None: raise ErreurLecture("fichier iCal invalide ou incomplet")
        except ErreurLecture as e:
            if e.definitive: return {**_arret(etat, "adresse iCal refusée", f"{e} : la copier de nouveau depuis Google Agenda dans agents\\rendez-vous-config.json", alerte, jour, a_blanc, fin), "messages": []}
            etat["echecs"] += 1
            if not a_blanc: etat_ecrire(etat)
            if etat["echecs"] >= 3: alerter(etat, "lecture", f"agenda illisible depuis {etat['echecs']} passages ({e}) : nouvel essai au prochain passage", alerte, jour, a_blanc)
            return {**fin("lecture impossible", str(e), echecs=etat["echecs"]), "messages": []}
        etat["echecs"] = 0
        premier, reel = not etat["initialise"], conf["envoi_automatique"] and not a_blanc
        silencieux = premier or (conf["envoi_automatique"] and not etat["reel_initialise"])   # 1er passage, ou 1er passage réel : état noté, jamais d'historique rejoué
        rdv, annonces, acc = etat["rdv"], [], []

        def poster(texte):
            if not acc:
                try:
                    a = acces()
                    acc.append((a[0], resoudre_salon(conf, a[0], api), a[2]) if a else None)
                except ErreurSalon as e:   # jamais de repli sur le salon par défaut : rien n'est posté, une alerte par jour (journalisée), nouvel essai au passage suivant
                    acc.append(None); alerter(etat, "salon", f"{e} : aucun message de rendez-vous n'est posté (jamais dans le salon par défaut) tant que ce n'est pas réglé", alerte, jour, a_blanc)
            if not acc[0]: return False
            jeton, salon, uid = acc[0]
            r = api(jeton, "POST", f"/channels/{salon}/messages", {"content": f"<@{uid}> {texte}"[:1900], "allowed_mentions": {"users": [uid]}}); return bool(r and "id" in r)

        def emettre(type_, e, maj, avant=None, forcer=False):
            if silencieux and not forcer: maj(); return
            if not reel:
                if not a_blanc: journaliser("serait posté", f"{type_} | {_net(e.get('prenom'), 30)} | {_net(e.get('entreprise'), 40)} | {quand(_dt(e['debut']))}")
                maj(); annonces.append(type_); return
            if poster(message(type_, e, avant, conf["rappel_minutes"])):
                maj(); annonces.append(type_); journaliser("posté", f"{type_} | {_net(e.get('prenom'), 30)} | {quand(_dt(e['debut']))}")
            else: journaliser("message non posté", f"{type_} : Discord n'a pas pris le message ou accès incomplet ; nouvel essai au prochain passage")

        for cle, ev in evs.items():
            rec, iso = rdv.get(cle), ev["debut"].isoformat()
            if ev["debut"] < maintenant - timedelta(days=2): continue
            def pose(ev=ev, cle=cle): rdv[cle] = _fiche(ev, "annulé" if ev["annule"] else "actif")
            if ev["annule"]:
                if rec and rec["statut"] == "actif": emettre("annule", rec, lambda r=rec: r.update(statut="annulé"))
                elif not rec: pose()
            elif not rec or rec["statut"] == "annulé": emettre("nouveau", ev, pose) if ev["debut"] > maintenant else pose()
            elif rec["debut"] != iso:
                def deplace(r=rec, ev=ev, iso=iso): r.update(_fiche(ev, "actif"), annonces=r["annonces"])
                emettre("deplace", ev, deplace, avant=rec["debut"]) if ev["debut"] > maintenant else deplace()
            else: rec.update(prenom=ev["prenom"], entreprise=ev["entreprise"], email=ev["email"], meet=ev["meet"])
        for cle, rec in list(rdv.items()):
            if cle not in evs and rec["statut"] == "actif" and _dt(rec["debut"]) > maintenant: emettre("annule", rec, lambda r=rec: r.update(statut="annulé"))
        for cle, rec in list(rdv.items()):   # rappel : une seule fois par horaire ; il regarde l'avenir, il part aussi au premier passage
            d = _dt(rec["debut"]); k = f"rappel|{rec['debut']}"
            if rec["statut"] == "actif" and d - timedelta(minutes=conf["rappel_minutes"]) <= maintenant < d and k not in rec["annonces"]: emettre("rappel", rec, lambda r=rec, k=k: r["annonces"].append(k), forcer=True)
        for cle in [c for c, r in rdv.items() if _dt(r["debut"]) < maintenant - timedelta(days=2)]: del rdv[cle]
        if not a_blanc:
            if premier: etat["initialise"] = True
            if conf["envoi_automatique"]: etat["reel_initialise"] = True
            etat_ecrire(etat)
        return {**(fin("état noté", f"{len(rdv)} rendez-vous suivis, aucun message pour l'existant") if silencieux else {"action": "ok"}), "messages": annonces}
    except Exception as ex: return {**_arret(etat_lire(), "erreur", type(ex).__name__, alerte, jour, a_blanc, fin), "messages": []}


def reprendre():
    e = etat_lire(); s = e.pop("suspendu", None); etat_ecrire(e); journaliser("reprise", f"suspension levée ({s['raison']})" if s else "rien à lever")
    return f"Suspension levée ({s['raison']}) : la boucle reprendra au prochain lancement." if s else "Aucune suspension."


def cmd_etat():
    e = etat_lire(); a = [r for r in e["rdv"].values() if r["statut"] == "actif"]
    print("Suspendu : " + e["suspendu"]["raison"] if e.get("suspendu") else "Agent actif (aucune suspension).")
    print(f"{len(a)} rendez-vous actif(s) suivi(s), {len(e['rdv']) - len(a)} annulé(s) ; premier passage fait : {'oui' if e['initialise'] else 'non'} ; passage réel fait : {'oui' if e['reel_initialise'] else 'non'}.")


# --- boucle, arrêt de secours --------------------------------------------------------------------------------------------------
def processus_vivant(pid):
    try:
        import ctypes
        k = ctypes.windll.kernel32; h = k.OpenProcess(0x1000, False, int(pid))
        if not h: return False
        code = ctypes.c_ulong(); ok = k.GetExitCodeProcess(h, ctypes.byref(code)); k.CloseHandle(h)
        return bool(ok) and code.value == 259
    except (ImportError, AttributeError):
        import os
        try: os.kill(int(pid), 0); return True
        except OSError: return False


def boucle_active():
    try: return VERROU.exists() and processus_vivant(int(VERROU.read_text(encoding="utf-8").strip()))
    except (ValueError, OSError): return False


def cmd_continu(conf, a_blanc=False, dormir=time.sleep, maintenant=lambda: datetime.now(UTC), lire_ical=None, api=None, acces=None, alerte=None, vivant=None):
    """Un passage toutes les cycle_minutes jusqu'à l'arrêt : `arreter`, Jarvis arrêté (--pid), suspension après une erreur. Jamais de reprise automatique."""
    import os
    if a_blanc: print(f"  [à blanc] boucle rendez-vous : un passage toutes les {conf['cycle_minutes']} min, " + ("messages Discord RÉELS" if conf["envoi_automatique"] else "SIMULATION") + ". Rien lancé."); return "à blanc"
    if boucle_active(): print("Une boucle rendez-vous tourne déjà (rendez-vous-continu.verrou)."); return "déjà lancée"
    prochain, raison = 0, ""

    def bat():
        VERROU.write_text(str(os.getpid()), encoding="utf-8")
        if ARRET.exists(): return "arrêt demandé"
        if vivant and not vivant(): return "Jarvis s'est arrêté"
        s = etat_lire().get("suspendu"); return f"suspendu ({s['raison']})" if s else ""
    try:
        while not raison:
            raison = bat()
            if raison: break
            if maintenant().timestamp() >= prochain:
                try: passage(conf, False, maintenant(), lire_ical, api, acces, alerte)
                except Exception as ex:   # filet : une erreur inattendue arrête l'agent et prévient Liam
                    e = etat_lire(); e["suspendu"] = {"raison": "erreur", "date": str(maintenant().date()), "detail": type(ex).__name__}; etat_ecrire(e)
                    journaliser("erreur", type(ex).__name__); (alerte or alerter_discord)(f"Erreur inattendue ({type(ex).__name__}) : l'agent s'arrête. Vérifie puis `python agents\\rendez-vous.py reprendre`.")
                prochain = maintenant().timestamp() + conf["cycle_minutes"] * 60
            dormir(5)
    finally:
        VERROU.unlink(missing_ok=True)
        if raison.startswith("arrêt"): ARRET.unlink(missing_ok=True)
        journaliser("boucle arrêtée", raison)
    return raison


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Agent rendez-vous LM MULTI-SERVICES (simulation par défaut, lecture seule de l'agenda).")
    ap.add_argument("cmd", choices=["jour", "continu", "etat", "arreter", "reprendre"]); ap.add_argument("--a-blanc", action="store_true"); ap.add_argument("--pid", type=int, default=0); a = ap.parse_args(); M.exiger("rendez-vous", a.cmd, a.a_blanc); conf = cfg()
    if a.cmd == "jour":
        r = passage(conf, a.a_blanc)
        if a.a_blanc and r["messages"]: print("  Serait posté : " + ", ".join(r["messages"]))
    elif a.cmd == "continu": cmd_continu(conf, a.a_blanc, vivant=(lambda: processus_vivant(a.pid)) if a.pid else None)
    elif a.cmd == "etat": cmd_etat()
    elif a.cmd == "arreter":
        if boucle_active(): ARRET.write_text(str(int(time.time())), encoding="utf-8"); print("Arrêt demandé : la boucle s'arrête dans quelques secondes.")
        else: ARRET.unlink(missing_ok=True); VERROU.unlink(missing_ok=True); print("Aucune boucle rendez-vous en cours.")
    else: print(reprendre())


if __name__ == "__main__":
    main()
