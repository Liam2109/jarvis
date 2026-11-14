#!/usr/bin/env python3
"""Tests silencieux de l'agent appels-sid : AUCUN réseau, aucun envoi, fichiers temporaires (rien dans le dépôt).  python agents\\test_appels_sid.py
Écrits AVANT le code (appels-sid.py). Règles de Liam : chaque matin une liste d'au moins 100 entreprises JAMAIS appelées pour Sid, parmi les 21 métiers du catalogue (plombier, électricien,
coiffeur, restaurant, boulangerie, fleuriste, garage et 15 autres ; catalogue étendu le 10 nov. 2026, remplace l'ancienne fourchette 50-60 et l'ancien quatuor restaurant/coiffeur/plombier/électricien) ;
téléphone valide ; ni STOP ni exclus ; créneau réparti sur 8 h - 19 h (jamais le même
pour deux lignes voisines) ; une entreprise non appelée revient en tête de la liste suivante (« A rappeler ») ; une entreprise confirmée appelée est exclue 365 jours (appels-sid-historique.json) ;
CSV docs\\sid\\liste-sid-AAAA-MM-JJ.csv ; commandes preparer / etat / annuler / --a-blanc ; aucun envoi, aucun partage, aucun appel API."""
import contextlib, csv, importlib.util, io, json, os, re, socket, sys, tempfile, urllib.request
from datetime import date
os.environ.setdefault("JARVIS_TEST", "1")
from pathlib import Path
ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))

def _etat_fichier(p):
    """(taille, date de modification) si présent, sinon None : un fichier d'agent réel (état, verrou, journal) peut déjà exister sur le portable serveur où l'agent tourne pour de vrai ;
    les tests ne doivent pas exiger qu'il soit absent, seulement qu'il reste inchangé."""
    if p.exists():
        s = p.stat(); return (s.st_size, s.st_mtime_ns)
    return None
_AVANT_REEL = {n: _etat_fichier(ICI / n) for n in ("appels-sid-etat.json", "appels-sid.verrou", "appels-sid-journal.log", "appels-sid-historique.json")}

def _instantane_dossier(p):
    """Liste triée (nom, taille, date) d'un dossier réel (docs\\sid) : peut déjà contenir de vraies listes si l'agent tourne pour de vrai sur le serveur ;
    les tests, qui écrivent dans un dossier temporaire, ne doivent rien y ajouter, modifier ni supprimer."""
    return sorted((f.name,) + (_etat_fichier(f) or (0, 0)) for f in p.iterdir() if f.is_file()) if p.exists() else []
_AVANT_SID_REEL = _instantane_dossier(ICI.parent / "docs" / "sid")
import prospection as P, suivi as S
spec = importlib.util.spec_from_file_location("appels_sid", ICI / "appels-sid.py"); A = importlib.util.module_from_spec(spec); spec.loader.exec_module(A)
CHERCHER_SITE_WEB_REEL = A.chercher_site_web   # référence vers la vraie implémentation, avant qu'elle soit remplacée plus bas par une doublure (section 31 : test direct du blocage/erreur réseau)

def reseau(*a, **k): raise AssertionError("appel réseau interdit dans les tests")
urllib.request.urlopen = reseau; socket.create_connection = reseau; P.lien_accessible = reseau   # aucune page exemple n'est ouverte : le lien est lu dans liens-metiers.json

tmp = Path(tempfile.mkdtemp(prefix="appels-sid-test-"))
(tmp / "docs").mkdir(); (tmp / "agents").mkdir()
A.ICI, A.RACINE, A.SORTIE = tmp / "agents", tmp, tmp / "docs" / "sid"
A.CONFIG, A.ETAT, A.VERROU, A.ARRET, A.JOURNAL, A.MAPS, A.HISTORIQUE = (tmp / "agents" / "appels-sid-config.json", tmp / "agents" / "appels-sid-etat.json", tmp / "agents" / "appels-sid.verrou",
                                                          tmp / "agents" / "appels-sid.arret", tmp / "agents" / "appels-sid-journal.log", tmp / "prospects_maps.csv", tmp / "agents" / "appels-sid-historique.json")
P.TROUVES, P.DOCS, P.ICI, P.ETAT, S.FICHIER = tmp / "prospection-trouves.csv", tmp / "docs", tmp / "agents", tmp / "agents" / "prospection-etat.json", tmp / "suivi-prospects.csv"
LIENS = {"plombier-chauffagiste": "https://exemple-plombier.example/", "electricien": "https://exemple-electricien.example/", "restaurant": "https://exemple-restaurant.example/",
         "coiffeur": "https://exemple-coiffeur.example/", "fleuriste": "https://exemple-fleuriste.example/", "boulangerie": "https://exemple-boulangerie.example/", "garage": "https://exemple-garage.example/"}
(tmp / "agents" / "liens-metiers.json").write_text(json.dumps(LIENS), encoding="utf-8")


# --- doublures : aucun accès réseau, Google, Discord ni tâche Windows réels -------------------------------------------------------------------------------
import google_sheets as GS
class FauxDrive:
    """Même interface que google_sheets.Drive : dossiers, feuilles, partages gardés en mémoire."""
    def __init__(s, compte="contact.lmsites@gmail.com"): s.dossiers, s.feuilles, s.partages, s.n, s.panne, s.appels, s.compte_reel, s.corbeille, s.mises_en_forme = {}, {}, [], 0, False, 0, compte, set(), []
    def _nouveau(s, p): s.n += 1; return f"{p}{s.n}"
    def _controle(s):
        s.appels += 1
        if s.panne: raise GS.ErreurDrive(503, "panne simulée")
    def compte(s): s._controle(); return s.compte_reel
    def trouver_dossier(s, nom, parent=None): s._controle(); return next((i for i, (n, p) in s.dossiers.items() if n == nom and p == parent and i not in s.corbeille), None)
    def creer_dossier(s, nom, parent=None): s._controle(); i = s._nouveau("D"); s.dossiers[i] = (nom, parent); return i
    def trouver_feuille(s, dossier, titre): s._controle(); return next((i for i, (t, d, _) in s.feuilles.items() if t == titre and d == dossier and i not in s.corbeille), None)
    def lister_feuilles(s, parent): s._controle(); return [(i, t) for i, (t, d, _) in s.feuilles.items() if d == parent and i not in s.corbeille]
    def creer_feuille(s, dossier, titre, contenu): s._controle(); i = s._nouveau("F"); s.feuilles[i] = (titre, dossier, contenu); return i
    def partager(s, dossier, email): s._controle(); s.partages.append((dossier, email))
    def lister_dossiers(s, parent): s._controle(); return [(i, n) for i, (n, p) in s.dossiers.items() if p == parent and i not in s.corbeille]
    def mettre_corbeille(s, id_): s._controle(); s.corbeille.add(id_)
    def lire_feuille_csv(s, id_): s._controle(); return s.feuilles[id_][2]
    def formater_feuille(s, id_, largeurs_px, liste=None): s._controle(); s.mises_en_forme.append((id_, tuple(largeurs_px), liste))
DRIVE = FauxDrive()
ALERTES, EXEC, SOMMEIL = [], [], []
def faux_alerte(texte): ALERTES.append(texte); return True
def faux_executer(cmd): EXEC.append(cmd); return 0, ""
def faux_dormir(s): SOMMEIL.append(s)
A.appel_reseau = reseau; A.alerter_discord = faux_alerte; A.executer = faux_executer; A.dormir = faux_dormir; A.ouvrir_drive = lambda conf: DRIVE
A.PROSPECTION_CONFIG = tmp / "agents" / "prospection-config.json"
A.appel_sirene = lambda dept, naf, page: {"results": []}; A.lire_site = lambda url: None      # SIRENE et les sites publics : jamais de réseau ici (section 14 bis : doublures complètes)
A.chercher_site_web = lambda nom, ville: ""    # vérification d'un site avant d'inscrire une entreprise : aucun résultat par défaut (section 26 : scénarios avec un site trouvé)
A.M.verifier = lambda *a, **k: (True, "")      # la garde « machine active » (machine.py) est testée dans test_machine.py

echecs = 0
def verifier(cond, msg):
    global echecs
    if cond: print("  OK    " + msg)
    else: print("  ECHEC " + msg); echecs += 1

