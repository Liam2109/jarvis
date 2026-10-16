# Test SILENCIEUX du pont Discord côté Jarvis (lib\discord.ps1) — 100 % SIMULÉ : aucune connexion réseau, aucun vrai jeton (de faux identifiants), aucun vrai bot.
# Un FAUX pont (petit script Python inoffensif) sert à vérifier le démarrage, la surveillance, le redémarrage et l'arrêt du processus ; un faux « pont » simulé dans Invoke-Pump
# répond aux confirmations. Aucune voix, aucun son, aucune fenêtre. Mémoire et journal dans un dossier temporaire. Code de sortie 0 = réussi.
# (La partie Python — filtrage de l'utilisateur et des salons, faux client Discord — est dans tests\discord-pont.py, lancée à la fin.)
$ErrorActionPreference = 'Stop'
$env:JARVIS_TEST = '1'
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $Root 'lib\journal.ps1')
$TR = Join-Path $env:TEMP ('jarvis-test-' + [guid]::NewGuid().ToString('N').Substring(0, 8)); New-Item -ItemType Directory $TR, "$TR\memoire", "$TR\logs" | Out-Null; $script:JarvisRoot = $TR
"# To-do de Liam`r`n- [ ] Appeler le comptable" | Set-Content "$TR\memoire\todo.md" -Encoding UTF8; '# Notes' | Set-Content "$TR\memoire\notes.md" -Encoding UTF8; '# R' | Set-Content "$TR\memoire\resume.md" -Encoding UTF8
$Config = Get-Content $(if ($env:JARVIS_CONFIG -and (Test-Path $env:JARVIS_CONFIG)) { $env:JARVIS_CONFIG } else { Join-Path $Root 'config.json' }) -Raw -Encoding UTF8 | ConvertFrom-Json      # (lecture seule : le test ne modifie que l'objet en mémoire)
foreach ($l in 'voix', 'business', 'permissions', 'actions', 'coffre', 'entrees', 'ecrans', 'tableau', 'visage', 'sons', 'raccourcis', 'cerveau', 'cerveau-local', 'veille', 'memoire', 'rapide', 'discretion', 'modejeu', 'competences', 'marche', 'priorite', 'comprehension', 'routeur', 'pc', 'bureau', 'salle-marche', 'matin', 'discord', 'boucle') { . (Join-Path $Root "lib\$l.ps1") }
foreach ($f in (Get-ChildItem (Join-Path $Root 'lib\sources') -Filter '*.ps1' | Where-Object { $_.Name -notlike '_*' })) { . $f.FullName }
[void](Import-Competences)
$script:JarvisRoot = $TR
$script:PolitesseFixe = $true
$echecs = 0
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }
function Fixer([string]$cle, $val) { if ($Config.PSObject.Properties[$cle]) { $Config.$cle = $val } else { $Config | Add-Member -NotePropertyName $cle -NotePropertyValue $val } }

$FAUX_JETON = 'MTIzNDU2Nzg5MDEyMzQ1Njc4.GabcDE.abcdefghijklmnopqrstuvwxyz0123456789ABCD'; $FAUX_UID = '111111111111111111'
$S_JARVIS = '100100000000000001'; $S_TODO = '100200000000000001'; $S_ALERTES = '100300000000000001'
$env:DISCORD_BOT_TOKEN = $FAUX_JETON; $env:DISCORD_USER_ID = $FAUX_UID; $script:Secrets += $FAUX_JETON
$jetonReel = ''; if (Test-Path (Join-Path $Root '.env')) { foreach ($l in (Get-Content (Join-Path $Root '.env') -Encoding UTF8)) { if ($l -match '^\s*DISCORD_BOT_TOKEN\s*=\s*(.*)$') { $jetonReel = $Matches[1].Trim().Trim('"') } } }      # (lu pour VÉRIFIER qu'il n'est nulle part ; jamais affiché)
function Set-Salons($j, $b, $sy, $m) { $Config.discord_salons.jarvis = $j; $Config.discord_salons.business = $b; $Config.discord_salons.systeme = $sy; $Config.discord_salons.marche = $m }      # (identifiants FORCÉS ; l'association automatique passe par le cache discord-salons.json)
function Sortants { @(Get-ChildItem "$TR\memoire\discord\sortant" -Filter '*.json' -File -ErrorAction SilentlyContinue | Sort-Object Name | ForEach-Object { Get-Content $_.FullName -Raw -Encoding UTF8 | ConvertFrom-Json }) }
function Vider { Remove-Item "$TR\memoire\discord\sortant\*", "$TR\memoire\discord\entrant\*" -Force -ErrorAction SilentlyContinue; $script:DiscordFile.Clear(); $script:DiscordReponses.Clear() }
function Poser($obj) { $d = "$TR\memoire\discord\entrant"; if (-not (Test-Path $d)) { New-Item -ItemType Directory $d -Force | Out-Null }; ($obj | ConvertTo-Json -Compress) | Set-Content ("$d\{0:D19}-{1}.json" -f [DateTime]::UtcNow.Ticks, [guid]::NewGuid().ToString('N').Substring(0, 6)) -Encoding UTF8 }
function Pomper { $script:DiscordProchainPump = [datetime]::MinValue; Invoke-PumpDiscord }
function Journal { $f = Join-Path $TR ('logs\journal-{0}.md' -f (Get-Date -Format 'yyyy-MM-dd')); if (Test-Path $f) { Get-Content $f -Raw -Encoding UTF8 } else { '' } }
function Todo { Get-Content "$TR\memoire\todo.md" -Raw -Encoding UTF8 }
function Messages([string]$type = 'message') { @(Sortants | Where-Object { $_.type -eq $type }) }
function Processus-FauxPont { @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match 'faux-pont\.py' }) }

# ----- bouchons : rien de réel ne part (réseau, PC, Claude) -----
$script:Appels = @{ veille = 0; claudecode = 0; chrome = 0 }
function Get-ChiffresBusiness { param($d, [switch]$SansSite) @{ stub = $true } }
function Get-PhrasesBusiness($d) { @('Le site répond.', 'Deux nouveaux abonnés depuis hier.') }
function Invoke-SystemePc([string]$quoi) { if ($quoi -eq 'veille') { $script:Appels.veille++ } }
function Invoke-ClaudeCode([string]$demande, [bool]$essai = $true) { $script:Appels.claudecode++; $script:DernierEssai = $essai; @{ ok = $true } }
function Resolve-Routeur([string]$o) { $script:RouteurEtat = 'desactive'; $script:RouteurRaison = 'bouchon'; $null }
function Test-Ollama { @{ pret = $false; raison = 'bouchon' } }
function Get-StatutSite([int]$timeout = 15) { [pscustomobject]@{ ok = $true; code = 200; detail = '' } }
$script:Actif = $true; $script:ModeJeu = $false
Fixer 'discord_actif' $false; foreach ($n in 'jarvis', 'systeme', 'marche', 'business') { $Config.discord_salons.$n = '' }      # (le test part d'un état neutre, quels que soient les réglages réels de Liam)
$Config.cerveau = 'claude'; $Config.marche_actif = $false
$script:HumourAlea = { 99 }      # pas de blague sauf test dédié (tirage de 0 à 99 ; blague si < humour_pourcent)

# ----- faux pont inoffensif (processus Python) -----
$fauxPont = Join-Path $TR 'faux-pont.py'
@'
import sys, os, time, json, glob
a = sys.argv[1:]
def arg(n, d=''):
    return a[a.index(n) + 1] if n in a else d
ech = arg('--echange'); parent = int(arg('--parent', '0') or 0); q = arg('--quitter-flag')
crash = os.path.join(ech, 'crash.json')
if os.path.exists(crash):
    c = json.load(open(crash, encoding='utf-8-sig'))
    if c.get('stderr'):
        sys.stderr.write(c['stderr'] + '\n'); sys.stderr.flush()
    sys.exit(int(c.get('code', 1)))
import ctypes
def vivant(pid):
    k = ctypes.windll.kernel32; h = k.OpenProcess(0x1000, False, pid)
    if not h: return False
    c = ctypes.c_ulong(); ok = k.GetExitCodeProcess(h, ctypes.byref(c)); k.CloseHandle(h)
    return bool(ok) and c.value == 259
while True:
    if q and os.path.exists(q): break
    if parent and not vivant(parent): break
    for f in glob.glob(os.path.join(ech, 'sortant', '*.json')):
        try:
            if '"type":"arret"' in open(f, encoding='utf-8').read().replace(' ', ''): sys.exit(0)
        except OSError: pass
    time.sleep(0.2)
'@ | Set-Content $fauxPont -Encoding UTF8
$env:JARVIS_PONT_FAUX = $fauxPont

