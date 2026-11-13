#!/usr/bin/env python3
"""Site vitrine de Liam Emo (LM MULTI-SERVICES) : création de sites pour artisans et commerces.
Génère index.html, mentions-legales.html et confidentialite.html à côté de ce fichier.
Lit agents/identite.json : téléphone et e-mail vides = « À COMPLÉTER » bien visible. Relancer après chaque changement.
  python sites/agence/build.py
Ne publie rien : le déploiement Vercel se fait seulement avec l'accord de Liam."""
import html, json, re
from pathlib import Path

ICI = Path(__file__).resolve().parent
ID = json.loads((ICI.parent.parent / "agents" / "identite.json").read_text(encoding="utf-8"))
NOM, ENTREPRISE = ID.get("prenom_nom") or "Liam Emo", ID.get("entreprise") or "LM MULTI-SERVICES"
brut = re.sub(r"\D", "", ID.get("siret") or "")
SIRET = " ".join([brut[:3], brut[3:6], brut[6:9], brut[9:]]) if len(brut) == 14 else ""
DATE_MAJ = "26 octobre 2026"
EXEMPLES = "https://b2b-demos.vercel.app"
EX_PLOMBIER = "https://exemple-plombier-phi.vercel.app/"
e = html.escape


def a_completer(): return '<mark class="todo">À COMPLÉTER</mark>'


def messenger():
    page = (ID.get("facebook_page") or "").strip()
    if re.match(r"https?://(?:www\.)?m\.me/[^/?#]+/?$", page): return page.rstrip("/")
    m = re.match(r"https?://(?:www\.)?facebook\.com/([^/?#]+)/?$", page)
    return f"https://m.me/{m.group(1)}" if m else None


MESSENGER = messenger()


def tel():
    t = re.sub(r"\D", "", ID.get("telephone") or "")
    if t.startswith("33") and len(t) == 11: t = "0" + t[2:]
    if len(t) != 10 or not t.startswith("0"): return None, None
    return " ".join(t[i:i + 2] for i in range(0, 10, 2)), "+33" + t[1:]


TEL, TEL_INTL = tel()
MAIL = (ID.get("email_reponse") or "").strip() if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", (ID.get("email_reponse") or "").strip()) else ""
lien_tel = f'<a href="tel:{TEL_INTL}">{TEL}</a>' if TEL else a_completer()
lien_mail = f'<a href="mailto:{e(MAIL)}">{e(MAIL)}</a>' if MAIL else a_completer()

RDV_URL = (ID.get("rdv_url") or "").strip()
if not re.match(r"^https?://", RDV_URL): RDV_URL = ""
MSG_BTN = f'<a class="btn btn-line" href="{e(MESSENGER)}" target="_blank" rel="noopener">Écrire sur Messenger</a>' if MESSENGER else ""
RDV_BTN = f'<a class="btn btn-main" href="{e(RDV_URL)}" target="_blank" rel="noopener">Réserver un appel de 15 min</a>' if RDV_URL else ""
RDV_HREF = e(RDV_URL) if RDV_URL else (("" ) + "#contact")
siret_txt = SIRET or a_completer()
# forme juridique et zone (pas d'adresse postale précise : choix de Liam, 12/11/2026)
FORME = (ID.get("forme_juridique") or "").strip()
ADRESSE = (ID.get("adresse") or "").strip()
forme_txt = e(FORME) if FORME else a_completer()
adresse_txt = e(ADRESSE) if ADRESSE else a_completer()
# le domaine lmlsmulti-services.com est hébergé chez Netlify (adresse : conditions d'utilisation Netlify, vérifiée le 12/11/2026)
HEBERGEUR = 'Netlify, Inc., 101 2nd Street, San Francisco, CA 94105, États-Unis. Site : <a href="https://www.netlify.com" rel="noopener">netlify.com</a>.'
HEBERGEUR_COURT = "Netlify, Inc., États-Unis"
DATE_LEGAL = "12 novembre 2026"

ICO = {
    "ok": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    "ext": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 17L17 7M9 7h8v8" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    "tel": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 1.9.7 2.8a2 2 0 0 1-.5 2.1L8 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.7 2z" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    "mail": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 6h18v12H3zM3 7l9 6 9-6" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/></svg>',
}

NAV = [("exemples", "Exemples"), ("offres", "Offre"), ("deroule", "Déroulé"), ("faq", "Questions"), ("contact", "Contact")]


