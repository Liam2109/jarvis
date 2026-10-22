# PILOTAGE : workspace (page visage\pilotage.html) + barre de widgets et menu (visage\widgets.js, chargé par visage\index.html). DÉSACTIVÉ par défaut (config.json « pilotage_actif » = "non" : toutes les routes répondent 404).
# AUCUNE nouvelle écoute réseau : mêmes serveur 127.0.0.1, même jeton, mêmes contrôles d'hôte et d'origine que lib\visage.ps1, mêmes pages servies par liste blanche (comme les vues).
# LECTURE : /pilotage-donnees et /pilotage-widgets (jeton) renvoient des champs choisis un par un, nettoyés (secrets masqués, jetons longs retirés, texte tronqué) : jamais .env, jetons, clés, config.local.json, valeurs de config ni contenu des mails.
# ÉCRITURE : POST /pilotage-action (approuver / rejeter / plus tard) appelle Invoke-InitiativeCommande, la MÊME fonction que les commandes Discord de lib\initiatives.ps1 (donc mêmes règles : skill_propose et leçons jamais approuvés seuls).
#           POST /pilotage-widget passe par Invoke-UneAction (actions et niveaux de permission existants) ; seule la réactivation du micro utilise le mécanisme existant Set-Actif (touche Alt + +). En sourdine, seul le micro répond.
# Partage d'écran et caméra : non branchés (aucune capture d'écran ni caméra). Les textes venant de fichiers ou de mails sont des DONNÉES : la page les affiche avec textContent, jamais avec innerHTML.

$script:PilotageFichiers = @('pilotage.js', 'widgets.js')
$script:PilotageTypes = @{ rappel = 'Rappel'; suggestion = 'Suggestion'; skill_propose = 'Proposition'; maintenance = 'Maintenance' }

function Get-PilotageConfig {
    $c = @{ actif = $false }
    if ($Config.PSObject.Properties['pilotage_actif'] -and "$($Config.pilotage_actif)".Trim().ToLower() -in @('oui', 'true', '1', 'on', 'yes')) { $c.actif = $true }
    $c
}
function ConvertTo-PilotageTexte($x, [int]$max = 200) {
    # Donnée de fichier -> texte court d'une ligne : secrets masqués, jetons longs retirés, caractères de contrôle retirés.
    $t = (Hide-Secrets "$x") -replace '[\u0000-\u001f\u007f]', ' ' -replace '[A-Za-z0-9_\-]{32,}', '[…]' -replace '\s+', ' '
    $t = $t.Trim(); if ($t.Length -gt $max) { $t.Substring(0, $max - 1) + '…' } else { $t }
}
function Get-FichierPilotageHttp([string]$chemin) {
    # @{ corps; type } ou $null : visage\pilotage.js et visage\widgets.js seulement (liste blanche, casse exacte). Désactivé : rien.
    if (-not (Get-PilotageConfig).actif) { return $null }
    if ($chemin -cmatch '^/pilotage/([a-z]+\.js)$' -and $Matches[1] -in $script:PilotageFichiers) {
        $f = Join-Path $script:JarvisRoot "visage\$($Matches[1])"; if (Test-Path $f -PathType Leaf) { return @{ corps = [IO.File]::ReadAllText($f, [Text.Encoding]::UTF8); type = 'text/javascript; charset=utf-8' } }
    }
    $null
}
function Get-PagePilotage([string]$jeton) {
    # visage\pilotage.html avec le jeton de la session (comme la salle de marché). $null si désactivé.
    if (-not (Get-PilotageConfig).actif) { return $null }
    $f = Join-Path $script:JarvisRoot 'visage\pilotage.html'; if (-not (Test-Path $f)) { return $null }
    [IO.File]::ReadAllText($f, [Text.Encoding]::UTF8).Replace('__TOKEN__', $jeton)
}

