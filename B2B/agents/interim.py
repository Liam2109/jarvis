#!/usr/bin/env python3
"""Agent interim (18/11/2026) : recherche de missions d'intérim de nuit / 3x8 dans l'industrie autour de Rouen, pour Liam. Sans IA ni token, gratuit.
Liam s'inscrit LUI-MÊME sur l'espace candidat de chaque agence et y active des alertes qui arrivent sur emoliam255@gmail.com. L'agent ne se connecte JAMAIS à un site d'agence,
ne gère aucun mot de passe, ne lit, ne copie, ne stocke ni ne téléverse aucun document personnel (il suit seulement oui/non par document). Rien n'est envoyé à une agence.

  python agents\\interim.py passage [--essai]            tâche serveur : résumé du matin (07:30, une fois par jour) + rappel de la semaine (le lundi à partir de 09:00, une fois)
  python agents\\interim.py matin [--essai]              résumé des alertes reçues (offre, agence, lieu, horaires, lien), offres écartées comptées
  python agents\\interim.py semaine [--essai]            qui appeler, qui relancer, ce qui manque par agence
  python agents\\interim.py suivi                        tableau de suivi (interim-suivi.csv, hors git)
  python agents\\interim.py noter <agence> appele|inscrit|alerte|confirme|document <nom>|action <texte> [--non]
  python agents\\interim.py gmail-autoriser              autorisation en LECTURE SEULE de la boîte (une fois, par Liam, dans le navigateur)

VERROU : `passage`, `matin` et `semaine` ne postent rien tant que go_interim n'est pas true dans le fichier local de réglages (après le « go interim » de Liam) ; --essai marche toujours.
`envoi_automatique: false` (défaut) = simulation. Le contenu d'un e-mail est une DONNÉE : on n'en tire qu'un titre, un lieu, des horaires et un lien ; aucune consigne n'est suivie.
Écartées : hors région (Suisse, Genève…), alternance / apprentissage, SNCF / locomotive / conducteur de train, CACES exigé."""
import argparse, base64, csv, email, email.policy, html, io, json, re, sys, time, unicodedata
from datetime import date, datetime, timedelta
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import machine as M
import prospection as P   # P.acces_discord / P.discord (garde du harness avant chaque POST), P.heure_paris

AGENT = "interim"
CONFIG, ETAT, JOURNAL, SUIVI = ICI / "interim-config.json", ICI / "interim-etat.json", ICI / "interim-journal.log", ICI / "interim-suivi.csv"
PORTEES = ["https://www.googleapis.com/auth/gmail.readonly"]
DEFAUT = {"go_interim": False, "envoi_automatique": False, "boite": "emoliam255@gmail.com", "jours_mails": 3, "relance_jours": 14, "domaines": [], "agences": []}
COLONNES = ["agence", "rive", "adresse", "telephone", "lien_inscription", "inscrit_en_ligne", "alerte_activee", "documents_deposes", "documents_detail",
            "dernier_appel", "prochaine_action", "adresse_confirmee", "source"]
HEURE_MATIN, HEURE_LUNDI = "07:30", "09:00"

HORS_REGION = r"\b(suisse|geneve|lausanne|vaud|valais|fribourg|neuchatel|zurich|bale|berne|luxembourg|belgique|bruxelles|monaco)\b"
ALTERNANCE = r"\b(alternance|alternant|apprenti|apprentissage|contrat pro|contrat de professionnalisation)\b"
FERROVIAIRE = r"\b(sncf|locomotive|conducteur de train|conductrice de train|agent de conduite|ferroviaire)\b"
CACES = r"\bcaces\b"
CACES_FACULTATIF = r"\bsans caces\b|\bcaces (non|pas) (obligatoire|exige|requis|necessaire)\b|\bcaces (apprecie|souhaite|serait un plus|est un plus|un plus)\b"
NUIT = [("nuit", r"\bnuit\b|\bnuits\b"), ("3x8", r"\b3\s?x\s?8\b|\b3\s?\*\s?8\b"), ("2x8", r"\b2\s?x\s?8\b"), ("5x8", r"\b5\s?x\s?8\b"),
        ("équipe", r"\ben equipes?\b|\bposte\b|\btravail poste\b"), ("week-end", r"\bweek.?end\b|\bvsd\b")]
