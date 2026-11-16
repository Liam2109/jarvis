# Histoires de la ligne B (compte recrutement de call callers) — écrites à la main (17/11/2026)

Petites histoires originales de 25 à 35 s pour attirer une audience large, puis l'appel à l'action (ajouté par le code, voir plus bas).
Structure fixe : **accroche** (2 premières secondes : situation absurde ou question qui pique), **mise en place**, **tension**, **retournement** drôle (la chute), puis l'appel à l'action (4 à 5 s).
Personnage récurrent : Gérard (une série). Qwen ne fait que varier prénoms, métiers et détails de ces histoires ; il n'en invente jamais (`Videos\agents\scripts.py` refuse une variante trop éloignée et garde alors le texte d'origine).

**Répartition (17/11/2026)** : 40 % leçons de vente au téléphone (`Lnn`, thème « leçon » : accroche dans les 3 premières secondes, pivot, chute ;
sujets : le cold call n'est pas mort, les premières secondes, répondre à « c'est trop cher », les premiers appels servent à se calibrer), 40 % comédie Gérard
(téléphone, peur du non, premier appel, trac, petit extra), 20 % entrepreneuriat et quotidien. `Videos\agents\histoires.py` choisit la catégorie la plus en retard
sur sa part dans les 20 dernières vidéos ; aucune histoire n'est rejouée avant 20 vidéos. Ces textes sont des graines : Qwen varie détails et métiers, le code fait
tourner l'ouverture, la structure et la fin, et refuse une vidéo trop proche d'une des 20 dernières.
Interdits en plus pour les leçons : revenu chiffré, « mon closer gagne », faux témoignage, statistique non vérifiée, chercher le numéro privé d'un décideur, promesse de gain.

