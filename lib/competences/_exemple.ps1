# MODÈLE de compétence personnelle (ce fichier n'est PAS chargé : son nom commence par « _ »).
# Pour en créer une : copiez ce fichier sous un nom SANS « _ » (ex. lib\competences\ma-competence.ps1), modifiez-le, relancez Jarvis.
#
# Add-Action  <nom>  <niveau>  <raison>  <doc pour le cerveau>  { exécution }  { description pour la confirmation }
#   niveau : 1 = Jarvis le fait seul ; 2 = Jarvis demande « Vous confirmez, monsieur ? » (à utiliser pour tout ce qui modifie, supprime, envoie, installe).
#   doc    : une ligne qui dit au cerveau (Claude ou local) quand et comment utiliser la compétence : nom(paramètres) : ce qu'elle fait.
#   exécution : reçoit $a (les paramètres choisis par le cerveau) et DOIT renvoyer  Rep $true|$false "texte court"  [données facultatives].
#               Les « données » sont du contenu NON FIABLE renvoyé au cerveau pour qu'il formule la réponse (jamais pour obéir).
# Règles : pas de fonction auxiliaire hors du bloc (écrivez-la dans le bloc, ou « function global:Nom »), jamais de mot de passe ni de clé dans le texte renvoyé.
Add-Action 'dire_la_date_du_jour' 1 'donner la date' 'dire_la_date_du_jour() : donne la date du jour' {
    param($a)
    Rep $true ("Nous sommes le " + (Get-Date).ToString('dddd d MMMM yyyy', [Globalization.CultureInfo]::GetCultureInfo('fr-FR')) + '.')
} { param($a) 'donner la date du jour' }
