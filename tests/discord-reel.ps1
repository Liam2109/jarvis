# TEST MANUEL du pont Discord — à lancer VOUS-MÊME (jamais par Claude, jamais par tests\tout.ps1) : il se connecte pour de vrai à votre bot Discord.
#   powershell -ExecutionPolicy Bypass -File tests\discord-reel.ps1 -Oui
# Prérequis : Jarvis ARRÊTÉ (deux ponts avec le même jeton se répondraient en double), pip install discord.py, DISCORD_BOT_TOKEN et DISCORD_USER_ID dans .env,
# un salon dont le nom contient « jarvis » sur votre serveur (les salons sont associés automatiquement par leur nom ; rien à renseigner dans config.json), « Message Content Intent » activé sur le portail développeur Discord.
# Le test envoie ses consignes DANS Discord (salon « jarvis ») : gardez votre téléphone ou Discord ouvert. Il dure 3 à 4 minutes au plus.
# JARVIS_TEST=1 : aucune action réelle sur le PC (les actions sont simulées), aucune voix. Le jeton n'est jamais affiché ni écrit.
param([switch]$Oui)
if (-not $Oui) { Write-Host 'Ce test se connecte à votre vrai bot Discord. Relancez avec -Oui :'; Write-Host '  powershell -ExecutionPolicy Bypass -File tests\discord-reel.ps1 -Oui'; exit 2 }
$ErrorActionPreference = 'Stop'
$env:JARVIS_TEST = '1'
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $Root 'lib\journal.ps1')
Import-JarvisEnv
$Config = Get-Content (Join-Path $Root 'config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($l in 'voix', 'business', 'permissions', 'actions', 'coffre', 'entrees', 'ecrans', 'tableau', 'visage', 'sons', 'raccourcis', 'cerveau', 'cerveau-local', 'veille', 'memoire', 'rapide', 'discretion', 'modejeu', 'competences', 'marche', 'priorite', 'comprehension', 'routeur', 'pc', 'bureau', 'salle-marche', 'matin', 'discord', 'boucle') { . (Join-Path $Root "lib\$l.ps1") }
foreach ($f in (Get-ChildItem (Join-Path $Root 'lib\sources') -Filter '*.ps1' | Where-Object { $_.Name -notlike '_*' })) { . $f.FullName }
$script:StopFlag = Join-Path $env:TEMP 'jarvis-test-stop.flag'          # (un « stop » écrit pendant le test ne touche pas au vrai drapeau de Jarvis)
$echecs = 0
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }
function Attendre([scriptblock]$cond, [int]$secondes) { $fin = (Get-Date).AddSeconds($secondes); while ((Get-Date) -lt $fin) { Invoke-PumpDiscord; if (& $cond) { return $true }; Start-Sleep -Milliseconds 300 }; $false }
function Terminer { Stop-PontDiscord; Remove-Item $script:StopFlag -Force -ErrorAction SilentlyContinue; Remove-Item Env:JARVIS_PONT_FAUX -ErrorAction SilentlyContinue }

Write-Host '1) Préconditions'
$pidf = Join-Path $Root 'memoire\jarvis.pid'
$tourne = $false; if (Test-Path $pidf) { try { $o = Get-Content $pidf -Raw -Encoding UTF8 | ConvertFrom-Json; $tourne = [bool](Get-Process -Id ([int]$o.pid) -ErrorAction SilentlyContinue) } catch {} }
Verifier (-not $tourne) 'Jarvis n''est pas lancé (sinon : arreter.ps1, puis relancez ce test)'
$id = Get-DiscordIdentifiants
Verifier $id.ok ("identifiants présents dans .env" + $(if (-not $id.ok) { " — il manque : $($id.manque -join ', ')" } else { '' }))
$dpy = (& python -I -c "import discord; print(discord.__version__)" 2>$null)
Verifier ([bool]$dpy) ("discord.py installé" + $(if ($dpy) { " (version $dpy)" } else { ' — faites : pip install discord.py' }))
if ($echecs) { Write-Host "`nPréconditions non remplies : test interrompu." -ForegroundColor Red; exit 1 }

