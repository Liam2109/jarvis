# Permissions : le NIVEAU est décidé ici par le code, jamais par Claude.
#   1 = autonome   2 = confirmation "oui" requise   3 = refus
# Get-Niveau retourne @{ niveau; raison }

$script:TypesNiveau3 = @{
    virement = 'les virements'; achat = 'les achats'; trade = 'les trades'; action_financiere = 'les actions financières'
    desactiver_antivirus = "la désactivation de l'antivirus"; desactiver_pare_feu = 'la désactivation du pare-feu'
    modifier_mot_de_passe = 'la modification de mots de passe'; supprimer_jarvis = 'la suppression de Jarvis ou de son journal'
}

# Chemins protégés : Jarvis lui-même (dossier, journal, mémoire, .env)
function Test-CheminJarvis([string]$chemin) {
    if (-not $chemin) { return $false }
    try { $p = [IO.Path]::GetFullPath($chemin).TrimEnd('\') } catch { return $false }
    $r = $script:JarvisRoot.TrimEnd('\')
    return ($p -ieq $r) -or $p.StartsWith($r + '\', [StringComparison]::OrdinalIgnoreCase)
}

# Fichiers sensibles qu'on ne lit jamais (le contenu partirait vers Claude)
function Test-CheminSecret([string]$chemin) {
    if (-not $chemin) { return $false }
    $c = $chemin.ToLower()
    return ($c -match '(^|\\)\.env(\.|$)') -or ($c -match '\\\.ssh\\') -or ($c -match '\\login data$|\\cookies$|\\web data$|\\key4\.db$|\\logins\.json$') -or ($c -match 'id_rsa|id_ed25519|\.kdbx$|\.pfx$|\.pem$|bitwarden') -or ((Test-CheminJarvis $chemin) -and ($c -match '\\config\.json$'))
}

# Chemins système : jamais supprimés/déplacés par Jarvis
function Test-CheminSysteme([string]$chemin) {
    if (-not $chemin) { return $false }
    try { $p = [IO.Path]::GetFullPath($chemin).TrimEnd('\') } catch { return $false }
    if ($p -match '^[A-Za-z]:$') { return $true }
    foreach ($s in $env:SystemRoot, $env:ProgramFiles, ${env:ProgramFiles(x86)}, $env:ProgramData, $env:USERPROFILE, "$env:USERPROFILE\AppData") {
        if ($s -and $p -ieq $s.TrimEnd('\')) { return $true }
    }
    foreach ($s in $env:SystemRoot, $env:ProgramFiles, ${env:ProgramFiles(x86)}) {
        if ($s -and $p.StartsWith($s.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase)) { return $true }
    }
    return $false
}

$script:ExtExecutables = '\.(exe|bat|cmd|ps1|psm1|vbs|vbe|js|jse|wsf|wsh|msi|msp|scr|com|pif|jar|reg|hta|lnk|cpl|dll)$'

# Motifs de code PowerShell bloqués (niveau 3), lus depuis lib\interdits.json. Garde-fou "au mieux" : la vraie barrière reste la confirmation.
$script:MotifsInterdits = @(Get-Content (Join-Path $PSScriptRoot 'interdits.json') -Raw -Encoding UTF8 | ConvertFrom-Json | ForEach-Object { $_ })   # ForEach : PS 5.1 renvoie sinon un tableau imbriqué

function Test-Courtier([string]$texte) {
    # Courtiers, plateformes de trading/crypto et banques : Jarvis ne s'y connecte jamais et n'y saisit aucun identifiant.
    if (-not $texte) { return $false }
    foreach ($m in $script:MotifsInterdits) { if ($m.raison -like '*courtier*' -and $texte -match $m.re) { return $true } }
    $false
}

function Get-Niveau($a) {
    $t = "$($a.type)".ToLower()
    if ($script:TypesNiveau3.ContainsKey($t)) { return @{ niveau = 3; raison = $script:TypesNiveau3[$t] } }
    if (-not $script:Actions.ContainsKey($t)) { return @{ niveau = 3; raison = "action inconnue ($t)" } }
    $def = $script:Actions[$t]

    # Garde-fous généraux sur les chemins
    foreach ($k in 'chemin', 'source', 'destination', 'dossier') {
        if ($a.$k -and ($t -in 'supprimer_fichier', 'deplacer_fichier', 'mettre_en_quarantaine', 'executer_script')) {
            if (Test-CheminJarvis "$($a.$k)") { return @{ niveau = 3; raison = 'le dossier Jarvis et son journal sont protégés' } }
        }
    }
    if ($t -in 'supprimer_fichier', 'deplacer_fichier') {
        foreach ($k in 'chemin', 'source') { if ($a.$k -and (Test-CheminSysteme "$($a.$k)")) { return @{ niveau = 3; raison = 'chemin système protégé' } } }
    }
    if ($t -eq 'bitwarden_saisir' -and (Test-Courtier "$($a.recherche)")) { return @{ niveau = 3; raison = 'connexion à un courtier ou à une banque (interdite)' } }
    if ($t -eq 'lire_fichier' -and (Test-CheminSecret "$($a.chemin)")) { return @{ niveau = 3; raison = 'ce fichier contient des secrets' } }
    if ($t -eq 'powershell') {
        $code = "$($a.code)"
        foreach ($m in $script:MotifsInterdits) { if ($code -match $m.re) { return @{ niveau = 3; raison = $m.raison } } }
        if ($code -match '(?i)\.env|\\Jarvis(\\|"|''|\s|$)|memoire\\|logs\\journal') { return @{ niveau = 3; raison = 'le dossier Jarvis et son journal sont protégés' } }
        return @{ niveau = 2; raison = 'commande PowerShell libre' }
    }
    if ($t -eq 'ouvrir_chemin' -and "$($a.chemin)" -match $script:ExtExecutables) { return @{ niveau = 2; raison = "lancer un programme ou un script" } }
    if ($t -eq 'executer_script') {
        $c = "$($a.chemin)"
        $tel = $c -match '(?i)\\Downloads\\|\\Temp\\|\\Telechargements|\\Téléchargements'
        return @{ niveau = 2; raison = $(if ($tel) { 'script situé dans un dossier de téléchargement' } else { 'exécuter un script' }) }
    }
    if ($def.niveau -is [scriptblock]) { return @{ niveau = (& $def.niveau $a); raison = $def.raison } }
    return @{ niveau = [int]$def.niveau; raison = $def.raison }
}
