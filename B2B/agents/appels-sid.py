#!/usr/bin/env python3
"""Agent appels-sid (LM MULTI-SERVICES) : prépare chaque matin la liste d'appels de Sid, 50 à 60 entreprises JAMAIS appelées, et alimente lui-même sa réserve de numéros.
Aucun message n'est envoyé à une entreprise ni à Sid, aucune API payante. Même modèle que devis et rendez-vous : script autonome, réglages (appels-sid-config.json), état (appels-sid-etat.json),
verrou, arrêt de secours, alerte Discord, journal, tests écrits avant le code. `envoi_automatique: false` (défaut) = SIMULATION : ni Google, ni partage, ni Discord (le journal dit ce qui serait fait).

  python agents\\appels-sid.py jour [--jour AAAA-MM-JJ] [--a-blanc]       le passage du matin : sourcer, préparer la liste, dossier + feuille Google, alerte de réserve (c'est ce que lance la tâche planifiée)
  python agents\\appels-sid.py preparer [--jour AAAA-MM-JJ] [--a-blanc]   seulement la liste du jour (docs\\sid\\liste-sid-AAAA-MM-JJ.csv) ; --a-blanc : affiche sans rien écrire
  python agents\\appels-sid.py sourcer [--jour AAAA-MM-JJ] [--a-blanc] [--dept 27] [--simulation]
                                                                          cherche de nouvelles entreprises AVEC téléphone dans toute la Normandie : OpenStreetMap (Overpass, une requête par département et par métier)
                                                                          + SIRENE (API officielle « Recherche d'entreprises », entreprises actives) dont le téléphone est lu sur la fiche OpenStreetMap ou le site public ;
                                                                          --dept limite à un département ; --simulation : aucun réseau, données fictives, rien n'est écrit
  python agents\\appels-sid.py etat                                       réserve par métier, dernière liste, Google, liste de Liam
  python agents\\appels-sid.py annuler [AAAA-MM-JJ] [--force] [--a-blanc] libère les entreprises d'une liste non utilisée (la plus récente par défaut)
  python agents\\appels-sid.py google-autoriser                           autorisation Google (Drive) du compte contact.lmsites@gmail.com, une seule fois
  python agents\\appels-sid.py rediriger-liste | rendre-liste [--a-blanc]  la liste d'appels quotidienne de Liam n'est plus produite (tout va à Sid) | est rendue à Liam
  python agents\\appels-sid.py installer-tache | retirer-tache [--oui]     tâche planifiée Windows de 8 h 00 : sans --oui, affiche seulement la commande

Sélection (la logique de prospection.py est réutilisée, pas recopiée : exclusions STOP / refus, exclus-emails.json, listes d'appels, zone et vagues, proximité de Rouen) :
métiers restaurant, coiffeur, plombier-chauffagiste, électricien seulement ; Normandie (départements 14, 27, 50, 61, 76) ; téléphone français valide ; jamais appelée ni donnée à Sid (ni son numéro) ; les entreprises des listes docs\\liste-appels-*.md
JAMAIS appelées sont reprises ; ni STOP, refus, exclue, hors zone, ni déjà contactée par e-mail. Une entreprise sortie est marquée dans l'état et ne ressort JAMAIS (sauf après `annuler`)."""
import argparse, contextlib, csv, io, json, math, os, re, subprocess, sys, time, urllib.parse
from datetime import date, datetime
from pathlib import Path

ICI = Path(__file__).resolve().parent
RACINE = ICI.parent
sys.path.insert(0, str(ICI))
import machine as M   # config locale (<agent>-config.local.json) et machine active (b2b.local.json)
import prospection as P, redaction as R, suivi as S, zone as ZN

SORTIE = RACINE / "docs" / "sid"
MAPS = RACINE / "prospects_maps.csv"
CONFIG, ETAT, VERROU, ARRET, JOURNAL = (ICI / "appels-sid-config.json", ICI / "appels-sid-etat.json", ICI / "appels-sid.verrou", ICI / "appels-sid.arret", ICI / "appels-sid-journal.log")
PROSPECTION_CONFIG = ICI / "prospection-config.json"
NORMANDIE = ("76", "27", "14", "50", "61")   # Seine-Maritime, Eure, Calvados, Manche, Orne : du plus proche de Rouen au plus lointain
NOMS_DEPT = {"14": "Calvados", "27": "Eure", "50": "Manche", "61": "Orne", "76": "Seine-Maritime"}
# Codes NAF (SIRENE) des quatre métiers : plombier-chauffagiste = installation d'eau et de gaz (43.22A) + équipements thermiques et climatisation (43.22B) ; restaurant = traditionnel (56.10A) + rapide (56.10C)
NAF_SID = {"plombier": ["43.22A", "43.22B"], "electricien": ["43.21A"], "coiffeur": ["96.02A"], "restaurant": ["56.10A", "56.10C"]}
ZONE = {"departements": list(NORMANDIE)}   # remplacé par cfg() : les départements dans lesquels l'agent cherche et accepte une entreprise
DEFAUT = {"envoi_automatique": False, "par_liste": 55, "repartition": {"plombier": 12, "electricien": 12, "coiffeur": 13, "restaurant": 18},
          "cible_reserve": 220, "seuil_alerte": 110, "sourcing_requetes_max": 6, "pause_overpass_s": 15, "sourcing_refaire_jours": 30,
          "zone": "Normandie", "departements": list(NORMANDIE), "sirene_actif": True, "sirene_requetes_max": 12, "sirene_pages_max": 4, "sirene_sites_max": 30, "pause_sirene_s": 1, "pause_site_s": 2,
          "avec_site": False, "partager_avec": "", "compte_google": "contact.lmsites@gmail.com", "heure_tache": "08:00"}
MIN_LISTE, MAX_LISTE = 50, 60
VERROU_MAX_S = 3 * 3600   # un verrou plus vieux est celui d'un processus bloqué : repris
TACHE = "Jarvis-AppelsSid"
HEURE_JAMAIS = "99:99"    # liste_appels_heure de prospection : jamais atteinte, donc plus de liste d'appels pour Liam
# Ordre de la journée de Sid : artisans du bâtiment (avant 9 h ou vers 17 h), coiffeurs (milieu de matinée), restaurants (14 h – 16 h). Créneaux indicatifs, non mesurés.
CRENEAUX = {"plombier": "avant 9 h ou vers 17 h (hors chantier)", "electricien": "avant 9 h ou vers 17 h (hors chantier)",
            "coiffeur": "milieu de matinée, 10 h – 11 h 30, mardi au jeudi (pas le samedi)", "restaurant": "14 h – 16 h, entre deux services (pas le week-end)"}
RANG = {"plombier": 0, "electricien": 0, "coiffeur": 1, "restaurant": 2}
NOMS = {"plombier": "Plombier-chauffagiste", "electricien": "Électricien", "coiffeur": "Coiffeur", "restaurant": "Restaurant"}
PRIORITE = ["plombier", "electricien", "coiffeur", "restaurant"]   # le sourcing commence par les métiers sans numéro
LABELS = {"plombier": "plombier-chauffagiste", "electricien": "électricien", "coiffeur": "coiffeur", "restaurant": "restaurant"}   # libellés de prospection.OSM_METIERS
COLONNES = ["#", "Nom", "Ville", "Téléphone", "Métier", "Créneau conseillé", "Constat vérifié", "Page d'exemple", "Appelé", "Répondu", "Rendez-vous pris", "Refus", "Remarque"]
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")


class ErreurAgent(Exception):
    """Problème signalé à Liam (message clair, code de sortie 2) : l'agent s'arrête sans rien écrire de plus."""


class ErreurSourcing(Exception):
    """Le sourcing a échoué (type de l'erreur seulement, jamais le détail)."""


# --- points d'accès au monde extérieur (remplacés par des doublures dans les tests) ---------------------------------------
def appel_reseau(requete):
    """Une requête Overpass (lecture seule, données ouvertes) : prospection.appel_overpass gère l'identification, les nouveaux essais après un refus (429, 5xx) et les limites de débit."""
    return P.appel_overpass(requete, dormir=dormir)


