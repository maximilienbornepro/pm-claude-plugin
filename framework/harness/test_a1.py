#!/usr/bin/env python3
"""Tests A1 - derivation du compte depuis les metadonnees. python3 framework/harness/test_a1.py"""
import os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "framework" / "lib"))
os.environ["PMF_PROFILES"] = str(ROOT / "profiles")   # tester sur le profil demo du framework (deterministe)
import generator_meta as gm      # noqa: E402
import profile as prof           # noqa: E402


def test_derive_by_connector():
    assert gm.derive_account({"mcp_deps": ["jira"]}, "pro", "perso", "by-connector") == "pro"
    assert gm.derive_account({"mcp_deps": []}, "pro", "perso", "by-connector") == "perso"
    # by-connector : le cost ne compte pas, seul le connecteur
    assert gm.derive_account({"mcp_deps": [], "cost": "heavy-local"}, "pro", "perso", "by-connector") == "perso"
    assert gm.derive_account({"mcp_deps": ["m365"], "cost": "heavy-local"}, "pro", "perso", "by-connector") == "pro"


def test_derive_by_cost():
    # by-cost : perso pour le lourd OU le purement local ; safran seulement pour le leger a connecteur
    assert gm.derive_account({"cost": "heavy-local", "mcp_deps": ["m365"]}, "safran", "perso", "by-cost") == "perso"
    assert gm.derive_account({"cost": "light", "mcp_deps": ["m365"]}, "safran", "perso", "by-cost") == "safran"
    assert gm.derive_account({"cost": "light", "mcp_deps": []}, "safran", "perso", "by-cost") == "perso"      # local pur -> perso
    assert gm.derive_account({"cost": "heavy-local", "mcp_deps": []}, "safran", "perso", "by-cost") == "perso"


def test_alias_meme_meta():
    assert gm.meta_for("gate-deck") == gm.meta_for("deck-gate")
    assert gm.meta_for("notion-sujets") == gm.meta_for("notion-topics-audit")
    assert gm.meta_for("deck-gate").get("cost") == "heavy-local"


def test_load_all():
    a = gm.load_all()
    assert a["archi"]["meta"].get("cost") == "heavy-local"
    assert a["poc"]["meta"].get("cost") == "heavy-local"
    assert a["projection"]["meta"].get("cost") == "light"


def test_derive_for_resout_alias():
    # gate-deck (alias) -> deck-gate (m365) -> pro en by-connector
    assert gm.derive_for("gate-deck", "pro", "perso", "by-connector") == "pro"
    assert gm.derive_for("poc", "pro", "perso", "by-connector") == "perso"


def test_account_for_demo():
    if not prof.is_multi_account():
        print("    (mono-compte : account_for -> None, test saute)"); return
    assert prof.account_for("demo", "poc") == "perso"
    assert prof.account_for("demo", "projection") == "pro"
    assert prof.account_for("demo", "gate-deck") == "pro"     # alias -> deck-gate -> pro
    assert prof.account_for("demo", "reset") == "perso"
    assert prof.account_for("demo", "notion-scaffold") == "pro"   # exception explicite (routing.yml)


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
