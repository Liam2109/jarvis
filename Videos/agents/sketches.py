#!/usr/bin/env python3
"""Ligne B (compte recrutement de call callers), 17/11/2026 : « sketch à deux ». Gérard + un interlocuteur (client, collègue, voisin…), répliques courtes,
retournement drôle, puis la fin dite par Gérard face caméra. Remplace les histoires racontées par un narrateur (histoires-base.md, retirées le 17/11/2026).
Tout le texte est écrit à la main une fois pour toutes dans Videos\\sketches-base.json : AUCUNE phrase n'est inventée par Qwen. Qwen (local, gratuit)
choisit seulement un sketch parmi ceux que le code autorise et remplit ses champs variables ({metier}, {objet}, {lieu}, {nom}) avec des valeurs prises
dans les listes écrites à la main ; le code refuse toute autre valeur et revient alors à un choix sans Qwen. Aucun token Claude.
Le code vérifie le schéma (6 à 8 répliques, 10 mots au plus par réplique même avec la valeur la plus longue, retournement, champs connus, jeu et
bruitages du catalogue), les interdits (revenus chiffrés, faux témoignages, statistiques, promesse de gains, chiffres, numéro privé…), et ne rejoue
jamais un sketch des 20 dernières vidéos de la ligne B. Répartition : 40 % comédie de Gérard au téléphone, 40 % leçons de vente, 20 % entrepreneuriat
et quotidien. Trois fins tournantes (on recrute des call callers à la commission, formulaire en bio ou DM)."""
import json, re, sys, unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import commun as C   # noqa: E402

SKETCHES = C.VIDEOS / "sketches-base.json"
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
DECORS_OK = {"bureau", "cabinet", "boutique", "librairie", "cafe", "café", "cuisine", "salon", "rue", "parc", "reunion", "réunion", "chambre"}

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


def categorie(s): return THEMES.get(s.get("theme"), "autre")


def liste_de(base, champ, genre):
    """Valeurs permises d'un champ ; {nom} suit le genre de l'interlocuteur (libre = les deux listes)."""
    l = base["listes"]
    if champ != "nom": return list(l.get(champ) or [])
    return list(l.get("nom_f") or []) * (genre in ("f", "libre")) + list(l.get("nom_h") or []) * (genre in ("h", "libre"))


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
    if str(s["decor"]).lower() not in DECORS_OK: pb.append(f"{sid} : décor inconnu « {s['decor']} »")
    genre = (s["interlocuteur"] or {}).get("genre")
    if genre not in ("f", "h", "libre"): pb.append(f"{sid} : genre de l'interlocuteur attendu f, h ou libre")
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
    return pb


def candidates(historique, sketches, fenetre=FENETRE):
    """Sketches autorisés, dans l'ordre où les jouer : catégorie la plus en retard sur sa part (40/40/20) d'abord, puis jamais joué, puis joué il y a le plus longtemps.
    Aucun des `fenetre` derniers sketches de la ligne B (liste vide si tous y sont)."""
    faits = [h.get("sketch") for h in historique if h.get("serie") == "B" and h.get("sketch")]
    recents = set(faits[-fenetre:]); derniere = {x: i for i, x in enumerate(faits)}
    cat = {s["id"]: categorie(s) for s in sketches}
    vues = [cat.get(x, "autre") for x in faits[-fenetre:]]
    retard = {c: part - (vues.count(c) / len(vues) if vues else 0) for c, part in PARTS.items()}
    return sorted((s for s in sketches if s["id"] not in recents), key=lambda s: (-retard[categorie(s)], derniere.get(s["id"], -1)))


def fin_suivante(historique, fins):
    """(index, fin) : les 3 fins tournent, d'une vidéo de sketch à la suivante."""
    n = sum(1 for h in historique if h.get("serie") == "B" and h.get("sketch")); i = n % len(fins)
    return i, fins[i]


def valeurs_par_defaut(s, base, n):
    """Choix sans Qwen : valeurs tournantes dans les listes (n = rang de la vidéo), genre libre alterné."""
    g = s["interlocuteur"]["genre"]; genre = g if g in ("f", "h") else ("f" if n % 2 == 0 else "h")
    return {c: (lambda l: l[(n * 3 + len(c)) % len(l)])(liste_de(base, c, genre)) for c in champs_de(s)}, genre


