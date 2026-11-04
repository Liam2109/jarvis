#!/usr/bin/env python3
"""Moteur de maquettes d'artisans : une page par ligne d'un CSV de prospects.

  python sites\\moteur\\generer.py prospects.csv          une maquette par ligne
  python sites\\moteur\\generer.py --exemples              les 3 maquettes d'électricien (données fictives)
  python sites\\moteur\\generer.py --rescore               recalcule les scores (après sites\\outils\\qa.mjs)

CSV : nom, metier, ville, telephone, site (site actuel). Facultatif : zone, note, avis, annees, labels,
services, photos (fichier|auteur|licence), direction (technique|rassurant|premium|lumiere|eau), exemple (oui).
Séparateur ; ou ,  Sortie : sites\\public\\<nom>-<jeton>\\index.html (noindex). Rien n'est publié ni envoyé.
Un champ vide n'est jamais rempli avec une valeur inventée : la zone est marquée « à compléter ».
"""
import argparse, csv, hashlib, html, json, re, secrets, shutil, sys, unicodedata
from datetime import date
from pathlib import Path

SITES = Path(__file__).resolve().parent.parent
MOTEUR = SITES / "moteur"
sys.path.insert(0, str(MOTEUR))
import modeles, modeles3, modeles4, modeles5, modeles6
PUBLIC = SITES / "public"
SORTIES = SITES / "sorties"
SUIVI = SITES.parent / "agents" / "dev-sites.md"
QA_JSON = SITES / "outils" / "qa-resultats.json"

THEMES = {  # polices : familles à embarquer, police d'affichage à précharger
    "technique": (["BarlowCondensed", "Barlow"], "BarlowCondensed-800.woff2"),
    "rassurant": (["BricolageGrotesque", "Figtree"], "BricolageGrotesque-500-800.woff2"),
    "premium": (["Fraunces", "HankenGrotesk"], "Fraunces-500-700.woff2"),
    "bistro": (["Fraunces", "HankenGrotesk"], "Fraunces-500-700.woff2"),
    "marche": (["BricolageGrotesque", "Figtree"], "BricolageGrotesque-500-800.woff2"),
    "atelier": (["Fraunces", "Figtree"], "Fraunces-500-700.woff2"),
    "lumiere": (["Fraunces", "Inter"], "Fraunces-500-700.woff2"),
    "eau": (["BricolageGrotesque", "HankenGrotesk"], "BricolageGrotesque-500-800.woff2"),
    "maison": (["Fraunces", "HankenGrotesk"], "Fraunces-500-700.woff2"),
    "braise": (["Fraunces", "HankenGrotesk"], "Fraunces-500-700.woff2"),
    "salon": (["Unbounded", "Manrope"], "Unbounded-300-900.woff2"),
    "petale": (["DMSerifDisplay", "Figtree"], "DMSerifDisplay-400.woff2"),
    "fournil": (["YoungSerif", "Figtree"], "YoungSerif-400.woff2"),
    "garage": (["BarlowCondensed", "Barlow"], "BarlowCondensed-800.woff2"),
}
FAMILLE_THEMES = {"artisan": ["technique", "rassurant", "premium", "lumiere", "eau"], "restaurant": ["bistro", "marche", "braise"], "commerce": ["atelier"], "groupe": ["maison"], "local": ["salon", "petale", "fournil", "garage"]}
DIRECTION_PAR_METIER = {"electricien": "lumiere", "plombier": "eau", "couvreur": "technique",
                        "macon": "premium", "peintre": "premium", "menuisier": "premium",
                        "restaurant": "bistro", "commerce": "atelier", "groupe": "maison",
                        "coiffeur": "salon", "fleuriste": "petale", "boulangerie": "fournil", "garage": "garage"}
MOTS_METIER = [("groupe", "groupe"), ("electric", "electricien"), ("plomb", "plombier"), ("chauffag", "plombier"), ("couv", "couvreur"),
               ("toit", "couvreur"), ("macon", "macon"), ("peint", "peintre"), ("menuis", "menuisier"),
               ("restaur", "restaurant"), ("brasserie", "restaurant"), ("bistro", "restaurant"), ("pizzeria", "restaurant"), ("creperie", "restaurant"),
               ("commerce", "commerce"), ("boutique", "commerce"), ("magasin", "commerce"),
               ("coiffeu", "coiffeur"), ("fleuri", "fleuriste"), ("boulang", "boulangerie"), ("patisser", "boulangerie"), ("garage", "garage")]
ICONE_TEL = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 1.9.7 2.8a2 2 0 0 1-.5 2.1L8 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.7 2z"/></svg>'

# --- petits outils ---------------------------------------------------------------------------------
def e(s): return html.escape(str(s), quote=True)

def fm(s):  # texte échappé ; [[...]] devient une zone surlignée « à compléter »
    return re.sub(r"\[\[(.+?)\]\]", r'<mark class="todo">\1</mark>', e(s))

def sans_accent(s): return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()

def slug(s): return re.sub(r"[^a-z0-9]+", "-", sans_accent(s).lower()).strip("-")[:48] or "prospect"

def jeton(nom, ville):
    f = SORTIES / "jeton.secret"
    SORTIES.mkdir(exist_ok=True)
    if not f.exists(): f.write_text(secrets.token_hex(16), encoding="utf-8")
    return hashlib.sha256((f.read_text(encoding="utf-8").strip() + slug(nom) + slug(ville)).encode()).hexdigest()[:8]

