# Test des SOURCES (RSS, Alpha Vantage), de la PRIORITÉ des ressources et des « 5 à surveiller » — 100 % SIMULÉ :
# aucun vrai appel réseau (les deux points réseau sont remplacés par des bouchons), aucun appel à Ollama, aucun son, aucune fenêtre, aucune vraie touche.
# La clé Alpha Vantage de ce test est FACTICE ; on vérifie qu'elle n'apparaît jamais dans une sortie, un journal ou un fichier. Code de sortie 0 = réussi.
$ErrorActionPreference = 'Stop'
$env:JARVIS_TEST = '1'      # TEST SILENCIEUX : aucun son, aucune fenêtre, aucun micro, aucune touche, aucune action réelle (voir lib\journal.ps1)
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $Root 'lib\journal.ps1')
$TR = Join-Path $env:TEMP ('jarvis-test-' + [guid]::NewGuid().ToString('N').Substring(0, 8)); New-Item -ItemType Directory $TR, "$TR\memoire", "$TR\logs" | Out-Null; $script:JarvisRoot = $TR
"# To-do de Liam" | Set-Content "$TR\memoire\todo.md" -Encoding UTF8; '# Notes' | Set-Content "$TR\memoire\notes.md" -Encoding UTF8; '# R' | Set-Content "$TR\memoire\resume.md" -Encoding UTF8
$Config = Get-Content (Get-ConfigPath) -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($l in 'voix', 'business', 'permissions', 'actions', 'coffre', 'entrees', 'ecrans', 'tableau', 'visage', 'sons', 'raccourcis', 'cerveau', 'cerveau-local', 'veille', 'memoire', 'rapide', 'discretion', 'modejeu', 'marche', 'priorite', 'matin', 'boucle') { . (Join-Path $Root "lib\$l.ps1") }
foreach ($f in (Get-ChildItem (Join-Path $Root 'lib\sources') -Filter '*.ps1' | Where-Object { $_.Name -notlike '_*' })) { . $f.FullName }
$script:JarvisRoot = $TR
$echecs = 0
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }
function Premier($plan) { if ($plan -and @($plan.actions).Count) { $plan.actions[0] } else { $null } }
$CLE = 'TESTKEY-0123456789abcdef'; $env:ALPHAVANTAGE_KEY = $CLE

$script:Dits = @(); $script:AppelsGetPlan = 0; $script:AppelsLlm = 0; $script:LlmReponse = ''
function Parler([string]$Texte, $Langue) { if ($script:Actif -ne $false -and $script:ModeJeu -ne $true) { $script:Dits += $Texte }; Add-Conv 'jarvis' $Texte }
function Get-Plan([string]$o) { $script:AppelsGetPlan++; $script:VoieCerveau = 'claude'; [pscustomobject]@{ dit = 'Réponse du cerveau.'; langue = 'fr'; actions = @() } }
function Invoke-LlmTexte([string]$systeme, [string]$utilisateur, [int]$timeoutSec = 120, [bool]$complexe = $true, [bool]$annoncer = $false) { $script:AppelsLlm++; $script:LlmReponse }
$script:Actif = $true; $script:ModeJeu = $false
# --- les SEULS points réseau sont remplacés : tout appel inattendu échouerait ---
$script:ReseauRss = 0; $script:XmlRss = $null; $script:ErreurRss = $null
function Get-FluxRssXml([string]$url) { $script:ReseauRss++; if ($script:ErreurRss) { throw $script:ErreurRss }; $x = New-Object Xml.XmlDocument; $x.LoadXml($script:XmlRss); $x }
$script:ReseauAv = 0; $script:ReponseAv = $null; $script:ErreurAv = $null; $script:DernierAvFonction = ''
function Get-AvReponse([string]$fonction, [hashtable]$params) { $script:ReseauAv++; $script:DernierAvFonction = $fonction; if ($script:ErreurAv) { throw $script:ErreurAv }; & $script:ReponseAv $params }
function Invoke-WebRequest { throw 'APPEL RÉSEAU INTERDIT EN TEST' }
function Invoke-RestMethod { throw 'APPEL RÉSEAU INTERDIT EN TEST' }
function Fabriquer-Rss([string[]]$titres, [datetime]$date = (Get-Date)) {
    $items = ($titres | ForEach-Object { "<item><title>$_</title><link>https://exemple.test/x</link><description>Texte intégral de l'article qui ne doit JAMAIS être recopié</description><pubDate>$($date.ToUniversalTime().ToString('r'))</pubDate></item>" }) -join ''
    "<?xml version='1.0'?><rss version='2.0'><channel><title>T</title><link>https://exemple.test</link><description>d</description>$items</channel></rss>"
}
$maintenant = Get-Date

