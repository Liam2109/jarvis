# Diagnostic du SERVEUR (jarvis.ps1 diag-serveur) : mémoire par processus, temps de réponse de Claude (claude -p) et d'Ollama, résumé lisible avec les causes probables d'une lenteur.
# Lecture seule : rien n'est modifié ni arrêté. Faits : UN appel très court à Claude (abonnement, ~1 requête) et deux appels très courts à Ollama s'il tourne (jamais démarré par ce diagnostic).
# Aucune ligne de commande, aucune clé n'est affichée : seulement des noms de rôles (écoute, pont Discord, Ollama...).
function Get-RoleProcessus($p) {
    # Nom lisible du rôle d'un processus (null = sans rapport avec Jarvis).
    $n = "$($p.Name)".ToLower(); $c = "$($p.CommandLine)"
    if ($n -match '^python' -and $c -match 'ecoute\.py') { return 'écoute du micro (ecoute.py)' }
    if ($n -match '^python' -and $c -match 'reveil\.py') { return 'écoute de veille (reveil.py)' }
    if ($n -match '^python' -and $c -match 'pont-discord[\\/]pont\.py|pont\.py') { return 'pont Discord' }
    if ($n -match '^python' -and $c -match 'piper') { return 'voix Piper' }
    if ($n -match '^python' -and $c -match 'prechauffe\.py') { return 'préchauffage de la voix' }
    if ($n -match '^python') { return 'python (autre)' }
    if ($n -match '^(powershell|pwsh)' -and $c -match 'jarvis\.ps1') { return 'Jarvis (jarvis.ps1)' }
    if ($n -match '^(powershell|pwsh)' -and $c -match 'veille-fond\.ps1') { return 'veille de fond' }
    if ($n -match '^(powershell|pwsh)' -and $c -match 'maj-auto\.ps1') { return 'mise à jour auto' }
    if ($n -match '^ollama') { return $(if ($n -match 'runner|llama_server') { 'Ollama (modèle chargé)' } else { 'Ollama (service)' }) }
    if ($n -match '^(claude|node)$' -or ($n -eq 'cmd' -and $c -match 'claude')) { return 'Claude (claude -p)' }
    if ($n -match '^(msedge|jarvis-edge)') { return 'Edge' }
    $null
}
function Get-RamProcessusJarvis {
    # @{ totalMo; libreMo; processus = @(@{ role; pid; mo }) } trié du plus gros au plus petit ; seulement les processus liés à Jarvis.
    $os = Get-CimInstance Win32_OperatingSystem
    $liste = @(Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -ne $PID } | ForEach-Object { $r = Get-RoleProcessus $_; if ($r) { @{ role = $r; pid = [int]$_.ProcessId; mo = [int]($_.WorkingSetSize / 1MB) } } } | Sort-Object { -$_.mo })
    @{ totalMo = [int]($os.TotalVisibleMemorySize / 1KB); libreMo = [int]($os.FreePhysicalMemory / 1KB); processus = $liste }
}
function Measure-ReponseClaude {
    # @{ ok; ms; raison } : un appel minimal à claude -p (même chemin que le cerveau).
    $t = Get-Date
    try { $r = Invoke-Claude 'Réponds uniquement par le mot : ok' 'test' 90 } catch { return @{ ok = $false; ms = 0; raison = 'erreur pendant l''appel' } }
    $ms = [int]((Get-Date) - $t).TotalMilliseconds
    if ($r) { @{ ok = $true; ms = $ms; raison = '' } } else { @{ ok = $false; ms = $ms; raison = 'pas de réponse (claude introuvable, non connecté ou délai dépassé)' } }
}
function Measure-ReponseOllama {
    # @{ actif; pret; modele; froidMs; chaudMs; chargeMo; keep; raison }. Ne démarre JAMAIS le service.
    $c = Get-OllamaConfig; $r = @{ actif = $false; pret = $false; modele = $c.modele; froidMs = 0; chaudMs = 0; chargeMo = 0; keep = "$($c.keep)"; raison = '' }
    $o = Test-Ollama; $r.actif = [bool]$o.actif; $r.pret = [bool]$o.pret; $r.raison = "$($o.raison)"
    if (-not $o.pret) { return $r }
    $deja = $false; try { $ps = Invoke-RestMethod -Uri "$($c.url)/api/ps" -TimeoutSec 3; $deja = [bool](@($ps.models) | Where-Object { $_.name -like "$($c.modele)*" }) } catch { }
    foreach ($k in 'froidMs', 'chaudMs') {
        $t = Get-Date; $rep = Invoke-Ollama 'Réponds par {"dit":"ok"}' 'test' 90
        $ms = [int]((Get-Date) - $t).TotalMilliseconds; if ($rep) { $r[$k] = $ms } else { $r.raison = 'le modèle n''a pas répondu'; break }
    }
    if ($deja) { $r.raison = 'modèle déjà chargé avant le test (le « 1er appel » n''est donc pas un démarrage à froid)' }
    try { $ps = Invoke-RestMethod -Uri "$($c.url)/api/ps" -TimeoutSec 3; $m = @($ps.models) | Where-Object { $_.name -like "$($c.modele)*" } | Select-Object -First 1; if ($m) { $r.chargeMo = [int]($m.size / 1MB) } } catch { }
    $r
}
function Format-Duree([int]$ms) { if ($ms -ge 1000) { '{0:N1} s' -f ($ms / 1000) } else { "$ms ms" } }
function Get-DiagServeur([switch]$SansMesure) {
    # Retourne les lignes du rapport (le serveur doit être en mode_serveur ; sur un autre PC le rapport le signale mais fonctionne).
    $L = New-Object System.Collections.Generic.List[string]
    $adv = New-Object System.Collections.Generic.List[string]
    $L.Add('=== Diagnostic du serveur Jarvis ===')
    $L.Add("Mode serveur : $(if (Test-ModeServeur) { 'oui' } else { 'NON (ce PC n''est pas configuré en serveur)' }) · cerveau : $(Get-ModeCerveau) · modèle local : $((Get-OllamaConfig).modele)")
    $ram = Get-RamProcessusJarvis
    $pct = if ($ram.totalMo) { [int](100 * ($ram.totalMo - $ram.libreMo) / $ram.totalMo) } else { 0 }
    $L.Add(''); $L.Add("Mémoire : $([math]::Round($ram.totalMo / 1024, 1)) Go au total, $([math]::Round($ram.libreMo / 1024, 1)) Go libres ($pct % utilisés)")
    $somme = 0
    if (@($ram.processus).Count) {
        foreach ($p in $ram.processus) { $L.Add(('  {0,6} Mo  {1}  (pid {2})' -f $p.mo, $p.role, $p.pid)); $somme += $p.mo }
        $L.Add(('  {0,6} Mo  TOTAL lié à Jarvis' -f $somme))
    } else { $L.Add('  (aucun processus Jarvis en cours)') }
    $roles = @($ram.processus | ForEach-Object { $_.role })
    if ((Test-ModeServeur) -and ($roles -match 'écoute')) { $adv.Add('ANOMALIE : une écoute du micro tourne alors que le serveur doit être sans micro. Mettez "serveur_micro": "non" dans config.local.json puis relancez Jarvis.') }
    if ($roles -match 'Piper|préchauffage') { $adv.Add('Une voix (Piper) est chargée : inutile sur un serveur (aucune parole). Vérifiez mode_serveur.') }
    if ($roles -match 'Edge') { $adv.Add('Edge tourne : inutile sur un serveur (pas de HUD).') }
    $ollamaMo = 0; foreach ($p in $ram.processus) { if ($p.role -like 'Ollama*') { $ollamaMo += $p.mo } }
    if ($ollamaMo -gt 1500) { $adv.Add("Ollama occupe $ollamaMo Mo : avec peu de RAM, réglez ollama.keep_alive à 5m dans config.local.json (le modèle se décharge après usage).") }
    if ($pct -ge 90) { $adv.Add("La mémoire est presque pleine ($pct %) : le PC swappe, d'où des réponses de plusieurs dizaines de secondes.") }
    if ($SansMesure) { $L.Add(''); $L.Add('(mesures de temps non faites : -SansMesure)') }
    else {
        $L.Add(''); $L.Add('Temps de réponse :')
        $cl = Measure-ReponseClaude
        if ($cl.ok) { $L.Add("  Claude (claude -p)  : $(Format-Duree $cl.ms)") ; if ($cl.ms -gt 15000) { $adv.Add("Claude met $(Format-Duree $cl.ms) pour un mot : machine saturée ou réseau lent (démarrage de Node/claude ~ plusieurs secondes sur un vieux PC).") } }
        else { $L.Add("  Claude (claude -p)  : ÉCHEC - $($cl.raison)"); $adv.Add("Claude ne répond pas : $($cl.raison).") }
        $ol = Measure-ReponseOllama
        if ($ol.pret -and $ol.chaudMs) {
            $L.Add("  Ollama $($ol.modele) : 1er appel $(Format-Duree $ol.froidMs), appel suivant $(Format-Duree $ol.chaudMs) · modèle en mémoire : $($ol.chargeMo) Mo · keep_alive $($ol.keep)")
            if ($ol.raison) { $L.Add("    ($($ol.raison))") }
            if ($ol.chaudMs -gt 8000) { $adv.Add("Ollama est lent même modèle chaud ($(Format-Duree $ol.chaudMs)) : sans GPU, mieux vaut cerveau = ""claude"" sur ce serveur, ou un modèle plus petit.") }
            if (($ol.froidMs - $ol.chaudMs) -gt 10000) { $adv.Add("Chargement du modèle : +$(Format-Duree ($ol.froidMs - $ol.chaudMs)) au premier appel après une pause (keep_alive $($ol.keep)).") }
        } else { $L.Add("  Ollama              : non mesuré ($(if ($ol.raison) { $ol.raison } else { 'indisponible' }))") }
    }
    $L.Add(''); $L.Add('Résumé :')
    if ($adv.Count) { foreach ($a in $adv) { $L.Add("  - $a") } } else { $L.Add('  Rien d''anormal : seuls les processus attendus tournent et les temps de réponse sont raisonnables.') }
    $L
}
