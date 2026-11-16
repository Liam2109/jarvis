#!/usr/bin/env python3
"""Agent videos-marketing (équipe Vidéos TikTok, 16/11/2026), entre videos-scripts (05:00) et videos-creation (06:00, 14:00, 22:00).
Qwen local (Ollama, gratuit, aucun token Claude) choisit l'accroche ; le code fait le reste, sans réseau :
  1. accroche : Qwen n'invente pas : il choisit 3 formules à trous écrites à la main dans Videos\\hooks.md (ligne de la vidéo) et remplit seulement leurs trous
     (1 à 4 mots) ; le code assemble, complète avec des formules sans trou si besoin, ajoute (ligne B) le brouillon de Liam, et note chaque accroche sur 10 (grille de Videos\\SKILL-VIDEOS.md
     ; noter_accroche : forme qui accroche, 2 secondes, adresse directe, concret, neuve ; éliminée si chiffre, promesse, mot interdit, phrase molle, mauvais public,
     adresse épelée, lieu sur B) ;
     la meilleure remplace la première phrase et est inscrite dans Videos\\journal-videos.csv avec les 3 notes ;
  2. rythme : phrases de plus de 11 mots coupées en deux (une image toutes les 2 à 4 secondes), durée estimée 20 à 35 s vérifiée ;
  3. sous-titres : groupes de 2 à 4 mots, mot clé en couleur d'accent (commun.decouper_sous_titres), utilisés par videos-creation.
Règles relues avant chaque exécution (SKILL-VIDEOS.md). Rien n'est publié ni envoyé.
  python Videos\\agents\\marketing.py jour [--jour AAAA-MM-JJ] [--a-blanc]
  python Videos\\agents\\marketing.py passage --heure 06:00 [--jour AAAA-MM-JJ] [--a-blanc]
  python Videos\\agents\\marketing.py etat"""
import argparse, json, random, re, sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import commun as C   # noqa: E402
import scripts as S  # noqa: E402  (mêmes garde-fous que l'agent scripts : nombres, promesses, mots interdits, phrases molles, lieux)

AGENT = "videos-marketing"
MOTS_PAR_S = 2.6
FIN_CARTE_S = 3.0
ACCROCHE_FORTE = re.compile(r"\?|\bpourtant\b|\bfaux\b|\barr[êe]te\b|\bpersonne ne\b|\bjamais\b|\berreur\b|\bvous perdez\b|\btu rates\b|\bvous ratez\b|"
                            r"\bstop\b|\bsans (chercher|appeler|attendre)\b|\bvoil[àa] pourquoi\b|\bcash\b|\bvraiment\b", re.I)
CONCRET = re.compile(r"t[ée]l[ée]phone|horaire|bouton|appel|liste|script|rendez-vous|client|page|vitrine|photo|adresse|itin[ée]raire|num[ée]ro|"
                     r"dimanche|soir|matin|boutique|atelier|chantier|devis|carte|avis|commande|r[ée]servation|maison|canap[ée]", re.I)
OUVERTURE_MOLLE = re.compile(r"^\s*(bonjour|salut|aujourd'hui|d[ée]couvrez|dans cette vid[ée]o|voici|alors voil[àa])\b", re.I)
FORMULE = re.compile(r"^- ([AB]\d{2}) \| (.+?)\s*$")
TROU = re.compile(r"\{(\w+)\}")
SYSTEME = ("Tu es l'agent marketing d'une équipe de vidéos TikTok en bonhomme bâton. L'accroche est la toute première phrase, lue en deux secondes. "
           "Tu n'inventes jamais d'accroche : tu choisis des formules écrites à la main et tu remplis seulement leurs trous. Ton oral et naturel : {ton}. "
           "Grille de notation et règles de l'équipe :\n{grille}\n{regles}\nRéponds uniquement avec un objet JSON valide.")


def mots(t): return len(C.mots_de(t))


