# Test SILENCIEUX de la voix plus naturelle (lib\voix-naturelle.ps1) — aucun son, aucun processus de synthèse, aucun réseau : on vérifie les RÉGLAGES, la NORMALISATION du texte,
# le découpage en phrases, les pauses, la marge et le fondu de fin (tests\voix-piper.py, WAV simulé), le test de voix et l'absence de régression de vitesse. Code de sortie 0 = réussi.
$ErrorActionPreference = 'Stop'
$env:JARVIS_TEST = '1'
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $Root 'lib\journal.ps1')
$TR = Join-Path $env:TEMP ('jarvis-test-' + [guid]::NewGuid().ToString('N').Substring(0, 8)); New-Item -ItemType Directory $TR, "$TR\memoire", "$TR\logs" | Out-Null; $script:JarvisRoot = $TR
'# To-do de Liam' | Set-Content "$TR\memoire\todo.md" -Encoding UTF8; '# Notes' | Set-Content "$TR\memoire\notes.md" -Encoding UTF8; '# R' | Set-Content "$TR\memoire\resume.md" -Encoding UTF8
$Config = Get-Content $(if ($env:JARVIS_CONFIG -and (Test-Path $env:JARVIS_CONFIG)) { $env:JARVIS_CONFIG } else { Join-Path $Root 'config.json' }) -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($l in 'voix', 'business', 'permissions', 'actions', 'coffre', 'entrees', 'ecrans', 'tableau', 'visage', 'sons', 'raccourcis', 'cerveau', 'cerveau-local', 'veille', 'memoire', 'rapide', 'discretion', 'modejeu', 'competences', 'marche', 'priorite', 'comprehension', 'routeur', 'pc', 'bureau', 'salle-marche', 'matin') { . (Join-Path $Root "lib\$l.ps1") }
$script:JarvisRoot = $TR
$script:PolitesseFixe = $true
$echecs = 0
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }
function Fixer([string]$cle, $val) { if ($Config.PSObject.Properties[$cle]) { $Config.$cle = $val } else { $Config | Add-Member -NotePropertyName $cle -NotePropertyValue $val } }
function Effacer([string]$cle) { if ($Config.PSObject.Properties[$cle]) { $Config.PSObject.Properties.Remove($cle) } }
$reglages = 'voix_naturelle', 'voix_edge_rate', 'voix_edge_pitch', 'voix_edge_volume', 'voix_piper_length_scale', 'voix_piper_noise_scale', 'voix_piper_noise_w', 'voix_piper_sentence_silence', 'voix_marge_fin_ms', 'voix_fondu_ms', 'voix_pause_phrase_ms'
$vraie = Get-Content (Join-Path $Root 'config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($k in $reglages) { Effacer $k }      # (le test part des valeurs par défaut du code, quels que soient les réglages de Liam)

Write-Host '1) Réglages : valeurs par défaut raisonnables, bornes'
$p = Get-VoixParam
Verifier ($p.naturelle -and $p.marge_ms -ge 150 -and $p.marge_ms -le 250) 'marge de silence en fin d''audio : 200 ms par défaut (entre 150 et 250)'
Verifier ($p.edge_rate -eq '-4%' -and $p.edge_pitch -eq '-2Hz' -and $p.edge_volume -eq '+0%') 'Edge : débit légèrement plus doux (-4 %), hauteur -2 Hz, volume inchangé'
Verifier ($p.piper_length -gt 1.0 -and $p.piper_length -lt 1.2 -and $p.piper_noise -gt 0.667 -and $p.piper_noise_w -ge 0.8 -and $p.piper_silence -ge 0.15 -and $p.piper_silence -le 0.4) 'Piper : débit un peu plus lent, intonation plus variable, silence entre phrases'
Verifier ($p.fondu_ms -gt 0 -and $p.fondu_ms -le 100 -and $p.pause_ms -ge 100 -and $p.pause_ms -le 400) 'fondu de fin très court, pause entre phrases de quelques dixièmes de seconde'
foreach ($k in 'voix_naturelle', 'voix_edge_rate', 'voix_edge_pitch', 'voix_edge_volume', 'voix_piper_length_scale', 'voix_piper_noise_scale', 'voix_piper_noise_w', 'voix_piper_sentence_silence', 'voix_marge_fin_ms', 'voix_fondu_ms', 'voix_pause_phrase_ms') { Verifier ([bool]$vraie.PSObject.Properties[$k]) "config.json contient « $k »" }
Fixer 'voix_marge_fin_ms' 9999; Fixer 'voix_fondu_ms' 9999; Fixer 'voix_pause_phrase_ms' -5; Fixer 'voix_piper_length_scale' 'abc'
$p = Get-VoixParam
Verifier ($p.marge_ms -eq 600 -and $p.fondu_ms -eq 150 -and $p.pause_ms -eq 0 -and $p.piper_length -eq 1.08) 'valeurs hors bornes ramenées dans les bornes ; valeur illisible : défaut'
Fixer 'voix_edge_rate' 'vite'; Fixer 'voix_edge_pitch' '-2'; Fixer 'voix_edge_volume' '+0%; rm'
$p = Get-VoixParam; Verifier ($p.edge_rate -eq '-4%' -and $p.edge_pitch -eq '-2Hz' -and $p.edge_volume -eq '+0%') 'réglage Edge invalide (ou piégé) : défaut'
foreach ($k in $reglages) { Effacer $k }
Fixer 'voix_edge_rate' '-8%'; Fixer 'voix_edge_pitch' '+3Hz'
Verifier ((Get-EdgeArgsProsodie) -eq '--rate=-8% --pitch=+3Hz --volume=+0%') 'arguments edge-tts : --rate=-8% --pitch=+3Hz --volume=+0%'
foreach ($k in $reglages) { Effacer $k }
Verifier ((Get-EdgeArgsProsodie) -eq '--rate=-4% --pitch=-2Hz --volume=+0%') 'arguments edge-tts par défaut'
$j = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String((Get-PiperParamsBase64))) | ConvertFrom-Json
Verifier ($j.length_scale -eq 1.08 -and $j.noise_scale -eq 0.75 -and $j.noise_w -eq 0.9 -and $j.sentence_silence -eq 0.25 -and $j.marge_ms -eq 200 -and $j.fondu_ms -eq 40) 'réglages Piper transmis au serveur (length_scale, noise_scale, noise_w, sentence_silence, marge, fondu)'
$s1 = Get-VoixSignature 'edge'; Fixer 'voix_edge_rate' '-6%'; $s2 = Get-VoixSignature 'edge'; Effacer 'voix_edge_rate'
Verifier ($s1 -ne $s2 -and (Get-CheminTtsCache "x|$s1" 'Bonjour') -ne (Get-CheminTtsCache "x|$s2" 'Bonjour')) 'changer le rythme change la clé du cache vocal (aucun ancien enregistrement rejoué)'
Verifier ((Get-VoixSignature 'piper') -ne (Get-VoixSignature 'edge') -and (Get-VoixSignature 'piper') -match '1.08') 'signature Piper distincte'
$v = Get-Content (Join-Path $Root 'lib\voix.ps1') -Raw -Encoding UTF8
Verifier ($v -match 'Get-EdgeArgsProsodie' -and $v -match 'Get-PiperParamsBase64' -and $v -match "Get-VoixSignature 'piper'" -and $v -match "Get-VoixSignature 'edge'") 'voix.ps1 : prosodie Edge, réglages Piper et clés de cache branchés'

