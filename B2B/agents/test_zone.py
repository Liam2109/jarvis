#!/usr/bin/env python3
"""Tests silencieux de la zone de prospection (aucun réseau, fichiers temporaires, rien d'envoyé) : python agents\\test_zone.py
Zone de Liam par vagues de départements (02/11/2026, vague 2 resserrée à la Normandie le 10/11/2026) : vague 1 = 76 et 27 ; 2 = 14, 50, 61 (Normandie complète avec la vague 1, rien de plus) ;
3 = 60, 80, 28 puis Paris et petite couronne, 78, 95, 72, 53, 35 ; 4 = le reste de la France. Hors zone = hors des vagues ouvertes."""
import os, sys, tempfile, json, csv
os.environ.setdefault("JARVIS_TEST", "1")
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import zone as ZN
import prospection as X

# --- zone.py : vagues, codes postaux, coordonnées, communes ---
assert ZN.VAGUES[1] == ["76", "27"] and ZN.VAGUES[2] == ["14", "50", "61"] and ZN.VAGUES[3] == ["60", "80", "28", "75", "92", "93", "94", "78", "95", "72", "53", "35"]
assert set(ZN.VAGUES[1]) | set(ZN.VAGUES[2]) == {"76", "27", "14", "50", "61"}                        # vagues 1+2 = exactement la Normandie, jamais plus
v4 = ZN.depts_vague(4); assert len(v4) == 96 - 17 and not {"76", "27", "14", "35"} & set(v4) and "2A" in v4 and "34" in v4 and "971" not in v4
assert v4 == sorted(v4, key=lambda d: ZN.distance_m(*ZN.ROUEN, *ZN.CENTRES[d])) and v4[0] in ("91", "77", "62")      # le reste de la France : du plus proche au plus lointain de Rouen
assert [ZN.vague_de_cp(c) for c in ("76000", "27400", "14000", "50100", "61000", "60000", "80000", "28000", "75001", "92100", "78000", "95000", "72000", "53000", "35000", "34000", "20100", "20200", "13001", "97100", "99999", "")] == [1, 1, 2, 2, 2, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 4, 4, 4, 4, 0, 0, 0]
assert ZN.VAGUE_MAX == 1                                                                                                  # par défaut seule la vague 1 est ouverte
for cp in ("76000", "76600", "76500", "76200", "27000", "27400"): assert ZN.dans_zone(cp=cp) and not ZN.cp_hors_zone(cp), cp
for cp in ("14000", "14100", "50100", "61000", "60000", "80000", "28000", "75001", "35000", "34000", "31000", "30000", "20100", "11120"): assert not ZN.dans_zone(cp=cp) and ZN.cp_hors_zone(cp), cp   # vagues fermées
assert not ZN.cp_hors_zone("") and not ZN.cp_hors_zone("abc")            # sans code postal on ne conclut pas
ZN.ouvrir(2)
for cp in ("14000", "14100", "50100", "61000", "76000"): assert ZN.dans_zone(cp=cp), cp
for cp in ("60000", "80000", "28000", "75001", "35000", "72000", "34000", "13001"): assert not ZN.dans_zone(cp=cp), cp   # Oise/Somme/Eure-et-Loir : hors Normandie, pas ouverts avec la seule vague 2
assert ZN.dans_zone(ville="Caen") and not ZN.dans_zone(ville="Marguerittes")
ZN.ouvrir(3); assert ZN.dans_zone(cp="75001") and ZN.dans_zone(cp="35000") and ZN.dans_zone(cp="95000") and not ZN.dans_zone(cp="34000")
assert ZN.dans_zone(cp="60000") and ZN.dans_zone(cp="80000") and ZN.dans_zone(cp="28000")                                # vague 3 ouverte : hors Normandie, mais désormais ouvert
ZN.ouvrir(4); assert ZN.dans_zone(cp="34000") and ZN.dans_zone(cp="20100") and ZN.dans_zone(cp="13001") and not ZN.dans_zone(cp="97100") and not ZN.dans_zone(cp="99999")
ZN.ouvrir(1)
assert ZN.dans_zone(cp="14000", vague_max=2) and not ZN.dans_zone(cp="14000") and ZN.cp_hors_zone("34000", 3) and not ZN.cp_hors_zone("34000", 4)   # vague_max explicite
assert [ZN.dans_zone(lat=la, lon=lo) for _, la, lo in [("Rouen", 49.4431, 1.0993), ("Elbeuf", 49.2873, 0.9895), ("Le Havre", 49.4938, 0.1077), ("Évreux", 49.0270, 1.1511), ("Dieppe", 49.9229, 1.0775), ("Yvetot", 49.6167, 0.75), ("Louviers", 49.2150, 1.17)]] == [True] * 7
assert not any(ZN.dans_zone(lat=la, lon=lo) for _, la, lo in [("Caen", 49.1829, -0.3707), ("Lisieux", 49.1460, 0.2290), ("Cherbourg", 49.6337, -1.6221), ("Paris", 48.8566, 2.3522), ("Amiens", 49.8941, 2.2958), ("Montpellier", 43.6119, 3.8772), ("Nîmes", 43.8367, 4.3601), ("Luchon", 42.79, 0.594)])
assert ZN.vague_coord(49.1829, -0.3707) == 2 and ZN.vague_coord(48.8566, 2.3522) == 3 and ZN.vague_coord(43.61, 3.87) == 4 and ZN.vague_coord(51.5, -0.1) == 0   # Londres : trop loin d'une préfecture
assert not ZN.dans_zone(ville="Marguerittes") and ZN.dans_zone(ville="Eslettes", villes_ok={"eslettes"})   # sans coordonnées ni code postal : commune connue seulement
assert ZN.cp_depuis_adresse("12 rue X, 34000 Montpellier, France") == "34000"
assert not ZN.dans_zone(cp="34000", lat=49.44, lon=1.09)                  # le code postal prime sur les coordonnées
# classement par proximité de Rouen : vague 1 d'abord, puis la plus proche
cp_tri = ["34000", "76000", "75001", "27000", "14000", "35000", "", "60000"]
tri = sorted(cp_tri, key=lambda c: ZN.cle_proximite(c)); assert tri[:3] == ["76000", "27000", "14000"] and tri[3:6] == ["60000", "75001", "35000"] and tri[6:] == ["34000", ""], tri   # 14000 seul en vague 2 (Normandie) ; 60000 passe en vague 3, derrière
assert ZN.cle_proximite("", "Le Havre")[0] == 1 and ZN.cle_proximite("", "Yvetot")[0] == 1 and ZN.cle_proximite("", "Amiens")[0] == 3   # département déduit de la ville ; Amiens (80) est hors Normandie, vague 3
assert ZN.cle_proximite("", "Caen")[0] == 2 and ZN.cle_proximite("", "Inconnue") == (9, 0)

