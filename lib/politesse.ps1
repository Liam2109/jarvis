# Ton majordome : catalogue UNIQUE des phrases de Jarvis pour le contrôle du PC (actions faites, confirmations, refus, incompréhension, annulation...).
# Chaque situation a plusieurs variantes par ton ; Get-Politesse en choisit une au hasard, jamais la même deux fois de suite pour une situation.
# Réglage : config.json "ton_majordome" = "courtois" (défaut) | "neutre" | "sec".  Marques : {x} = texte fourni, {X} = idem avec majuscule initiale, {raison} = motif court.
# Règle : aucune phrase de contrôle du PC ne doit être écrite en dur ailleurs (tests\politesse.ps1 le vérifie).
$script:PolitesseDernier = @{}
$script:PolitesseFixe = $false          # tests : $true = toujours la 1re variante (résultats déterministes)

$script:PolitesseCat = @{
    # Action faite, avec un mot (x = « j'ouvre Chrome », « je verrouille le PC »...)
    fait_action = @{
        courtois = @('Très bien, monsieur, {x}.', 'Bien sûr, monsieur, {x}.', 'À votre service : {x}.', 'Entendu, monsieur, {x}.')
        neutre   = @('{X}.', 'Compris, {x}.')
        sec      = @('{X}.', 'Fait.')
    }
    # Action faite, sans commentaire
    fait = @{
        courtois = @("C'est fait.", 'Voilà, monsieur.', 'Fait, monsieur.', "Voilà, c'est fait, monsieur.", "Bien sûr, c'est fait.", "Très bien, c'est fait.")
        neutre   = @("C'est fait.", 'Terminé.')
        sec      = @('Fait.', 'OK.')
    }
    # Action silencieuse et évidente (volume, pause, musique...) : aucune formule polie
    silencieux = @{
        courtois = @('Voilà.', "C'est réglé.", 'Fait.')
        neutre   = @('Fait.', "C'est réglé.")
        sec      = @('Fait.', 'OK.')
    }
    # Demande de confirmation (niveau 2) ; x = ce qu'il faut faire, à l'infinitif
    confirmer = @{
        courtois = @('Souhaitez-vous vraiment {x}, monsieur ?', 'Dois-je vraiment {x}, monsieur ?', 'Vous confirmez : {x}, monsieur ?')
        neutre   = @('Confirmez-vous : {x} ?', 'Voulez-vous vraiment {x} ?')
        sec      = @('{X} ? Oui ou non.', 'Confirmer : {x} ?')
    }
    # Refus ou action impossible ; raison = motif court
    refus = @{
        courtois = @('Je crains de ne pas pouvoir, monsieur : {raison}.', 'Navré, monsieur, je ne peux pas : {raison}.', 'Impossible, monsieur : {raison}.')
        neutre   = @('Impossible : {raison}.', 'Je ne peux pas : {raison}.')
        sec      = @('Impossible : {raison}.', 'Non : {raison}.')
    }
    # Aucun résultat (fichier, application proposée...) ; x = ce qui était cherché
    rien_trouve = @{
        courtois = @('Je ne trouve rien pour {x}, monsieur.', 'Aucun résultat pour {x}, monsieur.', 'Désolé, monsieur, rien pour {x}.')
        neutre   = @('Aucun résultat pour {x}.', 'Rien trouvé pour {x}.')
        sec      = @('Rien pour {x}.', 'Aucun résultat.')
    }
    # Information à communiquer (x = le contenu)
    info = @{
        courtois = @('Voici, monsieur : {x}.', 'Je vous indique : {x}.', 'Monsieur, {x}.')
        neutre   = @('{X}.', 'Voici : {x}.')
        sec      = @('{X}.', '{X}.')
    }
    # Phrase non comprise
    incompris = @{
        courtois = @('Pardonnez-moi, pouvez-vous reformuler ?', "Je n'ai pas saisi, monsieur. Pouvez-vous répéter ?", 'Excusez-moi, monsieur, pouvez-vous reformuler ?')
        neutre   = @("Je n'ai pas compris. Pouvez-vous reformuler ?", 'Pouvez-vous répéter ?')
        sec      = @('Pas compris.', 'Répétez.')
    }
    # Annulation (réponse « non », ou plus rien à faire)
    annulation = @{
        courtois = @('Bien, je laisse tomber.', "Très bien, j'annule.", "Entendu, je n'y touche pas.")
        neutre   = @('Annulé.', "D'accord, j'annule.")
        sec      = @('Annulé.', 'Abandonné.')
    }
    # Aucune réponse à une confirmation (délai dépassé = annulation)
    sans_reponse = @{
        courtois = @("Sans réponse, monsieur, j'annule.", "Pas de réponse : j'annule, monsieur.", 'Faute de réponse, je laisse tomber.')
        neutre   = @("Pas de réponse, j'annule.", 'Délai dépassé, annulé.')
        sec      = @('Pas de réponse. Annulé.', 'Annulé.')
    }
    # Retour au calme (accusé de réception sans action)
    calme = @{
        courtois = @('Bien, monsieur.', 'Je reste à votre disposition.', "À votre service, monsieur.")
        neutre   = @('Bien.', "D'accord.")
        sec      = @('Bien.', 'OK.')
    }
    # Conversation courante (réponses locales instantanées, plusieurs formulations, jamais la même deux fois de suite)
    va_bien = @{
        courtois = @("Très bien, monsieur, je vous remercie. Et vous, comment allez-vous ?", "Au mieux, monsieur. Et de votre côté, la journée se passe bien ?", "Tout va bien de mon côté, monsieur. J'espère qu'il en va de même pour vous.", "En pleine forme, monsieur, si l'on peut le dire d'un assistant. Et vous ?", "Très bien, merci de demander, monsieur. Que puis-je faire pour vous ?")
        neutre   = @('Tout va bien, merci. Et vous ?', 'Très bien. Et vous ?')
        sec      = @('Ça va. Et vous ?', 'Bien.')
    }
    quoi_de_neuf = @{
        courtois = @("Rien de particulier à signaler, monsieur : tout est calme de mon côté. Et de votre côté ?", "Pas de grande nouvelle pour l'instant, monsieur. Souhaitez-vous que je fasse un point ?", "Tout est tranquille, monsieur. Si vous le voulez, je peux vous résumer l'état du SaaS ou de votre liste de tâches.")
        neutre   = @('Rien de particulier.', 'Tout est calme.')
        sec      = @('Rien à signaler.', 'RAS.')
    }
    que_fais_tu = @{
        courtois = @("Je veille, monsieur, en attendant vos instructions.", "Je me tiens prêt, monsieur : un ordre, une question, et je m'en occupe.", "Pas grand-chose pour l'instant, monsieur, je reste à votre écoute.")
        neutre   = @("J'attends vos instructions.", 'Je suis en veille active.')
        sec      = @("J'attends.", 'Rien.')
    }
    presence = @{
        courtois = @("Je suis là, monsieur.", "Toujours là, monsieur. Je vous écoute.", "Bien présent, monsieur. Que puis-je faire pour vous ?", "Je vous entends parfaitement, monsieur.")
        neutre   = @('Je suis là.', 'Je vous entends.')
        sec      = @('Là.', 'Oui.')
    }
    identite = @{
        courtois = @("Je suis Jarvis, monsieur, votre assistant personnel : je m'occupe de votre ordinateur, de vos rappels et de votre activité, à votre service.", "Jarvis, monsieur, pour vous servir. Votre assistant, sur cet ordinateur comme sur Discord.")
        neutre   = @('Je suis Jarvis, votre assistant.')
        sec      = @('Jarvis.')
    }
    bonne_nuit = @{
        courtois = @("Bonne nuit, monsieur. Reposez-vous bien.", "Bonne nuit, monsieur. À demain.", "Faites de beaux rêves, monsieur. Je veille sur le reste.", "Bonne nuit, monsieur.")
        neutre   = @('Bonne nuit.')
        sec      = @('Bonne nuit.')
    }
    bonne_journee = @{
        courtois = @("Merci, monsieur, à vous aussi.", "Bonne journée à vous également, monsieur.", "Je vous la souhaite excellente, monsieur.")
        neutre   = @('À vous aussi.')
        sec      = @('Merci, vous aussi.')
    }
    # Remerciement
    merci = @{
        courtois = @('Avec plaisir, monsieur.', "Je vous en prie, monsieur.", "C'est un plaisir, monsieur.")
        neutre   = @('Avec plaisir.', 'De rien.')
        sec      = @('De rien.', 'OK.')
    }
    # Énumération des capacités (x = cinq capacités) et suite
    liste_capacites = @{
        courtois = @('Je peux, monsieur : {x}.', 'À votre service, monsieur : {x}.')
        neutre   = @('Je peux : {x}.')
        sec      = @('{X}.')
    }
    suite_capacites = @{
        courtois = @('Dites « la suite » pour en savoir plus.', 'Dites « la suite » si vous le souhaitez.')
        neutre   = @('Dites « la suite » pour la suite.')
        sec      = @('« La suite » pour continuer.')
    }
    fin_liste = @{
        courtois = @("Voilà, monsieur, c'est tout pour le moment.", 'Vous avez fait le tour, monsieur.')
        neutre   = @("C'est tout pour le moment.")
        sec      = @('Fin de la liste.')
    }
    # Valeur de marché inconnue de la liste (memoire\marche-valeurs.json) ; x = le nom entendu
    valeur_inconnue = @{
        courtois = @("Je ne connais pas « {x} » dans votre liste de marché, monsieur.", "« {x} » n'est pas dans votre liste de marché, monsieur.", "Navré, monsieur, « {x} » ne figure pas dans votre liste de marché.")
        neutre   = @("« {x} » n'est pas dans la liste de marché.", "Valeur inconnue : « {x} ».")
        sec      = @("Inconnu : « {x} ».", "« {x} » absent de la liste.")
    }
    # Précision après un redémarrage ou une extinction programmés
    annulable = @{
        courtois = @("Dites « annule l'extinction » pour l'arrêter.", "Un mot, « annule l'extinction », et je l'arrête.")
        neutre   = @("Dites « annule l'extinction » pour l'arrêter.")
        sec      = @("« Annule l'extinction » pour l'arrêter.")
    }
    # Réveil par la phrase « réveille-toi Jarvis » ou le double claquement (lib\veille-reveil.ps1) : réponse BRÈVE
    reveil_ecoute = @{
        courtois = @('Je vous écoute.')
        neutre   = @('Je vous écoute.')
        sec      = @('Je vous écoute.')
    }
    # Accusé instantané (joué dès qu'une commande qui prend un instant est comprise) et phrase d'attente avant une réponse de Claude : phrases COURTES, déjà en cache vocal
    accuse = @{
        courtois = @('Très bien, monsieur.', 'Voilà.', 'Un instant, monsieur.')
        neutre   = @('Très bien.', 'Un instant.')
        sec      = @('Voilà.')
    }
    attente = @{
        courtois = @('Un instant, monsieur.', 'Je réfléchis, monsieur.', 'Un petit instant, monsieur.')
        neutre   = @('Un instant.', 'Je réfléchis.')
        sec      = @('Un instant.')
    }
    # Petites transitions naturelles (début de phrase dite) et test de voix (« test de voix » : 3 phrases courtes, avec chiffres, pourcentage, date et heure pour juger le rythme)
    transition = @{
        courtois = @('Voilà.', 'Bien sûr.', 'Très bien.', 'Entendu.', 'Avec plaisir, monsieur.')
        neutre   = @('Voilà.', 'Entendu.')
        sec      = @('Voilà.', 'Fait.')
    }
    test_voix_a = @{
        courtois = @('Bonsoir, monsieur. Tout est en ordre de mon côté.', 'Bonjour, monsieur. Je suis à votre disposition.', 'Me voici, monsieur. Voyons comment je sonne ce soir.')
        neutre   = @('Bonjour. Tout est en ordre.')
        sec      = @('Bonjour. Tout va bien.')
    }
    test_voix_b = @{
        courtois = @("Pour l'exemple, monsieur : le {x}, trois tâches sur quatre sont faites, soit 75 %, et une variation de +2,5 %.", "Un exemple, monsieur : nous sommes le {x}, avec 12 euros de plus et -1,5 % sur la semaine.")
        neutre   = @('Exemple : le {x}, 75 % de la liste est faite.')
        sec      = @('Exemple : le {x}, +2,5 %.')
    }
    test_voix_c = @{
        courtois = @("C'est tout pour ce test, monsieur. Je reste à votre service.", "Voilà pour le test, monsieur. Dites-moi si ce rythme vous convient.")
        neutre   = @("C'est tout pour ce test.")
        sec      = @('Test terminé.')
    }
    # Touche d'humour discrète, SEULEMENT dans les réponses écrites de Discord (lib\discord.ps1, réglage humour_pourcent) ; jamais sur une erreur, une alerte, la finance ni une action sensible. Jamais dite à voix haute.
    humour = @{
        courtois = @("Je n'ai pas de café à vous proposer, monsieur, mais ma diligence est servie à toute heure.",
                     "Si je pouvais hausser un sourcil, monsieur, je le ferais avec la plus grande élégance.",
                     "Je ne dors ni ne prends de vacances, monsieur : vous voilà bien gâté.",
                     "Je range, je classe, je ne juge pas, monsieur. Ou si peu.",
                     "Discrétion assurée, monsieur : je ne commente que lorsqu'on me le demande. Pour une fois, j'ai fait une exception.",
                     "Mon agenda est impeccable, monsieur ; c'est le vôtre qui m'inquiète un peu.",
                     "Je suis toujours là, monsieur, même quand vous ne regardez pas.",
                     "Sans bruit de plateau d'argent, comme il se doit.",
                     "Rien n'est trop petit pour mon attention, monsieur, pas même une to-do.",
                     "Un majordome sans humour serait un simple tiroir, monsieur ; j'essaie de m'en tenir à l'écart.")
        neutre   = @("Je ne dors jamais, c'est pratique.", "Aucun plateau d'argent n'a été abîmé.", "Toujours là, même quand vous ne regardez pas.", "Je range, je classe, je ne juge pas.")
        sec      = @()
    }
    # Rappel arrivé à échéance (x = le rappel)
    rappel = @{
        courtois = @('Rappel, monsieur : {x}', 'Pardon de vous interrompre, monsieur : {x}', 'Monsieur, un rappel : {x}')
        neutre   = @('Rappel : {x}')
        sec      = @('Rappel : {x}')
    }
}

