#!/usr/bin/env python3
"""Tests silencieux de l'agent devis : aucun réseau, aucun envoi, aucun navigateur, fichiers temporaires, jamais de vrai Discord.  python agents\\test_devis.py
Écrits AVANT le code (devis.py). Ils fixent les règles de Liam : prix et liens pris dans docs\\KIT-RDV-15MIN.md et docs\\liens-paiement.md (jamais inventés ; information manquante = signalée et arrêt),
simulation par défaut, un seul devis en cours de validation, rien vers le client sans le « ok » de Liam (l'agent n'a AUCUNE fonction d'envoi), statuts dans l'ordre, erreur = arrêt + alerte, journal de chaque action."""
import os, re, sys, tempfile, json
os.environ.setdefault("JARVIS_TEST", "1")
from datetime import datetime, timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import devis as D

tmp = Path(tempfile.mkdtemp(prefix="devis-test-"))
D.DOSSIER, D.ETAT, D.CONFIG, D.ARRET, D.VERROU, D.JOURNAL, D.IDENTITE = tmp / "devis", tmp / "etat.json", tmp / "config.json", tmp / "arret", tmp / "verrou", tmp / "journal.log", tmp / "identite.json"
IDENT = {"prenom_nom": "Liam Emo", "entreprise": "LM MULTI-SERVICES", "siret": "10183903300012", "telephone": "06 00 00 00 00", "email_reponse": "liam@example.invalid"}
D.IDENTITE.write_text(json.dumps(IDENT), encoding="utf-8")
JOUR = datetime(2026, 11, 4, 10, 0)

FICHE_PAGE = """Entreprise : Boulangerie Fictive Dupont
Métier : boulangerie
Ville : Rouen
Contact : Jeanne Martin
E-mail : jeanne@example.invalid
Téléphone : 06 11 22 33 44
Offre : page web
Options : maintenance
Délai : 8 jours ouvrés
Livrables : photos de la boutique ; horaires d'ouverture ; bouton d'appel ; carte et itinéraire
Besoin : « Je veux que les gens m'appellent depuis leur téléphone. »
"""
FICHE_SITE = FICHE_PAGE.replace("Offre : page web", "Offre : site complet\nPrix : 994 €").replace("Options : maintenance\n", "Options : aucune\n")

# --- lecture de la fiche : accents, majuscules et alias sans importance ---
f = D.lire_fiche(FICHE_PAGE)
assert f["entreprise"] == "Boulangerie Fictive Dupont" and f["metier"] == "boulangerie" and f["ville"] == "Rouen" and f["contact"] == "Jeanne Martin" and f["offre"] == "page web", f
assert f["delai"] == "8 jours ouvrés" and f["email"] == "jeanne@example.invalid" and f["telephone"] == "06 11 22 33 44" and f["besoin"].startswith("« Je veux")
assert D.lire_fiche("ENTREPRISE: X\nmétier :  plombier \nNom: Paul")["contact"] == "Paul"
assert D.lire_fiche("rien de valable ici") == {}
MODELE = (Path(D.__file__).parent / "devis-fiche-modele.txt").read_text(encoding="utf-8")
assert D.lire_fiche("# Offre : site complet\nOffre : page web\n# note\nVille : Rouen") == {"offre": "page web", "ville": "Rouen"}      # lignes # ignorées
rm = D.construire(D.lire_fiche(MODELE), IDENT, "DEV-2026-009", JOUR); assert rm[0] is None and len(rm[1]) >= 6, rm       # le modèle non rempli ne produit JAMAIS de devis

# --- prix et lien de paiement du prix complet (paiement en une fois, 14/11/2026) : uniquement ceux de docs\KIT-RDV-15MIN.md / liens-paiement.md ---
d, manques = D.construire(f, IDENT, "DEV-2026-001", JOUR)
assert not manques and d["prix"] == 595 and "acompte" not in d and "solde" not in d and d["lien_paiement"] == "https://buy.stripe.com/bJebJ2ceVdZjbLN0ly5EY06", (d, manques)
assert d["maintenance"] is True and d["delai_jours"] == 8 and d["valide_jusqu"] == "2026-11-19" and len(d["livrables"]) == 4 and d["offre_nom"] == "Page web"
ds, m2 = D.construire(D.lire_fiche(FICHE_SITE), IDENT, "DEV-2026-002", JOUR)
assert not m2 and ds["prix"] == 994 and ds["lien_paiement"] == "https://buy.stripe.com/7sYaEY2ElaN7179d8k5EY07" and ds["maintenance"] is False
assert D.euros(590) == "590 €" and D.euros(1490) == "1 490 €"

