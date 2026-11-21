#!/usr/bin/env python3
"""Moteur commun des superviseurs de domaine (21/11/2026). Un superviseur = un domaine (Vente, Prospection, Sites, Mail) : toutes les 30 minutes il regarde
les agents de SON domaine (ont-ils tourné ? leur dernier passage est-il en erreur ? leurs données sont-elles cohérentes ?), corrige seul ce qui est sûr,
et alerte Liam sur Discord sans rien toucher dès que la correction serait risquée ou irréversible.

Partage commun à tous les superviseurs (ce fichier) : réglages + verrou « go superviseurs », état, journal, traces, détection de panne, relance unique,
classement sûr / risqué, message Discord, fiche B2B\\a-valider. Chaque superviseur n'apporte que la liste des agents de son domaine et ses contrôles.

Règles non négociables (codées ici, pas dans chaque superviseur) :
 - RISQUÉ = JAMAIS TOUCHÉ : supprimer une donnée, écraser une valeur existante, ou toucher à un montant, un paiement, un prix, un devis. Un souci risqué perd sa réparation (constructeur de Souci).
 - SÛR = seulement ajouter une clé manquante avec sa valeur vide, retirer un doublon STRICTEMENT identique, remettre une liste dans l'ordre des dates, relancer un agent planté (une fois par jour).
 - Un superviseur n'écrit que dans les fichiers de données de son domaine (`fichiers_ecrits` de son contrat) : jamais de code, jamais un autre domaine.
 - Verrou : rien n'est corrigé et rien n'est posté tant que `go_superviseurs` n'est pas true dans un fichier de réglages local (après le « go superviseurs » de Liam). `--essai` marche toujours.
 - `B2B\\STOP` présent : aucune relance, aucun envoi (la garde du harness bloque aussi chaque POST Discord)."""
import io, json, os, re, subprocess, sys, time
from datetime import date, datetime, timedelta
from pathlib import Path

ICI = Path(__file__).resolve().parent
RACINE = ICI.parent.parent
AGENTS = ICI.parent / "agents"
for _p in (str(ICI), str(AGENTS)):
    if _p not in sys.path: sys.path.insert(0, _p)
import traces as T          # noqa: E402  traces du harness (B2B\logs\agents\<agent>)
import machine as M         # noqa: E402  réglages propres à la machine et machine active
import surveillant as SV    # noqa: E402  contrats et serveur-taches.json

COMMUN = AGENTS / "superviseurs-config.json"
STOP = RACINE / "B2B" / "STOP"
A_VALIDER = RACINE / "B2B" / "a-valider"
DEFAUT = {"go_superviseurs": False, "envoi_automatique": False, "grace_minutes": 20, "heure_resume": "08:45", "tolerance_cycles": 3,
          "heure_debut": "07:00", "heure_fin": "22:00"}
GARDE_JOURS = 30
EN_DEFAUT = ("erreur", "silence", "bloque")


class ErreurAgent(Exception):
    """Problème signalé à Liam (message clair, code de sortie 2) : le superviseur s'arrête sans rien écrire de plus."""


# --- un souci repéré par un contrôle -------------------------------------------------------------------------------
class Souci:
    """Un problème constaté. `risque=True` : rien n'est touché, Liam est alerté et le superviseur attend son « go ».
    `reparer` : fonction sans argument qui corrige (seulement si le souci est sûr) et renvoie la phrase décrivant ce qui a changé."""

    def __init__(self, agent, quoi, detail="", risque=False, reparer=None, cle=None):
        self.agent, self.quoi, self.detail = str(agent), str(quoi), str(detail or "")
        self.risque = bool(risque)
        self.reparer = None if self.risque else reparer      # une correction risquée n'existe pas : la garde est ici, pas dans les superviseurs
        self.cle = cle or f"{agent}|{quoi}"
        self.corrige, self.change = False, ""

    def ligne(self):
        return f"{self.agent} : {self.quoi}" + (f" — {self.detail}" if self.detail else "")


def sur(agent, quoi, reparer, detail="", cle=None):
    """Souci corrigeable sans rien perdre."""
    return Souci(agent, quoi, detail, False, reparer, cle)


def risque(agent, quoi, detail="", cle=None):
    """Souci qu'on ne corrige JAMAIS tout seul : Liam est alerté et le superviseur attend son « go »."""
    return Souci(agent, quoi, detail, True, None, cle)


