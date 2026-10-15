# Données du tableau de bord. Règle : uniquement ce qui est réellement lu. Une source absente = { dispo = $false; raison = "..." }, jamais un chiffre inventé.
$script:Tableau = @{ systeme = $null; site = $null; business = $null; actus = $null }
$script:TableauMaj = @{ systeme = [datetime]::MinValue; site = [datetime]::MinValue; business = [datetime]::MinValue; actus = [datetime]::MinValue }
$script:BriefingLignes = New-Object System.Collections.Generic.List[string]

function Update-Tableau {
    # À appeler depuis la boucle principale (jamais depuis Invoke-Pump : certaines lectures prennent du temps).
    $now = Get-Date
    if (($now - $script:TableauMaj.systeme).TotalSeconds -ge 8) {
        $script:TableauMaj.systeme = $now
        try {
            $os = Get-CimInstance Win32_OperatingSystem
            $cpu = (Get-CimInstance Win32_Processor | Measure-Object LoadPercentage -Average).Average
            $tot = $os.TotalVisibleMemorySize / 1MB; $lib = $os.FreePhysicalMemory / 1MB
            $d = New-Object IO.DriveInfo ($env:SystemDrive)
            $script:Tableau.systeme = @{ dispo = $true; cpu = [int]$cpu; ram_pct = [int](100 * ($tot - $lib) / $tot); ram_go = [math]::Round($tot - $lib, 1); ram_total_go = [math]::Round($tot, 1)
                disque_pct = [int](100 * ($d.TotalSize - $d.AvailableFreeSpace) / $d.TotalSize); disque_libre_go = [int]($d.AvailableFreeSpace / 1GB); disque = $env:SystemDrive }
        } catch { $script:Tableau.systeme = @{ dispo = $false; raison = 'lecture impossible' } }
    }
    if (($now - $script:TableauMaj.site).TotalSeconds -ge 90) {
        $script:TableauMaj.site = $now
        $s = Get-StatutSite 6
        $script:Tableau.site = @{ dispo = $true; en_ligne = [bool]$s.ok; code = $s.code; verifie = $now.ToString('HH:mm:ss') }
    }
    if (($now - $script:TableauMaj.business).TotalSeconds -ge 300) {
        $script:TableauMaj.business = $now
        $d = Get-ChiffresBusiness $now.AddHours(-24) -SansSite
        $ko = { param($x) @{ dispo = $false; raison = $x.raison } }
        $b = @{}
        $b.visites = if ($d.visites.dispo) { @{ dispo = $true; valeur = $d.visites.valeur } } else { & $ko $d.visites }
        $b.quiz = if ($d.stats.dispo) { @{ dispo = $true; valeur = $d.stats.sessions; detail = "dont $($d.stats.payees) payé(s)" } } else { & $ko $d.stats }
        $b.emails = if ($d.stats.dispo) { @{ dispo = $true; valeur = $d.stats.emails } } else { & $ko $d.stats }
        $b.abonnes = if ($d.abonnes.dispo) { @{ dispo = $true; valeur = $d.abonnes.valeur } } else { & $ko $d.abonnes }
        $b.ca = if ($d.ca.dispo) { @{ dispo = $true; valeur = $(if ($d.ca.montants.Count) { Format-Montants $d.ca.montants } else { '0 euro' }) } } else { & $ko $d.ca }
        $b.saas = if ($d.stats.dispo) { @{ dispo = $true } + $d.stats.saas } else { @{ dispo = $false; raison = "$($d.stats.raison)" } }
        if ($d.stats.cas -eq '404' -and $d.stats.reessai) { $script:TableauMaj.business = $now.AddSeconds(-270) }     # cache de l'API pas à jour : UN seul nouvel essai dans 30 s
        $b.maj = $now.ToString('HH:mm')
        $script:Tableau.business = $b
    }
    if (($now - $script:TableauMaj.actus).TotalMinutes -ge 15) {
        $script:TableauMaj.actus = $now
        $script:Tableau.actus = Get-ActualitesTableau
    }
}
function Get-ActualitesTableau {
    # Titres DU JOUR des seules sources validées par Liam (config.json, veille.flux[].valide = true). Aucune source financière n'est branchée.
    if (-not (Get-Command Get-Actualites -ErrorAction SilentlyContinue)) { return @{ dispo = $false; raison = 'Actualités : module de veille absent' } }
    $valides = @($Config.veille.flux | Where-Object { $_ -and $_.valide -eq $true })
    if (-not $valides.Count) {
        $rm = if (Get-Command Get-RaisonMarche -ErrorAction SilentlyContinue) { Get-RaisonMarche } else { $null }
        if (-not $rm -and (Get-Command Read-DernierReleve -ErrorAction SilentlyContinue)) {      # sources de marché actives : titres de leur dernier relevé
            $r = Read-DernierReleve
            if ($r) { return @{ dispo = $true; items = @(@($r.actus) | Select-Object -First 8 | ForEach-Object { @{ titre = "$($_.titre)"; source = "$($_.source)"; date = ([datetime](ConvertTo-DateMarche $_.date)).ToString('dd/MM HH:mm') } }); manque = @($r.erreurs | ForEach-Object { "$_" }); maj = (Get-Date).ToString('HH:mm') } }
            return @{ dispo = $false; raison = 'En attente du premier relevé de la veille de fond.' }
        }
        return @{ dispo = $false; raison = $(if ($rm) { $rm } else { 'Source non branchée : aucune source d''actualités validée (veille.flux).' }) }
    }
    try {
        $a = Get-Actualites (Get-Date).Date
        $items = @($a.items | Select-Object -First 8 | ForEach-Object { @{ titre = "$($_.titre)"; source = "$($_.source)"; date = ([datetime]$_.date).ToString('dd/MM HH:mm') } })
        @{ dispo = $true; items = $items; manque = @($a.manque | ForEach-Object { "$_" }); maj = (Get-Date).ToString('HH:mm') }
    } catch { @{ dispo = $false; raison = 'Actualités : lecture impossible' } }
}
function Get-JournalRecent([int]$n = 7) {
    $f = Join-Path (Get-DossierLogs) ("journal-{0}.md" -f (Get-Date -Format 'yyyy-MM-dd'))
    if (-not (Test-Path $f)) { return , @() }
    $txt = Get-Content $f -Raw -Encoding UTF8
    $blocs = [regex]::Matches($txt, '(?ms)^## (\d\d:\d\d:\d\d)\s*\r?\n- \*\*Ordre :\*\* (.*?)\r?\n- \*\*Action :\*\* (.*?)\r?\n- \*\*Résultat :\*\* (.*?)\r?\n')
    # Les lignes "Parole" restent dans le journal complet mais n'encombrent pas le panneau
    $res = @($blocs | Where-Object { $_.Groups[3].Value -notlike 'Parole*' } | Select-Object -Last $n | ForEach-Object { @{ h = $_.Groups[1].Value; action = (Short $_.Groups[3].Value.Trim() 90); resultat = (Short $_.Groups[4].Value.Trim() 90) } })
    , $res
}

