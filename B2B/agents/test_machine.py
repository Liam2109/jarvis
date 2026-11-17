#!/usr/bin/env python3
"""Tests silencieux de la config locale et de la machine active des agents B2B : AUCUN réseau, aucun envoi, fichiers temporaires.  python agents\\test_machine.py
Écrits AVANT le code (machine.py). Règles de Liam (04/11/2026) :
 - tout paramètre secret ou propre à une machine vit dans <agent>-config.local.json (ignoré par git), qui surcharge les valeurs par défaut versionnées ;
 - « machine_active » (b2b.local.json) : un agent qui envoie ou écrit un état refuse de tourner sur une autre machine et le dit dans son journal ;
 - serveur 6 Go : aucun navigateur, aucun processus lourd (profil serveur) ;
 - rien ne démarre sans accord : tout est éteint par défaut."""
import importlib.util, json, os, re, shutil, subprocess, sys, tempfile
os.environ.setdefault("JARVIS_TEST", "1")
from pathlib import Path
ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import machine as M

tmp = Path(tempfile.mkdtemp(prefix="machine-test-"))
def ecrire(chemin, obj): chemin.parent.mkdir(parents=True, exist_ok=True); chemin.write_text(obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False), encoding="utf-8")
def charger(fichier):
    spec = importlib.util.spec_from_file_location(fichier.replace("-", "_").replace(".py", ""), ICI / fichier); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
def doit_lever(exc, f):
    try: f()
    except exc as e: return e
    raise AssertionError("exception attendue : " + exc.__name__)

# ---------- 1) machine active ----------
M.LOCAL = tmp / "b2b.local.json"; M.nom_machine = lambda: "PC-SERVEUR"; JR = tmp / "journal.log"
ok, raison = M.verifier("instagram", "jour", False, JR)
assert not ok and "machine_active" in raison and "refusé" in JR.read_text(encoding="utf-8"), (ok, raison)       # aucune config locale : refus (rien ne tourne sans réglage voulu)
ecrire(M.LOCAL, {"machine_active": "pc-serveur"}); JR.unlink()
assert M.verifier("instagram", "jour", False, JR) == (True, "") and not JR.exists()                           # même nom (casse ignorée) : autorisé, rien d'écrit
ecrire(M.LOCAL, {"machine_active": "PC-BUREAU"})
ok, raison = M.verifier("devis", "jour", False, JR)
assert not ok and "PC-BUREAU" in raison and "PC-SERVEUR" in raison, raison                                    # le refus nomme les deux machines
ligne = JR.read_text(encoding="utf-8"); assert "refusé" in ligne and "PC-BUREAU" in ligne and "PC-SERVEUR" in ligne and "devis" in ligne, ligne
assert M.verifier("devis", "jour", True, JR)[0], "--a-blanc n'écrit rien : jamais refusé"
for c in ("etat", "arreter", "file", "vagues", "rapport"): assert M.verifier("devis", c, False, JR)[0], c        # lecture seule / arrêt de secours : toujours permis
for mauvais in ({"machine_active": ""}, {"machine_active": 5}, {"machine_active": None}, {}): ecrire(M.LOCAL, mauvais); assert not M.verifier("devis", "jour", False, JR)[0], mauvais
ecrire(M.LOCAL, '{"machine_active": "PC-SERVEUR", "ical_url": "SECRETXYZ'); ok, raison = M.verifier("devis", "jour", False, JR)
assert not ok and "illisible" in raison and "SECRETXYZ" not in raison and "SECRETXYZ" not in JR.read_text(encoding="utf-8")   # fichier abîmé : refus, sans rien montrer de son contenu
ecrire(M.LOCAL, {"machine_active": "PC-BUREAU"}); e = doit_lever(SystemExit, lambda: M.exiger("rendez-vous", "jour", False, JR)); assert e.code == 3
ecrire(M.LOCAL, {"machine_active": "PC-SERVEUR"}); M.exiger("rendez-vous", "jour", False, JR)                  # autorisé : ne lève rien
ecrire(M.LOCAL, {"machine_active": "PC-SERVEUR", "agents_actifs": ["rendez-vous", "devis", "inconnu"], "serveur": True})
assert M.agents_actifs() == ["rendez-vous", "devis", "inconnu"] and M.serveur() is True
ecrire(M.LOCAL, {"machine_active": "PC-SERVEUR"}); assert M.agents_actifs() == [] and M.serveur() is False       # tout éteint par défaut
os.environ["JARVIS_B2B_SERVEUR"] = "1"; assert M.serveur() is True; del os.environ["JARVIS_B2B_SERVEUR"]         # le lanceur du serveur pose cette variable
# une boucle « continu » lancée par Jarvis ferait double emploi avec la tâche planifiée Jarvis-B2B-<agent> : refusée pour les agents planifiés, permise sinon (PC de bureau)
ecrire(M.LOCAL, {"machine_active": "PC-SERVEUR", "agents_actifs": ["rendez-vous", "prospection"]})
ok, raison = M.verifier("rendez-vous", "continu", False, JR); assert not ok and "Jarvis-B2B-rendez-vous" in raison and "double" in raison, raison
for c in ("ecouter", "demarrage"): assert not M.verifier("prospection", c, False, JR)[0], c
assert M.verifier("rendez-vous", "jour", False, JR)[0] and M.verifier("devis", "continu", False, JR)[0], "un agent non planifié garde sa boucle ; « jour » est toujours permis"
ecrire(M.LOCAL, {"machine_active": "PC-SERVEUR"})