def tel_norm(t):
    d = re.sub(r"\D", "", str(t or ""))
    if d.startswith("33") and len(d) == 11: d = "0" + d[2:]
    if len(d) != 10 or not d.startswith("0"): return None, None
    return " ".join(d[i:i + 2] for i in range(0, 10, 2)), "+33" + d[1:]

def liste(s): return [x.strip() for x in re.split(r"[,;/|]", str(s or "")) if x.strip()]

def nombre(s):
    try: return float(str(s).replace(",", ".").strip())
    except ValueError: return None

def metier_cle(texte):
    t = sans_accent(texte).lower()
    return next((c for m, c in MOTS_METIER if m in t), None)

# --- lecture du CSV ---------------------------------------------------------------------------------
def lire_csv(chemin):
    brut = Path(chemin).read_bytes()
    try: texte = brut.decode("utf-8-sig")
    except UnicodeDecodeError: texte = brut.decode("cp1252")
    delim = ";" if texte.split("\n", 1)[0].count(";") >= texte.split("\n", 1)[0].count(",") else ","
    lignes = []
    for r in csv.DictReader(texte.splitlines(), delimiter=delim):
        lignes.append({re.sub(r"[^a-z]", "", sans_accent(k).lower()): (v or "").strip() for k, v in r.items() if k})
    return lignes

# --- construction de la page -------------------------------------------------------------------------
def css_polices(familles):
    blocs = re.findall(r"@font-face \{.*?\}", (MOTEUR / "polices" / "polices.css").read_text(encoding="utf-8"), re.S)
    out = []
    for b in blocs:
        fam = re.search(r"font-family: '([^']+)'", b).group(1).replace(" ", "")
        if fam in familles: out.append(b.replace("url(", "url(../assets/polices/"))
    return "\n".join(out)

