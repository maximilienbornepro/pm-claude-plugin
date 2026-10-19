# Contrat de données du plan de sprints

La page `plan_design.tmpl.html` lit **un seul** bloc JSON (placeholder `__DATAJSON__`).
`render.py` l'injecte. Toute mission qui produit ce JSON obtient la page. Trois clés de
premier niveau : `meta`, `report`, `sprints`.

Unités : les jours sont des **jours-homme estimés** (nombres). Les dates sont `AAAA-MM-JJ`.

## `meta`

| Champ | Type | Rôle |
|---|---|---|
| `brand.title` | str | Titre affiché (et `<title>`). |
| `brand.sub` | str | Sous-titre sous le titre. |
| `brand.logo` | str | Logo en data-URI (`data:image/png;base64,…`) ou `""`. Masqué si vide. |
| `brand.app_url` | str | Lien du bouton d'en-tête (ex. l'application). Masqué si absent. |
| `brand.app_label` | str | Libellé du bouton (défaut « Ouvrir l'application »). |
| `today` | date | Aujourd'hui (position du repère et fin des courbes réelles). |
| `generated` | datetime | Horodatage de génération (affiché « Mis à jour le … » en pied de page). |
| `freeze` | date | Gel du code (repère + cible de la droite idéale). |
| `mep` | date | Mise en production (repère). |
| `jira` | str | Préfixe d'URL d'un ticket (ex. `https://…/browse/`). Concaténé à la clé. |
| `links` | list | Liens des jalons : `[{label, url}]` (ex. planning, board). |
| `nav` | list | Barre de navigation entre pages : `[{label, url, active?}]`. `active:true` marque la page courante (sans lien sortant). Omise = pas de barre. |
| `release_link` | obj | Lien optionnel sur la carte d'un sprint : `{label, url}`. |

Pas de `sre_absence` : si présent (`{start, end, label}`), une bande est dessinée sur les
jalons ; l'omettre la retire.

## `report`

- `kpi` : `{v1_pct, v1_real, v1_charge, v1_reste}` (bandeau compact d'en-tête).
- `poles` : `{back, front, sre}`, chacun `{charge, reste, pct, real, weeks, cap_etp}`.
- `poles_v11` : idem, périmètre V1.1 (dépliable). `{charge, reste, pct, real}` suffisent.
- `v11` : `{reste}` (total V1.1).
- `timeline` : `{v1_end, overshoot_weeks}` pour le bandeau (optionnels).
- `avail_weeks` : nombre (semaines avant le gel).
- `burn_v1` : burn-down du plan (voir ci-dessous).
- `epics` : reste par epic, `[{epic, pole, rV1, rV11, charge, phase, tickets:[{k,s,st,r,ph,ne}]}]`
  (carte « Reste par epic », en bas, repliée ; sous-sections V1.0 / V1.1, chaque epic dépliable sur ses tickets).
- `delta` : différentiel depuis la dernière publication (optionnel ; carte masquée si tout est vide).
  `{ref, pct_avant, pct_apres, gain, jours_termines, termine[], avance[], recul[], nouveau[], disparu[]}` ;
  chaque item : `{k, s, e, p, st, st_avant}` (+ `gain` pour avance/recul). Nécessite un état persistant
  entre deux publications, donc propre à la mission.

### `report.burn_v1` (burn-down du plan, réel)

```
{ scope, start, freeze, freeze_d, mep, mep_d, today, today_d,
  tk: [ {e: estimation, cd: date de fermeture|null, td: date d'entrée en Testing|null, st: statut}, … ] }
```
`scope` = charge totale du périmètre (somme des `e`). `*_d` = décalage en jours depuis `start`.
La **série est calculée dans la page** à partir de `tk`, selon le mode choisi par le lecteur
(**Fermés** = `cd`, **Testing** = `td` des tickets en Testing, **Les deux**). Un ticket descend la
courbe le jour de la date retenue. `cd` vient de `resolutiondate`, `td` de `updated` (entrée en Testing).

## `sprints[]` (un objet par sprint)

| Champ | Type | Rôle |
|---|---|---|
| `n` | int | Numéro (1 = sprint en cours). |
| `dates` | str | Libellé des dates, ex. `06 → 18 oct` ; `· gel` / `· MEP` déclenche les badges. |
| `hint` | str | Mention courte (« découpage proposé », « reste V1 + V1.1 »…). |
| `start`,`end` | date | Bornes (jalons, axe du burn-down). |
| `objectif` | str | Objectif global du sprint (1-3 phrases). |
| `fres` | str | « Ce que l'utilisateur pourra faire » (optionnel). |
| `fout` | str | « Non disponible » (optionnel). |
| `tot` | nombre | Reste à faire du sprint (pondéré). |
| `bugs` | nombre | Réserve de bugs ajoutée. |
| `ntk` | int | Nombre de tickets. |
| `estTotal` | nombre | Estimation totale des tickets du sprint. |
| `jiraUrl` | str | Lien « Sprint dans Jira » (sinon `meta.jira`). |
| `poles` | obj | `{back, front, sre}` (voir ci-dessous). |
| `tickets` | list | Tickets du sprint (voir ci-dessous). |
| `burn` | obj | Burn-down du sprint : `{scope, len, start, tk}` (même `tk` que `burn_v1`). Série calculée côté page selon le mode ; un sprint à venir donne une courbe idéale seule. |

### `sprints[].poles[pole]`

`{ label, tot, est, bugs, done, load, cap, n, objectif, epics: [{e, r, n, done}] }`
- `load = tot + bugs` ; `cap` = capacité cible du pôle sur le sprint.
- `done` = jours-homme estimés déjà terminés (barre de progression).
- `objectif` = phrase courte de l'objectif du pôle sur ce sprint.

### `sprints[].tickets[]`

`{ k, s, p, e, r, est, st, d, ne, ph }` : clé, résumé, pôle, epic, reste, estimation,
statut, terminé (bool), non estimé (bool), phase (`V1` / `V1.1`).

Voir `plan.example.json` pour un exemple complet et `validate.py` pour les contrôles.
