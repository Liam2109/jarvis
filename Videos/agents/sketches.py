#!/usr/bin/env python3
"""Ligne B (compte recrutement de call callers), 17/11/2026 : « sketch à deux ». Gérard + un interlocuteur (client, collègue, voisin…), répliques courtes,
retournement drôle, puis la fin dite par Gérard face caméra. Remplace les histoires racontées par un narrateur (histoires-base.md, retirées le 17/11/2026).
Tout le texte est écrit à la main une fois pour toutes dans Videos\\sketches-base.json : AUCUNE phrase n'est inventée par Qwen. Qwen (local, gratuit)
choisit seulement un sketch parmi ceux que le code autorise et remplit ses champs variables ({metier}, {objet}, {lieu}, {nom}) avec des valeurs prises
dans les listes écrites à la main ; le code refuse toute autre valeur et revient alors à un choix sans Qwen. Aucun token Claude.
Le code vérifie le schéma (6 à 8 répliques, 10 mots au plus par réplique même avec la valeur la plus longue, retournement, champs connus, jeu et
bruitages du catalogue), les interdits (revenus chiffrés, faux témoignages, statistiques, promesse de gains, chiffres, numéro privé…), et ne rejoue
jamais un sketch des 20 dernières vidéos de la ligne B. Répartition : 40 % comédie de Gérard au téléphone, 40 % leçons de vente, 20 % entrepreneuriat
et quotidien. Trois fins tournantes (on recrute des call callers à la commission, formulaire en bio ou DM).
Troupe et décors (17/11/2026, Videos\\troupe.json) : l'interlocuteur est un personnage récurrent (nommé par le sketch, sinon choisi par le code selon le rôle
et le genre) ; le code ne reprend jamais le même couple personnage / décor dans les 10 dernières vidéos de la ligne B.
Mini-séries : un sketch peut porter « serie » {id, titre, episode, episodes} ; une seule série à la fois, une vidéo ordinaire entre deux épisodes, épisodes dans l'ordre.
Lot hebdomadaire : python Videos\\agents\\sketches.py lot Videos\\idees-nouvelles\\AAAA-MM-JJ.json -> 20 sketches validés comme la banque, ajoutés à
sketches-base.json ; lot invalide refusé avec le motif (fichier .refus.txt à côté du lot), rien n'est ajouté."""
import argparse, json, re, sys, unicodedata
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import commun as C   # noqa: E402

SKETCHES = C.VIDEOS / "sketches-base.json"
TROUPE = C.VIDEOS / "troupe.json"
IDEES = C.VIDEOS / "idees-nouvelles"
FENETRE_COUPLE = 10       # aucun couple personnage / décor repris dans les 10 dernières vidéos de la ligne B
LOT_TAILLE = 20
SERIE_EPISODES = (3, 5)
MOTS_MAX = 10
REPLIQUES = (6, 8)
MOTS_DIALOGUE = (34, 66)   # mots du dialogue (sans la fin) : 25 à 35 s avec la fin, les pauses et la carte de fin
FENETRE = 20               # aucun sketch rejoué dans les 20 dernières vidéos de la ligne B
CHAMP = re.compile(r"\{(\w+)\}")
CHAMPS = {"metier", "objet", "lieu", "nom"}
THEMES = {"telephone": "comedie", "lecon": "lecon", "entrepreneuriat": "autre", "quotidien": "autre"}
PARTS = {"comedie": 0.4, "lecon": 0.4, "autre": 0.2}
SFX_MAISON = {"sonnerie"}   # généré par code (monteur.py)
SFX_CATALOGUE = {"pop", "boing", "whoosh", "swish", "zip", "record-scratch", "boom", "ding", "buzzer", "crickets", "rimshot", "slide-up", "slide-down", "sad-trombone",
                 "thud", "laugh", "sparkle", "ding-idea", "zap", "hum", "blip", "clack", "coins", "register", "stamp", "drawer", "rustle", "clock-tick", "click",
                 "riser-hit", "door-knock", "applause", "camera-shutter"}   # stick-stage, src/data/sfx.json : tous CC0-1.0, synthétisés par code
DECORS_OK = {"bureau", "cabinet", "boutique", "librairie", "cafe", "café", "cuisine", "salon", "rue", "parc", "reunion", "réunion", "chambre",
             "atelier", "attente", "agence", "commerces", "terrasse"}   # les 6 derniers : décors de jour de la troupe (Videos/stick-stage/decors)

