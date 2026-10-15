# Test musique (voix + volume mémorisé), veille du MARCHÉ (source factice, alertes, positions, dossiers) et veille de fond — 100 % SIMULÉ :
# aucun réseau, aucun son, aucune fenêtre, aucune vraie touche, aucun processus de fond lancé ; mémoire et journal dans un dossier temporaire.
# Code de sortie 0 = réussi.
$ErrorActionPreference = 'Stop'
$env:JARVIS_TEST = '1'      # TEST SILENCIEUX : aucun son, aucune fenêtre, aucun micro, aucune touche, aucune action réelle (voir lib\journal.ps1)
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $Root 'lib\journal.ps1')
$TR = Join-Path $env:TEMP ('jarvis-test-' + [guid]::NewGuid().ToString('N').Substring(0, 8)); New-Item -ItemType Directory $TR, "$TR\memoire", "$TR\logs" | Out-Null; $script:JarvisRoot = $TR
"# To-do de Liam" | Set-Content "$TR\memoire\todo.md" -Encoding UTF8; '# Notes' | Set-Content "$TR\memoire\notes.md" -Encoding UTF8; '# R' | Set-Content "$TR\memoire\resume.md" -Encoding UTF8
$Config = Get-Content (Get-ConfigPath) -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($l in 'voix', 'business', 'permissions', 'actions', 'coffre', 'entrees', 'ecrans', 'tableau', 'visage', 'sons', 'raccourcis', 'cerveau', 'cerveau-local', 'veille', 'memoire', 'rapide', 'discretion', 'modejeu', 'marche', 'matin', 'boucle') { . (Join-Path $Root "lib\$l.ps1") }
foreach ($f in (Get-ChildItem (Join-Path $Root 'lib\sources') -Filter '*.ps1' | Where-Object { $_.Name -notlike '_*' })) { . $f.FullName }
$script:JarvisRoot = $TR
$echecs = 0
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }
function Premier($plan) { if ($plan -and @($plan.actions).Count) { $plan.actions[0] } else { $null } }
function Attendre([int]$ms) { $t = (Get-Date).AddMilliseconds($ms); while ((Get-Date) -lt $t) { Update-Sons; Start-Sleep -Milliseconds 20 } }

$script:Dits = @(); $script:AppelsGetPlan = 0; $script:AppelsLlm = 0; $script:LlmReponse = ''
function Parler([string]$Texte, $Langue) { if ($script:Actif -ne $false -and $script:ModeJeu -ne $true) { $script:Dits += $Texte }; Add-Conv 'jarvis' $Texte }
function Get-Plan([string]$o) { $script:AppelsGetPlan++; $script:VoieCerveau = 'claude'; [pscustomobject]@{ dit = 'Réponse du cerveau.'; langue = 'fr'; actions = @() } }
function Invoke-LlmTexte([string]$systeme, [string]$utilisateur, [int]$timeoutSec = 120, [bool]$complexe = $true, [bool]$annoncer = $false) { $script:AppelsLlm++; $script:LlmReponse }
$script:Actif = $true; $script:ModeJeu = $false
$tmpSons = Join-Path $TR 'sounds'; New-Item -ItemType Directory $tmpSons | Out-Null; $script:SonsDossier = $tmpSons
[IO.File]::WriteAllBytes((Join-Path $tmpSons 'ambiance.mp3'), [byte[]](1..64))

Write-Host '1) Musique : commandes vocales'
$cas = @(@('baisse la musique', 'baisser'), @('baisse un peu la musique', 'baisser'), @('monte la musique', 'monter'), @('augmente la musique', 'monter'), @('coupe la musique', 'couper'), @('arrête la musique', 'couper'),
    @('remets la musique', 'remettre'), @('remets la musique, s''il te plaît', 'remettre'), @('musique très bas', 'tres_bas'), @('mets la musique très bas', 'tres_bas'), @('Jarvis, baisse la musique', 'baisser'))