def titre_anime(lignes, niveau="h2"):
    if isinstance(lignes, str): lignes = [lignes]
    spans = "".join(f'<span class="ligne"><span>{e(l)}</span></span>' for l in lignes)
    return f'<{niveau} class="titre-anime">{spans}</{niveau}>'


def num(n):
    return f'<span class="num-contour" aria-hidden="true">{n:02d}</span>'


def tete(titre, desc, racine=True, chemin="/"):
    liens = "".join(f'<a href="{"" if racine else "/"}#{i}">{t}</a>' for i, t in NAV)
    rdv_href = RDV_HREF if (RDV_URL or racine) else "/#contact"
    rdv_cible = ' target="_blank" rel="noopener"' if RDV_URL else ""
    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(titre)}</title>
<meta name="description" content="{e(desc)}">
<meta name="robots" content="noindex, nofollow, noarchive">
<meta name="theme-color" content="#1b1f23">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="preload" href="/assets/polices/BricolageGrotesque-500-800.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/assets/polices/HankenGrotesk-400-700.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/assets/style.css">
</head>
<body>
<a class="skip" href="#contenu">Aller au contenu</a>
<header class="top"><div class="w">
  <a class="brand" href="/"><span class="mark" aria-hidden="true">LM</span><span><b>{e(NOM)}</b><small>{e(ENTREPRISE)} · création de sites</small></span></a>
  <nav class="nav-d" aria-label="Navigation principale">{liens}</nav>
  <a class="btn btn-main btn-s" href="{rdv_href}"{rdv_cible}>Réserver un appel</a>
  <details class="menu"><summary>Menu</summary><nav aria-label="Menu mobile">{liens}</nav></details>
</div></header>
<main id="contenu">
"""


def pied():
    return f"""</main>
<footer><div class="w">
  <div><p class="fb">{e(NOM)} · {e(ENTREPRISE)}</p><p>SIRET {siret_txt}</p><p>Création de sites pour artisans et commerces, à distance, partout en France.</p></div>
  <div><p><a href="/mentions-legales.html">Mentions légales</a></p><p><a href="/confidentialite.html">Confidentialité et droit d'opposition (STOP)</a></p></div>
</div></footer>
<script src="/assets/slider.js" defer></script>
</body>
</html>
"""


# ---------------------------------------------------------------- page d'accueil
def accueil():
    ld = {"@context": "https://schema.org", "@type": "ProfessionalService", "name": f"{ENTREPRISE} — {NOM}",
          "description": "Création de sites web pour artisans et commerces, à distance, partout en France.", "areaServed": {"@type": "Country", "name": "France"}}
    if TEL_INTL: ld["telephone"] = TEL_INTL
    if MAIL: ld["email"] = MAIL
    h = tete("Création de sites pour artisans et commerces — Liam Emo",
             "Je crée des sites clairs pour artisans et commerces : votre métier, votre zone, un numéro cliquable. À distance, partout en France. Page exemple gratuite avant de payer.")
    h = h.replace("</head>", f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>\n</head>')

    h += f"""<section class="hero"><div class="w hero-g">
  <div>
    <p class="eyebrow">{e(ENTREPRISE)} — création de sites</p>
    {titre_anime(["Qu'on vous trouve.", "Qu'on vous appelle."], "h1")}
    <p class="lead">Je suis {e(NOM)}, je construis des pages pour les artisans et commerçants de Normandie : trouvées sur Google, comprises en cinq secondes, avec un numéro qu'on touche du doigt. Vous voyez la vôtre avant de payer un centime.</p>
    <div class="cta"><a class="btn btn-main btn-lg" href="{RDV_HREF}"{' target="_blank" rel="noopener"' if RDV_URL else ""}>Réserver un appel de 15 min</a><a class="btn btn-line" href="#exemples">Voir des exemples</a></div>
  </div>
  <div class="aa-bloc">
    <div class="avant-apres" id="demo-aa">
      <div class="aa-avant" aria-hidden="true">
        <div class="aa-carte">
          <p class="aa-nom">Boîte à Outils Dupont</p>
          <p class="aa-etat">Aucun site internet trouvé</p>
          <p class="aa-tel">{ICO["tel"]}<span>02 XX XX XX XX</span></p>
        </div>
      </div>
      <div class="aa-apres"><img src="/assets/img/ex-plombier.jpg" width="900" height="620" alt="Capture de la page exemple d'un plombier chauffagiste : photo d'intervention, titre et bouton d'appel"></div>
      <div class="aa-trait" aria-hidden="true"></div>
      <label class="sr" for="aa-curseur">Faites glisser pour comparer : sans site, avec votre page</label>
      <input type="range" id="aa-curseur" class="aa-curseur" min="0" max="100" value="50">
      <noscript><style>.aa-curseur{{display:none}}</style></noscript>
    </div>
    <p class="aa-legendes"><span>Sans site</span><span>Avec votre page</span></p>
  </div>