# --- réglages, état, journal ---------------------------------------------------------------------------------------
def cfg(agent, defaut=None):
    """Réglages : défauts communs, puis superviseurs-config.json, puis <agent>-config.json, puis leurs variantes locales (hors git).
    Le verrou « go superviseurs » peut donc être levé une seule fois pour les quatre, dans la variante locale du fichier commun."""
    c = dict(DEFAUT); c.update(defaut or {})
    propre = AGENTS / f"{agent}-config.json"
    for p in (COMMUN, propre):
        if not p.exists(): continue
        try: c.update({k: v for k, v in json.loads(p.read_text(encoding="utf-8-sig")).items() if not k.startswith("_")})
        except (OSError, ValueError): raise ErreurAgent(f"réglages illisibles : {p.name}")
    for p in (COMMUN, propre):      # les réglages locaux passent après les deux fichiers versionnés
        try: M.surcharge_locale(p, c)
        except M.ErreurLocale as e: raise ErreurAgent(str(e))
    c["go_superviseurs"] = c.get("go_superviseurs") is True
    c["envoi_automatique"] = c.get("envoi_automatique") is True
    for k, mini, maxi in (("grace_minutes", 0, 240), ("tolerance_cycles", 1, 20)):
        v = c.get(k)
        c[k] = v if isinstance(v, int) and not isinstance(v, bool) and mini <= v <= maxi else DEFAUT[k]
    for k in ("heure_resume", "heure_debut", "heure_fin"):
        if not re.fullmatch(r"([01][0-9]|2[0-3]):[0-5][0-9]", str(c.get(k) or "")): c[k] = DEFAUT[k]
    return c


def dans_plage(maintenant, conf):
    """Vrai dans la plage où un superviseur a le droit de poster (défaut 07:00-22:00) : la nuit, une alerte attend le passage du matin."""
    return _minutes(conf["heure_debut"]) <= maintenant.hour * 60 + maintenant.minute < _minutes(conf["heure_fin"])


def chemins(agent):
    return AGENTS / f"{agent}-etat.json", AGENTS / f"{agent}-journal.log"


def etat_lire(agent):
    p, _ = chemins(agent)
    try: e = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except (OSError, ValueError): raise ErreurAgent(f"état illisible ({p.name}) : rien n'est écrit ; corrigez ou supprimez le fichier à la main")
    if not isinstance(e, dict): raise ErreurAgent(f"état illisible ({p.name}) : rien n'est écrit")
    for k in ("corrections", "en_attente", "relances", "resumes", "empreintes"): e.setdefault(k, {})
    return e


