# Test du coffre Bitwarden : la fenêtre de déverrouillage ne bloque JAMAIS Jarvis ; le mot de passe maître ne passe pas par Jarvis.
# Code de sortie 0 = réussi.  -SansReel : saute le vrai lancement de Jarvis (qui ouvre la vraie fenêtre de déverrouillage pendant ~30 s).
param([switch]$SansReel)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $Root 'lib\journal.ps1')
$Config = Get-Content (Join-Path $Root 'config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($l in 'voix', 'business', 'permissions', 'actions', 'coffre', 'entrees', 'ecrans', 'tableau', 'visage', 'sons', 'raccourcis', 'cerveau', 'cerveau-local', 'veille', 'memoire', 'rapide', 'discretion', 'modejeu', 'boucle') { . (Join-Path $Root "lib\$l.ps1") }
$echecs = 0
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }
function JournalTexte { (Get-ChildItem (Join-Path $Root 'logs') -Filter 'journal-*.md' | Sort-Object Name | Select-Object -Last 1 | ForEach-Object { Get-Content $_.FullName -Raw -Encoding UTF8 }) }
function Attendre([int]$ms) { $t = (Get-Date).AddMilliseconds($ms); while ((Get-Date) -lt $t) { Invoke-Pump; Start-Sleep -Milliseconds 20 } }
$script:Dits = @(); function Parler([string]$Texte, $Langue) { $script:Dits += $Texte }

Write-Host '1) Le mot de passe principal ne passe pas par Jarvis (vérifications statiques)'
$parent = Get-Content (Join-Path $Root 'lib\coffre.ps1') -Raw -Encoding UTF8
$enfant = Get-Content (Join-Path $Root 'lib\coffre-dialogue.ps1') -Raw -Encoding UTF8
Verifier ($parent -notmatch 'ShowDialog|Windows\.Forms\.Form|JARVIS_BW_PWD|UseSystemPasswordChar') 'coffre.ps1 (Jarvis) ne contient ni fenêtre, ni champ de mot de passe, ni variable de mot de passe'
Verifier ($enfant -match 'ShowDialog' -and $enfant -match 'JARVIS_BW_PWD' -and $enfant -match '--passwordenv') 'la fenêtre vit dans un processus séparé et passe le mot de passe à bw par variable d''environnement'
Verifier ($enfant -notmatch 'Set-Content|Add-Content|Out-File|Write-Journal|Export-|>>') 'le processus de la fenêtre n''écrit rien sur le disque ni dans le journal'
$sorties = [regex]::Matches($enfant, 'Write-Output\s+(.+)') | ForEach-Object { $_.Groups[1].Value }
Verifier (-not ($sorties | Where-Object { $_ -match 'pwd|mot de passe' -and $_ -notmatch 'ERREUR|ANNULE' })) 'il ne renvoie à Jarvis que : SESSION / ERREUR / ANNULE (jamais le mot de passe)'
Verifier ($enfant -match '\.Replace\(\$pwd2, ''\[SECRET\]''\)') 'les messages d''erreur sont purgés du mot de passe avant d''être renvoyés'

