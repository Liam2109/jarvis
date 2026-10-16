"""Test SILENCIEUX de la conversation directe du pont (pont-discord\\conversation.py) : aucun réseau réel (faux serveur SSE sur 127.0.0.1, faux transports),
aucune clé réelle, dossiers temporaires. Sortie « OK ... » / « ECHEC ... » ; code 0 si tout est vert."""
import asyncio
import json
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ici = Path(__file__).resolve().parent
racine = ici.parent
sys.path.insert(0, str(racine / "pont-discord"))
import conversation as cv  # noqa: E402
import pont_logique as pl  # noqa: E402

try:
    sys.stdout.reconfigure(errors="replace")
except AttributeError:
    pass
echecs = 0
LIAM = 111111111111111111
FAUSSE_CLE = "sk-ant-FAUSSE-cle-de-test-0123456789abcdef"


def verifier(cond, msg):
    global echecs
    print(("  OK    " if cond else "  ECHEC ") + msg)
    if not cond:
        echecs += 1


tmp = Path(tempfile.mkdtemp(prefix="jarvis-test-conv-"))
(tmp / "memoire" / "discord").mkdir(parents=True)
QUOTA = tmp / "memoire" / "discord-claude.json"
CFG = {"discord_claude_max_par_jour": 50, "valeurs_suivies": [{"nom": "Thales"}]}
midi = datetime(2026, 10, 16, 14, 5)

print("1) Règles locales et décision (aucun réseau)")
verifier(cv.reponse_locale("Quelle heure est-il ?", midi) == "Il est 14 h 05, monsieur.", "heure : réponse instantanée")
verifier("vendredi 16 octobre 2026" in cv.reponse_locale("Quel jour sommes-nous ?", midi), "date : réponse instantanée")
verifier(cv.reponse_locale("Bonsoir Jarvis", midi).startswith("Bonsoir"), "salutation du soir")
verifier(cv.reponse_locale("merci", midi) == "Je vous en prie, monsieur.", "remerciement")
verifier(cv.reponse_locale("Pourquoi le ciel est-il bleu ?", midi) is None, "une vraie question n'est pas une règle locale")
for q in ("Pourquoi le ciel est-il bleu ?", "Quelle est la différence entre un SSD et un disque dur ?", "Donne-moi une idée de nom pour une boutique", "Explique-moi la TVA"):
    verifier(cv.est_conversation(q, ["Thales"]), "conversation directe : " + q)
for q in ("ouvre chrome", "ajoute à ma to-do : lait", "mets le volume à 30", "Dois-je acheter des actions Thales ?", "Quel est le cours de Thales ?",
          "où en est Thales ?", "montre-moi les stats du SaaS", "retiens que j'aime le café", "quel est mon mot de passe ?", "supprime le fichier test.txt", "Que fait Jarvis ?"):
    verifier(not cv.est_conversation(q, ["Thales"]), "reste à Jarvis (commande, marché, mémoire ou sujet réservé) : " + q)
verifier(not cv.est_conversation("lis https://exemple.fr/page ?", []) and not cv.est_conversation("c:\\users\\liam ?", []), "adresse ou chemin : reste à Jarvis")

print("2) Flux de l'API (analyse SSE)")
sse = ['event: message_start', 'data: {"type":"message_start"}', 'data: {"type":"content_block_delta","delta":{"type":"text_delta","text":"Le ciel "}}',
       'data: {"type":"content_block_delta","delta":{"type":"text_delta","text":"est bleu."}}', 'data: [DONE]']
verifier("".join(cv.lire_flux_sse(sse)) == "Le ciel est bleu.", "fragments de texte assemblés, autres évènements ignorés")
try:
    list(cv.lire_flux_sse(['data: {"type":"error","error":{"type":"overloaded_error"}}']))
    verifier(False, "évènement d'erreur levé")
except RuntimeError as e:
    verifier("overloaded_error" in str(e) and FAUSSE_CLE not in str(e), "évènement d'erreur levé, sans secret")

print("3) Conversation : voies, repli, mémoire, plafond")
appels = {"api": 0, "cli": 0}


async def api_ok(texte, systeme, sur_texte, cfg):
    appels["api"] += 1
    assert "monsieur" in systeme and "conseil" in systeme and "2 à 3 phrases" in systeme
    if sur_texte:
        await sur_texte("Parce que ")
        await sur_texte("Parce que la lumière se diffuse.")
    return "Parce que la lumière se diffuse."


async def cli_ok(texte, systeme, cfg):
    appels["cli"] += 1
    return "Réponse du repli."


async def api_ko(texte, systeme, sur_texte, cfg):
    appels["api"] += 1
    raise RuntimeError("HTTP 500 " + FAUSSE_CLE)

