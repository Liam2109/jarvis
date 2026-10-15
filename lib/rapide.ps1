# Chemin RAPIDE : reconnaissance par mots-clés et motifs, SANS IA, pour les ordres courants (réponse en quelques millisecondes).
# Il produit un plan (dit + actions) exactement comme le cerveau ; les actions passent par Invoke-UneAction, donc par les MÊMES niveaux 1, 2 et 3.
# Un ordre que les règles ne reconnaissent pas avec certitude (application inconnue, heure de rappel illisible...) retourne $null : il passe alors au modèle local, puis à Claude.
# Règles de sûreté : le chemin rapide ne contient AUCUNE action de niveau 2 destructrice (supprimer, déplacer, installer, PowerShell libre) ; seul « oublie tout » (niveau 2, confirmé) y figure.
$script:StartAppsCache = $null

function ConvertTo-OrdreNorm([string]$o) {
    # Minuscules, sans accents, apostrophes et tirets normalisés. La LONGUEUR est conservée : un index trouvé ici vaut aussi dans le texte d'origine.
    $t = $o.ToLowerInvariant().Normalize([Text.NormalizationForm]::FormD) -replace '\p{Mn}', ''
    $t = $t -replace "[’‘`´]", "'" -replace '-', ' '
    if ($t.Length -ne $o.Length) { return $o.ToLowerInvariant() }   # garde-fou : ne jamais décaler les index
    $t
}

$script:MoisFr = @{ janvier = 1; fevrier = 2; mars = 3; avril = 4; mai = 5; juin = 6; juillet = 7; aout = 8; septembre = 9; octobre = 10; novembre = 11; decembre = 12 }
$script:JoursFr = @{ lundi = 1; mardi = 2; mercredi = 3; jeudi = 4; vendredi = 5; samedi = 6; dimanche = 0 }
$script:NombresFr = @{ un = 1; une = 1; deux = 2; trois = 3; quatre = 4; cinq = 5; six = 6; sept = 7; huit = 8; neuf = 9; dix = 10; quinze = 15; vingt = 20; trente = 30 }

function Get-QuandFr([string]$n, [datetime]$now = (Get-Date)) {
    # Cherche une expression de date/heure en français (texte normalisé). Retourne @{ quand; debut; longueur } ou $null. Jamais de devinette.
    $nb = '(\d{1,3}|un|une|deux|trois|quatre|cinq|six|sept|huit|neuf|dix|quinze|vingt|trente)'
    $m = [regex]::Match($n, "\bdans un quart d'heure\b"); if ($m.Success) { return @{ quand = $now.AddMinutes(15); debut = $m.Index; longueur = $m.Length } }
    $m = [regex]::Match($n, "\bdans une demi heure\b"); if ($m.Success) { return @{ quand = $now.AddMinutes(30); debut = $m.Index; longueur = $m.Length } }
    $m = [regex]::Match($n, "\bdans $nb\s*(minutes?|min|heures?|h|jours?|semaines?)\b")
    if ($m.Success) {
        $v = $m.Groups[1].Value; $k = if ($v -match '^\d+$') { [int]$v } else { $script:NombresFr[$v] }; $u = $m.Groups[2].Value
        $d = if ($u -like 'min*') { $now.AddMinutes($k) } elseif ($u -like 'h*') { $now.AddHours($k) } elseif ($u -like 'jour*') { $now.AddDays($k) } else { $now.AddDays(7 * $k) }
        return @{ quand = $d; debut = $m.Index; longueur = $m.Length }
    }
    # jour (facultatif) + heure (facultative)
    $jourRe = "(?<jour>apres demain|demain(?: matin| soir)?|aujourd'hui|ce soir|ce matin|cet apres midi|lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche|(?:le )?(?<num>\d{1,2})(?:er)? (?<mois>janvier|fevrier|mars|avril|mai|juin|juillet|aout|septembre|octobre|novembre|decembre))"
    $heureRe = "(?:(?:a|vers) )?(?<h>\d{1,2})\s*(?:h|heures?|:)\s*(?<mn>\d{2})?"
    $mj = [regex]::Match($n, "\b$jourRe\b"); $mh = [regex]::Match($n, "\b$heureRe\b")
    if (-not $mj.Success -and -not $mh.Success) { return $null }
    $debut = if ($mj.Success -and $mh.Success) { [math]::Min($mj.Index, $mh.Index) } elseif ($mj.Success) { $mj.Index } else { $mh.Index }
    $fin = if ($mj.Success -and $mh.Success) { [math]::Max($mj.Index + $mj.Length, $mh.Index + $mh.Length) } elseif ($mj.Success) { $mj.Index + $mj.Length } else { $mh.Index + $mh.Length }
    $jour = if ($mj.Success) { $mj.Groups['jour'].Value } else { '' }
    $h = -1; $mn = 0
    if ($mh.Success) { $h = [int]$mh.Groups['h'].Value; if ($mh.Groups['mn'].Success) { $mn = [int]$mh.Groups['mn'].Value }; if ($h -gt 23 -or $mn -gt 59) { return $null } }
    $base = $now.Date
    if ($jour -match '^apres demain') { $base = $base.AddDays(2) }
    elseif ($jour -match '^demain') { $base = $base.AddDays(1) }
    elseif ($jour -match '^(aujourd|ce |cet )' -or -not $jour) { }
    elseif ($script:JoursFr.ContainsKey($jour)) { $delta = ($script:JoursFr[$jour] - [int]$now.DayOfWeek + 7) % 7; $base = $base.AddDays($delta) }
    elseif ($mj.Groups['mois'].Success) {
        $y = $now.Year; $d0 = $null
        try { $d0 = Get-Date -Year $y -Month $script:MoisFr[$mj.Groups['mois'].Value] -Day ([int]$mj.Groups['num'].Value) -Hour 0 -Minute 0 -Second 0 -Millisecond 0 } catch { return $null }
        if ($d0.Date -lt $now.Date) { $d0 = $d0.AddYears(1) }
        $base = $d0.Date
    }
    if ($h -lt 0) {   # pas d'heure : moment de la journée si connu, sinon on ne devine pas pour une heure
        if ($jour -match 'matin') { $h = 9 } elseif ($jour -match 'soir') { $h = 19 } elseif ($jour -match 'apres midi') { $h = 15 }
        elseif ($jour -match '^(demain|apres demain|lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)' -or $mj.Groups['mois'].Success) { $h = 9 }
        else { return $null }
    } elseif ($jour -match 'soir|apres midi' -and $h -lt 12) { $h += 12 }
    $q = $base.AddHours($h).AddMinutes($mn)
    if (-not $jour -and $q -le $now) { $q = $q.AddDays(1) }          # « à 9 h » déjà passé aujourd'hui = demain
    elseif ($jour -match '^(aujourd|ce )' -and $q -le $now) { return $null }
    elseif ($script:JoursFr.ContainsKey($jour) -and $q -le $now) { $q = $q.AddDays(7) }
    @{ quand = $q; debut = $debut; longueur = ($fin - $debut) }
}

function Get-StartAppsCache { if (-not $script:StartAppsCache) { $script:StartAppsCache = @(Get-StartApps | Select-Object Name, AppID) }; $script:StartAppsCache }

function Resolve-AppRapide([string]$nom) {
    # Application CONNUE (table de config.json ou menu Démarrer, correspondance exacte ou unique) ; sinon $null -> l'ordre passe au cerveau.
    $n = (ConvertTo-OrdreNorm $nom).Trim()
    if ($n.Length -lt 2) { return $null }
    $e = $Config.apps.PSObject.Properties[$n]; if ($e) { return $nom.Trim() }
    $apps = @(Get-StartAppsCache | Where-Object { (ConvertTo-OrdreNorm $_.Name) -eq $n })
    if ($apps.Count -eq 0 -and $n.Length -ge 4) { $apps = @(Get-StartAppsCache | Where-Object { (ConvertTo-OrdreNorm $_.Name) -like "*$n*" }) }
    if ($apps.Count -eq 1) { return $nom.Trim() }
    $null
}

$script:SitesConnus = @{ youtube = 'https://www.youtube.com'; gmail = 'https://mail.google.com'; google = 'https://www.google.com'; vercel = 'https://vercel.com/dashboard'; stripe = 'https://dashboard.stripe.com'
    supabase = 'https://supabase.com/dashboard'; github = 'https://github.com'; claude = 'https://claude.ai'; 'mon site' = $null; tonproduit = $null; 'trouve ton produit' = $null }

function New-PlanRapide([string]$dit, $actions = @(), [scriptblock]$finaliser = $null, [string]$regle = '') {
    @{ dit = $dit; langue = 'fr'; actions = @($actions); rapide = $true; regle = $regle; finaliser = $finaliser }
}
function Act([string]$type, [hashtable]$p = @{}) { $o = [ordered]@{ type = $type }; foreach ($k in $p.Keys) { $o[$k] = $p[$k] }; [pscustomobject]$o }

