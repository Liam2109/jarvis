#!/usr/bin/env python3
"""Agent Instagram (compte lmmultiservices.normandie) : lit la file de docs\\INSTAGRAM-PLAN.md, publie UN post par jour vers 12 h 30 (heure de Paris), coche la ligne avec la date,
fabrique les prochaines cartes quand la file passe sous 3 posts. Même architecture que l'agent de prospection : script autonome, réglages, état, verrou, arrêt de secours.

  python agents\\instagram.py jour [--a-blanc]       un passage : publie (ou SIMULE) le prochain post si c'est l'heure
  python agents\\instagram.py continu [--pid N]      boucle (lancée par Jarvis, lib\\instagram.ps1) : un passage toutes les cycle_minutes, s'arrête si Jarvis s'arrête
  python agents\\instagram.py file                   file des publications : prochain post, lignes bloquées et pourquoi
  python agents\\instagram.py visuels [--a-blanc]    file sous file_minimum : fabrique les prochaines cartes (à valider par Liam tant que envoi_automatique = false)
  python agents\\instagram.py valider                ajoute à la file les cartes que Liam a passées à « validé » dans instagram-a-valider.md
  python agents\\instagram.py arreter                arrêt de secours de la boucle (au prochain battement, 5 s)
  python agents\\instagram.py reprendre              lève la suspension après une erreur (connexion perdue, vérification de sécurité, erreur, publication incertaine)

Règles de Liam (docs\\INSTAGRAM-PLAN.md) : une seule publication par jour ; jamais de mot de passe saisi ; connexion perdue, vérification de sécurité ou erreur = ARRÊT IMMÉDIAT et alerte Discord, aucune reprise
automatique ; aucune information inventée (légendes du plan seulement, « exemple, pas un site client ») ; aucun message privé, commentaire ni abonnement ; journal de chaque action (agents\\instagram-journal.log).
envoi_automatique = false (défaut) = SIMULATION : rien n'est publié, rien n'est coché. --a-blanc : aucune écriture du tout.
Voie de publication : API officielle Instagram (Graph API, compte professionnel relié à la Page Facebook), jeton dans agents\\instagram-token.json (hors git, jamais affiché, envoyé en en-tête seulement)."""
import argparse, json, mimetypes, re, subprocess, sys, time, urllib.error, urllib.parse, urllib.request, uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

ICI = Path(__file__).resolve().parent
RACINE = ICI.parent
sys.path.insert(0, str(ICI))
import machine as M   # config locale (<agent>-config.local.json) et machine active (b2b.local.json)
PLAN, DOSSIER, A_VALIDER = RACINE / "docs" / "INSTAGRAM-PLAN.md", RACINE / "instagram", RACINE / "instagram-a-valider.md"
CONFIG, ETAT, JETON = ICI / "instagram-config.json", ICI / "instagram-etat.json", ICI / "instagram-token.json"
ARRET, VERROU, JOURNAL = ICI / "instagram.arret", ICI / "instagram-continu.verrou", ICI / "instagram-journal.log"
DEFAUT = {"envoi_automatique": False, "heure_publication": "12:30", "fenetre_minutes": 90, "cycle_minutes": 5, "file_minimum": 3, "graph_version": "v21.0",
          "poll_essais": 30, "poll_pause_s": 10, "image_url_base": "", "sources_cartes": [], "salon_nom": ""}
INTERDITS = re.compile(r"garanti|n°\s?1|num[ée]ro\s?1|meilleur|premi[èe]re page|classement|t[ée]moignage|\bavis\b|clients? satisfaits|\d+\s?clients|★|⭐|certifi|\blabel\b|\d\s?(?:€|euros?)", re.I)
LIGNE = re.compile(r"^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|\s*$")
_LIRE = object()   # jeton : « à lire dans le fichier » (None = absent)


# --- réglages, état, journal ---------------------------------------------------------------------------------------
def cfg():
    c = dict(DEFAUT)
    if CONFIG.exists(): c.update({k: v for k, v in json.loads(CONFIG.read_text(encoding="utf-8-sig")).items() if not k.startswith("_")})
    return M.surcharge_locale(CONFIG, c)


def etat_lire():
    e = json.loads(ETAT.read_text(encoding="utf-8")) if ETAT.exists() else {}
    for k in ("publications", "simulations", "alertes"): e.setdefault(k, {})
    return e


