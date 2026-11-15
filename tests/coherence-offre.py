#!/usr/bin/env python3
"""Cohérence de l'offre (harness, 15/11/2026) : compare docs, skills, agents et site vitrine à B2B\\docs\\OFFRE-REFERENCE.json. Sans réseau, sans token.

  python tests\\coherence-offre.py                 tout le périmètre ; échoue (code 1) sur toute faute NOUVELLE (fichier:ligne)
  python tests\\coherence-offre.py --strict        échoue aussi sur les fautes connues (B2B\\harness\\coherence-connus.json)
  python tests\\coherence-offre.py --connus        affiche aussi les fautes connues
  python tests\\coherence-offre.py --fichiers A B  seulement ces fichiers (hooks : rapide, sortie vide si tout va bien)
Fautes connues = déjà présentes le 15/11/2026, listées pour Liam, jamais corrigées sans son accord : elles avertissent, elles ne bloquent pas."""
import argparse, json, re, sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
REF = RACINE / "B2B" / "docs" / "OFFRE-REFERENCE.json"
CONNUS = RACINE / "B2B" / "harness" / "coherence-connus.json"
# Journaux datés (historique : une ancienne valeur y est un fait passé, pas une contradiction), archives et fixtures de tests : hors contrôle.
HISTORIQUES = {"IDEES-MASTER.md", "JOURNAL-B2B.md", "IDEES-CLAUDE-CHAT.md", "TODO-B2B.md", "A-FAIRE-2026-11-04.md", "INVENTAIRE.md", "coherence-connus.json"}
EXTS = {".md", ".py", ".json", ".html", ".js", ".txt"}
LIEN = re.compile(r"https://buy\.stripe\.com/[A-Za-z0-9]+")
# Phrases interdites propres à ce test (15/11/2026), en plus de OFFRE-REFERENCE.json : interdites quand la ligne parle de l'offre
# (l'abonnement de 49 €/mois est compris dans le lien Stripe : jamais « pas obligatoire »). La garde n'est pas concernée.
INTERDITES_OFFRE = ["pas obligatoire"]
OFFRE_MOTS = re.compile(r"maintenance|abonnement|h[ée]bergement|€|euros?\b|mois")
# Contradictions supplémentaires trouvées dans B2B le 15/11/2026 (offre de référence : 595 / 994 une fois, 49 €/mois inclus, sans acompte)
AUTRES = [(re.compile(r"990\s*(?:€\s*)?à\s*1\s?490"), "ancien prix du site (990 à 1 490 €) : 994 €"),
          (re.compile(r"29\s*à\s*49\s*€"), "ancienne maintenance 29 à 49 € : 49 €/mois"),
          (re.compile(r"\b20\s*€\s*/\s*mois|\b20-29\s*€"), "ancienne maintenance 20 €/mois : 49 €/mois"),
          (re.compile(r"acompte\s*30|lien d.acompte", re.I), "acompte : supprimé le 14/11 (paiement complet)")]


def charger_ref():
    return json.loads(REF.read_text(encoding="utf-8"))


def perimetre():
    f = [p for p in (RACINE / "B2B" / "docs").rglob("*") if p.suffix in (".md", ".json")]
    f += [p for p in (RACINE / ".claude" / "skills").rglob("*") if p.suffix in EXTS]
    f += [p for p in (RACINE / "B2B" / "agents").glob("*") if p.suffix in (".py", ".md", ".json")]
    for d in ("B2B/sites/agence", "B2B/sites/sorties/agence-prod"):
        f += [p for p in (RACINE / d).rglob("*") if p.suffix in (".html", ".js") and "node_modules" not in p.parts and "dist" not in p.parts]
    return f


PERIMETRE = ("B2B/docs/", ".claude/skills/", "B2B/agents/", "B2B/sites/agence/", "B2B/sites/sorties/agence-prod/")   # le code du harness (qui cite les phrases pour les chercher) est hors périmètre


def exclu(p):
    rel = p.relative_to(RACINE).as_posix()
    return (not rel.startswith(PERIMETRE) or "/archives/" in rel or p.name in HISTORIQUES or p.name.startswith(("DIAGNOSTIC-", "test_", "test-")) or p.name.endswith(".local.json")
            or p.name.endswith(".NOUVEAU.md") or "/sid/" in rel or p.name.startswith("liste-appels"))


