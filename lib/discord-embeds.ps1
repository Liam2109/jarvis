# Discord : modèles de messages (embeds) propres et compréhensibles d'un coup d'œil, sur mobile comme sur PC. Aucun bloc de code, aucune colonne en espaces.
# Principes : titre court avec une icône, une phrase d'explication en français simple, 3 à 6 champs (une idée, une icône, un libellé court), chaque chiffre accompagné d'un mot
# (jamais « 16 » seul : « 16 tâches ouvertes »), couleur selon le sens (vert : tout va bien / hausse, rouge : problème / baisse, orange : à surveiller, gris : neutre), pied avec source et date.
# Une fonction PURE par modèle (testable, et utilisée par l'aperçu : jarvis.ps1 discord-apercu) ; les fonctions Get-Embed… lisent les vraies données puis appellent le modèle.
# config.json « discord_style » : "embed" (défaut) ou "texte" (texte simple, comme avant). Jamais de blague sur les tâches, les erreurs, les refus ni la finance (voir Test-HumourPermis).
function Get-DiscordStyle { if ($Config.PSObject.Properties['discord_style'] -and "$($Config.discord_style)".Trim().ToLowerInvariant() -eq 'texte') { 'texte' } else { 'embed' } }
function Get-EmojiModele([string]$nom) {
    switch ($nom) { 'vide' { [char]::ConvertFromUtf32(0x2610) } 'coche' { [char]::ConvertFromUtf32(0x2611) } default { Get-EmojiDiscord $nom } }
}
function Get-BarreDiscord([int]$n, [int]$max, [int]$larg = 10) {
    $max = [math]::Max(1, $max); $p = [math]::Max(0, [math]::Min($larg, [int][math]::Round($larg * $n / $max, [MidpointRounding]::AwayFromZero)))
    ([string][char]0x2588) * $p + ([string][char]0x2591) * ($larg - $p)
}
function Get-MotNombre([int]$n, [string]$un, [string]$plusieurs, [string]$aucun = '') {
    if ($n -le 0 -and $aucun) { return $aucun }; if ($n -eq 1) { return "1 $un" }; "$n $plusieurs"
}
function Format-SignePct($x) { $fr = [Globalization.CultureInfo]::GetCultureInfo('fr-FR'); $v = [double]$x; $(if ($v -gt 0) { '+' } elseif ($v -lt 0) { '−' } else { '' }) + ([math]::Abs($v)).ToString('0.##', $fr) + ' %' }
function Get-PhraseVariation($x, [string]$periode) {
    if ([math]::Abs([double]$x) -lt 0.05) { return "Stable $periode." }; if ([double]$x -gt 0) { "En hausse $periode : $(Format-SignePct $x)." } else { "En baisse $periode : $(Format-SignePct $x)." }
}

# ---------- 1) STATUT ----------
function New-EmbedStatut($d) {
    # $d : mode ('actif' | 'sourdine' | 'jeu'), cerveau ('hybride' | 'local' | 'claude'), discord ('connecté' | 'en cours de connexion' | 'inactif'), todo, marche (bool), claude, claude_max
    $soucis = @()
    if ($d.mode -eq 'sourdine') { $soucis += "Jarvis est en sourdine : il n'exécute aucune commande" } elseif ($d.mode -eq 'jeu') { $soucis += 'le mode jeu est actif : Jarvis reste silencieux' }
    if ($d.discord -ne 'connecté') { $soucis += $(if ($d.discord -eq 'inactif') { "Discord n'est pas actif" } else { "Discord n'est pas encore connecté" }) }
    if ([int]$d.claude_max -gt 0 -and [int]$d.claude -ge [math]::Ceiling(0.8 * [int]$d.claude_max)) { $soucis += "le plafond d'appels à Claude approche" }
    $ok = ($soucis.Count -eq 0)
    $desc = $(if ($ok) { "Tout va bien : Jarvis est actif et à votre écoute." } else { 'À surveiller : ' + ($soucis -join ' ; ') + '.' })
    $modeTxt = $(if ($d.mode -eq 'sourdine') { 'En sourdine' } elseif ($d.mode -eq 'jeu') { 'En mode jeu (silencieux)' } else { 'Actif' })
    $cerv = $(switch ($d.cerveau) { 'local' { 'Local (sur ce PC)' } 'claude' { 'Cloud (Claude)' } default { 'Local + cloud' } })
    $disc = $(switch ($d.discord) { 'connecté' { 'Connecté' } 'inactif' { 'Inactif' } default { 'En cours de connexion' } })
    $champs = @(
        @{ nom = ((Get-EmojiModele $(if ($d.mode -eq 'actif') { 'ok' } else { 'alerte' })) + ' Mode'); valeur = $modeTxt; inline = $true },
        @{ nom = ((Get-EmojiModele 'cerveau') + ' Cerveau'); valeur = $cerv; inline = $true },
        @{ nom = ((Get-EmojiModele 'cloche') + ' Discord'); valeur = $disc; inline = $true },
        @{ nom = ((Get-EmojiModele 'note') + ' Tâches'); valeur = (Get-MotNombre ([int]$d.todo) 'tâche ouverte' 'tâches ouvertes' 'Aucune tâche ouverte'); inline = $true },
        @{ nom = ((Get-EmojiModele 'hausse') + ' Veille du marché'); valeur = $(if ($d.marche) { 'Activée' } else { 'Désactivée' }); inline = $true },
        @{ nom = ((Get-EmojiModele 'heure') + " Appels à Claude aujourd'hui"); valeur = ("$([int]$d.claude) sur $([int]$d.claude_max)`n" + (Get-BarreDiscord ([int]$d.claude) ([int]$d.claude_max))); inline = $true })
    New-EmbedDiscord ((Get-EmojiModele 'cerveau') + ' Jarvis · statut') $desc $(if ($ok) { $script:CouleurVerte } else { $script:CouleurOrange }) $champs (Get-PiedDiscord)
}

