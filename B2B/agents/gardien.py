#!/usr/bin/env python3
"""Gardien de l'architecture (24/11/2026) : une fois par semaine (dimanche 21:00, serveur), il vérifie que les agents, leurs fiches et leurs échanges de fichiers
tiennent ensemble. D'abord un script gratuit, puis (seulement s'il y a des suspects) UNE passe `claude -p` (Sonnet 5.5, sans outil) pour juger les vrais doublons.

  python agents\\gardien.py passage [--essai] [--maintenant AAAA-MM-JJTHH:MM]   un passage hebdomadaire (essai : n'écrit, n'envoie, ne relance, n'archive rien, pas de passe Claude)
  python agents\\gardien.py etat                                                verrou, dernier passage, agents archivés
  python agents\\gardien.py restaurer <agent>                                   remet un agent archivé (fiche, copie de skill, liens)

CORRIGE SEUL (réversible) : liens de notes cassés (remplacés par leur texte), fiches et carte régénérées (generer-fiches.py, architecture.py), notes orphelines rangées
dans docs\\archives\\agents-retires, redémarrage d'un agent en panne (liste fermée REDEMARRABLES, une fois par jour), réparation d'un fichier d'échange absent en relançant
son producteur ; ARCHIVE (jamais supprime) un agent sans exécution depuis 30 jours que rien n'exige.
NE TOUCHE JAMAIS SEUL (fiche B2B\\a-valider + attend « go ») : tout agent qui envoie à un prospect, publie ou encaisse, envoi_automatique et tout réglage d'envoi,
les liens de docs\\decisions, un vrai doublon, un agent qui reste en panne. Ce script n'écrit dans AUCUN fichier de réglages.
VERROU : go_gardien (gardien-config.json, variante locale) ET le verrou commun ; fermé = rien n'est corrigé ni envoyé. Tâche serveur : seulement si « gardien » est dans agents_actifs."""
import argparse, json, os, re, shutil, subprocess, sys, tempfile, time
from datetime import date, datetime, timedelta
from pathlib import Path

ICI = Path(__file__).resolve().parent
RACINE = ICI.parent.parent
sys.path.insert(0, str(ICI))
import machine as M   # noqa: E402

sys.path.insert(0, str(ICI.parent / "harness"))
import superviseurs as S   # noqa: E402  réglages, verrou, état, journal, relance, Discord, fiche a-valider
import traces as T         # noqa: E402
import architecture as AR  # noqa: E402  contrats actifs, état réel, carte
import graphe as GR        # noqa: E402  résolution des liens du coffre

AGENT = "gardien"
DEFAUT = {"go_gardien": False, "jours_silence": 14, "jours_archive": 30, "heure_debut": "07:00", "heure_fin": "23:00",
          "claude": {"commande": "claude", "modele": "claude-sonnet-5-5", "delai_secondes": 240}}
# Seuls ces agents peuvent être relancés seuls : aucun n'écrit à un prospect, ne publie ni n'encaisse (ils parlent à Liam ou écrivent des fichiers locaux).
REDEMARRABLES = {"relances", "appels-sid", "rendez-vous", "resume-sid", "stripe-alerte", "sauvegarde-leads", "nettoyage-fichiers", "panne-alerte",
                 "surveillant", "superviseur-vente", "superviseur-prospection"}
ARCHIVE = RACINE / "docs" / "archives" / "agents-retires"
NOTES = RACINE / "docs" / "agents"
FICHES_NOMS = RACINE / "B2B" / "harness" / "fiches-noms.json"
SORTIES_ETAT = re.compile(r"^b2b/(agents/[\w-]+-etat\.json|donnees/[\w.-]+\.(?:json|csv|jsonl))$", re.I)
LIEN = re.compile(r"\[\[([^\]|#\\]+)(#[^\]|\\]*)?(?:\\?\|([^\]]*))?\]\]")
CRITIQUE = "gros|"      # préfixe de clé : un souci « gros » déclenche la ligne d'alerte en tête du rapport


def contrats():
    """Contrats des agents vivants (les agents retirés ou archivés, sans fiche, ne comptent plus)."""
    return {c["nom"]: c for c in AR.actifs()}


