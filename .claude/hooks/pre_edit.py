#!/usr/bin/env python3
"""Hook PreToolUse (Edit, Write, MultiEdit, NotebookEdit) du projet Jarvis (harness, 15/11/2026) : refuse (code 2) toute écriture dans memoire\\, .env ou un *.local.json."""
import json, re, sys

INTERDIT = [(re.compile(r"(?:^|[\\/])memoire[\\/]", re.I), "memoire\\ (mémoire de Jarvis : Liam seulement)"),
            (re.compile(r"(?:^|[\\/])\.env$", re.I), ".env (secrets)"),
            (re.compile(r"\.local\.json$", re.I), "*.local.json (réglages secrets de la machine)")]


def raison(chemin):
    for rx, nom in INTERDIT:
        if rx.search(chemin): return f"écriture refusée par le harness : {nom}"
    return ""


def main():
    try: d = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace") or "{}")
    except ValueError: return 0
    ti = d.get("tool_input") or {}
    r = raison(str(ti.get("file_path") or ti.get("notebook_path") or ""))
    if r: sys.stderr.buffer.write((r + "\n").encode("utf-8")); return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
