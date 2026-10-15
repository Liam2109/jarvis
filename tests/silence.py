"""Test SILENCIEUX de la fin de phrase (voix/ecoute.py, MoteurWhisper.bloc) : aucun micro, aucun son, aucun modèle chargé.
Des blocs de 0,1 s simulés (voix = bloc fort, silence = bloc nul) sont envoyés au moteur ; on regarde QUAND la phrase est fermée.
Sortie : « OK ... » / « ECHEC ... » ; code 0 si tout est vert."""
import array
import importlib.util
import json
import os
import sys

ici = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("ecoute", os.path.join(os.path.dirname(ici), "voix", "ecoute.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

TAUX = 16000
VOIX = array.array("h", [9000, -9000] * (TAUX // 10 // 2)).tobytes()      # bloc de 0,1 s bien au-dessus du seuil
SILENCE = b"\x00\x00" * (TAUX // 10)
BRUIT_FAIBLE = array.array("h", [40, -40] * (TAUX // 10 // 2)).tobytes()   # ventilateur, pièce calme : sous le seuil = du silence
echecs = 0


def verifier(cond, msg):
    global echecs
    if cond:
        print("  OK    " + msg)
    else:
        print("  ECHEC " + msg)
        echecs += 1


class Gram:
    """Faux reconnaisseur Vosk : PartialResult renvoie le texte partiel fixé par le test."""
    def __init__(self): self.partiel = ""
    def AcceptWaveform(self, d): return False
    def PartialResult(self): return json.dumps({"partial": self.partiel})


def moteur(partiel="", fin=1.5, courte=0.6, maxp=30.0):
    e = m.MoteurWhisper.__new__(m.MoteurWhisper)
    e.seuil = 32; e.bloc_s = 0.1; e.vad = True; e.appareil = "cpu"
    e.fin = int(round(fin / 0.1)); e.fin_silence = fin; e.max_blocs = int(maxp / 0.1)
    e.fin_courte = max(1, min(e.fin, int(round(courte / 0.1))))
    e.buf = []; e.parle = False; e.silence = 0; e.voix = 0; e.dernier_fort = 0.0; e.infos = {}
    e.phrases = {"ouvre chrome", "jarvis ouvre chrome", "baisse la musique"}; e.conf_min = 0.85
    e.gram = Gram(); e.gram.partiel = partiel
    e.appels = 0
    def transcrire(): e.appels += 1; return "texte reconnu"
    e.transcrire = transcrire
    e._essai_grammaire = lambda: (partiel if partiel in e.phrases else None)
    return e


def jouer(e, scenario):
    """scenario : liste de (type, nombre de blocs), type 'v' voix, 's' silence, 'b' bruit faible. Retourne [(index du bloc, texte)] des phrases fermées."""
    sorties = []; i = 0
    for t, n in scenario:
        for _ in range(n):
            bloc = VOIX if t == "v" else (BRUIT_FAIBLE if t == "b" else SILENCE)
            texte, _ = e.bloc(bloc)
            if texte is not None: sorties.append((i, texte))
            i += 1
    return sorties


verifier(m.niveau_pct(VOIX) >= 32 and m.niveau_pct(SILENCE) < 32 and m.niveau_pct(BRUIT_FAIBLE) < 32, "le simulateur : voix > seuil, silence et bruit faible < seuil")

print("1) Phrase longue avec pauses : jamais coupée à la première respiration")
r = jouer(moteur(), [("v", 30), ("s", 12), ("v", 30), ("s", 20)])
verifier(len(r) == 1 and r[0][0] == 30 + 12 + 30 + 15 - 1, f"pause de 1,2 s au milieu : UNE seule phrase, fermée 1,5 s après la fin ({r})")
r = jouer(moteur(), [("v", 30), ("s", 14), ("v", 30), ("s", 20)])
verifier(len(r) == 1, "pause de 1,4 s au milieu : toujours une seule phrase")
r = jouer(moteur(), [("v", 30), ("s", 16), ("v", 30), ("s", 20)])
verifier(len(r) == 2 and r[0][0] == 30 + 15 - 1, "pause de 1,6 s : la phrase est bien fermée (1,5 s de silence)")
r = jouer(moteur(), [("v", 20), ("s", 14), ("v", 20), ("s", 14), ("v", 20), ("s", 14), ("v", 20), ("s", 20)])
verifier(len(r) == 1, "trois pauses de 1,4 s : toujours une seule phrase (dictée lente)")

print("2) Bruit de fond et bruits courts")
r = jouer(moteur(), [("v", 20), ("s", 10), ("v", 2), ("s", 10), ("v", 2), ("s", 10), ("v", 20), ("s", 20)])
verifier(len(r) == 1, "claquements de 0,2 s toutes les secondes : ils prolongent la phrase au lieu de la couper")
e = moteur(); r = jouer(e, [("v", 2), ("s", 20)])
verifier(len(r) == 1 and r[0][1] == "" and e.appels == 0, "un claquement isolé (0,2 s) : ignoré, aucune transcription lancée")

print("3) Commandes courtes : réaction rapide")
e = moteur(partiel="ouvre chrome"); r = jouer(e, [("v", 15), ("s", 20)])
verifier(len(r) == 1 and r[0][0] == 15 + 6 - 1, f"commande exacte « ouvre chrome » : fermée après 0,6 s de silence ({r})")
e = moteur(partiel="jarvis ouvre chrome"); r = jouer(e, [("v", 15), ("s", 20)])
verifier(len(r) == 1 and r[0][0] == 15 + 6 - 1, "avec le mot d'éveil (« jarvis ouvre chrome ») : même réaction rapide")
e = moteur(partiel="ouvre"); r = jouer(e, [("v", 15), ("s", 20)])
verifier(len(r) == 1 and r[0][0] == 15 + 15 - 1, "phrase qui n'est PAS une commande exacte : on attend 1,5 s")
e = moteur(partiel="ouvre chrome et puis"); r = jouer(e, [("v", 15), ("s", 20)])
verifier(len(r) == 1 and r[0][0] == 15 + 15 - 1, "commande suivie d'autre chose : on attend 1,5 s")
e = moteur(partiel="ouvre chrome"); r = jouer(e, [("v", 60), ("s", 20)])
verifier(len(r) == 1 and r[0][0] == 60 + 15 - 1, "phrase de plus de 4,5 s de voix, même si le partiel est une commande : on attend 1,5 s")
e = moteur(partiel="ouvre chrome"); e.gram = None; r = jouer(e, [("v", 15), ("s", 20)])
verifier(len(r) == 1 and r[0][0] == 15 + 15 - 1, "sans étage 1 (grammaire absente) : silence long seulement")
e = moteur(partiel="ouvre chrome"); r = jouer(e, [("v", 15), ("s", 5), ("v", 15), ("s", 20)])
verifier(len(r) == 1, "pause de 0,5 s dans une commande : pas de coupure (le seuil court est 0,6 s)")

print("4) Durée maximale d'une phrase")
r = jouer(moteur(), [("v", 400)])
verifier(len(r) >= 1 and r[0][0] == 299, f"40 s de parole continue : coupée à 30 s ({r[:1]})")
r = jouer(moteur(maxp=10.0), [("v", 150)])
verifier(len(r) >= 1 and r[0][0] == 99, "duree_max_phrase_s = 10 : coupée à 10 s")

print("5) Valeurs par défaut du moteur")
import inspect
sig = inspect.signature(m.MoteurWhisper.__init__).parameters
verifier(sig["fin_silence"].default == 1.5 and sig["max_phrase"].default == 30.0 and sig["fin_courte"].default == 0.6, "MoteurWhisper : fin 1,5 s, commande 0,6 s, phrase 30 s")
sig = inspect.signature(m.creer_moteur).parameters
verifier(sig["fin_silence"].default == 1.5 and sig["fin_courte"].default == 0.6 and sig["max_phrase"].default == 30.0, "creer_moteur : mêmes valeurs")
src = open(os.path.join(os.path.dirname(ici), "voix", "ecoute.py"), encoding="utf-8").read()
verifier('"--silence-fin", type=float, default=1.5' in src and '"--silence-courte", type=float, default=0.6' in src and '"--duree-max", type=float, default=30.0' in src, "options de la ligne de commande : --silence-fin, --silence-courte, --duree-max")

print("6) Fin de phrase ADAPTATIVE (vitesse V3)")
def adaptatif(brut, partiel="", fin=1.5, rapide=0.7, **kw):
    e = moteur(partiel=partiel, fin=fin, **kw)
    e.adaptatif = True; e.spec_blocs = 5; e.fin_rapide = max(5, int(round(rapide / 0.1))); e.voix_max_rapide = 80
    e.dernier_brut = ""
    def transcrire():
        e.appels += 1; e.dernier_brut = brut; return m.normaliser_texte(brut)
    e.transcrire = transcrire
    return e

e = adaptatif("Quel temps fait-il demain ?")
r = jouer(e, [("v", 20), ("s", 30)])
verifier(len(r) == 1 and r[0][0] == 20 + 7 - 1, f"question terminée (ponctuation finale) : fermée après 0,7 s de silence au lieu de 1,5 s ({r})")
verifier(e.appels == 1, "…avec UNE seule transcription : l'essai fait pendant le silence est réutilisé")
e = adaptatif("Ouvre Chrome et mets de la musique")
r = jouer(e, [("v", 20), ("s", 30)])
verifier(len(r) == 1 and r[0][0] == 20 + 7 - 1, "commande qui commence par un verbe (« ouvre ... ») : fermeture rapide")
e = adaptatif("Je voudrais que tu me dises ce que")
r = jouer(e, [("v", 20), ("s", 30)])
verifier(len(r) == 1 and r[0][0] == 20 + 15 - 1 and e.appels == 1, "phrase inachevée (finit par « que ») : silence long de 1,5 s, et toujours une seule transcription")
e = adaptatif("Je voudrais savoir,")
r = jouer(e, [("v", 20), ("s", 30)])
verifier(len(r) == 1 and r[0][0] == 20 + 15 - 1, "virgule finale : on attend la suite (1,5 s)")
e = adaptatif("Ouvre Chrome.")
r = jouer(e, [("v", 20), ("s", 4), ("v", 20), ("s", 30)])
verifier(len(r) == 1 and e.appels == 1, "la voix reprend avant 0,5 s : aucune transcription d'essai, une seule phrase")
e = adaptatif("Ouvre Chrome.")
r = jouer(e, [("v", 20), ("s", 6), ("v", 20), ("s", 30)])
verifier(len(r) == 1 and e.appels == 2, "la voix reprend après l'essai : l'essai est JETÉ (annulation propre), une seule phrase finale, retranscrite en entier")
e = adaptatif("Ouvre Chrome.")
r = jouer(e, [("v", 90), ("s", 30)])
verifier(len(r) == 1 and r[0][0] == 90 + 15 - 1 and e.appels == 1, "phrase longue (9 s de voix) : jamais de fermeture rapide, silence long conservé")
e = adaptatif("Je voudrais que")
r = jouer(e, [("v", 20), ("s", 12), ("v", 20), ("s", 30)])
verifier(len(r) == 1 and r[0][0] == 20 + 12 + 20 + 15 - 1, "pause de 1,2 s au milieu d'une phrase inachevée : jamais coupée, une seule phrase (protection conservée)")
e = adaptatif("Ouvre Chrome.")
r = jouer(e, [("v", 20), ("s", 12), ("v", 20), ("s", 30)])
verifier(len(r) == 2, "pause de 1,2 s après une commande COMPLÈTE : la phrase est fermée dès 0,7 s (choix assumé du mode rapide)")
e = adaptatif("Quel temps fait-il demain ?")
e.adaptatif = False
r = jouer(e, [("v", 20), ("s", 30)])
verifier(len(r) == 1 and r[0][0] == 20 + 15 - 1, "fin_adaptative = false : comportement d'avant (1,5 s)")
e = adaptatif("Jarvis")
r = jouer(e, [("v", 8), ("s", 30)])
verifier(len(r) == 1 and r[0][0] == 8 + 7 - 1, "« Jarvis » seul : fermeture rapide (la fenêtre d'ordre s'ouvre)")
e = adaptatif("texte quelconque sans fin claire")
r = jouer(e, [("v", 20), ("s", 30)])
verifier(len(r) == 1 and r[0][0] == 20 + 15 - 1, "phrase libre sans signe de fin : silence long (prudence)")
e = adaptatif("Ouvre Chrome.", fin=1.0)
r = jouer(e, [("v", 20), ("s", 30)])
verifier(len(r) == 1 and r[0][0] <= 20 + 10 - 1, "silence long réglé à 1,0 s : la fermeture rapide n'est jamais plus tardive")
print("   gain : 1,5 s -> 0,7 s de silence = environ 0,8 s de moins sur chaque phrase qui semble terminée, + la reconnaissance déjà faite")
e = adaptatif("Ouvre Chrome.", partiel="ouvre chrome")
r = jouer(e, [("v", 15), ("s", 30)])
verifier(len(r) == 1 and r[0][0] == 15 + 6 - 1, "commande exacte de la liste fermée : toujours 0,6 s (inchangé)")
# heuristique pure
P = {"ouvre chrome"}
verifier(m.phrase_semble_complete("Ouvre Chrome", P) and m.phrase_semble_complete("Quelle heure est-il ?") and m.phrase_semble_complete("Jarvis ouvre le bloc-notes"), "complète : commande connue, question terminée, verbe d'action + objet")
verifier(not m.phrase_semble_complete("Ouvre") and not m.phrase_semble_complete("Je voudrais que") and not m.phrase_semble_complete("Ajoute pain et") and not m.phrase_semble_complete("Rappelle-moi de"), "inachevée : verbe seul, fin sur « que » / « et » / « de »")
verifier(not m.phrase_semble_complete("") and not m.phrase_semble_complete("euh") and not m.phrase_semble_complete("Ouvre chrome,") and not m.phrase_semble_complete("Alors..."), "vide, hésitation, virgule, points de suspension : inachevée")
verifier(m.phrase_semble_complete("Jarvis") and not m.phrase_semble_complete("Jarvis et"), "« Jarvis » seul : complète")
import inspect
sig = inspect.signature(m.MoteurWhisper.__init__).parameters
verifier(m.ADAPTATIF is True and abs(m.FIN_RAPIDE - 0.7) < 1e-9 and "fin_rapide" in sig and "adaptatif" in sig, "valeurs par défaut : adaptatif, fermeture rapide à 0,7 s")
src2 = open(os.path.join(os.path.dirname(ici), "voix", "ecoute.py"), encoding="utf-8").read()
verifier('"--silence-rapide", type=float, default=0.7' in src2 and '"--adaptatif", type=int, default=1' in src2, "options de la ligne de commande : --silence-rapide 0.7, --adaptatif 1")

print()
print("TOUT EST VERT." if not echecs else f"{echecs} échec(s).")
sys.exit(1 if echecs else 0)
