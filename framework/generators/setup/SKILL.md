---
name: setup
description: Onboarding guidé d'un profil de mission. Détecte les champs manquants ou `à confirmer` (équipe/RACI, racine Drive, source du planning, carte de cohérence, variables d'env) et propose une valeur en sondant le disque. À utiliser au PREMIER prompt sur une mission dont le profil n'est pas complet : on accompagne l'utilisateur champ par champ, par formulaire cliquable, puis on écrit le profil après validation.
meta:
  produces: null
  consumes: []
  mcp_deps: [jira, notion, m365]
  cost: light
  status: stable
---

# Onboarding d'un profil (setup)

But : qu'un **projet frais** soit configurable **sans éditer un YAML à la main**. On détecte les trous,
on propose, l'utilisateur valide dans un formulaire, puis on écrit le profil.

## Quand le déclencher
- Au **premier prompt** d'une session sur une mission dont le profil a des trous (voir le `CLAUDE.md`
  du framework : si `pm run setup <mission>` liste des champs, on lance l'onboarding avant toute autre tâche).
- Quand l'utilisateur dit « configure le projet », « on démarre une nouvelle mission », « il manque quoi ».

## Déroulé (step by step)
1. **Diagnostic** : `python3 framework/pm.py run setup <mission> --json`. Il rend, pour chaque trou :
   `label`, `why` (à quoi ça sert), `current`, `suggestion` (valeur(s) proposées en sondant le disque),
   `where` (fichier/clé à écrire), `kind` (`value` / `list` / `path` / `env`).
2. **Formulaire cliquable** : présenter les champs **un par un**, chacun **pré-rempli avec la suggestion**,
   éditable au clic. Un champ = une question ; pour `env`, proposer la commande `export`. Respecter la
   règle projet « tout formulaire passe par le questionnaire standard » : texte complet, édition au clic,
   **jamais `AskUserQuestion`/elicit** pour ce remplissage.
3. **Validation** : l'utilisateur ajuste et valide. Rien n'est écrit avant son OK.
4. **Écriture** : appliquer les réponses **chirurgicalement** dans `profiles/<mission>/*.yml`
   (remplacer la valeur `à confirmer` / `[]` par la valeur validée ; ne toucher qu'aux clés concernées).
   Les variables d'env (`SINBAD_ROOT`, `SINBAD_PM_ROOT`, `CLAUDE_PROJECTS`, `PMF_JIRA_ENV`) ne vont pas
   dans le YAML : on donne la ligne `export` à poser (ou à mettre dans un `.env`), on ne les stocke pas en clair.
5. **Contrôle** : relancer `setup <mission>` → doit afficher « Profil complet ». Puis proposer un `pm demo`.

## Ce que setup NE fait pas
- Il **n'écrit rien** lui-même (lecture seule). L'écriture du profil est faite par Claude après validation.
- Il ne touche ni Jira, ni Notion, ni Office, ni le projet SINBAD d'origine : seulement les YAML du profil
  dans le framework.
- Il ne devine pas les **noms** des personnes (il propose les slots de rôles du RACI à remplir), ni un
  chemin inexistant (il propose les dossiers OneDrive réellement trouvés sur le disque).

## Garde-fous
Suggestions issues d'un **sondage en lecture seule** du disque (glob OneDrive, test d'existence des
dépôts, rôles lus de `raci.yml`). Aucune valeur inventée : un champ sans suggestion fiable est marqué
`<à renseigner>`. L'écriture finale suit les règles d'écriture du framework (une passe, pas d'écrasement).
