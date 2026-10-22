# PRESETS : une phrase déclenche une suite d'étapes. DÉSACTIVÉS par défaut (config.json « presets_actif » = "non").
# Un preset = nom, phrases déclencheuses, étapes. Chaque étape est UNE action existante, déjà classée par lib\permissions.ps1 (Get-Niveau < 3) ET dans la liste blanche ci-dessous
# (ouvrir un dossier / une appli / un site, régler un mode, afficher une vue, charger un point...). Chaque étape passe par Invoke-UneAction : son niveau reste celui de l'action (jamais contourné ni abaissé),
# une étape de niveau 2 demande « Vous confirmez, monsieur ? » comme d'habitude, un refus arrête le preset. Aucun envoi à des tiers : envoyer_message, powershell, executer_script... ne sont pas dans la liste.
# Fichiers : memoire\presets\<nom>.json (un par preset, créés au premier usage). Trois exemples sont préparés au premier usage, À VALIDER avant toute activation.
# Création par texte : « crée un preset X avec ouvre chrome, point saas » -> Jarvis PROPOSE (initiative skill_propose, jamais approuvée automatiquement) ; rien n'est enregistré avant « approuver ».
# Commandes : presets, lance le preset <nom>, désactive le preset <nom>, active le preset <nom>, crée un preset <nom> avec ... ; ou la phrase déclencheuse du preset.

$script:PresetsExecuteur = $null
$script:PresetsActionsPermises = @('ouvrir_app', 'fermer_app', 'pc_fermer', 'ouvrir_site', 'ouvrir_chemin', 'pc_dossier', 'vscode_ouvrir', 'mode_pc', 'mode_jeu', 'point_saas', 'briefing_details', 'resume_jour', 'reste_a_faire',
    'todo_lire', 'etat_systeme', 'etat_site', 'musique', 'volume', 'luminosite', 'pc_fenetre', 'pc_reduire_tout', 'salle_marche', 'salle_marche_fermer', 'vue_montrer', 'vue_fermer', 'disposition_enregistrer', 'disposition_restaurer')
$script:PresetsParamPrincipal = @{ ouvrir_app = 'nom'; fermer_app = 'nom'; pc_fermer = 'nom'; ouvrir_site = 'url'; ouvrir_chemin = 'chemin'; pc_dossier = 'nom'; vscode_ouvrir = 'chemin'; mode_pc = 'nom'; vue_montrer = 'nom'; volume = 'niveau'; luminosite = 'niveau'; musique = 'commande'; salle_marche = 'nom'; mode_jeu = 'etat' }
$script:PresetsExemples = @(
    @{ nom = 'saas'; description = 'Se mettre au travail sur le SaaS : dossier du projet, page du site, point SaaS.'; declencheurs = @('je veux bosser sur le saas', 'on bosse sur le saas', 'bosser sur le saas')
       etapes = @(@{ action = 'pc_dossier'; params = @{ nom = 'projets' } }, @{ action = 'ouvrir_site'; params = @{ url = 'https://tonproduit.shop' } }, @{ action = 'point_saas'; params = @{} }) },
    @{ nom = 'mode-streamer'; description = 'Préparer un direct : coupe la musique, règle la luminosité, ouvre OBS.'; declencheurs = @('mode streamer', 'je lance un stream')
       etapes = @(@{ action = 'musique'; params = @{ commande = 'couper' } }, @{ action = 'luminosite'; params = @{ niveau = 80 } }, @{ action = 'ouvrir_app'; params = @{ nom = 'obs' } }) },
    @{ nom = 'mode-nuit'; description = 'Fin de journée : bilan du soir, ferme les applis de travail, mode nuit.'; declencheurs = @('mode nuit', 'je vais me coucher')
       etapes = @(@{ action = 'resume_jour'; params = @{} }, @{ action = 'fermer_app'; params = @{ nom = 'vscode' } }, @{ action = 'fermer_app'; params = @{ nom = 'chrome' } }, @{ action = 'mode_pc'; params = @{ nom = 'nuit' } }) })

