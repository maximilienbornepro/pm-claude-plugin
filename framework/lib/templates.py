#!/usr/bin/env python3
"""templates - accès au REGISTRE de templates (objet × solution), déclaré en donnée (DM-020).

Les templates vivent dans `templates/trackers/<solution>/<objet>.yml` (ex. notion/sujets.yml). Ce
module les liste et les charge, sans rien afficher. Ils sont GENERIQUES : aucune valeur de mission.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "framework" / "lib"))
import yamlmin  # noqa: E402

TRK = ROOT / "templates" / "trackers"
OBJECTS = ["sujets", "planning", "raci", "risks"]      # ordre d'affichage


def solutions():
    """Les solutions disponibles (un sous-dossier de trackers/ = une solution)."""
    return sorted(d.name for d in TRK.iterdir() if d.is_dir()) if TRK.is_dir() else []


def catalog():
    """{solution: [objets présents]} - un objet = un <objet>.yml dans le dossier de la solution."""
    return {sol: sorted(f.stem for f in (TRK / sol).glob("*.yml")) for sol in solutions()}


def path_of(solution, obj):
    return TRK / solution / f"{obj}.yml"


def load(solution, obj):
    """Le template <solution>/<objet> (dict), ou None s'il n'existe pas."""
    p = path_of(solution, obj)
    return yamlmin.load(p.read_text(encoding="utf-8")) if p.exists() else None