Write-Host '1) Réglages par défaut (config.json) : tout est désactivé et vide'
$vraie = Get-Content (Join-Path $Root 'config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
Verifier ($vraie.PSObject.Properties['discord_actif'] -and $vraie.discord_actif -is [bool]) 'discord_actif existe (false livré par défaut ; réglage de Liam non imposé par le test)'
Verifier (@('jarvis', 'business', 'systeme', 'marche' | Where-Object { $vraie.discord_salons.PSObject.Properties[$_] }).Count -eq 4) 'discord_salons = { jarvis, systeme, marche, business } : quatre champs FACULTATIFS vides (les salons sont associés automatiquement par leur nom)'
Verifier ($vraie.discord_vocal -eq $false -and $vraie.discord_briefing_actif -eq $false) 'discord_vocal = false, briefing Discord désactivé par défaut'
Verifier ($vraie.discord_delai_confirmation_secondes -eq 60 -and $vraie.discord_alertes_max_par_heure -eq 6 -and $vraie.discord_briefing_heure -eq '08:30' -and $vraie.discord_claude_max_par_jour -eq 20) 'délai de confirmation 60 s, 6 alertes par heure, briefing à 08:30, 20 appels à Claude par jour (réglables)'
$c = Get-DiscordConfig
Verifier (-not $c.actif -and $c.salons.Count -eq 0 -and -not $c.vocal) 'lecture de la config : inactif, aucun salon'
Set-Salons $S_JARVIS $S_TODO $S_ALERTES ''; $c = Get-DiscordConfig
Verifier ($c.salons.Count -eq 3 -and $c.salons.jarvis -eq $S_JARVIS -and -not $c.salons.ContainsKey('marche')) 'salons renseignés lus ; un salon vide est ignoré'
Set-Salons 'abc' '12' '' ''; Verifier ((Get-DiscordConfig).salons.Count -eq 0) 'un identifiant invalide (pas un nombre) est ignoré'
Fixer 'discord_delai_confirmation_secondes' 99999; Verifier ((Get-DiscordConfig).delai -eq 300) 'délai de confirmation plafonné (300 s)'; Fixer 'discord_delai_confirmation_secondes' 'abc'; Verifier ((Get-DiscordConfig).delai -eq 60) 'délai illisible : 60 s'
Fixer 'discord_briefing_heure' '25:99'; Verifier ((Get-DiscordConfig).briefing_heure -eq '08:30') 'heure de briefing invalide : 08:30'

Write-Host '2) Jeton ou identifiant absent : poli, une seule fois, sans planter'
Fixer 'discord_actif' $true; Set-Salons $S_JARVIS $S_TODO $S_ALERTES ''
Fixer 'discord_delai_confirmation_secondes' 60
$env:DISCORD_BOT_TOKEN = ''
$id = Get-DiscordIdentifiants
Verifier (-not $id.ok -and $id.manque -contains 'DISCORD_BOT_TOKEN' -and $id.manque -notcontains 'DISCORD_USER_ID') 'jeton vide : seul son NOM est signalé'
$env:DISCORD_BOT_TOKEN = 'xxx'; Verifier (-not (Get-DiscordIdentifiants).ok) 'jeton « xxx » (modèle .env.example) : considéré comme manquant'
$env:DISCORD_BOT_TOKEN = $FAUX_JETON; $env:DISCORD_USER_ID = 'pas-un-nombre'; Verifier ((Get-DiscordIdentifiants).manque -contains 'DISCORD_USER_ID') 'identifiant Discord invalide : signalé'
$env:DISCORD_USER_ID = ''; $env:DISCORD_BOT_TOKEN = ''
$script:Dits = @(); $j0 = (Journal).Length
$r = Start-PontDiscord
$j = (Journal).Substring($j0)
Verifier (-not $r -and $script:PontDesactive -and -not $script:PontProc -and -not $script:DiscordPumpActif) 'pont désactivé, aucun processus'
Verifier ($j -match 'Pont Discord' -and $j -match 'désactivé' -and $j -match 'DISCORD_BOT_TOKEN' -and $j -match 'DISCORD_USER_ID') 'dit au journal quels noms manquent'
Verifier ($j -notmatch [regex]::Escape($FAUX_JETON)) 'aucune valeur secrète dans le journal'
$n1 = ([regex]::Matches((Journal).Substring($j0), 'Parole \(test silencieux\)')).Count
[void](Start-PontDiscord); [void](Start-PontDiscord)
$n2 = ([regex]::Matches((Journal).Substring($j0), 'Parole \(test silencieux\)')).Count
Verifier ($n1 -eq 1 -and $n2 -eq 1) 'Jarvis le dit poliment UNE seule fois (pas de répétition à chaque tentative)'
$script:PontDesactive = $false; $script:PontAnnonceFaite = $false
$env:DISCORD_BOT_TOKEN = $FAUX_JETON; $env:DISCORD_USER_ID = $FAUX_UID
Set-Salons '' '' '' ''; $r = Start-PontDiscord
Verifier ($r -and $script:PontProc -and -not $script:PontDesactive) 'aucun identifiant de salon dans config.json : le pont démarre quand même (il lit lui-même les salons du serveur)'
Stop-PontDiscord; Start-Sleep -Milliseconds 300; Vider
$script:PontDesactive = $false; $script:PontAnnonceFaite = $false; Set-Salons $S_JARVIS $S_TODO $S_ALERTES ''
Fixer 'discord_actif' $false; $r = Start-PontDiscord
Verifier (-not $r -and -not $script:PontProc -and -not $script:PontDesactive) 'discord_actif = false : rien ne démarre, rien n''est dit'
Fixer 'discord_actif' $true

Write-Host '3) Démarrage, arrêt et redémarrage du processus (faux pont)'
$r = Start-PontDiscord
Verifier ($r -and $script:PontProc -and -not $script:PontProc.HasExited -and $script:DiscordPumpActif) 'pont démarré (processus séparé) quand discord_actif = true et identifiants présents'
Verifier ((Test-Path (Get-FichierPidPont)) -and @(Processus-FauxPont).Count -ge 1) 'PID enregistré dans memoire\discord-pont.pid'
$cl = (Processus-FauxPont)[0].CommandLine
Verifier ($cl -notmatch [regex]::Escape($FAUX_JETON) -and $cl -notmatch 'DISCORD_BOT_TOKEN' -and $cl -match '--parent') 'le jeton n''est PAS dans la ligne de commande du pont (il passe par l''environnement)'
$pid1 = $script:PontProc.Id
Stop-PontDiscord
Start-Sleep -Milliseconds 300
Verifier ($null -eq $script:PontProc -and -not (Get-Process -Id $pid1 -ErrorAction SilentlyContinue) -and @(Processus-FauxPont).Count -eq 0 -and -not (Test-Path (Get-FichierPidPont))) 'arrêt de Jarvis : le pont s''arrête, plus de processus, PID effacé'
# plantage -> redémarrage seul avec délai, journal sans jeton
Vider; New-Item -ItemType Directory "$TR\memoire\discord" -Force | Out-Null
(@{ code = 1; stderr = "Traceback... token=$FAUX_JETON et Bot $FAUX_JETON" } | ConvertTo-Json -Compress) | Set-Content "$TR\memoire\discord\crash.json" -Encoding UTF8
$script:PontPannes.Clear(); $script:PontDesactive = $false; $script:PontCoupeUrgence = $false; $script:PontProchainEssai = [datetime]::MinValue
[void](Start-PontDiscord); $script:PontProc.WaitForExit(15000) | Out-Null; $j0 = (Journal).Length
Update-PontDiscord
$j = (Journal).Substring($j0)
Verifier ($null -eq $script:PontProc -and $script:PontPannes.Count -eq 1 -and $j -match 'arrêté \(code 1\)' -and $j -match 'redémarrage dans 5 s') 'le pont plante : noté au journal, redémarrage prévu dans 5 s'
Verifier ($j -notmatch [regex]::Escape($FAUX_JETON) -and $j -match '\[SECRET\]') 'journal d''erreurs : le jeton (même dans l''erreur du pont) est masqué'
Verifier ($script:PontProchainEssai -gt (Get-Date).AddSeconds(2) -and $script:PontProchainEssai -lt (Get-Date).AddSeconds(7)) 'délai avant le nouvel essai respecté'
Update-PontDiscord; Verifier ($null -eq $script:PontProc) 'pas de redémarrage avant la fin du délai'
Remove-Item "$TR\memoire\discord\crash.json" -Force; $script:PontProchainEssai = (Get-Date).AddSeconds(-1)
Update-PontDiscord
Verifier ($script:PontProc -and -not $script:PontProc.HasExited -and $script:DiscordPumpActif) 'après le délai, le pont est redémarré seul'
Stop-PontDiscord
# décisions pures
$p = New-Object System.Collections.Generic.List[datetime]; $now = Get-Date
$d = @(); for ($i = 1; $i -le 7; $i++) { $p.Add($now.AddSeconds($i)); $d += (Get-DecisionRedemarragePont 1 $p $now.AddSeconds($i)) }
Verifier (($d[0..4] | ForEach-Object { $_.delai_s }) -join ',' -eq '5,15,30,60,120' -and $d[0].action -eq 'redemarrer') 'délais de redémarrage croissants : 5, 15, 30, 60, 120 s'
Verifier ($d[5].action -eq 'abandon' -and $d[5].raison -match '10 minutes') 'plus de 5 plantages en 10 minutes : abandon (pas de boucle infinie)'
Verifier ((Get-DecisionRedemarragePont 3 (New-Object System.Collections.Generic.List[datetime])).action -eq 'abandon' -and (Get-DecisionRedemarragePont 2 (New-Object System.Collections.Generic.List[datetime])).action -eq 'abandon' -and (Get-DecisionRedemarragePont 0 (New-Object System.Collections.Generic.List[datetime])).action -eq 'fin') 'jeton refusé (3), identifiants manquants (2) : pas de redémarrage ; arrêt normal : pas de redémarrage'
$old = New-Object System.Collections.Generic.List[datetime]; 1..6 | ForEach-Object { $old.Add($now.AddMinutes(-30)) }
Verifier ((Get-DecisionRedemarragePont 1 $old $now).action -eq 'redemarrer') 'de vieux plantages (plus de 10 minutes) ne comptent plus'
# code 3 : abandon + dit poliment
$script:PontPannes.Clear(); $script:PontDesactive = $false; $script:PontAnnonceFaite = $false; $script:PontProchainEssai = [datetime]::MinValue
(@{ code = 3; stderr = '[pont] connexion refusée' } | ConvertTo-Json -Compress) | Set-Content "$TR\memoire\discord\crash.json" -Encoding UTF8
[void](Start-PontDiscord); $script:PontProc.WaitForExit(15000) | Out-Null; Update-PontDiscord
Verifier ($script:PontDesactive -and $null -eq $script:PontProc -and (Journal) -match 'connexion refusée par Discord') 'connexion refusée (code 3) : pont abandonné proprement, raison au journal'
Remove-Item "$TR\memoire\discord\crash.json" -Force; $script:PontDesactive = $false; $script:PontAnnonceFaite = $false

Write-Host '3 bis) Salons associés automatiquement (cache memoire\discord-salons.json)'
Vider; Set-Salons '' '' '' ''; $script:DiscordPumpActif = $true
$CJ = '120000000000000001'; $CS = '120000000000000002'; $CM = '120000000000000003'; $CB = '120000000000000004'
function Ecrire-CacheSalons($salons, $manquants) { [IO.File]::WriteAllText("$TR\memoire\discord-salons.json", (@{ serveur = '900'; salons = $salons; manquants = @($manquants); ts = 1 } | ConvertTo-Json -Depth 4 -Compress), [Text.UTF8Encoding]::new($false)) }
Remove-Item "$TR\memoire\discord-salons.json" -Force -ErrorAction SilentlyContinue
Verifier ((Get-DiscordConfig).salons.Count -eq 0 -and (Get-DiscordConfig).manquants.Count -eq 4) 'sans cache ni identifiant forcé : aucun salon, quatre introuvables'
Verifier ((Update-SalonsManquants) -eq $false) '…mais rien n''est dit tant que le pont n''a pas lu les salons du serveur'
Ecrire-CacheSalons @{ jarvis = $CJ; systeme = $CS } @('marche', 'business')
$c = Get-DiscordConfig
Verifier ($c.salons.jarvis -eq $CJ -and $c.salons.systeme -eq $CS -and ($c.manquants -join ',') -eq 'marche,business') 'les salons associés par le pont sont lus dans le cache'
Set-Salons '130000000000000009' '' '' ''; Verifier ((Get-DiscordConfig).salons.jarvis -eq '130000000000000009' -and (Get-DiscordConfig).salons.systeme -eq $CS) 'un identifiant forcé dans config.json est prioritaire sur le cache'
Set-Salons '' '' '' ''
$Config.discord_salons | Add-Member -NotePropertyName alertes -NotePropertyValue '140000000000000001' -Force; Verifier ((Get-DiscordConfig).salons.systeme -eq '140000000000000001') 'l''ancien champ « alertes » reste accepté (= système)'
$Config.discord_salons.PSObject.Properties.Remove('alertes')
Poser @{ type = 'message'; id = '31'; canal = 'systeme'; canal_id = $CS; auteur = $FAUX_UID; texte = 'statut' }
Poser @{ type = 'message'; id = '32'; canal = 'marche'; canal_id = $CM; auteur = $FAUX_UID; texte = 'statut' }
Pomper
Verifier ($script:DiscordFile.Count -eq 1 -and (Get-OrdreDiscord).canal -eq 'systeme') 'seuls les salons associés sont écoutés (« marche » introuvable : ignoré)'
$script:Dits = @(); $j0 = (Journal).Length; Vider
$r1 = Update-SalonsManquants; $r2 = Update-SalonsManquants
$j = (Journal).Substring($j0); $m = @(Messages)
Verifier ($r1 -and -not $r2 -and $m.Count -eq 1 -and $m[0].canal -eq 'jarvis' -and $m[0].texte -match 'marche, business') 'salon introuvable : Jarvis le dit poliment UNE seule fois, dans « jarvis »'
Verifier (([regex]::Matches($j, 'Parole \(test silencieux\)')).Count -eq 1 -and $j -match 'Je replie ces messages vers « jarvis »') '…et le dit à voix haute / au journal une fois'
Vider
[void](Send-MessageDiscord 'marche' 'Résumé du marché'); [void](Send-MessageDiscord 'business' 'Revenus')
$m = @(Messages)
Verifier ($m.Count -eq 2 -and (@($m | Where-Object { $_.canal -eq 'jarvis' }).Count -eq 2)) 'les messages d''un salon introuvable sont repliés vers « jarvis »'
Ecrire-CacheSalons @{ jarvis = $CJ; systeme = $CS; marche = $CM; business = $CB } @()
Verifier ((Get-DiscordConfig).salons.Count -eq 4 -and (Update-SalonsManquants) -eq $false) 'salon recréé ou renommé : repris au prochain relevé, plus rien d''introuvable'
Vider; [void](Send-MessageDiscord 'marche' 'Cours'); Verifier ((Messages).canal -eq 'marche') '…et les messages repartent dans « marche »'
Ecrire-CacheSalons @{ jarvis = $CJ; systeme = $CS; business = $CB } @('marche')
Verifier ((Update-SalonsManquants) -eq $true) 'un salon supprimé ou renommé plus tard est signalé de nouveau (une fois)'
Verifier ((Get-Content "$TR\memoire\discord-salons.json" -Raw) -notmatch [regex]::Escape($FAUX_JETON)) 'le cache ne contient aucun secret (identifiants de salons seulement)'
Remove-Item "$TR\memoire\discord-salons.json" -Force; $script:SalonsManquantsDits = ''
Set-Salons $S_JARVIS $S_TODO $S_ALERTES ''; Vider

Write-Host '4) Réception : Liam seul, salons listés (revérifié côté Jarvis)'
Vider; $script:DiscordPumpActif = $true
Poser @{ type = 'message'; id = '1'; canal = 'jarvis'; canal_id = $S_JARVIS; auteur = $FAUX_UID; texte = 'statut' }
Pomper
Verifier ($script:DiscordFile.Count -eq 1 -and (Get-OrdreDiscord).texte -eq 'statut') 'un message de Liam dans un salon listé est mis en file'
Poser @{ type = 'message'; id = '2'; canal = 'jarvis'; canal_id = $S_JARVIS; auteur = '999999999999999999'; texte = 'supprime tout le disque' }
Pomper
Verifier ($script:DiscordFile.Count -eq 0) 'un autre auteur (même si le pont le laissait passer) : ignoré'
Verifier ((Journal) -notmatch 'supprime tout le disque') 'son contenu n''est écrit nulle part'
Poser @{ type = 'message'; id = '3'; canal = 'jarvis'; canal_id = '777'; auteur = $FAUX_UID; texte = 'statut' }
Poser @{ type = 'message'; id = '4'; canal = 'marche'; canal_id = '100400000000000001'; auteur = $FAUX_UID; texte = 'statut' }
Poser @{ type = 'message'; id = '5'; canal = 'inconnu'; canal_id = $S_JARVIS; auteur = $FAUX_UID; texte = 'statut' }
Pomper
Verifier ($script:DiscordFile.Count -eq 0) 'salon non listé, salon vide ou nom inconnu : ignoré'
Poser @{ type = 'message'; id = '6'; canal = 'business'; canal_id = $S_TODO; auteur = $FAUX_UID; texte = ('x' * 1500) }
Pomper; $m = Get-OrdreDiscord
Verifier ($m.canal -eq 'business' -and $m.texte.Length -eq 1000) 'salon « business » reconnu ; texte limité à 1000 caractères'
"{pas du json" | Set-Content "$TR\memoire\discord\entrant\0000-casse.json" -Encoding UTF8; Pomper
Verifier (@(Get-ChildItem "$TR\memoire\discord\entrant" -File -ErrorAction SilentlyContinue).Count -eq 0 -and $script:DiscordFile.Count -eq 0) 'fichier illisible : supprimé sans planter'
Poser @{ type = 'stop'; canal = 'jarvis'; auteur = $FAUX_UID }; Pomper
Verifier (Test-Stop) '« stop » : le drapeau d''arrêt d''urgence est posé tout de suite'
Remove-Item $script:StopFlag -Force -ErrorAction SilentlyContinue; Vider
$script:DiscordPumpActif = $false; Poser @{ type = 'message'; id = '7'; canal = 'jarvis'; canal_id = $S_JARVIS; auteur = $FAUX_UID; texte = 'statut' }
$PumpReel = ${function:Invoke-Pump}; $script:DiscordPumpActif = $true; $script:DiscordProchainPump = [datetime]::MinValue
try { & $PumpReel } catch { Write-Host "  (pompe réelle : $($_.Exception.Message))" }
Verifier ($script:DiscordFile.Count -eq 1) 'Invoke-Pump (la vraie) lit le dossier du pont quand il tourne'
$script:DiscordFile.Clear(); $script:DiscordPumpActif = $false; Poser @{ type = 'message'; id = '8'; canal = 'jarvis'; canal_id = $S_JARVIS; auteur = $FAUX_UID; texte = 'statut' }
try { & $PumpReel } catch {}
Verifier ($script:DiscordFile.Count -eq 0) 'pont arrêté : Jarvis ne lit rien (aucune lecture inutile)'
Vider; $script:DiscordPumpActif = $true

Write-Host '5) Commandes en texte libre (même compréhension que la voix, réponse écrite)'
$script:BriefingMatin = @{ date = (Get-Date).ToString('yyyy-MM-dd'); parle = @('Bonjour monsieur.', 'Trois nouveaux quiz.', 'Deux nouveaux abonnés.', 'Le site répond.', 'Une cinquième phrase.'); lignes = @(); details = @() }
Vider; $j0 = (Journal).Length
Invoke-OrdreDiscord 'statut' 'jarvis' '11'
$msg = @(Messages)

$ch = @($msg[0].embed.champs | ForEach-Object { "$($_.nom)=$($_.valeur)" }) -join ' | '
Verifier ($msg.Count -eq 1 -and $msg[0].canal -eq 'jarvis' -and $msg[0].reply_to -eq '11' -and $msg[0].embed.titre -match 'Jarvis · statut' -and $ch -match 'Mode=Actif' -and $ch -match 'Discord=' -and $ch -match 'Tâches=1 tâche ouverte' -and $ch -match "Appels à Claude aujourd'hui=0 sur 20" -and $msg[0].embed.couleur -match '^(3066993|15105570)$') '« statut » : embed « Jarvis · statut », champs Mode / Cerveau / Discord / Tâches / Marché / Appels à Claude, chaque chiffre avec son mot' 
Verifier ($msg[0].embed.pied -match '\d\d/\d\d/\d{4} \d\d:\d\d') '…avec la date en pied'
$j = (Journal).Substring($j0)
Verifier ($j -notmatch 'Parole \(') 'la réponse est ÉCRITE : Jarvis ne prononce rien à voix haute'
Verifier ($null -eq $script:CanalDiscord) 'le contexte Discord est levé après l''ordre (la voix redevient normale)'
Vider; Invoke-OrdreDiscord 'Jarvis, briefing' 'jarvis'
$e = (Messages)[0].embed
Verifier ($e.titre -match 'Briefing' -and $e.description -match 'Bonjour monsieur' -and $e.description -match 'Trois nouveaux quiz' -and $e.description -match 'Le site répond' -and $e.description -notmatch 'cinquième' -and $e.description -notmatch '```') '« briefing » : embed ☀️ avec 4 phrases au plus, sans bloc de code' 
Vider; $j1 = (Journal).Length; Invoke-OrdreDiscord 'ajoute acheter du pain à ma to-do' 'business'
Verifier (((Journal).Substring($j1) -match 'Réponse écrite \(Discord\)') -and ((Journal).Substring($j1) -notmatch 'Parole \(')) 'une réponse qui passe par Parler est écrite sur Discord (« Réponse écrite »), jamais prononcée'
Verifier ((Todo) -match '\[ \] acheter du pain' -and (Messages)[0].canal -eq 'business' -and @(Messages).Count -eq 1) 'ajouter une tâche : écrite dans la to-do, réponse dans le salon d''où vient l''ordre'
Verifier (@(Messages 'confirmation').Count -eq 0) '…sans demander de confirmation (action libre)'
Vider; Invoke-OrdreDiscord 'lis ma to-do' 'business'
$e = (Messages)[0].embed
Verifier ($e.titre -match 'Tes tâches' -and $e.description -match "☐ 1 · Appeler le comptable" -and $e.description -match "☐ 2 · acheter du pain" -and $e.description -notmatch '```' -and $e.pied -match '2 ouvertes' -and $e.pied -match 'Aucune terminée') 'to-do : une ligne par tâche (☐ 1 · Texte), pied « 2 ouvertes · Aucune terminée »' 
Vider; Invoke-OrdreDiscord "j'ai fini acheter du pain" 'business'
Verifier ((Todo) -match '\[[xX]\] acheter du pain' -and (Todo) -match '\[ \] Appeler le comptable') 'terminer une tâche : cochée, les autres intactes'
Vider; Invoke-OrdreDiscord 'stats du SaaS' 'jarvis'
Verifier ((Messages)[0].texte -match 'Le site répond' -and (Messages)[0].texte -match 'Deux nouveaux abonnés') '« stats du SaaS » : lecture seule (bouchon des chiffres)'
# où en est X : lecture seule, avec source et date
$cours = @{ nom = 'Thales'; symbole = 'HO'; prix = 150.2; devise = 'EUR'; variation_pct = 1.5; date = (Get-Date).ToString('o'); source = 'Alpha Vantage' }
function Get-RaisonMarche { '' }
function Read-DernierReleve { [pscustomobject]@{ cours = @([pscustomobject]$cours); actus = @(); erreurs = @() } }
Set-Salons $S_JARVIS $S_TODO $S_ALERTES '100400000000000001'; Vider; Invoke-OrdreDiscord 'où en est Thales ?' 'marche'
$msg = @(Messages)
$e = $msg[0].embed
$ch = @($e.champs | ForEach-Object { "$($_.nom)=$($_.valeur)" }) -join ' | '
Verifier ($msg.Count -eq 1 -and $e.titre -match 'Thales' -and $e.description -match 'En hausse de 1,5 % aujourd''hui' -and $ch -match 'Dernier cours=150,2 euros' -and $ch -match "Aujourd'hui=\+1,5 %" -and $e.pied -match 'Source : Alpha Vantage · \d\d/\d\d' -and $e.description -notmatch '```') '« où en est Thales » : phrase explicative, champs Dernier cours / Aujourd''hui, pied « Source : Alpha Vantage · jour/mois »' 
Verifier ($e.couleur -eq 3066993 -and $e.titre.StartsWith([char]::ConvertFromUtf32(0x1F4C8))) '…vert et 📈 pour une hausse'
Verifier ($msg[0].canal -eq 'marche') 'réponse dans le salon « marche » d''où vient la demande'
Verifier (@(Messages 'confirmation').Count -eq 0 -and $msg[0].texte -notmatch '(?i)acheter|vendre|conseil') 'lecture seule : aucune confirmation, aucun conseil d''achat ou de vente'
Set-Salons $S_JARVIS $S_TODO $S_ALERTES ''
Vider; Invoke-OrdreDiscord 'dois-je acheter Thales ?' 'jarvis'
Verifier ((Messages)[0].texte -match '(?i)conseil|ne donne|verdict') 'une question d''achat : refus de conseil (règle existante conservée)'
Vider; Invoke-OrdreDiscord 'ok merci' 'jarvis'
Verifier ((Messages)[0].texte -match '\S') 'un simple remerciement : une réponse polie (règles locales, aucun appel IA)'
Vider; Invoke-OrdreDiscord 'stop' 'jarvis'
Verifier ((Test-Stop) -and (Messages)[0].texte -match 'Arrêt d''urgence') '« stop » en texte : arrêt d''urgence demandé'
Remove-Item $script:StopFlag -Force -ErrorAction SilentlyContinue
# sourdine : réponse écrite seulement, aucune action
Vider; $script:Actif = $false; $avant = Todo
Invoke-OrdreDiscord 'ajoute ranger le bureau à ma to-do' 'business'
Verifier ((Todo) -eq $avant -and (Messages)[0].texte -match '(?i)sourdine') 'Jarvis en sourdine : aucune action exécutée, le dit'
$script:Actif = $true

Write-Host '5 bis) Présentation : lignes courtes, puces, gras, embeds, emojis rares'
$E_OK = [char]::ConvertFromUtf32(0x2705); $E_WARN = [char]::ConvertFromUtf32(0x26A0) + [char]::ConvertFromUtf32(0xFE0F)
$t = Format-ReponseDiscord @('Bonjour monsieur. Trois nouveaux quiz. Deux nouveaux abonnés. Le site répond.')
Verifier (($t -split "`n").Count -eq 4) 'une idée par ligne : 4 phrases -> 4 lignes'
$t = Format-ReponseDiscord @('Vous avez 3 tâches : appeler le comptable ; acheter du pain ; ranger le bureau.')
Verifier ($t -match "^Vous avez 3 tâches :\n• appeler le comptable\n• acheter du pain\n• ranger le bureau$") 'énumération : liste à puces'
Verifier ((Format-ReponseDiscord @('- un', '- deux')) -eq "• un`n• deux") 'tirets -> puces'
$t = Format-ReponseDiscord @('Le cours bouge de +3,2 % pour 150,2 euros.')
Verifier ($t -match '\*\*\+3,2 %\*\*' -and $t -match '\*\*150,2 euros\*\*') 'l''essentiel (variations, montants) est en gras'
Verifier ((Format-GrasDiscord '**déjà gras** 3 %') -eq '**déjà gras** 3 %') 'une ligne déjà en gras n''est pas retouchée'
$long = Format-ReponseDiscord @(1..200 | ForEach-Object { "Phrase numéro $_." })
Verifier ($long.Length -le 1510 -and $long.EndsWith('…')) 'pas de pavé : 1500 caractères au plus, coupé proprement'
Verifier ((Format-ReponseDiscord @("C'est fait.")).StartsWith($E_OK + ' ')) 'action faite : ✅ en tête'
Verifier ((Format-ReponseDiscord @('Mon plafond quotidien est atteint.')).StartsWith($E_WARN + ' ')) 'refus poli / annulation : ⚠️ en tête'
$g = Format-ReponseDiscord @('Une erreur est survenue, monsieur.'); $g2 = Format-ReponseDiscord @("Arrêt d'urgence demandé, monsieur.")
$emo = '[' + [char]0x2600 + '-' + [char]0x27BF + [char]0xD800 + '-' + [char]0xDFFF + ']'
Verifier ($g -notmatch $emo -and $g2 -notmatch $emo) 'erreur grave, arrêt d''urgence : AUCUN emoji'
$tous = (Format-ReponseDiscord @("C'est fait.", 'Autre chose.', 'Encore.')); Verifier ((@([regex]::Matches($tous, $emo)).Count) -le 2) 'un emoji au plus par message (✅ = 1 caractère, ⚠️ = 2)'
# embeds
Vider; Invoke-OrdreDiscord 'statut' 'jarvis'
$e = (Messages)[0].embed

Verifier ($e.titre.StartsWith([char]::ConvertFromUtf32(0x1F9E0)) -and $e.description -notmatch '```' -and @($e.champs).Count -ge 3 -and @($e.champs).Count -le 6) 'statut : titre 🧠, aucun bloc de code, 3 à 6 champs' 
$script:Actif = $false; Vider; Invoke-OrdreDiscord 'statut' 'jarvis'; $script:Actif = $true
Verifier ((Messages)[0].embed.couleur -eq 15105570) 'statut en sourdine : orange'
Vider; $cours.variation_pct = -2.4; Invoke-OrdreDiscord 'où en est Thales ?' 'jarvis'
$e = (Messages)[0].embed
Verifier ($e.couleur -eq 15158332 -and $e.titre.StartsWith([char]::ConvertFromUtf32(0x1F4C9)) -and $e.description -match 'En baisse de 2,4 %' -and (@($e.champs | ForEach-Object { $_.valeur }) -join ' ') -match '−2,4 %') 'baisse : rouge, 📉, phrase « En baisse de 2,4 % », variation signée dans un champ' 
Vider; $cours.variation_pct = 0; Invoke-OrdreDiscord 'où en est Thales ?' 'jarvis'
Verifier ((Messages)[0].embed.couleur -eq 9807270) 'variation nulle : gris'
$cours.variation_pct = 1.5
function Get-RaisonMarche { 'La veille du marché est désactivée.' }
Vider; Invoke-OrdreDiscord 'où en est Thales ?' 'jarvis'
$e = (Messages)[0].embed
Verifier ($e.titre -match 'Pas de données' -and $e.couleur -eq 15105570 -and $e.description -match 'Que faire' -and $e.description -match 'marche_actif' -and -not (Messages)[0].texte) 'sans données de marché : message clair qui dit quoi faire (activer marche_actif, ajouter la clé)' 
function Get-RaisonMarche { '' }
$eb = New-EmbedDiscord 'T' "Bonjour $FAUX_JETON" 1 @(@{ nom = 'a'; valeur = ('v' * 3000) }, @{ nom = ''; valeur = 'x' }) 'p'
Verifier ($eb.description -notmatch [regex]::Escape($FAUX_JETON) -and $eb.champs.Count -eq 1 -and $eb.champs[0].valeur.Length -le 1024) 'embed : jeton masqué, champ vide écarté, longueur bornée'
# confirmations courtes (inchangées)
Verifier ((Get-Content (Join-Path $Root 'pont-discord\pont_logique.py') -Raw -Encoding UTF8) -match 'EMOJI_OUI, EMOJI_NON, delai') 'les confirmations restent courtes, avec ✅ / ❌'

# modèles d'embed : limites, absence de bloc de code, chiffres toujours accompagnés d'un mot, couleurs, style « texte », aperçu
$apercu = @(Get-ModelesApercu)
Verifier ($apercu.Count -ge 12) "aperçu : $($apercu.Count) modèles avec données fictives (statut ×2, to-do ×2, marché ×3, briefing, confirmation, alertes ×2, erreur, refus)"
$tousEmbeds = @($apercu | Where-Object { $_.embed } | ForEach-Object { $_.embed })
$total = { param($e) $n = "$($e.titre)".Length + "$($e.description)".Length + "$($e.pied)".Length; foreach ($c in @($e.champs)) { $n += "$($c.nom)".Length + "$($c.valeur)".Length }; $n }
Verifier (($tousEmbeds | Where-Object { $_.titre.Length -gt 256 -or $_.description.Length -gt 2000 -or @($_.champs).Count -gt 6 -or (& $total $_) -gt 6000 -or ($_.champs | Where-Object { $_.valeur.Length -gt 1024 -or $_.nom.Length -gt 256 }) }).Count -eq 0) 'limites : titre 256, description 2000, champs 1024, 6 champs au plus, 6000 caractères au total'
Verifier (@($tousEmbeds | Where-Object { ("$($_.description)" + (@($_.champs) | ForEach-Object { $_.valeur }) -join ' ') -match '```' }).Count -eq 0) 'aucun bloc de code, aucun tableau en espaces dans les modèles'
Verifier (@($tousEmbeds | Where-Object { $_.titre -match '^[A-Za-z0-9]' }).Count -eq 0) 'chaque titre commence par une icône'
$st = $apercu[0].embed
$chs = @($st.champs | ForEach-Object { "$($_.nom)=$($_.valeur)" }) -join ' | '
Verifier ($st.titre -match 'Jarvis · statut' -and $chs -match 'Cerveau=Local \+ cloud' -and $chs -match 'Discord=Connecté' -and $chs -match 'Tâches=4 tâches ouvertes' -and $chs -match 'Appels à Claude aujourd.hui=3 sur 20\n█' -and $st.couleur -eq 3066993) 'statut : « Local + cloud », « Connecté », « 4 tâches ouvertes », « 3 sur 20 » avec barre █░, vert'
Verifier ($chs -notmatch '(?i)hybride|pont|étage' -and $st.description -match 'Tout va bien') 'statut : aucun jargon (hybride, pont, étage)'
$st2 = $apercu[1].embed
Verifier ($st2.couleur -eq 15105570 -and $st2.description -match 'sourdine' -and ((@($st2.champs | ForEach-Object { $_.valeur }) -join ' ') -match 'Aucune tâche ouverte') -and ((@($st2.champs | ForEach-Object { $_.valeur }) -join ' ') -match '17 sur 20')) 'statut avec souci : orange, phrase qui explique, « Aucune tâche ouverte »'
Verifier ((Get-BarreDiscord 8 20) -eq '████░░░░░░' -and (Get-BarreDiscord 0 20) -eq '░░░░░░░░░░' -and (Get-BarreDiscord 40 20) -eq '██████████') 'barre █░ : 8 sur 20 = 4 cases sur 10 ; bornée'
Verifier ((Get-MotNombre 1 'tâche ouverte' 'tâches ouvertes') -eq '1 tâche ouverte' -and (Get-MotNombre 16 'tâche ouverte' 'tâches ouvertes') -eq '16 tâches ouvertes' -and (Get-MotNombre 0 'x' 'xs' 'Aucune') -eq 'Aucune') 'un nombre est toujours suivi de son mot (« 16 tâches ouvertes », jamais « 16 »)'
$td = $apercu[3].embed; $lt = @($td.description -split "`n")
Verifier ($lt.Count -eq 11 -and $lt[0] -match '^☐ 1 · ' -and $lt[10] -eq '… et 2 autres' -and $td.pied -match '10 ouvertes · 2 terminées') 'to-do de 12 tâches : 10 lignes puis « … et 2 autres », pied « 10 ouvertes · 2 terminées »'
Verifier ((New-EmbedTodo @(@{ texte = 'fini'; fait = $true })).description -match '^☑ 1 · fini$') 'tâche terminée : ☑'
Verifier ((New-EmbedTodo @()).description -match 'Aucune tâche' -and (New-EmbedTodo @()).couleur -eq 3066993) 'to-do vide : message clair'
$mb = $apercu[4].embed; $cm = @($mb.champs | ForEach-Object { "$($_.nom)=$($_.valeur)" }) -join ' | '
Verifier ($mb.titre.StartsWith([char]::ConvertFromUtf32(0x1F4C9)) -and $mb.couleur -eq 15158332 -and $mb.description -eq 'En baisse de 3,2 % sur la semaine.' -and $cm -match 'Dernier cours=150,2 EUR' -and $cm -match 'Aujourd.hui=−0,8 %' -and $cm -match '1 semaine=−3,2 %' -and $cm -match '1 mois=\+1,1 %' -and $mb.pied -match '^Source : Alpha Vantage · \d\d/\d\d$') 'marché en baisse : 📉, rouge, « En baisse de 3,2 % sur la semaine », champs jour / semaine / mois signés, pied source + jour/mois'
$mh = $apercu[5].embed
Verifier ($mh.titre.StartsWith([char]::ConvertFromUtf32(0x1F4C8)) -and $mh.couleur -eq 3066993 -and $mh.description -eq "En hausse de 1,5 % aujourd'hui.") 'marché en hausse : 📈, vert, phrase sur la période disponible'
Verifier ((New-EmbedMarche @{ nom = 'X'; prix = 10; devise = 'EUR'; var_jour = 0; var_sem = $null; var_mois = $null; source = 'S'; date = (Get-Date) }).couleur -eq 9807270) 'marché stable : gris'
Verifier ($apercu[6].embed.couleur -eq 15105570 -and $apercu[6].embed.description -match 'Que faire') 'marché sans données : orange, « Que faire »'
Verifier ((New-EmbedMarcheVide 'X' 'clé ALPHAVANTAGE_KEY absente').description -match 'ALPHAVANTAGE_KEY' -and (New-EmbedMarcheVide 'X' 'désactivée').description -match 'marche_actif') 'sans données : la bonne consigne selon la cause (clé ou marche_actif)'
$br = $apercu[7].embed; $cb = @($br.champs | ForEach-Object { $_.nom }) -join ' | '
Verifier ($br.titre -match 'Briefing du matin' -and $br.titre.StartsWith([char]::ConvertFromUtf32(0x2600)) -and $cb -match 'SaaS' -and $cb -match 'Marché' -and $cb -match 'À faire' -and $br.description -match '\n\n' -and ($br.description -split "`n`n").Count -le 4 -and $br.description -notmatch '(?i)acheter|vendre|conseil') 'briefing : ☀️, 4 phrases au plus séparées par une ligne vide, champs SaaS / Marché / À faire, aucun verdict'
Verifier ($apercu[8].texte -match '✅' -and -not $apercu[8].embed) 'confirmation : texte court avec ✅ / ❌, sans embed'
$al = $apercu[9].embed; $ag = $apercu[10].embed
Verifier ($al.titre -match '^⚠️ Alerte' -and $al.couleur -eq 15105570 -and $al.description -match 'Que faire' -and $ag.couleur -eq 15158332) 'alertes : titre ⚠️, orange (seuil) ou rouge (processus suspect), une phrase qui dit quoi faire'
Verifier ($apercu[11].embed.couleur -eq 15158332 -and $apercu[11].embed.titre -match '^⚠️' -and $apercu[11].embed.description -match 'Que faire' -and $apercu[12].embed.couleur -eq 15105570) 'erreur : rouge ; refus : orange ; titre ⚠️ et « Que faire »'
$e6 = New-EmbedDiscord 'T' ('x' * 2500) 1 @(1..8 | ForEach-Object { @{ nom = "N$_"; valeur = ('v' * 900) } }) 'p'
Verifier ((& $total $e6) -le 6000 -and $e6.description.Length -le 2000) 'une réponse énorme est ramenée sous 6000 caractères'
# style « texte »
Fixer 'discord_style' 'texte'
Verifier ((Get-DiscordStyle) -eq 'texte') 'discord_style = texte reconnu'
Vider; Invoke-OrdreDiscord 'statut' 'jarvis'; $mt = @(Messages)
Verifier ($mt.Count -eq 1 -and -not $mt[0].embed -and $mt[0].texte -match 'Jarvis est actif' -and $mt[0].texte -notmatch '```') 'style « texte » : statut en texte simple, aucun embed'
Vider; Invoke-OrdreDiscord 'lis ma to-do' 'jarvis'; $mt = @(Messages)
Verifier (-not $mt[0].embed -and $mt[0].texte -match 'Tâches ouvertes') 'style « texte » : to-do en texte simple'
Vider; Invoke-OrdreDiscord 'où en est Thales ?' 'jarvis'; $mt = @(Messages)
Verifier (-not $mt[0].embed -and $mt[0].texte -match 'Alpha Vantage') 'style « texte » : cours en texte simple (source indiquée)'
Vider; Invoke-OrdreDiscord 'briefing' 'jarvis'; $mt = @(Messages)
Verifier (-not $mt[0].embed -and $mt[0].texte -match 'Trois nouveaux quiz') 'style « texte » : briefing en texte simple'
Vider; [void](Send-AlerteDiscord 'kt' 'Alerte de test : processus inconnu'); $mt = @(Messages)
Verifier ($mt.Count -eq 1 -and -not $mt[0].embed -and $mt[0].texte -match '^Alerte, monsieur') 'style « texte » : alerte en texte simple'
Fixer 'discord_style' 'embed'
Verifier ((Get-DiscordStyle) -eq 'embed' -and $vraie.discord_style -eq 'embed') 'style « embed » par défaut (config.json)'
# erreurs et refus : embed rouge / orange
Vider; $script:CanalDiscord = 'jarvis'; $script:DiscordTampon = New-Object System.Collections.Generic.List[string]
Add-TamponDiscord "Je n'ai pas pu joindre mon cerveau, monsieur. Veuillez réessayer."; Send-TamponDiscord; $m = @(Messages)[0]
Verifier ($m.embed.couleur -eq 15158332 -and $m.embed.titre -match '^⚠️ Un souci' -and $m.embed.description -match 'Que faire') 'une erreur écrite devient un embed rouge avec « Que faire »'
Add-TamponDiscord "Cela ne se fait pas depuis Discord, monsieur."; Vider; Send-TamponDiscord
$script:DiscordTampon = New-Object System.Collections.Generic.List[string]; Vider
Add-TamponDiscord "Mon plafond quotidien est atteint, monsieur."; Send-TamponDiscord; $m = @(Messages)[0]
Verifier ($m.embed.couleur -eq 15105570 -and $m.embed.titre -match '^⚠️ Je ne peux pas') 'un refus devient un embed orange'
$script:DiscordTampon = New-Object System.Collections.Generic.List[string]; Vider
Add-TamponDiscord "Arrêt d'urgence demandé, monsieur."; Send-TamponDiscord; $m = @(Messages)[0]
Verifier (-not $m.embed -and $m.texte -match 'urgence') 'un arrêt d''urgence reste un texte simple (ce n''est pas une erreur)'
$script:CanalDiscord = $null; $script:DiscordTampon = $null
# aucune blague sur erreurs, refus, tâches (même à 100 %)
Fixer 'humour_pourcent' 100; $script:HumourAlea = { 0 }
Vider; Invoke-OrdreDiscord 'statut' 'jarvis'; Verifier ((Messages)[0].texte -match '^\*') 'statut : une blague est possible (100 % réglé)'
Vider; Invoke-OrdreDiscord 'lis ma to-do' 'jarvis'; Verifier ((Messages)[0].texte -eq '') 'to-do : jamais de blague'
Fixer 'humour_pourcent' 10; $script:HumourAlea = { 99 }
# aperçu HTML
$f = New-ApercuDiscord
$h = [Net.WebUtility]::HtmlDecode((Get-Content $f -Raw -Encoding UTF8))
Verifier ((Test-Path $f) -and $f -like '*apercu-discord.html' -and $h -match '<!doctype html>' -and ([regex]::Matches($h, "class='embed'")).Count -ge 12 -and $h -match 'Jarvis · statut' -and $h -match 'Données fictives') 'aperçu : memoire\apercu-discord.html écrit, un embed par modèle, données fictives'
Verifier ($h -notmatch '```' -and $h -notmatch [regex]::Escape($FAUX_JETON) -and $h -notmatch '<script') 'aperçu : aucun script, aucun secret'
Verifier ((ConvertTo-HtmlEmbed @{ titre = '<b>x</b>'; description = '<script>alert(1)</script> **gras**'; couleur = 255; champs = @(); pied = '' }) -notmatch '<script' -and (ConvertTo-HtmlEmbed @{ titre = 't'; description = '**gras**'; couleur = 255; champs = @(); pied = '' }) -match '<b>gras</b>') 'aperçu : le contenu est échappé (pas d''injection HTML), le **gras** est rendu'
$mj = Get-Content (Join-Path $Root 'jarvis.ps1') -Raw -Encoding UTF8
Verifier ($mj -match "'discord-apercu'" -and $mj -match 'New-ApercuDiscord') 'jarvis.ps1 discord-apercu : commande branchée'
Verifier ((Get-Content (Join-Path $Root 'lib\discord-embeds.ps1') -Raw -Encoding UTF8) -notmatch '```') 'le code des modèles ne produit aucun bloc de code'
Vider; Invoke-OrdreDiscord 'briefing' 'jarvis'
Verifier ((Messages)[0].embed.description -match "\n\n") 'briefing envoyé : une ligne vide entre les phrases'


Write-Host '5 ter) Humour discret (humour_pourcent) : jamais là où il ne faut pas'
$cat = @($script:PolitesseCat['humour'].courtois)
Verifier ($cat.Count -ge 8 -and @($script:PolitesseCat['humour'].sec).Count -eq 0) 'catalogue dans lib\politesse.ps1 : au moins 8 phrases variées (ton « sec » : aucune)'
Verifier ((Get-PolitessePrechauffe) -notcontains $cat[0]) 'les blagues ne sont jamais pré-synthétisées : la voix ne change pas'
Verifier ((Get-HumourPourcent) -eq 10) 'humour_pourcent = 10 par défaut'
Fixer 'humour_pourcent' 0
$script:HumourAlea = { 0 }; $script:DiscordSansHumour = $false; $script:DiscordConfirmeDansOrdre = $false; $script:DiscordPlafondAtteint = $false
Verifier ((Get-HumourDiscord 'merci' 'À votre service, monsieur.') -eq '') 'humour_pourcent = 0 : aucune blague, même avec le pire tirage'
Fixer 'humour_pourcent' 10
$script:HumourAlea = { 50 }; Verifier ((Get-HumourDiscord 'merci' 'À votre service, monsieur.') -eq '') 'tirage au-dessus du seuil : pas de blague (environ 10 % seulement)'
$script:HumourAlea = { 5 }; $h = Get-HumourDiscord 'merci' 'À votre service, monsieur.'
Verifier ($h -match '^\*.+\*$') 'tirage sous le seuil : une courte remarque en italique'
Fixer 'humour_pourcent' 100; $script:HumourAlea = { 0 }
$interdits = @(
    @('liste mes tâches', 'Une erreur est survenue, monsieur.', 'erreur'),
    @('liste mes tâches', "Mon plafond quotidien est atteint.", 'refus / plafond'),
    @('liste mes tâches', "Arrêt d'urgence demandé, monsieur.", 'arrêt d''urgence'),
    @('liste mes tâches', "Je ne trouve pas de salon pour : marche.", 'introuvable'),
    @('lis ma to-do', 'Vous avez 2 tâches.', 'tâches (liste)'),
    @('ajoute acheter du pain à ma to-do', 'Tâche ajoutée : acheter du pain', 'tâches (ajout)'),
    @('j''ai fini acheter du pain', 'Tâche cochée.', 'tâches (fin)'),
    @('rappelle-moi dans dix minutes', 'Rappel noté.', 'rappels'),
    @('où en est Thales', 'Thales : 150 euros.', 'finance (cours)'),
    @('dois-je acheter Thales ?', 'Je ne donne pas de conseil.', 'finance (conseil)'),
    @('stats du SaaS', 'Deux nouveaux abonnés.', 'finance (SaaS, revenus)'),
    @('briefing', 'Chiffre d''affaires : 120 euros.', 'finance (briefing)'))
foreach ($c in $interdits) { Verifier ((Get-HumourDiscord $c[0] $c[1]) -eq '') "aucune blague (100 % réglé) : $($c[2])" }
$script:DiscordSansHumour = $true; Verifier ((Get-HumourDiscord 'merci' 'ok') -eq '') 'aucune blague quand le traitement l''interdit (briefing, cours, SaaS)'; $script:DiscordSansHumour = $false
$script:DiscordConfirmeDansOrdre = $true; Verifier ((Get-HumourDiscord 'ouvre chrome' 'ok') -eq '') 'aucune blague après une confirmation d''action sensible'; $script:DiscordConfirmeDansOrdre = $false
Verifier ((Get-HumourDiscord 'merci' 'À votre service, monsieur.') -match '^\*') 'à 100 % et hors cas interdits : une blague'
# jamais deux fois la même d'affilée
$script:PolitesseFixe = $false; $dernier = ''; $rep = 0
for ($k = 0; $k -lt 60; $k++) { $x = Get-HumourDiscord 'merci' 'ok'; if ($x -eq $dernier) { $rep++ }; $dernier = $x }
Verifier ($rep -eq 0) 'jamais deux fois la même blague d''affilée (60 tirages)'
$script:PolitesseFixe = $true
# de bout en bout : blague seulement sur une réponse permise, ajoutée après la mise en forme
Vider; Invoke-OrdreDiscord 'statut' 'jarvis'; $m = @(Messages)
Verifier ($m[0].texte -match '^\*.+\*$' -and $m[0].embed.titre -match 'Statut') 'statut : embed + remarque en italique'
Vider; Invoke-OrdreDiscord 'où en est Thales ?' 'jarvis'; Verifier ((Messages)[0].texte -eq '') 'cours : embed seul, jamais de blague'
Vider; Invoke-OrdreDiscord 'lis ma to-do' 'jarvis'; Verifier ((Messages)[0].texte -eq '') 'liste des tâches (100 % réglé) : embed seul, jamais de blague'
Vider; Invoke-OrdreDiscord 'ajoute ranger le garage à ma to-do' 'jarvis'; Verifier ((Messages)[0].texte -notmatch '\*[^*]+\*$') 'ajout d''une tâche (100 % réglé) : aucune blague'
Vider; $script:SimRep = $null
Fixer 'humour_pourcent' 10; $script:HumourAlea = { 99 }
Vider; Invoke-OrdreDiscord 'statut' 'jarvis'; Verifier ((Messages)[0].texte -eq '') 'tirage haut : réponse sans blague'
$ajoute = $false
$j = (Get-Content (Join-Path $Root 'lib\discord.ps1') -Raw -Encoding UTF8)
Verifier ($j -notmatch "Get-HumourDiscord[^\r\n]*Parler" -and (Select-String -Path (Join-Path $Root 'lib\*.ps1') -Pattern 'Get-HumourDiscord' | Where-Object { $_.Path -notlike '*discord.ps1' }).Count -eq 0) 'l''humour n''est branché que sur les réponses écrites de Discord (ni voix, ni alertes)'
$alerte = Get-Content (Join-Path $Root 'lib\discord.ps1') -Raw -Encoding UTF8
$sa = $alerte.Substring($alerte.IndexOf('function Send-AlerteDiscord'), 1800)
Verifier ($sa -notmatch 'Humour') 'le ton des alertes ne change pas'
Fixer 'humour_pourcent' 10; $script:HumourAlea = { 99 }

Write-Host '6) Confirmations par Discord (oui / non / délai) — actions sensibles'
$script:SimRep = $null; $script:SimVus = @{}
function Invoke-BridgeSimule {
    foreach ($c in (Messages 'confirmation')) {
        if ($script:SimVus.ContainsKey($c.confirm_id)) { continue }; $script:SimVus[$c.confirm_id] = $true
        if ($script:SimRep -eq 'stop') { Set-Content $script:StopFlag '1' -Encoding ASCII }
        elseif ($script:SimRep) { Poser @{ type = 'reponse'; confirm_id = $c.confirm_id; reponse = $script:SimRep; via = 'texte' } }
    }
}
function Invoke-Pump { Invoke-BridgeSimule; if ($script:DiscordPumpActif) { Invoke-PumpDiscord } }
Fixer 'discord_delai_confirmation_secondes' 1
Vider; $script:SimRep = 'oui'; $script:Appels.veille = 0
Invoke-OrdreDiscord 'mets le PC en veille' 'jarvis' '21'
$cf = @(Messages 'confirmation')
Verifier ($cf.Count -eq 1 -and $cf[0].canal -eq 'jarvis' -and $cf[0].texte -match 'veille' -and $cf[0].delai -eq 1 -and $cf[0].reply_to -eq '21') 'la veille du PC demande une confirmation : question courte posée dans le salon'
Verifier ($script:Appels.veille -eq 1 -and $script:DerniereConfirmation -eq 'oui') '« oui » : l''action est exécutée'
Vider; $script:SimRep = 'non'; $script:Appels.veille = 0
Invoke-OrdreDiscord 'mets le PC en veille' 'jarvis'
Verifier ($script:Appels.veille -eq 0 -and $script:DerniereConfirmation -eq 'non' -and (Messages)[0].texte -match '\S') '« non » : rien n''est exécuté, annulation polie'
Vider; $script:SimRep = $null; $t0 = Get-Date
Invoke-OrdreDiscord 'mets le PC en veille' 'jarvis'
Verifier ($script:Appels.veille -eq 0 -and $script:DerniereConfirmation -eq 'delai' -and ((Get-Date) - $t0).TotalSeconds -lt 10) 'sans réponse dans le délai : annulation, rien n''est exécuté'
$fin = @(Messages 'confirmation_fin')
Verifier ($fin.Count -eq 1 -and $fin[0].issue -eq 'delai' -and (((Messages)[0].texte + (Messages)[0].embed.description) -match '\S')) 'le pont est prévenu de la fin du délai ; Liam reçoit une annulation polie'
Vider; $script:SimRep = 'non'
Invoke-OrdreDiscord 'ouvre chrome' 'jarvis'
Verifier (@(Messages 'confirmation').Count -eq 1 -and $script:DerniereConfirmation -eq 'non') 'même une action de niveau 1 qui agit sur le PC (ouvrir une application) demande une confirmation depuis Discord'
Vider; $script:SimRep = 'oui'; $script:Appels.claudecode = 0
Invoke-OrdreDiscord 'demande à Claude Code de ranger le dossier des projets' 'jarvis'
$cf = @(Messages 'confirmation')
Verifier ($cf.Count -ge 1 -and $script:Appels.claudecode -eq 1 -and $script:DernierEssai -eq $true) '« Demande à Claude Code de… » : confirmation, puis reste en essai à blanc (dry-run) par défaut'
Vider; $script:SimRep = 'oui'
$r = Invoke-OrdreDiscord 'ajoute appeler le dentiste à ma to-do' 'business'
Verifier (@(Messages 'confirmation').Count -eq 0) 'to-do, notes, lectures : aucune confirmation (pas de spam de questions)'
# refus par le code
$script:CanalDiscord = 'jarvis'; $script:DiscordTampon = New-Object System.Collections.Generic.List[string]; Vider
foreach ($t in 'powershell', 'executer_script', 'lire_fichier', 'bitwarden_saisir', 'envoyer_message', 'installer_programme', 'oublie_tout') {
    $a = [pscustomobject]@{ type = $t; code = 'Get-Date'; chemin = 'C:\Temp\x.txt'; recherche = 'x'; destinataire = 'a@b.fr'; id = 'x'; a = 'a@b.fr'; sujet = 's'; texte = 't'; resume = 'r' }
    $r = Invoke-UneAction $a "test $t"
    Verifier ($null -eq $r -and $script:DernierRefus -match 'niveau 3') "« $t » : refusé depuis Discord (jamais exécuté, même avec « oui »)"
}
Verifier (@(Messages 'confirmation').Count -eq 0) '…sans même poser de question'
foreach ($t in 'virement', 'achat', 'trade', 'action_financiere') { $r = Invoke-UneAction ([pscustomobject]@{ type = $t }) "test $t"; Verifier ($null -eq $r -and $script:DernierRefus -match 'niveau 3') "ordre financier « $t » : refusé (niveau 3)" }
$niv = Get-NiveauDiscord ([pscustomobject]@{ type = 'pc_veille' }) @{ niveau = 2; raison = 'x' }; Verifier ($niv.niveau -eq 2) 'niveau 2 reste 2'
$niv = Get-NiveauDiscord ([pscustomobject]@{ type = 'todo_lire' }) @{ niveau = 1; raison = 'x' }; Verifier ($niv.niveau -eq 1) 'action libre : niveau 1'
$niv = Get-NiveauDiscord ([pscustomobject]@{ type = 'fermer_app' }) @{ niveau = 1; raison = 'x' }; Verifier ($niv.niveau -eq 2) 'fermer une application : niveau 2 (confirmation) depuis Discord'
$niv = Get-NiveauDiscord ([pscustomobject]@{ type = 'une_competence_inconnue' }) @{ niveau = 1; raison = 'x' }; Verifier ($niv.niveau -eq 2) 'action de niveau 1 non listée : confirmation par prudence'
$niv = Get-NiveauDiscord ([pscustomobject]@{ type = 'virement' }) @{ niveau = 3; raison = 'x' }; Verifier ($niv.niveau -eq 3) 'niveau 3 reste 3'
$script:CanalDiscord = $null; $script:DiscordTampon = $null
# arrêt d'urgence pendant une confirmation
Vider; $script:SimRep = 'stop'; $script:Appels.veille = 0; $t0 = Get-Date
Invoke-OrdreDiscord 'mets le PC en veille' 'jarvis'
Verifier ($script:Appels.veille -eq 0 -and ((Get-Date) - $t0).TotalSeconds -lt 10) '« stop » pendant une confirmation : tout s''arrête, rien n''est exécuté'
Remove-Item $script:StopFlag -Force -ErrorAction SilentlyContinue; $script:SimRep = $null; Fixer 'discord_delai_confirmation_secondes' 60

Write-Host '7) Coût : règles et routeur local d''abord, plafond quotidien pour Claude'
$claudeAvant = @(Get-Process claude -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
Vider; Fixer 'discord_claude_max_par_jour' 2
Remove-Item "$TR\memoire\discord-claude.json" -Force -ErrorAction SilentlyContinue
Verifier ((Use-QuotaClaudeDiscord) -and (Use-QuotaClaudeDiscord) -and -not (Use-QuotaClaudeDiscord)) 'plafond de 2 appels par jour : le 3e est refusé'
Verifier ((Get-UsageClaudeDiscord) -eq 2) 'l''usage du jour est compté (2 sur 2)'
$script:CanalDiscord = 'jarvis'; $script:DiscordPlafondAtteint = $false
Verifier ($null -eq (Invoke-Claude 'système' 'utilisateur' 5) -and $script:DiscordPlafondAtteint) 'plafond atteint : Invoke-Claude ne lance rien (renvoie null)'
$script:CanalDiscord = $null
Vider; $n0 = (Journal).Length
Invoke-OrdreDiscord 'raconte-moi une histoire sur un dragon' 'jarvis'
Verifier ((((Messages)[0].texte + (Messages)[0].embed.description) -match '(?i)plafond') -and (Journal).Substring($n0) -match 'plafond quotidien atteint') 'question ouverte au plafond : Jarvis le dit poliment, sans appeler Claude'
Verifier (@(Get-Process claude -ErrorAction SilentlyContinue | Where-Object { $_.Id -notin $claudeAvant }).Count -eq 0) 'aucun nouveau processus Claude lancé'
Fixer 'discord_claude_max_par_jour' 20

Write-Host '8) Alertes sortantes : problème ou seuil seulement, limite par heure, doublons regroupés'
Vider; Fixer 'discord_alertes_max_par_heure' 3
$script:DiscordAlertesEnvoyees.Clear(); $script:DiscordAlertesAttente.Clear(); $script:DiscordAlertesVues = @{}
$r = @(1..5 | ForEach-Object { Send-AlerteDiscord "k$_" "Problème numéro $_ : processus suspect inconnu$('x' * $_)" })
Verifier (($r -join ',') -eq 'envoyee,envoyee,envoyee,regroupee,regroupee') 'limite de 3 par heure : les suivantes sont regroupées, pas envoyées'
Verifier (@(Messages).Count -eq 3 -and ((@(Messages) | Where-Object { $_.canal -ne 'systeme' })).Count -eq 0) 'les alertes partent dans « système » seulement'
Verifier ((Send-AlerteDiscord 'k1b' 'Problème numéro 1 : processus suspect inconnux') -eq 'doublon') 'la même alerte (à un chiffre près) n''est pas renvoyée : doublon'
Verifier ((Update-AlertesDiscord) -eq $false -and @(Messages).Count -eq 3) 'fenêtre pleine : le regroupement attend'
$script:DiscordAlertesEnvoyees.Clear(); $script:DiscordAlertesEnvoyees.Add((Get-Date).AddHours(-2)) | Out-Null
$r = Update-AlertesDiscord; $g = @(Messages)[-1]
Verifier ($r -and @(Messages).Count -eq 4 -and $g.embed.titre -match 'Alertes regroupées \(2\)' -and ([regex]::Matches($g.embed.description, '•')).Count -eq 2) 'dès que la limite le permet : UN message regroupe les alertes en attente'
Verifier ((Update-AlertesDiscord) -eq $false) 'rien de plus à envoyer'
Vider; $script:DiscordAlertesEnvoyees.Clear(); $script:DiscordAlertesVues = @{}
[void](Send-AlerteDiscord 'secret' "Fuite : $FAUX_JETON dans le journal"); $m = (Messages)[0]
Verifier ($m.texte -notmatch [regex]::Escape($FAUX_JETON)) 'un jeton dans le texte d''une alerte est masqué avant l''envoi'
Fixer 'discord_alertes_max_par_heure' 0; Verifier ((Send-AlerteDiscord 'z' 'zzz') -eq 'inactive') 'limite à 0 : aucune alerte Discord'
Fixer 'discord_alertes_max_par_heure' 6; Set-Salons $S_JARVIS $S_TODO '' ''; Verifier ((Send-AlerteDiscord 'y' 'yyy') -eq 'inactive') 'salon « système » introuvable : aucune alerte'
Set-Salons $S_JARVIS $S_TODO $S_ALERTES ''; $script:DiscordPumpActif = $false; Verifier ((Send-AlerteDiscord 'w' 'www') -eq 'inactive') 'pont arrêté : aucune alerte'
$script:DiscordPumpActif = $true
# branchement réel : Register-Alerte (menaces, seuils de marché) -> #alertes, une seule fois par alerte
Vider; $script:DiscordAlertesEnvoyees.Clear(); $script:DiscordAlertesVues = @{}
[void](Register-Alerte 'marche:thales:2026-01-01' 'Thales bouge de plus de 3 % aujourd''hui : +4,1 %' $false)
[void](Register-Alerte 'marche:thales:2026-01-01' 'Thales bouge de plus de 3 % aujourd''hui : +4,1 %' $false)
Verifier (@(Messages).Count -eq 1 -and (Messages)[0].embed.description -match 'Thales bouge') 'une alerte de seuil nouvelle part dans « système » ; la revoir ne la renvoie pas'

Write-Host '9) Briefing du matin dans #jarvis (à l''heure choisie, désactivé par défaut)'
Vider
Fixer 'discord_briefing_actif' $false; Fixer 'discord_briefing_heure' (Get-Date).AddMinutes(-1).ToString('HH:mm'); Remove-Item "$TR\memoire\discord-briefing.json" -Force -ErrorAction SilentlyContinue
Verifier ((Update-BriefingDiscord) -eq $false -and @(Messages).Count -eq 0) 'désactivé : rien n''est envoyé'
Fixer 'discord_briefing_actif' $true
Verifier ((Update-BriefingDiscord) -eq $true -and @(Messages).Count -eq 1 -and (Messages)[0].canal -eq 'jarvis' -and (Messages)[0].embed.description -match 'Trois nouveaux quiz') 'activé et l''heure passée : le briefing court (embed) est envoyé dans #jarvis'
Verifier ((Update-BriefingDiscord) -eq $false -and @(Messages).Count -eq 1) '…une seule fois par jour'
Remove-Item "$TR\memoire\discord-briefing.json" -Force; Fixer 'discord_briefing_heure' (Get-Date).AddHours(2).ToString('HH:mm')
Verifier ((Update-BriefingDiscord) -eq $false) 'avant l''heure choisie : rien'
if ((Get-Date).Hour -ge 6) { Fixer 'discord_briefing_heure' (Get-Date).AddHours(-6).ToString('HH:mm'); Verifier ((Update-BriefingDiscord) -eq $false) 'plus de 4 h après l''heure choisie : on ne l''envoie pas (ce ne serait plus un briefing du matin)' } else { Write-Host '  OK    (fenêtre de 4 h : contrôle sauté avant 6 h)' }
Fixer 'discord_briefing_actif' $false

Write-Host '10) Messages vocaux : prévus, désactivés'
Vider; Fixer 'discord_vocal' $false
$audio = "$TR\jarvis.mp3"; [IO.File]::WriteAllBytes($audio, [byte[]](73, 68, 51, 0, 0))
Verifier ((Send-VocalDiscord $audio) -eq $false -and @(Messages 'vocal').Count -eq 0 -and (Journal) -match 'discord_vocal est désactivé') 'discord_vocal = false : rien n''est envoyé'
Fixer 'discord_vocal' $true
Verifier ((Send-VocalDiscord $audio) -eq $true -and @(Messages 'vocal').Count -eq 1) 'discord_vocal = true : un fichier audio de Jarvis part vers le pont'
"x" | Set-Content "$TR\note.txt"; Verifier ((Send-VocalDiscord "$TR\note.txt") -eq $false -and (Send-VocalDiscord "$TR\absent.mp3") -eq $false -and (Send-VocalDiscord (Join-Path $Root '.env')) -eq $false) 'même activé : fichier non audio, absent ou secret (.env) refusé'
Fixer 'discord_vocal' $false
Verifier (-not (Select-String -Path (Join-Path $Root 'lib\*.ps1'), (Join-Path $Root 'jarvis.ps1') -Pattern 'Send-VocalDiscord' -SimpleMatch | Where-Object { $_.Path -notlike '*discord.ps1' })) 'rien dans Jarvis n''appelle encore cette fonction (désactivée par construction)'

Write-Host '11) « Jarvis stop » et arrêt avec Jarvis'
Vider; $script:PontCoupeUrgence = $false; $script:PontDesactive = $false; Fixer 'discord_actif' $true
Verifier ((Start-PontDiscord) -and $script:PontProc) 'pont de nouveau démarré'
$pid2 = $script:PontProc.Id; $script:DiscordStopCanal = 'jarvis'
Invoke-ArretUrgence
Start-Sleep -Milliseconds 400
$tous = @(Sortants)
Verifier (-not (Get-Process -Id $pid2 -ErrorAction SilentlyContinue) -and $null -eq $script:PontProc -and $script:PontCoupeUrgence) '« Jarvis stop » : le pont Discord est arrêté aussi'
Verifier ($tous.Count -ge 2 -and $tous[0].type -eq 'message' -and $tous[0].texte -match 'Arrêt d''urgence exécuté' -and $tous[-1].type -eq 'arret') 'Liam reçoit d''abord l''accusé d''arrêt d''urgence, puis le pont reçoit l''ordre de s''arrêter'
Update-PontDiscord; Verifier ($null -eq $script:PontProc -and @(Processus-FauxPont).Count -eq 0) 'après un arrêt d''urgence, le pont ne redémarre pas seul'
$plan = Get-PlanRapide 'réactive Discord'
Verifier ($plan -and $plan.actions[0].type -eq 'discord_reactiver') '« réactive Discord » est compris (règle)'
Verifier ((Get-PlanRapide 'ouvre discord') -and (Get-PlanRapide 'ouvre discord').actions[0].type -ne 'discord_reactiver') '« ouvre Discord » (l''application) reste inchangé'
Vider; $r = & $script:Actions['discord_reactiver'].run @{}
Verifier ($r.ok -and $script:PontProc -and -not $script:PontCoupeUrgence) '« réactive Discord » relance le pont'
Stop-PontDiscord
Verifier (@(Processus-FauxPont).Count -eq 0) 'plus aucun processus de pont'
$ar = Get-Content (Join-Path $Root 'arreter.ps1') -Raw -Encoding UTF8
Verifier ($ar -match 'pont-discord\\\\pont\\\.py' -and $ar -match 'discord-pont\.pid') 'arreter.ps1 arrête aussi le pont Discord (et efface son PID)'
$mj = Get-Content (Join-Path $Root 'jarvis.ps1') -Raw -Encoding UTF8
Verifier ($mj -match "lib\\discord\.ps1" -and $mj -match 'Start-PontDiscord' -and $mj -match 'finally \{ Save-HeureArret; Stop-PontDiscord' -and $mj -match 'Update-PontDiscord') 'jarvis.ps1 : charge le module, démarre le pont, le surveille et l''arrête à la fermeture'
Verifier ($mj -notmatch 'installer\.ps1') 'aucun démarrage automatique ajouté'
$ac = Get-Content (Join-Path $Root 'lib\discord.ps1') -Raw -Encoding UTF8
Verifier ($ac -match 'if \(\(Test-ModeTest\) -and -not \$env:JARVIS_PONT_FAUX\) \{ return \$false \}') 'en mode test, jamais de vrai pont (seulement le faux pont désigné par JARVIS_PONT_FAUX)'

Write-Host '11 bis) « Test d''alerte » : UN message dans le salon système, qui mentionne @Liam ; 3 par heure'
$script:DiscordPumpActif = $true; Vider; Remove-Item "$TR\memoire\discord-test-alerte.json" -Force -ErrorAction SilentlyContinue
Set-Salons $S_JARVIS $S_TODO $S_ALERTES ''
foreach ($o in 'test d''alerte', 'Jarvis, test d''alerte', 'fais un test d''alerte', 'lance un test alerte', 'teste l''alerte') { $pl = Get-PlanRapide $o; Verifier ($pl -and $pl.actions[0].type -eq 'test_alerte') "« $o » est compris (règle, voix et clavier)" }
Verifier ($script:Actions['test_alerte'].niveau -eq 1 -and 'test_alerte' -in $script:DiscordLibres) 'action test_alerte : niveau 1, permise depuis Discord'
$E_W = [string][char]0x26A0 + [string][char]0xFE0F
$r = Invoke-TestAlerteDiscord; $m = @(Messages)
Verifier ($r.ok -and $m.Count -eq 1 -and $m[0].canal -eq 'systeme' -and $m[0].mention -eq $FAUX_UID -and $m[0].texte -eq "$E_W Test d'alerte, monsieur." -and -not $m[0].embed) 'UN seul message, dans le salon « système », avec le texte exact et la mention de DISCORD_USER_ID (texte simple : la mention notifie)'
Verifier ($m[0].texte -notmatch [regex]::Escape($FAUX_JETON)) 'aucun secret dans le message'
Update-Discord; [void](Update-AlertesDiscord); Pomper
Verifier (@(Messages).Count -eq 1) 'pas de relance : rien d''autre n''est envoyé ensuite'
[void](Invoke-TestAlerteDiscord); [void](Invoke-TestAlerteDiscord)
Verifier (@(Messages).Count -eq 3) '2e et 3e tests de l''heure : envoyés'
$r4 = Invoke-TestAlerteDiscord
Verifier (-not $r4.ok -and $r4.texte -match '3 tests d''alerte' -and @(Messages).Count -eq 3) '4e test dans l''heure : refusé poliment, rien n''est envoyé (limite de 3 par heure)'
$vieux = (Get-Date).AddMinutes(-70).ToString('o'); $rec = (Get-Date).AddMinutes(-10).ToString('o')
Save-JsonMemoire 'discord-test-alerte.json' ([ordered]@{ envoyes = @($vieux, $vieux, $rec) })
$r5 = Invoke-TestAlerteDiscord
Verifier ($r5.ok -and @(Messages).Count -eq 4) 'les tests de plus d''une heure ne comptent plus'
Remove-Item "$TR\memoire\discord-test-alerte.json" -Force; Vider
$script:DiscordPumpActif = $false; $r = Invoke-TestAlerteDiscord
Verifier (-not $r.ok -and $r.texte -match "n'est pas actif" -and @(Messages).Count -eq 0) 'pont arrêté : refus poli, rien d''envoyé, rien de compté'
$script:DiscordPumpActif = $true
$u0 = $env:DISCORD_USER_ID; $env:DISCORD_USER_ID = ''; $r = Invoke-TestAlerteDiscord; $env:DISCORD_USER_ID = $u0
Verifier (-not $r.ok -and $r.texte -match 'DISCORD_USER_ID' -and @(Messages).Count -eq 0) 'identifiant Discord absent : refus poli (sans mentionner personne)'
Set-Salons $S_JARVIS $S_TODO '' ''; $r = Invoke-TestAlerteDiscord; $m = @(Messages)
Verifier ($r.ok -and $m.Count -eq 1 -and $m[0].canal -eq 'jarvis') 'salon système introuvable : repli sur « jarvis »'
Remove-Item "$TR\memoire\discord-test-alerte.json" -Force; Vider; Set-Salons $S_JARVIS $S_TODO $S_ALERTES ''
# depuis Discord (texte) : le test part dans « système », la réponse reste dans le salon d'où vient l'ordre
Invoke-OrdreDiscord 'test d''alerte' 'jarvis' '77'
$m = @(Messages)
Verifier ($m.Count -eq 2 -and @($m | Where-Object { $_.mention -eq $FAUX_UID -and $_.canal -eq 'systeme' }).Count -eq 1 -and @($m | Where-Object { $_.canal -eq 'jarvis' -and $_.reply_to -eq '77' }).Count -eq 1) 'depuis Discord : UN test dans « système » + une confirmation dans le salon de la demande'
Verifier ((Messages 'confirmation').Count -eq 0) '…sans demander de confirmation'
Remove-Item "$TR\memoire\discord-test-alerte.json" -Force; Vider
# voix / clavier : même action, réponse parlée
$script:DiscordPumpActif = $true; $j0 = (Journal).Length
Invoke-Ordre 'test d''alerte'
$m = @(Messages); $j = (Journal).Substring($j0)
Verifier ($m.Count -eq 1 -and $m[0].canal -eq 'systeme' -and $m[0].mention -eq $FAUX_UID -and $j -match "Test d'alerte envoyé") 'par la voix ou le clavier : le même message est envoyé, Jarvis répond « Test d''alerte envoyé »'
Remove-Item "$TR\memoire\discord-test-alerte.json" -Force; Vider
$script:DiscordPumpActif = $true

Write-Host '12) Aucun secret dans le code, les journaux ni les rapports'
$fichiers = @(Get-ChildItem $Root -Recurse -File -ErrorAction SilentlyContinue | Where-Object { $_.FullName -notmatch '\\(\.git|memoire|quarantaine|sounds|models|__pycache__|node_modules)\\' -and $_.Name -ne '.env' -and $_.Extension -in '.ps1', '.py', '.json', '.md', '.html', '.js', '.txt', '.example', '.css' })
Verifier ($fichiers.Count -gt 20) "fichiers du projet contrôlés : $($fichiers.Count) (hors .env, mémoire, sons)"
if ($jetonReel.Length -ge 20 -and $jetonReel -notmatch '^xxx') {
    $trouve = @($fichiers | Where-Object { Select-String -Path $_.FullName -Pattern $jetonReel -SimpleMatch -Quiet })
    Verifier ($trouve.Count -eq 0) 'le vrai DISCORD_BOT_TOKEN n''apparaît dans aucun fichier du projet (code, config, README, tests, logs)'
    $jr = @(Get-ChildItem (Join-Path $Root 'logs') -File -ErrorAction SilentlyContinue | Where-Object { Select-String -Path $_.FullName -Pattern $jetonReel -SimpleMatch -Quiet })
    Verifier ($jr.Count -eq 0) 'le vrai jeton n''est dans aucun journal existant'
    Verifier (-not ((Journal) -match [regex]::Escape($jetonReel))) 'ni dans le journal de ce test'
} else { Verifier $true '(pas de jeton Discord renseigné dans .env : contrôle du vrai jeton sans objet)' }
Verifier (-not ((Journal) -match [regex]::Escape($FAUX_JETON))) 'le faux jeton du test n''apparaît dans aucun journal du test'
Verifier ((Hide-Secrets "erreur $FAUX_JETON fin") -notmatch [regex]::Escape($FAUX_JETON)) 'Hide-Secrets masque la forme d''un jeton Discord même sans l''avoir chargé'
Verifier ([bool](Select-String -Path (Join-Path $Root '.gitignore') -Pattern '^\.env$' -Quiet)) '.env reste dans .gitignore'
$ex = Get-Content (Join-Path $Root '.env.example') -Raw -Encoding UTF8
Verifier ($ex -match 'DISCORD_BOT_TOKEN=xxx' -and $ex -match 'DISCORD_USER_ID=xxx') '.env.example : les deux variables Discord, avec des valeurs factices'

Write-Host '13) Partie Python (faux client Discord)'
$sortie = & python -I (Join-Path $PSScriptRoot 'discord-pont.py') 2>&1 | Out-String; $code = $LASTEXITCODE
$nbPy = ([regex]::Matches($sortie, '(?m)^\s+OK ')).Count
foreach ($l in ($sortie -split "`n" | Where-Object { $_ -match 'ECHEC' })) { Write-Host $l -ForegroundColor Red }
Verifier ($code -eq 0 -and $nbPy -ge 50) "tests\discord-pont.py : $nbPy vérifications (utilisateur, salons, confirmations, jeton, vocal, arrêt avec Jarvis) — tout vert"

Write-Host '14) Conversation directe du pont (API en flux, repli claude -p allégé, règles locales, notifier) — faux serveur local'
$sortie = & python -I (Join-Path $PSScriptRoot 'conversation-pont.py') 2>&1 | Out-String; $code = $LASTEXITCODE
$nbConv = ([regex]::Matches($sortie, '(?m)^\s+OK ')).Count
foreach ($l in ($sortie -split "`n" | Where-Object { $_ -match 'ECHEC' })) { Write-Host $l -ForegroundColor Red }
Verifier ($code -eq 0 -and $nbConv -ge 35) "tests\conversation-pont.py : $nbConv vérifications — tout vert"
$nt = Get-Content (Join-Path $Root 'pont-discord\notifier.py') -Raw -Encoding UTF8; $js = Get-Content (Join-Path $Root 'jarvis.ps1') -Raw -Encoding UTF8
Verifier ($js -match "'notifier'" -and $nt -match 'allowed_mentions' -and $nt -notmatch 'print\(\s*jeton') 'jarvis.ps1 notifier : poste dans le salon système via le bot, sans mention, jeton jamais affiché'

Remove-Item Env:JARVIS_PONT_FAUX, Env:DISCORD_BOT_TOKEN, Env:DISCORD_USER_ID -ErrorAction SilentlyContinue
Remove-Item $script:StopFlag -Force -ErrorAction SilentlyContinue
Remove-Item $TR -Recurse -Force -ErrorAction SilentlyContinue
if ($echecs) { Write-Host "`nÉCHEC : $echecs vérification(s) en échec." -ForegroundColor Red; exit 1 }
Write-Host "`nRÉUSSI"; exit 0
