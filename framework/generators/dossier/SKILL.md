---
name: dossier
description: Dossier projet en slides 16:9 à la charte du plugin (skill slide-style, ton voice-slides) depuis UNE source, profiles/<mission>/dossier.json - export PowerPoint natif (tableaux éditables, formes, logo du client, lien vers le fichier source sur chaque slide). Lecture seule vis-à-vis des systèmes ; n'écrit que le .pptx demandé, en local.
meta:
  produces: dossier-pptx
  consumes: [plan, projection, risks, raci, notion-topics, weekly-report, partner-report, meeting-agenda, archi]
  mcp_deps: []
  cost: light
  writes: local-file
  status: draft
---

# Générateur `dossier`

Le dossier projet du comité, en slides 16:9 : section noire par partie, slides de contenu ivoire, titre
court, légende qui explique comment lire la slide, unités en jours, logo du client, lien vers la source.
Charte et règles : skill `framework/skills/slide-style/SKILL.md` ; maquette HTML de référence :
`docs/maquette/index.html` (mêmes slides, même mise en page).

## Source : `profiles/<mission>/dossier.json`

```json
{ "project": "Atlas", "kicker": "Atlas · Comité de pilotage",
  "logos": {"dark": "logos/client-blanc.png", "light": "logos/client-noir-texte.png"},
  "slides": [ {"kind": "cover", "title": "...", "sub": "..."},
              {"kind": "section", "title": "Avancement\n& sprints", "sub": "...", "num": "01"},
              {"kind": "table", "id": "registre-des-risques", "section": "Risques", "eyebrow": "...",
               "title": "Registre des risques", "cap": "<légende>", "src": "Risks_ATLAS.xlsx", "table": {...}} ] }
```

Types de slide (`kind`) : `cover`, `section`, `table`, `tiles_table`, `progress`, `burndown`, `sprint`,
`gantt`, `milestones`, `meteo`, `matrix`, `diagram` (blocs et flèches sur un canevas 1000 × h : schémas
inter-équipes, architecture), `gate`, `weekly`, `mail`. Cellules de tableau : texte (`**gras**`),
`pill` (statut), `dot` (niveau de risque), `raci`, `heat` (ETP), `st` (pastille de chantier), `bar`
(avancement %), `stack` (répartition des états). Exemple complet : `profiles/demo/dossier.json`.

Chaque slide est le **reflet d'un livrable existant** (règle 0 du skill `slide-style`) : le contenu de
`dossier.json` vient du générateur ou du document source correspondant, jamais de tête.

## Usage

```bash
python3 framework/pm.py run dossier <mission>                          # liste des slides et de leurs sources
python3 framework/pm.py run dossier <mission> --pptx out.pptx          # deck complet
python3 framework/pm.py run dossier <mission> --pptx out.pptx --only 3,risques   # quelques slides (n° ou id)
```

Les contrôles s'affichent : une slide dont le contenu estimé dépasse le pied de page est signalée.
Aperçu sans ouvrir PowerPoint (macOS) : `--only <n>` puis `qlmanage -t -s 1600 -o <dossier> <fichier>`.

## Polices

Helvetica Neue Light / Thin (Mac). Sous Windows, PowerPoint les remplace : déclarer Segoe UI Light
comme police de substitution, ou installer Inter Light. Jamais de serif.

## Garde-fous

- N'écrit que le fichier `.pptx` demandé, en local. Le dépôt dans un espace partagé suit le déroulé
  Office (`framework/generators/_deroule-office.md`), après accord ; aucune notification.
- Dépendance : `python-pptx` (`pip install python-pptx`) et Pillow (dimensions du logo).
