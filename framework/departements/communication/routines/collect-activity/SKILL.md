---
name: collect-activity
description: "Transforme les requêtes Claude Code du jour qui ont modifié le projet en activités datées, versées dans un store local et une DB Notion privée, et résumables en bloc Weekly report. Écrit : local (store), notion (DB privée). Aucune notification."
meta:
  kind: routine
  scope: mission
  schedule: config          # routines.yml > routines.<projet>-collect-activity.schedule (ex. tous les jours 19h)
  chains: [activity]
  writes: [local, notion]
  validation: none          # upsert idempotent dans une DB privée ; rien n'est supprimé
  default_mode: apply       # routine planifiée ; la sync reste en dry-run sans --apply
  output: chat-md
  notifies: none
  mcp_deps: [notion]        # repli si NOTION_TOKEN est absent
  status: stable
---

# collect-activity - suivi d'activité du jour

Tient le **suivi d'activité** de l'utilisateur à partir de ses **requêtes Claude Code** : chaque jour,
les prompts qui ont **modifié le projet** deviennent des activités datées, rangées dans un store local et
une **DB Notion privée**, et résumables en bloc **Weekly report** (modèle actuel). Réponds dans la
langue du profil (`profile.yml > lang`).

## Déclencheur et modes

- **Planifiée** (quotidienne) : étapes 0 à 4 et 6.
- **Weekly** (sur demande) : étape 5, rendu du bloc Weekly report.
- `--dry-run` (ou « à blanc ») : collecte et curation rendues en texte ; ni store ni DB modifiés.

## Entrées

Clé d'instance `routines.<projet>-collect-activity` ; à défaut, l'ancienne clé (voir `framework/routines/README.md`, colonne « Anciennement »).

- Instance `routines.<projet>-collect-activity` : `reads.activity_yml` (par défaut
  `profiles/<mission>/activity.yml`), `writes[].guard`, et les clés de mission commentées dans
  `routines.example.yml` (ex. `weekly_report_owner`).
- `profiles/<mission>/activity.yml` (gabarit : `framework/departements/communication/generators/activity/activity.example.yml`) :
  `project_dir` (transcripts), `store`, `suivi_link`, `weekly_report_page`, `notion_db`, `themes`.
- Racine projet : `routines.yml > project_root_env`, puis replis.

## Enchaînements

`chains: [activity]` : le générateur `framework/departements/communication/generators/activity/` (`collect.py` lit les transcripts,
store `activites.jsonl`, `build_weekly.py` rend le Weekly report, `sync_notion.py` fait l'upsert dans
la DB privée), lancé par `python3 framework/pm.py run activity <mission> <sous-commande>`.

## Déroulé

0. **Préflight** : `python3 framework/pm.py run preflight <mission>`, puis `notion-get-self` :
   `workspace.id` + `workspace.name` == profil. BLOQUANT ou identité différente : pas de sync Notion
   (étape 4 sautée, dite dans le rapport) ; le store local reste alimenté.
1. **Lire** les prompts pertinents du jour :
   `python3 framework/pm.py run activity <mission> collect --date <jour>`. Pertinent = suivi, avant le
   prompt suivant, d'au moins une action modifiante (Write/Edit, publication sync/publish/Artifact, git
   commit/push, écriture Jira, Notion, Office/Drive, Teams/Outlook). Lectures, audits,
   `--dry-run`/`--check` et aperçus scratchpad sont ignorés. La sortie est un **brouillon**.
2. **Curer en activités** : pour chaque prompt gardé, **une activité courte et factuelle**
   `{date, type, theme, texte, lien?, projet}`. `type` parmi 4 catégories : **produit** (ce que j'ai
   produit), **attendu_moi** (ce qu'on attend de moi), **attends_autres** (ce que j'attends des autres),
   **bloquant** (ce qui me bloque). Ne garder que ce qui mérite d'être suivi ; fondre les doublons.
3. **Écrire le store** : ajouter les lignes au store (`activity.yml > store`), puis
   `python3 framework/pm.py run activity <mission> check`.
4. **Synchroniser la DB privée** : `python3 framework/pm.py run activity <mission> sync` (dry-run), puis
   `sync --apply` (ou le connecteur MCP si pas de `NOTION_TOKEN`). Upsert par clé `date|texte` : aucun
   doublon, rien n'est supprimé.
5. **Weekly report** (optionnel, sur demande) :
   `python3 framework/pm.py run activity <mission> weekly --week <jour>` rend le bloc au modèle actuel
   (produit -> Activités réalisées ; bloquant -> Difficultés ; attends_autres -> Ce qui manque ;
   attendu_moi -> Plan d'action). **Le report dans la page Weekly report partagée reste manuel** : la
   routine ne l'écrit jamais.
6. **Vérifier et rapporter**.

## Sortie

Trois lignes au plus : prompts pertinents trouvés, activités ajoutées au store, pages créées dans la DB
privée ; toute anomalie.

## Garde-fous

- **`notifies: none`** : la DB est **privée** (espace privé de l'utilisateur), elle ne notifie personne.
  Pas de mail, pas de mention, pas de commentaire, pas de Teams.
- **Écritures limitées** au store local et à la DB privée (`activity.yml > notion_db`). **Jamais** la
  page Weekly report partagée (`activity.yml > weekly_report_page`, tenue par `weekly_report_owner`),
  jamais une autre page ou base Notion, jamais Office ni Jira.
- **Lecture seule des transcripts.** Le collecteur ne modifie rien.
- Ne garder que les prompts **ayant réellement modifié le projet** ; le reste est du bruit.
- Respecter chaque `writes[].guard` de l'instance.

## Décisions datées

- Anciennement nommée `suivi` (routine), qui enchaînait l'alias de générateur `suivi` ; le générateur
  canonique est `activity` et sa config `profiles/<mission>/activity.yml`.
