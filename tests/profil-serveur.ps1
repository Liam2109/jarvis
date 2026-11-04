# Test SILENCIEUX du PROFIL SERVEUR de tests\tout.ps1 (lecture du texte du script seulement : rien n'est lancé).
# Vérifie : chaque série de la liste a sa ligne de revue (garde / SAUTÉE) ; seules les séries qui dépendent d'une voix, d'un écran, d'Edge ou du GPU sont sautées ;
# les séries du serveur ne le sont jamais ; le contrôle memoire\ est le seul assoupli ; le tableau est large ; logs\tests-dernier.txt est écrit.
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$echecs = 0
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }
$tt = Get-Content (Join-Path $Root 'tests\tout.ps1') -Raw -Encoding UTF8
$series = @([regex]::Matches($tt, "f = '([^']+\.ps1)' \}") | ForEach-Object { $_.Groups[1].Value })
Write-Host '1) Revue de chaque série'
Verifier ($series.Count -ge 55) "la liste compte $($series.Count) séries"
$sansRevue = @($series | Where-Object { $tt -notmatch ('(?m)^#\s+' + [regex]::Escape($_) + '\s+(garde|SAUTÉE)\s+\S') })
Verifier ($sansRevue.Count -eq 0) ('chaque série a une ligne de revue (garde / SAUTÉE + raison)' + $(if ($sansRevue.Count) { ' - manque : ' + ($sansRevue -join ', ') }))
$absentes = @($series | Where-Object { -not (Test-Path (Join-Path $Root "tests\$_")) })
Verifier ($absentes.Count -eq 0) ('chaque série de la liste existe sur le disque' + $(if ($absentes.Count) { ' - absent : ' + ($absentes -join ', ') }))
$revSautees = @([regex]::Matches($tt, '(?m)^#\s+(\S+\.ps1)\s+SAUTÉE\s') | ForEach-Object { $_.Groups[1].Value } | Sort-Object)
$dic = @([regex]::Matches($tt, "(?m)^\s+'([^']+\.ps1)' = '") | ForEach-Object { $_.Groups[1].Value } | Sort-Object)
Verifier (($revSautees -join ',') -eq ($dic -join ',') -and $dic.Count -gt 0) "les séries marquées SAUTÉE dans la revue sont exactement celles de la table des séries sautées ($($dic -join ', '))"
$dicOk = @('ecran.ps1', 'voix.ps1', 'pc.ps1', 'interface.ps1', 'interface-marche.ps1', 'bureau.ps1')
Verifier (@($dic | Where-Object { $_ -notin $dicOk }).Count -eq 0) 'seules les séries à voix / écran / Edge / GPU / micro sont sautables'

Write-Host '2) Ce que le serveur ne saute JAMAIS'
foreach ($f in 'cerveau.ps1', 'chemins.ps1', 'memoire.ps1', 'discord.ps1', 'sauvegarde.ps1', 'serveur.ps1', 'serveur-leger.ps1', 'prospection.ps1', 'instagram.ps1', 'devis.ps1', 'rendez-vous.ps1', 'appels-sid.ps1', 'b2b-serveur.ps1', 'profil-serveur.ps1') {
    Verifier (($f -in $series) -and ($f -notin $dic)) "$f : dans la liste et jamais sautée"
}

Write-Host '3) Profil, contrôles, sorties'
Verifier ($tt -match 'b2b\.local\.json' -and $tt -match "PSObject\.Properties\['serveur'\]" -and $tt -match '\[switch\]\$Serveur' -and $tt -match '\[switch\]\$Complet') 'le profil serveur s''active avec "serveur": true de b2b.local.json ou -Serveur ; -Complet force le profil normal'
Verifier ($tt -match 'if \(\$profilServeur\) \{ \$ctl \+= .{0,60}memoire') 'seul le contrôle memoire\ est assoupli en profil serveur'
Verifier ($tt -match "controle = 'config\.json inchangé" -and $tt -match "controle = '\.env inchangé'" -and $tt -match 'aucun processus Jarvis' -and $tt -match 'aucun fichier temporaire de test restant') 'config.json, .env, processus et fichiers temporaires restent contrôlés dans les deux profils'
Verifier ($tt -notmatch '\$Rapide -and') 'aucune série n''est écartée par -Rapide'
Verifier ($tt -match 'Out-String -Width 220') 'tableau final écrit avec Out-String -Width 220 (résultat en première colonne)'
Verifier ($tt -match 'tests-dernier\.txt' -and $tt -match 'WriteAllLines' -and $tt -match 'UTF8Encoding') 'logs\tests-dernier.txt : une ligne par série, UTF-8'
Verifier ((Get-Content (Join-Path $Root '.gitignore') -Raw) -match '(?m)^logs/') 'logs\ est ignoré par git (le fichier de résultat n''est jamais poussé)'
if ($echecs) { Write-Host "`nÉCHEC : $echecs vérification(s) en échec." -ForegroundColor Red; exit 1 }
Write-Host "`nRÉUSSI"; exit 0
