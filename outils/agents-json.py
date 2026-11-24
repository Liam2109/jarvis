#!/usr/bin/env python3
"""Tableau de bord « Jarvis - Mon entreprise » : écrit dashboard/agents.json, agents.js (même contenu, lu par la page même en file://) et docs.js (onglets À faire, Journal, Décisions, Idées).
Aussi ventes.json/js (chiffres du jour + Potentiel), data/historique.json/js (une entrée par jour depuis le 16/11/2026) et data/leads.json/js (les leads chauds que Liam doit rappeler).
Lancé toutes les 15 min par la tâche Jarvis-Tableau-PC (outils/tache-dashboard-pc.ps1).

Lecture seule, sans réseau ni token Claude. Sources : B2B/agents/*.py (un agent = un script qui appelle M.exiger), leur .md, docs/agents/agent-<nom>.md,
B2B/agents/b2b.local.json, B2B/agents/serveur-taches.json, les fichiers *-etat.json et *-journal.log, les tâches planifiées Windows Jarvis-B2B-* de CE PC.
Un nouvel agent apparaît seul dès que son script est créé dans B2B/agents/.

Confidentialité : AUCUN secret. Dans agents.json, ventes.json, docs.js et data/historique.json : aucune donnée de prospect — seuls sortent noms d'agents, rôles (docs), horaires,
dates, mots d'action du journal (2e colonne, jamais la 3e qui peut contenir un nom d'entreprise) et des COMPTES (nombres), e-mails et téléphones masqués.
SEULE EXCEPTION, data/leads.json (22/11/2026) : les leads chauds à rappeler, avec nom, ville et téléphone, comme le message Discord de l'agent Relances ; dashboard\\data\\ est hors
git. Aucune lecture de .env, de jeton ni de config locale autre que b2b.local.json.

  python outils/agents-json.py          écrit les deux fichiers (écriture atomique)
  python outils/agents-json.py --ouvrir écrit puis ouvre dashboard/index.html dans le navigateur par défaut (icône du bureau)
"""
import csv, io, json, os, re, socket, subprocess, sys
from datetime import datetime, date, timedelta
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


# Agents retirés de la grille (24/11/2026) : leurs scripts restent dans B2B/agents (des tests les citent), leurs fiches sont rangées dans docs/archives/agents-retires.
RETIRES = {"appels-liam", "facebook", "superviseur-sites", "superviseur-mail", "jarvis-vue", "linkedin", "vente-relances", "registre"}


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


def derniere_trace(nom):
    """Dernière ligne de B2B/logs/agents/<agent>/AAAA-MM-JJ.jsonl (le fichier du jour le plus récent) -> {quand, resultat, ok} ; None si aucune trace lisible. Jamais le commerce."""
    d = AGENTS.parent / "logs" / "agents" / nom
    try: fichiers = sorted(d.glob("*.jsonl"), reverse=True)
    except OSError: return None
    for f in fichiers:
        try: lignes = f.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError: continue
        for l in reversed(lignes):
            try: x = json.loads(l)
            except ValueError: continue
            if isinstance(x, dict) and x.get("heure"): return {"quand": str(x["heure"]).replace("T", " ")[:19], "resultat": str(x.get("resultat") or "")[:60], "ok": x.get("ok"), "decision": str(x.get("decision") or ""), "erreur": str(x.get("erreur") or "")[:120]}
    return None


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
    tr = derniere_trace(nom)
    if tr:      # la trace du harness fait foi pour « passé aujourd'hui » (les agents n'écrivent pas tous dans leur .log) ; sans trace, l'ancien comportement
        dernier = tr["quand"]; resultat = resultat or tr["resultat"]
        if tr["ok"] is False and tr.get("decision") != "stock": erreur = {"date": dernier, "action": "erreur (trace)"}      # « stock » = alerte de stock de listes bas (appels-sid) : la liste du jour est faite, ce n'est pas une panne
        elif erreur is not None and erreur["date"] != dernier: erreur = None if erreur["date"] < dernier else erreur
    return dernier, resultat, erreur, liste[-30:]


POLES = {"prospection": "Trouver", "page-exemple": "Trouver", "appels-sid": "Vendre", "appels-liam": "Vendre", "rendez-vous": "Vendre", "reponses": "Vendre", "devis": "Vendre",
         "stripe-alerte": "Encaisser", "resume-sid": "Communiquer", "vente-relances": "Vendre", "relances": "Vendre", "interim": "Autres", "facebook": "Trouver"}     # tout nouvel agent : « Autres »
