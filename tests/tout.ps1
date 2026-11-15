# Lance TOUS les tests SILENCIEUX de Jarvis et affiche un tableau final. Code de sortie 0 = tout est vert.
#   powershell -ExecutionPolicy Bypass -File tests\tout.ps1
#
# SILENCIEUX = aucun son, aucune voix, aucune musique, aucune fenêtre, aucun vol de focus, aucun changement de volume, aucune application ni site
# ouverts, aucune vraie touche, aucun accès au micro, aucun service Ollama. (JARVIS_TEST=1 neutralise ces effets dans les bibliothèques, et les
# tests utilisent des bouchons.) Les tests travaillent sur une COPIE temporaire de config.json (JARVIS_CONFIG), jamais sur votre vraie config.
# Les tests qui exigent de VRAIES fenêtres / de VRAIES touches ne sont pas ici : voir tests\manuels.ps1 (à lancer vous-même, si vous le voulez).
# Après les tests : contrôle que config.json et memoire\ n'ont pas bougé, que les fichiers temporaires sont nettoyés et qu'aucun processus
# Jarvis / orbe / écoute / Ollama ne reste.
#
# DEUX PROFILS (mêmes tests, mêmes contrôles ; le second saute seulement les séries qui ont besoin d'une voix, d'un écran, d'Edge, du GPU) :
#   - PROFIL NORMAL (PC principal, par défaut) : TOUTES les séries, TOUS les contrôles.
#   - PROFIL SERVEUR : automatique quand B2B\agents\b2b.local.json contient "serveur": true, ou avec -Serveur. Le portable serveur n'a ni micro, ni voix
#     française, ni écran à piloter, ni Edge utile : les séries qui en dépendent sont SAUTÉES (et listées « SAUTÉE » avec leur raison dans le tableau
#     et dans logs\tests-dernier.txt, jamais en silence). Le contrôle « memoire\ inchangé » est ignoré (Jarvis tourne sur le serveur et écrit sa
#     mémoire pendant les tests) ; config.json, .env et les processus restent contrôlés. -Complet force le profil normal même sur le serveur.
param([switch]$Rapide,          # (-Rapide est accepté pour compatibilité : tous les tests de cette liste sont déjà silencieux)
      [switch]$Serveur,         # force le profil serveur
      [switch]$Complet,         # force le profil normal
      [string]$FichierB2BLocal = '')   # (tests) autre b2b.local.json que le vrai
