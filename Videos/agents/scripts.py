#!/usr/bin/env python3
"""Agent videos-scripts (équipe Vidéos TikTok, 16/11/2026) : Qwen local (Ollama, gratuit, aucun token Claude) écrit le script et la légende de chaque passage du jour
(06:00, 14:00, 22:00) à partir de la note de veille et de deux séries :
  A) stickman divertissement / explications pour artisans et commerçants -> fin : planning de 15 min de Liam (lien LU dans B2B\\docs\\SCRIPT-APPEL-SID.md) ;
  B) recrutement de call callers pour vendre des sites web (aucun lieu, aucun revenu) -> fin : « à la commission » (taux seulement s'il est dans la config), lien en bio.
Règles relues avant chaque exécution : Videos\\SKILL-VIDEOS.md (section « Règles pour Qwen » injectée dans les consignes).
Garde-fous vérifiés par le code (le script est refusé et réécrit sinon, 6 essais) : aucun chiffre ni nombre écrit par Qwen (les seuls chiffres, 15 minutes et le taux de commission de la config, sont
ajoutés par le code), aucune promesse de gain ou de résultat, aucun témoignage inventé, une seule idée, accroche courte, jamais le même sujet deux fois
(Videos\\scripts\\sujets.json), longueur pour 20 à 35 secondes, aucune phrase molle. Rien n'est publié ici.
  python Videos\\agents\\scripts.py jour [--a-blanc] [--jour AAAA-MM-JJ]
  python Videos\\agents\\scripts.py passage --heure 06:00 [--a-blanc]
  python Videos\\agents\\scripts.py etat"""
import argparse, json, re, sys, unicodedata
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import commun as C   # noqa: E402

AGENT = "videos-scripts"
SERIES = {
    "A": {"theme": "explication en bonhomme bâton, vivante et un peu drôle : une chose concrète qu'une page web change pour un artisan ou un commerçant",
          "public": "artisans et commerçants : la voix parle AU professionnel (vouvoiement, « vous » = l'artisan ou le commerçant, jamais son client)",
          "fin": "Et vous, votre page répond à ça ? Quinze minutes avec Liam : le lien est dans la description.",
          "hashtags": "#stickman #artisan #commerce #siteweb",
          "angles": ["le client qui cherche vos horaires un dimanche soir", "le bouton Appeler sur le téléphone du client", "les photos de vos réalisations",
                     "l'itinéraire jusqu'à votre boutique", "vos prestations visibles avant même de venir", "une page à votre nom plutôt qu'un seul réseau social",
                     "le nouvel habitant du quartier qui ne vous connaît pas encore", "les touristes de passage en Normandie", "la prise de rendez-vous sans téléphoner",
                     "être trouvé quand on cherche votre métier dans votre ville", "montrer les avis que vos clients ont déjà laissés", "vos spécialités du moment",
                     "le client qui compare deux artisans le soir", "votre zone d'intervention claire", "être joignable vite pour une urgence",
                     "une page lisible sur téléphone", "votre histoire et votre savoir-faire", "les commandes et réservations pour les fêtes",
                     "le bouche-à-oreille qui continue en ligne", "les questions qu'on vous pose sans arrêt, réglées par une page"]},
    "B": {"theme": "Liam cherche des call callers pour vendre des sites web : on appelle depuis chez soi, on décroche des rendez-vous, commission sur chaque vente, pas de salaire fixe, liste et script fournis",
          "public": "personnes qui savent parler au téléphone et cherchent une activité depuis chez elles (tutoiement, ton direct et franc)",
          "fin": "Pas de salaire fixe, je te le dis cash : c'est {commission}, sur chaque vente. Liste et script fournis. Postule via le lien en bio. Alors, tu sais parler au téléphone ?",
          "hashtags": "#recrutement #teletravail #prospection #commission",
          "angles": ["ce que fait un apporteur d'affaires au téléphone", "obtenir un rendez-vous, pas vendre", "travailler depuis chez soi avec un téléphone",
                     "décrocher un rendez-vous plutôt que forcer une vente", "commission sans fixe : être honnête sur le risque", "appeler aux heures où les artisans répondent",
                     "à quoi ressemble une session d'appels", "accepter un refus poli sans le prendre mal", "ce qu'il faut pour commencer",
                     "pour qui ce travail est fait, et pour qui il ne l'est pas", "un script d'appel qui guide sans faire réciter", "choisir ses heures",
                     "ce qu'on ne promet jamais au client au téléphone", "écouter avant de parler", "noter chaque appel pour ne rien oublier"]},
}
NOMBRES = re.compile(r"\d|%|€|\beuros?\b|\b(deux|trois|quatre|cinq|six|sept|huit|neuf|dix|onze|douze|treize|quatorze|quinze|seize|vingt|trente|quarante|cinquante|"
                     r"soixante|cent|cents|mille|millions?|milliards?|moitié|double|triple|pour ?cent)\b", re.I)
