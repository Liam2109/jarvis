#!/usr/bin/env python3
"""Fiches Obsidian des agents (15/11/2026, un seul graphe depuis 20 h) : la fiche détaillée de chaque contrat est écrite DANS sa note
docs\\agents\\<nom de la note>.md (correspondance : B2B\\harness\\fiches-noms.json ; null = pas de note). La note « 🧠 Jarvis (CEO) » reçoit
en plus les responsables et l'organigramme (Mermaid). Graphe en arbre (22/11/2026) : Jarvis (CEO) -> les 4 superviseurs de domaine -> leurs agents
(AGENTS_SUIVIS) ; les agents sans domaine restent liés directement au CEO. Ces liens sont à la main dans « Liens et décisions » ; --verifier les contrôle (liens_arbre). Copie de chaque skill (.claude\\skills\\<skill>\\SKILL.md -> docs\\agents\\skills\\<skill>.md).
Lecture seule du code, sans réseau ni IA. Règle du graphe : la partie générée ne contient AUCUN lien [[...]] (chemins en texte simple).
Dans le frontmatter, seules les clés statut, mode, horaire, tags sont réécrites (les autres restent) ; seule la partie entre
<!-- GENERE:DEBUT --> et <!-- GENERE:FIN --> est réécrite ; les zones « Liens et décisions » et « Notes de Liam » qui suivent sont conservées.
Le bloc DYNAMIQUE (derniers tests, dernières traces) change d'une machine à l'autre : il n'entre pas dans la vérification.
  python B2B\\harness\\generer-fiches.py              régénère les fiches
  python B2B\\harness\\generer-fiches.py --tests      lance d'abord les tests des contrats (JARVIS_TEST=1) et note leur résultat (B2B\\logs\\agents\\_tests-fiches.json, hors git)
  python B2B\\harness\\generer-fiches.py --verifier   code 1 si une fiche manque ou n'est pas à jour, si un agent actif n'a pas de skill, ou si l'arbre des liens est faux (rien n'est écrit)"""
import argparse, json, os, re, subprocess, sys, time
from pathlib import Path

ICI = Path(__file__).resolve().parent
RACINE = ICI.parent.parent
sys.path.insert(0, str(ICI))
import traces as T   # noqa: E402
import rapport as R   # noqa: E402
from valider import valider   # noqa: E402
from domaines import domaines   # noqa: E402  agents de chaque superviseur de domaine (AGENTS_SUIVIS)

CONTRATS, SKILLS = ICI / "contrats", RACINE / ".claude" / "skills"
SORTIE = RACINE / "docs" / "agents"; COPIES = SORTIE / "skills"; NOMS_JSON = ICI / "fiches-noms.json"
ARCHIVES = RACINE / "docs" / "archives" / "agents-retires"   # fiches ET copies de skills des agents retirés (dossier ignoré du coffre Obsidian)
RETIRES = ("appels-liam", "vente-relances", "linkedin", "superviseur-sites", "superviseur-mail", "superviseur-videos", "jarvis-vue")   # copies de skills rangées dans ARCHIVES le 24/11/2026 (sources .claude\\skills gardées)
TACHES = RACINE / "B2B" / "agents" / "serveur-taches.json"
DEBUT, FIN = "<!-- GENERE:DEBUT (régénéré par python B2B\\harness\\generer-fiches.py : ne pas modifier) -->", "<!-- GENERE:FIN -->"
DYN_D, DYN_F = "<!-- DYNAMIQUE:DEBUT -->", "<!-- DYNAMIQUE:FIN -->"
NOTES = "## Notes de Liam\n\n_Zone libre, conservée telle quelle à chaque régénération._\n"
LIENS = "## Liens et décisions\n\n_Zone conservée à chaque régénération : liens vers docs\\decisions et docs clés seulement._\n"
GENERES = ("statut", "mode", "horaire", "tags")   # clés du frontmatter réécrites ; les autres sont gardées
MISSIONS_RESP = {"Prospection": "Remplir chaque jour ouvré la journée de vente : entreprises trouvées, lots d'e-mails validés par Liam, liste d'appels prête pour Sid à 7 h 30.",
                 "Vente": "Transformer réponses et rendez-vous en devis montrés à Liam, puis relancer, sans jamais rien envoyer au client sans son accord.",
                 "Argent": "Suivre les paiements Stripe en lecture seule et prévenir Liam de chaque encaissement.",
                 "Production": "Produire les pages et sites des clients, validés par Liam avant toute mise en ligne."}