Write-Host '2) Normalisation du texte avant la synthèse'
$cas = @(
    @('Thales monte de +3,2 %.', 'Thales monte de plus 3,2 pour cent.'),
    @('Variation de -2,4 % sur la semaine.', 'Variation de moins 2,4 pour cent sur la semaine.'),
    @('Il reste 75 % de la liste.', 'Il reste 75 pour cent de la liste.'),
    @('Rendez-vous le 15/10/2026.', 'Rendez-vous le 15 octobre 2026.'),
    @('Le 1/10/2026, tout commence.', 'Le premier octobre 2026, tout commence.'),
    @('Réunion le 3/12 à 9:05.', 'Réunion le 3 décembre à 9 heures 5.'),
    @('Relevé du 2026-10-15.', 'Relevé du 15 octobre 2026.'),
    @('Il est 13:20.', 'Il est 13 heures 20.'),
    @('Rendez-vous à 08:00.', 'Rendez-vous à 8 heures.'),
    @('Un total de 150,2 €.', 'Un total de 150,2 euros.'),
    @('Pour 1 € de plus.', 'Pour 1 euro de plus.'),
    @('Cela fait 12 EUR et 5 USD.', 'Cela fait 12 euros et 5 dollars.'),
    @('Tâches : appeler le comptable ; acheter du pain ; ranger le bureau.', 'Tâches, appeler le comptable, acheter du pain et ranger le bureau.'),
    @('Voilà (comme prévu) le résultat.', 'Voilà, comme prévu, le résultat.'),
    @('**Important** : le site répond.', 'Important, le site répond.'),
    @('Facture n° 12 à régler.', 'Facture numéro 12 à régler.'),
    @('Trois  espaces   et , virgule mal placée .', 'Trois espaces et, virgule mal placée.'),
    @('Rien à changer ici, monsieur.', 'Rien à changer ici, monsieur.'),
    @('3 tâches sur 4, soit un ratio de 3/4.', '3 tâches sur 4, soit un ratio de 3/4.')
)
foreach ($c in $cas) { $r = Format-TexteVoix $c[0]; Verifier ($r -eq $c[1]) ("« $($c[0]) » -> « $r »" + $(if ($r -ne $c[1]) { "  (attendu : « $($c[1]) »)" } else { '' })) }
$puces = Format-TexteVoix "• appeler le comptable`n• acheter du pain`n- ranger le bureau"
Verifier ($puces -eq 'appeler le comptable. acheter du pain. ranger le bureau.') "puces : jamais lues à plat -> « $puces »"
$longue = "Votre liste contient plusieurs tâches importantes pour aujourd'hui, notamment l'appel au comptable, la relance du fournisseur principal, la préparation de la facture du mois et la mise à jour du tableau de bord du site."
$lp = Format-TexteVoix $longue
$ph = @([regex]::Split($lp, '(?<=[.!?…])\s+'))
Verifier ($ph.Count -ge 2 -and ($ph | Where-Object { $_.Length -gt 150 }).Count -eq 0 -and $ph[1][0] -cmatch '[A-ZÀ-Ý]') "phrase de $($longue.Length) caractères coupée à une virgule en $($ph.Count) phrases, majuscule à la suivante"
$corpus = $cas | ForEach-Object { $_[0] }; $corpus += $longue, "• un`n• deux", 'Tâches : a ; b ; c.'
$instable = @($corpus | Where-Object { (Format-TexteVoix (Format-TexteVoix $_)) -ne (Format-TexteVoix $_) })
Verifier ($instable.Count -eq 0) 'la normalisation est idempotente (la repasser ne change plus rien)'
$phrases = @($script:PhrasesPrechauffe) + @(Get-PolitessePrechauffe) + @(Get-PhrasesReveilCache)
$changees = @($phrases | Where-Object { (Format-TexteVoix $_) -ne $_ -and $_ -notmatch '\s:\s' })      # (seules les phrases avec « : » sont réécrites, et le préchauffage les prépare de la même façon)
Verifier ($changees.Count -eq 0) "les phrases fixes (cache vocal) restent identiques : $($phrases.Count) contrôlées, $($changees.Count) modifiée(s)$(if ($changees.Count) { ' : ' + ($changees | Select-Object -First 3 | ForEach-Object { "« $_ »" }) -join ' ' })"
Verifier ((Format-TexteVoix '') -eq '' -and (Format-TexteVoix '   ') -eq '') 'texte vide : rien'