# --- information manquante ou sans source : signalée, aucun devis (rien d'inventé) ---
def manquent(texte, ident=IDENT):
    return D.construire(D.lire_fiche(texte), ident, "DEV-2026-009", JOUR)
def sans(cle): return "\n".join(l for l in FICHE_PAGE.splitlines() if not l.lower().startswith(cle.lower())) + "\n"
for cle, mot in (("Entreprise", "entreprise"), ("Métier", "métier"), ("Ville", "ville"), ("Offre", "offre"), ("Délai", "délai"), ("Livrables", "livrables"), ("Contact", "contact")):
    r, mq = manquent(sans(cle)); assert r is None and any(mot in x.lower() for x in mq), (cle, mq)
r, mq = manquent(sans("E-mail").replace("Téléphone : 06 11 22 33 44\n", "")); assert r is None and any("e-mail" in x or "téléphone" in x for x in mq), mq   # aucun moyen de joindre le client
assert manquent(FICHE_PAGE.replace("8 jours ouvrés", "bientôt"))[0] is None                       # délai non chiffré : jamais deviné
assert manquent(FICHE_PAGE.replace("Livrables : photos de la boutique ; horaires d'ouverture ; bouton d'appel ; carte et itinéraire", "Livrables : photos ; horaires"))[0] is None   # 3 à 5 éléments
assert manquent(FICHE_PAGE.replace("Offre : page web", "Offre : refonte totale"))[0] is None
r, mq = manquent(FICHE_PAGE.replace("maintenance", "maintenance ; nom de domaine")); assert r is None and any("domaine" in x and "prix" in x for x in mq), mq   # option sans prix dans les sources
assert manquent(FICHE_PAGE + "Prix : 500 €\n")[0] is None                                          # la page web coûte 595 €, pas un autre montant
assert manquent(FICHE_PAGE.replace("Offre : page web", "Offre : site complet"))[0] is None         # site complet sans prix (990 à 1 490 €) : à décider par Liam
assert manquent(FICHE_PAGE.replace("Offre : page web", "Offre : site complet\nPrix : 700 €"))[0] is None   # hors de 990 à 1 490 €
r, mq = manquent(FICHE_PAGE.replace("Offre : page web", "Offre : site complet\nPrix : 1 190 €")); assert r is None and any("lien" in x and "994 €" in x for x in mq), mq   # lien de paiement à créer par Liam
assert manquent(FICHE_PAGE.replace("Offre : page web", "Offre : site complet\nPrix : 990 €"))[0] is None   # 990 € : aucun lien de ce montant
assert manquent(FICHE_PAGE.replace("Offre : page web", "Offre : site complet\nPrix : 1 600 €"))[0] is None
assert manquent(FICHE_PAGE, {**IDENT, "siret": ""})[0] is None and manquent(FICHE_PAGE, {**IDENT, "email_reponse": ""})[0] is None   # en-tête incomplet

# --- le devis écrit (texte et PDF, même contenu) ---
txt = D.texte_devis(d)
for attendu in ("LM MULTI-SERVICES", "entreprise individuelle", "101 839 033 00012", "TVA non applicable, art. 293 B du CGI", "DEV-2026-001", "Boulangerie Fictive Dupont", "Rouen", "Page web",
                "595 €", "en une fois", "8 jours ouvrés", "valable 15 jours", "19/11/2026", d["lien_paiement"], "aperçu", "49 € par mois", "photos de la boutique", "carte et itinéraire"):
    assert attendu in txt, attendu
