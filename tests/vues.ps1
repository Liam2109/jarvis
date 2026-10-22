# Test SILENCIEUX des vues (lib\vues.ps1, visage\vues\, canal d'événements de lib\visage.ps1, panneau conversation de visage\index.html) : manifestes VUE.md, analyse du JS, fichiers servis, événements show_view / hide_view / view_command, routage, capacités.
# AUCUN navigateur, aucune fenêtre, aucun serveur : l'ouverture et la fermeture sont simulées par événements. Si node est présent : node --check sur tout le JS et un essai de la vue « horloge » sur un faux DOM (sinon : test sauté et signalé).
# Mémoire, config et dossiers TEMPORAIRES. Code de sortie 0 = réussi.
$ErrorActionPreference = 'Stop'
$env:JARVIS_TEST = '1'
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $Root 'lib\journal.ps1')
$TR = Join-Path $env:TEMP ('jarvis-test-' + [guid]::NewGuid().ToString('N').Substring(0, 8)); New-Item -ItemType Directory $TR, "$TR\memoire", "$TR\logs", "$TR\tmp", "$TR\visage\lib" | Out-Null; $script:JarvisRoot = $TR
'# To-do' | Set-Content "$TR\memoire\todo.md" -Encoding UTF8; '# N' | Set-Content "$TR\memoire\notes.md" -Encoding UTF8; '# R' | Set-Content "$TR\memoire\resume.md" -Encoding UTF8
Copy-Item (Join-Path $Root 'visage\vues') "$TR\visage\vues" -Recurse; Copy-Item (Join-Path $Root 'visage\lib\three') "$TR\visage\lib\three" -Recurse
$Config = Get-Content $(if ($env:JARVIS_CONFIG -and (Test-Path $env:JARVIS_CONFIG)) { $env:JARVIS_CONFIG } else { Join-Path $Root 'config.json' }) -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($l in 'voix', 'business', 'permissions', 'actions', 'coffre', 'entrees', 'ecrans', 'tableau', 'visage', 'sons', 'raccourcis', 'cerveau', 'cerveau-local', 'veille', 'memoire', 'rapide', 'discretion', 'modejeu', 'competences', 'marche', 'priorite', 'comprehension', 'routeur', 'pc', 'bureau', 'salle-marche', 'matin', 'discord', 'veille-train', 'veille-mail', 'candidatures', 'initiatives', 'lecons', 'skills', 'presets', 'vues') { . (Join-Path $Root "lib\$l.ps1") }
$script:JarvisRoot = $TR; $script:PolitesseFixe = $true
$echecs = 0
function Verifier([bool]$cond, [string]$msg) { if ($cond) { Write-Host "  OK    $msg" } else { Write-Host "  ECHEC $msg" -ForegroundColor Red; $script:echecs++ } }
function Fixer([string]$cle, $val) { if ($Config.PSObject.Properties[$cle]) { $Config.$cle = $val } else { $Config | Add-Member -NotePropertyName $cle -NotePropertyValue $val } }
function Journal { $f = Join-Path $TR ('logs\journal-{0}.md' -f (Get-Date -Format 'yyyy-MM-dd')); if (Test-Path $f) { Get-Content $f -Raw -Encoding UTF8 } else { '' } }
function Reset-Vues { $script:VuesEvt.Clear(); $script:VuesSeq = 0; $script:VueActive = $null }
function Variante([string]$id, [string]$js = $null, [scriptblock]$vueMd = $null) {
    # Copie la vue « horloge » dans un dossier de test et change son JS ou son VUE.md.
    $d = Join-Path $TR "visage\vues\$id"; if (Test-Path $d) { Remove-Item $d -Recurse -Force }
    Copy-Item "$TR\visage\vues\horloge" $d -Recurse
    $md = (Get-Content "$d\VUE.md" -Raw -Encoding UTF8) -replace '(?m)^id: horloge', "id: $id"
    if ($vueMd) { $md = & $vueMd $md }
    [IO.File]::WriteAllText("$d\VUE.md", $md, [Text.UTF8Encoding]::new($false))
    if ($js) { [IO.File]::WriteAllText("$d\vue.js", $js, [Text.UTF8Encoding]::new($false)) }
    Test-VueManifeste $id
}
function Cmd([string]$texte) {
    $script:DiscordTampon = New-Object System.Collections.Generic.List[string]; $script:DiscordEmbeds.Clear(); $script:CanalDiscord = 'jarvis'
    $r = Invoke-CommandeDiscord $texte
    @{ traite = $r; tampon = ($script:DiscordTampon -join ' '); embeds = @($script:DiscordEmbeds) }
}
$hashConfig = (Get-FileHash (Join-Path $Root 'config.json')).Hash
$vraie = Get-Content (Join-Path $Root 'config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$node = Get-Command node -ErrorAction SilentlyContinue
$jsBon = Get-Content "$TR\visage\vues\horloge\vue.js" -Raw -Encoding UTF8

# ---------- Réglage ----------
$sauve = $Config; $Config = [pscustomobject]@{}
Verifier (-not (Get-VuesConfig).actif) 'sans réglage : vues désactivées'
$Config = $sauve
Verifier ($vraie.vues_actif -eq 'non' -and $vraie.presets_actif -eq 'non') 'config.json : vues_actif et presets_actif = "non"'

# ---------- Manifestes livrés ----------
$hor = Test-VueManifeste 'horloge'; $mon = Test-VueManifeste 'monument-3d'
Verifier ($hor.ok -and $mon.ok) "les deux vues livrées passent la validation$(if (-not $hor.ok) { ' (horloge : ' + ($hor.motifs -join ' ; ') + ')' })$(if (-not $mon.ok) { ' (monument-3d : ' + ($mon.motifs -join ' ; ') + ')' })"
Verifier ($mon.vue.nom -eq 'Monuments 3D' -and $mon.vue.version -eq '1.0.0' -and @($mon.vue.commandes).Count -eq 3 -and (@($mon.vue.declencheurs | Where-Object { $_.phrase -eq 'tour eiffel' -and $_.params.monument -eq 'eiffel' }).Count -ge 1)) 'VUE.md lu : id, nom, version, description, commandes, déclencheurs avec paramètres (« tour eiffel => monument=eiffel »)'
$fm = ConvertFrom-VueFrontMatter "---`nid: x`nnom: 'Un nom'`nliste:`n  - a`n  - `"b c`"`n---`ncorps"
Verifier ($fm.ok -and $fm.meta.nom -eq 'Un nom' -and @($fm.meta.liste).Count -eq 2 -and $fm.meta.liste[1] -eq 'b c' -and -not (ConvertFrom-VueFrontMatter 'pas de front-matter').ok -and -not (ConvertFrom-VueFrontMatter "---`nligne sans deux-points`n---").ok) 'analyse du front-matter YAML (scalaires, listes, guillemets) et refus d''un fichier sans front-matter ou mal formé'
Verifier ((@(Get-Vues).Count -eq 2) -and (Get-VueParNom 'Monuments 3D').id -eq 'monument-3d' -and (Get-VueParNom 'horloge').id -eq 'horloge' -and -not (Get-VueParNom 'inconnue')) 'liste des vues et recherche par nom ou identifiant'

# ---------- Refus d'un manifeste ou d'un JS non conforme ----------
$cas = @(
    @('Sans VUE.md', { Remove-Item "$TR\visage\vues\horloge2" -Recurse -Force -ErrorAction SilentlyContinue; Copy-Item "$TR\visage\vues\horloge" "$TR\visage\vues\horloge2" -Recurse; Remove-Item "$TR\visage\vues\horloge2\VUE.md"; Test-VueManifeste 'horloge2' }, 'VUE.md absent'),
    @('id différent du dossier', { Variante 'horloge3' $null { param($m) $m -replace '(?m)^id: horloge3', 'id: autre' } }, 'différent du dossier'),
    @('version invalide', { Variante 'horloge4' $null { param($m) $m -replace '(?m)^version: .*', 'version: 1' } }, 'version'),
    @('sans commandes', { Variante 'horloge5' $null { param($m) $m -replace '(?s)commandes:.*?(?=---)', '' } }, 'commandes'),
    @('sans déclencheurs', { Variante 'horloge6' $null { param($m) $m -replace '(?s)declencheurs:.*?(?=commandes:)', '' } }, 'déclencheur'),
    @('paramètre de déclencheur invalide', { Variante 'horloge7' $null { param($m) $m -replace '"horloge"', '"horloge => x=a b;c"' } }, 'paramètre invalide'),
    @('eval', { Variante 'vue-eval' ($jsBon + "`nexport const x = () => eval('1');") }, 'eval'),
    @('new Function', { Variante 'vue-fn' ($jsBon + "`nexport const y = new Function('return 1');") }, 'eval ou Function'),
    @('fetch', { Variante 'vue-fetch' ($jsBon + "`nexport const z = () => fetch('/x');") }, 'réseau'),
    @('XMLHttpRequest', { Variante 'vue-xhr' ($jsBon + "`nexport const z = () => new XMLHttpRequest();") }, 'réseau'),
    @('WebSocket', { Variante 'vue-ws' ($jsBon + "`nexport const z = () => new WebSocket('x');") }, 'réseau'),
    @('adresse externe', { Variante 'vue-url' ($jsBon + "`nexport const u = 'https://exemple.test/x.js';") }, 'adresse externe'),
    @('import dynamique', { Variante 'vue-dyn' ($jsBon + "`nexport const d = () => import('./x.js');") }, 'import dynamique'),
    @('import hors liste (CDN ou paquet)', { Variante 'vue-imp' ("import * as L from 'lodash';`n" + $jsBon) }, 'import non permis'),
    @('import d''un fichier absent', { Variante 'vue-imp2' ("import { a } from './absent.js';`n" + $jsBon) }, 'import non permis'),
    @('lit memoire', { Variante 'vue-mem' ($jsBon + "`nexport const m = 'memoire/todo.md';") }, 'memoire'),
    @('lit la config', { Variante 'vue-cfg' ($jsBon + "`nexport const c = 'config.json';") }, 'config'),
    @('lit les données de Jarvis', { Variante 'vue-don' ($jsBon + "`nexport const c = '/donnees';") }, 'memoire|config'),
    @('stockage et cookie', { Variante 'vue-sto' ($jsBon + "`nexport const s = () => localStorage.getItem('a') + document.cookie;") }, 'stockage'),
    @('minuteur sans clearInterval', { Variante 'vue-int' ($jsBon -replace 'clearInterval\(minuteur\);', '') }, 'clearInterval'),
    @('animation sans cancelAnimationFrame', { Variante 'vue-raf' ($jsBon + "`nexport const r = () => requestAnimationFrame(() => 0);") }, 'cancelAnimationFrame'),
    @('écouteur jamais retiré', { Variante 'vue-ecou' ($jsBon + "`nexport const e = () => window.addEventListener('resize', () => 0);") }, 'removeEventListener'),
    @('racine pas en position fixed', { Variante 'vue-nofix' ($jsBon -replace 'position:fixed', 'position:absolute') }, 'position fixed'),
    @('sans export default', { Variante 'vue-noexp' ($jsBon -replace 'export default', 'const defaut =') }, 'export default'),
    @('hide() sans nettoyage du DOM', { Variante 'vue-nodom' ($jsBon -replace 'racine\.remove\(\);', '') }, 'hide\(\)|DOM'),
    @('méthode command absente', { Variante 'vue-nocmd' ($jsBon -replace 'command\(cmd, params\)', 'autre(cmd, params)') }, 'command'))
