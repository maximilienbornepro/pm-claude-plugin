---
description: Onboarding guide d'un profil de mission (champs manquants + suggestions, puis ecriture apres validation)
argument-hint: "[mission]"
allowed-tools: Bash(python3:*)
---

Diagnostic d'onboarding du profil `$ARGUMENTS` (defaut : sinbad) :

!`python3 "${CLAUDE_PLUGIN_ROOT}/framework/pm.py" run setup $ARGUMENTS || true`

Si des champs sont a renseigner : deroule l'onboarding **step by step** en suivant le skill
`/pm-framework:setup` (le SKILL de ce plugin) - formulaire cliquable, un champ a la fois, pre-rempli
avec la suggestion, editable au clic ; **jamais `AskUserQuestion`** pour ce remplissage. Rien n'est
ecrit avant le OK de l'utilisateur ; ensuite ecriture chirurgicale dans `profiles/<mission>/*.yml`,
et les variables d'env (`SINBAD_ROOT`, `SINBAD_PM_ROOT`, `CLAUDE_PROJECTS`, `PMF_JIRA_ENV`) sont
donnees en ligne `export`, pas ecrites dans le YAML. Relance ensuite ce diagnostic jusqu'a
« Profil complet ».

Si « Profil complet » s'affiche : dis-le et propose `/pm-framework:demo <mission>`.
