#!/usr/bin/env python3
"""templates - liste et montre le REGISTRE de templates (objet × solution) (DM-020).

Les templates vivent dans `templates/trackers/<solution>/<objet>.yml` (ex. notion/sujets.yml,
excel/risks.yml). Génériques : aucune valeur de mission. Lecture seule : il affiche, il n'écrit rien.

    python3 framework/generators/templates/templates.py                      # matrice objet × solution
    python3 framework/generators/templates/templates.py <solution> <objet>   # détail d'un template
    python3 framework/generators/templates/templates.py <objet>              # l'objet pour chaque solution
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "framework" / "lib"))
import templates as T  # noqa: E402


def _show(tpl, solution, obj):
    print(f"[{solution}/{obj}]  {tpl.get('title', obj)}")
    if tpl.get("solution") == "notion":
        props = tpl.get("properties") or []
        print(f"  propriétés : {', '.join(props)}")
        for sel, vals in (tpl.get("options") or {}).items():
            print(f"    {sel} : {', '.join(str(v) for v in (vals or []))}")
        vues = [v.get("name") for v in (tpl.get("views") or []) if isinstance(v, dict)]
        if vues:
            print(f"  vues : {', '.join(vues)}")
    else:  # excel
        if tpl.get("layout") == "matrix":
            print(f"  grille : {tpl.get('row_header')} × {', '.join((tpl.get('legende') or {}).get('roles', []))}")
            if tpl.get("per_role_sheets"):
                print(f"    + une feuille d'extrait par rôle : {', '.join(tpl.get('role_sheet_sections') or [])}")
        else:
            print(f"  colonnes : {', '.join(tpl.get('columns') or [])}")
        for k, vals in (tpl.get("legende") or {}).items():
            print(f"    {k} : {', '.join(str(v) for v in (vals or []))}")
    for key in ("sujets", "workstreams", "activites", "risques", "exemples"):
        if isinstance(tpl.get(key), list):
            print(f"  exemples : {len(tpl[key])} ligne(s)"); break
    if tpl.get("bareme_ref"):
        print(f"  cotation ← {tpl['bareme_ref']} (A4)")


def main():
    args = sys.argv[1:]
    sols = T.solutions()
    cat = T.catalog()
    if not args:
        print("Registre des templates (objet × solution) :\n")
        w = max([len(o) for o in T.OBJECTS] + [6])
        print("  " + "objet".ljust(w) + "  " + "  ".join(s.ljust(8) for s in sols))
        print("  " + "-" * (w + 2 + len(sols) * 10))
        for obj in T.OBJECTS:
            cells = ["  ✓     " if obj in cat.get(s, []) else "  ·     " for s in sols]
            print("  " + obj.ljust(w) + "  " + "".join(cells))
        print("\n  Détail : pm run templates <solution> <objet>")
        print("  Les templates sont GÉNÉRIQUES ; une mission redéfinit ses valeurs dans son profil.")
        return 0
    if len(args) == 1:
        obj = args[0]
        found = False
        for s in sols:
            tpl = T.load(s, obj)
            if tpl:
                _show(tpl, s, obj); print(); found = True
        if not found:
            print(f"[!] objet '{obj}' dans aucune solution. Objets : {', '.join(T.OBJECTS)}"); return 2
        return 0
    solution, obj = args[0], args[1]
    tpl = T.load(solution, obj)
    if not tpl:
        print(f"[!] pas de template {solution}/{obj}. Solutions : {', '.join(sols)}"); return 2
    _show(tpl, solution, obj)
    return 0


if __name__ == "__main__":
    sys.exit(main())