def sensible(c):
    """Un agent qu'on ne relance ni n'archive jamais seul : il peut écrire à un prospect, publier ou encaisser, ou n'est pas dans la liste fermée."""
    return bool(c.get("envoi_client")) or c["nom"] not in REDEMARRABLES


def relance_unique(nom, jour, etat, ts, conf, relance):
    def rep():
        if nom in (etat["relances"].get(jour) or {}): return f"{nom} déjà relancé aujourd'hui"
        ok, d = (relance or S.relancer)(nom, ts)
        etat["relances"].setdefault(jour, {})[nom] = d
        return f"agent {nom} relancé : {d}"
    return rep


# --- contrôles (gratuits) ------------------------------------------------------------------------------------------------------------
def ctrl_inactivite(ctx):
    out = []
    for nom, c in ctx["contrats"].items():
        t = ctx["ts"].get(nom)
        if c["statut"] not in ("actif", "simulation") or not t or nom not in ctx["actifs"] or nom == AGENT: continue
        if t.get("actif_le") and ctx["jour"] < str(t["actif_le"]): continue
        dernier = AR.derniere_activite(nom, ctx["traces"])
        age = None if dernier is None else (ctx["date"] - date.fromisoformat(dernier)).days
        if age is not None and age <= ctx["conf"]["jours_silence"]: continue
        quoi = f"n'a pas tourné depuis {ctx['conf']['jours_silence']} jours" if age is None else f"n'a pas tourné depuis {age} jours"
        if sensible(c): out.append(S.risque(nom, quoi, "peut écrire à un prospect, publier ou encaisser : relance seulement avec ton « go »", cle=CRITIQUE + f"{nom}|silence"))
        else: out.append(S.sur(nom, quoi, relance_unique(nom, ctx["jour"], ctx["etat"], ctx["ts"], ctx["conf"], ctx["relance"]), cle=f"{nom}|silence"))
    return out


def ctrl_circulation(ctx):
    """Un fichier d'échange déclaré dans un contrat (état d'agent, B2B\\donnees) qui n'existe pas alors que son producteur tourne : on relance le producteur (liste fermée)."""
    out, vus = [], set()
    for nom, c in ctx["contrats"].items():
        if c["statut"] not in ("actif", "simulation"): continue
        for ligne in c["fichiers_lus"]:
            for f in AR.FICHIER.findall(str(ligne).replace("\\", "/")):
                if not SORTIES_ETAT.match(f) or f.lower() in vus or "local" in f.lower() or (RACINE / f).exists(): continue
                vus.add(f.lower())
                prod = [p for p, cp in ctx["contrats"].items() if p != nom and f.rsplit("/", 1)[-1].lower() in AR.fichiers(cp["fichiers_ecrits"])]
                if not prod:
                    out.append(S.risque(nom, f"lit {f.rsplit('/', 1)[-1]} que personne n'écrit", "contrat à corriger ou agent à construire", cle=f"{nom}|{f}|sans-producteur")); continue
                p = prod[0]; cp = ctx["contrats"][p]
                if sensible(cp) or p not in ctx["actifs"]:
                    out.append(S.risque(nom, f"lit {f.rsplit('/', 1)[-1]} absent", f"producteur {p} : relance seulement avec ton « go » (ou agent pas planifié ici)", cle=f"{nom}|{f}|absent"))
                else:
                    out.append(S.sur(nom, f"lit {f.rsplit('/', 1)[-1]} absent", relance_unique(p, ctx["jour"], ctx["etat"], ctx["ts"], ctx["conf"], ctx["relance"]),
                                     f"on relance son producteur {p}", cle=f"{nom}|{f}|absent"))
    return out


