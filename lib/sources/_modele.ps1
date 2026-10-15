# MODÈLE de source de marché (ce fichier commence par « _ » : il n'est jamais chargé). Copiez-le en lib\sources\<nom>.ps1, remplissez-le, puis
# ajoutez "<nom>" à "sources_validees" dans config.json (et mettez "marche_actif": true). Rien n'est lu avant.
# Exigences : API ou flux RSS PUBLICS dont les conditions d'utilisation autorisent cet usage ; pas de scraping d'un site qui l'interdit ;
# lecture seule ; aucune clé en clair (utilisez .env) ; respectez la limite de requêtes de la source avec -MinSecondes.
# Register-SourceMarche -Nom 'exemple' -MinSecondes 900 `
#   -Cours { param($valeurs)                      # $valeurs : @{ nom; symbole } des valeurs suivies
#       # ... appel HTTPS en GET ...
#       @{ dispo = $true; cours = @(@{ nom = 'Thales'; symbole = 'HO'; prix = 150.2; devise = 'EUR'; variation_pct = 1.1; date = (Get-Date).ToString('o'); source = 'Exemple' }) }
#       # en cas de problème : @{ dispo = $false; raison = 'quota atteint' }
#   } `
#   -Actus { param($valeurs, [datetime]$depuis)
#       @{ dispo = $true; items = @(@{ titre = '...'; resume = '...'; date = (Get-Date).ToString('o'); source = 'Exemple'; valeur = 'Thales' }) }
#   }