$rate = @()
foreach ($c in $cas) { $r = & $c[1]; if ($r.ok -or ($r.motifs -join ' | ') -notmatch $c[2]) { $rate += "$($c[0]) -> " + $(if ($r.ok) { 'ACCEPTÉ' } else { $r.motifs -join ' | ' }) } }
Verifier ($rate.Count -eq 0) "refus de chacun des $($cas.Count) cas non conformes (manifeste, eval, réseau, adresse externe, import, memoire, config, stockage, nettoyage, position fixed...)$(if ($rate.Count) { ' ; non conformes : ' + ($rate -join ' || ') })"
Verifier ((Variante 'vue-ok' $jsBon).ok) 'la même vue sans défaut est acceptée'
Remove-Item "$TR\visage\vues\horloge2", "$TR\visage\vues\horloge3", "$TR\visage\vues\horloge4", "$TR\visage\vues\horloge5", "$TR\visage\vues\horloge6", "$TR\visage\vues\horloge7" -Recurse -Force -ErrorAction SilentlyContinue

# ---------- Fichiers servis (liste blanche) ----------
Fixer 'vues_actif' 'non'
Verifier ($null -eq (Get-FichierVueHttp '/vues/horloge/vue.js') -and $null -eq (Get-FichierVueHttp '/lib/three/build/three.module.min.js')) 'vues désactivées : aucun fichier de vue ni de three.js n''est servi'
Fixer 'vues_actif' 'oui'
$f1 = Get-FichierVueHttp '/vues/horloge/vue.js'; $f2 = Get-FichierVueHttp '/vues/monument-3d/monuments/eiffel.js'; $f3 = Get-FichierVueHttp '/lib/three/build/three.module.min.js'; $f4 = Get-FichierVueHttp '/lib/three/examples/jsm/controls/OrbitControls.js'
Verifier ($f1 -and $f1.type -match 'javascript' -and $f1.corps -match 'export default' -and $f2 -and $f2.corps -match 'Tour Eiffel' -and $f3 -and $f3.corps -match 'Three.js Authors' -and $f4 -and $f4.corps -match 'OrbitControls') 'servis : vue.js, monuments\eiffel.js, three.module.min.js et OrbitControls.js locaux'
$refuses = '/vues/horloge/VUE.md', '/vues/horloge/../../memoire/todo.md', '/vues/../config.json', '/vues/horloge/..%2f..%2fconfig.json', '/vues/vue-eval/vue.js', '/vues/inconnue/vue.js', '/lib/three/LICENSE', '/lib/three/../../config.json', '/lib/three/build/../../../config.json', '/vues/horloge/Vue.JS', '/vues/Horloge/vue.js', '/vues/horloge/sous/../vue.js'
$serv = @($refuses | Where-Object { Get-FichierVueHttp $_ })
Verifier ($serv.Count -eq 0) "refusés ($($refuses.Count) chemins : VUE.md, traversée .., config, memoire, vue invalide, vue inconnue, three hors liste)$(if ($serv.Count) { ' ; SERVIS À TORT : ' + ($serv -join ' | ') })"
$vp = Get-Content (Join-Path $Root 'lib\visage.ps1') -Raw -Encoding UTF8
Verifier ($vp.Contains("`$chemin -like '/vues/*' -or `$chemin -like '/lib/three/*'") -and $vp.Contains("'/vue'     { if (Get-Command Receive-VueEtat") -and $vp.Contains('Get-VuesEtatHttp') -and $vp.IndexOf("`$hoteOk") -lt $vp.IndexOf("`$chemin -like '/vues/*'")) 'lib\visage.ps1 : routes /vues et /lib/three (après les contrôles d''hôte et d''origine), POST /vue et événements dans /etat'
Remove-Item "$TR\visage\vues\vue-*" -Recurse -Force -ErrorAction SilentlyContinue

