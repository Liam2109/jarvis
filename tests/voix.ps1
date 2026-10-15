# Test de la COMPRÉHENSION et de l'EXÉCUTION des ordres vocaux — 100 % SIMULÉ : aucun micro, aucun son, aucune fenêtre, aucune vraie touche, aucun Ollama,
# aucun téléchargement. Les phrases « mal articulées » sont des textes simulés (ce que Vosk écrirait), l'écoute est une fausse file de lignes.
# Code de sortie 0 = réussi.
$ErrorActionPreference = 'Stop'
$env:JARVIS_TEST = '1'      # TEST SILENCIEUX : aucun son, aucune fenêtre, aucun micro, aucune touche, aucune action réelle (voir lib\journal.ps1)
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $Root 'lib\journal.ps1')
$TR = Join-Path $env:TEMP ('jarvis-test-' + [guid]::NewGuid().ToString('N').Substring(0, 8)); New-Item -ItemType Directory $TR, "$TR\memoire", "$TR\logs" | Out-Null; $script:JarvisRoot = $TR
"# To-do de Liam" | Set-Content "$TR\memoire\todo.md" -Encoding UTF8; '# Notes' | Set-Content "$TR\memoire\notes.md" -Encoding UTF8; '# R' | Set-Content "$TR\memoire\resume.md" -Encoding UTF8
$Config = Get-Content (Get-ConfigPath) -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($l in 'voix', 'business', 'permissions', 'actions', 'coffre', 'entrees', 'ecrans', 'tableau', 'visage', 'sons', 'raccourcis', 'cerveau', 'cerveau-local', 'veille', 'memoire', 'rapide', 'discretion', 'modejeu', 'marche', 'priorite', 'comprehension', 'matin', 'boucle') { . (Join-Path $Root "lib\$l.ps1") }
$script:JarvisRoot = $TR
$echecs = 0
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }

# ===================== A) Python : mot d'éveil, fenêtre d'ordre, moteurs (sans micro) =====================
Write-Host '1) Reconnaissance du mot d''éveil et fenêtre d''ordre (Python, phrases simulées)'
$py = @'
import sys, os, importlib.util, json, subprocess, tempfile, types
spec = importlib.util.spec_from_file_location("ecoute", sys.argv[1]); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
def T(nom, cond): print("T", nom, bool(cond))
def ordres(lignes): return [l[6:] for l in lignes if l.startswith("ORDRE:")]
def diag(lignes): return json.loads([l for l in lignes if l.startswith("DIAG:")][0][5:])
d = m.Dialogue(8.0)
# --- phrases mal articulées : ce que le petit modèle écrit au lieu de « Jarvis »
for brut, attendu in [("varices ouvre chrome", "ouvre chrome"), ("hey varices ouvre chrome", "ouvre chrome"), ("gervais baisse la musique", "baisse la musique"),
                      ("jar vis baisse la musique", "baisse la musique"), ("jarvi mets le volume à trente", "mets le volume à trente"), ("ouvre chrome jarvis", "ouvre chrome"),
                      ("ok jarvis quelle heure est il", "quelle heure est il"), ("harvey passe en sourdine", "passe en sourdine")]:
    T("dans la même phrase : " + brut, ordres(d.phrase(brut, 100.0)) == [attendu])
# --- pas de faux positifs
for brut in ["ouvre le jardin", "je suis arrivé à paris", "le parvis de l'église", "service rendu", "marvin ouvre chrome", "bonjour tout le monde"]:
    l = d.phrase(brut, 200.0); T("aucun ordre pour : " + brut, ordres(l) == [] and diag(l)["raison"].startswith("pas de mot d'éveil"))
