# Priorité des ressources : "normal" (défaut), "eleve", "max". config.json "priorite_ressources" ; « priorité normale / élevée / maximum » à la voix
# est mémorisé dans memoire\priorite.json (pas dans config.json) et l'emporte sur config.json.
# EFFET RÉEL :
#   normal : Ollama décharge son modèle après 10 min d'inactivité ; veille de fond à son rythme normal (veille_minutes).
#   eleve  : le modèle Ollama configuré est GARDÉ CHAUD en mémoire (keep_alive illimité) et préchargé si le service Ollama tourne déjà ;
#            la veille de fond repasse toutes les veille_minutes / 3 (5 min au plus bas) — mais JAMAIS au-delà des limites de chaque source
#            (RSS : 15 min par flux ; Alpha Vantage : plafond de requêtes par jour).
#   max    : comme « eleve », avec le plus gros modèle DÉJÀ INSTALLÉ qui tient dans la mémoire du PC (≤ 60 % de la RAM) ; veille / 5 (3 min au plus bas).
#            Rien n'est jamais téléchargé : si un modèle plus gros serait possible, `jarvis.ps1 priorite` le suggère, c'est à vous de décider.
# Redescend AUTOMATIQUEMENT à « normal » en mode jeu et en sourdine (le modèle est déchargé), puis remonte à la sortie.
$script:PrioriteAppliquee = ''
$script:PrioriteProchain = [datetime]::MinValue
$script:ModeleChaud = ''
$script:ModelePlusGrosCache = $null; $script:ModelePlusGrosHeure = [datetime]::MinValue

function ConvertTo-NiveauPriorite([string]$t) {
    switch -Regex ((ConvertTo-NormMarche $t)) { '^(normal|normale)$' { 'normal' } '^(eleve|elevee|haute|haut)$' { 'eleve' } '^(max|maximum|maximale)$' { 'max' } default { $null } }
}
function Get-PrioriteDemandee {
    $o = Read-JsonMemoire 'priorite.json'
    $n = if ($o -and $o.niveau) { ConvertTo-NiveauPriorite "$($o.niveau)" } else { $null }
    if (-not $n -and $Config.PSObject.Properties['priorite_ressources']) { $n = ConvertTo-NiveauPriorite "$($Config.priorite_ressources)" }
    if ($n) { $n } else { 'normal' }
}
function Get-PrioriteEffective { if ($script:ModeJeu -eq $true -or $script:Actif -eq $false) { return 'normal' }; Get-PrioriteDemandee }
function Set-PrioriteDemandee([string]$niveau) {
    Save-JsonMemoire 'priorite.json' ([ordered]@{ niveau = $niveau; modifie = (Get-Date).ToString('o') })
    Write-Journal -Action 'Priorité des ressources' -Resultat "demandée : $niveau (mémorisée dans memoire\priorite.json)"
    $script:PrioriteProchain = [datetime]::MinValue
}