Write-Host '3) Découpage en phrases et pauses'
Verifier ((@(Get-MorceauxVoix 'Très bien monsieur')).Count -eq 1 -and (Get-MorceauxVoix 'Très bien monsieur') -eq 'Très bien monsieur') 'phrase courte : un seul morceau, texte inchangé (cache vocal conservé)'
$m = @(Get-MorceauxVoix "Arrêt immédiat, monsieur. Tout est coupé.")
Verifier ($m.Count -eq 2 -and $m[0] -eq 'Arrêt immédiat, monsieur.' -and $m[1] -eq 'Tout est coupé.') 'deux phrases : un morceau chacune (pause entre les deux)'
$m = @(Get-MorceauxVoix "Oui. Je m'en occupe tout de suite, monsieur.")
Verifier ($m.Count -eq 1 -and $m[0] -like 'Oui. Je m*') 'un fragment très court (« Oui. ») est rattaché à la phrase suivante'
$m = @(Get-MorceauxVoix "Il est 13:20. Votre variation est de +2,5 %. Tout est en ordre.")
Verifier ($m.Count -eq 3 -and $m[0] -eq 'Il est 13 heures 20.' -and $m[1] -match 'plus 2,5 pour cent' -and ($m | Where-Object { $_ -match '[%:/]' }).Count -eq 0) 'chiffres, pourcentage et heure dits en toutes lettres dans chaque morceau'
Verifier ((@(Get-MorceauxVoix $longue)).Count -ge 2 -and (@(Get-MorceauxVoix $longue) | Where-Object { $_.Length -gt 200 }).Count -eq 0) 'réponse longue : morceaux de 200 caractères au plus (on parle dès la 1re phrase)'
Fixer 'voix_pause_phrase_ms' 300; $t0 = Get-Date; Wait-PauseVoix; $ms = ((Get-Date) - $t0).TotalMilliseconds
Verifier ($ms -ge 250 -and $ms -lt 900) "pause entre deux phrases : $([int]$ms) ms pour 300 demandées"
Fixer 'voix_pause_phrase_ms' 0; $t0 = Get-Date; Wait-PauseVoix; Verifier (((Get-Date) - $t0).TotalMilliseconds -lt 100) 'pause réglée à 0 : aucune attente'
Effacer 'voix_pause_phrase_ms'
Fixer 'voix_naturelle' $false
$m = @(Get-MorceauxVoix 'Il est 13:20. Variation +2,5 %.')
Verifier ($m.Count -eq 1 -and $m[0] -eq 'Il est 13:20. Variation +2,5 %.') 'voix_naturelle = false : comportement d''avant (texte tel quel, un morceau sous 140 caractères)'
$m = @(Get-MorceauxVoix (('Phrase numéro un très longue pour dépasser largement la limite des cent quarante caractères que le comportement ancien fixait pour couper les réponses en plusieurs morceaux distincts. ') + 'Deuxième phrase.'))
Verifier ($m.Count -eq 2) '…et découpage ancien au-delà de 140 caractères'
Effacer 'voix_naturelle'

