# PROMPT — Recherche : sites d'artisans qui convertissent, avec une dose de 3D
À donner à Claude (Liam, 22 oct.). Version courte du méga prompt. La version longue est dans PROMPT-RECHERCHE-SITES-LONG.md.
Lancer en recherche approfondie, puis enchaîner avec le navigateur pour les audits.

## 0. Contexte
- Tu es Claude, tu travailles pour Liam Emo, 18 ans, près de Rouen, micro-entrepreneur (LM MULTI-SERVICES).
- Il vend des sites web à des artisans et TPE locales (électricien, plombier, couvreur, maçon, peintre, menuisier).
- Le projet est piloté par des agents. L'agent « Dev sites » fabrique les maquettes et les sites. Ce travail doit le rendre excellent.
- Liam parle à l'oral et veut du direct. Réponds court, clair, en français simple. Humour sec 10 %, jamais s'il est énervé ou si ça parle d'argent.
- Dossier du projet : C:\Users\Liam\Jarvis\B2B\ (architecture, agents, scripts, prototype).

## 1. Ce que Liam veut (à respecter point par point)
1. Les sites faits jusqu'ici sont « moches », « pas assez modernes ».
2. S'inspirer des très grosses entreprises (Apple, Nvidia, LVMH et du même niveau) : même façon de faire, avec un peu de 3D, « mais pas trop » : les artisans sont vite bloqués par un site trop artistique.
3. Le site doit CONVERTIR : le client final doit vouloir choisir CET artisan et le contacter facilement. L'artisan, lui, doit dire « ouais » dès qu'il voit sa maquette.
4. Expliquer pourquoi on met l'artisan en avant (ses forces, ses preuves, sa zone, sa rapidité).
5. Prévoir des espaces pour des PHOTOS (artisan, chantiers, outils, véhicule). Photos d'internet : seulement avec licence claire.
6. Chaque site propre, avec une vraie landing page et de bonnes animations au scroll.
7. Un lien cliquable par prospect (un site maquette par prospect), par exemple sur Vercel.
8. Trouver des connecteurs, skills et plugins pour que les agents fassent de bien meilleurs sites.
9. Un prompt maître que l'agent Dev sites réutilise pour chaque métier.
10. Résultat rentable : un site qui fait sonner le téléphone, donc facile à vendre.

## 2. Point de départ
- Prototype d'électricien : ampoule en verre 3D (three.js) dans un studio sombre, allumée au scroll, puis landing page.
- Faiblesses : 3D faite de formes simples, design proche d'un modèle, aucune vraie photo, conversion pas assez poussée (pas de barre d'appel fixe mobile, pas de formulaire court), pas de SEO local.
- Limites techniques : un artifact claude.ai ne charge pas de fichiers 3D externes. Sur Vercel on peut héberger .glb, textures et images : c'est là que le vrai réalisme devient possible.
- Le shell cloud ne peut pas télécharger depuis n'importe quel site : utilise le navigateur de Liam et demande-lui de télécharger si besoin.

## 3. Règles de travail
1. Cherche à fond. La qualité compte plus que la vitesse.
2. Sources de 2025-2026. Date chaque source. Vérifie les prix sur la page officielle.
3. Pour chaque chiffre, dis : fait vérifié, avis d'un vendeur, ou estimation.
4. Termine chaque partie par « Sources » (titre + lien) et « Points incertains ».
5. Ne copie jamais code, textes, images ou logos d'une marque. On s'inspire des principes (structure, rythme, hiérarchie, mouvement).
6. Aucun faux avis, aucun faux chiffre, aucun faux client. Les exemples sont marqués « exemple ».
7. Au maximum 3 questions courtes à Liam au début, puis avance.
8. N'envoie rien, ne publie rien de public, ne dépense rien, ne crée aucun compte sans l'accord de Liam. Ne tape jamais de mot de passe.
9. Tiens une liste de tâches à jour. Envoie un point de 3 lignes à Liam après chaque grande partie.
10. Note chaque idée de Liam dans docs\IDEES-MASTER.md (dossier SaaS), sans qu'il le demande.
11. Si tu bloques deux fois sur la même action, arrête-toi et demande.