def lancer(*argv):
    """(code, sortie) de A.main(argv) : la sortie standard est capturée."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
        try: code = A.main(list(argv))
        except SystemExit as e: code = e.code if isinstance(e.code, int) else 2
    return code, buf.getvalue()

def tel(i): return f"02 35 {i // 100 % 100:02d} {i % 100:02d} {(i * 7) % 90 + 10:02d}"   # numéros fictifs, distincts, valides
def trouve(nom, metier, ville, t, statut="sans site, téléphone", cp="76000", note="", email=""):
    d = {c: "" for c in P.COLS}; d.update(nom=nom, metier=metier, ville=ville, telephone=t, statut=statut, cp=cp, note_besoin=note, email=email); return d
def suivi(nom, metier, ville, t, statut="à contacter", email=""):
    d = {c: "" for c in S.COLS}; d.update(nom=nom, metier=metier, ville=ville, telephone=t, statut=statut, email=email); return d

def monde(trouves=(), suivis=(), maps=(), listes=None, exclus_mails=(), exclus_cles=(), config=None):
    """Remet tout à zéro dans le dossier temporaire et écrit les faux fichiers sources."""
    for f in (A.ETAT, A.VERROU, A.ARRET, A.JOURNAL, A.HISTORIQUE, P.ETAT): f.unlink(missing_ok=True)
    for f in list((tmp / "docs").glob("liste-appels-*.md")) + (list(A.SORTIE.glob("*")) if A.SORTIE.exists() else []): f.unlink()
    P.ecrire_trouves(list(trouves), P.TROUVES); S.ecrire(list(suivis))
    with open(A.MAPS, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";"); w.writerow(["nom", "metier", "ville", "telephone", "note", "avis", "site"])
        for m in maps: w.writerow([m[0], m[1], m[2], m[3], "", "", ""])
    for jour, cles in (listes or {}).items():   # faux docs\liste-appels-AAAA-MM-JJ.md au format de prospection.py (ligne de tableau à 12 colonnes + <!-- k:clé -->)
        lignes = [f"| {i} <!-- k:{k.replace('|', '~')} --> | n | v | t | m | x |  |  | {c[0]} | {c[1]} | {c[2]} | {c[3]} |" for i, (k, c) in enumerate(cles, 1)]
        (tmp / "docs" / f"liste-appels-{jour}.md").write_text("\n".join(lignes) + "\n", encoding="utf-8")
    (tmp / "agents" / "exclus-emails.json").write_text(json.dumps(list(exclus_mails)), encoding="utf-8")
    if exclus_cles: P.ETAT.write_text(json.dumps({"appels": {"exclus": list(exclus_cles)}}), encoding="utf-8")
    A.CONFIG.write_text(json.dumps(config or {}), encoding="utf-8")
    A.PROSPECTION_CONFIG.write_text(json.dumps({"liste_appels_heure": "08:00", "appels_par_jour": 100, "decouverte_osm": True}), encoding="utf-8")
    DRIVE.__init__(); ALERTES.clear(); EXEC.clear(); SOMMEIL.clear()

def lire_csv(jour):
    f = A.SORTIE / f"liste-sid-{jour}.csv"
    with open(f, encoding="utf-8-sig", newline="") as fh: return list(csv.reader(fh, delimiter=";"))

def gros_monde(n=40):
    """Réserve large : n entreprises pour chacun des sept métiers les plus utilisés dans ces tests (restaurant, coiffeur, plombier, électricien, fleuriste, boulangerie, garage ;
    tous valides depuis le catalogue de 21 métiers du 10 nov. 2026)."""
    t = []
    for i in range(n):
        t.append(trouve(f"Resto Fictif {i}", "restaurant", f"Ville{i % 7}", tel(100 + i), note="carte absente du site" if i == 0 else ""))
        t.append(trouve(f"Coiff Fictif {i}", "coiffeur", f"Ville{i % 7}", tel(300 + i)))
        t.append(trouve(f"Plomb Fictif {i}", "plombier-chauffagiste", f"Ville{i % 7}", tel(500 + i)))
        t.append(trouve(f"Elec Fictif {i}", "électricien", f"Ville{i % 7}", tel(700 + i)))
        t.append(trouve(f"Fleur Fictif {i}", "fleuriste", "Rouen", tel(900 + i))); t.append(trouve(f"Boul Fictif {i}", "boulangerie", "Rouen", tel(1100 + i))); t.append(trouve(f"Gar Fictif {i}", "garage automobile", "Rouen", tel(1300 + i)))
    return t

SEPT = ("restaurant", "coiffeur", "plombier", "electricien", "fleuriste", "boulangerie", "garage")   # les sept métiers que gros_monde() fournit (catalogue de 21, règle du 10 nov. 2026)
# repartition limitée à SEPT : avec le réglage par défaut (poids égal pour les 21 métiers), le quota par métier de choisir() est trop petit (~5) pour que les ~14 lignes d'un même métier
# données par gros_monde() reviennent toutes en « A rappeler » le lendemain (certaines seraient évincées par le quota, remplacées par du frais d'un autre métier) : jamais le cas avec
# seulement 4 métiers (quota large) avant le catalogue du 10 nov. 2026, donc jamais testé ; repartition le restitue ici pour les tests qui dépendent de gros_monde().
REPART_SEPT = lambda: {m: (5 if m in SEPT else 0) for m in A.NOMS}

JOUR = "2026-11-04"; JOUR2 = "2026-11-05"
COLONNES = ["Créneau", "Entreprise", "Métier", "Ville", "Téléphone", "Détail fiche", "Résultat", "Note"]   # tableur « Appels AAAA-MM-JJ » (décision de Liam, 14 nov. 2026)
CR, NOM, MET, VIL, TEL, DET, RES, NOTE = range(8)

print("1. Téléphone valide")
ok = {"02 35 62 41 64": "02 35 62 41 64", "0235624164": "02 35 62 41 64", "+33 2 35 62 41 64": "02 35 62 41 64", "0033235624164": "02 35 62 41 64", "06.12.34.56.78": "06 12 34 56 78", " 07-66-39-19-52 ": "07 66 39 19 52", "09 51 23 45 67": "09 51 23 45 67"}
for brut, attendu in ok.items(): verifier(A.telephone_valide(brut) == attendu, f"« {brut} » -> « {attendu} »")
for mauvais in ("", "   ", "12345", "0235624", "02 35 62 41", "0800 12 34 56", "08 92 12 34 56", "00 00 00 00 00", "06 06 06 06 06 06", "abcdef", "+44 20 7946 0958", "00 12 34 56 78", "11 11 11 11 11", "02 35 62 41 64 / 02 35 62 41 65"):
    verifier(A.telephone_valide(mauvais) == "", f"« {mauvais} » refusé")

print("2. Sélection : métiers, statuts, exclusions, déjà données")
monde(trouves=[
    trouve("Bon Resto", "restaurant", "Rouen", "02 35 11 11 11"), trouve("Bon Coiffeur", "coiffeur", "Rouen", "02 35 22 22 22"),
    trouve("Bon Plombier", "plombier-chauffagiste", "Rouen", "02 35 33 33 33"), trouve("Bon Electricien", "électricien", "Rouen", "02 35 44 44 44"),
    trouve("Une Fleuriste", "fleuriste", "Rouen", "02 35 55 55 55"), trouve("Une Boulangerie", "boulangerie", "Rouen", "02 35 66 66 66"), trouve("Un Garage", "garage automobile", "Rouen", "02 35 77 77 77"),
    trouve("Sans Tel", "restaurant", "Rouen", ""), trouve("Tel Faux", "restaurant", "Rouen", "0800 12 34 56"),
    trouve("Hors Zone", "restaurant", "Rouen", "02 35 88 88 01", statut="hors zone"), trouve("Refus Resto", "restaurant", "Rouen", "02 35 88 88 02", statut="refusé"),
    trouve("Stop Resto", "restaurant", "Rouen", "02 35 88 88 03", statut="STOP"), trouve("Exclu Resto", "restaurant", "Rouen", "02 35 88 88 04", statut="exclu"),
    trouve("Ecarte Resto", "restaurant", "Rouen", "02 35 88 88 05", statut="écarté"), trouve("Prepare Resto", "restaurant", "Rouen", "02 35 88 88 06", statut="préparé"),
    trouve("Liste Resto", "restaurant", "Rouen", "02 35 88 88 07", statut="listé"), trouve("Cp Lointain", "restaurant", "Marseille", "04 91 88 88 08", cp="13001"),
    trouve("Mail Exclu", "restaurant", "Rouen", "02 35 88 88 09", email="stop@example.invalid"), trouve("Cle Exclue", "coiffeur", "Rouen", "02 35 88 88 10"),
    trouve("Deja Appele", "coiffeur", "Rouen", "02 35 88 88 11"), trouve("Deja Rendu A Liam", "plombier-chauffagiste", "Rouen", "02 35 88 88 12"), trouve("Meme Tel", "restaurant", "Rouen", "02 35 11 11 11"),
    trouve("Suivi Stop", "restaurant", "Rouen", "02 35 88 88 13"),
], suivis=[suivi("Suivi A Contacter", "plombier-chauffagiste", "Elbeuf", "06 10 20 30 40"), suivi("Suivi Envoye", "plombier-chauffagiste", "Elbeuf", "06 10 20 30 41", statut="envoyé"),
           suivi("Suivi Repondu", "électricien", "Elbeuf", "06 10 20 30 42", statut="répondu"), suivi("Suivi Stop", "restaurant", "Rouen", "06 10 20 30 43", statut="STOP"),
           suivi("Suivi Sans Tel", "électricien", "Elbeuf", "")],
      maps=[("Maps Elec", "électricien", "Rouen", "07 66 39 19 52"), ("Maps Couvreur", "couvreur", "Rouen", "07 66 39 19 53"), ("Suivi A Contacter", "plombier-chauffagiste", "Elbeuf", "06 10 20 30 40")],
      listes={"2026-11-03": [("deja-appele|rouen", "[x] [ ] [ ] [ ]".split()), ("deja-rendu-a-liam|rouen", "[ ] [ ] [ ] [ ]".split())]},
      exclus_mails=["stop@example.invalid"], exclus_cles=["cle-exclue|rouen"], config={"par_liste": 50})
cles = {c["nom"] for c in A.choisir(A.cfg(), A.etat_lire())}
verifier(cles == {"Bon Resto", "Bon Coiffeur", "Bon Plombier", "Bon Electricien", "Suivi A Contacter", "Maps Elec", "Liste Resto", "Deja Rendu A Liam",
                   "Une Fleuriste", "Une Boulangerie", "Un Garage", "Maps Couvreur"}, f"seuls les bons candidats sont retenus : {sorted(cles)}")
for bon in ("Une Fleuriste", "Une Boulangerie", "Un Garage", "Maps Couvreur"):
    verifier(bon in cles, f"gardé : {bon} (métier du catalogue des 21, règle du 10 nov. 2026)")
for interdit, raison in (("Sans Tel", "sans téléphone"), ("Tel Faux", "téléphone invalide (0800)"), ("Hors Zone", "hors zone"),
                         ("Refus Resto", "refus"), ("Stop Resto", "STOP"), ("Exclu Resto", "exclu"), ("Ecarte Resto", "écarté"), ("Prepare Resto", "déjà préparé pour l'e-mail"), ("Cp Lointain", "code postal hors zone"), ("Mail Exclu", "e-mail dans exclus-emails.json"), ("Cle Exclue", "exclu (état de prospection)"), ("Deja Appele", "déjà appelé (case cochée)"), ("Meme Tel", "même téléphone qu'une autre ligne"), ("Suivi Stop", "STOP du suivi"), ("Suivi Envoye", "déjà contacté par e-mail"),
                         ("Suivi Repondu", "a répondu")):
    verifier(interdit not in cles, f"écarté : {interdit} ({raison})")
verifier(len([c for c in A.choisir(A.cfg(), A.etat_lire()) if c["nom"] == "Suivi A Contacter"]) == 1, "même entreprise présente dans deux fichiers (suivi + maps) : une seule ligne")

for repris in ("Liste Resto", "Deja Rendu A Liam"): verifier(repris in cles, f"reprise : {repris} (listée pour Liam mais jamais appelée)")
print("3. Taille de la liste (100 à 130, règle fixe de Liam du 10 nov. 2026) et mélange des métiers")
monde(trouves=gros_monde(), config={})
ch = A.choisir(A.cfg(), A.etat_lire())
verifier(A.cfg()["par_liste"] == 100 and len(ch) == 100, f"par défaut : 100 lignes au moins (obtenu {len(ch)})")
par = {}
for c in ch: par[c["metier"]] = par.get(c["metier"], 0) + 1
verifier(set(par) == {"restaurant", "coiffeur", "plombier", "electricien", "fleuriste", "boulangerie", "garage"}, f"sept métiers présents (catalogue de 21 métiers, règle du 10 nov. 2026) : {par}")
verifier(all(v >= 8 for v in par.values()), f"mélange raisonnable (au moins 8 par métier) : {par}")
verifier(len({c["cle"] for c in ch}) == len(ch) and len({c["tel"] for c in ch}) == len(ch), "aucune entreprise ni aucun numéro en double")
for demande, attendu in ((30, 100), (150, 130), (100, 100), (130, 130), ("abc", 100)):
    monde(trouves=gros_monde(), config={"par_liste": demande}); verifier(len(A.choisir(A.cfg(), A.etat_lire())) == attendu, f"par_liste = {demande!r} -> {attendu} lignes (bornes 100 à 130)")
monde(trouves=[trouve(f"Resto Seul {i}", "restaurant", "Rouen", tel(100 + i)) for i in range(70)] + [trouve("Un Coiffeur", "coiffeur", "Rouen", tel(900))], config={})
ch = A.choisir(A.cfg(), A.etat_lire())
verifier(len(ch) == 71 and sum(1 for c in ch if c["metier"] == "restaurant") == 70, "un métier en manque, réserve totale sous 100 : tout ce qu'il y a est sorti (pas de liste réduite sans raison)")
monde(trouves=[trouve(f"Resto Seul {i}", "restaurant", "Rouen", tel(100 + i)) for i in range(12)], config={})
verifier(len(A.choisir(A.cfg(), A.etat_lire())) == 12, "réserve trop petite : on sort ce qu'il y a (le rapport le signale)")

print("4. Créneaux : répartis sur 8 h - 19 h, jamais le même pour deux lignes voisines (règle fixe de Liam du 10 nov. 2026, remplace les anciens textes partagés par métier)")
monde(trouves=gros_monde(), config={})
ch = A.choisir(A.cfg(), A.etat_lire()); ordre = [c["metier"] for c in ch]
rang = A.RANG   # ordre de la journée pour les 21 métiers du catalogue (bâtiment, puis commerces, puis restauration) : jamais une table figée qui casserait au prochain métier ajouté
verifier([rang[m] for m in ordre] == sorted(rang[m] for m in ordre), "lignes classées dans l'ordre de la journée : bâtiment, coiffeurs/commerces, restaurants")
def _debut_min(txt):
    h, _, reste = txt.split(" – ")[0].strip().partition(" h")
    return int(h) * 60 + (int(reste.strip()) if reste.strip() else 0)
par_metier = {}
for l in A.lignes_csv(ch)[1:]: par_metier.setdefault(l[MET], []).append(l[CR])
debuts_csv = [_debut_min(l[CR]) for l in A.lignes_csv(ch)[1:]]
verifier(debuts_csv == sorted(debuts_csv), "tableur : lignes triées par créneau (heure de début croissante)")
verifier(all(len(set(v)) == len(v) for v in par_metier.values()), f"jamais le même créneau pour deux lignes du même métier : {[(k, len(v) - len(set(v))) for k, v in par_metier.items() if len(set(v)) != len(v)]}")
tous_debuts = [_debut_min(c) for v in par_metier.values() for c in v]
verifier(all(480 <= d < 1140 for d in tous_debuts), "tous les créneaux commencent entre 8 h et 19 h")
verifier(all(not (720 <= _debut_min(c) < 840) for c in par_metier.get("Coiffeur", [])), "coiffeurs : jamais entre 12 h et 14 h")
verifier(bool(par_metier.get("Coiffeur")) and min(_debut_min(c) for c in par_metier["Coiffeur"]) < 720 and max(_debut_min(c) for c in par_metier["Coiffeur"]) >= 840, "coiffeurs : la réserve couvre bien le matin ET l'après-midi")
verifier(all(870 <= _debut_min(c) < 1050 for c in par_metier.get("Restaurant", [])), "restaurants : seulement entre 14 h 30 et 17 h 30")
verifier(all(_debut_min(c) < 540 or _debut_min(c) >= 1020 for m in ("Plombier-chauffagiste", "Électricien", "Garagiste") for c in par_metier.get(m, [])), "artisans du bâtiment : avant 9 h ou à partir de 17 h")

print("5. preparer : CSV, colonnes, constat, liens")
monde(trouves=gros_monde(), config={})
code, sortie = lancer("preparer", "--jour", JOUR)
verifier(code == 0, f"preparer : code 0 ({sortie.strip()[:120]})")
f = A.SORTIE / f"liste-sid-{JOUR}.csv"
verifier(f.exists(), "docs\\sid\\liste-sid-AAAA-MM-JJ.csv écrit")
brut = f.read_bytes()
verifier(brut.startswith(b"\xef\xbb\xbf") and b";" in brut.splitlines()[0], "UTF-8 avec BOM, séparateur « ; » (import Google Sheets / Excel français)")
lignes = lire_csv(JOUR)
verifier(lignes[0] == COLONNES, f"colonnes : {lignes[0]}")
corps = lignes[1:]
verifier(len(corps) == 100 and [_debut_min(l[CR]) for l in corps] == sorted(_debut_min(l[CR]) for l in corps), "100 lignes triées par créneau (règle fixe de Liam du 10 nov. 2026 ; tri du 14 nov. 2026)")
verifier(all(len(l) == len(COLONNES) for l in corps), "toutes les lignes ont toutes les colonnes")
verifier(all(l[RES] == l[NOTE] == "" for l in corps), "Résultat / Note : vides (Sid les remplit ; pas de colonne STOP)")
verifier(all(re.fullmatch(r"0\d( \d\d){4}", l[TEL]) for l in corps), "téléphones au format « 02 35 62 41 64 »")
verifier({l[MET] for l in corps} == {"Restaurant", "Coiffeur", "Plombier-chauffagiste", "Électricien", "Fleuriste", "Boulanger", "Garagiste"}, "métiers affichés en clair (catalogue de 21 métiers, règle du 10 nov. 2026)")
verifier(all(l[CR] for l in corps), "créneau renseigné pour chaque ligne")
resto0 = [l for l in corps if l[1] == "Resto Fictif 0"][0]; autre = [l for l in corps if l[1] == "Coiff Fictif 3"]
verifier(resto0[DET] == "carte absente du site" and all(l[DET] == A.CONSTAT_NEUTRE for l in corps if l[1] != "Resto Fictif 0"), "constat : celui vérifié (note_besoin) sinon le texte neutre, jamais une affirmation inventée")
verifier("liste-sid-" + JOUR in sortie and "100" in sortie, "la sortie dit le fichier et le nombre de lignes")
verifier(not any(f.name.endswith(".md") for f in A.SORTIE.iterdir()), "un seul fichier par liste (CSV)")

print("6. Formules de tableur neutralisées")
monde(trouves=[trouve("=SOMME(1+1) Resto", "restaurant", "Rouen", tel(100)), trouve("+Plomb @x", "plombier-chauffagiste", "Rouen", tel(500)), trouve("Nom; avec \"guillemets\"\net saut", "coiffeur", "Rouen", tel(300))], config={})
code, _ = lancer("preparer", "--jour", JOUR); l = lire_csv(JOUR)
noms = [x[1] for x in l[1:]]
verifier(code == 0 and all(not n.startswith(("=", "+", "-", "@")) for n in noms), f"nom commençant par = + - @ neutralisé : {noms}")
verifier(any("avec" in n and "\n" not in n for n in noms), "point-virgule, guillemets et saut de ligne : ligne CSV intacte")
verifier(all(len(x) == len(COLONNES) for x in l), "aucune colonne décalée")

print("7. État : A rappeler si pas appelée, exclue 365 jours si confirmée appelée (règles du 10 nov. 2026)")
monde(trouves=gros_monde(60), config={})   # réserve large (420, 7 métiers x 60) : la liste du lendemain doit pouvoir sortir 100 entreprises fraîches après que celles de JOUR soient confirmées appelées
lancer("preparer", "--jour", JOUR)
etat = json.loads(A.ETAT.read_text(encoding="utf-8"))
verifier(len(etat["sorties"]) == 100 and etat["listes"][JOUR]["nombre"] == 100, "appels-sid-etat.json : 100 entreprises marquées, liste du jour notée")
verifier("tel" not in json.dumps(etat) and not re.search(r"\d\d \d\d \d\d \d\d", json.dumps(etat)), "l'état ne contient aucun numéro de téléphone")
avant = A.ETAT.read_bytes(); csv1 = (A.SORTIE / f"liste-sid-{JOUR}.csv").read_bytes()
code, sortie = lancer("preparer", "--jour", JOUR)
verifier(code == 2 and "déjà" in sortie and A.ETAT.read_bytes() == avant and (A.SORTIE / f"liste-sid-{JOUR}.csv").read_bytes() == csv1, "deuxième preparer le même jour : refusé, rien écrasé, rien marqué en plus")
# scénario A : aucune case « Appelé » cochée sur la liste de JOUR -> elle revient à l'identique en tête de la liste du lendemain (« A rappeler »)
code, sortie = lancer("preparer", "--jour", JOUR2)
n1 = {l[1] for l in lire_csv(JOUR)[1:]}; n2 = {l[1] for l in lire_csv(JOUR2)[1:]}
verifier(code == 0 and "100 ligne(s) non appelée(s)" in sortie and n1 == n2, f"aucune case « Appelé » cochée : la liste revient à l'identique le lendemain, « A rappeler » ({sortie.strip().splitlines()[0]})")
verifier(len(json.loads(A.ETAT.read_text(encoding="utf-8"))["sorties"]) == 100, "état : toujours les 100 mêmes entreprises (reprises, pas doublées)")
# scénario B (monde propre, indépendant du scénario A) : la case « Appelé » de JOUR est cochée -> plus aucune reprise, l'historique (365 jours) retient ces 100 entreprises
monde(trouves=gros_monde(60), config={})
lancer("preparer", "--jour", JOUR)
rows = lire_csv(JOUR)
for l in rows[1:]: l[RES] = "Pas de réponse"   # simule ce que Sid aurait choisi dans la feuille Google
with open(A.SORTIE / f"liste-sid-{JOUR}.csv", "w", encoding="utf-8-sig", newline="") as fh: csv.writer(fh, delimiter=";").writerows(rows)
code, sortie = lancer("preparer", "--jour", JOUR2)
n1 = {l[1] for l in lire_csv(JOUR)[1:]}; n2 = {l[1] for l in lire_csv(JOUR2)[1:]}
verifier(code == 0 and "non appelée" not in sortie and not (n1 & n2), "case « Appelé » cochée : plus aucune reprise, le lendemain tire 100 nouvelles entreprises")
tel1 = {l[TEL] for l in lire_csv(JOUR)[1:]}; tel2 = {l[TEL] for l in lire_csv(JOUR2)[1:]}
verifier(not (tel1 & tel2), "ni le même numéro")
hist = json.loads(A.HISTORIQUE.read_text(encoding="utf-8"))
verifier(len(hist) == 200 and all(v == JOUR for v in hist.values()), f"historique : les 100 clés et les 100 numéros de JOUR notés avec sa date ({len(hist)} entrée(s))")
etat = json.loads(A.ETAT.read_text(encoding="utf-8")); verifier(len(etat["sorties"]) == 200, "200 entreprises marquées après deux jours (confirmées appelées, aucune reprise cette fois)")
lancer("preparer", "--jour", "2026-11-06"); code, sortie = lancer("preparer", "--jour", "2026-11-07")
verifier(code in (0, 2), "réserve épuisée : pas de plantage")
monde(trouves=[], config={}); code, sortie = lancer("preparer", "--jour", JOUR)
verifier(code == 2 and "aucune" in sortie.lower() and not (A.SORTIE / f"liste-sid-{JOUR}.csv").exists() and not A.ETAT.exists(), "aucun candidat : message clair, aucun fichier, aucun état")

print("8. --a-blanc : affiche sans rien écrire")
monde(trouves=gros_monde(), config={})
code, sortie = lancer("preparer", "--jour", JOUR, "--a-blanc")
verifier(code == 0 and "à blanc" in sortie.lower() and "Resto Fictif" in sortie, "affiche la liste")
verifier(not A.SORTIE.exists() or not list(A.SORTIE.iterdir()), "aucun CSV écrit")
verifier(not A.ETAT.exists() and not A.JOURNAL.exists() and not A.VERROU.exists(), "ni état, ni journal, ni verrou")
code, _ = lancer("preparer", "--jour", JOUR); verifier(code == 0 and len(lire_csv(JOUR)) == 101, "après un à blanc, le vrai preparer sort bien les mêmes entreprises (rien n'a été consommé)")
verifier(lancer("etat", "--a-blanc")[0] == 0, "etat accepte aussi --a-blanc")

print("9. etat : compte restant")
monde(trouves=gros_monde(40), config={})
code, sortie = lancer("etat"); verifier(code == 0 and "aucune liste" in sortie.lower() and "280" in sortie, f"avant toute liste : réserve = 280 (7 métiers x 40, catalogue du 10 nov. 2026) : {sortie.strip().splitlines()[:3]}")
lancer("preparer", "--jour", JOUR)
code, sortie = lancer("etat")
verifier("180" in sortie and JOUR in sortie and "100" in sortie, "après une liste de 100 : reste 180, liste du jour citée")
verifier(re.search(r"jour", sortie.lower()) is not None and "0" in sortie, "nombre de jours de réserve indiqué")
verifier(not re.search(r"\d\d \d\d \d\d \d\d \d\d", sortie), "etat n'affiche aucun numéro de téléphone")
verifier(re.search(r"restaurant\D+\d+", sortie, re.I) is not None, "reste par métier")

print("10. annuler : libère une liste non utilisée")
monde(trouves=gros_monde(), config={})
lancer("preparer", "--jour", JOUR); code1 = lire_csv(JOUR)
code, sortie = lancer("annuler", JOUR, "--a-blanc")
verifier(code == 0 and "à blanc" in sortie.lower() and (A.SORTIE / f"liste-sid-{JOUR}.csv").exists() and len(json.loads(A.ETAT.read_text(encoding="utf-8"))["sorties"]) == 100, "annuler --a-blanc : rien changé")
code, sortie = lancer("annuler", JOUR)
etat = json.loads(A.ETAT.read_text(encoding="utf-8"))
verifier(code == 0 and etat["sorties"] == {} and JOUR not in etat["listes"], "liste non utilisée : les 100 entreprises sont libérées")
verifier(not (A.SORTIE / f"liste-sid-{JOUR}.csv").exists() and (A.SORTIE / f"liste-sid-{JOUR}.annulee.csv").exists(), "le CSV n'est pas supprimé : renommé .annulee.csv")
code, _ = lancer("preparer", "--jour", JOUR); verifier(code == 0 and lire_csv(JOUR) == code1, "preparer à nouveau le même jour : mêmes entreprises (elles sont libres)")
verifier(lancer("annuler", "2026-01-01")[0] == 2, "annuler une date sans liste : erreur, rien changé")
verifier(lancer("annuler")[0] == 0 and not (A.SORTIE / f"liste-sid-{JOUR}.csv").exists(), "annuler sans date : la liste la plus récente")
lancer("preparer", "--jour", JOUR)
rows = lire_csv(JOUR); rows[3][RES] = "Non catégorique"; rows[5][NOTE] = "rappeler jeudi"
with open(A.SORTIE / f"liste-sid-{JOUR}.csv", "w", encoding="utf-8-sig", newline="") as fh: csv.writer(fh, delimiter=";").writerows(rows)
code, sortie = lancer("annuler", JOUR)
verifier(code == 2 and "utilisée" in sortie and (A.SORTIE / f"liste-sid-{JOUR}.csv").exists() and len(json.loads(A.ETAT.read_text(encoding="utf-8"))["sorties"]) == 100, "liste déjà commencée (case ou remarque remplie) : annulation refusée")
code, sortie = lancer("annuler", JOUR, "--force")
verifier(code == 0 and json.loads(A.ETAT.read_text(encoding="utf-8"))["sorties"] == {}, "--force : libère quand même")
lancer("preparer", "--jour", JOUR); (A.SORTIE / f"liste-sid-{JOUR}.csv").unlink()
verifier(lancer("annuler", JOUR)[0] == 0 and json.loads(A.ETAT.read_text(encoding="utf-8"))["sorties"] == {}, "fichier CSV disparu : l'état est quand même libéré")

print("11. Verrou, arrêt de secours, erreurs")
monde(trouves=gros_monde(), config={})
A.VERROU.write_text(str(os.getpid()), encoding="utf-8")
code, sortie = lancer("preparer", "--jour", JOUR)
verifier(code == 2 and "verrou" in sortie.lower() and not A.ETAT.exists(), "verrou tenu par un processus vivant : refusé, rien écrit")
A.VERROU.write_text("99999999", encoding="utf-8")
code, _ = lancer("preparer", "--jour", JOUR); verifier(code == 0 and not A.VERROU.exists(), "verrou d'un processus mort : repris puis libéré")
monde(trouves=gros_monde(), config={}); A.ARRET.write_text("stop", encoding="utf-8")
code, sortie = lancer("preparer", "--jour", JOUR)
verifier(code == 2 and "arrêt" in sortie.lower() and not A.ETAT.exists() and not (A.SORTIE / f"liste-sid-{JOUR}.csv").exists(), "fichier d'arrêt de secours : rien n'est généré")
monde(trouves=gros_monde(), config={}); A.ETAT.write_text("{pas du json", encoding="utf-8")
code, sortie = lancer("preparer", "--jour", JOUR)
verifier(code == 2 and A.ETAT.read_text(encoding="utf-8") == "{pas du json" and not A.VERROU.exists(), "état illisible : arrêt avec message, état NON écrasé, verrou libéré")
monde(trouves=gros_monde(), config={}); verifier(lancer("preparer", "--jour", "pas-une-date")[0] == 2, "date invalide : erreur")
verifier(lancer("n_importe_quoi")[0] == 2, "commande inconnue : erreur")
verifier(not A.VERROU.exists(), "aucun verrou laissé")

print("12. Journal, secrets, aucun envoi")
monde(trouves=gros_monde(), config={}); lancer("preparer", "--jour", JOUR)
j = A.JOURNAL.read_text(encoding="utf-8")
verifier(JOUR in j and "100" in j, "journal : une ligne par action")
verifier(not re.search(r"\d\d \d\d \d\d \d\d \d\d|@", j) and "Fictif" not in j, "journal : aucun numéro, e-mail ni nom d'entreprise")
src = (ICI / "appels-sid.py").read_text(encoding="utf-8")
verifier(not re.search(r"smtplib|send_message|messages\(\)\.send|gmail_api|stripe|webbrowser|os\.system|shell=True", src, re.I), "appels-sid.py : aucun envoi d'e-mail ni de message à une entreprise, aucun Stripe, pas de shell")
verifier(not re.search(r"print\([^)]*(jeton|token|password|mot de passe)", src, re.I), "aucun jeton ni mot de passe affiché")
cfg_reel = json.loads((ICI / "appels-sid-config.json").read_text(encoding="utf-8-sig"))
verifier(cfg_reel.get("envoi_automatique") is False, "appels-sid-config.json : envoi_automatique = false (fichier versionné ; activation réelle par machine dans appels-sid-config.local.json, ignoré par git)")
verifier(not cfg_reel.get("partager_avec"), "appels-sid-config.json : aucun partager_avec dans le fichier versionné (l'adresse vit dans appels-sid-config.local.json)")
verifier(cfg_reel.get("jours_appel") == ["lundi", "mardi", "mercredi", "jeudi", "vendredi"], "appels-sid-config.json : jours_appel = lundi à vendredi (14 nov. 2026)")
verifier(cfg_reel.get("par_liste") == 100 and cfg_reel.get("jours_sans_rappel") == 365, "appels-sid-config.json : règles fixes du 10 nov. 2026 écrites (par_liste 100, jours_sans_rappel 365)")
verifier(all(_etat_fichier(ICI / n) == _AVANT_REEL[n] for n in ("appels-sid-etat.json", "appels-sid.verrou", "appels-sid-journal.log", "appels-sid-historique.json")), "les tests n'ont rien écrit dans le dépôt (un fichier d'agent déjà présent, car l'agent tourne pour de vrai sur le serveur, reste inchangé)")
verifier(_instantane_dossier(ICI.parent / "docs" / "sid") == _AVANT_SID_REEL, "docs\\sid du dépôt : rien ajouté, modifié ni supprimé par les tests (une vraie liste de l'agent, s'il tourne sur le serveur, reste inchangée)")

print("13. Liste de Liam redirigée vers Sid (jamais appliquée sans ordre)")
monde(trouves=gros_monde(), config={})
avant = A.PROSPECTION_CONFIG.read_text(encoding="utf-8")
verifier(lancer("rediriger-liste", "--a-blanc")[0] == 0 and A.PROSPECTION_CONFIG.read_text(encoding="utf-8") == avant, "rediriger-liste --a-blanc : rien changé")
verifier("liste de liam : active" in lancer("etat")[1].lower(), "etat : la liste de Liam est encore active tant qu'on n'a pas redirigé")
code, sortie = lancer("rediriger-liste"); pc = A.M.lire_fusionnee(A.PROSPECTION_CONFIG)      # réglage écrit dans prospection-config.local.json
verifier(code == 0 and pc["liste_appels_heure"] == "99:99" and pc["appels_par_jour"] == 100 and pc["decouverte_osm"] is True, "rediriger-liste : liste_appels_heure = 99:99, le reste de prospection-config.json intact")
verifier(json.loads(A.ETAT.read_text(encoding="utf-8"))["liste_liam"]["ancienne"] == "08:00", "l'ancienne heure est notée dans l'état")
lancer("rediriger-liste"); verifier(json.loads(A.ETAT.read_text(encoding="utf-8"))["liste_liam"]["ancienne"] == "08:00", "rediriger deux fois : l'ancienne heure n'est pas écrasée")
verifier("redirig" in lancer("etat")[1].lower(), "etat : liste de Liam redirigée vers Sid")
verifier(json.loads(A.PROSPECTION_CONFIG.read_text(encoding="utf-8"))["liste_appels_heure"] == "08:00" and A.M.chemin_local(A.PROSPECTION_CONFIG).exists(), "rediriger-liste : le fichier par défaut (versionné) n'a pas bougé, le réglage est dans le fichier LOCAL")
conf_p = {**P.DEFAUT, **A.M.lire_fusionnee(A.PROSPECTION_CONFIG)}
class Matin:   # « 10 h à Paris » : bien après 08:00, donc la liste de Liam serait écrite et postée si rien n'était changé
    def strftime(self, f): return "10:00"
appels_discord = []
r = P.cmd_liste_matin(conf_p, api=lambda *a, **k: appels_discord.append(a) or {"id": "1"}, force=False, paris=Matin())
verifier(r == 0 and not appels_discord and not list((tmp / "docs").glob("liste-appels-*.md")), "prospection.cmd_liste_matin à 10 h : ne produit aucune liste, ne poste rien sur Discord")
verifier(lancer("rendre-liste")[0] == 0 and A.M.lire_fusionnee(A.PROSPECTION_CONFIG)["liste_appels_heure"] == "08:00", "rendre-liste : l'heure d'origine est restaurée")
A.PROSPECTION_CONFIG.unlink(); code, sortie = lancer("rediriger-liste"); verifier(code == 2 and "prospection-config.json" in sortie, "prospection-config.json absent : erreur claire, rien créé")
psrc = (ICI / "prospection.py").read_text(encoding="utf-8")
verifier(psrc.count('< conf["liste_appels_heure"]') >= 2, "prospection.py : les deux déclencheurs de la liste comparent l'heure à liste_appels_heure (un réglage suffit, le code de la prospection n'est pas modifié)")

print("14. Sourcing : numéros gratuits (OpenStreetMap), aucune API payante")
TYPE_REQ = re.compile(r'"(?:craft|shop|amenity|office|beauty)"="(\w+)"')   # catalogue de 21 métiers (10 nov. 2026) : taxi (office=taxi) et onglerie (beauty=nails) ajoutent deux catégories OSM
class FauxOverpass:
    """Faux Overpass : `fixes` = réponses imposées ; sinon `offre[type]` nouvelles fiches (téléphone, sans site) par requête. Garde les requêtes."""
    def __init__(s): s.requetes, s.offre, s.n, s.panne, s.fixes = [], {}, 0, False, []
    def __call__(s, requete):
        s.requetes.append(requete)
        if s.panne: raise OSError("panne simulée")
        if s.fixes: return {"elements": s.fixes.pop(0)}
        lab = TYPE_REQ.search(requete).group(1); out = []
        for _ in range(s.offre.get(lab, 0)):
            s.n += 1; tag = {"name": f"Nouveau {lab} {s.n}", "addr:city": "Rouen", "addr:postcode": "76000", "phone": tel(5000 + s.n)}
            tag.update({"craft": lab} if lab in ("electrician", "plumber") else {"shop": lab} if lab == "hairdresser" else {"amenity": lab})
            out.append({"type": "node", "id": 9000 + s.n, "lat": 49.44, "lon": 1.09, "tags": tag})
        return {"elements": out}
def el(i, **t):
    base = {"name": f"Fiche {i}", "addr:city": "Rouen", "addr:postcode": "76000", "phone": tel(6000 + i), "craft": "plumber"}; base.update(t)
    return {"type": "node", "id": 7000 + i, "lat": 49.44, "lon": 1.09, "tags": base}
def lot_mixte():
    return [el(1), el(2, phone=""), el(3, website="https://exemple.invalid"), el(4, phone="0800 12 34 56"), el(5, **{"addr:postcode": "13001", "addr:city": "Marseille"}), el(6, name=""), el(7, name="Deja Connue"),
            el(8, name="Suivi Connu"), el(9, name="Liste Connue"), el(10, name="Cle Exclue"), el(11, phone="02 35 99 99 99"), el(12, **{"contact:phone": "+33 2 35 77 00 12", "phone": ""}), el(1)]
FO = FauxOverpass(); A.appel_reseau = FO
monde(trouves=[trouve("Deja Connue", "plombier-chauffagiste", "Rouen", "02 35 99 99 99"), trouve("Resto Ancien", "restaurant", "Rouen", "02 35 98 98 98", statut="préparé", email="x@example.invalid")],
      suivis=[suivi("Suivi Connu", "plombier-chauffagiste", "Rouen", "06 10 11 12 13")], listes={"2026-11-03": [("liste-connue|rouen", "[ ] [ ] [ ] [ ]".split())]}, exclus_cles=["cle-exclue|rouen"], config={"sourcing_requetes_max": 1})
FO.__init__(); FO.fixes = [lot_mixte()]
trouves_avant = P.lire_trouves(); etat_p_avant = P.ETAT.read_text(encoding="utf-8")
code, sortie = lancer("sourcer", "--a-blanc", "--jour", JOUR)
verifier(code == 0 and "à blanc" in sortie.lower() and P.lire_trouves() == trouves_avant and not A.ETAT.exists() and not A.JOURNAL.exists(), "sourcer --a-blanc : affiche, n'écrit ni fichier de prospection, ni état, ni journal")
FO.__init__(); FO.fixes = [lot_mixte()]
code, sortie = lancer("sourcer", "--jour", JOUR)
apres = P.lire_trouves(); nouveaux = [l for l in apres if l not in trouves_avant]
verifier(code == 0 and len(apres) == len(trouves_avant) + len(nouveaux) and all(l in apres for l in trouves_avant), "sourcer : les anciennes lignes de prospection-trouves.csv sont intactes")
verifier(sorted(l["nom"] for l in nouveaux) == ["Fiche 1", "Fiche 12"], f"seules les fiches valides sont ajoutées (téléphone, sans site, en zone, nom, sans doublon) : {[l['nom'] for l in nouveaux]}")
verifier(all(l["statut"] == "sans site, téléphone" and l["metier"] == "plombier-chauffagiste" and l["source"].startswith("OpenStreetMap") and l["date_collecte"] == JOUR and l["telephone"] for l in nouveaux), "lignes au format de la prospection (statut, métier, source OpenStreetMap, date)")
verifier({l["telephone"] for l in nouveaux} == {tel(6001), "02 35 77 00 12"}, "téléphone normalisé (+33 accepté, tag contact:phone lu)")
verifier(P.ETAT.read_text(encoding="utf-8") == etat_p_avant and not list(tmp.glob("*.tmp")), "prospection-etat.json non touché, aucun fichier temporaire laissé")
verifier(len(FO.requetes) == 1 and "[out:json]" in FO.requetes[0], "une requête Overpass (sourcing_requetes_max = 1)")
verifier('"craft"="plumber"' in FO.requetes[0] and "phone" in FO.requetes[0] and "mobile" in FO.requetes[0] and "(around:" not in FO.requetes[0] and '"ref:INSEE"="76"' in FO.requetes[0] and "(area.a)" in FO.requetes[0], "requête : plombiers, fiches avec téléphone seulement, relation OpenStreetMap du département 76 (plus de cercle autour de Rouen)")
verifier("places.googleapis" not in src and "GOOGLE_PLACES" not in src and "api_key" not in src.lower(), "aucune API payante (Google Places non utilisé), aucune clé")
j = A.JOURNAL.read_text(encoding="utf-8")
verifier("sourcer" in j and not re.search(r"\d\d \d\d \d\d \d\d \d\d|Fiche|@", j), "journal : nombres seulement, aucune donnée personnelle")
etat = json.loads(A.ETAT.read_text(encoding="utf-8")); verifier(len(etat["sourcing"]["faits"]) == 1 and JOUR in json.dumps(etat["sourcing"]), "état : requête faite notée avec sa date")
monde(trouves=[], config={"sourcing_requetes_max": 1, "avec_site": True}); FO.__init__(); FO.fixes = [[el(1), el(3, website="https://exemple.invalid/")]]
lancer("sourcer", "--jour", JOUR); avs = {l["nom"]: l for l in P.lire_trouves()}
verifier(set(avs) == {"Fiche 1", "Fiche 3"} and avs["Fiche 3"]["statut"] == "téléphone seulement" and avs["Fiche 3"]["site_actuel"] == "https://exemple.invalid/" and avs["Fiche 1"]["statut"] == "sans site, téléphone", "avec_site=true : les fiches avec site sont gardées (statut « téléphone seulement »), jamais jugées ni ouvertes")
monde(trouves=[], config={"sourcing_requetes_max": 1}); FO.__init__(); FO.fixes = [[el(1), el(3, website="https://exemple.invalid/")]]; lancer("sourcer", "--jour", JOUR)
verifier([l["nom"] for l in P.lire_trouves()] == ["Fiche 1"], "avec_site=false (défaut) : une fiche avec site n'est pas ajoutée")
# mémoire des requêtes : deux jours de suite, puis requête vieille de plus de 30 jours
monde(trouves=[trouve("Deja Connue", "plombier-chauffagiste", "Rouen", "02 35 99 99 99")], config={"sourcing_requetes_max": 1}); FO.__init__(); FO.fixes = [[el(1)]]; lancer("sourcer", "--jour", JOUR)
FO.fixes = [[]]; lancer("sourcer", "--jour", JOUR2); verifier(len(FO.requetes) == 2 and FO.requetes[1] != FO.requetes[0], "le lendemain : une autre zone ou un autre métier (jamais la même requête)")
etat = json.loads(A.ETAT.read_text(encoding="utf-8")); etat["sourcing"]["faits"] = {k: "2026-09-01" for k in etat["sourcing"]["faits"]}; A.ETAT.write_text(json.dumps(etat), encoding="utf-8")
FO.fixes = [[]]; n0 = len(FO.requetes); lancer("sourcer", "--jour", JOUR2)
verifier(len(FO.requetes) == n0 + 1 and FO.requetes[-1] == FO.requetes[0], "requête vieille de plus de 30 jours : refaite (les fiches OpenStreetMap évoluent)")
# rythme et priorités
monde(trouves=[], config={"sourcing_requetes_max": 6, "pause_overpass_s": 15, "cible_reserve": 220}); FO.__init__()
lancer("sourcer", "--jour", JOUR)
ordre = [TYPE_REQ.search(r).group(1) for r in FO.requetes]
verifier(len(FO.requetes) == 6 and ordre[:2] == ["plumber", "electrician"], f"6 requêtes au plus par passage, plombiers puis électriciens d'abord : {ordre}")
verifier([s for s in SOMMEIL if s >= 15] == [15] * 5, f"pause de 15 s entre deux requêtes Overpass (jamais avant la première) : {SOMMEIL}")
monde(trouves=[trouve(f"Resto Plein {i}", "restaurant", "Rouen", tel(100 + i)) for i in range(120)] + [trouve(f"Coiff Plein {i}", "coiffeur", "Rouen", tel(300 + i)) for i in range(60)], config={"sourcing_requetes_max": 6, "cible_reserve": 220})
FO.__init__(); lancer("sourcer", "--jour", JOUR); ordre = [TYPE_REQ.search(r).group(1) for r in FO.requetes]
verifier(ordre and "restaurant" not in ordre and "hairdresser" not in ordre and ordre[0] == "plumber", f"métiers déjà assez fournis : pas de requête inutile ({ordre})")
monde(trouves=gros_monde(80), config={"cible_reserve": 220, "repartition": REPART_SEPT()}); FO.__init__(); lancer("sourcer", "--jour", JOUR)
verifier(FO.requetes == [], "réserve déjà au niveau de la cible (pour les sept métiers pesés ici) : aucune requête")
# panne
monde(trouves=[], config={}); FO.__init__(); FO.panne = True; avant_t = P.lire_trouves()
code, sortie = lancer("sourcer", "--jour", JOUR)
verifier(code == 2 and "échec" in sortie.lower() and P.lire_trouves() == avant_t, "panne réseau : message, rien écrit dans la prospection")
verifier(len(ALERTES) == 0, "simulation (envoi_automatique=false) : l'alerte n'est pas postée sur Discord")
j = A.JOURNAL.read_text(encoding="utf-8"); verifier("alerte" in j and "OSError" in j and "panne simulée" not in j, "mais elle est journalisée (type d'erreur seulement)")
monde(trouves=[], config={"envoi_automatique": True}); FO.__init__(); FO.panne = True
lancer("sourcer", "--jour", JOUR); lancer("sourcer", "--jour", JOUR)
verifier(len(ALERTES) == 1 and "sourcing" in ALERTES[0].lower() and not re.search(r"\d\d \d\d \d\d|@", ALERTES[0]), "envoi_automatique=true : une seule alerte Discord par jour, sans donnée personnelle")
lancer("sourcer", "--jour", JOUR2); verifier(len(ALERTES) == 2, "nouvelle alerte le lendemain si la panne continue")
A.appel_reseau = reseau

print("14 bis. Normandie (14, 27, 50, 61, 76) : OpenStreetMap par département, SIRENE, réserve par département")
A.appel_reseau = FO      # faux Overpass de la section 14 (la section se termine par le retour au réseau interdit)
EVAL0 = A.evaluer_site
verifier("rayon_osm_m" not in A.DEFAUT and "rayon_osm_m" not in A.cfg() and A.cfg()["departements"] == ["76", "27", "14", "50", "61"] and A.cfg()["zone"] == "Normandie", "rayon_osm_m (40 km) remplacé par la zone Normandie : cinq départements")
monde(trouves=[], config={"departements": ["27", "99", "76"]}); verifier(A.cfg()["departements"] == ["76", "27"], "départements du réglage : seuls ceux de Normandie sont gardés, dans l'ordre du plus proche de Rouen")
monde(trouves=[], config={"departements": ["75"]}); verifier(A.cfg()["departements"] == ["76", "27", "14", "50", "61"], "réglage sans département normand : retour à toute la Normandie")
# la zone d'acceptation : Normandie seulement (vagues de la prospection non utilisées pour cela)
monde(trouves=[trouve("Resto 76", "restaurant", "Rouen", "02 35 10 00 01", cp="76000"), trouve("Resto 27", "restaurant", "Évreux", "02 32 10 00 02", cp="27000"), trouve("Resto 14", "restaurant", "Caen", "02 31 10 00 03", cp="14000"),
               trouve("Resto 50", "restaurant", "Saint-Lô", "02 33 10 00 04", cp="50000"), trouve("Resto 61", "restaurant", "Alençon", "02 33 10 00 05", cp="61000"), trouve("Resto 75", "restaurant", "Paris", "01 40 10 00 06", cp="75001"),
               trouve("Resto 60", "restaurant", "Beauvais", "03 44 10 00 07", cp="60000"), trouve("Resto 28", "restaurant", "Chartres", "02 37 10 00 08", cp="28000"), trouve("Resto 35", "restaurant", "Rennes", "02 99 10 00 09", cp="35000")])
noms = {c["nom"] for c in A.candidats(A.etat_lire())}
verifier(noms == {"Resto 76", "Resto 27", "Resto 14", "Resto 50", "Resto 61"}, f"Calvados, Manche et Orne acceptés avec l'Eure et la Seine-Maritime ; Paris, Oise, Eure-et-Loir, Ille-et-Vilaine refusés : {sorted(noms)}")
monde(trouves=[trouve("Resto 76", "restaurant", "Rouen", "02 35 10 00 01", cp="76000"), trouve("Resto 14", "restaurant", "Caen", "02 31 10 00 03", cp="14000")], config={"departements": ["76"]})
A.cfg(); verifier({c["nom"] for c in A.candidats(A.etat_lire())} == {"Resto 76"}, "departements = [76] : seule la Seine-Maritime est acceptée")

# une requête Overpass par département et par métier (21 métiers, catalogue du 10 nov. 2026) : avec le plafond fixe de sourcing_requetes_max (30 au plus, cfg() le bride),
# une seule Seine-Maritime (21 métiers) ne suffit même plus à épuiser le budget en une seule série : le passage couvre 76 en entier puis commence 27, jamais les 5 départements d'un coup.
NM = len(A.PRIORITE)   # 21
monde(trouves=[], config={"sourcing_requetes_max": 30, "sirene_actif": False, "cible_reserve": 2000}); FO.__init__(); lancer("sourcer", "--jour", JOUR)
deps_req = [re.search(r'"ref:INSEE"="(\d\d)"', r).group(1) for r in FO.requetes]; types_req = [TYPE_REQ.search(r).group(1) for r in FO.requetes]
verifier(len(FO.requetes) == 30 and deps_req[:NM] == ["76"] * NM and deps_req[NM:] == ["27"] * (30 - NM), f"30 requêtes (plafond) : Seine-Maritime épuisée (21 métiers) puis l'Eure commencée (9) : {sorted(set(deps_req))}")
verifier(all("(around:" not in r and "(area.a)" in r and 'area["boundary"="administrative"]["ref:INSEE"=' in r for r in FO.requetes), "chaque requête cible la relation OpenStreetMap du département (area ref:INSEE), jamais un cercle")
verifier(all("[timeout:90]" in r for r in FO.requetes), "délai Overpass de 90 s par requête (requêtes découpées : jamais toute la région d'un coup)")
verifier(any('"craft"="hvac"' in r for r in FO.requetes) and any('"amenity"="fast_food"' in r for r in FO.requetes), "plombier-chauffagiste : craft=plumber et craft=hvac ; restaurant : restaurant et fast_food")
verifier(SOMMEIL == [15] * 29, f"15 s entre deux requêtes Overpass, jamais avant la première : {len(SOMMEIL)} pauses")
monde(trouves=[], config={"sourcing_requetes_max": 30, "sirene_actif": False, "cible_reserve": 2000}); FO.__init__(); lancer("sourcer", "--jour", JOUR, "--dept", "27")
verifier(len(FO.requetes) == NM and all('"ref:INSEE"="27"' in r for r in FO.requetes), f"--dept 27 : seulement les {NM} requêtes (une par métier) de l'Eure")
code, _ = lancer("sourcer", "--dept", "75"); verifier(code != 0, "--dept hors Normandie : refusé")
# nouvelles tentatives après une erreur Overpass (429 puis 503, puis réponse)
class Rep:
    def __init__(s, c): s.c = c
    def __enter__(s): return s
    def __exit__(s, *a): return False
    def read(s, *a): return json.dumps(s.c).encode()
import urllib.error
essais = []
def ouvrir_capricieux(rq, timeout=0):
    essais.append(1)
    if len(essais) == 1: raise urllib.error.HTTPError("u", 429, "trop vite", {}, None)
    if len(essais) == 2: raise urllib.error.HTTPError("u", 503, "occupé", {}, None)
    return Rep({"elements": []})
attentes = []; r = P.appel_overpass("[out:json];", ouvrir=ouvrir_capricieux, dormir=attentes.append)
verifier(r == {"elements": []} and len(essais) == 3 and attentes == [30, 60], f"Overpass : refus 429 puis 503 -> nouvelles tentatives après 30 s et 60 s ({attentes}), puis succès")

# SIRENE : doublures (aucun réseau)
class FauxSirene:
    def __init__(s): s.appels, s.pages, s.panne = [], {}, False
    def __call__(s, dept, naf, page):
        s.appels.append((dept, naf, page))
        if s.panne: raise OSError("panne simulée")
        return {"results": s.pages.get((dept, naf, page), [])}
def ent(siren, nom, cp="76000", ville="ROUEN", etat="A"): return {"siren": siren, "nom_complet": nom, "etat_administratif": etat, "siege": {"code_postal": cp, "libelle_commune": ville}}
class FauxSites:
    def __init__(s): s.pages, s.lus = {}, []
    def __call__(s, url):
        s.lus.append(url); t = s.pages.get(url)
        return (url, {}, t) if t else None
FS, FSI = FauxSites(), FauxSirene()
A.lire_site = FS; A.appel_sirene = FSI; A.evaluer_site = lambda url, texte: ("site faible" in texte, 5 if "site faible" in texte else 0)
def page(tel_html, faible):
    return f"<html>Rouen 76000 {'site faible' if faible else 'site soigné'} {tel_html}</html>"
SR = {("76", "43.22A", 1): [
    ent("111000001", "PLOMBERIE MARTIN (MARTIN PAUL)"),                       # téléphone trouvé sur la fiche OpenStreetMap SANS commune
    ent("111000002", "ENTREPRISE DUBOIS CHAUFFAGE"),                          # téléphone sur son site, site faible : gardée
    ent("111000003", "ATELIER BON SITE"),                                     # site correct : exclue
    ent("111000004", "SANS TEL SARL"),                                        # ni fiche ni site : aucun numéro, écartée
    ent("111000005", "ENTREPRISE DOUBLON TEL"),                               # numéro déjà connu
    ent("111000006", "ENTREPRISE FERMEE", etat="C"),                          # cessée : jamais prise
    ent("111000007", "ENTREPRISE HORS DEPT", cp="14000", ville="CAEN"),       # siège dans un autre département que celui demandé
    ent("111000008", "CHAUFFAGE EUROPE SA"),                                  # 08 : numéro spécial, refusé
    ent("111000009", "DEJA CONNUE", ville="ROUEN")]}                          # même nom et même ville qu'une fiche existante
SR[("76", "43.22B", 1)] = [ent("111000010", "PLOMBIER NORD", ville="ELBEUF", cp="76500")]
FS.pages = {"https://duboischauffage.fr": page("<a href='tel:+33235700030'>02 35 70 00 30</a>", True),
            "https://atelierbonsite.fr": page("<a href='tel:0235700040'>02 35 70 00 40</a>", False),
            "https://doublontel.fr": page("<a href='tel:0235999999'>02 35 99 99 99</a>", True),
            "https://chauffageeurope.fr": page("<a href='tel:0800123456'>0800 12 34 56</a>", True),
            "https://plombiernord.fr": page("Elbeuf 76500 <a href='tel:0235700050'>02 35 70 00 50</a>", True)}
FSI.pages = SR
def monde_s(config=None, **kw):
    cf = {"sourcing_requetes_max": 1, "sirene_requetes_max": 5, "sirene_pages_max": 2, "sirene_sites_max": 20, "departements": ["76"], "pause_site_s": 2, "pause_sirene_s": 1, "cible_reserve": 2000}; cf.update(config or {})
    monde(trouves=kw.get("trouves", [trouve("Deja Connue", "plombier-chauffagiste", "Rouen", "02 35 99 99 99")]), config=cf); FO.__init__(); FSI.appels.clear(); FS.lus.clear(); FSI.panne = False
    FO.fixes = [[el(1), el(1, name="Plomberie Martin", **{"addr:city": "", "phone": "02 35 70 00 20"})]]
monde_s(); avant = P.lire_trouves(); code, sortie = lancer("sourcer", "--a-blanc", "--jour", JOUR)
verifier(code == 0 and "à blanc" in sortie and P.lire_trouves() == avant and not A.ETAT.exists() and not A.JOURNAL.exists(), "SIRENE --a-blanc : rien n'est écrit (prospection-trouves.csv, état, journal)")
verifier(len(FSI.appels) > 0, "… mais l'API SIRENE est bien interrogée (à blanc = lecture seule)")
monde_s(); code, sortie = lancer("sourcer", "--jour", JOUR); apres = P.lire_trouves(); neuves = {l["nom"]: l for l in apres if l not in [trouve("Deja Connue", "plombier-chauffagiste", "Rouen", "02 35 99 99 99")]}
verifier(code == 0 and set(neuves) >= {"Plomberie Martin", "Entreprise Dubois Chauffage", "Plombier Nord"}, f"SIRENE : les entreprises dont on trouve un numéro sont ajoutées : {sorted(neuves)}")
verifier("Atelier Bon Site" not in neuves and "Sans Tel Sarl" not in neuves and "Entreprise Doublon Tel" not in neuves and "Entreprise Fermee" not in neuves and "Entreprise Hors Dept" not in neuves and "Chauffage Europe Sa" not in neuves and len([l for l in apres if l["nom"] == "Deja Connue"]) == 1,
         "écartées : site correct, aucun numéro, numéro déjà connu, entreprise cessée, autre département, numéro 08, même nom et même ville qu'une fiche existante")
m = neuves["Plomberie Martin"]; d = neuves["Entreprise Dubois Chauffage"]
verifier(m["telephone"] == "02 35 70 00 20" and m["siren"] == "111000001" and m["statut"] == "sans site, téléphone" and m["cp"] == "76000" and m["source"].startswith("SIRENE") and "fiche OpenStreetMap" in m["source"], "numéro lu sur la fiche OpenStreetMap (sans addr:city), SIREN et source notés")
verifier(d["telephone"] == "02 35 70 00 30" and d["statut"] == "téléphone seulement" and d["site_actuel"] == "https://duboischauffage.fr" and "site public" in d["source"], "numéro lu sur le site public (lien tel: +33), site faible : statut « téléphone seulement »")
verifier(all(A.telephone_valide(l["telephone"]) == l["telephone"] and l["telephone"] for l in neuves.values()), "toutes les lignes ajoutées ont un numéro français valide, normalisé")
verifier("https://atelierbonsite.fr" in FS.lus and "https://sanstel.fr" in FS.lus and not any("exemple" in u for u in FS.lus), "les sites sont cherchés sous les domaines usuels du nom (.fr puis .com)")
verifier(all(a[0] == "76" for a in FSI.appels) and ("76", "43.22A", 1) in FSI.appels and ("76", "43.22B", 1) in FSI.appels, f"codes NAF du plombier-chauffagiste : 43.22A et 43.22B interrogés ({FSI.appels[:3]})")
verifier(SOMMEIL.count(1) == len(FSI.appels) - 1 and SOMMEIL.count(2) >= 1, f"pauses : 1 s entre deux appels d'API, 2 s entre deux pages de sites ({SOMMEIL})")
etat = A.etat_lire(); sv = etat["sirene"]["vus"]
verifier(sv["111000001"].endswith("ajoutée") and sv["111000003"].endswith("site correct") and sv["111000004"].endswith("sans téléphone") and sv["111000005"].endswith("numéro déjà connu"), f"état : chaque entreprise examinée est notée avec son résultat : {sorted(set(v.split('|')[1] for v in sv.values()))}")
j = A.JOURNAL.read_text(encoding="utf-8"); verifier("SIRENE" in j and not re.search(r"\d\d \d\d \d\d \d\d \d\d|Dubois|Martin|@", j), "journal : nombres seulement, aucune donnée personnelle")
# deuxième passage : rien n'est refait (entreprises déjà examinées), aucune ligne en double
n_lignes = len(P.lire_trouves())
FO.__init__(); FO.fixes = [[]]; FSI.appels.clear(); FS.lus.clear(); lancer("sourcer", "--jour", JOUR2)
verifier(len(P.lire_trouves()) == n_lignes and not any(u in FS.lus for u in ("https://atelierbonsite.fr", "https://duboischauffage.fr")), "deuxième passage : aucune entreprise examinée deux fois, aucune ligne en double")
# limites : pages de sites, appels d'API, pages par code NAF et curseur
monde_s(config={"sirene_sites_max": 2}); lancer("sourcer", "--jour", JOUR)
verifier(len(FS.lus) <= 2, f"sirene_sites_max = 2 : au plus 2 pages de sites lues ({len(FS.lus)})")
monde_s(config={"sirene_requetes_max": 1}); lancer("sourcer", "--jour", JOUR); verifier(len(FSI.appels) == 1, "sirene_requetes_max = 1 : un seul appel d'API")
monde_s(config={"sirene_actif": False}); lancer("sourcer", "--jour", JOUR); verifier(FSI.appels == [] and FS.lus == [], "sirene_actif = false : SIRENE n'est pas interrogée")
page25 = [ent(f"2220{i:05d}", f"ENTREPRISE SANS NUMERO {i}") for i in range(25)]
FSI.pages = {("76", "43.22A", 1): page25, ("76", "43.22A", 2): page25[:3]}
monde_s(config={"sirene_pages_max": 1, "sirene_sites_max": 200}); lancer("sourcer", "--jour", JOUR)
verifier(FSI.appels[0] == ("76", "43.22A", 1) and A.etat_lire()["sirene"]["curseurs"].get("76|43.22A") == 2, f"sirene_pages_max = 1 : première page lue, le curseur de reprise est noté (page 2) : {A.etat_lire()['sirene']['curseurs']}")
FSI.appels.clear(); lancer("sourcer", "--jour", JOUR2); verifier(FSI.appels and FSI.appels[0] == ("76", "43.22A", 2), "le passage suivant reprend à la page 2 (le sourcing se fait par petites étapes)")
FSI.pages = SR
# panne de l'API SIRENE : message, ce qui a été trouvé est gardé, aucun plantage
monde_s(); FSI.panne = True; code, sortie = lancer("sourcer", "--jour", JOUR)
verifier(code == 2 and "échec" in sortie.lower() and any(l["nom"] == "Fiche 1" for l in P.lire_trouves()), "panne SIRENE : échec signalé (code 2), les fiches OpenStreetMap déjà trouvées sont gardées")
FSI.panne = False
# lecture du numéro sur une page publique
verifier(A.telephones_page("<a href='tel:+33 2 35 62 41 64'>x</a> Mobile 06.12.34.56.78 ; 0800 12 34 56 ; 02 35 62 41 64") == ["02 35 62 41 64", "06 12 34 56 78"], "telephones_page : liens tel: puis texte, mobile et fixe valides, 08 refusé, doublons écartés")
verifier(A.telephones_page("Du 12 34 56 78 90 au 11 11 11 11 11 : prix 20 35 624 164") == [], "telephones_page : suites de chiffres qui ne sont pas des numéros français : refusées")
verifier(callable(A.evaluer_site), "evaluer_site : constat vérifié de la prospection (site correct = entreprise exclue)")

print("14 ter. Jamais redonner un numéro, STOP par numéro, réserve par département")
monde(trouves=gros_monde(30), config={"par_liste": 100}); lancer("preparer", "--jour", JOUR)
donnes = {l[TEL] for l in lire_csv(JOUR)[1:]}; verifier(len(donnes) == 100, "liste du jour préparée (100 numéros)")
nom_donne = next(l[1] for l in lire_csv(JOUR)[1:])
P.ecrire_trouves(P.lire_trouves() + [trouve("Autre Nom Meme Numero", "restaurant", "Autre Ville", next(iter(donnes)))], P.TROUVES)
verifier("Autre Nom Meme Numero" not in {c["nom"] for c in A.candidats(A.etat_lire())}, "un numéro déjà donné à Sid ne ressort jamais, même sous un autre nom d'entreprise")
S.ecrire(S.lire() + [suivi("Nom Different Stop", "restaurant", "Autre Ville", "06 99 88 77 66", statut="STOP")])
P.ecrire_trouves(P.lire_trouves() + [trouve("Encore Un Nom", "restaurant", "Ville X", "06 99 88 77 66")], P.TROUVES)
verifier("Encore Un Nom" not in {c["nom"] for c in A.candidats(A.etat_lire())}, "le numéro d'une entreprise qui a dit STOP n'est jamais redonné, même sous un autre nom")
code, _ = lancer("annuler", JOUR, "--force"); P.ecrire_trouves([l for l in P.lire_trouves() if l["nom"] != "Autre Nom Meme Numero"], P.TROUVES)
verifier(code == 0 and "Autre Nom Meme Numero" not in {c["nom"] for c in A.candidats(A.etat_lire())} and len(donnes & {c["tel"] for c in A.candidats(A.etat_lire())}) == 100, "après annulation de la liste : les numéros sont de nouveau disponibles")
t_dep = [trouve(f"Plomb Calvados {i}", "plombier-chauffagiste", "Caen", tel(2000 + i), cp="14000") for i in range(3)] + [trouve(f"Resto Manche {i}", "restaurant", "Saint-Lô", tel(2100 + i), cp="50000") for i in range(2)] + \
        [trouve("Coiff Rouen", "coiffeur", "Rouen", tel(2200), cp="76000"), trouve("Elec Sans Cp", "électricien", "Quelque Part", tel(2300), cp="")]
monde(trouves=t_dep, config={"par_liste": 100}); code, sortie = lancer("etat")
verifier(code == 0 and "Réserve par métier et par département" in sortie and "Calvados 14" in sortie and "Manche 50" in sortie and "Seine-Maritime 76" in sortie and "Orne 61" in sortie and "Eure 27" in sortie, "etat : tableau métier x département (les cinq départements normands)")
verifier(re.search(r"Plombier-chauffagiste\s+3\s+0\s+0\s+0\s+0\s+3|Plombier-chauffagiste\s+[\d\s]*3", sortie) is not None and "inconnu" in sortie, "le tableau donne le nombre par métier et par département, et une colonne pour les codes postaux inconnus")
verifier("= 0 jour(s) à 100 numéros par jour" in sortie, f"jours de réserve à 100 numéros par jour (7 numéros : 0 jour) : {[l for l in sortie.splitlines() if 'jour(s)' in l]}")
monde(trouves=gros_monde(30), config={"par_liste": 100}); code, sortie = lancer("etat"); verifier("= 2 jour(s) à 100 numéros par jour" in sortie, "210 numéros (7 métiers x 30) / 100 par jour : 2 jours de réserve, dit en toutes lettres")
monde(trouves=gros_monde(30), config={"sourcing_requetes_max": 1, "sirene_actif": False}); FO.__init__(); FO.fixes = [[]]; code, sortie = lancer("sourcer", "--jour", JOUR, "--a-blanc")
verifier("Réserve par métier et par département" in sortie and "jour(s) à 100 numéros par jour" in sortie, "fin de `sourcer` : la réserve par métier et par département et les jours de réserve sont affichés")
monde(trouves=gros_monde(30), config={"sirene_actif": False, "cible_reserve": 100}); FO.__init__(); code, sortie = lancer("jour", "--jour", JOUR)
verifier("Réserve par métier et par département" in sortie and "jour(s) à 100 numéros par jour" in sortie, "fin de `jour` : même tableau")

print("14 quater. Mode simulation : aucun réseau, données fictives, rien d'écrit")
orig = (A.appel_reseau, A.appel_sirene, A.lire_site, A.evaluer_site, A.dormir)
#  NB : le générateur SIRENE fictif de _simulation() (appels-sid.py) ne connaît que 4 métiers (plombier, électricien, coiffeur, restaurant) ; au-delà, il lève KeyError.
#  Non modifié ici (appels-sid.py hors périmètre) : SIRENE désactivé pour ce test de simulation, qui porte sur Overpass et l'absence d'écriture, pas sur la couverture SIRENE des 21 métiers.
monde(trouves=[], config={"sourcing_requetes_max": 9, "sirene_actif": False, "cible_reserve": 2000}); avant = P.lire_trouves()
code, sortie = lancer("sourcer", "--simulation", "--jour", JOUR)
verifier(code == 0 and P.lire_trouves() == avant and not A.ETAT.exists() and not A.JOURNAL.exists() and not list(tmp.glob("*.tmp")), "sourcer --simulation : aucun accès réseau (urlopen interdit dans ce test), rien d'écrit")
verifier("9 requête(s) Overpass" in sortie and "0 appel(s) SIRENE" in sortie, f"simulation : les 9 premiers métiers du catalogue (plombier à paysagiste, règle du 10 nov. 2026) tournent : {[l for l in sortie.splitlines() if l.startswith('Sourcing')]}")
verifier("Réserve par métier et par département" in sortie and "Seine-Maritime 76" in sortie and "jour(s) à 100 numéros par jour" in sortie, "simulation : le tableau final de réserve est affiché")
A.appel_reseau, A.appel_sirene, A.lire_site, A.evaluer_site, A.dormir = orig
code, sortie = lancer("sourcer", "--simulation", "--dept", "50", "--jour", JOUR); verifier(code == 0 and "9 requête(s) Overpass" in sortie, "simulation limitée à un département : 9 requêtes")
A.appel_reseau, A.appel_sirene, A.lire_site, A.evaluer_site, A.dormir = orig
src2 = (ICI / "appels-sid.py").read_text(encoding="utf-8")
verifier("recherche-entreprises.api.gouv.fr" in (ICI / "prospection.py").read_text(encoding="utf-8") and "google.com/maps" not in src2 and "pagesjaunes" not in src2.lower() and "googleapis.com/maps" not in src2 and "places.googleapis" not in src2, "sources : OpenStreetMap (Overpass) et l'API officielle SIRENE seulement ; ni Google Maps ni Pages Jaunes")
A.appel_reseau = reseau; A.appel_sirene = lambda dept, naf, page: {"results": []}; A.lire_site = lambda url: None

print("15. Google Drive : un tableur « Appels AAAA-MM-JJ » par jour, directement dans le dossier « Sid » (aucun sous-dossier), partage")
monde(trouves=gros_monde(), config={"envoi_automatique": True})
lancer("preparer", "--jour", JOUR); A.exporter_google(A.cfg(), A.etat_lire(), JOUR, DRIVE, False)
racine = DRIVE.trouver_dossier("Sid")
verifier(racine and DRIVE.dossiers[racine] == ("Sid", None) and len(DRIVE.dossiers) == 1, "dossier « Sid » à la racine du Drive, aucun sous-dossier par jour")
fid = DRIVE.trouver_feuille(racine, f"Appels {JOUR}"); verifier(fid is not None and len(DRIVE.feuilles) == 1, "un seul tableur « Appels AAAA-MM-JJ », posé directement dans le dossier")
contenu = list(csv.reader(io.StringIO(DRIVE.feuilles[fid][2]))); verifier(contenu == lire_csv(JOUR), "la feuille a exactement le contenu du CSV")
verifier(contenu[0] == COLONNES, "colonnes dans l'ordre : Créneau, Entreprise, Métier, Ville, Téléphone, Détail fiche, Résultat, Note")
verifier(DRIVE.mises_en_forme == [(fid, tuple(A.LARGEURS_PX), (6, ["Pas de réponse", "À rappeler", "RDV pris", "Non catégorique", "Je dois réfléchir", "Trop cher", "Déjà un site", "Pas le temps"]))] and min(A.LARGEURS_PX) >= 120,
         "mise en forme : colonnes larges, en-tête figé, Résultat en liste à 8 valeurs")
verifier(json.loads(A.ETAT.read_text(encoding="utf-8"))["google"][JOUR]["feuille"] == fid, "état : identifiants du dossier et de la feuille")
n_avant = (len(DRIVE.dossiers), len(DRIVE.feuilles)); A.exporter_google(A.cfg(), A.etat_lire(), JOUR, DRIVE, False)
verifier((len(DRIVE.dossiers), len(DRIVE.feuilles)) == n_avant, "tableur du jour déjà là : rien recréé, rien écrasé")
etat = A.etat_lire(); etat["google"] = {}; A.etat_ecrire(etat); A.exporter_google(A.cfg(), A.etat_lire(), JOUR, DRIVE, False)
verifier((len(DRIVE.dossiers), len(DRIVE.feuilles)) == n_avant, "état perdu : le Drive est consulté, le tableur existant est reconnu (aucun doublon)")
DRIVE.feuilles.pop(fid); etat = A.etat_lire(); etat["google"] = {}; A.etat_ecrire(etat); A.exporter_google(A.cfg(), A.etat_lire(), JOUR, DRIVE, False)
verifier(len(DRIVE.dossiers) == n_avant[0] and len(DRIVE.feuilles) == 1, "tableur manquant : il est recréé, rien d'autre")
lancer("preparer", "--jour", JOUR2); A.exporter_google(A.cfg(), A.etat_lire(), JOUR2, DRIVE, False)
verifier(len(DRIVE.dossiers) == 1 and DRIVE.trouver_feuille(racine, f"Appels {JOUR2}"), "le lendemain : « Sid » réutilisé, nouveau tableur, toujours aucun sous-dossier")
DRIVE.__init__(); etat = A.etat_lire(); etat["google"] = {}; A.etat_ecrire(etat)
A.exporter_google(A.cfg(), A.etat_lire(), JOUR, DRIVE, True)
verifier(DRIVE.appels == 0, "--a-blanc : le Drive n'est pas contacté")
monde(trouves=gros_monde(), config={}); lancer("preparer", "--jour", JOUR); DRIVE.panne = True
code, sortie = lancer("jour", "--jour", JOUR); verifier(code == 0 and DRIVE.appels == 0 and "google" in sortie.lower() and "simulation" in sortie.lower(), "envoi_automatique=false : Google n'est jamais appelé, la sortie dit ce qui serait créé")
# partage
monde(trouves=gros_monde(), config={"envoi_automatique": True}); lancer("preparer", "--jour", JOUR); A.exporter_google(A.cfg(), A.etat_lire(), JOUR, DRIVE, False)
verifier(DRIVE.partages == [], "partager_avec vide : rien n'est partagé")
monde(trouves=gros_monde(), config={"envoi_automatique": True, "partager_avec": "Sid@Example.invalid"}); lancer("preparer", "--jour", JOUR); A.exporter_google(A.cfg(), A.etat_lire(), JOUR, DRIVE, False)
verifier(DRIVE.partages == [(DRIVE.trouver_dossier("Sid"), "sid@example.invalid")], "partager_avec renseigné : le dossier « Sid » est partagé (éditeur) avec cette adresse")
lancer("preparer", "--jour", JOUR2); A.exporter_google(A.cfg(), A.etat_lire(), JOUR2, DRIVE, False)
verifier(len(DRIVE.partages) == 1, "partage fait une seule fois")
monde(trouves=gros_monde(), config={"envoi_automatique": False, "partager_avec": "sid@example.invalid"}); lancer("preparer", "--jour", JOUR); lancer("jour", "--jour", JOUR); verifier(DRIVE.partages == [] and DRIVE.appels == 0, "simulation : jamais de partage, même avec une adresse")
monde(trouves=gros_monde(), config={"envoi_automatique": True, "partager_avec": "pas une adresse"}); lancer("preparer", "--jour", JOUR); A.exporter_google(A.cfg(), A.etat_lire(), JOUR, DRIVE, False)
verifier(DRIVE.partages == [] and DRIVE.trouver_feuille(DRIVE.trouver_dossier("Sid"), f"Appels {JOUR}"), "adresse invalide : rien partagé, le tableur est quand même créé")
monde(trouves=gros_monde(), config={"envoi_automatique": True}); DRIVE.compte_reel = "autre@example.invalid"; lancer("preparer", "--jour", JOUR)
try: A.exporter_google(A.cfg(), A.etat_lire(), JOUR, DRIVE, False); verifier(False, "jeton d'un autre compte : refusé")
except A.ErreurAgent as e: verifier("contact.lmsites@gmail.com" in str(e) and not DRIVE.dossiers, "jeton d'un autre compte : refusé avant toute création")

print("16. google_sheets : portée minimale, aucun jeton affiché")
gsrc = (ICI / "google_sheets.py").read_text(encoding="utf-8")
verifier(GS.PORTEES == ["https://www.googleapis.com/auth/drive.file"], "une seule portée : drive.file (fichiers créés par l'agent seulement)")
verifier(GS.JETON.name == "google-sheets-token.json" and GS.CLIENT.name == "google-client.json", "jeton agents\\google-sheets-token.json, client agents\\google-client.json")
verifier(not re.search(r"print\([^)]*(jeton|token|secret)", gsrc, re.I), "aucun jeton ni secret affiché")
class Req:
    def __init__(s, f): s.f = f
    def execute(s): return s.f()
class FauxSvc:
    """Imite googleapiclient : svc.files().list(...).execute() ; garde les appels."""
    def __init__(s): s.journal, s.fichiers, s.n, s.trashed = [], [], 0, set()
    def files(s): return s
    def permissions(s): return s
    def about(s): return s
    def list(s, **k):
        s.journal.append(("list", k))
        def _r():
            q = k["q"].replace("\\'", "'"); out = []
            for f in s.fichiers:
                if f["id"] in s.trashed or f["mimeType"] not in q: continue
                if "name = '" in q and f"name = '{f['name']}'" not in q: continue
                if f["parents"][0] not in q: continue
                out.append(f)
            return {"files": out}
        return Req(_r)
    def update(s, **k):
        s.journal.append(("update", k))
        def _r():
            if k.get("body", {}).get("trashed"): s.trashed.add(k["fileId"])
            return {"id": k["fileId"]}
        return Req(_r)
    def create(s, **k):
        s.journal.append(("create", k))
        def _r():
            s.n += 1; b = k.get("body", {})
            if "role" in b: return {"id": "perm"}
            s.fichiers.append({"id": f"X{s.n}", "name": b["name"], "mimeType": b["mimeType"], "parents": b.get("parents") or ["root"]}); return {"id": f"X{s.n}"}
        return Req(_r)
    def get(s, **k): s.journal.append(("get", k)); return Req(lambda: {"user": {"emailAddress": "contact.lmsites@gmail.com"}})
sv = FauxSvc(); d = GS.Drive(sv, "contact.lmsites@gmail.com")
verifier(d.compte() == "contact.lmsites@gmail.com", "compte lu dans le profil Drive")
i = d.creer_dossier("Sid"); j2 = d.creer_dossier("2026-11-04", i)
verifier(d.trouver_dossier("Sid") == i and d.trouver_dossier("2026-11-04", i) == j2 and d.trouver_dossier("Absent") is None, "recherche de dossier par nom et parent (corbeille exclue)")
verifier(all("trashed = false" in k["q"] for n, k in sv.journal if n == "list"), "les dossiers à la corbeille sont ignorés")
f = d.creer_feuille(j2, "Liste d'appels 2026-11-04", "a,b\n1,2\n"); cr = [k for n, k in sv.journal if n == "create"][-1]
verifier(cr["body"]["mimeType"] == "application/vnd.google-apps.spreadsheet" and cr["body"]["parents"] == [j2] and cr.get("media_body") is not None, "feuille créée par conversion du CSV (Drive), dans le dossier du jour")
verifier(d.trouver_feuille(j2, "Liste d'appels 2026-11-04") == f, "feuille retrouvée par son titre dans le dossier")
d.partager(i, "sid@example.invalid"); cr = [k for n, k in sv.journal if n == "create"][-1]
verifier(cr["body"] == {"type": "user", "role": "writer", "emailAddress": "sid@example.invalid"} and cr["fileId"] == i, "partage en éditeur (writer) du dossier")
d.creer_dossier("L'apostrophe", None); verifier(d.trouver_dossier("L'apostrophe") is not None, "apostrophe dans un nom : requête correctement échappée")
j3 = d.creer_dossier("2026-10-01", i)
verifier(sorted(n for _, n in d.lister_dossiers(i)) == ["2026-10-01", "2026-11-04"], "lister_dossiers : les sous-dossiers d'un dossier parent")
d.mettre_corbeille(j3); maj = [k for n, k in sv.journal if n == "update"][-1]
verifier(maj == {"fileId": j3, "body": {"trashed": True}, "fields": "id"}, "mettre_corbeille : trashed=true (jamais une suppression définitive)")
verifier(d.trouver_dossier("2026-10-01", i) is None and j3 not in [x for x, _ in d.lister_dossiers(i)], "dossier à la corbeille : plus retrouvé ni listé")
verifier(d.trouver_dossier("2026-11-04", i) == j2, "les autres dossiers ne sont pas touchés")
f2 = d.creer_feuille(i, "Appels 2026-11-04", "a,b\n1,2\n")
verifier([n for _, n in d.lister_feuilles(i)] == ["Appels 2026-11-04"] and all(n == "Liste d'appels 2026-11-04" for _, n in d.lister_feuilles(j2)), "lister_feuilles : les feuilles directement dans un dossier")
class Boom(Exception): pass
class SvcPanne(FauxSvc):
    def list(s, **k): return Req(lambda: (_ for _ in ()).throw(Boom("TOKEN-SECRET-123 ya29.xyz")))
try: GS.Drive(SvcPanne(), "x").trouver_dossier("Sid"); verifier(False, "erreur Google propagée")
except GS.ErreurDrive as e: verifier("TOKEN-SECRET" not in str(e) and "ya29" not in str(e), "erreur Google : aucun détail de la réponse (jeton) n'est repris")

print("17. Tâche planifiée : commande fournie, jamais installée sans --oui")
monde(trouves=gros_monde(), config={})
code, sortie = lancer("installer-tache")
verifier(code == 0 and EXEC == [], "installer-tache sans --oui : affiche la commande, n'exécute rien")
for motif in ("Register-ScheduledTask", "-Daily", "08:00", "-StartWhenAvailable", "IgnoreNew", "appels-sid.py", " jour", "Jarvis-AppelsSid", "Interactive"):
    verifier(motif in sortie, f"commande : contient « {motif} »")
verifier("--oui" in sortie, "la sortie dit comment l'installer vraiment")
code, sortie = lancer("retirer-tache"); verifier(code == 0 and EXEC == [] and "Unregister-ScheduledTask" in sortie and "Jarvis-AppelsSid" in sortie, "retirer-tache sans --oui : affiche la commande, n'exécute rien")
code, _ = lancer("installer-tache", "--oui"); verifier(code == 0 and len(EXEC) == 1 and "Register-ScheduledTask" in EXEC[0], "installer-tache --oui : exécutée une fois (doublure en test)")
code, _ = lancer("retirer-tache", "--oui"); verifier(code == 0 and len(EXEC) == 2 and "Unregister-ScheduledTask" in EXEC[1], "retirer-tache --oui : exécutée une fois")
A.executer = lambda cmd: (1, "accès refusé"); code, sortie = lancer("installer-tache", "--oui"); verifier(code == 2 and "accès refusé" in sortie, "échec de l'installation : message, code 2"); A.executer = faux_executer
verifier(not any("installer-tache" in str(c) for c in EXEC), "la tâche lance `jour` (jamais installer-tache)")

print("18. Alerte : réserve sous 2 jours")
monde(trouves=gros_monde(20), config={"envoi_automatique": True}); A.appel_reseau = FauxOverpass()
code, _ = lancer("jour", "--jour", JOUR)
verifier(code == 0 and any("réserve" in a.lower() for a in ALERTES), f"réserve 80 puis liste de 55 : sous 110, alerte Discord ({len(ALERTES)})")
verifier(all(not re.search(r"\d\d \d\d \d\d \d\d|@|Fictif", a) for a in ALERTES), "alerte sans donnée personnelle (nombres par métier seulement)")
n = len(ALERTES); lancer("jour", "--jour", JOUR); verifier(len(ALERTES) == n, "même jour : pas de seconde alerte")
monde(trouves=gros_monde(80), config={"envoi_automatique": True}); A.appel_reseau = FauxOverpass(); lancer("jour", "--jour", JOUR)
verifier(not any("réserve" in a.lower() for a in ALERTES), "réserve suffisante : aucune alerte")
monde(trouves=gros_monde(20), config={}); lancer("jour", "--jour", JOUR); verifier(ALERTES == [] and "réserve" in A.JOURNAL.read_text(encoding="utf-8").lower(), "simulation : pas de Discord, mais l'alerte est dans le journal")
A.appel_reseau = reseau

print("19. jour : verrou, panne d'une étape, rien de bloquant")
monde(trouves=gros_monde(), config={"envoi_automatique": True}); A.appel_reseau = FauxOverpass()
A.VERROU.write_text(str(os.getpid()), encoding="utf-8"); code, sortie = lancer("jour", "--jour", JOUR)
verifier(code == 2 and "verrou" in sortie.lower() and not (A.SORTIE / f"liste-sid-{JOUR}.csv").exists(), "deux lancements en même temps : le second est refusé")
A.VERROU.write_text("99999999", encoding="utf-8")
code, _ = lancer("jour", "--jour", JOUR); verifier(code == 0 and not A.VERROU.exists(), "verrou d'un processus mort : repris, puis libéré")
monde(trouves=gros_monde(), config={"envoi_automatique": True}); A.VERROU.write_text(str(os.getpid()), encoding="utf-8"); vieux = A.VERROU.stat().st_mtime - 4 * 3600; os.utime(A.VERROU, (vieux, vieux))
code, _ = lancer("jour", "--jour", JOUR); verifier(code == 0, "verrou vieux de plus de 3 h (processus bloqué) : repris, une panne ne bloque jamais les jours suivants")
monde(trouves=gros_monde(), config={"envoi_automatique": True}); FP = FauxOverpass(); FP.panne = True; A.appel_reseau = FP; DRIVE.panne = True
code, sortie = lancer("jour", "--jour", JOUR)
verifier((A.SORTIE / f"liste-sid-{JOUR}.csv").exists() and code == 0, "sourcing ET Google en panne : la liste du jour est quand même préparée (CSV local)")
verifier(sum("sourcing" in a.lower() for a in ALERTES) == 1 and sum("google" in a.lower() for a in ALERTES) == 1, "une alerte pour le sourcing, une pour Google")
verifier(not A.VERROU.exists(), "verrou libéré malgré les pannes")
DRIVE.panne = False; FP.panne = False; code, _ = lancer("jour", "--jour", JOUR)
verifier(code == 0 and DRIVE.trouver_feuille(DRIVE.trouver_dossier("Sid"), f"Appels {JOUR}"), "le passage suivant rattrape Google (la liste existante n'est ni refaite ni re-marquée)")
verifier(len(json.loads(A.ETAT.read_text(encoding="utf-8"))["sorties"]) == 100, "toujours 100 entreprises marquées (pas de seconde liste)")
A.appel_reseau = reseau
code, sortie = lancer("jour", "--jour", JOUR2, "--a-blanc"); verifier(code == 0 and "à blanc" in sortie.lower() and "sourcing" in sortie.lower() and "google" in sortie.lower(), "jour --a-blanc : décrit chaque étape, sans réseau")
monde(trouves=gros_monde(), config={"envoi_automatique": True}); A.ARRET.write_text("stop", encoding="utf-8"); verifier(lancer("jour", "--jour", JOUR)[0] == 2 and not DRIVE.dossiers and not DRIVE.feuilles, "arrêt de secours : rien n'est fait")
verifier(lancer("google-autoriser", "--a-blanc")[0] == 0, "google-autoriser --a-blanc : n'ouvre rien")

print("20. Contrôle de bout en bout : 3 jours de suite, à blanc, sans réseau ni Google réel")
JOURS = ["2026-11-05", "2026-11-06", "2026-11-07"]
base = ([trouve(f"Resto E2E {i}", "restaurant", "Rouen", tel(100 + i)) for i in range(34)] + [trouve(f"Coiff E2E {i}", "coiffeur", "Rouen", tel(300 + i)) for i in range(18)]
        + [trouve(f"Plomb E2E {i}", "plombier-chauffagiste", "Rouen", tel(500 + i)) for i in range(8)] + [trouve(f"Elec E2E {i}", "électricien", "Rouen", tel(700 + i)) for i in range(8)])
REPART_4 = {m: (5 if m in ("restaurant", "coiffeur", "plombier", "electricien") else 0) for m in A.NOMS}   # scénario historique à 4 métiers : sans cela, le quota (poids égal sur 21 métiers) disperserait le budget de sourcing sur des métiers que FauxOverpass ne fournit pas
monde(trouves=base, config={"envoi_automatique": True, "partager_avec": "sid@example.invalid", "cible_reserve": 400, "seuil_alerte": 50, "sourcing_requetes_max": 4, "repartition": REPART_4}, listes={"2026-11-03": [("ancienne-liste|rouen", "[ ] [ ] [ ] [ ]".split())]})
lancer("rediriger-liste")
FE = FauxOverpass(); A.appel_reseau = FE; reserves, alertes_par_jour, listes = [], {}, {}
def reserve_total(): return A.reserve(A.etat_lire())["total"]
def marquer_appele_sur_sheet(jour):
    """Simule Sid qui remplit « Résultat » sur toute la liste du jour, DANS LA FEUILLE GOOGLE (pas le fichier local) : c'est elle que relit le bilan du lendemain quand envoi_automatique=true."""
    racine = DRIVE.trouver_dossier("Sid"); fid = DRIVE.trouver_feuille(racine, f"Appels {jour}")
    titre, dossier, contenu = DRIVE.feuilles[fid]; lignes = list(csv.reader(io.StringIO(contenu)))
    for l in lignes[1:]:
        if len(l) > RES: l[RES] = "Pas de réponse"
    buf = io.StringIO(); csv.writer(buf).writerows(lignes); DRIVE.feuilles[fid] = (titre, dossier, buf.getvalue())