# ---------- 2) surcharge locale ----------
d = tmp / "agents"; d.mkdir(); cfg = d / "x-config.json"
ecrire(cfg, {"envoi_automatique": False, "ical_url": "", "api": {"actif": False, "comptes": ["a@x"]}, "_aide": "défaut"})
assert M.chemin_local(cfg).name == "x-config.local.json"
base = {"envoi_automatique": False, "ical_url": "", "api": {"actif": False, "comptes": ["a@x"]}}
assert M.surcharge_locale(cfg, dict(base)) == base                                                              # pas de fichier local : valeurs par défaut
ecrire(M.chemin_local(cfg), {"envoi_automatique": True, "ical_url": "https://calendar.google.com/secret-LOCAL", "api": {"actif": True}, "_aide": "ignoré"})
r = M.surcharge_locale(cfg, json.loads(json.dumps(base)))
assert r["envoi_automatique"] is True and r["ical_url"].endswith("secret-LOCAL") and r["api"] == {"actif": True, "comptes": ["a@x"]} and "_aide" not in r, r   # fusion en profondeur, « _ » ignorés
assert json.loads(cfg.read_text(encoding="utf-8"))["envoi_automatique"] is False                               # le défaut versionné n'est jamais modifié
ecrire(M.chemin_local(cfg), '{"ical_url": "SECRETABC')
e = doit_lever(M.ErreurLocale, lambda: M.surcharge_locale(cfg, dict(base))); assert "SECRETABC" not in str(e) and "x-config.local.json" in str(e), e
ecrire(M.chemin_local(cfg), "[1, 2]"); doit_lever(M.ErreurLocale, lambda: M.surcharge_locale(cfg, dict(base)))   # pas un objet : refusé
M.chemin_local(cfg).unlink()
assert M.lire_fusionnee(cfg)["api"]["comptes"] == ["a@x"] and M.lire_fusionnee(d / "absent.json") == {}
M.ecrire_local(cfg, {"api": {"actif": True}, "salon_id": "42"}); M.ecrire_local(cfg, {"salon_id": "43"})
assert json.loads(M.chemin_local(cfg).read_text(encoding="utf-8")) == {"api": {"actif": True}, "salon_id": "43"}   # fusion dans le local
assert json.loads(cfg.read_text(encoding="utf-8"))["api"]["actif"] is False                                    # défaut intact
assert M.lire_fusionnee(cfg)["api"] == {"actif": True, "comptes": ["a@x"]}