function Get-PresetsConfig {
    $c = @{ actif = $false }
    if ($Config.PSObject.Properties['presets_actif'] -and "$($Config.presets_actif)".Trim().ToLower() -in @('oui', 'true', '1', 'on', 'yes')) { $c.actif = $true }
    $c
}
function Get-PresetNorm([string]$s) { $n = ((("$s").ToLowerInvariant().Normalize([Text.NormalizationForm]::FormD) -replace '\p{Mn}', '') -replace "[’']", ' ' -replace '[^a-z0-9]+', ' ').Trim(); ($n -replace '^(?:jarvis )+', '') }
function Get-PresetsDossier { Join-Path (Split-Path (Get-FichierMemoire 'presets.dossier')) 'presets' }      # (sans le créer : il n'existe qu'au premier enregistrement)
function ConvertTo-PresetObjet($o) {
    if (-not $o) { return $null }
    $e = @($o.etapes | Where-Object { $_ } | ForEach-Object { $p = @{}; if ($_.params) { foreach ($q in $_.params.PSObject.Properties) { $p[$q.Name] = $q.Value } }; $h = [ordered]@{ action = "$($_.action)"; params = $p }; if ($_.PSObject.Properties['niveau']) { $h.niveau = [int]$_.niveau }; $h })
    $h = [ordered]@{}; foreach ($p in $o.PSObject.Properties) { if ($p.Name -notin 'etapes', 'declencheurs') { $h[$p.Name] = $p.Value } }
    $h.declencheurs = @($o.declencheurs | ForEach-Object { "$_" }); $h.etapes = @($e); $h
}
function Get-Presets {
    $d = Get-PresetsDossier; if (-not (Test-Path $d)) { return @() }
    @(Get-ChildItem $d -Filter *.json -File | Where-Object { $_.Name -notlike '_*' } | Sort-Object Name | ForEach-Object { try { ConvertTo-PresetObjet (Get-Content $_.FullName -Raw -Encoding UTF8 | ConvertFrom-Json) } catch { $null } } | Where-Object { $_ -and $_.nom })
}
function Get-Preset([string]$nom) { $n = Get-PresetNorm $nom; @(Get-Presets | Where-Object { (Get-PresetNorm "$($_.nom)") -eq $n }) | Select-Object -First 1 }
function Save-Preset($p) { Save-JsonMemoire "presets\$($p.nom).json" $p }

