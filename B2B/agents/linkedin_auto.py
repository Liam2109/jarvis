#!/usr/bin/env python3
"""LinkedIn automatique (24/11/2026, décision de Liam : son compte, sa décision). Module de linkedin-equipe.py (commande `auto`), FERMÉ tant que go_linkedin_auto n'est pas true
dans linkedin-equipe-config.json (Liam dit « go linkedin auto »). Fermé = l'équipe retombe sur « prépare, Liam envoie » (rien d'autre à changer).

Un passage (« tick », toutes les 10 minutes de 08:00 à 18:00 les jours ouvrés) fait UNE seule action, dans cet ordre : vérifier acceptations et réponses (une fois par heure),
post du jour, DM aux connexions acceptées, relance unique à J+3, demande de connexion sans note (au rythme du quota, réparti sur la journée), commentaire (quota bas).
Navigateur : Chrome/Edge local piloté par Playwright, profil DÉDIÉ hors du dépôt où Liam se connecte LUI-MÊME (`auto connexion`). Aucun mot de passe, aucun cookie n'est lu, demandé,
copié ni stocké par le code. Aucune technique d'évitement de détection : pas de falsification d'empreinte, pas de faux mouvements de souris, un seul compte.
Garde-fous : toute page de vérification, CAPTCHA, limite, restriction, avertissement ou déconnexion arrête tout (fichier AUTO-STOP, alerte Discord), sans rien contourner ;
`auto reprendre` (Liam, après avoir réglé la chose sur LinkedIn lui-même) lève l'arrêt. Kill-switch global : le fichier B2B\\STOP. Tout envoi est écrit dans
B2B\\linkedin\\auto-journal.jsonl (hors git, dans la sauvegarde de 03:30)."""
import json, os, re, time, unicodedata
from datetime import datetime, date, timedelta
from pathlib import Path

LI = None
E = None   # le module linkedin-equipe (injecté par lui : voir lier())


def lier(moi):
    global E, LI; E = moi; LI = moi.LI


class Arret(Exception):
    """LinkedIn demande quelque chose (vérification, limite, CAPTCHA, déconnexion...) : tout s'arrête et Liam est prévenu."""


class Inattendu(Exception):
    """La page n'a pas la forme attendue (interface LinkedIn modifiée ?) : par prudence, tout s'arrête aussi."""


def norm(s): return " ".join(re.sub(r"[^a-z0-9 ]+", " ", unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()).split())


# --- fichiers (dans le dossier de l'état : B2B\linkedin\, hors git ; dossier temporaire en test) ---------------------------------
def f_arret(): return E.ETAT.parent / "AUTO-STOP"
def f_envois(): return E.ETAT.parent / "auto-journal.jsonl"
def f_stop_global(): return E.RACINE / "STOP"


def profil_dedie(conf):
    if conf.get("auto_profil"): return Path(conf["auto_profil"])
    return Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "Jarvis" / "linkedin-profil"   # hors du dépôt : jamais committé


def envoi_journal(type_, ident, nom, texte, url=""):
    """Journal de tout ce qui est envoyé (texte complet), un objet JSON par ligne."""
    f = f_envois(); f.parent.mkdir(parents=True, exist_ok=True)
    with open(f, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"le": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "type": type_, "id": ident, "nom": nom, "texte": texte, "url": url}, ensure_ascii=False) + "\n")


# --- détection des avertissements de LinkedIn ----------------------------------------------------------------------------
URL_ALERTE = re.compile(r"/(checkpoint|authwall|login|uas/|challenge|captcha|restricted|help/linkedin/answer/.*restrict)", re.I)
TEXTE_ALERTE = re.compile(
    r"captcha|v[ée]rification de s[ée]curit[ée]|security verification|quick security check|v[ée]rifions que vous|let'?s do a quick|confirmez que vous [êe]tes|are you a human|"
    r"activit[ée] inhabituelle|unusual activity|compte (?:a [ée]t[ée] )?(?:temporairement )?(?:restreint|limit[ée])|account (?:has been )?(?:temporarily )?(?:restricted|limited)|"
    r"restriction|limite (?:hebdomadaire|d'invitations|atteinte)|weekly (?:invitation )?limit|invitation limit|vous avez atteint la limite|you'?ve reached the (?:weekly )?(?:invitation )?limit|"
    r"avertissement|warning|nous avons constat[ée]|violat|contraire (?:à|a) nos|pas autoris[ée]e?|d[ée]connect[ée]|session (?:expir|a expir)|se connecter [àa] linkedin|sign in to linkedin|rejoignez linkedin", re.I)