AC = "à compléter par Liam"
STATUT = {"actif": "actif", "simulation": "actif", "inactif": "arrêté", "prevu": "prévu"}
SKILLS_AGENT = {"prospection": ["agent-recherche", "agent-lots-emails"], "jarvis-ceo": ["jarvis-ceo"]}   # sinon agent-<nom>
RESPONSABLES = ["Prospection", "Vente", "Argent", "Production"]
JOURS = ["lun", "mar", "mer", "jeu", "ven", "sam", "dim"]
RESULTATS_TESTS = T.dossier_logs() / "_tests-fiches.json"


def texte_resp(r): return r if r in ("Jarvis (CEO)", "Liam") else f"{r} (pôle)"
def skills_de(nom): return SKILLS_AGENT.get(nom, [f"agent-{nom}"])
def contrats(): return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(CONTRATS.glob("*.json"))]
def noms(): return {k: v for k, v in json.loads(NOMS_JSON.read_text(encoding="utf-8")).items() if not k.startswith("_")}
def sans_liens(t): return re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", t)   # [[cible|texte]] -> texte
def q(v): return '"' + str(v).replace("\\", "\\\\").replace('"', '\\"') + '"'


def taches():
    try: return json.loads(TACHES.read_text(encoding="utf-8"))["agents"]
    except (OSError, ValueError, KeyError): return {}


def jours_txt(js): return "tous les jours" if sorted(js) == list(range(7)) else ("lundi-vendredi" if sorted(js) == list(range(5)) else ", ".join(JOURS[j] for j in sorted(js)))


def horaire(c, t):
    if c["statut"] == "prevu": return AC
    plage = f"{jours_txt(c['jours'])} {c['heures']['debut']}-{c['heures']['fin']}"
    if not t: return f"à la demande (aucune tâche serveur), plage {plage}"
    q = f"chaque jour à {', '.join([t['heure']] + list(t.get('heures_en_plus') or []))}" if t.get("heure") else f"toutes les {t.get('toutes_minutes')} min"
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
        if t: out.append((f"**Selon le skill `{s}` :**\n" if len(skills_de(c["nom"])) > 1 else "") + t)
    return "\n\n".join(out) or AC + " (aucun skill ne décrit les étapes)."


def puces(xs, vide=AC): return "\n".join(f"- {x}" for x in xs) if xs else f"- {vide}"


# Chaîne vidéo (17/11/2026) : ordre d'un passage, de bout en bout. (agent ou None pour l'étape de Liam, libellé, ce qui passe à l'étape suivante)
CHAINE_VIDEO = [("videos-veille", "Veille", "note du jour (Videos/veille) + formules d'accroche (hooks.md)"),
                ("videos-scripts", "Scripts", "script + légende (Videos/scripts/AAAA-MM-JJ-HHMM.json)"),
                ("videos-marketing", "Marketing", "script enrichi : accroche gardée, rythme, sous-titres"),
                ("videos-creation", "Création", "vidéo rendue (ligne A : directement dans Videos/a-valider)"),
                ("videos-monteur", "Monteur (ligne B)", "sketch monté et contrôlé, rangé dans Videos/a-valider (sinon Videos/a-part)"),
                (None, "Ton OK de Liam (« go publier », une fois par ligne)", "ligne ouverte : go_publier = true dans la config locale"),
                ("videos-publication", "Publication (verrouillée)", "vidéo publiée, déplacée dans Videos/publiees"),
                ("videos-nettoyage", "Nettoyage", "vieux fichiers supprimés après une ligne de journal-videos.csv")]
