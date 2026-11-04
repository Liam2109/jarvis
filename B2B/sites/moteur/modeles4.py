"""Direction « Plombier-chauffagiste » (direction = "eau" dans generer.py). Mise en page sobre d'un site d'artisan : vraies photos libres de droits
(Pexels, licence dans photos/CREDITS.json), texte direct, aucune illustration, aucune forme décorative. Contenus : metiers/plombier.json › "eau".
Mêmes variables CSV que modeles3 (note, avis, source, annees, labels, qualification, decennale, delai, avis_reels, lien_avis) : rien n'est affiché
sans donnée fournie. Sans photo utilisable (page d'un vrai prospect, sans accord de l'artisan), le hero reste uni et les sections gardent une zone
« photo à remplacer ». Haut de page : un seul bouton (Appeler), ni bandeau ni défilement. Interaction signature : curseur avant/après (salle de bain) ;
animations de photo : zoom lent du hero au scroll et révélation de la photo du radiateur (CSS natif, 2 images seulement) ; apparition douce et FAQ.
Curseur : metiers/plombier.json › eau › salle_de_bain › img_avant / img_apres. Deux chemins d'image, rien d'autre à changer : si les deux fichiers sont des photos
libres du registre (photos/CREDITS.json), le curseur est en mode « illustration » (Avant (simulé), mention, crédit) ; sinon ce sont les photos de l'artisan
(étiquettes Avant / Après, sans mention d'illustration) et les fichiers sont copiés depuis photos/ vers img/."""
import json, re

import modeles3 as M3


