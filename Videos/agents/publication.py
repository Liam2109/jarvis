#!/usr/bin/env python3
"""Agent videos-publication (équipe Vidéos TikTok, 16/11/2026) — gratuit, local, sans token Claude. FERMÉ pour une ligne tant que Liam n'a pas dit « go publier ».
Règle (16/11/2026) : Liam valide UNE fois la première vidéo de chaque ligne (A stickman, B recrutement) en disant « go publier » ; ensuite les vidéos de cette ligne
sont publiées automatiquement. Le go s'écrit à la main dans Videos\\videos-config.local.json : "lignes": {"A": {"go_publier": true}} (jamais par un agent).
Navigateur piloté localement (Playwright) avec un profil persistant par ligne (profil_navigateur) ; Liam s'y connecte lui-même, une fois
(`publication.py connexion --ligne A`) : l'agent ne tape JAMAIS de mot de passe et n'en stocke aucun.
Règles codées ici, jamais contournées :
  - Videos\\STOP ou B2B\\STOP présent = aucune publication ;
  - 3 publications par jour et par compte au plus, une par passage, seulement près des heures prévues (+/- 45 min) ; jamais deux publications en même temps (verrou) ;
  - délais aléatoires entre les gestes ; il ne fait que poster (aucun like, abonnement, commentaire ni message) ;
  - étiquette « contenu généré par IA » activée à chaque publication (introuvable = rien n'est publié) et mention dans la légende ;
  - anomalie (captcha, connexion ou vérification demandée, interface inattendue, échec) = ARRÊT de la ligne pour la journée, aucun contournement, journal + alerte Discord ;
  - mode essai (--essai) : va jusqu'au bouton Publier sans cliquer ; un essai réussi est obligatoire avant le premier vrai envoi d'une ligne ;
  - chaque publication (et chaque arrêt) est consignée dans Videos\\journal-videos.csv (date, compte, hook, résultat) ; la vidéo passe de a-valider\\ à publiees\\.
Seule exception au profil serveur « aucun navigateur » : cet agent, et seulement après le go de Liam. Avant le go, il ne fait rien (code 4).
  python Videos\\agents\\publication.py publier [--ligne A|B] [--essai] [--a-blanc]
  python Videos\\agents\\publication.py connexion --ligne A      (Liam seulement : ouvre le profil de la ligne pour qu'il se connecte lui-même)
  python Videos\\agents\\publication.py etat"""
import argparse, json, os, random, re, shutil, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import commun as C   # noqa: E402

AGENT = "videos-publication"
URL_DEPOT = "https://www.tiktok.com/tiktokstudio/upload"
URL_CONNEXION = "https://www.tiktok.com/login"
TOLERANCE_MIN = 45
PLAFOND_ABSOLU = 3
BLOCAGE = re.compile(r"captcha|puzzle|faites glisser|drag the slider|v[ée]rification de s[ée]curit[ée]|security (check|verification)|verify (it'?s|you)|"
                     r"confirmez que vous [êe]tes|unusual activity|activit[ée] inhabituelle|too many|trop de (tentatives|requ[êe]tes)|rate limit|"
                     r"r[ée]essayez plus tard|try again later|compte (suspendu|bloqu[ée]|restreint)|account (suspended|banned|restricted)|"
                     r"avertissement|warning|violation|community guidelines|code de v[ée]rification|verification code|se connecter|log in to tiktok|"
                     r"connectez-vous", re.I)
CONNEXION = re.compile(r"/login|/signup|passport", re.I)
STOP_VIDEOS = C.VIDEOS / "STOP"
STOP_B2B = C.RACINE / "B2B" / "STOP"
VERROU = C.VIDEOS / "publication.verrou"
ETAT_DEFAUT = {"publications": {}, "arrets": {}, "essais": {}}


class Arret(Exception):
    """Arrêt immédiat demandé par une règle (blocage, connexion, interface inattendue, étiquette IA introuvable…) : aucune nouvelle tentative ce jour-là."""