function Get-DonneesTableau {
    $todo = @(Get-TodoOuverte | Select-Object -First 8)
    $j = Get-JournalRecent 5
    @{
        etat = $script:VisageEtatVal
        mode = "$($Config.mode_affichage)"
        systeme = $script:Tableau.systeme
        site = $script:Tableau.site
        business = $script:Tableau.business
        actus = $script:Tableau.actus
        mode_jeu = [bool]($script:ModeJeu -eq $true)
        alertes = @($(if (Get-Command Get-AlertesPanneau -ErrorAction SilentlyContinue) { Get-AlertesPanneau 6 }))
        micro = $(if (Get-Command Get-DonneesMicro -ErrorAction SilentlyContinue) { Get-DonneesMicro } else { $null })
        todo = @($todo)
        taches = @(Get-TachesTodo)
        actus_secondes = $(if ($Config.PSObject.Properties['actualites_secondes'] -and "$($Config.actualites_secondes)" -match '^\d+$') { [math]::Max(3, [math]::Min(120, [int]$Config.actualites_secondes)) } else { 10 })
        briefing = @($script:BriefingLignes)
        marche = $(if (Get-Command Get-DonneesMarche -ErrorAction SilentlyContinue) { if ($script:MarchePanneau) { $script:MarchePanneau } else { Get-DonneesMarche } } else { $null })
        dossier = $script:Dossier
        capacites = $(if ((Get-Variable -Name CapacitesJusqua -Scope Script -ErrorAction SilentlyContinue) -and (Get-Date) -lt $script:CapacitesJusqua) { @($script:Capacites) } else { $null })
        diag = @($(if (Get-Command Get-DiagPanneau -ErrorAction SilentlyContinue) { Get-DiagPanneau 8 }))
        fenetre_ordre = $(if (Get-Command Get-FenetreOrdreRestante -ErrorAction SilentlyContinue) { Get-FenetreOrdreRestante } else { 0 })
        moteur_voix = "$script:MoteurVoix"
        surveiller = $(if (Get-Variable -Name Surveiller -Scope Script -ErrorAction SilentlyContinue) { $script:Surveiller } else { $null })
        priorite = $(if (Get-Command Get-PrioriteEffective -ErrorAction SilentlyContinue) { @{ demandee = (Get-PrioriteDemandee); effective = (Get-PrioriteEffective) } } else { $null })
        musique = $(if (Get-Command Get-EtatMusique -ErrorAction SilentlyContinue) { $em = Get-EtatMusique; @{ volume = [int]((Get-VolumeBase) * 100); coupee = [bool]$em.coupee } } else { $null })
        journal = @($j)
        conversation = @($(if (Get-Command Get-ConversationRecente -ErrorAction SilentlyContinue) { Get-ConversationRecente 40 }))
        guide = $(if ($script:Guide) { @{ titre = $script:Guide.titre; etapes = @($script:Guide.etapes); courant = $script:Guide.courant } } else { $null })
    }
}