def etat_ecrire(e): ETAT.write_text(json.dumps(e, ensure_ascii=False, indent=1), encoding="utf-8")


def journaliser(action, detail="", a_blanc=False):
    """Une ligne par action : date heure | action | détail. Jamais de jeton ni de mot de passe."""
    if a_blanc: return
    with open(JOURNAL, "a", encoding="utf-8") as f: f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} | {action} | {detail}\n")


def heure_paris(n=None):
    """Date et heure à Paris (heure d'été comprise), sans dépendre de la base de fuseaux de Windows. Résultat sans fuseau."""
    n = n or datetime.now(timezone.utc)
    try:
        from zoneinfo import ZoneInfo
        return n.astimezone(ZoneInfo("Europe/Paris")).replace(tzinfo=None)
    except Exception: pass
    u = n.astimezone(timezone.utc).replace(tzinfo=None)
    def dernier_dimanche(m): d = datetime(u.year, m, 31, 1); return d - timedelta(days=(d.weekday() + 1) % 7)
    return u + timedelta(hours=2 if dernier_dimanche(3) <= u < dernier_dimanche(10) else 1)


def moment(maintenant, conf):
    """« trop_tot » avant l'heure de publication, « ok » pendant la fenêtre (90 min), « trop_tard » après : pas de publication tardive."""
    h, m = (int(x) for x in conf["heure_publication"].split(":"))
    debut = maintenant.replace(hour=h, minute=m, second=0, microsecond=0)
    return "trop_tot" if maintenant < debut else "ok" if maintenant <= debut + timedelta(minutes=conf["fenetre_minutes"]) else "trop_tard"


# --- le plan : file, légendes, cases à cocher ------------------------------------------------------------------------
def lire_plan(texte):
    return [{"n": int(m.group(1)), "fichier": m.group(2), "etat": m.group(3), "date": m.group(4)} for m in (LIGNE.match(l) for l in texte.splitlines()) if m]


def lire_legendes(texte):
    sect = texte.partition("## Légendes")[2]
    return {int(m.group(1)): m.group(2).strip() for m in (re.match(r"^(\d+)\.\s+(.+)$", l) for l in sect.splitlines()) if m}


def cocher(texte, n, jour):
    """Passe la ligne n° n à « publié » avec la date ; les autres lignes ne changent pas."""
    sortie = []
    for l in texte.split("\n"):
        m = LIGNE.match(l)
        sortie.append(f"| {n} | {m.group(2)} | publié | {jour} |" if m and int(m.group(1)) == n else l)
    return "\n".join(sortie)


def ajouter_au_plan(texte, n, fichier, legende):
    """Ajoute la ligne « à publier » après la dernière du tableau et la légende après la dernière numérotée (sections existantes, rien d'autre ne change)."""
    lignes = texte.split("\n"); idx = [i for i, l in enumerate(lignes) if LIGNE.match(l)]
    lignes.insert(idx[-1] + 1, f"| {n} | {fichier} | à publier | |")
    deb = next((i for i, l in enumerate(lignes) if l.startswith("## Légendes")), None)
    if deb is None: return "\n".join(lignes).rstrip("\n") + f"\n\n## Légendes\n{n}. {legende}\n"
    fin = max((i for i in range(deb, len(lignes)) if re.match(r"^\d+\.\s", lignes[i])), default=deb)
    lignes.insert(fin + 1, f"{n}. {legende}")
    return "\n".join(lignes)


def legende_ok(t):
    """'' si la légende peut partir, sinon le motif. Aucune promesse, aucun avis ni chiffre de clients : seules les légendes écrites dans le plan partent."""
    if not (t or "").strip(): return "légende vide"
    if len(t) > 2200: return "légende de plus de 2200 caractères (limite d'Instagram)"
    m = INTERDITS.search(t)
    return f"mot interdit : « {m.group(0)} » (promesse, avis, chiffre de clients ou label)" if m else ""


def type_de(chemin): return "reel" if Path(chemin).suffix.lower() in (".mp4", ".mov") else "image"


def fichier_ok(chemin):
    p = Path(chemin)
    if not p.is_file(): return f"fichier introuvable ({p.name})"
    if p.suffix.lower() not in (".png", ".jpg", ".jpeg", ".mp4", ".mov"): return f"format non pris en charge ({p.suffix})"
    t = p.stat().st_size
    return "fichier vide" if not t else "image de plus de 8 Mo" if type_de(p) == "image" and t > 8 * 2**20 else ""


