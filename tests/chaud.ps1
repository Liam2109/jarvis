# Test SILENCIEUX du processus claude chaud de Invoke-Claude (lib\cerveau.ps1) avec un FAUX claude local (python) : aucun appel réseau, aucun vrai claude, aucune voix.
# Vérifie : démarrage une seule fois, prompt système fixe + contexte dans le message (accents intacts), relance toutes les N demandes, repli sur l'appel simple (processus mort, délai dépassé),
# arrêt d'urgence (processus tué puis relancé proprement), réglage claude_chaud = false, aucune clé API transmise, nettoyage.
$ErrorActionPreference = 'Stop'
$env:JARVIS_TEST = '1'
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $Root 'lib\journal.ps1')
$TR = Join-Path $env:TEMP ('jarvis-test-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
New-Item -ItemType Directory $TR, "$TR\memoire", "$TR\logs", "$TR\faux" | Out-Null
$script:JarvisRoot = $TR
$Config = Get-Content (Get-ConfigPath) -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($l in 'voix', 'business', 'permissions', 'actions', 'coffre', 'entrees', 'ecrans', 'tableau', 'visage', 'sons', 'raccourcis', 'cerveau', 'cerveau-local', 'veille', 'memoire', 'rapide', 'discretion', 'modejeu', 'boucle') { . (Join-Path $Root "lib\$l.ps1") }
$script:JarvisRoot = $TR
$echecs = 0
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }
function JournalTexte { (Get-ChildItem "$TR\logs" -Filter 'journal-*.md' -ErrorAction SilentlyContinue | ForEach-Object { Get-Content $_.FullName -Raw -Encoding UTF8 }) -join "`n" }

# --- faux claude : mode flux (--input-format) = une réponse JSON par ligne reçue ; mode simple = lit l'entrée et répond « simple ok » ---
@'
import sys, json, os, time
if '--help' in sys.argv:
    print('  --safe-mode'); sys.exit(0)
open(os.environ['FAUX_ARGS'], 'a', encoding='utf-8').write(' '.join(sys.argv[1:]) + ' | KEY=' + str('ANTHROPIC_API_KEY' in os.environ) + '\n')
if '--input-format' not in sys.argv:
    sys.stdin.read(); print('simple ok'); sys.exit(0)
for l in sys.stdin.buffer:      # octets UTF-8 comme le vrai claude (stdin texte = page de code Windows, dépend de l'environnement)
    t = json.loads(l.decode('utf-8'))['message']['content']
    open(os.environ['FAUX_MSGS'], 'a', encoding='utf-8').write(t.replace('\n', '¶') + '\n')
    if 'MORT' in t: sys.exit(3)
    if 'LENT' in t: time.sleep(30)
    print(json.dumps({'type': 'stream_event', 'event': {'type': 'content_block_delta', 'delta': {'type': 'text_delta', 'text': 'pid%d ' % os.getpid()}}}), flush=True)
    print(json.dumps({'type': 'result', 'result': 'pid%d ok' % os.getpid(), 'is_error': False}), flush=True)
'@ | Set-Content "$TR\faux\fake.py" -Encoding UTF8
$py = (Get-Command python).Source
"@`"$py`" `"%~dp0fake.py`" %*" | Set-Content "$TR\faux\claude.cmd" -Encoding ASCII
$env:FAUX_ARGS = "$TR\faux\args.txt"; $env:FAUX_MSGS = "$TR\faux\msgs.txt"; $env:ANTHROPIC_API_KEY = 'sk-ant-FAUSSE-cle-de-test-0123456789abcdef'
$script:ClaudeCmd = "$TR\faux\claude.cmd"; $script:DossierNeutre = "$TR\neutre"
function Pid-De([string]$t) { if ("$t" -match 'pid(\d+)') { [int]$Matches[1] } else { 0 } }
$sys = Get-PromptSysteme -SansContexte; $ctx = Get-ContexteCerveau
$mots = 'Réponds en JSON : où est l''été ? ÉÀÇ'

Write-Host '1) Prompt système fixe, contexte à part'
Verifier ($sys -notmatch 'CONTEXTE :' -and (Get-PromptSysteme) -match 'CONTEXTE :' -and $ctx -match '^CONTEXTE : ') 'le prompt fixe n''a pas la date ni la mémoire ; le prompt complet les a toujours'
Verifier ((Get-PromptSysteme -SansContexte) -eq $sys) 'prompt fixe identique d''un appel à l''autre'

Write-Host '2) Démarrage une seule fois, puis réponses rapides'
$r1 = Invoke-Claude $sys $mots 20 $null $ctx; $p1 = Pid-De $r1
Verifier ($p1 -gt 0 -and $r1 -match 'ok$') "1re demande : réponse du processus chaud ($r1)"
$r2 = Invoke-Claude $sys 'deuxième' 20 $null $ctx; Verifier ((Pid-De $r2) -eq $p1) 'la 2e demande utilise LE MÊME processus (pas de nouveau claude)'
$args1 = Get-Content $env:FAUX_ARGS -Raw -Encoding UTF8
Verifier (([regex]::Matches($args1, 'input-format stream-json')).Count -eq 1 -and $args1 -match 'KEY=False' -and $args1 -match '--safe-mode' -and $args1 -match '--tools') 'lancé une seule fois, en flux JSON, mêmes options minimales, sans clé API'
$m = Get-Content $env:FAUX_MSGS -Raw -Encoding UTF8
Verifier ($m -match 'CONTEXTE : .*Réponds en JSON : où est l''été \? ÉÀÇ' -and $m -notmatch 'Ã') 'la date / mémoire passent dans le message, accents intacts (UTF-8)'
Verifier ((JournalTexte) -match 'claude chaud \(démarré à froid, tour 1/' -and (JournalTexte) -match 'claude chaud \(déjà chaud, tour 2/') 'journal : démarré à froid puis déjà chaud, avec les temps'

