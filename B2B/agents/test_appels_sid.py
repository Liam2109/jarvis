#!/usr/bin/env python3
"""Tests silencieux de l'agent appels-sid : AUCUN réseau, aucun envoi, fichiers temporaires (rien dans le dépôt).  python agents\\test_appels_sid.py
Écrits AVANT le code (appels-sid.py). Règles de Liam : chaque matin une liste de 50 à 60 entreprises JAMAIS appelées pour Sid (restaurants, coiffeurs, plombiers-chauffagistes, électriciens ;
ni fleuriste, ni boulangerie, ni garage) ; téléphone valide ; ni STOP ni exclus ; jamais deux fois la même entreprise (état) ; CSV docs\\sid\\liste-sid-AAAA-MM-JJ.csv ; commandes
preparer / etat / annuler / --a-blanc ; aucun envoi, aucun partage, aucun appel API."""
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
_AVANT_REEL = {n: _etat_fichier(ICI / n) for n in ("appels-sid-etat.json", "appels-sid.verrou", "appels-sid-journal.log")}
import prospection as P, suivi as S
spec = importlib.util.spec_from_file_location("appels_sid", ICI / "appels-sid.py"); A = importlib.util.module_from_spec(spec); spec.loader.exec_module(A)

def reseau(*a, **k): raise AssertionError("appel réseau interdit dans les tests")
urllib.request.urlopen = reseau; socket.create_connection = reseau; P.lien_accessible = reseau   # aucune page exemple n'est ouverte : le lien est lu dans liens-metiers.json

tmp = Path(tempfile.mkdtemp(prefix="appels-sid-test-"))
(tmp / "docs").mkdir(); (tmp / "agents").mkdir()
A.ICI, A.RACINE, A.SORTIE = tmp / "agents", tmp, tmp / "docs" / "sid"
A.CONFIG, A.ETAT, A.VERROU, A.ARRET, A.JOURNAL, A.MAPS = (tmp / "agents" / "appels-sid-config.json", tmp / "agents" / "appels-sid-etat.json", tmp / "agents" / "appels-sid.verrou",
                                                          tmp / "agents" / "appels-sid.arret", tmp / "agents" / "appels-sid-journal.log", tmp / "prospects_maps.csv")
P.TROUVES, P.DOCS, P.ICI, P.ETAT, S.FICHIER = tmp / "prospection-trouves.csv", tmp / "docs", tmp / "agents", tmp / "agents" / "prospection-etat.json", tmp / "suivi-prospects.csv"
LIENS = {"plombier-chauffagiste": "https://exemple-plombier.example/", "electricien": "https://exemple-electricien.example/", "restaurant": "https://exemple-restaurant.example/",
         "coiffeur": "https://exemple-coiffeur.example/", "fleuriste": "https://exemple-fleuriste.example/", "boulangerie": "https://exemple-boulangerie.example/", "garage": "https://exemple-garage.example/"}
(tmp / "agents" / "liens-metiers.json").write_text(json.dumps(LIENS), encoding="utf-8")


# --- doublures : aucun accès réseau, Google, Discord ni tâche Windows réels -------------------------------------------------------------------------------
import google_sheets as GS
class FauxDrive:
    """Même interface que google_sheets.Drive : dossiers, feuilles, partages gardés en mémoire."""
    def __init__(s, compte="contact.lmsites@gmail.com"): s.dossiers, s.feuilles, s.partages, s.n, s.panne, s.appels, s.compte_reel, s.corbeille = {}, {}, [], 0, False, 0, compte, set()
    def _nouveau(s, p): s.n += 1; return f"{p}{s.n}"
    def _controle(s):
        s.appels += 1
        if s.panne: raise GS.ErreurDrive(503, "panne simulée")
    def compte(s): s._controle(); return s.compte_reel
    def trouver_dossier(s, nom, parent=None): s._controle(); return next((i for i, (n, p) in s.dossiers.items() if n == nom and p == parent and i not in s.corbeille), None)
    def creer_dossier(s, nom, parent=None): s._controle(); i = s._nouveau("D"); s.dossiers[i] = (nom, parent); return i
    def trouver_feuille(s, dossier, titre): s._controle(); return next((i for i, (t, d, _) in s.feuilles.items() if t == titre and d == dossier), None)
    def creer_feuille(s, dossier, titre, contenu): s._controle(); i = s._nouveau("F"); s.feuilles[i] = (titre, dossier, contenu); return i
    def partager(s, dossier, email): s._controle(); s.partages.append((dossier, email))
    def lister_dossiers(s, parent): s._controle(); return [(i, n) for i, (n, p) in s.dossiers.items() if p == parent and i not in s.corbeille]
    def mettre_corbeille(s, id_): s._controle(); s.corbeille.add(id_)
