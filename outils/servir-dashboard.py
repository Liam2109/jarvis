#!/usr/bin/env python3
"""Sert le tableau de bord en LECTURE SEULE : uniquement le dossier dashboard\\ (jamais le reste du dépôt), GET/HEAD, aucun listage de dossier.
SEULES écritures (24/11/2026) : POST /api/linkedin {id, action} (cases cochées de la rubrique LinkedIn) et POST /api/cerveau {id, action} (accepter, refuser, garder, abandonner une proposition du cerveau). Sécurité (audit du 24/11/2026) : réservée à la machine elle-même (127.0.0.1 / ::1) OU à un en-tête
X-Jarvis-Secret égal au secret du serveur (B2B/config/dashboard.local, hors git, créé au premier démarrage, jamais affiché) ; en-tête X-Jarvis et JSON obligatoires, corps limité à 512 octets, id de 8 caractères
hexadécimaux et action d'une liste fermée vérifiés AVANT toute lecture de fichier ; aucun chemin ne vient de la requête (module et état fixes) ; une écriture à la fois. data/leads.js et data/relais.js (téléphones de prospects) ne sont servis qu'à la machine elle-même ou avec ?k=SECRET ; data/linkedin.js et data/cerveau.js se lisent sans secret (25/11/2026).

  python outils/servir-dashboard.py [--port 8080] [--hote 0.0.0.0]
Sur le serveur, lancé par la tâche « Jarvis-Tableau-Service » (voir outils\\taches-dashboard-serveur.ps1). Ouvrir http://<serveur>:8080/ depuis le réseau local.
À l'ouverture de la page, les données sont régénérées si elles ont plus d'une minute (outils\\agents-json.py, comptes seulement).
"""
import argparse, hmac, importlib.util, json, re, secrets, subprocess, sys, threading, time
from urllib.parse import parse_qs, urlsplit
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
DOSSIER = RACINE / "dashboard"
PERMIS = {"index.html", "agents.js", "agents.json", "docs.js", "data/linkedin.js", "data/cerveau.js",
          "ventes.js", "data/historique.js", "data/historique-appels.js", "data/cockpit.js", "data/leads.js", "data/relais.js", "data/appels.js"}   # 25/11/2026 : les chiffres de la page (comptes) étaient en 404 depuis le serveur
PROTEGES = {"data/leads.js", "data/relais.js"}   # numéros de téléphone des prospects : machine elle-même ou secret. 25/11/2026 : LinkedIn et Cerveau se LISENT sans secret depuis le réseau local (le secret ne reste exigé que pour les POST qui agissent)
SECRET_FICHIER = RACINE / "B2B" / "config" / "dashboard.local"
TAILLE_MAX = 512
ID_OK = re.compile(r"[0-9a-f]{8}\Z")
ACTIONS_OK = ("demande_envoyee", "accepte", "dm_envoye", "repondu_positif", "repondu_negatif", "repondu_autre", "relance_envoyee", "ignorer", "annuler", "commente")
ACTIONS_CERVEAU = ("accepter", "refuser", "garder", "abandonner")
LOOPBACK = ("127.0.0.1", "::1", "::ffff:127.0.0.1")
VERROU = threading.Lock()   # une écriture à la fois (le serveur traite plusieurs requêtes en parallèle)
_EQUIPE = None
_CERVEAU = None


def secret():
    """Secret du serveur (créé au premier appel s'il manque, jamais affiché ni journalisé)."""
    try:
        t = SECRET_FICHIER.read_text(encoding="utf-8").strip()
        if len(t) >= 20: return t
    except OSError: pass
    t = secrets.token_urlsafe(32); SECRET_FICHIER.parent.mkdir(parents=True, exist_ok=True); SECRET_FICHIER.write_text(t + "\n", encoding="utf-8"); return t


def equipe():
    """Module linkedin-equipe.py (chemin fixe, chargé une seule fois)."""
    global _EQUIPE
    if _EQUIPE is None:
        s = importlib.util.spec_from_file_location("linkedin_equipe", RACINE / "B2B" / "agents" / "linkedin-equipe.py"); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); _EQUIPE = m
    return _EQUIPE


