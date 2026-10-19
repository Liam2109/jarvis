# Pont Discord (côté Jarvis) : Liam parle à Jarvis depuis son téléphone, par un bot Discord PRIVÉ. Le pont lui-même est un processus séparé (pont-discord\pont.py,
# discord.py) lancé par Jarvis SEULEMENT si config.json "discord_actif" vaut true (défaut false), arrêté par arreter.ps1, par « Jarvis stop » et à la fermeture de Jarvis,
# redémarré seul s'il plante (journal d'erreurs, sans jamais le jeton).
#
# Échange par fichiers (memoire\discord\entrant : pont -> Jarvis ; memoire\discord\sortant : Jarvis -> pont). Le pont ne laisse passer QUE l'identifiant DISCORD_USER_ID et les salons
# de discord_salons ; Jarvis revérifie les deux. Un message reçu est l'ordre de Liam (même compréhension que la voix : règle, routeur local, puis Claude), jamais autre chose :
# le contenu d'une actualité, d'un fichier ou d'un message d'un tiers est une DONNÉE.
# Sécurité : niveau 3 toujours refusé ; toute action autre que la lecture / les petits réglages réversibles demande une confirmation par Discord (✅/❌ ou oui/non, délai
# configurable, sans réponse = annulation polie) ; certaines actions (code libre, installations, coffre, e-mails, lecture de fichiers) ne se font JAMAIS depuis Discord.
# Aucun ordre financier, aucun envoi de message à un tiers : le niveau 3 et les listes ci-dessous le garantissent, par le code.
$script:PontProc = $null; $script:PontErr = $null
if (-not (Get-Command New-EmbedStatut -ErrorAction SilentlyContinue)) { . (Join-Path $PSScriptRoot 'discord-embeds.ps1') }      # modèles de messages (embeds) : statut, to-do, marché, briefing, alertes
$script:PontDesactive = $false          # identifiants / salons manquants, pont abandonné, ou dépendance absente
$script:PontCoupeUrgence = $false       # coupé par « Jarvis stop » : ne redémarre pas seul (« réactive Discord »)
$script:PontPannes = New-Object System.Collections.Generic.List[datetime]
$script:PontProchainEssai = [datetime]::MinValue
$script:PontAnnonceFaite = $false
$script:DiscordPumpActif = $false       # vrai quand le pont tourne : Jarvis lit alors memoire\discord\entrant
$script:DiscordProchainPump = [datetime]::MinValue
$script:DiscordFile = New-Object System.Collections.Generic.Queue[object]
$script:DiscordReponses = @{}
$script:DiscordConfirmN = 0
$script:DiscordStopCanal = ''
$script:CanalDiscord = $null            # non nul pendant le traitement d'un ordre venu de Discord : Parler écrit au lieu de parler, Confirmer passe par Discord
$script:DiscordTampon = $null
$script:DiscordReplyTo = ''
$script:DiscordPlafondAtteint = $false
$script:DiscordAlertesEnvoyees = New-Object System.Collections.Generic.List[datetime]
$script:DiscordAlertesAttente = New-Object System.Collections.Generic.List[hashtable]
$script:DiscordAlertesVues = @{}
$script:DiscordProchainEntretien = [datetime]::MinValue

# ---------- Actions qu'on peut demander depuis Discord ----------
# LIBRES (niveau 1, aucune confirmation) : lectures, notes, to-do, petits réglages réversibles. Tout le reste de niveau 1 demande une confirmation par Discord.
$script:DiscordLibres = 'todo_ajouter', 'todo_terminer', 'todo_lire', 'note_ajouter', 'rappel_ajouter', 'etat_systeme', 'etat_site', 'business_etat', 'point_saas', 'idees_contenu', 'marche_valeur', 'marche_resume',
    'surveiller_5', 'resume_jour', 'reste_a_faire', 'profil_lire', 'profil_ajouter', 'alertes_liste', 'alerte_ignorer', 'capacites', 'reseau_etat', 'lister_processus', 'inspecter_processus', 'scanner_menaces',
    'chercher_fichiers', 'pc_trouver_fichier', 'bitwarden_statut', 'mesure_vitesse', 'briefing_relire', 'briefing_details', 'briefing_dire', 'dire_la_date_du_jour', 'winget_proposer', 'dossier_valeur',
    'veille_ajouter', 'veille_retirer', 'position_noter', 'volume', 'luminosite', 'musique', 'pc_media', 'pc_capture', 'priorite', 'discord_reactiver', 'test_alerte', 'guide_demarrer', 'guide_suivant', 'guide_repeter', 'guide_arreter'
# JAMAIS depuis Discord (refusées par le code, même avec « oui ») : code libre, scripts, installations, coffre de mots de passe, e-mails, lecture de fichiers / écran / presse-papiers, effacement de la mémoire.
$script:DiscordBloquees = 'powershell', 'executer_script', 'installer_programme', 'desinstaller_programme', 'winget_installer', 'bitwarden_deverrouiller', 'bitwarden_saisir', 'bitwarden_chercher', 'bitwarden_verrouiller',
    'envoyer_message', 'lire_fichier', 'resume_contenu', 'oublie_tout', 'profil_oublier', 'pc_forcer_fermeture'

function Get-DiscordConfig {
    # Lecture bornée des réglages Discord de config.json (tout est facultatif ; défauts prudents).
    $c = @{ actif = $false; salons = @{}; manquants = @(); delai = 60; max_alertes = 6; briefing_actif = $false; briefing_heure = '08:30'; vocal = $false; claude_max = 20 }
    if ($Config.PSObject.Properties['discord_actif'] -and $Config.discord_actif -eq $true) { $c.actif = $true }
    # Salons : associés AUTOMATIQUEMENT par le pont (mot-clé dans le nom : jarvis, système, marché, business), cache memoire\discord-salons.json ; discord_salons de config.json = identifiants FORCÉS (facultatif).
    $c.manquants = @('jarvis', 'systeme', 'marche', 'business')
    $cache = Read-JsonMemoire 'discord-salons.json'
    if ($cache -and $cache.salons) { foreach ($p in $cache.salons.PSObject.Properties) { if ("$($p.Value)" -match '^\d{5,25}$') { $c.salons[$p.Name] = "$($p.Value)" } } }
    if ($Config.PSObject.Properties['discord_salons'] -and $Config.discord_salons) {
        foreach ($p in $Config.discord_salons.PSObject.Properties) {
            $n = $(if ($p.Name -eq 'alertes') { 'systeme' } elseif ($p.Name -eq 'todo') { 'jarvis' } else { $p.Name })
            if ($n -in 'jarvis', 'systeme', 'marche', 'business' -and "$($p.Value)".Trim() -match '^\d{5,25}$') { $c.salons[$n] = "$($p.Value)".Trim() }
        }
    }
    $c.manquants = @($c.manquants | Where-Object { -not $c.salons.ContainsKey($_) })
    $mini = $(if (Test-ModeTest) { 1 } else { 5 })
    if ($Config.PSObject.Properties['discord_delai_confirmation_secondes'] -and "$($Config.discord_delai_confirmation_secondes)" -match '^\d+$') { $c.delai = [math]::Max($mini, [math]::Min(300, [int]$Config.discord_delai_confirmation_secondes)) }
    if ($Config.PSObject.Properties['discord_alertes_max_par_heure'] -and "$($Config.discord_alertes_max_par_heure)" -match '^\d+$') { $c.max_alertes = [math]::Min(60, [int]$Config.discord_alertes_max_par_heure) }
    if ($Config.PSObject.Properties['discord_briefing_actif'] -and $Config.discord_briefing_actif -eq $true) { $c.briefing_actif = $true }
    if ($Config.PSObject.Properties['discord_briefing_heure'] -and "$($Config.discord_briefing_heure)" -match '^([01]?\d|2[0-3]):[0-5]\d$') { $c.briefing_heure = ('{0:00}:{1}' -f [int]($Matches[1]), "$($Config.discord_briefing_heure)".Split(':')[1]) }
    if ($Config.PSObject.Properties['discord_vocal'] -and $Config.discord_vocal -eq $true) { $c.vocal = $true }
    if ($Config.PSObject.Properties['discord_claude_max_par_jour'] -and "$($Config.discord_claude_max_par_jour)" -match '^\d+$') { $c.claude_max = [math]::Min(500, [int]$Config.discord_claude_max_par_jour) }
    $c
}
function Get-DiscordDossier { Split-Path (Get-FichierMemoire 'discord\x') }
function Get-FichierPidPont { Get-FichierMemoire 'discord-pont.pid' }

