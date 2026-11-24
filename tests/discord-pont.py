"""Test SILENCIEUX du pont Discord (pont-discord\\pont_logique.py) avec un FAUX client Discord : aucune connexion réseau, aucun jeton réel
(un faux jeton sert à vérifier qu'il ne sort jamais), dossiers temporaires. Sortie « OK ... » / « ECHEC ... » ; code 0 si tout est vert."""
import asyncio
import importlib.util
import io
import json
import os
import re
import sys
import tempfile
from pathlib import Path

ici = Path(__file__).resolve().parent
racine = ici.parent
spec = importlib.util.spec_from_file_location("pont_logique", racine / "pont-discord" / "pont_logique.py")
m = importlib.util.module_from_spec(spec)
sys.modules["pont_logique"] = m
spec.loader.exec_module(m)

try:
    sys.stdout.reconfigure(errors="replace")
except AttributeError:
    pass
echecs = 0
LIAM, INCONNU = 111111111111111111, 222222222222222222
SALONS = {"jarvis": 1001, "business": 1002, "systeme": 1003, "marche": 1004}
FAUX_JETON = "MTIzNDU2Nzg5MDEyMzQ1Njc4.GabcDE.abcdefghijklmnopqrstuvwxyz0123456789ABCD"


def verifier(cond, msg):
    global echecs
    if cond:
        print("  OK    " + msg)
    else:
        print("  ECHEC " + msg)
        echecs += 1


class FauxClient:
    def __init__(self):
        self.envoyes, self.reactions, self.saisies, self.fichiers = [], [], [], []
        self.embeds = []
        self.mentions = []
        self.n = 5000
        self.panne = False

    async def envoyer(self, canal_id, texte, embed=None, mention=None):
        if self.panne:
            raise RuntimeError("panne simulee " + FAUX_JETON)
        self.n += 1
        if embed is not None:
            self.embeds.append((canal_id, texte, embed))
        if mention is not None:
            self.mentions.append((canal_id, texte, mention))
        self.envoyes.append((canal_id, texte or (embed or {}).get("description", "")))      # une carte : on lit sa description
        return self.n

    async def reaction(self, canal_id, msg_id, emoji):
        self.reactions.append((canal_id, msg_id, emoji))

    async def taper(self, canal_id, actif):
        self.saisies.append((canal_id, actif))

    async def envoyer_fichier(self, canal_id, chemin):
        self.fichiers.append((canal_id, chemin))


class Banc:
    def __init__(self, vocal=False, salons=None):
        self.tmp = Path(tempfile.mkdtemp(prefix="jarvis-test-pont-"))
        self.config_path = self.tmp / "config.json"
        self.ecrire_config(salons if salons is not None else SALONS, vocal)
        self.client = FauxClient()
        self.logs = io.StringIO()
        self.flag = self.tmp / "STOP.flag"
        self.echange = m.Echange(self.tmp / "discord")
        self.pont = m.Pont(self.client, self.echange, m.ConfigJarvis(self.config_path), LIAM, secrets=[FAUX_JETON], stop_flag=self.flag,
                           journal_sortie=lambda l: self.logs.write(l + "\n"))

    def ecrire_config(self, salons, vocal=False):
        self.config_path.write_text(json.dumps({"discord_salons": {k: str(v) for k, v in salons.items()}, "discord_vocal": vocal}), encoding="utf-8")

    def entrants(self):
        return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(self.echange.entrant.glob("*.json"))]

    def vider_entrants(self):
        for p in self.echange.entrant.glob("*.json"):
            p.unlink()

    def sortie(self, **kw):
        self.echange.poster_sortant(kw)

    def run(self, coro):
        return asyncio.run(coro)


def msg(b, auteur=LIAM, canal=1001, mid=1, texte="ajoute acheter du pain à ma to-do", bot=False):
    return b.run(b.pont.sur_message(auteur, bot, canal, mid, texte))


