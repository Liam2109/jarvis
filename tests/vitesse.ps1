# Test SILENCIEUX de la VITESSE du cerveau et de la VOIX : ordre des étages (règle -> routeur -> Claude), jamais de commande du PC chez Claude, notes du diagnostic vocal,
# préchargement du modèle Ollama au réveil, voix d'homme par défaut. Aucun Ollama, aucun Claude, aucun son : tout est simulé. Code de sortie 0 = réussi.
$ErrorActionPreference = 'Stop'
$env:JARVIS_TEST = '1'
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $Root 'lib\journal.ps1')
$TR = Join-Path $env:TEMP ('jarvis-test-' + [guid]::NewGuid().ToString('N').Substring(0, 8)); New-Item -ItemType Directory $TR, "$TR\memoire", "$TR\logs" | Out-Null; $script:JarvisRoot = $TR
"# To-do de Liam`r`n- [ ] Envoyer la facture" | Set-Content "$TR\memoire\todo.md" -Encoding UTF8; '# Notes' | Set-Content "$TR\memoire\notes.md" -Encoding UTF8; '# R' | Set-Content "$TR\memoire\resume.md" -Encoding UTF8
$Config = Get-Content (Get-ConfigPath) -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($l in 'voix', 'business', 'permissions', 'actions', 'coffre', 'entrees', 'ecrans', 'tableau', 'visage', 'sons', 'raccourcis', 'cerveau', 'cerveau-local', 'veille', 'memoire', 'rapide', 'discretion', 'modejeu', 'marche', 'priorite', 'comprehension', 'routeur', 'competences', 'pc', 'bureau', 'matin', 'boucle') { . (Join-Path $Root "lib\$l.ps1") }
$script:JarvisRoot = $TR
$echecs = 0
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }
$script:Dits = @(); $script:AppelsGetPlan = 0; $script:PlanCerveau = $null; $script:Sequence = @(); $script:Ollama = $null; $script:AppelsOllama = 0; $script:ModeCerveau = 'local'
function Parler([string]$Texte, $Langue) { if ($script:Actif -ne $false -and $script:ModeJeu -ne $true) { $script:Dits += $Texte }; Add-Conv 'jarvis' $Texte; Set-AudioDebut }
function Get-Plan([string]$o) { $script:AppelsGetPlan++; $script:VoieCerveau = 'claude'; [pscustomobject]@{ dit = 'Réponse du cerveau.'; langue = 'fr'; actions = @() } }
function Get-ReponseOrale([string]$o, [string]$r) { 'Résumé.' }
function Get-ModeCerveau { $script:ModeCerveau }
function Invoke-Ollama([string]$s, [string]$u, [int]$t = 0) { $script:AppelsOllama++; $script:Ollama }
$script:Actif = $true; $script:ModeJeu = $false
foreach ($k in 'ouvrir_app', 'ouvrir_site', 'ouvrir_chemin', 'volume', 'luminosite', 'musique') { $script:Actions[$k].run = [scriptblock]::Create("param(`$a) `$script:Sequence += '$k'; Rep `$true (Get-Politesse 'silencieux')") }
$script:StartAppsCache = @('Discord', 'Steam', 'Google Chrome', 'Visual Studio Code', 'Microsoft Edge') | ForEach-Object { [pscustomobject]@{ Name = $_; AppID = "id.$_" } }
function Dit-Incompris { @($script:Dits | Where-Object { Test-PhrasePolitesse 'incompris' $_ }).Count -eq 1 }
function Ordre([string]$o) { $script:Dits = @(); $script:Sequence = @(); $script:AppelsGetPlan = 0; $script:AppelsOllama = 0; $script:DiagId = 0; $id = New-DiagSaisie $o 'clavier'; Invoke-Entree @{ src = 'clavier'; texte = $o; entendu = $false; diag = $id }; Get-DiagRecord $id }
$json = { param($d, $c, $acts) ConvertTo-Json -Compress ([ordered]@{ decision = $d; confiance = $c; resume = 'x'; actions = @($acts) }) }