DRIVE = FauxDrive()
ALERTES, EXEC, SOMMEIL = [], [], []
def faux_alerte(texte): ALERTES.append(texte); return True
def faux_executer(cmd): EXEC.append(cmd); return 0, ""
def faux_dormir(s): SOMMEIL.append(s)
A.appel_reseau = reseau; A.alerter_discord = faux_alerte; A.executer = faux_executer; A.dormir = faux_dormir; A.ouvrir_drive = lambda conf: DRIVE
A.PROSPECTION_CONFIG = tmp / "agents" / "prospection-config.json"
A.appel_sirene = lambda dept, naf, page: {"results": []}; A.lire_site = lambda url: None      # SIRENE et les sites publics : jamais de réseau ici (section 14 bis : doublures complètes)
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
    for f in (A.ETAT, A.VERROU, A.ARRET, A.JOURNAL, P.ETAT): f.unlink(missing_ok=True)
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
    """Réserve large : n restaurants, n coiffeurs, n plombiers, n électriciens, plus des métiers interdits."""
    t = []
    for i in range(n):
        t.append(trouve(f"Resto Fictif {i}", "restaurant", f"Ville{i % 7}", tel(100 + i), note="carte absente du site" if i == 0 else ""))
        t.append(trouve(f"Coiff Fictif {i}", "coiffeur", f"Ville{i % 7}", tel(300 + i)))
        t.append(trouve(f"Plomb Fictif {i}", "plombier-chauffagiste", f"Ville{i % 7}", tel(500 + i)))
        t.append(trouve(f"Elec Fictif {i}", "électricien", f"Ville{i % 7}", tel(700 + i)))
        t.append(trouve(f"Fleur Fictif {i}", "fleuriste", "Rouen", tel(900 + i))); t.append(trouve(f"Boul Fictif {i}", "boulangerie", "Rouen", tel(1100 + i))); t.append(trouve(f"Gar Fictif {i}", "garage automobile", "Rouen", tel(1300 + i)))
    return t

JOUR = "2026-11-04"; JOUR2 = "2026-11-05"
COLONNES = ["#", "Nom", "Ville", "Téléphone", "Métier", "Créneau conseillé", "Constat vérifié", "Page d'exemple", "Appelé", "Répondu", "Rendez-vous pris", "Refus", "Remarque"]

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
verifier(cles == {"Bon Resto", "Bon Coiffeur", "Bon Plombier", "Bon Electricien", "Suivi A Contacter", "Maps Elec", "Liste Resto", "Deja Rendu A Liam"}, f"seuls les bons candidats sont retenus : {sorted(cles)}")
for interdit, raison in (("Une Fleuriste", "fleuriste"), ("Une Boulangerie", "boulangerie"), ("Un Garage", "garage"), ("Sans Tel", "sans téléphone"), ("Tel Faux", "téléphone invalide (0800)"), ("Hors Zone", "hors zone"),
                         ("Refus Resto", "refus"), ("Stop Resto", "STOP"), ("Exclu Resto", "exclu"), ("Ecarte Resto", "écarté"), ("Prepare Resto", "déjà préparé pour l'e-mail"), ("Cp Lointain", "code postal hors zone"), ("Mail Exclu", "e-mail dans exclus-emails.json"), ("Cle Exclue", "exclu (état de prospection)"), ("Deja Appele", "déjà appelé (case cochée)"), ("Meme Tel", "même téléphone qu'une autre ligne"), ("Suivi Stop", "STOP du suivi"), ("Suivi Envoye", "déjà contacté par e-mail"),
                         ("Suivi Repondu", "a répondu"), ("Maps Couvreur", "métier non demandé (couvreur)")):
    verifier(interdit not in cles, f"écarté : {interdit} ({raison})")
verifier(len([c for c in A.choisir(A.cfg(), A.etat_lire()) if c["nom"] == "Suivi A Contacter"]) == 1, "même entreprise présente dans deux fichiers (suivi + maps) : une seule ligne")

for repris in ("Liste Resto", "Deja Rendu A Liam"): verifier(repris in cles, f"reprise : {repris} (listée pour Liam mais jamais appelée)")
print("3. Taille de la liste (50 à 60) et mélange des métiers")
monde(trouves=gros_monde(), config={})
ch = A.choisir(A.cfg(), A.etat_lire())
verifier(A.cfg()["par_liste"] == 55 and len(ch) == 55, f"par défaut : 55 lignes (obtenu {len(ch)})")
par = {}
for c in ch: par[c["metier"]] = par.get(c["metier"], 0) + 1
verifier(set(par) == {"restaurant", "coiffeur", "plombier", "electricien"}, f"quatre métiers présents : {par}")
verifier(all(v >= 8 for v in par.values()), f"mélange raisonnable (au moins 8 par métier) : {par}")
verifier(len({c["cle"] for c in ch}) == len(ch) and len({c["tel"] for c in ch}) == len(ch), "aucune entreprise ni aucun numéro en double")
for demande, attendu in ((30, 50), (70, 60), (50, 50), (60, 60), ("abc", 55)):
    monde(trouves=gros_monde(), config={"par_liste": demande}); verifier(len(A.choisir(A.cfg(), A.etat_lire())) == attendu, f"par_liste = {demande!r} -> {attendu} lignes (bornes 50 à 60)")
monde(trouves=[trouve(f"Resto Seul {i}", "restaurant", "Rouen", tel(100 + i)) for i in range(70)] + [trouve("Un Coiffeur", "coiffeur", "Rouen", tel(900))], config={})
ch = A.choisir(A.cfg(), A.etat_lire())
verifier(len(ch) == 55 and sum(1 for c in ch if c["metier"] == "restaurant") == 54, "un métier en manque : complété par les métiers disponibles (pas de liste réduite sans raison)")
monde(trouves=[trouve(f"Resto Seul {i}", "restaurant", "Rouen", tel(100 + i)) for i in range(12)], config={})
verifier(len(A.choisir(A.cfg(), A.etat_lire())) == 12, "réserve trop petite : on sort ce qu'il y a (le rapport le signale)")