LIEUX = ["rouen", "sotteville les rouen", "le petit quevilly", "petit quevilly", "le grand quevilly", "grand quevilly", "saint etienne du rouvray", "bois guillaume",
         "mont saint aignan", "deville les rouen", "maromme", "darnetal", "oissel", "elbeuf", "saint pierre les elbeuf", "caudebec les elbeuf", "cleon", "canteleu", "barentin",
         "malaunay", "notre dame de bondeville", "isneauville", "franqueville saint pierre", "la neuville chant d oisel", "boos", "mesnil esnard", "bonsecours", "le trait",
         "petit couronne", "grand couronne", "val de reuil", "louviers", "pont de l arche", "saint aubin les elbeuf", "tourville la riviere", "yvetot", "le havre", "evreux"]
SENSIBLE = r"\b(mot de passe|identifiant|code de verification|code de confirmation|carte bancaire|carte vitale|piece d identite|justificatif|rib)\b"
LIEN = re.compile(r"https?://[^\s\"'<>)\]]+")
LIEN_INUTILE = re.compile(r"unsubscribe|desinscri|desabonn|optout|opt-out|preferences|pixel|tracking|\.png|\.jpg|\.gif|privacy|confidentialite|cookies", re.I)


class ErreurAgent(Exception):
    """Problème signalé à Liam (message clair, code de sortie 2)."""


def plat(t): return " ".join("".join(c for c in unicodedata.normalize("NFD", str(t).lower()) if unicodedata.category(c) != "Mn").replace("-", " ").replace("'", " ").split())


# --- réglages, état, journal, suivi -------------------------------------------------------------------------------
def cfg():
    c = json.loads(json.dumps(DEFAUT))
    try:
        if CONFIG.exists(): c.update({k: v for k, v in json.loads(CONFIG.read_text(encoding="utf-8-sig")).items() if not k.startswith("_")})
    except (OSError, ValueError): raise ErreurAgent(f"réglages illisibles : {CONFIG.name}")
    try: M.surcharge_locale(CONFIG, c)
    except M.ErreurLocale as e: raise ErreurAgent(str(e))
    c["go_interim"] = c.get("go_interim") is True; c["envoi_automatique"] = c.get("envoi_automatique") is True
    c["domaines"] = [str(d).lower().strip() for d in c.get("domaines") or [] if str(d).strip()]
    return c


def etat_lire():
    try: e = json.loads(ETAT.read_text(encoding="utf-8")) if ETAT.exists() else {}
    except (OSError, ValueError): raise ErreurAgent(f"état illisible ({ETAT.name}) : corrigez ou supprimez le fichier à la main")
    e = e if isinstance(e, dict) else {}
    e.setdefault("vus", {}); e.setdefault("matin", {}); e.setdefault("semaine", {})
    return e