foreach ($c in $cas) { $a = Premier (Get-PlanRapide $c[0]); Verifier ($a -and $a.type -eq 'musique' -and $a.commande -eq $c[1]) "« $($c[0]) » -> musique / $($c[1])" }
Verifier ((Premier (Get-PlanRapide 'coupe le son')).type -eq 'volume') '« coupe le son » reste le volume du PC (pas la musique)'
$script:MusiqueEtat = $null; $v0 = Get-VolumeBase
Verifier ([math]::Abs($v0 - 0.2) -lt 0.001) "volume de départ au premier lancement : 20 % ($v0)"
$script:Dits = @(); Invoke-Ordre 'baisse la musique'
Verifier ([math]::Abs((Get-VolumeBase) - 0.1) -lt 0.001 -and (Test-PhrasePolitesse 'silencieux' $script:Dits[-1])) "baisse de 10 points : 10 % ($($script:Dits[-1]))"
Invoke-Ordre 'monte la musique'; Verifier ([math]::Abs((Get-VolumeBase) - 0.2) -lt 0.001) 'monte : 20 %'
Invoke-Ordre 'musique très bas'; Verifier ([math]::Abs((Get-VolumeBase) - 0.1) -lt 0.001 -and (Test-PhrasePolitesse 'silencieux' $script:Dits[-1])) "très bas : 10 % ($($script:Dits[-1]))"
$o = Get-Content "$TR\memoire\musique.json" -Raw | ConvertFrom-Json
Verifier ([math]::Abs([double]$o.volume - 0.1) -lt 0.001) 'volume mémorisé dans memoire\musique.json'
Verifier ([double]$Config.volume_musique -eq 0.2) 'config.json (copie) inchangé : volume_musique reste 0.2'
Invoke-Ordre 'baisse la musique'; Invoke-Ordre 'baisse la musique'; Verifier ((Get-VolumeBase) -ge 0.05) 'le volume ne tombe jamais à zéro par « baisse » (plancher 5 %)'
$script:MusiqueEtat = $null; Verifier ([math]::Abs((Get-VolumeBase) - 0.05) -lt 0.001 -or (Get-VolumeBase) -le 0.1) "relu depuis memoire\ après « redémarrage » : $([int]((Get-VolumeBase) * 100)) %"
Write-Host '   ... « musique à N pour cent » (0 à 100), mémorisée comme les autres'
foreach ($c in @(@('musique à 30 pour cent', 30), @('mets la musique à 45 %', 45), @('règle la musique à 80', 80), @('Jarvis, musique à 0 pour cent', 0), @('mets la musique à 100 pour cent', 100), @('baisse la musique à 15 pour cent', 15), @('mets le volume de la musique à 60 pour cent', 60))) {
    $a = Premier (Get-PlanRapide $c[0]); Verifier ($a -and $a.type -eq 'musique' -and $a.commande -eq 'niveau' -and $a.valeur -eq $c[1]) "« $($c[0]) » -> niveau $($c[1])"
}
Verifier ((Premier (Get-PlanRapide 'mets le volume à 30')).type -eq 'volume') '« mets le volume à 30 » reste le volume du PC'
$script:MusiqueEtat = $null; $script:Dits = @(); Invoke-Ordre 'musique à 30 pour cent'
Verifier ([math]::Abs((Get-VolumeBase) - 0.3) -lt 0.001 -and (Test-PhrasePolitesse 'silencieux' $script:Dits[-1])) "musique à 30 % : $($script:Dits[-1])"
$script:MusiqueEtat = $null; Verifier ([math]::Abs((Get-VolumeBase) - 0.3) -lt 0.001 -and [math]::Abs([double](Get-Content "$TR\memoire\musique.json" -Raw | ConvertFrom-Json).volume - 0.3) -lt 0.001) 'mémorisée dans memoire\musique.json (pas dans config.json)'
Invoke-Ordre 'musique à 0 pour cent'; Verifier ((Get-VolumeBase) -eq 0 -and (Test-PhrasePolitesse 'silencieux' $script:Dits[-1])) '0 % accepté (silence voulu)'
Invoke-Ordre 'musique à 100 pour cent'; Verifier ((Get-VolumeBase) -eq 1) '100 % accepté'
$avant = Get-VolumeBase; Invoke-Ordre 'musique à 150 pour cent'; Verifier ((Get-VolumeBase) -eq $avant -and $script:Dits[-1] -match 'entre 0 et 100') '150 % refusé : « entre 0 et 100 pour cent »'
Set-MusiqueCoupee $true | Out-Null; Invoke-Ordre 'musique à 40 pour cent'; Verifier (-not (Test-MusiqueCoupee) -and [math]::Abs((Get-VolumeBase) - 0.4) -lt 0.001) 'coupée puis « à 40 pour cent » : elle repart à 40 %'
$script:MusiqueEtat = $null; Remove-Item "$TR\memoire\musique.json" -ErrorAction SilentlyContinue; Verifier ([math]::Abs((Get-VolumeBase) - 0.2) -lt 0.001) 'premier lancement (rien de mémorisé) : 20 %'
[void](Set-VolumeMusique 0.5)
Write-Host '   ... volume respecté par la musique, y compris la baisse automatique pendant la parole (faux lecteur)'
$Config.musique_ambiance = $true; $script:VolActuel = $null; Start-Ambiance
Verifier ($null -ne $script:Ambiance) 'ambiance démarrée (faux lecteur)'
Attendre 300; Verifier ([math]::Abs($script:Ambiance.Volume - 0.5) -lt 0.02) ("l'ambiance joue au volume mémorisé : {0:N2}" -f $script:Ambiance.Volume)
Set-SonsParole $true; Attendre 700
Verifier ([math]::Abs($script:Ambiance.Volume - 0.5 * 0.2) -lt 0.02) ("pendant que Jarvis parle : 20 % du volume choisi ({0:N2})" -f $script:Ambiance.Volume)
Set-SonsParole $false; Attendre 1500
Verifier ([math]::Abs($script:Ambiance.Volume - 0.5) -lt 0.03) ("elle remonte doucement au volume choisi ({0:N2})" -f $script:Ambiance.Volume)
Invoke-Ordre 'coupe la musique'; Attendre 700
Verifier ((Test-MusiqueCoupee) -and $script:Ambiance.Volume -lt 0.02) ("coupée : silence ({0:N2}), volume choisi conservé" -f $script:Ambiance.Volume)
Set-SonsParole $true; Attendre 200; Set-SonsParole $false
Verifier ($script:Ambiance.Volume -lt 0.02) 'coupée, la fin de la parole ne la rallume pas'
Invoke-Ordre 'remets la musique'; Attendre 1600
Verifier (-not (Test-MusiqueCoupee) -and [math]::Abs($script:Ambiance.Volume - 0.5) -lt 0.03) ("remise au volume choisi ({0:N2})" -f $script:Ambiance.Volume)
Stop-Musiques

