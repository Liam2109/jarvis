# Discrétion : QUI a le droit de parler, alertes dites une seule fois, état du micro.
#
# Mode discret (par défaut) : Jarvis ne parle que dans trois cas — ce qui répond à un ordre de Liam ("reponse"), le briefing du matin
# ("briefing") et une alerte GRAVE, une seule fois ("alerte"). Tout le reste est écrit au tableau de bord et dans le journal, sans voix.
# config.json : "voix_autorisees": ["reponse", "briefing", "alerte"]   (ajoutez "rappel" pour que les rappels soient dits à voix haute)
#               "alertes": { "delai_heures": 24, "voix_graves_seulement": true, "ignorer": [ "sous-chaîne de chemin à ignorer" ] }
#               "briefing_vocal": { "avant": "12:00" }   (le briefing automatique n'est dit qu'une fois par jour, avant cette heure)
$script:ContexteVoix = 'spontane'
$script:Retenu = New-Object System.Collections.Generic.List[object]        # ce qui n'a pas été dit pendant le mode jeu
$script:AlertesCache = $null
$script:MicroNiveau = 0; $script:MicroNiveauHeure = [datetime]::MinValue; $script:MicroNom = ''; $script:MicroAbsent = ''
$script:DernierEntendu = ''; $script:DernierEntenduHeure = [datetime]::MinValue

# ---------- Qui peut parler ----------
function Invoke-AvecContexteVoix([string]$contexte, [scriptblock]$bloc) {
    $avant = $script:ContexteVoix; $script:ContexteVoix = $contexte
    try { & $bloc } finally { $script:ContexteVoix = $avant }
}

function Get-VoixAutorisees {
    if ($Config.voix_autorisees) { return @($Config.voix_autorisees | ForEach-Object { "$_".ToLower() }) }
    @('reponse', 'briefing', 'alerte')
}

function Test-VoixPermise {
    # @{ ok; raison } — appelée par Parler avant toute synthèse vocale.
    if ($script:ModeJeu -eq $true) { return @{ ok = $false; raison = 'mode jeu' } }
    if ($script:ContexteVoix -in (Get-VoixAutorisees)) { return @{ ok = $true; raison = '' } }
    @{ ok = $false; raison = 'mode discret' }
}

function Retenir-Parole([string]$texte, [string]$raison) {
    # Le texte reste visible au tableau de bord (Add-Conv l'a déjà écrit) et dans le journal ; on ne le dit pas.
    Write-Journal -Action "Parole non prononcée ($raison)" -Resultat $texte
    if ($script:ModeJeu -eq $true) { Add-Retenu 'parole' $texte }
}

function Add-Retenu([string]$type, [string]$texte, [bool]$grave = $false) {
    $script:Retenu.Add(@{ type = $type; texte = $texte; heure = (Get-Date).ToString('HH:mm'); grave = $grave })
}

# Briefing automatique : dit une seule fois par jour, le matin ; sinon il s'affiche au tableau de bord sans voix.
function Get-FichierBriefingVocal { Join-Path $script:JarvisRoot 'memoire\briefing-vocal.txt' }
function Test-BriefingVocalAuto([datetime]$now = (Get-Date)) {
    $avant = if ($Config.briefing_vocal -and $Config.briefing_vocal.avant) { "$($Config.briefing_vocal.avant)" } else { '12:00' }
    if ($now.ToString('HH:mm') -ge $avant) { return $false }
    $f = Get-FichierBriefingVocal
    if ((Test-Path $f) -and ((Get-Content $f -Raw -ErrorAction SilentlyContinue).Trim() -eq $now.ToString('yyyy-MM-dd'))) { return $false }
    $true
}
function Set-BriefingVocalFait([datetime]$now = (Get-Date)) {
    $f = Get-FichierBriefingVocal; $d = Split-Path $f
    if (-not (Test-Path $d)) { New-Item -ItemType Directory $d -Force | Out-Null }
    Set-Content $f $now.ToString('yyyy-MM-dd') -Encoding ASCII
}