def controler_page(url, texte):
    """Lève Arret à la moindre trace d'avertissement, de limite, de vérification, de CAPTCHA ou de déconnexion."""
    if URL_ALERTE.search(url or ""): raise Arret(f"page d'avertissement ou de connexion ({(url or '')[:80]})")
    m = TEXTE_ALERTE.search(texte or "")
    if m: raise Arret(f"LinkedIn affiche « {m.group(0)[:60]} »")


# --- navigateurs ----------------------------------------------------------------------------------------------------------
class Simule:
    """LinkedIn simulé pour les tests : aucun réseau, aucune fenêtre. Programmé par le test (attributs), enregistre ce qui serait envoyé."""
    def __init__(self):
        self.envoyes = []; self.resultats = {}; self.connexions = []; self.conversations = []; self.alerte = None; self.url = "https://www.linkedin.com/feed/"; self.texte = "Fil d'actualité"; self.ferme = False
        self.panne = None; self.limites = None

    def _etat(self):
        if self.alerte: self.url, self.texte = self.alerte
        return self.url, self.texte
    def etat_page(self): return self._etat()
    def _go(self, url): self.url = url; self.texte = "page"
    def recherche(self, url):
        self._go(url); return list(self.resultats.get(url, []))
    def demander(self, r):
        if self.panne == "demander": raise Inattendu("bouton introuvable")
        self.envoyes.append(("demande", r["profil"], None))
    def connexions_recentes(self): self._go("https://www.linkedin.com/mynetwork/invite-connect/connections/"); return list(self.connexions)
    def conversations_recentes(self): self._go("https://www.linkedin.com/messaging/"); return list(self.conversations)
    def envoyer_dm(self, profil, texte): self._go(profil); self.envoyes.append(("dm", profil, texte))
    def publier(self, texte): self._go("https://www.linkedin.com/feed/"); self.envoyes.append(("post", "", texte))
    def commenter(self, url, texte): self._go(url); self.envoyes.append(("commentaire", url, texte))
    def fermer(self): self.ferme = True


