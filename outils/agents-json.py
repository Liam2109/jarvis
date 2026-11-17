#!/usr/bin/env python3
"""Tableau de bord « Jarvis - Mon entreprise » : écrit dashboard/agents.json, agents.js (même contenu, lu par la page même en file://) et docs.js (onglets À faire, Journal, Décisions, Idées).

Lecture seule, sans réseau ni token Claude. Sources : B2B/agents/*.py (un agent = un script qui appelle M.exiger), leur .md, docs/agents/agent-<nom>.md,
B2B/agents/b2b.local.json, B2B/agents/serveur-taches.json, les fichiers *-etat.json et *-journal.log, les tâches planifiées Windows Jarvis-B2B-* de CE PC.
Un nouvel agent apparaît seul dès que son script est créé dans B2B/agents/.

Confidentialité : AUCUN secret ni donnée de prospect. Seuls sortent : noms d'agents, rôles (docs), horaires, dates, mots d'action du journal (2e colonne,
jamais la 3e qui peut contenir un nom d'entreprise) et des COMPTES (nombres). Aucune lecture de .env, de jeton ni de config locale autre que b2b.local.json.

  python outils/agents-json.py          écrit les deux fichiers (écriture atomique)
  python outils/agents-json.py --ouvrir écrit puis ouvre dashboard/index.html dans le navigateur par défaut (icône du bureau)
"""
import json, os, re, socket, subprocess, sys
from datetime import datetime, date
from pathlib import Path
from urllib.parse import quote

RACINE = Path(__file__).resolve().parent.parent
AGENTS = RACINE / "B2B" / "agents"
NOTES = RACINE / "docs" / "agents"
SORTIE = RACINE / "dashboard"
SANS_FENETRE = 0x08000000 if os.name == "nt" else 0          # CREATE_NO_WINDOW : jamais de fenêtre qui clignote
ERREUR = re.compile(r"erreur|échec|echec|suspendu|plant|exception", re.I)
LIGNE_JOURNAL = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}(?::\d{2})?)\s*\|\s*([^|]*?)\s*(?:\||$)")


def lire_json(p, defaut=None):
    try: return json.loads(Path(p).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError): return defaut


def est_archive(p):
    """Agent archivé : son .md commence par « Agent retiré … Archive. » (ex. instagram, retiré le 14/11/2026) : gardé sur disque, absent du tableau de bord."""
    try: return p.with_suffix(".md").read_text(encoding="utf-8-sig").lstrip().startswith("Agent retiré")
    except OSError: return False


def est_agent(p):
    if p.name.startswith("test") or p.suffix != ".py": return False
    try: return "M.exiger(" in p.read_text(encoding="utf-8", errors="ignore") and not est_archive(p)
    except OSError: return False


def frontmatter(p):
    """Clés simples « cle: valeur » de l'en-tête --- d'une note Obsidian."""
    try: t = p.read_text(encoding="utf-8")
    except OSError: return {}
    m = re.match(r"---\s*\n(.*?)\n---", t, re.S)
    return {k.strip(): v.strip().strip('"') for k, v in (l.split(":", 1) for l in m.group(1).splitlines() if ":" in l)} if m else {}


def note_de(nom):
    """Note Obsidian de l'agent : docs/agents/*.md dont l'en-tête porte « agent: <nom> » (noms de fichiers courts en français)."""
    for p in NOTES.glob("*.md"):
        if frontmatter(p).get("agent") == nom: return p
    return NOTES / f"{nom}.md"


def role_doc(nom):
    """Rôle : note docs/agents d'abord (courte), puis la ligne « Rôle : » du .md de l'agent, puis la 1re ligne de la docstring."""
    fm = frontmatter(note_de(nom))
    if fm.get("role"): return fm["role"]
    try:
        for l in (AGENTS / f"{nom}.md").read_text(encoding="utf-8").splitlines():
            if l.startswith("Rôle"): return re.sub(r"[*`]", "", l.split(":", 1)[1]).strip()[:220]
    except OSError: pass
    try:
        m = re.search(r'"""(.*?)(?:\n|""")', (AGENTS / f"{nom}.py").read_text(encoding="utf-8"), re.S)
        return m.group(1).strip()[:220] if m else ""
    except OSError: return ""


