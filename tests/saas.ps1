# Test SILENCIEUX du point SaaS (embed Discord à champs, sources branchées seulement, aucun chiffre inventé) et du briefing du matin (briefing_actif, briefing_heure, briefing-test).
# Toutes les sources sont des BOUCHONS : aucun réseau, aucun son, aucune fenêtre. Mémoire et journal dans un dossier temporaire. Code de sortie 0 = réussi.
$ErrorActionPreference = 'Stop'
$env:JARVIS_TEST = '1'
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $Root 'lib\journal.ps1')
$TR = Join-Path $env:TEMP ('jarvis-test-' + [guid]::NewGuid().ToString('N').Substring(0, 8)); New-Item -ItemType Directory $TR, "$TR\memoire", "$TR\logs" | Out-Null; $script:JarvisRoot = $TR
"# To-do de Liam`r`n- [ ] Corriger le formulaire du quiz`r`n- [ ] Appeler le comptable" | Set-Content "$TR\memoire\todo.md" -Encoding UTF8; '# N' | Set-Content "$TR\memoire\notes.md" -Encoding UTF8; '# R' | Set-Content "$TR\memoire\resume.md" -Encoding UTF8
$Config = Get-Content $(if ($env:JARVIS_CONFIG -and (Test-Path $env:JARVIS_CONFIG)) { $env:JARVIS_CONFIG } else { Join-Path $Root 'config.json' }) -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($l in 'voix', 'business', 'permissions', 'actions', 'coffre', 'entrees', 'ecrans', 'tableau', 'visage', 'sons', 'raccourcis', 'cerveau', 'cerveau-local', 'veille', 'memoire', 'rapide', 'discretion', 'modejeu', 'competences', 'marche', 'priorite', 'comprehension', 'routeur', 'pc', 'bureau', 'salle-marche', 'matin', 'discord', 'saas') { . (Join-Path $Root "lib\$l.ps1") }
[void](Import-Competences (Join-Path $Root 'lib\competences'))
$script:JarvisRoot = $TR; $script:PolitesseFixe = $true
$echecs = 0
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }
function Fixer([string]$cle, $val) { if ($Config.PSObject.Properties[$cle]) { $Config.$cle = $val } else { $Config | Add-Member -NotePropertyName $cle -NotePropertyValue $val } }
function Effacer([string]$cle) { if ($Config.PSObject.Properties[$cle]) { $Config.PSObject.Properties.Remove($cle) } }
$vraie = Get-Content (Join-Path $Root 'config.json') -Raw -Encoding UTF8 | ConvertFrom-Json

# ----- bouchons : aucune source réelle -----
$script:SimSite = [pscustomobject]@{ ok = $true; code = 200; detail = '' }
$script:SimStats = @{ dispo = $true; http = 200; sessions = 14; emails = 3; source = 'Supabase (jarvis_stats)'; saas = @{ quiz_total = 1280; quiz_24h = 14; emails_total = 412; emails_24h = 3; abonnes_actifs = 27; nouveaux_abonnes_24h = 2; abonnes_en_annulation = 1; paiements_echoues = 0 } }
$script:SimCa = @{ dispo = $true; montants = @{ EUR = 5800 }; paiements = 2; partiel = $false; source = 'Stripe' }
$script:Appels = 0
function Get-StatutSite([int]$timeout = 15) { $script:Appels++; $script:SimSite }
function Get-SupabaseStats([datetime]$depuis) { $script:Appels++; $script:SimStats }
function Get-StripeCA([datetime]$depuis) { $script:Appels++; $script:SimCa }
function Get-StripeAbonnes([datetime]$depuis) { @{ dispo = $false; raison = 'clé Stripe absente dans .env' } }
function Get-LigneMarcheCourte { $null }
$script:Messages = @()
function Send-MessageDiscord([string]$canal, [string]$texte, [string]$replyTo = '', $embed = $null) { $script:Messages += @{ canal = $canal; texte = $texte; embed = $embed }; $true }
$script:Actif = $true; $script:ModeJeu = $false
Fixer 'marche_actif' $false; Fixer 'discord_style' 'embed'; Effacer 'meteo_latitude'; Effacer 'meteo_longitude'
function Journal { $f = Join-Path $TR ('logs\journal-{0}.md' -f (Get-Date -Format 'yyyy-MM-dd')); if (Test-Path $f) { Get-Content $f -Raw -Encoding UTF8 } else { '' } }
function Champ($e, [string]$debut) { @($e.champs | Where-Object { $_.nom -like "*$debut*" })[0] }
$cc = [string][char]0xE7; $ee = [string][char]0xE9; $ap = [string][char]0x2019

