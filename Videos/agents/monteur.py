#!/usr/bin/env python3
"""Agent videos-monteur (équipe Vidéos TikTok, 17/11/2026) : monte les vidéos « sketch à deux » de la ligne B, appelé par videos-creation (pas de tâche à lui).
Aucun token Claude, aucun réseau : code + ffmpeg + stick-stage (MIT, hors git).
  1. Plans : un changement (coupe, gros plan ou zoom bref de caméra) au plus toutes les 3 s. Le réalisateur de stick-stage coupe à chaque réplique ; le monteur lit
     la timeline compilée (generated/timeline.json) AVANT le rendu et ajoute un zoom (punch-in) au milieu de chaque plan de plus de 3 s, puis recompile.
  2. Son : la voix (deux personnages) et les bruitages du skit (catalogue CC0 de stick-stage), une musique de fond légère en continu (catalogue CC0 de stick-stage,
     générée par code) environ 18 dB sous la voix, la sonnerie de téléphone (générée ici par code) dans le silence qui précède la réplique, volume final normalisé
     (-14 LUFS, crête -1,5 dB). Licences : Videos\\SKILL-VIDEOS.md.
  3. Image : sous-titres très grands, 1 à 3 mots, au centre vers le bas, contour épais, mot clé en couleur, hors des zones masquées par TikTok (bas et droite) ;
     titre du sketch en haut pendant 2,5 s ; « Contenu généré par IA » tout du long ; carte de fin bleu nuit (jamais de fond noir plein).
  4. Contrôle qualité automatique : durée 25-35 s, aucune image noire, sous-titres dans la zone sûre, voix au moins 12 dB au-dessus de la musique, aucun plan de plus de 3 s.
     Échec : on refait (2 fois au plus, rythme ajusté si la durée est en cause), puis la vidéo est mise à part dans Videos\\a-part avec le motif (.json).
Trace du harness à chaque montage (B2B\\logs\\agents\\videos-monteur). RIEN n'est publié ici.
  python Videos\\agents\\monteur.py etat"""
import json, math, os, re, shutil, subprocess, sys, time, wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "B2B" / "harness"))
import commun as C   # noqa: E402
import rendu_stickstage as RS   # noqa: E402

AGENT = "videos-monteur"
A_PART = C.VIDEOS / "a-part"
PLAN_MAX_S = 3.0
DUREE_S = (25.0, 35.0)
ESSAIS = 3                      # 1 montage + 2 reprises au plus
FIN_S = 2.0                     # carte de fin (la fin est déjà dite par Gérard face caméra)
FIN_S_COURTE = 1.2              # reprise d'une vidéo trop longue : carte de fin raccourcie
TEMPO_MAX = 1.12                # reprise d'une vidéo trop longue : voix accélérée de 12 % au plus (atempo garde la hauteur)
ECART_MUSIQUE_DB, ECART_MIN_DB = 18.0, 12.0
SONIE_FINALE = -14.0
MUSIQUES = {"comedie": "room", "lecon": "resolve", "autre": "mystery"}   # stick-stage public/music/<id>.wav : CC0-1.0, synthétisées par code (scripts/music-gen.ts)
SONNERIE_S = 1.1
# Sous-titres (1080x1920) : zone sûre TikTok = x de 120 à 880 (boutons à droite au-delà de 900), rien sous y = 1300 (légende et barre du bas)
ST_TAILLE, ST_CONTOUR, ST_MARGE_G, ST_MARGE_D, ST_BAS = 104, 9, 120, 200, 1240
ST_LARGEUR = 1080 - ST_MARGE_G - ST_MARGE_D
ST_CHASSE = 0.66                # largeur moyenne d'un caractère d'Arial Black, en fraction de la taille
ACCENT_ASS = "&H00D7FF&"        # jaune (#FFD700) : mot clé de chaque groupe
IA_Y = 1380
FOND_FIN = "0x1F4E79"


def _env(): return dict(os.environ, PATH=C.chemin_complet())


