---
description: Lance le faux projet et simule toutes les fonctionnalites (aucune ecriture)
argument-hint: "[mission]"
allowed-tools: Bash(python3:*)
---

Harnais de demonstration (faux projet, AUCUNE ecriture reelle) pour la mission `$ARGUMENTS` (defaut : demo) :

!`python3 "${CLAUDE_PLUGIN_ROOT}/framework/pm.py" demo $ARGUMENTS || true`

Resume a l'utilisateur ce que le harnais simulerait et confirme qu'aucun systeme externe n'a ete touche.
