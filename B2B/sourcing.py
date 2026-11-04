# Étape 1 : liste d'artisans autour de Rouen via l'API publique "Recherche d'entreprises" (gratuite, sans clé).
# Lancer :  python sourcing.py   -> écrit prospects.csv
# Ensuite : compléter téléphone / note / avis / site avec Outscraper (Google Maps), puis garder ceux SANS site.
import csv, json, time, urllib.parse, urllib.request

METIERS = {            # code NAF -> métier affiché (à changer : n'importe quel secteur, pas que le bâtiment)
    "43.22A": "plombier-chauffagiste",
    "43.21A": "électricien",
    "43.91B": "couvreur",
    "43.31Z": "plâtrier",
    "43.34Z": "peintre",
    "43.32A": "menuisier",
    "41.20A": "maçon",
}
CODES_POSTAUX = ["76000","76100","76130","76140","76150","76160","76170","76230","76240","76250",
                 "76300","76320","76400","76500","76520","76530","76550","76600","76650","76800",
                 "76190","76680","76690","76710","76770"]   # Rouen + alentours (à ajuster)

def appel(naf, cp, page):
    q = urllib.parse.urlencode({"activite_principale": naf, "code_postal": cp, "etat_administratif": "A",
                                "per_page": 25, "page": page})
    req = urllib.request.Request("https://recherche-entreprises.api.gouv.fr/search?" + q,
                                 headers={"User-Agent": "LM-MULTI-SERVICES-prospection"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

vus, lignes = set(), []
for naf, metier in METIERS.items():
    for cp in CODES_POSTAUX:
        page = 1
        while True:
            try:
                data = appel(naf, cp, page)
            except Exception as e:
                print("erreur", naf, cp, page, e); break
            for r in data.get("results", []):
                siren = r["siren"]
                if siren in vus: continue
                vus.add(siren)
                s = r.get("siege", {})
                lignes.append({
                    "siren": siren, "nom": r.get("nom_complet", ""), "metier": metier,
                    "adresse": s.get("adresse", ""), "cp": s.get("code_postal", ""),
                    "ville": s.get("libelle_commune", ""), "creation": s.get("date_creation", ""),
                    "effectif": r.get("tranche_effectif_salarie") or "",
                    "telephone": "", "note": "", "avis": "", "site": "",   # à remplir via Google Maps
                })
            if page >= data.get("total_pages", 1) or page >= 4: break
            page += 1
            time.sleep(0.2)          # limite API : 7 appels/seconde
        time.sleep(0.2)

with open("prospects.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(lignes[0].keys()), delimiter=";")
    w.writeheader(); w.writerows(lignes)
print(len(lignes), "entreprises écrites dans prospects.csv")
