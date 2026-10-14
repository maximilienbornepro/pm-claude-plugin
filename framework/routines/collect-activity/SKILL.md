---
name: suivi
description: Routine config-driven - transforme les requetes Claude Code du jour (celles ayant modifie le projet) en activites datees, versees dans un store local et une DB Notion PRIVEE, et en bloc Weekly report (modele actuel). Lecture des transcripts, ecriture uniquement locale + DB privee. Aucune notification.
schedule: config   # voir routines.yml > routines.suivi.schedule (quotidien par defaut, 19h)
---

Tient le **suivi d'activite** de Maximilien a partir de ses **requetes Claude Code** : chaque jour, les
prompts qui ont **modifie le projet** deviennent des activites datees, rangees dans un store local et une
**DB Notion privee**, et resumables en bloc **Weekly report** (modele actuel). Reponds dans la langue du
profil (`profile.yml > lang`).

Tout le propre-a-la-mission (dossier des transcripts, store, lien Suivi des sujets, id de la DB privee) vit
dans **`profiles/<mission>/suivi.yml`**, lu via `routines.yml > routines.suivi.reads.suivi_yml`. Ce SKILL
porte le deroule et les garde-fous. **Racine projet** : resolue de facon portable (`routines.yml >
project_root_env`).

## Ce qu'elle enchaine

`chains: [suivi]` - le generateur `framework/generators/suivi/` : `collect.py` (lecture des transcripts),
le store `activites.jsonl`, `build_weekly.py` (rendu Weekly report) et `sync_notion.py` (upsert DB privee).

## Etape 1 : collecter les prompts pertinents du jour

`collect.py --project-dir <suivi.project_dir> --date <jour>` liste les prompts **pertinents** = suivis, avant
le prompt suivant, d'au moins une action modifiante (Write/Edit, publication sync_*.sh/publish.sh/Artifact,
git commit/push, ecriture Jira, ecriture Notion, Office/Drive, Teams/Outlook). Les lectures, audits,
`--dry-run`/`--check` et apercus scratchpad sont ignores. La sortie est un **brouillon**.

## Etape 2 : curer en activites

Pour chaque prompt garde, ecrire **une activite courte et factuelle** : `{date, type, theme, texte, lien?,
projet}`. `type` parmi les 4 categories : **produit** (ce que j'ai produit), **attendu_moi** (ce qu'on attend
de moi), **attends_autres** (ce que j'attends des autres), **bloquant** (ce qui me bloque). Ne garder que ce
qui merite d'etre suivi ; fondre les doublons. Ajouter les lignes au store (`suivi.store`).

## Etape 3 : rendre le bloc Weekly report (optionnel, sur demande)

`build_weekly.py --store <suivi.store> --week <jour> --suivi-link <suivi.suivi_link>` rend le bloc au modele
actuel (produit -> Activites realisees ; bloquant -> Difficultes ; attends_autres -> Ce qui manque ;
attendu_moi -> Plan d'action). **Le report dans la page Weekly report partagee a Greg reste manuel** : la
routine ne l'ecrit jamais.

## Etape 4 : synchroniser la DB privee

`sync_notion.py --store <suivi.store> --db <suivi.notion_db>` (ou via le connecteur MCP si pas de
`NOTION_TOKEN`). Upsert par cle `date|texte` : aucun doublon, rien n'est supprime.

## Etape 5 : rapporter

Trois lignes maximum : nombre de prompts pertinents trouves, nombre d'activites ajoutees au store, nombre de
pages creees dans la DB privee ; toute anomalie.

## Garde-fous

- **`notifies: none`** : la DB est **privee** (espace prive de l'utilisateur), elle ne notifie personne. Pas
  de mail, pas de mention, pas de commentaire, pas de Teams.
- **Ecritures limitees** au store local et a la DB privee (`suivi.notion_db`). **Jamais** la page Weekly
  report de Greg, jamais une autre page/base Notion, jamais Office/Jira.
- **Lecture seule des transcripts.** Le collecteur ne modifie rien.
- Ne garder que les prompts **ayant reellement modifie le projet** ; le reste est du bruit.
- Respecter chaque `routines.yml > ...suivi.writes[].guard`.