assert not re.search(r"garanti|n°\s?1|meilleur|\bavis\b|clients? satisfaits|référence", txt, re.I)   # aucune promesse ni avis inventés
assert "49 €" in D.texte_devis(d) and "49 €" not in D.texte_devis(ds) and ds["lien_paiement"] in D.texte_devis(ds) and "994 €" in D.texte_devis(ds)   # maintenance seulement si demandée, jamais ajoutée au total
msg = D.texte_message(d)
for t in (txt, msg, D.texte_devis(ds), D.texte_message(ds)): assert not re.search(r"acompte|solde|30 %", t, re.I), t   # paiement en une fois : aucune étape intermédiaire
assert msg.startswith("Objet : Devis page web pour Boulangerie Fictive Dupont") and "Bonjour Jeanne Martin" in msg and "Je veux que les gens m'appellent" in msg and d["lien_paiement"] in msg and "DEV-2026-001" in msg and "Liam Emo" in msg and "valable 15 jours" in msg
assert "Je veux" not in D.texte_message({**d, "besoin": ""}) and "vos mots" not in D.texte_message({**d, "besoin": ""})
pdf = D.pdf_devis(d)
assert pdf.startswith(b"%PDF-1.4") and pdf.rstrip().endswith(b"%%EOF")
sx = int(re.search(rb"startxref\s+(\d+)", pdf).group(1)); assert pdf[sx:sx + 4] == b"xref"
nb = int(re.search(rb"xref\s+0 (\d+)", pdf).group(1)); offs = re.findall(rb"(\d{10}) 00000 n", pdf[sx:]); assert len(offs) == nb - 1
for i, o in enumerate(offs, 1): assert pdf[int(o):].startswith(f"{i} 0 obj".encode()), i      # table des références exacte
assert b"DEV-2026-001" in pdf and "595 €".encode("cp1252") in pdf and b"acompte" not in pdf.lower() and b"Boulangerie Fictive Dupont" in pdf
assert len(re.findall(rb"/Type /Page\b", pdf)) == 1
long = D.pdf_devis({**d, "besoin": "mot " * 3000}); assert len(re.findall(rb"/Type /Page\b", long)) >= 2 and long.rstrip().endswith(b"%%EOF")      # passage à la page suivante

# --- numérotation DEV-AAAA-NNN unique ---
assert D.numero_suivant({"devis": {}}, 2026) == "DEV-2026-001"
assert D.numero_suivant({"devis": {"DEV-2026-001": {}, "DEV-2026-007": {}, "DEV-2025-099": {}}}, 2026) == "DEV-2026-008"
assert D.numero_suivant({"devis": {"DEV-2026-007": {}}}, 2027) == "DEV-2027-001"
D.DOSSIER.mkdir(); (D.DOSSIER / "DEV-2026-020.pdf").write_bytes(b"x")
assert D.numero_suivant({"devis": {"DEV-2026-007": {}}}, 2026) == "DEV-2026-021"          # un fichier déjà présent n'est jamais écrasé
(D.DOSSIER / "DEV-2026-020.pdf").unlink()

# --- réglages : simulation par défaut ---
conf = D.cfg(); assert conf["envoi_automatique"] is False and conf["cycle_minutes"] >= 1
class Faux:
    """Faux Discord : aucun réseau. Messages du salon, réactions, échec simulé."""
    def __init__(self): self.msgs, self.reactions, self.appels, self.panne = [], [], [], False; self.n = 1000
    def acces(self): return ("jeton-faux", "salon-1", "42")
    def api(self, jeton, methode, chemin, corps=None):
        self.appels.append((methode, chemin))
        if self.panne: raise RuntimeError("panne simulée")
        if methode == "POST":
            self.n += 1; self.msgs.append({"id": str(self.n), "content": corps["content"], "author": {"id": "bot", "bot": True}}); return {"id": str(self.n)}
        if "/reactions/" in chemin: return self.reactions
        m = re.search(r"after=(\d+)", chemin)
        if m: return [x for x in self.msgs if int(x["id"]) > int(m.group(1))]
        return self.msgs[-1:] if "limit=1" in chemin else []
    def liam(self, texte, uid="42"): self.n += 1; self.msgs.append({"id": str(self.n), "content": texte, "author": {"id": uid, "bot": False}}); return str(self.n)
alertes = []
def alerte(t): alertes.append(t)
def effacer():
    for p in (D.ETAT, D.JOURNAL): p.unlink(missing_ok=True)
    for p in D.DOSSIER.glob("*"): p.unlink()
    alertes.clear()
def journal(): return D.JOURNAL.read_text(encoding="utf-8") if D.JOURNAL.exists() else ""

