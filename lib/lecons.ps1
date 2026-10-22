# Un agent qui GRANDIT : leçons (façons de faire apprises) et style de parole (comment Liam parle). Tout par règles et mots-clés : AUCUN appel à Claude ni à Ollama, donc 0 token.
# DÉSACTIVÉ par défaut (config.json « lecons_actif » = "non"). Fichiers créés au premier usage : memoire\lecons.json et memoire\style-parole.json.
# LEÇON = id, contexte, marche, rate, regle (la façon de faire), confiance (0 à 1), confirmations, etiquettes, dates. Une leçon identique est RENFORCÉE (confirmations + 1), pas dupliquée.
# Écrite après une action terminée ou échouée (Invoke-UneAction) et après une correction de Liam. Relue AVANT une tâche similaire (3 leçons fiables au plus), appliquée ou citée.
# REVUE DE NUIT (entre 3 h et 5 h, une fois par jour, tant que Jarvis tourne) : fusionne les doublons, baisse la confiance des leçons contredites, PROPOSE de promouvoir une leçon fiable
#   (confiance >= 0.8 et >= 3 confirmations) en règle permanente par une initiative « maintenance » (lib\initiatives.ps1). Rien n'est promu sans « approuver » de Liam.
# STYLE DE PAROLE : mots mal transcrits et leur correction probable (lit memoire\vocabulaire-voix.txt et grammaire-voix.json, ne les écrase JAMAIS), tournures habituelles, longueur de réponse préférée, sujets récurrents.
# Phrase ambiguë ou mal transcrite : Jarvis PROPOSE la lecture probable (« Tu veux dire Ollama ? »). Une correction de Liam crée ou renforce une leçon. Voie texte / Discord (la voix n'est pas touchée).
# SÉCURITÉ : jamais de secret (clé, jeton, mot de passe), jamais de donnée sensible (santé, argent, identifiants), jamais une leçon qui touche interdits.json, une permission ou un plafond de tokens.

$script:LeconsMax = 200
$script:LeconsNuitProchain = [datetime]::MinValue
$script:LeconsAppliquees = @(); $script:LeconsEnAttente = $null; $script:LeconsDernierOrdre = ''
$script:LeconsTermesCles = @('Ollama', 'Vosk', 'Jarvis', 'Supabase', 'Stripe', 'Vercel', 'Discord', 'Gmail', 'GitHub', 'Bitwarden', 'candidatures', 'initiatives', 'Shopify', 'TikTok')
$script:LeconsStop = @('dans', 'pour', 'avec', 'sans', 'cette', 'cela', 'comme', 'mais', 'donc', 'alors', 'vous', 'nous', 'plus', 'tres', 'bien', 'quand', 'avant', 'apres', 'chez', 'tout', 'tous', 'faire', 'faut', 'etre', 'avoir', 'fais', 'est', 'une', 'les', 'des', 'que', 'qui', 'pas', 'sur', 'par', 'aux', 'son', 'ses', 'mon', 'mes', 'ton', 'tes', 'jarvis', 'veux', 'peux', 'dois', 'cest', 'quel', 'quelle')
$script:LeconsTournures = @(      # [motif sur le texte normalisé, expression, sens]
    @('\bnote le\b', 'note-le', 'ajouter à la to-do ou aux notes ce dont on vient de parler'),
    @('\bfais le\b', 'fais-le', 'exécuter ce qui vient d''être proposé'),
    @('\btu captes\b', 'tu captes ?', 'est-ce que tu as compris ?'),
    @('\bvas y\b', 'vas-y', 'oui, lance'),
    @('\bbalance\b', 'balance', 'envoie ou affiche tout de suite'),
    @('\bc est bon\b', 'c''est bon', 'c''est validé'),
    @('\blaisse tomber\b', 'laisse tomber', 'annule, on n''en parle plus'),
    @('\bnickel\b', 'nickel', 'parfait, c''est bon'))
$script:LeconsSujets = @('saas', 'candidature', 'candidatures', 'train', 'conducteur', 'veille', 'marche', 'todo', 'discord', 'musique', 'mail', 'briefing', 'site', 'video', 'tiktok', 'initiative', 'initiatives', 'agenda', 'rappel')

function Get-LeconsConfig {
    $c = @{ actif = $false }
    if ($Config.PSObject.Properties['lecons_actif'] -and "$($Config.lecons_actif)".Trim().ToLower() -in @('oui', 'true', '1', 'on', 'yes')) { $c.actif = $true }
    $c
}

# ---------- Outils ----------
function Get-LeconNorm([string]$s) { ((("$s").ToLowerInvariant().Normalize([Text.NormalizationForm]::FormD) -replace '\p{Mn}', '') -replace "[’']", ' ' -replace '[^a-z0-9]+', ' ').Trim() }
function Get-LeconMots([string]$s, [int]$min = 4) { @((Get-LeconNorm $s) -split ' ' | Where-Object { $_.Length -ge $min -and $_ -notin $script:LeconsStop } | Select-Object -Unique) }
function ConvertTo-LeconTexte($x, [int]$max) {
    $t = ((Hide-Secrets "$x") -replace '[\u0000-\u001f\u007f]', ' ' -replace '\s+', ' ').Trim()
    if ($t.Length -gt $max) { $t.Substring(0, $max - 1) + '…' } else { $t }
}
function Get-Levenshtein([string]$a, [string]$b) {
    $n = $a.Length; $m = $b.Length; if (-not $n) { return $m }; if (-not $m) { return $n }
    $d = New-Object 'int[,]' ($n + 1), ($m + 1)
    for ($i = 0; $i -le $n; $i++) { $d[$i, 0] = $i }; for ($j = 0; $j -le $m; $j++) { $d[0, $j] = $j }
    for ($i = 1; $i -le $n; $i++) { for ($j = 1; $j -le $m; $j++) {
        $c = $(if ($a[$i - 1] -eq $b[$j - 1]) { 0 } else { 1 }); $pi = $i - 1; $pj = $j - 1
        $sup = $d[$pi, $j] + 1; $ins = $d[$i, $pj] + 1; $sub = $d[$pi, $pj] + $c
        $d[$i, $j] = [math]::Min([math]::Min($sup, $ins), $sub)
    } }
    $d[$n, $m]
}
function Get-LeconSimilarite([string]$a, [string]$b) {
    $x = @(Get-LeconMots $a 3); $y = @(Get-LeconMots $b 3); if (-not $x.Count -or -not $y.Count) { return 0.0 }
    $inter = @($x | Where-Object { $_ -in $y }).Count; $union = @($x + $y | Select-Object -Unique).Count
    [double]$inter / $union
}
function Get-DatePct([double]$c) { [int][math]::Round($c * 100) }

