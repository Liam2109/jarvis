#!/usr/bin/env python3
"""Voix des vidéos (équipe Vidéos TikTok, 16/11/2026) : edge-tts en principal (voix Microsoft gratuite, en ligne), bascule automatique sur Kokoro en local
(kokoro-onnx, modèle int8 dans Videos\\outils\\kokoro, hors git) si edge-tts échoue : internet absent, erreur, ou plus de EDGE_DELAI_S secondes pour toute la narration.
Une voix fixe par ligne éditoriale : videos-config.json > lignes.<X>.voix = {"edge": ..., "kokoro": ..., "kokoro_vitesse": ...}.
Une phrase = un fichier scene_001.mp3, scene_002.mp3… (repris tel quel par stickfigure-pipeline-v2 via reuse_audio_from). Toute la vidéo garde le même moteur.
Le moteur réellement utilisé est rendu à l'appelant (videos-creation l'écrit dans journal-videos.csv, colonne tts).
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


def voix_ligne(conf, serie):
    """Voix fixe de la ligne (A ou B) : config de la ligne, sinon « voix » générale pour edge-tts, sinon défaut."""
    v = dict(VOIX_DEFAUT, edge=conf.get("voix") or VOIX_DEFAUT["edge"])
    v.update({k: x for k, x in ((conf.get("lignes") or {}).get(serie, {}).get("voix") or {}).items() if x not in (None, "")})
    return v


def fichier_phrase(dossier, i): return Path(dossier) / f"scene_{i + 1:03d}.mp3"


def edge_synthese(phrases, voix, dossier, delai=EDGE_DELAI_S):
    """Une phrase = un mp3 + les temps de ses mots (WordBoundary). Lève une exception si edge-tts échoue ou dépasse `delai` secondes au total. -> [[(début, fin)]]"""
    if os.environ.get("JARVIS_VIDEOS_EDGE_ECHEC") == "1": raise RuntimeError("échec d'edge-tts simulé (JARVIS_VIDEOS_EDGE_ECHEC=1)")
    import edge_tts

    async def une(i, phrase):
        audio, mots = bytearray(), []
        async for c in edge_tts.Communicate(phrase, voix, boundary="WordBoundary").stream():
            if c.get("type") == "audio": audio += c["data"]
            elif c.get("type") == "WordBoundary": mots.append((c["offset"] / 1e7, (c["offset"] + c["duration"]) / 1e7))
        if not audio: raise RuntimeError("edge-tts n'a renvoyé aucun son")
        fichier_phrase(dossier, i).write_bytes(bytes(audio)); return mots

    async def toutes(): return [await une(i, p) for i, p in enumerate(phrases)]
    return asyncio.run(asyncio.wait_for(toutes(), timeout=delai))


def _ffmpeg_mp3(wav, mp3):
    r = subprocess.run([C.executable("ffmpeg"), "-y", "-v", "error", "-i", str(wav), "-c:a", "libmp3lame", "-q:a", "2", str(mp3)], capture_output=True,
                       env=dict(os.environ, PATH=C.chemin_complet()), creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0)
    if r.returncode != 0 or not Path(mp3).exists(): raise RuntimeError("conversion mp3 de la voix Kokoro en échec")


def kokoro_synthese(phrases, voix, dossier, vitesse=1.0):
    """Kokoro local (kokoro-onnx, français « fr-fr ») : une phrase = un mp3. Lève une exception si le modèle manque. -> None (pas de temps des mots)."""
    if not (KOKORO_MODELE.exists() and KOKORO_VOIX.exists()): raise RuntimeError(f"modèle Kokoro absent ({KOKORO})")
    if KOKORO_DLL.is_dir() and hasattr(os, "add_dll_directory"): os.add_dll_directory(str(KOKORO_DLL))   # runtime Visual C++ (msvcp140…) copié à côté du modèle
    import numpy as np
    from kokoro_onnx import Kokoro
    k = Kokoro(str(KOKORO_MODELE), str(KOKORO_VOIX))
    for i, phrase in enumerate(phrases):
        son, freq = k.create(phrase, voice=voix, speed=float(vitesse), lang="fr-fr")
        wav = fichier_phrase(dossier, i).with_suffix(".wav")
        with wave.open(str(wav), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(freq); w.writeframes((np.clip(son, -1, 1) * 32767).astype("<i2").tobytes())
        _ffmpeg_mp3(wav, fichier_phrase(dossier, i)); wav.unlink(missing_ok=True)
    return None


def synthese(phrases, voix, dossier, edge=edge_synthese, kokoro=kokoro_synthese, delai=EDGE_DELAI_S):
    """edge-tts d'abord ; s'il échoue (erreur, pas d'internet, plus de `delai` s), Kokoro pour TOUTE la narration (une seule voix par vidéo).
    -> {"moteur": "edge-tts" | "kokoro", "temps": [[(début, fin)]] ou None, "bascule": raison ou "", "duree_s": secondes}. Lève RuntimeError si les deux échouent."""
    dossier = Path(dossier); dossier.mkdir(parents=True, exist_ok=True); t0 = time.time()
    try:
        temps = edge(phrases, voix["edge"], dossier, delai)
        if all(fichier_phrase(dossier, i).exists() for i in range(len(phrases))):
            return {"moteur": MOTEUR_EDGE, "temps": temps, "bascule": "", "duree_s": round(time.time() - t0, 1)}
        raison = "fichier son manquant"
    except (asyncio.TimeoutError, TimeoutError): raison = f"plus de {delai} s"
    except Exception as e: raison = f"{type(e).__name__} : {str(e)[:120]}"
    for f in dossier.glob("scene_*.mp3"): f.unlink(missing_ok=True)   # jamais un mélange de deux voix
    try: kokoro(phrases, voix["kokoro"], dossier, voix.get("kokoro_vitesse", 1.0))
    except Exception as e: raise RuntimeError(f"aucune voix : edge-tts ({raison}), Kokoro ({type(e).__name__} : {str(e)[:120]})")
    if not all(fichier_phrase(dossier, i).exists() for i in range(len(phrases))): raise RuntimeError(f"aucune voix : edge-tts ({raison}), Kokoro (fichier manquant)")
    return {"moteur": MOTEUR_KOKORO, "temps": None, "bascule": f"edge-tts en échec ({raison})", "duree_s": round(time.time() - t0, 1)}


def chemin_sans_edge(chemin):
    """PATH sans les dossiers qui contiennent edge-tts : l'outil de rendu ne refait pas sa propre voix et reprend nos fichiers (reuse_audio_from)."""
    garde = []
    for d in chemin.split(os.pathsep):
        if d and not any((Path(d) / n).exists() for n in ("edge-tts.exe", "edge-tts")): garde.append(d)
    return os.pathsep.join(garde)
