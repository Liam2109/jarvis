# Test : mode discret, alertes dites UNE fois, fichiers ignorés, micro. N'ouvre ni micro, ni fenêtre, ni son ; n'écrit rien dans memoire\ (fichiers d'état redirigés vers %TEMP%).
$ErrorActionPreference = 'Stop'
$env:JARVIS_TEST = '1'      # TEST SILENCIEUX : aucun son, aucune fenêtre, aucun micro, aucune touche, aucune action réelle (voir lib\journal.ps1)
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $Root 'lib\journal.ps1'); Import-JarvisEnv
$Config = Get-Content (Get-ConfigPath) -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($l in 'voix', 'business', 'permissions', 'actions', 'coffre', 'entrees', 'ecrans', 'tableau', 'visage', 'sons', 'raccourcis', 'cerveau', 'cerveau-local', 'veille', 'memoire', 'rapide', 'discretion', 'modejeu', 'boucle') { . (Join-Path $Root "lib\$l.ps1") }
Remove-Item $script:StopFlag, $script:ParleFlag -ErrorAction SilentlyContinue
$echecs = 0
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }

$tmp = Join-Path $env:TEMP "jarvis-test-discretion-$([guid]::NewGuid().ToString('N'))"; New-Item -ItemType Directory $tmp | Out-Null
function Get-FichierAlertes { Join-Path $tmp 'alertes.json' }
function Get-FichierBriefingVocal { Join-Path $tmp 'briefing-vocal.txt' }
$script:AlertesCache = $null
# Aucun son : on remplace la lecture et la synthèse
$script:Lectures = 0
function Lire-Mp3([string]$f) { $script:Lectures++ }

Write-Host '1) Mode discret : seules les réponses, le briefing du matin et les alertes graves ont une voix'
$script:ModeJeu = $false
foreach ($c in 'reponse', 'briefing', 'alerte') { $script:ContexteVoix = $c; Verifier ((Test-VoixPermise).ok) "contexte « $c » : parole permise" }
foreach ($c in 'spontane', 'rappel') { $script:ContexteVoix = $c; Verifier (-not (Test-VoixPermise).ok) "contexte « $c » : silence (écrit au tableau)" }
$script:ContexteVoix = 'spontane'
$avant = $script:Lectures
Parler 'Phrase spontanée de test'
Verifier ($script:Lectures -eq $avant) 'Parler en contexte spontané : rien n''est lu ni synthétisé'
$j = Get-Content (Get-ChildItem (Get-DossierLogs) -Filter 'journal-*.md' | Sort-Object Name | Select-Object -Last 1).FullName -Raw -Encoding UTF8
Verifier ($j -match 'Parole non prononcée \(mode discret\)') 'la phrase est gardée au journal : « Parole non prononcée (mode discret) »'
$Config | Add-Member -NotePropertyName voix_autorisees -NotePropertyValue @('reponse', 'briefing', 'alerte', 'rappel') -Force
$script:ContexteVoix = 'rappel'; Verifier ((Test-VoixPermise).ok) 'on peut autoriser les rappels à voix haute dans config.json (voix_autorisees)'
$Config.voix_autorisees = @('reponse', 'briefing', 'alerte'); $script:ContexteVoix = 'spontane'
try { Invoke-AvecContexteVoix 'reponse' { throw 'boum' } } catch {}
Verifier ($script:ContexteVoix -eq 'spontane') 'le contexte est restauré même après une erreur'
function Invoke-OrdreCorps([string]$ordre) { $script:CtxPendant = $script:ContexteVoix }
Invoke-Ordre 'test'
Verifier ($script:CtxPendant -eq 'reponse' -and $script:ContexteVoix -eq 'spontane') 'pendant un ordre de Liam le contexte est « reponse » ; après, il redevient discret'

