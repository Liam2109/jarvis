# Agent devis (B2B\agents\devis.py) : lancé UNE fois par session (commande « continu --pid <Jarvis> »), dans un processus caché SÉPARÉ qui boucle (un passage toutes les cycle_minutes) et s'arrête si Jarvis s'arrête.
# Secours : python B2B\agents\devis.py arreter. Jarvis n'en dépend pas : le script est autonome. Les devis se PRÉPARENT à la main (python B2B\agents\devis.py preparer fiche.txt) ; la boucle poste l'aperçu « à valider »
# et lit le « ok devis » de Liam SEULEMENT si envoi_automatique = true dans B2B\agents\devis-config.json (par défaut false = simulation). L'agent n'envoie JAMAIS rien au client et n'écrit pas chez Stripe.
# Erreur : arrêt immédiat et alerte Discord. Ni Ollama ni Jarvis ne sont lancés par ce script. Désactivé tant que devis_actif n'est pas « oui » dans config.json.
function Get-DevisConfig {
    $oui = @('oui', 'true', '1', 'on', 'yes'); $c = @{ actif = $false; delai = 90 }
    if ($Config.PSObject.Properties['devis_actif'] -and "$($Config.devis_actif)".Trim().ToLower() -in $oui) { $c.actif = $true }
    $c
}

function Update-Devis([datetime]$now = (Get-Date)) {
    # Ne fait RIEN si devis_actif n'est pas "oui". Un seul lancement par session de Jarvis, 90 s après le démarrage ; jamais en mode jeu.
    $c = Get-DevisConfig; if (-not $c.actif) { return $false }
    if ($script:DevisLance) { return $false }
    if (-not $script:DevisDebut) { $script:DevisDebut = $now }
    if (($now - $script:DevisDebut).TotalSeconds -lt $c.delai) { return $false }
    if ($script:ModeJeu -eq $true) { return $false }
    $script:DevisLance = $true
    if (Test-ModeTest) { $script:DevisRunnerLance = $true; return $true }      # tests : jamais de vrai processus
    $s = Join-Path $script:RacineReelle 'B2B\agents\devis.py'; $py = Get-Command python -ErrorAction SilentlyContinue
    if (-not (Test-Path $s) -or -not $py) { Write-Journal -Action 'Devis' -Resultat 'non lancé (B2B\agents\devis.py ou python introuvable)'; return $false }
    $log = Join-Path $script:RacineReelle ('logs\devis-{0}.log' -f (Get-Date -Format 'yyyy-MM-dd'))
    try {
        $env:PYTHONIOENCODING = 'utf-8'
        [void](Start-Process $py.Source -ArgumentList "`"$s`"", 'continu', '--pid', "$PID" -WorkingDirectory (Split-Path (Split-Path $s -Parent) -Parent) -WindowStyle Hidden -RedirectStandardOutput $log -RedirectStandardError ($log + '.err') -PassThru)
        Write-Journal -Action 'Devis' -Resultat 'agent lancé (continu : aperçu « à valider » et « ok devis » de Liam ; simulation tant que envoi_automatique = false ; rien n''est envoyé au client ; arrêt immédiat et alerte sur toute erreur)'; $true
    } catch { Write-Journal -Action 'Devis' -Resultat "lancement impossible : $($_.Exception.Message)"; $false }
}
