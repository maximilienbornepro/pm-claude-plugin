---
name: trace-audit
description: Audit en lecture seule des RUPTURES de la chaîne de traçabilité d'une mission (besoin/TR → ticket → POC → test). La chaîne est déclarée en donnée dans method.yaml (bloc tracabilite : ordre, propriétaire, phase d'exigibilité) ; les items dans profiles/<mission>/tracabilite.yml. Calcule, pour la phase courante, les maillons exigibles manquants et dit OÙ ALLER (le propriétaire du maillon). Ne modifie rien.
meta:
  produces: null
  consumes: [method.yaml, tracabilite.yml]
  mcp_deps: []
  cost: light
  status: stable
---

# Générateur trace-audit (ruptures de traçabilité)

Unifie ce que disent la **matrice IADT** et le **périmètre** : la chaîne besoin/TR → ticket → POC →
test est déclarée **une fois**, en donnée, et l'audit calcule **où ça casse** et **qui doit agir**.
Détecte les trous **tôt**, avant qu'ils ne coûtent.

## Deux fichiers

- **La chaîne** (définition) : `profiles/<mission>/method.yaml` > `tracabilite` (A4) -
  `phases` (ordre des phases), `ordre` (les maillons), chaque maillon avec son `proprietaire`,
  son `exigible_des` (phase à partir de laquelle il est **obligatoire**) et un `facultatif` optionnel.
- **Les items** (données) : `profiles/<mission>/tracabilite.yml` - `phase_courante` et `items`
  (pour chaque besoin/TR, les `liens` : un maillon **relié** = valeur vraie, un identifiant comme un
  ticket compte ; absent ou `false` = manquant). En mission réelle, ce fichier est **produit par la
  synchro** (matrice IADT + `perimetre_scope.json` + Jira), pas tenu à la main.

## La règle de rupture

Pour chaque item, à la **phase courante** : un maillon est une **rupture** s'il est **exigible**
(`exigible_des` ≤ phase courante), **non facultatif**, et **non relié**. Un maillon pas encore
exigible (`·`) ou facultatif (`~`) n'est jamais une rupture. **Où aller** = le propriétaire du
**premier** maillon manquant dans l'ordre.

## Usage

```
python3 framework/pm.py run trace-audit <mission>         # vue d'ensemble (item, état, prochaine action)
python3 framework/pm.py run trace-audit <mission> <id>    # détail d'un item (chaîne maillon par maillon)
```

Marques du détail : `✓` relié · `✗` rupture · `·` pas encore exigible · `~` facultatif.

## Ce qu'il ne fait pas

- Il n'écrit **rien** : ni ticket, ni matrice, ni fichier. Il **dit où aller**, l'humain agit.
- Il ne crée pas d'item : la liste des besoins/TR vient de la mission (synchro ou `tracabilite.yml`).
