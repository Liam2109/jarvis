#!/usr/bin/env python3
"""Voix des vidéos (équipe Vidéos TikTok, 16/11/2026) : edge-tts en principal (voix Microsoft gratuite, en ligne), bascule automatique sur Kokoro en local
(kokoro-onnx, modèle int8 dans Videos\\outils\\kokoro, hors git) si edge-tts échoue : internet absent, erreur, ou plus de EDGE_DELAI_S secondes pour toute la narration.
Une voix fixe par ligne éditoriale : videos-config.json > lignes.<X>.voix = {"edge": ..., "kokoro": ..., "kokoro_vitesse": ...}.
Une phrase = un fichier scene_001.mp3, scene_002.mp3… (repris tel quel par stickfigure-pipeline-v2 via reuse_audio_from). Toute la vidéo garde le même moteur.
Le moteur réellement utilisé est rendu à l'appelant (videos-creation l'écrit dans journal-videos.csv, colonne tts).
Ligne B en sketch à deux (17/11/2026) : une voix par personnage (voix_dialogue) ; Gérard = voix de la ligne B, l'interlocuteur = voix_interlocuteur selon son genre.
Kokoro n'a qu'une voix française : en bascule, les deux personnages se distinguent par la hauteur (kokoro_hauteur, ffmpeg asetrate : plus grave sous 1) et la vitesse.
Échec simulé (tests, vérification) : variable d'environnement JARVIS_VIDEOS_EDGE_ECHEC=1 -> edge-tts est considéré en panne, sans aucun appel réseau."""
import asyncio, os, subprocess, sys, time, wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import commun as C   # noqa: E402

EDGE_DELAI_S = 30
KOKORO = C.VIDEOS / "outils" / "kokoro"
KOKORO_MODELE, KOKORO_VOIX, KOKORO_DLL = KOKORO / "kokoro-v1.0.int8.onnx", KOKORO / "voices-v1.0.bin", KOKORO / "dll"
VOIX_DEFAUT = {"edge": "fr-FR-RemyMultilingualNeural", "kokoro": "ff_siwis", "kokoro_vitesse": 1.0}
MOTEUR_EDGE, MOTEUR_KOKORO = "edge-tts", "kokoro"
DEBIT_SKETCH = "+15%"   # sketch à deux : répliques un peu plus vives (25 à 35 s)
VOIX_INTERLOCUTEUR = {"f": {"edge": "fr-FR-DeniseNeural", "kokoro": "ff_siwis", "kokoro_vitesse": 1.05, "kokoro_hauteur": 1.0},
                      "h": {"edge": "fr-FR-RemyMultilingualNeural", "kokoro": "ff_siwis", "kokoro_vitesse": 1.08, "kokoro_hauteur": 0.95}}


def voix_ligne(conf, serie):
    """Voix fixe de la ligne (A ou B) : config de la ligne, sinon « voix » générale pour edge-tts, sinon défaut."""
    v = dict(VOIX_DEFAUT, edge=conf.get("voix") or VOIX_DEFAUT["edge"])
    v.update({k: x for k, x in ((conf.get("lignes") or {}).get(serie, {}).get("voix") or {}).items() if x not in (None, "")})
    return v


def voix_dialogue(conf, genre):
    """{"G": voix de Gérard (voix fixe de la ligne B), "I": voix de l'interlocuteur selon son genre (lignes.B.voix_interlocuteur.<f|h>, sinon défaut)}."""
    g = "f" if genre == "f" else "h"
    vi = dict(VOIX_INTERLOCUTEUR[g]); vi.update({k: x for k, x in (((conf.get("lignes") or {}).get("B", {}).get("voix_interlocuteur") or {}).get(g) or {}).items() if x not in (None, "")})
    # Kokoro (une seule voix française) : Gérard plus grave (hauteur 0,85) que l'interlocuteur
    return {"G": dict({"kokoro_hauteur": 0.85}, **voix_ligne(conf, "B"), edge_debit=DEBIT_SKETCH), "I": dict({"edge_debit": DEBIT_SKETCH}, **vi)}