# ---------- 2) TO-DO ----------
function New-EmbedTodo($taches) {
    $t = @($taches); $ouv = @($t | Where-Object { -not $_.fait }); $fait = @($t | Where-Object { $_.fait })
    if (-not $t.Count) { return (New-EmbedDiscord ((Get-EmojiModele 'note') + ' Tes tâches') 'Aucune tâche pour le moment, monsieur.' $script:CouleurVerte @() (Get-PiedDiscord)) }
    $lignes = @(); $k = 0
    foreach ($x in ($t | Select-Object -First 10)) { $k++; $lignes += "$(if ($x.fait) { Get-EmojiModele 'coche' } else { Get-EmojiModele 'vide' }) $k · $($x.texte)" }
    if ($t.Count -gt 10) { $lignes += "… et $($t.Count - 10) autre$(if ($t.Count - 10 -gt 1) { 's' })" }
    New-EmbedDiscord ((Get-EmojiModele 'note') + ' Tes tâches') ($lignes -join "`n") $(if ($ouv.Count) { $script:CouleurBleue } else { $script:CouleurVerte }) @() ("$(Get-MotNombre $ouv.Count 'ouverte' 'ouvertes' 'Aucune ouverte') · $(Get-MotNombre $fait.Count 'terminée' 'terminées' 'Aucune terminée')")
}

# ---------- 3) MARCHÉ (lecture seule : faits, jamais de conseil) ----------
function New-EmbedMarche($d) {
    # $d : nom, prix, devise, var_jour, var_sem, var_mois (nombres ou $null), source, date (datetime)
    $ref = $(if ($null -ne $d.var_sem) { @($d.var_sem, 'sur la semaine') } elseif ($null -ne $d.var_jour) { @($d.var_jour, "aujourd'hui") } elseif ($null -ne $d.var_mois) { @($d.var_mois, 'sur le mois') } else { $null })
    $couleur = $script:CouleurGrise
    if ($ref) { if ([double]$ref[0] -gt 0.0499) { $couleur = $script:CouleurVerte } elseif ([double]$ref[0] -lt -0.0499) { $couleur = $script:CouleurRouge } }
    $fr = [Globalization.CultureInfo]::GetCultureInfo('fr-FR')
    $champs = @(@{ nom = ((Get-EmojiModele 'heure') + ' Dernier cours'); valeur = ((([double]$d.prix).ToString('0.####', $fr) + " $($d.devise)").Trim()); inline = $true })
    foreach ($p in @(@('var_jour', "Aujourd'hui"), @('var_sem', '1 semaine'), @('var_mois', '1 mois'))) {
        if ($null -ne $d[$p[0]]) { $champs += @{ nom = $p[1]; valeur = (Format-SignePct $d[$p[0]]); inline = $true } }
    }
    $desc = $(if ($ref) { Get-PhraseVariation $ref[0] $ref[1] } else { 'Cours relevé, sans variation disponible.' })
    $pied = "Source : $($d.source) · " + ([datetime]$d.date).ToString('dd/MM')
    New-EmbedDiscord "$($d.nom)" $desc $couleur $champs $pied
}
function New-EmbedMarcheVide([string]$nom, [string]$raison) {
    $que = $(if ($raison -match '(?i)d[ée]sactiv') { 'Mettez « marche_actif » à true dans config.json, puis relancez Jarvis.' } elseif ($raison -match '(?i)cl[ée]|ALPHAVANTAGE') { 'Ajoutez la clé ALPHAVANTAGE_KEY dans le fichier .env, puis relancez Jarvis.' } elseif ($raison -match '(?i)relev') { 'Patientez quelques minutes : la veille du marché fait son premier relevé.' } else { 'Vérifiez « marche_actif » dans config.json et la clé ALPHAVANTAGE_KEY dans .env.' })
    New-EmbedDiscord ((Get-EmojiModele 'alerte') + " Pas de données pour $nom") "Je n'ai pas de cours à vous montrer, et je n'invente rien.`n`nQue faire : $que" $script:CouleurOrange @(@{ nom = 'Pourquoi'; valeur = "$raison"; inline = $false }) (Get-PiedDiscord)
}

