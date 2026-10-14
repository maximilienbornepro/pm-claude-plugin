#!/usr/bin/env python3
"""poc - genere un POC React (Vite + TS + Material UI) a partir des recits d'une mission.

Depuis `profiles/<mission>/poc.yml` (liste d'ecrans = un par recit), produit un POC runnable
avec **Material UI** (AppBar + Drawer + composants Material) : un ecran-stub par entree, une nav
+ un routeur, et MET A JOUR la .claude/launch.json de la mission (launcher auto). Dry-run par defaut.

  python3 poc.py <mission>            # dry-run : liste ce qui serait cree + l'entree launcher
  python3 poc.py <mission> --apply    # ecrit le POC et met a jour launch.json
  python3 poc.py <mission> --json     # le plan en JSON

Etape suivante (hors de ce generateur) : scaffolder les ecrans dans Figma (connecteur Figma).
"""
import sys, json, re, os, importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location("pmf_profile", ROOT / "framework" / "lib" / "profile.py")
prof = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(prof)

REACT, RDOM, RROUTER, VITE, PLUGIN, TS = "18.3.1", "18.3.1", "6.26.2", "5.4.8", "4.3.2", "5.5.4"
MUI, EMOTION = "6.1.6", "11.13.3"

STARTER = {
"package.json": json.dumps({
    "name": "poc", "private": True, "version": "0.0.0", "type": "module",
    "scripts": {"dev": "vite", "build": "tsc -b && vite build", "preview": "vite preview"},
    "dependencies": {"react": f"^{REACT}", "react-dom": f"^{RDOM}", "react-router-dom": f"^{RROUTER}",
        "@mui/material": f"^{MUI}", "@mui/icons-material": f"^{MUI}",
        "@emotion/react": f"^{EMOTION}", "@emotion/styled": f"^{EMOTION}"},
    "devDependencies": {"@vitejs/plugin-react": f"^{PLUGIN}", "typescript": f"^{TS}", "vite": f"^{VITE}",
        "@types/react": "^18.3.5", "@types/react-dom": "^18.3.0"}
}, indent=2),
"vite.config.ts": "import { defineConfig } from 'vite'\nimport react from '@vitejs/plugin-react'\n\n// base relative : le POC se sert aussi en statique (gh-pages).\nexport default defineConfig({ plugins: [react()], base: './' })\n",
"tsconfig.json": json.dumps({
    "compilerOptions": {"target": "ES2020", "useDefineForClassFields": True, "lib": ["ES2020", "DOM", "DOM.Iterable"],
        "module": "ESNext", "skipLibCheck": True, "moduleResolution": "bundler", "jsx": "react-jsx",
        "strict": True, "noEmit": True, "esModuleInterop": True},
    "include": ["src"]}, indent=2),
"index.html": ("<!doctype html>\n<html lang=\"fr\">\n<head><meta charset=\"UTF-8\">"
    "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
    "<link rel=\"preconnect\" href=\"https://fonts.googleapis.com\">\n"
    "<link href=\"https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap\" rel=\"stylesheet\">\n"
    "<title>POC</title></head>\n<body><div id=\"root\"></div>"
    "<script type=\"module\" src=\"/src/main.tsx\"></script></body>\n</html>\n"),
"src/main.tsx": ("import React from 'react'\nimport ReactDOM from 'react-dom/client'\n"
    "import { ThemeProvider, createTheme, CssBaseline } from '@mui/material'\nimport App from './App'\n\n"
    "const theme = createTheme({ palette: { mode: 'light', primary: { main: '#2f6ff0' } } })\n\n"
    "ReactDOM.createRoot(document.getElementById('root')!).render(\n"
    "  <React.StrictMode>\n    <ThemeProvider theme={theme}><CssBaseline /><App /></ThemeProvider>\n"
    "  </React.StrictMode>\n)\n"),
"src/App.tsx": ("import { HashRouter, Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom'\n"
    "import { AppBar, Toolbar, Typography, Drawer, Box, List, ListItemButton, ListItemText } from '@mui/material'\n"
    "import { SCREENS, PROJECT } from './screens/registry'\n\n"
    "const DW = 240\n\n"
    "function Shell() {\n"
    "  const loc = useLocation(); const nav = useNavigate()\n"
    "  return (\n"
    "    <Box sx={{ display: 'flex' }}>\n"
    "      <AppBar position=\"fixed\" sx={{ zIndex: (t) => t.zIndex.drawer + 1 }}>\n"
    "        <Toolbar><Typography variant=\"h6\" noWrap>{PROJECT} — POC</Typography></Toolbar>\n"
    "      </AppBar>\n"
    "      <Drawer variant=\"permanent\" sx={{ width: DW, flexShrink: 0, ['& .MuiDrawer-paper']: { width: DW, boxSizing: 'border-box' } }}>\n"
    "        <Toolbar />\n        <List>\n"
    "          {SCREENS.map((s) => (\n"
    "            <ListItemButton key={s.path} selected={loc.pathname === s.path} onClick={() => nav(s.path)}>\n"
    "              <ListItemText primary={s.title} />\n            </ListItemButton>\n"
    "          ))}\n        </List>\n      </Drawer>\n"
    "      <Box component=\"main\" sx={{ flexGrow: 1, p: 3 }}>\n        <Toolbar />\n        <Routes>\n"
    "          {SCREENS.map((s) => <Route key={s.path} path={s.path} element={<s.Component />} />)}\n"
    "          <Route path=\"*\" element={<Navigate to={SCREENS[0]?.path ?? '/'} replace />} />\n"
    "        </Routes>\n      </Box>\n    </Box>\n  )\n}\n\n"
    "export default function App() {\n  return <HashRouter><Shell /></HashRouter>\n}\n"),
}