# ---------- Les règles ----------
$P = "^(?:jarvis[\s,]+)?(?:s'il (?:te|vous) plait[\s,]+)?(?:(?:peux tu|pourrais tu|veux tu|voudrais tu|tu peux|est ce que tu peux|peux vous|pouvez vous)\s+)?"
$FIN = "(?:[\s,]+(?:s'il (?:te|vous) plait|stp|svp|merci))?[\s.!?]*$"
$script:ReglesRapides = @(
    @{ nom = 'salutation'; re = "^(?:jarvis[\s,]+)?(?<s>bonjour|bonsoir|salut|coucou|hello|hey|bonne nuit)(?: jarvis| monsieur)?$FIN"
       build = { param($m, $o, $n) $h = (Get-Date).Hour; $r = if ($m.Groups['s'].Value -eq 'bonne nuit') { 'Bonne nuit, monsieur.' } elseif ($h -ge 18 -or $h -lt 5) { 'Bonsoir, monsieur.' } else { 'Bonjour, monsieur.' }; New-PlanRapide $r @() $null 'salutation' } }
    @{ nom = 'comment_vas_tu'; re = "$P(?:comment (?:vas|va|allez) (?:tu|vous)|comment tu vas|comment ca va|ca va(?: bien)?|tu vas bien|tout va bien|la forme)$FIN"
       build = { param($m, $o, $n) New-PlanRapide 'Très bien, monsieur, merci. Tout est en ordre de mon côté. Et vous ?' @() $null 'comment_vas_tu' } }
    @{ nom = 'politesse'; re = "^(?:jarvis[\s,]+)?(?<p>merci(?: beaucoup| bien)?|ok|okay|d'accord|parfait|super|tres bien|bien recu|c'est bon|nickel|genial|compris|entendu)(?: jarvis| monsieur)?$FIN"
       build = { param($m, $o, $n) $r = if ($m.Groups['p'].Value -like 'merci*') { Get-Politesse 'merci' } else { Get-Politesse 'calme' }; New-PlanRapide $r @() $null 'politesse' } }
    @{ nom = 'annuler'; re = "^(?:jarvis[\s,]+)?(?:annule(?: tout| ca| cela)?|laisse tomber|oublie ca|non merci|finalement non|stop|arrete ca)$FIN"
       build = { param($m, $o, $n) New-PlanRapide (Get-Politesse 'annulation') @() $null 'annuler' } }
    @{ nom = 'todo_lire_souple'; re = "^(?:jarvis[\s,]+)?(?:(?:normal|normale|alors|bon|et|donc|euh|ben|voila)\s+)?(?:(?:lis|lire|montre|affiche|donne|dis|ouvre)(?: moi)?\s+)?(?:la |ma |mes |les |de ma |de mes )?(?:to ?do|liste de taches|liste des taches|taches ouvertes|taches)$FIN"
       build = { param($m, $o, $n) New-PlanRapide '' @(Act 'todo_lire') { param($r) if ($r[0].donnees) { $l = @($r[0].donnees -split '\r?\n' | Where-Object { $_ }); "Vous avez $($l.Count) tâche$(if ($l.Count -gt 1) { 's' }) : $($l -join ', ')." } else { 'Votre liste de tâches est vide, monsieur.' } } 'todo_lire' } }
    @{ nom = 'heure'; re = "$P(?:quelle heure (?:est il|il est)|il est quelle heure|(?:dis moi |donne moi |donne |dis )?l'heure(?: qu'il est| actuelle)?|quelle est l'heure|c'est quelle heure)$FIN"
       build = { param($m, $o, $n) $t = Get-Date; New-PlanRapide ("Il est {0} heure{1}{2}, monsieur." -f $t.Hour, $(if ($t.Hour -gt 1) { 's' }), $(if ($t.Minute) { " $($t.Minute)" } else { '' })) @() $null 'heure' } }
    @{ nom = 'date'; re = "$P(?:quel jour (?:sommes nous|est on|on est|est ce)(?: aujourd'hui)?|quelle est la date(?: d'aujourd'hui)?|on est le combien|(?:dis moi |donne moi )?la date(?: du jour| d'aujourd'hui)?|date du jour)$FIN"
       build = { param($m, $o, $n) New-PlanRapide ("Nous sommes le " + (Get-Date).ToString('dddd d MMMM yyyy', [Globalization.CultureInfo]::GetCultureInfo('fr-FR')) + ', monsieur.') @() $null 'date' } }
    @{ nom = 'sourdine'; re = "$P(?:(?:passe|mets?|reste|va)(?: toi)?(?: en)? sourdine|sourdine|tais toi|te taire|silence|chut|mutes? toi|te muter|te mettre en sourdine|coupe toi|(?:fais|mets) toi muet|mute)$FIN"
       build = { param($m, $o, $n) New-PlanRapide 'Très bien monsieur, je passe en sourdine.' @(Act 'sourdine') $null 'sourdine' } }
    @{ nom = 'musique_niveau'; re = "$P(?:(?:mets?|regle|met|passe|monte|baisse|change|ajuste)(?: moi)? )?(?:le volume de |le son de |le niveau de )?(?:la )?musique\s+(?:a|au|sur|jusqu'a|jusqu a)\s*(?<v>\d{1,3})\s*(?:%|pour cent|pourcent)?$FIN"
       build = { param($m, $o, $n) New-PlanRapide '' @(Act 'musique' @{ commande = 'niveau'; valeur = [int]$m.Groups['v'].Value }) { param($r) "$($r[0].texte)" } 'musique_niveau' } }
    @{ nom = 'musique'; re = "$P(?:(?<c>baisse|diminue|descends?|reduis)(?: moi)?(?: un peu| un petit peu)? (?:le volume de |le son de )?(?:la )?musique|(?<c>monte|augmente|remonte)(?: moi)?(?: un peu| un petit peu)? (?:le volume de |le son de )?(?:la )?musique|(?<c>coupe|arrete|stoppe|eteins|mets en pause) (?:la )?musique|(?<c>remets?|relance|reactive|rallume|remettez) (?:la )?musique|(?:(?<c>mets|met|passe) (?:la )?musique (?:tres bas|au plus bas|au minimum)|musique (?<c>tres bas))|(?<c>baisse|mets) (?:la )?musique (?<c>tres bas))$FIN"
       build = { param($m, $o, $n)
            $c = $m.Groups['c'].Value
            $cmd = if ($n -match 'tres bas|plus bas|minimum') { 'tres_bas' } elseif ($c -match '^(baisse|diminue|descend|reduis)') { 'baisser' } elseif ($c -match '^(monte|augmente|remonte)') { 'monter' } elseif ($c -match '^(coupe|arrete|stoppe|eteins|mets en pause)') { 'couper' } else { 'remettre' }
            New-PlanRapide '' @(Act 'musique' @{ commande = $cmd }) { param($r) "$($r[0].texte)" } 'musique' } }
    @{ nom = 'alerte_ignorer'; re = "$P(?:ignore|ignorez|oublie|laisse tomber) (?:cette |l |la |l')?alerte$FIN"
       build = { param($m, $o, $n) New-PlanRapide '' @(Act 'alerte_ignorer') { param($r) "$($r[0].texte)" } 'alerte_ignorer' } }
    @{ nom = 'alertes_liste'; re = "$P(?:(?:liste|lis|donne|montre|affiche|dis)(?: moi)? (?:les |mes |toutes les )?alertes|quelles sont les alertes|y a t il des alertes)$FIN"
       build = { param($m, $o, $n) New-PlanRapide '' @(Act 'alertes_liste') { param($r) "$($r[0].texte)" } 'alertes_liste' } }
    @{ nom = 'mode_jeu_off'; re = "$P(?:(?:desactive|arrete|quitte|stoppe|coupe|sors du|fin du|fini le|termine le) (?:le )?mode jeu|mode jeu (?:off|desactive|termine|fini|arrete)|mode ne pas deranger (?:off|desactive)|j['\s]ai fini (?:de jouer|ma partie))$FIN"
       build = { param($m, $o, $n) New-PlanRapide '' @(Act 'mode_jeu' @{ etat = 'off' }) { param($r) "$($r[0].texte)" } 'mode_jeu_off' } }
    @{ nom = 'mode_jeu_on'; re = "$P(?:(?:active|lance|passe en|mets|mets moi en|demarre) (?:le )?mode jeu|mode jeu(?: on| active)?|ne pas deranger|mode ne pas deranger|je lance un jeu|je vais jouer)$FIN"
       build = { param($m, $o, $n) New-PlanRapide '' @(Act 'mode_jeu' @{ etat = 'on' }) { param($r) "$($r[0].texte)" } 'mode_jeu_on' } }
    @{ nom = 'coffre_deverrouiller'; re = "$P(?:deverrouille(?: moi)?|ouvre|rouvre|reouvre|debloque)(?: moi)? (?:le |la fenetre du |la fenetre de |mon )?coffre(?: fort| bitwarden)?$FIN"
       build = { param($m, $o, $n) New-PlanRapide '' @(Act 'bitwarden_deverrouiller') { param($r) "$($r[0].texte)" } 'coffre_deverrouiller' } }
    @{ nom = 'coffre_verrouiller'; re = "$P(?:verrouille|ferme)(?: moi)? (?:le |mon )?coffre(?: fort| bitwarden)?$FIN"
       build = { param($m, $o, $n) New-PlanRapide '' @(Act 'bitwarden_verrouiller') { param($r) "$($r[0].texte)" } 'coffre_verrouiller' } }
    @{ nom = 'coffre_statut'; re = "$P(?:etat du coffre|le coffre est (?:il )?(?:ouvert|verrouille|deverrouille)|coffre ouvert)$FIN"
       build = { param($m, $o, $n) New-PlanRapide '' @(Act 'bitwarden_statut') { param($r) "$($r[0].texte)" } 'coffre_statut' } }
    @{ nom = 'oublie_tout'; re = "$P(?:oublie tout|vide ta memoire|efface ta memoire|efface toute ta memoire)$FIN"
       build = { param($m, $o, $n) New-PlanRapide '' @(Act 'oublie_tout') { param($r) "$($r[0].texte)" } 'oublie_tout' } }
    @{ nom = 'volume_valeur'; re = "$P(?:(?:mets?|regle|met|change|baisse|monte|augmente|diminue)(?: moi)? )?(?:le )?(?:son|volume)(?: sonore)? (?:a|au|jusqu'a|sur)\s*(?<v>\d{1,3})\s*(?:%|pour cent|pourcent)?$FIN"
       build = { param($m, $o, $n) $v = [math]::Min(100, [int]$m.Groups['v'].Value); New-PlanRapide '' @(Act 'volume' @{ niveau = $v }) { param($r) "$($r[0].texte)" } 'volume' } }
    @{ nom = 'volume_relatif'; re = "$P(?<sens>monte|augmente|baisse|diminue)(?: moi)?(?: un peu| un petit peu| beaucoup)? (?:le )?(?:son|volume)$FIN"
       build = { param($m, $o, $n) $d = if ($m.Groups['sens'].Value -in 'monte', 'augmente') { 10 } else { -10 }; if ($n -match 'beaucoup') { $d *= 2 }; New-PlanRapide '' @(Act 'volume' @{ delta = $d }) { param($r) "$($r[0].texte)" } 'volume' } }
    @{ nom = 'volume_muet'; re = "$P(?:(?<mute>coupe|mute|desactive) (?:le )?son|(?<mute>remets?|retablis|reactive|reactives|demute) (?:le )?son)$FIN"
       build = { param($m, $o, $n) $coupe = ($m.Groups['mute'].Value -in 'coupe', 'mute', 'desactive'); New-PlanRapide '' @(Act 'volume' @{ muet = $coupe }) { param($r) "$($r[0].texte)" } 'volume' } }
    @{ nom = 'luminosite'; re = "$P(?:mets?|regle|baisse|monte|change)(?: moi)? (?:la )?luminosite (?:a|au|sur)\s*(?<v>\d{1,3})\s*(?:%|pour cent)?$FIN"
       build = { param($m, $o, $n) New-PlanRapide '' @(Act 'luminosite' @{ niveau = [math]::Min(100, [int]$m.Groups['v'].Value) }) { param($r) "$($r[0].texte)" } 'luminosite' } }
    @{ nom = 'defender'; re = "$P(?:lance|fais|demarre|fais moi)(?: moi)? (?:une )?(?:analyse|scan)(?<t> rapide| complete| complet)? (?:de )?(?:mon pc |de mon ordinateur )?(?:defender|antivirus|windows defender|de securite|antivirale)?$FIN"
       build = { param($m, $o, $n) $t = if ($m.Groups['t'].Value -match 'compl') { 'complete' } else { 'rapide' }; New-PlanRapide '' @(Act 'analyse_defender' @{ mode = $t }) { param($r) "$($r[0].texte)" } 'defender' } }
    @{ nom = 'menaces'; re = "$P(?:y a t il|as tu detecte|detecte(?:s)?|cherche|scanne|verifie)(?: des)? (?:menaces?|virus|processus suspects?|malwares?)(?: sur mon pc)?$FIN"
       build = { param($m, $o, $n) New-PlanRapide '' @(Act 'scanner_menaces') { param($r) if ($r[0].donnees) { "$($r[0].texte) $($r[0].donnees -replace '\r?\n', ' ; ')" } else { "$($r[0].texte)" } } 'menaces' } }
    @{ nom = 'business'; re = "$P(?:(?:donne moi |dis moi )?(?:l'etat|etat) (?:de |du )?(?:mon )?(?:business|saas|activite|boutique)|comment va (?:mon )?(?:business|saas|activite)|combien d'abonnes(?: j'ai)?|(?:quel est )?(?:mon |le )?chiffre d'affaires|combien de quiz(?: commences)?)$FIN"
       build = { param($m, $o, $n) New-PlanRapide '' @(Act 'business_etat') { param($r) "$($r[0].donnees)" } 'business' } }
    @{ nom = 'site_etat'; re = "$P(?:(?:donne moi |dis moi )?l'etat du site|(?:est ce que )?(?:mon |le |ton )?site (?:tonproduit(?: shop)? )?(?:est |marche|fonctionne|repond|est en ligne|est up|tourne|est accessible)(?: bien| en ligne| ok| up)?|tonproduit(?: shop|\.shop)? (?:est|marche|fonctionne|repond)(?: en ligne| ok| up)?)$FIN"
       build = { param($m, $o, $n) New-PlanRapide '' @(Act 'etat_site') { param($r) "$($r[0].texte)" } 'site_etat' } }
    @{ nom = 'pc_etat'; re = "$P(?:(?:donne moi |dis moi |montre moi |affiche )?(?:l'etat|etat) (?:de |du |de mon |de l')?(?:mon )?(?:pc|ordinateur|systeme|machine)|comment (?:va|se porte) (?:mon )?(?:pc|ordinateur)|(?:combien (?:de |d')?|quel(?:le)? (?:est )?(?:la |l')?)(?:memoire|ram|espace disque|espace|disque|batterie|cpu|processeur)(?: reste t il| il reste| libre| utilise| j'ai| est utilise)?(?: sur mon pc)?|(?:quelle est |donne moi )?(?:l'utilisation|la charge) (?:du |de la )?(?:cpu|processeur|memoire|ram))$FIN"
       build = { param($m, $o, $n) New-PlanRapide '' @(Act 'etat_systeme') { param($r) "Voici l'état de votre système, monsieur. $($r[0].donnees)" } 'pc_etat' } }
    @{ nom = 'reseau'; re = "$P(?:suis je connecte(?: a internet)?|internet (?:marche|fonctionne)(?: bien)?|(?:l'etat de |mon )?(?:etat du reseau|reseau|connexion)(?: internet)?(?: marche| fonctionne)?|ai je (?:internet|du reseau))$FIN"
       build = { param($m, $o, $n) New-PlanRapide '' @(Act 'reseau_etat') { param($r) "$($r[0].donnees)" } 'reseau' } }
    @{ nom = 'reste_a_faire'; re = "$P(?:qu'est ce qu'il (?:me )?reste(?: a faire)?|ce qu'il me reste a faire|qu'est ce que j'ai (?:encore )?a faire|reste a faire|que me reste t il a faire|quoi de prevu)$FIN"
       build = { param($m, $o, $n) New-PlanRapide '' @(Act 'reste_a_faire') { param($r) if ($r[0].donnees) { "Voici ce qu'il reste, monsieur. " + ($r[0].donnees -replace '\r?\n', ' ') } else { "$($r[0].texte)" } } 'reste_a_faire' } }
    @{ nom = 'resume_jour'; re = "$P(?:resume(?: moi)? (?:ce qu'on a fait|ce que nous avons fait|la journee|aujourd'hui|ce qu'on a fait aujourd'hui|notre journee)|(?:fais|donne)(?: moi)? (?:un )?(?:resume|bilan) (?:du jour|de la journee|d'aujourd'hui)|resume du jour|bilan de la journee)$FIN"
       build = { param($m, $o, $n) New-PlanRapide '' @(Act 'resume_jour') { param($r) Get-ResumeJourRapide } 'resume_jour' } }
    @{ nom = 'todo_lire'; re = "$P(?:(?:lis|lire|donne|dis|montre|affiche)(?: moi)? (?:ma|mes) (?:to ?do|liste(?: de taches)?|taches)|(?:ma|mes) (?:to ?do|taches)|ai je (?:des )?taches(?: a faire)?|qu'est ce qu'il y a dans ma to ?do)$FIN"
       build = { param($m, $o, $n) New-PlanRapide '' @(Act 'todo_lire') { param($r) if ($r[0].donnees) { $l = @($r[0].donnees -split '\r?\n' | Where-Object { $_ }); "Vous avez $($l.Count) tâche$(if ($l.Count -gt 1) { 's' }) : $($l -join ', ')." } else { 'Votre liste de tâches est vide, monsieur.' } } 'todo_lire' } }
    @{ nom = 'todo_ajouter'; re = "$P(?:(?:ajoute|ajouter|mets?|rajoute|inscris|note)\s+(?<t>.+?)\s+(?:a|dans|sur)\s+(?:ma|mes)\s+(?:to ?do|liste(?: de taches)?|taches)|(?:ajoute|ajouter|rajoute|cree)(?: moi)? (?:la |une )?(?:nouvelle )?tache\s*:?\s*(?<t>.+)|nouvelle tache\s*:?\s*(?<t>.+))$FIN"
       build = { param($m, $o, $n) $g = $m.Groups['t']; $t = $o.Substring($g.Index, $g.Length).Trim(' .!?'); if ($t.Length -lt 2) { return $null }; New-PlanRapide '' @(Act 'todo_ajouter' @{ texte = $t }) { param($r) "$($r[0].texte)" } 'todo_ajouter' } }
    @{ nom = 'todo_fini'; re = "$P(?:j'ai (?:fini|termine|fait)|c'est fait pour|c'est termine pour)\s+(?:la tache\s*:?\s*)?(?<t>.+)"
       build = { param($m, $o, $n) $g = $m.Groups['t']; $t = $o.Substring($g.Index, $g.Length).Trim(' .!?')
            if ($t.Length -lt 3 -or -not (Get-Command Get-TodoOuverte -ErrorAction SilentlyContinue) -or -not @(Get-TodoOuverte | Where-Object { $_ -like "*$t*" }).Count) { return $null }      # seulement si une tâche ouverte correspond
            New-PlanRapide '' @(Act 'todo_terminer' @{ texte = $t }) { param($r) "$($r[0].texte)" } 'todo_fini' } }
    @{ nom = 'todo_terminer'; re = "$P(?:coche|raye|barre|termine|valide)(?: moi)? (?:la )?tache\s*:?\s*(?<t>.+)"
       build = { param($m, $o, $n) $g = $m.Groups['t']; $t = $o.Substring($g.Index, $g.Length).Trim(' .!?'); New-PlanRapide '' @(Act 'todo_terminer' @{ texte = $t }) { param($r) "$($r[0].texte)" } 'todo_terminer' } }
    @{ nom = 'rappel'; re = "^(?=.*\b(?:rappelle moi|rappelles moi|fais moi penser|n'oublie pas de me rappeler|rappelle moi)\b).+$"
       build = { param($m, $o, $n)
            $q = Get-QuandFr $n; if (-not $q) { return $null }
            $o2 = $o.Remove($q.debut, $q.longueur).Trim(); $n2 = $n.Remove($q.debut, $q.longueur).Trim()
            $pre = [regex]::Match($n2, "^(?:jarvis[\s,]+)?(?:s'il (?:te|vous) plait[\s,]+)?(?:(?:peux tu|pourrais tu|veux tu|tu peux)\s+)?(?:n'oublie pas de me rappeler|rappelle moi|rappelles moi|fais moi penser)\s*(?:de |d'|que |qu'|a |pour )?")
            $reste = if ($pre.Success) { $o2.Substring($pre.Length) } else { $o2 }
            $reste = ($reste -replace '\s+', ' ' -replace '^\W+|\W+$', '').Trim()
            $reste = $reste -replace "(?i)^(?:de |d'|que je dois |que |qu'il faut |qu'il faudra )", ''
            if ($reste.Length -lt 2) { return $null }
            $quand = $q.quand
            $hm = "$($quand.Hour) heure$(if ($quand.Hour -gt 1) { 's' })" + $(if ($quand.Minute) { " $($quand.Minute)" } else { '' })
            New-PlanRapide (Get-Politesse 'fait_action' @{ x = "je vous le rappellerai le $($quand.ToString('dd/MM')) à $hm" }) @(Act 'rappel_ajouter' @{ texte = $reste; quand = $quand.ToString('yyyy-MM-dd HH:mm') }) { param($r) if ($r[0].ok) { $null } else { "$($r[0].texte)" } } 'rappel' } }
    @{ nom = 'note'; re = "$P(?:note|noter|notes|retiens|retenir|memorise|memoriser|prends en note|garde en memoire)\s*(?:bien )?(?:que |qu'|ceci ?:? ?|:)?\s*(?<t>.+)"
       build = { param($m, $o, $n) $g = $m.Groups['t']; $t = $o.Substring($g.Index, $g.Length).Trim(' !'); if ($t.Length -lt 2 -or $n.Substring($g.Index) -match "^(?:ma |mes )?(?:to ?do|taches)\b") { return $null }; New-PlanRapide '' @(Act 'note_ajouter' @{ texte = $t }) { param($r) "$($r[0].texte)" } 'note' } }
    @{ nom = 'surveiller_5'; re = "$P(?:(?:quels|quelles) sont |donne moi |dis moi |montre moi |affiche )?(?:les )?(?:5|cinq)(?: valeurs?)? (?:a|qu'il faut|qu il faut|que je dois) (?:regarder|surveiller|suivre)(?: aujourd'hui| ce matin| du jour| maintenant)?$FIN"
       build = { param($m, $o, $n) New-PlanRapide '' @(Act 'surveiller_5') { param($r) "$($r[0].texte)" } 'surveiller_5' } }
    @{ nom = 'priorite'; re = "$P(?:(?:mets?|passe|regle|change)(?: moi)? (?:la |en )?)?(?:mode )?priorite (?:en |a |sur )?(?<n>normale|normal|elevee|eleve|haute|maximum|maximale|max)$FIN"
       build = { param($m, $o, $n) New-PlanRapide '' @(Act 'priorite' @{ niveau = $m.Groups['n'].Value }) { param($r) "$($r[0].texte)" } 'priorite' } }
    @{ nom = 'briefing_details'; re = "$P(?:(?:(?:donne|lis|dis|montre|affiche)(?: moi)? )?(?:les? )?details? (?:du |de mon |de ce )?(?:briefing|point du jour)|(?:le )?briefing (?:detaille|complet|en detail))$FIN"
       build = { param($m, $o, $n) New-PlanRapide '' @(Act 'briefing_details') { param($r) $null } 'briefing_details' } }
    @{ nom = 'briefing_relire'; re = "$P(?:(?:relis|relit|relire|redis|repete|rejoue|refais)(?: moi)? (?:le |mon )?(?:briefing|point du jour)(?: du matin| de ce matin| de la nuit)?|(?:(?:donne|fais|lis|dis)(?: moi)? )?(?:le )?briefing de la nuit|que s'est il passe (?:cette nuit|pendant mon absence))$FIN"
       build = { param($m, $o, $n) New-PlanRapide '' @(Act 'briefing_relire') { param($r) $null } 'briefing_relire' } }
    @{ nom = 'salle_marche'; re = "$P(?:montre|affiche|ouvre|donne|fais)(?: moi)?\s+(?:le |la |les |l')?(?:marche|marches|salle de marche|cours)\s+(?:de |du |des |d'|de la |de l')?(?<v>.+?)$FIN"
       build = { param($m, $o, $n) $g = $m.Groups['v']; $t = $o.Substring($g.Index, $g.Length).Trim(' .!?,'); if ($t.Length -lt 1 -or $t.Length -gt 60) { return $null }
            New-PlanRapide '' @(Act 'salle_marche' @{ nom = $t }) { param($r) "$($r[0].texte)" } 'salle_marche' } }
    @{ nom = 'salle_marche_ouvrir'; re = "$P(?:ouvre|affiche|montre)(?: moi)?\s+(?:la )?salle de marche$FIN"
       build = { param($m, $o, $n) New-PlanRapide '' @(Act 'salle_marche') { param($r) "$($r[0].texte)" } 'salle_marche_ouvrir' } }
    @{ nom = 'salle_marche_fermer'; re = "$P(?:ferme|quitte|cache)(?: moi)?\s+(?:la )?salle de marche$FIN"
       build = { param($m, $o, $n) New-PlanRapide '' @(Act 'salle_marche_fermer') { param($r) "$($r[0].texte)" } 'salle_marche_fermer' } }
    @{ nom = 'salle_marche_ou_en_est'; re = "$P(?:ou en est|ou en sont)\s+(?<v>.+?)$FIN"
       build = { param($m, $o, $n) $g = $m.Groups['v']; $t = $o.Substring($g.Index, $g.Length).Trim(' .!?,'); if ($t.Length -lt 1 -or $t.Length -gt 60 -or -not (Get-Command Get-ValeurMarche -ErrorAction SilentlyContinue) -or -not (Get-ValeurMarche $t)) { return $null }
            New-PlanRapide '' @(Act 'salle_marche' @{ nom = $t }) { param($r) "$($r[0].texte)" } 'salle_marche_ou_en_est' } }
    @{ nom = 'marche_onglets'; re = "$P(?:ouvre|affiche)(?: moi)?\s+(?:le |les |un )?(?:graphique|graphiques|onglets?)(?: en ligne| de marche)?\s+(?:de |du |des |d'|de la |de l')?(?<v>.+?)$FIN"
       build = { param($m, $o, $n) $g = $m.Groups['v']; $t = $o.Substring($g.Index, $g.Length).Trim(' .!?,'); if ($t.Length -lt 1 -or $t.Length -gt 60) { return $null }
            New-PlanRapide '' @(Act 'marche_onglets' @{ nom = $t }) { param($r) "$($r[0].texte)" } 'marche_onglets' } }
    @{ nom = 'marche_resume'; re = "$P(?:quoi de neuf|quelles? (?:sont les )?(?:nouvelles|actualites?)|y a t il du nouveau|du nouveau|que se passe t il|ou en est)(?: sur| dans| a| au| pour)? (?:le |les |la |ma |mes )?(?:marche|marches|bourse|veille|valeurs|economie)$FIN"
       build = { param($m, $o, $n) New-PlanRapide '' @(Act 'marche_resume') { param($r) "$($r[0].texte)" } 'marche_resume' } }
    @{ nom = 'marche_valeur'; re = "$P(?:comment (?:va|vont|se porte|se porte t|se comporte)|ou en est|ou en sont|des nouvelles de|donne moi (?:le )?cours de|quel est le cours de|cours de|quoi de neuf sur)\s+(?<v>.+?)$FIN"
       build = { param($m, $o, $n) $g = $m.Groups['v']; $v = Find-ValeurSuivie ($o.Substring($g.Index, $g.Length)); if (-not $v) { return $null }
            New-PlanRapide '' @(Act 'marche_valeur' @{ nom = $v.nom }) { param($r) "$($r[0].texte)" } 'marche_valeur' } }
    @{ nom = 'veille_ajouter'; re = "$P(?:ajoute|rajoute|ajouter|suis|surveille)\s+(?:l'action |la valeur |le titre |l')?(?<v>.+?)\s+(?:a|dans|de|sur|en)\s+(?:ma |la )?(?:veille|liste de veille|surveillance)$FIN"
       build = { param($m, $o, $n) $g = $m.Groups['v']; $t = $o.Substring($g.Index, $g.Length).Trim(' .!?'); if ($t.Length -lt 2 -or $t.Length -gt 60) { return $null }
            New-PlanRapide '' @(Act 'veille_ajouter' @{ nom = $t }) { param($r) "$($r[0].texte)" } 'veille_ajouter' } }
    @{ nom = 'veille_retirer'; re = "$P(?:retire|enleve|supprime|retirer|enlever)\s+(?:l'action |la valeur |le titre |l')?(?<v>.+?)\s+(?:de|dans|a)\s+(?:ma |la )?(?:veille|liste de veille|surveillance)$FIN"
       build = { param($m, $o, $n) $g = $m.Groups['v']; $t = $o.Substring($g.Index, $g.Length).Trim(' .!?'); if ($t.Length -lt 2 -or $t.Length -gt 60) { return $null }
            New-PlanRapide '' @(Act 'veille_retirer' @{ nom = $t }) { param($r) "$($r[0].texte)" } 'veille_retirer' } }
    @{ nom = 'dossier_valeur'; re = "$P(?:fais|prepare|construis|monte|fabrique|donne)(?: moi)? (?:un |le |mon )?dossier (?:sur|de|pour|d'|a propos de)\s*(?<v>.+?)$FIN"
       build = { param($m, $o, $n) $g = $m.Groups['v']; $t = $o.Substring($g.Index, $g.Length).Trim(' .!?'); if ($t.Length -lt 2 -or $t.Length -gt 60) { return $null }
            New-PlanRapide '' @(Act 'dossier_valeur' @{ noms = @($t) }) { param($r) "$($r[0].texte)" } 'dossier_valeur' } }
    @{ nom = 'dossier_comparer'; re = "$P(?:compare|comparer|compare moi)\s+(?<a>[^\d]{2,30}?)\s+(?:et|avec|vs|versus|contre)\s+(?<b>[^\d]{2,30}?)$FIN"
       build = { param($m, $o, $n) $ga = $m.Groups['a']; $gb = $m.Groups['b']; $a = $o.Substring($ga.Index, $ga.Length).Trim(' .!?'); $b = $o.Substring($gb.Index, $gb.Length).Trim(' .!?')
            if (($a.Split(' ').Count -gt 3) -or ($b.Split(' ').Count -gt 3)) { return $null }
            New-PlanRapide '' @(Act 'dossier_valeur' @{ noms = @($a, $b) }) { param($r) "$($r[0].texte)" } 'dossier_comparer' } }
    @{ nom = 'position_noter'; re = "$P(?:j'ai|je viens de) (?:pris|achete|acquis)\s+(?:des |du |de la |l'action |l'|le |la |les )?(?<v>.+?)\s+a\s+(?<p>\d+(?:[.,]\d+)?)\s*(?:euros?|€)?[\s,;.]*(?:et )?(?:previens|prevenez|alerte|avertis)(?: moi)?(?: a| des| quand (?:il|ca|le cours) (?:atteint|arrive a|passe a))?\s+(?<s>\d+(?:[.,]\d+)?)\s*(?:euros?|€)?$FIN"
       build = { param($m, $o, $n) $g = $m.Groups['v']; $t = $o.Substring($g.Index, $g.Length).Trim(' .!?')
            New-PlanRapide '' @(Act 'position_noter' @{ nom = $t; prix = (ConvertTo-NombreFr $m.Groups['p'].Value); seuil = (ConvertTo-NombreFr $m.Groups['s'].Value) }) { param($r) "$($r[0].texte)" } 'position_noter' } }
    @{ nom = 'briefing'; re = "$P(?:(?:fais|donne|lance)(?: moi)? (?:le |un |mon )?(?:briefing|point du jour)|briefing|(?:le )?point du jour)$FIN"
       build = { param($m, $o, $n) New-PlanRapide '' @(Act 'briefing_dire') { param($r) $null } 'briefing' } }
    @{ nom = 'youtube'; re = "$P(?:mets?|lance|joue|cherche|recherche)(?: moi)?\s+(?<q>.+?)\s+sur youtube$FIN"
       build = { param($m, $o, $n) $g = $m.Groups['q']; $q = $o.Substring($g.Index, $g.Length).Trim(' .!?,'); if ($q.Length -lt 2 -or $q.Length -gt 100) { return $null }
            New-PlanRapide '' @(Act 'ouvrir_site' @{ url = ('https://www.youtube.com/results?search_query=' + [uri]::EscapeDataString($q)) }) ({ param($r) if ($r[0].ok) { Get-Politesse 'fait_action' @{ x = "j'ouvre les résultats pour $q" } } else { "$($r[0].texte)" } }.GetNewClosure()) 'youtube' } }
    @{ nom = 'pc_dossier'; re = "$P(?:ouvre|ouvrir|affiche|montre)(?: moi)? (?:le |mon |mes |l')?(?:dossier|repertoire) (?:des |de |du |d')?(?<d>.+)$FIN"
       build = { param($m, $o, $n) $g = $m.Groups['d']; New-PlanRapide '' @(Act 'pc_dossier' @{ nom = $o.Substring($g.Index, $g.Length).Trim(' .!?') }) { param($r) "$($r[0].texte)" } 'pc_dossier' } }
    @{ nom = 'pc_trouver_fichier'; re = "$P(?:trouve|cherche|retrouve)(?: moi)? (?:le |un |mon |ce )?(?:fichier|document) (?:qui s'appelle |nomme |appele )?(?<f>.+)$FIN"
       build = { param($m, $o, $n) $g = $m.Groups['f']; $t = $o.Substring($g.Index, $g.Length).Trim(' .!?'); if ($t.Length -lt 2) { return $null }; New-PlanRapide '' @(Act 'pc_trouver_fichier' @{ nom = $t }) { param($r) "$($r[0].texte)" } 'pc_trouver_fichier' } }
    @{ nom = 'pc_fenetre'; re = "$P(?:mets?|place|deplace|colle|met)(?: moi)? (?:la fenetre de |l'application |l'appli )?(?<a>.+?)\s+(?:(?:a|sur la|au|vers la) (?<p>gauche|droite)|en (?<p>plein ecran)|(?<p>plein ecran)|sur l'ecran (?:de |a |du )?(?<e>droite|gauche|principal))$FIN"
       build = { param($m, $o, $n) $g = $m.Groups['a']; $nom = $o.Substring($g.Index, $g.Length).Trim(' .!?'); if ((ConvertTo-OrdreNorm $nom) -match '\b(et|puis|gauche|droite)\b') { return $null }
            $mode = if ($m.Groups['e'].Success) { 'ecran' } elseif ($m.Groups['p'].Value -match 'plein') { 'plein' } else { $m.Groups['p'].Value }
            New-PlanRapide '' @(Act 'pc_fenetre' @{ nom = $nom; mode = $mode; ecran = $m.Groups['e'].Value }) { param($r) "$($r[0].texte)" } 'pc_fenetre' } }
    @{ nom = 'pc_reduire_tout'; re = "$P(?:reduis|minimise|cache|range)(?: moi)? (?:tout|toutes (?:les|mes) fenetres)$FIN"
       build = { param($m, $o, $n) New-PlanRapide '' @(Act 'pc_reduire_tout') { param($r) "$($r[0].texte)" } 'pc_reduire_tout' } }
    @{ nom = 'pc_media_pause'; re = "$P(?:mets? (?:en )?pause|pause|play|reprends(?: la lecture)?|lecture|stop la lecture)$FIN"
       build = { param($m, $o, $n) New-PlanRapide '' @(Act 'pc_media' @{ touche = 'pause' }) { param($r) "$($r[0].texte)" } 'pc_media' } }
    @{ nom = 'pc_media_suivant'; re = "$P(?:(?:piste |titre |morceau |chanson |musique )?suivant(?:e)?|passe (?:au|a la) (?:suivant|suivante|prochain(?:e)?)|next)$FIN"
       build = { param($m, $o, $n) New-PlanRapide '' @(Act 'pc_media' @{ touche = 'suivant' }) { param($r) "$($r[0].texte)" } 'pc_media' } }
    @{ nom = 'pc_media_precedent'; re = "$P(?:(?:piste |titre |morceau |chanson |musique )?precedent(?:e)?|reviens (?:au|a la) (?:precedent|precedente)|previous)$FIN"
       build = { param($m, $o, $n) New-PlanRapide '' @(Act 'pc_media' @{ touche = 'precedent' }) { param($r) "$($r[0].texte)" } 'pc_media' } }
    @{ nom = 'pc_capture'; re = "$P(?:fais|prends|fais moi|prends moi|realise)?\s*(?:une |un )?capture(?: d'ecran| de l'ecran)?$FIN"
       build = { param($m, $o, $n) New-PlanRapide '' @(Act 'pc_capture') { param($r) "$($r[0].texte)" } 'pc_capture' } }
    @{ nom = 'pc_verrouiller'; re = "$P(?:verrouille|bloque)(?: moi)?(?: le| mon| ma)? (?:pc|ordinateur|session|ecran)$FIN"
       build = { param($m, $o, $n) New-PlanRapide '' @(Act 'pc_verrouiller') { param($r) "$($r[0].texte)" } 'pc_verrouiller' } }
    @{ nom = 'pc_redemarrer'; re = "$P(?:redemarre|redemarrer|reboot)(?: le| mon)?(?: pc| ordinateur)?$FIN"
       build = { param($m, $o, $n) New-PlanRapide '' @(Act 'pc_redemarrer') { param($r) "$($r[0].texte)" } 'pc_redemarrer' } }
    @{ nom = 'pc_veille'; re = "$P(?:mets? )?(?:le |mon )?(?:pc |ordinateur )?en veille$FIN"
       build = { param($m, $o, $n) New-PlanRapide '' @(Act 'pc_veille') { param($r) "$($r[0].texte)" } 'pc_veille' } }
    @{ nom = 'pc_eteindre'; re = "$P(?:eteins|eteindre|arrete)(?: moi)?(?: le| mon) (?:pc|ordinateur)$FIN"
       build = { param($m, $o, $n) New-PlanRapide '' @(Act 'pc_eteindre') { param($r) "$($r[0].texte)" } 'pc_eteindre' } }
    @{ nom = 'pc_annuler_arret'; re = "$P(?:annule|annuler|stoppe)(?: moi)? (?:l'|le )?(?:extinction|arret|redemarrage)$FIN"
       build = { param($m, $o, $n) New-PlanRapide '' @(Act 'pc_annuler_arret') { param($r) "$($r[0].texte)" } 'pc_annuler_arret' } }
    @{ nom = 'winget_choisir'; re = "$P(?:oui )?installe(?: moi)? (?:le |l'|la )?(?:numero |option |choix |proposition )?(?<n>1|2|3|un|deux|trois|premier|deuxieme|troisieme)$FIN"
       build = { param($m, $o, $n) $v = switch -Regex ($m.Groups['n'].Value) { '^(1|un|premier)$' { 1 } '^(2|deux|deuxieme)$' { 2 } default { 3 } }; New-PlanRapide '' @(Act 'winget_installer' @{ numero = $v }) { param($r) "$($r[0].texte)" } 'winget_installer' } }
    @{ nom = 'winget_proposer'; re = "$P(?:j'ai besoin d'(?:une |un )?(?:application|appli|logiciel|programme)(?: pour| de| qui)?\s+(?<q>.+)|(?:installe|telecharge)(?: moi)? (?:une |un |l'|le |la )?(?:application |appli |logiciel |programme )?(?<q>.+)|propose(?: moi)? (?:une |un )?(?:application|appli|logiciel|programme) (?:pour|de) (?<q>.+))$FIN"
       build = { param($m, $o, $n) $g = $m.Groups['q']; $q = $o.Substring($g.Index, $g.Length).Trim(' .!?'); New-PlanRapide '' @(Act 'winget_proposer' @{ requete = $q }) { param($r) "$($r[0].texte)" } 'winget_proposer' } }
    @{ nom = 'disposition_enregistrer'; re = "$P(?:enregistre|sauvegarde|conserve)(?: moi)? (?:cette |la |ma |mon |l')?(?:disposition|organisation|bureau|agencement)(?: actuelle| actuel| de mon bureau| de mes fenetres| des fenetres)?$FIN"
       build = { param($m, $o, $n) New-PlanRapide '' @(Act 'disposition_enregistrer') { param($r) "$($r[0].texte)" } 'disposition_enregistrer' } }
    @{ nom = 'disposition_restaurer'; re = "$P(?:remets?|retablis|restaure|rouvre|reinstalle)(?: moi)? (?:mon |le |ma |mes |les |la )?(?:bureau|disposition|fenetres|espace de travail)(?: comme (?:avant|tout a l'heure|hier|la derniere fois|je les avais|il etait)| en place| comme avant)?$FIN"
       build = { param($m, $o, $n) New-PlanRapide '' @(Act 'disposition_restaurer') { param($r) "$($r[0].texte)" } 'disposition_restaurer' } }
    @{ nom = 'mode_pc'; re = "$P(?:(?:active|lance|passe en|passe au|mets|mets moi en|demarre|bascule en|bascule sur)(?: moi)? )?(?:le )?mode (?<m>[a-z]+)$FIN"
       build = { param($m, $o, $n) $md = Get-ModePc $m.Groups['m'].Value; if (-not $md) { return $null }; New-PlanRapide '' @(Act 'mode_pc' @{ nom = $md.nom }) { param($r) "$($r[0].texte)" } 'mode_pc' } }
    @{ nom = 'minuteur'; re = "$P(?:(?:mets?|lance|programme|demarre|regle|fais)(?: moi)? )?(?:un |le )?minuteur (?:de |pour |d')?(?<v>\d{1,3}|un|une|deux|trois|quatre|cinq|six|sept|huit|neuf|dix|quinze|vingt|trente)\s*(?<u>minutes?|min|heures?|h)$FIN"
       build = { param($m, $o, $n) $v = $m.Groups['v'].Value; $k = if ($v -match '^\d+$') { [int]$v } else { $script:NombresFr[$v] }; if (-not $k) { return $null }
            $unite = if ($m.Groups['u'].Value -like 'h*') { 'heure' } else { 'minute' }; $min = if ($unite -eq 'heure') { 60 * $k } else { $k }; if ($min -lt 1 -or $min -gt 1440) { return $null }
            $quand = (Get-Date).AddMinutes($min); $lib = "$k $unite$(if ($k -gt 1) { 's' })"
            New-PlanRapide (Get-Politesse 'fait_action' @{ x = "minuteur de $lib lancé" }) @(Act 'rappel_ajouter' @{ texte = "votre minuteur de $lib est terminé"; quand = $quand.ToString('yyyy-MM-dd HH:mm') }) { param($r) if ($r[0].ok) { $null } else { "$($r[0].texte)" } } 'minuteur' } }
    @{ nom = 'resume_presse_papiers'; re = "$P(?:resume|resumes|synthetise|resumer)(?: moi)? (?:le contenu de |ce qu'il y a dans |ce que j'ai dans )?(?:mon |le |ma )?(?:presse papiers?|clipboard|texte copie|ce que j'ai copie)$FIN"
       build = { param($m, $o, $n) New-PlanRapide '' @(Act 'resume_contenu' @{ source = 'presse_papiers' }) { param($r) if (-not @($r).Count -or -not $r[0].donnees) { return $null }; $rep = Get-ReponseOrale 'Résume en deux phrases courtes le texte que Liam vient de copier.' "$($r[0].donnees)"; if ($rep) { $rep } else { Get-Politesse 'refus' @{ raison = "je n'ai pas pu joindre mon cerveau" } } } 'resume_presse_papiers' } }
    @{ nom = 'resume_ecran'; re = "$P(?:resume|resumes|decris|resumer)(?: moi)? (?:ce qu'il y a sur |ce qui est ouvert sur |ce qui est sur )?(?:mon |l')?ecran$FIN"
       build = { param($m, $o, $n) New-PlanRapide '' @(Act 'resume_contenu' @{ source = 'ecran' }) { param($r) if (-not @($r).Count -or -not $r[0].donnees) { return $null }; $rep = Get-ReponseOrale 'Dis en deux phrases courtes ce que Liam a ouvert sur son PC, d''après ces titres de fenêtres.' "$($r[0].donnees)"; if ($rep) { $rep } else { Get-Politesse 'refus' @{ raison = "je n'ai pas pu joindre mon cerveau" } } } 'resume_ecran' } }
    @{ nom = 'claude_code'; re = "$P(?:demande|dis|prepare une demande)\s+(?:a )?claude code\s+(?:de |d'|pour |que |qu')?(?<t>.+?)$FIN"
       build = { param($m, $o, $n) $g = $m.Groups['t']; $t = $o.Substring($g.Index, $g.Length).Trim(' .!?,'); if ($t.Length -lt 3) { return $null }
            New-PlanRapide '' @(Act 'claude_code_demander' @{ demande = $t }) { param($r) "$($r[0].texte)" } 'claude_code' } }
    @{ nom = 'capacites_suite'; re = "$P(?:la suite|dis moi en plus|dis m'en plus|d'autres commandes|quoi d'autre|et quoi d'autre|continue la liste|encore des commandes)$FIN"
       build = { param($m, $o, $n) New-PlanRapide '' @(Act 'capacites' @{ suite = $true }) { param($r) "$($r[0].texte)" } 'capacites_suite' } }
    @{ nom = 'capacites'; re = "$P(?:qu'est ce que tu sais faire|que sais tu faire|qu'est ce que tu peux faire|quelles sont tes commandes|liste (?:tes|des) commandes|aide moi|aide|que peux tu faire)$FIN"
       build = { param($m, $o, $n) New-PlanRapide '' @(Act 'capacites') { param($r) "$($r[0].texte)" } 'capacites' } }
    @{ nom = 'dossier'; re = "$P(?:ouvre|ouvrir|affiche|montre)(?: moi)? (?:le |mon |mes |l')?(?:dossier |repertoire )?(?<d>documents?|telechargements?|bureau|images?|photos?|musique|videos?)$FIN"
       build = { param($m, $o, $n) $d = $m.Groups['d'].Value; $chemin = switch -Regex ($d) { '^document' { [Environment]::GetFolderPath('MyDocuments') } '^telechargement' { Join-Path $env:USERPROFILE 'Downloads' } '^bureau' { [Environment]::GetFolderPath('Desktop') } '^(image|photo)' { [Environment]::GetFolderPath('MyPictures') } '^musique' { [Environment]::GetFolderPath('MyMusic') } '^video' { [Environment]::GetFolderPath('MyVideos') } }
            New-PlanRapide '' @(Act 'ouvrir_chemin' @{ chemin = $chemin }) ({ param($r) if ($r[0].ok) { Get-Politesse 'fait_action' @{ x = "j'ouvre le dossier $d" } } else { Get-Politesse 'refus' @{ raison = "je n'ai pas pu ouvrir le dossier" } } }.GetNewClosure()) 'dossier' } }
    @{ nom = 'site'; re = "$P(?:ouvre|ouvrir|va sur|affiche|lance)(?: moi)? (?:le site |la page |le |mon |l'adresse )?(?<s>(?:[a-z0-9-]+\.)+[a-z]{2,}(?:/\S*)?|youtube|gmail|google|vercel|stripe|supabase|github|claude|mon site|tonproduit|trouve ton produit)$FIN"
       build = { param($m, $o, $n) $g = $m.Groups['s']; $s = $n.Substring($g.Index, $g.Length)
            $url = if ($s -in 'mon site', 'tonproduit', 'trouve ton produit') { "$($Config.site)" } elseif ($script:SitesConnus.ContainsKey($s) -and $script:SitesConnus[$s]) { $script:SitesConnus[$s] } else { $o.Substring($g.Index, $g.Length) }
            New-PlanRapide '' @(Act 'ouvrir_site' @{ url = $url }) { param($r) if ($r[0].ok) { Get-Politesse 'fait_action' @{ x = "j'ouvre le site" } } else { Get-Politesse 'refus' @{ raison = "adresse invalide" } } } 'site' } }
    @{ nom = 'pc_devant'; re = "$P(?:passe|bascule|va|reviens|mets le focus)\s+(?:sur|a|vers)\s+(?:l'application |l'appli |la fenetre de )?(?<a>.+)$FIN"
       build = { param($m, $o, $n) $g = $m.Groups['a']; $nom = $o.Substring($g.Index, $g.Length).Trim(' .!?'); if ($nom.Length -lt 2 -or $nom.Split(' ').Count -gt 4) { return $null }
            New-PlanRapide '' @(Act 'pc_fenetre' @{ nom = $nom; mode = 'devant'; ecran = '' }) { param($r) "$($r[0].texte)" } 'pc_devant' } }
    @{ nom = 'app_ouvrir'; re = "$P(?:ouvre|ouvrir|lance|lancer|demarre|demarrer)(?: moi)? (?:l'|le |la |les |un |une |mon |ma |mes )?(?:application |appli |programme |logiciel )?(?:(?:page|fenetre|onglet|session) )?(?:de |d')?(?<a>.+?)$FIN"
       build = { param($m, $o, $n) $g = $m.Groups['a']; $nom = $o.Substring($g.Index, $g.Length).Trim(' .!?'); if ($nom.Length -lt 2 -or $nom.Split(' ').Count -gt 5 -or (ConvertTo-OrdreNorm $nom) -match '\b(et|puis|ensuite|apres|avec|dans|pour|qui|que|ou|dis|moi)\b') { return $null }      # phrase composée : le cerveau s'en charge
            $r = if (Get-Command Resolve-AppPc -ErrorAction SilentlyContinue) { Resolve-AppPc $nom } else { $x = Resolve-AppRapide $nom; @{ ok = $x -ne $null; nom = $x } }
            if ($r.ok -and $r.site) { return (New-PlanRapide '' @(Act 'ouvrir_site' @{ url = $r.site }) { param($res) if ($res[0].ok) { Get-Politesse 'fait_action' @{ x = "j'ouvre le site" } } else { Get-Politesse 'refus' @{ raison = 'adresse invalide' } } } 'app_ouvrir') }
            if (-not $r.ok) { $pl = New-PlanRapide (Get-RefusApp $r $nom) @() $null 'app_ouvrir'; if (-not $r.interdit) { $pl.repli_routeur = $true }; return $pl }
            New-PlanRapide '' @(Act 'ouvrir_app' @{ nom = $r.nom }) ({ param($res) if ($res[0].ok) { Get-Politesse 'fait_action' @{ x = "j'ouvre $nom" } } else { Get-Politesse 'refus' @{ raison = "je n'ai pas pu l'ouvrir" } } }.GetNewClosure()) 'app_ouvrir' } }
    @{ nom = 'app_fermer'; re = "$P(?:ferme|fermer|quitte|quitter)(?: moi)? (?:l'|le |la |les |mon |ma )?(?:application |appli |programme |logiciel |fenetre de |fenetre )?(?:de |d')?(?<a>.+?)$FIN"
       build = { param($m, $o, $n) $g = $m.Groups['a']; $nom = $o.Substring($g.Index, $g.Length).Trim(' .!?'); if ((ConvertTo-OrdreNorm $nom) -match '^(tout|ca|cela|ceci|toi|jarvis|guide|le guide|la conversation|le tableau|tableau|le coffre|coffre|la fenetre|cette fenetre|fenetre)$') { return $null }
            if ($nom.Length -lt 2 -or $nom.Split(' ').Count -gt 5 -or (ConvertTo-OrdreNorm $nom) -match '\b(et|puis|ensuite|apres|avec|dans|pour|qui|que|ou|dis|moi)\b') { return $null }
            $r = if (Get-Command Resolve-AppPc -ErrorAction SilentlyContinue) { Resolve-AppPc $nom } else { $x = Resolve-AppRapide $nom; @{ ok = $x -ne $null; nom = $x } }
            if (-not $r.ok -or $r.site) { $pl = New-PlanRapide (Get-RefusApp $r $nom) @() $null 'app_fermer'; if (-not $r.interdit) { $pl.repli_routeur = $true }; return $pl }
            New-PlanRapide '' @(Act $(if (Get-Command Resolve-AppPc -ErrorAction SilentlyContinue) { 'pc_fermer' } else { 'fermer_app' }) @{ nom = $r.nom }) { param($res) if ($res[0].ok) { "$($res[0].texte)" } else { "$($res[0].texte)" } } 'app_fermer' } }
)

