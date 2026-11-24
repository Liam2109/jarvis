#!/usr/bin/env python3
"""Test silencieux de la source « nouvelles entreprises » (appels-sid) : AUCUN réseau, aucune clé réelle, fichiers temporaires.  python agents\\test_nouvelles_entreprises.py
Vérifie : filtre (holding, société civile, hors rayon, ancienne entreprise, fermée), ajout avec « Nouvelle entreprise, créée le … », pas de doublon au second passage, rien sans téléphone, sans clé = rien."""
import importlib.util, json, os, socket, sys, tempfile, urllib.request
from datetime import date
os.environ["JARVIS_TEST"] = "1"
from pathlib import Path
ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import nouvelles_entreprises as NE, prospection as P, suivi as S
spec = importlib.util.spec_from_file_location("appels_sid", ICI / "appels-sid.py"); A = importlib.util.module_from_spec(spec); spec.loader.exec_module(A)


def reseau(*a, **k): raise AssertionError("appel réseau interdit dans les tests")
urllib.request.urlopen = reseau; socket.create_connection = reseau

echecs = []
def verifier(cond, msg):
    print(("  OK    " if cond else "  ECHEC ") + msg)
    if not cond: echecs.append(msg)

JOUR = "2026-11-24"; DEPUIS = "2026-08-26"
COMMUNES = {"76540": 0.0, "76231": 12.5}                     # Rouen, Darnétal ; Le Havre (76351) est hors rayon
NAF = {"43.22A": "plombier", "96.02A": "coiffeur", "56.10A": "restaurant"}


def etab(siren, nom, naf="43.22A", cree="2026-10-12", juridique="5710", commune="76540", ville="ROUEN", etat="A", cree_ul=None, siege=True):
    return {"siren": siren, "siret": siren + "00011", "dateCreationEtablissement": cree, "etablissementSiege": siege,
            "uniteLegale": {"denominationUniteLegale": nom, "categorieJuridiqueUniteLegale": juridique, "dateCreationUniteLegale": cree_ul or cree},
            "adresseEtablissement": {"codeCommuneEtablissement": commune, "libelleCommuneEtablissement": ville, "codePostalEtablissement": "76000"},
            "periodesEtablissement": [{"dateFin": None, "etatAdministratifEtablissement": etat, "activitePrincipaleEtablissement": naf}]}


REPONSE = {"header": {"curseurSuivant": "*"}, "etablissements": [
    etab("111111111", "Dupont Plomberie"),                                              # gardée
    etab("222222222", "Holding Machin", naf="64.20Z"),                                   # holding : activité non locale
    etab("333333333", "SCI Les Tilleuls", juridique="6540"),                             # société civile
    etab("444444444", "Coiffure Le Havre", naf="96.02A", commune="76351", ville="LE HAVRE"),   # hors rayon
    etab("555555555", "Ancienne Plomberie", cree="2026-10-12", cree_ul="2015-03-01"),    # unité légale ancienne (nouvel établissement seulement)
    etab("666666666", "Plomberie Fermée", etat="F"),                                     # fermée
    etab("777777777", "Chez Sans Numéro", naf="56.10A", cree="2026-09-02", ville="DARNETAL", commune="76231"),   # gardée par le filtre, mais sans téléphone
]}

print("1. Filtre Sirene (module nouvelles_entreprises)")
vus = NE.chercher("CLE-FAUSSE", DEPUIS, JOUR, COMMUNES, NAF, ["76"], appel=lambda url, entetes=None: REPONSE)
verifier(sorted(c["nom"] for c in vus) == ["Chez Sans Numéro", "Dupont Plomberie"], f"seules 2 entreprises passent le filtre ({sorted(c['nom'] for c in vus)})")
verifier(vus[0]["nom"] == "Dupont Plomberie" and vus[0]["cree"] == "2026-10-12", "la plus récente en premier, date de création gardée")
verifier(NE.distance_km(NE.ROUEN, (49.4432, 1.0993)) < 0.01 and 70 < NE.distance_km(NE.ROUEN, (49.4944, 0.1079)) < 80, "distance Rouen - Le Havre cohérente (~ 75 km)")