INTERDITS_B = re.compile(r"facile|rapidement|vite riche|complément de revenu", re.I)   # série B (argent) : rien qui sonne comme de l'argent facile
INTERDITS = re.compile(r"garanti|assuré|promet|promesse|million|riche|fortune|sans effort|passif|revenus?\b|salaire|témoign|m'a dit|m'ont dit|"
                       r"nos clients|mes clients|j'ai gagné|vous allez gagner|tu vas gagner|explos|record|numéro un|n°|meilleur|jamais vu|incroyable|"
                       r"secret|astuce que personne|abonne|like|commente|https?://|"
                       r"boost|augment|multipli|décupl|vos ventes|chiffre d'affaires|en chiffres|rentab|\bgagn(ez|erez|erai|eras|e plus)\b|plus de clients|"
                       r"clients en plus|attire(ra|z)? (plus|enfin)|succès assuré|résultats?\b", re.I)
SYSTEME_A = ("Tu écris des scripts de vidéos TikTok de 20 à 35 secondes, en français, pour LM Multi-Services, qui crée des pages web pour les artisans et commerçants. "
             "Style : bonhomme bâton animé sur fond sombre, divertissant et explicatif, une seule idée par vidéo, phrases courtes, à l'oral, ton : {ton}. "
             "Ne dis jamais qu'une page augmente les ventes, booste ou fait gagner quoi que ce soit : décris seulement ce que le client voit ou peut faire, "
             "et ce que le professionnel peut montrer. Ne parle pas des réseaux sociaux. ")
SYSTEME_B = ("Tu écris des scripts de vidéos TikTok de 20 à 35 secondes, en français, pour recruter des call callers : {message} "
             "Style : bonhomme bâton animé sur fond sombre, une seule idée par vidéo, phrases courtes, à l'oral, ton : {ton}. "
             "Ne cite aucune ville, aucune région, aucun lieu. Ne parle jamais d'argent gagné, de revenu, de montant ni de nombre de ventes. ")
SYSTEME_FIN = ("Règles absolues (fichier de règles de l'équipe) :\n{regles}\n"
               "Pas d'appel à l'action ni de lien : la fin de la vidéo est ajoutée ensuite. Reste exactement sur l'angle du jour. Réponds uniquement avec un objet JSON valide.")
DIDASCALIES = re.compile(r"cam[ée]ra|gros plan|\bplan\b|\bsc[èe]ne\b|on voit|à l'image|la vidéo (commence|montre)|narrateur|voix off", re.I)
MOLLES = re.compile(r"dans cette vidéo|voici comment|apprenez comment|aujourd'hui,? (on|nous|je) (va|allons|vais)|il est important de|n'h[ée]sitez pas|n'h[ée]site pas|tout simplement|d[ée]couvrez|"
                    r"\bbonjour\b|\bsalut à tous\b|sans plus attendre|comme vous le savez", re.I)
