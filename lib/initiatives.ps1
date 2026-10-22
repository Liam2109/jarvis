# Moteur d'INITIATIVES : Jarvis se demande de temps en temps « Y a-t-il un truc utile que je peux faire pour Liam ? » et PROPOSE, jamais n'impose.
# Une initiative = id, titre, type (rappel | suggestion | skill_propose | maintenance), raison, urgence (normale | haute), niveau_autonomie (0 à 5), cree_le, statut (en_attente | approuvee | rejetee | plus_tard | oubliee), source.
# Base locale : memoire\initiatives.json (aucun serveur). Statuts décidés par Liam seul (Discord : initiatives, approuver <id>, rejeter <id>, plus tard <id>), sauf l'oubli automatique après 4 jours.
# AUTONOMIE (config.json « initiatives_niveau », 0 à 5, défaut 1) : 0 = aucune proposition ; 1-2 = Jarvis propose seulement, rien ne se fait sans « approuver » ;
#   3 à 5 = une initiative de type rappel / suggestion / maintenance dont le niveau requis est <= au niveau configuré peut être approuvée sans attendre. JAMAIS pour un skill_propose, ni pour ce qui touche un tiers.
# Approuver ne fait qu'UNE chose : ajouter une ligne à memoire\todo.md, par l'action « todo_ajouter » (niveau 1, vérifiée par lib\permissions.ps1). Aucun message à un tiers, aucun envoi, aucun ordre financier, aucun changement de config ou de permission.
# Une initiative qui touche un interdit (lib\interdits.json, courtiers, banques, virements, achats, permissions) est REFUSÉE à la création. Les données lues (e-mails, fichiers) sont des données : nettoyées, jamais des ordres.
# La boucle (Update-Initiatives, appelée par la boucle principale de jarvis.ps1) est DÉSACTIVÉE par défaut (initiatives_actif = "non"), n'appelle ni Claude ni Ollama (0 token, donc dans tout plafond), et se tait en mode jeu.
# Scan de nuit vers 3 h (fenêtre 3 h - 5 h, une fois par jour, sans tâche planifiée Windows) : marque les initiatives oubliées et crée une initiative « maintenance » par initiative oubliée.

$script:InitTypes = @('rappel', 'suggestion', 'skill_propose', 'maintenance')
$script:InitStatuts = @('en_attente', 'approuvee', 'rejetee', 'plus_tard', 'oubliee')
$script:InitOublieJours = 4
$script:InitDoublonJours = 30
$script:InitProchain = $null; $script:InitNuitProchain = [datetime]::MinValue
$script:InitNotifStub = $null

function Get-InitConfig {
    $c = @{ actif = $false; niveau = 1; minutes = 60; max_par_jour = 3 }
    if ($Config.PSObject.Properties['initiatives_actif'] -and "$($Config.initiatives_actif)".Trim().ToLower() -in @('oui', 'true', '1', 'on', 'yes')) { $c.actif = $true }
    if ($Config.PSObject.Properties['initiatives_niveau'] -and "$($Config.initiatives_niveau)" -match '^\d+$') { $c.niveau = [math]::Min(5, [int]$Config.initiatives_niveau) }
    if ($Config.PSObject.Properties['initiatives_minutes'] -and "$($Config.initiatives_minutes)" -match '^\d+$') { $c.minutes = [math]::Max(5, [math]::Min(1440, [int]$Config.initiatives_minutes)) }
    if ($Config.PSObject.Properties['initiatives_max_par_jour'] -and "$($Config.initiatives_max_par_jour)" -match '^\d+$') { $c.max_par_jour = [math]::Min(20, [int]$Config.initiatives_max_par_jour) }
    $c
}