# ---------- Fichiers et processus que Jarvis ne signale jamais ----------
function Test-CheminIgnore([string]$chemin) {
    # Les fichiers de Jarvis, de sa mémoire, les sauvegardes et les fichiers temporaires de Jarvis ne sont jamais des alertes.
    if (-not $chemin) { return $false }
    $c = $chemin.ToLower().Replace('/', '\')
    $racine = "$script:JarvisRoot".ToLower().TrimEnd('\')
    if ($c -eq $racine -or $c.StartsWith($racine + '\')) { return $true }                              # dossier de Jarvis (dont memoire\, logs\, quarantaine\, sounds\)
    if ($c -match 'sauvegarde|backup|\.bak(\\|$)|\.bak$|\.old$|~$') { return $true }                   # sauvegardes
    $tmp = "$env:TEMP".ToLower().TrimEnd('\')
    if ($tmp -and $c.StartsWith($tmp + '\')) {
        $rel = $c.Substring($tmp.Length + 1)
        if ($rel -match '^(jarvis|jtest|jarvis-edge|jarvis-neutre|claude|rebuild|ollama|scratchpad)') { return $true }   # fichiers temporaires de Jarvis et de son cerveau
    }
    if ($c -match '\\jarvis-sauvegarde|\\rebuild\\|\\\.ollama\\') { return $true }
    foreach ($m in @($Config.alertes.ignorer)) { if ($m -and $c.Contains("$m".ToLower())) { return $true } }
    $false
}

# ---------- Alertes : dites UNE seule fois (au moins 24 h avant de les redire), puis seulement dans le panneau ----------
function Get-FichierAlertes { Join-Path $script:JarvisRoot 'memoire\alertes.json' }
function Get-AlerteDelaiHeures { if ($Config.alertes -and $Config.alertes.delai_heures) { [double]$Config.alertes.delai_heures } else { 24.0 } }

function Read-AlertesVues {
    if ($null -ne $script:AlertesCache) { return $script:AlertesCache }
    $h = @{}
    $f = Get-FichierAlertes
    if (Test-Path $f) {
        try {
            $o = Get-Content $f -Raw -Encoding UTF8 | ConvertFrom-Json
            foreach ($pr in $o.PSObject.Properties) {
                $v = $pr.Value
                $h[$pr.Name] = @{ titre = "$($v.titre)"; grave = [bool]$v.grave; ignoree = [bool]$v.ignoree; premiere = "$($v.premiere)"; derniere_vue = "$($v.derniere_vue)"; derniere_dite = "$($v.derniere_dite)"; vues = [int]$v.vues }
            }
        } catch {}
    }
    $script:AlertesCache = $h; $h
}
function Save-AlertesVues {
    $h = Read-AlertesVues
    if ($h.Count -gt 200) { foreach ($k in @($h.Keys | Sort-Object { $h[$_].derniere_vue } | Select-Object -First ($h.Count - 200))) { $h.Remove($k) } }
    $f = Get-FichierAlertes; $d = Split-Path $f
    if (-not (Test-Path $d)) { New-Item -ItemType Directory $d -Force | Out-Null }
    try { [IO.File]::WriteAllText($f, ($h | ConvertTo-Json -Depth 4), [Text.UTF8Encoding]::new($false)) } catch {}
}

function Register-Alerte([string]$cle, [string]$titre, [bool]$grave = $false, [datetime]$now = (Get-Date)) {
    # Note l'alerte et dit si elle PEUT être dite : jamais dite, ou dite il y a au moins `delai_heures` heures.
    $h = Read-AlertesVues; $k = $cle.ToLower()
    $nouvelle = -not $h.ContainsKey($k)
    if ($nouvelle) { $h[$k] = @{ titre = $titre; grave = $grave; ignoree = $false; premiere = $now.ToString('o'); derniere_vue = ''; derniere_dite = ''; vues = 0 } }
    $e = $h[$k]; $e.vues = [int]$e.vues + 1; $e.derniere_vue = $now.ToString('o'); $e.titre = $titre; $e.grave = $grave
    $peut = $true
    if ($e.derniere_dite) {
        $dt = [datetime]::MinValue
        if ([datetime]::TryParse($e.derniere_dite, [Globalization.CultureInfo]::InvariantCulture, [Globalization.DateTimeStyles]::RoundtripKind, [ref]$dt)) { $peut = (($now - $dt).TotalHours -ge (Get-AlerteDelaiHeures)) }
    }
    if ($e.ignoree) { $peut = $false }              # « ignore cette alerte » : plus jamais dite (reste visible dans le panneau)
    Save-AlertesVues
    if ($nouvelle -and (Get-Command Send-AlerteDiscord -ErrorAction SilentlyContinue)) { try { [void](Send-AlerteDiscord $cle $titre $grave) } catch { Write-Journal -Action 'Alerte Discord' -Resultat ("échec : " + (Hide-Secrets $_.Exception.Message)) } }      # #alertes sur Discord (limite par heure, doublons regroupés)
    @{ peut_dire = $peut; nouvelle = $nouvelle; vues = $e.vues }
}
function Set-AlerteDite([string]$cle, [datetime]$now = (Get-Date)) {
    $h = Read-AlertesVues; $k = $cle.ToLower()
    if ($h.ContainsKey($k)) { $h[$k].derniere_dite = $now.ToString('o'); Save-AlertesVues }
}

function Test-AlerteVocale([bool]$grave) {
    # Une alerte est dite à voix haute seulement si elle est grave (ou si "voix_graves_seulement" est désactivé), si la voix "alerte" est
    # autorisée et si Jarvis n'est pas en mode jeu.
    if ($script:ModeJeu -eq $true -or $script:Actif -eq $false) { return $false }          # mode jeu ou sourdine : une alerte n'est jamais dite
    if ('alerte' -notin (Get-VoixAutorisees)) { return $false }
    $seulementGraves = -not ($Config.alertes -and $Config.alertes.PSObject.Properties['voix_graves_seulement'] -and -not [bool]$Config.alertes.voix_graves_seulement)
    if ($seulementGraves -and -not $grave) { return $false }
    $true
}

function Get-AlertesPanneau([int]$n = 6) {
    # Pour le tableau de bord : alertes déjà vues, sans voix. Aucune adresse ni donnée sensible : titre, gravité, date, nombre de fois.
    $h = Read-AlertesVues
    @($h.Keys | Sort-Object { $h[$_].derniere_vue } -Descending | Select-Object -First $n | ForEach-Object {
        $e = $h[$_]; $dt = [datetime]::MinValue
        $q = if ([datetime]::TryParse($e.derniere_vue, [Globalization.CultureInfo]::InvariantCulture, [Globalization.DateTimeStyles]::RoundtripKind, [ref]$dt)) { $dt.ToString('dd/MM HH:mm') } else { '' }
        @{ titre = "$($e.titre)"; grave = [bool]$e.grave; quand = $q; vues = [int]$e.vues; dite = [bool]$e.derniere_dite; ignoree = [bool]$e.ignoree }
    })
}

# ---------- Micro ----------
function Get-MicroConfig {
    $nom = if ($Config.PSObject.Properties['micro_nom'] -and "$($Config.micro_nom)".Trim()) { ("$($Config.micro_nom)".Trim() -replace '["`]', '') } else { '' }
    $seuil = if ($Config.PSObject.Properties['micro_seuil_mot'] -and $Config.micro_seuil_mot) { [double]$Config.micro_seuil_mot } else { 0.65 }
    $var = if ($Config.PSObject.Properties['mot_activation_variantes']) { @($Config.mot_activation_variantes | ForEach-Object { "$_".Trim().ToLower() -replace '["`,;]', '' } | Where-Object { $_ }) } else { @() }
    $mot = "$($Config.moteur_voix)".Trim().ToLower(); if ($mot -notin 'vosk', 'vosk-grand', 'faster-whisper') { $mot = 'vosk' }
    $fen = if (Get-Command Get-FenetreOrdreSecondes -ErrorAction SilentlyContinue) { Get-FenetreOrdreSecondes } else { 8 }
    $ws = if ($Config.PSObject.Properties['whisper_modele'] -and "$($Config.whisper_modele)" -match '^[a-z0-9._-]{2,30}$') { "$($Config.whisper_modele)" } else { 'small' }
    $wp = if ($Config.PSObject.Properties['whisper_peripherique'] -and "$($Config.whisper_peripherique)" -in 'cpu', 'cuda') { "$($Config.whisper_peripherique)" } else { 'cpu' }
    $mc2 = if ($Config.PSObject.Properties['vosk_modele_chemin']) { ("$($Config.vosk_modele_chemin)".Trim() -replace '["`]', '') } else { '' }
    $ap = if ($Config.PSObject.Properties['moteur_voix_appareil'] -and "$($Config.moteur_voix_appareil)" -in 'cpu', 'cuda') { "$($Config.moteur_voix_appareil)" } else { $wp }
    $th = 3; if ($Config.PSObject.Properties['whisper_threads'] -and "$($Config.whisper_threads)" -match '^\d+$') { $th = [math]::Max(1, [math]::Min(3, [int]$Config.whisper_threads)) }      # 3 au plus sur 4 cœurs
    $vd = -not ($Config.PSObject.Properties['whisper_vad'] -and $Config.whisper_vad -eq $false)
    # Fin de phrase à deux vitesses : silence_fin_ms (1500 par défaut, 300 à 4000) pour les phrases libres ; silence_commande_ms (600, 300 à 1500, jamais plus que le précédent) seulement
    # quand ce qui vient d'être dit est déjà une commande exacte de la liste fermée ; duree_max_phrase_s (30, 5 à 60) borne une phrase continue. (L'ancien réglage silence_fin_secondes est ignoré.)
    $si = 1.5; if ($Config.PSObject.Properties['silence_fin_ms'] -and "$($Config.silence_fin_ms)" -match '^\d+$') { $si = [math]::Max(300, [math]::Min(4000, [int]$Config.silence_fin_ms)) / 1000.0 }
    $sc = 0.6; if ($Config.PSObject.Properties['silence_commande_ms'] -and "$($Config.silence_commande_ms)" -match '^\d+$') { $sc = [math]::Max(300, [math]::Min(1500, [int]$Config.silence_commande_ms)) / 1000.0 }; $sc = [math]::Min($sc, $si)
    $sr = 0.7; if ($Config.PSObject.Properties['silence_rapide_ms'] -and "$($Config.silence_rapide_ms)" -match '^\d+$') { $sr = [math]::Max(500, [math]::Min(1000, [int]$Config.silence_rapide_ms)) / 1000.0 }      # fin de phrase ADAPTATIVE : fermeture rapide (500 à 1000 ms, 700 par défaut) quand la phrase semble terminée
    $ad = -not ($Config.PSObject.Properties['fin_adaptative'] -and $Config.fin_adaptative -eq $false)
    $dm = 30; if ($Config.PSObject.Properties['duree_max_phrase_s'] -and "$($Config.duree_max_phrase_s)" -match '^\d+$') { $dm = [math]::Max(5, [math]::Min(60, [int]$Config.duree_max_phrase_s)) }
    $bn = -not ($Config.PSObject.Properties['bruit_adaptatif'] -and $Config.bruit_adaptatif -eq $false)      # seuil de voix relevé avec le bruit de fond (télé, ventilateur)
    @{ bruit = $bn; nom = $nom; seuil = $seuil; variantes = $var; moteur = $mot; fenetre = $fen; modele_chemin = $mc2; whisper_modele = $ws; whisper_peripherique = $ap; threads = $th; vad = $vd; silence = $si; silence_courte = $sc; duree_max = $dm; silence_rapide = $sr; adaptatif = $ad }
}
function Read-LigneMicro([string]$ligne) {
    # Lignes d'information de l'écoute. Retourne $true si la ligne a été consommée.
    if ($ligne -match '^NIVEAU:(\d{1,3})$') { $script:MicroNiveau = [int]$Matches[1]; $script:MicroNiveauHeure = Get-Date; return $true }
    if ($ligne -match '^MICRO:(.+)$') { $script:MicroNom = $Matches[1].Trim(); Write-Journal -Action 'Micro' -Resultat "écoute sur : $script:MicroNom"; return $true }
    if ($ligne -match '^DIAG:(.+)$') { if (Get-Command Add-DiagVocal -ErrorAction SilentlyContinue) { Add-DiagVocal $Matches[1] }; return $true }
    if ($ligne -match '^MOTEUR:(.+)$') { $script:MoteurVoix = $Matches[1].Trim(); Write-Journal -Action 'Reconnaissance vocale' -Resultat "moteur : $script:MoteurVoix"
        if ($script:MoteurVoix -match 'whisper/cpu' -and (Get-MicroConfig).whisper_peripherique -eq 'cuda' -and -not $script:EcouteMoteurForce) { Write-Journal -Action 'Reconnaissance vocale' -Resultat 'ATTENTION : GPU (cuda) demandé dans config.json mais la reconnaissance tourne sur CPU (bibliothèques CUDA introuvables, ou ancien code encore chargé : redémarrez Jarvis)' }
        return $true }
    if ($ligne -match '^MOTEUR_REPLI:(.+)$') { $script:MoteurVoixRepli = $Matches[1].Trim(); Write-Journal -Action 'Reconnaissance vocale' -Resultat "repli : $script:MoteurVoixRepli"; return $true }
    if ($ligne -match '^MICRO_ABSENT:(.*)$') { $script:MicroAbsent = $Matches[1].Trim(); Write-Journal -Action 'Micro' -Resultat "micro demandé introuvable (« $script:MicroAbsent » dans config.json, micro_nom) : micro par défaut utilisé"; return $true }
    $false
}
function Get-DonneesMicro {
    $age = ((Get-Date) - $script:MicroNiveauHeure).TotalSeconds
    @{ nom = $script:MicroNom; absent = $script:MicroAbsent; niveau = $(if ($age -lt 3) { $script:MicroNiveau } else { 0 }); actif = ($age -lt 3)
       entendu = $script:DernierEntendu; entendu_h = $(if ($script:DernierEntendu) { $script:DernierEntenduHeure.ToString('HH:mm:ss') } else { '' }) }
}

# ---------- Commandes vocales sur les alertes ----------
function Set-DerniereAlerteIgnoree {
    # « ignore cette alerte » : la plus récente alerte non ignorée ne sera plus jamais dite. Elle reste visible (grisée) dans le panneau.
    $h = Read-AlertesVues
    $k = $h.Keys | Where-Object { -not $h[$_].ignoree } | Sort-Object { $h[$_].derniere_vue } -Descending | Select-Object -First 1
    if (-not $k) { return $null }
    $h[$k].ignoree = $true; Save-AlertesVues
    $h[$k].titre
}
Add-Action 'alerte_ignorer' 1 'ignorer la dernière alerte' 'alerte_ignorer() : ne plus jamais dire à voix haute la dernière alerte (elle reste dans le panneau Alertes)' {
    param($a)
    $t = Set-DerniereAlerteIgnoree
    if ($t) { Rep $true "C'est noté, monsieur : je n'en parlerai plus ($t)." } else { Rep $true 'Il n''y a aucune alerte à ignorer, monsieur.' }
} { param($a) 'ignorer la dernière alerte' }
Add-Action 'alertes_liste' 1 'lister les alertes' 'alertes_liste() : dit les alertes enregistrées (sans voix tant qu''on ne le demande pas)' {
    param($a)
    $l = @(Get-AlertesPanneau 5)
    if (-not $l.Count) { return Rep $true 'Aucune alerte, monsieur.' }
    Rep $true ("$($l.Count) alerte$(if ($l.Count -gt 1) { 's' }) : " + (($l | ForEach-Object { "$($_.titre)$(if ($_.grave) { ', grave' })$(if ($_.ignoree) { ', ignorée' })" }) -join ' ; ') + '.')
} { param($a) 'lister les alertes' }