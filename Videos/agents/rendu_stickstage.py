#!/usr/bin/env python3
"""Rendu des vidéos avec stick-stage (tamtree-ai/stick-stage, licence MIT, cloné dans Videos\\outils\\stick-stage, hors git), style « toon » (17/11/2026).
Choisi après comparaison sur la même scène de 15 s (voir Videos\\README.md) : couleurs, vrai décor (bureau, librairie, café…), personnage articulé avec
expressions et bouche synchronisée, plusieurs plans (plan large, plan moyen, gros plan), coupes et transitions choisies par le réalisateur de l'outil.
Le script de la vidéo (une phrase = une réplique du narrateur) devient un « skit » : décor, Gérard (personnage toon versionné : Videos\\stick-stage\\gerard.json),
jeu de scène par phrase (expression + geste : donné par l'histoire, sinon déduit de la ponctuation), voix déjà faite (edge-tts, sinon Kokoro : agents\\voix.py).
Ligne B en sketch à deux (17/11/2026) : skit_dialogue = Gérard (à gauche) + l'interlocuteur (claire.json ou karim.json selon son genre, à droite), chacun dit
ses répliques avec sa voix (bouche synchronisée), bruitages du catalogue CC0 de stick-stage dans le skit, la fin dite par Gérard en gros plan, regard caméra.
Sortie : corps de la vidéo (mp4 avec la voix) + début de chaque réplique (pour les sous-titres mot à mot). Rien n'est publié ici."""
import json, os, re, shutil, subprocess, sys, wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import commun as C   # noqa: E402

OUTIL = C.VIDEOS / "outils" / "stick-stage"
RENDU_MTS = Path(__file__).resolve().parent / "stickstage-rendu.mts"
PERSONNAGES = C.VIDEOS / "stick-stage"
TSX = OUTIL / "node_modules" / "tsx" / "dist" / "cli.mjs"
DECORS = {"bureau": "office-1", "cabinet": "office-1", "boutique": "bookshop-morning", "librairie": "bookshop-morning", "cafe": "cafe-1", "café": "cafe-1",
          "cuisine": "kitchen-1", "salon": "living-1", "rue": "street-1", "parc": "park-1", "reunion": "meeting-1", "réunion": "meeting-1", "chambre": "bedroom-1",
          "salle": "classroom-1"}
try: DECORS.update(json.loads((C.VIDEOS / "troupe.json").read_text(encoding="utf-8"))["decors"])   # décors de jour de la troupe (boutique, atelier, attente…)
except (OSError, ValueError, KeyError): pass
ASSIS = {"office-1"}   # décors avec un siège sous la marque de gauche : Gérard y est assis au départ
EXPRESSIONS = set("neutral happy smug sarcastic annoyed angry shocked sad crying cringe confused deadpan skeptical worried embarrassed thinking laughing".split())
POSES = set("idle point shrug facepalm arms-up arms-crossed think lean-in recoil slump hands-on-hips hold-phone hold-out hold-chest hold-up high-five shove faint wave thumbs-up".split())
STYLES = {"classic", "deadpan", "snappy", "chaotic", "sitcom", "argument"}   # styles de réalisation de stick-stage
ROTATION = [("neutral", "hands-on-hips"), ("worried", "think"), ("happy", "point"), ("skeptical", "arms-crossed"), ("thinking", "shrug")]


def decor(nom):
    """Décor stick-stage d'un nom français (bureau, cabinet, boutique…) ou d'un id du catalogue. Inconnu = bureau."""
    n = (nom or "").strip().lower()
    if (OUTIL / "src" / "data" / "sets" / f"{n}.json").exists() or n in DECORS.values(): return n
    return DECORS.get(n, "office-1")


def jeu_par_defaut(phrase, i):
    """Expression et geste d'une phrase sans indication : question = perplexe, exclamation = surpris, sinon rotation (jamais deux fois le même geste de suite)."""
    if phrase.rstrip().endswith("?"): return ("confused", "think") if i % 2 else ("thinking", "shrug")
    if phrase.rstrip().endswith("!"): return ("shocked", "recoil") if i % 2 else ("happy", "arms-up")
    return ROTATION[i % len(ROTATION)]


def personnage(nom="gerard"):
    return json.loads((PERSONNAGES / f"{nom}.json").read_text(encoding="utf-8"))