</div></section>

<section class="section dark probleme"><div class="w">
  {num(1)}
  <p class="eyebrow">Le problème</p>
  {titre_anime("Vos clients vous cherchent. Ils trouvent le suivant sur la liste.")}
  <div class="probleme-g">
    <p class="lead">Sur son téléphone, votre client tape « plombier Rouen » ou « coiffeur Elbeuf ». Google lui montre une liste : les entreprises qui ont un site ouvrent une page avec vos horaires, vos photos, un numéro à toucher. Les autres restent une ligne grise, parfois sans numéro visible — et il appelle l'entreprise juste au-dessus. Ce n'est pas une question de talent : c'est une question de visibilité. Un bon artisan sans site perd des appels qu'il ne voit même pas partir.</p>
    <div class="photo-cadre"><img src="/assets/img/garage-atelier.webp" width="1125" height="900" loading="lazy" alt="Voiture surélevée sur un pont élévateur dans un atelier de mécanique"></div>
  </div>
</div></section>

<section class="section solution"><div class="w">
  {num(2)}
  <p class="eyebrow">La solution</p>
  {titre_anime("Une page trouvée sur Google, avec un bouton pour appeler")}
  <p class="intro">Une fiche d'établissement bien reliée à une page rapide : c'est ce qui fait apparaître votre nom en haut d'une recherche « plombier Rouen » ou « coiffeur Elbeuf ». Pas de blog à tenir, pas de logiciel à apprendre : vous gardez votre métier, je garde le site qui tourne.</p>
  <div class="solution-g">
    <div class="solution-photo-fixe"><div class="photo-cadre telephone-cadre"><img src="/assets/img/ex-electricien.jpg" width="900" height="620" loading="lazy" alt="Page exemple d'un électricien affichée sur un téléphone : fond graphite, titre et bouton d'appel ambre"></div></div>
    <ul class="solution-phrases">
      <li><p>Trouvée sur Google, pas seulement sur une carte de visite.</p></li>
      <li><p>Un numéro affiché en haut, cliquable, sur chaque écran.</p></li>
      <li><p>Une page qui s'affiche en moins de deux secondes, même en 4G.</p></li>
    </ul>
  </div>
</div></section>

<section class="section" id="exemples"><div class="w">
  {num(3)}
  <p class="eyebrow">Ce que ça donne, concrètement</p>
  {titre_anime("Trois métiers, trois pages, vues aujourd'hui")}
  <p class="intro">Ce sont des exemples : entreprises, numéros et chiffres fictifs. Cliquez, essayez le bouton d'appel, regardez sur votre téléphone : votre page aura ce niveau, avec vos informations et vos photos.</p>
  <div class="exemples">
    <article class="card ex"><img src="/assets/img/ex-plombier.jpg" width="900" height="620" loading="lazy" alt="Aperçu de la page exemple d'un plombier chauffagiste : photo d'intervention plein cadre, titre et bouton d'appel blanc"><div class="ex-t"><h3>Plombier chauffagiste</h3><p>Photo d'intervention en fond, un seul bouton d'appel, zone de travaux en texte clair.</p><a class="lien" href="{EX_PLOMBIER}" target="_blank" rel="noopener">Voir l'exemple {ICO["ext"]}<span class="sr"> (s'ouvre dans un nouvel onglet)</span></a></div></article>
    <article class="card ex"><img src="/assets/img/ex-electricien.jpg" width="900" height="620" loading="lazy" alt="Aperçu de la page exemple d'un électricien : fond graphite, ampoule allumée, bouton Appeler ambre"><div class="ex-t"><h3>Électricien</h3><p>Fond sombre, mise aux normes expliquée, devis chiffré avant le premier perçage.</p><a class="lien" href="{EXEMPLES}/atelier-lumiere-exemple-d80eb712/" target="_blank" rel="noopener">Voir l'exemple {ICO["ext"]}<span class="sr"> (s'ouvre dans un nouvel onglet)</span></a></div></article>
    <article class="card ex"><img src="/assets/img/ex-coiffeur.jpg" width="900" height="620" loading="lazy" alt="Aperçu de la page exemple d'un coiffeur : curseur avant/après sur une coupe, boutons Réserver et Appeler"><div class="ex-t"><h3>Coiffeur</h3><p>Curseur avant/après sur une coupe, prise de rendez-vous et appel en un geste.</p><a class="lien" href="{EXEMPLES}/atelier-ciseaux-cine-exemple-546e7247/" target="_blank" rel="noopener">Voir l'exemple {ICO["ext"]}<span class="sr"> (s'ouvre dans un nouvel onglet)</span></a></div></article>
  </div>