# --- préparer en simulation : fichiers écrits, état « préparé », aucun appel Discord ---
effacer(); fx = Faux()
r = D.cmd_preparer(conf, FICHE_PAGE, False, JOUR, IDENT, alerte)
assert r["action"] == "préparé" and r["numero"] == "DEV-2026-001"
for ext in (".txt", ".pdf", "-message.txt"): assert (D.DOSSIER / f"DEV-2026-001{ext}").stat().st_size > 100, ext
e = D.etat_lire(); assert e["devis"]["DEV-2026-001"]["statut"] == "préparé" and e["devis"]["DEV-2026-001"]["prix"] == 595 and e["devis"]["DEV-2026-001"]["historique"]["préparé"] == "2026-11-04"
assert "jeanne@example.invalid" not in D.ETAT.read_text(encoding="utf-8") and "06 11 22 33 44" not in D.ETAT.read_text(encoding="utf-8")      # coordonnées du client : jamais dans l'état
assert "préparé" in journal() and "DEV-2026-001" in journal() and "jeanne@example.invalid" not in journal() and not fx.appels and not alertes
assert (D.DOSSIER / "DEV-2026-001.txt").read_text(encoding="utf-8") == txt and (D.DOSSIER / "DEV-2026-001-message.txt").read_text(encoding="utf-8") == msg   # fiche identique : mêmes textes

# --- un seul devis à la fois en cours de validation ---
r2 = D.cmd_preparer(conf, FICHE_SITE, False, JOUR, IDENT, alerte)
assert r2["action"] == "refusé" and "DEV-2026-001" in r2["raison"] and not (D.DOSSIER / "DEV-2026-002.pdf").exists() and "DEV-2026-002" not in D.etat_lire()["devis"]

# --- à blanc : aucune écriture du tout ---
effacer(); r = D.cmd_preparer(conf, FICHE_PAGE, True, JOUR, IDENT, alerte)
assert r["action"] == "à blanc" and r["numero"] == "DEV-2026-001" and not D.ETAT.exists() and not D.JOURNAL.exists() and not list(D.DOSSIER.glob("*"))

# --- information manquante : signalée, aucun fichier, aucun numéro consommé, code 2 ---
effacer(); r = D.cmd_preparer(conf, sans("Délai"), False, JOUR, IDENT, alerte)
assert r["action"] == "information manquante" and any("délai" in x for x in r["manques"]) and not list(D.DOSSIER.glob("*")) and not D.etat_lire()["devis"] and "information manquante" in journal()
assert D.cmd_preparer(conf, FICHE_PAGE, False, JOUR, IDENT, alerte)["numero"] == "DEV-2026-001"      # le numéro n'a pas été brûlé

# --- mode réel : aperçu « à valider » sur Discord, une seule fois ; le « ok » de Liam SEUL valide ---
effacer(); fx = Faux(); D.cmd_preparer(conf, FICHE_PAGE, False, JOUR, IDENT, alerte)
reel = {**conf, "envoi_automatique": True}
j = D.cmd_jour(reel, False, JOUR, fx.api, fx.acces, alerte); assert j["action"] == "aperçu posté"
apercu = fx.msgs[0]["content"]; assert "à valider" in apercu and "DEV-2026-001" in apercu and "595 €" in apercu and "ok devis" in apercu and "Boulangerie Fictive Dupont" in apercu and "jeton-faux" not in apercu
assert D.etat_lire()["devis"]["DEV-2026-001"]["apercu_id"] == "1001"
assert D.cmd_jour(reel, False, JOUR, fx.api, fx.acces, alerte)["action"] == "en attente du ok"        # aucun second aperçu
assert len([x for x in fx.msgs if x["author"]["bot"]]) == 1
fx.liam("ok devis", uid="777"); fx.liam("ok devis DEV-2026-999"); fx.liam("peut-être")             # autre personne, mauvais numéro, autre texte
assert D.cmd_jour(reel, False, JOUR, fx.api, fx.acces, alerte)["action"] == "en attente du ok" and D.etat_lire()["devis"]["DEV-2026-001"]["statut"] == "préparé"
fx.msgs.append({"id": "1500", "content": "ok devis", "author": {"id": "42", "bot": True}})           # un bot ne valide jamais
assert D.cmd_jour(reel, False, JOUR, fx.api, fx.acces, alerte)["action"] == "en attente du ok"
fx.liam("ok devis"); jv = D.cmd_jour(reel, False, JOUR + timedelta(hours=1), fx.api, fx.acces, alerte)
e = D.etat_lire(); assert jv["action"] == "validé" and e["devis"]["DEV-2026-001"]["statut"] == "validé" and e["devis"]["DEV-2026-001"]["historique"]["validé"] == "2026-11-04" and e["ok_utilises"]
assert D.cmd_jour(reel, False, JOUR, fx.api, fx.acces, alerte)["action"] == "rien"                  # validé : plus rien à faire seul, rien n'est envoyé au client
assert all(m == "GET" or c.endswith("/messages") for m, c in fx.appels)                              # le seul envoi d'Internet : le message à Liam dans son salon
# « ok » avant l'aperçu : ignoré ; ✅ de Liam : accepté ; « ok devis DEV-2026-001 » : accepté
effacer(); fx = Faux(); fx.liam("ok devis"); D.cmd_preparer(conf, FICHE_PAGE, False, JOUR, IDENT, alerte); D.cmd_jour(reel, False, JOUR, fx.api, fx.acces, alerte)
assert D.cmd_jour(reel, False, JOUR, fx.api, fx.acces, alerte)["action"] == "en attente du ok"
fx.reactions = [{"id": "42"}]; assert D.cmd_jour(reel, False, JOUR, fx.api, fx.acces, alerte)["action"] == "validé"
effacer(); fx = Faux(); D.cmd_preparer(conf, FICHE_PAGE, False, JOUR, IDENT, alerte); D.cmd_jour(reel, False, JOUR, fx.api, fx.acces, alerte); fx.liam("OK devis DEV-2026-001 !")
assert D.cmd_jour(reel, False, JOUR, fx.api, fx.acces, alerte)["action"] == "validé"

