# Lance TOUS les tests SILENCIEUX de Jarvis et affiche un tableau final. Code de sortie 0 = tout est vert.
#   powershell -ExecutionPolicy Bypass -File tests\tout.ps1
#
# SILENCIEUX = aucun son, aucune voix, aucune musique, aucune fenêtre, aucun vol de focus, aucun changement de volume, aucune application ni site
# ouverts, aucune vraie touche, aucun accès au micro, aucun service Ollama. (JARVIS_TEST=1 neutralise ces effets dans les bibliothèques, et les
# tests utilisent des bouchons.) Les tests travaillent sur une COPIE temporaire de config.json (JARVIS_CONFIG), jamais sur votre vraie config.
# Les tests qui exigent de VRAIES fenêtres / de VRAIES touches ne sont pas ici : voir tests\manuels.ps1 (à lancer vous-même, si vous le voulez).
# Après les tests : contrôle que config.json et memoire\ n'ont pas bougé, que les fichiers temporaires sont nettoyés et qu'aucun processus
# Jarvis / orbe / écoute / Ollama ne reste.
param([switch]$Rapide)      # (-Rapide est accepté pour compatibilité : tous les tests de cette liste sont déjà silencieux)
$racine = Split-Path -Parent $PSScriptRoot
$liste = @(
    @{ n = 'ecran';                       f = 'ecran.ps1' }
    @{ n = 'briefing (Supabase, Stripe)'; f = 'briefing.ps1' }
    @{ n = 'veille';                      f = 'veille.ps1' }
    @{ n = 'memoire';                     f = 'memoire.ps1' }
    @{ n = 'cerveau';                     f = 'cerveau.ps1' }
    @{ n = 'competences';                 f = 'competences.ps1' }
    @{ n = 'rapide';                      f = 'rapide.ps1' }
    @{ n = 'discretion (alertes, micro)'; f = 'discretion.ps1' }
    @{ n = 'mode jeu';                    f = 'modejeu.ps1' }
    @{ n = 'sons';                        f = 'sons.ps1' }
    @{ n = 'raccourcis + sourdine';       f = 'raccourcis.ps1' }
    @{ n = 'musique + marché + veille';   f = 'marche.ps1' }
    @{ n = 'sources + priorité + 5 à voir'; f = 'sources.ps1' }
    @{ n = 'voix : ordres + diagnostic';  f = 'voix.ps1' }
    @{ n = 'routeur + compréhension libre'; f = 'routeur.ps1' }
    @{ n = 'contrôle du PC + rapidité + GPU'; f = 'pc.ps1' }
    @{ n = 'ton majordome + bureau + modes'; f = 'politesse.ps1' }
    @{ n = 'vitesse : étages, routeur, voix'; f = 'vitesse.ps1' }
    @{ n = 'fin de phrase (silences)'; f = 'silence.ps1' }
    @{ n = 'salle de marché (lecture seule)'; f = 'salle.ps1' }
    @{ n = 'interface (Edge sans fenêtre)'; f = 'interface.ps1' }
    @{ n = 'interface salle de marché (Edge sans fenêtre)'; f = 'interface-marche.ps1' }
    @{ n = 'briefing du matin';           f = 'matin.ps1' }
    @{ n = 'sauvegarde (sans .env)';      f = 'sauvegarde.ps1' }
    @{ n = 'Discord (pont, salons, confirmations, alertes, tableaux, humour)'; f = 'discord.ps1' }
    @{ n = 'voix naturelle (texte, pauses, fin d''audio, test de voix)'; f = 'voix-naturelle.ps1' }
    @{ n = 'vitesse V3 (diagnostic, fin adaptative, action d''abord, accusé, flux)'; f = 'vitesse-v3.ps1' }
    @{ n = 'serveur 24/7 (dépôt, installateur en simulation, mise à jour auto)'; f = 'serveur.ps1' }
    @{ n = 'veille + réveil vocal / claquements (PC principal, installateur en simulation)'; f = 'bureau.ps1' }
    @{ n = 'serveur léger (aucune écoute, Ollama déchargé, français, diag-serveur)'; f = 'serveur-leger.ps1' }
    @{ n = 'vitesse ressentie (suite filtrée, bruit, Ollama chaud sur ce PC)'; f = 'suivi.ps1' }
)
function Get-Instantane {
    $mem = Join-Path $racine 'memoire'
    @{ config = (Get-FileHash (Join-Path $racine 'config.json')).Hash
       memoire = (@(Get-ChildItem $mem -File -ErrorAction SilentlyContinue | Sort-Object Name | ForEach-Object { "$($_.Name):$($_.Length):$($_.LastWriteTimeUtc.Ticks)" }) -join '|')
       env = (Get-FileHash (Join-Path $racine '.env') -ErrorAction SilentlyContinue).Hash }
}
function Get-ProcessusJarvis { @(Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -ne $PID -and $_.CommandLine -match 'Jarvis\\jarvis\.ps1|jarvis\.ps1|ecoute\.py|reveil\.py|coffre-dialogue|jarvis-edge|JarvisOrb|ollama|pont-discord|faux-pont' -and $_.CommandLine -notmatch 'tests\\tout\.ps1' }) }

