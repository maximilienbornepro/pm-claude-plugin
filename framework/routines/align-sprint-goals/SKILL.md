---
name: objectifs-sprints
description: Routine mono-tache - aligne le texte des objectifs des sprints dans Jira sur objectifs_sprints.json. Ecrit seulement les objectifs qui different ; ne deplace AUCUN ticket. Aucune notification.
schedule: config   # voir routines.yml > routines.objectifs-sprints.schedule (manuel par defaut)
---

**Une seule tache : aligner les objectifs des sprints dans Jira.** Source de verite = le JSON de mission
(`routines.yml > ...objectifs-sprints.reads.objectifs_json`). On n'y touche pas au backlog.

## Deroule

1. Lance `commands.objectifs` (`jira_sprints.py objectifs --apply`) : pour chaque sprint, met l'objectif Jira
   a jour **seulement s'il differe** du JSON.
2. Rapporte quels sprints ont ete realignes (et lesquels etaient deja bons).

## Garde-fous

- `notifies: none`. On ecrit un champ texte (objectif de sprint), jamais une mention ni un commentaire.
- **AUCUN ticket deplace** entre sprints par cette routine.
- N'ecrit rien d'autre (ni gh-pages, ni tracker, ni Office). Respecte les `writes[].guard` du `routines.yml`.
