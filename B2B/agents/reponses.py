#!/usr/bin/env python3
"""Agent Réponses : repère les réponses des prospects, les classe, prévient Liam sur Discord. N'ENVOIE RIEN AU PROSPECT.

  python agents\\reponses.py [--jours 14] [--a-blanc]     lit la boîte Gmail (API OAuth si « api » est actif dans reponses-config.json, sinon les 2 boîtes en IMAP ; lecture seule), classe, poste les réponses positives
  python agents\\reponses.py --test [--a-blanc]           poste un faux message « TEST » ; ne lit aucune boîte, ne touche à aucun statut

Lecture : seulement les messages dont l'expéditeur est un e-mail connu de suivi-prospects.csv, ou dont l'objet est « Re: <nom du prospect> : une maquette… »
(même fil). Les autres messages ne sont jamais ouverts : on ne lit que leur en-tête. Boîte ouverte en lecture seule (rien n'est marqué lu).
Classes : positive, négative, STOP, autre. Doute = « autre » (aucune alerte Discord). STOP -> statut STOP ; négative -> statut refusé (les deux excluent le
prospect : l'agent Rédaction les saute) ; positive ou autre -> « répondu » (sauf si le prospect est déjà en devis, signé, STOP ou refusé).
Discord : API REST, jeton du bot Jarvis lu dans Jarvis\\.env (jamais affiché). Créneaux : agenda Google via son adresse iCal secrète (B2B\\.env, GOOGLE_AGENDA_ICAL_URL), jamais réservés.
Idempotence : agents\\reponses-traitees.json (identifiants de messages). --a-blanc : affiche au lieu de poster, ne change rien.
Réglages : agents\\reponses-config.json. Secrets : B2B\\.env (GMAIL_1_APP_PASSWORD, GMAIL_2_APP_PASSWORD pour le repli IMAP, GOOGLE_AGENDA_ICAL_URL).
Mode API (« api »: {"actif": true, "comptes": [...]}) : les comptes de api › comptes sont lus l'un après l'autre, un jeton par compte (agents\\gmail-token-<adresse>.json, agents\\test-gmail-api.py) ;
jeton absent, expiré ou refusé = message clair, CE compte est sauté, l'autre est lu quand même."""
import argparse, email, imaplib, json, re, sys, unicodedata, urllib.request, urllib.error
from datetime import date, datetime, timedelta, timezone
from email import policy
from email.header import decode_header, make_header
from email.utils import parseaddr
from html import unescape
from pathlib import Path

ICI = Path(__file__).resolve().parent
RACINE = ICI.parent
sys.path.insert(0, str(ICI))
import suivi as S, gmail_api as GA, machine as M   # machine : config locale + machine active
import reponse_auto as RA                            # maillon 1 : réponse courte avec créneaux (réglage reponse_auto_envoi, faux par défaut)

CONFIG, TRAITES = ICI / "reponses-config.json", ICI / "reponses-traitees.json"
RETOURS_FICHIER = ICI / "prospection-retours.json"   # rebonds et plaintes comptés ici (fichier à part : prospection-etat.json n'est écrit que par prospection.py)
EXCLUS_MAILS = ICI / "exclus-emails.json"             # adresses à ne plus jamais contacter (refus, STOP) : lues par prospection.exclusions() pour toutes les sources
RETOURS = {"rebonds": {}, "plaintes": {}}             # {identifiant du message: date}, rempli pendant la lecture
REBOND_DE = re.compile(r"mailer-daemon|postmaster", re.I)
REBOND_OBJET = re.compile(r"delivery status notification|undeliver|mail delivery (?:failed|subsystem)|returned mail|failure notice|non remis|adresse introuvable|[ée]chec de (?:la )?remise", re.I)
PLAINTE = re.compile(r"\bspam\b|plainte|signal(?:e|er) (?:ce|cette)|\bcnil\b|\brgpd\b|droit d.opposition", re.I)


def est_rebond(exp, objet):
    """Retour d'un serveur de messagerie pour une adresse inexistante ou refusée : reconnu par l'expéditeur et l'objet seuls (le corps n'est jamais lu)."""
    return bool(REBOND_DE.search(exp or "") and REBOND_OBJET.search(objet or ""))
ADRESSE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")


def envoyes_par_la_boucle():
    """Adresses de suivi-prospects.csv avec une date d'envoi (donc écrites par la boucle) ; un prospect passé en « exclu » après un rebond y reste."""
    return {r["email"].strip().lower() for r in S.lire() if (r.get("email") or "").strip() and (r.get("date_envoi") or "").strip()}


def rebond_lie(brut, envoyes=None):
    """Vrai si le rebond (message brut) concerne une adresse à qui la boucle a écrit : X-Failed-Recipients, Final-Recipient ou toute adresse du texte. Un rebond sans lien (ancien courrier, autre outil) n'est pas compté."""
    envoyes = envoyes_par_la_boucle() if envoyes is None else envoyes
    msg = email.message_from_bytes(brut, policy=policy.default); trouvees = set(ADRESSE.findall(str(msg["X-Failed-Recipients"] or "").lower()))
    for part in msg.walk():
        if part.get_content_type() in ("text/plain", "message/delivery-status", "message/rfc822"):
            try: t = part.get_content() if part.get_content_type() == "text/plain" else str(part)
            except Exception: continue
            trouvees |= set(ADRESSE.findall(t.lower()))
    return bool(trouvees & set(envoyes))