def prochain_post(plan, legendes, dossier):
    """(post, raisons). Le premier « à publier » EXACT dont la légende (écrite dans le plan, jamais inventée) et le fichier sont valables ; les lignes bloquées sont expliquées, jamais publiées."""
    raisons, post = [], None
    for p in sorted(plan, key=lambda x: x["n"]):
        if p["etat"].lower().startswith("publié"): continue
        if p["etat"].strip().lower() != "à publier": raisons.append(f"n° {p['n']} : en attente (état « {p['etat']} »)"); continue
        if p["n"] not in legendes: raisons.append(f"n° {p['n']} : pas de légende dans le plan (jamais inventée)"); continue
        motif = legende_ok(legendes[p["n"]]) or fichier_ok(dossier / p["fichier"])
        if motif: raisons.append(f"n° {p['n']} : {motif}"); continue
        post = post or {"n": p["n"], "type": type_de(p["fichier"]), "fichier": dossier / p["fichier"], "legende": legendes[p["n"]]}
    return post, raisons


def file_restante(plan, legendes, dossier):
    """Nombre de posts publiables maintenant (légende et fichier valables)."""
    return sum(1 for p in plan if p["etat"].strip().lower() == "à publier" and p["n"] in legendes and not legende_ok(legendes[p["n"]]) and not fichier_ok(dossier / p["fichier"]))


# --- API officielle Instagram (Graph API) ----------------------------------------------------------------------------
class ErreurInstagram(Exception):
    """genre : « connexion perdue », « vérification de sécurité » ou « erreur ». publie : le post EST parti (échec seulement à la vérification). incertain : échec pendant la publication même."""
    def __init__(self, genre, detail="", publie=False, incertain=False, resultat=None):
        self.genre, self.publie, self.incertain, self.resultat = genre, publie, incertain, resultat
        super().__init__(f"{genre} : {detail}" if detail else genre)


class ErreurHttp(Exception):
    def __init__(self, statut, corps): self.statut, self.corps = statut, corps; super().__init__(f"HTTP {statut}")


def classer_erreur(statut, corps):
    err = (corps or {}).get("error") or {}; code, sous, msg = err.get("code"), err.get("error_subcode"), str(err.get("message") or "").lower()
    if code == 368 or sous in (459, 460, 464) or re.search(r"checkpoint|security check|challenge|confirm your identity|verify your|vérification de sécurité", msg): return "vérification de sécurité"
    if code in (190, 102) or statut == 401: return "connexion perdue"
    return "erreur"


def jeton_lu(chemin=None):
    """{access_token, ig_user_id, page_id} d'agents\\instagram-token.json, ou None s'il manque. Jamais affiché."""
    try: j = json.loads(Path(chemin or JETON).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError): return None
    return j if j.get("access_token") and j.get("ig_user_id") else None


def http_graph(conf, jeton):
    """Transport réel : https://graph.facebook.com/<version>/<chemin> ; le jeton part dans l'en-tête Authorization (jamais dans l'adresse ni dans un journal). Erreur -> ErreurHttp."""
    def appel(methode, chemin, params=None, fichier=None, entetes=None, url=None):
        adresse = url or f"https://graph.facebook.com/{conf['graph_version']}/{chemin}"; h = {"Authorization": ("OAuth " if url else "Bearer ") + jeton["access_token"], **(entetes or {})}; corps = None
        if methode == "GET" and params: adresse += "?" + urllib.parse.urlencode(params)
        elif fichier and url: corps = Path(fichier).read_bytes(); h["Content-Type"] = "application/octet-stream"   # envoi par morceau unique d'une vidéo (upload « resumable »)
        elif fichier:
            lim = uuid.uuid4().hex; p = Path(fichier); nom = p.name; mime = mimetypes.guess_type(nom)[0] or "application/octet-stream"
            champs = "".join(f'--{lim}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n' for k, v in (params or {}).items()).encode()
            corps = champs + f'--{lim}\r\nContent-Disposition: form-data; name="source"; filename="{nom}"\r\nContent-Type: {mime}\r\n\r\n'.encode() + p.read_bytes() + f"\r\n--{lim}--\r\n".encode()
            h["Content-Type"] = "multipart/form-data; boundary=" + lim
        elif methode == "POST": corps = urllib.parse.urlencode(params or {}).encode()
        try:
            with urllib.request.urlopen(urllib.request.Request(adresse, data=corps, method=methode, headers=h), timeout=120) as r: return json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            try: c = json.loads(e.read() or b"{}")
            except ValueError: c = {}
            raise ErreurHttp(e.code, c) from None
        except (urllib.error.URLError, OSError, ValueError): raise ErreurHttp(0, {}) from None
    return appel


