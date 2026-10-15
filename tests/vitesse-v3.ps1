# Test SILENCIEUX de la VITESSE V3 : diagnostic détaillé par étape, mesure sur 20 phrases, fin de phrase adaptative (réglages), action AVANT la parole, accusé instantané (cache, jamais de
# synthèse à la demande), phrase d'attente, réponses parlées courtes + « détaille », réponse de Claude en flux (analyse du flux simulée), préchauffage, routeur plus léger (banc, non adopté).
# Aucun son, aucun Ollama, aucun Claude, aucun micro. Code de sortie 0 = réussi.
$ErrorActionPreference = 'Stop'
$env:JARVIS_TEST = '1'
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $Root 'lib\journal.ps1')
$TR = Join-Path $env:TEMP ('jarvis-test-' + [guid]::NewGuid().ToString('N').Substring(0, 8)); New-Item -ItemType Directory $TR, "$TR\memoire", "$TR\logs", "$TR\sounds\cache" | Out-Null; $script:JarvisRoot = $TR
"# To-do de Liam`r`n- [ ] Envoyer la facture" | Set-Content "$TR\memoire\todo.md" -Encoding UTF8; '# Notes' | Set-Content "$TR\memoire\notes.md" -Encoding UTF8; '# R' | Set-Content "$TR\memoire\resume.md" -Encoding UTF8
$Config = Get-Content $(if ($env:JARVIS_CONFIG -and (Test-Path $env:JARVIS_CONFIG)) { $env:JARVIS_CONFIG } else { Join-Path $Root 'config.json' }) -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($l in 'voix', 'business', 'permissions', 'actions', 'coffre', 'entrees', 'ecrans', 'tableau', 'visage', 'sons', 'raccourcis', 'cerveau', 'cerveau-local', 'veille', 'memoire', 'rapide', 'discretion', 'modejeu', 'competences', 'marche', 'priorite', 'comprehension', 'routeur', 'pc', 'bureau', 'salle-marche', 'matin') { . (Join-Path $Root "lib\$l.ps1") }
$script:JarvisRoot = $TR
$script:PolitesseFixe = $true
$echecs = 0
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }
function Fixer([string]$cle, $val) { if ($Config.PSObject.Properties[$cle]) { $Config.$cle = $val } else { $Config | Add-Member -NotePropertyName $cle -NotePropertyValue $val } }
function Effacer([string]$cle) { if ($Config.PSObject.Properties[$cle]) { $Config.PSObject.Properties.Remove($cle) } }
$vraie = Get-Content (Join-Path $Root 'config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($k in 'voix_naturelle', 'voix_edge_rate', 'voix_edge_pitch', 'voix_marge_fin_ms', 'silence_rapide_ms', 'fin_adaptative', 'reponses_courtes', 'accuse_instantane', 'claude_flux', 'voix_moteur') { Effacer $k }
$Config | Add-Member -NotePropertyName voix_moteur -NotePropertyValue 'edge'
$script:Actif = $true; $script:ModeJeu = $false; $script:ContexteVoix = 'reponse'      # (comme pendant un ordre : la voix de réponse est permise)

Write-Host '1) Diagnostic vocal : chaque étape, le total, l''étape la plus lente'
$script:DernierOrdre = @{ plan_s = 0.9; action_s = 1.0; audio_s = 1.4; norm_ms = 4.0; synth_ms = 380.0; regle_ms = 3.0; routeur_ms = 850.0; claude_ms = $null; debut = (Get-Date) }
$t = [pscustomobject]@{ silence_ms = 760; reco_ms = 240; appareil = 'cuda'; t_emis = 0; silence_cfg_ms = 1500; silence_rapide_ms = 700; fin_rapide = $true }
$d = Format-EtapesDiag ([pscustomobject]@{ tps = $t; recu_ms = 0; etage = 'routeur'; routeur = 'ok en 850 ms' })
Verifier ($d -match 'fin de phrase 760 ms \(attendu 700 ms : fermeture rapide\)' -and $d -match 'reconnaissance 240 ms \(cuda\)') 'fin de parole : durée réelle du silence ET silence attendu (fermeture rapide)'
Verifier ($d -match 'règle 3 ms' -and $d -match 'routeur 850 ms' -and $d -match 'action 1000 ms' -and $d -match 'préparation du texte vocal 4 ms' -and $d -match 'synthèse 380 ms' -and $d -match '1er son 1400 ms') 'règle, routeur, action, préparation du texte, synthèse, premier son'
Verifier ($d -match 'TOTAL fin de parole → 1er son : 2[.,]4 s' -and $d -match 'étape la plus lente : routeur \(850 ms\)') 'total (2,4 s) et étape la plus lente (ici le routeur : 850 ms)'
$script:DernierOrdre = @{ plan_s = 6.2; action_s = 6.3; audio_s = 7.0; claude_ms = 6100.0; regle_ms = 2.0; norm_ms = 3.0; synth_ms = 400.0; debut = (Get-Date) }
$t2 = [pscustomobject]@{ silence_ms = 1500; reco_ms = 300; appareil = 'cpu'; t_emis = 0; silence_cfg_ms = 1500 }
$d = Format-EtapesDiag ([pscustomobject]@{ tps = $t2; recu_ms = 0; etage = 'claude'; routeur = '' })
Verifier ($d -match 'Claude 6100 ms' -and $d -match 'étape la plus lente : Claude' -and $d -match 'fin de phrase 1500 ms \(attendu 1500 ms\)') 'une question ouverte : l''étape Claude ressort comme la plus lente'
$script:DernierOrdre = $null
# enregistrement du diagnostic
$script:DernierOrdre = @{ plan_s = 0.5; action_s = 0.6; audio_s = 1.2; regle_ms = 2.0; routeur_ms = 450.0; norm_ms = 3.0; synth_ms = 300.0; debut = (Get-Date) }
Save-DiagTrace ([pscustomobject]@{ h = '12:00:00'; brut = 'test'; wake = $true; mot = ''; etage = 'routeur'; routeur = 'ok'; modele_ms = $null; tps = $t; intention = 'x'; resultat = 'ok'; moteur = 'whisper'; etapes = '' }) $true
$f = Get-ChildItem (Get-DossierLogs) -Filter 'diag-voix-*.jsonl' | Select-Object -First 1
$l = Get-Content $f.FullName -Encoding UTF8 | ConvertFrom-Json
Verifier ($l.ms.regle -eq 2 -and $l.ms.routeur -eq 450 -and $l.ms.prep -eq 3 -and $l.ms.synth -eq 300 -and $l.ms.silence -eq 760 -and $l.ms.reco -eq 240 -and $l.ms.son -eq 1200) 'le diagnostic enregistré (diag-voix-*.jsonl) garde le temps de chaque étape'
$script:DernierOrdre = $null
# mesure sur 20 phrases
$mk = { param($sil, $reco, $reg, $rout, $cl, $act, $prep, $syn, $son) [pscustomobject]@{ etage = 'x'; ms = [pscustomobject]@{ silence = $sil; reco = $reco; regle = $reg; routeur = $rout; claude = $cl; act = $act; prep = $prep; synth = $syn; son = $son } } }
$phr = @(1..19 | ForEach-Object { & $mk 1500 250 2 $null $null 30 4 350 900 }) + @(& $mk 1500 250 2 $null 7000 30 4 350 8000)
$r = Get-MesureVitesse $phr
Verifier ($r.n -eq 20 -and [math]::Abs($r.mediane_s - 2.65) -lt 0.01 -and [math]::Abs($r.pire_s - 9.75) -lt 0.01) "médiane et pire cas sur 20 phrases : $($r.mediane_s) s / $($r.pire_s) s"
Verifier ($r.dominante.Key -eq 'fin de phrase' -and $r.dominante.Value -eq 1500) 'étape dominante : le silence de fin de phrase (moyenne 1500 ms)'
$dir = Get-DossierLogs; $lignes = @($phr | ForEach-Object { $_ | ConvertTo-Json -Compress -Depth 4 })
Set-Content (Join-Path $dir 'diag-voix-2099-01-01.jsonl') $lignes -Encoding UTF8
$res = & $script:Actions['mesure_vitesse'].run @{}
Verifier ($res.ok -and $res.texte -match 'Sur les 20 dernières phrases : médiane 2,7 s, pire cas 9,8 s' -and $res.texte -match 'Étape dominante : fin de phrase' -and $res.texte -match 'reconnaissance') '« mesure la vitesse » : 20 dernières phrases, médiane, pire cas, étape dominante'
Remove-Item (Join-Path $dir 'diag-voix-2099-01-01.jsonl') -Force
Verifier ((Get-PlanRapide 'mesure la vitesse').actions[0].type -eq 'mesure_vitesse') '« mesure la vitesse » est compris par une règle'

Write-Host '2) Fin de phrase adaptative : réglages et arguments de l''écoute'
$mc = Get-MicroConfig
Verifier ($mc.silence_rapide -eq 0.7 -and $mc.adaptatif -eq $true) 'par défaut : fermeture rapide à 0,7 s, adaptative'
$a = Get-ArgsEcoute 'ecoute.py'
Verifier ($a -match '--silence-fin 1\.5 --silence-courte 0\.6 --duree-max 30 --silence-rapide 0\.7 --adaptatif 1') 'arguments : silence long 1,5 s conservé, --silence-rapide 0.7, --adaptatif 1'
Fixer 'silence_rapide_ms' 100; Verifier ((Get-MicroConfig).silence_rapide -eq 0.5) 'plancher de la fermeture rapide : 500 ms'
Fixer 'silence_rapide_ms' 5000; Verifier ((Get-MicroConfig).silence_rapide -eq 1.0) 'plafond : 1000 ms'
Fixer 'silence_rapide_ms' 800; Verifier ((Get-ArgsEcoute 'ecoute.py') -match '--silence-rapide 0\.8') 'réglable (800 ms)'
Fixer 'fin_adaptative' $false; Verifier ((Get-ArgsEcoute 'ecoute.py') -match '--adaptatif 0' -and (Get-MicroConfig).adaptatif -eq $false) 'fin_adaptative = false : ancien comportement (--adaptatif 0)'
foreach ($k in 'silence_rapide_ms', 'fin_adaptative') { Effacer $k }
Verifier ($vraie.silence_rapide_ms -eq 700 -and $vraie.fin_adaptative -eq $true) 'config.json : silence_rapide_ms = 700, fin_adaptative = true'
$py = Get-Content (Join-Path $Root 'voix\ecoute.py') -Raw -Encoding UTF8
Verifier ($py -match 'def phrase_semble_complete' -and $py -match 'spec_texte' -and $py -match 'voix_max_rapide') 'écoute : transcription d''essai réutilisée, phrase longue protégée (tests\silence.py : 15 scénarios)'

Write-Host '3) Action D''ABORD, puis la parole'
$script:GPRreel = ${function:Get-PlanRapide}; function Get-PlanRapide([string]$o) { $null }      # (les plans de ces tests viennent du « cerveau » simulé, pas des règles)
$script:Dits = @(); $script:Chrono = @(); $script:AppelsGetPlan = 0
function Parler([string]$Texte, $Langue) { $script:Dits += $Texte; $script:Chrono += "dit:$Texte"; Add-Conv 'jarvis' $Texte; Set-AudioDebut }
function Get-ReponseOrale([string]$o, [string]$r) { 'Résumé.' }
function Resolve-Routeur([string]$o) { $script:RouteurEtat = 'desactive'; $null }
function Get-ModeCerveau { 'claude' }
$script:PlanCerveau = $null
function Get-Plan([string]$o) { $script:AppelsGetPlan++; $script:VoieCerveau = 'claude'; $script:PlanCerveau | Select-Object * }      # (copie : Invoke-OrdreCorps modifie son plan)
$script:Actions['note_ajouter'].run = { param($a) $script:Chrono += 'action:note'; Rep $true 'Note enregistrée.' }
$script:PlanCerveau = [pscustomobject]@{ dit = 'Très bien, je note cela.'; langue = 'fr'; actions = @([pscustomobject]@{ type = 'note_ajouter'; texte = 'acheter du pain' }) }
Invoke-Ordre 'garde en mémoire ce détail précis sur le pain du boulanger du coin'
$i1 = $script:Chrono.IndexOf('action:note'); $i2 = $script:Chrono.IndexOf('dit:Très bien, je note cela.')
Verifier ($i1 -ge 0 -and $i2 -gt $i1) 'plan de Claude / du routeur avec une action : l''action est exécutée AVANT la phrase annoncée'
$script:Chrono = @(); $script:Actions['pc_veille'].niveau = 2
function Confirmer([string]$q) { $script:Chrono += 'confirmer'; $false }
$script:PlanCerveau = [pscustomobject]@{ dit = 'Je mets le PC en veille.'; langue = 'fr'; actions = @([pscustomobject]@{ type = 'pc_veille' }) }
Invoke-Ordre 'fais dormir la machine pendant la nuit entière'
Verifier ($script:Chrono.IndexOf('dit:Je mets le PC en veille.') -ge 0 -and $script:Chrono.IndexOf('dit:Je mets le PC en veille.') -lt $script:Chrono.IndexOf('confirmer')) 'action sensible (confirmation) : la phrase l''annonce AVANT la question'
Remove-Item function:Confirmer
$script:Chrono = @(); $script:PlanCerveau = [pscustomobject]@{ dit = 'Il fait beau.'; langue = 'fr'; actions = @() }
Invoke-Ordre 'dis-moi quelque chose de gentil pour la journée'
Verifier ($script:Dits -contains 'Il fait beau.' -and $script:Chrono.Count -eq 1) 'réponse sans action : dite tout de suite'
$rp = Get-Content (Join-Path $Root 'lib\cerveau.ps1') -Raw -Encoding UTF8
Verifier ($rp -match 'On agit D''ABORD, on parle ensuite' -and $rp -match '\$ditApres') 'cerveau.ps1 : action avant la parole pour tous les étages'

Write-Host '4) Accusé instantané pré-enregistré (jamais de synthèse à la demande)'
$phrasesAccuse = @($script:PolitesseCat['accuse'].courtois)
Verifier ($phrasesAccuse.Count -ge 3 -and ($phrasesAccuse | Where-Object { $_.Length -gt 30 }).Count -eq 0) 'catalogue « accuse » : « Très bien, monsieur. », « Voilà. », « Un instant, monsieur. » (phrases courtes)'
$planOuvre = [pscustomobject]@{ actions = @([pscustomobject]@{ type = 'ouvrir_app'; nom = 'chrome' }) }
$planVol = [pscustomobject]@{ actions = @([pscustomobject]@{ type = 'volume'; delta = 10 }) }
$script:DernierAccuse = ''
Verifier (-not (Start-AccuseInstantane $planOuvre) -and $script:DernierAccuse -eq '') 'aucun enregistrement en cache : pas d''accusé (rien n''est synthétisé pour cela)'
foreach ($ph in $phrasesAccuse) { $seg = @(Get-MorceauxVoix $ph)[0]; $c = Get-CheminTtsCache "$($Config.voix.fr)|$(Get-VoixSignature 'edge')" $seg; [IO.File]::WriteAllBytes($c, (New-Object byte[] 2000)) }
Verifier ((Start-AccuseInstantane $planOuvre) -and $script:DernierAccuse -in $phrasesAccuse) "enregistrement présent : accusé choisi dans le catalogue (« $script:DernierAccuse »)"
Verifier (-not (Start-AccuseInstantane $planVol)) 'réglage évident (volume) : pas d''accusé'
Verifier (-not (Start-AccuseInstantane ([pscustomobject]@{ actions = @() }))) 'sans action (conversation) : pas d''accusé'
$script:Actif = $false; Verifier (-not (Start-AccuseInstantane $planOuvre)) 'sourdine : aucun accusé'; $script:Actif = $true
$script:ModeJeu = $true; Verifier (-not (Start-AccuseInstantane $planOuvre)) 'mode jeu : aucun accusé'; $script:ModeJeu = $false
$script:CanalDiscord = 'jarvis'; Verifier (-not (Start-AccuseInstantane $planOuvre)) 'ordre venu de Discord : aucun accusé'; $script:CanalDiscord = $null
Fixer 'accuse_instantane' $false; Verifier (-not (Start-AccuseInstantane $planOuvre)) 'accuse_instantane = false : désactivé'; Effacer 'accuse_instantane'
$seq = @(); for ($k = 0; $k -lt 40; $k++) { [void](Start-AccuseInstantane $planOuvre); $seq += $script:DernierAccuse }
$rep = 0; for ($k = 1; $k -lt $seq.Count; $k++) { if ($seq[$k] -eq $seq[$k - 1]) { $rep++ } }
$script:PolitesseFixe = $false; $seq = @(); for ($k = 0; $k -lt 40; $k++) { [void](Start-AccuseInstantane $planOuvre); $seq += $script:DernierAccuse }; $rep = 0; for ($k = 1; $k -lt $seq.Count; $k++) { if ($seq[$k] -eq $seq[$k - 1]) { $rep++ } }; $script:PolitesseFixe = $true
Verifier ($rep -eq 0) 'jamais le même accusé deux fois de suite (40 tirages)'
$vx = Get-Content (Join-Path $Root 'lib\voix.ps1') -Raw -Encoding UTF8
Verifier ($vx -match 'Wait-AccuseFini' -and (Get-Content (Join-Path $Root 'lib\cerveau.ps1') -Raw -Encoding UTF8) -match 'Start-AccuseInstantane \$plan') 'l''accusé est joué sans attendre ; Parler le laisse finir avant de dire la suite'
Verifier ((Get-PolitessePrechauffe) -contains 'Voilà.' -and (Get-PolitessePrechauffe) -contains 'Un instant, monsieur.') 'les accusés sont dans le préchauffage du cache vocal'
Get-ChildItem "$TR\sounds\cache" | Remove-Item -Force

Write-Host '5) Question ouverte : phrase d''attente immédiate'
$script:Dits = @(); $script:ReflexionAnnoncee = $false; Annoncer-Reflexion
Verifier ($script:Dits.Count -eq 1 -and (Test-PhrasePolitesse 'attente' $script:Dits[0])) "phrase d'attente du catalogue : « $($script:Dits[0]) »"
$script:ReflexionAnnoncee = $false

Write-Host '6) Réponses parlées courtes ; le détail sur demande'
$long = "Voici la première idée, monsieur. Voici la deuxième. Et une troisième encore. Puis une quatrième, par souci de complétude. Enfin une cinquième pour conclure."
$lim = Limit-DitVocal $long
Verifier ($lim.coupe -and ([regex]::Split($lim.court, '(?<=[.!?…])\s+')).Count -le 2 -and $lim.court.Length -le 245 -and $lim.complet -eq $long) 'réponse longue : 2 phrases à voix haute, texte complet conservé'
Verifier (-not (Limit-DitVocal 'Très bien, monsieur.').coupe -and (Limit-DitVocal 'Une phrase. Deux phrases.').court -eq 'Une phrase. Deux phrases.') '1 à 2 phrases courtes : inchangées'
$un = Limit-DitVocal ('Un mot, ' * 80); Verifier ($un.court.Length -le 245 -and $un.coupe) 'une seule phrase énorme : coupée à 240 caractères'
$script:Dits = @(); $script:PlanCerveau = [pscustomobject]@{ dit = $long; langue = 'fr'; actions = @() }
Invoke-Ordre 'raconte-moi plein de choses sur ta journée de travail'
Verifier ($script:Dits.Count -eq 1 -and $script:Dits[0] -notmatch 'cinquième' -and $script:Dits[0] -match 'première') 'ordre vocal : seulement la version courte est dite'
Verifier ($script:DernierDitComplet -eq $long -and (Get-ConversationRecente 5 | Where-Object { "$($_.texte)" -match 'Détail : .*cinquième' }).Count -ge 1) 'le détail complet est gardé et affiché à l''écran (panneau de conversation)'
$script:Dits = @()
$r = & $script:Actions['detail_reponse'].run @{}
Verifier ($r.ok -and $r.texte -match 'détail' -and (Get-ConversationRecente 3 | Where-Object { "$($_.texte)" -eq $long }).Count -ge 1) '« détaille » : le texte complet est affiché'
foreach ($o in 'détaille', 'donne-moi plus de détails', 'développe', 'dis-m''en plus', 'en dis plus') { Verifier ((& $script:GPRreel $o).actions[0].type -eq 'detail_reponse') "« $o » est compris (règle)" }
Verifier ((& $script:GPRreel 'détails du briefing').actions[0].type -eq 'briefing_details') '« détails du briefing » garde sa règle'
$script:CanalDiscord = 'jarvis'; $script:DiscordTampon = New-Object System.Collections.Generic.List[string]; $script:Dits = @()
$script:DiscordPumpActif = $false
Invoke-Ordre 'raconte-moi plein de choses sur ta journée de travail'
Verifier ($script:Dits.Count -ge 1 -and $script:Dits[0] -match 'cinquième') 'sur Discord : la réponse n''est jamais raccourcie (le détail y est déjà)'
$script:CanalDiscord = $null; $script:DiscordTampon = $null
Fixer 'reponses_courtes' $false; $script:Dits = @(); Invoke-Ordre 'raconte-moi plein de choses sur ta journée de travail'
Verifier ($script:Dits[0] -match 'cinquième') 'reponses_courtes = false : réponse entière à voix haute'
Effacer 'reponses_courtes'

Write-Host '7) Réponse de Claude en flux (claude_flux ; désactivée par défaut)'
Verifier ((Get-ClaudeFlux) -eq $false -and $vraie.claude_flux -eq $false) 'claude_flux = false par défaut : le fonctionnement actuel de Claude ne change pas'
$sim = @(
    '{"type":"system","subtype":"init"}',
    '{"type":"stream_event","event":{"type":"content_block_delta","delta":{"type":"text_delta","text":"{\"dit\":\"Il fait beau"}}}',
    '{"type":"stream_event","event":{"type":"content_block_delta","delta":{"type":"text_delta","text":" aujourd''hui, monsieur. Prenez"}}}',
    'pas du json',
    '{"type":"result","result":"{\"dit\":\"Il fait beau aujourd''hui, monsieur. Prenez un parapluie.\",\"actions\":[]}"}')
$fl = ConvertFrom-FluxClaude $sim
Verifier ($fl.texte -match '^\{"dit":"Il fait beau aujourd.hui, monsieur\. Prenez$' -and $fl.fini -and $fl.final -match 'Prenez un parapluie') 'flux : texte cumulé, résultat final, ligne illisible ignorée'
Verifier ((Get-PremierePhraseDit $fl.texte) -eq "Il fait beau aujourd'hui, monsieur.") 'première phrase extraite dès qu''elle est terminée et suivie d''une autre'
Verifier ($null -eq (Get-PremierePhraseDit '{"dit":"Il fait beau aujourd''hui') -and $null -eq (Get-PremierePhraseDit '{"actions":[]') -and $null -eq (Get-PremierePhraseDit '{"dit":"Ok.') ) 'phrase pas encore terminée, ou trop courte : rien n''est dit'
Verifier ($null -eq (Get-PremierePhraseDit '{"dit":"Le cours est de 3.')) 'une décimale en cours (« 3. ») n''est pas une fin de phrase'
Verifier ((Get-PremierePhraseDit '{"dit":"Voilà la réponse complète, monsieur."}') -eq 'Voilà la réponse complète, monsieur.') 'une réponse d''une seule phrase, terminée : dite'
$script:DitPartiel = "Il fait beau aujourd'hui, monsieur."
Verifier ((Get-DitRestant "Il fait beau aujourd'hui, monsieur. Prenez un parapluie.") -eq 'Prenez un parapluie.' -and (Get-DitRestant "Il fait beau aujourd'hui, monsieur.") -eq '') 'ce qui reste à dire : la phrase déjà dite n''est pas répétée'
$script:DitPartiel = ''
# de bout en bout (Claude simulé)
Fixer 'claude_flux' $true; $script:Dits = @()
function Get-Plan([string]$o) { if ($script:SurPhraseClaude) { & $script:SurPhraseClaude "Il fait beau aujourd'hui, monsieur." }; $script:VoieCerveau = 'claude'; [pscustomobject]@{ dit = "Il fait beau aujourd'hui, monsieur. Prenez un parapluie."; langue = 'fr'; actions = @() } }
Invoke-Ordre 'quel temps fera-t-il demain dans la région de Lyon'
Verifier ($script:Dits.Count -eq 2 -and $script:Dits[0] -eq "Il fait beau aujourd'hui, monsieur." -and $script:Dits[1] -eq 'Prenez un parapluie.') 'flux : la 1re phrase est dite pendant que Claude écrit la suite, puis le reste (sans répétition)'
Effacer 'claude_flux'
$cl = Get-Content (Join-Path $Root 'lib\cerveau.ps1') -Raw -Encoding UTF8
Verifier ($cl -match 'stream-json' -and $cl -match 'SurPhraseClaude -and' -and $cl -match 'Get-ClaudeFlux') 'Invoke-Claude : les options de flux ne sont ajoutées que si claude_flux est activé'

Set-Item function:Get-PlanRapide $script:GPRreel      # règles réelles de nouveau
Write-Host '8) Modèles préchauffés, routeur plus léger, commandes du PC jamais chez Claude'
$mj = Get-Content (Join-Path $Root 'jarvis.ps1') -Raw -Encoding UTF8
Verifier ($mj -match 'Start-Ecoute; Start-PrechauffageTts' -and $mj -match "Get-VoixMoteur\) -eq 'piper'\) \{ \[void\]\(Test-PiperPret\)") 'au démarrage (hors sourdine) : écoute (Whisper chargé), cache vocal et serveur Piper préchauffés'
Verifier ((Get-Content (Join-Path $Root 'lib\cerveau-local.ps1') -Raw -Encoding UTF8) -match 'Start-OllamaChargement' -and (Get-Content (Join-Path $Root 'lib\raccourcis.ps1') -Raw -Encoding UTF8) -match 'Start-OllamaReveil|Start-OllamaChargement') 'modèle Ollama préchargé et gardé chaud (keep_alive) à l''activation'
$mr = Get-Content (Join-Path $Root 'tests\mesure-routeur.ps1') -Raw -Encoding UTF8
Verifier ($mr -match 'param\(\[string\]\$Modele' -and $mr -match '90 %') 'banc de précision du routeur : -Modele qwen2.5:3b (60 phrases) ; adopter seulement si au moins 90 % et au moins égal à l''actuel'
Verifier ($Config.ollama.modele -eq 'qwen2.5:7b' -and $vraie.ollama.modele -eq 'qwen2.5:7b') 'modèle du routeur inchangé (qwen2.5:7b) : un modèle plus léger n''est PAS adopté sans mesure réelle'
$script:AppelsGetPlan = 0; $script:PlanCerveau = [pscustomobject]@{ dit = 'x'; langue = 'fr'; actions = @() }
function Get-Plan([string]$o) { $script:AppelsGetPlan++; $script:VoieCerveau = 'claude'; $script:PlanCerveau | Select-Object * }      # (copie : Invoke-OrdreCorps modifie son plan)
foreach ($ph in 'ouvre le truc bizarre du bureau', 'mets le volume au niveau des étoiles', 'ferme la fenêtre qui gêne', 'baisse la luminosité de la lune') { $script:Dits = @(); Invoke-Ordre $ph }
Verifier ($script:AppelsGetPlan -eq 0) 'une commande du PC que ni la règle ni le routeur ne comprennent : jamais envoyée à Claude (demande de reformuler)'
$script:AppelsGetPlan = 0; Invoke-Ordre 'merci beaucoup'; Invoke-Ordre 'bonjour'
Verifier ($script:AppelsGetPlan -eq 0) 'politesse, salutations, to-do, heure... : règles locales, aucun appel à Claude'

Remove-Item $TR -Recurse -Force -ErrorAction SilentlyContinue
if ($echecs) { Write-Host "`nÉCHEC : $echecs vérification(s) en échec." -ForegroundColor Red; exit 1 }
Write-Host "`nRÉUSSI"; exit 0
