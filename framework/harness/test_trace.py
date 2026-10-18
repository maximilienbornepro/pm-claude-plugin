#!/usr/bin/env python3
"""Tests A5 - ruptures de la chaîne de traçabilité. python3 framework/harness/test_trace.py"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "framework" / "lib"))
sys.path.insert(0, str(ROOT / "framework" / "generators" / "trace-audit"))
os.environ["PMF_PROFILES"] = str(ROOT / "profiles")   # profil demo du framework
import trace_audit as T  # noqa: E402

PHASES = ["cadrage", "build", "recette", "prod"]
ORDRE = [
    {"maillon": "besoin", "proprietaire": "PMO", "exigible_des": "cadrage"},
    {"maillon": "ticket", "proprietaire": "TPM", "exigible_des": "cadrage"},
    {"maillon": "poc", "proprietaire": "Front", "exigible_des": "build"},
    {"maillon": "test", "proprietaire": "QA", "exigible_des": "recette"},
]


def _ev(liens, phase="build"):
    return T.evaluate({"id": "X", "liens": liens}, ORDRE, PHASES, phase)


def test_chaine_complete_pour_la_phase():
    r = _ev({"besoin": True, "ticket": "SIN-1", "poc": True})   # test pas exigible en build
    assert r["ruptures"] == [] and r["ou_aller"] == ""


def test_maillon_pas_encore_exigible_nest_pas_rupture():
    r = _ev({"besoin": True, "ticket": "SIN-1", "poc": True, "test": False})
    etats = {nom: st for nom, st, _, _ in r["etat"]}
    assert etats["test"] == "pas_encore" and r["ruptures"] == []


def test_ticket_manquant_des_cadrage_est_rupture():
    r = _ev({"besoin": True, "ticket": False, "poc": False})
    noms = [m["maillon"] for m in r["ruptures"]]
    assert noms == ["ticket", "poc"] and r["ou_aller"] == "TPM"   # premier manquant dans l'ordre


def test_poc_manquant_en_build():
    r = _ev({"besoin": True, "ticket": "SIN-1", "poc": False})
    assert [m["maillon"] for m in r["ruptures"]] == ["poc"] and r["ou_aller"] == "Front"


def test_test_devient_exigible_en_recette():
    r = _ev({"besoin": True, "ticket": "SIN-1", "poc": True, "test": False}, phase="recette")
    assert [m["maillon"] for m in r["ruptures"]] == ["test"] and r["ou_aller"] == "QA"


def test_facultatif_manquant_nest_pas_rupture():
    ordre = ORDRE[:2] + [{"maillon": "poc", "proprietaire": "Front", "exigible_des": "build", "facultatif": True}]
    r = T.evaluate({"id": "X", "liens": {"besoin": True, "ticket": "SIN-1", "poc": False}}, ordre, PHASES, "build")
    etats = {nom: st for nom, st, _, _ in r["etat"]}
    assert etats["poc"] == "facultatif" and r["ruptures"] == []


def test_relie_accepte_un_identifiant():
    assert T._relie("SIN-15") and T._relie(True)
    assert not T._relie(False) and not T._relie(None) and not T._relie("") and not T._relie("non")


def test_demo_charge_et_detecte_deux_ruptures():
    ordre, phases = T.load_chaine("demo")
    data = T.load_items("demo")
    assert data and data.get("phase_courante") == "build"
    rompus = [i for i in data["items"] if T.evaluate(i, ordre, phases, "build")["ruptures"]]
    assert {i["id"] for i in rompus} == {"TR-02", "TR-03"}


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