class PublieurApi:
    """Publie un post par l'API officielle : image (déposée NON publiée sur la Page Facebook pour obtenir une adresse d'image, ou image_url_base) ou reel (envoi direct du fichier) ; attend le traitement ;
    publie ; vérifie sur le profil que la légende est la bonne. `http` : transport (faux dans les tests)."""
    def __init__(self, conf, jeton, http, dormir=time.sleep): self.conf, self.j, self.http, self.dormir = conf, jeton, http, dormir

    def publier(self, post, maintenant=None):
        etape = ["préparation"]
        try: return self._publier(post, etape)
        except ErreurHttp as e:
            msg = str(((e.corps or {}).get("error") or {}).get("message") or "")[:150]
            raise ErreurInstagram(classer_erreur(e.statut, e.corps), f"HTTP {e.statut} {msg}".strip(), incertain=etape[0] == "publication") from None

    def _attendre(self, ct):
        for _ in range(self.conf["poll_essais"]):
            s = self.http("GET", ct, {"fields": "status_code"}).get("status_code")
            if s == "FINISHED": return
            if s in ("ERROR", "EXPIRED"): raise ErreurInstagram("erreur", f"traitement du média refusé (statut {s})")
            self.dormir(self.conf["poll_pause_s"])
        raise ErreurInstagram("erreur", "traitement du média trop long")

    def _publier(self, post, etape):
        ig, h = self.j["ig_user_id"], self.http
        if post["type"] == "reel":
            r = h("POST", f"{ig}/media", {"media_type": "REELS", "upload_type": "resumable", "caption": post["legende"]}); ct = r["id"]
            h("POST", None, None, post["fichier"], {"offset": "0", "file_size": str(Path(post["fichier"]).stat().st_size)}, r["uri"])
        else:
            if self.conf.get("image_url_base"): adresse = self.conf["image_url_base"].rstrip("/") + "/" + urllib.parse.quote(Path(post["fichier"]).name)
            else:
                if not self.j.get("page_id"): raise ErreurInstagram("erreur", "Page Facebook absente du jeton : aucune adresse d'image possible")
                ph = h("POST", f"{self.j['page_id']}/photos", {"published": "false"}, post["fichier"])["id"]
                adresse = h("GET", ph, {"fields": "images"})["images"][0]["source"]
            ct = h("POST", f"{ig}/media", {"image_url": adresse, "caption": post["legende"]})["id"]
        self._attendre(ct)
        etape[0] = "publication"; med = h("POST", f"{ig}/media_publish", {"creation_id": ct})["id"]; etape[0] = "vérification"
        info = h("GET", med, {"fields": "permalink,caption,timestamp"}); res = {"id": med, "permalink": info.get("permalink", "")}
        if " ".join(str(info.get("caption", "")).split()) != " ".join(post["legende"].split()):
            raise ErreurInstagram("erreur", "vérification du profil : la légende publiée n'est pas celle prévue", publie=True, resultat=res)
        return res


# --- alertes Discord (une seule par motif et par jour) -----------------------------------------------------------------
def alerter_discord(texte):
    """Message dans le salon de Liam (bot Jarvis, API REST ; jeton lu dans Jarvis\\.env, jamais affiché)."""
    try:
        import prospection as PR
        nom = cfg()["salon_nom"]; acces = PR.acces_discord("salon_instagram_id" if nom else None, nom or None)   # salon par défaut sauf réglage salon_nom
        if not acces: return False
        jeton, salon, uid = acces
        r = PR.discord(jeton, "POST", f"/channels/{salon}/messages", {"content": f"<@{uid}> **Instagram** : {texte}"[:1900], "allowed_mentions": {"users": [uid]}})
        return bool(r and "id" in r)
    except Exception as e: print(f"  alerte Discord impossible ({type(e).__name__})"); return False