NOTE_CHAINE = "⛓️ Chaîne vidéo"
REGLES_VIDEO = "Videos/SKILL-VIDEOS.md (règles communes de l'équipe Vidéos, relues avant chaque exécution ; absentes ou incomplètes = refus, code 3)"


def chaine_txt(nom):
    """Place d'un agent vidéo dans la chaîne (texte simple, sans lien) ; vide pour les autres agents."""
    ids = [a for a, _, _ in CHAINE_VIDEO]
    if nom not in ids: return ""
    i = ids.index(nom); lib = lambda j: CHAINE_VIDEO[j][1]
    amont = f"{lib(i - 1)} : {CHAINE_VIDEO[i - 1][2]}" if i > 0 else "aucun (premier maillon)"
    aval = lib(i + 1) if i + 1 < len(CHAINE_VIDEO) else "aucun (dernier maillon)"
    sens = " → ".join(("**" + l + "**") if a == nom else l for a, l, _ in CHAINE_VIDEO)
    return (f"**Chaîne vidéo :** {sens} (fiche « {NOTE_CHAINE} »)\n- **Reçoit de :** {amont}\n- **Produit :** {CHAINE_VIDEO[i][2]}\n- **Passe à :** {aval}\n\n")


def regles_txt(nom): return f"- Règles : {REGLES_VIDEO}\n" if nom.startswith("videos-") else ""


def tache_txt(nom, t):
    if not t: return "aucune (appelé par un autre agent ou lancé à la main)" if nom == "videos-monteur" else "aucune dans serveur-taches.json"
    return (f"entrée dans `B2B/agents/serveur-taches.json`" + (f", active à partir du {t['actif_le']}" if t.get("actif_le") else "") +
            " ; tourne seulement si l'agent est dans `agents_actifs` (choix de Liam)")


def note_chaine(cs, ts, ancien):
    """Note « ⛓️ Chaîne vidéo » : sens des flèches de bout en bout (Mermaid) et tableau des maillons ; aucun lien [[...]] (reliée par la note de Jarvis (CEO))."""
    par = {c["nom"]: c for c in cs}; n = noms()
    m = ["```mermaid", "flowchart LR", '  ceo["Jarvis (CEO)"] -.-> veille']
    ids = []
    for a, l, _ in CHAINE_VIDEO:
        i = (a or "ton_ok").replace("videos-", "").replace("-", "_"); ids.append(i)
        st = f" ({STATUT[par[a]['statut']]})" if a in par else ""
        m.append(f'  {i}["{(n.get(a) or l) if a else "✅ " + l}{st}"]')
    m += [f'  {ids[k]} -->|"{CHAINE_VIDEO[k][2].split(" (")[0]}"| {ids[k + 1]}' for k in range(len(ids) - 1)] + ["```"]
    lignes = ["| Étape | Agent | Horaire | Statut | Produit |", "|---|---|---|---|---|"]
    for k, (a, l, prod) in enumerate(CHAINE_VIDEO, 1):
        if a in par: lignes.append(f"| {k} | {n.get(a) or a} (`{a}`) | {horaire(par[a], ts.get(a))} | {STATUT[par[a]['statut']]} | {prod} |")
        else: lignes.append(f"| {k} | {l} | quand Liam a vu la première vidéo de la ligne | décision de Liam | {prod} |")
    corps = (f"# {NOTE_CHAINE}\n\nSens d'un passage, de bout en bout (06:00, 14:00, 22:00). Rattachée à Jarvis (CEO). Généré depuis les contrats `B2B/harness/contrats/videos-*.json` et `B2B/agents/serveur-taches.json`.\n\n"
             + "\n".join(m) + "\n\n" + "\n".join(lignes) + "\n\n"
             "- Le Monteur est appelé par la Création pour chaque sketch de la ligne B (aucune tâche à lui) ; la ligne A passe directement de la Création au ton OK.\n"
             "- Rien n'est publié avant le « go publier » de Liam pour la ligne ; la Publication reste verrouillée (contrat `inactif`).\n"
             "- Aucun agent vidéo ne tourne tant que Liam ne l'a pas ajouté à `agents_actifs` (`B2B/agents/b2b.local.json`).\n"
             f"- Règles communes : {REGLES_VIDEO}.\n"
             "- Pas de preuve = pas de fait : l'état de chaque maillon se lit dans sa fiche (rubrique « Horaire et état ») et dans `B2B/logs/agents/<agent>/`.\n")
    fm, reste = decouper(ancien)
    entete = "---\n" + "\n".join(fm or ["aliases: [⛓️ Chaîne vidéo]", "tags: [chaine-video]"]) + "\n---\n"
    return entete + DEBUT + "\n" + sans_liens(corps) + FIN + "\n" + "\n" + zone_conservee(reste)


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


