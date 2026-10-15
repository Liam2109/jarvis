# TEST MANUEL du ton majordome / bureau — à lancer VOUS-MÊME (via tests\manuels.ps1 -Oui), jamais par Claude ni par tests\tout.ps1.
# Il ouvre de VRAIES fenêtres (un Bloc-notes qu'il referme lui-même), déplace ce Bloc-notes, lit puis restaure le presse-papiers, et essaie
# « remets mon bureau comme avant » sur une disposition à une seule fenêtre (écrite dans un dossier temporaire, jamais dans votre memoire\).
# Il ne touche ni au volume, ni à la musique, ni au micro, ni à Ollama, ni à Claude Code. Pendant qu'il tourne : ne cliquez pas dans d'autres fenêtres.
$ErrorActionPreference = 'Stop'
Remove-Item Env:JARVIS_TEST -ErrorAction SilentlyContinue
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $Root 'lib\journal.ps1')
$TR = Join-Path $env:TEMP ('jarvis-test-' + [guid]::NewGuid().ToString('N').Substring(0, 8)); New-Item -ItemType Directory $TR, "$TR\memoire", "$TR\logs" | Out-Null; $script:JarvisRoot = $TR
$Config = Get-Content (Join-Path $Root 'config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($l in 'voix', 'business', 'permissions', 'actions', 'coffre', 'entrees', 'ecrans', 'tableau', 'visage', 'sons', 'raccourcis', 'cerveau', 'cerveau-local', 'veille', 'memoire', 'rapide', 'discretion', 'modejeu', 'marche', 'priorite', 'comprehension', 'pc', 'bureau', 'matin', 'boucle') { . (Join-Path $Root "lib\$l.ps1") }
$script:JarvisRoot = $TR
$echecs = 0
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }
function Parler([string]$Texte, $Langue) { }      # (aucune voix)
function Proche($a, $b, [int]$tol = 40) { [math]::Abs([int]$a - [int]$b) -le $tol }
$np = $null
try {
    Write-Host '1) Bloc-notes réel : lire et déplacer une fenêtre'
    $np = Start-Process notepad.exe -PassThru
    $fin = (Get-Date).AddSeconds(10); while (-not $np.MainWindowHandle -and (Get-Date) -lt $fin) { Start-Sleep -Milliseconds 200; $np.Refresh() }
    Verifier ([bool]$np.MainWindowHandle) 'le Bloc-notes a une fenêtre'
    $f = @{ hwnd = [int64]$np.MainWindowHandle; pid = $np.Id; proc = 'notepad'; titre = 'Bloc-notes' }
    Verifier ($null -ne (Get-FenetresPc | Where-Object { $_.pid -eq $np.Id })) 'Get-FenetresPc voit la fenêtre (et seulement les fenêtres non protégées)'
    Set-FenetreEtat $f 'rect' @{ X = 200; Y = 150; Width = 640; Height = 420; Etat = 0 }; Start-Sleep -Milliseconds 400
    $r = @(Get-RectFenetre $f)
    Verifier ((Proche $r[0] 200) -and (Proche $r[1] 150) -and (Proche $r[2] 640) -and (Proche $r[3] 420) -and $r[4] -eq 0) "position relue : x=$($r[0]) y=$($r[1]) l=$($r[2]) h=$($r[3]) (attendu 200, 150, 640, 420)"

    Write-Host '2) « remets mon bureau comme avant » (une seule fenêtre) : application fermée, rouverte, replacée'
    [void]$np.CloseMainWindow(); [void]$np.WaitForExit(5000); Start-Sleep -Milliseconds 500
    [pscustomobject]@{ date = (Get-Date).ToString('yyyy-MM-dd HH:mm'); fenetres = @([pscustomobject]@{ proc = 'notepad'; x = 200; y = 150; w = 640; h = 420; etat = 0 }) } | ConvertTo-Json -Depth 4 | Set-Content (Get-FichierDisposition) -Encoding UTF8
    $res = & $script:Actions['disposition_restaurer'].run ([pscustomobject]@{ type = 'disposition_restaurer' })
    Verifier ($res.ok -and (Test-PhrasePolitesse 'fait_action' $res.texte)) "réponse polie : « $($res.texte) »"
    Start-Sleep -Milliseconds 600
    $f2 = @(Get-FenetresPc | Where-Object { $_.proc -eq 'notepad' })[0]
    Verifier ($null -ne $f2) 'le Bloc-notes a été rouvert'
    if ($f2) { $r = @(Get-RectFenetre $f2); Verifier ((Proche $r[0] 200) -and (Proche $r[1] 150)) "et replacé : x=$($r[0]) y=$($r[1]) (attendu 200, 150)"; $np = Get-Process -Id $f2.pid -ErrorAction SilentlyContinue }

    Write-Host '3) Presse-papiers réel (restauré ensuite)'
    $avant = try { Get-Clipboard -Raw } catch { $null }
    try {
        Set-Clipboard -Value 'Réunion jeudi à 14 h avec le comptable.'
        Verifier ((Get-PressePapiers) -match 'comptable' -and -not (Test-ContenuSensible (Get-PressePapiers))) 'lecture du presse-papiers ; contenu ordinaire = pas sensible'
        Set-Clipboard -Value 'mot de passe : hunter2'
        Verifier (Test-ContenuSensible (Get-PressePapiers)) 'contenu sensible détecté (il faudrait votre « oui » avant tout envoi)'
    } finally { if ($null -ne $avant) { Set-Clipboard -Value $avant } else { Set-Clipboard -Value ' ' } }
} finally {
    if ($np) { try { [void]$np.CloseMainWindow(); if (-not $np.WaitForExit(3000)) { $np.Kill() } } catch {} }
    Remove-Item $TR -Recurse -Force -ErrorAction SilentlyContinue
}
Write-Host ''
Write-Host 'À vérifier AUSSI à la voix, Jarvis lancé par vous (rien de tout cela n''est automatisé) :' -ForegroundColor Cyan
@('« Jarvis, ouvre Chrome » puis « ferme Chrome » : phrase courte et courtoise, jamais deux fois la même d''affilée',
  '« Jarvis, mets le PC en veille » : UNE question (« Souhaitez-vous vraiment… »), répondre « vas-y » (ou « non » / se taire 8 s : annulation polie) — attention : « vas-y » met vraiment le PC en veille',
  '« Jarvis, volume à 30 pour cent », « pause » : aucune formule polie',
  '« Jarvis, enregistre cette disposition » puis déplacez des fenêtres, puis « Jarvis, remets mon bureau comme avant » (confirmation, puis fenêtres replacées)',
  '« Jarvis, mode nuit » / « mode travail » / « mode détente » : volume, musique, luminosité, applications du mode',
  '« Jarvis, mets un minuteur de 2 minutes » : annonce polie à l''échéance (ajoutez "rappel" à voix_autorisees pour l''entendre)',
  '« Jarvis, résume mon presse-papiers » (copiez un texte ordinaire), puis avec un texte contenant « mot de passe » : il doit demander votre accord',
  '« Jarvis, demande à Claude Code de lister les fichiers » : la demande est relue, « oui » -> noté dans memoire\claude-code-demandes.md (essai à blanc)',
  '« Jarvis, qu''est-ce que tu peux faire ? » puis « la suite » : 5 capacités à la fois',
  'Dans config.json : "ton_majordome": "neutre" puis "sec" (relancer Jarvis) : le ton change',
  'FIN DE PHRASE : dites « Jarvis, ouvre Chrome » (réaction vive, ~0,6 s), puis une phrase longue avec des pauses d''une seconde (« Jarvis, rappelle-moi ... euh ... demain à neuf heures ... de ... appeler le comptable ») : elle ne doit PAS être coupée ; regardez « fin de phrase N ms » dans le diagnostic vocal',
  'VITESSE : après Alt + + attendez ~5 s, dites une commande reformulée (« tu peux monter un petit peu le son ») : le diagnostic doit afficher « étage routeur » et « routeur : ok en N ms » (pas de Claude) ; une question ouverte (« pourquoi le ciel est bleu ») doit afficher « routeur : conversation » puis « étage claude »',
  'VOIX : toutes les réponses sont à la voix d''HOMME (Henri). Si elle bascule, le journal doit dire « repli Piper (tom) » (jamais Hortense) ; essayez "voix_moteur": "piper" puis "voix_piper": "siwis" pour comparer') | ForEach-Object { Write-Host "  - $_" }
if ($echecs) { Write-Host "`n$echecs échec(s)." -ForegroundColor Red; exit 1 }
Write-Host "`nTOUT EST VERT." -ForegroundColor Green; exit 0
