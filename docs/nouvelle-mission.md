# Créer une nouvelle mission en 10 minutes

Le framework a deux couches : un **moteur générique** (`framework/`) et un **profil par mission**
(`profiles/<mission>/`). Monter une nouvelle mission = **remplir un profil**, jamais toucher au moteur.

## 1. Copier le profil de référence (1 min)

```bash
cp -r profiles/sinbad profiles/<mission>
```

Puis vider / adapter les données propres à SINBAD (garder la structure des fichiers).

## 2. Remplir `profiles/<mission>/profile.yml` (3 min)

- `name`, `lang`.
- `jira` : `instance`, `cloud_id`, `project_key`, `board`.
- `notion` : `project_management_root`, `workspace_root`.
- `drive` : `web_site`, `root` (chemin local synchronisé), `sync`.
- `identity` : `palette` (voir étape 4), `logos`.
- `key_dates` : `t0`, `code_freeze`, `mep`.
- `team` : noms / rôles (pour le RACI).

## 3. Adapter `pipeline.yml` et les configs de générateurs (3 min)

- `pipeline.yml` : pour chaque livrable, `generator` + `tone` + `schema_style` + `targets`
  (**rappel : toute cible `gh-pages` est doublée d'un `artifact`**, voir `FRAMEWORK.md`). Table `agents` :
  ton par agent.
- Les `*.yml` par générateur : `projection.yml` (capacité/staff, epics-pôles, règles de versions),
  `risks.yml` (fichier registre + schéma), `jira_ticket.yml` (section image, racine des images),
  `suivi.yml` (transcripts, store, DB privée), `routines.yml` (horaires, commandes, écritures gardées).

## 4. Identité : palette et logos (1 min)

- `profiles/<mission>/palette.json` : couleurs de marque + sémantiques + thèmes.
- `profiles/<mission>/logos/` : logos des entités (embarqués dans le schéma d'archi).

## 5. Brancher l'accès et vérifier (2 min)

- `PMF_JIRA_ENV=<.env avec le jeton>` (jamais dans le dépôt), `PMF_PROJECT_ROOT`, `PMF_SYNC_MARKER` si
  la racine synchronisée n'est pas « OneDrive ».
- Vérifier en lecture seule :

```bash
python3 framework/pm.py missions
python3 framework/pm.py list
python3 framework/pm.py run projection <mission>        # dry-run / lecture seule
```

## 6. (Ré)activer les routines

Demander à Claude : « enregistre les routines de `framework/routines` selon leur `schedule` dans
`profiles/<mission>/routines.yml` ». Détails et règles : `framework/routines/README.md`.

## Garde-fous qui restent actifs d'office

- `framework/hooks/` branchés par `.claude/settings.json` : `garde_office` (écriture Office),
  `garde_suppression` (rm/mv Drive + déplacement Notion), `pas_ecraser_jira`, `journal_usage`.
- Règles d'or : on ne refactore pas la mission d'origine en place ; on n'écrase jamais l'existant
  (idempotence) ; aucune notification sans validation (voir `framework/NOTIFICATIONS.md`).