def etat_ecrire(agent, e):
    limite = (date.today() - timedelta(days=GARDE_JOURS)).isoformat()
    for k in ("corrections", "relances", "resumes"): e[k] = {j: v for j, v in e[k].items() if str(j) >= limite}
    p, _ = chemins(agent); p.write_text(json.dumps(e, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")


def journaliser(agent, action, detail=""):
    _, j = chemins(agent)
    try:
        with j.open("a", encoding="utf-8") as f: f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} | {action} | {T.nettoyer(detail)}\n")
    except OSError: pass


# --- Discord (garde du harness avant chaque POST) ------------------------------------------------------------------
def alerter_discord(texte):
    """Salon Discord habituel des agents. Le jeton est lu par prospection.py dans le fichier d'environnement de Jarvis, jamais affiché. False si rien n'est parti."""
    try:
        import prospection as P
        a = P.acces_discord()
        if not a: return False
        jeton, salon, uid = a
        r = P.discord(jeton, "POST", f"/channels/{salon}/messages", {"content": f"<@{uid}> {texte}"[:1900], "allowed_mentions": {"users": [uid]}})
        return bool(r and "id" in r)
    except Exception as ex:
        print(f"  alerte Discord impossible ({type(ex).__name__})"); return False


# --- lecture des traces : a-t-il tourné ? est-il planté ? ----------------------------------------------------------
def executions(nom, jour, dossier=None):
    """Traces d'exécution du jour (les lignes « garde … » écrites par la garde ne comptent pas comme un passage)."""
    return [x for x in T.lire(nom, jour, dossier) if not str(x.get("decision", "")).startswith("garde ")]


def taches():
    return SV.taches_serveur()


def agents_actifs():
    """Agents que Liam a réellement planifiés sur CETTE machine (agents_actifs). Un agent écrit dans serveur-taches.json mais absent de cette liste
    n'a aucune tâche Windows : il ne tourne pas, et son silence n'est pas une panne (même règle que le surveillant du harness). Remplacée dans les tests."""
    try: return set(M.agents_actifs())
    except Exception: return set()


def _minutes(s):
    h, m = str(s).split(":"); return int(h) * 60 + int(m)


def etat_agent(nom, maintenant, conf, dossier=None, ts=None, actifs=None):
    """-> (état, détail). « ok » ; « jamais prevu » (aucune tâche, tâche désactivée, ou agent absent de agents_actifs) ; « pas encore actif » ; « hors jour » ;
    « erreur » (dernier passage du jour ok:false) ; « silence » (heure fixe passée + grâce, aucun passage) ; « bloque » (agent cyclique muet depuis trop longtemps)."""
    ts = taches() if ts is None else ts
    t = ts.get(nom) or {}
    if not t: return "jamais prevu", "aucune tâche serveur"
    if t.get("desactive"): return "jamais prevu", "tâche désactivée par Liam"
    if nom not in (agents_actifs() if actifs is None else actifs):
        return "jamais prevu", "absent de agents_actifs : aucune tâche sur cette machine (Liam ne l'a pas encore ouvert)"
    jour = f"{maintenant:%Y-%m-%d}"
    if t.get("actif_le") and jour < str(t["actif_le"]): return "pas encore actif", f"actif le {t['actif_le']}"
    c = next((x for x in SV.contrats() if x["nom"] == nom), None)
    jours = t.get("jours") or (c["jours"] if c else list(range(7)))
    if maintenant.weekday() not in jours: return "hors jour", "pas prévu ce jour-là"
    passages = executions(nom, jour, dossier)
    if passages and not passages[-1].get("ok", True):
        p = passages[-1]
        return "erreur", f"dernier passage en erreur à {str(p.get('heure', ''))[11:16]} ({T.nettoyer(p.get('erreur') or p.get('resultat'))[:90]})"
    if t.get("heure"):
        heures = [t["heure"]] + [str(x) for x in (t.get("heures_en_plus") or [])] + ([t["lundi"]] if t.get("lundi") and maintenant.weekday() == 0 else [])
        dues = [h for h in heures if _minutes(h) + conf["grace_minutes"] <= maintenant.hour * 60 + maintenant.minute]
        if dues and not passages: return "silence", f"aucun passage aujourd'hui (prévu {', '.join(sorted(dues))}, {conf['grace_minutes']} min de grâce)"
        return "ok", f"{len(passages)} passage(s) aujourd'hui"
    n = t.get("toutes_minutes")
    if not isinstance(n, int) or isinstance(n, bool) or n <= 0: return "jamais prevu", "ni heure fixe ni cycle dans serveur-taches.json"
    muet = n * conf["tolerance_cycles"] + conf["grace_minutes"]
    if maintenant.hour * 60 + maintenant.minute < muet: return "ok", "début de journée : trop tôt pour juger un agent cyclique"
    limite = (maintenant - timedelta(minutes=muet)).strftime("%Y-%m-%dT%H:%M:%S")
    recentes = [x for x in passages + executions(nom, f"{maintenant - timedelta(days=1):%Y-%m-%d}", dossier) if str(x.get("heure", "")) >= limite]
    if not recentes: return "bloque", f"aucun passage depuis plus de {muet} min (cycle de {n} min)"
    return "ok", f"{len(recentes)} passage(s) récent(s)"


# --- relance d'un agent planté (une seule fois par jour) -----------------------------------------------------------
def commande_relance(nom, ts=None):
    """[exécutable, script, arguments…] de la PREMIÈRE commande de la tâche serveur de l'agent, ou None (rien d'inventé)."""
    t = (taches() if ts is None else ts).get(nom) or {}
    cmds = t.get("commandes") or []
    if not t.get("script") or not cmds: return None
    script = (AGENTS / str(t["script"])).resolve()
    if not script.is_file(): return None
    if script.suffix.lower() == ".ps1":
        return ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)] + [str(x) for x in cmds[0]]
    return [sys.executable, str(script)] + [str(x) for x in cmds[0]]


