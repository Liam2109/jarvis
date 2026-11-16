#!/usr/bin/env python3
"""Ligne B (compte recrutement de call callers), 17/11/2026 : petites histoires écrites à la main dans Videos\\histoires-base.md, puis appel à l'action.
Qwen ne fait que varier prénoms, métiers et détails d'une histoire choisie ; il n'en invente jamais : une variante trop éloignée de l'original (mots, longueur,
nombre de répliques) ou qui contient un interdit est refusée, et l'histoire d'origine est utilisée telle quelle.
L'appel à l'action est ajouté par le code (5 variantes tournantes, même sens) ; toute histoire qui le rate ou contient un interdit est refusée par verifier()."""
import json, re, sys, unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import commun as C   # noqa: E402

HISTOIRES = C.VIDEOS / "histoires-base.md"
TITRE = re.compile(r"^## ([HL]\d{2}) \| ([^|]+)\| ([^|]+)\| (.+?)\s*$")
LIGNE = re.compile(r"^- (accroche|mise en place|tension|pivot|retournement|chute) \| (\w+) \| ([\w-]+) \| (.+?)\s*$")
CTA_TITRE = "## Appels à l'action"
CTA_OK = [re.compile(r"\bcall callers?\b", re.I), re.compile(r"\bcommission\b", re.I), re.compile(r"\bbio\b", re.I), re.compile(r"\bDM\b")]
RDV15 = re.compile(r"(quinze|15)\s*min|rendez-vous de (quinze|15)", re.I)
# Leçons de vente (17/11/2026) : ni gain chiffré ou promis, ni « mon closer gagne », ni statistique, ni numéro privé de décideur
INTERDITS_LECONS = re.compile(r"closer gagne|statisti|selon (une|les) [ée]tudes?|des gens (d[ée]crochent|r[ée]pondent)|taux de|"
                              r"num[ée]ro (priv[ée]|perso)|portable (du|d'un|de son) (patron|d[ée]cideur|g[ée]rant|dirigeant)|ligne directe du", re.I)
# Répartition des vidéos de la ligne B par catégorie (thème des histoires)
CATEGORIES = {"lecon": ({"leçon"}, 0.4), "comedie": ({"téléphone", "peur du non", "premier appel", "le trac", "petit extra à côté"}, 0.4),
              "autre": ({"entrepreneuriat", "vie quotidienne"}, 0.2)}


def categorie(theme):
    return next((c for c, (themes, _) in CATEGORIES.items() if theme in themes), "autre")


VRAIES_PERSONNES = re.compile(r"\b(macron|musk|zuckerberg|bezos|jobs|mbapp[ée]|zidane|squeezie|inoxtag|cyprien|norman|tibo|booba|jul|aya nakamura)\b", re.I)


def lire(texte=None):
    """-> (histoires, appels à l'action). Une histoire : {id, theme, decor, titre, lignes: [{role, expr, pose, texte}]}."""
    texte = HISTOIRES.read_text(encoding="utf-8") if texte is None else texte
    hs, cta, cur, dans_cta = [], [], None, False
    for l in texte.splitlines():
        l = l.rstrip()
        if l.startswith("## "):
            dans_cta = l.startswith(CTA_TITRE); m = TITRE.match(l); cur = None
            if m: cur = {"id": m.group(1), "theme": m.group(2).strip(), "decor": m.group(3).strip(), "titre": m.group(4).strip(), "lignes": []}; hs.append(cur)
            continue
        if dans_cta and l.startswith("- "): cta.append(l[2:].strip()); continue
        m = LIGNE.match(l)
        if cur is not None and m: cur["lignes"].append({"role": m.group(1), "expr": m.group(2), "pose": m.group(3), "texte": m.group(4)})
    return hs, cta


def candidates(historique, histoires, fenetre=20):
    """Histoires dans l'ordre où les jouer : jamais faites d'abord (ordre du fichier), puis faites il y a le plus longtemps ;
    aucune des `fenetre` dernières vidéos de la ligne B n'est rejouée (liste vide si toutes y sont)."""
    faites = [h.get("histoire") for h in historique if h.get("histoire")]
    recentes = set(faites[-fenetre:])
    derniere = {x: i for i, x in enumerate(faites)}
    theme = {h["id"]: h["theme"] for h in histoires}
    vues = [categorie(theme.get(x, "")) for x in faites[-fenetre:]]
    retard = {c: part - (vues.count(c) / len(vues) if vues else 0) for c, (_, part) in CATEGORIES.items()}   # catégorie la plus en retard sur sa part d'abord
    return sorted((h for h in histoires if h["id"] not in recentes),
                  key=lambda h: (-retard[categorie(h["theme"])], derniere.get(h["id"], -1)))