function Test-LeconSensible([string]$texte) {
    [bool]($texte -match '(?i)\b(sant[ée]|maladie|m[ée]dicaments?|m[ée]decin|diagnostic|th[ée]rapie|salaire|revenus?|dettes?|solde|compte bancaire|iban|carte (bancaire|bleue)|cvv|mots? de passe|mdp|password|identifiants?|login|code pin|s[ée]curit[ée] sociale|num[ée]ro de s[ée]cu|tokens?|jetons?|cl[ée]s? api)\b')
}
function Test-LeconInterdite([string]$texte) {
    # '' si permise, sinon la raison du refus. Secrets, données sensibles, interdits, permissions, plafond de tokens.
    if (-not "$texte".Trim()) { return '' }
    if ((Hide-Secrets $texte) -ne $texte -or $texte -match '(?i)\b(sk|rk|pk|ghp|gho|xox[bp]|AKIA)[-_][A-Za-z0-9_-]{8,}|eyJ[A-Za-z0-9_-]{10,}|[A-Za-z0-9+/_-]{32,}') { return 'secret : jamais enregistré' }
    if (Test-LeconSensible $texte) { return 'donnée sensible (santé, argent, identifiants) : jamais apprise' }
    if (Get-Command Test-InitiativeInterdite -ErrorAction SilentlyContinue) { $r = Test-InitiativeInterdite $texte; if ($r) { return $r } }
    elseif (Get-Variable MotifsInterdits -Scope Script -ErrorAction SilentlyContinue) { foreach ($m in $script:MotifsInterdits) { if ($texte -match $m.re) { return "interdit : $($m.raison)" } } }
    if ($texte -match '(?i)plafond|\btokens?\b|quota' -and $texte -match '(?i)augment\w*|lever|lev[ée]e|supprim\w*|ignor\w*|contourn\w*|d[ée]sactiv\w*|retir\w*|enlev\w*|baiss\w*|chang\w*|modifi\w*|d[ée]pass\w*|sans limite') { return 'interdit : plafond de tokens' }
    ''
}

# ---------- Base des leçons ----------
function Get-LeconsEtat {
    $o = Read-JsonMemoire 'lecons.json'; $e = @{ prochain_id = 1; derniere_nuit = ''; lecons = @() }
    if ($o) {
        if ($o.PSObject.Properties['prochain_id'] -and "$($o.prochain_id)" -match '^\d+$') { $e.prochain_id = [int]$o.prochain_id }
        if ($o.PSObject.Properties['derniere_nuit']) { $e.derniere_nuit = "$($o.derniere_nuit)" }
        if ($o.PSObject.Properties['lecons']) { $e.lecons = @($o.lecons | Where-Object { $_ } | ForEach-Object { $h = [ordered]@{}; foreach ($p in $_.PSObject.Properties) { $h[$p.Name] = $(if ($p.Name -eq 'etiquettes') { @($p.Value | ForEach-Object { "$_" }) } else { $p.Value }) }; $h }) }
    }
    $e
}
function Save-LeconsEtat($e) { Save-JsonMemoire 'lecons.json' ([ordered]@{ prochain_id = $e.prochain_id; derniere_nuit = $e.derniere_nuit; lecons = @($e.lecons) }) }
function Get-Lecons { @((Get-LeconsEtat).lecons) }
function Get-Lecon([string]$id) { $id = "$id".Trim().TrimStart('#'); @(Get-Lecons | Where-Object { "$($_.id)" -eq $id }) | Select-Object -First 1 }
function Step-LeconConfiance([double]$c, [double]$pas = 0.3) { [math]::Round([math]::Min(1.0, $c + (1.0 - $c) * $pas), 3) }

