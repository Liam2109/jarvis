# Ouverture quotidienne du « pouls » (page Claude) dans le navigateur par défaut.
# Au démarrage de Jarvis, une seule fois par jour, au premier lancement après 7 h (jamais avant, jamais deux fois le même jour).
# Réglage : "ouvrir_pouls_au_demarrage" dans config.local.json (true par défaut ; false pour couper). Jamais en mode test (JARVIS_TEST=1) : aucun navigateur n'est ouvert, seule la date est mémorisée.
$script:PoulsUrl = 'https://claude.ai/artifact/VX1ybGvUaZ1S1WinAiX649'

function Get-OuvrirPoulsActif {
    if (-not $Config.PSObject.Properties['ouvrir_pouls_au_demarrage']) { return $true }
    [bool]$Config.ouvrir_pouls_au_demarrage
}

function Initialize-OuverturePouls([datetime]$now = (Get-Date)) {
    if (-not (Get-OuvrirPoulsActif)) { return $false }
    if ($now.Hour -lt 7) { return $false }
    $aujourdhui = $now.ToString('yyyy-MM-dd')
    $o = Read-JsonMemoire 'pouls-jour.json'
    if ($o -and "$($o.date)" -eq $aujourdhui) { return $false }
    if (Test-ModeTest) { Save-JsonMemoire 'pouls-jour.json' ([ordered]@{ date = $aujourdhui }); return $true }
    try {
        Start-Process $script:PoulsUrl
        Save-JsonMemoire 'pouls-jour.json' ([ordered]@{ date = $aujourdhui })
        Write-Journal -Action 'Pouls du jour' -Resultat 'ouvert dans le navigateur par défaut (une fois par jour, premier démarrage après 7 h)'
        $true
    } catch {
        Write-Journal -Action 'Pouls du jour' -Resultat "ouverture impossible : $($_.Exception.Message)"
        $false
    }
}