def construire(p, met):
    ex = p["exemple"]
    theme = p["direction"]
    familles, precharge = THEMES[theme]
    nom, ville, label = p["nom"], p["ville"], met["label"]
    aff_tel, tel_intl = tel_norm(p.get("telephone"))
    badge = '<span class="badge-ex">exemple</span>' if ex else ""
    if aff_tel:
        def appel(cls="btn btn-main", txt=None):
            return f'<a class="{cls}" href="tel:{tel_intl}">{ICONE_TEL}<span>{e(txt or "Appeler le " + aff_tel)}</span></a>'
        lien_tel = f'<a class="tel-big" href="tel:{tel_intl}">{aff_tel}</a>'
    else:
        def appel(cls="btn btn-main", txt=None):
            return f'<a class="{cls}" href="#contact">{ICONE_TEL}<span>Appeler : <mark class="todo">n° à compléter</mark></span></a>'
        lien_tel = '<a class="tel-big" href="#contact"><mark class="todo">n° à compléter</mark></a>'
    devis = '<a class="btn btn-line" href="#contact"><span>Demander un devis gratuit</span></a>'

    # preuves : seulement ce qui est fourni
    preuves = []
    note, avis = nombre(p.get("note")), nombre(p.get("avis"))
    if note and avis: preuves.append(f'<li><span class="star" aria-hidden="true">★</span> {note:.1f}'.replace(".", ",") + f' / 5 <small>· {int(avis)} avis Google</small>{badge}</li>')
    an = nombre(p.get("annees"))
    if an: preuves.append(f'<li>{int(an)} ans d\'activité{badge}</li>')
    for lb in liste(p.get("labels"))[:4]: preuves.append(f'<li>{e(lb)}{badge}</li>')
    n_preuves = len(preuves)
    if not preuves:
        preuves = ['<li><mark class="todo">Preuves à ajouter : note et avis Google, années d\'activité, labels, assurance décennale</mark></li>']
    if ex and n_preuves: pass

    # services : ceux fournis, sinon ceux du métier
    svc = met["services"][:6]
    fournis = liste(p.get("services"))
    if fournis:
        svc = []
        for s in fournis[:6]:
            mots = set(re.findall(r"[a-z]{4,}", sans_accent(s).lower()))
            m = next((x for x in met["services"] if mots & set(re.findall(r"[a-z]{4,}", sans_accent(x["t"]).lower()))), None)
            svc.append({"t": s, "d": m["d"] if m else "[[Description à compléter]]"})
    # zone
    zone = liste(p.get("zone"))
    if ville not in zone: zone.insert(0, ville)
    zone_txt = zone[:14]
    zone_todo = "" if len(zone) > 1 else '<mark class="todo">communes desservies à compléter</mark>'

    # photo du hero : fichier fourni (avec licence) ou zone à remplacer
    photo = p.get("photo_hero")
    if photo:
        hero_visuel = f'<img class="photo r45" src="img/{e(photo["fichier"])}" alt="{e(label)} {e(nom)} à {e(ville)}" width="800" height="1000" fetchpriority="high">'
    else:
        hero_visuel = f'<div class="ph r45"><b>Photo à remplacer</b><span>{e(met["photo_hero"])}</span><small>Format portrait 4:5, 1200 × 1500 px minimum. Photo de l\'artisan, avec son accord.</small></div>'

    reals = "".join(
        f'<article class="real rv"><div class="pair"><div class="ph r43"><b>Avant — photo à remplacer</b></div><div class="ph r43"><b>Après — photo à remplacer</b></div></div>'
        f'<h3>{e(t)} {"<span class=badge-ex>exemple</span>" if ex else ""}</h3><p>Lieu : <mark class="todo">à compléter</mark> · Durée : <mark class="todo">à compléter</mark></p></article>'
        for t in met["realisations"])
    svc_html = "".join(f'<article class="svc rv"><div class="n">{i:02d}</div><h3>{fm(s["t"])}</h3><p>{fm(s["d"])}</p></article>' for i, s in enumerate(svc, 1))
    why = "".join(f'<div class="why rv"><div class="big">{i}</div><h3>{fm(r["t"])}</h3><p>{fm(r["d"])}</p></div>' for i, r in enumerate(met["raisons"], 1))
    steps = "".join(f'<li class="rv"><h3>{fm(s["t"])}</h3><p>{fm(s["d"])}</p></li>' for s in met["etapes"])
    faq = "".join(f'<details class="rv"><summary>{fm(q["q"])}</summary><p>{fm(q["a"])}</p></details>' for q in met["faq"])
    villes = "".join(f"<li>{e(v)}</li>" for v in zone_txt)
    options = "".join(f"<option>{e(o)}</option>" for o in met["besoins"])

    titre = f"{label} à {ville} — {nom}"
    desc = f"{label} à {ville} et alentours. {met['accroche_urgence']} Devis gratuit, rappel rapide."
    if aff_tel: desc = f"{label} à {ville} et alentours : {met['accroche_urgence'].rstrip('.')} au {aff_tel}. Devis gratuit, rappel rapide."
    ld = {"@context": "https://schema.org", "@type": met["schema"], "name": nom, "description": desc,
          "address": {"@type": "PostalAddress", "addressLocality": ville, "addressCountry": "FR"},
          "areaServed": [{"@type": "City", "name": v} for v in zone_txt]}
    if tel_intl: ld["telephone"] = tel_intl
    if note and avis and not ex:
        ld["aggregateRating"] = {"@type": "AggregateRating", "ratingValue": note, "reviewCount": int(avis)}
    if ex:
        bandeau = '<b>EXEMPLE</b> — entreprise, numéro et chiffres fictifs, aucun avis réel. Maquette de démonstration LM MULTI-SERVICES.'
    else:
        bandeau = f'Maquette de démonstration préparée par LM MULTI-SERVICES pour {e(nom)}. <b>Ce n\'est pas le site officiel</b> de l\'entreprise. Les zones surlignées sont à compléter.'

    css = (MOTEUR / "base.css").read_text(encoding="utf-8") + (MOTEUR / "themes" / f"{theme}.css").read_text(encoding="utf-8")
    h1 = f'{e(label)} à <em>{e(ville)}</em>'
    return f"""<!doctype html>
<html lang="fr" data-theme="{theme}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(titre)}</title>
<meta name="description" content="{e(desc)}">
<meta name="robots" content="noindex, nofollow, noarchive">
<link rel="icon" href="data:,">
<link rel="preload" href="../assets/polices/{precharge}" as="font" type="font/woff2" crossorigin>
<style>
{css_polices(familles)}
{css}
</style>
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
<script>document.documentElement.classList.add("js")</script>
</head>
<body>
<a class="skip" href="#contact">Aller au formulaire</a>
<div class="banner" role="note">{bandeau}</div>
<header class="top"><div class="w">
  <a class="brand" href="#top">{e(nom)}</a>
  <nav class="nav" aria-label="Sections"><a href="#services">Services</a><a href="#zone">Zone</a><a href="#faq">Questions</a><a href="#contact">Contact</a></nav>
  {appel("btn btn-main", (aff_tel or "Appeler"))}
</div></header>
<main id="top">
<section class="hero"><div class="w">
  <div>
    <p class="eyebrow">{e(nom)}{badge}</p>
    <h1>{h1}</h1>
    <p class="lead">{fm(met["promesse"])}</p>
    <div class="cta">{appel()}{devis}</div>
    <p class="urg">{e(met["accroche_urgence"])}</p>
  </div>
  <div>{hero_visuel}</div>
</div></section>
<section class="proofs" aria-label="Preuves"><div class="w"><ul>{"".join(preuves)}</ul></div></section>
<section class="section" id="services"><div class="w">
  <p class="eyebrow rv">Ce que nous faisons</p><h2 class="rv">{e(label)} : {len(svc)} services pour {e(ville)}</h2>
  <div class="grid-s">{svc_html}</div>
</div></section>
<section class="section alt" id="realisations"><div class="w">
  <p class="eyebrow rv">Réalisations</p><h2 class="rv">Des chantiers, avant et après</h2>
  <div class="grid-r">{reals}</div>
</div></section>
<section class="section" id="pourquoi"><div class="w">
  <p class="eyebrow rv">Pourquoi nous choisir</p><h2 class="rv">Trois raisons concrètes</h2>
  <div class="grid-w">{why}</div>
</div></section>
<section class="section alt" id="methode"><div class="w">
  <p class="eyebrow rv">Comment ça se passe</p><h2 class="rv">De l'appel à l'intervention</h2>
  <ol class="steps">{steps}</ol>
</div></section>
<section class="section" id="zone"><div class="w zone">
  <div><p class="eyebrow rv">Zone d'intervention</p><h2 class="rv">Autour de {e(ville)}</h2>
  <p class="rv" style="color:var(--muted)">{e(nom)} intervient dans ces communes {zone_todo}. Une autre commune ? Appelez pour vérifier.</p></div>
  <ul class="villes rv">{villes}</ul>
</div></section>
<section class="section alt" id="avis"><div class="w">
  <p class="eyebrow rv">Avis clients</p><h2 class="rv">Ce que disent les clients</h2>
  <div class="rev rv"><b>Vos 3 vrais avis Google s'afficheront ici</b>Avis réels de la fiche Google, repris avec l'accord de l'artisan. Aucun avis n'est inventé.</div>
</div></section>
<section class="section" id="faq"><div class="w">
  <p class="eyebrow rv">Questions fréquentes</p><h2 class="rv">Vos questions</h2>
  <div class="faq">{faq}</div>
</div></section>
<section class="section contact" id="contact"><div class="w">
  <div><p class="eyebrow">Contact</p><h2>Un devis, un rappel</h2>
  <p class="lead">Appelez, ou laissez 4 informations : on vous rappelle sous <mark class="todo">délai à confirmer</mark>.</p>
  {lien_tel}</div>
  <form class="f" action="#contact" method="post" id="devis">
    <label for="f-nom">Votre nom<input id="f-nom" name="nom" autocomplete="name" required></label>
    <label for="f-tel">Votre téléphone<input id="f-tel" name="tel" type="tel" autocomplete="tel" inputmode="tel" required></label>
    <label for="f-besoin">Votre besoin<select id="f-besoin" name="besoin">{options}</select></label>
    <label for="f-ville">Votre commune<input id="f-ville" name="ville" autocomplete="address-level2"></label>
    <button class="btn btn-main" type="submit">Être rappelé(e)</button>
    <p class="note">Votre numéro sert uniquement à vous rappeler.</p>
    <p class="ok" role="status">Maquette : l'envoi est désactivé. {"Pour joindre l'artisan, appelez le " + aff_tel + "." if aff_tel else ""}</p>
  </form>
</div></section>
</main>
<footer><div class="w">
  <p><strong>{e(nom)}</strong> — {e(label)} à {e(ville)} · {appel("", aff_tel or "Appeler").replace('class=""', 'class="fl"')}</p>
  <p>SIRET <mark class="todo">à compléter</mark> · Assurance décennale <mark class="todo">à compléter</mark> · Mentions légales <mark class="todo">à compléter</mark></p>
  <p>Maquette réalisée par LM MULTI-SERVICES. Page privée, non référencée.</p>
</div></footer>
<div class="bar">{appel("btn btn-main", "Appeler")}<a class="btn btn-line" href="#contact"><span>Devis</span></a></div>
<script>
(function(){{
  var els=document.querySelectorAll(".rv");
  if(!("IntersectionObserver" in window)){{els.forEach(function(x){{x.classList.add("in")}});}}
  else{{var io=new IntersectionObserver(function(a){{a.forEach(function(i){{if(i.isIntersecting){{i.target.classList.add("in");io.unobserve(i.target)}}}})}},{{rootMargin:"0px 0px -8% 0px"}});els.forEach(function(x){{io.observe(x)}});}}
  var f=document.getElementById("devis");
  f.addEventListener("submit",function(ev){{ev.preventDefault();f.classList.add("sent")}});
}})();
</script>
</body>
</html>
"""