## 4. Axe A — Comment les sites d'artisans sont faits aujourd'hui
Audite au moins 40 sites :
- 15 électriciens, plombiers, couvreurs de la région de Rouen (page 1 de Google et de Maps).
- 10 des meilleurs sites d'artisans en France.
- 10 sites de services locaux à l'étranger (États-Unis, Royaume-Uni, Australie) réputés pour leur conversion.
- 5 offres « clé en main » vendues aux artisans (Wix, Jimdo, packs à 29-129 euros par mois). Ce que l'artisan peut déjà acheter ailleurs.
Grille (note de 0 à 5 et une phrase par point) :
1. Première impression en 5 secondes. 2. Numéro visible et cliquable, bouton fixe mobile. 3. Zone d'intervention.
4. Preuves : avis Google, labels (Qualifelec, RGE…), décennale, années. 5. Photos : vraies ou banque générique.
6. Services et tarifs. 7. Urgence. 8. Formulaire : nombre de champs. 9. Mobile et vitesse (Lighthouse).
10. SEO local : titre, ville, balisage LocalBusiness. 11. Design : moderne ou daté. 12. Animation : aide ou gêne.
13. Confiance : mentions légales, SIRET, visages. 14. Appels à l'action.
Sortie : tableau comparatif, 10 défauts fréquents, 10 éléments gagnants, « niveau moyen à Rouen » (notre site doit être visiblement au-dessus), captures annotées des 10 meilleurs.
Mesures : taux de sites avec numéro cliquable, avis affichés, vraies photos ; vitesse mobile médiane ; nombre de champs moyen.

