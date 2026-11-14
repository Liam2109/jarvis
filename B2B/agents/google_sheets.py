#!/usr/bin/env python3
"""Google Drive pour l'agent appels-sid (OAuth « application de bureau », gratuit). N'affiche jamais le client, un jeton ni le détail d'une réponse de Google.

  pip install google-auth-oauthlib google-api-python-client      (déjà installés pour Gmail)
  python agents\\appels-sid.py google-autoriser                   autorisation de contact.lmsites@gmail.com dans le navigateur (une seule fois)

Même mécanisme que gmail_api.py : client OAuth agents\\google-client.json, jeton agents\\google-sheets-token.json (hors git, rafraîchi automatiquement), erreurs traduites sans détail.
Portée minimale : drive.file = l'agent ne voit et ne modifie QUE les dossiers et feuilles qu'il a lui-même créés (pas le reste du Drive). Une feuille est créée par conversion d'un CSV
envoyé à Drive : l'API Sheets n'est pas nécessaire. Seule l'API « Google Drive » doit être activée dans le projet Google Cloud du client OAuth."""
import io, json, warnings
from pathlib import Path
import gmail_api as GA

warnings.filterwarnings("ignore", message=".*Python version.*", category=FutureWarning)   # avis de fin de support de Python 3.11 des bibliothèques Google : sans effet, et il ferait échouer les scripts de test

ICI = Path(__file__).resolve().parent
CLIENT, JETON = ICI / "google-client.json", ICI / "google-sheets-token.json"
PORTEES = ["https://www.googleapis.com/auth/drive.file"]
DOSSIER_MIME, FEUILLE_MIME = "application/vnd.google-apps.folder", "application/vnd.google-apps.spreadsheet"
PIP = GA.PIP


class JetonExpire(Exception):
    def __init__(self): super().__init__("Jeton Google absent, expiré ou refusé : relance python agents\\appels-sid.py google-autoriser")


class ErreurDrive(Exception):
    def __init__(self, code=0, texte=""):
        self.code = code; super().__init__(texte or (f"HTTP {code}" if code else "réseau"))


def _traduire(e):
    """Erreur de la bibliothèque Google -> nos erreurs, par nom de classe. Aucun détail de la réponse n'est repris."""
    if isinstance(e, (JetonExpire, ErreurDrive)): return e
    nom = type(e).__name__
    if nom == "RefreshError": return JetonExpire()
    if nom == "HttpError":
        code = getattr(getattr(e, "resp", None), "status", 0)
        return JetonExpire() if code == 401 else ErreurDrive(code)
    if isinstance(e, OSError): return ErreurDrive(0, "réseau")
    return ErreurDrive(0, nom)


def _appel(requete):
    try: return requete.execute()
    except Exception as e: raise _traduire(e) from None


def _q(texte): return str(texte).replace("\\", "\\\\").replace("'", "\\'")