# --- place du mot d'éveil : début, seul, ou fin d'une phrase de 6 mots au plus
LONGUE = "je n'ai pas recette rétournation là c'est un peu de la merde donc j'essaie de faire passer le temps de créer les jarvis"
d2 = m.Dialogue(8.0)
l = d2.phrase(LONGUE, 300.0); x = diag(l)
T("vraie phrase longue (« …de créer les jarvis ») : AUCUN déclenchement", ordres(l) == [] and "ACTIVE" not in l and x["wake"] is False)
T("... raison affichée : mot trouvé mais phrase trop longue", x["etat"] == "ignoré" and x["mot"] == "jarvis" and x["raison"].startswith("mot trouvé (« jarvis ») mais phrase trop longue") and "6 mots au plus" in x["raison"])
T("... et aucune fenêtre d'ordre ouverte par erreur", not d2.fenetre_ouverte(301.0) and ordres(d2.phrase("ouvre chrome", 302.0)) == [])
l = d2.phrase("jarvis", 310.0); T("« jarvis » seul : déclenche (fenêtre d'ordre)", "ACTIVE" in l and diag(l)["wake"] is True)
d2 = m.Dialogue(8.0)
T("« jarvis quelle heure est-il » : déclenche", ordres(d2.phrase("jarvis quelle heure est-il", 1.0)) == ["quelle heure est-il"])
T("« baisse la musique jarvis » (fin, 4 mots) : déclenche", ordres(d2.phrase("baisse la musique jarvis", 2.0)) == ["baisse la musique"])
T("« ouvre chrome jarvis » (fin, 3 mots) : déclenche", ordres(d2.phrase("ouvre chrome jarvis", 3.0)) == ["ouvre chrome"])
T("fin de phrase de 6 mots exactement : déclenche", ordres(d2.phrase("peux tu baisser la musique jarvis", 4.0)) == ["peux tu baisser la musique"])
l = d2.phrase("peux tu vraiment baisser la musique jarvis", 5.0); T("fin de phrase de 7 mots : ne déclenche pas (trop longue)", ordres(l) == [] and "trop longue (7 mots" in diag(l)["raison"])
l = d2.phrase("le jarvis est cassé aujourd'hui", 6.0); T("au milieu : ne déclenche pas (pas en début de phrase)", ordres(l) == [] and diag(l)["raison"] == "mot trouvé (« jarvis ») mais pas en début de phrase")
l = d2.phrase("hey jarvis ouvre chrome", 7.0); T("après un mot d'appel (hey) : c'est un début de phrase", ordres(l) == ["ouvre chrome"])
l = d2.phrase("j'ai dit jarvis ouvre chrome tout à l'heure à mon collègue", 8.0); T("mot au milieu d'une longue phrase : ne déclenche pas", ordres(l) == [])
T("diagnostiquer_wake : raisons lisibles pour le mode « mots »", m.diagnostiquer_wake("bonjour tout le monde")["raison"] == "pas de mot d'éveil" and m.diagnostiquer_wake("jarvis")["valide"])
T("arrêt d'urgence toujours reconnu, même dans une phrase longue", m.est_stop("attention à tout jarvis stop"))
# --- mot d'éveil seul, puis l'ordre dans la fenêtre (8 s), sans répéter le mot
d = m.Dialogue(8.0)
l = d.phrase("varices", 10.0); T("mot seul : fenêtre ouverte (ACTIVE)", "ACTIVE" in l and diag(l)["etat"] == "fenêtre ouverte" and ordres(l) == [])
l = d.phrase("ouvre chrome", 14.0); T("ordre 4 s plus tard, sans le mot : accepté", ordres(l) == ["ouvre chrome"] and diag(l)["etat"] == "ordre (fenêtre)")
l = d.phrase("ouvre chrome", 15.0); T("la fenêtre est consommée : plus d'ordre sans le mot", ordres(l) == [])
d = m.Dialogue(8.0); d.phrase("jarvis", 10.0)
l = d.phrase("baisse la musique", 17.9); T("à 7,9 s : encore dans la fenêtre", ordres(l) == ["baisse la musique"])
d = m.Dialogue(8.0); d.phrase("jarvis", 10.0)
l = d.phrase("baisse la musique", 18.5); T("à 8,5 s : fenêtre refermée, ordre ignoré avec la raison", ordres(l) == [] and "refermée" in diag(l)["raison"])
d = m.Dialogue(8.0); d.phrase("jarvis", 10.0); d.partiel("baisse", 17.0)
l = d.phrase("baisse la musique", 20.0); T("phrase COMMENCÉE dans la fenêtre mais finie après 8 s : acceptée", ordres(l) == ["baisse la musique"])
d = m.Dialogue(8.0); d.phrase("jarvis", 10.0); d.partiel("", 12.0)
T("un partiel vide n'ouvre rien", not d.parole_fenetre)
d = m.Dialogue(5.0); d.phrase("jarvis", 10.0)
T("fenêtre réglable (5 s)", ordres(d.phrase("ouvre chrome", 14.0)) == ["ouvre chrome"] and ordres(m.Dialogue(5.0).phrase("ouvre chrome", 20.0)) == [])
# --- diagnostic : sourdine / Jarvis parle
d = m.Dialogue(8.0)
l = d.phrase("jarvis ouvre chrome", 1.0, ecoute_ordres=False, sourdine=True); x = diag(l)
T("sourdine : aucun ORDRE, raison « sourdine »", ordres(l) == [] and x["raison"] == "sourdine" and x["wake"] is True and not any(s.startswith("ENTENDU") for s in l))
l = d.phrase("jarvis ouvre chrome", 1.0, ecoute_ordres=False, sourdine=False); T("Jarvis parle : aucun ORDRE, raison explicite", ordres(l) == [] and "Jarvis parle" in diag(l)["raison"])
l = d.phrase("jarvis ouvre chrome", 1.0); T("ordre normal : ENTENDU, DIAG puis ORDRE (dans cet ordre)", [s.split(":")[0] for s in l] == ["ENTENDU", "DIAG", "ORDRE"])
T("arrêt d'urgence reconnu aussi mal articulé", m.est_stop("jar vis stop") and m.est_stop("varices stoppe") and not m.est_stop("bonjour stop"))
# --- accents : la sortie est en UTF-8 (sinon « mets le volume à 30 » arrivait avec des caractères cassés dans PowerShell)
code = "import sys; sys.path.insert(0, r'%s'); import ecoute; ecoute.configurer_sortie(); print('mets le volume à 30 é')" % os.path.dirname(sys.argv[1])
r = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True)
T("sortie en UTF-8 quand elle est lue par Jarvis", r.stdout.decode("utf-8").strip() == "mets le volume à 30 é")
# --- moteurs : chemins, repli sans rien télécharger
ici = os.path.dirname(sys.argv[1])
T("chemin vosk par défaut", m.chemin_modele("vosk").endswith(os.path.join("models", "vosk-model-small-fr-0.22")))
T("chemin vosk-grand", m.chemin_modele("vosk-grand").endswith(os.path.join("models", "vosk-model-fr-0.22")))
T("chemin faster-whisper (taille configurable)", m.chemin_modele("faster-whisper", "", "medium").endswith(os.path.join("models", "faster-whisper-medium")))
class FauxVosk:
    nom = "vosk"
    def __init__(self, chemin, taux): self.chemin = chemin