REFUS_POLITIQUE = re.compile(r"spam|blocked|block ?list|blacklist|reputation|policy|dkim|spf|dmarc|too many|rate limit|greylist", re.I)
ADRESSES_REBONDIES = set()   # adresses refusées définitivement, repérées pendant la lecture : ajoutées à exclus-emails.json en fin de lecture (jamais en mode à blanc)


def echecs_permanents(brut):
    """Adresses refusées DÉFINITIVEMENT d'après les blocs « delivery-status » du rebond : statut 5.x.x (boîte inexistante, domaine qui ne reçoit pas de courrier, relais refusé).
    Pas d'exclusion pour un retard (4.x.x : boîte pleine, serveur injoignable) ni pour un refus de politique (spam, réputation) : le problème n'est pas l'adresse."""
    msg = email.message_from_bytes(brut, policy=policy.default); out = set()
    for part in msg.walk():
        if part.get_content_type() != "message/delivery-status": continue
        for bloc in part.get_payload():
            if not str(bloc.get("Status") or "").strip().startswith("5.") or REFUS_POLITIQUE.search(str(bloc.get("Diagnostic-Code") or "")): continue
            out |= set(ADRESSE.findall(str(bloc.get("Final-Recipient") or "").lower()))
    return out


MOIS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
SIGNE_OBJET = "une maquette de site pour votre activité"


def lire_env(chemin):  # secrets : jamais affichés
    out = {}
    if chemin.exists():
        for l in chemin.read_text(encoding="utf-8-sig").splitlines():
            m = re.match(r"\s*([A-Z0-9_]+)\s*=\s*(.*?)\s*$", l)
            if m and not l.lstrip().startswith("#"): out[m.group(1)] = m.group(2).strip("\"'")
    return out


# ---------- classement (règles seulement : pas d'IA, pas de coût) ----------
STOP = re.compile(r"\bstop\b|d[ée]sabonn|d[ée]sinscri|ne plus (?:recevoir|m'?envoyer|me contacter|nous contacter|[ée]crire)|ne (?:me|nous) (?:re)?contactez plus|ne plus [êe]tre (?:contact|d[ée]rang)|arr[êe]t(?:ez|er) de (?:me|nous) (?:contacter|[ée]crire|envoyer)|"
                  r"supprimez (?:mon|nos|mes)|retirez (?:mon|nos|moi)|\bspam\b|\brgpd\b|droit d.opposition|plainte|signal(?:e|er) (?:ce|cette)", re.I)
NEGATIF = re.compile(r"pas int[ée]ress|non merci|pas besoin|aucun besoin|pas de besoin|ne souhaite pas|ne souhaitons pas|ne suis pas preneur|pas preneur|"
                     r"d[ée]j[àa] (?:un|une|mon|notre|quelqu)|ça ne m.int[ée]resse|cela ne m.int[ée]resse|pas pour moi|pas concern|refus|sans suite", re.I)
POSITIF = re.compile(r"int[ée]ress(?!ant)|devis|\bprix\b|tarifs?\b|combien|appelez[- ]moi|rappelez|me rappeler|nous rappeler|un appel|t[ée]l[ée]phone|rendez-vous|\brdv\b|"
                     r"pourquoi pas|d.accord|\boui\b|volontiers|avec plaisir|envoyez|montrez|plus d.infos?|plus de d[ée]tails|disponible", re.I)
# refus net : l'emporte même après des compliments (« votre approche est top, mais je refais mon site moi-même »), sauf demande d'appel, de devis ou de rendez-vous
NEGATIF_NET = re.compile(r"pas (?:un |une |votre |des )?clients?|ne serai pas (?:un |votre )?(?:client|preneur|int[ée]ress)|je ne serai pas (?!disponible|l[àa]|joignable|pr[ée]sent|absent|au bureau|chez|en mesure)|nous ne serons pas (?!disponible|l[àa]|joignable|pr[ée]sent|absent)|"
                         r"(?:je|nous) (?:le )?(?:refai[ts]|refaisons) (?:mon|notre|ma|nos)? ?(?:propre )?(?:site|page)|(?:refait|refais|fais|faisons) (?:mon|notre) (?:propre )?site|(?:moi|nous)[- ]m[êe]mes?.{0,40}site|site.{0,40}(?:moi|nous)[- ]m[êe]mes?|"
                         r"d[ée]j[àa] (?:un|une|mon|notre) (?:site|page)|pas besoin|aucun besoin|non merci|pas pour moi|ça ne m.int[ée]resse pas|cela ne m.int[ée]resse pas|ne suis pas int[ée]ress|ne sommes pas int[ée]ress", re.I)
