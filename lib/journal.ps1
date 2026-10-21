# Journal lisible : logs\journal-AAAA-MM-JJ.md + résumé quotidien memoire\resume.md
$script:JarvisRoot = Split-Path -Parent $PSScriptRoot
$script:RacineReelle = $script:JarvisRoot      # (les tests peuvent pointer JarvisRoot vers un dossier temporaire ; RacineReelle reste le vrai dossier)
$script:Secrets = @()
# MODE TEST (JARVIS_TEST=1, posé par les tests) : AUCUN effet réel — pas de son, de voix, de musique, de fenêtre, de micro, de touche,
# de changement de volume, d'application ou de site ouverts. Les tests travaillent aussi sur une COPIE de config.json (JARVIS_CONFIG).
function Get-DossierLogs {
    # En mode test sur le vrai dossier, le journal va dans %TEMP% : jamais de lignes de test (fausses menaces...) dans VOTRE journal.
    if ((Test-ModeTest) -and $script:JarvisRoot -eq $script:RacineReelle) { return (Join-Path $env:TEMP 'jarvis-test-logs') }
    Join-Path $script:JarvisRoot 'logs'
}
function Test-ModeTest { $env:JARVIS_TEST -eq '1' }
function Test-VoixActive {
    # voix_actif ("oui" pour l'activer ; absent ou autre = "non") : seule porte du micro. Désactivée, AUCUN processus d'écoute (ecoute.py, reveil.py) n'est lancé : ni mot de réveil, ni claquements, ni détection de voix.
    [bool]($Config -and $Config.PSObject.Properties['voix_actif'] -and "$($Config.voix_actif)".Trim().ToLower() -in @('oui', 'true', '1', 'on', 'yes'))
}
function Get-ConfigPath { if ($env:JARVIS_CONFIG -and (Test-Path $env:JARVIS_CONFIG)) { $env:JARVIS_CONFIG } else { Join-Path $script:JarvisRoot 'config.json' } }

# ---------- Configuration : config.json (suivi par git) + config.local.json (réglages PROPRES à cette machine, jamais suivi par git : serveur, modèle Ollama...) ----------
function Merge-ConfigObjet($base, $local) {
    # Les propriétés de $local écrasent celles de $base ; les objets sont fusionnés récursivement (on ne remplace pas tout un bloc pour une clé).
    foreach ($p in $local.PSObject.Properties) {
        $b = $base.PSObject.Properties[$p.Name]
        if ($b -and $b.Value -is [pscustomobject] -and $p.Value -is [pscustomobject]) { Merge-ConfigObjet $b.Value $p.Value }
        elseif ($b) { $b.Value = $p.Value }
        else { Add-Member -InputObject $base -NotePropertyName $p.Name -NotePropertyValue $p.Value }
    }
}
function Import-ConfigJarvis {
    $f = Get-ConfigPath
    $c = Get-Content $f -Raw -Encoding UTF8 | ConvertFrom-Json
    $loc = Join-Path (Split-Path -Parent $f) 'config.local.json'
    if (-not $env:JARVIS_CONFIG -and (Test-Path $loc)) {      # (les tests utilisent une copie de config.json : jamais le fichier local de la machine)
        try { Merge-ConfigObjet $c (Get-Content $loc -Raw -Encoding UTF8 | ConvertFrom-Json) } catch { }
    }
    $c
}
# MODE SERVEUR (config.json « mode_serveur » : true) : Jarvis tourne sans écran ni micro (vieux PC allumé 24 h/24) : ni HUD, ni plein écran, ni voix, ni musique, ni raccourcis, ni coffre ; Discord reste actif.
function Test-ModeServeur { [bool]($Config -and $Config.PSObject.Properties['mode_serveur'] -and $Config.mode_serveur -eq $true) }
$script:FauxMicroServeur = $null      # (tests : $true / $false)
function Get-MicroServeur {
    # Micro du serveur : serveur_micro = "non" (défaut : AUCUNE écoute, ni Whisper ni Vosk, aucune recherche de micro) | "oui" | "auto" (écoute seulement si un micro est branché). Mesuré une seule fois.
    if ($null -ne $script:FauxMicroServeur) { return [bool]$script:FauxMicroServeur }
    $v = $(if ($Config -and $Config.PSObject.Properties['serveur_micro']) { "$($Config.serveur_micro)".Trim().ToLowerInvariant() } else { 'non' })
    if ($v -in 'true', 'oui', '1', 'on') { return $true }; if ($v -ne 'auto') { return $false }      # tout sauf « auto » et « oui » : pas de micro (jamais de sondage du matériel)
    if ($null -eq $script:MicroDetecte) {
        $script:MicroDetecte = $false
        try { & python -I -c "import sounddevice as sd,sys; sys.exit(0 if any(d['max_input_channels']>0 for d in sd.query_devices()) else 1)" 2>$null; $script:MicroDetecte = ($LASTEXITCODE -eq 0) } catch { }
    }
    [bool]$script:MicroDetecte
}
$script:MicroDetecte = $null

