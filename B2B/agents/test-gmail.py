"""Test de connexion IMAP Gmail. N'affiche jamais le mot de passe."""
import imaplib, re, sys
from pathlib import Path

env = Path(__file__).resolve().parent.parent / ".env"
d = dict(re.findall(r"^(\w+)=(.*)$", env.read_text(encoding="utf-8-sig"), re.M))
comptes = [("contact.lmsites@gmail.com", "GMAIL_1_APP_PASSWORD"),
           ("liamdigital2109@gmail.com", "GMAIL_2_APP_PASSWORD")]
for adresse, var in comptes:
    p = d.get(var, "").strip().strip("\"'").replace(" ", "")
    print(f"{adresse} : longueur du code = {len(p)} ; lettres minuscules seulement = {p.isalpha() and p.islower()}")
    if not p:
        print("   -> vide, boîte sautée")
        continue
    try:
        m = imaplib.IMAP4_SSL("imap.gmail.com", 993, timeout=20)
        print("   ->", m.login(adresse, p))
        m.logout()
    except Exception as e:
        print("   -> ERREUR :", type(e).__name__, str(e)[:200])
