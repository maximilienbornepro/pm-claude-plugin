---
name: reset
description: Remet à zéro ce que le framework a créé dans un dossier de projet de TEST (sous-dossiers standard + artefacts générés). Commande à fort risque : dry-run par défaut, backup horodaté obligatoire avant toute suppression, refus des chemins sensibles (OneDrive/SharePoint/SINBAD) sans --force.
meta:
  produces: null
  consumes: []
  mcp_deps: []
  cost: light
  status: stable
---

# reset (remise à zéro d'un projet de test)

Pour une phase de **test** : rejouer proprement un scaffold/une génération sans accumuler. **Commande
destructive**, encadrée :

- **Dry-run par défaut** : liste ce qui serait supprimé, ne touche à rien.
- **Backup horodaté OBLIGATOIRE** avant toute suppression (copie complète de la cible). Si le backup
  échoue, on abandonne sans rien supprimer.
- **Cibles délimitées** : seuls les **sous-dossiers standard** (`templates/project-management-tree.yml`)
  et les **artefacts générés** (`*.drawio`, `*_generated.html`) présents dans la cible. Tout le reste
  (fichiers perso, dossiers non standard) est **préservé**.
- **Refus d'un chemin sensible** (OneDrive/SharePoint synchronisé, dépôt SINBAD d'origine) sans `--force`.
- La suppression sur un Drive synchronisé reste **bloquée par le hook `garde_suppression`** (défense en profondeur).

## Usage
```
python3 framework/pm.py run reset --target <dossier de test>            # dry-run (rien supprimé)
python3 framework/pm.py run reset --target <...> --apply                # backup puis suppression
python3 framework/pm.py run reset --target <...> --apply --backup-dir <...>
python3 framework/pm.py run reset --target <...> --apply --force        # outrepasser le refus chemin sensible
```

## Garde-fous
Jamais sur un espace réel sans `--force` explicite. Le backup est la filet de sécurité : il est fait
**avant** toute suppression et conservé (chemin affiché). À n'utiliser que sur un projet de test.
