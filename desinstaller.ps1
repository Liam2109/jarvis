# Retire la tâche planifiée "Jarvis". Les fichiers, le journal et la mémoire ne sont PAS touchés.
$ErrorActionPreference = 'Stop'
if (Get-ScheduledTask -TaskName 'Jarvis' -ErrorAction SilentlyContinue) {
    Stop-ScheduledTask -TaskName 'Jarvis' -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName 'Jarvis' -Confirm:$false
    . (Join-Path $PSScriptRoot 'lib\journal.ps1')
    Write-Journal -Action 'Désinstallation du démarrage automatique' -Resultat 'tâche planifiée "Jarvis" supprimée'
    Write-Host 'Tâche "Jarvis" supprimée. Vos fichiers et votre journal sont intacts.'
} else { Write-Host 'Aucune tâche "Jarvis" à supprimer.' }
