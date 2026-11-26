---
name: publish-projection
description: "Publie les pages d'avancement (gh-pages) puis le même HTML sur les artefacts Claude, aligne les objectifs des sprints du tracker sur le JSON éditorial, et signale tout texte de sprint périmé ; mode goals-only pour n'aligner que les objectifs. Écrit : gh-pages, artefacts, objectifs de sprint Jira (champ texte). Aucune notification."
meta:
  kind: routine
  scope: mission
  schedule: config          # routines.yml > routines.<projet>-publish-projection.schedule (ex. 8h/11h/18h)
  chains: [projection, jira-sprints-audit]
  writes: [gh-pages, artifact, jira]
  validation: none          # écritures gardées et idempotentes (push seulement s'il y a une évolution)
  default_mode: apply       # routine planifiée de publication ; --dry-run pour un essai
  output: chat-md
  notifies: none
  mcp_deps: []              # Jira par les commandes de mission (jeton hors dépôt) ; artefacts par l'outil Artifact
  status: stable
---

# publish-projection - publier, aligner les objectifs, signaler la dérive

Les pages d'avancement mélangent deux sources : les chiffres et les listes de tickets suivent le tracker
à chaque génération ; le **texte des sprints** (objectif, « ce que l'utilisateur peut faire », « non
disponible », texte par pôle) est éditorial, tenu à la main dans les JSON de mission
(`reads.editorial`). Ce texte ne se met jamais à jour seul : la routine doit donc **dire** quand il ne
colle plus au tracker. Réponds dans la langue du profil (`profile.yml > lang`).

## Déclencheur et modes

- **Planifiée** : `schedule` de l'instance `routines.<projet>-publish-projection`.
- **Mode `full`** (par défaut) : étapes 1 à 5 du déroulé.
- **Mode `goals-only`** (manuel, anciennement la routine `align-sprint-goals`) : préflight puis
  **étape 3 seule** (objectifs des sprints) et rapport. Ni publication, ni artefact, ni contrôle de
  dérive. Se lance par « publish-projection en mode goals-only » ou par une instance qui porte
  `mode: goals-only`.
- **`--dry-run`** (ou « à blanc » dans l'invite) : on lit, on construit, on rapporte ce qui serait publié
  et aligné ; rien n'est poussé ni écrit.

## Entrées

Clé d'instance `routines.<projet>-publish-projection` ; à défaut, l'ancienne clé (voir `framework/routines/README.md`, colonne « Anciennement »).

Instance `routines.<projet>-publish-projection` de `profiles/<mission>/routines.yml` :

- `commands.publish` : génération et push gh-pages (depuis la racine projet) ;
- `commands.objectifs` : alignement des objectifs de sprint sur `reads.objectifs_json` (optionnel) ;
- `commands.drift_check` : contrôle de dérive, lecture seule (optionnel) ;
- `artifacts[]` : `{url, ghpages_path}`, et `ghpages_repo` (checkout local de la branche gh-pages) ;
- `reads.editorial` : les JSON éditoriaux des sprints ;
- `alerts[]` : alertes supplémentaires à relayer.

Racine projet : `routines.yml > project_root_env`, puis `$HOME/Documents/<profile.name>`, puis le
marqueur projet.

## Enchaînements

`chains: [projection, jira-sprints-audit]` : la projection alimente les pages, l'audit des sprints sert
le contrôle de dérive. Tant que la publication n'est pas portée par un générateur du framework, elle
passe par `commands.publish`.

## Déroulé

0. **Préflight** : `python3 framework/pm.py run preflight <mission>`, puis confirmer l'identité Jira
   (`getAccessibleAtlassianResources` : un `cloudId` == profil). BLOQUANT ou identité différente :
   aucune écriture Jira (étape 3 sautée, dite dans le rapport) ; la publication gh-pages et les
   artefacts restent possibles.
1. **Publier** : lance `commands.publish`. **Garde** : push uniquement s'il y a une évolution ; le jeton
   du tracker n'apparaît jamais dans les pages.
2. **Artefacts (règle gh-pages + artefact)** : pour chaque entrée de `artifacts`, récupère le HTML publié
   (`git show origin/gh-pages:<ghpages_path>` dans le checkout `ghpages_repo`) et publie-le tel quel sur
   son `url`. Jamais une page sans son artefact. Si « aucune évolution », rien à republier pour cette page.
3. **Objectifs des sprints** (si `commands.objectifs` est défini) : lance-le. Il n'écrit que le champ
   objectif des sprints qui diffèrent du JSON (`reads.objectifs_json`) ; aucun ticket touché.
4. **Contrôle de dérive** (si `commands.drift_check` est défini, lecture seule) : lance-le et lis ses
   sections « Objectifs des sprints » et « Narratif du plan à revoir ». S'il signale un ticket qui a
   changé de sprint, un objectif différent, ou un sprint sans texte, **alerte explicitement** :
   « ⚠ texte du sprint N périmé : <tickets déplacés> », sprint par sprint, avec une proposition de
   phrase. **Ne réécris jamais le texte toi-même** : c'est éditorial, l'utilisateur valide. Si le
   contrôle plante, le dire (jamais en silence) et continuer.
5. **Vérifier et rapporter** : pages poussées ou « aucune évolution », artefacts republiés, sprints
   réalignés (et ceux déjà bons), alertes.

## Sortie

Compte rendu court dans la conversation (Markdown) : publication, artefacts, objectifs, alertes à
relayer, jamais en silence :

- **Reliquat de fin de sprint** : quand la génération imprime `⚠ reliquat de fin de sprint`, le relayer
  (dashboard uniquement, aucune écriture dans le tracker).
- **Texte de sprint périmé** : étape 4.
- Toute autre entrée de `alerts`.

## Garde-fous

- `notifies: none`. Artefacts privés ; l'objectif de sprint est un champ texte qui ne notifie personne.
- **Aucun ticket déplacé ni modifié** par cette routine, y compris en mode `goals-only`. Pas de tracker
  Notion (routine `track-progress`), pas d'Office.
- Respecte chaque `writes[].guard` de l'instance.
- **Règle associée (hors routine)** : quiconque déplace des tickets entre sprints (Claude compris, en
  session) réécrit dans le **même passage** le texte des sprints concernés (JSON éditoriaux), lance
  `commands.objectifs`, puis republie. La routine n'est que le filet de sécurité.

## Décisions datées

- Fusion de `align-sprint-goals` (anciennement `objectifs-sprints`) dans cette routine, mode
  `goals-only` : les deux portaient la même commande `commands.objectifs`.
