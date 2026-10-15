# Synchro CHIFFRÉE du .env entre le PC principal et le serveur, via le dépôt GitHub privé : seul .env.chiffre est suivi par git, jamais .env.
# Chiffrement : AES-256-CBC + HMAC-SHA256 (« chiffrer puis authentifier » : toute altération ou mauvais mot de passe est détecté AVANT le déchiffrement), clés dérivées du mot de passe
# par PBKDF2-HMAC-SHA256 (600 000 itérations, sel aléatoire de 16 octets), IV aléatoire. Le mot de passe n'est jamais affiché, jamais écrit en clair, jamais dans le dépôt :
#   PC principal : saisi à chaque fois (saisie masquée) ; serveur : saisi UNE fois par installer-serveur.ps1, puis gardé protégé par DPAPI (lié au compte Windows) HORS du dépôt.
# Format de .env.chiffre (texte, 6 lignes) : JARVIS-ENV-V1 / iter=… / sel=… / iv=… / donnees=… / mac=…   (base64 ; aucune ligne du .env en clair).
$script:EnvIterations = 600000
if ($env:JARVIS_TEST -eq '1' -and $env:JARVIS_ENV_ITER_TEST -match '^\d{4,7}$') { $script:EnvIterations = [int]$env:JARVIS_ENV_ITER_TEST }      # (tests seulement : chiffrer plus vite ; jamais en production)
$script:EnvEntete = 'JARVIS-ENV-V1'
function Get-FichierMotDePasseServeur {
    # Emplacement du mot de passe protégé par DPAPI (HORS du dépôt). JARVIS_ENV_MDP_FICHIER le remplace (tests).
    if ($env:JARVIS_ENV_MDP_FICHIER) { return $env:JARVIS_ENV_MDP_FICHIER }
    Join-Path $env:LOCALAPPDATA 'Jarvis\env-mdp.dpapi'
}
function Clear-Octets($b) { if ($b -is [byte[]]) { [Array]::Clear($b, 0, $b.Length) } }
function ConvertTo-OctetsMotDePasse([securestring]$s) {
    $p = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($s)
    try { [Text.Encoding]::UTF8.GetBytes([Runtime.InteropServices.Marshal]::PtrToStringBSTR($p)) } finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($p) }
}
function ConvertTo-SecureDepuisTexte([string]$t) { $s = New-Object System.Security.SecureString; foreach ($c in $t.ToCharArray()) { $s.AppendChar($c) }; $s.MakeReadOnly(); $s }
function Read-MotDePasseSaisie([string]$invite) {
    # Saisie MASQUÉE (jamais affichée). Seul un test (JARVIS_TEST=1) peut fournir le mot de passe par JARVIS_ENV_MDP_TEST.
    if ($env:JARVIS_TEST -eq '1' -and $env:JARVIS_ENV_MDP_TEST) { return (ConvertTo-SecureDepuisTexte $env:JARVIS_ENV_MDP_TEST) }
    Read-Host $invite -AsSecureString
}
function Get-ClesEnv([byte[]]$mdp, [byte[]]$sel, [int]$iter) {
    $kdf = [Security.Cryptography.Rfc2898DeriveBytes]::new($mdp, $sel, $iter, [Security.Cryptography.HashAlgorithmName]::SHA256)
    try { $k = $kdf.GetBytes(64) } finally { $kdf.Dispose() }
    @{ enc = [byte[]]$k[0..31]; mac = [byte[]]$k[32..63] }
}
function Get-MacEnv([byte[]]$cleMac, [int]$iter, [byte[]]$sel, [byte[]]$iv, [byte[]]$ct) {
    $h = New-Object Security.Cryptography.HMACSHA256 -ArgumentList (, $cleMac)
    try { $h.ComputeHash([byte[]](@([Text.Encoding]::UTF8.GetBytes("$script:EnvEntete|$iter|")) + $sel + $iv + $ct)) } finally { $h.Dispose() }
}
function Test-OctetsEgaux([byte[]]$a, [byte[]]$b) {
    # Comparaison en temps constant.
    if ($a.Length -ne $b.Length) { return $false }
    $d = 0; for ($i = 0; $i -lt $a.Length; $i++) { $d = $d -bor ($a[$i] -bxor $b[$i]) }
    $d -eq 0
}
function Protect-EnvOctets([byte[]]$clair, [byte[]]$mdp, [int]$iter = 0) {
    if ($iter -le 0) { $iter = $script:EnvIterations }
    $rng = New-Object Security.Cryptography.RNGCryptoServiceProvider
    $sel = New-Object byte[] 16; $iv = New-Object byte[] 16; $rng.GetBytes($sel); $rng.GetBytes($iv); $rng.Dispose()
    $cles = Get-ClesEnv $mdp $sel $iter
    $aes = [Security.Cryptography.Aes]::Create(); $aes.KeySize = 256; $aes.Mode = 'CBC'; $aes.Padding = 'PKCS7'; $aes.Key = $cles.enc; $aes.IV = $iv
    try { $ct = $aes.CreateEncryptor().TransformFinalBlock($clair, 0, $clair.Length) } finally { $aes.Dispose() }
    $mac = Get-MacEnv $cles.mac $iter $sel $iv $ct
    Clear-Octets $cles.enc; Clear-Octets $cles.mac
    (@($script:EnvEntete, "iter=$iter", "sel=$([Convert]::ToBase64String($sel))", "iv=$([Convert]::ToBase64String($iv))", "donnees=$([Convert]::ToBase64String($ct))", "mac=$([Convert]::ToBase64String($mac))") -join "`n") + "`n"
}
function Unprotect-EnvTexte([string]$texte, [byte[]]$mdp) {
    # @{ ok; octets; raison }. Une altération et un mauvais mot de passe donnent le MÊME message (aucune information en plus).
    $echec = { param($r) @{ ok = $false; octets = $null; raison = $r } }
    $l = @("$texte" -split "`r?`n" | Where-Object { $_.Trim() })
    if ($l.Count -ne 6 -or $l[0].Trim() -ne $script:EnvEntete) { return (& $echec 'format inconnu ou fichier incomplet') }
    $v = @{}; foreach ($x in $l[1..5]) { $i = $x.IndexOf('='); if ($i -lt 1) { return (& $echec 'format inconnu ou fichier incomplet') }; $v[$x.Substring(0, $i)] = $x.Substring($i + 1).Trim() }
    foreach ($k in 'iter', 'sel', 'iv', 'donnees', 'mac') { if (-not $v.ContainsKey($k)) { return (& $echec 'format inconnu ou fichier incomplet') } }
    try {
        $iter = [int]$v['iter']; $sel = [Convert]::FromBase64String($v['sel']); $iv = [Convert]::FromBase64String($v['iv']); $ct = [Convert]::FromBase64String($v['donnees']); $mac = [Convert]::FromBase64String($v['mac'])
    } catch { return (& $echec 'format inconnu ou fichier incomplet') }
    if ($iter -lt 1000 -or $iter -gt 5000000 -or $sel.Length -ne 16 -or $iv.Length -ne 16 -or $mac.Length -ne 32 -or $ct.Length -lt 16 -or ($ct.Length % 16) -ne 0) { return (& $echec 'format inconnu ou fichier incomplet') }
    $cles = Get-ClesEnv $mdp $sel $iter
    try {
        $calc = Get-MacEnv $cles.mac $iter $sel $iv $ct
        if (-not (Test-OctetsEgaux $calc $mac)) { return (& $echec 'mot de passe incorrect ou fichier altéré') }      # jamais de déchiffrement avant la vérification
        $aes = [Security.Cryptography.Aes]::Create(); $aes.KeySize = 256; $aes.Mode = 'CBC'; $aes.Padding = 'PKCS7'; $aes.Key = $cles.enc; $aes.IV = $iv
        try { $clair = $aes.CreateDecryptor().TransformFinalBlock($ct, 0, $ct.Length) } finally { $aes.Dispose() }
        @{ ok = $true; octets = $clair; raison = '' }
    } catch { & $echec 'mot de passe incorrect ou fichier altéré' }
    finally { Clear-Octets $cles.enc; Clear-Octets $cles.mac }
}
# ---------- Mot de passe du serveur : protégé par DPAPI (lié au compte Windows de CE PC), hors du dépôt ----------
function Save-MotDePasseDpapi([securestring]$mdp, [string]$chemin = '') {
    if (-not $chemin) { $chemin = Get-FichierMotDePasseServeur }
    $d = Split-Path $chemin; if ($d -and -not (Test-Path $d)) { New-Item -ItemType Directory $d -Force | Out-Null }
    [IO.File]::WriteAllText($chemin, (ConvertFrom-SecureString $mdp), [Text.UTF8Encoding]::new($false))      # DPAPI (compte courant) : illisible sur un autre compte ou un autre PC
}
function Read-MotDePasseDpapi([string]$chemin = '') {
    # Octets du mot de passe, ou $null s'il est absent / illisible (autre compte Windows).
    if (-not $chemin) { $chemin = Get-FichierMotDePasseServeur }
    if (-not (Test-Path $chemin)) { return $null }
    try { ConvertTo-OctetsMotDePasse (ConvertTo-SecureString ((Get-Content $chemin -Raw -Encoding UTF8).Trim())) } catch { $null }
}
# ---------- Déchiffrement vers .env (atomique, avec sauvegarde .env.bak) ----------
function Restore-EnvDepuisChiffre([string]$racine, [byte[]]$mdp) {
    # @{ statut : 'absent' | 'cree' | 'mis-a-jour' | 'inchange' | 'echec' ; raison }. En cas d'échec, l'ancien .env n'est JAMAIS touché.
    $chif = Join-Path $racine '.env.chiffre'; $dest = Join-Path $racine '.env'
    if (-not (Test-Path $chif)) { return @{ statut = 'absent'; raison = '.env.chiffre absent' } }
    if (-not $mdp) { return @{ statut = 'echec'; raison = 'mot de passe du serveur absent (relancez installer-serveur.ps1)' } }
    $r = Unprotect-EnvTexte (Get-Content $chif -Raw -Encoding UTF8) $mdp
    if (-not $r.ok) { return @{ statut = 'echec'; raison = $r.raison } }
    try {
        if ((Test-Path $dest) -and (Test-OctetsEgaux ([IO.File]::ReadAllBytes($dest)) $r.octets)) { Clear-Octets $r.octets; return @{ statut = 'inchange'; raison = '' } }
        $tmp = "$dest.tmp"; [IO.File]::WriteAllBytes($tmp, $r.octets)
        if (Test-Path $dest) { [IO.File]::Replace($tmp, $dest, "$dest.bak"); $st = 'mis-a-jour' } else { Move-Item $tmp $dest -Force; $st = 'cree' }
        Clear-Octets $r.octets
        @{ statut = $st; raison = '' }
    } catch { Remove-Item "$dest.tmp" -Force -ErrorAction SilentlyContinue; @{ statut = 'echec'; raison = 'écriture de .env impossible' } }
}
function Initialize-EnvDepuisChiffre([string]$racine) {
    # Premier démarrage : si .env n'existe pas et que .env.chiffre et le mot de passe du serveur existent, .env est créé. Sinon rien ne change.
    if ((Test-Path (Join-Path $racine '.env')) -or -not (Test-Path (Join-Path $racine '.env.chiffre'))) { return @{ statut = 'rien'; raison = '' } }
    $m = Read-MotDePasseDpapi; try { Restore-EnvDepuisChiffre $racine $m } finally { Clear-Octets $m }
}
