#!/usr/bin/env python3
"""Agent alerte-candidatures (LM MULTI-SERVICES, 17/11/2026) : prévient Liam sur Discord dès qu'un candidat remplit le formulaire « Postuler comme call caller – LM Multi-Services »
(feuille de réponses Google Sheets liée au formulaire), pour qu'il le rappelle dans l'heure. Une ligne = une alerte, jamais deux fois la même ; une seule relance si la colonne
« Contacté » est encore vide 2 h après l'alerte. Sous chaque alerte : un brouillon de message au candidat, que Liam envoie LUI-MÊME (rien n'est jamais envoyé au candidat).
Même modèle que les autres agents B2B : réglages (alerte-candidatures-config.json + .local.json), état (alerte-candidatures-etat.json), journal, trace du harness.

VERROU : rien n'est lu ni envoyé tant que `go_alerte` n'est pas true dans alerte-candidatures-config.local.json (posé seulement après le « go alerte » écrit par Liam).
`envoi_automatique: false` (défaut) = SIMULATION : rien sur Discord, la console (et le journal) disent ce qui serait envoyé.

  python agents\\alerte-candidatures.py verifier [--a-blanc]          un passage (toutes les 5 minutes une fois planifié) : nouvelles lignes -> alertes ; relance à 2 h
  python agents\\alerte-candidatures.py etat                          candidatures du jour, non contactées, verrou
  python agents\\alerte-candidatures.py google-autoriser               autorisation (une seule fois, par Liam, dans le navigateur) du compte qui possède la feuille de réponses

Écriture dans la feuille : UNIQUEMENT l'en-tête « Contacté » (ligne 1, première colonne libre) s'il manque. Rien d'autre n'est jamais écrit, rien n'est inventé : un champ absent
de la feuille est simplement omis du message. Premier passage (état vide) : les lignes déjà présentes sont mémorisées SANS alerte (pas de rafale), le journal le dit.
Accès Google : jeton séparé (google-candidatures-token.json, hors git), portée « spreadsheets » (la portée drive.file d'appels-sid ne voit pas une feuille créée par Google Forms)."""
import argparse, hashlib, json, re, sys, time, unicodedata
from datetime import datetime
from pathlib import Path

ICI = Path(__file__).resolve().parent
RACINE = ICI.parent
sys.path.insert(0, str(ICI))
import machine as M   # config locale et machine active (b2b.local.json)
import prospection as P   # P.acces_discord / P.discord : salon Discord habituel, garde du harness avant chaque POST

AGENT = "alerte-candidatures"
CONFIG, ETAT, JOURNAL = ICI / f"{AGENT}-config.json", ICI / f"{AGENT}-etat.json", ICI / f"{AGENT}-journal.log"
JETON = ICI / "google-candidatures-token.json"
PORTEES = ["https://www.googleapis.com/auth/spreadsheets"]
DEFAUT = {"go_alerte": False, "envoi_automatique": False, "intervalle_minutes": 5, "relance_minutes": 120, "feuille_id": "", "onglet": "",
          "compte_google": "contact.lmsites@gmail.com", "colonne_contacte": "Contacté"}
GARDE_JOURS = 60
LIBELLES = [("nom", "Nom"), ("telephone", "Téléphone"), ("email", "E-mail"), ("ville", "Ville"), ("dispos", "Disponibilités"), ("message", "Message")]
BROUILLON = ("Merci pour votre candidature de call caller. Le principe est simple : vous appelez des commerçants et des artisans pour leur proposer un site internet, "
             "et vous touchez 15 % de commission sur chaque vente que vous amenez. C'est uniquement à la commission, sans fixe. "
             "Je vous propose un rendez-vous de 15 minutes en visio pour tout vous expliquer et répondre à vos questions. Quand êtes-vous disponible ? "
             "Liam, LM Multi-Services")


class ErreurAgent(Exception):
    """Problème signalé à Liam (message clair, code de sortie 2) : l'agent s'arrête sans rien écrire de plus."""