def etat_ecrire(e):
    limite = (date.today() - timedelta(days=60)).isoformat()
    e["vus"] = {k: v for k, v in e["vus"].items() if v >= limite}
    ETAT.write_text(json.dumps(e, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")


def journaliser(action, detail=""):
    with open(JOURNAL, "a", encoding="utf-8") as f: f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} | {action} | {detail}\n")


def ligne_depart(a):
    docs = a.get("documents") or []
    return {"agence": a.get("agence", ""), "rive": a.get("rive", ""), "adresse": a.get("adresse", "") or "inconnue", "telephone": a.get("telephone", ""),
            "lien_inscription": a.get("lien", ""), "inscrit_en_ligne": "non", "alerte_activee": "non", "documents_deposes": "non" if docs else "",
            "documents_detail": "; ".join(f"{d}=non" for d in docs), "dernier_appel": "", "prochaine_action": a.get("note", ""),
            "adresse_confirmee": a.get("confirmee", "non"), "source": a.get("source", "")}


def suivi_lire(conf):
    """Lignes du suivi ; créé (ou complété des agences de la liste de départ qui y manquent) sans jamais écraser ce que Liam a noté."""
    lignes = []
    if SUIVI.exists():
        with open(SUIVI, encoding="utf-8-sig", newline="") as f: lignes = [{k: (r.get(k) or "") for k in COLONNES} for r in csv.DictReader(f, delimiter=";")]
    connues = {plat(l["agence"]) for l in lignes}
    return lignes + [ligne_depart(a) for a in conf["agences"] if plat(a.get("agence", "")) not in connues]


def suivi_ecrire(lignes):
    with open(SUIVI, "w", encoding="utf-8-sig", newline="") as f:   # BOM + « ; » : s'ouvre directement dans Excel
        w = csv.DictWriter(f, fieldnames=COLONNES, delimiter=";"); w.writeheader(); w.writerows(lignes)


def docs(l):
    """[(document, oui/non)] du détail « nom=oui; nom=non »."""
    return [(d.rsplit("=", 1)[0].strip(), d.rsplit("=", 1)[1].strip()) for d in l["documents_detail"].split(";") if "=" in d]


def docs_texte(paires): return "; ".join(f"{d}={v}" for d, v in paires)


# --- monde extérieur (doublures dans les tests) -------------------------------------------------------------------
def jeton(boite): return ICI / f"gmail-lecture-{boite.strip().lower()}.json"


def ouvrir_gmail(boite):
    """Client Gmail en LECTURE SEULE (portée gmail.readonly, jeton séparé de celui de reponses.py qui peut envoyer)."""
    import gmail_api as GA
    j = jeton(boite)
    if not j.exists(): raise GA.JetonExpire(boite)
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    cr = Credentials.from_authorized_user_file(str(j), PORTEES)
    if not cr.valid:
        if not cr.refresh_token: raise GA.JetonExpire(boite)
        try: cr.refresh(Request())
        except Exception as e: raise GA._traduire(e, boite) from None
        j.write_text(cr.to_json(), encoding="utf-8")
    c = GA.Client(GA._service(cr), boite)
    if c.profil().lower() != boite.lower(): raise GA.ErreurApi(403, "jeton d'un autre compte")
    return c


def alerter_discord(texte):
    try:
        a = P.acces_discord()
        if not a: return False
        jeton_, salon, uid = a
        r = P.discord(jeton_, "POST", f"/channels/{salon}/messages", {"content": f"<@{uid}> {texte}"[:1900], "allowed_mentions": {"users": [uid]}})
        return bool(r and "id" in r)
    except Exception as ex: print(f"  alerte Discord impossible ({type(ex).__name__})"); return False


def maintenant(): return P.heure_paris()


# --- lecture d'un e-mail d'alerte ---------------------------------------------------------------------------------
def texte_mail(brut):
    """(expéditeur, sujet, texte) d'un message brut : texte brut, sinon HTML sans balises. Pièces jointes jamais lues."""
    m = email.message_from_bytes(brut, policy=email.policy.default)
    corps = m.get_body(preferencelist=("plain", "html"))
    t = ""
    if corps is not None:
        try: t = corps.get_content()
        except Exception: t = ""
        if corps.get_content_type() == "text/html":
            liens = " ".join(re.findall(r'href=["\'](https?://[^"\']+)', t))
            t = html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"(?is)<(script|style).*?</\1>", " ", t))) + " " + liens
    return str(m.get("From", "")), str(m.get("Subject", "")), t


def domaine(expediteur):
    m = re.search(r"@([\w.-]+)", expediteur or ""); return m.group(1).lower() if m else ""


def connu(dom, domaines): return any(dom == d or dom.endswith("." + d) for d in domaines)


def nom_agence(expediteur, dom):
    nom = re.sub(r"\s*<.*?>\s*", "", expediteur or "").strip().strip('"')
    return nom or dom


