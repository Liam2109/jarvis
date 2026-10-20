# Un passage de la veille « annonces-train » (lancé par Jarvis, processus séparé : la boucle principale n'attend jamais le réseau).
#   powershell -NoProfile -ExecutionPolicy Bypass -File veille-train.ps1
# Charge seulement ce qu'il faut (journal, .env, config, business pour Get-EnvPropre, discord pour les modèles d'embeds, lib\veille-train.ps1). Aucune voix, aucun micro, aucune fenêtre. Lecture seule : aucune candidature.
$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot
. (Join-Path $Root 'lib\journal.ps1')
Import-JarvisEnv
$Config = Import-ConfigJarvis
. (Join-Path $Root 'lib\business.ps1')
. (Join-Path $Root 'lib\discord.ps1')
. (Join-Path $Root 'lib\veille-train.ps1')
$script:Secrets = @($script:Secrets)
try { [void](Invoke-VeilleTrain) } catch {
    Write-Journal -Action 'Veille annonces-train : erreur' -Resultat (Hide-Secrets $_.Exception.Message)
    try { $e = Get-TrainEtat; $e.pid = 0; Save-TrainEtat $e } catch {}
}