Write-Host '2) Briefing automatique : dit une fois par jour, le matin ; sinon texte seul'
$matin = [datetime]'2026-10-14 08:30'; $apresmidi = [datetime]'2026-10-14 15:00'
Verifier (Test-BriefingVocalAuto $matin) 'le matin, jamais dit aujourd''hui : dit'
Set-BriefingVocalFait $matin
Verifier (-not (Test-BriefingVocalAuto $matin.AddMinutes(30))) 'le même jour : plus dit (2e démarrage de la journée)'
Verifier (Test-BriefingVocalAuto $matin.AddDays(1)) 'le lendemain matin : dit de nouveau'
Verifier (-not (Test-BriefingVocalAuto $apresmidi.AddDays(1))) 'l''après-midi : jamais dit automatiquement'
function Invoke-BriefingCorps { $script:CtxBriefing = $script:ContexteVoix }
function Test-BriefingVocalAuto([datetime]$now = (Get-Date)) { $script:StubAuto }
function Set-BriefingVocalFait([datetime]$now = (Get-Date)) { $script:AFait = $true }
$script:StubAuto = $true; $script:AFait = $false; Invoke-Briefing -Auto
Verifier ($script:CtxBriefing -eq 'briefing' -and $script:AFait) 'briefing automatique du matin : contexte « briefing » (voix permise), noté comme fait'
$script:StubAuto = $false; $script:AFait = $false; Invoke-Briefing -Auto
Verifier ($script:CtxBriefing -eq 'spontane' -and -not $script:AFait) 'briefing automatique hors matin : contexte discret (texte au tableau seulement)'
Invoke-Briefing
Verifier ($script:CtxBriefing -eq 'reponse') 'briefing DEMANDÉ par Liam : dit (c''est une réponse)'

Write-Host '3) Fichiers et processus que Jarvis ne signale jamais'
$dl = Join-Path $env:USERPROFILE 'Downloads\evil.exe'
Verifier (Test-CheminIgnore (Join-Path $Root 'memoire\x.exe')) 'dossier memoire de Jarvis ignoré'
Verifier (Test-CheminIgnore (Join-Path $Root 'quarantaine\x.exe')) 'dossier de Jarvis (quarantaine) ignoré'
Verifier (Test-CheminIgnore 'C:\Users\Liam\Jarvis-sauvegarde-corrompue\lib\a.exe') 'sauvegardes ignorées'
Verifier (Test-CheminIgnore (Join-Path $env:TEMP 'jarvis-123.mp3')) 'fichiers temporaires de Jarvis ignorés'
Verifier (Test-CheminIgnore (Join-Path $env:TEMP 'jtest\a.exe')) 'dossier de tests temporaire ignoré'
Verifier (Test-CheminIgnore 'D:\data\config.bak') 'fichier .bak ignoré'
Verifier (-not (Test-CheminIgnore $dl)) 'un exécutable inconnu dans Téléchargements n''est PAS ignoré'
Verifier (-not (Test-CheminIgnore (Join-Path $env:APPDATA 'Roaming\evil.exe'))) 'un exécutable inconnu dans AppData n''est PAS ignoré'
Verifier (-not (Test-CheminIgnore (Join-Path $env:TEMP 'autre\evil.exe'))) 'un exécutable inconnu dans Temp (hors Jarvis) n''est PAS ignoré'

Write-Host '4) Chaque alerte n''est dite qu''UNE fois (24 h minimum), puis seulement dans le panneau'
$t0 = [datetime]'2026-10-14 10:00'
$r1 = Register-Alerte 'C:\x\a.exe' 'a.exe : test' $true $t0
Verifier ($r1.nouvelle -and $r1.peut_dire) '1re détection : nouvelle, peut être dite'
Set-AlerteDite 'C:\x\a.exe' $t0
$r2 = Register-Alerte 'C:\x\a.exe' 'a.exe : test' $true $t0.AddHours(1)
Verifier (-not $r2.nouvelle -and -not $r2.peut_dire) '1 h plus tard : déjà dite, plus de voix'
$r3 = Register-Alerte 'C:\x\a.exe' 'a.exe : test' $true $t0.AddHours(23.9)
Verifier (-not $r3.peut_dire) '23 h 54 plus tard : toujours pas'
$r4 = Register-Alerte 'C:\x\a.exe' 'a.exe : test' $true $t0.AddHours(24.1)
Verifier ($r4.peut_dire) 'après 24 h : peut être redite'
$script:AlertesCache = $null
$r5 = Register-Alerte 'C:\x\a.exe' 'a.exe : test' $true $t0.AddHours(25)
Verifier ($r5.vues -ge 4 -and (Test-Path (Get-FichierAlertes))) 'les alertes vues sont mémorisées sur disque (survivent à un redémarrage)'
$pan = @(Get-AlertesPanneau 6)
Verifier ($pan.Count -ge 1 -and $pan[0].titre -match 'a\.exe' -and $pan[0].grave) 'le panneau contient l''alerte, marquée grave'
Verifier (-not ((Get-Content (Get-FichierAlertes) -Raw) -match '[\w.]+@[\w.]+')) 'le fichier d''alertes ne contient aucune adresse e-mail'
$script:ModeJeu = $false
Verifier ((Test-AlerteVocale $true)) 'alerte grave : voix permise'
Verifier (-not (Test-AlerteVocale $false)) 'alerte non grave : jamais à voix haute (panneau seulement)'
$Config.alertes.voix_graves_seulement = $false; Verifier ((Test-AlerteVocale $false)) 'option voix_graves_seulement=false : les autres peuvent être dites (une fois)'; $Config.alertes.voix_graves_seulement = $true
$script:ModeJeu = $true; Verifier (-not (Test-AlerteVocale $true)) 'mode jeu : même une alerte grave n''est pas dite'; $script:ModeJeu = $false