def skit(doc, voix_textes, decor_id):
    """Document skit.json (schemaVersion 2, 9:16) : narrateur en voix off, Gérard à l'écran, une réplique par phrase avec son jeu de scène."""
    assis = decor_id in ASSIS
    jeu = doc.get("jeu") or []
    beats = []
    for i, ligne in enumerate(voix_textes):
        expr, pose = (jeu[i] if i < len(jeu) and jeu[i] else jeu_par_defaut(ligne, i))
        mots = C.mots_de(ligne); ancre = {"word": re.sub(r"[\s ?!.,:;…»]+$", "", mots[min(1, len(mots) - 1)])} if mots else {"ms": 0}
        actions = []
        if expr in EXPRESSIONS: actions.append({"who": "gerard", "do": "expression", "expression": expr, "at": ancre})
        if pose in POSES and not (assis and i == 0): actions.append({"who": "gerard", "do": "pose", "pose": pose, "at": ancre})
        b = {"id": f"n{i + 1}", "speaker": "narrator", "line": ligne, "focus": "gerard"}
        if actions: b["actions"] = actions
        if doc.get("punchline") == i: b["punchline"] = True
        beats.append(b)
    if doc.get("punchline") is None and len(beats) > 1: beats[-2]["punchline"] = True   # la chute, pas l'appel à l'action
    s = {"schemaVersion": 2, "meta": {"title": doc.get("titre") or "Vidéo", "aspect": "9:16"},
         "narrator": {"id": "narrator", "voice": {"say": "Thomas"}}, "characters": [personnage("gerard")], "set": decor_id,
         "cast": [{"id": "gerard", "character": "gerard", "mark": "left" if assis else "center", "seated": assis, "expression": "neutral"}],
         "overlay": {"subtitles": False}, "beats": beats}
    if doc.get("style") in STYLES: s["style"] = doc["style"]   # ligne B : « deadpan » (ton sec : pauses, réaction tenue, fondus)
    return s


INTERLOCUTEURS = {"f": "claire", "h": "karim"}
PAUSE_SONNERIE_MS = 1400   # silence avant une réplique qui suit une sonnerie (la sonnerie est mixée dans ce silence par le monteur)


PLAN_LONG_S = 2.8   # une réplique plus longue : plan moyen + zoom bref au milieu (jamais plus de 3 s sans changement d'image)


def plan_de(i, qui, duree_s, n_fin, avant=None, pause_s=0):
    """Cadrage imposé d'une réplique : plan à deux pour la 1re, puis gros plan / plan moyen sur celui qui parle (plan à deux toutes les 4 répliques) ;
    jamais le même cadrage que la réplique précédente (`avant`), donc une coupe à chaque réplique ; réplique longue : zoom bref au milieu.
    (La chute n'en reçoit pas : le réalisateur y met le gros plan d'émotion puis la réaction.)"""
    if i == 0: f = {"framing": "two"} if pause_s == 0 else {"framing": "medium", "on": qui}   # après une sonnerie : coupe sur celui qui parle (plan à deux pendant la sonnerie)
    elif i % 4 == 0 and i < n_fin: f = {"framing": "two"}
    else: f = {"framing": "close" if i % 2 else "medium", "on": qui}
    if duree_s + pause_s > PLAN_LONG_S and f["framing"] == "close": f = {"framing": "medium", "on": qui}
    if avant and (f["framing"], f.get("on")) == (avant.get("framing"), avant.get("on")):
        f = {"framing": "close" if f["framing"] != "close" else "medium", "on": qui}
    if duree_s + pause_s > PLAN_LONG_S:   # zoom au milieu du plan réel (silence de la sonnerie compris), jamais au tout début de la réplique
        fr = max(0.15, min(0.5, ((pause_s + duree_s) / 2 - pause_s) / duree_s)) if duree_s else 0.5
        f["punchIn"] = {"on": qui, "at": {"fraction": round(fr, 2)}}
    return f