def blocage(texte, url=""):
    """Motif de blocage trouvé dans le texte visible de la page ou l'adresse (None si rien). Page de connexion = blocage aussi."""
    if CONNEXION.search(url or ""): return "page de connexion (session TikTok non ouverte) : aucun mot de passe n'est jamais tapé"
    m = BLOCAGE.search(texte or "")
    return f"« {m.group(0)} » affiché par TikTok" if m else None


def dans_un_creneau(conf, maintenant):
    """Heure prévue (HH:MM) si l'on est à +/- TOLERANCE_MIN d'un passage, sinon None."""
    m = maintenant.hour * 60 + maintenant.minute
    for h in conf["passages"]:
        if abs(int(h[:2]) * 60 + int(h[3:]) - m) <= TOLERANCE_MIN: return h
    return None


def ligne_du_passage(conf, passage):
    s = (conf["series_par_passage"] or {}).get(passage or "", "A")
    return s if s in ("A", "B") else "A"


def prochaine_video(ligne):
    """(mp4, légende, méta) de la plus ancienne vidéo complète de la ligne dans a-valider (mp4 + txt + json avec contenu_ia et mention IA), sinon None."""
    for mp4 in sorted(C.A_VALIDER.glob("*.mp4")) if C.A_VALIDER.exists() else []:
        txt, js = mp4.with_suffix(".txt"), mp4.with_suffix(".json")
        if not (txt.exists() and js.exists()): continue
        try: meta = json.loads(js.read_text(encoding="utf-8"))
        except ValueError: continue
        legende = txt.read_text(encoding="utf-8").strip()
        if meta.get("contenu_ia") is not True or C.MENTION_IA not in legende or (meta.get("serie") or "A") != ligne: continue
        return mp4, legende, meta
    return None


def compte(conf, ligne): return conf["lignes"][ligne].get("compte") or f"ligne {ligne}"


def du_jour(etat, jour, conf, ligne):
    """Publications du jour sur le COMPTE de la ligne (deux lignes sur un même compte partagent le plafond)."""
    c = compte(conf, ligne)
    return [p for p in etat.get("publications", {}).get(jour, []) if compte(conf, p.get("ligne", "A")) == c]


def refus(conf, etat, jour, maintenant, ligne, essai=False):
    """Raison de ne PAS publier maintenant (None = on peut). Vérifié avant toute ouverture de navigateur."""
    if STOP_B2B.exists() or STOP_VIDEOS.exists(): return "kill-switch STOP présent"
    if ligne not in ("A", "B"): return f"ligne inconnue « {ligne} »"
    arret = (etat.get("arrets") or {}).get(ligne) or {}
    if arret.get("jour") == jour: return f"ligne {ligne} arrêtée aujourd'hui après une anomalie ({arret.get('motif')}) : rien avant demain"
    if essai: return None
    if not conf["lignes"][ligne]["go_publier"]: return f"ligne {ligne} fermée : Liam n'a pas encore dit « go publier » pour sa première vidéo"
    if not (etat.get("essais") or {}).get(ligne): return f"ligne {ligne} : aucun essai réussi (publier --essai --ligne {ligne}) avant le premier vrai envoi"
    faites = du_jour(etat, jour, conf, ligne)
    if len(faites) >= min(PLAFOND_ABSOLU, int(conf["publications_max_par_jour"])): return f"plafond atteint ({len(faites)} publication(s) aujourd'hui sur ce compte)"
    h = dans_un_creneau(conf, maintenant)
    if not h: return "hors des heures prévues"
    if any(p.get("passage") == h and p.get("ligne") == ligne for p in faites): return f"passage {h} déjà publié"
    return None


def prendre_verrou():
    try:
        if VERROU.exists() and time.time() - VERROU.stat().st_mtime > 3 * 3600: VERROU.unlink()   # verrou abandonné
        fd = os.open(VERROU, os.O_CREAT | os.O_EXCL | os.O_WRONLY); os.write(fd, str(os.getpid()).encode()); os.close(fd); return True
    except FileExistsError: return False


def rendre_verrou():
    try: VERROU.unlink()
    except OSError: pass


