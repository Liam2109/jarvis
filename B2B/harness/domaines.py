#!/usr/bin/env python3
"""Domaines des superviseurs (22/11/2026) : qui suit qui. Source unique = les scripts B2B\agents\superviseur-*.py (AGENTS_SUIVIS),
celle que le superviseur applique vraiment ; les noms des notes viennent de B2B\harness\fiches-noms.json.
Sert au graphe Obsidian en arbre : Jarvis (CEO) -> les 4 superviseurs de domaine -> leurs agents ; un agent sans domaine reste lié au CEO.
Lecture seule, sans réseau ni IA."""
import json, re
from pathlib import Path

ICI = Path(__file__).resolve().parent
RACINE = ICI.parent.parent
AGENTS_DIR = RACINE / "B2B" / "agents"
NOMS_JSON = ICI / "fiches-noms.json"


def noms():
    """Agent (nom du contrat) -> nom de sa note dans docs\agents, sans les clés de documentation ni les agents sans note."""
    return {k: v for k, v in json.loads(NOMS_JSON.read_text(encoding="utf-8")).items() if not k.startswith("_")}


def domaines():
    """-> {agent superviseur: (domaine, [agents suivis])}, lu dans les scripts des superviseurs (AGENTS_SUIVIS)."""
    out = {}
    for p in sorted(AGENTS_DIR.glob("superviseur-*.py")):
        t = p.read_text(encoding="utf-8")
        a = re.search(r'^AGENT, DOMAINE = "([^"]+)", "([^"]+)"', t, re.M)
        l = re.search(r"^AGENTS_SUIVIS\s*=\s*\[([^\]]*)\]", t, re.M)
        if a and l: out[a.group(1)] = (a.group(2), re.findall(r'"([^"]+)"', l.group(1)))
    return out


def liens_permis(n=None):
    """-> {note d'un superviseur (chemin relatif): notes qu'elle a le droit de citer} : son CEO et les agents de son domaine, rien d'autre."""
    n = n or noms(); chemin = lambda a: f"docs/agents/{n[a]}.md"
    return {chemin(s): {chemin("jarvis-ceo")} | {chemin(a) for a in ag if n.get(a)}
            for s, (_, ag) in domaines().items() if n.get(s)}
