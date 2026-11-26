"""paths - where each plugin component lives (one place to know the folder layout).

    framework/departements/<dep>/{generators,skills,agents,routines}/   one department = one trade
    framework/charte/{skills,generators}/                               style and tones (transverse)
    framework/garde-fous/                                               hooks
    framework/routines/<name>/SKILL.md                                  pointers kept for scheduled tasks

Scripts never hard-code `framework/<kind>/<name>`: they ask `find(kind, name)` or `all(kind)`.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FW = ROOT / "framework"
HOOKS = FW / "garde-fous"
KINDS = ("generators", "skills", "agents", "routines")


def bases():
    """Folders that can hold components: each department, then the charte."""
    return sorted(p for p in (FW / "departements").iterdir() if p.is_dir()) + [FW / "charte"]


def kind_dirs(kind):
    return [b / kind for b in bases() if (b / kind).is_dir()]


def all(kind):  # noqa: A001 - mirrors the vocabulary of organisation.yml
    """{name: path} ; an agent's path is its .md file, the others are folders."""
    out = {}
    for d in kind_dirs(kind):
        for p in sorted(d.iterdir()):
            if p.name.startswith((".", "_")) or p.name == "__pycache__":
                continue
            if kind == "agents" and p.suffix == ".md":
                out[p.stem] = p
            elif kind != "agents" and p.is_dir():
                out[p.name] = p
    return out


def find(kind, name):
    return all(kind).get(name)


def department_of(path):
    """'suivi' for framework/departements/suivi/..., 'charte' for framework/charte/..., else None."""
    rel = Path(path).resolve().relative_to(FW).parts
    if rel and rel[0] == "departements" and len(rel) > 1:
        return rel[1]
    return "charte" if rel and rel[0] == "charte" else None
