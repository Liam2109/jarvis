# Test SILENCIEUX des presets (lib\presets.ps1) : étapes classées, niveaux jamais modifiés, exemples à valider, création sur validation seulement, exécution étape par étape, commandes.
# Mémoire et config TEMPORAIRES, exécution des étapes simulée (aucune application, aucun site, aucun son, aucune fenêtre). Code de sortie 0 = réussi.
$ErrorActionPreference = 'Stop'
$env:JARVIS_TEST = '1'
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $Root 'lib\journal.ps1')
$TR = Join-Path $env:TEMP ('jarvis-test-' + [guid]::NewGuid().ToString('N').Substring(0, 8)); New-Item -ItemType Directory $TR, "$TR\memoire", "$TR\logs", "$TR\visage" | Out-Null; $script:JarvisRoot = $TR
'# To-do' | Set-Content "$TR\memoire\todo.md" -Encoding UTF8; '# N' | Set-Content "$TR\memoire\notes.md" -Encoding UTF8; '# R' | Set-Content "$TR\memoire\resume.md" -Encoding UTF8
Copy-Item (Join-Path $Root 'visage\vues') "$TR\visage\vues" -Recurse
$Config = Get-Content $(if ($env:JARVIS_CONFIG -and (Test-Path $env:JARVIS_CONFIG)) { $env:JARVIS_CONFIG } else { Join-Path $Root 'config.json' }) -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($l in 'voix', 'business', 'permissions', 'actions', 'coffre', 'entrees', 'ecrans', 'tableau', 'visage', 'sons', 'raccourcis', 'cerveau', 'cerveau-local', 'veille', 'memoire', 'rapide', 'discretion', 'modejeu', 'competences', 'marche', 'priorite', 'comprehension', 'routeur', 'pc', 'bureau', 'salle-marche', 'matin', 'discord', 'saas', 'veille-train', 'veille-mail', 'candidatures', 'initiatives', 'lecons', 'skills', 'presets', 'vues') { . (Join-Path $Root "lib\$l.ps1") }
$script:JarvisRoot = $TR; $script:PolitesseFixe = $true
[void](Import-Competences (Join-Path $Root 'lib\competences'))      # point_saas, idees_contenu
$echecs = 0
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }
function Fixer([string]$cle, $val) { if ($Config.PSObject.Properties[$cle]) { $Config.$cle = $val } else { $Config | Add-Member -NotePropertyName $cle -NotePropertyValue $val } }
function Journal { $f = Join-Path $TR ('logs\journal-{0}.md' -f (Get-Date -Format 'yyyy-MM-dd')); if (Test-Path $f) { Get-Content $f -Raw -Encoding UTF8 } else { '' } }
function Vider { Remove-Item "$TR\memoire\presets", "$TR\memoire\initiatives.json" -Recurse -Force -ErrorAction SilentlyContinue }
function Cmd([string]$texte) {
    $script:DiscordTampon = New-Object System.Collections.Generic.List[string]; $script:DiscordEmbeds.Clear(); $script:CanalDiscord = 'jarvis'
    $r = Invoke-CommandeDiscord $texte
    @{ traite = $r; tampon = ((@($script:DiscordTampon) + @($script:DiscordEmbeds | ForEach-Object { "$($_.titre) $($_.description)" })) -join ' '); embeds = @($script:DiscordEmbeds) }
}
function P([string]$nom, $etapes, [string]$statut = 'actif', [string[]]$decl = @('un truc')) { [ordered]@{ nom = $nom; description = "Preset $nom."; declencheurs = @($decl); etapes = @($etapes); statut = $statut; version = 1 } }
function E([string]$a, $params = @{}) { [ordered]@{ action = $a; params = $params } }
$hashConfig = (Get-FileHash (Join-Path $Root 'config.json')).Hash
$vraie = Get-Content (Join-Path $Root 'config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$script:Appels = @(); $script:Cartes = @(); $script:InitNotifStub = { param($i) $script:Cartes += $i; $true }
$script:PresetsExecuteur = { param($a, $ordre) $script:Appels += $a; @{ ok = $true; texte = 'ok'; donnees = $null } }

# ---------- Réglage ----------
$sauve = $Config; $Config = [pscustomobject]@{}
Verifier (-not (Get-PresetsConfig).actif) 'sans réglage : presets désactivés'
$Config = $sauve
Verifier ($vraie.presets_actif -eq 'non') 'config.json : presets_actif = "non"'
Fixer 'presets_actif' 'non'
$x = Cmd 'presets'
Verifier ($x.traite -and $x.tampon -match 'désactivés' -and -not (Test-Path "$TR\memoire\presets")) 'désactivé : message poli, aucun dossier ni fichier créé'
Verifier (-not (Cmd 'je veux bosser sur le saas').traite) 'désactivé : une phrase déclencheuse n''est pas interceptée'

# ---------- Validation des étapes : classées, niveaux inchangés ----------
Fixer 'presets_actif' 'oui'
$ok = Test-PresetManifeste (P 'valide' @((E 'pc_dossier' @{ nom = 'projets' }), (E 'ouvrir_site' @{ url = 'https://tonproduit.shop' }), (E 'point_saas')))
Verifier ($ok.ok) "un preset d'actions classées passe$(if (-not $ok.ok) { ' : ' + ($ok.motifs -join ' ; ') })"
$cas = @(
    @('action hors liste (envoyer un message)', (P 'a1' @(E 'envoyer_message' @{ a = 'x'; sujet = 's'; texte = 't' })), 'liste des actions permises'),
    @('powershell libre', (P 'a2' @(E 'powershell' @{ code = 'dir' })), 'liste des actions permises'),
    @('script externe', (P 'a3' @(E 'executer_script' @{ chemin = 'x.ps1' })), 'liste des actions permises'),
    @('installation', (P 'a4' @(E 'installer_programme' @{ id = 'Git.Git' })), 'liste des actions permises'),
    @('suppression', (P 'a5' @(E 'supprimer_fichier' @{ chemin = 'x' })), 'liste des actions permises'),
    @('coffre de mots de passe', (P 'a6' @(E 'bitwarden_saisir' @{ recherche = 'x' })), 'liste des actions permises'),
    @('action inconnue', (P 'a7' @(E 'fais_n_importe_quoi')), 'liste des actions permises'),
    @('virement', (P 'a8' @(E 'virement' @{ montant = 5 })), 'liste des actions permises'),
    @('site de courtier', (P 'a9' @(E 'ouvrir_site' @{ url = 'https://www.boursorama.com' })), 'interdit'),
    @('adresse non http', (P 'b1' @(E 'ouvrir_site' @{ url = 'ftp://exemple.test' })), 'http'),
    @('secret dans un paramètre', (P 'b2' @(E 'ouvrir_app' @{ nom = 'mon mot de passe : hunter2' })), 'secret'),
    @('niveau déclaré abaissé', (P 'b3' @([ordered]@{ action = 'ouvrir_app'; params = @{ nom = 'chrome' }; niveau = 0 })), 'niveau déclaré'),
    @('niveau déclaré relevé', (P 'b4' @([ordered]@{ action = 'ouvrir_app'; params = @{ nom = 'chrome' }; niveau = 2 })), 'niveau déclaré'),
    @('plus de 8 étapes', (P 'b5' @(1..9 | ForEach-Object { E 'todo_lire' })), 'étapes : 1 à 8'),
    @('aucune étape', (P 'b6' @()), 'étapes : 1 à 8'),
    @('nom invalide', (P 'Mauvais Nom' @(E 'todo_lire')), 'kebab'),
    @('aucune phrase déclencheuse', (P 'b7' @(E 'todo_lire') 'actif' @()), 'déclencheuse'))
$rate = @(); foreach ($c in $cas) { $r = Test-PresetManifeste $c[1]; if ($r.ok -or ($r.motifs -join ' | ') -notmatch $c[2]) { $rate += "$($c[0]) -> " + $(if ($r.ok) { 'ACCEPTÉ' } else { $r.motifs -join ' | ' }) } }
Verifier ($rate.Count -eq 0) "refus de chacun des $($cas.Count) cas (action hors liste ou inconnue, virement, courtier, secret, niveau abaissé ou relevé, nombre d'étapes, nom)$(if ($rate.Count) { ' ; non conformes : ' + ($rate -join ' || ') })"
# action de la liste mais pas classée / classée niveau 3
$script:PresetsActionsPermises += 'zz_non_classee', 'virement'
$r1 = Test-PresetManifeste (P 'c1' @(E 'zz_non_classee'))
$script:Actions['virement'] = @{ niveau = 1; raison = 'x'; doc = 'x'; run = { param($a) Rep $true 'x' }; decrire = $null }
$r2 = Test-PresetManifeste (P 'c2' @(E 'virement'))
Verifier (-not $r1.ok -and ($r1.motifs -join ' ') -match 'pas classée' -and -not $r2.ok -and ($r2.motifs -join ' ') -match 'niveau 3') 'une étape non classée par les permissions, ou classée niveau 3 par le code, est refusée'
$script:Actions.Remove('virement'); $script:PresetsActionsPermises = @($script:PresetsActionsPermises | Where-Object { $_ -notin 'zz_non_classee', 'virement' })
$dang = 'envoyer_message', 'powershell', 'executer_script', 'installer_programme', 'desinstaller_programme', 'supprimer_fichier', 'deplacer_fichier', 'tuer_processus', 'bitwarden_saisir', 'bitwarden_chercher', 'claude_code_demander', 'oublie_tout', 'pc_eteindre', 'pc_redemarrer'
Verifier (@($dang | Where-Object { $_ -in $script:PresetsActionsPermises }).Count -eq 0) 'la liste blanche ne contient aucune action d''envoi, de suppression, d''installation, de script libre, de coffre ou d''extinction'
Verifier (@($script:PresetsActionsPermises | Where-Object { -not $script:Actions.ContainsKey($_) }).Count -eq 0) 'toute action de la liste existe et est classée'

# ---------- Exemples : préparés au premier usage, à valider ----------
Vider
$x = Cmd 'presets'
$pr = @(Get-Presets); $ini = @(Get-Initiatives | Where-Object { $_.source -eq 'presets' })
Verifier ($x.traite -and $pr.Count -eq 3 -and (@($pr.nom | Sort-Object) -join ',') -eq 'mode-nuit,mode-streamer,saas' -and @($pr | Where-Object { $_.statut -ne 'a_valider' }).Count -eq 0) 'au premier usage : 3 presets d''exemple (saas, mode-streamer, mode-nuit), tous « à valider »'
Verifier ($ini.Count -eq 3 -and @($ini | Where-Object { $_.type -ne 'skill_propose' -or $_.statut -ne 'en_attente' -or $_.titre -notmatch '^Valider le preset « ' }).Count -eq 0 -and (Test-Path "$TR\memoire\presets\saas.json")) 'une initiative skill_propose « Valider le preset » par exemple ; un fichier par preset dans memoire\presets\'
Verifier ($x.embeds.Count -eq 1 -and $x.embeds[0].titre -eq 'Presets' -and ($x.embeds[0].champs | ForEach-Object { $_.nom }) -join ' ' -match 'À valider \(3\)') 'commande « presets » : embed avec les 3 exemples à valider'
[void](Cmd 'presets'); Verifier (@(Get-Presets).Count -eq 3 -and @(Get-Initiatives | Where-Object { $_.source -eq 'presets' }).Count -eq 3) 'les exemples ne sont préparés qu''une fois'
$saas = Get-Preset 'saas'
Verifier (@($pr | Where-Object { -not (Test-PresetManifeste $_).ok }).Count -eq 0 -and (@($saas.etapes.action) -join ',') -eq 'pc_dossier,ouvrir_site,point_saas' -and $saas.declencheurs -contains 'je veux bosser sur le saas') 'les 3 exemples passent la validation ; « saas » = dossier, page du site, point SaaS'
$nuit = Get-Preset 'mode-nuit'
Verifier ((@($nuit.etapes.action) -join ',') -eq 'resume_jour,fermer_app,fermer_app,mode_pc') '« mode-nuit » = bilan du soir, ferme les applis de travail, mode nuit'
$script:Appels = @()
$x = Cmd 'lance le preset saas'
Verifier ($x.tampon -match 'pas actif' -and $script:Appels.Count -eq 0) 'un exemple non validé ne se lance pas'
$x = Cmd 'je veux bosser sur le SaaS'
Verifier (-not $x.traite -or $script:Appels.Count -eq 0) 'sa phrase déclencheuse ne le lance pas non plus'
$idS = ($ini | Where-Object { $_.titre -match 'saas' }).id
$x = Cmd "approuver $idS"
Verifier ((Get-Preset 'saas').statut -eq 'actif' -and $x.tampon -match 'enregistré et activé' -and (Get-Preset 'mode-nuit').statut -eq 'a_valider') 'approuver valide et active CE preset seulement'
$idN = ($ini | Where-Object { $_.titre -match 'mode-nuit' }).id
[void](Cmd "rejeter $idN")
Verifier ((Get-Preset 'mode-nuit').statut -eq 'refuse') 'rejeter : le preset est refusé'

# ---------- Lancer : étape par étape, niveaux inchangés ----------
$script:Appels = @()
$x = Cmd 'je veux bosser sur le SaaS'
Verifier ($x.traite -and $script:Appels.Count -eq 3 -and $script:Appels[0].type -eq 'pc_dossier' -and $script:Appels[0].nom -eq 'projets' -and $script:Appels[1].type -eq 'ouvrir_site' -and $script:Appels[1].url -eq 'https://tonproduit.shop' -and $script:Appels[2].type -eq 'point_saas' -and $x.tampon -match '3 étapes sur 3') 'la phrase déclencheuse lance les 3 étapes dans l''ordre'
Verifier ($x.embeds.Count -eq 0 -or $x.embeds[0].titre -match 'saas') 'réponse en carte ou en texte'
$script:Appels = @(); $x = Cmd 'Jarvis, lance le preset SaaS.'
Verifier ($script:Appels.Count -eq 3) '« lance le preset saas »'
Verifier ((Journal) -match 'Preset : lancement' -and (Journal) -match 'Preset : fin') 'lancement et fin journalisés'
# refus à l'étape 2 : arrêt
$n = 0; $script:PresetsExecuteur = { param($a, $ordre) $script:Appels += $a; $script:n2++; if ($a.type -eq 'ouvrir_site') { $null } else { @{ ok = $true; texte = 'ok' } } }
$script:Appels = @(); $r = Invoke-Preset (Get-Preset 'saas')
Verifier (-not $r.ok -and $script:Appels.Count -eq 2 -and $r.texte -match 'arrêté à l''étape 2' -and ($r.lignes -join ' ') -match 'refusée ou non confirmée') 'une étape refusée ou non confirmée arrête le preset (la suivante n''est pas lancée)'
# échec d'une étape : on continue et on le dit
$script:PresetsExecuteur = { param($a, $ordre) $script:Appels += $a; if ($a.type -eq 'ouvrir_site') { @{ ok = $false; texte = 'site injoignable' } } else { @{ ok = $true; texte = 'ok' } } }
$script:Appels = @(); $r = Invoke-Preset (Get-Preset 'saas')
Verifier ($script:Appels.Count -eq 3 -and -not $r.ok -and ($r.lignes -join ' ') -match '✗ ouvrir_site:https://tonproduit.shop : site injoignable' -and $r.texte -match 'ont échoué') 'une étape qui échoue est signalée, les suivantes continuent'
# vraie voie des permissions : Invoke-UneAction, confirmation de niveau 2
$script:ConfN = 0; $script:ConfRep = $false; $script:Fait = 0
function Confirmer([string]$q) { $script:ConfN++; $script:DerniereConfirmation = 'reponse'; $script:ConfRep }
Add-Action 'zz_niv2' 2 'test niveau 2' 'zz_niv2() : test' { param($a) $script:Fait++; Rep $true 'fait' } { param($a) 'faire le test niveau 2' }
$script:PresetsActionsPermises += 'zz_niv2'
$script:PresetsExecuteur = $null
$p2 = P 'niveau-deux' @((E 'todo_lire'), (E 'zz_niv2'), (E 'etat_site')) 'actif'
Verifier ((Test-PresetManifeste $p2).ok -and (Get-Niveau (ConvertTo-PresetAction (E 'zz_niv2'))).niveau -eq 2) 'une étape de niveau 2 reste de niveau 2 dans un preset'
$r = Invoke-Preset $p2
Verifier ($script:ConfN -eq 1 -and $script:Fait -eq 0 -and $r.texte -match 'arrêté à l''étape 2') 'étape de niveau 2 : « Vous confirmez, monsieur ? » est demandé ; refusé, l''action n''est PAS faite et le preset s''arrête'
$script:ConfRep = $true; $script:ConfN = 0
$r = Invoke-Preset $p2
Verifier ($script:ConfN -eq 1 -and $script:Fait -eq 1 -and $r.ok) 'confirmé : l''étape est faite, le preset va au bout'
$bas = P 'niveau-bas' @([ordered]@{ action = 'zz_niv2'; params = @{}; niveau = 1 }) 'actif'
Verifier (-not (Test-PresetManifeste $bas).ok -and (Invoke-Preset $bas).texte -match 'ne passe plus la validation') 'déclarer un niveau plus bas pour une action de niveau 2 est refusé, aussi au lancement'
$script:PresetsActionsPermises = @($script:PresetsActionsPermises | Where-Object { $_ -ne 'zz_niv2' }); $script:Actions.Remove('zz_niv2')
Remove-Item Function:\Confirmer
# preset modifié à la main après validation
$f = "$TR\memoire\presets\saas.json"; $o = Get-Content $f -Raw -Encoding UTF8 | ConvertFrom-Json
$o.etapes += [pscustomobject]@{ action = 'envoyer_message'; params = [pscustomobject]@{ a = 'x@y.z'; sujet = 's'; texte = 't' } }; [IO.File]::WriteAllText($f, ($o | ConvertTo-Json -Depth 6), [Text.UTF8Encoding]::new($false))
$script:Appels = @(); $script:PresetsExecuteur = { param($a, $ordre) $script:Appels += $a; @{ ok = $true; texte = 'ok' } }
$r = Invoke-Preset (Get-Preset 'saas')
Verifier ($script:Appels.Count -eq 0 -and $r.texte -match 'ne passe plus la validation') 'un fichier de preset modifié à la main pour ajouter un envoi est refusé au lancement : rien n''est exécuté'
$o.etapes = @($o.etapes | Where-Object { $_.action -ne 'envoyer_message' }); [IO.File]::WriteAllText($f, ($o | ConvertTo-Json -Depth 6), [Text.UTF8Encoding]::new($false))

# ---------- Création par texte : proposée, jamais enregistrée sans validation ----------
$f0 = @(Get-ChildItem "$TR\memoire\presets" -File).Count
$x = Cmd 'crée un preset focus avec ouvre chrome, ferme discord, point saas'
$prop = @(Get-Initiatives | Where-Object { $_.titre -eq 'Créer le preset « focus »' })
Verifier ($x.traite -and $prop.Count -eq 1 -and $prop[0].type -eq 'skill_propose' -and $prop[0].source -eq 'presets' -and $prop[0].statut -eq 'en_attente' -and $prop[0].raison -match 'ouvrir_app:chrome ; fermer_app:discord ; point_saas') 'création par texte : une initiative skill_propose avec les étapes lisibles'
Verifier (-not (Test-Path "$TR\memoire\presets\focus.json") -and @(Get-ChildItem "$TR\memoire\presets" -File).Count -eq $f0 -and -not (Get-Preset 'focus')) 'rien n''est enregistré avant la validation'
Verifier ((Cmd 'lance le preset focus').tampon -match 'ne connais pas') 'le preset proposé n''existe pas encore'
Fixer 'initiatives_niveau' 5
Verifier (-not (Test-InitiativeSansApprobation $prop[0] 5)) 'même au niveau d''autonomie 5, la création n''est jamais approuvée automatiquement'
[void](Set-InitiativeStatut $prop[0].id 'approuvee' 'auto (niveau 5)')
$d = Invoke-PresetsDecision (Get-Initiative $prop[0].id)
Verifier ($null -eq $d -and -not (Get-Preset 'focus')) 'approuvée par le moteur seul : toujours rien d''enregistré (seul « approuver » de Liam compte)'
Fixer 'initiatives_niveau' 1
# nouvelle proposition (la précédente est déjà décidée) puis approbation de Liam
$x = Cmd 'crée un preset focus-deux avec ouvre le dossier projets, ouvre le site tonproduit.shop, mode travail'
$p2i = @(Get-Initiatives | Where-Object { $_.titre -eq 'Créer le preset « focus-deux »' })[0]
$x = Cmd "approuver $($p2i.id)"
$pf = Get-Preset 'focus-deux'
Verifier ($pf -and $pf.statut -eq 'actif' -and @($pf.etapes).Count -eq 3 -and $pf.etapes[0].action -eq 'pc_dossier' -and $pf.etapes[0].params.nom -eq 'projets' -and $pf.etapes[1].params.url -eq 'https://tonproduit.shop' -and $pf.etapes[2].action -eq 'mode_pc' -and $pf.etapes[2].params.nom -eq 'travail' -and $x.tampon -match 'enregistré et activé') 'après « approuver » de Liam : preset enregistré (fichier) et actif, étapes décodées'
$script:Appels = @(); $x = Cmd 'lance le preset focus-deux'
Verifier ($script:Appels.Count -eq 3 -and $script:Appels[2].type -eq 'mode_pc') 'et il se lance'
[void](Cmd 'crée un preset a-jeter avec ouvre chrome')
$aj = @(Get-Initiatives | Where-Object { $_.titre -match 'a-jeter' })[0]; [void](Cmd "rejeter $($aj.id)")
Verifier (-not (Get-Preset 'a-jeter') -and -not (Test-Path "$TR\memoire\presets\a-jeter.json")) 'rejeté : rien d''enregistré'
$refus = @(
    @('crée un preset mail avec envoie un mail à Paul', 'ne sais pas encore faire'),
    @('crée un preset script avec exécute le script x.ps1', 'ne sais pas encore faire'),
    @('crée un preset bourse avec ouvre le site boursorama.com', 'interdit'),
    @('crée un preset saas avec ouvre chrome', 'existe déjà'),
    @('crée un preset trop-long avec ouvre a1, ouvre a2, ouvre a3, ouvre a4, ouvre a5, ouvre a6, ouvre a7, ouvre a8, ouvre a9', 'de 1 à 8'))
$mal = @(); foreach ($c in $refus) { $n0 = @(Get-Initiatives).Count; $x = Cmd $c[0]; if (-not ($x.traite -and $x.tampon -match $c[1] -and @(Get-Initiatives).Count -eq $n0)) { $mal += $c[0] } }
Verifier ($mal.Count -eq 0) "propositions refusées sans initiative ($($refus.Count) : envoi de mail, script, courtier, nom pris, trop d'étapes)$(if ($mal.Count) { ' ; ratées : ' + ($mal -join ' | ') })"

# ---------- Commandes ----------
$x = Cmd 'désactive le preset saas'
Verifier ($x.tampon -match 'désactivé' -and (Get-Preset 'saas').statut -eq 'desactive') 'commande « désactive le preset »'
$script:Appels = @(); $x = Cmd 'lance le preset saas'; $y = Cmd 'je veux bosser sur le SaaS'
Verifier ($x.tampon -match 'pas actif \(désactivé\)' -and $script:Appels.Count -eq 0 -and -not $y.traite) 'désactivé : ni la commande ni la phrase déclencheuse ne le lancent'
$x = Cmd 'active le preset saas'
Verifier ($x.tampon -match 'réactivé' -and (Get-Preset 'saas').statut -eq 'actif') 'commande « active le preset » (réactivation d''un preset déjà validé)'
$x = Cmd 'active le preset mode-nuit'; $y = Cmd 'active le preset mode-streamer'
Verifier ($x.tampon -match 'ne peut pas être réactivé' -and (Get-Preset 'mode-nuit').statut -eq 'refuse' -and (Get-Preset 'mode-streamer').statut -eq 'a_valider') 'un preset refusé ou jamais validé ne s''active pas par simple commande'
Verifier ((Cmd 'lance le preset inconnu').tampon -match 'ne connais pas' -and (Cmd 'désactive le preset inconnu').tampon -match 'ne connais pas') 'preset inconnu : réponse polie'
$x = Cmd 'presets'
$noms = ($x.embeds[0].champs | ForEach-Object { $_.nom }) -join ' | '
Verifier ($noms -match 'Actifs' -and $noms -match 'À valider' -and $noms -match 'Refusés' -and $x.embeds[0].couleur -eq $script:CouleurBleue) '« presets » : actifs, à valider, refusés'
Fixer 'discord_style' 'texte'; $x = Cmd 'presets'
Verifier ($x.traite -and $x.embeds.Count -eq 0 -and $x.tampon -match 'saas \(actif\)') 'style « texte » : liste simple'
Fixer 'discord_style' 'embed'
Verifier (-not (Cmd 'ouvre chrome').traite -or $script:Appels.Count -eq 0) 'les autres ordres ne sont pas interceptés'
# voix : même entrée
$ex = Invoke-ExtensionsOrdre 'lance le preset saas'
Verifier ($ex -and $ex.texte -match 'saas') 'la voix passe par la même entrée (Invoke-ExtensionsOrdre)'

# ---------- Garde-fous du code ----------
$src = Get-Content (Join-Path $Root 'lib\presets.ps1') -Raw -Encoding UTF8; $srcCode = (($src -split "`n") | Where-Object { $_ -notmatch '^\s*#' }) -join "`n"
Verifier ($srcCode -notmatch '(?i)Invoke-Claude|Invoke-Ollama|Invoke-RestMethod|Invoke-WebRequest|Start-Process\s+[-$''"a-z]|Invoke-Expression\s+\$|Set-Content|Out-File|Add-Content|WriteAllText' -and $srcCode -notmatch '\$script:(TypesNiveau3|MotifsInterdits)\s*=') 'aucun appel à Claude, au réseau ni à un programme ; aucune écriture directe ; permissions et interdits intacts'
Verifier ([regex]::Matches($srcCode, 'Invoke-UneAction \$a').Count -eq 1) 'chaque étape passe par Invoke-UneAction (un seul point d''exécution)'
$ini = Get-Content (Join-Path $Root 'lib\initiatives.ps1') -Raw -Encoding UTF8; $js = Get-Content (Join-Path $Root 'jarvis.ps1') -Raw -Encoding UTF8
Verifier ($ini -match 'Invoke-PresetsDecision' -and $js -match 'lib\\presets\.ps1') 'câblage : initiatives.ps1 appelle la décision, jarvis.ps1 charge le module'
$oct = [IO.File]::ReadAllBytes((Join-Path $Root 'lib\presets.ps1'))
Verifier ($oct[0] -eq 0xEF -and $oct[1] -eq 0xBB -and $oct[2] -eq 0xBF) 'lib\presets.ps1 en UTF-8 avec BOM'
Verifier ((Get-Content (Join-Path $Root 'README.md') -Raw -Encoding UTF8) -match 'presets_actif') 'README : presets décrits'
Verifier ((Get-FileHash (Join-Path $Root 'config.json')).Hash -eq $hashConfig) 'config.json réel inchangé par le test'

Write-Host ''
Remove-Item $TR -Recurse -Force -ErrorAction SilentlyContinue
if ($echecs) { Write-Host "ÉCHEC : $echecs vérification(s) en échec." -ForegroundColor Red; exit 1 }
Write-Host 'TOUT EST VERT.'