## 5. Axe B — Références de très haut niveau
Étudie au moins 15 marques : Apple (pages produit), Nvidia, LVMH et ses maisons (Louis Vuitton, Dior, Tiffany), Porsche, Mercedes, Tesla, Dyson, Bang & Olufsen, Stripe, Linear, Vercel, Framer, et les marques de l'artisan (Hilti, Bosch Professional, Legrand, Schneider Electric, Velux, Grohe). Étudie aussi le site Ecco que Liam a montré (chaussure 3D flottante sur une colline, vidéo de Marcelo Design X) : le principe, sans le copier. Relève 20 sites récents primés sur Awwwards et CSS Design Awards avec de la 3D.
Pour chaque référence, note :
1. L'idée centrale. 2. La structure et le rythme des sections. 3. Typographie (avec équivalents Google Fonts).
4. Couleurs. 5. Photo et vidéo (cadrage, lumière). 6. Mouvement : quoi, quand, comment.
7. 3D : où, combien de temps, ce qui se passe au scroll. 8. Mobile. 9. Appel à l'action.
10. Ce qu'on transpose à un artisan, et ce qu'on ne transpose pas (trop luxe, trop artistique, trop lent).
Test « artisan » : un électricien de Sotteville comprend-il en 5 secondes ? Un client en panne à 21h clique-t-il sur Appeler ? Sinon on adapte.
Sortie : moodboard de 10 références avec 3 principes retenus chacune ; règle de dosage de la 3D (hero + une section, jamais dans le formulaire ni l'appel) ; 3 directions artistiques pour un électricien (technique et précis / moderne et rassurant / premium maison), chacune en 10 lignes (palette, polices, photos, mouvement, 3D, ton).

## 6. Axe C — La 3D sur le web
Compare (réalisme, poids, mobile, difficulté, coût) :
- three.js pur (matériaux physiques, HDRI, ombres, post-traitement) et React Three Fiber + drei.
- Spline, model-viewer, Babylon.js.
- Vidéo ou séquence d'images pré-rendue pilotée par le scroll (technique d'Apple, très stable sur mobile) : à évaluer sérieusement, c'est souvent la meilleure option réaliste.
- Rendu Blender exporté, gaussian splats, shaders sur mesure, images 2.5D en parallaxe, fonds animés légers.
Modèles 3D (vérifier la licence à chaque fois) : Poly Haven (CC0), Sketchfab (CC0 et CC-BY), Quaternius, Kenney, banques payantes, générateurs IA (Meshy, Tripo, Rodin, Luma, Hunyuan3D : qualité, prix, droits commerciaux), création Blender procédurale, scan de vrais objets.
Objets par métier (3 propositions, source, licence, poids, qualité) :
électricien (ampoule, prise, tableau, disjoncteur) ; plombier (robinet, mitigeur, chaudière, chauffe-eau) ; couvreur (maison avec toit, tuile, zinc) ; maçon (briques, mur qui se construit) ; peintre (rouleau, nuancier) ; menuisier (fenêtre, porte).
Cibles de performance :
- Hero 3D : moins de 3 Mo au total, idéalement 1,5 Mo. Draco ou Meshopt, textures KTX2 ou WebP.
- LCP moins de 2,5 s en 4G moyenne. Texte et bouton d'appel s'affichent AVANT la 3D.
- 60 images par seconde sur un téléphone milieu de gamme (à mesurer).
- Le site fonctionne sans 3D : image fixe si écran lent, économie d'énergie, WebGL absent ou mouvement réduit.
- Accessibilité : contraste, focus visible, prefers-reduced-motion, navigation clavier.
Tests : Playwright et Chrome de Liam, Lighthouse mobile, un iPhone récent, un Android moyen, un PC portable sans carte dédiée. Captures à 4 moments du scroll et à 390 px et 1280 px. Rappel d'une erreur déjà faite : un observateur de visibilité a figé le rendu d'une section épinglée. Vérifie toujours que la scène bouge vraiment au scroll.
Sortie : tableau comparatif, recommandation à deux niveaux (« standard » pour tous les prospects, « premium » pour les gros clients), liste d'objets retenus par métier avec liens et licences, prototype de test de 2 techniques avec poids et vitesse mesurés.

