"""Test SILENCIEUX de l'écoute de veille (voix/reveil.py) : double claquement, faux déclenchements, phrase « réveille-toi Jarvis », calibrage. Niveaux sonores SIMULÉS : aucun micro,
aucun son, aucun modèle chargé. Sortie « OK ... » / « ECHEC ... » ; code 0 si tout est vert."""
import importlib.util
import json
import os
import sys

try:
    sys.stdout.reconfigure(errors="replace")
except AttributeError:
    pass
ici = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("reveil", os.path.join(os.path.dirname(ici), "voix", "reveil.py"))
r = importlib.util.module_from_spec(spec)
sys.modules["reveil"] = r
spec.loader.exec_module(r)
echecs = 0


def verifier(cond, msg):
    global echecs
    if cond:
        print("  OK    " + msg)
    else:
        print("  ECHEC " + msg)
        echecs += 1


FORT, CALME, FAIBLE = 90, 20, 65


def jouer(seq, **kw):
    """seq : [(niveau, nombre de blocs de 20 ms, parle?)]. Retourne la liste des index de blocs où un double claquement est détecté."""
    d = r.DetecteurClaquements(**kw)
    res, i = [], 0
    for e in seq:
        niveau, n = e[0], e[1]
        parle = e[2] if len(e) > 2 else False
        for _ in range(n):
            if d.bloc(niveau, parle):
                res.append(i)
            i += 1
    return res


def clap(n=2):
    return (FORT, n)