class Playwright:
    """Navigateur réel : profil dédié (Liam s'y connecte lui-même), fenêtre visible, aucune option de dissimulation. Sélecteurs par rôle et texte (français et anglais) ;
    tout élément absent lève Inattendu (arrêt prudent). Non testable hors LinkedIn : à superviser lors du premier jour."""
    def __init__(self, conf, headless=False):
        try: from playwright.sync_api import sync_playwright
        except ImportError: raise E.ErreurAgent("Playwright n'est pas installé : « pip install playwright » puis « playwright install msedge » (une fois, par Liam)")
        self._pw = sync_playwright().start(); dossier = profil_dedie(conf); dossier.mkdir(parents=True, exist_ok=True)
        try: self.ctx = self._pw.chromium.launch_persistent_context(str(dossier), channel=conf.get("auto_navigateur", "msedge"), headless=headless, viewport={"width": 1280, "height": 900})
        except Exception as ex: self._pw.stop(); raise E.ErreurAgent(f"navigateur local impossible à lancer ({type(ex).__name__})")
        self.page = self.ctx.pages[0] if self.ctx.pages else self.ctx.new_page(); self.page.set_default_timeout(15000)

    def _go(self, url):
        self.page.goto(url, wait_until="domcontentloaded"); self.page.wait_for_timeout(2500)
    def etat_page(self):
        try: return self.page.url, self.page.inner_text("body")[:6000]
        except Exception: return self.page.url, ""
    def _cliquer(self, nom, **kw):
        import re as _re
        b = self.page.get_by_role("button", name=_re.compile(nom, _re.I), **kw).first
        try: b.wait_for(state="visible", timeout=8000); b.click()
        except Exception: raise Inattendu(f"bouton « {nom[:40]} » introuvable")
    def _saisir(self, texte):
        zone = self.page.locator("div[role='textbox'][contenteditable='true']").last
        try: zone.wait_for(state="visible", timeout=8000); zone.click(); self.page.keyboard.insert_text(texte)
        except Exception: raise Inattendu("zone de saisie introuvable")
    def recherche(self, url):
        self._go(url)
        return self.page.evaluate("""() => { const out=[], vus=new Set();
          document.querySelectorAll('a[href*="/in/"]').forEach(a => { const href=a.href.split('?')[0]; if (vus.has(href)) return;
            const box=a.closest('li')||a.closest('[role=listitem]'); if (!box) return; vus.add(href);
            const nom=(a.innerText||'').split('\\n')[0].trim(); if (!nom) return;
            const ok=[...box.querySelectorAll('button')].some(x => /^(se connecter|connect)$/i.test((x.innerText||'').trim()) || /^(invitez|invite)\\b/i.test(x.getAttribute('aria-label')||''));
            out.push({nom, texte:(box.innerText||'').slice(0,400), profil:href, bouton:ok}); });
          return out; }""")
    def demander(self, r):
        import re as _re
        carte = self.page.locator(f'a[href^="{r["profil"]}"]').first.locator("xpath=ancestor::li[1]")
        try: carte.get_by_role("button", name=_re.compile(r"^(Se connecter|Connect)$|^(Invitez|Invite)\b", _re.I)).first.click()
        except Exception: raise Inattendu("bouton « Se connecter » introuvable")
        self.page.wait_for_timeout(1200); self._cliquer(r"Envoyer sans note|Send without a note")   # sans note, toujours ; sinon : arrêt
        self.page.wait_for_timeout(1500)
    def connexions_recentes(self):
        self._go("https://www.linkedin.com/mynetwork/invite-connect/connections/")
        return self.page.evaluate("""() => [...document.querySelectorAll('a[href*="/in/"]')].map(a => (a.innerText||'').split('\\n')[0].trim()).filter(x => x).slice(0,60)""")
    def conversations_recentes(self):
        self._go("https://www.linkedin.com/messaging/")
        return self.page.evaluate("""() => [...document.querySelectorAll('li[class*="msg-conversation"]')].slice(0,30).map(li => {
          const l=(li.innerText||'').split('\\n').map(x=>x.trim()).filter(x=>x); const nom=l[0]||''; const msg=l.slice(1).join(' ');
          return {nom, dernier:msg.replace(/^(Vous|You)\\s*:\\s*/i,''), de_moi:/^(Vous|You)\\s*:/i.test(msg)}; })""")
    def envoyer_dm(self, profil, texte):
        self._go(profil); self._cliquer(r"^(Message|Envoyer un message)$"); self.page.wait_for_timeout(1500); self._saisir(texte); self._cliquer(r"^(Envoyer|Send)$")
        self.page.wait_for_timeout(1500)
    def publier(self, texte):
        self._go("https://www.linkedin.com/feed/"); self._cliquer(r"Commencer un post|Start a post"); self.page.wait_for_timeout(1500); self._saisir(texte); self._cliquer(r"^(Publier|Post)$")
        self.page.wait_for_timeout(2500)
    def commenter(self, url, texte):
        self._go(url); self._cliquer(r"^(Commenter|Comment)$"); self.page.wait_for_timeout(1000); self._saisir(texte)
        try: self.page.locator("button[class*='comments-comment-box__submit-button'], form[class*='comment'] button[type='submit']").last.click()
        except Exception: raise Inattendu("bouton d'envoi du commentaire introuvable")
        self.page.wait_for_timeout(1500)
    def fermer(self):
        try: self.ctx.close(); self._pw.stop()
        except Exception: pass


class Session:
    """Enveloppe : contrôle la page après CHAQUE navigation ou action (Arret au premier signe d'avertissement, de limite ou de déconnexion)."""
    def __init__(self, nav): self.nav = nav
    def controle(self):
        controler_page(*self.nav.etat_page())
    def __getattr__(self, nom):
        f = getattr(self.nav, nom)
        if nom in ("fermer", "etat_page") or not callable(f): return f
        def appel(*a, **k):
            r = f(*a, **k); self.controle(); return r
        return appel


# --- plan du jour ---------------------------------------------------------------------------------------------------------
def hm(s): h, m = (s or "00:00").split(":"); return int(h) * 60 + int(m)