# ---------- Base locale ----------
function Get-InitEtat {
    $o = Read-JsonMemoire 'initiatives.json'; $e = @{ initiatives = @(); prochain_id = 1; derniere_nuit = '' }
    if ($o) {
        if ($o.PSObject.Properties['prochain_id'] -and "$($o.prochain_id)" -match '^\d+$') { $e.prochain_id = [int]$o.prochain_id }
        if ($o.PSObject.Properties['derniere_nuit']) { $e.derniere_nuit = "$($o.derniere_nuit)" }
        if ($o.PSObject.Properties['initiatives']) { $e.initiatives = @($o.initiatives | Where-Object { $_ } | ForEach-Object { $h = [ordered]@{}; foreach ($p in $_.PSObject.Properties) { $h[$p.Name] = $p.Value }; $h }) }
    }
    $e
}
function Save-InitEtat($e) { Save-JsonMemoire 'initiatives.json' ([ordered]@{ prochain_id = $e.prochain_id; derniere_nuit = $e.derniere_nuit; initiatives = @($e.initiatives) }) }
function ConvertTo-InitTexte($x, [int]$max) {
    # Donnée -> texte court d'une ligne : secrets masqués, caractères de contrôle retirés.
    $t = ((Hide-Secrets "$x") -replace '[\u0000-\u001f\u007f]', ' ' -replace '\s+', ' ').Trim()
    if ($t.Length -gt $max) { $t.Substring(0, $max - 1) + '…' } else { $t }
}
function Get-InitDate($i, [string]$cle = 'cree_le') { $d = [datetime]::MinValue; if ([datetime]::TryParse("$($i[$cle])", [Globalization.CultureInfo]::InvariantCulture, [Globalization.DateTimeStyles]::RoundtripKind, [ref]$d)) { $d } else { [datetime]::MinValue } }

# ---------- Garde-fous ----------
function Test-InitiativeInterdite([string]$texte) {
    # Retourne la raison du refus, ou '' si l'initiative est permise. Une initiative ne lève jamais un interdit et ne monte jamais un niveau de permission.
    if (Get-Variable MotifsInterdits -Scope Script -ErrorAction SilentlyContinue) { foreach ($m in $script:MotifsInterdits) { if ($texte -match $m.re) { return "interdit : $($m.raison)" } } }
    if ($texte -match '(?i)\b(virements?|achats?|acheter|vendre|vente|trades?|trader|ordre de bourse|ordre financier)\b') { return 'interdit : action financière' }
    if ($texte -match '(?i)antivirus|pare.?feu|firewall|defender' -and $texte -match '(?i)d[ée]sactiv|coup\w*|[ée]teign\w*|arr[êe]t\w*|stopp\w*|contourn\w*') { return 'interdit : antivirus ou pare-feu' }
    if ($texte -match '(?i)mots? de passe' -and $texte -match '(?i)modifi\w*|chang\w*|r[ée]initialis\w*') { return 'interdit : modifier un mot de passe' }
    if ($texte -match '(?i)permission|autonomie|interdit|garde.?fou|niveau 3|interdits\.json' -and $texte -match '(?i)\b(lever|lev[ée]e|monter|augment\w*|baisser|d[ée]sactiv\w*|contourn\w*|supprim\w*|retir\w*|assoupl\w*|ignor\w*|modifi\w*|changer)\b') { return 'interdit : toucher aux permissions ou aux interdits' }
    ''
}
function Test-InitiativeTiers([string]$texte) {
    # Vrai si l'initiative parle d'écrire, d'envoyer ou de contacter quelqu'un : validation de Liam TOUJOURS, quel que soit le niveau d'autonomie.
    [bool]($texte -match '(?i)\b(e-?mails?|courriels?|mails?|messages?|sms|whatsapp|envoy\w+|relanc\w+|r[ée]pond\w+|contacter|appeler|[ée]crire|postuler|candidater|inviter|publi\w+)\b')
}
function Test-InitiativeSansApprobation($i, [int]$niveau = -1) {
    # Faux dès que le niveau configuré est < 3. Au-delà : seulement un rappel / une suggestion / une maintenance dont le niveau requis est couvert, sans tiers, sans interdit.
    if ($niveau -lt 0) { $niveau = (Get-InitConfig).niveau }
    if ($niveau -lt 3 -or "$($i.statut)" -ne 'en_attente') { return $false }
    if ("$($i.type)" -notin @('rappel', 'suggestion', 'maintenance') -or "$($i.source)" -eq 'lecons') { return $false }      # (promouvoir une leçon en règle permanente : toujours l'accord de Liam)
    if ([int]$i.niveau_autonomie -gt $niveau) { return $false }
    $t = "$($i.titre) $($i.raison)"
    if (Test-InitiativeTiers $t) { return $false }
    [string]::IsNullOrEmpty((Test-InitiativeInterdite $t))
}