def relancer(nom, ts=None):
    """Relance l'agent avec la commande de sa tâche serveur (profil serveur, aucune fenêtre). -> (ok, détail). Remplacée par une doublure dans les tests."""
    if STOP.exists(): return False, "B2B\\STOP présent : aucune relance"
    cmd = commande_relance(nom, ts)
    if not cmd: return False, "aucune commande de relance (serveur-taches.json)"
    env = dict(os.environ, JARVIS_B2B_SERVEUR="1", PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
    try:
        r = subprocess.run(cmd, cwd=str(AGENTS), env=env, capture_output=True, timeout=600,
                           creationflags=0x08000000 if os.name == "nt" else 0)
        return r.returncode == 0, f"relancé, code {r.returncode}"
    except subprocess.TimeoutExpired: return False, "relance : délai de 10 min dépassé"
    except Exception as ex: return False, f"relance impossible ({type(ex).__name__})"


# --- contrôles génériques réutilisés par les quatre superviseurs ---------------------------------------------------
def lire_json(p):
    """-> (données, souci) : un fichier absent n'est pas un problème (rien à vérifier) ; un fichier illisible est RISQUÉ (jamais réécrit)."""
    p = Path(p)
    if not p.exists(): return None, None
    try: return json.loads(p.read_text(encoding="utf-8-sig")), None
    except (OSError, ValueError) as e:
        return None, risque(p.stem, f"{p.name} illisible", f"{type(e).__name__} : à corriger à la main, rien n'est réécrit", cle=f"{p.name}|illisible")


def ecrire_json(p, data):
    Path(p).write_text(json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")


def _suivre(d, pointeur):
    """Valeur pointée par une liste de clés ([] = la racine), ou None si le chemin n'existe pas."""
    x = d
    for k in pointeur:
        if not isinstance(x, dict) or k not in x: return None
        x = x[k]
    return x


def controle_forme(agent, chemin, attendu):
    """Clés attendues d'un fichier d'état : {clé: type}. Clé absente -> SÛR (ajoutée vide). Mauvais type -> RISQUÉ (jamais écrasé)."""
    d, pb = lire_json(chemin)
    if pb: return [pb]
    if d is None: return []
    nom = Path(chemin).name
    if not isinstance(d, dict):
        return [risque(agent, f"{nom} n'est pas un objet JSON", "structure inattendue : rien n'est touché", cle=f"{chemin}|racine")]
    out = []
    for cle, typ in attendu.items():
        if cle not in d:
            def rep(cle=cle, typ=typ):
                x, _ = lire_json(chemin); x[cle] = typ(); ecrire_json(chemin, x)
                return f"{nom} : clé « {cle} » manquante ajoutée, vide (aucune donnée perdue)"
            out.append(sur(agent, f"clé « {cle} » absente de {nom}", rep, "ajoutée vide", cle=f"{chemin}|{cle}|absente"))
        elif not isinstance(d[cle], typ):
            out.append(risque(agent, f"« {cle} » de {nom} a un type inattendu",
                              f"{type(d[cle]).__name__} au lieu de {typ.__name__} : rien n'est touché", cle=f"{chemin}|{cle}|type"))
    return out


def controle_doublons(agent, chemin, pointeur, nom_lisible=None):
    """Doublons STRICTEMENT identiques d'une liste d'un fichier JSON (pointeur : liste de clés, [] = racine).
    Dédoublonner garde la première occurrence et l'ordre : SÛR (rien d'autre n'est touché)."""
    d, pb = lire_json(chemin)
    if pb: return [pb]
    if d is None: return []
    x = _suivre(d, pointeur)
    if not isinstance(x, list): return []
    vus, doublons = set(), 0
    for v in x:
        s = json.dumps(v, ensure_ascii=False, sort_keys=True)
        if s in vus: doublons += 1
        else: vus.add(s)
    if not doublons: return []
    lib = nom_lisible or ("/".join(pointeur) or "liste")
    nom = Path(chemin).name

    def rep():
        y, _ = lire_json(chemin)
        src = _suivre(y, pointeur)
        garde, propre = set(), []
        for v in src:
            s = json.dumps(v, ensure_ascii=False, sort_keys=True)
            if s not in garde: garde.add(s); propre.append(v)
        if pointeur: _suivre(y, pointeur[:-1])[pointeur[-1]] = propre
        else: y = propre
        ecrire_json(chemin, y)
        return f"{nom} : {doublons} doublon(s) identique(s) retiré(s) de {lib} (la première ligne est gardée)"
    return [sur(agent, f"{doublons} doublon(s) dans {lib} ({nom})", rep, "lignes strictement identiques", cle=f"{chemin}|{lib}|doublons")]


def controle_entrees_datees(agent, chemin, cle_liste="jours", cle_date="date"):
    """Liste d'entrées datées (tableau de bord : data/historique.json). Deux entrées pour la même date -> RISQUÉ (laquelle garder ? Liam décide).
    Date dans le futur -> RISQUÉ. Sinon ordre cassé -> SÛR (tri par date, rien d'ajouté ni de retiré)."""
    d, pb = lire_json(chemin)
    if pb: return [pb]
    if d is None or not isinstance(d, dict) or not isinstance(d.get(cle_liste), list): return []
    nom = Path(chemin).name
    dates = [str(x.get(cle_date) or "") for x in d[cle_liste] if isinstance(x, dict)]
    out = []
    repetees = sorted({j for j in dates if dates.count(j) > 1})
    if repetees:
        out.append(risque(agent, f"{len(repetees)} date(s) en double dans {nom}",
                          f"{', '.join(repetees[:5])} : deux entrées pour le même jour, Liam choisit laquelle garder", cle=f"{chemin}|{cle_liste}|dates-doubles"))
    futures = sorted({j for j in dates if j > date.today().isoformat()})
    if futures:
        out.append(risque(agent, f"date dans le futur dans {nom}", f"{', '.join(futures[:5])} : donnée illogique, rien n'est touché", cle=f"{chemin}|{cle_liste}|futur"))
    if not repetees and not futures and dates != sorted(dates):
        def rep():
            y, _ = lire_json(chemin)
            y[cle_liste] = sorted(y[cle_liste], key=lambda x: str(x.get(cle_date) or "")); ecrire_json(chemin, y)
            return f"{nom} : « {cle_liste} » remis dans l'ordre des dates"
        out.append(sur(agent, f"« {cle_liste} » de {nom} n'est pas dans l'ordre des dates", rep, "remis dans l'ordre", cle=f"{chemin}|{cle_liste}|ordre"))
    return out


def controle_dates_valides(agent, chemin, pointeur, libelle):
    """Clés d'un dictionnaire qui doivent être des dates AAAA-MM-JJ, aujourd'hui au plus tard. Format invalide ou futur -> RISQUÉ (une date ne se devine pas)."""
    d, pb = lire_json(chemin)
    if pb: return [pb]
    if d is None: return []
    x = _suivre(d, pointeur)
    if not isinstance(x, dict): return []
    nom = Path(chemin).name
    mauvaises = [k for k in x if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(k))]
    futures = [k for k in x if re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(k)) and str(k) > date.today().isoformat()]
    out = []
    if mauvaises:
        out.append(risque(agent, f"{len(mauvaises)} date(s) mal formée(s) dans {libelle}", f"{', '.join(map(str, mauvaises[:5]))} ({nom})", cle=f"{chemin}|{libelle}|format"))
    if futures:
        out.append(risque(agent, f"{len(futures)} date(s) dans le futur dans {libelle}", f"{', '.join(map(str, futures[:5]))} ({nom})", cle=f"{chemin}|{libelle}|futur"))
    return out


