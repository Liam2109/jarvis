# Agents B2B sur le portable serveur : dépendances Python et tâches planifiées « Jarvis-B2B-<agent> », mises à jour par maj-auto.ps1 APRÈS un pull réussi et des tests verts.
# Règles (décision de Liam, 04/11/2026) :
#   - rien ne démarre sans réglage voulu : B2B\agents\b2b.local.json (ignoré par git, propre à cette machine) doit contenir « machine_active » = le nom de CETTE machine, et « agents_actifs » = la liste des agents à planifier ;
#   - seules les tâches des agents actifs sont (re)créées (idempotent : -Force) ; celle d'un agent retiré de la liste est supprimée ; si une AUTRE machine est la machine active, toutes les tâches B2B d'ici sont retirées ;
#   - jamais touchées : Jarvis-MajAuto et Jarvis-Serveur (seul le préfixe « Jarvis-B2B- » est géré) ;
#   - chaque tâche appelle B2B\agents\serveur-b2b.ps1 (verrou global : un seul agent à la fois, priorité basse, aucun navigateur) ;
#   - ce code ne lève jamais d'exception vers maj-auto : une erreur est journalisée et la mise à jour de Jarvis continue.
# Mode test / simulation (JARVIS_TEST=1 ou JARVIS_B2B_SIMULATION=1) : aucune vraie tâche, aucun vrai pip. $script:B2BHooks (tests) remplace les actions réelles.
$script:B2BHooks = $null
$script:NomMachineB2B = $null
$script:B2BPipEchec = $false
$script:PrefixeTacheB2B = 'Jarvis-B2B-'
function Test-B2BSimulation { $env:JARVIS_TEST -eq '1' -or $env:JARVIS_B2B_SIMULATION -eq '1' }
function Get-NomMachineB2B {
    if ($script:NomMachineB2B) { return "$script:NomMachineB2B" }
    if ($env:JARVIS_B2B_MACHINE_TEST) { return $env:JARVIS_B2B_MACHINE_TEST }
    "$env:COMPUTERNAME"
}
function Get-B2BTachesExistantes {
    if ($script:B2BHooks -and $script:B2BHooks.Existantes) { return @(& $script:B2BHooks.Existantes) }
    if (Test-B2BSimulation) { return @() }
    @(Get-ScheduledTask -ErrorAction SilentlyContinue | Where-Object { $_.TaskName -like "$($script:PrefixeTacheB2B)*" } | ForEach-Object { $_.TaskName })
}
function Register-TacheB2B($t) {
    if ($script:B2BHooks -and $script:B2BHooks.Enregistrer) { & $script:B2BHooks.Enregistrer $t; return }
    if (Test-B2BSimulation) { return }
    $user = "$env:USERDOMAIN\$env:USERNAME"
    $principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
    $action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $t.arguments -WorkingDirectory $t.racine
    $trigger = $(if ($t.heure) { New-ScheduledTaskTrigger -Daily -At $t.heure } else { New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(2) -RepetitionInterval (New-TimeSpan -Minutes $t.minutes) -RepetitionDuration (New-TimeSpan -Days 3650) })
    if ($t.PSObject.Properties['lundi'] -and $t.lundi) { $trigger = @($trigger, (New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At $t.lundi)) }   # harness : déclencheur du lundi en plus (surveillant 07:50)
    if ($t.heure -and $t.PSObject.Properties['heures_en_plus']) { foreach ($h in @($t.heures_en_plus | Where-Object { $_ })) { $trigger = @($trigger) + (New-ScheduledTaskTrigger -Daily -At $h) } }   # plusieurs heures par jour + 22:00
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 2) -StartWhenAvailable -MultipleInstances IgnoreNew
    Register-ScheduledTask -TaskName $t.nom -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "Agent B2B « $($t.agent) » sur le serveur (créée par maj-auto.ps1 ; un seul agent à la fois)" -Force | Out-Null
}
function Unregister-TacheB2B([string]$nom) {
    if ($script:B2BHooks -and $script:B2BHooks.Supprimer) { & $script:B2BHooks.Supprimer $nom; return }
    if (Test-B2BSimulation) { return }
    if ($nom -like "$($script:PrefixeTacheB2B)*") { Unregister-ScheduledTask -TaskName $nom -Confirm:$false -ErrorAction SilentlyContinue }
}
function Get-B2BConfigLocale([string]$racine) {
    # -> @{ presente; erreur; machine; agents; serveur }  (le contenu du fichier n'est jamais affiché)
    $r = @{ presente = $false; erreur = ''; machine = ''; agents = @(); serveur = $false }
    $f = Join-Path $racine 'B2B\agents\b2b.local.json'
    if (-not (Test-Path -LiteralPath $f)) { return $r }
    $r.presente = $true
    try {
        $j = Get-Content -LiteralPath $f -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($j.PSObject.Properties['machine_active']) { $r.machine = "$($j.machine_active)".Trim() }
        if ($j.PSObject.Properties['agents_actifs']) { $r.agents = @($j.agents_actifs | ForEach-Object { "$_" } | Where-Object { $_ }) }
        if ($j.PSObject.Properties['serveur']) { $r.serveur = ($j.serveur -eq $true) }
    } catch { $r.erreur = 'b2b.local.json illisible' }
    $r
}
function Get-B2BTaches([string]$racine) {
    # Plan des tâches à créer : seulement si cette machine EST la machine active, et seulement pour les agents actifs connus de serveur-taches.json.
    $plan = @{ ok = $false; raison = ''; taches = @(); avertissements = @(); autreMachine = $false }
    $c = Get-B2BConfigLocale $racine
    if ($c.erreur) { $plan.raison = $c.erreur; return $plan }
    if (-not $c.machine) { $plan.raison = 'machine_active absent de b2b.local.json : aucune tâche B2B'; return $plan }
    $moi = Get-NomMachineB2B
    if ($c.machine.ToLower() -ne $moi.Trim().ToLower()) { $plan.raison = "machine_active = « $($c.machine) », cette machine = « $moi » : aucune tâche B2B ici"; $plan.autreMachine = $true; return $plan }
    $plan.ok = $true
    $table = $null; try { $table = (Get-Content -LiteralPath (Join-Path $racine 'B2B\agents\serveur-taches.json') -Raw -Encoding UTF8 | ConvertFrom-Json).agents } catch { $plan.ok = $false; $plan.raison = 'serveur-taches.json illisible'; return $plan }
    $lanceur = Join-Path $racine 'B2B\agents\serveur-b2b.ps1'; $liste = @()
    foreach ($a in ($c.agents | Select-Object -Unique)) {
        $def = $table.PSObject.Properties[$a]
        if (-not $def) { $plan.avertissements += "agent inconnu ignoré : $a"; continue }
        $d = $def.Value
        if ($d.PSObject.Properties['desactive']) { $plan.avertissements += "agent désactivé ignoré (serveur-taches.json) : $a"; continue }   # 18/11/2026 : comme s'il était retiré de agents_actifs, sa tâche est retirée
        $liste += [pscustomobject]@{ nom = "$($script:PrefixeTacheB2B)$a"; agent = $a; minutes = $(if ($d.PSObject.Properties['toutes_minutes']) { [int]$d.toutes_minutes } else { 0 }); heure = $(if ($d.PSObject.Properties['heure']) { "$($d.heure)" } else { '' }); lundi = $(if ($d.PSObject.Properties['lundi']) { "$($d.lundi)" } else { '' }); heures_en_plus = $(if ($d.PSObject.Properties['heures_en_plus']) { @($d.heures_en_plus | ForEach-Object { "$_" }) } else { @() }); racine = $racine
            arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$lanceur`" -Agent $a" }
    }
    $plan.taches = $liste
    $plan
}
function Sync-B2BTaches([string]$racine, [switch]$SeulementManquantes) {
    # (Re)crée les tâches des agents actifs, retire celles des agents qui ne le sont plus. Retourne un résumé (vide : rien à dire).
    # -SeulementManquantes (rattrapage de maj-auto quand le serveur est DÉJÀ à jour, toutes les 10 min) : seules les tâches ABSENTES sont créées et les tâches
    # en trop retirées ; une tâche existante n'est jamais réenregistrée (son intervalle « toutes les N min » repartirait de zéro à chaque passage, donc un agent
    # à 30 min ne tournerait jamais) et rien n'est dit quand il n'y a rien à faire (pas une ligne de journal toutes les 10 min).
    $plan = Get-B2BTaches $racine; $dit = @()
    $existantes = @(Get-B2BTachesExistantes | Where-Object { $_ -like "$($script:PrefixeTacheB2B)*" })
    if (-not $plan.ok) {
        if ($plan.autreMachine) { foreach ($n in $existantes) { Unregister-TacheB2B $n; $dit += "B2B : tâche $n retirée ($($plan.raison))" } }
        elseif (-not $SeulementManquantes -and (Get-B2BConfigLocale $racine).presente) { $dit += "B2B : aucune tâche ($($plan.raison))" }
    } else {
        foreach ($t in $plan.taches) {
            if ($SeulementManquantes -and ($t.nom -in $existantes)) { continue }
            Register-TacheB2B $t; $dit += "B2B : tâche $($t.nom) $(if ($t.heure) { "chaque jour à $($t.heure)$(if ($t.PSObject.Properties['heures_en_plus'] -and @($t.heures_en_plus).Count) { ', ' + (@($t.heures_en_plus) -join ', ') })$(if ($t.PSObject.Properties['lundi'] -and $t.lundi) { " et le lundi à $($t.lundi)" })" } else { "toutes les $($t.minutes) min" }) créée ou mise à jour$(if (Test-B2BSimulation) { ' (simulation)' })" }
        $voulues = @($plan.taches | ForEach-Object { $_.nom })
        foreach ($n in $existantes) { if ($n -notin $voulues) { Unregister-TacheB2B $n; $dit += "B2B : tâche $n retirée (agent non actif)" } }
        if (-not $SeulementManquantes) {
            foreach ($w in $plan.avertissements) { $dit += "B2B : $w" }
            if (-not $plan.taches.Count) { $dit += 'B2B : aucun agent actif dans agents_actifs : aucune tâche (tout est éteint par défaut)' }
        }
    }
    $dit -join "`n"
}
function Install-B2BDependances([string]$racine) {
    # pip install -r B2B\requirements.txt. Retourne $true (fait, ou rien à faire) ou $false (échec) ; ne lève jamais d'exception.
    $req = Join-Path $racine 'B2B\requirements.txt'
    if (-not (Test-Path -LiteralPath $req)) { return $true }
    try {
        if ($script:B2BHooks -and $script:B2BHooks.Pip) { return [bool](& $script:B2BHooks.Pip $req) }
        if (Test-B2BSimulation) { return $true }
        $py = @(Get-Command python -All -ErrorAction SilentlyContinue | Where-Object { $_.CommandType -eq 'Application' -and $_.Source -notmatch '(?i)[\\/]WindowsApps[\\/]' }) | Select-Object -First 1
        if (-not $py) { return $false }
        & $py.Source -m pip install --disable-pip-version-check -r $req 2>&1 | Out-Null
        $LASTEXITCODE -eq 0
    } catch { $false }
}
function Update-B2BServeur([string]$racine, [switch]$SansPip) {
    # Appelée par maj-auto.ps1 après un pull réussi et des tests verts. Retourne le texte à afficher ('' : rien à dire). $script:B2BPipEchec = $true si pip a échoué.
    $script:B2BPipEchec = $false
    try {
        $c = Get-B2BConfigLocale $racine
        if (-not $c.presente) { return '' }      # machine sans réglage B2B (ex. le PC de Liam) : rien n'est fait
        $lignes = @()
        $plan = Get-B2BTaches $racine
        if ($plan.ok -and $plan.taches.Count -and -not $SansPip) {
            if (Install-B2BDependances $racine) { $lignes += 'B2B : dépendances Python à jour (requirements.txt)' } else { $script:B2BPipEchec = $true; $lignes += 'B2B : pip install -r B2B\requirements.txt a ÉCHOUÉ (les tâches sont tout de même mises à jour)' }
        }
        $s = Sync-B2BTaches $racine; if ($s) { $lignes += $s }
        foreach ($l in $lignes) { if (Get-Command Write-Journal -ErrorAction SilentlyContinue) { Write-Journal -Action 'B2B serveur' -Resultat $l } }
        return ($lignes -join "`n")
    } catch {
        $m = "B2B : étape ignorée (erreur : $($_.Exception.Message))"
        if (Get-Command Write-Journal -ErrorAction SilentlyContinue) { Write-Journal -Action 'B2B serveur' -Resultat $m }
        return $m
    }
}