# --- points d'accès au monde extérieur (remplacés par des doublures dans les tests) ---------------------------------
def maintenant(): return time.time()


class Feuille:
    """Les deux seuls appels : lire toutes les valeurs d'un onglet, écrire UNE cellule d'en-tête. API Sheets v4, jeton séparé."""
    def __init__(self, svc, feuille_id, onglet=""):
        self.svc, self.id = svc, feuille_id
        if not onglet:
            import google_sheets as GS
            meta = GS._appel(svc.spreadsheets().get(spreadsheetId=feuille_id, fields="sheets(properties(title))"))
            onglet = meta["sheets"][0]["properties"]["title"]
        self.onglet = onglet

    def _plage(self, a1=""): return "'" + self.onglet.replace("'", "''") + "'" + (f"!{a1}" if a1 else "")

    def lire(self):
        import google_sheets as GS
        return GS._appel(self.svc.spreadsheets().values().get(spreadsheetId=self.id, range=self._plage())).get("values", [])

    def ecrire_entete(self, colonne, texte):
        import google_sheets as GS
        GS._appel(self.svc.spreadsheets().values().update(spreadsheetId=self.id, range=self._plage(f"{lettre(colonne)}1"), valueInputOption="RAW", body={"values": [[texte]]}))


def _credentials():
    import google_sheets as GS
    if not JETON.exists(): raise GS.JetonExpire()
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
    except ImportError: raise GS.GA.BibliothequeManquante("Bibliothèques Google absentes : " + GS.PIP) from None
    try: cr = Credentials.from_authorized_user_file(str(JETON), PORTEES)
    except (ValueError, KeyError, OSError): raise GS.JetonExpire() from None
    if not cr.valid:
        if not cr.refresh_token: raise GS.JetonExpire()
        try: cr.refresh(Request())
        except Exception as e: raise GS._traduire(e) from None
        JETON.write_text(cr.to_json(), encoding="utf-8")
    return cr


def ouvrir_feuille(conf):
    from googleapiclient.discovery import build
    return Feuille(build("sheets", "v4", credentials=_credentials(), cache_discovery=False), conf["feuille_id"], conf["onglet"])


def alerter_discord(texte):
    """Salon Discord habituel des agents ; jeton lu par prospection.py dans Jarvis\\.env, jamais affiché ; la garde du harness passe avant chaque POST."""
    try:
        a = P.acces_discord()
        if not a: return False
        jeton, salon, uid = a
        r = P.discord(jeton, "POST", f"/channels/{salon}/messages", {"content": f"<@{uid}> {texte}"[:1900], "allowed_mentions": {"users": [uid]}})
        return bool(r and "id" in r)
    except Exception as ex: print(f"  alerte Discord impossible ({type(ex).__name__})"); return False


# --- réglages, état, journal ------------------------------------------------------------------------------------
def cfg():
    c = dict(DEFAUT)
    try:
        if CONFIG.exists(): c.update({k: v for k, v in json.loads(CONFIG.read_text(encoding="utf-8-sig")).items() if not k.startswith("_")})
    except (OSError, ValueError): raise ErreurAgent(f"réglages illisibles : {CONFIG.name}")
    try: M.surcharge_locale(CONFIG, c)
    except M.ErreurLocale as e: raise ErreurAgent(str(e))
    c["go_alerte"] = c.get("go_alerte") is True; c["envoi_automatique"] = c.get("envoi_automatique") is True
    for k, bas, haut in (("intervalle_minutes", 1, 1440), ("relance_minutes", 10, 1440)):
        n = c.get(k); c[k] = n if isinstance(n, int) and not isinstance(n, bool) and bas <= n <= haut else DEFAUT[k]
    for k in ("feuille_id", "onglet", "compte_google", "colonne_contacte"): c[k] = str(c.get(k) or DEFAUT[k]).strip()
    return c