reserves.append(reserve_total())
for k, jour in enumerate(JOURS):
    FE.offre = {"plumber": 0, "electrician": 0, "hairdresser": 0, "restaurant": 0} if k != 1 else {"plumber": 40, "electrician": 40, "hairdresser": 40, "restaurant": 40}
    FE.requetes.clear(); ALERTES.clear(); code, sortie = lancer("jour", "--jour", jour)
    verifier(code == 0, f"{jour} : jour terminé (code {code})")
    reserves.append(reserve_total()); alertes_par_jour[jour] = [a for a in ALERTES if "réserve" in a.lower()]
    listes[jour] = lire_csv(jour)[1:]
    marquer_appele_sur_sheet(jour)   # pour que le bilan du jour suivant (lu dans la feuille Google, envoi_automatique=true) ne reprenne rien en « A rappeler »
    P.cmd_liste_matin({**P.DEFAUT, **A.M.lire_fusionnee(A.PROSPECTION_CONFIG)}, api=reseau, paris=Matin())
verifier(reserves[1] < reserves[0] and reserves[2] > reserves[1] and reserves[3] < reserves[2], f"réserve : diminue (jour 1), se remplit (jour 2), diminue encore (jour 3) : {reserves}")
verifier(alertes_par_jour[JOURS[0]] and alertes_par_jour[JOURS[2]], "alerte déclenchée quand la réserve passe sous le seuil (jours 1 et 3)")
verifier(not alertes_par_jour[JOURS[1]], "pas d'alerte le jour où la réserve est remplie")
tous = [(l[NOM], l[TEL]) for j in JOURS for l in listes[j]]
total_attendu = sum(len(listes[j]) for j in JOURS)
verifier(len(tous) == len(set(tous)) == total_attendu and len({t[1] for t in tous}) == total_attendu, f"aucun doublon d'un jour à l'autre (toutes confirmées appelées) : {total_attendu} entreprises et autant de numéros différents")
verifier(not list((tmp / "docs").glob("liste-appels-2026-11-0[5-7].md")), "aucune liste d'appels générée pour Liam pendant les 3 jours (docs\\liste-appels-*.md)")
verifier({l[MET] for j in JOURS for l in listes[j]} <= {"Restaurant", "Coiffeur", "Plombier-chauffagiste", "Électricien"}, "uniquement les 4 métiers voulus")
racine = DRIVE.trouver_dossier("Sid")
verifier(sum(1 for n, p in DRIVE.dossiers.values() if n == "Sid") == 1 and len(DRIVE.dossiers) == 1, "un seul dossier « Sid », aucun sous-dossier par jour")
for jour in JOURS:
    f = DRIVE.trouver_feuille(racine, f"Appels {jour}")
    verifier(f is not None and [l[:RES] + l[RES + 1:] for l in list(csv.reader(io.StringIO(DRIVE.feuilles[f][2])))[1:]] == [l[:RES] + l[RES + 1:] for l in listes[jour]],
             f"{jour} : bon tableur, dans le dossier « Sid », même contenu que la liste du jour (hors Résultat, rempli depuis par le test)")