function Get-TonMajordome {
    $t = ''
    if ($Config -and $Config.PSObject.Properties['ton_majordome']) { $t = "$($Config.ton_majordome)".Trim().ToLowerInvariant() }
    if ($t -in 'courtois', 'neutre', 'sec') { $t } else { 'courtois' }
}

function Get-VariantesPolitesse([string]$situation, [string]$ton = '') {
    if (-not $ton) { $ton = Get-TonMajordome }
    if (-not $script:PolitesseCat.ContainsKey($situation)) { return @() }
    @($script:PolitesseCat[$situation][$ton])
}

function Get-Politesse([string]$situation, [hashtable]$v = @{}) {
    # Une phrase de la situation, dans le ton configuré, jamais identique à la précédente de la même situation.
    $l = @(Get-VariantesPolitesse $situation)
    if (-not $l.Count) { return '' }
    $i = 0
    if (-not $script:PolitesseFixe -and $l.Count -gt 1) {
        $dernier = if ($script:PolitesseDernier.ContainsKey($situation)) { [int]$script:PolitesseDernier[$situation] } else { -1 }
        $choix = @(0..($l.Count - 1) | Where-Object { $_ -ne $dernier })
        $i = $choix | Get-Random
    }
    $script:PolitesseDernier[$situation] = $i
    $t = $l[$i]
    $texteX = "$($v['x'])".Trim(); $majX = if ($texteX) { $texteX.Substring(0, 1).ToUpperInvariant() + $texteX.Substring(1) } else { '' }      # (PowerShell ignore la casse des variables : noms distincts)
    $t = $t.Replace('{X}', $majX).Replace('{x}', $texteX).Replace('{raison}', "$($v['raison'])".Trim())
    $t
}

