---
name: track-progress
description: "Pousse l'avancement V1 (un seul nombre, lu dans la projection) dans un seul champ d'une seule page du tracker Notion. Écrit : notion (un champ). Aucune notification."
meta:
  kind: routine
  scope: mission
  schedule: config          # routines.yml > routines.<projet>-track-progress.schedule (ex. 8h/11h/18h)
  chains: [projection]
  writes: [notion]
  validation: none          # un seul champ, idempotent : rien n'est écrit s'il est déjà à jour
  default_mode: apply       # routine planifiée ; --dry-run pour un essai
  output: chat-md
  notifies: none
  mcp_deps: [notion]
  status: stable
---

# track-progress - avancement V1 dans le tracker

**Une seule tâche : mettre à jour l'avancement V1 dans le tracker Notion.** Un seul champ, une seule page.

## Déclencheur et modes

Planifiée (`schedule` de l'instance). `--dry-run` (ou « à blanc ») : on lit et on dit la valeur qui
serait écrite, sans écrire.

## Entrées

Clé d'instance `routines.<projet>-track-progress` ; à défaut, l'ancienne clé (voir `framework/routines/README.md`, colonne « Anciennement »).

Instance `routines.<projet>-track-progress` : `tracker.page_id`, `tracker.field`.

## Enchaînements

`chains: [projection]` : pourcentage V1 (reste / charge), en lecture seule.

## Déroulé

0. **Préflight** : `python3 framework/pm.py run preflight <mission>`, puis `notion-get-self` :
   `workspace.id` + `workspace.name` == profil. BLOQUANT ou identité différente : on n'écrit pas, on
   rend la valeur dans le rapport.
1. **Lire** : `python3 framework/pm.py run projection <mission>` ; retenir `v1_pct`.
2. **Comparer** : lire `tracker.field` sur `tracker.page_id`. La valeur cible est `v1_pct / 100`
   (nombre 0..1). **Si le champ est déjà à jour, ne rien écrire.**
3. **Écrire** le seul champ `tracker.field` de la seule page `tracker.page_id`.
4. **Vérifier** : relire le champ.

## Sortie

Une ligne : valeur avant -> après, ou « déjà à jour ».

## Garde-fous

- `notifies: none`. Écriture d'un **seul champ** sur une **seule page** ; jamais une autre page, jamais
  une mention, jamais un déplacement de page (hook `garde_suppression.py`).
- N'écrit rien d'autre. Respecte `writes[].guard` de l'instance.