ADRESSE = re.compile(r"https?|www|\.(com|fr|net|org|io)\b|\bpoint (com|fr|net)\b|arobase|@|\bslash\b|tiret bas|bit\.ly|linktr", re.I)   # jamais une adresse épelée : « lien en bio » / « description » suffit
# Bon public : A parle À l'artisan ou au commerçant (vouvoiement), jamais à son client ; B parle au futur call caller (tutoiement), jamais en vouvoyant.
METIERS = r"(artisan|commer[çc]ant|plombier|[ée]lectricien|boulanger|garagiste|coiffeu(r|se)|menuisier|ma[çc]on|peintre|fleuriste|professionnel|prestataire)s?"
PUBLIC_FAUX = {"A": re.compile(rf"\b(votre|vos|ton|ta|tes)\s+{METIERS}\b|\b(tu|toi|ton|ta|tes)\b|\bt'|\bte\b"
                              # point de vue du client qui cherche un artisan (« trouver les numéros d'artisans ») : la ligne A parle À l'artisan de SA page
                              rf"|\b(trouver|trouvez|obtenir|obtenez|chercher|cherchez|contacter|contactez|joindre|joignez|appeler|appelez|choisir|choisissez|comparer|comparez)\b[^.?!]{{0,60}}?(\bd'|\b(des|un|une|les|le|la|du)\s+){METIERS}\b", re.I),
               "B": re.compile(r"\b(vous|votre|vos)\b", re.I)}


def public_faux(texte, serie):
    """Mot qui montre que le texte ne parle pas au bon public de la ligne (None si correct). Les paroles citées entre « » ou "" ne comptent pas."""
    sans_citation = re.sub(r"«[^»]*»|\"[^\"]*\"", " ", texte or "")
    m = PUBLIC_FAUX.get(serie, PUBLIC_FAUX["A"]).search(sans_citation)
    return m.group(0) if m else None


ROLES = ["l'accroche parlée : huit mots au plus, une question, une contradiction ou une erreur courante qui intrigue dès la première seconde",
         "le problème concret, vu du côté du public", "pourquoi ce problème arrive", "ce qui change concrètement", "un exemple concret de ce qu'on voit ou fait",
         "la phrase qui conclut l'idée et renvoie à l'accroche, sans appel à l'action"]
MOTS_PHRASE = (4, 11)   # une phrase = une image : 4 à 11 mots, soit un changement visuel toutes les 2 à 4 secondes


def systeme(serie, conf, regles):
    l = conf["lignes"][serie]
    debut = (SYSTEME_B if serie == "B" else SYSTEME_A).format(ton=l.get("ton") or "simple et sincère", message=l.get("message") or SERIES["B"]["theme"])
    return debut + SYSTEME_FIN.format(regles=C.section(regles, "Règles pour Qwen") or "aucun chiffre, aucune promesse, aucun témoignage")


def fin(serie, conf):
    """Phrase de fin ajoutée par le code. Ligne B : « à la commission » tant que taux_commission est vide (jamais de taux inventé) ; « lien en bio », jamais d'adresse épelée."""
    if serie != "B": return SERIES[serie]["fin"]
    taux = conf["lignes"]["B"]["taux_commission"]
    return SERIES["B"]["fin"].format(commission=f"{taux} de commission" if taux else "à la commission")


def lieu_interdit(texte, conf):
    bas = (texte or "").lower()
    for lieu in conf["lignes"]["B"].get("lieux_interdits") or []:
        if re.search(rf"(?<![\wà-ÿ]){re.escape(str(lieu).lower())}(?![\wà-ÿ])", bas): return lieu
    return None


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9 ]+", " ", s).split()


def proche(a, b):
    """Vrai si deux sujets se ressemblent trop (mêmes mots à 60 % ou plus, mots de plus de 3 lettres)."""
    x, y = {m for m in norm(a) if len(m) > 3}, {m for m in norm(b) if len(m) > 3}
    return bool(x and y) and len(x & y) / len(x | y) >= 0.6


def sujets_lire():
    try: return json.loads(C.SUJETS.read_text(encoding="utf-8"))
    except (OSError, ValueError): return []


