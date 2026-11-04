"""Modèles restaurant « marché » (version améliorée) et groupe de restaurants « maison ». Appelés via modeles.py / generer.py."""
import json
from pathlib import Path
import modeles as M

DOSSIER = Path(__file__).resolve().parent
JS_FORMS = """<script>
(function(){
  document.querySelectorAll("form.f").forEach(function(f){if(f.id!=="devis")f.addEventListener("submit",function(ev){ev.preventDefault();f.classList.add("sent")})});
})();
</script>"""
JS_GROUPE = """<script>
(function(){
  var s=document.querySelectorAll(".gh-hero .slide"),pts=document.querySelectorAll(".gh-hero .pts i"),leg=document.getElementById("leg");
  document.addEventListener("click",function(e){document.querySelectorAll("details.dd[open]").forEach(function(d){if(!d.contains(e.target))d.removeAttribute("open")})});
  document.querySelectorAll(".dd-panel a").forEach(function(a){a.addEventListener("click",function(){var d=a.closest("details");if(d)d.removeAttribute("open")})});
  if(s.length<2)return;
  function charge(){s.forEach(function(i){if(i.dataset.src){i.srcset=i.dataset.srcset||"";i.src=i.dataset.src;delete i.dataset.src}})}
  if(document.readyState==="complete")charge();else window.addEventListener("load",charge);
  if(window.matchMedia("(prefers-reduced-motion: reduce)").matches)return;
  var n=0;setInterval(function(){s[n].classList.remove("on");pts[n]&&pts[n].classList.remove("on");n=(n+1)%s.length;s[n].classList.add("on");pts[n]&&pts[n].classList.add("on");if(leg)leg.textContent=s[n].dataset.leg||""},6500);
})();
</script>"""
GIF = "data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=="


def carte_html(p, met, h, D, badge):
    chips = "".join(f'<a href="#cat-{i}">{h.e(c["cat"])}</a>' for i, c in enumerate(D["carte"] if D else met["carte_vide"]))
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
    legal = ('<p class="note-legale">Prix en euros TTC' + (" (exemple fictif)" if p["exemple"] else "") + '. Information allergènes : <mark class="todo">à compléter par le restaurateur</mark>.</p>')
    return (f'<section class="section" id="carte"><div class="w"><p class="eyebrow rv">La carte{badge}</p><h2 class="rv">Ce qu\'on mange ici</h2>'
            f'<nav class="chips" aria-label="Catégories de la carte">{chips}</nav>{blocs}{formule}{legal}</div></section>')


def fig_plein(ph, cle, alt, desc, ratio="r45", prio=False, sizes=None):
    f = ph.fig(cle, alt, prio=prio, ph_desc=desc, ratio=ratio, sizes=sizes)
    return f if f.startswith("<figure") else f'<div class="fig">{f}</div>'


def form_evt(h, types, aff, clair=True):
    opts = "".join(f"<option>{h.e(t)}</option>" for t in types)
    return (f'<form class="f{" clair" if clair else ""}" action="#devis-evenement" method="post" id="evt">'
            f'<label for="e-nom">Votre nom<input id="e-nom" name="nom" autocomplete="name" required></label>'
            f'<label for="e-tel">Votre téléphone<input id="e-tel" name="tel" type="tel" autocomplete="tel" inputmode="tel" required></label>'
            f'<label for="e-type">Type d\'événement<select id="e-type" name="type">{opts}</select></label>'
            f'<label for="e-nb">Nombre de personnes<input id="e-nb" name="personnes" type="number" min="1" inputmode="numeric"></label>'
            f'<button class="btn btn-main" type="submit">Demander un devis</button>'
            f'<p class="note">Vous recevez une réponse sous <mark class="todo">délai à confirmer</mark>. Votre numéro sert uniquement à vous rappeler.</p>'
            f'<p class="ok" role="status">Maquette : l\'envoi est désactivé. {"Pour un devis, appelez le " + aff + "." if aff else ""}</p></form>')


