---
name: setup
description: Onboarding guidé d'un profil de mission - détecte les champs manquants, propose des valeurs, puis écrit après validation.
argument-hint: "[mission]"
user-invocable: true
allowed-tools: Bash(python3:*)
---
Diagnostic d'onboarding du profil `$ARGUMENTS` (défaut : sinbad) :

`python3 "${CLAUDE_PLUGIN_ROOT}/framework/pm.py" run setup $ARGUMENTS`

S'il reste des champs à renseigner, déroule l'onboarding **step by step** : formulaire cliquable, un champ à la fois, pré-rempli avec la suggestion, éditable au clic ; **jamais `AskUserQuestion`** pour ce remplissage. Rien n'est écrit avant le OK de l'utilisateur, puis écriture chirurgicale dans `profiles/<mission>/*.yml` ; les variables d'env (`SINBAD_ROOT`, `SINBAD_PM_ROOT`, `CLAUDE_PROJECTS`, `PMF_JIRA_ENV`) sont données en ligne `export`, pas écrites dans le YAML. Relance le diagnostic jusqu'à « Profil complet », puis propose `/pm-framework:demo <mission>`.
