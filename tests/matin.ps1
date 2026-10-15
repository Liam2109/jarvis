# Test du BRIEFING DU MATIN (court : 5 lignes au plus, version dite de 15 s au plus, détails à la demande) — 100 % SIMULÉ :
# aucun réseau (Supabase, Stripe et site sont des bouchons), aucune voix, aucun son, aucune fenêtre. Mémoire et journal dans un dossier temporaire.
# Code de sortie 0 = réussi.
$ErrorActionPreference = 'Stop'
$env:JARVIS_TEST = '1'      # TEST SILENCIEUX : aucun son, aucune fenêtre, aucun micro, aucune touche, aucune action réelle (voir lib\journal.ps1)
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $Root 'lib\journal.ps1')
$TR = Join-Path $env:TEMP ('jarvis-test-' + [guid]::NewGuid().ToString('N').Substring(0, 8)); New-Item -ItemType Directory $TR, "$TR\memoire", "$TR\logs" | Out-Null; $script:JarvisRoot = $TR
"# To-do de Liam`r`n- [ ] Appeler le comptable" | Set-Content "$TR\memoire\todo.md" -Encoding UTF8; '# Notes' | Set-Content "$TR\memoire\notes.md" -Encoding UTF8; '# R' | Set-Content "$TR\memoire\resume.md" -Encoding UTF8
$Config = Get-Content (Get-ConfigPath) -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($l in 'voix', 'business', 'permissions', 'actions', 'coffre', 'entrees', 'ecrans', 'tableau', 'visage', 'sons', 'raccourcis', 'cerveau', 'cerveau-local', 'veille', 'memoire', 'rapide', 'discretion', 'modejeu', 'marche', 'matin', 'boucle') { . (Join-Path $Root "lib\$l.ps1") }
foreach ($f in (Get-ChildItem (Join-Path $Root 'lib\sources') -Filter '*.ps1' | Where-Object { $_.Name -notlike '_*' })) { . $f.FullName }
$script:JarvisRoot = $TR
$echecs = 0
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }
function Premier($plan) { if ($plan -and @($plan.actions).Count) { $plan.actions[0] } else { $null } }

$script:Dits = @(); $script:AppelsSupabase = 0; $script:StatsSupabase = $null; $script:SiteOk = $true; $script:CaStripe = $null
function Parler([string]$Texte, $Langue) { if ($script:Actif -ne $false -and $script:ModeJeu -ne $true -and (Test-VoixPermise).ok) { $script:Dits += $Texte }; Add-Conv 'jarvis' $Texte }
function Get-Plan([string]$o) { [pscustomobject]@{ dit = 'Réponse du cerveau.'; langue = 'fr'; actions = @() } }
function Get-SupabaseStats([datetime]$depuis) { $script:AppelsSupabase++; $script:StatsSupabase }
function Get-StripeCA([datetime]$depuis) { $script:CaStripe }
function Get-StatutSite([int]$timeout = 15) { [pscustomobject]@{ ok = $script:SiteOk; code = $(if ($script:SiteOk) { 200 } else { 503 }); detail = '' } }
function Get-StatsOk($q, $e, $n, $a, $p, $r, $qt = 500, $ab = 16) { @{ dispo = $true; http = 200; cas = '200'; source = 'Supabase (jarvis_stats)'; saas = @{ quiz_24h = $q; emails_24h = $e; nouveaux_abonnes_24h = $n; abonnes_en_annulation = $a; paiements_echoues = $p; demandes_retractation_a_traiter = $r; quiz_total = $qt; abonnes_actifs = $ab } } }
$script:Actif = $true; $script:ModeJeu = $false
$Config.marche_actif = $false

Write-Host '1) Comparaison « depuis hier » et taux de conversion (fonctions pures)'
$l = Get-LignesSaas @{ quiz_24h = 14; emails_24h = 9; nouveaux_abonnes_24h = 2; abonnes_en_annulation = 1; paiements_echoues = 0; demandes_retractation_a_traiter = 0 } ([pscustomobject]@{ quiz_24h = 10; emails_24h = 9; nouveaux_abonnes_24h = 3; abonnes_en_annulation = 1; paiements_echoues = 2; demandes_retractation_a_traiter = 0 })
Verifier ($l[0] -eq 'Nouveaux quiz : 14 (depuis hier : 10, +4).' -and $l[2] -eq 'Nouveaux abonnés : 2 (depuis hier : 3, -1).' -and $l[4] -match 'depuis hier : 2, -2') "détails : $($l[0]) | $($l[2])"
$t = Get-TauxConversion @{ abonnes_actifs = 16; quiz_total = 500 } ([pscustomobject]@{ abonnes_actifs = 14; quiz_total = 480 })
Verifier ($t.dispo -and [math]::Abs($t.pct - 3.2) -lt 0.001 -and [math]::Abs($t.hier - 2.9167) -lt 0.001 -and [math]::Abs($t.delta - 0.2833) -lt 0.001) 'conversion = abonnés actifs / quiz : 16 / 500 = 3,2 % (hier 2,9 %)'
Verifier ((Format-ConversionLigne $t) -eq 'Taux de conversion : 3,2 % (abonnés actifs / quiz ; hier 2,9 %, +0,3 point).') "ligne : $(Format-ConversionLigne $t)"
Verifier ((Format-ConversionLigne (Get-TauxConversion @{ abonnes_actifs = 16; quiz_total = 500 } $null)) -match 'pas de relevé d''hier pour comparer') 'sans relevé d''hier : le dit'
Verifier (-not (Get-TauxConversion @{ abonnes_actifs = 16; quiz_total = 0 } $null).dispo -and (Format-ConversionLigne (Get-TauxConversion @{ quiz_total = 100 } $null)) -match 'indisponible') 'quiz à 0 ou chiffre absent : « indisponible », jamais de division par zéro'