function Test-PhrasePolitesse([string]$situation, [string]$texte) {
    # $true si le texte est une des variantes (tous tons) de la situation, marques remplacées par n'importe quel texte.
    foreach ($ton in 'courtois', 'neutre', 'sec') {
        foreach ($m in (Get-VariantesPolitesse $situation $ton)) {
            $re = '^' + ([regex]::Escape($m) -replace '\\\{[xX]\}', '.+' -replace '\\\{raison\}', '.+') + '$'
            if ($texte -match $re) { return $true }
        }
    }
    $false
}

function Get-PolitessePrechauffe {
    # Phrases sans marque, ajoutées au cache des phrases fixes (voir $script:PhrasesPrechauffe dans voix.ps1).
    $r = @()
    foreach ($s in $script:PolitesseCat.Keys) { if ($s -eq 'humour') { continue }; foreach ($ton in 'courtois', 'neutre', 'sec') { foreach ($p in @($script:PolitesseCat[$s][$ton])) { if ($p -notmatch '\{') { $r += $p } } } }
    @($r | Select-Object -Unique)
}

function Get-RefusApp($r, [string]$nom) {
    # Refus pour une application (introuvable, protégée, hors liste blanche) — utilisé par pc.ps1 et par le chemin rapide.
    $raison = if ($r.interdit) { if ("$($r.raison)" -match 'liste blanche') { "$nom n'est pas autorisée" } else { "$nom est protégée" } } else { "je ne trouve pas $nom" }
    Get-Politesse 'refus' @{ raison = $raison }
}