$racine = Split-Path -Parent $PSScriptRoot
$profilServeur = [bool]$Serveur
if (-not $Complet -and -not $profilServeur) {
    $fb = $(if ($FichierB2BLocal) { $FichierB2BLocal } else { Join-Path $racine 'B2B\agents\b2b.local.json' })
    if (Test-Path -LiteralPath $fb) { try { $jb = Get-Content -LiteralPath $fb -Raw -Encoding UTF8 | ConvertFrom-Json; if ($jb.PSObject.Properties['serveur'] -and "$($jb.serveur)" -match '^(?i:true|oui|1)$') { $profilServeur = $true } } catch { } }
}
$liste = @(
    @{ n = 'ecran';                       f = 'ecran.ps1' }
    @{ n = 'briefing (Supabase, Stripe)'; f = 'briefing.ps1' }
    @{ n = 'veille';                      f = 'veille.ps1' }
    @{ n = 'memoire';                     f = 'memoire.ps1' }
    @{ n = 'cerveau';                     f = 'cerveau.ps1' }
    @{ n = 'competences';                 f = 'competences.ps1' }
    @{ n = 'rapide';                      f = 'rapide.ps1' }
    @{ n = 'discretion (alertes, micro)'; f = 'discretion.ps1' }
    @{ n = 'mode jeu';                    f = 'modejeu.ps1' }
    @{ n = 'sons';                        f = 'sons.ps1' }
    @{ n = 'raccourcis + sourdine';       f = 'raccourcis.ps1' }
    @{ n = 'musique + marché + veille';   f = 'marche.ps1' }
    @{ n = 'sources + priorité + 5 à voir'; f = 'sources.ps1' }
    @{ n = 'voix : ordres + diagnostic';  f = 'voix.ps1' }
    @{ n = 'routeur + compréhension libre'; f = 'routeur.ps1' }
    @{ n = 'contrôle du PC + rapidité + GPU'; f = 'pc.ps1' }
    @{ n = 'ton majordome + bureau + modes'; f = 'politesse.ps1' }
    @{ n = 'vitesse : étages, routeur, voix'; f = 'vitesse.ps1' }
    @{ n = 'fin de phrase (silences)'; f = 'silence.ps1' }
    @{ n = 'salle de marché (lecture seule)'; f = 'salle.ps1' }
    @{ n = 'interface (Edge sans fenêtre)'; f = 'interface.ps1' }
    @{ n = 'interface salle de marché (Edge sans fenêtre)'; f = 'interface-marche.ps1' }
    @{ n = 'briefing du matin';           f = 'matin.ps1' }
    @{ n = 'sauvegarde (sans .env)';      f = 'sauvegarde.ps1' }
    @{ n = 'Discord (pont, salons, confirmations, alertes, tableaux, humour)'; f = 'discord.ps1' }
    @{ n = 'voix naturelle (texte, pauses, fin d''audio, test de voix)'; f = 'voix-naturelle.ps1' }
    @{ n = 'vitesse V3 (diagnostic, fin adaptative, action d''abord, accusé, flux)'; f = 'vitesse-v3.ps1' }
    @{ n = 'serveur 24/7 (dépôt, installateur en simulation, mise à jour auto)'; f = 'serveur.ps1' }
    @{ n = 'veille + réveil vocal / claquements (PC principal, installateur en simulation)'; f = 'bureau.ps1' }
    @{ n = 'serveur léger (aucune écoute, Ollama déchargé, français, diag-serveur)'; f = 'serveur-leger.ps1' }
    @{ n = 'vitesse ressentie (suite filtrée, bruit, Ollama chaud sur ce PC)'; f = 'suivi.ps1' }
    @{ n = 'point SaaS + briefing du matin (sources branchées seulement)'; f = 'saas.ps1' }
    @{ n = 'visites Vercel Analytics (lecture seule, faux serveur local)'; f = 'vercel.ps1' }
    @{ n = 'agent de développement du SaaS (file, branche, garde-fous, valide / refuse)'; f = 'dev-agent.ps1' }
    @{ n = 'veille annonces-train (sources simulées, base locale, cartes, erreurs, résumé)'; f = 'veille-train.ps1' }
    @{ n = 'veille e-mail annonces-train (Gmail simulé : expéditeurs, filtre, doublons, lecture seule)'; f = 'veille-mail.ps1' }
    @{ n = 'offres conducteur débutant (exclusions, employeurs, pages, carte + brouillon Gmail, rien envoyé)'; f = 'offres-debutant.ps1' }
    @{ n = 'suivi des réponses aux candidatures (règles FR/DE/EN, Ollama, Claude Haiku plafonné, fils, cartes #candidatures)'; f = 'candidatures.ps1' }
    @{ n = 'emploi conducteur (zones, allemand et tram écartés, bac+2 à vérifier, CV, lettre, brouillon prêt, relance J+7, résumé)'; f = 'emploi-conducteur.ps1' }
    @{ n = 'initiatives (création, interdits, décisions, oubli 4 jours, scan de nuit, niveaux 0-5, boucle, commandes Discord, cartes)'; f = 'initiatives.ps1' }
    @{ n = 'leçons + style de parole (création, fusion, confiance, promotion proposée, secrets refusés, « omada » -> Ollama, commandes)'; f = 'lecons.ps1' }
    @{ n = 'skills (idée sans fichier, génération simulée, contrôle statique, quarantaine, validation, refus archivé + leçon, commandes)'; f = 'skills.ps1' }
    @{ n = 'presets (étapes classées, niveaux inchangés, création sur validation, exemples à valider, commandes)'; f = 'presets.ps1' }
    @{ n = 'vues (manifestes VUE.md, analyse du JS, événements show / hide / command, routage, capacités, node --check si présent)'; f = 'vues.ps1' }
    @{ n = 'pilotage (workspace, widgets, menu : lecture sans secret, boutons = fonctions Discord, jeton et hôte, échappement, node --check)'; f = 'pilotage.ps1' }
    @{ n = 'option voix_actif (désactivée par défaut : aucun micro, aucun réveil ; activée : comportement actuel)'; f = 'voix-actif.ps1' }
    @{ n = 'claude chaud (Invoke-Claude : démarrage unique, repli, arrêt d''urgence)'; f = 'chaud.ps1' }
    @{ n = 'agent Prospection (démarrage unique, désactivé par défaut, 10 par boîte, ok lot / ✅ de Liam seul, envoi_automatique, rien d''envoyé)'; f = 'prospection.ps1' }
    @{ n = 'agent Instagram (démarrage unique, désactivé par défaut, un post par jour à 12 h 30, simulation, arrêt et alerte sur erreur, rien de publié)'; f = 'instagram.ps1' }
    @{ n = 'agent devis (démarrage unique, désactivé par défaut, devis PDF + texte, prix des sources seulement, un seul devis en validation, rien envoyé au client, arrêt et alerte sur erreur)'; f = 'devis.ps1' }
    @{ n = 'agent rendez-vous (démarrage unique, désactivé par défaut, lecture iCal, nouveau / déplacé / annulé / rappel annoncés une fois, premier passage sans historique, simulation, adresse secrète jamais affichée)'; f = 'rendez-vous.ps1' }
    @{ n = 'agent appels-sid (liste d''appels du matin pour Sid : 50 à 60 entreprises jamais appelées, restaurants / coiffeurs / plombiers / électriciens, téléphone valide, STOP et exclus écartés, jamais deux fois la même, CSV, preparer / etat / annuler / à blanc, aucun envoi)'; f = 'appels-sid.ps1' }
    @{ n = 'agent resume-sid (résumé Discord du soir : appels Sid comptés sur la feuille Google en lecture seule, chiffre d''affaires Stripe du jour, désactivé par défaut, aucun chiffre inventé)'; f = 'resume-sid.ps1' }
    @{ n = 'agent stripe-alerte (alerte Discord sur nouveau paiement Stripe, lecture seule, désactivé par défaut, premier passage sans rafale sur l''historique, jamais deux fois le même paiement)'; f = 'stripe-alerte.ps1' }
    @{ n = 'agents B2B sur le serveur (liste blanche git sans secret, *.local.json, machine active, lanceur serveur 6 Go, tâches Jarvis-B2B idempotentes, intégration maj-auto, transfert)'; f = 'b2b-serveur.ps1' }
    @{ n = 'harness B2B (cohérence de l''offre, contrats d''agents, garde des envois, traces, surveillant en simulation, tests d''agents, sorties de Jarvis CEO)'; f = 'harness.ps1' }
    @{ n = 'chemins (protection du dossier Jarvis sous un chemin avec espace et en nom court 8.3 « SERVEU~1 », forme longue)'; f = 'chemins.ps1' }
    @{ n = 'diagnostic Discord du portable (faux serveur local, code 403 expliqué, jeton jamais affiché, rien d''envoyé)'; f = 'diag-discord.ps1' }
    @{ n = 'profil serveur (revue de chaque série, séries sautées, memoire\ non contrôlé, tableau lisible, tests-dernier.txt)'; f = 'profil-serveur.ps1' }
)
# Vérifié le 05/11/2026 sur un clone git propre (aucun fichier hors git : ni memoire\, ni config.local.json du PC), SANS claude ni Ollama dans le PATH, sans identité git, sans Node, dans un dossier à espace : routeur, vitesse ressentie (suivi),
# Discord, agent SaaS (dev-agent), agents Instagram et appels-sid n'exigent NI claude NI Ollama (tout y est simulé) : leurs échecs venaient de fichiers propres au PC (memoire\profil.md, config.local.json, journaux d'agents déjà existants,
# réglage serveur de b2b.local.json) ou de la lenteur d'un portable ; les tests ont été rendus indépendants de ces fichiers au lieu de sauter les séries. Si une série exige VRAIMENT une commande, la déclarer dans $exigeCommande ci-dessous : elle est sautée
# (profil serveur seulement) quand Get-Command ne la trouve pas, jamais d'après le nom de la machine.
# REVUE DE CHAQUE SÉRIE pour le profil serveur (voix / écran / Edge / GPU / Ollama / Windows Speech). « garde » = tourne aussi sur le serveur ;
# « SAUTÉE » = sautée seulement en profil serveur, pour la raison écrite. Une série ajoutée à la liste doit recevoir sa ligne ici (tests\profil-serveur.ps1 le vérifie).
#   ecran.ps1              SAUTÉE  choix de l'écran (ecran_jarvis) et géométrie de la fenêtre de l'orbe : le serveur n'a aucun écran à piloter
#   briefing.ps1           garde   appels réseau simulés (faux serveur local), aucune voix
#   veille.ps1             garde   sources simulées, lecture seule ; les mots vosk / GPU ne sont que des textes vérifiés
#   memoire.ps1            garde   dossier temporaire, aucune dépendance matérielle
#   cerveau.ps1            garde   Ollama et Claude simulés (bouchons) ; protection du dossier Jarvis : voir chemins.ps1
#   chemins.ps1            garde   protection du dossier Jarvis sous un chemin avec espace et en nom court 8.3 : aucun matériel
#   competences.ps1        garde   fichiers seulement
#   rapide.ps1             garde   chemin rapide en texte, aucune voix
#   discretion.ps1         garde   niveau du micro SIMULÉ : aucun accès au micro
#   modejeu.ps1            garde   premier plan simulé, aucune fenêtre
#   sons.ps1               garde   jingle généré en fichier, aucune lecture, aucun périphérique audio
#   raccourcis.ps1         garde   touches et raccourcis simulés
#   marche.ps1             garde   source factice, aucune voix réelle
#   sources.ps1            garde   réseau interdit en test (bouchons), Ollama simulé
#   voix.ps1               SAUTÉE  Windows Speech (voix française SAPI) fabrique un WAV que Vosk / Whisper reconnaissent, avec les modèles de voix\models : absents du serveur sans micro
#   routeur.ps1            garde   routeur Ollama simulé, synthèse vocale bouchonnée
#   pc.ps1                 SAUTÉE  contrôle des fenêtres et applications (écran) ; mesures réelles du moteur vocal CPU / GPU (cuda) avec voix française Windows
#   politesse.ps1          garde   ton majordome, fenêtres simulées
#   vitesse.ps1            garde   étages simulés, aucun Ollama réel, aucun son
#   silence.ps1            garde   réglages et arguments de l'écoute vérifiés en texte : aucune écoute lancée
#   salle.ps1              garde   Alpha Vantage simulé, aucune fenêtre
#   interface.ps1          SAUTÉE  charge la page dans Edge sans fenêtre (captures à plusieurs résolutions) : Edge / écran
#   interface-marche.ps1   SAUTÉE  charge la salle de marché dans Edge sans fenêtre : Edge / écran
#   matin.ps1              garde   tout simulé
#   sauvegarde.ps1         garde   faux dossier temporaire
#   discord.ps1            garde   faux pont : requis sur le serveur (pont / alertes)
#   voix-naturelle.ps1     garde   réglages et normalisation du texte, aucun processus de synthèse
#   vitesse-v3.ps1         garde   mesures simulées, aucune voix
#   serveur.ps1            garde   serveur 24/7 : dépôt, installateur en simulation, mise à jour auto
#   bureau.ps1             SAUTÉE  réveil vocal et détecteur de claquements du PC principal : dépend du micro (le serveur est sans micro)
#   serveur-leger.ps1      garde   mode serveur léger : c'est LA série du serveur
#   suivi.ps1              garde   réglages et seuils, Ollama simulé
#   saas.ps1               garde   sources branchées seulement, simulé
#   vercel.ps1             garde   faux serveur local 127.0.0.1
#   dev-agent.ps1          garde   dépôt git temporaire
#   veille-train.ps1       garde   sources simulées, base locale
#   veille-mail.ps1        garde   Gmail simulé
#   offres-debutant.ps1    garde   offres simulées
#   candidatures.ps1       garde   Ollama / Claude Haiku simulés
#   emploi-conducteur.ps1  garde   fichiers et règles seulement
#   initiatives.ps1        garde   dossier temporaire
#   lecons.ps1             garde   Ollama simulé
#   skills.ps1             garde   génération simulée
#   presets.ps1            garde   dossier temporaire
#   vues.ps1               garde   manifestes et JS en texte ; node --check seulement si node est présent
#   pilotage.ps1           garde   pages et routes en texte ; node --check seulement si node est présent
#   voix-actif.ps1         garde   vérifie que la détection vocale reste coupée : aucun micro ouvert
#   chaud.ps1              garde   faux claude local (python), aucun réseau
#   prospection.ps1        garde   agent B2B (requis sur le serveur)
#   instagram.ps1          garde   agent B2B (requis sur le serveur)
#   devis.ps1              garde   agent B2B (requis sur le serveur)
#   rendez-vous.ps1        garde   agent B2B (requis sur le serveur)
#   appels-sid.ps1         garde   agent B2B (requis sur le serveur)
#   resume-sid.ps1         garde   agent B2B, lecture seule (feuille Google + Stripe simulés)
#   stripe-alerte.ps1      garde   agent B2B, lecture seule (Stripe simulé)
#   b2b-serveur.ps1        garde   agents B2B sur le serveur (requis sur le serveur)
#   harness.ps1            garde   harness B2B : aucun réseau, aucun envoi, traces temporaires (requis sur le serveur)
#   profil-serveur.ps1     garde   texte de tout.ps1 seulement
#   diag-discord.ps1       garde   faux serveur local 127.0.0.1 : le diagnostic des alertes Discord sert justement sur le serveur
$exigeCommande = @{ }      # 'serie.ps1' = @('commande', ...) : séries qui exigent vraiment une commande installée (vide : aucune aujourd'hui)
$saute = @{
    'ecran.ps1' = 'choix de l''écran (ecran_jarvis) et géométrie de la fenêtre de l''orbe : le serveur n''a aucun écran à piloter'
    'voix.ps1' = 'Windows Speech (voix française SAPI) fabrique un WAV que Vosk / Whisper reconnaissent, avec les modèles de voix\models : absents du serveur sans micro'
    'pc.ps1' = 'contrôle des fenêtres et applications (écran) ; mesures réelles du moteur vocal CPU / GPU (cuda) avec voix française Windows'
    'interface.ps1' = 'charge la page dans Edge sans fenêtre (captures à plusieurs résolutions) : Edge / écran'
    'interface-marche.ps1' = 'charge la salle de marché dans Edge sans fenêtre : Edge / écran'
    'bureau.ps1' = 'réveil vocal et détecteur de claquements du PC principal : dépend du micro (le serveur est sans micro)'
}
function Get-Instantane {
    $mem = Join-Path $racine 'memoire'
    @{ config = (Get-FileHash (Join-Path $racine 'config.json')).Hash
       # arret.json, modejeu.flag, session-en-cours.jsonl : écrits par Jarvis lui-même quand Liam l'a lancé pendant la passe (faux rouge du 15/11/2026), jamais par un test
       memoire = (@(Get-ChildItem $mem -File -ErrorAction SilentlyContinue | Where-Object { $_.Name -notin @('arret.json', 'modejeu.flag', 'session-en-cours.jsonl') } | Sort-Object Name | ForEach-Object { "$($_.Name):$($_.Length):$($_.LastWriteTimeUtc.Ticks)" }) -join '|')
       env = (Get-FileHash (Join-Path $racine '.env') -ErrorAction SilentlyContinue).Hash }
}
function Get-ProcessusJarvis { @(Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -ne $PID -and $_.CommandLine -match 'Jarvis\\jarvis\.ps1|jarvis\.ps1|ecoute\.py|reveil\.py|coffre-dialogue|jarvis-edge|JarvisOrb|ollama|pont-discord|faux-pont' -and $_.CommandLine -notmatch 'tests\\tout\.ps1' }) }