print("1) Qui a le droit de parler")
b = Banc()
msg(b, auteur=INCONNU, mid=1, texte="supprime tout")
verifier(b.entrants() == [] and b.client.envoyes == [] and b.client.saisies == [], "un autre utilisateur : ignoré en silence (rien écrit, aucune réponse, pas de saisie)")
verifier("supprime tout" not in b.logs.getvalue() and b.logs.getvalue() == "", "un autre utilisateur : le contenu n'est ni journalisé ni affiché (journal vide)")
verifier(b.pont.ignores == 1, "…seul un compteur d'ignorés augmente")
msg(b, auteur=LIAM, bot=True, mid=2)
verifier(b.entrants() == [] and b.client.envoyes == [], "un bot (même avec l'identifiant de Liam) : ignoré")
msg(b, canal=9999, mid=3, texte="statut")
verifier(b.entrants() == [] and b.client.envoyes == [] and b.logs.getvalue() == "", "salon NON listé : ignoré en silence, aucune réponse, aucune trace")
msg(b, canal=1001, mid=4, texte="ajoute du pain à ma to-do")
e = b.entrants()
verifier(len(e) == 1 and e[0]["type"] == "message" and e[0]["canal"] == "jarvis" and e[0]["auteur"] == str(LIAM) and e[0]["texte"].startswith("ajoute du pain"), "Liam dans un salon listé : message transmis à Jarvis (salon = « jarvis »)")
verifier(b.client.saisies == [(1001, True)], "« en train d'écrire » démarre pendant que Jarvis réfléchit")
b.vider_entrants()
msg(b, canal=1001, mid=4, texte="ajoute du pain à ma to-do")
verifier(b.entrants() == [], "un message rejoué par Discord (même identifiant) n'est traité qu'une fois")
msg(b, canal=1002, mid=5, texte="liste mes tâches"); e = b.entrants()
verifier(len(e) == 1 and e[0]["canal"] == "business", "salon « business » reconnu par son identifiant")
b.vider_entrants()
msg(b, mid=6, texte="x" * 1001)
verifier(b.entrants() == [] and "trop long" in b.client.envoyes[-1][1], "message trop long : refusé poliment, rien transmis")
msg(b, mid=7, texte="   ")
verifier(b.entrants() == [], "message vide : rien")
b.ecrire_config({"jarvis": 0, "business": "", "systeme": "", "marche": ""})
b2 = Banc(salons={})
msg(b2, canal=1001, mid=1, texte="statut")
verifier(b2.entrants() == [] and b2.client.envoyes == [], "salons vides par défaut : le pont n'écoute nulle part")
b.ecrire_config({"jarvis": 1001}); os.utime(b.config_path, ns=(1000000000, 1000000000)); msg(b, mid=20, texte="statut")
verifier(len(b.entrants()) == 1, "config.json relu quand il change (salon renseigné après coup)")