function Get-FichierMemoire([string]$nom) {
    # Fichier de memoire\ (sous-dossiers permis). En test sur le vrai dossier : %TEMP%\jarvis-test-memoire, jamais votre vraie mémoire.
    if (Get-Command Get-Mem -ErrorAction SilentlyContinue) { $f = Get-Mem $nom }
    elseif ((Test-ModeTest) -and $script:JarvisRoot -eq $script:RacineReelle) { $f = Join-Path (Join-Path $env:TEMP 'jarvis-test-memoire') $nom }
    else { $f = Join-Path $script:JarvisRoot "memoire\$nom" }
    $d = Split-Path $f; if ($d -and -not (Test-Path $d)) { New-Item -ItemType Directory $d -Force | Out-Null }
    $f
}
function Read-JsonMemoire([string]$nom, $defaut = $null) {
    $f = Get-FichierMemoire $nom
    if (Test-Path $f) { try { return (Get-Content $f -Raw -Encoding UTF8 | ConvertFrom-Json) } catch {} }
    $defaut
}
function Save-JsonMemoire([string]$nom, $objet) {
    try { [IO.File]::WriteAllText((Get-FichierMemoire $nom), ($objet | ConvertTo-Json -Depth 6), [Text.UTF8Encoding]::new($false)) } catch {}
}

function Import-JarvisEnv {
    $p = Join-Path $script:JarvisRoot '.env'
    if (-not (Test-Path $p)) { return }
    foreach ($l in Get-Content $p -Encoding UTF8) {
        if ($l -match '^\s*#' -or $l -notmatch '^\s*([^=\s]+)\s*=\s*(.*)$') { continue }
        $nom = $Matches[1]; $v = $Matches[2].Trim().Trim('"')
        if ($v -like "$nom=*") { $v = $v.Substring($nom.Length + 1).Trim().Trim('"') }       # « NOM=NOM=valeur » (nom recopié dans la valeur) : toléré
        [Environment]::SetEnvironmentVariable($nom, $v, 'Process')
        if ($v.Length -ge 8 -and $v -notmatch '_xxx$|^xxx$') { $script:Secrets += $v }
    }
}

function Test-Luhn([string]$chiffres) {
    $s = 0; $alt = $false
    for ($k = $chiffres.Length - 1; $k -ge 0; $k--) { $d = [int][string]$chiffres[$k]; if ($alt) { $d *= 2; if ($d -gt 9) { $d -= 9 } }; $s += $d; $alt = -not $alt }
    ($s % 10) -eq 0
}