# ---------- Événements : ouverture, commande, fermeture ----------
Reset-Vues; Fixer 'vues_actif' 'non'
$r = Show-VueParNom 'horloge'
Verifier (-not $r.ok -and $r.texte -match 'désactivées' -and $script:VuesSeq -eq 0) 'désactivé : aucun événement'
Fixer 'vues_actif' 'oui'
$r = Show-VueParNom 'la tour eiffel'
$e = Get-VuesEtatHttp
Verifier ($r.ok -and $e.vue_seq -eq 1 -and $e.vue_events[0].type -eq 'show_view' -and $e.vue_events[0].id -eq 'monument-3d' -and $e.vue_events[0].params.monument -eq 'eiffel' -and $e.vue_active.id -eq 'monument-3d') '« la tour eiffel » : événement show_view (vue monument-3d, monument = eiffel) et vue active'
$json = ($e | ConvertTo-Json -Depth 6 -Compress) | ConvertFrom-Json
Verifier ($json.vue_seq -eq 1 -and $json.vue_events[0].type -eq 'show_view' -and $json.vue_active.params.monument -eq 'eiffel') 'les événements se sérialisent dans la réponse /etat'
$r = Send-VueCommande 'rotation' @{ actif = $true }
Verifier ($r.ok -and $script:VuesEvt[-1].type -eq 'view_command' -and $script:VuesEvt[-1].cmd -eq 'rotation' -and $script:VuesEvt[-1].params.actif -eq $true -and $script:VuesSeq -eq 2) 'événement view_command'
$r = Close-Vue
Verifier ($r.ok -and $script:VuesEvt[-1].type -eq 'hide_view' -and $null -eq $script:VueActive -and $script:VuesSeq -eq 3) 'événement hide_view : plus de vue active'
Verifier ((Close-Vue).texte -match 'Aucune vue' -and $script:VuesSeq -eq 3 -and -not (Send-VueCommande 'x').ok) 'fermer ou commander sans vue ouverte : rien envoyé'
[void](Show-VueParNom 'horloge'); Receive-VueEtat ([pscustomobject]@{ etat = 'fermee'; id = 'horloge' })
Verifier ($null -eq $script:VueActive -and (Journal) -match 'horloge : fermee') 'la page signale une fermeture (Échap, bouton Fermer) : état resynchronisé, journalisé'
[void](Show-VueParNom 'horloge'); Receive-VueEtat ([pscustomobject]@{ etat = 'erreur'; id = 'horloge'; message = 'boum' }); Receive-VueEtat ([pscustomobject]@{ etat = 'fermee'; id = '../x' })
Verifier ($null -eq $script:VueActive -and (Journal) -match 'Vue : erreur') 'une erreur de la page est journalisée ; un identifiant invalide est ignoré'
1..14 | ForEach-Object { [void](Show-VueParNom 'horloge') }
Verifier ($script:VuesEvt.Count -eq 10 -and $script:VuesEvt[0].seq -eq ($script:VuesSeq - 9)) 'seuls les 10 derniers événements sont gardés'
Verifier ((Show-VueParNom 'vue-inconnue').ok -eq $false) 'vue inconnue : refus poli'