def sujets_ecrire(liste):
    C.SCRIPTS.mkdir(parents=True, exist_ok=True); C.SUJETS.write_text(json.dumps(liste, ensure_ascii=False, indent=1), encoding="utf-8")


def serie_du_passage(conf, heure):
    """Ligne du passage (series_par_passage). La ligne B renvoie au lien en bio : elle est produite même sans lien_candidature (rien n'est publié avant le go de Liam)."""
    s = (conf["series_par_passage"] or {}).get(heure, "A")
    return s if s in SERIES else "A"


def angle_libre(serie, historique):
    faits = {h.get("angle") for h in historique}
    return next((a for a in SERIES[serie]["angles"] if a not in faits), "")


def note_veille(jour):
    notes = sorted(p for p in C.VEILLE.glob("*.md") if p.stem <= jour)
    if not notes: return "aucune note de veille aujourd'hui"
    lignes = [l[2:] for l in notes[-1].read_text(encoding="utf-8").splitlines() if l.startswith("- ")]
    return " ; ".join(lignes)[:900] or "aucune note de veille aujourd'hui"


EXEMPLE_PUBLIC = {"A": "Bonne phrase : « Votre client cherche votre numéro le soir. » Mauvaise phrase (interdite) : « Vous cherchez le numéro d'un artisan ? ». "
                        "La vidéo parle à l'artisan de SA propre page et de ce que SES clients y voient.",
                  "B": "Bonne phrase : « Tu appelles, tu décroches un rendez-vous. » Mauvaise phrase (interdite) : « Vous cherchez un emploi ? ». Tutoie toujours."}


def demande(serie, angle, historique, veille):
    s = SERIES[serie]; deja = [h["sujet"] for h in historique if h.get("serie") == serie][-25:]
    return (f"Série : {s['theme']}. Public : {s['public']}. {EXEMPLE_PUBLIC.get(serie, '')} " + (f"Angle du jour : {angle}. " if angle else "Choisis toi-même un angle nouveau. ")
            + "Sujets déjà traités, à ne jamais refaire : " + ("; ".join(deja) if deja else "aucun") + ". "
            + f"Titres d'articles repérés par la veille du jour (pour le format, pas pour les faits) : {veille}. "
            + "Écris : sujet (une phrase : l'idée unique de la vidéo), titre (cinq à huit mots), accroche (texte affiché à l'écran, trois à six mots, qui donne envie de rester), "
            + "scenes (exactement six phrases parlées, dans cet ordre : " + " ; ".join(f"{i + 1}) {r}" for i, r in enumerate(ROLES))
            + " ; les phrases deux à six font de six à onze mots chacune, à l'oral, et parlent toutes de la même idée), "
            + "legende (une ou deux phrases pour la description, vingt-cinq mots au plus). "
            + 'Format : {"sujet": "...", "titre": "...", "accroche": "...", "scenes": ["...", "...", "...", "...", "...", "..."], "legende": "..."}')


def mots(t): return len(re.findall(r"[\wÀ-ÿ'’-]+", t or ""))


