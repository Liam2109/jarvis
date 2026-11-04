"""Thème de base « premium 2026 » + direction artistique A « Atelier Lumière » (électricien), version 3. Appelé via generer.py.
Les contenus de la DA viennent de metiers/<métier>.json › "lumiere". Les variables du CSV pilotent le reste :
qualification, decennale, delai (bande de preuves, seulement si fournis), avis_reels ("texte|auteur||texte|auteur"), lien_avis,
note + avis + source (source_avis ou source), annees (chiffres animés seulement s'ils sont fournis)."""
import html, json, math, re
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent
CREDITS = DOSSIER / "photos" / "CREDITS.json"
TOUT_24H = re.compile(r"24\s?h\s?(?:/|sur)\s?24|24h24|24\s?/\s?7|7\s?j(?:ours)?\s?(?:/|sur)\s?7", re.I)
CHIFFRES_FIXES = {"0", "1", "2", "3", "4", "5", "01", "02", "03", "04", "15", "100", "1600"}  # numérotation, « 4 informations », « sur 5 », NF C 15-100, « 1600 px minimum » (légende des emplacements photo)


def credits():
    """Photos libres déclarées dans CREDITS.json ; une entrée sans url, auteur, licence et date n'est pas utilisable."""
    try: c = json.loads(CREDITS.read_text(encoding="utf-8"))
    except (OSError, ValueError): return {}
    return {k: v for k, v in c.items() if not k.startswith("_") and all(v.get(x) for x in ("fichier", "url", "auteur", "licence", "date", "alt", "largeur", "hauteur"))}


def controles(h, p, vars_txt):
    """Règles bloquantes : renvoie la liste des erreurs (vide si la page est conforme)."""
    err = []
    texte = re.sub(r"<(script|style)\b.*?</\1>", " ", h, flags=re.S)
    texte = html.unescape(re.sub(r"<[^>]+>", " ", texte))
    if TOUT_24H.search(texte) and not p.get("horaires"): err.append("« 24 h/24 » sans horaires fournis")
    if re.search(r'<img\b(?![^>]*\salt="[^"]+")', h): err.append("image sans alt")
    if "aggregateRating" in h: err.append("aggregateRating interdit")
    permis = CHIFFRES_FIXES | set(re.findall(r"\d+", vars_txt))
    inconnus = sorted({n for n in re.findall(r"\d+", texte) if n not in permis})
    if inconnus: err.append("chiffres qui ne viennent pas des variables : " + ", ".join(inconnus[:6]))
    return err