def elimine(texte, serie, conf):
    """Raison d'élimination d'une accroche (None si elle peut concourir) : mêmes garde-fous que les scripts, plus le bon public de la ligne."""
    for rx, quoi in ((S.NOMBRES, "chiffre ou nombre"), (S.INTERDITS, "formulation interdite"), (S.MOLLES, "phrase molle"), (S.DIDASCALIES, "mise en scène"),
                     (S.ADRESSE, "adresse épelée")):
        m = rx.search(texte or "")
        if m: return f"{quoi} (« {m.group(0)} »)"
    faux = S.public_faux(texte, serie)
    if faux: return f"mauvais public (« {faux} »)"
    if serie == "B":
        m = S.INTERDITS_B.search(texte or "")
        if m: return f"formulation interdite (« {m.group(0)} »)"
        lieu = S.lieu_interdit(texte, conf)
        if lieu: return f"lieu interdit (« {lieu} »)"
    if not (texte or "").strip(): return "vide"
    return None


def noter_accroche(texte, serie, conf, recentes=()):
    """Grille de SKILL-VIDEOS.md (« Grille des accroches »). -> (note sur 10, [raisons])."""
    raison = elimine(texte, serie, conf)
    if raison: return 0, [f"éliminée : {raison}"]
    note, r = 0, []
    if ACCROCHE_FORTE.search(texte): note += 3; r.append("forme qui accroche +3")
    n = mots(texte); pts = 3 if n <= 6 else 2 if n <= 8 else 1 if n <= 10 else 0
    note += pts; r.append(f"{n} mots +{pts}")
    direct = re.search(r"\b(tu|te|t'|toi|ton|ta|tes)\b", texte, re.I) if conf["lignes"][serie].get("tutoiement") else re.search(r"\b(vous|votre|vos)\b", texte, re.I)
    if direct: note += 2; r.append("adresse directe +2")
    if CONCRET.search(texte): note += 1; r.append("concret +1")
    cles = {m for m in S.norm(texte) if len(m) > 3}
    if not any(cles and len(cles & {m for m in S.norm(x) if len(m) > 3}) / len(cles) >= 0.6 for x in recentes): note += 1; r.append("neuve +1")
    if OUVERTURE_MOLLE.search(texte): note -= 3; r.append("ouverture molle -3")
    return max(0, min(10, note)), r


def choisir(candidates, serie, conf, recentes):
    """-> (meilleure ou None, [(texte, note, raisons)]). Égalité : la plus courte gagne."""
    notes = [(t.strip(), *noter_accroche(t.strip(), serie, conf, recentes)) for t in candidates if isinstance(t, str) and t.strip()]
    valables = [x for x in notes if x[1] > 0]
    best = max(valables, key=lambda x: (x[1], -mots(x[0])))[0] if valables else None
    return best, notes


def couper(phrase, maxi=11):
    """Coupe une phrase trop longue en deux (après une virgule, sinon avant « et / mais / donc / pour / avec ») si chaque moitié garde 4 mots ou plus."""
    ms = phrase.split()
    if len(ms) <= maxi: return [phrase]
    milieu = len(ms) / 2
    coupes = [i + 1 for i, m in enumerate(ms[:-1]) if m.endswith(",")] + [i for i, m in enumerate(ms) if m.lower() in {"et", "mais", "donc", "pour", "avec", "quand"}]
    coupes = [i for i in coupes if 4 <= i <= len(ms) - 4]
    if not coupes: return [phrase]
    i = min(coupes, key=lambda k: abs(k - milieu))
    a, b = " ".join(ms[:i]).rstrip(",") + ".", " ".join(ms[i:])
    return [a, b[0].upper() + b[1:]]


def duree_estimee(scenes): return round(sum(mots(s) for s in scenes) / MOTS_PAR_S + FIN_CARTE_S, 1)


def recentes_du_journal(n=20):
    return [r.get("hook", "") for r in C.csv_lire() if r.get("agent") == AGENT and r.get("hook")][-n:]


