#!/usr/bin/env python3
"""Agent Prospection : trouve des entreprises du bâtiment, cherche un contact public, prépare les lots, envoie SEULEMENT les lots validés.

  python agents\\prospection.py jour [--a-blanc]       journée complète : réponses -> recherche -> lot -> relances -> publication Discord -> approbation -> envoi
  python agents\\prospection.py chercher [--a-blanc]   annuaire officiel -> site ? -> e-mail publié / Facebook / LinkedIn -> prospection-trouves.csv
  python agents\\prospection.py preparer [--a-blanc]   lot de 10 par boîte -> messages-a-valider.md (statut « à valider ») + apercu-lot.html
  python agents\\prospection.py relances [--a-blanc]   UNE relance J+2 (via suivi-prospects.csv) -> bloc « à valider »
  python agents\\prospection.py publier [--a-blanc]    poste le lot sur Discord (salon business, bot Jarvis par REST, sans lancer Jarvis)
  python agents\\prospection.py approuver [--a-blanc]  lit Discord : « ok lot » ou ✅ de Liam SEUL -> blocs « validé »
  python agents\\prospection.py envoyer [--a-blanc]    envoie les blocs « validé » ET approuvés sur Discord (API Gmail OAuth si « api » actif dans reponses-config.json, sinon SMTP ; 10/boîte/jour, pause aléatoire)
  python agents\\prospection.py reponses [--a-blanc]   agents\\reponses.py (classe, poste les positives sur Discord, exclut STOP et refus)

--a-blanc : AUCUN envoi, aucune écriture (fichiers, état, statuts), rien posté sur Discord ; seules des lectures publiques (annuaire, sites) ont lieu.
Jamais d'envoi sans bloc « validé » par Liam ; jamais d'envoi sur Facebook/LinkedIn (le message est seulement préparé) ; STOP et refus = exclusion définitive.
Secrets : agents\\gmail-token-<adresse>.json (API, un jeton par compte) ou B2B\\.env (mots de passe d'application, repli SMTP), jamais affichés. Mode API : les comptes de reponses-config.json › api › comptes, 10 envois par jour chacun, un prospect = une seule boîte ; un compte sans jeton valide est sauté. Réglages : agents\\prospection-config.json. État : agents\\prospection-etat.json."""
import argparse, csv, html, json, random, re, smtplib, socket, subprocess, sys, time, traceback, urllib.error, urllib.parse, urllib.request, urllib.robotparser
socket.setdefaulttimeout(60)   # filet : tout appel réseau sans délai propre (Gmail, httplib2, DNS...) abandonne après 60 s au plus par opération
from datetime import date, datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path

ICI = Path(__file__).resolve().parent
RACINE = ICI.parent
sys.path.insert(0, str(ICI)); sys.path.insert(0, str(RACINE / "sites" / "moteur"))
import generer as G, redaction as R, suivi as S, reponses as P, gmail_api as GA, zone as ZN, filtre_adresses as FA, machine as M   # machine : config locale + machine active

CONFIG, ETAT = ICI / "prospection-config.json", ICI / "prospection-etat.json"
TROUVES, MESSAGES, APERCU, LOTS = RACINE / "prospection-trouves.csv", RACINE / "messages-a-valider.md", RACINE / "apercu-lot.html", RACINE / "lots"
UA = "LM-MULTI-SERVICES-prospection"
COLS = ["nom", "metier", "ville", "telephone", "email", "site_actuel", "note_besoin", "siren", "cp", "email_type", "email_source", "source",
        "facebook", "linkedin", "formulaire", "date_collecte", "statut", "osm", "modele", "fiche_web", "score"]
NAF_BATIMENT = [("43.21A", "électricien"), ("43.22A", "plombier-chauffagiste"), ("43.91B", "couvreur"), ("43.99C", "maçon"),
                ("43.34Z", "peintre"), ("43.32A", "menuisier"), ("43.31Z", "plâtrier")]
NAF_COMMERCES = [("56.10A", "restaurant"), ("56.10C", "restauration rapide"), ("96.02A", "coiffeur"), ("47.76Z", "fleuriste"),
                 ("10.71C", "boulangerie"), ("10.71D", "pâtisserie"), ("45.20A", "garage automobile"),
                 ("49.32Z", "taxi"), ("85.53Z", "auto-école"), ("96.02B", "esthéticienne")]   # taxi, auto-école, esthéticienne : cherchés seulement quand leur page exemple est déclarée (liens-metiers.json) et leur modèle de message ajouté (redaction.py)
NAF = NAF_BATIMENT + NAF_COMMERCES  # le curseur « bâtiment » (état : curseur) ne parcourt que NAF_BATIMENT ; les commerces ont un curseur par code NAF (état : curseurs_com)
DEPARTEMENTS = ZN.departements_ouverts(4)   # tous les départements de l'annuaire, vague 1 d'abord (zone.py) ; seuls ceux des vagues ouvertes sont parcourus : depts_ouverts()


def depts_ouverts():
    return ZN.departements_ouverts()
PETITS = "NN,00,01,02,03,11"  # sans salarié à moins de 20 : artisans, pas de grands groupes
DEFAUT = {"par_boite_par_jour": 10, "reseaux_par_jour": 10, "pause_envoi_s": [90, 300], "cible_trouves": 30, "max_examinees": 300, "osm_requetes_par_passage": 3, "pause_overpass_s": 15, "osm_max_examinees": 40, "osm_max_jour": 300, "decouverte_places": False, "places_max_jour": 30, "places_requetes_par_passage": 1, "pause_site_s": 3, "rayon_osm_m": 40000, "appels_par_jour": 100, "liste_appels_heure": "08:00", "liste_appels_md": False, "decouverte_osm": False, "formulaires_par_jour": 10, "pagespeed_par_jour": 30, "seuil_pagespeed": 50, "lent_secondes": 4, "lourd_octets": 1500000,
          "recherches_reseaux_par_jour": 40, "ans_site_vieux": 4, "envoi_automatique": False, "ecoute_max_heures": 12, "ecoute_pause_s": 60,
          "heure_limite": "17:00", "lot_attendre_les_deux_boites": False, "seuil_faiblesse": 25, "mesure_images": True, "verifier_sitemap": False, "montee_pas": 10, "montee_plafond": 50, "taux_alerte_retours": 0.05, "plaintes_max": 1, "retours_min_envois": 20,
          "quota_par_boite": 10, "cycle_minutes": 10, "recul_max_minutes": 60, "lot_min_emails": 5, "epuise_apres": 3, "seuil_vague": 15}
DERNIER, VERROU = ICI / "prospection-dernier-lancement.txt", ICI / "prospection.verrou"
LEGAL = {"sarl", "eurl", "sas", "sasu", "ei", "sa", "selarl", "sci", "ets", "etablissements", "entreprise", "societe", "la", "le", "les", "de", "du", "des", "et", "l", "d", "au", "aux"}
GRATUITS = {"gmail.com", "hotmail.com", "hotmail.fr", "outlook.com", "outlook.fr", "yahoo.fr", "yahoo.com", "orange.fr", "wanadoo.fr", "free.fr", "sfr.fr", "laposte.net", "live.fr", "icloud.com", "neuf.fr", "bbox.fr"}
GENERIQUES = {"contact", "info", "infos", "accueil", "bonjour", "devis", "commercial", "secretariat", "administration", "admin", "agence", "entreprise", "societe", "mail", "courrier", "service", "direction", "compta"}
MAUVAIS_MAIL = re.compile(r"no-?reply|noreply|abuse|dpo@|privacy|sentry|wixpress|example\.|exemple\.|domain\.|votre-?(?:nom|mail|adresse)|\.(?:png|jpe?g|gif|webp|svg|css|js)$", re.I)
CHEMINS = ["", "/contact", "/contact/", "/contactez-nous", "/nous-contacter", "/contact.html", "/contact.php", "/mentions-legales", "/mentions-legales/", "/mentions-legales.html", "/mentions_legales", "/mentions", "/legal", "/a-propos", "/qui-sommes-nous"]
RESEAU_MAUVAIS = re.compile(r"sharer|share\.php|/plugins|/tr\?|/dialog|/policies|/legal|/help|/login|/recover|/groups/|/events/|/watch|/hashtag|/pages/create|\.php", re.I)


# --- réglages et état -------------------------------------------------------------------------------------
def cfg():
    c = dict(DEFAUT)
    if CONFIG.exists(): c.update({k: v for k, v in json.loads(CONFIG.read_text(encoding="utf-8-sig")).items() if not k.startswith("_")})
    return M.surcharge_locale(CONFIG, c)


def lancer_generer(lot_csv):
    """Maquettes LOCALES des prospects du lot (sites\\moteur\\generer.py). Profil serveur (portable 6 Go) : jamais lancé. -> True si lancé."""
    if M.serveur(): print("  maquettes : non générées (profil serveur : aucun processus lourd)"); return False
    subprocess.run([sys.executable, str(RACINE / "sites" / "moteur" / "generer.py"), str(lot_csv)], check=False, timeout=900); return True


def boites():
    c = P.cfg()
    if c["api"]["actif"]: return [a for a in c["api"]["comptes"] if GA.jeton_existe(a)]  # mode API : les comptes autorisés (un jeton chacun)
    return [x["adresse"] for x in c["comptes"]]


def etat_lire():
    e = json.loads(ETAT.read_text(encoding="utf-8")) if ETAT.exists() else {}
    for k, v in (("curseur", {"i": 0, "page": 1}), ("vus", {}), ("envois", {}), ("relances", []), ("lots", {}), ("envoyes", {}), ("recherches", {}), ("lots_discord", {}), ("lots_box", {}), ("ok_utilises", []), ("publies", []), ("approuves", [])): e.setdefault(k, v)
    return e


def etat_ecrire(e, a_blanc):
    if not a_blanc: ETAT.write_text(json.dumps(e, ensure_ascii=False, indent=1), encoding="utf-8")


def aujourdhui(): return str(date.today())


# --- montée en charge des envois : 10 par boîte et par jour, puis +10 chaque jour jusqu'au plafond, gelée si les retours montent ----------
RETOURS = ICI / "prospection-retours.json"   # écrit par reponses.py : {"rebonds": {identifiant: date}, "plaintes": {identifiant: date}}


def retours_recents(etat, jours=14, j=None):
    """(envois, rebonds, plaintes) sur les `jours` derniers jours : envois relus dans l'état, retours dans prospection-retours.json (comptés d'après les en-têtes, corps jamais lus)."""
    j = j or date.today(); debut = max(str(j - timedelta(days=jours)), etat.get("montee", {}).get("retours_depuis", ""))   # après « montee --reprendre », seuls les retours plus récents comptent
    envois = sum(sum(b.values()) for d, b in etat.get("envoyes", {}).items() if d >= debut)
    try: r = json.loads(RETOURS.read_text(encoding="utf-8")) if RETOURS.exists() else {}
    except ValueError: r = {}
    return envois, sum(1 for d in r.get("rebonds", {}).values() if d >= debut), sum(1 for d in r.get("plaintes", {}).values() if d >= debut)


def palier_du_jour(etat, conf, j=None):
    """Palier par boîte pour aujourd'hui : montee_pas le premier jour (demain), puis +montee_pas par jour, plafonné à montee_plafond ; figé si la montée est gelée."""
    j = j or date.today(); m = etat["montee"]; depart = date.fromisoformat(m["depart"])
    p = min(conf["montee_plafond"], conf["montee_pas"] * (1 + max(0, (j - depart).days)))
    return min(p, m["palier_gele"]) if m.get("gele") else p


def verifier_retours(etat, conf, palier, api=None, a_blanc=False, j=None):
    """Taux de rebond (rebonds / envois) ou plainte : si le seuil est dépassé, la montée est gelée au palier actuel et Liam est prévenu UNE fois dans #business. -> True si gelée à l'instant."""
    m = etat["montee"]
    if m.get("gele"): return False
    envois, rebonds, plaintes = retours_recents(etat, j=j)
    taux = rebonds / envois if envois >= conf["retours_min_envois"] else 0
    if not (taux >= conf["taux_alerte_retours"] or plaintes >= conf.get("plaintes_max", 1)): return False
    geler(etat, conf, palier, f"rebonds {rebonds}/{envois}" + (f", plaintes {plaintes}" if plaintes else ""), f"{rebonds} rebond(s) sur {envois} envoi(s) sur 14 jours" + (f", {plaintes} plainte(s)" if plaintes else ""), api, a_blanc, j)
    return True


def geler(etat, conf, palier, motif, detail, api=None, a_blanc=False, j=None):
    """Fige la montée au palier actuel et prévient Liam UNE fois dans #business (rebonds, plaintes, ou refus d'un envoi par Gmail). Sans effet si déjà gelée ou sans montée."""
    m = etat.get("montee")
    if not m or m.get("gele"): return False
    m.update(gele=True, palier_gele=palier, gele_le=str(j or date.today()), motif=motif)
    if not a_blanc:
        acces = acces_discord()
        if acces:
            jeton, salon, uid = acces
            r = (api or discord)(jeton, "POST", f"/channels/{salon}/messages", {"content": f"<@{uid}> **Montée en charge arrêtée** : {detail}"
                                 + f". Palier figé à {palier} par boîte (plafond prévu : {conf['montee_plafond']}). Aucun envoi n'est supprimé : vérifie puis `python agents\\prospection.py montee --reprendre`.", "allowed_mentions": {"users": [uid]}})
            m["alerte_envoyee"] = bool(r and "id" in r)
    return True


def avec_montee(conf, a_blanc=False, api=None, j=None):
    """Copie de conf dont quota_par_boite et par_boite_par_jour valent le palier du jour. État : etat['montee'] = date de départ (demain, au premier appel), gel éventuel. Désactivable : montee = false."""
    if not conf.get("montee", True): return conf
    etat = etat_lire(); j = j or date.today(); neuf = "montee" not in etat
    if neuf: etat["montee"] = {"depart": str(j + timedelta(days=1)), "pas": conf["montee_pas"]}
    p = palier_du_jour(etat, conf, j); gele = verifier_retours(etat, conf, p, api, a_blanc, j)
    etat["montee"]["palier"] = p; etat["montee"]["maj"] = str(j)
    if (neuf or gele or etat["montee"].get("maj_ecrite") != str(j)): etat["montee"]["maj_ecrite"] = str(j); etat_ecrire(etat, a_blanc)
    return {**conf, "quota_par_boite": p, "par_boite_par_jour": p, "palier": p, "montee_gelee": bool(etat["montee"].get("gele"))}


def cmd_montee(a_blanc, conf, reprendre=False):
    """Affiche la montée en charge ; --reprendre lève le gel (la montée repart du palier figé)."""
    etat = etat_lire()
    if reprendre and etat.get("montee", {}).get("gele") and not a_blanc:
        m = etat["montee"]; m.pop("gele"); m.pop("alerte_envoyee", None); m["retours_depuis"] = aujourdhui(); m["depart"] = str(date.today() - timedelta(days=max(0, m["palier_gele"] // conf["montee_pas"] - 1)))
        etat_ecrire(etat, False); print("Gel levé : la montée repart du palier figé.")
    c = avec_montee(conf, a_blanc); m = etat_lire().get("montee", {}); e, r, p = retours_recents(etat_lire())
    print(f"Montée en charge : palier {c['palier']} par boîte aujourd'hui (pas {conf['montee_pas']}, plafond {conf['montee_plafond']}), départ le {m.get('depart', '—')}" + (f". GELÉE depuis le {m['gele_le']} ({m['motif']})" if m.get("gele") else "")
          + f". Sur 14 jours : {e} envoi(s), {r} rebond(s), {p} plainte(s).")


# --- petits outils ------------------------------------------------------------------------------------------
def norm(s): return re.sub(r"[^a-z0-9]+", " ", G.sans_accent(s).lower()).strip()


def beau(s):  # SAINT-ETIENNE-DU-ROUVRAY -> Saint-Etienne-du-Rouvray
    if not s.isupper(): return s
    t = re.sub(r"[A-Za-zÀ-ÿ']+", lambda m: m.group(0).capitalize(), s)
    return re.sub(r"(?<=[ -])(De|Du|Des|La|Le|Les|Sur|Sous|En|Lès|Aux|Au|Et)(?=[ -])", lambda m: m.group(1).lower(), t)


def nom_affiche(nc):
    m = re.search(r"\(([^)]+)\)", nc)
    interieur = m.group(1).strip() if m else ""
    brut = interieur if len(interieur) >= 5 else re.sub(r"\s*\([^)]*\)", "", nc).strip()
    return beau(brut)


def jetons(nom): return [t for t in norm(nom).split() if t not in LEGAL and len(t) > 1]


def domaines(nc):
    t = jetons(re.sub(r"[()]", " ", nc))
    t = t[:3]
    if not t or len("".join(t)) < 5: return []
    bases = list(dict.fromkeys(["".join(t), "-".join(t)]))
    return [b + tld for b in bases for tld in (".fr", ".com")]


def lire_page(url, timeout=8, octets=400_000, chrono=None, robots_timeout=5):
    """(url_finale, en-têtes, texte) ou None. Respecte robots.txt (en cas de doute : autorisé)."""
    try:
        p = urllib.parse.urlparse(url)
        rp = urllib.robotparser.RobotFileParser()
        try:
            rq = urllib.request.Request(f"{p.scheme}://{p.netloc}/robots.txt", headers={"User-Agent": UA})
            rp.parse(urllib.request.urlopen(rq, timeout=robots_timeout).read(100_000).decode("utf-8", "replace").splitlines())
            if not rp.can_fetch(UA, url): return None
        except Exception: pass
        rq = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "fr"})
        t0 = time.time()
        with urllib.request.urlopen(rq, timeout=timeout) as r:
            brut = r.read(octets)
            cs = r.headers.get_content_charset() or "utf-8"
            if chrono is not None: chrono["sec"] = time.time() - t0; chrono["octets"] = len(brut)
            return r.geturl(), r.headers, brut.decode(cs, "replace")
    except Exception:
        return None


# --- annuaire officiel ------------------------------------------------------------------------------------
def appel_api(dept, naf, page, ouvrir=urllib.request.urlopen, dormir=time.sleep):
    """Annuaire officiel. Si l'API refuse (429, 5xx, réseau) : jusqu'à 3 nouveaux essais après 3, 10 puis 30 s (Retry-After respecté, 60 s au plus) ; ensuite l'erreur remonte et la boucle recule."""
    q = urllib.parse.urlencode({"activite_principale": naf, "departement": dept, "etat_administratif": "A", "tranche_effectif_salarie": PETITS,
                                "per_page": 25, "page": page})
    rq = urllib.request.Request("https://recherche-entreprises.api.gouv.fr/search?" + q, headers={"User-Agent": UA})
    for essai, attente in enumerate((0, 3, 10, 30)):
        if attente: dormir(attente)
        try:
            with ouvrir(rq, timeout=30) as r: return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504) or essai == 3: raise
            ra = (e.headers.get("Retry-After") if e.headers else "") or ""
            if ra.isdigit(): dormir(min(int(ra), 60))
        except (urllib.error.URLError, TimeoutError, OSError):
            if essai == 3: raise


def metiers_actifs():
    """Clés des métiers qui ont une page exemple déclarée dans agents\\liens-metiers.json (lecture du fichier, aucun réseau : « en ligne » est vérifié plus tard par lien_exemple)."""
    f = ICI / "liens-metiers.json"
    try: return {k.split("-")[0] for k, u in json.loads(f.read_text(encoding="utf-8")).items() if u}
    except (OSError, ValueError): return set()


def metier_actif(metier):
    """Un métier n'entre dans la recherche que si une page exemple existe pour lui (règle de Liam, 27 oct.). Les autres s'activent seuls quand leur ligne est ajoutée au fichier."""
    cle = R.cle_metier(metier or "")
    return bool(cle) and cle in metiers_actifs()


def curseurs(etat):
    """Un curseur par code NAF : {naf: {"i": indice du département, "page": n}} (état : curseurs_naf). Au premier appel, l'ancien curseur unique du bâtiment
    (département par département) et celui des commerces (curseurs_com) sont convertis sans perdre la progression ; les pages déjà vues (vus) ne sont pas touchées."""
    cn = etat.get("curseurs_naf")
    if cn is None:
        cn = etat["curseurs_naf"] = {}
        for naf, c in etat.pop("curseurs_com", {}).items(): cn[naf] = c
        old = etat.get("curseur")
        if old and not old.get("migre"):
            n = len(NAF_BATIMENT); d, k = old["i"] // n, old["i"] % n
            for j, (naf, _) in enumerate(NAF_BATIMENT):
                cn.setdefault(naf, {"i": d + 1, "page": 1} if j < k else ({"i": d, "page": old["page"]} if j == k else {"i": d, "page": 1}))
            old["migre"] = True
    return cn


def _alimenter(etat, naf, metier, data, dept):
    """Résultats d'une page de l'annuaire -> tampon du code NAF (siège dans le département, pas déjà vu). Rien n'est marqué « vu » avant la livraison."""
    tamp = etat.setdefault("tampon", {}).setdefault(naf, [])
    deja = {x["siren"] for x in tamp}
    for r in data.get("results", []):
        s = r.get("siege", {})
        if r["siren"] in etat["vus"] or r["siren"] in deja or ZN.dept_de_cp(str(s.get("code_postal", ""))) != dept or not ZN.dans_zone(cp=str(s.get("code_postal", ""))): continue   # hors zone : jamais retenu
        tamp.append({"siren": r["siren"], "nc": r.get("nom_complet", ""), "metier": metier, "cp": s.get("code_postal", ""), "ville": beau(s.get("libelle_commune", "")), "dept": dept})
        deja.add(r["siren"])


def _livrer(etat, naf, k):
    tamp = etat.setdefault("tampon", {}).get(naf, [])
    sortie, etat["tampon"][naf] = tamp[:k], tamp[k:]
    for x in sortie: etat["vus"][x["siren"]] = "examiné"
    return sortie


def _suite(cur, data):  # page suivante, ou département suivant
    if cur["page"] >= data.get("total_pages", 1) or cur["page"] >= 400: cur["i"] += 1; cur["page"] = 1
    else: cur["page"] += 1


def groupes_actifs(etat):
    """[(clé du métier, [(code NAF, libellé)])] : métiers actifs qui ont encore des pages à lire, bâtiment et commerces en alternance (électricien, restaurant, plombier, …)."""
    cn, tamp = curseurs(etat), etat.get("tampon", {})
    nd = len(depts_ouverts()); vivant = lambda naf: cn.get(naf, {"i": 0})["i"] < nd or bool(tamp.get(naf))
    gb, gc = {}, {}
    for liste, g in ((NAF_BATIMENT, gb), (NAF_COMMERCES, gc)):
        for naf, m in liste:
            if metier_actif(m) and vivant(naf): g.setdefault(R.cle_metier(m), []).append((naf, m))
    b, c, out = list(gb.items()), list(gc.items()), []
    for k in range(max(len(b), len(c))):
        if k < len(b): out.append(b[k])
        if k < len(c): out.append(c[k])
    return out