Write-Host '2) Briefing court au démarrage : 5 lignes au plus, affiché SANS voix'
$script:StatsSupabase = Get-StatsOk 14 9 2 1 3 0
$script:CaStripe = @{ dispo = $true; montants = @{ EUR = [int64]12000 }; paiements = 4; partiel = $false; source = 'Stripe' }
Save-JsonMemoire 'saas-releves.json' ([ordered]@{ jours = [ordered]@{ ((Get-Date).AddDays(-1).ToString('yyyy-MM-dd')) = [ordered]@{ quiz_24h = 10; abonnes_actifs = 14; quiz_total = 480; paiements_echoues = 2 } } })
$arret = (Get-Date).AddHours(-11); Save-JsonMemoire 'arret.json' ([ordered]@{ arret = $arret.ToString('o') })
Verifier ([math]::Abs(((Get-DepuisBriefing) - $arret).TotalSeconds) -lt 2) 'depuis la dernière fermeture (heure mémorisée)'
$script:Dits = @(); $neuf = Initialize-BriefingMatin
Verifier ($neuf -eq $true -and $script:AppelsSupabase -eq 1 -and $script:Dits.Count -eq 0) 'préparé au démarrage (1 lecture Supabase), RIEN n''est dit'
$L = @($script:BriefingLignes); $txt = $L -join "`n"
Verifier ($L.Count -eq 3) "3 lignes (ni marché, ni rétractation : rien à dire) : $($L.Count)"
Verifier ($L[0] -eq 'Nouveaux quiz : 14 · Nouveaux abonnés : 2 · En annulation : 1.') "ligne 1 : $($L[0])"
Verifier ($L[1] -eq "Chiffre d'affaires sur la période : 120 euros.") "ligne 2 : $($L[1])"
Verifier ($L[2] -eq 'Taux de conversion : 3,2 % (abonnés actifs / quiz ; hier 2,9 %, +0,3 point).') "ligne 3 : $($L[2])"
Verifier ($txt -notmatch '(?i)paiement|échou|rétractation|marché|site|tâche|e-mail') 'aucun paiement échoué, ni autre détail, dans la version courte'
Verifier ((Get-DonneesTableau).briefing.Count -eq 3 -and $script:BriefingEnAttente -eq $true) 'le tableau reçoit les 3 lignes ; à dire à la première activation'
$P = @($script:BriefingMatin.parle); $mots = (($P -join ' ') -split '\s+').Count
Verifier ($mots -le 36 -and (Get-DureeDitSecondes $P) -le 15) "version dite : $mots mots ≈ $(Get-DureeDitSecondes $P) s (au plus 15 s) : « $($P -join ' ') »"
Verifier (($P -join ' ') -notmatch '(?i)paiement') 'rien sur les paiements dans la version dite'

