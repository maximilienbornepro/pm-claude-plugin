---
name: raci
description: Génère la matrice RACI et un extrait par rôle à partir de données (profiles/<mission>/raci.yml). Rendu markdown / JSON, et plan de cellules pour l'onglet matrice. Lecture seule ; l'écriture Office reste une étape gardée.
meta:
  produces: raci-xlsx
  consumes: []
  mcp_deps: [m365]
  cost: light
  writes: office
  status: stable
---

# Générateur raci

La RACI devient **data-driven** : une seule source de vérité, `profiles/<mission>/raci.yml`, et le
générateur en rend la **matrice** et un **extrait par rôle** (les « onglets »). Fini le patch à la main
d'un classeur à 13 onglets.

## Données (`raci.yml`)
- `roles` : colonnes de la matrice, dans l'ordre, avec `col` (libellé), `tab` (onglet) et `letter` (colonne Excel).
- `activities` : lignes, en **flow inline** (le parseur sans-dépendance ne lit pas les dicts en bloc) ; les
  clés de rôle sont **directes** sur chaque activité (`enix: R`, `esre: A`...). **Pas de virgule** dans les
  chaînes (utiliser `/` ou `;`). Valeurs : `R` / `A` / `C` / `I` / `A/R` / `-`.

## Usage
```
python3 framework/pm.py run raci <mission>            # matrice (markdown) + un extrait par rôle
python3 framework/pm.py run raci <mission> --json     # tout en JSON
python3 framework/pm.py run raci <mission> --role Enix # un seul rôle
python3 framework/pm.py run raci <mission> --cells    # plan de cellules pour l'onglet matrice
```

## Écriture dans le classeur (gardée, en session)
Le générateur **n'écrit pas** dans le fichier Office. L'application suit le **déroulé commun Office**
(`framework/generators/_deroule-office.md`), via le helper `framework/harness/onedrive_xlsx.py`.
Spécifique ici :
- `--cells` donne, par activité, la **colonne → lettre R/A/C/I** + le libellé en colonne A, pour l'onglet
  `matrix_sheet`, aux lignes libres après `first_activity_row`.
- Les **onglets de rôle** sont des extraits : on les régénère depuis le rendu `--role` (mêmes sections
  R/A/C/I). Tant qu'il n'y a pas de rebuild complet du classeur stylé en session (openpyxl indisponible),
  on met à jour l'onglet matrice et on régénère les onglets de rôle à la main depuis la sortie.

## Garde-fous
Rien n'est écrit sans validation ; jamais d'écriture Office hors du helper ; fraîcheur SharePoint vérifiée
avant toute écriture (voir le déroulé commun).