# ---------- Routage des commandes ----------
Reset-Vues
$c = Invoke-VuesCommande 'vues'
Verifier ($c.traite -and $c.embed.titre -eq 'Vues' -and $c.embed.couleur -eq $script:CouleurBleue -and ($c.embed.champs | ForEach-Object { $_.nom }) -join ' ' -match 'Monuments 3D' -and ($c.embed.champs | ForEach-Object { $_.valeur }) -join ' ' -match 'montre tour eiffel') 'commande « vues » : embed bleu avec les vues et leur phrase'
$paires = @(@('montre la vue horloge', 'horloge'), @('Montre-moi la vue Monuments 3D', 'monument-3d'), @('Jarvis, montre la tour Eiffel !', 'monument-3d'), @('montre l''horloge', 'horloge'), @('affiche la dame de fer', 'monument-3d'), @('ouvre l''horloge', 'horloge'))
$mal = @(); foreach ($p in $paires) { Reset-Vues; $r = Invoke-VuesCommande $p[0]; if (-not ($r -and $r.traite -and $script:VueActive.id -eq $p[1])) { $mal += $p[0] } }
Verifier ($mal.Count -eq 0) "ouvrir une vue : $($paires.Count) formulations routées vers la bonne vue$(if ($mal.Count) { ' ; ratées : ' + ($mal -join ' | ') })"
Reset-Vues; [void](Invoke-VuesCommande 'montre la tour eiffel')
$r = Invoke-VuesCommande 'ferme la vue'
Verifier ($r.traite -and $null -eq $script:VueActive -and $script:VuesEvt[-1].type -eq 'hide_view' -and (Invoke-VuesCommande 'ferme les vues').traite) 'commande « ferme la vue »'
Verifier ($null -eq (Invoke-VuesCommande 'ouvre chrome') -and $null -eq (Invoke-VuesCommande 'montre le ciel') -and $null -eq (Invoke-VuesCommande 'ferme chrome') -and $null -eq (Invoke-VuesCommande 'quelle heure est-il')) 'les autres ordres ne sont pas pris pour des commandes de vue'
Fixer 'vues_actif' 'non'; Reset-Vues
Verifier ((Invoke-VuesCommande 'vues').texte -match 'désactivées' -and (Invoke-VuesCommande 'montre la vue horloge').texte -match 'désactivées' -and $null -eq (Invoke-VuesCommande 'ferme la vue') -and $null -eq (Invoke-VuesCommande 'montre la tour eiffel') -and $script:VuesSeq -eq 0) 'désactivé : message poli, aucun événement ; « ferme la vue » et « montre la tour eiffel » ne sont pas interceptés'
Fixer 'vues_actif' 'oui'
$a = $script:Actions['vue_montrer']; $b = $script:Actions['vue_fermer']
Reset-Vues; $rr = & ($a.run) ([pscustomobject]@{ nom = 'horloge' })
Verifier ($a -and $b -and (Get-Niveau ([pscustomobject]@{ type = 'vue_montrer' })).niveau -eq 1 -and (Get-Niveau ([pscustomobject]@{ type = 'vue_fermer' })).niveau -eq 1 -and $rr.ok -and $script:VueActive.id -eq 'horloge') 'actions vue_montrer / vue_fermer classées au niveau 1 par les permissions ; utilisables par un preset'
# Discord et voix
Reset-Vues
$x = Cmd 'montre la tour Eiffel'
Verifier ($x.traite -and $script:VueActive.id -eq 'monument-3d' -and $x.tampon -match 'Voici la vue') 'Discord : « montre la tour Eiffel » ouvre la vue'
$x = Cmd 'ferme la vue'
Verifier ($x.traite -and $null -eq $script:VueActive) 'Discord : « ferme la vue »'
$x = Cmd 'vues'
Verifier ($x.traite -and $x.embeds.Count -eq 1 -and $x.embeds[0].titre -eq 'Vues') 'Discord : « vues » répond par un embed'
$cv = Get-Content (Join-Path $Root 'lib\cerveau.ps1') -Raw -Encoding UTF8; $dc = Get-Content (Join-Path $Root 'lib\discord.ps1') -Raw -Encoding UTF8
Verifier ($cv -match 'Invoke-ExtensionsOrdre \$ordre' -and $dc -match 'Invoke-ExtensionsOrdre \$texte') 'la voix (Invoke-OrdreCorps) et Discord passent par la même entrée Invoke-ExtensionsOrdre'