DEMANDE = re.compile(r"appelez|rappelez|rendez-vous|rdv|devis|envoyez|montrez", re.I)
NEGATION = re.compile(r"\b(?:pas|non|jamais|aucun|aucune|plus|sans|ni)\b|\bn'", re.I)
AUTO = re.compile(r"absent|absence|auto(?:matique)?|out of office|vacances|mailer-daemon|postmaster|ne pas répondre|no-?reply|delivery status|undeliver", re.I)


def texte_neuf(corps):  # la réponse sans les citations
    sortie = []
    for l in corps.splitlines():
        if re.match(r"\s*(?:Le .{5,100}(?:a écrit|écrit)\s*:?|On .{5,100}wrote:|De\s?:|From:|-{3,}|_{3,}|Envoyé de mon)", l, re.I) or l.lstrip().startswith(">"): break
        sortie.append(l)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(sortie)).strip()


def classer(objet, texte):
    """-> 'STOP' | 'négative' | 'positive' | 'autre'. En cas de doute : 'autre'."""
    t = f"{texte}"
    if not t.strip() or len(t) > 1500 or AUTO.search(objet or "") or AUTO.search(t[:300]): return "autre"
    if STOP.search(t): return "STOP"
    if NEGATIF_NET.search(t) and not DEMANDE.search(NEGATIF_NET.sub(" ", t)): return "négative"
    neg, pos = bool(NEGATIF.search(t)), bool(POSITIF.search(NEGATIF.sub(" ", t)))  # « pas intéressé » ne compte pas comme positif
    if neg and pos: return "autre"
    if neg: return "négative"
    if pos:
        if NEGATION.search(t) and not re.search(r"int[ée]ress|rappelez|appelez[- ]moi|volontiers|avec plaisir|pourquoi pas", t, re.I): return "autre"
        if re.search(r"(?:pas|ni|sans|aucun)\s+(?:de\s+|d')?(?:devis|prix|tarifs?|rendez-vous|appel)", t, re.I): return "autre"
        return "positive"
    return "autre"


# ---------- agenda : 2 créneaux de 15 min, jamais réservés ----------
def decalage_paris(u):  # Europe/Paris sans base de fuseaux : été du dernier dimanche de mars au dernier dimanche d'octobre, 01 h UTC
    def dernier_dim(a, m):
        d = date(a, m + 1, 1) - timedelta(days=1); return d - timedelta(days=(d.weekday() + 1) % 7)
    d1 = datetime.combine(dernier_dim(u.year, 3), datetime.min.time(), timezone.utc) + timedelta(hours=1)
    d2 = datetime.combine(dernier_dim(u.year, 10), datetime.min.time(), timezone.utc) + timedelta(hours=1)
    return timedelta(hours=2) if d1 <= u < d2 else timedelta(hours=1)


def paris_vers_utc(naif):  # heure locale -> UTC
    u = naif.replace(tzinfo=timezone.utc) - timedelta(hours=1)
    return naif.replace(tzinfo=timezone.utc) - decalage_paris(u)


def heure_ical(valeur, params):
    v = valeur.strip()
    if re.fullmatch(r"\d{8}", v): return None  # journée entière : ne bloque pas les créneaux
    d = datetime.strptime(v.rstrip("Z"), "%Y%m%dT%H%M%S")
    if v.endswith("Z"): return d.replace(tzinfo=timezone.utc)
    return paris_vers_utc(d)  # TZID (Europe/Paris en pratique) ou heure flottante : lue comme heure de Paris


def occupations(ics, debut, fin):
    """Intervalles occupés [(début, fin)] en UTC. Gère les événements simples et les répétitions DAILY/WEEKLY (INTERVAL, BYDAY, COUNT, UNTIL, EXDATE)."""
    txt = re.sub(r"\r?\n[ \t]", "", ics); occ = []; jours = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
    for ev in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", txt, re.S):
        champs = {}
        for l in ev.splitlines():
            if ":" in l:
                nom, val = l.split(":", 1); p = nom.split(";"); champs.setdefault(p[0].upper(), []).append((val, p[1:]))
        if "TRANSP" in champs and champs["TRANSP"][0][0].strip().upper() == "TRANSPARENT": continue
        if "STATUS" in champs and champs["STATUS"][0][0].strip().upper() == "CANCELLED": continue
        if "DTSTART" not in champs: continue
        try:
            a = heure_ical(*champs["DTSTART"][0])
            if a is None: continue
            b = heure_ical(*champs["DTEND"][0]) if "DTEND" in champs else a + timedelta(hours=1)
        except ValueError: continue
        if b is None: continue
        duree = b - a; exd = set()
        for v, p in champs.get("EXDATE", []):
            for x in v.split(","):
                try: exd.add(heure_ical(x, p))
                except ValueError: pass
        r = champs.get("RRULE")
        if not r:
            if b > debut and a < fin: occ.append((a, b))
            continue
        rr = dict(kv.split("=", 1) for kv in r[0][0].split(";") if "=" in kv)
        freq, pas = rr.get("FREQ"), int(rr.get("INTERVAL", 1))
        fin_r = heure_ical(rr["UNTIL"], []) if "UNTIL" in rr and re.fullmatch(r"\d{8}T\d{6}Z?", rr["UNTIL"]) else None
        if freq not in ("DAILY", "WEEKLY"):  # MONTHLY / YEARLY : non géré, on bloque prudemment la date de départ seulement
            if b > debut and a < fin: occ.append((a, b))
            continue
        n, cur = 0, a.replace(hour=0, minute=0, second=0, microsecond=0)
        # parcours jour par jour depuis le début de la série
        j = a
        while j < fin:
            sem = (j.date() - a.date()).days // 7; ok = True
            if freq == "DAILY": ok = (j.date() - a.date()).days % pas == 0
            else:
                par = [x[-2:] for x in rr["BYDAY"].split(",")] if "BYDAY" in rr else [jours[a.weekday()]]
                ok = sem % pas == 0 and jours[j.weekday()] in par
            if ok:
                n += 1
                if "COUNT" in rr and n > int(rr["COUNT"]): break
                if fin_r and j > fin_r: break
                if j not in exd and j + duree > debut: occ.append((j, j + duree))
            j += timedelta(days=1)
    return occ


