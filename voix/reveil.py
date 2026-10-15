"""Écoute de VEILLE (faible consommation) : seules deux choses réveillent Jarvis.
  1) la phrase « réveille-toi Jarvis » (Vosk, petit modèle, GRAMMAIRE RESTREINTE : le moteur ne connaît que cette phrase et ses variantes ; il n'est alimenté que quand il y a du son) ;
  2) un DOUBLE CLAQUEMENT de mains : deux pics sonores brefs espacés de 0,2 à 0,8 s (seuil réglable : config.json « claquement_seuil »).
Faux déclenchements évités : un pic isolé, un son long, une série de bruits (applaudissements, frappe au clavier), et tout ce qui se passe PENDANT que Jarvis parle (memoire/parle.flag).
Sortie : « PRET:veille », puis « REVEIL:phrase » ou « REVEIL:claque » (le processus s'arrête aussitôt après : Jarvis rouvre l'écoute normale).
Calibrage : python reveil.py --calibre 5  -> « CALIBRAGE:{json} » : mesure le bruit ambiant et propose un seuil de claquement.
Aucune écriture hors de la sortie standard ; aucun réseau."""
import argparse
import importlib.util
import json
import math
import os
import sys
import time

ici = os.path.dirname(os.path.abspath(__file__))
BLOC_MS = 20          # précision d'un claquement : blocs de 20 ms


_EV = None


