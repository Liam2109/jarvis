"""Test SILENCIEUX de la fenêtre de SUITE de conversation, des hallucinations de Whisper et du seuil de bruit adaptatif (voix/ecoute.py). Aucun micro, aucun son, aucun modèle chargé.
Sortie « OK ... » / « ECHEC ... » ; code 0 si tout est vert."""
import array
import importlib.util
import json
import os
import sys

try:
    sys.stdout.reconfigure(errors="replace")
except AttributeError:
    pass
ici = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("ecoute", os.path.join(os.path.dirname(ici), "voix", "ecoute.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
echecs = 0


def verifier(cond, msg):
    global echecs
    if cond:
        print("  OK    " + msg)
    else:
        print("  ECHEC " + msg)
        echecs += 1


def lignes(sortie, prefixe):
    return [x for x in sortie if x.startswith(prefixe)]


def etat(sortie):
    d = [json.loads(x[5:]) for x in sortie if x.startswith("DIAG:")]
    return d[0]["etat"] if d else ""


print("1) Suite de conversation : « SUIVI: » et non « ORDRE: »")
d = m.Dialogue(8.0, True)
s = d.phrase("jarvis ouvre chrome", 100.0)
verifier(lignes(s, "ORDRE:") == ["ORDRE:ouvre chrome"] and not lignes(s, "SUIVI:"), "avec « Jarvis » : ORDRE (jamais filtré)")
d.reponse_finie(105.0)
verifier(d.fenetre_ouverte(106.0) and d.suivi, "Jarvis a fini de répondre : la fenêtre de suite s'ouvre (8 s), marquée « suite »")
s = d.phrase("c'est incroyable", 107.0)
verifier(lignes(s, "SUIVI:") == ["SUIVI:c'est incroyable"] and not lignes(s, "ORDRE:") and etat(s) == "suivi (fenêtre)", "phrase de la fenêtre de suite : SUIVI (Jarvis décidera si elle compte)")
verifier(not d.suivi and not d.fenetre_ouverte(108.0), "après une phrase, la fenêtre est refermée")
s = d.phrase("wow", 120.0)
verifier(not lignes(s, "SUIVI:") and not lignes(s, "ORDRE:") and etat(s) == "ignoré", "hors fenêtre et sans « Jarvis » : ignoré")
d = m.Dialogue(8.0, True)
d.reponse_finie(1.0)  # (aucun ordre en attente de réponse : rien ne s'ouvre)
verifier(not d.fenetre_ouverte(2.0), "sans ordre précédent, aucune fenêtre ne s'ouvre")
d = m.Dialogue(8.0, True); d.phrase("jarvis ouvre chrome", 100.0); d.reponse_finie(101.0)
s = d.phrase("jarvis", 102.0)
verifier(lignes(s, "ACTIVE") and not d.suivi, "« Jarvis » seul pendant la suite : fenêtre explicite (plus une simple suite)")
s = d.phrase("ouvre youtube", 104.0)
verifier(lignes(s, "ORDRE:") == ["ORDRE:ouvre youtube"] and not lignes(s, "SUIVI:"), "…l'ordre qui suit est un ORDRE normal, jamais filtré")
d = m.Dialogue(8.0, True); d.phrase("jarvis ouvre chrome", 100.0); d.reponse_finie(101.0)
s = d.phrase("jarvis monte le volume", 103.0)
verifier(lignes(s, "ORDRE:") == ["ORDRE:monte le volume"] and not d.suivi, "« Jarvis, ordre » dans la fenêtre de suite : ORDRE")
d = m.Dialogue(8.0, False); d.phrase("jarvis ouvre chrome", 100.0); d.reponse_finie(101.0)
verifier(not d.fenetre_ouverte(102.0), "conversation_continue = false : aucune fenêtre de suite")

print("2) Hallucinations de Whisper (fin de vidéo, sous-titres, boucles)")
for t in ("merci beaucoup d'avoir regardé cette vidéo", "Merci d'avoir regardé !", "n'oubliez pas de vous abonner", "Sous-titrage ST' 501", "Sous-titres réalisés par la communauté d'Amara.org",
          "nassan est logo il est logo il est logo", "non non non n'y pas n'y pas n'y pas n'y pas", "à bientôt pour une nouvelle vidéo"):
    verifier(m.est_hallucination(t), "hallucination reconnue : « %s »" % t)
for t in ("ouvre youtube", "jarvis tu fermes la page", "non non non non", "oui oui oui s'il vous plaît", "ravie de vous retrouver", "merci jarvis", "mets la musique plus fort",
          "ouvre chrome et lance youtube", "merci beaucoup"):
    verifier(not m.est_hallucination(t), "vraie phrase gardée : « %s »" % t)
d = m.Dialogue(8.0, True); d.phrase("jarvis ouvre chrome", 100.0); d.reponse_finie(101.0)
s = d.phrase("merci beaucoup d'avoir regardé cette vidéo", 103.0)
verifier(not lignes(s, "SUIVI:") and not lignes(s, "ORDRE:") and etat(s) == "ignoré" and "hallucination" in json.loads(lignes(s, "DIAG:")[0][5:])["raison"], "dans la fenêtre : ignorée (journal : hallucination probable)")
verifier(d.fenetre_ouverte(104.0), "…et la fenêtre reste ouverte pour la vraie suite")
s = d.phrase("jarvis merci d'avoir regardé cette vidéo", 105.0)
verifier(not m.est_hallucination("jarvis ouvre youtube"), "un ordre normal avec « Jarvis » n'est jamais pris pour une hallucination")


class Seg:
    def __init__(self, texte, nsp, lp):
        self.text = texte; self.no_speech_prob = nsp; self.avg_logprob = lp


txt = m.MoteurWhisper._texte([Seg("ouvre chrome", 0.05, -0.2), Seg("merci d'avoir regardé", 0.9, -1.4), Seg("et youtube", 0.4, -0.3), Seg("incertain mais parlé", 0.8, -0.3)])
verifier(txt == "ouvre chrome et youtube incertain mais parlé", "segments : seuls ceux jugés SANS parole ET peu probables sont écartés (%s)" % txt)

print("3) Seuil de voix adaptatif au bruit de fond")
VOIX = array.array("h", [9000, -9000] * 800).tobytes()
SILENCE = b"\x00\x00" * 1600
niveaux = {a: m.niveau_pct(array.array("h", [a, -a] * 800).tobytes()) for a in (500, 800, 1200, 1800, 2500, 3500, 5000)}
a_tv = min(niveaux, key=lambda a: abs(niveaux[a] - 42))      # bruit continu un peu au-dessus du seuil de 32 (télé, conversation au loin)
TV = array.array("h", [a_tv, -a_tv] * 800).tobytes()
print("        (bruit simulé : niveau %d sur 100, voix : %d)" % (niveaux[a_tv], m.niveau_pct(VOIX)))


class Faux:
    def AcceptWaveform(self, d): return False
    def PartialResult(self): return json.dumps({"partial": ""})


def moteur(adaptatif):
    e = m.MoteurWhisper.__new__(m.MoteurWhisper)
    e.seuil = 32; e.bloc_s = 0.1; e.vad = True; e.appareil = "cpu"; e.fin = 15; e.fin_silence = 1.5; e.max_blocs = 300
    e.fin_courte = 6; e.buf = []; e.parle = False; e.silence = 0; e.voix = 0; e.dernier_fort = 0.0; e.infos = {}
    e.phrases = set(); e.conf_min = 0.85; e.gram = Faux(); e.bruit_adaptatif = adaptatif
    e.transcrire = lambda: "texte"; e._essai_grammaire = lambda: None
    return e


verifier(niveaux[a_tv] > 32, "le bruit simulé est au-dessus du seuil fixe (sinon le test ne prouve rien)")
e = moteur(False)
for _ in range(100): e.bloc(TV)
verifier(e.parle, "seuil FIXE : un bruit continu tient la phrase ouverte après 10 s (le défaut d'avant)")
e = moteur(True)
for _ in range(100): e.bloc(TV)
verifier(not e.parle and e.seuil_effectif() > niveaux[a_tv], "seuil ADAPTATIF : au bout de 10 s le bruit n'est plus pris pour de la voix (seuil relevé à %.0f)" % e.seuil_effectif())
phrases = []
for _ in range(30):
    t, _ = e.bloc(VOIX)
    if t is not None: phrases.append(t)
for _ in range(30):
    t, _ = e.bloc(TV)
    if t is not None: phrases.append(t)
verifier(phrases == ["texte"], "…et une vraie voix PAR-DESSUS le bruit est toujours entendue (une phrase, fermée après 1,5 s)")
e = moteur(True)
for _ in range(100): e.bloc(SILENCE)
verifier(e.seuil_effectif() == 32, "pièce calme : le seuil reste celui du réglage (32)")
e = moteur(True); e.ambiant = 95.0
verifier(e.seuil_effectif() == 32 + e.plafond_bruit, "plafonné : jamais plus de %d points au-dessus du réglage" % e.plafond_bruit)
e = moteur(True)
for _ in range(10): e.bloc(TV)
verifier(e.seuil_effectif() == 32, "moins de 2 s de mesure : pas encore d'adaptation")
verifier(m.MoteurWhisper.bruit_adaptatif is True, "adaptatif par défaut")
src = open(os.path.join(os.path.dirname(ici), "voix", "ecoute.py"), encoding="utf-8").read()
verifier('"--bruit-adaptatif"' in src and "MoteurWhisper.bruit_adaptatif = bool(a.bruit_adaptatif)" in src, "option --bruit-adaptatif (0 = seuil fixe)")
verifier('startswith(("ORDRE:", "SUIVI:"))' in src, "le mode « une écoute ponctuelle » s'arrête aussi sur un SUIVI")
print()
if echecs:
    print("ÉCHEC : %d vérification(s) en échec." % echecs)
    sys.exit(1)
print("TOUT EST VERT.")
