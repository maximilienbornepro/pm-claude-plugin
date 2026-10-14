# Routines planifiees - framework portable

Definitions **generiques et config-driven** des routines planifiees du framework. C'est la
**source de verite** : la tache reellement enregistree dans l'app n'est qu'un **pointeur mince** vers
`framework/routines/<nom>/SKILL.md`. On edite le fichier du projet, jamais la copie de l'app.

Deux couches, comme le reste du framework :

- **le SKILL generique** (`framework/routines/<nom>/SKILL.md`) : le deroule et les garde-fous, sans
  aucune valeur de mission ;
- **la config de mission** (`profiles/<mission>/routines.yml`) : horaire, generateurs enchaines,
  identifiants, chemins, perimetre des ecritures. Gabarit commente : `routines.example.yml`.

Changer de mission = remplir `routines.yml`, pas toucher aux SKILL ni au code.

**Nom des routines** : le **SKILL générique** vit dans `framework/routines/<nom>/` (sans préfixe, portable).
L'**instance de mission** - la clé dans `profiles/<mission>/routines.yml` et la tâche enregistrée dans l'app -
est **préfixée du nom du projet** (ex. `sinbad-<nom>`) et porte `skill: <nom>` qui pointe vers le SKILL
générique. Ainsi les routines de deux missions ne se confondent pas dans l'app, et le moteur reste générique.

Dans l'app (section **Scheduled**), chaque tâche porte **à la fois** :
- un **`taskId`** `<projet>-<nom>` (ex. `sinbad-publication-projection`) ;
- un **`title` préfixé du nom du projet en majuscules** `<PROJET> · …` (ex. « SINBAD · MAJ rapport… »). **C'est
  le `title` qui s'affiche** dans la liste : il **doit** être préfixé pour distinguer les missions d'un coup d'œil.

## Les routines

| Dossier (`framework/routines/`) | Horaire (config) | Enchaine (`chains`) | Ecrit (gardé) |
|---|---|---|---|
| `publication-projection` | cron (ex. 8h/11h/18h) | `projection`, `sprint-audit` | **gh-pages + artefact Claude** (rapport + plan, les deux a jour) |
| `objectifs-sprints` | manuel | - | objectifs de sprint Jira (texte ; aucun ticket deplace) |
| `avancement-tracker` | cron (ex. 8h/11h/18h) | `projection` | 1 champ du tracker Notion (avancement V1) |
| `audit-perimetre` | manuel | `sprint-audit` | **lecture seule** : perimetre V1/V2 + couverture TR (propositions, aucune ecriture) |
| `suivi` | cron (ex. 19h) | `suivi` (collect + weekly + sync) | store local + DB Notion **privee** (4 categories ; aucune notif) ; jamais la page Weekly report de Greg |
| `revue-sujets` | manuel | `revue-risques` (sauf mode `condensation`) | base de suivi (sujets valides, condensation des sujets a rallonge comprise via le mode `condensation`), puis registre des risques via `revue-risques` |
| `revue-risques` | manuel (planifiable) | `risks`, `projection` | registre des risques (Office, en place) |
| `slide-planning` | manuel | - | deck pptx, une seule slide (Office, en place) |
| `brouillons-relances` | manuel | - | brouillons Outlook ouverts en redaction (`mailto:`, nouveau fil) ou reponse dans le fil d'origine (presse-papiers / Outlook web) + copie `.eml` locale ; messages Slack internes rendus a copier, **rien n'est envoye ni poste** |

`chains` ne reference que des generateurs du framework (`python3 framework/pm.py list`) ou une autre
routine. L'horaire reel est dans le frontmatter `schedule` du SKILL (valeur `config`, qui renvoie a
`routines.yml`) : le cron effectif est dans `routines.yml > routines.<nom>.schedule`.

## Regles permanentes (toutes, sans exception)

- **Aucune routine n'envoie de notification.** `notifies: none` sur chaque routine : jamais de mail,
  de mention `@`, de commentaire, de message Teams, de partage ni d'invitation. Avant toute operation,
  se demander qui serait notifie ; au moindre doute, on decrit et on attend. Une notification partie ne
  se rattrape pas.
- **Aucune routine n'ecrit hors de son perimetre** decrit dans `routines.yml > routines.<nom>.writes`.
  Chaque ecriture porte une `guard` (condition imperative) ; sans validation et sans la garde, on ne
  touche a rien. Les lectures seules (`writes: []`) ne font que proposer.
- **Jamais de chemin propre a un poste.** La racine projet se resout par `project_root_env`, puis
  `$HOME/Documents/<profile.name>`, puis repli sur le marqueur projet. Le deck du planning se resout
  par glob (horodatage variable).
- **Jamais d'ecrasement.** Fichiers Office : fraicheur SharePoint, sauvegarde horodatee, ecriture
  chirurgicale, une seule ecriture en place (jamais `rm`/`mv`), controle de taille/inode ensuite.
  Jira : relire avant d'ecrire, aucun deplacement de ticket par une routine.

## (Re)activer sur un nouveau poste

L'horaire vit dans l'etat de l'app, pas dans un fichier : (re)activer = **re-enregistrer les pointeurs
minces**. Pre-requis : le framework present, `profiles/<mission>/routines.yml` rempli, les connecteurs
(suivi, Office) connectes sur le compte, et pour les routines Jira (`publication-projection`,
`objectifs-sprints`, `avancement-tracker`, `audit-perimetre`) l'acces Jira (jeton hors du
depot). Puis, pour chaque routine :

1. Dans l'app, section **Scheduled**, creer une tache (taskId `<projet>-<nom>`, **title préfixé**
   `<PROJET> · …` - voir « Nom des routines ») dont le prompt est **uniquement** un pointeur :

   > Lis et applique exactement `framework/routines/<nom>/SKILL.md` du framework (si ce chemin
   > n'existe pas, trouve le dossier qui contient `framework/routines/`). Mission : `<mission>`.
   > N'execute que cette routine, n'envoie aucune notification.

2. Donner l'horaire du `schedule` de `routines.yml` (ou aucun horaire si `manual`).

Ou, plus court : demander a Claude **« enregistre les routines de `framework/routines` selon leur
`schedule` dans `profiles/<mission>/routines.yml` »**. Les routines `manual` se lancent a la main
("Run now" ou en le demandant).

## Mettre a jour une routine

On modifie **le `SKILL.md` ici** (comportement) ou **`routines.yml`** (valeurs de mission), et c'est
tout : le pointeur relit ces fichiers a chaque execution. On ne re-enregistre que si l'**horaire**
change.

## Ce qui reste a confirmer

- Generaliser completement les etapes de publication (gh-pages) et d'alignement des objectifs de
  `publication-projection` et `objectifs-sprints` : aujourd'hui portees par des commandes de mission (`routines.yml > commands`),
  pas encore par un generateur du framework.
- Skills de methode et de redaction de `revue-sujets` (`methode_skill`, `redaction_skill`) : encore
  nommes par leurs skills SINBAD dans `routines.yml`, a porter en versions generiques.
- `absences` (`revue-risques`) et la racine Drive locale (`profile.yml > drive.root`) restent
  `a confirmer`.
