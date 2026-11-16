#!/usr/bin/env python3
"""Outils communs de l'équipe Vidéos TikTok (16/11/2026) : chemins, réglages (videos-config.json + videos-config.local.json), journal, état,
machine active (B2B\\agents\\machine.py), alerte Discord (fonction existante des agents B2B), lien du planning de 15 min (LU dans le dossier B2B, jamais recopié),
Qwen local via Ollama (démarré en silence si besoin, arrêté ensuite s'il a été démarré ici). Aucun secret affiché ni journalisé."""
import json, os, re, shutil, subprocess, sys, time, urllib.error, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ICI = Path(__file__).resolve().parent
VIDEOS = ICI.parent
RACINE = VIDEOS.parent
AGENTS_B2B = RACINE / "B2B" / "agents"
sys.path.insert(0, str(AGENTS_B2B))
import machine as M   # noqa: E402

CONFIG = VIDEOS / "videos-config.json"
VEILLE, SCRIPTS, A_VALIDER, PUBLIEES, TRAVAIL = (VIDEOS / "veille", VIDEOS / "scripts", VIDEOS / "a-valider", VIDEOS / "publiees", VIDEOS / "travail")
SUJETS = SCRIPTS / "sujets.json"
SCRIPT_APPEL = RACINE / "B2B" / "docs" / "SCRIPT-APPEL-SID.md"
LIEN_RDV = re.compile(r"https://calendar\.app\.google/[A-Za-z0-9]+")
MENTION_IA = "Contenu généré par IA."
OLLAMA_URL = "http://127.0.0.1:11434"
SKILL = VIDEOS / "SKILL-VIDEOS.md"
HOOKS_BASE, HOOKS = VIDEOS / "hooks-base.md", VIDEOS / "hooks.md"
JOURNAL_CSV = VIDEOS / "journal-videos.csv"
# tts : moteur de voix réellement utilisé (edge-tts ou kokoro). Suivi (17/11/2026) : histoire (H01…), formule d'accroche (A10, histoire H01…), thème,
# fin (variante de l'appel à l'action), durée, voix, date et heure de publication, adresse TikTok (remplies par l'agent qui les connaît ; vides sinon).
CSV_SUIVI = ["histoire", "formule", "theme", "fin", "duree_s", "voix", "publie_le", "url_tiktok"]
CSV_COLONNES = ["date", "agent", "video", "ligne", "compte", "statut", "hook", "detail", "tts"] + CSV_SUIVI
SECTIONS_SKILL = ("## Règles pour Qwen", "## Grille des accroches", "## Publication", "## Deux lignes éditoriales", "## Sous-titres", "## Nettoyage")
LIGNE_DEFAUT = {"nom": "", "compte": "", "ton": "", "tutoiement": False, "go_publier": False, "profil_navigateur": "", "hashtags": "", "taux_commission": "", "voix": {},
                "message": "", "brouillon_hook": "", "lieux_interdits": []}
DEFAUT = {"outil": "stickfigure-pipeline-v2", "voix": "fr-FR-RemyMultilingualNeural", "modele": "qwen2.5:3b", "passages": ["06:00", "14:00", "22:00"],
          "series_par_passage": {"06:00": "A", "14:00": "B", "22:00": "A"}, "mots_min": 52, "mots_max": 88, "duree_min_s": 20, "duree_max_s": 35,
          "veille_jours_gardes": 14, "veille_requetes": [], "lignes": {}, "lien_candidature": "", "publications_max_par_jour": 3,
          "navigateur": "msedge", "navigateur_visible": True, "nettoyage_jours": 14, "nettoyage_extensions": [".mp4"], "videos_protegees": []}


def cfg():
    c = json.loads(json.dumps(DEFAUT))
    try: c.update({k: v for k, v in json.loads(CONFIG.read_text(encoding="utf-8")).items() if not k.startswith("_")})
    except (OSError, ValueError): pass
    M.surcharge_locale(CONFIG, c)
    c["lien_candidature"] = str(c.get("lien_candidature") or "").strip()
    lignes = {}
    for x in ("A", "B"):
        l = dict(LIGNE_DEFAUT); l.update((c.get("lignes") or {}).get(x) or {})
        l["go_publier"] = l.get("go_publier") is True   # seul true (booléen) ouvre la publication ; "oui", 1… ne comptent pas
        l["taux_commission"] = str(l.get("taux_commission") or "").strip()
        lignes[x] = l
    c["lignes"] = lignes
    return c


