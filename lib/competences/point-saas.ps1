# Compétence : « point SaaS » : le point sur Trouve ton produit (site, quiz, e-mails, abonnés, chiffre d'affaires, tâches) à partir des seules sources branchées (lib\saas.ps1). Aucun chiffre inventé, aucun avis financier.
Add-Action 'point_saas' 1 'point sur le SaaS' 'point_saas() : point sur le SaaS Trouve ton produit (site, quiz, e-mails, abonnés, chiffre d''affaires, tâches ouvertes) ; sources non branchées signalées' {
    param($a)
    if (Get-Command Get-SaasDonnees -ErrorAction SilentlyContinue) {
        $d = Get-SaasDonnees
        if ($script:CanalDiscord -and (Get-DiscordStyle) -eq 'embed') { Add-EmbedDiscord (New-EmbedSaas $d); return (Rep $true '') }
        return (Rep $true (Get-SaasTexte $d))
    }
    $b = $null; try { $b = & $script:Actions['business_etat'].run $a } catch { }
    $txt = ''
    if ($b -and $b.donnees) { $txt = ("$($b.donnees)" -replace "?
", ' ').Trim() } elseif ($b) { $txt = "$($b.texte)" }
    $t = @(); try { $t = @(Get-TodoOuverte | Where-Object { $_ -match '(?i)saas|trouve ton produit|tonproduit|quiz|stripe|supabase|site' }) } catch { }
    $txt = ($txt + ' ' + $(if ($t.Count) { "Tâches SaaS ouvertes : $($t -join ' ; ')." } else { 'Aucune tâche SaaS ouverte.' })).Trim()
    Rep $true $txt
} { param($a) 'faire le point sur le SaaS' }
