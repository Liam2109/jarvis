#!/usr/bin/env python3
"""Superviseur du domaine VIDÉOS (22/11/2026) : toutes les 30 minutes, il regarde les sept agents de la chaîne vidéo (veille, scripts, marketing,
création, monteur, publication, nettoyage) et la cohérence de leurs données : ont-ils tourné ? leur dernier passage est-il en erreur ?
la chaîne s'est-elle déroulée dans l'ordre ? une légende prête à partir sur TikTok a-t-elle perdu la mention « Contenu généré par IA. » ?
Il corrige seul ce qui ne peut rien perdre et il n'écrit RIEN dès que la publication est en jeu : publier engage Liam, donc il alerte et attend son « go ».

  python agents\\superviseur-videos.py passage [--essai] [--maintenant AAAA-MM-JJTHH:MM]   un passage (tâche serveur, toutes les 30 min)
  python agents\\superviseur-videos.py etat                                                verrou, dernier passage, corrections du jour, ce qui attend un « go »

CORRIGE SEUL (rien ne peut être perdu) : relance une fois par jour un agent planté, silencieux ou bloqué ; retire une ligne strictement identique
de Videos\\journal-videos.csv ; retire un sujet strictement en double de Videos\\scripts\\sujets.json.
NE TOUCHE JAMAIS (alerte et attend « go ») : Videos\\videos-publication-etat.json (compléter une clé ou retirer une ligne de publication pourrait
faire republier une vidéo : c'est public et ça engage Liam), le verrou Videos\\publication.verrou (le retirer autoriserait deux publications en même
temps), le contenu d'une vidéo, d'une légende ou d'un script (texte destiné au public, jamais réécrit par un agent), un fichier illisible,
un plafond de publications dépassé, une date illogique, un maillon de la chaîne qui a tourné sans le précédent.
VERROU : ce domaine a son PROPRE verrou, go_superviseur_videos, en plus du « go superviseurs » commun : il reste fermé même quand les quatre autres
superviseurs sont ouverts, jusqu'au « go superviseur-videos » de Liam. --essai marche toujours."""
import argparse, sys
from datetime import datetime
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import machine as M   # machine active (refus hors du serveur, sauf --essai)

sys.path.insert(0, str(ICI.parent / "harness"))
import superviseurs as S   # moteur commun : réglages, verrou, état, journal, traces, relance, classement sûr / risqué, Discord, fiche a-valider

AGENT, DOMAINE = "superviseur-videos", "Vidéos"
AGENTS_SUIVIS = ["videos-veille", "videos-scripts", "videos-marketing", "videos-creation", "videos-monteur", "videos-publication", "videos-nettoyage"]
# Ordre d'un passage de la chaîne (Videos\README.md) : chaque maillon reçoit du précédent. Le monteur est appelé par la création (aucune tâche à lui)
# et la publication reste verrouillée : ni l'un ni l'autre n'entre dans le contrôle de l'ordre.
CHAINE = ["videos-veille", "videos-scripts", "videos-marketing", "videos-creation"]
DEFAUT = {"heure_resume": "08:45", "go_superviseur_videos": False, "publications_max_par_jour": 3, "legendes_max": 40}
RACINE = ICI.parent.parent
VIDEOS = RACINE / "Videos"
JOURNAL_CSV = VIDEOS / "journal-videos.csv"
SUJETS = VIDEOS / "scripts" / "sujets.json"
PUBLICATION_ETAT = VIDEOS / "videos-publication-etat.json"
VERROU_PUBLICATION = VIDEOS / "publication.verrou"
A_VALIDER_VIDEOS = VIDEOS / "a-valider"
MENTION_IA = "Contenu généré par IA."
VERROU_HEURES = 3      # publication.py abandonne lui-même son verrou au bout de 3 h : au-delà, c'est anormal


def _jour(maintenant): return f"{maintenant or datetime.now():%Y-%m-%d}"


