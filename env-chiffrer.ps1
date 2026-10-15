# PC PRINCIPAL : chiffre .env en .env.chiffre (le SEUL fichier de clés suivi par git ; .env reste dans .gitignore).
#   powershell -ExecutionPolicy Bypass -File env-chiffrer.ps1            chiffre .env -> .env.chiffre
#   powershell -ExecutionPolicy Bypass -File env-chiffrer.ps1 -Commit    ... puis commit de .env.chiffre SEUL et affichage de la commande « git push » (vous poussez vous-même)
#   powershell -ExecutionPolicy Bypass -File jarvis.ps1 env-pousser      même chose : LE geste à faire quand vous changez une clé
# Le mot de passe est demandé (saisie masquée, deux fois) : jamais affiché, jamais écrit sur disque, jamais dans le dépôt. Aucune clé n'est affichée. Détails : lib\env-chiffre.ps1.
param([switch]$Commit, [string]$Racine = $PSScriptRoot)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'lib\env-chiffre.ps1')
$envF = Join-Path $Racine '.env'; $chif = Join-Path $Racine '.env.chiffre'
if (-not (Test-Path $envF)) { Write-Host "Aucun .env dans $Racine : rien à chiffrer."; exit 1 }
$m1 = Read-MotDePasseSaisie 'Mot de passe de chiffrement du .env (10 caractères au moins)'
$b1 = ConvertTo-OctetsMotDePasse $m1
if ($b1.Length -lt 10) { Write-Host 'Mot de passe trop court (10 caractères au moins) : rien n''a été chiffré.'; Clear-Octets $b1; exit 1 }
if (-not ($env:JARVIS_TEST -eq '1' -and $env:JARVIS_ENV_MDP_TEST)) {
    $b2 = ConvertTo-OctetsMotDePasse (Read-MotDePasseSaisie 'Confirmez le mot de passe')
    if (-not (Test-OctetsEgaux $b1 $b2)) { Write-Host 'Les deux saisies sont différentes : rien n''a été chiffré.'; Clear-Octets $b1; Clear-Octets $b2; exit 1 }
    Clear-Octets $b2
}
try {
    $clair = [IO.File]::ReadAllBytes($envF)
    $inchange = $false
    if (Test-Path $chif) { $ex = Unprotect-EnvTexte (Get-Content $chif -Raw -Encoding UTF8) $b1; if ($ex.ok -and (Test-OctetsEgaux $ex.octets $clair)) { $inchange = $true }; Clear-Octets $ex.octets }
    if ($inchange) { Write-Host '.env.chiffre est déjà à jour (même contenu, même mot de passe) : rien à changer.' }
    else {
        $texte = Protect-EnvOctets $clair $b1
        $v = Unprotect-EnvTexte $texte $b1      # contrôle d'aller-retour AVANT d'écrire quoi que ce soit
        if (-not $v.ok -or -not (Test-OctetsEgaux $v.octets $clair)) { Write-Host 'Contrôle d''aller-retour échoué : .env.chiffre n''a pas été écrit.'; exit 1 }
        Clear-Octets $v.octets
        $tmp = "$chif.tmp"; [IO.File]::WriteAllText($tmp, $texte, [Text.UTF8Encoding]::new($false))
        if (Test-Path $chif) { [IO.File]::Replace($tmp, $chif, "$chif.bak"); Remove-Item "$chif.bak" -Force -ErrorAction SilentlyContinue } else { Move-Item $tmp $chif -Force }      # remplacement atomique
        Write-Host '.env.chiffre écrit et vérifié (AES-256 + HMAC, clé dérivée par PBKDF2 600 000 itérations).'
    }
} finally { Clear-Octets $b1; Clear-Octets $clair }
if ($Commit) {
    if (-not (Test-Path (Join-Path $Racine '.git'))) { Write-Host 'Ce dossier n''est pas un dépôt git : faites d''abord « git init -b main » (voir le README), puis relancez.'; exit 0 }
    $ErrorActionPreference = 'Continue'
    & git -C $Racine add -- .env.chiffre 2>$null
    $diff = & git -C $Racine diff --cached --name-only -- .env.chiffre 2>$null
    if (-not $diff) { Write-Host 'Rien à commiter : .env.chiffre est identique à la version déjà commitée.' }
    else {
        & git -C $Racine commit -q -m 'Clés : mise à jour chiffrée (.env.chiffre)' -- .env.chiffre 2>$null
        if ($LASTEXITCODE -ne 0) { Write-Host 'Le commit a échoué (identité git absente ? : git config user.name / user.email).'; exit 1 }
        Write-Host 'Commit créé (seul .env.chiffre est dedans).'
    }
    Write-Host "Pour envoyer sur GitHub (c'est vous qui poussez) :`n    git push"
}