# ---------- Capacités ----------
$d = Get-CapacitesDonnees
Verifier ($d.vues.Count -eq 2 -and $d.skills -is [array] -and $d.presets -is [array] -and $d.vues_actif -eq $true) 'données des capacités : skills, presets et vues'
$cap = Invoke-ExtensionsOrdre 'capacités'
Verifier ($cap.embed.titre -eq 'Capacités' -and @($cap.embed.champs).Count -eq 3 -and ($cap.embed.champs | ForEach-Object { $_.nom }) -join ' ' -match 'Skills.*Presets.*Vues' -and $cap.embed.couleur -eq $script:CouleurBleue) '« capacités » : un seul embed avec skills, presets et vues'
Fixer 'vues_actif' 'non'; Fixer 'presets_actif' 'non'
Verifier ($null -eq (Invoke-ExtensionsOrdre 'capacités')) 'ni presets ni vues activés : la commande « capacités » d''origine reste seule'
Fixer 'vues_actif' 'oui'
Verifier ($null -eq (Invoke-ExtensionsOrdre 'ouvre chrome')) 'un ordre ordinaire n''est jamais intercepté'

# ---------- Interface : fichiers livrés ----------
$idx = Get-Content (Join-Path $Root 'visage\index.html') -Raw -Encoding UTF8
Verifier ($idx -match 'type="importmap"' -and $idx -match '"three": "/lib/three/build/three\.module\.min\.js"' -and $idx -notmatch '(?i)(src|href)\s*=\s*"https?://' -and $idx -notmatch '(?i)cdn|unpkg|jsdelivr') 'index.html : import map LOCALE pour three, aucun CDN'
Verifier ($idx -match 'show_view' -and $idx -match 'hide_view' -and $idx -match 'view_command' -and $idx -match 'jarvis-vue-fermer' -and $idx -match 'vue_events' -and $idx -match 'poster\("/vue"') 'index.html : la page traite show_view / hide_view / view_command et répond par POST /vue'
Verifier ($idx -match 'if \(!vueFermer\(false\)\) poster\("/reduire"\)') 'Échap ferme d''abord la vue, sinon réduit la fenêtre comme avant'
Verifier ($idx -match 'id="btn-conv"' -and $idx -match 'id="soustitres"' -and $idx -match 'basculerConv' -and $idx -match 'body\.conv-ferme #p-conv' -and $idx -match 'majSousTitres') 'panneau conversation : bouton, touche C, sous-titres propres par-dessus une vue (le panneau d''origine est conservé)'
Verifier ($idx -match 'id="p-conv"') 'le panneau conversation d''origine est conservé (aucune refonte)'
$lic = Get-Content "$Root\visage\lib\three\LICENSE" -Raw -Encoding UTF8; $lm = Get-Content "$Root\visage\lib\three\LISEZMOI.md" -Raw -Encoding UTF8; $min = Get-Content "$Root\visage\lib\three\build\three.module.min.js" -TotalCount 5 -Encoding UTF8
Verifier ($lic -match 'MIT License' -and $lm -match '0\.160\.0' -and $lm -match 'MIT' -and ($min -join ' ') -match 'MIT' -and (Test-Path "$Root\visage\lib\three\examples\jsm\controls\OrbitControls.js")) 'three.js 0.160.0 en copie locale : licence MIT, version notée, OrbitControls local'
$eif = Get-Content "$Root\visage\vues\monument-3d\monuments\eiffel.js" -Raw -Encoding UTF8; $reg = Get-Content "$Root\visage\vues\monument-3d\monuments\index.js" -Raw -Encoding UTF8; $mv = Get-Content "$Root\visage\vues\monument-3d\vue.js" -Raw -Encoding UTF8
Verifier ($eif -match 'BufferGeometry' -and $eif -match 'TorusGeometry' -and $eif -notmatch '(?i)GLTF|OBJLoader|FBXLoader|TextureLoader|\.glb|\.gltf|\.obj\b' -and $reg -match 'MONUMENTS' -and $reg -match 'eiffel' -and $mv -match 'OrbitControls' -and $mv -match '0x04070c') 'monument-3d : Eiffel en géométrie procédurale (aucun modèle chargé), registre de monuments, OrbitControls, fond sombre du visage'
Verifier ((Get-ChildItem "$Root\visage\vues" -Recurse -File | ForEach-Object { Get-Content $_.FullName -Raw -Encoding UTF8 } | Out-String) -notmatch '(?i)cdn\.|unpkg|jsdelivr|cdnjs') 'aucune référence à un CDN dans les vues'