journal = []
c = cv.Conversation(tmp, lambda: CFG, env={"ANTHROPIC_API_KEY": FAUSSE_CLE}, journal=journal.append, transport_api=api_ok, transport_cli=cli_ok, horloge=lambda: midi)
morceaux = []


async def sur(cumul):
    morceaux.append(cumul)

r = asyncio.run(c.repondre("Pourquoi le ciel est-il bleu ?", sur))
verifier(r == "Parce que la lumière se diffuse." and c.dernier_mode == "api" and appels == {"api": 1, "cli": 0} and len(morceaux) == 2, "avec une clé : API en flux (claude -p non lancé), texte cumulé transmis")
r = asyncio.run(c.repondre("Quelle heure est-il ?", sur))
verifier(r.startswith("Il est 14 h") and c.dernier_mode == "local" and appels["api"] == 1, "heure : règle locale, aucun appel (ni API ni claude -p)")
verifier(len(cv.MemoireConversation(tmp / "memoire" / "discord" / "conversation.json").echanges) == 1, "mémoire écrite sur disque (une seule conversation Claude)")
c2 = cv.Conversation(tmp, lambda: CFG, env={}, journal=journal.append, transport_api=api_ok, transport_cli=cli_ok, horloge=lambda: midi)
r = asyncio.run(c2.repondre("Comment fonctionne un SSD ?"))
verifier(r == "Réponse du repli." and c2.dernier_mode == "cli" and appels["api"] == 1, "sans clé : repli automatique sur claude -p allégé")
c3 = cv.Conversation(tmp, lambda: CFG, env={"ANTHROPIC_API_KEY": FAUSSE_CLE}, journal=journal.append, transport_api=api_ko, transport_cli=cli_ok, horloge=lambda: midi)
r = asyncio.run(c3.repondre("Pourquoi la mer est-elle salée ?"))
verifier(r == "Réponse du repli." and c3.dernier_mode == "cli" and all(FAUSSE_CLE not in j for j in journal), "API en panne : repli sur claude -p, la clé n'est pas journalisée")
for i in range(12):
    c3.memoire.ajouter("q%d" % i, "r%d" % i)
verifier(len(c3.memoire.echanges) == 10 and len(c3.memoire.messages("x")) == 21, "mémoire : les 10 derniers échanges seulement")
QUOTA.unlink(missing_ok=True)
q = cv.Quota(QUOTA, 3)
verifier([q.utiliser() for _ in range(4)] == [True, True, True, False], "plafond quotidien partagé avec Jarvis (discord-claude.json)")
c4 = cv.Conversation(tmp, lambda: {"discord_claude_max_par_jour": 3}, env={}, transport_api=api_ok, transport_cli=cli_ok, horloge=lambda: midi)
verifier(asyncio.run(c4.repondre("Une autre question ?")) is None, "plafond atteint : None (Jarvis prend la main et l'explique)")
verifier(not cv.Conversation(tmp, lambda: {"discord_conversation": False}, env={}).prend("Pourquoi le ciel est-il bleu ?"), "discord_conversation = false : désactivée")
verifier(cv.Conversation(tmp, lambda: CFG, env={"ANTHROPIC_API_KEY": "sk-ant-xxx"}).cle_api() == "", "clé d'exemple (xxx) du .env.example : ignorée")

print("4) Vrai code réseau contre un faux serveur SSE local (127.0.0.1)")
try:
    from aiohttp import web
except ImportError:
    web = None
if web is None:
    print("  (aiohttp absent : partie sautée)")
else:
    vus = {}

    async def faux_messages(req):
        vus["cle"] = req.headers.get("x-api-key")
        vus["corps"] = await req.json()
        rep = web.StreamResponse(headers={"content-type": "text/event-stream"})
        await rep.prepare(req)
        for t in ("Bonjour ", "monsieur, ", "tout va bien."):
            await rep.write(('data: {"type":"content_block_delta","delta":{"type":"text_delta","text":%s}}\n\n' % json.dumps(t)).encode())
            await asyncio.sleep(0.01)
        await rep.write(b'data: {"type":"message_stop"}\n\n')
        return rep

    async def bout_en_bout():
        app = web.Application()
        app.router.add_post("/v1/messages", faux_messages)
        run = web.AppRunner(app)
        await run.setup()
        site = web.TCPSite(run, "127.0.0.1", 0)
        await site.start()
        port = site._server.sockets[0].getsockname()[1]
        cv.URL_API = "http://127.0.0.1:%d/v1/messages" % port
        cc = cv.Conversation(tmp, lambda: {"discord_claude_max_par_jour": 99, "discord_conversation_modele": "modele-test"}, env={"ANTHROPIC_API_KEY": FAUSSE_CLE}, horloge=lambda: midi)
        cumuls = []

        async def sur2(x):
            cumuls.append(x)
        rep = await cc.repondre("Comment vas-tu aujourd'hui, en détail ?", sur2)
        await run.cleanup()
        return rep, cumuls, cc
    rep, cumuls, cc = asyncio.run(bout_en_bout())
    verifier(rep == "Bonjour monsieur, tout va bien." and cumuls[0] == "Bonjour " and len(cumuls) == 3 and cc.dernier_mode == "api", "streaming réel : 3 fragments reçus au fil de l'eau")
    verifier(vus["cle"] == FAUSSE_CLE and vus["corps"]["model"] == "modele-test" and vus["corps"]["stream"] is True and vus["corps"]["max_tokens"] <= 400 and vus["corps"]["messages"][-1]["role"] == "user", "requête : clé en en-tête, modèle configurable, stream, réponse courte")

