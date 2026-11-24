#!/usr/bin/env python3
"""Agent devis (LM MULTI-SERVICES) : à partir d'une fiche client en texte, prépare un devis écrit (texte + PDF) et le message d'accompagnement dans B2B\\devis\\, numéro unique DEV-AAAA-NNN,
puis montre un aperçu « à valider » à Liam sur Discord. RIEN ne part vers le client : l'agent n'a aucune fonction d'envoi (e-mail, Messenger, Stripe en écriture). Liam envoie lui-même, après son « ok ».
Même architecture que prospection.py et instagram.py : script autonome, réglages, état, verrou, arrêt de secours, alerte Discord, journal.

  python agents\\devis.py preparer fiche.txt [--a-blanc]   crée le devis (simulation par défaut : fichiers écrits, rien sur Discord) ; --a-blanc : aucune écriture
  python agents\\devis.py rapide "Nom | métier | ville | livrables, séparés, par des virgules | délai | oui/non | besoin"   idem à partir d'UNE ligne (page web 500 €) ; aussi « devis : … » dans le salon Discord (mode réel)
  python agents\\devis.py jour [--a-blanc]               un passage : poste l'aperçu « à valider » (mode réel) ou lit le « ok devis » de Liam
  python agents\\devis.py continu [--pid N]                boucle (lancée par Jarvis, lib\\devis.ps1) : un passage toutes les cycle_minutes
  python agents\\devis.py etat                             liste des devis et de leur statut
  python agents\\devis.py marquer DEV-AAAA-NNN valide|envoye|accepte|paye   Liam coche à la main (statuts dans l'ordre, jamais de saut)
  python agents\\devis.py annuler DEV-AAAA-NNN             libère la place d'un devis préparé ou validé (jamais d'un devis envoyé)
  python agents\\devis.py arreter | reprendre              arrêt de secours de la boucle | lève la suspension après une erreur

Prix et liens de paiement : UNIQUEMENT ceux de docs\\OFFRE-REFERENCE.json (page web 500 € ou site complet 994 €, une fois, puis 29 €/mois avec hébergement, maintenance, support et nom de domaine,
premier mois offert, arrêt à tout moment ; le lien Stripe comprend l'abonnement, 15/11/2026). Le devis donne directement ce lien. Une information absente de la fiche ou des sources (délai, livrables, option sans prix,
lien de paiement sur mesure) est SIGNALÉE et l'agent s'arrête : rien n'est inventé.
Statut de paiement : l'agent n'accède ni à la banque ni à Stripe ; Liam coche « payé » à la main (`marquer`). Un seul devis à la fois « préparé » (en cours de validation).
envoi_automatique = false (défaut) : SIMULATION (aucun message Discord ; Liam valide en ligne de commande). true : aperçu et lecture du « ok devis » sur Discord (toujours rien vers le client)."""
import argparse, json, re, sys, time, unicodedata
from datetime import datetime, timedelta
from pathlib import Path
import textwrap

ICI = Path(__file__).resolve().parent
RACINE = ICI.parent
sys.path.insert(0, str(ICI))
import machine as M   # config locale (<agent>-config.local.json) et machine active (b2b.local.json)
DOSSIER = RACINE / "devis"
CONFIG, ETAT, IDENTITE = ICI / "devis-config.json", ICI / "devis-etat.json", ICI / "identite.json"
ARRET, VERROU, JOURNAL = ICI / "devis.arret", ICI / "devis-continu.verrou", ICI / "devis-journal.log"
DEFAUT = {"envoi_automatique": False, "cycle_minutes": 3, "salon_nom": ""}
STATUTS = ["préparé", "validé", "envoyé", "accepté", "payé"]

# Source : docs\OFFRE-REFERENCE.json (= liens-paiement.md, 15/11/2026). Rien d'autre n'est un prix. Un lien = le prix unique + l'abonnement de 29 €/mois (premier mois offert).
PRIX_PAGE, PRIX_SITE_LIEN, MAINTENANCE, VALIDITE_JOURS = 500, 994, 29, 15
LIEN_PAGE = "https://buy.stripe.com/14AfZifr7dZj7vxc4g5EY0c"      # « Pack page web » 500 € puis 29 €/mois, 1er mois offert (OFFRE-REFERENCE.json)
LIEN_SITE = "https://buy.stripe.com/8x23cwgvb1cx3fhgkw5EY0d"      # « Site complet » 994 € puis 29 €/mois, 1er mois offert (OFFRE-REFERENCE.json)
ABONNEMENT = f"Ensuite {MAINTENANCE} € par mois (hébergement, maintenance, support et nom de domaine compris), premier mois offert, arrêt possible à tout moment ; cet abonnement est inclus dans le lien de paiement."
OFFRES = {"page": "Page web", "site": "Site complet"}
ALIAS = {"entreprise": "entreprise", "nomdelentreprise": "entreprise", "societe": "entreprise", "metier": "metier", "ville": "ville", "contact": "contact", "nom": "contact", "nomducontact": "contact",
         "client": "contact", "email": "email", "mail": "email", "courriel": "email", "telephone": "telephone", "tel": "telephone", "offre": "offre", "offrechoisie": "offre", "prix": "prix",
         "options": "options", "option": "options", "delai": "delai", "livrables": "livrables", "elements": "livrables", "besoin": "besoin"}


