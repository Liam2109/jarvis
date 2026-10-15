"""Écoute locale (Vosk).
Mode ponctuel : python ecoute.py [--timeout 60]  -> imprime "ORDRE:<texte>" puis quitte (code 2 si rien, 3 si Vosk/micro indisponible)
Mode continu  : python ecoute.py --continu       -> imprime en boucle :
    ENTENDU:<texte>   toute phrase reconnue (sert aux réponses oui/non)
    DIAG:<json>       diagnostic de chaque phrase : texte brut, mot d'éveil oui/non, état (ordre / fenêtre ouverte / ignoré + raison)
    ORDRE:<texte>     phrase précédée du mot d'activation, ou phrase suivant "Jarvis" seul dans les --fenetre secondes (8 par défaut), sans répéter le mot
    ACTIVE            "Jarvis" seul entendu : la fenêtre d'ordre est ouverte
    MOTEUR:<nom>      moteur de reconnaissance utilisé (--moteur vosk | vosk-grand | faster-whisper) ; MOTEUR_REPLI:... si le moteur demandé est impossible
    STOP              "Jarvis stop" détecté : crée aussitôt memoire/STOP.flag
Test sur fichier : python ecoute.py --fichier x.wav
Micros          : python ecoute.py --liste                 -> liste les entrées audio
Test du micro   : python ecoute.py --test-micro 20 [--micro NOM]  -> niveau en direct + "J'ai entendu : ..." (aucune action)
Diagnostic mots : python ecoute.py --test-micro 60 --detail   -> pour chaque phrase : texte brut + verdict mot par mot (aucune action)
Options         : --variantes "a,b,c" (variantes exactes du mot d'éveil, config.json "mot_activation_variantes"), --micro NOM (sous-chaîne du nom du périphérique, config.json "micro_nom"), --seuil 0.65 (ressemblance minimale avec "Jarvis")
En mode continu, imprime aussi  MICRO:<nom>  au départ puis  NIVEAU:<0-100>  (niveau du micro en direct).
Pendant que Jarvis parle (memoire/parle.flag), seuls les STOP sont pris en compte."""
import sys, os, json, time, queue, argparse, wave, difflib, re, warnings
warnings.filterwarnings("ignore")
try:
    import audioop
except Exception:          # Python >= 3.13 : calcul du niveau sans audioop
    audioop = None
import array
ici = os.path.dirname(os.path.abspath(__file__))
racine = os.path.dirname(ici)
FLAG_STOP = os.path.join(racine, "memoire", "STOP.flag")
FLAG_PARLE = os.path.join(racine, "memoire", "parle.flag")
FLAG_SOURDINE = os.path.join(racine, "memoire", "sourdine.flag")   # présent = sourdine : on ne rapporte plus que "Jarvis stop"
WAKE = ["jarvis", "jarvisse", "jarvice", "jarvie", "jarvez", "jarvès", "jarvil", "jarvy", "jarvais", "jarviss", "jarbis", "jarvit",
        "gervais", "gervis", "jervis", "charvis", "charvais", "jar vis"]
SEUIL = 0.65     # ressemblance minimale avec un des mots ci-dessus (0.8 auparavant : « Jarvis » était souvent manqué)
STOPS = {"stop", "stoppe", "stoppez", "stoppes", "stope"}
# Variantes EXACTES acceptées telles que Vosk les écrit (config.json "mot_activation_variantes", option --variantes) : ce que le modèle
# français comprend vraiment quand on dit « Jarvis » (ex. « varices », « gervais »). Elles passent sans garde-fou de forme, mais seulement mot entier.
VARIANTES = {"jarvis", "gervais", "gervaise", "varices", "varice", "harvey", "jarvice", "jarvès", "jarvi", "harvis"}

def charger_variantes(texte):
    """'a, b,c' -> ensemble {'a','b','c'} (minuscules). Texte vide : on garde la liste par défaut."""
    mots = {m.strip().lower() for m in re.split(r"[,;]", texte or "") if m.strip()}
    return mots or set(VARIANTES)

def analyser_wake(mot):
    """Retourne la raison pour laquelle le mot déclenche « Jarvis » (ou None). Garde-fous de forme pour le flou, pour ne pas confondre avec
    « service », « jardin », « arrive », « paris »… : 4 à 9 lettres, initiale j / g / y / ch, et la suite « rv » (ou « rb »)."""
    if mot in VARIANTES: return "variante exacte"
    if not (4 <= len(mot) <= 9): return None
    if not (mot[0] in "jgy" or mot.startswith("ch")): return None
    if "rv" not in mot and "rb" not in mot: return None
    for w in WAKE:
        r = difflib.SequenceMatcher(None, mot, w).ratio()
        if r >= SEUIL: return f"ressemble à « {w} » ({r:.2f})"
    return None

def est_wake(mot):
    return analyser_wake(mot) is not None

