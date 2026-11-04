"""Modèles restaurant et commerce (même moteur que les artisans). Appelés par generer.py : h = module generer."""
import json, re, struct
from pathlib import Path

PHOTOS = Path(__file__).resolve().parent / "photos"
JS_COMMUN = """<script>
(function(){
  var els=document.querySelectorAll(".rv");
  if(!("IntersectionObserver" in window)){els.forEach(function(x){x.classList.add("in")});}
  else{var io=new IntersectionObserver(function(a){a.forEach(function(i){if(i.isIntersecting){i.target.classList.add("in");io.unobserve(i.target)}})},{rootMargin:"0px 0px -8% 0px"});els.forEach(function(x){io.observe(x)});}
  var f=document.getElementById("devis");
  if(f)f.addEventListener("submit",function(ev){ev.preventDefault();f.classList.add("sent")});
})();
</script>"""
JS_3D = """<script>
(function(){
  var box=document.querySelector(".v3d"),btn=document.getElementById("v3d-go");
  if(!box||!btn)return;
  btn.addEventListener("click",function(){
    btn.disabled=true;btn.textContent="Chargement…";
    var s=document.createElement("script");s.type="module";s.src=box.dataset.lib;
    s.onerror=function(){repli("Le 3D n'a pas pu se charger : voici la photo.")};
    s.onload=function(){
      var mv=document.createElement("model-viewer");
      mv.setAttribute("src",box.dataset.src);mv.setAttribute("alt",box.dataset.alt);
      mv.setAttribute("camera-controls","");mv.setAttribute("shadow-intensity","1");mv.setAttribute("poster",box.dataset.poster);
      mv.setAttribute("environment-image","neutral");mv.setAttribute("interaction-prompt","none");
      if(!window.matchMedia("(prefers-reduced-motion: reduce)").matches)mv.setAttribute("auto-rotate","");
      mv.addEventListener("error",function(){repli("Le 3D n'est pas disponible sur cet appareil : voici la photo.")});
      mv.addEventListener("load",function(){var i=box.querySelector("img");if(i)i.remove();btn.remove()});
      box.appendChild(mv);
    };
    document.head.appendChild(s);
  });
  function repli(t){var m=document.createElement("p");m.className="msg";m.textContent=t;box.appendChild(m);btn.remove();var v=box.querySelector("model-viewer");if(v)v.remove()}
})();
</script>"""


def dims_webp(f):
    b = Path(f).read_bytes()[:40]
    t = b[12:16]
    if t == b"VP8 ": return struct.unpack("<HH", b[26:30])[0] & 0x3FFF, struct.unpack("<HH", b[26:30])[1] & 0x3FFF
    if t == b"VP8L":
        v = struct.unpack("<I", b[21:25])[0]
        return (v & 0x3FFF) + 1, ((v >> 14) & 0x3FFF) + 1
    if t == b"VP8X": return int.from_bytes(b[24:27], "little") + 1, int.from_bytes(b[27:30], "little") + 1
    return 1200, 800


def licences():
    out = {}
    for l in (PHOTOS / "licences.csv").read_text(encoding="utf-8").splitlines()[1:]:
        f, a, s, lic, d = l.split(";")
        out[Path(f).stem] = {"fichier": f, "auteur": a, "source": s, "licence": lic, "date": d}
    return out


