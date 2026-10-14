---
name: audit-perimetre
description: Routine mono-tache, LECTURE SEULE - audite le perimetre V1/V2 et la couverture TR contre Jira, et la coherence du plan de sprints. Ne fait que proposer (cellule par cellule) ; n'ecrit dans aucun fichier Office. Aucune notification.
schedule: config   # voir routines.yml > routines.audit-perimetre.schedule (manuel par defaut)
---

**Une seule tache : auditer (lecture seule).** On compare le reel (Jira) aux references de mission et on
**propose** des corrections, sans jamais ecrire.

## Deroule

1. `chains: [sprint-audit]` : coherence plan de sprints / board Jira (charge par sprint, tickets sans
   estimation, blocages inverses, dates) - lecture seule.
2. `commands.scope` (`audit_perimetre.py`) : perimetre V1/V2 (`Scope_V1`, `Scope_V2`) et couverture TR
   (`TR_Couverture`) contre Jira, a partir de `reads.perimetre_json`. Rend des **propositions cellule par
   cellule**.
3. `commands.audit` (`jira_sprints.py audit`) : ecarts plan/Jira (backlog a ranger, versions en desaccord).

## Garde-fous

- `notifies: none`. **AUCUNE ecriture** : que des propositions. Les ecritures Office (perimetre, couverture)
  se font, apres validation, par la revue dediee et le helper Office - pas ici.
- Respecte `routines.yml > ...audit-perimetre.writes[].guard` (target office = propositions seulement).