def dormir(s): time.sleep(s)


def ouvrir_drive(conf):
    import google_sheets as GS
    return GS.ouvrir(conf["compte_google"])


def executer(commande):
    """Exécute une commande PowerShell : (code, message d'erreur court)."""
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", commande], capture_output=True, text=True, timeout=120)
    return r.returncode, " ".join((r.stderr or r.stdout or "").split())[:200]


def alerter_discord(texte):
    """Alerte dans le salon Discord habituel (celui des autres agents) ; jeton lu par prospection.py dans Jarvis\\.env, jamais affiché."""
    try:
        a = P.acces_discord()
        if not a: return False
        jeton, salon, uid = a
        r = P.discord(jeton, "POST", f"/channels/{salon}/messages", {"content": f"<@{uid}> **Appels Sid** : {texte}"[:1900], "allowed_mentions": {"users": [uid]}})
        return bool(r and "id" in r)
    except Exception as ex: print(f"  alerte Discord impossible ({type(ex).__name__})"); return False


# --- réglages, état, journal ---------------------------------------------------------------------------------------
def _entier(c, cle, mini, maxi):
    n = c.get(cle)
    c[cle] = max(mini, min(maxi, n)) if isinstance(n, int) and not isinstance(n, bool) else DEFAUT[cle]


def cfg():
    c = json.loads(json.dumps(DEFAUT))
    try:
        if CONFIG.exists(): c.update({k: v for k, v in json.loads(CONFIG.read_text(encoding="utf-8-sig")).items() if not k.startswith("_")})
    except (OSError, ValueError): raise ErreurAgent(f"réglages illisibles : {CONFIG.name}")
    try: M.surcharge_locale(CONFIG, c)
    except M.ErreurLocale as e: raise ErreurAgent(str(e))
    _entier(c, "par_liste", MIN_LISTE, MAX_LISTE); _entier(c, "cible_reserve", 0, 2000); _entier(c, "seuil_alerte", 0, 2000); _entier(c, "sourcing_requetes_max", 0, 30)
    _entier(c, "pause_overpass_s", 5, 600); _entier(c, "sourcing_refaire_jours", 1, 365)
    _entier(c, "sirene_requetes_max", 0, 200); _entier(c, "sirene_pages_max", 1, 40); _entier(c, "sirene_sites_max", 0, 300); _entier(c, "pause_sirene_s", 0, 60); _entier(c, "pause_site_s", 0, 60)
    c["sirene_actif"] = c.get("sirene_actif") is not False
    deps = [str(d).strip() for d in c.get("departements") or [] if str(d).strip() in NORMANDIE]
    c["departements"] = [d for d in NORMANDIE if d in deps] or list(NORMANDIE); ZONE["departements"] = list(c["departements"])
    c["envoi_automatique"] = c.get("envoi_automatique") is True; c["avec_site"] = c.get("avec_site") is True
    if not isinstance(c.get("repartition"), dict): c["repartition"] = DEFAUT["repartition"]
    if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", str(c.get("heure_tache"))): c["heure_tache"] = DEFAUT["heure_tache"]
    c["partager_avec"] = str(c.get("partager_avec") or "").strip(); c["compte_google"] = str(c.get("compte_google") or DEFAUT["compte_google"]).strip()
    return c


def etat_lire():
    try: e = json.loads(ETAT.read_text(encoding="utf-8")) if ETAT.exists() else {}
    except (OSError, ValueError): raise ErreurAgent(f"état illisible ({ETAT.name}) : rien n'est écrit ; corrigez ou supprimez le fichier à la main")
    if not isinstance(e, dict): raise ErreurAgent(f"état illisible ({ETAT.name}) : rien n'est écrit")
    e.setdefault("sorties", {}); e.setdefault("listes", {}); e.setdefault("alertes", {}); e.setdefault("google", {}); e.setdefault("sourcing", {}).setdefault("faits", {})
    s = e.setdefault("sirene", {}); s.setdefault("vus", {}); s.setdefault("curseurs", {}); s.setdefault("finis", {})
    return e


def etat_ecrire(e): ETAT.write_text(json.dumps(e, ensure_ascii=False, indent=1), encoding="utf-8")


def journaliser(action, detail="", a_blanc=False):
    """Une ligne par action : date heure | action | détail. Jamais de numéro, d'e-mail ni de nom d'entreprise."""
    if a_blanc: return
    with open(JOURNAL, "a", encoding="utf-8") as f: f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} | {action} | {detail}\n")


def alerter(etat, cle, texte, conf, jour, a_blanc=False):
    """Une alerte par motif et par jour. Simulation : journal seulement, rien sur Discord. Aucune donnée personnelle dans le texte."""
    k = f"{jour}|{cle}"
    if a_blanc or etat["alertes"].get(k): return
    etat["alertes"][k] = True
    for ancien in sorted(etat["alertes"])[:-60]: del etat["alertes"][ancien]
    etat_ecrire(etat); journaliser("alerte", f"{cle} : {texte}"[:300])
    if conf["envoi_automatique"]: alerter_discord(texte)


def vivant(pid):
    try:
        import ctypes
        k = ctypes.windll.kernel32; h = k.OpenProcess(0x1000, False, int(pid))
        if not h: return False
        code = ctypes.c_ulong(); ok = k.GetExitCodeProcess(h, ctypes.byref(code)); k.CloseHandle(h)
        return bool(ok) and code.value == 259
    except (ImportError, AttributeError):
        try: os.kill(int(pid), 0); return True
        except OSError: return False


@contextlib.contextmanager
def verrou():
    """Un seul lancement à la fois. Repris s'il est laissé par un processus mort ou vieux de plus de 3 h : une panne ne bloque jamais les jours suivants."""
    if VERROU.exists():
        try: pid = int(VERROU.read_text(encoding="utf-8").strip()); age = time.time() - VERROU.stat().st_mtime
        except (OSError, ValueError): pid, age = 0, 0
        if pid and age < VERROU_MAX_S and vivant(pid): raise ErreurAgent("verrou tenu par un autre lancement d'appels-sid : réessayez dans un instant")
        VERROU.unlink(missing_ok=True)
    try:
        with open(VERROU, "x", encoding="utf-8") as f: f.write(str(os.getpid()))
    except FileExistsError: raise ErreurAgent("verrou tenu par un autre lancement d'appels-sid : réessayez dans un instant")
    try: yield
    finally: VERROU.unlink(missing_ok=True)


def sous_verrou(a_blanc): return contextlib.nullcontext() if a_blanc else verrou()


# --- sélection -----------------------------------------------------------------------------------------------------
def telephone_valide(brut):
    """Numéro français normalisé « 02 35 62 41 64 », ou « » : 10 chiffres commençant par 01 à 07 ou 09 (pas 08 : numéros spéciaux), +33 / 0033 acceptés, rien d'autre."""
    t = (brut or "").strip()
    if not t or re.search(r"[^\d\s.\-+()]", t): return ""
    d = re.sub(r"\D", "", t)
    if t.startswith("+"):
        if not d.startswith("33"): return ""
        d = d[2:]; d = d if d.startswith("0") else "0" + d
    elif d.startswith("0033"): d = d[4:]; d = d if d.startswith("0") else "0" + d
    if not re.fullmatch(r"0[1-79]\d{8}", d) or len(set(d[1:])) == 1: return ""
    return " ".join(d[i:i + 2] for i in range(0, 10, 2))


def _lire_maps():
    if not MAPS.exists(): return []
    with open(MAPS, encoding="utf-8-sig", newline="") as f: return list(csv.DictReader(f, delimiter=";"))


def _lignes_des_listes():
    """Entreprises des docs\\liste-appels-*.md (nom, ville, téléphone, métier), pour celles qui n'auraient plus de ligne dans les fichiers de la prospection."""
    out = []
    for f in sorted(P.DOCS.glob("liste-appels-*.md")):
        out += [{"nom": e["nom"], "ville": e["ville"], "telephone": e["tel"], "metier": e["metier"]} for e in P.lire_liste_fichier(f)]
    return out


