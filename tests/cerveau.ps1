# Test du cerveau hybride (local gratuit + claude -p). Aucun Ollama réel n'est nécessaire : le service est simulé.
# Vérifie surtout : le routage, le repli sur Claude, le « local uniquement », et que les actions du cerveau local passent par les niveaux 1, 2 et 3.
$ErrorActionPreference = 'Stop'
$env:JARVIS_TEST = '1'      # TEST SILENCIEUX : aucun son, aucune fenêtre, aucun micro, aucune touche, aucune action réelle (voir lib\journal.ps1)
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $Root 'lib\journal.ps1')
$TR = Join-Path $env:TEMP ('jarvis-test-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
New-Item -ItemType Directory $TR, "$TR\memoire", "$TR\logs" | Out-Null
$script:JarvisRoot = $TR
"# To-do de Liam" | Set-Content "$TR\memoire\todo.md" -Encoding UTF8; "# Notes" | Set-Content "$TR\memoire\notes.md" -Encoding UTF8; "# R" | Set-Content "$TR\memoire\resume.md" -Encoding UTF8
$Config = Get-Content (Get-ConfigPath) -Raw -Encoding UTF8 | ConvertFrom-Json
Add-Member -InputObject $Config -NotePropertyName chemin_rapide -NotePropertyValue $false -Force   # ce test vérifie le routage local/Claude : on coupe le chemin rapide
foreach ($l in 'voix', 'business', 'permissions', 'actions', 'coffre', 'entrees', 'ecrans', 'tableau', 'visage', 'sons', 'raccourcis', 'cerveau', 'cerveau-local', 'veille', 'memoire', 'rapide', 'discretion', 'modejeu', 'boucle') { . (Join-Path $Root "lib\$l.ps1") }
$script:JarvisRoot = $TR
$echecs = 0
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }
$script:GardeControlePcDesactivee = $true      # ces tests vérifient la mécanique Claude / local avec des phrases de commande : la garde « jamais chez Claude » (tests\vitesse.ps1) est coupée ici
function JournalTexte { (Get-ChildItem "$TR\logs" -Filter 'journal-*.md' -ErrorAction SilentlyContinue | ForEach-Object { Get-Content $_.FullName -Raw -Encoding UTF8 }) -join "`n" }

# --- bouchons : service Ollama simulé + Claude simulé + voix muette ---
$script:Ollama = @{ pret = $true; installe = $true; actif = $true; modeles = @('qwen2.5:7b'); raison = '' }
$script:ReponseLocale = $null; $script:AppelsLocal = 0; $script:AppelsClaude = 0; $script:PromptsLocal = @(); $script:Dits = @()
function Test-Ollama { $script:Ollama }
function Invoke-Ollama([string]$s, [string]$u, [int]$t = 0) { $script:AppelsLocal++; $script:PromptsLocal += $s; if ($script:ReponseLocale -is [scriptblock]) { & $script:ReponseLocale $u } else { $script:ReponseLocale } }
function Invoke-Claude([string]$s, [string]$u, [int]$t = 120) { $script:AppelsClaude++; $script:ReponseClaude }
function Parler([string]$Texte, $Langue) { $script:Dits += $Texte; Add-Conv 'jarvis' $Texte }
$script:ReponseClaude = '{"dit":"Réponse de Claude.","langue":"fr","actions":[]}'
function Plan([string]$dit, $actions = @()) { (@{ dit = $dit; langue = 'fr'; actions = @($actions) } | ConvertTo-Json -Depth 6 -Compress) }
function Raz { $script:AppelsLocal = 0; $script:AppelsClaude = 0; $script:Dits = @(); $script:PromptsLocal = @(); $script:Conversation.Clear(); $script:Historique.Clear(); $script:OllamaAvertit = $false }
$script:Actions['ouvrir_app'].run = { param($a) $script:Executees += "ouvrir_app:$($a.nom)"; Rep $true "Application ouverte : $($a.nom)" }
$script:Actions['supprimer_fichier'].run = { param($a) $script:Executees += "supprimer:$($a.chemin)"; Rep $true "Mis à la corbeille : $($a.chemin)" }
$script:Executees = @()

