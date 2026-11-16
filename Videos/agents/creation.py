#!/usr/bin/env python3
"""Agent videos-creation (équipe Vidéos TikTok, 16/11/2026) : fabrique la vidéo d'un passage (06:00, 14:00, 22:00) à partir du script écrit par videos-scripts.
Règles relues avant chaque exécution : Videos\\SKILL-VIDEOS.md. Outil retenu : stickfigure-pipeline-v2 (Videos\\outils, hors git ; stick-stage plante sous Windows, voir Videos\\README.md). L'outil fait la voix (edge-tts, gratuite),
les dessins (bonhomme bâton, fond sombre) et le montage ; cet agent ajoute ensuite avec ffmpeg : sous-titres mot à mot (2 à 4 mots, mot clé en jaune, zone sûre TikTok ; temps des mots par edge-tts), accroche à l'écran pendant les 2 premières secondes,
mention « Contenu généré par IA » pendant toute la vidéo, et une carte de fin en français (la carte anglaise de l'outil n'est pas utilisée).
Sortie : Videos\\a-valider\\AAAA-MM-JJ-HHMM.mp4 + .txt (légende, avec la mention IA) + .json (métadonnées). RIEN n'est publié ici.
Un seul rendu à la fois (verrou), priorité « sous la normale » ; seul le processus lancé ici est arrêté en cas de délai dépassé.
  python Videos\\agents\\creation.py passage [--heure 06:00] [--jour AAAA-MM-JJ] [--a-blanc]
  python Videos\\agents\\creation.py etat"""
import argparse, json, os, re, shutil, subprocess, sys, time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import commun as C   # noqa: E402

AGENT = "videos-creation"
OUTIL = C.VIDEOS / "outils" / "stickfigure-pipeline-v2"
VERROU = C.VIDEOS / "creation.verrou"
DELAI_S = 25 * 60
FIN_S = 3.0
POLICE_SOURCE = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "arialbd.ttf"
POLICE = "police.ttf"   # copiée dans le dossier de travail : aucun chemin Windows (« C: ») à échapper dans le filtre ffmpeg
POLICE_ST_SOURCE = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "ariblk.ttf"   # Arial Black (sous-titres), sinon Arial gras
ACCENT_ASS = "&H00D7FF&"   # jaune (#FFD700, ordre BGR de l'ASS) : mot clé de chaque groupe
# Zone sûre TikTok 1080x1920 : sous-titres entre x = 120 et x = 880 (boutons à droite au-delà de 900), bas du texte à y = 1250 (interface du bas sous 1500)
ST_MARGE_G, ST_MARGE_D, ST_BAS, ST_TAILLE = 120, 200, 1250, 84
IA_Y = 1380   # mention « Contenu généré par IA » : au-dessus de l'interface du bas (y < 1500)


def fins(serie, conf):
    """Carte de fin. Ligne B : « À la commission » tant que taux_commission est vide (jamais de taux inventé), aucun lieu."""
    if serie != "B": return ["Réservez 15 minutes", "avec Liam", "Lien dans la description"]
    taux = conf["lignes"]["B"]["taux_commission"]
    return [f"Commission {taux}, sans fixe" if taux else "À la commission, sans fixe", "Liste et script fournis", "Postule : lien en bio"]


def passage_proche(maintenant):
    """Passage prévu le plus proche de l'heure actuelle (une tâche lancée à 06:02 traite 06:00)."""
    m = maintenant.hour * 60 + maintenant.minute
    return min(C.cfg()["passages"], key=lambda h: abs(int(h[:2]) * 60 + int(h[3:]) - m))


def nom_video(jour, heure): return f"{jour}-{heure.replace(':', '')}"


def entree_outil(doc, conf):
    """Fichier d'entrée de stickfigure-pipeline-v2 : narration seule (l'outil compose les dessins), portrait 9:16, fond sombre, voix française gratuite."""
    return {"title": nom_video(doc["jour"], doc["passage"]), "format": "portrait", "dark_mode": True, "voice": conf["voix"],
            "channel": "LM Multi-Services", "scenes": [{"narration": s} for s in doc["scenes"]]}


def echapper_texte(t):
    """Texte pour un fichier textfile= de drawtext (aucun échappement nécessaire dans un fichier, sauf le %)."""
    return t.replace("%", "\\%")