function Add-Lecon([string]$contexte, [string]$marche, [string]$rate, [string]$regle, [string[]]$etiquettes = @(), [double]$confiance = 0.5, [datetime]$now = (Get-Date)) {
    # @{ ok; motif; lecon; renforcee }. Refuse secrets, données sensibles et tout ce qui toucherait interdits, permissions ou plafond de tokens.
    $brut = "$contexte $marche $rate $regle $($etiquettes -join ' ')"
    $refus = Test-LeconInterdite $brut
    if ($refus) { Write-Journal -Action 'Leçon refusée' -Resultat $refus; return @{ ok = $false; motif = $refus; lecon = $null; renforcee = $false } }
    $regle = ConvertTo-LeconTexte $regle 220
    if (-not $regle) { return @{ ok = $false; motif = 'règle vide'; lecon = $null; renforcee = $false } }
    $tags = @($etiquettes | ForEach-Object { Get-LeconMots $_ 3 } | Select-Object -Unique | Select-Object -First 8)
    $e = Get-LeconsEtat
    foreach ($l in $e.lecons) {
        if ((Get-LeconSimilarite "$($l.regle)" $regle) -ge 0.8 -and (@($tags | Where-Object { $_ -in @($l.etiquettes) }).Count -ge 1 -or -not $tags.Count)) {
            $l.confirmations = [int]$l.confirmations + 1; $l.confiance = Step-LeconConfiance ([double]$l.confiance); $l.maj_le = $now.ToString('o')
            $l.etiquettes = @(@($l.etiquettes) + $tags | Select-Object -Unique | Select-Object -First 8)
            Save-LeconsEtat $e
            Write-Journal -Action 'Leçon renforcée' -Resultat "n° $($l.id), $($l.confirmations) confirmations, confiance $(Get-DatePct $l.confiance) %"
            return @{ ok = $true; motif = ''; lecon = $l; renforcee = $true }
        }
    }
    $l = [ordered]@{ id = "$($e.prochain_id)"; contexte = (ConvertTo-LeconTexte $contexte 160); marche = (ConvertTo-LeconTexte $marche 160); rate = (ConvertTo-LeconTexte $rate 160); regle = $regle
        confiance = [math]::Round([math]::Max(0.0, [math]::Min(1.0, $confiance)), 3); confirmations = 1; etiquettes = @($tags); cree_le = $now.ToString('o'); maj_le = $now.ToString('o')
        statut = 'active'; contredit = 0; promotion = ''; promotion_refusee = $false }
    $e.prochain_id = $e.prochain_id + 1; $e.lecons = @($e.lecons) + @($l)
    if ($e.lecons.Count -gt $script:LeconsMax) {      # plafond de taille : on retire les moins fiables, jamais une règle permanente
        $sup = @($e.lecons | Where-Object { $_.statut -ne 'permanente' } | Sort-Object { [double]$_.confiance }, { [int]$_.confirmations } | Select-Object -First ($e.lecons.Count - $script:LeconsMax))
        $e.lecons = @($e.lecons | Where-Object { $_ -notin $sup })
    }
    Save-LeconsEtat $e
    Write-Journal -Action 'Leçon apprise' -Resultat "n° $($l.id) : $($l.regle)"
    @{ ok = $true; motif = ''; lecon = $l; renforcee = $false }
}
function Remove-Lecon([string]$id) {
    $id = "$id".Trim().TrimStart('#'); $e = Get-LeconsEtat; $l = @($e.lecons | Where-Object { "$($_.id)" -eq $id }) | Select-Object -First 1
    if (-not $l) { return @{ ok = $false; lecon = $null } }
    $e.lecons = @($e.lecons | Where-Object { "$($_.id)" -ne $id }); Save-LeconsEtat $e
    Write-Journal -Action 'Leçon oubliée' -Resultat "n° $id retirée sur demande de Liam : $($l.regle)"
    @{ ok = $true; lecon = $l }
}

# ---------- Application avant une tâche similaire ----------
function Get-LeconsPertinentes([string]$texte, [int]$max = 3) {
    $q = @(Get-LeconMots $texte 3); if (-not $q.Count) { return @() }
    $sc = foreach ($l in (Get-Lecons)) {
        $perm = ("$($l.statut)" -eq 'permanente'); if (-not $perm -and [double]$l.confiance -lt 0.3) { continue }
        $lt = @(@($l.etiquettes) + (Get-LeconMots "$($l.contexte)" 3) | Select-Object -Unique)
        $com = @($q | Where-Object { $_ -in $lt }).Count; if (-not $com) { continue }
        [pscustomobject]@{ l = $l; s = ($com * [double]$l.confiance + $(if ($perm) { 1.0 } else { 0.0 })); c = [int]$l.confirmations }
    }
    @($sc | Sort-Object @{ e = 's'; Descending = $true }, @{ e = 'c'; Descending = $true } | Select-Object -First $max | ForEach-Object { $_.l })
}
function Use-LeconsAvant($a, [string]$ordre = '') {
    # Appelée au début de Invoke-UneAction. Journalise, retient les leçons appliquées et, sur Discord, cite la plus fiable.
    if (-not (Get-LeconsConfig).actif) { return }
    try {
        $desc = $(if (Get-Command Decrire-Action -ErrorAction SilentlyContinue) { Decrire-Action $a } else { '' })
        $l = @(Get-LeconsPertinentes "$($a.type) $desc $ordre")
        $script:LeconsAppliquees = @($l | ForEach-Object { "$($_.id)" })
        if (-not $l.Count) { return }
        Write-Journal -Action 'Leçons appliquées' -Resultat (($l | ForEach-Object { "n° $($_.id) : $($_.regle)" }) -join ' | ')
        $top = $l[0]; if ($script:CanalDiscord -and (Get-Command Add-TamponDiscord -ErrorAction SilentlyContinue) -and ([double]$top.confiance -ge 0.5 -or "$($top.statut)" -eq 'permanente')) { Add-TamponDiscord "Je me souviens : $($top.regle)" }
    } catch { Write-Journal -Action 'Leçons' -Resultat ("lecture : " + (Hide-Secrets $_.Exception.Message)) }
}
function Register-LeconContradiction([string[]]$ids) {
    if (-not @($ids).Count) { return }
    $e = Get-LeconsEtat; $n = 0
    foreach ($l in $e.lecons) { if ("$($l.id)" -in @($ids)) { $l.contredit = [int]$l.contredit + 1; $n++ } }
    if ($n) { Save-LeconsEtat $e }
}
function Register-LeconAction($a, $r) {
    # Appelée à la fin de Invoke-UneAction : une leçon « ça marche » ou « ça rate », par règles (aucune IA). Un échec contredit les leçons appliquées juste avant.
    if (-not (Get-LeconsConfig).actif) { return }
    try {
        $type = "$($a.type)"; $ok = [bool]($r -and $r.ok); $txt = "$($r.texte)"
        $tags = @($type, ($type -split '_'), $(if ($ok) { 'reussite' } else { 'echec' })) | ForEach-Object { $_ }
        if ($ok) { [void](Add-Lecon "Action $type" "L'action $type a abouti." '' "Pour « $type » : la démarche habituelle fonctionne, la reprendre telle quelle." $tags 0.4); return }
        $regle = $(if ($txt -match '(?i)introuvable|inconnu|n.existe pas|aucun') { "Pour « $type » : si la cible est introuvable, la chercher d'abord (nom exact ou chemin) avant d'agir." }
            elseif ($txt -match '(?i)refus|permission|interdit|non confirm') { "Pour « $type » : ne pas retenter après un refus ; le dire à Liam et lui demander son accord." }
            elseif ($txt -match '(?i)d[ée]lai|timeout|trop long|injoignable|r[ée]seau') { "Pour « $type » : en cas de délai ou de réseau coupé, réessayer une fois puis prévenir Liam." }
            else { "Pour « $type » : en cas d'échec, le dire clairement à Liam et proposer une autre voie au lieu d'insister." })
        [void](Add-Lecon "Action $type" '' "Échec de $type : $(ConvertTo-LeconTexte $txt 100)" $regle $tags 0.4)
        Register-LeconContradiction @($script:LeconsAppliquees)
    } catch { Write-Journal -Action 'Leçons' -Resultat ("écriture : " + (Hide-Secrets $_.Exception.Message)) }
}

