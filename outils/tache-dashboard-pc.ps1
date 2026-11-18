# Tâche planifiée du TABLEAU DE BORD sur le gros PC (18/11/2026) : outils\agents-json.py toutes les 15 min et à l'ouverture de session, sans fenêtre (pythonw), priorité basse.
# Gratuit (Planificateur de tâches Windows), lecture seule (comptes seulement), ne lance pas Jarvis. Le mécanisme de données ne change pas : c'est le même script que l'icône du bureau.
#   powershell -ExecutionPolicy Bypass -File outils\tache-dashboard-pc.ps1            -> montre ce qui serait fait
#   powershell -ExecutionPolicy Bypass -File outils\tache-dashboard-pc.ps1 -Oui       -> crée (ou met à jour) la tâche Jarvis-Tableau-PC
#   powershell -ExecutionPolicy Bypass -File outils\tache-dashboard-pc.ps1 -Retirer   -> supprime la tâche
param([switch]$Oui, [switch]$Retirer)
$nom = 'Jarvis-Tableau-PC'
if ($Retirer) { Unregister-ScheduledTask -TaskName $nom -Confirm:$false -ErrorAction SilentlyContinue; Write-Host "$nom retirée."; exit 0 }
$racine = Split-Path -Parent $PSScriptRoot
$pyw = (Get-Command pythonw -ErrorAction Stop).Source
$moi = "$env:USERDOMAIN\$env:USERNAME"
$arg = '"' + (Join-Path $racine 'outils\agents-json.py') + '"'
Write-Host "$nom : $pyw $arg (à l'ouverture de session, puis toutes les 15 min)"
if (-not $Oui) { Write-Host 'Rien n''a été créé (ajouter -Oui).'; exit 0 }
$a = New-ScheduledTaskAction -Execute $pyw -Argument $arg -WorkingDirectory $racine
$d = @((New-ScheduledTaskTrigger -AtLogOn -User $moi), (New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 15)))
$s = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -Priority 7 -ExecutionTimeLimit (New-TimeSpan -Minutes 10)
$p = New-ScheduledTaskPrincipal -UserId $moi -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $nom -Action $a -Trigger $d -Settings $s -Principal $p -Description 'Tableau de bord Jarvis : recalcule dashboard\ventes.json et data\historique.json (lecture seule, sans fenêtre).' -Force | Out-Null
Write-Host "  créée."