print("2) Messages de Jarvis vers Discord")
b = Banc()
msg(b, mid=1, texte="statut"); b.vider_entrants()
b.sortie(type="message", canal="systeme", texte="Alerte, monsieur.", reply_to="1")
b.run(b.pont.traiter_sortants())
verifier(b.client.envoyes == [(1003, "Alerte, monsieur.")], "message envoyé dans le salon demandé (alertes = 1003)")
verifier(b.client.saisies[-1] == (1001, False), "« en train d'écrire » s'arrête quand la réponse part")
verifier(list(b.echange.sortant.glob("*.json")) == [], "fichier sortant supprimé après envoi")
b.client.envoyes.clear()
b.sortie(type="message", canal="jarvis", texte="Bonjour @everyone et <@123> et @here")
b.run(b.pont.traiter_sortants())
t = b.client.envoyes[0][1]
verifier("@everyone" not in t and "@here" not in t and "<@123>" not in t, "mentions neutralisées (@everyone, @here, <@id>)")
b.client.envoyes.clear()
b.sortie(type="message", canal="jarvis", texte="le jeton est " + FAUX_JETON + " voilà")
b.run(b.pont.traiter_sortants())
verifier(FAUX_JETON not in b.client.envoyes[0][1] and "[SECRET]" in b.client.envoyes[0][1], "un jeton qui se glisserait dans une réponse est masqué avant l'envoi")
b.client.envoyes.clear()
b.sortie(type="message", canal="jarvis", texte=("ligne\n" * 600))
b.run(b.pont.traiter_sortants())
verifier(len(b.client.envoyes) >= 2 and all(len(x[1]) <= 2000 for x in b.client.envoyes), "réponse longue : coupée en messages de moins de 2000 caractères")
b.client.envoyes.clear()
b.sortie(type="message", canal="marche", texte="x"); b.ecrire_config({"jarvis": 1001}); os.utime(b.config_path, ns=(5000000000, 5000000000))
b.run(b.pont.traiter_sortants())
verifier(b.client.envoyes == [(1001, "x")] and "marche" in b.logs.getvalue(), "salon introuvable : le message est replié vers « jarvis », noté au journal")
b.sortie(type="message", canal="marche", texte="y"); b.run(b.pont.traiter_sortants())
verifier(b.logs.getvalue().count("introuvable") == 1, "…noté une seule fois")
b.ecrire_config({}); os.utime(b.config_path, ns=(9000000000, 9000000000)); b.client.envoyes.clear()
b.sortie(type="message", canal="marche", texte="z"); b.run(b.pont.traiter_sortants())
verifier(b.client.envoyes == [], "ni « marche » ni « jarvis » : rien n'est envoyé")
(b.echange.sortant / "0-casse.json").write_text("{pas du json", encoding="utf-8")
b.run(b.pont.traiter_sortants())
verifier(list(b.echange.sortant.glob("*.json")) == [], "fichier sortant illisible : supprimé sans planter")
b.ecrire_config({"jarvis": 1001}); os.utime(b.config_path, ns=(40000000000, 40000000000))
b.client.panne = True
b.sortie(type="message", canal="jarvis", texte="x")
b.run(b.pont.traiter_sortants())
verifier(FAUX_JETON not in b.logs.getvalue() and "RuntimeError" in b.logs.getvalue(), "panne d'envoi : le journal donne le type d'erreur, jamais le jeton")

print("3) Confirmations (réaction ✅/❌ ou oui/non)")
b = Banc()
msg(b, mid=1, texte="mets le PC en veille"); b.vider_entrants()
b.sortie(type="confirmation", confirm_id="c1", canal="jarvis", texte="Mettre le PC en veille, monsieur ?", delai=60, reply_to="1")
b.run(b.pont.traiter_sortants())
verifier(len(b.client.envoyes) == 1 and "veille" in b.client.envoyes[0][1] and "60 s" in b.client.envoyes[0][1], "question posée dans le salon, avec le délai")
verifier([r[2] for r in b.client.reactions] == ["✅", "❌"], "le bot ajoute ✅ et ❌ sous la question")
mid_q = b.client.reactions[0][1]
b.run(b.pont.sur_reaction(INCONNU, 1001, mid_q, "✅"))
verifier(b.entrants() == [], "✅ d'un autre utilisateur : ignoré")
b.run(b.pont.sur_reaction(LIAM, 1001, 424242, "✅"))
verifier(b.entrants() == [], "✅ sur un autre message : ignoré")
b.run(b.pont.sur_reaction(LIAM, 1001, mid_q, "\U0001F44D"))
verifier(b.entrants() == [], "un autre emoji n'est pas une réponse")
b.run(b.pont.sur_reaction(LIAM, 1001, mid_q, "✅"))
e = b.entrants()
verifier(len(e) == 1 and e[0] == {"type": "reponse", "confirm_id": "c1", "reponse": "oui", "via": "reaction"}, "✅ de Liam : réponse « oui »")
b.vider_entrants()
b.run(b.pont.sur_reaction(LIAM, 1001, mid_q, "❌"))
verifier(b.entrants() == [], "la confirmation n'est consommée qu'une fois")
for texte, attendu in (("oui", "oui"), ("OK", "oui"), ("Vas-y !", "oui"), ("non", "non"), ("Annule", "non")):
    b = Banc(); b.sortie(type="confirmation", confirm_id="c2", canal="jarvis", texte="Q ?", delai=60); b.run(b.pont.traiter_sortants())
    msg(b, mid=9, texte=texte); e = b.entrants()
    verifier(len(e) == 1 and e[0]["type"] == "reponse" and e[0]["reponse"] == attendu, "réponse écrite « %s » -> %s" % (texte, attendu))