def derniere_erreur(nom):
    """Dernière trace ok:false (heure, commande, erreur nettoyée), sur 30 jours au plus ; « aucune » sinon."""
    d = T.dossier_logs() / nom
    for f in (sorted(d.glob("*.jsonl"), reverse=True)[:30] if d.is_dir() else []):
        for l in reversed(f.read_text(encoding="utf-8").splitlines()):
            try: x = json.loads(l)
            except ValueError: continue
            if not x.get("ok"): return f"{str(x.get('heure', ''))[:16].replace('T', ' ')} {T.nettoyer(x.get('decision'))[:40]} ({T.nettoyer(x.get('erreur'))[:80]})"
    return "aucune"


def actif_ici(nom):
    try:
        sys.path.insert(0, str(RACINE / "B2B" / "agents")); import machine as M
        return "oui" if nom in M.agents_actifs() else "non (Liam l'ajoute s'il veut le planifier)"
    except Exception: return "inconnu"


def dynamique(c):
    res = resultats_tests()
    lt = [f"- `{t}` : " + (f"{'réussi' if res[t]['ok'] else 'ÉCHEC'} le {res[t]['date']}" if t in res else "pas encore lancé par `generer-fiches.py --tests`") for t in c["tests"]]
    h = traces_recentes(c["nom"])
    return (f"{DYN_D}\n**Derniers résultats de test (cette machine) :**\n" + ("\n".join(lt) or "- aucun test") +
            f"\n\n**Dernière trace :** {R.derniere_trace(c['nom'])} · **Dernière erreur :** {derniere_erreur(c['nom'])} · **Dans agents_actifs (cette machine) :** {actif_ici(c['nom'])}\n\n### Historique (5 dernières traces, sans données client)\n" + ("\n".join(f"- {x}" for x in h) or "- aucune trace sur cette machine") + f"\n{DYN_F}")


def entete(c, t, titre, ancien_fm):
    """Frontmatter : celui de la note (ordre et valeurs gardés) + statut, mode, horaire, tags recalculés ; pour une note neuve, un frontmatter complet."""
    if ancien_fm is None:
        ancien_fm = [f"agent: {c['nom']}", f"aliases: [{titre}]", f"name: {c['nom']}", f"role: {q(c['mission'])}", f"machine: {q(machine(c, t))}",
                     f"planification: {q(horaire(c, t))}", f"sorties: {q(', '.join(c['fichiers_ecrits']) or AC)}"]
    l = [x for x in ancien_fm if x.split(":", 1)[0].strip() not in GENERES]
    if not any(x.split(":", 1)[0].strip() == "responsable" for x in l): l.append(f"responsable: {c['responsable']}")
    st = STATUT[c["statut"]]
    l += [f"statut: {st}"] + ([f"mode: {'simulation' if c['statut'] == 'simulation' else 'réel'}"] if st == "actif" else []) + [f"horaire: {q(horaire(c, t))}", "tags: [agent-b2b]"]
    return "---\n" + "\n".join(l) + "\n---\n"