Write-Host '2) Connexion (le vrai pont, lancé par Jarvis comme en usage normal)'
$Config.discord_actif = $true
Remove-Item (Get-FichierMemoire 'discord-salons.json') -Force -ErrorAction SilentlyContinue      # (le pont doit relire les salons du serveur)
foreach ($d in 'entrant', 'sortant') { Remove-Item (Join-Path (Join-Path (Get-DiscordDossier) $d) '*') -Force -ErrorAction SilentlyContinue }      # (restes d'un essai précédent)
$env:JARVIS_PONT_FAUX = Join-Path $Root 'pont-discord\pont.py'
try {
    [void](Start-PontDiscord)
    Verifier ($script:PontProc -and -not $script:PontProc.HasExited) 'le processus du pont démarre'
    $ok = Attendre { (Get-EtatPontTexte) -eq 'connecté' } 45
    Verifier $ok 'le pont est connecté à Discord (en moins de 45 s)'
    if (-not $ok) { Update-PontDiscord; Write-Host '  Voir logs\journal-*.md (cherchez « Pont Discord ») : jeton refusé ? intention « Message Content » non activée ?'; Terminer; exit 1 }

    $ok = Attendre { (Get-DiscordConfig).salons.ContainsKey('jarvis') } 30
    $c = Get-DiscordConfig
    Verifier $ok ("salons associés automatiquement par le pont : trouvés = " + $(if ($c.salons.Count) { ($c.salons.Keys | Sort-Object) -join ', ' } else { 'aucun' }) + " ; introuvables = " + $(if ($c.manquants.Count) { $c.manquants -join ', ' } else { 'aucun' }))
    if (-not $ok) { Write-Host '  Aucun salon dont le nom contient « jarvis » sur le serveur où vous êtes (ou le bot n''est pas invité dessus) : créez-le puis relancez.'; Terminer; exit 1 }

    Write-Host '3) Un message de Liam (dans les 90 s) : écrivez « statut » dans le salon #jarvis'
    [void](Send-MessageDiscord 'jarvis' "Test manuel du pont Discord. Étape 1/3 : écrivez « statut » ici, dans les 90 secondes.")
    $recu = $null; $ok = Attendre { $script:r = Get-OrdreDiscord; if ($script:r) { $script:recu = $script:r; $true } else { $false } } 90
    Verifier ($ok -and $script:recu) 'un message de Liam est arrivé jusqu''à Jarvis (identifiant et salon vérifiés des deux côtés)'
    if ($script:recu) {
        Invoke-OrdreDiscord $script:recu.texte $script:recu.canal $script:recu.id
        Write-Host '  -> Jarvis vient de répondre dans Discord : vérifiez que la réponse est écrite, polie, sans le moindre jeton.'
    }

    Write-Host '4) Une confirmation (dans les 60 s) : répondez par ✅ / ❌ ou par « oui » / « non »'
    [void](Send-MessageDiscord 'jarvis' 'Étape 2/3 : la question suivante va arriver ; répondez avec la réaction ✅ ou ❌, ou en écrivant oui / non.')
    Start-Sleep -Seconds 2
    $script:CanalDiscord = 'jarvis'; $script:DiscordTampon = New-Object System.Collections.Generic.List[string]; $script:DiscordReplyTo = ''
    $r = Confirmer-Discord 'Test de confirmation : faire comme si je mettais le PC en veille (rien ne sera exécuté), monsieur ?'
    Send-TamponDiscord; $script:CanalDiscord = $null; $script:DiscordTampon = $null
    Verifier ($script:DerniereConfirmation -in 'oui', 'non') "une réponse est arrivée : « $($script:DerniereConfirmation) » ($(if ($r) { 'accepté' } else { 'refusé' }))"

    Write-Host '5) Un autre utilisateur (30 s) : faites écrire quelqu''un d''autre dans #jarvis (sans écrire vous-même)'
    [void](Send-MessageDiscord 'jarvis' 'Étape 3/3 : si vous le pouvez, faites écrire quelqu''un d''autre (ou un autre compte) dans ce salon pendant 30 s, sans écrire vous-même. Je ne dois RIEN répondre.')
    $recuAutre = Attendre { $script:DiscordFile.Count -gt 0 } 30
    Verifier (-not $recuAutre) 'aucun message étranger n''est arrivé jusqu''à Jarvis (et le bot n''a pas répondu : à vérifier dans Discord)'
    [void](Send-MessageDiscord 'jarvis' 'Test terminé. Le pont va s''arrêter.')
    Start-Sleep -Seconds 2
} finally { Terminer }
Start-Sleep -Milliseconds 500
Verifier (@(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'pont-discord\\pont\.py' }).Count -eq 0) 'le pont est arrêté (plus aucun processus)'
$jr = Join-Path $env:TEMP 'jarvis-test-logs'
Verifier (-not ($env:DISCORD_BOT_TOKEN -and (Get-ChildItem $jr -File -ErrorAction SilentlyContinue | Where-Object { Select-String -Path $_.FullName -Pattern $env:DISCORD_BOT_TOKEN -SimpleMatch -Quiet }))) 'le jeton n''apparaît dans aucun journal de ce test'
if ($echecs) { Write-Host "`nÉCHEC : $echecs vérification(s) en échec." -ForegroundColor Red; exit 1 }
Write-Host "`nRÉUSSI"; exit 0