# ---------- Lecture ----------
function Get-PilotageOptions {
    # État (oui / non) des options *_actif, *_auto et quelques veilles. Jamais une autre valeur : chaîne libre, chemin, jeton -> « défini ».
    $res = @()
    foreach ($p in ($Config.PSObject.Properties | Sort-Object Name)) {
        if ($p.Name -notmatch '(_actif|_auto)$|^veille_(train|mail|candidatures)$|^mode_serveur$|^initiatives_niveau$' -or $p.Name -match '(?i)token|jeton|secret|cle|key|pass|mdp') { continue }
        $v = $p.Value; $txt = $(if ($v -is [bool]) { $(if ($v) { 'oui' } else { 'non' }) } elseif ("$v".Trim().ToLower() -in @('oui', 'non')) { "$v".Trim().ToLower() } elseif ($p.Name -eq 'initiatives_niveau' -and "$v" -match '^[0-5]$') { "niveau $v" } else { 'défini' })
        $res += [ordered]@{ nom = "$($p.Name)"; etat = $txt }
    }
    @($res)
}
function Get-PilotageInitiatives {
    $now = Get-Date; $att = @(); $mnt = @()
    foreach ($i in @(Get-Initiatives)) {
        $dt = [datetime]::MinValue; [void][datetime]::TryParse("$($i.cree_le)", [Globalization.CultureInfo]::InvariantCulture, [Globalization.DateTimeStyles]::RoundtripKind, [ref]$dt)
        $o = [ordered]@{ id = "$($i.id)"; titre = (ConvertTo-PilotageTexte $i.titre 110); type = "$($i.type)"; type_libelle = $(if ($script:PilotageTypes.ContainsKey("$($i.type)")) { $script:PilotageTypes["$($i.type)"] } else { 'Autre' }); raison = (ConvertTo-PilotageTexte $i.raison 220)
            urgence = $(if ("$($i.urgence)" -eq 'haute') { 'haute' } else { 'normale' }); statut = "$($i.statut)"; source = (ConvertTo-PilotageTexte $i.source 30); age_heures = $(if ($dt -gt [datetime]::MinValue) { [int][math]::Max(0, ($now - $dt).TotalHours) } else { 0 }) }
        if ("$($i.statut)" -eq 'en_attente' -and "$($i.type)" -ne 'maintenance') { $att += $o }
        elseif (("$($i.statut)" -eq 'en_attente' -and "$($i.type)" -eq 'maintenance') -or "$($i.statut)" -eq 'oubliee') { $mnt += $o }
    }
    @{ en_attente = @($att); maintenance = @($mnt); a_traiter = @(Get-Initiatives 'en_attente').Count }
}
function Get-DonneesPilotage {
    # $null si désactivé. Aucun secret : chaque champ est choisi ici, un par un.
    if (-not (Get-PilotageConfig).actif) { return $null }
    $ini = Get-PilotageInitiatives
    $oui = { param($k) [bool]($Config.PSObject.Properties[$k] -and "$($Config.$k)".Trim().ToLower() -in @('oui', 'true', '1', 'on', 'yes')) }
    $nuitI = ''; try { $nuitI = "$((Get-InitEtat).derniere_nuit)" } catch {}; $nuitL = ''; if (Get-Command Get-LeconsEtat -ErrorAction SilentlyContinue) { try { $nuitL = "$((Get-LeconsEtat).derniere_nuit)" } catch {} }
    $apercu = [ordered]@{ voix_active = [bool](Test-VoixActive); sourdine = [bool]($script:Actif -eq $false); mode_jeu = [bool]($script:ModeJeu -eq $true)
        veilles = @([ordered]@{ nom = 'Annonces-train'; actif = (& $oui 'veille_train') }, [ordered]@{ nom = 'Annonces par e-mail'; actif = (& $oui 'veille_mail') }, [ordered]@{ nom = 'Marché'; actif = [bool]($Config.PSObject.Properties['marche_actif'] -and $Config.marche_actif -eq $true) }, [ordered]@{ nom = 'Initiatives'; actif = (& $oui 'initiatives_actif') })
        initiatives_a_traiter = $ini.a_traiter; derniere_revue_initiatives = $nuitI; derniere_revue_lecons = $nuitL }
    $missions = @(); $dev = Read-JsonMemoire 'dev-agent.json'
    if ($dev -and $dev.PSObject.Properties['taches']) { $missions = @($dev.taches | Select-Object -Last 12 | ForEach-Object { [ordered]@{ id = "$($_.id)"; texte = (ConvertTo-PilotageTexte $_.texte 160); statut = (ConvertTo-PilotageTexte $_.statut 20); nuit = (ConvertTo-PilotageTexte $_.nuit 12); raison = (ConvertTo-PilotageTexte $_.raison 160) } }) }
    $todo = @(); if (Get-Command Get-TachesTodo -ErrorAction SilentlyContinue) { $todo = @(Get-TachesTodo 4 | ForEach-Object { [ordered]@{ texte = (ConvertTo-PilotageTexte $_.texte 160); fait = [bool]$_.fait } }) }
    $cand = @(); if (Get-Command Get-CandEtat -ErrorAction SilentlyContinue) { $cand = @((Get-CandEtat).candidatures | Select-Object -Last 15 | ForEach-Object { [ordered]@{ entreprise = (ConvertTo-PilotageTexte $_.entreprise 70); poste = (ConvertTo-PilotageTexte $_.poste 90); statut = (ConvertTo-PilotageTexte $_.statut 20); date = (ConvertTo-PilotageTexte $_.date 12) } }) }      # (ni résumé, ni lien, ni contenu des mails)
    $series = @(); $rel = Read-JsonMemoire 'saas-releves.json'
    if ($rel -and $rel.PSObject.Properties['jours'] -and $rel.jours) {
        $jours = @($rel.jours.PSObject.Properties | Sort-Object Name | Select-Object -Last 30)
        foreach ($m in @(@('abonnes_actifs', 'Abonnés actifs'), @('quiz_total', 'Quiz (total)'), @('quiz_24h', 'Quiz sur 24 h'), @('emails_24h', 'E-mails sur 24 h'), @('nouveaux_abonnes_24h', 'Nouveaux abonnés sur 24 h'))) {
            $pts = @(); foreach ($j in $jours) { $v = $j.Value.PSObject.Properties[$m[0]]; if ($v -and "$($v.Value)" -match '^-?\d+(\.\d+)?$') { $pts += [ordered]@{ date = "$($j.Name)"; valeur = [double]$v.Value } } }
            if ($pts.Count) { $series += [ordered]@{ cle = $m[0]; nom = $m[1]; points = @($pts) } }
        }
    }
    $conv = @(); if (Get-Command Get-ConversationRecente -ErrorAction SilentlyContinue) { $conv = @(Get-ConversationRecente 8 | Where-Object { $_.role -ne 'action' } | ForEach-Object { [ordered]@{ role = "$($_.role)"; h = (ConvertTo-PilotageTexte $_.h 8); texte = (ConvertTo-PilotageTexte $_.texte 300) } }) }
    $cap = $null; if (Get-Command Get-CapacitesDonnees -ErrorAction SilentlyContinue) { $d = Get-CapacitesDonnees; $f = { param($l) @($l | ForEach-Object { [ordered]@{ nom = (ConvertTo-PilotageTexte $_.nom 40); etat = (ConvertTo-PilotageTexte $_.etat 20); description = (ConvertTo-PilotageTexte $_.description 140) } }) }; $cap = [ordered]@{ skills = @(& $f $d.skills); presets = @(& $f $d.presets); vues = @(& $f $d.vues); presets_actif = [bool]$d.presets_actif; vues_actif = [bool]$d.vues_actif } }
    [ordered]@{ apercu = $apercu; initiatives = $ini; missions = $missions; taches = [ordered]@{ todo = $todo; candidatures = $cand }; analytics = [ordered]@{ series = $series }; conversation = $conv; config = @(Get-PilotageOptions); capacites = $cap; widgets = (Get-WidgetsPilotage) }
}
function Get-WidgetsPilotage {
    # Léger (sondé toutes les 2 s par la barre de widgets) : état du micro, de la musique, noms des dossiers autorisés (jamais leurs chemins).
    if (-not (Get-PilotageConfig).actif) { return $null }
    $coupee = $false; if (Get-Command Get-EtatMusique -ErrorAction SilentlyContinue) { try { $coupee = [bool](Get-EtatMusique).coupee } catch {} }
    $dos = @(); if (Get-Command Get-DossiersAutorises -ErrorAction SilentlyContinue) { try { $dos = @((Get-DossiersAutorises).Keys | Sort-Object | ForEach-Object { ConvertTo-PilotageTexte $_ 30 }) } catch {} }
    [ordered]@{ micro_actif = [bool]($script:Actif -ne $false); musique_coupee = $coupee; dossiers = @($dos); partage_branche = $false; camera_branchee = $false }
}

