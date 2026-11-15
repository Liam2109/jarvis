#!/usr/bin/env python3
"""Registre - import des anciens lots (15/11/2026) : sur des fichiers FICTIFS (dossier temporaire), les entreprises des lots, les fiches « préparé »
et les prospects « envoyé/STOP/refusé » sont ajoutées une seule fois, comme données au lot e-mail sans résultat d'appel ; une entreprise déjà connue
(même téléphone, ou même nom et commune) n'est pas recopiée ; les annuaires bruts (prospects*.csv) ne sont pas lus. Sans réseau."""
import shutil, tempfile, unittest
from pathlib import Path
import commun as C
import registre as RG

ENTETE = "nom;metier;ville;telephone;email;cp;date_collecte;statut\n"


class Anciens(unittest.TestCase):
    def setUp(self):
        self.r = Path(tempfile.mkdtemp(prefix="registre-anciens-")); (self.r / "lots").mkdir()
        (self.r / "lots" / "lot-2026-10-29.csv").write_text(ENTETE + "Elec Martin;électricien;Rouen;06 11 22 33 44;;76000;;préparé\nPlomb Durand;plombier;Évreux;;a@b.fr;27000;;préparé\n", encoding="utf-8-sig")
        (self.r / "lots" / "lot1.csv").write_text("nom;metier;ville;telephone\nELEC  MARTIN;électricien;rouen;0611223344\n", encoding="utf-8-sig")   # même entreprise
        (self.r / "prospection-trouves.csv").write_text(ENTETE + "Garage Petit;garagiste;Caen;02 31 00 00 00;;14000;2026-10-30;préparé\nNeuf;fleuriste;Caen;02 31 99 99 99;;14000;2026-10-30;sans site, téléphone\n", encoding="utf-8-sig")
        (self.r / "suivi-prospects.csv").write_text("nom;metier;ville;email;telephone;statut;date_statut;date_envoi\nPlomb Durand;plombier;Evreux;a@b.fr;;envoyé;2026-10-29;2026-10-29\nCoif Léa;coiffeur;Rouen;c@d.fr;;STOP;2026-11-02;\nAttente;coiffeur;Rouen;;;à contacter;2026-11-02;\n", encoding="utf-8-sig")
        (self.r / "prospects.csv").write_text("siren;nom;ville;telephone\n1;Annuaire Brut;Rouen;0600000000\n", encoding="utf-8-sig")

    def tearDown(self): shutil.rmtree(self.r, ignore_errors=True)

    def test_import(self):
        reg = RG.vide(); RG.donner(reg, {"nom": "Garage Petit SARL", "ville": "Caen", "tel": "0231000000"}, RG.SID, "2026-11-16")   # déjà connue (même téléphone)
        n = RG.importer_anciens(reg, RG.anciens(self.r))
        self.assertEqual(sum(n.values()), 3)   # Elec Martin, Plomb Durand, Coif Léa
        noms = sorted(x["nom"] for x in reg["entreprises"].values())
        self.assertEqual(noms, ["Coif Léa", "Elec Martin", "Garage Petit SARL", "Plomb Durand"])
        x = reg["entreprises"][RG.trouver(reg, "Elec Martin", "Rouen", "0611223344")]
        self.assertEqual((x["a_qui"], x["essais"], x["dernier_resultat"], x["statut"], x["date"], x["departement"]), (RG.LOT, 0, "", "donnée", "2026-10-29", "76"))
        self.assertEqual(reg["entreprises"][RG.trouver(reg, "Garage Petit", "Caen", "0231000000")]["a_qui"], RG.SID)   # pas écrasée
        self.assertEqual(sum(RG.importer_anciens(reg, RG.anciens(self.r)).values()), 0)   # deuxième passage : rien
        self.assertFalse(RG.dues(reg, "2026-12-31", RG.SID) or RG.dues(reg, "2026-12-31", RG.LIAM))   # jamais redonnées


if __name__ == "__main__":
    unittest.main(verbosity=1)
