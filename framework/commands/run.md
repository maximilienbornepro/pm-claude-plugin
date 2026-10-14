---
description: Lance un generateur du framework sur une mission (lecture seule / dry-run par defaut)
argument-hint: "<generateur> <mission> [args]"
allowed-tools: Bash(python3:*)
---

Execute le generateur demande (`$ARGUMENTS`) via le moteur du framework :

!`python3 "${CLAUDE_PLUGIN_ROOT}/framework/pm.py" run $ARGUMENTS || true`

Presente la sortie a l'utilisateur. Les ecritures reelles (Jira, Notion, Office, gh-pages) restent
derriere un flag explicite (`--apply`...) et la validation en session : ne jamais appliquer sans son accord.
Si aucun argument n'a ete donne, propose `/pm-framework:list` pour voir les generateurs et les missions.