</div></section>

<section class="section dark" id="offres"><div class="w">
  {num(4)}
  <div class="offres-g">
    <div>
      <p class="eyebrow">L'offre</p>
      {titre_anime("Un seul prix, tout compris")}
      <p class="intro">Le prix est annoncé ici, avant tout paiement. La TVA applicable est précisée au moment du paiement.</p>
      <div class="card offre">
        <h3>Pack tout compris</h3>
        <p class="prix">595 €</p>
        <p class="sous">Une fois, puis 49 €/mois.</p>
        <ul class="checks">
          <li>{ICO["ok"]}<span>Le site : 1 page adaptée au téléphone, votre métier, votre ville, vos services, votre zone</span></li>
          <li>{ICO["ok"]}<span>Le nom de domaine, réservé avec vous, à votre nom</span></li>
          <li>{ICO["ok"]}<span>Une adresse e-mail professionnelle à votre nom de domaine</span></li>
          <li>{ICO["ok"]}<span>L'hébergement et la mise en ligne</span></li>
          <li>{ICO["ok"]}<span>La maintenance : textes, photos, horaires, sauvegarde</span></li>
          <li>{ICO["ok"]}<span>Une série de retouches incluse</span></li>
        </ul>
        <div class="cta offre-cta"><a class="btn btn-main" href="{RDV_HREF}"{' target="_blank" rel="noopener"' if RDV_URL else ""}>Réserver un appel de 15 min</a></div>
      </div>
    </div>
    <div class="photo-cadre offre-photo"><img src="/assets/img/plomb-robinets.webp" width="900" height="1200" loading="lazy" alt="Deux robinets d'arrêt chromés sortant d'un mur, dans une pièce en travaux"></div>
  </div>
</div></section>

<section class="section alt" id="deroule"><div class="w">
  {num(5)}
  <p class="eyebrow">Comment ça se passe</p>
  {titre_anime("Quatre étapes, dans cet ordre")}
  <div class="deroule-g">
    <ol class="etapes">
      <li><span class="n" aria-hidden="true">1</span><h3>Vous réservez l'appel de 15 minutes</h3><p>Par téléphone, à l'heure qui vous va : vous me dites votre métier et votre ville.</p></li>
      <li><span class="n" aria-hidden="true">2</span><h3>Vous recevez un devis et une page à votre nom</h3><p>Avec vos informations déjà en place, avant tout paiement de votre part.</p></li>
      <li><span class="n" aria-hidden="true">3</span><h3>Vous payez en ligne, quand vous êtes prêt</h3><p>Lien sécurisé, pour le montant annoncé sur cette page. Rien avant votre accord.</p></li>
      <li><span class="n" aria-hidden="true">4</span><h3>Le site est mis en ligne en quelques jours</h3><p>Domaine, e-mail professionnel et hébergement sont branchés, puis je vous préviens dès que tout est en ligne.</p></li>
    </ol>
    <div class="photo-cadre deroule-photo"><img src="/assets/img/coif-main.webp" width="1200" height="750" loading="lazy" alt="Mains qui tiennent une mèche de cheveux entre un peigne et des ciseaux"><p class="legende-photo">Vos vraies photos remplacent celles-ci dès le départ.</p></div>
  </div>
</div></section>

