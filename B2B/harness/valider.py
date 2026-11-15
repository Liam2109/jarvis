#!/usr/bin/env python3
"""Validateur JSON Schema minimal (sous-ensemble : type, required, properties, additionalProperties, items, enum, const, pattern, minimum, maximum,
minLength, maxLength, minItems), sans dépendance. Utilisé pour les contrats d'agents et les sorties de Jarvis CEO.
  python B2B\\harness\\valider.py            valide tous les contrats B2B\\harness\\contrats\\*.json ; code 1 si l'un est invalide"""
import json, re, sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
TYPES = {"object": dict, "array": list, "string": str, "integer": int, "boolean": bool, "number": (int, float), "null": type(None)}


def _type_ok(v, t):
    if isinstance(t, list): return any(_type_ok(v, x) for x in t)
    if t in ("integer", "number") and isinstance(v, bool): return False
    return isinstance(v, TYPES[t])


def valider(v, s, chemin="$"):
    """Liste des erreurs (vide si valide)."""
    e = []
    if "const" in s and v != s["const"]: return [f"{chemin} : doit valoir {json.dumps(s['const'])}"]
    if "enum" in s and v not in s["enum"]: return [f"{chemin} : valeur hors liste ({v!r})"]
    if "type" in s and not _type_ok(v, s["type"]): return [f"{chemin} : type attendu {s['type']}"]
    if isinstance(v, str):
        if "pattern" in s and not re.search(s["pattern"], v): e.append(f"{chemin} : format invalide ({v!r})")
        if len(v) < s.get("minLength", 0): e.append(f"{chemin} : trop court")
        if "maxLength" in s and len(v) > s["maxLength"]: e.append(f"{chemin} : trop long")
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        if "minimum" in s and v < s["minimum"]: e.append(f"{chemin} : < {s['minimum']}")
        if "maximum" in s and v > s["maximum"]: e.append(f"{chemin} : > {s['maximum']}")
    if isinstance(v, list):
        if len(v) < s.get("minItems", 0): e.append(f"{chemin} : au moins {s['minItems']} élément(s)")
        for i, x in enumerate(v): e += valider(x, s.get("items", {}), f"{chemin}[{i}]")
    if isinstance(v, dict):
        for k in s.get("required", []):
            if k not in v: e.append(f"{chemin} : champ obligatoire absent « {k} »")
        props = s.get("properties", {})
        for k, x in v.items():
            if k in props: e += valider(x, props[k], f"{chemin}.{k}")
            elif s.get("additionalProperties") is False: e.append(f"{chemin} : champ inconnu « {k} »")
    return e


def contrats():
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted((ICI / "contrats").glob("*.json"))}


def main():
    schema = json.loads((ICI / "contrat.schema.json").read_text(encoding="utf-8")); ko = 0
    for nom, c in contrats().items():
        e = valider(c, schema) + ([] if c.get("nom") == nom else [f"$.nom ({c.get('nom')}) différent du nom de fichier"])
        print(("OK    " if not e else "ECHEC ") + nom + ("" if not e else " : " + " ; ".join(e))); ko += bool(e)
    print(f"contrats : {len(contrats()) - ko} valide(s), {ko} invalide(s)")
    return 1 if ko else 0


if __name__ == "__main__":
    sys.exit(main())
