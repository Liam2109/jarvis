# Tableau de bord « Jarvis - Mon entreprise »

Fichier local `dashboard\index.html`, ouvert par l'icône du bureau « Jarvis - Mon entreprise » (`pythonw outils\agents-json.py --ouvrir`). Aucun hébergement, aucun CDN, tout marche hors ligne.

- **Données** : `outils\agents-json.py` écrit `agents.js`, `ventes.js` et `docs.js` (+ `agents.json`, `ventes.json`), hors git. La page les relit toutes les 5 minutes ; ils sont réécrits à chaque clic sur l'icône (et par `outils\servir-dashboard.py` sur le serveur).
- **Aujourd'hui** (en haut) : appels notés par Sid et leads chauds (À rappeler, Je dois réfléchir) et RDV pris, lus dans toutes les feuilles « Appels Sid » modifiées aujourd'hui (fonctions de `resume-sid.py`, API Google gratuite) ; devis envoyés (`devis-etat.json`) ; paiements reçus (Stripe en lecture seule). Un chiffre indisponible s'affiche « — » avec la raison. Comptes seulement, jamais de nom, d'e-mail ni de téléphone.
- **Style** (clair, 17/11) : barre latérale en verre flottante (barre du bas sur mobile), carte vedette bleu nuit pour les appels notés par Sid, puis une carte en verre par autre chiffre (icône en pastille, paiements en ocre foncé), une grande carte Agents avec une colonne par pôle ; Pipeline est dans Documents. Trois gammes : bleus, blancs bleutés, ocre. La courbe fine n'apparaît que si `ventes.json` donne une vraie série `serie` sur plusieurs jours (pas encore le cas). Sans `ventes.js`, la page dit de lancer l'icône.
- **Agents** : une carte par pôle, un voyant par agent (bleu plein = passé aujourd'hui, anneau bleu = passé avant, gris = aucun passage visible sur ce PC, losange bleu nuit = erreur).
- **Test** : `python tests\test_ventes_dashboard.py` (silencieux). **Captures** : `node B2B\sites\outils\dashboard-captures.mjs` → `dashboard\apercu\`.

## Crédit
Mise en page revue avec le skill **unslop** de Damir Sokolovsky ([@heydamir](https://x.com/heydamir)), https://github.com/heydamir/unslop, sous licence CC BY 4.0 (copie dans `.claude\skills\unslop\`).
