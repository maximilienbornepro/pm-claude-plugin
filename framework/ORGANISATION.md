# Organisation du plugin

Le plugin s'organise comme un **PMO**, par **métier** (un livrable, un responsable), et cette organisation
suit **le fonctionnement réel de Claude Code**. Le référentiel unique est `framework/organisation.yml` ; le
catalogue `framework/SKILLS.md` en est généré, le vérificateur le contrôle, l'écran « agence » de la console
l'affiche.

## Ce que chaque composant est vraiment

| Dans le plugin | Dans Claude Code | Dans l'agence |
|---|---|---|
| — | Claude principal : seul à réfléchir, décider et te répondre | **Chef de projet** |
| skill (`framework/skills`) | mode d'emploi que Claude charge et suit lui-même (outil `Skill`) | **Classeur** |
| générateur (`pm run <nom>`) | script lancé par Claude via Bash, résultat déterministe | **Machine** |
| agent (`framework/agents`) | sous-agent : brief, contexte propre, rapport (outil `Agent`) ; le seul vrai collègue | **Collègue** |
| connecteur MCP | service externe appelé par celui qui travaille | **Service partagé** |
| hook (`framework/hooks`) | script automatique autour d'une action ; peut la bloquer | **Garde-fou** |
| routine (`framework/routines`) | tâche planifiée : une autre session, à heure fixe | **Chef de garde** |

Conséquences : un skill ne « travaille » jamais seul (c'est toujours Claude, ou un sous-agent, qui suit le
classeur) ; un département sans agent dédié n'est pas vide, c'est Claude principal qui y travaille ; un
sous-agent ne voit pas la conversation, il ne connaît que son brief.

## Les départements

| Département | Rôle | Mission |
|---|---|---|
| Direction de projet | Chef de projet | cadrer la demande, préparer la mission, vérifier les connexions, décider des gates |
| Planification | PMO planning | planning, plan de sprints, projection de fin, objectifs de sprint |
| Suivi et gouvernance | Responsable du suivi | sujets, risques, RACI, traçabilité, cohérence des documents |
| Qualité du backlog | Responsable qualité | tickets propres et à jour, écarts maquette / tickets / contrat d'API |
| Communication | Chargé de communication | comptes rendus, weekly, ordres du jour, relances, transcriptions |
| Studio | Designer | mise en forme des livrables : dossier projet, deck, architecture, documents, POC |

**Transverse** (jamais « à » un seul département) : la **charte et les tons** (`slide-style`, `voice-*`), les
**services partagés** (connecteurs), les **garde-fous** (hooks), les **renforts** (agents génériques de Claude
Code, qui vont travailler dans le département qui les appelle).

Le détail composant par composant est dans `framework/SKILLS.md`.

## Ajouter un composant

1. Le créer à sa place habituelle (générateur, skill, agent, routine ou hook).
2. Le rattacher à **un** département dans `framework/organisation.yml` (ou à la charte, aux garde-fous).
3. `python3 framework/lib/organisation.py --catalogue` régénère `framework/SKILLS.md`.
4. `python3 framework/harness/verifier.py` doit passer : il échoue si un composant n'est rattaché nulle part,
   s'il l'est deux fois, ou si un rattachement vise un composant qui n'existe pas.

## Manques que cette organisation montre

- **Planification** et **Communication** n'ont aucun sous-agent dédié : tout y est fait par Claude principal.
  Candidats : un agent « planner » (tient `planning.json` et le Gantt) et un agent « rédacteur de CR » (CR,
  weekly, ordre du jour depuis les transcriptions).
- `doc-writer` et `adservio-writer` ne sont appelés par aucun générateur : ils servent à la demande.