def skit_dialogue(doc, decor_id, durees=None):
    """Skit d'un sketch à deux : doc["qui"] (G / I par réplique), doc["jeu"] (expression, geste de celui qui parle), doc["sfx"] (bruitage au début de la réplique),
    doc["fin_indices"] (répliques de fin : Gérard regarde la caméra, gros plan), doc["telephone"] (les deux tiennent un téléphone)."""
    i = doc.get("interlocuteur") or {}; assis = decor_id in ASSIS
    inter = i["personnage"] if i.get("personnage") and (PERSONNAGES / f"{i['personnage']}.json").exists() else INTERLOCUTEURS.get(i.get("genre"), "karim")
    qui = {"G": "gerard", "I": "inter"}; jeu = doc.get("jeu") or []; sfx = doc.get("sfx") or []; fin = set(doc.get("fin_indices") or [])
    beats, avant = [], None
    for i, ligne in enumerate(doc["scenes"]):
        who = qui[doc["qui"][i]]
        expr, pose = (jeu[i] if i < len(jeu) and jeu[i] else jeu_par_defaut(ligne, i))
        mots = C.mots_de(ligne); ancre = {"word": re.sub(r"[\s ?!.,:;…»«]+$", "", mots[min(1, len(mots) - 1)]).lstrip("«… ")} if mots else {"ms": 0}
        b = {"id": f"n{i + 1}", "speaker": who, "line": ligne}
        if expr in EXPRESSIONS: b["expression"] = expr
        actions = []
        if pose in POSES and not (assis and who == "gerard" and i == 0): actions.append({"who": who, "do": "pose", "pose": pose, "at": ancre})
        if i in fin:
            actions.insert(0, {"who": "gerard", "do": "look", "to": "camera", "at": {"ms": 0}})
            b["reaction"] = False
        if doc.get("punchline") != i:
            pause = (PAUSE_SONNERIE_MS / 1000 + (0.3 if i == 0 else 0)) if (sfx[i] if i < len(sfx) else None) == "sonnerie" else 0   # le plan court aussi pendant la sonnerie (+ 0,3 s d'ouverture)
            b["shot"] = plan_de(i, who, (durees or [0] * len(doc["scenes"]))[i], min(fin) if fin else len(doc["scenes"]), avant, pause)
        avant = b.get("shot") or {"framing": "extreme"}   # après la chute : le réalisateur finit sur un très gros plan de réaction
        if actions: b["actions"] = actions
        s = sfx[i] if i < len(sfx) else None
        if s == "sonnerie": b["pauseBeforeMs"] = PAUSE_SONNERIE_MS
        elif s: b["sfx"] = [{"id": s, "at": {"ms": 0}, "volume": 0.9}]
        if doc.get("punchline") == i: b["punchline"] = True
        beats.append(b)
    tel = {"holding": {"prop": "phone"}} if doc.get("telephone") else {}
    cast = [{"id": "gerard", "character": "gerard", "mark": "left", "seated": assis, "expression": "neutral"} | tel,
            {"id": "inter", "character": inter, "mark": "right", "expression": "neutral"} | tel]
    s = {"schemaVersion": 2, "meta": {"title": doc.get("titre") or "Sketch", "aspect": "9:16"}, "characters": [personnage("gerard"), personnage(inter)],
         "set": decor_id, "cast": cast, "overlay": {"subtitles": False}, "beats": beats}
    if doc.get("style") in STYLES: s["style"] = doc["style"]
    return s


def installer_decors():
    """Décors de la troupe (Videos/stick-stage/decors) enregistrés dans stick-stage s'ils manquent (Videos/correctifs/stick-stage-decors.py, idempotent)."""
    import importlib.util
    s = importlib.util.spec_from_file_location("stick_stage_decors", C.VIDEOS / "correctifs" / "stick-stage-decors.py")
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    _, manquants = m.installer(OUTIL)
    if manquants: raise RuntimeError(f"décors de la troupe non installés : {'; '.join(manquants)}")


def _wav_duree(f):
    with wave.open(str(f), "rb") as w: return w.getnframes() / float(w.getframerate())