def formules(serie, texte=None):
    """Formules à trous écrites à la main pour la ligne (Videos\\hooks.md, sinon hooks-base.md). -> [(id, formule)]"""
    return [(m.group(1), m.group(2)) for m in (FORMULE.match(x.strip()) for x in (C.hooks_texte() if texte is None else texte).splitlines())
            if m and m.group(1).startswith(serie)]


def trous_aide(serie, texte=None):
    """Ligne « Trous : … » de la section de la ligne dans hooks.md (ce que chaque trou doit contenir)."""
    sec = C.section(C.hooks_texte() if texte is None else texte, f"Formules ligne {serie}")
    return next((x for x in sec.splitlines() if x.startswith("Trous")), "")


def remplir(formule, trous):
    """Remplit les trous d'une formule. -> texte, ou None si un trou manque, est vide ou dépasse 4 mots (le reste de la formule n'est jamais modifié)."""
    vals = {}
    for n in TROU.findall(formule):
        v = " ".join(str((trous if isinstance(trous, dict) else {}).get(n) or "").split()).strip(" .,;:!?«»\"'")
        if not v or len(v.split()) > 4 or "{" in v or "}" in v: return None
        vals[n] = v
    texte = TROU.sub(lambda m: vals[m.group(1)], formule)
    return texte[:1].upper() + texte[1:]


def demander_accroches(ollama, doc, serie, conf, regles, recentes=(), graine=""):
    """3 accroches tirées des formules de la ligne : Qwen choisit les formules et remplit les trous ; complétées par des formules sans trou (jamais inventées).
    -> [(texte, id de formule)]"""
    l = conf["lignes"][serie]; liste = formules(serie)
    if not liste: return []
    consignes = SYSTEME.format(ton=l.get("ton") or "simple", grille=C.section(regles, "Grille des accroches"), regles=C.section(regles, "Règles pour Qwen"))
    demande = (f"Ligne : {l.get('nom') or serie}. Sujet de la vidéo : {doc.get('sujet')}. Script : {' '.join(doc.get('scenes', [])[:-1])}\n"
               "Formules écrites à la main (à remplir, jamais à modifier) :\n" + "\n".join(f"{i} : {f}" for i, f in liste) + f"\n{trous_aide(serie)}\n"
               "Choisis exactement trois formules différentes, celles qui collent le mieux au sujet, et remplis chacun de leurs trous avec un à quatre mots "
               f"tirés du sujet, {'en tutoyant' if l.get('tutoiement') else 'en vouvoyant'}. Ne change aucun autre mot, n'écris aucune autre phrase, aucun chiffre. "
               'Une formule sans trou se choisit avec "trous": {}. Format : {"choix": [{"id": "...", "trous": {"nom_du_trou": "..."}}, ...]}')
    choix = []
    try:
        r = json.loads(ollama.chat(consignes, demande, temperature=0.7, num_predict=300))
        choix = r.get("choix") if isinstance(r, dict) and isinstance(r.get("choix"), list) else []
    except (ValueError, KeyError): pass
    par_id, out = dict(liste), []
    for c in choix:
        if not isinstance(c, dict): continue
        i = str(c.get("id") or "").strip().upper()
        if i not in par_id or any(i == x for _, x in out): continue
        texte = remplir(par_id[i], c.get("trous"))
        if texte: out.append((texte, i))
        if len(out) == 3: return out
    sans_trou = [(f, i) for i, f in liste if not TROU.search(f) and all(i != x for _, x in out)]
    random.Random(graine).shuffle(sans_trou)
    sans_trou.sort(key=lambda x: x[0] in recentes)   # les formules déjà utilisées récemment passent en dernier
    return out + sans_trou[:3 - len(out)]


