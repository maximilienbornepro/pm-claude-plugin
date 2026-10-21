#!/usr/bin/env python3
"""Tests - generateur `plan` (design reutilisable + pipeline).
python3 framework/harness/test_plan.py

Hors-ligne : valide le contrat, le rendu, et les fonctions pures du pipeline
(allocation, burn-down) sur des fixtures. N'appelle jamais Jira.
"""
import os
import sys
import json
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GEN = ROOT / "framework" / "generators" / "plan"
sys.path.insert(0, str(ROOT / "framework" / "lib"))
sys.path.insert(0, str(ROOT / "framework" / "generators" / "projection"))
sys.path.insert(0, str(GEN))
import render as R        # noqa: E402
import validate as V      # noqa: E402
import from_jira as FJ    # noqa: E402

EXAMPLE = json.load(open(GEN / "plan.example.json", encoding="utf-8"))


def test_exemple_valide():
    errs, warns = V.check(EXAMPLE)
    assert not errs, f"exemple invalide : {errs}"
    assert not warns, f"exemple avec avertissements : {warns}"


def test_render_injecte_la_donnee():
    out = GEN / "__test_render.html"
    try:
        R.render(EXAMPLE, out)
        html = out.read_text(encoding="utf-8")
    finally:
        if out.exists():
            out.unlink()
    assert "__DATAJSON__" not in html, "placeholder non remplace"
    assert "Avancement et sprints Orion" in html, "marque absente du JSON injecte"
    assert '<script type="application/json" id="DATAJSON">' in html


def test_validate_detecte_les_manques():
    bad = {"meta": {}, "report": {}, "sprints": []}
    errs, _ = V.check(bad)
    assert errs, "un JSON vide devrait lever des erreurs"


def test_cdtd_par_statut():
    assert FJ._cdtd({"st": "Closed", "res": "2026-01-04", "d": 1}) == ("2026-01-04", None)
    assert FJ._cdtd({"st": "Closing", "res": "2026-01-05", "d": 1}) == ("2026-01-05", None)
    assert FJ._cdtd({"st": "Testing", "res": "2026-01-06"}) == (None, "2026-01-06")
    assert FJ._cdtd({"st": "In Progress", "res": None}) == (None, None)


def test_burndown_tk_inclut_lanterieur():
    start = datetime.date(2026, 1, 1)
    end = datetime.date(2026, 1, 15)
    rows = [
        {"est": 5.0, "st": "Closed", "res": "2026-01-04", "d": 1},      # fermé dans la fenêtre
        {"est": 3.0, "st": "In Progress", "res": None, "d": 0},         # ouvert
        {"est": 2.0, "st": "Closed", "res": "2025-12-30", "d": 1},      # fermé AVANT -> rattaché au sprint
    ]
    b = FJ.burndown(rows, start, end)
    # Le travail antérieur reste rattaché au sprint : scope = estimé total, il apparaît « fait » dès J0.
    assert b["scope"] == 10.0, f"scope attendu 10.0 (antérieur inclus), eu {b['scope']}"
    assert len(b["tk"]) == 3, "le ticket fermé avant le sprint reste dans le scope du sprint"
    assert b["start"] == "2026-01-01" and b["len"] == 14
    cds = [t.get("cd") for t in b["tk"]]
    assert "2026-01-04" in cds and "2025-12-30" in cds, "les dates de fermeture sont portées par les tickets"


def test_allocation_backlog_par_capacite():
    cfg = {"status_weights": {"In Progress": 0.4, "Testing": 0.85}}
    pcfg = {"caps": {"back": 10, "front": 10, "sre": 10}, "v11_from": 5}
    # 3 tickets back de 6 j sans sprint : tiennent 1 par sprint (cap 10, 2 ne tiennent pas ensemble)
    rows = [
        {"k": "A", "p": "back", "r": 6.0, "est": 6.0, "st": "To Do", "ph": "V1", "sp": None, "d": 0, "ne": 0},
        {"k": "B", "p": "back", "r": 6.0, "est": 6.0, "st": "To Do", "ph": "V1", "sp": None, "d": 0, "ne": 0},
        {"k": "C", "p": "back", "r": 6.0, "est": 6.0, "st": "To Do", "ph": "V1", "sp": None, "d": 0, "ne": 0},
    ]
    alloc, nsp = FJ.allocate(rows, cfg, pcfg)
    placed = {t["k"]: sp for sp, ts in alloc.items() for t in ts}
    assert placed["A"] == "S2" and placed["B"] == "S3" and placed["C"] == "S4", placed
    assert nsp >= 4


def test_pipeline_importe_les_helpers_projection():
    # from_jira reutilise bien le calcul verifie (pas de reimplementation parallele)
    assert hasattr(FJ.P, "_cap_etp") and hasattr(FJ.P, "load_config")
    assert hasattr(FJ.P, "_add_biz_days") and hasattr(FJ.P, "_pole")


def test_sprint_of_date_fenetres():
    pcfg = {"second_start": datetime.date(2026, 10, 18), "length": 14}
    assert FJ.sprint_of_date(datetime.date(2026, 10, 6), pcfg) == 1   # avant S2 -> S1
    assert FJ.sprint_of_date(datetime.date(2026, 10, 18), pcfg) == 2  # debut S2
    assert FJ.sprint_of_date(datetime.date(2026, 11, 1), pcfg) == 3   # +14 j -> S3


def test_reliquat_rattache_au_sprint_dentree_en_recette():
    # Un ticket en recette, bascule par Jira au sprint suivant, revient a son sprint d'entree.
    pcfg = {"second_start": datetime.date(2026, 10, 18), "length": 14,
            "test_status": "Testing", "reliquat": True}

    class FakeJ:
        def status_changes(self, key):
            return {
                "SIN-A": [("2026-10-06", "Dev Review", "Testing")],   # entre Testing en S1
                "SIN-B": [("2026-10-20", "Dev Review", "Testing")],   # entre Testing en S2
            }[key]

    rows = [{"k": "SIN-A", "s": "a", "p": "back", "st": "Testing", "sp": 2},   # Jira l'a mis en S2
            {"k": "SIN-B", "s": "b", "p": "back", "st": "Testing", "sp": 2},
            {"k": "SIN-C", "s": "c", "p": "back", "st": "In Progress", "sp": 2}]
    reliquat = FJ._appliquer_reliquat(FakeJ(), rows, pcfg)
    assert rows[0]["sp"] == 1, "le reliquat Testing S1 doit revenir en S1"
    assert rows[1]["sp"] == 2, "un Testing entre en S2 reste en S2"
    assert rows[2]["sp"] == 2, "un In Progress n'est pas touche"
    assert [r["k"] for r in reliquat] == ["SIN-A"]
    assert FJ.alert_reliquat(reliquat, pcfg), "une alerte doit etre produite"
    # desactivation par config
    rows2 = [{"k": "SIN-A", "s": "a", "p": "back", "st": "Testing", "sp": 2}]
    assert FJ._appliquer_reliquat(FakeJ(), rows2, {**pcfg, "reliquat": False}) == []
    assert rows2[0]["sp"] == 2


if __name__ == "__main__":
    import traceback
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    ok = 0
    for fn in fns:
        try:
            fn(); print(f"  PASS {fn.__name__}"); ok += 1
        except AssertionError as e:
            print(f"  FAIL {fn.__name__}: {e or 'assertion'}")
        except Exception as e:
            print(f"  ERR  {fn.__name__}: {e}"); traceback.print_exc()
    print(f"\n{ok}/{len(fns)} tests OK")
    sys.exit(0 if ok == len(fns) else 1)
