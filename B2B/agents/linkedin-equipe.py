#!/usr/bin/env python3
"""Équipe LinkedIn (24/11/2026) : des agents PRÉPARENT, Liam ENVOIE. Aucun envoi, aucune API LinkedIn, aucun scraping de LinkedIn (risque de blocage du profil).
Chaque jour ouvré à 08:00, le « lot du jour » est écrit pour la rubrique LinkedIn du tableau de bord (dashboard\\data\\linkedin.js, hors git), jamais sur Discord :
  1. 1 post prêt à coller, pris dans la file de l'agent linkedin (skill linkedin-posts) SANS l'activer : file.json n'est jamais modifié ici ;
  2. ~10 commentaires rédigés + lien du post à commenter (recherche web publique par moteur de recherche, jamais LinkedIn lui-même) ;
  3. 20 demandes de connexion par jour ouvré, SANS note (réglage demandes_par_jour), plafond strict de 100 par semaine (plafond_semaine) : 70 % entreprises (décideurs
     de 1 à 10 personnes, bâtiment d'abord, zone Rouen / Seine-Maritime puis élargissement progressif) et 30 % appelants / closers ; pour chaque cible : nom ou entreprise,
     lien de recherche LinkedIn cliquable et DM court prêt pour le jour où elle accepte ;
  4. suivi : Liam coche « demande envoyée », « acceptée » (le DM sort alors dans « DM du jour »), « DM envoyé », « a répondu ». Une relance courte (une seule par personne) est
     préparée 3 jours après un DM sans réponse. Une réponse positive entre dans les leads chauds (registre).
Scripts sans token ; le modèle local (Ollama, gratuit) ne sert qu'à rédiger les commentaires, sinon des gabarits.
  python agents\\linkedin-equipe.py jour [--jour AAAA-MM-JJ] [--refaire] [--essai]   génère le lot du jour (une seule fois par jour)
  python agents\\linkedin-equipe.py coche ID ACTION      ACTION : demande_envoyee | accepte | dm_envoye | repondu_positif | repondu_autre | relance_envoyee | ignorer | annuler | commente
  python agents\\linkedin-equipe.py etat | exporter"""
import argparse, csv, hashlib, json, os, re, sys, time, unicodedata, urllib.parse, urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import machine as M
import registre as RG
import linkedin as LI   # règles de contenu (regex) et file des posts de l'agent linkedin (lecture seule ici)

import linkedin_auto as LA   # mode automatique (go_linkedin_auto), fermé par défaut


class _Moi:
    """Donne à linkedin_auto l'accès vivant aux globals de ce module (même chargé sans nom de module)."""
    def __getattr__(self, k):
        try: return globals()[k]
        except KeyError: raise AttributeError(k)


LA.lier(_Moi())
AGENT = "linkedin-equipe"
RACINE = ICI.parent
CONFIG, JOURNAL = ICI / "linkedin-equipe-config.json", ICI / "linkedin-equipe-journal.log"
ETAT = RACINE / "linkedin" / "equipe.json"
SORTIE = RACINE.parent / "dashboard" / "data"
SOURCES = {"rouen": RACINE / "prospects_rouen.csv", "large": RACINE / "prospects.csv", "trouves": RACINE / "prospection-trouves.csv"}
SUIVI = RACINE / "suivi-prospects.csv"
if os.environ.get("JARVIS_TEST") == "1":   # tests : jamais le vrai état ni le vrai tableau de bord
    import tempfile; _t = Path(tempfile.mkdtemp(prefix="linkedin-equipe-test-")); ETAT = _t / "equipe.json"; SORTIE = _t / "data"; JOURNAL = _t / "journal.log"
DEFAUT = {"demandes_par_jour": 20, "plafond_semaine": 100, "part_entreprises": 0.7, "commerces_locaux": False, "commentaires": 10, "relance_jours": 3,
          "go_linkedin_auto": False, "auto_commentaires_par_jour": 3, "auto_dm_max_jour": 25, "auto_debut": "08:00", "auto_fin": "18:00", "auto_ecart_minutes": 7, "auto_profil": "", "auto_navigateur": "msedge",
          "zones": [["76"], ["27", "14", "50", "61"]], "zone_niveau": 1, "effectif_max": 9,
          "intitules_closers": ["closer", "téléconseiller", "téléprospecteur", "conseiller commercial sédentaire", "commercial indépendant", "agent commercial", "apporteur d'affaires"],
          "zones_closers": ["Rouen", "Seine-Maritime", "Normandie", "France"],
          "recherches_commentaires": ["artisan bâtiment site internet", "artisan plombier électricien visibilité en ligne", "créer son entreprise artisan Normandie", "petite entreprise site web artisans",
                                      "commerçant local site internet", "artisan Rouen entreprise", "gérant artisan TPE site web"],
          "ollama": {"url": "http://127.0.0.1:11434", "modele": "qwen2.5:7b", "delai_secondes": 60}}
BATIMENT = ("electricien", "plombier chauffagiste", "peintre", "menuisier", "macon", "couvreur", "platrier", "paysagiste", "couvreur zingueur", "carreleur", "chauffagiste")
SOCIETE = re.compile(r"\b(sarl|sas|sasu|eurl|sci|sa|snc|selarl|holding|groupe|ste|societe|entreprise|ets|etablissements?|batiment|renovation|services?|construction|plomberie|electricite|peinture|menuiserie|"
                     r"maconnerie|couverture|platrerie|chauffage|travaux|artisan|artisans|habitat|isolation|fermetures?|decoration|thermique|multi|express|pro|concept|energie|energies|bat|agencement|agencements|installation|installations|fibre|fast|depannage|bois|metal|sol|sols|toiture|toitures|deco|confort|eco|home|design|plus|tech|technique)\b")
