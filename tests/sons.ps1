# Test des sons : jingle original, ducking (baisse vite / remonte doucement / ne coupe jamais), sourdine, réglages. Code de sortie 0 = réussi.
$ErrorActionPreference = 'Stop'
$env:JARVIS_TEST = '1'      # TEST SILENCIEUX : aucun son, aucune fenêtre, aucun micro, aucune touche, aucune action réelle (voir lib\journal.ps1)
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $Root 'lib\journal.ps1')
$Config = Get-Content (Get-ConfigPath) -Raw -Encoding UTF8 | ConvertFrom-Json
. (Join-Path $Root 'lib\voix.ps1'); . (Join-Path $Root 'lib\business.ps1'); . (Join-Path $Root 'lib\permissions.ps1'); . (Join-Path $Root 'lib\actions.ps1')
. (Join-Path $Root 'lib\entrees.ps1'); . (Join-Path $Root 'lib\ecrans.ps1'); . (Join-Path $Root 'lib\tableau.ps1'); . (Join-Path $Root 'lib\visage.ps1'); . (Join-Path $Root 'lib\sons.ps1'); . (Join-Path $Root 'lib\raccourcis.ps1')
$echecs = 0
# AUCUN son réel : lecteur factice (lib\sons.ps1, mode test) ; les fichiers de sons vivent dans %TEMP%, jamais dans sounds\ de Jarvis
$tmpSons = Join-Path $env:TEMP "jarvis-test-sons-$([guid]::NewGuid().ToString('N'))"; New-Item -ItemType Directory $tmpSons | Out-Null
$script:SonsDossier = $tmpSons
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }
function Attendre([int]$ms) { $t = (Get-Date).AddMilliseconds($ms); while ((Get-Date) -lt $t) { Invoke-Pump; Start-Sleep -Milliseconds 20 } }

Write-Host '1) Jingle généré en code'
$b = [JarvisJingle]::Generer()
$n = ($b.Length - 44) / 2; $dur = $n / 44100.0
Verifier ($dur -ge 1.8 -and $dur -le 2.4) ("durée ≈ 2 s : {0:N2} s" -f $dur)
Verifier ([Text.Encoding]::ASCII.GetString($b[0..3]) -eq 'RIFF' -and [Text.Encoding]::ASCII.GetString($b[8..11]) -eq 'WAVE') 'fichier WAV valide'
$s = New-Object 'int[]' $n; for ($i = 0; $i -lt $n; $i++) { $s[$i] = [BitConverter]::ToInt16($b, 44 + 2 * $i) }
$pic = ($s | ForEach-Object { [math]::Abs($_) } | Measure-Object -Maximum).Maximum / 32767.0
$rms = [math]::Sqrt((($s | ForEach-Object { [double]$_ * $_ } | Measure-Object -Sum).Sum / $n)) / 32767.0
$fin = ($s[($n - 441)..($n - 1)] | ForEach-Object { [math]::Abs($_) } | Measure-Object -Maximum).Maximum / 32767.0
Verifier ($pic -gt 0.3 -and $pic -le 0.95) ("pas de saturation, signal présent (crête {0:P0})" -f $pic)
Verifier ($rms -gt 0.02) ("jingle audible (RMS {0:P1})" -f $rms)
Verifier ($fin -lt 0.02) ("se termine dans le silence (10 ms finales : {0:P2})" -f $fin)
$b2 = [JarvisJingle]::Generer(); Verifier (-not (Compare-Object $b $b2)) 'génération déterministe (même jingle à chaque démarrage)'
$f = Get-FichierDemarrage
Verifier ($f.genere -or (Split-Path $f.fichier -Leaf) -match '^demarrage\.') ("fichier de démarrage choisi : " + (Split-Path $f.fichier -Leaf))

Write-Host '2) Ducking : fonction pure'
$base = 0.7; $bas = 0.14; $montee = 1.2
$v = $base; for ($t = 0; $t -lt 0.5; $t += 0.02) { $v = Get-VolumeSuivant $v $bas 0.02 $base $bas $montee }
Verifier ([math]::Abs($v - $bas) -lt 0.005) ("pendant la voix : 20 % du volume normal ({0:N2} / {1:N2})" -f $v, $base)
$v2 = $v; for ($t = 0; $t -lt 0.2; $t += 0.02) { $v2 = Get-VolumeSuivant $v2 $base 0.02 $base $bas $montee }
Verifier ($v2 -gt $bas -and $v2 -lt ($base * 0.55)) ("après 0,2 s de remontée on est encore bas : fondu doux ({0:N2})" -f $v2)
$v3 = $v; for ($t = 0; $t -lt 1.3; $t += 0.02) { $v3 = Get-VolumeSuivant $v3 $base 0.02 $base $bas $montee }
Verifier ([math]::Abs($v3 - $base) -lt 0.001) ("remonte exactement au volume normal en ≈ duree_fondu ({0:N2})" -f $v3)
$monotone = $true; $prev = $bas; $w = $bas; for ($t = 0; $t -lt 1.4; $t += 0.02) { $w = Get-VolumeSuivant $w $base 0.02 $base $bas $montee; if ($w -lt $prev - 1e-9) { $monotone = $false }; $prev = $w }
Verifier $monotone 'la remontée est continue (jamais de saut ni de pompage)'