def analyser(expediteur, sujet, texte, domaines):
    """-> dict offre, ou {"ecart": raison}. Rien d'inventé : un champ introuvable vaut « non indiqué »."""
    dom = domaine(expediteur)
    if not connu(dom, domaines): return {"ecart": "expéditeur hors liste"}
    tout = plat(sujet + " " + texte)
    for raison, motif in (("hors région", HORS_REGION), ("alternance", ALTERNANCE), ("SNCF / train", FERROVIAIRE)):
        if re.search(motif, tout): return {"ecart": raison}
    if re.search(CACES, tout) and not re.search(CACES_FACULTATIF, tout): return {"ecart": "CACES exigé"}
    lieu = next((l for l in LIEUX if re.search(rf"\b{l}\b", tout)), "")
    horaires = [n for n, m in NUIT if re.search(m, tout)]
    lien = next((u.rstrip(".,;") for u in LIEN.findall(texte) if not LIEN_INUTILE.search(u)), "")
    return {"agence": nom_agence(expediteur, dom), "offre": " ".join(sujet.split())[:120] or "(sans objet)", "lieu": lieu.title() if lieu else "non indiqué",
            "horaires": ", ".join(horaires) or "non indiqués", "lien": lien[:300] or "aucun lien", "sensible": bool(re.search(SENSIBLE, tout))}


def requete(conf):
    return f"newer_than:{int(conf['jours_mails'])}d -in:sent -in:chats (" + " OR ".join(f"from:{d}" for d in conf["domaines"]) + ")"


# --- commandes ----------------------------------------------------------------------------------------------------
def poster(conf, texte, essai):
    if essai: print("[essai] message qui serait posté :\n" + texte); return True
    if not conf["envoi_automatique"]: print("[simulation : envoi_automatique=false] " + texte); return True
    ok = alerter_discord(texte); print(texte); print("  (posté sur Discord)" if ok else "  ! Discord : non envoyé"); return ok


def cmd_matin(conf, essai, gmail=None):
    etat = etat_lire(); jour = maintenant().date().isoformat()
    try: g = gmail or ouvrir_gmail(conf["boite"])
    except Exception as ex:
        print(f"  ! boîte {conf['boite']} non lisible ({type(ex).__name__}) : Liam lance une fois python agents\\interim.py gmail-autoriser")
        if not essai: journaliser("matin", f"boîte non lisible ({type(ex).__name__})")
        return 0
    try:
        ids = [i for i in g.ids(requete(conf), maxi=60) if i not in etat["vus"]]
        mails = [(i, texte_mail(g.brut(i))) for i in ids]
    except Exception as ex:
        print(f"  ! Gmail injoignable ({type(ex).__name__}) : réessayé au prochain passage")
        if not essai: journaliser("matin", f"Gmail injoignable ({type(ex).__name__})")
        return 2
    offres, ecarts = [], {}
    for i, (exp, suj, txt) in mails:
        r = analyser(exp, suj, txt, conf["domaines"])
        if "ecart" in r: ecarts[r["ecart"]] = ecarts.get(r["ecart"], 0) + 1
        else: offres.append(r)
    l = []
    if offres:
        l.append(f"**Intérim — {len(offres)} alerte(s) reçue(s)** (à vérifier sur le site de l'agence, rien n'est envoyé) :")
        for o in offres:
            l.append(f"- {o['offre']} — {o['agence']} — {o['lieu']} — horaires : {o['horaires']} — {o['lien']}")
            if o["sensible"]: l.append("  ⚠ ce mail parle d'identifiant, de mot de passe, de carte ou de justificatif : à faire toi-même sur le site, rien n'est stocké.")
    if ecarts: l.append("Écartées : " + ", ".join(f"{n} {r}" for r, n in sorted(ecarts.items())) + ".")
    if offres: poster(conf, "\n".join(l), essai)
    else: print(f"{len(mails)} nouveau(x) mail(s), aucune offre à garder" + (f" ({', '.join(f'{n} {r}' for r, n in ecarts.items())})" if ecarts else "") + " : aucun message.")
    if essai: return 0
    for i, _ in mails: etat["vus"][i] = jour
    etat["matin"][jour] = len(offres); etat_ecrire(etat)
    journaliser("matin", f"{len(mails)} mail(s) lu(s), {len(offres)} offre(s) gardée(s), {sum(ecarts.values())} écartée(s)")
    return 0


