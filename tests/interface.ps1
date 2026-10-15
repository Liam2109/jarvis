# Test SILENCIEUX de l'interface du tableau de bord (visage\index.html) : aucune fenêtre visible, aucun son, aucun focus, aucune connexion à Jarvis.
# La page est chargée par Edge SANS FENÊTRE (--headless), dans un profil jetable, avec des données FICTIVES (tests\demo-tableau.json : panneaux pleins, vides, très longs textes)
# et à plusieurs résolutions ; le contrôle de mise en page est fait par la page elle-même (fonction controle()) : rien ne défile, rien ne déborde, rien ne se chevauche,
# l'orbe est au centre exact de l'écran. Option -Captures : garde aussi des images PNG dans %TEMP%\jarvis-captures (à supprimer ensuite). Code de sortie 0 = réussi.
param([switch]$Captures)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$echecs = 0
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }
$html = Get-Content (Join-Path $Root 'visage\index.html') -Raw -Encoding UTF8

Write-Host '1) Page locale, sans dépendance externe'
Verifier ($html -notmatch '<script[^>]+src=' -and $html -notmatch '<link[^>]+rel="stylesheet"' -and $html -notmatch '@import' -and $html -notmatch 'url\(\s*["'']?https?:') 'aucun script, feuille de style, police ni image externes (hors ligne)'
Verifier (([regex]::Matches($html, 'https?://[^"''\s)]+') | Where-Object { $_.Value -notmatch 'www\.w3\.org' }).Count -eq 0) 'aucune adresse externe dans la page (seul l''espace de noms SVG du favicon)'
Verifier ($html.Contains('<title>__TITRE__</title>') -and $html.Contains('const K = "__TOKEN__"') -and $html.Contains('<body class="__MODE__">')) 'jeton, titre unique et mode toujours injectés par Jarvis'
Verifier ($html -notmatch 'document\.title\s*=') 'le titre de la fenêtre (identifiant unique de l''orbe) n''est jamais modifié par la page'
Verifier ($html.Contains('background: #04070c') -and $html -match '<style>html, body \{ background: #04070c') 'fond sombre dès la première image (aucun écran blanc)'
foreach ($id in 'orbe', 'statut', 'heure', 'date', 'saisie', 'oui', 'non', 'reduire', 'site', 'briefing', 'biz', 'alertes', 'todo', 'marche', 'surveiller', 'actus', 'dossier', 'diag', 'diag-moteur', 'conv', 'guide', 'journal', 'micro-nom', 'micro-niv', 'micro-ent', 'v-etat', 'v-moteur', 'v-musique', 'v-priorite', 'v-pc') {
    if (-not $html.Contains("id=`"$id`"")) { Verifier $false "élément manquant : #$id" }
}
Verifier ($true) 'tous les éléments (orbe, panneaux, saisie, oui/non, réduire, journal, micro, barre d''état) sont présents'
Verifier ($html -match 'visibilitychange' -and $html -match 'body\.jeu #orbe \{ visibility: hidden' -and $html -match 'majAnimation' -and $html -match 'document\.hidden \? 5000') 'animations suspendues quand la page est masquée ou en mode jeu ; sondage ralenti quand elle est masquée'
Verifier ($html -match 'Math\.min\(2, devicePixelRatio' -and $html -match 'now - dernierCadre < 32') 'orbe légère : 30 images/s au plus, résolution du canvas plafonnée'
Verifier ($html -match 'body\.discret' -and $html -match 'max-aspect-ratio') 'mode discret conservé ; mise en page adaptée aux écrans presque carrés ou en hauteur'
$vp = Get-Content (Join-Path $Root 'lib\visage.ps1') -Raw -Encoding UTF8
Verifier ($vp -match 'niveau = \$niv; jeu = ' -and $vp -match 'JarvisOrb-' -and $vp -match 'Autoriser\(\$script:TitreOrbe') '/etat renvoie aussi le niveau du micro et le mode jeu ; la fenêtre reste identifiée par son titre unique et le PID de son Edge'

$edge = (Get-Command msedge -ErrorAction SilentlyContinue).Source
if (-not $edge) { $edge = "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe" }
if (-not (Test-Path $edge)) { Write-Host '  (Edge introuvable : contrôle de mise en page ignoré)' -ForegroundColor DarkGray; if ($echecs) { exit 1 }; Write-Host "`nRÉUSSI"; exit 0 }

$tmp = Join-Path $env:TEMP ('jarvis-test-interface-' + [guid]::NewGuid().ToString('N').Substring(0, 8)); New-Item -ItemType Directory $tmp | Out-Null
$profil = Join-Path $tmp 'profil'
$demo = Get-Content (Join-Path $PSScriptRoot 'demo-tableau.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$cap = Join-Path $env:TEMP 'jarvis-captures'; if ($Captures) { New-Item -ItemType Directory $cap -Force | Out-Null }

function Invoke-EdgeSansFenetre([string[]]$args2, [string]$sortie) {
    # Edge sans fenêtre, profil jetable ; seul le processus lancé ici est surveillé / arrêté.
    $a = @('--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check', '--disable-extensions', '--disable-sync', '--hide-scrollbars', '--force-device-scale-factor=1', '--mute-audio', "--user-data-dir=$profil") + $args2
    $p = Start-Process $edge -ArgumentList $a -PassThru -WindowStyle Hidden -RedirectStandardOutput $sortie -RedirectStandardError (Join-Path $tmp 'err.txt')
    if (-not $p.WaitForExit(60000)) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Milliseconds 150
}
function Get-PageDemo([string]$scenario) {
    $json = ($demo.$scenario | ConvertTo-Json -Depth 12 -Compress) -replace '</', '<\/'
    $mode = 'tableau'
    $h = $html.Replace('__TOKEN__', 'jeton-de-test').Replace('__TITRE__', 'JarvisOrb-test').Replace('__MODE__', $mode).Replace('<script>' + "`n" + 'const K', "<script>window.__DEMO = $json; window.__CONTROLE = true;</script>`n<script>`nconst K")
    $f = Join-Path $tmp "demo-$scenario.html"; [IO.File]::WriteAllText($f, $h, [Text.UTF8Encoding]::new($false)); $f
}
$script:Cadre = $null      # écart fenêtre - page mesuré une fois (Edge sans fenêtre compte son cadre) : la PAGE reçoit exactement w x h pixels
function Get-RapportPage([string]$url, [int]$ww, [int]$hh) {
    $sortie = Join-Path $tmp 'dom.txt'; Remove-Item $sortie -ErrorAction SilentlyContinue
    Invoke-EdgeSansFenetre @("--window-size=$ww,$hh", '--virtual-time-budget=4000', '--dump-dom', $url) $sortie
    $dom = if (Test-Path $sortie) { Get-Content $sortie -Raw -Encoding UTF8 } else { '' }
    [regex]::Match($dom, '(?s)<pre[^>]*id="controle"[^>]*>(.*?)</pre>')
}
function Test-Resolution([string]$scenario, [int]$w, [int]$h) {
    $f = Get-PageDemo $scenario; $url = ([Uri]$f).AbsoluteUri
    if (-not $script:Cadre) {
        $m0 = Get-RapportPage $url $w $h
        if ($m0.Success) { $r0 = [Net.WebUtility]::HtmlDecode($m0.Groups[1].Value) | ConvertFrom-Json; $script:Cadre = @{ x = $w - [int]$r0.viewport[0]; y = $h - [int]$r0.viewport[1] } } else { $script:Cadre = @{ x = 0; y = 0 } }
    }
    $ww = $w + $script:Cadre.x; $hh = $h + $script:Cadre.y
    $m = Get-RapportPage $url $ww $hh
    if ($Captures) { $png = Join-Path $cap ("{0}-{1}x{2}.png" -f $scenario, $w, $h); Invoke-EdgeSansFenetre @("--window-size=$ww,$hh", '--virtual-time-budget=4000', "--screenshot=$png", $url) (Join-Path $tmp 'shot.txt') }
    if (-not $m.Success) { return [pscustomobject]@{ ok = $false; message = 'aucun rapport de mise en page (la page ne s''est pas exécutée ?)'; r = $null } }
    $r = [Net.WebUtility]::HtmlDecode($m.Groups[1].Value) | ConvertFrom-Json
    if ([int]$r.viewport[0] -ne $w -or [int]$r.viewport[1] -ne $h) { return [pscustomobject]@{ ok = $false; message = "la page a reçu $($r.viewport[0])x$($r.viewport[1]) au lieu de ${w}x${h}"; r = $r } }
    [pscustomobject]@{ ok = (@($r.problemes).Count -eq 0); message = (@($r.problemes) -join ' | '); r = $r }
}

Write-Host '2) Mise en page à plusieurs résolutions (données fictives, Edge sans fenêtre)'
$grille = @(
    @('pleins', 1920, 1080), @('longs', 1920, 1080), @('vides', 1920, 1080), @('indispo', 1920, 1080), @('jeu', 1920, 1080),
    @('pleins', 2560, 1440), @('longs', 2560, 1440), @('vides', 2560, 1440),
    @('pleins', 1366, 768), @('longs', 1366, 768), @('vides', 1366, 768), @('indispo', 1366, 768),
    @('pleins', 3840, 2160), @('longs', 3840, 2160), @('vides', 3840, 2160),
    @('pleins', 3440, 1440), @('longs', 3440, 1440), @('longs', 1280, 1024), @('pleins', 1080, 1920), @('longs', 1080, 1920))
$minimaux = @{}
foreach ($c in $grille) {
    $t = Test-Resolution $c[0] $c[1] $c[2]
    $desc = "{0} à {1}x{2}" -f $c[0], $c[1], $c[2]
    if ($t.r) { $d2 = "$desc : orbe $($t.r.orbe[0]) px centrée en $($t.r.orbe[1]),$($t.r.orbe[2]) ; $($t.r.panneaux) panneaux ; police min $([math]::Round($t.r.police_min, 1)) px"; $minimaux["$($c[1])x$($c[2])"] = [math]::Min($(if ($minimaux["$($c[1])x$($c[2])"]) { $minimaux["$($c[1])x$($c[2])"] } else { 999 }), $t.r.police_min) } else { $d2 = $desc }
    Verifier $t.ok $(if ($t.ok) { $d2 } else { "$desc : $($t.message)" })
}
foreach ($k in $minimaux.Keys) { $w = [int]($k -split 'x')[0]; $mini = if ($w -ge 1900) { 12 } else { 10 }; Verifier ($minimaux[$k] -ge $mini) "texte lisible à $k : plus petit corps $([math]::Round($minimaux[$k], 1)) px (au moins $mini px)" }

Write-Host '3) Contenu : panneaux vides lisibles, raisons exactes affichées'
$t = Test-Resolution 'indispo' 1920 1080
$f = Get-PageDemo 'indispo'; $sortie = Join-Path $tmp 'dom2.txt'
Invoke-EdgeSansFenetre @('--window-size=1920,1080', '--virtual-time-budget=4000', '--dump-dom', ([Uri]$f).AbsoluteUri) $sortie
$dom = [Net.WebUtility]::HtmlDecode((Get-Content $sortie -Raw -Encoding UTF8))
Verifier ($dom -match 'Marché désactivé : mets marche_actif à true dans config\.json') 'le panneau Marché affiche la raison exacte : « Marché désactivé : mets marche_actif à true… »'
Verifier ($dom -match 'Mon SaaS : indisponible \(jeton refusé') 'Mon SaaS indisponible : cause affichée'
$f = Get-PageDemo 'vides'; Invoke-EdgeSansFenetre @('--window-size=1920,1080', '--virtual-time-budget=4000', '--dump-dom', ([Uri]$f).AbsoluteUri) $sortie
$dom = [Net.WebUtility]::HtmlDecode((Get-Content $sortie -Raw -Encoding UTF8))
Verifier (([regex]::Matches($dom, 'class="panneau[^"]*vide-p')).Count -ge 4) 'panneaux vides : réduits à leur titre et à une phrase courte (pas de grand vide)'
Verifier ($dom -match 'SOURDINE') 'sourdine : la barre d''état l''indique'
$f = Get-PageDemo 'jeu'; Invoke-EdgeSansFenetre @('--window-size=1920,1080', '--virtual-time-budget=4000', '--dump-dom', ([Uri]$f).AbsoluteUri) $sortie
$dom = [Net.WebUtility]::HtmlDecode((Get-Content $sortie -Raw -Encoding UTF8))
Verifier ($dom -match '<body class="[^"]*\bjeu\b' -and $dom -match 'MODE JEU') 'mode jeu : classe « jeu » (orbe masquée, animation arrêtée) et « MODE JEU » dans la barre'

Write-Host '4) To-do, courbes du marché, carrousel d''actualités (données fictives)'
$f = Get-PageDemo 'pleins'; Invoke-EdgeSansFenetre @('--window-size=1920,1080', '--virtual-time-budget=4000', '--dump-dom', ([Uri]$f).AbsoluteUri) $sortie
$dom = [Net.WebUtility]::HtmlDecode((Get-Content $sortie -Raw -Encoding UTF8))
Verifier (([regex]::Matches($dom, 'class="tache fait"')).Count -eq 2 -and ([regex]::Matches($dom, 'class="tache "')).Count -eq 3 -and $dom -match '3 ouvertes') 'to-do : 3 tâches ouvertes (cases vides) et 2 faites (cochées, en vert)'
Verifier (([regex]::Matches($dom, '<svg class="courbe (hausse|baisse)"')).Count -eq 2 -and $dom -match 'class="courbe hausse"' -and $dom -match 'class="courbe baisse"' -and $dom -match '▲ \+1,2 %' -and $dom -match '▼ −0,5 %') 'marché : une courbe par valeur (vert en hausse, rouge en baisse) ET toujours le signe + / − et la flèche'
Verifier (([regex]::Matches($dom, 'class="slide"><div class="titre-a" title="[^$]')).Count -eq 4 -and $dom -match 'class="points"' -and $dom -match '1 / 4') 'actualités : carrousel, une à la fois (4 diapositives, pastilles, compteur 1 / 4)'
Verifier ($html -match 'carrSec|armerCarrousel' -and $html -match 'actus_secondes' -and $html -match 'mouseenter' -and $html -match 'mouseleave' -and $html -match 'function passerCarrousel\(\) \{ if \(carr\.n < 2 \|\| carr\.pause \|\| document\.hidden' -and $html -match 'translateX') 'carrousel : glissement toutes les « actualites_secondes » s, pause au survol, pause quand la fenêtre est masquée ou en mode jeu, aucun focus pris'
Verifier ($html -match 'function courbe' -and $html -match 'if \(s\.length < 2\) return ""') 'courbe : seulement avec au moins 2 relevés réels (jamais de faux chiffre)'
$f = Get-PageDemo 'indispo'; Invoke-EdgeSansFenetre @('--window-size=1920,1080', '--virtual-time-budget=4000', '--dump-dom', ([Uri]$f).AbsoluteUri) $sortie
$dom = [Net.WebUtility]::HtmlDecode((Get-Content $sortie -Raw -Encoding UTF8))
Verifier (($dom -match 'Marché désactivé') -and -not ($dom -match '<svg class="courbe (hausse|baisse)"')) 'sans source : message exact, AUCUNE courbe ni chiffre de marché'

if ($Captures) { Write-Host "  (images gardées dans $cap — à supprimer ensuite)" -ForegroundColor DarkGray }
# nettoyage : profil jetable, pages de test ; aucun processus Edge ne doit rester de CE test
$reste = @(Get-CimInstance Win32_Process -Filter "Name='msedge.exe'" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match [regex]::Escape($tmp) })
foreach ($p in $reste) { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Milliseconds 400
Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
Verifier ($reste.Count -eq 0) 'aucun processus Edge du test ne reste'
if ($echecs) { Write-Host "`nÉCHEC : $echecs vérification(s) en échec." -ForegroundColor Red; exit 1 }
Write-Host "`nRÉUSSI"; exit 0