def actifs_au_registre(cs, n): return [c for c in cs if n.get(c["nom"]) or c["nom"] not in n]   # agent archivé (null dans fiches-noms.json) : ni dans l'organigramme ni dans les responsables


def libelle(c, n): return f"{n.get(c['nom']) or c['nom']} ({STATUT[c['statut']]})"


def responsables(cs, n):
    cs = actifs_au_registre(cs, n)
    l = ["## Responsables", "", "Liam décide ; Jarvis (CEO) pilote ; chaque responsable pilote ses agents et rend compte à Jarvis.", "",
         "- **Rattachés directement à Jarvis (CEO) :** " + (", ".join(libelle(c, n) for c in cs if c["responsable"] == "Jarvis (CEO)") or "aucun") + "."]
    for r in RESPONSABLES:
        ag = [libelle(c, n) for c in cs if c["responsable"] == r]
        l.append(f"- **{r} :** {MISSIONS_RESP[r]} Agents : {', '.join(ag) or 'aucun sous contrat'}.")
    return "\n".join(l)


def organigramme(cs, n):
    cs = actifs_au_registre(cs, n)
    ceo = [c for c in cs if c["responsable"] == "Jarvis (CEO)"]
    m = ["## Organigramme", "", "Généré depuis les contrats (`B2B/harness/contrats`).", "", "```mermaid", "flowchart TD", '  liam["Liam"] --> ceo["Jarvis (CEO)"]']
    for c in ceo: m.append(f'  ceo --> {c["nom"].replace("-", "_")}["{libelle(c, n)}"]')
    for r in RESPONSABLES:
        m.append(f'  ceo --> r_{r.lower()}["Responsable {r}"]')
        m += [f'  r_{r.lower()} --> {c["nom"].replace("-", "_")}["{libelle(c, n)}"]' for c in cs if c["responsable"] == r]
    return "\n".join(m + ["```"])


def fiche(c, schema, t, titre, cs, n):
    """Bloc GENERE (sans frontmatter), sans aucun lien [[...]]."""
    nom, st = c["nom"], STATUT[c["statut"]]
    tests = [f"`{x}`" + ("" if (RACINE / x).is_file() else " (FICHIER ABSENT)") for x in c["tests"]]
    sk = [f"`.claude/skills/{s}/SKILL.md` (copie : `docs/agents/skills/{s}.md`)" if (SKILLS / s / "SKILL.md").is_file() else f"`{s}` (skill absent : {AC})" for s in skills_de(nom)]
    corps = f"""# {titre}

**Agent :** `{nom}` · **Statut :** {st}{' (simulation : envoi_automatique = false)' if c['statut'] == 'simulation' else ''} · **Responsable :** {texte_resp(c['responsable'])} · **Machine :** {machine(c, t)}
**Horaire :** {horaire(c, t)}
**Script :** {f"`{c['script']}`" if c.get('script') else AC + ' (aucun script)'} · **Contrat :** `B2B/harness/contrats/{nom}.json`

## Rôle et limites
### Mission
{c['mission']}

### Ce qu'il fait étape par étape
{etapes(c)}

### Ce qu'il n'a pas le droit de faire
{puces(c['actions_interdites'])}
- Engager Liam (envoyer au client, encaisser, publier, signer) : `peut_engager: false`, tout passe par `B2B/a-valider/`.

## Entrées et sorties
{chaine_txt(nom)}**Lit :**
{puces(c['fichiers_lus'])}

**Écrit :**
{puces(c['fichiers_ecrits'])}

**Discord :** {', '.join(c['canaux_discord']) or 'aucun'} · **Plafond :** {c['plafonds']['messages_par_jour']} messages par jour · **Envoi au client :** {'oui, seulement après accord de Liam' if c['envoi_client'] else 'non'}

## Horaire et état
- **Horaire :** {horaire(c, t)}
- **Tâche serveur :** {tache_txt(nom, t)}
- **Contrat :** {'valide' if not valider(c, schema) else 'INVALIDE'} (`python B2B\\harness\\valider.py`)
- **Garde branchée :** {R.garde(c)}
{garde_mode(c)}
- **Tests :** {', '.join(tests) or 'aucun : ' + AC}
- **Alerte si silence :** {('après ' + c['alerte_si_silence'] + ' (surveillant)') if c.get('alerte_si_silence') else 'aucune'}

{dynamique(c)}

## Skill et règles
{puces(sk)}
{regles_txt(nom)}- Pas de preuve = pas de fait : « il a tourné » = une trace du jour `ok: true` ci-dessus ; « c'est corrigé » = ses tests puis `tests\\b2b-rapide.ps1` en vert.
"""
    if nom == "jarvis-ceo": corps += "\n" + responsables(cs, n) + "\n\n" + organigramme(cs, n) + "\n"
    return DEBUT + "\n" + sans_liens(corps) + FIN + "\n"