Write-Host '2) Marché sans source : rien n''est lu, rien n''est inventé'
$d = Get-DonneesMarche
Verifier (-not $d.dispo -and $d.raison -match '^Marché désactivé : mets marche_actif à true') "marche_actif = false : « $($d.raison) »"
$Config.marche_actif = $true; $Config.sources_validees = @(); $d = Get-DonneesMarche
Verifier (-not $d.dispo -and $d.raison -match '^Source non branchée : sources_validees est vide') "marche_actif = true mais aucune source : « $($d.raison) »"
$Config.marche_actif = $false; $Config.sources_validees = @('factice')
Verifier ((Invoke-CycleVeilleFond @{}).fait -eq $false -and $script:FauxAppels -eq 0) 'marche_actif = false : le cycle ne contacte AUCUNE source (aucune lecture réseau)'
$Config.marche_actif = $true; $Config.sources_validees = @()
$r = Invoke-CycleVeilleFond @{}; Verifier (-not $r.fait -and $script:FauxAppels -eq 0) 'aucune source validée : le cycle ne lit rien'
Verifier ((@(Get-ValeursSuivies | ForEach-Object { $_.nom }) -join ',') -eq 'Thales,Société Générale') 'valeurs suivies par défaut : Thales, Société Générale'
Verifier ([double]$Config.seuil_alerte_pourcent -eq 3 -and $Config.marche_actif -eq $true -and $Config.PSObject.Properties['sources_validees']) 'config.json : seuil_alerte_pourcent = 3, marche_actif, sources_validees présents'
$script:Dits = @(); Invoke-Ordre 'comment va Thales ?'
Verifier ($script:Dits[-1] -match '^Source non branchée : sources_validees est vide' -and $script:Dits[-1] -notmatch '\d') "« comment va Thales ? » sans source : aucun chiffre ($($script:Dits[-1]))"
Invoke-Ordre 'quoi de neuf sur le marché ?'; Verifier ($script:Dits[-1] -match '^Source non branchée : sources_validees est vide') '« quoi de neuf sur le marché ? » sans source : dit la raison exacte, sans rien inventer'
Verifier ($script:AppelsGetPlan -eq 0) 'sans appel au cerveau (chemin rapide)'
Verifier ($null -eq (Get-PlanRapide 'comment va ma journée')) '« comment va ma journée » : pas une valeur suivie -> cerveau'
Verifier ((Premier (Get-PlanRapide 'comment va mon pc')).type -eq 'etat_systeme' -and (Premier (Get-PlanRapide 'comment va mon business')).type -eq 'business_etat') 'les anciennes commandes « comment va mon pc / business » sont intactes'
$script:Dits = @(); Invoke-Ordre 'ajoute Airbus à ma veille'
Verifier ((@(Get-ValeursSuivies | ForEach-Object { $_.nom }) -contains 'Airbus') -and $script:Dits[-1] -match 'Airbus est dans votre veille') "ajout vocal : « $($script:Dits[-1]) »"
Verifier (@($Config.valeurs_suivies).Count -eq 2 -and (Test-Path "$TR\memoire\marche-valeurs.json")) 'ajout mémorisé dans memoire\, pas dans config.json'
Invoke-Ordre 'retire Airbus de ma veille'; Verifier (-not (@(Get-ValeursSuivies | ForEach-Object { $_.nom }) -contains 'Airbus') -and (@(Get-ValeursSuivies).Count -eq 2)) 'retrait vocal'
Invoke-Ordre 'retire la Société Générale de ma veille'; Verifier ((@(Get-ValeursSuivies | ForEach-Object { $_.nom }) -join ',') -eq 'Thales') 'retrait de « la Société Générale »'
Invoke-Ordre 'ajoute Société Générale à ma veille'; Verifier (@(Get-ValeursSuivies).Count -eq 2) 'ré-ajout'