def controle_doublons_csv(agent, chemin, colonne_cle=None):
    """Lignes STRICTEMENT identiques d'un fichier CSV de données (hors git) : retirées en gardant la première et l'ordre -> SÛR.
    Deux lignes qui portent la même valeur dans `colonne_cle` mais diffèrent ailleurs -> RISQUÉ (laquelle garder ? Liam décide)."""
    import csv
    p = Path(chemin)
    if not p.exists(): return []
    nom = p.name
    try: lignes = list(csv.reader(p.read_text(encoding="utf-8-sig").splitlines()))
    except (OSError, ValueError) as e:
        return [risque(agent, f"{nom} illisible", f"{type(e).__name__} : rien n'est réécrit", cle=f"{chemin}|illisible")]
    if len(lignes) < 2: return []
    entete, corps = lignes[0], [l for l in lignes[1:] if any(str(c).strip() for c in l)]
    out = []
    vus, doublons = set(), 0
    for l in corps:
        s = "\u001f".join(l)
        if s in vus: doublons += 1
        else: vus.add(s)
    if doublons:
        def rep():
            txt = p.read_text(encoding="utf-8-sig").splitlines()
            ls = list(csv.reader(txt)); garde, propre = set(), []
            for l in ls[1:]:
                s = "\u001f".join(l)
                if s in garde: continue
                garde.add(s); propre.append(l)
            buf = io.StringIO()
            w = csv.writer(buf, lineterminator="\n"); w.writerow(ls[0]); w.writerows(propre)
            p.write_text(buf.getvalue(), encoding="utf-8")
            return f"{nom} : {doublons} ligne(s) en double retirée(s) (la première est gardée)"
        out.append(sur(agent, f"{doublons} ligne(s) en double dans {nom}", rep, "lignes strictement identiques", cle=f"{chemin}|lignes|doublons"))
    if colonne_cle and colonne_cle in entete:
        i = entete.index(colonne_cle)
        par_cle = {}
        for l in corps:
            if i < len(l): par_cle.setdefault(str(l[i]).strip(), set()).add("\u001f".join(l))
        melanges = sorted(k for k, v in par_cle.items() if k and len(v) > 1)
        if melanges:
            out.append(risque(agent, f"{len(melanges)} {colonne_cle}(s) en double avec des valeurs différentes dans {nom}",
                              f"{', '.join(melanges[:5])} : deux fiches pour la même clé, Liam choisit laquelle garder", cle=f"{chemin}|{colonne_cle}|conflit"))
    return out