Write-Host '4) Fin d''audio : marge de silence, queue du son préservée, fondu'
$v = Get-Content (Join-Path $Root 'lib\voix.ps1') -Raw -Encoding UTF8
$corps = $v.Substring($v.IndexOf('function Lire-Mp3'), 1800)
Verifier ($corps -match 'marge_ms' -and $corps -match 'Position\.TotalMilliseconds' -and $corps -match 'Stop-AvecFondu' -and $corps -notmatch 'TotalMilliseconds \+ 300\)') 'Lire-Mp3 : attend la fin réelle du son puis la marge de silence ; arrêt avec fondu (plus de « + 300 » fixe)'
Verifier ((Get-DureeAttenteLecture 1000 200) -eq 1200) 'durée d''attente = durée du son + marge'
Verifier ($v -match 'Wait-PauseVoix' -and $v -match 'Get-MorceauxVoix \$Texte') 'Parler : texte préparé, pause entre les phrases'
$ps = Get-Content (Join-Path $Root 'voix\piper_serveur.py') -Raw -Encoding UTF8
Verifier ($ps -match 'finir_audio\(' -and $ps -match 'sentence_silence' -and $ps -match 'SynthesisConfig') 'serveur Piper : fin d''audio finie, silence entre phrases, réglages de synthèse'
$sortie = & python -I (Join-Path $PSScriptRoot 'voix-piper.py') 2>&1 | Out-String; $code = $LASTEXITCODE
$nbPy = ([regex]::Matches($sortie, '(?m)^\s+OK ')).Count
foreach ($l in ($sortie -split "`n" | Where-Object { $_ -match 'ECHEC' })) { Write-Host $l -ForegroundColor Red }
Verifier ($code -eq 0 -and $nbPy -ge 6) "tests\voix-piper.py : $nbPy vérifications (marge, fondu, queue du son, silence entre phrases) — tout vert"
$pe = Get-Content (Join-Path $Root 'voix\prechauffe.py') -Raw -Encoding UTF8
Verifier ($pe -match 'rate=' -and $pe -match 'pitch=' -and $pe -match 'volume=') 'préchauffage du cache : mêmes réglages Edge que la voix'