# --- score qualité -----------------------------------------------------------------------------------
def score_auto(h, p, aff_tel):
    """70 points, vérifiés sur le HTML généré : 44 communs + 26 propres à la famille (artisan, restaurant, commerce)."""
    ex, fam = p["exemple"], p.get("famille", "artisan")
    texte = re.sub(r"<(script|style)\b.*?</\1>", " ", h, flags=re.S)
    texte = re.sub(r"<[^>]+>", " ", texte)
    form = re.search(r"<form\b.*?</form>", h, re.S)
    champs = [c for c in re.findall(r"<(?:input|select|textarea)\b[^>]*>", form.group(0) if form else "") if not re.search(r'type="(hidden|submit)"', c)]
    familles = set(re.findall(r"font-family: '([^']+)'", h))
    ville, mot = p["ville"].lower(), p["_met"]["label"].lower().split()[0]
    h1 = re.search(r"<h1>(.*?)</h1>", h, re.S)
    h1t = re.sub(r"<[^>]+>", "", h1.group(1)).lower() if h1 else ""
    titre = (re.search(r"<title>(.*?)</title>", h, re.S) or [0, ""])[1].lower()
    desc = (re.search(r'name="description" content="(.*?)"', h) or [0, ""])[1]
    zones = re.findall(r'<div class="ph\b.*?</div>', h, re.S)
    imgs = re.findall(r"<img\b[^>]*>", h)
    sect = lambda motif: re.search(motif, h, re.S)
    preuves = sect(r'<section class="proofs".*?</section>')
    try: json.loads(re.search(r'application/ld\+json">(.*?)</script>', h, re.S).group(1)); ld = True
    except Exception: ld = False
    mb = sect(r'<div class="bar">.*?</div>')
    barre = mb.group(0) if mb else ""
    ntel = h.count('href="tel:')
    hor = sect(r'<table class="hor".*?</table>')
    commun = [
        ("Numéro cliquable (en-tête ou hero, contact, pied, barre)", 5, 1 if ntel >= 4 else (.4 if ntel else 0)),
        ("Barre d'appel fixe mobile (Appeler + une 2e action)", 5, 1 if 'href="tel:' in barre and barre.count("<a ") >= 2 else 0),
        ("Titre et description avec métier + ville", 5, (3 / 5 if ville in titre and mot in titre else 0) + (2 / 5 if 70 <= len(desc) <= 165 else 0)),
        ("Balisage JSON-LD valide", 4, 1 if ld else 0),
        ("noindex présent", 4, 1 if 'name="robots" content="noindex' in h else 0),
        ("Bandeau « maquette, pas le site officiel »", 2, 1 if re.search(r"Ce n.est pas le site officiel|EXEMPLE", h) else 0),
        ("Aucun jeton ou mot « exemple » oublié", 2, 1 if "{{" not in h and "None" not in texte and "undefined" not in h and (ex or not re.search(r"\bexemple\b", texte, re.I)) else 0),
        ("Accessibilité de base (lang, viewport, lien d'évitement, labels, mouvement réduit)", 5,
         sum(map(bool, ['lang="fr"' in h, 'name="viewport"' in h, 'class="skip"' in h, h.count("<label") >= len(champs) > 0, "prefers-reduced-motion" in h])) / 5),
        ("Deux polices au maximum", 2, 1 if 0 < len(familles) <= 2 else 0),
        ("Visuel du hero (photo ou zone à remplacer)", 2, 1 if re.search(r'<section class="(?:v?hero|gh-hero)[^"]*".*?(<img|class="ph |<svg class="bulb"|<svg class="gout")', h, re.S) else 0),
        ("Pas de texte de remplissage ni d'emoji décoratif", 2, 1 if not re.search(r"lorem|ipsum|[\U0001F300-\U0001FAFF]", h, re.I) else 0),
        ("Photos : zones « à remplacer », alt, registre de licences", 3, 1 if all(re.search("à remplacer|à définir", z) for z in zones) and all('alt="' in i for i in imgs) and (not imgs or p.get("registre")) else 0),
        ("Avis : aucun faux avis", 3, 1 if ('class="rev' in h or 'class="avis-c' in h or fam == "commerce") and h.count("★") <= 1 else 0),
    ]
    forme = (4 / 6 if 3 <= len(champs) <= 4 else 0) + (2 / 6 if re.search(r"rappel|confirm|répond", texte, re.I) else 0)
    horaires = 1 if hor and len(re.findall(r'<th scope="row">', hor.group(0))) == 7 else 0
    if fam == "restaurant":
        carte = h.count('class="pl-n"') >= 9 if ex else h.count('class="cat') >= 3
        propres = [
            ("Réservation : 3 à 4 champs, date et heure, confirmation promise", 6, forme if "datetime-local" in h else forme / 2),
            ("H1 avec la ville", 5, 1 if ville in h1t else 0),
            ("Carte en HTML (pas de PDF), ≥ 3 catégories", 6, 1 if carte and ".pdf" not in h.lower() else 0),
            ("Horaires : 7 jours", 5, horaires),
            ("Infos pratiques : adresse, horaires, téléphone", 4, 1 if sect(r'<section class="infos"') and "Adresse" in h else 0),
        ]
    elif fam == "groupe":
        evt = sect(r'<section class="section" id="evenements".*?</section>')
        h1w = len(h1t.split()) if h1 else 99
        nm = len(re.findall(r'<article class="maison', h))
        ok_m = nm >= 3 and len(re.findall(r'<article class="maison[^>]*>.*?</article>', h, re.S)) == nm and all("Réserver" in a and ('href="tel:' in a or 'href="#contact"' in a) for a in re.findall(r'<article class="maison[^>]*>.*?</article>', h, re.S))
        propres = [
            ("Réservation : 3 à 4 champs, date et heure, confirmation promise", 6, forme if "datetime-local" in h else forme / 2),
            ("H1 : phrase d'ambiance de 12 mots maximum", 5, 1 if h1 and 3 <= h1w <= 12 else 0),
            ("Une carte par maison (≥ 3), avec Réserver et Appeler", 6, 1 if ok_m else 0),
            ("Événements : « Demander un devis » et formulaire de 3 à 4 champs", 5, 1 if evt and "Demander un devis" in evt.group(0) and 'id="evt"' in h and len(re.findall(r"<(?:input|select)\b", re.search(r'<form[^>]*id="evt".*?</form>', h, re.S).group(0))) in (3, 4) else 0),
            ("Histoire, fidélité et recrutement présents", 4, sum(map(bool, ['id="histoire"' in h, 'id="fidelite"' in h, 'id="recrutement"' in h])) / 3),
        ]
    elif fam == "commerce":
        v3d = (sect(r'<div class="v3d"') and 'data-lib="' in h and 'id="v3d-go"' in h and "<model-viewer" not in h and re.search(r'<div class="v3d".*?<img[^>]*alt="[^"]+"', h, re.S)) if ex else bool(sect(r"Option 3D"))
        propres = [
            ("Formulaire de 3 à 4 champs + promesse de réponse", 6, forme),
            ("H1 avec la ville", 5, 1 if ville in h1t else 0),
            ("Produits : au moins 4 cartes", 6, 1 if h.count('class="prod') >= 4 else 0),
            ("3D optionnelle avec image de repli, chargée au clic", 4, 1 if v3d else 0),
            ("Horaires : 7 jours", 5, horaires),
        ]
    else:
        propres = [
            ("Formulaire de 3 à 4 champs + promesse de rappel", 6, forme),
            ("H1 avec métier et ville", 5, 1 if mot in h1t and ville in h1t else 0),
            ("Zone d'intervention (≥ 2 communes)", 4, 1 if h.count('class="villes') and len(re.findall(r"<li>[^<]+</li>", re.search(r'class="villes.*?</ul>', h, re.S).group(0))) >= 2 else (.5 if h.count('class="villes') else 0)),
            ("Preuves en haut, fondées sur des données fournies", 5, (2 / 5 if preuves else 0) + (3 / 5 if preuves and "Preuves à ajouter" not in h else 0)),
            ("Contenu : 4-6 services, 5-8 questions, 3-4 étapes", 6, (2 if (3 if 'data-theme="lumiere"' in h else 4) <= h.count('class="svc') + h.count('class="pr ') <= 6 else 0) / 6 + (2 if 5 <= h.count("<details") <= 8 else 0) / 6 + (2 if 3 <= len(re.findall(r'<li class="rv">', h)) <= 4 else 0) / 6),
        ]
    regles = commun + propres
    assert sum(r[1] for r in regles) == 70, sum(r[1] for r in regles)
    pts, bad = 0.0, []
    for nom, mx, r in regles:
        r = max(0, min(1, r)); pts += mx * r
        if r < 1: bad.append(f"{nom} ({mx * r:.0f}/{mx})")
    if not aff_tel: bad.insert(0, "Téléphone manquant ou invalide")
    return round(pts), bad

