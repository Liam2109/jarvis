#!/usr/bin/env python3
"""Agent linkedin (23/11/2026), pôle Prospection : chaque jour ouvré à 07:45, poste sur Discord (salon B2B habituel) 1 à 2 posts LinkedIn pour le profil de Liam,
en texte brut prêt à copier, avec ✅ pour valider, ❌ pour rejeter et 📌 pour « publié ». Seul Liam valide ; il colle lui-même le texte sur LinkedIn.
L'agent ne publie JAMAIS sur LinkedIn (aucune API, aucune automatisation du site) et n'appelle aucune IA ni aucun service payant : les posts sont écrits par Claude dans le chat,
par lots d'environ 14, que Liam colle dans B2B\\linkedin\\lot-AAAA-MM-JJ.md ; l'agent les contrôle (règles de contenu ci-dessous) et les range dans B2B\\linkedin\\file.json.

  python agents\\linkedin.py importer [--essai]            contrôle les lots B2B\\linkedin\\lot-*.md et range les posts valides dans file.json (--essai : n'écrit rien)
  python agents\\linkedin.py jour [--jour AAAA-MM-JJ] [--essai]   le passage de 07:45 (tâche serveur, jours ouvrés) : lit les réactions de Liam, poste les posts du jour, surveille le stock
  python agents\\linkedin.py valider|rejeter|publie ID     même décision que ✅ / ❌ / 📌, à la main (ID = 4 caractères ou plus de l'identifiant)
  python agents\\linkedin.py etat                          file, stock en jours, posts qui attendent une décision

Format d'un lot (un bloc « ## » par post ; ce qui précède le premier « ## » est ignoré) :
  ## Post 1
  type: recrutement            (recrutement | prospect)
  statut: en file              (facultatif ; un lot ne contient que des posts neufs)
  texte:
  Le texte du post, sur plusieurs lignes...
  Écrivez-moi en message privé.

Alternance : un post recrutement (appelants à 15 %, closers à 10 %), puis un post recherche de prospects (site web pour artisans et commerçants locaux). Avec posts_par_jour = 2 :
un de chaque par jour (créneaux conseillés 08:30 et 12:30). Un post proposé et non validé n'est JAMAIS republié : il passe « non validé », signalé une fois. Stock < 3 jours de posts :
code de sortie 5 (trace en erreur, le surveillant la signale) et message « demande un nouveau lot à Claude ».
Règles de contenu (controle) : ni emoji, ni image, hashtags limités, vouvoiement, aucun témoignage, aucun chiffre hors prix de OFFRE-REFERENCE.json et commissions 15 % / 10 %,
aucune promesse de résultat, aucun lien, appel à l'action unique « écrivez-moi en message privé », rien de présentiel, aucune phrase interdite, aucun secret.
envoi_automatique: false (défaut versionné) = SIMULATION : `jour` affiche ce qu'il posterait, n'écrit rien, n'appelle pas Discord. Rien n'engage Liam : il copie, colle et décide."""
import argparse, copy, hashlib, json, re, sys, time, unicodedata
from datetime import date, datetime, timedelta
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import machine as M   # réglages locaux de l'agent et machine active (b2b)

AGENT = "linkedin"
CONFIG, JOURNAL, DOSSIER = ICI / "linkedin-config.json", ICI / "linkedin-journal.log", ICI.parent / "linkedin"
REF = ICI.parent / "docs" / "OFFRE-REFERENCE.json"
FILE = lambda: DOSSIER / "file.json"
TYPES = ("recrutement", "prospect")
LIB = {"en_file": "en file", "propose": "proposé", "pret": "prêt", "rejete": "rejeté", "non_valide": "non validé", "publie": "publié"}
CTA = "ecrivez-moi en message prive"
COMMISSIONS = {"appelant": 15, "closer": 10}   # décision de Liam (appelants 15 %, closers 10 %) ; les prix viennent de OFFRE-REFERENCE.json
SUIVI_JOURS = 7   # réactions relues pendant 7 jours après la proposition
OK, KO, PIN = "%E2%9C%85", "%E2%9D%8C", "%F0%9F%93%8C"   # ✅ ❌ 📌 (encodés pour l'URL Discord)
DEFAUT = {"envoi_automatique": False, "salon_nom": "", "posts_par_jour": 2, "stock_min_jours": 3, "max_hashtags": 3, "max_caracteres": 1500, "min_caracteres": 150,
          "creneaux": ["08:30", "12:30"]}