# Garde-fous propres à la ligne B (en plus de ceux de scripts.py : chiffres, promesses, phrases molles, adresses, lieux)
CTA_OK = [re.compile(r"\bcall callers?\b", re.I), re.compile(r"\bcommission\b", re.I), re.compile(r"\bbio\b", re.I), re.compile(r"\bDM\b")]
RDV15 = re.compile(r"(quinze|15)\s*min|rendez-vous de (quinze|15)", re.I)
INTERDITS_LECONS = re.compile(r"closer gagne|statisti|selon (une|les) [ée]tudes?|des gens (d[ée]crochent|r[ée]pondent)|taux de|"
                              r"num[ée]ro (priv[ée]|perso)|portable (du|d'un|de son) (patron|d[ée]cideur|g[ée]rant|dirigeant)|ligne directe du", re.I)
VRAIES_PERSONNES = re.compile(r"\b(macron|musk|zuckerberg|bezos|jobs|mbapp[ée]|zidane|squeezie|inoxtag|cyprien|norman|tibo|booba|jul|aya nakamura)\b", re.I)
LIEUX_FIN = re.compile(r"près de|chez moi|\brouen\b", re.I)   # la fin ne situe jamais Liam


def lire(f=SKETCHES):
    return json.loads(Path(f).read_text(encoding="utf-8"))


def mots(t): return len(C.mots_de(t))


def troupe(f=None):
    """{id: personnage} de Videos\\troupe.json (Gérard compris)."""
    try: return {x["id"]: x for x in json.loads(Path(f or TROUPE).read_text(encoding="utf-8"))["personnages"]}
    except (OSError, ValueError, KeyError): return {}


def decors_de(s): return list(s.get("decors") or [s["decor"]])


def distribution(s, tr=None):
    """Personnages qui peuvent jouer l'interlocuteur : celui que le sketch nomme, sinon ceux de la troupe qui tiennent son rôle (et son genre s'il est fixé)."""
    tr = tr if tr is not None else troupe(); i = s.get("interlocuteur") or {}
    if i.get("personnage"): return [i["personnage"]] if i["personnage"] in tr else []
    g = i.get("genre", "libre")
    return [p for p, x in tr.items() if p != "gerard" and i.get("role") in x.get("roles", []) and (g == "libre" or x["genre"] == g) and nom_tient(s, x["appel"])]


def nom_tient(s, appel):
    """Vrai si chaque réplique garde 10 mots au plus avec cet appel à la place de {nom} (« Madame Lefort » compte deux mots), les autres champs remplis avec
    leur valeur la plus longue."""
    try: listes = lire()["listes"]
    except (OSError, ValueError, KeyError): listes = {}
    long = {c: max(listes.get(c) or ["X X X"], key=mots) for c in ("metier", "objet", "lieu")} | {"nom": appel}
    return all(mots(remplir(r["texte"], long)) <= MOTS_MAX for r in s["repliques"] if "{nom}" in r["texte"])


def couples_recents(historique, n=FENETRE_COUPLE):
    return {(h.get("personnage"), h.get("decor")) for h in [h for h in historique if h.get("serie") == "B" and h.get("personnage")][-n:]}


def couples(s, historique, tr=None):
    """(personnage, décor) possibles pour ce sketch, hors des couples des 10 dernières vidéos ; les moins vus récemment d'abord."""
    vus = couples_recents(historique); b = [h for h in historique if h.get("serie") == "B"]
    der = lambda k, v: max([i for i, h in enumerate(b) if h.get(k) == v], default=-1)
    out = [(p, d) for p in distribution(s, tr) for d in decors_de(s) if (p, d) not in vus]
    return sorted(out, key=lambda x: (der("personnage", x[0]), der("decor", x[1])))


def categorie(s): return THEMES.get(s.get("theme"), "autre")


def liste_de(base, champ, genre):
    """Valeurs permises d'un champ ; {nom} suit le genre de l'interlocuteur (libre = les deux listes)."""
    l = base["listes"]
    if champ != "nom": return list(l.get(champ) or [])
    return list(l.get("nom_f") or []) * (genre in ("f", "libre")) + list(l.get("nom_h") or []) * (genre in ("h", "libre"))   # {nom} : appel du personnage (nom_tient)