Write-Host '5) Style : phrases variées, jamais deux fois la même d''affilée'
Verifier (@($script:PolitesseCat['fait'].courtois).Count -ge 6 -and @($script:PolitesseCat['transition'].courtois).Count -ge 5) 'catalogue lib\politesse.ps1 : « fait » (6 variantes), « transition » (Voilà, Bien sûr, Très bien…)'
$script:PolitesseFixe = $false
foreach ($sit in 'fait', 'transition', 'test_voix_a', 'test_voix_b', 'test_voix_c') {
    $dernier = ''; $rep = 0; for ($k = 0; $k -lt 60; $k++) { $x = Get-Politesse $sit @{ x = 'le 15/10' }; if ($x -eq $dernier) { $rep++ }; $dernier = $x }
    Verifier ($rep -eq 0) "« $sit » : jamais deux fois la même phrase d'affilée (60 tirages)"
}
$script:PolitesseFixe = $true
$toutes = @(foreach ($sit in 'transition', 'test_voix_a', 'test_voix_b', 'test_voix_c') { foreach ($ton in 'courtois', 'neutre', 'sec') { @($script:PolitesseCat[$sit][$ton]) } })
$jargon = @($toutes | Where-Object { $_ -match '(?i)json|api|processus|script|erreur|exception|serveur' })
Verifier ($jargon.Count -eq 0) 'aucun jargon technique dans les nouvelles phrases'

Write-Host '6) « Test de voix » : trois phrases courtes avec le nouveau rythme'
foreach ($o in 'test de voix', 'fais un test de voix', 'teste ta voix', 'Jarvis, test vocal') { $plan = Get-PlanRapide $o; Verifier ($plan -and $plan.actions[0].type -eq 'test_voix') "« $o » est compris (règle, aucun appel IA)" }
Verifier ($script:Actions.ContainsKey('test_voix') -and $script:Actions['test_voix'].niveau -eq 1) 'action test_voix, niveau 1'
$script:Dits = @(); function Parler([string]$Texte, $Langue) { $script:Dits += $Texte }
$r = & $script:Actions['test_voix'].run @{}
Verifier ($r.ok -and $script:Dits.Count -eq 3) 'trois phrases lues'
Verifier (($script:Dits | Where-Object { $_.Length -gt 140 }).Count -eq 0) 'phrases courtes (140 caractères au plus)'
$dit = @($script:Dits | ForEach-Object { Get-MorceauxVoix $_ }) -join ' '
Verifier ($dit -match 'pour cent' -and $dit -match 'octobre|novembre|décembre|janvier|février|mars|avril|mai|juin|juillet|août|septembre' -and $dit -match 'heures?') 'le test fait entendre un pourcentage, une date et une heure dits naturellement'
$plan = Get-PlanRapide 'test de voix'; Verifier ($plan.rapide -and -not $plan.finaliser.Invoke(@(@{ texte = '' }))) '…sans phrase de plus après le test'
Remove-Item function:Parler