def alerter(etat, cle, texte, alerte, jour, a_blanc=False):
    k = f"{jour}|{cle}"
    if a_blanc or etat["alertes"].get(k): return
    etat["alertes"][k] = True; etat_ecrire(etat); journaliser("alerte", f"{cle} : {texte}"[:300]); alerte(texte)


# --- le passage du jour --------------------------------------------------------------------------------------------------
def cmd_jour(conf, a_blanc=False, maintenant=None, publieur=None, alerte=None, jeton=_LIRE):
    """Un passage. -> {"action": ...}. Actions : attente, rien, manqué, file vide, simulation, publié, arrêt."""
    maintenant = maintenant or heure_paris(); jour = str(maintenant.date()); alerte = alerte or alerter_discord; etat = etat_lire()

    def fin(action, detail="", **k):
        journaliser(action, detail, a_blanc); print(f"  Instagram : {action}" + (f" ({detail})" if detail else "")); return {"action": action, **k}

    def arret(genre, detail, garder_en_cours=False):
        if not a_blanc:
            etat["suspendu"] = {"raison": genre, "date": jour, "detail": detail[:200]}
            if not garder_en_cours: etat.pop("en_cours", None)
            etat_ecrire(etat)
        alerter(etat, f"arret|{genre}", f"Publication arrêtée ({genre}) : {detail}. Rien n'est republié automatiquement : vérifie le compte puis `python agents\\instagram.py reprendre`.", alerte, jour, a_blanc)
        return fin("arrêt", f"{genre} : {detail}", raison=genre)

    if etat.get("suspendu"): return fin("arrêt", "suspendu : " + etat["suspendu"]["raison"], raison=etat["suspendu"]["raison"])
    if etat.get("en_cours"): return arret("publication incertaine", f"le post n° {etat['en_cours'].get('n')} était en cours de publication ; contrôle le profil avant toute reprise", garder_en_cours=True)
    texte = PLAN.read_text(encoding="utf-8"); plan, leg = lire_plan(texte), lire_legendes(texte)
    if jour in etat["publications"] or any(p["etat"].lower().startswith("publié") and p["date"] == jour for p in plan): return fin("rien", "déjà publié aujourd'hui")
    m = moment(maintenant, conf)
    if m == "trop_tot": return fin("attente", f"publication à {conf['heure_publication']}")
    if m == "trop_tard":
        alerter(etat, "manque", f"Publication manquée aujourd'hui (après {conf['heure_publication']} + {conf['fenetre_minutes']} min) : rien n'est publié en retard, prochain essai demain.", alerte, jour, a_blanc)
        return fin("manqué", "fenêtre dépassée")
    simulation = not conf["envoi_automatique"] or a_blanc
    if not conf["envoi_automatique"] and jour in etat["simulations"]: return fin("rien", "déjà simulé aujourd'hui")
    post, raisons = prochain_post(plan, leg, DOSSIER)
    for r in raisons: journaliser("ligne bloquée", r, a_blanc)
    if not post:
        alerter(etat, "file-vide", "File des publications vide ou bloquée : " + (" ; ".join(raisons) or "plus aucune ligne « à publier »") + ". Rien n'est publié ni inventé.", alerte, jour, a_blanc)
        return fin("file vide", "; ".join(raisons))
    if simulation:
        if not a_blanc: etat["simulations"][jour] = {"n": post["n"], "fichier": post["fichier"].name}; etat_ecrire(etat)
        return fin("simulation", f"n° {post['n']} {post['fichier'].name} : aurait été publié (envoi_automatique = false)", n=post["n"])
    if publieur is None:
        j = jeton_lu() if jeton is _LIRE else jeton
        if not j: return arret("connexion perdue", "jeton Instagram absent ou incomplet (agents\\instagram-token.json) : jamais de mot de passe saisi par l'agent")
        publieur = PublieurApi(conf, j, http_graph(conf, j))
    etat["en_cours"] = {"jour": jour, "n": post["n"], "etape": "création"}; etat_ecrire(etat)
    verif = ""   # le post est parti mais le profil ne montre pas la bonne légende : on coche (jamais de seconde publication), puis arrêt et alerte
    try: res = publieur.publier(post, maintenant)
    except ErreurInstagram as e:
        if e.publie: res, verif = e.resultat or {}, str(e).partition(" : ")[2] or e.genre
        elif e.incertain: return arret("publication incertaine", f"échec PENDANT la publication du post n° {post['n']} ({e.genre}) : contrôle le profil avant toute reprise", garder_en_cours=True)
        else: return arret(e.genre, str(e).partition(" : ")[2] or e.genre)
    except Exception as e: return arret("erreur", type(e).__name__)
    PLAN.write_text(cocher(texte, post["n"], jour), encoding="utf-8")
    etat.pop("en_cours", None); etat["publications"][jour] = {"n": post["n"], "id": res.get("id", ""), "permalink": res.get("permalink", "")}; etat_ecrire(etat)
    journaliser("publié", f"n° {post['n']} {post['fichier'].name} {res.get('permalink', '')}")
    if verif: return arret("erreur", verif)
    return fin("publié", f"n° {post['n']} {res.get('permalink', '')}", n=post["n"], permalink=res.get("permalink", ""))