# --- configuration : départements des vagues ouvertes, zones Overpass, villes Places ---
assert X.DEPARTEMENTS[:8] == ["76", "27", "14", "50", "61", "60", "80", "28"] and len(X.DEPARTEMENTS) == 96 and X.depts_ouverts() == ["76", "27"], X.depts_ouverts()
ZN.ouvrir(2); assert X.depts_ouverts() == ["76", "27", "14", "50", "61"]; ZN.ouvrir(1)   # Normandie complète, rien d'autre
assert [z["id"] for z in X.zones_osm()] == ["rouen-40km", "dept-76", "dept-27"], [z["id"] for z in X.zones_osm()]
ZN.ouvrir(3); ids = [z["id"] for z in X.zones_osm()]; assert ids[3:6] == ["dept-14", "dept-50", "dept-61"] and "dept-35" in ids and "dept-34" not in ids
assert "Caen" in X.villes_places() and "Rennes" in X.villes_places(); ZN.ouvrir(1)
assert X.villes_places() == X.PLACES_VILLES[1] and "Caen" not in X.villes_places() and "Paris" not in X.villes_places()

# --- OpenStreetMap : une réponse mêlant Normandie et Occitanie ne garde que la Normandie ---
els = [{"type": "node", "id": 1, "lat": 49.44, "lon": 1.09, "tags": {"name": "Elec Rouen", "addr:city": "Rouen", "addr:postcode": "76000"}},
       {"type": "node", "id": 2, "lat": 43.61, "lon": 3.87, "tags": {"name": "Elec Montpellier", "addr:city": "Montpellier", "addr:postcode": "34000"}},
       {"type": "node", "id": 3, "lat": 43.60, "lon": 1.44, "tags": {"name": "Elec Toulouse", "addr:city": "Toulouse", "addr:postcode": "31000"}},
       {"type": "node", "id": 4, "lat": 42.79, "lon": 0.59, "tags": {"name": "Elec Luchon", "addr:city": "Luchon", "addr:postcode": "31110"}},
       {"type": "way", "id": 5, "center": {"lat": 43.84, "lon": 4.45}, "tags": {"name": "Elec Marguerittes", "addr:city": "Marguerittes"}},                        # sans code postal : coordonnées du centre
       {"type": "node", "id": 6, "lat": 49.49, "lon": 0.11, "tags": {"name": "Elec Havre", "addr:city": "Le Havre"}},
       {"type": "node", "id": 7, "tags": {"name": "Elec Saint-Béat", "addr:city": "Saint-Béat-Lez", "addr:postcode": "31440"}}]      # sans coordonnées : code postal