print("4. Créneaux : bâtiment, puis coiffeurs, puis restaurants")
monde(trouves=gros_monde(), config={})
ch = A.choisir(A.cfg(), A.etat_lire()); ordre = [c["metier"] for c in ch]
rang = {"plombier": 0, "electricien": 0, "coiffeur": 1, "restaurant": 2}
verifier([rang[m] for m in ordre] == sorted(rang[m] for m in ordre), "lignes classées dans l'ordre de la journée : bâtiment, coiffeurs, restaurants")
verifier("avant 9 h" in A.CRENEAUX["plombier"] and "17 h" in A.CRENEAUX["electricien"] and "17 h" in A.CRENEAUX["plombier"], "artisans du bâtiment : avant 9 h ou vers 17 h")
verifier("matinée" in A.CRENEAUX["coiffeur"] and "14 h" in A.CRENEAUX["restaurant"] and "16 h" in A.CRENEAUX["restaurant"], "coiffeurs : milieu de matinée ; restaurants : 14 h – 16 h")

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
verifier(len(corps) == 55 and [l[0] for l in corps] == [str(i) for i in range(1, 56)], "55 lignes numérotées de 1 à 55")
verifier(all(len(l) == len(COLONNES) for l in corps), "toutes les lignes ont toutes les colonnes")
verifier(all(l[8] == l[9] == l[10] == l[11] == l[12] == "" for l in corps), "appelé / répondu / rendez-vous pris / refus / remarque : vides (pas de colonne STOP)")
verifier(all(re.fullmatch(r"0\d( \d\d){4}", l[3]) for l in corps), "téléphones au format « 02 35 62 41 64 »")
verifier(all(l[7] == "" for l in corps if l[4] == "Restaurant"), "restaurant : aucun lien de page d'exemple (numéro seulement)")
verifier(all(l[7] == LIENS["coiffeur"] for l in corps if l[4] == "Coiffeur") and all(l[7] == LIENS["plombier-chauffagiste"] for l in corps if l[4] == "Plombier-chauffagiste")
         and all(l[7] == LIENS["electricien"] for l in corps if l[4] == "Électricien"), "coiffeur / plombier / électricien : lien de liens-metiers.json")
verifier({l[4] for l in corps} == {"Restaurant", "Coiffeur", "Plombier-chauffagiste", "Électricien"}, "métiers affichés en clair, sans fleuriste, boulangerie ni garage")
verifier(all(l[5] for l in corps), "créneau conseillé renseigné pour chaque ligne")
resto0 = [l for l in corps if l[1] == "Resto Fictif 0"][0]; autre = [l for l in corps if l[1] == "Coiff Fictif 3"]
verifier(resto0[6] == "carte absente du site" and all(l[6] == "" for l in corps if l[1] != "Resto Fictif 0"), "constat : seulement celui vérifié (note_besoin), jamais inventé")
verifier("liste-sid-" + JOUR in sortie and "55" in sortie, "la sortie dit le fichier et le nombre de lignes")
verifier(not any(f.name.endswith(".md") for f in A.SORTIE.iterdir()), "un seul fichier par liste (CSV)")

print("6. Formules de tableur neutralisées")
monde(trouves=[trouve("=SOMME(1+1) Resto", "restaurant", "Rouen", tel(100)), trouve("+Plomb @x", "plombier-chauffagiste", "Rouen", tel(500)), trouve("Nom; avec \"guillemets\"\net saut", "coiffeur", "Rouen", tel(300))], config={})
code, _ = lancer("preparer", "--jour", JOUR); l = lire_csv(JOUR)
noms = [x[1] for x in l[1:]]
verifier(code == 0 and all(not n.startswith(("=", "+", "-", "@")) for n in noms), f"nom commençant par = + - @ neutralisé : {noms}")
verifier(any("avec" in n and "\n" not in n for n in noms), "point-virgule, guillemets et saut de ligne : ligne CSV intacte")
verifier(all(len(x) == len(COLONNES) for x in l), "aucune colonne décalée")

print("7. État : jamais la même entreprise deux fois")
monde(trouves=gros_monde(), config={})
lancer("preparer", "--jour", JOUR)
etat = json.loads(A.ETAT.read_text(encoding="utf-8"))
verifier(len(etat["sorties"]) == 55 and etat["listes"][JOUR]["nombre"] == 55, "appels-sid-etat.json : 55 entreprises marquées, liste du jour notée")
verifier("tel" not in json.dumps(etat) and not re.search(r"\d\d \d\d \d\d \d\d", json.dumps(etat)), "l'état ne contient aucun numéro de téléphone")
avant = A.ETAT.read_bytes(); csv1 = (A.SORTIE / f"liste-sid-{JOUR}.csv").read_bytes()
code, sortie = lancer("preparer", "--jour", JOUR)
verifier(code == 2 and "déjà" in sortie and A.ETAT.read_bytes() == avant and (A.SORTIE / f"liste-sid-{JOUR}.csv").read_bytes() == csv1, "deuxième preparer le même jour : refusé, rien écrasé, rien marqué en plus")
code, _ = lancer("preparer", "--jour", JOUR2)
n1 = {l[1] for l in lire_csv(JOUR)[1:]}; n2 = {l[1] for l in lire_csv(JOUR2)[1:]}
verifier(code == 0 and not (n1 & n2), "le lendemain : aucune entreprise déjà sortie ne revient")
tel1 = {l[3] for l in lire_csv(JOUR)[1:]}; tel2 = {l[3] for l in lire_csv(JOUR2)[1:]}
verifier(not (tel1 & tel2), "ni le même numéro")
etat = json.loads(A.ETAT.read_text(encoding="utf-8")); verifier(len(etat["sorties"]) == 110, "110 entreprises marquées après deux jours")
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
code, _ = lancer("preparer", "--jour", JOUR); verifier(code == 0 and len(lire_csv(JOUR)) == 56, "après un à blanc, le vrai preparer sort bien les mêmes entreprises (rien n'a été consommé)")
verifier(lancer("etat", "--a-blanc")[0] == 0, "etat accepte aussi --a-blanc")

