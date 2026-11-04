# Test SILENCIEUX de l'agent de développement du SaaS (lib\dev-agent.ps1) : commandes Discord « dev : », file d'attente, créneau de nuit, branche jarvis/<date>-<slug>, push de la branche SEULE,
# garde-fous (clés de production, secrets, .env, main, force-push, jeton), « valide » / « refuse », et un essai de bout en bout avec un DÉPÔT GIT LOCAL (bare) et un FAUX claude.
# Aucun réseau (GitHub est un bouchon), aucun vrai claude, aucun jeton réel, aucun son, aucune fenêtre. Tout est dans des dossiers temporaires. Code de sortie 0 = réussi.
$ErrorActionPreference = 'Stop'
$env:JARVIS_TEST = '1'
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $Root 'lib\journal.ps1')
$TR = Join-Path $env:TEMP ('jarvis-test-' + [guid]::NewGuid().ToString('N').Substring(0, 8)); New-Item -ItemType Directory $TR, "$TR\memoire", "$TR\logs" | Out-Null; $script:JarvisRoot = $TR
'# To-do' | Set-Content "$TR\memoire\todo.md" -Encoding UTF8; '# N' | Set-Content "$TR\memoire\notes.md" -Encoding UTF8; '# R' | Set-Content "$TR\memoire\resume.md" -Encoding UTF8
$Config = Get-Content $(if ($env:JARVIS_CONFIG -and (Test-Path $env:JARVIS_CONFIG)) { $env:JARVIS_CONFIG } else { Join-Path $Root 'config.json' }) -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($l in 'business', 'discord', 'dev-agent') { . (Join-Path $Root "lib\$l.ps1") }      # (mêmes fichiers que le processus dev-agent.ps1 : journal, business, discord, dev-agent ; rien d'autre, sinon un appel à une fonction absente passerait inaperçu)
$script:JarvisRoot = $TR; $script:PolitesseFixe = $true
$echecs = 0
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }
function Fixer([string]$cle, $val) { if ($Config.PSObject.Properties[$cle]) { $Config.$cle = $val } else { $Config | Add-Member -NotePropertyName $cle -NotePropertyValue $val } }
function Effacer([string]$cle) { if ($Config.PSObject.Properties[$cle]) { $Config.PSObject.Properties.Remove($cle) } }
$vraie = Get-Content (Join-Path $Root 'config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
function Journal { $f = Join-Path $TR ('logs\journal-{0}.md' -f (Get-Date -Format 'yyyy-MM-dd')); if (Test-Path $f) { Get-Content $f -Raw -Encoding UTF8 } else { '' } }
function Dire([string]$texte) { $script:DiscordTampon = New-Object System.Collections.Generic.List[string]; $script:DiscordEmbeds.Clear(); $r = Invoke-DevCommande $texte; @{ r = $r; texte = ($script:DiscordTampon -join ' ') } }
function Decider([string]$texte) { $script:DiscordTampon = New-Object System.Collections.Generic.List[string]; $r = Invoke-DevDecision $texte; @{ r = $r; texte = ($script:DiscordTampon -join ' ') } }
function Gt { & git.exe -C $args[0] @($args | Select-Object -Skip 1) 2>&1 | Out-String }
$TOKEN = 'ghp_' + ('A1b2C3d4' * 5)      # faux jeton (jamais valable)
$env:GITHUB_TOKEN_DEV = $TOKEN; $script:Secrets += $TOKEN
$env:STRIPE_RESTRICTED_KEY = 'rk_live_FAUSSE0123456789abcdefgh'; $env:SUPABASE_READ_KEY = 'fausse-cle-supabase-0123456789'
$script:Notifs = @(); $script:DevNotifStub = { param($salon, $texte, $embed) $script:Notifs += @{ salon = $salon; texte = $texte; embed = $embed } }
$script:ApiAppels = @(); $script:DevApiStub = { param($m, $p, $c) $script:ApiAppels += @{ m = $m; p = $p; c = $c }; if ($m -eq 'POST') { return [pscustomobject]@{ number = 7; html_url = 'https://github.com/Liam2109/ecom-quiz/pull/7' } }; if ($m -eq 'GET') { return [pscustomobject]@{ statuses = @(); check_runs = @() } }; [pscustomobject]@{ merged = $true } }

Write-Host '1) Désactivé par défaut'
Verifier ($vraie.dev_agent -eq 'non' -and $vraie.dev_depot -eq 'Liam2109/ecom-quiz' -and $vraie.dev_creneau -eq '01:00-06:00' -and $vraie.dev_max_taches_nuit -eq 3 -and $vraie.dev_minutes_par_tache -eq 30 -and $vraie.dev_dossier -eq 'C:\Projets\ecom-quiz') 'config.json : dev_agent = "non", dépôt Liam2109/ecom-quiz, dossier C:\Projets\ecom-quiz, créneau 01:00-06:00, 3 tâches, 30 minutes'
$c = Get-DevConfig; Verifier (-not $c.actif -and $c.fusion) 'sans réglage local : agent inactif'
$r = Dire 'dev : ajoute un champ prénom'; Verifier ($r.r -and $r.texte -match 'désactivé' -and @((Get-DevEtat).taches).Count -eq 0) 'inactif : « dev : ... » répond « désactivé » et ne met rien en file'
Verifier (-not (Update-DevAgent ([datetime]'2026-10-17T02:00:00'))) 'inactif : la boucle ne lance rien'
$r = Decider 'valide'; Verifier (-not $r.r) 'inactif : « valide » reste un message ordinaire'
Verifier (-not (Invoke-DevCommande 'ouvre chrome') -and -not (Invoke-DevCommande 'développe le site') -and -not (Invoke-DevCommande 'devine : quoi')) 'seul le préfixe « dev : » est reconnu'
Verifier (-not (Get-DevConfig).push -and $vraie.dev_push -eq 'non') 'config.json : dev_push = "non" (aucun envoi vers GitHub)'
Fixer 'dev_push' 'oui'; Verifier ((Get-DevConfig).push) 'dev_push = "oui" active le push'
Fixer 'dev_agent' 'oui'; Verifier ((Get-DevConfig).actif) 'config.local.json : dev_agent = "oui" l''active'

Write-Host '2) Fonctions pures'
Verifier ((ConvertTo-DevSlug 'Ajoute un champ « prénom » au formulaire !') -eq 'ajoute-un-champ-prenom-au-formulaire' -and (ConvertTo-DevSlug '???') -eq 'tache' -and (ConvertTo-DevSlug ('mot ' * 40)).Length -le 40) 'slug : sans accents ni symboles, 40 caractères au plus'
Verifier ((Get-DevBrancheNom 'mon-slug' ([datetime]'2026-10-17')) -eq 'jarvis/2026-10-17-mon-slug') 'branche : jarvis/<date>-<slug>'
foreach ($b in 'main', 'master', 'HEAD', 'jarvis/', 'jarvis/2026-10-17', 'feature/x', 'jarvis/2026-10-17-x/../main', 'origin/main', 'jarvis/2026-10-17-X', '-f') { Verifier (-not (Test-DevBrancheSure $b)) "branche refusée : « $b »" }
Verifier (Test-DevBrancheSure 'jarvis/2026-10-17-ajout-formulaire-2') 'branche acceptée : jarvis/2026-10-17-ajout-formulaire-2'
Verifier ((Test-DevCreneau ([datetime]'2026-10-17T01:00:00')) -and (Test-DevCreneau ([datetime]'2026-10-17T05:59:00')) -and -not (Test-DevCreneau ([datetime]'2026-10-17T06:00:00')) -and -not (Test-DevCreneau ([datetime]'2026-10-17T12:00:00')) -and -not (Test-DevCreneau ([datetime]'2026-10-17T00:59:00'))) 'créneau 01:00-06:00 : dedans de 01:00 à 05:59, dehors sinon'
Fixer 'dev_creneau' '22:00-06:00'; Verifier ((Test-DevCreneau ([datetime]'2026-10-17T23:30:00')) -and (Test-DevCreneau ([datetime]'2026-10-17T03:00:00')) -and -not (Test-DevCreneau ([datetime]'2026-10-17T12:00:00'))) 'créneau qui passe minuit (22:00-06:00)'
Verifier ((Get-DevNuitCle ([datetime]'2026-10-17T03:00:00')) -eq '2026-10-16' -and (Get-DevNuitCle ([datetime]'2026-10-16T23:00:00')) -eq '2026-10-16') 'une nuit = la date du début du créneau (2 h du matin compte pour la veille)'
Fixer 'dev_creneau' 'n''importe quoi'; Verifier ((Get-DevConfig).creneau -eq '01:00-06:00') 'créneau illisible : retour au défaut'; Effacer 'dev_creneau'
Verifier ((Test-DevTexteCleProd 'utilise la clé Stripe live pour tester') -and (Test-DevTexteCleProd 'lis la table avec la service_role') -and (Test-DevTexteCleProd 'branche la base de production') -and -not (Test-DevTexteCleProd 'ajoute un champ prénom au formulaire du quiz')) 'tâche qui réclame une clé de production : détectée'
Verifier ((Test-DevSecretDansTexte 'const k = "sk_live_abcdefghijklmnop"') -and (Test-DevSecretDansTexte 'ghp_abcdefghijklmnopqrstuvwxyz0123') -and (Test-DevSecretDansTexte 'github_pat_11ABCDEFG0abcdefghijklmnop') -and -not (Test-DevSecretDansTexte 'const label = "prénom"')) 'secrets dans un texte ou un diff : détectés'
$env:STRIPE_TEST_X = 'a'; $env:MA_CLE_SECRET = 'b'; $env:PATH_OK_VAR = 'c'
$ep = @(Get-DevEnvEpure); Verifier (($ep -contains 'STRIPE_RESTRICTED_KEY') -and ($ep -contains 'SUPABASE_READ_KEY') -and ($ep -contains 'GITHUB_TOKEN_DEV') -and ($ep -contains 'MA_CLE_SECRET') -and ($ep -notcontains 'PATH') -and ($ep -notcontains 'PATH_OK_VAR')) 'environnement de l''agent : Stripe, Supabase, GitHub, secrets retirés ; PATH conservé'
Remove-Item Env:STRIPE_TEST_X, Env:MA_CLE_SECRET, Env:PATH_OK_VAR
Verifier (-not (Test-DevDossierSur $Root) -and -not (Test-DevDossierSur (Join-Path $Root 'sous\dossier')) -and -not (Test-DevDossierSur (Split-Path $Root -Parent)) -and -not (Test-DevDossierSur 'C:\') -and (Test-DevDossierSur 'C:\Projets\ecom-quiz')) 'dossier de travail : jamais Jarvis, un de ses sous-dossiers, son parent ni une racine de disque'

Write-Host '3) Commandes « dev : » depuis Discord'
$r = Dire 'dev : ajoute un champ prénom au formulaire du quiz'
Verifier ($r.r -and $r.texte -match '^Tâche 1 enregistrée' -and $r.texte -match '01:00-06:00' -and $r.texte -match 'dev : maintenant') 'tâche mise en file, avec le rappel du créneau et de « dev : maintenant »'
Verifier ((Get-DevTache 1).statut -eq 'file' -and (Get-DevTache 1).slug -like 'ajoute-un-champ-prenom-au-formulaire*' -and (Get-DevTache 1).slug.Length -le 40) 'la file garde statut et slug'
$r = Dire 'DEV: corrige le bouton du pied de page'; Verifier ($r.texte -match '^Tâche 2 enregistrée') 'le préfixe est tolérant (majuscules, sans espace)'
$r = Dire 'dev : liste'; Verifier ($r.texte -match '#1 \[file\]' -and $r.texte -match '#2 \[file\]') '« dev : liste » montre la file'
$r = Dire 'dev : annule 2'; Verifier ($r.texte -match 'annulée' -and (Get-DevTache 2).statut -eq 'annulee') '« dev : annule 2 »'
$r = Dire 'dev : utilise la clé Stripe live pour tester les paiements'; Verifier ($r.texte -match 'clé de production' -and @((Get-DevEtat).taches).Count -eq 2) 'tâche qui réclame une clé de production : refusée dès Discord'
$r = Dire "dev : mets ce jeton ghp_abcdefghijklmnopqrstuvwxyz0123 dans le code"; Verifier ($r.texte -match 'clé d.accès' -and @((Get-DevEtat).taches).Count -eq 2 -and (Journal) -notmatch 'ghp_abcdefghijkl') 'secret dans la tâche : refusé, non enregistré, non journalisé'
$r = Dire ('dev : ' + ('x' * 1100)); Verifier ($r.texte -match 'trop longue') 'tâche de plus de 1 000 caractères : refusée'
$r = Dire 'dev :'; Verifier ($r.texte -match 'par exemple') 'dev : vide -> aide'
$r = Dire 'dev : maintenant'; Verifier ($r.texte -match 'tout de suite' -and (Get-DevEtat).maintenant) '« dev : maintenant » demande l''exécution immédiate'
$e = Get-DevEtat; $e.maintenant = $false; Save-DevEtat $e

Write-Host '4) Planification : la nuit, 3 tâches au plus, ou tout de suite'
$script:DevRunnerLance = $null
foreach ($k in 3, 4, 5, 6) { [void](Add-DevTache "tâche numéro $k") }
$script:DevProchainTour = [datetime]::MinValue; $r = Update-DevAgent ([datetime]'2026-10-17T12:00:00')
Verifier (-not $r -and $null -eq $script:DevRunnerLance) 'en plein jour : rien ne démarre'
$script:DevProchainTour = [datetime]::MinValue; $r = Update-DevAgent ([datetime]'2026-10-17T02:00:00')
Verifier ($r -and $script:DevRunnerLance -eq 1) 'à 02:00 : la plus ancienne tâche en file (n°1) démarre'
$script:DevProchainTour = [datetime]::MinValue; $r = Update-DevAgent ([datetime]'2026-10-17T02:00:10')
Verifier (-not $r -or $script:DevRunnerLance -eq 1) 'throttle : pas de relance avant 30 s'
foreach ($id in 1, 3, 4) { Set-DevTache $id @{ statut = 'termine'; debut = '2026-10-17T02:00:00'; nuit = '2026-10-17' } }
$script:DevRunnerLance = $null; $script:DevProchainTour = [datetime]::MinValue; $r = Update-DevAgent ([datetime]'2026-10-17T04:00:00')
Verifier (-not $r -and $null -eq $script:DevRunnerLance) 'quand 3 tâches ont déjà tourné cette nuit : plus aucune avant la nuit suivante'
$script:DevProchainTour = [datetime]::MinValue; $r = Update-DevAgent ([datetime]'2026-10-18T02:00:00')
Verifier ($r -and $script:DevRunnerLance -eq 5) 'nuit suivante : la tâche n°5 démarre'
Set-DevTache 5 @{ statut = 'file' }; $e = Get-DevEtat; $e.maintenant = $true; Save-DevEtat $e
$script:DevRunnerLance = $null; $script:DevProchainTour = [datetime]::MinValue; $r = Update-DevAgent ([datetime]'2026-10-17T14:00:00')
Verifier ($r -and $script:DevRunnerLance -eq 5) '« dev : maintenant » : démarre en journée aussi'
Set-DevTache 5 @{ statut = 'en_cours'; debut = (Get-Date).ToString('o') }
$e = Get-DevEtat; $e.pid = 0; Save-DevEtat $e; $script:Notifs = @(); $script:DevProchainTour = [datetime]::MinValue; [void](Update-DevAgent ([datetime]'2026-10-17T14:00:00'))
Verifier ((Get-DevTache 5).statut -eq 'echec' -and @($script:Notifs | Where-Object { $_.salon -eq 'systeme' -and $_.texte -match 'interrompue' }).Count -eq 1) 'processus disparu en cours de tâche : tâche en échec + alerte Discord (pas de relance automatique)'
$e = Get-DevEtat; $e.maintenant = $false; Save-DevEtat $e
foreach ($id in 3, 4, 6) { Set-DevTache $id @{ statut = 'annulee' } }

Write-Host '5) Garde-fous dans le code'
$src = Get-Content (Join-Path $Root 'lib\dev-agent.ps1') -Raw -Encoding UTF8; $run = Get-Content (Join-Path $Root 'dev-agent.ps1') -Raw -Encoding UTF8
$codeSeul = ($src -split "`n" | Where-Object { $_ -notmatch '^\s*#' }) -join "`n"
Verifier ($codeSeul -notmatch "--force|--force-with-lease|'-f'|push\s+(-f|--delete)|'--delete'|'-D'|'-d'|branch\s+(-d|-D|--delete)|push.*\+refs|'--mirror'|reset', '--hard|clean', '-f") 'jamais de force-push, de suppression de branche, de --mirror ni de reset --hard dans lib\dev-agent.ps1'
Verifier ($codeSeul -match 'refs/heads/\$\{branche\}:refs/heads/\$\{branche\}' -and $codeSeul -match 'Test-DevBrancheSure \$branche') 'le seul push : refs/heads/<branche>:refs/heads/<branche>, après contrôle du nom'
Verifier ($codeSeul -match 'GIT_CONFIG_VALUE_0' -and $codeSeul -notmatch 'Set-Content[^\n]*\$tok|WriteAllText[^\n]*\$tok|\s-Token\s|extraheader=\$|clone[^\n]*\$tok') 'le jeton GitHub ne passe que par l''environnement du processus git (jamais en argument, en URL ni dans un fichier)'
Verifier ($codeSeul -match 'Get-DevEnvEpure' -and $codeSeul -match 'Find-DevCleProductionDossier' -and $codeSeul -match 'JARVIS_BESOIN_CLE') 'environnement épuré, scan des .env du dépôt, arrêt si l''agent réclame une clé'
Verifier ($run -match 'Invoke-DevTache' -and $run -match 'Send-DevAlerte') 'dev-agent.ps1 : processus séparé, alerte Discord en cas d''erreur'
$js = Get-Content (Join-Path $Root 'jarvis.ps1') -Raw -Encoding UTF8; $dc = Get-Content (Join-Path $Root 'lib\discord.ps1') -Raw -Encoding UTF8
Verifier ($js -match 'Update-DevAgent' -and $js -match 'lib\\dev-agent\.ps1' -and $dc -match 'Invoke-DevCommande' -and $dc -match 'Invoke-DevDecision') 'branché sur la boucle de Jarvis et sur les messages Discord'
Verifier (-not ($js -split "`n" | Where-Object { $_ -match '^\s*(Update-DevAgent|Update-VeilleTrain)\b' }) -and $js -match '\[void\]\(Update-DevAgent\)' -and $js -match '\[void\]\(Update-VeilleTrain\)') 'boucle de jarvis.ps1 : Update-DevAgent / Update-VeilleTrain renvoient un booléen, capturé par [void] (sinon « False » s''écrit en continu dans la console)'

Write-Host '6) « valide » / « refuse »'
$e = Get-DevEtat; $e.taches = @(); $e.suivant = 1; Save-DevEtat $e
$r = Decider 'valide'; Verifier (-not $r.r) '« valide » sans tâche terminée : message ordinaire (aucune action)'
$t = Add-DevTache 'ajoute un champ prénom'; Set-DevTache 1 @{ statut = 'termine'; branche = 'jarvis/2026-10-17-ajoute-un-champ-prenom'; fichiers = @('a.tsx') }
$script:ApiAppels = @(); $r = Decider 'refuse'
Verifier ($r.r -and $r.texte -match 'refusée' -and $r.texte -match 'reste en place' -and (Get-DevTache 1).statut -eq 'refuse' -and $script:ApiAppels.Count -eq 0) '« refuse » : branche laissée, rien fusionné, aucun appel GitHub, aucune suppression'
Set-DevTache 1 @{ statut = 'termine' }; $script:ApiAppels = @(); $r = Decider 'valide'
Verifier ($r.r -and $r.texte -match 'fusionné dans main' -and $script:ApiAppels.Count -eq 2 -and $script:ApiAppels[0].m -eq 'POST' -and $script:ApiAppels[0].p -eq '/repos/Liam2109/ecom-quiz/pulls' -and $script:ApiAppels[0].c.head -eq 'jarvis/2026-10-17-ajoute-un-champ-prenom' -and $script:ApiAppels[0].c.base -eq 'main' -and $script:ApiAppels[1].m -eq 'PUT' -and $script:ApiAppels[1].p -match '/pulls/7/merge$' -and (Get-DevTache 1).statut -eq 'valide') '« valide » : pull request de la branche vers main puis fusion (le seul chemin vers main)'
Set-DevTache 1 @{ statut = 'termine' }; Fixer 'dev_fusion_valide' 'non'; $script:ApiAppels = @(); $r = Decider 'valide 1'
Verifier ($r.texte -match 'à fusionner vous-même' -and $script:ApiAppels.Count -eq 1 -and $script:ApiAppels[0].m -eq 'POST') 'dev_fusion_valide = "non" : seulement la pull request, la fusion reste à Liam'
Effacer 'dev_fusion_valide'
Set-DevTache 1 @{ statut = 'termine'; branche = 'main' }; $script:ApiAppels = @(); $r = Decider 'valide'
Verifier ($r.texte -match 'Branche refusée' -and $script:ApiAppels.Count -eq 0) 'une tâche dont la branche serait main : jamais fusionnée'
Set-DevTache 1 @{ statut = 'echec' }; Verifier (-not (Decider 'valide').r) 'seule une tâche « terminée » peut être validée'

Write-Host '7) De bout en bout : dépôt git local, faux claude'
$GT = Join-Path $env:TEMP ('jarvis-test-dev-' + [guid]::NewGuid().ToString('N').Substring(0, 8)); New-Item -ItemType Directory $GT | Out-Null
$bare = Join-Path $GT 'origine.git'; $seed = Join-Path $GT 'seed'; $travail = Join-Path $GT 'travail'
& git init -q --bare -b main $bare 2>&1 | Out-Null
& git init -q -b main $seed 2>&1 | Out-Null
'# ecom-quiz' | Set-Content (Join-Path $seed 'README.md') -Encoding UTF8
'{ "name": "ecom-quiz", "scripts": { "build": "echo build-ok", "test": "echo test-ok" } }' | Set-Content (Join-Path $seed 'package.json') -Encoding ASCII
'.env' | Set-Content (Join-Path $seed '.gitignore') -Encoding ASCII
& git -C $seed add -A 2>&1 | Out-Null; & git -C $seed -c user.name=t -c user.email=t@t commit -q -m init 2>&1 | Out-Null
& git -C $seed remote add origin $bare 2>&1 | Out-Null; & git -C $seed push -q origin main 2>&1 | Out-Null
$mainAvant = (Gt $bare 'rev-parse' 'main').Trim()
$env:JARVIS_TEST_DEV_REMOTE = $bare; $Config | Add-Member -NotePropertyName dev_dossier -NotePropertyValue $travail -Force
function Faux-Claude([string]$nom, [string]$corps) { $f = Join-Path $GT "$nom.cmd"; ("@echo off`r`n" + $corps) | Set-Content $f -Encoding ASCII; $f }
$ok = Faux-Claude 'ok' "<nul set /p=`"export const prenom = true;`">nouveau.ts`r`necho Ajout du champ prenom dans nouveau.ts.`r`necho Rien d autre a signaler."
Fixer 'dev_agent' 'oui'; $e = Get-DevEtat; $e.taches = @(); $e.suivant = 1; Save-DevEtat $e
$t = Add-DevTache 'ajoute un champ prénom au formulaire'
$env:JARVIS_TEST_DEV_CLAUDE = $ok; $script:Notifs = @(); $script:ApiAppels = @()
$res = Invoke-DevTache 1
Verifier ($res.ok -and $res.branche -match '^jarvis/\d{4}-\d{2}-\d{2}-ajoute-un-champ-prenom-au-formulaire$') "tâche exécutée : branche $($res.branche)"
$tk = Get-DevTache 1
Verifier ($tk.statut -eq 'termine' -and @($tk.fichiers) -contains 'nouveau.ts' -and $tk.lien -match '^https://github.com/Liam2109/ecom-quiz/tree/jarvis/') 'état : terminée, fichiers modifiés et lien de la branche notés'
$branches = Gt $bare 'branch' '--list'
Verifier ($branches -match 'jarvis/' -and $branches -match 'main') 'la branche jarvis/... est poussée sur l''origine'
Verifier ((Gt $bare 'rev-parse' 'main').Trim() -eq $mainAvant) 'main n''a PAS bougé sur l''origine'
Verifier ((Gt $bare 'show' "$($res.branche):nouveau.ts") -match 'prenom') 'le contenu de la branche contient le travail de l''agent'
$ent = $script:Notifs | Where-Object { $_.salon -eq 'jarvis' -and $_.embed } | Select-Object -First 1
$champs = @($ent.embed.champs | ForEach-Object { $_.nom }) -join ' | '
Verifier ($ent -and $champs -match 'Branche' -and $champs -match 'Fichiers modifiés' -and $champs -match 'Prévisualisation Vercel' -and $champs -match 'Build et tests' -and $champs -match 'Votre décision') 'compte rendu Discord : branche, fichiers, prévisualisation, build et tests, décision'
$txtE = ($ent.embed.champs | ForEach-Object { $_.valeur }) -join "`n"
$npmDispo = [bool](Get-Command npm -ErrorAction SilentlyContinue)      # sans Node (portable serveur) le dépôt ne peut pas être construit : le compte rendu doit alors le dire honnêtement, pas prétendre « réussi »
$verifNpm = $(if ($npmDispo) { $txtE -match 'npm run build : réussi' -and $txtE -match 'npm run test : réussi' } else { $txtE -match 'npm introuvable : build et tests non lancés' })
Verifier ($txtE -match 'nouveau\.ts' -and $txtE -match 'github\.com/Liam2109/ecom-quiz/tree/jarvis' -and $txtE -match "Pas disponible pour l'instant" -and $verifNpm -and $txtE -match '\*\*valide\*\*') ('le compte rendu dit : fichiers, lien, prévisualisation absente (honnête), build et tests ' + $(if ($npmDispo) { 'réussis' } else { 'non lancés (npm introuvable, dit honnêtement)' }) + ', valide / refuse')
$j = Journal
Verifier ($j -match 'git push' -and $j -match 'Agent de dev : tâche 1 terminée' -and $j -notmatch [regex]::Escape($TOKEN) -and $j -notmatch 'AUTHORIZATION') 'tout est journalisé, et le jeton n''apparaît nulle part'
Verifier (-not (Test-Path (Join-Path $travail '.git\config') -PathType Leaf) -or ((Get-Content (Join-Path $travail '.git\config') -Raw) -notmatch [regex]::Escape($TOKEN))) 'le jeton n''est écrit dans aucun fichier du dépôt de travail'
$sale = (Gt $travail 'status' '--porcelain').Trim(); Verifier ($sale -eq '') ('dépôt de travail propre après la tâche' + $(if ($sale) { ' — reste : ' + ($sale -replace '\s+', ' ') + ' | diff : ' + ((Gt $travail 'diff' '--stat') -replace '\s+', ' ') + ' | ' + (($d = ((Gt $travail 'diff') -replace '\s+', ' ')).Substring(0, [Math]::Min(300, $d.Length))) } else { '' }))
$mails = Gt $travail 'log' '-1' '--format=%an <%ae>'; Verifier ($mails -match 'Jarvis \(agent de dev\)') 'commit signé « Jarvis (agent de dev) »'

# 2e tâche : une nouvelle branche, la 1re intacte
$t2 = Add-DevTache 'ajoute un champ prénom au formulaire'; $script:Notifs = @()
$res2 = Invoke-DevTache 2
Verifier ($res2.ok -and $res2.branche -ne $res.branche -and $res2.branche -match '-2$') "même titre, même jour : nouvelle branche ($($res2.branche)), l'ancienne n'est jamais touchée ni écrasée"

# garde-fous d'exécution
function Essai([string]$texte, [string]$cmd) { $t = Add-DevTache $texte; $env:JARVIS_TEST_DEV_CLAUDE = $cmd; $script:Notifs = @(); $r = Invoke-DevTache ([int]$t.id); @{ id = [int]$t.id; r = $r; tache = (Get-DevTache ([int]$t.id)); alertes = @($script:Notifs | Where-Object { $_.salon -eq 'systeme' }) } }
$besoin = Faux-Claude 'besoin' "echo JARVIS_BESOIN_CLE : cle secrete Stripe live`r`necho echo ceci > intrus.txt"
$x = Essai 'ajoute une page de test' $besoin
Verifier ($x.tache.statut -eq 'bloque' -and $x.alertes.Count -eq 1 -and $x.alertes[0].texte -match 'besoin d.une clé' -and (Gt $bare 'branch' '--list') -notmatch 'page-de-test') 'l''agent réclame une clé : tâche arrêtée, alerte Discord, rien poussé'
$secret = Faux-Claude 'secret' "echo const k = `"sk_live_abcdefghijklmnop12345`"; > cle.ts`r`necho fini"
$x = Essai 'ajoute une constante' $secret
Verifier ($x.tache.statut -eq 'bloque' -and $x.alertes[0].texte -match 'clé d.accès' -and (Gt $bare 'branch' '--list') -notmatch 'constante') 'un secret dans le diff : refusé, rien poussé'
$envf = Faux-Claude 'envf' "echo A=1 > .env.local`r`necho fini"
$x = Essai 'ajoute une variable' $envf
Verifier ($x.tache.statut -eq 'bloque' -and $x.alertes[0].texte -match '\.env' -and (Gt $bare 'branch' '--list') -notmatch 'variable') 'un fichier .env créé : refusé, rien poussé'
$bad = Faux-Claude 'bad' "echo erreur >&2`r`nexit /b 3"
$x = Essai 'ajoute un truc qui plante' $bad
Verifier ($x.tache.statut -eq 'echec' -and $x.alertes.Count -eq 1 -and $x.alertes[0].texte -match 'échoué') 'l''agent échoue : tâche en échec + alerte Discord'
$lent = Faux-Claude 'lent' "ping -n 30 127.0.0.1 > nul"
$script:DevDelaiTestSec = 3; $x = Essai 'ajoute un truc interminable' $lent; $script:DevDelaiTestSec = $null
Verifier ($x.tache.statut -eq 'echec' -and $x.alertes[0].texte -match 'délai' -and (Gt $bare 'branch' '--list') -notmatch 'interminable') 'délai dépassé : processus tué, travail mis de côté, alerte, rien poussé'
Verifier ((Gt $travail 'status' '--porcelain').Trim() -eq '' -and (Gt $travail 'stash' 'list') -match 'jarvis-tache-') 'le travail interrompu est dans un stash, jamais effacé'
$x = Essai 'utilise la clé Stripe live pour les tests' $ok
Verifier ($x.tache.statut -eq 'bloque') 'tâche réclamant une clé de production, même arrivée dans la file : bloquée avant tout'
'STRIPE=rk_live_FAUSSE0123456789abcdefgh' | Set-Content (Join-Path $travail '.env.local') -Encoding ASCII
$x = Essai 'ajoute une page contact' $ok
Verifier ($x.tache.statut -eq 'bloque' -and $x.alertes[0].texte -match 'clé de production' -and (Gt $bare 'branch' '--list') -notmatch 'page-contact') 'clé de production trouvée dans le dépôt de travail : arrêt avant toute exécution, alerte'
Remove-Item (Join-Path $travail '.env.local') -Force
$env:GITHUB_TOKEN_DEV = ''; $x = Essai 'ajoute une page faq' $ok
Verifier ($x.tache.statut -eq 'bloque' -and $x.alertes[0].texte -match 'GITHUB_TOKEN_DEV') 'sans GITHUB_TOKEN_DEV : arrêt et alerte (aucun push tenté)'
$env:GITHUB_TOKEN_DEV = $TOKEN
$Config.dev_dossier = $Root; $x = Essai 'ajoute une page aide' $ok
Verifier ($x.tache.statut -eq 'bloque' -and $x.alertes[0].texte -match 'séparé de Jarvis') 'dossier de travail = dossier de Jarvis : refusé'
$Config.dev_dossier = $travail
[void](Gt $travail 'remote' 'set-url' 'origin' (Join-Path $GT 'autre.git')); $x = Essai 'ajoute une page equipe' $ok
Verifier ($x.tache.statut -eq 'bloque' -and $x.alertes[0].texte -match 'autre origine') 'le dépôt local pointe vers une autre origine que dev_depot : arrêt'
[void](Gt $travail 'remote' 'set-url' 'origin' $bare)
Verifier ((Gt $bare 'rev-parse' 'main').Trim() -eq $mainAvant) 'au bout de toutes ces tâches, main n''a toujours pas bougé sur l''origine'
Fixer 'dev_push' 'non'; $refsAvant = Gt $bare 'branch' '--list'; $x = Essai 'ajoute une page presse' $ok
Verifier ($x.tache.statut -eq 'termine' -and -not $x.tache.pousse -and -not $x.tache.lien -and (Gt $bare 'branch' '--list') -eq $refsAvant -and (Gt $travail 'branch' '--list') -match 'page-presse') 'dev_push = "non" : branche créée et commitée en local, rien envoyé à l''origine'
$script:ApiAppels = @(); $r = Invoke-DevFusion $x.tache
Verifier (-not $r.ok -and $r.texte -match 'push est désactivé' -and $script:ApiAppels.Count -eq 0) 'dev_push = "non" : « valide » n''ouvre aucune pull request'
Fixer 'dev_push' 'oui'
$allJ = Journal; Verifier ($allJ -notmatch [regex]::Escape($TOKEN) -and $allJ -notmatch 'rk_live_FAUSSE' -and $allJ -notmatch 'sk_live_abcdefghijklmnop') 'journal final : ni jeton, ni clé, ni secret'

Write-Host ''
Remove-Item Env:JARVIS_TEST_DEV_REMOTE, Env:JARVIS_TEST_DEV_CLAUDE, Env:GITHUB_TOKEN_DEV, Env:STRIPE_RESTRICTED_KEY, Env:SUPABASE_READ_KEY -ErrorAction SilentlyContinue
Remove-Item $GT -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $TR -Recurse -Force -ErrorAction SilentlyContinue
if ($echecs) { Write-Host "ÉCHEC : $echecs vérification(s) en échec." -ForegroundColor Red; exit 1 }
Write-Host 'TOUT EST VERT.'
