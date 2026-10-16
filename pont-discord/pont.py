"""Pont Discord de Jarvis : processus SÉPARÉ, lancé et arrêté par Jarvis (jarvis.ps1 / arreter.ps1), seulement si config.json discord_actif = true.

Usage (par Jarvis) : python -I -u pont-discord\\pont.py --echange memoire\\discord --config config.json --stop-flag memoire\\STOP.flag
                     --quitter-flag memoire\\quitter.flag --parent <pid de Jarvis>
Le jeton (DISCORD_BOT_TOKEN) et l'identifiant de Liam (DISCORD_USER_ID) viennent de l'environnement hérité de Jarvis (.env) : jamais d'argument,
jamais de fichier, jamais dans une sortie. Prérequis : pip install discord.py   (et « Message Content Intent » activé sur le portail développeur).
Codes de sortie : 0 arrêt normal · 2 identifiants / dépendance manquants (pas de redémarrage) · 3 connexion refusée (jeton ou intentions ; pas de redémarrage) · autre = plantage (Jarvis redémarre le pont).
"""
import argparse
import asyncio
import os
import sys
from pathlib import Path

ICI = os.path.dirname(os.path.abspath(__file__))
if ICI not in sys.path:
    sys.path.insert(0, ICI)          # (python -I n'ajoute pas le dossier du script)
from conversation import Conversation  # noqa: E402
from pont_logique import ConfigJarvis, Echange, Pont, boucler, diagnostiquer_salons, masquer, serveurs_de_liam  # noqa: E402

SORTIE_IDENTIFIANTS = 2
SORTIE_CONNEXION = 3