m.MoteurVosk = FauxVosk
mo, msg = m.creer_moteur("faster-whisper", 16000, "", "taille-absente")
T("faster-whisper absent -> repli vosk + message « rien n'est téléchargé »", mo.nom == "vosk" and msg.startswith("MOTEUR_REPLI:faster-whisper") and "rien n'est téléchargé" in msg)
mo, msg = m.creer_moteur("vosk-grand", 16000, "", "small")
T("vosk-grand absent -> repli vosk (petit modèle) + message", mo.nom == "vosk" and msg.startswith("MOTEUR_REPLI:vosk-grand") and mo.chemin.endswith("vosk-model-small-fr-0.22"))
mo, msg = m.creer_moteur("n_importe_quoi", 16000)
T("moteur inconnu -> vosk sans bruit", mo.nom == "vosk" and msg == "")
# --- faster-whisper (faux paquet, faux modèle) : détection de voix par le niveau, une transcription par phrase, local_files_only
appels = {}
class FauxWhisperModel:
    def __init__(self, chemin, **kw): appels["init"] = (chemin, kw)
    def transcribe(self, audio, **kw):
        appels["transcribe"] = kw; appels["n"] = appels.get("n", 0) + 1
        return [types.SimpleNamespace(text=" Jarvis, ouvre Chrome !")], None