# --- restaurant « marché » : hero immersif, histoire, événements, Réservations fixe ------------------------
def marche(p, met, h):
    R = json.loads((DOSSIER / "metiers" / "restaurant-marche.json").read_text(encoding="utf-8"))
    ex, theme = p["exemple"], "marche"
    nom, ville = p["nom"], p["ville"]
    aff, intl = h.tel_norm(p.get("telephone"))
    appel, tel_big = M.appels(h, aff, intl)
    tel_lien = f'<a href="tel:{intl}">{aff}</a>' if aff else '<mark class="todo">n° à compléter</mark>'
    D = met["exemple"] if ex else None
    ph = M.Photos(h, p, ex or p.get("illustrations"))
    badge = '<span class="badge-ex">exemple</span>' if ex else ""
    note, avis = h.nombre(p.get("note")), h.nombre(p.get("avis"))
    preuve = ""
    if note and avis:
        preuve = f'<p class="pill"><span class="star" aria-hidden="true">★</span> {note:.1f}'.replace(".", ",") + f' / 5 · {int(avis)} avis Google{badge}</p>'
    cuisine = D["cuisine"] if D else ""
    h1 = f'{h.e(R["h1_exemple"] if ex else R["h1_reel"])} <em>{h.e(ville)}</em>'
    hero_fig = fig_plein(ph, R["photos"]["hero"], f"Terrasse du restaurant {nom}" if ex else "Photo d'illustration du restaurant", met["photo_hero_desc"], prio=True, sizes="100vw")
    cta = f'<div class="cta"><a class="btn btn-main" href="#reserver"><span>Réserver une table</span></a>{appel("btn btn-line", "Appeler")}</div>'
    ambiance = f'<p class="ambiance">{h.e(R["ambiance"])}{" " + badge if ex else ""}</p>' if ex else '<p class="ambiance"><mark class="todo">Votre phrase d\'ambiance, courte et vraie</mark></p>'
    hero = (f'<section class="vhero plein">{hero_fig}<div class="w"><div><p class="eyebrow" style="color:#f3e6c4">{h.e(nom)} · {h.e(ville)}{(" · " + h.e(cuisine)) if cuisine else ""}{badge}</p>'
            f'<h1>{h1}</h1>{ambiance}{cta}{preuve}</div></div></section>')
    adresse = h.e(D["adresse"]) if D else '<mark class="todo">adresse à compléter</mark>'
    infos = (f'<section class="infos" aria-label="Infos pratiques"><div class="w"><div class="c"><b>Adresse</b>{adresse}</div>'
             f'<div class="c"><b>Aujourd\'hui</b>{"Horaires ci-dessous" if D else "<mark class=todo>horaires à compléter</mark>"}</div>'
             f'<div class="c"><b>Téléphone</b>{tel_lien}</div></div></section>')
    texte_h = "".join(f"<p>{h.fm(t)}</p>" for t in R["histoire_exemple"]) if ex else f'<p>{h.fm(R["histoire_reel"])}</p>'
    histoire = (f'<section class="section" id="histoire"><div class="w hist"><div class="rv"><p class="eyebrow">Le lieu{badge}</p><h2>Une maison, une histoire</h2>{texte_h}</div>'
                f'{fig_plein(ph, R["photos"]["histoire"], "Table dressée avec des fleurs de saison", "Le lieu, la salle ou l’équipe : une photo vraie du restaurant", ratio="r43")}</div></section>')
    carte = carte_html(p, met, h, D, badge)
    formats = "".join(f'<div class="rv"><h3>{h.e(f["t"])}</h3><p>{h.e(f["d"])} <mark class="todo">capacité à compléter</mark></p></div>' for f in R["evenements"])
    evt = (f'<section class="section alt" id="evenements"><div class="w evt"><div>{fig_plein(ph, R["photos"]["evt"], "Grande table dressée pour un repas de groupe", "Salle prête pour un événement, table dressée", ratio="r45")}</div>'
           f'<div><p class="eyebrow rv">Événements et privatisations{badge}</p><h2 class="rv">Réunir vos proches, vos équipes</h2><div class="formats">{formats}</div>'
           f'<p style="margin-top:var(--s3)"><a class="btn btn-main" href="#devis-evenement"><span>Demander un devis</span></a></p></div></div>'
           f'<div class="w"><div class="devis-box" id="devis-evenement"><h3 style="margin-bottom:var(--s2)">Votre événement en quatre informations</h3>{form_evt(h, R["types_evenement"], aff)}</div></div></section>')
    hor = M.horaires_html(h, D["horaires"] if D else None, met["horaires_jours"])
    acces = (f'<section class="section" id="horaires"><div class="w cols2"><div><p class="eyebrow rv">Horaires{badge}</p><h2 class="rv">Quand venir</h2>{hor}</div>'
             f'<div><p class="eyebrow rv">Accès</p><h2 class="rv">Nous trouver</h2><p class="rv">{adresse}</p><p class="rv" style="margin-top:12px">Parking, transports, accès PMR : <mark class="todo">à compléter</mark></p></div></div></section>')
    avis_html = ('<section class="section alt" id="avis"><div class="w"><p class="eyebrow rv">Avis</p><h2 class="rv">Ce qu\'en disent les clients</h2><div class="grid-a">'
                 + "".join('<div class="avis-c rv"><b>Avis Google à insérer</b>Nom, note, date et texte réels de la fiche Google, repris avec l\'accord du restaurateur. Aucun avis n\'est inventé.</div>' for _ in range(3)) + '</div></div></section>')
    resa = (f'<section class="section contact" id="reserver"><div class="w"><div><p class="eyebrow">Réservations</p><h2>Réserver une table</h2>'
            f'<p class="lead">Quatre informations et on vous confirme par téléphone sous <mark class="todo">délai à confirmer</mark>. Pour un groupe, appelez.</p>{tel_big}</div>'
            f'<form class="f" action="#reserver" method="post" id="devis">'
            f'<label for="f-nom">Votre nom<input id="f-nom" name="nom" autocomplete="name" required></label>'
            f'<label for="f-tel">Votre téléphone<input id="f-tel" name="tel" type="tel" autocomplete="tel" inputmode="tel" required></label>'
            f'<label for="f-date">Date et heure<input id="f-date" name="date" type="datetime-local" required></label>'
            f'<label for="f-nb">Nombre de personnes<select id="f-nb" name="couverts">{"".join(f"<option>{i}</option>" for i in range(1, 11))}<option>Plus de 10 : appelez</option></select></label>'
            f'<button class="btn btn-main" type="submit">Demander ma réservation</button><p class="note">Votre numéro sert uniquement à confirmer la réservation.</p>'
            f'<p class="ok" role="status">Maquette : l\'envoi est désactivé. {"Pour réserver, appelez le " + aff + "." if aff else ""}</p></form></div></section>')
    top = (f'<header class="top"><div class="w"><a class="brand" href="#top">{h.e(nom)}</a>'
           f'<nav class="nav" aria-label="Sections"><a href="#histoire">Le lieu</a><a href="#carte">Carte</a><a href="#evenements">Événements</a><a href="#horaires">Horaires</a></nav>'
           f'<a class="btn btn-main" href="#reserver"><span>Réservations</span></a></div></header>')
    lien_pied = appel("", aff or "Appeler").replace('class=""', 'class="fl"')
    foot = (f'<footer id="contact"><div class="w"><p><strong>{h.e(nom)}</strong> — restaurant à {h.e(ville)} · {lien_pied}</p>'
            f'<p>SIRET <mark class="todo">à compléter</mark> · Médiateur de la consommation <mark class="todo">à compléter</mark> · Mentions légales <mark class="todo">à compléter</mark></p>'
            f'<p>Maquette réalisée par LM MULTI-SERVICES. Page privée, non référencée.</p></div></footer>')
    bar = f'<div class="bar"><a class="btn btn-main" href="#reserver"><span>Réservations</span></a>{appel("btn btn-line", "Appeler")}</div>'
    corps = f'{top}<main id="top">{hero}{infos}{histoire}{carte}{evt}{acces}{avis_html}{resa}</main>{foot}{bar}'
    titre = f"{nom} — restaurant à {ville}"
    desc = f"Restaurant à {ville} : histoire du lieu, carte, événements, réservation en ligne" + (f" ou par téléphone au {aff}." if aff else ".")
    ld = {"@context": "https://schema.org", "@type": "Restaurant", "name": nom, "description": desc,
          "address": {"@type": "PostalAddress", "addressLocality": ville, "addressCountry": "FR"}, "acceptsReservations": True}
    if intl: ld["telephone"] = intl
    if note and avis and not ex: ld["aggregateRating"] = {"@type": "AggregateRating", "ratingValue": note, "reviewCount": int(avis)}
    p["_photos_utilisees"], p["_licences"] = ph.utilisees, ph.lic
    return M.page(p, h, theme, titre, desc, ld, None, M.bandeau(h, p), corps, JS_FORMS, preload_hero=True)