def champs_de(s): return sorted({c for r in s["repliques"] for c in CHAMP.findall(r["texte"])})


def remplir(texte, valeurs): return CHAMP.sub(lambda m: valeurs.get(m.group(1), m.group(0)), texte)


def _garde(t, conf, S, dialogue=True):
    """Problèmes d'un texte prêt (aucun champ). Dans le dialogue, les personnages se vouvoient ou se disent bonjour : seule la fin parle au spectateur (tutoiement)."""
    pb = []
    for rx, quoi in ((S.NOMBRES, "nombre ou chiffre"), (S.INTERDITS, "formulation interdite"), (S.INTERDITS_B, "formulation interdite"), (S.DIDASCALIES, "mise en scène"),
                     (S.ADRESSE, "adresse épelée"), (RDV15, "rendez-vous de 15 minutes"), (VRAIES_PERSONNES, "vraie personne"), (INTERDITS_LECONS, "interdit des leçons")):
        m = rx.search(t)
        if m: pb.append(f"{quoi} (« {m.group(0)} »)")
    m = S.MOLLES.search(re.sub(r"\bbonjour\b", "", t, flags=re.I) if dialogue else t)
    if m: pb.append(f"phrase molle (« {m.group(0)} »)")
    lieu = S.lieu_interdit(t, conf)
    if lieu: pb.append(f"lieu interdit (« {lieu} »)")
    if not dialogue:
        faux = S.public_faux(t, "B")
        if faux: pb.append(f"mauvais public (« {faux} ») : la fin tutoie le spectateur")
        m = LIEUX_FIN.search(t)
        if m: pb.append(f"lieu dans la fin (« {m.group(0)} »)")
    return pb


def verifier_fin(fin, conf, S):
    """Une fin = 2 répliques de Gérard face caméra (10 mots au plus chacune) qui disent call callers, commission, bio et DM."""
    pb = []
    if not (isinstance(fin, list) and len(fin) == 2 and all(isinstance(x, str) and x.strip() for x in fin)): return ["fin : 2 répliques attendues"]
    if not all(r.search(" ".join(fin)) for r in CTA_OK): pb.append("fin incomplète (call callers, commission, formulaire en bio, DM)")
    for x in fin:
        if mots(x) > MOTS_MAX: pb.append(f"fin trop longue ({mots(x)} mots) : « {x} »")
        pb += _garde(x, conf, S, dialogue=False)
    return pb