Write-Host '3) Ducking sur un vrai lecteur (jamais coupé pendant la parole)'
$Config.volume_musique = 0.3; $Config.volume_pendant_voix = 0.2; $Config.duree_fondu = 1.0     # volume modeste pour le test
$tonalite = Join-Path $env:TEMP 'jarvis-test-tonalite.wav'
$ms = New-Object IO.MemoryStream; $bw = New-Object IO.BinaryWriter $ms; $sr = 22050; $nn = $sr * 8
$bw.Write([Text.Encoding]::ASCII.GetBytes('RIFF')); $bw.Write([int](36 + $nn * 2)); $bw.Write([Text.Encoding]::ASCII.GetBytes('WAVEfmt ')); $bw.Write([int]16); $bw.Write([int16]1); $bw.Write([int16]1); $bw.Write([int]$sr); $bw.Write([int]($sr * 2)); $bw.Write([int16]2); $bw.Write([int16]16); $bw.Write([Text.Encoding]::ASCII.GetBytes('data')); $bw.Write([int]($nn * 2))
for ($i = 0; $i -lt $nn; $i++) { $bw.Write([int16](9000 * [math]::Sin(2 * [math]::PI * 330 * $i / $sr))) }
$bw.Flush(); [IO.File]::WriteAllBytes($tonalite, $ms.ToArray())
Start-MusiqueDemarrage $tonalite
Attendre 500
Verifier ($script:Musique -ne $null) 'la musique démarre'
Verifier ([math]::Abs($script:Musique.Volume - 0.3) -lt 0.01) ("elle commence à volume NORMAL (volume_musique) : {0:N2}" -f $script:Musique.Volume)
$pos0 = $script:Musique.Position.TotalSeconds
Set-SonsParole $true; Attendre 700
Verifier ($script:Musique -ne $null -and $script:Musique.Position.TotalSeconds -gt $pos0) ("la musique CONTINUE de jouer pendant la parole (position {0:N1} s -> {1:N1} s)" -f $pos0, $script:Musique.Position.TotalSeconds)
Verifier ([math]::Abs($script:Musique.Volume - 0.06) -lt 0.012) ("pendant la parole : ≈ 20 % du volume normal ({0:N3})" -f $script:Musique.Volume)
Set-SonsParole $false; Attendre 250
$vm = $script:Musique.Volume
Verifier ($vm -gt 0.06 -and $vm -lt 0.2) ("la musique remonte doucement ({0:N3} après 0,25 s)" -f $vm)
Attendre 1200
Verifier ([math]::Abs($script:Musique.Volume - 0.3) -lt 0.012) ("puis retrouve le volume normal ({0:N3})" -f $script:Musique.Volume)