function Get-ReponseConfirmation([string]$texte) {
    # Langage naturel : 'oui' | 'non' | 'autre'. « autre » est traité comme un refus (rien d'irréversible sans « oui » net).
    $t = "$texte".ToLowerInvariant().Normalize([Text.NormalizationForm]::FormD) -replace '\p{Mn}', ''
    $t = ($t -replace "[’‘`´]", "'" -replace '[\.,!?;]', ' ' -replace '-', ' ' -replace '\s+', ' ').Trim()
    if (-not $t) { return 'autre' }
    $non = "^(?:jarvis )?(?:non|nan|nope|negatif|annule|annulez|laisse|laissez|laisse tomber|laissez tomber|stop|surtout pas|pas maintenant|pas question|ne fais pas ca|ne le fais pas|oublie ca|finalement non|j'ai change d'avis|arrete)\b"
    if ($t -match $non) { return 'non' }
    $oui = "^(?:jarvis )?(?:oui|ouais|ouep|yep|yes|affirmatif|ok|okay|d'accord|dac|confirme|confirmez|confirmer|je confirme|vas y|allez y|vas-y|fais le|faites le|fais la|faites|fais ca|bien sur|volontiers|absolument|exactement|c'est bon|c'est ca|tout a fait|go)\b"
    if ($t -match $oui) { return 'oui' }
    'autre'
}
