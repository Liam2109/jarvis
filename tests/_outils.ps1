# Outils communs aux tests. Faux serveur HTTP local lancé comme un PROCESSUS (un Start-Job bloqué en écoute met 120 s à s'arrêter).
function Start-FauxServeur([object[]]$arguments, [scriptblock]$bloc) {
    $f = Join-Path $env:TEMP ('faux-serveur-' + [guid]::NewGuid().ToString('N').Substring(0, 6) + '.ps1')
    $a = ($arguments | ForEach-Object { "'" + ("$_" -replace "'", "''") + "'" }) -join ' '
    [IO.File]::WriteAllText($f, "& { $($bloc.ToString()) } $a", [Text.UTF8Encoding]::new($true))
    $p = Start-Process powershell -ArgumentList '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$f`"" -WindowStyle Hidden -PassThru
    @{ proc = $p; fichier = $f }
}
function Stop-FauxServeur($s) {
    if ($s -and $s.proc) { Stop-Process -Id $s.proc.Id -Force -ErrorAction SilentlyContinue }
    if ($s -and $s.fichier) { Remove-Item $s.fichier -Force -ErrorAction SilentlyContinue }
}