# Catégories = un superviseur par domaine (23/11/2026) ; tout agent non listé reste sous Jarvis (CEO).
SUPERVISEURS = ["Vente", "Prospection", "Sites", "Mail", "Jarvis (CEO)"]
CATEGORIE = {"devis": "Vente", "relances": "Vente", "rendez-vous": "Vente", "reponses": "Vente", "chiffres-serveur": "Vente", "stripe-alerte": "Vente", "superviseur-vente": "Vente", "vente-relances": "Vente",
             "prospection": "Prospection", "appels-sid": "Prospection", "appels-liam": "Prospection", "superviseur-prospection": "Prospection", "facebook": "Prospection",
             "page-exemple": "Sites", "superviseur-sites": "Sites", "interim": "Mail", "superviseur-mail": "Mail"}


def avertissement(nom, en_erreur):
    """Dernière trace = alerte de stock bas (decision « stock », ok=False) sans vraie panne : texte court, sinon None. L'agent a tourné ; le tableau de bord l'affiche en orange, jamais en rouge."""
    tr = None if en_erreur else derniere_trace(nom)
    return ("Stock bas : " + (tr["erreur"] or tr["resultat"]).replace("stock bas :", "").strip()[:100]) if tr and tr.get("decision") == "stock" and tr.get("ok") is False else None


def voyant(a, jour):
    """Statut à quatre couleurs : rouge = erreur ou suspendu ; gris = désactivé, à construire ou jamais passé ; vert = passé aujourd'hui ; orange = déjà passé mais pas encore aujourd'hui. -> (couleur, raison)"""
    if a.get("statut") == "erreur" or a.get("suspendu"): return "rouge", "Suspendu" if a.get("suspendu") else "En erreur"
    if a.get("etat_liste") in ("désactivé", "à construire"): return "gris", "Désactivé" if a["etat_liste"] == "désactivé" else "À construire"
    if a.get("avertissement"): return "orange", a["avertissement"]
    dp = a.get("dernier_passage")
    if not dp: return "gris", "Aucun passage visible"
    return ("vert", "Passé aujourd'hui") if str(dp)[:10] == jour else ("orange", "Pas encore passé aujourd'hui")