RAISON = None   # motif de la dernière erreur (trace du harness)


class ErreurAgent(Exception):
    """Problème signalé à Liam (message clair, code de sortie 2) : l'agent s'arrête sans rien écrire de plus."""


# --- règles de contenu -----------------------------------------------------------------------------------------------
def _n(s):
    """Minuscules, sans accents, espaces insécables et apostrophes typographiques normalisés."""
    s = (s or "").replace(" ", " ").replace(" ", " ").replace("’", "'").replace("‑", "-").lower()
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿⬀-⯿⌀-⏿■-◿️‍⃣]")
IMAGE = re.compile(r"!\[|<img|\.(?:png|jpe?g|gif|webp|svg)\b|\[(?:image|photo|visuel)\]|(?:image|photo|visuel) jointe?|piece jointe|carrousel")
TUTOIEMENT = re.compile(r"\b(?:tu|toi|te|ta|tes|tiens?|tienne?s?)\b|\bt'\w|\bton (?:site|entreprise|activite|metier|commerce|equipe|travail|temps)\b")
TEMOIGNAGE = re.compile(r"temoign|\bm'a (?:dit|confie|ecrit|raconte|appele)|\bnous a (?:dit|confie|ecrit|raconte)|\b(?:mes|nos|notre|mon) clients?\b|\bun client (?:m'|nous|a |de |qui)|\bune cliente\b"
                        r"|ils nous font confiance|\bavis (?:client|positif)|\bsatisfaits?\b|\bils (?:m'|nous) ont|\b(?:mes|nos) (?:realisations|references)\b|etude de cas|cas client|avant ?/? ?apres")
CLIENT_EXEMPLE = re.compile(r"\bclients? (?:comme|tels)|\bdeja (?:livre|realise|cree)|\bsites? (?:livres?|realises?|crees?) pour|\bce (?:plombier|electricien|boulanger|coiffeur|garagiste|fleuriste|commercant|artisan)\b")
PROMESSE = re.compile(r"garanti|\bassure[es]?s?\b|\bgagn(?:ez|erez|erons|er|e)\b|revenus? (?:regulier|stable|complementaire|passif|confortable)|liberte financiere|sans effort|facilement|sans risque|a coup sur"
                      r"|resultats? (?:rapides?|immediats?)|plus de (?:clients|ventes|appels|rendez|visibilite|chiffre)|\b(?:doubl|tripl|multipli)\w+|\bexplos\w+|vous allez (?:vendre|gagner|decrocher|attirer|avoir plus)"
                      r"|decroch(?:er|ez) (?:des|plus|de nouveaux) (?:clients|contrats|rendez)|augment\w+ (?:vos|votre|le) (?:ventes|chiffre|clients|visibilite)|rentabil|retour sur investissement")
AUTRE_CTA = re.compile(r"\b(?:appelez|contactez|cliquez|reservez|commentez|likez|partagez|abonnez|suivez|inscrivez|telechargez|visitez|calendly|dm|mp|inbox)\b|prenez (?:rendez-vous|rdv)|envoyez[- ]moi"
                       r"|dans les commentaires|en commentaire|lien en bio|lien ci-d")
COORDONNEES = re.compile(r"https?://|www\.|\b[\w.+-]+@[\w-]+\.\w+|(?:\+33|\b0)\s*[1-9](?:[\s.-]*\d{2}){4}|\b[\w-]+\.(?:fr|com|net|io|eu|app)\b|@")
PRESENTIEL = re.compile(r"passer (?:vous )?voir|sur place|en boutique|en magasin|rencontrer|venir (?:vous )?voir|me deplace|en personne|face a face|autour d'un cafe|porte a porte|demarcher? (?:en|sur)")
CITATION = re.compile(r"«[^»]{40,}»|“[^”]{40,}”")
NOMBRE = re.compile(r"\d+(?:[.,]\d+)?")


def offre():
    return json.loads(REF.read_text(encoding="utf-8"))


def _entier(s):
    try: f = float(s.replace(",", ".")); return int(f) if f == int(f) else None
    except ValueError: return None


def _phrases(n): return [x for x in re.split(r"[.!?\n]+", n) if x.strip()]