def mini_css(css):
    """Retire commentaires et espaces inutiles (sans toucher aux chaînes)."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"\s+", " ", css)
    css = re.sub(r"\s*([{};,>])\s*", r"\1", css)
    return css.replace(";}", "}").strip()


AMPOULE = """<svg class="bulb" viewBox="0 0 240 400" role="img" aria-label="Ampoule à filament allumée" width="240" height="400">
<defs><linearGradient id="vr" x1="0" x2="1"><stop offset="0" stop-color="#f4efe6" stop-opacity=".16"/><stop offset=".5" stop-color="#f4efe6" stop-opacity=".04"/><stop offset="1" stop-color="#f4efe6" stop-opacity=".14"/></linearGradient>
<linearGradient id="lt" x1="0" x2="1"><stop offset="0" stop-color="#7a5f2e"/><stop offset=".45" stop-color="#d9b779"/><stop offset="1" stop-color="#8d6e3a"/></linearGradient></defs>
<path d="M120 14c-58 0-98 40-98 96 0 38 20 62 38 86 10 14 14 26 14 44v12h92v-12c0-18 4-30 14-44 18-24 38-48 38-86 0-56-40-96-98-96z" fill="url(#vr)" stroke="#b08d57" stroke-opacity=".7" stroke-width="2"/>
<path d="M98 252V150M142 252V150" stroke="#b08d57" stroke-width="2" fill="none"/>
<path d="M98 150l11 -20 11 20 11 -20 11 20" stroke="#8a5a14" stroke-width="3.5" fill="none" stroke-linejoin="round" stroke-linecap="round"/>
<g class="glow"><path d="M98 150l11 -20 11 20 11 -20 11 20" stroke="#ffd37a" stroke-width="4" fill="none" stroke-linejoin="round" stroke-linecap="round" style="filter:drop-shadow(0 0 7px #e8a23a) drop-shadow(0 0 18px #e8a23a)"/></g>
<rect x="74" y="252" width="92" height="24" fill="url(#lt)"/><rect x="78" y="282" width="84" height="20" fill="url(#lt)"/><rect x="82" y="308" width="76" height="20" fill="url(#lt)"/>
<path d="M92 334h56l-8 20h-40z" fill="#3a352d"/></svg>"""

# scripts chargés dans l'ordre, à la première interaction ou 1,8 s après load (tout de suite si le navigateur n'a pas animation-timeline) : ils ne concurrencent ni les polices ni le premier affichage (LCP)
CHARGEUR = """<script>(function(){var ok=0;function go(){if(ok)return;ok=1;["gsap.min.js","ScrollTrigger.min.js","lumiere.js"].forEach(function(n){var s=document.createElement("script");s.src="../assets/js/"+n;s.async=false;document.body.appendChild(s)})}addEventListener("load",function(){if(document.documentElement.classList.contains("gsap-rv"))go();else setTimeout(go,1800)});["scroll","touchstart","pointerdown","keydown"].forEach(function(n){addEventListener(n,go,{once:true,passive:true})})})()</script>"""

# amorce : classes pour le JS, et repli GSAP pour les navigateurs sans animation-timeline (Safari avant 26, Firefox avant 159)
AMORCE = """<script>(function(r){r.classList.add("js");if(!matchMedia("(prefers-reduced-motion: reduce)").matches&&!(window.CSS&&CSS.supports&&CSS.supports("animation-timeline","view()"))){r.classList.add("gsap-rv");window.__rvT=setTimeout(function(){r.classList.remove("gsap-rv")},8000)}})(document.documentElement)</script>"""


def carte_zone(zone, ville, e):
    """Schéma stylisé (pas une carte à l'échelle) : la ville au centre, les communes en pastilles autour."""
    cx, cy = 300, 210
    autres = [v for v in zone if v != ville][:8]
    out = [f'<svg class="map" viewBox="0 0 600 420" role="img" aria-label="Schéma de la zone d\'intervention autour de {e(ville)}, sans échelle" width="600" height="420">',
           f'<ellipse cx="{cx}" cy="{cy}" rx="132" ry="92" class="ring1"/><ellipse cx="{cx}" cy="{cy}" rx="232" ry="160" class="ring2"/>']
    pas, lignes = [], []
    n = len(autres)
    for i, v in enumerate(autres):
        a = -math.pi / 2 + i * 2 * math.pi / max(n, 1) + 0.35
        rx, ry = (232, 160) if i % 2 == 0 else (132, 92)
        w = int(len(v) * 10.6 + 36)
        x = min(max(cx + rx * math.cos(a), w / 2 + 6), 600 - w / 2 - 6)
        y = min(max(cy + ry * math.sin(a), 24), 396)
        lignes.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.0f}" y2="{y:.0f}" class="lk"/>')
        pas.append(f'<g transform="translate({x - w / 2:.0f} {y - 20:.0f})"><g class="pas"><rect width="{w}" height="40" rx="20"/><text x="{w / 2}" y="27" text-anchor="middle">{e(v)}</text></g></g>')
    wc = int(len(ville) * 12 + 48)
    out += lignes + pas
    out.append(f'<g transform="translate({cx - wc / 2:.0f} {cy - 24})"><g class="ctr"><rect width="{wc}" height="48" rx="24"/><text x="{wc / 2}" y="31" text-anchor="middle">{e(ville)}</text></g></g></svg>')
    return "".join(out)


