"""Pont Discord de Jarvis : LOGIQUE (aucun réseau, aucun import de discord.py), donc testable avec un faux client.

Rôle : filtrer ce qui vient de Discord (un seul utilisateur, des salons listés), l'écrire dans un dossier d'échange que Jarvis lit
(memoire\\discord\\entrant), et envoyer sur Discord ce que Jarvis dépose dans memoire\\discord\\sortant.
Règles : jamais de jeton dans une sortie, jamais le contenu d'un message d'un inconnu (même pas dans le journal), aucune réponse à un inconnu.
"""
import asyncio
import json
import os
import re
import sys
import time
import unicodedata
import uuid
from collections import deque
from pathlib import Path

NOMS_SALONS = ("jarvis", "systeme", "marche", "business")      # jarvis : discussion et to-do · systeme : alertes, journal, rapports · marche : résumés et cours · business : SaaS, revenus, leads
ALIAS_FORCES = {"alertes": "systeme", "todo": "jarvis"}          # anciens noms de config.json, toujours acceptés pour forcer un identifiant
LONGUEUR_MAX = 1000          # un ordre plus long est refusé poliment
MORCEAU_MAX = 1900           # Discord limite un message à 2000 caractères
SAISIE_MAX_S = 180           # « en train d'écrire » : jamais plus de 3 minutes
EXTENSIONS_AUDIO = (".mp3", ".wav", ".ogg", ".m4a")
TAILLE_AUDIO_MAX = 8 * 1024 * 1024
REGLAGES_CONVERSATION = ("discord_conversation", "conversation_modele", "conversation_modele_rapide", "conversation_modele_cli", "conversation_modele_cli_capable", "discord_conversation_modele", "discord_conversation_modele_cli",
                         "discord_claude_max_par_jour", "valeurs_suivies", "humour_taux", "humour_pourcent")
EMOJI_OUI = "✅"         # ✅
EMOJI_NON = "❌"         # ❌

MOTS_OUI = {"oui", "ouais", "ok", "okay", "d'accord", "dac", "vas-y", "vas y", "go", "confirme", "je confirme", "fais-le", "fais le",
            "yes", "y", "volontiers", "bien sur", "affirmatif", "c'est bon", "allez"}
MOTS_NON = {"non", "no", "n", "annule", "annuler", "laisse", "laisse tomber", "pas maintenant", "refuse", "nope", "negatif", "surtout pas"}
MOTS_STOP = {"stop", "jarvis stop", "arret d'urgence", "jarvis arret d'urgence", "arrete tout", "jarvis arrete tout", "urgence"}

MOTIF_JETON = re.compile(r"[A-Za-z0-9_-]{23,28}\.[A-Za-z0-9_-]{6,7}\.[A-Za-z0-9_-]{27,}")


