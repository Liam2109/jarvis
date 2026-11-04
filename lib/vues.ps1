# VUES : extensions plein écran de l'interface (visage\index.html). DÉSACTIVÉES par défaut (config.json « vues_actif » = "non").
# Une vue = un dossier visage\vues\<id>\ avec VUE.md (front-matter YAML : id, nom, version, description, declencheurs, commandes) et vue.js (module ES : export default { show(params), hide(), command(cmd, params) }).
# Règles d'une vue : JS vanilla, idempotente, racine `position: fixed` plein écran, hide() nettoie TOUT (DOM, minuteurs, écouteurs, animations), aucun appel réseau, aucun eval, aucune lecture de memoire\ ni de la config.
# Le manifeste ET une analyse statique du JS sont vérifiés avant de servir le moindre fichier. Seuls les fichiers de la vue et deux fichiers three.js LOCAUX (visage\lib\three) sont servis, sur 127.0.0.1, avec les contrôles d'hôte et d'origine de lib\visage.ps1.
# CANAL : celui qui existe déjà. La page sonde /etat (127.0.0.1 + jeton) toutes les 200 ms ; Jarvis y ajoute vue_seq, vue_active et vue_events (show_view, hide_view, view_command). La page répond par POST /vue (ouverte, fermée, erreur).
# Commandes (texte / Discord / voix) : vues, montre la vue <nom>, montre <déclencheur> (« montre la tour eiffel »), ferme la vue. « capacités » : skills, presets et vues en un seul embed.

$script:VuesEvt = New-Object System.Collections.Generic.List[hashtable]
$script:VuesSeq = 0; $script:VueActive = $null
$script:VueImportsSurs = @('three', 'three/addons/controls/OrbitControls.js')
$script:VueFichiersLib = @('build/three.module.min.js', 'examples/jsm/controls/OrbitControls.js')
$script:VueReglesJs = @(      # [motif lisible, regex sur le JS]
    @('eval ou Function dynamique', '\beval\s*\(|new\s+Function\s*\(|(?<![\w.])Function\s*\('),
    @('minuteur à code texte', '(setTimeout|setInterval)\s*\(\s*[''"`]'),
    @('appel réseau', '\bfetch\s*\(|XMLHttpRequest|WebSocket|EventSource|sendBeacon|importScripts|\bWorker\s*\(|SharedWorker|navigator\.'),
    @('adresse externe', 'https?://|wss?://|ftp://'),
    @('import dynamique', '\bimport\s*\('),
    @('stockage, cookie ou fenêtre parente', 'document\.cookie|localStorage|sessionStorage|indexedDB|window\.(parent|top|opener)|document\.domain|postMessage|\blocation\s*=|location\.(href|assign|replace)'),
    @('injection de script ou document.write', '<script|document\.write'),
    @('lecture de memoire\ ou de la config de Jarvis', '(?i)memoire|\bconfig\b|\.env\b|/donnees|/etat|/ordre|/marche-donnees|Jarvis-Token'))

function Get-VuesConfig {
    $c = @{ actif = $false }
    if ($Config.PSObject.Properties['vues_actif'] -and "$($Config.vues_actif)".Trim().ToLower() -in @('oui', 'true', '1', 'on', 'yes')) { $c.actif = $true }
    $c
}
function Get-VueNorm([string]$s) { $n = ((("$s").ToLowerInvariant().Normalize([Text.NormalizationForm]::FormD) -replace '\p{Mn}', '') -replace "[’']", ' ' -replace '[^a-z0-9]+', ' ').Trim(); ($n -replace '^(?:jarvis )+', '') }
function Get-VuesDossier { Join-Path $script:JarvisRoot 'visage\vues' }