def suspects_doublons(cs):
    """Paires d'agents qui partagent un script, une mission quasi identique ou un fichier écrit hors état/journal/config."""
    norm = lambda s: re.sub(r"\W+", " ", s.lower()).strip()
    out = []
    noms = sorted(cs)
    for i, a in enumerate(noms):
        for b in noms[i + 1:]:
            ca, cb = cs[a], cs[b]
            if ca["statut"] == "prevu" or cb["statut"] == "prevu": continue
            commun = {f for f in AR.fichiers(ca["fichiers_ecrits"]) & AR.fichiers(cb["fichiers_ecrits"]) if not re.search(r"etat|journal|config|token", f)}
            meme = (ca.get("script") and ca.get("script") == cb.get("script")) or norm(ca["mission"]) == norm(cb["mission"])
            if commun or meme: out.append({"agents": [a, b], "raison": "script ou mission identique" if meme else "écrivent le même fichier : " + ", ".join(sorted(commun))})
    return out


def prompt_doublons(suspects, cs):
    corps = "\n".join(f"- {s['agents'][0]} / {s['agents'][1]} ({s['raison']}) :\n    {cs[s['agents'][0]]['mission']}\n    {cs[s['agents'][1]]['mission']}" for s in suspects)
    return ("Tu relis des couples d'agents d'une petite agence (prospection par téléphone et e-mail, devis, paiement). Pour chaque couple, dis s'ils font VRAIMENT le même travail "
            "(un doublon à fusionner) ou s'ils sont complémentaires. Réponds uniquement par un JSON : {\"vrais_doublons\":[{\"agents\":[\"a\",\"b\"],\"raison\":\"une phrase\"}]}, "
            "ou {\"vrais_doublons\":[]}. Aucun outil, aucune autre phrase.\n\n" + corps)


def appel_claude_reel(conf, prompt):
    c = conf["claude"]; exe = shutil.which(c["commande"]) or str(Path.home() / ".local" / "bin" / "claude.exe")
    d = tempfile.mkdtemp(prefix="gardien-claude-")
    try:
        r = subprocess.run([exe, "-p", "--model", c["modele"], "--tools", "", "--no-session-persistence", "--output-format", "text"], input=prompt, capture_output=True,
                           text=True, encoding="utf-8", timeout=c["delai_secondes"], cwd=d, creationflags=0x08000000 if os.name == "nt" else 0)
    except (OSError, subprocess.TimeoutExpired): raise S.ErreurAgent("passe Claude impossible (commande introuvable ou délai dépassé)")
    finally: shutil.rmtree(d, ignore_errors=True)
    if r.returncode != 0 or not r.stdout.strip(): raise S.ErreurAgent(f"passe Claude impossible (code {r.returncode})")
    return r.stdout


def ctrl_doublons(ctx):
    sus = suspects_doublons(ctx["contrats"])
    if not sus or ctx["essai"]: return [S.risque("doublons", f"{len(sus)} couple(s) suspect(s), pas jugés (essai)", cle="doublons|essai")] if sus else []
    try: texte = (ctx["claude"] or appel_claude_reel)(ctx["conf"], prompt_doublons(sus, ctx["contrats"]))
    except S.ErreurAgent as e: return [S.risque("doublons", f"{len(sus)} suspect(s) non jugés", str(e), cle="doublons|claude")]
    m = re.search(r"\{.*\}", texte or "", re.S)
    try: v = json.loads(m.group(0)).get("vrais_doublons", []) if m else []
    except ValueError: v = []
    valides = {tuple(s["agents"]) for s in sus}
    return [S.risque(" / ".join(x["agents"]), "vrai doublon selon Claude", str(x.get("raison", ""))[:160] + " — à fusionner par Liam, rien n'est touché", cle="doublon|" + "|".join(x["agents"]))
            for x in v if isinstance(x, dict) and isinstance(x.get("agents"), list) and tuple(x["agents"]) in valides]


