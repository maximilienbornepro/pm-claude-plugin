---
name: publication-projection
description: Routine mono-tache - publie le rapport de projection ET le plan de sprints sur gh-pages, puis republie le meme HTML sur les artefacts Claude (les deux a jour). Lecture Jira pour construire, ecriture gh-pages + artefact uniquement. Aucune notification.
schedule: config   # voir routines.yml > routines.publication-projection.schedule
---

**Une seule tache : publier.** Le rapport de projection et le plan de sprints sont deux pages couplees
(meme instantane Jira) ; les publier est donc une seule tache. Reponds dans la langue du profil.

## Deroule

1. Lance `commands.publish` (`sync_plan.sh`) : regenere et pousse rapport + plan sur gh-pages, sur un seul
   instantane Jira (chiffres identiques). **Garde** : push uniquement s'il y a une evolution ; le jeton Jira
   n'apparait jamais dans les pages.
2. **Regle gh-pages + artefact** : si un push a eu lieu, republie le **meme HTML** sur les artefacts de
   `routines.yml > ...artifacts` (`rapport`, `plan`). Recupere le HTML publie
   (`git show origin/gh-pages:rapport-avancement/index.html` et `:plan-sprints/index.html`) et publie chacun
   sur son URL d'artefact fixe. Jamais l'un sans l'autre. Si "aucune evolution", rien a republier.

## Garde-fous

- `notifies: none`. Artefacts prives : aucune notification.
- N'ecrit que gh-pages et les 2 artefacts. **Pas** d'objectifs Jira, **pas** de tracker, **pas** d'audit :
  ce sont d'autres routines (`objectifs-sprints`, `avancement-tracker`, `audit-perimetre`).
- Respecte chaque `routines.yml > ...publication-projection.writes[].guard`.