# --- réglages, état, journal ---------------------------------------------------------------------------------------
def cfg():
    c = dict(DEFAUT)
    if CONFIG.exists(): c.update({k: v for k, v in json.loads(CONFIG.read_text(encoding="utf-8-sig")).items() if not k.startswith("_")})
    return M.surcharge_locale(CONFIG, c)


def etat_lire():
    e = json.loads(ETAT.read_text(encoding="utf-8")) if ETAT.exists() else {}
    e.setdefault("devis", {}); e.setdefault("alertes", {}); e.setdefault("ok_utilises", [])
    return e


def etat_ecrire(e): ETAT.write_text(json.dumps(e, ensure_ascii=False, indent=1), encoding="utf-8")


def journaliser(action, detail="", a_blanc=False):
    """Une ligne par action : date heure | action | détail. Jamais de coordonnées du client, de jeton ni de mot de passe."""
    if a_blanc: return
    with open(JOURNAL, "a", encoding="utf-8") as f: f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} | {action} | {detail}\n")


def identite_lire():
    try: return json.loads(IDENTITE.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError): return {}


def euros(n): return f"{n:,}".replace(",", " ") + " €"


def _norm(s): return re.sub(r"[^a-z0-9]", "", "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn"))


# --- la fiche client -------------------------------------------------------------------------------------------------
def lire_fiche(texte):
    """« Clé : valeur » (accents, majuscules et alias sans importance) ; une ligne sans clé connue prolonge la valeur précédente. -> dict (vide si rien de reconnu)."""
    f, cle = {}, None
    for l in texte.splitlines():
        if l.lstrip().startswith("#"): continue   # commentaire du modèle de fiche
        m = re.match(r"\s*([^:]{1,40}?)\s*:\s*(.*)$", l); a = ALIAS.get(_norm(m.group(1))) if m else None
        if a: cle = a; f[a] = m.group(2).strip()
        elif cle and l.strip(): f[cle] = (f[cle] + "\n" + l.strip()).strip()
    return f


def _entier(s):
    m = re.match(r"\s*(\d[\d   ]*)", s or ""); return int(re.sub(r"\D", "", m.group(1))) if m else None


def construire(f, ident, numero, jour, rapide=False):
    """-> (devis, []) ou (None, [ce qui manque ou n'a pas de source]). Aucun prix, délai ni livrable inventé. rapide : ligne « rapide », sans contact ni coordonnées (Liam envoie lui-même)."""
    m = []
    for cle, lib in (("entreprise", "entreprise (nom de l'entreprise du client)"), ("metier", "métier"), ("ville", "ville"), ("offre", "offre choisie (page web ou site complet)")) + (() if rapide else (("contact", "contact (nom du client)"),)):
        if not f.get(cle): m.append(lib)
    if f.get("contact") and not rapide and not (f.get("email") or f.get("telephone")): m.append("contact : e-mail ou téléphone du client")
    for cle in ("prenom_nom", "entreprise", "siret", "telephone", "email_reponse"):
        if not str(ident.get(cle, "")).strip(): m.append(f"identité LM MULTI-SERVICES : « {cle} » vide (agents\\identite.json)")
    offre = None
    if f.get("offre"):
        n = _norm(f["offre"]); offre = "site" if "complet" in n or n.startswith("site") else "page" if "page" in n else None
        if not offre: m.append(f"offre : « {f['offre']} » inconnue (page web {euros(PRIX_PAGE)} ou site complet {euros(PRIX_SITE_LIEN)})")
    prix, lien, pv = None, None, _entier(f.get("prix"))
    if offre == "page":
        prix, lien = PRIX_PAGE, LIEN_PAGE
        if pv and pv != PRIX_PAGE: m.append(f"prix : la page web est à {euros(PRIX_PAGE)} (docs\\KIT-RDV-15MIN.md), pas {euros(pv)}")
    elif offre == "site":
        if pv and pv != PRIX_SITE_LIEN: m.append(f"prix : le site complet est à {euros(PRIX_SITE_LIEN)} (docs\\OFFRE-REFERENCE.json), pas {euros(pv)} ; un autre montant demande un lien Stripe créé par Liam")
        else: prix, lien = PRIX_SITE_LIEN, LIEN_SITE
    dj = _entier((re.search(r"\d+\s*jours?", f.get("delai", "")) or [""])[0])
    if not dj: m.append("délai : un nombre de jours ouvrés est nécessaire dans la fiche (aucun délai n'est inventé)")
    elif "ouvr" not in _norm(f["delai"]): m.append("délai : précise « jours ouvrés » dans la fiche"); dj = None
    livrables = [x.strip(" -•\t") for x in re.split(r"[;\n]", f.get("livrables", "")) if x.strip(" -•\t")]
    if not 3 <= len(livrables) <= 5: m.append(f"livrables : 3 à 5 éléments séparés par « ; » (la fiche en donne {len(livrables)}) : aucun livrable inventé")
    maintenance = False
    for o in (x.strip() for x in re.split(r"[;,]", f.get("options", ""))):
        if _norm(o) in ("", "aucune", "aucun", "non", "sans"): continue
        if "maintenance" in _norm(o): maintenance = True
        else: m.append(f"option « {o} » : aucun prix dans docs\\KIT-RDV-15MIN.md ni docs\\liens-paiement.md (jamais inventé)")
    if m: return None, m
    return {"numero": numero, "date": str(jour.date()), "date_fr": f"{jour:%d/%m/%Y}", "valide_jusqu": str((jour + timedelta(days=VALIDITE_JOURS)).date()), "valide_fr": f"{jour + timedelta(days=VALIDITE_JOURS):%d/%m/%Y}",
            "entreprise": f["entreprise"], "metier": f["metier"], "ville": f["ville"], "contact": f.get("contact", ""), "offre": offre, "offre_nom": OFFRES[offre], "prix": prix,
            "lien_paiement": lien, "maintenance": maintenance, "delai_jours": dj, "livrables": livrables, "besoin": f.get("besoin", "").strip(), "emetteur": {k: str(ident[k]).strip() for k in ("prenom_nom", "entreprise", "siret", "telephone", "email_reponse")}}, []


