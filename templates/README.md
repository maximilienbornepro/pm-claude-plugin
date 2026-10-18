# Registre des templates

Les templates décrivent, **en donnée**, les objets de pilotage d'une mission - suivi des sujets,
planning, RACI, registre des risques - pour chaque **solution de suivi** (Notion, Excel, ClickUp…).
Génériques : le moteur ne porte **aucune valeur de mission**. Une mission redéfinit ses propres
options (états, thématiques, barèmes…) dans son profil.

## Deux axes : solution × objet

```
templates/
├── project-management-tree.yml   # l'arborescence : où se place chaque page / base
└── trackers/
    ├── notion/   sujets.yml · planning.yml · raci.yml · risks.yml
    ├── excel/    raci.yml · risks.yml
    └── clickup/  (à prévoir - voir son README)
```

- **Organisé par solution** : ajouter une solution = ajouter un dossier `trackers/<solution>/` avec
  ses objets. Le profil choisit la solution : `profile.yml > pm_tracker: notion | excel`.
- **Un fichier par objet et par solution** : `trackers/<solution>/<objet>.yml`.

## Le format, par solution

**Notion** (base = data source) :
- `title` · `properties` (liste `"Nom:type"`, type ∈ title/text/select/date/number/person)
- `options` (map : pour chaque select, ses valeurs - les **états**, **thématiques**, priorités…)
- `views` (liste de vues : table / board / timeline, avec `group_by` / `filter` / `sort`)
- une liste d'**exemples** (insérés à la création) nommée comme l'objet (`sujets`, `risques`…).

**Excel** (base = feuille) :
- `title` · `sheet` · `columns` (ou `layout: matrix` pour le RACI) · `legende` (valeurs des colonnes
  à choix) · `exemples`.

## Cohérences

- **Risques** : les options Probabilité / Impact viennent du barème `method.yaml > baremes.risque`
  (axe A4). Les valeurs ici ne sont qu'un **défaut générique**.
- **Les vraies valeurs de mission** (thématiques réelles, états, barèmes) vivent dans le profil, pas
  ici. Ces templates sont le squelette commun, clonable.

## Lister / inspecter

`pm run templates` liste les templates disponibles (objet × solution) ; `pm run templates <objet>`
en montre le détail.