def lignes_csv(chemin):
    """[{colonne: valeur}] d'un CSV de données, [] s'il est absent ou illisible (un CSV n'est jamais réécrit par un contrôle de lecture)."""
    import csv
    p = Path(chemin)
    if not p.exists(): return []
    try: rows = list(csv.reader(p.read_text(encoding="utf-8-sig").splitlines()))
    except (OSError, ValueError): return []
    if len(rows) < 2: return []
    e = rows[0]
    return [{e[i]: (l[i] if i < len(l) else "") for i in range(len(e))} for l in rows[1:] if any(str(c).strip() for c in l)]


def controle_financier(agent, chemin, attendu):
    """Fichier d'ARGENT (paiements, devis, montants) : tout écart est signalé, RIEN n'est jamais corrigé — même une clé manquante
    (remettre « dernier_ts » à zéro ferait réannoncer d'anciens paiements). Décision de Liam : un superviseur ne touche pas à l'argent."""
    d, pb = lire_json(chemin)
    if pb: return [pb]
    if d is None: return []
    nom = Path(chemin).name
    if not isinstance(d, dict): return [risque(agent, f"{nom} n'est pas un objet JSON", "fichier d'argent : rien n'est touché", cle=f"{chemin}|racine")]
    out = []
    for cle, typ in attendu.items():
        if cle not in d:
            out.append(risque(agent, f"clé « {cle} » absente de {nom}", "fichier d'argent : jamais complété tout seul (risque de réannoncer d'anciens paiements)", cle=f"{chemin}|{cle}|absente"))
        elif not isinstance(d[cle], typ):
            out.append(risque(agent, f"« {cle} » de {nom} a un type inattendu", f"{type(d[cle]).__name__} au lieu de {typ.__name__} : rien n'est touché", cle=f"{chemin}|{cle}|type"))
    return out


def controle_disparition(agent, etat, cle_empreinte, valeurs, libelle):
    """Valeurs qui ne doivent pas disparaître d'un passage à l'autre ({identifiant: valeur}, seulement les non vides).
    Une valeur présente au passage précédent et devenue vide ou absente -> RISQUÉ (jamais rétablie tout seule). L'empreinte est gardée dans l'état du superviseur."""
    avant = (etat.get("empreintes") or {}).get(cle_empreinte) or {}
    perdues = sorted(k for k, v in avant.items() if v and not str(valeurs.get(k) or "").strip())
    etat.setdefault("empreintes", {})[cle_empreinte] = {k: str(v) for k, v in valeurs.items() if str(v or "").strip()}
    if not perdues: return []
    return [risque(agent, f"{len(perdues)} {libelle} a/ont disparu depuis le passage précédent",
                   f"{', '.join(perdues[:5])} : rien n'est rétabli, Liam dit s'il faut le remettre", cle=f"{cle_empreinte}|disparition|{date.today().isoformat()}")]


def ref_offre():
    """B2B\\docs\\OFFRE-REFERENCE.json : la référence unique de l'offre. Aucun prix n'est écrit dans un superviseur."""
    import garde as G
    return G.ref()


def fautes_de_texte(texte):
    """Phrases interdites, liens Stripe non autorisés et secrets trouvés dans un texte (référence : OFFRE-REFERENCE.json et la garde du harness)."""
    import garde as G
    try: r = G.ref()
    except Exception: return []
    bas = str(texte or "").lower()
    out = [f"phrase interdite « {p} »" for p in r["phrases_interdites"] if p != "facultative" and p.lower() in bas]
    out += [f"lien de paiement non autorisé (…{l[-6:]})" for l in re.findall(r"https://buy\.stripe\.com/[A-Za-z0-9]+", str(texte or "")) if l not in r["liens_stripe_autorises"]]
    out += [f"secret dans le fichier ({s})" for s in G.secrets_dans(str(texte or ""))]
    return out