function Get-DiscordIdentifiants {
    # @{ ok; manque[] } : seulement les NOMS des variables manquantes, jamais une valeur.
    $manque = @()
    $t = [Environment]::GetEnvironmentVariable('DISCORD_BOT_TOKEN', 'Process')
    if (-not (Test-Cle 'DISCORD_BOT_TOKEN') -or "$t".Trim().Length -lt 30) { $manque += 'DISCORD_BOT_TOKEN' }
    $u = [Environment]::GetEnvironmentVariable('DISCORD_USER_ID', 'Process')
    if ("$u".Trim() -notmatch '^\d{15,25}$') { $manque += 'DISCORD_USER_ID' }
    @{ ok = ($manque.Count -eq 0); manque = $manque }
}

# ---------- Cycle de vie du processus ----------
function Disable-PontDiscord([string]$raison) {
    # Désactive le pont pour cette session (config.json n'est pas modifié) ; Jarvis le dit poliment UNE seule fois.
    $script:PontDesactive = $true; $script:DiscordPumpActif = $false
    Write-Journal -Action 'Pont Discord' -Resultat "désactivé : $raison"
    if (-not $script:PontAnnonceFaite) {
        $script:PontAnnonceFaite = $true
        Invoke-AvecContexteVoix 'alerte' { Parler "Le pont Discord est désactivé, monsieur : $raison." }
    }
}
function Get-CommandePont {
    # Le vrai pont, ou (tests seulement) un faux pont inoffensif désigné par JARVIS_PONT_FAUX.
    if ((Test-ModeTest) -and $env:JARVIS_PONT_FAUX) { return $env:JARVIS_PONT_FAUX }
    Join-Path $script:RacineReelle 'pont-discord\pont.py'
}
function Start-PontProcessus {
    $py = Get-CommandePont
    if (-not (Test-Path $py)) { Disable-PontDiscord "le module pont-discord est introuvable"; return $false }
    $a = "-I -u `"$py`" --echange `"$(Get-DiscordDossier)`" --config `"$(Get-ConfigPath)`" --stop-flag `"$($script:StopFlag)`" --quitter-flag `"$(Join-Path $script:JarvisRoot 'memoire\quitter.flag')`" --parent $PID"
    $psi = New-Object Diagnostics.ProcessStartInfo 'python', $a
    $psi.UseShellExecute = $false; $psi.CreateNoWindow = $true; $psi.RedirectStandardOutput = $true; $psi.RedirectStandardError = $true
    $psi.StandardErrorEncoding = [Text.Encoding]::UTF8
    try {
        $p = [Diagnostics.Process]::Start($psi)
        try { if (-not ($Config.PSObject.Properties['priorite_cpu_basse'] -and $Config.priorite_cpu_basse -eq $false)) { $p.PriorityClass = 'BelowNormal' } } catch {}
        $script:PontErr = $p.StandardError.ReadToEndAsync(); [void]$p.StandardOutput.ReadToEndAsync()
        $script:PontProc = $p; $script:DiscordPumpActif = $true
        [IO.File]::WriteAllText((Get-FichierPidPont), (@{ pid = $p.Id; demarre = (Get-Date).ToString('o') } | ConvertTo-Json), [Text.UTF8Encoding]::new($false))
        Write-Journal -Action 'Pont Discord' -Resultat "démarré (PID $($p.Id))"
        return $true
    } catch {
        Write-Journal -Action 'Pont Discord' -Resultat ("échec au démarrage : " + (Hide-Secrets $_.Exception.Message))
        $script:PontProc = $null; return $false
    }
}
function Start-PontDiscord {
    # Appelée au démarrage de Jarvis. Ne fait rien si discord_actif n'est pas true. Retourne $true si le pont tourne.
    if ((Test-ModeTest) -and -not $env:JARVIS_PONT_FAUX) { return $false }          # tests : jamais de pont réel
    $c = Get-DiscordConfig
    if (-not $c.actif) { return $false }
    if ($script:PontProc -and -not $script:PontProc.HasExited) { return $true }
    if ($script:PontDesactive) { return $false }
    $id = Get-DiscordIdentifiants
    if (-not $id.ok) { Disable-PontDiscord ("il manque " + ($id.manque -join ' et ') + " dans le fichier .env"); return $false }
    Start-PontProcessus
}
function Get-DecisionRedemarragePont([int]$code, $pannes, [datetime]$now = (Get-Date)) {
    # Fonction pure. @{ action = 'redemarrer' | 'abandon' | 'fin'; delai_s; raison }. $pannes : liste des plantages récents (la panne actuelle y est ajoutée par l'appelant).
    if ($code -eq 0) { return @{ action = 'fin'; delai_s = 0; raison = 'arrêt normal' } }
    if ($code -eq 2) { return @{ action = 'abandon'; delai_s = 0; raison = "identifiants ou dépendance manquants (pip install discord.py)" } }
    if ($code -eq 3) { return @{ action = 'abandon'; delai_s = 0; raison = "connexion refusée par Discord (jeton invalide ou « Message Content Intent » non activé)" } }
    $recents = @($pannes | Where-Object { ($now - $_).TotalMinutes -le 10 })
    if ($recents.Count -gt 5) { return @{ action = 'abandon'; delai_s = 0; raison = "le pont a planté $($recents.Count) fois en 10 minutes" } }
    $delais = 5, 15, 30, 60, 120
    @{ action = 'redemarrer'; delai_s = $delais[[math]::Min([math]::Max($recents.Count, 1), $delais.Count) - 1]; raison = "plantage (code $code)" }
}
function Update-PontDiscord {
    # Appelée par la boucle principale : surveille le processus et le redémarre s'il plante.
    if ((Test-ModeTest) -and -not $env:JARVIS_PONT_FAUX) { return }
    if ($script:Quitter -or $script:PontDesactive -or $script:PontCoupeUrgence) { return }
    $c = Get-DiscordConfig; if (-not $c.actif) { return }
    if ($script:PontProc -and -not $script:PontProc.HasExited) { return }
    if ($script:PontProc) {
        $code = [int]$script:PontProc.ExitCode; $err = ''
        try { if ($script:PontErr -and $script:PontErr.Wait(800)) { $err = "$($script:PontErr.Result)" } } catch {}
        $script:PontProc = $null; $script:DiscordPumpActif = $false; Remove-Item (Get-FichierPidPont) -Force -ErrorAction SilentlyContinue
        $err = (Hide-Secrets (($err.Trim() -replace '\s+', ' '))); if ($err.Length -gt 500) { $err = $err.Substring($err.Length - 500) }
        if ($code -ne 0) { $script:PontPannes.Add((Get-Date)) }
        $d = Get-DecisionRedemarragePont $code $script:PontPannes
        Write-Journal -Action 'Pont Discord' -Resultat ("arrêté (code $code) : $($d.raison)" + $(if ($err) { " | erreur : $err" } else { '' }))
        if ($d.action -eq 'abandon') { Disable-PontDiscord $d.raison; return }
        if ($d.action -eq 'fin') { return }
        $script:PontProchainEssai = (Get-Date).AddSeconds($d.delai_s)
        Write-Journal -Action 'Pont Discord' -Resultat "redémarrage dans $($d.delai_s) s"
        return
    }
    if ((Get-Date) -lt $script:PontProchainEssai) { return }
    [void](Start-PontProcessus)
}
function Stop-PontOrphelin {
    # Filet : le processus enregistré dans memoire\discord-pont.pid, s'il est bien un pont Jarvis (ligne de commande vérifiée).
    $f = Get-FichierPidPont
    if (Test-Path $f) {
        try {
            $o = Get-Content $f -Raw -Encoding UTF8 | ConvertFrom-Json
            $pr = Get-CimInstance Win32_Process -Filter "ProcessId=$([int]$o.pid)" -ErrorAction SilentlyContinue
            if ($pr -and "$($pr.CommandLine)" -match 'pont\.py|pont-discord|faux-pont') { Stop-Process -Id ([int]$o.pid) -Force -ErrorAction SilentlyContinue; Write-Journal -Action 'Pont Discord' -Resultat "orphelin arrêté (PID $($o.pid))" }
        } catch {}
        Remove-Item $f -Force -ErrorAction SilentlyContinue
    }
}
function Stop-PontDiscord([switch]$Urgence) {
    if ($Urgence) { $script:PontCoupeUrgence = $true }
    $p = $script:PontProc
    if ($p -and -not $p.HasExited) {
        try { Send-DiscordSortant @{ type = 'arret' } } catch {}
        $ok = $false; try { $ok = $p.WaitForExit(3000) } catch {}
        if (-not $ok) { try { $p.Kill() } catch {} }
        Write-Journal -Action 'Pont Discord' -Resultat $(if ($ok) { 'arrêté proprement' } else { 'arrêt forcé' })
    }
    $script:PontProc = $null; $script:DiscordPumpActif = $false
    Stop-PontOrphelin
}
function Invoke-ArretUrgenceDiscord {
    # « Jarvis stop » : si le pont tourne, il dit où en sont les choses PUIS est coupé (il ne redémarre pas seul ; « réactive Discord » le relance).
    $c = Get-DiscordConfig
    if ($script:DiscordPumpActif -and $c.actif) {
        $canal = $(if ($script:DiscordStopCanal -and $c.salons.ContainsKey($script:DiscordStopCanal)) { $script:DiscordStopCanal } else { 'jarvis' })
        [void](Send-MessageDiscord $canal "Arrêt d'urgence exécuté, monsieur : tout est coupé. Le pont Discord s'arrête aussi ; dites « réactive Discord » à Jarvis, ou relancez-le, pour le remettre en marche.")
    }
    $script:DiscordStopCanal = ''
    $script:DiscordFile.Clear(); $script:DiscordReponses.Clear()
    if ($script:PontProc -or $script:DiscordPumpActif) { Stop-PontDiscord -Urgence }
}