def _norm(t): return unicodedata.normalize("NFC", str(t or "")).strip()


def valeurs_valides(s, base, valeurs, genre):
    """Vrai si Qwen a rempli chaque champ du sketch avec une valeur EXACTE des listes (le prénom suit le genre)."""
    g0 = s["interlocuteur"]["genre"]
    if genre not in ("f", "h") or (g0 in ("f", "h") and genre != g0): return False
    return all(_norm(valeurs.get(c)) in map(_norm, liste_de(base, c, genre)) for c in champs_de(s))


SYSTEME = ("Tu choisis un sketch dans une liste et tu remplis ses champs avec des valeurs prises EXACTEMENT dans les listes données. "
           "Tu n'écris aucune phrase. Réponds uniquement avec un objet JSON valide.")


def choisir(ollama, historique, base, n=None):
    """-> (sketch, valeurs, genre, origine « qwen » | « code »). Qwen choisit parmi les 3 premiers sketches autorisés ; réponse hors listes = choix du code."""
    cands = candidates(historique, base["sketches"])[:3]
    if not cands: return None, {}, "", ""
    n = sum(1 for h in historique if h.get("serie") == "B") if n is None else n
    if ollama is not None:
        offre = [{"id": s["id"], "titre": s["titre"], "champs": champs_de(s), "genre_interlocuteur": s["interlocuteur"]["genre"]} for s in cands]
        listes = {k: v for k, v in base["listes"].items()}
        demande = (f"Sketches possibles : {json.dumps(offre, ensure_ascii=False)}\nListes : {json.dumps(listes, ensure_ascii=False)}\n"
                   "Choisis un sketch. Pour chacun de ses champs, prends une valeur dans la liste du même nom (pour « nom » : nom_f si genre f, nom_h si genre h). "
                   "Si genre_interlocuteur vaut libre, choisis f ou h. "
                   'Format : {"sketch": "T01", "genre": "f", "valeurs": {"metier": "...", "nom": "..."}}')
        try:
            r = json.loads(ollama.chat(SYSTEME, demande, temperature=0.8, num_predict=200))
            s = next((x for x in cands if x["id"] == str(r.get("sketch", "")).strip()), None)
            vals = {k: _norm(v) for k, v in (r.get("valeurs") or {}).items() if k in CHAMPS}
            genre = s["interlocuteur"]["genre"] if s and s["interlocuteur"]["genre"] in ("f", "h") else str(r.get("genre", "")).strip().lower()[:1]
            if s and valeurs_valides(s, base, vals, genre): return s, {c: vals[c] for c in champs_de(s)}, genre, "qwen"
        except Exception: pass
    s = cands[0]; vals, genre = valeurs_par_defaut(s, base, n)
    return s, vals, genre, "code"


def document(s, valeurs, genre, i_fin, fin, conf, jour, heure, origine):
    """Script de la vidéo : répliques (champs remplis) + fin de Gérard face caméra ; qui parle, jeu, bruitages, retournement, décor."""
    rs = s["repliques"]; lignes = [remplir(r["texte"], valeurs) for r in rs]
    nom = valeurs.get("nom", "")
    leg = (f"{s['titre']}\n\nUn sketch de Gérard. On recrute des call callers à la commission : formulaire en bio, ou envoie un DM.\n\n{C.MENTION_IA}\n\n"
           + (conf["lignes"]["B"].get("hashtags") or "#callcaller #humour #prospection"))
    return {"jour": jour, "passage": heure, "serie": "B", "format": "sketch", "sketch": s["id"], "histoire": s["id"], "theme": s["theme"], "categorie": categorie(s),
            "formule": s["formule"], "decor": s["decor"], "variante": origine, "valeurs": valeurs,
            "interlocuteur": {"role": s["interlocuteur"]["role"], "genre": genre, "nom": nom},
            "telephone": bool(s.get("telephone")), "fin_variante": f"FIN{i_fin + 1}", "style": "classic", "sujet": s["titre"], "titre": s["titre"], "accroche": lignes[0],
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