# --- le devis écrit : mêmes blocs pour le texte et le PDF ---------------------------------------------------------------
def _siret(s): d = re.sub(r"\D", "", s); return f"{d[:3]} {d[3:6]} {d[6:9]} {d[9:]}" if len(d) == 14 else s


def blocs_devis(d):
    e = d["emetteur"]; b = [("h1", e["entreprise"]), ("p", f"{e['prenom_nom']}, entreprise individuelle · SIRET {_siret(e['siret'])}"), ("p", f"Téléphone {e['telephone']} · {e['email_reponse']}"),
                            ("p", "TVA non applicable, art. 293 B du CGI (franchise de TVA)."), ("sep", ""), ("h1", f"Devis n° {d['numero']}"),
                            ("p", f"Date : {d['date_fr']} · valable {VALIDITE_JOURS} jours, jusqu'au {d['valide_fr']}"), ("sep", ""), ("h2", "Client"),
                            ("p", f"{d['entreprise']} ({d['metier']}), {d['ville']}")] + ([("p", f"À l'attention de {d['contact']}")] if d["contact"] else [])
    if d["besoin"]: b += [("sep", ""), ("h2", "Ce que vous souhaitez"), ("p", d["besoin"])]
    b += [("sep", ""), ("h2", "Ce qui est livré"), ("p", f"{d['offre_nom']} pour {d['entreprise']} :")] + [("li", x) for x in d["livrables"]]
    b += [("sep", ""), ("h2", "Prix"), ("p", f"Prix {'de la' if d['offre'] == 'page' else 'du'} {d['offre_nom'].lower()} : {euros(d['prix'])}"),
          ("p", f"Paiement en une fois à la commande : {euros(d['prix'])}, avec le lien ci-dessous.")]
    b.append(("p", ABONNEMENT))
    b += [("sep", ""), ("h2", "Délai"), ("p", f"{d['delai_jours']} jours ouvrés après réception du paiement et de vos photos."), ("sep", ""), ("h2", "Régler"),
          ("p", f"Lien de paiement ({euros(d['prix'])}) :"), ("p", d["lien_paiement"]), ("sep", ""), ("h2", "Conditions"),
          ("li", "Vous validez ce devis et réglez avec le lien ci-dessus ; je commence dès le paiement reçu."),
          ("li", "Je vous montre un aperçu privé : la mise en ligne a lieu après votre validation de l'aperçu."),
          ("li", f"Devis valable {VALIDITE_JOURS} jours.")]
    return b


def _lignes(blocs, largeur=0.58):
    """Blocs -> lignes (style, texte) avec retour à la ligne (largeur de caractère prudente : jamais de dépassement de page)."""
    out = []
    for s, t in blocs:
        if s == "sep": out.append(("sep", "")); continue
        taille = 16 if s == "h1" else 12 if s == "h2" else 10; n = int(483 / (taille * largeur))
        suite = textwrap.wrap(t.replace("\r", ""), n, subsequent_indent="  " if s == "li" else "", break_long_words=True) if s != "li" else textwrap.wrap("- " + t, n, subsequent_indent="  ")
        out += [(s, x) for x in (suite or [""])]
    return out


def texte_devis(d): return "\n".join("" if s == "sep" else x for s, x in _lignes(blocs_devis(d), 0.4)) + "\n"