def ctrl_liens(ctx):
    notes = GR.toutes_notes(); par_nom = {}
    for n in sorted(notes, key=len): par_nom.setdefault(Path(n).stem.casefold(), []).append(n)
    out = []
    for p in sorted(NOTES.glob("*.md")) + [AR.DOC]:
        t = p.read_text(encoding="utf-8")
        cassés = [m.group(1).strip() for m in LIEN.finditer(t) if GR.resoudre(m.group(1).strip(), notes, par_nom) is None]
        if not cassés: continue
        if any(c.startswith("docs/decisions/") for c in cassés):
            out.append(S.risque(p.name, "lien cassé vers une décision", "les liens de docs\\decisions ne sont jamais réécrits seuls", cle=f"lien|{p.name}|decision"))
            cassés = [c for c in cassés if not c.startswith("docs/decisions/")]
        if not cassés: continue

        def rep(p=p, cassés=set(cassés)):
            t = p.read_text(encoding="utf-8")
            def sub(m):
                if m.group(1).strip() not in cassés: return m.group(0)
                return (m.group(3) or Path(m.group(1)).stem).strip()
            neuf = LIEN.sub(sub, t); p.write_text(neuf, encoding="utf-8", newline="")
            return f"{len(cassés)} lien(s) cassé(s) remplacé(s) par leur texte dans {p.name}"
        out.append(S.sur(p.name, f"{len(cassés)} lien(s) cassé(s)", rep, ", ".join(sorted(set(cassés)))[:120], cle=f"lien|{p.name}"))
    return out


