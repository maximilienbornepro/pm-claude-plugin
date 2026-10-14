# Générateur `suivi` — suivi d'activité à partir des requêtes Claude Code

Transforme les requêtes quotidiennes (prompts Claude Code) en un suivi d'activité, rendu au **modèle
Weekly report actuel** et stocké dans une **DB Notion privée**. Quatre pièces, zéro dépendance.

## Chaîne

1. **`collect.py`** — lit les transcripts de la mission (`~/.claude/projects/<slug>/*.jsonl`) et ne garde
   que les **prompts pertinents** = ceux qui ont **produit une modification du projet** (règles plus bas).
   Sortie : un candidat d'activité par prompt (date, heure, prompt, `modifs:[...]`, session). Lecture seule.
2. **`activites.jsonl`** (dans le profil, ex. `profiles/sinbad/suivi/`) — le **store**, source de vérité.
   Une ligne = une activité : `{date, type, theme, texte, lien?, projet}`.
   `type` ∈ `produit | attendu_moi | attends_autres | bloquant` (= les 4 catégories de la DB). Ils se
   projettent sur le Weekly report : produit → Activités réalisées · bloquant → Difficultés · attends_autres
   → Ce qui manque · attendu_moi → Plan d'action.
3. **`build_weekly.py`** — rend le bloc Weekly report (modèle actuel) pour une semaine à partir du store.
4. **`sync_notion.py`** — upsert du store vers la DB Notion privée (API officielle avec `NOTION_TOKEN`,
   ou via le connecteur MCP piloté par Claude). Clé d'upsert = `(date, texte)`, rien n'est supprimé.

## Point d'entrée

`python3 framework/pm.py run suivi <mission> collect|check|weekly|sync [--apply]` : lit
`profiles/<mission>/suivi.yml`, enchaîne les briques ci-dessus. `sync` est en dry-run sans `--apply`.

## Boucle quotidienne (« à partir de maintenant »)

- `collect.py --date <jour>` → liste des prompts pertinents du jour.
- On **cure** (une activité = une phrase courte, factuelle) et on verse dans `activites.jsonl`.
- `build_weekly.py` pour le bloc hebdo (à coller/mettre à jour dans la page Weekly report, toggle daté).
- `sync_notion.py` pour alimenter la DB privée.
- Peut devenir une **routine** (voir `profiles/sinbad/routines.yml`) : collecte + proposition, aucune
  écriture sans validation (règles du projet : on montre avant d'appliquer).

## Règles de pertinence (ce qui compte comme « modification du projet »)

Un prompt est **gardé** s'il est suivi, avant le prompt utilisateur suivant, d'au moins un appel d'outil
modifiant :

- **Fichiers** : `Write`, `Edit`, `MultiEdit`, `NotebookEdit`.
- **Publication** : `Artifact` (publish/delete) ; Bash `sync_plan.sh`, `sync_pages.sh`, `publish.sh`,
  `git commit`, `git push`.
- **Jira (écriture)** : `editJiraIssue`, `createJiraIssue`, `transitionJiraIssue`, `createIssueLink`,
  commentaire, `executeWrite`/`executeDestructive` ; Bash `embed_figma.py` (hors `--check`/`--dry-run`),
  `jira_sprints.py … --apply`.
- **Notion (écriture)** : `notion-update-*`, `notion-create-*`, `notion-move-*`, `notion-duplicate-*`,
  `notion-upload-*`, `notion-restore-*`.
- **Confluence** : `createConfluence*`, `updateConfluencePage`.
- **Office / Drive** : `create_file`, `update_file`, `trash_file`, `copy_file`, `share_file` ; Bash
  `onedrive_xlsx … write`.
- **Externe** : `teams_send*`, `teams_reply*`, `teams_create_chat`.

Sont **ignorés** (non pertinents) : questions, lectures (`Read`/`Grep`/`Glob`), recherches (`*_search`,
`executeRead`), audits, `--dry-run`/`--check`, génération d'un **aperçu dans le scratchpad**, et toute
réponse qui n'a produit que du texte. La sortie de `collect.py` reste un **brouillon à curer** : elle
peut capturer un prompt de peu d'intérêt, on ne verse au store que ce qui mérite d'y être.

## DB Notion privée (schéma)

Une page = une activité. Propriétés : **Activité** (titre), **Date** (date), **Type** (select : Produit /
Attendu de moi / J'attends des autres / Bloquant), **Thème** (select), **Projet** (select), **Lien** (url).
Les 4 Type = « Ce que j'ai produit », « Ce qu'on attend de moi », « Ce que j'attends des autres », « Ce qui me bloque ».
Privée = espace privé de l'utilisateur : **ne notifie personne** (conforme à la règle « aucune notification »).

## Config

`profiles/<mission>/suivi.yml` : `store`, `project_dir`, `suivi_link`, `weekly_report_page`, `notion_db`,
`themes`. Le SINBAD d'origine reste intact : le framework lit ses propres copies.