sys.modules["faster_whisper"] = types.SimpleNamespace(WhisperModel=FauxWhisperModel)
dossier = tempfile.mkdtemp(); mo, msg = m.creer_moteur("faster-whisper", 16000, dossier, "small")
T("faster-whisper chargé depuis le dossier local", mo.nom == "faster-whisper" and msg == "" and appels["init"][0] == dossier)
T("jamais de téléchargement : local_files_only=True, CPU int8", appels["init"][1].get("local_files_only") is True and appels["init"][1].get("compute_type") == "int8" and appels["init"][1].get("device") == "cpu")
import math, struct
def bloc(amplitude): return b"".join(struct.pack("<h", int(amplitude * math.sin(i / 4.0))) for i in range(4000))
sortie = []
for k in range(6):  sortie.append(mo.bloc(bloc(9000)))
T("pendant la phrase : pas de texte final, partiel non vide", all(t is None for t, p in sortie) and sortie[-1][1] == "…")
fin = [mo.bloc(bloc(20)) for k in range(16)]      # 1,5 s de silence = fin de phrase (silence_fin_ms)
n0 = appels["n"]
T("après le silence de fin de phrase (1,5 s) : UNE transcription (le modèle a été chauffé au chargement), texte normalisé", [t for t, p in fin if t is not None] == ["jarvis ouvre chrome"] and appels["n"] == n0 and n0 == 2)
T("temps de la phrase mesurés (silence, reconnaissance)", "reco_ms" in mo.infos and "silence_ms" in mo.infos and mo.infos["appareil"] == "cpu")
T("la transcription est en français, sans enchaîner le contexte", appels["transcribe"].get("language") == "fr" and appels["transcribe"].get("condition_on_previous_text") is False)
mo.bloc(bloc(9000)); r = [mo.bloc(bloc(20)) for k in range(16)]
T("un claquement (1 bloc) n'est pas transcrit", [t for t, p in r if t is not None] == [""] and appels["n"] == 2)
T("normaliser_texte retire majuscules et ponctuation", m.normaliser_texte("Jarvis, ouvre Chrome !") == "jarvis ouvre chrome")
'@
$f = Join-Path $TR 'voix.py'; [IO.File]::WriteAllText($f, $py, [Text.UTF8Encoding]::new($false))
$s = & python -I $f (Join-Path $Root 'voix\ecoute.py') 2>&1 | Out-String
foreach ($ligne in ($s -split "`r?`n" | Where-Object { $_ -match '^T ' })) { $ok = $ligne -match ' True\s*$'; Verifier $ok ($ligne -replace '^T ', '' -replace ' (True|False)\s*$', '') }
Verifier ($s -notmatch 'Traceback|Error') "aucune erreur Python$(if ($s -match 'Traceback|Error') { ' : ' + ($s -split "`n" | Select-Object -Last 4) -join ' ' })"

# ===================== B) PowerShell : diagnostic, fenêtre, exécution, permissions =====================
Write-Host '2) Écoute simulée : lignes DIAG / ORDRE / ACTIVE traitées par Jarvis'
$script:Dits = @(); $script:Sequence = @(); $script:AppelsGetPlan = 0; $script:PlanCerveau = $null
function Parler([string]$Texte, $Langue) { if ($script:Actif -ne $false -and $script:ModeJeu -ne $true) { $script:Dits += $Texte }; Add-Conv 'jarvis' $Texte }
function Get-Plan([string]$o) { $script:AppelsGetPlan++; $script:VoieCerveau = 'claude'; if ($script:PlanCerveau) { $script:PlanCerveau } else { [pscustomobject]@{ dit = 'Réponse du cerveau.'; langue = 'fr'; actions = @() } } }
$script:Actif = $true; $script:ModeJeu = $false
$script:Actions['ouvrir_app'].run = { param($a) $script:Sequence += "ouvrir_app:$($a.nom)"; Rep $true "Application ouverte : $($a.nom)" }
$script:Actions['fermer_app'].run = { param($a) $script:Sequence += "fermer_app:$($a.nom)"; Rep $false "Aucune fenêtre ouverte pour « $($a.nom) »." }
$script:Actions['mode_jeu'].run = { param($a) $script:Sequence += "mode_jeu:$($a.etat)"; Rep $true "Mode jeu $($a.etat)." }
$script:Actions['sourdine'].run = { param($a) $script:Sequence += 'sourdine'; Rep $true 'Sourdine activée.' }
$script:Actions['supprimer_fichier'].run = { param($a) $script:Sequence += 'SUPPRESSION'; Rep $true 'supprimé' }
$script:Actions['oublie_tout'].run = { param($a) $script:Sequence += 'OUBLI'; Rep $true 'oublié' }
# fausse écoute : un objet qui sert des lignes comme le ferait le processus Python
$script:FileLignes = New-Object System.Collections.Generic.Queue[string]
$script:Ecoute = [pscustomobject]@{ HasExited = $false; StandardOutput = $null }
$script:Ecoute.StandardOutput = [pscustomobject]@{}
$script:Ecoute.StandardOutput | Add-Member ScriptMethod ReadLineAsync { $l = if ($script:FileLignes.Count) { $script:FileLignes.Dequeue() } else { $null }; if ($null -eq $l) { [Threading.Tasks.Task]::FromResult([string]'NIVEAU:5') } else { [Threading.Tasks.Task]::FromResult([string]$l) } }
$script:EcouteTache = [Threading.Tasks.Task]::FromResult([string]'NIVEAU:5')
function Pomper([string[]]$lignes) { foreach ($x in $lignes) { $script:FileLignes.Enqueue($x) }; for ($i = 0; $i -lt ($lignes.Count + 2); $i++) { Invoke-Pump } }
function Diag([int]$id, [string]$brut, [bool]$wake, [string]$mot, [string]$etat, [string]$raison = '') { 'DIAG:' + (@{ id = $id; brut = $brut; wake = $wake; mot = $mot; ordre = ''; etat = $etat; raison = $raison } | ConvertTo-Json -Compress) }
function Traiter { while ($script:Entrees.Count) { $e = $script:Entrees.Dequeue(); if (-not $e.entendu) { Invoke-Entree $e } } }
$script:Entrees.Clear()

# a) « Jarvis, ouvre le bloc-notes » : mot d'éveil + ordre dans la même phrase
Pomper @('ENTENDU:varices ouvre le bloc-notes', (Diag 1 'varices ouvre le bloc-notes' $true 'varices' 'ordre'), 'ORDRE:ouvre le bloc-notes')
Traiter
$r = Get-DiagPanneau 8 | Where-Object { $_.brut -eq 'varices ouvre le bloc-notes' }
Verifier ($script:Sequence -contains 'ouvrir_app:bloc-notes') 'l''ordre est EXÉCUTÉ (ouvrir_app : bloc-notes)'
Verifier ($r.wake -eq 'oui' -and $r.mot -eq 'varices' -and $r.intention -eq 'app_ouvrir' -and $r.resultat -like 'action lancée : *bloc-notes*') "diagnostic : éveil $($r.wake) ($($r.mot)), intention « $($r.intention) », « $($r.resultat) »"
# b) mot seul, puis ordre dans la fenêtre
Pomper @('ENTENDU:jarvis', (Diag 2 'jarvis' $true 'jarvis' 'fenêtre ouverte' "j'écoute l'ordre pendant 8 s"), 'ACTIVE')
Verifier ((Get-FenetreOrdreRestante) -ge 7 -and (Get-FenetreOrdreRestante) -le 8 -and (Get-DonneesTableau).fenetre_ordre -ge 7) "« Jarvis » seul : fenêtre d'ordre ouverte ($(Get-FenetreOrdreRestante) s) et visible au tableau"
$script:Sequence = @()
Pomper @('ENTENDU:ferme chrome', (Diag 3 'ferme chrome' $false '' 'ordre (fenêtre)'), 'ORDRE:ferme chrome')
Traiter
Verifier ($script:Sequence -contains 'fermer_app:chrome') 'l''ordre donné dans la fenêtre (sans répéter le mot) est exécuté'
# c) phrase sans mot d'éveil : ignorée, raison dans le diagnostic
Pomper @('ENTENDU:ouvre chrome', (Diag 4 'ouvre chrome' $false '' 'ignoré' "pas de mot d'éveil"))
$x = Get-DiagPanneau 8 | Where-Object { $_.brut -eq 'ouvre chrome' -and $_.resultat -like 'non exécuté*' }
Verifier ($x.wake -eq 'non' -and $x.intention -eq 'aucune' -and $x.resultat -eq "non exécuté : pas de mot d'éveil") "sans mot d'éveil : « $($x.resultat) »"
# c bis) la vraie phrase longue : la ligne DIAG produite par Python s'affiche avec sa raison
$pyl = @'
import sys, importlib.util
spec = importlib.util.spec_from_file_location("ecoute", sys.argv[1]); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
sortie = m.Dialogue(8.0).phrase("je n'ai pas recette rétournation là c'est un peu de la merde donc j'essaie de faire passer le temps de créer les jarvis", 5.0)
open(sys.argv[2], "w", encoding="utf-8").write("\n".join(sortie))
'@
$fl = Join-Path $TR 'longue.py'; [IO.File]::WriteAllText($fl, $pyl, [Text.UTF8Encoding]::new($false))
$sortiePy = Join-Path $TR 'longue.txt'; & python -I $fl (Join-Path $Root 'voix\ecoute.py') $sortiePy
$lignesPy = @(Get-Content $sortiePy -Encoding UTF8)
$script:Sequence = @(); $script:Entrees.Clear()
Pomper $lignesPy; Traiter
$x = @(Get-DiagPanneau 8 | Where-Object { $_.brut -like '*créer les jarvis' })[0]
Verifier ($script:Sequence.Count -eq 0 -and $script:Entrees.Count -eq 0 -and $x.wake -eq 'non' -and $x.mot -eq 'jarvis' -and $x.resultat -like 'non exécuté : mot trouvé (*jarvis*) mais phrase trop longue*') "diagnostic de la vraie phrase : éveil $($x.wake), « $($x.resultat) »"
# d) ordre inconnu : aucune intention -> cerveau ; réponse sans action
$script:Dits = @(); $script:AppelsGetPlan = 0
Pomper @((Diag 5 'jarvis fais un truc bizarre' $true 'jarvis' 'ordre'), 'ORDRE:fais un truc bizarre'); Traiter
$x = Get-DiagPanneau 8 | Where-Object { $_.brut -eq 'jarvis fais un truc bizarre' }
Verifier ($script:AppelsGetPlan -eq 1 -and $x.intention -like 'aucune règle*' -and $x.resultat -eq 'aucune action à lancer (réponse parlée seulement)') "ordre inconnu : intention « $($x.intention) » ; « $($x.resultat) »"
# e) permission niveau 3 : refus expliqué
$script:PlanCerveau = [pscustomobject]@{ dit = ''; langue = 'fr'; actions = @([pscustomobject]@{ type = 'supprimer_fichier'; chemin = 'C:\Windows\System32\x.dll' }) }
Pomper @((Diag 6 'jarvis supprime le fichier système' $true 'jarvis' 'ordre'), 'ORDRE:supprime le fichier système'); Traiter
$x = Get-DiagPanneau 8 | Where-Object { $_.brut -eq 'jarvis supprime le fichier système' }
Verifier (($script:Sequence -notcontains 'SUPPRESSION') -and $x.resultat -match '^non exécuté : supprimer_fichier — permission : refusé \(niveau 3') "niveau 3 : « $($x.resultat) »"
# f) permission niveau 2 non confirmée
$script:PlanCerveau = [pscustomobject]@{ dit = ''; langue = 'fr'; actions = @([pscustomobject]@{ type = 'oublie_tout' }) }
$script:ReponseTest = 'non'
Pomper @((Diag 7 'jarvis oublie tout' $true 'jarvis' 'ordre'), 'ORDRE:oublie tout'); $script:PlanCerveau = $null; Traiter
$x = Get-DiagPanneau 8 | Where-Object { $_.brut -eq 'jarvis oublie tout' }
Verifier (($script:Sequence -notcontains 'OUBLI') -and $x.resultat -match 'confirmation de niveau 2 non donnée') "niveau 2 inchangé (confirmation exigée) : « $($x.resultat) »"
$script:ReponseTest = ''
# g) erreur d'exécution
$script:Sequence = @()
Pomper @((Diag 8 'jarvis ferme le bloc-notes' $true 'jarvis' 'ordre'), 'ORDRE:ferme le bloc-notes'); Traiter
$x = Get-DiagPanneau 8 | Where-Object { $_.brut -eq 'jarvis ferme le bloc-notes' }
Verifier ($x.resultat -match 'erreur : Aucune fenêtre ouverte') "erreur d'une action : « $($x.resultat) »"
# h) sourdine : aucune exécution
$script:Actif = $false; $script:Sequence = @()
Pomper @((Diag 9 'jarvis ouvre chrome' $true 'jarvis' 'ordre'), 'ORDRE:ouvre chrome'); Traiter
$x = Get-DiagPanneau 8 | Where-Object { $_.brut -eq 'jarvis ouvre chrome' }
Verifier ($script:Sequence.Count -eq 0 -and $x.resultat -eq 'non exécuté : sourdine') "sourdine : rien d'exécuté, « $($x.resultat) »"
$script:Actif = $true
# i) mode jeu : aucune exécution sauf pour en sortir
$script:ModeJeu = $true; $script:Sequence = @()
Pomper @((Diag 10 'jarvis ouvre chrome' $true 'jarvis' 'ordre'), 'ORDRE:ouvre chrome'); Traiter
$x = Get-DiagPanneau 8 | Where-Object { $_.brut -eq 'jarvis ouvre chrome' -and $_.resultat -like '*mode jeu*' }
Verifier ($script:Sequence.Count -eq 0 -and $x.resultat -like 'non exécuté : mode jeu*') "mode jeu : rien d'exécuté, « $($x.resultat) »"
Pomper @((Diag 11 'jarvis désactive le mode jeu' $true 'jarvis' 'ordre'), 'ORDRE:désactive le mode jeu'); Traiter
Verifier ($script:Sequence -contains 'mode_jeu:off') '... mais « mode jeu off » reste permis (sinon on ne pourrait plus en sortir)'
Verifier ((Test-OrdreAutoriseModeJeu 'passe en sourdine') -and -not (Test-OrdreAutoriseModeJeu 'ouvre chrome') -and -not (Test-OrdreAutoriseModeJeu 'baisse la musique')) 'en mode jeu : seulement « mode jeu off », « sourdine » et « quitte »'
$script:ModeJeu = $false
# j) ordre écrit (clavier / tableau) : une ligne de diagnostic aussi
$script:Sequence = @(); $script:Entrees.Enqueue(@{ src = 'clavier'; texte = 'ouvre chrome'; entendu = $false }); Traiter
$x = Get-DiagPanneau 8 | Where-Object { $_.wake -eq 'saisie' -and $_.brut -eq 'ouvre chrome' }
Verifier ($x -and $x.resultat -like 'action lancée*') 'ordre écrit : diagnostic « saisie » + action lancée'
Verifier ((Get-DiagPanneau 8)[0].brut -eq 'ouvre chrome' -and (Get-DonneesTableau).diag.Count -ge 5) 'le tableau reçoit le diagnostic, le plus récent en premier'
$script:Ecoute = $null; $script:EcouteTache = $null

# ===================== C) Compréhension tolérante =====================
Write-Host '3) Compréhension tolérante : le cerveau local choisit dans la liste fermée'
$Config | Add-Member routeur_intention $false -Force      # ancien étage « liste fermée » : le routeur d'intention est testé à part (tests/routeur.ps1)
$script:OllamaAppels = 0; $script:OllamaReponse = ''; $script:ModeCerveau = 'local'
function Invoke-Ollama([string]$systeme, [string]$utilisateur, [int]$timeoutSec = 0) { $script:OllamaAppels++; $script:OllamaSysteme = $systeme; $script:OllamaUser = $utilisateur; $script:OllamaReponse }
function Get-ModeCerveau { $script:ModeCerveau }
$script:MusiqueEtat = $null; Remove-Item (Get-FichierMemoire 'musique.json') -ErrorAction SilentlyContinue
$script:OllamaReponse = '{"commande":"musique_baisser","parametre":""}'
$script:Dits = @(); $script:Sequence = @(); $script:AppelsGetPlan = 0; $script:DiagId = 0
Verifier ($null -eq (Get-PlanRapide 'jarvis, la mizik plus doucement')) '« la mizik plus doucement » : aucun mot-clé ne la comprend'
$v0 = Get-VolumeBase
Pomper @() ; $script:Entrees.Enqueue(@{ src = 'voix'; texte = 'la mizik plus doucement'; entendu = $false; diag = (New-DiagSaisie 'la mizik plus doucement' 'voix') }); Traiter
Verifier ((Get-VolumeBase) -lt $v0 -and $script:Dits[0] -eq "J'ai compris : baisse la musique." -and $script:AppelsGetPlan -eq 0) "mal articulé -> le cerveau local choisit « musique_baisser » ; Jarvis dit « $($script:Dits[0]) » ; sans Claude"
$x = @(Get-DiagPanneau 1)[0]; Verifier ($x.intention -eq 'tolérante:musique_baisser' -and $x.resultat -like 'action lancée*') "diagnostic : « $($x.intention) » -> $($x.resultat)"
Verifier ($script:OllamaSysteme -match 'LISTE FERMÉE' -and $script:OllamaSysteme -match '- ouvrir_app' -and $script:OllamaUser -match '<phrase_non_fiable>') 'le modèle ne reçoit que la liste fermée ; la phrase est marquée comme non fiable'
# application : seulement une application connue
$script:OllamaReponse = '{"commande":"ouvrir_app","parametre":"chrome"}'; $script:Sequence = @()
Invoke-Ordre 'ouvr crom'; Verifier ($script:Sequence -contains 'ouvrir_app:chrome') '« ouvr crom » -> ouvrir_app chrome (application connue)'
$script:OllamaReponse = '{"commande":"ouvrir_app","parametre":"logiciel_inconnu_xyz"}'; $script:Sequence = @(); $script:AppelsGetPlan = 0
Invoke-Ordre 'ouvr le trucmuche'; Verifier ($script:Sequence.Count -eq 0 -and $script:AppelsGetPlan -eq 1) 'application inconnue : rien d''exécuté, la phrase passe au cerveau habituel'
# jamais d'invention
foreach ($c in @(@('{"commande":"formater_disque","parametre":""}', 'commande hors liste'), @('{"commande":"powershell","parametre":"Remove-Item C:\\ -Recurse"}', 'powershell'), @('{"commande":"supprimer_fichier","parametre":"x"}', 'suppression'),
                 @('{"commande":"volume_niveau","parametre":"30; Stop-Computer"}', 'paramètre piégé'), @('{"commande":"volume_niveau","parametre":"250"}', 'nombre hors 0-100'), @('{"commande":"ouvrir_app","parametre":"chrome.exe & del *.*"}', 'application piégée'),
                 @('{"commande":"aucune","parametre":""}', 'aucune'), @('n''importe quoi', 'réponse non JSON'), @('', 'pas de réponse'))) {
    $script:OllamaReponse = $c[0]; $script:Sequence = @(); $script:AppelsGetPlan = 0
    $plan = Resolve-IntentionTolerante 'phrase mal comprise'
    Verifier ($null -eq $plan) "refusé : $($c[1])"
}
Verifier ((ConvertTo-PhraseCanonique 'ouvrir_app' 'bloc-notes') -eq 'ouvre bloc-notes' -and (ConvertTo-PhraseCanonique 'volume_niveau' '30') -eq 'mets le volume à 30' -and (ConvertTo-PhraseCanonique 'heure' 'ignoré') -eq 'quelle heure est-il') 'seules des phrases canoniques fixes sont produites'
$tous = @(); foreach ($c in $script:CommandesFermees) { $p = ConvertTo-PhraseCanonique $c.id $(if ($c.p -eq 'nombre') { '40' } elseif ($c.p -eq 'app') { 'chrome' } else { '' }); $plan = Get-PlanRapide $p; if (-not $plan) { $tous += "$($c.id) : « $p » non reconnue" } else { foreach ($a in @($plan.actions)) { $n = (Get-Niveau $a).niveau; if ($n -ge 2) { $tous += "$($c.id) niveau $n" } } } }
Verifier ($tous.Count -eq 0) "les $($script:CommandesFermees.Count) commandes de la liste ont toutes une règle, et AUCUNE n'est de niveau 2 ou 3 (permissions inchangées)$(if ($tous.Count) { ' : ' + ($tous -join ' ; ') })"
Verifier (-not ($script:CommandesFermees | Where-Object { $_.id -match 'powershell|supprimer|deplacer|installer|coffre|bitwarden|script|fichier' })) 'la liste ne contient ni PowerShell, ni suppression, ni installation, ni coffre'
# niveau 2 : même confirmation que d'habitude (le plan tolérant passe par Invoke-UneAction)
$cn = Get-Niveau ([pscustomobject]@{ type = 'oublie_tout' }); Verifier ($cn.niveau -eq 2) 'permission de niveau 2 inchangée (« oublie tout » exige toujours « oui »)'
# garde-fous d'usage
$script:OllamaAppels = 0; $script:ModeCerveau = 'claude'; $script:OllamaReponse = '{"commande":"heure","parametre":""}'
Verifier ($null -eq (Resolve-IntentionTolerante 'quelle eur') -and $script:OllamaAppels -eq 0) 'cerveau en mode « claude » : aucune compréhension tolérante, aucun appel'
$script:ModeCerveau = 'local'; $Config | Add-Member -NotePropertyName comprehension_tolerante -NotePropertyValue $false -Force
Verifier ($null -eq (Resolve-IntentionTolerante 'quelle eur') -and $script:OllamaAppels -eq 0) 'comprehension_tolerante = false : désactivée'
$Config.comprehension_tolerante = $true
$plan = Resolve-IntentionTolerante 'quelle eur'; Verifier ($plan -and $plan.regle -eq 'tolérante:heure') '« quelle eur » -> heure (liste fermée)'
$script:OllamaAppels = 0; $plan = Get-PlanRapide 'quelle heure est-il'; Verifier ($script:OllamaAppels -eq 0) 'une phrase bien comprise ne demande JAMAIS rien au modèle'

# ===================== D) Moteur configurable =====================
Write-Host '4) Moteur de reconnaissance configurable (moteur_voix)'
$a = Get-ArgsEcoute 'C:\x\ecoute.py'
Verifier ($a -match '--fenetre 8' -and $a -match '--moteur faster-whisper' -and $a -match '--whisper-modele small' -and $a -match '--whisper-peripherique cuda' -and $a -match '--whisper-threads 3' -and $a -match '--silence-fin 1.5' -and $a -match '--vocabulaire') "arguments (config.json : moteur_voix = faster-whisper) : $($a -replace '^.*--continu ', '')"
$Config | Add-Member -NotePropertyName moteur_voix -NotePropertyValue 'faster-whisper' -Force; $Config | Add-Member -NotePropertyName whisper_modele -NotePropertyValue 'medium' -Force; $Config | Add-Member -NotePropertyName fenetre_ordre_secondes -NotePropertyValue 10 -Force
$a = Get-ArgsEcoute 'C:\x\ecoute.py'
Verifier ($a -match '--moteur faster-whisper' -and $a -match '--whisper-modele medium' -and $a -match '--fenetre 10') 'moteur_voix = faster-whisper, whisper_modele = medium, fenêtre 10 s transmis à l''écoute'
$Config.moteur_voix = 'nimporte quoi; calc'; Verifier ((Get-MicroConfig).moteur -eq 'vosk') 'valeur inconnue (ou piégée) : retour à vosk'
$Config.moteur_voix = 'vosk-grand'; Verifier ((Get-MicroConfig).moteur -eq 'vosk-grand') 'vosk-grand accepté'
$Config.moteur_voix = 'vosk'; $Config.fenetre_ordre_secondes = 99; Verifier ((Get-FenetreOrdreSecondes) -eq 30) 'fenêtre bornée à 30 s'
Verifier ((Read-LigneMicro 'MOTEUR:vosk') -and $script:MoteurVoix -eq 'vosk' -and (Read-LigneMicro 'MOTEUR_REPLI:faster-whisper impossible (modèle absent) -> vosk') -and $script:MoteurVoixRepli -match 'impossible') 'lignes MOTEUR / MOTEUR_REPLI lues et journalisées'
$ec = Get-Content (Join-Path $Root 'voix\ecoute.py') -Raw -Encoding UTF8
Verifier ($ec -match 'local_files_only=True' -and $ec -notmatch 'snapshot_download|hf_hub_download|pip install|urlretrieve|urlopen') 'le code ne télécharge ni n''installe rien'
$cf = Get-Content (Join-Path $Root 'config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
Verifier ($cf.moteur_voix -eq 'faster-whisper' -and $cf.whisper_modele -eq 'small' -and $cf.whisper_peripherique -eq 'cuda' -and $cf.fenetre_ordre_secondes -eq 8 -and $cf.comprehension_tolerante -eq $true -and $cf.diagnostic_vocal -eq $true) 'config.json : moteur_voix = faster-whisper (small, cuda), fenêtre 8 s, compréhension tolérante et diagnostic activés'
Verifier (-not (Test-Path (Join-Path $Root 'voix\models\vosk-model-fr-0.22'))) 'le grand modèle Vosk n''a pas été téléchargé'
$dirs = @(Get-ChildItem (Join-Path $Root 'voix\models') -Directory | ForEach-Object { $_.Name })
Verifier (($dirs | Sort-Object) -join ',' -eq 'faster-whisper-small,piper,vosk-model-small-fr-0.22') "voix\models ne contient que (Whisper small, Vosk petit, voix Piper autorisée) : $($dirs -join ', ')"

# ===================== E) Le VRAI moteur se charge (fichier audio généré, sans micro, sans son) =====================
Write-Host '5) Chargement réel du moteur faster-whisper (fichier WAV généré en silence, sans micro)'
$modele = Join-Path $Root 'voix\models\faster-whisper-small'
$wav = Join-Path $TR 'ordre.wav'; $genere = $false
try {
    Add-Type -AssemblyName System.Speech
    $syn = New-Object System.Speech.Synthesis.SpeechSynthesizer
    $fr = $syn.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Culture.Name -like 'fr*' } | Select-Object -First 1
    if ($fr) {
        $syn.SelectVoice($fr.VoiceInfo.Name)
        $fmt = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(16000, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
        $syn.SetOutputToWaveFile($wav, $fmt); $syn.Speak('Jarvis, baisse la musique à trente pour cent.'); $syn.SetOutputToNull(); $genere = $true      # écrit dans un fichier : aucun son joué
    }
    $syn.Dispose()
} catch {}
if (-not (Test-Path (Join-Path $modele 'model.bin'))) { Write-Host '  (modèle faster-whisper-small non installé : test du chargement réel ignoré)' -ForegroundColor DarkGray }
elseif (-not $genere) { Write-Host '  (aucune voix française locale : test du chargement réel ignoré)' -ForegroundColor DarkGray }
else {
    $ec = Join-Path $Root 'voix\ecoute.py'
    try { [Console]::OutputEncoding = [Text.Encoding]::UTF8 } catch {}      # ecoute.py écrit en UTF-8 ; Jarvis le lit en UTF-8 (Start-Ecoute)
    $sv =& python -I $ec --fichier $wav --moteur vosk --variantes 'jarvis,gervais,varices' 2>&1 | Out-String
    $sw = & python -I $ec --fichier $wav --moteur faster-whisper --variantes 'jarvis,gervais,varices' 2>&1 | Out-String
    Verifier ($sv -match 'MOTEUR:vosk' -and $sv -match 'ORDRE:baisse la musique') 'Vosk (petit modèle) comprend le fichier de test'
    Verifier ($sw -match 'MOTEUR:faster-whisper' -and $sw -notmatch 'MOTEUR_REPLI') 'faster-whisper se charge depuis voix\models\faster-whisper-small (pas de repli)'
    Verifier ($sw -match 'ORDRE:baisse la musique') "faster-whisper comprend le fichier de test : $((($sw -split "`r?`n") | Where-Object { $_ -match '^(ENTENDU|ORDRE|DUREE)' }) -join ' | ')"
    # étage 1 : Vosk limité à la liste fermée (grammaire) ; hors liste -> faster-whisper (jamais la seule voie)
    $gram = Join-Path $TR 'grammaire.json'; ConvertTo-Json -InputObject @('jarvis baisse la musique à trente pour cent', 'jarvis passe en sourdine', 'jarvis quelle heure est-il') -Compress | Set-Content $gram -Encoding UTF8
    $sg = & python -I $ec --fichier $wav --moteur faster-whisper --grammaire $gram --variantes 'jarvis,gervais,varices' 2>&1 | Out-String
    $sh = & python -I $ec --fichier $wav --moteur faster-whisper --grammaire (Join-Path $TR 'inexistante.json') --variantes 'jarvis,gervais,varices' 2>&1 | Out-String
    $dg = [regex]::Match($sg, 'DUREE:([\d.]+)').Groups[1].Value; $dw = [regex]::Match($sh, 'DUREE:([\d.]+)').Groups[1].Value
    Verifier ($sg -match 'ORDRE:baisse la musique' -and $sg -match 'ETAGE:(vosk-grammaire|whisper)') "avec grammaire : l'ordre est compris dans tous les cas ($((($sg -split "`r?`n") | Where-Object { $_ -match '^(ETAGE|ENTENDU)' }) -join ' | ')) ; durée $dg s contre $dw s sans grammaire"
    Verifier ($sh -notmatch 'ETAGE:vosk-grammaire' -and $sh -match 'ETAGE:whisper') 'sans fichier de grammaire : faster-whisper seul (étage 1 absent)'
    $gram2 = Join-Path $TR 'grammaire2.json'; ConvertTo-Json -InputObject @('jarvis quelle heure est-il', 'jarvis passe en sourdine') -Compress | Set-Content $gram2 -Encoding UTF8
    $s2 = & python -I $ec --fichier $wav --moteur faster-whisper --grammaire $gram2 --variantes 'jarvis,gervais,varices' 2>&1 | Out-String
    Verifier ($s2 -match 'ETAGE:whisper' -and $s2 -notmatch 'ETAGE:vosk-grammaire' -and $s2 -match 'ORDRE:baisse la musique') 'phrase HORS de la grammaire : confiée à faster-whisper (la grammaire n''est jamais la seule voie)'
    $plan = Get-PlanRapide ([regex]::Match($sw, 'ORDRE:(.+)').Groups[1].Value.Trim())
    Verifier ($plan -and $plan.regle -eq 'musique_niveau') 'et le texte de Whisper (« à 30 ») est compris par une règle de Jarvis'
    # repli automatique : modèle absent -> Vosk, avec un message clair, sans rien télécharger
    $sr = & python -I $ec --fichier $wav --moteur faster-whisper --modele-chemin 'dossier-qui-nexiste-pas' --variantes 'jarvis,gervais,varices' 2>&1 | Out-String
    Verifier ($sr -match 'MOTEUR_REPLI:faster-whisper impossible' -and $sr -match 'MOTEUR:vosk' -and $sr -match 'ORDRE:baisse la musique' -and $sr -match "rien n'est téléchargé") 'modèle absent : retour automatique sur Vosk, message clair, l''ordre est quand même compris'
    Verifier (-not (Test-Path (Join-Path $Root 'voix\models\dossier-qui-nexiste-pas'))) '... et rien n''a été créé ni téléchargé'
}
# affichage du moteur dans le diagnostic
$script:MoteurVoix = 'faster-whisper'; Add-DiagVocal ('{"id":901,"brut":"test moteur","wake":false,"mot":"","ordre":"","etat":"ignoré","raison":"pas de mot d''éveil"}')
Verifier ((@(Get-DiagPanneau 1)[0]).moteur -eq 'faster-whisper' -and (Get-DonneesTableau).moteur_voix -eq 'faster-whisper') 'le diagnostic affiche le moteur utilisé (par phrase et en titre du panneau)'
$jv = Get-Content (Join-Path $Root 'jarvis.ps1') -Raw -Encoding UTF8
Verifier ($jv.Contains("'--moteur', `$mc.moteur") -and $jv.Contains("{ `$_ -in 'micro', 'mots' }")) 'jarvis.ps1 mots / micro transmettent le moteur configuré (comparaison possible en changeant moteur_voix)'

Remove-Item $TR -Recurse -Force -ErrorAction SilentlyContinue
if ($echecs) { Write-Host "`nÉCHEC : $echecs vérification(s) en échec." -ForegroundColor Red; exit 1 }
Write-Host "`nRÉUSSI"; exit 0