def quota_demandes(conf, etat, jour):
    """Demandes autorisées aujourd'hui : demandes_par_jour (20 dès le premier jour, sans montée progressive), jamais plus que le reste du plafond de la semaine au début de la journée."""
    etat.setdefault("auto", {}).setdefault("debut", jour)
    return max(0, min(conf["demandes_par_jour"], conf["plafond_semaine"] - (E.envoyees_semaine(etat, jour) - aujourdhui(etat, "demande_envoyee_le", jour))))


def aujourdhui(etat, cle, jour):
    return sum(1 for c in etat["cibles"].values() if c.get(cle) == jour)


def prevu_a_cette_heure(quota, conf, now):
    """Nombre d'actions « dues » à cette heure si le quota est réparti de façon égale entre auto_debut et auto_fin (la première est due dès l'ouverture)."""
    d, f = hm(conf["auto_debut"]), hm(conf["auto_fin"]); m = now.hour * 60 + now.minute
    if quota <= 0 or m < d: return 0
    if m >= f: return quota
    return min(quota, 1 + int(quota * (m - d) / max(1, f - d)))


def alerter_reel(texte):
    try:
        import prospection as P
        a = P.acces_discord()
        if not a: return False
        jeton, salon, uid = a
        r = P.discord(jeton, "POST", f"/channels/{salon}/messages", {"content": f"<@{uid}> {texte}"[:1900], "allowed_mentions": {"users": [uid]}})
        return bool(r and "id" in r)
    except Exception: return False


def arret_urgence(raison, alerter, nav=None):
    """Arrête tout : fichier AUTO-STOP (aucun passage ne repart tant que Liam n'a pas fait `auto reprendre`), journal, alerte Discord UNE fois."""
    f = f_arret(); deja = f.exists()
    if not deja:
        f.parent.mkdir(parents=True, exist_ok=True); f.write_text(f"{datetime.now():%Y-%m-%d %H:%M:%S} | {raison}\n", encoding="utf-8")
        E.journaliser("auto-arret", raison)
        alerter(f"🛑 LinkedIn automatique arrêté : {raison}. Rien n'a été contourné. Regardez votre compte LinkedIn vous-même, puis « python B2B\\agents\\linkedin-equipe.py auto reprendre » quand c'est réglé.")
    try: nav and nav.fermer()
    except Exception: pass
    return 6


# --- textes ----------------------------------------------------------------------------------------------------------------
PRIX_E = ["Côté tarif : 500 € la création du site, puis 29 € par mois, hébergement et maintenance compris.",
          "Pour fixer les idées, la création est à 500 €, puis 29 € par mois avec l'hébergement et la maintenance.",
          "Le principe est simple : 500 € pour la création, puis 29 € par mois, hébergement et maintenance inclus.",
          "Pour le tarif : 500 € une fois, puis 29 € par mois avec l'hébergement et le suivi."]
PRIX_OK = re.compile(r"\b500 ?€|\b29 ?€")


def texte_dm(etat, c):
    """DM personnalisé, jamais identique à un texte déjà écrit. Entreprise : avec le prix (500 € puis 29 €/mois, chiffres de OFFRE-REFERENCE.json). Appelant/closer : sans prix, rémunération à la commission."""
    if c.get("dm_auto"): return c["dm_auto"]
    deja = set(etat["textes"]); metier = c.get("metier") or "artisan"; ville = c.get("ville") or ""
    rempl = lambda x: x.format(metier=metier, ville=ville or "chez vous")
    if c["type"] == "closer": t = E.dm_pour(c, deja)
    else:
        fins = [p + " " + f for p in PRIX_E for f in E.FIN_E]
        ouv = [o for o in E.OUV_E if "{ville}" not in o or ville]
        t = E.rediger_prix(ouv, E.COR_E_BAT if c.get("bat", True) else E.COR_E_COM, fins, c["id"], deja, rempl)
    c["dm_auto"] = t; etat["textes"].append(t); return t


def verifier_texte(t, c=None, commentaire=False):
    """Problèmes d'un texte avant envoi (liste vide = conforme). Les seuls chiffres admis : le prix de l'offre (500 € et 29 €)."""
    sans = PRIX_OK.sub("", t or "")
    pb = E.controle_message(sans, 480, commentaire=commentaire)
    return [p for p in pb if "chiffre" not in p or re.search(r"\d", sans)]


# --- actions (une par passage) -------------------------------------------------------------------------------------------
def nom_cherche(c): return c.get("dirigeant") or ""


