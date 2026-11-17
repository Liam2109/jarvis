#!/usr/bin/env python3
"""Rapport du harness (15/11/2026) : agent | contrat | garde branchée | test | dernière trace | statut. Lecture seule, sans réseau.
  python B2B\\harness\\rapport.py"""
import json, sys
from datetime import datetime
from pathlib import Path

ICI = Path(__file__).resolve().parent
RACINE = ICI.parent.parent
sys.path.insert(0, str(ICI))
import traces as T   # noqa: E402
import surveillant as SV   # noqa: E402
from valider import valider   # noqa: E402

# Envois gardés : prospection.discord (bot Discord de tous les agents), reponses.poster, prospection.refus (e-mail client).
GARDES = ("garde_harness", "garde.avant_envoi", "P.discord(", "PR.discord(")
NON_BRANCHE = {"instagram": "partielle : alertes Discord gardées, publication Instagram non gardée (agent retiré)",
               "page-exemple": "partielle : alertes Discord gardées, déploiement de page non gardé (Vercel, accord de Liam)",
               "jarvis-ceo": "sans objet : pas de script (sorties validées par jarvis_sortie.py)",
               "videos-monteur": "sans objet : le texte du sketch est gardé par videos-creation avant l'appel (aucun envoi)",
               "videos-nettoyage": "sans objet : ne produit aucun texte, n'envoie rien (garde de chemins codée : seulement les dossiers listés de Videos)"}


def garde(c):
    if c["statut"] == "prevu": return "à brancher avant activation"
    if c["nom"] in NON_BRANCHE: return NON_BRANCHE[c["nom"]]
    p = RACINE / c.get("script", "")
    if not p.is_file(): return "script absent"
    t = p.read_text(encoding="utf-8", errors="replace")
    if c["nom"] == "surveillant": t += (ICI / "surveillant.py").read_text(encoding="utf-8")
    return "oui" if any(g in t for g in GARDES) else "non"


def derniere_trace(nom, dossier=None):
    d = (dossier or T.dossier_logs()) / nom
    fs = sorted(d.glob("*.jsonl")) if d.is_dir() else []
    for f in reversed(fs):
        l = [x for x in f.read_text(encoding="utf-8").splitlines() if x.strip()]
        if l:
            try: x = json.loads(l[-1]); return f"{x.get('heure', '')[:16].replace('T', ' ')} {'ok' if x.get('ok') else 'ERREUR'}"
            except ValueError: pass
    return "aucune"


def lignes(maintenant=None):
    m = maintenant or datetime.now(); schema = json.loads((ICI / "contrat.schema.json").read_text(encoding="utf-8")); out = []
    for c in SV.contrats():
        ok_c = "valide" if not valider(c, schema) else "INVALIDE"
        tests = c["tests"]; manquants = [t for t in tests if not (RACINE / t).is_file()]
        test = "aucun" if not tests else (f"oui ({len(tests)})" if not manquants else f"MANQUANT : {', '.join(manquants)}")
        defaut, _ = SV.defauts(m, [c])
        statut = c["statut"] + ("" if c["statut"] not in SV.SURVEILLES else (" - " + defaut[0].replace(f"agent {c['nom']} ", "") if defaut else " - OK"))
        out.append((c["nom"], ok_c, garde(c), test, derniere_trace(c["nom"]), statut))
    return out


def main():
    print("| agent | contrat | garde branchée | test | dernière trace | statut |\n|---|---|---|---|---|---|")
    for l in lignes(): print("| " + " | ".join(l) + " |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