# ---------- JS : node --check et essai sur faux DOM (si node est présent) ----------
if ($node) {
    $jsFiles = @(Get-ChildItem "$Root\visage\vues" -Filter *.js -Recurse -File)
    $mauvais = @(); foreach ($f in $jsFiles) { $cp = Join-Path $TR ('tmp\chk-' + [guid]::NewGuid().ToString('N').Substring(0, 6) + '.mjs'); Copy-Item $f.FullName $cp; & node --check $cp 2>&1 | Out-Null; if ($LASTEXITCODE -ne 0) { $mauvais += $f.Name } }
    Verifier ($mauvais.Count -eq 0 -and $jsFiles.Count -ge 4) "node --check : $($jsFiles.Count) fichiers JS de vues sans erreur de syntaxe$(if ($mauvais.Count) { ' ; erreurs : ' + ($mauvais -join ', ') })"
    $pg = Join-Path $TR 'tmp\page.js'; $mod = [regex]::Matches($idx, '(?s)<script(?![^>]*type="importmap")[^>]*>(.*?)</script>'); [IO.File]::WriteAllText($pg, (($mod | ForEach-Object { $_.Groups[1].Value }) -join "`n"), [Text.UTF8Encoding]::new($false))
    & node --check $pg 2>&1 | Out-Null
    Verifier ($LASTEXITCODE -eq 0 -and $mod.Count -eq 1) 'node --check : le script de visage\index.html (avec les vues et la conversation) est valide'
    Copy-Item "$Root\visage\vues\horloge\vue.js" "$TR\tmp\vue-horloge.mjs"
    $essai = @'
const minuteurs = new Map(); let nid = 1;
globalThis.setInterval = (f) => { const id = nid++; minuteurs.set(id, f); return id; };
globalThis.clearInterval = (id) => { minuteurs.delete(id); };
const body = { children: [], appendChild(e) { this.children.push(e); e.parent = this; return e; } };
function el(tag) { return { tag, style: {}, children: [], className: '', id: '', textContent: '', parent: null,
  append(...k) { k.forEach((x) => { this.children.push(x); x.parent = this; }); },
  appendChild(x) { this.children.push(x); x.parent = this; return x; },
  remove() { if (this.parent) { this.parent.children = this.parent.children.filter((c) => c !== this); this.parent = null; } },
  querySelector(sel) { const c = sel.slice(1); const rec = (n) => { for (const k of n.children) { if (k.className === c) return k; const r = rec(k); if (r) return r; } return null; }; return rec(this); } }; }
globalThis.document = { body, createElement: el };
const { pathToFileURL } = await import('node:url');
const m = (await import(pathToFileURL(process.argv[2]).href)).default;
m.show({}); m.show({});
const out = { racines: body.children.length, minuteurs: minuteurs.size, fixed: /position:fixed/.test(body.children[0].style.cssText), heure: body.children[0].querySelector('.h').textContent.length > 0 };
m.command('secondes', { actif: false }); out.sansSecondes = body.children[0].querySelector('.h').textContent.split(':').length === 2;
m.hide(); out.apres = { racines: body.children.length, minuteurs: minuteurs.size };
m.hide(); m.show({}); out.reouvert = { racines: body.children.length, minuteurs: minuteurs.size }; m.hide(); out.final = { racines: body.children.length, minuteurs: minuteurs.size };
console.log(JSON.stringify(out));
'@
    [IO.File]::WriteAllText((Join-Path $TR 'tmp\essai.mjs'), $essai, [Text.UTF8Encoding]::new($false))
    $sortie = (& node (Join-Path $TR 'tmp\essai.mjs') (Join-Path $TR 'tmp\vue-horloge.mjs') 2>&1 | Out-String).Trim()
    $o = $null; try { $o = $sortie | ConvertFrom-Json } catch {}
    Verifier ($o -and $o.racines -eq 1 -and $o.minuteurs -eq 1 -and $o.fixed -and $o.heure -and $o.sansSecondes -and $o.apres.racines -eq 0 -and $o.apres.minuteurs -eq 0 -and $o.reouvert.racines -eq 1 -and $o.final.racines -eq 0 -and $o.final.minuteurs -eq 0) "vue « horloge » sur faux DOM : idempotente (une racine, un minuteur après 2 show), hide() ne laisse rien, réouverture propre$(if (-not $o) { ' — sortie : ' + $sortie })"
} else { Write-Host '  SAUTÉ node n''est pas installé : node --check et l''essai de l''horloge sur faux DOM ne sont pas faits (à refaire sur un PC avec node)' -ForegroundColor Yellow }

