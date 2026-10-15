# TEST MANUEL de la salle de marché — à lancer VOUS-MÊME (via tests\manuels.ps1 -Oui), jamais par Claude ni par tests\tout.ps1.
# Il ouvre une VRAIE fenêtre Edge (profil jetable) sur l'écran choisi (config.json : ecran_marche ; défaut : le deuxième écran s'il existe, sinon le principal), la fait servir
# la vraie page visage\marche.html par un serveur local temporaire (127.0.0.1, jeton, données FICTIVES), vérifie que la fenêtre est bien sur cet écran, puis la referme.
# Aucune requête Alpha Vantage, aucun onglet de navigateur, aucun son. Pendant qu'il tourne : ne cliquez pas dans d'autres fenêtres.
$ErrorActionPreference = 'Stop'
Remove-Item Env:JARVIS_TEST -ErrorAction SilentlyContinue
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $Root 'lib\journal.ps1')
$TR = Join-Path $env:TEMP ('jarvis-test-' + [guid]::NewGuid().ToString('N').Substring(0, 8)); New-Item -ItemType Directory $TR, "$TR\memoire", "$TR\logs" | Out-Null
$Config = Get-Content (Join-Path $Root 'config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($l in 'voix', 'marche', 'ecrans', 'visage', 'pc', 'salle-marche') { . (Join-Path $Root "lib\$l.ps1") }
New-Item -ItemType Directory "$TR\visage" | Out-Null; Copy-Item (Join-Path $Root 'visage\marche.html') "$TR\visage\marche.html"
$script:JarvisRoot = $TR      # la page est servie depuis une copie ; le journal et la mémoire de ce test restent dans le dossier temporaire (jamais dans votre logs\ ni memoire\)
$echecs = 0
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }
$port = 47651; $Config.visage_port = $port
$script:Jeton = 'jeton-de-test-manuel'
$script:Http = New-Object Net.HttpListener; $script:Http.Prefixes.Add("http://127.0.0.1:$port/"); $script:Http.Start(); $script:HttpTache = $script:Http.GetContextAsync()
function Pomper([int]$ms) { $fin = (Get-Date).AddMilliseconds($ms); while ((Get-Date) -lt $fin) { Invoke-PumpVisage; Start-Sleep -Milliseconds 50 } }
try {
    $pts = 0..21 | ForEach-Object { @{ t = (Get-Date).Date.AddDays($_ - 21).ToString('yyyy-MM-dd'); c = [math]::Round(140 + $_ * 0.8 + [math]::Sin($_ / 2.0) * 1.5, 2) } }
    $p = @{ libelle = 'le mois'; n = 21; points = $pts; variation_pct = 3.4; debut = @{ date = $pts[0].t; c = $pts[0].c }; fin = @{ date = $pts[-1].t; c = $pts[-1].c }; haut = @{ v = 160.2; date = $pts[-3].t }; bas = @{ v = 139.1; date = $pts[1].t } }
    $script:SalleDonnees = @{ nom = 'Valeur de test'; symbole = 'TEST'; devise = 'EUR'; maj = (Get-Date).ToString('o'); source = 'données fictives'; cache = $false; cache_perime = $false; quota = @{ n = 3; plafond = 20; presque = $false }; avertissements = @(); periodes = [ordered]@{ '1mois' = $p }
        reperes = @(); actus = @(@{ titre = 'Actualité fictive (texte seulement)'; source = 'Flux de test'; date = (Get-Date).ToString('o') }); phrase = 'x' }
    $ecran = Get-EcranMarche
    Write-Host "Écran choisi : index $($ecran.index) ($($ecran.peripherique) $($ecran.nom)), zone $($ecran.zone.Width)x$($ecran.zone.Height) en $($ecran.zone.X),$($ecran.zone.Y)"
    $ok = Open-FenetreMarche $ecran
    Verifier $ok 'la fenêtre Edge est lancée'
    Pomper 6000
    $w = $null; $fin = (Get-Date).AddSeconds(10)
    while (-not $w -and (Get-Date) -lt $fin) { Pomper 300; $w = @([JarvisPc]::Liste() | Where-Object { $_ -match '\|Jarvis - Salle de marché$' })[0] }
    Verifier ([bool]$w) 'la fenêtre « Jarvis - Salle de marché » existe (la page a bien été servie)'
    if ($w) {
        $h = [IntPtr]::new([int64]($w -split '\|')[0]); $r = @([JarvisPc]::Rect($h)); $z = $ecran.zone
        $cx = $r[0] + $r[2] / 2; $cy = $r[1] + $r[3] / 2
        Verifier ($cx -ge $z.X -and $cx -le $z.X + $z.Width -and $cy -ge $z.Y -and $cy -le $z.Y + $z.Height) "la fenêtre est sur l'écran choisi (centre $([int]$cx),$([int]$cy) ; zone $($z.X),$($z.Y) → $($z.X + $z.Width),$($z.Y + $z.Height))"
        Verifier (-not @(Get-FenetresPc | Where-Object { $_.titre -like 'Jarvis - Salle*' }).Count) 'les commandes du PC ne voient pas cette fenêtre (titre « Jarvis… » protégé)'
    }
    Stop-FenetreMarche; Pomper 800
    Verifier (-not (Get-Process -Id $script:SalleFenetrePid -ErrorAction SilentlyContinue) -and $script:SalleFenetrePid -eq 0) 'la fenêtre est refermée (et elle seule)'
} finally {
    try { Stop-FenetreMarche } catch {}
    try { $script:Http.Stop(); $script:Http.Close() } catch {}
    Remove-Item $TR -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item (Join-Path $env:TEMP 'jarvis-edge-marche') -Recurse -Force -ErrorAction SilentlyContinue
}
Write-Host ''
Write-Host 'À vérifier AUSSI à la voix, Jarvis lancé par vous, une fois marche_actif = true, Alpha Vantage validé et un symbole renseigné :' -ForegroundColor Cyan
@('« Jarvis, montre-moi le marché de <une valeur de memoire\marche-valeurs.json> » : résumé chiffré (jamais de conseil), page sur le bon écran, boutons 1 J / 1 S / 1 M / 1 A',
  '« Jarvis, où en est <valeur> » une 2e fois : aucune nouvelle requête (cache) — vérifiez le compteur « Requêtes du jour » sur la page',
  '« Jarvis, montre-moi le marché de <valeur inconnue> » : refus poli',
  'Avec sites_marche_autorises = ["tradingview.com"] et un lien (ou sites_marche_modeles) : 1 à 2 onglets sur le même écran ; avec la liste vide : refus poli',
  '« Jarvis, ferme la salle de marché »') | ForEach-Object { Write-Host "  - $_" }
if ($echecs) { Write-Host "`n$echecs échec(s)." -ForegroundColor Red; exit 1 }
Write-Host "`nTOUT EST VERT." -ForegroundColor Green; exit 0
