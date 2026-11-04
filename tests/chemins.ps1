# Test SILENCIEUX : la protection du dossier Jarvis (Test-CheminJarvis, Test-CheminSysteme) ne dépend pas de la forme du chemin.
# Cas du portable serveur : utilisateur « Serveur Liam » (avec espace), donc %TEMP% en nom court 8.3 (C:\Users\SERVEU~1\...) alors que Jarvis est en nom long.
# Aucun fichier de Jarvis n'est touché : tout se passe dans un dossier temporaire jetable.
$ErrorActionPreference = 'Stop'
$env:JARVIS_TEST = '1'
$Root = Split-Path -Parent $PSScriptRoot
$echecs = 0
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }
. (Join-Path $Root 'lib\journal.ps1')
. (Join-Path $Root 'lib\permissions.ps1')

$base = Join-Path $env:TEMP ('jarvis-test-chemins-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
$jar = Join-Path $base 'Dossier Jarvis Avec Espace'          # « Jarvis » sous un chemin avec espace
$dehors = Join-Path $base 'Autre Dossier Avec Espace'
New-Item -ItemType Directory $jar, "$jar\memoire", $dehors | Out-Null
'x' | Set-Content "$jar\memoire\notes.md"; 'x' | Set-Content "$dehors\fichier.txt"
try {
    $script:JarvisRoot = $jar
    Write-Host '1) Jarvis sous un chemin avec espace'
    Verifier (Test-CheminJarvis "$jar\memoire\notes.md") 'un fichier du dossier Jarvis est protégé'
    Verifier (Test-CheminJarvis $jar) 'le dossier Jarvis lui-même est protégé'
    Verifier (Test-CheminJarvis "$jar\n-existe-pas-encore\x.txt") 'un chemin pas encore créé, sous Jarvis, est protégé'
    Verifier (-not (Test-CheminJarvis "$dehors\fichier.txt")) 'un fichier voisin (hors Jarvis, avec espace aussi) n''est pas protégé'
    Verifier (-not (Test-CheminJarvis "$jar-voisin\x.txt")) 'un dossier dont le nom commence pareil n''est pas pris pour Jarvis'

    Write-Host '2) Forme courte 8.3 contre forme longue (la protection compare les deux)'
    $court = $null
    try { $court = (New-Object -ComObject Scripting.FileSystemObject).GetFolder($jar).ShortPath } catch { }
    if ($court -and $court -match '~\d' -and $court -ne $jar) {
        Write-Host "        (nom court trouvé : $(Split-Path $court -Leaf))"
        Verifier ((Get-CheminLong $court) -ieq (Get-CheminLong $jar)) 'Get-CheminLong : forme courte et forme longue donnent le même chemin'
        $script:JarvisRoot = $jar
        Verifier (Test-CheminJarvis "$court\memoire\notes.md") 'racine longue, chemin demandé en nom court : protégé'
        $script:JarvisRoot = $court
        Verifier (Test-CheminJarvis "$jar\memoire\notes.md") 'racine en nom court, chemin demandé en nom long : protégé'
        Verifier (Test-CheminJarvis "$court\pas-encore\x.txt") 'racine en nom court, chemin pas encore créé : protégé'
        Verifier (-not (Test-CheminJarvis "$dehors\fichier.txt")) 'racine en nom court : le dossier voisin n''est toujours pas protégé'
        $script:JarvisRoot = $jar
    } else { Write-Host '  (noms 8.3 désactivés sur ce volume : contrôle court / long ignoré)' -ForegroundColor DarkGray }
    Verifier ((Get-CheminLong 'C:\Windows\System32') -ieq 'C:\Windows\System32') 'un chemin déjà long reste inchangé'

    Write-Host '3) Dossiers système, quelle que soit l''écriture du profil'
    Verifier (Test-CheminSysteme $env:SystemRoot) 'le dossier Windows reste protégé'
    if ($env:USERPROFILE) { Verifier (Test-CheminSysteme $env:USERPROFILE) 'le dossier du profil utilisateur reste protégé'; Verifier (-not (Test-CheminSysteme $dehors)) 'un dossier de travail temporaire n''est pas un dossier système' }
} finally {
    Remove-Item $base -Recurse -Force -ErrorAction SilentlyContinue
}
if ($echecs) { Write-Host "`nÉCHEC : $echecs vérification(s) en échec." -ForegroundColor Red; exit 1 }
Write-Host "`nRÉUSSI"; exit 0
