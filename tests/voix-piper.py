"""Test SILENCIEUX de la fin d'audio de la voix Piper (voix/piper_serveur.py : finir_audio, silence, lire_reglages) — aucun modèle chargé, aucun son :
des échantillons PCM simulés. Sortie « OK ... » / « ECHEC ... » ; code 0 si tout est vert."""
import array
import base64
import importlib.util
import json
import os
import sys

try:
    sys.stdout.reconfigure(errors="replace")
except AttributeError:
    pass
ici = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("piper_serveur", os.path.join(os.path.dirname(ici), "voix", "piper_serveur.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
echecs = 0
TAUX = 22050


def verifier(cond, msg):
    global echecs
    if cond:
        print("  OK    " + msg)
    else:
        print("  ECHEC " + msg)
        echecs += 1


def pcm(n, valeur=12000):
    return array.array("h", [valeur] * n).tobytes()


def echantillons(b):
    a = array.array("h")
    a.frombytes(b)
    return a


son = pcm(TAUX)                       # 1 s de son plein
fini = m.finir_audio(son, TAUX, 200, 40)
a = echantillons(fini)
marge = int(TAUX * 0.2)
verifier(len(a) == TAUX + marge, "marge de silence : 200 ms ajoutés en fin d'audio (%d échantillons de plus)" % (len(a) - TAUX))
verifier(all(x == 0 for x in a[TAUX:]), "…et c'est du silence pur")
fondu = int(TAUX * 0.04)
verifier(a[TAUX - 1] == 0 or abs(a[TAUX - 1]) < 30, "la fin du son arrive à zéro : pas de coupure sèche (clic)")
verifier(a[TAUX - fondu - 5] == 12000, "le début et le corps du son sont intacts (la queue n'est pas rognée)")
descente = [a[TAUX - fondu + i] for i in range(fondu)]
verifier(all(descente[i] >= descente[i + 1] for i in range(fondu - 1)), "le fondu est une descente régulière sur 40 ms")
verifier(len(m.finir_audio(son, TAUX, 0, 0)) == len(son) and echantillons(m.finir_audio(son, TAUX, 0, 0))[-1] == 12000, "marge 0 et fondu 0 : audio inchangé")
court = pcm(100)
verifier(len(echantillons(m.finir_audio(court, TAUX, 150, 500))) == 100 + int(TAUX * 0.15), "audio plus court que le fondu : pas d'erreur, fondu limité à la durée")
verifier(len(m.finir_audio(b"", TAUX, 200, 40)) == marge * 2, "audio vide : seulement la marge")
verifier(len(m.silence(TAUX, 250)) == int(TAUX * 0.25) * 2 and m.silence(TAUX, -5) == b"", "silence(ms) : bonne longueur, jamais négatif")
r = m.lire_reglages(base64.b64encode(json.dumps({"length_scale": 1.2, "marge_ms": 180}).encode()).decode())
verifier(r["length_scale"] == 1.2 and r["marge_ms"] == 180 and r["noise_scale"] == m.PAR_DEFAUT["noise_scale"], "réglages reçus de Jarvis (base64) ; le reste garde la valeur par défaut")
verifier(m.lire_reglages("pas du base64 !!")["marge_ms"] == 200 and m.lire_reglages("")["fondu_ms"] == 40, "réglages illisibles : valeurs par défaut")
verifier(150 <= m.PAR_DEFAUT["marge_ms"] <= 250 and m.PAR_DEFAUT["sentence_silence"] > 0, "valeurs par défaut du serveur : marge entre 150 et 250 ms, silence entre phrases")
print()
if echecs:
    print("ÉCHEC : %d vérification(s) en échec." % echecs)
    sys.exit(1)
print("TOUT EST VERT.")
