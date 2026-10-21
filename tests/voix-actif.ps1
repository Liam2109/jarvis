# Test SILENCIEUX de l'option voix_actif (défaut « non ») : désactivée ou absente, aucun micro n'est ouvert (écoute continue, mot de réveil, claquements, commande ecoute, calibrage) ; « oui » : comportement actuel.
# Les processus d'écoute sont remplacés par un python inoffensif (-c pass) : aucun micro, aucun son, aucune fenêtre. Code de sortie 0 = réussi.
$ErrorActionPreference = 'Stop'
$env:JARVIS_TEST = '1'
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $Root 'lib\journal.ps1')
$TR = Join-Path $env:TEMP ('jarvis-test-' + [guid]::NewGuid().ToString('N').Substring(0, 8)); New-Item -ItemType Directory $TR, "$TR\memoire", "$TR\logs" | Out-Null; $script:JarvisRoot = $TR
'# To-do' | Set-Content "$TR\memoire\todo.md" -Encoding UTF8; '# N' | Set-Content "$TR\memoire\notes.md" -Encoding UTF8; '# R' | Set-Content "$TR\memoire\resume.md" -Encoding UTF8
$Config = Get-Content $(if ($env:JARVIS_CONFIG -and (Test-Path $env:JARVIS_CONFIG)) { $env:JARVIS_CONFIG } else { Join-Path $Root 'config.json' }) -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($l in 'voix', 'business', 'permissions', 'actions', 'coffre', 'entrees', 'ecrans', 'tableau', 'visage', 'sons', 'raccourcis', 'cerveau', 'cerveau-local', 'veille', 'memoire', 'rapide', 'discretion', 'modejeu', 'competences', 'marche', 'priorite', 'comprehension', 'routeur', 'pc', 'bureau', 'salle-marche', 'matin', 'discord', 'veille-train', 'veille-mail', 'candidatures', 'veille-reveil') { . (Join-Path $Root "lib\$l.ps1") }
$script:JarvisRoot = $TR; $script:PolitesseFixe = $true
$echecs = 0
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }
function Fixer([string]$cle, $val) { if ($Config.PSObject.Properties[$cle]) { $Config.$cle = $val } else { $Config | Add-Member -NotePropertyName $cle -NotePropertyValue $val } }
function Journal { $f = Join-Path $TR ('logs\journal-{0}.md' -f (Get-Date -Format 'yyyy-MM-dd')); if (Test-Path $f) { Get-Content $f -Raw -Encoding UTF8 } else { '' } }
$vraie = Get-Content (Join-Path $Root 'config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$hashConfig = (Get-FileHash (Join-Path $Root 'config.json')).Hash
$script:PyAppel = 0; $script:ArgsEcouteAppel = 0; $script:ArgsVeilleAppel = 0
function python { $script:PyAppel++; $null }      # jamais le vrai python pour l'écoute : tout appel est compté
function Get-ArgsEcoute { $script:ArgsEcouteAppel++; '-I -c "pass"' }      # processus inoffensif : il se termine aussitôt, aucun micro
function Get-ArgsVeille([string]$py) { $script:ArgsVeilleAppel++; '-I -c "pass"' }
function Test-ModeTest { $false }      # pour traverser la garde « tests : jamais le micro » : seul voix_actif est alors en jeu
function Arreter-Procs { foreach ($p in @($script:Ecoute, $script:VeilleProc)) { try { if ($p -and -not $p.HasExited) { $p.Kill() } } catch {} }; $script:Ecoute = $null; $script:VeilleProc = $null; $script:EcouteTache = $null; $script:VeilleTache = $null }
function Remettre { $script:PyAppel = 0; $script:ArgsEcouteAppel = 0; $script:ArgsVeilleAppel = 0; Arreter-Procs; $script:VeilleProchainEssai = [datetime]::MinValue }
function Regler-Voix($v) { if ($v -eq '<absent>') { if ($Config.PSObject.Properties['voix_actif']) { $Config.PSObject.Properties.Remove('voix_actif') } } else { Fixer 'voix_actif' $v } }
Fixer 'veille_reveil' $true; Fixer 'claquement_actif' $true; $script:Actif = $false; $script:ModeJeu = $false

# ---------- 1. Lecture de l'option ----------
Write-Host '1. Option voix_actif'
Verifier ($vraie.voix_actif -eq 'non') 'config.json : voix_actif = "non" (désactivée par défaut)'
$res = @{}; foreach ($v in '<absent>', 'non', 'oui', 'OUI ', 'true', '1', 'on', 'peut-être', '', 'false', 'non') { Regler-Voix $v; $res["$v"] = Test-VoixActive }
Verifier (-not $res['<absent>'] -and -not $res['non'] -and $res['oui'] -and $res['OUI '] -and $res['true'] -and $res['1'] -and $res['on'] -and -not $res['peut-être'] -and -not $res[''] -and -not $res['false']) 'option absente, « non », vide ou inconnue = désactivée ; « oui » (et true / 1 / on) = activée'

# ---------- 2. Option « non » (et option absente) : aucun micro ouvert ----------
Write-Host '2. Voix désactivée : aucun micro'
foreach ($etat in 'non', '<absent>') {
    Regler-Voix $etat; Remettre
    Start-Ecoute; Start-EcouteVeille; Update-VeilleReveil
    Verifier ($null -eq $script:Ecoute -and $null -eq $script:VeilleProc -and $script:ArgsEcouteAppel -eq 0 -and $script:ArgsVeilleAppel -eq 0) "voix_actif = $etat : ni l'écoute continue (ecoute.py) ni l'écoute de veille (reveil.py) ne démarrent"
    Verifier ((Get-EtatVeilleVoulu) -eq 'arret') "voix_actif = $etat : l'état voulu de la veille (mot de réveil, claquements) reste « arret » même en sourdine avec veille_reveil activé"
    $o = Ecouter-Ordre -Timeout 1
    Verifier ($null -eq $o -and $script:PyAppel -eq 0) "voix_actif = $etat : Ecouter-Ordre (commande « ecoute ») n'ouvre pas le micro"
    $c = Invoke-CalibrageClaquements
    Verifier (-not $c.ok -and $c.texte -match 'désactivée' -and $script:PyAppel -eq 0 -and $script:ArgsVeilleAppel -eq 0) "voix_actif = $etat : le calibrage des claquements refuse poliment, sans micro"
}

# ---------- 3. Option « oui » : comportement actuel ----------
Write-Host '3. Voix activée : comportement actuel'
Regler-Voix 'oui'; Remettre; $script:Actif = $true
Start-Ecoute
Verifier ($script:ArgsEcouteAppel -eq 1 -and $null -ne $script:Ecoute) 'voix_actif = oui : l''écoute continue démarre comme avant'
Arreter-Procs; $script:Actif = $false
Verifier ((Get-EtatVeilleVoulu) -eq 'ecoute') 'voix_actif = oui, sourdine, veille_reveil activé : la veille voulue est « ecoute » comme avant'
Update-VeilleReveil
Verifier ($script:ArgsVeilleAppel -eq 1 -and $null -ne $script:VeilleProc) 'voix_actif = oui : l''écoute de veille démarre comme avant'
Regler-Voix 'non'; Update-VeilleReveil
Verifier ($null -eq $script:VeilleProc) 'repasser à « non » à chaud : l''écoute de veille déjà lancée est arrêtée'
Remettre; Regler-Voix 'non'

# ---------- 4. Le reste ne change pas ----------
Write-Host '4. Le reste du programme'
$js = Get-Content (Join-Path $Root 'jarvis.ps1') -Raw -Encoding UTF8; $en = Get-Content (Join-Path $Root 'lib\entrees.ps1') -Raw -Encoding UTF8; $vr = Get-Content (Join-Path $Root 'lib\veille-reveil.ps1') -Raw -Encoding UTF8; $vx = Get-Content (Join-Path $Root 'lib\voix.ps1') -Raw -Encoding UTF8
Verifier ($js -match "Voix désactivée \(voix_actif = non\)" -and $js -match "Voix activée \(voix_actif = oui\)" -and $js.IndexOf('Voix désactivée') -lt $js.IndexOf("Action 'Démarrage de Jarvis'") + 400) 'jarvis.ps1 écrit au démarrage « Voix désactivée (voix_actif = non) » (ou « activée »)'
Verifier ($en.IndexOf('Test-VoixActive') -gt 0 -and $en.IndexOf('Test-VoixActive') -lt $en.IndexOf('Diagnostics.ProcessStartInfo') -and $vr.IndexOf('Test-VoixActive') -lt $vr.IndexOf('Diagnostics.ProcessStartInfo') -and $vx.IndexOf('Test-VoixActive') -lt $vx.IndexOf('ecoute.py')) 'la garde précède, dans le code, chaque lancement de python d''écoute (ecoute.py, reveil.py)'
Verifier ($js -match 'Start-PontDiscord' -and $js -match 'Update-VeilleMail' -and $js -match 'Update-VeilleTrain' -and $js -match 'Update-DevAgent' -and $js -match 'Initialize-BriefingMatin' -and $js -notmatch 'if \(Test-VoixActive\)[^\n]*(Start-PontDiscord|Update-VeilleMail|Update-VeilleTrain|Update-DevAgent)') 'Discord, veille e-mail, veille train, agent de dev, briefing : appelés comme avant, sans dépendre de la voix'
Verifier ((Get-FileHash (Join-Path $Root 'config.json')).Hash -eq $hashConfig) 'config.json réel inchangé par le test'

Write-Host ''
Remove-Item $TR -Recurse -Force -ErrorAction SilentlyContinue
if ($echecs) { Write-Host "ÉCHEC : $echecs vérification(s) en échec." -ForegroundColor Red; exit 1 }
Write-Host 'TOUT EST VERT.'