Format lu par le code (une histoire = un titre `## Hnn | thème | décor | titre` ou `## Lnn | leçon | …`, puis une ligne par réplique) :
`- <rôle> | <expression> | <geste> | <texte>`
- rôles : accroche, mise en place, tension, pivot (leçons), retournement (la première ligne « retournement » est la chute), chute (la chute d'une leçon, ou la suite de la chute) ;
- expressions : neutral happy smug sarcastic annoyed angry shocked sad crying cringe confused deadpan skeptical worried embarrassed thinking laughing ;
- gestes : idle point shrug facepalm arms-up arms-crossed think lean-in recoil slump hands-on-hips hold-phone hold-out hold-chest hold-up high-five shove faint wave thumbs-up ;
- décors : bureau, cabinet, boutique, cafe, cuisine, salon, rue, parc, reunion, chambre.
Interdits (refusés par le code) : chiffre ou nombre, promesse de revenu, faux témoignage, vraie personne imitée, ville ou lieu, vouvoiement du spectateur (hors paroles citées entre « »), « rendez-vous de 15 minutes », « Découvrez comment ».

## Appels à l'action (tournants, même sens)
- On recrute des call callers à la commission. Postule avec le lien du formulaire en bio, ou envoie-moi un DM.
- On cherche des call callers, à la commission. Le formulaire est en bio, ou écris-moi en DM.
- Call caller à la commission, ça te tente ? Postule via le formulaire en bio, ou envoie-moi un DM.
- Toi aussi, appelle à la commission : on recrute des call callers. Formulaire en bio, ou un DM.
- On recrute des call callers, payés à la commission. Le lien du formulaire est en bio, ou envoie un DM.

## L01 | leçon | bureau | Le cold call n'est pas mort
- accroche | skeptical | arms-crossed | « Le téléphone, c'est fini. » Vraiment ?
- mise en place | thinking | think | Tout le monde envoie des mails. Ta boîte aussi déborde.
- pivot | happy | point | Un appel, lui, on y répond. Une voix, ça ne se range pas dans les indésirables.
- chute | smug | hands-on-hips | Gérard a appelé ceux que tout le monde mailait. Il était le seul au bout du fil.

## L02 | leçon | bureau | Personne ne décroche ?
- accroche | confused | shrug | Personne ne décroche plus au téléphone ? Faux.
- mise en place | worried | hold-phone | Gérard appelait à l'heure où tout le monde est débordé.
- pivot | thinking | think | Il a changé d'heure : tôt le matin, ou en fin de journée.
- chute | happy | thumbs-up | Mêmes numéros, même texte. Mais cette fois, quelqu'un était là pour décrocher.

## L03 | leçon | bureau | Les premières secondes
- accroche | shocked | recoil | Au téléphone, ta première phrase décide de la suite.
- mise en place | worried | hold-phone | Gérard commençait par : « Je ne vous dérange pas ? » Réponse : si.
- pivot | thinking | think | Maintenant, il dit son prénom, pourquoi il appelle, et il pose une question simple.
- chute | happy | point | La personne répond à la question. Et la conversation commence enfin.

## L04 | leçon | bureau | Se taire au bon moment
- accroche | skeptical | arms-crossed | Tu parles trop dans tes premières secondes.
- mise en place | worried | hold-phone | Gérard enchaînait tout : son nom, l'offre, les détails, la météo.
- pivot | thinking | think | Il a appris à dire une phrase claire. Puis à se taire.
- chute | smug | hands-on-hips | Le silence fait parler l'autre. Gérard a découvert qu'il savait écouter.

## L05 | leçon | bureau | « C'est trop cher »
- accroche | shocked | recoil | « C'est trop cher. » Et là, tu paniques ?
- mise en place | worried | hold-chest | Gérard baissait le prix tout de suite. Par réflexe.
- pivot | thinking | think | Maintenant, il demande : « Trop cher par rapport à quoi ? »
- chute | happy | point | Cette fois, ce n'était pas le prix. C'était une question que personne n'avait posée.

## L06 | leçon | bureau | Trop cher, vraiment ?
- accroche | confused | shrug | « Trop cher » ne veut pas toujours dire trop cher.
- mise en place | thinking | think | Parfois, ça veut dire : je ne vois pas encore à quoi ça me sert.
- pivot | happy | point | Alors Gérard ne défend pas son prix. Il demande ce qui compte pour la personne.
- chute | smug | hands-on-hips | Il écoute, il reformule. Le prix n'a pas bougé. La conversation, si.

## L07 | leçon | bureau | Les premiers appels
- accroche | worried | hold-chest | Tes premiers appels vont être ratés. C'est normal.
- mise en place | embarrassed | facepalm | Gérard a bafouillé, oublié son propre nom, raccroché trop tôt.
- pivot | thinking | think | Mais chaque appel raté lui apprenait un réglage : le ton, le rythme, la question.
- chute | happy | thumbs-up | Les premiers appels ne servent pas à vendre. Ils servent à se calibrer.

## L08 | leçon | bureau | Le carnet de Gérard
- accroche | thinking | think | Gérard note chaque appel dans un carnet. Même les pires.
- mise en place | sad | slump | Ce qui a coincé, la phrase qui a fait raccrocher, l'objection qu'il n'attendait pas.
- pivot | happy | point | Après quelques jours, il voit revenir les mêmes pièges.
- chute | smug | hands-on-hips | Il ne les évite pas tous. Mais il ne tombe plus dans les mêmes.

## H01 | téléphone | bureau | Le premier appel répété
- accroche | shocked | recoil | Gérard a répété son premier appel pendant une heure.
- mise en place | thinking | think | Devant le miroir : le ton, le sourire, la phrase d'accroche.
- tension | worried | hold-phone | Il compose le numéro. Ça sonne. Son cœur fait du trampoline.
- tension | shocked | recoil | Quelqu'un décroche !
- retournement | embarrassed | facepalm | Et Gérard, par réflexe, répond : « Allô, oui, c'est pour quoi ? »

## H02 | peur du non | bureau | Prêt pour le refus
- accroche | worried | hold-chest | Gérard a peur d'un seul mot : non.
- mise en place | thinking | think | Alors il prépare une réponse à chaque objection possible.
- tension | worried | hold-phone | Il appelle, prêt au combat, en attendant le refus.
- retournement | confused | shrug | La dame dit oui tout de suite. Gérard n'avait rien préparé pour ça.
- chute | embarrassed | facepalm | Il a raccroché pour réfléchir.

## H03 | peur du non | bureau | Le collectionneur de non
- accroche | happy | arms-up | Gérard collectionne les « non ».
- mise en place | sad | slump | Au début, chaque refus le vexait pour la journée.
- tension | thinking | think | Puis il a compris : un non, c'est juste un appel de moins avant un oui.
- retournement | laughing | thumbs-up | Maintenant, quand on lui dit non, il dit merci. Les gens sont tellement surpris qu'ils restent en ligne.

## H04 | petit extra à côté | salon | Arrondir les fins de mois
- accroche | skeptical | arms-crossed | Gérard voulait arrondir ses fins de mois.
- mise en place | thinking | think | Il a pensé à garder des chiens. Il est allergique.
- tension | worried | shrug | Il a pensé à vendre des gâteaux. Il les mange avant.
- retournement | happy | hold-phone | Alors il a pris son téléphone : le seul truc qu'il ne lâche jamais, de toute façon.

## H05 | petit extra à côté | salon | Le fauteuil de direction
- accroche | smug | hands-on-hips | Le bureau de Gérard, c'est son canapé.
- mise en place | happy | hold-phone | Le matin, il appelle en pantoufles. Personne ne le sait.
- tension | worried | hold-chest | Un jour, un artisan lui demande s'il est bien installé.
- retournement | embarrassed | facepalm | Gérard répond : « Oui, dans mon fauteuil de direction. » C'était un pouf.

## H06 | premier appel | bureau | Hors script
- accroche | confused | think | Gérard a appris son script d'appel par cœur.
- mise en place | worried | hold-phone | Au premier appel, la dame pose une question qui n'est pas dans le script.
- tension | worried | hold-chest | Silence. Gérard cherche dans sa feuille.
- retournement | embarrassed | facepalm | Il lit quand même la ligne suivante : « Parfait, je vous note pour jeudi. » La dame voulait juste l'heure.

## H07 | téléphone | bureau | Le boulanger à midi
- accroche | shocked | recoil | Gérard appelle un boulanger à midi pile.
- mise en place | smug | hands-on-hips | Il est fier : son texte, sa voix posée, son plus beau sourire.
- tension | worried | hold-phone | Au bout du fil : la sonnette, la file d'attente, un four qui bipe.
- retournement | embarrassed | facepalm | Le boulanger souffle : « Rappelez quand je ne vends pas de pain. » Gérard note : jamais un boulanger à midi.

## H08 | le trac | salon | La cape
- accroche | worried | hold-chest | Gérard tremble avant chaque appel.
- mise en place | thinking | think | Il a tout essayé : respirer, chanter, les encouragements de son chat.
- tension | confused | shrug | Puis il remarque un détail : la personne au bout du fil ne le voit pas.
- retournement | laughing | arms-up | Depuis, il appelle avec une cape de super-héros. Le trac est parti. Les voisins, eux, s'inquiètent.

## H09 | entrepreneuriat | cabinet | Le cabinet introuvable
- accroche | sad | slump | Gérard a ouvert son cabinet. Personne ne vient.
- mise en place | smug | hands-on-hips | Une belle plaque, un bureau rangé, une plante.
- tension | worried | hold-phone | Il demande à son neveu de le chercher en ligne.
- retournement | shocked | recoil | Le neveu trouve un restaurant, une piscine et un chat qui s'appelle Gérard. Pas le cabinet.
- chute | embarrassed | facepalm | Gérard vient de découvrir qu'il lui manque un site.

## H10 | entrepreneuriat | bureau | Son propre patron
- accroche | smug | hands-on-hips | Gérard est devenu son propre patron.
- mise en place | happy | arms-up | Le premier jour, il s'accorde une longue pause café.
- tension | annoyed | arms-crossed | Le lendemain, il se convoque pour parler de ses pauses café.
- retournement | embarrassed | facepalm | Il s'est donné un avertissement. Puis il s'est pardonné, autour d'un café.

## H11 | entrepreneuriat | bureau | Le logo parfait
- accroche | happy | arms-up | Gérard a passé tout son mois sur un logo.
- mise en place | thinking | think | La couleur, la police, l'ombre portée, tout y est.
- tension | smug | point | Il l'imprime en grand et l'accroche au mur.
- retournement | confused | shrug | Il ne lui reste qu'une petite question : ce qu'il vend, exactement.

## H12 | entrepreneuriat | reunion | La réunion d'équipe
- accroche | thinking | think | Gérard organise une grande réunion d'équipe.
- mise en place | happy | point | Café, croissants, tableau blanc, ordre du jour.
- tension | smug | hands-on-hips | Il prend la parole, très sérieux : « Bien. Qui a une idée ? »
- retournement | deadpan | shrug | Silence. Gérard est tout seul dans son entreprise. Il a voté pour lui. À l'unanimité.

## H13 | entrepreneuriat | bureau | Les cartes de visite
- accroche | smug | hold-up | Gérard a fait imprimer des cartes de visite.
- mise en place | happy | hold-out | Il en donne à tout le monde : au facteur, au boulanger, à sa belle-mère.
- tension | shocked | recoil | Un soir, enfin, le téléphone sonne : quelqu'un a trouvé sa carte !
- retournement | embarrassed | facepalm | C'est sa belle-mère. Elle demande s'il peut passer réparer sa télé.

## H14 | entrepreneuriat | boutique | La stratégie de l'attente
- accroche | thinking | think | Gérard a une stratégie pour trouver des clients : attendre.
- mise en place | deadpan | arms-crossed | Il attend devant la porte. Il attend devant l'ordinateur.
- tension | sad | slump | Il lit même des livres sur la patience. Toujours rien.
- retournement | shocked | recoil | Un jour, quelqu'un entre ! C'est le livreur. Il s'est trompé d'adresse.

## H15 | vie quotidienne | cuisine | Manger sain
- accroche | smug | arms-crossed | Gérard a décidé de manger sain.
- mise en place | deadpan | idle | Lundi, salade. Mardi, salade.
- tension | worried | hold-chest | Mercredi, il passe devant une boulangerie. Il résiste. Il résiste encore.
- retournement | laughing | thumbs-up | Il ressort avec une salade. Et un éclair au chocolat, pour accompagner la salade.

## H16 | vie quotidienne | salon | La plante en plastique
- accroche | sad | slump | Gérard a fait mourir toutes ses plantes.
- mise en place | happy | hold-up | Alors il en achète une en plastique. Enfin tranquille.
- tension | worried | think | Elle a l'air triste. Il l'arrose quand même, par principe.
- retournement | shocked | recoil | La semaine suivante, elle a moisi. Gérard a réussi l'impossible.

## H17 | vie quotidienne | rue | Le raccourci
- accroche | skeptical | arms-crossed | Gérard ne fait pas confiance à son GPS.
- mise en place | smug | point | Le GPS dit à gauche. Gérard va à droite : il connaît un raccourci.
- tension | worried | shrug | Une heure plus tard, il est au milieu d'un champ. Une vache le regarde.
- retournement | embarrassed | facepalm | Le GPS annonce, calmement : « Vous êtes arrivé. » Gérard ne saura jamais s'il se moque de lui.

## H18 | vie quotidienne | chambre | Le réveil
- accroche | shocked | recoil | Gérard s'est réveillé en retard !
- mise en place | worried | arms-up | Il saute dans son pantalon, avale son café, court jusqu'à l'arrêt de bus.
- tension | smug | hands-on-hips | Le bus arrive. Il monte, essoufflé, fier de lui.
- retournement | embarrassed | facepalm | Le chauffeur le regarde : on est dimanche.

## H19 | vie quotidienne | bureau | Le mot de passe
- accroche | angry | hands-on-hips | Gérard a oublié son mot de passe.
- mise en place | thinking | think | Il clique sur « mot de passe oublié » et en choisit un nouveau.
- tension | annoyed | arms-crossed | Le site refuse : il doit être différent de l'ancien.
- retournement | confused | shrug | Gérard est maintenant sûr d'une chose : il s'en souvenait, de l'ancien.

## H20 | vie quotidienne | parc | Le parapluie
- accroche | smug | hold-up | Gérard ne sort jamais sans son parapluie.
- mise en place | deadpan | idle | Soleil, ciel bleu, pas un nuage : le parapluie vient quand même.
- tension | shocked | recoil | Le seul jour où il l'oublie, un orage éclate.
- retournement | laughing | arms-up | Gérard rentre trempé, ravi : il avait raison depuis le début.