# ---------- 3) chacun des 6 agents lit la surcharge locale ----------
def essai(fichier, nom_cfg, defaut, local, verifie):
    m = charger(fichier); c = tmp / "a" / nom_cfg; m.CONFIG = c; ecrire(c, defaut)
    base = m.cfg(); loc = M.chemin_local(c); loc.unlink(missing_ok=True)
    assert not base.get("envoi_automatique"), f"{fichier} : doit démarrer éteint"
    ecrire(loc, local); r = m.cfg(); assert verifie(r), (fichier, r)
    assert not json.loads(c.read_text(encoding="utf-8")).get("envoi_automatique"), f"{fichier} : le défaut versionné a bougé"
    return m
essai("instagram.py", "instagram-config.json", {"envoi_automatique": False}, {"envoi_automatique": True, "image_url_base": "https://exemple.invalid/x/", "salon_nom": "insta"}, lambda r: r["envoi_automatique"] is True and r["salon_nom"] == "insta")
essai("devis.py", "devis-config.json", {"envoi_automatique": False}, {"envoi_automatique": True, "salon_nom": "devis"}, lambda r: r["envoi_automatique"] is True and r["salon_nom"] == "devis")
essai("rendez-vous.py", "rendez-vous-config.json", {"envoi_automatique": False, "ical_url": ""}, {"envoi_automatique": True, "ical_url": "https://calendar.google.com/calendar/ical/x/private-L/basic.ics"}, lambda r: r["envoi_automatique"] is True and "private-L" in r["ical_url"])
essai("appels-sid.py", "appels-sid-config.json", {"envoi_automatique": False, "partager_avec": ""}, {"envoi_automatique": True, "partager_avec": "sid@example.invalid"}, lambda r: r["envoi_automatique"] is True and r["partager_avec"] == "sid@example.invalid")
essai("prospection.py", "prospection-config.json", {"envoi_automatique": False}, {"envoi_automatique": True}, lambda r: r["envoi_automatique"] is True)
rep = essai("reponses.py", "reponses-config.json", {"salon_paiement_id": ""}, {"salon_paiement_id": "777", "api": {"actif": True, "comptes": ["Z@X.fr"]}}, lambda r: r["salon_paiement_id"] == "777" and r["api"]["actif"] is True and r["api"]["comptes"] == ["z@x.fr"])
assert rep.cfg().get("envoi_automatique", False) is False

# ---------- 4) les écritures à l'exécution vont dans le LOCAL, jamais dans un fichier suivi par git ----------
rc = tmp / "b" / "reponses-config.json"; ecrire(rc, {"salon_paiement_id": "1"}); avant = rc.read_text(encoding="utf-8")
faux = lambda ch: [{"id": "g1"}] if ch == "/users/@me/guilds" else ([{"id": "c9", "name": "rdv", "type": 0}] if ch.endswith("/channels") else [])
assert rep.salon_par_nom("jeton", "salon_rdv_id", "rdv", "ancien", lire=faux, chemin_cfg=rc) == "c9"
assert rc.read_text(encoding="utf-8") == avant and json.loads(M.chemin_local(rc).read_text(encoding="utf-8")) == {"salon_rdv_id": "c9"}      # cache de salon : écrit dans le local
assert rep.salon_par_nom("jeton", "salon_rdv_id", "rdv", "ancien", lire=lambda ch: (_ for _ in ()).throw(AssertionError("pas de relecture")), chemin_cfg=rc) == "c9"   # relu depuis le local
GA = charger("gmail_api.py"); GA.enregistrer_adresse("Nouveau@X.fr", rc)
assert rc.read_text(encoding="utf-8") == avant and json.loads(M.chemin_local(rc).read_text(encoding="utf-8"))["api"]["comptes"] == ["nouveau@x.fr"]  # compte Gmail ajouté : dans le local