<section class="section" id="faq"><div class="w">
  {num(6)}
  <p class="eyebrow">Questions fréquentes</p>
  {titre_anime("Ce qu'on me demande souvent")}
  <div class="faq">
    <details><summary>Combien de temps pour avoir mon site ?</summary><p>En ligne en quelques jours après votre paiement. Le délai dépend surtout de la rapidité avec laquelle vous me donnez vos informations et vos photos.</p></details>
    <details><summary>Je n'ai pas de photos, est-ce un problème ?</summary><p>Non. Je mets des photos libres de droits à titre provisoire, clairement repérées. Vous me donnez les vôtres quand vous les avez, et je les remplace.</p></details>
    <details><summary>Pouvez-vous me garantir la première place sur Google ?</summary><p>Non, et personne ne peut le faire honnêtement. Je construis un site rapide, lisible sur téléphone, avec votre métier et votre ville bien écrits. Le reste dépend de beaucoup de choses.</p></details>
    <details><summary>Puis-je modifier mon site après la mise en ligne ?</summary><p>Une série de retouches est incluse à la livraison, et la maintenance (changements de textes, photos, horaires) fait partie du pack, chaque mois. Pour une modification plus importante, je vous annonce un prix avant de la faire.</p></details>
    <details><summary>Y aura-t-il des avis clients sur mon site ?</summary><p>Seulement de vrais avis, repris de votre fiche Google avec votre accord. S'il n'y en a pas, la section n'apparaît pas.</p></details>
    <details><summary>Comment se passe le paiement ?</summary><p>Vous recevez d'abord votre page exemple gratuite, sans engagement. Si elle vous plaît, je vous envoie un lien de paiement sécurisé : rien n'est débité avant que vous l'utilisiez vous-même.</p></details>
    <details><summary>Et le nom de domaine ?</summary><p>Il est inclus dans le pack : je le réserve avec vous, à votre nom, dès le départ.</p></details>
    <details><summary>Si je pars, est-ce que je garde mon domaine ?</summary><p>Oui. Il est réservé à votre nom depuis le premier jour : il reste le vôtre, quoi qu'il arrive.</p></details>
  </div>
</div></section>

<section class="section dark transition"><div class="w">
  {num(7)}
  <p class="phrase-geante">Taper votre nom sur Google doit donner une réponse. Pas un silence.</p>
</div></section>

<section class="section dark" id="contact"><div class="w contact">
  <div>
    <p class="eyebrow">Contact</p>
    <h2>Demandez votre page exemple, gratuite et à votre nom</h2>
    <p class="lead">Donnez-moi votre numéro et votre métier : je vous rappelle pour vous montrer votre page avant toute décision. Vous pouvez aussi m'écrire ou m'appeler directement.</p>
    <div class="cta">{RDV_BTN}{MSG_BTN}</div>
    <ul class="coord">
      <li><span class="ico">{ICO["tel"]}</span><div><small>Téléphone</small><b>{lien_tel}</b></div></li>
      <li><span class="ico">{ICO["mail"]}</span><div><small>E-mail</small><b>{lien_mail}</b></div></li>
    </ul>
  </div>
  <form class="card form-card" name="contact" method="POST" data-netlify="true" netlify-honeypot="bot-field" action="/merci.html">
    <input type="hidden" name="form-name" value="contact">
    <p hidden><label>Ne remplissez pas ce champ : <input name="bot-field" autocomplete="off" tabindex="-1"></label></p>
    <fieldset>
      <legend class="sr">Vos coordonnées pour être rappelé(e)</legend>
      <div class="paire">
        <div class="champ"><label for="c-nom">Nom</label><input id="c-nom" name="nom" type="text" autocomplete="name"></div>
        <div class="champ"><label for="c-tel">Téléphone <span aria-hidden="true">*</span><span class="sr"> (obligatoire)</span></label><input id="c-tel" name="telephone" type="tel" autocomplete="tel" required></div>
      </div>
      <div class="paire">
        <div class="champ"><label for="c-metier">Métier</label><input id="c-metier" name="metier" type="text"></div>
        <div class="champ"><label for="c-ville">Ville</label><input id="c-ville" name="ville" type="text" autocomplete="address-level2"></div>
      </div>
      <div class="champ"><label for="c-creneau">Créneau pour être rappelé(e)</label>
        <select id="c-creneau" name="creneau">
          <option value="">Peu importe</option>
          <option value="matin">Matin</option>
          <option value="midi">Midi</option>
          <option value="apres-midi">Après-midi</option>
          <option value="soir">Soir</option>
        </select>
      </div>
      <div class="champ"><label for="c-message">Message <span class="muted">(facultatif)</span></label><textarea id="c-message" name="message" rows="3"></textarea></div>
    </fieldset>
    <p class="consentement">En envoyant ce formulaire, vous acceptez que ces informations servent à vous rappeler. Voir la <a href="/confidentialite.html">politique de confidentialité</a>.</p>
    <button class="btn btn-main btn-lg" type="submit">Recevoir ma page exemple gratuite</button>
  </form>
