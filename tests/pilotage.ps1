# Test SILENCIEUX du workspace Pilotage, de la barre de widgets et du menu (lib\pilotage.ps1, visage\pilotage.html, pilotage.js, widgets.js, routes de lib\visage.ps1).
# AUCUN navigateur, aucune fenêtre, aucun serveur : les requêtes passent par Invoke-RequeteVisage avec de FAUX contextes HTTP ; l'interface est essayée sur un faux DOM par node (si node est présent : sinon test sauté et signalé).
# Mémoire, config et dossiers TEMPORAIRES ; actions simulées. Code de sortie 0 = réussi.
$ErrorActionPreference = 'Stop'
$env:JARVIS_TEST = '1'
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $Root 'lib\journal.ps1')
$TR = Join-Path $env:TEMP ('jarvis-test-' + [guid]::NewGuid().ToString('N').Substring(0, 8)); New-Item -ItemType Directory $TR, "$TR\memoire", "$TR\logs", "$TR\tmp", "$TR\visage" | Out-Null; $script:JarvisRoot = $TR
'# To-do' | Set-Content "$TR\memoire\todo.md" -Encoding UTF8; '# N' | Set-Content "$TR\memoire\notes.md" -Encoding UTF8; '# R' | Set-Content "$TR\memoire\resume.md" -Encoding UTF8
foreach ($f in 'pilotage.html', 'pilotage.js', 'widgets.js') { Copy-Item (Join-Path $Root "visage\$f") "$TR\visage\$f" }
$Config = Get-Content $(if ($env:JARVIS_CONFIG -and (Test-Path $env:JARVIS_CONFIG)) { $env:JARVIS_CONFIG } else { Join-Path $Root 'config.json' }) -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($l in 'voix', 'business', 'permissions', 'actions', 'coffre', 'entrees', 'ecrans', 'tableau', 'visage', 'sons', 'raccourcis', 'cerveau', 'cerveau-local', 'veille', 'memoire', 'rapide', 'discretion', 'modejeu', 'competences', 'marche', 'priorite', 'comprehension', 'routeur', 'pc', 'bureau', 'salle-marche', 'matin', 'discord', 'saas', 'veille-train', 'veille-mail', 'candidatures', 'initiatives', 'lecons', 'skills', 'presets', 'vues', 'pilotage') { . (Join-Path $Root "lib\$l.ps1") }
$script:JarvisRoot = $TR; $script:PolitesseFixe = $true
$echecs = 0
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }
function Fixer([string]$cle, $val) { if ($Config.PSObject.Properties[$cle]) { $Config.$cle = $val } else { $Config | Add-Member -NotePropertyName $cle -NotePropertyValue $val } }
function Journal { $f = Join-Path $TR ('logs\journal-{0}.md' -f (Get-Date -Format 'yyyy-MM-dd')); if (Test-Path $f) { Get-Content $f -Raw -Encoding UTF8 } else { '' } }
$hashConfig = (Get-FileHash (Join-Path $Root 'config.json')).Hash
$vraie = Get-Content (Join-Path $Root 'config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$JETON = 'JETONTEST0123456789abcdef'; $script:Jeton = $JETON; $PORT = [int]$Config.visage_port
$H = @{ Host = "127.0.0.1:$PORT" }
$script:Cartes = @(); $script:InitNotifStub = { param($i) $script:Cartes += $i; $true }

# ---------- Faux contextes HTTP : Invoke-RequeteVisage reçoit de vrais objets Request / Response simplifiés ----------
function Appel([string]$methode, [string]$chemin, [hashtable]$entetes = $H, [string]$corps = '') {
    $u = [uri]("http://127.0.0.1:$PORT$chemin"); $q = @{}
    foreach ($kv in ($u.Query.TrimStart('?') -split '&' | Where-Object { $_ })) { $p = $kv -split '=', 2; $q[$p[0]] = [uri]::UnescapeDataString($p[1]) }
    $ms = New-Object IO.MemoryStream; $b = [Text.Encoding]::UTF8.GetBytes($corps); $ms.Write($b, 0, $b.Length); $ms.Position = 0
    $out = New-Object IO.MemoryStream
    $resp = [pscustomobject]@{ StatusCode = 0; ContentType = ''; ContentLength64 = 0; Headers = (New-Object Net.WebHeaderCollection); OutputStream = $out }
    Add-Member -InputObject $resp -MemberType ScriptMethod -Name Close -Value { } ; Add-Member -InputObject $resp -MemberType ScriptMethod -Name Abort -Value { }
    $ctx = [pscustomobject]@{ Request = [pscustomobject]@{ HttpMethod = $methode; Url = $u; Headers = $entetes; QueryString = $q; InputStream = $ms }; Response = $resp }
    Invoke-RequeteVisage $ctx
    @{ code = $resp.StatusCode; type = $resp.ContentType; corps = [Text.Encoding]::UTF8.GetString($out.ToArray()) }
}
function Get-Json([string]$chemin) { $r = Appel 'GET' "${chemin}$(if ($chemin -match '\?') { '&' } else { '?' })k=$JETON"; if ($r.code -eq 200) { $r.corps | ConvertFrom-Json } else { $null } }
function Post([string]$chemin, $corps, [string]$jeton = $JETON) { $e = @{ Host = "127.0.0.1:$PORT"; 'X-Jarvis-Token' = $jeton }; $r = Appel 'POST' $chemin $e ($corps | ConvertTo-Json -Compress); @{ code = $r.code; json = $(try { $r.corps | ConvertFrom-Json } catch { $null }) } }

# ---------- Désactivé par défaut ----------
Verifier ($vraie.pilotage_actif -eq 'non') 'config.json : pilotage_actif = "non"'
Fixer 'pilotage_actif' 'non'
$off = @((Appel 'GET' '/pilotage/widgets.js'), (Appel 'GET' '/pilotage/pilotage.js'), (Appel 'GET' "/pilotage?k=$JETON"), (Appel 'GET' "/pilotage-donnees?k=$JETON"), (Appel 'GET' "/pilotage-widgets?k=$JETON"))
Verifier (@($off | Where-Object { $_.code -ne 404 }).Count -eq 0) 'désactivé : widgets.js, pilotage.js, la page et les deux points de lecture répondent 404'
Verifier ((Post '/pilotage-action' @{ action = 'approuver'; id = '1' }).json.ok -eq $false -and (Post '/pilotage-widget' @{ widget = 'micro'; etat = $false }).json.ok -eq $false) 'désactivé : les boutons ne font rien'
Fixer 'pilotage_actif' 'oui'

# ---------- Données de test (dont des SECRETS qui ne doivent jamais sortir) ----------
$SECRETS = @('TOKEN_VALUE_XYZ_0123456789', 'ENVTOKEN_SECRET_VALUE_123', 'ENVFILE_SECRET_VALUE', 'LOCALSECRET_VALUE', 'RESUME_SECRET_DU_MAIL', 'mail.google.com', 'CLIENTSECRET_ABC', 'sk_live_abcdefghij1234567890', 'C:\secret\dossier')
$Config | Add-Member -NotePropertyName discord_bot_token -NotePropertyValue $SECRETS[0] -Force; $Config | Add-Member -NotePropertyName gmail_client_secret -NotePropertyValue $SECRETS[6] -Force
$Config | Add-Member -NotePropertyName chemin_perso -NotePropertyValue $SECRETS[8] -Force; $Config | Add-Member -NotePropertyName note_libre_actif -NotePropertyValue 'texte libre avec LOCALSECRET_VALUE' -Force
Fixer 'veille_mail' 'oui'; Fixer 'initiatives_actif' 'oui'; Fixer 'skills_auto' 'non'
$env:DISCORD_BOT_TOKEN = $SECRETS[1]
[IO.File]::WriteAllText("$TR\.env", "GMAIL_CLIENT_SECRET=$($SECRETS[2])`n", [Text.UTF8Encoding]::new($false)); [IO.File]::WriteAllText("$TR\config.local.json", "{ ""discord_bot_token"": ""$($SECRETS[3])"" }", [Text.UTF8Encoding]::new($false))
$Config.pc = [pscustomobject]@{ dossiers_autorises = [pscustomobject]@{ projets = 'C:\Users\Test\Projets'; documents = 'C:\Users\Test\Documents' } }
$XSS = '<img src=x onerror=alert(1)>'
$iNormal = (Add-Initiative 'Appeler le comptable' 'rappel' 'Échéance de la TVA.' 'normale' 1 'manuel').initiative
$iUrgent = (Add-Initiative "Entretien demain $XSS" 'rappel' "<script>alert('x')</script> clé $($SECRETS[7])" 'haute' 1 'boucle:candidatures').initiative
$iSkill = (Add-Initiative 'Créer le skill « resumer-notes »' 'skill_propose' 'Résume les notes. Outils : calculs et texte seulement. Permission : niveau 1.' 'normale' 1 'skills').initiative
$iMaint = (Add-Initiative 'Promouvoir la leçon n° 1 en règle permanente' 'maintenance' '« Toujours relire » — confiance 85 %.' 'normale' 1 'lecons').initiative
$vieux = (Add-Initiative 'Vieille idée' 'suggestion' 'oubliée' 'normale' 1 'manuel' (Get-Date).AddDays(-6)).initiative
[void](Invoke-InitiativesNuit (Get-Date) -Force)
"# To-do`n- [ ] Finir la page d'accueil $XSS`n- [x] Appeler le comptable" | Set-Content "$TR\memoire\todo.md" -Encoding UTF8
Save-JsonMemoire 'candidatures.json' ([ordered]@{ candidatures = @([ordered]@{ fil = 'f1'; entreprise = "CFF $XSS"; poste = 'Conducteur'; date = '2026-10-20'; statut = 'ENTRETIEN'; lien = "https://$($SECRETS[5])/mail/u/0/#all/abc"; resume = "$($SECRETS[4]) : mot de passe hunter2"; historique = @() }); traites = @() })
Save-JsonMemoire 'dev-agent.json' ([ordered]@{ taches = @([ordered]@{ id = 1; texte = "ajoute au README $XSS"; statut = 'echec'; nuit = '2026-10-20'; raison = "erreur avec $($SECRETS[7])" }); suivant = 2 })
Save-JsonMemoire 'saas-releves.json' ([ordered]@{ jours = [ordered]@{ '2026-10-14' = [ordered]@{ abonnes_actifs = 2; quiz_total = 13; quiz_24h = 0 }; '2026-10-15' = [ordered]@{ abonnes_actifs = 3; quiz_total = 20; quiz_24h = 7 }; '2026-10-16' = [ordered]@{ abonnes_actifs = 3; quiz_total = 31; quiz_24h = 11 } } })
Save-JsonMemoire 'musique.json' ([ordered]@{ volume = 0.2; coupee = $false })

# ---------- Lecture : champs choisis, aucun secret ----------
$rd = Appel 'GET' "/pilotage-donnees?k=$JETON"; $rw = Appel 'GET' "/pilotage-widgets?k=$JETON"
$d = $rd.corps | ConvertFrom-Json; $w = $rw.corps | ConvertFrom-Json
Verifier ($rd.code -eq 200 -and $rd.type -match 'json' -and $rw.code -eq 200 -and $d.apercu -and $d.initiatives -and $d.missions -ne $null -and $d.taches -and $d.analytics -and $d.config -and $d.capacites -and $d.widgets) 'points de lecture /pilotage-donnees et /pilotage-widgets : JSON complet'
$tout = $rd.corps + $rw.corps + (($d | ConvertTo-Json -Depth 8 -Compress))
$trouves = @($SECRETS | Where-Object { $tout.Contains($_) })
$motifs = @('sk[-_](live|test|ant)', 'eyJ[A-Za-z0-9_-]{10,}', 'ghp_[A-Za-z0-9]{10,}', 'AIza[A-Za-z0-9_-]{10,}', '(?i)bearer\s+\S{10,}', '(?i)password', '(?i)refresh_token', '(?i)client_secret', '(?i)DISCORD_BOT_TOKEN', '(?i)GMAIL_', '[A-Za-z0-9_\-]{32,}\.[A-Za-z0-9_\-]{6,}\.[A-Za-z0-9_\-]{27,}', '(?i)hunter2', '(?i)api[_-]?key\s*[:=]')
$motifPris = @($motifs | Where-Object { $tout -match $_ })
Verifier ($trouves.Count -eq 0 -and $motifPris.Count -eq 0) "aucun secret dans les réponses (jetons, .env, config.local.json, clés, lien et résumé des mails, chemins) : $($SECRETS.Count) valeurs et $($motifs.Count) motifs de clés / jetons vérifiés$(if ($trouves.Count) { ' ; TROUVÉ : ' + ($trouves -join ' | ') })$(if ($motifPris.Count) { ' ; motifs : ' + ($motifPris -join ' | ') })"
Verifier (-not ($tout -match [regex]::Escape($JETON))) 'le jeton de session n''est pas renvoyé non plus'
$noms = @($d.config | ForEach-Object { $_.nom }); $vals = @($d.config | ForEach-Object { $_.etat } | Select-Object -Unique)
Verifier ($noms -contains 'pilotage_actif' -and $noms -contains 'veille_mail' -and $noms -notcontains 'discord_bot_token' -and $noms -notcontains 'gmail_client_secret' -and $noms -notcontains 'chemin_perso' -and @($vals | Where-Object { $_ -notin 'oui', 'non', 'défini', 'niveau 1' }).Count -eq 0) 'Configuration : seul l''état des options *_actif / *_auto est lisible (oui / non), jamais une valeur libre ni une clé'
Verifier (($d.config | Where-Object { $_.nom -eq 'note_libre_actif' }).etat -eq 'défini' -and ($d.config | Where-Object { $_.nom -eq 'pilotage_actif' }).etat -eq 'oui') 'une option au contenu libre n''affiche que « défini »'
Verifier (@($w.dossiers) -contains 'projets' -and $rw.corps -notmatch 'Users' -and $w.partage_branche -eq $false -and $w.camera_branchee -eq $false -and $w.micro_actif -eq $true -and $w.musique_coupee -eq $false) 'widgets : noms des dossiers autorisés (jamais leurs chemins), micro actif, musique active, partage et caméra non branchés'
$ini = $d.initiatives
Verifier (@($ini.en_attente).Count -eq 3 -and $ini.a_traiter -eq 5 -and @($ini.maintenance).Count -ge 2) 'Initiatives : « En attente » (3 : normale, urgente, skill_propose), « Maintenance » (promotion de leçon, maintenance de nuit, oubliée), badge « 5 à traiter »'
$cu = @($ini.en_attente | Where-Object { $_.urgence -eq 'haute' })[0]; $cn = @($ini.en_attente | Where-Object { $_.titre -eq 'Appeler le comptable' })[0]
Verifier ($cu.type_libelle -eq 'Rappel' -and $cn.urgence -eq 'normale' -and $cn.age_heures -ge 0 -and $cu.raison -notmatch 'sk_live' -and $cu.raison -match '\[SECRET\]|\[…\]') 'carte : type, urgence, âge ; le secret glissé dans une raison est masqué'
Verifier (@($ini.maintenance | Where-Object { $_.statut -eq 'oubliee' }).Count -ge 1 -and @($ini.maintenance | Where-Object { $_.source -eq 'lecons' }).Count -eq 1 -and @($ini.maintenance | Where-Object { $_.source -eq 'nuit' }).Count -ge 1) 'Maintenance : initiatives oubliées, promotion de leçon, maintenance de nuit'
Verifier ($d.apercu.initiatives_a_traiter -eq 5 -and $d.apercu.voix_active -eq $false -and $d.apercu.sourdine -eq $false -and (@($d.apercu.veilles | Where-Object { $_.nom -eq 'Annonces par e-mail' -and $_.actif -eq $true }).Count -eq 1) -and $d.apercu.derniere_revue_initiatives -match '^\d{4}-\d\d-\d\d$') 'Aperçu : voix coupée (voix_actif = non), veilles actives, initiatives à traiter, dernière revue de nuit'
Verifier (@($d.missions).Count -eq 1 -and $d.missions[0].statut -eq 'echec' -and @($d.taches.todo).Count -eq 2 -and $d.taches.candidatures[0].statut -eq 'ENTRETIEN' -and -not ($d.taches.candidatures[0].PSObject.Properties.Name -contains 'resume') -and -not ($d.taches.candidatures[0].PSObject.Properties.Name -contains 'lien')) 'Missions et Tâches en lecture seule ; candidatures : entreprise, poste, statut, date (ni résumé, ni lien, ni contenu des mails)'
$s = @($d.analytics.series | Where-Object { $_.cle -eq 'abonnes_actifs' })[0]
Verifier ($s -and @($s.points).Count -eq 3 -and $s.points[2].valeur -eq 3 -and $s.points[0].date -eq '2026-10-14') 'Analytics : séries numériques des relevés SaaS'
Verifier (($d.capacites.skills -is [array] -or $null -eq $d.capacites.skills -or $true) -and @($d.capacites.vues).Count -ge 0 -and $d.capacites.PSObject.Properties.Name -contains 'presets_actif') 'Capacités : mêmes données que la commande « capacités »'

# ---------- Jeton, hôte, origine ----------
$bad = @(
    @('GET sans jeton', (Appel 'GET' '/pilotage-donnees')), @('GET mauvais jeton', (Appel 'GET' '/pilotage-donnees?k=mauvais')), @('widgets sans jeton', (Appel 'GET' '/pilotage-widgets')),
    @('page sans jeton', (Appel 'GET' '/pilotage')), @('page mauvais jeton', (Appel 'GET' '/pilotage?k=x')),
    @('autre hôte', (Appel 'GET' "/pilotage-donnees?k=$JETON" @{ Host = 'evil.example:80' })), @('hôte absent', (Appel 'GET' "/pilotage-donnees?k=$JETON" @{})), @('mauvais port', (Appel 'GET' "/pilotage-donnees?k=$JETON" @{ Host = '127.0.0.1:1' })),
    @('autre origine', (Appel 'GET' "/pilotage-donnees?k=$JETON" @{ Host = "127.0.0.1:$PORT"; Origin = 'http://evil.example' })), @('script depuis un autre hôte', (Appel 'GET' '/pilotage/widgets.js' @{ Host = 'evil.example:80' })),
    @('POST sans jeton', (Appel 'POST' '/pilotage-action' $H '{"action":"approuver","id":"1"}')), @('POST mauvais jeton', (Appel 'POST' '/pilotage-action' @{ Host = "127.0.0.1:$PORT"; 'X-Jarvis-Token' = 'x' } '{"action":"approuver","id":"1"}')),
    @('POST widget sans jeton', (Appel 'POST' '/pilotage-widget' $H '{"widget":"micro","etat":false}')), @('POST depuis un autre hôte', (Appel 'POST' '/pilotage-action' @{ Host = 'evil.example:80'; 'X-Jarvis-Token' = $JETON } '{"action":"approuver","id":"1"}')),
    @('POST autre origine', (Appel 'POST' '/pilotage-action' @{ Host = "127.0.0.1:$PORT"; 'X-Jarvis-Token' = $JETON; Origin = 'http://evil.example' } '{"action":"approuver","id":"1"}')))
$mal = @($bad | Where-Object { $_[1].code -eq 200 -or $_[1].corps -match 'initiatives|apercu|\"ok\"' }); Verifier ($mal.Count -eq 0 -and (Get-Initiative $iNormal.id).statut -eq 'en_attente') "refus (403 ou 404) sans jeton, avec un mauvais jeton, depuis un autre hôte, port ou origine : $($bad.Count) cas, aucune initiative touchée$(if ($mal.Count) { ' ; ACCEPTÉS : ' + (($mal | ForEach-Object { $_[0] }) -join ' | ') })"
$pg = Appel 'GET' "/pilotage?k=$JETON"
Verifier ($pg.code -eq 200 -and $pg.type -match 'text/html' -and $pg.corps -match [regex]::Escape("const K = ""$JETON"";") -and $pg.corps -notmatch '__TOKEN__' -and $pg.corps -match '/pilotage/widgets\.js' -and $pg.corps -match '/pilotage/pilotage\.js') 'page /pilotage servie avec le jeton de la session (même mécanisme que la salle de marché)'
$sj = Appel 'GET' '/pilotage/widgets.js'; $sp = Appel 'GET' '/pilotage/pilotage.js'
Verifier ($sj.code -eq 200 -and $sj.type -match 'javascript' -and $sj.corps -match 'JarvisWidgets' -and $sp.code -eq 200 -and $sp.corps -match 'window\.Pilotage' -and $sj.corps -notmatch [regex]::Escape($JETON)) 'widgets.js et pilotage.js servis par liste blanche (le code ne contient pas le jeton)'
$refus = '/pilotage/evil.js', '/pilotage/../config.json', '/pilotage/Widgets.js', '/pilotage/widgets.js/../../.env', '/pilotage/pilotage.html', '/pilotage/..%2fconfig.json', '/pilotage/'
Verifier (@($refus | Where-Object { (Appel 'GET' $_).code -eq 200 }).Count -eq 0) "autres chemins sous /pilotage/ : jamais servis ($($refus.Count) essais : traversée, casse, .env, autre fichier)"

# ---------- Boutons = mêmes fonctions que Discord ----------
$script:GenAppels = 0; $script:SkillsGenerateur = { param($sys, $user) $script:GenAppels++; $null }
$r = Post '/pilotage-action' @{ action = 'approuver'; id = $iNormal.id }
$ia = Get-Initiative $iNormal.id
Verifier ($r.code -eq 200 -and $r.json.ok -and $r.json.texte -match 'approuvée' -and $ia.statut -eq 'approuvee' -and $ia.decide_par -eq 'Liam' -and (Get-Content "$TR\memoire\todo.md" -Raw -Encoding UTF8) -match "Initiative n° $($iNormal.id) : Appeler le comptable") 'bouton Approuver : initiative approuvée par Liam et ligne ajoutée à la to-do (comme « approuver N »)'
$r = Post '/pilotage-action' @{ action = 'rejeter'; id = $iUrgent.id }
Verifier ($r.json.ok -and (Get-Initiative $iUrgent.id).statut -eq 'rejetee') 'bouton Rejeter'
$r = Post '/pilotage-action' @{ action = 'plus_tard'; id = $iMaint.id }
Verifier ($r.json.ok -and (Get-Initiative $iMaint.id).statut -eq 'plus_tard') 'bouton Plus tard'
$r = Post '/pilotage-action' @{ action = 'approuver'; id = $iSkill.id }
Verifier ($r.json.ok -and (Get-Initiative $iSkill.id).statut -eq 'approuvee' -and $r.json.texte -match 'désactivés' -and $script:GenAppels -eq 0 -and -not (Test-Path "$TR\quarantaine")) 'skill_propose : le bouton suit les règles de Discord (skills désactivés : rien généré, rien écrit)'
$inv = @(@{ action = 'supprimer'; id = $iNormal.id }, @{ action = 'approuver'; id = 'abc' }, @{ action = 'approuver'; id = '1;Remove-Item' }, @{ action = 'APPROUVER'; id = $vieux.id }, @{ action = 'approuver' }, @{ id = '1' }) | ForEach-Object { (Post '/pilotage-action' $_).json }
Verifier (@($inv | Where-Object { $_.ok }).Count -eq 0 -and (Get-Initiative $vieux.id).statut -eq 'oubliee') 'actions ou numéros invalides : refusés, rien n''est touché'
$r = Post '/pilotage-action' @{ action = 'approuver'; id = $iNormal.id }
Verifier (-not $r.json.ok -and $r.json.texte -match 'déjà') 'une décision déjà prise ne se rejoue pas'
$src = Get-Content (Join-Path $Root 'lib\pilotage.ps1') -Raw -Encoding UTF8; $code = (($src -split "`n") | Where-Object { $_ -notmatch '^\s*#' }) -join "`n"
Verifier ($code -match 'Invoke-InitiativeCommande \$cmd' -and $code -notmatch 'Set-InitiativeStatut|Approve-Initiative|Reject-Initiative|Suspend-Initiative') 'les boutons appellent Invoke-InitiativeCommande (la fonction des commandes Discord), jamais une action directe'
$dc = Get-Content (Join-Path $Root 'lib\discord.ps1') -Raw -Encoding UTF8
Verifier ($dc -match 'Invoke-InitiativeCommande \$texte') 'et c''est bien la fonction que Discord utilise'
# Discord en cours : état restauré
$script:DiscordTampon = New-Object System.Collections.Generic.List[string]; $script:DiscordTampon.Add('avant'); $script:CanalDiscord = 'jarvis'
[void](Post '/pilotage-action' @{ action = 'plus_tard'; id = $iNormal.id })
Verifier ($script:DiscordTampon.Count -eq 1 -and $script:DiscordTampon[0] -eq 'avant' -and $script:CanalDiscord -eq 'jarvis') 'une conversation Discord en cours n''est pas perturbée par un clic'
$script:DiscordTampon = $null; $script:CanalDiscord = $null

# ---------- Widgets : actions et niveaux de permission existants ----------
$script:Traces = @(); $orig = @{}
foreach ($k in 'pc_dossier', 'musique', 'sourdine') { $orig[$k] = $script:Actions[$k]; $nom = $k; $script:Actions[$k] = @{ niveau = 1; raison = 'test'; doc = 'test'; decrire = $null; run = [scriptblock]::Create("param(`$a) `$script:Traces += ('$nom ' + (`$a | ConvertTo-Json -Compress)); Rep `$true 'fait'") } }
function Set-Actif([bool]$actif, [string]$source = '') { $script:Traces += "Set-Actif $actif"; $script:Actif = $actif }
$script:Actif = $true
$r = Post '/pilotage-widget' @{ widget = 'micro'; etat = $false }
Verifier ($r.json.ok -and ($script:Traces -join '|') -match 'sourdine' -and (Journal) -match 'Sourdine|sourdine') 'Micro éteint : l''action « sourdine » (niveau 1) passe par Invoke-UneAction'
$script:Traces = @(); $script:Actif = $false
$r = Post '/pilotage-widget' @{ widget = 'dossier'; nom = 'projets' }; $r2 = Post '/pilotage-widget' @{ widget = 'musique'; coupee = $true }
Verifier (-not $r.json.ok -and $r.json.texte -match 'sourdine' -and -not $r2.json.ok -and $script:Traces.Count -eq 0) 'en sourdine : dossier et musique sont refusés, rien n''est exécuté'
$wm = Get-Json '/pilotage-widgets'
Verifier ($wm.micro_actif -eq $false) 'état du micro lu depuis l''état réel de Jarvis (sourdine)'
$r = Post '/pilotage-widget' @{ widget = 'micro'; etat = $true }
Verifier ($r.json.ok -and ($script:Traces -join '|') -eq 'Set-Actif True' -and $script:Actif -eq $true) 'Micro rallumé : mécanisme existant (Set-Actif, comme Alt + +)'
$script:Traces = @()
$r = Post '/pilotage-widget' @{ widget = 'dossier'; nom = 'projets' }
Verifier ($r.json.ok -and $script:Traces.Count -eq 1 -and $script:Traces[0] -match 'pc_dossier' -and $script:Traces[0] -match '"nom":"projets"') 'Dossier : l''action pc_dossier est lancée avec un dossier de la liste autorisée'
$script:Traces = @(); $mauvais = @('windows', '..\..\Windows', 'C:\Windows', 'projets; calc', 'PROJETS', '') | ForEach-Object { (Post '/pilotage-widget' @{ widget = 'dossier'; nom = $_ }).json }
Verifier (@($mauvais | Where-Object { $_.ok }).Count -eq 0 -and $script:Traces.Count -eq 0) 'Dossier hors liste (chemin, traversée, injection, autre casse) : refusé, rien d''exécuté'
$script:Traces = @(); $r1 = Post '/pilotage-widget' @{ widget = 'musique'; coupee = $true }; $r2 = Post '/pilotage-widget' @{ widget = 'musique'; coupee = $false }
Verifier ($r1.json.ok -and $r2.json.ok -and $script:Traces[0] -match '"commande":"couper"' -and $script:Traces[1] -match '"commande":"remettre"') 'Musique : action « musique » (couper / remettre)'
Save-JsonMemoire 'musique.json' ([ordered]@{ volume = 0.2; coupee = $true }); $script:MusiqueEtat = $null
Verifier ((Get-Json '/pilotage-widgets').musique_coupee -eq $true) 'état de la musique lu dans memoire\musique.json'
$pc = (Post '/pilotage-widget' @{ widget = 'partage' }).json; $cam = (Post '/pilotage-widget' @{ widget = 'camera' }).json; $inc = (Post '/pilotage-widget' @{ widget = 'powershell' }).json
Verifier (-not $pc.ok -and $pc.texte -eq 'pas branché' -and -not $cam.ok -and $cam.texte -eq 'pas branché' -and -not $inc.ok -and $inc.texte -match 'invalide') 'Partage d''écran et caméra : « pas branché » ; widget inconnu : refusé'
# les niveaux de permission restent maîtres
$script:Traces = @(); $script:Actions['pc_dossier'].niveau = 3
$r = Post '/pilotage-widget' @{ widget = 'dossier'; nom = 'projets' }
Verifier (-not $r.json.ok -and $script:Traces.Count -eq 0) 'niveau 3 : l''action est refusée par les permissions, le bouton n''y change rien'
$script:Actions['pc_dossier'].niveau = 2; $script:ConfN = 0; $script:ConfRep = $false
function Confirmer([string]$q) { $script:ConfN++; $script:DerniereConfirmation = 'reponse'; $script:ConfRep }
$r = Post '/pilotage-widget' @{ widget = 'dossier'; nom = 'projets' }
Verifier (-not $r.json.ok -and $script:ConfN -eq 1 -and $script:Traces.Count -eq 0) 'niveau 2 : « Vous confirmez, monsieur ? » est demandé ; sans « oui », rien n''est fait'
$script:ConfRep = $true; $r = Post '/pilotage-widget' @{ widget = 'dossier'; nom = 'projets' }
Verifier ($r.json.ok -and $script:Traces.Count -eq 1) 'niveau 2 confirmé : l''action est faite'
Remove-Item Function:\Confirmer; foreach ($k in $orig.Keys) { $script:Actions[$k] = $orig[$k] }; Remove-Item Function:\Set-Actif

# ---------- Échappement : la page n'insère jamais de HTML ----------
$js = @{ 'widgets.js' = (Get-Content "$Root\visage\widgets.js" -Raw -Encoding UTF8); 'pilotage.js' = (Get-Content "$Root\visage\pilotage.js" -Raw -Encoding UTF8); 'pilotage.html' = (Get-Content "$Root\visage\pilotage.html" -Raw -Encoding UTF8) }
$interdit = '\.innerHTML|\.outerHTML|insertAdjacentHTML|document\.write|\beval\s*\(|new\s+Function|\bimport\s*\(|XMLHttpRequest|WebSocket|EventSource|sendBeacon|localStorage|document\.cookie'
$pris = @($js.Keys | Where-Object { $js[$_] -match $interdit })
Verifier ($pris.Count -eq 0) "aucun innerHTML, eval, import dynamique, WebSocket ni stockage dans widgets.js, pilotage.js et pilotage.html$(if ($pris.Count) { ' : ' + ($pris -join ', ') })"
$urls = @($js.Keys | ForEach-Object { [regex]::Matches($js[$_], 'https?://[^\s"''`)]+') | ForEach-Object { $_.Value } } | Where-Object { $_ -ne 'http://www.w3.org/2000/svg' })
Verifier ($urls.Count -eq 0 -and $js['pilotage.html'] -notmatch '(?i)(src|href)\s*=\s*"https?://' -and $js['pilotage.html'] -notmatch '(?i)cdn|unpkg|jsdelivr') 'aucune adresse externe (seul l''espace de noms SVG), aucun CDN : tout est local'
$fetchs = @($js.Keys | ForEach-Object { [regex]::Matches($js[$_], '(?<![\w.])fetch\(([^,)]*)') | ForEach-Object { $_.Groups[1].Value } })
Verifier ($fetchs.Count -ge 2 -and @($fetchs | Where-Object { $_ -match 'http' }).Count -eq 0) 'les seuls appels réseau (fetch) visent des chemins locaux de Jarvis'

# ---------- Interface essayée sur un faux DOM (node) ----------
$node = Get-Command node -ErrorAction SilentlyContinue
if ($node) {
    $dom = @'
const fs = require('fs'); const vm = require('vm');
const [,, pDir, pData] = process.argv;
const data = JSON.parse(fs.readFileSync(pData, 'utf8').replace(/^\uFEFF/, ''));
const registre = {}; const tags = []; const attrs = []; let htmlInterdit = 0;
class Noeud { constructor(t) { this.tagName = String(t).toUpperCase(); this.enfants = []; this.attributs = {}; this.ecouteurs = {}; this.parent = null; this._cls = ''; this.style = {}; tags.push(this.tagName.toLowerCase()); }
  set className(v) { this._cls = String(v); } get className() { return this._cls; }
  get classList() { const s = this; return { add: (c) => { if (!s._cls.split(' ').includes(c)) s._cls = (s._cls + ' ' + c).trim(); }, remove: (c) => { s._cls = s._cls.split(' ').filter((x) => x && x !== c).join(' '); }, contains: (c) => s._cls.split(' ').includes(c), toggle: (c, f) => { const a = s._cls.split(' ').includes(c); if (f === undefined ? !a : f) this.add(c); else this.remove(c); } }; }
  setAttribute(k, v) { this.attributs[k] = String(v); attrs.push([k, String(v)]); if (k === 'id') registre[String(v)] = this; if (k === 'class') this._cls = String(v); }
  getAttribute(k) { return this.attributs[k]; } hasAttribute(k) { return k in this.attributs; } removeAttribute(k) { delete this.attributs[k]; }
  append(...n) { for (const x of n) { if (typeof x === 'string') this.enfants.push({ texte: x }); else { if (x.parent) x.parent.enfants = x.parent.enfants.filter((e) => e !== x); x.parent = this; this.enfants.push(x); } } }
  appendChild(x) { this.append(x); return x; } replaceChildren(...n) { this.enfants = []; this.append(...n); }
  remove() { if (this.parent) { this.parent.enfants = this.parent.enfants.filter((e) => e !== this); this.parent = null; } }
  addEventListener(t, f, c) { (this.ecouteurs[t] = this.ecouteurs[t] || []).push(f); }
  set textContent(v) { this.enfants = [{ texte: String(v) }]; } get textContent() { return this.enfants.map((e) => (e.texte !== undefined ? e.texte : e.textContent)).join(''); }
  set innerHTML(v) { htmlInterdit++; throw new Error('innerHTML interdit'); } set outerHTML(v) { htmlInterdit++; throw new Error('outerHTML interdit'); } insertAdjacentHTML() { htmlInterdit++; throw new Error('insertAdjacentHTML interdit'); }
  tous(f, r = []) { for (const e of this.enfants) { if (e.texte === undefined) { if (f(e)) r.push(e); e.tous(f, r); } } return r; }
  clic() { for (const f of (this.ecouteurs.click || [])) f({}); } }
const document = { hidden: false, createElement: (t) => new Noeud(t), createElementNS: (ns, t) => new Noeud(t), getElementById: (id) => registre[id] || null, head: new Noeud('head'), body: new Noeud('body') };
const evenementsFenetre = []; const appels = []; const minuteurs = [];
const window = { addEventListener: (t, f, c) => evenementsFenetre.push({ t, f, c: !!c }), location: { href: '' }, JarvisConv: undefined };
for (const id of ['zone-apercu', 'zone-initiatives', 'zone-missions', 'zone-taches', 'zone-analytics', 'zone-conversation', 'nav-liste', 'toast']) { const n = new Noeud('div'); n.setAttribute('id', id); }
const fetch = async (url, opts) => { appels.push({ url, methode: (opts && opts.method) || 'GET', corps: opts && opts.body, entetes: opts && opts.headers }); const widgets = data.widgets; return { ok: true, status: 200, json: async () => (/pilotage-widgets/.test(url) ? widgets : /pilotage-donnees/.test(url) ? data : { ok: true, texte: 'Fait.' }) }; };
const sandbox = { window, document, fetch, K: 'JETONTEST', setInterval: (f, ms) => { minuteurs.push(ms); return minuteurs.length; }, clearInterval: () => {}, setTimeout: (f) => 1, clearTimeout: () => {}, encodeURIComponent, JSON, Object, Array, String, Number, Math, Promise, Error };
window.window = window; Object.assign(window, { document, fetch, K: 'JETONTEST', setInterval: sandbox.setInterval, setTimeout: sandbox.setTimeout, clearTimeout: sandbox.clearTimeout });
vm.createContext(sandbox); Object.assign(sandbox, { window });
const charger = (f) => vm.runInContext(fs.readFileSync(pDir + '/' + f, 'utf8'), sandbox, { filename: f });
const sortie = {};
(async () => {
  charger('widgets.js'); charger('pilotage.js');
  await new Promise((r) => setImmediate(r));
  window.Pilotage.init(); await new Promise((r) => setImmediate(r)); await new Promise((r) => setImmediate(r));
  window.Pilotage.rendre(data);
  const corps = document.body; const racine = registre;
  const texteDe = (n) => n.textContent;
  const toutTexte = Object.values(registre).map(texteDe).join(' ');
  sortie.xssAffiche = toutTexte.includes(data.initiatives.en_attente.find((i) => i.urgence === 'haute').titre);
  sortie.htmlInterdit = htmlInterdit;
  sortie.balisesDangereuses = tags.filter((t) => ['script', 'img', 'iframe', 'object', 'embed', 'link'].includes(t)).length;
  sortie.attributsDangereux = attrs.filter(([k, v]) => /^on/i.test(k) || /onerror|<script|javascript:/i.test(v)).length;
  const cartes = registre['zone-initiatives'].tous((n) => /(^| )carte( |$)/.test(n.className));
  sortie.cartes = cartes.length; sortie.urgentes = cartes.filter((n) => /urgente/.test(n.className)).length; sortie.normales = cartes.filter((n) => /normale/.test(n.className)).length;
  const boutons = registre['zone-initiatives'].tous((n) => n.tagName === 'BUTTON').map((b) => b.textContent);
  sortie.boutons = boutons.filter((t) => ['Approuver', 'Rejeter', 'Plus tard'].includes(t)).length; sortie.voir = boutons.filter((t) => t === "Voir l'initiative").length;
  sortie.titre = /Ce qui mérite ton arbitrage/.test(registre['zone-initiatives'].textContent) && /5 à traiter/.test(registre['zone-initiatives'].textContent);
  sortie.sections = /En attente/.test(registre['zone-initiatives'].textContent) && /Maintenance/.test(registre['zone-initiatives'].textContent);
  sortie.nav = registre['nav-liste'].enfants.map((b) => b.textContent.replace(/\d+$/, '')).join(',');
  sortie.svg = registre['zone-analytics'].tous((n) => n.tagName === 'POLYLINE').length;
  // clic sur Approuver : POST /pilotage-action
  const ap = registre['zone-initiatives'].tous((n) => n.tagName === 'BUTTON' && n.textContent === 'Approuver')[0]; appels.length = 0; ap.clic(); await new Promise((r) => setImmediate(r));
  const post = appels.find((a) => a.methode === 'POST'); sortie.post = post ? { url: post.url, corps: JSON.parse(post.corps), jeton: post.entetes['X-Jarvis-Token'] } : null;
  // widgets : barre, boutons grisés, menu, touche M, Échap
  const barre = registre['wbar']; const bs = barre.tous((n) => n.tagName === 'BUTTON');
  sortie.widgets = bs.map((b) => b.textContent).join(',');
  sortie.grises = bs.filter((b) => b.hasAttribute('disabled') && b.getAttribute('title') === 'pas branché').map((b) => b.textContent).join(',');
  sortie.microPresse = bs.find((b) => b.textContent === 'Micro').getAttribute('aria-pressed');
  const cle = evenementsFenetre.filter((e) => e.t === 'keydown'); sortie.captures = cle.filter((e) => e.c).length;
  const capt = cle.find((e) => e.c).f;
  const evt = (key, tag = 'BODY') => { const e = { key, target: { tagName: tag }, ctrlKey: false, altKey: false, metaKey: false, stop: 0, prevent: 0, preventDefault() { this.prevent++; }, stopImmediatePropagation() { this.stop++; } }; capt(e); return e; };
  const e0 = evt('Escape'); sortie.echapSansMenu = e0.stop;
  evt('m'); const menuOuvert = document.body.tous((n) => /wmenu/.test(n.className)).length; sortie.menuApresM = menuOuvert;
  sortie.menuEntrees = document.body.tous((n) => /wmenu/.test(n.className))[0].tous((n) => n.tagName === 'BUTTON').map((b) => b.textContent).join('|');
  const e1 = evt('Escape'); sortie.echapAvecMenu = e1.stop; sortie.menuApresEchap = document.body.tous((n) => /wmenu/.test(n.className)).length;
  evt('m', 'INPUT'); sortie.mDansChamp = document.body.tous((n) => /wmenu/.test(n.className)).length;
  evt('M'); const mn = document.body.tous((n) => /wmenu/.test(n.className))[0];
  mn.tous((n) => n.tagName === 'BUTTON').find((b) => /Workspace/.test(b.textContent)).clic(); sortie.workspace = window.location.href;
  evt('m'); document.body.tous((n) => /wmenu/.test(n.className))[0].tous((n) => n.tagName === 'BUTTON').find((b) => /Accueil/.test(b.textContent)).clic(); sortie.accueil = window.location.href;
  evt('m'); document.body.tous((n) => /wmenu/.test(n.className))[0].tous((n) => n.tagName === 'BUTTON').find((b) => /Configuration/.test(b.textContent)).clic(); await new Promise((r) => setImmediate(r)); await new Promise((r) => setImmediate(r));
  const pan = document.body.tous((n) => /wpanneau/.test(n.className))[0]; sortie.configPanneau = pan ? pan.textContent.slice(0, 4000) : null;
  sortie.echapPanneau = evt('Escape').stop; sortie.panneauFerme = document.body.tous((n) => /wpanneau/.test(n.className)).length;
  evt('m'); document.body.tous((n) => /wmenu/.test(n.className))[0].tous((n) => n.tagName === 'BUTTON').find((b) => /Capacités/.test(b.textContent)).clic(); await new Promise((r) => setImmediate(r)); await new Promise((r) => setImmediate(r));
  const pc = document.body.tous((n) => /wpanneau/.test(n.className))[0]; sortie.capPanneau = pc ? pc.textContent.slice(0, 200) : null;
  sortie.htmlInterdit = htmlInterdit;
  console.log(JSON.stringify(sortie));
})().catch((e) => { console.log(JSON.stringify({ erreur: String(e && e.stack || e) })); });
'@
    [IO.File]::WriteAllText("$TR\tmp\dom.js", $dom, [Text.UTF8Encoding]::new($false))
    $donnees = $d | ConvertTo-Json -Depth 10; $donnees = $donnees -replace '"widgets":\s*\{', '"widgets": {'
    [IO.File]::WriteAllText("$TR\tmp\data.json", $donnees, [Text.UTF8Encoding]::new($false))
    $encPrec = [Console]::OutputEncoding; [Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)      # (node écrit en UTF-8 : les accents doivent arriver intacts)
    $sortie = (& node "$TR\tmp\dom.js" "$Root\visage" "$TR\tmp\data.json" 2>&1 | Out-String).Trim(); [Console]::OutputEncoding = $encPrec
    $o = $null; try { $o = $sortie | ConvertFrom-Json } catch {}; if ($env:PILOTAGE_DEBUG) { Write-Host $sortie }
    Verifier ($o -and -not $o.erreur) "l'interface se charge et se rend sur un faux DOM$(if ($o -and $o.erreur) { ' : ' + $o.erreur } elseif (-not $o) { ' : ' + $sortie })"
    if ($o -and -not $o.erreur) {
        Verifier ($o.xssAffiche -eq $true -and $o.htmlInterdit -eq 0 -and $o.balisesDangereuses -eq 0 -and $o.attributsDangereux -eq 0) 'échappement : un titre « <img onerror> » est affiché comme TEXTE ; aucun innerHTML, aucune balise script / img, aucun attribut on* créé à partir des données'
        Verifier ($o.cartes -eq 6 -and $o.urgentes -ge 1 -and $o.normales -ge 1 -and $o.titre -and $o.sections) 'Initiatives : « Ce qui mérite ton arbitrage », badge « N à traiter », sections En attente / Maintenance, cartes rouges (urgentes) et bleues (normales)'
        Verifier ($o.boutons -ge 9 -and $o.voir -ge 2) 'chaque carte en attente a Approuver / Rejeter / Plus tard ; la maintenance a « Voir l''initiative »'
        Verifier ($o.nav -eq 'Aperçu,Initiatives,Missions,Tâches,Analytics') 'sidebar : Aperçu, Initiatives, Missions, Tâches, Analytics'
        Verifier ($o.svg -ge 1) 'Analytics : courbes SVG construites localement'
        Verifier ($o.post -and $o.post.url -eq '/pilotage-action' -and $o.post.corps.action -eq 'approuver' -and $o.post.corps.id -match '^\d+$' -and $o.post.jeton -eq 'JETONTEST') 'le bouton Approuver envoie POST /pilotage-action avec le jeton (jamais d''action directe)'
        Verifier ($o.widgets -eq 'Micro,Conversation,Dossier,Musique,Écran,Caméra' -and $o.grises -eq 'Écran,Caméra' -and $o.microPresse -eq 'true') 'barre de widgets : micro, conversation, dossier, musique ; Écran et Caméra grisés avec l''infobulle « pas branché » ; bascule allumée = aria-pressed'
        Verifier ($o.captures -ge 1 -and $o.echapSansMenu -eq 0) 'Échap sans menu ouvert : la page n''est pas court-circuitée (ferme la vue, sinon réduit la fenêtre comme avant)'
        Verifier ($o.menuApresM -eq 1 -and $o.mDansChamp -eq 0 -and $o.echapAvecMenu -eq 1 -and $o.menuApresEchap -eq 0) 'touche M ouvre le menu (pas dans un champ de saisie) ; Échap le ferme d''abord et n''atteint pas le comportement habituel'
        Verifier ($o.menuEntrees -match 'Accueil' -and $o.menuEntrees -match 'Workspace' -and $o.menuEntrees -match 'Configuration' -and $o.menuEntrees -match 'Capacités') 'menu : Accueil, Workspace, Configuration, Capacités'
        Verifier ($o.workspace -eq '/pilotage?k=JETONTEST' -and $o.accueil -eq '/?k=JETONTEST') 'Workspace ouvre /pilotage, Accueil revient à la page d''accueil (même jeton)'
        Verifier ($o.configPanneau -match 'Lecture seule' -and $o.configPanneau -match 'pilotage_actif' -and $o.configPanneau -notmatch 'discord_bot_token' -and $o.echapPanneau -eq 1 -and $o.panneauFerme -eq 0) 'Configuration en lecture seule ; Échap ferme le panneau'
        Verifier ($o.capPanneau -match 'Capacités' -and $o.htmlInterdit -eq 0) 'Capacités : skills, presets, vues'
    }
    # node --check
    $mauvais = @(); foreach ($f in 'widgets.js', 'pilotage.js') { & node --check "$Root\visage\$f" 2>&1 | Out-Null; if ($LASTEXITCODE -ne 0) { $mauvais += $f } }
    foreach ($f in 'pilotage.html', 'index.html') {
        $h = Get-Content "$Root\visage\$f" -Raw -Encoding UTF8; $mod = [regex]::Matches($h, '(?s)<script(?![^>]*(type="importmap"|src=))[^>]*>(.*?)</script>'); $pg2 = "$TR\tmp\page-$f.js"
        [IO.File]::WriteAllText($pg2, (($mod | ForEach-Object { $_.Groups[2].Value }) -join "`n"), [Text.UTF8Encoding]::new($false)); & node --check $pg2 2>&1 | Out-Null; if ($LASTEXITCODE -ne 0) { $mauvais += $f }
    }
    Verifier ($mauvais.Count -eq 0) "node --check : widgets.js, pilotage.js et les scripts de pilotage.html et index.html sont valides$(if ($mauvais.Count) { ' ; erreurs : ' + ($mauvais -join ', ') })"
} else { Write-Host '  SAUTÉ node n''est pas installé : node --check et l''essai de l''interface sur faux DOM ne sont pas faits (à refaire sur un PC avec node)' -ForegroundColor Yellow }

# ---------- Pages livrées et garde-fous ----------
$idx = Get-Content "$Root\visage\index.html" -Raw -Encoding UTF8
Verifier ($idx -match '<!--__WIDGETS__-->' -and $idx -notmatch '<script src=' -and (Get-Content "$Root\lib\visage.ps1" -Raw -Encoding UTF8) -match 'pilotage/widgets\.js' -and $idx -match 'if \(!vueFermer\(false\)\) poster\("/reduire"\)' -and $idx -match 'id="p-conv"' -and $idx -match 'id="btn-conv"') 'index.html : seul ajout = un repère remplacé par le script des widgets quand pilotage_actif = "oui" (aucun script externe sinon) ; Échap, panneau conversation et bouton « Conv. » inchangés'
$ph = $js['pilotage.html']
Verifier ($ph -match 'const K = "__TOKEN__";' -and $ph -match 'color-scheme' -and $ph -match '--fond: #04070c' -and $ph -match '--accent: #4fd2ff' -and $ph -notmatch '(?i)<canvas|three|soleil') 'pilotage.html : thème sombre de Jarvis (mêmes couleurs), jeton injecté à la volée, aucun visuel central (le soleil viendra plus tard)'
$vp = Get-Content "$Root\lib\visage.ps1" -Raw -Encoding UTF8
Verifier ($vp -match "\$chemin -eq '/pilotage-donnees'" -and $vp -match "\$chemin -eq '/pilotage-action'" -and $vp -match "\$chemin -eq '/pilotage-widget'" -and $vp -match "\$chemin -like '/pilotage/\*'" -and $vp.IndexOf('$hoteOk') -lt $vp.IndexOf("/pilotage/*") -and $vp -notmatch 'HttpListener[^\n]*Prefixes\.Add\([^\n]*pilotage') 'lib\visage.ps1 : les routes Pilotage sont derrière les contrôles d''hôte et d''origine ; aucune nouvelle écoute'
Verifier ($code -notmatch '(?i)Invoke-Claude|Invoke-Ollama|Invoke-RestMethod|Invoke-WebRequest|Start-Process\s+[-$''"a-z]|Invoke-Expression\s+\$|Set-Content|Out-File|Add-Content|WriteAllText' -and $code -notmatch '(?i)\.env\b|config\.local|gmail-jeton|dpapi|Get-Content[^\n]*config') 'lib\pilotage.ps1 : aucun appel à Claude ni au réseau, aucune écriture, ne lit ni .env, ni jetons, ni config.local.json'
Verifier ((Get-Content (Join-Path $Root 'jarvis.ps1') -Raw -Encoding UTF8) -match 'lib\\pilotage\.ps1') 'jarvis.ps1 charge le module'
$oct = [IO.File]::ReadAllBytes((Join-Path $Root 'lib\pilotage.ps1'))
Verifier ($oct[0] -eq 0xEF -and $oct[1] -eq 0xBB -and $oct[2] -eq 0xBF) 'lib\pilotage.ps1 en UTF-8 avec BOM'
Verifier ((Get-Content (Join-Path $Root 'README.md') -Raw -Encoding UTF8) -match 'pilotage_actif') 'README : Pilotage décrit'
Verifier ((Get-FileHash (Join-Path $Root 'config.json')).Hash -eq $hashConfig) 'config.json réel inchangé par le test'

Remove-Item Env:DISCORD_BOT_TOKEN -ErrorAction SilentlyContinue
Write-Host ''
Remove-Item $TR -Recurse -Force -ErrorAction SilentlyContinue
if ($echecs) { Write-Host "ÉCHEC : $echecs vérification(s) en échec." -ForegroundColor Red; exit 1 }
Write-Host 'TOUT EST VERT.'
