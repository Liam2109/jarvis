# Test des compétences personnelles (lib\competences\*.ps1). Code de sortie 0 = réussi.
$ErrorActionPreference = 'Stop'
$env:JARVIS_TEST = '1'      # TEST SILENCIEUX : aucun son, aucune fenêtre, aucun micro, aucune touche, aucune action réelle (voir lib\journal.ps1)
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $Root 'lib\journal.ps1')
$TR = Join-Path $env:TEMP ('jarvis-test-' + [guid]::NewGuid().ToString('N').Substring(0, 8)); New-Item -ItemType Directory $TR, "$TR\memoire", "$TR\logs" | Out-Null; $script:JarvisRoot = $TR
$Config = Get-Content (Get-ConfigPath) -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($l in 'voix', 'business', 'permissions', 'actions', 'coffre', 'entrees', 'ecrans', 'tableau', 'visage', 'sons', 'raccourcis', 'cerveau', 'cerveau-local', 'veille', 'memoire', 'rapide', 'discretion', 'modejeu', 'competences') { . (Join-Path $Root "lib\$l.ps1") }
$script:JarvisRoot = $TR
$echecs = 0
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }
try {
    $d = Join-Path $TR 'competences'; New-Item -ItemType Directory $d | Out-Null
    Copy-Item (Join-Path $Root 'lib\competences\_exemple.ps1') (Join-Path $d '_exemple.ps1')
    Copy-Item (Join-Path $Root 'lib\competences\_exemple.ps1') (Join-Path $d 'date.ps1')
    @'
Add-Action 'effacer_mon_cache' 2 'vider un cache' 'effacer_mon_cache(nom) : vide le cache de l''application nom' { param($a) Rep $true "Cache vidé : $($a.nom)" } { param($a) "vider le cache de $($a.nom)" }
'@ | Set-Content (Join-Path $d 'niveau2.ps1') -Encoding UTF8
    'Add-Action ''cassee'' 1 ''x'' ''cassee()'' { param($a) Rep $true ''x'' ' | Set-Content (Join-Path $d 'syntaxe.ps1') -Encoding UTF8        # accolade non fermée
    'Add-Action ''moitie'' 1 ''x'' ''moitie()'' { param($a) Rep $true ''x'' } { param($a) ''x'' }; throw ''échec en cours de route''' | Set-Content (Join-Path $d 'moitie.ps1') -Encoding UTF8
    $avant = $script:Actions.Count
    $r = Import-Competences $d
    Verifier ($r.chargees.Count -eq 2) "2 compétences chargées : $($r.chargees -join ' | ')"
    Verifier ($script:Actions.ContainsKey('dire_la_date_du_jour') -and $script:Actions.ContainsKey('effacer_mon_cache')) 'elles sont enregistrées'
    Verifier ($r.echecs.Count -eq 2 -and ($r.echecs -join ' ') -match 'syntaxe\.ps1' -and ($r.echecs -join ' ') -match 'moitie\.ps1') 'les fichiers défectueux (syntaxe, plantage en route) sont ignorés et signalés'
    Verifier (-not $script:Actions.ContainsKey('cassee') -and -not $script:Actions.ContainsKey('moitie')) 'une compétence à moitié chargée est retirée'
    Verifier ($script:Actions.Count -eq $avant + 2) 'seules les deux bonnes compétences ont été ajoutées'
    $reel = Import-Competences (Join-Path $Root 'lib\competences')
    Verifier ($reel.chargees.Count -eq 2 -and $reel.echecs.Count -eq 0 -and ($reel.chargees -join ' ') -notmatch '_exemple') 'dossier réel lib\competences : seules point-saas et idees-contenu sont chargées, le modèle _exemple.ps1 n''est PAS chargé (nom commençant par « _ »)'
    Verifier ((Get-CataloguePrompt) -match 'effacer_mon_cache\(nom\)' -and (Get-CataloguePrompt) -match 'dire_la_date_du_jour\(\)') 'le cerveau les voit dans son catalogue'
    Verifier ((Get-Niveau ([pscustomobject]@{ type = 'effacer_mon_cache'; nom = 'x' })).niveau -eq 2) 'niveau 2 respecté pour une compétence personnelle'
    Verifier ((Get-Niveau ([pscustomobject]@{ type = 'dire_la_date_du_jour' })).niveau -eq 1) 'niveau 1 respecté'
    $res = & $script:Actions['dire_la_date_du_jour'].run ([pscustomobject]@{})
    Verifier ($res.ok -and $res.texte -match '^Nous sommes le ') "elle s'exécute : $($res.texte)"
    Verifier ((Get-Niveau ([pscustomobject]@{ type = 'virement' })).niveau -eq 3 -and (Get-Niveau ([pscustomobject]@{ type = 'inconnue_xyz' })).niveau -eq 3) 'le niveau 3 reste décidé par le code (virement, action inconnue)'
    Verifier ((Get-Content (Get-ChildItem "$TR\logs" -Filter 'journal-*.md' | Select-Object -First 1).FullName -Raw -Encoding UTF8) -match 'Compétence personnelle IGNORÉE') 'les échecs sont au journal'
    Verifier ((Get-Niveau ([pscustomobject]@{ type = 'powershell'; code = "Set-Content '$Root\lib\competences\x.ps1' 'a'" })).niveau -eq 3) 'le cerveau ne peut pas écrire de compétence lui-même (le dossier Jarvis est protégé)'
    $vide = Import-Competences (Join-Path $TR 'inexistant'); Verifier ($vide.chargees.Count -eq 0 -and $vide.echecs.Count -eq 0) 'dossier absent : rien ne se passe'
} finally { Remove-Item $TR -Recurse -Force -ErrorAction SilentlyContinue }
if ($echecs) { Write-Host "`nÉCHEC : $echecs vérification(s) en échec." -ForegroundColor Red; exit 1 }
Write-Host "`nRÉUSSI"; exit 0
