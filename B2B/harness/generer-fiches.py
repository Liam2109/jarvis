#!/usr/bin/env python3
"""Fiches Obsidian des agents (15/11/2026) : une fiche par contrat dans B2B\\docs\\agents\\<agent>.md, l'organigramme, une note par responsable
et une copie de chaque skill (source : .claude\\skills\\<skill>\\SKILL.md -> B2B\\docs\\agents\\skills\\<skill>.md). Lecture seule du code, sans réseau ni IA.
Seule la partie entre <!-- GENERE:DEBUT --> et <!-- GENERE:FIN --> (et le frontmatter) est réécrite ; la zone « Notes de Liam » qui suit est conservée telle quelle.
Le bloc DYNAMIQUE (derniers tests, dernières traces) change d'une machine à l'autre : il n'entre pas dans la vérification.
  python B2B\\harness\\generer-fiches.py              régénère les fiches
  python B2B\\harness\\generer-fiches.py --tests      lance d'abord les tests des contrats (JARVIS_TEST=1) et note leur résultat (B2B\\logs\\agents\\_tests-fiches.json, hors git)
  python B2B\\harness\\generer-fiches.py --verifier   code 1 si une fiche manque ou n'est pas à jour, ou si un agent actif n'a pas de skill (rien n'est écrit)"""
import argparse, json, os, re, subprocess, sys, time
from pathlib import Path

ICI = Path(__file__).resolve().parent
RACINE = ICI.parent.parent
sys.path.insert(0, str(ICI))
import traces as T   # noqa: E402
import rapport as R   # noqa: E402
from valider import valider   # noqa: E402

CONTRATS, SKILLS = ICI / "contrats", RACINE / ".claude" / "skills"
SORTIE = RACINE / "B2B" / "docs" / "agents"; COPIES = SORTIE / "skills"
TACHES = RACINE / "B2B" / "agents" / "serveur-taches.json"
DEBUT, FIN = "<!-- GENERE:DEBUT (régénéré par python B2B\\harness\\generer-fiches.py : ne pas modifier) -->", "<!-- GENERE:FIN -->"
DYN_D, DYN_F = "<!-- DYNAMIQUE:DEBUT -->", "<!-- DYNAMIQUE:FIN -->"
NOTES = "## Notes de Liam\n\n_Zone libre, conservée telle quelle à chaque régénération._\n"
AC = "à compléter par Liam"
STATUT = {"actif": "actif", "simulation": "actif", "inactif": "arrêté", "prevu": "prévu"}
SKILLS_AGENT = {"prospection": ["agent-recherche", "agent-lots-emails"], "jarvis-ceo": ["jarvis-ceo"]}   # sinon agent-<nom>
RESPONSABLES = ["Prospection", "Vente", "Argent", "Production"]
JOURS = ["lun", "mar", "mer", "jeu", "ven", "sam", "dim"]
RESULTATS_TESTS = T.dossier_logs() / "_tests-fiches.json"


def lien_resp(r): return "[[jarvis-ceo|Jarvis (CEO)]]" if r == "Jarvis (CEO)" else ("Liam" if r == "Liam" else f"[[responsable-{r.lower()}|Responsable {r}]]")
def skills_de(nom): return SKILLS_AGENT.get(nom, [f"agent-{nom}"])
def contrats(): return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(CONTRATS.glob("*.json"))]


def taches():
    try: return json.loads(TACHES.read_text(encoding="utf-8"))["agents"]
    except (OSError, ValueError, KeyError): return {}


def jours_txt(js): return "tous les jours" if sorted(js) == list(range(7)) else ("lundi-vendredi" if sorted(js) == list(range(5)) else ", ".join(JOURS[j] for j in sorted(js)))


def horaire(c, t):
    if c["statut"] == "prevu": return AC
    plage = f"{jours_txt(c['jours'])} {c['heures']['debut']}-{c['heures']['fin']}"
    if not t: return f"à la demande (aucune tâche serveur), plage {plage}"
    q = f"chaque jour à {t['heure']}" if t.get("heure") else f"toutes les {t.get('toutes_minutes')} min"
    return q + (f" + lundi {t['lundi']}" if t.get("lundi") else "") + f", plage {plage}"


def machine(c, t): return AC if c["statut"] == "prevu" else ("serveur" if t else "gros PC")