def verifier(s, serie, historique, conf):
    """Liste des problèmes d'un script proposé par Qwen (vide = accepté)."""
    if not isinstance(s, dict): return ["réponse qui n'est pas un objet JSON"]
    pb = []
    champs = {k: s.get(k) for k in ("sujet", "titre", "accroche", "legende")}
    scenes = s.get("scenes")
    if any(not isinstance(v, str) or not v.strip() for v in champs.values()): pb.append("champ manquant (sujet, titre, accroche ou legende)")
    if not isinstance(scenes, list) or not 4 <= len(scenes) <= 7 or any(not isinstance(x, str) or not x.strip() for x in scenes): return pb + ["scenes : quatre à sept phrases attendues"]
    textes = [str(v) for v in champs.values()] + scenes
    for t in textes:
        m = NOMBRES.search(t)
        if m: pb.append(f"nombre ou chiffre interdit (« {m.group(0)} »)"); break
    for t in textes:
        m = INTERDITS.search(t) or (INTERDITS_B.search(t) if serie == "B" else None)
        if m: pb.append(f"formulation interdite (« {m.group(0)} »)"); break
    for t in scenes:
        m = DIDASCALIES.search(t)
        if m: pb.append(f"indication de mise en scène interdite (« {m.group(0)} ») : seulement le texte lu par la voix"); break
    for t in textes:
        m = MOLLES.search(t)
        if m: pb.append(f"phrase molle (« {m.group(0)} »)"); break
    for t in textes:
        m = ADRESSE.search(t)
        if m: pb.append(f"adresse épelée interdite (« {m.group(0)} ») : dire seulement « lien en bio » ou « dans la description »"); break
    for t in [champs["sujet"] or "", champs["titre"] or "", champs["accroche"] or ""] + scenes:
        faux = public_faux(t, serie)
        if faux: pb.append(f"mauvais public (« {faux} ») : " + ("parle À l'artisan ou au commerçant, en vouvoyant, jamais à son client" if serie == "A" else "parle au futur call caller, en le tutoyant")); break
    if serie == "B":
        for t in textes:
            lieu = lieu_interdit(t, conf)
            if lieu: pb.append(f"lieu interdit sur la ligne B (« {lieu} »)"); break
    if mots(scenes[0]) > 10: pb.append("accroche parlée trop longue (10 mots au plus)")
    longues = [i + 1 for i, x in enumerate(scenes[1:], 1) if mots(x) > 16]
    if longues: pb.append(f"phrase(s) {longues} trop longue(s) (16 mots au plus, une image toutes les 2 à 4 secondes)")
    if mots(champs["accroche"] or "") > 10: pb.append("accroche écran trop longue (10 mots au plus)")
    total = sum(mots(x) for x in scenes) + mots(fin(serie, conf))
    if not conf["mots_min"] <= total <= conf["mots_max"]: pb.append(f"longueur {total} mots (attendu {conf['mots_min']} à {conf['mots_max']} pour {conf['duree_min_s']} à {conf['duree_max_s']} secondes)")
    for h in historique:
        if norm(h.get("sujet")) == norm(champs["sujet"]) or proche(h.get("sujet", ""), champs["sujet"] or "") or norm(h.get("titre")) == norm(champs["titre"]):
            pb.append("sujet déjà traité"); break
    return pb


def legende(serie, s, conf):
    """Légende complète : titre, phrase de Qwen, renvoi (lien lu, jamais recopié dans un fichier du dépôt), mention IA, mots-dièse."""
    if serie == "A":
        lien = C.lien_rdv(); renvoi = f"Réserver 15 minutes avec Liam : {lien}" if lien else ""
    else:
        taux = conf["lignes"]["B"]["taux_commission"]
        renvoi = f"À la commission ({taux} sur chaque vente), pas de salaire fixe. Postule via le lien en bio." if taux else "À la commission, pas de salaire fixe. Postule via le lien en bio."
    tags = conf["lignes"][serie].get("hashtags") or SERIES[serie]["hashtags"]
    return "\n\n".join(x for x in (s["titre"].strip(), s["legende"].strip(), renvoi, C.MENTION_IA, tags) if x)