def choisir(c, res, etat):
    """Le résultat de recherche à contacter, ou None. Entreprise : le nom du dirigeant doit correspondre exactement (prénom et nom) ; sans dirigeant connu, le nom de l'entreprise doit figurer
    dans la fiche. Appelant/closer : le premier profil qui n'a jamais été contacté. Jamais de profil déjà vu."""
    vus = set(etat.setdefault("auto", {}).setdefault("profils", []))
    for r in res:
        if r["profil"] in vus or not r.get("bouton"): continue
        if c["type"] == "closer": return r
        if nom_cherche(c):
            if norm(r["nom"]) == norm(nom_cherche(c)) or set(norm(nom_cherche(c)).split()) <= set(norm(r["nom"]).split()): return r
        else:
            ent = norm(c.get("entreprise") or c["nom"])
            if ent and len(ent) >= 4 and ent in norm(r["texte"]): return r
    return None


def action_verifier(conf, etat, s, jour):
    """Acceptations (la personne apparaît dans les connexions) puis réponses aux DM. Une réponse STOP ou négative exclut la personne ; positive : leads chauds."""
    n_acc = n_rep = 0
    attendus = [c for c in etat["cibles"].values() if c.get("demande_envoyee_le") and not c.get("accepte_le") and not c.get("ignore") and c.get("nom_profil")]
    if attendus:
        noms = {norm(x) for x in s.connexions_recentes()}
        for c in attendus:
            if norm(c["nom_profil"]) in noms: E.appliquer(etat, c["id"], "accepte", jour, conf); n_acc += 1
    ouverts = [c for c in etat["cibles"].values() if c.get("dm_envoye_le") and not c.get("repondu_le") and not c.get("ignore") and c.get("nom_profil")]
    if ouverts:
        conv = {norm(x["nom"]): x for x in s.conversations_recentes()}
        for c in ouverts:
            x = conv.get(norm(c["nom_profil"]))
            if not x or x.get("de_moi") or not x.get("dernier"): continue
            sens = classer_reponse(x["dernier"]); c["reponse_texte"] = x["dernier"][:300]
            E.appliquer(etat, c["id"], {"positive": "repondu_positif", "negative": "repondu_negatif"}.get(sens, "repondu_autre"), jour, conf); n_rep += 1
    E.journaliser("auto-verif", f"{n_acc} acceptation(s), {n_rep} réponse(s)")
    return f"vérification : {n_acc} acceptation(s), {n_rep} réponse(s)"


NEGATIF = re.compile(r"\bstop\b|pas int[ée]ress|non merci|ne m'[ée]crivez|ne me contactez|arr[êe]tez|d[ée]sabonn|laissez[- ]moi|pas besoin|aucun int[ée]r[êe]t|spam|\bnon\b[ .!]*$", re.I)
POSITIF = re.compile(r"int[ée]ress|pourquoi pas|\boui\b|appelez|rappelez|appel|t[ée]l[ée]phone|num[ée]ro|envoyez|dites[- ]m'en|plus d'info|d'accord|\bok\b|quand|volontiers|chiffr|devis|prix|tarif|combien", re.I)


def classer_reponse(t):
    """negative (STOP, refus) l'emporte toujours ; positive ; sinon autre (aucune action automatique)."""
    t = t or ""
    if NEGATIF.search(t): return "negative"
    if POSITIF.search(t): return "positive"
    return "autre"


def action_post(conf, etat, s, jour):
    lot = etat["jours"].get(jour) or {}; p = lot.get("post")
    if not p or p.get("publie_le"): return None
    pb = LI.controle(p["type"], p["texte"], LI.cfg())   # règles de contenu des posts (agent linkedin) : le post vient de sa file, déjà contrôlée
    if pb: p["publie_le"] = "refuse"; E.journaliser("auto-post-refuse", ",".join(pb)); return f"post du jour non publié (règles de contenu : {', '.join(pb)})"
    s.publier(p["texte"]); p["publie_le"] = jour; envoi_journal("post", p["id"], "post du jour", p["texte"]); return "post du jour publié"