def _hors_zone(cp):
    """Vrai seulement si un code postal à 5 chiffres est donné ET que son département n'est pas dans la zone (Normandie par défaut) ; code postal absent : on ne conclut pas."""
    cp = (cp or "").strip()
    return bool(re.fullmatch(r"\d{5}", cp)) and ZN.dept_de_cp(cp) not in ZONE["departements"]


def _tels_donnes():
    """Numéros déjà donnés à Sid : colonne « Téléphone » de chaque liste docs\\sid\\liste-sid-*.csv (sauf les listes annulées). Un numéro donné ne ressort JAMAIS, même sous un autre nom d'entreprise."""
    out = set()
    for f in sorted(SORTIE.glob("liste-sid-*.csv")):
        if ".annulee" in f.name: continue
        try:
            with open(f, encoding="utf-8-sig", newline="") as fh:
                for l in list(csv.reader(fh, delimiter=";"))[1:]:
                    if len(l) > 3 and telephone_valide(l[3]): out.add(telephone_valide(l[3]))
        except OSError: pass
    return out


def _tels_stop():
    """Numéros des entreprises qui ont dit STOP, refusé ou ont été exclues (suivi) : jamais rappelés."""
    return {telephone_valide(r.get("telephone", "")) for r in S.lire() if r.get("statut") in ("STOP", "refusé", "exclu")} - {""}


def candidats(etat, extra=()):
    """Entreprises éligibles, sans doublon (même clé nom|ville ou même numéro), classées par proximité de Rouen. Reprend celles des listes d'appels de Liam jamais appelées."""
    P.appliquer_vagues()
    cles_exclues, mails = P.exclusions(); reprises, dans_listes = P.a_reprendre(cles_exclues); reprises = set(reprises); donnees = set(etat["sorties"])
    trouves = P.lire_trouves(); eligibles = P.STATUTS_TEL + ("listé",)
    ecartees = {S.cle(l) for l in trouves if l.get("statut") in P.STATUTS_ECARTES}
    autres = {S.cle(l) for l in trouves if l.get("statut") not in eligibles} - reprises   # déjà préparée pour l'e-mail, etc. (sauf si elle était dans une liste d'appels jamais appelée)
    sources = [l for l in trouves if l.get("statut") in eligibles] + [l for l in S.lire() if l.get("statut") == "à contacter"] + _lire_maps() + _lignes_des_listes() + list(extra)      # extra : lignes trouvées à blanc (pas encore écrites), pour projeter la réserve
    vus_cles, vus_tel, out = set(), set(), []; vus_tel |= _tels_donnes() | _tels_stop()
    for l in sources:
        cle = S.cle(l); metier = R.cle_metier(l.get("metier", "")); tel = telephone_valide(l.get("telephone", ""))
        if metier not in NOMS or not tel or cle in vus_cles or tel in vus_tel or cle in donnees or cle in ecartees or cle in autres: continue
        if cle in cles_exclues or (cle in dans_listes and cle not in reprises) or (l.get("email") or "").lower() in mails or _hors_zone(l.get("cp", "")): continue
        vus_cles.add(cle); vus_tel.add(tel)
        out.append({"cle": cle, "nom": l["nom"], "ville": l.get("ville", ""), "tel": tel, "metier": metier, "brut": l["metier"], "constat": (l.get("note_besoin") or "").strip(), "dept": ZN.dept_de_cp(str(l.get("cp", ""))) or "", "prox": ZN.cle_proximite(l.get("cp", ""), l.get("ville", ""))})
    return sorted(out, key=lambda c: c["prox"])


def reserve(etat, extra=()):
    """{"total": n, "par": {métier: n}, "par_dept": {métier: {département: n}}} : entreprises éligibles jamais sorties (département "?" = code postal inconnu)."""
    par = {m: 0 for m in NOMS}; par_dept = {m: {} for m in NOMS}
    for c in candidats(etat, extra):
        par[c["metier"]] += 1; d = c.get("dept") or "?"; par_dept[c["metier"]][d] = par_dept[c["metier"]].get(d, 0) + 1
    return {"total": sum(par.values()), "par": par, "par_dept": par_dept}


def afficher_reserve(conf, r):
    """Tableau de fin de passage : réserve par métier et par département, puis le nombre de jours de réserve à `par_liste` numéros par jour (55 par défaut)."""
    deps = [d for d in NORMANDIE if d in conf["departements"] or any(r["par_dept"][m].get(d) for m in NOMS)]
    if any(r["par_dept"][m].get("?") for m in NOMS): deps.append("?")
    nom = lambda d: NOMS_DEPT.get(d, "inconnu") + (f" {d}" if d != "?" else "")
    larg = max(len(nom(d)) for d in deps) if deps else 8; lm = max(len(NOMS[m]) for m in NOMS)
    print(f"Réserve par métier et par département ({r['total']} entreprise(s) jamais sorties, téléphone valide) :")
    print("  " + " " * lm + "  " + "  ".join(nom(d).rjust(larg) for d in deps) + "  " + "Total".rjust(6))
    for m in NOMS: print("  " + NOMS[m].ljust(lm) + "  " + "  ".join(str(r["par_dept"][m].get(d, 0)).rjust(larg) for d in deps) + "  " + str(r["par"][m]).rjust(6))
    print("  " + "Total".ljust(lm) + "  " + "  ".join(str(sum(r["par_dept"][m].get(d, 0) for m in NOMS)).rjust(larg) for d in deps) + "  " + str(r["total"]).rjust(6))
    jours = r["total"] // conf["par_liste"]
    print(f"Réserve : {r['total']} numéro(s) = {jours} jour(s) à {conf['par_liste']} numéros par jour (cible {conf['cible_reserve']}, alerte sous {conf['seuil_alerte']})")
    return jours


def _poids(conf):
    p = {m: (conf["repartition"].get(m, 0) if isinstance(conf["repartition"].get(m, 0), (int, float)) and conf["repartition"].get(m, 0) > 0 else 0) for m in NOMS}
    return p if sum(p.values()) else {m: 1 for m in NOMS}


def choisir(conf, etat):
    """par_liste lignes (50 à 60) : répartition par métier selon `repartition`, complétée par les métiers disponibles si l'un manque, puis classées dans l'ordre de la journée."""
    n = conf["par_liste"]; pools = {m: [] for m in NOMS}
    for c in candidats(etat): pools[c["metier"]].append(c)
    poids = _poids(conf); total = sum(poids.values())
    quota = {m: int(n * poids[m] / total) for m in NOMS}
    for m in sorted(NOMS, key=lambda m: (n * poids[m] / total) % 1, reverse=True)[:n - sum(quota.values())]: quota[m] += 1
    choisies = []
    for m in NOMS: choisies += [pools[m].pop(0) for _ in range(min(quota[m], len(pools[m])))]
    while len(choisies) < n and any(pools.values()):
        for m in sorted(NOMS, key=lambda m: -poids[m]):
            if pools[m] and len(choisies) < n: choisies.append(pools[m].pop(0))
    return sorted(choisies, key=lambda c: (RANG[c["metier"]], c["metier"], c["prox"]))


# --- CSV -----------------------------------------------------------------------------------------------------------
def cellule(v):
    """Une seule ligne ; une valeur qui commencerait par = + - @ ne sera jamais lue comme une formule par le tableur."""
    s = " ".join(str(v or "").split())
    return "'" + s if s[:1] in ("=", "+", "-", "@") else s


def lignes_csv(choisies):
    out = [COLONNES]
    for i, c in enumerate(choisies, 1):
        lien = "" if c["metier"] == "restaurant" else P.lien_exemple(c["brut"], lien_ok=lambda u: True)   # restaurant : numéro seulement ; lien lu dans liens-metiers.json, aucune page ouverte
        out.append([str(i), cellule(c["nom"]), cellule(c["ville"]), c["tel"], NOMS[c["metier"]], CRENEAUX[c["metier"]], cellule(c["constat"]), lien] + [""] * 5)
    return out


def chemin(jour, suffixe=""): return SORTIE / f"liste-sid-{jour}{suffixe}.csv"