def decouper(texte):
    """-> (lignes du frontmatter ou None, texte qui suit le frontmatter)."""
    m = re.match(r"---\n(.*?)\n---\n?", texte or "", re.S)
    return (m.group(1).splitlines(), texte[m.end():]) if m else (None, texte or "")


def zone_conservee(reste):
    """Ce qui suit GENERE:FIN (Liens et décisions, Notes de Liam) ; à la première exécution, le corps de l'ancienne note courte (sans son titre)."""
    if FIN in reste: return reste.split(FIN, 1)[1].lstrip("\n")
    corps = "\n".join(l for l in reste.strip("\n").splitlines() if not l.startswith("# ")).strip()
    return LIENS + "\n" + (corps or "Liens : aucun pour l'instant.") + "\n\n" + NOTES


def note(c, schema, t, titre, ancien, cs, n):
    fm, reste = decouper(ancien)
    return entete(c, t, titre, fm) + fiche(c, schema, t, titre, cs, n) + "\n" + zone_conservee(reste)


def sans_dynamique(t): return re.sub(re.escape(DYN_D) + r".*?" + re.escape(DYN_F), "", t, flags=re.S)


def cibles(cs):
    """-> (correspondance, [(contrat, chemin de la note)]) pour les agents qui ont une note."""
    n = noms(); return n, [(c, SORTIE / f"{n[c['nom']]}.md") for c in cs if n.get(c["nom"])]


def skills_retires(): return {s for r in RETIRES for s in skills_de(r)}


def copies_skills(): return {COPIES / f"{p.parent.name}.md": sans_liens(p.read_text(encoding="utf-8")) for p in sorted(SKILLS.glob("*/SKILL.md")) if p.parent.name not in skills_retires()}


def lire(p): return p.read_text(encoding="utf-8") if p.is_file() else None


def liens_arbre(n):
    """Arbre du graphe Obsidian (22/11/2026) : un agent suivi par un superviseur est lié depuis la note de SON superviseur, et plus depuis « 🧠 Jarvis (CEO) ».
    Ces liens vivent dans la zone « Liens et décisions », conservée à chaque régénération (la partie générée n'a aucun lien) : écrits à la main, ce contrôle les garde justes."""
    pb = []; ceo_nom = n.get("jarvis-ceo"); ceo = lire(SORTIE / f"{ceo_nom}.md") or ""
    for sup, (d, agents) in domaines().items():
        if not n.get(sup): continue      # superviseur archivé (null dans fiches-noms.json) : plus de note, plus de contrôle
        s = lire(SORTIE / f"{n[sup]}.md")
        if s is None: pb.append(f"note du superviseur absente : {n.get(sup) or sup}"); continue
        if f"|{ceo_nom}]]" not in s: pb.append(f"{n[sup]} : aucun lien vers « {ceo_nom} » dans « Liens et décisions »")
        for a in agents:
            if not n.get(a): continue
            if f"|{n[a]}]]" not in s: pb.append(f"{n[sup]} : lien manquant vers « {n[a]} » (agent du domaine {d})")
            if f"|{n[a]}]]" in ceo: pb.append(f"{ceo_nom} : lien direct vers « {n[a]} » à retirer (cet agent dépend de « {n[sup]} »)")
    return pb