def a_faire(l, jour, relance_jours, appel_hebdo):
    """Actions de la semaine pour une agence (texte), d'après le suivi seulement."""
    t = []
    if appel_hebdo: t.append("appeler cette semaine (dire que je suis dispo)")
    if l["adresse_confirmee"].startswith("non"): t.append("confirmer l'adresse")
    if l["inscrit_en_ligne"] != "oui": t.append("s'inscrire en ligne")
    elif l["alerte_activee"] != "oui": t.append("activer l'alerte nuit / 3x8 / industrie / Rouen")
    manquants = [d for d, v in docs(l) if v != "oui"]
    if manquants: t.append("documents à déposer toi-même : " + ", ".join(manquants))
    if l["inscrit_en_ligne"] == "oui" and not appel_hebdo and (not l["dernier_appel"] or l["dernier_appel"] <= (date.fromisoformat(jour) - timedelta(days=relance_jours)).isoformat()):
        t.append(f"relancer (dernier appel : {l['dernier_appel'] or 'jamais'})")
    if l["prochaine_action"]: t.append("note : " + l["prochaine_action"])
    return t


def cmd_semaine(conf, essai):
    jour = maintenant().date().isoformat(); hebdo = {plat(a["agence"]) for a in conf["agences"] if a.get("appel_hebdo")}
    lignes = suivi_lire(conf); l = [f"**Intérim — semaine du {jour}** (rien n'est envoyé aux agences) :"]
    for x in lignes:
        t = a_faire(x, jour, conf["relance_jours"], plat(x["agence"]) in hebdo)
        if t: l.append(f"- {x['agence']} ({x['telephone'] or 'tél. inconnu'}) : " + " ; ".join(t))
    l.append("Noter : python B2B\\agents\\interim.py noter <agence> appele|inscrit|alerte|confirme|document <nom>")
    poster(conf, "\n".join(l), essai)
    if essai: return 0
    if not SUIVI.exists(): suivi_ecrire(lignes)
    etat = etat_lire(); etat["semaine"][jour] = True; etat_ecrire(etat); journaliser("semaine", f"{len(lignes)} agence(s) passée(s) en revue")
    return 0


def cmd_passage(conf, essai, gmail=None):
    if not conf["go_interim"] and not essai:
        print("Verrou : Liam n'a pas encore écrit « go interim » (go_interim absent du fichier local de réglages) : rien posté."); return 0
    n = maintenant(); jour = n.date().isoformat(); etat = etat_lire(); code = 0
    if f"{n:%H:%M}" >= HEURE_MATIN and jour not in etat["matin"]: code = cmd_matin(conf, essai, gmail)
    lundi = (n.date() - timedelta(days=n.weekday())).isoformat()
    if n.weekday() == 0 and f"{n:%H:%M}" >= HEURE_LUNDI and lundi not in etat_lire()["semaine"]: code = max(code, cmd_semaine(conf, essai))
    return code


def trouver(lignes, nom):
    c = [l for l in lignes if plat(nom) in plat(l["agence"])]
    if len(c) != 1: raise ErreurAgent(f"« {nom} » : {'aucune agence' if not c else 'plusieurs agences : ' + ', '.join(l['agence'] for l in c)} ; précisez le nom")
    return c[0]


def cmd_noter(conf, nom, quoi, valeur, non):
    lignes = suivi_lire(conf); l = trouver(lignes, nom); oui = "non" if non else "oui"; jour = maintenant().date().isoformat()
    if quoi == "appele": l["dernier_appel"] = jour
    elif quoi == "inscrit": l["inscrit_en_ligne"] = oui
    elif quoi == "alerte": l["alerte_activee"] = oui
    elif quoi == "confirme": l["adresse_confirmee"] = f"oui (Liam, {jour})" if not non else "non"
    elif quoi == "action": l["prochaine_action"] = valeur
    elif quoi == "document":
        p = docs(l); i = [k for k, (d, _) in enumerate(p) if plat(valeur) in plat(d)]
        if len(i) != 1: raise ErreurAgent(f"document « {valeur} » introuvable ou ambigu ; documents suivis : {', '.join(d for d, _ in p) or 'aucun'}")
        p[i[0]] = (p[i[0]][0], oui); l["documents_detail"] = docs_texte(p)
        n = sum(1 for _, v in p if v == "oui"); l["documents_deposes"] = "oui" if n == len(p) else ("partiel" if n else "non")
    suivi_ecrire(lignes); journaliser("noter", f"{l['agence']} : {quoi}"); print(f"Noté : {l['agence']} — {quoi}{' ' + valeur if valeur else ''} ({'non' if non else 'oui'})."); return 0