def texte_message(d):
    e = d["emetteur"]; kind = d["offre_nom"].lower()
    l = [f"Objet : Devis {kind} pour {d['entreprise']}", "", (f"Bonjour {d['contact']}," if d["contact"] else "Bonjour,"), "Merci pour notre échange. Voici ce que je vous propose, comme convenu.", ""]
    if d["besoin"]: l.append(f"Ce que vous voulez (vos mots) : {d['besoin']}")
    l += [f"Ce que je réalise : {d['offre_nom']} : " + ", ".join(d["livrables"]) + ".", f"Délai : {d['delai_jours']} jours ouvrés après réception du paiement et de vos photos.",
          f"Prix : {euros(d['prix'])}, réglé en une fois à la commande. Je vous montre un aperçu privé ; la mise en ligne a lieu après votre validation."]
    l.append(ABONNEMENT)
    l += [f"Lien de paiement : {d['lien_paiement']}", f"Le devis n° {d['numero']} est joint (PDF). Devis valable {VALIDITE_JOURS} jours, jusqu'au {d['valide_fr']}.", "",
          "Cordialement,", f"{e['prenom_nom']}, {e['entreprise']}, SIRET {_siret(e['siret'])}", "TVA non applicable, art. 293 B du CGI."]
    return "\n".join(l) + "\n"


def _esc(s): return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def pdf_devis(d):
    """PDF A4 minimal (polices Helvetica standard, aucune dépendance) ; plusieurs pages si besoin."""
    pages, y = [[]], 786.0
    for s, x in _lignes(blocs_devis(d)):
        taille = {"h1": 16, "h2": 12}.get(s, 10)
        if s == "sep": y -= 8; continue
        if s in ("h1", "h2") and y < 786: y -= taille * 0.4
        if y < 56 + taille: pages.append([]); y = 786.0
        pages[-1].append(f"BT /{'F2' if s in ('h1', 'h2') else 'F1'} {taille} Tf 1 0 0 1 56 {y:.1f} Tm (" + _esc(x) + ") Tj ET"); y -= taille * 1.45
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>", ("<< /Type /Pages /Kids [" + " ".join(f"{5 + 2 * i} 0 R" for i in range(len(pages))) + f"] /Count {len(pages)} >>").encode(),
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>", b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>"]
    for i, p in enumerate(pages):
        flux = "\n".join(p).encode("cp1252", "replace")
        objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {6 + 2 * i} 0 R >>".encode())
        objs.append(f"<< /Length {len(flux)} >>\nstream\n".encode() + flux + b"\nendstream")
    sortie, offs = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"), []
    for i, o in enumerate(objs, 1): offs.append(len(sortie)); sortie += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    xref = len(sortie); sortie += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode() + "".join(f"{o:010d} 00000 n \n" for o in offs).encode()
    return bytes(sortie + f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())


def numero_suivant(etat, annee):
    """DEV-AAAA-NNN : après le plus grand numéro de l'année, dans l'état ET dans les fichiers déjà présents (jamais de réutilisation ni d'écrasement)."""
    vus = [int(m.group(1)) for n in list(etat.get("devis", {})) + ([p.name for p in DOSSIER.glob(f"DEV-{annee}-*")] if DOSSIER.exists() else []) for m in [re.match(rf"DEV-{annee}-(\d{{3}})", n)] if m]
    return f"DEV-{annee}-{max(vus, default=0) + 1:03d}"


def ecrire_sortie(d):
    DOSSIER.mkdir(parents=True, exist_ok=True); n = d["numero"]
    (DOSSIER / f"{n}.txt").write_text(texte_devis(d), encoding="utf-8"); (DOSSIER / f"{n}.pdf").write_bytes(pdf_devis(d)); (DOSSIER / f"{n}-message.txt").write_text(texte_message(d), encoding="utf-8")


# --- Discord : alerte, aperçu, « ok devis » de Liam SEUL ---------------------------------------------------------------------
def acces_discord_reel():
    """(jeton, salon, uid) du bot Jarvis (secrets lus dans Jarvis\\.env par prospection.py, jamais affichés) ou None."""
    import prospection as PR
    nom = cfg()["salon_nom"]; return PR.acces_discord("salon_devis_id" if nom else None, nom or None)


def api_discord_reel(jeton, methode, chemin, corps=None):
    import prospection as PR
    return PR.discord(jeton, methode, chemin, corps)


def alerter_discord(texte):
    try:
        a = acces_discord_reel()
        if not a: return False
        jeton, salon, uid = a
        r = api_discord_reel(jeton, "POST", f"/channels/{salon}/messages", {"content": f"<@{uid}> **Devis** : {texte}"[:1900], "allowed_mentions": {"users": [uid]}})
        return bool(r and "id" in r)
    except Exception as ex: print(f"  alerte Discord impossible ({type(ex).__name__})"); return False


def alerter(etat, cle, texte, alerte, jour, a_blanc=False):
    """Une alerte par motif et par jour."""
    k = f"{jour}|{cle}"
    if a_blanc or etat["alertes"].get(k): return
    etat["alertes"][k] = True; etat_ecrire(etat); journaliser("alerte", f"{cle} : {texte}"[:300]); alerte(texte)


OK_DEVIS = re.compile(r"\s*ok\s+devis(?:\s+(DEV-\d{4}-\d{3}))?\s*[.!]*\s*", re.I)


def texte_apercu(num, v, uid):
    return (f"<@{uid}> **Devis {num} : à valider** — {v['entreprise']} ({v['ville']})\n{v['offre_nom']} {euros(v['prix'])} en une fois · délai {v['delai_jours']} jours ouvrés"
            + f" · puis {MAINTENANCE} €/mois (1er mois offert, inclus dans le lien)" + f"\nLien de paiement : {v.get('lien_paiement', '')}\nFichiers : devis\\{num}.pdf, devis\\{num}.txt, devis\\{num}-message.txt\n"
            f"Réponds `ok devis` (ou ✅ sur ce message) pour valider. **Rien ne part vers le client** : tu l'envoies toi-même, puis `python agents\\devis.py marquer {num} envoye`.")[:1900]


