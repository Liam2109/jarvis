#!/usr/bin/env python3
"""Agent Rédaction : un brouillon de message (e-mail + LinkedIn) par prospect, à valider par Liam. N'ENVOIE RIEN.

  python agents\\redaction.py prospects.csv [-o messages-a-valider.md]

Lit : le CSV de prospects (nom, metier, ville, telephone, email, site_actuel ; facultatif : note_besoin, email_type,
email_source, fictif), agents\\identite.json (qui je suis, SIRET, lien de base des maquettes) et suivi-prospects.csv
(les STOP / refusés sont sautés). Écrit : messages-a-valider.md, un bloc par prospect, statut « à valider ».
Règles : aucun chiffre inventé, aucune promesse de classement Google, rien d'affirmé sur le site du prospect sauf
ce qui est écrit dans note_besoin (ou l'absence de site dans le CSV, signalée « à vérifier »)."""
import argparse, csv, json, re, sys
from datetime import date
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "sites" / "moteur"))
import generer as G

IDENTITE = Path(__file__).resolve().parent / "identite.json"
SUIVI = RACINE / "suivi-prospects.csv"
PLURIEL = {"electricien": "électriciens", "plombier": "plombiers", "couvreur": "couvreurs", "macon": "maçons",
           "peintre": "peintres", "menuisier": "menuisiers", "restaurant": "restaurateurs", "commerce": "commerçants",
           "coiffeur": "coiffeurs", "fleuriste": "fleuristes", "boulangerie": "boulangers et pâtissiers", "garage": "garagistes"}
# métiers hors du bâtiment, sans modèle dans generer.py : mot repéré dans le métier -> clé (la clé sert aussi dans agents\liens-metiers.json)
CLES_COMMERCES = [("coiffeur", "coiffeur"), ("fleuri", "fleuriste"), ("boulang", "boulangerie"), ("patisser", "boulangerie"), ("garage", "garage")]
ACCROCHE = {
    "electricien": "Quand quelqu'un a une panne {aville}, il veut trouver un numéro, voir que vous intervenez chez lui et vous joindre en un geste.",
    "plombier": "Quand quelqu'un a une fuite {aville}, il veut trouver un numéro, voir que vous intervenez chez lui et vous joindre en un geste.",
    "couvreur": "Quand quelqu'un a une fuite de toiture {aville}, il veut trouver un numéro, voir que vous intervenez chez lui et vous joindre en un geste.",
    "macon": "Quand quelqu'un a un projet de travaux {aville}, il veut voir ce que vous faites, où vous intervenez et comment vous joindre.",
    "peintre": "Quand quelqu'un a un projet de peinture {aville}, il veut voir ce que vous faites, où vous intervenez et comment vous joindre.",
    "menuisier": "Quand quelqu'un a un projet de menuiserie {aville}, il veut voir ce que vous faites, où vous intervenez et comment vous joindre.",
    "restaurant": "Quand on cherche où manger {aville}, on veut trouver la carte, les horaires et l'accès, puis réserver ou appeler en un geste.",
    "commerce": "Quand on cherche une boutique {aville}, on veut savoir ce que vous vendez, quand vous êtes ouvert et comment vous joindre.",
    "coiffeur": "Quand on cherche un coiffeur {aville}, on veut trouver vos prestations et vos horaires, puis prendre rendez-vous ou vous appeler en un geste.",
    "fleuriste": "Quand on cherche un fleuriste {aville}, on veut voir vos compositions, savoir quand vous êtes ouvert et vous joindre ou passer commande facilement.",
    "boulangerie": "Quand on cherche une boulangerie {aville}, on veut savoir ce que vous proposez, vos horaires d'ouverture et où vous trouver.",
    "garage": "Quand on cherche un garage {aville}, on veut trouver ce que vous faites et vos horaires, puis prendre rendez-vous ou vous appeler en un geste.",
}
MONTRE = {"artisan": "un numéro cliquable, une barre d'appel fixe sur mobile, votre zone d'intervention et un formulaire de quatre champs",
          "restaurant": "les boutons Réserver et Appeler, la carte, les horaires, l'accès et un formulaire de réservation de quatre champs",
          "commerce": "vos produits, vos horaires, l'accès et un formulaire de contact de quatre champs",
          "coiffeur": "un bouton Appeler, vos prestations, vos horaires, l'accès et un formulaire de prise de rendez-vous de quatre champs",
          "fleuriste": "un bouton Appeler, vos compositions, vos horaires, l'accès et un formulaire de commande de quatre champs",
          "boulangerie": "vos produits, vos horaires, l'accès et un formulaire de contact de quatre champs",
          "garage": "un bouton Appeler, vos prestations, vos horaires, l'accès et un formulaire de prise de rendez-vous de quatre champs"}