print("2. Intégration appels-sid (fichiers temporaires, doublures)")
tmp = Path(tempfile.mkdtemp(prefix="nouvelles-test-")); (tmp / "agents").mkdir(); (tmp / "docs").mkdir()
A.ICI, A.RACINE, A.SORTIE = tmp / "agents", tmp, tmp / "docs" / "sid"
A.CONFIG, A.ETAT, A.VERROU, A.ARRET, A.JOURNAL, A.MAPS, A.HISTORIQUE = (tmp / "agents" / "appels-sid-config.json", tmp / "agents" / "appels-sid-etat.json", tmp / "agents" / "appels-sid.verrou",
                                                          tmp / "agents" / "appels-sid.arret", tmp / "agents" / "appels-sid-journal.log", tmp / "prospects_maps.csv", tmp / "agents" / "appels-sid-historique.json")
P.TROUVES, P.DOCS, P.ICI, P.ETAT, S.FICHIER = tmp / "prospection-trouves.csv", tmp / "docs", tmp / "agents", tmp / "agents" / "prospection-etat.json", tmp / "suivi-prospects.csv"
NE.communes_proches = lambda depts, rayon, appel=None: COMMUNES
NE.chercher = lambda cle, depuis, jusqua, communes, naf, depts, **k: vus
A.dormir = lambda s: None
SITES = {"https://dupont-plomberie.fr": "Dupont Plomberie Rouen 76000 contact 02 35 62 41 64 <a href='tel:0235624164'>"}
A.lire_site = lambda url: (url, {}, SITES[url]) if url in SITES else None
A.evaluer_site = lambda url, texte: (True, 5)
P.domaines = lambda nom: ["dupont-plomberie.fr"] if "Dupont" in nom else []
P.verifie_osm = lambda texte, c: True
conf = A.cfg(); conf["insee_cle"] = "CLE-FAUSSE"; os.environ.pop("INSEE_CLE", None); os.environ["INSEE_FICHIER"] = os.path.join(os.environ.get("TEMP", "."), "insee-absent.local")
etat = A.etat_lire()

r = A._nouvelles({**conf, "insee_cle": ""}, etat, JOUR, False)
verifier(r is None and not P.TROUVES.exists(), "sans clé : rien n'est fait, rien n'est écrit")

r = A._nouvelles(conf, etat, JOUR, True)
verifier(r["ajoutees"] == 1 and not P.TROUVES.exists(), "à blanc : 1 entreprise trouvée avec téléphone, aucun fichier écrit")

r = A._nouvelles(conf, etat, JOUR, False)
lignes = P.lire_trouves()
verifier(r["ajoutees"] == 1 and len(lignes) == 1, f"1 entreprise ajoutée, 1 sans téléphone écartée (ajoutées={r['ajoutees']}, sans tél={r['sans_tel']})")
verifier(lignes and lignes[0]["note_besoin"] == "Nouvelle entreprise, créée le 12/10/2026", "Détail fiche « Nouvelle entreprise, créée le 12/10/2026 »")
verifier(lignes and "INSEE" in lignes[0]["source"] and lignes[0]["telephone"] == "02 35 62 41 64", "source INSEE notée, numéro lu sur le site public")
verifier(etat["nouvelles"]["jours"].get(JOUR) == 1, "compteur du jour (tableau de bord) = 1")

r2 = A._nouvelles(conf, etat, JOUR, False)
verifier(r2["ajoutees"] == 0 and len(P.lire_trouves()) == 1, "second passage : aucun doublon")

cand = [c for c in A.candidats(etat, jour=JOUR) if c["constat"].startswith(A.NOUVELLE)]
verifier(len(cand) == 1 and cand[0]["metier"] == "plombier", "la ligne entre dans la réserve de Sid (métier plombier) avec son constat « Nouvelle entreprise »")

journal = A.JOURNAL.read_text(encoding="utf-8") if A.JOURNAL.exists() else ""
verifier("nouvelles |" in journal and "0235624164" not in journal.replace(" ", ""), "une ligne au journal, sans numéro de téléphone")
verifier(not os.environ.get("INSEE_CLE") and "CLE-FAUSSE" not in journal, "aucune clé dans le journal")

print()
print("ÉCHEC : " + str(len(echecs)) if echecs else "Tous les tests nouvelles-entreprises passent.")
sys.exit(1 if echecs else 0)
