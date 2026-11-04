# Transfert des agents B2B du PC vers le portable serveur (une seule fois)

Rédigé le 04/11/2026. Principe : **une seule machine fait tourner les agents B2B à la fois**. Ce qui est dans git (le code, les configs par défaut, les tests) arrive sur le portable tout seul avec `maj-auto.ps1`. Ce qui est secret, propre à une machine ou qui est un état de travail **n'est jamais dans git** : on le déplace une seule fois, à la main, dans l'ordre ci-dessous.

Rien n'est installé ni démarré par ce document : chaque agent ne s'allume que quand vous l'avez écrit dans `agents_actifs`.

## Les 4 étapes, dans l'ordre

### 1. Arrêter les agents sur le PC
Dans `C:\Users\Liam\Jarvis` (PowerShell), pour chaque agent qui tourne ou a tourné (un arrêt sur un agent déjà arrêté est sans effet) :

```powershell
python B2B\agents\prospection.py arreter
python B2B\agents\instagram.py arreter
python B2B\agents\devis.py arreter
python B2B\agents\rendez-vous.py arreter
```
Puis fermez Jarvis sur le PC, ou mettez `"prospection_actif": "non"` (et `instagram_actif`, `devis_actif`, `rendez_vous_actif` s'ils sont à « oui ») dans le `config.local.json` du PC, pour que Jarvis ne relance rien au prochain démarrage. (`config.json` contient aujourd'hui `"prospection_actif": "oui"` : ne le poussez pas tel quel sur GitHub, voir le rapport.) Si la tâche planifiée « Jarvis-Appels-Sid » existe sur le PC : `python B2B\agents\appels-sid.py retirer-tache --oui`.
Vérifiez : plus aucun `*.verrou` dans `B2B\agents\` (un fichier `prospection-continu.verrou` qui reste est un verrou périmé : supprimez-le **après** avoir vérifié que le processus n'existe plus).

### 2. Copier les fichiers (PC -> portable, clé USB ou partage réseau), une seule fois
Respectez les mêmes chemins relatifs sous `C:\Users\Liam\Jarvis\` du portable. **Ne passez ni par e-mail, ni par Discord, ni par GitHub.**

**Secrets et jetons** (jamais dans git) :
| Fichier (sous `B2B\agents\`) | Rôle |
|---|---|
| `gmail-client.json` | client OAuth Gmail |
| `gmail-token-contact.lmsites@gmail.com.json`, `gmail-token-liamdigital2109@gmail.com.json` | jetons Gmail (un par boîte) |
| `google-client.json` | client OAuth Google Drive (appels-sid) |
| `google-sheets-token.json` | jeton Google Drive (si `google-autoriser` a été fait) |
| `instagram-token.json` | jeton Instagram (s'il existe) |
| `identite.json` | identité LM MULTI-SERVICES (modèle : `identite.exemple.json`) |
| `B2B\.env` (à la racine de B2B, pas dans `agents\`) | mots de passe d'application et adresse iCal ; ne jamais l'ouvrir devant quelqu'un ni le coller dans un chat |

**Configs locales** (ignorées par git ; surchargent les valeurs par défaut) :
`appels-sid-config.local.json`, `rendez-vous-config.local.json`, `reponses-config.local.json`, et ceux que vous avez créés pour `instagram`, `devis`, `prospection` (`<agent>-config.local.json`). Ils contiennent les salons Discord, les comptes Gmail, l'adresse iCal, `partager_avec`, `envoi_automatique`. Copiez-les, puis relisez-les sur le portable : **mettez `envoi_automatique` à `true` seulement un agent après l'autre, à l'étape 4**.

**États et listes de travail** (pour ne rien renvoyer deux fois) :
| Fichier | Rôle |
|---|---|
| `agents\prospection-etat.json` | lots, envois, relances, quotas du jour |
| `agents\prospection-retours.json` | rebonds et plaintes |
| `agents\exclus-emails.json` | adresses à ne plus jamais contacter (STOP, refus) |
| `agents\reponses-traitees.json` | réponses déjà classées |
| `agents\devis-etat.json`, `agents\rendez-vous-etat.json`, `agents\instagram-etat.json`, `agents\appels-sid-etat.json` | états de chaque agent (seulement ceux qui existent) |
| `prospection-trouves.csv`, `suivi-prospects.csv`, `prospects.csv`, `prospects_maps.csv`, `prospects_rouen.csv` | listes de prospects |
| `messages-a-valider.md` | messages en attente de votre « ok » |
| `lots\` | lots du jour et archives |
| `docs\sid\` et `docs\liste-appels-*.md` | listes d'appels déjà produites (pour ne jamais redonner la même entreprise à Sid) |
| `instagram\` | visuels de la file de publication (l'agent ne fabrique AUCUNE carte sur le serveur : pas de navigateur) |
| `devis\` | devis déjà préparés (s'il existe) |

**À ne pas copier** : les fichiers `*.verrou`, `*.arret`, `*.log`, `__pycache__\`, `maquettes\`, `sites\` (sauf `sites\moteur\*.py`, qui arrive par git). Les clés de Jarvis lui-même (`.env` de la racine) suivent leur chemin habituel : `.env.chiffre` + `installer-serveur.ps1`.

### 3. Définir `machine_active` sur le portable
Sur le portable, `B2B\agents\b2b.local.json` (fichier ignoré par git) :

```json
{ "machine_active": "NOM-DU-PORTABLE", "agents_actifs": [], "serveur": true }
```
Le nom exact s'obtient sur le portable avec `$env:COMPUTERNAME`. Tant que `machine_active` n'est pas ce nom, **aucun agent B2B ne tourne** (refus avec le code 3, écrit dans le journal de l'agent et dans `agents\serveur-b2b.log`).
**Sur le PC**, ouvrez aussi `B2B\agents\b2b.local.json` et remplacez `machine_active` par le nom du portable : le PC refusera alors de lancer un agent, même si Jarvis le relance par erreur. (Sans ce fichier, le PC refuse aussi : « machine_active absent ».)

### 4. Activer agent par agent sur le portable
Pour chacun, dans cet ordre conseillé (du plus inoffensif au plus sensible) : `rendez-vous` (lecture d'agenda), `appels-sid`, `devis`, `reponses`, `instagram`, `prospection`.
1. Ajoutez son nom dans `agents_actifs` de `b2b.local.json` (exemple : `["rendez-vous"]`).
2. Attendez la prochaine mise à jour automatique (10 min), ou lancez `powershell -File maj-auto.ps1`, qui, après un pull réussi et des tests verts, installe les dépendances (`B2B\requirements.txt`) et crée la tâche `Jarvis-B2B-<agent>`. Les agents sont lancés par `B2B\agents\serveur-b2b.ps1` : **un seul à la fois, priorité basse, jamais de navigateur**.
3. Essai sans rien envoyer : `powershell -File B2B\agents\serveur-b2b.ps1 -Agent rendez-vous -Simulation` (affiche ce qui serait lancé).
4. Regardez `B2B\agents\serveur-b2b.log` et le journal de l'agent après un cycle. Si tout est bon, mettez `envoi_automatique` à `true` dans **son** `*.local.json`, pas avant.
Retirer un agent de `agents_actifs` supprime sa tâche à la mise à jour suivante.
5. **Sur le portable, mettez aussi `"prospection_actif": "non"` (idem `instagram_actif`, `devis_actif`, `rendez_vous_actif`) dans son `config.local.json`** : les agents sont lancés par les tâches `Jarvis-B2B-*`, pas par Jarvis. Par sécurité, un agent listé dans `agents_actifs` refuse de toute façon les commandes `continu`, `ecouter` et `demarrage` (une seule boucle par agent, jamais deux) : le journal de l'agent écrit « double emploi ».

## Vérifier que rien ne tourne en double
Sur **chaque** machine :

```powershell
Get-ScheduledTask | Where-Object TaskName -like 'Jarvis-B2B-*' | Select TaskName, State   # PC : aucune ligne ; portable : les agents actifs seulement
Get-ChildItem B2B\agents\*.verrou                                                          # PC : aucun fichier
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'B2B\\agents\\(prospection|instagram|devis|rendez-vous|reponses|appels-sid)\.py' } | Select ProcessId, CommandLine
Get-Content B2B\agents\serveur-b2b.log -Tail 20                                            # portable : cycles, priorité BelowNormal, « occupé » si un autre agent tourne
```
- Le PC ne doit afficher **aucun** processus d'agent ni aucune tâche `Jarvis-B2B-*`.
- Sur le portable, au plus un processus d'agent à la fois (le verrou global l'impose ; « occupé » dans le journal = un cycle abandonné, normal).
- Un lancement par erreur sur le PC donne : `refusé : cette machine est « … », la machine active est « … »` dans `B2B\agents\<agent>-journal.log` (code 3, aucun état écrit, rien envoyé).
- Les agents n'envoient rien tant que `envoi_automatique` n'est pas `true` dans leur `*.local.json` : en cas de doute, il suffit de le remettre à `false`.

## En cas de problème
- Retour arrière : retirez l'agent de `agents_actifs` (sa tâche disparaît à la prochaine mise à jour) ; pour tout arrêter tout de suite : `Unregister-ScheduledTask -TaskName 'Jarvis-B2B-<agent>' -Confirm:$false`. `Jarvis-MajAuto` et `Jarvis-Serveur` ne sont jamais touchées par cette fonction.
- Une mise à jour refusée par `maj-auto` (tests rouges) ne change ni les tâches ni les dépendances B2B.
