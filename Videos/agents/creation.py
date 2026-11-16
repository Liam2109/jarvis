#!/usr/bin/env python3
"""Agent videos-creation (équipe Vidéos TikTok, 16/11/2026) : fabrique la vidéo d'un passage (06:00, 14:00, 22:00) à partir du script écrit par videos-scripts.
Règles relues avant chaque exécution : Videos\\SKILL-VIDEOS.md. Outil de rendu (config « outil ») : stick-stage en style toon depuis le 17/11/2026
(agents/rendu_stickstage.py : couleurs, vrai décor, Gérard articulé, plusieurs plans et transitions ; comparaison dans Videos\\README.md), ou l'ancien
stickfigure-pipeline-v2 (fond sombre) si « outil » vaut « stickfigure-pipeline-v2 ». La voix est faite ici avant le rendu (agents/voix.py : edge-tts, bascule automatique
sur Kokoro local s'il échoue ; voix fixe par ligne ; moteur noté dans journal-videos.csv, colonne tts) et reprise par l'outil, qui fait les dessins (bonhomme bâton, fond sombre) et le montage ; cet agent ajoute ensuite avec ffmpeg : sous-titres mot à mot (2 à 4 mots, mot clé en jaune, zone sûre TikTok ; temps des mots par edge-tts), accroche à l'écran pendant les 2 premières secondes,
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
import voix as VX    # noqa: E402  (edge-tts, bascule Kokoro local)
import rendu_stickstage as RS   # noqa: E402  (rendu toon en couleurs)
import monteur as MT   # noqa: E402  (ligne B, sketch à deux : plans, musique, bruitages, contrôle qualité)

AGENT = "videos-creation"
OUTIL = C.VIDEOS / "outils" / "stickfigure-pipeline-v2"
VERROU = C.VIDEOS / "creation.verrou"
DELAI_S = 25 * 60
FIN_S = 3.0
FIN_S_B = 2.0   # ligne B : l'appel à l'action est déjà dit à voix haute, la carte le rappelle 2 s (vidéo de 35 s au plus)


def fin_s(serie): return FIN_S_B if serie == "B" else FIN_S
FOND_FIN = "0x1F4E79"   # carte de fin bleu nuit : jamais de fond noir plein
POLICE_SOURCE = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "arialbd.ttf"
POLICE = "police.ttf"   # copiée dans le dossier de travail : aucun chemin Windows (« C: ») à échapper dans le filtre ffmpeg
POLICE_ST_SOURCE = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "ariblk.ttf"   # Arial Black (sous-titres), sinon Arial gras
ACCENT_ASS = "&H00D7FF&"   # jaune (#FFD700, ordre BGR de l'ASS) : mot clé de chaque groupe
# Zone sûre TikTok 1080x1920 : sous-titres entre x = 120 et x = 880 (boutons à droite au-delà de 900), bas du texte à y = 1250 (interface du bas sous 1500)
ST_MARGE_G, ST_MARGE_D, ST_BAS, ST_TAILLE = 120, 200, 1250, 84
IA_Y = 1380   # mention « Contenu généré par IA » : au-dessus de l'interface du bas (y < 1500)


def fins(serie, conf):
    """Carte de fin. Ligne A : une page à son nom, lien dans la description (jamais de rendez-vous de 15 minutes, aucune promesse).
    Ligne B : on recrute des call callers à la commission (taux seulement s'il est dans la config), formulaire en bio ou DM ; aucun lieu."""
    if serie != "B": return ["Une page à votre nom ?", "Parlons-en", "Lien dans la description"]
    taux = conf["lignes"]["B"]["taux_commission"]
    return ["On recrute des call callers", f"À la commission ({taux})" if taux else "À la commission", "Formulaire en bio ou DM"]


def passage_proche(maintenant):
    """Passage prévu le plus proche de l'heure actuelle (une tâche lancée à 06:02 traite 06:00)."""
    m = maintenant.hour * 60 + maintenant.minute
    return min(C.cfg()["passages"], key=lambda h: abs(int(h[:2]) * 60 + int(h[3:]) - m))


def nom_video(jour, heure): return f"{jour}-{heure.replace(':', '')}"


def entree_outil(doc, conf, audio=None):
    """Fichier d'entrée de stickfigure-pipeline-v2 : narration seule (l'outil compose les dessins), portrait 9:16, fond sombre, voix de la ligne.
    audio : dossier des scene_NNN.mp3 déjà faits (voix.synthese) que l'outil reprend tels quels (reuse_audio_from)."""
    e = {"title": nom_video(doc["jour"], doc["passage"]), "format": "portrait", "dark_mode": True, "voice": VX.voix_ligne(conf, doc.get("serie", "A"))["edge"],
         "channel": "LM Multi-Services", "scenes": [{"narration": s} for s in doc["scenes"]]}
    if audio: e["reuse_audio_from"] = str(audio)
    return e


def echapper_texte(t):
    """Texte pour un fichier textfile= de drawtext (aucun échappement nécessaire dans un fichier, sauf le %)."""
    return t.replace("%", "\\%")


ACCROCHE_LARGEUR = 900 - 120 - 2 * 28   # zone sûre TikTok (x de 120 à 900) moins le cadre noir de chaque côté


def accroche_ecran(texte, maxi=92, mini=44):
    """Accroche affichée les 2,5 premières secondes : une ligne, ou deux lignes équilibrées si elle est trop large, taille réduite pour tenir dans la zone sûre
    (largeur estimée à 0,6 x la taille par caractère en Arial gras ; drawtext ne coupe jamais seul). -> (texte, taille)"""
    t = re.sub(r"\s+([?!:;»])", " \\1", " ".join((texte or "").split()))   # « ? » jamais seul en début de ligne
    lignes = [t]
    if len(t) * 0.6 * maxi > ACCROCHE_LARGEUR and " " in t:
        ms = t.split(" ")
        i = min(range(1, len(ms)), key=lambda k: max(len(" ".join(ms[:k])), len(" ".join(ms[k:]))))
        lignes = [" ".join(ms[:i]), " ".join(ms[i:])]
    n = max(len(l) for l in lignes) or 1
    return "\n".join(lignes), max(mini, min(maxi, int(ACCROCHE_LARGEUR / (0.6 * n))))


def filtre_final(serie, sans_sous_titres, conf=None, taille_accroche=92):
    """filter_complex : [0] corps (sous-titres mot à mot + accroche 0-2,5 s + mention IA), [1] carte de fin (fond sombre, textes), concaténés avec leur son."""
    dt = lambda f, taille, y, extra="", x="(w-text_w)/2": (f"drawtext=fontfile={POLICE}:textfile={f}:fontsize={taille}:fontcolor=white:x={x}:y={y}{extra}")
    corps = []
    if sans_sous_titres:
        corps.append("subtitles=sous-titres.ass:fontsdir=.")
    corps.append(dt("accroche.txt", taille_accroche, "h*0.16", ":line_spacing=14:box=1:boxcolor=black@0.65:boxborderw=28:enable='lt(t,2.5)'", x="(1020-text_w)/2"))   # centrée dans la zone sûre (x de 120 à 900)
    corps.append(dt("ia.txt", 34, str(IA_Y), ":fontcolor=white@0.8:box=1:boxcolor=black@0.35:boxborderw=8"))
    fin = [dt(f"fin{i}.txt", 70 if i < 2 else 52, f"h*{0.36 + 0.11 * i:.2f}") for i in range(len(fins(serie, conf or C.cfg())))]
    fin.append(dt("ia.txt", 34, str(IA_Y), ":fontcolor=white@0.8"))
    return (f"[0:v]{','.join(corps)},fps=30,format=yuv420p,setsar=1[v0];[1:v]{','.join(fin)},format=yuv420p,setsar=1[v1];"
            "[0:a]aresample=44100,aformat=channel_layouts=stereo[a0];[2:a]aformat=channel_layouts=stereo[a1];[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]")


def lancer(cmd, cwd, journal_fichier, delai=DELAI_S, chemin=None):
    """Lance une commande (priorité sous la normale, sans fenêtre), sortie dans un journal ; arrête SON arbre de processus si le délai est dépassé. -> (code, texte)."""
    drapeaux = (getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0)) if os.name == "nt" else 0
    env = dict(os.environ, PATH=chemin or C.chemin_complet(), PYTHONIOENCODING="utf-8")
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