# ---------- Validation : étapes classées, niveaux jamais modifiés ----------
function ConvertTo-PresetAction($etape) { $o = [ordered]@{ type = "$($etape.action)" }; foreach ($k in $etape.params.Keys) { $o[$k] = $etape.params[$k] }; [pscustomobject]$o }
function Test-PresetManifeste($p) {
    # @{ ok; motifs }
    $mo = @()
    if (-not $p) { return @{ ok = $false; motifs = @('preset absent ou illisible') } }
    if ("$($p.nom)" -notmatch '^[a-z][a-z0-9-]{1,29}$') { $mo += 'nom non kebab-case' }
    if (-not "$($p.description)".Trim() -or "$($p.description)".Length -gt 160) { $mo += 'description absente ou trop longue' }
    if (@($p.declencheurs | Where-Object { $_ }).Count -lt 1 -or @($p.declencheurs).Count -gt 6) { $mo += 'phrases déclencheuses : 1 à 6' }
    foreach ($d in @($p.declencheurs | Where-Object { $_ })) { if (-not (Get-PresetNorm $d) -or (Get-PresetNorm $d).Length -gt 60) { $mo += "phrase déclencheuse invalide : $d" } }
    $et = @($p.etapes)
    if ($et.Count -lt 1 -or $et.Count -gt 8) { $mo += 'étapes : 1 à 8' }
    $i = 0
    foreach ($e in $et) {
        $i++; $a = "$($e.action)"
        if ($a -notin $script:PresetsActionsPermises) { $mo += "étape $i : l'action « $a » n'est pas dans la liste des actions permises pour un preset"; continue }
        if (-not $script:Actions -or -not $script:Actions.ContainsKey($a)) { $mo += "étape $i : l'action « $a » n'est pas classée (inconnue des permissions)"; continue }
        foreach ($k in @($e.params.Keys)) {
            $v = $e.params[$k]
            if ($k -notmatch '^[a-z_]{1,20}$' -or -not ($v -is [string] -or $v -is [int] -or $v -is [long] -or $v -is [bool] -or $v -is [double])) { $mo += "étape $i : paramètre invalide ($k)"; continue }
            if ("$v".Length -gt 120 -or "$v" -match '[\r\n]') { $mo += "étape $i : valeur trop longue ou sur plusieurs lignes ($k)" }
            if ((Hide-Secrets "$v") -ne "$v") { $mo += "étape $i : secret dans le paramètre $k" }
        }
        if ($a -eq 'ouvrir_site' -and "$($e.params.url)" -notmatch '^https?://[^\s]+$') { $mo += "étape $i : ouvrir_site demande une adresse http(s)" }
        if ((Get-Command Test-InitiativeInterdite -ErrorAction SilentlyContinue)) { $r = Test-InitiativeInterdite "$a $(@($e.params.Values) -join ' ')"; if ($r) { $mo += "étape $i : $r" } }
        $niv = (Get-Niveau (ConvertTo-PresetAction $e)).niveau
        if ($niv -ge 3) { $mo += "étape $i : « $a » est de niveau $niv (refusé par les permissions)" }
        elseif ($e.Contains('niveau') -and [int]$e.niveau -ne $niv) { $mo += "étape $i : niveau déclaré $($e.niveau) différent du niveau réel $niv de « $a » (un preset ne change aucun niveau)" }
    }
    @{ ok = ($mo.Count -eq 0); motifs = @($mo) }
}
function Format-PresetEtape($e) {
    $pp = $script:PresetsParamPrincipal["$($e.action)"]; if ($pp -and $e.params.Contains($pp)) { "$($e.action):$($e.params[$pp])" } else { "$($e.action)" }
}

# ---------- Étapes décrites en texte ----------
function ConvertFrom-PresetEtapeTexte([string]$t) {
    # « ouvre chrome » -> @{ action; params } ; $null si la phrase n'est pas une étape connue
    $n = Get-PresetNorm $t; if (-not $n) { return $null }
    $dom = '[a-z0-9][a-z0-9.-]*\.[a-z]{2,}(?:/\S*)?'
    if ($n -match '^(?:ouvre|ouvrir)(?: le)? dossier (.+)$') { return @{ action = 'pc_dossier'; params = @{ nom = $Matches[1] } } }
    $ms = [regex]::Match("$t".Trim(), "(?i)^(?:ouvre|ouvrir)(?: le)? site\s+(https?://\S+|$dom)$")      # (adresse lue sur le texte brut : la forme normalisée perd les points et les deux-points)
    if ($ms.Success) { $u = $ms.Groups[1].Value.ToLower(); if ($u -notmatch '^https?://') { $u = "https://$u" }; return @{ action = 'ouvrir_site'; params = @{ url = $u } } }
    if ($n -match '^(?:montre|affiche|ouvre)(?: la| le)? vue (.+)$') { return @{ action = 'vue_montrer'; params = @{ nom = $Matches[1] } } }
    if ($n -match '^(?:ferme|fermer) (?:l application |l appli |application )?(.+)$') { return @{ action = 'fermer_app'; params = @{ nom = $Matches[1] } } }
    if ($n -match '^(?:mode|passe en mode|passe en) (.+)$') { return @{ action = 'mode_pc'; params = @{ nom = $Matches[1] } } }
    if ($n -match '^(?:charge |donne |fais |lis )?(?:le )?point (?:du |de |sur le )?saas$') { return @{ action = 'point_saas'; params = @{} } }
    if ($n -match '^(?:le )?(?:bilan(?: du soir)?|resume du jour|resume de la journee)$') { return @{ action = 'resume_jour'; params = @{} } }
    if ($n -match '^(?:lis |montre |affiche )?(?:la |ma )?(?:to do|todo|liste de taches|taches)$') { return @{ action = 'todo_lire'; params = @{} } }
    if ($n -match '^(?:coupe|baisse) la musique$') { return @{ action = 'musique'; params = @{ commande = $(if ($n -match '^coupe') { 'couper' } else { 'baisser' }) } } }
    if ($n -match '^(?:regle )?(?:le )?volume (?:a )?(\d{1,3})$') { return @{ action = 'volume'; params = @{ niveau = [int]$Matches[1] } } }
    if ($n -match '^(?:regle )?(?:la )?luminosite (?:a )?(\d{1,3})$') { return @{ action = 'luminosite'; params = @{ niveau = [int]$Matches[1] } } }
    if ($n -match '^(?:ouvre|ouvrir|lance|lancer) (?:l application |l appli |application )?([a-z0-9][a-z0-9 ]{1,30})$') { return @{ action = 'ouvrir_app'; params = @{ nom = $Matches[1] } } }
    $null
}

