# Jarvis - point d'entrée.   Usage : jarvis.ps1 [commande] [texte]
#   (rien)          démarre Jarvis (briefing, puis écoute continue)
#   say "texte"     Jarvis prononce le texte
#   ordre "texte"   exécute un ordre écrit (comme s'il était dicté)
#   briefing        salutation + to-do + état du business
#   test            vérifie journal, voix, site, clés, cerveau
#   resume          génère le résumé du jour
#   micro [nom]     teste le micro : liste les entrées, niveau en direct et « J'ai entendu : ... » (20 s, aucune action)
#   mots [nom]      diagnostic du mot d'éveil (60 s) : texte brut reconnu par phrase + déclenché ou non, mot par mot (aucune action)
#   env-pousser     chiffre .env (mot de passe demandé, masqué) -> .env.chiffre, le commite SEUL et affiche « git push » (vous poussez vous-même)
#   discord-apercu  écrit memoire\apercu-discord.html : aperçu des messages Discord (données fictives, rien n'est envoyé)
#   discord-diag    liste les salons textuels que le bot Discord voit (noms et permissions seulement) et le mot-clé reconnu
#   avtest          UN appel Alpha Vantage (recherche « thales ») pour trouver les symboles de Paris à mettre dans config.json
#   priorite        priorité des ressources demandée / effective, mémoire du PC, modèle Ollama détecté (aucun téléchargement)
#   ecoute          une écoute ponctuelle (mot d'activation) puis journalise l'ordre
param([Parameter(Position = 0)][string]$Commande = 'run', [Parameter(Position = 1, ValueFromRemainingArguments)][string[]]$Reste, [string]$ReponseTest, [switch]$SansCoffre)
$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot
$Texte = ($Reste -join ' ').Trim()
. (Join-Path $Root 'lib\journal.ps1')
if (-not (Test-Path (Join-Path $Root '.env')) -and (Test-Path (Join-Path $Root '.env.chiffre'))) {      # premier démarrage (serveur) : .env est recréé depuis .env.chiffre (mot de passe protégé par DPAPI, voir installer-serveur.ps1)
    try { . (Join-Path $Root 'lib\env-chiffre.ps1'); $rEnv = Initialize-EnvDepuisChiffre $Root; if ($rEnv.statut -ne 'rien') { Write-Journal -Action 'Clés (.env)' -Resultat ".env : $($rEnv.statut) $($rEnv.raison)" } } catch { }
}
Import-JarvisEnv
$Config = Import-ConfigJarvis      # config.json + config.local.json (réglages de cette machine)
$script:ReponseTest = $ReponseTest   # crochet de test : réponse automatique aux confirmations
. (Join-Path $Root 'lib\voix.ps1')
. (Join-Path $Root 'lib\business.ps1')
. (Join-Path $Root 'lib\permissions.ps1')
. (Join-Path $Root 'lib\actions.ps1')
. (Join-Path $Root 'lib\coffre.ps1')
. (Join-Path $Root 'lib\entrees.ps1')
. (Join-Path $Root 'lib\ecrans.ps1')
. (Join-Path $Root 'lib\tableau.ps1')
. (Join-Path $Root 'lib\visage.ps1')
. (Join-Path $Root 'lib\sons.ps1')
. (Join-Path $Root 'lib\raccourcis.ps1')
. (Join-Path $Root 'lib\cerveau.ps1')
. (Join-Path $Root 'lib\cerveau-local.ps1')
. (Join-Path $Root 'lib\veille.ps1')
. (Join-Path $Root 'lib\memoire.ps1')
. (Join-Path $Root 'lib\rapide.ps1')
. (Join-Path $Root 'lib\discretion.ps1')
. (Join-Path $Root 'lib\modejeu.ps1')
. (Join-Path $Root 'lib\competences.ps1')
. (Join-Path $Root 'lib\marche.ps1')
. (Join-Path $Root 'lib\priorite.ps1')
. (Join-Path $Root 'lib\comprehension.ps1')
. (Join-Path $Root 'lib\routeur.ps1')
. (Join-Path $Root 'lib\pc.ps1')
. (Join-Path $Root 'lib\bureau.ps1')
. (Join-Path $Root 'lib\salle-marche.ps1')
. (Join-Path $Root 'lib\matin.ps1')
. (Join-Path $Root 'lib\discord.ps1')
. (Join-Path $Root 'lib\boucle.ps1')
foreach ($f in (Get-ChildItem (Join-Path $Root 'lib\sources') -Filter '*.ps1' -ErrorAction SilentlyContinue | Where-Object { $_.Name -notlike '_*' })) { . $f.FullName }      # modules de sources de marché (aucune n'est active tant qu'elle n'est pas dans sources_validees)
Remove-Item $script:StopFlag, $script:ParleFlag -ErrorAction SilentlyContinue
if (-not ($Config.PSObject.Properties['priorite_cpu_basse'] -and $Config.priorite_cpu_basse -eq $false)) { try { (Get-Process -Id $PID).PriorityClass = 'BelowNormal' } catch {} }      # Jarvis ne ralentit jamais le reste du PC
Set-FlagModeJeu $false
[void](Import-Competences)      # compétences personnelles : lib\competences\*.ps1

