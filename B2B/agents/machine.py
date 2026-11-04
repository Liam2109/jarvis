#!/usr/bin/env python3
"""Config locale et machine active des agents B2B (décision de Liam, 04/11/2026).

 - Réglages secrets ou propres à une machine : <agent>-config.local.json, à côté de <agent>-config.json (jamais versionné par git). Il surcharge les valeurs par défaut versionnées, clé par clé
   (les objets sont fusionnés en profondeur ; les clés qui commencent par « _ » sont ignorées).
 - b2b.local.json : « machine_active » (nom de la machine autorisée), « agents_actifs » (agents planifiés par maj-auto sur cette machine), « serveur » (profil serveur : aucun navigateur).
 - Un agent qui envoie ou écrit un état refuse de tourner si le nom de cette machine n'est pas « machine_active » (code 3) et le dit dans son journal. Jamais de repli : sans réglage, il refuse.
Aucun contenu de fichier local n'est jamais affiché ni journalisé (seulement son nom)."""
import json, os, sys
from datetime import datetime
from pathlib import Path

ICI = Path(__file__).resolve().parent
LOCAL = ICI / "b2b.local.json"
LECTURE = {"etat", "arreter", "file", "vagues", "rapport"}      # lecture seule ou arrêt de secours : permis sur toute machine
BOUCLES = {"continu", "ecouter", "demarrage"}      # boucles longues : refusées pour un agent déjà planifié par une tâche Jarvis-B2B-<agent> (jamais deux lancements du même agent)


class ErreurLocale(ValueError):
    """Fichier local illisible : le message nomme le fichier, jamais son contenu."""


def nom_machine():
    return (os.environ.get("JARVIS_B2B_MACHINE_TEST") or os.environ.get("COMPUTERNAME") or os.environ.get("HOSTNAME") or "").strip()


def _lire_objet(chemin):
    try: o = json.loads(chemin.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError): raise ErreurLocale(f"réglages locaux illisibles : {chemin.name}") from None
    if not isinstance(o, dict): raise ErreurLocale(f"réglages locaux illisibles : {chemin.name} (un objet JSON est attendu)")
    return o


def chemin_local(config):
    config = Path(config); return config.with_name(config.stem + ".local.json")


def _fusion(base, local):
    for k, v in local.items():
        if k.startswith("_"): continue
        if isinstance(v, dict) and isinstance(base.get(k), dict): _fusion(base[k], v)
        else: base[k] = v
    return base


def surcharge_locale(config, base):
    """Applique <agent>-config.local.json (s'il existe) sur le dictionnaire `base` (modifié et renvoyé)."""
    loc = chemin_local(config)
    return _fusion(base, _lire_objet(loc)) if loc.exists() else base


def lire_fusionnee(config):
    """Contenu du fichier par défaut + surcharge locale ({} si aucun des deux n'existe)."""
    config = Path(config); base = _lire_objet(config) if config.exists() else {}
    base = {k: v for k, v in base.items() if not k.startswith("_")}
    return surcharge_locale(config, base)


def ecrire_local(config, cles):
    """Écrit (fusionne) des clés dans le fichier LOCAL : un cache ou un réglage d'exécution ne modifie jamais un fichier suivi par git."""
    loc = chemin_local(config); actuel = _lire_objet(loc) if loc.exists() else {}
    for k, v in cles.items():
        if isinstance(v, dict) and isinstance(actuel.get(k), dict): actuel[k].update(v)
        else: actuel[k] = v
    loc.write_text(json.dumps(actuel, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _local_machine():
    return _lire_objet(LOCAL) if LOCAL.exists() else {}


def agents_actifs():
    try: a = _local_machine().get("agents_actifs")
    except ErreurLocale: return []
    return [str(x) for x in a] if isinstance(a, list) else []


def serveur():
    """Profil serveur (portable 6 Go) : aucun navigateur, aucun processus lourd. Posé par le lanceur (JARVIS_B2B_SERVEUR=1) ou par « serveur » dans b2b.local.json."""
    if os.environ.get("JARVIS_B2B_SERVEUR") == "1": return True
    try: return _local_machine().get("serveur") is True
    except ErreurLocale: return False


def verifier(agent, commande="", a_blanc=False, journal=None):
    """(autorisé, raison). Refus : journal de l'agent (<agent>-journal.log) sans aucun contenu secret."""
    if a_blanc or commande in LECTURE: return True, ""
    try:
        actif = _local_machine().get("machine_active")
        raison = None if isinstance(actif, str) and actif.strip() else "machine_active absent de b2b.local.json : aucun agent ne tourne tant que la machine active n'est pas choisie"
    except ErreurLocale as e: actif, raison = None, str(e)
    moi = nom_machine()
    if raison is None and actif.strip().lower() != moi.lower(): raison = f"cette machine est « {moi} », la machine active est « {actif.strip()} »"
    if raison is None and commande in BOUCLES and agent in agents_actifs():
        raison = f"agent planifié par la tâche Jarvis-B2B-{agent} (agents_actifs) : une boucle « {commande} » lancée par Jarvis ferait double emploi"
    if raison is None: return True, ""
    raison = f"refusé : {raison}"
    try:
        j = Path(journal) if journal else ICI / f"{agent}-journal.log"
        with j.open("a", encoding="utf-8") as f: f.write(f"{datetime.now():%Y-%m-%d %H:%M} | {agent} {commande} | {raison}\n")
    except OSError: pass
    return False, raison


def exiger(agent, commande="", a_blanc=False, journal=None):
    """À appeler au début de main() : sort avec le code 3 (et un message) si cette machine n'est pas la machine active."""
    ok, raison = verifier(agent, commande, a_blanc, journal)
    if not ok:
        print(f"  ! agent {agent} : {raison}"); sys.exit(3)