# ---------- Exemples (au premier usage) ----------
function Initialize-PresetsExemples {
    # Trois exemples, À VALIDER : fichiers statut « a_valider » + une initiative « Valider le preset » chacun. Une seule fois (memoire\presets\_exemples.json).
    $d = Get-PresetsDossier; if (Test-Path (Join-Path $d '_exemples.json')) { return 0 }
    $n = 0
    foreach ($x in $script:PresetsExemples) {
        $p = [ordered]@{ nom = $x.nom; description = $x.description; declencheurs = @($x.declencheurs); etapes = @($x.etapes | ForEach-Object { [ordered]@{ action = $_.action; params = $_.params } }); statut = 'a_valider'; version = 1; cree_le = (Get-Date).ToString('o'); exemple = $true }
        if (Get-Preset $p.nom) { continue }
        Save-Preset $p; $n++
        if (Get-Command Add-Initiative -ErrorAction SilentlyContinue) { $r = Add-Initiative "Valider le preset « $($p.nom) »" 'skill_propose' ("Étapes : " + ((@($p.etapes) | ForEach-Object { Format-PresetEtape $_ }) -join ' ; ') + ".") 'normale' 1 'presets'; if ($r.ok -and (Get-Command Send-InitiativeCarte -ErrorAction SilentlyContinue)) { [void](Send-InitiativeCarte $r.initiative) } }
    }
    Save-JsonMemoire 'presets\_exemples.json' ([ordered]@{ date = (Get-Date).ToString('o'); crees = $n })
    Write-Journal -Action 'Presets : exemples' -Resultat "$n exemple(s) préparé(s), à valider avant activation"
    $n
}

