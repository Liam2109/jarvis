# Compétence : « point SaaS » — statistiques du SaaS (Supabase, Stripe, état du site : action business_etat) + tâches SaaS ouvertes de la to-do. Aucun avis financier.
Add-Action 'point_saas' 1 'point sur le SaaS' 'point_saas() : point sur le SaaS Trouve ton produit (statistiques Supabase / Stripe / état du site) et les tâches SaaS ouvertes de la to-do' {
    param($a)
    $b = $null; try { $b = & $script:Actions['business_etat'].run $a } catch { }
    $txt = ''
    if ($b -and $b.donnees) { $txt = ("$($b.donnees)" -replace '?
', ' ; ').Trim() } elseif ($b) { $txt = "$($b.texte)" }
    $t = @(); try { $t = @(Get-TodoOuverte | Where-Object { $_ -match '(?i)saas|trouve ton produit|tonproduit|quiz|stripe|supabase|site' }) } catch { }
    $txt = ($txt + ' ' + $(if ($t.Count) { "Tâches SaaS ouvertes : $($t -join ' ; ')." } else { 'Aucune tâche SaaS ouverte.' })).Trim()
    Rep $true $txt
} { param($a) 'faire le point sur le SaaS' }
