#!/usr/bin/env python3
"""Gmail par l'API officielle (OAuth « application de bureau »), à la place d'IMAP / mot de passe d'application. N'affiche jamais le client ni un jeton.

  pip install google-auth-oauthlib google-api-python-client      (une seule fois)
  python agents\\test-gmail-api.py <adresse>                      autorisation de CE compte dans le navigateur (une fois), affiche « OK, adresse = … »
  python agents\\test-gmail-api.py                                teste tous les comptes déjà autorisés

Plusieurs comptes : même client OAuth (agents\\gmail-client.json), un jeton par compte (agents\\gmail-token-<adresse>.json, hors git).
Portées minimales : gmail.send (envoyer) et gmail.readonly (lire sans rien marquer ni supprimer).
Les comptes utilisés sont listés dans agents\\reponses-config.json › api › comptes (jamais dans identite.json).
Jeton absent, expiré ou refusé -> JetonExpire, message « relance python agents\\test-gmail-api.py <adresse> » ; l'appelant saute CE compte et continue avec les autres."""
import base64, json
from pathlib import Path

import sys
ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import machine as M
CLIENT, CONFIG, DOSSIER = ICI / "gmail-client.json", ICI / "reponses-config.json", ICI
PORTEES = ["https://www.googleapis.com/auth/gmail.send", "https://www.googleapis.com/auth/gmail.readonly"]
PIP = "pip install google-auth-oauthlib google-api-python-client"


class JetonExpire(Exception):
    def __init__(self, adresse=""):
        self.adresse = adresse
        super().__init__(f"Jeton Gmail{' de ' + adresse if adresse else ''} absent, expiré ou refusé : relance python agents\\test-gmail-api.py{' ' + adresse if adresse else ''}")


class BibliothequeManquante(Exception): pass


class ErreurApi(Exception):
    def __init__(self, code=0, texte=""):
        self.code = code; super().__init__(texte or (f"HTTP {code}" if code else "réseau"))


def chemin_jeton(adresse):
    return DOSSIER / f"gmail-token-{adresse.strip().lower()}.json"


def comptes_autorises():
    """Adresses ayant un jeton enregistré (le jeton lui-même n'est pas lu)."""
    pre, suf = "gmail-token-", ".json"
    return sorted(p.name[len(pre):-len(suf)] for p in DOSSIER.glob(pre + "*" + suf))


def jeton_existe(adresse): return chemin_jeton(adresse).exists()


def _traduire(e, adresse=""):
    """Erreur de la bibliothèque Google -> nos erreurs (par nom de classe : testable sans les bibliothèques). Aucun détail de la réponse n'est repris."""
    if isinstance(e, (JetonExpire, ErreurApi)): return e
    nom = type(e).__name__
    if nom == "RefreshError": return JetonExpire(adresse)
    if nom == "HttpError":
        code = getattr(getattr(e, "resp", None), "status", 0)
        return JetonExpire(adresse) if code == 401 else ErreurApi(code)
    if isinstance(e, OSError): return ErreurApi(0, "réseau")
    return ErreurApi(0, nom)


def _appel(requete, adresse=""):
    try: return requete.execute()
    except Exception as e: raise _traduire(e, adresse) from None


def bibliotheques():
    """Vérifie que les bibliothèques officielles sont installées (sinon BibliothequeManquante avec la commande pip)."""
    try: import google_auth_oauthlib.flow, googleapiclient.discovery  # noqa: F401
    except ImportError: raise BibliothequeManquante("Bibliothèques Google absentes : " + PIP) from None


def credentials(adresse):
    """Jeton valide du compte (rafraîchi et réenregistré si besoin), sinon JetonExpire."""
    jeton = chemin_jeton(adresse)
    if not jeton.exists(): raise JetonExpire(adresse)
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
    except ImportError: raise BibliothequeManquante("Bibliothèques Google absentes : " + PIP) from None
    try: cr = Credentials.from_authorized_user_file(str(jeton), PORTEES)
    except (ValueError, KeyError, OSError): raise JetonExpire(adresse) from None
    if not cr.valid:
        if not cr.refresh_token: raise JetonExpire(adresse)
        try: cr.refresh(Request())
        except Exception as e: raise _traduire(e, adresse) from None
        jeton.write_text(cr.to_json(), encoding="utf-8")
    return cr


