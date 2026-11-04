"""Zone de prospection de Liam : des vagues de départements, de la plus proche de Rouen à la plus lointaine (décision du 02/11/2026).
Vague 1 = Seine-Maritime (76) et Eure (27) ; vague 2 = Calvados, Manche, Orne, Oise, Somme, Eure-et-Loir ; vague 3 = Paris et petite couronne, Yvelines, Val-d'Oise, Sarthe, Mayenne, Ille-et-Vilaine ;
vague 4 = le reste de la France métropolitaine. Le programme n'ouvre la vague suivante que si la vague en cours a moins de `seuil_vague` (15) prospects utilisables par jour (voir prospection.py › vagues).
« Hors zone » = hors des vagues ouvertes (VAGUE_MAX, fixé par prospection.py depuis son état ; 1 par défaut).
Avec un code postal à 5 chiffres : le département donne la vague. Sans code postal mais avec des coordonnées (OpenStreetMap) : le département de la préfecture (ou de la grande ville côtière) la plus proche, à 100 km au plus.
Une fiche sans coordonnées ni code postal n'est acceptée que si sa commune est connue de la zone."""
import math, re, unicodedata

ROUEN = (49.4431, 1.0993)
VAGUES = {   # numéro: départements, dans l'ordre où l'annuaire les parcourt (les trois premiers, 76, 27, 14, ne changent pas : les curseurs de prospection-etat.json restent valables)
    1: ["76", "27"],
    2: ["14", "50", "61", "60", "80", "28"],
    3: ["75", "92", "93", "94", "78", "95", "72", "53", "35"],
}
CENTRES = {   # département: (latitude, longitude) de la préfecture, pour classer par proximité de Rouen et situer une fiche sans code postal
    "01": (46.205, 5.226), "02": (49.564, 3.620), "03": (46.566, 3.334), "04": (44.092, 6.236), "05": (44.559, 6.079), "06": (43.710, 7.262), "07": (44.735, 4.599), "08": (49.773, 4.720),
    "09": (42.965, 1.605), "10": (48.297, 4.074), "11": (43.213, 2.351), "12": (44.350, 2.575), "13": (43.296, 5.370), "14": (49.183, -0.371), "15": (44.926, 2.444), "16": (45.649, 0.156),
    "17": (46.160, -1.152), "18": (47.081, 2.399), "19": (45.267, 1.768), "2A": (41.919, 8.738), "2B": (42.697, 9.451), "21": (47.322, 5.041), "22": (48.514, -2.760), "23": (46.171, 1.871),
    "24": (45.184, 0.722), "25": (47.238, 6.024), "26": (44.933, 4.892), "27": (49.027, 1.151), "28": (48.447, 1.489), "29": (48.000, -4.102), "30": (43.837, 4.360), "31": (43.605, 1.444),
    "32": (43.646, 0.586), "33": (44.838, -0.579), "34": (43.611, 3.877), "35": (48.117, -1.678), "36": (46.811, 1.691), "37": (47.394, 0.685), "38": (45.189, 5.725), "39": (46.675, 5.555),
    "40": (43.890, -0.500), "41": (47.586, 1.335), "42": (45.440, 4.387), "43": (45.043, 3.885), "44": (47.218, -1.553), "45": (47.903, 1.909), "46": (44.448, 1.441), "47": (44.200, 0.621),
    "48": (44.518, 3.500), "49": (47.478, -0.563), "50": (49.116, -1.090), "51": (48.957, 4.363), "52": (48.111, 5.139), "53": (48.070, -0.769), "54": (48.692, 6.184), "55": (48.773, 5.161),
    "56": (47.659, -2.760), "57": (49.119, 6.176), "58": (46.990, 3.159), "59": (50.629, 3.057), "60": (49.430, 2.082), "61": (48.432, 0.091), "62": (50.292, 2.781), "63": (45.777, 3.087),
    "64": (43.295, -0.371), "65": (43.233, 0.078), "66": (42.699, 2.895), "67": (48.573, 7.752), "68": (48.079, 7.358), "69": (45.764, 4.836), "70": (47.620, 6.155), "71": (46.307, 4.829),
    "72": (48.006, 0.200), "73": (45.564, 5.917), "74": (45.899, 6.129), "75": (48.857, 2.352), "76": (49.443, 1.099), "77": (48.540, 2.660), "78": (48.801, 2.130), "79": (46.324, -0.459),
    "80": (49.894, 2.296), "81": (43.929, 2.148), "82": (44.018, 1.355), "83": (43.124, 5.928), "84": (43.949, 4.806), "85": (46.670, -1.426), "86": (46.580, 0.340), "87": (45.834, 1.262),
    "88": (48.173, 6.450), "89": (47.798, 3.567), "90": (47.640, 6.863), "91": (48.629, 2.443), "92": (48.892, 2.207), "93": (48.909, 2.439), "94": (48.790, 2.455), "95": (49.036, 2.076),
}
ANCRES = [("76", 49.4938, 0.1077), ("76", 49.9229, 1.0775), ("76", 49.7570, 0.3740), ("14", 49.1460, 0.2290), ("50", 49.6337, -1.6221), ("28", 48.7370, 1.3670), ("60", 49.4179, 2.8261), ("80", 50.1060, 1.8350), ("35", 48.6493, -2.0257)]   # villes que la préfecture la plus proche situerait dans le mauvais département : Le Havre, Dieppe, Fécamp, Lisieux, Cherbourg, Dreux, Compiègne, Abbeville, Saint-Malo
COMMUNES_CAEN = {"caen", "mondeville", "ifs", "herouville-saint-clair", "colombelles", "bretteville-sur-odon", "demouville", "verson", "carpiquet", "cormelles-le-royal", "fleury-sur-orne", "saint-contest", "epron"}   # commune seule : vague 2
VILLES_DEPT = {"rouen": "76", "le-havre": "76", "deville-les-rouen": "76", "bonsecours": "76", "sotteville-les-rouen": "76", "boos": "76", "sainte-marie-des-champs": "76", "saint-martin-du-manoir": "76",
               "yvetot": "76", "elbeuf": "76", "dieppe": "76", "mont-saint-aignan": "76", "evreux": "27", "louviers": "27", "caen": "14", "cherbourg-en-cotentin": "50", "alencon": "61", "beauvais": "60", "amiens": "80", "chartres": "28"}   # communes sans ambiguïté : département déduit d'une fiche sans code postal