# ---------- Revue de nuit ----------
function Update-LeconsPromotions {
    # Lit la décision de Liam sur les initiatives de promotion : approuvée -> règle permanente ; rejetée -> plus jamais reproposée.
    if (-not (Get-Command Get-Initiative -ErrorAction SilentlyContinue)) { return 0 }
    $e = Get-LeconsEtat; $n = 0
    foreach ($l in $e.lecons) {
        if (-not "$($l.promotion)") { continue }
        $i = Get-Initiative "$($l.promotion)"
        if (-not $i) { $l.promotion = ''; continue }
        if ("$($i.statut)" -eq 'approuvee') { $l.statut = 'permanente'; $l['permanente_le'] = (Get-Date).ToString('o'); $l.promotion = ''; $n++; Write-Journal -Action 'Leçon promue' -Resultat "n° $($l.id) devient une règle permanente (accord de Liam) : $($l.regle)" }
        elseif ("$($i.statut)" -eq 'rejetee') { $l.promotion = ''; $l.promotion_refusee = $true; Write-Journal -Action 'Promotion refusée' -Resultat "n° $($l.id) : Liam a refusé, elle ne sera pas reproposée" }
        elseif ("$($i.statut)" -eq 'oubliee') { $l.promotion = '' }
    }
    if ($n -or $e.lecons.Count) { Save-LeconsEtat $e }
    $n
}
function Get-LeconNegation([string]$regle) { [bool]((Get-LeconNorm $regle) -match '\b(jamais|evit\w*|pas|interdit|ne)\b') }
function Get-LeconCoeur([string]$regle) { (@((Get-LeconNorm $regle) -split ' ' | Where-Object { $_ -notin @('jamais', 'toujours', 'evite', 'eviter', 'pas', 'ne', 'faut', 'systematiquement', 'interdit') }) -join ' ') }
function Invoke-LeconsNuit([datetime]$now = (Get-Date), [switch]$Force) {
    $auj = $now.ToString('yyyy-MM-dd'); $e = Get-LeconsEtat
    if (-not $Force -and ($now.Hour -notin 3, 4 -or $e.derniere_nuit -eq $auj)) { return $null }
    $e.derniere_nuit = $auj
    $fus = 0; $bais = 0; $promos = @()
    # 1) doublons : la leçon permanente (sinon la plus ancienne) survit
    $l = @($e.lecons); $sup = @()
    for ($i = 0; $i -lt $l.Count; $i++) {
        if ($l[$i] -in $sup) { continue }
        for ($j = $i + 1; $j -lt $l.Count; $j++) {
            if ($l[$j] -in $sup) { continue }
            if ((Get-LeconSimilarite "$($l[$i].regle)" "$($l[$j].regle)") -ge 0.8 -and (Get-LeconNegation "$($l[$i].regle)") -eq (Get-LeconNegation "$($l[$j].regle)")) {
                $a = $l[$i]; $b = $l[$j]; if ("$($b.statut)" -eq 'permanente' -and "$($a.statut)" -ne 'permanente') { $a = $l[$j]; $b = $l[$i] }
                $a.confirmations = [int]$a.confirmations + [int]$b.confirmations; $a.confiance = [math]::Round([math]::Min(1.0, [math]::Max([double]$a.confiance, [double]$b.confiance) + 0.05), 3)
                $a.contredit = [int]$a.contredit + [int]$b.contredit; $a.etiquettes = @(@($a.etiquettes) + @($b.etiquettes) | Select-Object -Unique | Select-Object -First 8)
                $sup += $b; $fus++; Write-Journal -Action 'Leçons : fusion' -Resultat "n° $($b.id) fusionnée dans n° $($a.id)"
            }
        }
    }
    $e.lecons = @($e.lecons | Where-Object { $_ -notin $sup })
    # 2) règles opposées (« toujours X » / « jamais X ») : la moins confirmée baisse ; contradictions signalées pendant la journée
    $l = @($e.lecons)
    for ($i = 0; $i -lt $l.Count; $i++) { for ($j = $i + 1; $j -lt $l.Count; $j++) {
        if ((Get-LeconNegation "$($l[$i].regle)") -ne (Get-LeconNegation "$($l[$j].regle)") -and (Get-LeconSimilarite (Get-LeconCoeur "$($l[$i].regle)") (Get-LeconCoeur "$($l[$j].regle)")) -ge 0.7) {
            $pire = $(if ([int]$l[$i].confirmations -le [int]$l[$j].confirmations) { $l[$i] } else { $l[$j] }); if ("$($pire.statut)" -eq 'permanente') { $pire = $(if ($pire -eq $l[$i]) { $l[$j] } else { $l[$i] }) }
            if ("$($pire.statut)" -ne 'permanente') { $pire.contredit = [int]$pire.contredit + 1 }
        }
    } }
    foreach ($x in $e.lecons) {
        if ([int]$x.contredit -gt 0 -and "$($x.statut)" -ne 'permanente') { $x.confiance = [math]::Round([math]::Max(0.05, [double]$x.confiance - 0.15 * [int]$x.contredit), 3); $bais++; Write-Journal -Action 'Leçons : confiance baissée' -Resultat "n° $($x.id) contredite $($x.contredit) fois : $(Get-DatePct $x.confiance) %" }
        $x.contredit = 0
    }
    Save-LeconsEtat $e
    # 3) promotions décidées, puis nouvelles propositions (jamais appliquées sans « approuver »)
    [void](Update-LeconsPromotions)
    $e = Get-LeconsEtat
    if (Get-Command Add-Initiative -ErrorAction SilentlyContinue) {
        foreach ($x in $e.lecons) {
            if ("$($x.statut)" -eq 'permanente' -or "$($x.promotion)" -or $x.promotion_refusee -eq $true -or [double]$x.confiance -lt 0.8 -or [int]$x.confirmations -lt 3) { continue }
            $r = Add-Initiative "Promouvoir la leçon n° $($x.id) en règle permanente" 'maintenance' "« $($x.regle) » — confiance $(Get-DatePct $x.confiance) %, $($x.confirmations) confirmations. Approuvez pour la rendre permanente." 'normale' 1 'lecons' $now
            if ($r.ok -or $r.motif -eq 'doublon') { $x.promotion = "$($r.initiative.id)"; if ($r.ok) { $promos += $r.initiative; if (Get-Command Send-InitiativeCarte -ErrorAction SilentlyContinue) { [void](Send-InitiativeCarte $r.initiative) } } }
            else { $x.promotion_refusee = $true }
        }
        Save-LeconsEtat $e
    }
    Write-Journal -Action 'Leçons : revue de nuit' -Resultat "$fus fusionnée(s), $bais baissée(s), $($promos.Count) promotion(s) proposée(s)"
    @{ fusionnees = $fus; baissees = $bais; promotions = $promos }
}
function Update-Lecons([datetime]$now = (Get-Date)) {
    # Appelée par la boucle principale : seule la revue de nuit (3 h - 5 h), vérifiée au plus toutes les 5 minutes. Rien si lecons_actif n'est pas « oui » ou en mode jeu.
    if (-not (Get-LeconsConfig).actif -or $script:ModeJeu -eq $true) { return $false }
    if ($now.Hour -notin 3, 4 -or $now -lt $script:LeconsNuitProchain) { return $false }
    $script:LeconsNuitProchain = $now.AddMinutes(5)
    try { [bool](Invoke-LeconsNuit $now) } catch { Write-Journal -Action 'Leçons' -Resultat ("revue de nuit : " + (Hide-Secrets $_.Exception.Message)); $false }
}