def candidats(etat, n, api=appel_api, pause=0.2):
    """Jusqu'à ~n nouvelles entreprises, vague 1 (Seine-Maritime, Eure) d'abord, puis les vagues ouvertes, un tour par code NAF actif (un curseur par code, état : curseurs_naf). Répartition : n divisé entre les métiers actifs
    (environ un tiers chacun avec trois métiers) ; les métiers sont alternés bâtiment / commerce, donc dès que n >= 2 chaque famille en a au moins un. Le siège doit être dans le département."""
    cn, out = curseurs(etat), []; depts = depts_ouverts()
    groupes = groupes_actifs(etat)
    if not groupes: return out
    base, reste = divmod(n, len(groupes))
    quota = {cle: base + (1 if i < reste else 0) for i, (cle, _) in enumerate(groupes)}
    pris, ptr = {cle: 0 for cle, _ in groupes}, {cle: 0 for cle, _ in groupes}
    while len(out) < n:
        avance = False
        for cle, codes in groupes:
            reste_g = min(quota[cle] - pris[cle], n - len(out))
            vivants = [x for x in codes if cn.setdefault(x[0], {"i": 0, "page": 1})["i"] < len(depts) or etat.get("tampon", {}).get(x[0])]
            if reste_g <= 0 or not vivants: continue
            naf, metier = vivants[ptr[cle] % len(vivants)]; ptr[cle] += 1
            c = cn[naf]
            if len(etat.get("tampon", {}).get(naf, [])) < reste_g and c["i"] < len(depts):
                dept = depts[c["i"]]
                try: data = api(dept, naf, c["page"])
                except Exception as e:
                    print(f"  annuaire : erreur {type(e).__name__} ({dept} {naf} p.{c['page']}), arrêt de ce passage"); _client["erreur_api"] = True; return out
                _alimenter(etat, naf, metier, data, dept); _suite(c, data)
                time.sleep(pause)
            neufs = _livrer(etat, naf, reste_g)
            out += neufs; pris[cle] += len(neufs); avance = True
        if not avance: break
    return out


# --- diagnostic du site, e-mail, réseaux ----------------------------------------------------------------
def verifie(texte, c):  # la page parle bien de CETTE entreprise (ville, code postal ou SIREN)
    t = norm(texte); sir = c["siren"]
    return norm(c["ville"]) in t or c["cp"] in texte or bool(sir and (sir in re.sub(r"\s+", "", texte) or f"{sir[:3]} {sir[3:6]} {sir[6:]}" in texte))


def trouver_site(c, lire=lire_page):
    for d in domaines(c["nc"]):
        for sch in ("https", "http"):
            r = lire(f"{sch}://{d}")
            if r:
                if verifie(r[2], c): return r
                break
    return None


ORDRE_CONSTATS = ["https", "certificat", "mobile", "appel", "pagespeed", "copyright", "flash", "tableaux", "iframe", "lent", "lourd"]  # ordre de citation dans le message (1 ou 2 constats)


def constats_statiques(url, texte, ans=4, j=None):
    """[(code, phrase)] lus dans la page elle-même : HTTPS, viewport, © ancien, Flash, mise en page à tableaux. Que des faits vérifiables, jamais un jugement."""
    j = j or date.today(); out = []
    if url.startswith("http://"): out.append(("https", "site sans HTTPS (adresse en http, sans redirection vers https)"))
    if not re.search(r'<meta[^>]+name=["\']viewport', texte, re.I): out.append(("mobile", "site non adapté au mobile"))
    if not re.search(r'href=["\']tel:', texte, re.I): out.append(("appel", "aucun numéro cliquable sur la page d'accueil (pas de lien pour appeler d'un geste)"))
    annees = [int(y) for y in re.findall(r"(?:©|&copy;|copyright)[^0-9<]{0,20}(?:\d{4}\s*[-–]\s*)?(\d{4})", texte, re.I) if 1995 <= int(y) <= j.year]
    if annees and max(annees) <= j.year - ans: out.append(("copyright", f"site non mis à jour depuis {max(annees)} (mention © {max(annees)})"))
    if re.search(r'<(?:object|embed)[^>]+(?:\.swf|shockwave-flash)|["\'][^"\'<>]+\.swf["\']', texte, re.I): out.append(("flash", "page qui utilise Flash (technologie arrêtée fin 2020)"))
    nt, nd = len(re.findall(r"<table\b", texte, re.I)), len(re.findall(r"<div\b", texte, re.I))
    if nt >= 3 and nt > nd and re.search(r"cellpadding|cellspacing|<table[^>]+width=", texte, re.I): out.append(("tableaux", "mise en page construite avec des tableaux HTML"))
    return out


POIDS = {"https": 40, "certificat": 40, "mobile": 30, "flash": 30, "lent": 25, "pagespeed": 25, "lourd": 20, "images": 15, "copyright": 15, "tableaux": 15, "iframe": 15, "requetes": 10,
         "appel": 10, "title": 10, "description": 8, "h1": 8, "alt": 8, "sitemap": 6, "local": 8}   # poids du score de faiblesse (0 à 100) : seuls les constats MESURÉS comptent
SURS = ["https", "certificat", "mobile", "flash", "lent", "lourd", "pagespeed", "copyright", "iframe", "tableaux", "images", "requetes", "appel", "title", "h1", "description", "alt", "local", "sitemap"]  # du plus sûr au moins sûr


def score_faiblesse(cs):
    """Score 0 à 100 : somme des poids des constats mesurés (plafonnée à 100)."""
    return min(100, sum(POIDS.get(k, 0) for k, _ in cs))


def trier_constats(cs):
    """Les plus parlants (poids fort) puis les plus sûrs d'abord : le message n'en cite que 2."""
    return sorted(cs, key=lambda kp: (-POIDS.get(kp[0], 0), SURS.index(kp[0]) if kp[0] in SURS else 99))


def constats_seo(texte, url="", ans=None):
    """[(code, phrase)] SEO de base lus dans le code de la page d'accueil. Chaque phrase est un fait compté, jamais une promesse de classement."""
    out = []
    m = re.search(r"<title[^>]*>(.*?)</title>", texte, re.I | re.S); t = html.unescape(re.sub(r"\s+", " ", m.group(1))).strip() if m else ""
    if not m: out.append(("title", "aucune balise title sur la page d'accueil"))
    elif len(t) < 10: out.append(("title", f"titre de page très court (« {t[:30]} », {len(t)} caractères)" if t else "balise title vide"))
    if not re.search(r'<meta[^>]+name=["\']description["\'][^>]*content=["\'][^"\']{10,}', texte, re.I) and not re.search(r'<meta[^>]+content=["\'][^"\']{10,}["\'][^>]*name=["\']description', texte, re.I):
        out.append(("description", "pas de meta description sur la page d'accueil"))
    if not re.search(r"<h1\b", texte, re.I): out.append(("h1", "aucun titre principal (h1) sur la page d'accueil"))
    imgs = re.findall(r"<img\b[^>]*>", texte, re.I)
    sans = [i for i in imgs if not re.search(r'\balt=["\'][^"\']+["\']', i, re.I)]
    if len(imgs) >= 3 and len(sans) >= 2 and len(sans) * 2 >= len(imgs): out.append(("alt", f"{len(sans)} images sur {len(imgs)} sans texte alternatif"))
    corps = re.sub(r"<(script|style)\b.*?</\1>", " ", texte, flags=re.I | re.S); brut = html.unescape(re.sub(r"<[^>]+>", " ", corps))
    if len(brut) > 400 and not re.search(r"(?:\+33|\b0)[\s.]?[1-9](?:[\s.]?\d{2}){4}", brut) and not re.search(r"\b\d{5}\b", brut) and not re.search(r'href=["\']tel:', texte, re.I):
        out.append(("local", "ni numéro de téléphone ni adresse lisibles dans le texte de la page d'accueil"))
    n = len(re.findall(r"<(?:script|link|img|iframe)\b[^>]+(?:src|href)=", texte, re.I))
    if n >= 60: out.append(("requetes", f"la page d'accueil appelle au moins {n} fichiers (scripts, styles, images)"))
    return out


def images_lourdes(url, texte, o=None, seuil=500_000, max_images=3, pause=1.0):
    """Taille annoncée (Content-Length) de 3 images de la page au plus, une requête HEAD chacune. -> phrase ou ''."""
    srcs = [urllib.parse.urljoin(url, html.unescape(s)) for s in re.findall(r"<img\b[^>]+src=[\"']([^\"']+\.(?:jpe?g|png|bmp|tiff?))(?:\?[^\"']*)?[\"']", texte, re.I)][:max_images]
    taille = (o or {}).get("taille") or (lambda u: _taille_distante(u))
    for s in srcs:
        n = taille(s)
        if n and n >= seuil: return f"une image de la page pèse {n / 1e6:.1f} Mo (JPEG/PNG non optimisé)".replace(".", ",")
        if not (o or {}).get("taille"): time.sleep(pause)
    return ""


def _taille_distante(u, timeout=8):
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}, method="HEAD"), timeout=timeout) as r: return int(r.headers.get("Content-Length") or 0)
    except Exception: return 0


def note_constats(cs, j=None):
    j = j or date.today()
    return f"{' ; '.join(p for _, p in cs[:2])} (constaté le {j:%d/%m})" if cs else ""


def diagnostic(url, texte, ans=4, aujourdhui_=None):
    """Constats FACTUELS lus dans la page (vide = rien à signaler). Rien d'autre n'est affirmé. Version complète avec mesures : constats_site."""
    j = aujourdhui_ or date.today()
    return note_constats(constats_statiques(url, texte, ans, j), j)


def mesurer_page(url, timeout=15, plafond=3_000_000):
    """(octets du code HTML, secondes) de la page d'accueil, ou None. Une seule requête, comme un visiteur."""
    try:
        t0 = time.time()
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=timeout) as r: n = len(r.read(plafond))
        return n, time.time() - t0
    except Exception: return None


def statut_http(url, timeout=10):
    """Code HTTP d'une adresse (0 si injoignable)."""
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=timeout) as r: return r.status
    except urllib.error.HTTPError as e: return e.code
    except Exception: return 0


def etat_https(host, timeout=8):
    """« certificat » si https répond mais que le certificat est refusé, « absent » sinon (l'appelant sait déjà que https n'a pas répondu normalement)."""
    import ssl
    try:
        with urllib.request.urlopen(urllib.request.Request("https://" + host, headers={"User-Agent": UA}), timeout=timeout, context=ssl._create_unverified_context()): return "certificat"
    except Exception: return "absent"


def pagespeed(url, timeout=90):
    """Score de performance mobile (0 à 100) mesuré par l'API publique PageSpeed Insights, ou None. Sans clé : quota limité, d'où le plafond pagespeed_par_jour."""
    try:
        q = urllib.parse.urlencode({"url": url, "strategy": "mobile", "category": "performance"})
        with urllib.request.urlopen(urllib.request.Request("https://www.googleapis.com/pagespeedonline/v5/runPagespeed?" + q, headers={"User-Agent": UA}), timeout=timeout) as r:
            return round(json.load(r)["lighthouseResult"]["categories"]["performance"]["score"] * 100)
    except Exception: return None


def iframes_carte(texte, base):
    out = []
    for s in re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', texte, re.I):
        u = urllib.parse.urljoin(base, html.unescape(s))
        if u.startswith("http") and re.search(r"map|carte|plan|itineraire", u, re.I): out.append(u)
    return out


def constats_site(url, texte, conf, etat=None, outils=None, j=None):
    """[(code, phrase)] triés par ORDRE_CONSTATS. Mesures du jour : poids et durée de la page d'accueil, cartes intégrées cassées (erreur 404 ou 410), et, seulement si rien d'autre
    n'est trouvé, un score PageSpeed mobile (plafond pagespeed_par_jour). `outils` remplace les mesures (tests sans réseau)."""
    o, j = outils or {}, j or date.today()
    trouves = dict(constats_statiques(url, texte, conf["ans_site_vieux"], j))
    if "https" in trouves and (o.get("https") or etat_https)(urllib.parse.urlparse(url).netloc) == "certificat":
        del trouves["https"]; trouves["certificat"] = "certificat HTTPS invalide ou expiré (le navigateur affiche un avertissement)"
    m = (o.get("mesure") or mesurer_page)(url)
    if m:
        octets, sec = m
        if sec >= conf["lent_secondes"]: trouves["lent"] = f"la page d'accueil met {sec:.1f} s à se charger".replace(".", ",")
        if octets >= conf["lourd_octets"]: trouves["lourd"] = f"la page d'accueil pèse {octets / 1e6:.1f} Mo (code seul, hors images)".replace(".", ",")
    for src in iframes_carte(texte, url)[:2]:
        s = (o.get("statut") or statut_http)(src)
        if s in (404, 410): trouves["iframe"] = f"carte intégrée qui ne s'affiche plus (erreur {s} constatée)"; break
    trouves.update(constats_seo(texte, url))
    if conf.get("mesure_images", True) and (o.get("taille") or o.get("images_reseau") or etat is not None):
        ph = images_lourdes(url, texte, o, pause=conf.get("pause_site_s", 1))
        if ph: trouves["images"] = ph
    if conf.get("verifier_sitemap") or o.get("sitemap"):
        if not (o.get("sitemap") or statut_http)(urllib.parse.urljoin(url, "/sitemap.xml")) in (200, True): trouves["sitemap"] = "pas de sitemap.xml à la racine du site"
    if score_faiblesse(trouves.items()) < conf.get("seuil_faiblesse", 25) and etat is not None:
        jour = etat.setdefault("pagespeed", {})
        if jour.get(aujourdhui(), 0) < conf["pagespeed_par_jour"]:
            jour[aujourdhui()] = jour.get(aujourdhui(), 0) + 1
            sc = (o.get("psi") or pagespeed)(url)
            if sc is not None and sc < conf["seuil_pagespeed"]: trouves["pagespeed"] = f"score PageSpeed mobile de {sc} sur 100"
    return trier_constats(list(trouves.items()))


def decode_cf(h):
    """Adresse masquée par Cloudflare (data-cfemail / email-protection#) : le premier octet est la clé XOR."""
    try: k = int(h[:2], 16); return "".join(chr(int(h[i:i + 2], 16) ^ k) for i in range(2, len(h) - 1, 2))
    except ValueError: return ""


def deobfusquer(texte):
    """Texte de la page + adresses publiées sous une forme simplement masquée : Cloudflare, « arobase », [at], [dot], entités, schema.org (JSON-LD, itemprop="email")."""
    t = html.unescape(urllib.parse.unquote(texte)).replace("\\u0040", "@")
    extra = [decode_cf(a or b) for a, b in re.findall(r'data-cfemail=["\']([0-9a-fA-F]{6,})["\']|/cdn-cgi/l/email-protection#([0-9a-fA-F]{6,})', t)]
    extra += re.findall(r'"email"\s*:\s*"([^"]+)"', t) + re.findall(r'itemprop=["\']email["\'][^>]*>\s*([^<\s]+)', t, re.I) + re.findall(r'itemprop=["\']email["\'][^>]*content=["\']([^"\']+)', t, re.I)
    t = re.sub(r"\s*[\[(\{]\s*(?:at|arobase|@)\s*[\])\}]\s*|\s+arobase\s+", "@", t, flags=re.I)
    t = re.sub(r"\s*[\[(\{]\s*(?:dot|point)\s*[\])\}]\s*", ".", t, flags=re.I)
    return t + "\n" + "\n".join(x.replace("mailto:", "") for x in extra if x)


def emails_page(texte, domaine):
    """(adresse, type) publiées sur la page ; on ne garde que le domaine du site ou une boîte grand public publiée par l'entreprise elle-même."""
    texte = deobfusquer(texte)
    out = {}
    for m in re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+", texte):
        a = m.lower().strip(".")
        dom = a.split("@")[1]
        if MAUVAIS_MAIL.search(a): continue
        meme = dom == domaine or dom.endswith("." + domaine)
        if not meme and dom not in GRATUITS: continue  # autre domaine = agence web, hébergeur… : ignoré
        generique = a.split("@")[0] in GENERIQUES
        out[a] = ("generique" if generique else "nominatif", 0 if meme else 2, 0 if generique else 1)
    return [(a, v[0]) for a, v in sorted(out.items(), key=lambda kv: kv[1][1:])]


def a_formulaire(texte):
    """Vrai si la page porte un formulaire de contact (un champ message) : pas une recherche, une connexion ni une newsletter."""
    for f in re.findall(r"<form\b.*?</form>", texte, re.S | re.I):
        if re.search(r"<textarea", f, re.I) and not re.search(r"type=[\"']password|newsletter|recherche|search|connexion|login", f[:500], re.I): return True
    return False


def reseaux_page(texte):
    fb = next((u for u in re.findall(r"https?://(?:www\.|fr-fr\.|m\.)?facebook\.com/[^\"'\s<>#]+", texte) if not RESEAU_MAUVAIS.search(u)), "")
    li = next((u for u in re.findall(r"https?://(?:[a-z]{2}\.|www\.)?linkedin\.com/(?:company|in)/[^\"'\s<>#?]+", texte)), "")
    return fb.split("?")[0].rstrip("/"), li.rstrip("/")


def chercher_reseau(c, lire=None):
    """Page Facebook par un moteur autre que Google (DuckDuckGo, version HTML), 1 requête. Acceptée seulement si le titre COMMENCE par le nom de l'entreprise et si la ville figure dans titre/extrait."""
    q = f'{nom_affiche(c["nc"])} {c["ville"]} facebook'
    try:
        rq = urllib.request.Request("https://html.duckduckgo.com/html/", data=urllib.parse.urlencode({"q": q}).encode(), headers={"User-Agent": "Mozilla/5.0 (compatible; " + UA + ")"})
        page = urllib.request.urlopen(rq, timeout=15).read(300_000).decode("utf-8", "replace")
    except Exception: return "", ""
    toks = jetons(nom_affiche(c["nc"]))[:3]
    for href, titre, extrait in re.findall(r'class="result__a" href="([^"]+)"[^>]*>(.*?)</a>.*?class="result__snippet"[^>]*>(.*?)</a>', page, re.S):
        u = urllib.parse.parse_qs(urllib.parse.urlparse(html.unescape(href)).query).get("uddg", [html.unescape(href)])[0]
        host = urllib.parse.urlparse(u).netloc.lower()
        fb = host.endswith("facebook.com") and not RESEAU_MAUVAIS.search(u)
        li = host.endswith("linkedin.com") and "/company/" in u
        t, debut = norm(re.sub(r"<[^>]+>", " ", titre + " " + extrait)), jetons(re.sub(r"<[^>]+>", " ", html.unescape(titre)))
        if (fb or li) and toks and debut[:len(toks)] == toks and norm(c["ville"]) in t:
            return (u.split("?")[0].rstrip("/"), "") if fb else ("", u.split("?")[0].rstrip("/"))
    return "", ""


def enrichir(c, etat, conf, lire=lire_page, reseau=chercher_reseau, stat=None, outils=None):
    """-> (ligne CSV, None) ou (None, motif). Site absent ou faible (constats vérifiables) ; contact par e-mail publié sur SON site, sinon formulaire de contact de son site
    (message à coller à la main), sinon Facebook/LinkedIn ; sinon on passe. `stat` reçoit : site, faible, constats, canal (pour le rapport)."""
    stat = stat if stat is not None else {}
    stat.update(site=False, faible=False, constats=[], canal="")
    if not metier_actif(c["metier"]): return None, "métier sans page exemple (agents\\liens-metiers.json) : " + c["metier"]
    ligne = {k: "" for k in COLS}
    ligne.update(nom=nom_affiche(c["nc"]), metier=c["metier"], ville=c["ville"], siren=c["siren"], cp=c["cp"], date_collecte=aujourdhui(), statut="trouvé",
                 source="l'annuaire officiel des entreprises")
    site = trouver_site(c, lire)
    fb = li = formulaire = ""
    if site:
        url, _, texte = site; stat["site"] = True
        cs = constats_site(url, texte, conf, etat, outils); sc = score_faiblesse(cs)
        stat["constats"], stat["faible"], stat["score"] = [k for k, _ in cs], sc >= conf["seuil_faiblesse"], sc
        if not stat["faible"]: return None, f"site correct (score de faiblesse {sc}, seuil {conf['seuil_faiblesse']})"
        ligne.update(site_actuel=url, note_besoin=note_constats(cs), score=str(sc))
        dom = urllib.parse.urlparse(url).netloc.lower().removeprefix("www.")
        pages, liens = [(url, texte)], re.findall(r'href=["\']([^"\']+)["\']', texte)
        suppl = [urllib.parse.urljoin(url, h) for h in liens if re.search(r"contact|mention|legal", h, re.I) and dom in urllib.parse.urljoin(url, h)]
        for ch in [urllib.parse.urljoin(url, x) for x in CHEMINS[1:]] + suppl[:4]:
            if len(pages) >= 8: break
            r = lire(ch)
            if r and r[2] not in [tx for _, tx in pages] and dom in r[0]: pages.append((r[0], r[2]))
        for i, (u, tx) in enumerate(pages):
            trouves = emails_page(tx, dom)
            if trouves and not ligne["email"]:
                ligne.update(email=trouves[0][0], email_type=trouves[0][1], email_source=url if i == 0 else "page contact / mentions légales de " + url)
                ligne["source"] += f" ; adresse publiée sur votre site ({dom})"
            f, l = reseaux_page(tx); fb, li = fb or f, li or l
            if not formulaire and a_formulaire(tx): formulaire = u
    if ligne["email"]: stat["canal"] = "email"; return ligne, None
    if formulaire:
        ligne.update(formulaire=formulaire, facebook=fb, linkedin=li); stat["canal"] = "formulaire"; return ligne, None
    if not (fb or li) and etat["recherches"].get(aujourdhui(), 0) < conf["recherches_reseaux_par_jour"]:
        etat["recherches"][aujourdhui()] = etat["recherches"].get(aujourdhui(), 0) + 1
        fb, li = reseau(c)
        time.sleep(2)
    if not (fb or li): return None, "aucun e-mail publié, formulaire ni page Facebook/LinkedIn"
    ligne.update(facebook=fb, linkedin=li); stat["canal"] = "reseau"
    return ligne, None


def lire_trouves():
    if not TROUVES.exists(): return []
    with open(TROUVES, encoding="utf-8-sig", newline="") as f: return list(csv.DictReader(f, delimiter=";"))


def ecrire_trouves(lignes, chemin=None):
    with open(chemin or TROUVES, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS, delimiter=";", extrasaction="ignore"); w.writeheader(); w.writerows(lignes)