## 7. Axe D — Conversion (le plus important)
Recherche : études chiffrées sur la conversion des sites de services locaux (bouton d'appel, formulaire court, preuves, vitesse, mobile) ; comportement d'un particulier en urgence ou pour un devis ; éléments de confiance propres au bâtiment en France (décennale, Qualifelec, RGE, QualiPAC, Consuel, devis gratuit, SIRET) ; mots qui convertissent par métier ; ordre des sections qui marche le mieux ; pages à créer (accueil, services, villes, FAQ, réalisations, contact).
Éléments obligatoires sur chaque site :
1. Hero : métier + ville + promesse + boutons Appeler et Devis, visibles en 5 secondes.
2. Barre fixe mobile Appeler / Devis. 3. Numéro cliquable partout.
4. Zone d'intervention (villes, carte simple). 5. Preuves en haut : note Google, avis, années, labels, assurance.
6. 4 à 6 services clairs. 7. Réalisations avant/après avec lieu et durée.
8. 3 vrais avis (de la fiche Google, avec accord). 9. Trois raisons concrètes de choisir l'artisan.
10. Méthode en 3 ou 4 étapes. 11. Tarifs indicatifs. 12. Urgence : délai et horaires réels.
13. Formulaire de 4 champs maximum avec promesse de rappel. 14. FAQ de 5 à 8 vraies questions.
15. Mentions légales, SIRET, assurance. 16. Balisage SEO local, titres avec la ville. 17. Lien vers fiche Google et réseaux. 18. Aucune fausse promesse.
Psychologie : réduire l'effort (un clic), réduire le risque (devis gratuit, garantie), montrer le visage de l'artisan, preuve locale, urgence honnête, cohérence avec la fiche Google.
Suivi : appels, formulaires, clics sur le numéro, mesure sans cookie, résultat chiffré montré à l'artisan après 30 jours.
Sortie : checklist de conversion de 40 points ; plan de page par métier (ordre, but, texte type) ; 10 titres de hero par métier testés à la règle des 5 secondes ; bibliothèque de textes d'appel à l'action ; un exemple complet de page d'électricien en français avec zones photo.

## 8. Axe E — Photos et droits
Emplacements à prévoir : hero, portrait de l'artisan avec prénom, véhicule ou atelier, 4 à 8 chantiers avant/après, photos par service, labels et marques, fond de la zone d'intervention. Pour chacun : taille, ratio, texte alternatif, légende, consigne de cadrage.
Origine, dans l'ordre :
1. Vraies photos de l'artisan (téléphone, Google Business, Facebook), avec son accord écrit.
2. Banques libres à licence commerciale claire (Unsplash, Pexels, Pixabay) : relis les conditions à jour, note auteur et licence dans un registre par site.
3. Images générées par IA, marquées comme telles en interne, jamais présentées comme de vrais chantiers de l'artisan.
À éviter : photos copiées chez un concurrent, sur Google Images ou Pinterest ; personnes identifiables sans accord.
Sur une maquette envoyée, marque clairement les zones « photo à remplacer par les vôtres ».
Sortie : liste de 10 banques et outils d'images (licence, qualité, prix), gabarit de registre de licences, guide « 10 photos à prendre » pour l'artisan, règle « jamais de fausse photo présentée comme vraie ».

## 9. Axe F — Meilleurs prompts, outils, skills, connecteurs
Recherche :
- Meilleurs prompts publics pour générer des sites haut de gamme avec Claude, v0, Lovable, Bolt, Cursor, Framer AI, Figma Make, Webflow AI.
- Guides officiels d'Anthropic pour le design front-end avec Claude et skills de design de la communauté (frontend-design et autres).
- Composants et animations : shadcn/ui, Magic UI, Aceternity UI, 21st.dev, Framer Motion, GSAP + ScrollTrigger, Lenis, Rive, Lottie, Spline.
- Design : palettes (Radix Colors), Tailwind v4, polices de caractère (Google Fonts, Fontshare).
- Connecteurs MCP : Figma, Vercel (connecté), Supabase (connecté), Playwright et Chrome pour les captures, Lighthouse, photos libres, Blender MCP, API de génération 3D.
- Dépôts GitHub de templates haut de gamme (licences et usage commercial).
- Banque de styles Refero (https://styles.refero.design/, idée de Liam) : plus de 2 000 styles de vrais sites avec fichier DESIGN.md et un MCP (refero.design/mcp). Évalue-la : qualité, couverture (Apple, Nvidia, LVMH et du même niveau ?), prix, licence et conditions, intégration avec Claude Code. Choisis 3 styles par direction artistique.
- Cas concrets : agence qui produit des dizaines de sites d'artisans avec l'IA ; site fait avec Claude Code qui ressemble à Apple.
Pour chaque outil : ce qu'il fait, prix vérifié, qualité (exemples réels), facilité pour un agent autonome, droits commerciaux, verdict (indispensable / utile / à ignorer).
Prompt maître du site d'artisan, avec variables {NOM} {METIER} {VILLE} {ZONE} {TELEPHONE} {NOTE_GOOGLE} {NB_AVIS} {AVIS_REELS} {SERVICES} {ANNEES} {LABELS} {PHOTOS} {DIRECTION_ARTISTIQUE} {NIVEAU_3D}. Sections : rôle, objectif de conversion, direction artistique, structure, copywriting, design (typo, couleurs, espaces), animations, 3D et repli, photos et licences, SEO local, accessibilité, performance, fichiers livrés, auto-vérification. Ajoute un bloc « jamais » (dégradé violet générique, polices par défaut, cartes identiques, faux avis, texte de remplissage, animation partout) et des exemples avant/après. Fournis une version courte (30 lignes), une version longue (200 lignes), un niveau standard et un niveau premium, et un prompt d'AUTO-CRITIQUE : l'agent regarde ses captures et corrige jusqu'à 100 % de la checklist.
Sortie : tableau d'outils avec prix et verdict, 10 meilleurs prompts résumés, prompt maître prêt à copier, liste ordonnée des skills, plugins et connecteurs à installer avec lien ou commande.

## 10. Axe G — Industrialiser : un site par prospect, sans perdre en qualité
- Moteur de modèles : un thème par direction artistique, un contenu par métier, des variables par prospect.
- Un projet Vercel unique, une page par prospect (/nom-entreprise), non indexée, lien difficile à deviner. Étudie aussi sous-domaine par prospect, mot de passe léger, expiration automatique.
- Hébergement des .glb, images et vidéos : où, poids, cache, coût. Limites gratuites actuelles de Vercel à vérifier.
- Flux : liste de prospects, données Google Maps, prompt maître, génération, captures, contrôle, correction (3 essais maximum puis demande à Liam), lien.
- Contrôle automatique : captures à 390 et 1280 px à 4 points du scroll ; Lighthouse mobile (performance 85+, accessibilité 95+, SEO 95+) ; numéro cliquable, barre fixe, aucune faute, aucun « exemple » oublié, aucun avis inventé, licences renseignées, aucune copie de marque ; score sur 100 écrit dans agents\dev-sites.md.
- Après la vente : ce que l'agent change seul (textes, photos, couleurs, horaires), ce qui demande Liam (nouvelle page, intégration), où sont notées les demandes, délai de 7 jours.
- Propriété : site, nom de domaine, contenus, hébergement, résiliation. Mentions légales et RGPD du site livré.
Sortie : schéma du flux, checklist qualité automatisable, coût réel par site (temps, jetons, hébergement), plan pour passer de 1 à 50 sites par semaine.

## 11. Axe H — Vendre le résultat
- Présenter la maquette pour qu'il dise « ouais » en 10 secondes (premier écran, message d'accompagnement).
- Comparaison « votre site aujourd'hui / demain » sans agressivité.
- Arguments honnêtes sur ce qu'un site peut apporter (appels, devis), avec sources et prudence.
- Objections : « j'ai Facebook », « pas le temps », « trop cher », « mon neveu me le fait », « j'ai assez de travail ».
- Vérifier que les offres (59 euros par mois sans création, ou 590 à 990 euros) tiennent avec cette qualité ; ajuster.
- Garanties : maquette gratuite, modifications avant mise en ligne, résiliation, nom de domaine à l'artisan.
- 3 versions courtes de message (mail, LinkedIn, Facebook) avec lien de maquette, mentions légales et STOP. Jamais envoyé sans l'accord de Liam.

## 12. Créer les agents (à ne pas oublier)
La recherche rend les agents meilleurs, elle ne les remplace pas. Liam met en place l'infrastructure le 22 oct. (domaine, boîtes mail, connexions), puis on finit les agents.
- À créer ou finir (fichiers dans C:\Users\Liam\Jarvis\B2B\agents\) : sourcing, enrichissement, qualification, DEV SITES, rédaction, envoi, réponses, relances. Architecture : ARCHITECTURE-AGENT-B2B.md.
- DEV SITES en priorité : prompt maître, skills, plugins et connecteurs retenus, checklist, modèles par métier.
- Pour chaque agent : rôle, consignes, skills et plugins, entrées et sorties, ce qu'il fait seul, ce qui demande l'OK de Liam, fichier de suivi (clients, demandes, décisions).
- Ils remontent à Jarvis (4e superviseur « Agence B2B »).
- Dans la réponse finale : liste « agents créés / à finir » avec l'état de chacun, et ce que Liam doit faire de son côté.

## 13. Méthode, dans l'ordre
1. Relis ce prompt, pose au maximum 3 questions, crée la liste de tâches.
2. Axe A (audit). 3. Axe B (références). 4. Axe D (conversion) : priorité, ne la sacrifie pas.
5. Axe C (3D). 6. Axe E (photos). 7. Axe F (prompts et outils). 8. Axe G (industrialisation). 9. Axe H (vente).
10. Construis 3 prototypes d'électricien (une direction artistique chacun, niveau standard) et 1 premium avec 3D. Teste-les avec la checklist. Montre-les à Liam.
11. Avec son choix, décline en plombier, couvreur et maçon.
12. Mets à jour les fichiers des agents, l'architecture et IDEES-MASTER.md.
Points à Liam à la fin des étapes 3, 6 et 10.

## 14. Checklist qualité (un site n'est prêt que s'il passe tout)
Première impression : on comprend métier, ville et comment appeler en 5 secondes ; le design ressemble à une marque, pas à un modèle.
Conversion : numéro cliquable en en-tête, hero et bas de page ; barre d'appel fixe mobile ; formulaire de 4 champs maximum ; note, avis, labels et assurance en haut ; avis réels uniquement ; photos de chantiers ; zone d'intervention ; FAQ, méthode, tarifs indicatifs.
Design : deux polices au maximum avec hiérarchie nette ; un seul accent de couleur ; espaces réguliers, aucun débordement ; une seule grande séquence d'animation ; 3D dosée et remplaçable par une image.
Technique : vitesse mobile bonne ; fonctionne sans 3D, sans JavaScript d'animation et avec mouvement réduit ; accessibilité ; SEO local ; aucune erreur dans la console.
Honnêteté et droits : aucun faux avis, chiffre ou logo ; licence notée pour chaque photo ; aucune copie de marque ou de site ; zones « exemple » remplacées avant tout envoi.

## 15. Livrables (dans C:\Users\Liam\Jarvis\B2B\recherche-sites\)
01-audit-sites-artisans.md ; 02-references-grandes-marques.md ; 03-conversion.md ; 04-3d-web.md ; 05-photos-et-droits.md ; 06-prompts-outils-connecteurs.md ; 07-prompt-maitre.md ; 08-industrialisation.md ; 09-vente.md ; prototypes\ (3 standard + 1 premium, liens et captures) ; agents\ mis à jour ; 00-resume-pour-liam.md (1 page, 10 lignes de décisions).
Chaque fichier finit par « Sources » et « Points incertains ».

## 16. À ne pas faire
- Un site « pour Awwwards » que l'artisan ne comprend pas.
- Cacher le numéro derrière une animation, ou charger la 3D avant le texte.
- Copier une marque, un site, ses images.
- Inventer avis, clients, chiffres, labels, ou promettre un classement Google.
- Le même design pour tous les métiers.
- Envoyer une maquette à un vrai artisan sans l'accord de Liam ; publier une page publique au nom d'une vraie entreprise sans accord.
- Dépenser, créer un compte ou s'inscrire sans l'accord de Liam.
- Confondre joli et efficace : le but est que le téléphone sonne.

## 17. Critères de réussite
1. Liam regarde un site et dit « ouais » sans hésiter.
2. Un artisan de Rouen comprend sa maquette en 10 secondes.
3. Un client en panne trouve le numéro et appelle en moins de 10 secondes.
4. Le site passe la checklist à 100 %, et il est rapide sur un téléphone moyen.
5. Un agent fabrique un nouveau site de ce niveau en moins de 30 minutes avec le prompt maître.
6. Tout est documenté dans les fichiers des agents, sans problème de droits ni d'honnêteté.

## 18. Pour finir
- Annonce en une phrase ce que tu vas faire, puis lance la recherche. Recoupe les sources. Dis-le quand tu doutes.
- À la fin : ce qui est prêt, ce que Liam doit décider, la prochaine action la plus utile.