def fichier_phrase(dossier, i): return Path(dossier) / f"scene_{i + 1:03d}.mp3"


def edge_synthese(phrases, voix, dossier, delai=EDGE_DELAI_S, debit="+0%"):
    """Une phrase = un mp3 + les temps de ses mots (WordBoundary). voix : une voix, ou une liste (une par phrase : dialogue).
    Lève une exception si edge-tts échoue ou dépasse `delai` secondes au total. -> [[(début, fin)]]"""
    if os.environ.get("JARVIS_VIDEOS_EDGE_ECHEC") == "1": raise RuntimeError("échec d'edge-tts simulé (JARVIS_VIDEOS_EDGE_ECHEC=1)")
    import edge_tts

    async def une(i, phrase):
        audio, mots = bytearray(), []
        async for c in edge_tts.Communicate(phrase, voix[i] if isinstance(voix, list) else voix, rate=debit[i] if isinstance(debit, list) else debit,
                                            boundary="WordBoundary").stream():
            if c.get("type") == "audio": audio += c["data"]
            elif c.get("type") == "WordBoundary": mots.append((c["offset"] / 1e7, (c["offset"] + c["duration"]) / 1e7))
        if not audio: raise RuntimeError("edge-tts n'a renvoyé aucun son")
        fichier_phrase(dossier, i).write_bytes(bytes(audio)); return mots

    async def toutes(): return [await une(i, p) for i, p in enumerate(phrases)]
    return asyncio.run(asyncio.wait_for(toutes(), timeout=delai))


def _ffmpeg_mp3(wav, mp3, hauteur=1.0, freq=24000):
    """wav -> mp3 ; hauteur != 1 : voix plus grave (< 1) ou plus aiguë, même durée (asetrate puis atempo inverse)."""
    filtre = ["-af", f"asetrate={int(freq * hauteur)},aresample={freq},atempo={1 / hauteur:.4f}"] if abs(float(hauteur) - 1) > 1e-3 else []
    r = subprocess.run([C.executable("ffmpeg"), "-y", "-v", "error", "-i", str(wav), *filtre, "-c:a", "libmp3lame", "-q:a", "2", str(mp3)], capture_output=True,
                       env=dict(os.environ, PATH=C.chemin_complet()), creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0)
    if r.returncode != 0 or not Path(mp3).exists(): raise RuntimeError("conversion mp3 de la voix Kokoro en échec")