# ---------- Style de parole (memoire\style-parole.json) ----------
function Get-StyleEtat {
    $o = Read-JsonMemoire 'style-parole.json'; $s = @{ prochain_id = 1; elements = @(); courte = 0; detaillee = 0; oublies = @() }
    if ($o) {
        foreach ($k in 'prochain_id', 'courte', 'detaillee') { if ($o.PSObject.Properties[$k] -and "$($o.$k)" -match '^\d+$') { $s[$k] = [int]$o.$k } }
        if ($o.PSObject.Properties['oublies']) { $s.oublies = @($o.oublies | ForEach-Object { "$_" }) }
        if ($o.PSObject.Properties['elements']) { $s.elements = @($o.elements | Where-Object { $_ } | ForEach-Object { $h = [ordered]@{}; foreach ($p in $_.PSObject.Properties) { $h[$p.Name] = $p.Value }; $h }) }
    }
    $s
}
function Save-StyleEtat($s) { Save-JsonMemoire 'style-parole.json' ([ordered]@{ prochain_id = $s.prochain_id; courte = $s.courte; detaillee = $s.detaillee; oublies = @($s.oublies); elements = @($s.elements) }) }
function Get-LongueurPreferee { $s = Get-StyleEtat; if ($s.detaillee -gt $s.courte) { 'detaillee' } else { 'courte' } }
function Add-StyleElement([string]$genre, [string]$cle, [string]$valeur = '', [string]$sens = '', [datetime]$now = (Get-Date)) {
    # genre : mot | tournure | sujet. Retourne l'élément, ou $null (sensible, secret ou oublié par Liam).
    if (Test-LeconInterdite "$cle $valeur $sens") { return $null }      # (contrôle sur le texte BRUT : le nettoyage masquerait le secret au lieu de le refuser)
    $cle = ConvertTo-LeconTexte $cle 60; $valeur = ConvertTo-LeconTexte $valeur 60; $sens = ConvertTo-LeconTexte $sens 120
    if (-not $cle) { return $null }
    $s = Get-StyleEtat; $ck = (Get-LeconNorm $cle); $cleOubli = "${genre}:$ck"
    if ($cleOubli -in $s.oublies) { return $null }
    $x = @($s.elements | Where-Object { "$($_.genre)" -eq $genre -and (Get-LeconNorm "$($_.cle)") -eq $ck }) | Select-Object -First 1
    if ($x) { $x.confirmations = [int]$x.confirmations + 1; $x.maj_le = $now.ToString('o'); if ($valeur) { $x.valeur = $valeur } }
    else { $x = [ordered]@{ id = "$($s.prochain_id)"; genre = $genre; cle = $cle; valeur = $valeur; sens = $sens; confirmations = 1; cree_le = $now.ToString('o'); maj_le = $now.ToString('o') }; $s.prochain_id = $s.prochain_id + 1; $s.elements = @($s.elements) + @($x) }
    Save-StyleEtat $s
    $x
}
function Remove-StyleElement([string]$id) {
    $id = "$id".Trim().TrimStart('#'); $s = Get-StyleEtat
    if ($id -in 'longueur') { $s.courte = 0; $s.detaillee = 0; Save-StyleEtat $s; Write-Journal -Action 'Style oublié' -Resultat 'longueur préférée réinitialisée'; return @{ ok = $true; element = @{ cle = 'longueur préférée' } } }
    $x = @($s.elements | Where-Object { "$($_.id)" -eq $id }) | Select-Object -First 1
    if (-not $x) { return @{ ok = $false; element = $null } }
    $s.elements = @($s.elements | Where-Object { "$($_.id)" -ne $id }); $s.oublies = @($s.oublies) + @("$($x.genre):$(Get-LeconNorm "$($x.cle)")")
    Save-StyleEtat $s; Write-Journal -Action 'Style oublié' -Resultat "n° $id retiré sur demande de Liam, ne sera pas réappris"
    @{ ok = $true; element = $x }
}
function Update-StyleDepuisOrdre([string]$texte, [datetime]$now = (Get-Date)) {
    # Tournures habituelles, longueur préférée, sujets récurrents. Un ordre qui contient un secret ou une donnée sensible n'apprend rien.
    if (-not "$texte".Trim() -or (Test-LeconInterdite $texte)) { return }
    $n = Get-LeconNorm $texte
    foreach ($t in $script:LeconsTournures) { if ($n -match $t[0]) { [void](Add-StyleElement 'tournure' $t[1] '' $t[2] $now) } }
    $s = $null
    if ($n -match '\b(plus court|trop long|en bref|sois bref|sois concis|resume|va a l essentiel|plus direct)\b') { $s = Get-StyleEtat; $s.courte++ }
    elseif ($n -match '\b(plus de details|developpe|detaille|explique plus|plus long|en detail)\b') { $s = Get-StyleEtat; $s.detaillee++ }
    if ($s) { Save-StyleEtat $s }
    foreach ($m in @($n -split ' ' | Where-Object { $_ -in $script:LeconsSujets } | Select-Object -Unique)) { [void](Add-StyleElement 'sujet' $m '' '' $now) }
}