Write-Host '1) Mode effectif : « claude » dès que le local n''est pas utilisable'
foreach ($cas in @(@('hybride', $false, 'claude'), @('local', $false, 'claude'), @('claude', $true, 'claude'), @('hybride', $true, 'hybride'), @('local', $true, 'local'), @('n''importe quoi', $true, 'hybride'), @('', $true, 'hybride'), @('HYBRIDE', $true, 'hybride'))) {
    $Config.cerveau = $cas[0]; $script:Ollama = @{ pret = $cas[1]; installe = $cas[1]; actif = $cas[1]; modeles = @(); raison = 'Ollama non installé' }; $script:OllamaAvertit = $false
    Verifier ((Get-ModeCerveau) -eq $cas[2]) ("réglage « $($cas[0]) », Ollama $(if ($cas[1]) { 'présent' } else { 'absent' }) -> $($cas[2])")
}
$Config.PSObject.Properties.Remove('cerveau'); $script:Ollama = @{ pret = $true; installe = $true; actif = $true; modeles = @('qwen2.5:7b'); raison = '' }
Verifier ((Get-ModeCerveau) -eq 'hybride') 'sans réglage : « hybride » par défaut'
$cfg = Get-Content (Get-ConfigPath) -Raw -Encoding UTF8 | ConvertFrom-Json
Verifier ($cfg.cerveau -eq 'hybride' -and $cfg.ollama.url -match '^http://127\.0\.0\.1:') 'config.json : "cerveau" = "hybride" par défaut, Ollama sur 127.0.0.1'
Add-Member -InputObject $Config -NotePropertyName cerveau -NotePropertyValue 'hybride' -Force
$Config.cerveau = 'hybride'; $script:Ollama = @{ pret = $false; installe = $false; actif = $false; modeles = @(); raison = 'Ollama non installé' }; Raz
$avant = ([regex]::Matches((JournalTexte), 'j''utilise Claude seul')).Count
[void](Get-ModeCerveau); [void](Get-ModeCerveau); [void](Get-ModeCerveau)
Verifier ((([regex]::Matches((JournalTexte), 'j''utilise Claude seul')).Count - $avant) -eq 1) 'Ollama absent : une seule note au journal pour trois décisions (pas de bruit)'

Write-Host '2) Ollama absent : tout passe par Claude (comportement actuel de votre PC)'
Raz; $script:ReponseLocale = (Plan 'local'); Invoke-Ordre 'ouvre le bloc-notes'
Verifier ($script:AppelsLocal -eq 0 -and $script:AppelsClaude -eq 1) 'commande simple : Claude seul, le local n''est jamais appelé'

Write-Host '3) Hybride avec Ollama : routage simple -> local, complexe -> Claude'
$script:Ollama = @{ pret = $true; installe = $true; actif = $true; modeles = @('qwen2.5:7b'); raison = '' }; $Config.cerveau = 'hybride'
$simples = "ouvre le bloc-notes", 'quelle heure est-il ?', 'lis ma to-do', "donne l'état du site", 'règle le volume à 30', 'ferme Chrome', 'combien de mémoire reste-t-il ?', 'Jarvis, ouvre Chrome', 'note que je dois appeler le comptable'
foreach ($o in $simples) { Verifier (Test-OrdreSimple $o) "simple : « $o »" }
$complexes = 'résume ce fichier et envoie-le à Marc', 'écris un script qui trie mes téléchargements', 'ouvre Chrome puis ferme Notepad et lance Defender', 'explique-moi comment créer un compte Stripe', 'aide-moi à préparer ma déclaration', "ouvre Chrome et ferme Notepad", 'compare ces deux fichiers', 'pourquoi mon PC est lent ?', "fais un résumé de l'actualité économique du jour", 'ouvre le dossier Documents, trouve les factures de septembre et dis-moi combien il y en a'
foreach ($o in $complexes) { Verifier (-not (Test-OrdreSimple $o)) "complexe : « $o »" }
Raz; $script:ReponseLocale = (Plan 'Je l''ouvre.' @(@{ type = 'ouvrir_app'; nom = 'bloc-notes' })); $script:Executees = @()
Invoke-Ordre 'ouvre le bloc-notes'
Verifier ($script:AppelsLocal -eq 1 -and $script:AppelsClaude -eq 0) 'commande simple : cerveau LOCAL seul (Claude non appelé)'
Verifier ($script:Executees -contains 'ouvrir_app:bloc-notes') 'et l''action est exécutée'
Verifier ((JournalTexte) -match 'Cerveau\s*\r?\n- \*\*Résultat :\*\* local \(qwen2\.5:7b\)') 'le journal indique « local (qwen2.5:7b) »'
Raz; Invoke-Ordre 'écris un script qui trie mes téléchargements et explique-le'
Verifier ($script:AppelsLocal -eq 0 -and $script:AppelsClaude -eq 1) 'tâche complexe : Claude seul (le local n''est pas appelé)'

