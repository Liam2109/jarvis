# TESTS MANUELS — à lancer VOUS-MÊME, jamais par Claude ni par tests\tout.ps1.
# Ils ouvrent de VRAIES fenêtres (l'orbe, le tableau de bord, la fenêtre du coffre), regardent le focus et la barre des tâches, et peuvent
# faire du bruit. Pendant qu'ils tournent : ne cliquez pas dans d'autres fenêtres.
#   powershell -ExecutionPolicy Bypass -File tests\manuels.ps1 -Oui
param([switch]$Oui)
if (-not $Oui) {
    Write-Host 'Ces tests ouvrent de vraies fenêtres et peuvent faire du bruit. Relancez avec -Oui pour les exécuter :'
    Write-Host '  powershell -ExecutionPolicy Bypass -File tests\manuels.ps1 -Oui'; exit 2
}
$liste = @(
    @{ n = 'fenetres (tableau : PLEIN ÉCRAN sur l''écran choisi, principal par défaut)';          f = 'fenetres.ps1';  a = @('-Mode', 'tableau'); attendu = 0 }
    @{ n = 'fenetres (discret)';          f = 'fenetres.ps1';  a = @('-Mode', 'discret'); attendu = 0 }
    @{ n = 'affichage (tableau)';         f = 'affichage.ps1'; a = @('-Mode', 'tableau'); attendu = 0 }
    @{ n = 'affichage (discret)';         f = 'affichage.ps1'; a = @('-Mode', 'discret'); attendu = 0 }
    @{ n = 'coffre (fenêtre)';            f = 'coffre.ps1';    a = @();                   attendu = 0 }
    @{ n = 'majordome (Bloc-notes réel, bureau, presse-papiers)'; f = 'majordome-reel.ps1'; a = @(); attendu = 0 }
    @{ n = 'salle de marché (vraie fenêtre sur l''écran choisi)'; f = 'salle-reel.ps1'; a = @(); attendu = 0 }
    @{ n = 'Discord réel (vrai bot : message, confirmation ✅/❌, autre utilisateur ; Jarvis arrêté ; consignes envoyées DANS Discord)'; f = 'discord-reel.ps1'; a = @('-Oui'); attendu = 0 }
    @{ n = 'Voix réelle (VRAI SON : « test de voix », fin de phrase, pauses, chiffres ; Jarvis arrêté)'; f = 'voix-reel.ps1'; a = @('-Oui'); attendu = 0 }
    @{ n = 'sabotage (DOIT échouer)';     f = 'fenetres.ps1';  a = @('-Mode', 'discret'); attendu = 1; env = 'JARVIS_TEST_SABOTAGE' }
    @{ n = 'témoin blanc (DOIT échouer)'; f = 'affichage.ps1'; a = @('-Mode', 'discret'); attendu = 1; env = 'JARVIS_TEST_TEMOIN' }
)
$res = @()
foreach ($t in $liste) {
    if ($t.env) { Set-Item "Env:$($t.env)" '1' }
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $sortie = & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot $t.f) @($t.a) 2>&1 | Out-String; $code = $LASTEXITCODE
    if ($t.env) { Remove-Item "Env:$($t.env)" -ErrorAction SilentlyContinue }
    $nb = ([regex]::Matches($sortie, '(?m)^\s+OK ')).Count
    $res += [pscustomobject]@{ test = $t.n; resultat = $(if ($code -eq $t.attendu) { "VERT ($nb vérifications)" } else { "ROUGE (code $code)" }); duree = ('{0:N0} s' -f $sw.Elapsed.TotalSeconds) }
    if ($code -ne $t.attendu) { ($sortie -split "`n" | Where-Object { $_ -match 'ECHEC|ÉCHEC' }) | Select-Object -First 8 | ForEach-Object { Write-Host $_ } }
}
$res | Format-Table -AutoSize
if (@($res | Where-Object { $_.resultat -like 'ROUGE*' }).Count) { exit 1 }; Write-Host 'TOUT EST VERT.' -ForegroundColor Green; exit 0