def retravailler(doc, conf, ollama, regles, a_blanc=False):
    """Réécrit accroche, rythme et sous-titres d'un script (dict). -> doc modifié (champ « marketing »), ou None si aucune accroche valable."""
    serie = doc.get("serie", "A"); nom = f"{doc['jour']}-{doc['passage'].replace(':', '')}"
    recentes = recentes_du_journal()
    if doc.get("histoire"):   # ligne B : histoire écrite à la main, accroche comprise ; ni Qwen, ni découpe (le jeu de scène suit chaque réplique)
        best = doc["scenes"][0]; note, raisons = noter_accroche(best, serie, conf, recentes)
        sketch = doc.get("format") == "sketch"   # sketch à deux (17/11/2026) : la 1re réplique est un dialogue (vouvoiement possible), vérifiée par sketches.py
        formule = doc.get("formule") or f"histoire {doc['histoire']}"
        if note == 0 and not sketch:
            C.journal(AGENT, "erreur", f"{nom} : accroche de l'histoire {doc['histoire']} refusée ({'; '.join(raisons)})", a_blanc); return None
        d = duree_estimee(doc["scenes"])
        doc["sous_titres"] = [C.decouper_sous_titres(s, maxi=3, mini=1, car_max=16) if sketch else C.decouper_sous_titres(s) for s in doc["scenes"]]
        doc["marketing"] = {"accroches": [{"texte": best, "formule": formule, "note": note, "raisons": raisons}], "gardee": best,
                            "formule": formule, "phrases_coupees": 0, "duree_estimee_s": d,
                            "duree_ok": conf["duree_min_s"] <= d <= conf["duree_max_s"], "fait_le": f"{datetime.now():%Y-%m-%d %H:%M}"}
        C.csv_ligne(AGENT, nom, serie, conf["lignes"][serie].get("compte", ""), "accroche choisie", best,
                    (f"sketch {doc['sketch']} ({doc.get('variante', 'code')})" if sketch else f"histoire {doc['histoire']} ({doc.get('variante', 'original')}, {doc.get('structure', 'classique')})")
                    + f" ; note {note}/10 ; durée estimée {d} s", a_blanc, histoire=doc["histoire"], formule=formule, theme=doc.get("theme", ""), fin=doc.get("fin_variante", ""))
        return doc
    proposees = demander_accroches(ollama, doc, serie, conf, regles, recentes, nom)
    origine = {t: i for t, i in proposees}
    candidates = [t for t, _ in proposees]
    if serie == "B" and conf["lignes"]["B"].get("brouillon_hook"):
        brouillon = re.split(r"(?<=[?.!])\s", conf["lignes"]["B"]["brouillon_hook"].strip())[0]   # brouillon de Liam : sa première phrase concourt aussi
        if brouillon not in candidates: candidates.append(brouillon); origine[brouillon] = "brouillon de Liam"
    best, notes = choisir(candidates, serie, conf, recentes)
    if not best:   # aucune accroche de Qwen ne passe : la première phrase du script est gardée si elle passe la grille
        best, notes2 = choisir([doc["scenes"][0]], serie, conf, ()); notes += notes2
    if not best:
        C.journal(AGENT, "erreur", f"{nom} : aucune accroche valable ({len(notes)} notée(s))", a_blanc)
        C.csv_ligne(AGENT, nom, serie, conf["lignes"][serie].get("compte", ""), "aucune accroche valable", "", "; ".join(f"{t} = {n}" for t, n, _ in notes), a_blanc)
        return None
    corps = [best] + doc["scenes"][1:-1]
    rythme = [morceau for p in corps for morceau in couper(p)]
    scenes = rythme + [doc["scenes"][-1]]
    d = duree_estimee(scenes)
    # accroche écran = accroche parlée (même texte à l'écran et à l'oral) si elle a 7 mots au plus ; sinon la plus courte des accroches valables ;
    # l'accroche du script ne reste que si aucune ne convient et qu'elle passe les garde-fous
    courtes = sorted((t for t, n, _ in notes if n > 0 and mots(t) <= 7), key=lambda t: (t != best, mots(t)))
    if courtes: doc["accroche"] = courtes[0].rstrip(".")
    elif elimine(doc.get("accroche", ""), serie, conf) or mots(doc.get("accroche", "")) > 6: doc["accroche"] = best.rstrip(".")
    doc["scenes"] = scenes; doc["mots"] = sum(mots(s) for s in scenes)
    doc["sous_titres"] = [C.decouper_sous_titres(s) for s in scenes]
    doc["marketing"] = {"accroches": [{"texte": t, "formule": origine.get(t, "script"), "note": n, "raisons": r} for t, n, r in notes], "gardee": best,
                        "formule": origine.get(best, "script"), "phrases_coupees": len(rythme) - len(corps),
                        "duree_estimee_s": d, "duree_ok": conf["duree_min_s"] <= d <= conf["duree_max_s"], "fait_le": f"{datetime.now():%Y-%m-%d %H:%M}"}
    meilleure_note = max(n for t, n, _ in notes if t == best)
    C.csv_ligne(AGENT, nom, serie, conf["lignes"][serie].get("compte", ""), "accroche choisie", best,
                f"formule {origine.get(best, 'script')} ; note {meilleure_note}/10 ; autres : " + " | ".join(f"{t} = {n}" for t, n, _ in notes if t != best) + f" ; durée estimée {d} s", a_blanc,
                formule=origine.get(best, "script"), theme=doc.get("angle", ""))
    return doc