noms = [c["nom"] for c in X.candidats_osm({"elements": els}, "électricien")]
assert noms == ["Elec Rouen", "Elec Havre"], noms
ZN.ouvrir(4); assert len(X.candidats_osm({"elements": els}, "électricien")) == 7; ZN.ouvrir(1)             # toute la France ouverte : tout passe

# --- annuaire officiel : un siège hors zone n'entre jamais dans le tampon ---
etat = {"vus": {}, "tampon": {}}
data = {"results": [{"siren": "1", "nom_complet": "A", "siege": {"code_postal": "76100", "libelle_commune": "ROUEN"}},
                    {"siren": "2", "nom_complet": "B", "siege": {"code_postal": "34000", "libelle_commune": "MONTPELLIER"}},
                    {"siren": "3", "nom_complet": "C", "siege": {"code_postal": "14100", "libelle_commune": "LISIEUX"}},
                    {"siren": "4", "nom_complet": "D", "siege": {"code_postal": "14000", "libelle_commune": "CAEN"}}]}
X._alimenter(etat, "43.21A", "électricien", data, "14")
assert not etat["tampon"].get("43.21A"), etat["tampon"]                                              # le Calvados est en vague 2, fermée
ZN.ouvrir(2); X._alimenter(etat, "43.21A", "électricien", data, "14")
assert [x["siren"] for x in etat["tampon"]["43.21A"]] == ["3", "4"], etat["tampon"]                   # Lisieux et Caen : tout le Calvados ; Montpellier (34) jamais dans le 14
ZN.ouvrir(1)
X._alimenter(etat, "43.22A", "plombier", data, "76")
assert [x["siren"] for x in etat["tampon"]["43.22A"]] == ["1"], etat["tampon"]

# --- Google Places : adresse hors zone rejetée ---
pl = {"places": [{"id": "a", "displayName": {"text": "Salon Rouen"}, "formattedAddress": "3 rue X, 76000 Rouen, France"},
                 {"id": "b", "displayName": {"text": "Salon Toulouse"}, "formattedAddress": "3 rue Y, 31000 Toulouse, France"},
                 {"id": "c", "displayName": {"text": "Salon Cherbourg"}, "formattedAddress": "1 quai Z, 50100 Cherbourg-en-Cotentin, France"}]}
assert [c["nom"] for c in X.candidats_places(pl, "coiffeur")] == ["Salon Rouen"]
ZN.ouvrir(2); assert [c["nom"] for c in X.candidats_places(pl, "coiffeur")] == ["Salon Rouen", "Salon Cherbourg"]; ZN.ouvrir(1)