def score_qa(q):
    """30 points : Lighthouse mobile (performance, accessibilité, SEO), console, débordement, captures."""
    if not q: return None, ["QA non lancée (node sites\\outils\\qa.mjs)"]
    pts, bad = 0, []
    for cle, mx, seuil, nom in [("perf", 8, 85, "Performance"), ("a11y", 6, 95, "Accessibilité"), ("seo", 6, 95, "SEO")]:
        v = q.get(cle)
        if v is not None and v >= seuil: pts += mx
        else: bad.append(f"Lighthouse {nom} {v} < {seuil}")
    if not q.get("console"): pts += 4
    else: bad.append(f"{len(q['console'])} erreur(s) console")
    if not q.get("debordement"): pts += 4
    else: bad.append("Débordement horizontal : " + ", ".join(q["debordement"]))
    if q.get("captures"): pts += 2
    return pts, bad

# --- sortie -------------------------------------------------------------------------------------------
def copier_assets():
    dest = PUBLIC / "assets" / "polices"
    dest.mkdir(parents=True, exist_ok=True)
    for f in (MOTEUR / "polices").glob("*.woff2"): shutil.copy2(f, dest / f.name)
    if (MOTEUR / "js").exists(): shutil.copytree(MOTEUR / "js", PUBLIC / "assets" / "js", dirs_exist_ok=True)
    src3d = MOTEUR / "modeles3d"
    if src3d.exists(): shutil.copytree(src3d, PUBLIC / "assets" / "3d", dirs_exist_ok=True)
    (PUBLIC / "vercel.json").write_text(json.dumps({"cleanUrls": True, "headers": [{"source": "/(.*)", "headers": [
        {"key": "X-Robots-Tag", "value": "noindex, nofollow, noarchive"}, {"key": "Referrer-Policy", "value": "no-referrer"},
        {"key": "Cache-Control", "value": "public, max-age=0, must-revalidate"}]}, {"source": "/assets/(.*)", "headers": [
        {"key": "Cache-Control", "value": "public, max-age=31536000, immutable"}]}]}, indent=2), encoding="utf-8")
    (PUBLIC / "robots.txt").write_text("User-agent: *\nDisallow: /\n", encoding="utf-8")
    (PUBLIC / "index.html").write_text('<!doctype html><meta charset="utf-8"><meta name="robots" content="noindex,nofollow"><title>Accès privé</title><p style="font:16px system-ui;padding:2rem">Accès privé.</p>\n', encoding="utf-8")

