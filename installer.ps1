# OPTION « démarrage avec Windows » : tâche planifiée "Jarvis", lancement à l'ouverture de session, après 20 s.
#   powershell -ExecutionPolicy Bypass -File installer.ps1 -DemarrageWindows
# Jarvis démarre alors EN SOURDINE (config.json "etat_au_demarrage": "sourdine" : muet, sourd, sans son), le briefing du matin s'affiche au tableau SANS voix,
# la veille de fond ne se lance que si "marche_actif" est true. Rien ne parle avant votre Alt + +.
# Sans l'option -DemarrageWindows, ce script n'installe RIEN (il explique seulement). Annulable avec desinstaller.ps1. Aucun droit administrateur requis.
# (Ne l'exécutez que lorsque vous jugez Jarvis stable : il n'est jamais lancé automatiquement par Claude.)
param([switch]$DemarrageWindows)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
if (-not $DemarrageWindows) {
    Write-Host 'Rien installé. Pour que Jarvis démarre avec Windows (en sourdine, briefing affiché sans voix) : installer.ps1 -DemarrageWindows'
    Write-Host 'Pour annuler plus tard : desinstaller.ps1'
    return
}
if ("$((Get-Content (Join-Path $root 'config.json') -Raw -Encoding UTF8 | ConvertFrom-Json).etat_au_demarrage)" -ne 'sourdine') {
    Write-Host 'ATTENTION : config.json "etat_au_demarrage" n''est pas "sourdine" : Jarvis parlerait dès l''ouverture de session. Mettez "sourdine" avant d''installer.'
    return
}
$user = "$env:USERDOMAIN\$env:USERNAME"
$action = New-ScheduledTaskAction -Execute 'powershell.exe' `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$root\jarvis.ps1`"" -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $user
$trigger.Delay = 'PT20S'
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) -StartWhenAvailable
$principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName 'Jarvis' -Action $action -Trigger $trigger -Settings $settings -Principal $principal `
    -Description 'Assistant personnel Jarvis (démarrage à la connexion)' -Force | Out-Null
. (Join-Path $root 'lib\journal.ps1')
Write-Journal -Action 'Installation du démarrage automatique' -Resultat 'tâche planifiée "Jarvis" créée'
Write-Host 'Tâche "Jarvis" installée : Jarvis démarrera 20 s après votre ouverture de session.'