# ---------- Proposer, décider ----------
function New-PresetProposition([string]$nom, [string]$etapesTexte) {
    # « crée un preset X avec ... » : propose via lib\initiatives.ps1 (skill_propose). RIEN n'est enregistré. @{ ok; motif; initiative }
    if ($nom -notmatch '^[a-z][a-z0-9-]{1,29}$') { return @{ ok = $false; motif = 'nom non kebab-case (lettres minuscules, chiffres, tirets)'; initiative = $null } }
    if (Get-Preset $nom) { return @{ ok = $false; motif = 'ce preset existe déjà'; initiative = $null } }
    $parts = @("$etapesTexte" -split '\s*(?:,|;|\bpuis\b|\bet puis\b|\bet\b)\s*' | Where-Object { $_.Trim() })
    if (-not $parts.Count -or $parts.Count -gt 8) { return @{ ok = $false; motif = 'de 1 à 8 étapes'; initiative = $null } }
    $etapes = @(); $inconnues = @()
    foreach ($t in $parts) { $e = ConvertFrom-PresetEtapeTexte $t; if ($e) { $etapes += [ordered]@{ action = $e.action; params = $e.params } } else { $inconnues += $t.Trim() } }
    if ($inconnues.Count) { return @{ ok = $false; motif = "je ne sais pas encore faire : " + ($inconnues -join ' ; '); initiative = $null } }
    $p = [ordered]@{ nom = $nom; description = "Preset $nom ($($etapes.Count) étape$(if ($etapes.Count -gt 1) { 's' }))."; declencheurs = @($nom -replace '-', ' '); etapes = $etapes }
    $v = Test-PresetManifeste $p; if (-not $v.ok) { return @{ ok = $false; motif = ($v.motifs | Select-Object -First 2) -join ' ; '; initiative = $null } }
    $codes = (@($etapes | ForEach-Object { Format-PresetEtape $_ }) -join ' ; ')
    if ($codes.Length -gt 160) { return @{ ok = $false; motif = 'trop d''étapes ou étapes trop longues'; initiative = $null } }
    Add-Initiative "Créer le preset « $nom »" 'skill_propose' "Étapes : $codes." 'normale' 1 'presets'
}
function ConvertFrom-PresetCodes([string]$nom, [string]$raison) {
    # Relit les étapes codées dans la raison de l'initiative (« Étapes : ouvrir_app:chrome ; point_saas. »).
    $m = [regex]::Match("$raison", '^Étapes : (.+?)\.?$'); if (-not $m.Success) { return $null }
    $etapes = @()
    foreach ($c in ($m.Groups[1].Value -split '\s*;\s*')) {
        $a, $v = $c -split ':', 2; $e = [ordered]@{ action = $a.Trim(); params = @{} }
        $pp = $script:PresetsParamPrincipal[$e.action]; if ($v -and $pp) { $e.params[$pp] = $(if ($pp -eq 'niveau' -and "$v" -match '^\d+$') { [int]$v } else { $v.Trim() }) }
        $etapes += $e
    }
    [ordered]@{ nom = $nom; description = "Preset $nom ($($etapes.Count) étape$(if ($etapes.Count -gt 1) { 's' }))."; declencheurs = @($nom -replace '-', ' '); etapes = @($etapes) }
}
function Invoke-PresetsDecision($initiative) {
    # Après « approuver » / « rejeter » de Liam sur une initiative de source « presets ». Retourne @{ texte } ou $null. Jamais pour une approbation automatique.
    $i = Get-Initiative "$($initiative.id)"; if (-not $i -or "$($i.source)" -ne 'presets' -or "$($i.type)" -ne 'skill_propose') { return $null }
    if ("$($i.decide_par)" -ne 'Liam' -or "$($i.statut)" -notin 'approuvee', 'rejetee') { return $null }
    $m = [regex]::Match("$($i.titre)", '^(Créer|Valider) le preset « ([a-z][a-z0-9-]{1,29}) »$'); if (-not $m.Success) { return $null }
    $etape = $m.Groups[1].Value; $nom = $m.Groups[2].Value
    if ("$($i.statut)" -eq 'rejetee') {
        if ($etape -eq 'Valider') { $p = Get-Preset $nom; if ($p) { $p.statut = 'refuse'; Save-Preset $p } }
        return @{ texte = "Preset « $nom » refusé, monsieur. Rien n'est activé." }
    }
    $p = $(if ($etape -eq 'Valider') { Get-Preset $nom } else { ConvertFrom-PresetCodes $nom "$($i.raison)" })
    if (-not $p) { return @{ texte = "Je ne retrouve pas le preset « $nom », monsieur." } }
    $v = Test-PresetManifeste $p
    if (-not $v.ok) { return @{ texte = "Le preset « $nom » ne passe pas la validation ($((@($v.motifs) | Select-Object -First 2) -join ' ; ')) : je ne l'active pas, monsieur." } }
    $p.statut = 'actif'; $p.version = 1; $p.valide_le = (Get-Date).ToString('o'); $p.initiative = "$($i.id)"; if (-not $p.Contains('cree_le')) { $p.cree_le = (Get-Date).ToString('o') }
    Save-Preset $p
    Write-Journal -Action 'Preset validé' -Resultat "« $nom » enregistré et activé sur décision de Liam ($(@($p.etapes).Count) étape(s))"
    @{ texte = "Preset « $nom » enregistré et activé. Dites « lance le preset $nom »$(if (@($p.declencheurs).Count) { ' ou « ' + $p.declencheurs[0] + ' »' })." }
}

