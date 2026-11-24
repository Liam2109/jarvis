"""Test silencieux : la carte « Agents » du gros PC reprend l'état vivant du serveur (outils/agents-json.py › lire_serveur, fusionner_serveur). Aucun réseau, aucun fichier écrit.
  python tests/test_agents_serveur.py
"""
import importlib.util, os, sys
from datetime import datetime
from pathlib import Path

os.environ["JARVIS_TEST"] = "1"
s = importlib.util.spec_from_file_location("aj", Path(__file__).resolve().parent.parent / "outils" / "agents-json.py")
AJ = importlib.util.module_from_spec(s); s.loader.exec_module(AJ)
QUAND = datetime(2026, 11, 23, 19, 0)
ok = True


def verifier(cond, texte):
    global ok
    print(("OK  " if cond else "ÉCHEC ") + texte); ok = ok and cond


verifier(AJ.lire_serveur("SERVEUR-X") is None, "JARVIS_TEST=1 : aucun appel réseau")

# --- fusion pure -------------------------------------------------------------------------------------------------------------------------------
local = [{"nom": "relances", "statut": "inactif", "dernier_passage": None, "journal": [], "note": "docs/agents/x.md", "chiffre_du_jour": {"libelle": "x", "valeur": None}},
         {"nom": "inconnu-du-serveur", "statut": "inactif", "dernier_passage": None}]
photo = {"genere_le": "2026-11-23 18:55:00", "agents": [{"nom": "relances", "statut": "actif", "dernier_passage": "2026-11-23 08:30:01", "dernier_resultat": "relances",
         "derniere_erreur": None, "journal": [["2026-11-23 08:30", "relances"]], "chiffre_du_jour": {"libelle": "actions du jour", "valeur": 3},
         "tourne_sur_ce_pc": False, "planifie_sur_ce_pc": True, "suspendu": False, "note": "autre chemin"}, "pas un dict"]}
n = AJ.fusionner_serveur(local, photo)
verifier(n == 1, "un seul agent mis à jour (l'autre est absent de la photo)")
verifier(local[0]["dernier_passage"] == "2026-11-23 08:30:01" and local[0]["statut"] == "actif", "dernier passage et statut repris du serveur")
verifier(local[0]["journal"] == [["2026-11-23 08:30", "relances"]] and local[0]["chiffre_du_jour"]["valeur"] == 3, "journal et chiffre du jour repris du serveur")
verifier(local[0]["note"] == "docs/agents/x.md", "la note reste celle de ce PC")
verifier(local[1]["dernier_passage"] is None and not local[1].get("vu_sur_serveur"), "agent absent de la photo : inchangé")

# --- construire() comme sur le gros PC : machine active = autre machine -----------------------------------------------------------------------
lire_orig = AJ.lire_json
AJ.lire_json = lambda p, d=None: {"machine_active": "SERVEUR-X"} if Path(p).name == "b2b.local.json" else lire_orig(p, d)
os.environ["COMPUTERNAME"] = "GROS-PC"
try:
    sans = AJ.construire(QUAND)
    verifier(sans["serveur_lu"] is False and "injoignable" in sans["source"], "serveur injoignable : on le dit, états locaux gardés")
    noms = [a["nom"] for a in sans["agents"]]
    cible = "relances" if "relances" in noms else noms[0]
    photo2 = {"genere_le": "2026-11-23 18:55:00", "agents": [{"nom": cible, "statut": "actif", "dernier_passage": "2026-11-23 08:30:01", "journal": [["2026-11-23 08:30", "ok"]],
              "chiffre_du_jour": {"libelle": "actions du jour", "valeur": 7}, "tourne_sur_ce_pc": False, "planifie_sur_ce_pc": True}]}
    avec = AJ.construire(QUAND, photo_serveur=photo2)
    a = next(x for x in avec["agents"] if x["nom"] == cible)
    verifier(avec["serveur_lu"] is True and avec["serveur_photo"] == "2026-11-23 18:55:00" and "lu sur le serveur" in avec["source"], "photo du serveur lue : source et date annoncées")
    verifier(a["dernier_passage"] == "2026-11-23 08:30:01" and a["chiffre_du_jour"]["valeur"] == 7, f"« {cible} » : passage et chiffre du jour du serveur (pas écrasés par les fichiers locaux)")
finally:
    AJ.lire_json = lire_orig

# --- statuts gris / vert / orange / rouge, catégorie par superviseur, extrait de note (23/11/2026) -------------------------------------------------
v = lambda **k: AJ.voyant(k, "2026-11-23")[0]
verifier(v(statut="erreur", dernier_passage="2026-11-23 08:00:00") == "rouge" and v(suspendu=True) == "rouge", "erreur ou suspendu : rouge, même passé aujourd'hui")
verifier(v(etat_liste="désactivé", dernier_passage="2026-11-23 08:00:00") == "gris" and v(etat_liste="à construire") == "gris", "désactivé ou à construire : gris")
verifier(v(etat_liste="en place", dernier_passage=None) == "gris", "en place mais jamais passé : gris")
verifier(v(etat_liste="en place", dernier_passage="2026-11-23 08:30:01") == "vert", "passé aujourd'hui : vert")
verifier(v(etat_liste="en place", dernier_passage="2026-11-22 19:30:00") == "orange", "passé avant aujourd'hui : orange")
verifier(all(a["voyant"] in ("gris", "vert", "orange", "rouge") and a["categorie"] in AJ.SUPERVISEURS for a in sans["agents"]), "chaque agent a un voyant à quatre couleurs et une catégorie connue")
cat = {a["nom"]: a["categorie"] for a in sans["agents"]}
verifier(cat.get("superviseur-vente") == "Vente" and cat.get("appels-sid") == "Prospection" and cat.get("superviseur-prospection") == "Prospection" and not {"superviseur-sites", "superviseur-mail", "superviseur-videos"} & set(cat) and cat.get("panne-alerte") == "Jarvis (CEO)", "catégories : un superviseur par domaine, le reste sous Jarvis (CEO)")
ex = AJ.extrait_note("relances")
verifier(bool(ex) and "GENERE" not in ex and "---" not in ex and "Contrat" not in ex and len(ex) <= 905, "extrait de note : mission et étapes, sans en-tête ni commentaire généré")
verifier(AJ.extrait_note("agent-qui-n-existe-pas") is None, "note absente : None")

print("\nTOUT VERT" if ok else "\nÉCHEC"); sys.exit(0 if ok else 1)