# --- garde-fou commun : motif « hors zone » ---
ligne = {"nom": "Elec Nîmes", "ville": "Nîmes", "cp": "30000", "email": "a@b.fr", "site_actuel": ""}
assert X.motif_ligne(ligne, [], set(), set(), set(), set()).startswith("hors zone")
assert X.motif_ligne({**ligne, "ville": "Rouen", "cp": "76000", "nom": "Elec Rouen"}, [], set(), set(), set(), set()) == ""

# --- lot du jour : ne part que si les DEUX boîtes ont leur quota, même après l'heure limite ---
from datetime import datetime
bl = lambda box, i: {"id": f"p{i}|rouen", "statut": "à valider", "meta": {"type": "email", "box": box}}
X.boites = lambda: ["a@x", "b@x"]
conf = {**X.DEFAUT, "par_boite_par_jour": 3, "heure_limite": "17:00"}
etat = {"lots_box": {}, "publies": [], "lots_discord": {}}
tard = datetime(2026, 10, 30, 17, 30)
blocs = [bl("a@x", i) for i in range(3)] + [bl("b@x", i + 10) for i in range(2)]
r = X.lots_a_poster(etat, blocs, conf, tard); assert len(r) == 2 and r[1][2] is True   # sans l'option : le lot incomplet partait après 17 h
conf2 = {**conf, "lot_attendre_les_deux_boites": True}
assert X.lots_a_poster(etat, blocs, conf2, tard) == []                                    # une boîte incomplète : personne ne part
blocs2 = blocs + [bl("b@x", 99)]
assert sorted(b for b, _, _ in X.lots_a_poster(etat, blocs2, conf2, tard)) == ["a@x", "b@x"]   # les deux complètes : les deux partent

# --- nettoyage : retire les « à valider » et le suivi « à contacter » hors zone, garde les déjà contactés, marque « hors zone » ---
tmp = Path(tempfile.mkdtemp(prefix="zone-test-"))
X.ETAT, X.TROUVES, X.MESSAGES = tmp / "etat.json", tmp / "trouves.csv", tmp / "messages.md"
X.S.FICHIER = X.R.SUIVI = tmp / "suivi.csv"
L = lambda nom, ville, cp, st="préparé": {k: "" for k in X.COLS} | {"nom": nom, "ville": ville, "cp": cp, "statut": st, "siren": nom[-1] + "00", "metier": "électricien", "email": nom.lower().replace(" ", "") + "@ex.fr"}
rows = [L("Elec A", "Rouen", "76000"), L("Elec B", "Bruxelles", "99100"), L("Elec C", "Saint-Denis", "97400"), L("Elec D", "Nîmes", "99999"), L("Elec E", "Caen", "14000"), L("Elec F", "Montpellier", "34000")]
X.ecrire_trouves(rows)
cle = lambda l: X.S.cle(l)
with open(X.S.FICHIER, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=X.S.COLS, delimiter=";"); w.writeheader()
    for l in rows: w.writerow({"nom": l["nom"], "ville": l["ville"], "email": l["email"], "statut": "à contacter", "metier": "électricien"})
    w.writerow({"nom": "Elec D", "ville": "Nîmes", "email": "x@ex.fr", "statut": "envoyé", "date_envoi": "2026-10-29"})   # déjà contacté : jamais effacé
X.S.ecrire([r for r in X.S.lire() if not (r["nom"] == "Elec D" and r["statut"] == "à contacter")])
auj = X.aujourdhui()
def bloc(l, box):
    m = {"type": "email", "box": box, "email": l["email"], "nom": l["nom"], "ville": l["ville"], "lot": auj}
    return f"## {l['nom']} — {l['ville']}\n<!-- id:{cle(l)} -->\n<!-- meta:{X.meta_texte(m)} -->\n**Statut : à valider**\n\ntexte\n"