# ---------- Ajouter / lister / décider ----------
function Add-Initiative([string]$titre, [string]$type = 'suggestion', [string]$raison = '', [string]$urgence = 'normale', [int]$autonomie = 1, [string]$source = 'manuel', [datetime]$now = (Get-Date)) {
    # @{ ok; motif; initiative }
    $titre = ConvertTo-InitTexte $titre 100; $raison = ConvertTo-InitTexte $raison 200; $source = ConvertTo-InitTexte $source 40
    if (-not $titre) { return @{ ok = $false; motif = 'titre vide'; initiative = $null } }
    if ($type -notin $script:InitTypes) { return @{ ok = $false; motif = "type inconnu ($type)"; initiative = $null } }
    if ($urgence -notin @('normale', 'haute')) { $urgence = 'normale' }
    $autonomie = [math]::Max(0, [math]::Min(5, $autonomie))
    $refus = Test-InitiativeInterdite "$titre $raison"
    if ($refus) { Write-Journal -Action 'Initiative refusée' -Resultat "$refus : « $titre »"; return @{ ok = $false; motif = $refus; initiative = $null } }
    $e = Get-InitEtat
    $cle = $titre.ToLowerInvariant()
    foreach ($x in $e.initiatives) { if ("$($x.titre)".ToLowerInvariant() -eq $cle -and ($now - (Get-InitDate $x)).TotalDays -lt $script:InitDoublonJours) { return @{ ok = $false; motif = 'doublon'; initiative = $x } } }
    $i = [ordered]@{ id = "$($e.prochain_id)"; titre = $titre; type = $type; raison = $raison; urgence = $urgence; niveau_autonomie = $autonomie; cree_le = $now.ToString('o'); statut = 'en_attente'; source = $source }
    $e.prochain_id = $e.prochain_id + 1; $e.initiatives = @($e.initiatives) + @($i)
    Save-InitEtat $e
    Write-Journal -Action 'Initiative créée' -Resultat "n° $($i.id) ($type, $urgence, niveau $autonomie, source $source) : $titre"
    @{ ok = $true; motif = ''; initiative = $i }
}
function Get-Initiatives([string]$statut = '') {
    $l = @((Get-InitEtat).initiatives)
    if ($statut) { $l = @($l | Where-Object { "$($_.statut)" -eq $statut }) }
    $l
}
function Get-Initiative([string]$id) { $id = "$id".Trim().TrimStart('#'); @(Get-Initiatives | Where-Object { "$($_.id)" -eq $id }) | Select-Object -First 1 }

