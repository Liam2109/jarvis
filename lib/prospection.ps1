# Agent Prospection (B2B\agents\prospection.py) : lancé au démarrage de Jarvis dans un processus caché SÉPARÉ. Jarvis n'en dépend pas : le script est
# autonome (planifiable aussi). Python garde la date du dernier lancement (agents\prospection-dernier-lancement.txt) : la journée n'est lancée qu'UNE fois
# par jour. Le lot du jour est posté dans le salon business par le bot Jarvis (API REST) ; rien n'est envoyé sans « ok lot » (ou ✅) de Liam seul,
# sauf si envoi_automatique = true dans B2B\agents\prospection-config.json. Ni Ollama ni Jarvis ne sont lancés par ce script.
function Get-ProspectionConfig {
    $oui = @('oui', 'true', '1', 'on', 'yes'); $c = @{ actif = $false; delai = 90 }
    if ($Config.PSObject.Properties['prospection_actif'] -and "$($Config.prospection_actif)".Trim().ToLower() -in $oui) { $c.actif = $true }
    $c
}

function Update-Prospection([datetime]$now = (Get-Date)) {
    # Ne fait RIEN si prospection_actif n'est pas "oui". Un seul lancement par session de Jarvis, 90 s après le démarrage ; jamais en mode jeu.
    $c = Get-ProspectionConfig; if (-not $c.actif) { return $false }
    if ($script:ProspectionLancee) { return $false }
    if (-not $script:ProspectionDebut) { $script:ProspectionDebut = $now }
    if (($now - $script:ProspectionDebut).TotalSeconds -lt $c.delai) { return $false }
    if ($script:ModeJeu -eq $true) { return $false }
    $script:ProspectionLancee = $true
    if (Test-ModeTest) { $script:ProspectionRunnerLance = $true; return $true }      # tests : jamais de vrai processus
    $s = Join-Path $script:RacineReelle 'B2B\agents\prospection.py'; $py = Get-Command python -ErrorAction SilentlyContinue
    if (-not (Test-Path $s) -or -not $py) { Write-Journal -Action 'Prospection' -Resultat 'non lancée (B2B\agents\prospection.py ou python introuvable)'; return $false }
    $log = Join-Path $script:RacineReelle ('logs\prospection-{0}.log' -f (Get-Date -Format 'yyyy-MM-dd'))
    try {
        $env:PYTHONIOENCODING = 'utf-8'
        [void](Start-Process $py.Source -ArgumentList "`"$s`"", 'demarrage' -WorkingDirectory (Split-Path (Split-Path $s -Parent) -Parent) -WindowStyle Hidden -RedirectStandardOutput $log -RedirectStandardError ($log + '.err') -PassThru)
        Write-Journal -Action 'Prospection' -Resultat 'agent lancé (demarrage : journée une fois par jour, puis écoute de « ok lot » / ✅)'; $true
    } catch { Write-Journal -Action 'Prospection' -Resultat "lancement impossible : $($_.Exception.Message)"; $false }
}