def creneaux(ics, maintenant=None, n=2):
    """n créneaux de 15 min : jours ouvrés, 9 h–19 h (Paris), au moins 2 h d'avance, hors événements de l'agenda ; premiers jours différents."""
    now = (maintenant or datetime.now(timezone.utc)); debut = now + timedelta(hours=2)
    occ = occupations(ics, debut, debut + timedelta(days=10)) if ics else []
    trouves, jours_pris = [], set()
    loc0 = (debut + decalage_paris(debut)).date()
    for k in range(0, 10):
        jr = loc0 + timedelta(days=k)
        if jr.weekday() >= 5: continue
        cand = [paris_vers_utc(datetime.combine(jr, datetime.min.time()) + timedelta(hours=9, minutes=15 * i)) for i in range(0, 40)]  # 9 h00 .. 18 h45
        libres = [c for c in cand if c >= debut and not any(c < o1 and c + timedelta(minutes=15) > o0 for o0, o1 in occ)]
        # préférence : un créneau en début de plage libre, puis un autre jour
        if libres and jr not in jours_pris:
            trouves.append(libres[0] if not trouves else libres[min(len(libres) - 1, 20)]); jours_pris.add(jr)
        if len(trouves) >= n: break
    return trouves


def fr_creneau(u):
    l = u + decalage_paris(u); jours = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
    return f"{jours[l.weekday()]} {l.day:02d}/{l.month:02d} {l:%H:%M}–{(l + timedelta(minutes=15)):%H:%M}"


def telecharger_agenda(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "reponses-b2b"}), timeout=20) as r: return r.read().decode("utf-8", "replace")
    except Exception as e:
        print(f"  agenda illisible ({type(e).__name__}) : créneaux proposés sans contrôle de l'agenda"); return None


# ---------- Discord ----------
def exclure_adresses(adresses, fichier=None):
    """Ajoute les adresses (expéditeur, adresse de réponse, adresse du suivi) à la liste d'exclusion de toutes les sources."""
    fichier = fichier or EXCLUS_MAILS
    try: deja = set(json.loads(fichier.read_text(encoding="utf-8")))
    except (OSError, ValueError): deja = set()
    neuves = {a.strip().lower() for a in adresses if a and "@" in a} - deja
    if neuves: fichier.write_text(json.dumps(sorted(deja | neuves), ensure_ascii=False, indent=1), encoding="utf-8")
    return sorted(neuves)


def appliquer(r, cl):
    """Réponse négative ou STOP : prospect passé en « refusé » / « STOP » (suivi-prospects.csv, avec note), nom ET adresses exclus. Réponse « autre » : statut inchangé, seule la relance J+2 est annulée
    (il a répondu : pas de relance automatique). Positive : statut « répondu ». -> libellé de l'action pour le résumé Discord."""
    p, extrait = r["prospect"], re.sub(r"\s+", " ", assainir(r["texte"])).strip()[:140]
    if cl in ("négative", "STOP"):
        exclure_adresses([r.get("de"), r.get("repondre"), p.get("email")])
        etat = "STOP" if cl == "STOP" else "refusé"
        if p["statut"] not in ("STOP", "refusé", "devis", "signé"):
            try: S.statut(p["nom"], etat, p["ville"], None, f"réponse {cl} le {date.today()} (agent Réponses) : « {extrait} »")
            except SystemExit as e: print(f"  statut non changé : {e}"); return "statut non changé"
        return f"passé en {etat}, nom et adresse exclus"
    if cl == "positive":
        if p["statut"] not in ("STOP", "refusé", "devis", "signé"):
            try: S.statut(p["nom"], "répondu", p["ville"], None, f"réponse positive le {date.today()} (agent Réponses)")
            except SystemExit as e: print(f"  statut non changé : {e}")
        return "passé en répondu"
    lignes = S.lire()
    for l in lignes:
        if S.cle(l) == S.cle(p) and l["relance_j2"]: l["relance_j2"] = ""; l["note"] = (l["note"] + f" | réponse autre le {date.today()} : relance annulée").strip(" |"); S.ecrire(lignes); break
    return "statut inchangé (à lire)"


