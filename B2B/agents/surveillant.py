#!/usr/bin/env python3
"""Lanceur de l'agent surveillant (tâche serveur Jarvis-B2B-surveillant) : la logique est dans B2B\harness\surveillant.py."""
import importlib.util, sys
from pathlib import Path

_s = importlib.util.spec_from_file_location("harness_surveillant", Path(__file__).resolve().parent.parent / "harness" / "surveillant.py")
S = importlib.util.module_from_spec(_s); _s.loader.exec_module(S)
main = S.main

if __name__ == "__main__":
    sys.exit(main())