def section(texte, motif):
    """Contenu d'une section « ## … » du skill dont le titre correspond au motif (sans le titre)."""
    m = re.search(r"^## (?:" + motif + r").*?$\n(.*?)(?=^## |\Z)", texte, re.M | re.S)
    return m.group(1).strip() if m else ""


def etapes(c):
    if c["statut"] == "prevu": return AC + " (agent non construit)."
    out = []
    for s in skills_de(c["nom"]):
        p = SKILLS / s / "SKILL.md"
        if not p.is_file(): continue
        t = section(p.read_text(encoding="utf-8"), r"Ordres pas à pas|Ce qu'il fait|Rythme")
        if t: out.append((f"**Selon [[skills/{s}|{s}]] :**\n" if len(skills_de(c["nom"])) > 1 else "") + t)
    return "\n\n".join(out) or AC + " (aucun skill ne décrit les étapes)."


def puces(xs, vide=AC): return "\n".join(f"- {x}" for x in xs) if xs else f"- {vide}"


def garde_mode(c):
    b = ["kill-switch `B2B\\STOP`", "lien Stripe non autorisé", "phrase interdite (OFFRE-REFERENCE.json)", "secret dans le texte"]
    if c["envoi_client"]: b.append("envoi client hors lundi-vendredi 08:00-19:00")
    a = ["machine non active", "envoi_automatique = false (simulation)", f"hors horaires du contrat ({c['heures']['debut']}-{c['heures']['fin']})", f"plafond de {c['plafonds']['messages_par_jour']} messages par jour"]
    return f"- Bloque : {', '.join(b)}.\n- Avertit : {', '.join(a)}."


def resultats_tests():
    try: return json.loads(RESULTATS_TESTS.read_text(encoding="utf-8"))
    except (OSError, ValueError): return {}