$avant = Get-Instantane
$procAvant = @(Get-ProcessusJarvis).Count
$copie = Join-Path $env:TEMP ("jarvis-config-test-{0}.json" -f [guid]::NewGuid().ToString('N'))
Copy-Item (Join-Path $racine 'config.json') $copie
$env:JARVIS_TEST = '1'; $env:JARVIS_CONFIG = $copie
$res = @()
try {
    foreach ($t in $liste) {
        $sw = [Diagnostics.Stopwatch]::StartNew()
        $args2 = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $PSScriptRoot $t.f))
        $sortie = & powershell @args2 2>&1 | Out-String; $code = $LASTEXITCODE
        $nb = ([regex]::Matches($sortie, '(?m)^\s+OK ')).Count
        $res += [pscustomobject]@{ test = $t.n; resultat = $(if ($code -eq 0) { "VERT ($nb vérifications)" } else { "ROUGE (code $code)" }); duree = ('{0:N0} s' -f $sw.Elapsed.TotalSeconds) }
        if ($code -ne 0) { Write-Host ("--- sortie de « {0} » (extrait des échecs) ---" -f $t.n) -ForegroundColor Red; ($sortie -split "`n" | Where-Object { $_ -match 'ECHEC|ÉCHEC|Exception|n.est pas reconnu' }) | Select-Object -First 8 | ForEach-Object { Write-Host $_ } }
    }
} finally {
    Remove-Item $copie -Force -ErrorAction SilentlyContinue
    Get-ChildItem $env:TEMP -Force -ErrorAction SilentlyContinue | Where-Object { $_.Name -like 'jarvis-test-*' -or $_.Name -like 'jarvis-config-test-*' -or $_.Name -like 'jarvis-faux-serveur*' } | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item Env:JARVIS_TEST, Env:JARVIS_CONFIG -ErrorAction SilentlyContinue
    Remove-Item (Join-Path $racine 'memoire\STOP.flag'), (Join-Path $racine 'memoire\parle.flag') -Force -ErrorAction SilentlyContinue
}
# Contrôles de propreté
$apres = Get-Instantane
$ctl = @()
$ctl += [pscustomobject]@{ controle = 'config.json inchangé (les tests ont utilisé une copie)'; ok = ($apres.config -eq $avant.config) }
$ctl += [pscustomobject]@{ controle = 'memoire\ inchangé (aucune écriture dans votre mémoire)'; ok = ($apres.memoire -eq $avant.memoire) }
$ctl += [pscustomobject]@{ controle = '.env inchangé'; ok = ($apres.env -eq $avant.env) }
$ctl += [pscustomobject]@{ controle = 'aucun processus Jarvis / orbe / écoute / Ollama créé ou resté'; ok = (@(Get-ProcessusJarvis).Count -le $procAvant) }
$ctl += [pscustomobject]@{ controle = 'aucun fichier temporaire de test restant'; ok = (@(Get-ChildItem $env:TEMP -Force -ErrorAction SilentlyContinue | Where-Object { $_.Name -like 'jarvis-test-*' -or $_.Name -like 'jarvis-config-test-*' }).Count -eq 0) }
Write-Host ''; $res | Format-Table -AutoSize
$ctl | ForEach-Object { Write-Host ("  {0}  {1}" -f $(if ($_.ok) { 'OK   ' } else { 'ECHEC' }), $_.controle) -ForegroundColor $(if ($_.ok) { 'Gray' } else { 'Red' }) }
Write-Host "`nTests manuels (vraies fenêtres / vraies touches), NON lancés ici : tests\manuels.ps1" -ForegroundColor DarkGray
$rouges = @($res | Where-Object { $_.resultat -like 'ROUGE*' }); $mauvais = @($ctl | Where-Object { -not $_.ok })
if ($rouges.Count -or $mauvais.Count) { Write-Host "ÉCHEC : $($rouges.Count) test(s) rouge(s), $($mauvais.Count) contrôle(s) en échec." -ForegroundColor Red; exit 1 }
Write-Host 'TOUT EST VERT.' -ForegroundColor Green; exit 0
