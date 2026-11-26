# Routines planifiées - framework portable

Définitions **génériques et config-driven** des routines planifiées du framework. C'est la
**source de vérité** : la tâche réellement enregistrée dans l'app n'est qu'un **pointeur mince** vers
`framework/routines/<name>/SKILL.md`. On édite le fichier du projet, jamais la copie de l'app.

Deux couches, comme le reste du framework :

- **le SKILL générique** (`framework/routines/<name>/SKILL.md`) : le déroulé et les garde-fous, sans
  aucune valeur de mission ;
- **la config de mission** (`profiles/<mission>/routines.yml`) : horaire, générateurs enchaînés,
  identifiants, chemins, périmètre des écritures. Gabarit commenté : `routines.example.yml` ; exemple
  minimal : `profiles/demo/routines.yml` (`demo-audit-scope`, lecture seule).

Changer de mission = remplir `routines.yml`, pas toucher aux SKILL ni au code.

**Nom des routines** : le **SKILL générique** vit dans `framework/routines/<name>/` (nom anglais, sans
préfixe, portable) et son frontmatter porte `name: <name>` = nom du dossier. L'**instance de mission** -
la clé dans `profiles/<mission>/routines.yml` et la tâche enregistrée dans l'app - est **préfixée du nom
du projet** (`<projet>-<name>`) et porte `skill: <name>` qui pointe vers le SKILL générique. Ainsi les
routines de deux missions ne se confondent pas dans l'app, et le moteur reste générique.

Dans l'app (section **Scheduled**), chaque tâche porte **à la fois** :
- un **`taskId`** `<projet>-<name>` (ex. `sinbad-publish-projection`) ;
- un **`title` préfixé du nom du projet en majuscules** `<PROJET> · …` (ex. « SINBAD · MAJ rapport… »). **C'est
  le `title` qui s'affiche** dans la liste : il **doit** être préfixé pour distinguer les missions d'un coup d'œil.

## Les routines

| Routine (= dossier) | Horaire (config) | Enchaîne (`chains`) | Écrit (gardé) | Validation | Anciennement |
|---|---|---|---|---|---|
| `publish-projection` | cron (ex. 8h/11h/18h) | `projection`, `jira-sprints-audit` | **gh-pages + artefacts Claude** (mêmes HTML), **objectifs des sprints** Jira (champ texte, si `commands.objectifs`) ; alerte si le texte des sprints est périmé (`commands.drift_check`, lecture seule). Mode **`goals-only`** : objectifs seuls | none | `publication-projection` |
| `align-sprint-goals` | manuel | - | **dépréciée** : pointeur vers `publish-projection` mode `goals-only` (dossier gardé pour les tâches déjà enregistrées) | none | `objectifs-sprints` |
| `audit-scope` | manuel | `jira-sprints-audit` | **lecture seule** : périmètre V1/V2 + couverture des exigences (propositions cellule par cellule) | none | `audit-perimetre` |
| `track-progress` | cron (ex. 8h/11h/18h) | `projection` | 1 champ du tracker Notion (avancement V1) | none | `avancement-tracker` |
| `collect-activity` | cron (ex. 19h) | `activity` (collect + check + sync ; weekly sur demande) | store local + DB Notion **privée** (4 catégories) ; jamais la page Weekly report partagée | none | `suivi` |
| `review-topics` | manuel | `review-risks` (sauf mode `condensation`) | base de suivi (sujets validés), page de synthèse et deck de planning (même oui), puis registre des risques via `review-risks` | chat | `revue-sujets` |
| `review-risks` | manuel (planifiable) | `risks`, `projection` | registre(s) des risques (Office, en place, après oui en séance) | chat | `revue-risques` |
| `draft-followups` | manuel | - | `.eml` locaux + fenêtre de rédaction Outlook (`mailto:`, nouveau fil) ou réponse dans le fil (presse-papiers / Outlook web) ; messages Slack internes rendus à copier ; **rien n'est envoyé ni posté** | form | `brouillons-relances` |
| `morning-digest` | cron (ex. 9h30) | - | **un seul** canal Slack privé dédié (récap du matin) + fichier d'état ; lecture seule partout ailleurs | none | - |
| `omi-sync` | cron `*/5 * * * *` (transverse, hors mission) | `omi-sync` | 2 bases Notion **perso** (pro « Notes de réunion » + perso), pages Omi classées et fusionnées ; `--unlock` à la demande seulement | none | - |

`chains` ne référence que des générateurs du framework par leur **nom canonique**
(`python3 framework/pm.py list`) ou une autre routine. L'horaire est dans le frontmatter `meta.schedule`
du SKILL (valeur `config`, qui renvoie à `routines.yml`) : le cron effectif est dans
`routines.yml > routines.<projet>-<name>.schedule`.

**Compatibilité** : une mission dont `routines.yml` ou les tâches enregistrées portent encore l'ancien
nom (colonne « Anciennement ») reste lue : à défaut de la clé `<projet>-<name>`, le SKILL lit l'ancienne
clé. Migrer = renommer la clé et le `taskId`, rien d'autre.