def _ff(args, timeout=600):
    return subprocess.run([C.executable("ffmpeg"), "-hide_banner", "-nostats", *args], capture_output=True, text=True, encoding="utf-8", errors="replace",
                          env=_env(), timeout=timeout, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0)


# --- 1. Plans ---------------------------------------------------------------------------------------------------------
def changements(timeline):
    """Instants (s) où l'image change (coupe, zoom, début de scène) et durée du corps (s), lus dans la timeline compilée de stick-stage."""
    fps = timeline["fps"]; t, fin = [], 0
    for sc in timeline["scenes"]:
        tl = sc["timeline"]; base = sc["from"]
        t += [base] + [base + s["frame"] for s in tl.get("shots", [])] + [base + p["frame"] for p in tl.get("punchIns", [])]
        fin = max(fin, base + tl.get("durationInFrames", sc.get("durationInFrames", 0)))
    fin = timeline.get("durationInFrames", fin) or fin
    return sorted({x / fps for x in t}), fin / fps


def plans_trop_longs(timeline, maxi=PLAN_MAX_S):
    """[(début, fin)] des plans de plus de `maxi` s (la carte de fin, 2 s, est un plan à part)."""
    ch, fin = changements(timeline)
    bornes = ch + [fin]
    return [(a, b) for a, b in zip(bornes, bornes[1:]) if b - a > maxi + 0.05]


class TropLong(Exception):
    """Durée prévue (compilation) trop longue même au rythme le plus serré : la voix doit être accélérée AVANT le rendu."""
    def __init__(self, prevue): super().__init__(f"durée prévue {prevue:.1f} s au rythme le plus serré"); self.prevue = prevue


SERRES = ("snappy", "argument")   # du moins serré au plus serré


def retoucher_plans(dossier_skit, fin_s=FIN_S):
    """Après chaque compilation (avant le rendu, qui coûte 2 à 3 min) : durée prévue hors 25-35 s -> rythme changé (« snappy » puis « argument » si trop long,
    « sitcom » si trop court ; encore trop long au rythme « argument » : TropLong, la voix sera accélérée) ;
    sinon un zoom bref au milieu de chaque plan de plus de 3 s (sur celui qui parle). -> True si le skit a changé (à recompiler)."""
    d = Path(dossier_skit); tl = json.loads((d / "generated" / "timeline.json").read_text(encoding="utf-8")); skit = json.loads((d / "skit.json").read_text(encoding="utf-8"))
    beats = {b["id"]: b for b in skit["beats"]}; fps = tl["fps"]; change = False
    prevue = changements(tl)[1] + fin_s; style = skit.get("style")
    if prevue > DUREE_S[1] - 0.5:
        if style == SERRES[-1]: raise TropLong(prevue)
        skit["style"] = SERRES[SERRES.index(style) + 1] if style in SERRES else SERRES[0]
    elif prevue < DUREE_S[0] + 0.5 and style != "sitcom": skit["style"] = "sitcom"
    if skit.get("style") != style:
        (d / "skit.json").write_text(json.dumps(skit, ensure_ascii=False, indent=1), encoding="utf-8"); return True
    for a, b in plans_trop_longs(tl):
        m = (a + b) / 2 * fps
        # la réplique qui couvre le milieu du plan, sinon la suivante (le zoom tombe alors dans le silence qui la précède : ms négatif)
        spans = sorted(((sc, sp) for sc in tl["scenes"] for sp in sc["timeline"]["beats"] if not sp.get("synthetic") and sp["id"] in beats),
                       key=lambda x: x[0]["from"] + x[1]["from"])
        cible = next(((sc, sp) for sc, sp in spans if sc["from"] + sp["from"] <= m < sc["from"] + sp["to"]), None) or next(((sc, sp) for sc, sp in spans if sc["from"] + sp["from"] > m), None)
        for sc, sp in [cible] if cible else []:
                f0 = sc["from"] + sp["from"]
                beat = beats[sp["id"]]; qui = beat.get("speaker") or "gerard"
                debut = sc["from"] + (sp.get("audioFrom") if sp.get("audioFrom") is not None else sp["from"])
                ms = int((m - debut) / fps * 1000)
                cadre = next((s for s in reversed(sc["timeline"].get("shots", [])) if sc["from"] + s["frame"] <= f0), None)
                shot = beat.get("shot") or {"framing": (cadre or {}).get("framing", "two")} | ({"on": cadre["on"]} if cadre and cadre.get("on") else {})
                if "punchIn" in shot: continue
                shot["punchIn"] = {"on": qui, "at": {"ms": ms}}; beat["shot"] = shot; change = True
    if change: (d / "skit.json").write_text(json.dumps(skit, ensure_ascii=False, indent=1), encoding="utf-8")
    return change


