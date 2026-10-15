# TEST MANUEL de la voix (VRAI SON) — à lancer VOUS-MÊME (jamais par Claude, jamais par tests\tout.ps1) : Jarvis lit trois phrases courtes avec le rythme naturel
# (fin d'audio avec marge de silence et fondu, pauses entre phrases, chiffres / pourcentage / date / heure dits en toutes lettres). Même chose que dire « Jarvis, test de voix ».
#   powershell -ExecutionPolicy Bypass -File tests\voix-reel.ps1 -Oui
# À ÉCOUTER : (1) la fin de chaque phrase ne doit plus être coupée net ; (2) une courte pause après chaque point ; (3) « plus 2,5 pour cent », « le 15 octobre », « 13 heures 20 »
# lus naturellement ; (4) le ton majordome inchangé. Pour comparer l'ancien rythme : mettez "voix_naturelle": false dans config.json et relancez ce test.
# Jarvis doit être arrêté (sinon deux voix se superposent). Aucune clé n'est affichée.
param([switch]$Oui)
if (-not $Oui) { Write-Host 'Ce test parle à voix haute. Relancez avec -Oui :'; Write-Host '  powershell -ExecutionPolicy Bypass -File tests\voix-reel.ps1 -Oui'; exit 2 }
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $Root 'lib\journal.ps1')
Import-JarvisEnv
$Config = Get-Content (Join-Path $Root 'config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($l in 'voix', 'business', 'permissions', 'actions', 'coffre', 'entrees', 'ecrans', 'tableau', 'visage', 'sons', 'raccourcis', 'cerveau', 'cerveau-local', 'veille', 'memoire', 'rapide', 'discretion', 'modejeu', 'competences', 'marche', 'priorite', 'comprehension', 'routeur', 'pc', 'bureau', 'salle-marche', 'matin') { . (Join-Path $Root "lib\$l.ps1") }
$echecs = 0
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }
$pidf = Join-Path $Root 'memoire\jarvis.pid'
$tourne = $false; if (Test-Path $pidf) { try { $o = Get-Content $pidf -Raw -Encoding UTF8 | ConvertFrom-Json; $tourne = [bool](Get-Process -Id ([int]$o.pid) -ErrorAction SilentlyContinue) } catch {} }
Verifier (-not $tourne) 'Jarvis n''est pas lancé (sinon : arreter.ps1, puis relancez ce test)'
if ($echecs) { exit 1 }
$script:Actif = $true
$p = Get-VoixParam
Write-Host ("Moteur : {0} ; naturelle = {1} ; marge de fin {2} ms ; fondu {3} ms ; pause entre phrases {4} ms ; Edge : {5}" -f (Get-VoixMoteur), $p.naturelle, $p.marge_ms, $p.fondu_ms, $p.pause_ms, (Get-EdgeArgsProsodie))
try {
    $script:DernierOrdre = @{ debut = Get-Date }
    Invoke-AvecContexteVoix 'reponse' { $r = & $script:Actions['test_voix'].run @{} }
    $d = $script:DernierOrdre
    Verifier ($null -ne $d.audio_s) ("première parole : {0} ms (dont {1} ms de préparation du texte) — moteur : {2}" -f [int]($d.audio_s * 1000), [int]$d.norm_ms, $script:DernierModeVoix)
} finally { Stop-Piper }
Verifier ($script:DernierModeVoix -ne '') "les trois phrases ont été lues (voix : $script:DernierModeVoix)"
if ($echecs) { Write-Host "`nÉCHEC : $echecs vérification(s) en échec." -ForegroundColor Red; exit 1 }
Write-Host "`nRÉUSSI — à vous d'écouter : fin de phrase, pauses, chiffres, ton majordome."; exit 0