# ---------- Échange par fichiers ----------
function Send-DiscordSortant([hashtable]$obj) {
    $d = Join-Path (Get-DiscordDossier) 'sortant'; if (-not (Test-Path $d)) { New-Item -ItemType Directory $d -Force | Out-Null }
    $nom = '{0:D19}-{1}.json' -f [DateTime]::UtcNow.Ticks, [guid]::NewGuid().ToString('N').Substring(0, 6)
    $tmp = Join-Path $d "$nom.tmp"
    [IO.File]::WriteAllText($tmp, ($obj | ConvertTo-Json -Depth 6 -Compress), [Text.UTF8Encoding]::new($false))
    Move-Item $tmp (Join-Path $d $nom) -Force
}
function Send-MessageDiscord([string]$canal, [string]$texte, [string]$replyTo = '', $embed = $null) {
    # Écrit un message pour le pont (secrets masqués). Faux si le pont ne tourne pas ou si le salon n'est pas renseigné.
    $c = Get-DiscordConfig
    if ($canal -eq 'alertes') { $canal = 'systeme' }
    if (-not $c.salons.ContainsKey($canal)) { $canal = 'jarvis' }      # salon introuvable : repli vers « jarvis »
    if (-not $script:DiscordPumpActif -or -not $c.salons.ContainsKey($canal) -or (-not "$texte".Trim() -and -not $embed)) { return $false }
    $o = @{ type = 'message'; canal = $canal; texte = (Hide-Secrets "$texte"); reply_to = $replyTo }; if ($embed) { $o.embed = $embed }
    Send-DiscordSortant $o
    $true
}
function Receive-MessageDiscord($m) {
    # Un fichier du pont. Les deux garde-fous du pont (identifiant, salon) sont REVÉRIFIÉS ici.
    $type = "$($m.type)"
    if ($type -eq 'message') {
        $c = Get-DiscordConfig; $uid = [Environment]::GetEnvironmentVariable('DISCORD_USER_ID', 'Process')
        if (-not $uid -or "$($m.auteur)" -ne "$uid") { Write-Journal -Action 'Discord' -Resultat 'message ignoré : auteur non autorisé'; return }
        $salon = "$($m.canal)"
        if (-not $c.salons.ContainsKey($salon) -or "$($m.canal_id)" -ne $c.salons[$salon]) { Write-Journal -Action 'Discord' -Resultat 'message ignoré : salon non listé'; return }
        $t = "$($m.texte)".Trim(); if (-not $t) { return }
        if ($t.Length -gt 1000) { $t = $t.Substring(0, 1000) }
        if ($script:DiscordFile.Count -ge 20) { Write-Journal -Action 'Discord' -Resultat 'file pleine : message ignoré'; return }
        $script:DiscordFile.Enqueue(@{ id = "$($m.id)"; canal = $salon; texte = $t })
    }
    elseif ($type -eq 'reponse') { if ("$($m.confirm_id)") { $script:DiscordReponses["$($m.confirm_id)"] = "$($m.reponse)" } }
    elseif ($type -eq 'stop') {
        Set-Content $script:StopFlag '1' -Encoding ASCII
        $script:DiscordStopCanal = "$($m.canal)"
        Write-Journal -Ordre 'Jarvis stop' -Action "Arrêt d'urgence demandé par Discord" -Resultat 'drapeau posé'
    }
}
function Invoke-PumpDiscord {
    # Appelée par Invoke-Pump (toutes les ~250 ms, seulement si le pont tourne) : lit les fichiers déposés par le pont.
    if (-not $script:DiscordPumpActif) { return }
    $now = Get-Date; if ($now -lt $script:DiscordProchainPump) { return }
    $script:DiscordProchainPump = $now.AddMilliseconds(250)
    $d = Join-Path (Get-DiscordDossier) 'entrant'; if (-not (Test-Path $d)) { return }
    foreach ($f in @(Get-ChildItem $d -Filter '*.json' -File -ErrorAction SilentlyContinue | Sort-Object Name | Select-Object -First 20)) {
        $m = $null; try { $m = Get-Content $f.FullName -Raw -Encoding UTF8 | ConvertFrom-Json } catch {}
        Remove-Item $f.FullName -Force -ErrorAction SilentlyContinue
        if ($m) { try { Receive-MessageDiscord $m } catch { Write-Journal -Action 'Discord' -Resultat 'message du pont illisible' } } else { Write-Journal -Action 'Discord' -Resultat 'fichier du pont illisible : supprimé' }
    }
}
function Get-OrdreDiscord { if ($script:DiscordFile.Count) { $script:DiscordFile.Dequeue() } else { $null } }