def _prix_et_commissions(n, prix):
    """Contrôle chaque nombre du texte : euros = prix de l'offre, % = commission du bon rôle dans la même phrase, tout autre chiffre = non vérifié."""
    pb = []; pack, site, mensuel = prix["pack"], prix["site_complet"], prix["mensuel"]
    for s in (c for ph in _phrases(n) for c in re.split(r"[;,]| et ", ph)):   # chaque proposition séparément : « 15 % pour les appelants, 10 % pour les closers »
        for m in NOMBRE.finditer(s):
            v, suite = _entier(m.group()), s[m.end():m.end() + 12].lstrip()
            if suite.startswith("%"):
                kw = [(abs(k.start() - m.start()), r) for r in COMMISSIONS for k in re.finditer(r, s)]
                if not kw: pb.append(f"pourcentage « {m.group()} % » sans « appelant » ou « closer » dans la même proposition")
                else:
                    role = min(kw)[1]
                    if v != COMMISSIONS[role]: pb.append(f"commission {role} : {COMMISSIONS[role]} % (pas {m.group()} %)")
            elif suite.startswith(("€", "eur")):
                if v not in (pack, site, mensuel): pb.append(f"prix « {m.group()} € » : seuls {pack} €, {site} € et {mensuel} €/mois existent")
                elif v == site and "pack" in s and "site complet" not in s: pb.append(f"{site} € est le prix du site complet, pas du pack")
                elif v == pack and "site complet" in s and "pack" not in s: pb.append(f"{pack} € est le prix du pack, pas du site complet")
                elif v == mensuel and "mois" not in s: pb.append(f"{mensuel} € est un prix par mois (« par mois » manque dans la phrase)")
            else: pb.append(f"chiffre non vérifié « {m.group()} » (seuls les prix et commissions de l'offre sont permis)")
    return pb


def controle(type_, texte, conf):
    """Liste des problèmes d'un post (vide = conforme aux règles de contenu)."""
    pb = []; n = _n(texte); texte = texte or ""
    if type_ not in TYPES: return [f"type « {type_} » inconnu (recrutement ou prospect)"]
    if len(texte) < conf["min_caracteres"]: pb.append(f"texte trop court ({len(texte)} caractères, minimum {conf['min_caracteres']})")
    if len(texte) > conf["max_caracteres"]: pb.append(f"texte trop long ({len(texte)} caractères, maximum {conf['max_caracteres']} pour tenir dans un message Discord)")
    if "`" in texte: pb.append("accent grave interdit (il casserait le bloc à copier sur Discord)")
    if EMOJI.search(texte): pb.append("emoji interdit")
    if IMAGE.search(n): pb.append("image ou pièce jointe interdite")
    if len(re.findall(r"(?<!\w)#\w", texte)) > conf["max_hashtags"]: pb.append(f"plus de {conf['max_hashtags']} hashtags")
    if TUTOIEMENT.search(n): pb.append("tutoiement : le post vouvoie")
    if TEMOIGNAGE.search(n) or CITATION.search(texte): pb.append("témoignage, citation ou « nos clients » : rien d'inventé")
    if CLIENT_EXEMPLE.search(n): pb.append("page exemple ou cas présenté comme un client")
    if PROMESSE.search(n): pb.append("promesse de résultat ou de gain")
    if AUTRE_CTA.search(n): pb.append("autre appel à l'action : un seul est permis (« écrivez-moi en message privé »)")
    if COORDONNEES.search(n): pb.append("lien, e-mail, téléphone ou mention : l'appel à l'action est unique")
    if PRESENTIEL.search(n): pb.append("présentiel : Liam prospecte uniquement par téléphone")
    lignes = [l for l in n.split("\n") if l.strip()]
    if n.count(CTA) != 1 or not lignes or CTA not in lignes[-1]: pb.append("la dernière ligne doit contenir une seule fois « Écrivez-moi en message privé »")
    try: ref = offre(); prix = {"pack": ref["offres"]["pack"]["prix_unique_eur"], "site_complet": ref["offres"]["site_complet"]["prix_unique_eur"], "mensuel": ref["abonnement"]["prix_mensuel_eur"]}
    except (OSError, ValueError, KeyError): return pb + ["OFFRE-REFERENCE.json illisible : prix non contrôlables"]
    pb += _prix_et_commissions(n, prix)
    if type_ == "recrutement" and not any(r in n for r in COMMISSIONS): pb.append("post recrutement : il faut parler des appelants ou des closers")
    if type_ == "prospect":
        if "site" not in n or not ("artisan" in n or "commercant" in n): pb.append("post prospect : il faut parler d'un site web pour artisans ou commerçants")
        if re.search(r"recrut|appelant|closer|commission|%", n): pb.append("post prospect : pas de recrutement ni de commission")
    try:   # garde commune du harness : phrases interdites (OFFRE-REFERENCE.json), lien Stripe non autorisé, secrets ; le kill-switch est contrôlé à l'envoi
        sys.path.insert(0, str(ICI.parent / "harness")); import garde as G
        pb += [r.split(" : ", 1)[1] for r in G.verifier_envoi(AGENT, "discord", texte, ctx={"stop": False, "deja_envoyes": 0}, tracer=False)[1] if r.startswith("BLOQUE")]
    except Exception as ex: pb.append(f"garde du harness indisponible ({type(ex).__name__}) : post non contrôlé")
    return pb