verifier(len(DRIVE.feuilles) == 3 and DRIVE.partages == [(racine, "sid@example.invalid")], "3 tableurs « Appels », un par jour, dossier « Sid » partagé une seule fois")
verifier(len(json.loads(A.ETAT.read_text(encoding="utf-8"))["sorties"]) == total_attendu, f"état : {total_attendu} entreprises marquées (confirmées appelées via la feuille Google, jamais reprises)")
hist = json.loads(A.HISTORIQUE.read_text(encoding="utf-8"))
verifier(len(hist) == 2 * (len(listes[JOURS[0]]) + len(listes[JOURS[1]])), f"historique : clés et numéros des deux premiers jours notés (le 3e n'a pas de lendemain dans ce test pour le lire) : {len(hist)}")
j = A.JOURNAL.read_text(encoding="utf-8"); verifier(not re.search(r"\d\d \d\d \d\d \d\d \d\d|@|E2E", j), "journal des 3 jours : aucune donnée personnelle")
A.appel_reseau = reseau

print("21. jours_appel : jour hors planning (aucune liste, aucun accès réseau ni Google, aucune alerte)")
MERCREDI, JEUDI, SAMEDI, LUNDI, VENDREDI = date(2026, 11, 4), date(2026, 11, 5), date(2026, 11, 7), date(2026, 11, 2), date(2026, 11, 6)
reel_maintenant = A.maintenant_paris
monde(trouves=gros_monde(), config={"envoi_automatique": True, "jours_appel": ["lundi", "mardi", "vendredi"]})
A.maintenant_paris = lambda: MERCREDI
code, sortie = lancer("jour", "--jour", JOUR)
verifier(code == 0 and "hors planning" in sortie.lower(), f"mercredi hors jours_appel : code 0, message clair ({sortie.strip()[:160]})")
verifier(not (A.SORTIE / f"liste-sid-{JOUR}.csv").exists() and not A.ETAT.exists(), "mercredi : aucune liste générée, aucun état écrit")
verifier(DRIVE.appels == 0 and ALERTES == [], "mercredi : aucun accès Drive, aucune alerte Discord")
verifier("jour hors planning" in A.JOURNAL.read_text(encoding="utf-8").lower(), "le journal note le jour hors planning")
A.maintenant_paris = lambda: JEUDI
code, sortie = lancer("jour", "--jour", JOUR)
verifier(code == 0 and "hors planning" in sortie.lower() and not (A.SORTIE / f"liste-sid-{JOUR}.csv").exists(), "jeudi hors jours_appel (remplacé par vendredi, 9/11/2026) : aucune liste générée")
A.maintenant_paris = lambda: SAMEDI
code, sortie = lancer("jour", "--jour", JOUR2)
verifier(code == 0 and "hors planning" in sortie.lower() and not (A.SORTIE / f"liste-sid-{JOUR2}.csv").exists(), "samedi (hors liste) : pareil, rien généré")
A.maintenant_paris = lambda: LUNDI
code, sortie = lancer("jour", "--jour", JOUR)
verifier(code == 0 and "hors planning" not in sortie.lower() and (A.SORTIE / f"liste-sid-{JOUR}.csv").exists(), "lundi (dans jours_appel) : la liste est générée normalement")
monde(trouves=gros_monde(), config={"envoi_automatique": True, "jours_appel": ["lundi", "mardi", "vendredi"]})
A.maintenant_paris = lambda: VENDREDI
code, sortie = lancer("jour", "--jour", JOUR)
verifier(code == 0 and (A.SORTIE / f"liste-sid-{JOUR}.csv").exists(), "vendredi (dans jours_appel) : la liste est générée")
monde(trouves=gros_monde(), config={"envoi_automatique": True})   # jours_appel absent du réglage
A.maintenant_paris = lambda: MERCREDI
code, sortie = lancer("jour", "--jour", JOUR)
verifier(code == 0 and (A.SORTIE / f"liste-sid-{JOUR}.csv").exists(), "jours_appel absent du réglage : aucune restriction (tous les jours)")
verifier(set(A.cfg()["jours_appel"]) == set(A.JOURS_SEMAINE), "réglage absent -> tous les jours (sécurité, jamais un blocage silencieux)")
monde(trouves=gros_monde(), config={"jours_appel": ["LUNDI", " mardi ", "inconnu", 42]})
verifier(A.cfg()["jours_appel"] == ["lundi", "mardi"], "jours_appel : casse et espaces tolérés, valeurs invalides écartées")
monde(trouves=gros_monde(), config={"jours_appel": ["inconnu", 42, ""]})
verifier(set(A.cfg()["jours_appel"]) == set(A.JOURS_SEMAINE), "jours_appel entièrement invalide -> tous les jours")
A.maintenant_paris = reel_maintenant
verifier(callable(A.maintenant_paris) and A.maintenant_paris() is not None, "maintenant_paris restauré (fonction réelle)")