def journal(nom):
    """-> (dernier passage, dernier résultat, dernière erreur, 30 dernières lignes) : date + mot d'action seulement (jamais la 3e colonne)."""
    dernier = resultat = erreur = None; liste = []
    try: lignes = (AGENTS / f"{nom}-journal.log").read_text(encoding="utf-8", errors="ignore").splitlines()[-400:]
    except OSError: lignes = []
    for l in lignes:
        m = LIGNE_JOURNAL.match(l)
        if not m: continue
        quand, action = m.group(1), m.group(2)[:60]
        dernier, resultat = quand, action; liste.append([quand, action])
        if ERREUR.search(action): erreur = {"date": quand, "action": action}
    return dernier, resultat, erreur, liste[-30:]


POLES = {"prospection": "Trouver", "page-exemple": "Trouver", "appels-sid": "Vendre", "appels-liam": "Vendre", "rendez-vous": "Vendre", "reponses": "Vendre", "devis": "Vendre",
         "stripe-alerte": "Encaisser", "resume-sid": "Communiquer"}     # tout nouvel agent : « Autres »


def lignes_du_jour(nom, jour):
    """Nombre de lignes du journal de l'agent datées d'aujourd'hui (activité du jour, un compte)."""
    try: return sum(1 for l in (AGENTS / f"{nom}-journal.log").read_text(encoding="utf-8", errors="ignore").splitlines() if l.startswith(jour))
    except OSError: return None


def sections_md(p, niveau=r"#{1,3}"):
    """Fichier .md -> [{titre, texte}] découpé aux titres ; texte tel quel (docs suivies par git, sans donnée de prospect)."""
    try: t = Path(p).read_text(encoding="utf-8-sig")
    except OSError: return []
    out, cur = [], {"titre": Path(p).stem, "texte": []}
    for l in t.splitlines():
        if re.match(niveau + r"\s", l):
            if "".join(cur["texte"]).strip() or out == []: out.append(cur)
            cur = {"titre": l.lstrip("#").strip(), "texte": []}
        else: cur["texte"].append(l)
    out.append(cur)
    return [{"titre": s["titre"], "texte": "\n".join(s["texte"]).strip()} for s in out if s["titre"] or "".join(s["texte"]).strip()]


def documents():
    """Onglets À faire, Journal, Décisions, Idées (fichiers .md suivis par git)."""
    b2b = RACINE / "B2B" / "docs"
    try: jl = [l for l in (b2b / "JOURNAL-B2B.md").read_text(encoding="utf-8-sig").splitlines() if l.strip()][-50:]
    except OSError: jl = []
    journal_b2b = [{"titre": re.sub(r"[*`]", "", l.lstrip("- "))[:110], "texte": l.lstrip("- ")} for l in reversed(jl)]
    decisions = []
    for p in sorted((RACINE / "docs" / "decisions").glob("*.md")):
        t = re.sub(r"^---.*?---\s*", "", p.read_text(encoding="utf-8-sig"), flags=re.S)
        titre = next((l.lstrip("# ").strip() for l in t.splitlines() if l.startswith("#")), p.stem)
        decisions.append({"titre": titre, "texte": "\n".join(l for l in t.splitlines() if not l.startswith("#")).strip()})
    return {"a_faire": sections_md(b2b / "TODO-B2B.md"), "journal": journal_b2b, "decisions": decisions, "idees": sections_md(b2b / "IDEES-MASTER.md")}


def taches_windows():
    """Tâches Jarvis-B2B-* de CE PC -> {agent: actif?}."""
    try: out = subprocess.run(["schtasks", "/query", "/fo", "csv", "/nh"], capture_output=True, text=True, timeout=20, creationflags=SANS_FENETRE).stdout
    except Exception: return {}
    t = {}
    for l in out.splitlines():
        c = [x.strip('"') for x in l.split('","')]
        if c and c[0].startswith("\\Jarvis-B2B-"): t[c[0][len("\\Jarvis-B2B-"):]] = len(c) > 2 and "sactiv" not in c[2].lower() and "disabled" not in c[2].lower()
    return t