# --- lots -> file ---------------------------------------------------------------------------------------------------
def id_post(texte): return hashlib.sha1(re.sub(r"\s+", " ", _n(texte)).strip().encode("utf-8")).hexdigest()[:8]


def lire_lot(texte):
    """-> (posts [{ordre, type, texte}], erreurs [str]) d'un lot collé par Liam. Un bloc mal formé est signalé et ignoré, les autres restent importés."""
    texte = (texte or "").lstrip("﻿").replace("\r\n", "\n").replace("\r", "\n"); posts, erreurs = [], []
    for ordre, bloc in enumerate(re.split(r"(?m)^##[ \t]+", texte)[1:], 1):
        champs, lignes, dans_texte, pb = {}, [], False, []
        for l in bloc.partition("\n")[2].split("\n"):
            if dans_texte: lignes.append(l.rstrip()); continue
            if not l.strip(): continue
            m = re.match(r"\s*([A-Za-zÀ-ÿ]+)\s*:\s*(.*)$", l); k = _n(m.group(1)) if m else ""
            if k == "texte": dans_texte = True; lignes += [m.group(2).rstrip()] if m.group(2).strip() else []
            elif k in ("type", "statut"): champs[k] = m.group(2).strip()
            else: pb.append(f"ligne inattendue avant « texte: » ({l.strip()[:30]})")
        t = _n(champs.get("type", "")); s = _n(champs.get("statut", ""))
        if t not in TYPES: pb.append(f"type « {champs.get('type', '')} » absent ou inconnu (recrutement ou prospect)")
        if s not in ("", "en file", "nouveau", "a valider", "neuf"): pb.append(f"statut « {champs.get('statut')} » : un lot ne contient que des posts neufs (en file)")
        corps = "\n".join(lignes).strip()
        if not corps: pb.append("texte absent")
        if pb: erreurs.append(f"post {ordre} : " + " ; ".join(pb))
        else: posts.append({"ordre": ordre, "type": t, "texte": corps})
    if not posts and not erreurs: erreurs.append("aucun bloc « ## » trouvé dans le lot")
    return posts, erreurs


def importer(etat, conf, dossier=None):
    """Range dans `etat` les posts conformes de chaque lot-*.md (idempotent : un texte déjà connu n'est jamais ajouté deux fois). -> {lots: {nom: {importes, deja, refuses[]}}, importes}."""
    res = {"lots": {}, "importes": 0}; ids = {p["id"] for p in etat["posts"]}
    for f in sorted((dossier or DOSSIER).glob("lot-*.md")):
        try: posts, erreurs = lire_lot(f.read_text(encoding="utf-8"))
        except (OSError, ValueError): res["lots"][f.name] = {"importes": 0, "deja": 0, "refuses": ["fichier illisible (UTF-8 attendu)"]}; continue
        r = {"importes": 0, "deja": 0, "refuses": list(erreurs)}
        for p in posts:
            i = id_post(p["texte"])
            if i in ids: r["deja"] += 1; continue
            pb = controle(p["type"], p["texte"], conf)
            if pb: r["refuses"].append(f"post {p['ordre']} : " + " ; ".join(pb)); continue
            etat["posts"].append({"id": i, "type": p["type"], "texte": p["texte"], "statut": "en_file", "lot": f.name, "propose_le": None, "message_id": None, "decide_le": None, "publie_le": None})
            ids.add(i); r["importes"] += 1
        etat["lots"][f.name] = {"importes": r["importes"] + r["deja"], "refuses": len(r["refuses"])}; res["lots"][f.name] = r; res["importes"] += r["importes"]
    return res