function Invoke-InitiativeEffet($i) {
    # Seul effet d'une approbation : une ligne dans la to-do, par l'action « todo_ajouter » SI les permissions la classent au niveau 1.
    $a = [pscustomobject]@{ type = 'todo_ajouter'; texte = "Initiative n° $($i.id) : $($i.titre)" }
    if (-not (Get-Command Get-Niveau -ErrorAction SilentlyContinue) -or -not $script:Actions -or -not $script:Actions.ContainsKey('todo_ajouter')) { return $false }
    $n = Get-Niveau $a
    if ($n.niveau -ne 1) { Write-Journal -Action 'Initiative : effet refusé' -Resultat "n° $($i.id), permission niveau $($n.niveau) ($($n.raison))"; return $false }
    try { $r = & $script:Actions['todo_ajouter'].run $a; [bool]($r -and $r.ok) } catch { $false }
}
function Set-InitiativeStatut([string]$id, [string]$statut, [string]$par = 'Liam') {
    # Approuver / rejeter / reporter. Seules les initiatives en attente, reportées ou oubliées se décident ; une décision (approuvée / rejetée) est définitive.
    if ($statut -notin @('approuvee', 'rejetee', 'plus_tard')) { return @{ ok = $false; motif = 'statut non permis'; initiative = $null } }
    $id = "$id".Trim().TrimStart('#'); $e = Get-InitEtat
    $i = @($e.initiatives | Where-Object { "$($_.id)" -eq $id }) | Select-Object -First 1
    if (-not $i) { return @{ ok = $false; motif = 'introuvable'; initiative = $null } }
    if ("$($i.statut)" -in @('approuvee', 'rejetee')) { return @{ ok = $false; motif = "déjà décidée ($($i.statut))"; initiative = $i } }
    $i.statut = $statut; $i['decide_le'] = (Get-Date).ToString('o'); $i['decide_par'] = $par
    Save-InitEtat $e
    $effet = $false
    if ($statut -eq 'approuvee') { $effet = Invoke-InitiativeEffet $i }
    Write-Journal -Action "Initiative $statut" -Resultat "n° $id par $par : $($i.titre)$(if ($statut -eq 'approuvee') { if ($effet) { ' (ajoutée à la to-do)' } else { ' (rien ajouté à la to-do)' } })"
    @{ ok = $true; motif = ''; initiative = $i; effet = $effet }
}
function Approve-Initiative([string]$id, [string]$par = 'Liam') { Set-InitiativeStatut $id 'approuvee' $par }
function Reject-Initiative([string]$id, [string]$par = 'Liam') { Set-InitiativeStatut $id 'rejetee' $par }
function Suspend-Initiative([string]$id, [string]$par = 'Liam') { Set-InitiativeStatut $id 'plus_tard' $par }

# ---------- Oubli (4 jours) et scan de nuit ----------
function Invoke-InitiativesOubli([datetime]$now = (Get-Date)) {
    # Toute initiative EN ATTENTE depuis plus de 4 jours devient « oubliee ». Retourne les initiatives oubliées.
    $e = Get-InitEtat; $oub = @()
    foreach ($i in $e.initiatives) { if ("$($i.statut)" -eq 'en_attente' -and ($now - (Get-InitDate $i)).TotalDays -gt $script:InitOublieJours) { $i.statut = 'oubliee'; $i['oublie_le'] = $now.ToString('o'); $oub += $i } }
    if ($oub.Count) { Save-InitEtat $e; foreach ($i in $oub) { Write-Journal -Action 'Initiative oubliée' -Resultat "n° $($i.id) sans réponse depuis plus de $script:InitOublieJours jours : $($i.titre)" } }
    $oub
}
function Invoke-InitiativesNuit([datetime]$now = (Get-Date), [switch]$Force) {
    # Une fois par jour, entre 3 h et 5 h (ou Force). Une maintenance par initiative oubliée ; une maintenance oubliée n'en crée pas d'autre (pas de cascade).
    $auj = $now.ToString('yyyy-MM-dd'); $e = Get-InitEtat
    if (-not $Force -and ($now.Hour -notin 3, 4 -or $e.derniere_nuit -eq $auj)) { return $null }
    $e.derniere_nuit = $auj; Save-InitEtat $e
    $oub = @(Invoke-InitiativesOubli $now); $crees = @()
    foreach ($i in $oub) {
        if ("$($i.type)" -eq 'maintenance') { continue }
        $r = Add-Initiative "Reviewer ou rejeter l'initiative n° $($i.id)" 'maintenance' "Sans réponse depuis plus de $script:InitOublieJours jours : « $($i.titre) ». Approuvez pour la garder en tête, ou rejetez-la." 'normale' 1 'nuit' $now
        if ($r.ok) { $crees += $r.initiative; [void](Send-InitiativeCarte $r.initiative) }
    }
    Write-Journal -Action 'Initiatives : scan de nuit' -Resultat "$($oub.Count) oubliée(s), $($crees.Count) maintenance(s) créée(s)"
    @{ oubliees = $oub; maintenances = $crees }
}