def preparer(ligne, base_csv):
    cle = metier_cle(ligne.get("metier", ""))
    if not ligne.get("nom") or not ligne.get("ville"): return None, "nom ou ville manquant"
    if not cle: return None, f"métier non géré : « {ligne.get('metier', '')} »"
    p = dict(ligne)
    p["nom"] = ligne["nom"] if not ligne["nom"].isupper() else ligne["nom"].title()
    p["ville"] = ligne["ville"].title() if ligne["ville"].isupper() else ligne["ville"]
    p["cle"] = cle
    p["exemple"] = ligne.get("exemple", "").lower() in ("oui", "1", "true", "x")
    p["_met"] = json.loads((MOTEUR / "metiers" / f"{cle}.json").read_text(encoding="utf-8"))
    p["famille"] = p["_met"].get("famille", "artisan")
    if p["famille"] == "local" and not p["exemple"]: return None, "métier « local » : page exemple seulement (pas de maquette de vrai prospect)"
    p["site"] = ligne.get("site") or ligne.get("siteactuel", "")
    p["illustrations"] = ligne.get("illustrations", "").lower() in ("oui", "1", "true", "x")
    d = ligne.get("direction", "").lower()
    p["direction"] = d if d in FAMILLE_THEMES[p["famille"]] else DIRECTION_PAR_METIER[cle]
    if ligne.get("photos"):
        f, auteur, lic = (ligne["photos"].split("|") + ["", "", ""])[:3]
        src = Path(base_csv) / f.strip()
        if src.exists() and auteur.strip() and lic.strip(): p["photo_hero"] = {"fichier": src.name, "src": src, "auteur": auteur.strip(), "licence": lic.strip()}
        else: print(f"  ! photo ignorée pour {p['nom']} (fichier absent, auteur ou licence manquant)")
    return p, None

