---
name: plan
summary: Plan de sprints « Avancement et sprints » - une page HTML autonome (jalons, avancement par pole V1.0/V1.1, burn-downs reels, detail par sprint). Design reutilisable (gabarit + contrat + render + validate), comme le generateur archi ; pipeline Jira config-driven en option.
meta:
  produces: plan-sprints
  consumes: [jira]
  mcp_deps: [jira]
  cost: light
  status: stable
---

# Generateur `plan`

La page **« Avancement et sprints »** : avancement V1 et plan de sprints sur une seule
page, pilotee par les donnees. Deux usages, du plus reutilisable au plus integre.

## 1. Design reutilisable (model-first, comme `archi`)

Le design vit dans le **gabarit** `plan_design.tmpl.html` (CSS + Chart.js + interactions) ;
on l'edite. La donnee est **un seul bloc JSON** (`meta` + `report` + `sprints[]`) injecte
dans le gabarit. N'importe quelle mission qui produit ce JSON obtient la page, sans Jira.

| Fichier | Role |
|---|---|
| `plan_design.tmpl.html` | le design (source de verite visuelle, placeholder `__DATAJSON__`) |
| `CONTRACT.md` | le contrat du JSON (meta / report / sprints) |
| `render.py` | `render.py donnees.json [sortie.html]` - injecte et ecrit la page |
| `plan.example.json` | exemple complet (projet fictif Orion), sert de showcase et de fixture |
| `validate.py` | `validate.py donnees.json` - controle le JSON contre le contrat (garde + regression) |

```sh
python3 render.py --example plan.html        # rend l'exemple
python3 validate.py donnees.json             # valide avant de publier
```

## 2. Pipeline Jira config-driven (`from_jira.py`)

Construit le JSON depuis un Jira **sans aucune valeur de mission en dur**, puis le rend.
Les chiffres (charge/reste/capacite) viennent de `profiles/<mission>/projection.yml`
(memes regles que le generateur `projection`) ; la cadence des sprints, la marque, les
liens et l'editorial viennent de `profiles/<mission>/plan.yml` (gabarit `plan.example.yml`).

```sh
PMF_JIRA_ENV=<.../.env> python3 framework/pm.py run plan <mission> [sortie.html]
PMF_JIRA_ENV=<.../.env> python3 framework/generators/plan/from_jira.py <mission> --json plan.json
```

- **Jira fait foi** pour la repartition : chaque ticket va dans son sprint Jira ; seuls les
  tickets du backlog sont places par le calcul, sous la cible de capacite du pole (`caps`).
- **Burn-down reel** : un ticket descend la courbe le jour ou il passe **en Testing ou ferme**
  (`burn_wip` + `done_statuses`), date prise sur `resolutiondate` (repli `updated`). En jours
  estimes : le reste affiche reste donc au-dessus du reste pondere par statut (l'ecart est
  explique sur chaque carte).
- **Editorial** (maintenu a la main) : objectif par sprint, phrase `fres`/`fout`, objectif par
  pole - trois fichiers JSON references dans `plan.yml`.

## Reliquat de fin de sprint (regle Testing) - alerte obligatoire

Quand un sprint se termine, Jira **bascule tout le non-termine au sprint suivant**, y compris les
tickets deja **en recette**. Sans garde-fou, le dashboard les compte comme perimetre du nouveau
sprint (qui gonfle) et pollue son objectif.

- **Regle (dashboard seul, aucune ecriture Jira)** : un ticket actuellement dans le statut de recette
  reste rattache au sprint ou il est **entre dans ce statut** (1re transition, lue dans le changelog
  via `J.status_changes`), pas a son champ sprint courant. `_appliquer_reliquat` dans `from_jira.py`.
- **Config** `plan.yml` : `test_status` (nom du statut de recette, defaut `Testing` - a adapter :
  `QA`, `En test`, `In Review`...) et `reliquat: true|false` (defaut `true`) pour activer la regle.
- **Alerte explicite obligatoire** : `alert_reliquat` imprime `⚠ ATTENTION - reliquat de fin de
  sprint` et liste les tickets maintenus. **Toujours le repeter a l'utilisateur** et lui demander de
  verifier si certains doivent au contraire rester dans le scope du sprint courant. Jamais en silence.
- `data["reliquat"]` porte la liste (cle, sprint d'origine, sprint Jira) pour l'audit.

## Garde-fous

- **Lecture seule** cote systemes : uniquement des requetes Jira de lecture ; n'ecrit que le
  fichier de sortie. Aucune notification.
- **Publier = acte separe** : montrer un apercu local d'abord ; la publication (gh-pages,
  artefact) est une autre etape, validee par l'utilisateur.
- Le design est **commun** : on edite `plan_design.tmpl.html`, jamais le HTML genere.

> SINBAD garde sa propre chaine dans `scan-jira/projection` (serve.py + build_plan.py) ;
> ce generateur en est le portage **reutilisable** pour d'autres missions.
