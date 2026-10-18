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


def test_validate_detecte_burndown_remontant():
    data = json.loads(json.dumps(EXAMPLE))
    data["report"]["burn_v1"]["serie"][2]["y"] = 999.0  # remontee
    _, warns = V.check(data)
    assert any("remonte" in w for w in warns), "la remontee du burn-down doit etre signalee"


def test_burndown_monotone_et_fenetre():
    start = datetime.date(2026, 1, 1)
    end = datetime.date(2026, 1, 15)
    today = datetime.date(2026, 1, 10)
    rows = [
        {"est": 5.0, "res": "2026-01-04"},   # brule dans la fenetre
        {"est": 3.0, "res": None},           # pas encore brule
        {"est": 2.0, "res": "2025-12-30"},   # brule AVANT le sprint -> hors scope
    ]
    b = FJ.burndown(rows, start, end, today)
    assert b["scope"] == 8.0, f"scope attendu 8.0 (hors travail anterieur), eu {b['scope']}"
    ys = [p["y"] for p in b["serie"]]
    assert ys == sorted(ys, reverse=True), f"burn-down non monotone : {ys}"
    assert b["serie"][-1]["x"] == (today - start).days, "serie s'arrete aujourd'hui"


def test_burndown_sprint_futur_vide():
    start = datetime.date(2026, 2, 1)
    b = FJ.burndown([{"est": 3.0, "res": None}], start, start + datetime.timedelta(days=14),
                    datetime.date(2026, 1, 1))
    assert b["serie"] == [], "un sprint a venir n'a pas de serie reelle"


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