def exclusions():
    """Clés (nom|ville) et e-mails à ne plus jamais contacter : STOP et refusé du suivi."""
    cles, mails = set(), set()
    for r in S.lire():
        if r["statut"] in ("STOP", "refusé", "exclu"):
            cles.add(S.cle(r))
            if r.get("email"): mails.add(r["email"].lower())
    cles |= set(etat_lire().get("appels", {}).get("exclus", []))
    try: mails |= {m.lower() for m in json.loads((ICI / "exclus-emails.json").read_text(encoding="utf-8"))}   # adresses écrites par reponses.py (refus, STOP)
    except (OSError, ValueError): pass
    return cles, mails


def compter(table, metier, st):
    """Ajoute une entreprise examinée au tableau {métier: compteurs}."""
    m = table.setdefault(metier, {"examinees": 0, "sans_site": 0, "site": 0, "faible": 0, "email": 0, "formulaire": 0, "reseau": 0, "telephone": 0, "constats": {}})
    m["examinees"] += 1
    if not st.get("site"): m["sans_site"] += 1;
    else: m["site"] += 1
    if st.get("faible"): m["faible"] += 1
    for k in st.get("constats", []): m["constats"][k] = m["constats"].get(k, 0) + 1
    if st.get("canal"): m[st["canal"]] += 1


def fusionner(dest, table):
    for metier, m in table.items():
        d = dest.setdefault(metier, {"examinees": 0, "sans_site": 0, "site": 0, "faible": 0, "email": 0, "formulaire": 0, "reseau": 0, "telephone": 0, "constats": {}})
        for k, v in m.items():
            if k == "constats":
                for c, n in v.items(): d["constats"][c] = d["constats"].get(c, 0) + n
            else: d[k] = d.get(k, 0) + v   # une clé absente d'un ancien état (ex. « telephone ») ne fait plus planter la fusion


def rapport_texte(table, titre):
    """Entonnoir par métier et par constat : où perd-on les prospects ?"""
    if not table: return f"{titre} : aucune entreprise examinée."
    tot = {"examinees": 0, "sans_site": 0, "site": 0, "faible": 0, "email": 0, "formulaire": 0, "reseau": 0, "telephone": 0, "constats": {}}; fusionner({k: tot for k in table}, table)
    L = [f"=== {titre} ===", f"{'métier':<24}{'examinées':>10}{'sans site':>10}{'avec site':>10}{'site faible':>12}{'e-mail':>8}{'formulaire':>11}{'réseau':>8}{'tél. seul':>10}"]
    for metier, m in sorted(table.items()) + [("TOTAL", tot)]:
        L.append(f"{metier:<24}{m['examinees']:>10}{m['sans_site']:>10}{m['site']:>10}{m['faible']:>12}{m['email']:>8}{m['formulaire']:>11}{m['reseau']:>8}{m.get('telephone', 0):>10}")
    L.append("Constats (sites faibles) : " + (" ; ".join(f"{k} {v}" for k, v in sorted(tot["constats"].items(), key=lambda kv: -kv[1])) or "aucun"))
    for metier, m in sorted(table.items()):
        if m["constats"]: L.append(f"  {metier} : " + ", ".join(f"{k} {v}" for k, v in sorted(m['constats'].items(), key=lambda kv: -kv[1])))
    contacts = tot["email"] + tot["formulaire"] + tot["reseau"] + tot.get("telephone", 0)
    pertes = [("pas de site faible (aucun site trouvé ou site correct)", tot["examinees"] - tot["faible"]), ("site faible mais aucun contact public (ni e-mail, ni formulaire, ni réseau)", tot["faible"] - contacts)]
    e, p = max(pertes, key=lambda x: x[1])
    L.append(f"Goulot : {e} : {p} entreprises perdues sur {tot['examinees']} examinées ({tot['faible']} sites faibles, dont {tot['email']} avec e-mail, {tot['formulaire']} avec formulaire, {tot['reseau']} avec réseau, {tot.get('telephone', 0)} téléphone seul).")
    return "\n".join(L)


def n_type(blocs, typ):
    return sum(1 for _, b in blocs if f'"type": "{typ}"' in b)


def cmd_rapport(conf):
    s = etat_lire().get("stats", {})
    print(rapport_texte(s.get("jours", {}).get(aujourdhui(), {}), "Aujourd'hui (annuaire officiel)")); print(rapport_texte(s.get("cumul", {}), "Cumul depuis le premier passage (annuaire officiel)"))
    e = etat_lire(); o = e.get("stats_osm", {})
    print(rapport_texte(o.get("jours", {}).get(aujourdhui(), {}), "Aujourd'hui (découverte depuis les sites, OpenStreetMap)")); print(rapport_texte(o.get("cumul", {}), "Cumul (découverte depuis les sites, OpenStreetMap)"))
    tel = e.get("sans_site_telephone", {}); print("Sans e-mail, avec téléphone (SMS stocké, jamais envoyé) : " + (", ".join(f"{m} {len(v)}" for m, v in sorted(tel.items())) or "aucun") + f" ; total {sum(len(v) for v in tel.values())}")


# --- exclusions permanentes : chaînes et franchises, services publics et organismes, domaine partagé, aucun constat vérifié (jamais recontactés) ------------------------------
CHAINES = re.compile(r"buffalo grill|hippopotamus|courtepaille|flunch|\bquick\b|mc ?donald|\bkfc\b|burger king|subway|domino'?s|pizza hut|del arte|la boucherie|trois brasseurs|taverne alsacienne|les tavernes|brioche dor|marie blach|carrefour|leclerc|intermarch|auchan|\blidl\b|\baldi\b|monoprix|\bmidas\b|norauto|speedy|feu vert|euromaster|\bpoint s\b|dessange|franck provost|saint[- ]algue|camille albane|tchip|coiff ?& ?co|\bengie\b|vinci|eiffage|bouygues|\bspie\b|actemium|vik [ée]nergies|saint-gobain|\bpoint p\b", re.I)
PUBLIC = re.compile(r"\bcrous\b|mairie|h[oô]tel de ville|universit|\bcampus\b|(?<!auto-)(?<!auto )[ée]cole|coll[èe]ge|lyc[ée]e|h[oô]pital|\bchu\b|centre hospitalier|clinique|ehpad|pr[ée]fecture|communaut[ée] (?:de|d')|m[ée]tropole|\bcaf\b|france travail|p[oô]le emploi|\bcpam\b|restaurant (?:universitaire|scolaire|administratif|d'entreprise)|cantine|croix[- ]rouge|association", re.I)
PUBLIC_MAIL = re.compile(r"crous|\.gouv\.fr|mairie|(?:^|\.)ac-[a-z-]+\.fr|univ-|\.edu$|caf\.fr|ameli\.fr", re.I)
ACCUEIL = re.compile(r"index\.\w+|accueil(?:\.\w+)?|home(?:\.\w+)?|[a-z]{2}(?:-[a-z]{2})?", re.I)


def hote(u): return urllib.parse.urlparse(u if "//" in (u or "") else "//" + (u or "")).netloc.lower().removeprefix("www.")


def partages_connus(lignes):
    """Domaines (site ou adresse e-mail, hors messageries gratuites) portés par au moins deux entreprises différentes : sites de réseau ou domaines partagés entre plusieurs établissements."""
    vus = {}
    for l in lignes:
        for d in {hote(l.get("site_actuel", "")), (l.get("email") or "").split("@")[-1].lower() if l.get("email") else ""} - {"", *GRATUITS}:
            vus.setdefault(d, set()).add(S.cle(l))
    return {d for d, v in vus.items() if len(v) >= 2}


def motif_exclusion(nom, email="", site="", partages=()):
    """Motif d'exclusion permanente (chaîne ou franchise, service public ou organisme, page d'établissement d'un site de réseau, domaine partagé) ou chaîne vide. Le motif « aucun constat vérifié » est dans enrichir_osm."""
    dm = (email or "").split("@")[-1].lower() if email else ""
    if CHAINES.search(nom): return "chaîne ou franchise"
    if PUBLIC.search(nom) or (dm and PUBLIC_MAIL.search(dm)): return "service public ou organisme"
    if site and [s for s in urllib.parse.urlparse(site).path.split("/") if s and not ACCUEIL.fullmatch(s)]: return "page d'établissement d'un site de réseau"
    if hote(site) in partages or (dm and dm in partages): return "domaine partagé entre plusieurs établissements"
    return ""


def motif_ligne(ligne, connues, cles, mails, deja, adresses):
    """Motif pour écarter une ligne trouvée par OpenStreetMap ou Google Places (déjà exclue ou connue, puis exclusions permanentes), chaîne vide sinon."""
    if ZN.cp_hors_zone(ligne.get("cp", "")): return "hors zone (" + ligne.get("cp", "") + ")"
    if S.cle(ligne) in cles or S.cle(ligne) in deja or (ligne["email"] and (ligne["email"].lower() in mails or ligne["email"].lower() in adresses)): return "exclu ou déjà connu"
    return motif_exclusion(ligne["nom"], ligne["email"], ligne.get("site_actuel", ""), partages_connus(connues))


# --- filtre sur les données de l'annuaire officiel (catégorie, effectif, nature juridique) : donnée manquante = rien d'écarté -------------------------------------
TRANCHES_GRANDES = {"21", "22", "31", "32", "41", "42", "51", "52", "53"}   # 50 salariés et plus (codes INSEE de tranche d'effectif)
NATURES_EXCLUES = re.compile(r"^(41|7[1-4]|8[1-5]|9[123])")   # établissements publics industriels ou commerciaux, administrations (71 à 74), organismes sociaux et professionnels (81 à 85), syndicats, associations, fondations (91 à 93)


def appel_fiche(l, ouvrir=urllib.request.urlopen):
    """Fiche de l'annuaire officiel (catégorie, tranche d'effectif, nature juridique) pour une ligne : par SIREN si connu, sinon par nom + commune (commune identique, nom contenu). {} si introuvable ou en erreur."""
    import os
    if os.environ.get("JARVIS_TEST") == "1": return {}
    q = urllib.parse.urlencode({"q": l.get("siren") or f"{l['nom']} {l['ville']}", "per_page": 5})
    try:
        with ouvrir(urllib.request.Request("https://recherche-entreprises.api.gouv.fr/search?" + q, headers={"User-Agent": UA}), timeout=15) as r: res = json.load(r).get("results", [])
    except Exception: return {}
    for x in res:
        ok = x.get("siren") == l["siren"] if l.get("siren") else norm((x.get("siege") or {}).get("libelle_commune", "")) == norm(l["ville"]) and (norm(l["nom"]) in norm(x.get("nom_complet", "")) or norm(x.get("nom_complet", "")) in norm(l["nom"]))
        if ok: return {"categorie": x.get("categorie_entreprise") or "", "tranche": x.get("tranche_effectif_salarie") or "", "nature": str(x.get("nature_juridique") or "")}
    return {}


def fiche_annuaire(l, etat, api=None):
    """Fiche en cache (prospection-etat.json › fiches_annuaire, données publiques de l'annuaire) ou interrogée une fois (0,3 s de pause)."""
    cache = etat.setdefault("fiches_annuaire", {}); k = S.cle(l)
    if k not in cache:
        f = (api or appel_fiche)(l)
        if not f: return {}   # introuvable ou erreur : rien n'est mémorisé, rien n'est écarté
        cache[k] = f; time.sleep(0.3)
    return cache[k]


def motif_annuaire(f):
    if (f.get("categorie") or "").upper() in ("ETI", "GE"): return "catégorie d'entreprise " + f["categorie"].upper() + " (annuaire officiel)"
    if (f.get("tranche") or "") in TRANCHES_GRANDES: return "effectif de 50 salariés ou plus (annuaire officiel)"
    if NATURES_EXCLUES.match(f.get("nature") or ""): return "nature juridique : association, administration ou établissement public (annuaire officiel)"
    return ""


# --- re-vérification de dernière minute, juste avant la publication d'un lot --------------------------------------------------------------------------------
def cle_phrase(p): return re.sub(r"[\d,.]+", "#", p.strip().lower())   # un chiffre mesuré peut varier (« 4,3 s »), pas le fait cité


def reverifier_lot(blocs, lignes, conf, lire=lire_page):
    """Pour chaque entreprise ayant un site : UN accès poli (robots.txt respecté, 1 s de délai de connexion et de lecture), constats recalculés sur cette seule page (aucune mesure supplémentaire : cartes, images, PageSpeed
    et certificat ne peuvent donc pas être reconfirmés). Constat non reconfirmé : retiré du message et du texte de l'e-mail ; plus aucun constat : entreprise écartée. Sans site (« pas de site trouvé ») : rien à vérifier.
    -> (blocs gardés, [(bloc, motif)] écartés). Écrit messages-a-valider.md (texte reconfirmé, daté d'aujourd'hui)."""
    par_cle = {S.cle(l): l for l in lignes}; gardes, ecartes = [], []; texte = MESSAGES.read_text(encoding="utf-8"); jour = date.today()
    for b in blocs:
        m = b["meta"] or {}; l = par_cle.get(b["id"], {}); url = l.get("site_actuel", "")
        if m.get("type") != "email" or not url or m.get("constat", "").startswith("aucun site trouvé"): gardes.append(b); continue
        chrono = {}; r = lire(url, timeout=1, chrono=chrono, robots_timeout=1)
        if not r: ecartes.append((b, "site illisible à l'instant (ou robots.txt) : aucun constat reconfirmé")); continue
        o = {"https": lambda h: "", "statut": lambda u: 0, "taille": lambda u: 0, "psi": lambda u: None, "mesure": lambda u: (chrono["octets"], chrono["sec"]) if chrono.get("sec") else None}
        neufs = constats_site(r[0], r[2], conf, None, o); cites = [x.strip() for x in m.get("constat", "").split(" ; ") if x.strip()]
        ok = [p for _, p in neufs if any(cle_phrase(p).startswith(cle_phrase(c)) or cle_phrase(c).startswith(cle_phrase(p)) for c in cites)]
        if not ok: ecartes.append((b, "aucun constat reconfirmé sur son site")); continue
        if ok != cites:
            nouveau = " ; ".join(ok[:2]); bt = re.sub(r"(En regardant votre activité : )[^\n]*", lambda mm: mm.group(1) + nouveau + f" (constaté le {jour:%d/%m}).", b["texte"], count=1)
            m2 = {**m, "constat": nouveau[:160]}; bt = re.sub(r"<!-- meta:\{.*?\} -->", lambda mm: "<!-- meta:" + meta_texte(m2) + " -->", bt, count=1)   # le constat retiré disparaît aussi des métadonnées du bloc
            texte = texte.replace(b["texte"], bt); b = {**b, "texte": bt, "meta": m2}
        gardes.append(b)
    if texte != MESSAGES.read_text(encoding="utf-8"): MESSAGES.write_text(texte, encoding="utf-8")
    return gardes, ecartes


PASSAGE = {}   # trace du dernier passage de chaque source (annuaire, OpenStreetMap) : lue par la boucle continue pour la ligne de cycle


def examinees_jour(etat, cle="stats"):
    """Entreprises déjà examinées aujourd'hui par une source (compteur propre à chaque source : stats = annuaire, stats_osm = OpenStreetMap)."""
    return sum(m.get("examinees", 0) for m in etat.get(cle, {}).get("jours", {}).get(aujourdhui(), {}).values())


def cmd_chercher(a_blanc, conf):
    etat = etat_lire(); cles, mails = exclusions(); garde = lire_trouves(); deja = {l["siren"] for l in garde}
    nouveaux, vus_n, raisons, stats = [], 0, {}, {}
    budget = max(0, conf["max_examinees"] - examinees_jour(etat))   # plafond de l'annuaire : par jour (n'arrête pas la découverte OpenStreetMap)
    if not budget: print(f"  Annuaire : plafond du jour atteint ({conf['max_examinees']} examinées), passage sauté")
    while len(nouveaux) < conf["cible_trouves"] and vus_n < budget:
        lot = candidats(etat, min(25, budget - vus_n))
        if not lot: break
        for c in lot:
            vus_n += 1
            if c["siren"] in deja: continue
            st = {}
            ligne, motif = enrichir(c, etat, conf, stat=st)
            if ligne and (S.cle(ligne) in cles or ligne["email"].lower() in mails): ligne, motif = None, "exclu (STOP ou refus)"
            elif ligne and ZN.cp_hors_zone(ligne.get("cp", "")): ligne, motif = None, "hors zone"
            elif ligne and (mx := motif_exclusion(ligne["nom"], ligne["email"], ligne.get("site_actuel", ""), partages_connus(garde + nouveaux))): ligne, motif = None, mx
            compter(stats, c["metier"], st)
            if ligne: nouveaux.append(ligne); print(f"  + {ligne['nom']} ({ligne['ville']}) : {ligne['email'] or ('formulaire ' + ligne['formulaire'] if ligne.get('formulaire') else ligne['facebook'] or ligne['linkedin'])}")
            else: etat["vus"][c["siren"]] = motif; raisons[motif] = raisons.get(motif, 0) + 1
            if len(nouveaux) >= conf["cible_trouves"]: break
    print(f"{vus_n} entreprise(s) examinée(s), {len(nouveaux)} avec contact public" + (" ; écartées : " + ", ".join(f"{v} {k}" for k, v in raisons.items()) if raisons else ""))
    print(rapport_texte(stats, "Rapport de ce passage"))
    PASSAGE["annuaire"] = {"metier": ", ".join(sorted(stats)) or "-", "commune": "-", "elements": vus_n, "emails": sum(1 for l in nouveaux if l.get("email"))}
    if a_blanc: print("  [à blanc] rien écrit (curseurs, état et prospection-trouves.csv inchangés)"); return nouveaux
    s = etat.setdefault("stats", {"cumul": {}, "jours": {}})
    fusionner(s["cumul"], stats); fusionner(s["jours"].setdefault(aujourdhui(), {}), stats)
    for j in sorted(s["jours"])[:-14]: del s["jours"][j]
    ecrire_trouves(garde + nouveaux); etat_ecrire(etat, False)
    return nouveaux


# --- blocs de messages ---------------------------------------------------------------------------------------
def meta_texte(m): return json.dumps(m, ensure_ascii=True).replace("-->", "--\\u003e")


def lire_blocs(texte):
    out = []
    for m in re.finditer(r"^## .+?(?=^## |\Z)", texte, re.M | re.S):
        b = m.group(0); i = re.search(r"<!-- id:(.+?) -->", b); st = re.search(r"\*\*Statut : (.+?)\*\*", b)
        if not i or not st: continue
        try: me = json.loads(re.search(r"<!-- meta:(\{.*?\}) -->", b).group(1))
        except Exception: me = None
        mail = re.search(r"\*\*Objet :\*\* (.*?)\n\n```\n(.*?)\n```", b, re.S)
        out.append({"id": i.group(1), "statut": st.group(1).strip(), "meta": me, "objet": mail.group(1) if mail else "", "corps": mail.group(2) if mail else "",
                    "ok": "✅" in b, "texte": b})
    return out


def ajouter_blocs(blocs, a_blanc):
    ancien = MESSAGES.read_text(encoding="utf-8") if MESSAGES.exists() else "# Messages à valider\nRien n'est envoyé sans ton OK : passe le statut d'un bloc à « validé » pour l'autoriser.\n\n"
    ids = {b["id"] for b in lire_blocs(ancien)}
    neufs = [t for i, t in blocs if i not in ids]
    if not a_blanc and neufs: MESSAGES.write_text(ancien.rstrip("\n") + "\n\n" + "\n".join(neufs) + "\n", encoding="utf-8")
    return len(neufs)


def lien_exemple(metier, lien_ok=None, cache={}):
    """Page exemple EN LIGNE (réponse 200) du métier, d'après agents\liens-metiers.json ; '' s'il n'y en a pas (le prospect n'entre pas dans le lot)."""
    cle = R.cle_metier(metier or ""); fichier = ICI / "liens-metiers.json"
    if not cle or not fichier.exists(): return ""
    url = next((u for k, u in json.loads(fichier.read_text(encoding="utf-8")).items() if k.split("-")[0] == cle), "")
    if url and url not in cache: cache[url] = (lien_ok or lien_accessible)(url)
    return url if url and cache[url] else ""


def construire_bloc(p, ident, manque, statuts, box, lien_ok=None, exemple=""):
    r, err = R.bloc(p, ident, manque, statuts, exemple)
    if err: return None, err
    id_, t = r
    formulaire = not p.get("email") and bool(p.get("formulaire"))
    reseau = not p.get("email") and not formulaire
    if formulaire:
        t = t.replace("  - ⚠ pas d'e-mail : LinkedIn ou téléphone seulement", "  - ℹ pas d'e-mail publié : message à COLLER À LA MAIN par Liam dans le formulaire de contact de son site (jamais envoyé par l'agent)")
        t = t.replace("### E-mail", "### Message pour le formulaire de contact (à coller à la main)").replace("### LinkedIn", "### Version courte (si le formulaire limite la longueur)")
        if "⚠" not in t.split("### Message pour le formulaire")[0]: t = t.replace("⛔ à corriger avant envoi", "✅ prêt à relire")
    if reseau:
        t = t.replace("  - ⚠ pas d'e-mail : LinkedIn ou téléphone seulement", "  - ℹ pas d'e-mail : message réseau à envoyer À LA MAIN par Liam (jamais par l'agent)")
        t = t.replace("### E-mail", "### E-mail (non utilisé : pas d'adresse publiée)").replace("### LinkedIn", "### Message Facebook / LinkedIn (à envoyer à la main)")
        if "⚠" not in t.split("### E-mail")[0]: t = t.replace("⛔ à corriger avant envoi", "✅ prêt à relire")
    typ = "formulaire" if formulaire else "reseau" if reseau else "email"
    meta = {"type": typ, "formulaire": p.get("formulaire", ""), "box": "" if (reseau or formulaire) else box, "email": p.get("email", ""), "origine_adresse": FA.origine(p)[0] if typ == "email" else "", "nom": p["nom"], "ville": p["ville"], "metier": p.get("metier", ""), "lot": aujourdhui(),
            "lien": (re.search(r"- Maquette : (\S+)", t) or [0, ""])[1], "facebook": p.get("facebook", ""), "linkedin": p.get("linkedin", ""),
            "constat": "aucun site trouvé à son nom" if p.get("modele") == "sans-site" else re.sub(r"\s*\(constaté le [^)]*\)\s*$", "", p.get("notebesoin") or p.get("note_besoin", ""))[:160]}   # constat(s) cité(s) dans le message, repris dans la ligne Discord
    t = t.replace(f"<!-- id:{id_} -->\n", f"<!-- id:{id_} -->\n<!-- meta:{meta_texte(meta)} -->\n", 1)
    lignes = [f"- Boîte d'envoi : {box}" if not (reseau or formulaire) else ("- Canal : formulaire de contact " + p["formulaire"] if formulaire else "- Canal : " + (p.get("facebook") or p.get("linkedin")))]
    if typ == "email": lignes.append("- Origine de l'adresse : " + FA.etiquette_origine(p))   # d'où vient l'adresse (site, OpenStreetMap, saisie) et ce qui est à vérifier
    t = t.replace("- Maquette :", "\n".join(lignes) + "\n- Maquette :", 1)
    return (id_, t), None