print("22. Nettoyage Drive : tableurs « Appels » et anciens sous-dossiers de plus de 7 jours mis à la corbeille (jamais supprimés)")
monde(trouves=gros_monde(), config={})   # simulation
avant = DRIVE.appels; A.nettoyer_dossiers_drive(A.cfg(), A.etat_lire(), JOUR, DRIVE, False)
verifier(DRIVE.appels == avant, "simulation (envoi_automatique=false) : le Drive n'est pas contacté pour le nettoyage")
monde(trouves=gros_monde(), config={"envoi_automatique": True})
avant = DRIVE.appels; A.nettoyer_dossiers_drive(A.cfg(), A.etat_lire(), JOUR, DRIVE, True)
verifier(DRIVE.appels == avant, "--a-blanc : le Drive n'est pas contacté pour le nettoyage")
A.nettoyer_dossiers_drive(A.cfg(), A.etat_lire(), JOUR, DRIVE, False)
verifier(True, "pas encore de dossier « Sid » : rien ne casse")
racine = DRIVE.creer_dossier("Sid")
vieux = DRIVE.creer_dossier("2026-10-20", racine)      # 15 jours avant JOUR (2026-11-04)
pile = DRIVE.creer_dossier("2026-10-28", racine)       # exactement 7 jours avant JOUR : gardé (pas « plus de » 7)
recent = DRIVE.creer_dossier("2026-10-30", racine)     # 5 jours avant JOUR : gardé
autre = DRIVE.creer_dossier("pas-une-date", racine)    # nom non daté : jamais touché
f_vieux = DRIVE.creer_feuille(racine, "Appels 2026-10-20", "a\n"); f_pile = DRIVE.creer_feuille(racine, "Appels 2026-10-28", "a\n"); f_autre = DRIVE.creer_feuille(racine, "Guide d'appel", "a\n")
etat = A.etat_lire(); etat["google"]["racine"] = racine; A.etat_ecrire(etat)
A.nettoyer_dossiers_drive(A.cfg(), A.etat_lire(), JOUR, DRIVE, False)
verifier(vieux in DRIVE.corbeille and DRIVE.trouver_dossier("2026-10-20", racine) is None, "dossier de 15 jours : mis à la corbeille, plus retrouvé")
verifier(pile not in DRIVE.corbeille and recent not in DRIVE.corbeille and autre not in DRIVE.corbeille, "7 jours exactement, 5 jours, et nom non daté : conservés")
verifier(f_vieux in DRIVE.corbeille and f_pile not in DRIVE.corbeille and f_autre not in DRIVE.corbeille, "tableur « Appels » de 15 jours : corbeille ; 7 jours exactement et autre feuille : conservés")
verifier("corbeille" in A.JOURNAL.read_text(encoding="utf-8").lower(), "le nettoyage est journalisé")
n = len(ALERTES); A.nettoyer_dossiers_drive(A.cfg(), A.etat_lire(), JOUR, DRIVE, False)
verifier(len(ALERTES) == n, "rien à nettoyer la seconde fois : pas d'erreur, pas d'alerte")

