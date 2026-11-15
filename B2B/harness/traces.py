#!/usr/bin/env python3
"""Traces du harness (15/11/2026) : une ligne JSON par exécution dans B2B\\logs\\agents\\<agent>\\AAAA-MM-JJ.jsonl
{heure, decision, resultat, duree_s, ok, erreur?, commerce?}. Seulement le nom du commerce, jamais d'autre donnée client (ni e-mail, ni téléphone).
Dossier : JARVIS_HARNESS_LOGS s'il est posé ; sous JARVIS_TEST=1 un dossier temporaire (les tests n'écrivent jamais dans les vraies traces)."""
import json, os, re, tempfile
from datetime import datetime
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent.parent
_MAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_TEL = re.compile(r"(?:\+33|0)\s*[1-9](?:[\s.-]*\d{2}){4}")


def dossier_logs():
    if os.environ.get("JARVIS_HARNESS_LOGS"): return Path(os.environ["JARVIS_HARNESS_LOGS"])
    if os.environ.get("JARVIS_TEST") == "1": return Path(tempfile.gettempdir()) / "jarvis-harness-test-logs"
    return RACINE / "B2B" / "logs" / "agents"


def nettoyer(t):
    """Retire e-mails et numéros de téléphone d'un texte de trace."""
    return _TEL.sub("[tél]", _MAIL.sub("[e-mail]", str(t or "")))[:300]


def ecrire(agent, decision, resultat, duree_s=0.0, ok=True, erreur=None, commerce=None, maintenant=None):
    n = maintenant or datetime.now()
    ligne = {"heure": n.strftime("%Y-%m-%dT%H:%M:%S"), "decision": nettoyer(decision), "resultat": nettoyer(resultat), "duree_s": round(float(duree_s), 2), "ok": bool(ok)}
    if erreur: ligne["erreur"] = nettoyer(erreur)
    if commerce: ligne["commerce"] = nettoyer(commerce)[:80]
    d = dossier_logs() / agent
    try:
        d.mkdir(parents=True, exist_ok=True)
        with (d / f"{n:%Y-%m-%d}.jsonl").open("a", encoding="utf-8") as f: f.write(json.dumps(ligne, ensure_ascii=False) + "\n")
    except OSError: pass   # une trace qui échoue ne casse jamais un agent
    return ligne


def lire(agent, jour, dossier=None):
    p = (dossier or dossier_logs()) / agent / f"{jour}.jsonl"
    if not p.exists(): return []
    out = []
    for l in p.read_text(encoding="utf-8").splitlines():
        try: out.append(json.loads(l))
        except ValueError: pass
    return out


class Execution:
    """with traces.Execution("appels-sid", "jour") as t: ... ; t.resultat = "liste créée" ; une exception = ligne ok:false avec le type d'erreur (puis elle remonte)."""
    def __init__(self, agent, decision): self.agent, self.decision, self.resultat, self.commerce = agent, decision, "", None
    def __enter__(self): self.t0 = datetime.now(); return self
    def __exit__(self, typ, val, tb):
        d = (datetime.now() - self.t0).total_seconds()
        if typ is SystemExit and val.code in (0, None): typ = None
        ecrire(self.agent, self.decision, self.resultat or ("erreur" if typ else "terminé"), d, ok=typ is None,
               erreur=(f"{typ.__name__} {getattr(val, 'code', '')}".strip() if typ else None), commerce=self.commerce)
        return False
