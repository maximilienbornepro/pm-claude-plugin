---
name: console
description: Sert en direct, sur localhost, deux consoles de gestion - celle du plugin (commandes, templates, décisions, modifications par jour) et celle du projet (activité par jour, état des portes). Lecture seule, rien n'est écrit.
meta:
  produces: console
  consumes: []
  mcp_deps: []
  cost: light
  writes: none
  status: draft
---

# Générateur console

Deux consoles HTML servies en direct (stdlib `http.server`), relues à chaque requête :

- `/` : la console du **plugin** (sortie de `pm list`, templates, décisions, modifications par jour via git) ;
- `/projet` : la console du **projet** (activité par jour depuis `.claude/usage.log`, état des portes `gate`).

```bash
python3 framework/pm.py run console [--mission <mission>] [--port 8765]
```

Lecture seule : aucune écriture, aucune notification. Pour un livrable à montrer, préférer le dossier
projet (générateur `dossier`).