class Photos:
    """Photos de la bibliothèque libre : chaque photo posée est notée pour le registre de licences."""
    def __init__(self, h, p, illustrer):
        self.h, self.p, self.illustrer, self.lic, self.utilisees = h, p, illustrer, licences(), []

    def fig(self, cle, alt, cls="", prio=False, ph_desc="", ratio="r43", sizes=None):
        h = self.h
        if not self.illustrer or not cle:
            return (f'<div class="ph {ratio}"><b>Photo à remplacer</b><span>{h.e(ph_desc or alt)}</span>'
                    f'<small>Vos photos, avec votre accord. Ou photos libres de droits à valider ensemble.</small></div>')
        info = self.lic[cle]
        if cle not in self.utilisees: self.utilisees.append(cle)
        w, hh = dims_webp(PHOTOS / info["fichier"])
        cap = ("Photo d'illustration libre de droits (Unsplash, " + info["auteur"] + ") — à remplacer" if self.p["exemple"]
               else "Photo d'illustration — à remplacer par vos photos")
        attr = 'fetchpriority="high"' if prio else 'loading="lazy" decoding="async"'
        petit = info["fichier"].replace(".webp", "-800.webp")
        srcset = f'srcset="img/{petit} 800w, img/{info["fichier"]} 1400w" sizes="{sizes or "(min-width:900px) 50vw, 100vw"}"' if (PHOTOS / petit).exists() else ""
        return (f'<figure class="fig {cls}"><img src="img/{info["fichier"]}" {srcset} alt="{h.e(alt)}" width="{w}" height="{hh}" {attr}>'
                f'<figcaption class="cap">{h.e(cap)}</figcaption></figure>')


def horaires_html(h, ex_rows, jours):
    if ex_rows:
        rows = "".join(f'<tr><th scope="row">{h.e(j)}</th><td>{h.e(t)}</td></tr>' for j, t in ex_rows)
    else:
        rows = "".join(f'<tr><th scope="row">{h.e(j)}</th><td><mark class="todo">à compléter</mark></td></tr>' for j in jours)
    return f'<table class="hor"><caption class="skip" style="position:static;left:auto;background:none;color:inherit;padding:0;font-weight:700;text-align:left;margin-bottom:8px">Horaires d\'ouverture</caption><tbody>{rows}</tbody></table>'


def page(p, h, theme, titre, desc, ld, familles_css, bandeau, corps, js_extra="", css_extra=(), preload_hero=False):
    familles, precharge = h.THEMES[theme]
    pre = ""
    if preload_hero:
        mi = re.search(r'<img[^>]*fetchpriority="high"[^>]*>', corps)
        if mi:
            t = mi.group(0); ss = re.search(r'srcset="([^"]+)"', t); sz = re.search(r'sizes="([^"]+)"', t)
            pre = '<link rel="preload" as="image" href="' + re.search(r'src="([^"]+)"', t).group(1) + '"' + ((' imagesrcset="' + ss.group(1) + '" imagesizes="' + (sz.group(1) if sz else "100vw") + '"') if ss else "") + ' fetchpriority="high">'
    css = "".join((h.MOTEUR / f).read_text(encoding="utf-8") for f in ("base.css", "vitrine.css", *css_extra, f"themes/{theme}.css"))
    return f"""<!doctype html>
<html lang="fr" data-theme="{theme}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{h.e(titre)}</title>
<meta name="description" content="{h.e(desc)}">
<meta name="robots" content="noindex, nofollow, noarchive">
<link rel="icon" href="data:,">
<link rel="preload" href="../assets/polices/{precharge}" as="font" type="font/woff2" crossorigin>
{pre}<style>
{h.css_polices(familles)}
{css}
</style>
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
<script>document.documentElement.classList.add("js")</script>
</head>
<body>
<a class="skip" href="#contact">Aller au formulaire</a>
<div class="banner" role="note">{bandeau}</div>
{corps}
{JS_COMMUN}
{js_extra}
</body>
</html>
"""


def bandeau(h, p):
    nom = h.e(p["nom"])
    if p["exemple"]:
        return '<b>EXEMPLE</b> — établissement, numéro, carte, prix et chiffres fictifs, aucun avis réel. Maquette de démonstration LM MULTI-SERVICES.'
    return f"Maquette de démonstration préparée par LM MULTI-SERVICES pour {nom}. <b>Ce n'est pas le site officiel</b> de l'entreprise. Les zones surlignées sont à compléter."


