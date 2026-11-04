"""Pages exemples des commerces et métiers locaux hors bâtiment : salon (coiffeur), petale (fleuriste), fournil (boulangerie), garage.
Appelé par generer.py quand la direction vaut « salon », « petale », « fournil » ou « garage » (famille « local »). Exemples fictifs seulement : une page d'un vrai prospect
n'est pas générée (le message de prospection renvoie vers la page exemple du métier, agents\\liens-metiers.json). Contenus : metiers/<métier>.json › "page".
Structure de chaque page : voir STRUCTURES.md. Interface (navigation, boutons, étiquette, séparateurs) dessinée en CSS selon l'univers du métier : voir themes/<direction>.css.
Aucun avis, aucune note, aucun chiffre qui ne vienne du fichier du métier ; tout ce qui est inventé est marqué « exemple »."""
import json, re
from types import SimpleNamespace as NS

import modeles3 as M3


def contexte(p, met, G, icone_bouton=None):
    """Outils communs : appel, photos libres du registre, horaires, en-tête, pied de page, contrôles. G = module generer."""
    if not p["exemple"]: raise ValueError("page « local » : exemple seulement (pas de maquette de vrai prospect)")
    e, fm = G.e, G.fm
    aff_tel, tel_intl = G.tel_norm(p.get("telephone"))
    icone = icone_bouton or G.ICONE_TEL
    badge = '<span class="badge-ex">exemple</span>'
    cr = M3.credits(); utilisees = []

    def appel(cls="btn btn-main", txt=None, interieur=""):
        return f'<a class="{cls}" href="tel:{tel_intl}">{interieur or icone}<span>{e(txt or "Appeler le " + aff_tel)}</span></a>'

    def photo(cle, sizes="100vw", pos="50% 50%", lazy=True, cls=""):
        c = cr[cle]; utilisees.append(cle); base = c["fichier"][:-5]
        srcset = f' srcset="img/{e(base)}-800.webp 800w, img/{e(c["fichier"])} {c["largeur"]}w"' if (G.modeles.PHOTOS / f"{base}-800.webp").exists() else ""
        return (f'<img{(" class=" + chr(34) + cls + chr(34)) if cls else ""} src="img/{e(c["fichier"])}"{srcset} sizes="{sizes}" alt="{e(c["alt"])}" width="{c["largeur"]}" height="{c["hauteur"]}" '
                f'style="object-position:{pos}" ' + ('loading="lazy" decoding="async">' if lazy else 'fetchpriority="high" decoding="async">'))

    def credit(cle): return f'Photo d\'illustration libre de droits (Pexels, {e(cr[cle]["auteur"])}), à remplacer par une photo du lieu.'

    def horaires(rows):
        tr = "".join(f'<tr><th scope="row">{e(j)}</th><td>{e(t)}</td></tr>' for j, t in rows)
        return f'<table class="hor"><caption>Horaires d\'ouverture {badge}</caption><tbody>{tr}</tbody></table>'

    def tete(titre, desc, ld, couleur, theme, precharges, css_extra=""):
        familles, precharge = G.THEMES[theme]
        css = M3.mini_css(G.css_polices(familles) + (G.MOTEUR / "themes" / f"{theme}.css").read_text(encoding="utf-8") + css_extra)
        pre = "".join(f'<link rel="preload" href="../assets/polices/{f}" as="font" type="font/woff2" crossorigin>\n' for f in [precharge] + precharges)
        return (f'<!doctype html>\n<html lang="fr" data-theme="{theme}">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1">\n'
                f'<title>{e(titre)}</title>\n<meta name="description" content="{e(desc)}">\n<meta name="robots" content="noindex, nofollow, noarchive">\n<meta name="theme-color" content="{couleur}">\n'
                f'<link rel="icon" href="data:,">\n{pre}<style>{css}</style>\n<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>\n</head>\n')

    def formulaire(champs_html, bouton, note):
        return (f'<form class="f" action="#contact" method="post" id="devis">{champs_html}<button class="btn btn-main" type="submit"><span>{e(bouton)}</span></button>'
                f'<p class="note">{e(note)}</p><p class="ok" role="status">Maquette : l\'envoi est désactivé. Pour joindre l\'établissement, appelez le {aff_tel}.</p></form>')

    def pied(nom, ville, metier_txt, second_action, script, mention_plus=""):
        return (f'<section class="mentions" id="mentions"><div class="w"><h2>Mentions légales</h2><p>{e(nom)} — {e(metier_txt)} à {e(ville)}. {mention_plus}SIRET <mark class="todo">à compléter</mark> · '
                f'Responsable de publication et hébergeur <mark class="todo">à compléter</mark>.</p></div></section>\n</main>\n'
                f'<footer><div class="w"><p><strong>{e(nom)}</strong> — {e(metier_txt)} à {e(ville)} · <a class="fl" href="tel:{tel_intl}">{aff_tel}</a></p>'
                f'<p>Exemple de site, pas votre site officiel. Maquette réalisée par LM MULTI-SERVICES. Page privée, non référencée.</p></div></footer>\n'
                f'<div class="bar">{appel("btn btn-main", "Appeler")}{second_action}</div>\n<script src="../assets/js/{script}" defer></script>\n</body>\n</html>\n')

    def finaliser(page, B, texte_extra=""):
        if utilisees:
            uniques = list(dict.fromkeys(utilisees)); p["_photos_utilisees"] = uniques
            p["_licences"] = {k: {"fichier": cr[k]["fichier"], "auteur": cr[k]["auteur"], "source": cr[k]["url"], "licence": cr[k]["licence"], "date": cr[k]["date"], "traitement": cr[k].get("traitement", "")} for k in uniques}
        permis = " ".join(str(v) for k, v in p.items() if not k.startswith("_")) + " 14 6 7 8 9 10 " + json.dumps(B, ensure_ascii=False) + " " + texte_extra
        erreurs = M3.controles(page, p, permis)
        if erreurs: raise ValueError(f"page bloquée pour {p['nom']} : " + " ; ".join(erreurs))
        return page

    return NS(e=e, fm=fm, aff_tel=aff_tel, tel_intl=tel_intl, icone=icone, badge=badge, appel=appel, photo=photo, credit=credit, horaires=horaires, tete=tete, formulaire=formulaire,
              pied=pied, finaliser=finaliser, cr=cr, nom=p["nom"], ville=p["ville"])


