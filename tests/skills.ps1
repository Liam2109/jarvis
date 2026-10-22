# Test SILENCIEUX des skills créés par Jarvis (lib\skills.ps1) : idée sans fichier, génération simulée (aucun appel à Claude), contrôle statique de chaque cas interdit, test isolé, validation, activation, refus archivé + leçon, commandes.
# Mémoire, config et dossiers TEMPORAIRES (jamais votre quarantaine\ ni lib\competences\), Discord simulé, aucun son, aucune fenêtre, aucun programme lancé. Code de sortie 0 = réussi.
$ErrorActionPreference = 'Stop'
$env:JARVIS_TEST = '1'
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $Root 'lib\journal.ps1')
$TR = Join-Path $env:TEMP ('jarvis-test-' + [guid]::NewGuid().ToString('N').Substring(0, 8)); New-Item -ItemType Directory $TR, "$TR\memoire", "$TR\logs", "$TR\lib\competences", "$TR\tmp" | Out-Null; $script:JarvisRoot = $TR
'# To-do' | Set-Content "$TR\memoire\todo.md" -Encoding UTF8; '# N' | Set-Content "$TR\memoire\notes.md" -Encoding UTF8; '# R' | Set-Content "$TR\memoire\resume.md" -Encoding UTF8
Copy-Item (Join-Path $Root 'lib\competences\_exemple.ps1') "$TR\lib\competences\_exemple.ps1"
$Config = Get-Content $(if ($env:JARVIS_CONFIG -and (Test-Path $env:JARVIS_CONFIG)) { $env:JARVIS_CONFIG } else { Join-Path $Root 'config.json' }) -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($l in 'voix', 'business', 'permissions', 'actions', 'coffre', 'entrees', 'ecrans', 'tableau', 'visage', 'sons', 'raccourcis', 'cerveau', 'cerveau-local', 'veille', 'memoire', 'rapide', 'discretion', 'modejeu', 'competences', 'marche', 'priorite', 'comprehension', 'routeur', 'pc', 'bureau', 'salle-marche', 'matin', 'discord', 'veille-train', 'veille-mail', 'candidatures', 'initiatives', 'lecons', 'skills') { . (Join-Path $Root "lib\$l.ps1") }
$script:JarvisRoot = $TR; $script:PolitesseFixe = $true
$echecs = 0
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }
function Fixer([string]$cle, $val) { if ($Config.PSObject.Properties[$cle]) { $Config.$cle = $val } else { $Config | Add-Member -NotePropertyName $cle -NotePropertyValue $val } }
function Journal { $f = Join-Path $TR ('logs\journal-{0}.md' -f (Get-Date -Format 'yyyy-MM-dd')); if (Test-Path $f) { Get-Content $f -Raw -Encoding UTF8 } else { '' } }
function Fichier([string]$texte) { $f = Join-Path $TR ('tmp\s-' + [guid]::NewGuid().ToString('N').Substring(0, 6) + '.ps1'); [IO.File]::WriteAllText($f, $texte, [Text.UTF8Encoding]::new($true)); $f }
function Cmd([string]$texte) {
    $script:DiscordTampon = New-Object System.Collections.Generic.List[string]; $script:DiscordEmbeds.Clear(); $script:CanalDiscord = 'jarvis'
    $r = Invoke-CommandeDiscord $texte
    @{ traite = $r; tampon = ($script:DiscordTampon -join ' '); embeds = @($script:DiscordEmbeds) }
}
function Fichiers { @(Get-ChildItem $TR -Recurse -File | Where-Object { $_.FullName -notmatch '\\(logs|tmp)\\' } | ForEach-Object { $_.FullName.Substring($TR.Length + 1) } | Sort-Object) }
$hashConfig = (Get-FileHash (Join-Path $Root 'config.json')).Hash
$vraie = Get-Content (Join-Path $Root 'config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$realQ = @(Get-ChildItem (Join-Path $Root 'quarantaine') -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object { "$($_.FullName):$($_.Length)" }) -join '|'
$realC = @(Get-ChildItem (Join-Path $Root 'lib\competences') -Recurse -File | ForEach-Object { "$($_.Name):$((Get-FileHash $_.FullName).Hash)" }) -join '|'
$script:Cartes = @(); $script:InitNotifStub = { param($i) $script:Cartes += $i; $true }
$script:GenAppels = 0; $script:GenSysteme = ''; $script:GenRep = $null
$script:SkillsGenerateur = { param($sys, $user) $script:GenAppels++; $script:GenSysteme = $sys; $script:GenUser = $user; $script:GenRep }

# Un skill valide, et un gabarit pour les cas interdits
$OK = @'
# Skill de test
Add-Action 'resumer_notes' 1 'résumer les notes' 'resumer_notes() : compte les lignes des notes' {
    param($a)
    $n = @(Get-Content (Join-Path $global:SkillDossiers['resumer-notes'] 'notes.txt') -ErrorAction SilentlyContinue).Count
    Rep $true "Il y a $n ligne(s)."
} { param($a) 'résumer les notes' }
'@
$TPL = @'
Add-Action 'cas_test' 1 'raison' 'doc' {
    param($a)
    __LIGNE__
    Rep $true 'x'
} { param($a) 'cas' }
'@
function Bad([string]$ligne, [int]$max = 1, [string[]]$env = @()) { Test-SkillScript (Fichier $TPL.Replace('__LIGNE__', $ligne)) @{ variables_env = $env } $max }
function Script-Pour([string]$nom, [string]$action) { $OK.Replace("resumer_notes", $action).Replace("resumer-notes", $nom) }
function Reponse([string]$script, [string]$decl = "résume mes notes`ncompte mes notes", [string]$env = 'rien') { "=== SCRIPT ===`n$script`n=== DECLENCHEURS ===`n$decl`n=== ENV ===`n$env`n" }

# ---------- Réglage ----------
$sauve = $Config; $Config = [pscustomobject]@{}
Verifier (-not (Get-SkillsConfig).actif) 'sans réglage : skills désactivés'
$Config = $sauve
Verifier ($vraie.skills_auto -eq 'non') 'config.json : skills_auto = "non"'
Fixer 'skills_auto' 'oui'; Fixer 'lecons_actif' 'oui'; Fixer 'initiatives_niveau' 1

# ---------- Contrôle statique : le skill valide passe, chaque cas interdit est refusé ----------
$r = Test-SkillScript (Fichier $OK) @{ variables_env = @() } 1
Verifier ($r.ok -and $r.actions -contains 'resumer_notes') 'un skill ordinaire passe l''analyse statique'
$cas = @(
    @('Get-Content ''C:\Users\Liam\Jarvis\.env''', '\.env|secret'), @('$x = Get-Content ''.env''', 'secret'), @('Get-Content (Join-Path $env:APPDATA ''gmail-jeton.dpapi'')', 'secret'),
    @('Invoke-Expression $a.texte', 'Invoke-Expression'), @('iex ($a.texte)', 'iex'), @('[scriptblock]::Create($a.texte).Invoke()', 'construit'),
    @('Invoke-WebRequest -Uri ''https://exemple.test/x.ps1'' -OutFile x.ps1', 'distant'), @('(New-Object Net.WebClient).DownloadString(''http://exemple.test'')', 'distant'),
    @('Remove-Item ''C:\Users\Public\x.txt''', 'hors de son dossier'), @('Remove-Item (Join-Path $global:SkillDossiers[''cas''] ''..\..\y'') -Recurse', 'hors de son dossier'), @('Get-ChildItem C:\ -Recurse | Remove-Item -Force', 'hors de son dossier'),
    @('Set-Content ''C:\Users\Public\x.txt'' ''a''', 'hors de son dossier'), @('''a'' > C:\x.txt', 'redirection'), @('[IO.File]::Delete(''C:\x.txt'')', 'hors de son dossier'), @('[IO.File]::WriteAllText(''C:\x.txt'', ''a'')', 'hors de son dossier'),
    @('$p = New-Object System.Security.Cryptography.AesManaged', 'chiffre'), @('[Security.Cryptography.ProtectedData]::Protect($b, $null, ''CurrentUser'')', 'chiffre'),
    @('Get-Content ''lib\interdits.json''', 'interdits'), @('Set-Content ''lib\permissions.ps1'' ''''', 'interdits'), @('Get-Content ''..\config.json''', 'config'), @('Save-JsonMemoire ''x.json'' @{}', 'memoire'), @('Add-Memoire ''todo.md'' ''x''', 'memoire'), @('$Config.discord_actif = $true', 'config'),
    @('Start-Process ollama -ArgumentList serve', 'Ollama'), @('& ollama serve', 'Ollama'), @('Start-Process notepad -WindowStyle Hidden', 'processus caché'), @('Start-Job { 1 }', 'processus'), @('& .\jarvis.ps1', 'Jarvis'), @('Start-Process powershell', 'processus'),
    @('Send-MailMessage -To a@b.c -Subject x', 'envoie'), @('Send-MessageDiscord ''jarvis'' ''x''', 'envoie'), @('[Net.Mail.SmtpClient]::new(''smtp'')', 'envoie'),
    @('Rep $true ''je lance un virement de 500 euros''', 'financiers'), @('Rep $true ''acheter 10 actions''', 'financiers'), @('Rep $true ''ouvre boursorama''', 'interdit|financiers'),
    @('$script:Actions.Remove(''point_saas'')', 'autre skill'), @('Set-Content ''lib\competences\point-saas.ps1'' ''''', 'autre skill'), @('function Get-Niveau { 1 }', 'fonction'), @('$global:Foo = 1', 'variable globale'), @('$e = $env:SECRET_KEY', 'non déclarée'))
$rate = @()
foreach ($c in $cas) { $b = Bad $c[0]; if ($b.ok -or ($b.motifs -join ' | ') -notmatch $c[1]) { $rate += "$($c[0]) -> " + $(if ($b.ok) { 'ACCEPTÉ' } else { $b.motifs -join ' | ' }) } }
Verifier ($rate.Count -eq 0) "refus de chacun des $($cas.Count) cas interdits (.env, jetons, iex, code distant, suppression ou chiffrement hors dossier, interdits / permissions / config / memoire, autre skill, Ollama, processus caché, messages, ordres financiers)$(if ($rate.Count) { ' ; non conformes : ' + ($rate -join ' || ') })"
Verifier ((Bad '$e = $env:MON_NOM_ENV' 1 @('MON_NOM_ENV')).ok -and (Bad '$t = $env:TEMP').ok) 'variable d''environnement déclarée (par NOM) ou sûre : permise'
Verifier ((Bad 'Set-Content (Join-Path $global:SkillDossiers[''cas''] ''out.txt'') ''a''').ok -and (Bad 'Remove-Item (Join-Path $global:SkillDossiers[''cas''] ''out.txt'')').ok) 'écrire ou supprimer DANS son propre dossier : permis'
Verifier ((Test-SkillScript (Fichier ("# ne lit jamais .env ni les jetons, n'appelle jamais iex`n" + $OK)) @{ variables_env = @() } 1).ok) 'un commentaire qui MENTIONNE .env ou iex ne bloque pas (seul le code est analysé)'
$niv3 = $TPL.Replace('__LIGNE__', '').Replace("Add-Action 'cas_test' 1", "Add-Action 'cas_test' 3")
$niv2 = $TPL.Replace('__LIGNE__', '').Replace("Add-Action 'cas_test' 1", "Add-Action 'cas_test' 2")
$nivV = $TPL.Replace('__LIGNE__', '$n = 1').Replace("Add-Action 'cas_test' 1", 'Add-Action ''cas_test'' $n')
Verifier (-not (Test-SkillScript (Fichier $niv3) @{} 2).ok -and ((Test-SkillScript (Fichier $niv3) @{} 2).motifs -join ' ') -match 'niveau') 'niveau de permission 3 : refusé, même si 2 a été approuvé'
Verifier (-not (Test-SkillScript (Fichier $niv2) @{} 1).ok -and ((Test-SkillScript (Fichier $niv2) @{} 1).motifs -join ' ') -match 'alors que 1 a été approuvé' -and (Test-SkillScript (Fichier $niv2) @{} 2).ok) 'niveau 2 demandé alors que 1 est approuvé : refusé ; 2 approuvé : accepté'
Verifier (-not (Test-SkillScript (Fichier $nivV) @{} 2).ok) 'niveau calculé (non littéral) : refusé'
Verifier (-not (Test-SkillScript (Fichier ($TPL.Replace('__LIGNE__', '').Replace('cas_test', 'todo_ajouter'))) @{} 1).ok -and ((Test-SkillScript (Fichier ($TPL.Replace('__LIGNE__', '').Replace('cas_test', 'todo_ajouter'))) @{} 1).motifs -join ' ') -match 'existe déjà') 'une action qui existe déjà (todo_ajouter) n''est jamais remplacée'
$m1 = (Test-SkillScript (Fichier "Write-Host 'bonjour'`n$OK") @{} 1).motifs -join ' '; $m2 = (Test-SkillScript (Fichier '# rien') @{} 1).motifs -join ' '; $m3 = (Test-SkillScript (Fichier 'Add-Action 1 2') @{} 1).motifs -join ' '; $m4 = (Test-SkillScript (Fichier 'Add-Action ''x_y'' 1 {') @{} 1).motifs -join ' '
Verifier ($m1 -match 'hors Add-Action' -and $m2 -match 'aucune action' -and $m3 -match 'incomplet|invalide' -and $m4 -match 'syntaxe') 'code hors Add-Action, fichier sans action, Add-Action incomplet, erreur de syntaxe : refusés'
Verifier (-not (Test-SkillScript (Fichier ($OK + (' ' * 31000))) @{} 1).ok) 'script trop long : refusé'

# ---------- Manifeste ----------
$mOk = [ordered]@{ nom = 'resumer-notes'; version = '0.1.0'; description = 'Résume les notes.'; declencheurs = @('résume mes notes'); outils = @('lecture'); permission_niveau = 1; variables_env = @('MON_NOM_ENV') }
Verifier ((Test-SkillManifeste $mOk).ok) 'manifeste valide'
$mBad = [ordered]@{} + $mOk; $mBad.variables_env = @('API_KEY=abc123def'); $mBad2 = [ordered]@{} + $mOk; $mBad2.description = 'Utilise le mot de passe : hunter2secret'; $mBad3 = [ordered]@{} + $mOk; $mBad3.nom = 'Mauvais Nom'; $mBad4 = [ordered]@{} + $mOk; $mBad4.permission_niveau = 3
Verifier (-not (Test-SkillManifeste $mBad).ok -and -not (Test-SkillManifeste $mBad2).ok -and -not (Test-SkillManifeste $mBad3).ok -and -not (Test-SkillManifeste $mBad4).ok) 'manifeste refusé : variable avec VALEUR, secret, nom non kebab-case, permission 3'

# ---------- Test isolé ----------
$tmpAvant = @(Get-ChildItem $env:TEMP -Directory -Filter 'jarvis-test-skill-*').Count
$s1 = Test-SkillSandbox (Fichier $OK) 20 'resumer-notes'
Verifier ($s1.ok) 'test silencieux : l''action tourne dans un espace isolé et renvoie Rep'
$s2 = Test-SkillSandbox (Fichier ($TPL.Replace('__LIGNE__', 'throw ''boum'''))) 20 'cas'
$s3 = Test-SkillSandbox (Fichier ($TPL.Replace('__LIGNE__', '').Replace("Rep `$true 'x'", '$null'))) 20 'cas'
$s4 = Test-SkillSandbox (Fichier ($TPL.Replace('__LIGNE__', 'while ($true) { }'))) 2 'cas'
$s5 = Test-SkillSandbox (Fichier ($TPL.Replace('__LIGNE__', 'Commande-Inconnue-Xyz'))) 20 'cas'
Verifier (-not $s2.ok -and $s2.motif -match 'boum' -and -not $s3.ok -and $s3.motif -match 'Rep' -and -not $s4.ok -and $s4.motif -match 'dépasse' -and -not $s5.ok) 'test en échec : exception, résultat sans Rep, boucle infinie (délai), commande inconnue'
Verifier ($env:JARVIS_TEST -eq '1' -and @(Get-ChildItem $env:TEMP -Directory -Filter 'jarvis-test-skill-*').Count -eq $tmpAvant) 'le test isolé nettoie son dossier temporaire et remet l''environnement'

# ---------- 1. IDÉE : rien sur le disque ----------
Remove-Item "$TR\memoire\initiatives.json" -Force -ErrorAction SilentlyContinue
$f0 = Fichiers
$id1 = New-SkillIdeeDepuisDemande 'résumer mes notes'
$f1 = Fichiers
Verifier ($id1.ok -and $id1.initiative.type -eq 'skill_propose' -and $id1.initiative.statut -eq 'en_attente' -and $id1.initiative.titre -eq 'Créer le skill « resumer-notes »' -and $id1.initiative.source -eq 'skills') 'l''idée est une initiative skill_propose en attente, avec un nom kebab-case'
$idee = Get-SkillIdeeDepuisInitiative $id1.initiative
Verifier ($idee.nom -eq 'resumer-notes' -and $idee.description -match 'résumer mes notes' -and $idee.niveau -eq 1 -and $id1.initiative.raison -match 'Outils : .*Permission : niveau 1') 'description d''une phrase, outils et permission prévus lisibles dans l''initiative'
Verifier ((Compare-Object $f0 $f1).Count -le 1 -and (@($f1 | Where-Object { $_ -notin $f0 }) -join '') -eq 'memoire\initiatives.json' -and -not (Test-Path "$TR\quarantaine") -and -not (Test-Path "$TR\lib\competences\resumer-notes")) 'rien n''est écrit pour le skill : seul memoire\initiatives.json change, aucun dossier de skill'
Verifier ($script:GenAppels -eq 0) 'aucun appel au cerveau pour une idée'
$refus = @('envoyer un mail aux clients', 'faire un virement chaque mois', 'lire le fichier .env', 'télécharger une page web', 'acheter des actions', 'relancer les recruteurs par message')
Verifier (@($refus | Where-Object { (New-SkillIdeeDepuisDemande $_).ok }).Count -eq 0) "demandes refusées d'emblée ($($refus.Count) : mail, virement, secrets, réseau, achat, message)"
Verifier ((Add-SkillIdee 'Mauvais Nom' 'x').motif -match 'kebab') 'nom non kebab-case refusé'

# idée automatique : la même action réussie 3 fois
Remove-Item "$TR\memoire\initiatives.json", "$TR\memoire\skills.json" -Force -ErrorAction SilentlyContinue
$act = [pscustomobject]@{ type = 'todo_ajouter'; texte = 'Appeler le comptable' }; $succes = @{ ok = $true; texte = 'ok' }
Fixer 'skills_auto' 'non'; Register-SkillAction $act $succes; Register-SkillAction $act $succes; Register-SkillAction $act $succes
Verifier (-not (Test-Path "$TR\memoire\skills.json") -and @(Get-Initiatives).Count -eq 0) 'skills_auto = "non" : aucun compteur, aucune idée'
Fixer 'skills_auto' 'oui'
Register-SkillAction $act $succes; Register-SkillAction $act $succes
Verifier (@(Get-Initiatives).Count -eq 0) 'après 2 fois : pas d''idée'
Register-SkillAction $act $succes
$auto = @(Get-Initiatives)
Verifier ($auto.Count -eq 1 -and $auto[0].type -eq 'skill_propose' -and $auto[0].titre -match '^Créer le skill « todo-ajouter-auto »$' -and $auto[0].statut -eq 'en_attente') 'après 3 fois : une idée de skill (règles, sans IA)'
Register-SkillAction $act $succes
Verifier (@(Get-Initiatives).Count -eq 1 -and @(Get-ChildItem "$TR\quarantaine" -ErrorAction SilentlyContinue).Count -eq 0) 'pas de doublon à la 4e fois ; toujours aucun fichier de skill'
Register-SkillAction $act @{ ok = $false; texte = 'e' }; Register-SkillAction ([pscustomobject]@{ type = 'todo_ajouter'; texte = 'mon mot de passe est hunter2' }) $succes
Verifier (@(Get-Initiatives).Count -eq 1) 'un échec ne compte pas'

# ---------- Jamais d'approbation automatique ----------
Fixer 'initiatives_niveau' 5
$ia = $auto[0]
Verifier (-not (Test-InitiativeSansApprobation $ia 5)) 'niveau d''autonomie 5 : une initiative skill_propose n''est PAS approuvée automatiquement'
[void](Set-InitiativeStatut $ia.id 'approuvee' 'auto (niveau 5)')
$dec = Invoke-SkillsDecision (Get-Initiative $ia.id)
Verifier ($null -eq $dec -and $script:GenAppels -eq 0 -and -not (Test-Path "$TR\quarantaine")) 'même approuvée par le moteur seul, aucune génération (seul « approuver » de Liam compte)'
Fixer 'initiatives_niveau' 1

# ---------- 2. GÉNÉRATION après « approuver » ----------
Remove-Item "$TR\memoire\initiatives.json", "$TR\memoire\skills.json" -Force -ErrorAction SilentlyContinue
$x = Cmd 'fais-moi un skill pour résumer mes notes'
Verifier ($x.traite -and $x.embeds.Count -eq 1 -and $x.embeds[0].titre -match 'Initiative n° 1' -and (Get-Initiative '1').titre -match 'resumer-notes' -and $script:GenAppels -eq 0) 'commande « fais-moi un skill pour … » : une initiative, aucun appel au cerveau'
$script:GenRep = Reponse $OK
$x = Cmd 'approuver 1'
$qd = Join-Path $TR 'quarantaine\competences\resumer-notes'
$man = Read-SkillManifeste $qd
Verifier ($script:GenAppels -eq 1) 'un seul appel au cerveau, après « approuver »'
Verifier ($script:GenSysteme -match 'Add-Action' -and $script:GenSysteme -match 'RÈGLES ABSOLUES' -and $script:GenUser -match 'resumer_notes' -and $script:GenUser -match 'Niveau de permission maximal : 1') 'le cerveau reçoit le modèle _exemple.ps1, les règles absolues, le nom, la description (donnée) et le niveau maximal'
Verifier ((Test-Path "$qd\resumer-notes.ps1") -and (Test-Path "$qd\skill.json") -and -not (Test-Path "$TR\lib\competences\resumer-notes")) 'généré dans quarantaine\competences\<nom>\ (script + manifeste), rien dans lib\competences\'
$b = [IO.File]::ReadAllBytes("$qd\resumer-notes.ps1")
Verifier ($b[0] -eq 0xEF -and $b[1] -eq 0xBB -and $b[2] -eq 0xBF) 'le script généré est en UTF-8 avec BOM'
Verifier ($man.nom -eq 'resumer-notes' -and $man.version -eq '0.1.0' -and $man.description -and @($man.declencheurs).Count -eq 2 -and @($man.outils).Count -ge 1 -and $man.permission_niveau -eq 1 -and @($man.variables_env).Count -eq 0 -and $man.sha256 -and $man.statut -eq 'quarantaine') 'manifeste : nom, version, description, déclencheurs, outils, permission, variables d''environnement (noms seulement), empreinte'
Verifier ($man.controle.statique.ok -eq $true -and $man.controle.test.ok -eq $true -and (Journal) -match 'analyse statique OK, test silencieux OK') 'résultat du contrôle écrit dans le manifeste et dans le journal'
Verifier ($x.tampon -match 'J''ai créé le skill resumer-notes' -and $x.embeds.Count -ge 1 -and $x.embeds[-1].titre -match 'prêt à valider' -and $x.embeds[-1].couleur -eq $script:CouleurBleue -and (($script:Conversation | ForEach-Object { $_.texte }) -join ' ') -match 'J''ai créé le skill resumer-notes') 'annonce « J''ai créé le skill X » (Discord + conversation) avec le rapport'
$val = Get-Initiative '2'
Verifier ($val.type -eq 'skill_propose' -and $val.titre -eq 'Valider le skill « resumer-notes »' -and $val.statut -eq 'en_attente' -and $val.raison -match 'Contrôle statique : OK ; test silencieux : OK') 'initiative d''activation créée avec le rapport'
Verifier ((Set-SkillActif 'resumer-notes' $true).ok -eq $false -and (Set-SkillActif 'resumer-notes' $true).motif -match 'quarantaine' -and -not $script:Actions.ContainsKey('resumer_notes')) 'impossible d''activer un skill non validé'
Verifier ((Cmd 'active resumer-notes').tampon -match 'Je ne peux pas activer' -and -not $script:Actions.ContainsKey('resumer_notes')) 'la commande « active » refuse aussi'

# ---------- 4. VALIDATION puis ACTIVATION ----------
$x = Cmd 'approuver 2'
$vd = Join-Path $TR 'lib\competences\resumer-notes'
$mv = Read-SkillManifeste $vd
Verifier ((Test-Path "$vd\resumer-notes.ps1") -and -not (Test-Path $qd) -and $mv.statut -eq 'valide' -and $x.tampon -match 'désactivé') 'approuvé : déplacé dans lib\competences\<nom>\, DÉSACTIVÉ'
Verifier (-not $script:Actions.ContainsKey('resumer_notes') -and (Get-Skill 'resumer-notes').etat -eq 'validé') 'validé ne veut pas dire actif : l''action n''est pas chargée'
$c0 = Import-Competences (Join-Path $TR 'lib\competences')
Verifier (-not $script:Actions.ContainsKey('resumer_notes') -and @($c0.chargees | Where-Object { $_ -match 'resumer' }).Count -eq 0) 'au démarrage, un skill validé mais non activé n''est pas chargé'
$x = Cmd 'active resumer-notes'
Verifier ($x.traite -and $x.tampon -match 'activé' -and $script:Actions.ContainsKey('resumer_notes') -and (Get-Skill 'resumer-notes').etat -eq 'actif') 'commande « active <nom> » : actif et chargé'
$rr = & ($script:Actions['resumer_notes'].run) ([pscustomobject]@{})
Verifier ($rr.ok -and $rr.texte -match '0 ligne') 'l''action du skill fonctionne dans Jarvis (écrit et lit dans son dossier)'
Verifier ((Get-Niveau ([pscustomobject]@{ type = 'resumer_notes' })).niveau -eq 1) 'ses permissions passent par lib\permissions.ps1 (niveau 1)'
$x = Cmd 'désactive resumer-notes'
Verifier ($x.traite -and -not $script:Actions.ContainsKey('resumer_notes') -and (Get-Skill 'resumer-notes').etat -eq 'validé') 'commande « désactive <nom> »'
[void](Set-SkillActif 'resumer-notes' $true); $script:Actions.Remove('resumer_notes')
$c1 = Import-Competences (Join-Path $TR 'lib\competences')
Verifier ($script:Actions.ContainsKey('resumer_notes') -and @($c1.chargees | Where-Object { $_ -match 'skill resumer-notes' }).Count -eq 1) 'au démarrage, Import-Competences recharge les skills actifs'
$script:Actions.Remove('resumer_notes')
Add-Content "$vd\resumer-notes.ps1" "`n# modifié après la validation" -Encoding UTF8
$c2 = Import-Competences (Join-Path $TR 'lib\competences')
Verifier (-not $script:Actions.ContainsKey('resumer_notes') -and @($c2.echecs | Where-Object { $_ -match 'a changé' }).Count -eq 1 -and (Journal) -match 'Skill IGNORÉ') 'un script modifié après la validation n''est PAS rechargé (empreinte)'

# ---------- Contrôle en échec : écarté, rien d'activable ----------
$n0 = @(Get-Initiatives).Count
[void](New-SkillIdeeDepuisDemande 'nettoyer mes notes')
$mal = Script-Pour 'nettoyer-notes' 'nettoyer_notes'; $mal = $mal.Replace('param($a)', "param(`$a)`n    Invoke-Expression (Get-Content 'C:\x\.env' -Raw)")
$script:GenRep = Reponse $mal; $g0 = $script:GenAppels
$x = Cmd "approuver $((@(Get-Initiatives) | Where-Object { $_.titre -match 'nettoyer-notes' }).id)"
$mm = Read-SkillManifeste (Join-Path $TR 'quarantaine\competences\nettoyer-notes')
Verifier ($script:GenAppels -eq $g0 + 1 -and $mm.statut -eq 'echec_controle' -and $mm.controle.statique.ok -eq $false -and $mm.controle.test.ok -eq $false -and $mm.controle.test.motif -match 'non lancé') 'script dangereux : analyse statique en échec, le test n''est même pas lancé, statut « echec_controle »'
Verifier (@(Get-Initiatives | Where-Object { $_.titre -match 'Valider le skill « nettoyer' }).Count -eq 0 -and $x.tampon -match 'écarté' -and $x.embeds[-1].couleur -eq $script:CouleurRouge -and (Journal) -match 'ÉCHEC') 'aucune initiative d''activation, message « écarté », carte rouge, échec journalisé'
Verifier ((Set-SkillActif 'nettoyer-notes' $true).ok -eq $false -and -not $script:Actions.ContainsKey('nettoyer_notes')) 'un skill écarté ne peut pas être activé'
# cerveau muet
[void](New-SkillIdeeDepuisDemande 'lister mes rappels'); $script:GenRep = $null
$x = Cmd "approuver $((@(Get-Initiatives) | Where-Object { $_.titre -match 'lister-rappels' }).id)"
Verifier ($x.tampon -match 'pas pu créer' -and -not (Test-Path (Join-Path $TR 'quarantaine\competences\lister-rappels'))) 'cerveau indisponible : message poli, aucun fichier'
# idée rejetée
[void](New-SkillIdeeDepuisDemande 'compter mes tâches'); $g1 = $script:GenAppels
$ir = @(Get-Initiatives | Where-Object { $_.titre -match 'compter-taches' })[0]
$x = Cmd "rejeter $($ir.id)"
Verifier ($script:GenAppels -eq $g1 -and $x.tampon -match 'abandonnée' -and -not (Test-Path (Join-Path $TR 'quarantaine\competences\compter-taches'))) 'idée rejetée : aucun appel au cerveau, rien écrit'

# ---------- Refus de la validation : archivé + leçon ----------
[void](New-SkillIdeeDepuisDemande 'trier mes fichiers')
$script:GenRep = Reponse (Script-Pour 'trier-fichiers' 'trier_fichiers')
[void](Cmd "approuver $((@(Get-Initiatives) | Where-Object { $_.titre -match 'Créer le skill « trier-fichiers' }).id)")
$vid = (@(Get-Initiatives) | Where-Object { $_.titre -match 'Valider le skill « trier-fichiers' }).id
Remove-Item "$TR\memoire\lecons.json" -Force -ErrorAction SilentlyContinue
$x = Cmd "rejeter $vid"
$arch = @(Get-ChildItem (Join-Path $TR 'quarantaine\refuses') -Directory | Where-Object { $_.Name -like 'trier-fichiers-*' })
$ma = $(if ($arch.Count) { Read-SkillManifeste $arch[0].FullName } else { $null })
Verifier ($arch.Count -eq 1 -and $ma.statut -eq 'refuse' -and -not (Test-Path (Join-Path $TR 'quarantaine\competences\trier-fichiers')) -and -not (Test-Path (Join-Path $TR 'lib\competences\trier-fichiers')) -and $x.tampon -match 'refusé et archivé') 'refusé : archivé dans quarantaine\refuses\, jamais dans lib\competences\'
$lc = @(Get-Lecons | Where-Object { @($_.etiquettes) -contains 'skill' -and $_.regle -match 'trier-fichiers' })
Verifier ($lc.Count -eq 1 -and $x.tampon -match 'leçon') 'une leçon est écrite via lib\lecons.ps1'
[void](New-SkillIdeeDepuisDemande 'compter mes notes'); $script:GenRep = Reponse (Script-Pour 'compter-notes' 'compter_notes')
[void](Cmd "approuver $((@(Get-Initiatives) | Where-Object { $_.titre -match 'Créer le skill « compter-notes' }).id)")
Fixer 'lecons_actif' 'non'; Remove-Item "$TR\memoire\lecons.json" -Force -ErrorAction SilentlyContinue
[void](Cmd "rejeter $((@(Get-Initiatives) | Where-Object { $_.titre -match 'Valider le skill « compter-notes' }).id)")
Verifier (-not (Test-Path "$TR\memoire\lecons.json") -and (Journal) -match 'leçon non écrite') 'leçons désactivées : le refus est archivé mais aucune leçon n''est écrite (journalisé)'
Fixer 'lecons_actif' 'oui'

# ---------- Commandes ----------
$x = Cmd 'skills'
$noms = ($x.embeds[0].champs | ForEach-Object { $_.nom }) -join ' | '; $vals = ($x.embeds[0].champs | ForEach-Object { $_.valeur }) -join ' '
Verifier ($x.traite -and $x.embeds[0].titre -eq 'Skills' -and $x.embeds[0].couleur -eq $script:CouleurBleue -and $noms -match 'Actifs \(1\)' -and $noms -match 'En quarantaine \(1\)' -and $noms -match 'Refusés' -and $vals -match 'resumer-notes' -and $vals -match 'nettoyer-notes \S* ?.*contrôle échoué|contrôle échoué') 'commande « skills » : actifs, en quarantaine (contrôle échoué), refusés'
Fixer 'discord_style' 'texte'; $x = Cmd 'skills'
Verifier ($x.traite -and $x.embeds.Count -eq 0 -and $x.tampon -match 'resumer-notes : actif') 'style « texte » : liste simple'
Fixer 'discord_style' 'embed'
Verifier (-not (Cmd 'active sourdine').traite -and -not (Cmd 'désactive le mode jeu').traite -and -not (Cmd 'active le mode jeu').traite) '« active sourdine », « active le mode jeu » ne sont pas pris pour des commandes de skills'
$x = Cmd 'supprime le skill resumer-notes'
$ar = @(Get-ChildItem (Join-Path $TR 'quarantaine\refuses') -Directory | Where-Object { $_.Name -like 'resumer-notes-*' })
Verifier ($x.traite -and $ar.Count -eq 1 -and (Read-SkillManifeste $ar[0].FullName).statut -eq 'archive' -and (Test-Path "$($ar[0].FullName)\resumer-notes.ps1") -and -not (Get-Skill 'resumer-notes') -and -not $script:Actions.ContainsKey('resumer_notes')) '« supprime le skill » : désactivé et ARCHIVÉ (rien n''est supprimé définitivement)'
Verifier ((Cmd 'supprime le skill inexistant-xyz').tampon -match 'ne trouve pas') 'skill inconnu : réponse polie'
Verifier ((Cmd 'fais-moi un skill pour envoyer un mail aux clients').tampon -match 'ne peux pas créer' -and @(Get-Initiatives | Where-Object { $_.titre -match 'envoyer' }).Count -eq 0) 'demande interdite : refusée avec la raison, aucune initiative'
Fixer 'skills_auto' 'non'; $ni = @(Get-Initiatives).Count
Verifier ((Cmd 'fais-moi un skill pour trier mes notes').tampon -match 'désactivée' -and @(Get-Initiatives).Count -eq $ni -and (Cmd 'skills').traite) 'skills_auto = "non" : « fais-moi un skill » refusé poliment, la liste reste disponible'
Fixer 'skills_auto' 'oui'

# ---------- Compétences existantes intactes ----------
$noms = @(); foreach ($f in 'idees-contenu.ps1', 'point-saas.ps1', '_exemple.ps1') { $e = $null; [void][Management.Automation.Language.Parser]::ParseFile((Join-Path $Root "lib\competences\$f"), [ref]$null, [ref]$e); if (-not $e) { $noms += $f } }
$res = Import-Competences (Join-Path $Root 'lib\competences')
Verifier ($noms.Count -eq 3 -and $res.echecs.Count -eq 0 -and @($res.chargees | Where-Object { $_ -match 'idees-contenu|point-saas' }).Count -eq 2 -and (Test-Path (Join-Path $Root 'lib\competences\_exemple.ps1'))) 'idees-contenu.ps1, point-saas.ps1 et _exemple.ps1 intacts et toujours chargés comme avant'
$realC2 = @(Get-ChildItem (Join-Path $Root 'lib\competences') -Recurse -File | ForEach-Object { "$($_.Name):$((Get-FileHash $_.FullName).Hash)" }) -join '|'
$realQ2 = @(Get-ChildItem (Join-Path $Root 'quarantaine') -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object { "$($_.FullName):$($_.Length)" }) -join '|'
Verifier ($realC -eq $realC2 -and $realQ -eq $realQ2) 'le test n''a écrit ni dans lib\competences\ ni dans quarantaine\ de votre installation'

# ---------- Cartes ----------
$l = @(1..8 | ForEach-Object { [pscustomobject]@{ nom = "skill-$_"; etat = @('actif', 'validé', 'quarantaine', 'refusé')[$_ % 4]; description = ('d' * 250); statut = 'valide' } })
$gl = New-EmbedSkills $l; $tot = $gl.titre.Length + $gl.description.Length + $gl.pied.Length; foreach ($f in $gl.champs) { $tot += $f.nom.Length + $f.valeur.Length }
Verifier ($tot -le 6000 -and ($gl.champs | Where-Object { $_.valeur.Length -gt 1024 }).Count -eq 0 -and $gl.titre -match '^[\p{L}0-9]' -and (New-EmbedSkills @()).description -match 'Aucun skill') 'cartes : limites de Discord respectées, titre sans emoji, liste vide polie'

# ---------- Garde-fous du code ----------
$src = Get-Content (Join-Path $Root 'lib\skills.ps1') -Raw -Encoding UTF8; $srcCode = (($src -split "`n") | Where-Object { $_ -notmatch '^\s*#|^\s*@\(''|^- |SkillsEcrituresFichier' }) -join "`n"      # (hors commentaires, tableau des règles de refus et consignes au cerveau : ils CITENT les mots interdits)
Verifier ([regex]::Matches($srcCode, 'Invoke-Claude \$systeme').Count -eq 1 -and $srcCode -notmatch '(?i)Invoke-Ollama|Invoke-RestMethod|Invoke-WebRequest|Start-Process\s+[-$''"a-z]|Invoke-Expression\s+\$|\biex\s+[$(]') 'un seul appel au cerveau (dans la génération), ni Ollama, ni réseau, ni lancement de programme, ni iex'
$w = @($srcCode -split "`n" | Where-Object { $_ -match 'WriteAllText' })
Verifier ($w.Count -eq 3 -and @($w | Where-Object { $_ -notmatch 'Join-Path \$dossier|\$fichier|\$copie' }).Count -eq 0) 'le module n''écrit que le manifeste, le script généré et la copie du test (dans des dossiers de skills ou temporaires)'
Verifier ($srcCode -notmatch '(?i)Set-Content|Out-File|Add-Content' -and $srcCode -notmatch '\$script:(TypesNiveau3|MotifsInterdits)\s*=') 'ni config, ni interdits, ni permissions modifiés'
$js = Get-Content (Join-Path $Root 'jarvis.ps1') -Raw -Encoding UTF8; $dc = Get-Content (Join-Path $Root 'lib\discord.ps1') -Raw -Encoding UTF8; $cv = Get-Content (Join-Path $Root 'lib\cerveau.ps1') -Raw -Encoding UTF8; $cp = Get-Content (Join-Path $Root 'lib\competences.ps1') -Raw -Encoding UTF8; $ini = Get-Content (Join-Path $Root 'lib\initiatives.ps1') -Raw -Encoding UTF8
Verifier ($js -match 'lib\\skills\.ps1' -and $dc -match 'Invoke-SkillsCommande' -and $cv -match 'Register-SkillAction' -and $cp -match 'Import-SkillsActifs' -and $ini -match 'Invoke-SkillsDecision') 'câblage : jarvis.ps1, discord.ps1, cerveau.ps1, competences.ps1, initiatives.ps1'
$oct = [IO.File]::ReadAllBytes((Join-Path $Root 'lib\skills.ps1'))
Verifier ($oct[0] -eq 0xEF -and $oct[1] -eq 0xBB -and $oct[2] -eq 0xBF) 'lib\skills.ps1 en UTF-8 avec BOM'
Verifier ((Get-Content (Join-Path $Root 'README.md') -Raw -Encoding UTF8) -match 'skills_auto') 'README : skills décrits'
Verifier ((Get-FileHash (Join-Path $Root 'config.json')).Hash -eq $hashConfig) 'config.json réel inchangé par le test'

Remove-Variable SkillDossiers -Scope Global -ErrorAction SilentlyContinue
Write-Host ''
Remove-Item $TR -Recurse -Force -ErrorAction SilentlyContinue
if ($echecs) { Write-Host "ÉCHEC : $echecs vérification(s) en échec." -ForegroundColor Red; exit 1 }
Write-Host 'TOUT EST VERT.'