def etat_lire():
    try: e = json.loads(ETAT.read_text(encoding="utf-8")) if ETAT.exists() else {}
    except (OSError, ValueError): raise ErreurAgent(f"état illisible ({ETAT.name}) : rien n'est écrit ; corrigez ou supprimez le fichier à la main")
    if not isinstance(e, dict): raise ErreurAgent(f"état illisible ({ETAT.name}) : rien n'est écrit")
    e.setdefault("initialise", False); e.setdefault("candidats", {})
    return e


def etat_ecrire(e): ETAT.write_text(json.dumps(e, ensure_ascii=False, indent=1), encoding="utf-8")


def journaliser(action, detail="", a_blanc=False):
    if a_blanc: return
    with open(JOURNAL, "a", encoding="utf-8") as f: f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} | {action} | {detail}\n")


# --- lecture des lignes du formulaire ---------------------------------------------------------------------------
def lettre(i):
    """Indice de colonne (0 = A) -> lettres A1."""
    s = ""; i += 1
    while i: i, r = divmod(i - 1, 26); s = chr(65 + r) + s
    return s


def _plat(t): return "".join(c for c in unicodedata.normalize("NFD", str(t).lower()) if unicodedata.category(c) != "Mn")


def colonnes(entete, nom_contacte):
    """Champ -> liste d'indices de colonnes, d'après le texte des questions du formulaire (aucune colonne devinée au hasard : sans correspondance, le champ est omis)."""
    cols = {}; contacte = _plat(nom_contacte)
    for i, h in enumerate(entete):
        t = _plat(h).strip()
        if not t: continue
        if t == contacte or t.startswith("contacte"): champ = "contacte"
        elif any(m in t for m in ("horodateur", "horodatage", "timestamp")): champ = "horodateur"
        elif "mail" in t: champ = "email"
        elif any(m in t for m in ("telephone", "portable", "numero", "tel ", "tel.")) or t == "tel": champ = "telephone"
        elif any(m in t for m in ("ville", "commune", "localisation", "ou habitez", "ou vivez")): champ = "ville"
        elif "dispo" in t: champ = "dispos"
        elif "prenom" in t or re.search(r"\bnom\b", t): champ = "nom"
        elif any(m in t for m in ("message", "motivation", "pourquoi", "parlez", "presentez", "commentaire", "experience", "autre chose")): champ = "message"
        else: continue
        cols.setdefault(champ, []).append(i)
    return cols


def valeur(ligne, cols, champ):
    return " ".join(ligne[i].strip() for i in cols.get(champ, []) if i < len(ligne) and str(ligne[i]).strip())


def cle(ligne, cols):
    """Identifiant stable d'une réponse (empreinte, aucune donnée du candidat dans l'état) : horodateur + e-mail + téléphone si la feuille a un horodateur (Google Forms en met
    toujours un : corriger une faute dans la ligne ne crée pas une « nouvelle » candidature), sinon la ligne entière hors « Contacté »."""
    base = [valeur(ligne, cols, c) for c in ("horodateur", "email", "telephone")] if valeur(ligne, cols, "horodateur") else [str(x).strip() for x in ligne]
    return hashlib.sha1("\x1f".join(base).encode("utf-8")).hexdigest()[:16]


def message_alerte(ligne, cols):
    l = ["Nouvelle candidature call caller — **À rappeler dans l'heure.**"]
    for champ, lib in LIBELLES:
        v = valeur(ligne, cols, champ)
        if v: l.append(f"{lib} : {v[:400]}")
    l += ["", "Brouillon à envoyer vous-même (rien n'est parti) :", f"« {BROUILLON} »", "Une fois rappelé : mettez « oui » dans la colonne Contacté de la feuille."]
    return "\n".join(l)


def message_relance(ligne, cols, alerte_ts):
    qui = valeur(ligne, cols, "nom") or "un candidat"; tel = valeur(ligne, cols, "telephone")
    return (f"Relance candidature : {qui} (alerte de {datetime.fromtimestamp(alerte_ts):%H:%M}) n'est pas marqué « Contacté » depuis 2 h."
            + (f" Téléphone : {tel}." if tel else "") + " Mettez « oui » dans la colonne Contacté une fois rappelé.")


