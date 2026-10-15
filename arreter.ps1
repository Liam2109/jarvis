# Arrête Jarvis proprement : demande l'arrêt (memoire\quitter.flag), attend jusqu'à 75 s (le temps de résumer la session), puis ne force QUE le processus Jarvis
# enregistré dans memoire\jarvis.pid, son écoute vocale et son Edge. Rien d'autre n'est touché.
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
. (Join-Path $root 'lib\journal.ps1')
$pidFile = Join-Path $root 'memoire\jarvis.pid'
function Stop-VeilleFondAr {
    # La veille de fond (processus léger séparé) s'arrête aussi : seul le processus enregistré dans memoire\veille-fond.pid est touché.
    $vf = Join-Path $root 'memoire\veille-fond.pid'
    if (Test-Path $vf) {
        try { $vp = [int](Get-Content $vf -Raw).Trim(); $c = Get-CimInstance Win32_Process -Filter "ProcessId=$vp" -ErrorAction SilentlyContinue; if ($c -and $c.CommandLine -match 'veille-fond\.ps1') { Stop-Process -Id $vp -Force -ErrorAction SilentlyContinue; Write-Journal -Action 'Veille de fond arrêtée' -Resultat "PID $vp (arreter.ps1)" } } catch {}
        Remove-Item $vf -Force -ErrorAction SilentlyContinue
    }
    Remove-Item (Join-Path $root 'memoire\modejeu.flag'), (Join-Path $root 'memoire\discord-pont.pid') -Force -ErrorAction SilentlyContinue
    Stop-RestesJarvis
}
function Stop-RestesJarvis {
    # Filet de sécurité (appelé sur tous les chemins) : écoute vocale (voix\ecoute.py), pont Discord (pont-discord\pont.py), Edge de l'orbe (profil %TEMP%\jarvis-edge) et service Ollama.
    $edgeProfil = Join-Path $env:TEMP 'jarvis-edge'
    foreach ($pr in @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue)) {
        $cl = "$($pr.CommandLine)"; $quoi = $null
        if ($pr.Name -match '^python' -and $cl -match 'voix\\ecoute\.py') { $quoi = 'écoute' }
        elseif ($pr.Name -match '^python' -and $cl -match 'pont-discord\\pont\.py') { $quoi = 'pont Discord' }
        elseif ($pr.Name -match '^python' -and $cl -match 'voix\\reveil\.py') { $quoi = 'écoute de veille' }
        elseif ($pr.Name -eq 'msedge.exe' -and $cl.IndexOf($edgeProfil, [StringComparison]::OrdinalIgnoreCase) -ge 0) { $quoi = 'orbe (Edge)' }
        elseif ($pr.Name -eq 'ollama.exe' -and $cl -match 'serve') { $quoi = 'Ollama' }
        elseif ($pr.Name -match '^(llama-server|ollama_llama_server)\.exe$') { $quoi = 'Ollama (modèle)' }
        if ($quoi) { Stop-Process -Id ([int]$pr.ProcessId) -Force -ErrorAction SilentlyContinue; Write-Journal -Action 'Reste de Jarvis arrêté' -Resultat "$quoi PID $($pr.ProcessId) (arreter.ps1)" }
    }
}
if (-not (Test-Path $pidFile)) { Stop-VeilleFondAr; Write-Host 'Jarvis ne semble pas tourner (aucun memoire\jarvis.pid).'; return }
$o = Get-Content $pidFile -Raw -Encoding UTF8 | ConvertFrom-Json
$p = Get-CimInstance Win32_Process -Filter "ProcessId=$([int]$o.pid)" -ErrorAction SilentlyContinue
if (-not $p -or $p.CommandLine -notmatch 'jarvis\.ps1') { Stop-VeilleFondAr; Remove-Item $pidFile -Force; Write-Host 'Jarvis ne tourne plus (fichier PID périmé supprimé).'; return }
Set-Content (Join-Path $root 'memoire\quitter.flag') '1' -Encoding ASCII
Write-Host "Arrêt demandé à Jarvis (PID $($o.pid))..."
$fin = (Get-Date).AddSeconds(75)       # Jarvis résume la session (appel au cerveau) avant de s'arrêter
while ((Get-Date) -lt $fin -and (Get-Process -Id ([int]$o.pid) -ErrorAction SilentlyContinue)) { Start-Sleep -Milliseconds 300 }
if (Get-Process -Id ([int]$o.pid) -ErrorAction SilentlyContinue) {
    Write-Host 'Pas de réponse : arrêt forcé du processus Jarvis et de ses enfants.'
    $tous = @(Get-CimInstance Win32_Process | Select-Object ProcessId, ParentProcessId)
    $arbre = New-Object System.Collections.Generic.List[int]; $arbre.Add([int]$o.pid)
    for ($i = 0; $i -lt $arbre.Count; $i++) { foreach ($x in $tous) { if ($x.ParentProcessId -eq $arbre[$i] -and -not $arbre.Contains([int]$x.ProcessId)) { $arbre.Add([int]$x.ProcessId) } } }
    if ($o.edge) { $arbre.Add([int]$o.edge) }
    foreach ($id in $arbre) { Stop-Process -Id $id -Force -ErrorAction SilentlyContinue }
    Write-Journal -Action 'Arrêt forcé de Jarvis' -Resultat "processus $($arbre -join ', ')"
}
Stop-VeilleFondAr
Remove-Item $pidFile, (Join-Path $root 'memoire\quitter.flag'), (Join-Path $root 'memoire\modejeu.flag') -Force -ErrorAction SilentlyContinue
Write-Host 'Jarvis est arrêté.'