def rapport_import(res):
    if not res["lots"]: print(f"  aucun lot : déposez le lot collé dans {DOSSIER}\\lot-AAAA-MM-JJ.md")
    for nom, r in res["lots"].items():
        print(f"  {nom} : {r['importes']} post(s) importé(s), {r['deja']} déjà connu(s), {len(r['refuses'])} refusé(s)")
        for x in r["refuses"]: print(f"    refusé : {x}")


# --- file, alternance, stock ----------------------------------------------------------------------------------------
def autre(t): return TYPES[1] if t == TYPES[0] else TYPES[0]


def prochain_post(etat, t, exclus=()):
    return next((p for p in etat["posts"] if p["statut"] == "en_file" and p["type"] == t and p["id"] not in exclus), None)


def jours_de_stock(posts, prochain, par_jour):
    """Combien de jours complets (par_jour posts en alternance) la file couvre encore."""
    r = {t: sum(1 for p in posts if p["statut"] == "en_file" and p["type"] == t) for t in TYPES}; t, jours = prochain, 0
    while True:
        for _ in range(par_jour):
            if r[t] <= 0: return jours
            r[t] -= 1; t = autre(t)
        jours += 1


def message_post(p, i, n, creneau, uid, premier):
    tete = (f"<@{uid}> " if premier else "") + f"**LinkedIn, post {i}/{n}** ({p['type']}) · id `{p['id']}` · à publier vers {creneau}"
    return f"{tete}\nTexte brut à copier-coller :\n```\n{p['texte']}\n```\n✅ valider · ❌ rejeter · 📌 publié (après collage sur LinkedIn). Rien n'est publié par l'agent."


# --- réglages, état, journal ----------------------------------------------------------------------------------------
def cfg():
    c = json.loads(json.dumps(DEFAUT))
    try:
        if CONFIG.exists(): c.update({k: v for k, v in json.loads(CONFIG.read_text(encoding="utf-8-sig")).items() if not k.startswith("_")})
    except (OSError, ValueError): raise ErreurAgent(f"réglages illisibles : {CONFIG.name}")
    try: M.surcharge_locale(CONFIG, c)
    except M.ErreurLocale as e: raise ErreurAgent(str(e))
    c["envoi_automatique"] = c.get("envoi_automatique") is True
    for k in ("posts_par_jour", "stock_min_jours", "max_hashtags", "max_caracteres", "min_caracteres"):
        if not isinstance(c.get(k), int) or isinstance(c.get(k), bool) or c[k] < 0: raise ErreurAgent(f"réglage « {k} » invalide dans {CONFIG.name}")
    if c["posts_par_jour"] not in (1, 2): raise ErreurAgent("posts_par_jour : 1 ou 2")
    if not isinstance(c["creneaux"], list) or not c["creneaux"]: raise ErreurAgent("creneaux : liste d'heures attendue (08:30, 12:30)")
    c["salon_nom"] = str(c.get("salon_nom") or "").strip()
    return c


def etat_lire():
    try: e = json.loads(FILE().read_text(encoding="utf-8")) if FILE().exists() else {}
    except (OSError, ValueError): raise ErreurAgent(f"file illisible ({FILE().name}) : rien n'est écrit ; corrigez ou supprimez le fichier à la main")
    if not isinstance(e, dict) or not isinstance(e.get("posts", []), list): raise ErreurAgent(f"file illisible ({FILE().name}) : rien n'est écrit")
    e.setdefault("posts", []); e.setdefault("lots", {}); e.setdefault("alertes", {}); e.setdefault("jours", {}); e.setdefault("prochain_type", TYPES[0])
    return e


def etat_ecrire(e):
    FILE().parent.mkdir(parents=True, exist_ok=True); tmp = FILE().with_suffix(".tmp")
    tmp.write_text(json.dumps(e, ensure_ascii=False, indent=1), encoding="utf-8"); tmp.replace(FILE())


def journaliser(action, detail=""):
    try:
        with open(JOURNAL, "a", encoding="utf-8") as f: f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} | {action} | {detail}\n")
    except OSError: pass