def calme(ms):
    return (CALME, ms // 20)


print("1) Double claquement : le cas normal")
verifier(len(jouer([calme(1000), clap(), calme(300), clap(), calme(1000)])) == 1, "deux claquements brefs espacés de 0,34 s après un moment calme : détecté (une seule fois)")
verifier(len(jouer([calme(1000), clap(), calme(160), clap(), calme(1000)])) == 1, "espacement de 0,2 s (début à début) : accepté")
verifier(jouer([calme(1000), clap(), calme(140), clap(), calme(1000)]) == [], "espacement de 0,18 s : refusé (rebond / écho)")
verifier(len(jouer([calme(1000), clap(), calme(760), clap(), calme(1000)])) == 1, "espacement de 0,8 s : accepté")
verifier(jouer([calme(1000), clap(), calme(780), clap(), calme(1000)]) == [], "espacement de 0,82 s : refusé (trop lent)")
verifier(len(jouer([calme(1000), clap(1), calme(300), clap(1), calme(500)])) == 1, "claquements très brefs (un seul bloc de 20 ms) : détectés")
verifier(len(jouer([calme(1000), clap(3), calme(300), clap(3), calme(500)])) == 1, "claquements de 60 ms : détectés")
print("2) Faux déclenchements")
verifier(jouer([calme(1000), clap(), calme(3000)]) == [], "un pic isolé : jamais de réveil")
verifier(jouer([calme(1000), clap(), calme(1500), clap(), calme(1500)]) == [], "deux pics isolés espacés de plus de 0,8 s : aucun réveil")
verifier(jouer([calme(1000), (FORT, 10), calme(300), clap(), calme(500)]) == [], "un son LONG (0,2 s : voix, musique) puis un claquement : ignoré")
verifier(jouer([calme(1000), clap(), calme(300), (FORT, 10), calme(1500)]) == [], "un claquement puis un son long : ignoré")
verifier(jouer([calme(1000), (FORT, 200), calme(500)]) == [], "un bruit continu : ignoré")
verifier(jouer([calme(1000), (FAIBLE, 2), calme(300), (FAIBLE, 2), calme(500)]) == [], "des pics sous le seuil (65 pour un seuil de 72) : ignorés")
rafale = [calme(1000)] + [clap(1), calme(120)] * 6 + [calme(1500)]
verifier(jouer(rafale) == [], "une rafale de pics (applaudissements, frappe au clavier) : aucun réveil")
verifier(jouer([calme(1000), clap(1), calme(120), clap(1), calme(120), clap(1), calme(500)]) == [], "trois pics rapprochés (0,14 s) : aucun réveil")
verifier(jouer([(FORT, 10), calme(200), clap(), calme(300), clap(), calme(500)]) == [], "claquements juste après un autre bruit (moins de 0,5 s de calme avant) : ignorés")
verifier(len(jouer([calme(1000), clap(), calme(300), clap(), calme(300), clap(), calme(300), clap(), calme(2000)])) == 1, "quatre claquements de suite : un seul réveil (délai de 1,5 s après un déclenchement)")
verifier(len(jouer([calme(1000), clap(), calme(300), clap(), calme(2000), clap(), calme(300), clap(), calme(500)])) == 2, "deux doubles claquements séparés de plus de 1,5 s : deux réveils")
print("3) Pendant que Jarvis parle")
verifier(jouer([calme(1000), (CALME, 30, True), (FORT, 2, True), (CALME, 15, True), (FORT, 2, True), (CALME, 50, True), calme(100)]) == [], "claquements pendant que Jarvis parle (parle.flag) : ignorés")
verifier(jouer([calme(500), (CALME, 10, True), calme(200), clap(), calme(300), clap(), calme(500)]) == [], "claquements dans la seconde et demie qui suit la parole : ignorés")
verifier(len(jouer([calme(500), (CALME, 10, True), calme(2000), clap(), calme(300), clap(), calme(500)])) == 1, "…puis de nouveau détectés quand Jarvis s'est tu depuis plus de 1,5 s")
verifier(jouer([calme(1000), clap(), (CALME, 5, True), calme(100), clap(), calme(500)]) == [], "premier claquement, puis Jarvis parle : le premier est oublié")
print("4) Seuil réglable")
verifier(len(jouer([calme(1000), (80, 2), calme(300), (80, 2), calme(500)], seuil=75)) == 1 and jouer([calme(1000), (80, 2), calme(300), (80, 2), calme(500)], seuil=85) == [], "seuil 75 : des claquements à 80 passent ; seuil 85 : non")
d = r.DetecteurClaquements()
verifier(d.seuil == 72 and d.duree_max == 120 and d.ecart_min == 200 and d.ecart_max == 800, "valeurs par défaut : seuil 72, claquement de 120 ms au plus, écart de 0,2 à 0,8 s")
verifier(len(jouer([calme(1000), (FORT, 8), calme(300), (FORT, 8), calme(500)], duree_max_ms=200)) == 1 and jouer([calme(1000), (FORT, 8), calme(300), (FORT, 8), calme(500)]) == [], "durée maximale d'un claquement réglable (200 ms accepte un son de 0,16 s ; 120 ms le refuse)")

print("5) Phrase « réveille-toi Jarvis » (grammaire restreinte)")
for t in ("réveille-toi Jarvis", "Réveille toi jarvis", "reveille toi Jarvis", "réveille toi gervais", "Jarvis réveille-toi", "réveille-toi, Jarvis !"):
    verifier(r.phrase_reveil(t), "« %s » réveille" % t)
for t in ("Jarvis", "réveille-toi", "réveille-moi demain", "bonjour Jarvis", "ouvre chrome", "", "réveille toi service", "jardin réveille"):
    verifier(not r.phrase_reveil(t), "« %s » ne réveille PAS" % t)
verifier(r.phrase_reveil("réveille toi harvis", ["harvis"]) and not r.phrase_reveil("réveille toi xyz", ["harvis"]), "les variantes du mot d'éveil de config.json sont prises en compte")
g = r.phrases_grammaire(["gervais", "harvis"])
verifier("réveille toi jarvis" in g and "réveille toi gervais" in g and "réveille toi harvis" in g and g[-1] == "[unk]" and len(g) == 4, "grammaire Vosk : uniquement « réveille toi <variante> » + [unk] (le moteur ne connaît rien d'autre)")


class FauxRec:
    def __init__(self, final="", partiel=""):
        self.final, self.partiel, self.recus = final, partiel, 0

    def AcceptWaveform(self, d):
        self.recus += 1
        return bool(self.final) and self.recus % 4 == 0

    def Result(self):
        return json.dumps({"text": self.final})

    def PartialResult(self):
        return json.dumps({"partial": self.partiel})

    def FinalResult(self):
        return json.dumps({"text": self.final})


print("6) Faible consommation : le moteur vocal n'est alimenté que s'il y a du son")
rec = FauxRec()
v = r.Veille(r.DetecteurClaquements(), rec, [], claquement=False)
for _ in range(500):
    v.bloc(b"\x00" * 640, 10)
verifier(v.alimentes == 0 and rec.recus == 0, "10 secondes de silence : AUCUN bloc envoyé au moteur vocal")
v.bloc(b"x", 60)
for _ in range(40):
    v.bloc(b"\x00", 10)
verifier(0 < v.alimentes <= 13, "un bruit de 20 ms : le moteur reçoit ce bruit et une courte queue (%d blocs sur 41), puis plus rien" % v.alimentes)
rec = FauxRec(final="réveille toi jarvis")
v = r.Veille(r.DetecteurClaquements(), rec, [], claquement=False)
res = [v.bloc(b"x", 60) for _ in range(10)]
verifier("phrase" in res, "la phrase reconnue par le moteur déclenche le réveil (« phrase »)")
rec = FauxRec(final="bonjour jarvis")
v = r.Veille(r.DetecteurClaquements(), rec, [], claquement=False)
verifier(all(v.bloc(b"x", 60) is None for _ in range(10)) and all(v.bloc(b"x", 10) is None for _ in range(20)), "une autre phrase (« bonjour Jarvis ») : aucun réveil")
rec = FauxRec(partiel="réveille toi jarvis")
v = r.Veille(r.DetecteurClaquements(), rec, [], claquement=False)
verifier(v.bloc(b"x", 60) == "phrase", "le résultat partiel suffit : réaction immédiate")
rec = FauxRec(partiel="réveille toi jarvis")
v = r.Veille(r.DetecteurClaquements(), rec, [], claquement=False)
verifier(v.bloc(b"x", 60, parle=True) is None and rec.recus == 0, "pendant que Jarvis parle : le moteur vocal n'écoute pas (pas d'auto-réveil par sa propre voix)")
v = r.Veille(r.DetecteurClaquements(), None, [], claquement=True, voix=False)
res = [v.bloc(b"x", n) for n in [20] * 50 + [90, 90] + [20] * 15 + [90, 90] + [20] * 5]
verifier("claque" in res, "la veille renvoie « claque » pour un double claquement")

print("7) Calibrage du bruit ambiant")
c = r.calibrer([30] * 250)
verifier(c["seuil"] == 48 and c["ambiant_max"] == 30 and c["blocs"] == 250, "pièce calme (niveau 30) : seuil 48 -> remonté au plancher utile 48 (18 de marge)")
c = r.calibrer([30] * 245 + [85] * 2 + [30] * 3)
verifier(c["seuil"] <= 60 and c["ambiant_max"] == 85, "un pic isolé pendant la mesure ne fait pas monter le seuil (99e centile)")
c = r.calibrer([30] * 100 + [60] * 150)
verifier(c["seuil"] == 78, "pièce bruyante (ventilateur, musique à 60) : seuil 78")
verifier(r.calibrer([90] * 300)["seuil"] == 95 and r.calibrer([5] * 300)["seuil"] == 45 and r.calibrer([])["seuil"] == 45, "bornes : plafond 95, plancher 45, mesure vide : plancher")
src = open(os.path.join(os.path.dirname(ici), "voix", "reveil.py"), encoding="utf-8").read()
verifier('"--calibre"' in src and '"--seuil"' in src and '"--ecart-min"' in src and '"--ecart-max"' in src and "REVEIL:" in src and "PRET:veille" in src and "CALIBRAGE:" in src, "options et sorties du processus : --seuil, --ecart-min, --ecart-max, --calibre ; PRET:veille, REVEIL:phrase|claque, CALIBRAGE:")
verifier("print(" in src and "open(" not in src.replace("importlib", "") and "socket" not in src and "requests" not in src, "aucune écriture de fichier, aucun réseau")
print()
if echecs:
    print("ÉCHEC : %d vérification(s) en échec." % echecs)
    sys.exit(1)
print("TOUT EST VERT.")