# ---------- Mots mal transcrits : lecture probable ----------
function Get-ParoleConnus {
    # @{ connus = ensemble de mots normalisés (vocabulaire + grammaire) ; termes = @{ normalisé = affiché } } — lecture seule des fichiers de la voix.
    $connus = @{}; $termes = @{}
    foreach ($t in $script:LeconsTermesCles) { $termes[(Get-LeconNorm $t)] = $t }
    try {
        $f = Get-FichierMemoire 'vocabulaire-voix.txt'
        if (Test-Path $f) { foreach ($t in ((Get-Content $f -Raw -Encoding UTF8) -split ',')) { $t = $t.Trim(); $k = Get-LeconNorm $t; if ($k) { foreach ($w in ($k -split ' ')) { $connus[$w] = $true }; if ($k -notmatch ' ' -and $k.Length -ge 5) { $termes[$k] = $t } } } }
        $g = Get-FichierMemoire 'grammaire-voix.json'
        if (Test-Path $g) { foreach ($p in @(Get-Content $g -Raw -Encoding UTF8 | ConvertFrom-Json)) { foreach ($w in ((Get-LeconNorm "$p") -split ' ')) { if ($w) { $connus[$w] = $true } } } }
    } catch {}
    foreach ($x in (Get-StyleEtat).elements) { if ("$($x.genre)" -eq 'mot' -and $x.valeur) { $termes[(Get-LeconNorm "$($x.valeur)")] = "$($x.valeur)" } }
    @{ connus = $connus; termes = $termes }
}
function Test-LeconProche([string]$a, [string]$b) {
    # Deux mots normalisés qui se ressemblent assez pour être le même mot mal transcrit : même initiale et même finale, longueurs proches, peu de modifications.
    if ($a -eq $b -or $a.Length -lt 4 -or $b.Length -lt 5) { return $false }
    if ($a[0] -ne $b[0] -or $a[$a.Length - 1] -ne $b[$b.Length - 1] -or [math]::Abs($a.Length - $b.Length) -gt 2) { return $false }
    (Get-Levenshtein $a $b) -le [math]::Min(3, [math]::Floor($b.Length / 2))
}
function Find-AmbiguiteParole([string]$texte) {
    # $null, ou @{ original; propose; mots = @(@{ entendu; voulu; source; confirmations }); auto }. auto = une correction apprise et confirmée 3 fois : appliquée en le disant.
    $c = Get-ParoleConnus; $style = Get-StyleEtat; $mots = @(); $propose = $texte
    foreach ($tok in @([regex]::Split($texte, '[^\p{L}\p{N}]+') | Where-Object { $_.Length -ge 4 } | Select-Object -Unique)) {
        $k = Get-LeconNorm $tok; $voulu = $null; $src = ''; $conf = 0
        $app = @($style.elements | Where-Object { "$($_.genre)" -eq 'mot' -and (Get-LeconNorm "$($_.cle)") -eq $k -and $_.valeur }) | Select-Object -First 1
        if ($app) { $voulu = "$($app.valeur)"; $src = 'appris'; $conf = [int]$app.confirmations }
        elseif (-not $c.connus.ContainsKey($k) -and -not $c.termes.ContainsKey($k)) {
            $best = $null; $bd = 99
            foreach ($t in $c.termes.Keys) { if (Test-LeconProche $k $t) { $d = Get-Levenshtein $k $t; if ($d -lt $bd) { $bd = $d; $best = $t } } }
            if ($best) { $voulu = $c.termes[$best]; $src = 'proche' }
        }
        if ($voulu) { $mots += @{ entendu = $tok; voulu = $voulu; source = $src; confirmations = $conf }; $propose = [regex]::Replace($propose, "(?<![\p{L}\p{N}])$([regex]::Escape($tok))(?![\p{L}\p{N}])", { param($m) $voulu }.GetNewClosure()) }
    }
    if (-not $mots.Count) { return $null }
    @{ original = $texte; propose = $propose; mots = $mots; auto = (@($mots | Where-Object { $_.source -eq 'appris' -and $_.confirmations -ge 3 }).Count -eq $mots.Count) }
}
function Register-CorrectionMot([string]$ancien, [string]$corrige) {
    # Liam corrige : « je voulais dire Ollama ». Cherche dans l'ancien ordre le mot qui ressemble le plus au mot corrigé ; mémorise le mot (style) et une leçon.
    $best = $null; $bd = 99
    foreach ($u in @([regex]::Split($corrige, '[^\p{L}\p{N}]+') | Where-Object { $_.Length -ge 5 })) { foreach ($t in @([regex]::Split($ancien, '[^\p{L}\p{N}]+') | Where-Object { $_.Length -ge 4 })) {
        $a = Get-LeconNorm $t; $b = Get-LeconNorm $u
        if ($a -ne $b -and (Test-LeconProche $a $b)) { $d = Get-Levenshtein $a $b; if ($d -lt $bd) { $bd = $d; $best = @{ entendu = $t; voulu = $u } } }
    } }
    if (-not $best) { return $null }
    $el = Add-StyleElement 'mot' $best.entendu $best.voulu
    if (-not $el) { return @{ refuse = $true } }
    $l = Add-Lecon "Liam a corrigé ma compréhension d'un mot" "« $($best.voulu) »" "j'avais compris « $($best.entendu) »" "Quand j'entends « $($best.entendu) », Liam veut dire « $($best.voulu) » : proposer cette lecture." @('voix', 'correction', (Get-LeconNorm $best.entendu), (Get-LeconNorm $best.voulu)) 0.6
    Register-LeconContradiction @($script:LeconsAppliquees)
    @{ entendu = $best.entendu; voulu = $best.voulu; lecon = $l.lecon; element = $el }
}