print("9. etat : compte restant")
monde(trouves=gros_monde(40), config={})
code, sortie = lancer("etat"); verifier(code == 0 and "aucune liste" in sortie.lower() and "160" in sortie, f"avant toute liste : réserve = 160 (4 métiers x 40) : {sortie.strip().splitlines()[:3]}")
lancer("preparer", "--jour", JOUR)
code, sortie = lancer("etat")
verifier("105" in sortie and JOUR in sortie and "55" in sortie, "après une liste de 55 : reste 105, liste du jour citée")
verifier(re.search(r"jour", sortie.lower()) is not None and "2" in sortie, "nombre de jours de réserve indiqué")
verifier(not re.search(r"\d\d \d\d \d\d \d\d \d\d", sortie), "etat n'affiche aucun numéro de téléphone")
verifier(re.search(r"restaurant\D+\d+", sortie, re.I) is not None, "reste par métier")

print("10. annuler : libère une liste non utilisée")
monde(trouves=gros_monde(), config={})
lancer("preparer", "--jour", JOUR); code1 = lire_csv(JOUR)
code, sortie = lancer("annuler", JOUR, "--a-blanc")
verifier(code == 0 and "à blanc" in sortie.lower() and (A.SORTIE / f"liste-sid-{JOUR}.csv").exists() and len(json.loads(A.ETAT.read_text(encoding="utf-8"))["sorties"]) == 55, "annuler --a-blanc : rien changé")
code, sortie = lancer("annuler", JOUR)
etat = json.loads(A.ETAT.read_text(encoding="utf-8"))
verifier(code == 0 and etat["sorties"] == {} and JOUR not in etat["listes"], "liste non utilisée : les 55 entreprises sont libérées")
verifier(not (A.SORTIE / f"liste-sid-{JOUR}.csv").exists() and (A.SORTIE / f"liste-sid-{JOUR}.annulee.csv").exists(), "le CSV n'est pas supprimé : renommé .annulee.csv")
code, _ = lancer("preparer", "--jour", JOUR); verifier(code == 0 and lire_csv(JOUR) == code1, "preparer à nouveau le même jour : mêmes entreprises (elles sont libres)")
verifier(lancer("annuler", "2026-01-01")[0] == 2, "annuler une date sans liste : erreur, rien changé")
verifier(lancer("annuler")[0] == 0 and not (A.SORTIE / f"liste-sid-{JOUR}.csv").exists(), "annuler sans date : la liste la plus récente")
lancer("preparer", "--jour", JOUR)
rows = lire_csv(JOUR); rows[3][8] = "x"; rows[5][12] = "rappeler jeudi"
with open(A.SORTIE / f"liste-sid-{JOUR}.csv", "w", encoding="utf-8-sig", newline="") as fh: csv.writer(fh, delimiter=";").writerows(rows)
code, sortie = lancer("annuler", JOUR)
verifier(code == 2 and "utilisée" in sortie and (A.SORTIE / f"liste-sid-{JOUR}.csv").exists() and len(json.loads(A.ETAT.read_text(encoding="utf-8"))["sorties"]) == 55, "liste déjà commencée (case ou remarque remplie) : annulation refusée")
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
verifier(JOUR in j and "55" in j, "journal : une ligne par action")
verifier(not re.search(r"\d\d \d\d \d\d \d\d \d\d|@", j) and "Fictif" not in j, "journal : aucun numéro, e-mail ni nom d'entreprise")
src = (ICI / "appels-sid.py").read_text(encoding="utf-8")
verifier(not re.search(r"smtplib|send_message|messages\(\)\.send|gmail_api|stripe|webbrowser|os\.system|shell=True", src, re.I), "appels-sid.py : aucun envoi d'e-mail ni de message à une entreprise, aucun Stripe, pas de shell")
verifier(not re.search(r"print\([^)]*(jeton|token|password|mot de passe)", src, re.I), "aucun jeton ni mot de passe affiché")
cfg_reel = json.loads((ICI / "appels-sid-config.json").read_text(encoding="utf-8-sig"))
verifier(cfg_reel.get("envoi_automatique") is True, "appels-sid-config.json : envoi_automatique = true (activé pour de vrai par Liam le 09/11/2026, état voulu et définitif)")
verifier(A.EMAIL.match(cfg_reel.get("partager_avec") or ""), "appels-sid-config.json : partager_avec renseigné (adresse valide)")
verifier(cfg_reel.get("jours_appel") == ["lundi", "mardi", "vendredi"], "appels-sid-config.json : jours_appel = lundi, mardi, vendredi")
verifier(all(_etat_fichier(ICI / n) == _AVANT_REEL[n] for n in ("appels-sid-etat.json", "appels-sid.verrou", "appels-sid-journal.log")), "les tests n'ont rien écrit dans le dépôt (un fichier d'agent déjà présent, car l'agent tourne pour de vrai sur le serveur, reste inchangé)")
verifier(not (ICI.parent / "docs" / "sid").exists() or not list((ICI.parent / "docs" / "sid").glob("liste-sid-2026-11-0*.csv")), "aucun CSV de test dans docs\\sid du dépôt")

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
TYPE_REQ = re.compile(r'"(?:craft|shop|amenity)"="(\w+)"')
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
monde(trouves=gros_monde(80), config={"cible_reserve": 220}); FO.__init__(); lancer("sourcer", "--jour", JOUR)
verifier(FO.requetes == [], "réserve déjà au niveau de la cible : aucune requête")
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

