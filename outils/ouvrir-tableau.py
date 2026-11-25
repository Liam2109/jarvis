#!/usr/bin/env python3
"""Lanceur de l'icône « Jarvis - Mon entreprise » sur le gros PC : ouvre le tableau de bord du SERVEUR (http://<serveur>:8080/, réseau local seulement).
Adresses essayées dans l'ordre : le NOM du serveur (machine_active, suit l'adresse même si le routeur la change), puis serveur_adresse de B2B\\agents\\b2b.local.json
(lu sans jamais être affiché). Un serveur est « joignable » si son port 8080 répond en moins de 2 secondes.
Serveur injoignable : un message le dit clairement et l'ancienne copie locale (dashboard\\index.html, régénérée par agents-json.py) est ouverte à la place.
Secret : AUCUN secret dans le lien, l'historique ou un journal. La page et tous ses agents sont en lecture libre sur le réseau local ; pour les boutons LinkedIn et Cerveau, la page
demande une fois le secret du serveur (B2B\\config\\dashboard.local, sur le serveur) et le garde dans le navigateur.
  pythonw outils/ouvrir-tableau.py            ouvre le navigateur
  python  outils/ouvrir-tableau.py --adresse  affiche seulement l'adresse retenue (sans rien ouvrir)
  python  outils/ouvrir-tableau.py --regler 192.168.1.12   le serveur a changé d'IP : teste l'adresse puis l'écrit dans serveur_adresse (seule config, jamais figée ailleurs)
"""
import ctypes, json, os, re, socket, subprocess, sys, threading, time
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
    """Hôte joignable le plus prioritaire, sinon None. Les candidats sont testés en même temps (un nom que le routeur résout vers de
    mauvaises adresses coûterait sinon plusieurs secondes d'attente avant de passer à l'IP) ; l'ordre de la liste reste l'ordre de priorité."""
    test = test or joignable; res = {}
    def essai(h): res[h] = bool(test(h, port, delai))
    fils = [threading.Thread(target=essai, args=(h,), daemon=True) for h in candidats]
    for f in fils: f.start()
    fin = time.monotonic() + delai + 0.5   # attente totale plafonnée : un nom qui traîne ne retarde jamais l'ouverture de plus de ce délai
    for h, f in zip(candidats, fils):
        f.join(max(0.0, fin - time.monotonic()))
        if res.get(h): return h
    return None


def regler(adr, fichier=LOCAL, port=PORT, delai=2.0, test=None):
    """Seul endroit où l'adresse du serveur est écrite : la clé serveur_adresse de b2b.local.json (les autres clés et le BOM sont conservés, rien n'est affiché).
    Refuse une adresse qui ne répond pas sur le port du tableau. Renvoie True si la clé a été écrite."""
    adr = (adr or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.\-]{0,252}", adr) or not (test or joignable)(adr, port, delai): return False
    p = Path(fichier)
    try: brut = p.read_bytes()
    except OSError: return False
    try: c = json.loads(brut.decode("utf-8-sig"))
    except ValueError: return False
    if not isinstance(c, dict): return False
    c["serveur_adresse"] = adr
    p.write_bytes((b"\xef\xbb\xbf" if brut.startswith(b"\xef\xbb\xbf") else b"") + json.dumps(c, ensure_ascii=False, indent=2).encode("utf-8") + b"\n")
    return True


def adresse(hote, port=PORT): return "http://%s:%d/" % (hote, port)


def prevenir(texte):
    if os.name == "nt": ctypes.windll.user32.MessageBoxW(0, texte, "Jarvis - Mon entreprise", 0x40)
    else: print(texte, file=sys.stderr)


def main(argv=None, ouvrir=None):
    argv = sys.argv[1:] if argv is None else argv
    ouvrir = ouvrir or (lambda cible: os.startfile(cible))
    if "--regler" in argv:   # python outils/ouvrir-tableau.py --regler 192.168.1.12 : l'IP du serveur a changé (écrite une seule fois, après test)
        i = argv.index("--regler") + 1; ok = i < len(argv) and regler(argv[i])
        print("serveur_adresse mis à jour" if ok else "adresse refusée : elle ne répond pas sur le port %d (ou b2b.local.json illisible)" % PORT); return 0 if ok else 1
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
