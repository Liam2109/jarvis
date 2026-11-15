"""Outils communs des tests d'agents (harness, 15/11/2026) : mode test silencieux, traces dans un dossier temporaire, chargement d'un agent par son fichier."""
import importlib.util, os, sys, tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
AGENTS = RACINE / "B2B" / "agents"
HARNESS = RACINE / "B2B" / "harness"
FIXTURES = RACINE / "tests" / "fixtures"
os.environ["JARVIS_TEST"] = "1"
os.environ.setdefault("JARVIS_HARNESS_LOGS", tempfile.mkdtemp(prefix="harness-test-"))
os.environ.setdefault("JARVIS_GARDE_MAINTENANT", "2026-11-17T10:00")
sys.dont_write_bytecode = True
for p in (str(AGENTS), str(HARNESS)):
    if p not in sys.path: sys.path.insert(0, p)


def agent(nom):
    """Charge B2B\\agents\\<nom>.py (noms avec tiret) comme module."""
    s = importlib.util.spec_from_file_location(nom.replace("-", "_"), AGENTS / f"{nom}.py"); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


def harness(nom):
    s = importlib.util.spec_from_file_location("harness_" + nom, HARNESS / f"{nom}.py"); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