def preparer(skit_id, doc, phrases, dossier_voix, decor_id):
    """Écrit public/skits/<skit_id>/ : skit.json, voice/nN.wav (depuis les mp3 de voix.py), voice.json. -> dossier."""
    d = OUTIL / "public" / "skits" / skit_id
    shutil.rmtree(d, ignore_errors=True); (d / "voice").mkdir(parents=True)
    lignes = []; dialogue = bool(doc.get("qui"))
    for i, texte in enumerate(phrases):
        wav = d / "voice" / f"n{i + 1}.wav"
        subprocess.run([C.executable("ffmpeg"), "-v", "error", "-y", "-i", str(Path(dossier_voix) / f"scene_{i + 1:03d}.mp3"), "-ar", "44100", "-ac", "1", str(wav)],
                       check=True, capture_output=True, env={**os.environ, "PATH": C.chemin_complet()})
        lignes.append({"id": f"n{i + 1}", "speaker": ({"G": "gerard", "I": "inter"}[doc["qui"][i]] if dialogue else "narrator"), "text": texte, "audio": f"voice/n{i + 1}.wav", "durationMs": round(_wav_duree(wav) * 1000)})
    (d / "skit.json").write_text(json.dumps(skit_dialogue(doc, decor_id, [l["durationMs"] / 1000 for l in lignes]) if dialogue else skit(doc, phrases, decor_id), ensure_ascii=False, indent=1), encoding="utf-8")
    (d / "voice.json").write_text(json.dumps({"schemaVersion": 1, "lines": lignes}, ensure_ascii=False, indent=1), encoding="utf-8")
    return d


def debuts_repliques(dossier_skit, n):
    """Début (s) de chaque réplique dans la vidéo rendue, lu dans generated/timeline.json (le réalisateur ajoute des pauses entre les répliques)."""
    t = json.loads((Path(dossier_skit) / "generated" / "timeline.json").read_text(encoding="utf-8"))
    fps, debuts = t["fps"], {}
    for s in t["scenes"]:
        for a in s["timeline"]["audio"]: debuts[a["beatId"]] = (s["from"] + a["frame"]) / fps
    return [debuts[f"n{i + 1}"] for i in range(n)]


def rendre(doc, phrases, dossier_voix, travail, lancer, nom, decor_nom="", retoucher=None, avec_timeline=False):
    """Rend le corps de la vidéo. lancer(cmd, cwd, journal) -> (code, texte) (creation.lancer : priorité basse, délai, arbre arrêté).
    retoucher(dossier_skit) -> True si le skit a été modifié (monteur : plans de 3 s au plus) : appelé après la compilation, puis recompilation (3 fois au plus).
    -> (mp4, débuts des répliques en s, durées des répliques en s[, timeline]). Lève RuntimeError en cas d'échec. Le skit temporaire est toujours supprimé."""
    if not TSX.exists(): raise RuntimeError(f"stick-stage absent ou incomplet ({OUTIL})")
    skit_id = f"jarvis-{nom}"; decor_id = decor(decor_nom or doc.get("decor"))
    d = preparer(skit_id, doc, phrases, dossier_voix, decor_id)
    try:
        installer_decors()
        node = C.executable("node")
        code, sortie = lancer([node, str(TSX), "scripts/prep.ts", skit_id], OUTIL, Path(travail) / "stickstage-prep.log")
        if code != 0: raise RuntimeError(f"préparation stick-stage en échec (code {code}) : {sortie[-300:]}")
        code, sortie = lancer([node, str(TSX), "scripts/compile.ts", skit_id], OUTIL, Path(travail) / "stickstage-compile.log")   # écrit generated/timeline.json
        if code != 0: raise RuntimeError(f"skit refusé par stick-stage (code {code}) : {sortie[-300:]}")
        for _ in range(4 if retoucher else 0):
            if not retoucher(d): break
            code, sortie = lancer([node, str(TSX), "scripts/compile.ts", skit_id], OUTIL, Path(travail) / "stickstage-compile.log")
            if code != 0: raise RuntimeError(f"skit retouché refusé par stick-stage (code {code}) : {sortie[-300:]}")
        mp4 = Path(travail) / "corps-stickstage.mp4"
        code, sortie = lancer([node, str(TSX), str(RENDU_MTS), skit_id, str(mp4)], OUTIL, Path(travail) / "stickstage-rendu.log")
        if code != 0 or not mp4.exists(): raise RuntimeError(f"rendu stick-stage en échec (code {code}) : {sortie[-300:]}")
        durees = [l["durationMs"] / 1000 for l in json.loads((d / "voice.json").read_text(encoding="utf-8"))["lines"]]
        res = (mp4, debuts_repliques(d, len(phrases)), durees)
        return res + (json.loads((d / "generated" / "timeline.json").read_text(encoding="utf-8")),) if avec_timeline else res
    finally:
        shutil.rmtree(d, ignore_errors=True)