# --- Discord (doublures dans les tests) -----------------------------------------------------------------------------
def acces_reel(conf):
    """(jeton, salon, uid) du bot Jarvis (secrets lus dans Jarvis\\.env par prospection.py, jamais affichés) ou None. Salon = celui des autres agents B2B, ou `salon_nom` s'il est réglé."""
    import prospection as PR
    return PR.acces_discord("salon_linkedin_id", conf["salon_nom"]) if conf["salon_nom"] else PR.acces_discord()


def api_reel(jeton, methode, chemin, corps=None):
    import prospection as PR
    return PR.discord(jeton, methode, chemin, corps)   # garde du harness (STOP, phrases interdites, secrets) appliquée aux messages


def liu_par_liam(api, a, mid, emoji):
    """Vrai si Liam (et lui seul : ni le bot, ni un autre compte) a réagi ; None si Discord est illisible."""
    jeton, salon, uid = a; r = api(jeton, "GET", f"/channels/{salon}/messages/{mid}/reactions/{emoji}?limit=100")
    return None if r is None else any(str(u.get("id")) == uid for u in (r if isinstance(r, list) else []))


# --- le passage de 07:45 --------------------------------------------------------------------------------------------
def cmd_jour(conf, jour, essai=False, api=None, acces=None, dormir=time.sleep):
    """-> code de sortie : 0 ; 2 erreur (Discord, file illisible) ; 5 stock bas (posts du jour quand même envoyés)."""
    global RAISON; RAISON = None
    try: d = date.fromisoformat(jour)
    except ValueError: raise ErreurAgent(f"jour attendu au format AAAA-MM-JJ (reçu « {jour} »)")
    if d.weekday() >= 5: print(f"{jour} : jour non ouvré, rien à poster."); return 0
    sim = essai or not conf["envoi_automatique"]; etat = etat_lire(); api = api or api_reel; a = None
    jr = (lambda *x: None) if essai else journaliser   # --essai : aucun fichier touché, pas même le journal
    res = importer(etat, conf); rapport_import(res)
    if sim:
        etat = copy.deepcopy(etat); print("[simulation : " + ("--essai" if essai else "envoi_automatique=false") + "] rien n'est écrit, rien n'est posté sur Discord.")
        sauver = lambda: None
    else:
        a = (acces or acces_reel)(conf)
        if not a: RAISON = "accès Discord incomplet (jeton, salon ou utilisateur)"; print("  ! " + RAISON + " : rien posté"); return 2
        sauver = lambda: etat_ecrire(etat); sauver()
    uid = a[2] if a else "UID"

    def dire(cle, texte):
        """Un message court à Liam, une seule fois par motif et par jour (simulation : affiché seulement)."""
        k = f"{jour}|{cle}"
        if etat["alertes"].get(k): return
        etat["alertes"][k] = True; jr("alerte", f"{cle} : {texte}"[:300])
        if sim: print(f"  [message Discord] {texte}")
        else:
            r = api(a[0], "POST", f"/channels/{a[1]}/messages", {"content": f"<@{uid}> **LinkedIn** : {texte}"[:1900], "allowed_mentions": {"users": [uid]}})
            if not (r and "id" in r): print("  ! message Discord non pris : nouvel essai au prochain passage"); etat["alertes"].pop(k, None)
        sauver()

    for nom, r in res["lots"].items():
        if r["refuses"]: dire(f"lot|{nom}|{len(r['refuses'])}", f"lot {nom} : {len(r['refuses'])} post(s) refusé(s) par les règles de contenu (détail : `python agents\\linkedin.py importer --essai`).")
    if not sim:   # 1) décisions de Liam sur les posts déjà proposés (✅ ❌ 📌, lues uniquement s'il les a posées lui-même)
        limite = f"{d - timedelta(days=SUIVI_JOURS)}"; incertains = set()
        for p in etat["posts"]:
            if p["statut"] not in ("propose", "non_valide", "pret") or not p.get("message_id") or (p.get("propose_le") or "") < limite: continue
            ok, ko, pin = (liu_par_liam(api, a, p["message_id"], e) for e in (OK, KO, PIN))
            if None in (ok, ko, pin): incertains.add(p["id"]); continue
            if ko: p["statut"], p["decide_le"] = "rejete", jour; jr("rejeté", f"{p['id']} ({p['type']}) par ❌")
            elif pin: p["statut"], p["decide_le"], p["publie_le"] = "publie", p.get("decide_le") or jour, jour; jr("publié", f"{p['id']} ({p['type']}) le {jour} (📌)")
            elif ok and p["statut"] != "pret": p["statut"], p["decide_le"] = "pret", jour; jr("prêt", f"{p['id']} ({p['type']}) par ✅")
            dormir(0.3)
        sauver()
        if incertains: print(f"  ! réactions illisibles pour {len(incertains)} post(s) : relues au prochain passage, aucun n'est déclaré non validé")
    else: incertains = set()
    # 2) un post proposé un jour précédent et jamais validé ne repart jamais seul : il est signalé une fois (jamais sur une lecture ratée)
    nv = [p for p in etat["posts"] if p["statut"] == "propose" and (p.get("propose_le") or jour) < jour and p["id"] not in incertains]
    for p in nv: p["statut"] = "non_valide"; jr("non validé", f"{p['id']} ({p['type']}) proposé le {p['propose_le']}")
    if nv:
        sauver(); dire(f"non-valides|{'+'.join(p['id'] for p in nv)}", f"{len(nv)} post(s) non validé(s) : " + ", ".join(f"{p['id']} ({p['type']}, proposé le {p['propose_le']})" for p in nv)
                       + ". Ils ne repartent pas seuls : ✅ ou ❌ sur leur message, ou `python agents\\linkedin.py valider|rejeter ID`.")
    # 3) les posts du jour, en alternance (un post de chaque type par jour avec posts_par_jour = 2)
    deja = [p for p in etat["posts"] if p.get("propose_le") == jour]; code = 0; faits = []
    i = len(deja)
    while i < conf["posts_par_jour"]:
        t = etat["prochain_type"]; p = prochain_post(etat, t)
        if p is None: print(f"  ! plus aucun post « {t} » en file : alternance stricte, rien posté pour ce créneau"); break
        pb = controle(p["type"], p["texte"], conf)   # le texte a pu être modifié à la main dans file.json depuis l'import
        msg = message_post(p, i + 1, conf["posts_par_jour"], conf["creneaux"][i % len(conf["creneaux"])], uid, i == 0)
        if pb or len(msg) > 1990:   # écarté (jamais envoyé), le créneau est repris par le post suivant du même type
            p["statut"], p["decide_le"] = "rejete", jour; jr("rejeté", f"{p['id']} : règles de contenu non respectées à l'envoi"); sauver(); dire(f"refus|{p['id']}", f"post {p['id']} écarté : " + ("; ".join(pb) or "trop long pour Discord")); continue
        if sim: print(f"\n--- message qui serait posté ({t}) ---\n{msg}\n---"); mid = None
        else:
            r = api(a[0], "POST", f"/channels/{a[1]}/messages", {"content": msg, "allowed_mentions": {"users": [uid]} if i == 0 else {"parse": []}})
            if not (r and "id" in r): RAISON = "Discord n'a pas pris le message du post"; print("  ! " + RAISON + " : repris au prochain passage"); code = 2; break
            mid = str(r["id"])
            for e in (OK, KO, PIN): api(a[0], "PUT", f"/channels/{a[1]}/messages/{mid}/reactions/{e}/@me"); dormir(0.4)   # boutons ✅ ❌ 📌 prêts à cliquer
        p["statut"], p["propose_le"], p["message_id"] = "propose", jour, mid; etat["prochain_type"] = autre(t); faits.append(p)
        etat["jours"].setdefault(jour, []).append(p["id"]); jr("proposé" if not sim else "simulation", f"{p['id']} ({t}) le {jour}"); sauver(); i += 1
    # 4) stock : moins de stock_min_jours jours de posts = erreur (le surveillant la signale) + demande de lot
    reste = jours_de_stock(etat["posts"], etat["prochain_type"], conf["posts_par_jour"])
    print(f"{jour} : {len(deja) + len(faits)} post(s) proposé(s) au total aujourd'hui ; stock : {reste} jour(s) de posts.")
    if reste < conf["stock_min_jours"]:
        RAISON = f"stock bas : {reste} jour(s) de posts (minimum {conf['stock_min_jours']}), demander un nouveau lot à Claude"
        dire("stock", f"il reste {reste} jour(s) de posts : demande un nouveau lot à Claude (environ 14 posts), colle-le dans B2B\\linkedin\\lot-{jour}.md puis `python agents\\linkedin.py importer`.")
        code = code or 5
    return code