class Drive:
    """Les seuls appels utilisés : compte, dossier (chercher / créer), feuille (chercher / créer / lire), partage. Interface simple, remplaçable par un faux dans les tests."""
    def __init__(self, svc, adresse=""): self.svc, self.adresse = svc, adresse

    def compte(self):
        return _appel(self.svc.about().get(fields="user(emailAddress)")).get("user", {}).get("emailAddress", "")

    def _chercher(self, nom, mime, parent):
        q = f"name = '{_q(nom)}' and mimeType = '{mime}' and trashed = false and '{_q(parent or 'root')}' in parents"
        r = _appel(self.svc.files().list(q=q, fields="files(id)", spaces="drive", pageSize=10))
        return (r.get("files") or [{}])[0].get("id")

    def trouver_dossier(self, nom, parent=None): return self._chercher(nom, DOSSIER_MIME, parent)

    def lister_dossiers(self, parent):
        """(id, nom) des sous-dossiers directs d'un dossier, hors corbeille."""
        q = f"mimeType = '{DOSSIER_MIME}' and trashed = false and '{_q(parent)}' in parents"
        r = _appel(self.svc.files().list(q=q, fields="files(id,name)", spaces="drive", pageSize=1000))
        return [(f["id"], f["name"]) for f in r.get("files", [])]

    def mettre_corbeille(self, id_):
        """Corbeille (jamais une suppression définitive)."""
        _appel(self.svc.files().update(fileId=id_, body={"trashed": True}, fields="id"))

    def creer_dossier(self, nom, parent=None):
        corps = {"name": nom, "mimeType": DOSSIER_MIME}
        if parent: corps["parents"] = [parent]
        return _appel(self.svc.files().create(body=corps, fields="id"))["id"]

    def trouver_feuille(self, dossier, titre): return self._chercher(titre, FEUILLE_MIME, dossier)

    def creer_feuille(self, dossier, titre, contenu_csv):
        """Crée la feuille en convertissant un CSV (séparateur « , »). Ne remplace jamais une feuille existante."""
        try: from googleapiclient.http import MediaIoBaseUpload
        except ImportError: raise GA.BibliothequeManquante("Bibliothèques Google absentes : " + PIP) from None
        media = MediaIoBaseUpload(io.BytesIO(contenu_csv.encode("utf-8")), mimetype="text/csv", resumable=False)
        return _appel(self.svc.files().create(body={"name": titre, "mimeType": FEUILLE_MIME, "parents": [dossier]}, media_body=media, fields="id"))["id"]

    def lire_feuille(self, id_):
        """Contenu CSV (texte, séparateur « , » : c'est Sheets qui régénère l'export) d'une feuille déjà créée par cet agent.
        La portée drive.file suffit : elle couvre les fichiers créés par ce jeton, même partagés ensuite avec Sid."""
        brut = _appel(self.svc.files().export(fileId=id_, mimeType="text/csv"))
        return brut.decode("utf-8") if isinstance(brut, bytes) else str(brut)

    def partager(self, dossier, email):
        _appel(self.svc.permissions().create(fileId=dossier, body={"type": "user", "role": "writer", "emailAddress": email}, sendNotificationEmail=True, fields="id"))

    def lire_feuille_csv(self, id_):
        """Contenu CSV actuel d'une feuille créée par cette app (export Drive, pas l'API Sheets : lecture seule, même portée drive.file). Sert à relire ce que Sid a coché (appels-sid, « A rappeler »)."""
        r = _appel(self.svc.files().export(fileId=id_, mimeType="text/csv"))
        return r.decode("utf-8") if isinstance(r, (bytes, bytearray)) else r

    def lister_feuilles(self, parent):
        """(id, nom) des feuilles Google directement dans un dossier, hors corbeille (portée drive.file : seulement celles créées par cette app)."""
        q = f"mimeType = '{FEUILLE_MIME}' and trashed = false and '{_q(parent)}' in parents"
        r = _appel(self.svc.files().list(q=q, fields="files(id,name)", spaces="drive", pageSize=1000))
        return [(f["id"], f["name"]) for f in r.get("files", [])]

    def formater_feuille(self, id_, largeurs_px, liste=None):
        """Mise en forme lisible d'une feuille convertie depuis un CSV (un seul onglet, le premier) : ligne 1 figée, largeur de chaque colonne (`largeurs_px`, en pixels, dans l'ordre des
        colonnes), texte renvoyé à la ligne partout ; `liste` = (indice de colonne, [valeurs]) : liste déroulante sous l'en-tête. Aucune cellule fusionnée.
        API Sheets (v4) : la portée drive.file autorise cette API sur un fichier créé par cette app, sans ré-autorisation."""
        try: from googleapiclient.discovery import build
        except ImportError: raise GA.BibliothequeManquante("Bibliothèques Google absentes : " + PIP) from None
        svc = build("sheets", "v4", credentials=credentials(), cache_discovery=False)
        # un CSV converti n'a PAS d'onglet 0 (test réel du 14/11/2026 : « No sheet with id: 0 ») : on lit l'identifiant du premier onglet
        sid = _appel(svc.spreadsheets().get(spreadsheetId=id_, fields="sheets(properties(sheetId))"))["sheets"][0]["properties"]["sheetId"]
        requetes = [{"updateSheetProperties": {"properties": {"sheetId": sid, "gridProperties": {"frozenRowCount": 1}}, "fields": "gridProperties.frozenRowCount"}}]
        for i, px in enumerate(largeurs_px):
            requetes.append({"updateDimensionProperties": {"range": {"sheetId": sid, "dimension": "COLUMNS", "startIndex": i, "endIndex": i + 1}, "properties": {"pixelSize": px}, "fields": "pixelSize"}})
        requetes.append({"repeatCell": {"range": {"sheetId": sid}, "cell": {"userEnteredFormat": {"wrapStrategy": "WRAP"}}, "fields": "userEnteredFormat.wrapStrategy"}})
        if liste:
            col, valeurs = liste
            requetes.append({"setDataValidation": {"range": {"sheetId": sid, "startRowIndex": 1, "startColumnIndex": col, "endColumnIndex": col + 1},
                             "rule": {"condition": {"type": "ONE_OF_LIST", "values": [{"userEnteredValue": v} for v in valeurs]}, "showCustomUi": True, "strict": True}}})
        _appel(svc.spreadsheets().batchUpdate(spreadsheetId=id_, body={"requests": requetes}))


