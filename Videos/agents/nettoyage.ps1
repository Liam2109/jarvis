# Agent videos-nettoyage (équipe Vidéos TikTok, 16/11/2026) : sans token, sans réseau. Tâche quotidienne (03:30, lanceur B2B\agents\serveur-b2b.ps1).
# Supprime les fichiers vidéo (.mp4) et intermédiaires (son, images, sous-titres de rendu, journaux de rendu : liste « nettoyage_extensions ») plus vieux que
# « nettoyage_jours » jours (videos-config.json, surchargé par videos-config.local.json) dans Videos\a-valider, publiees, travail et outils\stickfigure-pipeline-v2\output.
# Avant chaque suppression : une ligne dans Videos\journal-videos.csv (date, nom, statut, hook) ; une seule ligne par dossier pour les fichiers intermédiaires.
# Ne touche JAMAIS : SKILL-VIDEOS.md, hooks*.md, README, la config, agents\, scripts\, veille\ (notes de veille), node_modules, les vidéos de « videos_protegees ».
# N'écrit que dans Videos\. Refuse (code 3) si cette machine n'est pas la machine active (B2B\agents\b2b.local.json), comme les autres agents.
#   powershell -File Videos\agents\nettoyage.ps1 [-Simulation] [-Racine <dossier Videos>] [-Maintenant AAAA-MM-JJ]
#   -Simulation : dit ce qui serait supprimé, ne supprime rien, n'écrit rien.
param([switch]$Simulation, [string]$Racine = '', [string]$Maintenant = '', [string]$NomMachine = $env:COMPUTERNAME)
$ErrorActionPreference = 'Stop'
$AGENT = 'videos-nettoyage'
$V = $(if ($Racine) { (Resolve-Path -LiteralPath $Racine).Path } else { (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path })
$JARVIS = Split-Path -Parent $V
$journal = Join-Path $V "$AGENT-journal.log"
$csv = Join-Path $V 'journal-videos.csv'
$utf8 = New-Object System.Text.UTF8Encoding($false)
function Log([string]$t) { if (-not $Simulation) { [IO.File]::AppendAllText($journal, ("{0:yyyy-MM-dd HH:mm:ss} | {1}`n" -f (Get-Date), $t), $utf8) }; Write-Host $t }
function Csv-Champ([string]$s) { $s = ("$s" -replace '\s+', ' ').Trim(); if ($s -match '[;"]') { '"' + ($s -replace '"', '""') + '"' } else { $s } }
function Csv-Ligne([string]$video, [string]$statut, [string]$hook, [string]$detail, [string]$ligne = '') {
    if ($Simulation) { return }
    $neuf = -not (Test-Path -LiteralPath $csv)
    $l = (@((Get-Date -Format 'yyyy-MM-dd HH:mm'), $AGENT, $video, $ligne, '', $statut, $hook, $detail, '') | ForEach-Object { Csv-Champ $_ }) -join ';'
    if ($neuf) { [IO.File]::WriteAllText($csv, "date;agent;video;ligne;compte;statut;hook;detail;tts;histoire;formule;theme;fin;duree_s;voix;publie_le;url_tiktok`r`n", (New-Object System.Text.UTF8Encoding($true))) }
    [IO.File]::AppendAllText($csv, "$l`r`n", $utf8)
}

# 1) machine active (comme B2B\agents\machine.py) ; -Simulation n'écrit rien et n'est pas refusé
if (-not $Simulation) {
    $fl = Join-Path $JARVIS 'B2B\agents\b2b.local.json'; $active = ''
    if (Test-Path -LiteralPath $fl) { try { $active = "$((Get-Content -LiteralPath $fl -Raw -Encoding UTF8 | ConvertFrom-Json).machine_active)".Trim() } catch { $active = '' } }
    if (-not $active) { Log "refusé : machine_active absent de b2b.local.json (aucune machine active choisie)"; exit 3 }
    if ($active -ne $NomMachine.Trim()) { Log "refusé : cette machine est « $NomMachine », la machine active est « $active »"; exit 3 }
}

# 2) réglages (jamais dans le code : videos-config.json puis videos-config.local.json)
$jours = 14; $ext = @('.mp4'); $proteges = @()
foreach ($n in 'videos-config.json', 'videos-config.local.json') {
    $p = Join-Path $V $n
    if (-not (Test-Path -LiteralPath $p)) { continue }
    try { $c = Get-Content -LiteralPath $p -Raw -Encoding UTF8 | ConvertFrom-Json } catch { Log "réglages illisibles ($n) : rien supprimé"; exit 2 }
    if ($c.PSObject.Properties['nettoyage_jours']) { $jours = [int]$c.nettoyage_jours }
    if ($c.PSObject.Properties['nettoyage_extensions']) { $ext = @($c.nettoyage_extensions | ForEach-Object { "$_".ToLower() }) }
    if ($c.PSObject.Properties['videos_protegees']) { $proteges = @($c.videos_protegees | ForEach-Object { "$_" }) }
}
if ($jours -lt 1) { Log "nettoyage_jours = $jours : refusé (1 jour au moins), rien supprimé"; exit 2 }
$ext = @($ext | Where-Object { $_ -match '^\.[a-z0-9]+$' -and $_ -notin '.md', '.py', '.ps1', '.json', '.txt', '.csv' })   # jamais un document, un script ou un réglage
$auj = $(if ($Maintenant) { [datetime]::ParseExact($Maintenant, 'yyyy-MM-dd', $null) } else { Get-Date })
$limite = $auj.AddDays(-$jours)

# 3) fichiers candidats, seulement dans ces dossiers de Videos\
$dossiers = @('a-valider', 'publiees', 'travail', 'outils\stickfigure-pipeline-v2\output') | ForEach-Object { Join-Path $V $_ } | Where-Object { Test-Path -LiteralPath $_ }
$sup = 0; $octets = 0
function Supprimer([IO.FileInfo]$f) {
    $script:octets += $f.Length; $script:sup++
    if (-not $Simulation) { Remove-Item -LiteralPath $f.FullName -Force }
}
foreach ($d in $dossiers) {
    $vieux = @(Get-ChildItem -LiteralPath $d -File -Recurse -Force | Where-Object {
            $_.FullName.StartsWith($V + '\', [StringComparison]::OrdinalIgnoreCase) -and $_.FullName -notmatch '\\node_modules\\' -and
            $_.Extension.ToLower() -in $ext -and $_.LastWriteTime -lt $limite -and $_.BaseName -notin $proteges })
    if (-not $vieux.Count) { continue }
    $rel = $d.Substring($V.Length + 1)
    $videos = @($vieux | Where-Object { $_.Extension -ieq '.mp4' -and $rel -in 'a-valider', 'publiees' })
    foreach ($m in $videos) {   # une vidéo finie : sa ligne (avec son hook), puis la vidéo et sa légende / ses métadonnées
        $hook = ''; $ligne = ''; $js = [IO.Path]::ChangeExtension($m.FullName, '.json')
        if (Test-Path -LiteralPath $js) { try { $meta = Get-Content -LiteralPath $js -Raw -Encoding UTF8 | ConvertFrom-Json; $hook = "$(if ($meta.PSObject.Properties['hook']) { $meta.hook } elseif ($meta.PSObject.Properties['accroche']) { $meta.accroche })"; $ligne = "$($meta.serie)" } catch { } }
        Csv-Ligne $m.BaseName "supprimée ($rel, plus de $jours jours)" $hook ("{0:N1} Mo" -f ($m.Length / 1MB)) $ligne
        Supprimer $m
        foreach ($x in '.txt', '.json') {
            $s = [IO.Path]::ChangeExtension($m.FullName, $x)
            if (Test-Path -LiteralPath $s) { $fi = Get-Item -LiteralPath $s; if ($Simulation) { Write-Host "  supprimerait $($fi.Name)" }; Supprimer $fi }
        }
        Write-Host "$(if ($Simulation) { 'supprimerait' } else { 'supprimé' }) : $rel\$($m.Name)"
    }
    $autres = @($vieux | Where-Object { $_.FullName -notin $videos.FullName })
    if ($autres.Count) {
        Csv-Ligne $rel "intermédiaires supprimés (plus de $jours jours)" '' ("{0} fichier(s), {1:N1} Mo" -f $autres.Count, (($autres | Measure-Object Length -Sum).Sum / 1MB))
        foreach ($f in $autres) { Supprimer $f }
        Write-Host "$(if ($Simulation) { 'supprimerait' } else { 'supprimé' }) : $($autres.Count) fichier(s) intermédiaire(s) dans $rel"
    }
}
# 4) dossiers de travail vides (jamais ailleurs que dans travail\)
$t = Join-Path $V 'travail'
if (-not $Simulation -and (Test-Path -LiteralPath $t)) { Get-ChildItem -LiteralPath $t -Directory -Recurse | Sort-Object { $_.FullName.Length } -Descending | Where-Object { -not (Get-ChildItem -LiteralPath $_.FullName -Force) } | ForEach-Object { Remove-Item -LiteralPath $_.FullName -Force } }
Log ("{0} : {1} fichier(s) {2}, {3:N1} Mo (plus de {4} jours ; protégées : {5})" -f $(if ($Simulation) { 'simulation' } else { 'nettoyage' }), $sup, $(if ($Simulation) { 'à supprimer' } else { 'supprimé(s)' }), ($octets / 1MB), $jours, $(if ($proteges.Count) { $proteges -join ', ' } else { 'aucune' }))
exit 0
