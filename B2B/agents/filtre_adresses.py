#!/usr/bin/env python3
"""Filtre des adresses e-mail AVANT la mise en lot (cmd_preparer). Vérifications gratuites et hors ligne ou DNS public seulement : aucun mail de test, aucun service payant, rien d'écrit.

controle_adresse(ligne, exclus, recoit_courrier) -> (motif, avertissements)
  motif = chaîne non vide : l'adresse est écartée du lot (syntaxe, faute de frappe probable sur un domaine grand public, déjà rebondie ou exclue, aucune source visible, domaine qui ne reçoit pas de courrier).
  avertissements = remarques NON bloquantes, affichées dans le bloc du lot pour que Liam voie d'où vient l'adresse et ce qui la rend moins sûre.
etiquette_origine(ligne) -> ligne de texte « Origine de l'adresse » du bloc.
Un doute (DNS injoignable, source d'un genre inconnu) n'écarte jamais : on n'exclut que sur une certitude."""
import re

GRAND_PUBLIC = {"gmail.com", "hotmail.com", "hotmail.fr", "outlook.com", "outlook.fr", "yahoo.fr", "yahoo.com", "orange.fr", "wanadoo.fr", "free.fr", "sfr.fr", "laposte.net", "live.fr", "icloud.com", "neuf.fr", "bbox.fr"}
SYNTAXE = re.compile(r"^[a-z0-9](?:[a-z0-9._%+-]{0,62}[a-z0-9])?@(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,24}$")
MOTIF_SYNTAXE, MOTIF_EXCLU, MOTIF_SANS_SOURCE, MOTIF_MX = "adresse mal formée", "adresse déjà rebondie ou exclue (exclus-emails.json, STOP, refus)", "adresse sans source visible (déduite ?)", "le domaine ne reçoit pas de courrier (aucun enregistrement MX)"


def distance_un(a, b):
    """Vrai si a et b diffèrent d'UNE seule lettre (substitution, ajout, retrait ou lettres permutées côte à côte) : « gmial.com », « gmai.com », « gmaill.com »."""
    if a == b: return False
    if abs(len(a) - len(b)) > 1: return False
    if len(a) == len(b):
        d = [i for i in range(len(a)) if a[i] != b[i]]
        return len(d) == 1 or (len(d) == 2 and d[1] == d[0] + 1 and a[d[0]] == b[d[1]] and a[d[1]] == b[d[0]])
    court, long_ = (a, b) if len(a) < len(b) else (b, a)
    return any(long_[:i] + long_[i + 1:] == court for i in range(len(long_)))


def faute_de_frappe(domaine, grand_public=GRAND_PUBLIC):
    """Domaine grand public bien connu auquel ce domaine ressemble à une lettre près (et qui n'en fait pas partie), sinon ''. Les domaines d'entreprise ne sont jamais comparés."""
    d = domaine.lower()
    if d in grand_public: return ""
    return next((g for g in sorted(grand_public) if len(g) >= 8 and distance_un(d, g)), "")   # 8 lettres au moins : « alive.fr » n'est pas une faute pour « live.fr »


def champ(ligne, *cles):
    """Première valeur non vide parmi plusieurs noms de colonne (le CSV du lot supprime les « _ » : email_source devient emailsource)."""
    return next((str(ligne.get(c) or "").strip() for c in cles if str(ligne.get(c) or "").strip()), "")


def origine(ligne):
    """(catégorie, détail) d'après la source notée au moment de la lecture de l'adresse. Catégories : site de l'entreprise, OpenStreetMap, saisie à la main, autre, inconnue."""
    s = champ(ligne, "email_source", "emailsource")
    if not s: return "inconnue", ""
    bas = s.lower()
    if bas.startswith("openstreetmap"): return "OpenStreetMap", "tag « email » d'une fiche OpenStreetMap (donnée libre, sans date)"
    if bas.startswith("saisie"): return "saisie à la main", s
    if bas.startswith("page contact"): return "site de l'entreprise", "page contact ou mentions légales : " + re.sub(r"^page contact[^:]*? de ", "", s, flags=re.I)
    if bas.startswith("page d'accueil"): return "site de l'entreprise", "page d'accueil : " + re.sub(r"^page d'accueil de ", "", s, flags=re.I)
    if bas.startswith("http"): return "site de l'entreprise", "page : " + s
    return "autre", s


def avertissements(ligne, grand_public=GRAND_PUBLIC):
    """Remarques non bloquantes (jamais un rejet) : ce qui rend l'adresse moins sûre d'après les 121 premiers envois (voir le rapport du 03/11/2026)."""
    a = champ(ligne, "email").lower(); u, _, d = a.partition("@"); cat, _ = origine(ligne); out = []
    if d in grand_public and cat == "OpenStreetMap": out.append("boîte grand public lue dans OpenStreetMap (donnée libre, sans date)")
    if d in grand_public and re.fullmatch(r"[a-z]+[._-][a-z]+", u): out.append("adresse personnelle (prénom.nom) sur une messagerie grand public")
    if cat == "autre": out.append("source d'un genre inconnu : " + champ(ligne, "email_source", "emailsource")[:60])
    return out


def etiquette_origine(ligne):
    """Ligne du bloc de lot : d'où vient l'adresse, et ce qui est à vérifier."""
    cat, detail = origine(ligne)
    txt = f"{cat}" + (f" — {detail}" if detail else "")
    av = avertissements(ligne)
    return txt + ("".join(f" ; ℹ à vérifier : {x}" for x in av))


def controle_adresse(ligne, exclus, recoit_courrier=None, grand_public=GRAND_PUBLIC):
    """-> (motif, avertissements). `exclus` : ensemble d'adresses en minuscules (prospection.exclusions()[1]). `recoit_courrier` : fonction domaine -> bool (DNS) ; None = pas de vérification DNS."""
    a = champ(ligne, "email").lower()
    if not a: return "", []
    if not SYNTAXE.match(a) or ".." in a: return MOTIF_SYNTAXE, []
    d = a.split("@")[1]
    f = faute_de_frappe(d, grand_public)
    if f: return f"domaine proche de {f} (faute de frappe probable)", []
    if a in exclus: return MOTIF_EXCLU, []
    if origine(ligne)[0] == "inconnue": return MOTIF_SANS_SOURCE, []
    if recoit_courrier is not None and not recoit_courrier(d): return MOTIF_MX, []
    return "", avertissements(ligne, grand_public)