CISEAUX = ('<svg class="ci" viewBox="0 0 28 28" width="26" height="26" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round">'
           '<g class="l1"><path d="M6.5 21.5 25 3"/><circle cx="6" cy="22" r="3.4"/></g><g class="l2"><path d="M6.5 6.5 25 25"/><circle cx="6" cy="6" r="3.4"/></g></svg>')


CUT = ('<svg class="cut" viewBox="0 0 64 40" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round">'
       '<g class="sa"><path d="M24 20 61 9"/><path d="M13.500 12.500 24 20"/><circle cx="9" cy="10" r="5"/></g><g class="sb"><path d="M24 20 61 31"/><path d="M13.500 27.500 24 20"/><circle cx="9" cy="30" r="5"/></g></svg>')

PLAN = ('<svg viewBox="0 0 520 340" role="img" aria-label="Plan schématique d\'exemple : le salon, une rue, une rivière et un arrêt de bus" xmlns="http://www.w3.org/2000/svg">'
        '<rect width="520" height="340" fill="#ece6d8"/>'
        '<path d="M-10 255C90 235 150 300 260 280S430 220 530 250V345H-10Z" fill="#c4d4d8"/>'
        '<g fill="#d9d1bd"><rect x="30" y="30" width="110" height="70" rx="4"/><rect x="30" y="125" width="110" height="60" rx="4"/><rect x="170" y="30" width="120" height="70" rx="4"/>'
        '<rect x="330" y="30" width="150" height="70" rx="4"/><rect x="330" y="125" width="150" height="60" rx="4"/><rect x="30" y="205" width="90" height="25" rx="4"/></g>'
        '<g stroke="#fbf9f3" stroke-linecap="round" fill="none"><path d="M10 112H510" stroke-width="16"/><path d="M155 10V240" stroke-width="14"/><path d="M310 10V240" stroke-width="14"/><path d="M10 198H300" stroke-width="9"/></g>'
        '<rect x="170" y="125" width="120" height="60" rx="4" fill="#15171a"/>'
        '<g font-family="Manrope,system-ui,sans-serif" font-size="13" font-weight="800" fill="#15171a"><text x="318" y="106" font-size="11" fill="#55554e">rue de l\'Exemple</text><text x="196" y="160" fill="#f4efe4">Le salon</text>'
        '<text x="338" y="150" font-size="12" fill="#55554e">arrêt de bus</text><text x="30" y="318" font-size="12" fill="#3d5a1c">rivière (schéma)</text></g>'
        '<circle cx="326" cy="118" r="9" fill="#3d5a1c" stroke="#fbf9f3" stroke-width="3"/><path d="M230 185v-34" stroke="#a8c66c" stroke-width="3" stroke-dasharray="2 5"/>'
        '<path d="M230 112v13" stroke="#a8c66c" stroke-width="5"/></svg>')