def _ecoute():
    global _EV
    if _EV is not None:
        return _EV
    spec = importlib.util.spec_from_file_location("ecoute_commun", os.path.join(ici, "ecoute.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    _EV = m
    return m


class DetecteurClaquements:
    """Double claquement : deux pics BREFS (moins de `duree_max_ms`), espacés (début à début) de `ecart_min_ms` à `ecart_max_ms`, précédés d'un moment calme (`calme_avant_ms`).
    Entrée : le niveau (0 à 100) de chaque bloc de `bloc_ms`. Sortie de bloc() : True au moment du 2e claquement."""

    def __init__(self, seuil=72, duree_max_ms=120, ecart_min_ms=200, ecart_max_ms=800, calme_avant_ms=500, apres_ms=1500, bloc_ms=BLOC_MS):
        self.seuil = seuil
        self.duree_max = duree_max_ms
        self.ecart_min = ecart_min_ms
        self.ecart_max = ecart_max_ms
        self.calme_avant = calme_avant_ms
        self.apres = apres_ms
        self.bloc_ms = bloc_ms
        self.t = 0                    # horloge (ms) : un bloc = bloc_ms
        self.fort_depuis = None       # début du son fort en cours
        self.long = False             # le son fort en cours dépasse déjà la durée d'un claquement
        self.fin_prec = -10 ** 9      # fin du son fort précédent (valide ou non) : sert à exiger un moment calme avant le premier claquement
        self.pic1 = None              # début du premier claquement valide, en attente du second
        self.bloque_jusqu = 0         # pas de détection avant cette heure (parole de Jarvis, déclenchement récent)

    def raz(self):
        self.fort_depuis = None
        self.long = False
        self.pic1 = None

    def bloc(self, niveau, parle=False):
        self.t += self.bloc_ms
        if parle:                                   # Jarvis parle : on ne regarde rien, et un peu après non plus
            self.raz()
            self.bloque_jusqu = self.t + self.apres
            self.fin_prec = self.t
            return False
        fort = niveau >= self.seuil
        if fort:
            if self.fort_depuis is None:
                self.fort_depuis = self.t
            if not self.long and self.t - self.fort_depuis >= self.duree_max:
                self.long = True                    # son trop long pour un claquement (voix, musique, bruit continu)
                self.pic1 = None
            return False
        if self.fort_depuis is None:
            if self.pic1 is not None and self.t - self.pic1 > self.ecart_max:
                self.pic1 = None                    # pic isolé : oublié
            return False
        debut, etait_long = self.fort_depuis, self.long
        self.fort_depuis = None
        self.long = False
        avant = debut - self.fin_prec
        self.fin_prec = self.t                      # (mis à jour pour le son suivant, quel que soit le sort de celui-ci)
        if etait_long or self.t < self.bloque_jusqu:
            return False
        if self.pic1 is None:
            if avant >= self.calme_avant:
                self.pic1 = debut                   # premier claquement valide : on attend le second
            return False
        ecart = debut - self.pic1
        if ecart < self.ecart_min:
            self.pic1 = None                        # pics trop rapprochés (rebond, rafale, frappe au clavier) : ce n'est pas un double claquement, on repart de zéro
            return False
        if ecart <= self.ecart_max:
            self.pic1 = None
            self.bloque_jusqu = self.t + self.apres
            return True                             # DOUBLE CLAQUEMENT
        self.pic1 = debut if avant >= self.calme_avant else None      # trop espacés : le nouveau devient le premier
        return False


def normaliser(texte):
    import unicodedata
    t = unicodedata.normalize("NFD", (texte or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return " ".join("".join(c if (c.isalnum() or c in " '") else " " for c in t.replace("-", " ")).split())


def phrases_grammaire(variantes):
    """Grammaire restreinte de Vosk : « réveille toi <Jarvis> » avec les variantes que le modèle comprend vraiment (config.json mot_activation_variantes)."""
    mots = sorted({v.strip().lower() for v in (variantes or []) if v.strip()} | {"jarvis"})
    res = []
    for v in mots:
        res.append("réveille toi " + v)
    res.append("[unk]")
    return res


def phrase_reveil(texte, variantes=()):
    """True si le texte reconnu est « réveille-toi Jarvis » (ou une variante). Il faut les deux : le verbe ET le mot d'appel (pas de déclenchement sur « Jarvis » seul)."""
    mots = normaliser(texte).split()
    if not mots:
        return False
    verbe = any(m in ("reveille", "reveil", "reveilles") for m in mots)
    if not verbe:
        return False
    ev = _ecoute()
    if variantes:
        ev.VARIANTES = ev.charger_variantes(",".join(variantes))
    return any(ev.est_wake(m) for m in mots)


def calibrer(niveaux, marge=18, plancher=45, plafond=95):
    """Bruit ambiant -> seuil de claquement. niveaux : niveau (0-100) de chaque bloc, mesuré dans le calme. Le seuil se place au-dessus du pic ambiant (99e centile) + une marge."""
    if not niveaux:
        return {"ambiant_moyen": 0, "ambiant_p99": 0, "ambiant_max": 0, "seuil": plancher, "blocs": 0}
    tri = sorted(niveaux)
    p99 = tri[min(len(tri) - 1, int(len(tri) * 0.99))]
    seuil = int(max(plancher, min(plafond, p99 + marge)))
    return {"ambiant_moyen": round(sum(tri) / len(tri), 1), "ambiant_p99": p99, "ambiant_max": tri[-1], "seuil": seuil, "blocs": len(tri)}


class Veille:
    """Un bloc audio de 20 ms à la fois. Retourne 'claque', 'phrase' ou None. Le moteur Vosk (rec) n'est alimenté QUE s'il y a du son (économie de CPU)."""

    def __init__(self, detecteur, rec=None, variantes=(), niveau_voix=30, queue_blocs=12, claquement=True, voix=True):
        self.det = detecteur
        self.rec = rec
        self.variantes = list(variantes)
        self.niveau_voix = niveau_voix
        self.queue_blocs = queue_blocs
        self.queue = 0
        self.alimentes = 0              # nombre de blocs envoyés à Vosk (pour mesurer l'économie)
        self.claquement = claquement
        self.voix = voix

    def bloc(self, d, niveau, parle=False):
        if parle:
            self.det.bloc(niveau, True)
            self.queue = 0
            return None
        if self.claquement and self.det.bloc(niveau, False):
            return "claque"
        if self.voix and self.rec is not None:
            if niveau >= self.niveau_voix:
                self.queue = self.queue_blocs
            if self.queue > 0:
                self.queue -= 1
                self.alimentes += 1
                if self.rec.AcceptWaveform(d):
                    t = json.loads(self.rec.Result()).get("text", "")
                    if t and phrase_reveil(t, self.variantes):
                        return "phrase"
                else:
                    p = json.loads(self.rec.PartialResult()).get("partial", "")
                    if p and phrase_reveil(p, self.variantes):
                        return "phrase"
                if self.queue == 0:
                    t = json.loads(self.rec.FinalResult()).get("text", "")      # fin du son : on finalise
                    if t and phrase_reveil(t, self.variantes):
                        return "phrase"
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--micro", default="")
    ap.add_argument("--variantes", default="")
    ap.add_argument("--modele-chemin", default="")
    ap.add_argument("--seuil", type=float, default=72)
    ap.add_argument("--claque-duree-max", type=int, default=120)
    ap.add_argument("--ecart-min", type=int, default=200)
    ap.add_argument("--ecart-max", type=int, default=800)
    ap.add_argument("--sans-claquement", action="store_true")
    ap.add_argument("--sans-voix", action="store_true")
    ap.add_argument("--calibre", type=float, default=0)
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ev = _ecoute()
    variantes = [v.strip() for v in a.variantes.split(",") if v.strip()]
    try:
        import queue
        import sounddevice as sd
        idx, nom, _ = ev.choisir_micro(a.micro)
        taux = 16000
        q = queue.Queue()
        stream = sd.RawInputStream(samplerate=taux, blocksize=int(taux * BLOC_MS / 1000), dtype="int16", channels=1, device=idx, callback=lambda d, f, t, s: q.put(bytes(d)))
    except Exception as e:
        print("ERREUR:micro " + str(e), file=sys.stderr)
        sys.exit(3)
    if a.calibre > 0:
        niveaux = []
        stream.start()
        fin = time.time() + a.calibre
        while time.time() < fin:
            try:
                niveaux.append(ev.niveau_pct(q.get(timeout=1)))
            except queue.Empty:
                pass
        stream.stop()
        print("CALIBRAGE:" + json.dumps(calibrer(niveaux)), flush=True)
        return
    rec = None
    if not a.sans_voix:
        try:
            from vosk import KaldiRecognizer, Model, SetLogLevel
            SetLogLevel(-1)
            chemin = ev.chemin_modele("vosk", a.modele_chemin)
            rec = KaldiRecognizer(Model(chemin), taux, json.dumps(phrases_grammaire(variantes), ensure_ascii=False))
        except Exception as e:
            print("ERREUR:vosk " + str(e), file=sys.stderr)      # sans Vosk : les claquements restent possibles
    det = DetecteurClaquements(seuil=a.seuil, duree_max_ms=a.claque_duree_max, ecart_min_ms=a.ecart_min, ecart_max_ms=a.ecart_max)
    veille = Veille(det, rec, variantes, claquement=not a.sans_claquement, voix=rec is not None)
    stream.start()
    print("PRET:veille", flush=True)
    while True:
        try:
            d = q.get(timeout=1)
        except queue.Empty:
            continue
        r = veille.bloc(d, ev.niveau_pct(d), ev.parle_en_cours())
        if r:
            print("REVEIL:" + ("claque" if r == "claque" else "phrase"), flush=True)
            return


if __name__ == "__main__":
    main()