# --- un passage complet --------------------------------------------------------------------------------------------
def collecter(controles):
    """Lance chaque contrôle en l'isolant : un contrôle qui casse devient un souci « contrôle impossible » et les autres continuent."""
    out = []
    for nom, f in controles:
        try: out += [s for s in (f() or []) if s]
        except Exception as ex:
            out.append(risque("superviseur", f"contrôle « {nom} » impossible", f"{type(ex).__name__} : à regarder dans le code", cle=f"controle|{nom}"))
    return out


def message(domaine, agents_etat, soucis, verrou_ferme):
    """Résumé court du domaine : où en sont les agents, ce qui a été corrigé, ce qui attend un « go »."""
    corriges = [s for s in soucis if s.corrige]
    bloques = [s for s in soucis if s.risque]
    restants = [s for s in soucis if not s.risque and not s.corrige]
    ko = [f"{n} ({e})" for n, (e, _) in sorted(agents_etat.items()) if e in EN_DEFAUT]
    l = [f"**Superviseur {domaine}** — {len(agents_etat)} agent(s) suivi(s), {len(corriges)} correction(s), {len(bloques)} en attente de « go »",
         "- agents : " + (", ".join(ko) if ko else "tous à l'heure")]
    if corriges: l += ["- corrigé :"] + [f"  - {s.change}" for s in corriges]
    if bloques: l += ["- **bloqué, j'attends « go »** (rien n'a été touché) :"] + [f"  - {s.ligne()}" for s in bloques]
    if restants: l += ["- vu, pas corrigé :"] + [f"  - {s.ligne()}" for s in restants]
    if verrou_ferme: l.append("- _verrou « go superviseurs » fermé : aucune correction appliquée._")
    return "\n".join(l)


def fiche_a_valider(agent, domaine, bloques, jour):
    """B2B\\a-valider\\AAAA-MM-JJ-<agent>.md : ce qui attend le « go » de Liam (rien n'est touché avant). -> chemin ou None."""
    if not bloques: return None
    f = A_VALIDER / f"{jour}-{agent}.md"
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        neuf = not f.exists()
        with f.open("a", encoding="utf-8") as fh:
            if neuf:
                fh.write(f"# Superviseur {domaine} — à valider ({jour})\n\nRien n'a été touché. Chaque ligne attend un « go » de Liam, ou une correction à la main.\n\n")
            fh.write(f"## Passage de {datetime.now():%H:%M}\n\n" + "\n".join(f"- [ ] {s.ligne()}" for s in bloques) + "\n\n")
        return f
    except OSError: return None