$avant = Get-Instantane
$procAvant = @(Get-ProcessusJarvis).Count
$copie = Join-Path $env:TEMP ("jarvis-config-test-{0}.json" -f [guid]::NewGuid().ToString('N'))
Copy-Item (Join-Path $racine 'config.json') $copie
$env:JARVIS_TEST = '1'; $env:JARVIS_CONFIG = $copie
$res = @()
try {
    foreach ($t in $liste) {
        if ($profilServeur -and $exigeCommande.ContainsKey($t.f)) { $absente = @($exigeCommande[$t.f] | Where-Object { -not (Get-Command $_ -ErrorAction SilentlyContinue) }); if ($absente.Count) { $res += [pscustomobject]@{ resultat = 'SAUTÉE (profil serveur)'; duree = '-'; test = $t.n; raison = ('commande absente de cette machine : ' + ($absente -join ', ')) }; continue } }
        if ($profilServeur -and $saute.ContainsKey($t.f)) { $res += [pscustomobject]@{ resultat = 'SAUTÉE (profil serveur)'; duree = '-'; test = $t.n; raison = $saute[$t.f] }; continue }
        $sw = [Diagnostics.Stopwatch]::StartNew()
        $args2 = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $PSScriptRoot $t.f))
        $sortie = & powershell @args2 2>&1 | Out-String; $code = $LASTEXITCODE
        $nb = ([regex]::Matches($sortie, '(?m)^\s+OK ')).Count
        $res += [pscustomobject]@{ resultat = $(if ($code -eq 0) { "VERT ($nb vérifications)" } else { "ROUGE (code $code)" }); duree = ('{0:N0} s' -f $sw.Elapsed.TotalSeconds); test = $t.n; raison = '' }
        if ($code -ne 0) { Write-Host ("--- sortie de « {0} » (extrait des échecs) ---" -f $t.n) -ForegroundColor Red; ($sortie -split "`n" | Where-Object { $_ -match 'ECHEC|ÉCHEC|Exception|n.est pas reconnu' }) | Select-Object -First 8 | ForEach-Object { Write-Host $_ } }
    }
} finally {
    Remove-Item $copie -Force -ErrorAction SilentlyContinue
    Get-ChildItem $env:TEMP -Force -ErrorAction SilentlyContinue | Where-Object { $_.Name -like 'jarvis-test-*' -or $_.Name -like 'jarvis-config-test-*' -or $_.Name -like 'jarvis-faux-serveur*' } | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item Env:JARVIS_TEST, Env:JARVIS_CONFIG -ErrorAction SilentlyContinue
    Remove-Item (Join-Path $racine 'memoire\STOP.flag'), (Join-Path $racine 'memoire\parle.flag') -Force -ErrorAction SilentlyContinue
}
# Contrôles de propreté
$apres = Get-Instantane
$ctl = @()
$ctl += [pscustomobject]@{ controle = 'config.json inchangé (les tests ont utilisé une copie)'; ok = ($apres.config -eq $avant.config) }
if ($profilServeur) { $ctl += [pscustomobject]@{ controle = 'memoire\ non contrôlé en profil serveur (Jarvis tourne sur le serveur et y écrit sa mémoire)'; ok = $true } }
else { $ctl += [pscustomobject]@{ controle = 'memoire\ inchangé (aucune écriture dans votre mémoire)'; ok = ($apres.memoire -eq $avant.memoire) } }
$ctl += [pscustomobject]@{ controle = '.env inchangé'; ok = ($apres.env -eq $avant.env) }
$ctl += [pscustomobject]@{ controle = 'aucun processus Jarvis / orbe / écoute / Ollama créé ou resté'; ok = (@(Get-ProcessusJarvis).Count -le $procAvant) }
$ctl += [pscustomobject]@{ controle = 'aucun fichier temporaire de test restant'; ok = (@(Get-ChildItem $env:TEMP -Force -ErrorAction SilentlyContinue | Where-Object { $_.Name -like 'jarvis-test-*' -or $_.Name -like 'jarvis-config-test-*' }).Count -eq 0) }
Write-Host ''
Write-Host ('Profil : ' + $(if ($profilServeur) { 'SERVEUR (séries sans voix, écran, Edge ni GPU)' } else { 'NORMAL (toutes les séries)' }))
# tableau LARGE (220 colonnes) : le résultat est la première colonne, donc jamais tronqué, quelle que soit la largeur de la console
$tableau = ($res | Select-Object resultat, duree, test | Format-Table -AutoSize | Out-String -Width 220)
Write-Host $tableau
foreach ($s in @($res | Where-Object { $_.resultat -like 'SAUTÉE*' })) { Write-Host ('  sautée : {0} -> {1}' -f $s.test.Split('(')[0].Trim(), $s.raison) -ForegroundColor DarkGray }
$ctl | ForEach-Object { Write-Host ("  {0}  {1}" -f $(if ($_.ok) { 'OK   ' } else { 'ECHEC' }), $_.controle) -ForegroundColor $(if ($_.ok) { 'Gray' } else { 'Red' }) }
Write-Host "`nTests manuels (vraies fenêtres / vraies touches), NON lancés ici : tests\manuels.ps1" -ForegroundColor DarkGray
$rouges = @($res | Where-Object { $_.resultat -like 'ROUGE*' }); $mauvais = @($ctl | Where-Object { -not $_.ok })
# une ligne par série (nom | VERT / ROUGE / SAUTÉE | durée) dans logs\tests-dernier.txt (UTF-8) : lisible même si la console tronque
try {
    $dl = Join-Path $racine 'logs'; if (-not (Test-Path -LiteralPath $dl)) { New-Item -ItemType Directory $dl -Force | Out-Null }
    $tx = @(('Tests Jarvis | {0:yyyy-MM-dd HH:mm:ss} | profil {1} | {2}' -f (Get-Date), $(if ($profilServeur) { 'SERVEUR' } else { 'NORMAL' }), $env:COMPUTERNAME))
    foreach ($r in $res) { $tx += ('{0} | {1} | {2}{3}' -f $r.test, ($r.resultat -replace ' \(.*$', ''), $r.duree, $(if ($r.raison) { ' | ' + $r.raison } else { '' })) }
    foreach ($c in $ctl) { $tx += ('controle | {0} | {1}' -f $(if ($c.ok) { 'OK' } else { 'ECHEC' }), $c.controle) }
    $tx += $(if ($rouges.Count -or $mauvais.Count) { 'RESULTAT | ROUGE' } else { 'RESULTAT | VERT' })
    [IO.File]::WriteAllLines((Join-Path $dl 'tests-dernier.txt'), $tx, (New-Object Text.UTF8Encoding($false)))
} catch { Write-Host ('  (logs\tests-dernier.txt non écrit : ' + $_.Exception.Message + ')') -ForegroundColor DarkGray }
if ($rouges.Count -or $mauvais.Count) { Write-Host "ÉCHEC : $($rouges.Count) test(s) rouge(s), $($mauvais.Count) contrôle(s) en échec." -ForegroundColor Red; exit 1 }
Write-Host 'TOUT EST VERT.' -ForegroundColor Green; exit 0
