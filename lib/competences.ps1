# Compétences personnelles : chaque fichier lib\competences\*.ps1 est chargé au démarrage (sauf ceux dont le nom commence par « _ »).
# Un fichier qui contient une erreur est ignoré (et noté au journal) : il ne peut pas empêcher Jarvis de démarrer.
# Le NIVEAU de permission s'applique comme pour les compétences intégrales : 1 = autonome, 2 = confirmation « oui » ; le niveau 3 reste décidé par le code.
function Import-Competences([string]$dossier = (Join-Path $script:JarvisRoot 'lib\competences')) {
    $res = @{ chargees = @(); echecs = @() }
    if (-not (Test-Path $dossier)) { return $res }
    foreach ($f in (Get-ChildItem $dossier -Filter *.ps1 -File | Where-Object { $_.Name -notlike '_*' } | Sort-Object Name)) {
        $avant = @($script:Actions.Keys)
        try {
            $erreurs = $null; [void][Management.Automation.Language.Parser]::ParseFile($f.FullName, [ref]$null, [ref]$erreurs)
            if ($erreurs) { throw "erreur de syntaxe ligne $($erreurs[0].Extent.StartLineNumber) : $($erreurs[0].Message)" }
            . $f.FullName
            $nouvelles = @($script:Actions.Keys | Where-Object { $_ -notin $avant })
            $res.chargees += "$($f.Name) ($($nouvelles -join ', '))"
            Write-Journal -Action 'Compétence personnelle chargée' -Resultat "$($f.Name) : $($nouvelles -join ', ')"
        } catch {
            foreach ($k in @($script:Actions.Keys | Where-Object { $_ -notin $avant })) { $script:Actions.Remove($k) }   # une compétence à moitié chargée est retirée
            $res.echecs += "$($f.Name) : $($_.Exception.Message)"
            Write-Journal -Action 'Compétence personnelle IGNORÉE' -Resultat "$($f.Name) : $($_.Exception.Message)"
        }
    }
    $res
}