def regles():
    """Relit Videos\\SKILL-VIDEOS.md avant chaque exécution. -> texte. Lève RuntimeError si le fichier manque ou s'il lui manque une section obligatoire."""
    try: t = SKILL.read_text(encoding="utf-8")
    except OSError: raise RuntimeError(f"règles introuvables ({SKILL.name}) : aucun agent vidéo ne tourne sans elles")
    manque = [s for s in SECTIONS_SKILL if s not in t]
    if manque: raise RuntimeError(f"{SKILL.name} incomplet (manque : {', '.join(manque)})")
    return t


def section(texte, titre):
    """Contenu d'une section « ## titre » du skill (jusqu'à la suivante)."""
    m = re.search(rf"^## {re.escape(titre)}[^\n]*\n(.*?)(?=^## |\Z)", texte, re.S | re.M)
    return m.group(1).strip() if m else ""


def exiger_regles(agent, a_blanc=False):
    """Appel obligatoire au début de chaque agent : relit le skill ; refus (code 3, journal) s'il manque."""
    try: return regles()
    except RuntimeError as e:
        journal(agent, "refusé", str(e), a_blanc); print(f"Refusé : {e}"); sys.exit(3)


def hooks_texte():
    for p in (HOOKS, HOOKS_BASE):
        try: return p.read_text(encoding="utf-8")
        except OSError: pass
    return ""