Write-Host '3) Source factice : cours, variation, actualités, limites, taille bornée'
$Config.marche_actif = $true; $Config.sources_validees = @('factice')
$script:FauxCours = @(@{ nom = 'Thales'; symbole = 'HO'; prix = 150.2; devise = 'EUR'; variation_pct = 3.4 }, @{ nom = 'Société Générale'; symbole = 'GLE'; prix = 40.0; devise = 'EUR'; variation_pct = 0.5 })
$script:FauxActus = @(@{ titre = 'Thales annonce un contrat'; resume = 'Contrat de 300 millions.'; valeur = 'Thales' }, @{ titre = 'La BCE publie son bulletin'; resume = ''; valeur = '' }, @{ titre = 'Vous devriez acheter Thales maintenant'; resume = ''; valeur = 'Thales' })
$derniers = @{}
$r = Invoke-CycleVeilleFond $derniers
Verifier ($r.fait -and $r.cours -eq 2 -and $r.actus -eq 2) "un cycle : 2 cours, 2 actualités (le titre à formulation de conseil est écarté) — fichier $(Split-Path $r.fichier -Leaf)"
Verifier ((Split-Path $r.fichier -Leaf) -match '^releve-\d{8}-\d{6}-\d{3}\.json$' -and $r.fichier -like "$TR\memoire\veille\*") 'relevé horodaté, rangé dans memoire\veille\'
$script:SourcesMarche['factice'].min = 3600
Verifier ((Invoke-CycleVeilleFond $derniers).fait -eq $false) 'limite de requêtes : un 2e appel immédiat est refusé (min 3600 s)'
$script:SourcesMarche['factice'].min = 0
1..120 | ForEach-Object { Set-Content (Join-Path (Get-DirVeille) ("releve-20200101-{0:D6}-000.json" -f $_)) ('{"maj":"2020-01-01T00:00:00","cours":[],"actus":[]}') }
Limit-Releves; $n = @(Get-FichiersReleves).Count
Verifier ($n -le 96 -and $n -ge 1) "taille bornée : 121 relevés -> $n conservés (au plus 96)"
Get-ChildItem (Get-DirVeille) -Filter 'releve-2020*' | Remove-Item -Force
$script:SourcesMarche['factice'].min = 0; $script:FauxPanne = 'quota atteint'
$r2 = Invoke-CycleVeilleFond @{}; Verifier ($r2.fait -and $r2.erreurs.Count -eq 2 -and $r2.erreurs[0] -match 'quota atteint') 'source en panne : relevé écrit avec « indisponible (cause) », sans planter'
$script:FauxPanne = ''
Remove-Item "$(Get-DirVeille)\releve-*.json" -Force; $script:MarcheDernierFichier = ''; $script:FauxAppels = 0
$r = Invoke-CycleVeilleFond @{}
$d = Get-DonneesMarche
Verifier ($d.dispo -and $d.valeurs.Count -eq 2 -and $d.valeurs[0].nom -eq 'Thales' -and $d.valeurs[0].prix -eq '150,2 euros' -and $d.valeurs[0].variation -eq 3.4) "panneau : Thales $($d.valeurs[0].prix), variation $($d.valeurs[0].variation) %, mis à jour à $($d.valeurs[0].maj)"
Verifier ($d.valeurs[0].actus.Count -eq 1 -and $d.valeurs[0].actus[0].source -eq 'Factice' -and $d.valeurs[0].actus[0].date -match '^\d\d/\d\d \d\d:\d\d$') 'actualités par valeur, avec source et date'
$script:Dits = @(); Invoke-Ordre 'comment va Thales ?'
$t = $script:Dits[-1]
Verifier ($t -match '150,2 euros' -and $t -match 'en hausse de 3,4 %' -and $t -match 'source Factice' -and $t -match 'mis à jour à \d\d:\d\d' -and $t -match 'Thales annonce un contrat \(Factice, \d\d/\d\d\)') "réponse factuelle : « $t »"
Verifier (-not (Test-SortieConseil $t)) 'aucun avis, aucune prédiction dans la réponse'
Invoke-Ordre 'quoi de neuf sur le marché ?'
Verifier ($script:Dits[-1] -match 'Société Générale : 40 euros' -and $script:Dits[-1] -match 'BCE publie') "résumé du marché : « $($script:Dits[-1]) »"
Invoke-Ordre 'comment va la Société Générale'; Verifier ($script:Dits[-1] -match 'Société Générale : 40 euros') '« comment va la Société Générale »'