def filtre_final(serie, sans_sous_titres, conf=None):
    """filter_complex : [0] corps (sous-titres mot à mot + accroche 0-2,5 s + mention IA), [1] carte de fin (fond sombre, textes), concaténés avec leur son."""
    dt = lambda f, taille, y, extra="": (f"drawtext=fontfile={POLICE}:textfile={f}:fontsize={taille}:fontcolor=white:x=(w-text_w)/2:y={y}{extra}")
    corps = []
    if sans_sous_titres:
        corps.append("subtitles=sous-titres.ass:fontsdir=.")
    corps.append(dt("accroche.txt", 92, "h*0.16", ":box=1:boxcolor=black@0.65:boxborderw=28:enable='lt(t,2.5)'"))
    corps.append(dt("ia.txt", 34, str(IA_Y), ":fontcolor=white@0.8:box=1:boxcolor=black@0.35:boxborderw=8"))
    fin = [dt(f"fin{i}.txt", 70 if i < 2 else 52, f"h*{0.36 + 0.11 * i:.2f}") for i in range(len(fins(serie, conf or C.cfg())))]
    fin.append(dt("ia.txt", 34, str(IA_Y), ":fontcolor=white@0.8"))
    return (f"[0:v]{','.join(corps)},fps=30,format=yuv420p,setsar=1[v0];[1:v]{','.join(fin)},format=yuv420p,setsar=1[v1];"
            "[0:a]aresample=44100,aformat=channel_layouts=stereo[a0];[2:a]aformat=channel_layouts=stereo[a1];[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]")


def lancer(cmd, cwd, journal_fichier, delai=DELAI_S):
    """Lance une commande (priorité sous la normale, sans fenêtre), sortie dans un journal ; arrête SON arbre de processus si le délai est dépassé. -> (code, texte)."""
    drapeaux = (getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0)) if os.name == "nt" else 0
    env = dict(os.environ, PATH=C.chemin_complet(), PYTHONIOENCODING="utf-8")
    with open(journal_fichier, "w", encoding="utf-8", errors="replace") as f:
        p = subprocess.Popen(cmd, cwd=str(cwd), stdout=f, stderr=subprocess.STDOUT, env=env, creationflags=drapeaux)
        try: code = p.wait(timeout=delai)
        except subprocess.TimeoutExpired:
            if os.name == "nt": subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], capture_output=True)
            else: p.kill()
            code = -1
    return code, Path(journal_fichier).read_text(encoding="utf-8", errors="replace")