def processus_python():
    """Lignes de commande des python(w).exe en cours (pour savoir quel agent tourne). Rien n'est gardé d'autre que le nom du script."""
    if os.name != "nt": return ""
    cmd = "Get-CimInstance Win32_Process -Filter \"Name='python.exe' or Name='pythonw.exe'\" | ForEach-Object { $_.CommandLine }"
    try: return subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd], capture_output=True, text=True, timeout=30, creationflags=SANS_FENETRE).stdout
    except Exception: return ""


def chiffres_du_jour(jour):
    """Comptes seulement (aucun nom, e-mail ni téléphone)."""
    j = jour.isoformat(); c = {"jour": j}
    rdv = (lire_json(AGENTS / "rendez-vous-etat.json", {}) or {}).get("rdv", {})
    vivants = [v for v in rdv.values() if "annul" not in str(v.get("statut", "")).lower()]
    c["rendez_vous_aujourdhui"] = sum(1 for v in vivants if str(v.get("debut", "")).startswith(j))
    c["rendez_vous_a_venir"] = sum(1 for v in vivants if str(v.get("debut", ""))[:10] >= j)
    p = lire_json(AGENTS / "prospection-etat.json", {}) or {}
    c["prospects_trouves_aujourdhui"] = int((p.get("recherches") or {}).get(j, 0) or 0)
    c["prospects_dans_les_lots_aujourdhui"] = sum((p.get("lots") or {}).get(j, {}).values()) if isinstance((p.get("lots") or {}).get(j), dict) else 0
    c["emails_envoyes_aujourdhui"] = sum(1 for v in (p.get("envois") or {}).values() if str(v.get("date", "")).startswith(j))
    c["emails_envoyes_total"] = len(p.get("envois") or {})
    d = (lire_json(AGENTS / "devis-etat.json", {}) or {}).get("devis", {})
    c["devis_prepares_aujourdhui"] = sum(1 for v in d.values() if (v.get("historique") or {}).get("préparé") == j)
    c["devis_en_cours"] = sum(1 for v in d.values() if v.get("statut") in ("préparé", "validé", "envoyé", "accepté"))
    c["devis_payes"] = sum(1 for v in d.values() if v.get("statut") == "payé")
    listes = (lire_json(AGENTS / "appels-sid-etat.json", {}) or {}).get("listes", {})
    c["appels_sid_aujourdhui"] = int((listes.get(j) or {}).get("nombre", 0) or 0)
    return c


