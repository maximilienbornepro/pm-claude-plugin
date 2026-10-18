#!/usr/bin/env python3
"""Tests A8 - orchestrateur cockpit (état calculé) + init (amorçage, plan sans écriture).
python3 framework/harness/test_cockpit.py"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "framework" / "lib"))
sys.path.insert(0, str(ROOT / "framework" / "generators" / "cockpit"))
sys.path.insert(0, str(ROOT / "framework" / "generators" / "init"))
os.environ["PMF_PROFILES"] = str(ROOT / "profiles")   # profil demo du framework
import cockpit as C  # noqa: E402
import init as I     # noqa: E402


def test_cockpit_classe_les_portes():
    _, cl, _ = C.etat_gates("demo")
    assert set(cl["franchie"]) == {"gate0", "gate1"}
    assert cl["bloquee"] == ["gate3"]
    assert cl["acte"] == ["gate2"]
    assert {"gate4", "gate5", "gate6"} <= set(cl["non_entamee"])


def test_cockpit_tracabilite():
    pc, n, rompus = C.etat_trace("demo")
    assert pc == "build" and n == 4
    assert {r[0] for r in rompus} == {"TR-02", "TR-03"}


def test_cockpit_actions_priorisees():
    _, cl, _ = C.etat_gates("demo")
    _, _, rompus = C.etat_trace("demo")
    acts = C.actions_suivantes("demo", cl, rompus)
    cmds = [a[1] for a in acts]
    # le bloquant passe avant l'acte, puis les ruptures
    assert cmds[0] == "pm run gate demo gate3"
    assert "pm run gate demo gate2" in cmds
    assert "pm run trace-audit demo" in cmds
    assert cmds.index("pm run gate demo gate3") < cmds.index("pm run gate demo gate2")


def test_init_plan_demo_tout_present():
    base, a_creer, deja = I.plan("demo")
    assert a_creer == [] and "profile.yml" in deja and "gate.yml" in deja


def test_init_plan_mission_neuve_tout_a_creer():
    base, a_creer, deja = I.plan("mission_neuve_inexistante_xyz")
    assert deja == []
    assert set(a_creer) >= {"profile.yml", "pipeline.yml", "gate.yml", "method.yaml",
                            "tracabilite.yml", "routing.yml"}
    assert not base.exists()   # le plan (dry-run) ne crée rien


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