b = Banc(); b.sortie(type="confirmation", confirm_id="c3", canal="jarvis", texte="Q ?", delai=60); b.run(b.pont.traiter_sortants())
msg(b, mid=9, texte="peut-être bien"); e = b.entrants()
verifier(len(e) == 1 and e[0]["type"] == "message", "phrase ambiguë : jamais un « oui » (transmise comme un nouvel ordre)")
msg(b, canal=1002, mid=10, texte="oui"); e = b.entrants()
verifier(len(e) == 2 and e[1]["type"] == "message" and e[1]["canal"] == "business", "« oui » dans un AUTRE salon : ne répond pas à la question")
bo = Banc()
for i in range(60):
    bo.echange.poster_entrant({"n": i})
verifier([x["n"] for x in bo.entrants()] == list(range(60)), "60 messages écrits d'affilée (horloge Windows ~15 ms) : lus dans l'ordre d'arrivée")
b.sortie(type="confirmation_fin", confirm_id="c3", issue="delai"); b.run(b.pont.traiter_sortants())
b.vider_entrants(); msg(b, mid=11, texte="oui"); e = b.entrants()
verifier(len(e) == 1 and e[0]["type"] == "message", "après le délai (confirmation_fin) : un « oui » tardif n'est plus une confirmation")
b = Banc(); b.sortie(type="confirmation", confirm_id="c4", canal="jarvis", texte="Q ?", delai=1); b.run(b.pont.traiter_sortants())
b.pont.horloge = lambda: 10 ** 9; b.run(b.pont.tick())
verifier(b.pont.attentes == {}, "confirmation périmée côté pont : oubliée (le délai est géré par Jarvis)")

print("4) Arrêt d'urgence")
b = Banc()
msg(b, mid=1, texte="Jarvis stop")
e = b.entrants()
verifier(b.flag.exists() and len(e) == 1 and e[0]["type"] == "stop", "« Jarvis stop » : drapeau STOP posé tout de suite + Jarvis prévenu")
verifier("urgence" in b.client.envoyes[-1][1].lower(), "accusé de réception de l'arrêt d'urgence")
b = Banc(); b.sortie(type="confirmation", confirm_id="c5", canal="jarvis", texte="Q ?", delai=60); b.run(b.pont.traiter_sortants())
msg(b, mid=2, texte="stop")
verifier(b.flag.exists() and b.entrants()[0]["type"] == "stop", "« stop » pendant une confirmation : l'arrêt passe avant tout")
b = Banc(); msg(b, auteur=INCONNU, mid=3, texte="stop")
verifier(not b.flag.exists(), "« stop » d'un autre utilisateur : aucun effet")

print("5) Jeton jamais affiché")
b = Banc()
b.pont.journal("erreur avec " + FAUX_JETON + " dedans")
b.pont.journal("Bot " + "Z" * 40)
l = b.logs.getvalue()
verifier(FAUX_JETON not in l and "[SECRET]" in l and "Z" * 40 not in l, "journal du pont : le jeton et les « Bot xxx » sont masqués")
verifier(FAUX_JETON not in m.masquer("x " + FAUX_JETON + " y") and m.masquer("rien à cacher") == "rien à cacher", "masquer() : jeton retiré, texte normal intact")
src = "\n".join(p.read_text(encoding="utf-8") for p in (racine / "pont-discord").glob("*.py"))
verifier(not m.MOTIF_JETON.search(src) and FAUX_JETON not in src, "aucun jeton dans le code du pont")
jeton_reel = os.environ.get("DISCORD_BOT_TOKEN", "")
verifier(not jeton_reel or len(jeton_reel) < 8 or jeton_reel not in src, "le vrai jeton (s'il existe dans l'environnement) n'est pas dans le code du pont")

