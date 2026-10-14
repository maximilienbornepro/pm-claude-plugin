#!/usr/bin/env python3
"""raci - genere la matrice RACI et un extrait par role depuis des donnees (config-driven).

Source de verite : `profiles/<mission>/raci.yml` (roles = colonnes, activities = lignes, letters
R/A/C/I). Le generateur rend la MATRICE (markdown) et un EXTRAIT par role, et peut emettre un
PLAN de cellules pour appliquer les lignes a l'onglet RACI du classeur (ecriture gardee, via le
helper Office en session - jamais ici). Lecture seule par defaut.

  python3 raci.py <mission>              # matrice + extraits par role (markdown)
  python3 raci.py <mission> --json       # tout en JSON
  python3 raci.py <mission> --role Enix  # un seul extrait de role
  python3 raci.py <mission> --cells      # plan de cellules pour l'onglet matrice (A/..)
"""
import sys, json, importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location("pmf_profile", ROOT / "framework" / "lib" / "profile.py")
prof = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(prof)

ORDER = ["R", "A", "C", "I"]


def load(mission):
    return prof._load_yaml(prof.mission_dir(mission) / "raci.yml")


def _val(a, key):
    return str(a.get(key, "") or "").strip()


def matrix_md(d):
    roles, acts = d["roles"], d["activities"]
    head = "| Activite | " + " | ".join(r["col"] for r in roles) + " |"
    sep = "|---|" + "|".join("---" for _ in roles) + "|"
    out = [head, sep]
    for a in acts:
        out.append("| " + a["name"] + " | " + " | ".join(_val(a, r["key"]) or "-" for r in roles) + " |")
    return "\n".join(out)


def role_extracts(d):
    """Pour chaque role : les activites ou il est R (ou A/R), A, C, I - avec commentaire."""
    res = {}
    for r in d["roles"]:
        buckets = {k: [] for k in ORDER}
        for a in d["activities"]:
            parts = [p.strip() for p in _val(a, r["key"]).split("/") if p.strip()]
            for p in parts:
                if p in buckets:
                    buckets[p].append({"activity": a["name"], "comment": a.get("comment", "")})
        res[r["col"]] = buckets
    return res


def role_md(col, buckets):
    labels = {"R": "Realise (R)", "A": "Rend des comptes (A)", "C": "Consulte (C)", "I": "Informe (I)"}
    out = [f"### {col}"]
    for k in ORDER:
        items = buckets.get(k) or []
        if not items:
            continue
        out.append(f"- **{labels[k]}**")
        for it in items:
            c = f" - {it['comment']}" if it["comment"] else ""
            out.append(f"  - {it['activity']}{c}")
    if len(out) == 1:
        out.append("- (aucune activite dans ce lot)")
    return "\n".join(out)


def cells_plan(d):
    """Plan de cellules pour l'onglet matrice : entetes de role + une ligne par activite.
    Les lignes s'AJOUTENT a partir de la premiere ligne libre (a fixer en session selon le classeur)."""
    roles = d["roles"]
    plan = {"sheet": d.get("matrix_sheet", "RACI"), "header_row": d.get("header_row", 9),
            "columns": {r["letter"]: r["col"] for r in roles}, "rows": []}
    for a in d["activities"]:
        row = {"A": a["name"], "comment": a.get("comment", "")}
        for r in roles:
            v = _val(a, r["key"])
            if v:
                row[r["letter"]] = v
        plan["rows"].append(row)
    return plan


def main():
    if len(sys.argv) < 2:
        print("usage: raci.py <mission> [--json|--cells] [--role <col>]"); return 2
    mission = sys.argv[1]
    d = load(mission)
    if "--json" in sys.argv:
        print(json.dumps({"matrix": d, "role_extracts": role_extracts(d)}, ensure_ascii=False, indent=2)); return 0
    if "--cells" in sys.argv:
        print(json.dumps(cells_plan(d), ensure_ascii=False, indent=2)); return 0
    if "--role" in sys.argv:
        col = sys.argv[sys.argv.index("--role") + 1]
        ex = role_extracts(d).get(col)
        if not ex:
            print(f"role inconnu: {col}"); return 2
        print(role_md(col, ex)); return 0
    print("## Matrice RACI\n")
    print(matrix_md(d))
    print("\n## Extraits par role (onglets)\n")
    exts = role_extracts(d)
    for r in d["roles"]:
        print(role_md(r["col"], exts[r["col"]]) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