# ---------- Cartes Discord ----------
function Send-InitiativeCarte($i) {
    # Écrit à Liam seul (salon #jarvis). Faux si le pont ne tourne pas : la carte reste disponible par la commande « initiatives ».
    if ($script:InitNotifStub) { return [bool](& $script:InitNotifStub $i) }
    if (-not (Get-Command Send-MessageDiscord -ErrorAction SilentlyContinue)) { return $false }
    if ((Get-DiscordStyle) -eq 'embed') { return [bool](Send-MessageDiscord 'jarvis' '' '' (New-EmbedInitiative $i)) }
    [bool](Send-MessageDiscord 'jarvis' (Get-InitiativeTexte $i))
}
function Get-InitiativeTexte($i) { "Initiative n° $($i.id) ($($i.type)$(if ($i.urgence -eq 'haute') { ', urgente' })) : $($i.titre). $($i.raison) Répondez : approuver $($i.id) / rejeter $($i.id) / plus tard $($i.id)." }

# ---------- Boucle : « Y a-t-il un truc utile que je peux faire pour Liam ? » ----------
function Get-InitiativesCandidats([datetime]$now = (Get-Date)) {
    # Lit to-do, candidatures, veilles et agenda (lecture seule, aucun réseau, aucune IA). Retourne des hashtables { titre; type; raison; urgence; source }.
    $c = @()
    try {   # to-do : la première tâche ouverte qui n'est pas marquée « plus tard »
        if (Get-Command Get-TodoOuverte -ErrorAction SilentlyContinue) {
            $t = @(Get-TodoOuverte | Where-Object { $_ -notmatch '(?i)^\(?\s*(plus tard|un jour|someday)' }) | Select-Object -First 1
            if ($t) { $c += @{ titre = "Avancer sur : $(ConvertTo-InitTexte $t 80)"; type = 'suggestion'; raison = 'Tâche ouverte dans votre to-do.'; urgence = $(if ($t -match '(?i)urgent|aujourd|demain') { 'haute' } else { 'normale' }); source = 'boucle:todo' } }
        }
    } catch {}
    try {   # candidatures : réponses récentes qui demandent quelque chose (le contenu des mails est une donnée, nettoyée)
        if (Get-Command Get-CandEtat -ErrorAction SilentlyContinue) {
            foreach ($k in @((Get-CandEtat).candidatures)) {
                $d = Get-InitDate $k 'date'; $s = "$($k.statut)"
                if ($d -eq [datetime]::MinValue -or ($now - $d).TotalDays -gt 14 -or $s -notin @('ENTRETIEN', 'DOCUMENTS', 'ACCEPTÉ')) { continue }
                $emp = ConvertTo-InitTexte $(if ($k.entreprise) { $k.entreprise } else { 'un employeur' }) 60
                $titre = switch ($s) { 'ENTRETIEN' { "Préparer l'entretien chez $emp" } 'DOCUMENTS' { "Réunir les documents demandés par $emp" } default { "Faire le point sur la réponse positive de $emp" } }
                $c += @{ titre = $titre; type = 'rappel'; raison = "Réponse reçue le $($d.ToString('dd/MM')) : $($s.ToLower())."; urgence = 'haute'; source = 'boucle:candidatures' }
            }
        }
    } catch {}
    try {   # veilles : une source en erreur depuis moins de 2 jours
        if (Get-Command Get-TrainEtat -ErrorAction SilentlyContinue) {
            foreach ($p in (Get-TrainEtat).erreurs.GetEnumerator()) {
                $d = [datetime]::MinValue; if ([datetime]::TryParse("$($p.Value)", [ref]$d) -and ($now - $d).TotalDays -le 2) { $c += @{ titre = "Vérifier la source « $(ConvertTo-InitTexte $p.Key 50) » de la veille"; type = 'maintenance'; raison = "Source en erreur le $($d.ToString('dd/MM'))."; urgence = 'normale'; source = 'boucle:veille' } }
            }
        }
    } catch {}
    try {   # agenda : rappels non faits dont l'heure est passée depuis plus de 2 h (Jarvis était éteint)
        if (Get-Command Get-Rappels -ErrorAction SilentlyContinue) {
            foreach ($r in @(Get-Rappels)) {
                $d = [datetime]::MinValue
                if (-not $r.fait -and [datetime]::TryParseExact("$($r.quand)", 'yyyy-MM-dd HH:mm', [Globalization.CultureInfo]::InvariantCulture, [Globalization.DateTimeStyles]::None, [ref]$d) -and ($now - $d).TotalHours -gt 2) {
                    $c += @{ titre = "Rappel manqué : $(ConvertTo-InitTexte $r.texte 70)"; type = 'rappel'; raison = "Prévu le $($d.ToString('dd/MM à HH:mm')), non dit."; urgence = 'haute'; source = 'boucle:agenda' }
                }
            }
        }
    } catch {}
    @($c | Sort-Object { if ($_.urgence -eq 'haute') { 0 } else { 1 } })
}
function Invoke-InitiativesBoucle([datetime]$now = (Get-Date)) {
    # Un tour : au plus « initiatives_max_par_jour » nouvelles initiatives par jour (source boucle:*). Niveau 0 : rien. Retourne les initiatives créées.
    $cfg = Get-InitConfig; if ($cfg.niveau -lt 1) { return @() }
    $auj = $now.ToString('yyyy-MM-dd')
    $deja = @((Get-InitEtat).initiatives | Where-Object { "$($_.source)" -like 'boucle:*' -and (Get-InitDate $_).ToString('yyyy-MM-dd') -eq $auj }).Count
    $reste = $cfg.max_par_jour - $deja; $crees = @()
    Write-Journal -Action 'Initiatives' -Resultat "question : y a-t-il un truc utile à faire pour Liam ? ($deja créée(s) aujourd'hui sur $($cfg.max_par_jour))"
    if ($reste -le 0) { return @() }
    foreach ($k in (Get-InitiativesCandidats $now)) {
        if ($reste -le 0) { break }
        $r = Add-Initiative $k.titre $k.type $k.raison $k.urgence 1 $k.source $now
        if ($r.ok) { $reste--; $crees += $r.initiative; [void](Send-InitiativeCarte $r.initiative) }
    }
    foreach ($i in $crees) { if (Test-InitiativeSansApprobation $i $cfg.niveau) { [void](Set-InitiativeStatut $i.id 'approuvee' "auto (niveau $($cfg.niveau))") } }
    $crees
}
function Update-Initiatives([datetime]$now = (Get-Date)) {
    # Appelée par la boucle principale. Ne fait RIEN si initiatives_actif n'est pas « oui », ni en mode jeu. Premier tour une période après le démarrage.
    $cfg = Get-InitConfig; if (-not $cfg.actif -or $cfg.niveau -lt 1) { return $false }
    if ($script:ModeJeu -eq $true) { return $false }
    if ($now.Hour -in 3, 4 -and $now -ge $script:InitNuitProchain) { $script:InitNuitProchain = $now.AddMinutes(5); try { [void](Invoke-InitiativesNuit $now) } catch { Write-Journal -Action 'Initiatives' -Resultat ("scan de nuit : " + (Hide-Secrets $_.Exception.Message)) } }
    if ($null -eq $script:InitProchain) { $script:InitProchain = $now.AddMinutes($cfg.minutes); return $false }
    if ($now -lt $script:InitProchain) { return $false }
    $script:InitProchain = $now.AddMinutes($cfg.minutes)
    try { [void](Invoke-InitiativesBoucle $now) } catch { Write-Journal -Action 'Initiatives' -Resultat ("erreur : " + (Hide-Secrets $_.Exception.Message)) }
    $true
}