print("6) Messages vocaux : prévus, désactivés par défaut")
b = Banc(vocal=False)
audio = b.tmp / "voix.mp3"; audio.write_bytes(b"ID3" + b"\x00" * 100)
b.sortie(type="vocal", canal="jarvis", fichier=str(audio)); b.run(b.pont.traiter_sortants())
verifier(b.client.fichiers == [] and "discord_vocal" in b.logs.getvalue(), "discord_vocal = false : aucun fichier audio n'est envoyé")
b = Banc(vocal=True)
audio = b.tmp / "voix.mp3"; audio.write_bytes(b"ID3" + b"\x00" * 100)
b.sortie(type="vocal", canal="jarvis", fichier=str(audio)); b.run(b.pont.traiter_sortants())
verifier(b.client.fichiers == [(1001, str(audio))], "discord_vocal = true : le fichier audio part dans le salon")
secret = b.tmp / ".env"; secret.write_text("X=1", encoding="utf-8")
txt = b.tmp / "note.txt"; txt.write_text("x", encoding="utf-8")
b.client.fichiers.clear()
b.sortie(type="vocal", canal="jarvis", fichier=str(secret)); b.sortie(type="vocal", canal="jarvis", fichier=str(txt)); b.sortie(type="vocal", canal="jarvis", fichier=str(b.tmp / "absent.mp3"))
b.run(b.pont.traiter_sortants())
verifier(b.client.fichiers == [], "même activé : .env, fichier non audio ou absent -> refusés")

print("7) Arrêt avec Jarvis")
b = Banc()
verifier(m.processus_vivant(os.getpid()) and m.processus_vivant(0), "processus_vivant : le processus courant vit ; pas de parent = rien à surveiller")
verifier(not m.processus_vivant(4000001), "processus_vivant : un processus qui n'existe pas est mort")
r = b.run(m.boucler(b.pont, parent_pid=4000001, pause=0.01, max_tours=50))
verifier(r == "parent", "le pont s'arrête de lui-même quand Jarvis (son parent) a disparu")
q = b.tmp / "quitter.flag"; q.write_text("1")
r = b.run(m.boucler(b.pont, parent_pid=os.getpid(), quitter_flag=q, pause=0.01, max_tours=50))
verifier(r == "quitter", "le pont s'arrête avec memoire\\quitter.flag (arreter.ps1)")
q.unlink(); b.sortie(type="arret")
r = b.run(m.boucler(b.pont, parent_pid=os.getpid(), quitter_flag=q, pause=0.01, max_tours=50))
verifier(r == "arret", "le pont s'arrête quand Jarvis le demande (« Jarvis stop », fin de Jarvis)")
b = Banc()
r = b.run(m.boucler(b.pont, parent_pid=os.getpid(), pause=0.01, max_tours=3))
et = json.loads((b.echange.dossier / "etat.json").read_text(encoding="utf-8"))
verifier(r == "tours" and et["pid"] == os.getpid() and et["connecte"] is False, "état écrit pour Jarvis (pid, connecté ou non)")

print("7 bis) Salons associés automatiquement par mot-clé")
verifier([m.normaliser_nom(x) for x in ("\U0001F916｜Jarvis", "⚙️-Système-Logs", "\U0001F4C8・Marché", "\U0001F4BC BUSINESS", "\U0001D409\U0001D400\U0001D411\U0001D415\U0001D408\U0001D412")]
         == ["jarvis", "systemelogs", "marche", "business", "jarvis"], "noms nettoyés : emojis, majuscules, accents, tirets, séparateurs, lettres fantaisie")