def extrait_note(nom, n=900):
    """Début du corps de la note docs/agents de l'agent (sans l'en-tête), pour le panneau du tableau de bord."""
    try: t = note_de(nom).read_text(encoding="utf-8")
    except OSError: return None
    t = re.sub(r"^---\s*\n.*?\n---\s*\n?", "", t, count=1, flags=re.S)
    t = re.sub(r"<!--.*?-->", "", re.sub(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]", r"\1", t), flags=re.S)
    m = re.search(r"### Mission\s*(.*?)(?=\n## |\Z)", t, re.S)      # « Rôle et limites » : mission, étapes, interdits (sans entrées/sorties ni contrat)
    t = re.sub(r"\n?#{1,4} ", "\n", m.group(1) if m else t).replace("`", "").strip()
    return (t[:n].rsplit(" ", 1)[0] + "…" if len(t) > n else t) or None


# Page Agents (18/11/2026) : état « à construire » décidé ici (raison affichée) ; « désactivé » vient de serveur-taches.json › desactive ; sinon « en place ».
A_CONSTRUIRE = {"devis": "l'état des devis est sur le serveur, pas encore relié à ce tableau de bord",
                "alerte-candidatures": "formulaire de candidature pas encore relié (fermé jusqu'au « go alerte »)",
                "interim": "boîte emoliam255 pas encore autorisée en lecture (fermé jusqu'au « go interim »)",
                "vente-relances": "contrat écrit, script pas encore construit", "facebook": "pas encore construit"}
SANS_SCRIPT = {"vente-relances": "Relancer à J+3 et J+7 les prospects qui ont reçu un devis (brouillons pour Liam, aucun envoi).",
               "facebook": "Publier sur Facebook (prévu, rien n'est publié)."}


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
    c["fiches_sid_preparees_aujourdhui"] = int((listes.get(j) or {}).get("nombre", 0) or 0)
    c["nouvelles_entreprises_aujourdhui"] = int(((lire_json(AGENTS / "appels-sid-etat.json", {}) or {}).get("nouvelles") or {}).get("jours", {}).get(j, 0) or 0)   # source INSEE Sirene (24/11/2026)
    return c


CHAMPS_SERVEUR = ("statut", "suspendu", "dernier_passage", "dernier_resultat", "derniere_erreur", "journal", "chiffre_du_jour")      # état vivant : les journaux et *-etat.json sont hors git, donc vus seulement sur la machine active


def lire_serveur(hote, port=8080, delai=4):
    """Photo agents.json de la machine active (servie en lecture seule par servir-dashboard.py) ; None si injoignable. JARVIS_TEST=1 : aucun réseau."""
    if not hote or os.environ.get("JARVIS_TEST") == "1": return None
    from urllib.request import urlopen
    try:
        with urlopen(f"http://{hote}:{port}/agents.json", timeout=delai) as r: d = json.loads(r.read().decode("utf-8-sig"))
        return d if isinstance(d, dict) and isinstance(d.get("agents"), list) else None
    except Exception: return None


def fusionner_serveur(agents, photo):
    """Surcharge l'état vivant de chaque agent par celui de la machine active ; notes, rôles et liens restent ceux de ce PC. -> nombre d'agents mis à jour."""
    par_nom = {a.get("nom"): a for a in photo.get("agents", []) if isinstance(a, dict)}; n = 0
    for a in agents:
        s = par_nom.get(a["nom"])
        if not s: continue
        for k in CHAMPS_SERVEUR:
            if k in s: a[k] = s[k]
        a["tourne_sur_ce_pc"], a["planifie_sur_ce_pc"], a["vu_sur_serveur"] = bool(s.get("tourne_sur_ce_pc")), bool(s.get("planifie_sur_ce_pc")), True; n += 1
    return n


def construire(maintenant=None, photo_serveur=None):
    maintenant = maintenant or datetime.now()
    local = lire_json(AGENTS / "b2b.local.json", {}) or {}
    machine_active = str(local.get("machine_active", "") or "")
    ce_pc = os.environ.get("COMPUTERNAME") or socket.gethostname()
    serveur = (lire_json(AGENTS / "serveur-taches.json", {}) or {}).get("agents", {})
    taches, procs = taches_windows(), processus_python()
    agents = []
    for py in sorted(AGENTS.glob("*.py")):
        if not est_agent(py) or py.stem in RETIRES: continue
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
            "statut": statut, "suspendu": suspendu, "avertissement": avertissement(nom, en_erreur),
            "dernier_passage": dernier, "dernier_resultat": resultat, "derniere_erreur": erreur,
            "pole": POLES.get(nom, "Autres"), "journal": lignes_journal,
            "responsable": frontmatter(note).get("responsable") or None,   # « responsable: prospection » dans l'en-tête de la note docs/agents (organigramme du 14/11/2026), None sinon
            "note": str(note.relative_to(RACINE)).replace("\\", "/") if note.exists() else None,
            "note_obsidian": ("obsidian://open?path=" + quote(str(note), safe="")) if note.exists() else None,
        })
    for nom, phrase in ((n, f) for n, f in SANS_SCRIPT.items() if n not in RETIRES):      # agents prévus sans script : une ligne « à construire » sur la page Agents (jamais planifiés)
        if not any(a["nom"] == nom for a in agents):
            agents.append({"nom": nom, "role": phrase, "machine": "aucune", "planifie": False, "horaire": "non planifié", "planifie_sur_ce_pc": False, "tourne_sur_ce_pc": False,
                           "statut": "inactif", "suspendu": False, "dernier_passage": None, "dernier_resultat": None, "derniere_erreur": None, "pole": POLES.get(nom, "Autres"),
                           "journal": [], "responsable": None, "note": None, "note_obsidian": None, "sans_script": True})
    ailleurs = bool(machine_active) and machine_active != ce_pc
    photo = (photo_serveur or lire_serveur(str(local.get("serveur_adresse", "") or "").strip() or machine_active)) if ailleurs else None   # serveur_adresse : IP du serveur, dans b2b.local.json (jamais en dur ici)
    vus = fusionner_serveur(agents, photo) if photo else 0
    for a in agents:
        d = (serveur.get(a["nom"]) or {}).get("desactive")
        a["etat_liste"], a["raison_etat"] = (("désactivé", str(d)) if d else ("à construire", A_CONSTRUIRE[a["nom"]]) if a["nom"] in A_CONSTRUIRE else ("en place", ""))
        a["phrase"] = (re.split(r"(?<=[.;])\s|\s—\s", a["role"] or "", maxsplit=1)[0].rstrip(".;") + ".")[:160] if a["role"] else ""
    c = chiffres_du_jour(maintenant.date()); j = maintenant.date().isoformat()
    for a in agents:
        a["categorie"] = CATEGORIE.get(a["nom"], "Jarvis (CEO)")
        a["voyant"], a["voyant_raison"] = voyant(a, j)
        a["note_extrait"] = extrait_note(a["nom"]) if a.get("note") else None
    du_jour = {"prospection": ("prospects trouvés", c["prospects_trouves_aujourdhui"]), "appels-sid": ("fiches Sid préparées" + (f" · {c['nouvelles_entreprises_aujourdhui']} nouvelle(s) entreprise(s) en réserve" if c["nouvelles_entreprises_aujourdhui"] else ""), c["fiches_sid_preparees_aujourdhui"]),
               "rendez-vous": ("rendez-vous", c["rendez_vous_aujourdhui"]), "devis": ("devis préparés", c["devis_prepares_aujourdhui"])}
    for a in agents:
        if a.get("vu_sur_serveur"): continue      # le chiffre du jour du serveur (journaux et états locaux de ce PC absents) est déjà en place
        lib, n = du_jour.get(a["nom"], ("actions du jour", lignes_du_jour(a["nom"], j)))
        a["chiffre_du_jour"] = {"libelle": lib, "valeur": n}
    rep = lignes_du_jour("reponses", j)
    c["pipeline"] = [["Prospects trouvés", c["prospects_trouves_aujourdhui"]], ["Contactés (e-mails)", c["emails_envoyes_aujourdhui"]],
                     ["Réponses traitées", rep], ["Rendez-vous", c["rendez_vous_aujourdhui"]], ["Devis préparés", c["devis_prepares_aujourdhui"]],
                     ["Payés (total)", c["devis_payes"]]]          # None = pas de donnée sur ce PC (affiché « — »)
    return {
        "genere_le": maintenant.strftime("%Y-%m-%d %H:%M:%S"), "ce_pc": ce_pc, "machine_active": machine_active,
        "ce_pc_est_actif": bool(machine_active) and machine_active == ce_pc,
        "source": ("état des agents lu sur le serveur " + machine_active + " (photo du " + str(photo.get("genere_le", "?")) + ", " + str(vus) + " agents)") if vus else
                  "fichiers locaux de " + ce_pc + (" ; le serveur " + machine_active + " est injoignable (port 8080), son état en direct n'est pas visible d'ici" if ailleurs else ""),
        "serveur_lu": bool(vus), "serveur_photo": photo.get("genere_le") if vus else None,
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
            appels["repartition"] = {v: int(r.get(v, 0) or 0) for v in RESULTATS}     # historique (data/historique.json) ; la carte vedette n'affiche que les valeurs non nulles
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


# --- historique (dashboard/data/historique.json, 18/11/2026) : une entrée par jour depuis le 16/11/2026, comptes seulement ---------------------------------
HISTO = SORTIE / "data" / "historique.json"
LEADS = SORTIE / "data" / "leads.json"      # carte « Leads chauds à appeler » (22/11/2026) : noms et numéros des prospects à rappeler, hors git, jamais masqués (voir ecrire)
DEBUT_HISTO = "2026-11-16"
RESULTATS = ["Pas de réponse", "À rappeler", "RDV pris", "Non catégorique", "Je dois réfléchir", "Trop cher", "Déjà un site", "Pas le temps"]   # = resume-sid.RESULTATS
CHAUDS = ("À rappeler", "Je dois réfléchir")
OFFRE = RACINE / "B2B" / "docs" / "OFFRE-REFERENCE.json"


def prix_pack():
    """Prix du pack lu dans la référence de l'offre (jamais codé en dur ici) ; None si illisible."""
    try: return int((lire_json(OFFRE) or {})["offres"]["pack"]["prix_unique_eur"])
    except (KeyError, TypeError, ValueError): return None


def feuilles_sid(rs):
    """(dispo, [{jour, modifiee, resultats, avec, metiers, lignes}] | raison) : chaque feuille « Appels Sid AAAA-MM-JJ » du dossier de Sid, avec le jour de SON TITRE (= le jour des appels,
    même définition que relances.py et le registre), le jour de dernière modification (Paris, pour information) et les comptes par Résultat.
    `lignes` (lignes notées : entreprise, ville, téléphone, résultat, note) ne sert qu'à la carte « Leads chauds à appeler » et n'entre jamais dans l'historique.
    Lecture seule, une lecture par feuille."""
    if rs is None: return False, "mode test : aucune lecture Google"
    try:
        conf = rs.cfg(); racine = str(rs.M.lire_fusionnee(rs.APPELS_SID_CONFIG).get("dossier_sid_id") or "").strip()
        if not racine: return False, "dossier Drive de Sid inconnu (appels-sid-config)"
        d = rs.ouvrir_drive(conf["compte_google"])
        if (d.compte() or "").lower() != conf["compte_google"].lower(): return False, "jeton Google d'un autre compte"
        out = []
        for i, nom, mod in d.lister_feuilles_modifiees(racine):
            m = rs.TITRE_SID.fullmatch(nom or "")
            if not m: continue
            lignes = list(csv.reader(io.StringIO(d.lire_feuille_csv(i))))
            if not lignes or "Résultat" not in lignes[0]: continue
            k = lignes[0].index("Résultat"); km = lignes[0].index("Métier") if "Métier" in lignes[0] else None
            notees = [l for l in lignes[1:] if k < len(l) and l[k].strip()]; vals = [l[k].strip() for l in notees]
            out.append({"jour": m.group(1), "modifiee": rs._jour_paris(mod), "resultats": {v: vals.count(v) for v in RESULTATS}, "avec": len(vals),
                        "metiers": compter_metiers((l[km] if km is not None and km < len(l) else "", l[k].strip()) for l in notees),
                        "lignes": lignes_notees(lignes[0], notees)})
        return True, out
    except Exception as e: return False, f"feuilles de Sid illisibles ({type(e).__name__})"


def lignes_notees(entete, notees):
    """Lignes notées d'une feuille de Sid -> [{nom, ville, tel, resultat, note}] (le format attendu par relances.leads). Ne sert qu'à la carte des leads chauds."""
    ix = {c: (entete.index(n) if n in entete else None) for c, n in (("nom", "Entreprise"), ("ville", "Ville"), ("tel", "Téléphone"), ("resultat", "Résultat"), ("note", "Note"))}
    v = lambda l, k: l[ix[k]].strip() if ix[k] is not None and ix[k] < len(l) else ""
    return [{c: v(l, c) for c in ix} for l in notees]


def compter_metiers(paires):
    """{métier: {appels, chauds, rdv}} à partir de paires (Métier, Résultat) des lignes notées ; métier vide = « Non renseigné ». Aucun nom d'entreprise."""
    out = {}
    for m, r in paires:
        m = " ".join(str(m or "").split()); m = (m[:1].upper() + m[1:].lower()) if m else "Non renseigné"
        x = out.setdefault(m, {"appels": 0, "chauds": 0, "rdv": 0}); x["appels"] += 1; x["chauds"] += r in CHAUDS; x["rdv"] += r == "RDV pris"
    return out


def metiers_du_jour(feuilles, jour):
    """Répartition par métier du jour : les feuilles dont le TITRE porte ce jour (pas celles modifiées ce jour-là)."""
    out = {}
    for f in feuilles:
        if f.get("jour") != jour: continue
        for m, x in (f.get("metiers") or {}).items():
            y = out.setdefault(m, {"appels": 0, "chauds": 0, "rdv": 0})
            for c in y: y[c] += int(x.get(c, 0) or 0)
    return out


def devis_envoyes(jour):
    """Devis marqués « envoyé » ce jour-là (devis-etat.json) ; None si l'état n'est pas sur ce PC (jamais 0 par défaut)."""
    dv = lire_json(AGENTS / "devis-etat.json")
    return None if dv is None else sum(1 for v in (dv.get("devis") or {}).values() if (v.get("historique") or {}).get("envoyé") == jour)


def entree(jour, appels, resultats, devis=None, paiements=None, source=""):
    r = {v: int(resultats.get(v, 0) or 0) for v in RESULTATS}
    return {"date": jour, "appels": appels, "resultats": r, "leads_chauds": sum(r[v] for v in CHAUDS), "rdv": r["RDV pris"], "devis": devis, "paiements": paiements, "source": source}


def fusionner(jours, e, auj, autorite=False):
    """Une seule entrée par date. `autorite` : l'entrée est recalculée depuis la feuille « Appels Sid » de ce jour-là, qui fait foi — elle remplace l'ancienne même si elle est plus
    basse (c'est ainsi qu'un jour faussé se corrige). Sinon un jour passé (complet) n'est remplacé que par un compte d'appels au moins égal.
    Dans les deux cas, une valeur inconnue (None) n'efface jamais une valeur connue."""
    old = jours.get(e["date"])
    if old:
        for k in ("devis", "paiements"):
            if e.get(k) is None and old.get(k) is not None: e[k] = old[k]
        if not autorite and old.get("complet") and (old.get("appels") or 0) > (e["appels"] or 0):
            for k in ("devis", "paiements"):
                if old.get(k) is None: old[k] = e[k]
            return
    e["complet"] = e["date"] < auj
    jours[e["date"]] = e


def historique(maintenant=None, v=None, feuilles=None):
    """Lit, complète et renvoie l'historique. Un appel est compté le jour de la FEUILLE qui le porte (la date de son titre, « Appels Sid AAAA-MM-JJ »), jamais le jour où la feuille
    a été modifiée : Sid note souvent ses appels un ou deux jours après, et la même feuille était alors recomptée EN ENTIER chaque jour où il y touchait — les leads déjà traités
    la veille revenaient comme neufs (cause corrigée le 22/11/2026). Chaque jour depuis DEBUT_HISTO dont la feuille est encore sur le Drive est donc recalculé depuis elle (elle fait
    foi) ; un jour dont la feuille a été mise à la corbeille (7 jours) garde la valeur déjà enregistrée. Sans lecture Google (mode test), le jour courant vient de ventes().
    Relancer ne crée jamais de doublon."""
    maintenant = maintenant or datetime.now(); auj = maintenant.date().isoformat()
    h = lire_json(HISTO, {}) or {}
    jours = {e["date"]: e for e in h.get("jours", []) if isinstance(e, dict) and e.get("date")}
    for e in jours.values(): e["complet"] = e["date"] < auj
    c = {x["cle"]: x for x in (v or {}).get("chiffres", [])}
    a = c.get("appels") or {}
    par_jour = {}
    for f in (feuilles or []): par_jour.setdefault(f.get("jour"), []).append(f)
    if feuilles:      # au moins une feuille lue : les jours sont recalculés depuis les feuilles (une liste vide ne remet jamais l'historique à zéro)
        d = date.fromisoformat(DEBUT_HISTO)
        while d.isoformat() <= auj:
            j = d.isoformat(); d += timedelta(days=1)
            fs = par_jour.get(j)
            if fs is None and j in jours: continue      # feuille mise à la corbeille : le jour déjà enregistré est gardé tel quel
            fs = fs or []
            dv = (c.get("devis") or {}).get("valeur") if j == auj else devis_envoyes(j)
            pa = (c.get("paiements") or {}).get("valeur") if j == auj else None
            fusionner(jours, entree(j, sum(f["avec"] for f in fs), {r: sum(f["resultats"].get(r, 0) for f in fs) for r in RESULTATS}, dv, pa, "feuille du jour"), auj, autorite=True)
    elif feuilles is None and a.get("valeur") is not None and isinstance(a.get("repartition"), dict):
        fusionner(jours, entree(auj, a["valeur"], a["repartition"], (c.get("devis") or {}).get("valeur"), (c.get("paiements") or {}).get("valeur"), "du jour"), auj)
    if feuilles:      # répartition par métier (18/11/2026) : recalculée pour les jours dont la feuille est là, ajoutée à ceux qui ne l'ont pas encore
        for j, e in jours.items():
            if par_jour.get(j) is not None or "metiers" not in e: e["metiers"] = metiers_du_jour(feuilles, j)
    return {"_aide": "Écrit par outils/agents-json.py : une entrée par jour (comptes seulement). null = inconnu sur ce PC, jamais 0.", "maj": maintenant.strftime("%Y-%m-%d %H:%M:%S"),
            "resultats": RESULTATS, "jours": [jours[k] for k in sorted(jours)]}


def aligner_jour(v, feuilles, jour):
    """Aligne les trois chiffres d'appels de la carte « Aujourd'hui » sur la même définition que l'historique : la feuille « Appels Sid <jour> », et non toutes les feuilles modifiées
    aujourd'hui — sinon une vieille feuille que Sid rouvre fait réapparaître ses appels et ses leads comme s'ils étaient du jour. Le résumé du soir (resume-sid) garde sa règle."""
    fs = [f for f in feuilles if f.get("jour") == jour]
    r = {x: sum(f["resultats"].get(x, 0) for f in fs) for x in RESULTATS}
    ou = f"feuille « Appels Sid {jour} »" if fs else f"aucune feuille « Appels Sid {jour} » (liste du jour pas encore créée, ou jour sans appels)"
    neuf = {"appels": {"valeur": sum(f["avec"] for f in fs), "detail": ou},
            "chauds": {"valeur": sum(r[x] for x in CHAUDS), "detail": f"{r['À rappeler']} à rappeler · {r['Je dois réfléchir']} je dois réfléchir" if fs else ou},
            "rdv": {"valeur": r["RDV pris"], "detail": "notés « RDV pris » par Sid" if fs else ou}}
    if fs: neuf["appels"]["repartition"] = r
    for x in v.get("chiffres", []):
        if x["cle"] in neuf: x.pop("raison", None); x.pop("repartition", None); x.update(neuf[x["cle"]])
    return v


def _relances():
    """Module B2B/agents/relances.py (nom à tiret) : on réutilise SON critère de lead chaud et SON rythme de relances (relances.leads, relances.etape) au lieu de les réécrire."""
    import importlib.util
    if str(AGENTS) not in sys.path: sys.path.insert(0, str(AGENTS))
    spec = importlib.util.spec_from_file_location("relances_agent", AGENTS / "relances.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def leads_a_appeler(feuilles, jour, R=None):
    """(dispo, [lead] | raison) : les leads chauds en cours, chacun avec LA RAISON pour laquelle il est chaud — le Résultat noté par Sid (« À rappeler » ou « Je dois réfléchir ») et sa
    Note. Critère, exclusions et rythme des relances viennent de l'agent Relances (relances.leads, relances.etape) : rien n'est réinventé ni inventé ici ; une Note vide reste vide.
    Les leads dus (relance à faire) sortent en premier."""
    try: R = R or _relances()
    except Exception as e: return False, f"relances.py illisible ({type(e).__name__})"
    try:
        tous = R.leads(sorted(((f.get("jour") or "", f.get("lignes") or []) for f in feuilles), key=lambda x: x[0]))
        out = []
        for t, x in tous.items():
            n, prevu, due = R.etape(x, jour)
            out.append({"nom": x["nom"], "ville": x["ville"], "tel": R.tel_lisible(t), "raison": x["resultat"], "note": x["note"], "appel": x["appel"],
                        "relance": n, "prevu": prevu, "due": bool(due), "moyen_terme": bool(x["moyen_terme"])})
        return True, sorted(out, key=lambda l: (not l["due"], l["prevu"], l["nom"]))
    except Exception as e: return False, f"leads chauds illisibles ({type(e).__name__})"


def leads_de_la_file(jour):
    """File unique « leads chauds » (B2B/agents/leads_chauds.py, maillon 2 de CARTE-RELAIS, 23/11/2026), même lecture que le reste : un fichier local, aucune dépendance de plus.
    -> liste au format de leads_a_appeler, ou None si la file n'existe pas (la lecture des feuilles de Sid sert alors de secours)."""
    try:
        if str(AGENTS) not in sys.path: sys.path.insert(0, str(AGENTS))
        import leads_chauds as LC
        file = LC.lire()
    except Exception: return None
    if file is None: return None
    return [{"nom": l["nom"], "ville": l.get("ville", ""), "tel": LC.tel_lisible(l["tel"]), "raison": l.get("resultat", ""), "note": l.get("note", ""), "appel": l.get("resultat_le", ""),
             "relance": 1, "prevu": l.get("jour", ""), "due": bool(l.get("jour")) and l["jour"] <= jour, "moyen_terme": bool(l.get("moyen_terme")), "rappelle": l.get("rappelle", "Sid")} for l in file]


def potentiel(dispo, leads):
    """Leads chauds en cours × prix du pack. `leads` = la liste de leads_a_appeler (même critère que l'agent Relances : un lead compté une fois, les exclus retirés) ou la raison de
    son absence. Indicatif, aucun taux de conversion."""
    prix = prix_pack()
    if prix is None: return {"valeur": None, "raison": "prix du pack illisible (B2B/docs/OFFRE-REFERENCE.json)"}
    if not dispo: return {"valeur": None, "raison": str(leads)}
    n = len(leads)
    return {"valeur": n * prix, "unite": "€", "leads": n, "prix": prix, "detail": f"{n} leads chauds en cours × {prix} € · indicatif, pas une prévision"}


def masquer(t):
    """Aucune adresse e-mail ni téléphone dans ce qui sort (même si une doc en contient)."""
    t = re.sub(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", "[e-mail masqué]", t)
    return re.sub(r"(?<!\d)(?:\+33\s?|0)[1-9](?:[ .-]?\d\d){4}(?!\d)", "[téléphone masqué]", t)


def lire_relais(n=30):
    """B2B/donnees/relais.jsonl : une ligne JSON par relais (maillon 1, réponse positive). -> les n dernières, la plus récente d'abord ; ligne illisible ignorée ; fichier absent = []."""
    out = []
    try:
        for l in (RACINE / "B2B" / "donnees" / "relais.jsonl").read_text(encoding="utf-8-sig").splitlines():
            try: out.append(json.loads(l))
            except ValueError: pass
    except OSError: pass
    return out[-n:][::-1]


def ecrire(donnees, chiffres_ventes=None, histo=None, leads=None):
    SORTIE.mkdir(exist_ok=True)
    rel = {"genere_le": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "relais": lire_relais()}      # data/relais.json : noms de prospects, hors git comme leads.json
    (SORTIE / "data").mkdir(exist_ok=True); t = json.dumps(rel, ensure_ascii=False, indent=1)
    for p, contenu in ((SORTIE / "data" / "relais.json", t), (SORTIE / "data" / "relais.js", "window.JARVIS_RELAIS = " + t + ";\n")):
        tmp = p.with_name(p.name + ".tmp"); tmp.write_text(contenu, encoding="utf-8"); os.replace(tmp, p)
    if histo is not None:      # data/historique.json (gardé d'un lancement à l'autre) + data/historique.js (même contenu, lu par la page en file://)
        HISTO.parent.mkdir(exist_ok=True); t = masquer(json.dumps(histo, ensure_ascii=False, indent=1))
        for p, contenu in ((HISTO, t), (HISTO.with_suffix(".js"), "window.JARVIS_HISTO = " + t + ";\n")):
            tmp = p.with_name(p.name + ".tmp"); tmp.write_text(contenu, encoding="utf-8"); os.replace(tmp, p)
    if leads is not None:      # data/leads.json : SEUL fichier du tableau de bord qui porte des noms et des numéros de prospects (ceux que Liam doit rappeler, comme le message
        LEADS.parent.mkdir(exist_ok=True)      # Discord de l'agent Relances). dashboard\data\ est hors git (.gitignore) : rien de tout cela n'entre dans le coffre ni dans un commit.
        t = json.dumps(leads, ensure_ascii=False, indent=1)
        for p, contenu in ((LEADS, t), (LEADS.with_suffix(".js"), "window.JARVIS_LEADS = " + t + ";\n")):
            tmp = p.with_name(p.name + ".tmp"); tmp.write_text(contenu, encoding="utf-8"); os.replace(tmp, p)
    texte = masquer(json.dumps(donnees, ensure_ascii=False, indent=1)); docs = masquer(json.dumps(documents(), ensure_ascii=False))
    fichiers = [("agents.json", texte), ("agents.js", "window.JARVIS_AGENTS = " + texte + ";\n"), ("docs.js", "window.JARVIS_DOCS = " + docs + ";\n")]
    if chiffres_ventes is not None:      # ventes.js : même contenu que ventes.json, lu par la page même en file://
        v = masquer(json.dumps(chiffres_ventes, ensure_ascii=False, indent=1))
        fichiers += [("ventes.json", v), ("ventes.js", "window.JARVIS_VENTES = " + v + ";\n")]
    for nom, contenu in fichiers:
        tmp = SORTIE / (nom + ".tmp"); tmp.write_text(contenu, encoding="utf-8"); os.replace(tmp, SORTIE / nom)


def main():
    maintenant = datetime.now(); rs = None
    if os.environ.get("JARVIS_TEST") != "1":
        try: rs = _resume_sid()
        except Exception: rs = None      # ventes() redit la raison
    v = ventes(maintenant, rs)
    dispo, fs = feuilles_sid(rs)
    jour = maintenant.date().isoformat()
    if dispo: aligner_jour(v, fs, jour)
    lds = leads_de_la_file(jour); dispo_l = lds is not None   # la file unique d'abord ; sinon les feuilles de Sid (secours)
    if not dispo_l: dispo_l, lds = leads_a_appeler(fs, jour) if dispo else (False, fs)
    v["chiffres"].append(dict(cle="potentiel", libelle="Potentiel", **potentiel(dispo_l, lds)))
    leads = {"jour": jour, "genere_le": maintenant.strftime("%Y-%m-%d %H:%M:%S"), "critere": "file unique des leads chauds (registre) : « À rappeler » ou « Je dois réfléchir » noté par Sid, sans STOP ni refus ; rappel par Sid ou un closer",
             "leads": lds if dispo_l else [], "raison": "" if dispo_l else str(lds)}
    ecrire(construire(maintenant), v, historique(maintenant, v, fs if dispo else None), leads)
    if "--ouvrir" in sys.argv[1:] and os.name == "nt": os.startfile(str(SORTIE / "index.html"))


if __name__ == "__main__":
    main()