def lancer_tests(cs):
    env = dict(os.environ, JARVIS_TEST="1", PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1"); res = resultats_tests()
    for t in sorted({t for c in cs for t in c["tests"] if (RACINE / t).is_file()}):
        t0 = time.time()
        try: code = subprocess.run([sys.executable, str(RACINE / t)], cwd=str(RACINE), env=env, capture_output=True, timeout=300).returncode
        except subprocess.TimeoutExpired: code = "délai dépassé"
        res[t] = {"date": time.strftime("%Y-%m-%d %H:%M"), "ok": code == 0, "duree_s": round(time.time() - t0, 1)}
        print(f"  {'OK   ' if code == 0 else 'ECHEC'} {t}")
    RESULTATS_TESTS.parent.mkdir(parents=True, exist_ok=True); RESULTATS_TESTS.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")


def traces_recentes(nom, n=5):
    d = T.dossier_logs() / nom; out = []
    for f in (sorted(d.glob("*.jsonl"), reverse=True) if d.is_dir() else []):
        for l in reversed([x for x in f.read_text(encoding="utf-8").splitlines() if x.strip()]):
            try: x = json.loads(l)
            except ValueError: continue
            # sans donnée client : ni « commerce » ni « resultat », seulement l'heure, la commande, ok et l'erreur nettoyée
            err = f" ({T.nettoyer(x.get('erreur'))[:80]})" if x.get("erreur") else ""
            out.append(f"{str(x.get('heure', ''))[:16].replace('T', ' ')} | {T.nettoyer(x.get('decision'))[:40]} | {'ok' if x.get('ok') else 'ERREUR'}{err} | {x.get('duree_s', 0)} s")
            if len(out) >= n: return out
    return out


def dynamique(c):
    res = resultats_tests()
    lt = [f"- `{t}` : " + (f"{'réussi' if res[t]['ok'] else 'ÉCHEC'} le {res[t]['date']}" if t in res else "pas encore lancé par `generer-fiches.py --tests`") for t in c["tests"]]
    h = traces_recentes(c["nom"])
    return (f"{DYN_D}\n**Derniers résultats de test (cette machine) :**\n" + ("\n".join(lt) or "- aucun test") +
            f"\n\n**Dernière trace :** {R.derniere_trace(c['nom'])}\n\n### Historique (5 dernières traces, sans données client)\n" + ("\n".join(f"- {x}" for x in h) or "- aucune trace sur cette machine") + f"\n{DYN_F}")


def fiche(c, schema, t):
    nom, st = c["nom"], STATUT[c["statut"]]
    fm = ["---", f"agent: {nom}", f"statut: {st}"] + ([f"mode: {'simulation' if c['statut'] == 'simulation' else 'réel'}"] if st == "actif" else []) + \
         [f"responsable: {c['responsable']}", f"horaire: \"{horaire(c, t)}\"", f"machine: {machine(c, t)}", "tags: [agent-b2b]", "---"]
    tests = [f"`{x}`" + ("" if (RACINE / x).is_file() else " (FICHIER ABSENT)") for x in c["tests"]]
    sk = [f"[[skills/{s}|{s}]]" + ("" if (SKILLS / s / "SKILL.md").is_file() else f" (skill absent : {AC})") for s in skills_de(nom)]
    corps = f"""# {nom}

**Statut :** {st}{' (simulation : envoi_automatique = false)' if c['statut'] == 'simulation' else ''} · **Responsable :** {lien_resp(c['responsable'])} · **Machine :** {machine(c, t)}
**Horaire :** {horaire(c, t)}
**Script :** {f"`{c['script']}`" if c.get('script') else AC + ' (aucun script)'} · **Contrat :** `B2B/harness/contrats/{nom}.json`

## Mission
{c['mission']}

## Ce qu'il fait étape par étape
{etapes(c)}

## Entrées et sorties
**Lit :**
{puces(c['fichiers_lus'])}

**Écrit :**
{puces(c['fichiers_ecrits'])}

**Discord :** {', '.join(c['canaux_discord']) or 'aucun'} · **Plafond :** {c['plafonds']['messages_par_jour']} messages par jour · **Envoi au client :** {'oui, seulement après accord de Liam' if c['envoi_client'] else 'non'}

## Ce qu'il n'a pas le droit de faire
{puces(c['actions_interdites'])}
- Engager Liam (envoyer au client, encaisser, publier, signer) : `peut_engager: false`, tout passe par `B2B/a-valider/`.

## Harness
- **Contrat :** {'valide' if not valider(c, schema) else 'INVALIDE'} (`python B2B\\harness\\valider.py`)
- **Garde branchée :** {R.garde(c)}
{garde_mode(c)}
- **Tests :** {', '.join(tests) or 'aucun : ' + AC}
- **Alerte si silence :** {('après ' + c['alerte_si_silence'] + ' (surveillant)') if c.get('alerte_si_silence') else 'aucune'}

{dynamique(c)}

## Skill
{puces(sk)}

## Liens
- Responsable : {lien_resp(c['responsable'])}
- Direction : [[jarvis-ceo|Jarvis (CEO)]] · [[00-ORGANIGRAMME|Organigramme]]
"""
    return "\n".join(fm) + "\n" + DEBUT + "\n" + corps + FIN + "\n"


def responsable(r, cs):
    s = SKILLS / f"responsable-{r.lower()}" / "SKILL.md"
    ag = [c for c in cs if c["responsable"] == r]
    return f"""---
responsable: {r}
tags: [responsable-b2b]
---
{DEBUT}
# Responsable {r}

**Rend compte à :** [[jarvis-ceo|Jarvis (CEO)]] · [[00-ORGANIGRAMME|Organigramme]]
**Skill :** {f'[[skills/responsable-{r.lower()}|responsable-{r.lower()}]]' if s.is_file() else 'aucun : ' + AC}

## Ses agents
{puces([f"[[{c['nom']}]] ({STATUT[c['statut']]}) : {c['mission']}" for c in ag], 'aucun agent sous contrat : ' + AC)}
{FIN}
"""


def organigramme(cs):
    ceo = [c for c in cs if c["responsable"] == "Jarvis (CEO)"]
    lignes = ["# Organigramme B2B", "", "Généré depuis les contrats (`B2B/harness/contrats`). Liam décide ; Jarvis (CEO) pilote ; chaque responsable pilote ses agents.", "",
              "- Liam", "  - [[jarvis-ceo|Jarvis (CEO)]]"]
    for c in ceo: lignes.append(f"    - [[{c['nom']}]] ({STATUT[c['statut']]}, rattaché directement à Jarvis)")
    for r in RESPONSABLES:
        lignes.append(f"    - [[responsable-{r.lower()}|Responsable {r}]]")
        lignes += [f"      - [[{c['nom']}]] ({STATUT[c['statut']]})" for c in cs if c["responsable"] == r]
    m = ["```mermaid", "flowchart TD", '  liam["Liam"] --> ceo["Jarvis (CEO)"]']
    for c in ceo: m.append(f'  ceo --> {c["nom"].replace("-", "_")}["{c["nom"]} ({STATUT[c["statut"]]})"]')
    for r in RESPONSABLES:
        m.append(f'  ceo --> r_{r.lower()}["Responsable {r}"]')
        m += [f'  r_{r.lower()} --> {c["nom"].replace("-", "_")}["{c["nom"]} ({STATUT[c["statut"]]})"]' for c in cs if c["responsable"] == r]
    m.append("```")
    return "---\ntags: [organigramme]\n---\n" + DEBUT + "\n" + "\n".join(lignes + [""] + m) + "\n" + FIN + "\n"


def avec_notes(neuf, ancien):
    """Garde tout ce qui suit GENERE:FIN dans l'ancienne fiche (notes de Liam) ; sinon la zone vide par défaut."""
    reste = ancien.split(FIN, 1)[1].lstrip("\n") if ancien and FIN in ancien else NOTES
    return neuf + "\n" + reste


def sans_dynamique(t): return re.sub(re.escape(DYN_D) + r".*?" + re.escape(DYN_F), "", t, flags=re.S)


def attendus(cs):
    """{chemin: contenu généré (sans notes)} pour toutes les fiches, responsables, organigramme ; {chemin: texte} pour les copies de skills."""
    schema = json.loads((ICI / "contrat.schema.json").read_text(encoding="utf-8")); ts = taches()
    gen = {SORTIE / f"{c['nom']}.md": fiche(c, schema, ts.get(c["nom"])) for c in cs}
    gen.update({SORTIE / f"responsable-{r.lower()}.md": responsable(r, cs) for r in RESPONSABLES})
    gen[SORTIE / "00-ORGANIGRAMME.md"] = organigramme(cs)
    copies = {COPIES / f"{p.parent.name}.md": p.read_text(encoding="utf-8") for p in sorted(SKILLS.glob("*/SKILL.md"))}
    return gen, copies


def lire(p): return p.read_text(encoding="utf-8") if p.is_file() else None


def verifier(cs):
    gen, copies = attendus(cs); pb = []
    for p, t in gen.items():
        a = lire(p)
        if a is None: pb.append(f"fiche absente : {p.relative_to(RACINE)}"); continue
        if FIN not in a or sans_dynamique(a.split(FIN, 1)[0]) != sans_dynamique(t.split(FIN, 1)[0]): pb.append(f"fiche pas à jour : {p.relative_to(RACINE)}")
    for p, t in copies.items():
        if lire(p) != t: pb.append(f"copie de skill absente ou pas à jour : {p.relative_to(RACINE)}")
    for c in cs:
        if c["statut"] in ("actif", "simulation"):
            pb += [f"agent actif sans skill : {c['nom']} (.claude/skills/{s}/SKILL.md)" for s in skills_de(c["nom"]) if not (SKILLS / s / "SKILL.md").is_file()]
    return pb


def ecrire(p, t):
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f: f.write(t)


def main(argv=None):
    a = argparse.ArgumentParser(prog="generer-fiches"); a.add_argument("--verifier", action="store_true"); a.add_argument("--tests", action="store_true"); a = a.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8"); cs = contrats()
    if a.verifier:
        pb = verifier(cs)
        for x in pb: print("  ECHEC " + x)
        print(f"  OK    {len(cs)} fiches à jour, skills des agents actifs présents" if not pb else f"{len(pb)} problème(s) : python B2B\\harness\\generer-fiches.py")
        return 1 if pb else 0
    if a.tests: lancer_tests(cs)
    gen, copies = attendus(cs)
    for p, t in gen.items(): ecrire(p, avec_notes(t, lire(p)))
    for p in (COPIES.glob("*.md") if COPIES.is_dir() else []):
        if p not in copies: p.unlink()   # dossier entièrement généré : une copie sans source est retirée
    for p, t in copies.items(): ecrire(p, t)
    print(f"{len(cs)} fiches d'agents, {len(RESPONSABLES)} responsables, organigramme et {len(copies)} copies de skills écrits dans {SORTIE.relative_to(RACINE)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
