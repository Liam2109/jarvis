"""Direction « Braise » (direction = "braise" dans generer.py) : restaurant ou pizzeria au feu de bois. Contenus : metiers/restaurant.json › "braise".
Hero : photo libre de droits d'un four à bois (photos/CREDITS.json) ; sur ordinateur, un script dessine braises, lueur et vapeur par-dessus (canvas, aucune vidéo,
donc aucun poids de vidéo) ; sur mobile et avec « mouvement réduit », l'image reste fixe (version recadrée en 4:5 pour le téléphone).
Puis six grandes photos de plats (empilées au scroll sur ordinateur), puis une carte en HTML : navigation collante par catégorie, prix alignés à droite, allergènes sous chaque plat.
Exemple : plats, prix, adresse et horaires fictifs, signalés « exemple ». Page d'un vrai prospect : carte et horaires « à compléter », aucune photo sans accord.
Aucun avis, aucune note : une zone modèle, à remplir avec les vrais avis Google."""
import json, re

import modeles3 as M3

ALLERG_TITRE = "Allergènes"


def braise(p, met, G):
    """Page restaurant « Braise ». G = module generer (outils partagés)."""
    B = met["braise"]
    ex = p["exemple"]
    nom, ville = p["nom"], p["ville"]
    e, fm = G.e, G.fm
    aff_tel, tel_intl = G.tel_norm(p.get("telephone"))
    badge = '<span class="badge-ex">exemple</span>' if ex else ""
    icone = G.ICONE_TEL
    if aff_tel:
        def appel(cls="btn btn-main", txt=None):
            return f'<a class="{cls}" href="tel:{tel_intl}">{icone}<span>{e(txt or "Appeler le " + aff_tel)}</span></a>'
        lien_tel = f'<a class="tel-big" href="tel:{tel_intl}">{aff_tel}</a>'
        lien_tel_s = f'<a href="tel:{tel_intl}">{aff_tel}</a>'
    else:
        def appel(cls="btn btn-main", txt=None):
            return f'<a class="{cls}" href="#reserver">{icone}<span>Appeler : <mark class="todo">n° à compléter</mark></span></a>'
        lien_tel = '<a class="tel-big" href="#reserver"><mark class="todo">n° à compléter</mark></a>'
        lien_tel_s = '<mark class="todo">n° à compléter</mark>'

    def prix(s):  # espace insécable fine avant le symbole
        return e(s).replace(" €", " €")

    def allerg(a, v=False):
        t = "Allergènes : " + (", ".join(a) if a else "aucun déclaré")
        return ("Végétarien · " if v else "") + t

    # photos libres (registre photos/CREDITS.json) : seulement pour l'exemple, ou si la ligne CSV demande les illustrations
    cr = M3.credits() if (ex or p.get("illustrations")) else {}
    utilisees = []

    def photo(cle, sizes, pos="50% 50%", lazy=True):
        c = cr.get(cle)
        if not c: return None
        utilisees.append(cle)
        base = c["fichier"][:-5]
        srcset = f' srcset="img/{e(base)}-800.webp 800w, img/{e(c["fichier"])} {c["largeur"]}w"' if (G.modeles.PHOTOS / f"{base}-800.webp").exists() else ""
        attr = 'loading="lazy" decoding="async"' if lazy else 'fetchpriority="high" decoding="async"'
        return (f'<img src="img/{e(c["fichier"])}"{srcset} sizes="{sizes}" alt="{e(c["alt"])}" width="{c["largeur"]}" height="{c["hauteur"]}" '
                f'style="object-position:{pos}" {attr}>')

    def credit(cle):
        c = cr[cle]
        return f'Photo d\'illustration libre de droits (Pexels, {e(c["auteur"])}), à remplacer par une photo du restaurant.'

    # --- hero : photo fixe (mobile, mouvement réduit) ; braises, lueur et vapeur dessinées par braise.js sur ordinateur
    hero_media, hero_cred, precharge_img = "", "", ""
    if "braise-hero" in cr and "braise-hero-m" in cr:
        utilisees.extend(["braise-hero", "braise-hero-m"])
        c, cm = cr["braise-hero"], cr["braise-hero-m"]
        hero_media = (f'<div class="hero-media"><picture>'
                      f'<source media="(max-width:899px)" srcset="img/{e(cm["fichier"])}" width="{cm["largeur"]}" height="{cm["hauteur"]}">'
                      f'<img src="img/{e(c["fichier"])}" srcset="img/braise-hero-800.webp 800w, img/{e(c["fichier"])} {c["largeur"]}w" sizes="100vw" '
                      f'alt="{e(c["alt"])}" width="{c["largeur"]}" height="{c["hauteur"]}" fetchpriority="high" decoding="async"></picture></div>')
        hero_cred = f'<p class="cred">{credit("braise-hero")}</p>'
        precharge_img = (f'<link rel="preload" as="image" href="img/{e(cm["fichier"])}" media="(max-width:899px)" fetchpriority="high">\n'
                         f'<link rel="preload" as="image" href="img/{e(c["fichier"])}" imagesrcset="img/braise-hero-800.webp 800w, img/{e(c["fichier"])} {c["largeur"]}w" '
                         f'imagesizes="100vw" media="(min-width:900px)" fetchpriority="high">')

    # --- infos pratiques
    adresse = e(B["adresse"]) if ex else '<mark class="todo">adresse à compléter</mark>'
    resume_h = e(B["resume_horaires"]) if ex else '<mark class="todo">horaires à compléter</mark>'
    infos = (f'<section class="infos" aria-label="Infos pratiques"><div class="w"><ul>'
             f'<li><small>Adresse</small>{adresse}</li><li><small>Horaires</small>{resume_h}</li><li><small>Téléphone</small>{lien_tel_s}</li></ul></div></section>')

    # --- grandes photos de plats
    chapitres = []
    if ex or cr:
        for x in B["plats"]:
            im = photo(x["photo"], "100vw", x.get("pos", "50% 50%"))
            if not im: continue
            chapitres.append(f'<article class="chap"><figure class="chap-ph">{im}</figure>'
                             f'<div class="chap-t"><div class="w"><h3>{e(x["n"])}<span class="pl-px">{prix(x["p"])}</span></h3><p>{e(x["d"])}</p>'
                             f'<p class="chap-a">{e(allerg(x["a"]))}</p><p class="cred">{badge} Plat et prix d\'exemple. {credit(x["photo"])}</p></div></div></article>')
    if chapitres:
        plats = (f'<section class="plats" id="plats"><div class="w plats-h"><p class="eyebrow">Plats typiques</p><h2>{e(B["plats_t"])}</h2>'
                 f'<p class="sub">{e(B["plats_d"])}</p></div><div class="chaps">{"".join(chapitres)}</div></section>')
    else:
        plats = ('<section class="plats" id="plats"><div class="w plats-h"><p class="eyebrow">Plats typiques</p><h2>Ce qui sort du four</h2>'
                 '<div class="ph"><b>Photos à remplacer</b><span>Trois à six plats signature, en grand</span><small>Photos du restaurant, avec son accord (paysage, grande définition).</small></div></div></section>')

    # --- carte
    if ex:
        cats = B["carte"]
    else:
        cats = [{"cat": c["cat"], "lignes": c["lignes"]} for c in met["carte_vide"]]
    ancres, blocs = [], []
    for c in cats:
        aid = "c-" + G.slug(c["cat"])
        ancres.append(f'<li><a href="#{aid}">{e(c["cat"])}</a></li>')
        if "plats" in c:
            li = "".join(
                f'<li><div class="pl-h"><span class="pl-n">{e(x["n"])}</span><span class="pl-l" aria-hidden="true"></span><span class="pl-p">{prix(x["p"])}</span></div>'
                f'<p class="pl-d">{e(x["d"])}</p><p class="pl-a">{e(allerg(x["a"], x.get("v")))}</p></li>' for x in c["plats"])
        else:
            li = "".join(f'<li><div class="pl-h"><span class="pl-n"><mark class="todo">{e(l)}</mark></span></div></li>' for l in c["lignes"])
        blocs.append(f'<section class="cat" id="{aid}"><h3 class="cat-t">{e(c["cat"])}</h3><ul class="pl">{li}</ul></section>')
    liste_a = ", ".join(B["allergenes"])
    aller = (f'<aside class="allerg" aria-labelledby="t-all"><h3 id="t-all">{ALLERG_TITRE}</h3>'
             f'<p>Les 14 allergènes à déclaration obligatoire (règlement UE n° 1169/2011) : {e(liste_a)}.</p>'
             f'<p>Chaque plat indique ceux qu\'il contient. Une allergie ou une intolérance ? Dites-le en réservant et au moment de commander : l\'équipe vous montre la fiche détaillée.</p>'
             + ('<p class="note-ex">' + badge + ' Cette carte est un exemple : la fiche allergènes réelle vient du restaurateur.</p>' if ex else
                '<p><mark class="todo">Fiche allergènes à compléter par le restaurateur</mark></p>') + '</aside>')
    carte_d = e(B["carte_d"]) if ex else "Prix nets, toutes taxes comprises, et allergènes sous chaque plat : <mark class=\"todo\">carte à compléter par le restaurateur</mark>."
    carte = (f'<section class="carte" id="carte"><div class="w"><div class="carte-h"><p class="eyebrow">Carte</p><h2>{e(B["carte_t"])} {badge}</h2><p class="sub">{carte_d}</p></div>'
             f'<nav class="cartenav" aria-label="Catégories de la carte"><ul>{"".join(ancres)}</ul></nav>'
             f'<div class="cats">{"".join(blocs)}{aller}</div></div></section>')

    # --- avis : zone modèle, jamais d'avis inventé
    lien = p.get("lienavis", "")
    lien_html = f'<a href="{e(lien)}" rel="noopener">Lire tous les avis sur Google</a>' if lien.startswith("https://") else ""
    reels = [x.split("|") for x in re.split(r"\|\|", p.get("avisreels", "")) if x.strip()]
    if reels:
        avis_html = '<div class="revs">' + "".join(f'<blockquote class="rev">{e(a[0])}<cite>{e(a[1].strip()) if len(a) > 1 else ""}</cite></blockquote>' for a in reels[:3]) + f'</div><p>{lien_html}</p>'
    else:
        avis_html = (f'<div class="rev"><b>Vos avis Google réels s\'afficheront ici</b>'
                     f'<p>Les avis sont repris tels quels depuis la fiche Google, avec l\'accord de leurs auteurs. Aucun avis, aucune note n\'est inventé.</p>{lien_html}</div>')

    # --- horaires, réservation
    if ex:
        rows = "".join(f'<tr><th scope="row">{e(j)}</th><td>{e(t)}</td></tr>' for j, t in B["horaires"])
    else:
        rows = "".join(f'<tr><th scope="row">{e(j)}</th><td><mark class="todo">à compléter</mark></td></tr>' for j in met["horaires_jours"])
    hor = f'<table class="hor"><caption>Horaires d\'ouverture {badge}</caption><tbody>{rows}</tbody></table>'
    nb = "".join(f"<option>{i}</option>" for i in range(1, 11))

    titre = f"{nom} — restaurant au feu de bois à {ville}"
    desc = f"Restaurant au feu de bois à {ville} : pizzas, viandes et légumes du four, carte avec allergènes" + (f", réservation ou appel au {aff_tel}." if aff_tel else ", réservation en ligne.")
    ld = {"@context": "https://schema.org", "@type": "Restaurant", "name": nom, "description": desc, "servesCuisine": "Pizzas et grillades au feu de bois",
          "address": {"@type": "PostalAddress", "addressLocality": ville, "addressCountry": "FR"}, "acceptsReservations": True}
    if tel_intl: ld["telephone"] = tel_intl
    if ex: note_ex = '<b>EXEMPLE</b> — ceci n\'est pas votre site : restaurant, plats, prix, adresse et horaires fictifs, aucun avis réel. Photos libres de droits.'
    else: note_ex = f'Maquette de démonstration préparée par LM MULTI-SERVICES pour {e(nom)}. <b>Ce n\'est pas le site officiel</b> de l\'établissement. Les zones surlignées sont à compléter.'

    familles, precharge = G.THEMES["braise"]
    css = M3.mini_css(G.css_polices(familles) + (G.MOTEUR / "themes" / "braise.css").read_text(encoding="utf-8"))
    page = f"""<!doctype html>
<html lang="fr" data-theme="braise">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(titre)}</title>
<meta name="description" content="{e(desc)}">
<meta name="robots" content="noindex, nofollow, noarchive">
<meta name="theme-color" content="#16100C">
<link rel="icon" href="data:,">
<link rel="preload" href="../assets/polices/{precharge}" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="../assets/polices/HankenGrotesk-400-700.woff2" as="font" type="font/woff2" crossorigin>
{precharge_img}
<style>{css}</style>
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
</head>
<body>
<a class="skip" href="#reserver">Aller à la réservation</a>
<header class="top"><div class="w">
  <a class="brand" href="#top">{e(nom)}{badge}</a>
  <nav class="nav" aria-label="Sections"><a href="#plats">Plats</a><a href="#carte">Carte</a><a href="#avis">Avis</a><a href="#reserver">Réserver</a></nav>
  <a class="btn btn-main only-rail" href="#reserver"><span>Réserver une table</span></a>{appel("btn btn-line", "Appeler")}
</div></header>
<main id="top">
<section class="hero{" sans-photo" if not hero_media else ""}">
  {hero_media}
  <div class="w hero-t">
    <h1><span class="kicker">{e(B["label"])} à {e(ville)}</span>{e(B["titre"])}</h1>
    <p class="lead">{e(B["lead"])}</p>
    <div class="cta"><a class="btn btn-main" href="#reserver"><span>Réserver une table</span></a>{appel("btn btn-line", "Appeler le " + aff_tel if aff_tel else None)}</div>
    <p class="exemple">{note_ex}</p>
  </div>
  {hero_cred}
</section>
{infos}
{plats}
{carte}
<section class="section avis" id="avis"><div class="w">
  <p class="eyebrow">Avis</p><h2>Ce qu'en disent les clients</h2>
  {avis_html}
</div></section>
<section class="section resa" id="reserver"><div class="w">
  <div><p class="eyebrow">Réservation</p><h2>Réserver une table</h2>
  <p class="sub">Quatre informations, et on vous confirme par téléphone sous <mark class="todo">délai à confirmer</mark>. Pour un groupe, appelez.</p>
  {lien_tel}
  <p class="adr"><b>Adresse</b> {adresse}</p>
  {hor}</div>
  <form class="f" action="#reserver" method="post" id="devis">
    <label for="f-nom">Votre nom<input id="f-nom" name="nom" autocomplete="name" required></label>
    <label for="f-tel">Votre téléphone<input id="f-tel" name="tel" type="tel" autocomplete="tel" inputmode="tel" required></label>
    <label for="f-date">Date et heure<input id="f-date" name="date" type="datetime-local" required></label>
    <label for="f-nb">Nombre de personnes<select id="f-nb" name="couverts">{nb}<option>Plus de 10 : appelez</option></select></label>
    <button class="btn btn-main" type="submit">Demander ma réservation</button>
    <p class="note">Votre numéro sert uniquement à confirmer la réservation.</p>
    <p class="ok" role="status">Maquette : l'envoi est désactivé. {"Pour réserver, appelez le " + aff_tel + "." if aff_tel else ""}</p>
  </form>
</div></section>
<section class="mentions" id="mentions"><div class="w">
  <h2>Mentions légales</h2>
  <p>{e(nom)} — restaurant à {e(ville)}. Prix nets, toutes taxes comprises. SIRET <mark class="todo">à compléter</mark> · Médiateur de la consommation <mark class="todo">à compléter</mark> · Responsable de publication et hébergeur <mark class="todo">à compléter</mark>.</p>
</div></section>
</main>
<footer><div class="w">
  <p><strong>{e(nom)}</strong> — restaurant à {e(ville)} · {appel("fl", aff_tel or "Appeler").replace(icone, "")}</p>
  <p>{"Exemple de site, pas votre site officiel. " if ex else ""}Maquette réalisée par LM MULTI-SERVICES. Page privée, non référencée.</p>
</div></footer>
<div class="bar">{appel("btn btn-line", "Appeler")}<a class="btn btn-main" href="#reserver"><span>Réserver</span></a></div>
<script src="../assets/js/braise.js" defer></script>
</body>
</html>
"""
    if utilisees:  # copie + registre faits par generer.ecrire
        uniques = list(dict.fromkeys(utilisees))
        p["_photos_utilisees"] = uniques
        p["_licences"] = {k: {"fichier": cr[k]["fichier"], "auteur": cr[k]["auteur"], "source": cr[k]["url"], "licence": cr[k]["licence"], "date": cr[k]["date"], "traitement": cr[k].get("traitement", "")} for k in uniques}
    # chiffres autorisés : variables du prospect, texte réglementaire fixe, liste « nombre de personnes » (1 à 10), et (exemple seulement) la carte et les horaires fictifs
    permis = " ".join(str(v) for k, v in p.items() if not k.startswith("_")) + " 14 1169 2011 6 7 8 9" + (" " + json.dumps(B, ensure_ascii=False) if ex else "")
    erreurs = M3.controles(page, p, permis)
    if erreurs: raise ValueError(f"page bloquée pour {nom} : " + " ; ".join(erreurs))
    return page
