---
name: demo
description: Lance le faux projet et simule toutes les fonctionnalités du framework (aucune écriture).
argument-hint: "[mission]"
user-invocable: true
disable-model-invocation: true
allowed-tools: Bash(python3:*)
---
Lance le harnais de démonstration (faux projet, AUCUNE écriture réelle) pour la mission `$ARGUMENTS` (défaut : demo), puis résume ce qu'il simulerait et confirme qu'aucun système externe n'a été touché :

`python3 "${CLAUDE_PLUGIN_ROOT}/framework/pm.py" demo $ARGUMENTS`