def cherche_ok(api, jeton, salon, uid, mid, num, utilises):
    """Id du message « ok devis » (ou « ok devis DEV-… » du bon numéro) écrit par Liam APRÈS l'aperçu ; '✅' si c'est une réaction de Liam ; None sinon ; False si Discord est illisible."""
    react = api(jeton, "GET", f"/channels/{salon}/messages/{mid}/reactions/%E2%9C%85?limit=100"); suite = api(jeton, "GET", f"/channels/{salon}/messages?after={mid}&limit=100")
    if suite is None: return False
    if any(str(u.get("id")) == uid for u in react or []): return "✅"
    for x in sorted(suite, key=lambda x: int(x["id"])):
        a = x.get("author", {}); m = OK_DEVIS.fullmatch(x.get("content", ""))
        if str(a.get("id")) == uid and not a.get("bot") and m and x["id"] not in utilises and (not m.group(1) or m.group(1).upper() == num): return x["id"]
    return None


def _passer(v, statut, jour):
    v["statut"] = statut; v.setdefault("historique", {})[statut] = jour


# --- les commandes ----------------------------------------------------------------------------------------------------------
def _arret(etat, genre, detail, alerte, jour, a_blanc, fin):
    if not a_blanc: etat["suspendu"] = {"raison": genre, "date": jour, "detail": detail[:200]}; etat_ecrire(etat)
    alerter(etat, f"arret|{genre}", f"Agent devis arrêté ({genre}) : {detail}. Rien n'est envoyé au client. Vérifie puis `python agents\\devis.py reprendre`.", alerte, jour, a_blanc)
    return fin("arrêt", f"{genre} : {detail}", raison=genre)


def _fin(a_blanc):
    def fin(action, detail="", **k):
        journaliser(action, detail, a_blanc); print(f"  Devis : {action}" + (f" ({detail})" if detail else "")); return {"action": action, **k}
    return fin


def fiche_rapide(ligne):
    """« Nom | métier | ville | livrables (virgules) | délai | maintenance oui/non | besoin (facultatif) » -> (texte de fiche, []) ou (None, [problèmes]). Offre = page web (seul prix connu sans décision de Liam) ;
    aucun prix n'est lu dans la ligne : le besoin du client est une donnée, jamais un ordre."""
    ligne = re.sub(r"^\s*devis\s*:\s*", "", " ".join((ligne or "").split()), flags=re.I); c = [x.strip() for x in ligne.split("|")]
    if len(c) < 6: return None, [f"ligne rapide : il faut au moins 6 champs séparés par « | » : Nom | métier | ville | livrables (virgules) | délai | maintenance oui/non | besoin (facultatif) ; la ligne en a {len(c) if ligne else 0}"]
    nom, metier, ville, livr, delai, maint, besoin = c[:6] + [" | ".join(c[6:])]
    m = [f"{lib} : vide" for lib, v in (("nom", nom), ("métier", metier), ("ville", ville)) if not v]
    mt = _norm(maint)
    if mt not in ("oui", "non"): m.append(f"maintenance : « {maint[:20]} » invalide (oui ou non)")
    if m: return None, m
    lignes = [f"Entreprise : {nom}", f"Métier : {metier}", f"Ville : {ville}", "Offre : page web", "Options : " + ("maintenance" if mt == "oui" else "aucune"), f"Délai : {delai}",
              "Livrables : " + " ; ".join(x.strip() for x in livr.split(",") if x.strip())] + ([f"Besoin : {besoin}"] if besoin else [])
    return "\n".join(lignes) + "\n", []


def cmd_rapide(conf, ligne, a_blanc=False, maintenant=None, ident=None, alerte=None):
    """Une ligne -> fiche interne -> `preparer` (PDF + texte + message, statut « préparé »). Champ manquant ou invalide : signalé, rien créé."""
    ft, mq = fiche_rapide(ligne)
    if mq:
        for x in mq: print("  À COMPLÉTER : " + x)
        return _fin(a_blanc)("information manquante", f"{len(mq)} point(s) : " + " | ".join(mq)[:300], manques=mq)
    return cmd_preparer(conf, ft, a_blanc, maintenant, ident, alerte, rapide=True)