# ---------- Voie texte / Discord : commandes, corrections, ambiguïtés ----------
function Resolve-LeconsOrdre([string]$texte, [datetime]$now = (Get-Date)) {
    # Appelée au début de Invoke-OrdreDiscord. Retourne @{ traite; texte } : traite = la réponse est déjà dans le tampon Discord ; texte = ordre éventuellement corrigé.
    $res = @{ traite = $false; texte = $texte }
    $n = (Get-LeconNorm $texte) -replace '^(?:jarvis )+', ''; $cfg = Get-LeconsConfig; $embed = ((Get-DiscordStyle) -eq 'embed')
    $cmdListe = ($n -match '^(?:(?:liste|montre|affiche|donne)(?: moi)? )?(?:(?:les|mes) )?lecons?(?: apprises?)?$')
    $mOubli = [regex]::Match($n, '^(?:oublie|oublier|supprime|efface)(?: la)? lecon(?: (?:n|no|numero))?\s*(\d+)$')
    $cmdStyle = ($n -match '^(?:(?:montre|affiche|donne)(?: moi)? )?(?:(?:le|mon) )?style(?: de parole)?$|^ma facon de parler$')
    $mStyle = [regex]::Match($n, '^(?:oublie|oublier|efface)(?: le)? style(?: (?:n|no|numero))?\s*(\d+|longueur)$')
    if ($cmdListe -or $mOubli.Success -or $cmdStyle -or $mStyle.Success) {
        $res.traite = $true
        if (-not $cfg.actif) { Add-TamponDiscord "L'apprentissage est désactivé, monsieur (réglage lecons_actif = non)."; return $res }
        if ($cmdListe) {
            [void](Update-LeconsPromotions); Write-Journal -Ordre $texte -Action 'Discord : leçons' -Resultat 'lues'
            $l = @(Get-Lecons); if ($embed) { Add-EmbedDiscord (New-EmbedLecons $l) } else { Add-TamponDiscord $(if ($l.Count) { (($l | Select-Object -First 8 | ForEach-Object { "n° $($_.id) : $($_.regle) (confiance $(Get-DatePct $_.confiance) %, $($_.confirmations) confirmation(s))" }) -join "`n") } else { "Je n'ai encore appris aucune leçon, monsieur." }) }
        } elseif ($mOubli.Success) {
            $r = Remove-Lecon $mOubli.Groups[1].Value
            Add-TamponDiscord $(if ($r.ok) { "Leçon n° $($mOubli.Groups[1].Value) oubliée : « $($r.lecon.regle) »." } else { "Je ne trouve pas de leçon n° $($mOubli.Groups[1].Value), monsieur." })
        } elseif ($cmdStyle) {
            Write-Journal -Ordre $texte -Action 'Discord : style de parole' -Resultat 'lu'
            $s = Get-StyleEtat; if ($embed) { Add-EmbedDiscord (New-EmbedStyle $s) } else { Add-TamponDiscord ("Réponses " + $(if ((Get-LongueurPreferee) -eq 'courte') { 'courtes et directes' } else { 'détaillées' }) + ". " + $(if (@($s.elements).Count) { (@($s.elements | Select-Object -First 8 | ForEach-Object { "n° $($_.id) : $($_.cle)$(if ($_.valeur) { ' = ' + $_.valeur })" }) -join ' ; ') } else { "Je n'ai encore rien appris de votre façon de parler." })) }
        } else {
            $r = Remove-StyleElement $mStyle.Groups[1].Value
            Add-TamponDiscord $(if ($r.ok) { "Style oublié : « $($r.element.cle) ». Je ne le réapprendrai pas." } else { "Je ne trouve pas d'élément de style n° $($mStyle.Groups[1].Value), monsieur." })
        }
        return $res
    }
    if (-not $cfg.actif) { return $res }
    try {
        # réponse à « Tu veux dire … ? »
        $p = $script:LeconsEnAttente
        if ($p) {
            $script:LeconsEnAttente = $null
            if ($now -le $p.expire) {
                if ($n -match '^(?:oui|ouais|yes|exact|c est ca|voila|tout a fait|c est bien ca)$') {
                    foreach ($m in $p.mots) { [void](Add-StyleElement 'mot' $m.entendu $m.voulu); [void](Add-Lecon "Liam a confirmé une lecture" "« $($m.voulu) »" "j'avais entendu « $($m.entendu) »" "Quand j'entends « $($m.entendu) », Liam veut dire « $($m.voulu) » : proposer cette lecture." @('voix', 'correction', (Get-LeconNorm $m.entendu), (Get-LeconNorm $m.voulu)) 0.6) }
                    $res.texte = $p.propose; $script:LeconsDernierOrdre = $p.propose; return $res
                }
                if ($n -match '^(?:non|nan|pas du tout|c est pas ca)$') { Add-TamponDiscord "D'accord, monsieur : je ne change rien."; $res.traite = $true; return $res }
            }
        }
        # correction explicite d'un mot
        $ancien = $script:LeconsDernierOrdre
        $mc = [regex]::Match($n, '^(?:non |nan |euh )?(?:je voulais dire|je veux dire|je disais|ca s ecrit|c est)\s+(.+)$')
        if ($mc.Success -and $ancien) {
            $voulu = ([regex]::Match($texte, '(?i)(?:je voulais dire|je veux dire|je disais|ça s.écrit|ca s.ecrit|c.est)\s+(.+)$')).Groups[1].Value.Trim(' .!?')
            $r = Register-CorrectionMot $ancien $voulu      # (aucun mot ressemblant dans l'ordre précédent : ce n'était pas une correction, l'ordre suit son chemin normal)
            if ($r) {
                Add-TamponDiscord $(if ($r.refuse) { "Je ne retiens pas cela, monsieur (donnée sensible ou secret)." } else { "Noté, monsieur : « $($r.entendu) » veut dire « $($r.voulu) »." })
                $res.traite = $true; return $res
            }
        }
        # correction générale : « non, plutôt ... » après un ordre -> une leçon
        $mg = [regex]::Match($texte, '(?i)^(?:non|nan|pas comme ça|c.est pas ça|ce n.est pas ça)\b[\s,.:;!-]*(.{8,})$')
        if ($mg.Success -and $ancien) {
            $corr = $mg.Groups[1].Value.Trim()
            $l = Add-Lecon "Liam a corrigé ma façon de faire (ordre : $(ConvertTo-LeconTexte $ancien 80))" '' 'ma manière de faire ne convenait pas' "Pour ce genre de demande : $corr" (@('correction') + @(Get-LeconMots $ancien 4 | Select-Object -First 5)) 0.6
            Register-LeconContradiction @($script:LeconsAppliquees); Update-StyleDepuisOrdre $corr $now
            Add-TamponDiscord $(if ($l.ok) { "Noté, monsieur : leçon n° $($l.lecon.id)$(if ($l.renforcee) { ' renforcée' })." } else { "Je ne retiens pas cela, monsieur ($($l.motif))." })
            $res.traite = $true; return $res
        }
        Update-StyleDepuisOrdre $res.texte $now
        $amb = Find-AmbiguiteParole $res.texte
        if ($amb) {
            if ($amb.auto) { Add-TamponDiscord "J'ai compris « $($amb.propose) », monsieur."; $res.texte = $amb.propose }
            else { $script:LeconsEnAttente = @{ propose = $amb.propose; mots = $amb.mots; expire = $now.AddMinutes(5) }; Add-TamponDiscord "Tu veux dire « $($amb.propose) » ? (oui / non)"; $script:LeconsDernierOrdre = $res.texte; $res.traite = $true; return $res }
        }
        $script:LeconsDernierOrdre = $res.texte
    } catch { Write-Journal -Action 'Leçons' -Resultat ("erreur : " + (Hide-Secrets $_.Exception.Message)) }
    $res
}
