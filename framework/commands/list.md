---
description: Liste les generateurs du framework et les missions du projet courant
allowed-tools: Bash(python3:*)
---

Generateurs disponibles et missions (profils) du projet courant :

!`python3 "${CLAUDE_PLUGIN_ROOT}/framework/pm.py" list || true`

Rappelle a l'utilisateur qu'il lance un generateur avec `/pm-framework:run <generateur> <mission>`,
et que tout est en lecture seule / dry-run par defaut.
