---
name: audit-scope
description: "Audite le périmètre V1/V2 et la couverture des exigences contre Jira, et la cohérence du plan de sprints ; ne fait que proposer, cellule par cellule. Lecture seule. Aucune notification."
meta:
  kind: routine
  scope: mission
  schedule: config          # routines.yml > routines.<projet>-audit-scope.schedule (manuel par défaut)
  chains: [jira-sprints-audit]
  writes: []
  validation: none
  default_mode: read-only
  output: chat-md
  notifies: none
  mcp_deps: []              # Jira par le générateur et les commandes de mission (jeton hors dépôt)
  status: stable
---

# audit-scope - auditer le périmètre et le plan de sprints

**Une seule tâche : auditer, en lecture seule.** On compare le réel (Jira) aux références de mission et
on **propose** des corrections, sans jamais écrire. Réponds dans la langue du profil.

## Déclencheur et modes

Manuel par défaut (« Run now » ou à la demande), planifiable via `schedule`. Un seul mode : lecture seule.

## Entrées

Clé d'instance `routines.<projet>-audit-scope` ; à défaut, l'ancienne clé (voir `framework/routines/README.md`, colonne « Anciennement »).

Instance `routines.<projet>-audit-scope` de `profiles/<mission>/routines.yml` :

- `reads.perimetre_json` : la référence de périmètre (V1/V2) et de couverture des exigences ;
- `reads.profile` : au moins `jira.board` ;
- `commands.scope` : audit du périmètre et de la couverture (optionnel, commande de mission) ;
- `commands.audit` : écarts plan / Jira (optionnel, commande de mission).

## Enchaînements

`chains: [jira-sprints-audit]` : cohérence plan de sprints / board Jira, en lecture seule.

## Déroulé

1. **Lire** : `python3 framework/pm.py run jira-sprints-audit <mission>` : charge par sprint, tickets
   sans estimation, blocages inversés, dates.
2. **Comparer** (si `commands.scope`) : périmètre V1/V2 et couverture des exigences contre Jira, à partir
   de `reads.perimetre_json`.
3. **Comparer** (si `commands.audit`) : écarts plan / Jira (backlog à ranger, versions en désaccord).
4. **Proposer** : des corrections **cellule par cellule** (feuille, ligne, colonne, avant -> après), et
   les écarts de plan. Rien n'est écrit.

## Sortie

Tableau des écarts et propositions dans la conversation (Markdown).

## Garde-fous

- `notifies: none`. **Aucune écriture** : que des propositions. Les écritures Office (périmètre,
  couverture) se font, après validation, par la revue dédiée et le harness Office - pas ici.
- `writes: []` dans l'instance ; une ligne `office` n'y figure que comme propositions.
