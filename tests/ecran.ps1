# Test du choix de l'écran (config.json "ecran_jarvis") et de la géométrie de la fenêtre. Code de sortie 0 = réussi.
$ErrorActionPreference = 'Stop'
$env:JARVIS_TEST = '1'      # TEST SILENCIEUX : aucun son, aucune fenêtre, aucun micro, aucune touche, aucune action réelle (voir lib\journal.ps1)
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $Root 'lib\journal.ps1')
. (Join-Path $Root 'lib\ecrans.ps1')
$Config = [pscustomobject]@{ visage = $true }
function Get-GeometrieVisage { param($ecran, [string]$mode, [int]$taille = 260, [int]$marge = 24) }   # remplacée ci-dessous par la vraie
. (Join-Path $Root 'lib\voix.ps1'); . (Join-Path $Root 'lib\business.ps1'); . (Join-Path $Root 'lib\permissions.ps1'); . (Join-Path $Root 'lib\actions.ps1'); . (Join-Path $Root 'lib\entrees.ps1'); . (Join-Path $Root 'lib\tableau.ps1'); . (Join-Path $Root 'lib\visage.ps1')

$echecs = 0
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }
function Mk($x, $y, $w, $h, $prim, $per, $nom) { [pscustomobject]@{ index = 0; peripherique = $per; nom = $nom; primaire = $prim; bounds = [pscustomobject]@{ X = $x; Y = $y; Width = $w; Height = $h; Right = $x + $w; Bottom = $y + $h }; zone = [pscustomobject]@{ X = $x; Y = $y; Width = $w; Height = $h - 40; Right = $x + $w; Bottom = $y + $h - 40 } } }

Write-Host '1) Choix de l''écran sur une configuration simulée (3 écrans, comme la vôtre)'
$sim = @(
    (Mk -1920 363 1920 1080 $false '\\.\DISPLAY2' 'SAM C27F390'),
    (Mk 0 0 2560 1440 $true '\\.\DISPLAY3' 'SAM Odyssey G5'),
    (Mk 2560 360 1920 1080 $false '\\.\DISPLAY1' 'HWV HUAWEI AD80HW')
)
for ($i = 0; $i -lt 3; $i++) { $sim[$i].index = $i }
Verifier ((Select-Ecran 'droite' $sim).ecran.peripherique -eq '\\.\DISPLAY1') '"droite" -> écran le plus à droite (Huawei)'
Verifier ((Select-Ecran '' $sim).ecran.peripherique -eq '\\.\DISPLAY3' -and -not (Select-Ecran '' $sim).raison) 'valeur vide -> écran PRINCIPAL par défaut (sans message)'
Verifier ((Select-Ecran 'gauche' $sim).ecran.peripherique -eq '\\.\DISPLAY2') '"gauche" -> écran le plus à gauche'
Verifier ((Select-Ecran 'principal' $sim).ecran.peripherique -eq '\\.\DISPLAY3') '"principal" -> écran principal'
Verifier ((Select-Ecran '1' $sim).ecran.peripherique -eq '\\.\DISPLAY3') 'index 1 -> deuxième écran en partant de la gauche'
Verifier ((Select-Ecran 'huawei' $sim).ecran.peripherique -eq '\\.\DISPLAY1') 'nom "huawei" -> moniteur HUAWEI'
Verifier ((Select-Ecran 'ODYSSEY' $sim).ecran.peripherique -eq '\\.\DISPLAY3') 'nom insensible à la casse'
Verifier ((Select-Ecran '\\.\DISPLAY2' $sim).ecran.peripherique -eq '\\.\DISPLAY2') 'nom de périphérique exact'
$r = Select-Ecran 'inconnu' $sim
Verifier ($r.ecran.peripherique -eq '\\.\DISPLAY3' -and $r.raison -match 'principal') 'choix introuvable -> repli sur l''écran principal, avec une raison'
$un = @((Mk 0 0 1920 1080 $true '\\.\DISPLAY1' 'X'))
Verifier ((Select-Ecran 'droite' $un).ecran.peripherique -eq '\\.\DISPLAY1') 'un seul écran -> il est choisi'