# ---------- 5) serveur 6 Go : aucun navigateur, aucun processus lourd ----------
ig = charger("instagram.py"); appels = []
subprocess_run = ig.subprocess.run; ig.subprocess.run = lambda *a, **k: appels.append(a) or None
os.environ["JARVIS_B2B_SERVEUR"] = "1"
try:
    e = doit_lever(RuntimeError, lambda: ig.rendre_carte({"metier": "x", "capture": "c.png"}, tmp / "o.png")); assert "navigateur" in str(e).lower() and not appels
    r = ig.cmd_visuels({"file_minimum": 3, "sources_cartes": [{"cle": "a", "metier": "m", "capture": "c.png"}]}, True); assert r["action"] == "serveur" and not appels, r   # pas de rendu de carte sur le serveur
    ps = charger("prospection.py"); ps.subprocess.run = lambda *a, **k: appels.append(a) or None
    assert ps.lancer_generer(tmp / "lot.csv") is False and not appels                                           # pas de génération de maquettes sur le serveur
finally:
    del os.environ["JARVIS_B2B_SERVEUR"]
assert ps.lancer_generer(tmp / "lot.csv") is True and len(appels) == 1 and "generer.py" in str(appels[0])       # sur le PC : comportement inchangé
ig.subprocess.run = subprocess_run
src = (ICI / "instagram.py").read_text(encoding="utf-8")
assert not re.search(r"^\s*(import|from)\s+(selenium|playwright|pyppeteer)", src, re.M)                         # l'API Graph seule : aucun module de navigateur

# ---------- 6) tâches du serveur (serveur-taches.json) : cohérence ----------
T = json.loads((ICI / "serveur-taches.json").read_text(encoding="utf-8"))["agents"]
assert set(T) == {"appels-sid", "appels-liam", "devis", "rendez-vous", "reponses", "prospection", "resume-sid", "stripe-alerte", "panne-alerte", "surveillant", "nettoyage-fichiers",
                  "videos-veille", "videos-scripts", "videos-marketing", "videos-creation", "videos-publication", "videos-nettoyage", "alerte-candidatures"}, sorted(T)   # équipe Vidéos TikTok (16/11/2026), scripts dans Videos\agents
assert T["videos-creation"]["heure"] == "06:00" and T["videos-creation"]["heures_en_plus"] == ["14:00", "22:00"] and T["videos-creation"]["commandes"] == [["passage"]]
assert T["videos-publication"]["commandes"] == [["publier"]] and "actif_le" not in T["videos-publication"]   # désactivée : seulement après le « go publier » de Liam (agents_actifs)   # instagram retiré du serveur le 14/11/2026 (archive) ; resume-sid/stripe-alerte/panne-alerte ajoutés (étape Argent, 15/11/2026) ; surveillant du harness (15/11/2026)
assert T["nettoyage-fichiers"]["heure"] == "03:00" and T["nettoyage-fichiers"]["commandes"] == [["nettoyer"]]   # nettoyage des traces et du journal de plus de 30 jours (15/11/2026)
assert T["surveillant"]["heure"] == "19:45" and T["surveillant"]["lundi"] == "07:50" and T["surveillant"]["commandes"] == [["verifier"]]
for nom, t in T.items():
    assert (ICI / t["script"]).is_file() and t["commandes"] and bool(t.get("toutes_minutes")) != bool(t.get("heure")), nom   # une cadence OU une heure
    for cmd in t["commandes"]: assert not set(cmd) & {"continu", "visuels", "ecouter", "demarrage", "google-autoriser", "installer-tache"}, (nom, cmd)   # ni boucle infinie, ni navigateur
