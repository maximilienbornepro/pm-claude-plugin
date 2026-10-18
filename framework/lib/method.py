#!/usr/bin/env python3
"""method - lecteur de la MÉTHODE d'une mission, déclarée en DONNÉE (A4, DM-017).

Principe du framework : « ce qui se calcule ne se raconte pas ». Ce qui relève de la méthode et
qui se calcule - barèmes de cotation, seuils-pivots, trames de livrables, chaîne de traçabilité -
vit dans `profiles/<mission>/method.yaml`, PAS dans la prose d'un skill ni en dur dans un script.
Les outils LISENT ici et calculent ; le modèle ne produit que la preuve. Migration INCRÉMENTALE,
livrable par livrable : une section absente rend simplement un défaut, rien ne casse.

    import method
    seuil = method.seuil(mission, "gate_defaut", 90)
    trame = method.trame(mission, "deck_gate")      # liste de sections, [] si absente

Sections conventionnelles de `method.yaml` :
  baremes:       échelles de cotation (ex. risque : niveaux + libellés)
  seuils:        valeurs-pivots comparées par les outils (ex. seuil de gate, capacité de sprint)
  trames:        plans de livrables (ordre des sections d'un deck, d'un CR…)
  tracabilite:   la chaîne besoin/TR -> ticket -> POC -> test (A5)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "framework" / "lib"))
import profile as prof  # noqa: E402
import yamlmin  # noqa: E402

SECTIONS = ["baremes", "seuils", "trames", "tracabilite"]
_CACHE = {}


def load(mission):
    """Le method.yaml de la mission, en dict. {} si le fichier est absent (fail-soft)."""
    if mission in _CACHE:
        return _CACHE[mission]
    path = Path(prof.mission_file(mission, "method.yaml"))
    data = yamlmin.load(path.read_text(encoding="utf-8")) if path.exists() else {}
    _CACHE[mission] = data or {}
    return _CACHE[mission]


def section(mission, name):
    """Une section de haut niveau (dict ou liste), sinon {}."""
    return load(mission).get(name) or {}


def bareme(mission, name):
    """Un barème de cotation déclaré sous `baremes:` (dict), sinon {}."""
    return section(mission, "baremes").get(name) or {}


def seuil(mission, key, default=None):
    """Un seuil-pivot déclaré sous `seuils:`, sinon `default`."""
    v = section(mission, "seuils").get(key)
    return default if v is None else v


def trame(mission, name):
    """Une trame de livrable déclarée sous `trames:` (liste de sections), sinon []."""
    t = section(mission, "trames").get(name)
    return t if isinstance(t, list) else []


def has(mission):
    """Vrai si la mission porte un method.yaml non vide."""
    return bool(load(mission))
