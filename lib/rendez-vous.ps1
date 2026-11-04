# Agent rendez-vous (B2B\agents\rendez-vous.py) : lancé UNE fois par session (commande « continu --pid <Jarvis> »), dans un processus caché SÉPARÉ qui boucle (un passage toutes les 5 minutes) et s'arrête si Jarvis s'arrête.
# Secours : python B2B\agents\rendez-vous.py arreter. Jarvis n'en dépend pas : le script est autonome. Il lit l'agenda Google de Liam par son adresse secrète iCal (agents\rendez-vous-config.json, hors git, jamais affichée)
# et poste dans le salon Discord « rendez-vous » un message pour chaque « Rendez-vous de 15 minutes » réservé, déplacé ou annulé, plus un rappel 30 minutes avant ; SEULEMENT si envoi_automatique = true
# (par défaut false = simulation : le journal dit ce qui serait posté). Lecture seule : rien n'est écrit dans l'agenda, personne n'est contacté. Erreur : arrêt immédiat et alerte Discord.
# Ni Ollama ni Jarvis ne sont lancés par ce script. Désactivé tant que rendez_vous_actif n'est pas « oui » dans config.json.
function Get-RendezVousConfig {
    $oui = @('oui', 'true', '1', 'on', 'yes'); $c = @{ actif = $false; delai = 90 }
    if ($Config.PSObject.Properties['rendez_vous_actif'] -and "$($Config.rendez_vous_actif)".Trim().ToLower() -in $oui) { $c.actif = $true }
    $c
}

function Update-RendezVous([datetime]$now = (Get-Date)) {
    # Ne fait RIEN si rendez_vous_actif n'est pas "oui". Un seul lancement par session de Jarvis, 90 s après le démarrage ; jamais en mode jeu.
    $c = Get-RendezVousConfig; if (-not $c.actif) { return $false }
    if ($script:RendezVousLance) { return $false }
    if (-not $script:RendezVousDebut) { $script:RendezVousDebut = $now }
    if (($now - $script:RendezVousDebut).TotalSeconds -lt $c.delai) { return $false }
    if ($script:ModeJeu -eq $true) { return $false }
    $script:RendezVousLance = $true
    if (Test-ModeTest) { $script:RendezVousRunnerLance = $true; return $true }      # tests : jamais de vrai processus
    $s = Join-Path $script:RacineReelle 'B2B\agents\rendez-vous.py'; $py = Get-Command python -ErrorAction SilentlyContinue
    if (-not (Test-Path $s) -or -not $py) { Write-Journal -Action 'Rendez-vous' -Resultat 'non lancé (B2B\agents\rendez-vous.py ou python introuvable)'; return $false }
    $log = Join-Path $script:RacineReelle ('logs\rendez-vous-{0}.log' -f (Get-Date -Format 'yyyy-MM-dd'))
    try {
        $env:PYTHONIOENCODING = 'utf-8'
        [void](Start-Process $py.Source -ArgumentList "`"$s`"", 'continu', '--pid', "$PID" -WorkingDirectory (Split-Path (Split-Path $s -Parent) -Parent) -WindowStyle Hidden -RedirectStandardOutput $log -RedirectStandardError ($log + '.err') -PassThru)
        Write-Journal -Action 'Rendez-vous' -Resultat 'agent lancé (continu : un passage toutes les 5 min ; simulation tant que envoi_automatique = false ; lecture seule de l''agenda ; arrêt immédiat et alerte sur toute erreur)'; $true
    } catch { Write-Journal -Action 'Rendez-vous' -Resultat "lancement impossible : $($_.Exception.Message)"; $false }
}
