# Tâches du TABLEAU DE BORD à créer sur le SERVEUR (DESKTOP-HLQSTAU). Par défaut : AFFICHE seulement les commandes, ne crée rien.
#   powershell -ExecutionPolicy Bypass -File outils\taches-dashboard-serveur.ps1        -> montre ce qui serait fait
#   powershell -ExecutionPolicy Bypass -File outils\taches-dashboard-serveur.ps1 -Oui   -> crée les deux tâches (à lancer par Liam, sur le serveur)
# 1) Jarvis-Tableau-de-bord : outils\agents-json.py toutes les 5 min (sans fenêtre, comptes seulement).
# 2) Jarvis-Tableau-Service : outils\servir-dashboard.py à l'ouverture de session (port 8080, lecture seule, dossier dashboard\ seulement).
# Pour y accéder depuis le gros PC : autoriser le port 8080 en RÉSEAU PRIVÉ (administrateur, à faire par Liam) :
#   New-NetFirewallRule -DisplayName 'Jarvis tableau de bord 8080' -Direction Inbound -Protocol TCP -LocalPort 8080 -Profile Private -Action Allow
param([switch]$Oui)
$racine = Split-Path -Parent $PSScriptRoot
$pyw = (Get-Command pythonw -ErrorAction Stop).Source
$moi = "$env:USERDOMAIN\$env:USERNAME"
$taches = @(
    @{ Nom = 'Jarvis-Tableau-de-bord'; Script = 'outils\agents-json.py'; Declencheur = { New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 5) } },
    @{ Nom = 'Jarvis-Tableau-Service'; Script = 'outils\servir-dashboard.py'; Declencheur = { New-ScheduledTaskTrigger -AtLogOn -User $moi } }
)
foreach ($t in $taches) {
    $arg = '"' + (Join-Path $racine $t.Script) + '"'
    Write-Host "$($t.Nom) : $pyw $arg"
    if (-not $Oui) { continue }
    $a = New-ScheduledTaskAction -Execute $pyw -Argument $arg -WorkingDirectory $racine
    $s = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -Priority 7 -ExecutionTimeLimit ([TimeSpan]::Zero)
    $p = New-ScheduledTaskPrincipal -UserId $moi -LogonType Interactive -RunLevel Limited
    Register-ScheduledTask -TaskName $t.Nom -Action $a -Trigger (& $t.Declencheur) -Settings $s -Principal $p -Force | Out-Null
    Write-Host "  créée."
}
if (-not $Oui) { Write-Host 'Rien n''a été créé (ajouter -Oui sur le serveur pour créer les tâches).' }