Write-Host '1) config.json : sources validées, marche_actif reste false'
$reel = Get-Content (Join-Path $Root 'config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
Verifier ((@($reel.sources_validees) -join ',') -eq 'rss,alphavantage' -and $reel.marche_actif -eq $false) 'sources_validees = ["rss", "alphavantage"] ; marche_actif = false'
Verifier ($reel.alphavantage_plafond_jour -eq 20 -and "$($reel.priorite_ressources)" -eq 'normal') 'plafond Alpha Vantage = 20 par jour ; priorité = normal'
Verifier (@($reel.rss_flux).Count -eq 1 -and $reel.rss_flux[0].nom -eq 'BCE' -and $reel.rss_flux[0].url -eq 'https://www.ecb.europa.eu/rss/press.xml') 'un seul flux RSS configuré : BCE (seul flux officiel dont l''adresse a été vérifiée)'
Verifier ("$($reel.alphavantage_symboles.Thales)" -eq '' -and "$($reel.alphavantage_symboles.'Société Générale')" -eq '') 'symboles Alpha Vantage NON devinés : à renseigner après jarvis.ps1 avtest'
$Config.marche_actif = $false; $r = Invoke-CycleVeilleFond @{}
Verifier (-not $r.fait -and $script:ReseauRss -eq 0 -and $script:ReseauAv -eq 0) 'marche_actif = false : le cycle ne lit AUCUNE source (0 appel RSS, 0 appel Alpha Vantage)'
Verifier ((Get-DonneesMarche).raison -match '^Marché désactivé : mets marche_actif à true') 'le panneau Marché dit : « Marché désactivé : mets marche_actif à true »'

Write-Host '2) RSS : flux valide, cache 15 min, flux vide, erreurs, sans article copié'
$Config.rss_flux = @([pscustomobject]@{ nom = 'BCE'; url = 'https://www.ecb.europa.eu/rss/press.xml' })
$script:XmlRss = Fabriquer-Rss @('Décision de politique monétaire', 'Discours de la présidente') (Get-Date).AddHours(-3)
$r = Get-ActusRss $maintenant.AddHours(-48) $maintenant
Verifier ($r.dispo -and $r.items.Count -eq 2 -and $r.items[0].source -eq 'BCE' -and $script:ReseauRss -eq 1) "flux valide : $($r.items.Count) titres, source « BCE », 1 appel"
Verifier ($r.items[0].resume -eq '' -and ($r.items | ForEach-Object { $_.titre }) -notmatch 'Texte intégral') 'titres + source + date seulement : le texte de l''article n''est jamais gardé'
Verifier ((ConvertTo-DateMarche $r.items[0].date) -gt $maintenant.AddHours(-4)) 'la date de publication est conservée'
$r = Get-ActusRss $maintenant.AddHours(-48) $maintenant.AddMinutes(10)
Verifier ($r.dispo -and $r.items.Count -eq 2 -and $script:ReseauRss -eq 1) 'cache : un 2e passage 10 min plus tard ne contacte pas le flux (toujours 1 appel)'
$Config | Add-Member -NotePropertyName rss_minutes -NotePropertyValue 1 -Force
Verifier ((Get-RssMinutes) -eq 15) 'rss_minutes réglé à 1 : plancher de 15 minutes imposé'
$r = Get-ActusRss $maintenant.AddHours(-48) $maintenant.AddMinutes(16)
Verifier ($script:ReseauRss -eq 2) 'après 16 min : le flux est relu (2 appels)'
Verifier ($script:RssUserAgent -match '^Jarvis' -and $script:RssUserAgent -match 'lecture seule' -and $script:RssUserAgent -match '15 min') 'User-Agent honnête : se présente comme Jarvis, usage personnel, lecture seule, 1 appel / 15 min'
Remove-Item "$TR\memoire\veille\rss-cache.json"; $script:ReseauRss = 0
$script:XmlRss = Fabriquer-Rss @()
$r = Get-ActusRss $maintenant.AddHours(-48) $maintenant
Verifier ($r.dispo -and $r.items.Count -eq 0 -and $r.avertissements.Count -eq 0) 'flux vide (valide, sans article) : disponible, zéro titre, aucune alerte'
Remove-Item "$TR\memoire\veille\rss-cache.json"
$script:ErreurRss = 'délai dépassé'; $r = Get-ActusRss $maintenant.AddHours(-48) $maintenant
Verifier (-not $r.dispo -and $r.raison -eq 'BCE : indisponible (délai dépassé)') "erreur réseau : « $($r.raison) »"
$n = $script:ReseauRss; $r = Get-ActusRss $maintenant.AddHours(-48) $maintenant.AddMinutes(5)
Verifier ($script:ReseauRss -eq $n -and -not $r.dispo) 'après une erreur, pas de nouvel essai avant 15 min (la source n''est pas martelée)'
$script:ErreurRss = $null; $script:XmlRss = "<html><body>pas un flux</body></html>"; Remove-Item "$TR\memoire\veille\rss-cache.json"
$r = Get-ActusRss $maintenant.AddHours(-48) $maintenant
Verifier (-not $r.dispo -and $r.raison -match 'pas un flux') "page HTML au lieu d'un flux : « $($r.raison) »"
$script:XmlRss = Fabriquer-Rss @('Titre 1') (Get-Date).AddHours(-2); Remove-Item "$TR\memoire\veille\rss-cache.json"; [void](Get-ActusRss $maintenant.AddHours(-48) $maintenant)
$script:ErreurRss = 'timed out'; $r = Get-ActusRss $maintenant.AddHours(-48) $maintenant.AddMinutes(20)
Verifier ($r.dispo -and $r.items.Count -eq 1 -and $r.avertissements[0] -match 'BCE : indisponible \(délai dépassé\)') 'flux en panne mais déjà lu : anciens titres gardés + « indisponible (cause) »'
$script:ErreurRss = $null
$Config.rss_flux = @([pscustomobject]@{ nom = 'X'; url = 'http://exemple.test/rss' }); $r = Get-ActusRss $maintenant.AddHours(-48) $maintenant
Verifier (-not $r.dispo -and $r.raison -match 'aucun flux') 'adresse http (non https) refusée'
$Config.rss_flux = @([pscustomobject]@{ nom = 'BCE'; url = 'https://www.ecb.europa.eu/rss/press.xml' })

Write-Host '3) Alpha Vantage : clé, symboles, heures de bourse, intervalle, plafond'
Remove-Item Env:ALPHAVANTAGE_KEY; $r = Get-CoursAlphaVantage @(@{ nom = 'Thales'; symbole = '' })
Verifier (-not $r.dispo -and $r.raison -match 'ALPHAVANTAGE_KEY absente' -and $script:ReseauAv -eq 0) 'clé absente : « clé ALPHAVANTAGE_KEY absente dans .env », aucun appel'
$env:ALPHAVANTAGE_KEY = $CLE
$vals = @(@{ nom = 'Thales'; symbole = 'HO' }, @{ nom = 'Société Générale'; symbole = 'GLE' })
$r = Get-CoursAlphaVantage $vals
Verifier (-not $r.dispo -and $r.raison -match 'symbole Alpha Vantage non configuré pour Thales' -and $script:ReseauAv -eq 0) 'symboles non configurés : message clair, aucun appel (aucun symbole n''est deviné)'
$Config | Add-Member -NotePropertyName alphavantage_symboles -NotePropertyValue ([pscustomobject]@{ 'Thales' = 'HO.TEST'; 'Société Générale' = 'GLE.TEST' }) -Force
$Config | Add-Member -NotePropertyName alphavantage_plafond_jour -NotePropertyValue 20 -Force
Verifier ((Get-AvPlafond) -eq 20) 'plafond par défaut : 20 requêtes par jour'
Verifier ((Get-AvIntervalleSecondes 2 20) -eq 3060 -and (Get-AvIntervalleSecondes 1 20) -eq 1530 -and (Get-AvIntervalleSecondes 5 20) -eq 7650 -and (Get-AvIntervalleSecondes 1 500) -eq 900) 'intervalle calculé : 2 valeurs / 20 par jour -> 51 min ; 1 valeur -> 25 min ; 5 valeurs -> 2 h 07 ; plancher 15 min'
Verifier ((8.5 * 3600 / (Get-AvIntervalleSecondes 2 20)) * 2 -le 21) 'avec 2 valeurs : au plus 10 passes x 2 = 20 requêtes sur la séance (jamais plus que le plafond)'
$mer = [datetime]'2026-10-14'   # mercredi
Verifier ((Test-HeuresBoursePar $mer.AddHours(10)) -and -not (Test-HeuresBoursePar $mer.AddHours(8).AddMinutes(59)) -and (Test-HeuresBoursePar $mer.AddHours(9)) -and (Test-HeuresBoursePar $mer.AddHours(17).AddMinutes(29)) -and -not (Test-HeuresBoursePar $mer.AddHours(17).AddMinutes(30))) 'heures de bourse de Paris : 9h00 inclus, 17h30 exclu'
Verifier (-not (Test-HeuresBoursePar ([datetime]'2026-10-17 11:00')) -and -not (Test-HeuresBoursePar ([datetime]'2026-10-18 11:00'))) 'samedi et dimanche : pas de lecture'
$script:ReponseAv = { param($p) $px = if ($p.symbol -like 'HO*') { '150.20' } else { '40.00' }; [pscustomobject]@{ 'Global Quote' = [pscustomobject]@{ '01. symbol' = $p.symbol; '05. price' = $px; '07. latest trading day' = $script:JourBourse; '10. change percent' = '3.4000%' } } }
$script:JourBourse = '2026-10-14'
Remove-Item "$TR\memoire\alphavantage-quota.json" -ErrorAction SilentlyContinue
$script:AvHeureParis = [datetime]'2026-10-17 11:00'; $script:AvMaintenant = [datetime]'2026-10-17 11:00'
$r = Get-CoursAlphaVantage $vals
Verifier ($r.dispo -and $r.cours.Count -eq 0 -and $script:ReseauAv -eq 0) 'samedi : aucun appel (0 requête)'
$script:AvHeureParis = [datetime]'2026-10-14 08:30'; $script:AvMaintenant = $script:AvHeureParis
$r = Get-CoursAlphaVantage $vals; Verifier ($script:ReseauAv -eq 0) 'mercredi avant l''ouverture : aucun appel'
$script:AvHeureParis = [datetime]'2026-10-14 10:00'; $script:AvMaintenant = $script:AvHeureParis
$r = Get-CoursAlphaVantage $vals
Verifier ($script:ReseauAv -eq 2 -and $script:DernierAvFonction -eq 'GLOBAL_QUOTE' -and $r.cours.Count -eq 2) 'séance : une requête GLOBAL_QUOTE par valeur (2 appels), 2 cours'
$c = $r.cours | Where-Object { $_.nom -eq 'Thales' }
Verifier ($c.prix -eq 150.2 -and $c.variation_pct -eq 3.4 -and $c.source -eq 'Alpha Vantage' -and (ConvertTo-DateMarche $c.date).ToString('yyyy-MM-dd HH:mm') -eq '2026-10-14 17:30') 'cours lu : 150,2 ; +3,4 % ; daté du dernier jour de bourse'
Verifier ((Read-JsonMemoire 'alphavantage-quota.json').n -eq 2) 'compteur du jour : 2/20 (memoire\alphavantage-quota.json)'
$script:AvHeureParis = [datetime]'2026-10-14 10:10'; $script:AvMaintenant = $script:AvHeureParis
$r = Get-CoursAlphaVantage $vals
Verifier ($script:ReseauAv -eq 2 -and $r.cours.Count -eq 2) '10 min plus tard (intervalle 51 min) : aucun nouvel appel, derniers cours renvoyés'
$script:AvHeureParis = [datetime]'2026-10-14 10:55'; $script:AvMaintenant = $script:AvHeureParis
$r = Get-CoursAlphaVantage $vals; Verifier ($script:ReseauAv -eq 4 -and (Read-JsonMemoire 'alphavantage-quota.json').n -eq 4) '55 min plus tard : nouvelle passe (4 appels, 4/20)'
# plafond atteint
$Config.alphavantage_plafond_jour = 4
Remove-Item "$TR\memoire\alphavantage-quota.json"; $script:ReseauAv = 0
$script:AvHeureParis = [datetime]'2026-10-14 10:00'; $script:AvMaintenant = $script:AvHeureParis; [void](Get-CoursAlphaVantage $vals)      # 2 appels
$script:AvHeureParis = [datetime]'2026-10-14 12:00'; $script:AvMaintenant = $script:AvHeureParis; [void](Get-CoursAlphaVantage $vals)
Verifier ($script:ReseauAv -eq 2) 'plafond 4, 2 valeurs : intervalle 4 h 15 -> pas de 2e passe à midi'
$script:AvHeureParis = [datetime]'2026-10-14 14:30'; $script:AvMaintenant = $script:AvHeureParis; $r = Get-CoursAlphaVantage $vals          # 2e passe : 4/4
Verifier ($script:ReseauAv -eq 4 -and (Read-JsonMemoire 'alphavantage-quota.json').n -eq 4) 'plafond 4 : deux passes, 4 appels exactement (4/4)'
Verifier ($r.avertissements -contains 'Alpha Vantage : quota du jour atteint (4/4), reprise demain') "message clair : « $($r.avertissements -join ' ; ') »"
$script:AvHeureParis = [datetime]'2026-10-14 15:00'; $script:AvMaintenant = $script:AvHeureParis; $r = Get-CoursAlphaVantage $vals
Verifier ($script:ReseauAv -eq 4 -and $r.cours.Count -ge 1 -and ($r.avertissements -join '') -match 'quota du jour atteint') 'plafond atteint : plus aucun appel, derniers cours gardés, message toujours affiché'
$Config.rss_flux = @(); $Config.sources_validees = @('alphavantage'); $Config.marche_actif = $true
$script:AvHeureParis = [datetime]'2026-10-14 15:30'; $script:AvMaintenant = $script:AvHeureParis
$r1 = Invoke-CycleVeilleFond @{}
Verifier ($r1.fait -and @($r1.erreurs | Where-Object { $_ -match 'quota du jour atteint' }).Count -eq 1) 'dans le relevé : « quota du jour atteint » apparaît une fois (panneau)'
$a1 = @(Select-ErreursNonRepetees $r1.erreurs); $a2 = @(Select-ErreursNonRepetees $r1.erreurs)
Verifier ($a1.Count -eq 1 -and $a2.Count -eq 0) 'sans répéter l''alerte : journalisée une seule fois tant qu''elle ne change pas'
$d = Get-DonneesMarche; Verifier ($d.dispo -and ($d.manque -join ' ') -match 'quota du jour atteint') 'le panneau Marché affiche « quota du jour atteint »'
$script:AvHeureParis = [datetime]'2026-10-15 10:00'; $script:AvMaintenant = $script:AvHeureParis; $script:JourBourse = '2026-10-15'; $n0 = $script:ReseauAv
[void](Get-CoursAlphaVantage $vals); Verifier ($script:ReseauAv -gt $n0 -and (Read-JsonMemoire 'alphavantage-quota.json').n -le 2) 'le lendemain : compteur remis à zéro, lecture reprise'
# réponses anormales
$Config.alphavantage_plafond_jour = 20; $script:AvHeureParis = [datetime]'2026-10-16 10:00'; $script:AvMaintenant = $script:AvHeureParis
$script:ReponseAv = { param($p) [pscustomobject]@{ 'Information' = 'Our standard API rate limit is 25 requests per day.' } }
$r = Get-CoursAlphaVantage $vals
Verifier ((($r.avertissements -join ' ') -match 'limite signalée par le service') -and (Read-JsonMemoire 'alphavantage-quota.json').n -eq 20) 'le service signale sa limite : on s''arrête et le compteur passe au plafond'
$script:AvHeureParis = [datetime]'2026-10-17 10:00'; $script:AvMaintenant = [datetime]'2026-10-19 10:00'
$script:AvHeureParis = [datetime]'2026-10-19 10:00'
$script:ReponseAv = { param($p) [pscustomobject]@{ 'Error Message' = 'Invalid API call.' } }; $r = Get-CoursAlphaVantage $vals
Verifier (($r.avertissements -join ' ') -match 'symbole « HO.TEST » refusé') 'symbole refusé : message clair'
$script:AvHeureParis = [datetime]'2026-10-20 10:00'; $script:AvMaintenant = $script:AvHeureParis
$script:ReponseAv = { param($p) [pscustomobject]@{ 'Global Quote' = [pscustomobject]@{} } }; $r = Get-CoursAlphaVantage $vals
Verifier (($r.avertissements -join ' ') -match 'aucune cotation pour Thales') 'cotation vide : « aucune cotation … symbole inconnu ou non couvert »'
$script:AvHeureParis = [datetime]'2026-10-21 10:00'; $script:AvMaintenant = $script:AvHeureParis; $script:ErreurAv = 'The operation has timed out'
$r = Get-CoursAlphaVantage $vals; Verifier (($r.avertissements -join ' ') -match 'indisponible \(délai dépassé\)') 'erreur réseau : « indisponible (délai dépassé) »'
$script:ErreurAv = $null
# alerte « aujourd'hui » : un cours d'hier n'en déclenche pas
$script:ReponseAv = { param($p) [pscustomobject]@{ 'Global Quote' = [pscustomobject]@{ '05. price' = '100.00'; '07. latest trading day' = $script:JourBourse; '10. change percent' = '5.0000%' } } }
$script:JourBourse = (Get-Date).AddDays(-1).ToString('yyyy-MM-dd'); $script:AvHeureParis = [datetime]'2026-10-22 10:00'; $script:AvMaintenant = $script:AvHeureParis
$Config.sources_validees = @('alphavantage'); Remove-Item "$TR\memoire\veille\releve-*.json" -ErrorAction SilentlyContinue
[void](Invoke-CycleVeilleFond @{}); $script:AlertesCache = $null
$al = @(Test-AlertesMarche (Read-DernierReleve) (Get-Date))
Verifier ($al.Count -eq 0) 'variation de +5 % datée d''hier (dernier jour de bourse) : aucune alerte « aujourd''hui »'
$script:AvHeureParis = $null; $script:AvMaintenant = $null

Write-Host '4) Les deux sources ensemble, et la clé ne fuit nulle part'
$Config.rss_flux = @([pscustomobject]@{ nom = 'BCE'; url = 'https://www.ecb.europa.eu/rss/press.xml' }); $Config.sources_validees = @('rss', 'alphavantage'); $Config.marche_actif = $true
$script:XmlRss = Fabriquer-Rss @('Communiqué de la BCE') (Get-Date).AddHours(-1); Remove-Item "$TR\memoire\veille\rss-cache.json" -ErrorAction SilentlyContinue
$script:JourBourse = (Get-Date).ToString('yyyy-MM-dd'); $script:ReponseAv = { param($p) [pscustomobject]@{ 'Global Quote' = [pscustomobject]@{ '05. price' = '150.20'; '07. latest trading day' = $script:JourBourse; '10. change percent' = '1.0000%' } } }
$script:AvHeureParis = [datetime]'2026-10-23 10:00'; $script:AvMaintenant = $script:AvHeureParis
$r = Invoke-CycleVeilleFond @{}
$rel = Read-DernierReleve
Verifier ($r.fait -and $rel.cours.Count -ge 1 -and $rel.actus.Count -eq 1 -and $rel.actus[0].source -eq 'BCE') 'un relevé avec les cours (Alpha Vantage) ET les titres (RSS)'
$tout = (Get-ChildItem $TR -Recurse -File | ForEach-Object { Get-Content $_.FullName -Raw -ErrorAction SilentlyContinue }) -join "`n"
Verifier ($tout -notmatch [regex]::Escape($CLE)) 'la clé ne figure ni dans le journal, ni dans la mémoire, ni dans les relevés, ni dans le compteur'
$av = Get-Content (Join-Path $Root 'lib\sources\alphavantage.ps1') -Raw -Encoding UTF8
Verifier ($av -notmatch 'Write-Host.*\$cle|Write-Journal[^\n]*Get-AvCle' ) 'le module n''écrit jamais la clé'
$script:AvHeureParis = $null; $script:AvMaintenant = $null
$t = Invoke-AvTest; Verifier ($t -match 'aucun appel réel') 'jarvis.ps1 avtest en mode test : aucun appel réel'

Write-Host '5) Priorité des ressources'
foreach ($c in @(@('normale', 'normal'), @('normal', 'normal'), @('élevée', 'eleve'), @('elevee', 'eleve'), @('haute', 'eleve'), @('maximum', 'max'), @('max', 'max'), @('bidule', $null))) { Verifier ((ConvertTo-NiveauPriorite $c[0]) -eq $c[1]) "niveau « $($c[0]) » -> $($c[1])" }
$Config | Add-Member -NotePropertyName priorite_ressources -NotePropertyValue 'normal' -Force
Verifier ((Get-PrioriteDemandee) -eq 'normal') 'défaut : normal'
foreach ($c in @(@('priorité normale', 'normale'), @('priorité élevée', 'elevee'), @('priorité maximum', 'maximum'), @('mets la priorité en maximum', 'maximum'), @('Jarvis, passe en priorité élevée', 'elevee'))) {
    $a = Premier (Get-PlanRapide $c[0]); Verifier ($a -and $a.type -eq 'priorite' -and $a.niveau -eq $c[1]) "« $($c[0]) » -> priorite / $($c[1])" }
$script:OllamaAppels = @(); function Invoke-OllamaPriorite([string]$eff, [string]$ancien) { $script:OllamaAppels += "$ancien>$eff" }
function Get-ModelesOllama { @(@{ nom = 'qwen2.5:7b'; octets = 4.7GB }, @{ nom = 'qwen2.5:14b'; octets = 9GB }, @{ nom = 'qwen2.5:32b'; octets = 20GB }, @{ nom = 'nomic-embed-text'; octets = 0.3GB }) }
function Get-RamGo { 32 }
$script:PrioriteAppliquee = ''; $script:PrioriteProchain = [datetime]::MinValue; Update-Priorite
Verifier ($script:PrioriteAppliquee -eq 'normal' -and (Get-OllamaConfig).keep -eq '30m' -and (Get-OllamaConfig).modele -eq 'qwen2.5:7b') 'normal : modèle configuré, gardé 30 min (keep_alive)'
$script:Dits = @(); Invoke-Ordre 'priorité élevée'
Verifier ($script:Dits[-1] -match '^Priorité élevée, monsieur\. Elle redescend toute seule en mode jeu et en sourdine\.$' -and (Read-JsonMemoire 'priorite.json').niveau -eq 'eleve') "commande vocale : « $($script:Dits[-1]) » (mémorisée dans memoire\priorite.json)"
Verifier ("$($Config.priorite_ressources)" -eq 'normal') 'config.json (copie) inchangé'
$script:PrioriteProchain = [datetime]::MinValue; Update-Priorite
Verifier ($script:PrioriteAppliquee -eq 'eleve' -and $script:OllamaAppels[-1] -eq 'normal>eleve' -and (Get-OllamaConfig).keep -eq -1 -and (Get-OllamaConfig).modele -eq 'qwen2.5:7b') 'élevée : modèle configuré GARDÉ CHAUD (keep_alive illimité)'
Verifier ((Get-Content "$TR\memoire\priorite-effective.txt" -Raw).Trim() -eq 'eleve' -and (Get-VeilleMinutesEffectif) -eq 5) 'veille de fond plus fréquente : 15 min -> 5 min'
Invoke-Ordre 'priorité maximum'; $script:ModelePlusGrosCache = $null; $script:PrioriteProchain = [datetime]::MinValue; Update-Priorite
Verifier ($script:PrioriteAppliquee -eq 'max' -and (Get-OllamaConfig).modele -eq 'qwen2.5:14b' -and (Get-VeilleMinutesEffectif) -eq 3) 'maximum (32 Go de RAM) : plus gros modèle INSTALLÉ qui tient (14b, 9 Go ; le 32b = 20 Go dépasse 60 % de la RAM) ; veille 3 min'
Verifier ((Select-ModelePlusGros @(@{ nom = 'a:70b'; octets = 40GB }, @{ nom = 'b-embed'; octets = 1GB }) 16 'qwen2.5:7b') -eq 'qwen2.5:7b') 'aucun modèle installé ne tient : on garde le modèle configuré (embeddings ignorés)'
Verifier ((Select-ModelePlusGros @(@{ nom = 'a:7b'; octets = 4GB }, @{ nom = 'b:14b'; octets = 9GB }) 16 'x') -eq 'b:14b') 'sélection pure : 9 Go tient dans 60 % de 16 Go'
function Get-ModelesOllama { @(@{ nom = 'qwen2.5:7b'; octets = 4.7GB }, @{ nom = 'qwen2.5:14b'; octets = 9GB }) }; function Get-RamGo { 64 }; $script:ModelePlusGrosCache = $null
$rap = (Get-RapportPriorite) -join "`n"
Verifier ($rap -match 'qwen2.5:14b' -and $rap -match 'Je ne télécharge rien sans votre accord') 'rapport : modèle détecté + suggestion plus gros, sans rien télécharger'
$pr = Get-Content (Join-Path $Root 'lib\priorite.ps1') -Raw -Encoding UTF8
Verifier ($pr -notmatch '/api/pull|ollama pull|Start-Process|ollama serve') 'le code de priorité ne télécharge rien et ne lance pas Ollama'
$script:ModeJeu = $true; $script:PrioriteProchain = [datetime]::MinValue; Update-Priorite
Verifier ($script:PrioriteAppliquee -eq 'normal' -and $script:OllamaAppels[-1] -eq 'max>normal' -and (Get-OllamaConfig).keep -eq '30m' -and (Get-OllamaConfig).modele -eq 'qwen2.5:7b' -and (Get-VeilleMinutesEffectif) -eq 15) 'mode jeu : redescend à normal (modèle déchargé, modèle configuré, veille au rythme normal)'
$script:ModeJeu = $false; $script:Actif = $false; $script:PrioriteProchain = [datetime]::MinValue; Update-Priorite; $n = $script:OllamaAppels.Count
Verifier ($script:PrioriteAppliquee -eq 'normal' -and (Get-PrioriteDemandee) -eq 'max') 'sourdine : reste à normal, la demande « maximum » est conservée'
$script:Actif = $true; $script:PrioriteProchain = [datetime]::MinValue; Update-Priorite
Verifier ($script:PrioriteAppliquee -eq 'max' -and $script:OllamaAppels[-1] -eq 'normal>max') 'à la réactivation : remonte à maximum'
Invoke-Ordre 'priorité normale'; $script:PrioriteProchain = [datetime]::MinValue; Update-Priorite; Verifier ($script:PrioriteAppliquee -eq 'normal' -and $script:OllamaAppels[-1] -eq 'max>normal') '« priorité normale » : retour à normal'
$vf = Get-Content (Join-Path $Root 'veille-fond.ps1') -Raw -Encoding UTF8
Verifier ($vf -match 'Get-VeilleMinutesEffectif' -and $vf -match 'Select-ErreursNonRepetees') 'la veille de fond suit la priorité effective et ne répète pas ses messages'

Write-Host '6) Aucune source : « source non branchée »'
$Config.sources_validees = @(); $Config.marche_actif = $true
$s = Get-Surveiller; Verifier (-not $s.dispo -and $s.raison -match 'non branchée') "5 à surveiller sans source : « $($s.raison) »"
$script:Dits = @(); Invoke-Ordre "quels sont les 5 à regarder aujourd'hui ?"
Verifier ($script:Dits[-1] -match '^Source non branchée' -and $script:AppelsGetPlan -eq 0) "réponse vocale : « $($script:Dits[-1]) »"
Update-Surveiller; Verifier ((Get-DonneesTableau).ContainsKey('surveiller') -and -not (Get-DonneesTableau).surveiller.dispo) 'le tableau de bord transporte « source non branchée »'

Write-Host '7) Les 5 à surveiller aujourd''hui : classement objectif'
$Config.sources_validees = @('factice'); $Config.marche_actif = $true
Remove-Item "$TR\memoire\veille\releve-*.json" -ErrorAction SilentlyContinue
Save-ValeursSuivies @(@{ nom = 'Alpha'; symbole = 'AA' }, @{ nom = 'Bravo'; symbole = 'BB' }, @{ nom = 'Charlie'; symbole = 'CC' }, @{ nom = 'Delta'; symbole = 'DD' }, @{ nom = 'Echo'; symbole = 'EE' }, @{ nom = 'Foxtrot'; symbole = 'FF' }, @{ nom = 'Golf'; symbole = 'GG' })
$now = Get-Date; $iso = { param($h) $now.AddHours($h).ToString('o') }
$cours = @(foreach ($c in @(@('Alpha', 'AA', 100, 4.2), @('Bravo', 'BB', 50, -2.5), @('Charlie', 'CC', 20, 0.4), @('Delta', 'DD', 30, 0.3), @('Echo', 'EE', 100, 0.2), @('Foxtrot', 'FF', 10, 0.1))) { [ordered]@{ nom = $c[0]; symbole = $c[1]; prix = $c[2]; devise = 'EUR'; variation_pct = $c[3]; date = (& $iso 0); source = 'Factice' } })
$actus = @(
    [ordered]@{ titre = 'Charlie publie ses résultats'; resume = ''; date = (& $iso 30); source = 'Factice'; valeur = 'Charlie' }
    [ordered]@{ titre = 'Charlie : assemblée générale'; resume = ''; date = (& $iso 60); source = 'Factice'; valeur = 'Charlie' }
    [ordered]@{ titre = 'Charlie signe un contrat'; resume = ''; date = (& $iso -2); source = 'Factice'; valeur = 'Charlie' }
    [ordered]@{ titre = 'Delta lance un produit'; resume = ''; date = (& $iso -1); source = 'Factice'; valeur = 'Delta' }
    [ordered]@{ titre = 'Delta recrute'; resume = ''; date = (& $iso -3); source = 'Factice'; valeur = 'Delta' }
    [ordered]@{ titre = 'Delta ouvre un site'; resume = ''; date = (& $iso -5); source = 'Factice'; valeur = 'Delta' })
[void](Save-Releve $cours $actus @() @('factice'))
Save-Positions @([pscustomobject]@{ nom = 'Echo'; symbole = 'EE'; prix = 110; seuil = 98; sens = 'bas'; date = $now.ToString('o'); atteint = $false })
$s = Get-Surveiller $now
Verifier ($s.dispo -and $s.items.Count -eq 5) "5 valeurs retenues sur 7 suivies"
Verifier ((($s.items | ForEach-Object { $_.nom }) -join ',') -eq 'Alpha,Bravo,Charlie,Delta,Echo') "classement : $(($s.items | ForEach-Object { $_.nom }) -join ' > ') (variation du jour, puis publications à venir, puis actualités, puis proximité du seuil)"
Verifier (-not ($s.items | Where-Object { $_.nom -in 'Foxtrot', 'Golf' })) 'Foxtrot (rien de notable) et Golf (aucun cours) ne sont pas retenues'
$i = $s.items
Verifier ($i[0].raison -match 'variation du jour : en hausse de 4,2 %' -and $i[0].raison -match 'source Factice') "raison n°1 : $($i[0].raison)"
Verifier ($i[2].raison -match '2 publication\(s\) à venir' -and $i[2].raison -match '1 titre\(s\) d''actualité en 24 h') 'Charlie : publications à venir comptées avant l''actualité récente'
Verifier ($i[3].raison -match '3 titre\(s\) d''actualité en 24 h') 'Delta : volume d''actualités'
Verifier ($i[4].raison -match 'cours proche de votre seuil \(2 %\)' -and ($i[4].negatifs -join ' ') -match 'seuil de 98') 'Echo : proximité de votre seuil (2 %), en point négatif factuel'
Verifier ($i[0].positifs[0] -match '^En hausse de 4,2 % \(source Factice, \d\d/\d\d \d\d:\d\d\)' -and $i[1].negatifs[0] -match '^En baisse de 2,5 %') 'points positifs / négatifs : faits datés et sourcés'
Verifier ((@($i | Where-Object { $_.positifs.Count -eq 0 -or $_.negatifs.Count -eq 0 -or $_.verifier.Count -eq 0 })).Count -eq 0) 'chaque valeur a ses points positifs, négatifs et « à vérifier »'
Verifier (($i[2].verifier -join ' ') -match 'À venir : Charlie publie ses résultats \(Factice, \d\d/\d\d\)' -and ($i[0].verifier -join ' ') -match 'Dates de publication à confirmer sur le site de l''émetteur') 'à vérifier : publications à venir sourcées ; sinon, confirmation du calendrier'
$txt = ($i | ForEach-Object { $_.raison; $_.positifs; $_.negatifs; $_.verifier }) -join ' | '
Verifier ($txt -notmatch '(?i)acheter|vendre|achat|vente|score|\bnote\b|probabilit|prédi|pr[ée]vo|objectif de cours|recommand|opportunit') 'aucun mot de verdict, de score, de probabilité ni de prédiction'
Verifier (-not (Test-SortieConseil $txt) -and -not (Test-SortieConseil (Get-PhraseSurveiller $s))) 'le filtre anti-conseil ne trouve rien (liste ni phrase dite)'
Verifier (-not ($i[0].Keys | Where-Object { $_ -match 'score|note|proba' })) 'aucun champ « note », « score » ou « probabilité » dans les données'
$script:Dits = @(); Invoke-Ordre "quels sont les 5 à regarder aujourd'hui ?"
Verifier ($script:Dits[-1] -match "^Voici ce qui est à regarder aujourd'hui, monsieur, classé sur des critères objectifs" -and $script:Dits[-1] -match '1\. Alpha\.' -and $script:Dits[-1] -match 'Ce n''est ni un verdict ni une prévision') 'réponse vocale avec critères, classement et rappel : ni verdict ni prévision'
foreach ($o in "les 5 à surveiller aujourd'hui", "donne-moi les cinq valeurs à regarder", "quelles sont les 5 à regarder ce matin") { Verifier ((Premier (Get-PlanRapide $o)).type -eq 'surveiller_5') "« $o » reconnu" }
Verifier ($script:AppelsGetPlan -eq 0 -and $script:AppelsLlm -eq 0) 'sans appel au cerveau : classement et phrases calculés localement'
Save-ValeursSuivies @(@{ nom = 'Alpha'; symbole = 'AA' }, @{ nom = 'Bravo'; symbole = 'BB' }); $s = Get-Surveiller $now
Verifier ($s.items.Count -eq 2 -and (Get-PhraseSurveiller $s) -match 'Votre veille ne compte que 2 valeurs') 'veille de 2 valeurs : 2 retenues, dit honnêtement'
Save-ValeursSuivies @(@{ nom = 'Alpha'; symbole = 'AA' }, @{ nom = 'Bravo'; symbole = 'BB' }, @{ nom = 'Charlie'; symbole = 'CC' }, @{ nom = 'Delta'; symbole = 'DD' }, @{ nom = 'Echo'; symbole = 'EE' }, @{ nom = 'Foxtrot'; symbole = 'FF' }, @{ nom = 'Golf'; symbole = 'GG' })
$script:MarcheProchain = [datetime]::MinValue; Update-Marche
Verifier ((Get-DonneesTableau).surveiller.items.Count -eq 5) 'le panneau Marché reçoit les 5 à surveiller (Update-Marche)'

Write-Host '8) Verdict ou probabilité demandés : refus net, puis ce qui est à regarder'
$ref = 'Je ne donne ni verdict ni probabilité, monsieur, mais voici ce qui est à regarder.'
$script:Dits = @(); $script:Dossier = $null; Invoke-Ordre 'quelle est la probabilité que Alpha monte ?'
Verifier ($script:Dits[0] -eq $ref -and $script:Dossier.titre -eq 'Dossier : Alpha') "probabilité sur une valeur : « $($script:Dits[0]) » + dossier"
$script:Dits = @(); Invoke-Ordre "donne-moi un score d'achat pour mes actions"
Verifier ($script:Dits[0] -eq $ref -and $script:Dits[-1] -match '1\. Alpha') 'score demandé : refus, puis les 5 à regarder'
$script:Dits = @(); Invoke-Ordre 'lequel acheter entre mes valeurs ?'
Verifier ($script:Dits[0] -eq $ref -and $script:Dits[-1] -match 'Voici ce qui est à regarder') '« lequel acheter » : même refus'
$script:Dits = @(); Invoke-Ordre 'quelles sont mes chances de gagner avec Bravo en bourse ?'
Verifier ($script:Dits[0] -eq $ref) '« chances de gagner … en bourse » : même refus'
Verifier (-not (Test-DemandeProba 'quel est le score du match') -and -not (Test-DemandeProba 'note que le code est 1234') -and -not (Test-DemandeProba 'quelle est la probabilité qu''il pleuve demain')) 'hors marché : pas d''interception (score du match, note, météo)'
$script:Dits = @(); $script:Dossier = $null; Invoke-Ordre 'dois-je acheter Alpha ?'
Verifier ($script:Dits[0] -eq 'Je ne donne pas de verdict, monsieur, mais voici le dossier.') 'l''ancien refus (« dois-je acheter … ») garde sa phrase et son dossier'
Verifier (-not (Test-SortieConseil ($script:Dits -join ' '))) 'aucune réponse ne contient de conseil'

Remove-Item Env:ALPHAVANTAGE_KEY -ErrorAction SilentlyContinue
Remove-Item $TR -Recurse -Force -ErrorAction SilentlyContinue
if ($echecs) { Write-Host "`nÉCHEC : $echecs vérification(s) en échec." -ForegroundColor Red; exit 1 }
Write-Host "`nRÉUSSI"; exit 0
