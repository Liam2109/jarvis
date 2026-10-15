# Test SILENCIEUX de la fin de phrase : réglages config.json (silence_fin_ms, silence_commande_ms, duree_max_phrase_s), arguments passés à l'écoute, et
# simulation du moteur (tests\silence.py : blocs de 0,1 s simulés, aucun micro, aucun son, aucun modèle). Code de sortie 0 = réussi.
$ErrorActionPreference = 'Stop'
$env:JARVIS_TEST = '1'
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $Root 'lib\journal.ps1')
$TR = Join-Path $env:TEMP ('jarvis-test-' + [guid]::NewGuid().ToString('N').Substring(0, 8)); New-Item -ItemType Directory $TR, "$TR\memoire", "$TR\logs" | Out-Null; $script:JarvisRoot = $TR
$Config = Get-Content (Get-ConfigPath) -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($l in 'voix', 'business', 'permissions', 'actions', 'coffre', 'entrees', 'ecrans', 'tableau', 'visage', 'sons', 'raccourcis', 'cerveau', 'cerveau-local', 'veille', 'memoire', 'rapide', 'discretion', 'modejeu', 'marche', 'priorite', 'comprehension', 'boucle') { . (Join-Path $Root "lib\$l.ps1") }
$script:JarvisRoot = $TR
$echecs = 0
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }
function Fixer([string]$cle, $val) { if ($Config.PSObject.Properties[$cle]) { $Config.$cle = $val } else { $Config | Add-Member -NotePropertyName $cle -NotePropertyValue $val } }
function Effacer([string]$cle) { if ($Config.PSObject.Properties[$cle]) { $Config.PSObject.Properties.Remove($cle) } }

Write-Host '1) Valeurs choisies dans config.json'
$vraie = Get-Content (Join-Path $Root 'config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
Verifier ($vraie.silence_fin_ms -eq 1500 -and $vraie.silence_commande_ms -eq 600 -and $vraie.duree_max_phrase_s -eq 30) 'config.json : silence_fin_ms = 1500, silence_commande_ms = 600, duree_max_phrase_s = 30'
Verifier (-not $vraie.PSObject.Properties['silence_fin_secondes']) 'l''ancien réglage silence_fin_secondes (0,5 s, cause des coupures) a disparu'

Write-Host '2) Lecture et bornes'
$mc = Get-MicroConfig; Verifier ($mc.silence -eq 1.5 -and $mc.silence_courte -eq 0.6 -and $mc.duree_max -eq 30) 'valeurs de config.json : 1,5 s / 0,6 s / 30 s'
foreach ($c in 'silence_fin_ms', 'silence_commande_ms', 'duree_max_phrase_s') { Effacer $c }
$mc = Get-MicroConfig; Verifier ($mc.silence -eq 1.5 -and $mc.silence_courte -eq 0.6 -and $mc.duree_max -eq 30) 'sans réglage : mêmes valeurs par défaut'
Fixer 'silence_fin_secondes' 0.5; $mc = Get-MicroConfig; Verifier ($mc.silence -eq 1.5) 'l''ancien réglage de 0,5 s est ignoré'; Effacer 'silence_fin_secondes'
Fixer 'silence_fin_ms' 2000; Fixer 'silence_commande_ms' 400; Fixer 'duree_max_phrase_s' 20; $mc = Get-MicroConfig
Verifier ($mc.silence -eq 2.0 -and $mc.silence_courte -eq 0.4 -and $mc.duree_max -eq 20) 'valeurs personnalisées : 2,0 s / 0,4 s / 20 s'
Fixer 'silence_fin_ms' 10; $mc = Get-MicroConfig; Verifier ($mc.silence -eq 0.3) 'plancher du silence long : 300 ms'
Fixer 'silence_fin_ms' 99999; $mc = Get-MicroConfig; Verifier ($mc.silence -eq 4.0) 'plafond du silence long : 4000 ms'
Fixer 'silence_fin_ms' 800; Fixer 'silence_commande_ms' 1400; $mc = Get-MicroConfig; Verifier ($mc.silence_courte -eq 0.8) 'le silence court ne dépasse jamais le silence long'
Fixer 'duree_max_phrase_s' 1; $mc = Get-MicroConfig; Verifier ($mc.duree_max -eq 5) 'durée maximale : 5 s au plus bas'
Fixer 'duree_max_phrase_s' 500; $mc = Get-MicroConfig; Verifier ($mc.duree_max -eq 60) 'durée maximale : 60 s au plus haut'
Fixer 'silence_fin_ms' 'abc'; $mc = Get-MicroConfig; Verifier ($mc.silence -eq 1.5) 'valeur illisible : défaut'
foreach ($c in 'silence_fin_ms', 'silence_commande_ms', 'duree_max_phrase_s') { Fixer $c $vraie.$c }

Write-Host '3) Arguments passés au processus d''écoute'
$a = Get-ArgsEcoute 'ecoute.py'
Verifier ($a -match '--silence-fin 1\.5 --silence-courte 0\.6 --duree-max 30') 'écoute lancée avec --silence-fin 1.5 --silence-courte 0.6 --duree-max 30'
Fixer 'silence_fin_ms' 2500; Fixer 'duree_max_phrase_s' 45; $a = Get-ArgsEcoute 'ecoute.py'; Verifier ($a -match '--silence-fin 2\.5 ' -and $a -match '--duree-max 45') 'réglages personnalisés transmis'
Fixer 'silence_fin_ms' 1500; Fixer 'duree_max_phrase_s' 30
$src = Get-Content (Join-Path $Root 'lib\entrees.ps1') -Raw -Encoding UTF8; Verifier ($src -match 'silence = 1\.5; silence_courte = 0\.6; duree_max = 30') 'valeurs de repli de Get-ArgsEcoute alignées'

Write-Host '4) Simulation du moteur (blocs de 0,1 s)'
$env:PYTHONIOENCODING = 'utf-8'
$sortie = & python -I (Join-Path $PSScriptRoot 'silence.py') 2>&1 | Out-String; $code = $LASTEXITCODE
foreach ($l in ($sortie -split "`r?`n")) { if ($l -match '^\s+(OK|ECHEC) ') { if ($l -match '^\s+OK ') { Write-Host $l } else { Write-Host $l -ForegroundColor Red; $script:echecs++ } } }
Verifier ($code -eq 0) 'tests\silence.py : code 0'

Remove-Item $TR -Recurse -Force -ErrorAction SilentlyContinue
if ($echecs) { Write-Host "`n$echecs échec(s)." -ForegroundColor Red; exit 1 }
Write-Host "`nTOUT EST VERT." -ForegroundColor Green; exit 0