Write-Host '4) Alertes de variation (UNE fois par valeur et par jour ; jamais en sourdine ni en mode jeu)'
$script:AlertesCache = $null; $script:Entrees = New-Object 'System.Collections.Generic.Queue[object]'
function Vider-Entrees { $l = @(); while ($script:Entrees.Count) { $l += $script:Entrees.Dequeue() }; $l }
$script:MarcheProchain = [datetime]::MinValue; Update-Marche
$e = @(Vider-Entrees)
Verifier ($e.Count -eq 1 -and $e[0].marche.texte -match "^Thales bouge de plus de 3 % aujourd'hui : en hausse de 3,4 %" -and $e[0].marche.texte -match 'source Factice') "Thales (+3,4 % >= 3 %) : alerte « $($e[0].marche.texte) »"
Verifier (-not (Test-SortieConseil $e[0].marche.texte)) 'le texte de l''alerte ne contient aucun conseil'
$script:MarcheDernierFichier = ''; $script:MarcheProchain = [datetime]::MinValue; Update-Marche
Verifier (@(Vider-Entrees).Count -eq 0) 'même relevé relu : la même alerte n''est PAS redite aujourd''hui'
$r = Invoke-CycleVeilleFond @{}; $script:MarcheProchain = [datetime]::MinValue; Update-Marche
Verifier (@(Vider-Entrees).Count -eq 0) 'nouveau relevé le même jour : toujours pas redite'
Verifier (@(Get-AlertesPanneau 6 | Where-Object { $_.titre -match 'Thales bouge' }).Count -eq 1) 'l''alerte reste visible au panneau Alertes'
# sourdine : panneau seulement
$script:FauxCours = @(@{ nom = 'Thales'; symbole = 'HO'; prix = 150.2; devise = 'EUR'; variation_pct = 3.4 }, @{ nom = 'Société Générale'; symbole = 'GLE'; prix = 38.0; devise = 'EUR'; variation_pct = -5.1 })
$script:Actif = $false; [void](Invoke-CycleVeilleFond @{}); $script:MarcheProchain = [datetime]::MinValue; Update-Marche
Verifier (@(Vider-Entrees).Count -eq 0 -and @(Get-AlertesPanneau 6 | Where-Object { $_.titre -match 'Société Générale bouge' }).Count -eq 1) 'sourdine : alerte notée au panneau, jamais dite'
$script:Actif = $true; $script:MarcheProchain = [datetime]::MinValue; Update-Marche
Verifier (@(Vider-Entrees).Count -eq 0) '... et pas dite non plus après la réactivation (une seule fois par jour)'
# mode jeu
$script:FauxCours = @(@{ nom = 'Thales'; symbole = 'HO'; prix = 150.2; devise = 'EUR'; variation_pct = 3.4 }, @{ nom = 'Société Générale'; symbole = 'GLE'; prix = 38.0; devise = 'EUR'; variation_pct = -5.1 }, @{ nom = 'Airbus'; symbole = 'AIR'; prix = 130.0; devise = 'EUR'; variation_pct = -4.0 })
$script:ModeJeu = $true; [void](Invoke-CycleVeilleFond @{}); $script:MarcheProchain = [datetime]::MinValue; Update-Marche
Verifier (@(Vider-Entrees).Count -eq 0 -and @(Get-AlertesPanneau 6 | Where-Object { $_.titre -match 'Airbus' }).Count -eq 1) 'mode jeu : alerte au panneau seulement, jamais dite'
$script:ModeJeu = $false
Write-Host '   ... alerte dite via la boucle (contexte « alerte »)'
$script:Dits = @(); Invoke-Entree @{ src = 'systeme'; texte = '[marche]'; marche = @{ cle = 'marche:test'; texte = 'Thales bouge de plus de 3 % aujourd''hui : en hausse de 3,4 %.'; dire = $true } }
Verifier ($script:Dits.Count -eq 1 -and $script:Dits[0] -match '^Alerte marché, monsieur\. Thales bouge') "dite : « $($script:Dits[0]) »"
$script:Actif = $false; $script:Dits = @(); Invoke-Entree @{ src = 'systeme'; texte = '[marche]'; marche = @{ cle = 'marche:test2'; texte = 'x'; dire = $true } }
Verifier ($script:Dits.Count -eq 0) 'en sourdine, la boucle ne dit rien'
$script:Actif = $true