NOMS = [(11, "général"), (12, "\U0001F916｜Jarvis"), (13, "⚙️-Système"), (14, "\U0001F4C8-marché-cours"), (15, "\U0001F4BC・business"), (16, "règles")]
verifier(m.associer_salons(NOMS) == {"jarvis": 12, "systeme": 13, "marche": 14, "business": 15}, "les quatre salons sont reconnus malgré les emojis et les accents")
verifier(m.associer_salons([(1, "jarvis-vieux"), (2, "jarvis")])["jarvis"] == 2, "nom exact préféré")
CIBLES = [(21, "🤖-jarvis"), (22, "🛠️-système"), (23, "💼-business"), (24, "💸-paiements"), (25, "🗓️-résumé-du-jour"), (26, "🚆-annonces-train"), (27, "🚨-important"), (28, "📓-journal"), (29, "📦-lots"), (30, "💬-réponses"), (31, "📞-appels-du-jour")]
verifier(m.associer_salons(CIBLES) == {"jarvis": 21, "systeme": 22, "business": 23, "important": 27, "journal": 28}, "noms cibles avec emojis : jarvis, système, business, important, journal reconnus ; lots / réponses / appels-du-jour ne volent aucun mot-clé")
bi = Banc(salons={}); bi.pont.maj_serveurs([{"id": 900, "salons": CIBLES}]); verifier(set(m.NOMS_SORTIE) == {"important", "journal"} and "important" not in m.NOMS_SALONS and bi.pont._nom_salon(27) is None and bi.pont._nom_salon(21) == "jarvis" and bi.pont.salons()["important"] == 27, "important et journal : trouvés pour écrire, jamais écoutés (aucun ordre), facultatifs")
b = Banc(salons={})
b.pont.maj_serveurs([{"id": 900, "salons": NOMS}])
cache = json.loads((b.tmp / "discord-salons.json").read_text(encoding="utf-8"))
verifier(cache["salons"] == {"jarvis": "12", "systeme": "13", "marche": "14", "business": "15"} and cache["manquants"] == [] and cache["serveur"] == "900", "cache memoire\\discord-salons.json écrit (identifiants de salons seulement)")
verifier(FAUX_JETON not in json.dumps(cache), "aucun secret dans le cache")
msg(b, canal=12, mid=1, texte="statut"); msg(b, canal=11, mid=2, texte="statut"); msg(b, auteur=INCONNU, canal=13, mid=3, texte="statut")
e = b.entrants()
verifier(len(e) == 1 and e[0]["canal"] == "jarvis", "sans aucun identifiant dans config.json : Liam est entendu dans « jarvis », pas ailleurs, et un autre utilisateur jamais")
b.vider_entrants(); b.sortie(type="message", canal="systeme", texte="alerte"); b.run(b.pont.traiter_sortants())
verifier(b.client.envoyes[-1][0] == 13, "une alerte part dans le salon « système »")
renomme = [(i, "cours" if i == 14 else n) for i, n in NOMS]
b.pont.maj_serveurs([{"id": 900, "salons": renomme}])
cache = json.loads((b.tmp / "discord-salons.json").read_text(encoding="utf-8"))
verifier(cache["manquants"] == ["marche"] and "marche" not in cache["salons"], "salon renommé : cache refait, « marche » devient introuvable")
msg(b, canal=14, mid=4, texte="cours")
verifier(b.entrants() == [], "l'ancien salon n'est plus écouté")
b.client.envoyes.clear(); b.sortie(type="message", canal="marche", texte="cours"); b.run(b.pont.traiter_sortants())
verifier(b.client.envoyes == [(12, "cours")], "…et ses messages sont repliés vers « jarvis »")
b.pont.maj_serveurs([{"id": 900, "salons": renomme + [(20, "marché")]}])
verifier(json.loads((b.tmp / "discord-salons.json").read_text(encoding="utf-8"))["salons"]["marche"] == "20", "salon ajouté : repris automatiquement")
b.pont.maj_serveurs([{"id": 900, "salons": [x for x in NOMS if x[0] != 13]}])
verifier("systeme" in json.loads((b.tmp / "discord-salons.json").read_text(encoding="utf-8"))["manquants"], "salon supprimé : devient introuvable")
b.ecrire_config({"jarvis": 777}); os.utime(b.config_path, ns=(30000000000, 30000000000))
verifier(b.pont.salons()["jarvis"] == 777, "identifiant forcé à la main : prioritaire sur l'association")
b = Banc(salons={})
A = {"id": 500, "salons": [(51, "général"), (52, "jarvis")]}
B = {"id": 400, "salons": NOMS}
b.pont.maj_serveurs([A, B])
c2 = json.loads((b.tmp / "discord-salons.json").read_text(encoding="utf-8"))
verifier(c2["serveur"] == "400" and "52" not in c2["salons"].values() and "2 serveurs" in b.logs.getvalue(), "deux serveurs où se trouve Liam : un seul retenu (le plus complet), l'autre ignoré")
msg(b, canal=52, mid=9, texte="statut")
verifier(b.entrants() == [], "…les salons de l'autre serveur sont ignorés")


async def est_membre(g):
    return g["id"] in (500, 400)