class Client:
    """Les seuls appels utilisés : profil, liste, en-têtes, message brut, envoi. Interface simple, remplaçable par un faux dans les tests."""
    def __init__(self, svc, adresse=""):
        self.svc, self.adresse = svc, adresse

    def profil(self):
        return _appel(self.svc.users().getProfile(userId="me"), self.adresse).get("emailAddress", "")

    def ids(self, requete, maxi=500):
        out, page = [], None
        while len(out) < maxi:
            r = _appel(self.svc.users().messages().list(userId="me", q=requete, maxResults=100, pageToken=page), self.adresse)
            out += [m["id"] for m in r.get("messages", [])]; page = r.get("nextPageToken")
            if not page: break
        return out[:maxi]

    def entetes(self, gid):  # en-têtes seulement, clés en minuscules
        r = _appel(self.svc.users().messages().get(userId="me", id=gid, format="metadata", metadataHeaders=["From", "Subject", "Message-ID", "Reply-To"]), self.adresse)
        return {h["name"].lower(): h["value"] for h in r.get("payload", {}).get("headers", [])}

    def brut(self, gid):
        r = _appel(self.svc.users().messages().get(userId="me", id=gid, format="raw"), self.adresse)
        return base64.urlsafe_b64decode(r["raw"] + "=" * (-len(r["raw"]) % 4))

    def envoyer(self, msg):
        """Envoie un EmailMessage. Renvoie l'identifiant Gmail du message envoyé."""
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        return _appel(self.svc.users().messages().send(userId="me", body={"raw": raw}), self.adresse).get("id", "")


def _service(cr):
    try: from googleapiclient.discovery import build
    except ImportError: raise BibliothequeManquante("Bibliothèques Google absentes : " + PIP) from None
    return build("gmail", "v1", credentials=cr, cache_discovery=False)


def client(adresse):
    """Client du compte (jeton valide, adresse vérifiée dans le profil). Peut lever JetonExpire, BibliothequeManquante, ErreurApi."""
    c = Client(_service(credentials(adresse)), adresse)
    vraie = c.profil()
    if vraie.lower() != adresse.lower(): raise ErreurApi(403, f"le jeton de {adresse} appartient à un autre compte")
    c.adresse = vraie; return c


def autoriser(adresse):
    """Flux « installed app » pour CE compte : le navigateur s'ouvre (adresse pré-remplie), Liam valide (avertissement « application non validée » normal).
    Le jeton n'est enregistré qu'après avoir vérifié que le compte autorisé est bien celui demandé."""
    try: from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError: raise BibliothequeManquante("Bibliothèques Google absentes : " + PIP) from None
    if not CLIENT.exists(): raise FileNotFoundError("agents\\gmail-client.json absent")
    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT), PORTEES)
    cr = flow.run_local_server(port=0, login_hint=adresse, authorization_prompt_message="", success_message="Autorisation reçue : tu peux fermer cet onglet.")
    vraie = Client(_service(cr), adresse).profil()
    if vraie.lower() != adresse.lower(): raise ErreurApi(403, f"le compte autorisé est {vraie}, pas {adresse} : jeton non enregistré")
    chemin_jeton(adresse).write_text(cr.to_json(), encoding="utf-8")


def enregistrer_adresse(adresse, chemin=None):
    """Ajoute le compte à reponses-config.json › api › comptes (le reste du fichier est conservé ; l'ancienne clé « adresse » est reprise dans la liste)."""
    chemin = chemin or CONFIG
    c = M.lire_fusionnee(chemin)      # défaut + local ; l'ajout est écrit dans le fichier LOCAL (jamais dans le fichier versionné)
    api = c.setdefault("api", {}); api.setdefault("actif", True)
    liste = [x.lower() for x in api.get("comptes", [])] or ([api["adresse"].lower()] if api.get("adresse") else [])
    api.pop("adresse", None)
    if adresse.lower() not in liste: liste.append(adresse.lower())
    api["comptes"] = liste
    M.ecrire_local(chemin, {"api": {"actif": api["actif"], "comptes": liste}})