# --- visuels : cartes fabriquées depuis les pages métier quand la file passe sous file_minimum ------------------------------
def legende_carte(s):
    art, nom = s.get("article", "un"), s.get("nom_fictif", "")
    base = f"Exemple de page pour {art} {s['metier']}. " + (f"« {nom} » est un nom fictif : ce n'est pas un site client. Votre page, avec vos photos et vos informations." if nom else "Ce n'est pas un site client : c'est ce que je peux réaliser avec vos photos et vos informations.")
    return f"{base} Devis écrit avant de commencer. {s.get('hashtags', '')}".strip()


def chemin_capture(s):
    p = Path(s["capture"]); return p if p.is_absolute() else RACINE / p   # relatif à B2B si non absolu


def rendre_carte(source, sortie):
    """Carte 1080 x 1350 (identité du compte) rendue par Edge sans fenêtre : sites\\outils\\instagram-carte.mjs. Une seule session de navigateur, priorité basse (nav-leger)."""
    import os
    if M.serveur(): raise RuntimeError("profil serveur : aucun navigateur, carte non rendue")
    cmd = ["node", str(RACINE / "sites" / "outils" / "instagram-carte.mjs"), json.dumps({"titre": source.get("titre", source["metier"]), "kicker": source.get("kicker", "Exemple de page"), "capture": str(chemin_capture(source)), "pied": "Exemple, pas un site client · avec vos photos et vos informations", "sortie": str(sortie)})]
    subprocess.run(cmd, check=True, timeout=240, cwd=str(RACINE / "sites" / "outils"), env={**os.environ, "NAV_CANAL": "msedge"})


def lire_propositions():
    out = []
    for m in re.finditer(r"^## .+?(?=^## |\Z)", A_VALIDER.read_text(encoding="utf-8") if A_VALIDER.exists() else "", re.M | re.S):
        b = m.group(0); me = re.search(r"<!-- meta:(\{.*?\}) -->", b); st = re.search(r"\*\*Statut : (.+?)\*\*", b); lg = re.search(r"### Légende\n```\n(.*?)\n```", b, re.S)
        if me and st and lg: out.append({"meta": json.loads(me.group(1)), "statut": st.group(1).strip(), "legende": lg.group(1), "texte": b})
    return out


