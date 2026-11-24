#!/usr/bin/env python3
"""Gardien de l'architecture (24/11/2026) : page « Architecture » du tableau de bord, carte du trajet d'un client et fiches de 3 lignes,
GÉNÉRÉES depuis les contrats (B2B\\harness\\contrats), serveur-taches.json et les traces. Rien n'est écrit à la main, aucun réseau, aucune IA.

  python B2B\\harness\\architecture.py              régénère les deux blocs de docs\\COMMENT-CA-MARCHE.md (carte Mermaid, fiches de 3 lignes)
  python B2B\\harness\\architecture.py --verifier   code 1 si : un agent n'a pas de fiche/note, un agent planifié n'a pas de contrat, une étape du trajet
                                                  n'a plus d'agent, ou si les blocs du document ne sont pas à jour (nouvel agent = relancer ce script)
  python B2B\\harness\\architecture.py --json       affiche les données de la page Architecture

Règle d'ajout : un agent (contrat) sans note dans fiches-noms.json, sans entrée dans les blocs générés ou sans contrat alors qu'il a une tâche serveur
fait échouer les tests (tests\\harness.ps1, tests\\b2b-rapide.ps1). Aucun contrôle existant n'est contourné : ce script s'ajoute à valider.py et generer-fiches.py.
Les blocs écrits dans le document sont STATIQUES (identiques d'une machine à l'autre) ; l'état réel (actif, jamais passé, en erreur) n'est que dans la page du tableau de bord."""
import importlib.util, json, re, sys
from datetime import date, datetime
from pathlib import Path

ICI = Path(__file__).resolve().parent
RACINE = ICI.parent.parent
sys.path.insert(0, str(ICI))
import traces as T   # noqa: E402

_spec = importlib.util.spec_from_file_location("generer_fiches", ICI / "generer-fiches.py")
GF = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(GF)

DOC = RACINE / "docs" / "COMMENT-CA-MARCHE.md"
AGENTS_DIR = RACINE / "B2B" / "agents"
ARCHIVES_JSON = RACINE / "docs" / "archives" / "agents-retires" / "gardien-archives.json"   # agents rangés par le gardien : {nom: {note, date}}
JOURS_SILENCE = 14
B_CARTE = ("<!-- CARTE:DEBUT (généré par python B2B\\harness\\architecture.py : ne pas modifier) -->", "<!-- CARTE:FIN -->")
B_FICHES = ("<!-- FICHES:DEBUT (généré par python B2B\\harness\\architecture.py : ne pas modifier) -->", "<!-- FICHES:FIN -->")
# Trajet d'un client : (identifiant, libellé, agent du contrat ou None si aucun agent n'existe). Si un agent est renommé, --verifier échoue.
CHAINE = [("prospection", "Prospection", "prospection"), ("appels", "Appels", "appels-sid"), ("chauds", "Leads chauds", "relances"),
          ("rdv", "Rendez-vous", "rendez-vous"), ("devis", "Devis", "devis"), ("paiement", "Paiement", "stripe-alerte"),
          ("production", "Production du site", "production"), ("validation", "Validation et mise en ligne", None)]
HUMAIN = re.compile(r"valid|attend|accord|« go|ok devis", re.I)
FICHIER = re.compile(r"[\w./\\-]+\.(?:json|csv|md|jsonl|xlsx|pdf)", re.I)


def archives():
    try: return json.loads(ARCHIVES_JSON.read_text(encoding="utf-8"))
    except (OSError, ValueError): return {}


def actifs():
    """Contrats des agents qui ont une note (les retirés et les archivés par le gardien n'y sont pas)."""
    n = GF.noms()
    return [c for c in GF.contrats() if n.get(c["nom"]) and c["nom"] not in archives()]


def fichiers(liste):
    """Noms de fichiers (sans dossier) cités dans une liste de lignes d'un contrat."""
    out = set()
    for ligne in liste:
        for f in FICHIER.findall(str(ligne).replace("\\", "/")): out.add(f.rsplit("/", 1)[-1].lower())
    return out


def _propres(c):
    """Fichiers lus / écrits en excluant ceux de l'agent lui-même (journal, état) pour ne chercher que les échanges entre agents."""
    return fichiers(c["fichiers_lus"]), {f for f in fichiers(c["fichiers_ecrits"]) if not f.startswith(c["nom"] + "-")}


def consommateurs(cs):
    """{agent: [agents qui lisent un fichier qu'il écrit]}."""
    lus = {c["nom"]: _propres(c)[0] for c in cs}
    return {c["nom"]: sorted(o for o, l in lus.items() if o != c["nom"] and l & _propres(c)[1]) for c in cs}


