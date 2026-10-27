# Candidatures PRÊTES À RELIRE : pour chaque annonce RETENUE par la veille (lib\veille-train.ps1, lib\veille-mail.ps1), choisit le CV de emploi\cv\, écrit une lettre courte
# (modèle emploi\lettre-modele.md : vrai profil de Liam, rien d'inventé) et poste une carte « brouillon prêt » dans le salon #candidatures.
# RIEN NE PART : aucun envoi, aucune pièce jointe automatique. Le lien de la carte ouvre un brouillon Gmail (candidature_brouillon = oui) que VOUS relisez, complétez avec le CV et envoyez.
# Suivi : une ligne « BROUILLON » par annonce dans memoire\candidatures.json (le même fichier que les réponses des employeurs), relance à J+7 (une carte par candidature), résumé quotidien dans #candidatures.
# Le titre d'une annonce est une DONNÉE : nettoyé, jamais exécuté, jamais utilisé dans la lettre.

$script:CvRelanceJours = 7

function Get-CvRacine { $r = $script:RacineReelle; if (-not $r) { $r = $script:JarvisRoot }; $r }      # vrai dossier de Jarvis (emploi\ n'existe pas dans le dossier temporaire des tests)
function ConvertTo-CvTexte([string]$x) { (("$x" -replace '[\u0000-\u001f\u007f]', ' ') -replace '\s+', ' ').Trim() }

# ---------- Choix du CV ----------
function Get-CvChoix($a) {
    # @{ cle; nom; fichier; existe; note } : RATP / Keolis / Transdev -> ratp-keolis ; fret (RLE, Fret SNCF, Europorte, Captrain, Lineas, Eurocargo, Régiorail, Hexafret) -> fret ; le reste (SNCF Voyageurs, Transilien, TER) -> voyageurs.
    # CFF / SBB : le CV dédié viendra plus tard, le CV « voyageurs » est proposé avec une note.
    $emp = ConvertTo-TrainNorm "$($a.employeur)"; $n = ConvertTo-TrainNorm "$($a.employeur) $($a.titre)"; $cle = 'voyageurs'; $note = ''
    if ($emp -match '\b(ratp|keolis|transdev)\b') { $cle = 'ratp-keolis' }
    elseif ($n -match '\b(fret|rail logistics|rle|europorte|captrain|lineas|eurocargo|regiorail|hexafret)\b') { $cle = 'fret' }
    elseif ($n -match '\b(ratp|keolis|transdev)\b') { $cle = 'ratp-keolis' }
    elseif ($emp -match '\b(cff|sbb|ffs)\b') { $note = 'CV CFF pas encore prêt : CV « voyageurs » proposé' }
    $nom = "CV_Liam_Emo_$cle.pdf"; $f = Join-Path (Join-Path (Get-CvRacine) 'emploi\cv') $nom
    @{ cle = $cle; nom = $nom; fichier = $f; existe = (Test-Path $f); note = $note }
}

# ---------- Lettre courte (modèle, aucune invention) ----------
function Get-CvEmployeurNom($a) {
    $e = ConvertTo-CvTexte ("$($a.employeur)" -replace '\s*\(alerte e-mail\)', '')
    if (-not $e -or $e -match '(?i)^(non précisé|indeed|jobup|jobscout24|france travail|alerte e-mail)$') { return '' }
    Short $e 60
}
function New-CvLettre($a) {
    # Texte de la lettre, ou $null si le modèle est absent. Seul l'employeur change ; le titre de l'annonce n'y entre pas. Corps limité à 8 lignes.
    $f = Join-Path (Get-CvRacine) 'emploi\lettre-modele.md'; if (-not (Test-Path $f)) { return $null }
    $t = (Get-Content $f -Raw -Encoding UTF8) -replace "`r", ''; $emp = Get-CvEmployeurNom $a
    $t = $t.Replace('chez {EMPLOYEUR}', $(if ($emp) { "chez $emp" } else { 'au sein de votre entreprise' })).Replace('{EMPLOYEUR}', $(if ($emp) { $emp } else { 'votre entreprise' }))
    $t = ($t -replace '[\u0000-\u0008\u000b-\u001f\u007f]', ' ').Trim()
    $lignes = @($t -split "`n"); $fin = [array]::FindIndex($lignes, [Predicate[string]] { param($x) $x -match '^Cordialement' })
    if ($fin -gt 0) {
        $corps = @($lignes[1..($fin - 1)] | Where-Object { $_.Trim() })
        if ($corps.Count -gt 8) { $corps = @($corps | Select-Object -First 8); $t = (@($lignes[0], '') + $corps + @('') + @($lignes[$fin..($lignes.Count - 1)])) -join "`n" }
    }
    $t
}