def niveau_pct(d):
    """Niveau sonore 0-100 d'un bloc int16 (échelle logarithmique : une voix normale tombe vers 40-80)."""
    try:
        rms = audioop.rms(d, 2) if audioop else int((sum(x * x for x in array.array("h", d)) / max(1, len(d) // 2)) ** 0.5)
    except Exception:
        return 0
    if rms <= 0: return 0
    import math
    db = 20 * math.log10(rms / 32768.0)            # 0 dB = pleine échelle
    return max(0, min(100, int((db + 70) / 70 * 100)))

def lister_micros():
    import sounddevice as sd
    sortie = []
    for i, d in enumerate(sd.query_devices()):
        if d.get("max_input_channels", 0) > 0:
            sortie.append((i, d["name"], int(d.get("default_samplerate", 16000))))
    return sortie

def choisir_micro(nom):
    """Retourne (index ou None, nom affiché, trouvé). nom vide = micro par défaut de Windows."""
    import sounddevice as sd
    if nom:
        n = nom.lower().strip()
        c = [m for m in lister_micros() if n in m[1].lower()]
        if c:
            return c[0][0], c[0][1], True
        return None, nom, False
    try:
        d = sd.query_devices(kind="input")
        return None, d["name"], True
    except Exception:
        return None, "", True

FILLERS = {"hey", "ok", "dis", "salut", "bonjour", "eh", "ah", "oh", "hé", "allo", "allô"}   # mots d'appel qui précèdent parfois « Jarvis »

def positions_wake(mots):
    """[(indice, largeur, mot)] des endroits où « Jarvis » est reconnu. Un mot seul, ou DEUX mots collés (« jar vis », « j'ai vis »)
    quand la voix est peu articulée : le modèle coupe alors « Jarvis » en deux."""
    res = []
    i = 0
    while i < len(mots):
        if est_wake(mots[i]):
            res.append((i, 1, mots[i])); i += 1; continue
        if i + 1 < len(mots):
            bi = (mots[i] + mots[i + 1]).replace("'", "").replace("-", "")
            if est_wake(bi):
                res.append((i, 2, bi)); i += 2; continue
        i += 1
    return res

MAX_MOTS_FIN = 6      # « Jarvis » en FIN de phrase n'est valable que si la phrase fait 6 mots ou moins (« ouvre Chrome, Jarvis »)

def diagnostiquer_wake(texte):
    """Où est « Jarvis » dans la phrase, et compte-t-il ? Retourne {"mot", "ordre", "valide", "raison"}.
    Le mot d'éveil n'est valable que : (a) en DÉBUT de phrase (« Jarvis, <ordre> », éventuellement après « hey / ok… »), (b) SEUL dans la phrase
    (une fenêtre d'ordre s'ouvre), (c) en FIN de phrase UNIQUEMENT si la phrase fait 6 mots ou moins. Au milieu, ou en fin d'une phrase plus longue
    (« … de créer les jarvis »), il ne déclenche rien : une conversation ou une vidéo ne doit pas réveiller Jarvis."""
    mots = texte.split()
    pos = positions_wake(mots)
    if not pos: return {"mot": "", "ordre": None, "valide": False, "raison": "pas de mot d'éveil"}
    for i, w, mot in pos:                                      # (a) / (b) début de phrase (les mots d'appel « hey, ok… » ne comptent pas)
        if all(m in FILLERS for m in mots[:i]):
            return {"mot": mot, "ordre": " ".join(mots[i + w:]), "valide": True, "raison": ""}
    i, w, mot = pos[-1]
    if i + w == len(mots):                                     # (c) fin de phrase
        if len(mots) <= MAX_MOTS_FIN:
            return {"mot": mot, "ordre": " ".join(m for m in mots[:i] if m not in FILLERS), "valide": True, "raison": ""}
        return {"mot": mot, "ordre": None, "valide": False, "raison": f"mot trouvé (« {mot} ») mais phrase trop longue ({len(mots)} mots ; en fin de phrase, {MAX_MOTS_FIN} mots au plus)"}
    return {"mot": mot, "ordre": None, "valide": False, "raison": f"mot trouvé (« {mot} ») mais pas en début de phrase"}

def trouver_wake(texte):
    """(mot reconnu, ordre) ; (None, None) si le mot d'éveil est absent OU n'est pas à une place valable (voir diagnostiquer_wake).
    ordre == "" : « Jarvis » seul (une fenêtre d'ordre s'ouvre)."""
    d = diagnostiquer_wake(texte)
    return (d["mot"], d["ordre"]) if d["valide"] else (None, None)

def extraire(texte):
    """Retourne l'ordre (peut être '') si le mot d'activation est présent, sinon None."""
    return trouver_wake(texte)[1]

def est_stop(texte):
    mots = texte.split()
    for i, w, mot in positions_wake(mots):
        if any(x in STOPS for x in mots[i + w:i + w + 2]): return True
    return False

def poser_stop():
    try:
        os.makedirs(os.path.dirname(FLAG_STOP), exist_ok=True)
        with open(FLAG_STOP, "w") as f: f.write(str(time.time()))
    except Exception:
        pass

def parle_en_cours():
    try:
        return os.path.exists(FLAG_PARLE) and time.time() - os.path.getmtime(FLAG_PARLE) < 120
    except Exception:
        return False

# ---------- Dialogue : mot d'éveil, fenêtre d'ordre, diagnostic ----------
class Dialogue:
    """Décide, pour chaque phrase finale, ce qui est envoyé à Jarvis. Pur (aucun micro) : testé avec des phrases simulées.
    Lignes produites : ENTENDU:<texte>  DIAG:<json>  ORDRE:<texte>  ACTIVE.
    Fenêtre d'ordre : après « Jarvis » seul, l'ordre suivant est accepté pendant `fenetre` secondes SANS répéter le mot ; si la personne a COMMENCÉ à parler
    dans la fenêtre (résultat partiel), la phrase est acceptée même si elle se termine après."""
    def __init__(self, fenetre=8.0, continu=True):
        self.fenetre = fenetre; self.attend_jusqua = 0.0; self.parole_fenetre = False; self.n = 0
        self.continu = continu; self.apres_ordre = 0.0          # conversation continue : heure du dernier ordre transmis (0 = aucun en attente de réponse)

    def reponse_finie(self, maintenant):
        """Jarvis vient de finir de parler : si c'était la réponse à un ordre (dans les 90 s), la fenêtre d'ordre se rouvre `fenetre` s, SANS mot d'éveil."""
        if self.continu and self.apres_ordre and maintenant - self.apres_ordre < 90:
            self.attend_jusqua = maintenant + self.fenetre; self.parole_fenetre = False
        self.apres_ordre = 0.0

    def fenetre_ouverte(self, maintenant):
        return maintenant < self.attend_jusqua

    def partiel(self, texte, maintenant):
        if texte and self.fenetre_ouverte(maintenant): self.parole_fenetre = True

    def phrase(self, t, maintenant, ecoute_ordres=True, sourdine=False):
        self.n += 1
        dw = diagnostiquer_wake(t)
        mot, ordre = (dw["mot"], dw["ordre"]) if dw["valide"] else (None, None)
        diag = {"id": self.n, "tps": getattr(self, "infos", {}), "brut": t, "wake": mot is not None, "mot": dw["mot"], "ordre": ordre or "", "raison_wake": dw["raison"]}
        if not ecoute_ordres:
            diag["etat"] = "ignoré"; diag["raison"] = "sourdine" if sourdine else "Jarvis parle (micro coupé pendant sa voix)"
            return ["DIAG:" + json.dumps(diag, ensure_ascii=False)]
        sortie = ["ENTENDU:" + t]
        if ordre:                                           # « Jarvis, <ordre> » dans la même phrase
            diag["etat"] = "ordre"; self.attend_jusqua = 0.0; self.parole_fenetre = False
            self.apres_ordre = maintenant
            sortie += ["DIAG:" + json.dumps(diag, ensure_ascii=False), "ORDRE:" + ordre]
        elif ordre == "":                                   # « Jarvis » seul : la fenêtre d'ordre s'ouvre
            diag["etat"] = "fenêtre ouverte"; diag["raison"] = f"j'écoute l'ordre pendant {self.fenetre:g} s, sans répéter « Jarvis »"
            self.attend_jusqua = maintenant + self.fenetre; self.parole_fenetre = False
            sortie += ["DIAG:" + json.dumps(diag, ensure_ascii=False), "ACTIVE"]
        elif self.fenetre_ouverte(maintenant) or self.parole_fenetre:
            diag["etat"] = "ordre (fenêtre)"; diag["ordre"] = t; self.attend_jusqua = 0.0; self.parole_fenetre = False; self.apres_ordre = maintenant
            sortie += ["DIAG:" + json.dumps(diag, ensure_ascii=False), "ORDRE:" + t]
        else:
            diag["etat"] = "ignoré"; diag["raison"] = (dw["raison"] or "pas de mot d'éveil") + (" (fenêtre d'ordre refermée)" if self.attend_jusqua else "")
            sortie += ["DIAG:" + json.dumps(diag, ensure_ascii=False)]
        return sortie

# ---------- Moteurs de reconnaissance (config.json "moteur_voix") ----------
# "vosk" (défaut) : petit modèle français, voix\models\vosk-model-small-fr-0.22 (41 Mo).
# "vosk-grand"    : vosk-model-fr-0.22 (1,4 Go) à placer dans voix\models\ — NON téléchargé par Jarvis.
# "faster-whisper": modèle local voix\models\faster-whisper-<taille> (config.json "whisper_modele") — NON téléchargé par Jarvis (local_files_only).
# Si le moteur demandé est impossible (paquet ou modèle absent), on RETOMBE sur "vosk" et on le dit (MOTEUR_REPLI:...). Rien n'est installé ni téléchargé.
DOSSIERS_MODELES = {"vosk": "vosk-model-small-fr-0.22", "vosk-grand": "vosk-model-fr-0.22"}

def chemin_modele(moteur, chemin_cfg="", taille_whisper="small"):
    base = os.path.join(ici, "models")
    if chemin_cfg:
        return chemin_cfg if os.path.isabs(chemin_cfg) else os.path.join(base, chemin_cfg)
    if moteur == "faster-whisper": return os.path.join(base, "faster-whisper-" + (taille_whisper or "small"))
    return os.path.join(base, DOSSIERS_MODELES.get(moteur, DOSSIERS_MODELES["vosk"]))

# ---------- Fin de phrase ADAPTATIVE (vitesse V3) ----------
# Le silence de fin long (1,5 s) protège les phrases inachevées mais coûte ~1 s sur chaque phrase libre. Pendant la demi-seconde qui suit la fin de la voix, une transcription
# d'essai est faite ; si elle ressemble à une phrase TERMINÉE (commande connue, ponctuation finale, question complète), la phrase est fermée après `fin_rapide` (0,7 s) et
# CETTE transcription est réutilisée (la reconnaissance est déjà faite). Si la phrase semble inachevée (finit par « et », « de », « que »...), on attend 1,5 s comme avant ;
# si la voix reprend, l'essai est jeté. Une phrase longue (plus de 8 s de voix) garde toujours le silence long.
ADAPTATIF = True
FIN_RAPIDE = 0.7
MOTS_INCOMPLETS = {"et", "ou", "de", "du", "des", "le", "la", "les", "un", "une", "à", "au", "aux", "pour", "que", "qui", "quoi", "mais", "donc", "alors", "puis", "euh", "heu", "hum", "avec",
                   "dans", "sur", "sans", "comme", "en", "mon", "ma", "mes", "ton", "ta", "tes", "ce", "cette", "ces", "si", "quand", "parce", "car", "ni", "or", "dis", "tu", "je", "il", "elle", "on"}
VERBES_COMMANDE = {"ouvre", "ouvrez", "ferme", "fermez", "mets", "mettez", "met", "baisse", "monte", "coupe", "lance", "lis", "dis", "donne", "montre", "affiche", "active", "désactive", "desactive",
                   "passe", "note", "ajoute", "rappelle", "cherche", "trouve", "fais", "démarre", "demarre", "verrouille", "réduis", "reduis", "range", "règle", "regle", "éteins", "eteins", "redémarre",
                   "sourdine", "arrête", "arrete", "annule", "relis", "résume", "resume", "explique", "détaille", "detaille", "prépare", "prepare", "envoie", "supprime", "déplace", "deplace"}
INTERROGATIFS = {"quel", "quelle", "quels", "quelles", "quand", "combien", "comment", "pourquoi", "où", "ou", "est-ce", "qu'est-ce", "qui", "qu'est", "peux-tu", "peux", "pourrais-tu", "as-tu"}


def phrase_semble_complete(brut, phrases=()):
    """True si la transcription (texte brut de Whisper, avec sa ponctuation) ressemble à une phrase terminée : on peut alors fermer vite. Prudent : dans le doute, False."""
    t = normaliser_texte(brut)
    mots = t.split()
    if not mots:
        return False
    fin = (brut or "").strip()
    if fin.endswith((",", ":", ";", "...", "\u2026", "-")):
        return False
    if mots[-1] in MOTS_INCOMPLETS or mots[-1].endswith("'"):
        return False
    if t in phrases:
        return True
    if fin[-1:] in (".", "?", "!"):
        return True
    reste = mots[1:] if est_wake(mots[0]) else mots
    if not reste:
        return len(mots) == 1                       # « Jarvis » seul : la fenêtre d'ordre s'ouvre, inutile d'attendre
    if reste[0] in VERBES_COMMANDE and len(reste) >= 2:
        return True
    if reste[0] in INTERROGATIFS and len(reste) >= 3:
        return True
    return False


def normaliser_texte(t):
    """Texte de Whisper (majuscules, ponctuation) -> même forme que Vosk : minuscules, sans ponctuation."""
    t = re.sub(r"[^\w\s'’-]", " ", (t or "").lower())
    return re.sub(r"\s+", " ", t.replace("’", "'")).strip()

class MoteurVosk:
    nom = "vosk"
    def __init__(self, chemin, taux):
        from vosk import Model, KaldiRecognizer, SetLogLevel
        SetLogLevel(-1)
        self.rec = KaldiRecognizer(Model(chemin), taux)
    def bloc(self, d):
        """(phrase finale ou None, résultat partiel)"""
        if self.rec.AcceptWaveform(d): return json.loads(self.rec.Result()).get("text", ""), ""
        return None, json.loads(self.rec.PartialResult()).get("partial", "")

def preparer_cuda():
    if os.environ.get("JARVIS_TEST_CUDA_ECHEC"): raise RuntimeError("échec GPU simulé (test)")
    """Bibliothèques CUDA installées par pip (nvidia-cublas-cu12, nvidia-cudnn-cu12) : leurs dossiers bin doivent être connus de Windows avant le chargement du modèle."""
    import site, glob
    bases = list(site.getsitepackages()) + [site.getusersitepackages()]
    for base in bases:
        for d in glob.glob(os.path.join(base, "nvidia", "*", "bin")):
            try:
                os.add_dll_directory(d); os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")
            except Exception:
                pass

class MoteurWhisper:
    """faster-whisper, GARDÉ CHARGÉ tant que ce processus vit (Jarvis actif) : aucun rechargement entre les phrases. Pas de flux continu : le niveau sonore détecte la fin d'une phrase
    (silence de `fin_silence` s, par blocs de 0,1 s), puis UNE transcription locale (beam 1, filtre de voix). GPU (cuda) ou CPU (threads plafonnés) ; si le GPU échoue au chargement
    ou en cours de route, repli automatique sur le CPU. Chargé en `local_files_only` : ne télécharge jamais rien."""
    nom = "faster-whisper"
    adaptatif = False; spec_texte = None; spec_brut = None; spec_complet = False; spec_fait = False; spec_ms = 0; dernier_brut = ""      # valeurs de repli (l'instance les remplace)
    spec_blocs = 5; fin_rapide = 7; voix_max_rapide = 80
    def __init__(self, chemin, taux, peripherique="cpu", seuil_voix=32, fin_silence=1.5, max_phrase=30.0, bloc_s=0.1, prompt="", cpu_threads=3, vad=True, grammaire="", fin_courte=0.6, fin_rapide=None, adaptatif=None):
        self.chemin = chemin; self.taux = taux; self.seuil = seuil_voix; self.bloc_s = bloc_s; self.vad = vad; self.cpu_threads = cpu_threads
        self.fin = max(1, int(round(fin_silence / bloc_s))); self.fin_silence = fin_silence; self.max_blocs = int(max_phrase / bloc_s)
        # Fin de phrase À DEUX VITESSES : longue (fin_silence, 1,5 s par défaut) pour ne jamais couper quelqu'un qui parle longtemps ou qui marque une pause ;
        # courte (fin_courte, 0,6 s) SEULEMENT si ce qui vient d'être dit est déjà, mot pour mot, une commande exacte de la liste fermée (grammaire Vosk).
        self.fin_courte = max(1, min(self.fin, int(round(fin_courte / bloc_s))))
        self.adaptatif = ADAPTATIF if adaptatif is None else bool(adaptatif)
        self.spec_blocs = max(1, int(round(0.5 / bloc_s)))                       # la transcription d'essai part après 0,5 s de silence
        self.fin_rapide = max(self.spec_blocs, min(self.fin, int(round((FIN_RAPIDE if fin_rapide is None else fin_rapide) / bloc_s))))
        self.voix_max_rapide = int(8.0 / bloc_s)                                 # au-delà de 8 s de voix : silence long seulement
        self.spec_texte = None; self.spec_brut = None; self.spec_complet = False; self.spec_fait = False; self.spec_ms = 0; self.dernier_brut = ""
        self.prompt = prompt; self.buf = []; self.parle = False; self.silence = 0; self.voix = 0; self.dernier_fort = 0.0; self.infos = {}; self.repli = ""
        self.appareil = peripherique if peripherique in ("cpu", "cuda") else "cpu"
        self.gram = None; self.phrases = set(); self.conf_min = 0.85
        self._charger()
        self._charger_grammaire(grammaire)
    @property
    def nom_affiche(self): return "faster-whisper/" + self.appareil
    def _charger(self):
        from faster_whisper import WhisperModel
        if self.appareil == "cuda": preparer_cuda()
        kw = dict(device=self.appareil, compute_type=("float16" if self.appareil == "cuda" else "int8"), local_files_only=True)
        if self.appareil == "cpu": kw["cpu_threads"] = max(1, int(self.cpu_threads))
        self.modele = WhisperModel(self.chemin, **kw)
        self._chauffer()
    def _charger_grammaire(self, chemin):
        """Étage 1 (ordres exacts, même mal articulés) : Vosk limité à la liste fermée des commandes (fichier écrit par Jarvis). JAMAIS la seule voie : une phrase hors liste,
        un mot inconnu ([unk]) ou une confiance trop basse passe à faster-whisper."""
        if not chemin or not os.path.isfile(chemin): return
        try:
            from vosk import Model, KaldiRecognizer, SetLogLevel
            SetLogLevel(-1)
            ph = [normaliser_texte(x) for x in json.load(open(chemin, encoding="utf-8-sig")) if isinstance(x, str)]
            ph = sorted(set(x for x in ph if x))
            if not ph: return
            self.phrases = set(ph)
            self.gram = KaldiRecognizer(Model(chemin_modele("vosk")), self.taux, json.dumps(ph + ["[unk]"], ensure_ascii=False))
            self.gram.SetWords(True)
        except Exception:
            self.gram = None; self.phrases = set()
    def _essai_grammaire(self):
        """Texte de l'étage 1 si la phrase est EXACTEMENT une commande de la liste (sans [unk], confiance suffisante), sinon None."""
        if not self.gram: return None
        try:
            r = json.loads(self.gram.FinalResult())
            try: self.gram.Reset()
            except Exception: pass
            txt = normaliser_texte(r.get("text", ""))
            if not txt or "unk" in txt.split() or txt not in self.phrases: return None
            confs = [m.get("conf", 1.0) for m in r.get("result", [])]
            return txt if (not confs or min(confs) >= self.conf_min) else None
        except Exception:
            return None
    def _commande_exacte_en_cours(self):
        """True si le texte partiel de l'étage 1 est EXACTEMENT une commande de la liste fermée (non destructif : PartialResult). Sert à fermer vite une commande courte."""
        if not self.gram or self.voix > 45: return False                      # phrase longue (> ~4,5 s de voix) : on attend la fin de phrase longue
        try:
            txt = normaliser_texte(json.loads(self.gram.PartialResult()).get("partial", ""))
            return bool(txt) and "unk" not in txt.split() and txt in self.phrases
        except Exception:
            return False
    def _chauffer(self):
        """Une transcription à blanc : les noyaux GPU / les caches s'initialisent maintenant, pas pendant votre première phrase."""
        try:
            seg, _ = self.modele.transcribe(self._vers_flottants([b"\x00\x00" * self.taux]), language="fr", beam_size=1)
            list(seg)
        except Exception:
            if self.appareil == "cuda": raise
    def _passer_cpu(self, cause):
        self.appareil = "cpu"; self.repli = f"MOTEUR_REPLI:cuda impossible ({str(cause)[:120]}) -> cpu"
        self._charger()
    def _vers_flottants(self, octets):
        try:
            import numpy as np
            a = np.frombuffer(b"".join(octets), dtype=np.int16).astype(np.float32) / 32768.0
            if self.taux != 16000 and len(a): a = np.interp(np.linspace(0, len(a) - 1, int(len(a) * 16000 / self.taux)), np.arange(len(a)), a).astype(np.float32)
            return a
        except ImportError:
            return [x / 32768.0 for x in array.array("h", b"".join(octets))]
    def transcrire(self):
        audio = self._vers_flottants(self.buf)
        kw = dict(language="fr", beam_size=1, condition_on_previous_text=False, vad_filter=self.vad, initial_prompt=self.prompt or None)
        if self.vad: kw["vad_parameters"] = dict(min_silence_duration_ms=300)
        try:
            segments, _info = self.modele.transcribe(audio, **kw)
            self.dernier_brut = " ".join(s.text for s in segments)
            return normaliser_texte(self.dernier_brut)
        except Exception as e:
            if self.appareil != "cuda": raise
            self._passer_cpu(e)                                  # GPU indisponible (pilote, mémoire prise par un jeu...) : on continue sur le CPU
            segments, _info = self.modele.transcribe(audio, **kw)
            self.dernier_brut = " ".join(s.text for s in segments)
            return normaliser_texte(self.dernier_brut)
    def bloc(self, d):
        adapt = getattr(self, "adaptatif", False)
        if niveau_pct(d) >= self.seuil:
            self.parle = True; self.silence = 0; self.voix += 1; self.buf.append(d); self.dernier_fort = time.time()
            if self.gram: self.gram.AcceptWaveform(d)
            if adapt: self.spec_texte = None; self.spec_complet = False; self.spec_fait = False      # la voix reprend : la transcription d'essai est jetée
        elif self.parle:
            self.silence += 1; self.buf.append(d)
            if self.gram: self.gram.AcceptWaveform(d)
        fin_ok = self.parle and (self.silence >= self.fin or len(self.buf) >= self.max_blocs)
        if adapt and self.parle and not fin_ok and not self.spec_fait and self.silence >= self.spec_blocs and 3 <= self.voix <= self.voix_max_rapide:
            self.spec_fait = True; t1 = time.time()        # transcription d'essai (réutilisée à la fermeture si la voix ne reprend pas)
            self.spec_texte = self.transcrire(); self.spec_brut = getattr(self, "dernier_brut", "") or self.spec_texte; self.spec_ms = int((time.time() - t1) * 1000)
            self.spec_complet = phrase_semble_complete(self.spec_brut, self.phrases)
        if adapt and self.parle and not fin_ok and self.spec_complet and self.silence >= self.fin_rapide: fin_ok = True      # phrase qui semble terminée : fermeture rapide
        if self.parle and not fin_ok and self.silence >= self.fin_courte and self._commande_exacte_en_cours(): fin_ok = True      # commande courte exacte : réaction rapide
        if fin_ok:
            ok = self.voix >= 3                                  # moins de ~0,3 s de voix : un claquement, pas une phrase
            t0 = time.time(); etage = "whisper"; t = ""
            if ok:
                t = self._essai_grammaire() or ""
                if t: etage = "vosk-grammaire"
                elif adapt and self.spec_texte is not None: t = self.spec_texte; etage = "whisper (essai réutilisé)"      # déjà transcrit pendant le silence : aucune attente de plus
                else: t = self.transcrire()
            elif self.gram:
                try: self.gram.FinalResult()
                except Exception: pass
            self.infos = {"silence_ms": int(max(0.0, t0 - self.dernier_fort) * 1000), "reco_ms": int((time.time() - t0) * 1000), "t_emis": time.time(), "appareil": self.appareil, "etage": etage, "adaptatif": bool(adapt), "fin_rapide": bool(adapt and self.spec_complet and self.silence < self.fin), "spec_ms": self.spec_ms}
            self.buf = []; self.parle = False; self.silence = 0; self.voix = 0; self.spec_texte = None; self.spec_complet = False; self.spec_fait = False; self.spec_ms = 0
            return t, ""
        return None, ("…" if self.parle else "")

def creer_moteur(moteur, taux, chemin_cfg="", taille_whisper="small", peripherique="cpu", cpu_threads=3, vad=True, fin_silence=1.5, prompt="", grammaire="", fin_courte=0.6, max_phrase=30.0):
    """(moteur, message) — retombe sur Vosk (petit modèle) avec un message clair si le moteur demandé est impossible. Ne télécharge rien.
    faster-whisper en « cuda » : si le GPU échoue, repli automatique sur « cpu » (message MOTEUR_REPLI)."""
    demande = moteur if moteur in ("vosk", "vosk-grand", "faster-whisper") else "vosk"
    if demande != "vosk":
        ch = chemin_modele(demande, chemin_cfg, taille_whisper)
        try:
            if not os.path.isdir(ch): raise FileNotFoundError(f"modèle absent : {ch} (rien n'est téléchargé : voir README)")
            if demande == "faster-whisper":
                try:
                    return MoteurWhisper(ch, taux, peripherique, fin_silence=fin_silence, cpu_threads=cpu_threads, vad=vad, prompt=prompt, grammaire=grammaire, fin_courte=fin_courte, max_phrase=max_phrase), ""
                except Exception as e:
                    if peripherique != "cuda": raise
                    mo = MoteurWhisper(ch, taux, "cpu", fin_silence=fin_silence, cpu_threads=cpu_threads, vad=vad, prompt=prompt, grammaire=grammaire, fin_courte=fin_courte, max_phrase=max_phrase)
                    return mo, f"MOTEUR_REPLI:cuda impossible ({str(e)[:120]}) -> cpu"
            return MoteurVosk(ch, taux), ""
        except Exception as e:
            msg = f"MOTEUR_REPLI:{demande} impossible ({e}) -> vosk (petit modèle)"
            return MoteurVosk(chemin_modele("vosk"), taux), msg
    return MoteurVosk(chemin_modele("vosk", chemin_cfg if moteur == "vosk" else ""), taux), ""

def charger_prompt(chemin):
    """Indice de vocabulaire pour Whisper (écrit par Jarvis : mots à bien orthographier). Longueur bornée."""
    try:
        t = open(chemin, encoding="utf-8").read().strip()
        return t[:600]
    except Exception:
        return ""

def configurer_sortie(forcer=False):
    """Sortie en UTF-8 quand elle est lue par Jarvis (tube). Sans cela Python écrit en cp1252 sous Windows et PowerShell (qui lit de l'UTF-8) reçoit
    « � » à la place de é, à, è… : « mets le volume à 30 » ou « règle … » ne correspondaient plus à aucune commande."""
    try:
        if forcer or not sys.stdout.isatty(): sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def main():
    global SEUIL, VARIANTES, ADAPTATIF, FIN_RAPIDE
    ap = argparse.ArgumentParser()
    ap.add_argument("--variantes", default=""); ap.add_argument("--detail", action="store_true")
    ap.add_argument("--fenetre", type=float, default=8.0); ap.add_argument("--moteur", default="vosk"); ap.add_argument("--modele-chemin", default="")
    ap.add_argument("--whisper-modele", default="small"); ap.add_argument("--whisper-peripherique", default="cpu")
    ap.add_argument("--whisper-threads", type=int, default=3); ap.add_argument("--whisper-vad", type=int, default=1); ap.add_argument("--silence-fin", type=float, default=1.5); ap.add_argument("--silence-courte", type=float, default=0.6); ap.add_argument("--silence-rapide", type=float, default=0.7); ap.add_argument("--adaptatif", type=int, default=1); ap.add_argument("--duree-max", type=float, default=30.0); ap.add_argument("--vocabulaire", default=""); ap.add_argument("--grammaire", default=""); ap.add_argument("--conversation-continue", type=int, default=1)
    ap.add_argument("--fichier"); ap.add_argument("--timeout", type=int, default=60); ap.add_argument("--continu", action="store_true")
    ap.add_argument("--micro", default=""); ap.add_argument("--seuil", type=float, default=SEUIL)
    ap.add_argument("--liste", action="store_true"); ap.add_argument("--test-micro", type=int, default=0)
    a = ap.parse_args()
    ADAPTATIF = bool(a.adaptatif); FIN_RAPIDE = max(0.5, min(1.0, a.silence_rapide))
    SEUIL = max(0.4, min(0.95, a.seuil))
    VARIANTES = charger_variantes(a.variantes)
    configurer_sortie(a.continu)
    if a.liste:
        try:
            for i, nom, fe in lister_micros(): print(f"{i}	{nom}	{fe} Hz")
        except Exception as e:
            print("ERREUR:micro " + str(e), file=sys.stderr); sys.exit(3)
        return
    if a.fichier:
        # Test SANS micro, SANS son : un fichier WAV 16 bits mono est lu bloc par bloc par le moteur choisi (--moteur), puis un peu de silence referme la phrase.
        w = wave.open(a.fichier, "rb"); taux = w.getframerate()
        if w.getsampwidth() != 2 or w.getnchannels() != 1:
            print("ERREUR:fichier WAV 16 bits mono attendu", file=sys.stderr); sys.exit(3)
        try:
            moteur, repli = creer_moteur(a.moteur, taux, a.modele_chemin, a.whisper_modele, a.whisper_peripherique, a.whisper_threads, bool(a.whisper_vad), a.silence_fin, charger_prompt(a.vocabulaire), a.grammaire, a.silence_courte, a.duree_max)
        except Exception as e:
            print("ERREUR:moteur " + str(e), file=sys.stderr); sys.exit(3)
        print("MOTEUR:" + moteur.nom, flush=True)
        if repli: print(repli, flush=True)
        t0 = time.time(); finals = []; etages = []
        taille = max(1, int(taux * 0.25)) * 2
        while True:
            d = w.readframes(taille // 2)
            if not d: break
            t, p = moteur.bloc(d)
            if t: finals.append(t); etages.append(getattr(moteur, "infos", {}).get("etage", ""))
        for _ in range(max(6, int(round(a.silence_fin * 10)) + 3)):      # silence de fin (un peu plus long que --silence-fin) : referme la dernière phrase (Whisper) ou la finalise (Vosk)
            t, p = moteur.bloc(b"\x00\x00" * (taille // 2))
            if t: finals.append(t); etages.append(getattr(moteur, "infos", {}).get("etage", ""))
        if hasattr(moteur, "rec"):
            t = json.loads(moteur.rec.FinalResult()).get("text", "")
            if t: finals.append(t)
        t = " ".join(finals).strip()
        print(f"DUREE:{time.time() - t0:.2f}", flush=True)
        if any(etages): print("ETAGE:" + ",".join(e for e in etages if e), flush=True)
        print("ENTENDU:" + t)
        if est_stop(t): print("STOP"); sys.exit(0)
        o = extraire(t)
        if o: print("ORDRE:" + o); return
        sys.exit(2)
    try:
        import sounddevice as sd
        idx, nom_micro, trouve = choisir_micro(a.micro)
        if not trouve:
            print("MICRO_ABSENT:" + a.micro, flush=True)          # le micro demandé n'existe pas : on prend celui par défaut
        taux = 16000
        q = queue.Queue()
        cb = lambda d, f, t, s: q.put(bytes(d))
        try:
            stream = sd.RawInputStream(samplerate=taux, blocksize=int(taux * 0.1), dtype="int16", channels=1, device=idx, callback=cb)
        except Exception:
            # certains micros n'acceptent pas 16 kHz : on prend leur fréquence native, le moteur rééchantillonne
            info = sd.query_devices(idx if idx is not None else None, "input")
            taux = int(info["default_samplerate"])
            stream = sd.RawInputStream(samplerate=taux, blocksize=int(taux * 0.1), dtype="int16", channels=1, device=idx, callback=cb)
        try:
            moteur, repli = creer_moteur(a.moteur, taux, a.modele_chemin, a.whisper_modele, a.whisper_peripherique, a.whisper_threads, bool(a.whisper_vad), a.silence_fin, charger_prompt(a.vocabulaire), a.grammaire, a.silence_courte, a.duree_max)
        except Exception as e:
            print("ERREUR:vosk " + str(e), file=sys.stderr); sys.exit(3)
        stream.start()
        if not nom_micro:
            nom_micro = sd.query_devices(idx, "input")["name"] if idx is not None else "défaut"
    except SystemExit:
        raise
    except Exception as e:
        print("ERREUR:micro " + str(e), file=sys.stderr); sys.exit(3)
    print("MICRO:" + nom_micro, flush=True)
    print("MOTEUR:" + getattr(moteur, "nom_affiche", moteur.nom), flush=True)
    if repli: print(repli, flush=True)
    print("PRET", flush=True)
    dernier_niveau = -9; dernier_envoi = 0.0
    if a.test_micro:
        print(f"Micro utilisé : {nom_micro}   moteur : {moteur.nom}   (seuil du mot « Jarvis » : {SEUIL})", flush=True)
        print(f"Parlez pendant {a.test_micro} s : le niveau s'affiche en direct, puis ce que j'ai entendu.", flush=True)
        a.timeout = a.test_micro
    fin = time.time() + a.timeout
    dlg = Dialogue(a.fenetre, bool(a.conversation_continue)); muet_jusqua = 0.0; stop_envoye = 0.0; parlait = False
    while a.continu or time.time() < fin:
        try: d = q.get(timeout=1)
        except queue.Empty: continue
        maintenant = time.time()
        lvl = niveau_pct(d)
        if a.test_micro:
            if maintenant - dernier_envoi > 0.12:
                dernier_envoi = maintenant
                print("\r  niveau " + "#" * (lvl // 4) + "." * (25 - lvl // 4) + f" {lvl:3d} %   ", end="", flush=True)
        elif abs(lvl - dernier_niveau) >= 3 and maintenant - dernier_envoi > 0.2:
            dernier_niveau = lvl; dernier_envoi = maintenant
            print("NIVEAU:" + str(lvl), flush=True)
        if parle_en_cours():
            muet_jusqua = maintenant + 1.2; parlait = True
        elif parlait and maintenant > muet_jusqua:
            parlait = False; dlg.reponse_finie(maintenant)         # conversation continue : la réponse est finie, j'écoute la suite sans mot d'éveil
        sourdine = os.path.exists(FLAG_SOURDINE)
        ecoute_ordres = maintenant > muet_jusqua and not sourdine
        t, p = moteur.bloc(d)
        if t is not None:
            if not t: continue
            if a.test_micro and a.detail:
                print("\n  BRUT : « " + t + " »", flush=True)
                for m in t.split():
                    r = analyser_wake(m)
                    print(f"     {m:<14} -> " + ("DÉCLENCHE (" + r + ")" if r else "non"), flush=True)
                dw = diagnostiquer_wake(t)
                print("  => mot d'activation " + ("DÉCLENCHÉ, ordre = « " + (dw["ordre"] or "") + " »" + (" (« Jarvis » seul : fenêtre d'ordre)" if dw["ordre"] == "" else "") if dw["valide"] else "NON déclenché : " + dw["raison"]), flush=True)
                continue
            if a.test_micro:
                dw = diagnostiquer_wake(t)
                print("\n  J'ai entendu : " + t + ("   -> mot d'activation reconnu" if dw["valide"] else "   (" + dw["raison"] + ")"), flush=True)
                continue
            if est_stop(t):
                if maintenant - stop_envoye > 2: poser_stop(); print("STOP", flush=True); stop_envoye = maintenant
                continue
            if getattr(moteur, "repli", ""): print(moteur.repli, flush=True); moteur.repli = ""
            dlg.infos = dict(getattr(moteur, "infos", {}) or {}, silence_cfg_ms=int(a.silence_fin * 1000), silence_courte_ms=int(a.silence_courte * 1000), silence_rapide_ms=int(FIN_RAPIDE * 1000) if ADAPTATIF else 0, duree_max_s=int(a.duree_max))
            for ligne in dlg.phrase(t, maintenant, ecoute_ordres, sourdine):
                print(ligne, flush=True)
                if ligne.startswith("ORDRE:") and not a.continu: return
        else:
            dlg.partiel(p, maintenant)
            if p and p != "…" and est_stop(p) and maintenant - stop_envoye > 2:  # réaction immédiate, sans attendre la fin de phrase
                poser_stop(); print("STOP", flush=True); stop_envoye = maintenant
    sys.exit(2)

if __name__ == "__main__":
    main()