# --- décisions à la main, état ---------------------------------------------------------------------------------------
def trouver(etat, ident):
    ident = (ident or "").strip().lower(); tous = [p for p in etat["posts"] if len(ident) >= 4 and p["id"].startswith(ident)]
    if len(tous) != 1: raise ErreurAgent(f"identifiant « {ident} » : " + ("introuvable" if not tous else "ambigu") + " (voir `python agents\\linkedin.py etat`)")
    return tous[0]


def cmd_decision(action, ident, jour):
    etat = etat_lire(); p = trouver(etat, ident)
    if action == "valider" and p["statut"] in ("en_file", "propose", "non_valide"): p["statut"], p["decide_le"] = "pret", jour
    elif action == "rejeter" and p["statut"] not in ("publie", "rejete"): p["statut"], p["decide_le"] = "rejete", jour
    elif action == "publie" and p["statut"] in ("en_file", "propose", "non_valide", "pret"): p["statut"], p["decide_le"], p["publie_le"] = "publie", p.get("decide_le") or jour, jour
    else: raise ErreurAgent(f"post {p['id']} : « {action} » impossible depuis le statut « {LIB[p['statut']]} »")
    etat_ecrire(etat); journaliser({"valider": "prêt", "rejeter": "rejeté", "publie": "publié"}[action], f"{p['id']} ({p['type']}) le {jour} (à la main)")
    print(f"post {p['id']} ({p['type']}) : {LIB[p['statut']]} le {jour}."); return 0