def credentials():
    """Jeton valide (rafraîchi et réenregistré si besoin), sinon JetonExpire."""
    if not JETON.exists(): raise JetonExpire()
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
    except ImportError: raise GA.BibliothequeManquante("Bibliothèques Google absentes : " + PIP) from None
    try: cr = Credentials.from_authorized_user_file(str(JETON), PORTEES)
    except (ValueError, KeyError, OSError): raise JetonExpire() from None
    if not cr.valid:
        if not cr.refresh_token: raise JetonExpire()
        try: cr.refresh(Request())
        except Exception as e: raise _traduire(e) from None
        JETON.write_text(cr.to_json(), encoding="utf-8")
    return cr


def ouvrir(adresse=""):
    """Drive du jeton enregistré. Peut lever JetonExpire, BibliothequeManquante, ErreurDrive."""
    try: from googleapiclient.discovery import build
    except ImportError: raise GA.BibliothequeManquante("Bibliothèques Google absentes : " + PIP) from None
    return Drive(build("drive", "v3", credentials=credentials(), cache_discovery=False), adresse)


def autoriser(adresse):
    """Flux « installed app » : le navigateur s'ouvre (adresse pré-remplie), Liam valide (avertissement « application non validée » normal).
    Le jeton n'est enregistré qu'après avoir vérifié que le compte autorisé est bien celui demandé."""
    try: from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError: raise GA.BibliothequeManquante("Bibliothèques Google absentes : " + PIP) from None
    if not CLIENT.exists(): raise FileNotFoundError("agents\\google-client.json absent")
    cr = None
    for essai in range(1, 4):
        try:
            cr = InstalledAppFlow.from_client_secrets_file(str(CLIENT), PORTEES).run_local_server(
                port=0, login_hint=adresse, authorization_prompt_message="  lien (si besoin) : {url}",
                success_message="Autorisation reçue : tu peux fermer cet onglet.")
            break
        except Exception as e:
            if essai == 3: raise
            print(f"  ! tentative {essai}/3 interrompue ({type(e).__name__}, souvent une connexion parasite du navigateur) : nouvelle tentative, nouveau lien")
    try: from googleapiclient.discovery import build
    except ImportError: raise GA.BibliothequeManquante("Bibliothèques Google absentes : " + PIP) from None
    vraie = Drive(build("drive", "v3", credentials=cr, cache_discovery=False), adresse).compte()
    if vraie.lower() != adresse.lower(): raise ErreurDrive(403, f"le compte autorisé est {vraie}, pas {adresse} : jeton non enregistré")
    JETON.write_text(cr.to_json(), encoding="utf-8")