# ---------- 4) BRIEFING ----------
function New-EmbedBriefing($lignes, $saas = @(), $marche = @(), $afaire = @(), [string]$titre = 'Briefing') {
    $l = @($lignes | Where-Object { "$_".Trim() } | Select-Object -First 4 | ForEach-Object { "$_".Trim() })
    $champs = @()
    if (@($saas).Count) { $champs += @{ nom = ((Get-EmojiModele 'hausse') + ' SaaS'); valeur = (@($saas | Select-Object -First 4) -join "`n"); inline = $false } }
    if (@($marche).Count) { $champs += @{ nom = ((Get-EmojiModele 'heure') + ' Marché'); valeur = (@($marche | Select-Object -First 3) -join "`n"); inline = $false } }
    if (@($afaire).Count) { $champs += @{ nom = ((Get-EmojiModele 'note') + ' À faire'); valeur = (@($afaire | Select-Object -First 4) -join "`n"); inline = $false } }
    New-EmbedDiscord ((Get-EmojiModele 'soleil') + " $titre") (($l | ForEach-Object { Format-GrasDiscord $_ }) -join "`n`n") $script:CouleurBleue $champs (Get-PiedDiscord)
}

# ---------- 5) INITIATIVES (propositions de Jarvis : barre bleue = normal, rouge = urgent) ----------
function Get-InitiativeLibelleType([string]$t) { switch ($t) { 'rappel' { 'Rappel' } 'suggestion' { 'Suggestion' } 'skill_propose' { 'Nouvelle compétence' } 'maintenance' { 'Entretien' } default { "$t" } } }
function Get-InitiativeLibelleStatut([string]$s) { switch ($s) { 'en_attente' { 'À valider' } 'approuvee' { 'Approuvée' } 'rejetee' { 'Rejetée' } 'plus_tard' { 'Reportée' } 'oubliee' { 'Oubliée' } default { "$s" } } }
function New-EmbedInitiative($i) {
    # $i : id, titre, type, raison, urgence, niveau_autonomie, statut. Une idée par rubrique, la consigne pour répondre en dernier.
    $urgent = ("$($i.urgence)" -eq 'haute')
    $champs = @(
        @{ nom = 'Pourquoi'; valeur = "$($i.raison)"; inline = $false },
        @{ nom = 'Type'; valeur = (Get-InitiativeLibelleType "$($i.type)"); inline = $true },
        @{ nom = 'Urgence'; valeur = $(if ($urgent) { 'Urgente' } else { 'Normale' }); inline = $true },
        @{ nom = 'Statut'; valeur = (Get-InitiativeLibelleStatut "$($i.statut)"); inline = $true })
    if ("$($i.statut)" -in 'en_attente', 'plus_tard', 'oubliee') { $champs += @{ nom = 'Votre réponse'; valeur = "approuver $($i.id)`nrejeter $($i.id)`nplus tard $($i.id)"; inline = $false } }
    New-EmbedDiscord "Initiative n° $($i.id) · $(Get-InitiativeLibelleType "$($i.type)")" "**$($i.titre)**" $(if ($urgent) { $script:CouleurRouge } else { $script:CouleurBleue }) $champs "Rien n'est fait sans votre accord · $(Get-PiedDiscord)"
}
function New-EmbedInitiatives($liste, [int]$oubliees = 0) {
    $l = @($liste)
    if (-not $l.Count) { return (New-EmbedDiscord 'Initiatives' 'Aucune initiative en attente, monsieur.' $script:CouleurBleue @() (Get-PiedDiscord)) }
    $urgent = @($l | Where-Object { "$($_.urgence)" -eq 'haute' -and "$($_.statut)" -eq 'en_attente' }).Count
    $att = @($l | Where-Object { "$($_.statut)" -eq 'en_attente' }); $rep = @($l | Where-Object { "$($_.statut)" -eq 'plus_tard' })
    $fmt = { param($x) "**n° $($x.id)** · $($x.titre)`n$($x.raison)" }
    $champs = @()
    if ($att.Count) { $champs += @{ nom = (Get-MotNombre $att.Count 'initiative à valider' 'initiatives à valider'); valeur = ((@($att | Select-Object -First 5 | ForEach-Object { & $fmt $_ })) -join "`n`n"); inline = $false } }
    if ($rep.Count) { $champs += @{ nom = (Get-MotNombre $rep.Count 'initiative reportée' 'initiatives reportées'); valeur = ((@($rep | Select-Object -First 5 | ForEach-Object { & $fmt $_ })) -join "`n`n"); inline = $false } }
    $champs += @{ nom = 'Votre réponse'; valeur = "approuver <n°> · rejeter <n°> · plus tard <n°>"; inline = $false }
    $desc = $(if ($urgent) { (Get-MotNombre $urgent 'initiative urgente' 'initiatives urgentes') + ' à regarder en premier.' } else { 'Voici ce que je vous propose, monsieur.' })
    $pied = (Get-PiedDiscord); if ($oubliees) { $pied = (Get-MotNombre $oubliees 'initiative oubliée' 'initiatives oubliées') + ' (sans réponse depuis plus de 4 jours) · ' + $pied }
    New-EmbedDiscord 'Initiatives' $desc $(if ($urgent) { $script:CouleurRouge } else { $script:CouleurBleue }) $champs $pied
}

