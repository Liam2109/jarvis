#!/usr/bin/env python3
"""Maillon 1 de docs\\agents\\CARTE-RELAIS.md (23/11/2026) : réponse courte et automatique à un prospect qui répond POSITIVEMENT : un membre de l'équipe rappelle, on demande le numéro et le jour + matin/après-midi.
Appelé par reponses.py, jamais seul. Réglage séparé reponse_auto_envoi (reponses-config.json), FAUX par défaut : en simulation, le message est écrit dans
B2B\\donnees\\reponses-auto\\ et annoncé sur Discord, RIEN n'est envoyé. Une seule réponse par prospect, aucune relance par ce maillon.
Jamais de réponse automatique à un STOP, un refus ou un message ambigu (classés « autre » par reponses.classer) : seule l'alerte Discord existante part.
Aucun texte inventé : modèle fixe, aucun agenda lu, aucun créneau. Aucun prix, aucune promesse de résultat."""
import json, os, re
from datetime import date
from pathlib import Path

ICI = Path(__file__).resolve().parent
DONNEES = ICI.parent / "donnees"
ETAT = DONNEES / "reponse-auto-etat.json"       # {clé prospect: {mode, date, mid}} : une seule réponse par prospect
DOSSIER = DONNEES / "reponses-auto"             # messages écrits en simulation (et copie des envoyés)
RELAIS = DONNEES / "relais.jsonl"               # une ligne de relais par événement, lue par le tableau de bord
if os.environ.get("JARVIS_TEST") == "1":        # tests : jamais les vrais fichiers
    import tempfile; _t = Path(tempfile.mkdtemp(prefix="reponse-auto-test-")); DONNEES = _t; ETAT = _t / "etat.json"; DOSSIER = _t / "msgs"; RELAIS = _t / "relais.jsonl"
BLOQUES = ("STOP", "refusé", "devis", "signé", "exclu")
JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


def message(ident, signer):
    """Texte fixe, ton oral, aucun créneau ni agenda : un membre de l'équipe rappelle ; on demande le numéro et le jour + matin/après-midi. signer(texte, ident) ajoute signature et ligne STOP."""
    lignes = ["Merci pour votre réponse.", "",
              "Un membre de notre équipe va vous rappeler pour vous expliquer en deux mots ce que nous vous proposons.", "",
              "Pour que ça tombe au bon moment, dites-moi simplement :",
              "• le meilleur numéro pour vous joindre ;",
              "• le jour et la tranche horaire qui vous arrangent (matin ou après-midi)."]
    return signer("\n".join(lignes), ident)


def objet_reponse(objet):
    o = (objet or "").strip() or "Votre réponse"
    return o if re.match(r"\s*(re|ré|rép)\s*:", o, re.I) else "Re: " + o


def etat_lire():
    try: return json.loads(ETAT.read_text(encoding="utf-8")) if ETAT.exists() else {}
    except (OSError, ValueError): return {}


def etat_noter(cle, mode, mid):
    e = etat_lire(); e[cle] = {"mode": mode, "date": str(date.today()), "mid": mid}
    ETAT.parent.mkdir(parents=True, exist_ok=True); tmp = ETAT.with_name(ETAT.name + ".tmp")
    tmp.write_text(json.dumps(e, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8"); os.replace(tmp, ETAT)


def raison_de_ne_pas_repondre(cl, statut_avant, cle, simulation, destinataire):
    """None = on peut répondre ; sinon la raison (affichée dans l'alerte Discord, qui prévient Liam à la place)."""
    if cl != "positive": return "réponse non positive : aucune réponse automatique"
    if statut_avant in BLOQUES: return f"prospect déjà en « {statut_avant} »"
    if not destinataire or "@" not in destinataire: return "adresse de réponse introuvable"
    ancien = etat_lire().get(cle)
    if ancien and (ancien.get("mode") == "envoye" or simulation): return f"déjà répondu le {ancien.get('date')} (une seule réponse par prospect)"
    return None


def ecrire_message(p, destinataire, objet, texte, mode, jour=None):
    DOSSIER.mkdir(parents=True, exist_ok=True)
    nom = re.sub(r"[^a-z0-9]+", "-", (p.get("nom") or "prospect").lower()).strip("-")[:40] or "prospect"
    f = DOSSIER / f"{jour or date.today()}-{nom}.md"
    f.write_text(f"# Réponse automatique ({mode}) — {p.get('nom', '')}\n\nÀ : {destinataire}\nObjet : {objet}\n\n{texte}\n", encoding="utf-8")
    return f


def ligne_relais(p, mode):
    RELAIS.parent.mkdir(parents=True, exist_ok=True)
    with open(RELAIS, "a", encoding="utf-8") as f:
        f.write(json.dumps({"date": str(date.today()), "relais": "réponse positive → réponse au prospect (numéro et créneau demandés)", "prospect": p.get("nom", ""), "ville": p.get("ville", ""),
                            "mode": mode}, ensure_ascii=False) + "\n")


def noter_registre(p, mode, registre=None):
    """Ajoute au lead du registre le champ « reponse_auto » (aucun autre champ : dernier_resultat et retour pilotent les rappels). Introuvable : rien."""
    import registre as RG
    try:
        with RG.verrou():
            reg = RG.charger(); k = RG.trouver(reg, p.get("nom"), p.get("ville"), p.get("telephone"))
            if not k: return False
            reg["entreprises"][k]["reponse_auto"] = {"date": str(date.today()), "mode": mode}; RG.sauver(reg); return True
    except (OSError, ValueError, TimeoutError): return False