def cmd_preparer(conf, texte_fiche, a_blanc=False, maintenant=None, ident=None, alerte=None, rapide=False):
    """Fiche -> devis (txt, pdf, message) dans devis\\, état « préparé ». -> {"action": préparé | à blanc | information manquante | refusé | arrêt}."""
    maintenant = maintenant or datetime.now(); jour = str(maintenant.date()); alerte = alerte or alerter_discord; etat = etat_lire(); fin = _fin(a_blanc)
    if etat.get("suspendu"): return fin("arrêt", "suspendu : " + etat["suspendu"]["raison"], raison=etat["suspendu"]["raison"])
    num = numero_suivant(etat, maintenant.year); d, manques = construire(lire_fiche(texte_fiche), ident if ident is not None else identite_lire(), num, maintenant, rapide)
    if manques:
        for x in manques: print("  À COMPLÉTER : " + x)
        return fin("information manquante", f"{len(manques)} point(s) : " + " | ".join(manques)[:300], manques=manques)
    cours = [n for n, v in etat["devis"].items() if v.get("statut") == "préparé"]
    if cours: return fin("refusé", f"un seul devis à la fois en cours de validation : {cours[0]} attend le « ok » de Liam (valider avec `marquer {cours[0]} valide` ou annuler)", raison=f"{cours[0]} attend la validation", numero=cours[0])
    if a_blanc: return fin("à blanc", f"{num} serait préparé : {d['offre_nom']} {euros(d['prix'])} en une fois (rien écrit)", numero=num)
    try:
        ecrire_sortie(d)
        etat["devis"][num] = {"statut": "préparé", "historique": {"préparé": jour}, "entreprise": d["entreprise"], "metier": d["metier"], "ville": d["ville"], "offre_nom": d["offre_nom"], "prix": d["prix"],
                              "maintenance": d["maintenance"], "delai_jours": d["delai_jours"], "lien_paiement": d["lien_paiement"]}
        etat_ecrire(etat)
    except Exception as ex: return _arret(etat, "erreur", f"écriture du devis impossible ({type(ex).__name__})", alerte, jour, a_blanc, fin)
    return fin("préparé", f"{num} | {d['entreprise']} | {d['offre_nom']} {euros(d['prix'])}", numero=num, dossier=str(DOSSIER))


LIGNE_DISCORD = re.compile(r"\s*devis\s*:\s*(.+)", re.I | re.S)


def _recevoir_discord(conf, maintenant, api, acces, alerte):
    """Mode réel seulement : une ligne « devis : Nom | métier | ville | … » écrite par Liam SEUL dans le salon crée le devis (comme `rapide`) et reçoit l'aperçu « à valider » en réponse.
    Le curseur du salon est posé au 1er passage (l'historique n'est jamais rejoué) puis avancé AVANT le traitement : un message n'est jamais traité deux fois."""
    a = acces()
    if not a: return
    jeton, salon, uid = a; etat = etat_lire(); cur = etat.get("discord_curseur")
    if cur is None:
        dernier = api(jeton, "GET", f"/channels/{salon}/messages?limit=1")
        if dernier is None: return
        etat["discord_curseur"] = str(max((int(x["id"]) for x in dernier), default=0)); etat_ecrire(etat); return
    suite = api(jeton, "GET", f"/channels/{salon}/messages?after={cur}&limit=100")
    if not suite: return
    suite = sorted(suite, key=lambda x: int(x["id"])); etat["discord_curseur"] = str(suite[-1]["id"]); etat_ecrire(etat)

    def repondre(texte): return api(jeton, "POST", f"/channels/{salon}/messages", {"content": f"<@{uid}> {texte}"[:1900], "allowed_mentions": {"users": [uid]}})
    for x in suite:
        au = x.get("author", {}); m = LIGNE_DISCORD.fullmatch(x.get("content", ""))
        if not (m and str(au.get("id")) == uid and not au.get("bot")): continue
        journaliser("ligne devis reçue sur Discord", f"{len(m.group(1).split('|'))} champ(s)")
        r = cmd_rapide(conf, m.group(1), False, maintenant, None, alerte)
        if r["action"] == "préparé":
            e = etat_lire(); rep = repondre(texte_apercu(r["numero"], e["devis"][r["numero"]], uid).split("> ", 1)[1])
            if rep and "id" in rep: e["devis"][r["numero"]]["apercu_id"] = str(rep["id"]); etat_ecrire(e)
        elif r["action"] == "information manquante": repondre("**Devis non créé**, à compléter : " + " ; ".join(r["manques"]))
        elif r["action"] == "refusé": repondre(f"**Devis non créé** : un seul devis à la fois en cours de validation ({r['numero']} attend ton `ok devis`).")
        else: repondre("**Devis non créé** : l'agent est suspendu (voir l'alerte), `python agents\\devis.py reprendre`.")