# ---------- 5 bis) LEÇONS ET STYLE DE PAROLE (ce que Jarvis a appris ; barre bleue) ----------
function New-EmbedLecons($liste) {
    $l = @($liste)
    if (-not $l.Count) { return (New-EmbedDiscord 'Leçons apprises' "Je n'ai encore appris aucune leçon, monsieur." $script:CouleurBleue @() (Get-PiedDiscord)) }
    $fmt = { param($x) "**n° $($x.id)** · $($x.regle)`nConfiance $([int][math]::Round([double]$x.confiance * 100)) % · $(Get-MotNombre ([int]$x.confirmations) 'confirmation' 'confirmations')" }
    $groupes = @(@('Règles permanentes', @($l | Where-Object { "$($_.statut)" -eq 'permanente' })), @('Leçons fiables', @($l | Where-Object { "$($_.statut)" -ne 'permanente' -and [double]$_.confiance -ge 0.6 })), @('Leçons en cours', @($l | Where-Object { "$($_.statut)" -ne 'permanente' -and [double]$_.confiance -lt 0.6 })))
    $champs = @(); foreach ($g in $groupes) { if ($g[1].Count) { $champs += @{ nom = "$($g[0]) ($($g[1].Count))"; valeur = ((@($g[1] | Sort-Object { -[double]$_.confiance } | Select-Object -First 4 | ForEach-Object { & $fmt $_ })) -join "`n`n"); inline = $false } } }
    $champs += @{ nom = 'Votre réponse'; valeur = 'oublie la leçon <n°>'; inline = $false }
    New-EmbedDiscord 'Leçons apprises' (Get-MotNombre $l.Count 'leçon retenue' 'leçons retenues' 'Aucune leçon') $script:CouleurBleue $champs (Get-PiedDiscord)
}
function New-EmbedStyle($s) {
    # $s : elements (id, genre, cle, valeur, sens, confirmations), courte, detaillee
    $el = @($s.elements)
    $mots = @($el | Where-Object { "$($_.genre)" -eq 'mot' } | Sort-Object { -[int]$_.confirmations } | Select-Object -First 5 | ForEach-Object { "**n° $($_.id)** · « $($_.cle) » veut dire « $($_.valeur) » ($(Get-MotNombre ([int]$_.confirmations) 'fois' 'fois'))" })
    $tour = @($el | Where-Object { "$($_.genre)" -eq 'tournure' } | Sort-Object { -[int]$_.confirmations } | Select-Object -First 5 | ForEach-Object { "**n° $($_.id)** · « $($_.cle) » : $($_.sens)" })
    $suj = @($el | Where-Object { "$($_.genre)" -eq 'sujet' -and [int]$_.confirmations -ge 2 } | Sort-Object { -[int]$_.confirmations } | Select-Object -First 5 | ForEach-Object { "**n° $($_.id)** · $($_.cle) ($(Get-MotNombre ([int]$_.confirmations) 'fois' 'fois'))" })
    $champs = @(@{ nom = 'Longueur des réponses'; valeur = $(if ([int]$s.detaillee -gt [int]$s.courte) { 'Détaillées' } else { 'Courtes et directes' }); inline = $true })
    if ($mots.Count) { $champs += @{ nom = 'Mots que je corrige'; valeur = ($mots -join "`n"); inline = $false } }
    if ($tour.Count) { $champs += @{ nom = 'Vos tournures'; valeur = ($tour -join "`n"); inline = $false } }
    if ($suj.Count) { $champs += @{ nom = 'Sujets qui reviennent'; valeur = ($suj -join "`n"); inline = $false } }
    $champs += @{ nom = 'Votre réponse'; valeur = 'oublie le style <n°>'; inline = $false }
    New-EmbedDiscord 'Votre façon de parler' $(if ($el.Count) { "Voici ce que j'ai retenu, monsieur." } else { "Je n'ai encore rien appris de votre façon de parler, monsieur." }) $script:CouleurBleue $champs (Get-PiedDiscord)
}