# une requête Overpass par département et par métier, pauses, nouvelles tentatives
monde(trouves=[], config={"sourcing_requetes_max": 30, "sirene_actif": False, "cible_reserve": 2000}); FO.__init__(); lancer("sourcer", "--jour", JOUR)
deps_req = [re.search(r'"ref:INSEE"="(\d\d)"', r).group(1) for r in FO.requetes]; types_req = [TYPE_REQ.search(r).group(1) for r in FO.requetes]
verifier(len(FO.requetes) == 20 and sorted(set(deps_req)) == ["14", "27", "50", "61", "76"] and deps_req[:4] == ["76"] * 4 and all(deps_req.count(d) == 4 for d in set(deps_req)), f"20 requêtes : une par département et par métier, Seine-Maritime d'abord : {deps_req}")
verifier(all("(around:" not in r and "(area.a)" in r and 'area["boundary"="administrative"]["ref:INSEE"=' in r for r in FO.requetes), "chaque requête cible la relation OpenStreetMap du département (area ref:INSEE), jamais un cercle")
verifier(all("[timeout:90]" in r for r in FO.requetes), "délai Overpass de 90 s par requête (requêtes découpées : jamais toute la région d'un coup)")
verifier(any('"craft"="hvac"' in r for r in FO.requetes) and any('"amenity"="fast_food"' in r for r in FO.requetes), "plombier-chauffagiste : craft=plumber et craft=hvac ; restaurant : restaurant et fast_food")
verifier(SOMMEIL == [15] * 19, f"15 s entre deux requêtes Overpass, jamais avant la première : {len(SOMMEIL)} pauses")
monde(trouves=[], config={"sourcing_requetes_max": 30, "sirene_actif": False, "cible_reserve": 2000}); FO.__init__(); lancer("sourcer", "--jour", JOUR, "--dept", "27")
verifier(len(FO.requetes) == 4 and all('"ref:INSEE"="27"' in r for r in FO.requetes), "--dept 27 : seulement les quatre requêtes de l'Eure")
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
monde(trouves=gros_monde(30), config={"par_liste": 50}); lancer("preparer", "--jour", JOUR)
donnes = {l[3] for l in lire_csv(JOUR)[1:]}; verifier(len(donnes) == 50, "liste du jour préparée (50 numéros)")
nom_donne = next(l[1] for l in lire_csv(JOUR)[1:])
P.ecrire_trouves(P.lire_trouves() + [trouve("Autre Nom Meme Numero", "restaurant", "Autre Ville", next(iter(donnes)))], P.TROUVES)
verifier("Autre Nom Meme Numero" not in {c["nom"] for c in A.candidats(A.etat_lire())}, "un numéro déjà donné à Sid ne ressort jamais, même sous un autre nom d'entreprise")
S.ecrire(S.lire() + [suivi("Nom Different Stop", "restaurant", "Autre Ville", "06 99 88 77 66", statut="STOP")])
P.ecrire_trouves(P.lire_trouves() + [trouve("Encore Un Nom", "restaurant", "Ville X", "06 99 88 77 66")], P.TROUVES)
verifier("Encore Un Nom" not in {c["nom"] for c in A.candidats(A.etat_lire())}, "le numéro d'une entreprise qui a dit STOP n'est jamais redonné, même sous un autre nom")
code, _ = lancer("annuler", JOUR, "--force"); P.ecrire_trouves([l for l in P.lire_trouves() if l["nom"] != "Autre Nom Meme Numero"], P.TROUVES)
verifier(code == 0 and "Autre Nom Meme Numero" not in {c["nom"] for c in A.candidats(A.etat_lire())} and len(donnes & {c["tel"] for c in A.candidats(A.etat_lire())}) == 50, "après annulation de la liste : les numéros sont de nouveau disponibles")
t_dep = [trouve(f"Plomb Calvados {i}", "plombier-chauffagiste", "Caen", tel(2000 + i), cp="14000") for i in range(3)] + [trouve(f"Resto Manche {i}", "restaurant", "Saint-Lô", tel(2100 + i), cp="50000") for i in range(2)] + \
        [trouve("Coiff Rouen", "coiffeur", "Rouen", tel(2200), cp="76000"), trouve("Elec Sans Cp", "électricien", "Quelque Part", tel(2300), cp="")]