def controle_publication(etat=None, maintenant=None, conf=None, dossier_traces=None):
    """Videos\\videos-publication-etat.json : SIGNALÉ, JAMAIS corrigé. Compléter une clé absente ou retirer une ligne en double pourrait faire
    republier une vidéo sur TikTok — c'est public, ça engage Liam, et une publication ne se reprend pas. Verrou de publication oublié : signalé aussi."""
    out = []
    d, pb = S.lire_json(PUBLICATION_ETAT)
    if pb: out.append(pb)
    elif isinstance(d, dict):
        nom = PUBLICATION_ETAT.name
        for cle, typ in (("publications", dict), ("arrets", dict), ("essais", dict)):
            if cle not in d:
                out.append(S.risque("videos-publication", f"clé « {cle} » absente de {nom}",
                                    "jamais complétée tout seul : une vidéo déjà publiée pourrait repartir", cle=f"{nom}|{cle}|absente"))
            elif not isinstance(d[cle], typ):
                out.append(S.risque("videos-publication", f"« {cle} » de {nom} a un type inattendu",
                                    f"{type(d[cle]).__name__} au lieu de {typ.__name__} : rien n'est touché", cle=f"{nom}|{cle}|type"))
        out += S.controle_dates_valides("videos-publication", PUBLICATION_ETAT, ["publications"], "jours de publication")
        out += _controle_plafonds(d.get("publications"), nom, (conf or {}).get("publications_max_par_jour", 3))
    elif d is not None:
        out.append(S.risque("videos-publication", f"{PUBLICATION_ETAT.name} n'est pas un objet JSON", "état de publication : rien n'est touché",
                            cle=f"{PUBLICATION_ETAT.name}|racine"))
    if VERROU_PUBLICATION.is_file():
        try: age_h = (datetime.now().timestamp() - VERROU_PUBLICATION.stat().st_mtime) / 3600
        except OSError: age_h = 0
        if age_h > VERROU_HEURES:
            out.append(S.risque("videos-publication", f"verrou de publication en place depuis {int(age_h)} h",
                                "publication.verrou n'est jamais retiré par un superviseur : le retirer autoriserait deux publications en même temps",
                                cle=f"publication.verrou|{_jour(maintenant)}"))
    return out


def _controle_plafonds(pubs, nom, plafond):
    """Plafond de publications par jour et par ligne, et deux fois la même vidéo au même passage. Signalé seulement : retirer une ligne de
    publication ferait republier la vidéo au prochain passage."""
    if not isinstance(pubs, dict): return []
    out = []
    for jour, liste in sorted(pubs.items()):
        if not isinstance(liste, list): continue
        par_ligne = {}
        for p in liste:
            if isinstance(p, dict): par_ligne.setdefault(str(p.get("ligne")), []).append(p)
        for ligne, faites in sorted(par_ligne.items()):
            if len(faites) > plafond:
                out.append(S.risque("videos-publication", f"{len(faites)} publications le {jour} sur la ligne {ligne} (plafond {plafond})",
                                    "rien n'est retiré : une ligne de publication retirée ferait republier la vidéo", cle=f"{nom}|{jour}|{ligne}|plafond"))
            vus = set()
            for p in faites:
                c = (str(p.get("passage")), str(p.get("video")))
                if c in vus:
                    out.append(S.risque("videos-publication", f"deux fois la même vidéo publiée le {jour} au passage {p.get('passage')}",
                                        f"{str(p.get('video'))[:60]} : à vérifier sur TikTok, rien n'est touché ici", cle=f"{nom}|{jour}|{p.get('video')}|double"))
                vus.add(c)
    return out


def controle_legendes(etat=None, maintenant=None, conf=None, dossier_traces=None):
    """Légendes des vidéos qui attendent Liam (Videos\\a-valider\\*.txt) : mention « Contenu généré par IA. » perdue, phrase interdite,
    lien de paiement inconnu, secret. Un texte qui partira sur TikTok n'est JAMAIS réécrit par un agent : Liam le corrige lui-même."""
    if not A_VALIDER_VIDEOS.is_dir(): return []
    out = []
    for f in sorted(A_VALIDER_VIDEOS.glob("*.txt"))[:int((conf or {}).get("legendes_max", 40))]:
        try: t = f.read_text(encoding="utf-8", errors="replace")
        except OSError: continue
        if MENTION_IA.lower() not in t.lower():
            out.append(S.risque("videos-creation", f"légende sans la mention « {MENTION_IA} » : {f.name}",
                                "mention obligatoire sur TikTok : jamais ajoutée par un agent dans un texte destiné au public", cle=f"{f.name}|mention-ia"))
        for faute in S.fautes_de_texte(t):
            out.append(S.risque("videos-creation", f"{faute} dans {f.name}", "légende destinée au public : jamais réécrite par un agent", cle=f"{f.name}|{faute[:40]}"))
    return out