def construire(maintenant=None):
    maintenant = maintenant or datetime.now()
    local = lire_json(AGENTS / "b2b.local.json", {}) or {}
    machine_active = str(local.get("machine_active", "") or "")
    ce_pc = os.environ.get("COMPUTERNAME") or socket.gethostname()
    serveur = (lire_json(AGENTS / "serveur-taches.json", {}) or {}).get("agents", {})
    taches, procs = taches_windows(), processus_python()
    agents = []
    for py in sorted(AGENTS.glob("*.py")):
        if not est_agent(py): continue
        nom = py.stem; s = serveur.get(nom, {})
        horaire = (f"chaque jour à {s['heure']}" if s.get("heure") else f"toutes les {s['toutes_minutes']} min" if s.get("toutes_minutes") else "")
        dernier, resultat, erreur, lignes_journal = journal(nom)
        tourne = re.search(rf"[\\/]{re.escape(py.name)}\b", procs or "") is not None
        planifie_ici = taches.get(nom, False)
        etat = lire_json(AGENTS / f"{nom}-etat.json", {}) or {}
        suspendu = bool(etat.get("suspendu"))
        en_erreur = suspendu or (erreur is not None and erreur["date"] == dernier)
        statut = "erreur" if en_erreur else "actif" if (tourne or planifie_ici) else "inactif"
        note = note_de(nom)
        agents.append({
            "nom": nom, "role": role_doc(nom),
            "machine": f"serveur {machine_active}" if s and machine_active and machine_active != ce_pc else (machine_active or "aucune machine active"),
            "planifie": bool(s), "horaire": horaire or "non planifié sur le serveur",
            "planifie_sur_ce_pc": planifie_ici, "tourne_sur_ce_pc": tourne,
            "statut": statut, "suspendu": suspendu,
            "dernier_passage": dernier, "dernier_resultat": resultat, "derniere_erreur": erreur,
            "pole": POLES.get(nom, "Autres"), "journal": lignes_journal,
            "responsable": frontmatter(note).get("responsable") or None,   # « responsable: prospection » dans l'en-tête de la note docs/agents (organigramme du 14/11/2026), None sinon
            "note": str(note.relative_to(RACINE)).replace("\\", "/") if note.exists() else None,
            "note_obsidian": ("obsidian://open?path=" + quote(str(note), safe="")) if note.exists() else None,
        })
    c = chiffres_du_jour(maintenant.date()); j = maintenant.date().isoformat()
    du_jour = {"prospection": ("prospects trouvés", c["prospects_trouves_aujourdhui"]), "appels-sid": ("appels Sid", c["appels_sid_aujourdhui"]),
               "rendez-vous": ("rendez-vous", c["rendez_vous_aujourdhui"]), "devis": ("devis préparés", c["devis_prepares_aujourdhui"])}
    for a in agents:
        lib, n = du_jour.get(a["nom"], ("actions du jour", lignes_du_jour(a["nom"], j)))
        a["chiffre_du_jour"] = {"libelle": lib, "valeur": n}
    rep = lignes_du_jour("reponses", j)
    c["pipeline"] = [["Prospects trouvés", c["prospects_trouves_aujourdhui"]], ["Contactés (e-mails)", c["emails_envoyes_aujourdhui"]],
                     ["Réponses traitées", rep], ["Rendez-vous", c["rendez_vous_aujourdhui"]], ["Devis préparés", c["devis_prepares_aujourdhui"]],
                     ["Payés (total)", c["devis_payes"]]]          # None = pas de donnée sur ce PC (affiché « — »)
    return {
        "genere_le": maintenant.strftime("%Y-%m-%d %H:%M:%S"), "ce_pc": ce_pc, "machine_active": machine_active,
        "ce_pc_est_actif": bool(machine_active) and machine_active == ce_pc,
        "source": "fichiers locaux de " + ce_pc + (" ; l'état en direct du serveur " + machine_active + " n'est pas visible d'ici (états et journaux hors git)" if machine_active and machine_active != ce_pc else ""),
        "chiffres": c, "agents": agents,
    }