print("22bis. Nettoyage branché dans la commande « jour »")
monde(trouves=gros_monde(), config={"envoi_automatique": True})
lancer("preparer", "--jour", JOUR); A.exporter_google(A.cfg(), A.etat_lire(), JOUR, DRIVE, False)
racine = DRIVE.trouver_dossier("Sid"); ancien = DRIVE.creer_dossier("2026-10-01", racine)
code, sortie = lancer("jour", "--jour", JOUR2)
verifier(code == 0 and ancien in DRIVE.corbeille, "jour : le nettoyage tourne aussi pendant le passage normal (vieux dossier mis à la corbeille)")

print("23. 365 jours écoulés : une entreprise confirmée appelée redevient disponible (règle fixe de Liam, 10 nov. 2026)")
monde(trouves=gros_monde(60), config={})
lancer("preparer", "--jour", JOUR)
rows = lire_csv(JOUR)
for l in rows[1:]: l[RES] = "RDV pris"
with open(A.SORTIE / f"liste-sid-{JOUR}.csv", "w", encoding="utf-8-sig", newline="") as fh: csv.writer(fh, delimiter=";").writerows(rows)
lancer("preparer", "--jour", JOUR2)   # le bilan de JOUR2 confirme JOUR dans l'historique (365 jours)
loin = "2027-11-10"   # plus de 365 jours après JOUR (2026-11-04)
code, sortie = lancer("preparer", "--jour", loin, "--a-blanc")
verifier(code == 0 and "100 entreprise(s) de nouveau disponible(s)" in sortie, f"365 jours écoulés : les 100 entreprises de JOUR redeviennent disponibles : {[l for l in sortie.splitlines() if 'disponible' in l]}")
proche = "2026-11-06"   # moins de 365 jours après JOUR : toujours exclues
code, sortie = lancer("preparer", "--jour", proche, "--a-blanc")
verifier(code == 0 and "de nouveau disponible" not in sortie, "moins de 365 jours écoulés : toujours exclues, aucune purge annoncée")