switch ($Commande.ToLower()) {
    'say'      { if (-not $Texte) { Write-Host 'Usage : jarvis.ps1 say "texte"'; return }; Invoke-AvecContexteVoix 'reponse' { Parler $Texte } }
    'ordre'    { if (-not $Texte) { Write-Host 'Usage : jarvis.ps1 ordre "texte"'; return }; Invoke-Ordre $Texte }
    'briefing' { Invoke-Briefing }
    { $_ -in 'micro', 'mots' } {
        # Test du micro : AUCUNE action n'est exécutée. Sans argument, utilise micro_nom de config.json (sinon le micro par défaut de Windows).
        # « mots » = même test en mode diagnostic : texte brut reconnu + verdict mot par mot (60 s) pour affiner mot_activation_variantes.
        $py = Join-Path $Root 'voix\ecoute.py'
        Write-Host 'Entrées audio disponibles (index, nom, fréquence) :'
        & python -I $py --liste 2>$null
        $mc = Get-MicroConfig; $nom = if ($Texte) { $Texte } else { $mc.nom }
        Write-Host ("`nMicro testé : " + $(if ($nom) { $nom } else { '(micro par défaut de Windows)' }) + "   — pour un autre : jarvis.ps1 micro Arctis")
        $diag = ($Commande.ToLower() -eq 'mots')
        $a = @('-I', '-u', $py, '--test-micro', $(if ($diag) { '60' } else { '20' }), '--seuil', [string]::Format([Globalization.CultureInfo]::InvariantCulture, '{0}', $mc.seuil)); if ($nom) { $a += @('--micro', $nom) }
        if ($mc.variantes.Count) { $a += @('--variantes', ($mc.variantes -join ',')) }
        $a += @('--moteur', $mc.moteur, '--whisper-modele', $mc.whisper_modele, '--whisper-peripherique', $mc.whisper_peripherique, '--fenetre', [string]$mc.fenetre); if ($mc.modele_chemin) { $a += @('--modele-chemin', $mc.modele_chemin) }
        Write-Host ("Moteur de reconnaissance (config.json, moteur_voix) : " + $mc.moteur + $(if ($mc.moteur -eq 'faster-whisper') { " ($($mc.whisper_modele), $($mc.whisper_peripherique)) — repli automatique sur Vosk si le moteur ou le modèle manque" }) + "   — pour comparer : changez moteur_voix et relancez cette commande")
        if ($diag) { $a += '--detail' }
        & python @a
        Write-Host "`nSi le niveau reste à 0 : mauvais micro (mettez son nom dans config.json, clé « micro_nom ») ou micro coupé dans Windows."
    }
    'env-pousser' { & (Join-Path $Root 'env-chiffrer.ps1') -Commit }      # LE geste quand vous changez une clé : chiffre .env, commit de .env.chiffre SEUL, puis la commande « git push » à lancer vous-même
    'discord-apercu' {    # écrit memoire\apercu-discord.html : chaque modèle de message Discord avec des données fictives (rien n'est envoyé à Discord)
        $f = New-ApercuDiscord; Write-Host "Aperçu écrit : $f"; Write-Host "Ouvrez-le dans votre navigateur (double-clic). Données fictives ; style actuel : $(Get-DiscordStyle)."
    }
    'discord-diag' {      # lit les NOMS des salons textuels que le bot voit et ses permissions dessus (aucun contenu, aucun identifiant, aucun secret) puis quitte
        $d = Join-Path $env:TEMP 'jarvis-discord-diag'; New-Item -ItemType Directory $d -Force | Out-Null
        & python -I -u (Join-Path $Root 'pont-discord\pont.py') --echange $d --config (Get-ConfigPath) --diagnostic 2>&1 | ForEach-Object { Write-Host (Hide-Secrets "$_") }
        Remove-Item $d -Recurse -Force -ErrorAction SilentlyContinue
    }
    'avtest'   { Invoke-AvTest | ForEach-Object { Write-Host $_ } }       # UN seul appel Alpha Vantage (SYMBOL_SEARCH) : quels symboles pour Paris ? Aucune clé affichée.
    'priorite' { Get-RapportPriorite | ForEach-Object { Write-Host $_ } }     # état de la priorité des ressources et modèle détecté (rien n'est téléchargé)
    'resume'   { Update-Resume; Write-Journal -Action 'Résumé quotidien généré' -Resultat 'ok' }
    'ecoute'   {
        $o = Ecouter-Ordre
        if (-not $o) { Write-Host '(rien entendu, saisie clavier)'; $o = Lire-Clavier }
        Write-Journal -Ordre $o -Action 'Ordre reçu' -Resultat 'ok (non exécuté dans ce mode)'
        Dire 'bien'
    }
    'test'     {
        Write-Journal -Ordre 'test' -Action 'Auto-test' -Resultat 'début'
        Write-Host "Journal   : OK ($((Get-ChildItem (Join-Path $Root 'logs') -Filter 'journal-*.md' | Measure-Object).Count) fichier(s))"
        Dire 'bonjour'
        $s = Get-StatutSite; Write-Host ("Site      : " + $(if ($s.ok) { 'OK (200)' } else { "PROBLÈME (code $($s.code))" }))
        foreach ($k in 'STRIPE_RESTRICTED_KEY', 'SUPABASE_URL', 'SUPABASE_READ_KEY', 'JARVIS_STATS_TOKEN', 'DISCORD_BOT_TOKEN', 'DISCORD_USER_ID') { Write-Host ("{0,-22}: {1}" -f $k, $(if (Test-Cle $k) { 'renseignée' } else { 'VIDE' })) }
        $r = Invoke-Claude 'Réponds uniquement par {"ok":true}' 'test' 60
        Write-Host ("Cerveau   : " + $(if ($r -match 'ok') { 'OK (claude -p répond)' } else { 'PROBLÈME (claude -p ne répond pas)' }))
        $o = Test-Ollama; Write-Host ("Cerveau   : réglage « {0} » -> mode effectif « {1} » (Ollama : {2})" -f $(if ($Config.cerveau) { $Config.cerveau } else { 'hybride' }), (Get-ModeCerveau), $(if ($o.pret) { "prêt, modèle $((Get-OllamaConfig).modele)" } else { $o.raison }))
        Write-Host ("Actions   : {0} compétences chargées" -f $script:Actions.Count)
        Write-Journal -Ordre 'test' -Action 'Auto-test' -Resultat 'terminé'
    }
    default    {
        # Une seule instance : deux Jarvis se disputeraient les raccourcis, le micro et le port du tableau de bord.
        $pidFile = Join-Path $Root 'memoire\jarvis.pid'; $quitFlag = Join-Path $Root 'memoire\quitter.flag'
        if (Test-Path $pidFile) {
            try {
                $o = Get-Content $pidFile -Raw -Encoding UTF8 | ConvertFrom-Json
                $vivant = Get-CimInstance Win32_Process -Filter "ProcessId=$([int]$o.pid)" -ErrorAction SilentlyContinue
                if ($vivant -and $vivant.CommandLine -match 'jarvis\.ps1') { Write-Host "Jarvis tourne déjà (PID $($o.pid)). Arrêtez-le avec arreter.ps1."; Write-Journal -Action 'Démarrage refusé' -Resultat "Jarvis tourne déjà (PID $($o.pid))"; return }
            } catch {}
        }
        Remove-Item $quitFlag -ErrorAction SilentlyContinue
        Write-Journal -Action 'Démarrage de Jarvis' -Resultat $(if ($SansCoffre) { 'ok (lancé avec -SansCoffre : pas de fenêtre de déverrouillage au démarrage)' } else { 'ok' })
        $serveur = Test-ModeServeur      # mode serveur : ni HUD, ni voix, ni musique, ni raccourcis, ni coffre ; micro seulement s'il y en a un ; Discord actif
        if (-not $serveur) { Start-Visage } else { Write-Journal -Action 'Mode serveur' -Resultat "actif : aucune fenêtre, aucune voix, aucun raccourci ; micro $(if (Get-MicroServeur) { 'détecté' } else { 'absent' }) ; Discord $(if ($Config.PSObject.Properties['discord_actif'] -and $Config.discord_actif -eq $true) { 'actif' } else { 'INACTIF (discord_actif)' })" }
        @{ pid = $PID; edge = $script:EdgePid; demarre = (Get-Date).ToString('o') } | ConvertTo-Json | Set-Content $pidFile -Encoding UTF8
        if ($serveur) { $problemes = @(); $script:Actif = $true } else { $problemes = Initialize-Raccourcis }          # raccourcis globaux + état actif/sourdine mémorisé (serveur : toujours actif, aucun raccourci)
        Initialize-Memoire                          # session précédente interrompue ? elle sera résumée au démarrage
        try { [void](Initialize-BriefingMatin) } catch { Write-Journal -Action 'Briefing du matin' -Resultat "indisponible : $($_.Exception.Message)" }     # affiché au tableau dès le démarrage, SANS voix (dit à la première activation de la journée)
        [void](Start-VeilleFond)                    # processus de fond léger, sans voix : seulement si marche_actif = true (même en sourdine)
        [void](Start-PontDiscord)                   # pont Discord (processus séparé) : seulement si discord_actif = true ; identifiants manquants = désactivé poliment, sans planter
        if ($serveur) { if (Get-MicroServeur) { Start-Ecoute } }
        elseif ($script:Actif) { Start-Ecoute; Start-PrechauffageTts; $script:TtsPrechauffe = $true; if ((Get-VoixMoteur) -eq 'piper') { [void](Test-PiperPret) } }     # en sourdine : micro fermé, aucune synthèse ; tout démarre à Alt + +
        try {
            if ($serveur) {
                Write-Journal -Action 'Mode serveur' -Resultat 'démarrage silencieux : pas de musique, pas de briefing vocal, pas de coffre'
            } elseif ($script:Actif) {
                Start-MusiqueDemarrage                                  # la musique commence à volume normal...
                $t = (Get-Date).AddMilliseconds(900); while ((Get-Date) -lt $t) { Invoke-Pump; Start-Sleep -Milliseconds 40 }
                Invoke-BriefingMatinDire                                # ...puis Jarvis parle par-dessus (ducking) — une seule fois par jour, à la première activation ; sinon texte au tableau
                Start-Ambiance
                Dire 'ordres'                                           # (en mode discret, « À vos ordres » est écrit, pas dit)
                foreach ($pb in $problemes) { Parler "Attention monsieur : $pb." }
                if ($script:AvertissementToucheSeule) { Parler "Attention monsieur : la touche seule est activée. Les touches plus et moins du pavé numérique sont réservées à Jarvis dans tous les programmes." }
            } else {
                Write-Journal -Action 'Briefing différé' -Resultat 'Jarvis démarre en sourdine (muet, sourd, sans son) ; briefing affiché au tableau, dit à la première activation (Alt + +) de la journée'
            }
            if (-not $SansCoffre -and -not $serveur -and $script:Actif) { Invoke-CoffreDemarrage }      # jamais de fenêtre en sourdine
            $dernierResume = ''; $dernierCoeur = Get-Date; Save-HeureArret
            while (-not $script:Quitter) {
                Invoke-Pump
                if (Test-Path $quitFlag) { Remove-Item $quitFlag -ErrorAction SilentlyContinue; Write-Journal -Action 'Arrêt demandé' -Resultat 'par arreter.ps1'; $script:Quitter = $true; break }
                if (Test-Stop) {
                    Invoke-ArretUrgence
                    Start-Sleep -Milliseconds 700
                    Remove-Item $script:StopFlag -ErrorAction SilentlyContinue
                    Invoke-AvecContexteVoix 'reponse' { Parler "Arrêt immédiat, monsieur. Tout est coupé." }
                    continue
                }
                if ($script:BriefingEnAttente -and $script:Actif) { Invoke-BriefingMatinDire; Invoke-AvecContexteVoix 'reponse' { Parler (Get-PhraseReveil) }; continue }
                $e = Get-Entree
                if ($e) { Invoke-Entree $e; continue }
                $dm = Get-OrdreDiscord                                   # ordre écrit reçu par Discord (Liam seul, salons listés) : traité comme un ordre, réponse écrite
                if ($dm) { Invoke-OrdreDiscordEntree $dm; continue }
                Update-Priorite                                          # priorité des ressources (retombe à « normal » en mode jeu / sourdine)
                Update-Marche                                            # relevés locaux de la veille de fond : panneau Marché, alertes, seuils (aucun réseau ici)
                Update-PontDiscord                                       # redémarre le pont Discord s'il a planté (journal d'erreurs, délais croissants)
                Update-Discord                                           # alertes regroupées et briefing planifié sur Discord (tout est désactivé par défaut)
                if (((Get-Date) - $dernierCoeur).TotalMinutes -ge 5) { $dernierCoeur = Get-Date; Save-HeureArret }      # « dernière activité » (si Jarvis est arrêté de force)
                Update-ModeJeu                                           # jeu / plein écran / heures : lecture seule du premier plan, toutes les 3 s
                if (-not $script:ModeJeu -and -not $serveur) { Update-Tableau }            # en mode jeu, Jarvis ne fait aucune lecture inutile (ni réseau, ni CPU)
                if ((Get-Date) -gt $script:ProchainScan) { $script:ProchainScan = (Get-Date).AddMinutes([int]$Config.scan_menaces_minutes); Invoke-ScanMenaces }
                $h = Get-Date -Format 'HH:mm'
                if ($h -ge $Config.resume_quotidien_heure -and $dernierResume -ne (Get-Date -Format 'yyyy-MM-dd')) { $dernierResume = Get-Date -Format 'yyyy-MM-dd'; [void](Invoke-ResumeSession 'soir'); Update-Resume; Write-Journal -Action 'Résumé quotidien généré' -Resultat 'ok' }
                Invoke-Rappels
                if ($script:LignesOrphelines) { Invoke-ResumeOrphelin }
                Start-Sleep -Milliseconds 150
            }
        } finally { Save-HeureArret; Stop-PontDiscord; Stop-VeilleFond; Stop-CoffreDialogue; Stop-Ollama; Close-Memoire; Stop-Musiques; Stop-Ecoute; Stop-Piper; Stop-Raccourcis; Stop-Visage; Remove-Item $pidFile -ErrorAction SilentlyContinue; Write-Journal -Action 'Arrêt de Jarvis' -Resultat 'ok' }
    }
}