Write-Host '2) Géométrie de la fenêtre'
$huawei = $sim[2]
$g = Get-GeometrieVisage $huawei 'tableau' 260
Verifier ($g.type -eq 'zone' -and $g.x -eq 2560 -and $g.y -eq 360 -and $g.w -eq 1920 -and $g.h -eq 1040) 'tableau : occupe la zone de travail (1920x1040, barre des tâches de 40 px exclue), pas tout l''écran'
Verifier (($g.y + $g.h) -le (360 + 1040)) 'tableau : ne recouvre pas la barre des tâches'
$g = Get-GeometrieVisage $huawei 'discret' 260
Verifier ($g.type -eq 'coin' -and $g.w -eq 260 -and $g.h -eq 260 -and $g.droite -eq 4480 -and $g.bas -eq 1400 -and $g.marge -eq 24) 'discret : zone cliente 260x260, ancrée en bas à droite de la zone de travail (marge 24)'
Verifier (($g.x -ge 2560) -and ($g.x + $g.w -le 4480) -and ($g.y + $g.h -le 1400)) 'discret : reste à l''intérieur de la zone de travail de l''écran choisi'

Write-Host '2 bis) Plein écran sur l''écran principal : valeurs par défaut, écran inexistant, position mémorisée'
$vraie = Get-Content (Join-Path $Root 'config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
Verifier ($vraie.ecran_jarvis -eq 'principal' -and $vraie.jarvis_plein_ecran -eq $true -and $vraie.jarvis_memoriser_position -eq $false) 'config.json : ecran_jarvis = principal, jarvis_plein_ecran = true, jarvis_memoriser_position = false'
$Config = [pscustomobject]@{ visage = $true }
Verifier ((Get-PleinEcranVisage) -eq $true -and (Get-MemoriserPosition) -eq $false) 'sans réglage dans la config : plein écran OUI, mémorisation NON'
$Config | Add-Member -NotePropertyName jarvis_plein_ecran -NotePropertyValue $false; Verifier ((Get-PleinEcranVisage) -eq $false) 'jarvis_plein_ecran = false : fenêtre (zone de travail)'
$Config | Add-Member -NotePropertyName jarvis_memoriser_position -NotePropertyValue $true; Verifier ((Get-MemoriserPosition) -eq $true) 'jarvis_memoriser_position = true : activée seulement sur demande'
$prim = $sim[1]
$g = Get-GeometrieVisage $prim 'tableau' 260 24 $true
Verifier ($g.type -eq 'zone' -and $g.plein -and $g.x -eq 0 -and $g.y -eq 0 -and $g.w -eq 2560 -and $g.h -eq 1440) 'plein écran : tout l''écran principal (2560x1440 en 0,0), barre des tâches comprise'
$g = Get-GeometrieVisage $prim 'tableau' 260 24
Verifier (-not $g.plein -and $g.type -eq 'zone') 'sans demande de plein écran : zone de travail comme avant'
$g = Get-GeometrieVisage $prim 'discret' 260 24 $true
Verifier ($g.type -eq 'coin' -and $g.w -eq 260) 'mode discret : l''orbe reste en petit dans le coin (jamais plein écran)'
$g = Get-GeometrieVisage $sim[2] 'tableau' 260 24 $true
Verifier ($g.x -eq 2560 -and $g.w -eq 1920 -and $g.h -eq 1080) 'un autre écran choisi (ecran_jarvis) : plein écran sur celui-là'
Verifier ((Select-Ecran '7' $sim).ecran.primaire -and (Select-Ecran 'ecran-inexistant' $sim).ecran.primaire) 'écran inexistant (numéro ou nom) : retombe sur l''écran principal'
$sansPrim = @((Mk 0 0 1920 1080 $false 'DISPLAY9' 'X')); Verifier ((Select-Ecran 'principal' $sansPrim).ecran.peripherique -eq 'DISPLAY9') 'aucun écran marqué principal : le premier est pris (pas d''erreur)'
$TR = Join-Path $env:TEMP ('jarvis-test-' + [guid]::NewGuid().ToString('N').Substring(0, 8)); New-Item -ItemType Directory $TR, "$TR\memoire", "$TR\logs" | Out-Null; $script:JarvisRoot = $TR
Verifier ($null -eq (Get-FenetreMemorisee $sim)) 'aucun fichier memoire\fenetre-jarvis.json : rien à restaurer'
Verifier ((Save-FenetreMemorisee @(100, 80, 1300, 900)) -and (Test-Path "$TR\memoire\fenetre-jarvis.json")) 'position choisie à la main enregistrée dans memoire\fenetre-jarvis.json'
$m = Get-FenetreMemorisee $sim
Verifier ($m -and $m.x -eq 100 -and $m.y -eq 80 -and $m.w -eq 1200 -and $m.h -eq 820 -and -not $m.plein) 'et relue (1200x820 en 100,80)'
Verifier (-not (Save-FenetreMemorisee @(0, 0, 50, 40)) -and -not (Save-FenetreMemorisee @(-32000, -32000, -31840, -31972))) 'fenêtre minuscule ou réduite : jamais mémorisée'
Save-JsonMemoire 'fenetre-jarvis.json' ([ordered]@{ x = 90000; y = 90000; w = 800; h = 600 })
Verifier ($null -eq (Get-FenetreMemorisee $sim)) 'position qui ne tombe plus sur aucun écran (écran débranché) : ignorée'
Remove-Item $TR -Recurse -Force -ErrorAction SilentlyContinue
$vs = Get-Content (Join-Path $Root 'lib\visage.ps1') -Raw -Encoding UTF8
Verifier ($vs -match '--start-fullscreen' -and $vs -match 'Get-PleinEcranVisage' -and $vs -match 'Get-MemoriserPosition' -and $vs -match 'Save-FenetreMemorisee') 'Start-Visage / Stop-Visage : plein écran et mémorisation branchés'
Verifier ($vs -match 'public static bool Sur\(IntPtr h\)' -and $vs -match 'titreOk' -and $vs -match 'pidsOk' -and $vs -match 'JarvisOrb-' -and $vs -match 'Get-ArbrePids \$script:EdgePid') 'protection de la fenêtre par TITRE UNIQUE et PID de l''Edge lancé par Jarvis : intacte'
Verifier ($vs -match 'Stop-FenetreMarche' -and $vs -match 'Stop-Process -Id \$p') 'fermeture avec Jarvis : l''Edge de Jarvis (et la salle de marché) se ferment'
Verifier ((Get-Content (Join-Path $Root 'lib\salle-marche.ps1') -Raw -Encoding UTF8) -match 'ecran_marche') 'la salle de marché garde son propre réglage (ecran_marche)'


Write-Host '3) Écrans réels de ce PC'
$reels = @(Get-Ecrans)
Verifier ($reels.Count -ge 1) ("$($reels.Count) écran(s) détecté(s) : " + (($reels | ForEach-Object { "$($_.peripherique) [$($_.nom)]" }) -join ' ; '))
$droit = (Select-Ecran 'droite').ecran
Verifier (($reels | Sort-Object { $_.bounds.X } | Select-Object -Last 1).peripherique -eq $droit.peripherique) 'l''écran "droite" réel est bien le plus à droite'

if ($echecs) { Write-Host "`nÉCHEC : $echecs vérification(s) en échec." -ForegroundColor Red; exit 1 }
Write-Host "`nRÉUSSI"; exit 0
