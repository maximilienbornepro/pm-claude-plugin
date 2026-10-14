---
name: sprint-audit
description: Audit en lecture seule des sprints d'un board Jira (charge estimée, tickets sans estimation, Done resté dans un sprint, blocages inversés, dates). Projet/board/identifiants viennent du profil de mission. N'écrit jamais.
---

# Générateur sprint-audit (audit des sprints Jira)

Au-dessus du client Jira du framework (`framework/lib/jira.py`), contrôle ce qui ne dépend
**que de Jira** pour les sprints actifs et futurs du board (lu du profil) :

- charge estimée par sprint (somme des estimations) ;
- tickets d'un sprint **sans estimation** ;
- tickets déjà **Done** encore présents dans un sprint ;
- **blocages inversés** (un bloquant rangé dans un sprint postérieur) ;
- dates des sprints.

Ce qui dépend d'un **plan de mission** (objectifs, versions V1/V1.1, cibles par pôle) n'est
pas porté ici : il vit au niveau du profil et de l'audit de plan (`sinbad-plan-sprints`).

## Usage
```
PMF_JIRA_ENV=<.../scan-jira/.env> python3 framework/pm.py run sprint-audit <mission>
```

## Garde-fous
Lecture seule stricte : aucune écriture Jira, aucun déplacement de ticket. Les identifiants
sont lus de l'environnement (`PMF_JIRA_ENV`) et du profil, jamais affichés.