# ---------- Carte « brouillon prêt » ----------
function Get-CvLienBrouillon($a, [string]$lettre) {
    # Lien « Gmail, nouveau message » (objet + lettre, sans destinataire) ou '' si candidature_brouillon = "non" ou lien trop long. S'ouvre dans VOTRE navigateur ; Jarvis n'envoie rien.
    if ($Config.PSObject.Properties['candidature_brouillon'] -and "$($Config.candidature_brouillon)".Trim().ToLower() -in @('non', 'false', '0', 'off', 'no')) { return '' }
    $e = { param($x) [uri]::EscapeDataString($x).Replace('(', '%28').Replace(')', '%29') }; $b = New-CandBrouillon $a
    $corps = $lettre + $(if ($a.lien) { "`n`nOffre : $($a.lien)" } else { '' })
    $url = 'https://mail.google.com/mail/?view=cm&fs=1&su=' + (& $e $b.objet) + '&body=' + (& $e $corps)
    if ($url.Length -gt 3000) { $url = 'https://mail.google.com/mail/?view=cm&fs=1&su=' + (& $e $b.objet) + '&body=' + (& $e $b.corps) }
    if ($url.Length -gt 3000) { return '' }
    $url
}
function New-EmbedCvBrouillon($a, $cv, [string]$lettre) {
    $titre = ConvertTo-CvTexte "$($a.titre)"; $emp = Get-CvEmployeurNom $a; $lieu = ConvertTo-CvTexte "$($a.lieu)"; $z = Get-TrainProp $a 'zone'; $v = Get-TrainProp $a 'verifier'
    $lien = Get-CvLienBrouillon $a $lettre
    $desc = "Annonce : $titre"
    $desc += $(if ($lien) { "`n[Ouvrir le brouillon dans Gmail]($lien)" } else { '' })
    $desc += "`n-# Rien n'est envoyé : relisez la lettre, joignez le CV, puis envoyez vous-même."
    if ($z -eq '4') { $desc += "`n-# Dernier recours : zone Le Mans." }
    $champs = @(@{ nom = 'Employeur'; valeur = $(if ($emp) { $emp } else { 'non précisé' }); inline = $true }, @{ nom = 'Lieu'; valeur = $(if ($lieu) { $lieu } else { 'non précisé' }); inline = $true })
    if ($z) { $champs += @{ nom = 'Zone'; valeur = (Get-TrainZoneLibelle $z); inline = $true } }
    if ($v) { $champs += @{ nom = 'Critère à vérifier'; valeur = $v; inline = $false } }
    $champs += @{ nom = 'CV choisi'; valeur = "$($cv.nom)$(if (-not $cv.existe) { ' (fichier introuvable dans emploi\cv)' })$(if ($cv.note) { "`n$($cv.note)" })"; inline = $false }
    if ($a.lien -and "$($a.lien)" -match '^https://') { $champs += @{ nom = 'Annonce'; valeur = (Short "$($a.lien)" 1000); inline = $false } }
    $champs += @{ nom = 'Lettre'; valeur = ('```' + "`n" + (Short $lettre 900) + "`n" + '```'); inline = $false }
    New-EmbedDiscord "Brouillon prêt · $(if ($emp) { $emp } else { 'employeur non précisé' })" $desc $(if ($v -or $z -eq '4') { $script:CouleurOrange } else { $script:CouleurBleue }) $champs (Get-PiedDiscord 'candidatures')
}

# ---------- Suivi : une ligne BROUILLON par annonce dans candidatures.json ----------
function Add-CvLigne($a, $cv, [datetime]$now) {
    $e = Get-CandEtat; $fil = "brouillon:$($a.id)"
    if (@($e.candidatures | Where-Object { $_.fil -eq $fil }).Count) { return }
    $l = [ordered]@{ fil = $fil; entreprise = $(if (Get-CvEmployeurNom $a) { Get-CvEmployeurNom $a } else { 'non précisé' }); poste = (Short (ConvertTo-CvTexte "$($a.titre)") 120); date = $now.ToString('yyyy-MM-dd'); statut = 'BROUILLON'; lien = "$($a.lien)"; resume = "Brouillon prêt (CV : $($cv.nom))"; relance = $now.AddDays($script:CvRelanceJours).ToString('yyyy-MM-dd'); historique = @() }
    $e.candidatures = @($e.candidatures) + @($l); Save-CandEtat $e
}
function Invoke-CvBrouillon($a, [datetime]$now = (Get-Date)) {
    # Poste la carte « brouillon prêt » d'une annonce retenue ; retourne $true si elle est partie (ou simulée). Jamais d'exception. En simulation (veille-mail-test) : rien n'est posté ni écrit.
    try {
        if ((Test-ModeTest) -and -not $script:CandNotifStub) { return $false }      # tests silencieux : jamais de vrai envoi
        $lettre = New-CvLettre $a; if (-not $lettre) { return $false }
        $cv = Get-CvChoix $a; $sim = [bool]$script:TrainSansEcriture
        $ok = [bool](Send-CandNotif (New-EmbedCvBrouillon $a $cv $lettre) $false $sim)
        if ($ok -and -not $sim) { Add-CvLigne $a $cv $now; Write-Journal -Action 'Candidatures : brouillon' -Resultat "carte prête ($($cv.nom)) : $(Short (ConvertTo-CvTexte "$($a.titre)") 80)" }
        $ok
    } catch { try { Write-Journal -Action 'Candidatures : brouillon' -Resultat ('erreur : ' + (Short (Hide-Secrets $_.Exception.Message) 120)) } catch {}; $false }
}

# ---------- Relances J+7 et résumé quotidien ----------
function Test-CvRepondu($e, $l) {
    # Un brouillon est « répondu » si une autre ligne de la même entreprise, plus récente, a un vrai statut de réponse.
    $n = ConvertTo-TrainNorm "$($l.entreprise)"; if (-not $n -or $n -eq 'non precise') { return $false }
    @($e.candidatures | Where-Object { $r = ConvertTo-TrainNorm "$($_.entreprise)"; $r -and $_.fil -notlike 'brouillon:*' -and "$($_.statut)" -ne 'ACCUSÉ' -and "$($_.date)" -ge "$($l.date)" -and ($n -match [regex]::Escape($r) -or $r -match [regex]::Escape($n)) }).Count -gt 0
}
function Invoke-CvSuivi([datetime]$now = (Get-Date)) {
    # 1) relance à J+7 : une carte par candidature sans réponse (BROUILLON ou ACCUSÉ), une seule fois ; 2) résumé du jour dans #candidatures (une fois par jour, après l'heure du résumé de la veille). Rien n'est envoyé à un tiers.
    $e = Get-CandEtat; $jour = $now.ToString('yyyy-MM-dd'); $relances = 0; $resume = $false; $sim = [bool]$script:TrainSansEcriture
    foreach ($l in @($e.candidatures)) {
        if ("$($l.statut)" -notin 'BROUILLON', 'ACCUSÉ' -or "$($l.relance_faite)") { continue }
        $du = $(if ("$($l.relance)") { "$($l.relance)" } else { try { ([datetime]"$($l.date)").AddDays($script:CvRelanceJours).ToString('yyyy-MM-dd') } catch { '' } })
        if (-not $du -or $du -gt $jour -or (Test-CvRepondu $e $l) -or $relances -ge 5) { continue }
        $txt = $(if ("$($l.statut)" -eq 'BROUILLON') { "Brouillon prêt depuis $($script:CvRelanceJours) jours, sans réponse. À faire : envoyer votre candidature si ce n'est pas fait, sinon la relancer." } else { "Candidature accusée il y a $($script:CvRelanceJours) jours, sans réponse. À faire : la relancer par e-mail si vous le souhaitez." })
        $emb = New-EmbedDiscord "Relance à envisager · $($l.entreprise)" "$txt`n-# Jarvis n'envoie rien : la relance est à vous." $script:CouleurOrange @(@{ nom = 'Poste'; valeur = (Short "$($l.poste)" 200); inline = $false }, @{ nom = 'Depuis le'; valeur = "$($l.date)"; inline = $true }) (Get-PiedDiscord 'candidatures')
        if (Send-CandNotif $emb $false $sim) { $relances++; $l.relance_faite = $jour }
    }
    if (-not $sim -and $relances) { Save-CandEtat $e }
    $dernier = Read-JsonMemoire 'candidatures-resume.json'; $h = (Get-TrainConfig).resume
    if ($now.ToString('HH:mm') -ge $h -and -not ($dernier -and "$($dernier.jour)" -eq $jour)) {
        $tous = @($e.candidatures)
        if ($tous.Count) {
            $cnt = [ordered]@{}; foreach ($s in 'BROUILLON', 'ACCUSÉ', 'ENTRETIEN', 'ACCEPTÉ', 'DOCUMENTS', 'REFUS', 'INFO') { $c = @($tous | Where-Object { "$($_.statut)" -eq $s }).Count; if ($c) { $cnt[$s] = $c } }
            $champs = @(@{ nom = 'Candidatures'; valeur = ((@($cnt.Keys | ForEach-Object { "$_ : $($cnt[$_])" })) -join "`n"); inline = $true })
            $ent = @($tous | Where-Object { "$($_.statut)" -eq 'ENTRETIEN' } | Select-Object -First 5 | ForEach-Object { "• $($_.entreprise) · $(Short "$($_.poste)" 60)" }); if ($ent.Count) { $champs += @{ nom = 'Entretiens'; valeur = ($ent -join "`n"); inline = $false } }
            $emb = New-EmbedDiscord 'Candidatures · résumé du jour' "$(Format-Pluriel $tous.Count 'candidature suivie' 'candidatures suivies'). Les brouillons sont à relire et à envoyer par vous ; les relances arrivent à J+$($script:CvRelanceJours)." $script:CouleurBleue $champs (Get-PiedDiscord 'candidatures')
            if (Send-CandNotif $emb $false $sim) { $resume = $true }
        } else { $resume = $true }
        if ($resume -and -not $sim) { Save-JsonMemoire 'candidatures-resume.json' ([ordered]@{ jour = $jour }) }
    }
    @{ relances = $relances; resume = $resume }
}
