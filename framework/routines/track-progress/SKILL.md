---
name: avancement-tracker
description: Routine mono-tache - pousse l'avancement V1 (un seul nombre) dans un seul champ d'une seule page du tracker Notion. Lecture de la projection, ecriture d'un unique champ. Aucune notification.
schedule: config   # voir routines.yml > routines.avancement-tracker.schedule
---

**Une seule tache : mettre a jour l'avancement V1 dans le tracker Notion.** Un seul champ, une seule page.

## Deroule

1. `chains: [projection]` : lit le pourcentage V1 (reste/charge) de la projection, en lecture seule.
2. Ecrit `tracker.field` sur `tracker.page_id` (`routines.yml > ...avancement-tracker.tracker`) : la valeur
   est `v1_pct / 100` (nombre 0..1). **Si le champ est deja a jour, ne rien ecrire.**

## Garde-fous

- `notifies: none`. Ecriture d'un **seul champ** sur une **seule page** ; jamais une autre page, jamais une
  mention, jamais un deplacement de page (hook `garde_suppression.py`).
- N'ecrit rien d'autre. Respecte `routines.yml > ...avancement-tracker.writes[].guard`.