# --- simulation : jour ne touche pas à Discord ; validation à la main (commande de Liam) ---
effacer(); fx = Faux(); D.cmd_preparer(conf, FICHE_PAGE, False, JOUR, IDENT, alerte)
assert D.cmd_jour(conf, False, JOUR, fx.api, fx.acces, alerte)["action"] == "simulation" and not fx.appels and D.etat_lire()["devis"]["DEV-2026-001"]["statut"] == "préparé"

# --- suivi : statuts dans l'ordre, jamais de saut ; l'agent ne lit ni n'écrit Stripe : Liam coche à la main ---
assert D.STATUTS == ["préparé", "validé", "envoyé", "accepté", "payé"]
assert D.cmd_marquer("DEV-2026-001", "envoyé", JOUR)["action"] == "refusé"                           # pas envoyé sans « ok » de Liam
assert D.cmd_marquer("DEV-2026-404", "validé", JOUR)["action"] == "refusé"
assert D.cmd_marquer("DEV-2026-001", "validé", JOUR)["action"] == "marqué" and D.cmd_marquer("DEV-2026-001", "accepté", JOUR)["action"] == "refusé"
for s, dj in (("envoyé", 1), ("accepté", 2), ("payé", 3)): assert D.cmd_marquer("DEV-2026-001", s, JOUR + timedelta(days=dj))["action"] == "marqué", s
h = D.etat_lire()["devis"]["DEV-2026-001"]; assert h["statut"] == "payé" and h["historique"]["payé"] == "2026-11-07" and list(h["historique"]) == D.STATUTS
assert D.cmd_marquer("DEV-2026-001", "validé", JOUR)["action"] == "refusé"                            # jamais en arrière
assert len(re.findall(r"marqué", journal())) == 4
assert D.statut_court("paye") == "payé" and D.statut_court("acompte") is None and D.statut_court("envoye") == "envoyé" and D.statut_court("valide") == "validé" and D.statut_court("zzz") is None
# un nouveau devis est possible une fois le précédent validé (un seul en cours de VALIDATION)
assert D.cmd_preparer(conf, FICHE_SITE, False, JOUR, IDENT, alerte)["numero"] == "DEV-2026-002"
# annuler libère la place
assert D.cmd_annuler("DEV-2026-002", JOUR)["action"] == "annulé" and D.cmd_annuler("DEV-2026-001", JOUR)["action"] == "refusé"      # un devis envoyé ne s'annule pas
assert D.cmd_preparer(conf, FICHE_SITE, False, JOUR, IDENT, alerte)["numero"] == "DEV-2026-003"