def date_valide(jour):
    try: return date.fromisoformat(jour).isoformat()
    except (TypeError, ValueError): raise ErreurAgent(f"date invalide : « {jour} » (format AAAA-MM-JJ)")


def repartition(choisies):
    r = {}
    for c in choisies: r[NOMS[c["metier"]]] = r.get(NOMS[c["metier"]], 0) + 1
    return ", ".join(f"{k} {v}" for k, v in r.items())


# --- la liste du jour ----------------------------------------------------------------------------------------------
def _preparer(conf, etat, jour, a_blanc, complet=True):
    if jour in etat["listes"] or chemin(jour).exists(): raise ErreurAgent(f"la liste du {jour} est déjà préparée ({chemin(jour).name}) : utilisez `annuler {jour}` si elle n'a pas servi")
    choisies = choisir(conf, etat)
    if not choisies: raise ErreurAgent("aucune entreprise disponible (téléphone valide, jamais appelée, jamais donnée) : la réserve est épuisée")
    if len(choisies) < conf["par_liste"]: print(f"  ! réserve insuffisante : {len(choisies)} ligne(s) au lieu de {conf['par_liste']}")
    if a_blanc:
        print(f"Liste du {jour} [à blanc : rien n'est écrit, rien n'est marqué] : {len(choisies)} ligne(s) ({repartition(choisies)})")
        if complet:
            for i, c in enumerate(choisies, 1): print(f"  {i:>2}. {c['nom']} · {c['ville']} · {c['tel']} · {NOMS[c['metier']]}")
        return choisies
    SORTIE.mkdir(parents=True, exist_ok=True); fichier = chemin(jour)
    with open(fichier, "x", encoding="utf-8-sig", newline="") as f: csv.writer(f, delimiter=";").writerows(lignes_csv(choisies))
    try:
        etat["sorties"].update({c["cle"]: jour for c in choisies})
        etat["listes"][jour] = {"fichier": fichier.name, "nombre": len(choisies), "cles": [c["cle"] for c in choisies]}
        etat_ecrire(etat)
    except OSError: fichier.unlink(missing_ok=True); raise
    journaliser("preparer", f"{jour} : {len(choisies)} entreprises ({repartition(choisies)})")
    print(f"Liste du {jour} : {len(choisies)} ligne(s) ({repartition(choisies)}) -> {fichier}")
    return choisies


def cmd_preparer(conf, jour, a_blanc):
    if ARRET.exists(): raise ErreurAgent(f"arrêt de secours présent ({ARRET.name}) : rien n'est généré (supprimez le fichier pour reprendre)")
    with sous_verrou(a_blanc):
        _preparer(conf, etat_lire(), jour, a_blanc)
        if not a_blanc: print("À importer dans une feuille Google (Fichier > Importer, séparateur « ; ») ou laissez `jour` la créer. Rien n'a été envoyé ni partagé.")
        return 0


# --- sourcing : de nouvelles entreprises avec téléphone (OpenStreetMap, gratuit) -----------------------------------------
def requete_tel(tags, zone, conf):
    """La requête de la prospection pour UN département (relation OpenStreetMap du département : area["ref:INSEE"]) limitée aux fiches qui portent un téléphone (phone, mobile, contact:phone, contact:mobile)."""
    q = P.requete_overpass(tags, zone, {"rayon_osm_m": 0})
    return re.sub(r'(nwr\["[^"]+"="[^"]+"\])', r'\1[~"^(contact:)?(phone|mobile)$"~"."]', q)


def _jours_ecoules(jour, ancien):
    try: return (date.fromisoformat(jour) - date.fromisoformat(ancien)).days
    except (TypeError, ValueError): return 10 ** 6


def _connu():
    """(clés, téléphones, identifiants OSM) de tout ce qui existe déjà : prospection-trouves.csv, suivi, maps, listes d'appels, exclusions, entreprises déjà sorties pour Sid."""
    cles, mails = P.exclusions(); trouves = P.lire_trouves(); tout = trouves + S.lire() + _lire_maps() + _lignes_des_listes()
    cles = set(cles) | {S.cle(l) for l in tout} | {k for k, _, _ in P.lire_listes()}
    tels = {telephone_valide(l.get("telephone", "")) for l in tout} - {""}
    ids = {l.get("osm") for l in trouves if l.get("osm")} | {k.removeprefix("osm:") for k in P.etat_lire().get("vus", {}) if k.startswith("osm:")}
    return cles, tels, ids


def lignes_osm(data, label, jour, cles, tels, ids, avec_site=False):
    """Fiches OpenStreetMap -> lignes de prospection-trouves.csv (statut « sans site, téléphone »). Gardées : nom et commune connus, en zone, téléphone français valide, AUCUN site indiqué
    (aucune page n'est ouverte : un site déclaré n'est pas jugé ici ; avec avec_site=true il est gardé, statut « téléphone seulement »), pas de doublon avec ce qui existe. `cles`, `tels` et `ids` sont complétés au fil de l'eau."""
    out = []
    for c in P.candidats_osm(data, label):
        tel = telephone_valide(c["telephone"]); cle = S.cle({"nom": c["nom"], "ville": c["ville"]})
        if not tel or (c["site"] and not avec_site) or c["id"] in ids or cle in cles or tel in tels: continue
        ligne = {k: "" for k in P.COLS}
        ligne.update(nom=c["nom"], metier=label, ville=c["ville"], cp=c.get("cp", ""), telephone=tel, osm=c["id"], date_collecte=jour, statut="téléphone seulement" if c["site"] else "sans site, téléphone", modele="" if c["site"] else "sans-site",
                     site_actuel=c["site"], source="OpenStreetMap, base de données ouverte")
        out.append(ligne); cles.add(cle); tels.add(tel); ids.add(c["id"])
    return out


def _ajouter_trouves(lignes):
    """Relit prospection-trouves.csv juste avant d'écrire, ajoute à la fin et remplace le fichier d'un coup (jamais de fichier à moitié écrit)."""
    tmp = P.TROUVES.with_name(P.TROUVES.name + ".tmp")
    P.ecrire_trouves(P.lire_trouves() + lignes, tmp); os.replace(tmp, P.TROUVES)


# --- SIRENE : entreprises actives, téléphone lu sur la fiche OpenStreetMap ou sur le site public -----------------------------
def appel_sirene(dept, naf, page):
    """API officielle « Recherche d'entreprises » (data.gouv, gratuite, sans clé) : entreprises ACTIVES d'un code NAF dans un département, 25 par page. prospection.appel_api gère les nouveaux essais (429, 5xx)."""
    return P.appel_api(dept, naf, page, dormir=dormir)


def lire_site(url):
    """(url finale, en-têtes, texte) ou None : page d'accueil publique, robots.txt respecté (prospection.lire_page)."""
    return P.lire_page(url)


def evaluer_site(url, texte):
    """(faible, score) : le constat vérifié de la prospection sur la page d'accueil lue (aucune mesure réseau supplémentaire). Faible = le site justifie un appel."""
    pc = P.cfg(); o = {"images_reseau": True, "mesure": (lambda u: None), "psi": (lambda u: None)}
    sc = P.score_faiblesse(P.constats_site(url, texte, pc, None, o)); return sc >= pc["seuil_faiblesse"], sc


TEL_TEXTE = re.compile(r"(?<![\d])(?:(?:\+|00)33[\s.\-]?\(?0?\)?|0)[1-79](?:[\s.\-]?\d{2}){4}(?![\d])")


def telephones_page(texte):
    """Numéros français valides d'une page publique : liens tel: d'abord, puis numéros écrits dans le texte. Format normalisé « 02 35 62 41 64 »."""
    brut = re.findall(r'href=["\']tel:([^"\']+)', texte or "", re.I) + TEL_TEXTE.findall(texte or ""); out = []
    for b in brut:
        n = telephone_valide(urllib.parse.unquote(b))
        if n and n not in out: out.append(n)
    return out


def _tel_fiche(tags):
    for k in ("phone", "contact:phone", "mobile", "contact:mobile"):
        v = tags.get(k)
        if v:
            n = telephone_valide(re.split(r"[;,]", v)[0])
            if n: return n
    return ""