Write-Host '5) Position et seuil (« j''ai pris … à …, préviens-moi à … »)'
$p = Get-PlanRapide "j'ai pris Thales à 120, préviens-moi à 110"; $a = Premier $p
Verifier ($a.type -eq 'position_noter' -and $a.nom -eq 'Thales' -and $a.prix -eq 120 -and $a.seuil -eq 110) "reconnu : $($a.nom) à $($a.prix), seuil $($a.seuil)"
$p = Get-PlanRapide "j'ai pris Société Générale à 41,5 euros, préviens-moi à 45"; $a = Premier $p
Verifier ($a.type -eq 'position_noter' -and $a.prix -eq 41.5 -and $a.seuil -eq 45) 'virgule décimale, seuil au-dessus du prix'
$script:Dits = @(); Invoke-Ordre "j'ai pris Thales à 120, préviens-moi à 110"
Verifier ($script:Dits[-1] -match 'Noté, monsieur : Thales à 120' -and @(Get-Positions2).Count -eq 1 -and @(Get-Positions2)[0].sens -eq 'bas') "position mémorisée dans memoire\positions.json : « $($script:Dits[-1]) »"
Verifier ((Get-Content "$TR\memoire\positions.json" -Raw) -notmatch '(?i)courtier|broker|compte') 'aucune donnée de courtier ni de compte'
$script:FauxCours = @(@{ nom = 'Thales'; symbole = 'HO'; prix = 109.5; devise = 'EUR'; variation_pct = 0.2 })
[void](Invoke-CycleVeilleFond @{}); $script:MarcheProchain = [datetime]::MinValue; Update-Marche
$e = @(Vider-Entrees)
Verifier ($e.Count -eq 1 -and $e[0].marche.texte -match 'Thales a atteint votre seuil de 110 : le cours est à 109,5') "seuil atteint : « $($e[0].marche.texte) »"
[void](Invoke-CycleVeilleFond @{}); $script:MarcheProchain = [datetime]::MinValue; Update-Marche
Verifier (@(Vider-Entrees).Count -eq 0 -and @(Get-Positions2)[0].atteint) 'dit UNE seule fois (la position est marquée « atteint »)'
Invoke-Ordre "j'ai pris Thales à 100, préviens-moi à 105"; $script:Actif = $false
$script:FauxCours = @(@{ nom = 'Thales'; symbole = 'HO'; prix = 106; devise = 'EUR'; variation_pct = 0.1 }); [void](Invoke-CycleVeilleFond @{}); $script:MarcheProchain = [datetime]::MinValue; Update-Marche
Verifier (@(Vider-Entrees).Count -eq 0 -and @(Get-Positions2)[0].atteint) 'seuil atteint en sourdine : jamais dit (marqué, visible au panneau)'
$script:Actif = $true