Write-Host '5) Le scan de menaces : une seule alerte vocale, ni Jarvis, ni sauvegardes, ni temporaires'
$script:AlertesCache = $null; Remove-Item (Get-FichierAlertes) -ErrorAction SilentlyContinue
function Find-ProcessusSuspects {
    @([pscustomobject]@{ nom = 'svchost.exe'; pid = 4001; chemin = 'C:\Users\Liam\AppData\Local\Faux\svchost.exe'; raison = 'imite un processus Windows hors de System32'; signature = 'NON SIGNÉ' },
      [pscustomobject]@{ nom = 'outil.exe'; pid = 4002; chemin = (Join-Path $env:USERPROFILE 'Downloads\outil.exe'); raison = 'exécutable non signé dans un dossier à risque'; signature = 'NON SIGNÉ' },
      [pscustomobject]@{ nom = 'python.exe'; pid = 4003; chemin = (Join-Path $Root 'memoire\interne.exe'); raison = 'exécutable non signé dans un dossier à risque'; signature = 'NON SIGNÉ' },
      [pscustomobject]@{ nom = 'copie.exe'; pid = 4004; chemin = 'C:\Users\Liam\Jarvis-sauvegarde-corrompue\copie.exe'; raison = 'exécutable non signé dans un dossier à risque'; signature = 'NON SIGNÉ' },
      [pscustomobject]@{ nom = 'tmp.exe'; pid = 4005; chemin = (Join-Path $env:TEMP 'jarvis-neutre\tmp.exe'); raison = 'exécutable non signé dans un dossier à risque'; signature = 'NON SIGNÉ' })
}
$script:Entrees.Clear(); $script:ModeJeu = $false
Invoke-ScanMenaces
Verifier ($script:Entrees.Count -eq 1 -and $script:Entrees.Peek().menace.nom -eq 'svchost.exe') "1re analyse : UNE seule alerte à dire (la grave) sur 5 détections ($($script:Entrees.Count))"
$pan = @(Get-AlertesPanneau 10)
Verifier ($pan.Count -eq 2 -and -not ($pan | Where-Object { $_.titre -match 'interne|copie|tmp\.exe' })) 'les deux seules alertes retenues sont dans le panneau ; Jarvis, sauvegardes et temporaires sont écartés'
Verifier ((@($pan | Where-Object { $_.titre -match 'outil' -and -not $_.grave })).Count -eq 1) 'l''alerte non grave est dans le panneau, sans voix'
$e = $script:Entrees.Dequeue()
$script:CtxAlerte = $null
function Invoke-MenaceCorps($e) { $script:CtxAlerte = $script:ContexteVoix }
Invoke-Menace $e
Verifier ($script:CtxAlerte -eq 'alerte') 'dite avec le contexte « alerte »'
Invoke-ScanMenaces
Verifier ($script:Entrees.Count -eq 0) '2e analyse (10 min plus tard) : plus aucune voix, la même alerte n''est pas redite'
Invoke-ScanMenaces; Invoke-ScanMenaces
Verifier ($script:Entrees.Count -eq 0) 'ni à la 3e, ni à la 4e'
$script:ModeJeu = $true; $script:Retenu.Clear(); Remove-Item (Get-FichierAlertes) -ErrorAction SilentlyContinue; $script:AlertesCache = $null
Invoke-ScanMenaces; Invoke-ScanMenaces
Verifier ($script:Entrees.Count -eq 0 -and $script:Retenu.Count -eq 1 -and $script:Retenu[0].grave) 'mode jeu : l''alerte grave est gardée en silence, UNE seule fois ; la non grave n''est pas retenue'
$script:ModeJeu = $false; $script:Retenu.Clear()