def garde_harness(texte):
    """Garde du harness (B2B\\harness\\garde.py) : STOP, phrase interdite, secret. True si la légende peut partir."""
    try:
        sys.path.insert(0, str(C.RACINE / "B2B" / "harness")); import garde as G
        return G.avant_envoi("tiktok", texte, agent=AGENT)
    except Exception as e: print(f"  ! garde indisponible ({type(e).__name__})"); return True


# --- Navigateur (jamais en test) -----------------------------------------------------------------------------------
def profil(conf, ligne):
    p = os.path.expandvars(conf["lignes"][ligne].get("profil_navigateur") or f"%LOCALAPPDATA%\\JarvisTikTok\\ligne-{ligne}")
    if "%" in p: raise Arret("dossier du profil du navigateur introuvable (variable d'environnement absente)")
    return p


def ouvrir_profil(conf, ligne):   # pragma: no cover
    from playwright.sync_api import sync_playwright
    pw = sync_playwright().start()
    try:
        ctx = pw.chromium.launch_persistent_context(profil(conf, ligne), channel=conf["navigateur"] or None, headless=not conf["navigateur_visible"],
                                                    viewport={"width": 1280, "height": 900}, locale="fr-FR")
    except Exception: pw.stop(); raise
    return pw, ctx


def pause(page, mini=0.9, maxi=2.6):   # pragma: no cover
    page.wait_for_timeout(int(random.uniform(mini, maxi) * 1000))


def _texte(page):
    try: return page.inner_text("body", timeout=5000)
    except Exception: return ""


def controler(page):
    motif = blocage(_texte(page), page.url)
    if motif: raise Arret(motif)


def publier_tiktok(conf, ligne, mp4, legende, essai=False):   # pragma: no cover (navigateur réel, jamais en test)
    """Dépôt dans TikTok Studio avec le profil de la ligne. Lève Arret à la moindre anomalie. essai : s'arrête devant le bouton Publier sans cliquer."""
    pw, ctx = ouvrir_profil(conf, ligne)
    try:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(URL_DEPOT, wait_until="domcontentloaded", timeout=60000); pause(page, 3, 5); controler(page)
        champ = page.locator("input[type=file]")
        try: champ.first.wait_for(state="attached", timeout=30000)
        except Exception: raise Arret("interface inattendue : champ de dépôt de vidéo introuvable")
        champ.first.set_input_files(str(mp4), timeout=30000); pause(page, 2, 4); controler(page)
        editeur = page.locator("[contenteditable=true]").first
        try: editeur.wait_for(timeout=120000)
        except Exception: raise Arret("interface inattendue : zone de légende introuvable")
        controler(page); editeur.click(); pause(page)
        page.keyboard.press("Control+A"); page.keyboard.press("Delete"); pause(page, 0.5, 1.2)
        page.keyboard.insert_text(legende[:2100]); pause(page); controler(page)
        plus = page.get_by_text(re.compile(r"^(Afficher plus|Show more|Paramètres avancés|Advanced settings)$", re.I))
        if plus.count(): plus.first.click(); pause(page)
        ligne_ia = page.locator("div", has_text=re.compile(r"(contenu généré par (l')?IA|AI-generated content)", re.I)).last
        if not ligne_ia.count(): raise Arret("option « contenu généré par IA » introuvable : rien n'est publié sans l'étiquette")
        inter = ligne_ia.locator("[role=switch], input[type=checkbox]").first
        if not inter.count(): raise Arret("interrupteur « contenu généré par IA » introuvable : rien n'est publié sans l'étiquette")
        actif = lambda: (inter.get_attribute("aria-checked") or "").lower() == "true" or inter.is_checked()
        if not actif():
            inter.click(); pause(page)
            confirmer = page.get_by_role("button", name=re.compile(r"^(Activer|Turn on|OK|Confirmer)$", re.I))
            if confirmer.count(): confirmer.first.click(); pause(page)
        if not actif(): raise Arret("étiquette « contenu généré par IA » non activée : rien n'est publié")
        controler(page)
        bouton = page.get_by_role("button", name=re.compile(r"^(Publier|Post)$", re.I)).last
        try: bouton.wait_for(timeout=180000)
        except Exception: raise Arret("interface inattendue : bouton Publier introuvable")
        for _ in range(180):   # bouton actif quand le téléversement est fini
            if bouton.is_enabled(): break
            page.wait_for_timeout(1000); controler(page)
        else: raise Arret("téléversement non terminé après 3 minutes")
        if essai: return "essai : arrêté devant le bouton Publier, rien publié"
        pause(page); bouton.click(); page.wait_for_timeout(8000); controler(page)
        if not re.search(r"publi[ée]e?|posted|en cours de publication|being posted|manage your posts|gérer vos publications", _texte(page) + page.url, re.I):
            raise Arret("aucune confirmation de publication lue : vérifier à la main avant de relancer")
        return page.url
    finally:
        try: ctx.close()
        except Exception: pass
        pw.stop()