assert T["appels-sid"]["heure"] == "07:30" and T["appels-sid"]["commandes"] == [["jour"]]
assert T["appels-liam"]["heure"] == "07:30" and T["appels-liam"]["commandes"] == [["jour"]] and T["appels-liam"]["actif_le"] == "2026-11-17" and T["appels-liam"]["jours"] == [0, 1, 2, 3, 4]   # liste de Liam (registre commun, 15/11/2026), même heure que Sid
assert "instagram" not in T and T["rendez-vous"]["commandes"] == [["jour"]] and T["devis"]["commandes"] == [["jour"]]

# ---------- 7) refus de bout en bout : la vraie ligne de commande de chaque agent, dans une COPIE du dossier ----------
copie = tmp / "copie" / "B2B"; (copie / "agents").mkdir(parents=True)
for f in ICI.glob("*.py"): shutil.copy(f, copie / "agents" / f.name)
for f in ICI.parent.glob("*.py"): shutil.copy(f, copie / f.name)
shutil.copytree(ICI.parent / "harness", copie / "harness", ignore=shutil.ignore_patterns("__pycache__"))   # harness (15/11/2026) : surveillant, garde, contrats
if (ICI.parent / "sites" / "moteur").is_dir():
    (copie / "sites" / "moteur").mkdir(parents=True)
    for f in (ICI.parent / "sites" / "moteur").glob("*.py"): shutil.copy(f, copie / "sites" / "moteur" / f.name)
ecrire(copie / "agents" / "b2b.local.json", {"machine_active": "UNE-AUTRE-MACHINE-QUI-N-EXISTE-PAS"})
videos = copie.parent / "Videos"; (videos / "agents").mkdir(parents=True)   # équipe Vidéos (16/11/2026) : mêmes refus, journaux dans Videos\
for f in [*(ICI.parent.parent / "Videos" / "agents").glob("*.py"), *(ICI.parent.parent / "Videos" / "agents").glob("*.ps1")]: shutil.copy(f, videos / "agents" / f.name)
for f in ("videos-config.json", "SKILL-VIDEOS.md"): shutil.copy(ICI.parent.parent / "Videos" / f, videos / f)
env = {**os.environ, "JARVIS_TEST": "1", "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"}
for agent, args in [(n, [] if n == "reponses" else T[n]["commandes"][0]) for n in T] + [("instagram", ["jour"])]:   # chaque agent du serveur (sa vraie commande, lue dans serveur-taches.json) + l'archive instagram (lancée à la main : refusée aussi)
    script = copie / "agents" / (T[agent]["script"] if agent in T else agent + ".py"); dossier = videos if agent.startswith("videos-") else copie / "agents"
    lanceur = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File"] if script.suffix == ".ps1" else [sys.executable]   # videos-nettoyage : agent PowerShell
    p = subprocess.run(lanceur + [str(script)] + [x for x in args if x], capture_output=True, text=True, timeout=60, env=env, cwd=str(copie))
    assert p.returncode == 3, (agent, p.returncode, p.stdout[-300:], p.stderr[-300:])
    jr = dossier / f"{agent}-journal.log"
    assert jr.is_file() and "refusé" in jr.read_text(encoding="utf-8") and "UNE-AUTRE-MACHINE" in jr.read_text(encoding="utf-8"), agent   # le journal le dit
    assert not any(dossier.glob(f"{agent}-etat.json")), f"{agent} : aucun état écrit"
    assert "machine" in (p.stdout + p.stderr).lower()
# --a-blanc et commandes de lecture ne sont pas refusés (rien n'est écrit ni envoyé)
p = subprocess.run([sys.executable, str(copie / "agents" / "rendez-vous.py"), "etat"], capture_output=True, text=True, timeout=60, env=env, cwd=str(copie))
assert p.returncode == 0, (p.returncode, p.stdout[-300:], p.stderr[-300:])

shutil.rmtree(tmp, ignore_errors=True)
print("OK : tous les tests de la config locale et de la machine active passent")