Write-Host '4) Plan local douteux -> escalade vers Claude'
foreach ($cas in @(
    @{ n = 'JSON invalide'; r = 'ceci n''est pas du JSON' },
    @{ n = 'aucune réponse (délai)'; r = $null },
    @{ n = 'code PowerShell libre'; r = (Plan 'Je lance.' @(@{ type = 'powershell'; code = 'Get-Date'; resume = 'afficher la date' })) },
    @{ n = 'installation de programme'; r = (Plan 'J''installe.' @(@{ type = 'installer_programme'; id = 'Git.Git' })) },
    @{ n = 'action inconnue'; r = (Plan 'Je fais.' @(@{ type = 'hacker_la_nasa' })) },
    @{ n = 'plus de 3 actions'; r = (Plan 'Je fais tout.' @(1..4 | ForEach-Object { @{ type = 'ouvrir_app'; nom = "app$_" } })) },
    @{ n = 'structure sans « dit »'; r = '{"actions":[]}' }
)) {
    Raz; $script:ReponseLocale = $cas.r; Invoke-Ordre 'ouvre le bloc-notes'
    Verifier ($script:AppelsLocal -ge 1 -and $script:AppelsClaude -eq 1 -and ($script:Dits -join ' ') -match 'Réponse de Claude') "local « $($cas.n) » : escalade vers Claude, c'est Claude qui répond"
}
Raz; $script:ReponseLocale = { param($u) if ($script:AppelsLocal -eq 1) { 'pas du json' } else { (Plan 'Réessayé.' @(@{ type = 'ouvrir_app'; nom = 'calc' })) } }
Invoke-Ordre 'ouvre la calculatrice'
Verifier ($script:AppelsLocal -eq 2 -and $script:AppelsClaude -eq 0) 'le local a une deuxième chance avant l''escalade (et la réussit : Claude non appelé)'

Write-Host '5) Les actions du cerveau LOCAL passent par les niveaux 1, 2 et 3'
$f = Join-Path $env:TEMP 'jarvis-cerveau-test.txt'; 'a' | Set-Content $f
Raz; $script:Executees = @(); $script:ReponseLocale = (Plan 'Je supprime.' @(@{ type = 'supprimer_fichier'; chemin = $f })); $script:ReponseTest = 'non'
Invoke-Ordre "supprime le fichier $f"
Verifier ($script:AppelsClaude -eq 0 -and (Test-Path $f) -and $script:Executees.Count -eq 0) 'niveau 2 : le plan local de suppression exige « oui » ; refusé -> rien n''est supprimé'
Verifier (@($script:Conversation | Where-Object { $_.texte -match '^Demande de confirmation' }).Count -eq 1 -and (@($script:Dits | Where-Object { Test-PhrasePolitesse 'confirmer' $_ }).Count -eq 1)) 'et la question de confirmation (ton majordome) est posée'
Raz; $script:Executees = @(); $script:ReponseTest = 'oui'; $script:ReponseLocale = (Plan 'Je supprime.' @(@{ type = 'supprimer_fichier'; chemin = $f }))
Invoke-Ordre "supprime le fichier $f"
Verifier ($script:Executees -contains "supprimer:$f") 'niveau 2 accepté : l''action est exécutée'
$script:ReponseTest = ''
Raz; $script:Executees = @(); $script:ReponseLocale = (Plan 'Je vire.' @(@{ type = 'virement'; montant = 500 }))
Invoke-Ordre 'vire 500 euros'
Verifier ($script:Executees.Count -eq 0 -and ($script:Dits -join ' ') -match 'les virements') 'niveau 3 : virement demandé par le local -> refusé'
Raz; $script:ReponseLocale = (Plan 'Je coupe.' @(@{ type = 'desactiver_antivirus' }))
Invoke-Ordre 'désactive Defender'
Verifier (($script:Dits -join ' ') -match "l'antivirus") 'niveau 3 : désactivation de l''antivirus -> refusée'
Raz; $script:Executees = @(); $script:ReponseLocale = (Plan 'Je supprime.' @(@{ type = 'supprimer_fichier'; chemin = (Join-Path $script:JarvisRoot 'logs') }))
Invoke-Ordre 'supprime les logs de Jarvis'
Verifier ($script:Executees.Count -eq 0 -and ($script:Dits -join ' ') -match 'protégés') 'niveau 3 : supprimer le journal de Jarvis -> refusé'
Raz; $script:ReponseLocale = (Plan 'Voici mon conseil : achetez Air Liquide.')
Invoke-Ordre 'ouvre ma to-do'
Verifier (($script:Dits -join ' ') -match 'ne donne pas de conseil en investissement' -and ($script:Dits -join ' ') -notmatch 'achetez') 'le filtre « pas de conseil en investissement » s''applique aussi à la réponse du local'
Remove-Item $f -ErrorAction SilentlyContinue