ACTIONS = ("demande_envoyee", "accepte", "dm_envoye", "repondu_positif", "repondu_autre", "relance_envoyee", "repondu_negatif", "ignorer", "annuler", "commente")
ETAPES = ("repondu_le", "relance_envoyee_le", "dm_envoye_le", "accepte_le", "demande_envoyee_le")   # de la plus avancée à la première (annuler retire la plus avancée)
RAISON = None


class ErreurAgent(Exception):
    """Problème signalé à Liam (code de sortie 2)."""


def n(s): return RG.norm(s)


# --- réglages, état, journal ----------------------------------------------------------------------------------------------
def cfg():
    c = json.loads(json.dumps(DEFAUT))
    try:
        if CONFIG.exists(): c.update({k: v for k, v in json.loads(CONFIG.read_text(encoding="utf-8-sig")).items() if not k.startswith("_")})
    except (OSError, ValueError): raise ErreurAgent(f"réglages illisibles : {CONFIG.name}")
    for k in ("demandes_par_jour", "plafond_semaine", "commentaires", "relance_jours", "zone_niveau", "effectif_max", "auto_commentaires_par_jour", "auto_dm_max_jour", "auto_ecart_minutes"):
        if not isinstance(c[k], int) or isinstance(c[k], bool) or c[k] < 0: raise ErreurAgent(f"réglage « {k} » invalide dans {CONFIG.name}")
    if not isinstance(c["part_entreprises"], (int, float)) or not 0 <= c["part_entreprises"] <= 1: raise ErreurAgent("part_entreprises : un nombre entre 0 et 1")
    c["commerces_locaux"] = c.get("commerces_locaux") is True; c["go_linkedin_auto"] = c.get("go_linkedin_auto") is True
    return c


def etat_lire(fichier=None):
    f = Path(fichier or ETAT)
    try: e = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    except (OSError, ValueError): raise ErreurAgent(f"état illisible ({f.name}) : rien n'est écrit ; corrigez ou supprimez le fichier à la main")
    if not isinstance(e, dict): raise ErreurAgent(f"état illisible ({f.name})")
    for k, v in (("cibles", {}), ("jours", {}), ("textes", []), ("posts_utilises", []), ("commentaires_urls", [])): e.setdefault(k, v)
    return e


def etat_ecrire(e, fichier=None):
    f = Path(fichier or ETAT); f.parent.mkdir(parents=True, exist_ok=True); tmp = f.with_name(f.name + ".tmp")
    tmp.write_text(json.dumps(e, ensure_ascii=False, indent=1), encoding="utf-8"); os.replace(tmp, f)


def journaliser(action, detail=""):
    try:
        with open(JOURNAL, "a", encoding="utf-8") as f: f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} | {action} | {detail}\n")
    except OSError: pass


def lien_recherche(mots):
    return "https://www.linkedin.com/search/results/people/?" + urllib.parse.urlencode({"keywords": mots, "origin": "GLOBAL_SEARCH_HEADER"})


# --- règles des messages (DM, relances, commentaires) ---------------------------------------------------------------------
def controle_message(texte, max_car=300, commentaire=False):
    """Problèmes d'un DM, d'une relance ou d'un commentaire (liste vide = conforme)."""
    pb = []; t = texte or ""; x = LI._n(t)
    if len(t) < 30 or len(t) > max_car: pb.append(f"longueur {len(t)} (30 à {max_car})")
    if LI.EMOJI.search(t): pb.append("emoji")
    if LI.TUTOIEMENT.search(x): pb.append("tutoiement")
    if LI.PROMESSE.search(x): pb.append("promesse")
    if LI.COORDONNEES.search(x): pb.append("lien, e-mail ou téléphone")
    if LI.PRESENTIEL.search(x): pb.append("présentiel")
    if LI.TEMOIGNAGE.search(x) or LI.CLIENT_EXEMPLE.search(x): pb.append("témoignage ou client inventé")
    if re.search(r"\d", t): pb.append("chiffre non vérifié")
    if commentaire and re.search(r"\b(?:mon site|je cree|devis|mon offre|contactez|ecrivez-moi|mes services)\b", x): pb.append("commentaire commercial")
    try:
        sys.path.insert(0, str(RACINE / "harness")); import garde as G
        pb += [r.split(" : ", 1)[1] for r in G.verifier_envoi("linkedin", "discord", t, ctx={"stop": False, "deja_envoyes": 0}, tracer=False)[1] if r.startswith("BLOQUE")]
    except Exception as ex: pb.append(f"garde du harness indisponible ({type(ex).__name__})")
    return pb


OUV_E = ["Merci d'avoir accepté ma demande.", "Content d'être en contact avec vous.", "Merci pour l'ajout.", "Je me permets de vous écrire maintenant que nous sommes en contact.",
         "Votre activité de {metier} à {ville} m'a donné envie de vous écrire.", "Bonne idée de s'être connectés, merci.",
         "Ravi de faire partie de votre réseau.", "Merci de m'avoir accepté dans votre réseau.", "Heureux d'être en lien avec vous.", "Votre profil de {metier} m'a interpellé, d'où ma demande de connexion."]
COR_E_BAT = ["Je crée des sites web simples pour les artisans du bâtiment : une page claire avec votre activité et un moyen de vous joindre.",
             "Mon métier : faire des sites web pour les artisans qui n'en ont pas, ou dont le site a vieilli.",
             "Je réalise des sites web pour les professionnels du bâtiment, sans jargon technique.",
             "Je conçois des sites web pour les artisans : une vitrine propre qui présente votre travail et vos coordonnées.",
             "Je fabrique des sites web pour les artisans du bâtiment : clairs, rapides à lire sur un téléphone, avec vos réalisations.",
             "Mon activité : créer le site web des artisans, de la page d'accueil aux coordonnées, sans que vous ayez à vous en occuper.",
             "J'aide les artisans à avoir une présence en ligne propre : un site simple, à leur image.",
             "Je m'occupe de sites web pour les entreprises du bâtiment : textes, photos et mise en page, pendant que vous êtes sur vos chantiers."]