print("24. Historique reconstruit automatiquement au premier lancement, à partir des listes déjà présentes (10 nov. 2026)")
monde(trouves=gros_monde(), config={})
lancer("preparer", "--jour", JOUR)
rows = lire_csv(JOUR)
for l in rows[1:3]: l[RES] = "Non catégorique"   # seules 2 lignes avec un Résultat, le reste pas (jamais inventé)
with open(A.SORTIE / f"liste-sid-{JOUR}.csv", "w", encoding="utf-8-sig", newline="") as fh: csv.writer(fh, delimiter=";").writerows(rows)
A.HISTORIQUE.unlink(missing_ok=True)   # simule une mise à jour de l'agent sur une machine qui a déjà des listes, mais pas encore d'historique
h = A._historique_reconstruire_tout()
verifier(len(h) == 4 and all(v == JOUR for v in h.values()), f"reconstitution : les 2 lignes confirmées appelées de la liste existante (clé + téléphone chacune), datées du fichier ({len(h)})")
A.HISTORIQUE.unlink(missing_ok=True)
code, sortie = lancer("preparer", "--jour", JOUR2, "--a-blanc")   # premier appel réel après la mise à jour : doit reconstituer puis faire son bilan, sans planter
verifier(code == 0, f"preparer après mise à jour (historique absent, listes existantes) : code {code} ({sortie.strip()[:160]})")

print("25. Google : un seul tableur par jour ; les lignes reprises (non appelées ou « À rappeler ») sont dedans, Détail fiche « Reprise de la liste du … »")
monde(trouves=gros_monde(60), config={"envoi_automatique": True})
lancer("preparer", "--jour", JOUR); A.exporter_google(A.cfg(), A.etat_lire(), JOUR, DRIVE, False)
racine = DRIVE.trouver_dossier("Sid"); fid1 = DRIVE.trouver_feuille(racine, f"Appels {JOUR}")
titre, dossier, contenu = DRIVE.feuilles[fid1]; lignes = list(csv.reader(io.StringIO(contenu)))
for k, l in enumerate(lignes[1:]): l[RES] = ("À rappeler" if k < 3 else "Trop cher" if k < 5 else "")
lignes[1][NOTE] = "rappeler après 17 h"
buf = io.StringIO(); csv.writer(buf).writerows(lignes); DRIVE.feuilles[fid1] = (titre, dossier, buf.getvalue())
lancer("preparer", "--jour", JOUR2); A.exporter_google(A.cfg(), A.etat_lire(), JOUR2, DRIVE, False)
fid2 = DRIVE.trouver_feuille(racine, f"Appels {JOUR2}")
verifier(fid2 is not None and len(DRIVE.feuilles) == 2 and DRIVE.trouver_feuille(racine, f"A rappeler {JOUR2}") is None and len(DRIVE.dossiers) == 1, "lendemain : un seul nouveau tableur, aucune feuille « A rappeler », aucun sous-dossier")
c2 = list(csv.reader(io.StringIO(DRIVE.feuilles[fid2][2])))
reprises = {l[NOM] for l in c2[1:] if l[DET].startswith(f"Reprise de la liste du {JOUR}")}
attendues = {l[NOM] for l in lignes[1:] if l[RES] in ("", "À rappeler")}
verifier(reprises == attendues and len(reprises) == 98, f"reprises : non appelées + « À rappeler » ({len(reprises)}), jamais « Trop cher »")
verifier(any("note : rappeler après 17 h" in l[DET] for l in c2[1:] if l[NOM] == lignes[1][NOM]), "la note de Sid suit la ligne reprise")
verifier([_debut_min(l[CR]) for l in c2[1:]] == sorted(_debut_min(l[CR]) for l in c2[1:]), "tableur du lendemain : toujours trié par créneau")

print("26. Type de numéro (fixe / mobile / box), vérification GRATUITE d'un site avant d'inscrire une entreprise (règle de Liam, 10 nov. 2026)")
for brut, attendu in (("02 35 62 41 64", "fixe"), ("01 40 10 00 06", "fixe"), ("05 61 10 00 00", "fixe"), ("06 12 34 56 78", "mobile"), ("07 66 39 19 52", "mobile"), ("09 51 23 45 67", "box")):
    verifier(A.type_telephone(brut) == attendu, f"type_telephone(« {brut} ») -> « {attendu} »")