Write-Host '2) bw simulé : le mot de passe voyage par l''environnement, jamais par les arguments'
$fausse = Join-Path $env:TEMP ('fausse-bw-' + [guid]::NewGuid().ToString('N').Substring(0, 6)); New-Item -ItemType Directory $fausse | Out-Null
@"
@echo off
echo %* > "$fausse\args.txt"
echo %JARVIS_BW_PWD%| find /c /v "" > nul
set /a n=0
if defined JARVIS_BW_PWD (echo present > "$fausse\env.txt") else (echo absent > "$fausse\env.txt")
echo FAUX_JETON_SESSION_1234567890
"@ | Set-Content (Join-Path $fausse 'bw.cmd') -Encoding ASCII
$ancienPath = $env:Path; $env:Path = "$fausse;$env:Path"
try {
    $ast = [Management.Automation.Language.Parser]::ParseInput($enfant, [ref]$null, [ref]$null)
    foreach ($fn in $ast.FindAll({ param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] }, $true)) { . ([scriptblock]::Create($fn.Extent.Text)) }
    $mdp = 'MotDePasseMaitre-Tres-Secret-42!'
    $r = Invoke-BwLocal @('unlock', '--passwordenv', 'JARVIS_BW_PWD', '--raw') @{ JARVIS_BW_PWD = $mdp } 30
    $args1 = Get-Content (Join-Path $fausse 'args.txt') -Raw
    Verifier ($r.out -match 'FAUX_JETON_SESSION_1234567890') 'bw (simulé) renvoie son jeton de session'
    Verifier ($args1 -notmatch [regex]::Escape($mdp) -and $args1 -match '--passwordenv') 'le mot de passe n''est PAS dans les arguments de bw (seulement le NOM de la variable)'
    Verifier ((Get-Content (Join-Path $fausse 'env.txt') -Raw) -match 'present') 'il est bien fourni à bw par l''environnement du processus fils'
    Verifier (-not [Environment]::GetEnvironmentVariable('JARVIS_BW_PWD', 'Process') -and -not [Environment]::GetEnvironmentVariable('JARVIS_BW_PWD', 'User')) 'et n''est défini dans aucun environnement durable'
} finally { $env:Path = $ancienPath; Remove-Item $fausse -Recurse -Force -ErrorAction SilentlyContinue; $script:BwCmd = $null }   # oublie le chemin du faux bw

Write-Host '3) Fenêtre ouverte : la boucle de Jarvis ne s''arrête pas'
$script:Entrees.Clear(); Remove-Item $script:StopFlag -ErrorAction SilentlyContinue
$t0 = Get-Date; $txt = Start-CoffreDialogue 'locked' 'ANNULE' 4; $dtLancement = ((Get-Date) - $t0).TotalMilliseconds
Verifier ($dtLancement -lt 2500 -and $script:CoffreProc -and -not $script:CoffreProc.HasExited) ("l'ouverture rend la main aussitôt ({0:N0} ms) : la fenêtre attend, pas Jarvis" -f $dtLancement)
$maxIter = 0; $traites = 0; $stopOk = $false; $dep = Get-Date
while (((Get-Date) - $dep).TotalSeconds -lt 3.2) {
    $a = Get-Date; Invoke-Pump; $e = Get-Entree; if ($e) { $traites++ }
    if (((Get-Date) - $dep).TotalSeconds -gt 0.8 -and $traites -eq 0) { $script:Entrees.Enqueue(@{ src = 'clavier'; texte = 'ordre pendant la fenêtre'; entendu = $false }) }
    if (((Get-Date) - $dep).TotalSeconds -gt 1.6 -and -not $stopOk) { Set-Content $script:StopFlag 'x'; $c = Get-Date; $stopOk = (Test-Stop); $dt = ((Get-Date) - $c).TotalMilliseconds; Remove-Item $script:StopFlag -ErrorAction SilentlyContinue }
    $d = ((Get-Date) - $a).TotalMilliseconds; if ($d -gt $maxIter) { $maxIter = $d }; Start-Sleep -Milliseconds 40
}
Verifier ($maxIter -lt 400) ("la boucle principale tourne pendant l'attente : itération la plus lente {0:N0} ms" -f $maxIter)
Verifier ($traites -ge 1) 'un ordre arrivé pendant que la fenêtre est ouverte est bien reçu'
Verifier ($stopOk) 'l''arrêt d''urgence reste détecté pendant que la fenêtre est ouverte'
Verifier ((Start-CoffreDialogue 'locked') -match 'déjà ouverte') 'une deuxième ouverture est refusée (une seule fenêtre)'
Attendre 2500
Verifier ($null -eq $script:CoffreProc) 'la fenêtre fermée (« Plus tard ») est détectée'
Verifier ((JournalTexte) -match 'reporté par Liam' -and $script:Entrees.Count -eq 0 -and -not $script:BwSession) '« Plus tard » : aucun jeton, aucune annonce, simple note au journal'