# ---------- Réponses : Parler et Confirmer redirigés vers Discord ----------
function Add-TamponDiscord([string]$texte) {
    $t = "$texte".Trim(); if (-not $t -or $t -match '^(Je réfléchis|Un instant|Un petit instant)') { return }      # (« Je réfléchis » : inutile, Discord affiche « en train d'écrire »)
    if ($null -ne $script:DiscordTampon) { [void]$script:DiscordTampon.Add($t) }      # (une liste vide est « fausse » en PowerShell : test explicite)
}
# ---------- Présentation des messages : lignes courtes, puces, gras, embeds, emojis rares, humour discret ----------
$script:DiscordEmbeds = New-Object System.Collections.Generic.List[hashtable]
$script:DiscordHumour = ''; $script:DiscordSansHumour = $false; $script:DiscordConfirmeDansOrdre = $false
$script:HumourAlea = { Get-Random -Minimum 0 -Maximum 100 }       # (les tests le remplacent : tirage de 0 à 99)
$script:CouleurVerte = 3066993; $script:CouleurRouge = 15158332; $script:CouleurBleue = 3447003; $script:CouleurOrange = 15105570; $script:CouleurGrise = 9807270
$script:MessageMaxCar = 1500
function Get-EmojiDiscord([string]$nom) {
    # Plus aucun emoji de tête (titres, champs, pieds, réponses) : le titre et la barre de couleur portent le sens. (Les ✅/❌ des confirmations restent : ce sont des réactions.)
    ''
}
$script:MotifGrave = '(?i)erreur|[ée]chec|impossible|n.ai pas pu|urgence|injoignable|incompris|pas compris|panne|plantage|introuvable|ne trouve pas|attention|alerte'
$script:MotifRefus = '(?i)refus|ne se fait pas|plafond|annul|sans r[ée]ponse|je ne peux|pas autoris'
function Get-NatureDiscord([string]$texte) {
    # 'grave' (aucune blague) | 'refus' (aucune blague) | 'fait' | 'neutre'
    $t = "$texte"
    if ($t -match $script:MotifGrave) { return 'grave' }
    if ($t -match $script:MotifRefus) { return 'refus' }
    $premiere = ($t -split "`n")[0].Trim()
    if ($script:DiscordConversation -eq $true) { return 'neutre' }      # pas de pastille ✅ sur une simple réponse de conversation : elle ne confirme que l'exécution d'une ACTION
    if ($premiere -and ((Test-PhrasePolitesse 'fait' $premiere) -or (Test-PhrasePolitesse 'fait_action' $premiere) -or (Test-PhrasePolitesse 'silencieux' $premiere))) { return 'fait' }
    'neutre'
}
function Format-GrasDiscord([string]$t) {
    # **Gras** sur l'essentiel : variations, montants (une ligne déjà en gras n'est pas retouchée).
    if ($t -match '\*\*') { return $t }
    [regex]::Replace($t, '(?<![\*\w])([+\-−]?\d+(?:[  ]\d{3})*(?:[,.]\d+)?\s?(?:%|€|euros?|dollars?|EUR|USD))(?![\*\w])', '**$1**')
}
function Format-ReponseDiscord([string[]]$lignes) {
    # Une idée par ligne, puces pour les énumérations, pas de pavé (1500 caractères au plus), aucun emoji.
    $out = New-Object System.Collections.Generic.List[string]
    foreach ($l in @($lignes)) {
        $l = "$l".Trim(); if (-not $l) { continue }
        if ($l -match '^\s*(?:[-•*]|\d+[.)])\s+(.+)$') { $out.Add('• ' + (Format-GrasDiscord $Matches[1].Trim())); continue }
        $parts = @($l -split ';\s+' | Where-Object { $_.Trim() })
        if ($parts.Count -ge 3) {
            $tete = $parts[0].Trim(); $k = $tete.IndexOf(' : ')
            if ($k -gt 0) { $out.Add((Format-GrasDiscord $tete.Substring(0, $k + 2).Trim())); $out.Add('• ' + (Format-GrasDiscord $tete.Substring($k + 3).Trim(' .'))) } else { $out.Add('• ' + (Format-GrasDiscord $tete.Trim(' .'))) }
            foreach ($p in $parts[1..($parts.Count - 1)]) { $out.Add('• ' + (Format-GrasDiscord $p.Trim(' .'))) }
            continue
        }
        foreach ($ph in @($l -split '(?<=[.!?…])\s+(?=[A-ZÀ-ÖØ-Þ«"])')) { if ($ph.Trim()) { $out.Add((Format-GrasDiscord $ph.Trim())) } }
    }
    if (-not $out.Count) { return '' }
    $txt = ''; foreach ($x in $out) { if (($txt.Length + $x.Length + 1) -gt $script:MessageMaxCar) { $txt = $txt.TrimEnd() + "`n…"; break }; $txt += $x + "`n" }
    $txt.TrimEnd()
}
function New-EmbedDiscord([string]$titre, [string]$description = '', [int]$couleur = 3447003, $champs = @(), [string]$pied = '') {
    # Embed (titre, description, champs, couleur, pied) : secrets masqués, jamais de conseil financier, longueurs bornées.
    $net = { param($x, $max) $y = (Hide-Secrets "$x").Trim(); if (Get-Command Protect-Conseil -ErrorAction SilentlyContinue) { $y = Protect-Conseil $y }; if ($y.Length -gt $max) { $y.Substring(0, $max - 1) + '…' } else { $y } }
    $ch = @(); foreach ($c in @($champs)) { if ($c -and "$($c.nom)".Trim() -and "$($c.valeur)".Trim()) { $ch += @{ nom = (& $net $c.nom 256); valeur = (& $net $c.valeur 1024); inline = [bool]$c.inline } } }
    $e = @{ titre = (& $net $titre 256); description = (& $net $description 2000); couleur = $couleur; champs = @($ch | Select-Object -First 25); pied = (& $net $pied 2048) }
    # Limite de Discord : 6000 caractères au total (titre, description, noms et valeurs de champs, pied) : les derniers champs sautent d'abord.
    $total = { $n = $e.titre.Length + $e.description.Length + $e.pied.Length; foreach ($c in $e.champs) { $n += $c.nom.Length + $c.valeur.Length }; $n }
    while ((& $total) -gt 6000 -and @($e.champs).Count -gt 0) { $e.champs = @($e.champs | Select-Object -SkipLast 1) }
    if ((& $total) -gt 6000) { $e.description = $e.description.Substring(0, [math]::Max(0, $e.description.Length - ((& $total) - 6000) - 1)) + '…' }
    $e
}
function Add-EmbedDiscord($e) { if ($e) { [void]$script:DiscordEmbeds.Add($e) } }
function Get-PiedDiscord([string]$source = '', $date = (Get-Date)) { $d = $date.ToString('dd/MM/yyyy HH:mm'); if ($source) { "Source $source · relevé du $d" } else { (Get-EmojiDiscord 'heure') + " Jarvis · $d" } }
function Get-HumourPourcent {
    # humour_taux (défaut 10) : part des réponses de CONVERSATION décontractée qui reçoivent une touche d'humour (0 = jamais). Ancien nom accepté : humour_pourcent.
    $p = 10
    foreach ($k in 'humour_pourcent', 'humour_taux') { if ($Config.PSObject.Properties[$k] -and "$($Config.$k)" -match '^\d+$') { $p = [math]::Min(100, [int]$Config.$k); break } }
    $p
}
function Test-HumourPermis([string]$ordre, [string]$reponse) {
    # Jamais sur les erreurs, refus, alertes, sujets financiers ni après une confirmation d'action sensible.
    if ($script:DiscordConversation -eq $false) { return $false }      # l'humour n'existe que dans la conversation décontractée : jamais autour d'une action, d'un statut ou d'un tableau
    if ($script:DiscordSansHumour -or $script:DiscordConfirmeDansOrdre -or $script:DiscordPlafondAtteint -or (Test-Stop)) { return $false }
    $tout = "$ordre`n$reponse"
    if ($tout -match $script:MotifGrave -or $tout -match $script:MotifRefus) { return $false }
    if ($tout -match '(?i)\b(cours|bourse|march[eé]s?|actions?|acheter|achat|vendre|vente|euros?|€|dollars?|revenus?|chiffre d.affaires|paiements?|abonn[eé]s?|stripe|virement|trade|trading|position|seuil|crypto|bitcoin|conseil|saas|business|lead|leads|facture|argent)\b') { return $false }
    if ((Test-QuestionConseil $ordre)) { return $false }
    if ($tout -match '(?i)\b(t[âa]ches?|to-?do|todo|rappels?|rappelle(?:-moi|r)?|termin[ée]e?s?|fini(?:e|s)?|coch[ée]e?s?)\b') { return $false }      # jamais de blague sur les tâches et les rappels
    $true
}
function Get-HumourDiscord([string]$ordre, [string]$reponse) {
    # Environ humour_pourcent % des réponses permises reçoivent une courte remarque (catalogue : lib\politesse.ps1, « humour »). 0 = jamais. Ne change ni les alertes ni la voix.
    $p = Get-HumourPourcent; if ($p -le 0) { return '' }
    if (-not (Test-HumourPermis $ordre $reponse)) { return '' }
    if ([int](& $script:HumourAlea) -ge $p) { return '' }
    $h = Get-Politesse 'humour'; if ($h) { "*$h*" } else { '' }
}
function Send-TamponDiscord {
    $lignes = @(); if ($null -ne $script:DiscordTampon) { $lignes = @($script:DiscordTampon); $script:DiscordTampon.Clear() }
    $embeds = @($script:DiscordEmbeds); $script:DiscordEmbeds.Clear()
    $hum = "$script:DiscordHumour"; $script:DiscordHumour = ''
    if (-not $lignes.Count -and -not $embeds.Count -and -not $hum) { return }
    if ((Get-DiscordStyle) -eq 'embed' -and $lignes.Count -and -not $embeds.Count) {      # toute réponse écrite est une carte : Réponse, C'est fait, Attention ou Problème
        $embeds = @(ConvertTo-EmbedReponse $lignes $hum); $lignes = @(); $hum = ''
    }
    $txt = Format-ReponseDiscord $lignes
    if ($hum) { $txt = ($txt + "`n" + $hum).Trim() }
    $ok = $true
    if ($embeds.Count) {
        $ok = Send-MessageDiscord "$script:CanalDiscord" $txt "$script:DiscordReplyTo" $embeds[0]
        foreach ($e in @($embeds | Select-Object -Skip 1)) { [void](Send-MessageDiscord "$script:CanalDiscord" '' "$script:DiscordReplyTo" $e) }
    } else { $ok = Send-MessageDiscord "$script:CanalDiscord" $txt "$script:DiscordReplyTo" }
    if (-not $ok) { Write-Journal -Action 'Discord' -Resultat "réponse non envoyée (pont arrêté ou salon « $script:CanalDiscord » non renseigné)" }
}
function Confirmer-Discord([string]$question) {
    # Question courte sur Discord ; réponse par ✅/❌ ou « oui »/« non » ; sans réponse dans le délai (60 s par défaut) = annulation polie.
    $script:DerniereConfirmation = ''
    $script:DiscordConfirmeDansOrdre = $true
    Send-TamponDiscord
    $script:DiscordConfirmN++; $id = 'c{0}-{1}' -f $script:DiscordConfirmN, [guid]::NewGuid().ToString('N').Substring(0, 6)
    $c = Get-DiscordConfig; [void]$script:DiscordReponses.Remove($id)
    if (-not (Send-MessageDiscordConfirmation $id $question $c.delai)) { $script:DerniereConfirmation = 'delai'; Write-Journal -Action 'Confirmation Discord' -Resultat 'question non envoyée : refusé'; return $false }
    Write-Journal -Action 'Confirmation Discord demandée' -Resultat "id $id, délai $($c.delai) s"
    $fin = (Get-Date).AddSeconds($c.delai); $rep = $null
    while ((Get-Date) -lt $fin) {
        Invoke-Pump
        if ($script:DiscordReponses.ContainsKey($id)) { $rep = "$($script:DiscordReponses[$id])"; break }
        if (Test-Stop) { break }
        Start-Sleep -Milliseconds 100
    }
    [void]$script:DiscordReponses.Remove($id)
    if ($rep -eq 'oui') { $script:DerniereConfirmation = 'oui'; Write-Journal -Action 'Réponse à la confirmation Discord' -Resultat 'accepté'; return $true }
    if ($rep) { $script:DerniereConfirmation = 'non'; Write-Journal -Action 'Réponse à la confirmation Discord' -Resultat 'refusé'; return $false }
    if (Test-Stop) { $script:DerniereConfirmation = 'non'; return $false }
    $script:DerniereConfirmation = 'delai'
    Send-DiscordSortant @{ type = 'confirmation_fin'; confirm_id = $id; issue = 'delai' }
    Write-Journal -Action 'Confirmation Discord' -Resultat 'aucune réponse : refusé'
    Add-TamponDiscord (Get-Politesse 'sans_reponse')
    $false
}
function Send-MessageDiscordConfirmation([string]$id, [string]$question, [int]$delai) {
    $c = Get-DiscordConfig; $canal = "$script:CanalDiscord"
    if (-not $script:DiscordPumpActif -or -not $c.salons.ContainsKey($canal)) { return $false }
    Send-DiscordSortant @{ type = 'confirmation'; confirm_id = $id; canal = $canal; texte = (Hide-Secrets "$question"); delai = $delai; reply_to = "$script:DiscordReplyTo" }
    $true
}
function Get-NiveauDiscord($a, $niv) {
    # Durcit les permissions pour un ordre venu de Discord : niveau 3 reste 3 ; les actions bloquées passent à 3 ; tout niveau 1 hors liste libre passe à 2 (confirmation).
    if ($niv.niveau -ge 3) { return $niv }
    $t = "$($a.type)".ToLower()
    if ($t -in $script:DiscordBloquees) { return @{ niveau = 3; raison = "cela ne se fait pas depuis Discord, uniquement à votre clavier" } }
    if ($niv.niveau -eq 1 -and $t -notin $script:DiscordLibres) { return @{ niveau = 2; raison = "$($niv.raison) (action sensible depuis Discord)" } }
    $niv
}