SCREEN_TPL = ("import { Box, Typography, Paper } from '@mui/material'\n\n"
    "export default function __COMP__() {\n  return (\n    <Box>\n"
    "      <Typography variant=\"h4\" gutterBottom>__TITLE__</Typography>\n"
    "      <Typography variant=\"body2\" color=\"text.secondary\" sx={{ mb: 3 }}>__RECIT__</Typography>\n"
    "      <Paper variant=\"outlined\" sx={{ p: 6, textAlign: 'center', color: 'text.disabled' }}>\n"
    "        Écran à construire (__PATH__).\n      </Paper>\n    </Box>\n  )\n}\n")


def _comp(name):
    c = re.sub(r"[^A-Za-z0-9]", "", name) or "Screen"
    return "Screen" + c[0].upper() + c[1:]


def load(mission):
    return prof._load_yaml(prof.mission_dir(mission) / "poc.yml")


def mission_root(mission, cfg):
    env = os.environ.get("PMF_PROJECT_ROOT")
    if env:
        return Path(env)
    if cfg.get("root"):
        return Path(cfg["root"]).expanduser()
    name = prof.load(mission)["profile"].get("name", mission)
    return Path.home() / "Documents" / name


def build_plan(mission):
    cfg = load(mission)
    root = mission_root(mission, cfg)
    out = root / cfg["output"]
    screens = cfg.get("screens") or []
    project = prof.load(mission)["profile"].get("name", mission)
    files = dict(STARTER)
    reg_imports, reg_rows = [], []
    for s in screens:
        comp = _comp(s["name"])
        files[f"src/screens/{comp}.tsx"] = (SCREEN_TPL.replace("__COMP__", comp)
            .replace("__TITLE__", s.get("title", s["name"]))
            .replace("__RECIT__", s.get("recit", "")).replace("__PATH__", s.get("path", "/")))
        reg_imports.append(f"import {comp} from './{comp}'")
        reg_rows.append(f"  {{ path: {json.dumps(s.get('path','/'))}, title: {json.dumps(s.get('title', s['name']))}, Component: {comp} }},")
    files["src/screens/registry.tsx"] = ("import type { ComponentType } from 'react'\n" +
        "\n".join(reg_imports) + "\n\n" + f"export const PROJECT = {json.dumps(project)}\n\n" +
        "export const SCREENS: { path: string; title: string; Component: ComponentType }[] = [\n" +
        "\n".join(reg_rows) + "\n]\n")
    launcher = {"name": cfg["preview"]["name"], "runtimeExecutable": "npm",
                "runtimeArgs": ["--prefix", str(out), "run", "dev", "--", "--port", str(cfg["preview"]["port"])],
                "port": cfg["preview"]["port"]}
    return {"root": str(root), "out": str(out),
            "launcher_path": str(root / cfg.get("launcher", ".claude/launch.json")),
            "files": files, "launcher": launcher, "screens": [s["name"] for s in screens]}


def update_launcher(path, entry, apply):
    p = Path(path)
    data = {"version": "0.0.1", "configurations": []}
    if p.exists():
        try: data = json.loads(p.read_text(encoding="utf-8"))
        except Exception: pass
    cfgs = [c for c in data.get("configurations", []) if c.get("name") != entry["name"]]
    cfgs.append(entry)
    data["configurations"] = cfgs
    if apply:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return len(cfgs)


def main():
    if len(sys.argv) < 2:
        print("usage: poc.py <mission> [--apply|--json]"); return 2
    mission = sys.argv[1]
    plan = build_plan(mission)
    if "--json" in sys.argv:
        print(json.dumps({k: (sorted(v) if k == "files" else v) for k, v in plan.items()}, ensure_ascii=False, indent=2)); return 0
    apply = "--apply" in sys.argv
    print(f"POC '{mission}' (React + Vite + Material UI) -> {plan['out']}")
    print(f"Ecrans ({len(plan['screens'])}) : {', '.join(plan['screens'])}")
    print(f"Fichiers : {len(plan['files'])}  ·  launcher : {plan['launcher']['name']} (port {plan['launcher']['port']})")
    if not apply:
        print("\nDry-run : seraient crees (--apply pour ecrire) :")
        for rel in sorted(plan["files"]): print("  + " + rel)
        print("  ~ maj " + plan["launcher_path"] + " (serveur " + plan["launcher"]["name"] + ")")
        return 0
    out = Path(plan["out"])
    for rel, content in plan["files"].items():
        f = out / rel; f.parent.mkdir(parents=True, exist_ok=True); f.write_text(content, encoding="utf-8")
    n = update_launcher(plan["launcher_path"], plan["launcher"], True)
    print(f"\nEcrit : {len(plan['files'])} fichiers sous {out}")
    print(f"launch.json mis a jour ({n} serveurs). Lancer : npm install puis preview_start \"{plan['launcher']['name']}\".")
    return 0


if __name__ == "__main__":
    sys.exit(main())