def reponse_auto(r, cl, statut_avant, c, envoyer=None, signer=None, ident=None):
    """Maillon 1 : -> ligne ajoutée à l'alerte Discord. Réglage reponse_auto_envoi faux (défaut) : le message est écrit dans B2B\\donnees\\reponses-auto\\, rien n'est envoyé.
    Vrai : envoi par l'API Gmail depuis la boîte qui a reçu la réponse, une seule fois par prospect."""
    p = r["prospect"]; cle = S.cle(p); reel = bool(c.get("reponse_auto_envoi")); dest = r.get("repondre") or r.get("de")
    raison = RA.raison_de_ne_pas_repondre(cl, statut_avant, cle, not reel, dest)
    if raison: return f"↩️ Réponse automatique NON envoyée : {raison}. À traiter par Liam."
    if signer is None:
        import redaction as RD; signer = RD.avec_signature
    ident = ident if ident is not None else M.lire_fusionnee(ICI / "identite.json")
    texte = RA.message(ident, signer); objet = RA.objet_reponse(r["objet"])
    if reel:
        compte = r.get("compte", "")
        if not (c["api"]["actif"] and compte in c["api"]["comptes"]): return "↩️ Réponse automatique NON envoyée : boîte de réception sans jeton d'envoi. À traiter par Liam."
        try:
            sys.path.insert(0, str(RACINE / "harness")); import garde
            if not garde.avant_envoi("mail", texte, dest, agent="reponses"): return "↩️ Réponse automatique bloquée par la garde du harness. À traiter par Liam."
        except ImportError: pass
        from email.message import EmailMessage; from email.utils import formatdate
        msg = EmailMessage(); msg["From"] = f"{ident.get('prenom_nom', '')} <{compte}>"; msg["To"] = dest; msg["Subject"] = objet; msg["Date"] = formatdate(localtime=True)
        if str(r.get("mid", "")).startswith("<"): msg["In-Reply-To"] = msg["References"] = r["mid"]
        msg.set_content(texte)
        try: (envoyer or (lambda m: GA.client(compte).envoyer(m)))(msg)
        except (GA.JetonExpire, GA.BibliothequeManquante, GA.ErreurApi) as e: return f"↩️ Réponse automatique NON envoyée ({type(e).__name__}). À traiter par Liam."
        mode = "envoye"
    else: mode = "simule"
    RA.etat_noter(cle, mode, r["mid"]); f = RA.ecrire_message(p, dest, objet, texte, mode); RA.ligne_relais(p, mode); RA.noter_registre(p, mode)
    lignes = S.lire()
    for l in lignes:
        if S.cle(l) == cle: l["note"] = (l["note"] + f" | réponse auto {mode} le {date.today()}").strip(" |"); S.ecrire(lignes); break
    return ("↩️ Réponse automatique ENVOYÉE au prospect (numéro et créneau demandés)." if mode == "envoye" else f"↩️ SIMULATION (rien envoyé) : réponse écrite dans {f.name}. Active reponse_auto_envoi pour l'envoi.")


def resume_discord(cl, p, extrait, action):
    """Résumé court pour 💬-réponses (négative, STOP, autre) : aucune mention, texte du prospect assaini."""
    e = re.sub(r"\s+", " ", assainir(extrait)).strip()
    return f"💬 réponse **{cl}** — **{p['nom']}** ({p.get('ville', '?')}) — « {e[:200]}{'…' if len(e) > 200 else ''} » — {action}"[:1900]


def assainir(t):  # le texte du prospect est une donnée : pas de mention, pas de balisage
    t = re.sub(r"@(everyone|here)", "@​\\1", t); t = re.sub(r"<[@#&!][^>]*>", "", t)
    return t.replace("```", "'''").replace("`", "'")


def message_discord(uid, p, extrait, adresse, slots, agenda_ok, test=False, boite=""):
    l = [("**TEST — ne pas traiter** " if test else "") + f"<@{uid}> réponse positive",
         f"**{p['nom']}** — {p.get('metier', '?')} — {p.get('ville', '?')}",
         f"Extrait : « {assainir(extrait)[:420]}{'…' if len(extrait) > 420 else ''} »", f"Adresse de réponse : {adresse}" + (f" — reçue sur la boîte {boite}" if boite else ""),
         "Créneaux d'appel de 15 min proposés (non réservés" + ("" if agenda_ok else " ; agenda non contrôlé : à vérifier") + ") :"]
    l += [f"• {fr_creneau(s)}" for s in slots] or ["• aucun créneau trouvé"]
    return "\n".join(l)[:1900]


def _norm_salon(t):  # « 📦│Lots » -> « lots » : minuscules, sans accents ni emojis ni séparateurs
    return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().lower())