def csv_ligne(agent, video="", ligne="", compte="", statut="", hook="", detail="", a_blanc=False, quand=None, tts="", **suivi):
    """Une ligne dans Videos\\journal-videos.csv (séparateur « ; », en-tête écrit à la création). Jamais de secret ni de donnée personnelle.
    suivi : colonnes de suivi (CSV_SUIVI : histoire, formule, theme, fin, duree_s, voix, publie_le, url_tiktok). Un fichier à l'ancien en-tête est d'abord migré."""
    if a_blanc: return
    import csv
    inconnues = set(suivi) - set(CSV_SUIVI)
    if inconnues: raise ValueError(f"colonnes inconnues : {', '.join(sorted(inconnues))}")
    if JOURNAL_CSV.exists():
        with JOURNAL_CSV.open(encoding="utf-8-sig", newline="") as f: lignes = list(csv.reader(f, delimiter=";"))
        if lignes and lignes[0] != CSV_COLONNES:   # ancien en-tête : on réécrit avec les nouvelles colonnes (vides pour les anciennes lignes)
            ancien = lignes[0]
            rangs = [{k: (r[i] if i < len(r) else "") for i, k in enumerate(ancien)} for r in lignes[1:] if any(x.strip() for x in r)]
            tmp = JOURNAL_CSV.with_suffix(".tmp")
            with tmp.open("w", encoding="utf-8-sig", newline="") as f:
                w = csv.writer(f, delimiter=";"); w.writerow(CSV_COLONNES); w.writerows([[x.get(k, "") for k in CSV_COLONNES] for x in rangs])
            os.replace(tmp, JOURNAL_CSV)
    neuf = not JOURNAL_CSV.exists()
    with JOURNAL_CSV.open("a", encoding="utf-8-sig" if neuf else "utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        if neuf: w.writerow(CSV_COLONNES)
        w.writerow([f"{quand or datetime.now():%Y-%m-%d %H:%M}", agent, video, ligne, compte, statut, " ".join(str(hook).split())[:200], " ".join(str(detail).split())[:300], tts]
                   + [" ".join(str(suivi.get(k, "")).split())[:200] for k in CSV_SUIVI])


VIDES = set("le la les l un une des de du d à au aux et ou mais donc or ni car que qu qui quoi ce c cet cette ces se s sa son ses ta ton tes ma mon mes vos votre "
            "nos notre leur leurs il elle on ils elles je j tu te t me m nous vous y en ne n pas plus est sont a as ai avez avons pour par sur dans avec sans chez "
            "comme si là ça ca tout tous toute toutes très bien aussi même alors".split())


def mots_de(phrase):
    """Mots d'une phrase, ponctuation collée (« téléphone ? » reste un seul mot, espace insécable : le « ? » ne se perd jamais dans les sous-titres)."""
    p = re.sub(r"\s+([?!:;»])", " \\1", phrase or "")
    return re.findall(r"[\wÀ-ÿ'’%-]+(?:[?!.,:;…]| [?!:;»])*", p)


def decouper_sous_titres(phrase, maxi=4, mini=2):
    """Groupes de 2 à 4 mots pour les sous-titres, coupés après une ponctuation puis en groupes de taille égale ; le mot clé (couleur d'accent) = le plus long mot plein.
    -> [{"mots": [...], "cle": index}]"""
    ms = mots_de(phrase); segments, cur = [], []
    for m in ms:   # morceaux de phrase coupés après une ponctuation
        cur.append(m)
        if re.search(r"[,.;:!?…]$", m): segments.append(cur); cur = []
    if cur: segments.append(cur)
    groupes = []
    for seg in segments:   # chaque morceau en groupes de taille égale, 4 mots au plus
        k = -(-len(seg) // maxi); base, reste = divmod(len(seg), k); i = 0
        for n in range(k):
            t = base + (n < reste); groupes.append(seg[i:i + t]); i += t
    i = 0
    while i < len(groupes):   # un mot seul rejoint son voisin s'il y a la place
        if len(groupes[i]) < mini and len(groupes) > 1:
            if i > 0 and len(groupes[i - 1]) < maxi: groupes[i - 1] += groupes.pop(i); continue
            if i + 1 < len(groupes) and len(groupes[i + 1]) < maxi: seul = groupes.pop(i); groupes[i] = seul + groupes[i]; continue   # (avant le 17/11 : mauvais indice, mot dupliqué ou perdu)
        i += 1
    out = []
    for g in groupes:
        nus = [re.sub(r"[\s ?!.,:;…»]+$", "", m).lower().replace("’", "'") for m in g]
        pleins = [i for i, m in enumerate(nus) if m.split("'")[-1] not in VIDES and len(m.split("'")[-1]) > 2]
        cle = max(pleins, key=lambda i: len(nus[i].split("'")[-1])) if pleins else -1
        out.append({"mots": g, "cle": cle})
    return out


def csv_lire():
    import csv
    try:
        with JOURNAL_CSV.open(encoding="utf-8-sig", newline="") as f: return list(csv.DictReader(f, delimiter=";"))
    except OSError: return []


def heure_paris(maintenant=None):
    """Heure de Paris sans fuseau (heure d'été comprise), sans dépendre de la base de fuseaux de Windows."""
    n = maintenant or datetime.now(timezone.utc)
    try:
        from zoneinfo import ZoneInfo
        return n.astimezone(ZoneInfo("Europe/Paris")).replace(tzinfo=None)
    except Exception: pass
    u = n.astimezone(timezone.utc).replace(tzinfo=None)
    def dernier_dimanche(m): d = datetime(u.year, m, 31, 1); return d - timedelta(days=(d.weekday() + 1) % 7)
    return u + timedelta(hours=2 if dernier_dimanche(3) <= u < dernier_dimanche(10) else 1)


def journal(agent, action, detail, a_blanc=False):
    """Une ligne par action : date heure | action | détail. Jamais de secret, de mot de passe ni de donnée personnelle."""
    if a_blanc: return
    with (VIDEOS / f"{agent}-journal.log").open("a", encoding="utf-8") as f: f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} | {action} | {detail}\n")


def etat_lire(agent, defaut):
    try: e = json.loads((VIDEOS / f"{agent}-etat.json").read_text(encoding="utf-8"))
    except (OSError, ValueError): e = {}
    for k, v in defaut.items(): e.setdefault(k, v)
    return e


def etat_ecrire(agent, etat):
    p = VIDEOS / f"{agent}-etat.json"; tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(etat, ensure_ascii=False, indent=1), encoding="utf-8"); os.replace(tmp, p)


def exiger(agent, commande, a_blanc=False):
    """Machine active (b2b.local.json) : refus (code 3) ailleurs, comme les agents B2B."""
    M.exiger(agent, commande, a_blanc, journal=VIDEOS / f"{agent}-journal.log")