def eau(p, met, G):
    """Page plombier. G = module generer (outils partagés)."""
    E = met["eau"]
    ex = p["exemple"]
    nom, ville, label = p["nom"], p["ville"], E["label"]
    e, fm = G.e, G.fm
    aff_tel, tel_intl = G.tel_norm(p.get("telephone"))
    badge = '<span class="badge-ex">exemple</span>' if ex else ""
    icone = G.ICONE_TEL
    if aff_tel:
        def appel(cls="btn btn-main", txt=None):
            return f'<a class="{cls}" href="tel:{tel_intl}">{icone}<span>{e(txt or "Appeler le " + aff_tel)}</span></a>'
        lien_tel = f'<a class="tel-big" href="tel:{tel_intl}">{aff_tel}</a>'
    else:
        def appel(cls="btn btn-main", txt=None):
            return f'<a class="{cls}" href="#contact">{icone}<span>Appeler : <mark class="todo">n° à compléter</mark></span></a>'
        lien_tel = '<a class="tel-big" href="#contact"><mark class="todo">n° à compléter</mark></a>'

    zone = G.liste(p.get("zone"))
    if ville not in zone: zone.insert(0, ville)
    zone = zone[:14]
    zone_todo = "" if len(zone) > 1 else ' <mark class="todo">communes desservies à compléter</mark>'
    communes = ", ".join(e(v) for v in zone[1:5]) + (" et alentours" if len(zone) > 1 else "")

    # photos libres (registre photos/CREDITS.json) : seulement pour l'exemple, ou si la ligne CSV demande les illustrations
    cr = M3.credits() if (ex or p.get("illustrations")) else {}
    utilisees = []

    def photo(cle, sizes, lazy=True, cls="", legende=True):
        """<figure> avec la photo libre `cle`, ou None si elle n'est pas utilisable."""
        c = cr.get(cle)
        if not c: return None
        utilisees.append(cle)
        base = c["fichier"][:-5]
        srcset = f' srcset="img/{e(base)}-800.webp 800w, img/{e(c["fichier"])} {c["largeur"]}w"' if (G.modeles.PHOTOS / f"{base}-800.webp").exists() else ""
        img = (f'<img src="img/{e(c["fichier"])}"{srcset} sizes="{sizes}" alt="{e(c["alt"])}" width="{c["largeur"]}" height="{c["hauteur"]}" '
               + ('loading="lazy" decoding="async">' if lazy else 'fetchpriority="high" decoding="async">'))
        cap = f'<figcaption>Photo d\'illustration libre de droits (Pexels, {e(c["auteur"])}), à remplacer par une photo de l\'artisan.</figcaption>' if legende else ""
        return f'<figure class="{cls}">{img}{cap}</figure>'

    def a_remplacer(detail):
        return f'<div class="ph"><b>Photo à remplacer</b><span>{e(detail)}</span><small>Photo de l\'artisan, avec son accord (paysage, grande définition).</small></div>'

    # preuves : seulement ce que les variables fournissent
    pr = []
    note, avis = G.nombre(p.get("note")), G.nombre(p.get("avis"))
    source_avis = p.get("sourceavis") or p.get("source") or ""
    if note and avis and (ex or source_avis): pr.append(("Note Google", f"{note:.1f}".replace(".", ",") + f" / 5 · {int(avis)} avis"))
    for cle, lib in (("qualification", "Qualification"), ("decennale", "Décennale")):
        if p.get(cle) and re.search(r"\d", p[cle]): pr.append((lib, e(p[cle])))
        elif p.get(cle): print(f"  ! {lib} ignorée pour {nom} : pas de numéro")
    if p.get("delai"): pr.append(("Délai d'intervention", e(p["delai"])))
    an = G.nombre(p.get("annees"))
    if an: pr.append(("Activité", f"{int(an)} ans"))
    for lb in G.liste(p.get("labels"))[:3]: pr.append(("Label", e(lb)))
    preuves = ""
    if pr:
        li = "".join(f"<li><small>{e(k)}</small>{v}{badge}</li>" for k, v in pr)
        preuves = f'<section class="proofs" aria-label="Preuves"><div class="w"><ul>{li}</ul></div></section>'

    # --- urgence : trois gestes pour limiter les dégâts, photo des robinets d'arrêt (section courte)
    D = E["depannage"]
    gestes = "".join(f'<li><h3>{fm(g["t"])}</h3><p>{fm(g["d"])}</p></li>' for g in D["gestes"])
    ph_dep = photo("plomb-robinets", "(min-width:900px) 30vw, 100vw", cls="ph-img") or a_remplacer("Robinets d'arrêt d'un point d'eau")
    urgence = (f'<section class="section urg" id="depannage"><div class="w"><div><p class="eyebrow">Dépannage fuite</p><h2>{fm(D["t"])}</h2>'
               f'<p class="sub">{fm(D["d"])}</p><ol class="gestes">{gestes}</ol></div>{ph_dep}</div></section>')
    C = E["chaleur"]

    S = E["salle_de_bain"]
    par_fichier = {v["fichier"]: k for k, v in cr.items()}
    f_av, f_ap = S.get("img_avant", "").rsplit("/", 1)[-1], S.get("img_apres", "").rsplit("/", 1)[-1]
    if not cr:  # page d'un vrai prospect, sans accord pour les photos : deux zones à remplacer
        media = (f'<div class="ba-ph">{a_remplacer("Avant : " + S["photo"])}{a_remplacer("Après : " + S["photo"])}</div>')
    else:
        illu = f_av in par_fichier and f_ap in par_fichier
        if illu:
            ca, cp = cr[par_fichier[f_av]], cr[par_fichier[f_ap]]
            utilisees.extend([par_fichier[f_av], par_fichier[f_ap]])
            alt_av, alt_ap, dim = ca["alt"], cp["alt"], (cp["largeur"], cp["hauteur"])
            t_av, t_ap = "Avant (simulé)", "Après"
            ill = '<span class="ba-ill">Illustration</span>'
            legende = (f'Illustration : « après » = photo libre de droits (Pexels, {e(cp["auteur"])}) ; « avant » simulé par traitement d\'image à partir de la même photo, '
                       f'donc au même cadrage. Pas un chantier de l\'artisan : à remplacer par ses photos avant/après.')
        else:
            p.setdefault("_fichiers_artisan", []).extend([f_av, f_ap])
            alt_av = S.get("alt_avant") or "Salle de bain avant les travaux"
            alt_ap = S.get("alt_apres") or "Salle de bain après les travaux"
            dim = (S.get("largeur", 1200), S.get("hauteur", 800))
            t_av, t_ap, ill = "Avant", "Après", ""
            legende = fm(S.get("legende") or "Chantier de l'artisan : [[lieu et durée à compléter]]")
        img = lambda f, alt, cls, prio=False: f'<img class="{cls}" src="img/{e(f)}" alt="{e(alt)}" width="{dim[0]}" height="{dim[1]}" ' + ('fetchpriority="high" decoding="async">' if prio else 'decoding="async">')
        fleches = '<svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true"><path d="M9 6l-6 6 6 6M15 6l6 6-6 6" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>'
        media = (f'<figure class="ba" data-ba><div class="ba-in">{img(f_av, alt_av, "ba-avant")}{img(f_ap, alt_ap, "ba-apres", True)}'
                 f'<span class="ba-tag av">{e(t_av)}</span><span class="ba-tag ap">{e(t_ap)}</span>{ill}'
                 f'<div class="ba-h" role="slider" tabindex="0" aria-orientation="horizontal" aria-valuemin="0" aria-valuemax="100" aria-valuenow="50" '
                 f'aria-valuetext="Séparation au milieu" aria-label="Comparer avant et après : faites glisser, ou utilisez les flèches du clavier"><span class="ba-k">{fleches}</span></div></div>'
                 f'<figcaption>{legende}</figcaption></figure>')
    # --- ce que nous faisons : cartes à faire défiler (chauffage, eau chaude, salle de bain, autres)
    def carte(t_, d_, pts, fig):
        li = "".join(f"<li>{fm(x)}</li>" for x in pts)
        return f'<article class="card">{fig or ""}<div class="cb"><h3>{fm(t_)}</h3><p>{fm(d_)}</p><ul class="pts">{li}</ul></div></article>'
    b0, b1 = C["blocs"][0], C["blocs"][1]
    cartes = [carte(b0["t"], b0["d"], b0["points"], photo("plomb-radiateur", "380px", cls="ph-img")),
              carte(b1["t"], b1["d"], b1["points"], photo("plomb-hero", "380px", cls="ph-img")),
              carte(S["t"], S["d"], S["points"], None),
              f'<article class="card card-txt"><div class="cb"><h3>Aussi</h3><p>{e(E["autres"])}</p><p class="marques">{fm(C["marques"])}</p></div></article>']
    faire = (f'<section class="section faire" id="chaleur"><div class="w"><p class="eyebrow">Ce que nous faisons</p><h2>{fm(C["t"])}</h2>'
             f'<p class="hint">Faites défiler vers la droite pour voir toutes les prestations.</p></div>'
             f'<div class="scroll" role="region" aria-label="Prestations, à faire défiler" tabindex="0">{"".join(cartes)}</div></section>')

    # --- frise des étapes : de l'appel à l'intervention
    steps = "".join(f'<li class="rv"><h3>{fm(s["t"])}</h3><p>{fm(s["d"])}</p></li>' for s in met["etapes"])
    methode = (f'<section class="section dark frisesec" id="methode"><div class="w"><p class="eyebrow">Comment ça se passe</p><h2>De l\'appel à l\'intervention</h2>'
               f'<ol class="frise">{steps}</ol></div></section>')

    eng = "".join(f'<li><h3>{fm(x["t"])}</h3><p>{fm(x["d"])}</p></li>' for x in met["raisons"])
    engagements = (f'<div class="eng" id="engagements"><p class="eyebrow">Nos engagements</p><h2>Trois raisons de nous appeler</h2>'
                   f'<ol>{eng}</ol><p class="note"><mark class="todo">Engagements proposés : à confirmer par l\'artisan avant mise en ligne</mark></p></div>')

    faq = "".join(f'<details><summary>{fm(q["q"])}</summary><p>{fm(q["a"])}</p></details>' for q in met["faq"])
    villes = "".join(f"<li>{e(v)}</li>" for v in zone)
    options = "".join(f"<option>{e(o)}</option>" for o in met["besoins"])

    lien = p.get("lienavis", "")
    lien_html = f'<a href="{e(lien)}" rel="noopener">Lire tous les avis sur Google</a>' if lien.startswith("https://") else ""
    reels = [x.split("|") for x in re.split(r"\|\|", p.get("avisreels", "")) if x.strip()]
    if reels:
        avis_html = '<div class="revs">' + "".join(f'<blockquote class="rev">{e(a[0])}<cite>{e(a[1].strip()) if len(a) > 1 else ""}</cite></blockquote>' for a in reels[:3]) + f'</div><p style="margin-top:var(--s3)">{lien_html}</p>'
    else:
        resume = f"Note Google : {note:.1f} / 5 sur {int(avis)} avis. ".replace(".", ",", 1) if note and avis else ""
        avis_html = (f'<div class="rev"><b>Vos avis Google réels s\'afficheront ici</b>'
                     f'<p>{resume}Les avis sont repris tels quels depuis la fiche Google, avec l\'accord de leurs auteurs. Aucun avis n\'est inventé.</p>{lien_html}</div>')

    titre = f"{label} à {ville} — {nom}"
    desc = f"{label} à {ville} et alentours : dépannage fuite, chauffe-eau, chaudière, salle de bain. Prix écrit avant les travaux" + (f". Appelez le {aff_tel}." if aff_tel else ".")
    ld = {"@context": "https://schema.org", "@type": met["schema"], "name": nom, "description": desc,
          "address": {"@type": "PostalAddress", "addressLocality": ville, "addressCountry": "FR"},
          "areaServed": [{"@type": "City", "name": v} for v in zone]}
    if tel_intl: ld["telephone"] = tel_intl
    if ex: note_ex = '<b>EXEMPLE</b> — ceci n\'est pas votre site : entreprise, numéro et textes fictifs, aucun avis réel.'
    else: note_ex = f'Maquette de démonstration préparée par LM MULTI-SERVICES pour {e(nom)}. <b>Ce n\'est pas le site officiel</b> de l\'entreprise. Les zones surlignées sont à compléter.'

    familles, precharge = G.THEMES["eau"]
    css = M3.mini_css(G.css_polices(familles) + (G.MOTEUR / "themes" / "eau.css").read_text(encoding="utf-8"))
    page = f"""<!doctype html>
<html lang="fr" data-theme="eau">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(titre)}</title>
<meta name="description" content="{e(desc)}">
<meta name="robots" content="noindex, nofollow, noarchive">
<meta name="theme-color" content="#1F4A45">
<link rel="icon" href="data:,">
<link rel="preload" href="../assets/polices/{precharge}" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="../assets/polices/HankenGrotesk-400-700.woff2" as="font" type="font/woff2" crossorigin>
<style>{css}</style>
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
</head>
<body>
<a class="skip" href="#contact">Aller au formulaire</a>
<header class="top mini"><div class="w">
  <a class="brand" href="#top">{e(nom)}{badge}</a>
  {appel("btn btn-main", "Appeler")}<a class="btn btn-line" href="#contact"><span>Devis gratuit</span></a>
</div></header>
<main id="top">
<section class="herosplit"><div class="w hs">
  <div class="hero-t">
    <h1><span class="kicker">{e(label)} à {e(ville)}</span>{e(E["titre"])}</h1>
    <p class="lead">{fm(E["lead"])}</p>
    {appel()}
    <p class="zone-line"><b>{e(ville)}</b>{" et " + communes if len(zone) > 1 else ""}.{zone_todo}</p>
    <p class="exemple">{note_ex}</p>
  </div>
  <div class="hs-m" id="salle-de-bain">{media}</div>
</div></section>
{preuves}
{urgence}
{faire}
{methode}
<section class="section alt band"><div class="w band-g">
  {engagements}
  <div id="avis"><p class="eyebrow">Avis clients</p><h2>Ce que disent les clients</h2>{avis_html}</div>
</div></section>
<section class="section zf" id="zone"><div class="w zf-g">
  <div><p class="eyebrow">Zone d'intervention</p><h2>Autour de {e(ville)}</h2>
  <p class="sub">{e(nom)} intervient dans ces communes{zone_todo}. Une autre commune ? Appelez pour vérifier.</p>
  <ul class="villes">{villes}</ul></div>
  <div id="faq"><p class="eyebrow">Questions fréquentes</p><h2>Vos questions</h2><div class="faq">{faq}</div></div>
</div></section>
<section class="section contact dark" id="contact"><div class="w">
  <div><p class="eyebrow">Contact</p><h2>Un devis, un rappel</h2>
  <p class="sub">Appelez, ou laissez 4 informations : on vous rappelle sous <mark class="todo">délai à confirmer</mark>.</p>
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
  <p><strong>{e(nom)}</strong> — {e(label)} à {e(ville)} · {appel("fl", aff_tel or "Appeler").replace(icone, "")}</p>
  <p>{"Exemple de site, pas votre site officiel. " if ex else ""}Maquette réalisée par LM MULTI-SERVICES. Page privée, non référencée.</p>
</div></footer>
<div class="bar">{appel("btn btn-main", "Appeler")}<a class="btn btn-line" href="#contact"><span>Devis gratuit</span></a></div>
<script src="../assets/js/eau.js" defer></script>
</body>
</html>
"""
    if utilisees:  # copie + registre faits par generer.ecrire
        uniques = list(dict.fromkeys(utilisees))
        p["_photos_utilisees"] = uniques
        p["_licences"] = {k: {"fichier": cr[k]["fichier"], "auteur": cr[k]["auteur"], "source": cr[k]["url"], "licence": cr[k]["licence"], "date": cr[k]["date"], "traitement": cr[k].get("traitement", "")} for k in uniques}
    erreurs = M3.controles(page, p, " ".join(str(v) for k, v in p.items() if not k.startswith("_")))
    if erreurs: raise ValueError(f"page bloquée pour {nom} : " + " ; ".join(erreurs))
    return page
