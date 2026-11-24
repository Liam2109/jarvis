# Tâche planifiée « Jarvis-MajGrosPC » (24/11/2026) : outils\maj-gros-pc.py toutes les 10 min et à l'ouverture de session, sans fenêtre (pythonw), priorité basse.
# Le script fait « git pull --ff-only origin main » seulement si le dossier est propre et si aucun Claude Code n'y travaille ; sinon il saute le tour (jamais de stash, reset ni force).
# Ne lance pas Jarvis. Trace : logs\maj-gros-pc.log.
#   powershell -ExecutionPolicy Bypass -File outils\tache-maj-gros-pc.ps1            -> montre ce qui serait fait
#   powershell -ExecutionPolicy Bypass -File outils\tache-maj-gros-pc.ps1 -Oui       -> crée (ou met à jour) la tâche
#   powershell -ExecutionPolicy Bypass -File outils\tache-maj-gros-pc.ps1 -Retirer   -> supprime la tâche
param([switch]$Oui, [switch]$Retirer)
$nom = 'Jarvis-MajGrosPC'
if ($Retirer) { Unregister-ScheduledTask -TaskName $nom -Confirm:$false -ErrorAction SilentlyContinue; Write-Host "$nom retirée."; exit 0 }
$racine = Split-Path -Parent $PSScriptRoot
$pyw = (Get-Command pythonw -ErrorAction Stop).Source
$moi = "$env:USERDOMAIN\$env:USERNAME"
$arg = '"' + (Join-Path $racine 'outils\maj-gros-pc.py') + '"'
Write-Host "$nom : $pyw $arg (à l'ouverture de session, puis toutes les 10 min)"
if (-not $Oui) { Write-Host 'Rien n''a été créé (ajouter -Oui).'; exit 0 }
$a = New-ScheduledTaskAction -Execute $pyw -Argument $arg -WorkingDirectory $racine
$d = @((New-ScheduledTaskTrigger -AtLogOn -User $moi), (New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(2) -RepetitionInterval (New-TimeSpan -Minutes 10)))
$s = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -Priority 7 -ExecutionTimeLimit (New-TimeSpan -Minutes 10)
$p = New-ScheduledTaskPrincipal -UserId $moi -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $nom -Action $a -Trigger $d -Settings $s -Principal $p -Description 'Gros PC : git pull --ff-only origin main si le dossier est propre et sans Claude Code actif (sans fenêtre, rien forcé).' -Force | Out-Null
Write-Host "  créée."
