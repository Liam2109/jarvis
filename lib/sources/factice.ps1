# Source FACTICE — réservée aux tests (JARVIS_TEST=1). Hors test elle refuse de répondre : jamais de faux cours affiché par erreur.
# Pour qu'un test l'utilise : "sources_validees": ["factice"] dans la COPIE temporaire de config.json.
# $script:FauxCours (liste de @{ nom; symbole; prix; devise; variation_pct }) et $script:FauxActus (liste de @{ titre; resume; valeur }) pilotent les réponses ;
# $script:FauxPanne = 'texte' simule une source indisponible. Aucun réseau.
$script:FauxCours = $null; $script:FauxActus = $null; $script:FauxPanne = ''; $script:FauxAppels = 0
Register-SourceMarche -Nom 'factice' -MinSecondes 0 -Cours {
    param($valeurs)
    $script:FauxAppels++
    if (-not (Test-ModeTest)) { return @{ dispo = $false; raison = 'source factice réservée aux tests' } }
    if ($script:FauxPanne) { return @{ dispo = $false; raison = $script:FauxPanne } }
    $l = if ($script:FauxCours) { @($script:FauxCours) } else { @($valeurs | ForEach-Object { @{ nom = $_.nom; symbole = $_.symbole; prix = 100.0; devise = 'EUR'; variation_pct = 1.5 } }) }
    @{ dispo = $true; cours = @($l | ForEach-Object { @{ nom = $_.nom; symbole = $_.symbole; prix = $_.prix; devise = $_.devise; variation_pct = $_.variation_pct; date = (Get-Date).ToString('o'); source = 'Factice' } }) }
} -Actus {
    param($valeurs, [datetime]$depuis)
    if (-not (Test-ModeTest)) { return @{ dispo = $false; raison = 'source factice réservée aux tests' } }
    if ($script:FauxPanne) { return @{ dispo = $false; raison = $script:FauxPanne } }
    @{ dispo = $true; items = @(@($script:FauxActus) | Where-Object { $_ } | ForEach-Object { @{ titre = $_.titre; resume = $_.resume; valeur = $_.valeur; date = (Get-Date).AddMinutes(-30).ToString('o'); source = 'Factice' } }) }
}