# ---------- Lancer ----------
function Invoke-Preset($p) {
    # @{ ok; texte; lignes; embed }. Chaque étape passe par Invoke-UneAction (permissions, confirmation de niveau 2, journal). Un refus arrête le preset.
    $nom = "$($p.nom)"
    if ("$($p.statut)" -ne 'actif') { return @{ ok = $false; texte = "Le preset « $nom » n'est pas actif ($(switch ("$($p.statut)") { 'a_valider' { 'à valider' } 'desactive' { 'désactivé' } 'refuse' { 'refusé' } default { "$($p.statut)" } })), monsieur."; lignes = @() } }
    $v = Test-PresetManifeste $p; if (-not $v.ok) { return @{ ok = $false; texte = "Le preset « $nom » ne passe plus la validation ($((@($v.motifs) | Select-Object -First 2) -join ' ; ')), monsieur."; lignes = @() } }
    $lignes = @(); $faites = 0; $i = 0; $stop = ''
    Write-Journal -Action 'Preset : lancement' -Resultat "« $nom » ($(@($p.etapes).Count) étape(s))"
    foreach ($e in @($p.etapes)) {
        $i++
        if (Get-Command Test-Stop -ErrorAction SilentlyContinue) { if (Test-Stop) { $stop = "arrêt d'urgence à l'étape $i"; break } }
        $a = ConvertTo-PresetAction $e; $lib = Format-PresetEtape $e
        $r = $(if ($script:PresetsExecuteur) { & $script:PresetsExecuteur $a "preset $nom" } else { Invoke-UneAction $a "preset $nom" })
        if ($null -eq $r) { $lignes += "✗ $lib : refusée ou non confirmée"; $stop = "arrêté à l'étape $i ($lib)"; break }
        $faites++; $lignes += $(if ($r.ok) { "✓ $lib" } else { "✗ $lib : $($r.texte)" })
    }
    $ok = (-not $stop -and @($lignes | Where-Object { $_ -like '✗*' }).Count -eq 0)
    Write-Journal -Action 'Preset : fin' -Resultat "« $nom » : $faites étape(s) sur $(@($p.etapes).Count)$(if ($stop) { ' — ' + $stop })"
    @{ ok = $ok; texte = "Preset « $nom » : $faites étape$(if ($faites -gt 1) { 's' }) sur $(@($p.etapes).Count)$(if ($stop) { ' — ' + $stop } elseif (-not $ok) { ' (certaines ont échoué)' } else { ', terminé' }), monsieur."; lignes = $lignes }
}