COR_E_COM = ["Je crée des sites web simples pour les commerçants locaux : une page claire avec vos horaires et un moyen de vous joindre.",
             "Mon métier : faire des sites web pour les commerces qui n'en ont pas, ou dont le site a vieilli.",
             "Je réalise des sites web pour les commerçants de proximité, sans jargon technique.",
             "Je fabrique des sites web pour les commerces locaux : clairs, lisibles sur un téléphone, avec vos horaires.",
             "J'aide les commerçants à avoir une présence en ligne propre : un site simple, à leur image."]
FIN_E = ["Avez-vous déjà un site aujourd'hui ?", "Seriez-vous ouvert à un court échange téléphonique pour en discuter ?", "Si le sujet vous parle, je vous explique tout par téléphone, en quelques minutes.",
         "Un site vous manque-t-il, ou est-ce déjà réglé de votre côté ?",
         "Est-ce un sujet pour vous en ce moment ?", "Je peux vous en dire deux mots par téléphone si vous le souhaitez.", "Votre activité est-elle déjà bien présentée en ligne ?",
         "Dites-moi si cela vous parle, sinon aucun souci."]
OUV_C = ["Merci d'avoir accepté ma demande.", "Content d'être en contact avec vous.", "Merci pour l'ajout.", "Je me permets de vous écrire maintenant que nous sommes en contact.",
         "Ravi de faire partie de votre réseau.", "Merci de m'avoir accepté dans votre réseau.", "Heureux d'être en lien avec vous.", "Votre parcours m'a donné envie de vous écrire."]
COR_C = ["Je recrute des appelants et des closers pour vendre des sites web à des artisans et des commerçants locaux, par téléphone, depuis chez soi.",
         "Je monte une petite équipe d'appelants et de closers : on appelle des artisans pour leur proposer un site web, depuis chez soi, avec une rémunération à la commission.",
         "Je cherche des personnes à l'aise au téléphone pour présenter des sites web à des artisans, à distance, avec une rémunération à la commission.",
         "Je constitue une équipe d'appelants et de closers pour une activité de création de sites web destinés aux artisans, à distance, rémunérée à la commission.",
         "Je propose une mission d'appelant ou de closer : présenter des sites web à des artisans par téléphone, à vos horaires, avec une rémunération à la commission.",
         "Je cherche des appelants et des closers à l'aise au téléphone pour une offre de sites web destinée aux commerçants et artisans de proximité."]
FIN_C = ["Est-ce un type de mission qui pourrait vous intéresser ?", "Seriez-vous curieux d'en savoir plus ?", "Je vous détaille le fonctionnement si cela vous parle.",
         "Cela pourrait-il vous intéresser, ou connaissez-vous quelqu'un à qui cela parlerait ?", "Dites-moi si vous voulez en savoir plus, sinon aucun souci."]
REL_E = ["Je me permets une courte relance sur mon message : un site web pour votre activité, présenté par téléphone en quelques minutes. Sans retour de votre part, je ne vous écrirai plus.",
         "Un petit rappel sur mon message de la semaine. Si un site web ne vous intéresse pas, dites-le moi simplement et je n'insisterai pas.",
         "Je reviens une seule fois vers vous au sujet d'un site web pour votre activité. Si ce n'est pas le moment, aucun souci.",
         "Dernier message de ma part : si l'idée d'un site web vous parle, un échange téléphonique suffit. Sinon, merci de votre temps."]
REL_C = ["Je me permets une courte relance sur mon message : la mission d'appelant ou de closer vous intéresse-t-elle ? Sans retour de votre part, je ne vous écrirai plus.",
         "Un petit rappel sur mon message de la semaine. Si la mission ne vous convient pas, dites-le moi simplement et je n'insisterai pas.",
         "Je reviens une seule fois vers vous sur le poste d'appelant ou de closer. Si ce n'est pas le moment, aucun souci."]


def _h(s): return int(hashlib.sha1(s.encode("utf-8")).hexdigest(), 16)


def rediger(liste_ouv, liste_cor, liste_fin, graine, deja, remplir):
    """Un message construit parmi toutes les combinaisons, jamais identique à un texte déjà écrit ; démarre à une position fixée par la graine (pas de motif répété d'une cible à l'autre)."""
    combos = [(o, c, f) for o in liste_ouv for c in liste_cor for f in liste_fin]; d = _h(graine) % len(combos)
    for i in range(len(combos)):
        o, c, f = combos[(d + i) % len(combos)]; t = " ".join(remplir(x) for x in (o, c, f))
        if t not in deja and not controle_message(t, 420): return t
    o, c, f = combos[d]; return " ".join(remplir(x) for x in (o, c, f))   # toutes les combinaisons sont prises : un message se répète plutôt que d'arrêter le lot (ajouter des variantes ci-dessus)


def rediger_prix(liste_ouv, liste_cor, liste_fin, graine, deja, remplir):
    """Comme rediger, pour le DM du mode automatique (le prix y est admis : contrôlé par linkedin_auto.verifier_texte)."""
    combos = [(o, c, f) for o in liste_ouv for c in liste_cor for f in liste_fin]; d = _h(graine) % len(combos)
    for i in range(len(combos)):
        o, c, f = combos[(d + i) % len(combos)]; t = " ".join(remplir(x) for x in (o, c, f))
        if t not in deja and not LA.verifier_texte(t): return t
    o, c, f = combos[d]; return " ".join(remplir(x) for x in (o, c, f))