# --- erreur : arrêt, alerte Discord UNE fois, aucune reprise automatique ---
effacer(); fx = Faux(); D.cmd_preparer(conf, FICHE_PAGE, False, JOUR, IDENT, alerte); fx.panne = True
je = D.cmd_jour(reel, False, JOUR, fx.api, fx.acces, alerte)
assert je["action"] == "arrêt" and D.etat_lire()["suspendu"]["raison"] == "erreur" and len(alertes) == 1 and "reprendre" in alertes[0] and "jeton-faux" not in alertes[0] and "arrêt" in journal()
fx.panne = False; assert D.cmd_jour(reel, False, JOUR, fx.api, fx.acces, alerte)["action"] == "arrêt" and len(alertes) == 1 and not fx.appels[1:]     # suspendu : plus aucun appel, pas de seconde alerte
assert D.cmd_preparer(conf, FICHE_SITE, False, JOUR, IDENT, alerte)["action"] == "arrêt"
D.reprendre(); assert "suspendu" not in D.etat_lire() and D.cmd_jour(reel, False, JOUR, fx.api, fx.acces, alerte)["action"] == "aperçu posté"
# Discord sans accès (jeton ou salon manquant) : pas d'aperçu, signalé, devis intact, nouvel essai plus tard
effacer(); fx = Faux(); D.cmd_preparer(conf, FICHE_PAGE, False, JOUR, IDENT, alerte)
assert D.cmd_jour(reel, False, JOUR, fx.api, lambda: None, alerte)["action"] == "aperçu impossible" and D.etat_lire()["devis"]["DEV-2026-001"]["statut"] == "préparé" and "suspendu" not in D.etat_lire()
# fichier introuvable pendant la préparation (disque) : arrêt + alerte
effacer(); real_ecrire = D.ecrire_sortie
def casse(*a, **k): raise OSError("disque plein")
D.ecrire_sortie = casse; rr = D.cmd_preparer(conf, FICHE_PAGE, False, JOUR, IDENT, alerte); D.ecrire_sortie = real_ecrire
assert rr["action"] == "arrêt" and D.etat_lire()["suspendu"] and alertes and not D.etat_lire()["devis"]; D.reprendre()

# --- boucle : verrou, arrêt de secours, Jarvis arrêté, suspension ---
def boucle(**k):
    t = [0.0]
    def dormir(s): t[0] += s
    return D.cmd_continu(reel, False, dormir=dormir, maintenant=lambda: JOUR + timedelta(seconds=t[0]), api=Faux().api, acces=Faux().acces, alerte=alerte, **k)
effacer(); D.ARRET.write_text("1"); assert boucle().startswith("arrêt") and not D.VERROU.exists() and not D.ARRET.exists()              # arrêt de secours
assert boucle(vivant=lambda: False) == "Jarvis s'est arrêté" and not D.VERROU.exists()
e = D.etat_lire(); e["suspendu"] = {"raison": "erreur", "date": "2026-11-04", "detail": ""}; D.etat_ecrire(e); assert boucle().startswith("suspendu"); D.reprendre()
D.VERROU.write_text(str(os.getpid())); assert D.cmd_continu(reel, False) == "déjà lancée"; D.VERROU.unlink()
assert D.cmd_continu(reel, True) == "à blanc" and not D.VERROU.exists()
n_pas = [0]; effacer(); D.cmd_preparer(conf, FICHE_PAGE, False, JOUR, IDENT, alerte)
def vivant_3():
    n_pas[0] += 1; return n_pas[0] < 4
assert boucle(vivant=vivant_3) == "Jarvis s'est arrêté" and D.etat_lire()["devis"]["DEV-2026-001"].get("apercu_id")      # un passage au moins : l'aperçu est posté pendant la boucle