Write-Host '1) Reconnaître une demande de point SaaS'
foreach ($p in @("as-tu les donn${ee}es du SaaS", 'chiffres', 'stats', 'les stats', "comment va le site", 'où en est le SaaS ?', "Jarvis, comment va le site ?", 'donne-moi les chiffres du SaaS', 'fais le point sur le business', "quelles sont les statistiques du site", 'état du business')) {
    Verifier (Test-DemandePointSaas $p) "point SaaS : « $p »"
}
foreach ($p in @('ouvre le site', 'ajoute une tâche pour le site', 'ferme chrome', 'comment ça va', 'pourquoi le ciel est bleu', 'où en est Thales', 'mets le volume à trente', 'ajoute stats à ma to-do', 'dev : améliore le site')) {
    Verifier (-not (Test-DemandePointSaas $p)) "pas un point SaaS : « $p »"
}

Write-Host '2) Données lues et embed à champs'
$d = Get-SaasDonnees
$e = New-EmbedSaas $d
$noms = @($e.champs | ForEach-Object { $_.nom }) -join ' | '
Verifier ($e.champs.Count -ge 8 -and $noms -match 'Site' -and $noms -match 'Quiz' -and $noms -match 'E-mails' -and $noms -match 'Abonn' -and $noms -match "Chiffre d'affaires" -and $noms -match 'Visites' -and $noms -match 'ches' -and $noms -match 'Veille') "embed : champs site, quiz, e-mails, abonnés, chiffre d'affaires, visites, tâches, veille ($($e.champs.Count) champs)"
Verifier ((Champ $e 'Site').valeur -eq 'En ligne (HTTP 200)') 'site : « En ligne (HTTP 200) »'
Verifier ((Champ $e 'Quiz').valeur -match '^14 sur 24 h' -and (Champ $e 'Quiz').valeur -match 'Total : 1280') 'quiz : 14 sur 24 h, total 1280'
Verifier ((Champ $e 'E-mails').valeur -match '^3 sur 24 h' -and (Champ $e 'E-mails').valeur -match 'Total : 412') 'e-mails : 3 sur 24 h, total 412'
Verifier ((Champ $e 'Abonn').valeur -match '27 actifs' -and (Champ $e 'Abonn').valeur -match '2 nouveaux sur 24 h' -and (Champ $e 'Abonn').valeur -match "1 en cours d.annulation") 'abonnés : actifs, nouveaux, annulations'
Verifier ((Champ $e "Chiffre").valeur -match '^58 euros sur 24 h') "chiffre d'affaires : 58 euros sur 24 h (Stripe)"
Verifier ((Champ $e 'Visites').valeur -eq 'Source non branchée (Vercel Analytics)') 'visites : « Source non branchée (Vercel Analytics) » (aucun chiffre inventé)'
Verifier ((Champ $e 'ches').valeur -match '^2 ouvertes' -and (Champ $e 'ches').valeur -match 'Corriger le formulaire du quiz') 'tâches ouvertes : nombre et premières tâches'
Verifier ((Champ $e 'Veille').valeur -match 'désactivée') 'veille : désactivée (marche_actif = false), dit honnêtement'
Verifier ($e.couleur -eq $script:CouleurBleue -and -not ($e.champs | Where-Object { $_.nom -match 'Paiements' })) 'tout va bien : embed bleu, pas de champ paiements'
Verifier (($e.description -match '^(Bonjour|Bonsoir) monsieur, voici le point') -and $e.description -notmatch '\.\.|;|vais vous lire|écoute') 'description : Bonjour / Bonsoir selon l''heure, sans « Je vais vous lire », sans « Je vous écoute », sans double point'
$tout = ($e.champs | ForEach-Object { $_.valeur }) -join ' '
Verifier ($tout -notmatch ';' -and $tout -notmatch '\.\.' -and $tout -notmatch 'souci est survenu') 'aucun point-virgule en chaîne, aucun double point'
Verifier ($e.titre -notmatch 'souci') 'ce n''est pas un embed d''erreur'