Write-Host '4) Réussite et échec du déverrouillage'
$script:Dits = @(); $tok = 'FAUXJETONSESSION1234567890ABCDEF'
[void](Start-CoffreDialogue 'locked' "SESSION:$tok" 1); Attendre 2500
Verifier ($script:BwSession -eq $tok) 'réussite : le jeton de session est gardé EN MÉMOIRE'
$j = JournalTexte
Verifier ($j -match 'session gardée en mémoire seulement' -and $j -notmatch [regex]::Escape($tok)) 'le journal note la réussite mais pas le jeton'
Verifier ((Hide-Secrets "x $tok y") -notmatch [regex]::Escape($tok)) 'le jeton est ajouté aux secrets masqués'
$e = $script:Entrees.ToArray() | Where-Object { $_.texte -like '[[]coffre]*' } | Select-Object -First 1
Verifier ($e -ne $null) 'une annonce système est mise en file (traitée par la boucle)'
$script:Entrees.Clear(); if ($e) { Invoke-Entree $e }
Verifier (($script:Dits -join '|') -eq 'Coffre déverrouillé, monsieur.') 'Jarvis dit seulement : « Coffre déverrouillé, monsieur. »'
$script:BwSession = $null; $script:Dits = @(); $script:Secrets = @()
[void](Start-CoffreDialogue 'locked' 'ERREUR:Invalid master password' 1); Attendre 2500
$e = $script:Entrees.ToArray() | Where-Object { $_.texte -like '[[]coffre]*' } | Select-Object -First 1; $script:Entrees.Clear(); if ($e) { Invoke-Entree $e }
Verifier (-not $script:BwSession -and ($script:Dits -join '|') -match 'a échoué' -and (JournalTexte) -match 'échec : Invalid master password') 'échec : pas de jeton, message clair, aucune boucle de relance'

Write-Host '5) « Le coffre est verrouillé, monsieur » : une seule fois'
$script:Dits = @(); $script:CoffreAnnonce = $false; $script:Lances = 0
function Initialize-Coffre { 'locked' }; function Start-CoffreDialogue([string]$e = '') { $script:Lances++; 'ok' }
1..3 | ForEach-Object { Invoke-CoffreDemarrage }
Verifier (@($script:Dits | Where-Object { $_ -eq 'Le coffre est verrouillé, monsieur.' }).Count -eq 1) 'annoncé une seule fois, même si le démarrage est rejoué'
Verifier ($script:Lances -eq 3) 'la fenêtre, elle, peut être rouverte sans nouvelle annonce'
$Config.coffre_au_demarrage = $false; $script:Dits = @(); $script:CoffreAnnonce = $false; Invoke-CoffreDemarrage
Verifier ($script:Dits.Count -eq 0) 'coffre_au_demarrage = false : silence complet'
$Config.coffre_au_demarrage = $true