def dm_pour(c, deja):
    metier = c.get("metier") or "artisan"; ville = c.get("ville") or ""
    rempl = lambda x: x.format(metier=metier, ville=ville or "chez vous")
    if c["type"] == "closer": return rediger(OUV_C, COR_C, FIN_C, c["id"], deja, rempl)
    ouv = [o for o in OUV_E if "{ville}" not in o or ville]
    return rediger(ouv, COR_E_BAT if c.get("bat", True) else COR_E_COM, FIN_E, c["id"], deja, rempl)


def relance_pour(c, deja):
    liste = REL_C if c["type"] == "closer" else REL_E; d = _h("rel" + c["id"]) % len(liste)
    for i in range(len(liste)):
        t = liste[(d + i) % len(liste)]
        if t not in deja and not controle_message(t, 420): return t
    return liste[d]   # une relance peut se répéter une fois toutes les variantes prises (courte et neutre)


# --- cibles : fichiers de prospects et d'entreprises déjà trouvés ---------------------------------------------------------
def _csv(f):
    try:
        with open(f, encoding="utf-8-sig", newline="") as fh: return list(csv.DictReader(fh, delimiter=";"))
    except OSError: return []


def dirigeant(nom):
    """(prénom nom du dirigeant, nom commercial) : « JULIEN RUPALLEY (JR PLOMBERIE) » = entrepreneur individuel connu ; une société garde seulement son nom commercial."""
    base = re.sub(r"\s*\([^)]*\)", "", nom or "").strip(); com = (re.findall(r"\(([^)]*)\)", nom or "") or [""])[-1].strip() or base
    mots = re.findall(r"[A-Za-zÀ-ÿ-]+", base)
    if 2 <= len(mots) <= 4 and all(len(m) >= 3 for m in mots) and not SOCIETE.search(n(base)) and len(base.split()) == len(mots): return " ".join(m.capitalize() for m in mots), (com if com != base else "")
    return "", (base or nom or "").title()


def rang_effectif(code):
    code = (code or "").strip()
    return {"00": 0, "01": 0, "02": 0, "03": 0}.get(code, 1 if code in ("", "NN") else 9)   # 1 à 9 personnes ; NN = non renseigné (gardé) ; 11 et plus = exclu


def metier_bat(m): return n(m) in BATIMENT


def deja_traites():
    """Noms+villes déjà contactés par e-mail ou déjà dans le registre (appels) : jamais redonnés."""
    contactes = {f"{n(l.get('nom'))}|{n(l.get('ville'))}" for l in _csv(SUIVI) if (l.get("date_envoi") or "").strip() or (l.get("statut") or "") not in ("", "à contacter")}
    try: reg = RG.charger()
    except (OSError, ValueError): reg = RG.vide()
    return contactes, RG.index(reg)


def candidats(conf):
    """Entreprises candidates, triées : zone (Seine-Maritime d'abord), dirigeant connu, 1 à 9 personnes, création récente (profils plus actifs). -> liste de dicts."""
    contactes, (nc, tels) = deja_traites(); vus, out = set(), []
    commerces = conf["commerces_locaux"] or conf["go_linkedin_auto"]   # mode automatique : commerces locaux (coiffeurs, restaurants, garages...) inclus
    fichiers = [(SOURCES["rouen"], True), (SOURCES["large"], True)] + ([(SOURCES["trouves"], False)] if True else [])
    for f, siren_f in fichiers:
        for l in _csv(f):
            nom, ville, metier = (l.get("nom") or "").strip(), (l.get("ville") or "").strip(), (l.get("metier") or "").strip()
            bat = metier_bat(metier)
            if not nom or (not bat and not commerces) or (f == SOURCES["trouves"] and not (bat or commerces)): continue
            if f == SOURCES["trouves"] and n(l.get("statut")) in ("exclu", "ecarte", "hors zone"): continue   # écartés / hors zone : jamais ciblés
            if rang_effectif(l.get("effectif")) > 1: continue
            if int(re.sub(r"\D", "", l.get("effectif") or "") or 0) > conf["effectif_max"] and (l.get("effectif") or "") not in ("NN", ""): continue
            cp = (l.get("cp") or "").strip(); dept = cp[:2]
            niveau = next((i for i, z in enumerate(conf["zones"]) if dept in z), None)
            if niveau is None: continue
            cle_nv = f"{n(nom)}|{n(ville)}"; siren = (l.get("siren") or "").strip()
            if cle_nv in vus or (siren and siren in vus) or cle_nv in contactes or cle_nv in nc or RG.tel_norm(l.get("telephone")) in tels - {""}: continue
            vus.add(cle_nv); siren and vus.add(siren)
            dir_, com = dirigeant(nom); an = (l.get("creation") or l.get("date_collecte") or "")[:4]
            out.append({"nom": com or nom.title() if not dir_ else dir_, "entreprise": (com or "") if dir_ else (com or nom.title()), "dirigeant": dir_, "metier": metier, "ville": ville.title(), "cp": cp, "bat": bat,
                        "effectif": (l.get("effectif") or "").strip(), "niveau": niveau, "creation": an, "siren": siren, "profil_connu": bool((l.get("linkedin") or "").strip()), "a_site": bool((l.get("site") or l.get("site_actuel") or "").strip())})
    out.sort(key=lambda c: (c["niveau"], c["a_site"], not c["bat"], not c["dirigeant"], not c["profil_connu"], rang_effectif(c["effectif"]), -(int(c["creation"]) if c["creation"].isdigit() else 0), _h(c["nom"] + c["ville"])))
    return out


def lien_entreprise(c):
    if c["dirigeant"]: mots = f"{c['dirigeant']} {c['metier']} {c['ville']}".strip()
    else: mots = f"gérant {c['entreprise'] or c['nom']} {c['ville']}".strip()
    return lien_recherche(mots)