def en_attente(texte, box):
    return sum(1 for b in lire_blocs(texte) if b["statut"] == "à valider" and b["meta"] and b["meta"].get("box") == box)


def ecarter_adresse(l, motif, etat, ecartes):
    """Adresse refusée par le filtre : le prospect sort des lots (statut « exclu », comme pour l'annuaire) et le motif est gardé dans l'état (prospection-etat.json › adresses_ecartees)."""
    l["statut"] = "exclu"; ecartes.append(l)
    etat.setdefault("adresses_ecartees", {})[S.cle(l)] = {"date": aujourdhui(), "motif": motif}
    print(f"  écarté : {l['nom']} ({l['ville']}) : adresse refusée : {motif}")


def cmd_preparer(a_blanc, conf, generer=True, api_fiche=None):
    etat = etat_lire(); cles, mails = exclusions(); ident, manque = R.charger_identite(); statuts = R.statuts_suivi()
    lignes = lire_trouves(); texte = MESSAGES.read_text(encoding="utf-8") if MESSAGES.exists() else ""
    jour = etat["lots"].setdefault(aujourdhui(), {}); quota = {b: max(0, conf["par_boite_par_jour"] - jour.get(b, 0)) for b in boites()}
    if not quota: print("  mode API : aucune boîte autorisée (python agents\\test-gmail-api.py <adresse>) : aucun e-mail préparé, seuls les messages réseau le sont.")
    for b in quota:
        if en_attente(texte, b) >= conf["par_boite_par_jour"]: quota[b] = 0; print(f"  {b} : déjà {conf['par_boite_par_jour']} blocs en attente de ta validation, rien de nouveau")
    choisis, reseaux, formulaires, adresses = [], 0, 0, set()
    partages = partages_connus(lignes)
    dispo = [l for l in lignes if l["statut"] == "trouvé" and not ZN.cp_hors_zone(l.get("cp", "")) and S.cle(l) not in cles and l["email"].lower() not in mails and not motif_exclusion(l["nom"], l["email"], l.get("site_actuel", ""), partages)]
    sans = [l for l in dispo if not lien_exemple(l.get("metier", ""))]
    print("  Prospects par canal : e-mail " + str(sum(1 for l in dispo if l["email"])) + ", formulaire " + str(sum(1 for l in dispo if not l["email"] and l.get("formulaire"))) + ", Facebook " + str(sum(1 for l in dispo if l.get("facebook"))) + ", LinkedIn " + str(sum(1 for l in dispo if l.get("linkedin")))
          + f" ; {len(sans)} sans page exemple en ligne pour leur métier (écartés du lot)")
    ecartes = []

    def ecarte_annuaire(l):   # filtre sur l'annuaire officiel (ETI / GE, plus de 50 salariés, association, administration, établissement public) ; donnée manquante : rien d'écarté
        mo = motif_annuaire(fiche_annuaire(l, etat, api_fiche))
        if mo: l["statut"] = "exclu"; ecartes.append(l); print(f"  écarté : {l['nom']} ({l['ville']}) : {mo}")
        return bool(mo)

    for l in dispo:
        if l in sans: continue
        if l["email"]:
            if l["email"].lower() in adresses: continue  # même prospect deux fois dans le lot : une seule boîte
            if conf.get("filtre_adresses", True):   # filtre gratuit avant la mise en lot (filtre_adresses.py) : syntaxe, faute de frappe, déjà rebondie, source visible, MX
                mo, _ = FA.controle_adresse(l, mails, domaine_recoit_courrier)
                if mo: ecarter_adresse(l, mo, etat, ecartes); continue
            box = max(quota, key=lambda b: quota[b], default=None)
            if not box or quota[box] <= 0 or ecarte_annuaire(l): continue
            quota[box] -= 1; choisis.append((l, box)); adresses.add(l["email"].lower())
        elif l.get("formulaire"):
            if formulaires < conf["formulaires_par_jour"] and not ecarte_annuaire(l): formulaires += 1; choisis.append((l, ""))  # compté à part : message à coller à la main dans le formulaire du site
        elif reseaux < conf["reseaux_par_jour"] and not ecarte_annuaire(l): reseaux += 1; choisis.append((l, ""))
    if ecartes and not a_blanc: ecrire_trouves(lignes); etat_ecrire(etat, False)   # statut « exclu » et fiches d'annuaire en cache
    if not choisis:
        print("LOT VIDE : aucun e-mail utilisable aujourd'hui" if not any(l["email"] for l in dispo if l not in sans) else "Aucun prospect à préparer."); return 0
    lot_csv = LOTS / f"lot-{aujourdhui()}.csv"
    if not a_blanc:
        LOTS.mkdir(exist_ok=True); ecrire_trouves([l for l, _ in choisis], lot_csv)
        if generer: lancer_generer(lot_csv)  # maquettes LOCALES, rien n'est déployé
    blocs, apercu = [], []
    par_cle = {S.cle(p): p for p in G.lire_csv(lot_csv)} if lot_csv.exists() else {}
    for l, box in choisis:
        p = par_cle.get(S.cle(l)) or {re.sub(r"[^a-z]", "", k): v for k, v in l.items()}
        i2 = {**ident, "email_reponse": box or ident["email_reponse"]}  # les réponses arrivent dans la boîte qui écrit (lue par reponses.py)
        r, err = construire_bloc(p, i2, [m for m in manque if m != "email_reponse"], statuts, box, exemple=lien_exemple(p.get("metier", "")))
        if err: print(f"  sauté : {l['nom']} ({err})"); continue
        blocs.append(r)
        if box: jour[box] = jour.get(box, 0) + 1; apercu.append((box, p["nom"], re.search(r"\*\*Objet :\*\* (.*?)\n", r[1]).group(1), re.search(r"```\n(.*?)\n```", r[1], re.S).group(1)))
    n = ajouter_blocs(blocs, a_blanc)
    print(f"{n} bloc(s) {'prévus' if a_blanc else 'ajoutés à messages-a-valider.md'} ({len(apercu)} e-mails, {n_type(blocs, 'formulaire')} messages pour formulaire, {n_type(blocs, 'reseau')} messages réseau)" + (" [à blanc : rien écrit]" if a_blanc else " : statut « à valider »"))
    if a_blanc: return n
    if apercu: APERCU.write_text(apercu_html(apercu), encoding="utf-8"); print(f"Aperçu : {APERCU}")
    fait = {S.cle(l) for l, _ in choisis}
    for l in lignes:
        if S.cle(l) in fait: l["statut"] = "préparé"
    ecrire_trouves(lignes)
    if lot_csv.exists(): S.init(str(lot_csv))
    etat_ecrire(etat, False)
    return n


def apercu_html(items):
    """Boîte de réception façon téléphone + premier message ouvert (aperçu avant tout envoi)."""
    e = html.escape
    def extrait(c): return (c.partition(chr(10) * 2)[2] or c)[:90]
    liste = "".join(f"<li><b>{e(nom)}</b><span>{e(obj)}</span><small>{e(extrait(c))}…</small></li>" for _, nom, obj, c in items[:10])
    box, nom, obj, corps = items[0]
    return f"""<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Aperçu du lot</title>
<style>body{{font:15px system-ui;background:#eef0f2;margin:0;padding:24px;display:flex;gap:24px;flex-wrap:wrap;justify-content:center}}
.tel{{width:340px;background:#fff;border-radius:28px;padding:18px;box-shadow:0 8px 30px #0003}}h2{{margin:0 0 10px;font-size:17px}}
li{{list-style:none;border-bottom:1px solid #e5e7ea;padding:9px 0}}li span,li small{{display:block;color:#555}}li small{{color:#888}}ul{{margin:0;padding:0}}
pre{{white-space:pre-wrap;font:14px system-ui;margin:0}}</style>
<div class="tel"><h2>Boîte de réception ({len(items)} e-mails du lot)</h2><ul>{liste}</ul></div>
<div class="tel"><h2>{e(obj)}</h2><p style="color:#666">De : {e(box)}</p><pre>{e(corps)}</pre></div>"""


# --- relance J+2 (une seule) --------------------------------------------------------------------------------
def cmd_relances(a_blanc, conf):
    etat = etat_lire(); ident, manque = R.charger_identite(); jour = etat["lots"].setdefault(aujourdhui(), {}); blocs = []; _, exclus_mails = exclusions()
    for r in S.lire():
        id_ = S.cle(r)
        e = etat["envois"].get(id_)
        if r["statut"] != "envoyé" or not r["relance_j2"] or r["relance_j2"] > aujourdhui() or id_ in etat["relances"] or not e: continue
        if e["email"].lower() in exclus_mails: continue   # adresse rebondie, STOP ou refus : pas de relance (3 des 18 rebonds du 03/11/2026 étaient des relances vers une adresse déjà rebondie)
        box = e["box"]
        if jour.get(box, 0) >= conf["par_boite_par_jour"]: continue
        corps = R.avec_signature(f"""Bonjour,

Je reviens vers vous une seule fois, suite à mon message du {datetime.fromisoformat(e['date']):%d/%m/%Y} au sujet d'une maquette de site pour {e['nom']} : {e['lien']}
Si ce n'est pas utile pour vous, il n'y a rien à faire : je ne vous écrirai pas à nouveau.

Cordialement,""", {**ident, "email_reponse": box})
        meta = {"type": "relance", "box": box, "email": e["email"], "nom": e["nom"], "ville": e["ville"], "lot": aujourdhui(), "lien": e["lien"], "origine": id_}
        blocs.append((id_ + "|relance", f"## {e['nom']} — relance J+2 — {e['ville']}\n<!-- id:{id_}|relance -->\n<!-- meta:{meta_texte(meta)} -->\n**Statut : à valider**\n\n"
                      f"- Boîte d'envoi : {box}\n- Contact : {e['email']}\n- Contrôles : ✅ prêt à relire\n\n### E-mail\n**Objet :** {e['objet']}\n\n```\n{corps}\n```\n"))
        jour[box] = jour.get(box, 0) + 1
    n = ajouter_blocs(blocs, a_blanc)
    print(f"{len(blocs)} relance(s) due(s), {n} bloc(s) {'prévus (à blanc)' if a_blanc else 'ajoutés « à valider »'}. Une seule relance par prospect.")
    if not a_blanc: etat_ecrire(etat, False)
    return n


# --- envoi des blocs validés ---------------------------------------------------------------------------------
def lien_accessible(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=10) as r: return r.status == 200
    except Exception: return False


# --- vérification gratuite du domaine avant l'envoi : le domaine doit pouvoir recevoir du courrier (MX, ou à défaut une adresse A/AAAA) ----------
MOTIF_MX = "le domaine ne reçoit pas de courrier (aucun enregistrement MX)"
RESOLVEUR_MX = None   # tests : fonction domaine -> (rcode, [(préférence, serveur)]) ; None = vraie requête DNS (sauf JARVIS_TEST=1, où le contrôle est sauté)
_mx_cache = {}


def _nom_dns(rep, i):
    """Saute un nom DNS (avec compression) à partir de l'octet i ; renvoie l'indice suivant."""
    while True:
        n = rep[i]
        if n == 0: return i + 1
        if n & 0xC0 == 0xC0: return i + 2
        i += n + 1


def analyser_mx(rep):
    """Réponse DNS brute -> (rcode, [(préférence, serveur)]) ; serveur '' = MX nul (« . »)."""
    if len(rep) < 12: raise ValueError("réponse DNS trop courte")
    rcode, qd, an = rep[3] & 0x0F, int.from_bytes(rep[4:6], "big"), int.from_bytes(rep[6:8], "big"); i = 12
    for _ in range(qd): i = _nom_dns(rep, i) + 4
    mx = []
    for _ in range(an):
        i = _nom_dns(rep, i); typ, rdl = int.from_bytes(rep[i:i + 2], "big"), int.from_bytes(rep[i + 8:i + 10], "big"); i += 10
        if typ == 15: mx.append((int.from_bytes(rep[i:i + 2], "big"), "" if rep[i + 2] == 0 else "x"))
        i += rdl
    return rcode, mx


def requete_mx(domaine, serveurs=("1.1.1.1", "8.8.8.8")):
    """Une requête MX en UDP (socket, rien d'installé). Lève OSError si aucun résolveur ne répond."""
    import socket
    q = bytes.fromhex("123401000001000000000000") + b"".join(bytes([len(x)]) + x.encode("idna") for x in domaine.split(".")) + bytes.fromhex("00000f0001")
    for srv in serveurs:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as so:
                so.settimeout(4); so.sendto(q, (srv, 53)); return analyser_mx(so.recv(4096))
        except (OSError, ValueError): continue
    raise OSError("aucun résolveur DNS joignable")


def domaine_recoit_courrier(domaine, resolveur=None):
    """Faux seulement si on est SÛR que le domaine ne reçoit rien : NXDOMAIN, MX nul, ou ni MX ni adresse A/AAAA. Doute (DNS injoignable, erreur) = vrai : on n'exclut jamais sur un doute."""
    import os, socket
    domaine = domaine.strip().lower().rstrip(".")
    resolveur = resolveur or RESOLVEUR_MX
    if resolveur is None and os.environ.get("JARVIS_TEST") == "1": return True
    if domaine in _mx_cache and resolveur is None: return _mx_cache[domaine]
    try: rcode, mx = (resolveur or requete_mx)(domaine)
    except Exception: return True
    if rcode == 3: ok = False
    elif rcode != 0: ok = True
    elif mx: ok = any(h for _, h in mx)
    else:
        try: socket.getaddrinfo(domaine, 25); ok = True
        except socket.gaierror: ok = False
        except OSError: ok = True
    if resolveur is None: _mx_cache[domaine] = ok
    return ok


def exclure_domaine_mort(m, reel=True):
    """Passe le prospect en « exclu » (suivi-prospects.csv, note d'historique) ; ses messages ne partiront plus."""
    try: S.statut(m["nom"], "exclu", m.get("ville", ""), None, f"{MOTIF_MX} : {m['email'].split('@')[1]} (vérifié le {aujourdhui()})")
    except SystemExit as ex: print(f"  statut non changé : {ex}")