print("5) Dans le pont (faux client Discord)")


class Faux:
    def __init__(self):
        self.ev = []
        self.n = 9000

    async def envoyer(self, canal_id, texte, embed=None, mention=None):
        self.n += 1
        self.ev.append(("envoi", self.n, texte))
        return self.n

    async def editer(self, canal_id, msg_id, texte):
        self.ev.append(("edition", msg_id, texte))

    async def supprimer(self, canal_id, msg_id):
        self.ev.append(("suppr", msg_id))

    async def taper(self, canal_id, actif):
        self.ev.append(("saisie", actif))

    async def reaction(self, *a):
        pass


def banc(conv):
    d = Path(tempfile.mkdtemp(prefix="jarvis-test-pont-"))
    (d / "config.json").write_text(json.dumps({"discord_salons": {"jarvis": "1001"}}), encoding="utf-8")
    f = Faux()
    e = pl.Echange(d / "discord")
    return f, e, pl.Pont(f, e, pl.ConfigJarvis(d / "config.json"), LIAM, journal_sortie=lambda l: None, conversation=conv), d


async def scenario(pont, texte, mid):
    await pont.sur_message(LIAM, False, 1001, mid, texte)
    if pont._taches:
        await asyncio.gather(*list(pont._taches))

QUOTA.unlink(missing_ok=True)
f, e, p, d = banc(cv.Conversation(tmp, lambda: CFG, env={"ANTHROPIC_API_KEY": FAUSSE_CLE}, transport_api=api_ok, transport_cli=cli_ok, horloge=lambda: midi))
asyncio.run(scenario(p, "Pourquoi le ciel est-il bleu ?", 1))
verifier(f.ev[0][0] == "envoi" and "réfléchis" in f.ev[0][2] and f.ev[-1] == ("edition", f.ev[0][1], "Parce que la lumière se diffuse."), "« Je réfléchis… » aussitôt, remplacé par la réponse (même message)")
verifier(list(e.entrant.glob("*.json")) == [], "aucun fichier envoyé à Jarvis (donc aucun PowerShell, aucun routeur)")
asyncio.run(scenario(p, "Quelle heure est-il ?", 2))
verifier(f.ev[-1][0] == "envoi" and f.ev[-1][2].startswith("Il est 14 h") and not any("réfléchis" in str(x) for x in f.ev[-2:]), "heure : réponse directe, sans « Je réfléchis »")
asyncio.run(scenario(p, "ajoute à ma to-do : lait", 3))
verifier(len(list(e.entrant.glob("*.json"))) == 1 and ("saisie", True) in f.ev, "commande : transmise à Jarvis comme avant (+ « en train d'écrire »)")
shutil.rmtree(d, ignore_errors=True)


async def api_vide(texte, systeme, sur_texte, cfg):
    raise RuntimeError("x")


async def cli_vide(texte, systeme, cfg):
    return ""

QUOTA.unlink(missing_ok=True)
f, e, p, d = banc(cv.Conversation(tmp, lambda: CFG, env={}, transport_api=api_vide, transport_cli=cli_vide, horloge=lambda: midi))
asyncio.run(scenario(p, "Pourquoi le ciel est-il bleu ?", 4))
verifier(("suppr", f.ev[0][1]) in f.ev and len(list(e.entrant.glob("*.json"))) == 1, "aucune voie disponible : « Je réfléchis… » retiré, Jarvis reprend la main")
shutil.rmtree(d, ignore_errors=True)
shutil.rmtree(tmp, ignore_errors=True)
print()
if echecs:
    print("ÉCHEC : %d vérification(s) en échec." % echecs)
    sys.exit(1)
print("TOUT EST VERT.")