function Test-OrdreControlePc([string]$ordre) {
    # $true si la phrase est une COMMANDE de contrôle du PC (ouvrir, fermer, volume, musique, fenêtres...) : elle ne doit jamais partir chez Claude.
    # Les questions ouvertes (pourquoi, comment, explique, résume...) restent pour Claude.
    if ($script:GardeControlePcDesactivee -eq $true) { return $false }      # crochet des tests du cerveau seulement (ils vérifient la mécanique Claude / local avec des phrases de commande)
    $n = (ConvertTo-OrdreNorm "$ordre").Trim() -replace '^(?:jarvis[\s,]+)+', ''
    if (-not $n -or @($n -split '\s+').Count -gt 12) { return $false }
    if ($n -match '\b(pourquoi|comment|explique|raconte|ecris|redige|traduis|resume|idee|conseil|que penses|ton avis|c.est quoi|qu.est.ce que)\b') { return $false }
    [bool]($n -match '^(?:s.il (?:te|vous) plait\s+)?(?:(?:peux tu|pourrais tu|tu peux|veux tu)\s+)?(?:ouvre|ouvrir|ferme|fermer|quitte|lance|demarre|mets|met|place|deplace|reduis|minimise|passe|bascule|monte|baisse|coupe|remets|augmente|diminue|verrouille|eteins|redemarre|volume|son|musique|pause|suivant|precedent|luminosite)\b')
}