# ---------- 5 ter) SKILLS (liste et rapport de validation ; barre bleue, rouge si le contrôle a échoué) ----------
function New-EmbedSkills($liste) {
    $l = @($liste)
    if (-not $l.Count) { return (New-EmbedDiscord 'Skills' "Aucun skill pour le moment, monsieur. Dites « fais-moi un skill pour … »." $script:CouleurBleue @() (Get-PiedDiscord)) }
    $champs = @()
    foreach ($g in @(@('Actifs', 'actif'), @('Validés, désactivés', 'validé'), @('En quarantaine', 'quarantaine'), @('Refusés ou archivés', 'refusé'))) {
        $x = @($l | Where-Object { $_.etat -eq $g[1] }); if (-not $x.Count) { continue }
        $champs += @{ nom = "$($g[0]) ($($x.Count))"; valeur = ((@($x | Select-Object -First 6 | ForEach-Object { "**$($_.nom)** · $($_.description)$(if ($_.statut -eq 'echec_controle') { ' (contrôle échoué)' })" })) -join "`n"); inline = $false }
    }
    $champs += @{ nom = 'Votre réponse'; valeur = "active <nom>`ndésactive <nom>`nsupprime le skill <nom>"; inline = $false }
    New-EmbedDiscord 'Skills' (Get-MotNombre $l.Count 'skill' 'skills') $script:CouleurBleue $champs (Get-PiedDiscord)
}
function New-EmbedSkillRapport($m, $initiative = $null) {
    # $m : manifeste (nom, description, outils, permission_niveau, controle) ; $initiative : l'initiative de validation (ou $null si le contrôle a échoué)
    $ok = ($m.controle -and $m.controle.statique -and $m.controle.statique.ok -eq $true -and $m.controle.test -and $m.controle.test.ok -eq $true)
    $mot = { param($x) if ($x -and $x.ok -eq $true) { 'OK' } else { 'Échec' } }
    $champs = @(
        @{ nom = 'Ce qu''il fait'; valeur = "$($m.description)"; inline = $false },
        @{ nom = 'Outils prévus'; valeur = (@($m.outils) -join ', '); inline = $true },
        @{ nom = 'Permission'; valeur = "Niveau $($m.permission_niveau)"; inline = $true },
        @{ nom = 'Contrôle statique'; valeur = (& $mot $m.controle.statique); inline = $true },
        @{ nom = 'Test silencieux'; valeur = (& $mot $m.controle.test); inline = $true })
    if (-not $ok) { $champs += @{ nom = 'Motifs'; valeur = ((@(@($m.controle.statique.motifs) + @($m.controle.test.motif) | Where-Object { $_ } | Select-Object -First 4)) -join "`n"); inline = $false } }
    elseif ($initiative) { $champs += @{ nom = 'Votre réponse'; valeur = "approuver $($initiative.id)`nrejeter $($initiative.id)"; inline = $false } }
    New-EmbedDiscord $(if ($ok) { "Skill « $($m.nom) » prêt à valider" } else { "Skill « $($m.nom) » écarté" }) $(if ($ok) { "Rien n'est activé tant que vous n'avez pas validé, puis dit « active $($m.nom) »." } else { 'Le contrôle a échoué : le skill reste en quarantaine, rien n''est activé.' }) $(if ($ok) { $script:CouleurBleue } else { $script:CouleurRouge }) $champs (Get-PiedDiscord)
}