def lire_discord(jeton, chemin):
    req = urllib.request.Request("https://discord.com/api/v10" + chemin, headers={"Authorization": "Bot " + jeton, "User-Agent": "DiscordBot (reponses-b2b, 1.0)"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r: return json.loads(r.read())
    except urllib.error.HTTPError as e: print(f"  Discord a refusé la lecture (HTTP {e.code})"); return None
    except Exception as e: print(f"  Discord injoignable ({type(e).__name__})"); return None


def salon_par_nom(jeton, cle, nom, defaut, lire=None, chemin_cfg=None):
    """Identifiant du salon texte « nom » (insensible à la casse, aux accents et aux emojis), mis en cache dans reponses-config.json › cle.
    Introuvable ou inaccessible : renvoie `defaut` (l'ancien salon) et écrit l'erreur (jamais le jeton). Un salon déjà en cache n'est pas recherché de nouveau."""
    chemin_cfg = chemin_cfg or CONFIG; lire = lire or (lambda ch: lire_discord(jeton, ch))
    try: brut = M.lire_fusionnee(chemin_cfg)      # défaut + surcharge locale (le cache de salon est écrit dans le fichier local)
    except ValueError: brut = {}
    if brut.get(cle): return str(brut[cle])
    cherche = _norm_salon(nom); trouves = []
    for g in lire("/users/@me/guilds") or []:
        salons = lire(f"/guilds/{g['id']}/channels") or []
        cats = {c["id"]: _norm_salon(c.get("name")) for c in salons if c.get("type") == 4}
        trouves += [(c, cats.get(c.get("parent_id"), "")) for c in salons if c.get("type") in (0, 5) and _norm_salon(c.get("name")) == cherche]
    if not trouves: print(f"  salon « {nom} » introuvable ou inaccessible au bot : ancien salon gardé"); return defaut
    c = next((c for c, cat in trouves if "b2bventesiteweb" in cat), trouves[0][0])
    brut[cle] = str(c["id"])
    try: M.ecrire_local(chemin_cfg, {cle: brut[cle]})
    except (OSError, ValueError) as e: print(f"  cache du salon « {nom} » non écrit ({type(e).__name__})")
    return brut[cle]


def poster(jeton, salon, contenu, uid):
    try:   # garde commune du harness (B2B\harness\garde.py, 15/11/2026) : False = envoi bloqué
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "harness")); import garde
        if not garde.avant_envoi("discord", contenu, agent="reponses"): return False
    except ImportError: pass
    req =urllib.request.Request(f"https://discord.com/api/v10/channels/{salon}/messages", method="POST",
        data=json.dumps({"content": contenu, "allowed_mentions": {"users": [str(uid)]}}).encode(),
        headers={"Authorization": "Bot " + jeton, "Content-Type": "application/json", "User-Agent": "DiscordBot (reponses-b2b, 1.0)"})
    try:
        with urllib.request.urlopen(req, timeout=20): return True
    except urllib.error.HTTPError as e: print(f"  Discord a refusé le message (HTTP {e.code})"); return False
    except Exception as e: print(f"  Discord injoignable ({type(e).__name__})"); return False


# ---------- boîtes mail ----------
def dec(v): return str(make_header(decode_header(v or "")))


def corps_texte(msg):
    b = msg.get_body(preferencelist=("plain", "html"))
    if not b: return ""
    t = b.get_content()
    if b.get_content_type() == "text/html": t = unescape(re.sub(r"<(?:br|/p|/div)[^>]*>", "\n", re.sub(r"<(?:style|script).*?</(?:style|script)>", "", t, flags=re.S | re.I))); t = re.sub(r"<[^>]+>", "", t)
    return t


def connus():
    par_mail, par_nom = {}, {}
    for r in S.lire():
        if r["email"]: par_mail[r["email"].strip().lower()] = r
        par_nom[S.G.slug(r["nom"])] = r
    return par_mail, par_nom


def prospect_du_message(expediteur, objet, par_mail, par_nom):
    if expediteur in par_mail: return par_mail[expediteur]
    m = re.match(r"\s*(?:re|ré|rép|aw|tr)\s*:\s*(.+?)\s*:\s*" + re.escape(SIGNE_OBJET), objet or "", re.I)
    return par_nom.get(S.G.slug(m.group(1))) if m else None


def reponse_depuis(compte, mid, exp, objet, msg, p):
    return dict(mid=mid, compte=compte, de=exp, repondre=parseaddr(dec(msg["Reply-To"]))[1].lower() or exp, objet=objet, texte=texte_neuf(corps_texte(msg)), prospect=p)


def lire_boite(compte, mdp, jours, deja, par_mail, par_nom, propres):
    trouves = []
    m = imaplib.IMAP4_SSL("imap.gmail.com", 993)
    try:
        m.login(compte, mdp); m.select("INBOX", readonly=True)
        depuis = date.today() - timedelta(days=jours)
        _, data = m.uid("search", None, f"SINCE {depuis.day:02d}-{MOIS[depuis.month - 1]}-{depuis.year}")
        for uid in data[0].split():
            _, h = m.uid("fetch", uid, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT MESSAGE-ID)])")  # en-tête seulement
            if not h or not h[0] or not isinstance(h[0], tuple): continue
            ent = email.message_from_bytes(h[0][1], policy=policy.default)
            exp = parseaddr(dec(ent["From"]))[1].lower(); objet = dec(ent["Subject"]); mid = (ent["Message-ID"] or "").strip() or f"{compte}:{uid.decode()}"
            if est_rebond(exp, objet):
                _, full = m.uid("fetch", uid, "(BODY.PEEK[])")
                if full and full[0] and isinstance(full[0], tuple) and rebond_lie(full[0][1]): RETOURS["rebonds"][mid] = str(date.today()); ADRESSES_REBONDIES.update(echecs_permanents(full[0][1]))
                continue
            if exp in propres or mid in deja: continue
            p = prospect_du_message(exp, objet, par_mail, par_nom)
            if not p: continue  # pas une réponse à notre prospection : le corps n'est jamais lu
            _, full = m.uid("fetch", uid, "(BODY.PEEK[])")
            msg = email.message_from_bytes(full[0][1], policy=policy.default)
            trouves.append(reponse_depuis(compte, mid, exp, objet, msg, p))
    finally:
        try: m.logout()
        except Exception: pass
    return trouves


