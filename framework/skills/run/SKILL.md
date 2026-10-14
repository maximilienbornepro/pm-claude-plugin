---
name: run
description: Lance un générateur du pm-framework sur une mission (lecture seule / dry-run par défaut).
argument-hint: "<générateur> <mission> [args]"
user-invocable: true
disable-model-invocation: true
allowed-tools: Bash(python3:*)
---
Exécute le générateur demandé et présente la sortie :

`python3 "${CLAUDE_PLUGIN_ROOT}/framework/pm.py" run $ARGUMENTS`

Les écritures réelles (Jira, Notion, Office, gh-pages) restent derrière un flag explicite (`--apply`…) et la validation : ne jamais appliquer sans l'accord de l'utilisateur. Sans argument, propose `/pm-framework:list`.