# ---------- Ordres reçus par Discord ----------
function Get-DiscordClaudeFichier { 'discord-claude.json' }
function Use-QuotaClaudeDiscord {
    # Plafond quotidien d'appels à Claude pour les ordres venus de Discord (discord_claude_max_par_jour, 20 par défaut). Règles et routeur local d'abord : Claude seulement si nécessaire.
    $c = Get-DiscordConfig; $auj = (Get-Date).ToString('yyyy-MM-dd')
    $o = Read-JsonMemoire (Get-DiscordClaudeFichier); $n = $(if ($o -and "$($o.date)" -eq $auj) { [int]$o.n } else { 0 })
    if ($n -ge $c.claude_max) { $script:DiscordPlafondAtteint = $true; Write-Journal -Action 'Cerveau (Discord)' -Resultat "plafond quotidien atteint ($n sur $($c.claude_max)) : pas d'appel à Claude"; return $false }
    Save-JsonMemoire (Get-DiscordClaudeFichier) ([ordered]@{ date = $auj; n = ($n + 1) })
    $true
}
function Get-UsageClaudeDiscord { $o = Read-JsonMemoire (Get-DiscordClaudeFichier); if ($o -and "$($o.date)" -eq (Get-Date).ToString('yyyy-MM-dd')) { [int]$o.n } else { 0 } }
function Get-EtatPontTexte {
    $f = Join-Path (Get-DiscordDossier) 'etat.json'
    if (-not $script:DiscordPumpActif) { return 'inactif' }
    try { $e = Get-Content $f -Raw -Encoding UTF8 | ConvertFrom-Json; if ($e.connecte -eq $true -and ([DateTimeOffset]::UtcNow.ToUnixTimeSeconds() - [double]$e.ts) -lt 90) { return 'connecté' } } catch {}
    'en cours de connexion'
}
function Get-StatutJarvisDonnees {
    $mode = $(if ($script:Actif -eq $false) { 'en sourdine' } elseif ($script:ModeJeu -eq $true) { 'actif, en mode jeu (silencieux)' } else { 'actif' })
    $cerv = $(if (Get-Command Get-ModeCerveau -ErrorAction SilentlyContinue) { try { Get-ModeCerveau } catch { 'inconnu' } } else { 'inconnu' })
    $marche = $(if ((Get-Command Test-MarcheActif -ErrorAction SilentlyContinue) -and (Test-MarcheActif)) { 'actif' } else { 'désactivé' })
    $etat = $(if ($script:Actif -eq $false) { 'sourdine' } elseif ($script:ModeJeu -eq $true) { 'jeu' } else { 'actif' })
    $pont = Get-EtatPontTexte
    @{ mode = $mode; etat = $etat; cerveau = $cerv; pont = $pont; discord = $pont; todo = @(Get-TodoOuverte).Count; marche = $marche; marche_actif = ($marche -eq 'actif'); claude = (Get-UsageClaudeDiscord); claude_max = (Get-DiscordConfig).claude_max }
}
function Get-StatutJarvisTexte {
    $d = Get-StatutJarvisDonnees
    "Jarvis est $($d.mode), monsieur. Cerveau : $($d.cerveau). Pont Discord : $($d.pont). Tâches ouvertes : $($d.todo). Veille du marché : $($d.marche). Appels à Claude par Discord aujourd'hui : $($d.claude) sur $($d.claude_max)."
}
function Get-EmbedStatutDiscord {
    $d = Get-StatutJarvisDonnees
    $cv = $(if ("$($d.cerveau)" -in 'local', 'claude') { "$($d.cerveau)" } else { 'hybride' })
    New-EmbedStatut @{ mode = $d.etat; cerveau = $cv; discord = $d.discord; todo = $d.todo; marche = $d.marche_actif; claude = $d.claude; claude_max = $d.claude_max }
}
function Get-BriefingDiscordLignes {
    # 3 ou 4 phrases : la version courte du briefing du matin.
    if (-not $script:BriefingMatin -and (Get-Command Initialize-BriefingMatin -ErrorAction SilentlyContinue)) { try { [void](Initialize-BriefingMatin) } catch { Write-Journal -Action 'Briefing Discord' -Resultat "indisponible : $($_.Exception.Message)" } }
    $l = @(); if ($script:BriefingMatin) { $l = @($script:BriefingMatin.parle | Where-Object { "$_".Trim() } | Select-Object -First 4 | ForEach-Object { "$_".Trim() }) }
    $l
}
function Get-BriefingDiscordTexte {
    $l = @(Get-BriefingDiscordLignes)
    if (-not $l.Count) { return "Le briefing n'est pas disponible pour le moment, monsieur." }
    $l -join ' '
}
function Get-EmbedBriefingDiscord([string]$titre = 'Briefing') {
    $l = @(Get-BriefingDiscordLignes); if (-not $l.Count) { return $null }
    $det = @(); if ($script:BriefingMatin -and $script:BriefingMatin.details) { $det = @($script:BriefingMatin.details | ForEach-Object { "$_".Trim() } | Where-Object { $_ }) }
    $saas = @($det | Where-Object { $_ -match '^(Nouveaux quiz|Nouveaux abonnés|Taux de conversion|Chiffre d.affaires|Paiements)' } | Select-Object -First 4)
    $marche = @($det | Where-Object { $_ -match '(?i)march[eé]|cours|variation' -and $_ -notmatch '^Mon SaaS' } | Select-Object -First 3)
    $nb = @(Get-TodoOuverte); $afaire = @(); if ($nb.Count) { $afaire += (Get-MotNombre $nb.Count 'tâche ouverte' 'tâches ouvertes'); $afaire += @($nb | Select-Object -First 2 | ForEach-Object { (Get-EmojiModele 'vide') + " $_" }) }
    New-EmbedBriefing $l $saas $marche $afaire $titre
}
function Get-EmbedTodoDiscord { New-EmbedTodo @(Get-TachesTodo 4) }
function Get-PeriodesCache($v) {
    # Variations sur 1 semaine (5 séances) et 1 mois (21 séances) lues dans le CACHE local seulement (aucun réseau, aucune requête). $null si le cache est absent.
    try {
        $sym = Get-SymboleValide $v; if (-not $sym) { return $null }
        $f = Get-FichierHistorique $sym 'jour'; if (-not (Test-Path $f)) { return $null }
        $pts = @((Get-Content $f -Raw -Encoding UTF8 | ConvertFrom-Json).points); if ($pts.Count -lt 6) { return $null }
        $s5 = Get-StatsPeriode $pts 5; $s21 = Get-StatsPeriode $pts 21
        @{ sem = $(if ($s5) { $s5.variation_pct } else { $null }); mois = $(if ($s21) { $s21.variation_pct } else { $null }) }
    } catch { $null }
}
function Get-EmbedValeurDiscord($v) {
    # « Où en est X ? » : cours, variations (jour, semaine, mois), source et date. Sans données : un message clair qui dit quoi faire.
    $rm = Get-RaisonMarche; if ($rm) { return (New-EmbedMarcheVide "$($v.nom)" "$rm") }
    $r = Read-DernierReleve; if (-not $r) { return (New-EmbedMarcheVide "$($v.nom)" "la veille n'a pas encore fait de relevé") }
    $c = Select-CoursValeur $r.cours $v; if (-not $c) { return (New-EmbedMarcheVide "$($v.nom)" "mes sources ne donnent pas de cours pour cette valeur") }
    $var = $null; if ($null -ne $c.variation_pct -and "$($c.variation_pct)" -ne '') { $var = [double]$c.variation_pct }
    $per = Get-PeriodesCache $v
    $e = New-EmbedMarche @{ nom = "$($v.nom)"; prix = [double]$c.prix; devise = (Get-NomDevise $c.devise); var_jour = $var; var_sem = $(if ($per) { $per.sem } else { $null }); var_mois = $(if ($per) { $per.mois } else { $null }); source = "$($c.source)"; date = (ConvertTo-DateMarche $c.date) }
    $a = @(Select-ActusValeur $r.actus $v 3)
    if ($a.Count) { $e.champs = @($e.champs) + @(@{ nom = ((Get-EmojiModele 'note') + ' Titres récents'); valeur = (($a | ForEach-Object { '• ' + (Get-PhraseActu $_) }) -join "`n"); inline = $false }) }
    $e
}
function Get-ReponseValeurDiscord($v) {
    # « Où en est X ? » en LECTURE SEULE : texte, source et date du relevé. Aucune fenêtre, aucun conseil.
    $txt = Get-ReponseValeur $v.nom
    if (-not (Get-RaisonMarche)) {
        $r = Read-DernierReleve; $c = $(if ($r) { Select-CoursValeur $r.cours $v } else { $null })
        if ($c) { $txt += " Relevé du " + (ConvertTo-DateMarche $c.date).ToString('dd/MM/yyyy à HH:mm') + "." }
    }
    Protect-Conseil $txt
}
function Invoke-CommandeDiscord([string]$texte) {
    # Commandes propres à Discord, comprises par règle (aucune IA). Retourne $true si l'ordre est traité ici.
    $n = (ConvertTo-OrdreNorm $texte).Trim() -replace '^(?:jarvis[\s,]+)+', '' -replace '[\s.!?]+$', ''
    if ($n -match '^(?:stop|arret d.urgence|urgence|arrete tout)$') {      # (le pont l'intercepte déjà : filet si le message arrive quand même jusqu'ici)
        Set-Content $script:StopFlag '1' -Encoding ASCII; $script:DiscordStopCanal = "$script:CanalDiscord"
        Write-Journal -Ordre $texte -Action "Arrêt d'urgence demandé par Discord" -Resultat 'drapeau posé'; Add-TamponDiscord "Arrêt d'urgence demandé, monsieur."; return $true
    }
    if ((Get-Command Invoke-DevCommande -ErrorAction SilentlyContinue) -and (Invoke-DevCommande $texte)) { $script:DiscordSansHumour = $true; return $true }      # « dev : ... » : agent de développement du SaaS (désactivé par défaut)
    if ((Get-Command Invoke-DevDecision -ErrorAction SilentlyContinue) -and (Invoke-DevDecision $texte)) { $script:DiscordSansHumour = $true; return $true }      # « valide » / « refuse » après un compte rendu de l'agent
    if ((Get-Command Test-DemandePointSaas -ErrorAction SilentlyContinue) -and (Test-DemandePointSaas $texte)) {      # « as-tu les données du SaaS », « stats », « comment va le site »... : le point, directement (embed à champs)
        Write-Journal -Ordre $texte -Action 'Discord : point SaaS' -Resultat 'lecture seule, sources branchées uniquement'; $script:DiscordSansHumour = $true
        $d = Get-SaasDonnees
        if ((Get-DiscordStyle) -eq 'embed') { Add-EmbedDiscord (New-EmbedSaas $d) } else { Add-TamponDiscord (Get-SaasTexte $d) }
        return $true
    }
    $plan = Get-PlanRapide $texte
    if ($plan -and "$($plan.regle)" -match '^todo_lire') { Write-Journal -Ordre $texte -Action 'Discord : to-do' -Resultat 'lue'; $script:DiscordSansHumour = $true
        if ((Get-DiscordStyle) -eq 'embed') { Add-EmbedDiscord (Get-EmbedTodoDiscord) } else { $o = @(Get-TodoOuverte); Add-TamponDiscord $(if ($o.Count) { "Tâches ouvertes : " + ($o -join ' ; ') + '.' } else { 'Aucune tâche ouverte, monsieur.' }) }
        return $true }
    if ($n -match '^(?:le |ton |mon )?(?:statut|etat|status)(?: de jarvis)?$|^(?:donne moi |quel est )(?:le |ton )?(?:statut|etat)(?: de jarvis)?$') { Write-Journal -Ordre $texte -Action 'Discord : statut' -Resultat 'lu'; if ((Get-DiscordStyle) -eq 'embed') { Add-EmbedDiscord (Get-EmbedStatutDiscord) } else { Add-TamponDiscord (Get-StatutJarvisTexte) }; return $true }
    if ($n -match '^(?:fais |donne |lance |envoie )?(?:moi )?(?:le |un |mon )?(?:briefing|point du jour)(?: court)?$') { Write-Journal -Ordre $texte -Action 'Discord : briefing' -Resultat 'court (3-4 phrases)'; $script:DiscordSansHumour = $true; $eb = $(if ((Get-DiscordStyle) -eq 'embed') { Get-EmbedBriefingDiscord } else { $null }); if ($eb) { Add-EmbedDiscord $eb } else { Add-TamponDiscord (Get-BriefingDiscordTexte) }; return $true }
    if ($n -match '^(?:ou en est|ou en sont|comment va|comment vont)\s+(?<v>.+)$') {
        $v = Find-ValeurSuivie $Matches['v']
        if ($v) { Write-Journal -Ordre $texte -Action 'Discord : où en est (marché, lecture seule)' -Resultat $v.nom; $script:DiscordSansHumour = $true; if ((Get-DiscordStyle) -eq 'embed') { Add-EmbedDiscord (Get-EmbedValeurDiscord $v) } else { Add-TamponDiscord (Get-ReponseValeurDiscord $v) }; return $true }
        return $false
    }
    if ($n -match '^(?:les? |mes )?(?:stats?|statistiques|chiffres)(?: (?:du|de|des|sur|de mon|de la))?(?: (?:mon|le|ton|la))?(?: (?:saas|site|business|boutique))?$|^(?:point|etat|bilan) (?:du |de mon |sur le |sur mon |de la )?(?:saas|business)$') {
        $script:DiscordSansHumour = $true
        $t = $(if ($script:Actions.ContainsKey('point_saas')) { 'point_saas' } else { 'business_etat' })
        $r = Invoke-UneAction ([pscustomobject]@{ type = $t }) $texte
        if ($r) { Add-TamponDiscord (Short (Hide-Secrets $(if ($r.donnees) { "$($r.donnees)" } else { "$($r.texte)" })) 1500) } else { Add-TamponDiscord (Get-Politesse 'incompris') }
        return $true
    }
    $false
}
function Invoke-OrdreDiscord([string]$texte, [string]$canal = 'jarvis', [string]$replyTo = '') {
    # Traite UN ordre de Liam venu de Discord et lui répond par écrit. Même compréhension que la voix (règle, routeur local, Claude), ton majordome.
    $script:CanalDiscord = $canal; $script:DiscordReplyTo = $replyTo; $script:DiscordPlafondAtteint = $false; $script:DiscordNbActions = 0; $script:DiscordConversation = $null
    $script:DiscordTampon = New-Object System.Collections.Generic.List[string]; $script:DiscordEmbeds.Clear(); $script:DiscordHumour = ''; $script:DiscordSansHumour = $false; $script:DiscordConfirmeDansOrdre = $false
    try {
        Write-Journal -Ordre "[Discord #$canal] $texte" -Action 'Ordre reçu par Discord' -Resultat 'traitement'
        if (-not (Invoke-CommandeDiscord $texte)) {
            if ($script:Actif -eq $false) { Invoke-OrdreSourdine $texte }          # sourdine : réponse écrite seulement, aucune action
            else { Invoke-OrdreCorps $texte }
        }
    } catch {
        Write-Journal -Ordre "[Discord] $texte" -Action 'Ordre Discord' -Resultat ("erreur : " + (Hide-Secrets $_.Exception.Message))
        Add-TamponDiscord "Une erreur est survenue, monsieur : $(Hide-Secrets (Short $_.Exception.Message 160))"
    } finally {
        if ($script:DiscordPlafondAtteint) { Add-TamponDiscord (Get-Politesse 'refus' @{ raison = "mon plafond quotidien d'appels à Claude est atteint ($((Get-DiscordConfig).claude_max)) ; les commandes simples restent disponibles" }) }
        if (-not $script:DiscordTampon.Count -and -not $script:DiscordEmbeds.Count -and -not (Test-Stop)) { Add-TamponDiscord (Get-Politesse 'fait') }
        $script:DiscordConversation = ([int]$script:DiscordNbActions -eq 0 -and -not $script:DiscordEmbeds.Count)      # aucune action exécutée, aucun embed : de la conversation (texte simple, sans pastille)
        try { $rep = (($script:DiscordTampon -join ' ') + ' ' + (($script:DiscordEmbeds | ForEach-Object { "$($_.titre)" }) -join ' ')); $script:DiscordHumour = Get-HumourDiscord $texte $rep } catch { $script:DiscordHumour = '' }
        Send-TamponDiscord
        $script:CanalDiscord = $null; $script:DiscordReplyTo = ''; $script:DiscordTampon = $null; $script:DiscordEmbeds.Clear(); $script:DiscordConversation = $null
    }
}
function Invoke-OrdreDiscordEntree($d) { Invoke-OrdreDiscord "$($d.texte)" "$($d.canal)" "$($d.id)" }