function Get-ResumeJourRapide {
    # Résumé SANS IA : uniquement ce qui figure dans la conversation du jour et dans les résumés écrits aujourd'hui.
    $faits = @()
    if (Get-Command Get-Mem -ErrorAction SilentlyContinue) {
        $auj = Get-Date -Format 'yyyy-MM-dd'
        foreach ($b in @(Get-BlocsConversation | Where-Object { $_.date -eq $auj })) { $faits += Get-PucesSection $b.texte 'Fait' }
        $faits += @($script:Conversation.ToArray() | Where-Object { $_.role -eq 'action' -and $_.texte -notmatch '^(Refusé|Échec|Demande de confirmation|Annulé|Non exécuté)' } | ForEach-Object { $_.texte })
    }
    $faits = @($faits | Select-Object -Unique | Select-Object -First 8)
    if (-not $faits.Count) { return "Je n'ai rien noté de particulier aujourd'hui, monsieur." }
    "Aujourd'hui, nous avons : " + ($faits -join ' ; ') + '.'
}

$script:MotsNombres = @{ zero = 0; un = 1; une = 1; deux = 2; trois = 3; quatre = 4; cinq = 5; six = 6; sept = 7; huit = 8; neuf = 9; dix = 10; onze = 11; douze = 12; treize = 13; quatorze = 14; quinze = 15; seize = 16; vingt = 20; vingts = 20; trente = 30; quarante = 40; cinquante = 50; soixante = 60 }
function ConvertTo-ChiffresFr([string]$o) {
    # « à trente », « à soixante-dix », « à quatre-vingt-dix », « à cent » -> « à 30 » ... (0 à 100 seulement, derrière à / au / sur / de / jusqu'à). « pour cent » n'est jamais touché.
    $mot = '(?:z[ée]ro|une?|deux|trois|quatre|cinq|six|sept|huit|neuf|dix|onze|douze|treize|quatorze|quinze|seize|vingts?|trente|quarante|cinquante|soixante|cent)'
    [regex]::Replace($o, "(?i)\b(?<pre>à|au|sur|jusqu'à|jusqu'a)\s+(?<seq>$mot(?:(?:[\s-]+et)?[\s-]+$mot){0,3})\b", [Text.RegularExpressions.MatchEvaluator]{
        param($m)
        $toks = @($m.Groups['seq'].Value.ToLowerInvariant().Normalize([Text.NormalizationForm]::FormD) -replace '\p{Mn}', '' -split '[\s-]+' | Where-Object { $_ -and $_ -ne 'et' })
        $tot = 0; $prev = ''
        foreach ($t in $toks) {
            if ($t -eq 'cent') { if ($tot -ne 0) { return $m.Value }; $tot = 100 }
            elseif ($t -in 'vingt', 'vingts' -and $prev -eq 'quatre') { $tot = $tot - 4 + 80 }
            elseif ($script:MotsNombres.ContainsKey($t)) { $tot += $script:MotsNombres[$t] }
            else { return $m.Value }
            $prev = $t
        }
        if ($tot -gt 100) { return $m.Value }
        "$($m.Groups['pre'].Value) $tot"
    })
}
function Resolve-VariantesOrdre([string]$o) {
    $o = ConvertTo-ChiffresFr $o
    # Mots anglais ou phonétiques ramenés à la forme que connaissent les règles : « to-do list », « todo », « to do », « tou dou », « ma liste » -> « to-do » ; « screenshot » -> « capture d'écran »...
    $o = $o -replace '(?i)\bto[\s-]?do[\s-]?list\b|\btou[\s-]?dou[xs]?(?:[\s-]?list[e]?)?\b|\bto[\s-]?do\b|\btodo\b|\bt[oe][\s-]?dou\b', 'to-do'
    $o = $o -replace '(?i)\bma liste(?! de)\b', 'ma to-do'
    $o = $o -replace '(?i)\bscreen[\s-]?shot\b', "capture d'écran"
    $o
}
function Get-PlanRapide([string]$ordre) {
    # Retourne un plan, ou $null si aucune règle ne reconnaît l'ordre AVEC CERTITUDE.
    if ($null -ne $Config.chemin_rapide -and $Config.chemin_rapide -eq $false) { return $null }
    $o = Resolve-VariantesOrdre "$ordre".Trim(); if (-not $o -or $o.Length -gt 220) { return $null }
    $n = ConvertTo-OrdreNorm $o
    $nc = $n -replace '^(?:jarvis[\s,]+)+', ''
    if ($nc -match "(?:\bet\b|\bpuis\b|\bensuite\b|\bapres\b|,)\s*(?:et\s+)?(?:ouvre|ferme|mets|met|baisse|monte|coupe|ajoute|note|lis|lance|active|desactive|verrouille|reduis|passe|eteins|redemarre|range|cherche|trouve|rappelle|fais)\b" -and $nc -notmatch '^(?:jarvis[\s,]+)?(?:rappelle moi|fais moi penser)\b.*\b(?:de|que|qu|d)\b') { return $null }
    foreach ($r in $script:ReglesRapides) {
        $m = [regex]::Match($n, $r.re)
        if (-not $m.Success) { continue }
        try { $plan = & $r.build $m $o $n } catch { Write-Journal -Action 'Chemin rapide' -Resultat "règle « $($r.nom) » en erreur : $($_.Exception.Message)"; $plan = $null }
        if ($plan) { return $plan }
    }
    $null
}

# ---------- Actions propres au chemin rapide ----------
Add-Action 'etat_site' 1 'lire l''état du site' 'etat_site() : dit si tonproduit.shop répond (code HTTP)' {
    param($a)
    $s = Get-StatutSite 8
    if ($s.ok) { Rep $true 'Le site tonproduit.shop répond, code 200, monsieur.' } else { Rep $true ("Attention monsieur, le site ne répond pas correctement. " + $(if ($s.code) { "Code $($s.code)." } else { 'Aucune réponse.' })) }
} { param($a) "vérifier l'état du site" }

Add-Action 'sourdine' 1 'passer en sourdine' 'sourdine() : met Jarvis en sourdine (n''écoute plus, ne parle plus, n''exécute plus rien ; on réactive avec Alt + « + » du pavé numérique)' {
    param($a)
    Set-Actif $false 'ordre vocal'; Rep $true 'Sourdine activée.'
} { param($a) 'passer en sourdine' }

Add-Action 'briefing_dire' 1 'faire le briefing' 'briefing_dire() : lit le briefing (chiffres, site, to-do, veille)' {
    param($a)
    Invoke-Briefing; Rep $true 'Briefing terminé.'
} { param($a) 'faire le briefing' }