def salon(p, met, G):
    """Coiffeur, sans réservation en ligne (les salons ont déjà leur appli) : la page sert à être trouvé, montrer le travail, appeler ou écrire.
    Structure : hero « ciseaux qui coupent » (photo de salon assombrie ; les ciseaux découpent COUPE. COULEUR. SOIN. un mot à la fois) > ancres collantes > le salon > prestations (fourchettes d'exemple)
    > LE TRAVAIL : galerie qui défile au scroll (moment fort ; pas de paire de photos au même cadrage pour un avant/après) > horaires et venir (plan dessiné, itinéraire) > avis (zone modèle) > contact (appeler / écrire).
    Interface : cadre de miroir à ampoules, ciseaux, peigne, ticket de cape."""
    B = met["page"]; X = contexte(p, met, G, CISEAUX); e = X.e
    nom, ville, label = X.nom, X.ville, met["label"]
    sep = '<div class="sep" aria-hidden="true"></div>'
    ch, cm = X.cr["coif-hero"], X.cr["coif-hero-m"]; X.photo("coif-hero"); X.photo("coif-hero-m")
    pre = (f'<link rel="preload" as="image" href="img/{e(cm["fichier"])}" media="(max-width:759px)" fetchpriority="high">\n<link rel="preload" as="image" href="img/{e(ch["fichier"])}" '
           f'imagesrcset="img/coif-hero-800.webp 800w, img/{e(ch["fichier"])} {ch["largeur"]}w" imagesizes="100vw" media="(min-width:760px)" fetchpriority="high">\n')
    media = (f'<div class="hero-media"><picture><source media="(max-width:759px)" srcset="img/{e(cm["fichier"])}" width="{cm["largeur"]}" height="{cm["hauteur"]}"><img src="img/{e(ch["fichier"])}" '
             f'srcset="img/coif-hero-800.webp 800w, img/{e(ch["fichier"])} {ch["largeur"]}w" sizes="100vw" alt="{e(ch["alt"])}" width="{ch["largeur"]}" height="{ch["hauteur"]}" fetchpriority="high" decoding="async"></picture></div>')
    mot = lambda i, t: f'<span class="mot m{i}"><span class="txt">{t}</span><span class="cc">{CUT}</span></span>'
    hero = (f'<section class="hero">{media}<div class="w hero-t"><h1><span class="kicker">{e(label)} à {e(ville)}</span>{mot(1, "Coupe.")}{mot(2, "Couleur.")}{mot(3, "Soin.")}</h1>'
            f'<p class="lead">{e(B["lead"])}</p><div class="cta">{X.appel("btn btn-main", "Appeler le " + X.aff_tel, CISEAUX)}<a class="btn btn-line" href="#contact"><span>Écrire un message</span></a></div>'
            f'<p class="exemple"><b>EXEMPLE</b> — ceci n\'est pas votre site : salon, prestations, prix, adresse et horaires fictifs, aucun avis réel. Photos libres de droits.</p>'
            f'<p class="cred">{X.credit("coif-hero")}</p></div></section>')
    ancres = (f'<nav class="ancres" aria-label="Sections de la page"><div class="w"><a href="#salon">Le salon</a><a href="#prestations">Prestations</a><a href="#travail">Le travail</a><a href="#venir">Venir</a>'
              f'<a href="#contact">Contact</a>{X.appel("btn btn-main", "Appeler", CISEAUX)}</div></nav>')
    trouvez = (f'<section class="infos" id="trouver" aria-label="Infos pratiques"><div class="w"><ul><li><small>Adresse</small>{e(B["adresse"])}</li>'
               f'<li><small>Horaires</small>Du mardi au samedi (exemple)</li><li><small>Téléphone</small><a href="tel:{X.tel_intl}">{X.aff_tel}</a></li></ul></div></section>')
    salon_s = (f'<section class="section salon" id="salon"><div class="w sal"><div><p class="eyebrow">{e(B["salon_t"])}</p><h2>{e(B["salon_h2"])}</h2>' + "".join(f"<p>{e(t)}</p>" for t in B["salon"]) +
               f'</div><figure class="sal-ph">{X.photo("coif-salon", "(min-width:900px) 45vw, 100vw")}<figcaption>{X.credit("coif-salon")}</figcaption></figure></div></section>')
    lignes = "".join(f'<li><span class="tn">{e(t["n"])}<small>{e(t["duree"])}</small></span><b>{e(t["p"].replace(" €", chr(0x202f) + "€"))}</b></li>' for t in B["tarifs"])
    tarifs = (f'<section class="section tarifs" id="prestations"><div class="w"><p class="eyebrow">{e(B["tarifs_t"])} {X.badge}</p><h2>Ce que fait le salon</h2><p class="sub">{e(B["tarifs_d"])}</p><ul class="liste">{lignes}</ul>'
              f'<div class="cta"><a class="btn btn-main" href="tel:{X.tel_intl}">{CISEAUX}<span>Un renseignement ? Appelez</span></a></div></div></section>')
    figs = []
    for i, k in enumerate(B["travail"]):
        figs.append(f'<li class="fig f{i}"><figure>{X.photo(k, "(min-width:900px) 30vw, 78vw")}<figcaption>{e(X.cr[k]["theme"].capitalize())} · Pexels, {e(X.cr[k]["auteur"])}</figcaption></figure></li>')
    travail = (f'<section class="travail" id="travail"><div class="pin"><div class="w"><p class="eyebrow">Réalisations {X.badge}</p><h2>{e(B["travail_t"])}</h2><p class="sub">{e(B["travail_d"])}</p></div>'
               f'<div class="piste" role="region" aria-label="Photos du travail, à faire défiler" tabindex="0"><ul class="rail">{"".join(figs)}</ul></div></div></section>')
    venir = (f'<section class="section venir" id="venir"><div class="w venir-g"><div><p class="eyebrow">Nous trouver</p><h2>{e(B["venir_t"])}</h2><p>{e(B["adresse"])}</p><p>{e(B["acces"])}</p>'
             f'<p><a class="tel-big" href="tel:{X.tel_intl}">{X.aff_tel}</a></p><p><a class="btn btn-line" href="{e(B["itineraire"])}" rel="noopener"><span>Itinéraire (carte du centre de Rouen)</span></a></p>{X.horaires(B["horaires"])}</div>'
             f'<figure class="plan">{PLAN}<figcaption>{e(B["plan_legende"])}</figcaption></figure></div></section>')
    avis = (f'<section class="section avis" id="avis"><div class="w"><p class="eyebrow">{e(B["avis_t"])} {X.badge}</p><h2>Ce qu\'en disent les clients</h2><div class="rev"><b>Ici s\'afficheront vos vrais avis Google</b>'
            f'<p>Les avis sont repris tels quels depuis la fiche Google, avec l\'accord de leurs auteurs. Aucun avis, aucune note n\'est inventé sur cette maquette.</p></div></div></section>')
    sujets = "".join(f"<option>{e(s)}</option>" for s in B["sujets"])
    champs = (f'<label for="f-nom">Votre nom<input id="f-nom" name="nom" autocomplete="name" required></label>'
              f'<label for="f-tel">Votre téléphone<input id="f-tel" name="tel" type="tel" autocomplete="tel" inputmode="tel" required></label>'
              f'<label for="f-sujet">Votre demande<select id="f-sujet" name="sujet">{sujets}</select></label>'
              f'<label for="f-msg">Votre message<textarea id="f-msg" name="message" rows="4"></textarea></label>')
    contact = (f'<section class="section contact" id="contact"><div class="w"><div><p class="eyebrow">Contact</p><h2>{e(B["contact_t"])}</h2><p class="sub">{e(B["contact_d"])}</p>'
               f'<p><a class="tel-big" href="tel:{X.tel_intl}">{X.aff_tel}</a></p><p>{e(B["adresse"])}</p></div>'
               + X.formulaire(champs, "Envoyer le message", "Votre numéro sert uniquement à vous rappeler.") + '</div></section>')
    titre = f"{nom} — salon de coiffure à {ville}"
    desc = f"Salon de coiffure à {ville} : coupe, couleur, soin. Découvrez le salon et son travail, trouvez l'adresse, appelez le {X.aff_tel} ou écrivez."
    ld = {"@context": "https://schema.org", "@type": met["schema"], "name": nom, "description": desc, "address": {"@type": "PostalAddress", "addressLocality": ville, "addressCountry": "FR"}, "telephone": X.tel_intl}
    haut = X.tete(titre, desc, ld, "#101111", "salon", ["Manrope-300-800.woff2"]).replace("<style>", pre + "<style>", 1)
    corps = f"""<body>
<a class="skip" href="#contact">Aller au contact</a>
<header class="entete"><div class="w"><a class="brand" href="#top">{e(nom)}{X.badge}</a>{X.appel("btn btn-main", "Appeler", CISEAUX)}</div></header>
<main id="top">
{hero}
{ancres}
{trouvez}
{salon_s}
{sep}
{tarifs}
{travail}
{venir}
{avis}
{contact}
"""
    page = haut + corps + X.pied(nom, ville, "salon de coiffure", '<a class="btn btn-line" href="#contact"><span>Écrire</span></a>', "salon.js")
    return X.finaliser(page, B)