# ---------- 5 quater) PRESETS, VUES ET CAPACITÉS (barre bleue) ----------
function New-EmbedPresets($liste) {
    $l = @($liste)
    if (-not $l.Count) { return (New-EmbedDiscord 'Presets' "Aucun preset pour le moment, monsieur. Dites « crée un preset X avec … »." $script:CouleurBleue @() (Get-PiedDiscord)) }
    $champs = @()
    foreach ($g in @(@('Actifs', 'actif'), @('À valider', 'a_valider'), @('Désactivés', 'desactive'), @('Refusés', 'refuse'))) {
        $x = @($l | Where-Object { "$($_.statut)" -eq $g[1] }); if (-not $x.Count) { continue }
        $champs += @{ nom = "$($g[0]) ($($x.Count))"; valeur = ((@($x | Select-Object -First 6 | ForEach-Object { "**$($_.nom)** · $($_.description)$(if (@($_.declencheurs).Count) { "`nDites : « $($_.declencheurs[0]) »" })" })) -join "`n"); inline = $false }
    }
    $champs += @{ nom = 'Votre réponse'; valeur = "lance le preset <nom>`ndésactive le preset <nom>"; inline = $false }
    New-EmbedDiscord 'Presets' (Get-MotNombre $l.Count 'preset' 'presets') $script:CouleurBleue $champs (Get-PiedDiscord)
}
function New-EmbedPresetRun($preset, $r) {
    # $r : ok, texte, lignes (✓ / ✗ par étape)
    New-EmbedDiscord "Preset « $($preset.nom) »" "$($r.texte)" $(if ($r.ok) { $script:CouleurBleue } else { $script:CouleurOrange }) $(if (@($r.lignes).Count) { @(@{ nom = 'Étapes'; valeur = (@($r.lignes) -join "`n"); inline = $false }) } else { @() }) (Get-PiedDiscord)
}
function New-EmbedVues($liste) {
    $l = @($liste)
    if (-not $l.Count) { return (New-EmbedDiscord 'Vues' 'Aucune vue installée, monsieur.' $script:CouleurBleue @() (Get-PiedDiscord)) }
    $champs = @(foreach ($v in ($l | Select-Object -First 8)) {
        if ($v.ok) { @{ nom = "$($v.vue.nom)"; valeur = "$($v.vue.description)`nDites : « montre $(@($v.vue.declencheurs)[0].phrase) »"; inline = $false } }
        else { @{ nom = "$($v.id) (invalide)"; valeur = "$((@($v.motifs) | Select-Object -First 2) -join ' ; ')"; inline = $false } }
    })
    $champs += @{ nom = 'Votre réponse'; valeur = "montre la vue <nom>`nferme la vue"; inline = $false }
    New-EmbedDiscord 'Vues' (Get-MotNombre $l.Count 'vue installée' 'vues installées') $script:CouleurBleue $champs (Get-PiedDiscord)
}
function New-EmbedCapacites($d) {
    # $d : skills, presets, vues (listes de @{ nom; etat; description }), presets_actif, vues_actif
    $bloc = { param($titre, $l, $actif) $x = @($l); $v = $(if ($x.Count) { (@($x | Select-Object -First 6 | ForEach-Object { "**$($_.nom)** · $($_.etat)" }) -join "`n") } else { 'Aucun.' }); @{ nom = "$titre ($($x.Count))$(if ($actif -eq $false) { ' · désactivés' })"; valeur = $v; inline = $false } }
    $champs = @((& $bloc 'Skills' $d.skills $null), (& $bloc 'Presets' $d.presets $d.presets_actif), (& $bloc 'Vues' $d.vues $d.vues_actif))
    New-EmbedDiscord 'Capacités' "Ce que j'ai installé, monsieur." $script:CouleurBleue $champs (Get-PiedDiscord)
}

# ---------- 6) ERREURS, REFUS ET ALERTES ----------
function New-EmbedProbleme([string]$titre, [string]$phrase, [string]$quoiFaire, [bool]$grave = $true) {
    New-EmbedDiscord ((Get-EmojiModele 'alerte') + " $titre") ("$phrase" + $(if ($quoiFaire) { "`n`nQue faire : $quoiFaire" } else { '' })) $(if ($grave) { $script:CouleurRouge } else { $script:CouleurOrange }) @() (Get-PiedDiscord)
}
function New-EmbedAlerte([string]$phrase, [string]$cle = '', [bool]$grave = $false) {
    $que = $(if ($cle -match '^(marche|seuil):') { "Dites « où en est » suivi du nom de la valeur pour voir le détail." } else { "Regardez ce processus ; dites « liste les alertes » pour le détail." })
    New-EmbedDiscord ((Get-EmojiModele 'alerte') + ' Alerte') "$phrase`n`nQue faire : $que" $(if ($grave) { $script:CouleurRouge } else { $script:CouleurOrange }) @() ((Get-EmojiModele 'cloche') + ' ' + (Get-PiedDiscord))
}
function New-EmbedAlertesGroupees($alertes) {
    $a = @($alertes); $l = @($a | ForEach-Object { "• $($_.texte)" + $(if ([int]$_.n -gt 1) { " (×$($_.n))" } else { '' }) })
    New-EmbedDiscord ((Get-EmojiModele 'cloche') + " Alertes regroupées ($($a.Count))") ($l -join "`n") $script:CouleurOrange @() (Get-PiedDiscord)
}
function Get-MotifErreur { '(?i)erreur|[ée]chec|impossible|n.ai pas pu|injoignable|panne|plantage' }
function ConvertTo-EmbedReponse([string[]]$lignes, [string]$humour = '') {
    # Toute réponse écrite devient une carte : Problème (rouge), Attention (orange), C'est fait (vert) ou Réponse (bleu). Le titre et la couleur portent le sens, aucun emoji.
    $phrase = (@($lignes) | Where-Object { "$_".Trim() }) -join ' '
    if ($phrase -match (Get-MotifErreur)) { return (New-EmbedProbleme 'Problème' $phrase "Réessayez dans un instant ; si cela continue, consultez le journal de Jarvis." $true) }
    if ($phrase -match $script:MotifRefus -or $phrase -match '(?i)compris|reformul') { return (New-EmbedProbleme 'Attention' $phrase "Dites-moi autre chose, ou faites-le directement à votre clavier." $false) }
    $corps = Format-ReponseDiscord $lignes; $nat = Get-NatureDiscord $corps
    if ($nat -eq 'grave' -or $nat -eq 'refus') { return (New-EmbedProbleme 'Attention' $phrase '' $false) }
    if ($humour) { $corps += "`n$humour" }
    if ($nat -eq 'fait') { return (New-EmbedDiscord "C'est fait" $corps $script:CouleurVerte @() (Get-PiedDiscord)) }
    New-EmbedDiscord 'Réponse' $corps $script:CouleurBleue @() (Get-PiedDiscord)
}

# ---------- Aperçu : memoire\apercu-discord.html (données fictives, rien n'est envoyé à Discord) ----------
function ConvertTo-HtmlSur([string]$s) { [Net.WebUtility]::HtmlEncode("$s") }
function ConvertTo-HtmlMarkdown([string]$s) { $h = ConvertTo-HtmlSur $s; $h = [regex]::Replace($h, '\*\*(.+?)\*\*', '<b>$1</b>'); $h = [regex]::Replace($h, '(?<!\w)\*([^*\n]+)\*(?!\w)', '<i>$1</i>'); $h -replace "`r?`n", '<br>' }
function ConvertTo-HtmlEmbed($e) {
    $c = '#{0:X6}' -f [int]$e.couleur
    $h = "<div class='embed' style='border-left:4px solid $c'>"
    if ($e.titre) { $h += "<div class='titre'>$(ConvertTo-HtmlSur $e.titre)</div>" }
    if ($e.description) { $h += "<div class='desc'>$(ConvertTo-HtmlMarkdown $e.description)</div>" }
    if (@($e.champs).Count) { $h += "<div class='champs'>"; foreach ($f in @($e.champs)) { $h += "<div class='champ$(if ($f.inline) { ' inline' })'><div class='nom'>$(ConvertTo-HtmlSur $f.nom)</div><div class='val'>$(ConvertTo-HtmlMarkdown $f.valeur)</div></div>" }; $h += '</div>' }
    if ($e.pied) { $h += "<div class='pied'>$(ConvertTo-HtmlSur $e.pied)</div>" }
    $h + '</div>'
}
function Get-ModelesApercu {
    $now = Get-Date; $dt = $now
    $tl = @(@{ texte = 'Appeler le comptable'; fait = $false }, @{ texte = 'Relancer le fournisseur'; fait = $false }, @{ texte = 'Écrire la page « À propos »'; fait = $false }, @{ texte = 'Publier la vidéo du lundi'; fait = $true })
    $longue = @(1..12 | ForEach-Object { @{ texte = "Tâche d'exemple numéro $_"; fait = ($_ -gt 10) } })
    @(
        @{ nom = '1 · Statut — tout va bien'; embed = (New-EmbedStatut @{ mode = 'actif'; cerveau = 'hybride'; discord = 'connecté'; todo = 4; marche = $true; claude = 3; claude_max = 20 }) },
        @{ nom = '1 · Statut — à surveiller (sourdine, plafond proche)'; embed = (New-EmbedStatut @{ mode = 'sourdine'; cerveau = 'local'; discord = 'en cours de connexion'; todo = 0; marche = $false; claude = 17; claude_max = 20 }) },
        @{ nom = '2 · To-do'; embed = (New-EmbedTodo $tl) },
        @{ nom = '2 · To-do — plus de 10 tâches'; embed = (New-EmbedTodo $longue) },
        @{ nom = '3 · Marché — baisse (fictif)'; embed = (New-EmbedMarche @{ nom = 'Thales'; prix = 150.2; devise = 'EUR'; var_jour = -0.8; var_sem = -3.2; var_mois = 1.1; source = 'Alpha Vantage'; date = $dt }) },
        @{ nom = '3 · Marché — hausse (fictif)'; embed = (New-EmbedMarche @{ nom = 'Société Générale'; prix = 42.35; devise = 'EUR'; var_jour = 1.5; var_sem = $null; var_mois = $null; source = 'Alpha Vantage'; date = $dt }) },
        @{ nom = '3 · Marché — sans données'; embed = (New-EmbedMarcheVide 'Thales' 'la veille du marché est désactivée (marche_actif dans config.json)') },
        @{ nom = '4 · Briefing'; embed = (New-EmbedBriefing @('Bonjour monsieur.', '14 nouveaux quiz depuis hier.', '2 nouveaux abonnés.', 'Le site répond.') @('14 nouveaux quiz (hier : 10)', '2 nouveaux abonnés (hier : 3)') @('Thales : −0,8 % aujourd''hui (Alpha Vantage)') @('4 tâches ouvertes', '☐ Appeler le comptable') 'Briefing du matin') },
        @{ nom = '5 · Confirmation (texte court, sans embed)'; texte = "Mettre le PC en veille, monsieur ?`n(✅ ou ❌, ou répondez « oui » / « non » — 60 s)" },
        @{ nom = '6 · Alerte — seuil de marché'; embed = (New-EmbedAlerte "Thales bouge de plus de 3 % aujourd'hui : en baisse de 3,4 %." 'marche:thales:2026-10-15' $false) },
        @{ nom = '6 · Alerte — processus suspect'; embed = (New-EmbedAlerte 'Un programme inconnu (update.exe) tourne depuis le dossier Téléchargements.' 'menace' $true) },
        @{ nom = '6 · Erreur'; embed = (New-EmbedProbleme 'Problème' "Je n'ai pas pu joindre mon cerveau, monsieur." "Réessayez dans un instant ; si cela continue, consultez le journal de Jarvis." $true) },
        @{ nom = '6 · Refus'; embed = (New-EmbedProbleme 'Attention' 'Cela ne se fait pas depuis Discord, monsieur.' 'Dites-moi autre chose, ou faites-le directement à votre clavier.' $false) },
        @{ nom = '7 · Carte Réponse (bleu)'; embed = (New-EmbedDiscord 'Réponse' 'Le ciel est bleu parce que l''atmosphère diffuse davantage la lumière bleue.' $script:CouleurBleue @() (Get-PiedDiscord)) },
        @{ nom = '7 · Carte C''est fait (vert)'; embed = (New-EmbedDiscord "C'est fait" 'Tâche ajoutée à votre liste : lire un livre.' $script:CouleurVerte @() (Get-PiedDiscord)) },
        @{ nom = '7 · Carte Attention (orange)'; embed = (New-EmbedProbleme 'Attention' 'Votre plafond quotidien d''appels à Claude est presque atteint.' '' $false) },
        @{ nom = '7 · Carte Problème (rouge)'; embed = (New-EmbedProbleme 'Problème' 'Je n''ai pas pu joindre mon cerveau, monsieur.' 'Réessayez dans un instant ; si cela continue, consultez le journal de Jarvis.' $true) }
    )
}
function New-ApercuDiscord {
    # Écrit memoire\apercu-discord.html et retourne son chemin. Aucun envoi, aucun réseau.
    $f = Get-FichierMemoire 'apercu-discord.html'
    $cartes = foreach ($m in (Get-ModelesApercu)) {
        $corps = $(if ($m.embed) { ConvertTo-HtmlEmbed $m.embed } else { "<div class='msg'>$(ConvertTo-HtmlMarkdown $m.texte)</div>" })
        "<section><h2>$(ConvertTo-HtmlSur $m.nom)</h2>$corps</section>"
    }
    $css = "body{background:#313338;color:#dbdee1;font-family:'Segoe UI',Arial,sans-serif;margin:0;padding:24px;max-width:520px}h1{font-size:18px;color:#fff}h2{font-size:12px;color:#949ba4;text-transform:uppercase;letter-spacing:.04em;margin:26px 0 6px}.note{color:#949ba4;font-size:13px}.embed{background:#2b2d31;border-radius:4px;padding:10px 14px 12px;max-width:480px}.titre{font-weight:700;color:#fff;font-size:15px;margin-bottom:4px}.desc{font-size:14px;line-height:1.35;margin:4px 0 8px}.champs{display:flex;flex-wrap:wrap;gap:8px 12px}.champ{flex:1 1 100%}.champ.inline{flex:1 1 30%;min-width:120px}.nom{font-weight:700;font-size:13px;color:#fff}.val{font-size:13px;line-height:1.35}.pied{font-size:12px;color:#949ba4;margin-top:8px}.msg{background:#313338;border:1px dashed #4e5058;padding:8px 12px;border-radius:4px;font-size:14px}"
    $html = "<!doctype html><html lang='fr'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Aperçu Discord</title><style>$css</style></head><body><h1>Aperçu des messages Discord de Jarvis</h1><p class='note'>Données fictives : rien n'est envoyé à Discord. Style actuel (config.json, discord_style) : <b>$(Get-DiscordStyle)</b>.</p>$($cartes -join "`n")</body></html>"
    [IO.File]::WriteAllText($f, $html, [Text.UTF8Encoding]::new($false))
    $f
}
