#!/usr/bin/env python3
"""Agent Suivi : suivi-prospects.csv. Le script ne change JAMAIS un statut tout seul : seule la commande « statut » le fait, à la demande de Liam.

  python agents\\suivi.py init prospects.csv                 ajoute les prospects absents, statut « à contacter » (ne touche pas aux autres)
  python agents\\suivi.py statut "Nom" <statut> [--ville V] [--date AAAA-MM-JJ] [--note "..."]
  python agents\\suivi.py a-relancer                         liste (lecture seule) ceux à relancer : « envoyé » depuis J+2 sans réponse
  python agents\\suivi.py liste [statut]
Statuts : à contacter, envoyé, répondu, maquette envoyée, devis, signé, refusé, STOP.
« envoyé » (ou « maquette envoyée ») pose la relance à date + 2 jours ; tout autre statut efface la relance.
STOP = exclusion définitive : le prospect ne reçoit plus aucun message (l'agent Rédaction le saute). Ce script n'envoie rien."""
import argparse, csv, sys
from datetime import date, timedelta
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "sites" / "moteur"))
import generer as G

FICHIER = RACINE / "suivi-prospects.csv"
STATUTS = ["à contacter", "envoyé", "répondu", "maquette envoyée", "devis", "signé", "refusé", "STOP", "exclu"]
COLS = ["nom", "metier", "ville", "email", "telephone", "statut", "date_statut", "date_envoi", "relance_j2", "maquette", "note", "historique"]
RELANCE = ("envoyé", "maquette envoyée")


def lire():
    if not FICHIER.exists(): return []
    with open(FICHIER, encoding="utf-8-sig", newline="") as f: return list(csv.DictReader(f, delimiter=";"))


def ecrire(lignes):
    with open(FICHIER, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS, delimiter=";"); w.writeheader(); w.writerows(lignes)


def cle(r): return G.slug(r["nom"]) + "|" + G.slug(r["ville"])


def init(csv_prospects):
    lignes = lire(); vus = {cle(r) for r in lignes}; n = 0
    for p in G.lire_csv(csv_prospects):
        if not p.get("nom") or not p.get("ville"): continue
        r = {c: "" for c in COLS}
        r.update(nom=p["nom"], metier=p.get("metier", ""), ville=p["ville"], email=p.get("email", ""), telephone=p.get("telephone", ""),
                 statut="à contacter", date_statut=str(date.today()), maquette=f"{G.slug(p['nom'])}-{G.jeton(p['nom'], p['ville'])}",
                 historique=f"{date.today()} créé : à contacter")
        if cle(r) in vus: continue
        lignes.append(r); vus.add(cle(r)); n += 1
    ecrire(lignes)
    print(f"{n} prospect(s) ajouté(s), {len(lignes)} au total dans {FICHIER}")


def statut(nom, nouveau, ville, jour, note):
    if nouveau not in STATUTS: sys.exit(f"Statut inconnu : {nouveau}. Choix : {', '.join(STATUTS)}")
    lignes = lire()
    cand = [r for r in lignes if G.slug(r["nom"]) == G.slug(nom) and (not ville or G.slug(r["ville"]) == G.slug(ville))]
    if len(cand) != 1: sys.exit(f"{len(cand)} prospect(s) trouvé(s) pour « {nom} » : précise --ville." if cand else f"Prospect inconnu : {nom}")
    r = cand[0]; d = jour or str(date.today())
    ancien = r["statut"]
    r["statut"], r["date_statut"] = nouveau, d
    if nouveau in RELANCE:
        r["date_envoi"] = d
        r["relance_j2"] = str(date.fromisoformat(d) + timedelta(days=2))
    else:
        r["relance_j2"] = ""
    if note: r["note"] = note
    r["historique"] = (r["historique"] + f" | {d} {ancien} -> {nouveau}").strip(" |")
    ecrire(lignes)
    print(f"{r['nom']} : {ancien} -> {nouveau} ({d})" + (f" ; relance le {r['relance_j2']}" if r["relance_j2"] else ""))


def a_relancer():
    auj = str(date.today())
    dus = [r for r in lire() if r["statut"] in RELANCE and r["relance_j2"] and r["relance_j2"] <= auj]
    for r in dus: print(f"- {r['nom']} ({r['ville']}) : {r['statut']} le {r['date_envoi']}, relance due le {r['relance_j2']}")
    print(f"{len(dus)} relance(s) due(s) au {auj}. Aucun message n'est préparé ni envoyé par cette commande.")


def liste(filtre):
    for r in lire():
        if not filtre or r["statut"] == filtre:
            print(f"{r['statut']:<17} {r['nom']} ({r['ville']}) {('relance ' + r['relance_j2']) if r['relance_j2'] else ''}")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("init").add_argument("csv")
    s = sp.add_parser("statut"); s.add_argument("nom"); s.add_argument("nouveau"); s.add_argument("--ville"); s.add_argument("--date"); s.add_argument("--note")
    sp.add_parser("a-relancer"); sp.add_parser("liste").add_argument("filtre", nargs="?")
    a = ap.parse_args()
    if a.cmd == "init": init(a.csv)
    elif a.cmd == "statut": statut(a.nom, a.nouveau, a.ville, a.date, a.note)
    elif a.cmd == "a-relancer": a_relancer()
    else: liste(a.filtre)


if __name__ == "__main__":
    main()