def cmd_connexion(ligne):   # pragma: no cover (Liam seulement, devant l'écran)
    """Ouvre le profil de la ligne sur la page de connexion de TikTok : Liam se connecte LUI-MÊME puis ferme la fenêtre. Rien n'est tapé ni enregistré par l'agent."""
    conf = C.cfg(); conf["navigateur_visible"] = True
    print(f"Profil de la ligne {ligne} ({compte(conf, ligne)}) : connecte-toi toi-même à TikTok, puis ferme la fenêtre. Je ne tape et ne lis aucun mot de passe.")
    pw, ctx = ouvrir_profil(conf, ligne)
    try:
        page = ctx.pages[0] if ctx.pages else ctx.new_page(); page.goto(URL_CONNEXION, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_event("close", timeout=0)
    finally:
        try: ctx.close()
        except Exception: pass
        pw.stop()
    C.journal(AGENT, "connexion", f"profil de la ligne {ligne} ouvert puis fermé par Liam"); return 0


def cmd_publier(a_blanc=False, maintenant=None, ligne=None, essai=False, publieur=publier_tiktok, alerter=C.alerter_discord, garde=garde_harness):
    conf = C.cfg(); maintenant = maintenant or C.heure_paris(); jour = f"{maintenant:%Y-%m-%d}"
    passage = dans_un_creneau(conf, maintenant)
    ligne = ligne or ligne_du_passage(conf, passage)
    etat = C.etat_lire(AGENT, ETAT_DEFAUT)
    r = refus(conf, etat, jour, maintenant, ligne, essai)
    if r:
        print(f"Rien publié : {r}."); C.journal(AGENT, "refus", r, a_blanc)
        return 0 if any(x in r for x in ("hors des heures", "déjà publié", "plafond")) else 4
    v = prochaine_video(ligne)
    if not v: print(f"Aucune vidéo complète de la ligne {ligne} dans a-valider."); C.journal(AGENT, "rien", f"ligne {ligne} : aucune vidéo à publier", a_blanc); return 0
    mp4, legende, meta = v; hook = meta.get("hook") or meta.get("accroche") or ""
    if a_blanc: print(f"[à blanc] {'essai' if essai else 'publication'} de {mp4.name} (« {meta.get('titre')} ») ligne {ligne}, passage {passage}, étiquette IA ; rien ouvert."); return 0
    if not essai and not garde(legende): print("Rien publié : légende bloquée par la garde."); C.journal(AGENT, "refus", "légende bloquée par la garde"); return 4
    if not prendre_verrou(): print("Une autre publication est en cours : rien fait (jamais deux en même temps)."); C.journal(AGENT, "occupé", mp4.name); return 0
    try:
        try: url = publieur(conf, ligne, mp4, legende, essai)
        except Exception as e:
            motif = str(e)[:200] if isinstance(e, Arret) else f"erreur {type(e).__name__}"
            etat.setdefault("arrets", {})[ligne] = {"jour": jour, "motif": motif}; C.etat_ecrire(AGENT, etat)
            C.journal(AGENT, "ARRÊT", f"ligne {ligne} : {motif}")
            C.csv_ligne(AGENT, mp4.stem, ligne, compte(conf, ligne), "arrêt" + (" (essai)" if essai else ""), hook, motif)
            alerter(f"🛑 Publication TikTok arrêtée (ligne {ligne}{', essai' if essai else ''}) : {motif}. Rien d'autre n'est tenté aujourd'hui sur cette ligne ; à vérifier par Liam.")
            print(f"ARRÊT : {motif}"); return 1
        if essai:
            etat.setdefault("essais", {})[ligne] = f"{maintenant:%Y-%m-%d %H:%M}"; C.etat_ecrire(AGENT, etat)
            C.journal(AGENT, "essai", f"ligne {ligne} : {mp4.name} jusqu'au bouton Publier, rien publié")
            C.csv_ligne(AGENT, mp4.stem, ligne, compte(conf, ligne), "essai réussi (rien publié)", hook)
            alerter(f"🧪 Essai TikTok réussi (ligne {ligne}) : {mp4.name} prêt jusqu'au bouton Publier, rien publié.")
            print(f"Essai réussi : {mp4.name} (rien publié)."); return 0
        C.PUBLIEES.mkdir(parents=True, exist_ok=True)
        for f in (mp4, mp4.with_suffix(".txt"), mp4.with_suffix(".json")): shutil.move(str(f), C.PUBLIEES / f.name)
        etat.setdefault("publications", {}).setdefault(jour, []).append({"ligne": ligne, "passage": passage, "video": mp4.name, "heure": f"{maintenant:%H:%M}"})
        etat["publications"] = dict(sorted(etat["publications"].items())[-31:])   # un mois suffit (le reste est dans le journal)
        C.etat_ecrire(AGENT, etat)
        C.journal(AGENT, "publié", f"ligne {ligne} : {mp4.name} « {meta.get('titre')} » (passage {passage}, étiquette IA)")
        C.csv_ligne(AGENT, mp4.stem, ligne, compte(conf, ligne), "publié", hook, f"passage {passage}, étiquette IA",
                    histoire=meta.get("histoire") or "", theme=meta.get("theme") or "", duree_s=meta.get("duree_s") or "", voix=meta.get("voix") or "",
                    publie_le=f"{maintenant:%Y-%m-%d %H:%M}", url_tiktok="")   # adresse TikTok : pas encore relevée après publication (à faire avant le go publier)
        alerter(f"🎬 TikTok ({compte(conf, ligne)}) : vidéo publiée « {meta.get('titre')} » ({mp4.name}, passage {passage}, étiquette IA activée).")
        print(f"Publié : {mp4.name}"); return 0
    finally: rendre_verrou()


def cmd_etat():
    conf = C.cfg(); e = C.etat_lire(AGENT, ETAT_DEFAUT); jour = f"{C.heure_paris():%Y-%m-%d}"
    for l in ("A", "B"):
        n = sum(p.get("ligne") == l for p in e["publications"].get(jour, []))
        print(f"ligne {l} ({compte(conf, l)}) : go_publier {conf['lignes'][l]['go_publier']} ; essai {e['essais'].get(l) or 'jamais'} ; aujourd'hui {n} publication(s)"
              + (f" ; arrêt du {e['arrets'][l].get('jour')} : {e['arrets'][l].get('motif')}" if e["arrets"].get(l) else ""))
    return 0


def main(argv=None):
    a = argparse.ArgumentParser(prog="videos-publication"); sp = a.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("publier"); p.add_argument("--a-blanc", action="store_true"); p.add_argument("--essai", action="store_true"); p.add_argument("--ligne", choices=["A", "B"])
    c = sp.add_parser("connexion"); c.add_argument("--ligne", choices=["A", "B"], required=True)
    sp.add_parser("etat")
    a = a.parse_args(argv)
    if a.cmd == "etat": return cmd_etat()
    C.exiger(AGENT, a.cmd, getattr(a, "a_blanc", False)); C.exiger_regles(AGENT, getattr(a, "a_blanc", False))
    if a.cmd == "connexion": return cmd_connexion(a.ligne)
    return cmd_publier(a.a_blanc, ligne=a.ligne, essai=a.essai)


if __name__ == "__main__":
    sys.exit(main())