def controle_journal():
    """Videos\\journal-videos.csv (données d'exécution, hors git) : lignes strictement identiques retirées, la première reste, l'ordre ne bouge pas."""
    return S.controle_doublons_csv("videos-creation", JOURNAL_CSV)


def controle_sujets():
    """Videos\\scripts\\sujets.json : historique des sujets déjà traités, qui sert à ne pas se répéter. Un doublon strictement identique ne sert à rien : retiré."""
    return S.controle_doublons("videos-scripts", SUJETS, [], "sujets déjà traités")


def controle_chaine(etat=None, maintenant=None, conf=None, dossier_traces=None):
    """Ordre de la chaîne du jour : un maillon qui a tourné alors que le précédent n'a jamais tourné aujourd'hui.
    Signalé seulement : relancer la chaîne à l'envers refabriquerait des vidéos, et personne ne saurait laquelle garder.
    Un maillon que Liam n'a pas planifié sur cette machine (hors agents_actifs, sans tâche ou désactivé) sort de la chaîne : son silence est normal."""
    jour = _jour(maintenant)
    ts, actifs = S.taches(), S.agents_actifs()
    chaine = [n for n in CHAINE if n in actifs and isinstance(ts.get(n), dict) and not ts[n].get("desactive")]
    passages = {nom: len(S.executions(nom, jour, dossier_traces)) for nom in chaine}
    out = []
    for i in range(1, len(chaine)):
        amont, aval = chaine[i - 1], chaine[i]
        if passages[aval] and not passages[amont]:
            out.append(S.risque(aval, f"{aval} a tourné aujourd'hui, {amont} jamais",
                                "la chaîne vidéo s'est déroulée dans le désordre : rien n'est relancé, Liam dit quoi garder", cle=f"chaine|{amont}|{aval}|{jour}"))
    return out


AVEC_CONTEXTE = (controle_publication, controle_legendes, controle_chaine)
CONTROLES = [("publication", controle_publication), ("légendes", controle_legendes), ("journal des vidéos", controle_journal),
             ("sujets", controle_sujets), ("chaîne", controle_chaine)]


def controles(conf, maintenant=None, dossier_traces=None, etat=None):
    """Les contrôles du domaine. Ceux qui ont besoin du contexte du passage (heure figée des tests, dossier de traces, réglages) le reçoivent ici."""
    return [(nom, (lambda f=f: f(etat=etat, maintenant=maintenant, conf=conf, dossier_traces=dossier_traces)) if f in AVEC_CONTEXTE else f)
            for nom, f in CONTROLES]


def cmd_etat(conf):
    r = S.resume_pour_jarvis(AGENT, DOMAINE, conf)
    print(f"Superviseur {DOMAINE} : {r['etat']} ; verrou « {conf.get('verrou_propre') or 'go superviseurs'} » {r['verrou']} ; "
          f"dernier passage : {r['dernier_passage'] or 'aucun'}.")
    print(f"  agents suivis : {', '.join(AGENTS_SUIVIS)}")
    print(f"  corrections du jour : {len(r['corrections'])}" + ("".join(f"\n    - {x}" for x in r["corrections"][:10]) if r["corrections"] else ""))
    print(f"  en attente d'un « go » : {len(r['bloques'])}" + ("".join(f"\n    - {x}" for x in r["bloques"][:10]) if r["bloques"] else ""))
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog=AGENT, description="Superviseur du domaine Vidéos : chaîne à l'heure, légendes conformes, publication jamais touchée.")
    sp = p.add_subparsers(dest="cmd", required=True)
    j = sp.add_parser("passage"); j.add_argument("--essai", "--a-blanc", dest="essai", action="store_true", help="lit, affiche, n'écrit rien, n'envoie rien, ne relance rien")
    j.add_argument("--maintenant", default=None, help="heure figée (tests)")
    sp.add_parser("etat")
    a = p.parse_args(argv)
    M.exiger(AGENT, a.cmd, getattr(a, "essai", False))
    try:
        conf = S.cfg(AGENT, DEFAUT)
        if a.cmd == "etat": return cmd_etat(conf)
        m = datetime.fromisoformat(a.maintenant) if a.maintenant else None
        return S.lancer(AGENT, DOMAINE, AGENTS_SUIVIS, controles(conf, m), conf, a.essai, m)
    except S.ErreurAgent as e:
        print(f"  ! {e}"); return 2
    except OSError as e:
        print(f"  ! erreur de fichier : {e.strerror or type(e).__name__}"); return 2


if __name__ == "__main__":
    sys.exit(main())