def id_cible(t, *parts): return hashlib.sha1("|".join([t] + [n(p) for p in parts]).encode("utf-8")).hexdigest()[:8]


def cibles_entreprises(conf, etat, k):
    """k nouvelles entreprises, zone la plus proche d'abord ; niveau d'élargissement = zone_niveau (puis suivant seulement si le niveau est épuisé)."""
    if k <= 0: return []
    connus = set(etat["cibles"]); pool = [c for c in candidats(conf) if id_cible("entreprise", c["nom"], c["ville"]) not in connus]
    jusque = max(0, conf["zone_niveau"] - 1); res = []
    for niv in range(jusque, len(conf["zones"])):
        niveau = [c for c in pool if c["niveau"] <= niv and c not in res]
        bat = [c for c in niveau if c["bat"]]; com = [c for c in niveau if not c["bat"]]
        while len(res) < k and (bat or com):   # bâtiment d'abord ; commerces locaux (si le réglage les autorise) : un sur trois
            prendre_com = com and (not bat or (len(res) % 3 == 2))
            res.append((com if prendre_com else bat).pop(0))
        if len(res) >= k: break
    return [{"id": id_cible("entreprise", c["nom"], c["ville"]), "type": "entreprise", "nom": c["nom"], "entreprise": c["entreprise"], "dirigeant": c["dirigeant"], "metier": c["metier"], "ville": c["ville"],
             "bat": c["bat"], "effectif": c["effectif"], "lien": lien_entreprise(c),
             "zone": c["cp"][:2], "siren": c["siren"]} for c in res[:k]]


def cibles_closers(conf, etat, k):
    """k recherches LinkedIn d'appelants / closers (aucun nom : Liam choisit le profil dans la recherche), jamais deux fois la même (intitulé, zone, page)."""
    if k <= 0: return []
    connus = set(etat["cibles"]); res = []
    for page in range(1, 50):
        for z in conf["zones_closers"]:
            for it in conf["intitules_closers"]:
                i = id_cible("closer", it, z, str(page))
                if i in connus: continue
                res.append({"id": i, "type": "closer", "nom": f"Profil à choisir : {it}", "entreprise": "", "dirigeant": "", "metier": it, "ville": z, "bat": False, "effectif": "", "page": page,
                            "lien": lien_recherche(f"{it} {z}") + (f"&page={page}" if page > 1 else "")})
                if len(res) >= k: return res
    return res


# --- commentaires ---------------------------------------------------------------------------------------------------------
GABARITS = ["Merci pour ce partage, un point de vue utile pour les artisans et les petites entreprises.", "Un sujet important, merci de l'avoir mis en avant.",
            "Voilà un retour d'expérience qui parle à beaucoup de professionnels, merci.", "Bien dit, c'est une réalité que beaucoup d'entrepreneurs reconnaîtront.",
            "Merci pour ces précisions, elles sont les bienvenues.", "Une réflexion intéressante, merci de la partager.",
            "C'est un point qu'on oublie trop souvent, merci de le rappeler.", "Très clair, merci pour ce rappel.",
            "Merci pour cette publication, utile pour ceux qui se lancent.", "Un regard de terrain précieux, merci d'en parler."]


def http_reel(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; Jarvis)"})
    with urllib.request.urlopen(req, timeout=20) as r: return r.read().decode("utf-8", "replace")


def chercher_posts(conf, deja_urls, http=None, dormir=time.sleep):
    """Posts LinkedIn publics trouvés par un MOTEUR DE RECHERCHE (jamais en parcourant LinkedIn). -> [{url, titre}] ; un échec réseau donne simplement moins de posts."""
    http = http or http_reel; trouves = []; vus = set(deja_urls)
    for q in conf["recherches_commentaires"]:
        if len(trouves) >= conf["commentaires"] * 2: break
        try: html = http("https://html.duckduckgo.com/html/?" + urllib.parse.urlencode({"q": f"site:linkedin.com/posts {q}"}))
        except Exception: continue
        for m in re.finditer(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, re.S):
            href = m.group(1); u = urllib.parse.parse_qs(urllib.parse.urlparse(href).query).get("uddg", [href])[0]
            u = urllib.parse.unquote(u).split("?")[0]
            if not re.match(r"https://(?:[a-z]{2,3}\.)?linkedin\.com/posts/", u) or u in vus: continue
            vus.add(u); titre = re.sub(r"<[^>]+>|&[#\w]+;", " ", m.group(2)); titre = re.sub(r"\s+", " ", titre).strip()
            trouves.append({"url": u, "titre": titre[:160]})
        dormir(1.5)
    return trouves


def modele_reel(conf, titre):
    """Brouillon de commentaire par le modèle local (Ollama), ou None s'il ne répond pas (jamais démarré ici)."""
    o = conf["ollama"]; consigne = ("Rédige un commentaire LinkedIn de une ou deux phrases, en français, au vouvoiement, sans emoji, sans chiffre, sans lien, sans promesse et sans rien vendre, "
                                    f"qui réagit sincèrement à ce post : « {titre} ». Réponds uniquement avec le commentaire.")
    req = urllib.request.Request(o["url"].rstrip("/") + "/api/generate", data=json.dumps({"model": o["modele"], "prompt": consigne, "stream": False}).encode("utf-8"), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=o["delai_secondes"]) as r: return json.loads(r.read().decode("utf-8")).get("response", "").strip().strip('"«» ')
    except Exception: return None