Write-Host '4) Sourdine et réglages'
Set-SonsSourdine $true
Verifier ($script:Musique -eq $null -and $script:Ambiance -eq $null) 'la sourdine coupe toute musique'
$Config.musique_ambiance = $false; $script:Actif = $true; Start-Ambiance
Verifier ($script:Ambiance -eq $null) 'ambiance désactivée par défaut : rien ne démarre'
Verifier ([bool]$Config.musique_ambiance -eq $false) 'musique_ambiance est à false dans la config fournie'
# Réglages propres au test (copie de config) : jamais ceux de votre vraie config
$Config.musique_ambiance = $false; $Config.volume_musique = 0.3; $Config.volume_pendant_voix = 0.2; $Config.duree_fondu = 1.0
Verifier ((Get-VolumeBase) -eq 0.3 -and (Get-FractionVoix) -eq 0.2 -and (Get-DureeFondu) -eq 1.0 -and -not [bool]$Config.musique_ambiance) 'réglages lus depuis la config fournie : volume 0.3, voix 20 %, fondu 1 s, ambiance désactivée'
# ambiance activée avec un fichier : même ducking, coupée en sourdine
$fichierAmb = Join-Path $script:SonsDossier 'ambiance.mp3'; $existait = $false
if (-not $existait) { Copy-Item $tonalite $fichierAmb }            # fichier de test (un WAV nommé .mp3 est lu quand même) ; supprimé ensuite
try {
    $Config.musique_ambiance = $true; $script:VolActuel = $null; Start-Ambiance; Attendre 400
    Verifier ($script:Ambiance -ne $null) 'ambiance activée : démarre en boucle'
    Set-SonsParole $true; Attendre 700
    Verifier ($script:Ambiance -ne $null -and $script:Ambiance.Volume -lt 0.1) ("ambiance : même ducking pendant la parole ({0:N3})" -f $script:Ambiance.Volume)
    Set-SonsParole $false
    Set-SonsSourdine $true
    Verifier ($script:Ambiance -eq $null) 'ambiance coupée en sourdine'
} finally {
    Stop-Musiques
    if (-not $existait) { for ($i = 0; $i -lt 20 -and (Test-Path $fichierAmb); $i++) { [GC]::Collect(); Start-Sleep -Milliseconds 250; Remove-Item $fichierAmb -ErrorAction SilentlyContinue } }   # le lecteur libère le fichier avec un léger retard
}
if (-not $existait) { Verifier (-not (Test-Path $fichierAmb)) 'le fichier de test sounds\ambiance.mp3 est bien supprimé' }
Remove-Item $tonalite -ErrorAction SilentlyContinue
Write-Host '5) Sourdine totale et mode jeu : aucun son, aucune musique'
$script:Actif = $false; $script:DernierSon = $null; Invoke-Son 'actif'; Invoke-Son 'sourdine'
Verifier ($null -eq $script:DernierSon) 'sourdine : aucun bip ni carillon'
$Config.musique_ambiance = $true; Start-MusiqueDemarrage; Start-Ambiance
Verifier ($null -eq $script:Musique -and $null -eq $script:Ambiance) 'sourdine : ni musique de démarrage ni ambiance'
$script:Actif = $true; $script:ModeJeu = $true; Start-MusiqueDemarrage; Start-Ambiance; Invoke-Son 'actif'
Verifier ($null -eq $script:Musique -and $null -eq $script:Ambiance -and $null -eq $script:DernierSon) 'mode jeu : ni musique ni son'
$script:ModeJeu = $false
[IO.File]::WriteAllBytes((Join-Path $script:SonsDossier 'ambiance.mp3'), [byte[]](1..64))
Start-MusiqueDemarrage; Start-Ambiance
Verifier ($null -ne $script:Musique -and $null -ne $script:Ambiance) 'actif et hors mode jeu : musique de démarrage et ambiance repartent (faux lecteur)'
Stop-Musiques
Write-Host '6) Fichiers sounds\ trouvés (extension doublée tolérée), aucun son joué'
$script:SonsDossier = Join-Path $tmpSons 'dbl'; New-Item -ItemType Directory $script:SonsDossier | Out-Null
[IO.File]::WriteAllBytes((Join-Path $script:SonsDossier 'demarrage.mp3.mp3'), [byte[]](1..64)); [IO.File]::WriteAllBytes((Join-Path $script:SonsDossier 'ambiance.mp3.mp3'), [byte[]](1..64))
Verifier ((Find-FichierSon 'ambiance') -like '*ambiance.mp3.mp3' -and (Get-FichierDemarrage).fichier -like '*demarrage.mp3.mp3' -and -not (Get-FichierDemarrage).genere) 'ambiance.mp3.mp3 et demarrage.mp3.mp3 sont trouvés (pas le jingle généré)'
$Config.musique_ambiance = $true; $script:Actif = $true; $script:ModeJeu = $false; $script:Ambiance = $null; $script:VolActuel = $null
Start-Ambiance
Verifier ($null -ne $script:Ambiance -and $script:Ambiance.Fichier -like '*ambiance.mp3.mp3') 'musique_ambiance = true : l''ambiance utilise ce fichier (faux lecteur)'
Stop-Musiques
$script:SonsDossier = Join-Path $Root 'sounds'     # les vrais fichiers de Liam : on vérifie seulement qu'ils sont trouvés, sans les lire ni les jouer
$fa = Find-FichierSon 'ambiance'; $fd = Find-FichierSon 'demarrage'
Verifier ($fa -and $fd) ("vrai dossier sounds\ : ambiance = $(if ($fa) { Split-Path $fa -Leaf } else { 'ABSENT' }), démarrage = $(if ($fd) { Split-Path $fd -Leaf } else { 'ABSENT' })")
$script:SonsDossier = $tmpSons
Remove-Item $tmpSons -Recurse -Force -ErrorAction SilentlyContinue

if ($echecs) { Write-Host "`nÉCHEC : $echecs vérification(s) en échec." -ForegroundColor Red; exit 1 }
Write-Host "`nRÉUSSI"; exit 0