# ---------- Garde-fous du code ----------
$src = Get-Content (Join-Path $Root 'lib\vues.ps1') -Raw -Encoding UTF8; $srcCode = (($src -split "`n") | Where-Object { $_ -notmatch '^\s*#|^\s*@\(''' }) -join "`n"
Verifier ($srcCode -notmatch '(?i)Invoke-Claude|Invoke-Ollama|Invoke-RestMethod|Invoke-WebRequest|Start-Process\s+[-$''"a-z]|Invoke-Expression\s+\$|Set-Content|Out-File|Add-Content|WriteAllText') 'lib\vues.ps1 : aucun appel à Claude, au réseau ni à un programme, et aucune écriture de fichier'
$js = Get-Content (Join-Path $Root 'jarvis.ps1') -Raw -Encoding UTF8
Verifier ($js -match 'lib\\vues\.ps1' -and $js -match 'lib\\presets\.ps1') 'câblage : jarvis.ps1 charge les deux modules'
$oct = [IO.File]::ReadAllBytes((Join-Path $Root 'lib\vues.ps1'))
Verifier ($oct[0] -eq 0xEF -and $oct[1] -eq 0xBB -and $oct[2] -eq 0xBF) 'lib\vues.ps1 en UTF-8 avec BOM'
Verifier ((Get-Content (Join-Path $Root 'README.md') -Raw -Encoding UTF8) -match 'vues_actif') 'README : vues décrites'
Verifier ((Get-FileHash (Join-Path $Root 'config.json')).Hash -eq $hashConfig) 'config.json réel inchangé par le test'

Write-Host ''
Remove-Item $TR -Recurse -Force -ErrorAction SilentlyContinue
if ($echecs) { Write-Host "ÉCHEC : $echecs vérification(s) en échec." -ForegroundColor Red; exit 1 }
Write-Host 'TOUT EST VERT.'