Write-Host '1) Ordre des étages : règle, puis routeur, Claude seulement pour les questions ouvertes'
$r = Ordre 'ouvre discord'
Verifier ($r.etage -eq 'règle' -and $script:AppelsOllama -eq 0 -and $script:AppelsGetPlan -eq 0 -and $r.routeur -match 'règle exacte') 'règle exacte : ni routeur ni Claude ; le diagnostic dit « sauté : règle exacte »'
$script:Ollama = & $json 'actions' 0.95 @(@{ type = 'volume'; delta = 10 })
$r = Ordre 'tu peux monter un petit peu le son là'
Verifier ($r.etage -eq 'routeur' -and $script:AppelsOllama -eq 1 -and $script:AppelsGetPlan -eq 0 -and $script:Sequence -contains 'volume' -and $r.routeur -match '^ok en \d+ ms') 'commande reformulée : le routeur la comprend, Claude n''est PAS appelé'
$script:Ollama = & $json 'conversation' 0.9 @()
$r = Ordre 'pourquoi le ciel est bleu'
Verifier ($script:AppelsOllama -eq 1 -and $script:AppelsGetPlan -eq 1 -and $r.etage -eq 'claude' -and $r.routeur -match '^conversation en \d+ ms') 'question ouverte : routeur « conversation » puis Claude'
$script:Ollama = & $json 'incertain' 0.2 @()
$r = Ordre 'explique-moi comment marche le routeur'
Verifier ($script:AppelsGetPlan -eq 1 -and $r.routeur -match '^incertain') 'question ouverte « incertain » : Claude'

Write-Host '2) Une commande du PC ne va JAMAIS à Claude'
foreach ($ph in 'ouvre le truc de musique là', 'mets le son un peu plus fort s''il te plaît', 'ferme moi cette fenêtre lourde', 'baisse un peu la luminosité de l''écran') {
    $script:Ollama = & $json 'incertain' 0.2 @(); $r = Ordre $ph
    Verifier ($script:AppelsGetPlan -eq 0 -and $script:AppelsOllama -eq 1 -and $r.etage -in 'aucun', 'règle' -and $r.routeur -match 'incertain') "« $ph » : routeur « incertain » -> reformulation ou refus poli, Claude jamais appelé"
}
$script:Ollama = $null; $r = Ordre 'mets le son un peu plus fort s''il te plaît'
Verifier ($script:AppelsGetPlan -eq 0 -and (Dit-Incompris) -and $r.routeur -match 'échec : aucune réponse') 'Ollama muet (délai) : la raison est notée, et toujours pas de Claude pour une commande du PC'
$script:Ollama = & $json 'actions' 0.3 @(@{ type = 'volume'; delta = 10 }); $r = Ordre 'mets le son un peu plus fort s''il te plaît'
Verifier ($script:AppelsGetPlan -eq 0 -and $r.routeur -match 'confiance basse 0[.,]30 < 0[.,]60') 'confiance trop basse : raison chiffrée dans le diagnostic, pas de Claude'
$script:Ollama = & $json 'actions' 0.9 @(@{ type = 'powershell'; code = 'Remove-Item C:\x' }); $r = Ordre 'mets le son un peu plus fort s''il te plaît'
Verifier ($script:AppelsGetPlan -eq 0 -and $script:Sequence.Count -eq 0 -and $r.routeur -match 'réponse refusée') 'le routeur propose une commande interdite : refusée, notée, pas de Claude'
$script:ModeCerveau = 'claude'; $r = Ordre 'mets le son un peu plus fort s''il te plaît'
Verifier ($script:AppelsGetPlan -eq 0 -and (Dit-Incompris) -and $r.routeur -match '^sauté') 'cerveau local indisponible : raison « sauté : … », toujours pas de Claude pour une commande du PC'
$r = Ordre 'pourquoi le ciel est bleu'; Verifier ($script:AppelsGetPlan -eq 1 -and $r.routeur -match '^sauté') 'question ouverte avec cerveau local indisponible : Claude (seul étage possible)'
$script:ModeCerveau = 'local'
foreach ($ph in 'ouvre chrome', 'ferme discord', 'mets le son à 30', 'monte la musique', 'passe sur chrome', 'coupe le son', 'verrouille le PC', 'baisse la luminosité', 'tu peux ouvrir discord', 'mets chrome à gauche') { Verifier (Test-OrdreControlePc $ph) "commande du PC reconnue : « $ph »" }
foreach ($ph in 'pourquoi le ciel est bleu', 'explique-moi le routeur', 'résume ce document', 'quelle est la capitale de la France', 'comment ouvrir un compte en banque', 'raconte-moi une histoire', 'écris un mail à mon comptable') { Verifier (-not (Test-OrdreControlePc $ph)) "question ouverte : « $ph » reste possible pour Claude" }
$script:Ollama = & $json 'conversation' 0.9 @(); $r = Ordre 'ouvre-moi une discussion sur la philosophie des sciences et de la logique ancienne grecque en détail'
Verifier ($script:AppelsGetPlan -eq 1) 'phrase de plus de 12 mots : jamais prise pour une commande du PC'