# ---------- Alertes sortantes (#alertes) : problème ou seuil dépassé seulement ----------
function Send-AlerteDiscord([string]$cle, [string]$titre, [bool]$grave = $false) {
    # Retourne 'envoyee' | 'regroupee' | 'doublon' | 'inactive'. Limite par heure (discord_alertes_max_par_heure) ; au-delà, les alertes sont regroupées en UN message.
    $c = Get-DiscordConfig
    if (-not $c.actif -or -not $script:DiscordPumpActif -or -not $c.salons.ContainsKey('systeme') -or $c.max_alertes -lt 1) { return 'inactive' }
    $now = Get-Date
    $texte = Hide-Secrets "$titre"; if (Get-Command Protect-Conseil -ErrorAction SilentlyContinue) { $texte = Protect-Conseil $texte }
    $k = (ConvertTo-OrdreNorm $texte) -replace '\d+', '#'                                                 # même alerte, chiffres près : un doublon
    if ($script:DiscordAlertesVues.ContainsKey($k) -and ($now - $script:DiscordAlertesVues[$k]).TotalHours -lt 1) {
        $att = @($script:DiscordAlertesAttente | Where-Object { $_.k -eq $k }); if ($att.Count) { $att[0].n = [int]$att[0].n + 1 }
        return 'doublon'
    }
    [void]$script:DiscordAlertesEnvoyees.RemoveAll([Predicate[datetime]]{ param($t) ($now - $t).TotalHours -ge 1 })
    $script:DiscordAlertesVues[$k] = $now
    if ($script:DiscordAlertesEnvoyees.Count -lt $c.max_alertes) {
        if ((Get-DiscordStyle) -eq 'embed') { [void](Send-MessageDiscord 'systeme' '' '' (New-EmbedAlerte $texte $cle $grave)) } else { [void](Send-MessageDiscord 'systeme' "Alerte, monsieur : $texte") }
        $script:DiscordAlertesEnvoyees.Add($now); Write-Journal -Action 'Alerte Discord' -Resultat "envoyée : $cle"
        return 'envoyee'
    }
    $script:DiscordAlertesAttente.Add(@{ k = $k; texte = $texte; n = 1 })
    Write-Journal -Action 'Alerte Discord' -Resultat "limite de $($c.max_alertes) par heure atteinte : regroupée ($cle)"
    'regroupee'
}
function Update-AlertesDiscord {
    # Envoie, dès que la limite horaire le permet, UN message qui regroupe les alertes en attente.
    if (-not $script:DiscordAlertesAttente.Count) { return $false }
    $c = Get-DiscordConfig; $now = Get-Date
    [void]$script:DiscordAlertesEnvoyees.RemoveAll([Predicate[datetime]]{ param($t) ($now - $t).TotalHours -ge 1 })
    if ($script:DiscordAlertesEnvoyees.Count -ge $c.max_alertes) { return $false }
    $l = @($script:DiscordAlertesAttente | ForEach-Object { "• $($_.texte)" + $(if ([int]$_.n -gt 1) { " (×$($_.n))" } else { '' }) })
    $nb = $script:DiscordAlertesAttente.Count; $att = @($script:DiscordAlertesAttente); $script:DiscordAlertesAttente.Clear()
    if ((Get-DiscordStyle) -eq 'embed') { [void](Send-MessageDiscord 'systeme' '' '' (New-EmbedAlertesGroupees $att)) } else { [void](Send-MessageDiscord 'systeme' ("Alertes regroupées ($nb), monsieur :`n" + ($l -join "`n"))) }
    $script:DiscordAlertesEnvoyees.Add($now); Write-Journal -Action 'Alerte Discord' -Resultat "$nb alerte(s) regroupée(s) envoyée(s) en un message"
    $true
}