</div></section>
<div class="barre-mobile" role="group" aria-label="Action rapide">
  <a class="btn btn-main" href="{RDV_HREF}"{' target="_blank" rel="noopener"' if RDV_URL else ""}>Réserver un appel</a>
</div>
"""
    return h + pied()


# ---------------------------------------------------------------- mentions légales
PROP_ANCIEN = f"""<p>Les textes et la mise en page de ce site sont la propriété de {e(NOM)}. Les pages présentées comme exemples sont des maquettes de démonstration : les entreprises, numéros et chiffres qu'elles contiennent sont fictifs. Les photos d'illustration de ces exemples sont des photos libres de droits (licence Unsplash), dont les auteurs sont indiqués sur chaque exemple. Les polices Bricolage Grotesque et Hanken Grotesk sont sous licence SIL Open Font 1.1 et hébergées avec le site.</p>"""
PROP_LUXE2 = f"""<p>Les textes et la mise en page de ce site sont la propriété de {e(NOM)}. Les pages présentées comme exemples sont des maquettes de démonstration : les entreprises, numéros et chiffres qu'elles contiennent sont fictifs. Les photos d'illustration de ces exemples sont des photos libres de droits, dont les auteurs sont indiqués sur chaque exemple. Les polices Archivo et IBM Plex Mono sont sous licence SIL Open Font 1.1 ; les bibliothèques GSAP, Lenis et three.js (licence MIT) sont hébergées avec le site. La scène 3D de la page d'accueil affiche une capture de la page exemple « Velin », coiffeur (entreprise fictive), réalisée par {e(ENTREPRISE)}. Les contours des départements viennent du projet france-geojson (données publiques IGN/Etalab, licence ouverte).</p>"""


def corps_mentions(propriete, racine="/"):
    return f"""<h1>Mentions légales</h1>
<p class="maj">Dernière mise à jour : {DATE_LEGAL}</p>
<h2>Éditeur du site</h2>
<dl class="fiche">
<dt>Nom</dt><dd>{e(NOM)}</dd>
<dt>Nom commercial</dt><dd>{e(ENTREPRISE)}</dd>
<dt>SIRET</dt><dd>{siret_txt}</dd>
<dt>Forme juridique</dt><dd>{forme_txt}</dd>
<dt>Adresse</dt><dd>{adresse_txt}</dd>
<dt>TVA</dt><dd>TVA non applicable, article 293 B du CGI</dd>
<dt>Téléphone</dt><dd>{lien_tel}</dd>
<dt>E-mail</dt><dd>{lien_mail}</dd>
<dt>Directeur de la publication</dt><dd>{e(NOM)}</dd>
</dl>
<h2>Hébergeur</h2>
<p>{HEBERGEUR}</p>
<h2>Propriété intellectuelle</h2>
{propriete}
<h2>Responsabilité</h2>
<p>Je m'efforce de fournir des informations exactes et à jour, sans garantie d'exhaustivité. Les liens vers des sites externes (par exemple les pages d'exemple) sont donnés à titre d'information : je ne contrôle pas leur contenu après leur publication.</p>
<h2>Données personnelles</h2>
<p>Voir la page <a href="{racine}confidentialite.html">Confidentialité et droit d'opposition</a>.</p>
"""


def mentions():
    h = tete("Mentions légales — Liam Emo, LM MULTI-SERVICES", "Mentions légales du site : éditeur, SIRET, hébergeur.", racine=False)
    h += '<article class="doc"><div class="w narrow">\n' + corps_mentions(PROP_ANCIEN) + "</div></article>\n"
    return h + pied()