X.MESSAGES.write_text("# Messages\n\n" + "\n".join(bloc(l, "a@x" if i % 2 else "b@x") for i, l in enumerate(rows)), encoding="utf-8")
X.ETAT.write_text(json.dumps({"lots": {auj: {"a@x": 2, "b@x": 3}}, "vus": {}}), encoding="utf-8")
r = X.cmd_zone(True, X.DEFAUT); assert r["trouves_hors_zone"] == 4 and sum(r["blocs_retires"].values()) == 4 and X.lire_trouves()[1]["statut"] == "préparé"   # à blanc : rien d'écrit
r = X.cmd_zone(False, X.DEFAUT)
assert r["trouves_hors_zone"] == 4 and r["suivi_retires"] == 3 and len(r["suivi_deja_contactes"]) == 1, r                       # B, C et F (Montpellier, hors Normandie) retirés ; D déjà contacté, gardé et signalé
assert sorted(b["meta"]["nom"] for b in X.lire_blocs(X.MESSAGES.read_text(encoding="utf-8"))) == ["Elec A", "Elec E"]
assert {l["nom"]: l["statut"] for l in X.lire_trouves()} == {"Elec A": "préparé", "Elec B": "hors zone", "Elec C": "hors zone", "Elec D": "hors zone", "Elec E": "préparé", "Elec F": "hors zone"}   # Caen (Normandie) gardé ; Montpellier hors des 5 départements autorisés (14/11/2026) : retiré
suivi = {x["nom"]: x["statut"] for x in X.S.lire()}; assert "Elec B" not in suivi and "Elec C" not in suivi and "Elec F" not in suivi and suivi["Elec D"] == "envoyé" and suivi["Elec A"] == "à contacter", suivi
e = json.loads(X.ETAT.read_text(encoding="utf-8")); assert e["vus"]["B00"] == "hors zone" and sum(e["lots"][auj].values()) == 2   # a@x : 2 - 3 blocs (B, D, F) -> 0 ; b@x : 3 - 1 (C) -> 2
assert X.cmd_zone(False, X.DEFAUT)["suivi_retires"] == 0                                                                        # idempotent

