---
name: poc
description: Génère un POC React (Vite + TypeScript + Material UI) à partir des récits d'une mission. Un écran-stub par écran déclaré, une nav + un routeur, et la .claude/launch.json de la mission mise à jour (launcher auto). Dry-run par défaut ; étape suivante possible : scaffold Figma.
---

# Générateur poc (prototype d'interface)

À partir des **récits** d'une mission (les écrans à montrer), produit un **POC React runnable**
avec une **stack définie** : Vite + TypeScript + React Router + **Material UI**. Chaque écran
déclaré devient un composant-stub (titre + récit + zone « à construire »), relié par une nav
Material (AppBar + Drawer). Le **launcher se met à jour tout seul**.

## Données (`profiles/<mission>/poc.yml`)
- `output` : où générer le POC (relatif à la racine de la mission).
- `preview` : `{ name, port }` du serveur de preview (entrée ajoutée à `launch.json`).
- `screens` : la liste des écrans, **en flow inline** (pas de virgule dans les chaînes) :
  `{ name, path, title, recit }`. Les écrans peuvent être importés des récits du tracker.
- Racine de la mission : `PMF_PROJECT_ROOT`, sinon `root` du yml, sinon `$HOME/Documents/<name>`.

## Usage
```
python3 framework/pm.py run poc <mission>            # dry-run : fichiers + entrée launcher
python3 framework/pm.py run poc <mission> --apply    # écrit le POC + met à jour launch.json
python3 framework/pm.py run poc <mission> --json     # le plan en JSON
```
Après `--apply` : `npm install` dans le dossier généré, puis `preview_start "<preview.name>"`.

## Ce qui est généré
`package.json` (React/Vite/TS + MUI + Emotion), `vite.config.ts`, `tsconfig.json`, `index.html`
(police Roboto), `src/main.tsx` (ThemeProvider + CssBaseline), `src/App.tsx` (AppBar + Drawer +
routeur), `src/screens/registry.tsx` (typé), et un `src/screens/Screen<Nom>.tsx` par écran.

## Étape suivante (hors de ce générateur)
Scaffolder les écrans dans **Figma** depuis la même liste d'écrans (connecteur Figma), pour partir
d'une maquette. Le registre d'écrans sert de source commune POC ↔ Figma.

## Garde-fous
Dry-run par défaut ; `--apply` écrit seulement sous `output` (dossier de la mission) et fusionne
l'entrée dans `launch.json` (remplace le même `name`, n'efface pas les autres serveurs). Idempotent.