# ---------- Manifeste VUE.md ----------
function ConvertFrom-VueFrontMatter([string]$texte) {
    # Sous-ensemble de YAML : « cle: valeur » et listes « - élément ». @{ ok; meta; erreur }
    $m = [regex]::Match("$texte", '(?s)^﻿?---\r?\n(.*?)\r?\n---')
    if (-not $m.Success) { return @{ ok = $false; meta = $null; erreur = 'front-matter YAML absent (---)' } }
    $meta = [ordered]@{}; $cle = $null
    $sans = { param($v) $v = "$v".Trim(); if ($v.Length -ge 2 -and (($v[0] -eq '"' -and $v[-1] -eq '"') -or ($v[0] -eq "'" -and $v[-1] -eq "'"))) { $v = $v.Substring(1, $v.Length - 2) }; $v }
    foreach ($l in ($m.Groups[1].Value -split '\r?\n')) {
        if (-not $l.Trim() -or $l.Trim().StartsWith('#')) { continue }
        if ($l -match '^([A-Za-z_][\w-]*):\s*(.*)$') { $cle = $Matches[1]; $v = $Matches[2]; if ("$v".Trim() -eq '') { $meta[$cle] = @() } else { $meta[$cle] = & $sans $v } }
        elseif ($l -match '^\s+-\s+(.*)$' -and $cle -and $meta[$cle] -is [array]) { $meta[$cle] = @($meta[$cle]) + @(& $sans $Matches[1]) }
        else { return @{ ok = $false; meta = $null; erreur = "ligne YAML non comprise : $($l.Trim())" } }
    }
    @{ ok = $true; meta = $meta; erreur = '' }
}
function Test-VueScripts([string]$dossier) {
    # Analyse statique de TOUS les .js de la vue. Retourne la liste des motifs de refus.
    $mo = @(); $fichiers = @(Get-ChildItem $dossier -Filter *.js -File -Recurse -ErrorAction SilentlyContinue)
    $baseVue = $(if (Get-Command Get-CheminLong -ErrorAction SilentlyContinue) { Get-CheminLong $dossier } else { $dossier }).TrimEnd('\')      # forme longue : un %TEMP% en nom court 8.3 (SERVEU~1) ne doit pas fausser les noms relatifs
    if (-not (Test-Path (Join-Path $dossier 'vue.js'))) { return @('vue.js absent') }
    foreach ($f in $fichiers) {
        $rel = $f.FullName.Substring($baseVue.Length + 1).Replace('\', '/')
        if ($rel -cnotmatch '^(vue\.js|[a-z0-9-]+(/[a-z0-9-]+)*\.js)$') { $mo += "nom de fichier non permis : $rel"; continue }
        $js = Get-Content $f.FullName -Raw -Encoding UTF8
        foreach ($r in $script:VueReglesJs) { if ($js -match $r[1]) { $mo += "$rel : $($r[0])" } }
        foreach ($i in [regex]::Matches($js, '(?m)^\s*(?:import|export)\s+(?:[^''";\r\n]*?\s+from\s+)?[''"]([^''"]+)[''"]')) {
            $s = $i.Groups[1].Value
            $ok = ($s -in $script:VueImportsSurs)
            if (-not $ok -and $s -match '^\./[a-z0-9-]+(/[a-z0-9-]+)*\.js$') { $ok = Test-Path (Join-Path (Split-Path $f.FullName) ($s -replace '^\./', '' -replace '/', '\')) }
            if (-not $ok) { $mo += "$rel : import non permis ($s)" }
        }
        if ($js -match '\bsetInterval\s*\(' -and $js -notmatch '\bclearInterval\s*\(') { $mo += "$rel : setInterval sans clearInterval" }
        if ($js -match '\bsetTimeout\s*\(' -and $js -notmatch '\bclearTimeout\s*\(') { $mo += "$rel : setTimeout sans clearTimeout" }
        if ($js -match '\brequestAnimationFrame\s*\(' -and $js -notmatch '\bcancelAnimationFrame\s*\(') { $mo += "$rel : requestAnimationFrame sans cancelAnimationFrame" }
        if ([regex]::Matches($js, '\.addEventListener\s*\(').Count -gt [regex]::Matches($js, '\.removeEventListener\s*\(').Count) { $mo += "$rel : plus d'addEventListener que de removeEventListener (hide() doit tout retirer)" }
    }
    $main = Get-Content (Join-Path $dossier 'vue.js') -Raw -Encoding UTF8
    if ($main -notmatch 'export\s+default') { $mo += 'vue.js : export default absent' }
    foreach ($k in 'show', 'hide', 'command') { if ($main -notmatch "\b$k\s*\(") { $mo += "vue.js : méthode $k() absente" } }
    if ($main -notmatch '(?i)position\s*:\s*fixed|position\s*=\s*[''"]fixed') { $mo += 'vue.js : racine en position fixed absente' }
    if ($main -notmatch '\.remove\s*\(|removeChild\s*\(') { $mo += 'vue.js : hide() ne retire rien du DOM' }
    @($mo)
}
function Test-VueManifeste([string]$id) {
    # @{ ok; motifs; vue } — le dossier, VUE.md, les déclencheurs et le JS.
    $d = Join-Path (Get-VuesDossier) $id; $mo = @()
    if ($id -cnotmatch '^[a-z][a-z0-9-]{1,29}$') { return @{ ok = $false; motifs = @('identifiant invalide'); vue = $null } }
    $f = Join-Path $d 'VUE.md'; if (-not (Test-Path $f)) { return @{ ok = $false; motifs = @('VUE.md absent'); vue = $null } }
    $fm = ConvertFrom-VueFrontMatter (Get-Content $f -Raw -Encoding UTF8)
    if (-not $fm.ok) { return @{ ok = $false; motifs = @($fm.erreur); vue = $null } }
    $m = $fm.meta
    if ("$($m.id)" -ne $id) { $mo += "id (« $($m.id) ») différent du dossier" }
    if (-not "$($m.nom)".Trim()) { $mo += 'nom absent' }
    if ("$($m.version)" -notmatch '^\d+\.\d+\.\d+$') { $mo += 'version invalide (x.y.z)' }
    if (-not "$($m.description)".Trim() -or "$($m.description)".Length -gt 200) { $mo += 'description absente ou trop longue' }
    if (@($m.commandes | Where-Object { $_ }).Count -lt 1) { $mo += 'commandes absentes' }
    $decl = @()
    foreach ($e in @($m.declencheurs | Where-Object { $_ })) {
        $p = "$e" -split '\s*=>\s*', 2; $phrase = (Get-VueNorm $p[0]) -replace '^(?:la|le|les|l|un|une) ', ''
        $par = @{}
        if ($p.Count -gt 1 -and $p[1].Trim()) { foreach ($kv in ($p[1] -split '\s*,\s*')) { if ($kv -match '^([a-z_]{1,20})=([a-z0-9_-]{1,30})$') { $par[$Matches[1]] = $Matches[2] } else { $mo += "déclencheur : paramètre invalide ($kv)" } } }
        if (-not $phrase -or $phrase.Length -gt 60) { $mo += "déclencheur invalide : $e" } else { $decl += @{ phrase = $phrase; params = $par } }
    }
    if (-not $decl.Count) { $mo += 'au moins un déclencheur' }
    $mo += @(Test-VueScripts $d)
    @{ ok = ($mo.Count -eq 0); motifs = @($mo); vue = @{ id = $id; nom = "$($m.nom)"; version = "$($m.version)"; description = "$($m.description)"; commandes = @($m.commandes); declencheurs = @($decl); dossier = $d } }
}
function Get-Vues {
    # Toutes les vues du dossier, valides ou non : @{ id; ok; motifs; vue }
    $r = @(); $d = Get-VuesDossier; if (-not (Test-Path $d)) { return @() }
    foreach ($x in (Get-ChildItem $d -Directory | Where-Object { $_.Name -notlike '_*' } | Sort-Object Name)) { $t = Test-VueManifeste $x.Name; $r += [pscustomobject]@{ id = $x.Name; ok = $t.ok; motifs = $t.motifs; vue = $t.vue } }
    @($r)
}
function Get-VueParNom([string]$nom) {
    $n = Get-VueNorm $nom; if (-not $n) { return $null }
    @(Get-Vues | Where-Object { $_.ok -and ((Get-VueNorm $_.id) -eq $n -or (Get-VueNorm $_.vue.nom) -eq $n) }) | Select-Object -First 1
}
function Resolve-VueDeclencheur([string]$objet) {
    # « la tour eiffel » -> @{ id; nom; params } si une vue valide a ce déclencheur.
    $n = (Get-VueNorm $objet) -replace '^(?:la|le|les|l|un|une) ', ''; if (-not $n) { return $null }
    foreach ($v in @(Get-Vues | Where-Object { $_.ok })) { foreach ($d in $v.vue.declencheurs) { if ($d.phrase -eq $n) { return @{ id = $v.id; nom = $v.vue.nom; params = $d.params } } } }
    $null
}

# ---------- Événements vers la page (canal /etat existant) ----------
function Send-VueEvenement([string]$type, [string]$id = '', $params = @{}, [string]$cmd = '') {
    $script:VuesSeq++
    $script:VuesEvt.Add(@{ seq = $script:VuesSeq; type = $type; id = $id; params = $params; cmd = $cmd })
    while ($script:VuesEvt.Count -gt 10) { $script:VuesEvt.RemoveAt(0) }
    if ($type -eq 'show_view') { $script:VueActive = @{ id = $id; params = $params } } elseif ($type -eq 'hide_view') { $script:VueActive = $null }
}
function Get-VuesEtatHttp { @{ vue_seq = $script:VuesSeq; vue_active = $script:VueActive; vue_events = @($script:VuesEvt) } }
function Receive-VueEtat($c) {
    if (-not $c -or "$($c.id)" -notmatch '^[a-z0-9-]{2,30}$') { return }
    $e = "$($c.etat)"
    if ($e -in 'fermee', 'erreur' -and $script:VueActive -and $script:VueActive.id -eq "$($c.id)") { $script:VueActive = $null }
    if ($e -eq 'erreur') { Write-Journal -Action 'Vue : erreur' -Resultat "$($c.id) : $((Hide-Secrets "$($c.message)"))" } else { Write-Journal -Action 'Vue' -Resultat "$($c.id) : $e (signalé par la page)" }
}
function Get-FichierVueHttp([string]$chemin) {
    # @{ corps; type } ou $null. Liste blanche stricte : fichiers .js d'une vue VALIDE, ou deux fichiers three.js locaux. Vues désactivées : rien.
    if (-not (Get-VuesConfig).actif) { return $null }
    $rel = $null; $racine = $null
    if ($chemin -cmatch '^/vues/([a-z][a-z0-9-]{1,29})/((?:vue|[a-z0-9-]+(?:/[a-z0-9-]+)*)\.js)$') {
        if (-not (Test-VueManifeste $Matches[1]).ok) { return $null }
        $racine = Join-Path (Get-VuesDossier) $Matches[1]; $rel = $Matches[2]
    } elseif ($chemin -cmatch '^/lib/three/(.+)$' -and $Matches[1] -cin $script:VueFichiersLib) { $racine = Join-Path $script:JarvisRoot 'visage\lib\three'; $rel = $Matches[1] }
    if (-not $rel) { return $null }
    $f = Join-Path $racine ($rel -replace '/', '\'); if (-not (Test-Path $f -PathType Leaf)) { return $null }
    @{ corps = [IO.File]::ReadAllText($f, [Text.Encoding]::UTF8); type = 'text/javascript; charset=utf-8' }
}

# ---------- Ouvrir / fermer ----------
function Show-Vue($v, $params = @{}) {
    if (-not (Get-VuesConfig).actif) { return @{ ok = $false; texte = "Les vues sont désactivées, monsieur (réglage vues_actif = non)." } }
    if (-not $v) { return @{ ok = $false; texte = "Je ne connais pas cette vue, monsieur." } }
    Send-VueEvenement 'show_view' $v.id $params
    Write-Journal -Action 'Vue : afficher' -Resultat "$($v.id) (événement show_view n° $script:VuesSeq)"
    @{ ok = $true; texte = "Voici la vue « $($v.vue.nom) », monsieur. Échap la ferme." }
}
function Close-Vue {
    if (-not $script:VueActive) { return @{ ok = $true; texte = "Aucune vue n'est ouverte, monsieur." } }
    $id = $script:VueActive.id; Send-VueEvenement 'hide_view' $id
    Write-Journal -Action 'Vue : fermer' -Resultat "$id (événement hide_view n° $script:VuesSeq)"
    @{ ok = $true; texte = "Vue fermée, monsieur." }
}
function Send-VueCommande([string]$cmd, $params = @{}) {
    if (-not $script:VueActive) { return @{ ok = $false; texte = "Aucune vue n'est ouverte, monsieur." } }
    Send-VueEvenement 'view_command' $script:VueActive.id $params $cmd
    @{ ok = $true; texte = "Commande « $cmd » envoyée à la vue." }
}
function Show-VueParNom([string]$nom) {
    $v = Get-VueParNom $nom; $params = @{}
    if (-not $v) { $d = Resolve-VueDeclencheur $nom; if ($d) { $v = Get-VueParNom $d.id; $params = $d.params } }
    Show-Vue $v $params
}
if (Get-Command Add-Action -ErrorAction SilentlyContinue) {
    Add-Action 'vue_montrer' 1 'afficher une vue plein écran' 'vue_montrer(nom) : affiche une vue plein écran de l''interface (horloge, tour Eiffel en 3D...) si les vues sont activées' {
        param($a)
        $r = Show-VueParNom "$($a.nom)"; Rep $r.ok $r.texte
    } { param($a) "afficher la vue $($a.nom)" }
    Add-Action 'vue_fermer' 1 'fermer la vue en cours' 'vue_fermer() : ferme la vue plein écran en cours' {
        param($a)
        $r = Close-Vue; Rep $r.ok $r.texte
    } { param($a) 'fermer la vue en cours' }
}

# ---------- Commandes (une seule entrée pour Discord, la voix et le texte) ----------
function Invoke-VuesCommande([string]$texte) {
    # @{ traite; texte; embed } ; $null si ce n'est pas une commande de vue.
    $n = Get-VueNorm $texte; $actif = (Get-VuesConfig).actif
    if ($n -match '^(?:(?:liste|montre|affiche)(?: moi)? )?(?:(?:les|mes) )?vues$') {
        if (-not $actif) { return @{ traite = $true; texte = "Les vues sont désactivées, monsieur (réglage vues_actif = non)."; embed = $null } }
        $l = @(Get-Vues); Write-Journal -Ordre $texte -Action 'Vues : liste' -Resultat "$($l.Count) vue(s)"
        return @{ traite = $true; texte = $(if ($l.Count) { 'Vues : ' + (($l | ForEach-Object { "$($_.id)$(if (-not $_.ok) { ' (invalide)' })" }) -join ', ') + '.' } else { "Aucune vue installée, monsieur." }); embed = $(if ((Get-DiscordStyle) -eq 'embed') { New-EmbedVues $l } else { $null }) }
    }
    $m = [regex]::Match($n, '^(?:montre|affiche|ouvre|lance)(?: moi)? (?:la |le )?vue (.+)$')
    if ($m.Success) {
        if (-not $actif) { return @{ traite = $true; texte = "Les vues sont désactivées, monsieur (réglage vues_actif = non)."; embed = $null } }
        $r = Show-VueParNom $m.Groups[1].Value; return @{ traite = $true; texte = $r.texte; embed = $null }
    }
    if (-not $actif) { return $null }
    if ($n -match '^(?:ferme|fermer|quitte|cache|masque)(?: moi)? (?:la |les |cette )?vues?(?: en cours| actuelle)?$') { $r = Close-Vue; return @{ traite = $true; texte = $r.texte; embed = $null } }
    $m = [regex]::Match($n, '^(?:montre|affiche|ouvre)(?: moi)? (.+)$')
    if ($m.Success -and (Resolve-VueDeclencheur $m.Groups[1].Value)) { $r = Show-VueParNom $m.Groups[1].Value; return @{ traite = $true; texte = $r.texte; embed = $null } }
    $null
}

# ---------- Registre : skills, presets et vues en un seul embed ----------
function Get-CapacitesDonnees {
    $sk = @(); if (Get-Command Get-Skills -ErrorAction SilentlyContinue) { $sk = @(Get-Skills | ForEach-Object { @{ nom = $_.nom; etat = $_.etat; description = $_.description } }) }
    $pr = @(); if (Get-Command Get-Presets -ErrorAction SilentlyContinue) { $pr = @(Get-Presets | ForEach-Object { @{ nom = $_.nom; etat = $(switch ("$($_.statut)") { 'actif' { 'actif' } 'a_valider' { 'à valider' } 'desactive' { 'désactivé' } 'refuse' { 'refusé' } default { "$($_.statut)" } }); description = $_.description } }) }
    $vu = @(Get-Vues | ForEach-Object { @{ nom = $_.id; etat = $(if ($_.ok) { 'disponible' } else { 'invalide' }); description = $(if ($_.ok) { $_.vue.description } else { 'manifeste invalide : ' + (($_.motifs | Select-Object -First 1) -join '') }) } })
    @{ skills = $sk; presets = $pr; vues = $vu; presets_actif = [bool]((Get-Command Get-PresetsConfig -ErrorAction SilentlyContinue) -and (Get-PresetsConfig).actif); vues_actif = [bool](Get-VuesConfig).actif }
}
function Invoke-CapacitesCommande([string]$texte) {
    $n = Get-VueNorm $texte
    if ($n -notmatch '^(?:(?:liste|montre|affiche|donne)(?: moi)? )?(?:(?:les|mes|toutes les|tes) )?capacites(?: installees)?$') { return $null }
    if (-not ((Get-VuesConfig).actif -or ((Get-Command Get-PresetsConfig -ErrorAction SilentlyContinue) -and (Get-PresetsConfig).actif))) { return $null }      # ni presets ni vues : la commande « capacités » d'origine reste seule
    $d = Get-CapacitesDonnees; Write-Journal -Ordre $texte -Action 'Capacités' -Resultat "$($d.skills.Count) skill(s), $($d.presets.Count) preset(s), $($d.vues.Count) vue(s)"
    @{ traite = $true; texte = "Capacités : $($d.skills.Count) skill(s), $($d.presets.Count) preset(s), $($d.vues.Count) vue(s)."; embed = $(if ((Get-DiscordStyle) -eq 'embed') { New-EmbedCapacites $d } else { $null }) }
}
function Invoke-ExtensionsOrdre([string]$texte) {
    # Presets, vues et capacités : @{ texte; embed } ou $null. Appelée par Discord et par la voix ; sans effet tant que presets_actif et vues_actif sont « non ».
    $r = Invoke-CapacitesCommande $texte; if ($r) { return $r }
    if (Get-Command Invoke-PresetsCommande -ErrorAction SilentlyContinue) { $r = Invoke-PresetsCommande $texte; if ($r -and $r.traite) { return $r } }
    $r = Invoke-VuesCommande $texte; if ($r -and $r.traite) { return $r }
    $null
}