def action_dm(conf, etat, s, jour):
    if aujourdhui(etat, "dm_envoye_le", jour) >= conf["auto_dm_max_jour"]: return None
    for c in etat["cibles"].values():
        if c.get("accepte_le") and not c.get("dm_envoye_le") and not c.get("ignore") and c.get("profil_url"):
            t = texte_dm(etat, c); pb = verifier_texte(t)
            if pb: c["ignore"] = True; E.journaliser("auto-dm-refuse", f"{c['id']} {','.join(pb)}"); return f"DM écarté pour {c['id']} (règles de contenu : {', '.join(pb)})"
            s.envoyer_dm(c["profil_url"], t); E.appliquer(etat, c["id"], "dm_envoye", jour, conf); envoi_journal("dm", c["id"], c.get("nom_profil", ""), t, c["profil_url"]); return f"DM envoyé ({c['id']})"
    return None


def action_relance(conf, etat, s, jour):
    for c in E.relances_dues(etat, jour, conf):
        if c.get("ignore") or not c.get("profil_url"): continue
        if not c.get("relance"): c["relance"] = E.relance_pour(c, set(etat["textes"])); etat["textes"].append(c["relance"])
        pb = verifier_texte(c["relance"])
        if pb: c["ignore"] = True; return f"relance écartée pour {c['id']} (règles de contenu : {', '.join(pb)})"
        s.envoyer_dm(c["profil_url"], c["relance"]); E.appliquer(etat, c["id"], "relance_envoyee", jour, conf); envoi_journal("relance", c["id"], c.get("nom_profil", ""), c["relance"], c["profil_url"])
        return f"relance envoyée ({c['id']})"
    return None


def action_demande(conf, etat, s, jour, now):
    q = quota_demandes(conf, etat, jour); fait = aujourdhui(etat, "demande_envoyee_le", jour)
    if fait >= prevu_a_cette_heure(q, conf, now) or fait >= q: return None
    lot = etat["jours"].get(jour) or {}; ids = [i for i in lot.get("demandes", []) if i in etat["cibles"]]
    for c in etat["cibles"].values():   # les demandes reportées d'un jour précédent passent aussi
        if c.get("demande_prevue_le") and c["id"] not in ids: ids.append(c["id"])
    for i in ids:
        c = etat["cibles"][i]
        if c.get("demande_envoyee_le") or c.get("ignore") or c.get("auto_essais", 0) >= 2: continue
        c["auto_essais"] = c.get("auto_essais", 0) + 1
        r = choisir(c, s.recherche(c["lien"]), etat)
        if not r: E.appliquer(etat, i, "ignorer", jour, conf); E.journaliser("auto-introuvable", i); return f"cible {i} : profil introuvable ou ambigu, écartée"
        s.demander(r); c["nom_profil"] = r["nom"]; c["profil_url"] = r["profil"]; etat["auto"]["profils"].append(r["profil"])
        E.appliquer(etat, i, "demande_envoyee", jour, conf); envoi_journal("demande", i, r["nom"], "(demande de connexion sans note)", r["profil"]); return f"demande de connexion envoyée ({i})"
    return None


def action_commentaire(conf, etat, s, jour, now):
    q = conf["auto_commentaires_par_jour"]; lot = etat["jours"].get(jour) or {}; coms = lot.get("commentaires", [])
    faits = sum(1 for x in coms if x.get("fait_le") == jour)
    if faits >= prevu_a_cette_heure(q, conf, now) or faits >= q: return None
    for x in coms:
        if x.get("fait") or x.get("ecarte"): continue
        if x["texte"] in set(etat["textes"]) or verifier_texte(x["texte"], commentaire=True): x["ecarte"] = True; continue   # jamais le même texte, jamais hors règles
        s.commenter(x["url"], x["texte"]); E.appliquer(etat, x["id"], "commente", jour, conf); x["fait_le"] = jour; etat["textes"].append(x["texte"]); envoi_journal("commentaire", x["id"], x["titre"], x["texte"], x["url"])
        return "commentaire posté"
    return None


