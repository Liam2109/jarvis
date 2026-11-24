#!/usr/bin/env python3
"""Vue Jarvis des superviseurs (21/11/2026) : le seul endroit où Liam voit l'état des quatre domaines d'un coup d'œil (Vente, Prospection, Sites, Mail).
Elle NE CORRIGE RIEN et ne relance rien : elle lit l'état et le journal que chaque superviseur a déjà écrits, et les remet en un fichier court
(B2B\\logs\\superviseurs\\ETAT-SUPERVISEURS.md, hors git, réécrit à chaque passage, sans historique) plus UN seul message Discord groupé par jour.

  python agents\\jarvis-vue.py passage [--essai] [--maintenant AAAA-MM-JJTHH:MM]   un passage (tâche serveur, toutes les 30 min)
  python agents\\jarvis-vue.py etat                                                le tableau des quatre domaines, à l'écran

Un domaine est : « ok » (rien à signaler), « corrigé » (le superviseur a réparé tout seul aujourd'hui), « bloqué » (il attend un « go » de Liam),
« jamais passé » (le superviseur n'a pas encore tourné) ou « inconnu » (son état est illisible). Aucun chiffre n'est recalculé ici : si deux domaines
se contredisent, c'est leur superviseur qui le dit, pas la vue.
VERROU : aucun message tant que go_superviseurs n'est pas true dans un fichier de réglages local (après le « go superviseurs » de Liam). --essai marche toujours."""
import argparse, sys, time
from datetime import date, datetime
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import machine as M   # machine active (refus hors du serveur, sauf --essai)

sys.path.insert(0, str(ICI.parent / "harness"))
import superviseurs as S   # moteur commun (lecture des états, Discord gardé, traces)
import traces as T

AGENT, DOMAINE = "jarvis-vue", "Jarvis"
DEFAUT = {"heure_resume": "19:40"}
DOMAINES = [("superviseur-vente", "Vente"), ("superviseur-prospection", "Prospection"), ("superviseur-sites", "Sites"), ("superviseur-mail", "Mail")]
SORTIE = ICI.parent / "logs" / "superviseurs" / "ETAT-SUPERVISEURS.md"
SIGNES = {"ok": "OK", "corrigé": "corrigé", "bloqué": "BLOQUÉ (attend « go »)", "jamais passé": "jamais passé", "inconnu": "état illisible"}


def resumes(conf):
    """L'état remonté par les superviseurs de domaine, lu tel quel (aucun contrôle refait, aucune écriture)."""
    out = []
    for agent, domaine in DOMAINES:
        try: r = S.resume_pour_jarvis(agent, domaine, S.cfg(agent, {}))
        except Exception as ex: r = {"domaine": domaine, "agent": agent, "etat": "inconnu", "dernier_passage": "", "corrections": [], "bloques": [f"réglages ou état illisibles ({type(ex).__name__})"], "verrou": "?"}
        out.append(r)
    return out


def texte_fichier(rs, maintenant):
    """Fichier court : une ligne par domaine, puis ce qui attend un « go ». Pas d'historique (il est dans git et dans les journaux des superviseurs)."""
    l = [f"# État des superviseurs — {maintenant:%d/%m/%Y %H:%M}", "",
         "Écrit par la vue Jarvis (`B2B\\agents\\jarvis-vue.py`), qui ne corrige rien. Réécrit à chaque passage, sans historique.", "",
         "| Domaine | État | Dernier passage | Corrections du jour | En attente de « go » |", "|---|---|---|---|---|"]
    for r in rs:
        l.append(f"| {r['domaine']} | {SIGNES.get(r['etat'], r['etat'])} | {r['dernier_passage'] or '—'} | {len(r['corrections'])} | {len(r['bloques'])} |")
    bloques = [(r["domaine"], x) for r in rs for x in r["bloques"]]
    corriges = [(r["domaine"], x) for r in rs for x in r["corrections"]]
    l += ["", "## En attente d'un « go » de Liam (rien n'a été touché)", ""]
    l += [f"- **{d}** : {x}" for d, x in bloques] or ["- rien"]
    l += ["", "## Corrigé tout seul aujourd'hui", ""]
    l += [f"- **{d}** : {x}" for d, x in corriges] or ["- rien"]
    l += ["", "Détail d'un domaine : `python agents\\<superviseur>.py etat`. Les corrections risquées ne sont jamais faites : elles attendent Liam."]
    return "\n".join(l) + "\n"