Write-Host '3) Sources absentes ou en panne : dit, jamais inventé'
$script:SimStats = @{ dispo = $false; http = 403; cas = '403'; raison = 'Supabase : jeton refusé (JARVIS_STATS_TOKEN faux ou vide)' }
$script:SimCa = @{ dispo = $false; raison = 'clé Stripe absente dans .env' }
$script:SimSite = [pscustomobject]@{ ok = $false; code = 503; detail = '' }
$d = Get-SaasDonnees; $e = New-EmbedSaas $d
Verifier ((Champ $e 'Quiz').valeur -match '^Indisponible : accès refusé par Supabase' -and (Champ $e 'Abonn').valeur -match '^Indisponible') 'Supabase refusé : « Indisponible : accès refusé par Supabase… » (aucun chiffre)'
Verifier ((Champ $e "Chiffre").valeur -match '^Source non branchée' -and (Champ $e "Chiffre").valeur -match 'STRIPE_RESTRICTED_KEY') 'Stripe sans clé : « Source non branchée (STRIPE_RESTRICTED_KEY) »'
Verifier ((Champ $e 'Site').valeur -eq 'Problème : HTTP 503' -and $e.couleur -eq $script:CouleurOrange) 'site en panne : HTTP 503 affiché, embed orange'
Verifier (((Champ $e 'Quiz').valeur + (Champ $e 'E-mails').valeur) -notmatch '\d{2,}') 'aucun chiffre dans les champs indisponibles'
$j = Journal; Verifier ($j -match 'Point SaaS : lecture stats' -and $j -match 'indisponible' -and $j -match 'lecture ca') 'le journal note chaque source lue ou indisponible'
$script:SimStats = @{ dispo = $true; http = 200; sessions = 0; emails = 0; saas = @{ quiz_24h = 0; paiements_echoues = 2; abonnes_actifs = 1 } }
$script:SimCa = @{ dispo = $true; montants = @{}; paiements = 0; partiel = $true; source = 'Stripe' }
$script:SimSite = [pscustomobject]@{ ok = $true; code = 200; detail = '' }
$e = New-EmbedSaas (Get-SaasDonnees)
Verifier ((Champ $e 'Paiements').valeur -match '2 paiements échoués' -and $e.couleur -eq $script:CouleurOrange) 'paiements échoués : champ dédié, embed orange'
Verifier ((Champ $e "Chiffre").valeur -match '0 € sur 24 h \(au moins\)' -and (Champ $e 'E-mails').valeur -eq 'Non communiqué par la source') 'zéro lu = « 0 € » ; champ absent de la source = « Non communiqué » (pas un zéro inventé)'