def cmd_suivi(conf):
    lignes = suivi_lire(conf)
    for l in lignes:
        print(f"- {l['agence']} [{l['rive'] or '?'}] {l['adresse']} {l['telephone']} | inscrit {l['inscrit_en_ligne']} | alerte {l['alerte_activee']} | documents {l['documents_deposes'] or '-'}"
              f" | dernier appel {l['dernier_appel'] or '-'} | adresse confirmée {l['adresse_confirmee']}")
    print(f"Fichier : {SUIVI}" + ("" if SUIVI.exists() else " (créé au premier « noter » ou au rappel du lundi)")); return 0


def cmd_autoriser(conf):
    import gmail_api as GA
    from google_auth_oauthlib.flow import InstalledAppFlow
    cr = InstalledAppFlow.from_client_secrets_file(str(GA.CLIENT), PORTEES).run_local_server(port=0, login_hint=conf["boite"], authorization_prompt_message="",
                                                                                         success_message="Autorisation reçue : tu peux fermer cet onglet.")
    if GA.Client(GA._service(cr), conf["boite"]).profil().lower() != conf["boite"].lower(): raise ErreurAgent("le compte autorisé n'est pas la bonne boîte : jeton non enregistré")
    jeton(conf["boite"]).write_text(cr.to_json(), encoding="utf-8"); print("Jeton de lecture enregistré (hors git)."); return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog=AGENT, description="Intérim de nuit / 3x8 autour de Rouen : résumé des alertes, suivi des agences (rien n'est envoyé).")
    sp = p.add_subparsers(dest="cmd", required=True)
    for n in ("passage", "matin", "semaine"): sp.add_parser(n).add_argument("--essai", "--a-blanc", dest="essai", action="store_true")
    sp.add_parser("suivi"); sp.add_parser("gmail-autoriser")
    n = sp.add_parser("noter"); n.add_argument("agence"); n.add_argument("quoi", choices=["appele", "inscrit", "alerte", "confirme", "document", "action"])
    n.add_argument("valeur", nargs="*"); n.add_argument("--non", action="store_true")
    args = p.parse_args(argv)
    M.exiger(AGENT, args.cmd, getattr(args, "essai", False) or args.cmd in ("suivi", "noter", "gmail-autoriser"))
    try:
        conf = cfg()
        if args.cmd == "passage": return cmd_passage(conf, args.essai)
        if args.cmd in ("matin", "semaine"):
            if not conf["go_interim"] and not args.essai: print("Verrou « go interim » fermé : utilisez --essai."); return 0
            return cmd_matin(conf, args.essai) if args.cmd == "matin" else cmd_semaine(conf, args.essai)
        if args.cmd == "suivi": return cmd_suivi(conf)
        if args.cmd == "noter": return cmd_noter(conf, args.agence, args.quoi, " ".join(args.valeur), args.non)
        return cmd_autoriser(conf)
    except ErreurAgent as e:
        print(f"  ! {e}"); return 2
    except OSError as e:
        print(f"  ! erreur de fichier : {e.strerror or type(e).__name__}"); return 2


if __name__ == "__main__":
    _t0 = time.time(); _code = main()
    if sys.argv[1:2] == ["passage"] and "--essai" not in sys.argv:   # trace du harness (B2B\logs\agents\interim), jamais bloquante
        try: sys.path.insert(0, str(ICI.parent / "harness")); import traces; traces.ecrire(AGENT, "passage", "terminé" if _code == 0 else "échec", time.time() - _t0, ok=_code == 0, erreur=None if _code == 0 else f"code {_code}")
        except Exception: pass
    sys.exit(_code)