# --- le passage -------------------------------------------------------------------------------------------------
def poster(conf, texte, action):
    if conf["envoi_automatique"]:
        ok = alerter_discord(texte); print(texte); print("  (posté sur Discord)" if ok else "  ! Discord : non envoyé (voir ci-dessus)")
    else:
        print(f"[simulation : envoi_automatique=false] {texte}")
    journaliser(action, "message Discord (sans donnée du candidat dans le journal)")


def cmd_verifier(conf, a_blanc, feuille=None):
    if not conf["go_alerte"]:
        print("Verrou : Liam n'a pas encore écrit « go alerte » (go_alerte absent de alerte-candidatures-config.local.json) : rien lu, rien envoyé."); return 0
    if not conf["feuille_id"]:
        print("  ! feuille_id absent : liez le formulaire à une feuille (Réponses > Lier à Sheets) et mettez son identifiant dans alerte-candidatures-config.local.json")
        journaliser("verifier", "feuille_id absent", a_blanc); return 0
    etat = etat_lire()
    try:
        f = feuille or ouvrir_feuille(conf); lignes = f.lire()
    except Exception as ex:
        print(f"  ! feuille de réponses illisible ({type(ex).__name__}) : le prochain passage réessaie"); journaliser("verifier", f"feuille illisible ({type(ex).__name__})", a_blanc); return 2
    if not lignes: print("Feuille vide : aucune candidature."); journaliser("verifier", "feuille vide", a_blanc); return 0
    entete = lignes[0]; cols = colonnes(entete, conf["colonne_contacte"]); ic = (cols.get("contacte") or [None])[0]
    if ic is None:
        if a_blanc: print(f"[à blanc] colonne « {conf['colonne_contacte']} » absente : elle serait créée (en-tête seulement, colonne {lettre(len(entete))})")
        else:
            try: f.ecrire_entete(len(entete), conf["colonne_contacte"]); journaliser("contacte", f"en-tête « {conf['colonne_contacte']} » créé en colonne {lettre(len(entete))}")
            except Exception as ex: print(f"  ! en-tête « {conf['colonne_contacte']} » non créé ({type(ex).__name__})")
    cols_sans = {k: v for k, v in cols.items() if k != "contacte"}
    sans = lambda l: [x if j != ic else "" for j, x in enumerate(l)]   # la clé ignore « Contacté » : cocher la case ne crée pas une « nouvelle » ligne
    t = maintenant(); jour = datetime.fromtimestamp(t).date().isoformat()
    vues = [(cle(sans(l), cols_sans), l) for l in lignes[1:] if any(str(x).strip() for x in sans(l))]
    if not etat["initialise"]:
        if a_blanc: print(f"[à blanc] premier passage : {len(vues)} candidature(s) déjà dans la feuille, mémorisée(s) sans alerte"); return 0
        for k, l in vues: etat["candidats"][k] = {"jour": "", "alerte": 0, "relance": True, "contacte": True}
        etat["initialise"] = True; etat_ecrire(etat)
        journaliser("verifier", f"premier passage : {len(vues)} candidature(s) existante(s) mémorisée(s) sans alerte")
        print(f"Premier passage : {len(vues)} candidature(s) déjà présente(s), aucune alerte (point de départ fixé)."); return 0
    nouvelles = relances = 0
    for k, l in vues:
        contacte = bool(ic is not None and ic < len(l) and str(l[ic]).strip())
        c = etat["candidats"].get(k)
        if c is None:
            nouvelles += 1
            if a_blanc: print("[à blanc] alerte : " + message_alerte(l, cols)); continue
            poster(conf, message_alerte(l, cols), "alerte")
            etat["candidats"][k] = {"jour": jour, "alerte": t, "relance": False, "contacte": contacte}; continue
        c["contacte"] = contacte
        if not contacte and not c["relance"] and c["alerte"] and t - c["alerte"] >= conf["relance_minutes"] * 60:
            relances += 1
            if a_blanc: print("[à blanc] relance : " + message_relance(l, cols, c["alerte"])); continue
            poster(conf, message_relance(l, cols, c["alerte"]), "relance"); c["relance"] = True
    if a_blanc: print(f"[à blanc] {nouvelles} nouvelle(s), {relances} relance(s) ; rien écrit ni envoyé."); return 0
    for k in [k for k, c in etat["candidats"].items() if c.get("alerte") and t - c["alerte"] > GARDE_JOURS * 86400]: del etat["candidats"][k]
    etat_ecrire(etat)
    journaliser("verifier", f"{nouvelles} nouvelle(s) candidature(s), {relances} relance(s)")
    print(f"{nouvelles} nouvelle(s) candidature(s), {relances} relance(s).")
    return 0