def ecrire(p):
    dossier = f"{slug(p['nom'])}-{jeton(p['nom'], p['ville'])}"
    out = PUBLIC / dossier
    out.mkdir(parents=True, exist_ok=True)
    if p.get("photo_hero"):
        (out / "img").mkdir(exist_ok=True)
        shutil.copy2(p["photo_hero"]["src"], out / "img" / p["photo_hero"]["fichier"])
        ph = p["photo_hero"]
        (out / "registre-licences.md").write_text(f"| Fichier | Auteur | Licence | Date |\n|---|---|---|---|\n| {ph['fichier']} | {ph['auteur']} | {ph['licence']} | {date.today()} |\n", encoding="utf-8")
        p["registre"] = True
    import modeles2
    fam = {"restaurant": modeles.restaurant, "commerce": modeles.commerce, "groupe": modeles2.groupe}.get(p["famille"])
    if p["famille"] == "artisan" and p["direction"] == "lumiere" and p["_met"].get("lumiere"): fam = modeles3.lumiere
    if p["famille"] == "artisan" and p["direction"] == "eau" and p["_met"].get("eau"): fam = modeles4.eau
    if p["famille"] == "restaurant" and p["direction"] == "braise" and p["_met"].get("braise"): fam = modeles5.braise
    if p["famille"] == "local": fam = getattr(modeles6, p["direction"])
    h = fam(p, p["_met"], sys.modules[__name__]) if fam else construire(p, p["_met"])
    if p.get("_photos_utilisees"):  # photos libres de la bibliothèque : copie + registre de licences
        (out / "img").mkdir(exist_ok=True)
        lignes = ["| Fichier | Auteur | Source | Licence | Vérifié le |", "|---|---|---|---|---|"]
        for cle in p["_photos_utilisees"]:
            i = p["_licences"][cle]
            shutil.copy2(modeles.PHOTOS / i["fichier"], out / "img" / i["fichier"])
            petit = modeles.PHOTOS / i["fichier"].replace(".webp", "-800.webp")
            if petit.exists(): shutil.copy2(petit, out / "img" / petit.name)
            lignes.append(f"| {i['fichier']} | {i['auteur']} | {i['source']} | {i['licence']} | {i['date']} |")
        notes = "".join(f"\n- {p['_licences'][c]['fichier']} : {p['_licences'][c]['traitement']}" for c in p["_photos_utilisees"] if p["_licences"][c].get("traitement"))
        notes = f"\n\nImages dérivées (traitement appliqué) :{notes}" if notes else ""
        (out / "registre-licences.md").write_text("\n".join(lignes) + notes + "\n\nPhotos d'illustration : à remplacer par les photos de l'établissement.\n", encoding="utf-8")
        p["registre"] = True
    for nom_f in p.get("_fichiers_artisan", []):  # photos de l'artisan (curseur avant/après) : déposées dans moteur\photos\
        if (modeles.PHOTOS / nom_f).exists(): (out / "img").mkdir(exist_ok=True); shutil.copy2(modeles.PHOTOS / nom_f, out / "img" / nom_f)
    if p["famille"] == "commerce" and p["exemple"] and (modeles.PHOTOS / "vase-poster.webp").exists():
        (out / "img").mkdir(exist_ok=True)
        shutil.copy2(modeles.PHOTOS / "vase-poster.webp", out / "img" / "vase-poster.webp")
    (out / "index.html").write_text(h, encoding="utf-8")
    return dossier, h

def maj_suivi(lignes_score, lignes_suivi):
    if not SUIVI.exists(): print("  ! agents\\dev-sites.md introuvable, suivi non mis à jour"); return
    t = SUIVI.read_text(encoding="utf-8")
    def remplace(texte, debut, fin, nouvelles, cle_col):
        m = re.search(rf"({re.escape(debut)}.*?\n)(.*?)(\n?{re.escape(fin)})", texte, re.S)
        if not m: return texte
        corps = m.group(2).split("\n")
        entete, anciennes = corps[:2], [l for l in corps[2:] if l.strip()]
        cles = {l.split("|")[cle_col].strip() for l in nouvelles}
        gardees = [l for l in anciennes if l.split("|")[cle_col].strip() not in cles]
        return texte[:m.start(2)] + "\n".join(entete + gardees + nouvelles) + m.group(3) + texte[m.end():]
    t = remplace(t, "<!-- SCORES:DEBUT", "<!-- SCORES:FIN", lignes_score, 2)
    t = remplace(t, "<!-- SUIVI:DEBUT", "<!-- SUIVI:FIN", lignes_suivi, 1)
    SUIVI.write_text(t, encoding="utf-8")

def calculer(manifeste):
    qa = json.loads(QA_JSON.read_text(encoding="utf-8")) if QA_JSON.exists() else {}
    sc, su = [], []
    for dossier, m in manifeste.items():
        h = (PUBLIC / dossier / "index.html").read_text(encoding="utf-8")
        p = {**m, "_met": json.loads((MOTEUR / "metiers" / f"{m['cle']}.json").read_text(encoding="utf-8"))}
        a, bad = score_auto(h, p, tel_norm(m.get("telephone"))[0])
        q, badq = score_qa(qa.get(dossier))
        total = f"{a + q}/100" if q is not None else f"{a}/70 (QA à faire)"
        m["score"] = total
        lib = " ; ".join((bad + ([] if q is not None else []) + badq)[:3]).replace("|", "/") or "—"
        sc.append(f"| {date.today()} | {dossier} | {m['direction']} | {a} | {q if q is not None else '—'} | {total} | {lib} |")
        etat = "EXEMPLE (fictif), local" if m["exemple"] else "maquette générée, locale, non déployée"
        su.append(f"| {m['nom']} | {m['_metier_txt']} | {m['ville']} | {etat} | sites\\public\\{dossier}\\ | {date.today()} : génération |")
    return sc, su