def commentaires(conf, etat, http=None, modele=None, dormir=time.sleep):
    modele = modele or (lambda t: modele_reel(conf, t)); res = []; utilises = set()
    for p in chercher_posts(conf, etat["commentaires_urls"], http, dormir):
        if len(res) >= conf["commentaires"]: break
        txt = modele(p["titre"]); source = "modèle local"
        if not txt or controle_message(txt, 280, commentaire=True):
            g = [x for x in GABARITS if x not in utilises]; txt = g[len(res) % len(g)] if g else GABARITS[len(res) % len(GABARITS)]; source = "gabarit : relisez avant de poster"
        utilises.add(txt); res.append({"id": id_cible("commentaire", p["url"]), "url": p["url"], "titre": p["titre"], "texte": txt, "source": source, "fait": False})
    return res


# --- post du jour (file de l'agent linkedin, sans l'activer ni la modifier) -----------------------------------------------
def post_du_jour(etat, jour):
    try: file_ = LI.etat_lire(); LI.importer(file_, LI.cfg())   # en mémoire seulement : file.json n'est pas réécrit
    except LI.ErreurAgent: return None, "file des posts illisible"
    dispo = [p for p in file_["posts"] if p["type"] == "prospect" and p["statut"] in ("en_file", "pret") and p["id"] not in etat["posts_utilises"] and not LI.controle(p["type"], p["texte"], LI.cfg())]
    dispo.sort(key=lambda p: p["statut"] != "pret")
    if not dispo: return None, "plus de post prospect en stock : demandez un lot à Claude (skill linkedin-posts, lot à déposer dans B2B\\linkedin\\lot-AAAA-MM-JJ.md)"
    p = dispo[0]; etat["posts_utilises"].append(p["id"]); return {"id": p["id"], "texte": p["texte"], "type": "prospect"}, ""


# --- le lot du jour ---------------------------------------------------------------------------------------------------------
def semaine(j): return date.fromisoformat(j).isocalendar()[:2]


def envoyees_semaine(etat, jour):
    s = semaine(jour); return sum(1 for c in etat["cibles"].values() if c.get("demande_envoyee_le") and semaine(c["demande_envoyee_le"]) == s)


def cmd_jour(conf, jour, essai=False, refaire=False, http=None, modele=None, dormir=time.sleep):
    global RAISON; RAISON = None
    try: d = date.fromisoformat(jour)
    except ValueError: raise ErreurAgent(f"jour attendu au format AAAA-MM-JJ (reçu « {jour} »)")
    if d.weekday() >= 5: print(f"{jour} : jour non ouvré, pas de lot."); return 0
    etat = etat_lire()
    if jour in etat["jours"] and not refaire: print(f"{jour} : lot déjà généré."); exporter(etat, conf, jour); return 0
    deja = set(etat["textes"]); lot = {"genere_le": datetime.now().strftime("%Y-%m-%d %H:%M"), "demandes": [], "notes": []}
    reste = max(0, conf["plafond_semaine"] - envoyees_semaine(etat, jour)); total = min(conf["demandes_par_jour"], reste)
    reportees = [c for c in etat["cibles"].values() if c.get("demande_prevue_le") and c["demande_prevue_le"] < jour and not c.get("demande_envoyee_le") and not c.get("ignore")
                 and (d - date.fromisoformat(c["demande_prevue_le"])).days <= 7]
    reportees.sort(key=lambda c: c["demande_prevue_le"]); reportees = reportees[:total]
    cible_ent = total if conf["go_linkedin_auto"] else round(total * conf["part_entreprises"])   # mode automatique : jamais d'appelants/closers
    cible_clo = total - cible_ent
    ent_r = sum(1 for c in reportees if c["type"] == "entreprise"); clo_r = len(reportees) - ent_r
    neufs = cibles_entreprises(conf, etat, max(0, cible_ent - ent_r)); neufs_c = cibles_closers(conf, etat, max(0, cible_clo - clo_r))
    if len(neufs) < max(0, cible_ent - ent_r): lot["notes"].append(f"seulement {len(neufs)} entreprise(s) neuve(s) disponible(s) dans les fichiers (zone_niveau {conf['zone_niveau']}) : élargir la zone dans linkedin-equipe-config.json")
    for c in neufs + neufs_c:
        c["dm"] = dm_pour(c, deja); deja.add(c["dm"]); c["demande_prevue_le"] = jour; c["cree_le"] = jour; etat["cibles"][c["id"]] = c; etat["textes"].append(c["dm"])
    lot["demandes"] = [c["id"] for c in reportees] + [c["id"] for c in neufs + neufs_c]
    lot["reste_semaine"] = reste
    if total == 0: lot["notes"].append("plafond hebdomadaire atteint : aucune nouvelle demande de connexion cette semaine")
    lot["post"], raison = post_du_jour(etat, jour)
    if raison: lot["notes"].append(raison)
    if essai: lot["commentaires"] = []; lot["notes"].append("--essai : commentaires non cherchés (aucun accès réseau)")
    else: lot["commentaires"] = commentaires(conf, etat, http, modele, dormir); etat["commentaires_urls"] += [x["url"] for x in lot["commentaires"]]
    if len(lot["commentaires"]) < conf["commentaires"] and not essai: lot["notes"].append(f"{len(lot['commentaires'])} commentaire(s) sur {conf['commentaires']} : la recherche web publique n'a pas donné plus de posts")
    etat["jours"][jour] = lot
    print(f"{jour} : {len(lot['demandes'])} demande(s) de connexion ({len(reportees)} reportée(s)), {len(lot['commentaires'])} commentaire(s), post {'prêt' if lot['post'] else 'absent'}, reste {reste} demande(s) cette semaine.")
    for x in lot["notes"]: print("  ! " + x)
    if essai: print("[--essai] rien n'est écrit."); return 0
    etat_ecrire(etat); journaliser("lot", f"{jour} : {len(lot['demandes'])} demandes, {len(lot['commentaires'])} commentaires, post {'oui' if lot['post'] else 'non'}")
    exporter(etat, conf, jour)
    if not lot["post"] or lot["notes"] and total == 0: RAISON = "; ".join(lot["notes"])[:200]; return 5 if not lot["post"] else 0
    return 0