monde(trouves=t_dep, config={"par_liste": 55}); code, sortie = lancer("etat")
verifier(code == 0 and "Réserve par métier et par département" in sortie and "Calvados 14" in sortie and "Manche 50" in sortie and "Seine-Maritime 76" in sortie and "Orne 61" in sortie and "Eure 27" in sortie, "etat : tableau métier x département (les cinq départements normands)")
verifier(re.search(r"Plombier-chauffagiste\s+3\s+0\s+0\s+0\s+0\s+3|Plombier-chauffagiste\s+[\d\s]*3", sortie) is not None and "inconnu" in sortie, "le tableau donne le nombre par métier et par département, et une colonne pour les codes postaux inconnus")
verifier("= 0 jour(s) à 55 numéros par jour" in sortie, f"jours de réserve à 55 numéros par jour (7 numéros : 0 jour) : {[l for l in sortie.splitlines() if 'jour(s)' in l]}")
monde(trouves=gros_monde(30), config={"par_liste": 55}); code, sortie = lancer("etat"); verifier("= 2 jour(s) à 55 numéros par jour" in sortie or "= 3 jour(s) à 55 numéros par jour" in sortie, "120 numéros / 55 par jour : 2 jours de réserve, dit en toutes lettres")
monde(trouves=gros_monde(30), config={"sourcing_requetes_max": 1, "sirene_actif": False}); FO.__init__(); FO.fixes = [[]]; code, sortie = lancer("sourcer", "--jour", JOUR, "--a-blanc")
verifier("Réserve par métier et par département" in sortie and "jour(s) à 55 numéros par jour" in sortie, "fin de `sourcer` : la réserve par métier et par département et les jours de réserve sont affichés")
monde(trouves=gros_monde(30), config={"sirene_actif": False, "cible_reserve": 100}); FO.__init__(); code, sortie = lancer("jour", "--jour", JOUR)
verifier("Réserve par métier et par département" in sortie and "jour(s) à 55 numéros par jour" in sortie, "fin de `jour` : même tableau")

print("14 quater. Mode simulation : aucun réseau, données fictives, rien d'écrit")
orig = (A.appel_reseau, A.appel_sirene, A.lire_site, A.evaluer_site, A.dormir)
monde(trouves=[], config={"sourcing_requetes_max": 20, "sirene_requetes_max": 20, "sirene_sites_max": 40, "cible_reserve": 2000}); avant = P.lire_trouves()
code, sortie = lancer("sourcer", "--simulation", "--jour", JOUR)
verifier(code == 0 and P.lire_trouves() == avant and not A.ETAT.exists() and not A.JOURNAL.exists() and not list(tmp.glob("*.tmp")), "sourcer --simulation : aucun accès réseau (urlopen interdit dans ce test), rien d'écrit")
verifier("20 requête(s) Overpass" in sortie and re.search(r"[1-9]\d* appel\(s\) SIRENE", sortie) and re.search(r"dont SIRENE : [1-9]", sortie), f"simulation : les 20 requêtes (5 départements x 4 métiers) et SIRENE tournent : {[l for l in sortie.splitlines() if l.startswith('Sourcing')]}")
verifier("Réserve par métier et par département" in sortie and "Seine-Maritime 76" in sortie and "jour(s) à 55 numéros par jour" in sortie, "simulation : le tableau final de réserve est affiché")
A.appel_reseau, A.appel_sirene, A.lire_site, A.evaluer_site, A.dormir = orig
code, sortie = lancer("sourcer", "--simulation", "--dept", "50", "--jour", JOUR); verifier(code == 0 and "4 requête(s) Overpass" in sortie, "simulation limitée à un département : 4 requêtes")
A.appel_reseau, A.appel_sirene, A.lire_site, A.evaluer_site, A.dormir = orig
src2 = (ICI / "appels-sid.py").read_text(encoding="utf-8")
verifier("recherche-entreprises.api.gouv.fr" in (ICI / "prospection.py").read_text(encoding="utf-8") and "google.com/maps" not in src2 and "pagesjaunes" not in src2.lower() and "googleapis.com/maps" not in src2 and "places.googleapis" not in src2, "sources : OpenStreetMap (Overpass) et l'API officielle SIRENE seulement ; ni Google Maps ni Pages Jaunes")
A.appel_reseau = reseau; A.appel_sirene = lambda dept, naf, page: {"results": []}; A.lire_site = lambda url: None