def fautes_ligne(ligne, ref, nom, suffixe):
    f = []
    if nom not in ref["fichiers_liens_libres"]:
        for l in LIEN.findall(ligne):
            if l not in ref["liens_stripe_autorises"]: f.append(("lien", f"lien Stripe non autorisé {l[-6:]}"))
    bas = ligne.lower()
    for ph in ref["phrases_interdites"]:
        if ph == "facultative":   # mot courant (« caméra facultative ») : interdit seulement à propos de l'offre
            if any("facultati" in s and re.search(r"maintenance|abonnement|h[ée]bergement|€|mois", s) for s in re.split(r"[.;|!?]", bas)): f.append(("phrase", "« facultative » à propos de l'offre"))   # même phrase ou même champ
        elif ph.lower() in bas and not (ph == "facultative"): f.append(("phrase", f"phrase interdite « {ph} »"))
    if "maintenance facultative" in bas: f = [x for x in f if x[1] != "« facultative » à propos de l'offre"]
    f += [("phrase", f"phrase interdite « {ph} » à propos de l'offre") for ph in INTERDITES_OFFRE if ph in bas and OFFRE_MOTS.search(bas)]   # toute la ligne (« … 49 euros par mois … ; ce n'est pas obligatoire »)
    if suffixe == ".md":   # anciennes valeurs de Résultat, quand elles sont citées comme valeurs (liste, guillemets, tableau)
        for v in ref["resultats_anciens"]:
            if re.search(rf"(?:[«\"`|]\s*|^\s*[-*]\s*){v}(?:\s*[»\"`|:]|\s*$)", ligne): f.append(("resultat", f"ancienne valeur de Résultat « {v} »"))
    for rx, msg in AUTRES:
        if rx.search(ligne): f.append(("autre", msg))
    return f


def verifier_resultats_code(texte, ref):
    """Une liste RESULTATS dans le code doit être exactement les 8 valeurs de référence, dans l'ordre."""
    out = []
    for i, l in enumerate(texte.splitlines(), 1):
        m = re.match(r"\s*RESULTATS\s*=\s*(\[.*?\])", l)
        if m:
            try: v = json.loads(m.group(1))
            except ValueError: continue
            if v != ref["resultats_appel"]: out.append((i, "resultat", "liste RESULTATS différente des 8 valeurs de référence"))
    return out


def scanner(fichiers, ref):
    res = []
    for p in fichiers:
        p = Path(p).resolve()
        if not p.is_file() or p.suffix not in EXTS or p == REF: continue
        try: p.relative_to(RACINE)
        except ValueError: continue
        if exclu(p): continue
        try: texte = p.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError): continue
        rel = p.relative_to(RACINE).as_posix()
        if p.name == "liens-paiement.md":   # registre : les anciens liens y sont listés « NE PLUS ENVOYER » ; on vérifie seulement que les 2 liens valides y sont
            for l in ref["liens_stripe_autorises"]:
                if l not in texte: res.append((rel, 1, "registre", f"lien autorisé absent du registre {l[-6:]}"))
            continue
        for i, l in enumerate(texte.splitlines(), 1):
            for regle, msg in fautes_ligne(l, ref, p.name, p.suffix): res.append((rel, i, regle, msg))
        if p.suffix == ".py":
            for i, regle, msg in verifier_resultats_code(texte, ref): res.append((rel, i, regle, msg))
    return res


def connus():
    try: return {(c["fichier"], c["regle"]) for c in json.loads(CONNUS.read_text(encoding="utf-8"))["connus"]}
    except (OSError, ValueError, KeyError): return set()


def main(argv=None):
    a = argparse.ArgumentParser(); a.add_argument("--strict", action="store_true"); a.add_argument("--connus", action="store_true"); a.add_argument("--fichiers", nargs="*")
    a = a.parse_args(argv)
    ref = charger_ref(); k = connus()
    res = scanner(a.fichiers if a.fichiers is not None else perimetre(), ref)
    nouveaux = [r for r in res if a.strict or (r[0], r[2]) not in k]
    vieux = [r for r in res if r not in nouveaux]
    for f, i, _, m in nouveaux: print(f"ECHEC {f}:{i} : {m}")
    if a.connus:
        for f, i, _, m in vieux: print(f"CONNU {f}:{i} : {m}")
    if a.fichiers is None: print(f"cohérence de l'offre : {len(nouveaux)} faute(s) nouvelle(s), {len(vieux)} connue(s) (à corriger par Liam)")
    return 1 if nouveaux else 0


if __name__ == "__main__":
    sys.exit(main())