# --- commande « rapide » : UNE ligne « Nom | métier | ville | livrables (virgules) | délai | maintenance oui/non | besoin » ---
LIGNE = "Boulangerie Fictive Dupont | boulangerie | Rouen | photos de la boutique, horaires, bouton d'appel, carte | 8 jours ouvrés | oui | Je veux être appelé"
ft, mq = D.fiche_rapide(LIGNE); assert not mq, mq
fr = D.lire_fiche(ft); assert fr["entreprise"] == "Boulangerie Fictive Dupont" and fr["metier"] == "boulangerie" and fr["ville"] == "Rouen" and fr["offre"] == "page web" and fr["options"] == "maintenance" and fr["delai"] == "8 jours ouvrés" and fr["besoin"] == "Je veux être appelé" and "prix" not in fr
assert D.lire_fiche(D.fiche_rapide(LIGNE.rsplit("|", 2)[0] + "| non")[0])["options"] == "aucune" and "besoin" not in D.lire_fiche(D.fiche_rapide(LIGNE.rsplit("|", 2)[0] + "| non")[0])      # besoin facultatif (6 champs)
assert D.fiche_rapide("Devis : " + LIGNE)[0] == ft and D.fiche_rapide("  DEVIS: " + LIGNE)[0] == ft                       # préfixe « devis : » accepté (Discord)
assert D.lire_fiche(D.fiche_rapide(LIGNE + "\nPrix : 100\nOffre : site complet")[0])["offre"] == "page web"   # le besoin est une donnée : jamais un prix ni une offre
for mauvaise, mot in (("A | b | c | d, e, f | 8 jours ouvrés", "champs"), ("A | b | c | d, e, f | 8 jours ouvrés | oui | x | y"[:0] + "A | b", "champs"), ("A | b | c | d, e, f | 8 jours ouvrés | peut-être", "maintenance"),
                      (" | b | c | d, e, f | 8 jours ouvrés | non", "nom"), ("A |  | c | d, e, f | 8 jours ouvrés | non", "métier"), ("A | b |  | d, e, f | 8 jours ouvrés | non", "ville"), ("", "champs")):
    assert D.fiche_rapide(mauvaise)[0] is None and any(mot in x for x in D.fiche_rapide(mauvaise)[1]), (mauvaise, D.fiche_rapide(mauvaise))
effacer(); fx = Faux(); r = D.cmd_rapide(conf, LIGNE, False, JOUR, IDENT, alerte)
assert r["action"] == "préparé" and r["numero"] == "DEV-2026-001"
q = D.etat_lire()["devis"]["DEV-2026-001"]; assert q["statut"] == "préparé" and q["prix"] == 595 and "acompte" not in q and q["lien_paiement"] == D.LIEN_PAGE and q["maintenance"] is True and q["offre_nom"] == "Page web"
t = (D.DOSSIER / "DEV-2026-001.txt").read_text(encoding="utf-8")
for x in ("595 €", "en une fois", "49 € par mois", "8 jours ouvrés", "photos de la boutique", "bouton d'appel", "Je veux être appelé", "https://buy.stripe.com/bJebJ2ceVdZjbLN0ly5EY06", "TVA non applicable"): assert x in t, x
assert "acompte" not in t.lower() and "acompte" not in (D.DOSSIER / "DEV-2026-001-message.txt").read_text(encoding="utf-8").lower()
assert "attention de" not in t and (D.DOSSIER / "DEV-2026-001.pdf").read_bytes().startswith(b"%PDF") and (D.DOSSIER / "DEV-2026-001-message.txt").read_text(encoding="utf-8").startswith("Objet : Devis page web pour Boulangerie Fictive Dupont\n\nBonjour,")
assert not fx.appels and not alertes                                                          # simulation : aucun Discord, aucune alerte
effacer(); D.cmd_rapide(conf, LIGNE.replace("| oui |", "| non |"), False, JOUR, IDENT, alerte); assert "49 €" not in (D.DOSSIER / "DEV-2026-001.txt").read_text(encoding="utf-8")
# un seul devis en validation, à blanc, champ manquant ou invalide : rien créé, numéro non brûlé
assert D.cmd_rapide(conf, LIGNE, False, JOUR, IDENT, alerte)["action"] == "refusé"
effacer(); assert D.cmd_rapide(conf, LIGNE, True, JOUR, IDENT, alerte)["action"] == "à blanc" and not D.ETAT.exists() and not list(D.DOSSIER.glob("*"))
for ligne, mot in ((LIGNE.replace("8 jours ouvrés", "bientôt"), "délai"), (LIGNE.replace("8 jours ouvrés", "8 jours"), "ouvrés"), (LIGNE.replace("photos de la boutique, horaires, bouton d'appel, carte", "photos, horaires"), "livrables"),
                   (LIGNE.replace("photos de la boutique, horaires, bouton d'appel, carte", "a, b, c, d, e, f"), "livrables"), (LIGNE.replace("| oui |", "| peut-être |"), "maintenance")):
    r = D.cmd_rapide(conf, ligne, False, JOUR, IDENT, alerte); assert r["action"] in ("information manquante",) and any(mot in x for x in r["manques"]), (ligne, r)
    assert not list(D.DOSSIER.glob("*")) and not D.etat_lire()["devis"]