cands = asyncio.run(m.serveurs_de_liam([A, B, {"id": 300, "salons": NOMS}], est_membre))
verifier([c["id"] for c in cands] == [500, 400], "un serveur où ne se trouve pas DISCORD_USER_ID n'est jamais pris en compte")
b.pont.maj_serveurs([])
verifier(b.pont.salons() == {} and json.loads((b.tmp / "discord-salons.json").read_text(encoding="utf-8"))["manquants"] == list(m.NOMS_SALONS), "aucun serveur : tous les salons introuvables, rien n'est écouté")

print("7 ter) Noms réalistes : emojis à sélecteur de variation, accents composés / décomposés, caractères invisibles")
import unicodedata
REELS = ["\U0001F6E0️-système", "\U0001F4C8-marché", "\U0001F4BC-business", "\U0001F916-jarvis"]
verifier([m.normaliser_nom(x) for x in REELS] == ["systeme", "marche", "business", "jarvis"], "« 🛠️-système », « 📈-marché », « 💼-business », « 🤖-jarvis » -> systeme, marche, business, jarvis")
for forme in ("NFC", "NFD", "NFKC", "NFKD"):
    verifier([m.normaliser_nom(unicodedata.normalize(forme, x)) for x in REELS] == ["systeme", "marche", "business", "jarvis"], "accents %s : mêmes mots-clés" % forme)
INVISIBLES = ["syst​ème", "sys­tème", "‍marché‌", "bus⁠iness", "﻿business", "ｓｙｓｔèｍｅ", "SYSTÈME", "système", "marché"]
verifier([m.normaliser_nom(x) for x in INVISIBLES] == ["systeme", "systeme", "marche", "business", "business", "systeme", "systeme", "systeme", "marche"], "espace de largeur nulle, trait d'union conditionnel, ZWJ, BOM, pleine chasse, majuscules : reconnus")
for forme in ("NFC", "NFD"):
    noms = [(1, unicodedata.normalize(forme, "\U0001F916-jarvis")), (2, unicodedata.normalize(forme, "\U0001F6E0️-système")), (3, unicodedata.normalize(forme, "\U0001F4C8-marché")), (4, unicodedata.normalize(forme, "\U0001F4BC-business")), (5, "général")]
    verifier(m.associer_salons(noms) == {"jarvis": 1, "systeme": 2, "marche": 3, "business": 4}, "les quatre salons réalistes sont associés (%s)" % forme)
b = Banc(salons={})
infos = [{"nom": "\U0001F916-jarvis", "voir": True, "ecrire": True, "historique": True}, {"nom": "\U0001F6E0️-système", "voir": True, "ecrire": False, "historique": True},
         {"nom": "général", "voir": True, "ecrire": True, "historique": True}]
b.pont.maj_serveurs([{"id": 7, "salons": [(1, infos[0]["nom"]), (2, infos[1]["nom"]), (3, infos[2]["nom"])], "infos": infos}])
dg = json.loads((b.tmp / "discord-diagnostic.json").read_text(encoding="utf-8"))
verifier([x["cle"] for x in dg["salons"]] == ["jarvis", "systeme", None], "diagnostic : chaque salon visible avec son mot-clé reconnu")
verifier(any("syst" in p and "Envoyer des messages" in p for p in dg["problemes"]), "diagnostic : « système » visible mais sans permission d'écrire -> signalé")
verifier(any("marche" in p and "Voir le salon" in p for p in dg["problemes"]) and any("business" in p and "Voir le salon" in p for p in dg["problemes"]), "diagnostic : salon absent de la liste visible -> cause probable = permission « Voir le salon »")
txt = json.dumps(dg) + b.logs.getvalue()
verifier(FAUX_JETON not in txt and "'id'" not in json.dumps(dg) and '"id"' not in json.dumps(dg), "le diagnostic ne contient ni identifiant ni secret")

print("7 quater) Embeds : sûrs et bornés")
b = Banc()
gros = {"titre": "T" * 400, "description": "d" * 5000 + " @everyone " + FAUX_JETON, "couleur": 99999999, "pied": "Source X \u00b7 " + FAUX_JETON,
        "champs": [{"nom": "N%d" % i, "valeur": "v" * 2000, "inline": True} for i in range(40)] + [{"nom": "", "valeur": "vide"}]}