def passage(agent, domaine, agents_suivis, controles, conf, essai=False, maintenant=None, dossier_traces=None, relance=None, envoyer=None, etat=None):
    """Un passage complet d'un superviseur. -> (code de sortie, texte du résumé, soucis).
    `essai` : lit tout, affiche, n'écrit rien, n'envoie rien, ne relance rien. `relance` / `envoyer` : doublures des tests.
    `etat` : état déjà chargé par le superviseur, quand un de ses contrôles doit y écrire une empreinte (comparaison avec le passage précédent)."""
    m = maintenant or datetime.now(); jour = f"{m:%Y-%m-%d}"
    ts = taches(); etat = etat_lire(agent) if etat is None else etat
    verrou = not conf["go_superviseurs"] and not essai
    actifs = agents_actifs()
    agents_etat, soucis = {}, []
    for nom in agents_suivis:
        e, detail = etat_agent(nom, m, conf, dossier_traces, ts, actifs)
        agents_etat[nom] = (e, detail)
        if e not in EN_DEFAUT: continue
        deja = (etat["relances"].get(jour) or {}).get(nom)
        if deja:
            soucis.append(risque(nom, f"toujours {e} après une relance", f"{detail} — déjà relancé aujourd'hui ({deja})", cle=f"{nom}|{e}|apres-relance"))
            continue

        def rep(nom=nom, e=e, detail=detail):
            ok, d = (relance or relancer)(nom, ts)
            etat["relances"].setdefault(jour, {})[nom] = d
            return f"agent {nom} {e} ({detail}) : {d}" + ("" if ok else " — à surveiller au prochain passage")
        soucis.append(sur(nom, f"agent {e}", rep, detail, cle=f"{nom}|{e}|{jour}"))
    soucis += collecter(controles)
    for s in soucis:      # corrections sûres seulement : jamais en essai, jamais verrou fermé
        if not s.reparer or essai or verrou: continue
        try:
            s.change = s.reparer() or s.ligne(); s.corrige = True
            etat["corrections"].setdefault(jour, []).append(s.change)
            journaliser(agent, "corrige", s.change)
        except Exception as ex:
            s.change, s.corrige = "", False
            s.detail = (s.detail + " ; " if s.detail else "") + f"correction impossible ({type(ex).__name__})"
    bloques = [s for s in soucis if s.risque]
    nouveaux = [s for s in bloques if s.cle not in etat["en_attente"]]
    texte = message(domaine, agents_etat, soucis, verrou)
    plage = dans_plage(m, conf)
    a_dire = bool(nouveaux) or any(s.corrige for s in soucis) or (jour not in etat["resumes"] and f"{m:%H:%M}" >= conf["heure_resume"])
    if essai: poste = "essai : rien envoyé, rien écrit, rien relancé"
    elif verrou: poste = "verrou « go superviseurs » fermé : rien envoyé"
    elif not a_dire: poste = "rien de neuf à dire (résumé du jour déjà posté)"
    elif not plage: poste = f"hors plage d'envoi ({conf['heure_debut']}-{conf['heure_fin']}) : gardé pour le passage du matin"
    elif conf["envoi_automatique"]: poste = "posté sur Discord" if (envoyer or alerter_discord)(texte) else "Discord : non envoyé, réessayé au prochain passage"
    else: poste = "simulation (envoi_automatique = false) : rien envoyé"
    if not essai and not verrou and not plage:      # la nuit : les corrections sûres sont faites et écrites, rien n'est annoncé ni classé « vu »
        etat_ecrire(agent, etat)
        journaliser(agent, "passage", f"{len(agents_etat)} agent(s), {sum(1 for s in soucis if s.corrige)} correction(s) ; {poste}")
    elif not essai and not verrou:
        f = fiche_a_valider(agent, domaine, nouveaux, jour)
        for s in bloques: etat["en_attente"].setdefault(s.cle, {"depuis": jour, "quoi": s.ligne()[:300]})
        for cle in [k for k in etat["en_attente"] if k not in {s.cle for s in bloques}]: del etat["en_attente"][cle]
        if a_dire and "non envoyé" not in poste: etat["resumes"][jour] = f"{m:%H:%M}"
        etat_ecrire(agent, etat)
        journaliser(agent, "passage", f"{len(agents_etat)} agent(s), {sum(1 for s in soucis if s.corrige)} correction(s), "
                    f"{len(bloques)} en attente ; {poste}" + (f" ; fiche {f.name}" if f else ""))
    print(texte); print(f"  [{poste}]")
    return 0, texte, soucis


def lancer(agent, domaine, agents_suivis, controles, conf, essai=False, maintenant=None, etat=None):
    """Enveloppe d'un passage : une trace du harness par exécution (jamais bloquante), code 2 si le superviseur s'arrête."""
    t0 = time.time()
    try:
        code, _texte, soucis = passage(agent, domaine, agents_suivis, controles, conf, essai, maintenant, etat=etat)
    except ErreurAgent as e:
        print(f"  ! {e}")
        if not essai: T.ecrire(agent, "passage", "échec", time.time() - t0, ok=False, erreur=str(e))
        return 2
    if not essai:
        T.ecrire(agent, "passage", f"{sum(1 for s in soucis if s.corrige)} correction(s), {sum(1 for s in soucis if s.risque)} en attente de go", time.time() - t0, ok=True)
    return code


def resume_pour_jarvis(agent, domaine, conf=None):
    """Ce que la vue Jarvis lit (lecture seule, aucun calcul refait) : ok / corrigé / bloqué, depuis l'état et le journal du superviseur."""
    jour = date.today().isoformat()
    try: e = etat_lire(agent)
    except ErreurAgent as ex: return {"domaine": domaine, "agent": agent, "etat": "inconnu", "detail": str(ex), "corrections": [], "bloques": []}
    p, j = chemins(agent)
    corrections = list(e["corrections"].get(jour) or [])
    bloques = [v.get("quoi", k) for k, v in sorted(e["en_attente"].items())]
    if not p.exists(): etat = "jamais passé"
    elif bloques: etat = "bloqué"
    elif corrections: etat = "corrigé"
    else: etat = "ok"
    dernier = ""
    try:
        if j.exists():
            lignes = [l for l in j.read_text(encoding="utf-8", errors="replace").splitlines() if l.strip()]
            dernier = lignes[-1].split(" | ")[0] if lignes else ""
    except OSError: pass
    return {"domaine": domaine, "agent": agent, "etat": etat, "dernier_passage": dernier, "corrections": corrections, "bloques": bloques,
            "verrou": "fermé" if not (conf or {}).get("go_superviseurs") else "ouvert"}