def _index_osm(data):
    """{nom normalisé: (téléphone, commune normalisée, site)} des fiches OpenStreetMap d'une réponse Overpass qui portent un téléphone, AVEC OU SANS commune (une fiche sans addr:city n'est pas une ligne de prospection,
    mais sert à retrouver le téléphone d'une entreprise connue de SIRENE)."""
    idx = {}
    for e in (data or {}).get("elements", []):
        t = e.get("tags") or {}; nom = P.norm(t.get("name") or t.get("brand") or ""); tel = _tel_fiche(t)
        if nom and tel: idx.setdefault(nom, (tel, P.norm(t.get("addr:city", "")), (t.get("website") or t.get("contact:website") or t.get("url") or "").strip()))
    return idx


def _nom_sirene(nc):
    """« DUPONT PLOMBERIE (DUPONT JEAN) » -> « Dupont Plomberie » : le nom commercial sans le nom du dirigeant entre parenthèses."""
    return P.beau(re.sub(r"\s+", " ", re.sub(r"\s*\(.*?\)\s*", " ", nc or "")).strip())


def _sirene(conf, etat, jour, a_blanc, dept, m, idx, cles, tels, sirens, stat):
    """Entreprises actives de SIRENE pour (département, métier) -> lignes de prospection-trouves.csv, uniquement celles dont on trouve un téléphone valide :
    1. fiche OpenStreetMap du même nom (index de la réponse Overpass de ce passage), 2. site public (domaines usuels, page vérifiée par la commune ou le code postal, robots.txt respecté).
    Un site CORRECT d'après le constat de la prospection exclut l'entreprise ; un site faible la garde (statut « téléphone seulement »). Au plus sirene_pages_max pages par code NAF et par passage (curseur gardé),
    sirene_requetes_max appels d'API et sirene_sites_max pages de sites par passage. Lève ErreurSourcing (après avoir gardé ce qui a été trouvé)."""
    sr = etat["sirene"]; out = []; pc = None
    for naf in NAF_SID[m]:
        cle_c = f"{dept}|{naf}"
        if sr["finis"].get(cle_c) and _jours_ecoules(jour, sr["finis"][cle_c]) < conf["sourcing_refaire_jours"]: continue
        page = sr["curseurs"].get(cle_c, 1) if not sr["finis"].get(cle_c) else 1
        for _ in range(conf["sirene_pages_max"]):
            if stat["api"] >= conf["sirene_requetes_max"]: return out
            if stat["api"]: dormir(conf["pause_sirene_s"])
            data = appel_sirene(dept, naf, page); stat["api"] += 1; res = (data or {}).get("results", []); complet = True
            for r in res:
                s = r.get("siege") or {}; cp = str(s.get("code_postal", "")); siren = str(r.get("siren", ""))
                if not siren or ZN.dept_de_cp(cp) != dept or str(r.get("etat_administratif", "A")) != "A": continue
                ancien = sr["vus"].get(siren)
                if siren in sirens or (ancien and not ancien.endswith("sans téléphone")) or (ancien and _jours_ecoules(jour, ancien.split("|")[0]) < conf["sourcing_refaire_jours"]): continue
                nom = _nom_sirene(r.get("nom_complet", "")); ville = P.beau(s.get("libelle_commune", "")); cle = S.cle({"nom": nom, "ville": ville})
                if not nom or not ville or cle in cles: continue
                c = {"nom": nom, "ville": ville, "cp": cp, "siren": siren, "metier": LABELS[m]}; tel, url, texte, source = "", "", "", ""
                f = idx.get(P.norm(nom))
                if f and (not f[1] or f[1] == P.norm(ville)): tel, source = f[0], "fiche OpenStreetMap"; url = f[2]
                elif P.domaines(nom):
                    if stat["sites"] >= conf["sirene_sites_max"]: complet = False; break
                    for d in P.domaines(nom)[:2]:
                        if stat["sites"] >= conf["sirene_sites_max"]: break
                        if stat["sites"]: dormir(conf["pause_site_s"])
                        stat["sites"] += 1; pg = lire_site("https://" + d)
                        if pg and P.verifie_osm(pg[2], c):
                            tl = telephones_page(pg[2])
                            if tl: tel, url, texte, source = tl[0], pg[0], pg[2], "site public"; break
                if not tel: sr["vus"][siren] = f"{jour}|sans téléphone"; continue
                if tel in tels: sr["vus"][siren] = f"{jour}|numéro déjà connu"; continue
                faible = True
                if url:
                    if not texte: pg = lire_site(url); texte = pg[2] if pg else ""; url = pg[0] if pg else url
                    if texte:
                        faible, sc = evaluer_site(url, texte)
                        if not faible: sr["vus"][siren] = f"{jour}|site correct"; continue
                    elif not conf["avec_site"]: sr["vus"][siren] = f"{jour}|site illisible"; continue   # aucun constat possible : comme la prospection, on n'appelle pas à l'aveugle
                ligne = {k: "" for k in P.COLS}
                ligne.update(nom=nom, metier=LABELS[m], ville=ville, cp=cp, telephone=tel, siren=siren, date_collecte=jour, statut="téléphone seulement" if url else "sans site, téléphone", modele="" if url else "sans-site",
                             site_actuel=url, source=f"SIRENE (Recherche d'entreprises, data.gouv) ; téléphone : {source}")
                out.append(ligne); cles.add(cle); tels.add(tel); sr["vus"][siren] = f"{jour}|ajoutée"; stat["ajoutes"] += 1
            if not complet: break
            if len(res) < 25: sr["finis"][cle_c] = jour; sr["curseurs"].pop(cle_c, None); break
            page += 1; sr["curseurs"][cle_c] = page
    return out