def temps_mots(scenes, durees, voix="", edge=temps_edge, debuts=None):
    """Début et fin (s, temps de la vidéo) de chaque mot de chaque phrase. debuts : début réel de chaque phrase (stick-stage ajoute des pauses) ;
    sans debuts, les phrases se suivent sans blanc (stickfigure-pipeline-v2 : narration = phrases bout à bout, scene_timings.json).
    Temps d'edge-tts recalés sur la durée réelle de la phrase ; si edge-tts ne répond pas ou ne compte pas les mêmes mots : mots répartis selon leur longueur."""
    t0, out = 0.0, []
    for n, (phrase, d) in enumerate(zip(scenes, durees)):
        if debuts: t0 = debuts[n]
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
    stickstage = conf["outil"] == "stick-stage"
    if not (RS.TSX.exists() if stickstage else (OUTIL / "scripts" / "run.js").exists()):
        print(f"! Outil absent : {RS.OUTIL if stickstage else OUTIL}"); C.journal(AGENT, "erreur", f"outil {conf['outil']} absent"); return 1
    if not prendre_verrou(): print("Un autre rendu est en cours : ce passage est abandonné."); C.journal(AGENT, "occupé", nom); return 1
    t0 = time.time(); travail = C.TRAVAIL / nom
    try:
        shutil.rmtree(travail, ignore_errors=True)   # restes d'un passage précédent (un dossier ouvert ailleurs n'empêche pas le rendu)
        travail.mkdir(parents=True, exist_ok=True)
        # Voix d'abord (edge-tts, sinon Kokoro local) : l'outil reprend ces fichiers ; edge-tts est retiré de son PATH pour qu'il ne refasse pas la voix.
        sketch = doc.get("format") == "sketch"
        voix_doc = [VX.voix_dialogue(conf, doc["interlocuteur"]["genre"])[q] for q in doc["qui"]] if sketch else VX.voix_ligne(conf, doc["serie"])
        try: voix = VX.synthese(doc["scenes"], voix_doc, travail / "voix")
        except RuntimeError as e: C.journal(AGENT, "erreur", f"{nom} : {e}"); print(f"! Voix impossible : {e}"); return 1
        if voix["bascule"]: C.journal(AGENT, "bascule voix", f"{nom} : {voix['bascule']} -> Kokoro local"); print(f"  voix : {voix['bascule']}, bascule sur Kokoro local")
        print(f"  voix : {voix['moteur']} ({voix['duree_s']} s)")
        if sketch:   # sketch à deux : l'agent monteur fait tout le reste (plans, son, sous-titres, contrôle qualité, 2 reprises, mise à part)
            return finir_sketch(conf, doc, nom, travail, voix, t0)
        debuts = None
        if stickstage:   # skit stick-stage (toon, décor, plans) ; début réel de chaque réplique lu dans sa timeline
            try: corps, debuts, durees = RS.rendre(doc, doc["scenes"], travail / "voix", travail, lancer, nom)
            except RuntimeError as e: C.journal(AGENT, "erreur", f"{nom} : {e}"[:300]); print(f"! Rendu stick-stage en échec : {e}"); return 1
        else:
            entree = travail / "entree.json"; entree.write_text(json.dumps(entree_outil(doc, conf, travail / "voix"), ensure_ascii=False, indent=1), encoding="utf-8")
            for f in ("final/body.mp4", "audio/full_narration.srt", "audio/full_narration.ass", "audio/scene_timings.json"):   # jamais les fichiers d'un rendu précédent
                (OUTIL / "output" / f).unlink(missing_ok=True)
            code, sortie = lancer([C.executable("node"), "scripts/run.js", str(entree), "jarvis"], OUTIL, travail / "outil.log", chemin=VX.chemin_sans_edge(C.chemin_complet()))
            corps = OUTIL / "output" / "final" / "body.mp4"
            if code != 0 or not corps.exists():
                C.journal(AGENT, "erreur", f"{nom} : rendu de l'outil en échec (code {code})"); print(f"! Rendu en échec (code {code}), voir {travail / 'outil.log'}"); return 1
            # Les sous-titres de l'outil sont invisibles (hors du cadre) : on incruste toujours les nôtres, mot à mot (scene_timings.json de l'outil).
            durees = durees_outil(len(doc["scenes"]))
            if not durees: C.journal(AGENT, "erreur", f"{nom} : durées des phrases introuvables (scene_timings.json)"); print("! Durées des phrases introuvables."); return 1
        deja_temps = dict(zip(doc["scenes"], voix["temps"] or []))   # temps des mots donnés par edge-tts pendant la synthèse ; Kokoro : répartis selon la longueur
        temps = temps_mots(doc["scenes"], durees, edge=lambda p, v: deja_temps.get(p, []), debuts=debuts)
        sans_st = True
        shutil.copy2(corps, travail / "corps.mp4"); shutil.copy2(POLICE_SOURCE, travail / POLICE)
        police_st = "Arial Black" if POLICE_ST_SOURCE.exists() else "Arial"
        if POLICE_ST_SOURCE.exists(): shutil.copy2(POLICE_ST_SOURCE, travail / POLICE_ST_SOURCE.name)
        (travail / "sous-titres.ass").write_text(sous_titres_ass(doc, temps, police_st), encoding="utf-8")
        accroche, taille_accroche = accroche_ecran(doc["accroche"])
        textes = {"accroche.txt": accroche, "ia.txt": "Contenu généré par IA"} | {f"fin{i}.txt": t for i, t in enumerate(fins(doc["serie"], conf))}
        for f, t in textes.items(): (travail / f).write_text(echapper_texte(t), encoding="utf-8")
        sortie_mp4 = travail / "final.mp4"
        cmd = [C.executable("ffmpeg"), "-y", "-v", "error", "-i", "corps.mp4", "-f", "lavfi", "-i", f"color=c={FOND_FIN}:s=1080x1920:r=30:d={fin_s(doc['serie'])}",
               "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo:d={fin_s(doc['serie'])}", "-filter_complex", filtre_final(doc["serie"], sans_st, conf, taille_accroche),
               "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
               "-movflags", "+faststart", "final.mp4"]
        code, sortie = lancer(cmd, travail, travail / "ffmpeg.log", delai=10 * 60)
        if code != 0 or not sortie_mp4.exists():
            C.journal(AGENT, "erreur", f"{nom} : montage final ffmpeg en échec (code {code})"); print(f"! Montage final en échec : {sortie[-400:]}"); return 1
        d = duree(sortie_mp4)
        C.A_VALIDER.mkdir(parents=True, exist_ok=True)
        shutil.move(str(sortie_mp4), C.A_VALIDER / f"{nom}.mp4")
        (C.A_VALIDER / f"{nom}.txt").write_text(doc["legende"] + "\n", encoding="utf-8")
        meta = {k: doc.get(k) for k in ("jour", "passage", "serie", "sujet", "titre", "accroche", "theme", "angle", "fin_variante", "structure")} | {
            "duree_s": round(d, 1), "duree_ok": conf["duree_min_s"] <= d <= conf["duree_max_s"], "marketing": bool(doc.get("marketing")), "hook": (doc.get("marketing") or {}).get("gardee") or doc["scenes"][0], "contenu_ia": True, "etiquette_ia_tiktok": True, "outil": conf["outil"], "decor": RS.decor(doc.get("decor")) if stickstage else "", "histoire": doc.get("histoire"), "tts": voix["moteur"], "voix": VX.voix_ligne(conf, doc["serie"])["edge" if voix["moteur"] == VX.MOTEUR_EDGE else "kokoro"], "tts_bascule": voix["bascule"],
            "rendu_s": round(time.time() - t0), "cree_le": f"{datetime.now():%Y-%m-%d %H:%M}"}
        (C.A_VALIDER / f"{nom}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
        shutil.rmtree(travail, ignore_errors=True)
        plage = f"{conf['duree_min_s']}-{conf['duree_max_s']} s"
        C.journal(AGENT, "video", f"{nom} : {d:.1f} s, rendu en {meta['rendu_s']} s, série {doc['serie']}, outil {conf['outil']}, voix {voix['moteur']}" + ("" if meta["duree_ok"] else f" (durée hors {plage})"))
        C.csv_ligne(AGENT, nom, doc["serie"], conf["lignes"][doc["serie"]].get("compte", ""), "à valider", (doc.get("marketing") or {}).get("gardee") or doc["scenes"][0], f"{d:.1f} s, rendu en {meta['rendu_s']} s, {conf['outil']}" + (f", histoire {doc['histoire']}" if doc.get("histoire") else "") + (f" ; {voix['bascule']}" if voix["bascule"] else ""), tts=voix["moteur"],
                    histoire=doc.get("histoire") or "", formule=(doc.get("marketing") or {}).get("formule", ""), theme=doc.get("theme") or doc.get("angle") or "",
                    fin=doc.get("fin_variante") or ("fin A" if doc["serie"] == "A" else ""), duree_s=f"{d:.1f}", voix=meta["voix"])
        print(f"Vidéo prête : {C.A_VALIDER / (nom + '.mp4')} ({d:.1f} s, rendu en {meta['rendu_s']} s, outil {conf['outil']}, voix {voix['moteur']})" + ("" if meta["duree_ok"] else f" ; ATTENTION durée hors {plage}"))
        return 0
    finally:
        try: VERROU.unlink()
        except OSError: pass


def finir_sketch(conf, doc, nom, travail, voix, t0):
    """Vidéo d'un sketch montée par videos-monteur ; acceptée -> a-valider + journal + CSV ; refusée 3 fois -> déjà mise à part par le monteur (code 1)."""
    r = MT.monter(doc, conf, nom, travail, lancer, voix, POLICE_SOURCE, POLICE_ST_SOURCE, fins(doc["serie"], conf), accroche_ecran, temps_mots)
    moteur = voix["moteur"]; noms_voix = VX.voix_dialogue(conf, doc["interlocuteur"]["genre"])
    voix_txt = " + ".join(noms_voix[k]["edge" if moteur == VX.MOTEUR_EDGE else "kokoro"] + (f" (hauteur {noms_voix[k].get('kokoro_hauteur', 1.0)})" if moteur != VX.MOTEUR_EDGE else "")
                          for k in ("G", "I"))
    if not r["ok"]:
        C.journal(AGENT, "erreur", f"{nom} : sketch {doc['sketch']} mis à part ({'; '.join(r['motifs'])[:200]})")
        C.csv_ligne(AGENT, nom, "B", conf["lignes"]["B"].get("compte", ""), "mise à part", doc["scenes"][0], "; ".join(r["motifs"])[:200], tts=moteur,
                    histoire=doc["sketch"], formule=doc.get("formule", ""), theme=doc.get("theme", ""), fin=doc.get("fin_variante", ""), voix=voix_txt)
        print(f"! Sketch {doc['sketch']} mis à part ({r['mp4']}) : {'; '.join(r['motifs'])}"); return 1
    C.A_VALIDER.mkdir(parents=True, exist_ok=True); shutil.move(str(r["mp4"]), C.A_VALIDER / f"{nom}.mp4")
    (C.A_VALIDER / f"{nom}.txt").write_text(doc["legende"] + "\n", encoding="utf-8")
    d = r["duree_s"]; rapport = r["rapport"]
    meta = {k: doc.get(k) for k in ("jour", "passage", "serie", "format", "sketch", "titre", "theme", "categorie", "formule", "fin_variante", "valeurs", "interlocuteur", "variante")} | {
        "duree_s": d, "duree_ok": True, "contenu_ia": True, "etiquette_ia_tiktok": True, "outil": "stick-stage", "decor": RS.decor(doc.get("decor")), "histoire": doc["sketch"],
        "tts": moteur, "voix": voix_txt, "tts_bascule": voix["bascule"], "musique": rapport.get("musique"), "musique_licence": "CC0-1.0 (stick-stage, synthétisée par code)",
        "sonnerie": "générée par code (monteur.py)", "ecart_voix_musique_db": rapport.get("ecart_db"), "controle_qualite": rapport.get("controle"), "essais": r["essais"],
        "rendu_s": round(time.time() - t0), "cree_le": f"{datetime.now():%Y-%m-%d %H:%M}"}
    (C.A_VALIDER / f"{nom}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    shutil.rmtree(travail, ignore_errors=True)
    C.journal(AGENT, "video", f"{nom} : sketch {doc['sketch']}, {d:.1f} s, {r['essais']} essai(s), {meta['rendu_s']} s, voix {moteur}")
    C.csv_ligne(AGENT, nom, "B", conf["lignes"]["B"].get("compte", ""), "à valider", doc["scenes"][0], f"{d:.1f} s, rendu en {meta['rendu_s']} s, sketch {doc['sketch']}, contrôle OK"
                + (f" ; {voix['bascule']}" if voix["bascule"] else ""), tts=moteur, histoire=doc["sketch"], formule=doc.get("formule", ""), theme=doc.get("theme", ""),
                fin=doc.get("fin_variante", ""), duree_s=f"{d:.1f}", voix=voix_txt)
    print(f"Vidéo prête : {C.A_VALIDER / (nom + '.mp4')} ({d:.1f} s, {r['essais']} essai(s), rendu en {meta['rendu_s']} s, voix {moteur})"); return 0


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