function Hide-Secrets([string]$t) {
    # Masque tout ce qui ne doit jamais être écrit : clés, jetons, mots de passe (même dits en phrase), cartes, IBAN, CVV, codes.
    if (-not $t) { return $t }
    foreach ($s in $script:Secrets) { $t = $t.Replace($s, '[SECRET]') }
    $t = $t -replace '\b(sk|rk|pk|whsec)_(live|test)_[A-Za-z0-9]+', '[SECRET]'
    $t = $t -replace 'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+', '[SECRET]'
    $t = $t -replace '[A-Za-z0-9_-]{23,28}\.[A-Za-z0-9_-]{6,7}\.[A-Za-z0-9_-]{27,}', '[SECRET]'      # jeton de bot Discord (forme : id.horodatage.signature)
    # « mon mot de passe Vercel est hunter2 », « le token : abc », « password = x »
    $t = $t -replace "(?i)\b(mot de passe|mdp|password|passwd|code secret|code pin|jeton|token|cl[ée] api|api[ _-]?key|secret)\b((?:\s+[^\s:=]+){0,3}?\s*(?:\b(?:est|c'est|is)\b|[:=])\s*)\S+", '$1$2[SECRET]'
    $t = $t -replace '(?i)(password|mot de passe|mdp|token|jeton|api[_-]?key|secret)(\s*[:=]\s*|\s+)\S+', '$1 [SECRET]'
    $t = $t -replace '(?i)(Bearer)\s+\S+', '$1 [SECRET]'
    # Données bancaires
    $t = $t -replace '(?i)\b(cvv|cvc|cryptogramme|code de s[ée]curit[ée])\s*[:=]?\s*\d{3,4}\b', '[CVV]'
    $t = $t -replace '(?i)\b(code pin|pin)\s*[:=]?\s*\d{4,8}\b', '[CODE]'
    $t = $t -replace '(?i)\b(bic|swift)\s*[:=]?\s*[A-Z0-9]{8,11}\b', '[BIC]'
    $t = $t -replace '(?i)\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]{4}){2,7}(?:[ ]?[A-Z0-9]{1,4})?\b', '[IBAN]'
    $t = $t -replace '\b[12]\s?\d{2}\s?(?:0[1-9]|1[0-2])\s?\d{2}\s?\d{3}\s?\d{3}\s?\d{2}\b', '[N° SÉCU]'
    $t = [regex]::Replace($t, '\b(?:\d[ -]?){12,18}\d\b', [Text.RegularExpressions.MatchEvaluator]{ param($m) $c = $m.Value -replace '[ -]', ''; if ($c.Length -ge 13 -and $c.Length -le 19 -and (Test-Luhn $c)) { '[CARTE]' } else { $m.Value } })
    $t
}
function Write-Journal {
    param([string]$Ordre = '-', [string]$Action = '-', [string]$Resultat = '-')
    $dir = Get-DossierLogs
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory $dir | Out-Null }
    $f = Join-Path $dir ("journal-{0}.md" -f (Get-Date -Format 'yyyy-MM-dd'))
    if (-not (Test-Path $f)) { "# Journal Jarvis - $(Get-Date -Format 'dd/MM/yyyy')`r`n" | Out-File $f -Encoding utf8 }
    $flat = { param($x) (Hide-Secrets "$x") -replace '\s*\r?\n\s*', ' ' }
    $e = "## {0}`r`n- **Ordre :** {1}`r`n- **Action :** {2}`r`n- **Résultat :** {3}`r`n" -f (Get-Date -Format 'HH:mm:ss'), (& $flat $Ordre), (& $flat $Action), (& $flat $Resultat)
    Add-Content $f $e -Encoding utf8
}

function Update-Resume {
    param([datetime]$Jour = (Get-Date))
    $f = Join-Path (Get-DossierLogs) ("journal-{0}.md" -f $Jour.ToString('yyyy-MM-dd'))
    if (-not (Test-Path $f)) { return }
    $txt = Get-Content $f -Raw -Encoding UTF8
    $n = ([regex]::Matches($txt, '(?m)^## \d\d:')).Count
    $err = ([regex]::Matches($txt, '(?mi)^- \*\*Résultat :\*\* (échec|erreur|refus)')).Count
    $ordres = [regex]::Matches($txt, '(?m)^- \*\*Ordre :\*\* (.+)$') | Where-Object { $_.Groups[1].Value.Trim() -ne '-' } | Select-Object -First 15 | ForEach-Object { "  - " + $_.Groups[1].Value }
    $res = Join-Path $script:JarvisRoot 'memoire\resume.md'
    if (-not (Test-Path $res)) { "# Résumés quotidiens Jarvis`r`n" | Out-File $res -Encoding utf8 }
    $marq = "## Résumé du " + $Jour.ToString('yyyy-MM-dd')
    $bloc = "$marq`r`n- Actions journalisées : $n`r`n- Échecs/refus : $err`r`n- Principaux ordres :`r`n" + ($ordres -join "`r`n") + "`r`n"
    $cur = Get-Content $res -Raw -Encoding UTF8
    $cur = [regex]::Replace($cur, "(?s)$([regex]::Escape($marq)).*?(?=\r?\n## |\z)", '')
    Set-Content $res ($cur.TrimEnd() + "`r`n`r`n" + $bloc) -Encoding utf8
}