def normaliser(texte):
    t = unicodedata.normalize("NFD", (texte or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = t.replace("’", "'").replace("‘", "'")
    t = re.sub(r"[.,!?;:]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def normaliser_nom(nom):
    """Nom de salon sans majuscules, accents, emojis, tirets ni séparateurs (« 🤖｜Système-Logs » -> « systemelogs »)."""
    t = unicodedata.normalize("NFKD", str(nom or "")).lower()
    return re.sub(r"[^a-z0-9]+", "", "".join(c for c in t if unicodedata.category(c) != "Mn"))


def associer_salons(salons):
    """salons : liste de (identifiant, nom). Retourne {clé: identifiant} pour jarvis / systeme / marche / business, par mot-clé dans le nom.
    Nom exact d'abord, sinon le nom le plus court qui contient le mot-clé ; un salon ne sert qu'à une clé."""
    norm = [(int(i), normaliser_nom(n)) for i, n in salons]
    pris, res = set(), {}
    for cle in NOMS_SALONS:
        cands = sorted((len(n), 0 if n == cle else 1, i) for i, n in norm if cle in n and i not in pris)
        cands.sort(key=lambda c: (c[1], c[0], c[2]))
        if cands:
            res[cle] = cands[0][2]
            pris.add(cands[0][2])
    return res


def diagnostiquer_salons(infos):
    """infos : [{"nom", "voir", "ecrire", "historique"}] des salons textuels que le bot VOIT (Discord n'envoie pas les autres).
    Retourne {"salons": [...], "problemes": [...]} : nom, nom normalisé, mot-clé reconnu, permissions. Aucun identifiant, aucun contenu de message."""
    ident = {i: n for i, n in enumerate(x["nom"] for x in infos)}
    assoc = associer_salons([(i, n) for i, n in ident.items()])
    cle_de = {i: k for k, i in assoc.items()}
    salons, problemes = [], []
    for i, x in enumerate(infos):
        cle = cle_de.get(i)
        salons.append({"nom": x["nom"], "normalise": normaliser_nom(x["nom"]), "cle": cle, "voir": bool(x.get("voir", True)),
                       "ecrire": bool(x.get("ecrire", True)), "historique": bool(x.get("historique", True))})
        if cle and not x.get("ecrire", True):
            problemes.append("« %s » (%s) : le bot ne peut pas y écrire (permission « Envoyer des messages »)" % (x["nom"], cle))
        if cle and not x.get("historique", True):
            problemes.append("« %s » (%s) : le bot ne peut pas lire l'historique (permission « Lire l'historique des messages »)" % (x["nom"], cle))
    for k in NOMS_SALONS:
        if k not in assoc:
            problemes.append("aucun des %d salons visibles par le bot ne contient « %s » : s'il existe, le bot n'a pas la permission « Voir le salon » dessus" % (len(infos), k))
    return {"salons": salons, "problemes": problemes}


async def serveurs_de_liam(serveurs, est_membre):
    """serveurs : [{"id", "salons"}] où le bot se trouve ; est_membre(serveur) -> vrai si DISCORD_USER_ID est membre. Les autres serveurs sont ignorés."""
    res = []
    for g in serveurs:
        try:
            if await est_membre(g):
                res.append({"id": g["id"], "salons": g["salons"], "infos": g.get("infos")})
        except Exception:
            continue
    return res


def interpreter_reponse(texte):
    """'oui' | 'non' | None pour une réponse écrite à une confirmation. Une phrase ambiguë n'est jamais un « oui »."""
    t = normaliser(texte)
    if t in MOTS_OUI:
        return "oui"
    if t in MOTS_NON:
        return "non"
    return None


def est_arret_urgence(texte):
    return normaliser(texte) in MOTS_STOP


def masquer(texte, secrets=()):
    """Retire tout jeton / secret d'un texte destiné à un journal ou à Discord."""
    t = str(texte)
    for s in secrets:
        if s and len(s) >= 8:
            t = t.replace(s, "[SECRET]")
    t = MOTIF_JETON.sub("[SECRET]", t)
    t = re.sub(r"(?i)\b(bot|bearer)\s+\S{20,}", r"\1 [SECRET]", t)
    return t


def neutraliser_mentions(texte):
    """@everyone, @here et mentions : cassées (en plus de allowed_mentions=none côté Discord)."""
    return str(texte).replace("@", "@​")


LIMITES_EMBED = {"titre": 256, "description": 2000, "nom": 256, "valeur": 1024, "pied": 2048, "champs": 25}


def _net(texte, limite, secrets):
    t = neutraliser_mentions(masquer(texte, secrets))
    return t if len(t) <= limite else t[: limite - 1].rstrip() + "\u2026"


def preparer_embed(e, secrets=()):
    """Embed venant de Jarvis -> embed sûr : secrets masqués, mentions cassées, longueurs de Discord respectées, couleur entière."""
    if not isinstance(e, dict):
        return None
    L = LIMITES_EMBED
    try:
        couleur = max(0, min(0xFFFFFF, int(e.get("couleur", 0x3498DB))))
    except (TypeError, ValueError):
        couleur = 0x3498DB
    champs = []
    for c in (e.get("champs") or [])[: L["champs"]]:
        if isinstance(c, dict) and str(c.get("nom", "")).strip() and str(c.get("valeur", "")).strip():
            champs.append({"nom": _net(c["nom"], L["nom"], secrets), "valeur": _net(c["valeur"], L["valeur"], secrets), "inline": bool(c.get("inline", False))})
    r = {"titre": _net(e.get("titre", ""), L["titre"], secrets), "description": _net(e.get("description", ""), L["description"], secrets),
         "couleur": couleur, "champs": champs, "pied": _net(e.get("pied", ""), L["pied"], secrets)}
    def total():
        return len(r["titre"]) + len(r["description"]) + len(r["pied"]) + sum(len(c["nom"]) + len(c["valeur"]) for c in r["champs"])
    while total() > 6000 and r["champs"]:      # limite de Discord : 6000 caractères au total, les derniers champs sautent d'abord
        r["champs"].pop()
    if total() > 6000:
        r["description"] = r["description"][: max(0, len(r["description"]) - (total() - 6000) - 1)] + "…"
    return r if (r["titre"] or r["description"] or r["champs"]) else None


CARTES = {"reponse": ("Réponse", 0x3498DB), "fait": ("C'est fait", 0x2ECC71), "attention": ("Attention", 0xE67E22), "probleme": ("Problème", 0xE74C3C)}


def carte(nature, texte, secrets=()):
    """Message de Jarvis -> carte : la couleur et le titre portent le sens (réponse bleue, fait vert, attention orange, problème rouge), aucun emoji."""
    titre, couleur = CARTES[nature]
    return preparer_embed({"titre": titre, "description": texte, "couleur": couleur}, secrets)


def decouper(texte, taille=MORCEAU_MAX):
    texte = str(texte).strip()
    if not texte:
        return []
    morceaux = []
    while len(texte) > taille:
        coupe = texte.rfind("\n", 0, taille)
        if coupe < taille // 2:
            coupe = texte.rfind(" ", 0, taille)
        if coupe < taille // 2:
            coupe = taille
        morceaux.append(texte[:coupe].rstrip())
        texte = texte[coupe:].lstrip()
    if texte:
        morceaux.append(texte)
    return morceaux


def processus_vivant(pid):
    """Vrai si le processus existe encore (parent de surveillance). Un pid nul = rien à surveiller."""
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return True
    if pid <= 0:
        return True
    if os.name == "nt":
        import ctypes
        k = ctypes.windll.kernel32
        h = k.OpenProcess(0x1000, False, pid)       # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return False
        try:
            code = ctypes.c_ulong()
            return bool(k.GetExitCodeProcess(h, ctypes.byref(code))) and code.value == 259     # STILL_ACTIVE
        finally:
            k.CloseHandle(h)
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


class Echange:
    """Dossier d'échange avec Jarvis : fichiers JSON écrits de façon atomique, un seul écrivain par sous-dossier."""

    def __init__(self, dossier):
        self.dossier = Path(dossier)
        self.entrant = self.dossier / "entrant"      # pont -> Jarvis
        self.sortant = self.dossier / "sortant"      # Jarvis -> pont
        for d in (self.entrant, self.sortant):
            d.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _ecrire(dossier, objet):
        nom = "%019d-%s.json" % (time.time_ns(), uuid.uuid4().hex[:6])
        tmp = dossier / (nom + ".tmp")
        tmp.write_text(json.dumps(objet, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, dossier / nom)

    def poster_entrant(self, objet):
        self._ecrire(self.entrant, objet)

    def poster_sortant(self, objet):         # (utilisé par les tests ; Jarvis écrit lui-même ces fichiers)
        self._ecrire(self.sortant, objet)

    def sortants(self):
        return sorted(self.sortant.glob("*.json"))

    def ecrire_etat(self, objet):
        tmp = self.dossier / "etat.json.tmp"
        tmp.write_text(json.dumps(objet, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self.dossier / "etat.json")


class ConfigJarvis:
    """Lit config.json (relu quand il change) : discord_salons, discord_vocal. Jamais de secret ici."""

    def __init__(self, chemin):
        self.chemin = Path(chemin) if chemin else None
        self._mtime = None
        self._val = {"salons": {}, "vocal": False}      # salons = identifiants FORCÉS à la main (facultatif)
        self.brut = {}

    def reglages(self):
        """Réglages de la conversation directe (config.json / config.local.json), relus quand le fichier change."""
        self.valeurs()
        return self.brut

    def valeurs(self):
        if not self.chemin or not self.chemin.exists():
            return self._val
        try:
            m = self.chemin.stat().st_mtime_ns
            if m != self._mtime:
                brut = json.loads(self.chemin.read_text(encoding="utf-8-sig"))
                loc = self.chemin.with_name("config.local.json")      # réglages propres à cette machine (serveur) : prioritaires, jamais suivis par git
                if loc.exists() and self.chemin.name == "config.json":
                    try:
                        brut.update({k: v for k, v in json.loads(loc.read_text(encoding="utf-8-sig")).items() if k in ("discord_salons", "discord_vocal") or k in REGLAGES_CONVERSATION})
                    except (OSError, ValueError):
                        pass
                salons = {}
                for nom, v in (brut.get("discord_salons") or {}).items():
                    nom = ALIAS_FORCES.get(nom, nom)
                    if nom in NOMS_SALONS and str(v).strip().isdigit():
                        salons[nom] = int(str(v).strip())
                self._val = {"salons": salons, "vocal": brut.get("discord_vocal") is True}
                self.brut = {k: brut[k] for k in REGLAGES_CONVERSATION if k in brut}
                self._mtime = m
        except (OSError, ValueError):
            pass          # config momentanément illisible : on garde les dernières valeurs
        return self._val


class Pont:
    """client : objet asynchrone avec envoyer(canal_id, texte)->id, reaction(canal_id, msg_id, emoji), taper(canal_id, actif),
    envoyer_fichier(canal_id, chemin). (discord.py en vrai, un faux client dans les tests.)"""

    def __init__(self, client, echange, config, user_id, secrets=(), stop_flag=None, journal_sortie=None, horloge=time.monotonic, cache_salons=None, conversation=None):
        self.client = client
        self.echange = echange
        self.config = config
        self.user_id = int(user_id)
        self.secrets = [s for s in secrets if s]
        self.stop_flag = Path(stop_flag) if stop_flag else None
        self._sortie = journal_sortie or (lambda ligne: (sys.stderr.write(ligne + "\n"), sys.stderr.flush()))
        self.horloge = horloge
        self.vus = deque(maxlen=300)
        self.ignores = 0                  # nombre de messages ignorés : un compteur, JAMAIS leur contenu
        self.saisies = {}                 # id du message de Liam -> (canal_id, début)
        self.attentes = {}                # confirm_id -> {msg_id, canal, canal_id, expire}
        self.cache_salons = Path(cache_salons) if cache_salons else self.echange.dossier.parent / "discord-salons.json"
        self.decouverts = {}              # salons associés automatiquement par mot-clé
        self.manquants = list(NOMS_SALONS)
        self._repli_dit = set()
        self.conversation = conversation      # conversation directe (API Anthropic / claude -p allégé), sans PowerShell : voir conversation.py
        self._taches = set()
        self.arret = False
        self.connecte = False
        self._dernier_etat = -1e9

    # ---------- journal (stderr), toujours masqué ----------
    def journal(self, message):
        self._sortie("[pont] " + masquer(message, self.secrets))

    # ---------- Discord -> Jarvis ----------
    def salons(self):
        """Associations automatiques, surchargées par les identifiants forcés de config.json."""
        r = dict(self.decouverts)
        r.update(self.config.valeurs()["salons"])
        return r

    def maj_serveurs(self, candidats):
        """candidats : [{"id": serveur, "salons": [(id, nom), ...]}] pour les serveurs OÙ SE TROUVE Liam (les autres ne sont jamais passés ici).
        Un seul serveur est retenu : celui qui contient le plus de salons reconnus (puis le plus petit identifiant). Écrit le cache memoire\discord-salons.json."""
        meilleur = None
        for c in candidats:
            a = associer_salons(c["salons"])
            cle = (-len(a), int(c["id"]))
            if meilleur is None or cle < meilleur[0]:
                meilleur = (cle, c, a)
        if meilleur is None:
            self.decouverts, serveur = {}, 0
        else:
            self.decouverts, serveur = meilleur[2], int(meilleur[1]["id"])
        if meilleur is not None and meilleur[1].get("infos") is not None:
            diag = diagnostiquer_salons(meilleur[1]["infos"])
            self._ecrire_diagnostic(diag)
        eff = self.salons()
        self.manquants = [n for n in NOMS_SALONS if n not in eff]
        if len(candidats) > 1:
            self.journal("le bot est sur %d serveurs où se trouve Liam : un seul est utilisé" % len(candidats))
        donnees = {"serveur": str(serveur), "salons": {k: str(v) for k, v in self.decouverts.items()}, "manquants": self.manquants, "ts": time.time()}
        try:
            ancien = json.loads(self.cache_salons.read_text(encoding="utf-8")) if self.cache_salons.exists() else None
        except (OSError, ValueError):
            ancien = None
        if not ancien or {k: ancien.get(k) for k in ("serveur", "salons", "manquants")} != {k: donnees[k] for k in ("serveur", "salons", "manquants")}:
            tmp = self.cache_salons.with_suffix(".tmp")
            tmp.write_text(json.dumps(donnees, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, self.cache_salons)
            self.journal("salons associés : %s ; introuvables : %s" % (", ".join(sorted(self.decouverts)) or "aucun", ", ".join(self.manquants) or "aucun"))

    def _ecrire_diagnostic(self, diag):
        """memoire\\discord-diagnostic.json : NOMS de salons et permissions seulement (ni identifiant de message, ni contenu, ni secret)."""
        chemin = self.cache_salons.with_name("discord-diagnostic.json")
        try:
            ancien = json.loads(chemin.read_text(encoding="utf-8")) if chemin.exists() else None
        except (OSError, ValueError):
            ancien = None
        if ancien != diag:
            tmp = chemin.with_suffix(".tmp")
            tmp.write_text(json.dumps(diag, ensure_ascii=False, indent=1), encoding="utf-8")
            os.replace(tmp, chemin)
            for pb in diag["problemes"]:
                self.journal("diagnostic salons : " + pb)

    def _nom_salon(self, canal_id):
        for nom, ident in self.salons().items():
            if ident == canal_id:
                return nom
        return None

    def _attente_du_salon(self, nom):
        for cid, a in self.attentes.items():
            if a["canal"] == nom:
                return cid
        return None

    async def sur_message(self, auteur_id, est_bot, canal_id, msg_id, contenu):
        # 1) SEUL Liam : tout autre auteur (et tout bot) est ignoré en silence, sans réponse ni trace du contenu.
        if est_bot or int(auteur_id) != self.user_id:
            self.ignores += 1
            return
        # 2) Seulement les salons listés dans config.json (discord_salons).
        nom = self._nom_salon(int(canal_id))
        if nom is None:
            self.ignores += 1
            return
        if msg_id in self.vus:
            return
        self.vus.append(msg_id)
        texte = (contenu or "").strip()
        if not texte:
            return
        if len(texte) > LONGUEUR_MAX:
            await self._ecrire_poliment(canal_id, "Ce message est trop long, monsieur (%d caractères au plus)." % LONGUEUR_MAX, "attention")
            return
        if est_arret_urgence(texte):
            self._lever_stop()
            self.echange.poster_entrant({"type": "stop", "canal": nom, "id": str(msg_id), "auteur": str(auteur_id)})
            await self._ecrire_poliment(canal_id, "Arrêt d'urgence demandé, monsieur.", "attention")
            return
        rep = interpreter_reponse(texte)
        cid = self._attente_du_salon(nom) if rep else None
        if cid:
            self.echange.poster_entrant({"type": "reponse", "confirm_id": cid, "reponse": rep, "via": "texte"})
            self.attentes.pop(cid, None)
            return
        if self.conversation is not None and self.conversation.est_diag(texte):
            t = asyncio.ensure_future(self._diagnostic(int(canal_id)))      # « diag » : appels de test et temps mesurés
            self._taches.add(t)
            t.add_done_callback(self._taches.discard)
            return
        if self.conversation is not None and self.conversation.prend(texte):
            t = asyncio.ensure_future(self._conversation(int(canal_id), nom, msg_id, auteur_id, texte))      # réponse directe : aucun PowerShell, aucun Ollama
            self._taches.add(t)
            t.add_done_callback(self._taches.discard)
            return
        await self._vers_jarvis(canal_id, nom, msg_id, auteur_id, texte)

    async def _vers_jarvis(self, canal_id, nom, msg_id, auteur_id, texte):
        self.echange.poster_entrant({"type": "message", "id": str(msg_id), "canal": nom, "canal_id": str(canal_id),
                                     "auteur": str(auteur_id), "texte": texte, "ts": time.time()})
        self.saisies[str(msg_id)] = (int(canal_id), self.horloge())
        try:
            await self.client.taper(int(canal_id), True)           # « Jarvis est en train d'écrire… » pendant qu'il réfléchit
        except Exception as e:
            self.journal("saisie impossible : %s" % type(e).__name__)

    async def _carte_envoyer(self, canal_id, texte, nature="reponse"):
        return await self.client.envoyer(canal_id, "", embed=carte(nature, texte, self.secrets))

    async def _carte_editer(self, canal_id, msg_id, texte, nature="reponse"):
        await self.client.editer(canal_id, msg_id, "", embed=carte(nature, texte, self.secrets))      # la carte « Je réfléchis… » est modifiée au fil du flux

    async def _diagnostic(self, canal_id):
        place = None
        try:
            place = await self._carte_envoyer(canal_id, "Diagnostic en cours (quelques appels de test)…")
            nature = "reponse"
            try:
                rapport = await asyncio.wait_for(self.conversation.diagnostic(), 170)
            except Exception as e:
                rapport, nature = "Le diagnostic a échoué (%s)." % type(e).__name__, "probleme"
            self.journal("diagnostic demandé : " + rapport.replace("\n", " | ")[:400])
            await self._carte_editer(canal_id, place, self._preparer(rapport)[0], nature)
        except Exception as e:
            self.journal("diagnostic impossible (%s)" % type(e).__name__)

    async def _conversation(self, canal_id, nom, msg_id, auteur_id, texte):
        """Répond directement : « Je réfléchis… » aussitôt, remplacé par la réponse (modifié au fil du flux). En cas d'échec : Jarvis reprend la main comme avant."""
        conv = self.conversation
        place = None
        try:
            if not conv.est_local(texte):
                place = await self._carte_envoyer(canal_id, "Je réfléchis…")
                try:
                    await self.client.taper(canal_id, True)
                except Exception:
                    pass
            dernier = [0.0]

            async def flux(cumul):
                if place is not None and self.horloge() - dernier[0] >= 1.1 and cumul.strip():
                    dernier[0] = self.horloge()
                    await self._carte_editer(canal_id, place, self._preparer(cumul + " …")[0])

            async def lent():
                # 15 s sans un mot de réponse : on le dit sur Discord au lieu de rester silencieux
                await asyncio.sleep(getattr(conv, "delai_lent_s", 15))
                if place is not None and dernier[0] == 0.0:
                    await self._carte_editer(canal_id, place, "Je suis un peu lent, je regarde…", "attention")

            tache_lent = asyncio.ensure_future(lent())
            try:
                rep = await conv.repondre(texte, flux)
            finally:
                tache_lent.cancel()
            try:
                await self.client.taper(canal_id, False)
            except Exception:
                pass
            if not rep:
                if place is not None:
                    await self.client.supprimer(canal_id, place)
                await self._vers_jarvis(canal_id, nom, msg_id, auteur_id, texte)
                return
            morceaux = self._preparer(rep) or ["…"]
            t_envoi = self.horloge()
            if place is not None:
                await self._carte_editer(canal_id, place, morceaux[0])
            else:
                await self._carte_envoyer(canal_id, morceaux[0])
            for suite in morceaux[1:]:
                await self._carte_envoyer(canal_id, suite)
            envoi_ms = int((self.horloge() - t_envoi) * 1000)
            mes = getattr(conv, "mesures", None) or {}
            detail = ""
            if mes.get("mode") and conv.dernier_mode in ("chaud", "cli"):
                detail = " (%s%s : démarrage %s ms, première sortie %s ms, fin %s ms)" % (mes.get("mode"), "" if mes.get("chaud", True) else " à froid", mes.get("demarrage_ms"), mes.get("premiere_ms"), mes.get("fin_ms"))
            self.journal("conversation directe : %s en %d ms%s, envoi Discord %d ms" % (conv.dernier_mode, conv.dernier_ms, detail, envoi_ms))
        except Exception as e:
            self.journal("conversation directe impossible (%s) : message passé à Jarvis" % type(e).__name__)
            try:
                if place is not None:
                    await self.client.supprimer(canal_id, place)
            except Exception:
                pass
            await self._vers_jarvis(canal_id, nom, msg_id, auteur_id, texte)

    async def sur_reaction(self, user_id, canal_id, msg_id, emoji):
        if int(user_id) != self.user_id:
            return
        for cid, a in list(self.attentes.items()):
            if a["msg_id"] == msg_id:
                rep = "oui" if str(emoji) == EMOJI_OUI else "non" if str(emoji) == EMOJI_NON else None
                if rep:
                    self.echange.poster_entrant({"type": "reponse", "confirm_id": cid, "reponse": rep, "via": "reaction"})
                    self.attentes.pop(cid, None)
                return

    def _lever_stop(self):
        if self.stop_flag:
            try:
                self.stop_flag.parent.mkdir(parents=True, exist_ok=True)
                self.stop_flag.write_text("1", encoding="ascii")
            except OSError as e:
                self.journal("drapeau d'arrêt non écrit : %s" % type(e).__name__)

    # ---------- Jarvis -> Discord ----------
    async def _ecrire_poliment(self, canal_id, texte, nature="reponse"):
        try:
            await self.client.envoyer(int(canal_id), "", embed=carte(nature, texte, self.secrets))
        except Exception as e:
            self.journal("envoi impossible : %s" % type(e).__name__)

    def _fin_saisie(self, reply_to):
        s = self.saisies.pop(str(reply_to), None) if reply_to else None
        return s

    async def _arreter_saisie(self, reply_to):
        s = self._fin_saisie(reply_to)
        if s:
            try:
                await self.client.taper(s[0], False)
            except Exception:
                pass

    def _canal_id(self, nom):
        """Salon demandé ; s'il est introuvable, repli vers « jarvis » (noté une fois au journal)."""
        s = self.salons()
        if str(nom) in s:
            return s[str(nom)]
        if str(nom) not in self._repli_dit:
            self._repli_dit.add(str(nom))
            self.journal("salon « %s » introuvable : messages repliés vers « jarvis »" % nom)
        return s.get("jarvis")

    async def traiter_sortants(self):
        for chemin in self.echange.sortants():
            try:
                m = json.loads(chemin.read_text(encoding="utf-8-sig"))
            except (OSError, ValueError):
                self.journal("fichier sortant illisible, supprimé")
                m = None
            try:
                chemin.unlink()
            except OSError:
                pass
            if not isinstance(m, dict):
                continue
            try:
                await self._executer(m)
            except Exception as e:
                self.journal("erreur d'envoi (%s) : %s" % (m.get("type"), type(e).__name__))

    async def _executer(self, m):
        t = m.get("type")
        if t == "arret":
            self.arret = True
        elif t == "message":
            await self._envoyer_message(m)
        elif t == "confirmation":
            await self._envoyer_confirmation(m)
        elif t == "confirmation_fin":
            self.attentes.pop(str(m.get("confirm_id")), None)
        elif t == "vocal":
            await self._envoyer_vocal(m)
        else:
            self.journal("type sortant inconnu ignoré")

    def _preparer(self, texte):
        return decouper(neutraliser_mentions(masquer(texte, self.secrets)))

    async def _envoyer_message(self, m):
        canal_id = self._canal_id(m.get("canal"))
        await self._arreter_saisie(m.get("reply_to"))
        if not canal_id:
            self.journal("salon « %s » non renseigné dans config.json : message non envoyé" % m.get("canal"))
            return
        morceaux = self._preparer(m.get("texte", ""))
        mention = str(m.get("mention", "")).strip() == str(self.user_id)      # @Liam : SEULEMENT l'identifiant autorisé (jamais @everyone, @here ni un autre utilisateur)
        if mention and morceaux:
            morceaux[0] = "<@%d> %s" % (self.user_id, morceaux[0])
            await self.client.envoyer(canal_id, morceaux[0], mention=self.user_id)
            for morceau in morceaux[1:]:
                await self.client.envoyer(canal_id, morceau)
            return
        embed = preparer_embed(m.get("embed"), self.secrets)
        if not morceaux and embed:
            await self.client.envoyer(canal_id, "", embed=embed)
            return
        for i, morceau in enumerate(morceaux):
            if embed and i == len(morceaux) - 1:
                await self.client.envoyer(canal_id, morceau, embed=embed)      # l'embed accompagne le dernier morceau de texte
            else:
                await self.client.envoyer(canal_id, morceau)

    async def _envoyer_confirmation(self, m):
        canal_id = self._canal_id(m.get("canal"))
        await self._arreter_saisie(m.get("reply_to"))
        if not canal_id:
            self.journal("salon « %s » non renseigné : confirmation non envoyée (Jarvis annulera)" % m.get("canal"))
            return
        delai = int(m.get("delai") or 60)
        texte = "%s\n(%s ou %s, ou répondez « oui » / « non » — %d s)" % (m.get("texte", ""), EMOJI_OUI, EMOJI_NON, delai)
        morceaux = self._preparer(texte)
        msg_id = None
        for morceau in morceaux:
            msg_id = await self.client.envoyer(canal_id, morceau)
        self.attentes[str(m.get("confirm_id"))] = {"msg_id": msg_id, "canal": str(m.get("canal")), "canal_id": canal_id,
                                                  "expire": self.horloge() + delai + 10}
        for e in (EMOJI_OUI, EMOJI_NON):
            try:
                await self.client.reaction(canal_id, msg_id, e)
            except Exception as ex:
                self.journal("réaction impossible : %s" % type(ex).__name__)

    async def _envoyer_vocal(self, m):
        """Message vocal / fichier audio de Jarvis. DÉSACTIVÉ par défaut (config.json : discord_vocal = false)."""
        if not self.config.valeurs()["vocal"]:
            self.journal("envoi audio refusé : discord_vocal est désactivé")
            return
        canal_id = self._canal_id(m.get("canal") or "jarvis")
        chemin = Path(str(m.get("fichier", "")))
        ok = (canal_id and chemin.suffix.lower() in EXTENSIONS_AUDIO and chemin.is_file() and chemin.stat().st_size <= TAILLE_AUDIO_MAX
              and not re.search(r"(?i)(^|[\\/])\.env", str(chemin)))
        if not ok:
            self.journal("envoi audio refusé : fichier ou salon invalide")
            return
        await self.client.envoyer_fichier(canal_id, str(chemin))

    # ---------- entretien périodique ----------
    async def tick(self):
        now = self.horloge()
        for cid, a in list(self.attentes.items()):
            if now > a["expire"]:
                self.attentes.pop(cid, None)
        for mid, (canal_id, debut) in list(self.saisies.items()):
            if now - debut > SAISIE_MAX_S:
                self.saisies.pop(mid, None)
                try:
                    await self.client.taper(canal_id, False)
                except Exception:
                    pass
        if now - self._dernier_etat >= 15:
            self._dernier_etat = now
            try:
                self.echange.ecrire_etat({"pid": os.getpid(), "connecte": bool(self.connecte), "ts": time.time()})
            except OSError:
                pass


async def boucler(pont, parent_pid=0, quitter_flag=None, pause=0.3, max_tours=None):
    """Boucle du pont : s'arrête quand Jarvis (le parent) a disparu, quand memoire\\quitter.flag existe ou quand Jarvis envoie « arret »."""
    tours = 0
    while True:
        await pont.traiter_sortants()
        await pont.tick()
        if pont.arret:
            return "arret"
        if quitter_flag and Path(quitter_flag).exists():
            return "quitter"
        if not processus_vivant(parent_pid):
            return "parent"
        tours += 1
        if max_tours is not None and tours >= max_tours:
            return "tours"
        await asyncio.sleep(pause)
