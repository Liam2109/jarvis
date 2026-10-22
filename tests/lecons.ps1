# Test SILENCIEUX des leçons et du style de parole (lib\lecons.ps1) : création, renforcement, application, revue de nuit (fusion, confiance, promotion PROPOSÉE), secrets et interdits refusés, « omada » -> Ollama, commandes.
# Mémoire et config TEMPORAIRES, Discord simulé (aucun réseau), aucun appel à Claude ni à Ollama, aucun son, aucune fenêtre. Code de sortie 0 = réussi.
$ErrorActionPreference = 'Stop'
$env:JARVIS_TEST = '1'
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $Root 'lib\journal.ps1')
$TR = Join-Path $env:TEMP ('jarvis-test-' + [guid]::NewGuid().ToString('N').Substring(0, 8)); New-Item -ItemType Directory $TR, "$TR\memoire", "$TR\logs" | Out-Null; $script:JarvisRoot = $TR
'# To-do' | Set-Content "$TR\memoire\todo.md" -Encoding UTF8; '# N' | Set-Content "$TR\memoire\notes.md" -Encoding UTF8; '# R' | Set-Content "$TR\memoire\resume.md" -Encoding UTF8
$Config = Get-Content $(if ($env:JARVIS_CONFIG -and (Test-Path $env:JARVIS_CONFIG)) { $env:JARVIS_CONFIG } else { Join-Path $Root 'config.json' }) -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($l in 'voix', 'business', 'permissions', 'actions', 'coffre', 'entrees', 'ecrans', 'tableau', 'visage', 'sons', 'raccourcis', 'cerveau', 'cerveau-local', 'veille', 'memoire', 'rapide', 'discretion', 'modejeu', 'competences', 'marche', 'priorite', 'comprehension', 'routeur', 'pc', 'bureau', 'salle-marche', 'matin', 'discord', 'veille-train', 'veille-mail', 'candidatures', 'initiatives', 'lecons') { . (Join-Path $Root "lib\$l.ps1") }
$script:JarvisRoot = $TR; $script:PolitesseFixe = $true
$echecs = 0
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }
function Fixer([string]$cle, $val) { if ($Config.PSObject.Properties[$cle]) { $Config.$cle = $val } else { $Config | Add-Member -NotePropertyName $cle -NotePropertyValue $val } }
function Journal { $f = Join-Path $TR ('logs\journal-{0}.md' -f (Get-Date -Format 'yyyy-MM-dd')); if (Test-Path $f) { Get-Content $f -Raw -Encoding UTF8 } else { '' } }
function Vider { foreach ($f in 'lecons.json', 'style-parole.json', 'initiatives.json') { Remove-Item (Join-Path $TR "memoire\$f") -Force -ErrorAction SilentlyContinue }; $script:LeconsAppliquees = @(); $script:LeconsEnAttente = $null; $script:LeconsDernierOrdre = '' }
function Cmd([string]$texte) {
    $script:DiscordTampon = New-Object System.Collections.Generic.List[string]; $script:DiscordEmbeds.Clear(); $script:CanalDiscord = 'jarvis'
    $r = Resolve-LeconsOrdre $texte
    @{ traite = $r.traite; texte = $r.texte; tampon = ($script:DiscordTampon -join ' '); embeds = @($script:DiscordEmbeds) }
}
function Etat { Get-LeconsEtat }
$hashConfig = (Get-FileHash (Join-Path $Root 'config.json')).Hash
$vraie = Get-Content (Join-Path $Root 'config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$script:Cartes = @(); $script:InitNotifStub = { param($i) $script:Cartes += $i; $true }
$now = Get-Date

# ---------- Réglage : désactivé par défaut ----------
$sauve = $Config; $Config = [pscustomobject]@{}
Verifier (-not (Get-LeconsConfig).actif) 'sans réglage : leçons désactivées'
$Config = $sauve
Verifier ($vraie.lecons_actif -eq 'non') 'config.json : lecons_actif = "non"'
Fixer 'lecons_actif' 'oui'
Verifier ((Get-LeconsConfig).actif) 'lecons_actif = "oui" : activées'

# ---------- Création et lecture ----------
Vider
Verifier (-not (Test-Path "$TR\memoire\lecons.json") -and -not (Test-Path "$TR\memoire\style-parole.json")) 'aucun fichier avant le premier usage'
$r = Add-Lecon 'Chercher un fichier' 'La recherche par nom exact a marché' 'La recherche large était trop lente' 'Pour chercher un fichier : commencer par le nom exact, élargir ensuite.' @('fichier', 'Recherche') 0.5 $now
$l1 = $r.lecon
Verifier ($r.ok -and $l1.id -eq '1' -and $l1.contexte -and $l1.marche -and $l1.rate -and $l1.regle -and $l1.confiance -eq 0.5 -and $l1.confirmations -eq 1 -and @($l1.etiquettes) -contains 'fichier' -and @($l1.etiquettes) -contains 'recherche' -and $l1.cree_le) 'une leçon a id, contexte, ce qui a marché / raté, règle, confiance, confirmations, étiquettes, date'
Verifier ((Test-Path "$TR\memoire\lecons.json") -and -not (Test-Path "$TR\memoire\style-parole.json")) 'memoire\lecons.json créé au premier usage (style-parole.json seulement quand le style apprend)'
$r2 = Add-Lecon 'Chercher un fichier' '' '' 'Pour chercher un fichier : commencer par le nom exact, élargir ensuite.' @('fichier') 0.5 $now
Verifier ($r2.ok -and $r2.renforcee -and $r2.lecon.confirmations -eq 2 -and $r2.lecon.confiance -eq 0.65 -and @(Get-Lecons).Count -eq 1) 'une leçon identique est renforcée (2 confirmations, confiance 0,65), pas dupliquée'
Verifier ((Get-Lecon '#1').regle -match 'nom exact' -and -not (Get-Lecon '99')) 'lecture par id'
Verifier ((Journal) -match 'Leçon apprise' -and (Journal) -match 'Leçon renforcée') 'journalisé'

# ---------- Refus : secrets, données sensibles, interdits ----------
$refus = @(
    'Utiliser la clé sk_live_abcdefghij1234567890 pour payer', 'Se connecter avec ghp_abcdefghijklmnopqrstuvwx', 'Le jeton eyJabcdefghijklmnop.qrstuvwxyz.abcdefghij est valable', 'Coller AAAABBBBCCCCDDDDEEEEFFFFGGGGHHHH12345678 dans le champ',
    'Le mot de passe est hunter2', 'Retenir mon salaire et mes dettes', 'Rappeler l''ordonnance du médecin', 'Garder mon IBAN en mémoire',
    'Lever l''interdit sur les courtiers', 'Augmenter le plafond de tokens pour Claude', 'Monter le niveau de permission à 1', 'Désactiver l''antivirus pour aller plus vite', 'Acheter des actions Thales', 'Se connecter à Boursorama')
$ok = @($refus | Where-Object { (Add-Lecon 'ctx' '' '' $_ @('test') 0.5).ok })
Verifier ($ok.Count -eq 0 -and @(Get-Lecons).Count -eq 1) "refusées, rien enregistré ($($refus.Count) cas : clés, jetons, mot de passe, santé, argent, identifiants, interdits, permissions, plafond de tokens, antivirus, achat, courtier)"
Verifier ((Journal) -match 'Leçon refusée' -and (Get-Content "$TR\memoire\lecons.json" -Raw -Encoding UTF8) -notmatch 'sk_live|hunter2|ghp_|salaire|IBAN') 'refus journalisés, aucun secret ni donnée sensible dans lecons.json'
$a = Add-Lecon 'ctx' 'secret caché : sk_live_abcdefghij1234567890' '' 'Une règle tout à fait ordinaire sur les fichiers' @('test') 0.5
Verifier (-not $a.ok) 'un secret dans un autre champ (ce qui a marché) est aussi refusé'

# ---------- Application : 3 leçons fiables au plus ----------
Vider
$specs = @(
    @('Règle alpha : toujours confirmer la tâche ajoutée à la to-do avant de répondre.', 0.9), @('Règle bêta : citer le texte exact de la tâche enregistrée dans la réponse.', 0.7),
    @('Règle gamma : proposer de la cocher quand elle est faite plus tard.', 0.6), @('Règle delta : regrouper plusieurs ajouts consécutifs dans un seul message.', 0.5), @('Règle epsilon : vérifier les doublons de tâche dans la liste existante.', 0.2))
foreach ($s in $specs) { [void](Add-Lecon 'Ajout à la to-do' '' '' $s[0] @('todo', 'ajouter') $s[1] $now) }
[void](Add-Lecon 'Musique' '' '' 'Règle zêta : baisser la musique avant de parler à Liam.' @('musique', 'volume') 0.95 $now)
$p = @(Get-LeconsPertinentes 'ajouter une tâche à la todo')
Verifier ($p.Count -eq 3 -and $p[0].regle -match 'alpha' -and $p[1].regle -match 'bêta' -and $p[2].regle -match 'gamma') '3 leçons pertinentes au plus, les plus fiables d''abord'
Verifier (@($p | Where-Object { $_.regle -match 'epsilon|zêta' }).Count -eq 0 -and @(Get-LeconsPertinentes 'quelle heure est-il').Count -eq 0) 'confiance trop basse ou hors sujet : non relue ; aucune leçon pour une tâche sans rapport'
$script:DiscordTampon = New-Object System.Collections.Generic.List[string]; $script:CanalDiscord = 'jarvis'
Use-LeconsAvant ([pscustomobject]@{ type = 'todo_ajouter'; texte = 'x' }) 'ajoute une tâche'
Verifier (($script:DiscordTampon -join ' ') -match 'Je me souviens : Règle alpha' -and @($script:LeconsAppliquees).Count -eq 3 -and (Journal) -match 'Leçons appliquées') 'avant une tâche similaire : la leçon la plus fiable est citée dans la réponse, les 3 sont journalisées'
$script:CanalDiscord = $null; $script:DiscordTampon = $null

# ---------- Après une action : réussite et échec (par Invoke-UneAction) ----------
Vider
$rr = Invoke-UneAction ([pscustomobject]@{ type = 'todo_ajouter'; texte = 'Tâche de test' }) 'ajoute test'
$ls = @(Get-Lecons)
Verifier ($rr.ok -and $ls.Count -eq 1 -and @($ls[0].etiquettes) -contains 'reussite' -and @($ls[0].etiquettes) -contains 'todo') 'une action réussie écrit une leçon « ça marche » (via Invoke-UneAction)'
[void](Invoke-UneAction ([pscustomobject]@{ type = 'todo_ajouter'; texte = 'Autre tâche' }) 'ajoute test 2')
Verifier (@(Get-Lecons).Count -eq 1 -and (Get-Lecon '1').confirmations -eq 2) 'la même réussite renforce la leçon au lieu d''en créer une autre'
$id = (Get-Lecon '1').id; $script:LeconsAppliquees = @($id)
Register-LeconAction ([pscustomobject]@{ type = 'ouvrir_application' }) @{ ok = $false; texte = 'application introuvable' }
$ech = @(Get-Lecons | Where-Object { @($_.etiquettes) -contains 'echec' })
Verifier ($ech.Count -eq 1 -and $ech[0].regle -match 'introuvable' -and $ech[0].rate -match 'introuvable') 'un échec écrit une leçon « ça rate » avec une règle déduite des mots-clés'
Verifier ((Get-Lecon $id).contredit -eq 1) 'un échec contredit les leçons appliquées juste avant'
Fixer 'lecons_actif' 'non'
$n0 = @(Get-Lecons).Count; [void](Invoke-UneAction ([pscustomobject]@{ type = 'todo_ajouter'; texte = 'Désactivé' }) 'x'); Register-LeconAction ([pscustomobject]@{ type = 'x' }) @{ ok = $false; texte = 'e' }
Verifier (@(Get-Lecons).Count -eq $n0 -and (Get-Lecon '1').confirmations -eq 2) 'désactivé : aucune leçon écrite'
Fixer 'lecons_actif' 'oui'

# ---------- Revue de nuit ----------
Vider
$nuit = $now.Date.AddHours(3).AddMinutes(10)
function L([string]$id, [string]$regle, [double]$conf, [int]$confs, [string[]]$tags = @('test'), [int]$contredit = 0, [string]$statut = 'active') { [ordered]@{ id = $id; contexte = 'ctx'; marche = ''; rate = ''; regle = $regle; confiance = $conf; confirmations = $confs; etiquettes = @($tags); cree_le = $now.ToString('o'); maj_le = $now.ToString('o'); statut = $statut; contredit = $contredit; promotion = ''; promotion_refusee = $false } }
Save-LeconsEtat @{ prochain_id = 20; derniere_nuit = ''; lecons = @(
    (L '1' 'Pour renommer un fichier : vérifier le nom exact avant de renommer' 0.6 2 @('renommer')),
    (L '2' 'Pour renommer un fichier : vérifier le nom exact avant de renommer.' 0.5 1 @('renommer')),
    (L '3' 'Pour trier les mails : commencer par les plus récents' 0.7 2 @('mails') 2),
    (L '4' 'Toujours lancer la sauvegarde avant la mise à jour du site' 0.6 1 @('site')),
    (L '5' 'Ne jamais lancer la sauvegarde avant la mise à jour du site' 0.6 3 @('site')),
    (L '6' 'Toujours relire les dates avant de valider un rappel' 0.85 3 @('rappel')),
    (L '7' 'Règle permanente déjà acquise sur les noms de fichiers' 0.9 6 @('fichier') 3 'permanente')) }
Verifier ($null -eq (Invoke-LeconsNuit $nuit.Date.AddHours(14))) 'à 14 h : aucune revue de nuit'
$rn = Invoke-LeconsNuit $nuit
$e = Etat; $byId = @{}; foreach ($x in $e.lecons) { $byId[$x.id] = $x }
Verifier ($rn.fusionnees -eq 1 -and -not $byId.ContainsKey('2') -and $byId['1'].confirmations -eq 3 -and $byId['1'].confiance -eq 0.65) 'doublons fusionnés (n° 2 dans n° 1 : 3 confirmations, confiance 0,65)'
Verifier ($byId['3'].confiance -eq 0.4 -and $byId['3'].contredit -eq 0) 'leçon contredite deux fois : confiance 0,7 -> 0,4'
Verifier ($byId['4'].confiance -eq 0.45 -and $byId['5'].confiance -eq 0.6) 'règles opposées (toujours / jamais) : la moins confirmée baisse (0,6 -> 0,45)'
Verifier ($byId['7'].confiance -eq 0.9 -and $byId['7'].statut -eq 'permanente') 'une règle permanente n''est jamais baissée'
$promo = @(Get-Initiatives | Where-Object { $_.source -eq 'lecons' })
Verifier ($rn.promotions.Count -eq 1 -and $promo.Count -eq 1 -and $promo[0].type -eq 'maintenance' -and $promo[0].statut -eq 'en_attente' -and $promo[0].titre -match 'n° 6' -and $byId['6'].promotion -eq $promo[0].id) 'leçon fiable (>= 0,8 et >= 3 confirmations) : promotion PROPOSÉE par une initiative « maintenance » en attente'
Verifier ($byId['6'].statut -eq 'active' -and $byId['1'].statut -eq 'active') 'rien n''est promu sans accord : la leçon reste « active »'
Verifier (@(Get-Initiatives | Where-Object { $_.source -eq 'lecons' }).Count -eq 1 -and $script:Cartes.Count -eq 1) 'la proposition est annoncée à Liam (une carte)'
Verifier ($null -eq (Invoke-LeconsNuit $nuit.AddMinutes(30))) 'une seule revue par jour'
$rn2 = Invoke-LeconsNuit $nuit.AddDays(1)
Verifier ($rn2.promotions.Count -eq 0 -and @(Get-Initiatives | Where-Object { $_.source -eq 'lecons' }).Count -eq 1) 'le lendemain : la promotion en attente n''est pas reproposée'
Fixer 'initiatives_niveau' 5
Verifier (-not (Test-InitiativeSansApprobation $promo[0] 5)) 'même au niveau d''autonomie 5, la promotion exige l''accord de Liam'
Fixer 'initiatives_niveau' 1
[void](Approve-Initiative $promo[0].id)
Verifier ((Etat).lecons | Where-Object { $_.id -eq '6' } | ForEach-Object { $_.statut -eq 'active' }) 'approuver l''initiative seul ne change pas encore la leçon (elle est lue à la revue suivante ou en listant)'
Verifier ((Update-LeconsPromotions) -eq 1 -and (Get-Lecon '6').statut -eq 'permanente' -and (Journal) -match 'Leçon promue') 'après « approuver » : la leçon devient une règle permanente'
# refus de Liam : jamais reproposée
Vider
Save-LeconsEtat @{ prochain_id = 5; derniere_nuit = ''; lecons = @((L '1' 'Toujours vérifier les liens avant de les ouvrir' 0.9 4 @('liens'))) }
[void](Invoke-LeconsNuit $nuit.AddDays(2)); $pi = @(Get-Initiatives | Where-Object { $_.source -eq 'lecons' })[0]
[void](Reject-Initiative $pi.id); [void](Update-LeconsPromotions)
$l1 = Get-Lecon '1'
Verifier ($l1.promotion_refusee -eq $true -and $l1.statut -eq 'active') 'promotion refusée par Liam : la leçon reste active et marquée « refusée »'
[void](Invoke-LeconsNuit $nuit.AddDays(3))
Verifier (@(Get-Initiatives | Where-Object { $_.source -eq 'lecons' }).Count -eq 1) 'une promotion refusée n''est plus jamais reproposée'
# Update-Lecons : conditions
Fixer 'lecons_actif' 'non'; $script:LeconsNuitProchain = [datetime]::MinValue
Verifier (-not (Update-Lecons $nuit.AddDays(9))) 'désactivé : Update-Lecons ne fait rien'
Fixer 'lecons_actif' 'oui'; $script:ModeJeu = $true
Verifier (-not (Update-Lecons $nuit.AddDays(9))) 'mode jeu : rien'
$script:ModeJeu = $false
Verifier (-not (Update-Lecons $nuit.Date.AddDays(9).AddHours(14))) 'à 14 h : rien'
Verifier ((Update-Lecons $nuit.AddDays(9)) -and -not (Update-Lecons $nuit.AddDays(9).AddMinutes(1))) 'entre 3 h et 5 h : la revue tourne, vérifiée au plus toutes les 5 minutes'

# ---------- Style de parole : mots mal transcrits ----------
Vider
[IO.File]::WriteAllText("$TR\memoire\vocabulaire-voix.txt", 'Jarvis, Supabase, Stripe, chrome, ouvre, ferme', [Text.UTF8Encoding]::new($false))
[IO.File]::WriteAllText("$TR\memoire\grammaire-voix.json", '["ouvre chrome","ferme chrome","quelle heure est-il"]', [Text.UTF8Encoding]::new($false))
$hv = (Get-FileHash "$TR\memoire\vocabulaire-voix.txt").Hash + (Get-FileHash "$TR\memoire\grammaire-voix.json").Hash
Verifier (Test-LeconProche 'omada' 'ollama') '« omada » ressemble à « Ollama » (même initiale et finale, 3 modifications au plus)'
Verifier (-not (Test-LeconProche 'chrome' 'chronos') -and -not (Test-LeconProche 'ouvre' 'ouvert')) 'deux mots différents ne sont pas confondus'
$amb = Find-AmbiguiteParole 'ouvre omada'
Verifier ($amb -and $amb.propose -eq 'ouvre Ollama' -and $amb.mots[0].entendu -eq 'omada' -and $amb.mots[0].voulu -eq 'Ollama' -and -not $amb.auto) 'ambiguïté : « ouvre omada » -> lecture probable « ouvre Ollama »'
Verifier ($null -eq (Find-AmbiguiteParole 'ouvre chrome') -and $null -eq (Find-AmbiguiteParole 'lance Ollama') -and $null -eq (Find-AmbiguiteParole 'quelle heure est-il')) 'les mots connus (grammaire, vocabulaire, termes clés) ne déclenchent rien'
$x = Cmd 'ouvre omada'
Verifier ($x.traite -and $x.tampon -match 'Tu veux dire « ouvre Ollama » \?' -and $script:LeconsEnAttente) 'Jarvis demande « Tu veux dire Ollama ? » au lieu de deviner'
$x = Cmd 'oui'
Verifier (-not $x.traite -and $x.texte -eq 'ouvre Ollama' -and -not $script:LeconsEnAttente) '« oui » : l''ordre continue avec « ouvre Ollama »'
$st = Get-StyleEtat; $m = @($st.elements | Where-Object { $_.genre -eq 'mot' })[0]
Verifier ($m.cle -eq 'omada' -and $m.valeur -eq 'Ollama' -and $m.confirmations -eq 1 -and (Test-Path "$TR\memoire\style-parole.json")) 'le mot corrigé est mémorisé dans memoire\style-parole.json (créé à ce moment)'
$lc = @(Get-Lecons | Where-Object { @($_.etiquettes) -contains 'omada' })
Verifier ($lc.Count -eq 1 -and $lc[0].regle -match 'omada.*Ollama') 'la confirmation de Liam crée une leçon'
$x = Cmd 'ouvre omada'; $x = Cmd 'non'
Verifier ($x.traite -and $x.tampon -match 'ne change rien' -and (@(Get-StyleEtat).elements | Where-Object { $_.genre -eq 'mot' }).confirmations -eq 1) '« non » : rien n''est appris, rien n''est changé'
$x = Cmd 'ouvre omada'; $x = Cmd 'non, je voulais dire Ollama'
$m = @((Get-StyleEtat).elements | Where-Object { $_.genre -eq 'mot' })[0]
Verifier ($x.traite -and $x.tampon -match 'Noté.*omada.*Ollama' -and $m.confirmations -eq 2 -and (Get-Lecon $lc[0].id).confirmations -eq 2) 'correction « je voulais dire Ollama » : le mot et la leçon sont renforcés'
$x = Cmd 'ouvre omada'
Verifier ($x.traite -and $x.tampon -match 'Tu veux dire') 'avec 2 confirmations, Jarvis demande encore'
$x = Cmd 'non'; [void](Add-StyleElement 'mot' 'omada' 'Ollama')
$x = Cmd 'ouvre omada'
Verifier (-not $x.traite -and $x.texte -eq 'ouvre Ollama' -and $x.tampon -match 'J''ai compris « ouvre Ollama »') 'avec 3 confirmations : appliqué en le disant (« J''ai compris … »)'
$x = Cmd 'c''est bon'
Verifier (-not $x.traite) '« c''est bon » n''est pas pris pour une correction de mot'
Verifier ((Get-FileHash "$TR\memoire\vocabulaire-voix.txt").Hash + (Get-FileHash "$TR\memoire\grammaire-voix.json").Hash -eq $hv) 'vocabulaire-voix.txt et grammaire-voix.json jamais modifiés'

# ---------- Style : tournures, longueur, sujets, sensible ----------
Vider
Update-StyleDepuisOrdre 'note-le dans la to-do'; Update-StyleDepuisOrdre 'Note le aussi'; Update-StyleDepuisOrdre 'tu captes ?'
$s = Get-StyleEtat
$tn = @($s.elements | Where-Object { $_.genre -eq 'tournure' -and $_.cle -eq 'note-le' })[0]; $tc = @($s.elements | Where-Object { $_.genre -eq 'tournure' -and $_.cle -eq 'tu captes ?' })[0]
Verifier ($tn.confirmations -eq 2 -and $tn.sens -match 'to-do' -and $tc.sens -match 'compris') 'tournures habituelles reconnues avec leur sens (« note-le », « tu captes ? »)'
Verifier ((Get-LongueurPreferee) -eq 'courte') 'longueur préférée par défaut : courte et directe'
Update-StyleDepuisOrdre 'développe un peu'; Update-StyleDepuisOrdre 'explique plus'
Verifier ((Get-LongueurPreferee) -eq 'detaillee') 'longueur apprise : plus de détails demandés deux fois -> détaillée'
Update-StyleDepuisOrdre 'sois plus court'; Update-StyleDepuisOrdre 'en bref'; Update-StyleDepuisOrdre 'trop long'
Verifier ((Get-LongueurPreferee) -eq 'courte') 'longueur apprise : « plus court » plus souvent -> courte'
Update-StyleDepuisOrdre 'où en est le saas'; Update-StyleDepuisOrdre 'ouvre le saas'; Update-StyleDepuisOrdre 'candidatures du jour'
$sj = @((Get-StyleEtat).elements | Where-Object { $_.genre -eq 'sujet' -and $_.cle -eq 'saas' })[0]
Verifier ($sj.confirmations -eq 2) 'sujets récurrents comptés (saas ×2)'
$avant = @((Get-StyleEtat).elements).Count
Update-StyleDepuisOrdre 'note-le, mon salaire est de 3000 euros pour le saas'; Update-StyleDepuisOrdre 'note-le, le mot de passe du saas est hunter2'
Verifier (@((Get-StyleEtat).elements).Count -eq $avant -and (Get-Content "$TR\memoire\style-parole.json" -Raw -Encoding UTF8) -notmatch 'salaire|hunter2') 'un ordre qui parle d''argent, de santé ou de mot de passe n''apprend rien'
Verifier ($null -eq (Add-StyleElement 'mot' 'bidule' 'mot de passe') -and $null -eq (Add-StyleElement 'mot' 'sk_live_abcdefghij1234567890' 'x')) 'le style refuse secrets et données sensibles'
$idt = $tn.id; $r = Remove-StyleElement $idt
Update-StyleDepuisOrdre 'note-le encore'
Verifier ($r.ok -and @((Get-StyleEtat).elements | Where-Object { $_.cle -eq 'note-le' }).Count -eq 0) 'un élément oublié par Liam n''est pas réappris'

# ---------- Commandes ----------
Vider
$a1 = (Add-Lecon 'ctx' '' '' 'Règle permanente : relire avant d''envoyer à Liam' @('relire') 0.9 $now).lecon; $a2 = (Add-Lecon 'ctx' '' '' 'Règle en cours : vérifier les dates des rappels' @('dates') 0.4 $now).lecon; $a3 = (Add-Lecon 'ctx' '' '' 'Règle fiable : citer la source des chiffres' @('chiffres') 0.7 $now).lecon
$e = Etat; $e.lecons[0].statut = 'permanente'; Save-LeconsEtat $e
$x = Cmd 'leçons'
$noms = ($x.embeds[0].champs | ForEach-Object { $_.nom }) -join ' | '
Verifier ($x.traite -and $x.embeds.Count -eq 1 -and $x.embeds[0].titre -eq 'Leçons apprises' -and $x.embeds[0].couleur -eq $script:CouleurBleue -and $noms -match 'Règles permanentes \(1\)' -and $noms -match 'Leçons fiables \(1\)' -and $noms -match 'Leçons en cours \(1\)') 'commande « leçons » : carte bleue, règles permanentes / fiables / en cours'
$x = Cmd 'Jarvis, oublie la leçon 2.'
Verifier ($x.traite -and $x.tampon -match 'n° 2 oubliée' -and -not (Get-Lecon '2') -and (Get-Lecons).Count -eq 2) 'commande « oublie la leçon 2 »'
Verifier ((Cmd 'oublie la leçon 99').tampon -match 'ne trouve pas') 'leçon inconnue : réponse polie'
[void](Add-StyleElement 'mot' 'omada' 'Ollama'); [void](Add-StyleElement 'tournure' 'note-le' '' 'ajouter à la to-do'); Update-StyleDepuisOrdre 'sois plus court'
$x = Cmd 'style'
$noms = ($x.embeds[0].champs | ForEach-Object { $_.nom }) -join ' | '
Verifier ($x.traite -and $x.embeds[0].titre -eq 'Votre façon de parler' -and $x.embeds[0].couleur -eq $script:CouleurBleue -and $noms -match 'Longueur des réponses' -and $noms -match 'Mots que je corrige' -and $noms -match 'Vos tournures' -and ($x.embeds[0].champs | Where-Object { $_.nom -eq 'Mots que je corrige' }).valeur -match 'omada.*Ollama') 'commande « style » : longueur, mots corrigés, tournures'
$idm = @((Get-StyleEtat).elements | Where-Object { $_.genre -eq 'mot' })[0].id
$x = Cmd "oublie le style $idm"
Verifier ($x.traite -and $x.tampon -match 'Style oublié' -and @((Get-StyleEtat).elements | Where-Object { $_.genre -eq 'mot' }).Count -eq 0) 'commande « oublie le style <n°> »'
$x = Cmd 'oublie le style longueur'
Verifier ($x.traite -and (Get-StyleEtat).courte -eq 0) 'commande « oublie le style longueur »'
Verifier ((Cmd 'oublie le style 999').tampon -match 'ne trouve pas') 'élément de style inconnu : réponse polie'
Fixer 'discord_style' 'texte'
$x = Cmd 'leçons'
Verifier ($x.traite -and $x.embeds.Count -eq 0 -and $x.tampon -match 'Règle') 'style « texte » : réponse en texte simple'
Fixer 'discord_style' 'embed'
$x = Cmd 'quelle heure est-il'
Verifier (-not $x.traite -and $x.texte -eq 'quelle heure est-il') 'un ordre ordinaire passe sans changement'
# désactivé
Vider; Fixer 'lecons_actif' 'non'
$x = Cmd 'leçons'
Verifier ($x.traite -and $x.tampon -match 'désactivé') 'désactivé : « leçons » répond poliment'
$x = Cmd 'ouvre omada'; [void](Cmd 'note-le')
Verifier (-not $x.traite -and -not (Test-Path "$TR\memoire\style-parole.json") -and -not (Test-Path "$TR\memoire\lecons.json")) 'désactivé : aucune ambiguïté, aucun apprentissage, aucun fichier créé'
Fixer 'lecons_actif' 'oui'
$script:CanalDiscord = $null; $script:DiscordTampon = $null; $script:DiscordEmbeds.Clear()

# ---------- Cartes (limites de Discord) ----------
$beaucoup = @(1..12 | ForEach-Object { [ordered]@{ id = "$_"; regle = ('Règle ' + $_ + ' ' + ('z' * 200)); confiance = 0.7; confirmations = 3; statut = 'active' } })
$gl = New-EmbedLecons $beaucoup
$tot = $gl.titre.Length + $gl.description.Length + $gl.pied.Length; foreach ($f in $gl.champs) { $tot += $f.nom.Length + $f.valeur.Length }
Verifier ($tot -le 6000 -and ($gl.champs | Where-Object { $_.valeur.Length -gt 1024 }).Count -eq 0 -and $gl.titre -match '^[\p{L}0-9]' -and (($gl.description + ($gl.champs | ForEach-Object { $_.valeur })) -notmatch '```')) 'carte « leçons » : limites de Discord respectées, titre sans emoji, aucun bloc de code'
$gv = New-EmbedLecons @(); $gs = New-EmbedStyle @{ elements = @(); courte = 0; detaillee = 0 }
Verifier ($gv.description -match 'aucune leçon' -and $gs.description -match 'rien appris') 'cartes vides : messages polis'

# ---------- Garde-fous du code ----------
$src = Get-Content (Join-Path $Root 'lib\lecons.ps1') -Raw -Encoding UTF8; $srcCode = (($src -split "`n") | Where-Object { $_ -notmatch '^\s*#' }) -join "`n"
Verifier ($srcCode -notmatch '(?i)Invoke-Claude|claude\s+-p|Invoke-OllamaLocal|Invoke-Ollama|localhost:11434|Invoke-RestMethod|Invoke-WebRequest|Start-Process|Invoke-Expression|\biex\b') 'aucun appel à Claude, à Ollama, au réseau ni à un programme : 0 token'
Verifier ($srcCode -notmatch '(?i)Set-Content|Out-File|WriteAllText|Add-Content' -and $srcCode -notmatch '(?i)config\.json|config\.local|interdits\.json|permissions\.ps1' -and $srcCode -notmatch '\$script:(TypesNiveau3|MotifsInterdits|Actions)\s*=') 'le module n''écrit aucun fichier directement et ne touche ni config, ni interdits, ni permissions'
Verifier ($srcCode -notmatch '(?i)vocabulaire-voix\.txt''[^\n]*(Set|Out|Write|Add)' -and $srcCode -match 'Get-Content \$f' ) 'vocabulaire-voix.txt et grammaire-voix.json : lecture seule'
$js = Get-Content (Join-Path $Root 'jarvis.ps1') -Raw -Encoding UTF8; $dc = Get-Content (Join-Path $Root 'lib\discord.ps1') -Raw -Encoding UTF8; $cv = Get-Content (Join-Path $Root 'lib\cerveau.ps1') -Raw -Encoding UTF8
Verifier ($js -match 'lib\\lecons\.ps1' -and $js -match '\(Update-Lecons\)' -and $dc -match 'Resolve-LeconsOrdre' -and $cv -match 'Use-LeconsAvant' -and $cv -match 'Register-LeconAction') 'câblage : jarvis.ps1 (chargement + revue de nuit), discord.ps1 (commandes), cerveau.ps1 (avant / après une action)'
$octets = [IO.File]::ReadAllBytes((Join-Path $Root 'lib\lecons.ps1'))
Verifier ($octets[0] -eq 0xEF -and $octets[1] -eq 0xBB -and $octets[2] -eq 0xBF) 'lib\lecons.ps1 en UTF-8 avec BOM'
Verifier ((Get-Content (Join-Path $Root 'README.md') -Raw -Encoding UTF8) -match 'lecons_actif') 'README : leçons décrites'
Verifier ((Get-FileHash (Join-Path $Root 'config.json')).Hash -eq $hashConfig) 'config.json réel inchangé par le test'

Write-Host ''
Remove-Item $TR -Recurse -Force -ErrorAction SilentlyContinue
if ($echecs) { Write-Host "ÉCHEC : $echecs vérification(s) en échec." -ForegroundColor Red; exit 1 }
Write-Host 'TOUT EST VERT.'