def cmd_jour(conf, a_blanc=False, maintenant=None, api=None, acces=None, alerte=None):
    """Un passage : poste l'aperçu « à valider » puis attend le « ok devis » de Liam. Simulation par défaut (aucun appel Discord). -> {"action": ...}."""
    maintenant = maintenant or datetime.now(); jour = str(maintenant.date()); alerte = alerte or alerter_discord; api = api or api_discord_reel; acces = acces or acces_discord_reel
    etat = etat_lire(); fin = _fin(a_blanc)
    if etat.get("suspendu"): return fin("arrêt", "suspendu : " + etat["suspendu"]["raison"], raison=etat["suspendu"]["raison"])
    if conf["envoi_automatique"] and not a_blanc:
        try: _recevoir_discord(conf, maintenant, api, acces, alerte)
        except Exception as ex: return _arret(etat_lire(), "erreur", type(ex).__name__, alerte, jour, a_blanc, fin)
        etat = etat_lire()
        if etat.get("suspendu"): return {"action": "arrêt"}
    cours = [n for n, v in etat["devis"].items() if v.get("statut") == "préparé"]
    if not cours: return {"action": "rien"}
    num = cours[0]; v = etat["devis"][num]
    if not conf["envoi_automatique"] or a_blanc:
        if not v.get("simule") and not a_blanc: v["simule"] = True; etat_ecrire(etat); journaliser("simulation", f"{num} : aperçu non posté (envoi_automatique = false) ; valider avec `marquer {num} valide`")
        return {"action": "simulation", "numero": num}
    try:
        a = acces()
        if not a: return fin("aperçu impossible" if not v.get("apercu_id") else "lecture impossible", "accès Discord incomplet (jeton, salon ou utilisateur) : nouvel essai au prochain passage", numero=num)
        jeton, salon, uid = a
        if not v.get("apercu_id"):
            r = api(jeton, "POST", f"/channels/{salon}/messages", {"content": texte_apercu(num, v, uid), "allowed_mentions": {"users": [uid]}})
            if not r or "id" not in r: return fin("aperçu impossible", "Discord n'a pas pris le message : nouvel essai au prochain passage", numero=num)
            v["apercu_id"] = str(r["id"]); etat_ecrire(etat); return fin("aperçu posté", f"{num} : aperçu « à valider » envoyé à Liam sur Discord (rien au client)", numero=num)
        ok = cherche_ok(api, jeton, salon, uid, v["apercu_id"], num, etat["ok_utilises"])
        if ok is False: return fin("lecture impossible", "Discord illisible : nouvel essai au prochain passage", numero=num)
        if not ok: return {"action": "en attente du ok", "numero": num}
        if ok != "✅": etat["ok_utilises"].append(ok)
        _passer(v, "validé", jour); etat_ecrire(etat)
        return fin("validé", f"{num} validé par Liam sur Discord : à toi de l'envoyer au client, puis `marquer {num} envoye`", numero=num)
    except Exception as ex: return _arret(etat, "erreur", type(ex).__name__, alerte, jour, a_blanc, fin)


def statut_court(s):
    n = _norm(s or ""); return next((x for x in STATUTS if _norm(x) == n or (n == "paye" and x == "payé")), None)


def cmd_marquer(num, statut, maintenant=None):
    """Liam coche à la main : statuts dans l'ordre (préparé > validé > envoyé > accepté > payé), jamais de saut ni de retour. Aucune lecture de Stripe ni de banque."""
    maintenant = maintenant or datetime.now(); jour = str(maintenant.date()); etat = etat_lire(); fin = _fin(False); st = statut_court(statut); v = etat["devis"].get(num)
    if not v: return fin("refusé", f"{num} : devis inconnu")
    if not st: return fin("refusé", f"statut « {statut} » inconnu (valide, envoye, accepte, paye)")
    cur = v.get("statut")
    if cur not in STATUTS or STATUTS.index(st) != STATUTS.index(cur) + 1: return fin("refusé", f"{num} est « {cur} » : le statut suivant est « {STATUTS[STATUTS.index(cur) + 1] if cur in STATUTS and cur != STATUTS[-1] else 'aucun'} » (jamais de saut ni de retour)")
    _passer(v, st, jour); etat_ecrire(etat); return fin("marqué", f"{num} : {st}", numero=num, statut=st)


def cmd_annuler(num, maintenant=None):
    maintenant = maintenant or datetime.now(); etat = etat_lire(); fin = _fin(False); v = etat["devis"].get(num)
    if not v: return fin("refusé", f"{num} : devis inconnu")
    if v.get("statut") not in ("préparé", "validé"): return fin("refusé", f"{num} est « {v.get('statut')} » : seul un devis préparé ou validé s'annule")
    _passer(v, "annulé", str(maintenant.date())); etat_ecrire(etat); return fin("annulé", f"{num} annulé (le numéro n'est pas réutilisé)", numero=num)


def reprendre():
    e = etat_lire(); s = e.pop("suspendu", None); etat_ecrire(e); journaliser("reprise", f"suspension levée ({s['raison']})" if s else "rien à lever")
    return f"Suspension levée ({s['raison']}) : contrôle les devis (`etat`), la boucle reprendra au prochain lancement." if s else "Aucune suspension."


def cmd_etat():
    e = etat_lire()
    print("Suspendu : " + e["suspendu"]["raison"] if e.get("suspendu") else "Agent actif (aucune suspension).")
    for n, v in sorted(e["devis"].items()): print(f"  {n} | {v['statut']:<12} | {v['entreprise']} | {v['offre_nom']} {euros(v['prix'])}")
    if not e["devis"]: print("  aucun devis.")


# --- boucle, arrêt de secours ------------------------------------------------------------------------------------------------
def processus_vivant(pid):
    try:
        import ctypes
        k = ctypes.windll.kernel32; h = k.OpenProcess(0x1000, False, int(pid))
        if not h: return False
        code = ctypes.c_ulong(); ok = k.GetExitCodeProcess(h, ctypes.byref(code)); k.CloseHandle(h)
        return bool(ok) and code.value == 259
    except (ImportError, AttributeError):
        import os
        try: os.kill(int(pid), 0); return True
        except OSError: return False