print("15. Google Drive : dossier « Sid » > date, feuille du jour, partage")
monde(trouves=gros_monde(), config={"envoi_automatique": True})
lancer("preparer", "--jour", JOUR); A.exporter_google(A.cfg(), A.etat_lire(), JOUR, DRIVE, False)
racine = DRIVE.trouver_dossier("Sid"); jour_d = DRIVE.trouver_dossier(JOUR, racine)
verifier(racine and jour_d and DRIVE.dossiers[jour_d] == (JOUR, racine) and DRIVE.dossiers[racine] == ("Sid", None), "dossier « Sid » à la racine du Drive, puis « AAAA-MM-JJ » dedans")
fid = DRIVE.trouver_feuille(jour_d, f"Liste d'appels {JOUR}"); verifier(fid is not None, "feuille « Liste d'appels AAAA-MM-JJ » dans le dossier du jour")
contenu = list(csv.reader(io.StringIO(DRIVE.feuilles[fid][2]))); verifier(contenu == lire_csv(JOUR), "la feuille a exactement le contenu du CSV")
verifier("STOP" not in contenu[0] and len(contenu[0]) == 13, "13 colonnes, pas de colonne STOP")
verifier(json.loads(A.ETAT.read_text(encoding="utf-8"))["google"][JOUR]["feuille"] == fid, "état : identifiants du dossier et de la feuille")
n_avant = (len(DRIVE.dossiers), len(DRIVE.feuilles)); A.exporter_google(A.cfg(), A.etat_lire(), JOUR, DRIVE, False)
verifier((len(DRIVE.dossiers), len(DRIVE.feuilles)) == n_avant, "dossier du jour déjà là : rien recréé, rien écrasé")
etat = A.etat_lire(); etat["google"] = {}; A.etat_ecrire(etat); A.exporter_google(A.cfg(), A.etat_lire(), JOUR, DRIVE, False)
verifier((len(DRIVE.dossiers), len(DRIVE.feuilles)) == n_avant, "état perdu : le Drive est consulté, le dossier existant est reconnu (aucun doublon)")
DRIVE.feuilles.pop(fid); etat = A.etat_lire(); etat["google"] = {}; A.etat_ecrire(etat); A.exporter_google(A.cfg(), A.etat_lire(), JOUR, DRIVE, False)
verifier(len(DRIVE.dossiers) == n_avant[0] and len(DRIVE.feuilles) == 1, "dossier présent mais feuille manquante : seule la feuille est créée")
lancer("preparer", "--jour", JOUR2); A.exporter_google(A.cfg(), A.etat_lire(), JOUR2, DRIVE, False)
verifier(sum(1 for n, p in DRIVE.dossiers.values() if n == "Sid") == 1 and DRIVE.trouver_dossier(JOUR2, racine), "le lendemain : « Sid » réutilisé, nouveau dossier de date")
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
verifier(DRIVE.partages == [] and DRIVE.trouver_dossier(JOUR, DRIVE.trouver_dossier("Sid")), "adresse invalide : rien partagé, le dossier et la feuille sont quand même créés")
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
verifier(code == 0 and DRIVE.trouver_feuille(DRIVE.trouver_dossier(JOUR, DRIVE.trouver_dossier("Sid")), f"Liste d'appels {JOUR}"), "le passage suivant rattrape Google (la liste existante n'est ni refaite ni re-marquée)")
verifier(len(json.loads(A.ETAT.read_text(encoding="utf-8"))["sorties"]) == 55, "toujours 55 entreprises marquées (pas de seconde liste)")
A.appel_reseau = reseau
code, sortie = lancer("jour", "--jour", JOUR2, "--a-blanc"); verifier(code == 0 and "à blanc" in sortie.lower() and "sourcing" in sortie.lower() and "google" in sortie.lower(), "jour --a-blanc : décrit chaque étape, sans réseau")
monde(trouves=gros_monde(), config={"envoi_automatique": True}); A.ARRET.write_text("stop", encoding="utf-8"); verifier(lancer("jour", "--jour", JOUR)[0] == 2 and not DRIVE.dossiers, "arrêt de secours : rien n'est fait")
verifier(lancer("google-autoriser", "--a-blanc")[0] == 0, "google-autoriser --a-blanc : n'ouvre rien")

print("20. Contrôle de bout en bout : 3 jours de suite, à blanc, sans réseau ni Google réel")
JOURS = ["2026-11-05", "2026-11-06", "2026-11-07"]
base = ([trouve(f"Resto E2E {i}", "restaurant", "Rouen", tel(100 + i)) for i in range(34)] + [trouve(f"Coiff E2E {i}", "coiffeur", "Rouen", tel(300 + i)) for i in range(18)]
        + [trouve(f"Plomb E2E {i}", "plombier-chauffagiste", "Rouen", tel(500 + i)) for i in range(8)] + [trouve(f"Elec E2E {i}", "électricien", "Rouen", tel(700 + i)) for i in range(8)])
monde(trouves=base, config={"envoi_automatique": True, "partager_avec": "sid@example.invalid", "cible_reserve": 400, "sourcing_requetes_max": 4}, listes={"2026-11-03": [("ancienne-liste|rouen", "[ ] [ ] [ ] [ ]".split())]})
lancer("rediriger-liste")
FE = FauxOverpass(); A.appel_reseau = FE; reserves, alertes_par_jour, listes = [], {}, {}
def reserve_total(): return A.reserve(A.etat_lire())["total"]
reserves.append(reserve_total())
for k, jour in enumerate(JOURS):
    FE.offre = {"plumber": 0, "electrician": 0, "hairdresser": 0, "restaurant": 0} if k != 1 else {"plumber": 40, "electrician": 40, "hairdresser": 40, "restaurant": 40}
    FE.requetes.clear(); ALERTES.clear(); code, sortie = lancer("jour", "--jour", jour)
    verifier(code == 0, f"{jour} : jour terminé (code {code})")
    reserves.append(reserve_total()); alertes_par_jour[jour] = [a for a in ALERTES if "réserve" in a.lower()]
    listes[jour] = lire_csv(jour)[1:]
    P.cmd_liste_matin({**P.DEFAUT, **A.M.lire_fusionnee(A.PROSPECTION_CONFIG)}, api=reseau, paris=Matin())
    verifier(len(listes[jour]) == 55, f"{jour} : 55 lignes")