Write-Host '6) Dossier de décision : jamais de verdict'
$script:FauxCours = @(@{ nom = 'Thales'; symbole = 'HO'; prix = 150.2; devise = 'EUR'; variation_pct = 3.4 }, @{ nom = 'Société Générale'; symbole = 'GLE'; prix = 40.0; devise = 'EUR'; variation_pct = 0.5 })
[void](Invoke-CycleVeilleFond @{})
$script:LlmReponse = '{"dates":[],"pour":["Le cours progresse de 3,4 % aujourd''hui (Factice).","Le cours atteint 999 euros.","Vous devriez acheter Thales dès maintenant."],"contre":["Le titre a déjà monté de 3,4 % aujourd''hui."],"risques":["Une seule source est disponible."],"scenarios":["Si le contrat annoncé se confirme alors la hausse du jour pourrait être justifiée.","Le titre va monter de 20 %."],"comparaison":[]}'
$script:Dits = @(); $script:AppelsLlm = 0; Invoke-Ordre 'fais-moi un dossier sur Thales'
$D = $script:Dossier
$tous = @($D.sections | ForEach-Object { $_.lignes }) -join ' | '
Verifier ($D -and $D.titre -eq 'Dossier : Thales' -and $script:AppelsLlm -eq 1) "dossier construit : $(@($D.sections).Count) rubriques, 1 appel au cerveau, affiché au tableau (Get-DonneesTableau.dossier)"
Verifier ((Get-DonneesTableau).dossier.titre -eq 'Dossier : Thales') 'le tableau de bord transporte le dossier'
$titres = @($D.sections | ForEach-Object { $_.titre })
Verifier (($titres -contains 'Chiffres clés') -and ($titres -contains 'Faits récents (sources)') -and ($titres -contains 'Arguments pour') -and ($titres -contains 'Arguments contre') -and ($titres -contains 'Risques') -and ($titres -match 'Scénarios') -and ($titres -contains 'Ce qui manque') -and ($titres -contains 'Questions à vous poser')) "rubriques : $($titres -join ' ; ')"
Verifier ($tous -match 'progresse de 3,4 %' -and $tous -notmatch '999' -and $tous -notmatch 'acheter Thales dès' -and $tous -notmatch 'va monter de 20') 'lignes du cerveau écartées : chiffre absent des sources (999, 20 %), conseil (« acheter »), prédiction'
Verifier ($tous -match 'Si le contrat annoncé se confirme alors') 'scénario conditionnel « si… alors… » conservé'
$q = ($D.sections | Where-Object { $_.titre -eq 'Questions à vous poser' }).lignes -join ' '
Verifier ($q -match 'horizon' -and $q -match 'part de votre capital' -and $q -match 'seuil') 'questions : horizon, part du capital, seuil de sortie'
$m = ($D.sections | Where-Object { $_.titre -eq 'Ce qui manque' }).lignes -join ' '
Verifier ($m -match 'calendrier') 'ce qui manque est dit (calendrier non branché)'
Verifier (-not (Test-SortieConseil $tous)) 'aucune recommandation ni prédiction dans tout le dossier'
Verifier ($script:Dits[-1] -match 'Le dossier est affiché au tableau') "réponse courte : « $($script:Dits[-1]) »"
$script:Dits = @(); Invoke-Ordre 'compare Thales et Société Générale'
Verifier ($script:Dossier.titre -eq 'Dossier : Thales / Société Générale' -and ((($script:Dossier.sections | Where-Object { $_.titre -eq 'Chiffres clés' }).lignes -join ' ') -match 'Thales : .*Société Générale : ')) 'comparaison : deux valeurs, chiffres clés des deux'
# achat / vente : pas de verdict, le dossier à la place
$script:Dits = @(); $script:Dossier = $null; Invoke-Ordre 'dois-je acheter Thales ?'
Verifier ($script:Dits[0] -eq 'Je ne donne pas de verdict, monsieur, mais voici le dossier.' -and $script:Dossier -and $script:Dossier.titre -eq 'Dossier : Thales') "« dois-je acheter Thales ? » : « $($script:Dits[0]) » + dossier affiché"
$script:Dits = @(); $script:Dossier = $null; Invoke-Ordre 'faut-il vendre Airbus ?'
Verifier ($script:Dits[0] -match '^Je ne donne pas de verdict' -and $script:Dossier.titre -eq 'Dossier : Airbus') '« faut-il vendre Airbus ? » : dossier sur Airbus'
$script:Dits = @(); $script:Dossier = $null; Invoke-Ordre 'dois-je acheter des actions ?'
Verifier ($script:Dits[0] -match '^Je ne donne pas de conseil en investissement' -and -not $script:Dossier) 'sans valeur identifiée : refus standard (faits et risques), pas de dossier'
Verifier ($script:AppelsGetPlan -eq 0) 'jamais d''appel au cerveau pour ces commandes'
# sans source : le cerveau n'est même pas appelé, le dossier dit ce qui manque
$Config.sources_validees = @(); $script:AppelsLlm = 0; $script:Dossier = $null; Invoke-Ordre 'fais un dossier sur Thales'
$m = ($script:Dossier.sections | Where-Object { $_.titre -eq 'Ce qui manque' }).lignes -join ' '
Verifier ($script:AppelsLlm -eq 0 -and $m -match 'Source non branchée : sources_validees est vide' -and -not ($script:Dossier.sections | Where-Object { $_.titre -eq 'Chiffres clés' })) 'sans source validée : aucun appel au cerveau, aucun chiffre, « aucune source de marché validée »'
$Config.sources_validees = @('factice')