def refus(b, etat, conf, cles, mails, lien_ok):
    """Motif de refus d'un bloc validé, ou '' s'il peut partir."""
    m = b["meta"]; jour = etat["envoyes"].get(aujourdhui(), {})
    if not m or m.get("type") not in ("email", "relance"): return "bloc sans données d'envoi (non préparé par l'agent) ou message réseau"
    if not b["ok"]: return "contrôles ⛔ : corriger le bloc"
    if b["id"] not in etat["approuves"]: return "lot non approuvé sur Discord (« ok lot » ou ✅ de Liam seulement)"
    if m["box"] not in boites(): return "boîte d'envoi inconnue" + (" (mode API : seuls les comptes autorisés peuvent envoyer)" if P.cfg()["api"]["actif"] else "")
    lot_box = next((v.get("box") for v in etat["lots_discord"].values() if b["id"] in v["ids"]), None)
    if lot_box and lot_box != m["box"]: return f"le lot approuvé est celui de {lot_box} : ce message ne part pas depuis {m['box']}"
    if not re.fullmatch(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", m.get("email", "")): return "adresse du destinataire invalide"
    if conf.get("verifier_mx", True) and not domaine_recoit_courrier(m["email"].split("@")[1]): return MOTIF_MX
    if b["id"] in etat["envois"] and m["type"] == "email": return "déjà envoyé"
    if m["type"] == "email" and any(e["email"].lower() == m["email"].lower() for e in etat["envois"].values()): return "prospect déjà contacté (une seule boîte par prospect)"
    if m["type"] == "relance" and etat["envois"].get(m["origine"], {}).get("box", m["box"]) != m["box"]: return "relance depuis une autre boîte que le premier message"
    if m["type"] == "relance" and (m["origine"] in etat["relances"]): return "relance déjà faite (une seule)"
    if S.cle(m) in cles or m["email"].lower() in mails: return "prospect exclu (STOP ou refus)"
    if jour.get(m["box"], 0) >= conf["par_boite_par_jour"]: return f"plafond de {conf['par_boite_par_jour']} atteint pour {m['box']} aujourd'hui"
    if R.LIGNE_STOP not in b["corps"]: return "ligne STOP absente"
    if R.A_COMPLETER in b["corps"] or "[LIEN" in b["corps"]: return "texte « à compléter » restant"
    if R.INTERDITS.search(b["corps"]) or R.INTERDITS.search(b["objet"]): return "mot interdit (promesse, chiffre, urgence)"
    if not lien_ok(m.get("lien", "")): return "lien de la maquette inaccessible (déployer d'abord, avec ton accord)"
    return ""


def marquer(texte, id_, nouveau):
    return re.sub(rf"(<!-- id:{re.escape(id_)} -->\n(?:<!-- meta:.*? -->\n)?\*\*Statut : )[^*]+(\*\*)", lambda m: m.group(1) + nouveau + m.group(2), texte, count=1)


def smtp_gmail(box, mdp, msg):
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as s:
        s.login(box, mdp); s.send_message(msg)


_client = {}  # clients API ouverts par boîte, et "hors" : boîtes sautées pendant cette exécution (jeton refusé, droits, quota)


def envoi_api(box, _mdp, msg, ouvrir=GA.client):
    """Envoi par l'API Gmail depuis la boîte `box`, qui doit être le compte autorisé de son jeton. Le Message-ID réel est relu (Gmail peut le remplacer) pour que la relance reste dans le fil."""
    if box not in _client: _client[box] = ouvrir(box)
    cl = _client[box]
    if cl.adresse.lower() != box.lower(): raise GA.ErreurApi(403, "le compte autorisé n'est pas l'expéditeur prévu")
    gid = cl.envoyer(msg)
    try:
        vrai = cl.entetes(gid).get("message-id")
        if vrai: msg.replace_header("Message-ID", vrai)
    except Exception: pass


def par_api(box):
    """Cette boîte envoie par l'API Gmail : mode API global, ou jeton OAuth enregistré pour elle (sinon repli SMTP + mot de passe d'application)."""
    return P.cfg()["api"]["actif"] or GA.jeton_existe(box)


def envoi_auto(box, mdp, msg):
    (envoi_api if par_api(box) else smtp_gmail)(box, mdp, msg)


def bilan_envoi(etat):
    """(envoyés aujourd'hui, réponses, STOP) : envois du jour relus dans l'état ; réponses et STOP d'après le statut des prospects déjà contactés (suivi-prospects.csv)."""
    cles = set(etat["envois"]); st = {S.cle(r): r["statut"] for r in S.lire() if S.cle(r) in cles}
    return sum(etat["envoyes"].get(aujourdhui(), {}).values()), sum(1 for s in st.values() if s in ("répondu", "refusé", "STOP", "devis", "signé")), sum(1 for s in st.values() if s == "STOP")


def annonce_envoi(etat, api=None):
    """Après un envoi : « Envoyé : N. Réponses : n. STOP : n. » dans #business (aucun e-mail n'est envoyé par ce message)."""
    acces = acces_discord()
    if not acces: return False
    jeton, salon, uid = acces; n, rep, stop = bilan_envoi(etat)
    r = (api or discord)(jeton, "POST", f"/channels/{salon}/messages", {"content": f"Envoyé : {n}. Réponses : {rep}. STOP : {stop}."})
    return bool(r and "id" in r)


def gel_gmail(etat, conf, boite, motif, reel):
    """Gmail refuse un envoi (quota, blocage) : la montée se fige au palier du jour, message dans #business (seulement pour un vrai envoi), état écrit."""
    if geler(etat, conf, conf.get("palier") or etat.get("montee", {}).get("palier", 0), f"Gmail ({motif})", f"Gmail a refusé un envoi depuis {boite} ({motif})", None, not reel):
        etat_ecrire(etat, False); print("  montée en charge figée (refus de Gmail)")


def cmd_envoyer(a_blanc, conf, envoi=None, dormir=time.sleep, lien_ok=lien_accessible):
    if not MESSAGES.exists(): print("Pas de messages-a-valider.md."); return 0
    etat = etat_lire(); cles, mails = exclusions(); ident, _ = R.charger_identite(); faits = 0; reel = envoi is None   # message Discord d'après-envoi : seulement pour un vrai envoi
    envoi = envoi or envoi_auto; hors = _client.setdefault("hors", set())
    env = P.lire_env(RACINE / ".env")  # lu seulement pour une boîte sans jeton API (repli SMTP)
    a_envoyer = [b for b in lire_blocs(MESSAGES.read_text(encoding="utf-8")) if b["statut"].lower() == "validé"]
    if not a_envoyer: print("Aucun bloc au statut « validé » : rien à envoyer."); return 0
    vars_ = {x["adresse"]: x["var"] for x in P.cfg()["comptes"]}
    for b in a_envoyer:
        motif = refus(b, etat, conf, cles, mails, lien_ok); m = b["meta"] or {}
        if motif: print(f"  non envoyé : {m.get('nom', b['id'])} : {motif}")
        if motif == MOTIF_MX and reel and not a_blanc: exclure_domaine_mort(m)
        if motif: continue
        if m["box"] in hors: continue  # boîte sautée plus haut (message déjà affiché) : l'autre boîte continue
        if a_blanc: print(f"  [à blanc] enverrait à {m['email']} depuis {m['box']} : « {b['objet']} »"); faits += 1; continue
        api = reel and par_api(m["box"])   # injecté (tests) : l'envoi fourni décide
        mdp = None if api else env.get(vars_.get(m["box"], ""), "").replace(" ", "")
        if not api and not mdp and reel: print(f"  {m['box']} : ni jeton Gmail API ni mot de passe d'application, boîte sautée"); continue
        msg = EmailMessage(); msg["From"] = f"{ident['prenom_nom']} <{m['box']}>"; msg["To"] = m["email"]; msg["Subject"] = b["objet"]
        msg["Date"] = formatdate(localtime=True); msg["Message-ID"] = make_msgid(domain=m["box"].split("@")[1]); msg["List-Unsubscribe"] = f"<mailto:{m['box']}?subject=STOP>"
        if m["type"] == "relance": msg["In-Reply-To"] = msg["References"] = etat["envois"][m["origine"]]["message_id"]
        msg.set_content(b["corps"])
        try: envoi(m["box"], mdp, msg)
        except GA.BibliothequeManquante as ex: print("  " + str(ex)); break  # aucune boîte ne peut envoyer
        except GA.JetonExpire as ex: print("  " + str(ex)); hors.add(m["box"]); continue  # CETTE boîte est sautée, l'autre continue
        except GA.ErreurApi as ex:
            print(f"  échec pour {m['nom']} ({m['box']}) : Gmail API ({ex})")
            if ex.code in (403, 429):   # refus général de cette boîte (droits, quota) : inutile d'insister, et la montée se fige
                hors.add(m["box"]); gel_gmail(etat, conf, m["box"], f"Gmail API {ex.code}", reel)
            continue
        except smtplib.SMTPAuthenticationError: print(f"  {m['box']} : connexion refusée (mot de passe d'application ?), boîte sautée"); gel_gmail(etat, conf, m["box"], "connexion refusée", reel); continue
        except (smtplib.SMTPSenderRefused, smtplib.SMTPDataError) as ex: print(f"  échec pour {m['nom']} : {type(ex).__name__}"); hors.add(m["box"]); gel_gmail(etat, conf, m["box"], f"SMTP {getattr(ex, 'smtp_code', '')}", reel); continue
        except (smtplib.SMTPException, OSError) as ex: print(f"  échec pour {m['nom']} : {type(ex).__name__}"); continue
        etat["envoyes"].setdefault(aujourdhui(), {}); etat["envoyes"][aujourdhui()][m["box"]] = etat["envoyes"][aujourdhui()].get(m["box"], 0) + 1
        if m["type"] == "email":
            etat["envois"][b["id"]] = {"nom": m["nom"], "ville": m["ville"], "email": m["email"], "box": m["box"], "date": aujourdhui(), "message_id": msg["Message-ID"], "objet": b["objet"], "lien": m["lien"]}
            try: S.statut(m["nom"], "envoyé", m["ville"], None, f"lot du {m['lot']} (agent Prospection)")
            except SystemExit as ex: print(f"  suivi non mis à jour : {ex}")
        else: etat["relances"].append(m["origine"])
        MESSAGES.write_text(marquer(MESSAGES.read_text(encoding="utf-8"), b["id"], f"envoyé le {aujourdhui()}"), encoding="utf-8")
        etat_ecrire(etat, False); faits += 1; print(f"  envoyé : {m['nom']} ({m['box']})")
        if b is not a_envoyer[-1]: dormir(random.uniform(*conf["pause_envoi_s"]))
    print(f"{faits} e-mail(s) {'prévus (à blanc)' if a_blanc else 'envoyé(s)'}.")
    if faits and not a_blanc and reel: annonce_envoi(etat)
    return faits


# --- Discord : publication du lot et approbation par Liam seul ----------------------------------------------
def discord(jeton, methode, chemin, corps=None):
    """Appel REST Discord (bot Jarvis, aucun lancement de Jarvis). Renvoie le JSON (ou {}), None en cas d'échec. Le jeton n'est jamais affiché."""
    rq = urllib.request.Request("https://discord.com/api/v10" + chemin, method=methode, data=None if corps is None else json.dumps(corps).encode(),
                                headers={"Authorization": "Bot " + jeton, "Content-Type": "application/json", "User-Agent": "DiscordBot (prospection-b2b, 1.0)"})
    try:
        with urllib.request.urlopen(rq, timeout=20) as r:
            brut = r.read(); return json.loads(brut) if brut else {}
    except urllib.error.HTTPError as ex: print(f"  Discord a refusé la demande (HTTP {ex.code})"); return None
    except Exception as ex: print(f"  Discord injoignable ({type(ex).__name__})"); return None


def acces_discord(cle=None, nom=None, api=None):
    """(jeton, salon, uid) ou None si un réglage manque (dit lequel). Secrets lus dans Jarvis\\.env, jamais affichés.
    Avec cle + nom : le salon de ce nom (cache reponses-config.json › cle), l'ancien salon (salon_paiement_id) s'il est introuvable."""
    c = P.cfg(); env = P.lire_env(RACINE.parent / ".env")
    uid, jeton = c["utilisateur_id"] or env.get("DISCORD_USER_ID", ""), env.get("DISCORD_BOT_TOKEN", "")
    manque = [n for n, v in (("salon_paiement_id (reponses-config.json)", c["salon_paiement_id"]), ("DISCORD_USER_ID (Jarvis\\.env)", uid), ("DISCORD_BOT_TOKEN (Jarvis\\.env)", jeton)) if not v]
    if manque: print("  Discord : à COMPLÉTER : " + ", ".join(manque)); return None
    salon = c["salon_paiement_id"]
    if cle: salon = P.salon_par_nom(jeton, cle, nom, salon, (lambda ch: api(jeton, "GET", ch)) if api else None)
    return jeton, salon, str(uid)


def heure_paris(maintenant=None):
    """Date et heure à Paris (heure d'été comprise), sans dépendre de la base de fuseaux horaires de Windows. Résultat sans fuseau."""
    n = maintenant or datetime.now(timezone.utc)
    try:
        from zoneinfo import ZoneInfo
        return n.astimezone(ZoneInfo("Europe/Paris")).replace(tzinfo=None)
    except Exception: pass
    u = n.astimezone(timezone.utc).replace(tzinfo=None)
    def dernier_dimanche(m): d = datetime(u.year, m, 31, 1); return d - timedelta(days=(d.weekday() + 1) % 7)
    return u + timedelta(hours=2 if dernier_dimanche(3) <= u < dernier_dimanche(10) else 1)


def texte_lot(uid, blocs, box, quota, palier=None, incomplet=False, auto=False):
    """Message Discord d'UN lot (une boîte, un jour) : « Lot de <boîte> du <date> : N e-mails (quota Q). Palier du jour : P par boîte. Aperçu : apercu-lot.html. Réponds `ok lot` pour envoyer. »
    puis une ligne par entreprise : nom, métier, ville, constat cité, lien de la maquette."""
    n = len(blocs)
    fin = "Envoi automatique ACTIVÉ (envoi_automatique = true) : ce lot part sans `ok lot`, avec toutes les protections." if auto else "Réponds `ok lot` pour envoyer."
    l = [f"<@{uid}> Lot de {box} du {aujourdhui()} : {n} e-mails (quota {quota})." + (f" Lot incomplet : {n} sur {quota}." if incomplet else "") + f" Palier du jour : {palier or quota} par boîte. Aperçu : apercu-lot.html. {fin}"]
    for b in blocs:
        m = b["meta"]
        c = "relance J+2" if m["type"] == "relance" else (P.assainir(m.get("constat", "")) or "—")
        ligne = f"• {P.assainir(m['nom'])}, {P.assainir(m.get('metier') or '—')}, {P.assainir(m['ville'])} : {c}" + (f" : <{m['lien']}>" if m.get("lien", "").startswith("http") else "")
        if len(chr(10).join(l + [ligne])) > 1800: l.append("… et d'autres (voir messages-a-valider.md)"); break
        l.append(ligne)
    return chr(10).join(l)[:1900]


def reste_complement(etat, box):
    """Places libérées dans le lot du jour d'une boîte (entreprises retirées, champ « retires ») et pas encore reprises par un lot complémentaire."""
    auj = [v for v in etat["lots_discord"].values() if v.get("date") == aujourdhui() and v.get("box") == box]
    return sum(v.get("retires", 0) for v in auj if not v.get("complement")) - sum(len(v["ids"]) for v in auj if v.get("complement"))


def lots_a_poster(etat, blocs, conf, paris=None):
    """[(boîte, blocs, incomplet)] : UN lot par boîte et par jour, jamais reposté. Un lot part quand la boîte a atteint son quota du jour (palier) ; après l'heure limite (heure_limite, heure de Paris),
    le lot incomplet part UNE fois. Tant que le quota n'est pas atteint avant l'heure limite : rien (l'agent continue de chercher)."""
    paris = paris or heure_paris(); q = conf["par_boite_par_jour"]; limite = paris.strftime("%H:%M") >= conf["heure_limite"]; sortie = []
    for box in boites():
        qb = q
        if etat["lots_box"].get(aujourdhui(), {}).get(box):   # lot déjà posté : seul un lot complémentaire (places libérées par des exclusions) peut suivre, avec son propre « ok lot »
            qb = reste_complement(etat, box)
            if qb <= 0: continue
        neufs = [b for b in blocs if b["statut"] == "à valider" and b["meta"] and b["meta"].get("type") in ("email", "relance") and b["meta"].get("box") == box and b["id"] not in etat["publies"]][:qb]
        if not neufs: continue
        if len(neufs) < qb and (not limite or conf.get("lot_attendre_les_deux_boites")): print(f"  {box} : {len(neufs)} sur {qb}, lot non posté (quota du jour pas atteint" + ("" if conf.get("lot_attendre_les_deux_boites") else f", heure limite {conf['heure_limite']}") + ")"); continue
        sortie.append((box, neufs, len(neufs) < qb))
    if conf.get("lot_attendre_les_deux_boites") and len(sortie) < len([b for b in boites() if not etat["lots_box"].get(aujourdhui(), {}).get(b)]):
        if sortie: print("  lot non posté : les deux boîtes doivent avoir leur quota de prospects en zone (lot_attendre_les_deux_boites)")
        return []
    return sortie


def cmd_publier(a_blanc, conf, api=discord, paris=None, lire_verif=None):
    etat = etat_lire(); texte = MESSAGES.read_text(encoding="utf-8") if MESSAGES.exists() else ""
    lots = lots_a_poster(etat, lire_blocs(texte), conf, paris)
    if not lots: print("Lot à publier : rien (quota du jour pas atteint, ou lot déjà posté)."); return 0
    acces = None if a_blanc else acces_discord("salon_lots_id", "lots", api); q = conf["par_boite_par_jour"]; n = 0
    for box, neufs, incomplet in lots:
        compl = bool(etat["lots_box"].get(aujourdhui(), {}).get(box))   # lot complémentaire : son propre message, son propre « ok lot »
        if not a_blanc and (lire_verif or __import__("os").environ.get("JARVIS_TEST") != "1"):   # re-vérification de dernière minute (jamais en test sans lecture simulée)
            gardes, ecartes = reverifier_lot(neufs, lire_trouves(), conf, lire_verif or lire_page)
            if ecartes:
                texte2, lignes2 = MESSAGES.read_text(encoding="utf-8"), lire_trouves()
                for b, mo in ecartes:
                    print(f"  retiré du lot de {box} : {b['meta']['nom']} ({b['meta']['ville']}) : {mo}"); texte2 = marquer(texte2, b["id"], f"écarté à la re-vérification du {aujourdhui()}")
                    for l in lignes2:
                        if S.cle(l) == b["id"]: l["statut"] = "écarté"
                MESSAGES.write_text(texte2, encoding="utf-8"); ecrire_trouves(lignes2)
                incomplet = True; neufs = [x for x in lire_blocs(texte2) if x["id"] in {g["id"] for g in gardes}]
            elif gardes != neufs: neufs = [x for x in lire_blocs(MESSAGES.read_text(encoding="utf-8")) if x["id"] in {g["id"] for g in gardes}]
            if not neufs: continue
        msg = texte_lot((acces or ("", "", "0"))[2], neufs, box, reste_complement(etat, box) if compl else q, conf.get("palier"), incomplet, conf["envoi_automatique"])
        if compl: msg = msg.replace("Lot de", "Lot complémentaire de", 1)
        if a_blanc: print("  [à blanc] message Discord qui serait publié (rien posté) :\n  " + msg.replace("\n", "\n  ")); n += len(neufs); continue
        if not acces: return n
        jeton, salon, uid = acces
        r = api(jeton, "POST", f"/channels/{salon}/messages", {"content": msg, "allowed_mentions": {"users": [uid]}})
        ancien = P.cfg()["salon_paiement_id"]
        if (not r or "id" not in r) and salon != ancien:   # salon « lots » refusé en écriture : repli sur l'ancien salon
            print("  salon « lots » refusé : lot posté dans l'ancien salon"); salon = ancien; r = api(jeton, "POST", f"/channels/{salon}/messages", {"content": msg, "allowed_mentions": {"users": [uid]}})
        if not r or "id" not in r: print(f"Lot de {box} non publié sur Discord."); continue
        api(jeton, "PUT", f"/channels/{salon}/messages/{r['id']}/reactions/%E2%9C%85/@me")  # ✅ prêt à cliquer
        etat["lots_discord"][r["id"]] = {"ids": [b["id"] for b in neufs], "date": aujourdhui(), "box": box, "salon": salon, "incomplet": incomplet, **({"complement": True} if compl else {})}; etat["publies"] += [b["id"] for b in neufs]
        etat["lots_box"].setdefault(aujourdhui(), {})[box] = r["id"]; etat_ecrire(etat, False)   # écrit tout de suite : ce lot ne sera jamais reposté, même après un redémarrage
        print(f"LOT POSTÉ {datetime.now():%H:%M} : lot de {box} publié sur Discord ({len(neufs)} bloc(s)" + (f", lot incomplet : {len(neufs)} sur {q}" if incomplet else "") + ") : en attente de son « ok lot » ou ✅."); n += len(neufs)
    return n


OK_LOT = re.compile(r"\s*ok\s+lot\s*[.!]*\s*", re.I)


def cible_ok(x, lots):
    """Lot visé par un message « ok lot » : celui auquel il répond (réponse Discord), sinon le dernier lot posté avant lui. Deux lots postés = deux « ok lot » distincts."""
    ref = str((x.get("message_reference") or {}).get("message_id", ""))
    if ref in lots: return ref
    avant = [m for m in lots if int(m) < int(x["id"])]
    return max(avant, key=int) if avant else None


def cmd_approuver(a_blanc, conf, api=discord):
    """Un lot est approuvé par UN message « ok lot » écrit par Liam APRÈS sa publication, ou par un ✅ de Liam sur le message du lot (utilisateur_id seulement).
    Avec envoi_automatique = true, le lot DU JOUR est approuvé d'office ; toutes les autres protections de l'envoi restent actives."""
    etat = etat_lire(); attente = {m: v for m, v in etat["lots_discord"].items() if not v.get("approuve")}
    if not attente: print("Aucun lot en attente d'approbation."); return 0
    auto = conf["envoi_automatique"]
    if a_blanc:
        print(f"  [à blanc] {len(attente)} lot(s) en attente ; " + ("envoi_automatique = true : le lot du jour serait approuvé d'office. " if auto else "") + "lecture de Discord sautée, aucun lot approuvé."); return 0
    acces = None if auto and all(v["date"] == aujourdhui() for v in attente.values()) else acces_discord()
    if not acces and not auto: return 0
    jeton, salon_ancien, uid = acces or ("", "", "")
    n = 0
    for mid, lot in attente.items():
        salon = lot.get("salon") or salon_ancien   # lot posté avant le salon « lots » : il reste lisible dans l'ancien salon
        meme_salon = {m: v for m, v in etat["lots_discord"].items() if (v.get("salon") or salon_ancien) == salon}
        d_office = auto and lot["date"] == aujourdhui()
        if not d_office:
            react = api(jeton, "GET", f"/channels/{salon}/messages/{mid}/reactions/%E2%9C%85?limit=100") or []
            suite = api(jeton, "GET", f"/channels/{salon}/messages?after={mid}&limit=100") or []
            liam = [x for x in suite if str(x.get("author", {}).get("id")) == uid and not x.get("author", {}).get("bot")]
            oks = [x for x in liam if OK_LOT.fullmatch(x.get("content", "")) and x["id"] not in etat["ok_utilises"] and cible_ok(x, meme_salon) == mid]   # un « ok lot » n'autorise QUE son lot, une seule fois
            if not (any(str(u.get("id")) == uid for u in react) or oks):
                if liam and not any(x.get("content") for x in liam): print("  (contenu des messages illisible par le bot : utilise le ✅)")
                continue
            if oks and not any(str(u.get("id")) == uid for u in react): etat["ok_utilises"].append(oks[0]["id"])
        texte = MESSAGES.read_text(encoding="utf-8")
        for id_ in lot["ids"]:
            if next((b for b in lire_blocs(texte) if b["id"] == id_), {}).get("statut") == "à valider":
                texte = marquer(texte, id_, "validé"); etat["approuves"].append(id_)
        MESSAGES.write_text(texte, encoding="utf-8"); lot["approuve"] = True; n += 1; etat_ecrire(etat, False)
        print(f"Lot {lot['date']} approuvé " + ("d'office (envoi_automatique = true)." if d_office else "par Liam sur Discord."))
    return n


def en_attente_d_envoi(etat):
    return any(not v.get("approuve") for v in etat["lots_discord"].values())


def cmd_ecouter(a_blanc, conf, dormir=time.sleep, api=discord, envoi=None, lien_ok=lien_accessible, maintenant=time.time):
    """Écoute Discord (lecture seule + REST) jusqu'à ce que tous les lots publiés soient approuvés puis envoyés, ou ecoute_max_heures. Un seul écouteur à la fois."""
    if a_blanc:
        print("  [à blanc] écoute simulée : un seul passage approuver + envoyer à blanc."); cmd_approuver(True, conf, api); cmd_envoyer(True, conf); return 0
    if VERROU.exists() and maintenant() - VERROU.stat().st_mtime < 3600 * (conf["ecoute_max_heures"] + 2):
        print("Un écouteur tourne déjà (prospection.verrou)."); return 0
    fin = maintenant() + 3600 * conf["ecoute_max_heures"]; n = 0
    try:
        while True:
            VERROU.write_text(str(int(maintenant())), encoding="utf-8")
            cmd_approuver(False, conf, api); n += cmd_envoyer(False, conf, envoi, dormir, lien_ok)
            if boites() and set(boites()) <= _client.get("hors", set()): break  # toutes les boîtes sont hors service : message déjà affiché, inutile de réessayer toutes les minutes
            if not en_attente_d_envoi(etat_lire()) or maintenant() >= fin: break
            dormir(conf["ecoute_pause_s"])
    finally: VERROU.unlink(missing_ok=True)
    return n


def cmd_demarrage(a_blanc, conf, **kw):
    """Appelé par Jarvis au démarrage : 'jour' UNE fois par jour au plus (date gardée dans prospection-dernier-lancement.txt), puis l'écoute des lots."""
    deja = DERNIER.exists() and DERNIER.read_text(encoding="utf-8").strip().startswith(aujourdhui())
    if deja: print("Journée déjà lancée aujourd'hui : pas de nouvelle recherche.")
    elif a_blanc: print("  [à blanc] la journée serait lancée maintenant (date du dernier lancement non écrite).")
    else: DERNIER.write_text(aujourdhui(), encoding="utf-8")
    if not deja: cmd_jour(a_blanc, conf)
    return cmd_ecouter(a_blanc, conf, **kw)


def cmd_jour(a_blanc, conf):
    cmd_reponses(a_blanc); cmd_chercher(a_blanc, conf)
    if conf.get("decouverte_osm"): cmd_decouvrir(a_blanc, conf); cmd_appels(a_blanc, conf)
    integrer_saisies(a_blanc, conf); cmd_preparer(a_blanc, conf); cmd_relances(a_blanc, conf); cmd_publier(a_blanc, conf)


def cmd_reponses(a_blanc):
    subprocess.run([sys.executable, str(ICI / "reponses.py")] + (["--a-blanc"] if a_blanc else []), check=False, timeout=600)

# --- fonctionnement continu : une boucle dans le processus de l'agent, tant que Jarvis est en ligne ---------------------------------
ARRET, VERROU_C = ICI / "prospection.arret", ICI / "prospection-continu.verrou"


def quota_jour(conf, nb_boites=None):
    """E-mails à préparer, valider et envoyer par jour : quota_par_boite (plafonné par par_boite_par_jour) x boîtes autorisées."""
    return min(conf["quota_par_boite"], conf["par_boite_par_jour"]) * (len(boites()) if nb_boites is None else nb_boites)


def processus_vivant(pid):
    try:
        import ctypes
        k = ctypes.windll.kernel32; h = k.OpenProcess(0x1000, False, int(pid))
        if not h: return False
        code = ctypes.c_ulong(); ok = k.GetExitCodeProcess(h, ctypes.byref(code)); k.CloseHandle(h)
        return bool(ok) and code.value == 259  # STILL_ACTIVE
    except (ImportError, AttributeError):
        import os
        try: os.kill(int(pid), 0); return True
        except OSError: return False


def boucle_active():
    """Une boucle tourne-t-elle ? Le verrou contient son numéro de processus (une pause d'envoi peut durer 5 minutes : l'heure du fichier ne suffit pas)."""
    try: return VERROU_C.exists() and processus_vivant(int(VERROU_C.read_text(encoding="utf-8").strip()))
    except (ValueError, OSError): return False


class _Arret(Exception):
    pass


def eligibles():
    """Prospects « trouvé » qu'un lot peut encore accueillir (non exclus, page exemple de leur métier en ligne)."""
    cles, mails = exclusions()
    return [l for l in lire_trouves() if l["statut"] == "trouvé" and not ZN.cp_hors_zone(l.get("cp", "")) and S.cle(l) not in cles and l["email"].lower() not in mails and lien_exemple(l.get("metier", ""))]


def bilan(conf, jour=None, lien_ok=lien_accessible):
    """Chiffres du jour, relus dans les fichiers (aucun compteur à tenir à jour) : trouvés, préparés, validés, envoyés, bloqués, en cours, non publiés."""
    jour = jour or aujourdhui(); etat = etat_lire()
    b = {"trouves": sum(1 for l in lire_trouves() if l.get("date_collecte") == jour), "prepares": 0, "valides": 0,
         "envoyes": sum(etat["envoyes"].get(jour, {}).values()), "bloques": 0, "en_cours": 0, "non_publies": 0}
    cles, mails = exclusions()
    for x in (lire_blocs(MESSAGES.read_text(encoding="utf-8")) if MESSAGES.exists() else []):
        m = x["meta"] or {}
        if m.get("lot") != jour or m.get("type") not in ("email", "relance"): continue
        st = x["statut"].lower(); b["prepares"] += 1
        if st.startswith("envoy"): b["valides"] += 1; continue
        if not x["ok"]: b["bloques"] += 1; continue
        if st == "à valider": b["en_cours"] += 1; b["non_publies"] += x["id"] not in etat["publies"]
        elif st == "validé":
            b["valides"] += 1; motif = refus(x, etat, conf, cles, mails, lien_ok)
            if not motif or "non approuvé" in motif or "plafond" in motif: b["en_cours"] += 1
            else: b["bloques"] += 1
        else: b["bloques"] += 1
    return b


def ligne_bilan(jour, b, raison):
    return f"{jour} | trouvés {b['trouves']} | préparés {b['prepares']} | validés {b['valides']} | envoyés {b['envoyes']} | bloqués {b['bloques']} | arrêt : {raison}"


def continu_sauver(c):
    e = etat_lire(); e["continu"] = c; etat_ecrire(e, False)


def cmd_continu(a_blanc, conf, dormir=time.sleep, maintenant=time.time, vivant=None, lien_ok=lien_accessible, max_cycles=None):
    """Boucle de l'agent. Un cycle (recherche -> lot -> Discord -> approbation -> envoi) toutes les cycle_minutes ; recul exponentiel après une erreur ;
    veille jusqu'au lendemain quand le quota du jour est envoyé ou que les prospects éligibles sont épuisés ; arrêt si Jarvis s'arrête ou après `arreter`.
    Rien ne part sans « ok lot » / ✅ de Liam : envoi_automatique est forcé à false ici. Reprise après redémarrage grâce à l'état (champ « continu »)."""
    conf = {**conf, "envoi_automatique": False}
    if a_blanc: print(f"  [à blanc] boucle continue : quota {quota_jour(conf)} e-mail(s) par jour, un cycle toutes les {conf['cycle_minutes']} min. Rien lancé."); return 0
    if boucle_active(): print("Une boucle de prospection tourne déjà (prospection-continu.verrou)."); return 0
    ARRET.unlink(missing_ok=True)
    c = {"jour": "", "echecs": 0, "prochain": 0, "reponses": 0, "sans_nouveau": 0, "fini": "", "relances": False, **(etat_lire().get("continu") or {})}
    raison_arret, cycles = "", 0

    def bat():
        import os
        VERROU_C.write_text(str(os.getpid()), encoding="utf-8")
        if ARRET.exists(): return "arrêt demandé (prospection.py arreter)"
        if vivant and not vivant(): return "Jarvis s'est arrêté"
        return ""

    def pause(s):  # pause d'envoi découpée en battements de 5 s : l'arrêt reste immédiat
        for _ in range(int(s // 5) + 1):
            dormir(5); r = bat()
            if r: raise _Arret(r)

    erreurs = []

    def tentative(etape, f, *a):
        """Une étape du cycle : son erreur est tracée en entier sur stderr (logs\\prospection-AAAA-MM-JJ.log.err quand Jarvis lance la boucle) et n'empêche pas les étapes suivantes ; la première est relevée en fin de cycle pour le recul."""
        debut = time.time()
        try: return f(*a)
        except _Arret: raise
        except Exception as ex:
            erreurs.append(ex); print(f"  étape « {etape} » en erreur ({type(ex).__name__}: {str(ex)[:120]})")
            print(f"--- {datetime.now():%Y-%m-%d %H:%M:%S} étape « {etape} »", file=sys.stderr); traceback.print_exc(file=sys.stderr); sys.stderr.flush()
        finally:
            if time.time() - debut > 300: print(f"  étape « {etape} » longue : {int(time.time() - debut)} s")

    def ecrire_fin(jour, raison):
        traces = [l for l in (DERNIER.read_text(encoding="utf-8").splitlines() if DERNIER.exists() else []) if " | cycle | " in l][-200:]
        DERNIER.write_text("\n".join([ligne_bilan(jour, bilan(conf, jour, lien_ok), raison)] + traces), encoding="utf-8"); print("  " + ligne_bilan(jour, bilan(conf, jour, lien_ok), raison))

    def tracer(cle, source):  # une ligne par source et par cycle : heure | cycle | source | métier | commune | éléments | e-mails trouvés
        p = PASSAGE.pop(cle, None)
        if not p: return
        ligne = f"{aujourdhui()} {datetime.now().strftime('%H:%M')} | cycle | {source} | métier : {p['metier']} | commune : {p['commune']} | éléments : {p['elements']} | e-mails trouvés : {p['emails']}"
        anciennes = DERNIER.read_text(encoding="utf-8").splitlines() if DERNIER.exists() else []
        bilan_l = [l for l in anciennes[:1] if " | cycle | " not in l]
        DERNIER.write_text("\n".join(bilan_l + [l for l in anciennes if " | cycle | " in l][-199:] + [ligne]), encoding="utf-8")

    try:
        while not raison_arret:
            raison_arret = bat()
            if raison_arret: break
            jour = aujourdhui(); appliquer_vagues()
            if "palier" in conf: conf = avec_montee(conf)   # lancée par main : le palier suit les jours (et se fige si les retours montent)
            if c["jour"] != jour:  # nouvelle journée (ou premier lancement)
                if c["jour"] and not c["fini"]: ecrire_fin(c["jour"], "minuit atteint")
                c.update(jour=jour, echecs=0, sans_nouveau=0, fini="", relances=False, prochain=0); continu_sauver(c)
            if not c["fini"] and maintenant() >= c["prochain"]:
                cycles += 1; q = quota_jour(conf)
                try:
                    _client["erreur_api"] = False; erreurs.clear()
                    if q == 0: c["fini"] = "aucune boîte autorisée (jeton Gmail manquant)"
                    else:
                        tentative("envoi des lots validés", lambda: (cmd_approuver(False, conf), cmd_envoyer(False, conf, dormir=pause, lien_ok=lien_ok)))   # AVANT toute recherche : une panne de recherche ne retarde jamais un envoi
                        tentative("liste d'appels de 8 h", cmd_liste_matin, conf)   # 100 numéros jamais appelés, postés une fois par jour dans « appels-du-jour » ; rien n'est envoyé aux entreprises
                        def recherche():
                            nouveaux = []
                            if conf.get("decouverte_osm"):   # désactivé par défaut (prospection-config.json › decouverte_osm) ; en premier, avec son propre plafond du jour (osm_max_jour)
                                nouveaux += cmd_decouvrir(False, conf) or []; tracer("osm", "OpenStreetMap"); cmd_appels(False, conf)
                            if conf.get("decouverte_places"):   # désactivé par défaut (prospection-config.json › decouverte_places) ; plafond places_max_jour
                                nouveaux += cmd_places(False, conf) or []; tracer("places", "Google Places"); cmd_appels(False, conf)
                            nouveaux += cmd_chercher(False, conf) or []; tracer("annuaire", "annuaire")   # plafond de l'annuaire (max_examinees par jour) : ne bloque jamais la boucle
                            c["sans_nouveau"] = 0 if nouveaux else c["sans_nouveau"] + 1
                            integrer_saisies(False, conf)   # adresses saisies par Liam dans docs\liste-appels-*.md : relues à chaque cycle
                            cmd_preparer(False, conf)
                            if not c["relances"]: cmd_relances(False, conf); c["relances"] = True
                        if bilan(conf, jour, lien_ok)["prepares"] < q: tentative("recherche et préparation", recherche)
                        if tentative("vague suivante", vague_suivante_si_besoin, conf, jour, c["sans_nouveau"] >= conf["epuise_apres"]): c["sans_nouveau"] = 0   # la vague en cours ne donne plus assez : la suivante s'ouvre, le comptage repart de zéro
                        b = bilan(conf, jour, lien_ok); epuise = c["sans_nouveau"] >= conf["epuise_apres"] and not eligibles()
                        if b["non_publies"]: tentative("publication du lot", cmd_publier, False, conf)   # un lot par boîte : posté seulement quand la boîte a son quota (ou après l'heure limite)
                        tentative("envoi des lots validés", lambda: (cmd_approuver(False, conf), cmd_envoyer(False, conf, dormir=pause, lien_ok=lien_ok)))
                        if maintenant() - c["reponses"] >= 3600: tentative("réponses", cmd_reponses, False); c["reponses"] = maintenant()
                        if erreurs: raise erreurs[0]   # recul exponentiel comme avant, mais seulement après les envois
                        b = bilan(conf, jour, lien_ok); plein = b["prepares"] >= q or sum(etat_lire()["lots"].get(jour, {}).values()) >= q
                        if b["envoyes"] >= q and b["non_publies"]: print(f"  LOT RETARDÉ : {b['non_publies']} e-mail(s) du jour préparé(s) mais pas encore posté(s) (heure limite {conf['heure_limite']}) ; la boucle continue jusqu'à la publication")
                        if b["envoyes"] >= q and not b["non_publies"]: c["fini"] = f"quota atteint ({b['envoyes']} e-mail(s) envoyé(s))"
                        elif (epuise or plein) and not b["en_cours"]: c["fini"] = "liste des prospects éligibles épuisée pour aujourd'hui" if epuise else "quota de préparation atteint, plus rien à valider"
                    if _client.get("erreur_api"): raise OSError("annuaire ou recherche indisponible")
                    c["echecs"] = 0
                except _Arret as ex:
                    raison_arret = str(ex); break
                except Exception as ex:
                    c["echecs"] += 1; print(f"  cycle en erreur ({type(ex).__name__}: {str(ex)[:120]}) : nouvel essai après recul")
                    print(f"--- {datetime.now():%Y-%m-%d %H:%M:%S} cycle", file=sys.stderr); traceback.print_exc(file=sys.stderr); sys.stderr.flush()
                pas = conf["cycle_minutes"] * 60
                c["prochain"] = maintenant() + (min(pas * 2 ** min(c["echecs"], 6), conf["recul_max_minutes"] * 60) if c["echecs"] else pas)
                if c["fini"]: ecrire_fin(jour, c["fini"])
                continu_sauver(c)
                if max_cycles and cycles >= max_cycles: raison_arret = "nombre de cycles atteint (test)"; break
            dormir(5)
    finally:
        VERROU_C.unlink(missing_ok=True)
        if raison_arret and not raison_arret.startswith("nombre") and not c["fini"]: ecrire_fin(aujourdhui(), raison_arret)
        if raison_arret.startswith("arrêt"): ARRET.unlink(missing_ok=True)
    return cycles


def cmd_arreter():
    """Commande de secours : demande à la boucle de s'arrêter proprement (au prochain battement, 5 s au plus)."""
    if boucle_active(): ARRET.write_text(str(int(time.time())), encoding="utf-8"); print("Arrêt demandé : la boucle s'arrête dans quelques secondes (au prochain battement, même pendant une pause d'envoi).")
    else: ARRET.unlink(missing_ok=True); VERROU_C.unlink(missing_ok=True); print("Aucune boucle de prospection en cours.")


# --- découverte « depuis les sites » : OpenStreetMap (Overpass), canal appel-SMS, saisies de Liam -----------------------------------------------
# Source : © les contributeurs d'OpenStreetMap, licence ODbL 1.0 (https://www.openstreetmap.org/copyright) ; voir docs\SOURCES-DONNEES.md.
# Overpass : une requête à la fois, pause entre deux requêtes, User-Agent explicite. Aucune lecture de Google ni de Facebook. Rien n'est envoyé.
OVERPASS = "https://overpass-api.de/api/interpreter"
DOCS = RACINE / "docs"
OSM_METIERS = [("électricien", ["craft=electrician"]), ("plombier-chauffagiste", ["craft=plumber", "craft=hvac"]), ("couvreur", ["craft=roofer"]), ("maçon", ["craft=builder", "craft=mason"]),
               ("peintre", ["craft=painter"]), ("menuisier", ["craft=carpenter"]), ("plâtrier", ["craft=plasterer"]), ("restaurant", ["amenity=restaurant", "amenity=fast_food"]),
               ("coiffeur", ["shop=hairdresser"]), ("fleuriste", ["shop=florist"]), ("boulangerie", ["shop=bakery", "shop=pastry"]), ("garage automobile", ["shop=car_repair"]),
               ("taxi", ["office=taxi"]), ("auto-école", ["amenity=driving_school"]), ("esthéticienne", ["shop=beauty"]),
               # Ajoutés le 10 nov. 2026 pour appels-sid (~20 métiers) : couverture OpenStreetMap plus clairsemée pour ces métiers que pour les premiers, à surveiller.
               ("carreleur", ["craft=tiler"]), ("onglerie", ["beauty=nails"]), ("traiteur", ["shop=caterer"]), ("boucher", ["shop=butcher"]),
               ("serrurier", ["craft=locksmith"]), ("paysagiste", ["craft=gardener"]), ("nettoyage", ["craft=cleaner"])]
ROUEN = (49.4431, 1.0993)


def zones_osm():
    """Zones Overpass : le cercle de 40 km autour de Rouen d'abord, puis les départements des vagues ouvertes (zone.py), vague 1 d'abord."""
    return [{"id": "rouen-40km", "type": "rayon"}] + [{"id": f"dept-{d}", "type": "dept", "dept": d} for d in ZN.departements_ouverts()]


PLATEFORMES = re.compile(r"wix|ovh|ionos|1and1|godaddy|squarespace|jimdo|weebly|shopify|webnode|hostinger|gandi|o2switch|infomaniak|cloudflare|sentry|wordpress|domainsbyproxy|namecheap|ikoula|planethoster|pagesjaunes|solocal|facebook|google", re.I)
EMAIL_OK = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$")


def email_valide(s):
    return bool(EMAIL_OK.match((s or "").strip()))


def email_plateforme(a):
    """Adresse d'une plateforme (hébergeur, constructeur de site, annuaire) et non de l'entreprise : ignorée."""
    return bool(PLATEFORMES.search(a.split("@")[-1])) or bool(MAUVAIS_MAIL.search(a))


def requete_overpass(tags, zone, conf):
    """Requête Overpass : les éléments portant l'un des tags, dans le cercle autour de Rouen ou dans un département. Résultat : JSON, centre des surfaces, tags."""
    centre, rayon = zone.get("centre", ROUEN), zone.get("rayon", conf["rayon_osm_m"])
    filtre = f"(around:{rayon},{centre[0]},{centre[1]})" if zone["type"] == "rayon" else "(area.a)"
    corps = "".join(f'nwr["{k}"="{v}"]{filtre};' for k, v in (t.split("=") for t in tags))
    zone_def = f'area["boundary"="administrative"]["ref:INSEE"="{zone["dept"]}"]->.a;' if zone["type"] == "dept" else ""
    return f"[out:json][timeout:90];{zone_def}({corps});out center tags;"


def appel_overpass(requete, ouvrir=urllib.request.urlopen, dormir=time.sleep):
    """Une requête Overpass. En cas de refus (429, 5xx) : jusqu'à 3 nouveaux essais après 30, 60 et 120 s, puis l'erreur remonte."""
    ident = ""
    try: ident = json.loads((ICI / "identite.json").read_text(encoding="utf-8")).get("email_reponse", "")
    except (OSError, ValueError): pass
    ua = "LM-MULTI-SERVICES-prospection/1.0 (découverte de sites d'entreprises, 1 requête à la fois" + (f" ; contact : {ident}" if ident else "") + ")"
    rq = urllib.request.Request(OVERPASS, data=urllib.parse.urlencode({"data": requete}).encode(), headers={"User-Agent": ua})
    for essai, attente in enumerate((0, 30, 60, 120)):
        if attente: dormir(attente)
        try:
            with ouvrir(rq, timeout=120) as r: return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504) or essai == 3: raise
        except (urllib.error.URLError, TimeoutError, OSError):
            if essai == 3: raise


def candidats_osm(data, metier):
    """Éléments Overpass -> candidats {id, nom, metier, ville, cp, site, emails, telephone}. Sans nom ni commune : ignoré (on ne peut pas écrire à « Rouen et alentours »)."""
    out = []
    for el in data.get("elements", []):
        t = el.get("tags") or {}
        nom, ville = (t.get("name") or t.get("brand") or "").strip(), (t.get("addr:city") or "").strip()
        if not nom or not ville: continue
        c = el.get("center") or {}; lat, lon = el.get("lat", c.get("lat")), el.get("lon", c.get("lon"))
        if not ZN.dans_zone(cp=t.get("addr:postcode", ""), ville=ville, lat=lat, lon=lon): continue   # hors zone (coordonnées, sinon code postal) : rejeté
        site = (t.get("website") or t.get("contact:website") or t.get("url") or "").strip()
        if site and not site.startswith("http"): site = "https://" + site
        mails = [a.strip().lower() for v in (t.get("email"), t.get("contact:email")) if v for a in re.split(r"[;,]", v) if a.strip()]
        tel = ""
        for v in (t.get("phone"), t.get("contact:phone"), t.get("mobile"), t.get("contact:mobile")):
            n = G.tel_norm(re.split(r"[;,]", v)[0]) if v else (None, None)
            if n[0]: tel = n[0]; break
        out.append({"id": f"{el.get('type', 'node')}/{el.get('id')}", "nom": beau(nom), "metier": metier, "ville": beau(ville), "cp": t.get("addr:postcode", ""), "site": site, "emails": mails, "telephone": tel})
    return out


def enrichir_osm(c, etat, conf, lire=lire_page, outils=None, stat=None, dormir=time.sleep):
    """-> (ligne CSV, None) ou (None, motif). Site (page d'accueil lue UNE fois) faible d'après constats vérifiés ; e-mail : tag OSM, puis lien mailto / texte de l'accueil, puis page contact ou mentions légales ;
    sinon formulaire de contact du site ; sinon téléphone seulement (statut « appel »). Aucune affirmation sur un site qu'on n'a pas lu."""
    stat = stat if stat is not None else {}
    stat.update(site=False, faible=False, constats=[], canal="", telephone=False)
    if not metier_actif(c["metier"]): return None, "métier sans page exemple (agents\\liens-metiers.json) : " + c["metier"]
    ligne = {k: "" for k in COLS}
    ligne.update(nom=c["nom"], metier=c["metier"], ville=c["ville"], cp=c.get("cp", ""), telephone=c.get("telephone", ""), osm=c["id"], date_collecte=aujourdhui(), statut="trouvé",
                 source=c.get("source", "OpenStreetMap, base de données ouverte"))
    mail_osm = next((a for a in c.get("emails", []) if email_valide(a) and not email_plateforme(a)), "")
    email, origine, formulaire, dom = "", "", "", ""
    r, chrono = None, {}
    if c.get("site"): r = lire(c["site"], chrono=chrono)
    else:   # fiche OpenStreetMap sans site : on teste les noms de domaine usuels (4 au plus, vérifiés par la commune ou le code postal), rien d'autre n'est deviné
        for d in domaines(c["nom"])[:4]:
            dormir(conf["pause_site_s"]); rr = lire("https://" + d, chrono=chrono)
            if rr and verifie_osm(rr[2], c): r = rr; break
    if r:
        url, _, texte = r; stat["site"] = True
        o = {"images_reseau": True, **(outils or {}), "mesure": (lambda u: (chrono.get("octets", 0), chrono["sec"]) if chrono.get("sec") else None), "psi": (lambda u: None)}   # page d'accueil lue une seule fois : pas de seconde mesure, pas de PageSpeed
        cs = constats_site(url, texte, conf, None, o); sc = score_faiblesse(cs)
        stat["constats"], stat["faible"], stat["score"] = [k for k, _ in cs], sc >= conf["seuil_faiblesse"], sc
        if not stat["faible"]: return None, f"site correct (score de faiblesse {sc}, seuil {conf['seuil_faiblesse']})"
        ligne.update(site_actuel=url, note_besoin=note_constats(cs), score=str(sc))
        dom = urllib.parse.urlparse(url).netloc.lower().removeprefix("www.")
        pages = [(url, texte)]
        if mail_osm: email, origine = mail_osm, "OpenStreetMap (tag email)"
        else:
            tr = [a for a, _ in emails_page(texte, dom) if not email_plateforme(a)]
            if tr: email, origine = tr[0], "page d'accueil de " + url
        if not email or not a_formulaire(texte):
            liens = [urllib.parse.urljoin(url, h) for h in re.findall(r'href=["\']([^"\']+)["\']', texte) if re.search(r"contact|mention|legal", h, re.I) and dom in urllib.parse.urljoin(url, h)]
            for ch in list(dict.fromkeys(liens))[:2]:
                dormir(conf["pause_site_s"]); r2 = lire(ch)
                if not r2: continue
                pages.append((r2[0], r2[2]))
                if not email:
                    tr = [a for a, _ in emails_page(r2[2], dom) if not email_plateforme(a)]
                    if tr: email, origine = tr[0], "page contact / mentions légales de " + url
        formulaire = next((u for u, tx in pages if a_formulaire(tx)), "")
        if email and origine.startswith("page"): ligne["source"] += f" ; adresse publiée sur votre site ({dom})"
    else:
        if c.get("site"): return None, "site indiqué mais illisible : aucun constat vérifié sur son site"
        if mail_osm: email, origine = mail_osm, "OpenStreetMap (tag email)"
        if not c.get("site"): ligne["modele"] = "sans-site"   # recherche faite, aucun site trouvé : modèle de message « je n'ai pas trouvé de site à votre nom »
    if email:
        ligne.update(email=email, email_type="generique" if email.split("@")[0] in GENERIQUES else "nominatif", email_source=origine); stat["canal"] = "email"; return ligne, None
    if formulaire: ligne.update(formulaire=formulaire); stat["canal"] = "formulaire"; return ligne, None
    if ligne["telephone"]:
        ligne["statut"] = "sans site, téléphone" if not stat["site"] else "téléphone seulement"; stat["canal"] = "telephone"; stat["telephone"] = not stat["site"]
        return ligne, None
    return None, "aucun e-mail, formulaire ni téléphone"


def verifie_osm(texte, c):   # la page parle bien de CETTE entreprise : sa commune ou son code postal y figurent
    return norm(c["ville"]) in norm(texte) or bool(c.get("cp") and c["cp"] in texte)


def lien_declare(metier):
    """Adresse de la page exemple du métier d'après agents\liens-metiers.json (sans réseau), ou ''."""
    cle = R.cle_metier(metier or ""); f = ICI / "liens-metiers.json"
    try: return next((u for k, u in json.loads(f.read_text(encoding="utf-8")).items() if k.split("-")[0] == cle), "")
    except (OSError, ValueError): return ""


STATUTS_TEL = ("sans site, téléphone", "téléphone seulement")


def memoriser_telephone(etat, ligne, ident):
    """Entreprise sans e-mail ni formulaire mais avec téléphone : entrée dans prospection-etat.json (par métier) + texte de SMS (300 caractères au plus, identification et STOP), STOCKÉ et jamais envoyé."""
    cle = R.cle_metier(ligne["metier"]); sms = R.sms_appel(ligne, ident, cle, lien_declare(ligne["metier"]))
    etat.setdefault("sans_site_telephone", {}).setdefault(ligne["metier"], {})[S.cle(ligne).replace("|", "~")] = {"nom": ligne["nom"], "ville": ligne["ville"], "telephone": ligne["telephone"], "statut": ligne["statut"],
        "sms": sms, "sms_envoye": False, "date": aujourdhui()}


def requetes_osm(etat):
    """(zone, métier, tags, clé) restant à interroger : le cercle autour de Rouen d'abord, puis les départements des vagues ouvertes dans l'ordre ; seulement les métiers actifs."""
    faits = set(etat.setdefault("osm", {}).setdefault("faits", []))
    actifs = [(lab, tags) for lab, tags in OSM_METIERS if metier_actif(lab)]
    for z in zones_osm():
        for lab, tags in actifs:
            k = f"{z['id']}|{lab}"
            if k not in faits: yield z, lab, tags, k


def cmd_decouvrir(a_blanc, conf, ouvrir=urllib.request.urlopen, lire=lire_page, dormir=time.sleep, outils=None):
    """Découverte depuis les sites : interroge OpenStreetMap (osm_requetes_par_passage requêtes au plus, une à la fois), puis examine au plus osm_max_examinees entreprises.
    Exclusions (STOP, refus, saisies de Liam) et doublons (prospection-etat.json › vus, prospection-trouves.csv) respectés. Les lots restent soumis à « ok lot »."""
    etat = etat_lire(); cles, mails = exclusions(); garde = lire_trouves(); osm = etat.setdefault("osm", {"faits": [], "tampon": []}); tampon = osm.setdefault("tampon", [])
    deja = {S.cle(l) for l in garde}; adresses = {l["email"].lower() for l in garde if l["email"]}; n_req = 0; ident_osm, _ = R.charger_identite()
    budget = max(0, min(conf["osm_max_examinees"], conf["osm_max_jour"] - examinees_jour(etat, "stats_osm"))); reqs = []   # compteur du jour propre à OpenStreetMap
    if not budget: print(f"  OpenStreetMap : plafond du jour atteint ({conf['osm_max_jour']} examinées), passage sauté")
    for z, lab, tags, k in list(requetes_osm(etat)) if budget else []:
        if n_req >= conf["osm_requetes_par_passage"] or len(tampon) >= conf["osm_max_examinees"] * 3: break
        if n_req: dormir(conf["pause_overpass_s"])
        try: data = appel_overpass(requete_overpass(tags, z, conf), ouvrir, dormir)
        except Exception as e:
            print(f"  Overpass : erreur {type(e).__name__} ({k}), arrêt de ce passage"); _client["erreur_api"] = True; break
        vus_t = {x["id"] for x in tampon}
        for c in candidats_osm(data, lab):
            if "osm:" + c["id"] not in etat["vus"] and c["id"] not in vus_t: tampon.append(c); vus_t.add(c["id"])
        osm["faits"].append(k); n_req += 1; reqs.append((lab, z["id"], len(data.get("elements", []))))
        print(f"  Overpass {k} : {len(data.get('elements', []))} élément(s)")
    stats, nouveaux, raisons, examines = {}, [], {}, 0
    while tampon and examines < budget:
        c = tampon.pop(0); examines += 1
        if "osm:" + c["id"] in etat["vus"]: continue
        st = {}
        ligne, motif = enrichir_osm(c, etat, conf, lire, outils, st, dormir)
        mx = ligne and motif_ligne(ligne, garde + nouveaux, cles, mails, deja, adresses)
        if mx: ligne, motif = None, mx
        compter(stats, c["metier"], st)
        if ligne:
            nouveaux.append(ligne); deja.add(S.cle(ligne)); adresses.add(ligne["email"].lower()) if ligne["email"] else None
            if ligne["statut"] in STATUTS_TEL: memoriser_telephone(etat, ligne, ident_osm)
            print(f"  + {ligne['nom']} ({ligne['ville']}) [{st['canal']}] {ligne['email'] or ligne['formulaire'] or ligne['telephone']}")
        else: raisons[motif] = raisons.get(motif, 0) + 1
        etat["vus"]["osm:" + c["id"]] = "retenu" if ligne else motif
        dormir(conf["pause_site_s"])   # pause entre deux entreprises examinées (sites lus ou domaines essayés)
    print(f"{examines} entreprise(s) examinée(s) depuis OpenStreetMap, {len(nouveaux)} retenue(s)" + (" ; écartées : " + ", ".join(f"{v} {k}" for k, v in raisons.items()) if raisons else "") + f" ; {len(tampon)} en réserve")
    print(rapport_texte(stats, "Rapport de ce passage (découverte depuis les sites)"))
    PASSAGE["osm"] = {"metier": ", ".join(dict.fromkeys(r[0] for r in reqs)) or ", ".join(sorted(stats)) or "-", "commune": ", ".join(dict.fromkeys(r[1] for r in reqs)) or "(réserve)",
                      "elements": sum(r[2] for r in reqs) or examines, "emails": sum(1 for l in nouveaux if l.get("email"))}
    if a_blanc: print("  [à blanc] rien écrit"); return nouveaux
    s = etat.setdefault("stats_osm", {"cumul": {}, "jours": {}}); fusionner(s["cumul"], stats); fusionner(s["jours"].setdefault(aujourdhui(), {}), stats)
    for j in sorted(s["jours"])[:-14]: del s["jours"][j]
    ecrire_trouves(garde + nouveaux); etat_ecrire(etat, False)
    return nouveaux


# --- source Google Places API (New) : Text Search, FieldMask minimal, plafond places_max_jour ----------------------------------------------------
# Clé GOOGLE_PLACES_API_KEY dans B2B\.env : jamais affichée ni journalisée. Une requête = jusqu'à 20 fiches ; rien n'est envoyé. Les conditions de Google s'appliquent à ces données.
PLACES_URL = "https://places.googleapis.com/v1/places:searchText"
PLACES_MASQUE = "places.id,places.displayName,places.formattedAddress,places.websiteUri"
PLACES_VILLES = {1: ["Rouen", "Le Havre", "Évreux", "Dieppe", "Elbeuf", "Sotteville-lès-Rouen", "Mont-Saint-Aignan"],   # villes interrogées par vague ouverte (zone.py) ; la vague 4 n'a pas de liste : annuaire et OpenStreetMap seulement
                 2: ["Caen", "Lisieux", "Cherbourg-en-Cotentin", "Saint-Lô", "Alençon"],   # Normandie seulement (10/11/2026) : Beauvais/Amiens/Chartres déménagent en vague 3, hors zone
                 3: ["Beauvais", "Compiègne", "Amiens", "Abbeville", "Chartres", "Dreux", "Paris", "Boulogne-Billancourt", "Saint-Denis", "Créteil", "Versailles", "Cergy", "Le Mans", "Laval", "Rennes", "Saint-Malo"]}


def villes_places():
    return [v for n in range(1, ZN.VAGUE_MAX + 1) for v in PLACES_VILLES.get(n, [])]


VITRINES = re.compile(r"(?:^|\.)(?:instagram|facebook|fb|linktr|planity|doctolib|pagesjaunes|tripadvisor|thefork|treatwell|booksy|kiute|google|goo|business\.site|ubereats|deliveroo)\.", re.I)


def cle_places():
    return (P.lire_env(RACINE / ".env").get("GOOGLE_PLACES_API_KEY") or "").strip()


def appel_places(texte, cle, ouvrir=urllib.request.urlopen):
    """Une requête Text Search. Pas de nouvel essai : l'erreur remonte telle quelle (message de Google, clé masquée)."""
    rq = urllib.request.Request(PLACES_URL, data=json.dumps({"textQuery": texte, "languageCode": "fr", "regionCode": "FR"}).encode(),
                                headers={"Content-Type": "application/json", "X-Goog-Api-Key": cle, "X-Goog-FieldMask": PLACES_MASQUE})
    try:
        with ouvrir(rq, timeout=30) as r: return json.load(r)
    except urllib.error.HTTPError as e:
        corps = e.read().decode("utf-8", "replace").replace(cle, "***")
        raise OSError(f"Google Places HTTP {e.code} : {corps[:400]}") from None


def candidats_places(data, metier, ville_req=""):
    """Fiches Places -> candidats comme candidats_osm. Un site « vitrine » (réseau social, plateforme de réservation, annuaire) n'est pas un site de l'entreprise : site vide. Sans nom ni commune : ignoré."""
    out = []
    for p in data.get("places", []):
        nom = ((p.get("displayName") or {}).get("text") or "").strip(); m = re.search(r"(\d{5})\s+([^,]+)", p.get("formattedAddress") or "")
        if not nom or not m or not ZN.dans_zone(cp=m.group(1)): continue   # hors zone (code postal de l'adresse) : rejeté
        site = (p.get("websiteUri") or "").strip()
        if site and VITRINES.search(urllib.parse.urlparse(site).netloc.lower() + "."): site = ""
        out.append({"id": "places/" + str(p.get("id") or norm(nom) + m.group(1)), "nom": beau(nom), "metier": metier, "ville": beau(m.group(2).strip()), "cp": m.group(1), "site": site, "emails": [], "telephone": "",
                    "source": "Google Places (fiche publique)"})
    return out


def cmd_places(a_blanc, conf, ouvrir=urllib.request.urlopen, lire=lire_page, dormir=time.sleep, outils=None):
    """Découverte par Google Places : places_requetes_par_passage requêtes au plus (une par métier actif et par ville), puis examen d'au plus places_max_jour entreprises par jour.
    Même jugement que pour OpenStreetMap (site lu une fois, constats vérifiés, e-mail ou formulaire du site). Conservation limitée : prospection-etat.json ne garde que l'identifiant de fiche
    (place_id), le domaine du site et le jugement (score, constats, e-mail, formulaire). Nom, adresse et téléphone de Google restent en mémoire le temps du cycle (pas de réserve entre deux cycles) ;
    seule une entreprise dont le SITE donne un e-mail ou un formulaire entre dans prospection-trouves.csv (nom, ville, métier, e-mail) ; le téléphone de Google n'est jamais gardé ni mis en liste d'appels."""
    etat = etat_lire(); cles, mails = exclusions(); garde = lire_trouves(); pl = etat.setdefault("places", {"faits": [], "jugements": {}}); pl.pop("tampon", None); jug = pl.setdefault("jugements", {})
    restant = max(0, conf["places_max_jour"] - examinees_jour(etat, "stats_places")); reqs, n_req, stats, nouveaux, raisons, examines = [], 0, {}, [], {}, 0
    cle = cle_places() if restant else ""
    if not restant: print(f"  Google Places : plafond du jour atteint ({conf['places_max_jour']} examinées), passage sauté")
    elif not cle: print("  Google Places : GOOGLE_PLACES_API_KEY absente de B2B\\.env, source sautée"); restant = 0
    deja = {S.cle(l) for l in garde}; adresses = {l["email"].lower() for l in garde if l["email"]}
    actifs = [lab for lab, _ in OSM_METIERS if metier_actif(lab)]; faits = set(pl["faits"])
    for ville in villes_places():
        for lab in actifs:
            k = f"{ville}|{lab}"
            if restant <= 0 or k in faits or n_req >= conf["places_requetes_par_passage"]: continue
            try: data = appel_places(f"{lab} {ville}", cle, ouvrir)
            except Exception as e:
                print(f"  {e}"); _client["erreur_api"] = True; restant = 0; continue   # erreur de facturation ou d'autorisation : arrêt de la source, aucun nouvel essai
            n_req += 1; cands = [c for c in candidats_places(data, lab) if "places:" + c["id"] not in etat["vus"]]; reqs.append((lab, ville, len(data.get("places", [])))); print(f"  Google Places {k} : {len(data.get('places', []))} fiche(s)")
            for c in cands[:restant]:
                examines += 1; restant -= 1; st = {}
                ligne, motif = enrichir_osm(c, etat, conf, lire, outils, st, dormir)
                if ligne: ligne.update(cp="", telephone="")   # adresse et téléphone de Google : jamais gardés
                mx = ligne and motif_ligne(ligne, garde + nouveaux, cles, mails, deja, adresses)
                if mx: ligne, motif = None, mx
                compter(stats, c["metier"], st)
                dom = urllib.parse.urlparse(ligne["site_actuel"] if ligne else c["site"]).netloc.lower().removeprefix("www.")
                jug[c["id"].removeprefix("places/")] = {"domaine": dom, "score": st.get("score"), "constats": st.get("constats", []), "email": ligne["email"] if ligne else "", "formulaire": ligne["formulaire"] if ligne else ""}
                if ligne:
                    nouveaux.append(ligne); deja.add(S.cle(ligne)); adresses.add(ligne["email"].lower()) if ligne["email"] else None
                    print(f"  + {ligne['nom']} ({ligne['ville']}) [{st['canal']}] {ligne['email'] or ligne['formulaire']}")
                else: raisons[motif] = raisons.get(motif, 0) + 1
                etat["vus"]["places:" + c["id"]] = "retenu" if ligne else motif
                dormir(conf["pause_site_s"])
            if all("places:" + c["id"] in etat["vus"] for c in cands): pl["faits"].append(k)   # requête terminée seulement si toutes ses fiches sont examinées
    print(f"{examines} entreprise(s) examinée(s) depuis Google Places, {len(nouveaux)} retenue(s)" + (" ; écartées : " + ", ".join(f"{v} {k}" for k, v in raisons.items()) if raisons else ""))
    print(rapport_texte(stats, "Rapport de ce passage (Google Places)"))
    PASSAGE["places"] = {"metier": ", ".join(dict.fromkeys(r[0] for r in reqs)) or ", ".join(sorted(stats)) or "-", "commune": ", ".join(dict.fromkeys(r[1] for r in reqs)) or "-",
                         "elements": sum(r[2] for r in reqs) or examines, "emails": sum(1 for l in nouveaux if l.get("email"))}
    if a_blanc: print("  [à blanc] rien écrit"); return nouveaux
    s = etat.setdefault("stats_places", {"cumul": {}, "jours": {}}); fusionner(s["cumul"], stats); fusionner(s["jours"].setdefault(aujourdhui(), {}), stats)
    for j in sorted(s["jours"])[:-14]: del s["jours"][j]
    ecrire_trouves(garde + nouveaux); etat_ecrire(etat, False)
    return nouveaux


# --- canal appel-SMS : liste du jour, saisies de Liam ----------------------------------------------------------------------------------------------------
ENTETE_LISTE = "| # | Nom | Ville | Téléphone | Métier | Page exemple | e-mail trouvé (à remplir par Liam) | lien Facebook / fiche Google (à remplir) | appelé | répondu | refus | STOP |"


def choisir_appels(lignes, etat, conf, exclues):
    """Au plus appels_par_jour lignes avec téléphone : d'abord les entreprises déjà listées mais jamais appelées (la liste la plus récente d'abord), puis des lignes « sans site (ou site non joignable / sans e-mail) mais avec téléphone » jamais listées,
    réparties à tour de rôle entre les métiers actifs puis classées restaurants, coiffeurs, boulangeries… ; jamais deux fois la même entreprise, jamais un refus ni un exclu."""
    listees = set(etat.setdefault("appels", {}).setdefault("listees", [])); pool, out = {}, []
    reprises, dans_listes = a_reprendre(exclues); par_cle = {S.cle(l): l for l in lignes}; suivi = {S.cle(x): x for x in S.lire()}
    for k in reprises:
        l = par_cle.get(k) or suivi.get(k)
        if l and l.get("telephone") and l.get("statut") not in ("hors zone", "refusé", "STOP", "exclu", "écarté") and not ZN.cp_hors_zone(l.get("cp", "")) and metier_actif(l["metier"]) and len(out) < conf["appels_par_jour"]: out.append(l)
    for l in lignes:
        if l.get("statut") not in STATUTS_TEL or not l.get("telephone"): continue
        k = S.cle(l)
        if k in listees or k in dans_listes or k in exclues or not metier_actif(l["metier"]) or ZN.cp_hors_zone(l.get("cp", "")): continue
        pool.setdefault(R.cle_metier(l["metier"]) or l["metier"], []).append(l)
    prox = lambda l: ZN.cle_proximite(l.get("cp", ""), l.get("ville", ""))   # (vague, distance à Rouen) : la vague 1 d'abord
    groupes, neufs = [sorted(v, key=prox) for _, v in sorted(pool.items())], []
    while len(out) + len(neufs) < conf["appels_par_jour"] and any(groupes):
        for g in groupes:
            if g and len(out) + len(neufs) < conf["appels_par_jour"]: neufs.append(g.pop(0))
    rang = lambda l: ORDRE_METIERS.index(R.cle_metier(l["metier"])) if R.cle_metier(l["metier"]) in ORDRE_METIERS else len(ORDRE_METIERS)
    return sorted(out + neufs, key=lambda l: (prox(l), 0, 0) if l in out else (prox(l), 1, rang(l)))   # toujours par proximité de Rouen (vague 1 d'abord) ; à proximité égale : les déjà listées, puis les nouvelles par métier


def texte_liste(choisies, ident, jour):
    c = lambda s: str(s).replace("|", "/").replace("\n", " ")
    app, sui, details = [], [], []
    for i, l in enumerate(choisies, 1):
        cle = R.cle_metier(l["metier"]); lien = lien_exemple(l["metier"])
        constat = l.get("note_besoin", "")
        acc = R.accroche_appel(l, ident, cle, constat); sms = R.sms_appel(l, ident, cle, lien)
        k = S.cle(l).replace("|", "~")
        app.append(f"| {i} <!-- k:{k} --> | {c(l['nom'])} | {c(l['ville'])} | {c(l['telephone'])} | {c(l['metier'])} | {('[page exemple](' + lien + ')') if lien else 'à venir'} |  |  | [ ] | [ ] | [ ] | [ ] |")
        sui.append(f"| {i} | {c(l['nom'])} | {c(phrase_constat(l))} | {c(CRENEAUX.get(cle, '').split(',')[0])} |  |  |  |")
        contexte = f"constat vérifié sur son site : {constat}" if constat else "aucun site indiqué sur OpenStreetMap (vérifié seulement sur cette base : rien n'est affirmé sur son site)"
        details.append(f"### {i}. {c(l['nom'])} — {c(l['ville'])} — {c(l['metier'])}\n- Téléphone : {c(l['telephone'])}\n- Contexte : {contexte}\n- Accroche (2 phrases) : {acc}\n- SMS ({len(sms)} caractères) : `{sms}`\n")
    nb = (len(choisies) + 24) // 25; corps = []
    for b in range(nb):
        a, z = b * 25, min((b + 1) * 25, len(choisies))
        corps += [f"## Bloc {b + 1} sur {nb} (lignes {a + 1} à {z})", "", f"### Appels, bloc {b + 1}", "", ENTETE_LISTE, "|---|---|---|---|---|---|---|---|---|---|---|---|", *app[a:z], "",
                  f"### Suivi, bloc {b + 1}", "", "| # | Nom | Constat | Créneau conseillé | rappel (date, heure) | RDV (date) | note |", "|---|---|---|---|---|---|---|", *sui[a:z], ""]
    cren = ["## Créneaux conseillés et pages exemples", "", "Créneaux indicatifs (heures creuses habituelles du métier), non mesurés.", "", "| Métier | Lignes | Créneau conseillé | Page exemple |", "|---|---|---|---|"]
    for cle in ORDRE_METIERS + sorted({R.cle_metier(l["metier"]) for l in choisies} - set(ORDRE_METIERS)):
        lot = [l for l in choisies if R.cle_metier(l["metier"]) == cle]
        if lot: cren.append(f"| {NOMS_METIERS.get(cle, cle)} | {len(lot)} | {CRENEAUX.get(cle, 'à définir')} | " + (f"[page exemple]({lien_exemple(lot[0]['metier'])})" if lien_exemple(lot[0]['metier']) else "à venir") + " |")
    return (f"# Liste d'appels du {jour} ({len(choisies)} ligne(s), en blocs de 25)\n\nRien n'est envoyé : appelez ou envoyez le SMS à la main. Les quatre cases à cocher : `[x]` pour cocher. **refus** ou **STOP** = exclusion définitive (aucun e-mail, aucun message).\n"
            f"Si vous trouvez une adresse e-mail (vous seul : le programme ne lit ni Google ni Facebook), écrivez-la dans la colonne « e-mail trouvé » : au prochain cycle elle entre dans le lot, avec la même rédaction, la ligne STOP et « ok lot ».\n"
            f"Le tableau « Appels » est lu par le programme (12 colonnes, n'en ajoutez pas) ; le tableau « Suivi » (constat, rappel, RDV, note) est pour vous seul. Pour un refus, cochez la case **refus** du tableau « Appels ».\n"
            f"Les entreprises listées mais jamais appelées reviennent d'abord dans la liste suivante (la plus récente en premier), sans refus ni exclus.\n\n"
            + "\n".join(cren) + "\n\n" + "\n".join(corps) + "\n## Détail : accroche et SMS\n\n" + "\n".join(details) +
            "\nSource des numéros et des noms : © les contributeurs d'OpenStreetMap, licence ODbL 1.0 (https://www.openstreetmap.org/copyright).\n")


def lire_listes():
    """Relit tous les docs\\liste-appels-*.md : [(clé, jour, {email, lien, cases})] pour chaque ligne du tableau."""
    out = []
    for f in sorted(DOCS.glob("liste-appels-*.md")):
        jour = f.stem.removeprefix("liste-appels-")
        for lg in f.read_text(encoding="utf-8").splitlines():
            m = re.search(r"<!-- k:(.+?) -->", lg)
            if not m or not lg.lstrip().startswith("|"): continue
            cel = [x.strip() for x in lg.strip().strip("|").split("|")]
            if len(cel) != 12: print(f"  ! {f.name} : ligne de tableau ignorée (12 colonnes attendues, {len(cel)} lues)"); continue
            coche = lambda s: bool(re.search(r"\[[xX]\]", s))
            out.append((m.group(1).replace("~", "|"), jour, {"email": cel[6], "lien": cel[7], "appele": coche(cel[8]), "repondu": coche(cel[9]), "refus": coche(cel[10]), "stop": coche(cel[11])}))
    return out


def integrer_saisies(a_blanc, conf):
    """À chaque cycle : relit les listes d'appels. refus / STOP -> exclusion définitive ; adresse e-mail valide saisie par Liam -> la ligne entre dans le prochain lot (statut « trouvé »),
    avec la même rédaction (redaction.py), la ligne STOP et « ok lot ». Le lien Facebook / fiche Google est seulement noté, jamais ouvert."""
    etat = etat_lire(); lignes = lire_trouves(); par_cle = {S.cle(l): l for l in lignes}; ap = etat.setdefault("appels", {}); exclus = set(ap.setdefault("exclus", [])); saisies = ap.setdefault("saisies", {})
    cles, mails = exclusions(); envoyes = {v.get("email", "").lower() for v in etat.get("envois", {}).values()}; ajoutes = refus = 0
    for k, jour, v in lire_listes():
        l = par_cle.get(k)
        if v["refus"] or v["stop"]:
            if k not in exclus: exclus.add(k); refus += 1
            if l: l["statut"] = "STOP" if v["stop"] else "refusé"
            continue
        if not l: continue
        lien = v["lien"].strip("<> ")
        if lien.startswith("http") and l.get("fiche_web") != lien: l["fiche_web"] = lien
        a = re.sub(r"^mailto:", "", v["email"].strip("<> ").strip(), flags=re.I).lower()
        if not a or not email_valide(a):
            if a: print(f"  ! adresse non valide ignorée pour {l['nom']} : « {v['email']} »")
            continue
        if k in cles or k in exclus or a in mails or a in envoyes: print(f"  ! {l['nom']} : adresse ignorée (exclusion définitive ou déjà contacté)"); continue
        if any(x is not l and x["email"].lower() == a for x in lignes): print(f"  ! {l['nom']} : adresse déjà utilisée par une autre entreprise, ignorée"); continue
        if saisies.get(k) == a and l.get("statut") not in ("listé",) + STATUTS_TEL: continue
        if l.get("statut") in ("listé", "trouvé") + STATUTS_TEL:
            l.update(email=a, email_type="saisi", email_source=f"saisie à la main par Liam (liste d'appels du {jour})", statut="trouvé"); saisies[k] = a; ajoutes += 1
    ap["exclus"] = sorted(exclus)
    print(f"  saisies de Liam : {ajoutes} adresse(s) entrée(s) dans le prochain lot, {refus} exclusion(s) définitive(s)")
    if not a_blanc and (ajoutes or refus or any(l.get("fiche_web") for l in lignes)): ecrire_trouves(lignes); etat_ecrire(etat, False)
    return ajoutes


def cmd_appels(a_blanc, conf, jour=None, api=None):
    """Liste du jour : docs\\liste-appels-AAAA-MM-JJ.md (appels_par_jour lignes au plus, tous métiers actifs). Une seule liste par jour ; rien n'est envoyé. Elle est postée sur Discord par cmd_liste_matin.
    Arrêtée le 14/11/2026 (liste_appels_md = false par défaut) : la liste d'appels est le tableur Google « Appels AAAA-MM-JJ » de appels-sid.py ; les anciens .md restent relus (saisies, reprises)."""
    if not conf.get("liste_appels_md"): print("  liste d'appels .md arrêtée : tableur « Appels AAAA-MM-JJ » (appels-sid.py)"); return 0
    if not jour and heure_paris().strftime("%H:%M") < conf["liste_appels_heure"] and __import__("os").environ.get("JARVIS_TEST") != "1": print(f"  liste d'appels : écrite à partir de {conf['liste_appels_heure']}"); return 0
    jour = jour or aujourdhui(); fichier = DOCS / f"liste-appels-{jour}.md"
    if fichier.exists(): print(f"  liste du jour déjà écrite : {fichier}"); return 0
    etat = etat_lire(); lignes = lire_trouves(); ident, _ = R.charger_identite(); exclues = set(etat.get("appels", {}).get("exclus", [])) | exclusions()[0]
    choisies = choisir_appels(lignes, etat, conf, exclues)
    if not choisies: print("  liste d'appels : aucune entreprise sans site avec téléphone disponible aujourd'hui"); return 0
    texte = texte_liste(choisies, ident, jour)
    print(f"  liste d'appels du {jour} : {len(choisies)} ligne(s) -> {fichier}" + (" [à blanc : rien écrit]" if a_blanc else ""))
    if a_blanc: return len(choisies)
    DOCS.mkdir(exist_ok=True); fichier.write_text(texte, encoding="utf-8")
    cles = {S.cle(l) for l in choisies}; etat["appels"]["listees"] = sorted(set(etat["appels"]["listees"]) | cles)
    for l in lignes:
        if S.cle(l) in cles: l["statut"] = "listé"
    ecrire_trouves(lignes); etat_ecrire(etat, False)
    return len(choisies)


# --- liste d'appels de 8 h : 100 numéros jamais appelés, postée UNE fois par jour dans « appels-du-jour » (décision de Liam, 2 nov. 2026) ---------------------------------
# Aucune tâche planifiée : c'est la boucle (cmd_continu) qui s'en charge au premier cycle après liste_appels_heure. Rien n'est envoyé aux entreprises.
ORDRE_METIERS = ["restaurant", "coiffeur", "boulangerie", "garage", "fleuriste", "plombier", "electricien"]
NOMS_METIERS = {"restaurant": "Restaurants", "coiffeur": "Coiffeurs", "boulangerie": "Boulangeries", "garage": "Garages", "fleuriste": "Fleuristes", "plombier": "Plombiers", "electricien": "Électriciens"}
CRENEAUX = {"restaurant": "14 h 30 – 17 h, mardi au jeudi (entre deux services)", "coiffeur": "mardi au jeudi, 9 h – 10 h ou 13 h 30 – 14 h 30 (pas le samedi)", "boulangerie": "13 h 30 – 15 h 30, après le coup de feu de midi",
            "garage": "13 h 30 – 14 h 30, après la pause déjeuner", "fleuriste": "14 h – 16 h, mardi au jeudi (pas le vendredi ni la veille d'une fête)", "plombier": "12 h – 13 h 30 ou 17 h 30 – 19 h, hors chantier", "electricien": "12 h – 13 h 30 ou 17 h 30 – 19 h, hors chantier"}
JOURS_FR = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS_FR = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]


def a_reprendre(exclues):
    """(clés listées mais jamais appelées, clés listées un jour) d'après docs\\liste-appels-*.md. « Appelé » = case appelé ou répondu cochée dans n'importe quelle liste ; refus / STOP = jamais repris. La liste la plus récente d'abord."""
    vus = {}
    for k, jour, v in lire_listes():
        d = vus.setdefault(k, {"appele": False, "stop": False, "jour": jour})
        d["appele"] |= v["appele"] or v["repondu"]; d["stop"] |= v["refus"] or v["stop"]; d["jour"] = jour
    return [k for k, d in sorted(vus.items(), key=lambda x: x[1]["jour"], reverse=True) if not d["appele"] and not d["stop"] and k not in exclues], set(vus)


def phrase_constat(l):
    """Une phrase par entreprise, sans rien affirmer qui n'ait été vérifié."""
    if l.get("note_besoin"): return "Sur son site : " + l["note_besoin"].rstrip(".") + "."
    if l.get("date_statut") is not None:   # ligne du suivi (suivi-prospects.csv)
        return "Déjà dans le suivi, pas encore contacté ; aucun constat vérifié sur son site." if l.get("statut") == "à contacter" else f"Déjà contacté par e-mail le {l.get('date_envoi') or '?'} ; pas encore appelé."
    return "Aucun site indiqué sur OpenStreetMap ; rien n'a été vérifié ailleurs (Google, Facebook)."


def lire_liste_fichier(fichier):
    """Lignes d'une liste d'appels : [{n, nom, ville, tel, metier, lien, constat}] (tableau « Appels » de 12 colonnes + tableau « Suivi » de 7 colonnes)."""
    app, constats = [], {}
    for lg in fichier.read_text(encoding="utf-8").splitlines():
        if not lg.lstrip().startswith("|"): continue
        cel = [x.strip() for x in lg.strip().strip("|").split("|")]
        if "<!-- k:" in lg and len(cel) == 12:
            n = re.match(r"(\d+)", cel[0]); lien = re.search(r"\((https?://[^)]+)\)", cel[5])
            if n: app.append({"n": int(n.group(1)), "nom": cel[1], "ville": cel[2], "tel": cel[3], "metier": cel[4], "lien": lien.group(1) if lien else ""})
        elif len(cel) == 7 and re.fullmatch(r"\d+", cel[0]): constats[int(cel[0])] = cel[2]
    for a in app: a["constat"] = constats.get(a["n"], "")
    return app


def messages_liste(entrees, jour, lien_par_cle=None):
    """[(texte, [descriptions d'embed])] : un message de départ (créneaux conseillés), puis un message par bloc de 25 entreprises, lisible sur téléphone (découpé si Discord l'impose : 6000 caractères d'embeds par message)."""
    def ec(t): return re.sub(r"([*_~|`>\\])", r"\\\1", P.assainir(str(t)).replace(chr(10), " "))
    def cle_de(m): return R.cle_metier(m or "") or ""
    d = date.fromisoformat(jour); quand = f"{JOURS_FR[d.weekday()]} {d.day} {MOIS_FR[d.month - 1]}"
    cles = [c for c in ORDRE_METIERS if any(cle_de(e["metier"]) == c for e in entrees)]
    liens = dict(lien_par_cle or {})
    for e in entrees:
        if e.get("lien"): liens.setdefault(cle_de(e["metier"]), e["lien"])
    tete = [f"📞 **Liste d'appels du {quand} : {len(entrees)} numéros**", f"Rien n'est envoyé : vous appelez, puis vous cochez dans `docs\\liste-appels-{jour}.md`.", "", "**Créneaux conseillés** (indicatifs, non mesurés) :"]
    for c in cles: tete.append(f"• **{NOMS_METIERS[c]}** : {CRENEAUX[c]}" + (f"\n  page exemple : <{liens[c]}>" if liens.get(c) else ""))
    nb = (len(entrees) + 24) // 25; sortie = [(chr(10).join(tete)[:1990], [])]
    for b in range(nb):
        lot = entrees[b * 25:(b + 1) * 25]; titre = f"**Bloc {b + 1} sur {nb}** · lignes {lot[0]['n']} à {lot[-1]['n']}"
        morceaux, precedent = [], None
        for e in lot:
            c = cle_de(e["metier"])
            if c != precedent:
                precedent = c; morceaux.append(f"\n__**{NOMS_METIERS.get(c, ec(e['metier']).capitalize())}**__" + (f" · <{liens[c]}>" if liens.get(c) else "") + "\n")
            cons = ec(e.get("constat", ""))
            if len(cons) > 110: cons = cons[:107].rsplit(" ", 1)[0] + "…"
            morceaux.append(f"**{e['n']}. {ec(e['nom'])}** · {ec(e['ville'])}\n📞 {ec(e['tel'])}\n" + (f"_{cons}_\n" if cons else ""))
        msgs, emb, cur, tot = [], [], "", 0
        for m_ in morceaux:
            if len(cur) + len(m_) > 3500: emb.append(cur); tot += len(cur); cur = ""
            if tot + len(cur) + len(m_) > 5600: emb.append(cur); msgs.append(emb); emb, cur, tot = [], "", 0
            cur += m_
        emb.append(cur); msgs.append(emb)
        for i, e_ in enumerate(msgs): sortie.append((titre + ("" if i == 0 else " (suite)"), [x for x in e_ if x.strip()]))
    return sortie


def poster_liste(fichier, jour, api):
    """Poste la liste dans le salon « appels-du-jour » (salon_appels_id) : message de départ + un message par bloc. Aucun message n'est envoyé à une entreprise. -> True si tout est posté."""
    acces = acces_discord("salon_appels_id", "appels-du-jour", api)
    if not acces: return False
    jeton, salon, uid = acces; ok = True
    for texte, emb in messages_liste(lire_liste_fichier(fichier), jour):
        r = api(jeton, "POST", f"/channels/{salon}/messages", {"content": texte, **({"embeds": [{"description": e, "color": 0x2B5E9E} for e in emb]} if emb else {}), "allowed_mentions": {"parse": []}})
        ok = ok and bool(r and "id" in r)
        if not (r and "id" in r): print("  ! un message de la liste d'appels n'a pas pu être posté")
        time.sleep(0 if __import__("os").environ.get("JARVIS_TEST") == "1" else 1.2)
    return ok


def cmd_liste_matin(conf, api=None, force=False, paris=None):
    """À partir de liste_appels_heure (08:00, heure de Paris) : écrit la liste du jour (appels_par_jour numéros, la liste non appelée la plus récente d'abord) puis la poste UNE fois (état : appels.postee). -> 1 si postée. Arrêtée avec liste_appels_md = false (14/11/2026)."""
    if not conf.get("liste_appels_md"): return 0
    etat = etat_lire(); jour = aujourdhui()
    if etat.get("appels", {}).get("postee") == jour and not force: return 0
    if not force and (paris or heure_paris()).strftime("%H:%M") < conf["liste_appels_heure"]: return 0
    if not api and __import__("os").environ.get("JARVIS_TEST") == "1": return 0
    integrer_saisies(False, conf)   # refus / STOP cochés hier : relus avant de choisir
    fichier = DOCS / f"liste-appels-{jour}.md"
    if not fichier.exists(): cmd_appels(False, conf, jour=jour)
    if not fichier.exists() or not poster_liste(fichier, jour, api or discord): print("  liste d'appels : non postée sur Discord (nouvel essai au prochain cycle)"); return 0
    etat = etat_lire(); etat.setdefault("appels", {})["postee"] = jour; etat_ecrire(etat, False); print(f"  liste d'appels du {jour} postée dans « appels-du-jour »"); return 1


# --- vagues de départements (décision de Liam, 02/11/2026) : la vague suivante ne s'ouvre que si la vague en cours a moins de seuil_vague prospects utilisables par jour -------------
STATUTS_ECARTES = ("hors zone", "refusé", "STOP", "exclu", "écarté")


def vagues_etat(etat):
    return etat.setdefault("vagues", {"ouverte": 1, "ouvertures": {}})


def appliquer_vagues(etat=None):
    """Fixe les vagues ouvertes de zone.py d'après l'état (prospection-etat.json › vagues › ouverte ; 1 au départ)."""
    ZN.ouvrir(vagues_etat(etat if etat is not None else etat_lire())["ouverte"])


def utilisables_par_vague(lignes, jour=None, cles=(), mails=()):
    """{vague: nombre de prospects utilisables (e-mail ou téléphone, métier avec page exemple, ni exclu ni refusé)} ; jour : seulement ceux collectés ce jour-là. Les fiches sans code postal reconnu ne sont dans aucune vague."""
    out = {n: 0 for n in range(1, 5)}
    for l in lignes:
        if jour and l.get("date_collecte") != jour: continue
        if l.get("statut") in STATUTS_ECARTES or not (l.get("email") or l.get("telephone")): continue
        if S.cle(l) in cles or (l.get("email") or "").lower() in mails or not metier_actif(l.get("metier", "")): continue
        n = ZN.cle_proximite(l.get("cp", ""), l.get("ville", ""))[0]
        if n in out: out[n] += 1
    return out


def vague_suivante_si_besoin(conf, jour=None, epuisee=True):
    """Ouvre la vague suivante si la vague en cours (la dernière ouverte) a moins de seuil_vague prospects utilisables trouvés aujourd'hui ET que la recherche n'y trouve plus de nouveau prospect (epuisee). -> n° de la vague ouverte, sinon 0."""
    etat = etat_lire(); v = vagues_etat(etat); jour = jour or aujourdhui(); n = v["ouverte"]
    if n >= 4 or not epuisee: return 0
    cles, mails = exclusions(); nb = utilisables_par_vague(lire_trouves(), jour, cles, mails)[n]
    if nb >= conf["seuil_vague"]: return 0
    v["ouverte"] = n + 1; v["ouvertures"][str(n + 1)] = {"jour": jour, "utilisables_vague_precedente": nb}; etat_ecrire(etat, False); ZN.ouvrir(n + 1)
    print(f"  vague {n} : {nb} prospect(s) utilisable(s) aujourd'hui (moins de {conf['seuil_vague']}) et plus rien de nouveau -> vague {n + 1} ouverte ({', '.join(ZN.depts_vague(n + 1)[:12])}{'…' if len(ZN.depts_vague(n + 1)) > 12 else ''})")
    return n + 1


def cmd_vagues(conf):
    """Récapitulatif : départements de chaque vague, ouverte ou fermée, prospects utilisables (au total et collectés aujourd'hui). Lecture seule."""
    etat = etat_lire(); v = vagues_etat(etat); cles, mails = exclusions(); lignes = lire_trouves(); jour = aujourdhui()
    tot, auj = utilisables_par_vague(lignes, None, cles, mails), utilisables_par_vague(lignes, jour, cles, mails)
    reste = utilisables_par_vague([l for l in lignes if l.get("statut") in ("trouvé",) + STATUTS_TEL], None, cles, mails)   # pas encore préparés ni contactés
    for n in range(1, 5):
        ds = ZN.depts_vague(n)
        print(f"Vague {n} ({'ouverte' if n <= v['ouverte'] else 'fermée'}) : " + (", ".join(ds) if n < 4 else f"reste de la France métropolitaine ({len(ds)} départements, du plus proche au plus lointain de Rouen)") + f" | utilisables : {tot[n]} au total dont {reste[n]} pas encore utilisés, {auj[n]} collectés aujourd'hui")
    sans = sum(1 for l in lignes if l.get("statut") not in STATUTS_ECARTES and (l.get("email") or l.get("telephone")) and ZN.cle_proximite(l.get("cp", ""), l.get("ville", ""))[0] == 9)
    print(f"Sans code postal reconnu (dans aucune vague) : {sans} | seuil d'ouverture de la vague suivante : {conf['seuil_vague']} utilisables par jour | vagues ouvertes : 1 à {v['ouverte']}")
    return {"ouverte": v["ouverte"], "utilisables_total": tot, "utilisables_aujourdhui": auj, "pas_encore_utilises": reste, "sans_cp": sans}


# --- zone de Liam : nettoyage de tout ce qui a été trouvé hors de la Normandie autour de Rouen (zone.py) -----------------------------------------------------
VILLES_ZONE_SANS_CP = {"eslettes", "bois-d-ennebourg", "saint-martin-du-manoir", "sainte-marie-des-champs"}   # communes normandes de fiches anciennes sans code postal


def hors_zone_ligne(l, villes_ok):
    return not ZN.dans_zone(cp=l.get("cp", ""), ville=l.get("ville", ""), villes_ok=villes_ok, vague_max=4)   # vagues fermées : gardées (elles s'ouvriront)


def cmd_zone(a_blanc, conf):
    """Retire de la liste des prospects, du suivi (jamais contactés seulement) et des blocs « à valider » tout ce qui est hors zone ; marque leur ligne « hors zone » (ils ne reviennent jamais),
    rend leur place au lot du jour, vide les réserves de découverte. Un prospect hors zone DÉJÀ contacté n'est jamais effacé : il est seulement signalé. -> dict de comptes."""
    etat = etat_lire(); lignes = lire_trouves(); texte = MESSAGES.read_text(encoding="utf-8") if MESSAGES.exists() else ""
    ok_v = {ZN.norm(l["ville"]) for l in lignes if l.get("cp") and not ZN.cp_hors_zone(l["cp"], 4)} | VILLES_ZONE_SANS_CP
    hors = {S.cle(l): l for l in lignes if hors_zone_ligne(l, ok_v)}
    r = {"trouves_hors_zone": len(hors), "suivi_retires": 0, "suivi_deja_contactes": [], "blocs_retires": {}, "blocs_deja_envoyes": [], "villes": sorted({l["ville"] + " " + l.get("cp", "") for l in hors.values()})}
    # 1) blocs « à valider » hors zone
    for b in lire_blocs(texte):
        if b["id"] not in hors: continue
        box = (b["meta"] or {}).get("box", "") or "(sans boîte : réseau ou formulaire)"
        if b["statut"] == "à valider":
            r["blocs_retires"][box] = r["blocs_retires"].get(box, 0) + 1
            if not a_blanc: texte = texte.replace(b["texte"], "")
            if (b["meta"] or {}).get("lot") == aujourdhui() and (b["meta"] or {}).get("box"): etat["lots"].setdefault(aujourdhui(), {})[b["meta"]["box"]] = max(0, etat["lots"].get(aujourdhui(), {}).get(b["meta"]["box"], 0) - 1)
        else: r["blocs_deja_envoyes"].append(f"{(b['meta'] or {}).get('nom', b['id'])} ({b['statut']})")
    # 2) suivi : retirer les « à contacter » hors zone, signaler les autres
    suivi = S.lire(); gardes = []
    for x in suivi:
        if S.cle(x) in hors and x["statut"] == "à contacter" and not x.get("date_envoi"): r["suivi_retires"] += 1
        else:
            if S.cle(x) in hors: r["suivi_deja_contactes"].append(f"{x['nom']} ({x['ville']}) : {x['statut']}")
            gardes.append(x)
    # 3) lignes trouvées, mémoire des « déjà vus », réserves de découverte, SMS stockés
    for l in hors.values():
        if not a_blanc:
            l["statut"] = "hors zone"
            if l.get("siren"): etat["vus"][l["siren"]] = "hors zone"
            if l.get("osm"): etat["vus"]["osm:" + l["osm"]] = "hors zone"
            for m in etat.get("sans_site_telephone", {}).values(): m.pop(S.cle(l).replace("|", "~"), None)
    if not a_blanc:
        osm = etat.get("osm", {}); osm["tampon"] = [c for c in osm.get("tampon", []) if ZN.dans_zone(cp=c.get("cp", ""), ville=c.get("ville", ""), villes_ok=ok_v, vague_max=4)]
        for naf, tamp in list(etat.get("tampon", {}).items()): etat["tampon"][naf] = [x for x in tamp if ZN.dans_zone(cp=x.get("cp", ""), vague_max=4)]
        MESSAGES.write_text(re.sub(r"\n{3,}", "\n\n", texte), encoding="utf-8"); S.ecrire(gardes); ecrire_trouves(lignes); etat_ecrire(etat, False)
    return r


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Agent Prospection (jamais d'envoi sans bloc « validé »).")
    ap.add_argument("cmd", choices=["jour", "chercher", "preparer", "relances", "publier", "approuver", "envoyer", "ecouter", "demarrage", "reponses", "continu", "arreter", "zone", "vagues", "rapport", "decouvrir", "places", "appels", "montee"]); ap.add_argument("--a-blanc", action="store_true"); ap.add_argument("--pid", type=int, default=0)
    ap.add_argument("--reprendre", action="store_true")
    a = ap.parse_args(); M.exiger("prospection", a.cmd, a.a_blanc); conf = cfg(); appliquer_vagues()   # vagues ouvertes (zone.py) d'après l'état
    if a.cmd in ("jour", "preparer", "publier", "approuver", "envoyer", "ecouter", "demarrage", "continu"): conf = avec_montee(conf, a.a_blanc)   # palier du jour (10, 20, 30… jusqu'au plafond)
    if a.cmd == "montee": cmd_montee(a.a_blanc, conf, a.reprendre)
    elif a.cmd == "demarrage": cmd_demarrage(a.a_blanc, conf)
    elif a.cmd == "continu": cmd_continu(a.a_blanc, conf, vivant=(lambda: processus_vivant(a.pid)) if a.pid else None)
    elif a.cmd == "arreter": cmd_arreter()
    elif a.cmd == "vagues": cmd_vagues(conf)
    elif a.cmd == "zone": print(json.dumps(cmd_zone(a.a_blanc, conf), ensure_ascii=False, indent=1))
    elif a.cmd == "rapport": cmd_rapport(conf)
    elif a.cmd == "decouvrir": cmd_decouvrir(a.a_blanc, conf); integrer_saisies(a.a_blanc, conf); cmd_appels(a.a_blanc, conf)
    elif a.cmd == "places": cmd_places(a.a_blanc, conf); integrer_saisies(a.a_blanc, conf); cmd_appels(a.a_blanc, conf)
    elif a.cmd == "appels": integrer_saisies(a.a_blanc, conf); cmd_appels(a.a_blanc, conf); (not a.a_blanc) and cmd_liste_matin(conf, force=True)
    elif a.cmd == "ecouter": cmd_ecouter(a.a_blanc, conf)
    elif a.cmd == "jour": cmd_jour(a.a_blanc, conf); cmd_approuver(a.a_blanc, conf); cmd_envoyer(a.a_blanc, conf)      # un seul passage, sans écoute prolongée
    elif a.cmd == "reponses": cmd_reponses(a.a_blanc)
    elif a.cmd == "chercher": cmd_chercher(a.a_blanc, conf)
    elif a.cmd == "preparer": cmd_preparer(a.a_blanc, conf)
    elif a.cmd == "relances": cmd_relances(a.a_blanc, conf)
    elif a.cmd == "publier": cmd_publier(a.a_blanc, conf)
    elif a.cmd == "approuver": cmd_approuver(a.a_blanc, conf)
    elif a.cmd == "envoyer": cmd_approuver(a.a_blanc, conf); cmd_envoyer(a.a_blanc, conf)


if __name__ == "__main__":
    main()