def derniere_activite(nom, dossier=None):
    """AAAA-MM-JJ du dernier signe de vie : dernière trace du harness, sinon date du fichier d'état / journal de l'agent. None = jamais."""
    jours = []
    d = (dossier or T.dossier_logs()) / nom
    if d.is_dir(): jours += [p.stem for p in d.glob("*.jsonl") if re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.stem)]
    for suffixe in ("-etat.json", "-journal.log") if dossier is None else ():   # dossier fourni (tests) : seules les traces comptent
        p = AGENTS_DIR / f"{nom}{suffixe}"
        if p.is_file(): jours.append(datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d"))
    return max(jours) if jours else None


def etat_reel(c, aujourdhui=None, dossier=None):
    """-> (code, libellé) : actif / silencieux / erreur / jamais / ferme / prevu. Dynamique : jamais écrit dans le document."""
    nom, auj = c["nom"], aujourdhui or date.today()
    if c["statut"] == "prevu": return "prevu", "prévu, pas construit"
    dernier = derniere_activite(nom, dossier)
    d = (dossier or T.dossier_logs()) / nom
    if d.is_dir():
        for p in sorted(d.glob("*.jsonl"), reverse=True)[:1]:
            try:
                lignes = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
                lignes = [x for x in lignes if not str(x.get("decision", "")).startswith("garde ")]
                if lignes and lignes[-1].get("ok") is False: return "erreur", f"en erreur le {p.stem}"
            except (OSError, ValueError): pass
    if dernier is None: return ("ferme", "fermé, jamais passé") if c["statut"] == "inactif" else ("jamais", "jamais passé")
    age = (auj - date.fromisoformat(dernier)).days
    if age > JOURS_SILENCE: return "silencieux", f"aucun passage depuis {age} jours (dernier {dernier})"
    return "actif", f"dernier passage le {dernier}"


def declencheur(c, ts):
    return GF.horaire(c, ts.get(c["nom"]))


def mode(c, ts):
    if c["statut"] == "prevu": return "à construire"
    base = "auto" if ts.get(c["nom"]) else "humain / à la demande"
    return base + (", puis humain" if base == "auto" and HUMAIN.search(c["mission"]) else "")


def court(liste, n=4):
    liste = sorted(set(liste))
    return ", ".join(liste[:n]) + (f" (+{len(liste) - n})" if len(liste) > n else "") if liste else "rien"


def fiche3(c, ts, cons):
    """Fiche de 3 lignes : but ; déclencheur et mode ; ce qui entre et sort et qui en dépend. Déterministe."""
    lus, ecrits = fichiers(c["fichiers_lus"]), fichiers(c["fichiers_ecrits"])
    return [c["mission"].strip(), f"Déclencheur : {declencheur(c, ts)} · {mode(c, ts)} · statut {c['statut']}",
            f"Lit : {court(lus)} · écrit : {court(ecrits)} · utilisé par : {court(cons.get(c['nom'], []))}"]


def chaine(cs, cons):
    """Noeuds et liens du trajet d'un client. Un lien est PLEIN seulement si un fichier écrit par l'amont est lu par l'aval ; un noeud manque si son agent
    n'existe pas ou n'est qu'un contrat (statut prevu, pas de script). Tout le reste est en pointillé = maillon manquant."""
    par = {c["nom"]: c for c in cs}
    noeuds = []
    for ident, label, agent in CHAINE:
        c = par.get(agent) if agent else None
        manque = c is None or c["statut"] == "prevu" or not (RACINE / c.get("script", "x")).is_file()
        noeuds.append({"id": ident, "label": label, "agent": agent, "manque": manque, "statut": c["statut"] if c else "aucun agent"})
    liens = []
    for a, b in zip(noeuds, noeuds[1:]):
        plein = bool(a["agent"] and b["agent"] and b["agent"] in cons.get(a["agent"], []) and not a["manque"] and not b["manque"])
        liens.append({"de": a["id"], "vers": b["id"], "plein": plein})
    return noeuds, liens


def mermaid(noeuds, liens):
    l = ["```mermaid", "flowchart LR"]
    for n in noeuds:
        l.append(f'  {n["id"]}["{n["label"]}"]' + (":::manque" if n["manque"] else ""))
    l += [f'  {x["de"]} {"-->" if x["plein"] else "-.->"} {x["vers"]}' for x in liens]
    l += ["  classDef manque stroke-dasharray: 5 5,stroke:#b45309,color:#b45309", "```"]
    return "\n".join(l)


def manquants(noeuds, liens):
    lab = {n["id"]: n["label"] for n in noeuds}
    out = [f"{n['label']} : {'aucun agent' if not n['agent'] else 'agent seulement prévu (contrat sans script)'}" for n in noeuds if n["manque"]]
    return out + [f"{lab[x['de']]} → {lab[x['vers']]} : aucun fichier échangé entre les deux" for x in liens if not x["plein"]]


def construire(aujourdhui=None, dossier=None):
    cs, ts = actifs(), GF.taches()
    cons = consommateurs(cs)
    noeuds, liens = chaine(cs, cons)
    ags = []
    for c in cs:
        code, lib = etat_reel(c, aujourdhui, dossier)
        ags.append({"nom": c["nom"], "note": GF.noms()[c["nom"]], "but": c["mission"], "declencheur": declencheur(c, ts), "lit": sorted(fichiers(c["fichiers_lus"])),
                    "ecrit": sorted(fichiers(c["fichiers_ecrits"])), "utilise_par": cons[c["nom"]], "mode": mode(c, ts), "statut": c["statut"],
                    "etat": code, "etat_libelle": lib, "fiche": fiche3(c, ts, cons)})
    return {"genere_le": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "agents": ags, "noeuds": noeuds, "liens": liens, "manquants": manquants(noeuds, liens),
            "mermaid": mermaid(noeuds, liens)}


# --- document -------------------------------------------------------------------------------------------------------------------------
def bloc_carte(d):
    return ("## Carte du trajet d'un client (générée)\n\nTrait plein = un fichier passe d'un agent au suivant ; **pointillé = maillon manquant** (aucun fichier échangé, ou agent seulement prévu).\n\n"
            + d["mermaid"] + "\n\nMaillons manquants : " + (" ; ".join(d["manquants"]) if d["manquants"] else "aucun") + ".")


def bloc_fiches(d):
    l = ["## Fiches de 3 lignes (générées)\n"]
    for a in sorted(d["agents"], key=lambda x: x["nom"]):
        l.append(f"**{a['nom']}**\n" + "\n".join(f"- {x}" for x in a["fiche"]) + "\n")
    return "\n".join(l).rstrip()


def poser(texte, balises, bloc, avant):
    """Remplace le bloc entre balises ; s'il n'existe pas encore, l'insère juste avant le titre `avant` (ou à la fin)."""
    d, f = balises; neuf = f"{d}\n{bloc}\n{f}"
    if d in texte and f in texte: return re.sub(re.escape(d) + r".*?" + re.escape(f), lambda _m: neuf, texte, flags=re.S)
    i = texte.find(avant) if avant else -1
    return texte[:i] + neuf + "\n\n" + texte[i:] if i >= 0 else texte.rstrip("\n") + "\n\n" + neuf + "\n"


def document_attendu(texte, d):
    texte = poser(texte, B_CARTE, bloc_carte(d), "## Le trajet d'un client")
    return poser(texte, B_FICHES, bloc_fiches(d), "## Maillons manquants, par effet")


def verifier(d=None):
    d = d or construire(); pb = []
    cs, noms, ts = GF.contrats(), GF.noms(), GF.taches()
    for c in cs:
        n = c["nom"]
        if n not in noms: pb.append(f"agent « {n} » : aucune entrée dans fiches-noms.json (pas de fiche)")
    pb += [f"tâche serveur « {n} » sans contrat : un agent planifié doit avoir son contrat" for n in ts if n not in {c["nom"] for c in cs}]
    manque = [n["agent"] for n in d["noeuds"] if n["agent"] and n["agent"] not in {a["nom"] for a in d["agents"]}]
    pb += [f"trajet d'un client : l'agent « {a} » n'existe plus dans les contrats actifs (mettre CHAINE à jour)" for a in manque]
    pb += [f"agent « {a['nom']} » : fiche de 3 lignes incomplète" for a in d["agents"] if len(a["fiche"]) != 3 or not all(a["fiche"])]
    try: texte = DOC.read_text(encoding="utf-8")
    except OSError: return pb + [f"{DOC.name} illisible"]
    if document_attendu(texte, d) != texte:
        pb.append("docs\\COMMENT-CA-MARCHE.md : carte ou fiches de 3 lignes pas à jour (python B2B\\harness\\architecture.py)")
    return pb


def ecrire_doc(d=None):
    """Réécrit les deux blocs ; renvoie True si le fichier a changé. Écriture atomique, reste du document intact."""
    d = d or construire(); texte = DOC.read_text(encoding="utf-8"); neuf = document_attendu(texte, d)
    if neuf == texte: return False
    tmp = DOC.with_name(DOC.name + ".tmp"); tmp.write_text(neuf, encoding="utf-8", newline=""); tmp.replace(DOC)
    return True


def main(argv=None):
    a = argv if argv is not None else sys.argv[1:]
    if "--json" in a: print(json.dumps(construire(), ensure_ascii=False, indent=1)); return 0
    if "--verifier" in a:
        pb = verifier()
        for p in pb: print("  ECHEC", p)
        print(f"architecture : {'ROUGE, ' + str(len(pb)) + ' problème(s)' if pb else 'verte, fiches, tâches, trajet et document à jour'}")
        return 1 if pb else 0
    print("COMMENT-CA-MARCHE.md réécrit" if ecrire_doc() else "COMMENT-CA-MARCHE.md déjà à jour"); return 0


if __name__ == "__main__":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass
    sys.exit(main())