def cmd_visuels(conf, a_blanc=False, rendre=None):
    if M.serveur(): return {"action": "serveur", "detail": "profil serveur : aucun navigateur, cartes non fabriquées"}
    texte = PLAN.read_text(encoding="utf-8"); plan, leg = lire_plan(texte), lire_legendes(texte)
    restants = file_restante(plan, leg, DOSSIER)
    if restants >= conf["file_minimum"]: return {"action": "assez", "restants": restants}
    props = lire_propositions(); deja = {p["meta"]["cle"] for p in props}; pris = " ".join(p["fichier"] for p in plan)
    manques, a_faire = [], []
    for s in conf.get("sources_cartes") or []:
        if s["cle"] in deja or f"-{s['cle']}." in pris: continue
        if not chemin_capture(s).is_file(): manques.append(f"{s['cle']} : capture introuvable ({s['capture']})"); continue
        a_faire.append(s)
    a_faire = a_faire[:max(0, conf["file_minimum"] - restants - sum(1 for p in props if p["statut"] == "à valider"))]
    if not a_faire: return {"action": "déjà proposé" if any(p["statut"] == "à valider" for p in props) else "rien à fabriquer", "manques": manques}
    n = max([p["n"] for p in plan] + [p["meta"]["n"] for p in props] + [0]); blocs, ajoutes = [], []
    for s in a_faire:
        n += 1; nom = f"{n:02d}-{s['cle']}.png"; leg_s = legende_carte(s)
        if legende_ok(leg_s): manques.append(f"{s['cle']} : légende refusée ({legende_ok(leg_s)})"); continue
        if not a_blanc: (rendre or rendre_carte)(s, DOSSIER / nom)
        if conf["envoi_automatique"] and not a_blanc: texte = ajouter_au_plan(texte, n, nom, leg_s); ajoutes.append(n); journaliser("carte ajoutée", f"n° {n} {nom}"); continue
        meta = json.dumps({"cle": s["cle"], "n": n, "fichier": nom}, ensure_ascii=False)
        blocs.append(f"## Carte {s['metier']} — n° {n}\n<!-- meta:{meta} -->\n**Statut : à valider**\n\n- Fichier : instagram\\{nom}\n- Source : capture de la page exemple ({chemin_capture(s).name}), pas un site client\n\n### Légende\n```\n{leg_s}\n```\n")
    if ajoutes: PLAN.write_text(texte, encoding="utf-8"); return {"action": "ajouté", "ajoutes": ajoutes, "manques": manques}
    if blocs and not a_blanc:
        entete = "# Visuels Instagram à valider\nRien n'entre dans la file sans ton accord : passe le statut d'une carte à « validé » (puis `python agents\\instagram.py valider`, ou le prochain passage de l'agent).\n\n"
        A_VALIDER.write_text((A_VALIDER.read_text(encoding="utf-8").rstrip("\n") + "\n\n" if A_VALIDER.exists() else entete) + "\n".join(blocs), encoding="utf-8"); journaliser("cartes proposées", f"{len(blocs)} à valider")
    return {"action": "proposé" if blocs else "rien à fabriquer", "manques": manques}


def integrer_valides(conf, a_blanc=False):
    """Cartes passées à « validé » par Liam -> ajoutées à la file (ligne « à publier » + légende) après les mêmes contrôles ; -> liste des numéros ajoutés."""
    if not A_VALIDER.exists(): return []
    texte, av, ajoutes = PLAN.read_text(encoding="utf-8"), A_VALIDER.read_text(encoding="utf-8"), []
    for p in lire_propositions():
        if p["statut"].lower() != "validé": continue
        m = p["meta"]
        if legende_ok(p["legende"]) or fichier_ok(DOSSIER / m["fichier"]) or any(x["n"] == m["n"] for x in lire_plan(texte)): continue
        texte = ajouter_au_plan(texte, m["n"], m["fichier"], p["legende"]); ajoutes.append(m["n"])
        av = av.replace(p["texte"], p["texte"].replace("**Statut : validé**", f"**Statut : ajouté à la file le {datetime.now():%Y-%m-%d}**"), 1)
    if ajoutes and not a_blanc: PLAN.write_text(texte, encoding="utf-8"); A_VALIDER.write_text(av, encoding="utf-8"); journaliser("cartes ajoutées à la file", ", ".join(f"n° {n}" for n in ajoutes))
    return ajoutes


# --- boucle, arrêt de secours, reprise -------------------------------------------------------------------------------------
def processus_vivant(pid):
    try:
        import ctypes
        k = ctypes.windll.kernel32; h = k.OpenProcess(0x1000, False, int(pid))
        if not h: return False
        code = ctypes.c_ulong(); ok = k.GetExitCodeProcess(h, ctypes.byref(code)); k.CloseHandle(h)
        return bool(ok) and code.value == 259
    except (ImportError, AttributeError):
        import os
        try: os.kill(int(pid), 0); return True
        except OSError: return False


def boucle_active():
    try: return VERROU.exists() and processus_vivant(int(VERROU.read_text(encoding="utf-8").strip()))
    except (ValueError, OSError): return False