verifier(reserves[1] < reserves[0] and reserves[2] > reserves[1] and reserves[3] < reserves[2], f"réserve : diminue (jour 1), se remplit (jour 2), diminue encore (jour 3) : {reserves}")
verifier(alertes_par_jour[JOURS[0]] and alertes_par_jour[JOURS[2]], "alerte déclenchée quand la réserve passe sous le seuil (jours 1 et 3)")
verifier(not alertes_par_jour[JOURS[1]], "pas d'alerte le jour où la réserve est remplie")
tous = [(l[1], l[3]) for j in JOURS for l in listes[j]]
verifier(len(tous) == len(set(tous)) == 165 and len({t[1] for t in tous}) == 165, "aucun doublon d'un jour à l'autre : 165 entreprises et 165 numéros différents")
verifier(not list((tmp / "docs").glob("liste-appels-2026-11-0[5-7].md")), "aucune liste d'appels générée pour Liam pendant les 3 jours (docs\\liste-appels-*.md)")
verifier({l[4] for j in JOURS for l in listes[j]} <= {"Restaurant", "Coiffeur", "Plombier-chauffagiste", "Électricien"}, "uniquement les 4 métiers voulus")
racine = DRIVE.trouver_dossier("Sid")
verifier(sum(1 for n, p in DRIVE.dossiers.values() if n == "Sid") == 1 and sorted(n for n, p in DRIVE.dossiers.values() if p == racine) == JOURS, "un dossier « Sid » et un sous-dossier par jour")
for jour in JOURS:
    d = DRIVE.trouver_dossier(jour, racine); f = DRIVE.trouver_feuille(d, f"Liste d'appels {jour}")
    verifier(f is not None and list(csv.reader(io.StringIO(DRIVE.feuilles[f][2])))[1:] == listes[jour], f"{jour} : bonne feuille, dans le bon dossier, contenu identique à la liste du jour")
verifier(len(DRIVE.feuilles) == 3 and DRIVE.partages == [(racine, "sid@example.invalid")], "3 feuilles, dossier « Sid » partagé une seule fois")
verifier(len(json.loads(A.ETAT.read_text(encoding="utf-8"))["sorties"]) == 165, "état : 165 entreprises marquées, jamais retirées")
j = A.JOURNAL.read_text(encoding="utf-8"); verifier(not re.search(r"\d\d \d\d \d\d \d\d \d\d|@|E2E", j), "journal des 3 jours : aucune donnée personnelle")
A.appel_reseau = reseau

print("21. jours_appel : jour hors planning (aucune liste, aucun accès réseau ni Google, aucune alerte)")
MERCREDI, SAMEDI, LUNDI, VENDREDI = date(2026, 11, 4), date(2026, 11, 7), date(2026, 11, 2), date(2026, 11, 6)
reel_maintenant = A.maintenant_paris
monde(trouves=gros_monde(), config={"envoi_automatique": True, "jours_appel": ["lundi", "mardi", "vendredi"]})
A.maintenant_paris = lambda: MERCREDI
code, sortie = lancer("jour", "--jour", JOUR)
verifier(code == 0 and "hors planning" in sortie.lower(), f"mercredi hors jours_appel : code 0, message clair ({sortie.strip()[:160]})")
verifier(not (A.SORTIE / f"liste-sid-{JOUR}.csv").exists() and not A.ETAT.exists(), "mercredi : aucune liste générée, aucun état écrit")
verifier(DRIVE.appels == 0 and ALERTES == [], "mercredi : aucun accès Drive, aucune alerte Discord")
verifier("jour hors planning" in A.JOURNAL.read_text(encoding="utf-8").lower(), "le journal note le jour hors planning")
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

print("22. Nettoyage Drive : sous-dossiers « Sid » de plus de 7 jours mis à la corbeille (jamais supprimés)")
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
etat = A.etat_lire(); etat["google"]["racine"] = racine; A.etat_ecrire(etat)
A.nettoyer_dossiers_drive(A.cfg(), A.etat_lire(), JOUR, DRIVE, False)
verifier(vieux in DRIVE.corbeille and DRIVE.trouver_dossier("2026-10-20", racine) is None, "dossier de 15 jours : mis à la corbeille, plus retrouvé")
verifier(pile not in DRIVE.corbeille and recent not in DRIVE.corbeille and autre not in DRIVE.corbeille, "7 jours exactement, 5 jours, et nom non daté : conservés")
verifier("corbeille" in A.JOURNAL.read_text(encoding="utf-8").lower(), "le nettoyage est journalisé")
n = len(ALERTES); A.nettoyer_dossiers_drive(A.cfg(), A.etat_lire(), JOUR, DRIVE, False)
verifier(len(ALERTES) == n, "rien à nettoyer la seconde fois : pas d'erreur, pas d'alerte")

print("22bis. Nettoyage branché dans la commande « jour »")
monde(trouves=gros_monde(), config={"envoi_automatique": True})
lancer("preparer", "--jour", JOUR); A.exporter_google(A.cfg(), A.etat_lire(), JOUR, DRIVE, False)
racine = DRIVE.trouver_dossier("Sid"); ancien = DRIVE.creer_dossier("2026-10-01", racine)
code, sortie = lancer("jour", "--jour", JOUR2)
verifier(code == 0 and ancien in DRIVE.corbeille, "jour : le nettoyage tourne aussi pendant le passage normal (vieux dossier mis à la corbeille)")

print()
if echecs: print(f"{echecs} ÉCHEC(S)"); sys.exit(1)
print("OK : tous les tests de l'agent appels-sid passent")
