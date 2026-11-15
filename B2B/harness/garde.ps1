# Garde commune des envois (harness, 15/11/2026) : même contrôle que garde.py, pour les scripts PowerShell.
# Test-GardeEnvoi -Agent 'appels-sid' -Canal 'discord' -Texte $t  ->  [pscustomobject]@{ ok = $true/$false ; raisons = @(...) }
# BLOQUE : B2B\STOP, lien Stripe non autorisé, phrase interdite, secret, envoi client hors lun-ven 08:00-19:00. Le reste avertit (trace).
function Test-GardeEnvoi([string]$Agent, [string]$Canal = 'discord', [string]$Texte, [string]$Destinataire = '') {
    $py = Join-Path $PSScriptRoot 'garde.py'
    $psi = New-Object System.Diagnostics.ProcessStartInfo 'python'
    $psi.Arguments = "`"$py`" --agent `"$Agent`" --canal `"$Canal`" --destinataire `"$Destinataire`""
    $psi.UseShellExecute = $false; $psi.RedirectStandardInput = $true; $psi.RedirectStandardOutput = $true; $psi.CreateNoWindow = $true
    $psi.StandardOutputEncoding = [System.Text.Encoding]::UTF8; $psi.EnvironmentVariables['PYTHONIOENCODING'] = 'utf-8'
    try {
        $p = [System.Diagnostics.Process]::Start($psi)
        $b = [System.Text.Encoding]::UTF8.GetBytes($Texte); $p.StandardInput.BaseStream.Write($b, 0, $b.Length); $p.StandardInput.Close()
        $sortie = $p.StandardOutput.ReadToEnd(); $p.WaitForExit()
        $r = $sortie | ConvertFrom-Json
        return [pscustomobject]@{ ok = [bool]$r.ok; raisons = @($r.raisons) }
    } catch { return [pscustomobject]@{ ok = $true; raisons = @("AVERTIT : garde indisponible ($($_.Exception.GetType().Name)), envoi non contrôlé") } }
}