BOURGEON = ('<svg class="bg" viewBox="0 0 28 28" width="26" height="26" aria-hidden="true" fill="currentColor" stroke="none">'
            '<g class="p2"><path d="M14 25C6 23 3 15 6 9 11 11 13.4 17 14 25Z"/></g><g class="p3"><path d="M14 25C22 23 25 15 22 9 17 11 14.6 17 14 25Z"/></g><g class="p1"><path d="M14 25C8.5 19 8.5 10 14 3 19.5 10 19.5 19 14 25Z"/></g></svg>')


def petale(p, met, G):
    """Fleuriste. Structure : bande étroite (photo de l'étal) avec la preuve en dessous > catalogue d'abord, en grille asymétrique > COMPOSEUR de commande (moment fort : la photo change,
    le prix d'exemple se calcule) > atelier et boutique > avis (zone modèle) > commande. Navigation réduite à l'appel et à la commande. Interface : bourgeon qui s'ouvre, carton à ficelle, tige à feuilles."""
    B = met["page"]; X = contexte(p, met, G, BOURGEON); e = X.e
    nom, ville, label = X.nom, X.ville, met["label"]
    eur = lambda n: f"{n} €"
    comps = B["compositions"]; tailles = B["tailles"]
    bande = (f'<section class="bande"><figure>{X.photo("fleur-bande", "100vw", "50% 55%", lazy=False)}</figure><div class="w"><h1><span class="kicker">{e(label)} à {e(ville)}</span>Des fleurs, préparées pour vous.</h1></div></section>')
    preuve = ('<section class="preuve" aria-label="Infos pratiques"><div class="w"><ul>' + "".join(f"<li><small>{e(k)}</small>{e(v)}</li>" for k, v in B["preuve"]) + f'</ul>'
              f'<p class="exemple"><b>EXEMPLE</b> — ceci n\'est pas votre site : boutique, compositions, prix, adresse et horaires fictifs, aucun avis réel.</p></div></section>')
    cartes = "".join(
        f'<li class="carte c{i}"><figure>{X.photo(c["photo"], "(min-width:900px) 40vw, 100vw")}</figure><div class="cb"><h3>{e(c["n"])}</h3><p>{e(c["d"])}</p>'
        f'<p class="prix">À partir de <b>{eur(c["prix"][tailles[0]])}</b></p><a class="btn btn-line" href="#composeur" data-choisir="{e(c["id"])}"><span>Choisir cette composition</span></a></div></li>'
        for i, c in enumerate(comps))
    tg = B["tige"]
    cartes += (f'<li class="carte c4"><figure>{X.photo(tg["photo"], "(min-width:900px) 40vw, 100vw")}</figure><div class="cb"><h3>{e(tg["n"])}</h3><p>{e(tg["d"])}</p>'
               f'<p class="prix"><b>{e(tg["p"].replace(" €", chr(0x202f) + "€"))}</b></p></div></li>')
    catalogue = (f'<section class="section catalogue" id="compositions"><div class="w"><p class="eyebrow">Catalogue {X.badge}</p><h2>{e(B["catalogue_t"])}</h2><p class="sub">{e(B["catalogue_d"])}</p></div>'
                 f'<ul class="grille">{cartes}</ul></section>')
    sep = '<div class="sep" aria-hidden="true"></div>'
    radios = "".join(
        f'<label class="choix-c"><input type="radio" name="compo" value="{e(c["id"])}" data-nom="{e(c["n"])}"{" checked" if i == 0 else ""}><span class="vig">{X.photo(c["photo"], "120px")}</span><span class="nm">{e(c["n"])}</span></label>'
        for i, c in enumerate(comps))
    apercus = "".join(f'<figure class="ap{" on" if i == 0 else ""}" data-id="{e(c["id"])}">{X.photo(c["photo"], "(min-width:900px) 45vw, 100vw")}</figure>' for i, c in enumerate(comps))
    tailles_html = "".join(
        f'<label class="choix-t"><input type="radio" name="taille" value="{e(t)}"{" checked" if t == tailles[1] else ""}><span><b>{e(t)}</b><small>{e(B["tailles_d"][t])}</small></span></label>' for t in tailles)
    prix_js = json.dumps({c["id"]: c["prix"] for c in comps}, ensure_ascii=False)
    composeur = (f'<section class="section composeur" id="composeur" data-prix=\'{e(prix_js)}\'><div class="w comp"><div class="apercu">{apercus}</div><div><p class="eyebrow">Commande {X.badge}</p><h2>{e(B["composeur_t"])}</h2><p class="sub">{e(B["composeur_d"])}</p>'
                 f'<fieldset><legend>1. La composition</legend><div class="choix-grid">{radios}</div></fieldset>'
                 f'<fieldset><legend>2. La taille</legend><div class="tailles">{tailles_html}</div></fieldset>'
                 f'<p class="recap" id="recap" role="status" aria-live="polite">{e(comps[0]["n"])} · {tailles[1]} · {eur(comps[0]["prix"][tailles[1]])} (prix d\'exemple)</p>'
                 f'<div class="cta">{X.appel("btn btn-main", "Commander par téléphone : " + X.aff_tel, BOURGEON)}<a class="btn btn-line" href="#commande"><span>Passer la commande en ligne</span></a></div></div></div></section>')
    atelier = (f'<section class="section atelier" id="boutique"><div class="w atl"><figure class="atl-ph">{X.photo("fleur-vitrine", "(min-width:900px) 50vw, 100vw")}<figcaption>{X.credit("fleur-vitrine")}</figcaption></figure>'
               f'<div><p class="eyebrow">Nous trouver</p><h2>{e(B["atelier_t"])}</h2><p>{e(B["atelier"])}</p><p>{e(B["adresse"])}</p><p>{e(B["acces"])}</p>'
               f'<p><a class="tel-big" href="tel:{X.tel_intl}">{X.aff_tel}</a></p>{X.horaires(B["horaires"])}</div></div></section>')
    avis = ('<section class="section avis" id="avis"><div class="w"><p class="eyebrow">Avis</p><h2>Ce qu\'en disent les clients</h2>'
            '<div class="rev"><b>Vos avis Google réels s\'afficheront ici</b><p>Les avis sont repris tels quels depuis la fiche Google, avec l\'accord de leurs auteurs. Aucun avis, aucune note n\'est inventé.</p></div></div></section>')
    champs = (f'<label for="f-nom">Votre nom<input id="f-nom" name="nom" autocomplete="name" required></label>'
              f'<label for="f-tel">Votre téléphone<input id="f-tel" name="tel" type="tel" autocomplete="tel" inputmode="tel" required></label>'
              f'<label for="f-date">Date de retrait<input id="f-date" name="date" type="date" required></label>'
              f'<label for="f-compo">Votre composition<input id="f-compo" name="composition" readonly placeholder="Choisissez dans le composeur"></label>')
    commande = (f'<section class="section commande" id="commande"><div class="w"><div><p class="eyebrow">Commande</p><h2>On prépare, vous passez le chercher</h2>'
                f'<p class="sub">Quatre informations, puis un appel de confirmation sous <mark class="todo">délai à confirmer</mark>.</p></div>'
                + X.formulaire(champs, "Envoyer ma commande", "Votre numéro sert uniquement à confirmer la commande.") + '</div></section>')
    titre = f"{nom} — fleuriste à {ville}"
    desc = f"Fleuriste à {ville} : bouquets, compositions sur commande, fleurs à la tige. Commandez en ligne ou appelez le {X.aff_tel}."
    ld = {"@context": "https://schema.org", "@type": met["schema"], "name": nom, "description": desc, "address": {"@type": "PostalAddress", "addressLocality": ville, "addressCountry": "FR"}, "telephone": X.tel_intl}
    haut = X.tete(titre, desc, ld, "#17301f", "petale", ["Figtree-400-700.woff2"])
    corps = f"""<body>
<a class="skip" href="#composeur">Aller au composeur de commande</a>
<header class="entete"><div class="w"><a class="brand" href="#top">{e(nom)}{X.badge}</a><div class="actions">{X.appel("btn btn-main", "Appeler", BOURGEON)}<a class="btn btn-line" href="#composeur"><span>Commander</span></a></div></div></header>
<main id="top">
{bande}
{preuve}
{catalogue}
{sep}
{composeur}
{atelier}
{sep}
{avis}
{commande}
"""
    page = haut + corps + X.pied(nom, ville, "fleuriste", '<a class="btn btn-line" href="#composeur"><span>Commander</span></a>', "petale.js")
    return X.finaliser(page, B)