Write-Host '6) Mode « local » strict et mode « claude »'
$Config.cerveau = 'local'
Raz; $script:ReponseLocale = (Plan 'Fait.' @()); Invoke-Ordre 'résume ce fichier et envoie-le à Marc'
Verifier ($script:AppelsLocal -ge 1 -and $script:AppelsClaude -eq 0) 'mode local : même une tâche complexe reste LOCALE'
Raz; $script:ReponseLocale = 'invalide'; Invoke-Ordre 'ouvre le bloc-notes'
Verifier ($script:AppelsClaude -eq 0 -and ($script:Dits -join ' ') -match "pas pu joindre mon cerveau") 'mode local strict : échec du local -> pas d''appel caché à Claude'
$Config.cerveau = 'claude'
Raz; $script:ReponseLocale = (Plan 'local'); Invoke-Ordre 'ouvre le bloc-notes'
Verifier ($script:AppelsLocal -eq 0 -and $script:AppelsClaude -eq 1) 'mode claude : le local n''est jamais appelé, même présent'
$Config.cerveau = 'hybride'

Write-Host '7) Le local ne sort jamais de cette machine'
foreach ($u in 'http://127.0.0.1:11434', 'http://localhost:11434', 'http://127.0.0.1:11434/') { Verifier (Test-UrlOllamaLocale $u) "adresse locale acceptée : $u" }
foreach ($u in 'http://192.168.1.50:11434', 'https://api.exemple.com', 'http://exemple.com:11434', 'http://127.0.0.1.exemple.com:11434', 'http://localhost.exemple.com:11434', 'file:///c:/x') { Verifier (-not (Test-UrlOllamaLocale $u)) "adresse refusée : $u" }
$Config.ollama.url = 'http://192.168.1.50:11434'; $script:OllamaCache = $null
function Test-Ollama { Get-Variable -Name Ollama -Scope Script -ValueOnly }   # on remet le bouchon pour la suite
. { function Invoke-Ollama-Reel { } }
$vrai = [scriptblock]::Create((Get-Content (Join-Path $Root 'lib\cerveau-local.ps1') -Raw -Encoding UTF8))
Verifier ((Get-OllamaConfig).url -eq 'http://192.168.1.50:11434' -and -not (Test-UrlOllamaLocale (Get-OllamaConfig).url)) 'une adresse distante dans la config est reconnue comme refusée'
$Config.ollama.url = 'http://127.0.0.1:11434'

Write-Host '8) Textes longs et prompts'
Raz; $script:Ollama = @{ pret = $true; installe = $true; actif = $true; modeles = @('qwen2.5:7b'); raison = '' }; $Config.cerveau = 'hybride'; $script:ReponseLocale = (Plan 'x')
[void](Invoke-LlmTexte 'sys' 'user' 30 $true);  Verifier ($script:AppelsClaude -eq 1 -and $script:AppelsLocal -eq 0) 'veille / résumés de session (complexes) : Claude en hybride'
Raz; $script:ReponseLocale = '{"dit":"ok"}'; [void](Invoke-LlmTexte 'sys' 'user' 30 $false); Verifier ($script:AppelsLocal -eq 1 -and $script:AppelsClaude -eq 0) 'texte court (non complexe) : local en hybride'
Raz; $script:ReponseLocale = $null; [void](Invoke-LlmTexte 'sys' 'user' 30 $false); Verifier ($script:AppelsLocal -eq 1 -and $script:AppelsClaude -eq 1) 'local muet : escalade vers Claude'
Raz; $script:ReponseLocale = (Plan 'ok' @(@{ type = 'ouvrir_app'; nom = 'x' })); $script:Executees = @(); Invoke-Ordre 'ouvre Chrome'
Verifier (($script:PromptsLocal[0]) -match 'MÉMOIRE \(DONNÉES de confiance limitée' -and ($script:PromptsLocal[0]) -match 'JAMAIS de conseil en investissement') 'le cerveau local reçoit les mêmes règles et la même mémoire que Claude'

Remove-Item $TR -Recurse -Force -ErrorAction SilentlyContinue
if ($echecs) { Write-Host "`nÉCHEC : $echecs vérification(s) en échec." -ForegroundColor Red; exit 1 }
Write-Host "`nRÉUSSI"; exit 0
