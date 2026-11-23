#!/usr/bin/env python3
"""Tests silencieux de la file « leads chauds » (maillon 2, CARTE-RELAIS) : AUCUN réseau, aucun envoi, fichiers temporaires.  python agents\\test_leads_chauds.py
Cas : un lead chaud entre (nom, téléphone, jour, métier, dernière réponse, Sid par défaut) ; un STOP / « pas intéressé » sort ; « moyen terme » reste avec sa date du 07/12 ;
une seule alerte par lead (même après sortie et retour) ; un envoi raté est réessayé ; la simulation n'écrit ni ne marque rien ; un lead = une entrée."""
import os, sys, tempfile
os.environ.setdefault("JARVIS_TEST", "1")
from pathlib import Path
ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import registre as RG, leads_chauds as LC

tmp = Path(tempfile.mkdtemp(prefix="lc-test-")); F = tmp / "file.json"; SUIVI = tmp / "suivi.csv"
SUIVI.write_text("nom;telephone;statut\nLes 4M;02 33 08 56 42;STOP\n", encoding="utf-8")


def ent(nom, tel, res, note, metier="garage", statut="à reprendre", retour="2026-11-19"):
    return {"nom": nom, "commune": "Rouen", "tel": tel, "metier": metier, "dernier_resultat": res, "note": note, "statut": statut, "retour": retour, "pour": "Liam", "resultat_le": "2026-11-16"}


def registre(*es): return {"version": 1, "entreprises": {f"{RG.norm(e['nom'])}|rouen|{e['tel']}": e for e in es}, "feuilles_lues": {}}


envois = []
def envoyer(t): envois.append(t); return True


# 1) un lead chaud entre : alerte avec nom, téléphone, jour, qui rappelle (Sid) ; la file porte les 5 champs
reg = registre(ent("Auto Dupont", "0235000001", "À rappeler", "rappeler mardi", retour="2026-11-24"))
e, s, t = LC.synchroniser(reg, "2026-11-23", envoyer, F, SUIVI)
assert len(e) == 1 and not s and len(envois) == 1, (e, s, envois)
a = envois[0]; assert "Sid" in a and "Auto Dupont" in a and "02 35 00 00 01" in a and "2026-11-24" in a and "garage" in a and "Aucun message" in a, a
l = LC.lire(F)[0]; assert l["nom"] == "Auto Dupont" and l["tel"] == "0235000001" and l["jour"] == "2026-11-24" and l["metier"] == "garage" and "rappeler mardi" in l["derniere_reponse"] and l["rappelle"] == "Sid", l

# 2) pas de doublon d'alerte : un second passage ne renvoie rien, la file garde une seule entrée
LC.synchroniser(reg, "2026-11-23", envoyer, F, SUIVI); LC.synchroniser(reg, "2026-11-24", envoyer, F, SUIVI)
assert len(envois) == 1 and len(LC.lire(F)) == 1, envois

# 3) STOP / pas intéressé / refus de l'agent Réponses sortent ; « moyen terme » reste avec le 07/12
reg = registre(ent("Auto Dupont", "0235000001", "À rappeler", "STOP"),
               ent("Les 4M", "0233085642", "Je dois réfléchir", "hésite"),
               ent("Garage du Rond Point", "0235647009", "Je dois réfléchir", "pas intéressé pour l'instant ( prospect moyen terme )"),
               ent("Autre", "0235000002", "Je dois réfléchir", "non"),
               ent("Fini", "0235000003", "Non catégorique", "x", statut="terminée"))
e, s, t = LC.synchroniser(reg, "2026-11-25", envoyer, F, SUIVI)
noms = [x["nom"] for x in LC.lire(F)]
assert noms == ["Garage du Rond Point"], noms                                  # Auto Dupont (STOP en note), Les 4M (STOP reçu), Autre (« non ») : sortis
assert len(s) == 1 and LC.lire(F)[0]["jour"] == "2026-12-07", LC.lire(F)         # moyen terme : relance le 07/12
assert len(envois) == 2 and "Garage du Rond Point" in envois[1] and "4M" not in " ".join(envois), envois

# 4) un lead sorti puis revenu n'est pas ré-annoncé
reg = registre(ent("Auto Dupont", "0235000001", "À rappeler", "rappeler"))
LC.synchroniser(reg, "2026-11-26", envoyer, F, SUIVI)
assert len(envois) == 2 and [x["nom"] for x in LC.lire(F)] == ["Auto Dupont"], envois

# 5) envoi raté : pas marqué, réessayé ; simulation : rien envoyé, rien marqué ; ecrire=False : rien écrit
F2 = tmp / "f2.json"; reg = registre(ent("Neuf", "0235000009", "À rappeler", "ok"))
LC.synchroniser(reg, "2026-11-23", lambda t: False, F2, SUIVI); assert not LC.charger(F2)["alertes"]
n0 = len(envois); LC.synchroniser(reg, "2026-11-23", None, F2, SUIVI); assert len(envois) == n0 and not LC.charger(F2)["alertes"]
LC.synchroniser(reg, "2026-11-24", envoyer, F2, SUIVI); assert len(envois) == n0 + 1 and LC.charger(F2)["alertes"]
F3 = tmp / "f3.json"; LC.synchroniser(reg, "2026-11-23", envoyer, F3, SUIVI, ecrire=False); assert not F3.exists()
print("test_leads_chauds : OK")
