r"""Mise à jour automatique du gros PC : « git pull --ff-only origin main », sans jamais rien forcer (24/11/2026).

Lancé toutes les 10 minutes par la tâche Windows Jarvis-MajGrosPC (outils\tache-maj-gros-pc.ps1, pythonw : aucune fenêtre).
Le pull n'a lieu QUE si le dossier est propre (aucune modification locale non commitée, fichiers nouveaux compris),
si aucune opération git n'est en cours et si aucun Claude Code n'y a travaillé depuis 10 minutes.
Sinon le tour est sauté : pas de stash, pas de reset, pas de force, pas de merge.
Trace : logs\maj-gros-pc.log (ignoré par git, lignes de plus de 30 jours supprimées).
Pull impossible ou divergent : une alerte Discord par jour au plus (jeton lu dans .env par B2B\agents\prospection.py, jamais affiché).

Usage : python outils\maj-gros-pc.py [--racine DOSSIER] [--sans-discord]   (les options servent aux tests)
Code de sortie : 0 = à jour, mis à jour ou tour sauté ; 1 = pull échoué ou divergent.
"""
import argparse, json, os, re, subprocess, sys, time
from datetime import date, datetime, timedelta
from pathlib import Path

RACINE_DEFAUT = Path(__file__).resolve().parent.parent
PAUSE_CLAUDE_S = 600       # un Claude Code qui a écrit dans sa conversation depuis moins de 10 min travaille peut-être ici
GARDE_JOURS = 30
SANS_FENETRE = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def git(racine, *args, delai=120):
    """(code, sortie) d'une commande git ; jamais d'invite, jamais de fenêtre."""
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never")
    try:
        r = subprocess.run(["git", "-C", str(racine), *args], capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=delai, env=env, creationflags=SANS_FENETRE)
        return r.returncode, (r.stdout + r.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as ex:
        return 99, type(ex).__name__


def tracer(racine, texte, maintenant=None):
    """Une ligne dans logs\\maj-gros-pc.log ; on garde 30 jours au plus."""
    maintenant = maintenant or datetime.now()
    f = racine / "logs" / "maj-gros-pc.log"
    try:
        f.parent.mkdir(exist_ok=True)
        limite = (maintenant - timedelta(days=GARDE_JOURS)).strftime("%Y-%m-%d")
        gardees = []
        if f.exists():
            gardees = [l for l in f.read_text(encoding="utf-8", errors="replace").splitlines() if l[:10] >= limite]
        gardees.append(f"{maintenant:%Y-%m-%d %H:%M:%S} {texte}")
        f.write_text("\n".join(gardees) + "\n", encoding="utf-8")
    except OSError:
        pass


def claude_actif(racine, maintenant=None):
    """Vrai si une conversation Claude Code de ce dossier a été écrite depuis PAUSE_CLAUDE_S secondes."""
    maintenant = maintenant or time.time()
    dossier = Path.home() / ".claude" / "projects" / re.sub(r"[^A-Za-z0-9]", "-", str(racine))
    try:
        return any(maintenant - f.stat().st_mtime < PAUSE_CLAUDE_S for f in dossier.glob("*.jsonl"))
    except OSError:
        return False


def operation_en_cours(racine):
    g = racine / ".git"
    return any((g / n).exists() for n in ("index.lock", "MERGE_HEAD", "rebase-merge", "rebase-apply", "CHERRY_PICK_HEAD", "REVERT_HEAD"))


def alerte_deja_envoyee(racine, jour):
    try:
        return json.loads((racine / "logs" / "maj-gros-pc-alerte.json").read_text(encoding="utf-8")).get("jour") == jour
    except (OSError, ValueError):
        return False


def alerter(racine, texte, jour, discord=True):
    """Une alerte Discord par jour au plus. Renvoie True si elle est partie."""
    if alerte_deja_envoyee(racine, jour):
        return False
    if not discord:
        return False
    try:
        sys.path.insert(0, str(racine / "B2B" / "agents"))
        import prospection as P
        a = P.acces_discord()
        if not a:
            return False
        jeton, salon, uid = a
        r = P.discord(jeton, "POST", f"/channels/{salon}/messages", {"content": f"<@{uid}> {texte}"[:1900], "allowed_mentions": {"users": [uid]}})
        if not (r and "id" in r):
            return False
        (racine / "logs" / "maj-gros-pc-alerte.json").write_text(json.dumps({"jour": jour}), encoding="utf-8")
        return True
    except Exception:
        return False


def tour(racine, discord=True, maintenant=None):
    """Un tour de mise à jour. Renvoie (code de sortie, phrase de trace)."""
    maintenant = maintenant or datetime.now()
    jour = f"{maintenant:%Y-%m-%d}"
    if operation_en_cours(racine):
        return 0, "sauté : une opération git est en cours"
    if claude_actif(racine):
        return 0, "sauté : Claude Code a travaillé ici depuis moins de 10 min"
    code, sale = git(racine, "status", "--porcelain", "--untracked-files=normal")
    if code != 0:
        return 0, "sauté : état git illisible"
    if sale:
        return 0, f"sauté : {len(sale.splitlines())} modification(s) locale(s) non commitée(s)"
    code, branche = git(racine, "branch", "--show-current")
    if code != 0 or branche != "main":
        return 0, f"sauté : branche « {branche or 'détachée'} » (seule main est mise à jour)"
    avant = git(racine, "rev-parse", "HEAD")[1]
    code, sortie = git(racine, "pull", "--ff-only", "origin", "main", delai=300)
    apres = git(racine, "rev-parse", "HEAD")[1]
    if code == 0:
        return 0, ("à jour" if avant == apres else f"mis à jour {avant[:7]} -> {apres[:7]}")
    resume = (sortie.splitlines() or ["?"])[-1][:120]
    envoyee = alerter(racine, f"Mise à jour du gros PC impossible (git pull --ff-only : {resume}). Rien n'a été forcé ni écrasé.", jour, discord)
    return 1, f"ÉCHEC pull ({resume}){' ; alerte Discord envoyée' if envoyee else ''}"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--racine", default=str(RACINE_DEFAUT))
    p.add_argument("--sans-discord", action="store_true")
    a = p.parse_args()
    racine = Path(a.racine).resolve()
    code, phrase = tour(racine, discord=not a.sans_discord)
    tracer(racine, phrase)
    print(phrase)
    return code


if __name__ == "__main__":
    sys.exit(main())