VAGUE_MAX = 1   # vagues ouvertes (1 à 4) ; fixé au démarrage et à chaque cycle par prospection.py (état › vagues)


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def distance_m(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6371000 * math.asin(math.sqrt(a))


def depts_vague(n):
    """Départements de la vague n. La vague 4 : tout le reste de la métropole, du plus proche au plus lointain de Rouen."""
    if n in VAGUES: return list(VAGUES[n])
    pris = {d for v in VAGUES.values() for d in v}
    return sorted((d for d in CENTRES if d not in pris), key=lambda d: distance_m(*ROUEN, *CENTRES[d]))


def departements_ouverts(vague_max=None):
    """Départements des vagues ouvertes, dans l'ordre (vague 1 d'abord)."""
    return [d for n in range(1, (VAGUE_MAX if vague_max is None else vague_max) + 1) for d in depts_vague(n)]


def vague_de_dept(d):
    """1 à 4 ; 0 si le département est inconnu (outre-mer, étranger)."""
    for n, ds in VAGUES.items():
        if d in ds: return n
    return 4 if d in CENTRES else 0


def dept_de_cp(cp):
    cp = (cp or "").strip()
    if not re.fullmatch(r"\d{5}", cp): return ""
    if cp[:2] == "20": return "2A" if int(cp) < 20200 else "2B"
    return cp[:2] if cp[:2] in CENTRES else ""


def vague_de_cp(cp):
    return vague_de_dept(dept_de_cp(cp))


def vague_coord(lat, lon):
    """Vague du département de la préfecture la plus proche (à 100 km au plus), 0 sinon."""
    d, r = min([(d, distance_m(lat, lon, *c)) for d, c in CENTRES.items()] + [(d, distance_m(lat, lon, la, lo)) for d, la, lo in ANCRES], key=lambda x: x[1])
    return vague_de_dept(d) if r <= 100000 else 0


def ouvrir(n):
    global VAGUE_MAX
    VAGUE_MAX = max(1, min(4, int(n)))


def cp_hors_zone(cp, vague_max=None):
    """Vrai seulement si un code postal à 5 chiffres est donné ET qu'il est hors des vagues ouvertes (ou hors des vagues 1 à vague_max donné ; 4 = toute la France) ; code postal absent : on ne conclut pas."""
    cp = (cp or "").strip()
    if not re.fullmatch(r"\d{5}", cp): return False
    return not 1 <= vague_de_cp(cp) <= (VAGUE_MAX if vague_max is None else vague_max)


def cp_depuis_adresse(adresse):
    m = re.search(r"\b(\d{5})\b", adresse or "")
    return m.group(1) if m else ""


def dans_zone(cp="", ville="", lat=None, lon=None, villes_ok=(), vague_max=None):
    """Vrai si l'entreprise est dans une vague ouverte (ou dans les vagues 1 à vague_max donné). Code postal d'abord, puis coordonnées, puis commune connue."""
    vm = VAGUE_MAX if vague_max is None else vague_max; cp = (cp or "").strip()
    if re.fullmatch(r"\d{5}", cp): return not cp_hors_zone(cp, vm)
    try:
        if lat is not None and lon is not None and str(lat) != "" and str(lon) != "": return 1 <= vague_coord(float(lat), float(lon)) <= vm
    except (TypeError, ValueError): pass
    v = norm(ville)
    return bool(v) and (v in villes_ok or (vm >= 2 and v in COMMUNES_CAEN))


def cle_proximite(cp="", ville=""):
    """Clé de tri « proche de Rouen d'abord » : (vague, distance de la préfecture du département à Rouen en km). Sans code postal reconnu : en dernier."""
    d = dept_de_cp(cp)
    if not d and norm(ville) in COMMUNES_CAEN: d = "14"
    if not d: d = VILLES_DEPT.get(norm(ville), "")
    if not d or d not in CENTRES: return (9, 0)
    return (vague_de_dept(d), round(distance_m(*ROUEN, *CENTRES[d]) / 1000))