def lire_boite_api(cl, jours, deja, par_mail, par_nom, propres):
    """Même lecture que lire_boite, par l'API Gmail (gmail.readonly) : en-têtes d'abord, corps seulement pour les messages de prospects connus, rien n'est marqué lu."""
    trouves = []; depuis = date.today() - timedelta(days=jours)
    for gid in cl.ids(f"in:inbox after:{depuis:%Y/%m/%d}"):
        ent = cl.entetes(gid)
        exp = parseaddr(dec(ent.get("from")))[1].lower(); objet = dec(ent.get("subject")); mid = (ent.get("message-id") or "").strip() or f"{cl.adresse}:{gid}"
        if est_rebond(exp, objet):
            brut = cl.brut(gid)
            if rebond_lie(brut): RETOURS["rebonds"][mid] = str(date.today()); ADRESSES_REBONDIES.update(echecs_permanents(brut))
            continue
        if exp in propres or mid in deja: continue
        p = prospect_du_message(exp, objet, par_mail, par_nom)
        if not p: continue  # pas une réponse à notre prospection : le corps n'est jamais lu
        trouves.append(reponse_depuis(cl.adresse, mid, exp, objet, email.message_from_bytes(cl.brut(gid), policy=policy.default), p))
    return trouves


def lire_api(c, jours, deja, par_mail, par_nom, propres, ouvrir=GA.client):
    """Lecture par l'API Gmail, compte après compte (api › comptes). Jeton absent/expiré/refusé, erreur ou mauvais compte : message clair, CE compte est sauté, les autres continuent."""
    sortie = []
    for adresse in c["api"]["comptes"]:
        try:
            cl = ouvrir(adresse)
            sortie += lire_boite_api(cl, jours, deja, par_mail, par_nom, propres)
        except (GA.JetonExpire, GA.BibliothequeManquante) as e: print(f"  {adresse} : " + str(e))
        except GA.ErreurApi as e: print(f"  {adresse} : Gmail API erreur ({e}), boîte sautée")
    return sortie


