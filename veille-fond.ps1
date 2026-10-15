# Veille de fond LÉGÈRE : processus séparé, sans voix, sans fenêtre, sans son. Lancé par Jarvis (même en sourdine) SEULEMENT si "marche_actif" est true.
# Toutes les "veille_minutes" minutes : interroge les SEULES sources validées (config.json "sources_validees"), dans le respect de leur limite de requêtes,
# et écrit un relevé horodaté dans memoire\veille\ (taille bornée). Jarvis lit ces relevés (panneau Marché, alertes, briefing, dossiers).
# Pause pendant le mode jeu (memoire\modejeu.flag). S'arrête avec Jarvis (processus parent disparu, memoire\quitter.flag) et avec arreter.ps1.
# LECTURE SEULE : aucun ordre, aucun courtier, aucun conseil.
param([int]$ParentPid = 0)
$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot
. (Join-Path $Root 'lib\journal.ps1')
Import-JarvisEnv
. (Join-Path $Root 'lib\veille.ps1')
. (Join-Path $Root 'lib\marche.ps1')
. (Join-Path $Root 'lib\priorite.ps1')
foreach ($f in (Get-ChildItem (Join-Path $Root 'lib\sources') -Filter '*.ps1' -ErrorAction SilentlyContinue | Where-Object { $_.Name -notlike '_*' })) { . $f.FullName }
try { [Diagnostics.Process]::GetCurrentProcess().PriorityClass = 'BelowNormal' } catch {}
$quit = Join-Path $Root 'memoire\quitter.flag'
$derniers = @{}
$Config = Import-ConfigJarvis
Write-Journal -Action 'Veille de fond' -Resultat "démarrée (PID $PID, parent $ParentPid)"
function Test-ParentVivant { if ($ParentPid -le 0) { return $true }; [bool](Get-Process -Id $ParentPid -ErrorAction SilentlyContinue) }
try {
    while (Test-ParentVivant) {
        if (Test-Path $quit) { break }
        try {
            $Config = Import-ConfigJarvis          # relu à chaque passe : marche_actif / sources_validees à jour
            if ((Test-MarcheActif) -and -not (Test-Path (Get-FichierFlagJeu))) {
                $r = Invoke-CycleVeilleFond $derniers
                $nouv = @(Select-ErreursNonRepetees $r.erreurs)      # une indisponibilité inchangée n'est pas répétée au journal
                if ($r.fait -and $nouv.Count) { Write-Journal -Action 'Veille de fond' -Resultat ("relevé écrit ; source(s) indisponible(s) : " + ($nouv -join ' ; ')) }
            }
        } catch { Write-Journal -Action 'Veille de fond' -Resultat "erreur : $($_.Exception.Message)" }
        $fin = (Get-Date).AddMinutes((Get-VeilleMinutesEffectif))      # rythme plus soutenu si la priorité effective est élevée / max (les limites de chaque source priment)
        while ((Get-Date) -lt $fin -and (Test-ParentVivant) -and -not (Test-Path $quit)) { Start-Sleep -Seconds 5 }
    }
} finally {
    Write-Journal -Action 'Veille de fond' -Resultat 'arrêtée'
    Remove-Item (Get-FichierPidVeille) -ErrorAction SilentlyContinue
}