Write-Host '7) Veille de fond : pause en mode jeu, arrêt avec Jarvis, jamais lancée par les tests'
Verifier ((Start-VeilleFond) -eq $false) 'en test, aucun processus de fond n''est lancé'
$script:ModeJeu = $false; Enter-ModeJeu 'test'
Verifier (Test-Path (Get-FichierFlagJeu)) 'mode jeu : memoire\modejeu.flag posé (la veille de fond se met en pause)'
[void](Exit-ModeJeu 'test'); Verifier (-not (Test-Path (Get-FichierFlagJeu))) 'fin du mode jeu : drapeau retiré'
$vf = Get-Content (Join-Path $Root 'veille-fond.ps1') -Raw -Encoding UTF8
Verifier ($vf -match 'ParentPid' -and $vf -match 'quitter\.flag' -and $vf -match 'Get-FichierFlagJeu' -and $vf -match 'Test-MarcheActif' -and $vf -match 'BelowNormal') 'veille-fond.ps1 : s''arrête avec Jarvis, pause en mode jeu, aucune lecture si marche_actif est false, priorité basse'
Verifier ($vf -notmatch 'Parler|Invoke-Son|Add-Type|Start-Process') 'veille-fond.ps1 : ni voix, ni son, ni fenêtre'
$ar = Get-Content (Join-Path $Root 'arreter.ps1') -Raw -Encoding UTF8
Verifier ($ar -match 'veille-fond') 'arreter.ps1 arrête aussi la veille de fond'
$ins = Get-Content (Join-Path $Root 'installer.ps1') -Raw -Encoding UTF8
Verifier ($ins -match 'param\(\[switch\]\$DemarrageWindows\)' -and $ins.IndexOf('if (-not $DemarrageWindows)') -lt $ins.IndexOf('Register-ScheduledTask') -and $ins -match 'sourdine') 'installer.ps1 : option -DemarrageWindows explicite, n''installe rien sans elle, exige le démarrage en sourdine (NON exécuté ici)'
$mj = Get-Content (Join-Path $Root 'jarvis.ps1') -Raw -Encoding UTF8
Verifier ($mj -match 'Start-VeilleFond' -and $mj -match 'Stop-VeilleFond') 'jarvis.ps1 lance et arrête la veille de fond'
$fa = Get-Content (Join-Path $Root 'lib\sources\factice.ps1') -Raw -Encoding UTF8
Verifier (((Get-ChildItem (Join-Path $Root 'lib\sources') -Filter '*.ps1' | Where-Object { $_.Name -notlike '_*' }).Name -join ',') -eq 'alphavantage.ps1,factice.ps1,rss.ps1' -and (Get-Content (Join-Path $Root 'config.json') -Raw -Encoding UTF8 | ConvertFrom-Json).marche_actif -eq $false) 'modules présents : alphavantage, factice (tests), rss — et marche_actif reste false dans config.json : rien n''est lu'
Verifier ($fa -match 'Test-ModeTest') 'la source factice refuse de répondre hors test'

Remove-Item $TR -Recurse -Force -ErrorAction SilentlyContinue
if ($echecs) { Write-Host "`nÉCHEC : $echecs vérification(s) en échec." -ForegroundColor Red; exit 1 }
Write-Host "`nRÉUSSI"; exit 0