def compte_jour(jour, etat=None):
    """(candidatures alertées ce jour, dont non contactées) d'après l'état ; None si l'agent n'a jamais tourné (verrou). Utilisé par le résumé du soir (resume-sid)."""
    try: e = etat if etat is not None else etat_lire()
    except ErreurAgent: return None
    if not e.get("initialise"): return None
    du_jour = [c for c in e["candidats"].values() if c.get("jour") == jour]
    return len(du_jour), sum(1 for c in du_jour if not c.get("contacte"))


def cmd_etat(conf):
    print(f"Verrou « go alerte » : {'levé' if conf['go_alerte'] else 'fermé (rien ne tourne)'} ; feuille : {'renseignée' if conf['feuille_id'] else 'absente'} ; "
          f"mode : {'réel' if conf['envoi_automatique'] else 'simulation'}.")
    n = compte_jour(datetime.now().date().isoformat())
    print("Aucun passage pour l'instant." if n is None else f"Aujourd'hui : {n[0]} candidature(s), {n[1]} non contactée(s)."); return 0


def cmd_autoriser(conf):
    """Flux « installed app » (navigateur), lancé par Liam lui-même ; jeton enregistré seulement si le compte est le bon."""
    import google_sheets as GS
    from google_auth_oauthlib.flow import InstalledAppFlow
    if not GS.CLIENT.exists(): raise ErreurAgent("agents\\google-client.json absent")
    cr = InstalledAppFlow.from_client_secrets_file(str(GS.CLIENT), PORTEES).run_local_server(port=0, login_hint=conf["compte_google"],
            authorization_prompt_message="  lien (si besoin) : {url}", success_message="Autorisation reçue : tu peux fermer cet onglet.")
    JETON.write_text(cr.to_json(), encoding="utf-8"); print("Jeton enregistré (google-candidatures-token.json, hors git)."); return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog=AGENT, description="Alerte Discord sur nouvelle candidature call caller (rien n'est envoyé au candidat).")
    base = argparse.ArgumentParser(add_help=False); base.add_argument("--a-blanc", action="store_true", help="affiche sans rien écrire ni envoyer")
    sp = p.add_subparsers(dest="cmd", required=True)
    for nom in ("verifier", "etat", "google-autoriser"): sp.add_parser(nom, parents=[base])
    args = p.parse_args(argv); M.exiger(AGENT, args.cmd, getattr(args, "a_blanc", False))
    try:
        conf = cfg()
        if args.cmd == "verifier": return cmd_verifier(conf, args.a_blanc)
        if args.cmd == "etat": return cmd_etat(conf)
        return cmd_autoriser(conf)
    except ErreurAgent as e:
        print(f"  ! {e}"); return 2
    except OSError as e:
        print(f"  ! erreur de fichier : {e.strerror or type(e).__name__}"); return 2


if __name__ == "__main__":
    _t0 = time.time(); _code = main()
    if sys.argv[1:2] == ["verifier"] and "--a-blanc" not in sys.argv:   # trace du harness (B2B\logs\agents\alerte-candidatures), jamais bloquante
        try: sys.path.insert(0, str(ICI.parent / "harness")); import traces; traces.ecrire(AGENT, "verifier", "terminé" if _code == 0 else "échec", time.time() - _t0, ok=_code == 0, erreur=None if _code == 0 else f"code {_code}")
        except Exception: pass
    sys.exit(_code)