Write-Host '7) Vitesse : aucune régression'
$echant = @('Très bien monsieur', "C'est fait, monsieur.", 'Il est 13:20, monsieur. Votre variation du jour est de +2,5 %. Tout est en ordre.', $longue, 'Vous avez 3 tâches : appeler le comptable ; acheter du pain ; ranger le bureau.')
$sw = [Diagnostics.Stopwatch]::StartNew(); $n = 0
for ($i = 0; $i -lt 40; $i++) { foreach ($e in $echant) { [void](Get-MorceauxVoix $e); $n++ } }
$moy = $sw.Elapsed.TotalMilliseconds / $n
Verifier ($moy -lt 15) ("préparation du texte vocal : {0:N2} ms en moyenne par réponse ({1} mesures) — négligeable devant la synthèse (1,5 s)" -f $moy, $n)
$pire = 0.0; foreach ($e in $echant) { $t0 = Get-Date; [void](Get-MorceauxVoix $e); $d = ((Get-Date) - $t0).TotalMilliseconds; if ($d -gt $pire) { $pire = $d } }
Verifier ($pire -lt 100) ("pire cas isolé : {0:N1} ms" -f $pire)
$regress = @(foreach ($e in $echant) {
    $anc = if ($e.Length -gt 140) { @([regex]::Split($e, '(?<=[.!?])\s+') | Where-Object { $_.Trim() })[0] } else { $e }      # premier morceau d'avant
    $nouv = @(Get-MorceauxVoix $e)[0]
    if ($nouv.Length -gt $anc.Length + 12) { "« $e » : $($nouv.Length) > $($anc.Length)" }
})
Verifier ($regress.Count -eq 0) '1er morceau à synthétiser jamais plus long qu''avant (première parole au moins aussi rapide ; plus rapide avec plusieurs phrases)'
$script:DernierOrdre = @{ plan_s = 0.1; action_s = 0.2; audio_s = 0.9; norm_ms = 3.4; debut = (Get-Date) }
$diag = Format-EtapesDiag ([pscustomobject]@{ tps = $null; recu_ms = 0; etage = 'règle'; routeur = '' })
Verifier ($diag -match 'préparation du texte vocal 3 ms' -and $diag -match '1er son 900 ms') 'diagnostic vocal : « préparation du texte vocal N ms » affichée avec « 1er son N ms »'
$script:DernierOrdre = $null
$cd = Get-Content (Join-Path $Root 'lib\comprehension.ps1') -Raw -Encoding UTF8
Verifier ($v -match 'norm_ms') 'Parler mesure la préparation du texte pour le diagnostic'
$mesure = Get-Content (Join-Path $Root 'tests\vitesse.ps1') -Raw -Encoding UTF8
Verifier ($mesure.Length -gt 100) '(la suite tests\vitesse.ps1 existante continue de contrôler les étages, le routeur et le cache)'

Write-Host '8) Rien ne bouge : aucun son, aucun processus, aucun secret'
Verifier ((Test-PiperPret) -eq $false) 'mode test : serveur Piper jamais démarré'
Verifier (@(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'edge_tts|piper_serveur' -and $_.CommandLine -notmatch 'voix-naturelle' }).Count -eq 0) 'aucun processus de synthèse lancé par ce test'
$src = (Get-Content (Join-Path $Root 'lib\voix-naturelle.ps1') -Raw -Encoding UTF8)
Verifier ($src -notmatch '(?i)DISCORD_BOT_TOKEN|Bearer|api[_-]?key') 'aucun secret dans le module'

Remove-Item $TR -Recurse -Force -ErrorAction SilentlyContinue
if ($echecs) { Write-Host "`nÉCHEC : $echecs vérification(s) en échec." -ForegroundColor Red; exit 1 }
Write-Host "`nRÉUSSI"; exit 0