function Get-RamGo { try { [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 1) } catch { 0 } }
function Get-ModelesOllama {
    # Modèles installés avec leur taille (octets). Local uniquement ; @() si Ollama ne répond pas.
    $o = $Config.ollama; $url = if ($o -and $o.url) { "$($o.url)".TrimEnd('/') } else { 'http://127.0.0.1:11434' }
    if (-not (Test-UrlOllamaLocale $url)) { return @() }
    try { @((Invoke-RestMethod -Uri "$url/api/tags" -Method Get -TimeoutSec 2).models | ForEach-Object { @{ nom = "$($_.name)"; octets = [int64]$_.size } }) } catch { @() }
}
function Select-ModelePlusGros($modeles, [double]$ramGo, [string]$defaut) {
    # Fonction PURE : le plus gros modèle installé (hors « embed ») dont la taille tient dans 60 % de la RAM ; sinon le modèle configuré.
    $max = $ramGo * 0.6 * 1GB
    $c = @($modeles | Where-Object { $_.nom -notmatch 'embed' -and $_.octets -gt 0 -and $_.octets -le $max } | Sort-Object { $_.octets } -Descending)
    if ($c.Count) { $c[0].nom } else { $defaut }
}
function Get-SuggestionModele([double]$ramGo) {
    # Indication, jamais une action : rien n'est téléchargé sans votre accord.
    if ($ramGo -ge 48) { 'qwen2.5:32b (≈ 20 Go)' } elseif ($ramGo -ge 24) { 'qwen2.5:14b (≈ 9 Go)' } else { '' }
}
function Get-ModelePlusGros {
    if ($script:ModelePlusGrosCache -and ((Get-Date) - $script:ModelePlusGrosHeure).TotalMinutes -lt 5) { return $script:ModelePlusGrosCache }
    $defaut = if ($Config.ollama -and $Config.ollama.modele) { "$($Config.ollama.modele)" } else { 'qwen2.5:7b' }
    $ram = Get-RamGo; $inst = @(Get-ModelesOllama)
    $r = @{ modele = (Select-ModelePlusGros $inst $ram $defaut); ram_go = $ram; installes = @($inst | ForEach-Object { $_.nom }); suggestion = (Get-SuggestionModele $ram); defaut = $defaut }
    $script:ModelePlusGrosCache = $r; $script:ModelePlusGrosHeure = Get-Date; $r
}

function Get-PrioriteEffectiveFichier {
    # Lu par la veille de fond (qui ne connaît ni le mode jeu ni la sourdine autrement que par ce fichier).
    $f = Get-FichierMemoire 'priorite-effective.txt'
    if (Test-Path $f) { $n = ConvertTo-NiveauPriorite ((Get-Content $f -Raw -ErrorAction SilentlyContinue) -replace '\s', ''); if ($n) { return $n } }
    'normal'
}
function Get-VeilleMinutesEffectif {
    $m = Get-VeilleMinutes
    switch (Get-PrioriteEffectiveFichier) { 'eleve' { [math]::Max(5, [int][math]::Floor($m / 3)) } 'max' { [math]::Max(3, [int][math]::Floor($m / 5)) } default { $m } }
}

function Invoke-OllamaDecharger {
    # Décharge de la VRAM le modèle Ollama (configuré et/ou gardé chaud). Local uniquement ; ne démarre JAMAIS le service ; rien si le service ne répond pas.
    if (Test-ModeTest) { return }
    $o = $Config.ollama; $url = if ($o -and $o.url) { "$($o.url)".TrimEnd('/') } else { 'http://127.0.0.1:11434' }
    if (-not (Test-UrlOllamaLocale $url)) { return }
    try {
        $modeles = @($script:ModeleChaud, $(if ($o -and $o.modele) { "$($o.modele)" } else { 'qwen2.5:7b' })) | Where-Object { $_ } | Select-Object -Unique
        foreach ($m in $modeles) { [void](Invoke-RestMethod -Uri "$url/api/generate" -Method Post -Body (@{ model = $m; keep_alive = 0 } | ConvertTo-Json -Compress) -ContentType 'application/json' -TimeoutSec 3) }
        $script:ModeleChaud = ''; Write-Journal -Action 'GPU' -Resultat 'modèle Ollama déchargé de la mémoire'
    } catch {}
}
function Invoke-OllamaPriorite([string]$eff, [string]$ancien) {
    # Seul point qui parle à Ollama pour la priorité (remplacé par un bouchon dans les tests). Local uniquement ; ne démarre JAMAIS le service.
    if (Test-ModeTest) { return }
    $o = $Config.ollama; $url = if ($o -and $o.url) { "$($o.url)".TrimEnd('/') } else { 'http://127.0.0.1:11434' }
    if (-not (Test-UrlOllamaLocale $url)) { return }
    try {
        if ($eff -eq 'normal') {
            if ($script:ModeleChaud) { [void](Invoke-RestMethod -Uri "$url/api/generate" -Method Post -Body (@{ model = $script:ModeleChaud; keep_alive = 0 } | ConvertTo-Json -Compress) -ContentType 'application/json' -TimeoutSec 5); Write-Journal -Action 'Priorité des ressources' -Resultat "modèle $($script:ModeleChaud) déchargé"; $script:ModeleChaud = '' }
        } elseif ((Test-Ollama).actif) {
            $m = (Get-OllamaConfig).modele
            [void](Invoke-RestMethod -Uri "$url/api/generate" -Method Post -Body (@{ model = $m; keep_alive = -1 } | ConvertTo-Json -Compress) -ContentType 'application/json' -TimeoutSec 60)
            $script:ModeleChaud = $m; Write-Journal -Action 'Priorité des ressources' -Resultat "modèle $m gardé chaud"
        }
    } catch { Write-Journal -Action 'Priorité des ressources' -Resultat "Ollama : $(Hide-Secrets $_.Exception.Message)" }
}

