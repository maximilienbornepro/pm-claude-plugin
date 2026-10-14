---
name: notion-planning
description: Construit et tient a jour le planning de reference de la mission - une PAGE NOTION avec un GANTT (vue timeline), pas un Excel. Un seul sens (source -> Notion), ecriture GARDEE "demander-avant". Le dossier Drive "04 - Planning" n'est pas forcement utilise. Le report sur la slide du deck est porte par slide-planning. Aucune notification.
---

Le **planning de reference** de la mission est une **page Notion avec un GANTT** (vue timeline) : une ligne
= un **workstream** avec `debut`/`fin`, un `statut` et un `avancement` ; des **jalons** en marqueurs.
**Ce n'est PAS un Excel**, et le dossier Drive `04 - Planning` n'est pas forcement utilise.

Forme des donnees : `planning.sample.yml` (sample livre) = `workstreams[{workstream, pole, debut, fin,
statut, avancement}]` + `jalons[{jalon, date}]`. On construit/tient a jour la page Notion a partir de ca.
**Sens unique** : source -> Notion, jamais l'inverse. Ecriture **gardee** : on montre, on attend le oui.
Voix du profil (`notion_planning.yml > tone`).

## Structure de la page (Gantt)

Une **base Notion** (une ligne par workstream) avec une **vue timeline** : propietes `Workstream`, `Pole`,
`Debut` (date), `Fin` (date), `Statut` (select), `Avancement` (number %). Les **jalons** sont des lignes
reperes (ou une colonne dediee). C'est cette vue timeline qui fait office de Gantt.

## Deroule

1. Lire la source (`notion_planning.yml > source`, forme `planning.sample.yml` : workstreams + jalons) et
   le planning actuel dans Notion (`planning_tracker`, la base Gantt), en lecture seule.
2. Calculer le **diff** (workstreams/dates/jalons qui changent). Si rien ne change, ne rien ecrire.
3. **Montrer le contenu exact** (avant/apres) et **attendre le oui** (`guard: demander-avant`).
4. Ecrire **uniquement** les champs valides, de maniere chirurgicale (`notion-update-page`, `update_content`
   ou `update_properties` cible ; jamais `replace_content`). Mentions en texte simple.
5. Relire (`notion-fetch`).

## Lien avec la slide

Le **meme** planning se reporte sur la slide du deck via la routine `slide-planning` (OneDrive, ecriture en
place, garde-fou anti-ecrasement). Les deux lisent la **meme source** : ne jamais corriger la source depuis
la slide ou depuis Notion, c'est l'inverse.

## Garde-fous

- `guard: demander-avant` : **rien sans validation**. Sens unique. Aucune notification (pas de mention,
  commentaire, partage, deplacement de page - hook `garde_suppression.py`).
- **Ne rien inventer** : une date inconnue reste "a confirmer". Les modifs manuelles de l'utilisateur sont
  prioritaires (on garde, on ajuste autour).