# --- un passage -----------------------------------------------------------------------------------------------------------
def tick(conf, jour, now, fabrique=None, alerter=None, dormir=time.sleep):
    """Une action au plus. -> code de sortie : 0 (rien ou fait), 6 (arrêt d'urgence). `fabrique(conf)` donne le navigateur (réel par défaut, simulé en test)."""
    alerter = alerter or alerter_reel
    if conf.get("go_linkedin_auto") is not True: print("LinkedIn automatique fermé (go_linkedin_auto = false) : mode « prépare, Liam envoie »."); return 0
    if f_stop_global().exists(): print("Kill-switch B2B\\STOP présent : aucune action."); return 0
    if f_arret().exists(): print("Arrêt d'urgence en cours (AUTO-STOP) : « auto reprendre » après vérification sur LinkedIn."); return 6
    d = date.fromisoformat(jour)
    if d.weekday() >= 5: print("Jour non ouvré."); return 0
    m = now.hour * 60 + now.minute
    if m < hm(conf["auto_debut"]) or m >= hm(conf["auto_fin"]): print("Hors de la plage horaire."); return 0
    etat = E.etat_lire(); a = etat.setdefault("auto", {}); a.setdefault("debut", jour)
    if a.get("derniere_action") and (now - datetime.fromisoformat(a["derniere_action"])).total_seconds() < conf["auto_ecart_minutes"] * 60: print("Dernière action trop récente."); return 0
    if jour not in etat["jours"]:
        E.cmd_jour(conf, jour); etat = E.etat_lire(); a = etat.setdefault("auto", {}); a.setdefault("debut", jour)
    s = None
    try:
        s = Session((fabrique or (lambda c: Playwright(c)))(conf)); s.controle()
        msg = None
        a_verifier = any((c.get("demande_envoyee_le") and not c.get("accepte_le") or c.get("dm_envoye_le") and not c.get("repondu_le")) and not c.get("ignore") and c.get("nom_profil") for c in etat["cibles"].values())
        if a_verifier and (not a.get("derniere_verif") or (now - datetime.fromisoformat(a["derniere_verif"])).total_seconds() >= 3600):
            a["derniere_verif"] = now.isoformat(timespec="seconds"); msg = action_verifier(conf, etat, s, jour)
        for f in (lambda: action_post(conf, etat, s, jour), lambda: action_dm(conf, etat, s, jour), lambda: action_relance(conf, etat, s, jour),
                  lambda: action_demande(conf, etat, s, jour, now), lambda: action_commentaire(conf, etat, s, jour, now)):
            if msg: break
            msg = f()
        if msg: a["derniere_action"] = now.isoformat(timespec="seconds"); E.journaliser("auto", msg); print(msg)
        else: print("Rien à faire à cette heure.")
        for c in E.relances_dues(etat, jour, conf):
            if not c.get("relance"): c["relance"] = E.relance_pour(c, set(etat["textes"])); etat["textes"].append(c["relance"])
        E.etat_ecrire(etat); E.exporter(etat, conf, jour); s.fermer(); return 0
    except Arret as ex:
        try: E.etat_ecrire(etat)   # ce qui a été fait avant l'alerte reste noté
        except Exception: pass
        return arret_urgence(str(ex), alerter, s)
    except Inattendu as ex:
        try: E.etat_ecrire(etat)
        except Exception: pass
        return arret_urgence(f"page inattendue ({ex}) : l'interface de LinkedIn a peut-être changé", alerter, s)


def reprendre():
    f = f_arret()
    if not f.exists(): print("Aucun arrêt en cours."); return 0
    f.unlink(); E.journaliser("auto-reprise", "arrêt levé par Liam"); print("Arrêt levé : le prochain passage reprendra."); return 0


def connexion(conf):
    """Ouvre le navigateur à la page de connexion : Liam se connecte LUI-MÊME, puis ferme la fenêtre. Le code ne lit, ne demande et ne garde aucun identifiant ni cookie."""
    nav = Playwright(conf)
    try:
        nav.page.goto("https://www.linkedin.com/login"); print("Connectez-vous dans la fenêtre ouverte, puis fermez-la. Rien n'est lu ni enregistré par Jarvis.")
        nav.page.wait_for_event("close", timeout=0)
    except Exception: pass
    finally: nav.fermer()
    return 0


def etat_auto(conf, etat, jour):
    a = etat.get("auto", {}); print(f"go_linkedin_auto : {conf['go_linkedin_auto']} ; arrêt d'urgence : {'OUI ' + f_arret().read_text(encoding='utf-8').strip() if f_arret().exists() else 'non'} ; profil dédié : {profil_dedie(conf)}")
    print(f"Début : {a.get('debut', '-')} ; quota du jour : {quota_demandes(conf, etat, jour)} demandes ; envoyées aujourd'hui : {aujourdhui(etat, 'demande_envoyee_le', jour)} ; cette semaine : {E.envoyees_semaine(etat, jour)}/{conf['plafond_semaine']}.")
    return 0