PAIN = ('<svg class="pn" viewBox="0 0 32 24" width="28" height="22" aria-hidden="true" fill="currentColor"><path d="M3 20C1.5 11 8 3 16 3s14.500 8 13 17c0 1-.8 1.5-1.800 1.500H4.800C3.800 21.500 3 21 3 20Z"/>'
        '<g stroke="#fbf6ec" stroke-width="2" stroke-linecap="round" fill="none"><path d="M9 14 12 8M15 15l3-7M21 14l3-6"/></g></svg>')


def fournil(p, met, G):
    """Boulangerie. Structure : hero plein écran photo > PREUVE D'ABORD (« ouvert maintenant », prochaine fournée, journée en frise : moment fort) > produits en cartes à défilement horizontal
    > du fournil au comptoir (3 étapes) > nous trouver > réserver un pain. Navigation : barre fixe. Sections courtes et denses. Interface : toile de lin, pain qui lève, tampon de farine, crantage de lame."""
    B = met["page"]; X = contexte(p, met, G, PAIN); e = X.e
    nom, ville, label = X.nom, X.ville, met["label"]
    sep = '<div class="sep" aria-hidden="true"></div>'
    hm = lambda t: t.replace(":", " h ").replace(" h 00", " h").replace("h 0", "h ").replace(" h  ", " h ") if t else ""
    def aff(t): h, m = t.split(":"); return f"{int(h)} h" + (f" {m}" if m != "00" else "")
    lignes = []
    for i, (j, o, f) in enumerate(B["horaires"]):
        lignes.append(f'<tr data-j="{(i + 1) % 7}" data-o="{o or ""}" data-f="{f or ""}"><th scope="row">{e(j)}</th><td>{e(aff(o) + " – " + aff(f)) if o else "Fermé"}</td></tr>')
    table = f'<table class="hor" id="horaires-t"><caption>Horaires d\'ouverture {X.badge}</caption><tbody>{"".join(lignes)}</tbody></table>'
    repères = "".join(f'<li data-h="{h}"><b>{e(aff(h))}</b><span>{e(t)}</span></li>' for h, t in B["fournees"])
    marques = "".join(f'<i style="left:{(int(h[:2]) * 60 + int(h[3:]) - 360) / 840 * 100:.1f}%"></i>' for h, _ in B["fournees"])
    aujourdhui = (f'<section class="auj" id="aujourdhui" aria-labelledby="t-auj"><div class="w"><div class="auj-c"><p class="eyebrow" id="t-auj">Aujourd\'hui {X.badge}</p>'
                  f'<p class="etat" id="etat" role="status" aria-live="polite">Horaires d\'ouverture : voir le tableau plus bas.</p><p class="prochaine" id="prochaine">Trois fournées par jour.</p>'
                  f'<div class="jour"><div class="piste" aria-hidden="true">{marques}<span class="curseur" id="curseur"></span></div><ol class="fournees" id="fournees">{repères}</ol></div>'
                  f'<p class="note-j">{e(B["aujourdhui_d"])}</p><div class="cta">{X.appel("btn btn-main", "Appeler le " + X.aff_tel, PAIN)}<a class="btn btn-line" href="#commande"><span>Réserver un pain</span></a></div></div></div></section>')
    cartes = "".join(
        f'<li class="pc"><figure>{X.photo(c["photo"], "(min-width:900px) 320px, 78vw")}</figure><div class="cb"><h3>{e(c["n"])}<b>{e(c["p"].replace(" €", chr(0x202f) + "€"))}</b></h3><p>{e(c["d"])}</p><p class="al">Allergènes : {e(c["a"])}</p></div></li>'
        for c in B["produits"])
    produits = (f'<section class="section produits" id="produits"><div class="w"><p class="eyebrow">Carte des produits {X.badge}</p><h2>{e(B["produits_t"])}</h2><p class="sub">{e(B["produits_d"])}</p></div>'
                f'<div class="rail" role="region" aria-label="Produits, à faire défiler" tabindex="0"><ul>{cartes}</ul></div></section>')
    etapes = "".join(f'<li class="et"><figure>{X.photo(s["photo"], "(min-width:900px) 30vw, 100vw")}</figure><h3>{e(s["n"])}</h3><p>{e(s["d"])}</p></li>' for s in B["fabrication"])
    fabrication = f'<section class="section fab" id="fabrication"><div class="w"><p class="eyebrow">Fabrication</p><h2>{e(B["fabrication_t"])}</h2><ol class="etapes">{etapes}</ol></div></section>'
    lieu = (f'<section class="section lieu" id="trouver"><div class="w lieu-g"><div><p class="eyebrow">Nous trouver</p><h2>Au centre de Rouen</h2><p>{e(B["adresse"])}</p><p>{e(B["acces"])}</p>'
            f'<p><a class="tel-big" href="tel:{X.tel_intl}">{X.aff_tel}</a></p></div><div>{table}</div></div></section>')
    avis = ('<section class="section avis" id="avis"><div class="w"><p class="eyebrow">Avis</p><h2>Ce qu\'en disent les clients</h2><div class="rev"><b>Vos avis Google réels s\'afficheront ici</b>'
            '<p>Les avis sont repris tels quels depuis la fiche Google, avec l\'accord de leurs auteurs. Aucun avis, aucune note n\'est inventé.</p></div></div></section>')
    opt = lambda l: "".join(f"<option>{e(o)}</option>" for o in l)
    champs = (f'<label for="f-nom">Votre nom<input id="f-nom" name="nom" autocomplete="name" required></label>'
              f'<label for="f-tel">Votre téléphone<input id="f-tel" name="tel" type="tel" autocomplete="tel" inputmode="tel" required></label>'
              f'<label for="f-produit">Produit<select id="f-produit" name="produit">{opt(B["produits_select"])}</select></label>'
              f'<label for="f-jour">Retrait<select id="f-jour" name="jour">{opt(B["jours_select"])}</select></label>')
    commande = (f'<section class="section commande" id="commande"><div class="w"><div><p class="eyebrow">Commande</p><h2>{e(B["commande_t"])}</h2><p class="sub">{e(B["commande_d"])} Confirmation par téléphone sous <mark class="todo">délai à confirmer</mark>.</p></div>'
                + X.formulaire(champs, "Mettre de côté", "Votre numéro sert uniquement à confirmer la commande.") + '</div></section>')
    titre = f"{nom} — boulangerie à {ville}"
    desc = f"Boulangerie à {ville} : horaires du jour, prochaine fournée, pains et viennoiseries. Réservez un pain ou appelez le {X.aff_tel}."
    ld = {"@context": "https://schema.org", "@type": met["schema"], "name": nom, "description": desc, "address": {"@type": "PostalAddress", "addressLocality": ville, "addressCountry": "FR"}, "telephone": X.tel_intl}
    haut = X.tete(titre, desc, ld, "#2b1a0e", "fournil", ["Figtree-400-700.woff2"])
    cm, c = X.cr["boul-hero-m"], X.cr["boul-hero"]; X.photo("boul-hero-m"); X.photo("boul-hero")
    hero_img = (f'<picture><source media="(max-width:759px)" srcset="img/{e(cm["fichier"])}" width="{cm["largeur"]}" height="{cm["hauteur"]}"><img src="img/{e(c["fichier"])}" srcset="img/boul-hero-800.webp 800w, img/{e(c["fichier"])} {c["largeur"]}w" '
                f'sizes="100vw" alt="{e(c["alt"])}" width="{c["largeur"]}" height="{c["hauteur"]}" fetchpriority="high" decoding="async"></picture>')
    pre = (f'<link rel="preload" as="image" href="img/{e(cm["fichier"])}" media="(max-width:759px)" fetchpriority="high">\n<link rel="preload" as="image" href="img/{e(c["fichier"])}" '
           f'imagesrcset="img/boul-hero-800.webp 800w, img/{e(c["fichier"])} {c["largeur"]}w" imagesizes="100vw" media="(min-width:760px)" fetchpriority="high">\n')
    haut = haut.replace("<style>", pre + "<style>", 1)
    corps = f"""<body>
<a class="skip" href="#aujourdhui">Aller aux horaires du jour</a>
<header class="barre"><div class="w"><a class="brand" href="#top">{e(nom)}{X.badge}</a><nav class="liens" aria-label="Sections"><a href="#aujourdhui">Aujourd'hui</a><a href="#produits">Produits</a><a href="#fabrication">Fabrication</a><a href="#trouver">Nous trouver</a></nav>{X.appel("btn btn-main", "Appeler", PAIN)}</div></header>
<main id="top">
<section class="hero"><div class="hero-media">{hero_img}</div><div class="w hero-t"><h1><span class="kicker">{e(label)} à {e(ville)}</span>Le pain sort du four toute la journée.</h1><p class="lead">{e(B["lead"])}</p>
<p class="exemple"><b>EXEMPLE</b> — ceci n'est pas votre site : boulangerie, produits, prix, adresse et horaires fictifs, aucun avis réel. Photos libres de droits.</p><p class="cred">{X.credit("boul-hero")}</p></div></section>
{aujourdhui}
{produits}
{sep}
{fabrication}
{lieu}
{avis}
{commande}
"""
    page = haut + corps + X.pied(nom, ville, "boulangerie", '<a class="btn btn-line" href="#commande"><span>Réserver</span></a>', "fournil.js")
    return X.finaliser(page, B)