Write-Host '4) Sur Discord : le point direct, sans embed rouge'
$script:SimStats = @{ dispo = $true; http = 200; sessions = 14; emails = 3; saas = @{ quiz_total = 1280; quiz_24h = 14; emails_total = 412; emails_24h = 3; abonnes_actifs = 27; nouveaux_abonnes_24h = 2; abonnes_en_annulation = 0; paiements_echoues = 0 } }
$script:SimCa = @{ dispo = $true; montants = @{ EUR = 5800 }; paiements = 2; partiel = $false; source = 'Stripe' }
$script:DiscordTampon = New-Object System.Collections.Generic.List[string]; $script:DiscordEmbeds.Clear()
foreach ($p in @("as-tu les donn${ee}es du SaaS", 'stats', 'comment va le site', 'où en est le SaaS')) {
    $script:DiscordTampon.Clear(); $script:DiscordEmbeds.Clear()
    $r = Invoke-CommandeDiscord $p
    Verifier ($r -eq $true -and $script:DiscordEmbeds.Count -eq 1 -and $script:DiscordTampon.Count -eq 0 -and $script:DiscordEmbeds[0].titre -match 'Trouve ton produit') "« $p » : un seul embed « le point », aucun texte parasite"
}
$script:DiscordTampon.Clear(); $script:DiscordEmbeds.Clear(); Fixer 'discord_style' 'texte'
[void](Invoke-CommandeDiscord 'chiffres')
Verifier ($script:DiscordEmbeds.Count -eq 0 -and "$($script:DiscordTampon -join ' ')" -match 'Site : En ligne' -and "$($script:DiscordTampon -join ' ')" -notmatch ';|\.\.|vais vous lire') 'style texte : phrases courtes, sans point-virgule, sans « Je vais vous lire »'
Fixer 'discord_style' 'embed'
# la mise en forme générique ne transforme PAS le point en « Un souci est survenu » même quand une source manque
$script:SimStats = @{ dispo = $false; raison = 'Supabase : jeton refusé' }; $script:SimCa = @{ dispo = $false; raison = 'clé Stripe absente dans .env' }
$script:DiscordEmbeds.Clear(); $script:DiscordTampon.Clear(); [void](Invoke-CommandeDiscord 'stats')
$eb = $script:DiscordEmbeds[0]
Verifier ($eb.titre -notmatch 'souci' -and $eb.couleur -ne $script:CouleurRouge) 'sources manquantes : embed du point normal (jamais l''embed rouge « Un souci est survenu »)'
$vrai = ConvertTo-EmbedReponse @('Une erreur est survenue : disque plein.'); Verifier ($vrai -and $vrai.titre -eq 'Problème' -and $vrai.couleur -eq $script:CouleurRouge) 'le vrai embed d''erreur existe toujours pour une vraie erreur'
$ancien = ConvertTo-EmbedReponse @("Sur les 24 dernières heures : 3 e-mails. Je n'ai pas pu lire : Stripe, clé absente.")
Verifier ($null -ne $ancien) 'cause trouvée : l''ancien texte du point contenait « Je n''ai pas pu lire », reconnu à tort comme erreur par ConvertTo-EmbedReponse (le point ne passe plus par là)'
$script:DiscordTampon = $null; $script:DiscordEmbeds.Clear()

Write-Host '5) Action point_saas (voix et Claude) : mêmes données'
$script:CanalDiscord = $null; $script:SimStats = @{ dispo = $true; http = 200; sessions = 14; emails = 3; saas = @{ quiz_total = 1280; quiz_24h = 14; emails_total = 412; emails_24h = 3; abonnes_actifs = 27; nouveaux_abonnes_24h = 2; abonnes_en_annulation = 0; paiements_echoues = 0 } }; $script:SimCa = @{ dispo = $true; montants = @{ EUR = 5800 }; paiements = 2; partiel = $false; source = 'Stripe' }
$act = $script:Actions['point_saas']; $arg = [pscustomobject]@{ type = 'point_saas' }; $r = & $act.run $arg
Verifier ($r.ok -and $r.texte -match 'Site : En ligne \(HTTP 200\)\.' -and $r.texte -match 'Quiz : 14 sur 24 h' -and $r.texte -notmatch ';|\.\.') 'point_saas : phrases courtes à voix haute, mêmes chiffres, sans point-virgule'