Write-Host '3) Relance toutes les N demandes'
$script:ChaudToursMax = 3
$r3 = Invoke-Claude $sys 'trois' 20 $null $ctx; $r4 = Invoke-Claude $sys 'quatre' 20 $null $ctx
Verifier ((Pid-De $r3) -eq $p1 -and (Pid-De $r4) -ne $p1 -and (Pid-De $r4) -gt 0) 'après N demandes : processus renouvelé'
Stop-ClaudeChaud; $script:ChaudToursMax = 10

Write-Host '4) Repli : processus mort, délai dépassé'
$r = Invoke-Claude $sys 'MORT' 20 $null $ctx
Verifier ($r -match 'simple ok' -and (JournalTexte) -match 'claude chaud indisponible .*repli sur l''appel simple') 'processus mort : repli automatique sur l''appel simple'
$r = Invoke-Claude $sys 'normal' 20 $null $ctx; Verifier ((Pid-De $r) -gt 0) 'la demande suivante relance un processus chaud'
$t = Get-Date; $r = Invoke-Claude $sys 'LENT' 2 $null $ctx; $d = ((Get-Date) - $t).TotalSeconds
Verifier ($r -match 'simple ok' -and $d -lt 12 -and $null -eq $script:Chaud) "délai dépassé : processus tué, repli sur l'appel simple ($([math]::Round($d, 1)) s)"

Write-Host '5) Arrêt d''urgence'
$r = Invoke-Claude $sys 'avant' 20 $null $ctx; $vieux = $script:Chaud.p; $pAvant = Pid-De $r
$r = Invoke-Claude $sys 'LENT' 20 { New-Item -ItemType File $script:StopFlag -Force | Out-Null } $ctx
Verifier ($null -eq $r -and $null -eq $script:Chaud -and $vieux.WaitForExit(5000)) 'arrêt d''urgence : aucune réponse, processus tué'
Remove-Item $script:StopFlag -Force -ErrorAction SilentlyContinue
$r = Invoke-Claude $sys 'après' 20 $null $ctx; Verifier ((Pid-De $r) -gt 0 -and (Pid-De $r) -ne $pAvant) 'après l''arrêt : nouveau processus propre'
$vieux2 = $script:Chaud.p; Invoke-ArretUrgence; Verifier ($null -eq $script:Chaud -and $vieux2.WaitForExit(5000)) 'Invoke-ArretUrgence tue aussi le processus chaud au repos'
Remove-Item $script:StopFlag -Force -ErrorAction SilentlyContinue

Write-Host '6) Réglages et nettoyage'
$Config | Add-Member -NotePropertyName claude_chaud -NotePropertyValue $false -Force
$r = Invoke-Claude $sys 'sans chaud' 20 $null $ctx; Verifier ($r -match 'simple ok' -and $null -eq $script:Chaud) 'claude_chaud = false : appel simple, aucun processus chaud'
$Config.claude_chaud = $true
$r = Invoke-Claude $sys 'x' 20 $null $ctx; $f = $script:Chaud.sys; $pp = $script:Chaud.p
Verifier ((Test-Path $f) -and $f -match 'jarvis-sys-\d+-\d+\.txt$') 'fichier du prompt fixe nommé comme celui de Discord (arreter.ps1 sait le nettoyer)'
Stop-ClaudeChaud; Verifier ($pp.WaitForExit(5000) -and -not (Test-Path $f)) 'Stop-ClaudeChaud : processus tué, fichier supprimé'
Verifier (-not (Test-Path $script:StopFlag)) 'aucun drapeau d''arrêt laissé'

Write-Host '7) Préchauffage au lancement de Jarvis'
Stop-ClaudeChaud; Start-PrechauffageClaude; $pre = $script:Chaud
Verifier ($pre -and -not $pre.p.HasExited -and (JournalTexte) -match 'claude chaud préchauffé au démarrage') 'préchauffage : processus démarré avant toute demande, noté au journal'
$r = Invoke-Claude $sys 'première' 20 $null $ctx
Verifier ([object]::ReferenceEquals($script:Chaud, $pre) -and (Pid-De $r) -gt 0 -and (JournalTexte) -match 'claude chaud \(déjà chaud, tour 1/') 'la 1re demande utilise le processus préchauffé (« déjà chaud, tour 1 »)'
Stop-ClaudeChaud; $Config.claude_chaud = $false; Start-PrechauffageClaude
Verifier ($null -eq $script:Chaud) 'claude_chaud = false : aucun préchauffage'
$Config.claude_chaud = $true
$orig = (Get-Command Start-ClaudeChaud).ScriptBlock; function Start-ClaudeChaud { throw 'boum' }
Start-PrechauffageClaude; Set-Item function:Start-ClaudeChaud $orig
Verifier ($null -eq $script:Chaud -and (JournalTexte) -match 'préchauffage du claude chaud impossible \(boum\) : appel simple') 'démarrage en échec : journalisé, aucune exception, rien ne reste'
$r = Invoke-Claude $sys 'après échec' 20 $null $ctx; Verifier ((Pid-De $r) -gt 0 -or $r -match 'simple ok') 'après un préchauffage raté, les demandes fonctionnent comme avant'
Stop-ClaudeChaud

Remove-Item Env:ANTHROPIC_API_KEY, Env:FAUX_ARGS, Env:FAUX_MSGS -ErrorAction SilentlyContinue
Remove-Item $TR -Recurse -Force -ErrorAction SilentlyContinue
if ($echecs) { Write-Host "`nÉCHEC : $echecs vérification(s) en échec." -ForegroundColor Red; exit 1 }
Write-Host "`nRÉUSSI"; exit 0
