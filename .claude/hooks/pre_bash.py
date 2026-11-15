#!/usr/bin/env python3
"""Hook PreToolUse (Bash, PowerShell) du projet Jarvis (harness, 15/11/2026) : refuse (code 2) git add -A / git add . / git reset --hard / git clean / git push --force,
et toute commande qui afficherait .env ou un *.local.json. Sinon : rien (code 0). Moins de 2 s, sans dépendance."""
import json, re, sys

GIT = [(re.compile(r"\bgit\s+add\s+(?:[^;&|]*\s)?(?:-A|--all)\b"), "git add -A (ajouter les fichiers un par un)"),
       (re.compile(r"\bgit\s+add\s+(?:[^;&|]*\s)?\.(?=\s|$|;|&|\|)"), "git add . (ajouter les fichiers un par un)"),
       (re.compile(r"\bgit\s+reset\s+(?:[^;&|]*\s)?--hard\b"), "git reset --hard"),
       (re.compile(r"\bgit\s+clean\b"), "git clean"),
       (re.compile(r"\bgit\s+push\s+(?:[^;&|]*\s)?(?:--force(?:-with-lease)?|-f)\b"), "git push --force")]
LECTURE = re.compile(r"\b(?:cat|type|more|less|head|tail|nl|od|xxd|hexdump|strings|bat|grep|rg|sed|awk|gc|Get-Content|Select-String|sls|findstr|print|open|read_text|notepad|code)\b", re.I)
SECRET = re.compile(r"(?:^|[\s\"'\\/=(])(?:[\w.-]*\\|[\w.-]*/)*(?:\.env|[\w.-]+\.local\.json)(?=$|[\s\"');|&])", re.I)


def raison(cmd):
    for rx, nom in GIT:
        if rx.search(cmd): return f"commande refusée par le harness : {nom}"
    if SECRET.search(cmd) and LECTURE.search(cmd): return "commande refusée par le harness : elle afficherait .env ou un *.local.json (secrets jamais dans le chat)"
    return ""


def main():
    try: d = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace") or "{}")
    except ValueError: return 0
    r = raison(str((d.get("tool_input") or {}).get("command", "")))
    if r: sys.stderr.buffer.write((r + "\n").encode("utf-8")); return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
