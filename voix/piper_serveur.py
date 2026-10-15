"""Serveur de synthèse vocale LOCALE (Piper TTS) : le modèle est chargé UNE fois, puis chaque ligne reçue sur l'entrée standard produit un fichier WAV.
Ligne reçue (ASCII) : {"t": "<texte en base64 UTF-8>", "d": "<chemin du .wav à écrire>"}.  Le fichier est écrit en .part puis renommé : sa présence = synthèse terminée.
Usage : python -I piper_serveur.py <modele.onnx> <fichier_pret> [<réglages JSON en base64>]   (le fichier_pret est créé quand le modèle est chargé et réchauffé).
Réglages (config.json, voix_piper_*) : length_scale (débit), noise_scale / noise_w (variation d'intonation), sentence_silence (silence entre phrases, en s), marge_ms et fondu_ms (fin d'audio).
S'arrête tout seul quand Jarvis se ferme (entrée standard fermée). Ne télécharge rien, n'utilise aucun réseau."""
import base64
import json
import os
import sys
import wave
from array import array

PAR_DEFAUT = {"length_scale": 1.08, "noise_scale": 0.75, "noise_w": 0.9, "sentence_silence": 0.25, "marge_ms": 200, "fondu_ms": 40}


def lire_reglages(arg):
    r = dict(PAR_DEFAUT)
    try:
        r.update(json.loads(base64.b64decode(arg).decode("utf-8")))
    except Exception:
        pass
    return r


def silence(rate, ms):
    return b"\x00\x00" * int(rate * max(0, ms) / 1000)


def finir_audio(pcm, rate, marge_ms, fondu_ms):
    """Fin d'audio naturelle : fondu très court sur la dernière partie du son (pas de coupure sèche) puis marge de silence (150 à 250 ms conseillées)."""
    a = array("h")
    a.frombytes(pcm[: len(pcm) - (len(pcm) % 2)])
    if sys.byteorder == "big":
        a.byteswap()
    n = min(int(rate * max(0, fondu_ms) / 1000), len(a))
    for i in range(n):
        k = len(a) - n + i
        a[k] = int(a[k] * (1.0 - (i + 1) / float(n)))
    if sys.byteorder == "big":
        a.byteswap()
    return a.tobytes() + silence(rate, marge_ms)


def main():
    modele, pret = sys.argv[1], sys.argv[2]
    reglages = lire_reglages(sys.argv[3]) if len(sys.argv) > 3 else dict(PAR_DEFAUT)
    from piper import PiperVoice
    try:
        from piper import SynthesisConfig
        cfg = SynthesisConfig(length_scale=float(reglages["length_scale"]), noise_scale=float(reglages["noise_scale"]), noise_w_scale=float(reglages["noise_w"]))
    except Exception:
        cfg = None
    voix = PiperVoice.load(modele)
    for _ in voix.synthesize("Bonjour.", cfg) if cfg else voix.synthesize("Bonjour."):
        pass
    with open(pret, "w") as f:
        f.write("1")
    try: sys.stdin.reconfigure(encoding="utf-8-sig", errors="replace")      # PowerShell 5.1 peut écrire un BOM devant la 1re ligne : sans cette ligne, la 1re requête était ignorée en silence
    except Exception: pass
    for ligne in sys.stdin:
        ligne = ligne.lstrip("\ufeff")
        try:
            r = json.loads(ligne)
            texte = base64.b64decode(r["t"]).decode("utf-8")
            dest = r["d"]
        except Exception:
            continue
        tmp = dest + ".part"
        try:
            pcm, taux = [], 22050
            for morceau in (voix.synthesize(texte, cfg) if cfg else voix.synthesize(texte)):
                taux = morceau.sample_rate
                if pcm:
                    pcm.append(silence(taux, reglages["sentence_silence"] * 1000))      # silence entre deux phrases
                pcm.append(morceau.audio_int16_bytes)
            if not pcm:
                continue
            with wave.open(tmp, "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(taux)
                w.writeframes(finir_audio(b"".join(pcm), taux, reglages["marge_ms"], reglages["fondu_ms"]))
            os.replace(tmp, dest)
        except Exception:
            try:
                os.remove(tmp)
            except Exception:
                pass


if __name__ == "__main__":
    main()