def _resume_sid():
    """Module B2B/agents/resume-sid.py (nom à tiret) : on réutilise ses lectures (feuilles « Appels Sid », Stripe) au lieu de les réécrire."""
    import importlib.util
    if str(AGENTS) not in sys.path: sys.path.insert(0, str(AGENTS))
    spec = importlib.util.spec_from_file_location("resume_sid", AGENTS / "resume-sid.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def ventes(maintenant=None, rs=None):
    """Bloc « Aujourd'hui » (dashboard/ventes.json) : chiffres de vente du jour, COMPTES seulement (jamais un nom d'entreprise, un e-mail ni un téléphone).
    Appels, leads chauds et RDV : feuilles « Appels Sid » modifiées aujourd'hui (resume-sid.stats_appels, API Google gratuite) ; paiements : Stripe en lecture seule
    (resume-sid.stripe_jour) ; devis envoyés : devis-etat.json. Aucun token Claude. Indisponible = valeur None + raison, jamais estimé. JARVIS_TEST=1 : aucun réseau."""
    maintenant = maintenant or datetime.now(); j = maintenant.date().isoformat()
    ko = lambda raison: {"valeur": None, "raison": raison}
    if rs is None and os.environ.get("JARVIS_TEST") == "1": rs, err = None, "mode test : aucune lecture Google ni Stripe"
    elif rs is None:
        try: rs, err = _resume_sid(), ""
        except Exception as e: rs, err = None, f"resume-sid.py illisible ({type(e).__name__})"
    else: err = ""
    try: dispo, d = rs.stats_appels(rs.cfg(), j) if rs else (False, err)
    except Exception as e: dispo, d = False, f"feuilles de Sid illisibles ({type(e).__name__})"
    if dispo:
        r = d.get("resultats")
        n = len(d.get("feuilles") or []) if d.get("multi") else 1
        appels = {"valeur": d.get("Appelé", 0), "detail": f"{n} feuille{'s' if n > 1 else ''} « Appels Sid » modifiée{'s' if n > 1 else ''} aujourd'hui"}
        if r is not None:
            chauds = {"valeur": r.get("À rappeler", 0) + r.get("Je dois réfléchir", 0), "detail": f"{r.get('À rappeler', 0)} à rappeler · {r.get('Je dois réfléchir', 0)} je dois réfléchir"}
            rdv = {"valeur": r.get("RDV pris", 0), "detail": "notés « RDV pris » par Sid"}
        else:
            chauds = ko("ancienne feuille sans colonne Résultat"); rdv = {"valeur": d.get("Rendez-vous pris", 0), "detail": "case « Rendez-vous pris »"}
    else: appels = chauds = rdv = ko(str(d))
    dv = lire_json(AGENTS / "devis-etat.json")
    devis = ko("devis-etat.json absent sur ce PC (l'état des devis est sur la machine active)") if dv is None else \
        {"valeur": sum(1 for v in (dv.get("devis") or {}).values() if (v.get("historique") or {}).get("envoyé") == j), "detail": "marqués « envoyé » aujourd'hui"}
    try: dispo, s = rs.stripe_jour(j) if rs else (False, err)
    except Exception as e: dispo, s = False, f"Stripe illisible ({type(e).__name__})"
    paiements = {"valeur": s["paiements"], "detail": ("au moins " if s.get("partiel") else "") + rs._montants_texte(s["montants"]) + " encaissés"} if dispo else ko(str(s))
    items = [["appels", "Appels notés par Sid", appels], ["chauds", "Leads chauds", chauds], ["rdv", "Rendez-vous pris", rdv],
             ["devis", "Devis envoyés", devis], ["paiements", "Paiements reçus", paiements]]
    if (AGENTS / "alerte-candidatures.py").exists():      # agent pas encore construit (17/11/2026) : ligne masquée tant qu'il n'existe pas
        items.append(["candidatures", "Candidatures call callers", ko("agent alerte-candidatures présent, compteur pas encore branché")])
    return {"jour": j, "genere_le": maintenant.strftime("%Y-%m-%d %H:%M:%S"),
            "chiffres": [dict(cle=c, libelle=l, **v) for c, l, v in items]}


def masquer(t):
    """Aucune adresse e-mail ni téléphone dans ce qui sort (même si une doc en contient)."""
    t = re.sub(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", "[e-mail masqué]", t)
    return re.sub(r"(?<!\d)(?:\+33\s?|0)[1-9](?:[ .-]?\d\d){4}(?!\d)", "[téléphone masqué]", t)


def ecrire(donnees, chiffres_ventes=None):
    SORTIE.mkdir(exist_ok=True)
    texte = masquer(json.dumps(donnees, ensure_ascii=False, indent=1)); docs = masquer(json.dumps(documents(), ensure_ascii=False))
    fichiers = [("agents.json", texte), ("agents.js", "window.JARVIS_AGENTS = " + texte + ";\n"), ("docs.js", "window.JARVIS_DOCS = " + docs + ";\n")]
    if chiffres_ventes is not None:      # ventes.js : même contenu que ventes.json, lu par la page même en file://
        v = masquer(json.dumps(chiffres_ventes, ensure_ascii=False, indent=1))
        fichiers += [("ventes.json", v), ("ventes.js", "window.JARVIS_VENTES = " + v + ";\n")]
    for nom, contenu in fichiers:
        tmp = SORTIE / (nom + ".tmp"); tmp.write_text(contenu, encoding="utf-8"); os.replace(tmp, SORTIE / nom)


def main():
    ecrire(construire(), ventes())
    if "--ouvrir" in sys.argv[1:] and os.name == "nt": os.startfile(str(SORTIE / "index.html"))


if __name__ == "__main__":
    main()