assert D.cmd_rapide(conf, LIGNE, False, JOUR, IDENT, alerte)["numero"] == "DEV-2026-001"      # numéro non brûlé

# --- « devis : … » depuis le salon Discord de Jarvis : mode réel seulement, Liam SEUL, une fois, réponse = aperçu « à valider » ---
effacer(); fx = Faux()
assert D.cmd_jour(reel, False, JOUR, fx.api, fx.acces, alerte)["action"] == "rien" and not D.etat_lire()["devis"]      # 1er passage : curseur posé, l'historique du salon n'est jamais rejoué
fx.liam("devis : " + LIGNE, uid="777"); assert D.cmd_jour(reel, False, JOUR, fx.api, fx.acces, alerte)["action"] == "rien" and not D.etat_lire()["devis"]   # autre personne : ignoré
fx.n += 1; fx.msgs.append({"id": str(fx.n), "content": "devis : " + LIGNE, "author": {"id": "42", "bot": True}}); assert D.cmd_jour(reel, False, JOUR, fx.api, fx.acces, alerte)["action"] == "rien" and not D.etat_lire()["devis"]   # un bot : ignoré
nb = len(fx.msgs); fx.liam("devis : " + LIGNE); jr = D.cmd_jour(reel, False, JOUR, fx.api, fx.acces, alerte)
assert jr["action"] == "en attente du ok" and D.etat_lire()["devis"]["DEV-2026-001"]["statut"] == "préparé" and (D.DOSSIER / "DEV-2026-001.pdf").exists(), jr
rep = [x["content"] for x in fx.msgs[nb + 1:] if x["author"]["bot"]]; assert len(rep) == 1 and "à valider" in rep[0] and "DEV-2026-001" in rep[0] and "595 €" in rep[0] and D.LIEN_PAGE in rep[0] and "acompte" not in rep[0].lower() and "49 €" in rep[0] and "ok devis" in rep[0]
assert D.etat_lire()["devis"]["DEV-2026-001"]["apercu_id"]
D.cmd_jour(reel, False, JOUR, fx.api, fx.acces, alerte); assert len(D.etat_lire()["devis"]) == 1 and len([x for x in fx.msgs if x["author"]["bot"]]) == 2    # le même message n'est jamais retraité
fx.liam("devis : " + LIGNE.replace("Fictive", "Autre")); D.cmd_jour(reel, False, JOUR, fx.api, fx.acces, alerte)
assert len(D.etat_lire()["devis"]) == 1 and "DEV-2026-001" in fx.msgs[-1]["content"] and "un seul devis" in fx.msgs[-1]["content"]                   # un seul devis à la fois : réponse claire
fx.liam("ok devis"); assert D.cmd_jour(reel, False, JOUR, fx.api, fx.acces, alerte)["action"] == "validé"                                              # la validation habituelle continue de marcher
fx.liam("devis : " + LIGNE.replace("8 jours ouvrés", "bientôt")); D.cmd_jour(reel, False, JOUR, fx.api, fx.acces, alerte)
assert len(D.etat_lire()["devis"]) == 1 and "non créé" in fx.msgs[-1]["content"] and "délai" in fx.msgs[-1]["content"] and "bientôt" not in fx.msgs[-1]["content"] and not alertes     # champ invalide : signalé à Liam, rien créé
effacer(); fx = Faux(); fx.liam("devis : " + LIGNE)
assert D.cmd_jour(conf, False, JOUR, fx.api, fx.acces, alerte)["action"] == "rien" and not fx.appels and not D.etat_lire()["devis"]                       # simulation : le salon n'est jamais lu

# --- règles de sécurité sur le code lui-même ---
src = (Path(D.__file__)).read_text(encoding="utf-8")
assert not re.search(r"smtplib|send_message|gmail_api|api\.stripe\.com|stripe\.com/v1|sk_live|sk_test|\bimport stripe\b|getpass|input\(", src), "l'agent n'envoie rien au client, n'écrit pas chez Stripe, ne saisit aucun mot de passe"
assert not re.search(r"print\([^)]*(jeton|token|password|mot_de_passe)", src, re.I)
import shutil; shutil.rmtree(tmp, ignore_errors=True)
print("OK : tous les tests de l'agent devis passent")
