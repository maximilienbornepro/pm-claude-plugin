---
name: traceability
description: Matrice de couverture IADT (Inspection / Analyse / Démonstration / Test) pré-remplie depuis un backlog ou des exigences - classeur Excel avec listes déroulantes, ou schéma de la base Notion équivalente. N'écrit que le fichier de sortie, en local.
meta:
  produces: traceability-xlsx
  consumes: []
  mcp_deps: []
  cost: light
  writes: local-file
  status: stable
---

# Générateur traceability

Part d'un backlog ou d'un jeu d'exigences (TR) et produit une matrice où chaque ligne est confrontée à une
méthode de vérification **IADT**, un **responsable** et un **état de couverture**. Les colonnes à choix
sont des listes déroulantes Excel ; le reste est du texte libre. Gabarits :
`templates/trackers/excel/traceability.yml`, `templates/trackers/notion/traceability.yml`.

```bash
python3 framework/pm.py run traceability <items.(yml|json|csv)> [sortie.xlsx]
python3 framework/pm.py run traceability --example [sortie.xlsx]
python3 framework/pm.py run traceability --notion [<items>]      # schéma de la base Notion (JSON)
```

Le classeur est **nouveau** : on le dépose ensuite où il doit aller, selon le déroulé Office
(`framework/garde-fous/_deroule-office.md`), après accord. L'audit des ruptures de la chaîne
besoin → ticket → POC → test est le générateur `trace-audit`.