Write-Host '3) Lignes conditionnelles : rétractation (> 0) et marché (source branchée)'
$script:StatsSupabase = Get-StatsOk 14 9 2 1 3 2
Remove-Item "$TR\memoire\briefing-jour.json"; $null = Initialize-BriefingMatin; $L = @($script:BriefingLignes)
Verifier ($L.Count -eq 4 -and $L[3] -eq 'Demandes de rétractation à traiter : 2.') "rétractation à 2 : ligne ajoutée ($($L[3]))"
Verifier (($script:BriefingMatin.parle -join ' ') -match '2 demandes de rétractation à traiter') 'et dite'
$script:StatsSupabase = Get-StatsOk 14 9 2 1 3 1
Remove-Item "$TR\memoire\briefing-jour.json"; $null = Initialize-BriefingMatin; $L = @($script:BriefingLignes)
Verifier ($L[3] -eq 'Demande de rétractation à traiter : 1.') 'au singulier pour 1'
$Config.marche_actif = $true; $Config.sources_validees = @('factice')
$script:FauxCours = @(@{ nom = 'Thales'; symbole = 'HO'; prix = 150.2; devise = 'EUR'; variation_pct = 1.2 }, @{ nom = 'Société Générale'; symbole = 'GLE'; prix = 40.0; devise = 'EUR'; variation_pct = -0.5 })
$script:FauxActus = @(@{ titre = 'Thales annonce un contrat'; resume = ''; valeur = 'Thales' })
Remove-Item "$TR\memoire\briefing-jour.json"; $null = Initialize-BriefingMatin; $L = @($script:BriefingLignes)
Verifier ($L.Count -eq 5 -and $L[3] -eq 'Marché : en attente du premier relevé de la veille de fond.') "source branchée mais aucun relevé : « $($L[3]) »"
[void](Invoke-CycleVeilleFond @{})
Remove-Item "$TR\memoire\briefing-jour.json"; $null = Initialize-BriefingMatin; $L = @($script:BriefingLignes)
Verifier ($L.Count -eq 5 -and $L[3] -eq 'Marché : Thales 150,2 euros +1,2 % ; Société Générale 40 euros -0,5 %.' -and $L[4] -match 'rétractation') "source branchée : ligne marché ajoutée, 5 lignes au plus : $($L[3])"
$P = @($script:BriefingMatin.parle); $mots = (($P -join ' ') -split '\s+').Count
Verifier ($mots -le 36 -and (Get-DureeDitSecondes $P) -le 15) "avec tout : version dite toujours ≤ 15 s ($mots mots ≈ $(Get-DureeDitSecondes $P) s)"
Verifier (($P -join ' ') -match 'rétractation') 'la rétractation passe avant le marché si l''on doit couper'
$Config.marche_actif = $false; $Config.sources_validees = @()
Remove-Item "$TR\memoire\briefing-jour.json"; $null = Initialize-BriefingMatin
Verifier (@($script:BriefingLignes | Where-Object { $_ -match 'Marché' }).Count -eq 0) 'marché désactivé ou sans source : AUCUNE ligne marché'
$script:StatsSupabase = Get-StatsOk 14 9 2 1 3 0

Write-Host '4) Sources indisponibles : « indisponible (cause) », le reste n''est pas bloqué'
$script:StatsSupabase = @{ dispo = $false; http = 403; cas = '403'; raison = 'Supabase : jeton refusé (JARVIS_STATS_TOKEN faux ou vide)' }
Remove-Item "$TR\memoire\briefing-jour.json"; $null = Initialize-BriefingMatin; $L = @($script:BriefingLignes)
Verifier ($L[0] -match '^Mon SaaS : indisponible \(jeton refusé' -and $L[1] -eq "Chiffre d'affaires sur la période : 120 euros." -and $L.Count -le 5) "Supabase en panne : « $($L[0]) » ; le chiffre d'affaires reste là"
$script:StatsSupabase = Get-StatsOk 14 9 2 1 3 0; $script:CaStripe = @{ dispo = $false; raison = 'Stripe (chiffre d''affaires) : clé refusée ou permission de lecture manquante' }
Remove-Item "$TR\memoire\briefing-jour.json"; $null = Initialize-BriefingMatin; $L = @($script:BriefingLignes)
Verifier ($L[1] -eq "Chiffre d'affaires : indisponible (clé refusée ou permission de lecture manquante)." -and $L[0] -match 'Nouveaux quiz : 14') "Stripe en panne : « $($L[1]) »"
$script:CaStripe = @{ dispo = $true; montants = @{ EUR = [int64]12000 }; paiements = 4; partiel = $false; source = 'Stripe' }

Write-Host '5) « Détails du briefing » : tout le détail reste disponible'
foreach ($o in 'détails du briefing', 'donne-moi les détails du briefing', 'briefing détaillé') { Verifier ((Premier (Get-PlanRapide $o)).type -eq 'briefing_details') "« $o » -> briefing_details" }
Verifier ((Premier (Get-PlanRapide 'relis le briefing')).type -eq 'briefing_relire' -and (Premier (Get-PlanRapide 'fais le briefing')).type -eq 'briefing_dire') '« relis le briefing » et « fais le briefing » inchangés'
$script:StatsSupabase = Get-StatsOk 14 9 2 1 3 0
Remove-Item "$TR\memoire\briefing-jour.json"; $null = Initialize-BriefingMatin
$D = @($script:BriefingMatin.details); $dt = $D -join "`n"
Verifier ($dt -match 'Mon SaaS depuis hier' -and $dt -match 'Paiements échoués : 3' -and $dt -match 'E-mails récupérés : 9' -and $dt -match 'Site tonproduit.shop : en ligne' -and $dt -match 'Tâches ouvertes : 1' -and $dt -match 'Alertes graves et rappels' -and $dt -match "Chiffre d'affaires" -and $dt -match 'Taux de conversion') "détails complets conservés ($($D.Count) lignes, paiements échoués compris)"
$script:Dits = @(); Invoke-Ordre 'détails du briefing'
Verifier ($script:Dits.Count -eq $D.Count -and ($script:Dits -join ' ') -match 'Paiements échoués : 3' -and $script:BriefingLignes.Count -eq $D.Count) 'dit et affiche le détail complet'
$script:Dits = @(); Invoke-Ordre 'relis le briefing'
Verifier ($script:Dits.Count -eq @($script:BriefingMatin.parle).Count -and $script:BriefingLignes.Count -eq @($script:BriefingMatin.lignes).Count) '« relis le briefing » : version courte seulement'