## Le frontmatter commun

Chaque `SKILL.md` porte le même bloc `meta` et les mêmes sections (Déclencheur et modes, Entrées,
Enchaînements, Déroulé, Sortie, Garde-fous, Décisions datées) :

```yaml
meta:
  kind: routine
  scope: mission            # mission | transverse (omi-sync)
  schedule: config          # config -> routines.yml ; sinon "<cron>"
  chains: [<générateurs canoniques>]
  writes: [gh-pages|artifact|jira|notion|office|slack|local|mail-draft]   # [] = lecture seule
  validation: none | chat | form
  default_mode: dry-run | apply | read-only   # read-only si writes == [] ; apply = routine planifiée qui écrit seule
  output: chat-md | html-widget | file:<chemin> | slack | notion
  notifies: none
  mcp_deps: [...]
  status: stable | draft
```

Le déroulé commence par **0. Préflight** dès que `writes` n'est pas vide, puis Lire, Proposer, Valider,
Écrire, Vérifier. Les décisions datées (JJ/MM) sont sorties du déroulé dans leur propre section.

## Règles permanentes (toutes, sans exception)

- **Aucune routine n'envoie de notification.** `notifies: none` sur chaque routine : jamais de mail,
  de mention `@`, de commentaire, de message Teams, de partage ni d'invitation. Avant toute opération,
  se demander qui serait notifié ; au moindre doute, on décrit et on attend. Une notification partie ne
  se rattrape pas.
- **Préflight avant toute écriture externe** : `python3 framework/pm.py run preflight <mission>`, puis
  l'identité de chaque connecteur écrit (Notion `notion-get-self`, Microsoft 365 `get_me`, Jira
  `getAccessibleAtlassianResources`, Figma `whoami`). Non renseigné, différent ou BLOQUANT : on n'écrit
  pas sur ce connecteur.
- **Aucune routine n'écrit hors de son périmètre** décrit dans `routines.yml > routines.<projet>-<name>.writes`.
  Chaque écriture porte une `guard` (condition impérative) ; sans validation et sans la garde, on ne
  touche à rien. Les lectures seules (`writes: []`) ne font que proposer.
- **Jamais de chemin propre à un poste.** La racine projet se résout par `project_root_env`, puis
  `$HOME/Documents/<profile.name>`, puis repli sur le marqueur projet. Le deck du planning se résout
  par glob (horodatage variable).
- **Jamais d'écrasement.** Fichiers Office : fraîcheur SharePoint, sauvegarde horodatée, écriture
  chirurgicale, une seule écriture en place (jamais `rm`/`mv`), contrôle de taille/inode ensuite.
  Jira : relire avant d'écrire, aucun déplacement de ticket par une routine.

## (Ré)activer sur un nouveau poste

L'horaire vit dans l'état de l'app, pas dans un fichier : (ré)activer = **ré-enregistrer les pointeurs
minces**. Prérequis : le framework présent, `profiles/<mission>/routines.yml` rempli, les connecteurs
(suivi, Office) connectés sur le compte, et pour les routines Jira (`publish-projection`, `audit-scope`,
`track-progress`) l'accès Jira (jeton hors du dépôt). Puis, pour chaque routine :

1. Dans l'app, section **Scheduled**, créer une tâche (taskId `<projet>-<name>`, **title préfixé**
   `<PROJET> · …` - voir « Nom des routines ») dont le prompt est **uniquement** un pointeur :

   > Lis et applique exactement `framework/routines/<name>/SKILL.md` du framework (si ce chemin
   > n'existe pas, trouve le dossier qui contient `framework/routines/`). Mission : `<mission>`.
   > N'exécute que cette routine, n'envoie aucune notification.

2. Donner l'horaire du `schedule` de `routines.yml` (ou aucun horaire si `manual`).

Ou, plus court : demander à Claude **« enregistre les routines de `framework/routines` selon leur
`schedule` dans `profiles/<mission>/routines.yml` »**. Les routines `manual` se lancent à la main
(« Run now » ou en le demandant).

## Mettre à jour une routine

On modifie **le `SKILL.md` ici** (comportement) ou **`routines.yml`** (valeurs de mission), et c'est
tout : le pointeur relit ces fichiers à chaque exécution. On ne ré-enregistre que si l'**horaire**
change.

## Ce qui reste à confirmer

- Généraliser complètement les étapes de publication (gh-pages) et d'alignement des objectifs de
  `publish-projection` : aujourd'hui portées par des commandes de mission (`routines.yml > commands`),
  pas encore par un générateur du framework.
- Skills de méthode et de rédaction de `review-topics` (`methode_skill`, `redaction_skill`) : encore
  nommés par leurs skills SINBAD dans `routines.yml`, à porter en versions génériques.
- `absences` (`review-risks`) et la racine Drive locale (`profile.yml > drive.root`) restent
  `à confirmer`.
