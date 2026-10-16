r"""Poste UN message (ou un fichier texte) dans un salon Discord avec le bot, SANS passer par Jarvis ni par le pont (appel REST direct, stdlib seulement).

Usage : python -I pont-discord\notifier.py --racine <dossier Jarvis> [--salon systeme] (--texte "..." | --fichier chemin.txt)
Le jeton (DISCORD_BOT_TOKEN) vient de l'environnement (.env chargé par jarvis.ps1) : jamais d'argument, jamais affiché. Le salon vient de config.json (discord_salons),
sinon de memoire\discord-salons.json (écrit par le pont), sinon « jarvis ». Seul le salon désigné est écrit ; aucune mention (@) n'est possible.
Sortie : une ligne « ok : N message(s) envoyé(s) dans #<salon> » ou « echec : <raison sans secret> ». Code 0 = envoyé."""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

API = "https://discord.com/api/v10"


def identifiant_salon(racine, cle):
    racine = Path(racine)
    try:
        forces = json.loads((racine / "config.json").read_text(encoding="utf-8-sig")).get("discord_salons") or {}
        loc = racine / "config.local.json"
        if loc.exists():
            forces.update(json.loads(loc.read_text(encoding="utf-8-sig")).get("discord_salons") or {})
    except (OSError, ValueError):
        forces = {}
    for c in (cle, "alertes" if cle == "systeme" else cle):
        v = str(forces.get(c, "")).strip()
        if v.isdigit():
            return int(v), cle
    try:
        cache = json.loads((racine / "memoire" / "discord-salons.json").read_text(encoding="utf-8")).get("salons") or {}
        if str(cache.get(cle, "")).isdigit():
            return int(cache[cle]), cle
        if str(cache.get("jarvis", "")).isdigit():
            return int(cache["jarvis"]), "jarvis"
    except (OSError, ValueError):
        pass
    return None, cle


def morceaux(texte, taille=1900):
    texte = texte.replace("@", "@​").strip()
    res = []
    while len(texte) > taille:
        coupe = texte.rfind("\n", 0, taille)
        if coupe < taille // 2:
            coupe = taille
        res.append(texte[:coupe].rstrip())
        texte = texte[coupe:].lstrip()
    if texte:
        res.append(texte)
    return res


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--racine", required=True)
    p.add_argument("--salon", default="systeme")
    p.add_argument("--texte", default="")
    p.add_argument("--fichier", default="")
    a = p.parse_args()
    jeton = os.environ.get("DISCORD_BOT_TOKEN", "").strip()
    if not jeton:
        print("echec : DISCORD_BOT_TOKEN absent de .env")
        return 2
    texte = a.texte
    if a.fichier:
        texte = Path(a.fichier).read_text(encoding="utf-8-sig")
    if not texte.strip():
        print("echec : rien à envoyer")
        return 2
    cid, nom = identifiant_salon(a.racine, a.salon)
    if not cid:
        print("echec : salon « %s » introuvable (config.json discord_salons ou memoire\discord-salons.json)" % a.salon)
        return 2
    n = 0
    for m in morceaux(texte):
        req = urllib.request.Request("%s/channels/%d/messages" % (API, cid), data=json.dumps({"content": m, "allowed_mentions": {"parse": []}}).encode("utf-8"), method="POST",
                                     headers={"Authorization": "Bot " + jeton, "Content-Type": "application/json", "User-Agent": "DiscordBot (https://github.com/Liam2109, 1.0)"})
        try:
            urllib.request.urlopen(req, timeout=20).read()
            n += 1
        except urllib.error.HTTPError as e:
            print("echec : Discord a répondu HTTP %d (%s)" % (e.code, "permission ou salon invalide" if e.code in (401, 403, 404) else "réessayer plus tard"))
            return 1
        except Exception as e:
            print("echec : %s" % re.sub(r"\S*" + re.escape(jeton) + r"\S*", "[SECRET]", type(e).__name__))
            return 1
    print("ok : %d message(s) envoyé(s) dans #%s" % (n, nom))
    return 0


if __name__ == "__main__":
    sys.exit(main())