def cerveau():
    """Module cerveau.py (chemin fixe, chargé une seule fois)."""
    global _CERVEAU
    if _CERVEAU is None:
        s = importlib.util.spec_from_file_location("cerveau", RACINE / "B2B" / "agents" / "cerveau.py"); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); _CERVEAU = m
    return _CERVEAU


class LectureSeule(SimpleHTTPRequestHandler):
    def _autorise(self, fourni):
        """Vrai pour la machine elle-même ou si `fourni` est le secret du serveur."""
        if self.client_address[0] in LOOPBACK: return True
        return bool(fourni) and hmac.compare_digest(str(fourni).encode("utf-8"), secret().encode("utf-8"))

    def _permis(self):
        nom = self.path.split("?", 1)[0].lstrip("/") or "index.html"
        return nom if nom in PERMIS else None

    def do_GET(self):
        nom = self._permis()
        if not nom: return self.send_error(404)
        if nom in PROTEGES and not self._autorise((parse_qs(urlsplit(self.path).query).get("k") or [""])[0]): return self.send_error(403)
        donnees = DOSSIER / "agents.js"
        if nom == "index.html" and (not donnees.exists() or time.time() - donnees.stat().st_mtime > 60):
            subprocess.run([sys.executable, str(RACINE / "outils" / "agents-json.py")], timeout=60, creationflags=0x08000000 if sys.platform == "win32" else 0)
        self.path = "/" + nom
        return super().do_GET()

    def do_HEAD(self):
        nom = self._permis()
        if not nom: return self.send_error(404)
        if nom in PROTEGES and not self._autorise((parse_qs(urlsplit(self.path).query).get("k") or [""])[0]): return self.send_error(403)
        return super().do_HEAD()

    def _repondre(self, code, msg):
        corps = json.dumps({"message": msg}, ensure_ascii=False).encode("utf-8")
        self.send_response(code); self.send_header("Content-Type", "application/json; charset=utf-8"); self.send_header("Content-Length", str(len(corps))); self.end_headers(); self.wfile.write(corps)

    def do_POST(self):
        route = urlsplit(self.path).path
        if route not in ("/api/linkedin", "/api/cerveau") or self.headers.get("X-Jarvis") != "1": return self.send_error(405)
        permises, charger = (ACTIONS_OK, equipe) if route == "/api/linkedin" else (ACTIONS_CERVEAU, cerveau)
        if not self._autorise(self.headers.get("X-Jarvis-Secret")): return self._repondre(403, "Accès refusé : secret du serveur absent ou faux.")
        if not (self.headers.get("Content-Type") or "").lower().startswith("application/json"): return self.send_error(415)
        try: taille = int(self.headers.get("Content-Length") or 0)
        except ValueError: return self.send_error(400)
        if taille <= 0: return self.send_error(411)
        if taille > TAILLE_MAX: return self.send_error(413)
        try:
            d = json.loads(self.rfile.read(taille).decode("utf-8")); ident, action = d["id"], d["action"]
        except (ValueError, KeyError, TypeError, UnicodeDecodeError): return self.send_error(400)
        if not (isinstance(ident, str) and ID_OK.match(ident) and isinstance(action, str) and action in permises): return self._repondre(400, "Requête refusée (identifiant ou action inconnus).")
        try:
            with VERROU:
                m = charger(); msg = m.appliquer_et_exporter(m.cfg(), ident, action, time.strftime("%Y-%m-%d")); code = 200
        except Exception as e:
            if type(e).__name__ != "ErreurAgent": return self._repondre(500, "Erreur du serveur : rien n'a été enregistré.")   # jamais le détail technique (chemins, trace)
            msg, code = str(e), 409
        return self._repondre(code, msg)
    do_PUT = do_DELETE = do_PATCH = lambda self: self.send_error(405)
    def list_directory(self, path): self.send_error(404)
    def end_headers(self):
        self.send_header("Cache-Control", "no-store"); self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'")
        super().end_headers()
    def log_message(self, *a): pass   # aucun journal d'accès


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--port", type=int, default=8080); ap.add_argument("--hote", default="0.0.0.0")
    o = ap.parse_args()
    ThreadingHTTPServer((o.hote, o.port), partial(LectureSeule, directory=str(DOSSIER))).serve_forever()


if __name__ == "__main__":
    main()
