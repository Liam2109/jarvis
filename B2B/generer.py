# Étape 2 : une maquette HTML par prospect, à partir de maquette-plombier.html
# Lancer :  python generer.py prospects.csv    (CSV avec colonnes nom;metier;ville;telephone;note;avis;site)
# Ne génère que pour les lignes dont la colonne "site" est vide. Sortie : dossier maquettes\
import csv, html, os, re, sys, unicodedata

def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

modele = open("maquette-plombier.html", encoding="utf-8").read()
os.makedirs("maquettes", exist_ok=True)
n = 0
for r in csv.DictReader(open(sys.argv[1], encoding="utf-8-sig"), delimiter=";"):
    if r.get("site", "").strip(): continue
    nom = r["nom"].title()
    vals = {"NOM": nom, "METIER": r["metier"], "VILLE": r["ville"].title(),
            "TEL": r.get("telephone") or "", "NOTE": r.get("note") or "—", "AVIS": r.get("avis") or "—"}
    out = modele
    for k, v in vals.items():
        out = out.replace("{{" + k + "}}", html.escape(str(v)))
    open(f"maquettes/{slug(nom)}.html", "w", encoding="utf-8").write(out)
    n += 1
print(n, "maquettes dans le dossier maquettes\\")