def verifier_sketch(s, base, conf, S, ids_vus=None):
    """Problèmes d'un sketch de la base (vide = accepté). Chaque réplique est vérifiée avec la valeur la plus longue de chaque champ."""
    sid = s.get("id", "?"); pb = []
    for k in ("id", "theme", "titre", "formule", "decor", "interlocuteur", "repliques", "retournement"):
        if k not in s: pb.append(f"{sid} : champ « {k} » manquant")
    if pb: return pb
    if ids_vus is not None:
        if sid in ids_vus: pb.append(f"{sid} : identifiant en double")
        ids_vus.add(sid)
    if s["theme"] not in THEMES: pb.append(f"{sid} : thème inconnu « {s['theme']} »")
    for dd in decors_de(s):
        if str(dd).lower() not in DECORS_OK: pb.append(f"{sid} : décor inconnu « {dd} »")
    inter = s["interlocuteur"] or {}; tr = troupe()
    if inter.get("personnage"):
        if inter["personnage"] not in tr or inter["personnage"] == "gerard": pb.append(f"{sid} : personnage inconnu de la troupe « {inter['personnage']} »")
        genre = tr.get(inter["personnage"], {}).get("genre", "libre")
    else:
        genre = inter.get("genre")
        if genre not in ("f", "h", "libre"): pb.append(f"{sid} : genre de l'interlocuteur attendu f, h ou libre")
        elif tr and not distribution(s, tr): pb.append(f"{sid} : aucun personnage de la troupe ne tient le rôle « {inter.get('role')} »")
    se = s.get("serie")
    if se is not None and not (isinstance(se, dict) and se.get("id") and se.get("titre") and isinstance(se.get("episode"), int)
                               and isinstance(se.get("episodes"), int) and SERIE_EPISODES[0] <= se["episodes"] <= SERIE_EPISODES[1] and 1 <= se["episode"] <= se["episodes"]):
        pb.append(f"{sid} : série mal décrite (id, titre, episode, episodes de 3 à 5)")
    rs = s["repliques"]
    if not REPLIQUES[0] <= len(rs) <= REPLIQUES[1]: pb.append(f"{sid} : {len(rs)} répliques ({REPLIQUES[0]} à {REPLIQUES[1]} attendues)")
    if {r.get("qui") for r in rs} != {"G", "I"}: pb.append(f"{sid} : Gérard (G) et l'interlocuteur (I) doivent parler tous les deux")
    if not (isinstance(s["retournement"], int) and 1 <= s["retournement"] < len(rs)): pb.append(f"{sid} : retournement hors des répliques")
    champs = champs_de(s)
    if not champs: pb.append(f"{sid} : aucun champ variable")
    inconnus = set(champs) - CHAMPS
    if inconnus: pb.append(f"{sid} : champ inconnu {sorted(inconnus)}")
    long = {c: max(liste_de(base, c, genre or "libre") or [""], key=mots) for c in CHAMPS}
    try: import rendu_stickstage as RS; expr_ok, poses_ok = RS.EXPRESSIONS, RS.POSES
    except Exception: expr_ok = poses_ok = None
    total = 0
    for i, r in enumerate(rs):
        t = remplir(r.get("texte", ""), long); n = mots(t); total += n
        if not n: pb.append(f"{sid} réplique {i + 1} : vide")
        if n > MOTS_MAX: pb.append(f"{sid} réplique {i + 1} : {n} mots (10 au plus) « {t} »")
        pb += [f"{sid} réplique {i + 1} : {x}" for x in _garde(t, conf, S)]
        if r.get("jeu"):
            e, _, p = r["jeu"].partition(" ")
            if expr_ok and (e not in expr_ok or p not in poses_ok): pb.append(f"{sid} réplique {i + 1} : jeu inconnu « {r['jeu']} »")
        if r.get("sfx") and r["sfx"] not in SFX_MAISON | SFX_CATALOGUE: pb.append(f"{sid} réplique {i + 1} : bruitage inconnu « {r['sfx']} »")
    if not MOTS_DIALOGUE[0] <= total <= MOTS_DIALOGUE[1]: pb.append(f"{sid} : {total} mots de dialogue ({MOTS_DIALOGUE[0]} à {MOTS_DIALOGUE[1]} pour 25-35 s)")
    return pb


def verifier_base(base, conf, S):
    """Problèmes de tout le fichier (vide = accepté) : listes, 3 fins, chaque sketch, valeurs des listes, répartition des thèmes."""
    pb = []
    for k in ("metier", "objet", "lieu", "nom_f", "nom_h"):
        vals = (base.get("listes") or {}).get(k)
        if not vals: pb.append(f"liste « {k} » vide ou absente"); continue
        for v in vals: pb += [f"liste {k} « {v} » : {x}" for x in _garde(v, conf, S)]
    fins = base.get("fins") or []
    if len(fins) != 3: pb.append(f"{len(fins)} fins (3 attendues)")
    for i, f in enumerate(fins): pb += [f"fin {i + 1} : {x}" for x in verifier_fin(f, conf, S)]
    vus = set()
    for s in base.get("sketches") or []: pb += verifier_sketch(s, base, conf, S, vus)
    cats = [categorie(s) for s in base.get("sketches") or []]
    for c, part in PARTS.items():
        if cats and abs(cats.count(c) / len(cats) - part) > 0.1: pb.append(f"répartition : {cats.count(c)} sketch(es) « {c} » sur {len(cats)} (part visée {int(part * 100)} %)")
    pb += verifier_series(base.get("sketches") or [])
    return pb


def verifier_series(sketches):
    """Chaque série : de 3 à 5 épisodes numérotés de 1 à N, sans trou ni doublon, même titre."""
    pb, series = [], {}
    for s in sketches:
        if s.get("serie"): series.setdefault(s["serie"]["id"], []).append(s["serie"])
    for sid, eps in series.items():
        n = eps[0].get("episodes")
        if sorted(e.get("episode") for e in eps) != list(range(1, (n or 0) + 1)) or any(e.get("episodes") != n or e.get("titre") != eps[0].get("titre") for e in eps):
            pb.append(f"série « {sid} » : épisodes attendus 1 à {n}, même titre")
    return pb