# ---------- Commandes ----------
function Invoke-PresetsCommande([string]$texte) {
    # @{ traite; texte; embed } ou $null. Une seule entrée pour Discord, la voix et le texte.
    $raw = "$texte".Trim(); $n = Get-PresetNorm $texte; $actif = (Get-PresetsConfig).actif; $embed = ((Get-DiscordStyle) -eq 'embed')
    $off = @{ traite = $true; texte = "Les presets sont désactivés, monsieur (réglage presets_actif = non)."; embed = $null }
    $mCree = [regex]::Match($raw, "(?i)^\W*(?:jarvis\W+)?cr[ée]e(?:r)?(?:-moi| moi)? un preset (?:nomm[ée] |appel[ée] )?([a-z][a-z0-9-]{1,29})\s+avec\s+(.+?)\W*$")
    $liste = ($n -match '^(?:(?:liste|montre|affiche)(?: moi)? )?(?:(?:les|mes) )?presets?$')
    $mLance = [regex]::Match($n, '^(?:lance|lancer|execute|applique)(?: le| mon)? preset (.+)$')
    $mDes = [regex]::Match($n, '^desactive(?:r)?(?: le)? preset (.+)$')
    $mAct = [regex]::Match($n, '^active(?:r)?(?: le)? preset (.+)$')
    if (-not ($mCree.Success -or $liste -or $mLance.Success -or $mDes.Success -or $mAct.Success)) {
        if (-not $actif) { return $null }
        foreach ($p in @(Get-Presets | Where-Object { "$($_.statut)" -eq 'actif' })) { foreach ($d in @($p.declencheurs)) { if ((Get-PresetNorm $d) -eq $n) { $r = Invoke-Preset $p; return @{ traite = $true; texte = $r.texte; embed = $(if ($embed) { New-EmbedPresetRun $p $r } else { $null }) } } } }
        return $null
    }
    if (-not $actif) { return $off }
    [void](Initialize-PresetsExemples)
    if ($liste) {
        $l = @(Get-Presets); Write-Journal -Ordre $texte -Action 'Presets : liste' -Resultat "$($l.Count) preset(s)"
        return @{ traite = $true; texte = $(if ($l.Count) { 'Presets : ' + (($l | ForEach-Object { "$($_.nom) ($($_.statut))" }) -join ', ') + '.' } else { 'Aucun preset, monsieur.' }); embed = $(if ($embed) { New-EmbedPresets $l } else { $null }) }
    }
    if ($mCree.Success) {
        $r = New-PresetProposition $mCree.Groups[1].Value.ToLower() $mCree.Groups[2].Value
        if (-not $r.ok) { return @{ traite = $true; texte = "Je ne peux pas proposer ce preset : $($r.motif), monsieur."; embed = $null } }
        Write-Journal -Ordre $texte -Action 'Presets : proposition' -Resultat "initiative n° $($r.initiative.id), rien n'est enregistré avant votre accord"
        return @{ traite = $true; texte = "Je vous propose le preset « $($mCree.Groups[1].Value.ToLower()) » ($($r.initiative.raison)) Rien n'est enregistré : approuver $($r.initiative.id) / rejeter $($r.initiative.id)."; embed = $(if ($embed) { New-EmbedInitiative $r.initiative } else { $null }) }
    }
    $cible = $(if ($mLance.Success) { $mLance.Groups[1].Value } elseif ($mDes.Success) { $mDes.Groups[1].Value } else { $mAct.Groups[1].Value })
    $p = Get-Preset $cible
    if (-not $p) { return @{ traite = $true; texte = "Je ne connais pas de preset « $cible », monsieur."; embed = $null } }
    if ($mLance.Success) { $r = Invoke-Preset $p; return @{ traite = $true; texte = $r.texte; embed = $(if ($embed) { New-EmbedPresetRun $p $r } else { $null }) } }
    if ($mDes.Success) {
        if ("$($p.statut)" -ne 'actif') { return @{ traite = $true; texte = "Le preset « $($p.nom) » n'est pas actif, monsieur."; embed = $null } }
        $p.statut = 'desactive'; Save-Preset $p; Write-Journal -Ordre $texte -Action 'Preset désactivé' -Resultat $p.nom
        return @{ traite = $true; texte = "Preset « $($p.nom) » désactivé, monsieur."; embed = $null }
    }
    if ("$($p.statut)" -ne 'desactive') { return @{ traite = $true; texte = "Le preset « $($p.nom) » ne peut pas être réactivé ainsi ($(if ("$($p.statut)" -eq 'actif') { 'déjà actif' } else { 'il doit d''abord être validé par vous' })), monsieur."; embed = $null } }
    $v = Test-PresetManifeste $p; if (-not $v.ok) { return @{ traite = $true; texte = "Le preset « $($p.nom) » ne passe plus la validation, monsieur."; embed = $null } }
    $p.statut = 'actif'; Save-Preset $p; Write-Journal -Ordre $texte -Action 'Preset réactivé' -Resultat $p.nom
    @{ traite = $true; texte = "Preset « $($p.nom) » réactivé, monsieur."; embed = $null }
}
