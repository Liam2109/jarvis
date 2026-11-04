#!/usr/bin/env python3
"""Autorise l'accès Gmail (API, OAuth) d'un compte puis affiche seulement « OK, adresse = … » ou l'erreur. N'ENVOIE RIEN, ne lit aucun message.

  python agents\\test-gmail-api.py contact.lmsites@gmail.com   autorise CE compte seulement (navigateur, une fois ; jeton expiré ou absent = nouvelle autorisation)
  python agents\\test-gmail-api.py                            teste tous les comptes déjà autorisés (aucune autorisation lancée)

L'avertissement « application non validée » du navigateur est normal. Jeton : agents\\gmail-token-<adresse>.json. Le compte est inscrit dans agents\\reponses-config.json › api › comptes."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gmail_api as GA


def un_compte(adresse, autoriser):
    try:
        try: cl = GA.client(adresse)
        except GA.JetonExpire:
            if not autoriser: raise
            print("Autorisation : valide dans le navigateur qui s'ouvre (avertissement « application non validée » normal).")
            GA.autoriser(adresse); cl = GA.client(adresse)
        GA.enregistrer_adresse(cl.adresse)
        print(f"OK, adresse = {cl.adresse}")
        return True
    except (GA.JetonExpire, GA.BibliothequeManquante, FileNotFoundError, GA.ErreurApi) as e: print(f"ERREUR ({adresse}) : {e}")
    except Exception as e: print(f"ERREUR ({adresse}) : {type(e).__name__} (autorisation refusée ou interrompue ?)")
    return False


def main(argv):
    if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")
    try: GA.bibliotheques()
    except GA.BibliothequeManquante as e: print(f"ERREUR : {e}"); return 1
    if argv:
        return 0 if un_compte(argv[0].strip().lower(), True) else 1
    comptes = GA.comptes_autorises()
    if not comptes: print("Aucun compte autorisé : python agents\\test-gmail-api.py <adresse>"); return 1
    return 0 if all([un_compte(a, False) for a in comptes]) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