Write-Host '6) Micro : choix par config.json, niveau en direct, « J''ai entendu »'
$Config | Add-Member -NotePropertyName micro_nom -NotePropertyValue 'Arctis "X"' -Force
$mc = Get-MicroConfig
Verifier ($mc.nom -eq 'Arctis X' -and $mc.seuil -eq 0.65) 'micro_nom lu dans config.json (guillemets retirés) ; seuil du mot « Jarvis » : 0.65 (0.8 auparavant)'
$a = Get-ArgsEcoute 'C:\x\ecoute.py'
Verifier ($a -match '--continu' -and $a -match '--micro "Arctis X"' -and $a -match '--seuil 0\.65') 'l''écoute reçoit --micro et --seuil'
$Config.micro_nom = ''; Verifier ((Get-ArgsEcoute 'C:\x\ecoute.py') -notmatch '--micro') 'micro_nom vide : micro par défaut de Windows'
Verifier ((Read-LigneMicro 'NIVEAU:57') -and $script:MicroNiveau -eq 57) 'ligne NIVEAU lue'
Verifier ((Read-LigneMicro 'MICRO:Microphone (ArctisX PnP)') -and $script:MicroNom -match 'ArctisX') 'ligne MICRO lue (nom du micro utilisé)'
Verifier ((Read-LigneMicro 'MICRO_ABSENT:Bidule') -and $script:MicroAbsent -eq 'Bidule') 'micro demandé introuvable : signalé'
Verifier (-not (Read-LigneMicro 'ORDRE:ouvre chrome')) 'une ligne d''ordre n''est pas absorbée'
$script:DernierEntendu = 'ouvre chrome'; $script:DernierEntenduHeure = Get-Date
$m = Get-DonneesMicro
Verifier ($m.niveau -eq 57 -and $m.actif -and $m.entendu -eq 'ouvre chrome' -and $m.absent -eq 'Bidule') 'le tableau de bord reçoit niveau, « entendu » et micro absent'
$script:MicroNiveauHeure = (Get-Date).AddSeconds(-10); Verifier ((Get-DonneesMicro).niveau -eq 0 -and -not (Get-DonneesMicro).actif) 'sans nouvelles du micro depuis 3 s : niveau 0, marqué muet'
$d = Get-DonneesTableau
Verifier ($d.ContainsKey('micro') -and $d.ContainsKey('alertes') -and $d.ContainsKey('mode_jeu')) 'données du tableau : micro, alertes, mode_jeu'