def erreur(msg, secrets=()):
    sys.stderr.write("[pont] " + masquer(msg, secrets) + "\n")
    sys.stderr.flush()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--echange", required=True)
    p.add_argument("--config", default="")
    p.add_argument("--stop-flag", default="")
    p.add_argument("--quitter-flag", default="")
    p.add_argument("--parent", type=int, default=0)
    p.add_argument("--diagnostic", action="store_true", help="liste les NOMS des salons textuels visibles et leurs permissions, puis quitte")
    a = p.parse_args()

    jeton = os.environ.get("DISCORD_BOT_TOKEN", "").strip()
    uid = os.environ.get("DISCORD_USER_ID", "").strip()
    secrets = [jeton]
    if not jeton or not uid.isdigit():
        erreur("identifiants Discord manquants (DISCORD_BOT_TOKEN / DISCORD_USER_ID dans .env) : le pont ne démarre pas")
        return SORTIE_IDENTIFIANTS
    try:
        import discord
    except ImportError:
        erreur("discord.py n'est pas installé (pip install discord.py) : le pont ne démarre pas")
        return SORTIE_IDENTIFIANTS

    intents = discord.Intents.none()
    intents.guilds = True
    intents.guild_messages = True
    intents.guild_reactions = True
    intents.message_content = True          # privilégié : à activer sur https://discord.com/developers (Bot > Privileged Gateway Intents)
    client = discord.Client(intents=intents, allowed_mentions=discord.AllowedMentions.none())

    class Adaptateur:
        """Ce que Pont attend d'un client, branché sur discord.py."""
        def __init__(self):
            self.saisies = {}

        async def _canal(self, canal_id):
            return client.get_channel(canal_id) or await client.fetch_channel(canal_id)

        async def envoyer(self, canal_id, texte, embed=None, mention=None):
            e = None
            if embed:
                e = discord.Embed(title=embed["titre"] or None, description=embed["description"] or None, colour=discord.Colour(embed["couleur"]))
                for c in embed["champs"]:
                    e.add_field(name=c["nom"], value=c["valeur"], inline=c["inline"])
                if embed["pied"]:
                    e.set_footer(text=embed["pied"])
            am = discord.AllowedMentions(users=[discord.Object(id=int(mention))]) if mention else discord.AllowedMentions.none()      # une seule mention possible : Liam
            return (await (await self._canal(canal_id)).send(texte or None, embed=e, allowed_mentions=am)).id

        async def reaction(self, canal_id, msg_id, emoji):
            await (await self._canal(canal_id)).get_partial_message(msg_id).add_reaction(emoji)

        async def envoyer_fichier(self, canal_id, chemin):
            await (await self._canal(canal_id)).send(file=discord.File(chemin))

        async def editer(self, canal_id, msg_id, texte):
            await (await self._canal(canal_id)).get_partial_message(msg_id).edit(content=texte)

        async def supprimer(self, canal_id, msg_id):
            try:
                await (await self._canal(canal_id)).get_partial_message(msg_id).delete()
            except Exception:
                pass

        async def taper(self, canal_id, actif):
            t = self.saisies.pop(canal_id, None)
            if t:
                t.cancel()
            if actif:
                canal = await self._canal(canal_id)

                async def en_cours():
                    async with canal.typing():
                        await asyncio.Event().wait()
                self.saisies[canal_id] = asyncio.ensure_future(en_cours())

    cfg = ConfigJarvis(a.config)
    cle_api = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    secrets.append(cle_api)
    racine = str(Path(a.echange).resolve().parents[1])      # memoire\discord -> memoire -> racine de Jarvis
    conv = None if a.diagnostic else Conversation(racine, cfg.reglages, journal=lambda m: erreur(m, secrets), secrets=secrets)
    pont = Pont(Adaptateur(), Echange(a.echange), cfg, int(uid), secrets=secrets, stop_flag=a.stop_flag or None, conversation=conv)
    if conv is not None:
        pont.journal("conversation directe : %s" % ("API Anthropic (streaming)" if cle_api else "claude -p allégé (ANTHROPIC_API_KEY absente)"))

    infos_diag = []

    async def decouvrir():
        """Lit les salons des serveurs où se trouve Liam (les autres serveurs sont ignorés) et les associe par mot-clé."""
        try:
            def infos(g):
                res = []
                for c in g.text_channels:
                    p = c.permissions_for(g.me) if g.me else None
                    res.append({"nom": c.name, "voir": bool(p.view_channel) if p else True, "ecrire": bool(p.send_messages) if p else True,
                                "historique": bool(p.read_message_history) if p else True})
                return res
            serveurs = [{"id": g.id, "salons": [(c.id, c.name) for c in g.text_channels], "infos": infos(g), "obj": g} for g in client.guilds]

            async def est_membre(srv):
                try:
                    await srv["obj"].fetch_member(int(uid))
                    return True
                except discord.HTTPException:
                    return False
            cands = await serveurs_de_liam(serveurs, est_membre)
            infos_diag[:] = max((c.get("infos") or [] for c in cands), key=len, default=[])
            pont.maj_serveurs(cands)
        except Exception as e:
            pont.journal("lecture des salons impossible : %s" % type(e).__name__)

    @client.event
    async def on_ready():
        pont.connecte = True
        pont.journal("connecté à Discord")
        await decouvrir()
        if a.diagnostic:
            d = diagnostiquer_salons(infos_diag)
            print("Salons textuels visibles par le bot (%d) :" % len(d["salons"]))
            for x in d["salons"]:
                print("  - %s  [normalisé : %s]  voir=%s écrire=%s historique=%s  -> %s" % (x["nom"], x["normalise"], x["voir"], x["ecrire"], x["historique"], x["cle"] or "(aucun mot-clé)"))
            for pb in d["problemes"]:
                print("PROBLÈME : " + pb)
            await client.close()

    @client.event
    async def on_guild_channel_create(c):
        await decouvrir()

    @client.event
    async def on_guild_channel_delete(c):
        await decouvrir()

    @client.event
    async def on_guild_channel_update(avant, apres):
        if avant.name != apres.name:
            await decouvrir()

    @client.event
    async def on_guild_join(g):
        await decouvrir()

    @client.event
    async def on_guild_remove(g):
        await decouvrir()

    @client.event
    async def on_disconnect():
        pont.connecte = False

    @client.event
    async def on_message(m):
        try:
            await pont.sur_message(m.author.id, m.author.bot, m.channel.id, m.id, m.content)
        except Exception as e:
            pont.journal("message non traité : %s" % type(e).__name__)

    @client.event
    async def on_raw_reaction_add(r):
        try:
            await pont.sur_reaction(r.user_id, r.channel_id, r.message_id, str(r.emoji))
        except Exception as e:
            pont.journal("réaction non traitée : %s" % type(e).__name__)

    async def lancer():
        async with client:
            tache = asyncio.ensure_future(client.start(jeton))
            fin = asyncio.ensure_future(boucler(pont, a.parent, a.quitter_flag or None)) if not a.diagnostic else asyncio.ensure_future(asyncio.sleep(120))
            fait, _ = await asyncio.wait({tache, fin}, return_when=asyncio.FIRST_COMPLETED)
            if tache in fait:
                tache.result()                  # relève LoginFailure & co
            pont.journal("arrêt (%s)" % (fin.result() if fin in fait else "déconnexion"))
            for t in (fin, tache):
                t.cancel()
            await asyncio.gather(fin, tache, return_exceptions=True)

    try:
        asyncio.run(lancer())
    except discord.LoginFailure:
        erreur("connexion refusée : jeton invalide (DISCORD_BOT_TOKEN)", secrets)
        return SORTIE_CONNEXION
    except discord.PrivilegedIntentsRequired:
        erreur("connexion refusée : activez « Message Content Intent » sur le portail développeur Discord", secrets)
        return SORTIE_CONNEXION
    except KeyboardInterrupt:
        return 0
    except Exception as e:
        erreur("plantage : %s: %s" % (type(e).__name__, e), secrets)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