def lumiere(p, met, G):
    """Page « Atelier Lumière ». G = module generer (outils partagés)."""
    L = met["lumiere"]
    ex = p["exemple"]
    nom, ville, label = p["nom"], p["ville"], met["label"]
    e, fm = G.e, G.fm
    aff_tel, tel_intl = G.tel_norm(p.get("telephone"))
    badge = '<span class="badge-ex">exemple</span>' if ex else ""
    icone = G.ICONE_TEL.replace("<svg ", '<svg class="ring" ', 1)
    if aff_tel:
        def appel(cls="btn btn-main", txt=None):
            return f'<a class="{cls}" href="tel:{tel_intl}">{icone}<span>{e(txt or "Appeler le " + aff_tel)}</span></a>'
        lien_tel = f'<a class="tel-big" href="tel:{tel_intl}">{aff_tel}</a>'
    else:
        def appel(cls="btn btn-main", txt=None):
            return f'<a class="{cls}" href="#contact">{icone}<span>Appeler : <mark class="todo">n° à compléter</mark></span></a>'
        lien_tel = '<a class="tel-big" href="#contact"><mark class="todo">n° à compléter</mark></a>'
    devis = '<a class="btn btn-line" href="#contact"><span>Demander un devis</span></a>'

    # zone : communes fournies, sinon la ville seule + « à compléter »
    zone = G.liste(p.get("zone"))
    if ville not in zone: zone.insert(0, ville)
    zone = zone[:14]
    zone_todo = "" if len(zone) > 1 else ' <mark class="todo">communes desservies à compléter</mark>'
    communes = ", ".join(e(v) for v in zone[1:5]) + (" et alentours" if len(zone) > 1 else "")

    # preuves : seulement ce que les variables fournissent ; les chiffres animés sont ceux de ces variables
    pr = []
    note, avis = G.nombre(p.get("note")), G.nombre(p.get("avis"))
    source_avis = p.get("sourceavis") or p.get("source") or ""
    if note and avis and (ex or source_avis):
        nf = f"{note:.1f}"
        pr.append(("Note Google", f'<span class="num" data-to="{nf}" data-dec="1">{nf.replace(".", ",")}</span> / 5 · <span class="num" data-to="{int(avis)}">{int(avis)}</span> avis', True))
    for cle, lib in (("qualification", "Qualification"), ("decennale", "Décennale")):  # un badge sans numéro n'est pas affiché
        if p.get(cle) and re.search(r"\d", p[cle]): pr.append((lib, e(p[cle]), True))
        elif p.get(cle): print(f"  ! {lib} ignorée pour {nom} : pas de numéro")
    if p.get("delai"): pr.append(("Délai d'intervention", e(p["delai"]), True))
    an = G.nombre(p.get("annees"))
    if an: pr.append(("Activité", f'<span class="num" data-to="{int(an)}">{int(an)}</span> ans', True))
    for lb in G.liste(p.get("labels"))[:3]: pr.append(("Label", e(lb), True))
    preuves = ""
    if pr:
        li = "".join(f"<li class=\"rv p\"><small>{e(k)}</small>{v}{badge}</li>" for k, v, _ in pr)
        preuves = f'<section class="proofs" aria-label="Preuves"><div class="w"><ul>{li}</ul></div></section>'

    cr = credits() if (ex or p.get("illustrations")) else {}
    utilisees = []

    def photo(cle, sizes, legende, lazy=True):
        """<figure> avec la photo libre `cle` (licence dans CREDITS.json) ou None si elle n'est pas utilisable."""
        c = cr.get(cle)
        if not c: return None
        utilisees.append(cle)
        base = c["fichier"][:-5]
        petit = (G.modeles.PHOTOS / f"{base}-800.webp").exists()
        srcset = f' srcset="img/{e(base)}-800.webp 800w, img/{e(c["fichier"])} {c["largeur"]}w"' if petit else ""
        return (f'<figure class="ph-img rv"><img src="img/{e(c["fichier"])}"{srcset} sizes="{sizes}" alt="{e(c["alt"])}" width="{c["largeur"]}" height="{c["hauteur"]}" loading="lazy" decoding="async">'
                f'<figcaption>{legende.format(auteur=e(c["auteur"]))}</figcaption></figure>')

    def zone_photo(titre, detail):
        return f'<div class="ph rv"><b>{e(titre)}</b><span>{e(detail)}</span><small>Photo de l\'artisan, avec son accord (1600 px minimum).</small></div>'

    LEG = "Photo d'illustration libre de droits (Unsplash, {auteur}) — à remplacer par une photo de l'artisan"
    LEG_C = "Illustration libre de droits (Unsplash, {auteur}) — à remplacer"
    prest = ""
    for i, s in enumerate(L["prestations"], 1):
        vis = photo(s.get("img"), "(min-width:900px) 55vw, 100vw", LEG) or f'<div class="ph"><b>Photo à remplacer</b><span>{e(s["photo"])}</span><small>Photo de l\'artisan, avec son accord (4:3, 1600 px minimum).</small></div>'
        prest += f'<article class="pr rv">{vis}<div><p class="n">0{i}</p><h3>{e(s["t"])}</h3><p>{fm(s["d"])}</p></div></article>'

    # bandeau défilant : les prestations, deux fois (la copie est masquée aux lecteurs d'écran)
    mots = [s["t"] for s in L["prestations"]] + [x.strip() for x in L["autres"].split("·") if x.strip()]
    liste_mq = "".join(f"<li>{e(m)}</li>" for m in mots)
    marq = f'<div class="marq" aria-label="Nos prestations"><div class="marq-t"><ul>{liste_mq}</ul><ul aria-hidden="true">{liste_mq}</ul></div></div>'

    # avant / après : curseur accessible (input range) si les deux photos sont utilisables, sinon zones à remplacer
    AA = L["avant_apres"]
    av, ap_ = cr.get("lumiere-avant"), cr.get("lumiere-apres")
    if av and ap_:
        utilisees += ["lumiere-avant", "lumiere-apres"]
        def im(c, cls): return f'<img class="{cls}" src="img/{e(c["fichier"])}" alt="{e(c["alt"])}" width="{c["largeur"]}" height="{c["hauteur"]}" loading="lazy" decoding="async">'
        ba = (f'<figure class="ba-f rv"><div class="ba" data-ba>{im(ap_, "ap")}<div class="av">{im(av, "")}</div>'
              f'<span class="ba-h" aria-hidden="true"></span><span class="ba-l l1" aria-hidden="true">Avant</span><span class="ba-l l2" aria-hidden="true">Après</span>'
              f'<input class="ba-range" type="range" min="0" max="100" value="50" aria-label="Comparer avant et après : déplacez le curseur"></div>'
              f'<figcaption>Photos d\'illustration libres de droits (Unsplash, {e(av["auteur"])} et {e(ap_["auteur"])}) — à remplacer par un vrai chantier de l\'artisan</figcaption></figure>')
    else:
        ba = ('<div class="ba-ph rv">' + zone_photo("Avant — photo à remplacer", "Installation d'origine, avant les travaux") + zone_photo("Après — photo à remplacer", "Même endroit, une fois les travaux finis") + "</div>")
    avant_apres = (f'<section class="section ba-sec" id="avant-apres"><div class="w"><div><p class="eyebrow rv">Avant / après</p><h2 class="rv">{e(AA["t"])}</h2>'
                   f'<p class="rv" style="color:var(--muted)">{fm(AA["d"])}</p></div>{ba}</div></section>')

    # engagements : propositions à confirmer par l'artisan, sans chiffre
    eng = "".join(f'<li class="rv e"><span class="big" aria-hidden="true">{i}</span><h3>{e(x["t"])}</h3><p>{fm(x["d"])}</p></li>' for i, x in enumerate(L["engagements"], 1))
    engagements = (f'<section class="section eng" id="engagements"><div class="w"><p class="eyebrow rv">Nos engagements</p><h2 class="rv">Trois promesses, tenues</h2>'
                   f'<ol>{eng}</ol><p class="note rv"><mark class="todo">Engagements proposés : à confirmer par l\'artisan avant mise en ligne</mark></p></div></section>')

    # galerie : photos d'exemple libres, ou zones à remplacer
    tuiles = [photo(k, "(min-width:900px) 25vw, 50vw", LEG_C) for k in L["galerie"]]
    tuiles = [t or zone_photo("Photo à remplacer", "Réalisation de l'artisan") for t in tuiles]
    galerie = f'<section class="section" id="realisations"><div class="w"><p class="eyebrow rv">Réalisations</p><h2 class="rv">Des chantiers soignés</h2><div class="gal">{"".join(tuiles)}</div></div></section>'

    steps = "".join(f'<li class="rv"><h3>{fm(s["t"])}</h3><p>{fm(s["d"])}</p></li>' for s in met["etapes"])
    faq = "".join(f'<details class="rv"><summary>{fm(q["q"])}</summary><p>{fm(q["a"])}</p></details>' for q in met["faq"])
    villes = "".join(f"<li>{e(v)}</li>" for v in zone)
    options = "".join(f"<option>{e(o)}</option>" for o in met["besoins"])

    # avis : réels seulement (variable avis_reels), sinon zone d'attente
    lien = p.get("lienavis", "")
    lien_html = f'<a href="{e(lien)}" rel="noopener">Lire tous les avis sur Google</a>' if lien.startswith("https://") else ""
    reels = [x.split("|") for x in re.split(r"\|\|", p.get("avisreels", "")) if x.strip()]
    if reels:
        avis_html = '<div class="revs">' + "".join(f'<blockquote class="rev rv">{e(a[0])}<cite>{e(a[1].strip()) if len(a) > 1 else ""}</cite></blockquote>' for a in reels[:3]) + f'</div><p style="margin-top:var(--s3)">{lien_html}</p>'
    else:
        resume = f"Note Google : {note:.1f} / 5 sur {int(avis)} avis. ".replace(".", ",", 1) if note and avis else ""
        avis_html = (f'<div class="rev rv"><b>Vos avis Google réels s\'afficheront ici</b>'
                     f'<p>{resume}Les avis sont repris tels quels depuis la fiche Google, avec l\'accord de leurs auteurs. Aucun avis n\'est inventé.</p>{lien_html}</div>')

    titre = f"{label} à {ville} — {nom}"
    desc = f"{label} à {ville} et alentours : éclairage, tableau, mise aux normes. Devis gratuit, rappel rapide" + (f" au {aff_tel}." if aff_tel else ".")
    ld = {"@context": "https://schema.org", "@type": met["schema"], "name": nom, "description": desc,
          "address": {"@type": "PostalAddress", "addressLocality": ville, "addressCountry": "FR"},
          "areaServed": [{"@type": "City", "name": v} for v in zone]}
    if tel_intl: ld["telephone"] = tel_intl
    if ex:
        bandeau = '<b>EXEMPLE</b> — entreprise, numéro et chiffres fictifs, aucun avis réel. Maquette de démonstration LM MULTI-SERVICES.'
    else:
        bandeau = f'Maquette de démonstration préparée par LM MULTI-SERVICES pour {e(nom)}. <b>Ce n\'est pas le site officiel</b> de l\'entreprise. Les zones surlignées sont à compléter.'

    # titre du hero : un <span> par mot (montée échelonnée en CSS pur ; le texte reste visible dès le premier affichage)
    mots_h1 = " ".join(f'<span class="wd" style="--i:{i}">{e(w)}</span>' for i, w in enumerate(L["titre"].split()))

    familles, precharge = G.THEMES["lumiere"]
    css = mini_css(G.css_polices(familles) + (G.MOTEUR / "themes" / "lumiere.css").read_text(encoding="utf-8"))
    page = f"""<!doctype html>
<html lang="fr" data-theme="lumiere">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(titre)}</title>
<meta name="description" content="{e(desc)}">
<meta name="robots" content="noindex, nofollow, noarchive">
<meta name="theme-color" content="#1C1A17">
<link rel="icon" href="data:,">
<link rel="preload" href="../assets/polices/{precharge}" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="../assets/polices/Inter-400-600.woff2" as="font" type="font/woff2" crossorigin>
<style>{css}</style>
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
{AMORCE}
</head>
<body>
<a class="skip" href="#contact">Aller au formulaire</a>
<div class="pg" aria-hidden="true"><i></i></div>
<div class="banner" role="note">{bandeau}</div>
<header class="top"><div class="w">
  <a class="brand" href="#top">{e(nom)}</a>
  <nav class="nav" aria-label="Sections"><a href="#prestations">Prestations</a><a href="#methode">Méthode</a><a href="#zone">Zone</a><a href="#faq">Questions</a></nav>
  {appel("btn btn-main", "Appeler")}
</div></header>
<main id="top">
<section class="hero dark"><div class="w">
  <div>
    <h1><span class="kicker">{e(label)} à {e(ville)}{badge}</span>{mots_h1}</h1>
    <p class="lead">{fm(L["lead"])}</p>
    <div class="cta">{appel()}{devis}</div>
    <p class="zone-line"><b>{e(ville)}</b>{" et " + communes if len(zone) > 1 else ""}.{zone_todo}</p>
  </div>
  <div class="bulbwrap"><div class="halo" aria-hidden="true"></div><div class="halo hot" aria-hidden="true"></div>{AMPOULE}</div>
</div></section>
<div class="dawn" aria-hidden="true"><div class="dawn-g"></div></div>
{preuves}
{marq}
<section class="section" id="prestations"><div class="w">
  <p class="eyebrow rv">Ce que nous faisons</p><h2 class="rv">Trois savoir-faire, un même soin</h2>
  <div class="presta">{prest}</div>
  <p class="autres rv">Aussi : {e(L["autres"])}</p>
</div></section>
{avant_apres}
<section class="section dark" id="methode"><div class="w m-grid">
  <div class="m-pin"><p class="eyebrow">Comment ça se passe</p><h2>De l'appel à l'intervention</h2><div class="m-count" aria-hidden="true">01</div></div>
  <div class="steps-w"><span class="m-line" aria-hidden="true"><i></i></span><ol class="steps">{steps}</ol></div>
</div></section>
{engagements}
{galerie}
<section class="section alt" id="avis"><div class="w">
  <p class="eyebrow rv">Avis clients</p><h2 class="rv">Ce que disent les clients</h2>
  {avis_html}
</div></section>
<section class="section" id="zone"><div class="w zone">
  <div><p class="eyebrow rv">Zone d'intervention</p><h2 class="rv">Autour de {e(ville)}</h2>
  <p class="rv" style="color:var(--muted)">{e(nom)} intervient dans ces communes{zone_todo}. Une autre commune ? Appelez pour vérifier.</p>
  <ul class="villes rv">{villes}</ul></div>
  <div class="rv">{carte_zone(zone, ville, e)}<p class="map-n">Schéma indicatif, sans échelle.</p></div>
</div></section>
<section class="section alt" id="faq"><div class="w">
  <p class="eyebrow rv">Questions fréquentes</p><h2 class="rv">Vos questions</h2>
  <div class="faq">{faq}</div>
</div></section>
<section class="section contact dark" id="contact"><div class="w">
  <div><p class="eyebrow">Contact</p><h2>Un devis, un rappel</h2>
  <p class="lead">Appelez, ou laissez 4 informations : on vous rappelle sous <mark class="todo">délai à confirmer</mark>.</p>
  {lien_tel}</div>
  <form class="f" action="#contact" method="post" id="devis">
    <label for="f-nom">Votre nom<input id="f-nom" name="nom" autocomplete="name" required></label>
    <label for="f-tel">Votre téléphone<input id="f-tel" name="tel" type="tel" autocomplete="tel" inputmode="tel" required></label>
    <label for="f-ville">Votre commune<input id="f-ville" name="ville" autocomplete="address-level2"></label>
    <label for="f-besoin">Votre besoin<select id="f-besoin" name="besoin">{options}</select></label>
    <button class="btn btn-main" type="submit">Être rappelé(e)</button>
    <p class="note">Votre numéro sert uniquement à vous rappeler.</p>
    <p class="ok" role="status">Maquette : l'envoi est désactivé. {"Pour joindre l'artisan, appelez le " + aff_tel + "." if aff_tel else ""}</p>
  </form>
</div></section>
<section class="mentions" id="mentions"><div class="w">
  <h2>Mentions légales</h2>
  <p>{e(nom)} — {e(label)} à {e(ville)}. SIRET <mark class="todo">à compléter</mark> · Assurance décennale <mark class="todo">à compléter</mark> · Responsable de publication et hébergeur <mark class="todo">à compléter</mark>.</p>
</div></section>
</main>
<footer><div class="w">
  <p><strong>{e(nom)}</strong> — {e(label)} à {e(ville)} · {appel("", aff_tel or "Appeler").replace('class=""', 'class="fl"')}</p>
  <p>Maquette réalisée par LM MULTI-SERVICES. Page privée, non référencée.</p>
</div></footer>
<div class="bar">{appel("btn btn-main", "Appeler")}<a class="btn btn-line" href="#contact"><span>Devis gratuit</span></a></div>
{CHARGEUR}
</body>
</html>
"""
    if utilisees:  # copie + registre faits par generer.ecrire
        uniques = list(dict.fromkeys(utilisees))
        p["_photos_utilisees"] = uniques
        p["_licences"] = {k: {"fichier": cr[k]["fichier"], "auteur": cr[k]["auteur"], "source": cr[k]["url"], "licence": cr[k]["licence"], "date": cr[k]["date"]} for k in uniques}
    erreurs = controles(page, p, " ".join(str(v) for k, v in p.items() if not k.startswith("_")))
    if erreurs: raise ValueError(f"page bloquée pour {nom} : " + " ; ".join(erreurs))
    return page