INTERDITS = re.compile(r"classement|première page|premiere page|\b1er\b|n°\s?1|garanti|référencement|vous n.avez pas de site|\d\s?%|€|euros?\b", re.I)
A_COMPLETER = "[à compléter]"
LIGNE_STOP = "Pour ne plus recevoir mes messages : répondez simplement STOP"


def cle_metier(texte):
    """Clé du métier : commerces d'abord (coiffeur, fleuriste, boulangerie, garage), puis les métiers de generer.py. None si inconnu."""
    t = G.sans_accent(texte or "").lower()
    return next((c for m, c in CLES_COMMERCES if m in t), None) or G.metier_cle(texte or "")


def siret_espace(s):  # 10183903300012 -> 101 839 033 00012
    c = re.sub(r"\D", "", s or "")
    return f"{c[:3]} {c[3:6]} {c[6:9]} {c[9:]}" if len(c) == 14 else (s or A_COMPLETER)


def signature(ident):
    return "\n".join([ident["prenom_nom"], "Création de sites web pour artisans et commerces",
                       f"{ident['entreprise']} · SIRET {siret_espace(ident['siret'])}",
                       f"Tél. {ident['telephone'] or A_COMPLETER} · {ident['email_reponse'] or A_COMPLETER}", LIGNE_STOP])


def avec_signature(texte, ident):
    """Ajoute la signature texte (sans image) ; ne la duplique pas si la ligne STOP y est déjà."""
    if LIGNE_STOP in texte: return texte
    return texte.rstrip() + "\n\n" + signature(ident)


def en_ville(v):  # « à Rouen », « au Havre », « aux Andelys »
    if v.startswith("Le "): return "au " + v[3:]
    if v.startswith("Les "): return "aux " + v[4:]
    return "à " + v


def charger_identite():
    i = json.loads(IDENTITE.read_text(encoding="utf-8"))
    manque = [k for k in ("siret", "telephone", "email_reponse") if not i.get(k)]
    return i, manque


def statuts_suivi():
    if not SUIVI.exists(): return {}
    with open(SUIVI, encoding="utf-8-sig", newline="") as f:
        return {G.slug(r["nom"]) + "|" + G.slug(r["ville"]): r["statut"] for r in csv.DictReader(f, delimiter=";")}


def corps_email(p, ident, lien, constat, cle, fam, exemple=False):
    pl = PLURIEL[cle]
    tel = ident["telephone"] or A_COMPLETER
    siret = ident["siret"] or A_COMPLETER
    reponse = ident["email_reponse"] or A_COMPLETER
    objet = f"{p['nom']} : une maquette de site pour votre activité {en_ville(p['ville'])}"
    exemple_txt = "un exemple de page pour votre métier" if exemple else f"une maquette pour {p['nom']}"
    texte = f"""Bonjour,

Je m'appelle {ident['prenom_nom']}, je crée des sites web pour les {pl} de la région.
{constat}
J'ai préparé {exemple_txt}, sans engagement : {lien}
Ce n'est pas votre site, juste un exemple.

Si ça vous parle, le plus simple est un appel ou un Google Meet de 15 minutes, quand cela vous arrange : répondez avec un créneau, ou appelez-moi au {tel}. On peut aussi rester par e-mail, comme vous préférez.

Vous recevez ce message car votre entreprise figure dans {p['_origine']}.

Cordialement,"""
    return objet, avec_signature(texte, ident)