def _sourcer(conf, etat, jour, a_blanc, depts=None):
    """Au plus sourcing_requetes_max requêtes Overpass (UNE par département et par métier, une à la fois, pause_overpass_s entre deux, nouvelles tentatives après un refus), puis, pour le même département et le même
    métier, SIRENE (voir _sirene). Zone : les départements de `departements` (Normandie : 76, 27, 14, 50, 61). Les métiers dont la réserve est sous leur part de cible_reserve passent d'abord
    (plombiers, électriciens). -> {"requetes": n, "ajoutes": {métier: n}, "sirene": {...}}. Lève ErreurSourcing (après avoir gardé ce qui a été trouvé)."""
    P.appliquer_vagues(); ZN.ouvrir(max(ZN.VAGUE_MAX, 2))      # Normandie = vagues 1 et 2 de zone.py ; les fiches sont de toute façon prises dans la relation du département
    poids = _poids(conf); total = sum(poids.values()); besoin = {m: math.ceil(conf["cible_reserve"] * poids[m] / total) for m in NOMS}
    etat["sirene"].setdefault("vus", {}); etat["sirene"].setdefault("curseurs", {}); etat["sirene"].setdefault("finis", {})
    res = reserve(etat)["par"]; faits = etat["sourcing"]["faits"]; ajoutes = {m: 0 for m in NOMS}; n_req = 0; erreur = None; cles, tels, ids = _connu()
    stat = {"api": 0, "sites": 0, "ajoutes": 0}; trouvees = []; sirens = {l.get("siren") for l in P.lire_trouves() + S.lire() if l.get("siren")} | {k for k in P.etat_lire().get("vus", {}) if not k.startswith("osm:")}
    for d in (depts or conf["departements"]):
        z = {"id": f"dept-{d}", "type": "dept", "dept": d}
        for m in PRIORITE:
            if res[m] >= besoin[m]: continue
            k = f"{z['id']}|{m}"; osm_du = n_req < conf["sourcing_requetes_max"] and not (k in faits and _jours_ecoules(jour, faits[k]) < conf["sourcing_refaire_jours"])
            sirene_du = conf["sirene_actif"] and stat["api"] < conf["sirene_requetes_max"]
            if not (osm_du or sirene_du): continue
            idx, nouvelles = {}, []
            try:
                if osm_du:
                    if n_req: dormir(conf["pause_overpass_s"])
                    data = appel_reseau(requete_tel(dict(P.OSM_METIERS)[LABELS[m]], z, conf)); n_req += 1; idx = _index_osm(data)
                    nouvelles = lignes_osm(data, LABELS[m], jour, cles, tels, ids, conf["avec_site"])
                    print(f"  OpenStreetMap {NOMS_DEPT[d]} / {NOMS[m]} : {len((data or {}).get('elements', []))} fiche(s) avec téléphone, {len(nouvelles)} nouvelle(s)", flush=True)
                    if not a_blanc:
                        if nouvelles: _ajouter_trouves(nouvelles)
                        faits[k] = jour; etat_ecrire(etat)
                    ajoutes[m] += len(nouvelles); res[m] += len(nouvelles); trouvees += nouvelles
            except Exception as e: erreur = type(e).__name__; break
            if sirene_du:
                try: sn = _sirene(conf, etat, jour, a_blanc, d, m, idx, cles, tels, sirens, stat)
                except Exception as e: erreur = type(e).__name__; sn = []
                print(f"  SIRENE {NOMS_DEPT[d]} / {NOMS[m]} : {len(sn)} entreprise(s) avec téléphone ({stat['api']} appel(s) d'API, {stat['sites']} page(s) de site en tout)", flush=True)
                if sn and not a_blanc: _ajouter_trouves(sn)
                if not a_blanc: etat_ecrire(etat)
                ajoutes[m] += len(sn); res[m] += len(sn); trouvees += sn
                if erreur: break
        if erreur or (n_req >= conf["sourcing_requetes_max"] and (not conf["sirene_actif"] or stat["api"] >= conf["sirene_requetes_max"])): break
    detail = ", ".join(f"{NOMS[m]} {n}" for m, n in ajoutes.items() if n) or "aucune"
    if not a_blanc: journaliser("sourcer", f"{jour} : {n_req} requête(s) Overpass, {stat['api']} appel(s) SIRENE, {stat['sites']} page(s) de site, {sum(ajoutes.values())} ajoutée(s) ({detail})" + (f", échec {erreur}" if erreur else ""))
    print(f"Sourcing{' [à blanc : rien écrit]' if a_blanc else ''} : {n_req} requête(s) Overpass, {stat['api']} appel(s) SIRENE, {stat['sites']} page(s) de site lue(s), {sum(ajoutes.values())} nouvelle(s) entreprise(s) avec téléphone ({detail}) ; dont SIRENE : {stat['ajoutes']}")
    if erreur: raise ErreurSourcing(erreur)
    return {"requetes": n_req, "ajoutes": ajoutes, "sirene": stat, "lignes": trouvees}


def _alerte_sourcing(conf, etat, jour, e, a_blanc):
    print(f"  ! Échec du sourcing ({e}) : aucune nouvelle entreprise ajoutée, la réserve existante reste utilisable")
    alerter(etat, "sourcing", f"Sourcing échoué ({e}) : aucune nouvelle entreprise avec téléphone ajoutée aujourd'hui. Les listes continuent avec la réserve existante.", conf, jour, a_blanc)


def cmd_sourcer(conf, jour, a_blanc, depts=None):
    if ARRET.exists(): raise ErreurAgent(f"arrêt de secours présent ({ARRET.name}) : rien n'est fait")
    with sous_verrou(a_blanc):
        etat = etat_lire()
        try:
            r = _sourcer(conf, etat, jour, a_blanc, depts)
            if a_blanc: print("Réserve projetée (à blanc : la réserve actuelle + ce que ce sourcing aurait ajouté) :")
            afficher_reserve(conf, reserve(etat, r["lignes"] if a_blanc else ())); return 0
        except ErreurSourcing as e: _alerte_sourcing(conf, etat, jour, e, a_blanc); afficher_reserve(conf, reserve(etat)); return 2


# --- Google Drive : dossier « Sid » > date, feuille du jour --------------------------------------------------------------
def exporter_google(conf, etat, jour, drive, a_blanc):
    """Crée (une seule fois) Sid > AAAA-MM-JJ > « Liste d'appels AAAA-MM-JJ » depuis le CSV du jour. Ce qui existe déjà n'est ni recréé ni écrasé. Partage du dossier « Sid » avec partager_avec
    (éditeur, une fois) seulement s'il est renseigné. Simulation (envoi_automatique=false) et --a-blanc : aucun contact avec Google."""
    fichier = chemin(jour); titre = f"Liste d'appels {jour}"; cible = conf["partager_avec"].lower()
    if not conf["envoi_automatique"] or a_blanc:
        print(f"  Google : {'à blanc' if a_blanc else 'simulation (envoi_automatique=false)'} : serait créé Sid > {jour} > « {titre} »" + (f", dossier « Sid » partagé avec une adresse ({'valide' if EMAIL.match(cible) else 'INVALIDE'})" if cible else ", aucun partage"))
        if not a_blanc: journaliser("google", f"{jour} : simulation, rien créé")
        return
    if not fichier.exists(): raise ErreurAgent(f"la liste du {jour} n'existe pas ({fichier.name}) : rien à envoyer à Google")
    if (drive.compte() or "").lower() != conf["compte_google"].lower(): raise ErreurAgent(f"le jeton Google appartient à un autre compte que {conf['compte_google']} : relancez google-autoriser avec le bon compte")
    g = etat["google"]
    racine = g.get("racine") or drive.trouver_dossier("Sid") or drive.creer_dossier("Sid"); g["racine"] = racine; etat_ecrire(etat)
    if cible:
        if not EMAIL.match(cible): print("  ! partager_avec n'est pas une adresse e-mail valide : rien n'est partagé"); journaliser("google", "partage ignoré : adresse invalide")
        elif g.get("partage") != cible: drive.partager(racine, cible); g["partage"] = cible; etat_ecrire(etat); journaliser("google", "dossier Sid partagé (éditeur)")
    jg = g.setdefault(jour, {})
    jg["dossier"] = jg.get("dossier") or drive.trouver_dossier(jour, racine) or drive.creer_dossier(jour, racine); etat_ecrire(etat)
    if not jg.get("feuille"):
        jg["feuille"] = drive.trouver_feuille(jg["dossier"], titre) or None
        if not jg["feuille"]:
            with open(fichier, encoding="utf-8-sig", newline="") as f: lignes = list(csv.reader(f, delimiter=";"))
            tampon = io.StringIO(); csv.writer(tampon).writerows(lignes)
            jg["feuille"] = drive.creer_feuille(jg["dossier"], titre, tampon.getvalue())
        etat_ecrire(etat)
    journaliser("google", f"{jour} : dossier et feuille en place")
    print(f"  Google : Sid > {jour} > « {titre} » en place")


# --- le passage du matin -------------------------------------------------------------------------------------------
def _etape(nom, fn, conf, etat, jour, a_blanc):
    """Exécute une étape ; une panne est journalisée et alertée (une fois par jour) mais n'arrête jamais les étapes suivantes. -> résultat ou None."""
    try: return fn()
    except ErreurSourcing as e: _alerte_sourcing(conf, etat, jour, e, a_blanc)
    except ErreurAgent as e:
        print(f"  ! {nom} : {e}"); journaliser("erreur", f"{nom} : {e}"[:200], a_blanc)
        alerter(etat, nom, f"{'Google' if nom == 'google' else nom.capitalize()} : {e}"[:300], conf, jour, a_blanc)
    except Exception as e:
        print(f"  ! {nom} : {type(e).__name__}"); journaliser("erreur", f"{nom} : {type(e).__name__}", a_blanc)
        alerter(etat, nom, f"{'Google' if nom == 'google' else nom.capitalize()} : échec ({type(e).__name__}) ; le prochain passage réessaie", conf, jour, a_blanc)
    return None


