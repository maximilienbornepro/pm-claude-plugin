---
name: align-sprint-goals
description: "Dépréciée - pointeur vers publish-projection en mode goals-only (aligne les objectifs des sprints Jira sur le JSON éditorial, aucun ticket déplacé). Écrit : objectifs de sprint Jira (champ texte). Aucune notification."
meta:
  kind: routine
  scope: mission
  schedule: config          # manuel ; garder l'instance existante, ou passer à <projet>-publish-projection mode goals-only
  chains: []
  writes: [jira]
  validation: none
  default_mode: apply       # comme publish-projection, mode goals-only
  output: chat-md
  notifies: none
  mcp_deps: []
  status: draft             # dépréciée : conservée pour les tâches déjà enregistrées qui pointent ici
---

# align-sprint-goals - dépréciée, voir publish-projection (mode goals-only)

Cette routine est **fusionnée** dans `framework/routines/publish-projection/SKILL.md`, **mode
`goals-only`**. Le dossier reste pour que les tâches déjà enregistrées dans l'app qui pointent ici
continuent de fonctionner.

## Déclencheur et modes

Lancée par une tâche enregistrée (ou à la main) : appliquer exactement
`framework/routines/publish-projection/SKILL.md`, **mode `goals-only`**, pour la mission donnée.

## Entrées

L'instance `routines.<projet>-align-sprint-goals` de `routines.yml` si elle existe (son
`commands.objectifs` et ses `writes[].guard`), sinon `routines.<projet>-publish-projection`.

## Enchaînements

Aucun : tout est porté par `publish-projection`.

## Déroulé

0. Préflight, puis étape 3 (objectifs des sprints) de `publish-projection`, rien d'autre.

## Sortie

Les sprints réalignés et ceux déjà bons.

## Garde-fous

Ceux de `publish-projection` : `notifies: none`, **aucun ticket déplacé**, n'écrit que le champ objectif
des sprints qui diffèrent du JSON.

## Décisions datées

- Fusionnée dans `publish-projection` (mode `goals-only`) ; anciennement nommée `objectifs-sprints`.
  Pour migrer une tâche enregistrée : pointer vers `publish-projection` avec « mode goals-only ».