def alerter_discord(texte):
    """Salon Discord habituel des agents (bot Jarvis, jeton lu dans Jarvis\\.env par prospection.py, jamais affiché). True si posté."""
    try:
        import prospection as P
        a = P.acces_discord()
        if not a: return False
        jeton, salon, uid = a
        r = P.discord(jeton, "POST", f"/channels/{salon}/messages", {"content": f"<@{uid}> {texte}"[:1900], "allowed_mentions": {"users": [uid]}})
        return bool(r and "id" in r)
    except Exception as ex: print(f"  alerte Discord impossible ({type(ex).__name__})"); return False


def lien_rdv():
    """Planning de rendez-vous de 15 minutes de Liam, LU dans B2B\\docs\\SCRIPT-APPEL-SID.md (jamais recopié ailleurs). "" s'il est introuvable."""
    try: m = LIEN_RDV.search(SCRIPT_APPEL.read_text(encoding="utf-8"))
    except OSError: return ""
    return m.group(0) if m else ""


def executable(nom, *secours):
    """Un programme du PATH, sinon du PATH utilisateur enregistré (winget l'y ajoute ; une tâche planifiée ne le voit pas toujours), sinon un chemin de secours."""
    trouve = shutil.which(nom)
    if trouve: return trouve
    try:
        import winreg
        for racine, cle in ((winreg.HKEY_CURRENT_USER, "Environment"), (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment")):
            with winreg.OpenKey(racine, cle) as k: chemin = winreg.QueryValueEx(k, "Path")[0]
            trouve = shutil.which(nom, path=os.path.expandvars(chemin))
            if trouve: return trouve
    except (OSError, ImportError): pass
    for s in secours:
        if s and Path(s).exists(): return str(s)
    return nom


def chemin_complet():
    """PATH du processus + PATH utilisateur et machine enregistrés : les outils installés par winget (node, ffmpeg) sont trouvés même depuis une tâche planifiée."""
    morceaux = [os.environ.get("PATH", "")]
    try:
        import winreg
        for racine, cle in ((winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"), (winreg.HKEY_CURRENT_USER, "Environment")):
            with winreg.OpenKey(racine, cle) as k: morceaux.append(os.path.expandvars(winreg.QueryValueEx(k, "Path")[0]))
    except (OSError, ImportError): pass
    scripts = Path(sys.executable).parent / "Scripts"
    morceaux.append(str(scripts))
    return os.pathsep.join(m for m in morceaux if m)


# --- Qwen local (Ollama) -------------------------------------------------------------------------------------------
def _ollama_repond(timeout=3):
    try:
        with urllib.request.urlopen(OLLAMA_URL + "/api/tags", timeout=timeout): return True
    except (urllib.error.URLError, OSError): return False


class Ollama:
    """with Ollama() as o: o.chat(...). Démarre le service en silence s'il ne répond pas, et l'arrête à la sortie seulement s'il a été démarré ici."""
    def __init__(self, modele): self.modele, self.proc = modele, None

    def __enter__(self):
        if not _ollama_repond():
            exe = executable("ollama", Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe")
            drapeaux = (getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0)) if os.name == "nt" else 0
            self.proc = subprocess.Popen([exe, "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=drapeaux)
            for _ in range(30):
                if _ollama_repond(): break
                time.sleep(1)
            else: raise RuntimeError("Ollama ne répond pas après 30 s")
        return self

    def chat(self, systeme, demande, temperature=0.7, num_predict=700):
        corps = {"model": self.modele, "stream": False, "format": "json", "keep_alive": "1m",
                 "options": {"temperature": temperature, "num_predict": num_predict},
                 "messages": [{"role": "system", "content": systeme}, {"role": "user", "content": demande}]}
        rq = urllib.request.Request(OLLAMA_URL + "/api/chat", data=json.dumps(corps).encode("utf-8"), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(rq, timeout=600) as r: return json.loads(r.read())["message"]["content"]

    def __exit__(self, *a):
        if self.proc:
            try: self.proc.terminate(); self.proc.wait(timeout=15)
            except Exception:
                try: self.proc.kill()
                except Exception: pass
        return False