Write-Host '6) Dit UNE seule fois, à la première activation ; jamais en sourdine ni en mode jeu'
Remove-Item "$TR\memoire\briefing-jour.json"; $null = Initialize-BriefingMatin
$script:Actif = $false; $script:Dits = @(); Invoke-BriefingMatinDire
Verifier ($script:Dits.Count -eq 0 -and $script:BriefingEnAttente -eq $true) 'sourdine : rien de dit, toujours en attente'
$script:Actif = $true; Invoke-BriefingMatinDire
Verifier ($script:Dits.Count -eq @($script:BriefingMatin.parle).Count -and $script:Dits[0] -match '^(Bonjour|Bonsoir) monsieur\.$' -and $script:BriefingMatin.dit) "première activation : version courte dite ($($script:Dits.Count) phrases), marquée « dit »"
$script:Dits = @(); Invoke-BriefingMatinDire; Verifier ($script:Dits.Count -eq 0) 'deuxième activation le même jour : rien'
$script:AppelsSupabase = 0; $null = Initialize-BriefingMatin; Verifier ($script:BriefingEnAttente -eq $false -and $script:AppelsSupabase -eq 0) 'redémarrage le même jour : même briefing, aucune relecture, plus « à dire »'
Remove-Item "$TR\memoire\briefing-jour.json"; $null = Initialize-BriefingMatin
$script:ModeJeu = $true; $script:Dits = @(); Invoke-BriefingMatinDire
Verifier ($script:Dits.Count -eq 0 -and $script:BriefingMatin.dit -and -not $script:BriefingEnAttente) 'mode jeu : jamais dit (affiché au tableau seulement)'
$script:ModeJeu = $false
Remove-Item "$TR\memoire\briefing-jour.json"; $Config.briefing_vocal = $false; $null = Initialize-BriefingMatin
Verifier ($script:BriefingEnAttente -eq $false -and $script:BriefingLignes.Count -eq 3) 'briefing_vocal = false : affiché au tableau, jamais dit'
$Config.briefing_vocal = $true
# ancien format du même jour (sans version courte) : régénéré, « déjà dit » conservé
Save-JsonMemoire 'briefing-jour.json' ([ordered]@{ date = (Get-Date).ToString('yyyy-MM-dd'); genere = (Get-Date).ToString('o'); depuis = (Get-Date).ToString('o'); dit = $true; lignes = @('ancien 1', 'ancien 2') })
$neuf = Initialize-BriefingMatin
Verifier ($neuf -and $script:BriefingMatin.dit -and $script:BriefingLignes[0] -match 'Nouveaux quiz' -and -not $script:BriefingEnAttente) 'ancien format du jour : régénéré en version courte, sans le redire'

Write-Host '7) Heure d''arrêt mémorisée'
Remove-Item "$TR\memoire\arret.json" -ErrorAction SilentlyContinue; Save-HeureArret
$o = Read-JsonMemoire 'arret.json'; Verifier ([math]::Abs(((Get-Date) - [datetime]::Parse($o.arret, [Globalization.CultureInfo]::InvariantCulture, [Globalization.DateTimeStyles]::RoundtripKind)).TotalSeconds) -lt 5) 'Save-HeureArret écrit l''heure dans memoire\arret.json'
$mj = Get-Content (Join-Path $Root 'jarvis.ps1') -Raw -Encoding UTF8
Verifier ($mj -match 'finally \{ Save-HeureArret' -and $mj -match 'Initialize-BriefingMatin' -and $mj -notmatch 'Invoke-Briefing -Auto') 'jarvis.ps1 : briefing préparé au démarrage, heure d''arrêt enregistrée à la fermeture'

Remove-Item $TR -Recurse -Force -ErrorAction SilentlyContinue
if ($echecs) { Write-Host "`nÉCHEC : $echecs vérification(s) en échec." -ForegroundColor Red; exit 1 }
Write-Host "`nRÉUSSI"; exit 0