Write-Host '6) Briefing du matin'
$b = Get-BriefingConfig
Verifier ($vraie.briefing_actif -eq 'non' -and $vraie.briefing_heure -eq '07:30' -and -not $b.actif -and $b.heure -eq '07:30') 'config.json : briefing_actif = "non", briefing_heure = "07:30" (défaut)'
Fixer 'briefing_heure' '6:05'; Verifier ((Get-BriefingConfig).heure -eq '06:05') 'briefing_heure : 6:05 -> 06:05'; Fixer 'briefing_heure' 'n''importe quoi'; Verifier ((Get-BriefingConfig).heure -eq '07:30') 'heure illisible : retour à 07:30'
Fixer 'briefing_actif' 'oui'; Verifier ((Get-BriefingConfig).actif) 'briefing_actif = "oui" l''active'; Fixer 'briefing_actif' 'non'
$script:DiscordPumpActif = $true; $script:Messages = @()
Verifier (-not (Update-BriefingMatinSaas)) 'briefing_actif = "non" : rien n''est envoyé'
$moins = (Get-Date).AddMinutes(-1)
if ($moins.Date -eq (Get-Date).Date) {
    Fixer 'briefing_actif' 'oui'; Fixer 'briefing_heure' ($moins.ToString('HH:mm'))
    $fait = Update-BriefingMatinSaas; $encore = Update-BriefingMatinSaas
    Verifier ($fait -and -not $encore -and $script:Messages.Count -eq 1 -and $script:Messages[0].canal -eq 'jarvis') 'à l''heure : UN embed dans le salon principal, une seule fois par jour'
    $m = $script:Messages[0].embed
    Verifier ($m.titre -match 'Briefing du matin' -and $m.description -match '^(Bonjour|Bonsoir) monsieur, voici votre briefing du ' -and (Champ $m 'Météo').valeur -match 'non configurée' -and (Champ $m 'Site') -and (Champ $m 'Quiz') -and (Champ $m 'ches') -and (Champ $m 'Veille')) 'embed du matin : salutation, météo (source non configurée), site, quiz, e-mails, abonnés, chiffre d''affaires, tâches, veille'
    Verifier ((Champ $m 'Météo').valeur -notmatch '\d') 'météo non configurée : aucun chiffre inventé'
} else { Write-Host '  (test horaire sauté : juste après minuit)' }
Fixer 'briefing_actif' 'non'; $script:DiscordPumpActif = $false
$mt = Get-MeteoBriefing; Verifier (-not $mt.dispo -and $mt.texte -match 'meteo_latitude') 'météo : seulement si meteo_latitude / meteo_longitude sont dans config.json (Open-Meteo, gratuit, sans clé)'

Write-Host '7) Commande briefing-test et notifier --embed'
$js = Get-Content (Join-Path $Root 'jarvis.ps1') -Raw -Encoding UTF8; $nt = Get-Content (Join-Path $Root 'pont-discord\notifier.py') -Raw -Encoding UTF8
Verifier ($js -match "'briefing-test'" -and $js -match 'Invoke-BriefingTest' -and $js -match 'lib\\saas\.ps1') 'jarvis.ps1 briefing-test existe et charge lib\saas.ps1'
Verifier ($nt -match '--embed' -and $nt -match 'allowed_mentions' -and $nt -match 'def embed_discord') 'notifier.py sait poster un embed (sans mention)'
$tmp = Join-Path $TR 'emb.json'; [IO.File]::WriteAllText($tmp, ((New-EmbedSaas (Get-SaasDonnees)) | ConvertTo-Json -Depth 6), [Text.UTF8Encoding]::new($false))
$pyf = Join-Path $TR 'emb.py'
[IO.File]::WriteAllText($pyf, "import sys, json`nsys.path.insert(0, r'$Root\pont-discord')`nimport notifier`ne = notifier.embed_discord(r'$tmp')`nprint(len(e['fields']), ord(e['title'][0]) > 0, e['color'], 'footer' in e)`n", [Text.UTF8Encoding]::new($false))
$py = (& python -I $pyf 2>&1 | Out-String).Trim()
Verifier ($py -match '^\d+ ' -and $py -match 'True$') "l'embed de Jarvis est converti au format de l'API Discord ($py)"

Write-Host ''
Remove-Item $TR -Recurse -Force -ErrorAction SilentlyContinue
if ($echecs) { Write-Host "ÉCHEC : $echecs vérification(s) en échec." -ForegroundColor Red; exit 1 }
Write-Host 'TOUT EST VERT.'
