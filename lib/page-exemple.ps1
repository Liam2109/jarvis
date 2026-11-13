# Agent « page exemple » (B2B\agents\page-exemple.py) : lancé UNE fois par session (commande « continu --pid <Jarvis> »), dans un processus caché SÉPARÉ qui boucle (un passage toutes les cycle_minutes) et s'arrête si Jarvis s'arrête.
# Sur Discord (salon_nom, « pages » par défaut), Liam écrit « métier, ville, nom » (ex. « plombier, Yvetot, Dupont Plomberie ») : l'agent choisit le modèle déjà validé du métier, relit les règles de style, remplace le nom, la
# ville et les textes (sans répéter les mêmes phrases d'une page à l'autre), déploie la page sur b2b-demos (Vercel, noindex), répond SEULEMENT avec le lien, et ajoute une ligne au suivi (B2B\pages-exemple\suivi.csv).
# Aucune question posée à Liam : une information manquante reçoit l'hypothèse la plus raisonnable, dite dans la réponse. Un métier non reconnu ne crée rien (l'agent le dit).
# Secours : python B2B\agents\page-exemple.py arreter. Jarvis n'en dépend pas : le script est autonome. Désactivé tant que page_exemple_actif n'est pas « oui » dans config.json (ou config.local.json).
function Get-PageExempleConfig {
    $oui = @('oui', 'true', '1', 'on', 'yes'); $c = @{ actif = $false; delai = 90 }
    if ($Config.PSObject.Properties['page_exemple_actif'] -and "$($Config.page_exemple_actif)".Trim().ToLower() -in $oui) { $c.actif = $true }
    $c
}

function Update-PageExemple([datetime]$now = (Get-Date)) {
    # Ne fait RIEN si page_exemple_actif n'est pas "oui". Un seul lancement par session de Jarvis, 90 s après le démarrage ; jamais en mode jeu.
    $c = Get-PageExempleConfig; if (-not $c.actif) { return $false }
    if ($script:PageExempleLance) { return $false }
    if (-not $script:PageExempleDebut) { $script:PageExempleDebut = $now }
    if (($now - $script:PageExempleDebut).TotalSeconds -lt $c.delai) { return $false }
    if ($script:ModeJeu -eq $true) { return $false }
    $script:PageExempleLance = $true
    if (Test-ModeTest) { $script:PageExempleRunnerLance = $true; return $true }      # tests : jamais de vrai processus
    $s = Join-Path $script:RacineReelle 'B2B\agents\page-exemple.py'; $py = Get-Command python -ErrorAction SilentlyContinue
    if (-not (Test-Path $s) -or -not $py) { Write-Journal -Action 'Page exemple' -Resultat 'non lancé (B2B\agents\page-exemple.py ou python introuvable)'; return $false }
    $log = Join-Path $script:RacineReelle ('logs\page-exemple-{0}.log' -f (Get-Date -Format 'yyyy-MM-dd'))
    try {
        $env:PYTHONIOENCODING = 'utf-8'
        [void](Start-Process $py.Source -ArgumentList "`"$s`"", 'continu', '--pid', "$PID" -WorkingDirectory (Split-Path (Split-Path $s -Parent) -Parent) -WindowStyle Hidden -RedirectStandardOutput $log -RedirectStandardError ($log + '.err') -PassThru)
        Write-Journal -Action 'Page exemple' -Resultat 'agent lancé (continu : lit « métier, ville, nom » sur Discord, écrit et déploie la page sur b2b-demos (noindex), répond avec le seul lien, ajoute une ligne au suivi ; arrêt immédiat et alerte sur toute erreur)'; $true
    } catch { Write-Journal -Action 'Page exemple' -Resultat "lancement impossible : $($_.Exception.Message)"; $false }
}