def cmd_etat(conf):
    e = etat_lire(); n = {s: sum(1 for p in e["posts"] if p["statut"] == s) for s in LIB}
    print(f"Envoi automatique : {'oui' if conf['envoi_automatique'] else 'non (simulation)'} ; {conf['posts_par_jour']} post(s) par jour ; prochain type : {e['prochain_type']}.")
    print("File : " + ", ".join(f"{n[s]} {LIB[s]}" for s in LIB) + f" ; stock : {jours_de_stock(e['posts'], e['prochain_type'], conf['posts_par_jour'])} jour(s) (minimum {conf['stock_min_jours']}).")
    for p in e["posts"]:
        if p["statut"] in ("propose", "non_valide", "pret"): print(f"  {p['id']} · {p['type']} · {LIB[p['statut']]} (proposé le {p['propose_le']})")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog=AGENT, description="Posts LinkedIn du jour pour Liam : proposés sur Discord, validés et collés par Liam. Ne publie jamais.")
    sp = p.add_subparsers(dest="cmd", required=True)
    i = sp.add_parser("importer"); i.add_argument("--essai", "--a-blanc", dest="essai", action="store_true", help="contrôle les lots sans rien écrire")
    j = sp.add_parser("jour"); j.add_argument("--jour", default=None); j.add_argument("--essai", "--a-blanc", dest="essai", action="store_true", help="n'écrit rien et ne parle pas à Discord")
    for c in ("valider", "rejeter", "publie"): sp.add_parser(c).add_argument("id")
    sp.add_parser("etat")
    args = p.parse_args(argv); M.exiger(AGENT, args.cmd, getattr(args, "essai", False))
    try:
        conf = cfg()
        if args.cmd == "etat": return cmd_etat(conf)
        import prospection as P
        jour = getattr(args, "jour", None) or P.heure_paris().date().isoformat()
        if args.cmd == "importer":
            e = etat_lire(); res = importer(e, conf); rapport_import(res)
            if not args.essai: etat_ecrire(e); journaliser("importer", f"{res['importes']} post(s) importé(s)")
            return 0
        if args.cmd == "jour": return cmd_jour(conf, jour, args.essai)
        return cmd_decision(args.cmd, args.id, jour)
    except ErreurAgent as e:
        print(f"  ! {e}"); return 2
    except OSError as e:
        print(f"  ! erreur de fichier : {e.strerror or type(e).__name__}"); return 2


if __name__ == "__main__":
    _t0 = time.time(); _code = main()
    if sys.argv[1:2] == ["jour"] and not {"--essai", "--a-blanc"} & set(sys.argv):   # trace du harness (B2B\logs\agents\linkedin), jamais bloquante
        try:
            sys.path.insert(0, str(ICI.parent / "harness")); import traces
            traces.ecrire(AGENT, "jour", "terminé" if _code == 0 else "échec", time.time() - _t0, ok=_code == 0, erreur=None if _code == 0 else (RAISON or f"code {_code}"))
        except Exception: pass
    sys.exit(_code)