Write-Host '6) Vrai lancement de Jarvis (sans -SansCoffre) pendant que la fenêtre est ouverte'
if ($SansReel) { Write-Host '  (sauté : -SansReel)' }
else {
    Add-Type -TypeDefinition 'using System; using System.Runtime.InteropServices; public class FrC { [DllImport("user32.dll")] static extern void keybd_event(byte v, byte s, uint f, UIntPtr e); public static void Combo(params byte[] t){ foreach(byte b in t){ keybd_event(b,0,0,UIntPtr.Zero); System.Threading.Thread.Sleep(30);} for(int i=t.Length-1;i>=0;i--){ keybd_event(t[i],0,2,UIntPtr.Zero); System.Threading.Thread.Sleep(30);} } }'
    $sauve = Join-Path $env:TEMP ('jarvis-memoire-sauvegarde-' + [guid]::NewGuid().ToString('N').Substring(0, 6)); Copy-Item (Join-Path $Root 'memoire') $sauve -Recurse
    $pj = $null
    try {
        Remove-Item (Join-Path $Root 'memoire\jarvis.pid') -ErrorAction SilentlyContinue
        $jDebut = (JournalTexte).Length                          # on ne regarde QUE ce que ce lancement écrit
        $etat = try { ((Invoke-Bw @('status')).sortie | ConvertFrom-Json).status } catch { 'inconnu' }
        Write-Host "  (état Bitwarden réel : $etat)"
        if ($etat -notin 'locked', 'unauthenticated') { Write-Host '  (coffre déjà déverrouillé ou absent : la fenêtre ne s''ouvrira pas, vérification partielle)' }
        $pj = Start-Process powershell -ArgumentList '-NoProfile', '-ExecutionPolicy', 'Bypass', '-WindowStyle', 'Hidden', '-File', (Join-Path $Root 'jarvis.ps1') -PassThru
        $fin = (Get-Date).AddSeconds(90); $ok = $false
        while ((Get-Date) -lt $fin) { Start-Sleep -Seconds 1; $nouveau = (JournalTexte).Substring($jDebut); if ($nouveau -match 'Écoute vocale démarrée' -and $nouveau -match 'fenêtre de déverrouillage ouverte') { $ok = $true; break } }
        Start-Sleep -Seconds 2
        $enfants = @(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'coffre-dialogue\.ps1' })
        Write-Host "  (processus de fenêtre vus : $($enfants.Count) ; PID Jarvis $($pj.Id))"
        if ($etat -in 'locked', 'unauthenticated') {
            Verifier ($ok) 'Jarvis démarre ET ouvre la fenêtre de déverrouillage'
            Verifier ($enfants.Count -ge 1) 'la fenêtre est un processus séparé, ouvert'
        }
        $j0 = (JournalTexte).Length
        Start-Sleep -Seconds 12                                   # le briefing parle pendant que la fenêtre est ouverte
        [FrC]::Combo(0x12, 0x6D); Start-Sleep -Seconds 2          # Alt + « − » pendant que la fenêtre est ouverte
        $jr = (JournalTexte).Substring($jDebut)
        Verifier ((JournalTexte).Substring($j0) -match 'Jarvis en SOURDINE') 'le raccourci Alt+« − » répond pendant que la fenêtre attend (la boucle n''est pas bloquée)'
        [FrC]::Combo(0x12, 0x6B); Start-Sleep -Seconds 2
        Verifier ((JournalTexte).Substring($j0) -match 'Jarvis ACTIVÉ') 'et Alt+« + » aussi'
        Verifier ((([regex]::Matches($jr, 'Le coffre est verrouillé, monsieur\.')).Count) -eq 1 -or $etat -notin 'locked', 'unauthenticated') '« Le coffre est verrouillé, monsieur » : dit exactement une fois pendant ce lancement'
        Verifier ($jr -notmatch 'MotDePasse|JARVIS_BW_PWD') 'aucun mot de passe dans le journal'
    } finally {
        & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Root 'arreter.ps1') 2>&1 | Out-Null
        Start-Sleep -Seconds 2
        $reste = @(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'coffre-dialogue\.ps1|Jarvis\\jarvis\.ps1' })
        Verifier ($reste.Count -eq 0) 'à l''arrêt de Jarvis, la fenêtre de déverrouillage est fermée aussi (aucun processus restant)'
        $reste | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
        # la session de test ne doit pas laisser de trace dans VOTRE mémoire : on la restaure
        Get-ChildItem (Join-Path $Root 'memoire') -File | Where-Object { $_.Name -ne 'jarvis.pid' } | Remove-Item -Force -ErrorAction SilentlyContinue
        Copy-Item (Join-Path $sauve '*') (Join-Path $Root 'memoire') -Force
        Remove-Item $sauve -Recurse -Force -ErrorAction SilentlyContinue
    }
}

if ($echecs) { Write-Host "`nÉCHEC : $echecs vérification(s) en échec." -ForegroundColor Red; exit 1 }
Write-Host "`nRÉUSSI"; exit 0