def episode_suivant(historique, sketches):
    """Épisode à jouer maintenant, ou None : une seule série à la fois (la première pas finie, dans l'ordre de la banque), jamais deux épisodes de suite
    (une vidéo ordinaire entre deux), épisodes dans l'ordre."""
    b = [h for h in historique if h.get("serie") == "B" and h.get("sketch")]
    joues = {h["sketch"] for h in b}; par_id = {s["id"]: s for s in sketches}
    if b and par_id.get(b[-1]["sketch"], {}).get("serie"): return None   # le dernier était un épisode : une vidéo ordinaire d'abord
    series = []
    for s in sketches:
        if s.get("serie") and s["serie"]["id"] not in series: series.append(s["serie"]["id"])
    for sid in series:
        eps = sorted((s for s in sketches if (s.get("serie") or {}).get("id") == sid), key=lambda s: s["serie"]["episode"])
        reste = [s for s in eps if s["id"] not in joues]
        if reste: return reste[0]
    return None


def candidates(historique, sketches, fenetre=FENETRE, tr=None):
    """Sketches autorisés, dans l'ordre où les jouer. Épisode de série dû : lui seul (s'il a un couple personnage / décor libre).
    Sinon les sketches ordinaires : catégorie la plus en retard sur sa part (40/40/20) d'abord, puis jamais joué (lot le plus récent d'abord), puis joué il y a
    le plus longtemps. Aucun des `fenetre` derniers sketches de la ligne B, aucun sketch sans couple personnage / décor libre (liste vide si aucun)."""
    ep = episode_suivant(historique, sketches)
    if ep and couples(ep, historique, tr): return [ep]
    sketches = [s for s in sketches if not s.get("serie")]
    faits = [h.get("sketch") for h in historique if h.get("serie") == "B" and h.get("sketch")]
    recents = set(faits[-fenetre:]); derniere = {x: i for i, x in enumerate(faits)}
    cat = {s["id"]: categorie(s) for s in sketches}
    vues = [cat.get(x, "autre") for x in faits[-fenetre:]]
    retard = {c: part - (vues.count(c) / len(vues) if vues else 0) for c, part in PARTS.items()}
    lots = sorted({s.get("lot", "") for s in sketches}, reverse=True); rang = {l: i for i, l in enumerate(lots)}
    return sorted((s for s in sketches if s["id"] not in recents and couples(s, historique, tr)),
                  key=lambda s: (-retard[categorie(s)], derniere.get(s["id"], -1), rang[s.get("lot", "")]))


def fin_suivante(historique, fins):
    """(index, fin) : les 3 fins tournent, d'une vidéo de sketch à la suivante."""
    n = sum(1 for h in historique if h.get("serie") == "B" and h.get("sketch")); i = n % len(fins)
    return i, fins[i]


def valeurs_par_defaut(s, base, n, genre="h"):
    """Choix sans Qwen : valeurs tournantes dans les listes (n = rang de la vidéo) ; {nom} est rempli ensuite avec l'appel du personnage joué."""
    return {c: (lambda l: l[(n * 3 + len(c)) % len(l)])(liste_de(base, c, genre)) for c in champs_de(s) if c != "nom"}


def _norm(t): return unicodedata.normalize("NFC", str(t or "")).strip()


def valeurs_valides(s, base, valeurs):
    """Vrai si Qwen a rempli chaque champ du sketch (sauf {nom}, donné par le personnage joué) avec une valeur EXACTE des listes."""
    return all(_norm(valeurs.get(c)) in map(_norm, liste_de(base, c, "libre")) for c in champs_de(s) if c != "nom")


SYSTEME = ("Tu choisis un sketch dans une liste et tu remplis ses champs avec des valeurs prises EXACTEMENT dans les listes données. "
           "Tu n'écris aucune phrase. Réponds uniquement avec un objet JSON valide.")


def distribuer(s, historique, vals, tr=None):
    """Couple personnage / décor du code (le moins vu récemment, jamais un des 10 derniers) ; {nom} = appel du personnage. -> (vals, personnage, décor)"""
    tr = tr if tr is not None else troupe(); p, d = couples(s, historique, tr)[0]
    if "nom" in champs_de(s): vals = dict(vals, nom=tr[p]["appel"])
    return vals, p, d