def ecrire_script(conf, jour, heure, ollama, historique, a_blanc, essais=6):
    """Écrit Videos\\scripts\\AAAA-MM-JJ-HHMM.json pour ce passage (rien si déjà fait). -> chemin, ou None après `essais` refus."""
    fichier = C.SCRIPTS / f"{jour}-{heure.replace(':', '')}.json"
    if fichier.exists(): print(f"  {heure} : script déjà écrit ({fichier.name})"); return fichier
    serie = serie_du_passage(conf, heure); angle = angle_libre(serie, historique); veille = note_veille(jour)
    try: consignes = systeme(serie, conf, C.regles())
    except RuntimeError: consignes = systeme(serie, conf, "")
    if serie == "A" and not C.lien_rdv(): print("  ! lien du planning de 15 min introuvable dans B2B\\docs\\SCRIPT-APPEL-SID.md : la fin renverra à la description sans lien")
    raisons = []
    for n in range(1, essais + 1):
        texte = demande(serie, angle, historique, veille) + (f" Ta réponse précédente a été refusée : {'; '.join(raisons)}. Corrige-la." if raisons else "")
        try: s = json.loads(ollama.chat(consignes, texte, temperature=0.6 + 0.1 * n))
        except (ValueError, KeyError) as e: raisons = [f"JSON illisible ({type(e).__name__})"]; continue
        raisons = verifier(s, serie, historique, conf)
        if raisons: print(f"  {heure} : essai {n} refusé ({'; '.join(raisons)})"); continue
        scenes = [x.strip() for x in s["scenes"]] + [fin(serie, conf)]
        doc = {"jour": jour, "passage": heure, "serie": serie, "angle": angle, "sujet": s["sujet"].strip(), "titre": s["titre"].strip(), "accroche": s["accroche"].strip(),
               "scenes": scenes, "legende": legende(serie, s, conf), "mots": sum(mots(x) for x in scenes), "modele": conf["modele"], "cree_le": f"{datetime.now():%Y-%m-%d %H:%M}"}
        if a_blanc: print(f"[à blanc] {heure} (série {serie}) : {json.dumps(doc, ensure_ascii=False, indent=1)}"); return fichier
        C.SCRIPTS.mkdir(parents=True, exist_ok=True); fichier.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
        historique.append({k: doc[k] for k in ("jour", "passage", "serie", "angle", "sujet", "titre")}); sujets_ecrire(historique)
        C.journal(AGENT, "script", f"{jour} {heure} : série {serie}, {doc['mots']} mots, essai {n}")
        print(f"  {heure} : série {serie} « {doc['titre']} » ({doc['mots']} mots, essai {n})"); return fichier
    C.journal(AGENT, "erreur", f"{jour} {heure} : {essais} essais refusés ({'; '.join(raisons)[:160]})", a_blanc)
    print(f"  ! {heure} : aucun script valable après {essais} essais"); return None


def cmd(conf, jour, heures, a_blanc):
    historique = sujets_lire(); faits = 0
    a_faire = [h for h in heures if not (C.SCRIPTS / f"{jour}-{h.replace(':', '')}.json").exists()]
    if not a_faire: print(f"Scripts du {jour} : déjà tous écrits."); return 0
    with C.Ollama(conf["modele"]) as o:
        for h in a_faire: faits += ecrire_script(conf, jour, h, o, historique, a_blanc) is not None
    print(f"Scripts du {jour} : {faits}/{len(a_faire)} écrit(s).")
    return 0 if faits == len(a_faire) else 2


def cmd_etat(jour):
    du_jour = sorted(C.SCRIPTS.glob(f"{jour}-*.json")); h = sujets_lire()
    print(f"{len(du_jour)} script(s) le {jour} ; {len(h)} sujet(s) déjà traité(s) (A : {sum(x.get('serie') == 'A' for x in h)}, B : {sum(x.get('serie') == 'B' for x in h)})")
    return 0


def main(argv=None):
    a = argparse.ArgumentParser(prog="videos-scripts"); sp = a.add_subparsers(dest="cmd", required=True)
    for n in ("jour", "passage"):
        p = sp.add_parser(n); p.add_argument("--a-blanc", action="store_true"); p.add_argument("--jour")
    sp.choices["passage"].add_argument("--heure", required=True)
    sp.add_parser("etat")
    a = a.parse_args(argv); jour = getattr(a, "jour", None) or f"{C.heure_paris():%Y-%m-%d}"
    if a.cmd == "etat": return cmd_etat(jour)
    C.exiger(AGENT, a.cmd, a.a_blanc); C.exiger_regles(AGENT, a.a_blanc); conf = C.cfg()
    heures = conf["passages"] if a.cmd == "jour" else [a.heure]
    return cmd(conf, jour, heures, a.a_blanc)


if __name__ == "__main__":
    sys.exit(main())
