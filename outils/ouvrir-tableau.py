"""Ouvre le tableau de bord du serveur (http://<serveur>:8080) depuis un autre PC du réseau.
Essaie dans l'ordre : le NOM réseau du serveur (machine_active), ce nom + « .home », puis l'IP de secours (serveur_adresse) de B2B\\agents\\b2b.local.json.
  python outils/ouvrir-tableau.py            ouvre le navigateur sur la première adresse qui répond
  python outils/ouvrir-tableau.py --test     affiche seulement quelle adresse répond (ouvre rien)
"""
import json, os, sys, webbrowser
from pathlib import Path
from urllib.request import urlopen

RACINE = Path(__file__).resolve().parent.parent
PORT = 8080


def adresses():
    try: local = json.loads((RACINE / "B2B" / "agents" / "b2b.local.json").read_text(encoding="utf-8-sig"))
    except Exception: local = {}
    nom = str(local.get("machine_active", "") or "").strip(); ip = str(local.get("serveur_adresse", "") or "").strip()
    return [h for h in dict.fromkeys([nom, nom + ".home" if nom else "", ip]) if h]


def joignable(hote, delai=4):
    try:
        with urlopen(f"http://{hote}:{PORT}/agents.json", timeout=delai) as r: return r.status == 200
    except Exception: return False


def main():
    essais = adresses()
    if not essais: print("Aucune adresse : machine_active manque dans B2B\\agents\\b2b.local.json."); return 2
    for h in essais:
        if joignable(h):
            print(f"OK : http://{h}:{PORT}/")
            if "--test" not in sys.argv: webbrowser.open(f"http://{h}:{PORT}/")
            return 0
        print(f"injoignable : {h}")
    print("Serveur injoignable : vérifier que le serveur est allumé et la règle de pare-feu du port 8080 (outils\\taches-dashboard-serveur.ps1)."); return 1


if __name__ == "__main__": sys.exit(main())