def cmd_jour(conf, jour, a_blanc):
    if ARRET.exists(): raise ErreurAgent(f"arrêt de secours présent ({ARRET.name}) : rien n'est fait (supprimez le fichier pour reprendre)")
    with sous_verrou(a_blanc):
        etat = etat_lire(); print(f"Passage du {jour}" + (" [à blanc : rien n'est écrit, aucun accès réseau ni Google]" if a_blanc else ""))
        if a_blanc: print("  1. sourcing : serait lancé ici (jusqu'à %d requête(s) Overpass, %d appel(s) SIRENE) ; `sourcer --a-blanc` montre ce qu'il trouverait" % (conf["sourcing_requetes_max"], conf["sirene_requetes_max"]))
        else: _etape("sourcing", lambda: _sourcer(conf, etat, jour, False), conf, etat, jour, False)
        if jour in etat["listes"] or chemin(jour).exists(): print(f"  2. liste du {jour} : déjà préparée"); liste = True
        else: liste = _etape("liste", lambda: _preparer(conf, etat, jour, a_blanc, complet=False), conf, etat, jour, a_blanc) is not None
        if liste: _etape("google", lambda: exporter_google(conf, etat, jour, None if (a_blanc or not conf["envoi_automatique"]) else ouvrir_drive(conf), a_blanc), conf, etat, jour, a_blanc)
        r = reserve(etat); detail = ", ".join(f"{NOMS[m]} {n}" for m, n in r["par"].items())
        print(f"  Réserve : {r['total']} entreprise(s) ({detail})"); afficher_reserve(conf, r)
        if r["total"] < conf["seuil_alerte"]:
            alerter(etat, "reserve", f"Réserve appels-sid sous 2 jours : {r['total']} entreprise(s) (seuil {conf['seuil_alerte']}) — {detail}. La recherche de nouveaux numéros continue chaque matin.", conf, jour, a_blanc)
        return 0 if liste else 2


# --- état, annulation ----------------------------------------------------------------------------------------------
def _heure_liste_liam():
    try: return M.lire_fusionnee(PROSPECTION_CONFIG).get("liste_appels_heure", P.DEFAUT["liste_appels_heure"])
    except (OSError, ValueError): return None


def cmd_etat(conf):
    etat = etat_lire(); r = reserve(etat)
    print(f"Réserve : {r['total']} entreprise(s) jamais sorties (cible {conf['cible_reserve']}, alerte sous {conf['seuil_alerte']})")
    for m in NOMS: print(f"  {NOMS[m]} : {r['par'][m]}")
    print(f"Environ {r['total'] // conf['par_liste']} jour(s) de réserve à {conf['par_liste']} par liste"); afficher_reserve(conf, r)
    h = _heure_liste_liam()
    print("Liste de Liam : " + ("redirigée vers Sid (aucune liste d'appels pour Liam)" if h == HEURE_JAMAIS else f"active ({h}) : `rediriger-liste` pour tout envoyer à Sid" if h else "réglage introuvable"))
    print(f"Google : {'actif' if conf['envoi_automatique'] else 'simulation (envoi_automatique=false)'} ; partage : {'oui' if conf['partager_avec'] else 'non (partager_avec vide)'}")
    s = etat["sourcing"]
    if s["faits"]: print(f"Sourcing : {len(s['faits'])} requête(s) faite(s), dernière le {max(s['faits'].values())}")
    if etat["sirene"]["vus"]: print(f"SIRENE : {len(etat['sirene']['vus'])} entreprise(s) examinée(s), {sum(1 for v in etat['sirene']['vus'].values() if v.endswith('ajoutée'))} ajoutée(s) ; {len(etat['sirene']['finis'])} série(s) département + code NAF terminée(s)")
    if not etat["listes"]: print("Aucune liste préparée pour l'instant."); return 0
    jour = max(etat["listes"]); l = etat["listes"][jour]
    print(f"{len(etat['listes'])} liste(s) préparée(s), {len(etat['sorties'])} entreprise(s) sorties. Dernière : {jour} ({l['nombre']} lignes, {l['fichier']})")
    return 0


def cmd_annuler(jour, force, a_blanc):
    with sous_verrou(a_blanc):
        etat = etat_lire()
        jour = jour or (max(etat["listes"]) if etat["listes"] else None)
        if not jour or jour not in etat["listes"]: raise ErreurAgent(f"aucune liste à annuler{' pour le ' + jour if jour else ''}")
        fichier = chemin(jour)
        if fichier.exists() and not force:
            with open(fichier, encoding="utf-8-sig", newline="") as f: lignes = list(csv.reader(f, delimiter=";"))[1:]
            if any(any(x.strip() for x in l[8:]) for l in lignes if len(l) > 8): raise ErreurAgent(f"la liste du {jour} a déjà été utilisée (une case ou une remarque est remplie) : annulation refusée (--force pour libérer quand même)")
        cles = etat["listes"][jour]["cles"]
        if a_blanc: print(f"Annulation du {jour} [à blanc : rien n'est changé] : {len(cles)} entreprise(s) seraient libérées"); return 0
        for k in cles: etat["sorties"].pop(k, None)
        del etat["listes"][jour]; etat["google"].pop(jour, None); etat_ecrire(etat)
        if fichier.exists(): os.replace(fichier, chemin(jour, ".annulee"))
        journaliser("annuler", f"{jour} : {len(cles)} entreprises libérées")
        print(f"Liste du {jour} annulée : {len(cles)} entreprise(s) libérées (fichier conservé en .annulee.csv ; un dossier Google déjà créé reste en place)")
        return 0


# --- la liste d'appels de Liam : un réglage de prospection-config.json, le code de la prospection n'est pas touché -------------------
def _lire_config_prospection():
    try:
        if not PROSPECTION_CONFIG.exists(): raise OSError(PROSPECTION_CONFIG.name)
        return M.lire_fusionnee(PROSPECTION_CONFIG)      # réglages par défaut + surcharge locale de cette machine
    except (OSError, ValueError): raise ErreurAgent(f"{PROSPECTION_CONFIG.name} introuvable ou illisible : rien n'est changé")


def _ecrire_config_prospection(pc): M.ecrire_local(PROSPECTION_CONFIG, {"liste_appels_heure": pc["liste_appels_heure"]})      # dans prospection-config.local.json : le fichier versionné ne bouge jamais


def cmd_rediriger(a_blanc):
    """liste_appels_heure = 99:99 : jamais atteinte, donc cmd_liste_matin ne produit ni fichier ni message Discord pour Liam. L'ancienne heure est gardée pour `rendre-liste`."""
    with sous_verrou(a_blanc):
        pc = _lire_config_prospection(); courant = pc.get("liste_appels_heure", P.DEFAUT["liste_appels_heure"])
        if courant == HEURE_JAMAIS: print("La liste de Liam est déjà redirigée vers Sid."); return 0
        if a_blanc: print(f"[à blanc] liste_appels_heure passerait de {courant} à {HEURE_JAMAIS} : Liam ne recevrait plus de liste d'appels"); return 0
        etat = etat_lire(); etat["liste_liam"] = {"ancienne": courant, "date": date.today().isoformat()}; etat_ecrire(etat)
        pc["liste_appels_heure"] = HEURE_JAMAIS; _ecrire_config_prospection(pc); journaliser("rediriger-liste", f"heure {courant} -> {HEURE_JAMAIS}")
        print(f"Liste de Liam redirigée : liste_appels_heure {courant} -> {HEURE_JAMAIS}. Tout va dans la réserve de Sid. `rendre-liste` pour revenir en arrière.")
        return 0


def cmd_rendre(a_blanc):
    with sous_verrou(a_blanc):
        pc = _lire_config_prospection(); etat = etat_lire(); ancienne = (etat.get("liste_liam") or {}).get("ancienne") or P.DEFAUT["liste_appels_heure"]
        if pc.get("liste_appels_heure") != HEURE_JAMAIS: print("La liste de Liam n'est pas redirigée : rien à rendre."); return 0
        if a_blanc: print(f"[à blanc] liste_appels_heure reviendrait à {ancienne}"); return 0
        pc["liste_appels_heure"] = ancienne; _ecrire_config_prospection(pc); etat.pop("liste_liam", None); etat_ecrire(etat); journaliser("rendre-liste", f"heure -> {ancienne}")
        print(f"Liste de Liam rendue : liste_appels_heure = {ancienne}.")
        return 0


# --- tâche planifiée Windows (jamais installée sans --oui) ---------------------------------------------------------------
def _ps(s): return str(s).replace("'", "''")