function Update-Priorite {
    # Boucle principale : au plus toutes les 5 s. Applique la priorité EFFECTIVE (qui retombe à « normal » en mode jeu et en sourdine).
    $now = Get-Date; if ($now -lt $script:PrioriteProchain) { return }
    $script:PrioriteProchain = $now.AddSeconds(5)
    $eff = Get-PrioriteEffective
    if ($eff -eq $script:PrioriteAppliquee) { return }
    $ancien = $script:PrioriteAppliquee; $script:PrioriteAppliquee = $eff
    try { Set-Content (Get-FichierMemoire 'priorite-effective.txt') $eff -Encoding ASCII } catch {}
    $script:OllamaCache = $null                                               # le modèle / keep_alive attendu change
    Write-Journal -Action 'Priorité des ressources' -Resultat "effective : $eff$(if ($eff -eq 'normal' -and (Get-PrioriteDemandee) -ne 'normal') { ' (mode jeu ou sourdine : redescendue)' })"
    Invoke-OllamaPriorite $eff $ancien
}

function Get-RapportPriorite {
    $r = Get-ModelePlusGros; $dem = Get-PrioriteDemandee; $eff = Get-PrioriteEffective
    @("Priorité demandée : $dem ; effective maintenant : $eff (redescend à normal en mode jeu et en sourdine).",
      "Mémoire du PC : $($r.ram_go) Go. Modèle configuré : $($r.defaut). Modèles Ollama installés : $(if ($r.installes.Count) { $r.installes -join ', ' } else { 'aucun détecté (service arrêté ?)' }).",
      "Modèle utilisé en « max » : $($r.modele) (le plus gros installé qui tient dans 60 % de la RAM).",
      $(if ($r.suggestion -and -not (@($r.installes) -contains ($r.suggestion -replace ' .*$', ''))) { "Un modèle plus gros tiendrait dans la mémoire du PC : $($r.suggestion), non installé. Je ne télécharge rien sans votre accord." } else { 'Aucun téléchargement n''est proposé ni fait.' }))
}

if (Get-Command Add-Action -ErrorAction SilentlyContinue) {
    Add-Action 'priorite' 1 'régler la priorité des ressources' 'priorite(niveau) : normal | eleve | max — modèle local gardé chaud et veille plus fréquente (dans les limites des sources) ; redescend à normal en mode jeu / sourdine' {
        param($a)
        $n = ConvertTo-NiveauPriorite "$($a.niveau)"; if (-not $n) { return (Rep $false 'Priorité inconnue, monsieur : normale, élevée ou maximum.') }
        Set-PrioriteDemandee $n
        $noms = @{ normal = 'normale'; eleve = 'élevée'; max = 'maximum' }
        $t = "Priorité $($noms[$n]), monsieur."
        if ($n -ne 'normal') { $t += ' Elle redescend toute seule en mode jeu et en sourdine.' }
        if ($script:ModeJeu -eq $true -and $n -ne 'normal') { $t += ' Elle s''appliquera à la fin du mode jeu.' }
        Rep $true $t
    } { param($a) "priorité : $($a.niveau)" }
}
