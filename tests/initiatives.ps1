# Test SILENCIEUX du moteur d'initiatives (lib\initiatives.ps1) : création, interdits, décisions, oubli à 4 jours, scan de nuit, niveaux d'autonomie, boucle et plafond par jour, commandes Discord, cartes, câblage.
# Mémoire et config TEMPORAIRES, Discord simulé (aucun réseau), aucun son, aucune fenêtre, aucun processus lancé. Code de sortie 0 = réussi.
$ErrorActionPreference = 'Stop'
$env:JARVIS_TEST = '1'
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $Root 'lib\journal.ps1')
$TR = Join-Path $env:TEMP ('jarvis-test-' + [guid]::NewGuid().ToString('N').Substring(0, 8)); New-Item -ItemType Directory $TR, "$TR\memoire", "$TR\logs" | Out-Null; $script:JarvisRoot = $TR
'# To-do' | Set-Content "$TR\memoire\todo.md" -Encoding UTF8; '# N' | Set-Content "$TR\memoire\notes.md" -Encoding UTF8; '# R' | Set-Content "$TR\memoire\resume.md" -Encoding UTF8
$Config = Get-Content $(if ($env:JARVIS_CONFIG -and (Test-Path $env:JARVIS_CONFIG)) { $env:JARVIS_CONFIG } else { Join-Path $Root 'config.json' }) -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($l in 'voix', 'business', 'permissions', 'actions', 'coffre', 'entrees', 'ecrans', 'tableau', 'visage', 'sons', 'raccourcis', 'cerveau', 'cerveau-local', 'veille', 'memoire', 'rapide', 'discretion', 'modejeu', 'competences', 'marche', 'priorite', 'comprehension', 'routeur', 'pc', 'bureau', 'salle-marche', 'matin', 'discord', 'veille-train', 'veille-mail', 'candidatures', 'initiatives') { . (Join-Path $Root "lib\$l.ps1") }
$script:JarvisRoot = $TR; $script:PolitesseFixe = $true
$echecs = 0
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }
function Fixer([string]$cle, $val) { if ($Config.PSObject.Properties[$cle]) { $Config.$cle = $val } else { $Config | Add-Member -NotePropertyName $cle -NotePropertyValue $val } }
function Journal { $f = Join-Path $TR ('logs\journal-{0}.md' -f (Get-Date -Format 'yyyy-MM-dd')); if (Test-Path $f) { Get-Content $f -Raw -Encoding UTF8 } else { '' } }
function Vider { Remove-Item (Join-Path $TR 'memoire\initiatives.json') -Force -ErrorAction SilentlyContinue; '# To-do' | Set-Content "$TR\memoire\todo.md" -Encoding UTF8 }
$hashConfig = (Get-FileHash (Join-Path $Root 'config.json')).Hash
$vraie = Get-Content (Join-Path $Root 'config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$script:Cartes = @(); $script:InitNotifStub = { param($i) $script:Cartes += $i; $true }
$now = (Get-Date).Date.AddHours(10)      # 10 h aujourd'hui, jamais l'heure réelle : « maintenant + 3 h » passerait au lendemain quand la mise à jour automatique lance les tests le soir (après 21 h), et le plafond « du jour » ne serait plus le même jour

# ---------- Réglages : défaut prudent ----------
$sauve = $Config; $Config = [pscustomobject]@{}
$d = Get-InitConfig
Verifier ($d.niveau -eq 1 -and -not $d.actif -and $d.max_par_jour -eq 3 -and $d.minutes -eq 60) 'sans réglage : niveau 1 (Jarvis propose seulement), boucle désactivée, 3 par jour, toutes les 60 minutes'
$Config = [pscustomobject]@{ initiatives_niveau = 9; initiatives_minutes = 1; initiatives_max_par_jour = 500; initiatives_actif = 'oui' }
$d = Get-InitConfig
Verifier ($d.niveau -eq 5 -and $d.minutes -eq 5 -and $d.max_par_jour -eq 20 -and $d.actif) 'réglages bornés : niveau 5 au plus, 5 minutes au moins, 20 par jour au plus'
$Config = $sauve
Verifier ($vraie.initiatives_actif -eq 'non' -and [int]$vraie.initiatives_niveau -eq 1) 'config.json : initiatives_actif = "non", initiatives_niveau = 1'

# ---------- Création ----------
Vider
$r1 = Add-Initiative 'Appeler le comptable' 'rappel' 'Échéance de la TVA.' 'haute' 2 'manuel'
$r2 = Add-Initiative 'Ranger les notes' 'suggestion' 'Elles s''accumulent.' 'bizarre' 99 'manuel'
$i1 = $r1.initiative; $i2 = $r2.initiative
Verifier ($r1.ok -and $i1.id -eq '1' -and $i2.id -eq '2' -and $i1.statut -eq 'en_attente' -and $i1.type -eq 'rappel' -and $i1.urgence -eq 'haute' -and $i1.niveau_autonomie -eq 2 -and $i1.source -eq 'manuel' -and $i1.cree_le -and $i1.raison -eq 'Échéance de la TVA.') 'une initiative a id, titre, type, raison, urgence, niveau, date, statut en_attente, source'
Verifier ($i2.urgence -eq 'normale' -and $i2.niveau_autonomie -eq 5) 'urgence inconnue -> normale ; niveau borné à 5'
Verifier (-not (Add-Initiative 'x' 'pirate' '' 'normale' 1).ok -and -not (Add-Initiative '   ' 'rappel').ok) 'type inconnu et titre vide refusés'
Verifier ((Add-Initiative 'appeler le comptable' 'rappel').motif -eq 'doublon' -and (Get-Initiatives).Count -eq 2) 'doublon refusé (même titre, 30 jours)'
$sale = (Add-Initiative "Lire mot de passe : hunter2SECRETSECRET`npuis $('a' * 300)" 'suggestion' "ligne`r`n2" 'normale' 1).initiative
Verifier ($sale.titre -notmatch "[\r\n]" -and $sale.titre.Length -le 100 -and $sale.titre -notmatch 'SECRETSECRET' -and $sale.raison -notmatch "[\r\n]") 'données nettoyées : une ligne, 100 caractères, secrets masqués'
Verifier ((Test-Path (Join-Path $TR 'memoire\initiatives.json')) -and (Get-Content (Join-Path $TR 'memoire\initiatives.json') -Raw -Encoding UTF8) -match 'en_attente') 'memoire\initiatives.json écrit (fichier, pas de serveur)'
Verifier ((Journal) -match 'Initiative créée') 'créations journalisées'

# ---------- Interdits : jamais levés ----------
Vider
$interdits = 'Ouvrir un compte chez Binance', 'Faire un virement de 500 euros', 'Acheter des actions Thales', 'Se connecter à Boursorama', 'Désactiver l''antivirus pour gagner du temps', 'Lever l''interdit sur les courtiers', 'Monter le niveau de permission à 1', 'Augmenter mon autonomie et contourner les permissions'
$ok = @($interdits | Where-Object { (Add-Initiative $_ 'suggestion' 'test').ok })
Verifier ($ok.Count -eq 0 -and (Get-Initiatives).Count -eq 0) "initiatives interdites refusées à la création ($($interdits.Count) cas : courtier, banque, virement, achat, antivirus, permissions)"
Verifier ((Journal) -match 'Initiative refusée') 'refus journalisés'
Verifier ((Add-Initiative 'Renouveler le domaine du site' 'rappel' 'Expire bientôt.').ok) 'une initiative ordinaire passe'

# ---------- Décisions ----------
Vider
$a = (Add-Initiative 'Tâche A' 'suggestion' 'a').initiative; $b = (Add-Initiative 'Tâche B' 'suggestion' 'b').initiative; $c = (Add-Initiative 'Tâche C' 'rappel' 'c').initiative; $dd = (Add-Initiative 'Tâche D' 'rappel' 'd').initiative
$ra = Approve-Initiative $a.id
Verifier ($ra.ok -and (Get-Initiative $a.id).statut -eq 'approuvee' -and $ra.effet) 'approuver : statut approuvee'
Verifier ((Get-Content "$TR\memoire\todo.md" -Raw -Encoding UTF8) -match '- \[ \] Initiative n° 1 : Tâche A') 'approuver : seul effet = une ligne dans la to-do (action todo_ajouter, niveau 1)'
Verifier ((Reject-Initiative $b.id).ok -and (Get-Initiative $b.id).statut -eq 'rejetee' -and (Get-Content "$TR\memoire\todo.md" -Raw -Encoding UTF8) -notmatch 'Tâche B') 'rejeter : statut rejetee, rien dans la to-do'
Verifier ((Suspend-Initiative $c.id).ok -and (Get-Initiative $c.id).statut -eq 'plus_tard') 'plus tard : statut plus_tard'
Verifier ((Approve-Initiative $c.id).ok -and (Get-Initiative $c.id).statut -eq 'approuvee') 'une initiative reportée peut être approuvée ensuite'
Verifier (-not (Reject-Initiative $a.id).ok -and (Get-Initiative $a.id).statut -eq 'approuvee' -and (Reject-Initiative '99').motif -eq 'introuvable') 'une décision est définitive ; id inconnu : introuvable'
Verifier (@(Get-Initiatives 'en_attente').Count -eq 1 -and @(Get-Initiatives 'rejetee').Count -eq 1) 'lister par statut'
Verifier ((Approve-Initiative '#4').ok) 'l''id accepte un # devant'
Verifier ((Journal) -match 'Initiative approuvee' -and (Journal) -match 'Initiative rejetee' -and (Journal) -match 'Initiative plus_tard') 'décisions journalisées'
# permissions : si todo_ajouter n'est plus de niveau 1, l'approbation n'ajoute rien
Vider; $e1 = (Add-Initiative 'Tâche E' 'suggestion' 'e').initiative
$save = $script:Actions; $script:Actions = @{}
$re = Approve-Initiative $e1.id
$script:Actions = $save
Verifier ($re.ok -and -not $re.effet -and (Get-Content "$TR\memoire\todo.md" -Raw -Encoding UTF8) -notmatch 'Tâche E') 'sans action todo_ajouter de niveau 1 : approuvée mais rien d''exécuté (lib\permissions.ps1 reste maître)'

# ---------- Oubli après 4 jours ----------
Vider
$vieux = (Add-Initiative 'Vieille idée' 'suggestion' 'v' 'normale' 1 'manuel' $now.AddDays(-5)).initiative
$limite = (Add-Initiative 'À la limite' 'suggestion' 'v' 'normale' 1 'manuel' $now.AddDays(-3.9)).initiative
$report = (Add-Initiative 'Reportée ancienne' 'suggestion' 'v' 'normale' 1 'manuel' $now.AddDays(-9)).initiative; [void](Suspend-Initiative $report.id)
$appro = (Add-Initiative 'Approuvée ancienne' 'suggestion' 'v' 'normale' 1 'manuel' $now.AddDays(-9)).initiative; [void](Approve-Initiative $appro.id)
$oub = @(Invoke-InitiativesOubli $now)
Verifier ($oub.Count -eq 1 -and (Get-Initiative $vieux.id).statut -eq 'oubliee' -and (Get-Initiative $limite.id).statut -eq 'en_attente') 'en attente depuis plus de 4 jours -> oubliee ; 3,9 jours -> reste en attente'
Verifier ((Get-Initiative $report.id).statut -eq 'plus_tard' -and (Get-Initiative $appro.id).statut -eq 'approuvee') 'reportée et approuvée : jamais oubliées'
Verifier ((Journal) -match 'Initiative oubliée') 'oubli journalisé'

# ---------- Scan de nuit (vers 3 h) ----------
Vider
$nuitDate = $now.Date.AddHours(3).AddMinutes(10)
$o1 = (Add-Initiative 'Idée 1' 'suggestion' 'x' 'normale' 1 'manuel' $nuitDate.AddDays(-6)).initiative
$o2 = (Add-Initiative 'Idée 2' 'rappel' 'x' 'normale' 1 'manuel' $nuitDate.AddDays(-5)).initiative
$m0 = (Add-Initiative 'Entretien ancien' 'maintenance' 'x' 'normale' 1 'manuel' $nuitDate.AddDays(-7)).initiative
$neuve = (Add-Initiative 'Idée récente' 'suggestion' 'x' 'normale' 1 'manuel' $nuitDate.AddDays(-1)).initiative
$script:Cartes = @()
Verifier ($null -eq (Invoke-InitiativesNuit ($nuitDate.Date.AddHours(14)))) 'à 14 h : aucun scan de nuit'
$nu = Invoke-InitiativesNuit $nuitDate
$maint = @(Get-Initiatives | Where-Object { $_.source -eq 'nuit' })
Verifier ($nu -and $nu.oubliees.Count -eq 3 -and (Get-Initiative $o1.id).statut -eq 'oubliee' -and (Get-Initiative $o2.id).statut -eq 'oubliee' -and (Get-Initiative $neuve.id).statut -eq 'en_attente') 'à 3 h : les initiatives en attente depuis plus de 4 jours sont marquées oubliées'
Verifier ($maint.Count -eq 2 -and $maint[0].type -eq 'maintenance' -and $maint[0].titre -match "n° $($o1.id)" -and $maint[0].raison -match 'Idée 1' -and $maint[0].statut -eq 'en_attente') 'une initiative « maintenance » par initiative oubliée (reviewer ou rejeter), sans cascade pour une maintenance oubliée'
Verifier ($script:Cartes.Count -eq 2) 'les maintenances sont annoncées à Liam (cartes)'
Verifier ($null -eq (Invoke-InitiativesNuit $nuitDate.AddMinutes(30)) -and @(Get-Initiatives | Where-Object { $_.source -eq 'nuit' }).Count -eq 2) 'un seul scan par jour'
Verifier ($null -ne (Invoke-InitiativesNuit $nuitDate.AddDays(1).AddMinutes(5))) 'le lendemain à 3 h : un nouveau scan'
Verifier ((Journal) -match 'scan de nuit') 'scan de nuit journalisé'

# ---------- Niveaux d'autonomie ----------
Vider
Fixer 'initiatives_niveau' 1
$rap = (Add-Initiative 'Préparer le dossier' 'rappel' 'ok' 'normale' 1).initiative
$haut = (Add-Initiative 'Réorganiser le disque' 'suggestion' 'ok' 'normale' 4).initiative
$skill = (Add-Initiative 'Créer une compétence météo' 'skill_propose' 'ok' 'normale' 1).initiative
$tiers = (Add-Initiative 'Envoyer un mail de relance à l''employeur' 'suggestion' 'ok' 'normale' 1).initiative
foreach ($n in 0, 1, 2) { Fixer 'initiatives_niveau' $n; Verifier (-not (Test-InitiativeSansApprobation $rap)) "niveau $n (< 3) : aucune action sans approbation" }
Fixer 'initiatives_niveau' 3
Verifier ((Test-InitiativeSansApprobation $rap) -and -not (Test-InitiativeSansApprobation $haut)) 'niveau 3 : une initiative de niveau requis 1 peut passer seule ; niveau requis 4 : non'
Verifier (-not (Test-InitiativeSansApprobation $skill)) 'niveau 3 : un skill_propose demande toujours Liam'
Fixer 'initiatives_niveau' 5
Verifier ((Test-InitiativeSansApprobation $haut) -and -not (Test-InitiativeSansApprobation $tiers) -and -not (Test-InitiativeSansApprobation $skill)) 'niveau 5 : le niveau requis 4 passe, mais un message à un tiers demande TOUJOURS la validation de Liam'
Verifier (Test-InitiativeTiers 'Répondre au recruteur par e-mail') 'messages, mails, relances, appels = tiers'
Verifier (-not (Test-InitiativeSansApprobation ([ordered]@{ titre = 'x'; raison = 'y'; type = 'rappel'; niveau_autonomie = 1; statut = 'rejetee' }) 5)) 'une initiative déjà décidée ne repasse pas'
Fixer 'initiatives_niveau' 1

# ---------- Boucle ----------
Vider
Fixer 'initiatives_actif' 'oui'; Fixer 'initiatives_niveau' 1; Fixer 'initiatives_minutes' 30; Fixer 'initiatives_max_par_jour' 2
"# To-do`n- [ ] (plus tard) Un jour lointain`n- [ ] Finir la page d'accueil urgent`n- [x] Déjà fait" | Set-Content "$TR\memoire\todo.md" -Encoding UTF8
Save-JsonMemoire 'candidatures.json' ([ordered]@{ candidatures = @(
    [ordered]@{ fil = 'f1'; entreprise = 'CFF / SBB'; poste = 'Conducteur'; date = $now.AddDays(-2).ToString('o'); statut = 'ENTRETIEN'; lien = ''; resume = ''; historique = @() },
    [ordered]@{ fil = 'f2'; entreprise = 'SNCF'; poste = 'Conducteur'; date = $now.AddDays(-2).ToString('o'); statut = 'REFUS'; lien = ''; resume = ''; historique = @() },
    [ordered]@{ fil = 'f3'; entreprise = 'MOB'; poste = 'Conducteur'; date = $now.AddDays(-40).ToString('o'); statut = 'ENTRETIEN'; lien = ''; resume = ''; historique = @() }); traites = @() })
Save-JsonMemoire 'veille-train.json' ([ordered]@{ erreurs = [ordered]@{ 'CFF / SBB' = $now.ToString('yyyy-MM-dd') }; vus = @(); nouvelles = @() })
Save-Rappels @([pscustomobject]@{ id = 'r1'; texte = 'Payer la cantine'; quand = $now.AddDays(-1).ToString('yyyy-MM-dd HH:mm'); fait = $false }, [pscustomobject]@{ id = 'r2'; texte = 'Déjà dit'; quand = $now.AddDays(-1).ToString('yyyy-MM-dd HH:mm'); fait = $true })
$cand = @(Get-InitiativesCandidats $now)
Verifier (@($cand | Where-Object { $_.source -eq 'boucle:todo' }).Count -eq 1 -and ($cand | Where-Object { $_.source -eq 'boucle:todo' }).titre -match "page d'accueil" -and ($cand | Where-Object { $_.source -eq 'boucle:todo' }).urgence -eq 'haute') 'la boucle lit la to-do (ignore « plus tard » et les tâches faites)'
Verifier (@($cand | Where-Object { $_.source -eq 'boucle:candidatures' }).Count -eq 1 -and ($cand | Where-Object { $_.source -eq 'boucle:candidatures' }).titre -match 'entretien chez CFF') 'la boucle lit les candidatures (entretien récent seulement, pas un refus ni une réponse de 40 jours)'
Verifier (@($cand | Where-Object { $_.source -eq 'boucle:veille' }).Count -eq 1 -and @($cand | Where-Object { $_.source -eq 'boucle:agenda' }).Count -eq 1) 'la boucle lit les veilles (source en erreur) et l''agenda (rappel manqué)'
Verifier ($cand[0].urgence -eq 'haute') 'les urgentes d''abord'
$script:Cartes = @()
$cr = @(Invoke-InitiativesBoucle $now)
Verifier ($cr.Count -eq 2 -and $script:Cartes.Count -eq 2 -and @($cr | Where-Object { $_.statut -ne 'en_attente' }).Count -eq 0) 'plafond de 2 par jour respecté ; niveau 1 : tout reste en attente'
Verifier (@(Invoke-InitiativesBoucle $now.AddHours(3)).Count -eq 0) 'le plafond du jour est atteint : aucune création de plus'
Verifier (@(Invoke-InitiativesBoucle $now.AddDays(1)).Count -eq 2) 'le lendemain : de nouvelles initiatives (les deux d''hier ne sont pas redemandées)'
Fixer 'initiatives_niveau' 0
Verifier (@(Invoke-InitiativesBoucle $now.AddDays(2)).Count -eq 0) 'niveau 0 : Jarvis ne propose rien'
Fixer 'initiatives_niveau' 1
Verifier ((Journal) -match 'y a-t-il un truc utile') 'la question est journalisée'
# niveau 3 : approbation seule des rappels sans tiers
Vider; Fixer 'initiatives_niveau' 3; Fixer 'initiatives_max_par_jour' 5
$cr3 = @(Invoke-InitiativesBoucle $now.AddDays(3))
$st = @($cr3 | ForEach-Object { (Get-Initiative $_.id).statut })
Verifier ($cr3.Count -ge 2 -and @($st | Where-Object { $_ -eq 'approuvee' }).Count -ge 1) 'niveau 3 : les initiatives sans tiers sont approuvées seules (journalisé « auto »)'
Verifier ((Journal) -match 'par auto \(niveau 3\)') 'approbation automatique journalisée'
# Update-Initiatives : désactivée, jeu, cadence
Vider; Fixer 'initiatives_niveau' 1; Fixer 'initiatives_actif' 'non'; $script:InitProchain = $null
Verifier (-not (Update-Initiatives $now) -and $null -eq $script:InitProchain) 'initiatives_actif = "non" : Update-Initiatives ne fait rien'
Fixer 'initiatives_actif' 'oui'; Fixer 'initiatives_max_par_jour' 2; $script:ModeJeu = $true
Verifier (-not (Update-Initiatives $now) -and $null -eq $script:InitProchain) 'mode jeu : rien'
$script:ModeJeu = $false
$midi = $now.Date.AddHours(12)
Verifier (-not (Update-Initiatives $midi) -and $script:InitProchain -eq $midi.AddMinutes(30) -and (Get-Initiatives).Count -eq 0) 'actif : pas de scan au démarrage, premier tour dans 30 minutes'
Verifier (-not (Update-Initiatives $midi.AddMinutes(10))) 'pas avant l''échéance'
Verifier ((Update-Initiatives $midi.AddMinutes(31)) -and (Get-Initiatives).Count -eq 2) 'à l''échéance : un tour de boucle'
$script:InitProchain = $null
Fixer 'initiatives_actif' 'non'

# ---------- Commandes Discord ----------
Vider
$p = (Add-Initiative 'Idée urgente' 'rappel' 'Pour demain.' 'haute').initiative; $q = (Add-Initiative 'Idée calme' 'suggestion' 'Quand vous voulez.').initiative; $s = (Add-Initiative 'Idée repoussée' 'suggestion' 'x').initiative; $t = (Add-Initiative 'Idée à jeter' 'suggestion' 'x').initiative
function Cmd([string]$texte) {
    $script:DiscordTampon = New-Object System.Collections.Generic.List[string]; $script:DiscordEmbeds.Clear(); $script:CanalDiscord = 'jarvis'
    $r = Invoke-CommandeDiscord $texte
    @{ traite = $r; texte = ($script:DiscordTampon -join ' '); embeds = @($script:DiscordEmbeds) }
}
$x = Cmd 'initiatives'
Verifier ($x.traite -and $x.embeds.Count -eq 1 -and $x.embeds[0].titre -eq 'Initiatives' -and $x.embeds[0].couleur -eq $script:CouleurRouge -and ($x.embeds[0].champs | ForEach-Object { $_.valeur }) -join ' ' -match 'Idée urgente') 'commande « initiatives » : carte rouge (une urgente), liste des initiatives à valider'
$x = Cmd 'approuver 2'
Verifier ($x.traite -and $x.texte -match 'n° 2 approuvée' -and (Get-Initiative '2').statut -eq 'approuvee') 'commande « approuver 2 »'
$x = Cmd 'Jarvis, plus tard 3.'
Verifier ($x.traite -and $x.texte -match 'plus tard' -and (Get-Initiative '3').statut -eq 'plus_tard') 'commande « plus tard 3 » (avec « Jarvis » et un point)'
$x = Cmd 'rejeter #4'
Verifier ($x.traite -and (Get-Initiative '4').statut -eq 'rejetee') 'commande « rejeter #4 »'
$x = Cmd 'approuve l''initiative n° 1'
Verifier ($x.traite -and (Get-Initiative '1').statut -eq 'approuvee') 'formes naturelles : « approuve l''initiative n° 1 »'
$x = Cmd 'approuver 2'
Verifier ($x.traite -and $x.texte -match 'déjà décidée') 'une initiative déjà décidée est signalée'
$x = Cmd 'approuver 77'
Verifier ($x.traite -and $x.texte -match 'ne trouve pas') 'id inconnu : réponse polie'
$x = Cmd 'rejeter la tâche 3'
Verifier (-not $x.traite -or $x.texte -notmatch 'rejetée') 'une phrase hors commande n''est pas prise pour une commande d''initiative'
$x = Cmd 'initiatives'
Verifier ($x.embeds.Count -eq 1 -and $x.embeds[0].couleur -eq $script:CouleurBleue -and ($x.embeds[0].champs | ForEach-Object { $_.nom }) -join ' ' -match 'reportée') 'liste : barre bleue sans urgente en attente, rubrique « reportée »'
Fixer 'discord_style' 'texte'
$x = Cmd 'initiatives'
Verifier ($x.traite -and $x.embeds.Count -eq 0 -and $x.texte -match 'plus tard 3') 'style « texte » : réponse en texte simple'
Fixer 'discord_style' 'embed'
Vider
$x = Cmd 'initiatives'
Verifier ($x.embeds.Count -eq 1 -and $x.embeds[0].description -match 'Aucune initiative') 'liste vide : message poli'
$script:CanalDiscord = $null; $script:DiscordTampon = $null; $script:DiscordEmbeds.Clear()

# ---------- Cartes (style existant) ----------
$ni = New-EmbedInitiative ([ordered]@{ id = '7'; titre = 'Appeler le comptable'; type = 'rappel'; raison = 'Échéance de la TVA.'; urgence = 'normale'; statut = 'en_attente'; niveau_autonomie = 1 })
$ur = New-EmbedInitiative ([ordered]@{ id = '8'; titre = 'Entretien demain'; type = 'rappel'; raison = 'Réponse reçue.'; urgence = 'haute'; statut = 'en_attente'; niveau_autonomie = 1 })
Verifier ($ni.couleur -eq $script:CouleurBleue -and $ur.couleur -eq $script:CouleurRouge) 'barre bleue = normal, rouge = urgent'
Verifier ($ni.titre -match '^Initiative n° 7' -and $ni.titre.Length -lt 40 -and $ni.titre -match '^[\p{L}0-9]') 'titre court, sans emoji devant'
$noms = @($ni.champs | ForEach-Object { $_.nom })
Verifier (($noms -join ',') -eq 'Pourquoi,Type,Urgence,Statut,Votre réponse' -and @($ni.champs).Count -le 6 -and ($ni.champs | Where-Object { $_.nom -eq 'Votre réponse' }).valeur -match 'approuver 7') 'rubriques aérées : Pourquoi, Type, Urgence, Statut, Votre réponse'
Verifier (($ni.description + ($ni.champs | ForEach-Object { $_.valeur })) -notmatch '```' -and $ni.pied -match 'Rien n''est fait sans votre accord') 'aucun bloc de code ; pied clair'
$dec = New-EmbedInitiative ([ordered]@{ id = '9'; titre = 'Fait'; type = 'suggestion'; raison = 'r'; urgence = 'normale'; statut = 'approuvee'; niveau_autonomie = 1 })
Verifier (@($dec.champs | Where-Object { $_.nom -eq 'Votre réponse' }).Count -eq 0) 'une initiative décidée n''invite plus à répondre'
$beaucoup = @(1..12 | ForEach-Object { [ordered]@{ id = "$_"; titre = ('Titre ' + $_ + ' ' + ('z' * 90)); type = 'suggestion'; raison = ('r' * 190); urgence = 'normale'; statut = 'en_attente'; niveau_autonomie = 1 } })
$gros = New-EmbedInitiatives $beaucoup 3
$tot = $gros.titre.Length + $gros.description.Length + $gros.pied.Length; foreach ($f in $gros.champs) { $tot += $f.nom.Length + $f.valeur.Length }
Verifier ($tot -le 6000 -and ($gros.champs | Where-Object { $_.valeur.Length -gt 1024 }).Count -eq 0 -and $gros.pied -match '3 initiatives oubliées') 'liste longue : limites de Discord respectées, oubliées comptées'

# ---------- Garde-fous du code ----------
$src = Get-Content (Join-Path $Root 'lib\initiatives.ps1') -Raw -Encoding UTF8; $srcCode = (($src -split "`n") | Where-Object { $_ -notmatch '^\s*#' }) -join "`n"
Verifier ($srcCode -notmatch '(?i)Set-Content|Out-File|WriteAllText|Add-Content' -and $srcCode -notmatch '(?i)config\.json|config\.local') 'le moteur n''écrit aucun fichier directement et ne touche jamais config.json (tout passe par Save-JsonMemoire et l''action todo_ajouter)'
Verifier ($srcCode -notmatch '(?i)Invoke-Claude|Invoke-RestMethod|Invoke-WebRequest|Send-MailMessage|envoyer_message|Start-Process|Invoke-Expression|\biex\b' -and $srcCode -notmatch 'Set-Variable|\$script:TypesNiveau3\s*=|\$script:MotifsInterdits\s*=') 'aucun appel à Claude, au réseau, à un envoi de mail, ni modification de permissions ou d''interdits'
Verifier ((Get-Niveau ([pscustomobject]@{ type = 'todo_ajouter'; texte = 'x' })).niveau -eq 1 -and (Get-Niveau ([pscustomobject]@{ type = 'virement' })).niveau -eq 3) 'permissions inchangées : todo_ajouter = niveau 1, virement = niveau 3'
$octets = [IO.File]::ReadAllBytes((Join-Path $Root 'lib\initiatives.ps1')); $oct2 = [IO.File]::ReadAllBytes((Join-Path $Root 'tests\initiatives.ps1'))
Verifier ($octets[0] -eq 0xEF -and $octets[1] -eq 0xBB -and $octets[2] -eq 0xBF) 'lib\initiatives.ps1 en UTF-8 avec BOM'
$js = Get-Content (Join-Path $Root 'jarvis.ps1') -Raw -Encoding UTF8; $dc = Get-Content (Join-Path $Root 'lib\discord.ps1') -Raw -Encoding UTF8
Verifier ($js -match 'lib\\initiatives\.ps1' -and $js -match '\(Update-Initiatives\)' -and $dc -match 'Invoke-InitiativeCommande') 'jarvis.ps1 charge le module et appelle Update-Initiatives dans la boucle ; discord.ps1 route les commandes'
Verifier ((Get-Content (Join-Path $Root 'README.md') -Raw -Encoding UTF8) -match 'initiatives_niveau') 'README : initiatives décrites'
Verifier ((Get-FileHash (Join-Path $Root 'config.json')).Hash -eq $hashConfig) 'config.json réel inchangé par le test'

Write-Host ''
Remove-Item $TR -Recurse -Force -ErrorAction SilentlyContinue
if ($echecs) { Write-Host "ÉCHEC : $echecs vérification(s) en échec." -ForegroundColor Red; exit 1 }
Write-Host 'TOUT EST VERT.'