def message(rs):
    """UN message Discord groupé : une ligne par domaine, puis ce qui bloque."""
    etats = ", ".join(f"{r['domaine']} : {SIGNES.get(r['etat'], r['etat'])}" for r in rs)
    bloques = [(r["domaine"], x) for r in rs for x in r["bloques"]]
    l = [f"**Superviseurs — état du jour** ({len([r for r in rs if r['etat'] == 'ok'])}/{len(rs)} domaine(s) sans rien à signaler)", f"- {etats}"]
    if bloques:
        l += ["- **en attente de ton « go »** (rien n'a été touché) :"] + [f"  - {d} — {x}" for d, x in bloques[:12]]
        if len(bloques) > 12: l.append(f"  - … et {len(bloques) - 12} autre(s), voir le fichier d'état")
    corriges = sum(len(r["corrections"]) for r in rs)
    if corriges: l.append(f"- {corriges} correction(s) faite(s) tout seul aujourd'hui (détail dans le fichier d'état)")
    return "\n".join(l)


def cmd_passage(conf, essai, maintenant=None, envoyer=None):
    t0 = time.time(); m = maintenant or datetime.now(); jour = f"{m:%Y-%m-%d}"
    rs = resumes(conf)
    texte = message(rs)
    verrou = not conf["go_superviseurs"] and not essai
    etat = S.etat_lire(AGENT)
    a_dire = jour not in etat["resumes"] and f"{m:%H:%M}" >= conf["heure_resume"]
    if essai: poste = "essai : rien écrit, rien envoyé"
    elif verrou: poste = "verrou « go superviseurs » fermé : rien envoyé"
    elif not a_dire: poste = "fichier à jour ; message du jour déjà posté ou pas encore l'heure"
    elif conf["envoi_automatique"]: poste = "posté sur Discord" if (envoyer or S.alerter_discord)(texte) else "Discord : non envoyé, réessayé au prochain passage"
    else: poste = "simulation (envoi_automatique = false) : rien envoyé"
    print(texte); print(f"  [{poste}]")
    if not essai:
        try:
            SORTIE.parent.mkdir(parents=True, exist_ok=True); SORTIE.write_text(texte_fichier(rs, m), encoding="utf-8")
            print(f"  état écrit dans {SORTIE.relative_to(ICI.parent.parent)}")
        except OSError as e: print(f"  ! fichier d'état non écrit ({e.strerror or type(e).__name__})")
        if a_dire and "non envoyé" not in poste and not verrou: etat["resumes"][jour] = f"{m:%H:%M}"
        S.etat_ecrire(AGENT, etat)
        S.journaliser(AGENT, "passage", f"{len([r for r in rs if r['etat'] == 'ok'])}/{len(rs)} domaine(s) ok, "
                      f"{sum(len(r['bloques']) for r in rs)} en attente ; {poste}")
        T.ecrire(AGENT, "passage", f"{len(rs)} domaine(s), {sum(len(r['bloques']) for r in rs)} en attente de go", time.time() - t0, ok=True)
    return 0


def cmd_etat(conf):
    rs = resumes(conf)
    print(f"Vue Jarvis des superviseurs ({date.today():%d/%m/%Y}) — verrou « go superviseurs » {'ouvert' if conf['go_superviseurs'] else 'fermé'}")
    for r in rs:
        print(f"  {r['domaine']:<12} {SIGNES.get(r['etat'], r['etat']):<24} dernier passage : {r['dernier_passage'] or 'aucun'} ; "
              f"{len(r['corrections'])} correction(s), {len(r['bloques'])} en attente")
        for x in r["bloques"][:5]: print(f"      - {x}")
    print(f"  fichier : {SORTIE}" + ("" if SORTIE.exists() else " (pas encore écrit)"))
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog=AGENT, description="Vue Jarvis des superviseurs de domaine : un fichier court et un message Discord groupé, aucune correction.")
    sp = p.add_subparsers(dest="cmd", required=True)
    j = sp.add_parser("passage"); j.add_argument("--essai", "--a-blanc", dest="essai", action="store_true", help="lit, affiche, n'écrit rien, n'envoie rien")
    j.add_argument("--maintenant", default=None, help="heure figée (tests)")
    sp.add_parser("etat")
    a = p.parse_args(argv)
    M.exiger(AGENT, a.cmd, getattr(a, "essai", False))
    try:
        conf = S.cfg(AGENT, DEFAUT)
        if a.cmd == "etat": return cmd_etat(conf)
        return cmd_passage(conf, a.essai, datetime.fromisoformat(a.maintenant) if a.maintenant else None)
    except S.ErreurAgent as e:
        print(f"  ! {e}"); return 2
    except OSError as e:
        print(f"  ! erreur de fichier : {e.strerror or type(e).__name__}"); return 2


if __name__ == "__main__":
    sys.exit(main())
