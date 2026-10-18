#!/usr/bin/env python3
"""method - montre la MÉTHODE d'une mission, déclarée en donnée (A4, DM-017).

Rend `profiles/<mission>/method.yaml` en clair - barèmes, seuils, trames, chaîne de traçabilité - et
signale les sections encore VIDES (ce qui reste à sortir de la prose). Lecture seule : il affiche,
il ne calcule aucun verdict et n'écrit rien. Les générateurs qui en ont besoin lisent, eux, via
`framework/lib/method.py`.

    python3 framework/generators/method/method.py [mission]            # toutes les sections
    python3 framework/generators/method/method.py [mission] <section>  # baremes | seuils | trames | tracabilite
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "framework" / "lib"))
import method as M  # noqa: E402

TITRES = {
    "baremes": "Barèmes de cotation",
    "seuils": "Seuils-pivots",
    "trames": "Trames de livrables (ordre des sections)",
    "tracabilite": "Chaîne de traçabilité",
}


def _dump(val, indent=2):
    pad = " " * indent
    if isinstance(val, dict):
        for k, v in val.items():
            if isinstance(v, (dict, list)):
                print(f"{pad}{k} :")
                _dump(v, indent + 2)
            else:
                print(f"{pad}{k} : {v}")
    elif isinstance(val, list):
        print(f"{pad}" + " -> ".join(str(x) for x in val))
    else:
        print(f"{pad}{val}")


def _section(mission, name):
    data = M.section(mission, name)
    titre = TITRES.get(name, name)
    if not data:
        print(f"[{name}] {titre} : (vide - encore en prose, à sortir en donnée)")
        return False
    print(f"[{name}] {titre} :")
    _dump(data)
    return True


def main():
    mission = sys.argv[1] if len(sys.argv) > 1 else "demo"
    target = sys.argv[2] if len(sys.argv) > 2 else None
    if not M.has(mission) and not target:
        print(f"[!] pas de method.yaml pour la mission {mission}.")
        print("    Gabarit : copier une section à la fois dans profiles/" + mission + "/method.yaml.")
        return 2
    if target:
        if target not in M.SECTIONS:
            print(f"[!] section inconnue : {target}. Connues : {', '.join(M.SECTIONS)}"); return 2
        _section(mission, target)
    else:
        print(f"Méthode de la mission {mission} (profiles/{mission}/method.yaml) :\n")
        pleines = 0
        for name in M.SECTIONS:
            pleines += 1 if _section(mission, name) else 0
            print()
        print(f"{pleines}/{len(M.SECTIONS)} sections remplies.")
    print("\nLa méthode est une donnée : les outils calculent à partir d'ici, le modèle ne fait que la preuve.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