Write-Host '3) Diagnostic vocal : étage, raison du routeur, chargement du modèle'
$script:OllamaChargeMs = 3120; $script:Ollama = & $json 'actions' 0.95 @(@{ type = 'volume'; delta = 10 }); $r = Ordre 'tu peux monter un petit peu le son là'
$p = @(Get-DiagPanneau 1)[0]
Verifier ($p.etapes -match 'étage routeur' -and $p.etapes -match 'routeur : ok en \d+ ms' -and $p.etapes -match 'chargement du modèle 3120 ms') "le panneau note l'étage, la raison et le chargement du modèle : « $($p.etapes) »"
$brut = Get-Content (Get-ChildItem (Join-Path $TR 'logs') -Filter 'diag-voix-*.jsonl')[0].FullName -Encoding UTF8 -Tail 1; $ligne = try { $brut | ConvertFrom-Json } catch { Write-Host "  (trace illisible : $brut)"; $null }
Verifier ($null -ne $ligne -and $ligne.routeur -match '^ok en' -and $ligne.modele_ms -eq 3120 -and $ligne.etage -eq 'routeur') 'la trace logs\diag-voix-*.jsonl contient étage, routeur et modele_ms'
$script:OllamaChargeMs = $null
$Config | Add-Member -NotePropertyName routeur_intention -NotePropertyValue $false -Force
$script:Ollama = $null; $r = Ordre 'mets le son un peu plus fort s''il te plaît'
Verifier ($r.routeur -match 'routeur_intention = false') 'routeur coupé dans config.json : la raison le dit'
$Config.routeur_intention = $true

Write-Host '4) Modèle Ollama préchargé au réveil (keep_alive)'
Verifier ((Get-OllamaConfig).keep -eq '30m' -and (Get-OllamaConfig).modele -eq 'qwen2.5:7b') 'keep_alive 30 min, modèle qwen2.5:7b'
$set = Get-Content (Join-Path $Root 'lib\raccourcis.ps1') -Raw -Encoding UTF8
Verifier ($set -match 'Start-OllamaReveil') 'Set-Actif (Alt + +, Verr. défil.) appelle le préchargement'
$script:JobArgs = $null
function Start-Job { param([scriptblock]$ScriptBlock, $ArgumentList) $script:JobArgs = $ArgumentList; [pscustomobject]@{ State = 'Running' } }
Start-OllamaChargement
$corps = $script:JobArgs[1] | ConvertFrom-Json
Verifier ($script:JobArgs[0] -eq 'http://127.0.0.1:11434' -and $corps.keep_alive -eq '30m' -and $corps.model -eq 'qwen2.5:7b' -and $corps.options.num_predict -eq 1) 'tâche de fond : 127.0.0.1 seulement, keep_alive 30m, une seule unité générée'
$script:JobOllama = [pscustomobject]@{ State = 'Completed' }
function Receive-Job { param($j, $ErrorAction) 4210 }
function Remove-Job { param($j, [switch]$Force, $ErrorAction) }
Update-OllamaChargement
Verifier ($script:OllamaChargeMs -eq 4210 -and $null -eq $script:JobOllama) 'fin du préchargement : temps de chargement mesuré (4210 ms) et mémorisé'
Verifier ((Get-Content (Get-ChildItem (Join-Path $TR 'logs') -Filter 'journal-*.md' | Select-Object -First 1).FullName -Raw -Encoding UTF8) -match 'modèle chargé en 4210 ms') 'le journal note « modèle chargé en N ms »'
$script:JobOllama = [pscustomobject]@{ State = 'Completed' }
function Receive-Job { param($j, $ErrorAction) -1 }
Update-OllamaChargement; Verifier ($script:OllamaChargeMs -eq 4210) 'service injoignable (-1) : la dernière mesure n''est pas écrasée'
Remove-Item function:Start-Job, function:Receive-Job, function:Remove-Job
$script:JobArgs = $null; Start-OllamaReveil; Verifier ($null -eq $script:JobArgs -and $null -eq $script:JobOllama) 'en test : jamais de service ni de tâche réels'
$src = Get-Content (Join-Path $Root 'lib\cerveau-local.ps1') -Raw -Encoding UTF8
Verifier ($src -match 'function Start-OllamaReveil' -and $src -match 'ModeJeu -eq \$true' -and $src -match "-eq 'claude'") 'préchargement : jamais en sourdine, en mode jeu ni si le cerveau est « claude »'

