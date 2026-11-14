# Lanceur d'UN cycle d'un agent B2B sur le portable serveur (tâches planifiées « Jarvis-B2B-<agent> », créées par maj-auto.ps1 pour les agents actifs seulement).
#   powershell -File B2B\agents\serveur-b2b.ps1 -Agent devis [-Simulation]
# Garde-fous (6 Go de RAM, aucune écoute, aucun navigateur) :
#   1. machine : refuse si le nom de cette machine n'est pas « machine_active » de b2b.local.json (code 3, dit dans serveur-b2b.log) ;
#   2. agent connu de serveur-taches.json (code 6) ET listé dans agents_actifs de b2b.local.json (code 4) ;
#   3. UN SEUL agent à la fois : verrou global (mutex) ; si un autre agent tourne encore après -AttenteMax minutes, ce cycle est abandonné (code 5), il repassera au suivant ;
#   4. priorité « sous la normale » (BelowNormal, héritée par les sous-processus), profil serveur (JARVIS_B2B_SERVEUR=1 : aucun navigateur, aucune génération de maquettes) ;
#   5. des commandes COURTES, une par une (jamais « continu ») ; la première qui échoue arrête le cycle ; délai maximal par commande ; seul le processus lancé ici est arrêté (jamais d'arrêt global de processus : le navigateur de Liam, Ollama, le pont Discord ne sont pas touchés).
# Rien d'autre n'est lancé. -Simulation : dit ce qui serait lancé, ne lance rien. Aucun secret n'est lu ni affiché.
param([Parameter(Mandatory = $true)][string]$Agent, [switch]$Simulation, [string]$NomMachine = $env:COMPUTERNAME, [string]$NomMutex = 'JarvisB2BServeur', [double]$AttenteMax = 20, [string]$Python = '', [int]$DelaiMinutes = 35)
$ErrorActionPreference = 'Stop'
$AG = $PSScriptRoot; $B2B = Split-Path -Parent $AG
$journal = Join-Path $AG 'serveur-b2b.log'
function Log([string]$t) { try { Add-Content -LiteralPath $journal -Value ("{0:yyyy-MM-dd HH:mm:ss} | {1} | {2}" -f (Get-Date), $Agent, $t) -Encoding UTF8 } catch { }; Write-Host $t }

# 1) machine
$loc = $null; $fl = Join-Path $AG 'b2b.local.json'
if (Test-Path -LiteralPath $fl) { try { $loc = Get-Content -LiteralPath $fl -Raw -Encoding UTF8 | ConvertFrom-Json } catch { Log 'refusé : b2b.local.json illisible (machine_active inconnue)'; exit 3 } }
$active = $(if ($loc -and $loc.PSObject.Properties['machine_active']) { "$($loc.machine_active)".Trim() } else { '' })
if (-not $active) { Log 'refusé : machine_active absent de b2b.local.json : aucun agent ne tourne tant que la machine active n''est pas choisie'; exit 3 }
if ($active -ne $NomMachine.Trim()) { Log "refusé : cette machine est « $NomMachine », la machine active est « $active »"; exit 3 }
# 2) agent connu et actif
$table = $null; try { $table = (Get-Content -LiteralPath (Join-Path $AG 'serveur-taches.json') -Raw -Encoding UTF8 | ConvertFrom-Json).agents } catch { }
$t = $(if ($table) { $table.PSObject.Properties[$Agent] } else { $null })
if (-not $t) { Log "agent inconnu : « $Agent » (serveur-taches.json)"; exit 6 }
$actifs = @($(if ($loc.PSObject.Properties['agents_actifs']) { $loc.agents_actifs })) | ForEach-Object { "$_" }
if ($Agent -notin $actifs) { Log "agent « $Agent » non marqué actif dans agents_actifs (b2b.local.json) : rien lancé"; exit 4 }
$script = Join-Path $AG $t.Value.script
$commandes = @($t.Value.commandes | ForEach-Object { , @($_) })
# 3) python
$py = $Python
if (-not $py) { $c = @(Get-Command python -All -ErrorAction SilentlyContinue | Where-Object { $_.CommandType -eq 'Application' -and $_.Source -notmatch '(?i)[\\/]WindowsApps[\\/]' }) | Select-Object -First 1; if ($c) { $py = $c.Source } elseif ($Simulation) { $py = 'python' } }
if (-not $py) { Log 'python introuvable (ni dans le PATH, ni hors WindowsApps) : rien lancé'; exit 7 }
if ($Simulation) {
    foreach ($c in $commandes) { Write-Host ("SIMULATION : python {0} {1}" -f (Split-Path $script -Leaf), ($c -join ' ')).TrimEnd() }
    Write-Host 'priorité : BelowNormal ; JARVIS_B2B_SERVEUR=1 (aucun navigateur) ; un seul agent à la fois (verrou global)'; exit 0
}
# 4) un seul agent à la fois
$mx = New-Object System.Threading.Mutex($false, "Global\$NomMutex"); $pris = $false
try {
    try { $pris = $mx.WaitOne([TimeSpan]::FromMinutes($AttenteMax)) } catch [System.Threading.AbandonedMutexException] { $pris = $true }
    if (-not $pris) { Log 'occupé : un autre agent B2B tourne encore, ce cycle est abandonné (il repassera au prochain)'; exit 5 }
    Log "début du cycle ($($commandes.Count) commande(s))"
    foreach ($c in $commandes) {
        $args2 = ('"{0}" {1}' -f $script, ($c -join ' ')).TrimEnd()
        $psi = New-Object System.Diagnostics.ProcessStartInfo; $psi.FileName = $py; $psi.Arguments = $args2; $psi.UseShellExecute = $false; $psi.CreateNoWindow = $true; $psi.WorkingDirectory = $B2B
        $psi.EnvironmentVariables['JARVIS_B2B_SERVEUR'] = '1'; $psi.EnvironmentVariables['PYTHONIOENCODING'] = 'utf-8'; $psi.EnvironmentVariables['PYTHONDONTWRITEBYTECODE'] = '1'
        $p = [System.Diagnostics.Process]::Start($psi)
        try { $p.PriorityClass = [System.Diagnostics.ProcessPriorityClass]::BelowNormal; Log "$(Split-Path $script -Leaf) $($c -join ' ') : priorité BelowNormal appliquée (pid $($p.Id))" } catch { Log "priorité non appliquée : $($_.Exception.Message)" }
        if (-not $p.WaitForExit($DelaiMinutes * 60000)) { try { $p.Kill() } catch { }; Log "échec : $(Split-Path $script -Leaf) $($c -join ' ') arrêté (délai de $DelaiMinutes min dépassé)"; exit 1 }
        if ($p.ExitCode -ne 0) { Log "échec : $(Split-Path $script -Leaf) $($c -join ' ') a rendu le code $($p.ExitCode) : cycle arrêté"; exit 1 }
    }
    Log 'terminé'
} finally { if ($pris) { try { $mx.ReleaseMutex() } catch { } }; $mx.Dispose() }
exit 0