def choisir(ollama, historique, base, n=None):
    """-> (sketch, valeurs, personnage, décor, origine « qwen » | « code »). Qwen choisit parmi les 3 premiers sketches autorisés et remplit les champs
    (sauf {nom}) ; réponse hors listes = choix du code. Le personnage et le décor sont toujours choisis par le code."""
    tr = troupe(); cands = candidates(historique, base["sketches"], tr=tr)[:3]
    if not cands: return None, {}, "", "", ""
    n = sum(1 for h in historique if h.get("serie") == "B") if n is None else n
    if ollama is not None and len(cands) > 1 or (ollama is not None and [c for c in champs_de(cands[0]) if c != "nom"]):
        offre = [{"id": s["id"], "titre": s["titre"], "champs": [c for c in champs_de(s) if c != "nom"]} for s in cands]
        listes = {k: v for k, v in base["listes"].items() if k in ("metier", "objet", "lieu")}
        demande = (f"Sketches possibles : {json.dumps(offre, ensure_ascii=False)}\nListes : {json.dumps(listes, ensure_ascii=False)}\n"
                   "Choisis un sketch. Pour chacun de ses champs, prends une valeur dans la liste du même nom. "
                   'Format : {"sketch": "T01", "valeurs": {"metier": "..."}}')
        try:
            r = json.loads(ollama.chat(SYSTEME, demande, temperature=0.8, num_predict=200))
            s = next((x for x in cands if x["id"] == str(r.get("sketch", "")).strip()), None)
            vals = {k: _norm(v) for k, v in (r.get("valeurs") or {}).items() if k in CHAMPS and k != "nom"}
            if s and valeurs_valides(s, base, vals):
                v, p, d = distribuer(s, historique, {c: vals[c] for c in champs_de(s) if c != "nom"}, tr); return s, v, p, d, "qwen"
        except Exception: pass
    s = cands[0]; v, p, d = distribuer(s, historique, valeurs_par_defaut(s, base, n), tr)
    return s, v, p, d, "code"


def document(s, valeurs, personnage, decor, i_fin, fin, conf, jour, heure, origine):
    """Script de la vidéo : répliques (champs remplis) + fin de Gérard face caméra ; qui parle, jeu, bruitages, retournement, personnage, décor, série."""
    rs = s["repliques"]; lignes = [remplir(r["texte"], valeurs) for r in rs]
    tr = troupe(); pers = tr.get(personnage, {}); genre = pers.get("genre", "h"); se = s.get("serie")
    titre_ecran = f"{se['titre']} · épisode {se['episode']}/{se['episodes']}" if se else s["titre"]
    leg = (f"{s['titre']}\n\nUn sketch de Gérard. On recrute des call callers à la commission : formulaire en bio, ou envoie un DM.\n\n{C.MENTION_IA}\n\n"
           + (conf["lignes"]["B"].get("hashtags") or "#callcaller #humour #prospection"))
    return {"jour": jour, "passage": heure, "serie": "B", "format": "sketch", "sketch": s["id"], "histoire": s["id"], "theme": s["theme"], "categorie": categorie(s),
            "formule": s["formule"], "decor": decor, "variante": origine, "valeurs": valeurs, "titre_ecran": titre_ecran, "serie_sketch": se,
            "interlocuteur": {"personnage": personnage, "role": pers.get("role", (s.get("interlocuteur") or {}).get("role", "")), "genre": genre, "nom": pers.get("appel", "")},
            "telephone": bool(s.get("telephone")), "fin_variante": f"FIN{i_fin + 1}", "style": "classic", "sujet": s["titre"], "titre": titre_ecran, "accroche": lignes[0],
            "scenes": lignes + list(fin), "qui": [r["qui"] for r in rs] + ["G", "G"],
            "jeu": [r.get("jeu", "").split(" ") if r.get("jeu") else None for r in rs] + [["happy", "point"], ["happy", "wave"]],
            "sfx": [r.get("sfx") for r in rs] + ["pop", None], "punchline": s["retournement"], "fin_indices": [len(rs), len(rs) + 1], "legende": leg,
            "mots": sum(mots(x) for x in lignes + list(fin)), "modele": conf["modele"]}


def trop_proche(texte, anciens, seuil=0.8):
    """Vrai si la vidéo reprend (80 % des mots pleins ou plus) le texte d'une des vidéos récentes."""
    def pleins(t):
        t = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().lower()
        return {m for m in re.findall(r"[a-z]+", t) if len(m) > 3}
    a = pleins(texte)
    for b in map(pleins, anciens):
        if a and b and len(a & b) / min(len(a), len(b)) >= seuil: return True
    return False