def appels(h, aff, intl):
    if aff:
        def appel(cls="btn btn-main", txt=None):
            return f'<a class="{cls}" href="tel:{intl}">{h.ICONE_TEL}<span>{h.e(txt or "Appeler le " + aff)}</span></a>'
        return appel, f'<a class="tel-big" href="tel:{intl}">{aff}</a>'
    def appel(cls="btn btn-main", txt=None):
        return f'<a class="{cls}" href="#contact">{h.ICONE_TEL}<span>Appeler : <mark class="todo">n° à compléter</mark></span></a>'
    return appel, '<a class="tel-big" href="#contact"><mark class="todo">n° à compléter</mark></a>'


# --- restaurant -------------------------------------------------------------------------------------
def restaurant(p, met, h):
    if p["direction"] == "marche":
        import modeles2
        return modeles2.marche(p, met, h)
    ex, theme = p["exemple"], p["direction"]
    nom, ville = p["nom"], p["ville"]
    aff, intl = h.tel_norm(p.get("telephone"))
    appel, tel_big = appels(h, aff, intl)
    tel_lien = f'<a href="tel:{intl}">{aff}</a>' if aff else '<mark class="todo">n° à compléter</mark>'
    D = met["exemple"] if ex else None
    ph = Photos(h, p, ex or p.get("illustrations"))
    cles = met["photos"].get(theme, met["photos"]["bistro"])
    badge = '<span class="badge-ex">exemple</span>' if ex else ""
    note, avis = h.nombre(p.get("note")), h.nombre(p.get("avis"))
    preuve = ""
    if note and avis:
        preuve = f'<p class="pill"><span class="star" aria-hidden="true">★</span> {note:.1f}'.replace(".", ",") + f' / 5 · {int(avis)} avis Google{badge}</p>'
    plein = theme == "bistro"
    hero_fig = ph.fig(cles["hero"], f"Salle du restaurant {nom} à {ville}" if ex else "Photo d'illustration du restaurant", prio=True, ph_desc=met["photo_hero_desc"], ratio="r45")
    promesse = met["promesse_exemple"] if ex else met["promesse"]
    cuisine = D["cuisine"] if D else ""
    h1 = f'{h.e(nom)}' if ex else f'Restaurant à <em>{h.e(ville)}</em>'
    if ex: h1 = f'{h.e(nom)}<br><em>{h.e(ville)}</em>'
    cta = f'<div class="cta"><a class="btn btn-main" href="#reserver"><span>Réserver une table</span></a>{appel("btn btn-line", "Appeler")}</div>'
    hero_txt = f'<p class="eyebrow">Restaurant · {h.e(ville)}{(" · " + h.e(cuisine)) if cuisine else ""}{badge}</p><h1>{h1}</h1><p class="lead">{h.fm(promesse)}</p>{cta}{preuve}'
    if plein: hero = f'<section class="vhero plein">{hero_fig}<div class="w"><div>{hero_txt}</div></div></section>'
    else: hero = f'<section class="vhero split"><div class="w"><div>{hero_txt}</div>{hero_fig}</div></section>'

    adresse = h.e(D["adresse"]) if D else '<mark class="todo">adresse à compléter</mark>'
    infos = (f'<section class="infos" aria-label="Infos pratiques"><div class="w">'
             f'<div class="c"><b>Adresse</b>{adresse}</div>'
             f'<div class="c"><b>Aujourd\'hui</b>{"Horaires ci-dessous" if D else "<mark class=todo>horaires à compléter</mark>"}</div>'
             f'<div class="c"><b>Téléphone</b>{tel_lien}</div></div></section>')

    carte = D["carte"] if D else None
    chips = "".join(f'<a href="#cat-{i}">{h.e(c["cat"] if D else c["cat"])}</a>' for i, c in enumerate(carte or met["carte_vide"]))
    blocs = ""
    if D:
        for i, c in enumerate(D["carte"]):
            li = "".join(f'<li><div class="pl-h"><span class="pl-n">{h.e(x["n"])}</span><span class="pl-l"></span><span class="pl-p">{h.e(x["p"])}</span></div><p>{h.e(x["d"])}</p></li>' for x in c["plats"])
            blocs += f'<section class="cat rv" id="cat-{i}"><h3>{h.e(c["cat"])}</h3><ul class="plats">{li}</ul></section>'
    else:
        for i, c in enumerate(met["carte_vide"]):
            li = "".join(f'<li><div class="pl-h"><span class="pl-n"><mark class="todo">{h.e(l)}</mark></span></div></li>' for l in c["lignes"])
            blocs += f'<section class="cat rv" id="cat-{i}"><h3>{h.e(c["cat"])}</h3><ul class="plats">{li}</ul></section>'
    formule = f'<p class="formule">{h.e(D["formule"])}</p>' if D else ""
    legal = ('<p class="note-legale">Prix en euros TTC' + (" (exemple fictif)" if ex else "") +
             '. Information allergènes : <mark class="todo">à compléter par le restaurateur</mark>.</p>')
    carte_html = (f'<section class="section" id="carte"><div class="w"><p class="eyebrow rv">La carte{badge}</p><h2 class="rv">Ce qu\'on mange ici</h2>'
                  f'<nav class="chips" aria-label="Catégories de la carte">{chips}</nav>{blocs}{formule}{legal}</div></section>')
    strip = (f'<section class="section alt" aria-label="Ambiance"><div class="w strip">'
             f'{ph.fig(cles.get("p1"), "Un plat de la carte", ph_desc="Plat signature, vu de dessus, lumière douce", ratio="r43")}'
             f'{ph.fig(cles.get("p2"), "Un autre plat de la carte", ph_desc="Seconde photo : salle, équipe ou plat", ratio="r43")}</div></section>')
    hor = horaires_html(h, D["horaires"] if D else None, met["horaires_jours"])
    acces = (f'<div><p class="eyebrow rv">Horaires{badge}</p><h2 class="rv">Quand venir</h2>{hor}</div>'
             f'<div><p class="eyebrow rv">Accès</p><h2 class="rv">Nous trouver</h2><p class="rv">{adresse}</p>'
             f'<p class="rv" style="margin-top:12px">Parking, transports, accès PMR : <mark class="todo">à compléter</mark></p></div>')
    avis_html = ('<section class="section alt" id="avis"><div class="w"><p class="eyebrow rv">Avis</p><h2 class="rv">Ce qu\'en disent les clients</h2>'
                 '<div class="grid-a">' + "".join('<div class="avis-c rv"><b>Avis Google à insérer</b>Nom, note, date et texte réels de la fiche Google, repris avec l\'accord du restaurateur. Aucun avis n\'est inventé.</div>' for _ in range(3)) +
                 '</div></div></section>')
    resa = (f'<section class="section contact" id="reserver"><div class="w"><div><p class="eyebrow">Réservation</p><h2>Réserver une table</h2>'
            f'<p class="lead">Quatre informations et on vous confirme par téléphone sous <mark class="todo">délai à confirmer</mark>. Pour un groupe, appelez.</p>{tel_big}</div>'
            f'<form class="f" action="#reserver" method="post" id="devis">'
            f'<label for="f-nom">Votre nom<input id="f-nom" name="nom" autocomplete="name" required></label>'
            f'<label for="f-tel">Votre téléphone<input id="f-tel" name="tel" type="tel" autocomplete="tel" inputmode="tel" required></label>'
            f'<label for="f-date">Date et heure<input id="f-date" name="date" type="datetime-local" required></label>'
            f'<label for="f-nb">Nombre de personnes<select id="f-nb" name="couverts">{"".join(f"<option>{i}</option>" for i in range(1, 11))}<option>Plus de 10 : appelez</option></select></label>'
            f'<button class="btn btn-main" type="submit">Demander ma réservation</button>'
            f'<p class="note">Votre numéro sert uniquement à confirmer la réservation.</p>'
            f'<p class="ok" role="status">Maquette : l\'envoi est désactivé. {"Pour réserver, appelez le " + aff + "." if aff else ""}</p></form></div></section>')
    sect_contact = f'<a id="contact"></a>'
    top = (f'<header class="top"><div class="w"><a class="brand" href="#top">{h.e(nom)}</a>'
           f'<nav class="nav" aria-label="Sections"><a href="#carte">Carte</a><a href="#horaires">Horaires</a><a href="#avis">Avis</a><a href="#reserver">Réserver</a></nav>'
           f'<a class="btn btn-main" href="#reserver"><span>Réserver</span></a></div></header>')
    horaires_sec = f'<section class="section" id="horaires"><div class="w cols2">{acces}</div></section>'
    lien_pied = appel("", aff or "Appeler").replace('class=""', 'class="fl"')
    foot = (f'<footer><div class="w"><p><strong>{h.e(nom)}</strong> — restaurant à {h.e(ville)} · {lien_pied}</p>'
            f'<p>SIRET <mark class="todo">à compléter</mark> · Médiateur de la consommation <mark class="todo">à compléter</mark> · Mentions légales <mark class="todo">à compléter</mark></p>'
            f'<p>Maquette réalisée par LM MULTI-SERVICES. Page privée, non référencée.</p></div></footer>')
    bar = f'<div class="bar"><a class="btn btn-main" href="#reserver"><span>Réserver</span></a>{appel("btn btn-line", "Appeler")}</div>'
    corps = f'{top}<main id="top">{hero}{infos}{carte_html}{strip}{horaires_sec}{avis_html}{resa}</main>{sect_contact}{foot}{bar}'
    titre = f"{nom} — restaurant à {ville}"
    desc = f"Restaurant à {ville} : carte, horaires, réservation en ligne" + (f" ou par téléphone au {aff}." if aff else ".")
    ld = {"@context": "https://schema.org", "@type": "Restaurant", "name": nom, "description": desc,
          "address": {"@type": "PostalAddress", "addressLocality": ville, "addressCountry": "FR"}, "acceptsReservations": True}
    if intl: ld["telephone"] = intl
    if note and avis and not ex: ld["aggregateRating"] = {"@type": "AggregateRating", "ratingValue": note, "reviewCount": int(avis)}
    p["_photos_utilisees"] = ph.utilisees
    p["_licences"] = ph.lic
    return page(p, h, theme, titre, desc, ld, None, bandeau(h, p), corps)


