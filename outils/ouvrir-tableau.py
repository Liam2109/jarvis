#!/usr/bin/env python3
"""Lanceur de l'icône « Jarvis - Mon entreprise » sur le gros PC : ouvre le tableau de bord du SERVEUR (http://<serveur>:8080/, réseau local seulement).
Adresses essayées dans l'ordre : le NOM du serveur (machine_active, suit l'adresse même si le routeur la change), puis serveur_adresse de B2B\\agents\\b2b.local.json
(lu sans jamais être affiché). Un serveur est « joignable » si son port 8080 répond en moins de 2 secondes.
Serveur injoignable : un message le dit clairement et l'ancienne copie locale (dashboard\\index.html, régénérée par agents-json.py) est ouverte à la place.
Secret : AUCUN secret dans le lien, l'historique ou un journal. La page et ses 18 agents sont en lecture libre sur le réseau local ; pour les boutons LinkedIn et Cerveau, la page
demande une fois le secret du serveur (B2B\\config\\dashboard.local, sur le serveur) et le garde dans le navigateur.
  pythonw outils/ouvrir-tableau.py            ouvre le navigateur
  python  outils/ouvrir-tableau.py --adresse  affiche seulement l'adresse retenue (sans rien ouvrir)
"""
import ctypes, json, os, socket, subprocess, sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
PORT = 8080
LOCAL = RACINE / "B2B" / "agents" / "b2b.local.json"


def hotes(fichier=LOCAL):
    """Noms/adresses candidats, sans doublon (seules les clés machine_active et serveur_adresse sont lues)."""
    try: c = json.loads(Path(fichier).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError): c = {}
    vus = []
    for cle in ("machine_active", "serveur_adresse"):
        v = c.get(cle) if isinstance(c, dict) else None
        if isinstance(v, str) and v.strip() and v.strip() not in vus: vus.append(v.strip())
    return vus


def joignable(hote, port=PORT, delai=2.0):
    try:
        with socket.create_connection((hote, port), timeout=delai): return True
    except OSError: return False


def choisir(candidats, port=PORT, delai=2.0, test=None):
    """Premier hôte dont le port répond, sinon None."""
    test = test or joignable
    for h in candidats:
        if test(h, port, delai): return h
    return None


def adresse(hote, port=PORT): return "http://%s:%d/" % (hote, port)


def prevenir(texte):
    if os.name == "nt": ctypes.windll.user32.MessageBoxW(0, texte, "Jarvis - Mon entreprise", 0x40)
    else: print(texte, file=sys.stderr)


def main(argv=None, ouvrir=None):
    argv = sys.argv[1:] if argv is None else argv
    ouvrir = ouvrir or (lambda cible: os.startfile(cible))
    cand = hotes(); hote = choisir(cand)
    if "--adresse" in argv:
        print(adresse(hote) if hote else "injoignable : " + (", ".join(cand) or "aucune adresse")); return 0 if hote else 1
    if hote: ouvrir(adresse(hote)); return 0
    # serveur injoignable : on régénère la copie locale (comptes seulement) puis on l'ouvre en le disant
    try: subprocess.run([sys.executable, str(RACINE / "outils" / "agents-json.py")], timeout=90, creationflags=0x08000000 if os.name == "nt" else 0)
    except (OSError, subprocess.SubprocessError): pass
    prevenir("Le serveur du tableau de bord (%s, port %d) ne répond pas : il est peut-être éteint ou hors du réseau.\n\nJ'ouvre l'ANCIENNE copie locale, dont les chiffres viennent de ce PC seulement." % (", ".join(cand) or "adresse inconnue", PORT))
    ouvrir(str(RACINE / "dashboard" / "index.html")); return 2


if __name__ == "__main__":
    sys.exit(main())
