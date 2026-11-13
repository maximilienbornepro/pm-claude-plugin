#!/usr/bin/env python3
"""Hook PostToolUse : tient a jour le kit portable du generateur d'archi (dist/archi-kit.zip).

Apres chaque Edit / Write / MultiEdit d'un fichier du generateur (framework/generators/archi, logos
partages, modele de demo), ou apres une commande Bash, relance `pack_kit.py --if-stale` sur le depot
de travail concerne : le zip n'est reconstruit que si une source a reellement change (empreinte).
Depots surveilles : celui qui contient le fichier modifie, sinon PM_FRAMEWORK_SRC, sinon
~/Documents/pm-framework s'il s'agit d'un clone git. Jamais le cache du plugin (copie en lecture).
Ne bloque jamais l'outil : toute erreur est ignoree.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

WATCH = ("framework/generators/archi/", "framework/assets/logos/", "profiles/demo/architecture/",
         "framework/lib/profile.py")


def repo_of(p):
    p = Path(p).resolve()
    for d in [p] + list(p.parents):
        if (d / "framework" / "generators" / "archi" / "pack_kit.py").exists():
            return d
    return None


def is_dev(root):
    return root and (root / ".git").exists() and "/plugins/cache/" not in str(root)


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}
    tool = data.get("tool_name", "")
    ti = data.get("tool_input") or {}
    roots = []
    fp = ti.get("file_path") or ti.get("notebook_path")
    if fp:
        r = repo_of(fp)
        if r and is_dev(r):
            rel = str(Path(fp).resolve().relative_to(r))
            if any(rel.startswith(w) or rel == w for w in WATCH):
                roots.append(r)
    elif tool == "Bash":
        for c in (os.environ.get("PM_FRAMEWORK_SRC"), str(Path.home() / "Documents" / "pm-framework")):
            if c and is_dev(Path(c)) and Path(c) not in roots:
                roots.append(Path(c))
    for r in roots:
        try:
            out = subprocess.run([sys.executable, str(r / "framework/generators/archi/pack_kit.py"), "--if-stale", "--quiet"],
                                 capture_output=True, text=True, timeout=120)
            if out.returncode != 0 and out.stderr:
                print(out.stderr.strip()[:300], file=sys.stderr)
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
