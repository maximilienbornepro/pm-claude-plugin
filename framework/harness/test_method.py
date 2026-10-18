#!/usr/bin/env python3
"""Tests A4 - la méthode en donnée (method.py). python3 framework/harness/test_method.py

Teste le lecteur sur le profil demo du framework (déterministe) + le fail-soft sur une mission
sans method.yaml."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "framework" / "lib"))
os.environ["PMF_PROFILES"] = str(ROOT / "profiles")   # profil demo du framework
import method as M  # noqa: E402


def test_load_demo():
    assert M.has("demo")
    assert set(M.load("demo")) >= {"baremes", "seuils", "trames"}


def test_seuil_present():
    assert M.seuil("demo", "gate_defaut", 0) == 90
    assert M.seuil("demo", "sprint_capacite_defaut", 0) == 20


def test_seuil_defaut_si_absent():
    assert M.seuil("demo", "cle_qui_nexiste_pas", 42) == 42


def test_bareme():
    r = M.bareme("demo", "risque")
    assert r.get("niveaux") == ["faible", "moyen", "élevé", "critique"]
    assert "critique" in (r.get("labels") or {})


def test_trame_liste():
    t = M.trame("demo", "deck_gate")
    assert isinstance(t, list) and t[0] == "Contexte" and "Risques" in t


def test_trame_absente_rend_liste_vide():
    assert M.trame("demo", "livrable_inconnu") == []


def test_fail_soft_mission_sans_method():
    # mission inexistante -> fichier absent -> {} et défauts, sans exception
    assert M.load("mission_bidon_xyz") == {}
    assert not M.has("mission_bidon_xyz")
    assert M.seuil("mission_bidon_xyz", "gate_defaut", 90) == 90
    assert M.trame("mission_bidon_xyz", "deck_gate") == []


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