# --- 2. Son ------------------------------------------------------------------------------------------------------------
def sonnerie(fichier, freq=44100):
    """Sonnerie de téléphone générée par code (deux salves d'un timbre 1 200 + 1 500 Hz modulé à 25 Hz) : aucun droit d'auteur."""
    n = int(SONNERIE_S * freq); data = bytearray()
    for i in range(n):
        t = i / freq; salve = (t % 0.55) < 0.4
        env = min(1.0, (t % 0.55) / 0.01) * (1 - max(0.0, ((t % 0.55) - 0.36) / 0.04)) if salve else 0.0
        v = 0.32 * env * (0.6 + 0.4 * math.sin(2 * math.pi * 25 * t)) * (math.sin(2 * math.pi * 1200 * t) + 0.7 * math.sin(2 * math.pi * 1500 * t)) / 1.7
        data += int(max(-1, min(1, v)) * 32767).to_bytes(2, "little", signed=True)
    with wave.open(str(fichier), "wb") as w: w.setnchannels(1); w.setsampwidth(2); w.setframerate(freq); w.writeframes(bytes(data))
    return Path(fichier)


def sonie(fichier):
    """Sonie intégrée (LUFS) d'un fichier, mesurée par ffmpeg (filtre loudnorm, passe d'analyse). None si illisible ou silence."""
    r = _ff(["-i", str(fichier), "-vn", "-af", "loudnorm=print_format=json", "-f", "null", "-"])
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr or "")
    try: v = float(json.loads(m.group(0))["input_i"]) if m else None
    except (ValueError, KeyError): return None
    return v if v is not None and v > -70 else None


def musique(categorie, n=0):
    """Fichier de la musique de fond (catalogue CC0 de stick-stage) : selon la catégorie du sketch ; autre musique si absente."""
    dossier = RS.OUTIL / "public" / "music"
    f = dossier / f"{MUSIQUES.get(categorie, 'room')}.wav"
    if f.exists(): return f
    autres = sorted(dossier.glob("*.wav")) if dossier.exists() else []
    return autres[n % len(autres)] if autres else None