# ---------------------------------------------------------------- confidentialité
def corps_confidentialite(formulaire):
    formulaire_ou = " ou utilisez le formulaire de contact de ce site," if formulaire else ","
    formulaire_phrase = " Le formulaire de contact est traité par le service Netlify Forms (mon hébergeur) pour me transmettre votre demande ; il n'est utilisé pour aucune autre fin." if formulaire else ""
    return f"""<h1>Politique de confidentialité</h1>
<p class="maj">Dernière mise à jour : {DATE_LEGAL}</p>
<h2>Qui est responsable de vos données</h2>
<p>{e(NOM)}, sous le nom {e(ENTREPRISE)}, SIRET {siret_txt}. Pour toute question : {lien_mail}.</p>
<h2>Ce site</h2>
<p>Ce site n'utilise aucun cookie, aucun traceur ni aucun outil de mesure d'audience. L'hébergeur ({HEBERGEUR_COURT}) enregistre des journaux techniques (adresse IP, date et page demandée) pour assurer la sécurité et le fonctionnement du service.</p>
<h2>Si vous me contactez</h2>
<p>Si vous m'écrivez, m'appelez{formulaire_ou} je traite les informations que vous me donnez (nom, téléphone, métier, ville, créneau souhaité, message, ou nom, entreprise, coordonnées et contenu de votre demande) uniquement pour vous rappeler, vous répondre, établir un devis et, si vous acceptez, réaliser votre site.{formulaire_phrase} La base légale est la demande de mesures précontractuelles puis l'exécution du contrat. Je conserve ces informations pendant la relation, puis jusqu'à 3 ans après le dernier échange si nous n'avons pas travaillé ensemble ; les pièces comptables sont conservées selon les durées légales.</p>
<p>Si vous payez en ligne, le paiement est assuré par un prestataire de paiement sécurisé. Je ne vois ni ne conserve votre numéro de carte.</p>
<h2 id="stop">Prospection et droit d'opposition : répondez STOP</h2>
<p>Je peux contacter des professionnels (artisans, commerçants) par e-mail ou par message professionnel pour leur proposer la création d'un site, en rapport avec leur activité. Dans ce cas :</p>
<ul>
<li>Je vous écris à votre adresse professionnelle ou sur votre profil professionnel, jamais à une adresse personnelle devinée.</li>
<li>Je vous indique qui je suis et d'où vient votre contact. Les sources sont publiques : annuaire officiel des entreprises, fiche publique de votre entreprise, site de votre entreprise.</li>
<li>La base légale est mon intérêt légitime à proposer un service lié à votre activité professionnelle.</li>
<li><strong>Vous pouvez vous y opposer à tout moment, gratuitement et sans justification : répondez simplement STOP</strong> à mon message, ou écrivez-moi à {lien_mail}.</li>
<li>Dès réception, je ne vous contacte plus jamais, par aucune voie. Je garde uniquement l'information minimale nécessaire pour ne pas vous recontacter (votre adresse et la date de votre opposition).</li>
</ul>
<h2>Vos droits</h2>
<p>Vous pouvez demander l'accès à vos données, leur rectification, leur effacement, la limitation de leur traitement, leur portabilité, et vous opposer à leur traitement. Écrivez-moi à {lien_mail}. Vous pouvez aussi saisir la CNIL : <a href="https://www.cnil.fr" rel="noopener">cnil.fr</a>.</p>
<h2>Destinataires</h2>
<p>Vos données ne sont ni vendues ni cédées. Elles peuvent être traitées par mon hébergeur, mon prestataire de messagerie et, si vous payez en ligne, mon prestataire de paiement, uniquement pour fournir le service.</p>
"""


def confidentialite():
    h = tete("Confidentialité et droit d'opposition — Liam Emo", "Politique de confidentialité : données collectées, droits, et droit d'opposition à la prospection (répondez STOP).", racine=False)
    h += '<article class="doc"><div class="w narrow">\n' + corps_confidentialite(True) + "</div></article>\n"
    return h + pied()


# ---------------------------------------------------------------- confirmation du formulaire
def merci():
    h = tete("Merci — Liam Emo, LM MULTI-SERVICES", "Votre demande de rappel a bien été envoyée.", racine=False)
    h += f"""<article class="doc"><div class="w narrow">
<h1>Merci, votre demande est envoyée</h1>
<p>Je vous rappelle au créneau que vous avez indiqué, ou dès que possible. Si c'est urgent, vous pouvez aussi m'appeler directement : {lien_tel}.</p>
<p><a class="btn btn-main" href="/">Retour à l'accueil</a></p>
</div></article>
"""
    return h + pied()