Write-Host '7) Reconnaissance du mot « Jarvis » (Python, sans micro)'
$py = @'
import sys, importlib.util
spec = importlib.util.spec_from_file_location("ecoute", sys.argv[1]); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
ok = [mot for mot in ("jarvis", "jarvisse", "jarvy", "jervis", "jarvoir", "gervais") if m.est_wake(mot)]
ko = [mot for mot in ("bonjour", "service", "jar", "ouvre", "chrome", "parvis", "jardin", "arrive", "paris", "servir", "marvin", "") if m.est_wake(mot)]
m.SEUIL = 0.8
ancien = [mot for mot in ("jarvoir",) if m.est_wake(mot)]
m.SEUIL = 0.65
print("OK", ",".join(ok)); print("KO", ",".join(ko)); print("ANCIEN", ",".join(ancien))
print("NIV0", m.niveau_pct(b"\x00\x00" * 4000)); import math, struct
fort = b"".join(struct.pack("<h", int(12000 * math.sin(i / 5))) for i in range(4000)); faible = b"".join(struct.pack("<h", int(60 * math.sin(i / 5))) for i in range(4000))
print("FORT", m.niveau_pct(fort)); print("FAIBLE", m.niveau_pct(faible))
print("STOP", m.est_stop("jarvis stop"), m.est_stop("jarvy stoppe"), m.est_stop("bonjour stop"))
m.VARIANTES = m.charger_variantes("jarvis, gervais,varices")
print("VAR", m.extraire("hey varices ouvre chrome"), "|", m.extraire("ah"), "|", m.extraire("gervais"), "|", m.extraire("les varices du jardin") is not None)
print("VARKO", ",".join(x for x in ("jardin", "arrive", "paris", "service", "servis", "javier", "davis") if m.est_wake(x)))
print("DEFAUT", "varices" in m.charger_variantes(""))
'@
$f = Join-Path $tmp 'wake.py'; [IO.File]::WriteAllText($f, $py, [Text.UTF8Encoding]::new($false))
$s = & python -I $f (Join-Path $Root 'voix\ecoute.py') 2>&1 | Out-String
$ok = ([regex]::Match($s, '(?m)^OK (.*)$').Groups[1].Value) -split ','; $ko = ([regex]::Match($s, '(?m)^KO (.*)$').Groups[1].Value).Trim()
Verifier (($ok -contains 'jarvis') -and ($ok -contains 'jarvy') -and ($ok -contains 'jervis') -and ($ok -contains 'jarvoir')) "variantes reconnues avec le nouveau seuil : $($ok -join ' ')"
Verifier ($ko -eq '') "mots qui ne doivent pas déclencher Jarvis : aucun faux positif ($ko)"
Verifier (([regex]::Match($s, '(?m)^ANCIEN (.*)$').Groups[1].Value).Trim() -eq '') '« jarvoir » (variante) était manqué avec l''ancien seuil 0.8, maintenant reconnu'
Verifier ($s -match 'NIV0 0') 'niveau du micro : silence = 0'
$fort = [int]([regex]::Match($s, 'FORT (\d+)').Groups[1].Value); $faible = [int]([regex]::Match($s, 'FAIBLE (\d+)').Groups[1].Value)
Verifier ($fort -gt 60 -and $faible -lt 25 -and $fort -gt $faible) "niveau du micro : voix forte $fort %, souffle faible $faible %"
Verifier ($s -match 'STOP True True False') '« Jarvis stop » reste détecté (y compris variantes), sans « Jarvis » pas d''arrêt'
Verifier ($s -match 'VAR ouvre chrome \| None \|\s+\| False') '« hey varices ouvre chrome » déclenche (ordre « ouvre chrome »), « ah » non, « gervais » seul = activation, « les varices du jardin » (mot au milieu) ne déclenche plus'
Verifier (([regex]::Match($s, '(?m)^VARKO (.*)$').Groups[1].Value).Trim() -eq '') 'variantes : toujours aucun faux positif (jardin, arrive, paris, service, servis, javier, davis…)'
Verifier ($s -match 'DEFAUT True') 'sans liste fournie, la liste par défaut (dont « varices ») s''applique'
$Config | Add-Member -NotePropertyName mot_activation_variantes -NotePropertyValue @('Jarvis', 'varices', 'Gervais') -Force
$mc = Get-MicroConfig; Verifier (($mc.variantes -join ',') -eq 'jarvis,varices,gervais') 'config.json mot_activation_variantes lu (minuscules)'
$Config.micro_nom = ''; Verifier ((Get-ArgsEcoute 'C:\x\ecoute.py') -match '--variantes "jarvis,varices,gervais"') 'l''écoute reçoit --variantes'
$l = & python -I (Join-Path $Root 'voix\ecoute.py') --liste 2>$null
Verifier (@($l | Where-Object { $_ -match '^\d+\t' }).Count -ge 1) "la liste des micros fonctionne (aucun micro ouvert) : $(@($l | Where-Object { $_ -match '^\d+\t' }).Count) entrée(s)"

Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
if ($echecs) { Write-Host "`nÉCHEC : $echecs vérification(s) en échec." -ForegroundColor Red; exit 1 }
Write-Host "`nRÉUSSI"; exit 0