verifier(A.type_telephone("") == "", "type_telephone('') -> ''")

def _boom(nom, ville): raise AssertionError("chercher_site_web ne doit pas être appelé si site_actuel est déjà connu (tag OpenStreetMap)")
A.chercher_site_web = _boom
url, raison = A.verifier_site({"nom": "Connu", "ville": "Rouen", "cp": "76000", "site_actuel": "https://connu.example/"})
verifier(url == "https://connu.example/" and "OpenStreetMap" in raison, "verifier_site : site déjà connu (tag OpenStreetMap) : jamais de recherche web")

A.chercher_site_web = lambda nom, ville: "https://inconnu.example/"
A.lire_site = lambda url: (url, {}, "une page qui ne parle pas de la bonne ville")
url, raison = A.verifier_site({"nom": "Sans Confirmation", "ville": "Rouen", "cp": "76000", "site_actuel": ""})
verifier(url == "" and raison == "", "verifier_site : page trouvée mais qui ne parle pas de cette entreprise (ni ville ni code postal) : rien n'est affirmé")

A.lire_site = lambda url: (url, {}, "Rouen 76000, bienvenue sur notre site")
url, raison = A.verifier_site({"nom": "Confirmee", "ville": "Rouen", "cp": "76000", "site_actuel": ""})
verifier(url == "https://inconnu.example/" and "recherche web" in raison, "verifier_site : page confirmée (sa ville y figure) : site officiel retenu")

A.lire_site = lambda url: None
url, raison = A.verifier_site({"nom": "Page Illisible", "ville": "Rouen", "cp": "76000", "site_actuel": ""})
verifier(url == "" and raison == "", "verifier_site : page introuvable après la recherche web : rien n'est affirmé")

A.chercher_site_web = lambda nom, ville: ""
url, raison = A.verifier_site({"nom": "Rien Trouve", "ville": "Rouen", "cp": "76000", "site_actuel": ""})
verifier(url == "" and raison == "", "verifier_site : aucun résultat de recherche web : rien n'est affirmé")
A.lire_site = lambda url: None   # retour à la doublure par défaut (aucun site trouvé)

print("26 bis. choisir : avant d'inscrire une entreprise, vérification du site ; exclusion, remplacement et historique si un site officiel est confirmé")
monde(trouves=[], config={})
def _cand(nom, prox): return {"cle": S.cle({"nom": nom, "ville": "Rouen"}), "nom": nom, "ville": "Rouen", "tel": tel(100 + prox), "metier": "restaurant", "brut": "restaurant",
                               "constat": "", "cp": "76000", "site_actuel": "", "dept": "76", "prox": prox}
CANDIDATS_FIXES = [_cand("Has Site", 0), _cand("Pas De Site 1", 1), _cand("Pas De Site 2", 2)]
A_candidats_orig = A.candidats; A.candidats = lambda *a, **k: list(CANDIDATS_FIXES)
A.chercher_site_web = lambda nom, ville: "https://a-un-site.example/" if nom == "Has Site" else ""
A.lire_site = lambda url: (url, {}, "Rouen 76000 bienvenue") if url == "https://a-un-site.example/" else None
hist, trouv = {}, []
conf_test = {**A.cfg(), "repartition": {"restaurant": 1}}
choisies = A.choisir(conf_test, A.etat_lire(), n=2, jour=JOUR, historique=hist, sites_trouves=trouv)
verifier({c["nom"] for c in choisies} == {"Pas De Site 1", "Pas De Site 2"}, f"« Has Site » (site confirmé) écartée, remplacée par les suivantes du même métier : {[c['nom'] for c in choisies]}")
verifier(len(trouv) == 1 and trouv[0]["metier"] == "restaurant" and "site" in trouv[0]["raison"], f"sites_trouves : une entreprise écartée, métier et raison notés, jamais le nom : {trouv}")
cle_exclu = S.cle({"nom": "Has Site", "ville": "Rouen"}); tel_exclu = tel(100)
verifier(hist.get(cle_exclu, {}).get("jour") == JOUR and "site" in hist.get(cle_exclu, {}).get("raison", ""), "historique : la clé de l'entreprise écartée note le jour et la raison")
verifier(hist.get(tel_exclu, {}).get("jour") == JOUR, "historique : son téléphone aussi (exclusion valable même sous un autre nom)")
verifier(cle_exclu != S.cle({"nom": "Pas De Site 1", "ville": "Rouen"}) and S.cle({"nom": "Pas De Site 1", "ville": "Rouen"}) not in hist, "les entreprises retenues ne sont pas dans l'historique")

print("26 ter. --a-blanc : la vérification est prévisualisée (l'entreprise avec un site n'est pas proposée) mais rien n'est noté dans l'historique")
hist2, trouv2 = {}, []
choisies2 = A.choisir(conf_test, A.etat_lire(), n=2, jour=JOUR, historique=hist2, a_blanc=True, sites_trouves=trouv2)
verifier({c["nom"] for c in choisies2} == {"Pas De Site 1", "Pas De Site 2"}, "à blanc : « Has Site » est quand même écartée de la prévisualisation")
verifier(len(trouv2) == 1 and hist2 == {}, "à blanc : l'exclusion est comptée pour le compte rendu, mais rien n'est écrit dans l'historique")
A.candidats = A_candidats_orig; A.chercher_site_web = lambda nom, ville: ""; A.lire_site = lambda url: None   # retour aux doublures par défaut

print("26 quater. Colonne « Type de numéro », constat neutre, et bout en bout (lancer preparer) avec des entreprises écartées pour site trouvé")
AVEC_SITE = {f"Resto Fictif {i}" for i in range(40)}   # TOUS les restaurants fictifs ont un site confirmé : garantit qu'aucun n'est jamais appelé (déterministe, quel que soit l'ordre de
                                                        # proximité), le manque étant comblé par les autres métiers (coiffeur, plombier, électricien), comme en section 3 (métier en manque)
monde(trouves=gros_monde(), config={})
A.chercher_site_web = lambda nom, ville: "https://a-deja-un-site.example/" if nom in AVEC_SITE else ""
A.lire_site = lambda url: (url, {}, "Rouen 76000, notre page d'accueil") if url == "https://a-deja-un-site.example/" else None
code, sortie = lancer("preparer", "--jour", JOUR)
lignes = lire_csv(JOUR); corps = lignes[1:]
noms = {l[1] for l in corps}
verifier(code == 0 and len(corps) == 100, f"malgré les entreprises écartées, la liste a quand même 100 lignes (code {code})")
verifier(not (noms & AVEC_SITE), f"aucune des entreprises avec un site officiel confirmé n'est inscrite : {sorted(noms & AVEC_SITE)}")
verifier(any("écartée" in l and "site officiel" in l for l in sortie.splitlines()), f"la sortie annonce l'exclusion : {[l for l in sortie.splitlines() if 'écart' in l]}")
verifier(not any(l[MET] == "Restaurant" for l in corps), "aucun restaurant dans la liste finale : les 40 avaient tous un site confirmé")
hist = json.loads(A.HISTORIQUE.read_text(encoding="utf-8")); raisons = [v for v in hist.values() if isinstance(v, dict)]
verifier(len(raisons) == 80 and all(v["jour"] == JOUR and "site" in v["raison"] for v in raisons), f"historique : clé + téléphone de chacun des 40 restaurants écartés ({len(raisons)} entrée(s))")
verifier(not any(n in A.JOURNAL.read_text(encoding="utf-8") for n in AVEC_SITE), "journal : aucun nom d'entreprise, même pour une exclusion")
verifier(lignes[0] == COLONNES, f"colonnes du tableur : {lignes[0]}")
verifier(all(l[DET] == A.CONSTAT_NEUTRE for l in corps), "aucun constat vérifié dans ce monde fictif : texte neutre (« à confirmer avec vous »), jamais une affirmation inventée")
A.chercher_site_web = lambda nom, ville: ""; A.lire_site = lambda url: None   # retour aux doublures par défaut

print("27. Robustesse de la vérification de site (règles de Liam, 11 nov. 2026) : délai aléatoire entre deux requêtes web, timeouts")
verifier((A.DELAI_MIN_S, A.DELAI_MAX_S) == (1, 3), "délai aléatoire de 1 à 3 secondes entre deux requêtes web")
verifier(A.TIMEOUT_REQUETE_S == 10, "délai maximum de 10 secondes par requête web")
SOMMEIL.clear()
A.chercher_site_web = lambda nom, ville: "https://inconnu.example/"; A.lire_site = lambda url: (url, {}, "Rouen 76000, bienvenue")
url, raison = A.verifier_site({"nom": "Delai Test", "ville": "Rouen", "cp": "76000", "site_actuel": ""})
verifier(url == "https://inconnu.example/", "verifier_site : site confirmé malgré le délai inséré entre les deux requêtes")
verifier(len(SOMMEIL) == 1 and A.DELAI_MIN_S <= SOMMEIL[0] <= A.DELAI_MAX_S, f"un seul délai (entre chercher_site_web et lire_site, aucun avant la 1re requête) : {SOMMEIL}")
etat_pause = A._etat_verif_defaut(); SOMMEIL.clear()
A._pause_requete(etat_pause); A._pause_requete(etat_pause); A._pause_requete(etat_pause)
verifier(len(SOMMEIL) == 2 and all(A.DELAI_MIN_S <= s <= A.DELAI_MAX_S for s in SOMMEIL), f"_pause_requete : rien avant la 1re requête, un délai 1-3 s avant chacune des suivantes : {SOMMEIL}")
A.chercher_site_web = lambda nom, ville: ""; A.lire_site = lambda url: None; SOMMEIL.clear()   # retour aux doublures par défaut

print("28. 3 blocages/erreurs consécutifs du moteur de recherche : arrêt des vérifications web pour cette liste (reprend avec OpenStreetMap seul), sans faire échouer la liste")
monde(trouves=[], config={})
def _cand_bloc(nom, prox): return {"cle": S.cle({"nom": nom, "ville": "Rouen"}), "nom": nom, "ville": "Rouen", "tel": tel(1500 + prox), "metier": "restaurant", "brut": "restaurant",
                                    "constat": "", "cp": "76000", "site_actuel": "", "dept": "76", "prox": prox}
CAND_BLOQUES = [_cand_bloc(f"Bloc {i}", i) for i in range(5)]
A_candidats_sauve = A.candidats; A.candidats = lambda *a, **k: list(CAND_BLOQUES)
appels_recherche = []
def _bloque(nom, ville):
    appels_recherche.append(nom); raise A.ErreurRecherche("429")
A.chercher_site_web = _bloque
conf_bloc = {**A.cfg(), "repartition": {"restaurant": 1}}
choisies = A.choisir(conf_bloc, A.etat_lire(), n=5, jour=JOUR, historique={}, sites_trouves=[])
verifier(len(choisies) == 5, f"malgré des blocages répétés du moteur de recherche, les 5 entreprises sont quand même retenues (liste non cassée) : {len(choisies)}")
verifier(len(appels_recherche) == A.ECHECS_RECHERCHE_MAX, f"le moteur de recherche n'est plus interrogé après {A.ECHECS_RECHERCHE_MAX} blocages consécutifs (OpenStreetMap seul ensuite) : {len(appels_recherche)} appel(s)")
A.candidats = A_candidats_sauve; A.chercher_site_web = lambda nom, ville: ""   # retour aux doublures par défaut

print("29. Budget de 8 minutes pour la vérification des sites d'une liste : au-delà, les entreprises restantes sont inscrites sans vérification (constat neutre), rien n'est affirmé")
appels_recherche_budget = []
A.chercher_site_web = lambda nom, ville: (appels_recherche_budget.append(nom), "")[1]
etat_budget = A._etat_verif_defaut(); etat_budget["debut"] -= A.BUDGET_VERIF_S + 1   # budget déjà dépassé avant le premier appel
url, raison = A.verifier_site(_cand_bloc("Budget 1", 0), etat_budget)
verifier((url, raison) == ("", ""), "verifier_site : budget dépassé -> rien n'est affirmé (ni site trouvé ni absence de site)")
verifier(appels_recherche_budget == [], f"verifier_site : budget dépassé -> le moteur de recherche n'est plus interrogé du tout : {appels_recherche_budget}")
verifier(etat_budget["budget_signale"] is True, "le dépassement de budget est repéré (signalé une seule fois)")
url2, raison2 = A.verifier_site(_cand_bloc("Budget 2", 1), etat_budget)
verifier((url2, raison2) == ("", "") and appels_recherche_budget == [], "verifier_site : le budget dépassé reste dépassé pour les entreprises suivantes de la même liste")
A.chercher_site_web = lambda nom, ville: ""   # retour à la doublure par défaut

print("30. --hors-ligne : aucune requête réseau (vérification de site simulée), implique --a-blanc")
monde(trouves=gros_monde(), config={})
appels_recherche_hl = []
def _boom_hl(nom, ville): appels_recherche_hl.append(nom); raise AssertionError("chercher_site_web ne doit jamais être appelé en --hors-ligne")
A.chercher_site_web = _boom_hl
code, sortie = lancer("preparer", "--jour", JOUR, "--hors-ligne")
verifier(code == 0 and appels_recherche_hl == [], f"--hors-ligne : code {code}, aucune requête réseau (vérification simulée) : {appels_recherche_hl}")
verifier(not A.chemin(JOUR).exists(), "--hors-ligne : rien n'est écrit, comme --a-blanc")
url3, raison3 = A.verifier_site({"nom": "Hors Ligne", "ville": "Rouen", "cp": "76000", "site_actuel": ""}, A._etat_verif_defaut(hors_ligne=True))
verifier((url3, raison3) == ("", "") and appels_recherche_hl == [], "verifier_site hors_ligne=True : aucune requête, vérification simulée")
A.chercher_site_web = lambda nom, ville: ""   # retour à la doublure par défaut

print("31. chercher_site_web : distingue un blocage/erreur du moteur de recherche (ErreurRecherche) d'une recherche qui n'a simplement rien trouvé")
class _RepVide:
    def __enter__(s): return s
    def __exit__(s, *a): return False
    def read(s, *a): return b""
def _ouvrir_429(rq, timeout=0): raise urllib.error.HTTPError("u", 429, "trop vite", {}, None)
try:
    CHERCHER_SITE_WEB_REEL("Nom", "Ville", ouvrir=_ouvrir_429); verifier(False, "chercher_site_web : un blocage HTTP 429 doit lever ErreurRecherche")
except A.ErreurRecherche: verifier(True, "chercher_site_web : blocage HTTP 429 -> ErreurRecherche")
def _ouvrir_503(rq, timeout=0): raise urllib.error.HTTPError("u", 503, "occupé", {}, None)
try:
    CHERCHER_SITE_WEB_REEL("Nom", "Ville", ouvrir=_ouvrir_503); verifier(False, "chercher_site_web : un blocage HTTP 503 doit lever ErreurRecherche")
except A.ErreurRecherche: verifier(True, "chercher_site_web : blocage HTTP 503 -> ErreurRecherche")
def _ouvrir_404(rq, timeout=0): raise urllib.error.HTTPError("u", 404, "introuvable", {}, None)
try:
    r = CHERCHER_SITE_WEB_REEL("Nom", "Ville", ouvrir=_ouvrir_404)
    verifier(r == "", "chercher_site_web : une erreur HTTP non bloquante (404) n'est pas un blocage : chaîne vide, pas d'exception")
except A.ErreurRecherche: verifier(False, "chercher_site_web : 404 ne doit pas lever ErreurRecherche (ce n'est pas un blocage du moteur de recherche)")
def _ouvrir_reseau(rq, timeout=0): raise urllib.error.URLError("réseau coupé")
try:
    CHERCHER_SITE_WEB_REEL("Nom", "Ville", ouvrir=_ouvrir_reseau); verifier(False, "chercher_site_web : une panne réseau doit lever ErreurRecherche")
except A.ErreurRecherche: verifier(True, "chercher_site_web : panne réseau (URLError) -> ErreurRecherche")
r = CHERCHER_SITE_WEB_REEL("Nom", "Ville", ouvrir=lambda rq, timeout=0: _RepVide())
verifier(r == "", "chercher_site_web : page vide, aucun résultat exploitable : chaîne vide, pas d'exception")

monde(trouves=[], config={})   # ne laisse aucun fichier temporaire dans un état inattendu pour la suite

print()
if echecs: print(f"{echecs} ÉCHEC(S)"); sys.exit(1)
print("OK : tous les tests de l'agent appels-sid passent")
