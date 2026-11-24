#!/usr/bin/env python3
"""Sert le tableau de bord en LECTURE SEULE : uniquement le dossier dashboard\\ (jamais le reste du dépôt), GET/HEAD seulement, aucun listage de dossier.

  python outils/servir-dashboard.py [--port 8080] [--hote 0.0.0.0]
Sur le serveur, lancé par la tâche « Jarvis-Tableau-Service » (voir outils\\taches-dashboard-serveur.ps1). Ouvrir http://<serveur>:8080/ depuis le réseau local.
À l'ouverture de la page, les données sont régénérées si elles ont plus d'une minute (outils\\agents-json.py, comptes seulement).
"""
import argparse, importlib.util, json, subprocess, sys, time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
DOSSIER = RACINE / "dashboard"
PERMIS = {"index.html", "agents.js", "agents.json", "docs.js", "data/linkedin.js"}


class LectureSeule(SimpleHTTPRequestHandler):
    def _permis(self):
        nom = self.path.split("?", 1)[0].lstrip("/") or "index.html"
        return nom if nom in PERMIS else None

    def do_GET(self):
        nom = self._permis()
        if not nom: return self.send_error(404)
        donnees = DOSSIER / "agents.js"
        if nom == "index.html" and (not donnees.exists() or time.time() - donnees.stat().st_mtime > 60):
            subprocess.run([sys.executable, str(RACINE / "outils" / "agents-json.py")], timeout=60, creationflags=0x08000000 if sys.platform == "win32" else 0)
        self.path = "/" + nom
        return super().do_GET()

    def do_HEAD(self):
        if not self._permis(): return self.send_error(404)
        return super().do_HEAD()

    def do_POST(self):
        if self.path.split("?", 1)[0] != "/api/linkedin" or self.headers.get("X-Jarvis") != "1": return self.send_error(405)
        try:
            taille = int(self.headers.get("Content-Length") or 0)
            if not 0 < taille <= 1024: return self.send_error(400)
            d = json.loads(self.rfile.read(taille).decode("utf-8")); ident, action = str(d["id"]), str(d["action"])
            s = importlib.util.spec_from_file_location("linkedin_equipe", RACINE / "B2B" / "agents" / "linkedin-equipe.py"); m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
            conf = m.cfg(); jour = time.strftime("%Y-%m-%d")
            try: msg = m.appliquer_et_exporter(conf, ident, action, jour); code = 200
            except m.ErreurAgent as e: msg, code = str(e), 409
        except (ValueError, KeyError, OSError): return self.send_error(400)
        corps = json.dumps({"message": msg}, ensure_ascii=False).encode("utf-8")
        self.send_response(code); self.send_header("Content-Type", "application/json; charset=utf-8"); self.send_header("Content-Length", str(len(corps))); self.end_headers(); self.wfile.write(corps)
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