def bande_son(corps, total_s, sonneries_s, categorie, travail):
    """Bande son finale (wav) : voix + bruitages du skit, musique 18 dB sous la voix, sonneries ; normalisée à -14 LUFS.
    -> (fichier, rapport {voix_lufs, musique_lufs, ecart_db, musique})."""
    travail = Path(travail)
    voix = travail / "voix-skit.wav"
    r = _ff(["-y", "-v", "error", "-i", str(corps), "-vn", "-ac", "2", "-ar", "44100", "-af", f"apad,atrim=0:{total_s:.3f}", str(voix)])
    if r.returncode != 0: raise RuntimeError(f"extraction de la voix en échec : {r.stderr[-200:]}")
    v = sonie(corps)
    if v is None: raise RuntimeError("voix inaudible dans le rendu")
    rapport = {"voix_lufs": round(v, 1), "musique": "", "musique_lufs": None, "ecart_db": None}
    entrees, filtres, mix = ["-i", str(voix)], [], ["[0:a]"]
    m = musique(categorie)
    if m:
        brute = travail / "musique-brute.wav"
        _ff(["-y", "-v", "error", "-stream_loop", "-1", "-i", str(m), "-t", f"{total_s:.3f}", "-ac", "2", "-ar", "44100", str(brute)])
        m0 = sonie(brute)
        if m0 is not None:
            gain = (v - ECART_MUSIQUE_DB) - m0
            fond = travail / "musique.wav"
            _ff(["-y", "-v", "error", "-i", str(brute), "-af", f"volume={gain:.2f}dB,afade=t=in:d=0.6,afade=t=out:st={max(0, total_s - 1.2):.2f}:d=1.2", str(fond)])
            m1 = sonie(fond)
            rapport.update(musique=f"{m.stem} (stick-stage, CC0-1.0)", musique_lufs=round(m1, 1) if m1 is not None else None,
                           ecart_db=round(v - m1, 1) if m1 is not None else None)
            entrees += ["-i", str(fond)]; mix.append(f"[{len(mix)}:a]")
    if sonneries_s:
        son = sonnerie(travail / "sonnerie.wav")
        for t in sonneries_s:
            k = len(mix); entrees += ["-i", str(son)]
            filtres.append(f"[{k}:a]aformat=channel_layouts=stereo,aresample=44100,volume=0.9,adelay={int(max(0, t) * 1000)}:all=1[s{k}]"); mix.append(f"[s{k}]")
    sortie = travail / "bande.wav"
    graphe = ";".join(filtres + [f"{''.join(mix)}amix=inputs={len(mix)}:duration=first:normalize=0,loudnorm=I={SONIE_FINALE}:TP=-1.5:LRA=11,"
                                 f"aresample=44100,atrim=0:{total_s:.3f}[a]"])
    r = _ff(["-y", "-v", "error", *entrees, "-filter_complex", graphe, "-map", "[a]", "-ac", "2", "-ar", "44100", str(sortie)])
    if r.returncode != 0 or not sortie.exists(): raise RuntimeError(f"mixage en échec : {r.stderr[-300:]}")
    return sortie, rapport


# --- 3. Image : sous-titres ----------------------------------------------------------------------------------------------
def largeur_px(texte, taille=ST_TAILLE): return len(re.sub(r"\{[^}]*\}", "", texte)) * ST_CHASSE * taille


