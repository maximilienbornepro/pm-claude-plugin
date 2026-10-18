---
name: office
description: Crée un fichier Office (xlsx) depuis un template excel du registre s'il n'existe pas, et l'édite de façon chirurgicale (ajout de ligne, cellules) s'il existe. Le pendant Excel de notion-scaffold, pour le disque OneDrive synchronisé - PAS le connecteur Microsoft 365 (lecture seule). Stdlib, sans openpyxl : compatible avec le garde-fou Office. Dry-run par défaut ; sauvegarde avant toute édition.
meta:
  produces: office-file
  consumes: [templates]
  mcp_deps: []
  cost: light
  status: stable
  writes: office
---

# Générateur office (fichiers Office, create-si-absent + chirurgical)

**Le connecteur Microsoft 365 est en lecture seule** : il ne crée ni ne modifie de fichier. Écrire dans
SharePoint se fait par le **disque OneDrive synchronisé** (le fichier posé dans le dossier local remonte
sur SharePoint). Ce générateur écrit sur ce disque, **en stdlib** (pas openpyxl, qui détruit images et
dessins et que le garde-fou `garde_office` refuse).

## Deux modes, un seul outil

- **Fichier absent → création** depuis `trackers/excel/<objet>.yml` (structure, en-têtes, exemples).
  `create-si-absent` : il ne crée que si le fichier n'est pas là.
- **Fichier présent → édition chirurgicale** via `onedrive_xlsx` : `--append` ajoute une ligne, sans
  toucher au reste (images, mises en forme préservées). **Sauvegarde horodatée d'abord**, puis **une seule
  écriture**. Jamais d'écrasement global, jamais `openpyxl`, jamais `rm`/`mv`.

## Usage

```
pm run office <mission> <objet> --out <chemin.xlsx>                    # plan (dry-run)
pm run office <mission> <objet> --out <chemin.xlsx> --apply            # crée si absent
pm run office <mission> <objet> --out <chemin.xlsx> --append "a|b|c|d" --apply   # ajoute une ligne
```

`<objet>` ∈ templates excel (`risks`, `raci`). `--out` pointe le fichier (dans le dossier synchronisé
pour remonter sur SharePoint). Les colonnes de `--append` suivent l'ordre du template.

## Placement dans un dossier synchronisé

Poser le fichier dans OneDrive/SharePoint, c'est dérouler **[_deroule-office](../_deroule-office.md)** :
fraîcheur (ne pas écrire par-dessus le travail récent d'autrui), **sauvegarde**, **une seule écriture**,
puis vérifier que la synchro est passée (taille locale ≈ SharePoint). Ce générateur fait la sauvegarde et
l'écriture unique ; la **fraîcheur** et la **validation** restent des étapes de session.

## Ce qu'il ne fait pas

- Il n'utilise **jamais** le connecteur M365 (lecture seule) ni openpyxl.
- Il n'écrase pas un fichier existant : présent = édition chirurgicale uniquement.