def cmd_continu(conf, a_blanc=False, dormir=time.sleep, maintenant=heure_paris, publieur=None, alerte=None, vivant=None, jeton=_LIRE, rendre=None):
    """Un passage toutes les cycle_minutes jusqu'à l'arrêt : `arreter`, Jarvis arrêté (--pid), suspension après une erreur. Jamais de reprise automatique après une erreur."""
    import os
    if a_blanc: print(f"  [à blanc] boucle Instagram : un passage toutes les {conf['cycle_minutes']} min, publication à {conf['heure_publication']}, " + ("RÉELLE" if conf["envoi_automatique"] else "SIMULATION") + ". Rien lancé."); return "à blanc"
    if boucle_active(): print("Une boucle Instagram tourne déjà (instagram-continu.verrou)."); return "déjà lancée"
    prochain, raison = 0, ""

    def bat():
        VERROU.write_text(str(os.getpid()), encoding="utf-8")
        if ARRET.exists(): return "arrêt demandé"
        if vivant and not vivant(): return "Jarvis s'est arrêté"
        s = etat_lire().get("suspendu")
        return f"suspendu ({s['raison']})" if s else ""
    try:
        while not raison:
            raison = bat()
            if raison: break
            if maintenant().timestamp() >= prochain:
                try:
                    cmd_jour(conf, False, maintenant(), publieur, alerte, jeton)
                    integrer_valides(conf, False)
                    if not etat_lire().get("suspendu") and conf.get("sources_cartes"): cmd_visuels(conf, False, rendre)
                except Exception as ex:   # filet : une erreur inattendue arrête la publication et prévient Liam, sans reprise automatique
                    e = etat_lire(); e["suspendu"] = {"raison": "erreur", "date": str(maintenant().date()), "detail": type(ex).__name__}; etat_ecrire(e)
                    journaliser("erreur", type(ex).__name__); (alerte or alerter_discord)(f"Erreur inattendue ({type(ex).__name__}) : l'agent s'arrête. Vérifie puis `python agents\\instagram.py reprendre`.")
                prochain = maintenant().timestamp() + conf["cycle_minutes"] * 60
            dormir(5)
    finally:
        VERROU.unlink(missing_ok=True)
        if raison.startswith("arrêt"): ARRET.unlink(missing_ok=True)
        journaliser("boucle arrêtée", raison)
    return raison


def reprendre():
    e = etat_lire(); s = e.pop("suspendu", None); e.pop("en_cours", None); etat_ecrire(e); journaliser("reprise", f"suspension levée ({s['raison']})" if s else "rien à lever")
    return f"Suspension levée ({s['raison']}) : contrôle le profil, la boucle reprendra au prochain lancement." if s else "Aucune suspension."


def cmd_file(conf):
    texte = PLAN.read_text(encoding="utf-8"); plan, leg = lire_plan(texte), lire_legendes(texte); post, raisons = prochain_post(plan, leg, DOSSIER); e = etat_lire()
    print(f"Mode : {'RÉEL (envoi_automatique = true)' if conf['envoi_automatique'] else 'SIMULATION (envoi_automatique = false)'} · publication à {conf['heure_publication']} (Paris)" + (f" · SUSPENDU : {e['suspendu']['raison']}" if e.get("suspendu") else ""))
    print(f"File : {file_restante(plan, leg, DOSSIER)} post(s) publiable(s) (minimum {conf['file_minimum']}) ; prochain : " + (f"n° {post['n']} {post['fichier'].name}" if post else "aucun"))
    for r in raisons: print("  bloqué : " + r)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Agent Instagram LM MULTI-SERVICES (simulation par défaut)."); ap.add_argument("cmd", choices=["jour", "continu", "file", "visuels", "valider", "arreter", "reprendre"])
    ap.add_argument("--a-blanc", action="store_true"); ap.add_argument("--pid", type=int, default=0); a = ap.parse_args(); M.exiger("instagram", a.cmd, a.a_blanc); conf = cfg()
    if a.cmd == "jour": cmd_jour(conf, a.a_blanc)
    elif a.cmd == "continu": cmd_continu(conf, a.a_blanc, vivant=(lambda: processus_vivant(a.pid)) if a.pid else None)
    elif a.cmd == "file": cmd_file(conf)
    elif a.cmd == "visuels": print(cmd_visuels(conf, a.a_blanc))
    elif a.cmd == "valider": print("Ajoutées à la file :", integrer_valides(conf, a.a_blanc) or "aucune")
    elif a.cmd == "arreter":
        if boucle_active(): ARRET.write_text(str(int(time.time())), encoding="utf-8"); print("Arrêt demandé : la boucle s'arrête dans quelques secondes.")
        else: ARRET.unlink(missing_ok=True); VERROU.unlink(missing_ok=True); print("Aucune boucle Instagram en cours.")
    else: print(reprendre())


if __name__ == "__main__":
    main()