def choisir(historique, histoires, fenetre=20):
    c = candidates(historique, histoires, fenetre)
    return c[0] if c else None


def appel_action(historique, ctas):
    """Variante suivante (tournante) de l'appel à l'action."""
    n = sum(1 for h in historique if h.get("serie") == "B")
    return ctas[n % len(ctas)]


def _mots_pleins(t):
    s = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().lower()
    return {m for m in re.findall(r"[a-z]+", s) if len(m) > 3}


def proche_de(original, variante):
    """Vrai si la variante reste la même réplique (métiers, prénoms secondaires, détails changés) : la moitié au moins des mots pleins gardés,
    longueur de 70 à 140 %, et Gérard (personnage récurrent de la série) garde toujours son prénom."""
    a, b = _mots_pleins(original), _mots_pleins(variante)
    n0, n1 = len(original.split()), len(variante.split())
    if "Gérard" in original and "Gérard" not in variante: return False
    return bool(a) and len(a & b) / len(a) >= 0.5 and 0.7 <= n1 / max(n0, 1) <= 1.4


def verifier(lignes, cta, conf, S):
    """Problèmes d'une histoire prête (répliques + appel à l'action) ; vide = acceptée. S = module scripts (mêmes garde-fous que les autres scripts)."""
    pb = []
    if len(lignes) < 3: pb.append("structure : accroche, mise en place ou tension, retournement attendus")
    if not cta or not all(r.search(cta) for r in CTA_OK): pb.append("appel à l'action manquant ou incomplet (call callers, commission, formulaire en bio, DM)")
    tout = lignes + [cta or ""]
    for t in tout:
        for rx, quoi in ((S.NOMBRES, "nombre ou chiffre"), (S.INTERDITS, "formulation interdite"), (S.INTERDITS_B, "formulation interdite"), (S.MOLLES, "phrase molle"),
                         (S.DIDASCALIES, "mise en scène"), (S.ADRESSE, "adresse épelée"), (RDV15, "rendez-vous de 15 minutes"), (VRAIES_PERSONNES, "vraie personne"),
                         (INTERDITS_LECONS, "interdit des leçons")):
            m = rx.search(t)
            if m: pb.append(f"{quoi} (« {m.group(0)} »)")
        lieu = S.lieu_interdit(t, conf)
        if lieu: pb.append(f"lieu interdit (« {lieu} »)")
        faux = S.public_faux(t, "B")
        if faux: pb.append(f"mauvais public (« {faux} ») : tutoyer le spectateur")
    if lignes and len(C.mots_de(lignes[0])) > 10: pb.append("accroche trop longue (10 mots au plus, 2 secondes)")
    return sorted(set(pb))


def varier(ollama, h, consignes):
    """Qwen change prénoms, métiers et détails, ligne par ligne. -> (répliques, "qwen" | "original"). Toute ligne trop éloignée = histoire d'origine."""
    orig = [l["texte"] for l in h["lignes"]]
    demande = ("Voici une petite histoire écrite à la main, une réplique par ligne :\n" + "\n".join(f"{i + 1}. {t}" for i, t in enumerate(orig)) +
               "\nRéécris-la en gardant le prénom Gérard et en changeant SEULEMENT un métier, un prénom secondaire ou un petit détail (objet, aliment, animal, pièce de la maison). Garde le même nombre de "
               "lignes, le même ordre, la même chute, presque les mêmes mots. Aucun chiffre, aucune ville, aucune personne célèbre. "
               'Réponds en JSON : {"lignes": ["...", "..."]}')
    try:
        r = json.loads(ollama.chat(consignes, demande, temperature=0.5, num_predict=500))
        v = r.get("lignes") if isinstance(r, dict) else None
    except (ValueError, KeyError, OSError): v = None
    if isinstance(v, list) and len(v) == len(orig) and all(isinstance(x, str) and proche_de(o, x) for o, x in zip(orig, v)):
        return [x.strip() for x in v], "qwen"
    return orig, "original"


OUVERTURES = ["Tu connais Gérard ?", "Encore Gérard.", "Gérard, épisode du jour.", "Petite histoire de bureau.", "Ça, c'est Gérard."]
STRUCTURES = ("classique", "ouverture", "resserree")
FENETRE = 20   # aucune histoire rejouée et aucune vidéo trop proche dans les 20 dernières vidéos de la ligne B


DUREE_MAX_S = 34.0   # marge sous les 35 s de la règle


