# Agent Instagram (B2B\agents\instagram.py) : lancé UNE fois par session (commande « continu --pid <Jarvis> »), dans un processus caché SÉPARÉ qui boucle (un passage toutes les cycle_minutes) et s'arrête si Jarvis s'arrête.
# Secours : python B2B\agents\instagram.py arreter. Jarvis n'en dépend pas : le script est autonome (planifiable aussi). Il publie UN post par jour vers 12 h 30 (heure de Paris) d'après B2B\docs\INSTAGRAM-PLAN.md,
# mais SEULEMENT si envoi_automatique = true dans B2B\agents\instagram-config.json (par défaut false = simulation : rien n'est publié). Connexion perdue, vérification de sécurité ou erreur : arrêt immédiat et alerte Discord.
# Ni Ollama ni Jarvis ne sont lancés par ce script. Désactivé tant que instagram_actif n'est pas « oui » dans config.json.
function Get-InstagramConfig {
    $oui = @('oui', 'true', '1', 'on', 'yes'); $c = @{ actif = $false; delai = 90 }
    if ($Config.PSObject.Properties['instagram_actif'] -and "$($Config.instagram_actif)".Trim().ToLower() -in $oui) { $c.actif = $true }
    $c
}

function Update-Instagram([datetime]$now = (Get-Date)) {
    # Ne fait RIEN si instagram_actif n'est pas "oui". Un seul lancement par session de Jarvis, 90 s après le démarrage ; jamais en mode jeu.
    $c = Get-InstagramConfig; if (-not $c.actif) { return $false }
    if ($script:InstagramLancee) { return $false }
    if (-not $script:InstagramDebut) { $script:InstagramDebut = $now }
    if (($now - $script:InstagramDebut).TotalSeconds -lt $c.delai) { return $false }
    if ($script:ModeJeu -eq $true) { return $false }
    $script:InstagramLancee = $true
    if (Test-ModeTest) { $script:InstagramRunnerLance = $true; return $true }      # tests : jamais de vrai processus
    $s = Join-Path $script:RacineReelle 'B2B\agents\instagram.py'; $py = Get-Command python -ErrorAction SilentlyContinue
    if (-not (Test-Path $s) -or -not $py) { Write-Journal -Action 'Instagram' -Resultat 'non lancé (B2B\agents\instagram.py ou python introuvable)'; return $false }
    $log = Join-Path $script:RacineReelle ('logs\instagram-{0}.log' -f (Get-Date -Format 'yyyy-MM-dd'))
    try {
        $env:PYTHONIOENCODING = 'utf-8'
        [void](Start-Process $py.Source -ArgumentList "`"$s`"", 'continu', '--pid', "$PID" -WorkingDirectory (Split-Path (Split-Path $s -Parent) -Parent) -WindowStyle Hidden -RedirectStandardOutput $log -RedirectStandardError ($log + '.err') -PassThru)
        Write-Journal -Action 'Instagram' -Resultat 'agent lancé (continu : un post par jour vers 12 h 30 ; simulation tant que envoi_automatique = false ; arrêt immédiat et alerte sur toute erreur)'; $true
    } catch { Write-Journal -Action 'Instagram' -Resultat "lancement impossible : $($_.Exception.Message)"; $false }
}
