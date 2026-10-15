# MESURE du vrai routeur local (Ollama déjà démarré, modèle de config.json) sur le corpus de 60 phrases : taux de réussite par catégorie et temps de réponse.
# N'EXÉCUTE AUCUNE action (on regarde seulement les actions choisies), n'ouvre rien, ne parle pas. N'est PAS dans tout.ps1 : à lancer à la main, à la demande.
# Ne démarre PAS Ollama (s'il ne répond pas, la mesure est ignorée) ; décharge le modèle de la VRAM à la fin.
param([string]$Modele = '')      # comparer un modèle plus léger : -Modele qwen2.5:3b (ou 1.5b). À adopter SEULEMENT si la précision reste >= 90 % et au moins égale au modèle actuel (voir README, « Vitesse V3 »).
$ErrorActionPreference = 'Stop'
$env:JARVIS_TEST = '1'
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $Root 'lib\journal.ps1')
$TR = Join-Path $env:TEMP ('jarvis-test-' + [guid]::NewGuid().ToString('N').Substring(0, 8)); New-Item -ItemType Directory $TR, "$TR\memoire", "$TR\logs", "$TR\projets" | Out-Null; $script:JarvisRoot = $TR
"# To-do de Liam`r`n- [ ] Envoyer la facture`r`n- [ ] Appeler le comptable" | Set-Content "$TR\memoire\todo.md" -Encoding UTF8
Copy-Item (Join-Path $Root 'memoire\profil.md') "$TR\memoire\profil.md"
$cfg = Join-Path $env:TEMP ('jarvis-config-test-' + [guid]::NewGuid().ToString('N') + '.json'); Copy-Item (Join-Path $Root 'config.json') $cfg; $env:JARVIS_CONFIG = $cfg
$Config = Get-Content (Get-ConfigPath) -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($l in 'voix', 'business', 'permissions', 'actions', 'coffre', 'entrees', 'ecrans', 'tableau', 'visage', 'sons', 'raccourcis', 'cerveau', 'cerveau-local', 'veille', 'memoire', 'rapide', 'discretion', 'modejeu', 'marche', 'priorite', 'comprehension', 'routeur', 'competences', 'pc', 'bureau', 'matin', 'boucle') { . (Join-Path $Root "lib\$l.ps1") }
$script:JarvisRoot = $TR
[void](Import-Competences (Join-Path $Root 'lib\competences'))
$script:StartAppsCache = @('Discord', 'Steam', 'Google Chrome', 'Visual Studio Code', 'Spotify', 'Microsoft Edge') | ForEach-Object { [pscustomobject]@{ Name = $_; AppID = "id.$_" } }
. (Join-Path $PSScriptRoot 'corpus-routeur.ps1')
$script:OllamaTestAutorise = $true; $script:OllamaCache = $null
$c = Get-OllamaConfig
if ($Modele -match '^[A-Za-z0-9._:/-]{2,60}$') { $c.modele = $Modele; $Config.ollama.modele = $Modele; $script:OllamaCache = $null; Write-Host "Modèle comparé : $Modele (config.json n'est pas modifiée)" }
try { $ps = Invoke-RestMethod -Uri "$($c.url)/api/tags" -TimeoutSec 3; $ok = [bool]($ps.models | Where-Object { $_.name -like "$($c.modele)*" }) } catch { $ok = $false }
if (-not $ok) { Write-Host "Ollama ne répond pas ou le modèle $($c.modele) est absent : mesure ignorée (rien n'a été démarré)."; foreach ($x in $TR, $cfg) { Remove-Item $x -Recurse -Force -ErrorAction SilentlyContinue }; exit 0 }
function Get-ModeCerveau { 'local' }
$stats = [ordered]@{}; $temps = @(); $premier = $null; $lignes = @()
foreach ($e in $corpus) {
    $rapide = Get-PlanRapide $e.p
    if ($rapide -and $rapide.repli_routeur) { $rapide = $null }
    if ($rapide) { $obtenu = if ($rapide.actions.Count) { ($rapide.actions | ForEach-Object { $_.type }) -join '+' } else { 'dit' }; $via = 'règle' }
    else {
        $t0 = Get-Date; $plan = Resolve-Routeur $e.p; $ms = [int]((Get-Date) - $t0).TotalMilliseconds
        if ($null -eq $premier) { $premier = $ms } else { $temps += $ms }
        $obtenu = if ($plan) { ($plan.actions | ForEach-Object { $_.type }) -join '+' } else { 'claude' }; $via = "routeur $ms ms ($($script:RouteurEtat)) : $(("$($script:RouteurDernier.brut)" -replace '\s+', ' ').Substring(0, [math]::Min(230, "$($script:RouteurDernier.brut)".Length)))"
    }
    $att = $e.att; if ($att -eq 'aucune') { $att = 'pc_eteindre' }
    $ok2 = ($obtenu -eq $att) -or ($e.ContainsKey('ok2') -and $obtenu -eq $e.ok2)      # ok2 : réponse sûre aussi acceptable (valeur bornée à 100 ; l'action refuse elle-même un dossier hors liste)
    if (-not $stats.Contains($e.c)) { $stats[$e.c] = @(0, 0) }; $stats[$e.c][1]++; if ($ok2) { $stats[$e.c][0]++ }
    if (-not $ok2) { $lignes += "  ✗ [$($e.c)] « $($e.p) » attendu $att, obtenu $obtenu — $via" }
}
Write-Host "Modèle : $($c.modele) — premier appel (modèle à charger) : $premier ms"
if ($temps.Count) { $tr = $temps | Sort-Object; Write-Host ("Routeur, modèle chargé : médiane {0} ms, moyenne {1} ms, pire {2} ms ({3} appels)" -f $tr[[int]($tr.Count / 2)], [int]($tr | Measure-Object -Average).Average, $tr[-1], $tr.Count) }
$tot = 0; $ok3 = 0; foreach ($k in $stats.Keys) { Write-Host ("  {0,-22} {1}/{2}" -f $k, $stats[$k][0], $stats[$k][1]); $tot += $stats[$k][1]; $ok3 += $stats[$k][0] }
Write-Host ("  {0,-22} {1}/{2} ({3:N0} %)" -f 'TOTAL', $ok3, $tot, (100 * $ok3 / $tot))
$lignes | ForEach-Object { Write-Host $_ }
try { Invoke-RestMethod -Uri "$($c.url)/api/generate" -Method Post -Body (@{ model = $c.modele; keep_alive = 0 } | ConvertTo-Json -Compress) -ContentType 'application/json' -TimeoutSec 20 | Out-Null } catch { }
foreach ($x in $TR, $cfg) { Remove-Item $x -Recurse -Force -ErrorAction SilentlyContinue }