def boucle_active():
    try: return VERROU.exists() and processus_vivant(int(VERROU.read_text(encoding="utf-8").strip()))
    except (ValueError, OSError): return False


def cmd_continu(conf, a_blanc=False, dormir=time.sleep, maintenant=datetime.now, api=None, acces=None, alerte=None, vivant=None):
    """Un passage toutes les cycle_minutes jusqu'à l'arrêt : `arreter`, Jarvis arrêté (--pid), suspension après une erreur. Jamais de reprise automatique après une erreur."""
    import os
    if a_blanc: print(f"  [à blanc] boucle devis : un passage toutes les {conf['cycle_minutes']} min, " + ("aperçu et « ok » sur Discord" if conf["envoi_automatique"] else "SIMULATION") + ". Rien lancé."); return "à blanc"
    if boucle_active(): print("Une boucle devis tourne déjà (devis-continu.verrou)."); return "déjà lancée"
    prochain, raison = 0, ""

    def bat():
        VERROU.write_text(str(os.getpid()), encoding="utf-8")
        if ARRET.exists(): return "arrêt demandé"
        if vivant and not vivant(): return "Jarvis s'est arrêté"
        s = etat_lire().get("suspendu"); return f"suspendu ({s['raison']})" if s else ""
    try:
        while not raison:
            raison = bat()
            if raison: break
            if maintenant().timestamp() >= prochain:
                try: cmd_jour(conf, False, maintenant(), api, acces, alerte)
                except Exception as ex:   # filet : une erreur inattendue arrête l'agent et prévient Liam
                    e = etat_lire(); e["suspendu"] = {"raison": "erreur", "date": str(maintenant().date()), "detail": type(ex).__name__}; etat_ecrire(e)
                    journaliser("erreur", type(ex).__name__); (alerte or alerter_discord)(f"Erreur inattendue ({type(ex).__name__}) : l'agent s'arrête. Vérifie puis `python agents\\devis.py reprendre`.")
                prochain = maintenant().timestamp() + conf["cycle_minutes"] * 60
            dormir(5)
    finally:
        VERROU.unlink(missing_ok=True)
        if raison.startswith("arrêt"): ARRET.unlink(missing_ok=True)
        journaliser("boucle arrêtée", raison)
    return raison


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Agent devis LM MULTI-SERVICES (simulation par défaut, rien n'est envoyé au client).")
    ap.add_argument("cmd", choices=["preparer", "rapide", "jour", "continu", "etat", "marquer", "annuler", "arreter", "reprendre"]); ap.add_argument("args", nargs="*")
    ap.add_argument("--a-blanc", action="store_true"); ap.add_argument("--pid", type=int, default=0); a = ap.parse_args(); M.exiger("devis", a.cmd, a.a_blanc); conf = cfg()
    if a.cmd == "preparer":
        if not a.args or not Path(a.args[0]).is_file(): print("Usage : python agents\\devis.py preparer fiche.txt [--a-blanc]"); sys.exit(2)
        r = cmd_preparer(conf, Path(a.args[0]).read_text(encoding="utf-8-sig"), a.a_blanc)
        if r["action"] == "préparé": print(f"  Fichiers : {DOSSIER}\\{r['numero']}.pdf / .txt / -message.txt (aperçu à valider ; rien n'est envoyé)")
        sys.exit(0 if r["action"] in ("préparé", "à blanc") else 2)
    elif a.cmd == "rapide":
        r = cmd_rapide(conf, " ".join(a.args), a.a_blanc)
        if r["action"] == "préparé": print(f"  Fichiers : {DOSSIER}\\{r['numero']}.pdf / .txt / -message.txt (aperçu à valider ; rien n'est envoyé)")
        sys.exit(0 if r["action"] in ("préparé", "à blanc") else 2)
    elif a.cmd == "jour": cmd_jour(conf, a.a_blanc)
    elif a.cmd == "continu": cmd_continu(conf, a.a_blanc, vivant=(lambda: processus_vivant(a.pid)) if a.pid else None)
    elif a.cmd == "etat": cmd_etat()
    elif a.cmd in ("marquer", "annuler"):
        if a.cmd == "marquer" and len(a.args) == 2: sys.exit(0 if cmd_marquer(a.args[0].upper(), a.args[1])["action"] == "marqué" else 2)
        elif a.cmd == "annuler" and len(a.args) == 1: sys.exit(0 if cmd_annuler(a.args[0].upper())["action"] == "annulé" else 2)
        else: print("Usage : marquer DEV-AAAA-NNN valide|envoye|accepte|paye  ·  annuler DEV-AAAA-NNN"); sys.exit(2)
    elif a.cmd == "arreter":
        if boucle_active(): ARRET.write_text(str(int(time.time())), encoding="utf-8"); print("Arrêt demandé : la boucle s'arrête dans quelques secondes.")
        else: ARRET.unlink(missing_ok=True); VERROU.unlink(missing_ok=True); print("Aucune boucle devis en cours.")
    else: print(reprendre())


if __name__ == "__main__":
    main()
