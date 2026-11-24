#!/usr/bin/env python3
"""Source « nouvelles entreprises » de l'agent appels-sid (24/11/2026) : entreprises créées depuis moins de 3 mois autour de Rouen, d'après l'API Sirene officielle de l'INSEE
(gratuite, mais avec une CLÉ : portail-api.insee.fr ; l'API « Recherche d'entreprises » de data.gouv, sans clé, n'a aucun filtre de date de création).
Ce module ne fait que chercher et filtrer (aucune écriture, aucun envoi) ; appels-sid.py ajoute le téléphone, écarte les doublons et écrit dans prospection-trouves.csv.
Gardées : établissement siège actif, société commerciale ou entreprise individuelle (catégories juridiques 1xxx et 5xxx : jamais société civile 65xx, ni association, ni administration),
activité = l'un des métiers locaux d'appels-sid (NAF_SID : donc jamais holding 64.20Z ni location de biens), commune à moins de `rayon_km` de Rouen, unité légale elle aussi créée depuis `depuis`."""
import json, math, time, urllib.error, urllib.parse, urllib.request

ROUEN = (49.4432, 1.0993)
URL_SIRET = "https://api.insee.fr/api-sirene/3.11/siret"
URL_COMMUNES = "https://geo.api.gouv.fr/communes?departement={}&fields=code,centre&format=json&geometry=centre"
UA = "LM-MULTI-SERVICES-prospection"
CATEGORIES_OK = ("1", "5")


class ErreurInsee(Exception): pass


def distance_km(a, b):
    """Distance à vol d'oiseau (haversine) entre deux points (latitude, longitude)."""
    p1, p2 = math.radians(a[0]), math.radians(b[0]); dp = p2 - p1; dl = math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 12742 * math.asin(math.sqrt(h))


def appel_json(url, entetes=None, ouvrir=urllib.request.urlopen, dormir=time.sleep):
    """GET JSON ; jusqu'à 3 nouveaux essais après 3, 10 puis 30 s si l'API refuse (429, 5xx) ou coupe. 401/403 : ErreurInsee (clé refusée), jamais réessayé."""
    rq = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json", **(entetes or {})})
    for essai, attente in enumerate((0, 3, 10, 30)):
        if attente: dormir(attente)
        try:
            with ouvrir(rq, timeout=60) as r: return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (401, 403): raise ErreurInsee(f"clé INSEE refusée (HTTP {e.code})")
            if e.code == 404: return {}                       # l'API Sirene répond 404 quand rien ne correspond
            if e.code not in (429, 500, 502, 503, 504) or essai == 3: raise ErreurInsee(f"API Sirene : HTTP {e.code}")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            if essai == 3: raise ErreurInsee(f"API injoignable ({type(e).__name__})")


def communes_proches(depts, rayon_km, appel=appel_json):
    """{code INSEE de commune: distance en km} des communes à moins de rayon_km de Rouen (geo.api.gouv.fr, gratuit, sans clé)."""
    out = {}
    for d in depts:
        for c in appel(URL_COMMUNES.format(d)) or []:
            xy = ((c.get("centre") or {}).get("coordinates")) or []
            if len(xy) == 2 and distance_km(ROUEN, (xy[1], xy[0])) <= rayon_km: out[str(c["code"])] = round(distance_km(ROUEN, (xy[1], xy[0])), 1)
    return out


def _nom(e, ul, per):
    for v in (per.get("enseigne1Etablissement"), per.get("denominationUsuelleEtablissement"), ul.get("denominationUniteLegale"), ul.get("denominationUsuelle1UniteLegale")):
        if v and "[ND]" not in v: return " ".join(str(v).split())
    prenom = ul.get("prenomUsuelUniteLegale") or ul.get("prenom1UniteLegale") or ""; nom = ul.get("nomUsageUniteLegale") or ul.get("nomUniteLegale") or ""
    return " ".join(f"{prenom} {nom}".split()) if nom and "[ND]" not in f"{prenom}{nom}" else ""


def retenir(e, depuis, communes, naf_metier):
    """Un établissement de la réponse Sirene -> dict de candidat, ou None s'il n'est pas à garder (voir la docstring du module)."""
    ul = e.get("uniteLegale") or {}; adr = e.get("adresseEtablissement") or {}; per = next((p for p in e.get("periodesEtablissement") or [] if not p.get("dateFin")), {})
    metier = naf_metier.get(str(per.get("activitePrincipaleEtablissement") or ""))
    if not metier or per.get("etatAdministratifEtablissement") != "A" or str(e.get("etablissementSiege")).lower() != "true": return None
    if str(ul.get("categorieJuridiqueUniteLegale") or "")[:1] not in CATEGORIES_OK: return None
    if str(e.get("dateCreationEtablissement") or "") < depuis or str(ul.get("dateCreationUniteLegale") or "") < depuis: return None
    commune = str(adr.get("codeCommuneEtablissement") or "")
    nom = _nom(e, ul, per)
    if commune not in communes or not nom or not e.get("siren"): return None
    return {"siren": str(e["siren"]), "siret": str(e.get("siret") or e["siren"]), "nom": nom, "ville": str(adr.get("libelleCommuneEtablissement") or "").title(),
            "cp": str(adr.get("codePostalEtablissement") or ""), "cree": str(e["dateCreationEtablissement"]), "naf": str(per["activitePrincipaleEtablissement"]), "metier": metier,
            "km": communes[commune]}


def chercher(cle, depuis, jusqua, communes, naf_metier, depts, pages_max=8, appel=appel_json, dormir=time.sleep):
    """Établissements-sièges créés entre `depuis` et `jusqua` (AAAA-MM-JJ), un département à la fois (1000 par page, curseur), filtrés par retenir(). -> liste de candidats, du plus récent au plus ancien.
    Lève ErreurInsee (clé refusée, API en panne). Au plus pages_max pages par département."""
    out = []; entetes = {"X-INSEE-Api-Key-Integration": cle}
    for d in depts:
        q = f"dateCreationEtablissement:[{depuis} TO {jusqua}] AND etablissementSiege:true AND codePostalEtablissement:{d}*"; curseur = "*"
        for page in range(pages_max):
            if page: dormir(2)
            data = appel(f"{URL_SIRET}?" + urllib.parse.urlencode({"q": q, "nombre": 1000, "curseur": curseur}), entetes) or {}
            etabs = data.get("etablissements") or []
            out += [c for c in (retenir(e, depuis, communes, naf_metier) for e in etabs) if c]
            suivant = (data.get("header") or {}).get("curseurSuivant")
            if not etabs or not suivant or suivant == curseur: break
            curseur = suivant
    return sorted(out, key=lambda c: c["cree"], reverse=True)