# --- commerce -----------------------------------------------------------------------------------------
def commerce(p, met, h):
    ex, theme = p["exemple"], p["direction"]
    nom, ville = p["nom"], p["ville"]
    aff, intl = h.tel_norm(p.get("telephone"))
    appel, tel_big = appels(h, aff, intl)
    tel_lien = f'<a href="tel:{intl}">{aff}</a>' if aff else '<mark class="todo">n° à compléter</mark>'
    D = met["exemple"] if ex else None
    ph = Photos(h, p, ex or p.get("illustrations"))
    cles = met["photos"]["atelier"]
    badge = '<span class="badge-ex">exemple</span>' if ex else ""
    type_txt = D["type"] if D else "Boutique"
    h1base = D["h1"] if D else "Boutique"
    h1 = f'{h.e(h1base)} à <em>{h.e(ville)}</em>'
    promesse = met["promesse_exemple"] if ex else met["promesse"]
    hero_fig = ph.fig(cles["hero"], f"Produits de la boutique {nom}" if ex else "Photo d'illustration de la boutique", prio=True, ph_desc=met["photo_hero_desc"], ratio="r11")
    cta = f'<div class="cta">{appel()}<a class="btn btn-line" href="#produits"><span>Voir les produits</span></a></div>'
    hero = (f'<section class="vhero split"><div class="w"><div><p class="eyebrow">{h.e(nom)}{badge}</p><h1>{h1}</h1>'
            f'<p class="lead">{h.fm(promesse)}</p>{cta}</div>{hero_fig}</div></section>')
    adresse = h.e(D["adresse"]) if D else '<mark class="todo">adresse à compléter</mark>'
    infos = (f'<section class="infos" aria-label="Infos pratiques"><div class="w">'
             f'<div class="c"><b>Adresse</b>{adresse}</div>'
             f'<div class="c"><b>Horaires</b>{"Voir ci-dessous" if D else "<mark class=todo>horaires à compléter</mark>"}</div>'
             f'<div class="c"><b>Téléphone</b>{tel_lien}</div></div></section>')
    if D:
        cards = "".join(f'<article class="prod rv">{ph.fig(cles[x["photo"]], x["n"] + " — " + x["d"], ratio="r11")}<h3>{h.e(x["n"])}</h3><p>{h.e(x["d"])}</p><p class="prix">{h.e(x["p"])}{badge}</p></article>' for x in D["produits"])
    else:
        cards = "".join(f'<article class="prod rv">{ph.fig(None, "Photo du produit", ph_desc=l, ratio="r11")}<h3><mark class="todo">{h.e(l.split(" — ")[0])}</mark></h3><p><mark class="todo">description et prix à compléter</mark></p></article>' for l in met["produits_vides"])
    produits = (f'<section class="section" id="produits"><div class="w"><p class="eyebrow rv">La boutique{badge}</p><h2 class="rv">Nos produits</h2>'
                f'<div class="grid-p">{cards}</div><p class="note-legale">Prix en euros TTC{" (exemple fictif)" if ex else ""}. Disponibilité confirmée par la boutique.</p></div></section>')
    if ex:
        v3d = ('<section class="section alt" id="vitrine"><div class="w"><p class="eyebrow rv">Vitrine 3D · option</p><h2 class="rv">Tournez le vase</h2>'
               '<div class="v3d" data-lib="../assets/3d/model-viewer.min.js" data-src="../assets/3d/ceramic_vase_02_1k.gltf" data-poster="img/vase-poster.webp" data-alt="Vase en céramique, modèle 3D à faire tourner">'
               '<img src="img/vase-poster.webp" alt="Vase en céramique (image fixe, le modèle 3D se charge au clic)" width="1000" height="800" loading="lazy">'
               '<button class="btn btn-main" id="v3d-go" type="button"><span>Voir en 3D</span></button></div>'
               '<p class="note-legale">Option facultative : le modèle 3D (≈ 1,7 Mo) ne se charge qu\'au clic. Sans 3D, l\'image fixe reste affichée. Modèle libre CC0 (Poly Haven, James Ray Cock), exemple.</p></div></section>')
    else:
        v3d = ('<section class="section alt" id="vitrine"><div class="w"><p class="eyebrow rv">Vitrine 3D · option</p><h2 class="rv">Un produit en 3D</h2>'
               '<div class="ph r32"><b>Option 3D — à définir ensemble</b><span>Un de vos produits phares en 3D, chargé seulement au clic, avec une photo de repli.</span></div></div></section>')
    raisons = "".join(f'<div class="why rv"><div class="big">{i}</div><h3>{h.fm(r["t"])}</h3><p>{h.fm(r["d"])}</p></div>' for i, r in enumerate(met["raisons"], 1))
    pourquoi = f'<section class="section" id="pourquoi"><div class="w"><p class="eyebrow rv">Pourquoi venir</p><h2 class="rv">Trois raisons</h2><div class="grid-w">{raisons}</div></div></section>'
    hor = horaires_html(h, D["horaires"] if D else None, met["horaires_jours"])
    horaires_sec = (f'<section class="section alt" id="horaires"><div class="w cols2"><div><p class="eyebrow rv">Horaires{badge}</p><h2 class="rv">Quand venir</h2>{hor}</div>'
                    f'<div><p class="eyebrow rv">Accès</p><h2 class="rv">Nous trouver</h2><p class="rv">{adresse}</p>'
                    f'<p class="rv" style="margin-top:12px">Parking, transports, accès PMR : <mark class="todo">à compléter</mark></p></div></div></section>')
    faq = "".join(f'<details class="rv"><summary>{h.fm(q["q"])}</summary><p>{h.fm(q["a"])}</p></details>' for q in met["faq"])
    faq_sec = f'<section class="section" id="faq"><div class="w"><p class="eyebrow rv">Questions</p><h2 class="rv">Vos questions</h2><div class="faq">{faq}</div></div></section>'
    options = "".join(f"<option>{h.e(o)}</option>" for o in met["besoins"])
    contact = (f'<section class="section contact" id="contact"><div class="w"><div><p class="eyebrow">Contact</p><h2>Une question, un produit ?</h2>'
               f'<p class="lead">Appelez, ou laissez 4 informations : la boutique vous répond sous <mark class="todo">délai à confirmer</mark>.</p>{tel_big}</div>'
               f'<form class="f" action="#contact" method="post" id="devis">'
               f'<label for="f-nom">Votre nom<input id="f-nom" name="nom" autocomplete="name" required></label>'
               f'<label for="f-tel">Votre téléphone<input id="f-tel" name="tel" type="tel" autocomplete="tel" inputmode="tel" required></label>'
               f'<label for="f-besoin">Votre demande<select id="f-besoin" name="besoin">{options}</select></label>'
               f'<label for="f-msg">Produit concerné<input id="f-msg" name="produit"></label>'
               f'<button class="btn btn-main" type="submit">Envoyer ma demande</button>'
               f'<p class="note">Votre numéro sert uniquement à vous répondre.</p>'
               f'<p class="ok" role="status">Maquette : l\'envoi est désactivé. {"Pour joindre la boutique, appelez le " + aff + "." if aff else ""}</p></form></div></section>')
    top = (f'<header class="top"><div class="w"><a class="brand" href="#top">{h.e(nom)}</a>'
           f'<nav class="nav" aria-label="Sections"><a href="#produits">Produits</a><a href="#horaires">Horaires</a><a href="#faq">Questions</a><a href="#contact">Contact</a></nav>'
           f'{appel("btn btn-main", aff or "Appeler")}</div></header>')
    lien_pied = appel("", aff or "Appeler").replace('class=""', 'class="fl"')
    foot = (f'<footer><div class="w"><p><strong>{h.e(nom)}</strong> — {h.e(type_txt.lower())} à {h.e(ville)} · {lien_pied}</p>'
            f'<p>SIRET <mark class="todo">à compléter</mark> · Médiateur de la consommation <mark class="todo">à compléter</mark> · Mentions légales et CGV <mark class="todo">à compléter</mark></p>'
            f'<p>Maquette réalisée par LM MULTI-SERVICES. Page privée, non référencée.</p></div></footer>')
    bar = f'<div class="bar">{appel("btn btn-main", "Appeler")}<a class="btn btn-line" href="#contact"><span>Contact</span></a></div>'
    corps = f'{top}<main id="top">{hero}{infos}{produits}{v3d}{pourquoi}{horaires_sec}{faq_sec}{contact}</main>{foot}{bar}'
    titre = f"{h1base} à {ville} — {nom}"
    desc = f"{h1base} à {ville} : produits, horaires, accès" + (f" et contact au {aff}." if aff else ".")
    ld = {"@context": "https://schema.org", "@type": "Store", "name": nom, "description": desc,
          "address": {"@type": "PostalAddress", "addressLocality": ville, "addressCountry": "FR"}}
    if intl: ld["telephone"] = intl
    p["_photos_utilisees"] = ph.utilisees
    p["_licences"] = ph.lic
    p["_h1base"] = h1base
    return page(p, h, theme, titre, desc, ld, None, bandeau(h, p), corps, JS_3D if ex else "")
