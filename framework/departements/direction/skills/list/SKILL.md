---
name: list
description: Liste les générateurs du pm-framework et les missions (profils) du projet courant.
user-invocable: true
disable-model-invocation: true
allowed-tools: Bash(python3:*)
---
Exécute et présente la sortie à l'utilisateur :

`python3 "${CLAUDE_PLUGIN_ROOT}/framework/pm.py" list`

Rappelle qu'on lance un générateur avec `/pm-framework:run <générateur> <mission>`, tout en lecture seule / dry-run par défaut.
