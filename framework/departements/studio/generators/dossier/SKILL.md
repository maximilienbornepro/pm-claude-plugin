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
Charte et règles : skill `framework/charte/skills/slide-style/SKILL.md` ; maquette HTML de référence :
`docs/maquette/index.html` (mêmes slides, même mise en page).

## Le dossier de la mission : `profiles/<mission>/dossier/`

| Fichier | Rôle |
|---|---|
| `dossier.json` | **la source unique** (slides, données, légendes, liens vers les fichiers sources) |
| `dossier.pptx` | le PowerPoint, **éditable à la main** |
| `index.html` | la version HTML, même contenu et même charte (rendu `html_render.py`) |
| `architecture.html` | le schéma d'architecture au gabarit dossier, ouvert depuis la slide Architecture |
| `.state.json`, `.backup/` | empreintes du dernier build ou de la dernière synchro ; copies avant réécriture |

## Usage

```bash
python3 framework/pm.py run dossier <mission>              # slides, sources, état du PPTX (retouché ou non)
python3 framework/pm.py run dossier <mission> --build      # dossier.json -> dossier.pptx + index.html
python3 framework/pm.py run dossier <mission> --sync       # dossier.pptx retouché -> dossier.json -> index.html
python3 framework/pm.py run dossier <mission> --sync --dry-run   # ce qui serait repris, sans rien écrire
```

**Aller-retour PowerPoint → HTML.** On génère, on retouche le PPTX à la main, puis `--sync` reporte les
retouches dans `dossier.json` et régénère le HTML : rien n'est perdu. **Garde-fou** : `--build` refuse
d'écraser un PPTX retouché tant qu'il n'a pas été synchronisé (`--force` pour passer outre, avec copie de
sauvegarde).

## Le PowerPoint, éditable et relisible

- **Structure** : chaque slide a un vrai **titre** (espace réservé de titre : plan, sommaire, accessibilité),
  la légende est l'espace réservé de texte ; une slide **Sommaire** suit la couverture (sections et slides,
  avec liens) ; les polices du thème sont celles de la charte.
- **Ce qui remonte au `--sync`** : titres, sur-titres, légendes, sources ; texte des tableaux natifs, statuts
  (couleur de cellule), niveaux, RACI, ETP, pourcentages ; **barres d'avancement que l'on étire** ; données du
  **graphique natif** du burn-down ; barres du **Gantt** déplacées ou étirées, trait « aujourd'hui », jalons ;
  frise des jalons ; météo ; **pastilles déplacées dans la matrice des risques** ; weekly (puces à niveaux) ;
  compte rendu ; textes des schémas ; ordre des slides et slides supprimées.
- **Ce qui ne remonte pas** : une slide ajoutée à la main (signalée), la géométrie des schémas, la vue
  d'architecture (elle vient de `architecture/model.json`).
- Chaque forme porte un nom stable `dx:<rôle>` (volet Sélection de PowerPoint) : ne pas renommer.

## Source : `profiles/<mission>/dossier/dossier.json`

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

## Polices

Helvetica Neue Light / Thin (Mac). Sous Windows, PowerPoint les remplace : déclarer Segoe UI Light
comme police de substitution, ou installer Inter Light. Jamais de serif.

## Garde-fous

- N'écrit que le fichier `.pptx` demandé, en local. Le dépôt dans un espace partagé suit le déroulé
  Office (`framework/garde-fous/_deroule-office.md`), après accord ; aucune notification.
- Dépendance : `python-pptx` (`pip install python-pptx`) et Pillow (dimensions du logo).