# --- ouverture des vagues : seulement si la vague en cours a moins de 15 prospects utilisables par jour ET que la recherche n'y trouve plus rien ---
X.ETAT, X.TROUVES = tmp / "etat-vagues.json", tmp / "trouves-vagues.csv"
X.S.FICHIER = X.R.SUIVI = tmp / "suivi-vagues.csv"; X.S.ecrire([])
ZN.ouvrir(1); auj = X.aujourdhui(); hier = str(X.date.today() - X.timedelta(days=1)); conf = {**X.DEFAUT, "seuil_vague": 15}
def lg(i, cp, **kw): return {k: "" for k in X.COLS} | {"nom": f"Ent {i}", "ville": "V" + str(i), "cp": cp, "email": f"e{i}@ex.fr", "metier": "électricien", "statut": "trouvé", "date_collecte": auj, "siren": str(i)} | kw
X.ecrire_trouves([lg(i, "76000") for i in range(14)] + [lg(99, "75001")] + [lg(100, "76000", date_collecte=hier), lg(101, "76000", statut="hors zone"), lg(102, "76000", email="", telephone=""), lg(103, "76000", email="", telephone="02 35 00 00 03")])
assert X.utilisables_par_vague(X.lire_trouves(), auj) == {1: 15, 2: 0, 3: 1, 4: 0}                       # 14 avec e-mail + 1 avec téléphone seul ; hier, hors zone et sans contact : non comptés
X.ecrire_trouves([lg(i, "76000") for i in range(14)] + [lg(99, "75001"), lg(100, "76000", date_collecte=hier), lg(101, "76000", statut="refusé"), lg(102, "76000", email="", telephone="")])
assert X.utilisables_par_vague(X.lire_trouves(), auj) == {1: 14, 2: 0, 3: 1, 4: 0} and X.utilisables_par_vague(X.lire_trouves())[1] == 15
assert X.vague_suivante_si_besoin(conf, auj, epuisee=False) == 0 and X.vagues_etat(X.etat_lire())["ouverte"] == 1 and ZN.VAGUE_MAX == 1   # la recherche trouve encore : on attend
assert X.vague_suivante_si_besoin(conf, auj) == 2 and ZN.VAGUE_MAX == 2 and X.etat_lire()["vagues"]["ouvertures"]["2"] == {"jour": auj, "utilisables_vague_precedente": 14}   # 14 < 15 : vague 2
X.ecrire_trouves([lg(i, "14000") for i in range(15)])                                                      # la vague en cours (2) donne 15 utilisables aujourd'hui : on reste dessus
assert X.vague_suivante_si_besoin(conf, auj) == 0 and ZN.VAGUE_MAX == 2
X.ecrire_trouves([lg(i, "14000") for i in range(14)] + [lg(50 + i, "76000") for i in range(30)])           # la vague 1 en donne beaucoup, mais c'est la vague en cours (2) qui compte
assert X.vague_suivante_si_besoin(conf, auj) == 0 and ZN.VAGUE_MAX == 2 and X.vagues_etat(X.etat_lire())["ouverte"] == 2   # plafond (14/11/2026) : jamais au-delà de la Normandie
assert X.vague_suivante_si_besoin({**conf, "seuil_vague": 0}, auj) == 0
ZN.ouvrir(1); X.appliquer_vagues(); assert ZN.VAGUE_MAX == 2                                                # relu depuis l'état au démarrage
X.etat_ecrire({**X.etat_lire(), "vagues": {"ouverte": 4, "ouvertures": {}}}, False); X.appliquer_vagues(); assert ZN.VAGUE_MAX == 2   # un ancien état « vague 4 » reste plafonné
r = X.cmd_vagues(conf); assert r["ouverte"] == 2 and r["utilisables_total"][2] == 14 and r["utilisables_total"][1] == 30
ZN.ouvrir(1)

# --- liste d'appels : jamais hors des vagues ouvertes, toujours classée par proximité de Rouen (vague 1 d'abord) ---
X.DOCS = tmp / "docs-vagues"; X.DOCS.mkdir(exist_ok=True)
tel = lambda i, cp, v: {k: "" for k in X.COLS} | {"nom": f"Appel {i}", "ville": v, "cp": cp, "metier": "électricien", "telephone": f"02 35 00 00 {i:02d}", "statut": X.STATUTS_TEL[0], "osm": f"node/9{i}", "modele": "sans-site"}
pool = [tel(1, "34000", "Montpellier"), tel(2, "76000", "Rouen"), tel(3, "75001", "Paris"), tel(4, "27000", "Évreux"), tel(5, "14000", "Caen"), tel(6, "35000", "Rennes"), tel(7, "60000", "Beauvais")]
confa = {**X.DEFAUT, "appels_par_jour": 100}
ZN.ouvrir(1); assert [l["ville"] for l in X.choisir_appels(pool, {}, confa, set())] == ["Rouen", "Évreux"]                    # vague 1 seule
ZN.ouvrir(2); assert [l["ville"] for l in X.choisir_appels(pool, {}, confa, set())] == ["Rouen", "Évreux", "Caen"]            # Beauvais (60, hors Normandie) pas encore ouvert
ZN.ouvrir(4); assert [l["ville"] for l in X.choisir_appels(pool, {}, confa, set())] == ["Rouen", "Évreux", "Caen", "Beauvais", "Paris", "Rennes", "Montpellier"]   # Caen (Normandie, vague 2) avant Beauvais (vague 3), même si Beauvais est géographiquement plus proche
assert [l["ville"] for l in X.choisir_appels(pool, {}, {**confa, "appels_par_jour": 3}, set())] == ["Rouen", "Évreux", "Caen"]   # le plafond garde les plus proches (vague d'abord, distance ensuite)
ZN.ouvrir(1)
import shutil; shutil.rmtree(tmp, ignore_errors=True)
print("OK : tous les tests de zone passent")