b.sortie(type="message", canal="jarvis", texte="", embed=gros); b.run(b.pont.traiter_sortants())
em = b.client.embeds[0][2] if b.client.embeds else {}
verifier(len(b.client.embeds) == 1 and b.client.embeds[0][0] == 1001 and b.client.embeds[0][1] == "", "un message sans texte avec un embed : envoyé tel quel dans le bon salon")
verifier(len(em["titre"]) <= 256 and len(em["description"]) <= 2000 and len(em["champs"]) <= 25 and all(len(c["valeur"]) <= 1024 for c in em["champs"]) and len(em["titre"]) + len(em["description"]) + len(em["pied"]) + sum(len(c["nom"]) + len(c["valeur"]) for c in em["champs"]) <= 6000, "titre, description, champs : limites de Discord respectées (dont 6000 caractères au total)")
verifier(em["couleur"] <= 0xFFFFFF and "@everyone" not in em["description"] and FAUX_JETON not in json.dumps(em), "couleur bornée, mentions cassées, jeton masqué dans l'embed")
b.client.embeds.clear(); b.sortie(type="message", canal="jarvis", texte="Voici", embed={"titre": "Statut", "champs": [{"nom": "a", "valeur": "b"}]}); b.run(b.pont.traiter_sortants())
verifier(b.client.embeds and b.client.embeds[0][1] == "Voici", "texte + embed : l'embed accompagne le texte")
b.client.embeds.clear(); b.sortie(type="message", canal="jarvis", texte="Seul", embed={"titre": "", "description": "", "champs": []}); b.run(b.pont.traiter_sortants())
verifier(not b.client.embeds and b.client.envoyes[-1][1] == "Seul", "embed vide : ignoré, le texte part seul")

print("7 quinquies) Test d'alerte : une seule mention, celle de Liam")
b = Banc()
b.sortie(type="message", canal="systeme", texte="\u26a0\ufe0f Test d'alerte, monsieur.", mention=str(LIAM)); b.run(b.pont.traiter_sortants())
verifier(b.client.mentions == [(1003, "<@%d> \u26a0\ufe0f Test d'alerte, monsieur." % LIAM, LIAM)] and len(b.client.envoyes) == 1, "un seul message dans « système », qui mentionne @Liam (identifiant autorisé)")
b = Banc()
b.sortie(type="message", canal="systeme", texte="x @everyone", mention=str(INCONNU)); b.run(b.pont.traiter_sortants())
verifier(b.client.mentions == [] and "<@" not in b.client.envoyes[0][1] and "@everyone" not in b.client.envoyes[0][1], "la mention d'un autre identifiant est refusée ; @everyone reste neutralisé")
b = Banc()
b.sortie(type="message", canal="systeme", texte="sans mention"); b.run(b.pont.traiter_sortants())
verifier(b.client.mentions == [], "sans champ « mention » : aucune mention")

print("8) pont.py sans identifiants ni réseau")
import subprocess
env = {k: v for k, v in os.environ.items() if k not in ("DISCORD_BOT_TOKEN", "DISCORD_USER_ID")}
env["PYTHONIOENCODING"] = "utf-8"
p = subprocess.run([sys.executable, "-I", str(racine / "pont-discord" / "pont.py"), "--echange", str(b.tmp / "x")], env=env, capture_output=True, text=True, timeout=60)
verifier(p.returncode == 2 and "manquants" in p.stderr, "sans jeton ni identifiant : sort proprement (code 2, pas de plantage, pas de réseau)")
env["DISCORD_BOT_TOKEN"] = FAUX_JETON; env["DISCORD_USER_ID"] = str(LIAM)
p = subprocess.run([sys.executable, "-I", str(racine / "pont-discord" / "pont.py"), "--echange", str(b.tmp / "x"), "--parent", "4000001"], env=env, capture_output=True, text=True, timeout=60)
verifier(p.returncode in (2, 3, 0) and FAUX_JETON not in p.stdout + p.stderr, "avec un faux jeton : jamais écrit dans la sortie (code %d)" % p.returncode)

import shutil
for d in Path(tempfile.gettempdir()).glob("jarvis-test-pont-*"):
    shutil.rmtree(d, ignore_errors=True)
print()
if echecs:
    print("ÉCHEC : %d vérification(s) en échec." % echecs)
    sys.exit(1)
print("TOUT EST VERT.")