CLE = ('<svg class="cle" viewBox="0 0 28 28" width="24" height="24" aria-hidden="true" fill="currentColor"><g transform="rotate(-45 14 14)"><rect x="12" y="10" width="4" height="17" rx="2"/>'
       '<path d="M8.500 2.500h3.200V8h4.600V2.500h3.200V9a5.500 5.500 0 0 1-11 0Z"/></g></svg>')


def garage(p, met, G):
    """Garage automobile. Structure : hero en écran partagé (texte et appel / photo de l'atelier) > OFFRE D'ABORD : interventions en bandes alternées pleine largeur > DEVIS PAR TYPE D'INTERVENTION
    (moment fort, au milieu : cases à cocher, prix indicatif d'exemple calculé) > planning de rendez-vous en lignes > atelier et horaires > avis (zone modèle) > demande. Navigation : ancres collantes en jauge.
    Interface : clé à molette (bouton), plaque de tôle à rivets, damier (séparateurs et étiquette), jauge de tableau de bord (navigation)."""
    B = met["page"]; X = contexte(p, met, G, CLE); e = X.e
    nom, ville, label = X.nom, X.ville, met["label"]
    eur = lambda n: f"{n} €"
    inter = B["interventions"]
    sep = '<div class="sep" aria-hidden="true"></div>'
    ph = X.cr["garage-atelier"]; X.photo("garage-atelier")
    hero = (f'<section class="hero"><div class="hero-t"><h1><span class="kicker">{e(label)} à {e(ville)}</span>Un devis écrit, un créneau, une voiture suivie.</h1><p class="lead">{e(B["lead"])}</p>'
            f'<div class="cta">{X.appel("btn btn-main", "Appeler le " + X.aff_tel, CLE)}<a class="btn btn-line" href="#devis-type"><span>Composer mon devis</span></a></div>'
            f'<p class="exemple"><b>EXEMPLE</b> — ceci n\'est pas votre site : garage, interventions, prix, adresse et horaires fictifs, aucun avis réel. Photos libres de droits.</p></div>'
            f'<figure class="hero-p"><img src="img/{e(ph["fichier"])}" srcset="img/garage-atelier-800.webp 800w, img/{e(ph["fichier"])} {ph["largeur"]}w" sizes="(min-width:900px) 50vw, 100vw" alt="{e(ph["alt"])}" '
            f'width="{ph["largeur"]}" height="{ph["hauteur"]}" fetchpriority="high" decoding="async"><figcaption>{X.credit("garage-atelier")}</figcaption></figure></section>')
    pre = (f'<link rel="preload" as="image" href="img/{e(ph["fichier"])}" imagesrcset="img/garage-atelier-800.webp 800w, img/{e(ph["fichier"])} {ph["largeur"]}w" imagesizes="(min-width:900px) 50vw, 100vw" fetchpriority="high">\n')
    ancres = (f'<nav class="jauge" aria-label="Sections de la page"><div class="w"><a href="#interventions">Interventions</a><a href="#devis-type">Devis</a><a href="#rendez-vous">Rendez-vous</a><a href="#atelier">Atelier</a>'
              f'{X.appel("btn btn-main", "Appeler", CLE)}</div></nav>')
    bandes = "".join(
        f'<article class="bande b{i % 2}"><div class="w bd"><figure>{X.photo(s["photo"], "(min-width:900px) 45vw, 100vw")}</figure><div class="bt"><p class="eyebrow">Intervention {X.badge}</p><h3>{e(s["n"])}</h3><p>{e(s["d"])}</p>'
        f'<ul class="meta"><li>Durée indicative : <b>{e(s["duree"])}</b></li><li>À partir de <b>{eur(s["prix"])}</b>, hors pièces</li></ul><a class="btn btn-line" href="#devis-type" data-ajouter="{e(s["id"])}"><span>Ajouter au devis</span></a></div></div></article>'
        for i, s in enumerate([s for s in inter if s["bande"]]))
    offre = f'<section class="offre" id="interventions"><div class="w"><p class="eyebrow">Offre</p><h2>{e(B["services_t"])}</h2><p class="sub">{e(B["services_d"])}</p></div>{bandes}</section>'
    cases = "".join(
        f'<li><label class="cb"><input type="checkbox" name="inter" value="{e(s["id"])}" data-n="{e(s["n"])}"><span class="ck"></span><span class="nm">{e(s["n"])}<small>{e(s["duree"])}</small></span><b>{eur(s["prix"])}</b></label></li>' for s in inter)
    prix_js = json.dumps({s["id"]: s["prix"] for s in inter}, ensure_ascii=False)
    devis = (f'<section class="section devis" id="devis-type" data-prix=\'{e(prix_js)}\'><div class="w"><p class="eyebrow">Devis {X.badge}</p><h2>{e(B["devis_t"])}</h2><p class="sub">{e(B["devis_d"])}</p>'
             f'<div class="dv"><fieldset><legend>Interventions souhaitées</legend><ul class="cases">{cases}</ul></fieldset><aside class="total" aria-live="polite"><p class="tl">Prix indicatif d\'exemple</p>'
             f'<p class="tot" id="tot">0 €</p><p class="det" id="det">Cochez au moins une intervention.</p><a class="btn btn-main" href="#demande">{CLE}<span>Demander ce devis</span></a></aside></div></div></section>')
    lignes = []
    for j in B["jours"]:
        sl = []
        for h in B["heures"]:
            if [j, h] in B["fermes"]: sl.append(f'<li class="slot ferme"><span>fermé</span></li>')
            elif [j, h] in B["complets"]: sl.append(f'<li class="slot complet"><button type="button" disabled aria-label="{e(j)} {e(h)} : complet">{e(h)}</button></li>')
            else: sl.append(f'<li class="slot"><button type="button" data-j="{e(j)}" data-h="{e(h)}" aria-pressed="false" aria-label="{e(j)} {e(h)}">{e(h)}</button></li>')
        lignes.append(f'<div class="ligne"><h3>{e(j)}</h3><ul>{"".join(sl)}</ul></div>')
    rdv = (f'<section class="section rdv" id="rendez-vous"><div class="w"><p class="eyebrow">Rendez-vous {X.badge}</p><h2>{e(B["rdv_t"])}</h2><p class="sub">{e(B["rdv_d"])}</p><div class="planning">{"".join(lignes)}</div>'
           f'<p class="choix" id="choix" role="status" aria-live="polite">Aucun créneau choisi.</p></div></section>')
    atelier = (f'<section class="section atelier" id="atelier"><div class="w at"><figure>{X.photo("garage-outils", "(min-width:900px) 45vw, 100vw")}<figcaption>{X.credit("garage-outils")}</figcaption></figure>'
               f'<div><p class="eyebrow">Nous trouver</p><h2>{e(B["lieu_t"])}</h2><p>{e(B["lieu"])}</p><p>{e(B["adresse"])}</p><p>{e(B["acces"])}</p><p><a class="tel-big" href="tel:{X.tel_intl}">{X.aff_tel}</a></p>{X.horaires(B["horaires"])}</div></div></section>')
    avis = ('<section class="section avis" id="avis"><div class="w"><p class="eyebrow">Avis</p><h2>Ce qu\'en disent les clients</h2><div class="rev"><b>Vos avis Google réels s\'afficheront ici</b>'
            '<p>Les avis sont repris tels quels depuis la fiche Google, avec l\'accord de leurs auteurs. Aucun avis, aucune note n\'est inventé.</p></div></div></section>')
    champs = (f'<label for="f-nom">Votre nom<input id="f-nom" name="nom" autocomplete="name" required></label>'
              f'<label for="f-tel">Votre téléphone<input id="f-tel" name="tel" type="tel" autocomplete="tel" inputmode="tel" required></label>'
              f'<label for="f-veh">Marque et modèle du véhicule<input id="f-veh" name="vehicule" required></label>'
              f'<label for="f-dem">Votre demande<input id="f-dem" name="demande" readonly placeholder="Cochez des interventions et choisissez un créneau"></label>')
    demande = (f'<section class="section demande" id="demande"><div class="w"><div><p class="eyebrow">Demande</p><h2>On vous rappelle avec le devis</h2><p class="sub">Quatre informations, puis un appel de confirmation sous <mark class="todo">délai à confirmer</mark>.</p></div>'
               + X.formulaire(champs, "Envoyer ma demande", "Votre numéro sert uniquement à vous rappeler.") + '</div></section>')
    titre = f"{nom} — garage automobile à {ville}"
    desc = f"Garage automobile à {ville} : entretien, freins, pneus, diagnostic. Composez votre devis, choisissez un créneau ou appelez le {X.aff_tel}."
    ld = {"@context": "https://schema.org", "@type": met["schema"], "name": nom, "description": desc, "address": {"@type": "PostalAddress", "addressLocality": ville, "addressCountry": "FR"}, "telephone": X.tel_intl}
    haut = X.tete(titre, desc, ld, "#15181b", "garage", ["Barlow-500.woff2"]).replace("<style>", pre + "<style>", 1)
    corps = f"""<body>
<a class="skip" href="#devis-type">Aller au devis</a>
<header class="entete"><div class="w"><a class="brand" href="#top">{e(nom)}{X.badge}</a></div></header>
<main id="top">
{hero}
{ancres}
{offre}
{sep}
{devis}
{rdv}
{atelier}
{avis}
{demande}
"""
    page = haut + corps + X.pied(nom, ville, "garage automobile", '<a class="btn btn-line" href="#devis-type"><span>Devis</span></a>', "garage.js")
    return X.finaliser(page, B)
