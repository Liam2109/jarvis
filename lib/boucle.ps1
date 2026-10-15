# Traitement des entrées de la boucle principale (séparé de jarvis.ps1 pour pouvoir être testé).
$script:BriefingEnAttente = $false

function Invoke-Menace($e) {
    if ($e.cle -and (Get-Command Set-AlerteDite -ErrorAction SilentlyContinue)) { Set-AlerteDite $e.cle }          # dite UNE fois : pas de répétition avant 24 h
    Invoke-AvecContexteVoix 'alerte' { Invoke-MenaceCorps $e }
}
function Invoke-MenaceCorps($e) {
    $p = $e.menace
    Set-VisageEtat 'question'
    Parler "Alerte, monsieur. J'ai détecté un processus suspect : $($p.nom). Chemin : $($p.chemin). $($p.signature). Motif : $($p.raison)."
    $q = [pscustomobject]@{ type = 'mettre_en_quarantaine'; pid = $p.pid }
    $r = Invoke-UneAction $q "alerte automatique : $($p.nom)" "Je propose de le mettre en quarantaine, sans rien supprimer. Vous confirmez, monsieur ?"
    if ($r) { Parler $r.texte; return }
    if (Test-Stop) { return }
    $k = [pscustomobject]@{ type = 'tuer_processus'; pid = $p.pid }
    $r = Invoke-UneAction $k "alerte automatique : $($p.nom)" "Souhaitez-vous seulement que j'arrête le processus ? Vous confirmez, monsieur ?"
    if ($r) { Parler $r.texte } else { Write-Journal -Action "Alerte menace $($p.nom)" -Resultat 'laissé en place sur décision de Liam' }
}

function Invoke-CoffreDemarrage {
    # NON BLOQUANT : la fenêtre de déverrouillage est un processus séparé ; Jarvis le dit UNE seule fois et continue sans accès aux mots de passe.
    $s = Initialize-Coffre
    Write-Journal -Action 'Coffre Bitwarden' -Resultat "état au démarrage : $s"
    if ($s -in 'locked', 'unauthenticated' -and $Config.coffre_au_demarrage) {
        if (-not $script:CoffreAnnonce) { $script:CoffreAnnonce = $true; Parler 'Le coffre est verrouillé, monsieur.' }
        [void](Start-CoffreDialogue $s)
    }
}

function Invoke-Entree($e) {
    $script:DiagId = 0; $script:DiagRecuMs = $(if ($e.recu_ms) { [int64]$e.recu_ms } else { 0 })
    if ($e.src -ne 'systeme' -and (Get-Command New-DiagSaisie -ErrorAction SilentlyContinue)) {
        $script:DiagId = $(if ($e.diag) { [int]$e.diag } else { New-DiagSaisie "$($e.texte)" "$($e.src)" })      # diagnostic : une ligne par phrase / ordre
    }
    # SOURDINE : aucune commande n'est exécutée (ni vocale, ni écrite). Les alertes système sont gardées et traitées à la réactivation.
    if ($script:Actif -eq $false) {
        if ($e.src -eq 'systeme') { Write-Journal -Action 'Alerte gardée en silence (sourdine)' -Resultat "$($e.texte)" }
        elseif ($e.src -in 'clavier', 'visage') { Set-DiagOrdre 'sourdine : réponse écrite seulement, aucune action exécutée'; Invoke-OrdreSourdine "$($e.texte)" }     # ordre écrit : réponse écrite seulement, AUCUNE action
        else { Set-DiagOrdre 'non exécuté : sourdine'; Write-Journal -Ordre "$($e.texte)" -Action 'Ordre IGNORÉ (sourdine)' -Resultat "refus : source $($e.src)" }
        return
    }
    if ($e.src -eq 'systeme') {
        if ($e.menace) { Invoke-Menace $e }
        elseif ($e.marche) { Invoke-AlerteMarche $e }
        elseif ($e.texte -like '[[]coffre] deverrouille') { $script:CoffreAnnonce = $false; Invoke-AvecContexteVoix 'reponse' { Parler 'Coffre déverrouillé, monsieur.' } }
        elseif ($e.texte -like '[[]coffre] echec') { Invoke-AvecContexteVoix 'reponse' { Parler 'Le déverrouillage du coffre a échoué, monsieur.' } }
        elseif ($e.texte -like '[[]defender]*') {
            # Fin d'une analyse demandée par Liam : dite (réponse à son ordre), ou gardée en silence pour le résumé en mode jeu
            $txt = ($e.texte -replace '^\[defender\]\s*', '')
            if ($script:ModeJeu -eq $true -and $txt -like 'menaces*') { $script:Retenu.Add(@{ type = 'alerte'; texte = "Analyse Defender : $txt"; heure = (Get-Date).ToString('HH:mm'); grave = $true }) }
            Invoke-AvecContexteVoix 'reponse' { Parler ("Analyse Defender terminée, monsieur. " + $txt) }
            Write-Journal -Action 'Analyse Defender terminée' -Resultat $e.texte
        }
        return
    }
    if ($script:ModeJeu -eq $true -and $e.src -eq 'voix' -and (Get-Command Test-OrdreAutoriseModeJeu -ErrorAction SilentlyContinue) -and -not (Test-OrdreAutoriseModeJeu "$($e.texte)")) {
        Set-DiagOrdre 'non exécuté : mode jeu (seuls « mode jeu off » et « sourdine » restent permis par la voix)'
        Write-Journal -Ordre "$($e.texte)" -Action 'Ordre vocal IGNORÉ (mode jeu)' -Resultat 'Jarvis ne réagit qu''à « mode jeu off » et « sourdine » pendant un jeu'
        return
    }
    if ($e.texte -match '(?i)^\W*(jarvis\W+)?(quitte|éteins.toi|ferme.toi|au revoir|à bientôt|arrête.toi complètement)\W*$') { $script:Quitter = $true; Invoke-AvecContexteVoix 'reponse' { Parler "À bientôt, monsieur." }; return }
    $script:OrdreSuivi = [bool]$e.suivi      # phrase venue de la fenêtre de SUITE de conversation (sans « Jarvis ») : filtrée dans Invoke-OrdreCorps
    try { Invoke-Ordre $e.texte } finally { $script:OrdreSuivi = $false }
}