def duree_estimee(repliques):
    """Durée finale estimée (s) d'une vidéo stick-stage de la ligne B, appel à l'action et carte de 2 s compris.
    Calée le 17/11/2026 sur deux rendus réels (5 répliques / 68 mots = 32,4 s ; 7 répliques / 62 mots = 36,0 s) : chaque réplique coûte des pauses et un plan."""
    mots = sum(len(C.mots_de(x)) for x in repliques)
    return round(0.34 * mots + 2.8 * len(repliques) - 4.7, 1)


def structure_qui_tient(h, lignes, cta, n_b):
    """La structure tournante si la vidéo tient sous DUREE_MAX_S, sinon la plus courte des autres. -> (répliques, rôles, structure, durée estimée)"""
    essais = []
    for k in range(len(STRUCTURES)):
        l2, r2, s = varier_structure(h, lignes, n_b + k)
        d = duree_estimee(l2 + [cta])
        if d <= DUREE_MAX_S: return l2, r2, s, d
        essais.append((d, l2, r2, s))
    d, l2, r2, s = min(essais, key=lambda x: x[0]); return l2, r2, s, d


def varier_structure(h, lignes, n_b):
    """Structure de la vidéo, tournante (n_b = nombre de vidéos B déjà faites) : classique ; ouverture (une courte réplique avant l'accroche) ;
    resserrée (deux répliques de tension fusionnées, ou mise en place et tension). -> (répliques, rôles, structure)"""
    roles = [l["role"] for l in h["lignes"]]; lignes, roles = list(lignes), list(roles)
    s = STRUCTURES[n_b % len(STRUCTURES)]
    if s == "ouverture":
        lignes.insert(0, OUVERTURES[(n_b // len(STRUCTURES)) % len(OUVERTURES)]); roles.insert(0, "ouverture")
    elif s == "resserree":
        i = next((k for k in range(1, len(roles) - 1) if roles[k] in ("mise en place", "tension") and roles[k + 1] == "tension"), None)
        if i is None: s = "classique"
        else: lignes[i] = lignes[i].rstrip() + " " + lignes.pop(i + 1); roles.pop(i + 1)
    return lignes, roles, s


def trop_proche(texte, anciens, seuil=0.8):
    """Vrai si la vidéo reprend (80 % des mots pleins ou plus, dans les deux sens) le texte d'une des vidéos récentes."""
    a = _mots_pleins(texte)
    for b in map(_mots_pleins, anciens):
        if a and b and len(a & b) / min(len(a), len(b)) >= seuil: return True
    return False


def textes_recents(dossier, n=FENETRE):
    """Texte complet des n dernières vidéos de la ligne B (scripts\\*.json)."""
    docs = []
    for p in sorted(Path(dossier).glob("*.json")) if Path(dossier).exists() else []:
        try: d = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError): continue
        if isinstance(d, dict) and d.get("serie") == "B": docs.append(" ".join(d.get("scenes", [])[:-1]))
    return docs[-n:]


def document(h, lignes, cta, conf, jour, heure, origine, roles=None, structure="classique", fin_variante=""):
    """Script de la vidéo (même forme que les autres scripts) + jeu de scène, décor, chute, histoire."""
    roles = roles or [l["role"] for l in h["lignes"]]
    jeu_par_role = {}
    for l in h["lignes"]: jeu_par_role.setdefault(l["role"], []).append([l["expr"], l["pose"]])
    pris, jeu = {}, []
    for r in roles:   # le jeu de scène suit le rôle de chaque réplique (une ouverture : Gérard regarde, neutre)
        lst = jeu_par_role.get(r) or [["deadpan", "idle"]]; k = pris.get(r, 0); jeu.append(lst[min(k, len(lst) - 1)]); pris[r] = k + 1
    i_chute = roles.index("retournement") if "retournement" in roles else (roles.index("chute") if "chute" in roles else len(lignes) - 1)
    leg = (f"{h['titre']}\n\nUne histoire de Gérard. On recrute des call callers à la commission : formulaire en bio, ou envoie un DM.\n\n{C.MENTION_IA}\n\n"
           + (conf["lignes"]["B"].get("hashtags") or "#callcaller #histoire #humour"))
    return {"jour": jour, "passage": heure, "serie": "B", "histoire": h["id"], "theme": h["theme"], "categorie": categorie(h["theme"]), "decor": h["decor"], "variante": origine,
            "structure": structure, "fin_variante": fin_variante, "style": "classic", "sujet": h["titre"], "titre": h["titre"], "accroche": lignes[0], "scenes": lignes + [cta],
            "jeu": jeu + [["happy", "wave"]], "punchline": i_chute, "legende": leg,
            "mots": sum(len(C.mots_de(x)) for x in lignes + [cta]), "modele": conf["modele"]}