def textes_recents(dossier, n=FENETRE):
    """Dialogue (sans la fin) des n dernières vidéos de la ligne B (scripts\\*.json)."""
    docs = []
    for p in sorted(Path(dossier).glob("*.json")) if Path(dossier).exists() else []:
        try: d = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError): continue
        if isinstance(d, dict) and d.get("serie") == "B": docs.append(" ".join(d.get("scenes", [])[:-2]))
    return docs[-n:]


# --- Lot hebdomadaire de sketches -------------------------------------------------------------------------------------------------
def verifier_lot(lot, base, conf, S):
    """Problèmes d'un lot (vide = accepté) : 20 sketches, mêmes validations que la banque, identifiants nouveaux, répartition 8 / 8 / 4 (à un près),
    séries complètes et nouvelles (une série n'est jamais à cheval sur deux lots)."""
    sk = lot.get("sketches") if isinstance(lot, dict) else None
    if not isinstance(sk, list): return ["format : objet JSON {\"sketches\": [...]} attendu"]
    pb = [] if len(sk) == LOT_TAILLE else [f"{len(sk)} sketches ({LOT_TAILLE} attendus)"]
    banque, vus = {s["id"] for s in base["sketches"]}, set()
    for s in sk:
        if not isinstance(s, dict): pb.append("un sketch n'est pas un objet JSON"); continue
        if s.get("id") in banque: pb.append(f"{s.get('id')} : identifiant déjà dans la banque")
        pb += verifier_sketch(s, base, conf, S, vus)
    if pb: return pb
    cats = [categorie(s) for s in sk]
    for c, part in PARTS.items():
        if abs(cats.count(c) - part * len(sk)) > 1: pb.append(f"répartition : {cats.count(c)} sketch(es) « {c} » ({int(part * len(sk))} attendus, à un près)")
    anciennes = {s["serie"]["id"] for s in base["sketches"] if s.get("serie")}
    pb += [f"série « {s['serie']['id']} » déjà dans la banque" for s in sk if s.get("serie") and s["serie"]["id"] in anciennes]
    return pb + verifier_series(sk)


def ajouter_lot(fichier, conf, S, base_f=SKETCHES):
    """Valide le lot et l'ajoute à la banque (chaque sketch marqué « lot » = date du fichier). -> (True, nombre) ou (False, motifs). Lot refusé : .refus.txt."""
    fichier = Path(fichier); base = lire(base_f)
    try: lot = json.loads(fichier.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e: motifs = [f"lot illisible ({type(e).__name__})"]
    else: motifs = verifier_lot(lot, base, conf, S)
    if motifs:
        fichier.with_suffix(".refus.txt").write_text(f"Lot refusé le {datetime.now():%Y-%m-%d %H:%M} :\n" + "\n".join(f"- {m}" for m in motifs) + "\n", encoding="utf-8")
        return False, motifs
    for s in lot["sketches"]: base["sketches"].append(dict(s, lot=fichier.stem))
    pb = verifier_base(base, conf, S)
    if pb: return False, [f"banque refusée après ajout : {x}" for x in pb]
    tmp = Path(base_f).with_suffix(".tmp"); tmp.write_text(json.dumps(base, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"); tmp.replace(base_f)
    fichier.with_suffix(".refus.txt").unlink(missing_ok=True)
    C.journal("videos-scripts", "lot de sketches", f"{fichier.name} : {len(lot['sketches'])} sketches ajoutés à la banque")
    return True, len(lot["sketches"])


def main(argv=None):
    a = argparse.ArgumentParser(prog="sketches"); sp = a.add_subparsers(dest="cmd", required=True)
    sp.add_parser("lot").add_argument("fichier", help="Videos\\idees-nouvelles\\AAAA-MM-JJ.json")
    sp.add_parser("verifier")
    a = a.parse_args(argv)
    import scripts as S
    if a.cmd == "verifier":
        pb = verifier_base(lire(), C.cfg(), S); print("Banque de sketches : " + ("valide" if not pb else "; ".join(pb))); return 1 if pb else 0
    ok, r = ajouter_lot(a.fichier, C.cfg(), S)
    print(f"Nouveau lot de sketches : {r} sketches ajoutés à la banque." if ok else "Lot refusé :\n" + "\n".join(f"- {m}" for m in r)); return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