# --- suivi (cases du tableau de bord) -------------------------------------------------------------------------------------
def positif_vers_leads_chauds(c, jour):
    """Réponse positive -> registre (lead chaud « À rappeler », qui rappelle : Sid par défaut, voir leads_chauds.py)."""
    with RG.verrou():
        reg = RG.charger(); nom = c.get("entreprise") or c["nom"]
        k = RG.donner(reg, {"nom": nom, "ville": c.get("ville", ""), "tel": "", "metier": c.get("metier", "")}, "LinkedIn", jour)
        qui = "recrutement" if c["type"] == "closer" else "vente de site"
        RG.noter(reg, k, "À rappeler", f"LinkedIn : réponse positive ({qui}), à recontacter", jour, "LinkedIn"); RG.sauver(reg)
    return k


def appliquer(etat, ident, action, jour, conf):
    """Applique une case cochée. -> message. Lève ErreurAgent si impossible (plafond, ordre des étapes)."""
    if action not in ACTIONS: raise ErreurAgent(f"action « {action} » inconnue")
    if action == "commente":
        for lot in etat["jours"].values():
            for x in lot.get("commentaires", []):
                if x["id"] == ident: x["fait"] = True; return "commentaire noté comme posté"
        raise ErreurAgent("commentaire introuvable")
    c = etat["cibles"].get(ident)
    if not c: raise ErreurAgent(f"cible « {ident} » introuvable")
    if action == "ignorer": c["ignore"] = True; c.pop("demande_prevue_le", None) if not c.get("demande_envoyee_le") else None; return "cible écartée (profil introuvable)"
    if action == "annuler":
        for k in ETAPES:
            if c.get(k):
                c.pop(k);
                if k == "repondu_le": c.pop("reponse", None)
                return "dernière étape annulée"
        raise ErreurAgent("rien à annuler")
    if action == "demande_envoyee":
        if c.get("demande_envoyee_le"): return "déjà noté"
        if envoyees_semaine(etat, jour) >= conf["plafond_semaine"]: raise ErreurAgent(f"plafond de {conf['plafond_semaine']} demandes par semaine atteint : rien de plus avant lundi")
        c["demande_envoyee_le"] = jour; return "demande envoyée notée"
    if action == "accepte":
        if not c.get("demande_envoyee_le"): raise ErreurAgent("cochez d'abord « demande envoyée »")
        c["accepte_le"] = c.get("accepte_le") or jour; return "acceptation notée : le DM sort dans « DM du jour »"
    if action == "dm_envoye":
        if not c.get("accepte_le"): raise ErreurAgent("le DM n'est possible qu'après l'acceptation")
        c["dm_envoye_le"] = c.get("dm_envoye_le") or jour; return "DM noté comme envoyé"
    if action == "relance_envoyee":
        if not c.get("dm_envoye_le"): raise ErreurAgent("pas de DM envoyé : pas de relance")
        c["relance_envoyee_le"] = c.get("relance_envoyee_le") or jour; return "relance notée (une seule par personne)"
    if action == "repondu_negatif":
        if not c.get("accepte_le"): raise ErreurAgent("la personne n'a pas encore accepté")
        c["repondu_le"] = c.get("repondu_le") or jour; c["reponse"] = "negative"; c["ignore"] = True; c.pop("relance", None); return "réponse négative ou STOP : personne exclue, plus aucun message"
    if action in ("repondu_positif", "repondu_autre"):
        if not c.get("accepte_le"): raise ErreurAgent("la personne n'a pas encore accepté")
        c["repondu_le"] = c.get("repondu_le") or jour; c["reponse"] = "positive" if action == "repondu_positif" else "autre"
        if action == "repondu_positif": positif_vers_leads_chauds(c, jour); c["lead_chaud"] = True; return "réponse positive : ajoutée aux leads chauds"
        return "réponse notée"


def relances_dues(etat, jour, conf):
    lim = (date.fromisoformat(jour) - timedelta(days=conf["relance_jours"])).isoformat()
    return [c for c in etat["cibles"].values() if c.get("dm_envoye_le") and not c.get("repondu_le") and not c.get("relance_envoyee_le") and c["dm_envoye_le"] <= lim]


def appliquer_et_exporter(conf, ident, action, jour):
    """Une case cochée : applique, prépare les relances dues, réécrit l'état et le tableau de bord (appelé par outils/servir-dashboard.py et par `coche`)."""
    etat = etat_lire(); msg = appliquer(etat, ident, action, jour, conf)
    for c in relances_dues(etat, jour, conf):
        if not c.get("relance"): c["relance"] = relance_pour(c, set(etat["textes"])); etat["textes"].append(c["relance"])
    etat_ecrire(etat); journaliser("coche", f"{ident} {action} {jour}"); exporter(etat, conf, jour); return msg


def cmd_coche(conf, ident, action, jour):
    print(appliquer_et_exporter(conf, ident, action, jour)); return 0


# --- export vers le tableau de bord ---------------------------------------------------------------------------------------
def statut(c):
    for k, lib in (("repondu_le", "a répondu"), ("relance_envoyee_le", "relancé"), ("dm_envoye_le", "DM envoyé"), ("accepte_le", "accepté"), ("demande_envoyee_le", "demande envoyée")):
        if c.get(k): return lib
    return "à envoyer"


