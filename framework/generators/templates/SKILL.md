---
name: templates
description: Liste et montre le registre de templates (objet × solution) - suivi des sujets, planning, RACI, registre des risques, pour Notion / Excel / ClickUp. Les templates vivent dans templates/trackers/<solution>/<objet>.yml, génériques : aucune valeur de mission. Lecture seule : il affiche, il n'écrit rien. C'est le scaffold qui crée les bases à partir de ces templates.
meta:
  produces: null
  consumes: [templates]
  mcp_deps: []
  cost: light
  status: stable
---

# Générateur templates (registre de templates)

Le registre des templates de pilotage, à **deux axes** : **objet** (sujets, planning, raci, risks) ×
**solution** (notion, excel, clickup…). Chaque template décrit un objet **en donnée**, pour une
solution. Génériques : le moteur ne porte **aucune valeur de mission** ; une mission redéfinit ses
états, thématiques et barèmes dans son profil.

## Où ils vivent

```
templates/trackers/<solution>/<objet>.yml
  notion/   sujets.yml · planning.yml · raci.yml · risks.yml
  excel/    raci.yml · risks.yml
  clickup/  (à prévoir)
```

- **Notion** : `title`, `properties` (`"Nom:type"`), `options` (valeurs des selects - **états**,
  **thématiques**…), `views`, exemples.
- **Excel** : `sheet`/`columns` (ou `layout: matrix` pour le RACI), `header_rows`, `legende`, exemples.
  Les templates Excel sont calqués sur les fichiers réels d'une mission (structure, pas les données).

## Usage

```
python3 framework/pm.py run templates                      # matrice objet × solution
python3 framework/pm.py run templates <solution> <objet>   # détail d'un template
python3 framework/pm.py run templates <objet>              # l'objet pour chaque solution
```

## Cohérences

- **Risques** : les options Probabilité / Impact d'un template risques pointent vers le barème
  `method.yaml > baremes.risque` (axe A4) ; les valeurs du template ne sont qu'un défaut.
- **La solution d'une mission** se choisit dans `profile.yml > pm_tracker` (`notion` par défaut) ;
  le `scaffold` lit alors `trackers/<pm_tracker>/<objet>.yml` pour créer la base.

## Ce qu'il ne fait pas

- Il n'écrit **rien** et ne crée aucune base : il montre le registre. La création est le rôle du
  `scaffold` (create-si-absent), à partir de ces templates.