Write-Host '5) Voix : homme par défaut'
Verifier ($Config.voix.fr -eq 'fr-FR-HenriNeural' -and $Config.voix.en -eq 'en-GB-RyanNeural') 'Edge : fr-FR-HenriNeural (homme) et en-GB-RyanNeural (homme)'
Verifier ($Config.voix.fr -notmatch 'Denise|Eloise|Vivienne|Brigitte|Sylvie|Jacqueline|Yvette|Coralie|Ariane|Charline') 'aucune voix Edge féminine configurée'
Verifier ((Get-VoixMoteur) -eq 'edge') 'moteur : edge'
Verifier ((Get-PiperVoix) -eq 'tom' -and (Get-PiperModele) -match 'fr_FR-tom-medium\.onnx$') 'Piper : voix « tom » (homme) par défaut'
Verifier ((Test-Path (Get-PiperModele)) -and (Test-Path ((Get-PiperModele) + '.json')) -and (Get-Item (Get-PiperModele)).Length -gt 20MB) 'le modèle tom est téléchargé dans voix\models\piper'
Verifier ((Get-Content ((Get-PiperModele) + '.json') -Raw) -match '"dataset":\s*"tom"') 'et son fichier de description est bien celui de tom'
$Config | Add-Member -NotePropertyName voix_piper -NotePropertyValue 'siwis' -Force; Verifier ((Get-PiperVoix) -eq 'siwis' -and (Get-PiperModele) -match 'siwis') 'siwis reste disponible en option (voix_piper = siwis)'
$Config.voix_piper = '../../etc'; Verifier ((Get-PiperVoix) -eq 'tom') 'nom de voix invalide : tom'
$Config.voix_piper = 'inconnue'; Verifier ((Get-PiperVoix) -eq 'siwis' -or (Get-PiperVoix) -eq 'tom') 'voix absente : repli sur une voix installée'
$Config.voix_piper = 'tom'
Verifier ((Get-CheminTtsCache 'piper-tom' 'Bonjour') -ne (Get-CheminTtsCache 'piper-siwis' 'Bonjour')) 'cache vocal séparé par voix (aucune ancienne phrase de siwis rejouée avec tom)'
$v = Get-Content (Join-Path $Root 'lib\voix.ps1') -Raw -Encoding UTF8
Verifier ($v -match "\`$delai = if \(\`$texte\.Length -le 60\) \{ 5 \}") 'cause du repli féminin : le délai de 1,5 s pour les phrases courtes passe à 5 s'
Verifier ($v -match "Gender -eq 'Male'" -and $v -match 'repli Piper' -and $v -match 'voix_repli_piper') 'repli : Piper (homme) d''abord, puis une voix Windows masculine si elle existe, et le journal dit laquelle'
Verifier ((Get-Content (Join-Path $Root 'voix\piper_serveur.py') -Raw -Encoding UTF8) -match 'utf-8-sig') 'serveur Piper : la 1re requête n''est plus perdue à cause du BOM de PowerShell'

Remove-Item $TR -Recurse -Force -ErrorAction SilentlyContinue
if ($echecs) { Write-Host "`n$echecs échec(s)." -ForegroundColor Red; exit 1 }
Write-Host "`nTOUT EST VERT." -ForegroundColor Green; exit 0
