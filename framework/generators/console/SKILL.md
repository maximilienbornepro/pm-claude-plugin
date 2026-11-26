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

Trois écrans HTML servis en direct (stdlib `http.server`), relues à chaque requête :

- `/` : la console du **plugin** (sortie de `pm list`, templates, décisions, modifications par jour via git) ;
- `/projet` : la console du **projet** (activité par jour depuis `.claude/usage.log`, état des portes `gate`) ;
- `/agence` : l'**agence en direct**. Un bureau par famille (Accueil, Pilotage, Jira, Notion et suivi, Office,
  Studio, Rédaction, Renforts) ; dans chaque bureau, ses **Agents** et ses **Skills** (skills,
  générateurs, routines, connecteurs, distingués par le style de l'étiquette), calculés depuis le plugin (`agence.py`). Ce qui s'exécute passe en
  **rouge** (agent, skill, bureau, bandeau « En cours » en haut) et reste allumé au moins 4 secondes, et le fil liste chaque
  « agent → skill ». Source : `.claude/activity.log`, écrit par le hook `journal_activite` (demande, début et
  fin de chaque action ; noms d'outils et extrait de la demande seulement). Bouton « Rejouer une démo ».

```bash
python3 framework/pm.py run console [--mission <mission>] [--port 8765]
```

Lecture seule : aucune écriture, aucune notification. Pour un livrable à montrer, préférer le dossier
projet (générateur `dossier`).