def sous_titres_ass(plan, temps, police="Arial Black"):
    """Fichier .ass : 1 à 3 mots à la fois (plan = groupes par phrase), très gros, contour épais, mot clé en jaune, dans la zone sûre TikTok."""
    lignes = ["[Script Info]", "ScriptType: v4.00+", "PlayResX: 1080", "PlayResY: 1920", "WrapStyle: 0", "ScaledBorderAndShadow: yes", "",
              "[V4+ Styles]", "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
              "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
              f"Style: Mot,{police},{ST_TAILLE},&H00FFFFFF,&H00FFFFFF,&H00000000,&H78000000,-1,0,0,0,100,100,0,0,1,{ST_CONTOUR},3,2,{ST_MARGE_G},{ST_MARGE_D},{1920 - ST_BAS},1", "",
              "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    for groupes, tm in zip(plan, temps):
        i = 0
        for g in groupes:
            n = len(g["mots"]); morceau = tm[i:i + n]
            if not morceau: break
            debut, fin = morceau[0][0], morceau[-1][1]
            texte = " ".join((f"{{\\c{ACCENT_ASS}}}{m}{{\\c&HFFFFFF&}}" if j == g.get("cle") else m) for j, m in enumerate(g["mots"]))
            lignes.append(f"Dialogue: 0,{_t(debut)},{_t(max(fin, debut + 0.3))},Mot,,0,0,0,,{texte}")
            i += n
    return "\n".join(lignes) + "\n"


def _t(s): s = max(0.0, s); return f"{int(s // 3600)}:{int(s % 3600 // 60):02d}:{s % 60:05.2f}"


def controle_sous_titres(ass):
    """Problèmes de placement : chaque sous-titre tient en 2 lignes au plus entre x = 120 et x = 880 et reste entre y = 700 et y = 1300."""
    pb = []
    m = re.search(r"^Style: Mot,[^,]*,(\d+),(?:[^,]*,){13}(\d+),\d+,(\d+),(\d+),(\d+),(\d+)", ass, re.M)
    if not m: return ["style des sous-titres illisible"]
    taille, contour, _al, mg, md, mv = map(int, m.groups())
    if mg < 120 or 1080 - md > 900: pb.append(f"marges hors zone sûre (x de {mg} à {1080 - md})")
    bas = 1920 - mv
    if bas > 1300: pb.append(f"sous-titres trop bas (y = {bas}, zone de l'interface TikTok)")
    for l in re.findall(r"^Dialogue: [^,]*,[^,]*,[^,]*,[^,]*,[^,]*,[^,]*,[^,]*,[^,]*,[^,]*,(.*)$", ass, re.M):
        n = max(1, math.ceil(largeur_px(l, taille) / (1080 - mg - md)))
        if n > 2: pb.append(f"sous-titre trop long ({n} lignes) : « {re.sub(r'{[^}]*}', '', l)} »")
        elif bas - n * taille * 1.15 < 700: pb.append(f"sous-titre trop haut : « {re.sub(r'{[^}]*}', '', l)} »")
    return pb


def filtre_video(taille_accroche, n_fins):
    """[0] corps -> sous-titres + titre du sketch (0-2,5 s) + mention IA ; [1] carte de fin bleu nuit ; concaténés (le son vient de la bande déjà mixée)."""
    dt = lambda f, t, y, extra="", x="(w-text_w)/2": f"drawtext=fontfile=police.ttf:textfile={f}:fontsize={t}:fontcolor=white:x={x}:y={y}{extra}"
    corps = ["subtitles=sous-titres.ass:fontsdir=.",
             dt("accroche.txt", taille_accroche, "h*0.13", ":line_spacing=14:box=1:boxcolor=0x1F4E79@0.85:boxborderw=26:enable='lt(t,2.5)'", x="(1020-text_w)/2"),
             dt("ia.txt", 34, str(IA_Y), ":fontcolor=white@0.85:box=1:boxcolor=black@0.35:boxborderw=8")]
    fin = [dt(f"fin{i}.txt", 70 if i < 2 else 52, f"h*{0.36 + 0.11 * i:.2f}") for i in range(n_fins)] + [dt("ia.txt", 34, str(IA_Y), ":fontcolor=white@0.85")]
    return f"[0:v]{','.join(corps)},fps=30,format=yuv420p,setsar=1[v0];[1:v]{','.join(fin)},format=yuv420p,setsar=1[v1];[v0][v1]concat=n=2:v=1:a=0[v]"


# --- 4. Contrôle qualité -----------------------------------------------------------------------------------------------
def images_noires(fichier):
    """Passages noirs (début, fin) détectés par ffmpeg blackdetect (0,2 s au moins)."""
    r = _ff(["-i", str(fichier), "-vf", "blackdetect=d=0.2:pix_th=0.08", "-an", "-f", "null", "-"])
    return [(float(a), float(b)) for a, b in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", r.stderr or "")]


def controle(duree_s, noirs, pb_sous_titres, rapport_son, plans_longs):
    """Liste des motifs d'échec (vide = vidéo acceptée)."""
    pb = []
    if not DUREE_S[0] <= duree_s <= DUREE_S[1]: pb.append(f"durée {duree_s:.1f} s (25 à 35 s attendues)")
    if noirs: pb.append(f"image noire à {noirs[0][0]:.1f} s")
    pb += pb_sous_titres
    e = rapport_son.get("ecart_db")
    if e is None: pb.append("musique absente ou non mesurée")
    elif e < ECART_MIN_DB: pb.append(f"voix seulement {e:.1f} dB au-dessus de la musique ({ECART_MIN_DB:.0f} dB au moins)")
    if plans_longs: pb.append(f"plan de {plans_longs[0][1] - plans_longs[0][0]:.1f} s à {plans_longs[0][0]:.1f} s (3 s au plus)")
    return pb


def accelerer_voix(dossier, facteur, temps):
    """Accélère chaque réplique (scene_NNN.mp3) d'un facteur (ffmpeg atempo : même hauteur de voix) et recale les temps des mots. -> nouveaux temps."""
    for f in sorted(Path(dossier).glob("scene_*.mp3")):
        tmp = f.with_name(f.stem + "-vite.mp3")
        r = _ff(["-y", "-v", "error", "-i", str(f), "-af", f"atempo={facteur:.4f}", "-c:a", "libmp3lame", "-q:a", "2", str(tmp)])
        if r.returncode != 0 or not tmp.exists(): raise RuntimeError(f"accélération de la voix en échec : {r.stderr[-200:]}")
        os.replace(tmp, f)
    return [[(a / facteur, b / facteur) for a, b in mots] for mots in temps] if temps else temps


def style_suivant(style, motifs, duree_s):
    """Rythme du prochain essai : trop long -> « snappy » (pauses courtes) ; trop court -> « sitcom » (pauses plus longues) ; sinon le même."""
    if any(m.startswith("durée") for m in motifs): return "snappy" if duree_s > DUREE_S[1] else "sitcom"
    return style


# --- Montage complet ---------------------------------------------------------------------------------------------------
def monter(doc, conf, nom, travail, lancer, voix, police_src, police_st_src, fins_texte, accroche_ecran, temps_mots):
    """Monte la vidéo d'un sketch (ESSAIS fois au plus). voix = résultat de voix.synthese (fichiers scene_NNN.mp3 dans travail/voix).
    Les fonctions de videos-creation sont passées en paramètres (aucune importation croisée). -> dict {ok, mp4, duree_s, essais, motifs, rapport}."""
    travail = Path(travail); t0 = time.time(); style = doc.get("style") or "classic"; motifs, essai, final, rapport, duree = [], 0, None, {}, 0.0
    sonneries = [i for i, s in enumerate(doc.get("sfx") or []) if s == "sonnerie"]
    fin_s, temps_voix, tempo = FIN_S, voix.get("temps"), 1.0
    for essai in range(1, ESSAIS + 1):
        if essai > 1 and any(m.startswith("durée") for m in motifs) and duree > DUREE_S[1]:   # trop long : la parole prend le temps, le rythme seul ne suffit pas
            fin_s = FIN_S_COURTE
            f = min(TEMPO_MAX / tempo, max(1.02, (duree - (FIN_S - fin_s)) / (DUREE_S[1] - 0.6)))
            if f > 1.005:
                try: temps_voix = accelerer_voix(travail / "voix", f, temps_voix); tempo *= f
                except RuntimeError as e: print(f"  monteur : {e}")
        d = dict(doc, style=style); final = travail / f"final-{essai}.mp4"
        try:
            corps, debuts, durees, timeline = RS.rendre(d, d["scenes"], travail / "voix", travail, lancer, nom, retoucher=lambda dd: retoucher_plans(dd, fin_s), avec_timeline=True)
            total = duree_fichier(corps) + fin_s
            son, rapport = bande_son(corps, total, [debuts[i] - RS.PAUSE_SONNERIE_MS / 1000 + 0.15 for i in sonneries], d.get("categorie", "autre"), travail)
            deja = dict(zip(d["scenes"], temps_voix or []))
            temps = temps_mots(d["scenes"], durees, edge=lambda p, v: deja.get(p, []), debuts=debuts)
            plan = d.get("sous_titres") or [C.decouper_sous_titres(s, maxi=3, mini=1, car_max=16) for s in d["scenes"]]
            police = "Arial Black" if Path(police_st_src).exists() else "Arial"
            if Path(police_st_src).exists(): shutil.copy2(police_st_src, travail / Path(police_st_src).name)
            shutil.copy2(police_src, travail / "police.ttf"); shutil.copy2(corps, travail / "corps.mp4")
            ass = sous_titres_ass(plan, temps, police); (travail / "sous-titres.ass").write_text(ass, encoding="utf-8")
            accroche, taille = accroche_ecran(d.get("titre") or d["scenes"][0])
            textes = {"accroche.txt": accroche, "ia.txt": "Contenu généré par IA"} | {f"fin{i}.txt": t for i, t in enumerate(fins_texte)}
            for f, t in textes.items(): (travail / f).write_text(t.replace("%", "\\%"), encoding="utf-8")
            cmd = [C.executable("ffmpeg"), "-y", "-v", "error", "-i", "corps.mp4", "-f", "lavfi", "-i", f"color=c={FOND_FIN}:s=1080x1920:r=30:d={fin_s}", "-i", str(son),
                   "-filter_complex", filtre_video(taille, len(fins_texte)), "-map", "[v]", "-map", "2:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
                   "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", final.name]
            code, sortie = lancer(cmd, travail, travail / f"ffmpeg-{essai}.log", delai=10 * 60)
            if code != 0 or not final.exists(): raise RuntimeError(f"montage ffmpeg en échec : {sortie[-200:]}")
            duree = duree_fichier(final)
            motifs = controle(duree, images_noires(final), controle_sous_titres(ass), rapport, plans_trop_longs(timeline))
        except TropLong as e:   # aucun rendu lancé : la voix est accélérée à l'essai suivant
            duree, motifs = e.prevue, [f"durée {e.prevue:.1f} s prévue avant le rendu (25 à 35 s attendues)"]
        except (RuntimeError, OSError, ValueError, KeyError, subprocess.TimeoutExpired) as e:
            duree, motifs = 0.0, [f"essai {essai} : {type(e).__name__} : {str(e)[:200]}"]
        rapport = dict(rapport, essai=essai, style=style, voix_acceleree=round(tempo, 3), carte_fin_s=fin_s, controle="OK" if not motifs else "; ".join(motifs))
        print(f"  monteur, essai {essai} ({style}) : {duree:.1f} s, " + ("contrôle OK" if not motifs else f"refusé : {'; '.join(motifs)}"))
        if not motifs:
            _trace(f"monter {nom}", f"OK en {essai} essai(s), {duree:.1f} s, voix {rapport.get('ecart_db')} dB au-dessus de la musique", time.time() - t0, True)
            return {"ok": True, "mp4": final, "duree_s": round(duree, 1), "essais": essai, "motifs": [], "rapport": rapport}
        style = style_suivant(style, motifs, duree)
    A_PART.mkdir(parents=True, exist_ok=True)
    if final and final.exists(): shutil.move(str(final), A_PART / f"{nom}.mp4")
    (A_PART / f"{nom}.json").write_text(json.dumps({"video": nom, "sketch": doc.get("sketch"), "motifs": motifs, "essais": essai, "rapport": rapport,
                                                    "mis_a_part_le": time.strftime("%Y-%m-%d %H:%M")}, ensure_ascii=False, indent=1), encoding="utf-8")
    C.journal(AGENT, "à part", f"{nom} : {'; '.join(motifs)[:250]}")
    _trace(f"monter {nom}", f"mise à part après {essai} essais", time.time() - t0, False, "; ".join(motifs))
    return {"ok": False, "mp4": A_PART / f"{nom}.mp4", "duree_s": 0.0, "essais": essai, "motifs": motifs, "rapport": rapport}


def duree_fichier(f):
    r = subprocess.run([C.executable("ffprobe"), "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(f)], capture_output=True, text=True, env=_env())
    try: return float(r.stdout.strip())
    except ValueError: return 0.0


def _trace(decision, resultat, duree_s, ok, erreur=None):
    try:
        import traces as T
        T.ecrire(AGENT, decision, resultat, duree_s, ok=ok, erreur=erreur)
    except Exception: pass   # une trace qui échoue ne casse jamais le montage


def cmd_etat():
    n = sorted(A_PART.glob("*.json")) if A_PART.exists() else []
    print(f"{len(n)} vidéo(s) mise(s) à part" + (f" (dernière : {n[-1].stem} : {'; '.join(json.loads(n[-1].read_text(encoding='utf-8')).get('motifs', []))[:160]})" if n else ""))
    return 0


if __name__ == "__main__":
    if sys.argv[1:2] == ["etat"]: sys.exit(cmd_etat())
    print(__doc__); sys.exit(2)