def kokoro_synthese(phrases, voix, dossier, vitesse=1.0, hauteur=1.0):
    """Kokoro local (kokoro-onnx, français « fr-fr ») : une phrase = un mp3. voix, vitesse, hauteur : une valeur ou une liste (une par phrase : dialogue).
    Lève une exception si le modèle manque. -> None (pas de temps des mots)."""
    if not (KOKORO_MODELE.exists() and KOKORO_VOIX.exists()): raise RuntimeError(f"modèle Kokoro absent ({KOKORO})")
    if KOKORO_DLL.is_dir() and hasattr(os, "add_dll_directory"): os.add_dll_directory(str(KOKORO_DLL))   # runtime Visual C++ (msvcp140…) copié à côté du modèle
    import numpy as np
    from kokoro_onnx import Kokoro
    k = Kokoro(str(KOKORO_MODELE), str(KOKORO_VOIX))
    for i, phrase in enumerate(phrases):
        un = lambda x: x[i] if isinstance(x, list) else x
        son, freq = k.create(phrase, voice=un(voix), speed=float(un(vitesse)), lang="fr-fr")
        wav = fichier_phrase(dossier, i).with_suffix(".wav")
        with wave.open(str(wav), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(freq); w.writeframes((np.clip(son, -1, 1) * 32767).astype("<i2").tobytes())
        _ffmpeg_mp3(wav, fichier_phrase(dossier, i), float(un(hauteur) or 1.0), freq); wav.unlink(missing_ok=True)
    return None


def synthese(phrases, voix, dossier, edge=edge_synthese, kokoro=kokoro_synthese, delai=EDGE_DELAI_S):
    """edge-tts d'abord ; s'il échoue (erreur, pas d'internet, plus de `delai` s), Kokoro pour TOUTE la narration (jamais deux moteurs dans une vidéo).
    voix : la voix de la ligne, ou une liste de voix (une par phrase : sketch à deux, voir voix_dialogue).
    -> {"moteur": "edge-tts" | "kokoro", "temps": [[(début, fin)]] ou None, "bascule": raison ou "", "duree_s": secondes}. Lève RuntimeError si les deux échouent."""
    dossier = Path(dossier); dossier.mkdir(parents=True, exist_ok=True); t0 = time.time()
    par = isinstance(voix, list); champ = lambda k, d=None: [v.get(k, d) for v in voix] if par else voix.get(k, d)
    try:
        debits = champ("edge_debit", "+0%")
        kw = {"debit": debits} if any(x not in (None, "+0%") for x in (debits if par else [debits])) else {}   # débit (sketch : un peu plus vif)
        temps = edge(phrases, champ("edge"), dossier, delai, **kw)
        if all(fichier_phrase(dossier, i).exists() for i in range(len(phrases))):
            for i, mots in enumerate(temps or []):   # silence après le dernier mot (0,5 à 1 s par phrase chez edge-tts) coupé à 0,2 s
                if mots: couper_fin(fichier_phrase(dossier, i), mots[-1][1] + FIN_APRES_MOT_S)
            return {"moteur": MOTEUR_EDGE, "temps": temps, "bascule": "", "duree_s": round(time.time() - t0, 1)}
        raison = "fichier son manquant"
    except (asyncio.TimeoutError, TimeoutError): raison = f"plus de {delai} s"
    except Exception as e: raison = f"{type(e).__name__} : {str(e)[:120]}"
    for f in dossier.glob("scene_*.mp3"): f.unlink(missing_ok=True)   # jamais un mélange de deux voix
    try: kokoro(phrases, champ("kokoro"), dossier, champ("kokoro_vitesse", 1.0), champ("kokoro_hauteur", 1.0))
    except Exception as e: raise RuntimeError(f"aucune voix : edge-tts ({raison}), Kokoro ({type(e).__name__} : {str(e)[:120]})")
    if not all(fichier_phrase(dossier, i).exists() for i in range(len(phrases))): raise RuntimeError(f"aucune voix : edge-tts ({raison}), Kokoro (fichier manquant)")
    return {"moteur": MOTEUR_KOKORO, "temps": None, "bascule": f"edge-tts en échec ({raison})", "duree_s": round(time.time() - t0, 1)}


FIN_APRES_MOT_S = 0.2


def couper_fin(mp3, fin_s):
    """Coupe un mp3 à fin_s secondes (copie sans réencodage). Sans effet si le fichier n'est pas un vrai mp3 ou si ffmpeg échoue."""
    mp3 = Path(mp3)
    if not mp3.exists() or mp3.stat().st_size < 2000: return False
    tmp = mp3.with_name(mp3.stem + "-coupe.mp3")
    r = subprocess.run([C.executable("ffmpeg"), "-y", "-v", "error", "-i", str(mp3), "-t", f"{fin_s:.3f}", "-c", "copy", str(tmp)], capture_output=True,
                       env=dict(os.environ, PATH=C.chemin_complet()), creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0)
    if r.returncode != 0 or not tmp.exists() or tmp.stat().st_size < 1000: tmp.unlink(missing_ok=True); return False
    os.replace(tmp, mp3); return True


def chemin_sans_edge(chemin):
    """PATH sans les dossiers qui contiennent edge-tts : l'outil de rendu ne refait pas sa propre voix et reprend nos fichiers (reuse_audio_from)."""
    garde = []
    for d in chemin.split(os.pathsep):
        if d and not any((Path(d) / n).exists() for n in ("edge-tts.exe", "edge-tts")): garde.append(d)
    return os.pathsep.join(garde)
