# Exécute UNE tâche de l'agent de développement (lancé par Jarvis, processus séparé : la boucle principale n'est jamais bloquée pendant les 30 minutes d'une tâche).
#   powershell -NoProfile -ExecutionPolicy Bypass -File dev-agent.ps1 -Id <numéro de tâche>
# Charge seulement ce qu'il faut (journal, .env, config, business pour la lecture des variables, discord pour les modèles d'embeds, lib\dev-agent.ps1). Aucune voix, aucun micro, aucune fenêtre.
param([Parameter(Mandatory = $true)][int]$Id)
$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot
. (Join-Path $Root 'lib\journal.ps1')
Import-JarvisEnv
$Config = Import-ConfigJarvis
. (Join-Path $Root 'lib\business.ps1')
. (Join-Path $Root 'lib\discord.ps1')
. (Join-Path $Root 'lib\dev-agent.ps1')
$script:Secrets = @($script:Secrets)
$e = Get-DevEtat; $e.pid = $PID; Save-DevEtat $e
try {
    $r = Invoke-DevTache $Id
    Write-Journal -Ordre 'dev' -Action "Agent de dev : fin du processus (tâche $Id)" -Resultat $(if ($r.ok) { 'ok' } else { "arrêtée : $($r.raison)" })
} catch {
    Write-Journal -Ordre 'dev' -Action "Agent de dev : erreur (tâche $Id)" -Resultat (Hide-Secrets $_.Exception.Message)
    try { Set-DevTache $Id @{ statut = 'echec'; fin = (Get-Date).ToString('o'); raison = (Hide-Secrets $_.Exception.Message) }; Send-DevAlerte "tâche $Id : erreur inattendue ($(Hide-Secrets $_.Exception.Message))" } catch {}
} finally {
    try { $e = Get-DevEtat; if ([int]$e.pid -eq $PID) { $e.pid = 0; Save-DevEtat $e } } catch {}
}