# --- groupe de restaurants « maison » -----------------------------------------------------------------
def groupe(p, met, h):
    G = met
    ex, theme = p["exemple"], "maison"
    nom, ville = p["nom"], p["ville"]
    aff, intl = h.tel_norm(p.get("telephone"))
    D = G["exemple"] if ex else None
    appel, tel_big = M.appels(h, aff, intl)
    ph = M.Photos(h, p, ex or p.get("illustrations"))
    badge = '<span class="badge-ex">exemple</span>' if ex else ""
    maisons = D["maisons"] if D else [{"id": f"m{i}", "nom": m["nom"], "ville": "", "ambiance": "", "photo": None, "tel": "", "adresse": "", "horaires": "", "plats": [], "_note": m["note"]} for i, m in enumerate(G["maisons_vides"], 1)]
    phs = G["photos"]

    def tel_m(m):
        a, i = h.tel_norm(m["tel"]) if m.get("tel") else (None, None)
        return a, i
    # en-tête fixe : menu, nom du groupe, Réservations (liste des maisons avec téléphone)
    menu = "".join(f'<a href="#{x}">{t}</a>' for x, t in (("maisons", "Nos maisons"), ("cartes", "Les cartes"), ("evenements", "Événements"), ("histoire", "Notre histoire"), ("fidelite", "Fidélité"), ("recrutement", "Nous rejoindre"), ("contact", "Contact")))
    lignes_resa = ""
    for m in maisons:
        a, i = tel_m(m)
        lt = f'<a href="tel:{i}">{a}</a>' if a else '<mark class="todo">n° à compléter</mark>'
        lignes_resa += f'<li><span class="nm">{h.e(m["nom"])}{(" · " + h.e(m["ville"])) if m["ville"] else ""}</span><span class="lien">{lt}<a href="#reserver">Réserver en ligne</a></span></li>'
    header = (f'<header class="gh"><div class="gh-in"><details class="dd dd-menu"><summary aria-label="Menu"><span class="burger" aria-hidden="true"></span><span class="gh-lbl">Nos maisons</span></summary>'
              f'<nav class="dd-panel" aria-label="Sections">{menu}</nav></details>'
              f'<a class="gh-brand" href="#top">{h.e(nom)}</a>'
              f'<details class="dd dd-resa"><summary>Réservations</summary><div class="dd-panel dd-right"><ul>{lignes_resa}</ul></div></details></div></header>')
    # hero immersif : 3 vues en fondu, phrase d'ambiance
    slides_def = [(phs["hero"], f"Salle à manger du groupe {nom}", f"{nom} · salle"),
                  (phs["slide2"], "Grande salle chaleureuse", (maisons[0]["nom"] + " · " + maisons[0]["ville"]) if D else "Maison 1"),
                  (phs["slide3"], "Terrasse ombragée", (maisons[1]["nom"] + " · " + maisons[1]["ville"]) if D else "Maison 2")]
    if ex or p.get("illustrations"):
        sl = ""
        for k, (cle, alt, leg) in enumerate(slides_def):
            info = ph.lic[cle]
            if cle not in ph.utilisees: ph.utilisees.append(cle)
            w, hh = M.dims_webp(M.PHOTOS / info["fichier"])
            petit = info["fichier"].replace(".webp", "-800.webp")
            ss = f'img/{petit} 800w, img/{info["fichier"]} 1400w'
            if k == 0: sl += f'<img class="slide on" src="img/{info["fichier"]}" srcset="{ss}" sizes="100vw" alt="{h.e(alt)}" width="{w}" height="{hh}" fetchpriority="high" data-leg="{h.e(leg)}">'
            else: sl += f'<img class="slide" src="{GIF}" data-src="img/{info["fichier"]}" data-srcset="{ss}" sizes="100vw" alt="{h.e(alt)}" width="{w}" height="{hh}" data-leg="{h.e(leg)}">'
        leg0 = slides_def[0][2]
    else:
        sl = '<div class="ph" style="position:absolute;inset:0;min-height:0;border:0"><b>Photo à remplacer</b><span>Vue d\'ensemble du groupe : la plus belle salle ou terrasse, lumière du soir</span></div>'
        leg0 = "Photo à remplacer"
    sub = (f"{len(maisons)} maisons à " + ", ".join(sorted({m["ville"] for m in maisons})) + ". Une même exigence : bien recevoir.") if D else "[[Votre groupe en une phrase : nombre de maisons, villes, esprit]]"
    hero = (f'<section class="gh-hero" id="top">{sl}<div class="w"><p class="eyebrow" style="color:var(--gold)">{h.e(nom)}{badge}</p>'
            f'<h1>Des tables où l\'on prend <em>le temps</em> de recevoir</h1><p class="sub">{h.fm(sub)}</p>'
            f'<div class="cta"><a class="btn btn-main" href="#reserver"><span>Réservations</span></a><a class="btn btn-line" href="#maisons"><span>Découvrir les maisons</span></a></div>'
            f'<div class="legende"><span id="leg">{h.e(leg0)}</span><span class="pts" aria-hidden="true"><i class="on"></i><i></i><i></i></span></div></div></section>')
    # une carte par maison
    tuiles = ""
    for m in maisons:
        a, i = tel_m(m)
        fig = ph.fig(m["photo"], f'{m["nom"]} à {m["ville"]}' if m["ville"] else "Photo de la maison", ratio="r45", ph_desc=f'Photo de {m["nom"]} : salle, terrasse ou plat signature')
        lt = f'<a href="tel:{i}">Appeler</a>' if a else '<a href="#contact">Appeler</a>'
        nm = h.e(m["nom"]) if D else f'{h.e(m["nom"])} <mark class="todo">nom à compléter</mark>'
        vil = f'<p class="ville">{h.e(m["ville"])}</p>' if m["ville"] else '<p class="ville"><mark class="todo">ville</mark></p>'
        amb = f'<p>{h.e(m["ambiance"])}</p>' if m["ambiance"] else f'<p><mark class="todo">{h.e(m["_note"])}</mark></p>'
        tuiles += (f'<article class="maison rv">{fig}<div class="txt"><h3>{nm}</h3>{vil}{amb}'
                   f'<div class="liens"><a href="#m-{m["id"]}">Découvrir</a><a href="#reserver">Réserver</a>{lt}</div></div></article>')
    maisons_sec = f'<section class="section" id="maisons"><div class="w"><p class="eyebrow rv">Nos maisons{badge}</p><h2 class="rv">Des lieux qui ont une âme</h2><div class="maisons">{tuiles}</div></div></section>'
    photos_plats = ["resto1-saumon", "resto1-assiette", "resto2-plat", "resto1-saumon"]
    fiches = ""
    for k, m in enumerate(maisons):
        a, i = tel_m(m)
        if D:
            li = "".join(f'<li><div class="pl-h"><span class="pl-n">{h.e(x["n"])}</span><span class="pl-l"></span><span class="pl-p">{h.e(x["p"])}</span></div><p>{h.e(x["d"])}</p></li>' for x in m["plats"])
            meta = (f'<div class="meta"><span><b>Adresse</b> · {h.e(m["adresse"])}</span><span><b>Horaires</b> · {h.e(m["horaires"])}</span><span><b>Téléphone</b> · <a href="tel:{i}">{a}</a></span></div>')
        else:
            li = '<li><div class="pl-h"><span class="pl-n"><mark class="todo">3 plats phares avec prix</mark></span></div></li>'
            meta = '<div class="meta"><span><b>Adresse</b> · <mark class="todo">à compléter</mark></span><span><b>Horaires</b> · <mark class="todo">à compléter</mark></span><span><b>Téléphone</b> · <mark class="todo">à compléter</mark></span></div>'
        cta_t = f'<a class="btn btn-line" href="tel:{i}"><span>Appeler</span></a>' if a else ''
        fig = ph.fig(photos_plats[k % 4] if D else None, f'Un plat de {m["nom"]}', ratio="r43", ph_desc="Plat signature de la maison")
        fiches += (f'<details name="maisons" id="m-{m["id"]}"{" open" if k == 0 else ""}><summary><span>{h.e(m["nom"])}<small>{h.e(m["ville"])}</small></span></summary>'
                   f'<div class="fiche"><div>{fig}</div><div><p>{h.e(m["ambiance"]) if m["ambiance"] else ""}</p><ul class="plats" style="margin-top:var(--s2)">{li}</ul>{meta}'
                   f'<div class="cta"><a class="btn btn-main" href="#reserver"><span>Réserver</span></a>{cta_t}</div></div></div></details>')
    cartes = (f'<section class="section alt" id="cartes"><div class="w"><p class="eyebrow rv">Les cartes{badge}</p><h2 class="rv">Une carte par maison</h2><div class="fiches">{fiches}</div>'
              f'<p class="note-legale">Prix en euros TTC{" (exemple fictif)" if ex else ""}. Information allergènes : <mark class="todo">à compléter par le restaurateur</mark>.</p></div></section>')
    formats = "".join(f'<div class="rv"><h3>{h.e(f["t"])}</h3><p>{h.e(f["d"])} <mark class="todo">capacité à compléter</mark></p></div>' for f in G["evenements"])
    evt = (f'<section class="section" id="evenements"><div class="w evt"><div>{fig_plein(ph, phs["evt"], "Longue table dressée sous une galerie, pour un repas de groupe", "Salle ou terrasse prête pour un événement", ratio="r45")}</div>'
           f'<div><p class="eyebrow rv">Événements et privatisations{badge}</p><h2 class="rv">Une table pour vos grands moments</h2><div class="formats">{formats}</div>'
           f'<p style="margin-top:var(--s3)"><a class="btn btn-main" href="#devis-evenement"><span>Demander un devis</span></a></p></div></div>'
           f'<div class="w"><div class="devis-box" id="devis-evenement"><h3 style="margin-bottom:var(--s2)">Votre événement en quatre informations</h3>{form_evt(h, G["types_evenement"], aff)}</div></div></section>')
    texte_h = "".join(f"<p>{h.fm(t)}</p>" for t in D["histoire"]) if D else '<p><mark class="todo">Histoire du groupe : comment il est né, qui l\'a fondé, ce qui relie les maisons. Quelques lignes vraies, écrites avec vous.</mark></p>'
    histoire = (f'<section class="section alt" id="histoire"><div class="w hist inv"><div class="rv"><p class="eyebrow">Notre histoire{badge}</p><h2>Des maisons, une façon de recevoir</h2>{texte_h}</div>'
                f'{fig_plein(ph, phs["histoire"], "Cave à vins éclairée et verres sur une table", "La cave, la cuisine ou l’équipe : une photo vraie du groupe", ratio="r43")}</div></section>')
    txt_f = h.e(D["fidelite"]) if D else '<mark class="todo">Programme de fidélité : avantages, fonctionnement, maisons concernées</mark>'
    fidelite = (f'<section class="section sombre" id="fidelite"><div class="w fid"><div class="rv"><p class="eyebrow">Fidélité{badge}</p><h2>Programme fidélité</h2><p>{txt_f}</p></div>'
                f'<div class="rv"><a class="btn btn-line" href="#contact"><span>Rejoindre le programme</span></a></div></div></section>')
    txt_r = h.e(D["recrutement"]) if D else '<mark class="todo">Message de recrutement : ce que vous cherchez, ce que vous offrez</mark>'
    recrut = (f'<section class="section" id="recrutement"><div class="w hist"><div class="rv"><p class="eyebrow">Recrutement{badge}</p><h2>Rejoindre l\'aventure</h2><p>{txt_r}</p>'
              f'<ul class="roles clair">{"".join(f"<li>{h.e(r)}</li>" for r in G["metiers_recrutement"])}</ul>'
              f'<p style="margin-top:var(--s3)"><a class="btn btn-main" href="#contact"><span>Envoyer ma candidature</span></a></p></div>'
              f'{fig_plein(ph, phs["recrutement"], "Mains d’un cuisinier dressant une assiette", "L’équipe au travail, sans visage identifiable sans accord", ratio="r43")}</div></section>')
    avis_html = ('<section class="section alt" id="avis"><div class="w"><p class="eyebrow rv">Avis</p><h2 class="rv">Ce qu\'en disent les clients</h2><div class="grid-a">'
                 + "".join('<div class="avis-c rv"><b>Avis Google à insérer</b>Nom, note, date et texte réels de la fiche Google, repris avec l\'accord du restaurateur. Aucun avis n\'est inventé.</div>' for _ in range(3)) + '</div></div></section>')
    opts_m = "".join(f"<option>{h.e(m['nom'])}</option>" for m in maisons)
    resa = (f'<section class="section contact" id="reserver"><div class="w"><div><p class="eyebrow">Réservations</p><h2>Réserver dans l\'une de nos maisons</h2>'
            f'<p class="lead">Choisissez la maison, la date et l\'heure : on vous confirme par téléphone sous <mark class="todo">délai à confirmer</mark>. Le nombre de personnes se précise au rappel.</p>{tel_big}</div>'
            f'<form class="f" action="#reserver" method="post" id="resa">'
            f'<label for="r-nom">Votre nom<input id="r-nom" name="nom" autocomplete="name" required></label>'
            f'<label for="r-tel">Votre téléphone<input id="r-tel" name="tel" type="tel" autocomplete="tel" inputmode="tel" required></label>'
            f'<label for="r-maison">Maison<select id="r-maison" name="maison">{opts_m}</select></label>'
            f'<label for="r-date">Date et heure<input id="r-date" name="date" type="datetime-local" required></label>'
            f'<button class="btn btn-main" type="submit">Demander ma réservation</button><p class="note">Votre numéro sert uniquement à confirmer la réservation.</p>'
            f'<p class="ok" role="status">Maquette : l\'envoi est désactivé. {"Pour réserver, appelez le " + aff + "." if aff else ""}</p></form></div></section>')
    cols = ""
    for m in maisons:
        a, i = tel_m(m)
        cols += (f'<div><h3>{h.e(m["nom"])}</h3><address>{h.e(m["adresse"]) if m["adresse"] else "<mark class=todo>adresse à compléter</mark>"}<br>'
                 f'{(f"<a href=tel:{i}>{a}</a>") if a else "<mark class=todo>n° à compléter</mark>"}</address></div>')
    mail = D["adresse_mail"] if D else ""
    tel_groupe = f'<a href="tel:{intl}">{aff}</a>' if aff else '<mark class="todo">n° du groupe à compléter</mark>'
    foot = (f'<footer class="gf" id="contact"><div class="w"><div class="grid4"><div><h3>{h.e(nom)}</h3><p>Restaurants et lieux de réception{(" à " + h.e(ville)) if ville else ""}.</p>'
            f'<p style="margin-top:12px">{(h.e(mail) + " (adresse fictive)") if mail else "<mark class=todo>e-mail du groupe à compléter</mark>"}</p>'
            f'<p style="margin-top:8px">{tel_groupe}</p></div>{cols}</div>'
            f'<div class="bas"><a href="#recrutement">Recrutement</a><span>SIRET <mark class="todo">à compléter</mark></span><span>Médiateur de la consommation <mark class="todo">à compléter</mark></span><span>Mentions légales <mark class="todo">à compléter</mark></span><span>Maquette réalisée par LM MULTI-SERVICES. Page privée, non référencée.</span></div></div></footer>')
    bar = f'<div class="bar"><a class="btn btn-main" href="#reserver"><span>Réservations</span></a>{appel("btn btn-line", "Appeler")}</div>'
    corps = f'{header}<main>{hero}{maisons_sec}{cartes}{evt}{histoire}{fidelite}{recrut}{avis_html}{resa}</main>{foot}{bar}'
    villes = sorted({m["ville"] for m in maisons if m["ville"]})
    titre = f"Groupe de restaurants à {ville} — {nom}"
    desc = f"Groupe de restaurants à {ville} : {len(maisons)} maisons, une carte par adresse, événements et privatisations, réservations."
    ld = {"@context": "https://schema.org", "@type": "Organization", "name": nom, "description": desc,
          "address": {"@type": "PostalAddress", "addressLocality": ville, "addressCountry": "FR"},
          "subOrganization": [{"@type": "Restaurant", "name": m["nom"], "address": {"@type": "PostalAddress", "addressLocality": m["ville"], "addressCountry": "FR"},
                               **({"telephone": tel_m(m)[1]} if tel_m(m)[1] else {})} for m in maisons if m["ville"]]}
    if intl: ld["telephone"] = intl
    p["_photos_utilisees"], p["_licences"] = ph.utilisees, ph.lic
    return M.page(p, h, theme, titre, desc, ld, None, M.bandeau(h, p), corps, JS_FORMS + JS_GROUPE, css_extra=("groupe.css",), preload_hero=True)