# ---------- Commandes Discord : initiatives, approuver <id>, rejeter <id>, plus tard <id> ----------
function Invoke-InitiativeCommande([string]$texte) {
    # $true si l'ordre est traité ici (réponse dans le tampon Discord). Aucune IA : des règles.
    $n = (ConvertTo-OrdreNorm $texte).Trim() -replace '^(?:jarvis[\s,]+)+', '' -replace '[\s.!?]+$', ''
    $embed = ((Get-DiscordStyle) -eq 'embed')
    if ($n -match '^(?:(?:liste|montre|affiche|donne)(?: moi)? )?(?:(?:les|mes) )?initiatives?$') {
        Write-Journal -Ordre $texte -Action 'Discord : initiatives' -Resultat 'lues'
        $l = @(Get-Initiatives | Where-Object { "$($_.statut)" -in 'en_attente', 'plus_tard' })
        $oub = @(Get-Initiatives 'oubliee').Count
        if ($embed) { Add-EmbedDiscord (New-EmbedInitiatives $l $oub) } else { Add-TamponDiscord $(if ($l.Count) { (($l | ForEach-Object { Get-InitiativeTexte $_ }) -join "`n") } else { 'Aucune initiative en attente, monsieur.' }) }
        return $true
    }
    $m = [regex]::Match($n, '^(approuve|approuver|j approuve|rejette|rejeter|je rejette|plus tard|reporte|reporter)(?:\s+l.?initiative)?(?:\s+(?:n|no|numero)\s*°?)?\s*#?\s*(\d+)$')
    if (-not $m.Success) { return $false }
    $v = $m.Groups[1].Value; $id = $m.Groups[2].Value
    $r = $(if ($v -match '^(?:j )?approuv') { Approve-Initiative $id } elseif ($v -match 'rejet') { Reject-Initiative $id } else { Suspend-Initiative $id })
    if (-not $r.ok) { Add-TamponDiscord $(if ($r.motif -eq 'introuvable') { "Je ne trouve pas d'initiative n° $id, monsieur." } else { "L'initiative n° $id est $($r.motif), monsieur." }); return $true }
    $i = $r.initiative
    $phrase = $(switch ("$($i.statut)") {
        'approuvee' { "Initiative n° $id approuvée : « $($i.titre) ».$(if ($r.effet) { ' Je l''ai ajoutée à votre to-do.' } else { ' Rien n''a été ajouté à la to-do.' }) Je n''écris à personne." }
        'rejetee' { "Initiative n° $id rejetée : « $($i.titre) »." }
        default { "Initiative n° $id remise à plus tard : « $($i.titre) »." } })
    Add-TamponDiscord $phrase
    if ("$($i.source)" -eq 'skills' -and (Get-Command Invoke-SkillsDecision -ErrorAction SilentlyContinue)) {      # étapes des skills (lib\skills.ps1) : génération après l'idée, déplacement ou archivage après la validation
        $sk = Invoke-SkillsDecision $i; if ($sk) { if ($sk.embed) { Add-EmbedDiscord $sk.embed } ; Add-TamponDiscord $sk.texte }
    }
    elseif ("$($i.source)" -eq 'presets' -and (Get-Command Invoke-PresetsDecision -ErrorAction SilentlyContinue)) {      # presets (lib\presets.ps1) : enregistrés seulement après « approuver » de Liam
        $pr = Invoke-PresetsDecision $i; if ($pr) { Add-TamponDiscord $pr.texte }
    }
    $true
}