EXEMPLES_ARCHIVE = [  # anciens styles électricien (technique, rassurant, premium) : archivés, toujours générables avec --archive
    dict(nom="Exemple Électricité (technique)", metier="Électricien", ville="Rouen", telephone="02 61 91 66 01", zone="Rouen, Sotteville-lès-Rouen, Petit-Quevilly, Le Grand-Quevilly, Mont-Saint-Aignan, Bois-Guillaume, Darnétal, Canteleu",
         note="4,8", avis="52", annees="12", labels="Qualifelec (exemple), Assurance décennale (exemple)", direction="technique", exemple="oui"),
    dict(nom="Exemple Élec Famille (rassurant)", metier="Électricien", ville="Elbeuf", telephone="02 61 91 66 02", zone="Elbeuf, Caudebec-lès-Elbeuf, Saint-Aubin-lès-Elbeuf, Cléon, Oissel, Tourville-la-Rivière",
         note="4,9", avis="87", annees="8", labels="Devis gratuit", direction="rassurant", exemple="oui"),
    dict(nom="Atelier Exemple Électricité (premium)", metier="Électricien", ville="Rouen", telephone="02 61 91 66 03", zone="Rouen, Bihorel, Bois-Guillaume, Mont-Saint-Aignan, Maromme, Déville-lès-Rouen",
         note="5,0", avis="31", annees="20", labels="Rénovation haut de gamme (exemple)", direction="premium", exemple="oui"),
]

EXEMPLES = [  # données fictives. N° du plan de numérotation réservé à la fiction (ARCEP : 02 61 91 66 xx)
    dict(nom="Atelier Lumière Exemple", metier="Électricien", ville="Rouen", telephone="02 61 91 66 08", zone="Rouen, Sotteville-lès-Rouen, Petit-Quevilly, Mont-Saint-Aignan, Bois-Guillaume, Darnétal",
         note="4,9", avis="64", annees="15", qualification="Qualifelec RGE n° 00000 (exemple)", decennale="Assureur fictif, contrat n° 000 (exemple)", delai="Rappel sous 2 h (exemple)", direction="lumiere", exemple="oui"),
    dict(nom="Atelier Exemple Plomberie", metier="Plombier-chauffagiste", ville="Rouen", telephone="02 61 91 66 09", zone="Rouen, Sotteville-lès-Rouen, Petit-Quevilly, Mont-Saint-Aignan, Bois-Guillaume, Darnétal", direction="eau", exemple="oui"),
    dict(nom="Bistro Exemple", metier="Restaurant", ville="Rouen", telephone="02 61 91 66 04", note="4,6", avis="214", direction="bistro", exemple="oui"),
    dict(nom="La Table Exemple du Marché", metier="Restaurant", ville="Rouen", telephone="02 61 91 66 05", note="4,7", avis="96", direction="marche", exemple="oui"),
    dict(nom="La Braise Exemple", metier="Restaurant", ville="Rouen", telephone="02 61 91 66 10", direction="braise", exemple="oui"),
    dict(nom="Atelier Ciseaux Exemple", metier="Coiffeur", ville="Rouen", telephone="02 61 91 66 11", direction="salon", exemple="oui"),
    dict(nom="Atelier Pétale Exemple", metier="Fleuriste", ville="Rouen", telephone="02 61 91 66 12", direction="petale", exemple="oui"),
    dict(nom="Fournil Exemple", metier="Boulangerie", ville="Rouen", telephone="02 61 91 66 13", direction="fournil", exemple="oui"),
    dict(nom="Garage Exemple Mécanique", metier="Garage automobile", ville="Rouen", telephone="02 61 91 66 14", direction="garage", exemple="oui"),
    dict(nom="Atelier Exemple Céramique", metier="Commerce", ville="Rouen", telephone="02 61 91 66 06", direction="atelier", exemple="oui"),
    dict(nom="Maisons Exemple", metier="Groupe de restaurants", ville="Rouen", telephone="02 61 91 66 07", direction="maison", exemple="oui"),
]

def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Génère une maquette par prospect (CSV).")
    ap.add_argument("csv", nargs="?"); ap.add_argument("--exemples", action="store_true"); ap.add_argument("--rescore", action="store_true"); ap.add_argument("--archive", action="store_true"); ap.add_argument("--exemple", help="un seul exemple fictif (mot du nom), sans régénérer les autres")
    a = ap.parse_args()
    SORTIES.mkdir(exist_ok=True)
    mf = SORTIES / "manifeste.json"
    manifeste = json.loads(mf.read_text(encoding="utf-8")) if mf.exists() else {}
    if a.rescore:
        pass
    else:
        if a.archive: lignes, base = [{**x, "site": ""} for x in EXEMPLES_ARCHIVE], "."
        elif a.exemples or a.exemple: lignes, base = [{**x, "site": ""} for x in EXEMPLES if not a.exemple or a.exemple.lower() in slug(x["nom"])], "."
        elif a.csv: lignes, base = lire_csv(a.csv), Path(a.csv).resolve().parent
        else: ap.error("donner un CSV ou --exemples")
        copier_assets()
        n, ignores = 0, []
        for l in lignes:
            p, err = preparer(l, base)
            if err: ignores.append((l.get("nom", "?"), err)); continue
            dossier, _ = ecrire(p)
            manifeste[dossier] = {k: v for k, v in p.items() if k not in ("_met", "photo_hero") and not k.startswith("_")} | {"_metier_txt": l.get("metier", ""), "registre": p.get("registre", False)}
            n += 1
        print(f"{n} maquette(s) dans {PUBLIC}")
        for nom, err in ignores: print(f"  ignoré : {nom} ({err})")
    sc, su = calculer(manifeste)
    mf.write_text(json.dumps(manifeste, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    maj_suivi(sc, su)
    for l in sc: print(" ", l)

if __name__ == "__main__":
    main()
