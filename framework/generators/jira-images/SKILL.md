---
name: jira-ticket
description: Generateur de tickets Jira du pm-framework - pilote par la config, deux outils ensemble (connecteur = texte, API = images). Poser, verifier ou retablir l'image d'un ticket sans jamais la perdre, sur n'importe quelle mission, en lecture seule / dry-run par defaut.
meta:
  produces: jira-images
  consumes: []
  mcp_deps: [jira]
  cost: light
  status: stable
---

# Generateur jira-ticket : le pattern deux outils

Jira se pilote ici avec **deux outils complementaires**, parce qu'aucun ne fait tout :

| Outil | Ce qu'il fait | Ce qu'il ne fait pas |
|---|---|---|
| **Connecteur Jira (Atlassian)** | edite le **texte** d'un ticket : resume, statut, assignation, libelles, liens, commentaires, et la **description** | **ne sait pas uploader de piece jointe ni poser une image** |
| **API REST (`jira_image.py`)** | **uploade** une image et la **retablit** dans la description (ADF) | n'est pas l'outil pour reecrire le texte au fil de l'eau |

On utilise donc **les deux ensemble** : le connecteur pour le texte, l'API pour l'image.

## Regle « l'image ne saute jamais »

Reecrire une description **efface la section image** (le connecteur en markdown, ou toute
reconstruction de la description, perd les medias). La regle de mission est donc :

> Apres **toute** modification d'un ticket, on re-verifie l'image (`check`) et, si elle a saute,
> on la **remet** (`--apply`).

Deux garde-fous portent cette regle :

- **Garde-fou texte** (`framework/hooks/pas_ecraser_jira.py`) : un hook `PreToolUse` refuse que le
  connecteur ecrive une **description** - il remplace la version courante sans la relire et peut
  effacer le travail de quelqu'un. Le connecteur reste bon pour statut, resume, assignation,
  libelles, liens, commentaires. (Auteurs proteges informatifs via `PMF_JIRA_PROTECTED`.)
- **Garde-fou image** (`jira_image.py`, cle `guard_media_single`) : avant un `PUT` de description,
  le nombre de `mediaSingle` (images) ne doit **pas baisser** par rapport a la version lue, sinon
  l'ecriture est refusee. Une image ne peut pas disparaitre a cause d'une repose.

## Lecture seule / dry-run par defaut

`jira_image.py` **n'ecrit jamais** sauf flag explicite `--apply`. Trois modes :

```bash
# Jira (base, identifiants) : comme framework/lib/jira.py
#   JIRA_EMAIL / JIRA_TOKEN dans l'env, ou PMF_JIRA_ENV pointant un fichier .env (ex. scan-jira/.env).
cd framework/generators/jira_ticket

python3 jira_image.py <mission> --dry-run [CLE ...]     # 0. liste ticket -> image, AUCUN appel Jira
PMF_JIRA_ENV=.../.env \
  python3 jira_image.py <mission> [CLE ...]             # 1. CHECK (defaut) : l'image est-elle en place ? GET seul
PMF_JIRA_ENV=.../.env \
  python3 jira_image.py <mission> --apply [CLE ...]     # 2. ECRIT : upload + repose (sur accord explicite)
```

Marche a suivre : **toujours** `--dry-run` puis `check`, **montrer le resultat a l'utilisateur**,
et ne lancer `--apply` **qu'apres son accord**, en ciblant les tickets valides. Sans cle, tous les
tickets ayant une image locale sont pris. Idempotent : `--apply` ne touche qu'aux tickets dont
l'image manque ou differe ; il ne supprime jamais une piece jointe.

## Ce que la config pilote

Rien n'est code en dur. La mission vit dans `profiles/<mission>/jira_ticket.yml`
(gabarit commente : `jira_ticket.example.yml`). Cles de la section `image` :

| Cle | Role |
|---|---|
| `section_title` | titre de la section ou l'image est posee, cree s'il manque (SINBAD : « Figma / Prototype ») |
| `section_match` | sous-chaine minuscule pour **retrouver** un titre deja present, meme reformule (`figma`) |
| `images_root` | dossier racine des images, parcouru recursivement (SINBAD : `scan-jira/images`) |
| `file_glob` | motif des fichiers image (`SIN-*.png`) |
| `key_pattern` | regex lisant la **cle** du ticket dans le prefixe du nom de fichier (`'SIN-\d+'`) |
| `pick` | choix si plusieurs fichiers pour un ticket : `most_recent_mtime` (le plus recent gagne) |
| `content_type` | type MIME a l'upload (`image/png`) |
| `guard_media_single` | garde-fou « l'image ne saute jamais » (nb de mediaSingle non decroissant) |

Le Jira lui-meme (base, projet, board, identifiants) **n'est pas** dans ce fichier : il vient du
**profil** (`profiles/<mission>/profile.yml`) et de l'**env**, exactement comme `framework/lib/jira.py`.

### Convention de nommage (portee par la config)

- Une image **par ticket**, rangee dans un sous-dossier au nom du ticket :
  `<images_root>/<CLE>/<CLE>_<slug>.png`. Le nom **commence** par la cle (lue par `key_pattern`).
- L'image est identifiee par son **nom de fichier**. Une **nouvelle version doit porter un nouveau
  nom** (horodate), sinon le ticket est juge a jour et l'ancienne piece jointe du meme nom est
  reutilisee. C'est pourquoi les captures sont horodatees.

## Faire evoluer sans toucher au code

- **Autre mission** : copier `jira_ticket.example.yml` vers `profiles/<mission>/jira_ticket.yml`,
  renseigner `images_root`, `key_pattern` (ex. `'ABC-\d+'`) et au besoin `section_title`. Le profil
  (`profile.yml`) fournit deja le bon Jira. Aucune ligne de code a changer.
- **Autre titre de section** : changer `section_title` / `section_match`.
- **Autre format d'image** : `file_glob` + `content_type`.

## Detail technique (pour debugger)

- L'image est inseree en **ADF** sous le titre `section_title`. L'ADF exige l'**UUID Media Services**
  de la piece jointe (pas son id numerique) : il est lu dans la redirection **303** de
  `/rest/api/3/attachment/content/<id>`. L'id numerique donne `ATTACHMENT_VALIDATION_ERROR`.
- **401** : identifiants invalides (env / `.env` vise par `PMF_JIRA_ENV`).
- **`uuid introuvable`** : la piece jointe n'a pas encore ete traitee par Media Services, relancer
  apres quelques secondes.

## A confirmer

- SINBAD d'origine fait evoluer le titre de section vers « Rendu » (deux captures V1/V2) sur les
  tickets front. Ici `section_title` reste « Figma / Prototype » par defaut, pilotable par la config :
  arbitrer le titre cible de la mission avant une passe `--apply`.
- Le pendant **capture** (regenerer les PNG du POC) reste cote mission (SINBAD : skill `poc-captures`).
  Ce generateur ne couvre que la pose/verification de l'image, pas sa production.