# ---------------------------------------------------------------- site luxe2 (pages légales et confirmation, mêmes données)
LUXE2 = ICI / "luxe2"
RDV_LUXE2 = RDV_URL or "https://calendar.app.google/kmCmw8PKKkK7pjMn6"

def luxe2_page(titre, desc, corps):
    contact = " · ".join(x for x in (lien_tel, lien_mail) if x).replace(" · ", "<br>")
    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(titre)}</title>
<meta name="description" content="{e(desc)}">
<meta name="robots" content="noindex, nofollow, noarchive">
<meta name="theme-color" content="#14110F">
<link rel="icon" href="assets/favicon.svg" type="image/svg+xml">
<link rel="preload" href="assets/polices/Archivo-var.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="assets/style.css">
</head>
<body class="legal">
<a class="saut" href="#contenu">Aller au contenu</a>

<header class="tete">
  <a class="marque" href="index.html" aria-label="{e(ENTREPRISE)}, retour à l'accueil">
    <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><path d="M4 3v18h7M13 21V3l4 8 4-8v18" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>
    <span>{e(ENTREPRISE)}</span>
  </a>
  <nav class="tete-nav" aria-label="Sections">
    <a href="index.html#recherche">La recherche</a>
    <a href="index.html#exemples">Exemples</a>
    <a href="index.html#offre">L'offre</a>
    <a href="#contact">Contact</a>
  </nav>
  <a class="bouton bouton-s" href="{e(RDV_LUXE2)}" target="_blank" rel="noopener">Réserver un appel<span class="vh"> de 15 minutes (s'ouvre dans un nouvel onglet)</span></a>
</header>

<main id="contenu">
<article class="doc">
{corps}</article></main>

<footer id="contact" class="pied">
  <div class="pied-in">
    <p class="pied-marque affiche">{e(ENTREPRISE)}</p>
    <p class="pied-qui">{e(NOM)} · sites pour artisans et commerçants</p>
    <div class="pied-cols">
      <div><p class="mono">Zone</p><p>Normandie&nbsp;: Seine-Maritime, Eure, Calvados, Manche, Orne. Rendez-vous par téléphone et par e-mail.</p></div>
      <div><p class="mono">Contact</p><p>{contact}</p></div>
      <div><p class="mono">Entreprise</p><p>SIRET {siret_txt}<br><a href="mentions-legales.html">Mentions légales</a> · <a href="confidentialite.html">Confidentialité</a></p></div>
    </div>
    <p class="mono pied-credits">Pages montrées&nbsp;: exemples LM, entreprises fictives, photos libres de droits créditées sur chaque exemple · Contours des départements&nbsp;: IGN via france-geojson</p>
  </div>
</footer>

</body>
</html>
"""

def luxe2_pages():
    pages = {
        "mentions-legales.html": luxe2_page(f"Mentions légales · {ENTREPRISE}", "Mentions légales du site : éditeur, SIRET, hébergeur.", corps_mentions(PROP_LUXE2, racine="")),
        "confidentialite.html": luxe2_page(f"Confidentialité · {ENTREPRISE}", "Politique de confidentialité : données, droits, et droit d'opposition à la prospection (répondez STOP).", corps_confidentialite(False)),
        "merci.html": luxe2_page(f"Merci · {ENTREPRISE}", "Votre demande a bien été envoyée.", f"<h1>Merci, votre demande est envoyée</h1>\n<p>Je vous rappelle dès que possible. Si c'est urgent, appelez-moi directement : {lien_tel}.</p>\n<p><a class=\"bouton\" href=\"index.html\">Retour à l'accueil</a></p>\n"),
    }
    for nom, h in pages.items(): (LUXE2 / nom).write_text(h, encoding="utf-8")
    return list(pages)


if __name__ == "__main__":
    for nom, f in (("index.html", accueil), ("mentions-legales.html", mentions), ("confidentialite.html", confidentialite), ("merci.html", merci)):
        (ICI / nom).write_text(f(), encoding="utf-8")
    manque = [x for x, v in (("téléphone", TEL), ("e-mail", MAIL), ("SIRET", SIRET), ("page Facebook (lien Messenger)", MESSENGER), ("forme juridique", FORME), ("adresse", ADRESSE)) if not v]
    print("4 pages écrites dans", ICI)
    print(len(luxe2_pages()), "pages légales écrites dans", LUXE2)
    if manque: print("  ! À COMPLÉTER dans agents/identite.json :", ", ".join(manque))