def verifier(cs):
    schema = json.loads((ICI / "contrat.schema.json").read_text(encoding="utf-8")); ts = taches(); pb = []
    n, cb = cibles(cs); copies = copies_skills()
    pb += [f"contrat sans entrée dans B2B/harness/fiches-noms.json : {c['nom']}" for c in cs if c["nom"] not in n]
    for c, p in cb:
        a = lire(p)
        if a is None: pb.append(f"note absente : {p.relative_to(RACINE)}"); continue
        t = note(c, schema, ts.get(c["nom"]), p.stem, a, cs, n)
        if FIN not in a or sans_dynamique(a.split(FIN, 1)[0]) != sans_dynamique(t.split(FIN, 1)[0]): pb.append(f"bloc GENERE pas à jour : {p.relative_to(RACINE)}")
    for p, t in copies.items():
        if lire(p) != t: pb.append(f"copie de skill absente ou pas à jour : {p.relative_to(RACINE)}")
    for s in sorted(skills_retires()):   # une copie d'agent retiré vit dans l'archive, jamais dans le coffre ; un agent retiré n'a plus de note
        if (COPIES / f"{s}.md").exists(): pb.append(f"copie de skill d'un agent retiré à ranger dans {ARCHIVES.relative_to(RACINE)} : docs/agents/skills/{s}.md")
        if not (ARCHIVES / f"{s}.md").is_file(): pb.append(f"copie archivée absente : {ARCHIVES.relative_to(RACINE)}/{s}.md")
    pb += [f"« {r} » est dans RETIRES mais a encore une note dans fiches-noms.json" for r in RETIRES if n.get(r)]
    pc = SORTIE / f"{NOTE_CHAINE}.md"; a = lire(pc)
    if a is None or FIN not in a or a.split(FIN, 1)[0] != note_chaine(cs, ts, a).split(FIN, 1)[0]: pb.append(f"note de la chaîne vidéo absente ou pas à jour : {pc.relative_to(RACINE)}")
    pb += liens_arbre(n)
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
        print(f"  OK    {len(cibles(cs)[1])} notes d'agents à jour dans docs/agents, skills des agents actifs présents" if not pb else f"{len(pb)} problème(s) : python B2B\\harness\\generer-fiches.py")
        return 1 if pb else 0
    if a.tests: lancer_tests(cs)
    schema = json.loads((ICI / "contrat.schema.json").read_text(encoding="utf-8")); ts = taches(); n, cb = cibles(cs); copies = copies_skills()
    for c, p in cb: ecrire(p, note(c, schema, ts.get(c["nom"]), p.stem, lire(p), cs, n))   # relue juste avant d'être écrite (Obsidian peut être ouvert)
    pc = SORTIE / f"{NOTE_CHAINE}.md"; ecrire(pc, note_chaine(cs, ts, lire(pc)))
    for p in (COPIES.glob("*.md") if COPIES.is_dir() else []):
        if p not in copies: p.unlink()   # dossier entièrement généré : une copie sans source est retirée
    for p, t in copies.items(): ecrire(p, t)
    print(f"{len(cb)} notes d'agents (bloc GENERE) et {len(copies)} copies de skills écrites dans {SORTIE.relative_to(RACINE)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