# ---------- Écriture : les mêmes fonctions que Discord ----------
function Invoke-AvecTamponPilotage([scriptblock]$bloc) {
    # Exécute un bloc qui répond par Add-TamponDiscord / Add-EmbedDiscord et en récupère le texte, sans toucher à une conversation Discord en cours.
    $oldT = $script:DiscordTampon; $oldE = @($script:DiscordEmbeds); $oldC = $script:CanalDiscord
    $script:DiscordTampon = New-Object System.Collections.Generic.List[string]; $script:DiscordEmbeds.Clear(); $script:CanalDiscord = 'pilotage'      # (le plafond d'appels à Claude des ordres Discord s'applique)
    try { $r = & $bloc; $txt = (@($script:DiscordTampon) + @($script:DiscordEmbeds | ForEach-Object { "$($_.titre) $($_.description)" })) -join ' ' }
    finally { $script:DiscordTampon = $oldT; $script:DiscordEmbeds.Clear(); foreach ($e in $oldE) { [void]$script:DiscordEmbeds.Add($e) }; $script:CanalDiscord = $oldC }
    @{ traite = [bool]$r; texte = (ConvertTo-PilotageTexte $txt 400) }
}
function Invoke-PilotageAction($c) {
    # Corps : { action : approuver | rejeter | plus_tard ; id }. Même fonction que « approuver 3 », « rejeter 3 », « plus tard 3 » sur Discord.
    if (-not (Get-PilotageConfig).actif) { return @{ ok = $false; texte = 'désactivé' } }
    $id = "$($c.id)"; $a = "$($c.action)"
    if ($id -notmatch '^\d{1,6}$' -or $a -cnotin 'approuver', 'rejeter', 'plus_tard') { return @{ ok = $false; texte = 'demande invalide' } }
    $cmd = $(switch ($a) { 'approuver' { "approuver $id" } 'rejeter' { "rejeter $id" } default { "plus tard $id" } })
    Write-Journal -Ordre $cmd -Action 'Pilotage : bouton' -Resultat "initiative n° $id : $a (même fonction que la commande Discord)"
    $avant = "$((Get-Initiative $id).statut)"
    $r = Invoke-AvecTamponPilotage { Invoke-InitiativeCommande $cmd }
    $voulu = $(switch ($a) { 'approuver' { 'approuvee' } 'rejeter' { 'rejetee' } default { 'plus_tard' } })
    @{ ok = [bool]($r.traite -and $avant -in 'en_attente', 'plus_tard', 'oubliee' -and "$((Get-Initiative $id).statut)" -eq $voulu); texte = $r.texte }      # (ok = la décision a bien été prise maintenant ; sinon le texte dit pourquoi : déjà décidée, introuvable...)
}
function Invoke-PilotageWidget($c) {
    # Corps : { widget : micro | musique | dossier | partage | camera ; etat | nom }. Chaque bouton passe par une action existante et ses niveaux de permission.
    if (-not (Get-PilotageConfig).actif) { return @{ ok = $false; texte = 'désactivé' } }
    $w = "$($c.widget)"
    if ($w -in 'partage', 'camera') { return @{ ok = $false; texte = 'pas branché' } }
    if ($w -cnotin 'micro', 'musique', 'dossier') { return @{ ok = $false; texte = 'demande invalide' } }
    if ($w -eq 'micro') {
        $voulu = [bool]$c.etat
        if ($voulu) { Set-Actif $true 'bouton micro (pilotage)'; Write-Journal -Action 'Pilotage : micro' -Resultat 'réactivé (mécanisme existant, comme Alt + +)'; return @{ ok = $true; texte = 'Jarvis est réactivé.' } }
        $r = Invoke-UneAction ([pscustomobject]@{ type = 'sourdine' }) 'bouton micro (pilotage)'
        return @{ ok = [bool]($r -and $r.ok); texte = $(if ($r) { ConvertTo-PilotageTexte $r.texte 120 } else { 'refusé' }) }
    }
    if ($script:Actif -eq $false) { return @{ ok = $false; texte = 'Jarvis est en sourdine : réactivez-le d''abord (bouton micro).' } }
    if ($w -eq 'musique') {
        $r = Invoke-UneAction ([pscustomobject]@{ type = 'musique'; commande = $(if ([bool]$c.coupee) { 'couper' } else { 'remettre' }) }) 'bouton musique (pilotage)'
        return @{ ok = [bool]($r -and $r.ok); texte = $(if ($r) { ConvertTo-PilotageTexte $r.texte 120 } else { 'refusé' }) }
    }
    $noms = @(); if (Get-Command Get-DossiersAutorises -ErrorAction SilentlyContinue) { $noms = @((Get-DossiersAutorises).Keys) }
    if ("$($c.nom)" -cnotin $noms) { return @{ ok = $false; texte = 'dossier absent de la liste autorisée' } }
    $r = Invoke-UneAction ([pscustomobject]@{ type = 'pc_dossier'; nom = "$($c.nom)" }) 'bouton dossier (pilotage)'
    @{ ok = [bool]($r -and $r.ok); texte = $(if ($r) { ConvertTo-PilotageTexte $r.texte 120 } else { 'refusé' }) }
}