def corps_linkedin(p, ident, lien, cle, exemple=False):
    return avec_signature(f"Bonjour, {ident['prenom_nom']} ({ident['entreprise']}). {ACCROCHE[cle].format(aville=en_ville(p['ville']))} " +
            (f"J'ai préparé une page d'exemple pour votre métier, sans engagement : {lien} " if exemple else f"J'ai préparé une maquette de site pour {p['nom']}, sans engagement : {lien} ") +
            f"Ce n'est pas votre site officiel, juste un exemple.", ident)


def bloc(p, ident, manque_ident, statuts, exemple=""):
    cle = cle_metier(p.get("metier", ""))
    if not cle: return None, f"métier non géré : « {p.get('metier', '')} »"
    fam = cle if cle in MONTRE else "artisan"  # textes propres au restaurant, au commerce, au coiffeur, etc. ; les métiers du bâtiment partagent « artisan »
    nom, ville = p["nom"], p["ville"]
    st = statuts.get(G.slug(nom) + "|" + G.slug(ville), "")
    if st in ("STOP", "refusé"): return None, f"statut {st} dans le suivi : aucun message"
    dossier = f"{G.slug(nom)}-{G.jeton(nom, ville)}"
    existe = (G.PUBLIC / dossier / "index.html").exists()
    base = ident.get("base_url_maquettes", "").rstrip("/")
    lien = f"{base}/{dossier}/" if base else f"[LIEN À INSÉRER APRÈS DÉPLOIEMENT : /{dossier}/]"
    if exemple: lien = exemple + " (exemple, pas votre site)"  # page exemple du métier (agents\liens-metiers.json), vérifiée en ligne par l'appelant
    site, note = p.get("siteactuel") or p.get("site", ""), p.get("notebesoin", "")
    if note: constat = f"En regardant votre activité : {note.rstrip('.')}."
    elif p.get("modele") == "sans-site": constat = "Je n'ai pas trouvé de site à votre nom."   # recherche faite : formule exacte, jamais « vous n'avez pas de site »
    else: constat = ""  # rien d'affirmé sur un site que personne n'a vérifié
    p["_origine"] = "l'annuaire officiel des entreprises" if not p.get("source") else p["source"]
    objet, mail = corps_email(p, ident, lien, constat, cle, fam, bool(exemple))
    mail = re.sub(r"\n{3,}", "\n\n", mail)
    li = corps_linkedin(p, ident, lien, cle, bool(exemple))
    controles = []
    if p.get("fictif", "").lower() in ("oui", "1", "x"): controles.append("⚠ PROSPECT FICTIF (test) : ne jamais envoyer")
    if not existe and not exemple: controles.append("⚠ maquette absente : lancer `python sites\\moteur\\generer.py <csv>`")
    if not base and not exemple: controles.append("⚠ lien non actif : projet Vercel pas encore déployé (identite.json › base_url_maquettes vide)")
    if manque_ident: controles.append("⚠ identité incomplète dans agents\\identite.json : " + ", ".join(manque_ident))
    if not p.get("email"): controles.append("⚠ pas d'e-mail : LinkedIn ou téléphone seulement")
    elif p.get("emailtype", "") == "nominatif" and not p.get("emailsource"): controles.append("⚠ e-mail nominatif sans source : ne pas écrire par e-mail")
    elif not p.get("emailsource"): controles.append("⚠ source de l'e-mail non notée")
    if not constat: controles.append("ℹ aucun constat sur son site : ajouter `note_besoin` (fait vérifié à la main) pour personnaliser")
    elif not note and p.get("modele") != "sans-site": controles.append("⚠ « pas de site » repris du CSV : à vérifier à la main avant envoi")
    for nom_t, t in (("e-mail", mail), ("LinkedIn", li)):
        for m in INTERDITS.finditer(t): controles.append(f"⚠ mot interdit dans {nom_t} : « {m.group(0)} »")
    if "STOP" not in mail or "STOP" not in li: controles.append("⚠ ligne STOP absente")
    ok = "✅ prêt à relire" if not [c for c in controles if c.startswith("⚠")] else "⛔ à corriger avant envoi"
    id_ = G.slug(nom) + "|" + G.slug(ville)
    contact = f"{p.get('email') or '—'} ({p.get('emailtype') or 'type ?'}; source : {p.get('emailsource') or '—'}) · tél. {p.get('telephone') or '—'}"
    out = [f"## {nom} — {p.get('metier', '')} — {ville}", f"<!-- id:{id_} -->", "**Statut : à valider**", "",
           f"- Maquette : {lien}", f"- Contact : {contact}", f"- Site actuel : {site or 'aucun noté'}", f"- Contrôles : {ok}"]
    out += [f"  - {c}" for c in controles]
    out += ["", "### E-mail", f"**Objet :** {objet}", "", "```", mail, "```", "", "### LinkedIn", "```", li, "```", ""]
    return (id_, "\n".join(out)), None


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Brouillons de messages à valider (aucun envoi).")
    ap.add_argument("csv"); ap.add_argument("-o", "--sortie", default=str(RACINE / "messages-a-valider.md"))
    a = ap.parse_args()
    ident, manque = charger_identite()
    statuts = statuts_suivi()
    sortie = Path(a.sortie)
    anciens = {}
    if sortie.exists():  # on garde les statuts déjà changés par Liam dans le fichier
        for m in re.finditer(r"<!-- id:(.+?) -->\n\*\*Statut : (.+?)\*\*", sortie.read_text(encoding="utf-8")):
            anciens[m.group(1)] = m.group(2)
    blocs, sautes = [], []
    for p in G.lire_csv(a.csv):
        if not p.get("nom") or not p.get("ville"): sautes.append((p.get("nom", "?"), "nom ou ville manquant")); continue
        r, err = bloc(p, ident, manque, statuts)
        if err: sautes.append((p["nom"], err)); continue
        id_, texte = r
        if anciens.get(id_) and anciens[id_] != "à valider": texte = texte.replace("**Statut : à valider**", f"**Statut : {anciens[id_]}**")
        blocs.append(texte)
    tete = ["# Messages à valider", f"Généré le {date.today()} par agents\\redaction.py. **Rien n'a été envoyé.** Chaque bloc reste « à valider » jusqu'à ton OK.",
            "Pour valider ou refuser un bloc, remplace son statut (ex. « validé », « à modifier », « refusé ») : une régénération le conserve.", ""]
    sortie.write_text("\n".join(tete + blocs) + "\n", encoding="utf-8")
    print(f"{len(blocs)} bloc(s) écrits dans {sortie}")
    for nom, err in sautes: print(f"  sauté : {nom} ({err})")