def lancer_script(script, *args):
    r = subprocess.run([sys.executable, str(RACINE / "B2B" / "harness" / script), *args], cwd=str(RACINE), capture_output=True, text=True, encoding="utf-8", timeout=300,
                       env=dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1"), creationflags=0x08000000 if os.name == "nt" else 0)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def ctrl_fiches(ctx):
    out = []
    if ctx.get("sans_scripts"): return out
    code, sortie = lancer_script("generer-fiches.py", "--verifier")
    if code != 0:
        def rep():
            lancer_script("generer-fiches.py")
            c2, s2 = lancer_script("generer-fiches.py", "--verifier")
            if c2 != 0: raise RuntimeError("fiches encore en défaut : " + s2.strip().splitlines()[-1][:100] if s2.strip() else "fiches encore en défaut")
            return "fiches des agents régénérées (generer-fiches.py), contrôle vert"
        out.append(S.sur("fiches", "fiches des agents pas à jour", rep, cle="fiches|generer"))
    code, sortie = lancer_script("architecture.py", "--verifier")
    if code != 0:
        def rep2():
            lancer_script("architecture.py")
            c2, s2 = lancer_script("architecture.py", "--verifier")
            if c2 != 0: raise RuntimeError("architecture encore en défaut : " + (s2.strip().splitlines() or ["?"])[0][:100])
            return "carte et fiches de 3 lignes régénérées (architecture.py), contrôle vert"
        out.append(S.sur("architecture", "carte ou fiches de 3 lignes pas à jour", rep2, cle="architecture|generer"))
    noms = {c["nom"] for c in AR.GF.contrats()}
    for p in sorted(NOTES.glob("*.md")):
        m = re.search(r"^agent:\s*(\S+)", p.read_text(encoding="utf-8")[:600], re.M)
        if m and m.group(1) not in noms:
            out.append(S.sur(p.name, f"fiche orpheline (aucun contrat « {m.group(1)} »)", lambda p=p: ranger(p), "rangée dans docs\\archives\\agents-retires", cle=f"orpheline|{p.name}"))
    return out


def ranger(p):
    ARCHIVE.mkdir(parents=True, exist_ok=True); dest = ARCHIVE / p.name
    if dest.exists(): raise RuntimeError(f"{dest.name} existe déjà dans l'archive : rien déplacé")
    shutil.move(str(p), str(dest)); return f"fiche orpheline {p.name} rangée dans docs\\archives\\agents-retires"


def ctrl_contradictions(ctx):
    out = []
    for nom in sorted(ctx["actifs"]):
        c = ctx["contrats"].get(nom)
        if nom == AGENT: continue
        if c is None: out.append(S.risque(nom, "dans agents_actifs mais sans contrat vivant (retiré, archivé ou jamais déclaré)", "à retirer de agents_actifs ou à déclarer par Liam", cle=f"{nom}|sans-contrat"))
        elif c["statut"] in ("inactif", "prevu"):
            out.append(S.risque(nom, f"planifié ici alors que son contrat est « {c['statut']} »", "le contrat ou la planification dit faux : Liam tranche", cle=f"{nom}|contradiction"))
    return out


# --- archivage ---------------------------------------------------------------------------------------------------------------------
def archives_lire():
    try: return json.loads(AR.ARCHIVES_JSON.read_text(encoding="utf-8"))
    except (OSError, ValueError): return {}


def archives_ecrire(a):
    AR.ARCHIVES_JSON.parent.mkdir(parents=True, exist_ok=True)
    AR.ARCHIVES_JSON.write_text(json.dumps(a, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def exige_par_ailleurs(nom, cs):
    """Un agent que rien ne justifie de garder en pause : il figure dans le trajet du client, un autre contrat le lit ou un autre test le cite."""
    if nom in {a for _, _, a in AR.CHAINE} or nom == "jarvis-ceo": return "il figure dans le trajet du client"
    if any(nom in " ".join(c["fichiers_lus"]) for n, c in cs.items() if n != nom): return "un autre contrat le lit"
    propres = {Path(t).name for t in cs[nom]["tests"]}
    for dossier in (RACINE / "tests", RACINE / "B2B" / "agents"):
        for f in dossier.rglob("test*.py"):
            if f.name in propres or "__pycache__" in f.parts: continue
            try:
                if re.search(r'["\']' + re.escape(nom) + r'["\']', f.read_text(encoding="utf-8", errors="replace")): return f"{f.name} le cite"
            except OSError: pass
    return None


def archiver(nom):
    """Range un agent (jamais de suppression) : fiche et copies de skills -> archive, liens retirés des notes, entrée de fiches-noms à null. Réversible : restaurer()."""
    noms = json.loads(FICHES_NOMS.read_text(encoding="utf-8"))
    note = noms.get(nom)
    if not note: raise RuntimeError(f"{nom} n'a pas de fiche à ranger")
    src = NOTES / f"{note}.md"
    enr = {"note": note, "date": date.today().isoformat(), "fichiers": [], "liens": {}}
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    for f in [src] + [NOTES / "skills" / f"{s}.md" for s in AR.GF.skills_de(nom)]:
        if f.is_file():
            if (ARCHIVE / f.name).exists(): raise RuntimeError(f"{f.name} existe déjà dans l'archive")
            shutil.move(str(f), str(ARCHIVE / f.name)); enr["fichiers"].append(str(f.relative_to(NOTES)).replace("\\", "/"))
    lien = r"\[\[docs/agents/" + re.escape(note) + r"(?:\|[^\]]*)?\]\]"
    for p in sorted(NOTES.glob("*.md")):      # lien vers la fiche rangée (arbre des liens) : retiré de sa ligne, mémorisé pour la restauration
        t = p.read_text(encoding="utf-8")
        if re.search(lien, t):
            enr["liens"][p.name] = note
            neuf = re.sub(lien + " · ", "", t, count=1) if re.search(lien + " · ", t) else re.sub(" · " + lien, "", t, count=1) if re.search(" · " + lien, t) else re.sub(lien, "", t, count=1)
            p.write_text(neuf, encoding="utf-8", newline="")
    t = FICHES_NOMS.read_text(encoding="utf-8")
    neuf = re.sub(r'("' + re.escape(nom) + r'"\s*:\s*)"[^"]*"', r"\1null", t, count=1)
    FICHES_NOMS.write_text(neuf, encoding="utf-8", newline="")
    a = archives_lire(); a[nom] = enr; archives_ecrire(a)
    return f"agent {nom} archivé (fiche et liens rangés ; restauration : python B2B\\agents\\gardien.py restaurer {nom})"


def restaurer(nom):
    a = archives_lire(); enr = a.get(nom)
    if not enr: raise S.ErreurAgent(f"{nom} n'est pas dans l'archive du gardien")
    for rel in enr["fichiers"]:
        src = ARCHIVE / Path(rel).name
        if src.is_file(): (NOTES / rel).parent.mkdir(parents=True, exist_ok=True); shutil.move(str(src), str(NOTES / rel))
    for nom_note, note in enr["liens"].items():
        p = NOTES / nom_note
        if p.is_file():
            t = p.read_text(encoding="utf-8"); lien = f"[[docs/agents/{note}|{note}]]"
            if lien not in t: p.write_text(re.sub(r"^(Liens : .*?)\s*$", lambda m: m.group(1) + " · " + lien, t, count=1, flags=re.M), encoding="utf-8", newline="")
    t = FICHES_NOMS.read_text(encoding="utf-8")
    FICHES_NOMS.write_text(re.sub(r'("' + re.escape(nom) + r'"\s*:\s*)null', lambda m: m.group(1) + json.dumps(enr["note"], ensure_ascii=False), t, count=1), encoding="utf-8", newline="")
    del a[nom]; archives_ecrire(a)
    lancer_script("generer-fiches.py"); lancer_script("architecture.py")
    return f"agent {nom} restauré (relancer la tâche serveur et l'ajouter à agents_actifs si besoin)"


def ctrl_archivage(ctx):
    out = []
    for nom, c in ctx["contrats"].items():
        if nom == AGENT or not AR.GF.noms().get(nom) or nom in archives_lire(): continue
        if c["statut"] not in ("inactif", "prevu") or ctx["ts"].get(nom): continue      # un agent actif, ou fermé avec sa tâche serveur (attend le « go » de Liam), n'est jamais archivé seul
        dernier = AR.derniere_activite(nom, ctx["traces"])
        if dernier is not None and (ctx["date"] - date.fromisoformat(dernier)).days <= ctx["conf"]["jours_archive"]: continue
        if c.get("envoi_client"): continue
        raison = exige_par_ailleurs(nom, ctx["contrats"])
        if raison: continue
        out.append(S.sur(nom, f"sans exécution depuis {ctx['conf']['jours_archive']} jours et rien ne l'exige", lambda nom=nom: archiver(nom),
                         "archivé, jamais supprimé", cle=f"archive|{nom}"))
    return out


CONTROLES = [("inactivité", ctrl_inactivite), ("circulation des fichiers", ctrl_circulation), ("doublons", ctrl_doublons), ("liens", ctrl_liens),
             ("fiches", ctrl_fiches), ("contradictions", ctrl_contradictions), ("archivage", ctrl_archivage)]


# --- rapport (10 lignes au plus) ---------------------------------------------------------------------------------------------------
def rapport(soucis, manquants):
    repares = [s.change for s in soucis if s.corrige and not s.cle.startswith("archive|")]
    archives = [s.change for s in soucis if s.corrige and s.cle.startswith("archive|")]
    go = [s for s in soucis if s.risque]
    gros = [s for s in go if s.cle.startswith(CRITIQUE)]
    l = []
    if gros: l.append("**⚠ Gros problème** : " + " ; ".join(s.ligne() for s in gros[:2])[:300])
    l.append(f"**Gardien de l'architecture — semaine du {date.today():%d/%m}**")
    l.append(f"- Réparé seul ({len(repares)}) : " + (" ; ".join(repares[:3])[:300] if repares else "rien à réparer"))
    l.append(f"- Archivé ({len(archives)}) : " + (" ; ".join(archives[:2])[:200] if archives else "rien"))
    l.append(f"- Attend ton « go » ({len(go)}) :" + ("" if go else " rien"))
    l += [f"  · {s.ligne()}"[:200] for s in go[:3]]
    if len(go) > 3: l.append(f"  · … et {len(go) - 3} autre(s) dans B2B\\a-valider")
    l.append(f"- Maillons manquants ({len(manquants)}) : " + ("; ".join(manquants[:3])[:260] if manquants else "aucun"))
    return "\n".join(l[:10])


def passage(conf, essai=False, maintenant=None, relance=None, envoyer=None, claude=None, traces=None, sans_scripts=False, ts=None, actifs=None):
    m = maintenant or datetime.now(); jour = f"{m:%Y-%m-%d}"
    etat = S.etat_lire(AGENT)
    verrou = not conf["go_superviseurs"] and not essai
    ctx = {"contrats": contrats(), "ts": S.taches() if ts is None else ts, "actifs": S.agents_actifs() if actifs is None else actifs, "conf": conf, "jour": jour, "date": m.date(),
           "etat": etat, "relance": relance, "claude": claude, "traces": traces, "essai": essai, "sans_scripts": sans_scripts}
    soucis = S.collecter([(n, (lambda f=f: f(ctx))) for n, f in CONTROLES])
    for s in soucis:
        if not s.reparer or essai or verrou or STOP():
            continue
        try:
            s.change = s.reparer() or s.ligne(); s.corrige = True
            etat["corrections"].setdefault(jour, []).append(s.change); S.journaliser(AGENT, "corrige", s.change)
        except Exception as ex:
            s.corrige = False; s.detail = (s.detail + " ; " if s.detail else "") + f"correction impossible ({type(ex).__name__})"
            if s.cle.startswith("archive|") or s.cle.startswith("fiches|") or s.cle.startswith("architecture|"):
                s.risque = True; s.reparer = None      # ce qu'on n'a pas pu réparer seul attend Liam
    d = AR.construire(m.date(), traces)
    texte = rapport(soucis, d["manquants"])
    bloques = [s for s in soucis if s.risque]
    if essai: poste = "essai : rien envoyé, rien écrit, rien relancé, pas de passe Claude"
    elif verrou: poste = "verrou « go gardien » fermé : rien corrigé, rien envoyé"
    elif conf["envoi_automatique"] and S.dans_plage(m, conf): poste = "posté sur Discord" if (envoyer or S.alerter_discord)(texte) else "Discord : non envoyé"
    else: poste = "simulation (envoi_automatique = false) ou hors plage : rien envoyé"
    f = None
    if not essai and not verrou:
        f = S.fiche_a_valider(AGENT, "Gardien", bloques, jour)
        etat["en_attente"] = {s.cle: {"depuis": jour, "quoi": s.ligne()[:300]} for s in bloques}; etat["resumes"][jour] = f"{m:%H:%M}"
        S.etat_ecrire(AGENT, etat)
        S.journaliser(AGENT, "passage", f"{sum(1 for s in soucis if s.corrige)} correction(s), {len(bloques)} en attente ; {poste}" + (f" ; fiche {f.name}" if f else ""))
    print(texte); print(f"  [{poste}]")
    return soucis, texte


def STOP(): return S.STOP.exists()


def cmd_etat(conf):
    e = S.etat_lire(AGENT); a = archives_lire()
    print(f"Gardien : verrou « go gardien » {'ouvert' if conf['go_superviseurs'] else 'fermé'} ; dernier passage : {max(e['resumes']) if e['resumes'] else 'aucun'}.")
    print(f"  en attente d'un « go » : {len(e['en_attente'])}" + "".join(f"\n    - {v['quoi']}" for v in list(e["en_attente"].values())[:10]))
    print(f"  agents archivés : {', '.join(sorted(a)) or 'aucun'}" + (" (restaurer : gardien.py restaurer <agent>)" if a else ""))
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog=AGENT, description="Gardien de l'architecture : hebdomadaire, autonome sur le réversible.")
    sp = p.add_subparsers(dest="cmd", required=True)
    j = sp.add_parser("passage"); j.add_argument("--essai", "--a-blanc", dest="essai", action="store_true"); j.add_argument("--maintenant", default=None)
    sp.add_parser("etat"); r = sp.add_parser("restaurer"); r.add_argument("agent")
    a = p.parse_args(argv)
    M.exiger(AGENT, a.cmd, getattr(a, "essai", False))
    t0 = time.time()
    try:
        conf = S.cfg(AGENT, DEFAUT)
        if a.cmd == "etat": return cmd_etat(conf)
        if a.cmd == "restaurer": print(" ", restaurer(a.agent)); return 0
        soucis, _ = passage(conf, a.essai, datetime.fromisoformat(a.maintenant) if a.maintenant else None)
        if not a.essai: T.ecrire(AGENT, "passage", f"{sum(1 for s in soucis if s.corrige)} correction(s), {sum(1 for s in soucis if s.risque)} en attente de go", time.time() - t0, ok=True)
        return 0
    except S.ErreurAgent as e:
        print(f"  ! {e}")
        if a.cmd == "passage" and not a.essai: T.ecrire(AGENT, "passage", "échec", time.time() - t0, ok=False, erreur=str(e))
        return 2
    except OSError as e:
        print(f"  ! erreur de fichier : {e.strerror or type(e).__name__}"); return 2


if __name__ == "__main__":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass
    sys.exit(main())