def duree(fichier):
    r = subprocess.run([C.executable("ffprobe"), "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(fichier)],
                       capture_output=True, text=True, env=dict(os.environ, PATH=C.chemin_complet()))
    try: return float(r.stdout.strip())
    except ValueError: return 0.0


# --- Sous-titres mot à mot ------------------------------------------------------------------------------------------
def temps_edge(phrase, voix):
    """Temps des mots d'une phrase donnés par edge-tts (WordBoundary : même voix et même texte que l'outil, gratuit). -> [(début_s, fin_s)] ou [] si impossible."""
    try:
        import asyncio, edge_tts
        async def lire():
            out = []
            async for c in edge_tts.Communicate(phrase, voix, boundary="WordBoundary").stream():
                if c.get("type") == "WordBoundary": out.append((c["offset"] / 1e7, (c["offset"] + c["duration"]) / 1e7))
            return out
        return asyncio.run(lire())
    except Exception: return []


def temps_mots(scenes, durees, voix="", edge=temps_edge):
    """Début et fin (s, temps de la vidéo) de chaque mot de chaque phrase. Les phrases se suivent sans blanc (narration = phrases bout à bout, scene_timings.json).
    Temps d'edge-tts recalés sur la durée réelle de la phrase ; si edge-tts ne répond pas ou ne compte pas les mêmes mots : mots répartis selon leur longueur."""
    t0, out = 0.0, []
    for phrase, d in zip(scenes, durees):
        ms = C.mots_de(phrase); b = edge(phrase, voix) if ms else []
        if b and len(b) == len(ms) and b[-1][1] > 0:
            k = min(1.0, d / b[-1][1]) if b[-1][1] > d else 1.0
            tm = [(t0 + a * k, t0 + min(z * k, d)) for a, z in b]
        else:
            poids = [len(m) + 2 for m in ms]; tot = sum(poids) or 1; utile = d * 0.94; x = d * 0.03; tm = []
            for p in poids: tm.append((t0 + x, t0 + x + utile * p / tot)); x += utile * p / tot
        out.append(tm); t0 += d
    return out


def ass_temps(s):
    s = max(0.0, s); return f"{int(s // 3600)}:{int(s % 3600 // 60):02d}:{s % 60:05.2f}"


def sous_titres_ass(doc, temps, police="Arial Black"):
    """Fichier .ass : groupes de 2 à 4 mots (plan de l'agent marketing, sinon calculé), mot clé en jaune, gros, contour noir épais, dans la zone sûre TikTok."""
    plan = doc.get("sous_titres") or [C.decouper_sous_titres(s) for s in doc["scenes"]]
    lignes = ["[Script Info]", "ScriptType: v4.00+", "PlayResX: 1080", "PlayResY: 1920", "WrapStyle: 0", "ScaledBorderAndShadow: yes", "",
              "[V4+ Styles]", "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
              "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
              f"Style: Mot,{police},{ST_TAILLE},&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,7,2,2,{ST_MARGE_G},{ST_MARGE_D},{1920 - ST_BAS},1", "",
              "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    for groupes, tm in zip(plan, temps):
        i = 0
        for g in groupes:
            n = len(g["mots"]); morceau = tm[i:i + n]
            if not morceau: break
            debut, fin = morceau[0][0], morceau[-1][1]
            texte = " ".join((f"{{\\c{ACCENT_ASS}}}{m}{{\\c&HFFFFFF&}}" if j == g.get("cle") else m).replace("\n", " ") for j, m in enumerate(g["mots"]))
            lignes.append(f"Dialogue: 0,{ass_temps(debut)},{ass_temps(max(fin, debut + 0.25))},Mot,,0,0,0,,{texte}")
            i += n
    return "\n".join(lignes) + "\n"


def durees_outil(n):
    """Durées réelles des phrases (scene_timings.json de l'outil) ; [] si illisible ou si le nombre ne correspond pas."""
    try: d = [float(x["duration"]) for x in json.loads((OUTIL / "output" / "audio" / "scene_timings.json").read_text(encoding="utf-8"))]
    except (OSError, ValueError, KeyError, TypeError): return []
    return d if len(d) == n else []


def prendre_verrou():
    try:
        if VERROU.exists() and time.time() - VERROU.stat().st_mtime > 3600: VERROU.unlink()   # verrou abandonné (plus d'une heure)
        fd = os.open(VERROU, os.O_CREAT | os.O_EXCL | os.O_WRONLY); os.write(fd, str(os.getpid()).encode()); os.close(fd); return True
    except FileExistsError: return False


def fabriquer(conf, jour, heure, a_blanc=False):
    """-> 0 vidéo faite (ou déjà faite), 2 pas de script, 1 échec."""
    nom = nom_video(jour, heure); script = C.SCRIPTS / f"{nom}.json"
    deja = [d / f"{nom}.mp4" for d in (C.A_VALIDER, C.PUBLIEES) if (d / f"{nom}.mp4").exists()]
    if deja: print(f"Vidéo {nom} déjà faite ({deja[0].parent.name})."); return 0
    if not script.exists():
        print(f"! Aucun script pour {jour} {heure} ({script.name}) : videos-scripts doit passer avant."); C.journal(AGENT, "erreur", f"{nom} : script absent", a_blanc); return 2
    doc = json.loads(script.read_text(encoding="utf-8"))
    if a_blanc:
        print(f"[à blanc] {nom} : série {doc['serie']}, « {doc['titre']} », {len(doc['scenes'])} phrases, {doc.get('mots')} mots ; outil {conf['outil']} ; rien rendu."); return 0
    if not (OUTIL / "scripts" / "run.js").exists(): print(f"! Outil absent : {OUTIL}"); C.journal(AGENT, "erreur", "outil stickfigure-pipeline-v2 absent"); return 1
    if not prendre_verrou(): print("Un autre rendu est en cours : ce passage est abandonné."); C.journal(AGENT, "occupé", nom); return 1
    t0 = time.time(); travail = C.TRAVAIL / nom
    try:
        shutil.rmtree(travail, ignore_errors=True)   # restes d'un passage précédent (un dossier ouvert ailleurs n'empêche pas le rendu)
        travail.mkdir(parents=True, exist_ok=True)
        entree = travail / "entree.json"; entree.write_text(json.dumps(entree_outil(doc, conf), ensure_ascii=False, indent=1), encoding="utf-8")
        for f in ("final/body.mp4", "audio/full_narration.srt", "audio/full_narration.ass", "audio/scene_timings.json"):   # jamais les fichiers d'un rendu précédent
            (OUTIL / "output" / f).unlink(missing_ok=True)
        code, sortie = lancer([C.executable("node"), "scripts/run.js", str(entree), "jarvis"], OUTIL, travail / "outil.log")
        corps = OUTIL / "output" / "final" / "body.mp4"
        if code != 0 or not corps.exists():
            C.journal(AGENT, "erreur", f"{nom} : rendu de l'outil en échec (code {code})"); print(f"! Rendu en échec (code {code}), voir {travail / 'outil.log'}"); return 1
        # Les sous-titres incrustés par l'outil sont invisibles (MarginV=320 pour une hauteur de référence de 288 : hors du cadre) : on incruste toujours les nôtres,
        # mot à mot (temps edge-tts recalés sur la durée réelle de chaque phrase, scene_timings.json de l'outil).
        durees = durees_outil(len(doc["scenes"]))
        if not durees: C.journal(AGENT, "erreur", f"{nom} : durées des phrases introuvables (scene_timings.json)"); print("! Durées des phrases introuvables."); return 1
        temps = temps_mots(doc["scenes"], durees, conf["voix"])
        sans_st = True
        shutil.copy2(corps, travail / "corps.mp4"); shutil.copy2(POLICE_SOURCE, travail / POLICE)
        police_st = "Arial Black" if POLICE_ST_SOURCE.exists() else "Arial"
        if POLICE_ST_SOURCE.exists(): shutil.copy2(POLICE_ST_SOURCE, travail / POLICE_ST_SOURCE.name)
        (travail / "sous-titres.ass").write_text(sous_titres_ass(doc, temps, police_st), encoding="utf-8")
        textes = {"accroche.txt": doc["accroche"], "ia.txt": "Contenu généré par IA"} | {f"fin{i}.txt": t for i, t in enumerate(fins(doc["serie"], conf))}
        for f, t in textes.items(): (travail / f).write_text(echapper_texte(t), encoding="utf-8")
        sortie_mp4 = travail / "final.mp4"
        cmd = [C.executable("ffmpeg"), "-y", "-v", "error", "-i", "corps.mp4", "-f", "lavfi", "-i", f"color=c=0x141414:s=1080x1920:r=30:d={FIN_S}",
               "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo:d={FIN_S}", "-filter_complex", filtre_final(doc["serie"], sans_st, conf),
               "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
               "-movflags", "+faststart", "final.mp4"]
        code, sortie = lancer(cmd, travail, travail / "ffmpeg.log", delai=10 * 60)
        if code != 0 or not sortie_mp4.exists():
            C.journal(AGENT, "erreur", f"{nom} : montage final ffmpeg en échec (code {code})"); print(f"! Montage final en échec : {sortie[-400:]}"); return 1
        d = duree(sortie_mp4)
        C.A_VALIDER.mkdir(parents=True, exist_ok=True)
        shutil.move(str(sortie_mp4), C.A_VALIDER / f"{nom}.mp4")
        (C.A_VALIDER / f"{nom}.txt").write_text(doc["legende"] + "\n", encoding="utf-8")
        meta = {k: doc.get(k) for k in ("jour", "passage", "serie", "sujet", "titre", "accroche")} | {
            "duree_s": round(d, 1), "duree_ok": conf["duree_min_s"] <= d <= conf["duree_max_s"], "marketing": bool(doc.get("marketing")), "hook": (doc.get("marketing") or {}).get("gardee") or doc["scenes"][0], "contenu_ia": True, "etiquette_ia_tiktok": True, "outil": conf["outil"], "voix": conf["voix"],
            "rendu_s": round(time.time() - t0), "cree_le": f"{datetime.now():%Y-%m-%d %H:%M}"}
        (C.A_VALIDER / f"{nom}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
        shutil.rmtree(travail, ignore_errors=True)
        plage = f"{conf['duree_min_s']}-{conf['duree_max_s']} s"
        C.journal(AGENT, "video", f"{nom} : {d:.1f} s, rendu en {meta['rendu_s']} s, série {doc['serie']}" + ("" if meta["duree_ok"] else f" (durée hors {plage})"))
        C.csv_ligne(AGENT, nom, doc["serie"], conf["lignes"][doc["serie"]].get("compte", ""), "à valider", (doc.get("marketing") or {}).get("gardee") or doc["scenes"][0], f"{d:.1f} s")
        print(f"Vidéo prête : {C.A_VALIDER / (nom + '.mp4')} ({d:.1f} s, rendu en {meta['rendu_s']} s)" + ("" if meta["duree_ok"] else f" ; ATTENTION durée hors {plage}"))
        return 0
    finally:
        try: VERROU.unlink()
        except OSError: pass


def cmd_etat():
    v = sorted(C.A_VALIDER.glob("*.mp4")) if C.A_VALIDER.exists() else []; p = sorted(C.PUBLIEES.glob("*.mp4")) if C.PUBLIEES.exists() else []
    print(f"{len(v)} vidéo(s) à valider" + (f" (dernière : {v[-1].name})" if v else "") + f" ; {len(p)} publiée(s)"); return 0


def main(argv=None):
    a = argparse.ArgumentParser(prog="videos-creation"); sp = a.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("passage"); p.add_argument("--heure"); p.add_argument("--jour"); p.add_argument("--a-blanc", action="store_true")
    sp.add_parser("etat")
    a = a.parse_args(argv)
    if a.cmd == "etat": return cmd_etat()
    C.exiger(AGENT, a.cmd, a.a_blanc); C.exiger_regles(AGENT, a.a_blanc)
    maintenant = C.heure_paris()
    heure = a.heure or passage_proche(maintenant)
    if not re.fullmatch(r"\d\d:\d\d", heure): print("--heure attendue au format HH:MM"); return 2
    return fabriquer(C.cfg(), a.jour or f"{maintenant:%Y-%m-%d}", heure, a.a_blanc)


if __name__ == "__main__":
    sys.exit(main())