# ---------- principal ----------
def cfg():
    c = M.lire_fusionnee(CONFIG)      # réglages par défaut + reponses-config.local.json (salons, comptes, API Gmail de CETTE machine)
    c.setdefault("comptes", [{"adresse": "contact.lmsites@gmail.com", "var": "GMAIL_1_APP_PASSWORD"}, {"adresse": "liamdigital2109@gmail.com", "var": "GMAIL_2_APP_PASSWORD"}])
    c.setdefault("salon_paiement_id", ""); c.setdefault("utilisateur_id", ""); c.setdefault("jours_relus", 14); c.setdefault("reponse_auto_envoi", False)
    c["api"] = {"actif": False, "comptes": [], **c.get("api", {})}  # actif = API Gmail (OAuth) à la place d'IMAP ; comptes = boîtes lues et utilisées pour l'envoi (test-gmail-api.py <adresse>)
    if not c["api"]["comptes"] and c["api"].get("adresse"): c["api"]["comptes"] = [c["api"]["adresse"]]  # ancien réglage à un seul compte
    c["api"]["comptes"] = [x.strip().lower() for x in c["api"]["comptes"]]; c["api"].pop("adresse", None)
    return c


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Réponses des prospects : classement et alerte Discord (aucun envoi au prospect).")
    ap.add_argument("--test", action="store_true"); ap.add_argument("--a-blanc", action="store_true"); ap.add_argument("--jours", type=int)
    a = ap.parse_args(); M.exiger("reponses", "", a.a_blanc); c = cfg(); env_b2b = lire_env(RACINE / ".env"); env_j = lire_env(RACINE.parent / ".env")
    uid = c["utilisateur_id"] or env_j.get("DISCORD_USER_ID", ""); jeton = env_j.get("DISCORD_BOT_TOKEN", "")
    if not a.a_blanc:
        manque = [x for x, v in (("salon_paiement_id (agents\\reponses-config.json)", c["salon_paiement_id"]), ("DISCORD_USER_ID (Jarvis\\.env)", uid), ("DISCORD_BOT_TOKEN (Jarvis\\.env)", jeton)) if not v]
        if manque: sys.exit("À COMPLÉTER avant de poster sur Discord : " + ", ".join(manque))
    ics = telecharger_agenda(env_b2b["GOOGLE_AGENDA_ICAL_URL"]) if env_b2b.get("GOOGLE_AGENDA_ICAL_URL") else None
    if not ics: print("  GOOGLE_AGENDA_ICAL_URL absent de B2B\\.env : créneaux calculés sans lire l'agenda (signalé dans le message)")
    slots = creneaux(ics)
    if a.test:
        p = {"nom": "Entreprise Exemple (TEST)", "metier": "électricien", "ville": "Rouen"}
        msg = message_discord(uid or "0", p, "Bonjour, oui ça m'intéresse, pouvez-vous m'appeler pour un devis ? (faux message de test)", "test@example.invalid", slots, bool(ics), test=True, boite="boite@example.invalid")
        if a.a_blanc: print(msg)
        else: print("TEST posté sur Discord." if poster(jeton, c["salon_paiement_id"], msg, uid) else "TEST non posté.")
        return  # aucun statut touché, aucun identifiant stocké
    traites = set(json.loads(TRAITES.read_text(encoding="utf-8"))) if TRAITES.exists() else set()
    par_mail, par_nom = connus(); reponses = []
    propres = {x["adresse"].lower() for x in c["comptes"]} | set(c["api"]["comptes"])
    if c["api"]["actif"]: reponses += lire_api(c, a.jours or c["jours_relus"], traites, par_mail, par_nom, propres)
    for cpt in ([] if c["api"]["actif"] else c["comptes"]):
        mdp = env_b2b.get(cpt["var"], "").replace(" ", "")
        if not mdp: print(f"  {cpt['adresse']} : {cpt['var']} absent de B2B\\.env, boîte sautée"); continue
        try: reponses += lire_boite(cpt["adresse"], mdp, a.jours or c["jours_relus"], traites, par_mail, par_nom, propres)
        except imaplib.IMAP4.error as e: print(f"  {cpt['adresse']} : connexion refusée ({type(e).__name__}) : vérifier le mot de passe d'application et l'IMAP activé")
        except OSError as e: print(f"  {cpt['adresse']} : réseau ({type(e).__name__})")
    salons = {}
    compte = {"positive": 0, "négative": 0, "STOP": 0, "autre": 0}
    for r in reponses:
        p = r["prospect"]; statut_avant = p["statut"]; cl = classer(r["objet"], r["texte"]); compte[cl] += 1
        if cl == "STOP" and PLAINTE.search(r["texte"]): RETOURS["plaintes"][r["mid"]] = str(date.today())
        print(f"- {p['nom']} ({p['ville']}) : {cl}")
        action = "" if a.a_blanc else appliquer(r, cl)   # statut + exclusions d'abord : ils ne dépendent pas de Discord
        if cl == "positive":
            auto = "↩️ Réponse automatique : à blanc, rien fait." if a.a_blanc else reponse_auto(r, cl, statut_avant, c)
            msg, cle_salon, nom_salon = ("🚨 PRIORITÉ " + message_discord(uid or "0", p, r["texte"], r["repondre"], slots, bool(ics), boite=r["compte"]))[:1650] + "\n" + auto, "salon_important_id", "important"
        else: msg, cle_salon, nom_salon = resume_discord(cl, p, r["texte"], action or "à blanc : rien modifié"), "salon_reponses_id", "réponses"
        if a.a_blanc: print("  [à blanc] " + msg.replace(chr(10), chr(10) + "  ")); continue
        salons[cle_salon] = salons.get(cle_salon) or salon_par_nom(jeton, cle_salon, nom_salon, c["salon_paiement_id"])
        if not poster(jeton, salons[cle_salon], msg, uid): continue
        traites.add(r["mid"]); TRAITES.write_text(json.dumps(sorted(traites), ensure_ascii=False, indent=1), encoding="utf-8")
    if not a.a_blanc and (RETOURS["rebonds"] or RETOURS["plaintes"]):
        try: cumul = json.loads(RETOURS_FICHIER.read_text(encoding="utf-8")) if RETOURS_FICHIER.exists() else {}
        except ValueError: cumul = {}
        for k in ("rebonds", "plaintes"): cumul.setdefault(k, {}).update(RETOURS[k])
        RETOURS_FICHIER.write_text(json.dumps(cumul, ensure_ascii=False, indent=1), encoding="utf-8")
    if not a.a_blanc and ADRESSES_REBONDIES:
        neuves = exclure_adresses(sorted(ADRESSES_REBONDIES))   # une adresse rebondie ne reçoit ni nouveau lot ni relance (exclus-emails.json, lu par prospection.exclusions())
        if neuves: print(f"{len(neuves)} adresse(s) rebondie(s) ajoutée(s) à exclus-emails.json")
    print(f"{len(RETOURS['rebonds'])} rebond(s) et {len(RETOURS['plaintes'])} plainte(s) repérés" + (" (à blanc : non enregistrés)" if a.a_blanc else "") + f"\n{len(reponses)} réponse(s) de prospects : " + ", ".join(f"{k} {v}" for k, v in compte.items()) + (" (à blanc : rien posté, rien modifié)" if a.a_blanc else ""))


if __name__ == "__main__":
    main()