# ---------- Briefing du matin dans #jarvis (si demandé ; désactivé par défaut) ----------
function Update-BriefingDiscord {
    $c = Get-DiscordConfig
    if ((Get-Command Get-BriefingConfig -ErrorAction SilentlyContinue) -and (Get-BriefingConfig).actif) { return $false }      # le nouveau briefing du matin (briefing_actif, lib\saas.ps1) remplace celui-ci
    if (-not $c.briefing_actif -or -not $script:DiscordPumpActif -or -not $c.salons.ContainsKey('jarvis')) { return $false }
    $now = Get-Date; $auj = $now.ToString('yyyy-MM-dd')
    $h = [datetime]::ParseExact("$auj $($c.briefing_heure)", 'yyyy-MM-dd HH:mm', $null)
    if ($now -lt $h -or $now -gt $h.AddHours(4)) { return $false }
    $o = Read-JsonMemoire 'discord-briefing.json'; if ($o -and "$($o.date)" -eq $auj) { return $false }
    Save-JsonMemoire 'discord-briefing.json' ([ordered]@{ date = $auj })
    $eb = $(if ((Get-DiscordStyle) -eq 'embed') { Get-EmbedBriefingDiscord 'Briefing du matin' } else { $null })
    if ($eb) { [void](Send-MessageDiscord 'jarvis' ((Get-SalutationHeure) + '.') '' $eb) } else { [void](Send-MessageDiscord 'jarvis' ((Get-SalutationHeure) + ". " + (Get-BriefingDiscordTexte))) }
    Write-Journal -Action 'Briefing Discord' -Resultat "envoyé dans #jarvis ($($c.briefing_heure))"
    $true
}
$script:SalonsManquantsDits = ''
function Update-SalonsManquants {
    # Un salon introuvable (ni associé par son nom, ni forcé) : Jarvis le dit poliment UNE fois par changement et replie vers « jarvis ». Rien tant que le pont n'a pas lu les salons.
    $cache = Read-JsonMemoire 'discord-salons.json'; if (-not $cache) { return $false }
    $c = Get-DiscordConfig; $m = @($c.manquants); $cle = ($m -join ',')
    if ($cle -eq $script:SalonsManquantsDits) { return $false }
    $script:SalonsManquantsDits = $cle
    if (-not $m.Count) { return $false }
    $txt = "Je ne trouve pas de salon pour : " + ($m -join ', ') + ". Je replie ces messages vers « jarvis », monsieur ; créez ou renommez un salon contenant ce mot."
    Write-Journal -Action 'Pont Discord' -Resultat $txt
    [void](Send-MessageDiscord 'jarvis' $txt)
    Invoke-AvecContexteVoix 'alerte' { Parler $txt }
    $true
}
function Update-Discord {
    # Entretien léger (toutes les ~20 s) : alertes regroupées et briefing planifié.
    if (-not $script:DiscordPumpActif) { return }
    $now = Get-Date; if ($now -lt $script:DiscordProchainEntretien) { return }
    $script:DiscordProchainEntretien = $now.AddSeconds(20)
    try { [void](Update-AlertesDiscord); [void](Update-BriefingMatinSaas); [void](Update-BriefingDiscord); [void](Update-SalonsManquants) } catch { Write-Journal -Action 'Discord' -Resultat ("entretien : " + (Hide-Secrets $_.Exception.Message)) }
}

