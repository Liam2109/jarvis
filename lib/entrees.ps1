# Entrées : écoute vocale continue (processus Python), clavier console, file d'ordres, arrêt d'urgence, tâches de fond.
$script:AccuseN = 0
$script:Entrees = New-Object System.Collections.Generic.Queue[object]   # @{ src; texte; entendu }
$script:Ecoute = $null; $script:EcouteTache = $null
$script:ClavierBuf = ''; $script:ClavierOk = $true
$script:AttendConfirm = $false
$script:Actif = $true                  # faux = sourdine (voir lib\raccourcis.ps1)
$script:DerniereAlerte = @{}
$script:ProchainScan = (Get-Date).AddMinutes(1)

function Get-ArgsEcoute([string]$py, [string]$MoteurForce = '') {
    # Arguments de l'écoute continue : micro, seuil et variantes du mot « Jarvis », fenêtre d'ordre, moteur (moteur_voix / moteur_voix_appareil), threads plafonnés, silence de fin, vocabulaire.
    # -MoteurForce « vosk » : mode jeu (reconnaissance légère sur CPU, le GPU n'est plus utilisé).
    $mc = if (Get-Command Get-MicroConfig -ErrorAction SilentlyContinue) { Get-MicroConfig } else { @{ silence_rapide = 0.7; adaptatif = $true; nom = ''; seuil = 0.65; variantes = @(); moteur = 'vosk'; fenetre = 8; modele_chemin = ''; whisper_modele = 'small'; whisper_peripherique = 'cpu'; threads = 3; vad = $true; silence = 1.5; silence_courte = 0.6; duree_max = 30 } }
    $moteur = if ($MoteurForce) { $MoteurForce } else { $mc.moteur }
    "-I -u `"$py`" --continu --seuil $([string]::Format([Globalization.CultureInfo]::InvariantCulture, '{0}', $mc.seuil))" + $(if ($mc.nom) { " --micro `"$($mc.nom)`"" } else { '' }) + $(if ($mc.variantes.Count) { " --variantes `"$($mc.variantes -join ',')`"" } else { '' }) +
        " --fenetre $($mc.fenetre) --moteur $moteur" + $(if ($mc.modele_chemin -and -not $MoteurForce) { " --modele-chemin `"$($mc.modele_chemin)`"" } else { '' }) +
        " --whisper-modele $($mc.whisper_modele) --whisper-peripherique $($mc.whisper_peripherique) --whisper-threads $($mc.threads) --whisper-vad $(if ($mc.vad) { 1 } else { 0 }) --silence-fin $([string]::Format([Globalization.CultureInfo]::InvariantCulture, '{0}', $mc.silence)) --silence-courte $([string]::Format([Globalization.CultureInfo]::InvariantCulture, '{0}', $mc.silence_courte)) --duree-max $([int]$mc.duree_max) --silence-rapide $([string]::Format([Globalization.CultureInfo]::InvariantCulture, '{0}', $mc.silence_rapide)) --adaptatif $(if ($mc.adaptatif) { 1 } else { 0 })" +
        $(if (Get-Command Update-VocabulaireVoix -ErrorAction SilentlyContinue) { $v = Update-VocabulaireVoix; if ($v) { " --vocabulaire `"$v`"" } else { '' } } else { '' }) +
        $(if (-not $MoteurForce -and (Get-Command Get-GrammaireVoix -ErrorAction SilentlyContinue)) { $g = Get-GrammaireVoix; if ($g) { " --grammaire `"$g`"" } else { '' } } else { '' }) +
        " --conversation-continue $(if ($Config.PSObject.Properties['conversation_continue'] -and $Config.conversation_continue -eq $false) { 0 } else { 1 })" +
        " --bruit-adaptatif $(if ($mc.bruit -eq $false) { 0 } else { 1 })"
}

$script:EcouteMoteurForce = ''        # « vosk » pendant le mode jeu : le moteur GPU est déchargé
function Start-Ecoute {
    if ((Test-ModeServeur) -and -not (Get-MicroServeur)) { $script:EcouteServeurRefusee = 1 + [int]$script:EcouteServeurRefusee; return }      # mode serveur sans micro voulu : ecoute.py n'est JAMAIS lancé (ni Whisper, ni Vosk, ni recherche de micro)
    if (Test-ModeTest) { return }                        # tests : jamais le micro
    if ($script:Ecoute -and -not $script:Ecoute.HasExited) { return }
    $py = Join-Path $script:VoixDir 'ecoute.py'
    $psi = New-Object Diagnostics.ProcessStartInfo 'python', (Get-ArgsEcoute $py $script:EcouteMoteurForce)
    $psi.UseShellExecute = $false; $psi.CreateNoWindow = $true
    $psi.RedirectStandardOutput = $true; $psi.RedirectStandardError = $true
    $psi.StandardOutputEncoding = [Text.Encoding]::UTF8
    try {
        $script:Ecoute = [Diagnostics.Process]::Start($psi)
        if (-not ($Config.PSObject.Properties['priorite_cpu_basse'] -and $Config.priorite_cpu_basse -eq $false)) { try { $script:Ecoute.PriorityClass = 'BelowNormal' } catch {} }      # l'écoute ne gêne jamais le reste du PC
        $script:EcouteTache = $script:Ecoute.StandardOutput.ReadLineAsync()
        $script:Ecoute.StandardError.ReadToEndAsync() | Out-Null
        Write-Journal -Action 'Écoute vocale démarrée' -Resultat "processus de reconnaissance lancé (moteur : $(if ($script:EcouteMoteurForce) { $script:EcouteMoteurForce + ' — mode jeu, sans GPU' } else { (Get-MicroConfig).moteur }))"
    } catch { Write-Journal -Action 'Écoute vocale' -Resultat "échec : $($_.Exception.Message)"; $script:Ecoute = $null }
}

function Stop-Ecoute { if ($script:Ecoute -and -not $script:Ecoute.HasExited) { try { $script:Ecoute.Kill() } catch {} } }

function Switch-EcouteMode([string]$mode) {
    # CYCLE DE VIE DU GPU. « jeu » : le processus de reconnaissance (modèle sur le GPU) est ARRÊTÉ -> VRAM libérée ; une reconnaissance légère Vosk sur CPU le remplace pour « mode jeu off » / « sourdine ».
    # « normal » : le moteur configuré est rechargé tout de suite (le chargement se fait en parallèle de « À vos ordres »). En sourdine : aucune écoute, donc aucun GPU (voir Set-Actif).
    $force = if ($mode -eq 'jeu') { 'vosk' } else { '' }
    if ($script:EcouteMoteurForce -eq $force) { return }
    $script:EcouteMoteurForce = $force
    if ($script:Actif -eq $false) { return }
    Stop-Ecoute; $script:Ecoute = $null; $script:EcouteTache = $null
    Start-Ecoute
    Write-Journal -Action 'Écoute vocale' -Resultat $(if ($force) { 'mode jeu : modèle déchargé du GPU, reconnaissance légère sur CPU' } else { 'fin du mode jeu : modèle rechargé' })
}
function Release-GpuModeles {
    # Sourdine / mode jeu : tout modèle que Jarvis a chargé en VRAM est déchargé (Ollama). La reconnaissance vocale est libérée par l'arrêt de son processus.
    if (Get-Command Invoke-OllamaDecharger -ErrorAction SilentlyContinue) { Invoke-OllamaDecharger }
}

function Invoke-ArretUrgence {
    Write-Journal -Ordre 'Jarvis stop' -Action "ARRÊT D'URGENCE : toute action en cours est coupée" -Resultat 'exécuté'
    $script:Entrees.Clear()
    if (Get-Command Invoke-ArretUrgenceDiscord -ErrorAction SilentlyContinue) { try { Invoke-ArretUrgenceDiscord } catch { Write-Journal -Action 'Pont Discord' -Resultat "arrêt d'urgence : $($_.Exception.Message)" } }      # le pont Discord est coupé aussi (« réactive Discord » pour le relancer)
    if ($script:JobDefender) { Stop-Job $script:JobDefender -ErrorAction SilentlyContinue; Remove-Job $script:JobDefender -Force -ErrorAction SilentlyContinue; $script:JobDefender = $null }
}

function Invoke-Pump {
    # Appelée en permanence (pendant l'attente, la parole, les commandes). Ne bloque jamais.
    # 0. Raccourcis clavier globaux (effet immédiat : sourdine, activation, tableau)
    if (Get-Command Invoke-PumpRaccourcis -ErrorAction SilentlyContinue) { Invoke-PumpRaccourcis }
    if (Get-Command Update-Sons -ErrorAction SilentlyContinue) { Update-Sons }   # ducking de la musique
    # 1. Écoute vocale
    if ($script:Ecoute -and $script:EcouteTache -and $script:EcouteTache.IsCompleted) {
        $ligne = $null; try { $ligne = $script:EcouteTache.Result } catch {}
        if ($null -eq $ligne -and $script:Ecoute.HasExited) { $script:Ecoute = $null; $script:EcouteTache = $null; Write-Journal -Action 'Écoute vocale' -Resultat 'processus terminé' }
        else {
            if ((Get-Command Read-LigneMicro -ErrorAction SilentlyContinue) -and $ligne -and (Read-LigneMicro $ligne)) { }
            elseif ($ligne -match '^(ORDRE|SUIVI):(.+)$') { $suiviLigne = ($Matches[1] -eq 'SUIVI'); $texteLigne = $Matches[2].Trim(); $script:AccuseN++; if ($Config.PSObject.Properties['accuse_sonore'] -and $Config.accuse_sonore -eq $true -and (Get-Command Invoke-Son -ErrorAction SilentlyContinue)) { Invoke-Son 'actif' }; $script:Entrees.Enqueue(@{ src = 'voix'; texte = $texteLigne; suivi = $suiviLigne; entendu = $false; diag = [int]$script:DiagDernierId; recu_ms = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds() }) }      # accusé : flash de l'orbe tout de suite (son seulement si accuse_sonore)
            elseif ($ligne -match '^ENTENDU:(.+)$') { $script:DernierEntendu = $Matches[1].Trim(); $script:DernierEntenduHeure = Get-Date; $script:Entrees.Enqueue(@{ src = 'voix'; texte = $Matches[1].Trim(); entendu = $true }) }
            elseif ($ligne -eq 'ACTIVE') { Set-VisageEtat 'ecoute'; $script:FenetreOrdreJusqua = (Get-Date).AddSeconds($(if (Get-Command Get-FenetreOrdreSecondes -ErrorAction SilentlyContinue) { Get-FenetreOrdreSecondes } else { 8 })) }      # « Jarvis » seul : l'ordre suivant est écouté sans répéter le mot
            if ($script:Ecoute) { $script:EcouteTache = $script:Ecoute.StandardOutput.ReadLineAsync() }
        }
    }
    # 2. Clavier console (si une console existe)
    if ($script:ClavierOk) {
        try {
            while ([Console]::KeyAvailable) {
                $k = [Console]::ReadKey($true)
                if ($k.Key -eq 'Enter') { if ($script:ClavierBuf.Trim()) { $script:Entrees.Enqueue(@{ src = 'clavier'; texte = $script:ClavierBuf.Trim(); entendu = $false }) }; $script:ClavierBuf = ''; Write-Host '' }
                elseif ($k.Key -eq 'Backspace') { if ($script:ClavierBuf.Length) { $script:ClavierBuf = $script:ClavierBuf.Substring(0, $script:ClavierBuf.Length - 1) } }
                elseif ($k.KeyChar -ne [char]0) { $script:ClavierBuf += $k.KeyChar; Write-Host $k.KeyChar -NoNewline }
            }
        } catch { $script:ClavierOk = $false }
    }
    # 3. Visage (fenêtre, bouton réduire, saisie, boutons oui/non)
    if (Get-Command Invoke-PumpVisage -ErrorAction SilentlyContinue) { Invoke-PumpVisage }
    if (Get-Command Invoke-PumpCoffre -ErrorAction SilentlyContinue) { Invoke-PumpCoffre }   # résultat de la fenêtre de déverrouillage (processus séparé)
    if (Get-Command Update-OllamaChargement -ErrorAction SilentlyContinue) { Update-OllamaChargement }      # fin du préchauffage du modèle local
    if ($script:VeilleProc -and (Get-Command Invoke-PumpVeille -ErrorAction SilentlyContinue)) { Invoke-PumpVeille }      # réveil par « réveille-toi Jarvis » ou double claquement (écoute de veille)
    if ($script:DiscordPumpActif -and (Get-Command Invoke-PumpDiscord -ErrorAction SilentlyContinue)) { Invoke-PumpDiscord }      # messages, réponses ✅/❌ et « stop » venant du pont Discord
    # 4. Fin d'analyse Defender
    if ($script:JobDefender -and $script:JobDefender.State -in 'Completed', 'Failed') {
        $j = $script:JobDefender; $script:JobDefender = $null
        $sortie = (Receive-Job $j -ErrorAction SilentlyContinue) -join '; '; $echec = $j.State -eq 'Failed'; Remove-Job $j -Force
        $script:Entrees.Enqueue(@{ src = 'systeme'; texte = "[defender] " + $(if ($echec) { 'échec' } elseif ($sortie) { "menaces : $sortie" } else { 'aucune menace' }); entendu = $false })
    }
}

function Get-Entree([int]$timeoutSec = 0, [switch]$AvecEntendu) {
    # Retourne la prochaine entrée ou $null. -AvecEntendu : accepte aussi les phrases sans mot d'activation (pour oui/non).
    $fin = if ($timeoutSec -gt 0) { (Get-Date).AddSeconds($timeoutSec) } else { Get-Date }
    do {
        Invoke-Pump
        while ($script:Entrees.Count -gt 0) {
            $e = $script:Entrees.Dequeue()
            if ($e.entendu -and -not $AvecEntendu) { continue }
            return $e
        }
        if (Test-Stop) { return $null }
        if ($AvecEntendu -and -not $script:Actif) { return $null }     # sourdine pendant une confirmation : on n'attend plus de réponse
        Start-Sleep -Milliseconds 100
    } while ((Get-Date) -lt $fin)
    return $null
}

function Get-DelaiConfirmation { $d = 8; if ($Config.PSObject.Properties['delai_confirmation_secondes']) { [void][int]::TryParse("$($Config.delai_confirmation_secondes)", [ref]$d) }; [math]::Max(3, [math]::Min(120, $d)) }
$script:DerniereConfirmation = ''
function Confirmer([string]$question) {
    # Pose la question à voix haute et attend un « oui » en langage naturel (oui / vas-y / fais-le / d'accord...) par la voix, le clavier ou un bouton.
    # « non / annule / laisse » = refus ; toute autre réponse = refus aussi ; aucune réponse dans le délai (8 s par défaut) = annulation polie.
    if ($script:CanalDiscord) { return (Confirmer-Discord $question) }      # ordre venu de Discord : la question et la réponse (✅/❌, oui/non) passent par Discord
    $script:DerniereConfirmation = ''
    $script:Entrees.Clear()
    Set-VisageEtat 'question'
    Parler $question
    if (Test-Stop) { return $false }
    $script:AttendConfirm = $true
    try {
        if ($script:ReponseTest) { $e = @{ texte = $script:ReponseTest } }   # crochet de test uniquement (commande "ordre -ReponseTest")
        else { $e = Get-Entree -timeoutSec (Get-DelaiConfirmation) -AvecEntendu }
    } finally { $script:AttendConfirm = $false }
    if (-not $e) { $script:DerniereConfirmation = 'delai'; Write-Journal -Action 'Confirmation' -Resultat 'aucune réponse : refusé'; Parler (Get-Politesse 'sans_reponse'); return $false }
    $script:DerniereConfirmation = Get-ReponseConfirmation "$($e.texte)"; $oui = ($script:DerniereConfirmation -eq 'oui')
    Write-Journal -Ordre $e.texte -Action 'Réponse à la confirmation' -Resultat $(if ($oui) { 'accepté' } else { 'refusé' })
    Start-Sleep -Milliseconds 600; Invoke-Pump; $script:Entrees.Clear()   # évite qu'un "Jarvis oui" soit rejoué comme nouvel ordre
    return $oui
}

function Invoke-ScanMenaces {
    # Surveillance périodique : alerte (une seule fois par exécutable) si un processus suspect apparaît.
    $s = @(Find-ProcessusSuspects)
    foreach ($p in $s) {
        if ((Get-Command Test-CheminIgnore -ErrorAction SilentlyContinue) -and (Test-CheminIgnore $p.chemin)) { continue }      # fichiers de Jarvis, sauvegardes, temporaires : jamais signalés
        $grave = [bool]($p.raison -match 'imite')                                                                              # grave = se fait passer pour un processus Windows
        $reg = Register-Alerte $p.chemin ("{0} : {1}" -f $p.nom, $p.raison) $grave
        if ($reg.nouvelle) { Write-Journal -Action 'Menace potentielle détectée' -Resultat ("{0} PID {1} | {2} | {3} | {4}" -f $p.nom, $p.pid, $p.chemin, $p.signature, $p.raison) }
        $dire = $reg.peut_dire -and (Test-AlerteVocale $grave)
        if ($script:ModeJeu -eq $true) {
            # mode jeu : une alerte grave est gardée en silence pour le résumé (une seule fois) ; les autres restent seulement dans le panneau
            if ($grave -and -not ($script:Retenu | Where-Object { $_.cle -eq $p.chemin })) { $script:Retenu.Add(@{ type = 'alerte'; texte = "$($p.nom) ($($p.raison))"; heure = (Get-Date).ToString('HH:mm'); grave = $true; cle = $p.chemin }) }
            continue
        }
        if ($dire) { $script:Entrees.Enqueue(@{ src = 'systeme'; texte = '[menace]'; entendu = $false; menace = $p; cle = $p.chemin }) }
    }
}