def exporter(etat, conf, jour=None):
    """data\\linkedin.json et .js (noms de prospects : dashboard\\data est hors git). Les sections DM et relances sont recalculées à chaque export."""
    jours = sorted(etat["jours"]); jour = jour or (jours[-1] if jours else date.today().isoformat()); lot = etat["jours"].get(jour) or (etat["jours"][jours[-1]] if jours else {})
    for c in relances_dues(etat, jour, conf):   # la relance est préparée le jour où elle devient due (une seule par personne)
        if not c.get("relance"): c["relance"] = relance_pour(c, set(etat["textes"])); etat["textes"].append(c["relance"])
    fiche = lambda c: {k: c.get(k, "") for k in ("id", "type", "nom", "entreprise", "dirigeant", "metier", "ville", "lien", "dm", "relance", "reponse")} | {"statut": statut(c), "effectif": c.get("effectif", ""),
                                                                                                                                          "demande_envoyee_le": c.get("demande_envoyee_le", ""), "accepte_le": c.get("accepte_le", ""),
                                                                                                                                          "dm_envoye_le": c.get("dm_envoye_le", ""), "prevu_le": c.get("demande_prevue_le", "")}
    cs = etat["cibles"]; demandes = [fiche(cs[i]) for i in lot.get("demandes", []) if i in cs and not cs[i].get("ignore")]
    dms = [fiche(c) for c in cs.values() if c.get("accepte_le") and not c.get("dm_envoye_le") and not c.get("ignore")]
    rel = [fiche(c) for c in relances_dues(etat, jour, conf)]
    sem = envoyees_semaine(etat, jour)
    out = {"genere_le": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "jour": jour, "post": lot.get("post"), "commentaires": lot.get("commentaires", []), "demandes": demandes, "dms": dms, "relances": rel, "notes": lot.get("notes", []),
           "semaine": {"envoyees": sem, "plafond": conf["plafond_semaine"]}, "par_jour": conf["demandes_par_jour"],
           "suivi": {"demandes_envoyees": sum(1 for c in cs.values() if c.get("demande_envoyee_le")), "acceptees": sum(1 for c in cs.values() if c.get("accepte_le")),
                     "dm_envoyes": sum(1 for c in cs.values() if c.get("dm_envoye_le")), "reponses": sum(1 for c in cs.values() if c.get("repondu_le")),
                     "positives": sum(1 for c in cs.values() if c.get("reponse") == "positive")}}
    SORTIE.mkdir(parents=True, exist_ok=True); t = json.dumps(out, ensure_ascii=False, indent=1)
    for f, contenu in ((SORTIE / "linkedin.json", t), (SORTIE / "linkedin.js", "window.JARVIS_LINKEDIN = " + t + ";\n")):
        tmp = f.with_name(f.name + ".tmp"); tmp.write_text(contenu, encoding="utf-8"); os.replace(tmp, f)
    etat_ecrire(etat)
    return out


def cmd_etat(conf):
    e = etat_lire(); jour = date.today().isoformat(); print(f"Demandes par jour : {conf['demandes_par_jour']} ; plafond semaine : {conf['plafond_semaine']} (envoyées cette semaine : {envoyees_semaine(e, jour)}).")
    print(f"Lots : {len(e['jours'])} jour(s) ; cibles : {len(e['cibles'])} ; relances dues : {len(relances_dues(e, jour, conf))}."); return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog=AGENT, description="Équipe LinkedIn : prépare le lot du jour, Liam envoie. Aucun envoi, aucun scraping de LinkedIn.")
    sp = p.add_subparsers(dest="cmd", required=True)
    j = sp.add_parser("jour"); j.add_argument("--jour", default=None); j.add_argument("--refaire", action="store_true"); j.add_argument("--essai", "--a-blanc", dest="essai", action="store_true")
    c = sp.add_parser("coche"); c.add_argument("id"); c.add_argument("action", choices=ACTIONS); c.add_argument("--jour", default=None)
    au = sp.add_parser("auto"); au.add_argument("sous", nargs="?", default="passage", choices=("passage", "connexion", "reprendre", "etat", "resume", "apercu")); au.add_argument("--jour", default=None)
    sp.add_parser("etat"); sp.add_parser("exporter")
    a = p.parse_args(argv); M.exiger(AGENT, a.cmd, getattr(a, "essai", False))
    try:
        conf = cfg()
        if a.cmd == "etat": return cmd_etat(conf)
        jour = getattr(a, "jour", None) or datetime.now().date().isoformat()
        if a.cmd == "auto":
            if a.sous == "reprendre": return LA.reprendre()
            if a.sous == "connexion": return LA.connexion(conf)
            if a.sous == "etat": return LA.etat_auto(conf, etat_lire(), jour)
            if a.sous == "apercu": return LA.apercu(conf, etat_lire(), jour)
            if a.sous == "resume": LA.resume(conf, jour, datetime.now(), force=True); return 0   # envoi immédiat (essai à la main)
            code = LA.tick(conf, jour, datetime.now())
            try: LA.resume(conf, jour, datetime.now())   # résumé du soir : une fois par jour dès 18:05
            except Exception: pass
            return code
        if a.cmd == "jour": return cmd_jour(conf, jour, a.essai, a.refaire)
        if a.cmd == "coche": return cmd_coche(conf, a.id, a.action, jour)
        exporter(etat_lire(), conf, jour); print("tableau de bord mis à jour."); return 0
    except ErreurAgent as e:
        print(f"  ! {e}"); return 2
    except OSError as e:
        print(f"  ! erreur de fichier : {e.strerror or type(e).__name__}"); return 2


if __name__ == "__main__":
    _t0 = time.time(); _code = main()
    if sys.argv[1:2] == ["jour"] and not {"--essai", "--a-blanc"} & set(sys.argv):
        try:
            sys.path.insert(0, str(RACINE / "harness")); import traces
            traces.ecrire(AGENT, "jour", "terminé" if _code == 0 else "échec", time.time() - _t0, ok=_code == 0, erreur=None if _code == 0 else (RAISON or f"code {_code}"))
        except Exception: pass
    sys.exit(_code)