# ---------- Messages vocaux : PRÉVUS, désactivés par défaut (config.json discord_vocal = false) ----------
function Send-VocalDiscord([string]$fichier, [string]$canal = 'jarvis') {
    # Envoie un fichier audio de Jarvis dans un salon. Rien n'appelle cette fonction pour l'instant. Faux (et journalisé) tant que discord_vocal n'est pas true.
    $c = Get-DiscordConfig
    if (-not $c.vocal) { Write-Journal -Action 'Discord vocal' -Resultat 'refusé : discord_vocal est désactivé (false)'; return $false }
    if (-not $script:DiscordPumpActif -or -not $c.salons.ContainsKey($canal)) { return $false }
    try { $f = [IO.Path]::GetFullPath($fichier) } catch { return $false }
    if (-not (Test-Path $f -PathType Leaf) -or $f -notmatch '(?i)\.(mp3|wav|ogg|m4a)$' -or (Test-CheminSecret $f) -or (Get-Item $f).Length -gt 8MB) { Write-Journal -Action 'Discord vocal' -Resultat 'refusé : fichier audio invalide'; return $false }
    Send-DiscordSortant @{ type = 'vocal'; canal = $canal; fichier = $f }
    $true
}

# ---------- « Test d'alerte » : UN message dans le salon système qui mentionne Liam (@moi) ; 3 tests par heure au plus ----------
$script:TestAlerteMax = 3
function Invoke-TestAlerteDiscord {
    # @{ ok; texte }. Un seul message, aucune relance. Faux (poliment) si le pont ne tourne pas, si DISCORD_USER_ID manque ou si la limite horaire est atteinte.
    $c = Get-DiscordConfig; $uid = "$([Environment]::GetEnvironmentVariable('DISCORD_USER_ID', 'Process'))".Trim()
    if (-not $script:DiscordPumpActif -or -not $c.actif) { return @{ ok = $false; texte = "Discord n'est pas actif, monsieur : je ne peux pas envoyer le test." } }
    if ($uid -notmatch '^\d{15,25}$') { return @{ ok = $false; texte = "Je n'ai pas votre identifiant Discord (DISCORD_USER_ID dans .env), monsieur." } }
    $canal = $(if ($c.salons.ContainsKey('systeme')) { 'systeme' } elseif ($c.salons.ContainsKey('jarvis')) { 'jarvis' } else { '' })
    if (-not $canal) { return @{ ok = $false; texte = "Je ne trouve aucun salon Discord pour le test, monsieur." } }
    $o = Read-JsonMemoire 'discord-test-alerte.json'; $now = Get-Date
    $recents = @(); if ($o -and $o.envoyes) { foreach ($x in @($o.envoyes)) { $d = [datetime]::MinValue; if ([datetime]::TryParse("$x", [Globalization.CultureInfo]::InvariantCulture, [Globalization.DateTimeStyles]::RoundtripKind, [ref]$d) -and ($now - $d).TotalHours -lt 1) { $recents += $d.ToString('o') } } }
    if ($recents.Count -ge $script:TestAlerteMax) { Write-Journal -Action "Test d'alerte Discord" -Resultat "refusé : $($script:TestAlerteMax) tests par heure atteints"; return @{ ok = $false; texte = "J'ai déjà envoyé $($script:TestAlerteMax) tests d'alerte cette heure, monsieur ; patientez un peu." } }
    $recents += $now.ToString('o'); Save-JsonMemoire 'discord-test-alerte.json' ([ordered]@{ envoyes = $recents })
    Send-DiscordSortant @{ type = 'message'; canal = $canal; texte = ([string][char]0x26A0 + [string][char]0xFE0F + " Test d'alerte, monsieur."); mention = $uid; reply_to = '' }
    Write-Journal -Action "Test d'alerte Discord" -Resultat "envoyé dans « $canal » ($($recents.Count) sur $($script:TestAlerteMax) cette heure)"
    @{ ok = $true; texte = "Test d'alerte envoyé dans le salon $(if ($canal -eq 'systeme') { 'système' } else { $canal }), monsieur." }
}

# ---------- « Réactive Discord » (après un arrêt d'urgence ou un abandon du pont) ----------
if (Get-Command Add-Action -ErrorAction SilentlyContinue) {
    Add-Action 'discord_reactiver' 1 'relancer le pont Discord' 'discord_reactiver() : relance le pont Discord (coupé par un arrêt d''urgence ou abandonné après des pannes)' {
        param($a)
        $script:PontCoupeUrgence = $false; $script:PontDesactive = $false; $script:PontPannes.Clear(); $script:PontProchainEssai = [datetime]::MinValue; $script:PontAnnonceFaite = $false
        if (Start-PontDiscord) { Rep $true (Get-Politesse 'fait_action' @{ x = 'le pont Discord est relancé' }) }
        else { Rep $false (Get-Politesse 'refus' @{ raison = $(if ((Get-DiscordConfig).actif) { 'le pont ne peut pas démarrer (voir le journal)' } else { 'discord_actif est à false dans config.json' }) }) }
    } { param($a) 'relancer le pont Discord' }
    Add-Action 'test_alerte' 1 'envoyer un test d''alerte sur Discord' 'test_alerte() : envoie UN message de test dans le salon système de Discord, qui mentionne Liam (3 tests par heure au plus)' {
        param($a) $r = Invoke-TestAlerteDiscord; Rep $r.ok $r.texte
    } { param($a) 'envoyer un test d''alerte sur Discord' }
}
if ($P -and $FIN -and (Get-Command New-PlanRapide -ErrorAction SilentlyContinue) -and $script:ReglesRapides) {
    $script:ReglesRapides = @(@{ nom = 'test_alerte'; re = "$P(?:(?:fais|lance|envoie)(?: moi)? (?:un |le )?)?(?:test (?:d'|de l')?alertes?|teste (?:l'|les )?alertes?)$FIN"
        build = { param($m, $o, $n) New-PlanRapide '' @(Act 'test_alerte') { param($r) "$($r[0].texte)" } 'test_alerte' } }, @{ nom = 'discord_reactiver'; re = "$P(?:reactive|rallume)(?: moi)? (?:le )?(?:pont )?(?:de )?discord$FIN|$P(?:relance|redemarre|remets en marche)(?: moi)? (?:le )?pont(?: de)? discord$FIN"
        build = { param($m, $o, $n) New-PlanRapide '' @(Act 'discord_reactiver') { param($r) "$($r[0].texte)" } 'discord_reactiver' } }) + @($script:ReglesRapides)
}