def commande_tache(action, conf):
    if action == "retirer": return f"Unregister-ScheduledTask -TaskName '{TACHE}' -Confirm:$false"
    py = Path(sys.executable); pyw = py.with_name("pythonw.exe"); pyw = pyw if pyw.exists() else py   # pythonw : aucune fenêtre ; la trace est dans appels-sid-journal.log
    return (f"$a = New-ScheduledTaskAction -Execute '{_ps(pyw)}' -Argument '\"{_ps(Path(__file__).resolve())}\" jour' -WorkingDirectory '{_ps(RACINE)}'; "
            f"$t = New-ScheduledTaskTrigger -Daily -At {conf['heure_tache']}; $p = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited; "
            "$s = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 2); "
            f"Register-ScheduledTask -TaskName '{TACHE}' -Action $a -Trigger $t -Principal $p -Settings $s -Description 'Liste d appels de Sid : sourcing, liste du jour, dossier Google (LM MULTI-SERVICES)' -Force")


def cmd_tache(action, oui, conf):
    cmd = commande_tache(action, conf); verbe = "installer" if action == "installer" else "retirer"
    if not oui:
        print(f"Commande PowerShell ({verbe} la tâche « {TACHE} », tous les jours à {conf['heure_tache']}, rattrapage au réveil du PC si manquée) — rien n'est exécuté :\n\n{cmd}\n\n"
              f"Pour l'exécuter vraiment : python agents\\appels-sid.py {verbe}-tache --oui")
        return 0
    code, msg = executer(cmd)
    if code != 0: print(f"  ! la tâche n'a pas pu être {'installée' if action == 'installer' else 'retirée'} : {msg or 'code ' + str(code)}"); return 2
    journaliser(f"{verbe}-tache", TACHE); print(f"Tâche « {TACHE} » {'installée' if action == 'installer' else 'retirée'}."); return 0


def cmd_google_autoriser(conf, a_blanc):
    if a_blanc: print(f"[à blanc] ouvrirait le navigateur pour autoriser {conf['compte_google']} (Google Drive, portée drive.file) ; jeton enregistré dans agents\\google-sheets-token.json"); return 0
    import google_sheets as GS
    try: GS.autoriser(conf["compte_google"])
    except Exception as e: raise ErreurAgent(f"autorisation Google impossible ({type(e).__name__})")
    journaliser("google-autoriser", "jeton enregistré"); print(f"Autorisation enregistrée pour {conf['compte_google']}."); return 0


def _simulation():
    """Remplace le réseau par des données FICTIVES (aucun accès Internet) : mêmes fonctions, mêmes filtres, rien n'est écrit (--simulation force --a-blanc). Sert à voir le flux complet et le tableau de réserve."""
    global appel_reseau, appel_sirene, lire_site, evaluer_site, dormir
    TYPE = re.compile(r'"(craft|shop|amenity)"="(\w+)"'); CP = {"14": "14000", "27": "27000", "50": "50000", "61": "61000", "76": "76000"}; VILLE = {"14": "Caen", "27": "Évreux", "50": "Saint-Lô", "61": "Alençon", "76": "Rouen"}
    def reseau(requete):
        d = re.search(r'"ref:INSEE"="(\d\d)"', requete).group(1); typ = TYPE.search(requete).group(2); els = []
        for i in range(1, 7):
            tags = {"name": f"Simulation {typ} {d} {i}", "phone": f"02 3{i} {d} 00 1{i}", "addr:postcode": CP[d]}
            if i != 6: tags["addr:city"] = VILLE[d]      # la sixième n'a pas de commune : elle ne sert qu'à retrouver un téléphone pour SIRENE
            tags.update({"craft": typ} if typ in ("electrician", "plumber", "hvac") else {"shop": typ} if typ == "hairdresser" else {"amenity": typ})
            els.append({"type": "node", "id": int(d) * 1000 + i, "lat": 49.4, "lon": 1.1, "tags": tags})
        return {"elements": els}
    def sirene(dept, naf, page):
        if page > 1: return {"results": []}
        met = next(m for m, nafs in NAF_SID.items() if naf in nafs); typ = {"plombier": "plumber", "electricien": "electrician", "coiffeur": "hairdresser", "restaurant": "restaurant"}[met]
        rs = [{"siren": f"9{dept}{naf[:2]}{i:04d}", "nom_complet": f"SIMULATION {typ.upper()} {dept} {i}", "etat_administratif": "A", "siege": {"code_postal": CP[dept], "libelle_commune": VILLE[dept].upper()}} for i in (6, 7, 8)]
        return {"results": rs}
    def site(url):      # un domaine usuel sur deux « existe » (déterministe) et publie un numéro ; la page cite les cinq communes pour passer le contrôle de commune
        import zlib
        h = zlib.crc32(url.encode())
        if "simulation" in url and url.endswith(".fr") and h % 2 == 0: return url, {}, f"<html>Rouen Caen Évreux Alençon Saint-Lô <a href='tel:+33232{h % 90 + 10}0012'>02 32 {h % 90 + 10} 00 12</a></html>"
        return None
    appel_reseau, appel_sirene, lire_site, evaluer_site, dormir = reseau, sirene, site, (lambda u, t: (len(u) % 3 != 0, 3)), (lambda s: None)


def main(argv=None):
    p = argparse.ArgumentParser(prog="appels-sid", description="Liste d'appels du matin pour Sid (aucun envoi).")
    base = argparse.ArgumentParser(add_help=False); base.add_argument("--a-blanc", action="store_true", help="aucune écriture")
    sp = p.add_subparsers(dest="cmd", required=True)
    for nom in ("preparer", "sourcer", "jour"): sp.add_parser(nom, parents=[base]).add_argument("--jour", default=None)
    sc = sp.choices["sourcer"]; sc.add_argument("--dept", default=None, choices=list(NORMANDIE), help="limite le sourcing à un département"); sc.add_argument("--simulation", action="store_true", help="aucun réseau, données fictives, rien n'est écrit")
    for nom in ("etat", "google-autoriser", "rediriger-liste", "rendre-liste"): sp.add_parser(nom, parents=[base])
    c = sp.add_parser("annuler", parents=[base]); c.add_argument("jour", nargs="?"); c.add_argument("--force", action="store_true")
    for nom in ("installer-tache", "retirer-tache"): sp.add_parser(nom, parents=[base]).add_argument("--oui", action="store_true")
    args = p.parse_args(argv); M.exiger("appels-sid", args.cmd, getattr(args, "a_blanc", False) or getattr(args, "simulation", False))      # --simulation n'écrit rien et n'ouvre aucun réseau : permise sur toute machine, comme --a-blanc
    try:
        conf = cfg(); jour = date_valide(getattr(args, "jour", None) or date.today().isoformat()) if args.cmd in ("preparer", "sourcer", "jour") else None
        if args.cmd == "preparer": return cmd_preparer(conf, jour, args.a_blanc)
        if args.cmd == "sourcer":
            if args.simulation: _simulation()
            return cmd_sourcer(conf, jour, args.a_blanc or args.simulation, [args.dept] if args.dept else None)
        if args.cmd == "jour": return cmd_jour(conf, jour, args.a_blanc)
        if args.cmd == "etat": return cmd_etat(conf)
        if args.cmd == "annuler": return cmd_annuler(date_valide(args.jour) if args.jour else None, args.force, args.a_blanc)
        if args.cmd == "rediriger-liste": return cmd_rediriger(args.a_blanc)
        if args.cmd == "rendre-liste": return cmd_rendre(args.a_blanc)
        if args.cmd == "google-autoriser": return cmd_google_autoriser(conf, args.a_blanc)
        return cmd_tache("installer" if args.cmd == "installer-tache" else "retirer", args.oui, conf)
    except ErreurAgent as e:
        print(f"  ! {e}"); return 2
    except OSError as e:
        print(f"  ! erreur de fichier : {e.strerror or type(e).__name__} (rien n'a été marqué si l'écriture a échoué)"); return 2


if __name__ == "__main__":
    sys.exit(main())