if __name__ == "__main__":
    main()

def accroche_appel(p, ident, cle, constat=""):
    """Accroche de 2 phrases pour un appel : être trouvé et joint en un geste ; page d'exemple ; un constat seulement s'il a été vérifié sur le site. Aucune promesse de classement."""
    a = ACCROCHE[cle].format(aville=en_ville(p["ville"]))
    b = "J'ai préparé une page d'exemple pour votre métier, sans engagement" + (f" ; sur votre site, j'ai constaté : {constat.rstrip('.')}" if constat else "") + "."
    t = f"{a} {b}"
    if INTERDITS.search(t): raise ValueError("mot interdit dans l'accroche d'appel : " + INTERDITS.search(t).group(0))
    return t


def sms_appel(p, ident, cle, lien):
    """Texte de SMS de 300 caractères au plus, avec identification et STOP. STOCKÉ, jamais envoyé par le programme."""
    pl = PLURIEL[cle]; nom = ident.get("prenom_nom") or A_COMPLETER; ent = ident.get("entreprise") or A_COMPLETER; fin = " (exemple, pas votre site)" if lien else ""
    for debut in (f"Pour être trouvé et joint facilement, j'ai préparé une page d'exemple pour les {pl} de {p['ville']}", f"J'ai préparé une page d'exemple pour les {pl}, pour être trouvé et joint facilement", "J'ai préparé une page d'exemple pour votre métier"):
        t = f"Bonjour, c'est {nom} ({ent}). {debut} : {lien}{fin}. Répondez STOP pour ne plus être contacté." if lien else f"Bonjour, c'est {nom} ({ent}). {debut}. Répondez STOP pour ne plus être contacté."
        if len(t) <= 300: break
    else: raise ValueError(f"SMS trop long ({len(t)} caractères)")
    if INTERDITS.search(t): raise ValueError("mot interdit dans le SMS : " + INTERDITS.search(t).group(0))
    return t