def traiter(conf, jour, heures, ollama_cls=C.Ollama, a_blanc=False):
    a_faire = []
    for h in heures:
        f = C.SCRIPTS / f"{jour}-{h.replace(':', '')}.json"
        if not f.exists(): print(f"  {h} : pas de script (videos-scripts doit passer avant)"); continue
        doc = json.loads(f.read_text(encoding="utf-8"))
        if doc.get("marketing"): print(f"  {h} : déjà retravaillé"); continue
        a_faire.append((f, doc))
    if not a_faire: print(f"Marketing du {jour} : rien à faire."); return 0
    regles = C.regles(); faits = 0
    with ollama_cls(conf["modele"]) as o:
        for f, doc in a_faire:
            nouveau = retravailler(doc, conf, o, regles, a_blanc)
            if not nouveau: print(f"  ! {doc['passage']} : aucune accroche valable, script laissé tel quel"); continue
            m = nouveau["marketing"]
            if a_blanc: print(f"[à blanc] {doc['passage']} : accroche « {m['gardee']} », {len(nouveau['scenes'])} phrases, ~{m['duree_estimee_s']} s ; rien écrit"); faits += 1; continue
            f.write_text(json.dumps(nouveau, ensure_ascii=False, indent=1), encoding="utf-8")
            C.journal(AGENT, "accroche", f"{f.stem} : « {m['gardee']} », ~{m['duree_estimee_s']} s" + ("" if m["duree_ok"] else " (durée hors plage)"))
            print(f"  {doc['passage']} : « {m['gardee']} » (~{m['duree_estimee_s']} s)"); faits += 1
    print(f"Marketing du {jour} : {faits}/{len(a_faire)} script(s) retravaillé(s).")
    return 0 if faits == len(a_faire) else 2


def cmd_etat(jour):
    docs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(C.SCRIPTS.glob(f"{jour}-*.json"))] if C.SCRIPTS.exists() else []
    print(f"{sum(bool(d.get('marketing')) for d in docs)}/{len(docs)} script(s) du {jour} retravaillé(s) ; {len(recentes_du_journal(1000))} accroche(s) au journal"); return 0


def main(argv=None):
    a = argparse.ArgumentParser(prog="videos-marketing"); sp = a.add_subparsers(dest="cmd", required=True)
    for n in ("jour", "passage"):
        p = sp.add_parser(n); p.add_argument("--a-blanc", action="store_true"); p.add_argument("--jour")
    sp.choices["passage"].add_argument("--heure", required=True)
    sp.add_parser("etat")
    a = a.parse_args(argv); jour = getattr(a, "jour", None) or f"{C.heure_paris():%Y-%m-%d}"
    if a.cmd == "etat": return cmd_etat(jour)
    C.exiger(AGENT, a.cmd, a.a_blanc); C.exiger_regles(AGENT, a.a_blanc); conf = C.cfg()
    return traiter(conf, jour, conf["passages"] if a.cmd == "jour" else [a.heure], a_blanc=a.a_blanc)


if __name__ == "__main__":
    sys.exit(main())
